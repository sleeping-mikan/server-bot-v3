"""
paths.py — アプリケーションが使うファイルパスを一か所で管理するクラス
"""

from pathlib import Path


class BotPaths:
    """server.py のあるディレクトリを起点に各種パスを提供する。

    Args:
        base_dir: server.py のあるディレクトリの絶対パス。
    """

    def __init__(self, base_dir: str | Path) -> None:
        self.base = Path(base_dir)

    # ── ルート直下 ────────────────────────────────────────────

    @property
    def config_file(self) -> Path:
        return self.base / ".config"

    @property
    def token_file(self) -> Path:
        return self.base / ".token"

    @property
    def logs_dir(self) -> Path:
        return self.base / "logs"

    def log_file(self, name: str) -> Path:
        return self.logs_dir / name

    # ── mikanassets/ ──────────────────────────────────────────

    @property
    def mikanassets_dir(self) -> Path:
        return self.base / "mikanassets"

    @property
    def data_dir(self) -> Path:
        """永続データ置き場。self-update の対象外。"""
        return self.mikanassets_dir / "data"

    @property
    def dat_file(self) -> Path:
        """自己更新用のコミット ID を保持する JSON ファイル。"""
        return self.data_dir / ".dat"

    @property
    def web_tokens_file(self) -> Path:
        """Web 管理画面の認証トークン一覧 JSON。"""
        return self.data_dir / "tokens.json"

    @property
    def extension_dir(self) -> Path:
        return self.mikanassets_dir / "extension"

    def extension_subdir(self, name: str) -> Path:
        return self.extension_dir / name

    # ── mikanassets/main/ (self-update で丸ごと入れ替わる) ────

    @property
    def main_dir(self) -> Path:
        return self.mikanassets_dir / "main"

    @property
    def src_dir(self) -> Path:
        return self.main_dir / "src"

    @property
    def update_apply_file(self) -> Path:
        """自己更新スクリプト。旧パス (src/update_apply.py) から移動済み。"""
        return self.src_dir / "update" / "apply.py"

    @property
    def assets_dir(self) -> Path:
        return self.main_dir / "assets"

    # ── mikanassets/main/web/ (self-update 対象、テンプレート・静的ファイル) ─

    @property
    def web_dir(self) -> Path:
        return self.main_dir / "web"

    @property
    def web_index_file(self) -> Path:
        return self.web_dir / "index.html"

    @property
    def web_login_file(self) -> Path:
        return self.web_dir / "login.html"

    @property
    def web_pictures_dir(self) -> Path:
        return self.web_dir / "pictures"

    @property
    def web_icon_file(self) -> Path:
        return self.web_pictures_dir / "icon.png"
