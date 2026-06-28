"""
routes/backups.py — バックアップ管理ルート

  POST /flask_backup_server
  GET  /api/backups/list
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from core.state import ctx
from web.auth import is_valid_session, unauth

bp = Blueprint("backups", __name__)
_logger = logging.getLogger("web.backups")


@bp.route("/flask_backup_server", methods=["POST"])
def backup_server():
    if not is_valid_session():
        return unauth()
    from server.backup import create_backup_sync
    data = request.get_json(silent=True, force=True) or {}
    world_name = data.get("fileName") or request.form.get("fileName", "world")
    if "\\" in world_name or "/" in world_name:
        return jsonify({"ok": False, "message": ctx.text.response_msg["backup"]["not_allowed_path"]})
    from_path = ctx.server_path / world_name
    if ctx.server_process.is_stopped():
        if from_path.exists():
            _logger.info(f"backup: {from_path}")
            dst = create_backup_sync(str(from_path))
            _logger.info(f"backup done: {dst}")
            return jsonify({"ok": True, "message": f"Backup created: {dst}"})
        return jsonify({"ok": False, "message": ctx.text.response_msg["backup"]["data_not_found"]})
    return jsonify({"ok": False, "message": ctx.text.response_msg["other"]["is_running"]})


@bp.route("/api/backups/apply", methods=["POST"])
def backups_apply():
    if not is_valid_session():
        return unauth()
    from server.backup import apply_backup_sync
    from web.utils import resolve_server_path
    data = request.get_json(silent=True) or {}
    backup_name = data.get("name", "")
    dest_rel = data.get("dest", "")
    if not backup_name or not dest_rel:
        return jsonify({"error": "name and dest required"}), 400
    if "/" in backup_name or "\\" in backup_name:
        return jsonify({"error": "invalid backup name"}), 400
    backup_path = ctx.backup_path / backup_name
    if not backup_path.exists():
        return jsonify({"error": "backup not found"}), 404
    if ctx.server_process.is_running():
        return jsonify({"ok": False, "message": ctx.text.response_msg["other"]["is_running"]})
    dest = resolve_server_path(dest_rel)
    if dest is None:
        return jsonify({"error": "invalid destination path"}), 400
    apply_backup_sync(backup_name, str(dest))
    _logger.info(f"applied backup: {backup_name} -> {dest}")
    return jsonify({"ok": True, "message": f"Applied '{backup_name}' to '{dest_rel}'"})


@bp.route("/api/backups/list")
def backups_list():
    if not is_valid_session():
        return unauth()
    bp_path = ctx.backup_path
    if not bp_path.is_dir():
        return jsonify({"backups": []})
    backups = sorted([e.name for e in bp_path.iterdir()], reverse=True)
    return jsonify({"backups": backups})
