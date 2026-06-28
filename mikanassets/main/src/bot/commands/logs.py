"""
commands/logs.py — /logs コマンド

実装 (Implementation)
---------------------
_resolve_log_path(filename, server_path)
  → (path: str | None, error_key: str | None)
  ファイル名を検証してフルパスを返す。不正な場合は error_key を返す。
_trim_to_discord_limit(lines)
  → list[str]
  2000 文字を超えないよう末尾から詰める。
表示 (Presentation)
--------------------
setup() 内の @tree.command ハンドラ
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import discord
from discord import app_commands

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from core.log_setup import LogManager
from core.state import ctx
from bot.utils import not_enough_permission, print_user, user_permission


# ── 実装 (Implementation) ────────────────────────────────────────────────────

def _resolve_log_path(filename: str, server_logs_dir: Path) -> tuple[str | None, str | None]:
    """
    戻り値: (full_path, error_key)
    正常: (path, None)
    エラー: (None, error_key)   error_key は RESPONSE_MSG["logs"][error_key]
    """
    if any(c in filename for c in "/\\%"):
        return None, "cant_access_other_dir"
    if not filename.endswith(".log"):
        return None, "not_found"
    candidates = [
        server_logs_dir / filename,
        ctx.paths.log_file(filename),
    ]
    for p in candidates:
        if p.exists():
            return str(p), None
    return None, "not_found"


def _trim_to_discord_limit(lines: list[str], limit: int = 1900) -> list[str]:
    result: list[str] = []
    total = 0
    for line in lines:
        total += len(line)
        result.append(line)
        while total > limit and result:
            removed = result.pop(0)
            total -= len(removed)
    return result


# ── 表示 (Presentation) ──────────────────────────────────────────────────────

def setup(server_path: str, log_msg: deque) -> None:
    """
    server_path : サーバーディレクトリのパス
    log_msg     : main.py 側でリアルタイム更新される最新ログのリスト
    """
    log_logger = LogManager.cmd.getChild("logs")
    server_logs_dir = Path(server_path) / "logs"

    async def _autocomplete(interaction: discord.Interaction, current: str):
        current = current.translate(str.maketrans("/\\:", "--_"))
        candidates: list[str] = []
        if server_logs_dir.is_dir():
            candidates += [p.name for p in server_logs_dir.iterdir()]
        candidates += [p.name for p in ctx.paths.logs_dir.iterdir()]
        filtered = [f for f in candidates if current in f and f.endswith(".log")][-25:]
        return [app_commands.Choice(name=f, value=f) for f in filtered]

    @tree.command(name="logs", description=ctx.text.command_desc[ctx.text.lang]["logs"])
    @app_commands.autocomplete(filename=_autocomplete)
    async def logs_cmd(interaction: discord.Interaction, filename: str | None = None) -> None:
        await print_user(log_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/logs {filename}")
        if await user_permission(interaction.user) < ctx.text.command_permission["logs"]:
            await not_enough_permission(interaction, log_logger)
            return
        if filename is None:
            lines = _trim_to_discord_limit(list(log_msg))
            await interaction.response.send_message("```ansi\n" + "\n".join(lines) + "\n```")
            log_logger.info("sended logs -> Server logs")
            return
        path, error_key = _resolve_log_path(filename, server_logs_dir)
        if error_key:
            log_logger.error(f"invalid filename : {filename} ({interaction.user} {interaction.user.id})")
            embed.add_field(name="", value=ctx.text.response_msg["logs"][error_key], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        await interaction.response.send_message(file=discord.File(path))
        log_logger.info(f"sended logs -> {path}")
