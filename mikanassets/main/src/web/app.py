"""
web/app.py — Flask アプリ組み立て + uvicorn 起動

Blueprint を登録するだけの薄い層。
ルートのロジックは web/routes/ 以下の各モジュールに分散している。
"""

from __future__ import annotations

import logging

from fastapi.middleware.wsgi import WSGIMiddleware
from flask import Flask, request, session
import uvicorn

from core.log_setup import LogManager
from core.state import ctx
from web.auth import is_valid_token
from web.download_server import SendDiscordSelfServer

_EXCLUDED_LOG_PATHS = {"/get_console_data", "/api/status"}


class _LogIPMiddleware:
    def __init__(self, wsgi_app):
        self.app = wsgi_app

    def __call__(self, environ, start_response):
        uri = environ.get("PATH_INFO", "")
        if uri not in _EXCLUDED_LOG_PATHS:
            ip     = environ.get("REMOTE_ADDR", "")
            method = environ.get("REQUEST_METHOD", "")
            query  = environ.get("QUERY_STRING", "")
            logging.getLogger("werkzeug").info(
                f"Client IP: {ip}, Method: {method}, URL: {uri}, Query: {query}"
            )
        return self.app(environ, start_response)


def _create_flask_app() -> Flask:
    from web.routes import backups, files, logs, main, server, status

    app = Flask(
        __name__,
        template_folder=str(ctx.paths.web_dir),
        static_folder=str(ctx.paths.web_dir),
    )
    app.secret_key = ctx.config["web"]["secret_key"]
    app.wsgi_app = _LogIPMiddleware(app.wsgi_app)

    @app.before_request
    def _load_token_from_cookie():
        token = request.cookies.get("token")
        if token and is_valid_token(token):
            session["token"] = token

    for bp in [main.bp, server.bp, files.bp, logs.bp, backups.bp, status.bp]:
        app.register_blueprint(bp)

    return app


def run_webservice_server() -> None:
    from core.log_setup import ExcludePathFilter

    flask_logger       = LogManager.setup_third_party("werkzeug",       "FLASK")
    uvicorn_logger_err = LogManager.setup_third_party("uvicorn.error",  "UVICORN")
    uvicorn_logger     = LogManager.setup_third_party("uvicorn.access", "UVICORN")
    _excl = ExcludePathFilter("/get_console_data")
    for lg in [flask_logger, uvicorn_logger_err, uvicorn_logger]:
        lg.addFilter(_excl)

    fastapi_app = SendDiscordSelfServer.create_app()
    if ctx.config["web"]["use_front_page"]:
        flask_app = _create_flask_app()
        fastapi_app.mount("/", WSGIMiddleware(flask_app))

    uvicorn.run(fastapi_app, host="0.0.0.0", port=ctx.web_port, log_config=None)
