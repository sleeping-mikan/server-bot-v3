"""
routes/main.py — 認証・コンソール関連ルート

  GET|POST /           ログイン / ダッシュボード
  GET      /logout
  GET      /get_console_data
  POST     /submit_data
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ansi2html import Ansi2HTMLConverter
from flask import (
    Blueprint,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from core.log_setup import LogManager
from core.state import ctx
from web.auth import is_valid_session, is_valid_token, unauth

bp = Blueprint("main", __name__)


@bp.route("/", methods=["GET", "POST"])
def index():
    if is_valid_session():
        return render_template("index.html")
    if "logout_reason" in session:
        flash(session.pop("logout_reason"))
    if request.method == "POST":
        token = request.form["token"]
        if is_valid_token(token):
            session["token"] = token
            resp = make_response(redirect(url_for("main.index")))
            expires = datetime.now() + timedelta(days=30)
            resp.set_cookie("token", token, expires=expires)
            return resp
        flash("Invalid token, please try again.")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.pop("token", None)
    resp = make_response(redirect(url_for("main.index")))
    resp.set_cookie("token", "", expires=0)
    return resp


@bp.route("/get_console_data")
def get_console_data():
    if not is_valid_session():
        session["logout_reason"] = "This token has expired. create new token."
        return jsonify({"redirect": url_for("main.logout")})
    converter = Ansi2HTMLConverter(inline=True, scheme="xterm")
    html_string = converter.convert("\n".join(LogManager.log_msg), full=False)
    server_online = ctx.server_process.poll_or_kill()
    return jsonify({
        "html_string": html_string,
        "online_status": {"server": server_online, "bot": True},
    })


@bp.route("/submit_data", methods=["POST"])
def submit_data():
    if not is_valid_session():
        return unauth()
    data = request.get_json(silent=True) or {}
    user_input = data.get("userInput") or request.form.get("userInput", "")
    if ctx.server_process.is_stopped():
        return jsonify({"ok": False, "message": "Server is not running"})
    if user_input == ctx.STOP:
        from server.control import stop_server
        stop_server()
    else:
        ctx.server_process.write(user_input)
    return jsonify({"ok": True})
