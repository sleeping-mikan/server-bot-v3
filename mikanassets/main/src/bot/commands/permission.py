"""bot/commands/permission.py — /permission change, /permission view, /lang handlers."""

from __future__ import annotations

from enum import Enum, auto
from typing import Awaitable, Callable

import discord
from discord import app_commands

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from bot.text_data import available_languages
from core.log_setup import LogManager
from core.state import ctx
from bot.utils import (
    get_member_level,
    is_administrator,
    not_enough_permission,
    print_user,
    rewrite_config,
    set_member_level,
    user_permission,
)


# ── 実装 (Implementation) ─────────────────────────────────────────────────────

class PermChangeResult(Enum):
    ADDED         = auto()
    UPDATED       = auto()
    REMOVED       = auto()
    NOT_FOUND     = auto()
    INVALID_LEVEL = auto()


def _set_permission(user_id: int, level: int) -> PermChangeResult:
    """権限レベルを設定する (新規追加・既存更新どちらも対応)。"""
    max_level = max(ctx.text.command_permission.values())
    if not (1 <= level <= max_level):
        return PermChangeResult.INVALID_LEVEL
    is_update = get_member_level(user_id) != 0
    set_member_level(user_id, level)
    return PermChangeResult.UPDATED if is_update else PermChangeResult.ADDED


def _remove_permission(user_id: int) -> PermChangeResult:
    if get_member_level(user_id) == 0:
        return PermChangeResult.NOT_FOUND
    set_member_level(user_id, 0)
    return PermChangeResult.REMOVED


async def _change_lang(language: str, reload_text: Callable[[], Awaitable[None]]) -> None:
    ctx.config["discord_commands"]["lang"] = language
    ctx.text.lang = language
    await rewrite_config()
    await reload_text()


# ── 表示 (Presentation) ───────────────────────────────────────────────────────

def setup(get_text_dat: Callable[[], Awaitable[None]]) -> None:
    admin_logger      = LogManager.cmd.getChild("admin")
    permission_logger = LogManager.cmd.getChild("permission")
    lang_logger       = LogManager.cmd.getChild("lang")

    command_group_permission = app_commands.Group(name="permission", description="permission group")

    @command_group_permission.command(
        name="change",
        description=ctx.text.command_desc[ctx.text.lang]["permission"]["change"],
    )
    @app_commands.describe(**ctx.text.command_args_desc[ctx.text.lang]["permission"]["change"])
    async def change_cmd(interaction: discord.Interaction, level: int, user: discord.User) -> None:
        await print_user(admin_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/permission change {level} {user}")
        if await user_permission(interaction.user) < ctx.text.command_permission["permission change"]:
            await not_enough_permission(interaction, admin_logger)
            return
        result = _remove_permission(user.id) if level == 0 else _set_permission(user.id, level)
        add_success = ctx.text.response_msg["permission"]["change"]["add_success"].format(user)
        msg_map = {
            PermChangeResult.ADDED:         add_success,
            PermChangeResult.UPDATED:       add_success,
            PermChangeResult.REMOVED:       ctx.text.response_msg["permission"]["change"]["remove_success"].format(user),
            PermChangeResult.NOT_FOUND:     ctx.text.response_msg["permission"]["change"]["already_removed"],
            PermChangeResult.INVALID_LEVEL: ctx.text.response_msg["permission"]["change"]["invalid_level"].format(
                max(ctx.text.command_permission.values()), level
            ),
        }
        embed.add_field(name="", value=msg_map[result], inline=False)
        await interaction.response.send_message(embed=embed)
        if result in (PermChangeResult.ADDED, PermChangeResult.UPDATED, PermChangeResult.REMOVED):
            await rewrite_config()
            admin_logger.info(f"permission change {result.name} -> {user}")
        else:
            admin_logger.error(f"permission change {result.name} -> {user} (level {level})")

    @command_group_permission.command(
        name="view",
        description=ctx.text.command_desc[ctx.text.lang]["permission"]["view"],
    )
    @app_commands.describe(**ctx.text.command_args_desc[ctx.text.lang]["permission"]["view"])
    async def view_cmd(interaction: discord.Interaction, user: discord.User, detail: bool) -> None:
        await print_user(permission_logger, interaction.user)
        if await user_permission(interaction.user) < ctx.text.command_permission["permission view"]:
            await not_enough_permission(interaction, permission_logger)
            return
        embed     = ModifiedEmbeds.DefaultEmbed(title=f"/permission view {user} {detail}")
        max_len   = max(len(k) for k in ctx.text.command_permission)
        advanced  = "☑" if ctx.enable_advanced_features else "☐"
        admin_mark = (
            f"☑({max(ctx.text.command_permission.values())})"
            if await is_administrator(user) else "☐"
        )
        perm_level = await user_permission(user)
        if detail:
            can_use    = {
                k: ("☑" if ctx.text.command_permission[k] <= perm_level else "☐")
                   + f"({ctx.text.command_permission[k]})"
                for k in ctx.text.command_permission
            }
            detail_str = "\n".join(f"{k.ljust(max_len)} : {v}" for k, v in can_use.items())
            embed.add_field(
                name="",
                value=ctx.text.response_msg["permission"]["success"].format(
                    user, advanced, admin_mark, perm_level
                ) + "\n```\n" + detail_str + "\n```",
                inline=False,
            )
        else:
            embed.add_field(
                name="",
                value=ctx.text.response_msg["permission"]["success"].format(
                    user, advanced, admin_mark, perm_level
                ),
                inline=False,
            )
        await interaction.response.send_message(embed=embed)
        permission_logger.info(f"send permission info : {user.id}({user})")

    tree.add_command(command_group_permission)

    @tree.command(name="lang", description=ctx.text.command_desc[ctx.text.lang]["lang"])
    @app_commands.describe(**ctx.text.command_args_desc[ctx.text.lang]["lang"])
    @app_commands.choices(language=[
        app_commands.Choice(name=lang, value=lang) for lang in available_languages()
    ])
    async def lang_cmd(interaction: discord.Interaction, language: str) -> None:
        await print_user(lang_logger, interaction.user)
        if await user_permission(interaction.user) < ctx.text.command_permission["lang"]:
            await not_enough_permission(interaction, lang_logger)
            return
        await _change_lang(language, get_text_dat)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/lang {language}")
        embed.add_field(
            name="",
            value=ctx.text.response_msg["lang"]["success"].format(language)
            + "\n" + ctx.text.response_msg["lang"]["restart_note"],
        )
        await interaction.response.send_message(embed=embed)
        lang_logger.info(f"change lang to {ctx.text.lang}")
