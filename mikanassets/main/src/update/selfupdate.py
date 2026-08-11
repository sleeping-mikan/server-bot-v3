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

# .config の update.branch が存在しない場合や config 未読込時に使う、常に存在する前提のブランチ。
_FALLBACK_BRANCH = "release"

# LogManager.init() 後にこのモジュールがインポートされることを前提にする
_update_logger  = logging.getLogger("update")
_replace_logger = logging.getLogger("update.replace")
_sys_logger     = logging.getLogger("sys")


def _get_commit_id_for_branch(branch: str) -> tuple[str | None, str, str]:
    """指定ブランチ HEAD の最新コミット SHA を GitHub API で取得する。

    戻り値: (コミット SHA, エラー種別, 詳細(ログ用の生の英語文字列))。
    エラー種別は text_pack (assets/text/*.json の response_msg.update) のキー名と対応させる:
      "" (成功) / "branch_not_found" / "github_api_error"
    Discord に表示する文言は呼び出し側が text_pack を使って言語ごとに組み立てるため、
    ここでは(ログ用途以外の)整形済み英語メッセージは作らない。
    """
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
            return None, "branch_not_found", branch
        return None, "github_api_error", str(response.status_code)
    return response.json()["sha"], "", ""


def resolve_update_branch() -> tuple[str, str | None, str, str]:
    """.config の update.branch を確認し、実際に使うブランチとそのコミットを決定する。

    指定ブランチが GitHub 上に存在しない場合は _FALLBACK_BRANCH にフォールバックする。
    コミット取得そのものが失敗した場合(ネットワークエラー等)はフォールバックせずそのまま返す
    (フォールバックしても同じ理由で失敗する可能性が高いため)。

    戻り値: (実際に使ったブランチ名, コミット SHA (失敗時 None), エラー種別, 詳細)
    """
    branch = ctx.config["update"]["branch"] if ctx.config else _FALLBACK_BRANCH
    commit, error_kind, detail = _get_commit_id_for_branch(branch)
    if commit is not None or branch == _FALLBACK_BRANCH or error_kind != "branch_not_found":
        return branch, commit, error_kind, detail
    _update_logger.warning(
        f"update.branch '{branch}' not found on GitHub. falling back to '{_FALLBACK_BRANCH}'."
    )
    commit, error_kind, detail = _get_commit_id_for_branch(_FALLBACK_BRANCH)
    return _FALLBACK_BRANCH, commit, error_kind, detail


def get_self_commit_id() -> tuple[str | None, str]:
    """.config の update.branch (フォールバック込み) の最新コミット SHA を取得する。

    戻り値: (コミット SHA, エラー種別)。成功時は種別が空文字列になる。
    """
    _, commit, error_kind, _ = resolve_update_branch()
    return commit, error_kind


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

    branch, github_commit, error_kind, error_detail = resolve_update_branch()
    if github_commit is None:
        _update_logger.error(
            f"github commit is None. kind={error_kind or 'unknown'} detail={error_detail}"
        )
        if interaction is not None and embed is not None:
            if error_kind == "branch_not_found":
                message = text_pack["branch_not_found"].format(error_detail)
            elif error_kind == "github_api_error":
                message = text_pack["github_api_error"].format(error_detail)
            else:
                message = text_pack["github_response_error"]
            embed.add_field(name="error", value=message, inline=False)
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

    # branch は上の resolve_update_branch() で実際に見つかったブランチ
    # (.config の指定が無効ならここまでに release へフォールバック済み)。
    # ここで .config の値を読み直すとコミット確認とzip取得のブランチがずれるため使わない。
    zip_url = (
        f'https://github.com/{_REPOSITORY["user"]}'
        f'/{_REPOSITORY["name"]}/archive/refs/heads/{branch}.zip'
    )
    response = requests.get(zip_url)
    if response.status_code != 200:
        _sys_logger.error(f"response error. status_code : {response.status_code}")
        _sys_logger.error(f"request url: {zip_url}")
        if interaction is not None and embed is not None:
            embed.add_field(name="error", value=text_pack["download_failed"], inline=False)
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
            embed.add_field(name="error", value=text_pack["unexpected_zip_structure"], inline=False)
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
