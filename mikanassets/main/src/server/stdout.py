"""
server/stdout.py — サーバー標準出力の読み取りスレッド

make_reader() でスレッド関数を生成して server_process.start() に渡す。
"""

from __future__ import annotations

import subprocess
from datetime import datetime

from core.log_setup import LogManager
from core.state import ctx


def make_reader(log_server: bool, server_path: str):
    """サーバーの stdout を読み続けるスレッド関数を生成して返す。

    Args:
        log_server  : True の場合ファイルにもログを書き出す
        server_path : サーバーディレクトリのパス
    """
    def reader(proc: subprocess.Popen, _ret) -> None:
        server_log = LogManager.server
        sys_log    = LogManager.sys

        if log_server:
            log_path = (
                server_path + "logs/server "
                + datetime.now().strftime("%Y-%m-%d_%H_%M_%S") + ".log"
            )
            log_file = open(log_path, mode="w", encoding="utf-8")

        while True:
            try:
                line = proc.stdout.readline()
            except Exception as e:
                sys_log.error(e)
                continue
            if line == "":
                if proc.poll() is not None:
                    break
                continue
            if line == "\n":
                continue
            line = line.rstrip("\n")
            server_log.info(line)
            if log_server:
                log_file.write(line + "\n")
                log_file.flush()
            if ctx.is_back_discord:
                ctx.cmd_logs.append(line)
                ctx.is_back_discord = False

        sys_log.info("server is ended")
        if not ctx.use_stop:
            sys_log.error("stop command is not found")
            ctx.use_stop = True
        ctx.server_process.reset()

    return reader
