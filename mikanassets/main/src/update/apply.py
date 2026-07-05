"""
update/apply.py — 自己更新の実行役

main.py から `subprocess.Popen` で子プロセスとして起動される。役割は以下の通り:
    1. ダウンロード済みの新しいリポジトリ内容で mikanassets/main (src + assets) を入れ替える
    2. server.py (エントリファイル) 自体も新しい内容に入れ替える
    3. Discord の完了報告メッセージを REST API で直接編集する (可能な場合)
    4. server.py を再起動する (subprocess.Popen で子プロセスとして起動)

旧パス: mikanassets/main/src/update_apply.py
新パス: mikanassets/main/src/update/apply.py
core/paths.py の update_apply_file プロパティも合わせて更新済み。

このファイルは mikanassets/main/src/update/ に置かれたまま実行される。
Python はスクリプトの実行開始時点で既にソースを読み込み済みのため、
実行中に自分自身が含まれるディレクトリを移動・削除しても動作に影響しない。

引数 (sys.argv):
    argv[1]: new_repo_root   ダウンロード・展開済みの新しいリポジトリのルートパス
    argv[2]: now_path        server.py を基準とするベースディレクトリ
    argv[3]: now_file        エントリファイル名 (通常 "server.py")
    argv[4]: msg_id          完了報告先の Discord メッセージ ID ("0" なら報告しない)
    argv[5]: channel_id      完了報告先の Discord チャンネル ID ("0" なら報告しない)

環境変数 MIKAN_BOT_TOKEN に完了報告メッセージ編集用の Bot トークンを渡す。
"""

import os
import sys
import shutil
import subprocess
import time
import json
import logging
import traceback


# 本体 (log_setup.py) の ColoredFormatter / PlainFormatter に合わせた書式を再現する。
# update/apply.py は単体スクリプトのため core モジュールを使わず直接定義する。
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


class _PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dt    = self.formatTime(record, self.datefmt)
        level = record.levelname.ljust(_LEVEL_W)
        name  = record.name.ljust(_NAME_W)
        return f"{dt} {level} {name}: {record.getMessage()}"


def setup_logger(now_path: str) -> logging.Logger:
    """ファイル (PlainFormatter) + コンソール (ColoredFormatter) のロガーを返す。

    書式は本体の log_setup.py に合わせる:
        {datetime} {level:-8} {name:-10}: {message}
    """
    logger = logging.getLogger("update.apply")
    logger.setLevel(logging.INFO)

    log_dir = os.path.join(now_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_dir, "update_apply.log"), encoding="utf-8")
    fh.setFormatter(_PlainFormatter(datefmt=_DATE_FMT))
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(_ColoredFormatter(datefmt=_DATE_FMT))
    logger.addHandler(sh)

    return logger


def report_to_discord(channel_id: str, msg_id: str, token: str, field_value: str, logger: logging.Logger) -> None:
    """discord.py クライアントを起動せず REST API で直接メッセージの embed を編集する。

    channel_id / msg_id のいずれかが "0" の場合は何もしない。
    既存メッセージの embed を取得してフィールドを追加する。
    ネットワークエラーはログに記録するが例外を伝播させない (更新処理の中断を防ぐ)。
    """
    if channel_id == "0" or msg_id == "0" or not token:
        return
    try:
        import requests
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{msg_id}"
        headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}

        get_res = requests.get(url, headers=headers, timeout=10)
        if get_res.status_code >= 300:
            logger.error(f"discord fetch failed: status={get_res.status_code} body={get_res.text}")
            return

        msg_data = get_res.json()
        embeds = msg_data.get("embeds", [])
        embed = embeds[0] if embeds else {}
        embed.setdefault("fields", [])
        embed["fields"].append({"name": "", "value": field_value, "inline": False})

        res = requests.patch(url, headers=headers, data=json.dumps({"embeds": [embed]}), timeout=10)
        if res.status_code >= 300:
            logger.error(f"discord report failed: status={res.status_code} body={res.text}")
    except Exception:
        logger.error("discord report failed:\n" + traceback.format_exc())


def replace_main(new_repo_root: str, now_path: str, logger: logging.Logger) -> None:
    """mikanassets/main (src/ と assets/ をまとめて) を新しい内容に入れ替える。

    入れ替え手順:
        1. 現在の mikanassets/main を main_backup_before_update へ退避する
        2. 新しい mikanassets/main を配置する
        3. 成功ならバックアップを削除、失敗ならバックアップを戻す
    """
    new_main_dir = os.path.join(new_repo_root, "mikanassets", "main")
    if not os.path.isdir(new_main_dir):
        raise RuntimeError(f"new repository does not contain mikanassets/main/: {new_main_dir}")

    current_main_dir = os.path.join(now_path, "mikanassets", "main")
    backup_main_dir  = os.path.join(now_path, "mikanassets", "main_backup_before_update")

    # 既存バックアップがあれば先に消す (前回の更新が中断したケース)
    if os.path.exists(backup_main_dir):
        shutil.rmtree(backup_main_dir)
    if os.path.exists(current_main_dir):
        shutil.move(current_main_dir, backup_main_dir)

    try:
        shutil.move(new_main_dir, current_main_dir)
    except Exception:
        # 配置に失敗した場合はバックアップから元に戻してロールバック
        logger.error("failed to move new mikanassets/main. rolling back.\n" + traceback.format_exc())
        if os.path.exists(current_main_dir):
            shutil.rmtree(current_main_dir)
        if os.path.exists(backup_main_dir):
            shutil.move(backup_main_dir, current_main_dir)
        raise
    else:
        # 配置成功: バックアップは不要なので削除する
        if os.path.exists(backup_main_dir):
            shutil.rmtree(backup_main_dir)

    logger.info(f"replaced mikanassets/main -> {current_main_dir}")


def replace_entry_file(new_repo_root: str, now_path: str, now_file: str, logger: logging.Logger) -> None:
    """エントリファイル (通常 server.py) を新しいものに上書きする。

    新しいリポジトリに server.py が存在しない場合はスキップ (エラーログのみ)。
    """
    new_server_py = os.path.join(new_repo_root, "server.py")
    if not os.path.isfile(new_server_py):
        logger.error(f"new repository does not contain server.py: {new_server_py} (skip entry file update)")
        return
    dst_server_py = os.path.join(now_path, now_file)
    shutil.copy2(new_server_py, dst_server_py)
    logger.info(f"replaced entry file -> {dst_server_py}")


def cleanup_temp(new_repo_root: str, logger: logging.Logger) -> None:
    """解凍した一時ディレクトリ (new_repo_root の親) を削除する。

    new_repo_root は temp_path/new_repo/{repo}-{branch} の形なので、
    その親 (temp_path/new_repo) をまるごと削除する。
    失敗しても更新自体は完了しているためエラーログだけ記録して続行する。
    """
    tmp_dir = os.path.dirname(new_repo_root)
    try:
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
    except Exception:
        logger.error("failed to cleanup temp dir:\n" + traceback.format_exc())


def restart(now_path: str, now_file: str, logger: logging.Logger) -> None:
    """server.py を子プロセスとして起動し、自分は即終了する。

    os.execv は Windows 環境でプロセスがクラッシュする (STATUS_ACCESS_VIOLATION)
    ことが確認されたため使用しない。
    """
    server_py_path = os.path.join(now_path, now_file)
    logger.info(f"restarting -> {server_py_path}")
    os.chdir(now_path)
    # DETACHED_PROCESS は子のコンソール出力が消えるため使わない。コンソールは継承する。
    subprocess.Popen([sys.executable, server_py_path], close_fds=True)
    os._exit(0)


def main() -> None:
    if len(sys.argv) < 6:
        print("usage: update/apply.py <new_repo_root> <now_path> <now_file> <msg_id> <channel_id>")
        sys.exit(1)

    new_repo_root, now_path, now_file, msg_id, channel_id = sys.argv[1:6]
    token = os.environ.get("MIKAN_BOT_TOKEN", "")

    logger = setup_logger(now_path)
    logger.info("update/apply.py start")
    logger.info(f"new_repo_root={new_repo_root} now_path={now_path} now_file={now_file}")

    # 直前のプロセス (main.py) がファイルハンドルを完全に閉じるまで少し待つ
    time.sleep(1.0)

    try:
        replace_main(new_repo_root, now_path, logger)
        replace_entry_file(new_repo_root, now_path, now_file, logger)
        cleanup_temp(new_repo_root, logger)
    except Exception:
        logger.error("update failed:\n" + traceback.format_exc())
        report_to_discord(channel_id, msg_id, token, "update failed. check logs/update_apply.log", logger)
        sys.exit(1)

    report_to_discord(channel_id, msg_id, token, "update complete. restarting...", logger)
    restart(now_path, now_file, logger)


if __name__ == "__main__":
    main()
