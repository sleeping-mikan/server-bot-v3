"""
routes/backups.py — バックアップ管理ルート

  POST /flask_backup_server
  GET  /api/backups/list
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from core.path_utils import is_important_bot_file, would_destroy_important_files
from core.state import ctx
from web.auth import require_permission

bp = Blueprint("backups", __name__)
_logger = logging.getLogger("web.backups")


@bp.route("/flask_backup_server", methods=["POST"])
def backup_server():
    err = require_permission("backup create")
    if err:
        return err
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
    err = require_permission("backup apply")
    if err:
        return err
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
    # apply_backup_sync は dest を rmtree してから展開するため、dest 自体が保護対象
    # (.config / .token / mikanassets 等) を内包している場合は丸ごと消えてしまう。
    # is_important_bot_file だけでは dest == server_path のようなケース (保護対象の
    # 親ディレクトリ) を検出できないため would_destroy_important_files も併用する。
    if not ctx.enable_advanced_features and (
        is_important_bot_file(dest) or would_destroy_important_files(dest)
    ):
        return jsonify({"error": "invalid destination path"}), 400
    apply_backup_sync(backup_name, str(dest))
    _logger.info(f"applied backup: {backup_name} -> {dest}")
    return jsonify({"ok": True, "message": f"Applied '{backup_name}' to '{dest_rel}'"})


@bp.route("/api/backups/list")
def backups_list():
    # 一覧表示のみなので、破壊的な apply より緩い create と同じ権限にする
    err = require_permission("backup create")
    if err:
        return err
    bp_path = ctx.backup_path
    if not bp_path.is_dir():
        return jsonify({"backups": []})
    backups = sorted([e.name for e in bp_path.iterdir()], reverse=True)
    return jsonify({"backups": backups})
