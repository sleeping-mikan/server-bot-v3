"""
server-bot-v3 のエントリポイント

役割:
    - mikanassets/src にプログラム本体が存在するか確認する
    - 存在しない場合は GitHub リポジトリから本体をダウンロードして配置する
    - mikanassets/src/main.py をサブプロセスとして起動する
    - 本体プロセスが終了したら、その終了コードをそのまま引き継いで終了する

このファイル自身は最小限の責務(配置確認・取得・起動)のみを持ち、
Bot/Webサーバーとしての実処理は mikanassets/src 側に存在する。
"""

import io
import logging
import os
import shutil
import sys
import zipfile
import urllib.request
import urllib.error

# ------------------------------------------------------------------
# ロガー設定
# 本体 (log_setup.py) の ColoredFormatter / PlainFormatter に合わせた書式を再現する。
# server.py は単体スクリプトのため core モジュールを使わず直接定義する。
# ------------------------------------------------------------------
_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_LEVEL_W  = 8
_NAME_W   = 10

_RESET    = '\033[0m'
_DT_COLOR = '\033[1m\033[30m'   # BOLD + BLACK
_LEVEL_COLORS = {
    'DEBUG':    '\033[1m\033[37m',  # BOLD + WHITE
    'INFO':     '\033[1m\033[34m',  # BOLD + BLUE
    'WARNING':  '\033[1m\033[33m',  # BOLD + YELLOW
    'ERROR':    '\033[1m\033[31m',  # BOLD + RED
    'CRITICAL': '\033[1m\033[35m',  # BOLD + MAGENTA
}


class _ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dt    = f"{_DT_COLOR}{self.formatTime(record, self.datefmt)}{_RESET}"
        level = f"{_LEVEL_COLORS.get(record.levelname, '')}{record.levelname.ljust(_LEVEL_W)}{_RESET}"
        name  = record.name.ljust(_NAME_W)
        return f"{dt} {level} {name}: {record.getMessage()}"


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_ColoredFormatter(datefmt=_DATE_FMT))

_logger = logging.getLogger("server.py")
_logger.setLevel(logging.INFO)
_logger.addHandler(_handler)

# ------------------------------------------------------------------
# 設定: 本体を配置している GitHub リポジトリ
# ------------------------------------------------------------------
# TODO: リポジトリを公開したら、ここを実際の owner/repo に書き換えてください。
GITHUB_OWNER  = "sleeping-mikan"
GITHUB_REPO   = "server-bot-v3"
GITHUB_BRANCH = "main"

# 上記から自動生成される、ブランチのzipballURL
GITHUB_ZIP_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"

# ------------------------------------------------------------------
# パスの定義
# ------------------------------------------------------------------
THIS_DIR        = os.path.dirname(os.path.abspath(__file__))
MIKANASSETS_DIR = os.path.join(THIS_DIR, "mikanassets")
MAIN_DIR        = os.path.join(MIKANASSETS_DIR, "main")
SRC_DIR         = os.path.join(MAIN_DIR, "src")
MAIN_FILE       = os.path.join(SRC_DIR, "main.py")


def is_src_ready() -> bool:
    """mikanassets/src にプログラム本体(main.py)が既に存在するか確認する"""
    return os.path.isfile(MAIN_FILE)


def download_and_extract_src() -> None:
    """GitHubリポジトリから本体をダウンロードし、mikanassets/src に展開する"""
    _logger.info("mikanassets/src not found. Downloading from GitHub.")
    _logger.info(f"download: {GITHUB_ZIP_URL}")

    os.makedirs(MIKANASSETS_DIR, exist_ok=True)

    try:
        with urllib.request.urlopen(GITHUB_ZIP_URL, timeout=60) as res:
            zip_bytes = res.read()
    except urllib.error.URLError as e:
        _logger.error(f"Download failed: {e}")
        _logger.error("Check your network connection or repository settings (GITHUB_OWNER/GITHUB_REPO/GITHUB_BRANCH).")
        sys.exit(1)

    # zipを一時フォルダに展開する
    tmp_extract_dir = os.path.join(MIKANASSETS_DIR, "_download_tmp")
    if os.path.exists(tmp_extract_dir):
        shutil.rmtree(tmp_extract_dir)
    os.makedirs(tmp_extract_dir, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(tmp_extract_dir)

    # GitHubのzipballは "{repo}-{branch}/" という単一のルートフォルダを持つので、それを探す
    extracted_items = os.listdir(tmp_extract_dir)
    if len(extracted_items) != 1:
        _logger.error(f"Unexpected zip structure: {extracted_items}")
        sys.exit(1)
    extracted_root = os.path.join(tmp_extract_dir, extracted_items[0])

    # リポジトリ内の mikanassets/main/ ディレクトリ(本体 src/ と データ assets/ の両方を含む)を
    # mikanassets/main に配置する。リポジトリ構成は「リポジトリ直下に mikanassets/main/」を想定
    # (ローカル配置と一致させている)。
    candidate_main = os.path.join(extracted_root, "mikanassets", "main")
    if not os.path.isdir(candidate_main):
        # 後方互換: 旧構成(mikanassets/src/ や 直下src/、main/フォルダが無くsrcのみの場合)
        candidate_src = os.path.join(extracted_root, "mikanassets", "src")
        if not os.path.isdir(candidate_src):
            candidate_src = os.path.join(extracted_root, "src")
            if not os.path.isdir(candidate_src):
                candidate_src = extracted_root
        if os.path.exists(SRC_DIR):
            shutil.rmtree(SRC_DIR)
        os.makedirs(MAIN_DIR, exist_ok=True)
        shutil.move(candidate_src, SRC_DIR)
    else:
        if os.path.exists(MAIN_DIR):
            shutil.rmtree(MAIN_DIR)
        os.makedirs(MIKANASSETS_DIR, exist_ok=True)
        shutil.move(candidate_main, MAIN_DIR)

    shutil.rmtree(tmp_extract_dir)

    if not is_src_ready():
        _logger.error(f"Failed to place main module. main.py not found: {MAIN_FILE}")
        sys.exit(1)

    _logger.info(f"Main module placed: {MAIN_DIR}")


def run_main() -> int:
    """mikanassets/src/main.py をサブプロセスとして実行し、終了コードを返す"""
    import subprocess

    _logger.info(f"Starting: {MAIN_FILE}")
    # 本体に渡された引数(server.py自身への引数)をそのまま引き継ぐ
    args = [sys.executable, MAIN_FILE, *sys.argv[1:]]

    # .config / logs / mikanassets/extension などの各種ファイルは
    # mikanassets/src ではなく、このserver.pyのあるディレクトリを基準にしたいため、
    # 環境変数で基準ディレクトリを明示的に伝える。
    env = os.environ.copy()
    env["MIKAN_BASE_DIR"]   = THIS_DIR
    env["MIKAN_ENTRY_FILE"] = os.path.basename(os.path.abspath(__file__))

    # cwdもTHIS_DIR(server.py基準)にしておく(相対パス指定の挙動を揃えるため)
    proc = subprocess.run(args, cwd=THIS_DIR, env=env)
    return proc.returncode


def main() -> None:
    if not is_src_ready():
        download_and_extract_src()

    exit_code = run_main()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
