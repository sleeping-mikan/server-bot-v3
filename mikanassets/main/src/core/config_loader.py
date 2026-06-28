"""
config_loader.py — .config の読み込み・検証・既定値補完

main.py から切り出したモジュール。
`now_path` や `INITIAL_COMMAND_PERMISSION` はプロセスごとに決まる値なので、
グローバル参照ではなく引数として明示的に渡す形にしている
(元のコードでは make_config() の呼び出しは1箇所のみだったため、
 呼び出し側を1箇所だけ書き換えれば済む)。
"""

import os
import re
import json
import platform
from copy import deepcopy


def normalize_path(path: str) -> str:
    ## \\や//のような連続するスラッシュを1つにする
    path = re.sub(r'\\+', '/', path)
    path = re.sub(r'//+', '/', path)
    return path.replace("\\", "/")


def wait_for_keypress():
    print("please press any key to continue...")
    if platform.system() == "Windows":
        import msvcrt
        while True:
            if msvcrt.kbhit():
                msvcrt.getch()
                break
        exit()
    else:
        import sys
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            exit()


def delete_config(config_dict):
    changed = False
    # v2.2.0まで存在した -> 現在はupdate keyに複数要素が存在している
    if "auto_update" in config_dict:
        del config_dict["auto_update"]
        changed = True
    # v2.4.12まで存在した (現在は削除)
    if "mc" in config_dict:
        del config_dict["mc"]
        changed = True
    # process_type は廃止
    if "process_type" in config_dict:
        del config_dict["process_type"]
        changed = True
    return changed


def make_config(now_path: str, INITIAL_COMMAND_PERMISSION: dict):
    config_file_place = now_path + "/" + ".config"
    if not os.path.exists(config_file_place):
        server_path = now_path
        default_backup_path = server_path + "/../backup/" + server_path.replace("\\","/").split("/")[-1]
        if not os.path.exists(default_backup_path):
            os.makedirs(default_backup_path)
        default_backup_path = os.path.realpath(default_backup_path) + "/"
        print("default backup path: " + default_backup_path)
        config_dict = {
            "allow": {"ip": True},
            "update": {"auto": True, "branch": "main"},
            "server_path": now_path + "/",
            "server_name": "bedrock_server.exe",
            "server_args": "",
            "server_char_encoding": "utf-8",
            "log": {"server": True, "all": False},
            "web": {"secret_key": "YOURSECRETKEY", "port": 80, "use_front_page": True},
            "discord_commands": {
                "permission": {"commands_level": INITIAL_COMMAND_PERMISSION},
                "ip": {
                    "address": {"prefix": "", "suffix": "", "body": None},
                },
                "cmd": {
                    "stdin": {
                        "sys_files": [".config", ".token", "logs", "mikanassets"],
                        "send_discord": {"bits_capacity": 2 * 1024 * 1024 * 1024},
                    },
                    "serverin": {"allow_mccmd": ["list", "whitelist", "tellraw", "w", "tell"]},
                },
                "terminal": {"discord": False, "capacity": "inf"},
                "stop": {"submit": "stop"},
                "backup": {"path": default_backup_path},
                "admin": {"members": {}},
                "lang": "en",
            },
            "enable_advanced_features": False,
        }
        with open(config_file_place, "w") as f:
            json.dump(config_dict, f, indent=4)
        config_changed = True
    else:
        try:
            with open(now_path + "/" + ".config", "r", encoding="utf-8") as f:
                config_dict = json.load(f)
            # 不要な要素があれば削除
            changed = delete_config(config_dict)
        except json.decoder.JSONDecodeError:
            print("config file is broken. please delete .config and try again.")
            wait_for_keypress()
        #要素がそろっているかのチェック
        def check(cfg):
            if "allow" not in cfg:
                cfg["allow"] = {"ip":True}
            if "ip" not in cfg["allow"]:
                cfg["allow"]["ip"] = True

            if "update" not in cfg:
                cfg["update"] = {"auto":True,"branch":"main"}
            if "auto" not in cfg["update"]:
                cfg["update"]["auto"] = True
            if "branch" not in cfg["update"]:
                cfg["update"]["branch"] = "main"
            elif "ip" not in cfg["allow"]:
                cfg["allow"]["ip"] = True
            if "server_path" not in cfg:
                cfg["server_path"] = now_path + "/"
            if "server_args" not in cfg:
                cfg["server_args"] = ""
            if "server_char_encoding" not in cfg:
                cfg["server_char_encoding"] = "utf-8"
            if "discord_commands" not in cfg:
                cfg["discord_commands"] = {}
            if "permission" not in cfg["discord_commands"]:
                cfg["discord_commands"]["permission"] = {}
            if "commands_level" not in cfg["discord_commands"]["permission"]:
                cfg["discord_commands"]["permission"]["commands_level"] = INITIAL_COMMAND_PERMISSION
            # 特定コマンドのキーが不足していれば追加
            for key in INITIAL_COMMAND_PERMISSION.keys():
                if key not in cfg["discord_commands"]["permission"]["commands_level"]:
                    cfg["discord_commands"]["permission"]["commands_level"][key] = INITIAL_COMMAND_PERMISSION[key]
            if "ip" not in cfg["discord_commands"]:
                cfg["discord_commands"]["ip"] = {}
            if "address" not in cfg["discord_commands"]["ip"]:
                cfg["discord_commands"]["ip"]["address"] = {}
            addr = cfg["discord_commands"]["ip"]["address"]
            if "prefix" not in addr:
                addr["prefix"] = ""
            if "suffix" not in addr:
                addr["suffix"] = ""
            if "body" not in addr:
                addr["body"] = None
            if "cmd" not in cfg["discord_commands"]:
                cfg["discord_commands"]["cmd"] = {}
            if "stdin" not in cfg["discord_commands"]["cmd"]:
                cfg["discord_commands"]["cmd"]["stdin"] = {}
            if "sys_files" not in cfg["discord_commands"]["cmd"]["stdin"]:
                cfg["discord_commands"]["cmd"]["stdin"]["sys_files"] = [".config",".token","logs","mikanassets"]
            if "send_discord" not in cfg["discord_commands"]["cmd"]["stdin"]:
                cfg["discord_commands"]["cmd"]["stdin"]["send_discord"] = {"mode":"selfserver","bits_capacity":2 * 1024 * 1024 * 1024}
            if "bits_capacity" not in cfg["discord_commands"]["cmd"]["stdin"]["send_discord"]:
                cfg["discord_commands"]["cmd"]["stdin"]["send_discord"]["bits_capacity"] = 2 * 1024 * 1024 * 1024
            if "serverin" not in cfg["discord_commands"]["cmd"]:
                cfg["discord_commands"]["cmd"]["serverin"] = {}
            if "allow_mccmd" not in cfg["discord_commands"]["cmd"]["serverin"]:
                cfg["discord_commands"]["cmd"]["serverin"]["allow_mccmd"] = ["list","whitelist","tellraw","w","tell"]
            if "terminal" not in cfg["discord_commands"]:
                cfg["discord_commands"]["terminal"] = {"discord":False,"capacity":"inf"}
            if "discord" not in cfg["discord_commands"]["terminal"]:
                cfg["discord_commands"]["terminal"]["discord"] = False
            if "capacity" not in cfg["discord_commands"]["terminal"]:
                cfg["discord_commands"]["terminal"]["capacity"] = "inf"
            if "stop" not in cfg["discord_commands"]:
                cfg["discord_commands"]["stop"] = {"submit":"stop"}
            elif "submit" not in cfg["discord_commands"]["stop"]:
                cfg["discord_commands"]["stop"]["submit"] = "stop"
            if "admin" not in cfg["discord_commands"]:
                cfg["discord_commands"]["admin"] = {"members":{}}
            elif "members" not in cfg["discord_commands"]["admin"]:
                cfg["discord_commands"]["admin"]["members"] = {}
            if "lang" not in cfg["discord_commands"]:
                cfg["discord_commands"]["lang"] = "en"
            if "server_name" not in cfg:
                cfg["server_name"] = "bedrock_server.exe"
            if "log" not in cfg:
                cfg["log"] = {"server":True,"all":False}
            else:
                if "server" not in cfg["log"]:
                    cfg["log"]["server"] = True
                if "all" not in cfg["log"]:
                    cfg["log"]["all"] = False
            if "backup" not in cfg["discord_commands"]:
                try:
                    server_name = cfg["server_path"].replace("\\","/").split("/")[-2]
                except IndexError:
                    print(f"server_path is broken. please check config file and try again.\ninput : {cfg['server_path']}")
                    wait_for_keypress()
                if server_name == "":
                    print("server_path is broken. please check config file and try again.")
                    wait_for_keypress()
                cfg["discord_commands"]["backup"] = {}
                cfg["discord_commands"]["backup"]["path"] = cfg["server_path"] + "../backup/" + server_name
                cfg["discord_commands"]["backup"]["path"] = os.path.realpath(cfg["discord_commands"]["backup"]["path"]) + "/"
                if not os.path.exists(cfg["discord_commands"]["backup"]["path"]):
                    os.makedirs(cfg["discord_commands"]["backup"]["path"])
            if "web" not in cfg:
                cfg["web"] = {"secret_key":"YOURSECRETKEY","port":80,"use_front_page": True}
            if "port" not in cfg["web"]:
                cfg["web"]["port"] = 80
            if "secret_key" not in cfg["web"]:
                cfg["web"]["secret_key"] = "YOURSECRETKEY"
            if "use_front_page" not in cfg["web"]:
                cfg["web"]["use_front_page"] = True
            if "enable_advanced_features" not in cfg:
                cfg["enable_advanced_features"] = False
            # バージョン移行処理
            # v2.0.0までは、admin.membersがlistで管理されていた(当時の権限レベルは現在の1に該当する。)
            if isinstance(cfg["discord_commands"]["admin"]["members"], list):
                users = {}
                for user in cfg["discord_commands"]["admin"]["members"]:
                    users[str(user)] = 1
                cfg["discord_commands"]["admin"]["members"] = users
                print("admin.members is list. format changed to dict.(this version isv2.1.0 or later)")
            return cfg
        checked_config = check(deepcopy(config_dict))
        if config_dict != checked_config or changed:
            config_dict = checked_config
            with open(now_path + "/" + ".config", "w") as f:
                json.dump(config_dict, f, indent=4)
            config_changed = True
            print("config file is changed.")
        else: config_changed = False
    return config_dict,config_changed


def to_config_safe(config, config_file_place):
    #"force_admin"に重複があれば削除する
    save = False
    if save:
        file = open(config_file_place,"w")
        json.dump(config,file,indent=4)
        file.close()
