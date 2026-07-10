"""
selfupdate.py — ボット本体のセルフアップデート機能

main.py から切り出したモジュール。
GitHub API で最新コミット SHA を確認し、差分があれば zip をダウンロードして
update_apply.py にバトンタッチする。

このモジュールのロガーは logging.getLogger() で取得する。
main.py 側で create_logger() を呼んでハンドラを付けた後にこのモジュールを
インポートすれば、同じロガー名を通じて出力が正しく機能する。
"""

from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import sys
import zipfile
from shutil import rmtree
from typing import Any

import requests

from core.state import ctx

_REPOSITORY = {
    "user": "sleeping-mikan",
    "name": "server-bot-v3",
}

# LogManager.init() 後にこのモジュールがインポートされることを前提にする
_update_logger  = logging.getLogger("update")
_replace_logger = logging.getLogger("update.replace")
_sys_logger     = logging.getLogger("sys")


def get_self_commit_id() -> tuple[str | None, str]:
    """リポジトリ HEAD の最新コミット SHA を GitHub API で取得する。

    戻り値: (コミット SHA, エラー理由)。成功時は理由が空文字列になる。
    """
    branch = ctx.config["update"]["branch"] if ctx.config else "main"
    url = (
        f'https://api.github.com/repos/{_REPOSITORY["user"]}'
        f'/{_REPOSITORY["name"]}/commits/{branch}'
    )
    response = requests.get(url)
    if response.status_code != 200:
        _sys_logger.error(f"github api error. status code: {response.status_code}")
        _sys_logger.error(f"request url: {url}")
        _sys_logger.error(f"response body: {response.text}")
        # 422 はブランチ(ref)が存在しない場合に返される
        if response.status_code == 422:
            return None, f"branch '{branch}' not found. check 'update.branch' in .config"
        return None, f"github api error. (status code: {response.status_code})"
    return response.json()["sha"], ""


def save_mikanassets_dat() -> None:
    """コミット ID を mikanassets/.dat に保存する(初回のみ)。"""
    ctx.paths.data_dir.mkdir(parents=True, exist_ok=True)
    if not ctx.paths.dat_file.exists():
        commit, _ = get_self_commit_id()
        ctx.paths.dat_file.write_text(json.dumps({"commit_id": commit or ""}))


async def update_self_if_commit_changed(
    interaction: Any = None,
    embed: Any = None,
    text_pack: dict | None = None,
    sender: Any = None,
    is_force: bool = False,
) -> None:
    """GitHub と比較してコミットが変わっていれば自己更新を実行する。

    interaction / embed / sender は Discord 経由で呼ぶ場合のみ指定する。
    """
    if not ctx.paths.dat_file.exists():
        save_mikanassets_dat()

    try:
        data = json.loads(ctx.paths.dat_file.read_text(encoding="utf-8"))
        commit = data["commit_id"]
    except (json.JSONDecodeError, KeyError, OSError):
        if interaction is not None and embed is not None:
            embed.add_field(
                name="error",
                value="json load error (mikanassets/.dat). delete file.",
                inline=False,
            )
            await sender(interaction=interaction, embed=embed)
        _update_logger.error("json load error (mikanassets/.dat). delete file.")
        return

    github_commit, error_reason = get_self_commit_id()
    if github_commit is None:
        _update_logger.error(
            "github commit is None. (github api error. check network / repository settings)"
        )
        if interaction is not None and embed is not None:
            embed.add_field(name="error", value=error_reason or "github response error.", inline=False)
            await sender(interaction=interaction, embed=embed)
        return

    _update_logger.info(f"github commit -> {github_commit}")
    _update_logger.info(f" local commit -> {commit}")

    if interaction is not None and embed is not None:
        embed.add_field(name="github file", value=github_commit, inline=False)
        embed.add_field(name="local file", value=commit, inline=False)
        await sender(interaction=interaction, embed=embed)

    if commit == github_commit and not is_force:
        if interaction is not None and embed is not None:
            embed.add_field(name="", value=text_pack["same"], inline=False)
            await sender(interaction=interaction, embed=embed)
        _update_logger.info("commit is same. no update.")
        return

    data["commit_id"] = github_commit
    ctx.paths.dat_file.write_text(json.dumps(data), encoding="utf-8")

    if interaction is not None and embed is not None:
        key = "force" if is_force else "different"
        embed.add_field(name="", value=text_pack[key], inline=False)
        await sender(interaction=interaction, embed=embed)

    _update_logger.info("commit changed. update self.")

    branch = ctx.config["update"]["branch"] if ctx.config else "main"
    zip_url = (
        f'https://github.com/{_REPOSITORY["user"]}'
        f'/{_REPOSITORY["name"]}/archive/refs/heads/{branch}.zip'
    )
    response = requests.get(zip_url)
    if response.status_code != 200:
        _sys_logger.error(f"response error. status_code : {response.status_code}")
        _sys_logger.error(f"request url: {zip_url}")
        if interaction is not None and embed is not None:
            embed.add_field(name="error : github zip download error", value="", inline=False)
            await sender(interaction=interaction, embed=embed)
        return

    new_repo_extract_dir = ctx.temp_path / "new_repo"
    if new_repo_extract_dir.exists():
        rmtree(new_repo_extract_dir)
    new_repo_extract_dir.mkdir()

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(new_repo_extract_dir)

    extracted_items = list(new_repo_extract_dir.iterdir())
    if len(extracted_items) != 1:
        _sys_logger.error(f"unexpected zip structure: {extracted_items}")
        if interaction is not None and embed is not None:
            embed.add_field(name="error : unexpected zip structure", value="", inline=False)
            await sender(interaction=interaction, embed=embed)
        return

    new_repo_root = str(extracted_items[0])

    msg_id = "0"
    channel_id = "0"
    if interaction is not None and embed is not None:
        msg_id = str((await interaction.original_response()).id)
        channel_id = str(interaction.channel_id)
        await sender(interaction=interaction, embed=embed)

    _replace_logger.info("call update_apply.py")
    _replace_logger.info(f"replace args : {msg_id} {channel_id}")

    now_path = str(ctx.paths.base)
    update_apply_path = str(ctx.paths.update_apply_file)

    env = os.environ.copy()
    env["MIKAN_BOT_TOKEN"] = ctx.token
    entry_file = os.environ.get("MIKAN_ENTRY_FILE", "server.py")

    # os.execve は Windows 環境でプロセスがクラッシュする (STATUS_ACCESS_VIOLATION) ことが
    # 確認されたため、子プロセスとして起動してから自分は即終了する方式に変更している。
    # (DETACHED_PROCESS は子のコンソール出力が消えるため使わない。コンソールは継承する)
    subprocess.Popen(
        [
            sys.executable,
            update_apply_path,
            new_repo_root,
            now_path,
            entry_file,
            msg_id,
            channel_id,
        ],
        env=env,
        close_fds=True,
    )
    os._exit(0)
