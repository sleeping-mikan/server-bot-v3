"""
routes/files.py — ファイル管理ルート

  GET  /api/files/list?path=
  POST /api/files/mkdir
  POST /api/files/rmdir
  POST /api/files/rm
  POST /api/files/mv
  GET  /api/files/download?path=
  POST /api/files/upload
  POST /api/files/wget
"""

from __future__ import annotations

import io
import zipfile

import requests as _requests
from flask import Blueprint, jsonify, request, send_file

from core.path_utils import is_entry_file, is_important_bot_file
from core.state import ctx
from core.zip_utils import safe_unzip
from web.auth import require_permission
from web.utils import resolve_server_path

bp = Blueprint("files", __name__)


def _protected(path) -> bool:
    """path が保護対象 (entry file / sys_files) で、advanced機能が無効かを返す。

    core.path_utils のガードは元々 Discord コマンド (bot/commands/cmd.py) 向けに
    書かれていたが、Web の file manager ルートはこれまで is_path_within_scope
    (スコープ内かどうか) しか見ておらず、.config や mikanassets/data/tokens.json
    のような重要ファイルを rm / mv / download できてしまっていた。
    """
    if ctx.enable_advanced_features:
        return False
    return is_entry_file(path) or is_important_bot_file(path)


@bp.route("/api/files/list")
def files_list():
    err = require_permission("cmd stdin ls")
    if err:
        return err
    rel = request.args.get("path", "")
    path = resolve_server_path(rel) if rel else ctx.server_path
    if path is None or not path.exists() or not path.is_dir():
        return jsonify({"error": "not a directory"}), 400
    entries = []
    for e in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        size = 0
        if e.is_file():
            try:
                size = e.stat().st_size
            except OSError:
                pass
        entries.append({
            "name": e.name,
            "type": "dir" if e.is_dir() else ("link" if e.is_symlink() else "file"),
            "size": size,
        })
    return jsonify({"entries": entries, "path": rel})


@bp.route("/api/files/mkdir", methods=["POST"])
def files_mkdir():
    err = require_permission("cmd stdin mkdir")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    path = resolve_server_path(data.get("path", ""))
    if path is None:
        return jsonify({"error": "invalid path"}), 400
    if path.exists():
        return jsonify({"error": "already exists"}), 400
    path.mkdir(parents=True)
    return jsonify({"ok": True})


@bp.route("/api/files/rmdir", methods=["POST"])
def files_rmdir():
    err = require_permission("cmd stdin rmdir")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    path = resolve_server_path(data.get("path", ""))
    if path is None or not path.exists() or not path.is_dir():
        return jsonify({"error": "not a directory"}), 400
    if _protected(path):
        return jsonify({"error": "permission denied"}), 403
    from shutil import rmtree
    rmtree(path)
    return jsonify({"ok": True})


@bp.route("/api/files/rm", methods=["POST"])
def files_rm():
    err = require_permission("cmd stdin rm")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    path = resolve_server_path(data.get("path", ""))
    if path is None or not path.exists():
        return jsonify({"error": "not found"}), 404
    if not path.is_file():
        return jsonify({"error": "not a file"}), 400
    if _protected(path):
        return jsonify({"error": "permission denied"}), 403
    path.unlink()
    return jsonify({"ok": True})


@bp.route("/api/files/mv", methods=["POST"])
def files_mv():
    err = require_permission("cmd stdin mv")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    src = resolve_server_path(data.get("src", ""))
    dst = resolve_server_path(data.get("dst", ""))
    if src is None or dst is None:
        return jsonify({"error": "invalid path"}), 400
    if not src.exists():
        return jsonify({"error": "source not found"}), 404
    if _protected(src) or _protected(dst):
        return jsonify({"error": "permission denied"}), 403
    from shutil import move as _move
    _move(str(src), str(dst))
    return jsonify({"ok": True})


@bp.route("/api/files/download")
def files_download():
    # ダウンロードはDiscordの /cmd stdin send-discord (任意ファイルをリンクとして
    # 外部に取り出す操作) と実質同じ権限を要求する
    err = require_permission("cmd stdin send-discord")
    if err:
        return err
    rel = request.args.get("path", "")
    path = resolve_server_path(rel) if rel else None
    if path is None or not path.exists():
        return jsonify({"error": "not found"}), 404
    if _protected(path):
        return jsonify({"error": "access denied"}), 403
    if path.is_file():
        return send_file(path, as_attachment=True, download_name=path.name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    zf.write(f, f.relative_to(path))
                except OSError:
                    pass
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name=f"{path.name}.zip")


@bp.route("/api/files/upload", methods=["POST"])
def files_upload():
    # 新規ファイル作成はDiscordの /cmd stdin mk (attachmentで内容を書き込める) と同じ操作
    err = require_permission("cmd stdin mk")
    if err:
        return err
    file = request.files.get("file")
    rel_dir = request.form.get("path", "")
    if file is None or not file.filename:
        return jsonify({"error": "no file"}), 400
    target = f"{rel_dir}/{file.filename}" if rel_dir else file.filename
    path = resolve_server_path(target)
    if path is None:
        return jsonify({"error": "invalid path"}), 400
    if path.exists():
        return jsonify({"error": "file already exists"}), 400
    if _protected(path):
        return jsonify({"error": "permission denied"}), 403
    path.parent.mkdir(parents=True, exist_ok=True)
    file.save(path)
    return jsonify({"ok": True, "name": path.name})


@bp.route("/api/files/unzip", methods=["POST"])
def files_unzip():
    err = require_permission("cmd stdin unzip")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    rel = data.get("path", "")
    if not rel:
        return jsonify({"error": "path required"}), 400
    path = resolve_server_path(rel)
    if path is None or not path.exists():
        return jsonify({"error": "not found"}), 404
    if path.suffix.lower() != ".zip":
        return jsonify({"error": "not a zip file"}), 400
    try:
        count = safe_unzip(path, path.parent)
    except ValueError as e:
        return jsonify({"error": f"unsafe path in zip: {e}"}), 400
    except zipfile.BadZipFile:
        return jsonify({"error": "invalid or corrupt zip file"}), 400
    return jsonify({"ok": True, "count": count})


@bp.route("/api/files/wget", methods=["POST"])
def files_wget():
    err = require_permission("cmd stdin wget")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    rel = data.get("path", "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400
    if rel:
        path = resolve_server_path(rel)
    else:
        filename = url.split("/")[-1].split("?")[0] or "download"
        path = resolve_server_path(filename)
    if path is None:
        return jsonify({"error": "invalid path"}), 400
    if path.exists():
        return jsonify({"error": "file already exists"}), 400
    if _protected(path):
        return jsonify({"error": "permission denied"}), 403
    try:
        resp = _requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True, "name": path.name})
