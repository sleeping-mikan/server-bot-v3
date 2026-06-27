"""
log_setup.py — ロギング用フォーマッタ・ロガー生成処理

main.py から切り出したモジュール。
create_logger() は元のコードと挙動を変えないため、
(name, console_formatter, file_formatter) 以外の必要情報(now_path, log["all"]の値, start_time)は
init() で事前に設定しておく方式にしている(main.py側の呼び出し箇所 `create_logger("xxx")` を
そのまま変更せずに使えるようにするための工夫)。
"""

import sys
import logging
from collections import deque
from pathlib import Path

from colors import Color


class Formatter():
    levelname_size = 8
    name_size = 10
    class ColoredFormatter(logging.Formatter):
        # ANSI escape codes for colors
        COLORS = {
            'DEBUG': Color.BOLD + Color.WHITE,   # White
            'INFO': Color.BOLD + Color.BLUE,    # Blue
            'WARNING': Color.BOLD + Color.YELLOW, # Yellow
            'ERROR': Color.BOLD + Color.RED,   # Red
            'CRITICAL': Color.BOLD + Color.MAGENTA # Red background
        }
        RESET = '\033[0m'  # Reset color
        BOLD_BLACK = Color.BOLD + Color.BLACK  # Bold Black

        def format(self, record):
            # Format the asctime
            record.asctime = self.formatTime(record, self.datefmt)
            bold_black_asctime = f"{self.BOLD_BLACK}{record.asctime}{self.RESET}"

            # Adjust level name to be 8 characters long
            original_levelname = record.levelname
            padded_levelname = original_levelname.ljust(Formatter.levelname_size)
            original_name = record.name
            padded_name = original_name.ljust(Formatter.name_size)

            # Apply color to the level name only
            color = self.COLORS.get(original_levelname, self.RESET)
            colored_levelname = f"{color}{padded_levelname}{self.RESET}"

            # Get the formatted message
            message = record.getMessage()

            # Create the final formatted message
            formatted_message = f"{bold_black_asctime} {colored_levelname} {padded_name}: {message}"

            return formatted_message

    class MinecraftFormatter(logging.Formatter):

        # ANSI escape codes for colors
        COLORS = {
            'SERVER': Color.BOLD + Color.GREEN,   # Green
        }
        RESET = '\033[0m'  # Reset color
        BOLD_BLACK = Color.BOLD + Color.BLACK  # Bold Black

        def format(self, record):
            # Format the asctime
            record.asctime = self.formatTime(record, self.datefmt)
            bold_black_asctime = f"{self.BOLD_BLACK}{record.asctime}{self.RESET}"

            # Apply color to the level name only
            color = self.COLORS["SERVER"]
            colored_levelname = f"{color}SERVER  {self.RESET}"

            # Get the formatted message
            message = record.getMessage()
            what_type = message.upper()
            if "INFO" in what_type:
                msg_color = Color.CYAN
            elif "ERROR" in what_type:
                msg_color = Color.RED
            elif "WARN" in what_type:
                msg_color = Color.YELLOW
            else:
                msg_color = Color.RESET

            message = msg_color + message + Color.RESET

            # Create the final formatted message
            formatted_message = f"{bold_black_asctime} {colored_levelname} {message}"

            return formatted_message
    class WebFormatter(logging.Formatter):
        def __init__(self, prefix, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.COLORS = {
                'FLASK': Color.BOLD + Color.CYAN,   # Green
            }
            self.RESET = '\033[0m'  # Reset color
            self.BOLD_BLACK = Color.BOLD + Color.BLACK  # Bold Black
            self.prefix = prefix
        def format(self, record):
            # Format the asctime
            record.asctime = self.formatTime(record, self.datefmt)
            bold_black_asctime = f"{self.BOLD_BLACK}{record.asctime}{self.RESET}"

            # Apply color to the level name only
            color = self.COLORS["FLASK"]
            colored_levelname = f"{color}{self.prefix.ljust(Formatter.levelname_size)}{self.RESET}"

            # Get the formatted message
            message = record.getMessage()

            message = message + Color.RESET

            # Create the final formatted message
            formatted_message = f"{bold_black_asctime} {colored_levelname} {message}"

            return formatted_message

    class DefaultConsoleFormatter(logging.Formatter):
        def format(self, record):
            # Format the asctime
            record.asctime = self.formatTime(record, self.datefmt)

            # Adjust level name to be 8 characters long
            original_levelname = record.levelname
            padded_levelname = original_levelname.ljust(Formatter.levelname_size)
            original_name = record.name
            padded_name = original_name.ljust(Formatter.name_size)


            # Get the formatted message
            message = record.getMessage()

            # Create the final formatted message
            formatted_message = f"{record.asctime} {padded_levelname} {padded_name}: {message}"

            return formatted_message

    class MinecraftConsoleFormatter(logging.Formatter):
        def format(self, record):
            # Format the asctime
            record.asctime = self.formatTime(record, self.datefmt)

            padded_levelname = "SERVER".ljust(Formatter.levelname_size)


            # Get the formatted message
            message = record.getMessage()

            # Create the final formatted message
            formatted_message = f"{record.asctime} {padded_levelname} {message}"

            return formatted_message
    class WebConsoleFormatter(logging.Formatter):
        def __init__(self, prefix, fmt = None, datefmt = None, style = "%", validate = True, *, defaults = None):
            super().__init__(fmt, datefmt, style, validate, defaults=defaults)
            self.prefix = prefix
        def format(self, record):
            # Format the asctime
            record.asctime = self.formatTime(record, self.datefmt)

            padded_levelname = self.prefix.ljust(Formatter.levelname_size)


            # Get the formatted message
            message = record.getMessage()

            # Create the final formatted message
            formatted_message = f"{record.asctime} {padded_levelname} {message}"

            return formatted_message

    # カスタムフィルタ（/get_console_data を除外）
    class ExcludeConsoleDataFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return "/get_console_data" not in record.getMessage()


#logger
dt_fmt = '%Y-%m-%d %H:%M:%S'
console_formatter = Formatter.ColoredFormatter(f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt)
file_formatter = Formatter.DefaultConsoleFormatter('%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt)

#/log用のログ保管場所
log_msg = deque(maxlen=100)
#discord送信用のログ
discord_log_msg = deque()

# create_logger()が参照する、main.py側の実行時情報(init()で設定される)
_now_path = None
_log_all = False
_start_time = None


def init(now_path: str, log_all: bool, start_time: str) -> None:
    """create_logger() がファイル出力等に使う情報を設定する。main.py起動時に一度呼ぶ。"""
    global _now_path, _log_all, _start_time
    _now_path = now_path
    _log_all = log_all
    _start_time = start_time


def create_logger(name, console_formatter=console_formatter, file_formatter=file_formatter):
    class DequeHandler(logging.Handler):
        def __init__(self, deque):
            super().__init__()
            self.deque = deque

        def emit(self, record):
            log_entry = self.format(record)
            self.deque.append(log_entry)
    class DiscordHandler(logging.Handler):
        def __init__(self, deque):
            super().__init__()
            self.deque = deque
        def emit(self, record):
            log_entry = self.format(record)
            self.deque.append(log_entry)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(console_formatter)
    logger.addHandler(console)
    if _log_all:
        import os
        f = _start_time + ".log"
        file = logging.FileHandler(str(Path(_now_path) / "logs" / f"all {f}"), encoding="utf-8")
        file.setLevel(logging.DEBUG)
        file.setFormatter(file_formatter)
        logger.addHandler(file)
    deque_handler = DequeHandler(log_msg)
    deque_handler.setLevel(logging.DEBUG)
    deque_handler.setFormatter(console_formatter)  # フォーマットは任意で設定
    discord_handler = DiscordHandler(discord_log_msg)
    discord_handler.setLevel(logging.DEBUG)
    discord_handler.setFormatter(console_formatter)  # フォーマットは任意で設定
    logger.addHandler(deque_handler)
    logger.addHandler(discord_handler)
    return logger


def get_log():
    return log_msg
