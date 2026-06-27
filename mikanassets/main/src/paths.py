"""
paths.py — server.py(エントリファイル)を基準とした各種パスをまとめて扱うクラス

これまでは `now_path + "/" + ".config"` や `os.path.join(now_path, "mikanassets", ".dat")` のように、
同じ基準ディレクトリ(now_path)からの相対パスを文字列結合で都度組み立てていた。
これを `BotPaths` クラスに集約し、`pathlib.Path` で統一的に扱うようにする。

使い方:
    from paths import BotPaths
    paths = BotPaths(now_path)
    paths.config_file        # -> Path(now_path) / ".config"
    paths.logs_dir           # -> Path(now_path) / "logs"
    paths.log_file("foo.log")  # -> Path(now_path) / "logs" / "foo.log"

既存コードとの橋渡しのため、文字列が必要な場所では `str(paths.xxx)` または
`paths.xxx.as_posix()` (常に "/" 区切りにしたい場合) を使う。
"""

from pathlib import Path


class BotPaths:
    def __init__(self, base_dir):
        self.base = Path(base_dir)

    # --- ルート直下 ---

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

    # --- mikanassets/ ---

    @property
    def mikanassets_dir(self) -> Path:
        return self.base / "mikanassets"

    @property
    def extension_dir(self) -> Path:
        return self.mikanassets_dir / "extension"

    def extension_subdir(self, name: str) -> Path:
        return self.extension_dir / name

    @property
    def dat_file(self) -> Path:
        return self.mikanassets_dir / ".dat"

    # --- mikanassets/main/ (本体プログラム。self-updateで丸ごと入れ替わる) ---

    @property
    def main_dir(self) -> Path:
        return self.mikanassets_dir / "main"

    @property
    def src_dir(self) -> Path:
        return self.main_dir / "src"

    @property
    def update_apply_file(self) -> Path:
        return self.src_dir / "update_apply.py"

    @property
    def assets_dir(self) -> Path:
        return self.main_dir / "assets"

    # --- mikanassets/main/web/ (Web管理画面テンプレート・静的ファイル) ---
    # mikanassets/main/ に含まれるため、self-update で自動的に入れ替わる。

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

    # --- mikanassets/web/usr/ (ユーザーデータ) ---
    # mikanassets/main/ の外に置くことで、self-update の影響を受けない。

    @property
    def web_usr_dir(self) -> Path:
        return self.mikanassets_dir / "web" / "usr"

    @property
    def web_tokens_file(self) -> Path:
        return self.web_usr_dir / "tokens.json"
