"""
log_setup.py — ロギングインフラ

フォーマッタ定義 + LogManager クラスによる一元管理。

使い方:
    # 起動時に一度だけ
    LogManager.init(now_path, log_all, start_time)

    # ロガー取得
    LogManager.sys.info("起動")
    backup_log = LogManager.cmd.getChild("backup")

    # サードパーティ (Flask/uvicorn)
    LogManager.setup_third_party("werkzeug", "FLASK")
"""

from __future__ import annotations

import logging
import sys
from collections import deque
from pathlib import Path
from typing import ClassVar

from core.colors import Color

# ── 共通定数 ─────────────────────────────────────────────────────────────────

DT_FMT = "%Y-%m-%d %H:%M:%S"
_LEVEL_W = 8   # levelname 表示幅
_NAME_W = 10   # logger name 表示幅

# Color は Enum なので文字列として使う場合は .value を使う
_RESET    = Color.RESET.value          # "\033[0m"
_DT_COLOR = Color.BOLD + Color.BLACK   # __add__ が str を返すので OK

_LEVEL_COLORS: dict[str, str] = {
    "DEBUG":    Color.BOLD + Color.WHITE,    # str
    "INFO":     Color.BOLD + Color.BLUE,
    "WARNING":  Color.BOLD + Color.YELLOW,
    "ERROR":    Color.BOLD + Color.RED,
    "CRITICAL": Color.BOLD + Color.MAGENTA,
}

# サーバーログ用メッセージカラー (str)
_SERVER_MSG_COLORS: dict[str, str] = {
    "INFO":  Color.CYAN.value,
    "WARN":  Color.YELLOW.value,
    "ERROR": Color.RED.value,
}
_SERVER_LABEL_COLOR = Color.BOLD + Color.GREEN   # str


def _dt(record: logging.LogRecord, fmt: logging.Formatter) -> str:
    return fmt.formatTime(record, DT_FMT)


# ── フォーマッタ ──────────────────────────────────────────────────────────────

class ColoredFormatter(logging.Formatter):
    """標準ログ用カラーコンソールフォーマッタ。"""

    def format(self, record: logging.LogRecord) -> str:
        dt      = f"{_DT_COLOR}{_dt(record, self)}{_RESET}"
        level   = f"{_LEVEL_COLORS.get(record.levelname, '')}{record.levelname.ljust(_LEVEL_W)}{_RESET}"
        name    = record.name.ljust(_NAME_W)
        return f"{dt} {level} {name}: {record.getMessage()}"


class PlainFormatter(logging.Formatter):
    """標準ログ用ファイルフォーマッタ (ANSIなし)。"""

    def format(self, record: logging.LogRecord) -> str:
        dt    = _dt(record, self)
        level = record.levelname.ljust(_LEVEL_W)
        name  = record.name.ljust(_NAME_W)
        return f"{dt} {level} {name}: {record.getMessage()}"


class ServerConsoleFormatter(logging.Formatter):
    """サーバー stdout 用カラーフォーマッタ。"""

    def format(self, record: logging.LogRecord) -> str:
        dt    = f"{_DT_COLOR}{_dt(record, self)}{_RESET}"
        label = f"{_SERVER_LABEL_COLOR}SERVER  {_RESET}"
        msg   = record.getMessage()
        for key, color in _SERVER_MSG_COLORS.items():
            if key in msg.upper():
                msg = f"{color}{msg}{_RESET}"
                break
        return f"{dt} {label} {msg}"


class ServerPlainFormatter(logging.Formatter):
    """サーバー stdout 用ファイルフォーマッタ。"""

    def format(self, record: logging.LogRecord) -> str:
        return f"{_dt(record, self)} SERVER   {record.getMessage()}"


class PrefixedConsoleFormatter(logging.Formatter):
    """Flask / uvicorn 等の prefix 付きカラーフォーマッタ。"""

    def __init__(self, prefix: str, **kwargs):
        super().__init__(**kwargs)
        self._prefix = prefix
        self._label  = f"{Color.BOLD + Color.CYAN}{prefix.ljust(_LEVEL_W)}{_RESET}"

    def format(self, record: logging.LogRecord) -> str:
        dt = f"{_DT_COLOR}{_dt(record, self)}{_RESET}"
        return f"{dt} {self._label} {record.getMessage()}{_RESET}"


class PrefixedPlainFormatter(logging.Formatter):
    """Flask / uvicorn 等の prefix 付きファイルフォーマッタ。"""

    def __init__(self, prefix: str, **kwargs):
        super().__init__(**kwargs)
        self._prefix = prefix

    def format(self, record: logging.LogRecord) -> str:
        return f"{_dt(record, self)} {self._prefix.ljust(_LEVEL_W)} {record.getMessage()}"


class ExcludePathFilter(logging.Filter):
    """指定パスを含むログレコードを除外するフィルタ。"""

    def __init__(self, path: str):
        super().__init__()
        self._path = path

    def filter(self, record: logging.LogRecord) -> bool:
        return self._path not in record.getMessage()


# ── 内部ハンドラ ──────────────────────────────────────────────────────────────

class _DequeHandler(logging.Handler):
    def __init__(self, target: deque, formatter: logging.Formatter):
        super().__init__()
        self.setFormatter(formatter)
        self._target = target

    def emit(self, record: logging.LogRecord) -> None:
        self._target.append(self.format(record))


# ── LogManager ────────────────────────────────────────────────────────────────

class LogManager:
    """アプリ全体のロガー管理クラス。init() 後に各属性が利用可能になる。"""

    # ログメッセージバッファ
    log_msg:         ClassVar[deque] = deque(maxlen=100)
    discord_log_msg: ClassVar[deque] = deque()

    # 共通フォーマッタ (init() 前から使用可)
    console_formatter: ClassVar[ColoredFormatter] = ColoredFormatter(datefmt=DT_FMT)
    file_formatter:    ClassVar[PlainFormatter]   = PlainFormatter(datefmt=DT_FMT)

    # アプリロガー (init() 後に利用可)
    bot:       ClassVar[logging.Logger]
    sys:       ClassVar[logging.Logger]
    server:    ClassVar[logging.Logger]
    cmd:       ClassVar[logging.Logger]
    web:       ClassVar[logging.Logger]
    update:    ClassVar[logging.Logger]
    extension: ClassVar[logging.Logger]

    _now_path:   ClassVar[str | None] = None
    _log_all:    ClassVar[bool]       = False
    _start_time: ClassVar[str | None] = None

    @classmethod
    def init(cls, now_path: str, log_all: bool, start_time: str) -> None:
        """起動時に一度だけ呼ぶ。各ロガーを生成して属性に設定する。"""
        cls._now_path   = now_path
        cls._log_all    = log_all
        cls._start_time = start_time

        cls.bot       = cls._make("bot")
        cls.sys       = cls._make("sys")
        cls.server    = cls._make("server",
                            con_fmt=ServerConsoleFormatter(datefmt=DT_FMT),
                            file_fmt=ServerPlainFormatter(datefmt=DT_FMT))
        cls.cmd       = cls._make("cmd")
        cls.web       = cls._make("web")
        cls.update    = cls._make("update")
        cls.extension = cls._make("extension")

    @classmethod
    def _make(
        cls,
        name:     str,
        con_fmt:  logging.Formatter | None = None,
        file_fmt: logging.Formatter | None = None,
    ) -> logging.Logger:
        """ハンドラ付きロガーを生成する。既にハンドラが存在すれば何もしない。"""
        logger = logging.getLogger(name)
        if logger.handlers:
            return logger
        logger.setLevel(logging.INFO)
        logger.propagate = False

        _con = con_fmt or cls.console_formatter
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(_con)
        logger.addHandler(ch)

        if cls._log_all:
            _file = file_fmt or cls.file_formatter
            path  = Path(cls._now_path) / "logs" / f"all {cls._start_time}.log"
            fh    = logging.FileHandler(str(path), encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(_file)
            logger.addHandler(fh)

        logger.addHandler(_DequeHandler(cls.log_msg,         _con))
        logger.addHandler(_DequeHandler(cls.discord_log_msg, _con))

        return logger

    @classmethod
    def setup_third_party(cls, logger_name: str, display_prefix: str) -> logging.Logger:
        """Flask / uvicorn 等のサードパーティロガーにカスタムハンドラを付ける。"""
        return cls._make(
            logger_name,
            con_fmt  = PrefixedConsoleFormatter(display_prefix, datefmt=DT_FMT),
            file_fmt = PrefixedPlainFormatter(display_prefix,   datefmt=DT_FMT),
        )

    @classmethod
    def setup_discord_lib(cls) -> None:
        """discord.py 内部ロガーにファイルハンドラを追加する (log_all=True 時のみ)。"""
        if not cls._log_all:
            return
        dlog = logging.getLogger("discord")
        path = Path(cls._now_path) / "logs" / f"all {cls._start_time}.log"
        fh   = logging.FileHandler(str(path), encoding="utf-8")
        fh.setFormatter(cls.file_formatter)
        dlog.addHandler(fh)


# ── モジュールレベルのエイリアス (後方互換・外部アクセス用) ──────────────────────

log_msg         = LogManager.log_msg
discord_log_msg = LogManager.discord_log_msg
