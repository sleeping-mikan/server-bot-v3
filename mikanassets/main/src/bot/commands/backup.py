"""
bot/commands/backup.py — /backup create, /backup apply Discord コマンドハンドラ

バックアップの実装は server/backup.py を参照。
"""

from __future__ import annotations

import os

import discord
from discord import app_commands

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from bot.utils import (
    is_important_bot_file,
    is_path_within_scope,
    is_running_server,
    not_enough_permission,
    print_user,
    user_permission,
)
from core.config_loader import normalize_path
from core.log_setup import LogManager
from core.state import ctx
from server.backup import ProgressCallback, apply_backup, create_backup


def _make_progress_callback(
    interaction: discord.Interaction,
    embed:       ModifiedEmbeds.DefaultEmbed,
    src:         str,
    dst:         str,
    max_send:    int = 20,
) -> ProgressCallback:
    """Discord embed を更新する進捗コールバックを生成する。"""
    async def on_progress(copied: int, total: int, copied_bytes: int, total_bytes: int) -> None:
        send_sens = max(1, total // max_send)
        if copied % send_sens != 0 and copied != total:
            return
        bar_width = 30
        ratio  = copied / total if total else 0
        filled = max(0, int(ratio * bar_width) - 1)
        bar    = "=" * filled
        space  = "-" * (bar_width - filled - 1)
        label  = (
            ctx.text.response_msg["backup"]["success"]
            if copied == total
            else ctx.text.response_msg["backup"]["now_backup"]
        )
        embed.clear_fields()
        embed.add_field(
            name=label,
            value=(
                f"copy {src} -> {dst}\n"
                f"```{bar}☆{space}\n"
                f"{copied:5} / {total:5} "
                f"({copied_bytes / 1024 ** 3:.2f} / {total_bytes / 1024 ** 3:.2f} GB)```"
            ),
            inline=False,
        )
        await interaction.edit_original_response(embed=embed)
    return on_progress


def setup() -> None:
    _backup  = LogManager.cmd.getChild("backup")
    _create  = _backup.getChild("create")
    _apply   = _backup.getChild("apply")

    command_group_backup = app_commands.Group(name="backup", description="backup group")

    @command_group_backup.command(
        name="create",
        description=ctx.text.command_desc[ctx.text.lang]["backup"]["create"],
    )
    async def backup_create_cmd(interaction: discord.Interaction, path: str) -> None:
        from_path = normalize_path(os.path.join(ctx.server_path, path))
        await print_user(_create, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/backup create {path}")
        if await user_permission(interaction.user) < ctx.text.command_permission["backup create"]:
            await not_enough_permission(interaction, _create)
            return
        if is_running_server(_create):
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_running"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not is_path_within_scope(from_path) or await is_important_bot_file(from_path):
            _create.error(f"path not allowed : {from_path}")
            embed.add_field(
                name="",
                value=ctx.text.response_msg["backup"]["create"]["path_not_allowed"] + f"\n`{from_path}`",
                inline=False,
            )
            await interaction.response.send_message(embed=embed)
            return
        if not os.path.exists(from_path):
            _create.error(f"data not found : {from_path}")
            embed.add_field(
                name="",
                value=ctx.text.response_msg["backup"]["create"]["data_not_found"] + f"\n`{from_path}`",
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.response.send_message(embed=embed)
        progress = _make_progress_callback(interaction, embed, from_path, ctx.backup_path)
        dst = await create_backup(from_path, on_progress=progress)
        _create.info(f"backup done -> {dst}")

    async def _backup_autocomplete(interaction: discord.Interaction, current: str):
        current = current.translate(str.maketrans("/\\:", "--_"))
        items   = [i for i in os.listdir(ctx.backup_path) if current in i][-25:]
        return [app_commands.Choice(name=i, value=i) for i in items]

    @command_group_backup.command(name="apply", description="apply backup")
    @app_commands.autocomplete(witch=_backup_autocomplete)
    async def backup_apply_cmd(
        interaction: discord.Interaction,
        witch:       str,
        path:        str = "",
    ) -> None:
        await print_user(_apply, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/backup apply {witch} {path}")
        if await user_permission(interaction.user) < ctx.text.command_permission["backup apply"]:
            await not_enough_permission(interaction, _apply)
            return
        if is_running_server(_apply):
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_running"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        src = os.path.join(ctx.backup_path, witch)
        if not os.path.exists(src):
            _apply.error(f"backup not found : {src}")
            embed.add_field(
                name="",
                value=ctx.text.response_msg["backup"]["apply"]["path_not_found"] + f"\n`{src}`",
                inline=False,
            )
            await interaction.response.send_message(embed=embed)
            return
        dest_path = os.path.join(ctx.server_path, path) if path else ctx.server_path
        if not is_path_within_scope(dest_path) or await is_important_bot_file(dest_path):
            _apply.error(f"path not allowed : {dest_path}")
            embed.add_field(
                name="",
                value=ctx.text.response_msg["backup"]["apply"]["path_not_allowed"] + f"\n`{dest_path}`",
                inline=False,
            )
            await interaction.response.send_message(embed=embed)
            return
        _apply.info(f"backup apply started -> {witch} to {dest_path}")
        await interaction.response.send_message(embed=embed)
        progress = _make_progress_callback(interaction, embed, src, dest_path)
        await apply_backup(witch, dest_path, on_progress=progress)
        _apply.info("backup apply done")

    tree.add_command(command_group_backup)
