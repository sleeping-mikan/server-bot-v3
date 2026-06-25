"""
update_apply.py — 自己更新の実行役

main.py から `os.execv` で起動される。役割は以下の通り:
    1. ダウンロード済みの新しいリポジトリ内容で mikanassets/main(src+assets)を入れ替える
    2. server.py(エントリファイル)自体も新しい内容に入れ替える
    3. Discordの完了報告メッセージを編集する(可能な場合)
    4. server.py を再起動する

このファイルは mikanassets/main/src/update_apply.py に置かれたまま実行される
(要望により、mikanassets直下への複製は行わない)。
Pythonはスクリプトの実行開始時点で既にソースを読み込み済みのため、
実行中に自分自身が含まれるディレクトリを移動・削除しても動作に影響しない。

引数:
    argv[1]: new_repo_root   ダウンロード・展開済みの新しいリポジトリのルートパス
    argv[2]: now_path        server.py を基準とするベースディレクトリ
    argv[3]: now_file        エントリファイル名 (通常 "server.py")
    argv[4]: msg_id          完了報告先のDiscordメッセージID ("0"なら報告しない)
    argv[5]: channel_id      完了報告先のDiscordチャンネルID ("0"なら報告しない)
    argv[6]: token           完了報告メッセージ編集に使うBotトークン
"""

import os
import sys
import shutil
import time
import json
import logging
import traceback


def setup_logger(now_path: str) -> logging.Logger:
    logger = logging.getLogger("update_apply")
    logger.setLevel(logging.INFO)
    log_dir = os.path.join(now_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    handler = logging.FileHandler(os.path.join(log_dir, "update_apply.log"), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s: %(message)s"))
    logger.addHandler(handler)
    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s: %(message)s"))
    logger.addHandler(stream)
    return logger


def report_to_discord(channel_id: str, msg_id: str, token: str, content: str, logger: logging.Logger) -> None:
    """discord.pyのクライアントを起動せず、REST APIで直接メッセージを編集する"""
    if channel_id == "0" or msg_id == "0" or not token:
        return
    try:
        import requests
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{msg_id}"
        headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
        res = requests.patch(url, headers=headers, data=json.dumps({"content": content}), timeout=10)
        if res.status_code >= 300:
            logger.error(f"discord report failed: status={res.status_code} body={res.text}")
    except Exception:
        logger.error("discord report failed:\n" + traceback.format_exc())


def replace_main(new_repo_root: str, now_path: str, logger: logging.Logger) -> None:
    """mikanassets/main(src/ と assets/ をまとめて)を新しい内容に入れ替える"""
    new_main_dir = os.path.join(new_repo_root, "mikanassets", "main")
    if not os.path.isdir(new_main_dir):
        raise RuntimeError(f"new repository does not contain mikanassets/main/: {new_main_dir}")

    current_main_dir = os.path.join(now_path, "mikanassets", "main")
    backup_main_dir = os.path.join(now_path, "mikanassets", "main_backup_before_update")

    # 失敗時に戻せるよう、入れ替え前に一旦バックアップへ退避してから新しいものを配置する
    if os.path.exists(backup_main_dir):
        shutil.rmtree(backup_main_dir)
    if os.path.exists(current_main_dir):
        shutil.move(current_main_dir, backup_main_dir)

    try:
        shutil.move(new_main_dir, current_main_dir)
    except Exception:
        # 失敗したらバックアップを戻す
        logger.error("failed to move new mikanassets/main. rolling back.\n" + traceback.format_exc())
        if os.path.exists(current_main_dir):
            shutil.rmtree(current_main_dir)
        if os.path.exists(backup_main_dir):
            shutil.move(backup_main_dir, current_main_dir)
        raise
    else:
        # 成功したらバックアップは削除する
        if os.path.exists(backup_main_dir):
            shutil.rmtree(backup_main_dir)

    logger.info(f"replaced mikanassets/main -> {current_main_dir}")


def replace_entry_file(new_repo_root: str, now_path: str, now_file: str, logger: logging.Logger) -> None:
    new_server_py = os.path.join(new_repo_root, "server.py")
    if not os.path.isfile(new_server_py):
        logger.error(f"new repository does not contain server.py: {new_server_py} (skip entry file update)")
        return
    dst_server_py = os.path.join(now_path, now_file)
    shutil.copy2(new_server_py, dst_server_py)
    logger.info(f"replaced entry file -> {dst_server_py}")


def cleanup_temp(new_repo_root: str, logger: logging.Logger) -> None:
    # new_repo_root は temp_path/new_repo/{repo}-{branch} の形なので、
    # その親(temp_path/new_repo)をまるごと削除する
    tmp_dir = os.path.dirname(new_repo_root)
    try:
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
    except Exception:
        logger.error("failed to cleanup temp dir:\n" + traceback.format_exc())


def restart(now_path: str, now_file: str, logger: logging.Logger) -> None:
    server_py_path = os.path.join(now_path, now_file)
    logger.info(f"restarting -> {server_py_path}")
    os.chdir(now_path)
    os.execv(sys.executable, [sys.executable, server_py_path])


def main() -> None:
    if len(sys.argv) < 7:
        print("usage: update_apply.py <new_repo_root> <now_path> <now_file> <msg_id> <channel_id> <token>")
        sys.exit(1)

    new_repo_root, now_path, now_file, msg_id, channel_id, token = sys.argv[1:7]

    logger = setup_logger(now_path)
    logger.info("update_apply.py start")
    logger.info(f"new_repo_root={new_repo_root} now_path={now_path} now_file={now_file}")

    # 直前のプロセス(main.py)がファイルハンドルを完全に閉じるまで少し待つ
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
