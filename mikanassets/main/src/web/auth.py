"""
web/auth.py — トークン・セッション検証ヘルパー
"""

from __future__ import annotations

from datetime import datetime

from flask import jsonify, session, url_for

from core.state import ctx


def _load_tokens() -> set:
    tokens: set = set()
    now = datetime.now()
    for t in ctx.web_tokens:
        if datetime.strptime(t["deadline"], "%Y-%m-%d %H:%M:%S") > now:
            tokens.add(t["token"])
    return tokens


def is_valid_token(token: str) -> bool:
    return token in _load_tokens()


def is_valid_session() -> bool:
    token = session.get("token")
    return token is not None and is_valid_token(token)


def unauth():
    """認証エラー時のレスポンスを返す。"""
    return jsonify({"error": "unauthorized", "redirect": url_for("main.logout")}), 401
