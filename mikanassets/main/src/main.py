
#--------------------

"""
各種必要なパッケージを呼び出す / libraryをインストール
"""

from datetime import datetime, timedelta
from collections import deque
import threading
import asyncio
import platform
import os
from shutil import copystat,Error,copy2,copytree,rmtree,move as shutil_move
shutil_copy2 = copy2
import logging
from copy import deepcopy
import importlib
import uuid
import io
import zipfile
import base64
import subprocess
import sys
import json
from contextlib import asynccontextmanager
import pathlib
import re
from config_loader import normalize_path, wait_for_keypress, make_config, to_config_safe
from text_data import load_text_data
#--------------------


#--------------------


args = sys.argv[1:]
do_init = False
#引数を処理する。
for i in args:
    arg = i.split("=")
    if arg[0] == "-init":
        do_init = True
#--------------------


#--------------------

# インストールしたいパッケージのリスト（パッケージ名: バージョン）
packages = {
    "discord.py": "2.3.2",
    "requests": "2.32.4",
    "Flask": "3.0.3",
    "ansi2html": "1.9.2",
    "waitress": "3.0.1",
    "aiohttp": "3.12.14",
    "psutil": "5.9.0",
    "uvicorn": "0.35.0",
    "fastapi": "0.116.1",
    "zipstream-ng": "1.8.0"
}
all_packages = [f"{pkg}=={ver}" for pkg, ver in packages.items()]


#--------------------


#--------------------


try:
    from flask import Flask, render_template, jsonify, request, session, redirect, url_for, make_response, flash
    from ansi2html import Ansi2HTMLConverter
    import waitress

    import discord 
    from discord import app_commands 
    from discord.ext import tasks
    import waitress.server
    import requests

    import aiohttp

    import psutil

    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
    import uvicorn
    import zipstream  # pip install zipstream-ng
    from fastapi.middleware.wsgi import WSGIMiddleware
except:
    print("import error. please run 'pip install -r requirements.txt'")
    sys.exit(1)
#--------------------



# 基本的な変数の読み込み

#--------------------

"""
処理に必要な定数を宣言する
"""

__version__ = "2.4.13"

def get_version():
    return __version__


intents = discord.Intents.default() 
intents.message_content = True
client = discord.Client(intents=intents) 
tree = app_commands.CommandTree(client)



#プロンプトを送る
print()

#サーバープロセス
process = None

#起動した時刻
start_time = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")

#外部変数
token = None
temp_path = None 

#現在のディレクトリ
# 本体(main.py)は mikanassets/src 内に配置されるが、.config/logs/mikanassets 等の
# 各種ファイルはエントリファイル(server.py)を基準にする必要があるため、
# server.py(ランチャー)から渡される MIKAN_BASE_DIR を優先的に使用する。
# MIKAN_BASE_DIR が無い場合(本体を直接単独実行した場合など)は、
# 従来通り __file__ の場所を基準にする。
now_path = os.environ.get("MIKAN_BASE_DIR")
if not now_path:
    now_path = "/".join(__file__.replace("\\","/").split("/")[:-1])
    # 相対パス
    if now_path == "": now_path = "."
now_path = os.path.abspath(now_path)
#現在のファイル(server.py)
now_file = "server.py"
WEB_TOKEN_FILE = '/mikanassets/web/usr/tokens.json'

#asyncioの制限を回避
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#/cmdに関する定数
cmd_logs = deque(maxlen=100)


status_lock = threading.Lock()
discord_terminal_item = deque()
discord_terminal_send_length = 0
discord_loop_is_run = False

# 濃い目の黄色
from embeds import ModifiedEmbeds, bot_color, embed_under_line_url, embed_thumbnail_url



# 権限データ
INITIAL_COMMAND_PERMISSION = {
    "stop":1,
    "start":1,
    "exit":2,
    "cmd serverin":1,
    "cmd stdin mk":3,
    "cmd stdin rm":2,
    "cmd stdin mkdir":2,
    "cmd stdin rmdir":2,
    "cmd stdin ls":2,
    "cmd stdin mv":3,
    "cmd stdin send-discord":2,
    "cmd stdin wget":3,
    "help":0,
    "backup create":1,
    "backup apply":3,
    # "replace":4,
    "ip":0,
    "logs":1,
    "permission view":0,
    "permission change":4,
    "lang":2,
    "tokengen":1,
    "terminal set":1,
    "terminal del":1,
    "update":3,
    "announce embed":4,
    "status":0,
}



unti_GC_obj = deque()

# 拡張機能から読み込むdiscord.tasks
extension_tasks_func = []

#--------------------


#--------------------


#ログをdiscordにも返す可能性がある
is_back_discord = False
#--------------------


# オブジェクトのロード

#--------------------


#--------------------

# util関数のロード

#--------------------


async def not_enough_permission(interaction: discord.Interaction,logger: logging.Logger) -> bool:
    logger.error('permission denied')
    embed = ModifiedEmbeds.ErrorEmbed(title=RESPONSE_MSG["other"]["no_permission"])
    await interaction.response.send_message(embed = embed,ephemeral = True)


async def is_administrator(user: discord.User) -> bool:
    if not user.guild_permissions.administrator:
        return False
    return True

async def is_force_administrator(user: discord.User) -> bool:
    #user idがforce_adminに含まれないなら
    if user.id not in config["discord_commands"]["admin"]["members"]:
        return False
    return True

#既にサーバが起動しているか
def is_running_server(logger: logging.Logger) -> bool:
    global process
    if process is not None:
        logger.error('server is still running')
        return True
    return False

#サーバーが閉まっている状態か
def is_stopped_server(logger: logging.Logger) -> bool:
    global process
    if process is None:
        logger.error('server is not running')
        return True
    return False

async def reload_config():
    import json
    with open(config_file_place, 'r') as f:
        global config
        config = json.load(f)
        #TODO
    

async def rewrite_config(config: dict) -> bool:
    try:
        with open(config_file_place, 'w') as f:
            json.dump(config, f,indent=4, ensure_ascii=False)
        return True
    except:
        return False
    



# ファイルパスを"/"に統一する


async def dircp_discord(src, dst, interaction: discord.Interaction, embed: ModifiedEmbeds.DefaultEmbed, symlinks=False) -> None:
    global exist_files, copyed_files
    """
    src : コピー元dir
    dst : コピー先dir
    symlinks : リンクをコピーするか
    """
    src = normalize_path(src)
    dst = normalize_path(dst)
    original_src = src
    original_dst = dst
    #表示サイズ
    bar_width = 30
    #送信制限
    max_send = 20
    # dstがbackuppathの場合だけ名前を操作する
    if dst.startswith(backup_path):
        dst = os.path.join(dst,datetime.now().strftime('%Y-%m-%d_%H_%M_%S') + "-" + os.path.basename(src))
    exist_files = 0
    total_size, copied_size = 0, 0
    for root, dirs, files in os.walk(top=src, topdown=False):
        exist_files += len(files)
        for file in files:
            filepath = os.path.join(root, file)
            if not os.path.islink(filepath):
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass
    #何ファイルおきにdiscordへ送信するか(最大100回送信するようにする)
    send_sens = int(exist_files / max_send) if exist_files > max_send else 1
    copyed_files = 0
    async def copytree(src, dst, symlinks=False):
        global copyed_files
        nonlocal total_size, copied_size
        names = os.listdir(src)
        if not os.path.exists(dst):
            os.makedirs(dst)
        errors = []
        for name in names:
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            try:
                if symlinks and os.path.islink(srcname):
                    linkto = os.readlink(srcname)
                    os.symlink(linkto, dstname)
                elif os.path.isdir(srcname):
                    await copytree(srcname, dstname, symlinks)
                else:
                    await asyncio.to_thread(copy2, srcname, dstname)
                    # コピーサイズ加算
                    try:
                        file_size = os.path.getsize(srcname)
                    except OSError:
                        file_size = 0
                    copied_size += file_size
                    copyed_files += 1
                    if copyed_files % send_sens == 0 or copyed_files == exist_files:
                        now = RESPONSE_MSG["backup"]["now_backup"]
                        if copyed_files == exist_files:
                            now = RESPONSE_MSG["backup"]["success"]
                        embed.clear_fields()
                        embed.add_field(name = f"{now}",value=f"copy {original_src} -> {original_dst}\n```{int((copyed_files / exist_files * bar_width) - 1) * '='}☆{((bar_width) - int(copyed_files / exist_files * bar_width)) * '-'}\n{'{: 5}'.format(copyed_files)} / {'{: 5}'.format(exist_files)} ({'{: 3.2f} / {: 3.2f} GB'.format(copied_size / 1024 / 1024 / 1024, total_size / 1024 / 1024 / 1024)})```", inline = False)
                        await interaction.edit_original_response(embed=embed)
            except OSError as why:
                errors.append((srcname, dstname, str(why)))
            # catch the Error from the recursive copytree so that we can
            # continue with other files
            except Error as err:
                errors.extend(err.args[0])
        try:
            copystat(src, dst)
        except OSError as why:
            # can't copy file access times on Windows
            if why.winerror is None:
                errors.extend((src, dst, str(why)))
        if errors:
            raise Error(errors)
    await copytree(src, dst, symlinks)
    
#logger thread
def server_logger(proc:subprocess.Popen,ret):
    global process,is_back_discord , use_stop
    if log["server"]:
        file = open(file = server_path + "logs/server " + datetime.now().strftime("%Y-%m-%d_%H_%M_%S") + ".log",mode = "w", encoding="utf-8")
    while True:
        try:
            logs = proc.stdout.readline()
        except Exception as e:
            sys_logger.error(e)
            continue
        # プロセスが終了している
        if logs == '': 
            if proc.poll() is not None:
                break
            continue
        #ログが\nのみであれば不要
        if logs == "\n":
            continue
        #後ろが\nなら削除
        logs = logs.rstrip("\n")
        minecraft_logger.info(logs)
        if log["server"]:
            file.write(logs + "\n")
            file.flush()
        if is_back_discord:
            cmd_logs.append(logs)
            is_back_discord = False
    #サーバーが終了したことをログに残す
    sys_logger.info('server is ended')
    #もし、stop命令が見当たらないなら、エラー出力をしておく
    if not use_stop:
        sys_logger.error('stop command is not found')
        use_stop = True
    #プロセスを終了させる
    process = None

async def print_user(logger: logging.Logger,user: discord.user):
    logger.info('command used by ' + str(user))

class ServerBootException(Exception):pass

async def user_permission(user:discord.User):
    # ユーザが管理者なら
    if await is_administrator(user):
        return USER_PERMISSION_MAX
    # configに権限が書かれていないなら
    if str(user.id) not in config["discord_commands"]["admin"]["members"]:
        return 0
    return config["discord_commands"]["admin"]["members"][str(user.id)]

# 操作可能なパスかを確認
def is_path_within_scope(path):
    # 絶対パスを取得
    path = os.path.abspath(path)
    resolved_target_path = pathlib.Path(path).resolve(strict=False)
    resolved_server_path = pathlib.Path(server_path).resolve()
    try:
        resolved_target_path.relative_to(resolved_server_path)
        sys_logger.info("valid path -> " + path + f"[{resolved_target_path}]" + f"(server_path : {server_path}[{resolved_server_path}])")
        return True
    except ValueError:
        sys_logger.info("invalid path -> " + path + f"[{resolved_target_path}]" + f"(server_path : {server_path}[{resolved_server_path}])")
        return False

async def create_zip_async(file_path: str) -> tuple[io.BytesIO, int]:
    """ディレクトリをZIP化し、非同期的に返す関数"""
    loop = asyncio.get_event_loop()
    zip_buffer = io.BytesIO()

    def zip_task():
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_STORED) as zipf:
            for root, dirs, files in os.walk(file_path):
                for file in files:
                    full_file_path = os.path.join(root, file)
                    zipf.write(full_file_path, os.path.relpath(full_file_path, file_path))
        zip_buffer.seek(0)
        return zip_buffer

    # 非同期スレッドでZIP作成を実行
    zip_buffer = await loop.run_in_executor(None, zip_task)
    file_size = zip_buffer.getbuffer().nbytes
    return zip_buffer, file_size

async def send_discord_message_or_followup(interaction: discord.Interaction, message: str = discord.utils.MISSING, file = discord.utils.MISSING):
    if interaction.response.is_done():
        await interaction.followup.send(message, file=file)
    else:
        await interaction.response.send_message(message, file=file)

async def send_discord_message_or_edit(interaction: discord.Interaction, message: str = discord.utils.MISSING, file = discord.utils.MISSING, embed = discord.utils.MISSING, ephemeral = False):
    if interaction.response.is_done():
        await interaction.edit_original_response(content=message, embed=embed, attachments=[file] if file is not discord.utils.MISSING else discord.utils.MISSING)
    else:
        await interaction.response.send_message(content=message, file=file, embed=embed, ephemeral=ephemeral)


async def parse_mimd(text: str):
    first_title_flag = False
    send_data = deque([{"name":"","value":""}])
    origin_data = {"title": ""}
    for line in text.split("\n"):
        parse_line = line
        while parse_line.startswith(" "):
            parse_line = parse_line[1:]
        # #から始まる一文ならnameに
        if parse_line[0] == "#":
            send_data.append({"name":"","value":""})
            send_data[-1]["name"] = parse_line[1:]
        # タイトルの設定(先頭のみ有効)
        elif parse_line.startswith("|title|") and not first_title_flag:
            origin_data["title"] = parse_line[7:]
            first_title_flag = True
        # 何でもないテキストならデータをセット
        else:
            send_data[-1]["value"] += line
    return send_data, origin_data

async def get_directory_size(path):
    size = 0
    for entry in os.scandir(path):
        if entry.is_file():
            size += entry.stat().st_size
        elif entry.is_dir():
            size += await get_directory_size(entry.path)
    return size
#--------------------

# 基本変数の加工処理

#--------------------


now_path = normalize_path(now_path)
#--------------------


# エラー時の処理

#--------------------

#--------------------


# ロガー作成前なので最小限

#--------------------

"""
configの読み込みと最小限の変数へのロードを行う
"""


config_file_place = now_path + "/" + ".config"



config,config_changed = make_config(now_path, INITIAL_COMMAND_PERMISSION)
#整合性チェック
to_config_safe(config, config_file_place)
#ロガー作成前なので最小限の読み込み
try:
    log = config["log"]
    server_path = normalize_path(config["server_path"])
    if not os.path.exists(server_path):
        print("not exist server_path dir")
        wait_for_keypress()
    #ログファイルの作成
    def make_logs_file():
        #./logsが存在しなければlogsを作成する
        if not os.path.exists(now_path + "/" + "logs"):
            os.makedirs(now_path + "/" + "logs")
        if not os.path.exists(server_path + "logs"):
            os.makedirs(server_path + "logs")
    make_logs_file()
except KeyError:
    print("(log or server_path) in config file is broken. please input true or false and try again.")
    wait_for_keypress()
#--------------------


# Colorクラスの定義

#--------------------


#--------------------------------------------------------------------------------------------ログ関連
from colors import Color
from log_setup import (
    Formatter,
    dt_fmt,
    console_formatter,
    file_formatter,
    log_msg,
    discord_log_msg,
    create_logger,
    get_log,
)
import log_setup as _log_setup
# create_logger()がファイル出力等に使う情報を設定する(ここ以降のcreate_logger呼び出しに必須)
_log_setup.init(now_path, log["all"], start_time)

#ロガーの作成
logger_name = ["stop", "start", "exit", "ready", "cmd", "help", "backup", "replace", "ip", "sys"]

stop_logger = create_logger("stop")
start_logger = create_logger("start")
exit_logger = create_logger("exit")
ready_logger = create_logger("ready")
cmd_logger = create_logger("cmd")
help_logger = create_logger("help")
backup_logger = create_logger("backup")
replace_logger = create_logger("replace")
ip_logger = create_logger("ip")
sys_logger = create_logger("sys")
log_logger = create_logger("log")
permission_logger = create_logger("permission")
admin_logger = create_logger("admin")
lang_logger = create_logger("lang")
token_logger = create_logger("token")
terminal_logger = create_logger("terminal")
base_extension_logger = create_logger("extension")
update_logger = create_logger("update")
announce_logger = create_logger("send")
status_logger = create_logger("status")
minecraft_logger = create_logger("minecraft",Formatter.MinecraftFormatter(f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt),Formatter.MinecraftConsoleFormatter('%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt))

#--------------------


# 残りのconfig読み出し

#--------------------


#configの読み込み
try:
    allow_cmd = set(config["discord_commands"]["cmd"]["serverin"]["allow_mccmd"])
    server_name = config["server_name"]
    server_args = config["server_args"].split(" ")
    if not os.path.exists(server_path + server_name):
        sys_logger.error("not exist " + server_path + server_name + " file. please check your config.")
        wait_for_keypress()
    allow = {"ip":config["allow"]["ip"]}
    log = config["log"]
    now_dir = server_path.replace("\\","/").split("/")[-2]
    backup_path = normalize_path(config["discord_commands"]["backup"]["path"])
    lang = config["discord_commands"]["lang"]
    bot_admin = config["discord_commands"]["admin"]["members"]
    flask_secret_key = config["web"]["secret_key"]
    web_port = config["web"]["port"]
    STOP = config["discord_commands"]["stop"]["submit"]
    where_terminal = config["discord_commands"]["terminal"]["discord"]
    is_auto_update = config["update"]["auto"]
    update_branch = config["update"]["branch"]
    enable_advanced_features = config["enable_advanced_features"]
    sys_files = config["discord_commands"]["cmd"]["stdin"]["sys_files"]
    if config["discord_commands"]["terminal"]["capacity"] == "inf":
        terminal_capacity = float("inf")
    else:
        terminal_capacity = config["discord_commands"]["terminal"]["capacity"]
    # send_discord_mode = config["discord_commands"]["cmd"]["stdin"]["send_discord"]["mode"]
    send_discord_bits_capacity = config["discord_commands"]["cmd"]["stdin"]["send_discord"]["bits_capacity"]
    use_flask_server = config["web"]["use_front_page"]
    server_char_code = config["server_char_encoding"]
    COMMAND_PERMISSION = config["discord_commands"]["permission"]["commands_level"]
    SUBPROCESS_PROCESS_TYPE = config["process_type"]
    
except KeyError:
    sys_logger.error("config file is broken. please delete .config and try again.")
    wait_for_keypress()

# 関連の定数
USER_PERMISSION_MAX = max(COMMAND_PERMISSION.values())

sys_logger.info("advanced features -> " + str(enable_advanced_features))
#--------------------


# ファイルの作成/修正/アップデート

#--------------------



repository = {
    "user": "sleeping-mikan",     # 公開リポジトリのowner名(server.py側のGITHUB_OWNERと必ず一致させること)
    "name": "server-bot-v3",      # 公開リポジトリ名(server.py側のGITHUB_REPOと必ず一致させること)
    "branch": update_branch,#!debug else main
}

def get_self_commit_id():
    """
    リポジトリ全体(branch先頭)の最新commit shaを取得する。
    旧バージョンはserver.py単一ファイルのshaのみを見ていたが、
    本体が mikanassets/src 配下の複数ファイル(リポジトリ全体)になったため、
    リポジトリ全体のHEADコミットのshaで判定する。
    """
    url = f'https://api.github.com/repos/{repository["user"]}/{repository["name"]}/commits/{repository["branch"]}'
    response = requests.get(url)
    if response.status_code != 200:
        sys_logger.error("github api error. status code: " + str(response.status_code))
        return None
    commit_id = response.json()["sha"]
    return commit_id




is_first_run = False

# mikanassets/extensionフォルダを作成
if not os.path.exists(now_path + "/mikanassets/extension"):
    # 最初の起動の場合にはフラグを立てておく
    is_first_run = True
    os.makedirs(now_path + "/mikanassets/extension")

# update_apply.py(自己更新の実行役)は mikanassets/main/src/update_apply.py に常駐し、
# 起動時の複製は行わない(self-update実行時にこのファイル自身も含めて新しい内容に置き換わる)。
if not os.path.exists(now_path + "/mikanassets"):
    os.makedirs(now_path + "/mikanassets")
if not os.path.exists(os.path.join(now_path, "mikanassets", "main", "src", "update_apply.py")):
    sys_logger.error("update_apply.py が見つかりません (自己更新が正しく行えない可能性があります)")

def save_mikanassets_dat():
    if not os.path.exists(now_path + "/mikanassets"):
        os.makedirs(now_path + "/mikanassets")
    if not os.path.exists(os.path.join(now_path, "mikanassets", ".dat")):
        # 存在しなければデータファイルを作成する(現状 commit id 保管用)
        file = open(os.path.join(now_path, "mikanassets", ".dat"), "w")
        file.write('{"commit_id":' + f'"{get_self_commit_id()}"' + '}')
        file.close()
save_mikanassets_dat()
    #os.system("curl https://www.dropbox.com/scl/fi/w93o5sndwaiuie0otorm4/update.py?rlkey=gh3gqbt39iwg4afey11p99okp&st=2i9a9dzp&dl=1 -o ./update.py")
if not os.path.exists(now_path + "/mikanassets/web"):
    os.makedirs(now_path + "/mikanassets/web")
if not os.path.exists(now_path + "/mikanassets/web/index.html") or do_init:
    url='https://www.dropbox.com/scl/fi/04to7yrstmgdz9j09ljy2/index.html?rlkey=7q8eu0nooj8zy34dguwwsbkjd&st=4cb6y9sr&dl=1'
    filename= now_path + '/mikanassets/web/index.html'
    urlData = requests.get(url).content
    with open(filename ,mode='wb') as f: # wb でバイト型を書き込める
        f.write(urlData)
if not os.path.exists(now_path + "/mikanassets/web/login.html") or do_init:
    url='https://www.dropbox.com/scl/fi/6yuq2dhqozxeh8vxj8wgy/login.html?rlkey=9w9tbevra7r9vwjeofslb8j0x&st=sxtayji2&dl=1'
    filename= now_path + '/mikanassets/web/login.html'
    urlData = requests.get(url).content
    with open(filename ,mode='wb') as f: # wb でバイト型を書き込める
        f.write(urlData)
#mikanassets/web/usr/tokens.jsonを作成
if not os.path.exists(now_path + "/mikanassets/web/usr"):
    os.makedirs(now_path + "/mikanassets/web/usr")
if not os.path.exists(now_path + "/mikanassets/web/usr/tokens.json"):
    #ファイルを作成
    tokenfile_items = {"tokens":[]}
    file = open(now_path + "/mikanassets/web/usr/tokens.json","w",encoding="utf-8")
    file.write(json.dumps(tokenfile_items,indent=4))
    file.close()
    del tokenfile_items
if not os.path.exists(now_path + "/mikanassets/web/pictures"):
    os.makedirs(now_path + "/mikanassets/web/pictures")
if not os.path.exists(now_path + "/mikanassets/web/pictures/icon.png") or do_init:
    url = 'https://www.dropbox.com/scl/fi/cr6uejk7s2vk4zevm8zc6/boticon.png?rlkey=szuisf29w1rnynz9xs9ucr24l&st=a8kuy1fd&dl=1'
    filename= now_path + '/mikanassets/web/pictures/icon.png'
    urlData = requests.get(url).content
    with open(filename ,mode='wb') as f: # wb でバイト型を書き込める
        f.write(urlData)

def read_web_tokens():
    file = open(now_path + "/mikanassets/web/usr/tokens.json","r",encoding="utf-8")
    tokens = json.load(file)["tokens"]
    file.close()
    return tokens

web_tokens = read_web_tokens()

def make_token_file():
    global token
    #./.tokenが存在しなければ.tokenを作成する
    if not os.path.exists(now_path + "/" + ".token"):
        file = open(now_path + "/" + ".token","w",encoding="utf-8")
        file.write("ここにtokenを入力")
        file.close()
        sys_logger.error("please write token in" + now_path + "/" +".token")
        #ブロッキングする
        wait_for_keypress()
    #存在するならtokenを読み込む(json形式)
    else:
        token = open(now_path + "/" + ".token","r",encoding="utf-8").read()

def make_temp():
    global temp_path
    #tempファイルの作成場所
    if platform.system() == 'Windows':
        # %temp%/mcserver を作成
        temp_path = os.environ.get('TEMP') + "/mcserver"
    else:
        # /tmp/mcserver を作成
        temp_path = "/tmp/mcserver"

    #tempファイルの作成
    if not os.path.exists(temp_path):
        os.mkdir(temp_path)

async def update_self_if_commit_changed(interaction: discord.Interaction | None = None,embed: ModifiedEmbeds.DefaultEmbed | None = None, text_pack: dict | None = None, sender = None, is_force = False):
    # ファイルが存在しなければ作る
    if not os.path.exists(os.path.join(now_path, "mikanassets", ".dat")):
        save_mikanassets_dat()
    file = open(os.path.join(now_path, "mikanassets", ".dat"))
    # 現在のserver.pyのコミットidを取り出す
    try:
        data = json.load(file)
        commit = data["commit_id"]
    except:
        if interaction is not None and embed is not None:
            embed.add_field(name="error", value="json load error (mikanassets/.dat). delete file.", inline=False)
            await sender(interaction=interaction,embed=embed)
        update_logger.error("json load error (mikanassets/.dat). delete file.")
    file.close()
    # github/mainのコミットidを取り出す
    github_commit = get_self_commit_id()
    # 戻り値が正常でない場合はここで中断する(以前はログ出力でNone+strの結合がそのまま例外になっていた)
    if github_commit is None:
        update_logger.error("github commit is None. (github api error. check network / repository settings)")
        if interaction is not None and embed is not None:
            embed.add_field(name="error", value="github response error.", inline=False)
            await sender(interaction=interaction,embed=embed)
        return
    update_logger.info("github commit -> " + github_commit)
    update_logger.info(" local commit -> " + commit)
    # コミットid出力
    if interaction is not None and embed is not None:
        embed.add_field(name="github file", value=github_commit, inline=False)
        embed.add_field(name="local file", value=commit, inline=False)
        await sender(interaction=interaction,embed=embed)
    # 更新がない場合
    if commit == github_commit and not is_force: 
        if interaction is not None and embed is not None:
            embed.add_field(name="", value=text_pack["same"], inline=False)
            await sender(interaction=interaction,embed=embed)
        update_logger.info("commit is same. no update.")
        return
    # ファイルに新しいcommit id を書き込む
    data["commit_id"] = github_commit
    file = open(os.path.join(now_path, "mikanassets", ".dat"), "w")
    json.dump(data, file)
    file.close()
    # ローカルとgithubのコードが違ったことを出力
    if interaction is not None and embed is not None:
        if is_force:
            embed.add_field(name="", value=text_pack["force"], inline=False)
        else:
            embed.add_field(name="", value=text_pack["different"], inline=False)
        await sender(interaction=interaction,embed=embed)
    update_logger.info("commit changed. update self.")
    # リポジトリ全体をzipでダウンロードする(server.py起動時のダウンロードと同じ方式)
    zip_url = f'https://github.com/{repository["user"]}/{repository["name"]}/archive/refs/heads/{repository["branch"]}.zip'
    response = requests.get(zip_url)
    if response.status_code != 200:
        sys_logger.error("response error. status_code : " + str(response.status_code))
        if interaction is not None and embed is not None:
            embed.add_field(name="error : github zip download error", value="", inline=False)
            await sender(interaction=interaction,embed=embed)
        return
    # temp_path/new_repo に展開する(既存があれば消してから展開し直す)
    new_repo_extract_dir = os.path.join(temp_path, "new_repo")
    if os.path.exists(new_repo_extract_dir):
        rmtree(new_repo_extract_dir)
    os.makedirs(new_repo_extract_dir)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(new_repo_extract_dir)
    # githubのzipballは "{repo}-{branch}/" という単一のルートフォルダを持つ
    extracted_items = os.listdir(new_repo_extract_dir)
    if len(extracted_items) != 1:
        sys_logger.error("unexpected zip structure: " + str(extracted_items))
        if interaction is not None and embed is not None:
            embed.add_field(name="error : unexpected zip structure", value="", inline=False)
            await sender(interaction=interaction,embed=embed)
        return
    new_repo_root = os.path.join(new_repo_extract_dir, extracted_items[0])
    # discordにコードを置き換えることを通知
    msg_id = str(0)
    channel_id = str(0)
    if interaction is not None and embed is not None:
        msg_id = str((await interaction.original_response()).id)
        channel_id = str(interaction.channel_id)
        # embed.add_field(name="", value=text_pack["replace"].format(channel_id,msg_id), inline=False)
        await sender(interaction=interaction,embed=embed)
    replace_logger.info("call update_apply.py")
    replace_logger.info('replace args : ' + msg_id + " " + channel_id)
    update_apply_path = os.path.join(now_path, "mikanassets", "main", "src", "update_apply.py")
    # update_apply.py は mikanassets/main/src 配下に常駐したまま実行される
    # (Pythonはスクリプト読み込み後に実行するため、自分自身が入っているmainディレクトリを
    #  入れ替えても動作に影響しない)
    os.execv(sys.executable,[
        sys.executable,
        update_apply_path,
        new_repo_root,      # 展開済みの新しいリポジトリのルート
        now_path,           # server.pyを基準とするベースディレクトリ
        now_file,           # エントリファイル名(通常 "server.py")
        msg_id,
        channel_id,
        token,              # 完了報告メッセージ編集用のbotトークン
    ])



make_token_file()
make_temp()
if is_auto_update:
    asyncio.run(update_self_if_commit_changed())
#--------------------


# mcサーバー用properties読み込み

#--------------------



#java properties の読み込み
def properties_to_dict(filename):
    properties = {}
    try:
        with open(filename) as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith(' ') or line.startswith('\t'):
                        line = line[1:]
                    key, value = line.split('=', 1)
                    properties[key] = value
        return properties
    except Exception as e:#ファイルが存在しなければ存在しないことを出力して終了
        sys_logger.error(e)
        sys_logger.info("not exist server.properties file in " + server_path + ". if you are not using a minecraft server, please set mc to false in .config .if not, restart it and server.properties should be generated in the server hierarchy.")
        return {}

#minecraftサーバーであればpropertiesを読み込む
if SUBPROCESS_PROCESS_TYPE == "mc-server":
    properties = properties_to_dict(server_path + "server.properties")
    sys_logger.info("read properties file -> " + server_path + "server.properties")

#コマンド利用ログ
use_stop = False
#--------------------


# テキスト関連データの作成

#--------------------



async def get_text_dat():
    global HELP_MSG, COMMAND_DESCRIPTION, send_help, RESPONSE_MSG, ACTIVITY_NAME
    HELP_MSG, COMMAND_DESCRIPTION, RESPONSE_MSG, ACTIVITY_NAME, send_help = load_text_data(lang, allow_cmd)
    def make_send_help():
        global send_help
        send_help += f"web : http://{requests.get('https://api.ipify.org').text}:{web_port}\n"
        embed = ModifiedEmbeds.DefaultEmbed(title="How to use this bot")
        for key in HELP_MSG[lang]:
            embed.add_field(name=key,value=HELP_MSG[lang][key],inline=False)
        embed.add_field(name="detail",value=send_help,inline=False)
        send_help = embed
    make_send_help()


get_text = asyncio.run(get_text_dat())
sys_logger.info('create text data')


#--------------------



# 読み込み結果の出力

#--------------------


#ローカルファイルの読み込み結果出力
sys_logger.info("bot instance root -> " + now_path)
sys_logger.info("server instance root -> " + server_path)
sys_logger.info("read token file -> " + normalize_path(now_path + "/" +".token"))
sys_logger.info("read config file -> " + normalize_path(now_path + "/" +".config"))
view_config = config.copy()
view_config["web"]["secret_key"] = "****"
sys_logger.info("config -> " + str(view_config))
if config_changed: sys_logger.info("added config because necessary elements were missing")
#--------------------


# 読み込み時関数/ループ関数/メッセージ受信時関数を定義

#--------------------

@tasks.loop(seconds=10)
async def update_loop():
    global discord_terminal_item, discord_terminal_send_length, discord_loop_is_run
    # discord_loop_is_runを確認(2回以上実行された場合は処理をしない)
    if discord_loop_is_run: return
    try:
        discord_loop_is_run = True
        with status_lock:
            if process is not None:
                await client.change_presence(activity=discord.Game(name=ACTIVITY_NAME["running"].format(server_name)))
            else:
                await client.change_presence(activity=discord.Game(name=ACTIVITY_NAME["ended"]))
            # discord_log_msgにデータがあれば送信
            # 送信が無効の場合
            if where_terminal == False:
                discord_log_msg.clear()
                discord_loop_is_run = False
                return
            pop_flg = False
            while len(discord_log_msg) > 0:
                while len(discord_log_msg) > terminal_capacity:
                    discord_log_msg.popleft()
                    pop_flg = True
                if pop_flg:
                    await client.get_channel(where_terminal).send(f"データ件数が{terminal_capacity}件を超えたため以前のデータを破棄しました。より多くのログを出力するには.config内のterminal.capacityを変更してください。")
                    pop_flg = False
                if len(discord_log_msg[0]) >= 1900:
                    discord_log_msg.popleft()
                    raise Exception("message is too long(skipped)")
                discord_terminal_send_length += len(discord_log_msg[0]) + 1
                if discord_terminal_send_length >= 1900:
                    # 送信処理(where_terminal chに送信)
                    await client.get_channel(where_terminal).send("```ansi\n" + ''.join(discord_terminal_item) + "\n```")
                    # discord_terminal_itemをリセット
                    discord_terminal_item = deque()
                    discord_terminal_send_length = len(discord_log_msg[0]) + 1
                    # 連投を避けるためにsleep
                    await asyncio.sleep(1)
                discord_terminal_item.append(discord_log_msg.popleft() + "\n")
            # 残っていれば送信
            if len(discord_terminal_item) > 0:
                await client.get_channel(where_terminal).send("```ansi\n" + ''.join(discord_terminal_item) + "\n```")
                discord_terminal_item = deque()
                discord_terminal_send_length = 0
        discord_loop_is_run = False
    except Exception as e:
        terminal_logger.error(e)
        discord_loop_is_run = False

# メッセージが送信されたときの処理
@client.event
async def on_message(message: discord.Message):
    try:
        # ボット自身のメッセージは無視する
        if message.author == client.user:
            return
        # terminal ch以外のメッセージは無視
        if message.channel.id != where_terminal:
            return
        # 管理者以外をはじく
        if not await is_administrator(message.author) and not await is_force_administrator(message.author):
            await message.reply("permission denied")
            return
        # サーバーが閉じていたらはじく
        if process is None or process.poll() is not None:
            await message.reply("server is not running")
            return
        # コマンドを処理
        cmd_list = message.content.split(" ")
        # 許可されないコマンドをはじく
        if message.author.bot is True: pass
        elif cmd_list[0] not in allow_cmd:
            sys_logger.error('unknown command : ' + " ".join(cmd_list))
            await message.reply("this command is not allowed")
            return
        else:
            process.stdin.write(message.content + "\n")
            process.stdin.flush()
    except Exception as e:
        sys_logger.error(e)

@client.event
async def on_ready():
    global process
    ready_logger.info('discord bot logging on')
    # update_loopを開始
    update_loop.start()
    # 拡張で読み込んだtasksを実行
    for task in extension_tasks_func:
        task.start()
    try:
        #サーバーの起動
        await client.change_presence(activity=discord.Game(ACTIVITY_NAME["starting"]))
        if process is  None:
            #server を実行する
            process = subprocess.Popen([server_path + server_name, *server_args],cwd=server_path,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,encoding=server_char_code)
            threading.Thread(target=server_logger,args=(process,deque())).start()
            ready_logger.info('server starting')
        else:
            ready_logger.info('skip server starting because server already running')
        # アクティビティを設定 
        await client.change_presence(activity=discord.Game(ACTIVITY_NAME["running"].format(server_name))) 
    except Exception as e:
        sys_logger.error(f"error on ready (server start) -> {e}")
    # スラッシュコマンドを同期
    # (サーバー起動に失敗してもコマンド自体は使えるようにするため、上のtry/exceptとは別に必ず実行する)
    try:
        await tree.sync()
        ready_logger.info('slash commands synced')
    except Exception as e:
        sys_logger.error(f"error on ready (command sync) -> {e}")
#--------------------


# 機能関数読み込み

#--------------------



#--------------------





def core_stop() -> str:
    global process,use_stop
    if is_stopped_server(stop_logger):
        return RESPONSE_MSG["other"]["is_not_running"]
    use_stop = True
    stop_logger.info('server stopping')
    process.stdin.write(STOP + "\n")
    process.stdin.flush()
    return RESPONSE_MSG["stop"]["success"]

def core_start() -> str:
    global process,use_stop
    if is_running_server(start_logger):
        return RESPONSE_MSG["other"]["is_running"]
    start_logger.info('server starting')
    process = subprocess.Popen([server_path + server_name, *server_args],cwd=server_path,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,encoding=server_char_code)
    threading.Thread(target=server_logger,args=(process,deque())).start()
    return RESPONSE_MSG["start"]["success"]

#--------------------


#--------------------


# スラッシュコマンドを定義

#--------------------



#start
@tree.command(name="start",description=COMMAND_DESCRIPTION[lang]["start"])
async def start(interaction: discord.Interaction):
    await print_user(start_logger,interaction.user)
    if await user_permission(interaction.user) < COMMAND_PERMISSION["start"]: 
        await not_enough_permission(interaction,start_logger)
        return
    # core_start()がサーバー起動処理(プロセス起動・ディスクI/O)で3秒を超えると、
    # interaction.response.send_message が "Unknown interaction" (404) になるため、
    # 先にdeferで受付応答してから本処理・followupで結果を送る。
    await interaction.response.defer()
    result = core_start()
    embed = ModifiedEmbeds.DefaultEmbed(title = f"/start")
    embed.add_field(name="",value=result,inline=False)
    await interaction.followup.send(embed=embed)
    if result == RESPONSE_MSG["other"]["is_running"]:
        return
    await client.change_presence(activity=discord.Game(ACTIVITY_NAME["running"].format(server_name)))

#/stop
@tree.command(name="stop",description=COMMAND_DESCRIPTION[lang]["stop"])
async def stop(interaction: discord.Interaction):
    global use_stop
    await print_user(stop_logger,interaction.user)
    global process
    #管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["stop"]: 
        #両方not(権限がないなら)
        await not_enough_permission(interaction,stop_logger)
        return
    # 同様にdeferしてからcore_stop()を実行する(start同様のタイムアウト対策)
    await interaction.response.defer()
    result = core_stop()
    embed = ModifiedEmbeds.DefaultEmbed(title = f"/stop")
    embed.add_field(name="",value=result,inline=False)

    await interaction.followup.send(embed=embed)
    if result == RESPONSE_MSG["other"]["is_not_running"]:
        return
    await client.change_presence(activity=discord.Game(ACTIVITY_NAME["ending"])) 
    while True:
        #終了するまで待つ
        if process is None:
            await client.change_presence(activity=discord.Game(ACTIVITY_NAME["ended"])) 
            break
        await asyncio.sleep(1)


#--------------------


# グループの設定
# root
command_group_permission = app_commands.Group(name="permission",description="permission group")

#/admin force <add/remove>
@command_group_permission.command(name="change",description=COMMAND_DESCRIPTION[lang]["permission"]["change"])
async def change(interaction: discord.Interaction,level: int,user:discord.User):
    await print_user(admin_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title = f"/permission change {level} {user}")
    if await user_permission(interaction.user) < COMMAND_PERMISSION["permission change"]:
        await not_enough_permission(interaction,lang_logger)
        return
    async def read_force_admin():
        global bot_admin
        bot_admin = config["discord_commands"]["admin"]["members"]
    # 権限レベル1~4を付与
    if level >= 1 and level <= USER_PERMISSION_MAX:
        if user.id in config["discord_commands"]["admin"]["members"]:
            embed.add_field(name="",value=RESPONSE_MSG["permission"]["change"]["already_added"],inline=False)
            await interaction.response.send_message(embed=embed)
            return
        config["discord_commands"]["admin"]["members"][str(user.id)] = level
        #configファイルを変更する
        await rewrite_config(config)
        await read_force_admin()
        embed.add_field(name="",value=RESPONSE_MSG["permission"]["change"]["add_success"].format(user),inline=False)
        await interaction.response.send_message(embed=embed)
        admin_logger.info(f"exec force admin add {user}")
    elif level == 0:
        if str(user.id) not in config["discord_commands"]["admin"]["members"]:
            embed.add_field(name="",value=RESPONSE_MSG["permission"]["change"]["already_removed"],inline=False)
            await interaction.response.send_message(embed=embed)
            return
        config["discord_commands"]["admin"]["members"].pop(str(user.id))
        #configファイルを変更する
        await rewrite_config(config)
        await read_force_admin()
        embed.add_field(name="",value=RESPONSE_MSG["permission"]["change"]["remove_success"].format(user),inline=False)
        await interaction.response.send_message(embed=embed)
        admin_logger.info(f"exec force admin remove {user}")
    else:
        embed.add_field(name="",value=RESPONSE_MSG["permission"]["change"]["invalid_level"].format(USER_PERMISSION_MAX,level),inline=False)
        await interaction.response.send_message(embed=embed)
        admin_logger.info("invalid level")

#/permission <user>
@command_group_permission.command(name="view",description=COMMAND_DESCRIPTION[lang]["permission"]["view"])
async def view(interaction: discord.Interaction,user:discord.User,detail:bool):
    await print_user(permission_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title = f"/permission view {user} {detail}")
    COMMAND_MAX_LENGTH = max([len(key) for key in COMMAND_PERMISSION])
    advanced = "☑" if enable_advanced_features else "☐"
    value = {"admin":"☐","force_admin":"☐"}
    if await is_administrator(user): value["admin"] = f"☑({USER_PERMISSION_MAX})"
    value["force_admin"] = await user_permission(user)
    if detail:
        my_perm_level = await user_permission(user)
        can_use_cmd = {f"{key}":("☑" if COMMAND_PERMISSION[key] <= my_perm_level else "☐") + f"({COMMAND_PERMISSION[key]})" for key in COMMAND_PERMISSION}
        embed.add_field(name="",value=RESPONSE_MSG["permission"]["success"].format(user,advanced,value["admin"],value["force_admin"]) + "\n```\n"+"\n".join([f"{key.ljust(COMMAND_MAX_LENGTH)} : {value}" for key,value in can_use_cmd.items()]) + "\n```",inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        embed.add_field(name="",value=RESPONSE_MSG["permission"]["success"].format(user,advanced,value["admin"],value["force_admin"]),inline=False)
        await interaction.response.send_message(embed=embed)
    permission_logger.info("send permission info : " + str(user.id) + f"({user})")

tree.add_command(command_group_permission)
#--------------------



#/lang <lang>
@tree.command(name="lang",description=COMMAND_DESCRIPTION[lang]["lang"])
@app_commands.choices(
    language = [
        app_commands.Choice(name="en",value="en"),
        app_commands.Choice(name="ja",value="ja"),
    ]
)
async def language(interaction: discord.Interaction,language:str):
    """
    config の lang を変更する
    permission : discord 管理者 (2)
    lang : str "en"/"ja"
    """
    await print_user(lang_logger,interaction.user)
    global lang
    #管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["lang"]:
        await not_enough_permission(interaction,lang_logger)
        return
    #データの書き換え
    config["discord_commands"]["lang"] = language
    lang = config["discord_commands"]["lang"]
    #configファイルを変更する
    await rewrite_config(config)
    #textデータを再構築
    await get_text_dat()
    embed = ModifiedEmbeds.DefaultEmbed(title = f"/lang {language}")
    embed.add_field(name="",value=RESPONSE_MSG["lang"]["success"].format(language))
    await interaction.response.send_message(embed=embed)
    lang_logger.info("change lang to " + lang)

#/cmd serverin <server command>
#/cmd stdin 


#--------------------





#--------------------


# グループの設定
# root
command_group_cmd = app_commands.Group(name="cmd",description="cmd group")

serverin_logger = cmd_logger.getChild("serverin")
#--------------------



#--------------------




@command_group_cmd.command(name="serverin",description=COMMAND_DESCRIPTION[lang]["cmd"]["serverin"])
async def cmd(interaction: discord.Interaction,command:str):
    await print_user(serverin_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/cmd serverin {command}")
    global is_back_discord,cmd_logs
    #管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["cmd serverin"]: 
        await not_enough_permission(interaction,serverin_logger)
        return
    #サーバー起動確認
    if is_stopped_server(serverin_logger): 
        serverin_logger.info("is not running")
        embed.add_field(name="",value=RESPONSE_MSG["other"]["is_not_running"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    #コマンドの利用許可確認
    if command.split()[0] not in allow_cmd:
        serverin_logger.error('unknown command : ' + command)
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["serverin"]["skipped_cmd"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    serverin_logger.info("run command : " + command)
    try:
        process.stdin.write(command + "\n")
    except UnicodeEncodeError:
        serverin_logger.error(f"UnicodeEncodeError({command})")
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["serverin"]["unicode_encode_error"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    process.stdin.flush()
    #結果の返却を要求する
    is_back_discord = True
    #結果を送信できるまで待機
    while True:
        #何もなければ次を待つ
        if len(cmd_logs) == 0:
            await asyncio.sleep(0.1)
            continue
        embed.add_field(name="",value=cmd_logs.popleft(),inline=False)
        await interaction.response.send_message(embed=embed)
        break
#--------------------




#--------------------


stdin_logger = cmd_logger.getChild("stdin")

#サブグループstdinを作成
command_group_cmd_stdin = app_commands.Group(name="stdin",description="stdin group")
# サブグループを設定
command_group_cmd.add_command(command_group_cmd_stdin)


important_bot_file = [
    pathlib.Path(os.path.abspath(os.path.join(os.path.dirname(__file__),i))).resolve() for i in sys_files
] + [
    pathlib.Path(os.path.join(server_path,i)).resolve() for i in sys_files
]



# 重要ファイルでないか(最高権限要求するようなファイルかを確認)
async def is_important_bot_file(path):
    # 絶対パスを取得
    path = pathlib.Path(os.path.abspath(path)).resolve()
    # 重要ファイルの場合はTrueを返す
    for f in important_bot_file:
        if path == f or path.is_relative_to(f):
            return True
    return False
#--------------------


#--------------------



stdin_ls_logger = stdin_logger.getChild("ls")
@command_group_cmd_stdin.command(name="ls",description=COMMAND_DESCRIPTION[lang]["cmd"]["stdin"]["ls"])
async def ls(interaction: discord.Interaction, file_path: str):
    await print_user(stdin_ls_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/cmd stdin ls {file_path}")
    # 管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["cmd stdin ls"]:
        await not_enough_permission(interaction,stdin_ls_logger)
        return
    # server_path + file_path 閲覧パスの生成
    file_path = os.path.abspath(os.path.join(server_path,file_path))
    # 操作可能なパスか確認
    if not is_path_within_scope(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["invalid_path"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_ls_logger.info("invalid path -> " + file_path)
        return
    # 対象が存在するか
    if not os.path.exists(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["ls"]["file_not_found"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_ls_logger.info("file not found -> " + file_path)
        return
    # 対象がディレクトリであるか
    if not os.path.isdir(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["ls"]["not_directory"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_ls_logger.info("not directory -> " + file_path)
        return
    # lsコマンドを実行
    files = os.listdir(file_path)

    colorized_files = deque()
    
    for f in files:
        full_path = os.path.join(file_path, f)
        if os.path.isdir(full_path):
            # ディレクトリは青色
            colorized_files.append(f"\033[34m{f}\033[0m")
        elif os.path.islink(full_path):
            # シンボリックリンクは紫
            colorized_files.append(f"\033[35m{f}\033[0m")
        else:
            # 通常ファイルは緑
            colorized_files.append(f"\033[32m{f}\033[0m")
    formatted_files = "\n".join(colorized_files)
    stdin_ls_logger.info("list directory -> " + file_path)
    if len(formatted_files) > 900:
            with io.StringIO() as temp_file:
                temp_file.write("\n".join(files))
                temp_file.seek(0)
                # Discordファイルオブジェクトに変換して送信
                discord_file = discord.File(temp_file, filename="directory_list.txt")
                embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["ls"]["to_long"].format(file_path),inline=False)
                await interaction.response.send_message(
                    embed=embed,
                    file=discord_file
                )
    else:
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["ls"]["success"].format(file_path,formatted_files),inline=False)
        await interaction.response.send_message(embed=embed)

#--------------------


#--------------------


stdin_mk_logger = stdin_logger.getChild("mk")

# 以下のコマンドはserver_pathを起点としてそれ以下のファイルを操作する
# ファイル送信コマンドを追加
@command_group_cmd_stdin.command(name="mk",description=COMMAND_DESCRIPTION[lang]["cmd"]["stdin"]["mk"])
async def mk(interaction: discord.Interaction, file_path: str,file:discord.Attachment|None = None):
    await print_user(stdin_mk_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/cmd stdin mk {file_path} {file.filename if file is not None else ''}")
    # 管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["cmd stdin mk"]:
        await not_enough_permission(interaction,stdin_mk_logger)
        return
    #サーバー起動確認
    if is_running_server(stdin_mk_logger): 
        embed.add_field(name="",value=RESPONSE_MSG["other"]["is_running"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    # server_path + file_path にファイルを作成
    file_path = os.path.abspath(os.path.join(server_path,file_path))
    # 操作可能なパスか確認
    if not is_path_within_scope(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["invalid_path"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mk_logger.info("invalid path -> " + file_path)
        return
    # ファイルがリンクであれば拒否
    if os.path.islink(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["mk"]["is_link"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mk_logger.info("file is link -> " + file_path)
        return
    #ディレクトリであれば拒否
    if os.path.isdir(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["mk"]["is_directory"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mk_logger.info("file is directory -> " + file_path)
        return
    # 全ての条件を満たすがサーバー管理者権限を持たないまたは危険な操作を拒否されている状態で、重要ファイルを操作しようとしている場合
    if ((not await is_administrator(interaction.user)) or not enable_advanced_features) and await is_important_bot_file(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["permission_denied"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mk_logger.info("permission denied -> " + file_path)
        return
    else:
        # 空のファイルを作成
        open(file_path,"w").close()
        # ファイルをfile_pathに保存
        if file is not None:
            await file.save(file_path)
    stdin_mk_logger.info("create file -> " + file_path)
    embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["mk"]["success"].format(file_path),inline=False)
    await interaction.response.send_message(embed=embed)

#--------------------


#--------------------


stdin_rm_logger = stdin_logger.getChild("rm")

@command_group_cmd_stdin.command(name="rm",description=COMMAND_DESCRIPTION[lang]["cmd"]["stdin"]["rm"])
async def rm(interaction: discord.Interaction, file_path: str):
    await print_user(stdin_rm_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title=f"/cmd stdin rm {file_path}")
    # 管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["cmd stdin rm"]:
        await not_enough_permission(interaction,stdin_rm_logger)
        return
    #サーバー起動確認
    if is_running_server(stdin_rm_logger): 
        embed.add_field(name="",value=RESPONSE_MSG["other"]["is_running"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    # server_path + file_path のパスを作成
    file_path = os.path.abspath(os.path.join(server_path,file_path))
    # 操作可能なパスか確認
    if not is_path_within_scope(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["invalid_path"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_rm_logger.info("invalid path -> " + file_path)
        return
    # ファイルが存在しているかを確認
    if not os.path.exists(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["rm"]["file_not_found"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_rm_logger.info("file not found -> " + file_path)
        return
    # 該当のアイテムがファイルか
    if not os.path.isfile(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["not_file"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_rm_logger.info("not file -> " + file_path)
        return
    # 全ての条件を満たすがサーバー管理者権限を持たず、重要ファイルを操作しようとしている場合
    if (not await is_administrator(interaction.user) or not enable_advanced_features) and await is_important_bot_file(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["permission_denied"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_rm_logger.info("permission denied -> " + file_path)
        return
    # ファイルを削除
    os.remove(file_path)
    stdin_rm_logger.info("remove file -> " + file_path)
    embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["rm"]["success"].format(file_path),inline=False)
    await interaction.response.send_message(embed=embed)

#--------------------


#--------------------


stdin_mkdir_logger = stdin_logger.getChild("mkdir")

@command_group_cmd_stdin.command(name="mkdir",description=COMMAND_DESCRIPTION[lang]["cmd"]["stdin"]["mkdir"])
async def mkdir(interaction: discord.Interaction, dir_path: str):
    await print_user(stdin_mkdir_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/cmd stdin mkdir {dir_path}")
    # 管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["cmd stdin mkdir"]:
        await not_enough_permission(interaction,stdin_mkdir_logger)
        return
    # server_path + file_path のパスを作成
    dir_path = os.path.abspath(os.path.join(server_path,dir_path))
    # 操作可能なパスか確認
    if not is_path_within_scope(dir_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["invalid_path"].format(dir_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mkdir_logger.info("invalid path -> " + dir_path)
        return
    # 既に存在するか確認
    if os.path.exists(dir_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["mkdir"]["exists"].format(dir_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mkdir_logger.info("directory already exists -> " + dir_path)
        return
    # ディレクトリを作成
    os.makedirs(dir_path)
    stdin_mkdir_logger.info("create directory -> " + dir_path)
    embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["mkdir"]["success"].format(dir_path),inline=False)
    await interaction.response.send_message(embed=embed)

#--------------------


#--------------------


stdin_rmdir_logger = stdin_logger.getChild("rmdir")

@command_group_cmd_stdin.command(name="rmdir",description=COMMAND_DESCRIPTION[lang]["cmd"]["stdin"]["rmdir"])
async def rmdir(interaction: discord.Interaction, dir_path: str):
    await print_user(stdin_rmdir_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/cmd stdin rmdir {dir_path}")
    # 管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["cmd stdin rmdir"]:
        await not_enough_permission(interaction,stdin_rmdir_logger)
        return
    #サーバー起動確認
    if is_running_server(stdin_rmdir_logger): 
        embed.add_field(name="",value=RESPONSE_MSG["other"]["is_running"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    # server_path + file_path のパスを作成
    dir_path = os.path.abspath(os.path.join(server_path,dir_path))
    # 操作可能なパスか確認
    if not is_path_within_scope(dir_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["invalid_path"].format(dir_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_rmdir_logger.info("invalid path -> " + dir_path)
        return
    # 既に存在するか確認
    if not os.path.exists(dir_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["rmdir"]["not_exists"].format(dir_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_rmdir_logger.info("directory not exists -> " + dir_path)
        return
    # 全ての条件を満たすが、権限が足りず、対象が重要なディレクトリか確認
    if await is_important_bot_file(dir_path) and (not enable_advanced_features or (not await is_administrator(interaction.user))):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["permission_denied"].format(dir_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_rmdir_logger.info("permission denied -> " + dir_path)
        return
    # ディレクトリを削除
    rmtree(dir_path)
    stdin_rmdir_logger.info("remove directory -> " + dir_path)
    embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["rmdir"]["success"].format(dir_path),inline=False)
    await interaction.response.send_message(embed=embed)

#--------------------


#--------------------


stdin_mv_logger = stdin_logger.getChild("mv")

@command_group_cmd_stdin.command(name="mv",description=COMMAND_DESCRIPTION[lang]["cmd"]["stdin"]["mv"])
async def cmd_stdin_mv(interaction: discord.Interaction, path: str, dest: str):
    await print_user(stdin_mv_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/cmd stdin mv {path} {dest} ")
    # 権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["cmd stdin mv"]:
        await not_enough_permission(interaction,stdin_mv_logger)
        return
    #サーバー起動確認
    if is_running_server(stdin_mv_logger): 
        embed.add_field(name="",value=RESPONSE_MSG["other"]["is_running"],inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mv_logger.info("server is running")
        return
    # server_path + path のパスを作成
    path = os.path.abspath(os.path.join(server_path,path))
    # server_path + dest のパスを作成
    dest = os.path.abspath(os.path.join(server_path,dest))
    # 操作可能なパスか確認
    if not is_path_within_scope(path) or not is_path_within_scope(dest):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["invalid_path"].format(path,dest),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mv_logger.info("invalid path -> " + path + " or " + dest)
        return
    # ファイルが存在しているかを確認
    if not os.path.exists(path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["mv"]["file_not_found"].format(path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mv_logger.info("file not found -> " + path)
        return
    # 該当のアイテムがファイルかディレクトリ
    if not os.path.isfile(path) and not os.path.isdir(path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["not_file_or_directory"].format(path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mv_logger.info("not file -> " + path)
        return
    # 移動先がディレクトリではない
    if not os.path.isdir(os.path.dirname(dest)):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["not_directory"].format(dest),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mv_logger.info("not directory -> " + dest)
        return
    # 全ての条件を満たすがサーバー管理者権限を持たず、重要ファイルを操作しようとしている場合
    if (not await is_administrator(interaction.user) or not enable_advanced_features) and (await is_important_bot_file(path) or await is_important_bot_file(dest)):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["permission_denied"].format(path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_mv_logger.info("permission denied -> " + path + " or " + dest)
        return
    # ファイルを移動
    shutil_move(path,dest)
    stdin_mv_logger.info("move file -> " + path + " -> " + dest)
    embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["mv"]["success"].format(path,dest),inline=False)
    await interaction.response.send_message(embed=embed)
#--------------------


#--------------------


stdin_send_discord_logger = stdin_logger.getChild("send-discord")

# # !open ./repos/discord/command/cmd/stdin/send_discord/fileio.py

#--------------------



class SendDiscordSelfServer:
    # クラススコープで状態を保持
    _download_registry: dict[str, tuple[str, float]] = {}
    _lock = asyncio.Lock()
    _ttl_default = 300  # 5分

    @classmethod
    async def register_download(cls, directory_path: str, ttl_seconds: int = None) -> str:
        # if not os.path.isdir(directory_path):
        #     raise ValueError("指定されたパスはディレクトリではありません")
        ttl = ttl_seconds if ttl_seconds else cls._ttl_default
        token = uuid.uuid4().hex
        expire_at = datetime.now() + timedelta(seconds=ttl)
        # ファイル容量がbits_capacityを超えるなら、ダウンロード不可
        if (dir_size := await get_directory_size(directory_path) if os.path.isdir(directory_path) else os.path.getsize(directory_path)) > send_discord_bits_capacity:
            return False, [1, str(dir_size),str(send_discord_bits_capacity)]
        async with cls._lock:
            cls._download_registry[token] = (directory_path, expire_at)
        stdin_send_discord_logger.info("register download -> " + directory_path + f"({dir_size} Bytes)")
        return True, f"http://{requests.get('https://api.ipify.org').text}:{web_port}/download/{token}"

    @classmethod
    async def _cleanup_loop(cls):
        while True:
            now = datetime.now()
            async with cls._lock:
                expired = [t for t, (_, exp) in cls._download_registry.items() if now > exp]
                for t in expired:
                    del cls._download_registry[t]
                    stdin_send_discord_logger.info("cleanup download -> " + t)
            await asyncio.sleep(30)

    @classmethod
    async def download(cls, token: str):
        async with cls._lock:
            entry = cls._download_registry.pop(token, None)
        if not entry:
            stdin_send_discord_logger.info("download not found -> " + token)
            raise HTTPException(status_code=404, detail="リンクが無効または既に使用されました")
        directory_path, expire_at = entry
        if 	datetime.now() > expire_at > expire_at:
            stdin_send_discord_logger.info("download expired -> " + token)
            raise HTTPException(status_code=410, detail="このリンクは期限切れです")

        # zipstreamでリアルタイムZIP
        z = zipstream.ZipStream()
        z.add_path(directory_path)
        # for root, _, files in os.walk(directory_path):
        #     for file in files:
        #         full_path = os.path.join(root, file)
        #         arcname = os.path.relpath(full_path, start=directory_path)
        #         z.add(, arcname)
        stdin_send_discord_logger.info("download -> " + directory_path)
        filename = os.path.basename(directory_path) or "download"
        return StreamingResponse(
            z,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}.zip"'}
        )

    @classmethod
    def create_app(cls) -> FastAPI:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            task = asyncio.create_task(cls._cleanup_loop())
            yield
            task.cancel()

        app = FastAPI(lifespan=lifespan)
        app.add_api_route("/download/{token}", cls.download, methods=["GET"])
        return app

#--------------------


#--------------------


@command_group_cmd_stdin.command(name="send-discord",description=COMMAND_DESCRIPTION[lang]["cmd"]["stdin"]["send-discord"])
async def send_discord(interaction: discord.Interaction, path: str):
    await print_user(stdin_send_discord_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/cmd stdin send-discord {path}")
    file_path = os.path.abspath(os.path.join(server_path,path))  # ファイルのパス
    file_name = os.path.basename(file_path)
    file_size_limit = 9 * 1024 * 1024  # 9MB
    file_size_limit_web = send_discord_bits_capacity  # 2GBを超えた場合file.ioでも無理なのでエラー
    # 権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["cmd stdin send-discord"]:
        await not_enough_permission(interaction,stdin_send_discord_logger)
        return
    # ファイルが存在しているかを確認
    if not os.path.exists(file_path):
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["send-discord"]["file_not_found"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_send_discord_logger.info("file not found -> " + file_path)
        return
    # パスが許可されているかを確認 or .tokenなら常に拒否
    if not is_path_within_scope(file_path) or os.path.basename(file_path) == ".token":
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["invalid_path"].format(file_path),inline=False)
        await interaction.response.send_message(embed=embed)
        stdin_send_discord_logger.info("invalid path -> " + file_path)
        return
    # if send_discord_mode == "fileio":
    #     await send_discord_fileio(interaction, embed, stdin_send_discord_logger, file_size_limit_web, file_size_limit,file_path, file_name)
    link = await SendDiscordSelfServer.register_download(file_path)
    if link[0]:
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["send-discord"]["send_myserver_link"].format(interaction.user.id, link[1], file_path),inline=False)
    else:
        # エラーコードを読む
        if link[1][0] == 1:
            embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["send-discord"]["send_capacity_error"].format(interaction.user.id, link[1][1], link[1][2]),inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
#--------------------


#--------------------


#--------------------


stdin_wget_logger = stdin_logger.getChild("wget")

@command_group_cmd_stdin.command(name="wget",description=COMMAND_DESCRIPTION[lang]["cmd"]["stdin"]["wget"])
async def wget(interaction: discord.Interaction,url:str,path:str = "mi_dl_file.tmp"):
    await print_user(stdin_wget_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/cmd stdin wget {url} {path} ")
    # 権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["cmd stdin wget"]: 
        await not_enough_permission(interaction,stdin_wget_logger)
        return
    save_path = os.path.abspath(os.path.join(server_path,path))
    # 既にファイルが存在しているか確認
    if os.path.exists(save_path):
        stdin_wget_logger.info("file already exists -> " + save_path)
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["wget"]["already_exists"].format(path),inline=False)
        await interaction.response.send_message(embed=embed)
        return
    # pathが操作可能か確認
    if not is_path_within_scope(save_path):
        stdin_wget_logger.info("invalid path -> " + save_path)
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["invalid_path"].format(save_path),inline=False)
        await interaction.response.send_message(embed=embed)
        return
    # 管理者権限を持っていなくて、重要ファイルをダウンロードする場合は拒否
    if (not await is_administrator(interaction.user) or not enable_advanced_features) and await is_important_bot_file(save_path):
        stdin_wget_logger.info("permission denied -> " + save_path)
        embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["permission_denied"].format(save_path),inline=False)
        await interaction.response.send_message(embed=embed)
        return
    # URLからファイルをダウンロード
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    stdin_wget_logger.info("download failed -> " + url)
                    embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["wget"]["download_failed"].format(url),inline=False)
                    await interaction.response.send_message(embed=embed)
                    return

                # ファイルを保存
                with open(save_path, 'wb') as file:
                    file.write(await response.read())
        except Exception as e:
            stdin_wget_logger.info("download failed -> " + url + f"({e})")
            embed.add_field(name="",value=f"invalid url -> ({e})",inline=False)
            await interaction.response.send_message(embed=embed)
            return
    stdin_wget_logger.info("download success -> " + url + " to " + save_path)
    embed.add_field(name="",value=RESPONSE_MSG["cmd"]["stdin"]["wget"]["download_success"].format(url,save_path),inline=False)
    await interaction.response.send_message(embed=embed)
#--------------------



#--------------------


# コマンドを追加
tree.add_command(command_group_cmd)
#--------------------


#--------------------



#--------------------


command_group_backup = app_commands.Group(name="backup",description="backup group")


#--------------------


backup_create_logger = backup_logger.getChild("create")

#/backup()
@command_group_backup.command(name="create",description=COMMAND_DESCRIPTION[lang]["backup"]["create"])
async def backup(interaction: discord.Interaction,path:str):
    from_backup = normalize_path(os.path.join(server_path,path))
    world_name = path
    await print_user(backup_logger,interaction.user)
    global exist_files, copyed_files
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/backup create {world_name}")
    #管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["backup create"]:
        await not_enough_permission(interaction,backup_logger) 
        return
    #サーバー起動確認
    if is_running_server(backup_logger): 
        embed.add_field(name="",value=RESPONSE_MSG["other"]["is_running"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    # 操作可能パスかを判定
    if not is_path_within_scope(from_backup) or await is_important_bot_file(from_backup):
        backup_logger.error("path not allowed : " + from_backup)
        embed.add_field(name="",value = RESPONSE_MSG["backup"]["create"]["path_not_allowed"] + ":" + from_backup,inline=False)
        await interaction.response.send_message(embed=embed)
        return
    backup_logger.info('backup started')
    #server_path + world_namの存在確認
    if os.path.exists(from_backup):
        await interaction.response.send_message(embed=embed)
        # discordにcopyed_files / exist_filesをプログレスバーで
        await dircp_discord(from_backup,backup_path + "/",interaction,embed)
        backup_logger.info('backup done')
    else:
        backup_logger.error('data not found : ' + from_backup)
        embed.add_field(name="",value=RESPONSE_MSG["backup"]["create"]["data_not_found"] + ":" + from_backup,inline=False)
        await interaction.response.send_message(embed=embed,ephemeral=True)
#--------------------


#--------------------



backup_apply_logger = backup_logger.getChild("apply")

async def server_backup_list(interaction: discord.Interaction, current: str):
    current = current.translate(str.maketrans("/\\:","--_"))
    #全てのファイルを取得
    backups = os.listdir(backup_path)
    # current と一致するものを返す & logファイル & 25個制限を実装
    logfiles = [i for i in backups if current in i][-25:]
    # open("./tmp.txt","w").write("\n".join(logfiles))
    return [
        app_commands.Choice(name = i,value = i) for i in logfiles
    ]

@command_group_backup.command(name="apply",description="apply backup")
@app_commands.autocomplete(witch=server_backup_list)
async def backup_apply(interaction:discord.Interaction, witch:str, path:str = ""):
    await print_user(backup_apply_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/backup apply {witch} {path}")
    #管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["backup apply"]: 
        await not_enough_permission(interaction,backup_apply_logger)
        return
    #サーバー起動確認
    if is_running_server(backup_apply_logger): 
        embed.add_field(name="",value=RESPONSE_MSG["other"]["is_running"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    # dirの存在確認
    if not os.path.exists(os.path.join(server_path,path)):
        backup_apply_logger.error('data not found : ' + os.path.join(server_path,path))
        embed.add_field(name="",value = RESPONSE_MSG["backup"]["apply"]["path_not_found"] + ":" + os.path.join(server_path,path),inline=False)
        await interaction.response.send_message(embed=embed)
        return
    # 操作可能パスかを判定
    if not is_path_within_scope(os.path.join(server_path,path)) or await is_important_bot_file(os.path.join(server_path,path)):
        backup_logger.error("path not allowed : " + os.path.join(server_path,path))
        embed.add_field(name="",value = RESPONSE_MSG["backup"]["apply"]["path_not_allowed"] + ":" + os.path.join(server_path,path),inline=False)
        await interaction.response.send_message(embed=embed)
        return
    backup_apply_logger.info('backup apply started' + " -> " + witch + " to " + os.path.join(server_path,path,witch))
    await interaction.response.send_message(embed=embed)
    # dircp_discordを用いて進捗を出しつつ、コピーする
    await dircp_discord(os.path.join(backup_path,witch),os.path.join(server_path,path),interaction,embed)
    backup_apply_logger.info('backup apply done')
    
#--------------------


tree.add_command(command_group_backup)

#--------------------



#--------------------


#/update
@tree.command(name="update",description=COMMAND_DESCRIPTION[lang]["update"])
async def update(interaction: discord.Interaction, is_force: bool = False):
    await print_user(update_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/update {is_force}")
    #サーバー起動確認
    if is_running_server(update_logger): 
        embed.add_field(name="",value=RESPONSE_MSG["other"]["is_running"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    #サーバー管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["update"]: 
        await not_enough_permission(interaction,update_logger)
        return
    #py_builder.pyを更新
    await update_self_if_commit_changed(interaction=interaction,embed=embed,text_pack=RESPONSE_MSG["update"],sender=send_discord_message_or_edit,is_force = is_force)
#--------------------



#--------------------


# グループの設定
# root
command_group_announce = app_commands.Group(name="announce",description="send messege to discord")


#--------------------


@command_group_announce.command(name="embed",description=COMMAND_DESCRIPTION[lang]["announce"]["embed"])
async def embed(interaction: discord.Interaction, file: discord.Attachment|None = None, txt: str = ""):
    await print_user(announce_logger,interaction.user)
    return_embed = ModifiedEmbeds.DefaultEmbed(title= f"/embed {file.filename if file is not None else ''} {txt}")
    embed = ModifiedEmbeds.DefaultEmbed(title= f"")
    # 権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["announce embed"]: 
        await not_enough_permission(interaction,announce_logger)
        return
    # ファイルとテキストの両方が存在する場合はエラー
    if file is not None and txt != "":
        return_embed.add_field(name="",value=RESPONSE_MSG["cmd"]["announce"]["embed"]["exist_file_and_txt"],inline=False)
        await interaction.response.send_message(embed=return_embed)
        announce_logger.info("file and txt exist")
        return
    # ファイルがある場合はファイルを展開してtxtに代入
    if file is not None:
        try:
            txt = (await file.read()).decode("utf-8")
        except:
            return_embed.add_field(name="",value=RESPONSE_MSG["announce"]["embed"]["decode_error"],inline=False)
            await interaction.response.send_message(embed=return_embed)
            announce_logger.info("file decode error")
            return
    # テキストで送られてるなら\\nを改行に変換
    if txt:
        txt = txt.replace("\\n","\n")
        return_embed.add_field(name="",value=RESPONSE_MSG["announce"]["embed"]["replace_slash_n"],inline=False)
    # 内容が空なら
    if txt == "":
        return_embed.add_field(name="",value=RESPONSE_MSG["announce"]["embed"]["empty"],inline=False)
        await interaction.response.send_message(embed=return_embed)
        announce_logger.info("txt is empty")
        return
    send_data, other_dat = await parse_mimd(txt)
    announce_logger.info("parsed txt")
    # embedに追加
    embed.title = other_dat["title"]
    for items in send_data:
        embed.add_field(name=items["name"],value=items["value"],inline=False)
    return_embed.add_field(name="",value=RESPONSE_MSG["announce"]["embed"]["success"],inline=False)
    # embedを送信
    await interaction.response.send_message(embed=return_embed,ephemeral=True)
    # 同じchidにembedを送信
    await interaction.channel.send(embed=embed)
    announce_logger.info('embed sent')



#--------------------


tree.add_command(command_group_announce)
#--------------------


#/replace <py file>
# @tree.command(name="replace",description=COMMAND_DESCRIPTION[lang]["replace"])
# async def replace(interaction: discord.Interaction,py_file:discord.Attachment):
#     await print_user(replace_logger,interaction.user)
#     embed = ModifiedEmbeds.DefaultEmbed(title= f"/replace {py_file.filename}")
#     #デフォルトでコマンドを無効に
#     if not allow["replace"]:
#         embed.add_field(name=RESPONSE_MSG["replace"]["not_allow"]["name"],value=RESPONSE_MSG["replace"]["not_allow"]["value"],inline=False)
#         await interaction.response.send_message(embed=embed)
#         return
#     #管理者権限を要求
#     if await user_permission(interaction.user) < COMMAND_PERMISSION["replace"]:
#         await not_enough_permission(interaction,replace_logger)
#         return
#     #サーバー起動確認
#     if is_running_server(replace_logger): 
#         embed.add_field(name="",value=RESPONSE_MSG["other"]["is_running"],inline=False)
#         await interaction.response.send_message(embed=embed)
#         return
#     replace_logger.info('replace started')
#     # ファイルをすべて読み込む
#     with open(temp_path + "/new_source.py","w",encoding="utf-8") as f:
#         f.write((await py_file.read()).decode("utf-8").replace("\r\n","\n"))
#     # discordにコードを置き換える
#     replace_logger.info('replace done')
#     embed.add_field(name="",value=RESPONSE_MSG["replace"]["progress"],inline=False)
#     await interaction.response.send_message(embed=embed)
#     response = await interaction.original_response()
#     #interaction id を保存
#     msg_id = str(response.id)
#     channel_id = str(interaction.channel_id)
#     replace_logger.info("call update.py")
#     replace_logger.info('replace args : ' + msg_id + " " + channel_id)
#     os.execv(sys.executable,["python3",now_path + "/mikanassets/" + "update.py",temp_path + "/new_source.py",msg_id,channel_id,now_file])

#/ip
@tree.command(name="ip",description=COMMAND_DESCRIPTION[lang]["ip"])
async def ip(interaction: discord.Interaction):
    await print_user(ip_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/ip")
    if await user_permission(interaction.user) < COMMAND_PERMISSION["ip"]:
        await not_enough_permission(interaction,ip_logger)
        return
    if not allow["ip"]:
        embed.add_field(name="",value=RESPONSE_MSG["ip"]["not_allow"],inline=False)
        await interaction.response.send_message(embed=embed)
        ip_logger.error('ip is not allowed')
        return
    # ipをget
    try:
        addr = requests.get("https://api.ipify.org")
    except:
        ip_logger.error('get ip failed')
        embed.add_field(name="",value=RESPONSE_MSG["ip"]["get_ip_failed"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    if SUBPROCESS_PROCESS_TYPE == "mc-server":
        ip_logger.info('get ip : ' + addr.text + ":" + properties["server-port"])
        embed.add_field(name=RESPONSE_MSG["ip"]["msg_startwith"] + addr.text + ":" + properties["server-port"],value=f"(ip:{addr.text} port(ポート):{properties['server-port']})",inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        ip_logger.info('get ip : ' + addr.text)
        embed.add_field(name="",value=RESPONSE_MSG["ip"]["msg_startwith"] + addr.text,inline=False)
        await interaction.response.send_message(embed=embed)


async def get_log_files_choice_format(interaction: discord.Interaction, current: str):
    current = current.translate(str.maketrans("/\\:","--_"))
    #全てのファイルを取得
    s_logfiles = os.listdir(server_path + "logs/")
    a_logfiles = os.listdir(now_path + "/logs/")
    logfiles = (s_logfiles + a_logfiles)
    # current と一致するものを返す & logファイル & 25個制限を実装
    logfiles = [i for i in logfiles if current in i and i.endswith(".log")][-25:]
    # open("./tmp.txt","w").write("\n".join(logfiles))
    return [
        app_commands.Choice(name = i,value = i) for i in logfiles
    ]


#/log <filename>
# filename : ログファイル名
# filename == None -> 最新のログ10件
# filename != None -> server_path + "logs/" または now_path + "logs/"の中を候補表示する
@tree.command(name="logs",description=COMMAND_DESCRIPTION[lang]["logs"])
@app_commands.autocomplete(filename = get_log_files_choice_format)
async def logs(interaction: discord.Interaction,filename:str = None):
    await print_user(log_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/logs {filename}")
    #管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["logs"]: 
        await not_enough_permission(interaction,log_logger)
        return
    # discordにログを送信
    if filename is None:
        # 2000文字こ超えない最長のログを取得
        send_msg = []
        send_length = 0
        for i in log_msg:
            send_length += len(i)
            send_msg.append(i)
            while True:
                if send_length > 1900:
                    delete = send_msg.pop(0)
                    send_length -= len(delete)
                else:
                    break
        # embed.add_field(name="",value="```ansi\n" + "\n".join(send_msg) + "\n```",inline=False)
        await interaction.response.send_message("```ansi\n" + "\n".join(send_msg) + "\n```")
    else:
        if "/" in filename or "\\" in filename or "%" in filename:
            log_logger.error('invalid filename : ' + filename + "\n" + f"interaction user / id：{interaction.user} {interaction.user.id}")
            embed.add_field(name="",value=RESPONSE_MSG["logs"]["cant_access_other_dir"],inline=False)
            await interaction.response.send_message(embed=embed)
            return
        elif not filename.endswith(".log"):
            log_logger.error('invalid filename : ' + filename + "\n" + f"interaction user / id：{interaction.user} {interaction.user.id}")
            embed.add_field(name="",value=RESPONSE_MSG["logs"]["not_found"],inline=False)
            await interaction.response.send_message(embed=embed)
            return
        elif filename.startswith("server"):
            filename = server_path + "logs/" + filename
        elif filename.startswith("all"):
            filename = now_path + "/logs/" + filename
        else:
            filename = server_path + "logs/" + filename
            if not os.path.exists(filename):
                if os.path.exists(now_path + "/logs/" + filename):
                    filename = now_path + "/logs/" + filename
                else:
                    log_logger.error('invalid filename : ' + filename + "\n" + f"interaction user / id：{interaction.user} {interaction.user.id}")
                    embed.add_field(name="",value=RESPONSE_MSG["logs"]["not_found"],inline=False)
                    await interaction.response.send_message(embed=embed)
                    return
        #ファイルを返却
        await interaction.response.send_message(file=discord.File(filename))
    log_ = "Server logs" if filename is None else filename
    log_logger.info(f"sended logs -> {log_}")


def gen_web_token():
    from random import choices
    from string import ascii_letters, digits
    return ''.join(choices(ascii_letters + digits, k=12))

#/tokengen トークンを生成する
@tree.command(name="tokengen",description=COMMAND_DESCRIPTION[lang]["tokengen"])
async def tokengen(interaction: discord.Interaction):
    await print_user(token_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/tokengen")
    #権限レベルを確認
    if await user_permission(interaction.user) < COMMAND_PERMISSION["tokengen"]:
        await not_enough_permission(interaction,token_logger)
        return
    new_token = gen_web_token()
    embed.add_field(name=RESPONSE_MSG["tokengen"]["success"].format(""),value=new_token,inline=False)
    await interaction.response.send_message(embed=embed,ephemeral=True)
    token_logger.info('token sent')
    #トークンをファイルに書き込む
    dat_token = {"token":new_token, "deadline":(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")}
    web_tokens.append(dat_token)
    with open(now_path + "/mikanassets/web/usr/tokens.json","r",encoding="utf-8") as f:
        item = json.load(f)
        item["tokens"].append(dat_token)
    with open(now_path + "/mikanassets/web/usr/tokens.json","w",encoding="utf-8") as f:
        json.dump(item,f,indent=4,ensure_ascii=False)
    token_logger.info('token added : ' + str(dat_token))


#--------------------


command_group_terminal = app_commands.Group(name="terminal",description="terminal group")

async def change_terminal_ch(channel: int | bool, logger: logging.Logger):    
    global where_terminal
    #terminalを無効化
    where_terminal = channel
    config["discord_commands"]["terminal"]["discord"] = where_terminal
    logger.info(f"terminal setting -> {where_terminal}")
    await rewrite_config(config=config)


#--------------------


terminal_set_logger = terminal_logger.getChild("set")

#/terminal
@command_group_terminal.command(name="set",description=COMMAND_DESCRIPTION[lang]["terminal"]["set"])
async def terminal_set(interaction: discord.Interaction, channel:discord.TextChannel = None):
    global where_terminal
    await print_user(terminal_set_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/terminal set {channel}")
    # 権限レベルが足りていないなら
    if await user_permission(interaction.user) < COMMAND_PERMISSION["terminal set"]:
        await not_enough_permission(interaction,terminal_set_logger)
        return
    #発言したチャンネルをwhere_terminalに登録
    await change_terminal_ch(channel.id if channel else interaction.channel.id, terminal_set_logger)
    embed.add_field(name="",value=RESPONSE_MSG["terminal"]["success"].format(where_terminal),inline=False)
    await interaction.response.send_message(embed=embed)
#--------------------


#--------------------


terminal_delete_logger = terminal_logger.getChild("delete")

#/terminal
@command_group_terminal.command(name="del",description=COMMAND_DESCRIPTION[lang]["terminal"]["del"])
async def terminal_set(interaction: discord.Interaction):
    global where_terminal
    await print_user(terminal_delete_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/terminal del")
    # 権限レベルが足りていないなら
    if await user_permission(interaction.user) < COMMAND_PERMISSION["terminal del"]:
        await not_enough_permission(interaction,terminal_delete_logger)
        return
    #発言したチャンネルをwhere_terminalに登録
    await change_terminal_ch(False, terminal_delete_logger)
    embed.add_field(name="",value=RESPONSE_MSG["terminal"]["success"].format(where_terminal),inline=False)
    await interaction.response.send_message(embed=embed)

#--------------------


tree.add_command(command_group_terminal)

#--------------------



#--------------------


async def get_process_memory(process: subprocess.Popen | None) -> dict:
    MB = 1024**2
    # このプログラムの利用メモリを取得する
    origin_process = psutil.Process(os.getpid())
    origin_mem = origin_process.memory_info().rss / MB
    # サーバープロセスの利用メモリを取得する
    if process is not None:
        childs = psutil.Process(process.pid).children(recursive=True)
        server_mem = sum([psutil.Process(child.pid).memory_info().wset for child in childs]) / MB
        server_mem += (psutil.Process(process.pid)).memory_info().wset / MB
    else:
        server_mem = 0
    return {
        "origin_mem": origin_mem,
        "server_mem": server_mem
    }

async def get_process_cpu(process: subprocess.Popen) -> float:
    return psutil.cpu_percent(interval=1.0)

async def get_thread_cpu_usage(pid : int, interval=1.0, is_self = False):
    # 全てのスレッドを取得
    process = psutil.Process(pid)
    # 初回のCPU時間を取得
    thread_cpu_times = {t.id: t.user_time + t.system_time for t in process.threads()}
    # 1秒間のCPU使用率を取得
    await asyncio.sleep(interval)
    # CPU時間の差分を取得
    tmp_cpu_times = {t.id: t.user_time + t.system_time for t in process.threads()}
    for tid in thread_cpu_times:
        try:
            thread_cpu_times[tid] = tmp_cpu_times[tid] - thread_cpu_times[tid]
        except KeyError:
            thread_cpu_times[tid] = 0
    # 全体のCPU時間を取得
    sum_cpu_times = sum(thread_cpu_times.values())
    # is_selfがtrueであれば、自身の名前に置き換える
    if is_self:
    # スレッド名の辞書を作成
        items = {thread.ident: thread.name for thread in threading.enumerate()}
        # 一時辞書を用意（ループ中の辞書変更を防ぐ）
        updated_thread_cpu_times = {}
        # IDをスレッド名に変換
        for thread_id, cpu_time in thread_cpu_times.items():
            if thread_id in items:
                updated_thread_cpu_times[items[thread_id]] = cpu_time
            else:
                updated_thread_cpu_times[thread_id] = cpu_time
        # 名前のないスレッドを "NoName Thread x" にする
        no_name_thread_count = 1
        final_thread_cpu_times = {}
        for key, cpu_time in updated_thread_cpu_times.items():
            if isinstance(key, int):  # スレッドIDが残っている場合
                final_thread_cpu_times[f"NoName {no_name_thread_count}"] = cpu_time
                no_name_thread_count += 1
            else:
                final_thread_cpu_times[key] = cpu_time
        # 更新後の辞書を適用
        thread_cpu_times = final_thread_cpu_times
    # 全体のCPU時間を取得
    sum_cpu_times = sum(thread_cpu_times.values())

    status_logger.debug(f"thread_cpu_times: {thread_cpu_times}")
    status_logger.debug(f"sum_cpu_times: {sum_cpu_times}")

    # threadごとのパーセントを計算
    cpu_usage = {
        tid: (thread_cpu_times[tid] / sum_cpu_times) * 100 if sum_cpu_times != 0 else 0
        for tid in thread_cpu_times
    }

    status_logger.debug(f"cpu_usage: {cpu_usage}")
    
    process_cpu = await get_process_cpu(process)

    status_logger.debug(f"process_cpu: {process_cpu}")

    # CPU使用率を計算
    cpu_usage = {
        tid : cpu_usage[tid] / 100 * process_cpu
        for tid in cpu_usage
    }

    status_logger.debug(f"cpu_usage: {cpu_usage}")

    return cpu_usage

async def check_response(url:str = "http://127.0.0.1"):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    sys_logger.info("Waitress server is running.")
                    return True
                else:
                    sys_logger.info(f"Server returned status code: {response.status}")
                    return False
    except aiohttp.ClientError as e:
        sys_logger.info(f"Server is not running: {e}")
        return False

#/status
@tree.command(name="status",description=COMMAND_DESCRIPTION[lang]["status"])
async def status(interaction: discord.Interaction):
    await print_user(status_logger,interaction.user)
    await interaction.response.defer()
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/status")
    # 権限の確認
    if await user_permission(interaction.user) < COMMAND_PERMISSION["status"]:
        await not_enough_permission(interaction,status_logger)
        return
    
    # プログラムの利用メモリを取得する
    memorys = await get_process_memory(process)
    embed.add_field(name=RESPONSE_MSG["status"]["mem_title"],value=RESPONSE_MSG["status"]["mem_value"].format(round(memorys["origin_mem"],2)) + "\n" + RESPONSE_MSG["status"]["mem_server_value"].format(round(memorys["server_mem"],2)))

    status_logger.info(f"get memory -> process {memorys['origin_mem']}, server {memorys['server_mem']}")

    # online状態を取得する
    is_server_online = "🟢" if process is not None and process.poll() is None else "🔴"
    is_waitress_online = "🟢" if await check_response(f"http://127.0.0.1:{web_port}") else "🔴"
    is_bot_online = "🟢"
    embed.add_field(name=RESPONSE_MSG["status"]["online_title"],value=RESPONSE_MSG["status"]["online_value"].format(is_server_online, is_waitress_online, is_bot_online))

    # SERVER PROCESS CPUの利用率を取得する
    if process is not None:
        cpu_usage = {server_name :(await get_process_cpu(process.pid))}
    else:
        cpu_usage = {"NULL": "NULL"}
    send_str = ["Server"]
    send_str += [RESPONSE_MSG["status"]["cpu_value_proc"].format(cpu_usage[key], key) for key in cpu_usage]
    # BOT PROCESS CPUの利用率を取得する
    cpu_usage = await get_thread_cpu_usage(os.getpid(), is_self=True)
    send_str += ["Self"]
    send_str += [RESPONSE_MSG["status"]["cpu_value_thread"].format(cpu_usage[key], key) for key in cpu_usage]
    embed.add_field(name=RESPONSE_MSG["status"]["cpu_title"],value="\n".join(send_str), inline=False)

    status_logger.info(f"get cpu usage -> {' '.join(send_str)}")

    # 基本情報を記載
    embed.add_field(name=RESPONSE_MSG["status"]["base_title"],value=RESPONSE_MSG["status"]["base_value"].format(platform.system() + " " + platform.release(), sys.version, get_version()), inline=True)

    await interaction.edit_original_response(embed=embed)
    status_logger.info('status command end')
#--------------------


#/help
@tree.command(name="help",description=COMMAND_DESCRIPTION[lang]["help"])
async def help(interaction: discord.Interaction):
    await print_user(help_logger,interaction.user)
    await interaction.response.send_message(embed=send_help)
    help_logger.info('help sent')

#/exit
@tree.command(name="exit",description=COMMAND_DESCRIPTION[lang]["exit"])
async def exit(interaction: discord.Interaction):
    await print_user(exit_logger,interaction.user)
    embed = ModifiedEmbeds.DefaultEmbed(title= f"/exit")
    #管理者権限を要求
    if await user_permission(interaction.user) < COMMAND_PERMISSION["exit"]: 
        await not_enough_permission(interaction,exit_logger)
        return
    #サーバが動いているなら終了
    if is_running_server(exit_logger): 
        embed.add_field(name="",value=RESPONSE_MSG["other"]["is_running"],inline=False)
        await interaction.response.send_message(embed=embed)
        return
    embed.add_field(name="",value=RESPONSE_MSG["exit"]["success"],inline=False)
    await interaction.response.send_message(embed=embed)
    exit_logger.info('exit')
    await client.close()
    #waitressサーバーを終了

    sys.exit()

# 拡張コマンドを読み込む

#--------------------



def get_process():
    return process

def append_tasks_func(func):
    extension_tasks_func.append(func)
    return

is_write_server_block = False
def write_server_in(command: str):
    global is_write_server_block
    if is_write_server_block:
        return False, "write_server_block"
    is_write_server_block = True
    # サーバーが動いていれば、コマンドを送る
    if is_stopped_server(sys_logger):
        is_write_server_block = False
        return False, "server_is_not_running"
    process.stdin.write(command + "\n")
    process.stdin.flush()
    is_write_server_block = False
    return True, "success"
#--------------------


#--------------------

base_extension_logger.info("search extension commands")
extension_commands_group = None
extension_logger = None
def read_extension_commands():
    global extension_commands_group,extension_logger
    extension_commands_groups = deque()
    extension_path = normalize_path(now_path + "/mikanassets/extension")
    sys_logger.info("read extension commands ->" + extension_path)
    # 拡張moduleに追加コマンドが存在すればするだけ読み込む(mikanassets/extension/<拡張名>/commands.py)
    for file in os.listdir(extension_path):
        extension_file_path = normalize_path(extension_path + "/" + file)
        extension_command_file_path = normalize_path(extension_file_path + "/commands.py")
        if os.path.isdir(now_path + "/mikanassets/extension/" + file):
            sys_logger.info("read extension commands ->" + extension_file_path)
            if os.path.exists(extension_command_file_path):
                # <拡張名>コマンドグループを作成
                extension_commands_group = app_commands.Group(name="extension-" + file,description="This commands group is extention.\nUse this code at your own risk." + file)
                extension_commands_groups.append(extension_commands_group)
                # 拡張moduleが/mikanassets/extension/<拡張名>/commans.pyにある場合は読み込む
                try:
                    extension_logger = base_extension_logger.getChild(file)
                    importlib.import_module("mikanassets.extension." + file + ".commands")
                    # コマンドを追加
                    tree.add_command(extension_commands_group)
                    sys_logger.info("read extension commands success -> " + extension_command_file_path)
                except Exception as e:
                    sys_logger.info("cannot read extension commands " + extension_command_file_path + f"({e})")
            else:
                sys_logger.info("not exist extension commands file in " + extension_command_file_path)
        else:
            sys_logger.info("not directory -> " + extension_file_path)

    unti_GC_obj.append(extension_commands_groups)

extension_path = normalize_path(now_path + "/mikanassets/extension")
# mikanassets/extension/<extension_dir>にディレクトリが存在すれば
if os.path.exists(extension_path):
    if len(os.listdir(extension_path)) > 0:
        # 拡張コマンドを読み込む
        read_extension_commands()
    else:
        sys_logger.info("no extension commands in " + extension_path)
del extension_commands_group
del extension_path

#--------------------


import traceback

#コマンドがエラーの場合
@tree.error
async def on_error(interaction: discord.Interaction, error: Exception):
    try:
        sys_logger.error(error)
        sys_logger.error(traceback.format_exc())
        message = RESPONSE_MSG["error"]["error_base"] + str(error)
        # すでにdefer/応答済みのinteractionにresponse.send_messageすると
        # InteractionResponded/Unknown interaction になるため、状態を見て送り先を分ける
        if interaction.response.is_done():
            await interaction.followup.send(message)
        else:
            await interaction.response.send_message(message)
    except Exception as e:
        sys_logger.error(e)
        sys_logger.error(traceback.format_exc())
        
#--------------------


# flask関連コードの読み込み

#--------------------



app = Flask(__name__,template_folder="mikanassets/web",static_folder="mikanassets/web")
app.secret_key = flask_secret_key
flask_logger = create_logger("werkzeug",Formatter.WebFormatter("FLASK",f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt),Formatter.WebConsoleFormatter("FLASK",'%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt=dt_fmt))
uvicorn_logger_err = create_logger("uvicorn.error",Formatter.WebFormatter("UVICORN",f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt),Formatter.WebConsoleFormatter("UVICORN",'%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt=dt_fmt))
uvicorn_logger = create_logger("uvicorn.access",Formatter.WebFormatter("UVICORN",f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt),Formatter.WebConsoleFormatter("UVICORN",'%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt=dt_fmt))

class ExcludeGetConsoleDataFilter(logging.Filter):
    def filter(self, record):
        # record.args はログ出力の引数、record.msg が生ログ文字列
        # "GET /get_console_data" を含むかどうかを確認
        return "/get_console_data" not in str(record.getMessage())
for logger in [flask_logger,uvicorn_logger_err,uvicorn_logger]:
    logger.addFilter(ExcludeGetConsoleDataFilter())
# def get_uvicorn_custom_log_config():
#     from uvicorn.config import LOGGING_CONFIG
#     uvicorn_custom_log_config = LOGGING_CONFIG.copy()
#     uvicorn_custom_log_config["formatters"]["default"]["fmt"] = f'{Color.BOLD + Color.BLACK}%(asctime)s {Color.BOLD + Color.CYAN}UVICORN  {Color.RESET.value}%(name)s: %(message)s'
#     uvicorn_custom_log_config["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
#     uvicorn_custom_log_config["formatters"]["access"]["fmt"] = f'{Color.BOLD + Color.BLACK}%(asctime)s {Color.BOLD + Color.CYAN}UVICORN  {Color.RESET.value}%(name)s: %(message)s'
#     uvicorn_custom_log_config["formatters"]["access"]["datefmt"] = "%Y-%m-%d %H:%M:%S"

#     class ExcludeGetConsoleDataFilter(logging.Filter):
#         def filter(self, record):
#             # record.args はログ出力の引数、record.msg が生ログ文字列
#             # "GET /get_console_data" を含むかどうかを確認
#             return "/get_console_data" not in str(record.getMessage())

#     uvicorn_custom_log_config["filters"] = {
#         "exclude_get_console_data": {
#             "()": ExcludeGetConsoleDataFilter,
#         }
#     }
#     uvicorn_custom_log_config["handlers"]["access"]["filters"] = ["exclude_get_console_data"]
#     return uvicorn_custom_log_config

# fastapi_logger = [
#     create_logger("uvicorn.access", Formatter.WebFormatter("UVICORN",f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt), Formatter.WebConsoleFormatter("UVICORN",'%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt=dt_fmt)),
#     create_logger("uvicorn", Formatter.WebFormatter("UVICORN",f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt), Formatter.WebConsoleFormatter("UVICORN",'%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt=dt_fmt)),
#     create_logger("uvicorn.error", Formatter.WebFormatter("UVICORN",f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt), Formatter.WebConsoleFormatter("UVICORN",'%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt=dt_fmt)),

#     ]

class LogIPMiddleware:
    def __init__(self, app):
        self.app = app
        # self.before_log = {"Client IP": "", "Method": "", "URL": "", "Query": ""}

    def __call__(self, environ, start_response):
        # クライアントのIPアドレスを取得
        client_ip = environ.get('REMOTE_ADDR', '')
        # リクエストされたURLを取得
        request_method = environ.get('REQUEST_METHOD', '')
        request_uri = environ.get('PATH_INFO', '')
        query_string = environ.get('QUERY_STRING', '')

        # ログに記録
        if request_uri != "/get_console_data":
            flask_logger.info(f"Client IP: {client_ip}, Method: {request_method}, URL: {request_uri}, Query: {query_string}")

        return self.app(environ, start_response)
    
# class LogIPMiddlewareASGI:
#     def __init__(self, app):
#         self.app = app

#     async def __call__(self, scope, receive, send):
#         if scope["type"] == "http":
#             client = scope.get("client")
#             method = scope.get("method")
#             path = scope.get("path")
#             query_string = scope.get("query_string", b"").decode("utf-8")

#             if path != "/get_console_data":
#                 client_ip = client[0] if client else "unknown"
#                 flask_logger.info(
#                     f"Client IP: {client_ip}, Method: {method}, URL: {path}, Query: {query_string}"
#                 )

#         await self.app(scope, receive, send)

# ミドルウェアをアプリに適用
app.wsgi_app = LogIPMiddleware(app.wsgi_app)


# トークンをロードする
def load_tokens():
    tokens = set()
    try:
        items = web_tokens
        now = datetime.now()
        for token in items:
            if datetime.strptime(token["deadline"], "%Y-%m-%d %H:%M:%S") > now:
                tokens.add(token["token"])
        return tokens
    except FileNotFoundError:
        flask_logger.info(f"Token file not found: {WEB_TOKEN_FILE}")
        return {}

# トークンを検証する
def is_valid_token(token):
    tokens = load_tokens()
    return token in tokens

def is_valid_session(token):
    if 'token' not in session:
        # ログアウトにリダイレクトするためのフラグを返す
        return False
    if not is_valid_token(session['token']):
        #ログアウト
        # ログアウトにリダイレクトするためのフラグを返す
        return False
    return True


# クッキーからトークンを取得し、セッションにセット
@app.before_request
def load_token_from_cookie():
    token = request.cookies.get('token')
    if token and is_valid_token(token):
        session['token'] = token

@app.route('/', methods=['GET', 'POST'])
def index():
    # セッションにトークンがある場合、ログイン済み
    if 'token' in session:
        if is_valid_token(session['token']):
            return render_template('index.html', logs = log_msg)

    # ログアウトさせられた場合理由を表示
    if 'logout_reason' in session:
        flash(session['logout_reason'])
        session.pop('logout_reason') 

    if request.method == 'POST':
        token = request.form['token']
        if is_valid_token(token):
            # トークンをセッションとクッキーに保存
            session['token'] = token
            resp = make_response(redirect(url_for('index')))
            
            # クッキーにトークンを保存、有効期限を30日間に設定
            expires = datetime.now() + timedelta(days=30)
            resp.set_cookie('token', token, expires=expires)

            return resp
        else:
            flash('Invalid token, please try again.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    # セッションとクッキーからトークンを削除してログアウト
    session.pop('token', None)
    resp = make_response(redirect(url_for('index')))
    resp.set_cookie('token', '', expires=0)  # クッキーを無効化
    return resp

# @app.route('/')
# def index():
#     return render_template('index.html', logs = log_msg)

@app.route('/get_console_data')
def get_console_data():
    if not is_valid_session(session['token']):
        # ログアウト
        session["logout_reason"] = "This token has expired. create new token."
        return jsonify({"redirect": url_for('logout')})
    
    converter = Ansi2HTMLConverter()
    html_string = converter.convert("\n".join(log_msg))

    try:
        server_online = process.poll() is None#サーバーが起動している = True
    except:
        if process is not None:
            process.kill()
        server_online = False

    bot_online = True

    return jsonify({"html_string": html_string, "online_status": {"server": server_online, "bot": bot_online}})


@app.route('/flask_start_server', methods=['POST'])
def flask_start_server():
    if not is_valid_session(session['token']):
        # ログアウト
        session["logout_reason"] = "This token has expired. create new token."
        return jsonify({"redirect": url_for('logout')})
    result = core_start()
    if result == RESPONSE_MSG["other"]["is_running"]:
        return jsonify(RESPONSE_MSG["other"]["is_running"])
    return jsonify(result)

@app.route('/flask_backup_server', methods=['POST'])
def flask_backup_server():
    if not is_valid_session(session['token']):
        # ログアウト
        session["logout_reason"] = "This token has expired. create new token."
        return jsonify({"redirect": url_for('logout')})
    world_name = request.form['fileName']
    if "\\" in world_name or "/" in world_name:
        return jsonify(RESPONSE_MSG["backup"]["not_allowed_path"] + ":" + server_path + world_name)
    if process is None:
        if os.path.exists(server_path + world_name):
            backup_logger.info("backup server")
            to = backup_path + "/" + datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
            copytree(server_path + world_name,to)
            backup_logger.info("backuped server to " + to)
            return jsonify("backuped server!! " + to)
        else:
            backup_logger.info('data not found : ' + server_path + world_name)
            return jsonify(RESPONSE_MSG["backup"]["data_not_found"] + ":" + server_path + world_name)
    else:
        return jsonify(RESPONSE_MSG["other"]["is_running"])

@app.route('/submit_data', methods=['POST'])
def submit_data():
    global use_stop
    if not is_valid_session(session['token']):
        # ログアウト
        session["logout_reason"] = "This token has expired. create new token."
        return jsonify({"redirect": url_for('logout')})
    user_input = request.form['userInput']
    #サーバーが起きてるかを確認
    if process is None:
        return jsonify("server is not running")
    #ifに引っかからない = サーバーが起動している

    #もし入力されたコマンドがstopだったら
    if user_input == STOP:
        use_stop = True

    #サーバーの標準入力に入力
    process.stdin.write(user_input + "\n")
    process.stdin.flush()

    # データを処理し、結果を返す（例: メッセージを返す）
    return jsonify(f"result: {user_input}")

def run_webservice_server():
    fastapi_app = SendDiscordSelfServer.create_app()
    if use_flask_server:
        fastapi_app.mount("/", WSGIMiddleware(app))
    # fastapi_app = LogIPMiddlewareASGI(fastapi_app)
    uvicorn.run(fastapi_app, host="0.0.0.0", port=web_port, log_config=None)

    
web_thread = threading.Thread(target=run_webservice_server, daemon=True, name="web_thread")
web_thread.start()


#--------------------


# discordロガーの設定

#--------------------


# discord.py用のロガーを取得して設定
discord_logger = logging.getLogger('discord')
if log["all"]:
    file_handler = logging.FileHandler(now_path + "/logs/all " + start_time + ".log")
    file_handler.setFormatter(file_formatter)
    discord_logger.addHandler(file_handler)
#--------------------



# 事実上のエントリポイント(client.runを実行)
client.run(token, log_formatter=console_formatter)
