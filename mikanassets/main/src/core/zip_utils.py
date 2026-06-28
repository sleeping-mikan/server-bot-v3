"""
core/zip_utils.py — zip 展開ユーティリティ

bot と web の両方から利用する。
Zip slip 攻撃（../../../ などのパス）を防ぐため、
展開先が ctx.server_path 以下に収まることを確認してから展開する。
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from core.path_utils import is_path_within_scope


def safe_unzip(zip_path: Path, dest_dir: Path) -> int:
    """zip_path を dest_dir に安全に展開し、展開したエントリ数を返す。

    Raises:
        ValueError: zip 内に scope 外のパスが含まれていた場合
        zipfile.BadZipFile: 壊れた / 不正な zip の場合
    """
    count = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            target = (dest_dir / info.filename).resolve(strict=False)
            if not is_path_within_scope(target):
                raise ValueError(info.filename)
            zf.extract(info, dest_dir)
            count += 1
    return count
