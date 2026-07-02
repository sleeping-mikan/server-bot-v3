"""
config_loader.py — .config の読み込み・検証・既定値補完

main.py から切り出したモジュール。
`now_path` や `INITIAL_COMMAND_PERMISSION` はプロセスごとに決まる値なので、
グローバル参照ではなく引数として明示的に渡す形にしている
(元のコードでは make_config() の呼び出しは1箇所のみだったため、
 呼び出し側を1箇所だけ書き換えれば済む)。
"""

import json
import platform
from copy import deepcopy
from pathlib import Path

from core.config_types import AppConfig


def wait_for_keypress() -> None:
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


def delete_config(config_dict: dict) -> bool:
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


def _fill_config_defaults(cfg: dict, now_path: str, INITIAL_COMMAND_PERMISSION: dict) -> AppConfig:
    """既存 config に不足しているキーをデフォルト値で補完する。"""
    if "allow" not in cfg:
        cfg["allow"] = {"ip": True}
    if "ip" not in cfg["allow"]:
        cfg["allow"]["ip"] = True

    if "update" not in cfg:
        cfg["update"] = {"auto": True, "branch": "main"}
    if "auto" not in cfg["update"]:
        cfg["update"]["auto"] = True
    if "branch" not in cfg["update"]:
        cfg["update"]["branch"] = "main"
    elif "ip" not in cfg["allow"]:
        cfg["allow"]["ip"] = True
    if "server_path" not in cfg:
        cfg["server_path"] = str(Path(now_path).resolve()) + "/"
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
        cfg["discord_commands"]["cmd"]["stdin"]["sys_files"] = [".config", ".token", "logs", "mikanassets"]
    if "send_discord" not in cfg["discord_commands"]["cmd"]["stdin"]:
        cfg["discord_commands"]["cmd"]["stdin"]["send_discord"] = {"mode": "selfserver", "bits_capacity": 2 * 1024 * 1024 * 1024}
    if "bits_capacity" not in cfg["discord_commands"]["cmd"]["stdin"]["send_discord"]:
        cfg["discord_commands"]["cmd"]["stdin"]["send_discord"]["bits_capacity"] = 2 * 1024 * 1024 * 1024
    if "serverin" not in cfg["discord_commands"]["cmd"]:
        cfg["discord_commands"]["cmd"]["serverin"] = {}
    if "allow_cmd" not in cfg["discord_commands"]["cmd"]["serverin"]:
        cfg["discord_commands"]["cmd"]["serverin"]["allow_cmd"] = ["stop"]
    if "terminal" not in cfg["discord_commands"]:
        cfg["discord_commands"]["terminal"] = {"discord": False, "capacity": "inf"}
    if "discord" not in cfg["discord_commands"]["terminal"]:
        cfg["discord_commands"]["terminal"]["discord"] = False
    if "capacity" not in cfg["discord_commands"]["terminal"]:
        cfg["discord_commands"]["terminal"]["capacity"] = "inf"
    if "stop" not in cfg["discord_commands"]:
        cfg["discord_commands"]["stop"] = {"submit": "stop"}
    elif "submit" not in cfg["discord_commands"]["stop"]:
        cfg["discord_commands"]["stop"]["submit"] = "stop"
    if "admin" not in cfg["discord_commands"]:
        cfg["discord_commands"]["admin"] = {"members": {}, "use_discord_admin": True}
    elif "members" not in cfg["discord_commands"]["admin"]:
        cfg["discord_commands"]["admin"]["members"] = {}
    if "use_discord_admin" not in cfg["discord_commands"]["admin"]:
        cfg["discord_commands"]["admin"]["use_discord_admin"] = True
    if "lang" not in cfg["discord_commands"]:
        cfg["discord_commands"]["lang"] = "en"
    if "server_name" not in cfg:
        cfg["server_name"] = "bedrock_server.exe"
    if "log" not in cfg:
        cfg["log"] = {"server": True, "all": False}
    else:
        if "server" not in cfg["log"]:
            cfg["log"]["server"] = True
        if "all" not in cfg["log"]:
            cfg["log"]["all"] = False
    if "backup" not in cfg["discord_commands"]:
        try:
            server_name = cfg["server_path"].replace("\\", "/").split("/")[-2]
        except IndexError:
            print(f"server_path is broken. please check config file and try again.\ninput : {cfg['server_path']}")
            wait_for_keypress()
        if server_name == "":
            print("server_path is broken. please check config file and try again.")
            wait_for_keypress()
        backup_path = (Path(cfg["server_path"]) / ".." / "backup" / server_name).resolve()
        backup_path.mkdir(parents=True, exist_ok=True)
        cfg["discord_commands"]["backup"] = {"path": str(backup_path) + "/"}
    if "web" not in cfg:
        cfg["web"] = {"secret_key": "YOURSECRETKEY", "port": 80, "use_front_page": True}
    if "port" not in cfg["web"]:
        cfg["web"]["port"] = 80
    if "secret_key" not in cfg["web"]:
        cfg["web"]["secret_key"] = "YOURSECRETKEY"
    if "use_front_page" not in cfg["web"]:
        cfg["web"]["use_front_page"] = True
    if "enable_advanced_features" not in cfg:
        cfg["enable_advanced_features"] = False
    # v2.0.0 まで admin.members は list だった (権限レベルは現在の 1 相当)
    if isinstance(cfg["discord_commands"]["admin"]["members"], list):
        cfg["discord_commands"]["admin"]["members"] = {
            str(user): 1 for user in cfg["discord_commands"]["admin"]["members"]
        }
        print("admin.members is list. format changed to dict.(this version isv2.1.0 or later)")
    return cfg


def make_config(now_path: str, INITIAL_COMMAND_PERMISSION: dict) -> tuple[AppConfig, bool]:
    base         = Path(now_path)
    config_path  = base / ".config"

    if not config_path.exists():
        default_backup = (base / ".." / "backup" / base.name).resolve()
        default_backup.mkdir(parents=True, exist_ok=True)
        print("default backup path: " + str(default_backup))
        config_dict = {
            "allow": {"ip": True},
            "update": {"auto": True, "branch": "main"},
            "server_path": str(base) + "/",
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
                    "serverin": {"allow_cmd": ["stop"]},
                },
                "terminal": {"discord": False, "capacity": "inf"},
                "stop": {"submit": "stop"},
                "backup": {"path": str(default_backup) + "/"},
                "admin": {"members": {}, "use_discord_admin": True},
                "lang": "en",
            },
            "enable_advanced_features": False,
        }
        config_path.write_text(json.dumps(config_dict, indent=4), encoding="utf-8")
        config_changed = True
    else:
        try:
            config_dict = json.loads(config_path.read_text(encoding="utf-8"))
            changed = delete_config(config_dict)
        except json.decoder.JSONDecodeError:
            print("config file is broken. please delete .config and try again.")
            wait_for_keypress()
        checked_config = _fill_config_defaults(deepcopy(config_dict), now_path, INITIAL_COMMAND_PERMISSION)
        if config_dict != checked_config or changed:
            config_dict = checked_config
            config_path.write_text(json.dumps(config_dict, indent=4), encoding="utf-8")
            config_changed = True
            print("config file is changed.")
        else:
            config_changed = False
    return config_dict, config_changed
