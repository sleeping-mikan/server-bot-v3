"""
config_types.py — アプリ設定 (.config) の TypedDict 型定義

make_config() の返り値、AppState.config、各モジュールの引数注釈に使う。
キーを追加・削除するときはここと config_loader._fill_config_defaults の両方を更新する。
"""

from typing import TypedDict


# ── トップレベルのサブ設定 ────────────────────────────────────────────────────

class AllowConfig(TypedDict):
    ip: bool


class UpdateConfig(TypedDict):
    auto: bool
    branch: str


class LogConfig(TypedDict):
    server: bool
    all: bool


class WebConfig(TypedDict):
    secret_key: str
    port: int
    use_front_page: bool


# ── discord_commands 以下 ─────────────────────────────────────────────────────

class PermissionConfig(TypedDict):
    commands_level: dict[str, int]


class IpAddressConfig(TypedDict):
    prefix: str
    suffix: str
    body: str | None


class DiscordIpConfig(TypedDict):
    address: IpAddressConfig


class SendDiscordConfig(TypedDict):
    bits_capacity: int


class StdinConfig(TypedDict):
    sys_files: list[str]
    send_discord: SendDiscordConfig


class ServeInConfig(TypedDict):
    allow_mccmd: list[str]


class CmdConfig(TypedDict):
    stdin: StdinConfig
    serverin: ServeInConfig


class TerminalConfig(TypedDict):
    discord: int | bool   # Discord チャンネル ID または False (未設定)
    capacity: int | str   # 上限数または "inf"


class StopConfig(TypedDict):
    submit: str


class BackupConfig(TypedDict):
    path: str


class AdminConfig(TypedDict):
    members: dict[str, int]


class DiscordCommandsConfig(TypedDict):
    permission: PermissionConfig
    ip:         DiscordIpConfig
    cmd:        CmdConfig
    terminal:   TerminalConfig
    stop:       StopConfig
    backup:     BackupConfig
    admin:      AdminConfig
    lang:       str


# ── ルート ────────────────────────────────────────────────────────────────────

class AppConfig(TypedDict):
    allow:                  AllowConfig
    update:                 UpdateConfig
    server_path:            str
    server_name:            str
    server_args:            str
    server_char_encoding:   str
    log:                    LogConfig
    web:                    WebConfig
    discord_commands:       DiscordCommandsConfig
    enable_advanced_features: bool
