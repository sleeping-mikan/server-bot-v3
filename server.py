"""
mikan minecraft-discord-bridge bot のエントリポイント

役割:
    - mikanassets/src にプログラム本体が存在するか確認する
    - 存在しない場合は GitHub リポジトリから本体をダウンロードして配置する
    - mikanassets/src/main.py をサブプロセスとして起動する
    - 本体プロセスが終了したら、その終了コードをそのまま引き継いで終了する

このファイル自身は最小限の責務(配置確認・取得・起動)のみを持ち、
Bot/Webサーバーとしての実処理は mikanassets/src 側に存在する。
"""

import os
import sys
import io
import shutil
import zipfile
import urllib.request
import urllib.error

# ------------------------------------------------------------------
# 設定: 本体を配置している GitHub リポジトリ
# ------------------------------------------------------------------
# TODO: リポジトリを公開したら、ここを実際の owner/repo に書き換えてください。
GITHUB_OWNER = "your-github-name"
GITHUB_REPO = "your-repo-name"
GITHUB_BRANCH = "main"

# 上記から自動生成される、ブランチのzipballURL
GITHUB_ZIP_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"

# ------------------------------------------------------------------
# パスの定義
# ------------------------------------------------------------------
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MIKANASSETS_DIR = os.path.join(THIS_DIR, "mikanassets")
SRC_DIR = os.path.join(MIKANASSETS_DIR, "src")
MAIN_FILE = os.path.join(SRC_DIR, "main.py")


def is_src_ready() -> bool:
    """mikanassets/src にプログラム本体(main.py)が既に存在するか確認する"""
    return os.path.isfile(MAIN_FILE)


def download_and_extract_src() -> None:
    """GitHubリポジトリから本体をダウンロードし、mikanassets/src に展開する"""
    print(f"[server.py] mikanassets/src が見つかりません。GitHubから取得します。")
    print(f"[server.py] download: {GITHUB_ZIP_URL}")

    os.makedirs(MIKANASSETS_DIR, exist_ok=True)

    try:
        with urllib.request.urlopen(GITHUB_ZIP_URL, timeout=60) as res:
            zip_bytes = res.read()
    except urllib.error.URLError as e:
        print(f"[server.py] ダウンロードに失敗しました: {e}")
        print("[server.py] ネットワーク接続、またはリポジトリ設定(GITHUB_OWNER/GITHUB_REPO/GITHUB_BRANCH)を確認してください。")
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
        print("[server.py] 想定外のzip構成です。展開結果:", extracted_items)
        sys.exit(1)
    extracted_root = os.path.join(tmp_extract_dir, extracted_items[0])

    # リポジトリ内の src/ ディレクトリ(本体)を mikanassets/src に配置する
    # リポジトリ構成は "リポジトリ直下に src/" を想定。
    # (mikanassets/src を直接リポジトリのルートとして公開しても良い)
    candidate_src = os.path.join(extracted_root, "src")
    if not os.path.isdir(candidate_src):
        candidate_src = extracted_root  # リポジトリ直下がそのまま本体の場合

    if os.path.exists(SRC_DIR):
        shutil.rmtree(SRC_DIR)
    shutil.move(candidate_src, SRC_DIR)

    shutil.rmtree(tmp_extract_dir)

    if not is_src_ready():
        print(f"[server.py] 本体の配置に失敗しました。main.pyが見つかりません: {MAIN_FILE}")
        sys.exit(1)

    print(f"[server.py] 本体を配置しました: {SRC_DIR}")


def run_main() -> int:
    """mikanassets/src/main.py をサブプロセスとして実行し、終了コードを返す"""
    import subprocess

    print(f"[server.py] 起動します: {MAIN_FILE}")
    # 本体に渡された引数(server.py自身への引数)をそのまま引き継ぐ
    args = [sys.executable, MAIN_FILE, *sys.argv[1:]]

    # .config / logs / mikanassets/extension などの各種ファイルは
    # mikanassets/src ではなく、このserver.pyのあるディレクトリを基準にしたいため、
    # 環境変数で基準ディレクトリを明示的に伝える。
    env = os.environ.copy()
    env["MIKAN_BASE_DIR"] = THIS_DIR

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
