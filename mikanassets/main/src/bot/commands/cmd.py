"""
commands/cmd.py — /cmd serverin, /cmd stdin * コマンド

実装 (Implementation)
---------------------
_send_server_cmd(command) → ServeInResult
  サーバーへ stdin コマンドを送信し結果を返す。
ファイル操作コマンド (ls/mk/rm/mkdir/rmdir/mv/send-discord/wget) は
パス検証を core.path_utils.is_path_within_scope / is_important_bot_file に委譲し、
実際のファイル操作を標準 Python ライブラリで実装する。

表示 (Presentation)
--------------------
setup() 内の @tree.command ハンドラが Discord スラッシュコマンドを登録する。
"""

from __future__ import annotations

import asyncio
import io
import os
from enum import Enum, auto
from shutil import move as shutil_move, rmtree

import aiohttp
import discord
from discord import app_commands

from bot.client import tree
from web.download_server import SendDiscordSelfServer
from bot.embeds import ModifiedEmbeds
from core.log_setup import LogManager
from core.path_utils import is_important_bot_file, is_path_within_scope
from core.state import ctx
from bot.utils import (
    is_administrator,
    is_running_server,
    is_stopped_server,
    not_enough_permission,
    print_user,
    user_permission,
)


# ── 実装 (Implementation) ────────────────────────────────────────────────────

class ServeInResult(Enum):
    SUCCESS = auto()
    NOT_RUNNING = auto()
    DISALLOWED_CMD = auto()
    ENCODE_ERROR = auto()


def _send_server_cmd(command: str) -> ServeInResult:
    if ctx.server_process.is_stopped():
        return ServeInResult.NOT_RUNNING
    if command.split()[0] not in ctx.allow_cmd:
        return ServeInResult.DISALLOWED_CMD
    try:
        ctx.server_process.write(command)
    except UnicodeEncodeError:
        return ServeInResult.ENCODE_ERROR
    return ServeInResult.SUCCESS


def _abs_server_path(rel: str) -> str:
    return os.path.abspath(os.path.join(ctx.server_path, rel))


# ── 表示 (Presentation) ──────────────────────────────────────────────────────

def setup() -> None:  # noqa: C901 (多数のサブコマンドのため長い)
    cmd_logger = LogManager.cmd.getChild("file")
    stdin_logger = cmd_logger.getChild("stdin")
    serverin_logger = cmd_logger.getChild("serverin")
    ls_logger = stdin_logger.getChild("ls")
    mk_logger = stdin_logger.getChild("mk")
    rm_logger = stdin_logger.getChild("rm")
    mkdir_logger = stdin_logger.getChild("mkdir")
    rmdir_logger = stdin_logger.getChild("rmdir")
    mv_logger = stdin_logger.getChild("mv")
    send_discord_logger = stdin_logger.getChild("send-discord")
    wget_logger = stdin_logger.getChild("wget")

    command_group_cmd = app_commands.Group(name="cmd", description="cmd group")
    command_group_cmd_stdin = app_commands.Group(name="stdin", description="stdin group")
    command_group_cmd.add_command(command_group_cmd_stdin)

    # /cmd serverin ───────────────────────────────────────────────────────────

    @command_group_cmd.command(name="serverin", description=ctx.text.command_desc[ctx.text.lang]["cmd"]["serverin"])
    async def serverin_cmd(interaction: discord.Interaction, command: str) -> None:
        await print_user(serverin_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/cmd serverin {command}")
        if await user_permission(interaction.user) < ctx.text.command_permission["cmd serverin"]:
            await not_enough_permission(interaction, serverin_logger)
            return
        result = _send_server_cmd(command)
        if result == ServeInResult.NOT_RUNNING:
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_not_running"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if result == ServeInResult.DISALLOWED_CMD:
            serverin_logger.error(f"unknown command : {command}")
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["serverin"]["skipped_cmd"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if result == ServeInResult.ENCODE_ERROR:
            serverin_logger.error(f"UnicodeEncodeError({command})")
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["serverin"]["unicode_encode_error"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        serverin_logger.info(f"run command : {command}")
        ctx.is_back_discord = True
        while True:
            if len(ctx.cmd_logs) == 0:
                await asyncio.sleep(0.1)
                continue
            embed.add_field(name="", value=ctx.cmd_logs.popleft(), inline=False)
            await interaction.response.send_message(embed=embed)
            break

    # /cmd stdin ls ───────────────────────────────────────────────────────────

    @command_group_cmd_stdin.command(name="ls", description=ctx.text.command_desc[ctx.text.lang]["cmd"]["stdin"]["ls"])
    async def ls_cmd(interaction: discord.Interaction, file_path: str) -> None:
        await print_user(ls_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/cmd stdin ls {file_path}")
        if await user_permission(interaction.user) < ctx.text.command_permission["cmd stdin ls"]:
            await not_enough_permission(interaction, ls_logger)
            return
        path = _abs_server_path(file_path)
        if not is_path_within_scope(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["invalid_path"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not os.path.exists(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["ls"]["file_not_found"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not os.path.isdir(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["ls"]["not_directory"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        files = os.listdir(path)
        colorized = []
        for f in files:
            full = os.path.join(path, f)
            if os.path.isdir(full):
                colorized.append(f"\033[34m{f}\033[0m")
            elif os.path.islink(full):
                colorized.append(f"\033[35m{f}\033[0m")
            else:
                colorized.append(f"\033[32m{f}\033[0m")
        formatted = "\n".join(colorized)
        ls_logger.info(f"list directory -> {path}")
        if len(formatted) > 900:
            with io.StringIO() as buf:
                buf.write("\n".join(files))
                buf.seek(0)
                embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["ls"]["to_long"].format(path), inline=False)
                await interaction.response.send_message(embed=embed, file=discord.File(buf, filename="directory_list.txt"))
        else:
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["ls"]["success"].format(path, formatted), inline=False)
            await interaction.response.send_message(embed=embed)

    # /cmd stdin mk ───────────────────────────────────────────────────────────

    @command_group_cmd_stdin.command(name="mk", description=ctx.text.command_desc[ctx.text.lang]["cmd"]["stdin"]["mk"])
    async def mk_cmd(interaction: discord.Interaction, file_path: str, file: discord.Attachment | None = None) -> None:
        await print_user(mk_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/cmd stdin mk {file_path}")
        if await user_permission(interaction.user) < ctx.text.command_permission["cmd stdin mk"]:
            await not_enough_permission(interaction, mk_logger)
            return
        if is_running_server(mk_logger):
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_running"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        path = _abs_server_path(file_path)
        if not is_path_within_scope(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["invalid_path"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if os.path.islink(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["mk"]["is_link"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if os.path.isdir(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["mk"]["is_directory"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if (not await is_administrator(interaction.user) or not ctx.enable_advanced_features) and await is_important_bot_file(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["permission_denied"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        with open(path, "w"):
            pass
        if file is not None:
            await file.save(path)
        mk_logger.info(f"create file -> {path}")
        embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["mk"]["success"].format(path), inline=False)
        await interaction.response.send_message(embed=embed)

    # /cmd stdin rm ───────────────────────────────────────────────────────────

    @command_group_cmd_stdin.command(name="rm", description=ctx.text.command_desc[ctx.text.lang]["cmd"]["stdin"]["rm"])
    async def rm_cmd(interaction: discord.Interaction, file_path: str) -> None:
        await print_user(rm_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/cmd stdin rm {file_path}")
        if await user_permission(interaction.user) < ctx.text.command_permission["cmd stdin rm"]:
            await not_enough_permission(interaction, rm_logger)
            return
        if is_running_server(rm_logger):
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_running"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        path = _abs_server_path(file_path)
        if not is_path_within_scope(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["invalid_path"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not os.path.exists(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["rm"]["file_not_found"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not os.path.isfile(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["not_file"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if (not await is_administrator(interaction.user) or not ctx.enable_advanced_features) and await is_important_bot_file(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["permission_denied"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        os.remove(path)
        rm_logger.info(f"remove file -> {path}")
        embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["rm"]["success"].format(path), inline=False)
        await interaction.response.send_message(embed=embed)

    # /cmd stdin mkdir ────────────────────────────────────────────────────────

    @command_group_cmd_stdin.command(name="mkdir", description=ctx.text.command_desc[ctx.text.lang]["cmd"]["stdin"]["mkdir"])
    async def mkdir_cmd(interaction: discord.Interaction, dir_path: str) -> None:
        await print_user(mkdir_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/cmd stdin mkdir {dir_path}")
        if await user_permission(interaction.user) < ctx.text.command_permission["cmd stdin mkdir"]:
            await not_enough_permission(interaction, mkdir_logger)
            return
        path = _abs_server_path(dir_path)
        if not is_path_within_scope(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["invalid_path"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if os.path.exists(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["mkdir"]["exists"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        os.makedirs(path)
        mkdir_logger.info(f"create directory -> {path}")
        embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["mkdir"]["success"].format(path), inline=False)
        await interaction.response.send_message(embed=embed)

    # /cmd stdin rmdir ────────────────────────────────────────────────────────

    @command_group_cmd_stdin.command(name="rmdir", description=ctx.text.command_desc[ctx.text.lang]["cmd"]["stdin"]["rmdir"])
    async def rmdir_cmd(interaction: discord.Interaction, dir_path: str) -> None:
        await print_user(rmdir_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/cmd stdin rmdir {dir_path}")
        if await user_permission(interaction.user) < ctx.text.command_permission["cmd stdin rmdir"]:
            await not_enough_permission(interaction, rmdir_logger)
            return
        if is_running_server(rmdir_logger):
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_running"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        path = _abs_server_path(dir_path)
        if not is_path_within_scope(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["invalid_path"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not os.path.exists(path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["rmdir"]["not_exists"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if await is_important_bot_file(path) and (not ctx.enable_advanced_features or not await is_administrator(interaction.user)):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["permission_denied"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        rmtree(path)
        rmdir_logger.info(f"remove directory -> {path}")
        embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["rmdir"]["success"].format(path), inline=False)
        await interaction.response.send_message(embed=embed)

    # /cmd stdin mv ───────────────────────────────────────────────────────────

    @command_group_cmd_stdin.command(name="mv", description=ctx.text.command_desc[ctx.text.lang]["cmd"]["stdin"]["mv"])
    async def mv_cmd(interaction: discord.Interaction, path: str, dest: str) -> None:
        await print_user(mv_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/cmd stdin mv {path} {dest}")
        if await user_permission(interaction.user) < ctx.text.command_permission["cmd stdin mv"]:
            await not_enough_permission(interaction, mv_logger)
            return
        if is_running_server(mv_logger):
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_running"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        abs_path = _abs_server_path(path)
        abs_dest = _abs_server_path(dest)
        if not is_path_within_scope(abs_path) or not is_path_within_scope(abs_dest):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["invalid_path"].format(abs_path, abs_dest), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not os.path.exists(abs_path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["mv"]["file_not_found"].format(abs_path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not os.path.isfile(abs_path) and not os.path.isdir(abs_path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["not_file_or_directory"].format(abs_path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not os.path.isdir(os.path.dirname(abs_dest)):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["not_directory"].format(abs_dest), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if (not await is_administrator(interaction.user) or not ctx.enable_advanced_features) and \
                (await is_important_bot_file(abs_path) or await is_important_bot_file(abs_dest)):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["permission_denied"].format(abs_path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        shutil_move(abs_path, abs_dest)
        mv_logger.info(f"move file -> {abs_path} -> {abs_dest}")
        embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["mv"]["success"].format(abs_path, abs_dest), inline=False)
        await interaction.response.send_message(embed=embed)

    # /cmd stdin send-discord ─────────────────────────────────────────────────

    @command_group_cmd_stdin.command(name="send-discord", description=ctx.text.command_desc[ctx.text.lang]["cmd"]["stdin"]["send-discord"])
    async def send_discord_cmd(interaction: discord.Interaction, path: str) -> None:
        await print_user(send_discord_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/cmd stdin send-discord {path}")
        if await user_permission(interaction.user) < ctx.text.command_permission["cmd stdin send-discord"]:
            await not_enough_permission(interaction, send_discord_logger)
            return
        file_path = _abs_server_path(path)
        if not os.path.exists(file_path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["send-discord"]["file_not_found"].format(file_path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not is_path_within_scope(file_path) or os.path.basename(file_path) == ".token":
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["invalid_path"].format(file_path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        ok, result = await SendDiscordSelfServer.register_download(file_path)
        if ok:
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["send-discord"]["send_myserver_link"].format(interaction.user.id, result, file_path), inline=False)
        else:
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["send-discord"]["send_capacity_error"].format(interaction.user.id, result[1], result[2]), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /cmd stdin wget ─────────────────────────────────────────────────────────

    @command_group_cmd_stdin.command(name="wget", description=ctx.text.command_desc[ctx.text.lang]["cmd"]["stdin"]["wget"])
    async def wget_cmd(interaction: discord.Interaction, url: str, path: str = "mi_dl_file.tmp") -> None:
        await print_user(wget_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/cmd stdin wget {url} {path}")
        if await user_permission(interaction.user) < ctx.text.command_permission["cmd stdin wget"]:
            await not_enough_permission(interaction, wget_logger)
            return
        save_path = _abs_server_path(path)
        if os.path.exists(save_path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["wget"]["already_exists"].format(path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if not is_path_within_scope(save_path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["invalid_path"].format(save_path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if (not await is_administrator(interaction.user) or not ctx.enable_advanced_features) and await is_important_bot_file(save_path):
            embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["permission_denied"].format(save_path), inline=False)
            await interaction.response.send_message(embed=embed)
            return
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["wget"]["download_failed"].format(url), inline=False)
                        await interaction.response.send_message(embed=embed)
                        return
                    with open(save_path, "wb") as f:
                        f.write(await response.read())
            except Exception as e:
                embed.add_field(name="", value=f"invalid url -> ({e})", inline=False)
                await interaction.response.send_message(embed=embed)
                return
        wget_logger.info(f"download success -> {url} to {save_path}")
        embed.add_field(name="", value=ctx.text.response_msg["cmd"]["stdin"]["wget"]["download_success"].format(url, save_path), inline=False)
        await interaction.response.send_message(embed=embed)

    tree.add_command(command_group_cmd)
