"""
main.py — エントリポイント

役割: アプリケーションの起動シーケンスのみ。
      設定・ロギング・コマンド登録などのロジックは各モジュールに委譲する。
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import platform
import sys
import threading

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ── パッケージ存在確認 ────────────────────────────────────────────────────────

try:
    for _pkg in ("requests", "discord", "flask", "ansi2html", "aiohttp", "fastapi", "uvicorn", "zipstream", "waitress", "psutil"):
        importlib.import_module(_pkg)
    del _pkg
except ImportError:
    print("import error. please run 'pip install -r requirements.txt'")
    sys.exit(1)

# ── 起動時定数 ────────────────────────────────────────────────────────────────

from datetime import datetime
start_time = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")

now_path = os.environ.get("MIKAN_BASE_DIR") or os.path.dirname(os.path.abspath(__file__))
now_path = os.path.abspath(now_path)

# ── コア初期化 ────────────────────────────────────────────────────────────────

from pathlib import Path

from core.config_loader import wait_for_keypress, make_config
from core.state import ctx
from bot.commands import INITIAL_COMMAND_PERMISSION

ctx.init_paths(now_path)

config, config_changed = make_config(now_path, INITIAL_COMMAND_PERMISSION)
ctx.config = config

try:
    log         = config["log"]
    server_path = Path(config["server_path"])
    if not server_path.exists():
        print("not exist server_path dir")
        wait_for_keypress()

    ctx.paths.logs_dir.mkdir(parents=True, exist_ok=True)
    (server_path / "logs").mkdir(exist_ok=True)
except KeyError:
    print("(log or server_path) in config is broken.")
    wait_for_keypress()

# ── ロガー初期化 ──────────────────────────────────────────────────────────────

from core.log_setup import LogManager

LogManager.init(now_path, log["all"], start_time)
LogManager.setup_discord_lib()

# ── 設定の ctx への展開 ───────────────────────────────────────────────────────

try:
    ctx.server_name            = config["server_name"]
    ctx.server_path            = server_path
    ctx.server_args            = config["server_args"].split(" ")
    ctx.server_char_code       = config["server_char_encoding"]
    ctx.STOP                   = config["discord_commands"]["stop"]["submit"]
    ctx.backup_path            = Path(config["discord_commands"]["backup"]["path"])
    ctx.web_port               = config["web"]["port"]
    ctx.allow_cmd              = set(config["discord_commands"]["cmd"]["serverin"]["allow_mccmd"])
    ctx.enable_advanced_features = config["enable_advanced_features"]
    ctx.terminal.channel_id    = config["discord_commands"]["terminal"]["discord"]
    ctx.terminal_capacity      = (
        float("inf")
        if config["discord_commands"]["terminal"]["capacity"] == "inf"
        else config["discord_commands"]["terminal"]["capacity"]
    )
    ctx.text.lang              = config["discord_commands"]["lang"]
    ctx.text.command_permission = config["discord_commands"]["permission"]["commands_level"]
    if ctx.server_name and not (ctx.server_path / ctx.server_name).exists():
        LogManager.sys.error(
            f"not exist {ctx.server_path / ctx.server_name} file. please check your config."
        )
except KeyError:
    LogManager.sys.error("config file is broken. please delete .config and try again.")
    wait_for_keypress()

# ── 自己更新モジュール (ロガー初期化後にインポート) ───────────────────────────

from update.selfupdate import save_mikanassets_dat, update_self_if_commit_changed

# ── ディレクトリ・ファイルの初期化 ───────────────────────────────────────────

ctx.paths.mikanassets_dir.mkdir(parents=True, exist_ok=True)
ctx.paths.extension_dir.mkdir(parents=True, exist_ok=True)
if not ctx.paths.update_apply_file.exists():
    LogManager.sys.error("update_apply.py が見つかりません")

save_mikanassets_dat()

ctx.paths.data_dir.mkdir(parents=True, exist_ok=True)
if not ctx.paths.web_tokens_file.exists():
    ctx.paths.web_tokens_file.write_text(json.dumps({"tokens": []}, indent=4), encoding="utf-8")

ctx.web_tokens = json.loads(ctx.paths.web_tokens_file.read_text(encoding="utf-8"))["tokens"]

if not ctx.paths.token_file.exists():
    ctx.paths.token_file.write_text("ここにtokenを入力", encoding="utf-8")
    LogManager.sys.error(f"please write token in {ctx.paths.token_file}")
    wait_for_keypress()
ctx.token = ctx.paths.token_file.read_text(encoding="utf-8").strip()
if not ctx.token or ctx.token == "ここにtokenを入力":
    LogManager.sys.error(f"token が未設定です。{ctx.paths.token_file} に Discord bot のトークンを記入してください。")
    wait_for_keypress()

temp_base = Path(os.environ.get("TEMP", "/tmp")) if platform.system() == "Windows" else Path("/tmp")
ctx.temp_path = temp_base / "mcserver"
ctx.temp_path.mkdir(exist_ok=True)

# asyncio.run() を2回呼んでいるのは意図的: update後に sys.exit() が走るケースがあるため
# 単一 coroutine にまとめると制御フローが変わり update → exit の逐次性が崩れる。
if config.get("update", {}).get("auto"):
    asyncio.run(update_self_if_commit_changed())

# ── 公開 IP 取得 (起動時 1 回のみ) ──────────────────────────────────────────

import requests as _requests
try:
    ctx.web_ip = _requests.get("https://api.ipify.org", timeout=10).text
except Exception:
    ctx.web_ip = "unknown"
    LogManager.sys.error("failed to get public IP address")
del _requests

# ── テキストデータ ────────────────────────────────────────────────────────────

from bot.setup import load_text, setup_commands

asyncio.run(load_text())
LogManager.sys.info("text data loaded")

# ── server stdout リーダーを ctx に格納 ───────────────────────────────────────

from server.stdout import make_reader
ctx.server_logger = make_reader(log["server"])

# ── 起動ログ ──────────────────────────────────────────────────────────────────

LogManager.sys.info(f"bot instance root -> {now_path}")
LogManager.sys.info(f"server instance root -> {ctx.server_path}")
if config_changed:
    LogManager.sys.info("added config because necessary elements were missing")

# ── コマンド登録・イベント登録・拡張機能ロード ───────────────────────────────

setup_commands(config, LogManager.log_msg)

# ── Web サーバー起動 ──────────────────────────────────────────────────────────

from web.app import run_webservice_server
web_thread = threading.Thread(target=run_webservice_server, daemon=True, name="web_thread")
web_thread.start()

# ── Discord Bot 起動 ──────────────────────────────────────────────────────────

from bot.client import client
import discord as _discord
try:
    client.run(ctx.token, log_formatter=LogManager.console_formatter)
except _discord.errors.LoginFailure:
    LogManager.sys.error(f"トークンが無効です。{ctx.paths.token_file} の内容を確認してください。")
    wait_for_keypress()
