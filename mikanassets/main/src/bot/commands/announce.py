"""bot/commands/announce.py — /announce embed Discord command handler."""

from __future__ import annotations

from collections import deque

import discord
from discord import app_commands

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from core.log_setup import LogManager
from core.state import ctx
from bot.utils import not_enough_permission, print_user, user_permission


def _parse_mimd(text: str) -> tuple[deque, dict]:
    first_title = False
    fields: deque[dict] = deque([{"name": "", "value": ""}])
    meta = {"title": ""}
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            fields.append({"name": stripped[1:].strip(), "value": ""})
        elif stripped.startswith("|title|") and not first_title:
            meta["title"] = stripped[7:].strip()
            first_title = True
        else:
            fields[-1]["value"] += line + "\n"
    for f in fields:
        f["value"] = f["value"].rstrip("\n")
    return fields, meta


def setup() -> None:
    announce_logger = LogManager.cmd.getChild("announce")
    command_group_announce = app_commands.Group(name="announce", description="send message to discord")

    @command_group_announce.command(
        name="embed",
        description=ctx.text.command_desc[ctx.text.lang]["announce"]["embed"],
    )
    @app_commands.describe(**ctx.text.command_args_desc[ctx.text.lang]["announce"]["embed"])
    async def announce_embed_cmd(
        interaction: discord.Interaction,
        file:        discord.Attachment | None = None,
        txt:         str                       = "",
    ) -> None:
        await print_user(announce_logger, interaction.user)
        return_embed = ModifiedEmbeds.DefaultEmbed(title=f"/embed {file.filename if file else ''} {txt}")
        embed        = ModifiedEmbeds.DefaultEmbed(title="")
        if await user_permission(interaction.user) < ctx.text.command_permission["announce embed"]:
            await not_enough_permission(interaction, announce_logger)
            return
        if file is not None and txt:
            announce_logger.error("both file and txt specified")
            return_embed.add_field(
                name="",
                value=ctx.text.response_msg["cmd"]["announce"]["embed"]["exist_file_and_txt"],
                inline=False,
            )
            await interaction.response.send_message(embed=return_embed)
            return
        if file is not None:
            try:
                txt = (await file.read()).decode("utf-8")
            except Exception as e:
                announce_logger.error(f"decode error : {file.filename} ({e})")
                return_embed.add_field(
                    name="",
                    value=ctx.text.response_msg["announce"]["embed"]["decode_error"],
                    inline=False,
                )
                await interaction.response.send_message(embed=return_embed)
                return
        if txt:
            txt = txt.replace("\\n", "\n")
            return_embed.add_field(
                name="",
                value=ctx.text.response_msg["announce"]["embed"]["replace_slash_n"],
                inline=False,
            )
        if not txt:
            announce_logger.error("empty message")
            return_embed.add_field(
                name="",
                value=ctx.text.response_msg["announce"]["embed"]["empty"],
                inline=False,
            )
            await interaction.response.send_message(embed=return_embed)
            return
        fields, meta = _parse_mimd(txt)
        embed.title  = meta["title"]
        for item in fields:
            if item["name"] or item["value"]:
                embed.add_field(name=item["name"], value=item["value"], inline=False)
        return_embed.add_field(
            name="",
            value=ctx.text.response_msg["announce"]["embed"]["success"],
            inline=False,
        )
        await interaction.response.send_message(embed=return_embed, ephemeral=True)
        await interaction.channel.send(embed=embed)
        announce_logger.info("embed sent")

    tree.add_command(command_group_announce)
