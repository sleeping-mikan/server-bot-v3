"""
state.py — アプリ全体で共有される可変状態

## 構成
- TextBundle   : テキスト・i18n データ (lang 変更時に一括更新)
- DiscordTerminal : Discord チャンネルへのログ転送状態
- AppState     : アプリシングルトン (ctx)

## 使い方
    from core.state import ctx
    ctx.text.response_msg["backup"]["success"]
    ctx.terminal.channel_id
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.config_types import AppConfig
from core.paths import BotPaths
from server.process import ServerProcess


# ── サブデータクラス ──────────────────────────────────────────────────────────

@dataclass
class TextBundle:
    """テキスト・i18n データ。/lang 実行時に load_text_data() で一括更新される。"""

    lang:               str  = "en"
    help_msg:           dict = field(default_factory=dict)
    command_desc:       dict = field(default_factory=dict)
    response_msg:       dict = field(default_factory=dict)
    activity_name:      dict = field(default_factory=dict)
    send_help:          Any  = None
    command_permission: dict = field(default_factory=dict)


@dataclass
class DiscordTerminal:
    """Discord チャンネルへのログ転送状態。"""

    channel_id:   int | bool = False
    item:         deque      = field(default_factory=deque)
    send_length:  int        = 0
    loop_is_run:  bool       = False


# ── AppState ─────────────────────────────────────────────────────────────────

@dataclass
class AppState:
    """アプリケーション全体の共有状態。`ctx` シングルトンを通じて使う。"""

    # ── インフラ ──────────────────────────────────────────────────
    server_process: ServerProcess  = field(default_factory=ServerProcess)
    paths:          BotPaths | None = None

    # ── 認証 ──────────────────────────────────────────────────────
    token:      str | None = None
    web_tokens: list       = field(default_factory=list)
    web_ip:     str        = ""

    # ── 設定 ──────────────────────────────────────────────────────
    config:                 AppConfig | None = None
    server_name:            str         = ""
    server_path:            Path        = field(default_factory=Path)
    server_args:            list        = field(default_factory=list)
    server_char_code:       str         = "utf-8"
    STOP:                   str         = ""
    backup_path:            Path        = field(default_factory=Path)
    web_port:               int         = 8080
    allow_cmd:              set         = field(default_factory=set)
    enable_advanced_features: bool      = False
    terminal_capacity:      float       = float("inf")
    temp_path:              Path | None = None

    # ── テキスト・言語 ─────────────────────────────────────────────
    text: TextBundle = field(default_factory=TextBundle)

    # ── Discord terminal ───────────────────────────────────────────
    terminal: DiscordTerminal = field(default_factory=DiscordTerminal)

    # ── ランタイム状態 ─────────────────────────────────────────────
    use_stop:              bool  = False
    is_back_discord:       bool  = False
    cmd_logs:              deque = field(default_factory=lambda: deque(maxlen=100))
    is_write_server_block: bool  = False

    # ── 拡張機能ローディング用 ─────────────────────────────────────
    extension_commands_group: Any  = None
    extension_logger:         Any  = None
    extension_tasks:          list = field(default_factory=list)

    # ── 内部参照 ──────────────────────────────────────────────────
    server_logger: Any = None  # server/stdout.py の読み取り関数

    def init_paths(self, base_dir: str | Path) -> None:
        self.paths = BotPaths(base_dir)


# シングルトン
ctx = AppState()
