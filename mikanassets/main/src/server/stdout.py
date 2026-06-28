"""
server/stdout.py — サーバー標準出力の読み取りスレッド

make_reader() でスレッド関数を生成して server_process.start() に渡す。
"""

from __future__ import annotations

import subprocess
from datetime import datetime

from core.log_setup import LogManager
from core.state import ctx


def make_reader(log_server: bool):
    """サーバーの stdout を読み続けるスレッド関数を生成して返す。

    Args:
        log_server : True の場合ファイルにもログを書き出す
    """
    def reader(proc: subprocess.Popen, _ret) -> None:
        server_log = LogManager.server
        sys_log    = LogManager.sys
        log_file   = None

        if log_server:
            log_path = (
                ctx.server_path / "logs"
                / f"server {datetime.now().strftime('%Y-%m-%d_%H_%M_%S')}.log"
            )
            log_file = log_path.open(mode="w", encoding="utf-8")

        try:
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
                if log_file is not None:
                    log_file.write(line + "\n")
                    log_file.flush()
                if ctx.is_back_discord:
                    ctx.cmd_logs.append(line)
                    ctx.is_back_discord = False
        finally:
            if log_file is not None:
                log_file.close()

        sys_log.info("server is ended")
        if not ctx.use_stop:
            sys_log.error("stop command is not found")
            ctx.use_stop = True
        ctx.server_process.reset()

    return reader
