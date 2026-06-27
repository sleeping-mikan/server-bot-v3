"""
server_process.py — Minecraft(等)サーバーの起動中プロセスを管理するクラス

これまでは生の `subprocess.Popen` オブジェクトをあちこちのコードから直接触っていた
(`process.stdin.write(...)` 、 `process.poll()` 、 `process.kill()` など)。
これを「サーバープロセスに対してできる操作」としてこのクラスに集約し、
呼び出し側は `start()` / `write()` / `is_running()` のような意味の分かる
メソッド越しに操作する形に変える。

このクラスのインスタンスは state.py の `state.server_process` として
1つだけ生成され(シングルトン的に使う)、他のモジュールからは
`import state` した上で `state.server_process.xxx()` という形で利用する。
"""

import subprocess
import threading
from collections import deque


class ServerProcess:
    def __init__(self):
        self._popen: subprocess.Popen | None = None

    @property
    def pid(self):
        """プロセスID(起動していなければNone)"""
        return self._popen.pid if self._popen is not None else None

    def is_running(self) -> bool:
        """プロセスが起動中か(Noneでなく、かつまだ終了していない)"""
        return self._popen is not None and self._popen.poll() is None

    def is_stopped(self) -> bool:
        """プロセスが存在しないか(起動を試みていない/既にNoneに戻された)"""
        return self._popen is None

    def poll(self):
        """生のPopen.poll()と同じ(起動していなければNoneを返す)"""
        return self._popen.poll() if self._popen is not None else None

    def poll_or_kill(self) -> bool:
        """
        状態確認中に例外が起きた場合は強制終了してFalseを返す。
        (Web管理画面のステータス確認で、ハンドルが無効になっている場合への
         既存の防御的な挙動をそのまま引き継いだメソッド)
        """
        try:
            return self._popen.poll() is None
        except Exception:
            if self._popen is not None:
                self._popen.kill()
            return False

    def start(self, command: list, cwd: str, char_code: str, logger_func) -> subprocess.Popen:
        """
        サーバープロセスを起動し、標準出力を読み続けるロガースレッドを開始する。

        logger_func: (proc, ret_deque) を受け取る関数(main.py の server_logger を渡す想定)
        """
        self._popen = subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding=char_code,
        )
        threading.Thread(target=logger_func, args=(self._popen, deque()), daemon=True).start()
        return self._popen

    def write(self, command: str) -> None:
        """標準入力にコマンドを書き込み、即座にflushする"""
        self._popen.stdin.write(command + "\n")
        self._popen.stdin.flush()

    def kill(self) -> None:
        """プロセスを強制終了する(起動していなければ何もしない)"""
        if self._popen is not None:
            self._popen.kill()

    def reset(self) -> None:
        """プロセスが終了した後の後始末(server_loggerスレッドの終了時に呼ばれる)"""
        self._popen = None

    def raw(self) -> subprocess.Popen | None:
        """
        生のPopenオブジェクトが必要な箇所(psutilでメモリ/CPUを調べる既存関数、
        拡張機能向けAPIの get_process() )のための脱出口。
        基本的にはこのメソッドを新たに使う場面を増やさないようにする。
        """
        return self._popen
