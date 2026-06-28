"""
web/utils.py — Web 層で共通利用するユーティリティ
"""

from __future__ import annotations

from pathlib import Path

from core.path_utils import is_path_within_scope
from core.state import ctx


def resolve_server_path(rel: str) -> Path | None:
    """サーバールートからの相対パスを解決し、スコープ外なら None を返す。"""
    p = (ctx.server_path / rel).resolve(strict=False)
    return p if is_path_within_scope(p) else None
