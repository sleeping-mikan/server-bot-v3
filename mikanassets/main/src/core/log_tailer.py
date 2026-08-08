"""
core/log_tailer.py — ログの逐次読み取り (tail -f 相当)

インスタンス化した後 `async for line in tailer:` で使う。既存の行を順に返し、
以降は新しく追加された行が来るまでポーリングで待ち続ける無限非同期イテレータ。
呼び出し側で break/return するまで終わらない。

ファイルではなく LogManager.snapshot_log_msg() (常時貯まる共有バッファのgetter)
をデフォルトのソースにする。log_all=False (ログをファイルへ出力しない設定) でも
snapshot_log_msg() は常に最新の中身を返すため、ファイルの有無に左右されない。
getter越しにしか触らないので、LogManager側の内部表現(deque)には依存しない。

tail 開始時点でソースが空だった場合は LogTailerEmptyError を送出する。

依存: 標準ライブラリ + core.log_setup。asyncio ベース (extension/bot どちらの
イベントループからも使える)。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Sequence

from core.log_setup import LogManager


class LogTailerEmptyError(Exception):
    """tail 開始時点でソースが空だった場合に送出される。"""


class LogTailer:
    def __init__(
        self,
        source: Callable[[], Sequence[str]] = LogManager.snapshot_log_msg,
        poll_interval: float = 1.0,
    ) -> None:
        self._get_source = source
        self.poll_interval = poll_interval

    async def __aiter__(self) -> AsyncIterator[str]:
        snapshot = list(self._get_source())
        if not snapshot:
            raise LogTailerEmptyError("log is empty")
        for line in snapshot:
            yield line
        last_line = snapshot[-1]

        while True:
            current = list(self._get_source())
            try:
                # 末尾から last_line を探し、それより後ろを「未処理の新規分」とする
                cut = len(current) - current[::-1].index(last_line)
            except ValueError:
                # maxlen 超過で last_line 自体が退避済み: 追跡不能なので現在の内容を丸ごと新規扱いにする
                cut = 0
            new_lines = current[cut:]
            if not new_lines:
                await asyncio.sleep(self.poll_interval)
                continue
            for line in new_lines:
                yield line
            last_line = new_lines[-1]
