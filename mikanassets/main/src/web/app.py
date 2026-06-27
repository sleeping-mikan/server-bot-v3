"""
web_app.py — Web 管理画面 (Flask + FastAPI/uvicorn)

main.py から切り出したモジュール。
Flask アプリの生成・全ルートの登録・WSGI ミドルウェアの適用と、
uvicorn で起動するための run_webservice_server() を提供する。

run_webservice_server() はロガーのセットアップも行うため、
log_setup.init() が呼ばれた後に実行すること(main.py の web_thread から呼ばれる)。
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta

from ansi2html import Ansi2HTMLConverter
from fastapi.middleware.wsgi import WSGIMiddleware
from flask import (
    Flask,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import uvicorn

from web.download_server import SendDiscordSelfServer
from core.log_setup import LogManager
from core.state import ctx


def _create_flask_app(flask_logger: logging.Logger) -> Flask:
    """Flask アプリを生成してルートを登録し返す。"""
    app = Flask(
        __name__,
        template_folder=str(ctx.paths.web_dir),
        static_folder=str(ctx.paths.web_dir),
    )
    app.secret_key = ctx.config["web"]["secret_key"]

    # ── WSGI ミドルウェア ─────────────────────────────────────────────────────

    class _LogIPMiddleware:
        def __init__(self, wsgi_app):
            self.app = wsgi_app

        def __call__(self, environ, start_response):
            client_ip = environ.get("REMOTE_ADDR", "")
            method = environ.get("REQUEST_METHOD", "")
            uri = environ.get("PATH_INFO", "")
            query = environ.get("QUERY_STRING", "")
            if uri != "/get_console_data":
                flask_logger.info(
                    f"Client IP: {client_ip}, Method: {method}, URL: {uri}, Query: {query}"
                )
            return self.app(environ, start_response)

    app.wsgi_app = _LogIPMiddleware(app.wsgi_app)

    # ── トークンヘルパー ──────────────────────────────────────────────────────

    def _load_tokens() -> set:
        tokens: set = set()
        now = datetime.now()
        for token in ctx.web_tokens:
            if datetime.strptime(token["deadline"], "%Y-%m-%d %H:%M:%S") > now:
                tokens.add(token["token"])
        return tokens

    def _is_valid_token(token: str) -> bool:
        return token in _load_tokens()

    def _is_valid_session() -> bool:
        token = session.get("token")
        return token is not None and _is_valid_token(token)

    @app.before_request
    def _load_token_from_cookie():
        token = request.cookies.get("token")
        if token and _is_valid_token(token):
            session["token"] = token

    # ── ルート ───────────────────────────────────────────────────────────────

    @app.route("/", methods=["GET", "POST"])
    def index():
        if _is_valid_session():
            return render_template("index.html", logs=LogManager.log_msg)
        if "logout_reason" in session:
            flash(session.pop("logout_reason"))
        if request.method == "POST":
            token = request.form["token"]
            if _is_valid_token(token):
                session["token"] = token
                resp = make_response(redirect(url_for("index")))
                expires = datetime.now() + timedelta(days=30)
                resp.set_cookie("token", token, expires=expires)
                return resp
            flash("Invalid token, please try again.")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop("token", None)
        resp = make_response(redirect(url_for("index")))
        resp.set_cookie("token", "", expires=0)
        return resp

    @app.route("/get_console_data")
    def get_console_data():
        if not _is_valid_session():
            session["logout_reason"] = "This token has expired. create new token."
            return jsonify({"redirect": url_for("logout")})
        converter = Ansi2HTMLConverter()
        html_string = converter.convert("\n".join(LogManager.log_msg))
        server_online = ctx.server_process.poll_or_kill()
        return jsonify({
            "html_string": html_string,
            "online_status": {"server": server_online, "bot": True},
        })

    @app.route("/flask_start_server", methods=["POST"])
    def flask_start_server():
        if not _is_valid_session():
            session["logout_reason"] = "This token has expired. create new token."
            return jsonify({"redirect": url_for("logout")})
        from server.control import StartResult, start_server
        result = start_server(ctx.server_logger)
        if result == StartResult.ALREADY_RUNNING:
            return jsonify(ctx.text.response_msg["other"]["is_running"])
        return jsonify(ctx.text.response_msg["start"]["success"])

    @app.route("/flask_backup_server", methods=["POST"])
    def flask_backup_server():
        if not _is_valid_session():
            session["logout_reason"] = "This token has expired. create new token."
            return jsonify({"redirect": url_for("logout")})
        from server.backup import create_backup
        world_name = request.form["fileName"]
        if "\\" in world_name or "/" in world_name:
            return jsonify(
                ctx.text.response_msg["backup"]["not_allowed_path"] + f": {ctx.server_path}{world_name}"
            )
        from_path = os.path.join(ctx.server_path, world_name)
        if ctx.server_process.is_stopped():
            if os.path.exists(from_path):
                flask_logger.info("backup server")
                dst = asyncio.run(create_backup(from_path))
                flask_logger.info("backuped server to " + dst)
                return jsonify("backuped server!! " + dst)
            flask_logger.info("data not found : " + from_path)
            return jsonify(
                ctx.text.response_msg["backup"]["data_not_found"] + f": {from_path}"
            )
        return jsonify(ctx.text.response_msg["other"]["is_running"])

    @app.route("/submit_data", methods=["POST"])
    def submit_data():
        if not _is_valid_session():
            session["logout_reason"] = "This token has expired. create new token."
            return jsonify({"redirect": url_for("logout")})
        user_input = request.form["userInput"]
        if ctx.server_process.is_stopped():
            return jsonify("server is not running")
        if user_input == ctx.STOP:
            ctx.use_stop = True
        ctx.server_process.write(user_input)
        return jsonify(f"result: {user_input}")

    return app


def run_webservice_server() -> None:
    """Flask (オプション) + FastAPI を uvicorn で起動する。

    log_setup.init() 後に呼ぶこと。ロガー生成もここで行う。
    """
    from core.log_setup import ExcludePathFilter
    flask_logger       = LogManager.setup_third_party("werkzeug",      "FLASK")
    uvicorn_logger_err = LogManager.setup_third_party("uvicorn.error", "UVICORN")
    uvicorn_logger     = LogManager.setup_third_party("uvicorn.access", "UVICORN")
    _excl = ExcludePathFilter("/get_console_data")
    for lg in [flask_logger, uvicorn_logger_err, uvicorn_logger]:
        lg.addFilter(_excl)

    use_flask_server: bool = ctx.config["web"]["use_front_page"]
    web_port: int = ctx.web_port

    fastapi_app = SendDiscordSelfServer.create_app()
    if use_flask_server:
        flask_app = _create_flask_app(flask_logger)
        fastapi_app.mount("/", WSGIMiddleware(flask_app))

    uvicorn.run(fastapi_app, host="0.0.0.0", port=web_port, log_config=None)
