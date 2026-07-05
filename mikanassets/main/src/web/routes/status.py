"""
routes/status.py — システムステータス・IP ルート

  GET /api/status
  GET /api/ip
"""

from __future__ import annotations

import os

import psutil
from flask import Blueprint, jsonify

from core.state import ctx
from web.auth import require_permission

bp = Blueprint("status", __name__)


@bp.route("/api/status")
def status():
    err = require_permission("status")
    if err:
        return err
    MB = 1024 ** 2
    server_online = ctx.server_process.poll_or_kill()
    bot_mem_mb = psutil.Process(os.getpid()).memory_info().rss / MB
    server_mem_mb = 0.0
    raw = ctx.server_process.raw()
    if raw is not None:
        try:
            server_mem_mb = psutil.Process(raw.pid).memory_info().rss / MB
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    vm = psutil.virtual_memory()
    return jsonify({
        "server_online": server_online,
        "bot_online": True,
        "cpu_percent": psutil.cpu_percent(),
        "bot_mem_mb": round(bot_mem_mb, 1),
        "server_mem_mb": round(server_mem_mb, 1),
        "total_mem_mb": round(vm.total / MB, 1),
        "used_mem_mb": round(vm.used / MB, 1),
    })


@bp.route("/api/ip")
def ip():
    err = require_permission("ip")
    if err:
        return err
    from bot.commands.ip import get_display_ip
    display = get_display_ip()
    return jsonify({"ip": display or "N/A"})
