"""
utils.py — コマンドハンドラ共通のヘルパー関数

commands/*.py はここから import する。main.py への直接 import は不要。
"""

from __future__ import annotations

import json
import logging
import os
import pathlib

import discord

from bot.embeds import ModifiedEmbeds
from core.state import ctx


async def print_user(logger: logging.Logger, user: discord.User) -> None:
    logger.info("command used by " + str(user))


async def is_administrator(user: discord.User) -> bool:
    return user.guild_permissions.administrator


async def is_force_administrator(user: discord.User) -> bool:
    return user.id in ctx.config["discord_commands"]["admin"]["members"]


async def user_permission(user: discord.User) -> int:
    if await is_administrator(user):
        return max(ctx.text.command_permission.values())
    return ctx.config["discord_commands"]["admin"]["members"].get(str(user.id), 0)


async def rewrite_config() -> bool:
    """ctx.config をファイルに書き戻す。"""
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
    logger.error("permission denied")
    embed = ModifiedEmbeds.ErrorEmbed(title=ctx.text.response_msg["other"]["no_permission"])
    await interaction.response.send_message(embed=embed, ephemeral=True)


def is_running_server(logger: logging.Logger) -> bool:
    if not ctx.server_process.is_stopped():
        logger.error("server is still running")
        return True
    return False


def is_stopped_server(logger: logging.Logger) -> bool:
    if ctx.server_process.is_stopped():
        logger.error("server is not running")
        return True
    return False


def is_path_within_scope(path: str) -> bool:
    """path が ctx.server_path 以下にあるかを確認する。"""
    resolved_path = pathlib.Path(os.path.abspath(path)).resolve(strict=False)
    resolved_server = pathlib.Path(ctx.server_path).resolve()
    try:
        resolved_path.relative_to(resolved_server)
        return True
    except ValueError:
        return False


async def is_important_bot_file(path: str) -> bool:
    """path が sys_files (重要ファイル) に該当するかを確認する。"""
    resolved = pathlib.Path(os.path.abspath(path)).resolve()
    sys_files = ctx.config["discord_commands"]["cmd"]["stdin"]["sys_files"]
    src_dir = pathlib.Path(__file__).parent
    important = [
        pathlib.Path(os.path.abspath(src_dir / f)).resolve()
        for f in sys_files
    ] + [
        pathlib.Path(os.path.join(ctx.server_path, f)).resolve()
        for f in sys_files
    ]
    return any(resolved == f or resolved.is_relative_to(f) for f in important)
