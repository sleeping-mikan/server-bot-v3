"""
routes/logs.py — ログ閲覧ルート

  GET /api/logs/list
  GET /api/logs/get?filename=
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.state import ctx
from web.auth import require_permission

bp = Blueprint("logs", __name__)


@bp.route("/api/logs/list")
def logs_list():
    err = require_permission("logs")
    if err:
        return err
    files: list[str] = []
    server_logs = ctx.server_path / "logs"
    if server_logs.is_dir():
        files += [p.name for p in server_logs.iterdir() if p.name.endswith(".log")]
    if ctx.paths.logs_dir.is_dir():
        files += [p.name for p in ctx.paths.logs_dir.iterdir() if p.name.endswith(".log")]
    return jsonify({"files": sorted(set(files))})


@bp.route("/api/logs/get")
def logs_get():
    err = require_permission("logs")
    if err:
        return err
    filename = request.args.get("filename", "")
    if not filename or any(c in filename for c in "/\\%") or not filename.endswith(".log"):
        return jsonify({"error": "invalid filename"}), 400
    for p in [ctx.server_path / "logs" / filename, ctx.paths.log_file(filename)]:
        if p.exists():
            try:
                return jsonify({"content": p.read_text(encoding="utf-8", errors="replace"),
                                "filename": filename})
            except OSError as e:
                return jsonify({"error": str(e)}), 500
    return jsonify({"error": "not found"}), 404
