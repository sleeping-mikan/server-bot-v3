"""
download_server.py — /cmd stdin send-discord 用の一時ダウンロードサーバー

FastAPI エンドポイント /download/{token} を提供する。
SendDiscordSelfServer.create_app() で FastAPI アプリを生成し、main.py の uvicorn に mount する。
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import zipstream
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

import logging as _logging

from core.state import ctx

# "web" ロガーは LogManager.init() 後に親として設定される
_logger = _logging.getLogger("web.download")


async def _get_directory_size(path: str) -> int:
    size = 0
    for entry in Path(path).iterdir():
        if entry.is_file():
            size += entry.stat().st_size
        elif entry.is_dir():
            size += await _get_directory_size(str(entry))
    return size


class SendDiscordSelfServer:
    _download_registry: dict[str, tuple[str, datetime]] = {}
    _lock = asyncio.Lock()
    _ttl_default = 300  # 秒

    @classmethod
    async def register_download(
        cls, path: str, ttl_seconds: int | None = None
    ) -> tuple[bool, str | list]:
        ttl = ttl_seconds or cls._ttl_default
        token = uuid.uuid4().hex
        expire_at = datetime.now() + timedelta(seconds=ttl)
        bits_capacity = ctx.config["discord_commands"]["cmd"]["stdin"]["send_discord"]["bits_capacity"]
        p = Path(path)
        dir_size = await _get_directory_size(path) if p.is_dir() else p.stat().st_size
        if dir_size > bits_capacity:
            return False, [1, str(dir_size), str(bits_capacity)]
        async with cls._lock:
            cls._download_registry[token] = (path, expire_at)
        _logger.info(f"register download -> {path} ({dir_size} Bytes)")
        return True, f"http://{ctx.web_ip}:{ctx.web_port}/download/{token}"

    @classmethod
    async def _cleanup_loop(cls) -> None:
        while True:
            now = datetime.now()
            async with cls._lock:
                expired = [t for t, (_, exp) in cls._download_registry.items() if now > exp]
                for t in expired:
                    del cls._download_registry[t]
                    _logger.info(f"cleanup download -> {t}")
            await asyncio.sleep(30)

    @classmethod
    async def download(cls, token: str):
        async with cls._lock:
            entry = cls._download_registry.pop(token, None)
        if not entry:
            _logger.info(f"download not found -> {token}")
            raise HTTPException(status_code=404, detail="リンクが無効または既に使用されました")
        path, expire_at = entry
        if datetime.now() > expire_at:
            _logger.info(f"download expired -> {token}")
            raise HTTPException(status_code=410, detail="このリンクは期限切れです")
        z = zipstream.ZipStream()
        z.add_path(path)
        _logger.info(f"download -> {path}")
        filename = Path(path).name or "download"
        return StreamingResponse(
            z,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}.zip"'},
        )

    @classmethod
    def create_app(cls) -> FastAPI:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            task = asyncio.create_task(cls._cleanup_loop())
            yield
            task.cancel()

        app = FastAPI(lifespan=lifespan)
        app.add_api_route("/download/{token}", cls.download, methods=["GET"])
        return app
