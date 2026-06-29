"""
routes/server.py — サーバー起動・停止ルート

  POST /flask_start_server
  POST /api/stop_server
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from core.state import ctx
from web.auth import is_valid_session, unauth

bp = Blueprint("server", __name__)


@bp.route("/flask_start_server", methods=["POST"])
def start_server():
    if not is_valid_session():
        return unauth()
    from server.control import StartResult, start_server as _start
    result = _start(ctx.server_logger)
    if result == StartResult.ALREADY_RUNNING:
        return jsonify({"ok": False, "message": ctx.text.response_msg["other"]["is_running"]})
    return jsonify({"ok": True, "message": ctx.text.response_msg["start"]["success"]})


@bp.route("/api/stop_server", methods=["POST"])
def stop_server():
    if not is_valid_session():
        return unauth()
    from server.control import StopResult, stop_server as _stop
    result = _stop()
    if result == StopResult.ALREADY_STOPPED:
        return jsonify({"ok": False, "message": "Server is already stopped"})
    return jsonify({"ok": True, "message": "Stop command sent"})


@bp.route("/api/exit", methods=["POST"])
def exit_bot():
    if not is_valid_session():
        return unauth()
    if ctx.server_process.is_running():
        return jsonify({"ok": False, "message": ctx.text.response_msg["other"]["is_running"]})
    import asyncio
    from bot.client import client, shutdown
    asyncio.run_coroutine_threadsafe(shutdown(), client.loop)
    return jsonify({"ok": True, "message": "Bot is shutting down…"})
