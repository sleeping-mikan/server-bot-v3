"""
web/auth.py — トークン・セッション検証ヘルパー

## 権限レベル
これまで Web パネルは「トークンが有効か」しか見ておらず、/tokengen で発行された
トークンは全て同格 (ファイル管理・バックアップ復元・Bot終了まで全操作が可能) だった。

Web専用の固定スケールを新設するのではなく、Discord側で既に使っている
ctx.text.command_permission (= config の discord_commands.permission.commands_level)
のキーをそのまま各Webルートの必要レベルとして参照する。こうすることで、
config を書き換えれば Discord コマンドと Web ルートの必要レベルが常に同じ値を
指したままになる (二重管理・食い違いを防ぐ)。
"""

from __future__ import annotations

from datetime import datetime

from flask import jsonify, session, url_for

from core.state import ctx


def _load_tokens() -> dict[str, int]:
    """有効なトークン -> 権限レベル のマップを返す。"""
    now = datetime.now()
    tokens: dict[str, int] = {}
    for t in ctx.web_tokens:
        if datetime.strptime(t["deadline"], "%Y-%m-%d %H:%M:%S") > now:
            # level を持たない旧トークンは最低権限 (0) にフォールバックする
            tokens[t["token"]] = t.get("level", 0)
    return tokens


def is_valid_token(token: str) -> bool:
    return token in _load_tokens()


def token_level(token: str) -> int:
    return _load_tokens().get(token, 0)


def is_valid_session() -> bool:
    token = session.get("token")
    return token is not None and is_valid_token(token)


def session_level() -> int:
    token = session.get("token")
    return token_level(token) if token else 0


def unauth():
    """認証エラー時のレスポンスを返す。"""
    return jsonify({"error": "unauthorized", "redirect": url_for("main.logout")}), 401


def require_permission(command_key: str):
    """セッションが有効かつ、ctx.text.command_permission[command_key] 以上かを確認する。

    command_key には bot/commands/__init__.py の INITIAL_COMMAND_PERMISSION
    (= config の discord_commands.permission.commands_level) のキーのうち、
    対応する Discord コマンドと同じものを渡す。これにより Web だけの
    別スケールを持たず、config 1箇所の変更が Discord/Web 両方に反映される。

    問題なければ None、問題があればそのまま return できるエラーレスポンスを返す。
    使い方: `err = require_permission("cmd stdin rm")\n if err: return err`
    """
    if not is_valid_session():
        return unauth()
    required = ctx.text.command_permission[command_key]
    if session_level() < required:
        return jsonify({"error": "insufficient permission"}), 403
    return None
