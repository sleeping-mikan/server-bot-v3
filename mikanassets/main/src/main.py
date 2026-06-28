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
    import requests
    for _pkg in ("discord", "flask", "ansi2html", "aiohttp", "fastapi", "uvicorn", "zipstream", "waitress"):
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

from core.config_loader import normalize_path, wait_for_keypress, make_config, to_config_safe
from core.state import ctx

now_path = normalize_path(now_path)
ctx.init_paths(now_path)

config_file_place = str(ctx.paths.config_file)

INITIAL_COMMAND_PERMISSION = {
    "stop": 1, "start": 1, "exit": 2,
    "cmd serverin": 1, "cmd stdin mk": 3, "cmd stdin rm": 2,
    "cmd stdin mkdir": 2, "cmd stdin rmdir": 2, "cmd stdin ls": 2,
    "cmd stdin mv": 3, "cmd stdin send-discord": 2, "cmd stdin wget": 3,
    "help": 0, "backup create": 1, "backup apply": 3, "ip": 0,
    "logs": 1, "permission view": 0, "permission change": 4,
    "lang": 2, "tokengen": 1, "terminal set": 1, "terminal del": 1,
    "update": 3, "announce embed": 4, "status": 0,
}

config, config_changed = make_config(now_path, INITIAL_COMMAND_PERMISSION)
ctx.config = config
to_config_safe(config, config_file_place)

try:
    log        = config["log"]
    server_path = normalize_path(config["server_path"])
    if not os.path.exists(server_path):
        print("not exist server_path dir")
        wait_for_keypress()

    if not ctx.paths.logs_dir.exists():
        ctx.paths.logs_dir.mkdir(parents=True, exist_ok=True)
    if not os.path.exists(server_path + "logs"):
        os.makedirs(server_path + "logs")
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
    ctx.backup_path            = normalize_path(config["discord_commands"]["backup"]["path"])
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
    if ctx.server_name and not os.path.exists(server_path + ctx.server_name):
        LogManager.sys.error(
            "not exist " + server_path + ctx.server_name + " file. please check your config."
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
    LogManager.sys.error("please write token in " + ctx.paths.token_file.as_posix())
    wait_for_keypress()
ctx.token = ctx.paths.token_file.read_text(encoding="utf-8")

if platform.system() == "Windows":
    ctx.temp_path = os.environ.get("TEMP", "/tmp") + "/mcserver"
else:
    ctx.temp_path = "/tmp/mcserver"
if not os.path.exists(ctx.temp_path):
    os.mkdir(ctx.temp_path)

if config.get("update", {}).get("auto"):
    asyncio.run(update_self_if_commit_changed())

# ── Minecraft server.properties ───────────────────────────────────────────────

properties: dict = {}
if config.get("process_type") == "mc-server":
    props_path = server_path + "server.properties"
    try:
        with open(props_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if line.startswith((" ", "\t")):
                        line = line[1:]
                    key, value = line.split("=", 1)
                    properties[key] = value
        LogManager.sys.info("read properties file -> " + props_path)
    except Exception as e:
        LogManager.sys.error(e)

# ── テキストデータ ────────────────────────────────────────────────────────────

from bot.text_data import load_text_data

async def _load_text() -> None:
    (
        ctx.text.help_msg,
        ctx.text.command_desc,
        ctx.text.response_msg,
        ctx.text.activity_name,
        send_help_initial,
    ) = load_text_data(ctx.text.lang, ctx.allow_cmd)
    send_help_initial += (
        f"web : http://{requests.get('https://api.ipify.org').text}:{ctx.web_port}\n"
    )
    from bot.embeds import ModifiedEmbeds
    embed = ModifiedEmbeds.DefaultEmbed(title="How to use this bot")
    for key in ctx.text.help_msg[ctx.text.lang]:
        embed.add_field(name=key, value=ctx.text.help_msg[ctx.text.lang][key], inline=False)
    embed.add_field(name="detail", value=send_help_initial, inline=False)
    ctx.text.send_help = embed

asyncio.run(_load_text())
LogManager.sys.info("text data loaded")

# ── server stdout リーダーを ctx に格納 ───────────────────────────────────────

from server.stdout import make_reader
ctx.server_logger = make_reader(log["server"], server_path)

# ── 起動ログ ──────────────────────────────────────────────────────────────────

LogManager.sys.info("bot instance root -> " + now_path)
LogManager.sys.info("server instance root -> " + server_path)
if config_changed:
    LogManager.sys.info("added config because necessary elements were missing")

# ── イベントハンドラ登録 (import だけで登録される) ────────────────────────────

importlib.import_module("bot.events")  # デコレータ実行によるイベント登録が目的

# ── コマンド登録 ──────────────────────────────────────────────────────────────

from bot.commands import (
    misc, status as status_cmd, server as server_cmd,
    permission as permission_cmd, terminal as terminal_cmd,
    tokengen as tokengen_cmd, ip as ip_cmd, logs as logs_cmd,
    cmd as cmd_cmd, backup as backup_cmd, announce as announce_cmd,
    update as update_cmd,
)

misc.setup()
status_cmd.setup(server_name=ctx.server_name, web_port=ctx.web_port)
server_cmd.setup(server_logger=ctx.server_logger)
permission_cmd.setup(get_text_dat=_load_text)
terminal_cmd.setup()
tokengen_cmd.setup()
ip_cmd.setup(
    allow_ip=config["allow"]["ip"],
    server_port=properties.get("server-port") if config.get("process_type") == "mc-server" else None,
)
logs_cmd.setup(server_path=server_path, log_msg=LogManager.log_msg)
cmd_cmd.setup()
backup_cmd.setup()
announce_cmd.setup()
update_cmd.setup()

# ── 拡張機能ロード ────────────────────────────────────────────────────────────

from bot.extensions import load as load_extensions
load_extensions()

# ── Web サーバー起動 ──────────────────────────────────────────────────────────

from web.app import run_webservice_server
web_thread = threading.Thread(target=run_webservice_server, daemon=True, name="web_thread")
web_thread.start()

# ── Discord Bot 起動 ──────────────────────────────────────────────────────────

from bot.client import client
client.run(ctx.token, log_formatter=LogManager.console_formatter)
