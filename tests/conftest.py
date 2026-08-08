"""tests/conftest.py — pytest 共通設定

mikanassets/main/src 以下は `core.state` のような絶対importを前提にしている
(main.py が実行時にそのディレクトリを sys.path に持つ想定のため)。
pytest から同じ import を可能にするため、ここで sys.path に追加する。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "mikanassets" / "main" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.paths import BotPaths  # noqa: E402
from core.state import ctx  # noqa: E402


@pytest.fixture
def app_ctx(tmp_path, monkeypatch):
    """ctx をテスト用の一時ディレクトリに向けて隔離する。

    ctx はアプリ全体で1つだけ生成されるシングルトンなので、
    monkeypatch でテストごとに属性を差し替え、テスト終了時に自動で元に戻す。
    """
    monkeypatch.setattr(ctx, "server_path", tmp_path)
    monkeypatch.setattr(ctx, "paths", BotPaths(tmp_path))
    monkeypatch.setattr(
        ctx,
        "config",
        {
            "discord_commands": {
                "cmd": {
                    "stdin": {
                        "sys_files": [".config", ".token", "logs", "mikanassets"],
                    },
                },
            },
        },
    )
    monkeypatch.delenv("MIKAN_ENTRY_FILE", raising=False)
    return ctx
