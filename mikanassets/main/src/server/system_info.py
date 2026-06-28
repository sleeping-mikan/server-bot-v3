"""
system_info.py — プロセス・スレッドの CPU・メモリ使用率取得ユーティリティ
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import threading

import aiohttp
import psutil


def _mem_bytes(proc: psutil.Process) -> int:
    """プロセスの実メモリ使用量をバイトで返す。Windows は wset、それ以外は rss。"""
    info = proc.memory_info()
    return getattr(info, "wset", None) or info.rss


async def get_process_memory(process: subprocess.Popen | None) -> dict[str, float]:
    MB = 1024 ** 2
    origin_mem = _mem_bytes(psutil.Process(os.getpid())) / MB
    if process is not None:
        parent     = psutil.Process(process.pid)
        children   = parent.children(recursive=True)
        server_mem = (_mem_bytes(parent) + sum(_mem_bytes(psutil.Process(c.pid)) for c in children)) / MB
    else:
        server_mem = 0.0
    return {"origin_mem": origin_mem, "server_mem": server_mem}


async def get_process_cpu() -> float:
    return psutil.cpu_percent(interval=1.0)


async def get_thread_cpu_usage(
    pid:      int,
    interval: float = 1.0,
    is_self:  bool  = False,
) -> dict[str | int, float]:
    proc   = psutil.Process(pid)
    before = {t.id: t.user_time + t.system_time for t in proc.threads()}
    await asyncio.sleep(interval)
    after  = {t.id: t.user_time + t.system_time for t in proc.threads()}

    diff  = {tid: after.get(tid, before[tid]) - before[tid] for tid in before}
    total = sum(diff.values())

    usage: dict[str | int, float] = {
        tid: (diff[tid] / total * 100) if total else 0.0
        for tid in diff
    }

    if is_self:
        name_map = {t.ident: t.name for t in threading.enumerate()}
        named: dict[str | int, float] = {}
        no_name = 1
        for tid, val in usage.items():
            name = name_map.get(tid)
            if name:
                named[name] = val
            else:
                named[f"NoName {no_name}"] = val
                no_name += 1
        usage = named

    process_cpu = await get_process_cpu()
    return {k: v / 100 * process_cpu for k, v in usage.items()}


async def check_response(url: str = "http://127.0.0.1") -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
    except aiohttp.ClientError:
        return False
