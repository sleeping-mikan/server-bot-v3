"""
utils.py — コマンドハンドラ共通のヘルパー関数

commands/*.py はここから import する。main.py への直接 import は不要。

パス検証 (is_path_within_scope / is_important_bot_file) は
web/ からも参照できるよう core/path_utils.py に移動済み。
"""

from __future__ import annotations

import json
import logging

import discord

from bot.embeds import ModifiedEmbeds
from core.state import ctx


async def print_user(logger: logging.Logger, user: discord.User) -> None:
    """コマンド実行ユーザーをログに記録する。"""
    logger.info("command used by " + str(user))


async def is_administrator(user: discord.User) -> bool:
    """ユーザーがサーバー管理者権限を持つかを返す。"""
    return user.guild_permissions.administrator


async def is_force_administrator(user: discord.User) -> bool:
    """コンフィグの admin.members リストに含まれるユーザーかを返す。"""
    return user.id in ctx.config["discord_commands"]["admin"]["members"]


async def user_permission(user: discord.User) -> int:
    """ユーザーのコマンド権限レベルを返す。

    管理者は最大レベル、それ以外はコンフィグの members テーブルから取得する。
    未登録ユーザーは 0 (最低権限) 扱い。
    """
    if await is_administrator(user):
        return max(ctx.text.command_permission.values())
    return ctx.config["discord_commands"]["admin"]["members"].get(str(user.id), 0)


async def rewrite_config() -> bool:
    """ctx.config をファイルに書き戻す。失敗時は False を返す。"""
    try:
        with ctx.paths.config_file.open("w", encoding="utf-8") as f:
            json.dump(ctx.config, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


async def not_enough_permission(
    interaction: discord.Interaction,
    logger: logging.Logger,
) -> None:
    """権限不足の場合に ephemeral エラーメッセージを返す。"""
    logger.error("permission denied")
    embed = ModifiedEmbeds.ErrorEmbed(title=ctx.text.response_msg["other"]["no_permission"])
    await interaction.response.send_message(embed=embed, ephemeral=True)


def is_running_server(logger: logging.Logger) -> bool:
    """サーバーが起動中なら True を返してエラーログを出す。

    停止が前提のコマンド (backup create など) の先頭ガードとして使う。
    is_stopped() ではなく is_running() を使うことで、プロセス終了済みだが
    reset() がまだ呼ばれていない競合状態での誤判定を防ぐ。
    """
    if ctx.server_process.is_running():
        logger.error("server is still running")
        return True
    return False


def is_stopped_server(logger: logging.Logger) -> bool:
    """サーバーが停止中なら True を返してエラーログを出す。

    稼働が前提のコマンド (serverin など) の先頭ガードとして使う。
    """
    if ctx.server_process.is_stopped():
        logger.error("server is not running")
        return True
    return False
