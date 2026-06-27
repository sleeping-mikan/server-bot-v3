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


def get_self_commit_id() -> str | None:
    """リポジトリ HEAD の最新コミット SHA を GitHub API で取得する。"""
    branch = ctx.config["update"]["branch"] if ctx.config else "main"
    url = (
        f'https://api.github.com/repos/{_REPOSITORY["user"]}'
        f'/{_REPOSITORY["name"]}/commits/{branch}'
    )
    response = requests.get(url)
    if response.status_code != 200:
        _sys_logger.error("github api error. status code: " + str(response.status_code))
        return None
    return response.json()["sha"]


def save_mikanassets_dat() -> None:
    """コミット ID を mikanassets/.dat に保存する(初回のみ)。"""
    ctx.paths.data_dir.mkdir(parents=True, exist_ok=True)
    if not ctx.paths.dat_file.exists():
        commit = get_self_commit_id() or ""
        ctx.paths.dat_file.write_text(json.dumps({"commit_id": commit}))


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

    github_commit = get_self_commit_id()
    if github_commit is None:
        _update_logger.error(
            "github commit is None. (github api error. check network / repository settings)"
        )
        if interaction is not None and embed is not None:
            embed.add_field(name="error", value="github response error.", inline=False)
            await sender(interaction=interaction, embed=embed)
        return

    _update_logger.info("github commit -> " + github_commit)
    _update_logger.info(" local commit -> " + commit)

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
        _sys_logger.error("response error. status_code : " + str(response.status_code))
        if interaction is not None and embed is not None:
            embed.add_field(name="error : github zip download error", value="", inline=False)
            await sender(interaction=interaction, embed=embed)
        return

    new_repo_extract_dir = os.path.join(ctx.temp_path, "new_repo")
    if os.path.exists(new_repo_extract_dir):
        rmtree(new_repo_extract_dir)
    os.makedirs(new_repo_extract_dir)

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(new_repo_extract_dir)

    extracted_items = os.listdir(new_repo_extract_dir)
    if len(extracted_items) != 1:
        _sys_logger.error("unexpected zip structure: " + str(extracted_items))
        if interaction is not None and embed is not None:
            embed.add_field(name="error : unexpected zip structure", value="", inline=False)
            await sender(interaction=interaction, embed=embed)
        return

    new_repo_root = os.path.join(new_repo_extract_dir, extracted_items[0])

    msg_id = "0"
    channel_id = "0"
    if interaction is not None and embed is not None:
        msg_id = str((await interaction.original_response()).id)
        channel_id = str(interaction.channel_id)
        await sender(interaction=interaction, embed=embed)

    _replace_logger.info("call update_apply.py")
    _replace_logger.info("replace args : " + msg_id + " " + channel_id)

    now_path = str(ctx.paths.base)
    update_apply_path = str(ctx.paths.update_apply_file)

    os.execv(sys.executable, [
        sys.executable,
        update_apply_path,
        new_repo_root,
        now_path,
        "server.py",
        msg_id,
        channel_id,
        ctx.token,
    ])
