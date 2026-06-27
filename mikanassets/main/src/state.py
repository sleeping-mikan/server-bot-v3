"""
state.py — main.py内の複数の関数・コマンド間で共有される、書き換え可能な実行時状態

これまでのコードは `global process` のように関数ごとに `global` 文を書いて
モジュールレベル変数を直接書き換えていたが、この方式には以下の問題がある。

    - どの関数が状態を書き換えているかが`global`文を読むまで分からない
    - 同名のローカル変数(関数の引数など)と紛れやすい
    - テストや別モジュールからの参照・差し替えがしづらい

このモジュールを `import state` した上で `state.xxx` のように属性アクセスする方式に変えることで、
`global` 文を書かずに(=関数のどの行が共有状態を書き換えているかが`state.`という接頭辞で一目で分かる形で)
読み書きできるようにしている。

【commands 分割後のアクセスパターン】
main.py がモジュールレベルで持つ変数のうち、コマンドファイルが必要とするものは
すべて state.py から `import state; state.xxx` でアクセスできるようにしている。
これにより commands/*.py は main から import せずに済む(循環 import を回避)。
"""

from collections import deque
from server_process import ServerProcess
from paths import BotPaths

# --- サーバープロセス ---

# Minecraft(等)サーバーのプロセスを管理するインスタンス(プロセス全体で1つだけ)
server_process = ServerProcess()

# --- ファイルパス ---

# server.pyを基準とした各種パス。main.py起動時にinit_paths()で初期化される。
paths: BotPaths | None = None


def init_paths(base_dir) -> None:
    global paths
    paths = BotPaths(base_dir)


# --- 起動時に確定する値 ---

# Discord bot トークン。make_token_file() で .token ファイルから読み込む。
token: str | None = None

# 一時ファイルの作成先。make_temp() で OS に応じて設定する。
temp_path: str | None = None

# --- 設定・コンテキスト ---

# メインの設定 dict。make_config() で生成後に代入される。
# dict はミュータブルなので、ここへの参照を持つ全コードが常に最新値を参照できる。
config: dict | None = None

# コマンドごとの必要権限レベル。config 読み込み後に代入される。
COMMAND_PERMISSION: dict = {}

# 現在の言語 ("ja" / "en")。/lang コマンドで変更される。
lang: str = ""

# --- テキストデータ (lang が変わるたびに get_text_dat() で再設定) ---

# 言語ごとのヘルプメッセージ辞書
HELP_MSG: dict = {}

# 言語ごとのコマンド説明辞書
COMMAND_DESCRIPTION: dict = {}

# 現在の言語のレスポンスメッセージ辞書
RESPONSE_MSG: dict = {}

# アクティビティ表示名 (起動中/停止中など)
ACTIVITY_NAME: dict = {}

# /help コマンドで返す embed (Discordオブジェクト、起動後に生成)
send_help = None

# --- 実行時フラグ ---

# /stop コマンドで正常停止させた場合に True になる。
# server_logger がプロセス終了を検知したとき、このフラグが False なら異常終了とみなしてエラーログを出す。
use_stop: bool = False

# /cmd serverin の結果を Discord に返すために True にする。
# server_logger がログを cmd_logs に積んだ後、False に戻す。
is_back_discord: bool = False

# /cmd serverin の結果ログキュー。server_logger が書き込み、cmd コマンドが読み出す。
cmd_logs: deque = deque(maxlen=100)

# --- Discord terminal ---

# Discord terminal 送信バッファ。update_loop が積み上げ、1900文字を超えたら送信してリセット。
discord_terminal_item: deque = deque()

# discord_terminal_item の現在の合計文字数。
discord_terminal_send_length: int = 0

# update_loop の多重実行防止フラグ。タスクループは10秒ごとだが処理が長引いた場合の保護。
discord_loop_is_run: bool = False

# ログ転送先の Discord チャンネル ID。False のとき転送無効。
# 初期値は config から main.py の起動処理で設定される。
where_terminal: int | bool = False

# write_server_in() の多重実行防止フラグ。
is_write_server_block: bool = False

# --- 拡張機能ローディング用 ---

# 拡張機能のコマンドグループ。read_extension_commands() がループ内で各拡張ごとに設定し、
# 拡張の commands.py が import される際にここを参照する。ロード完了後は None にリセット。
# 拡張側: `import state; @state.extension_commands_group.command(...)`
extension_commands_group = None

# 拡張機能ごとのロガー。read_extension_commands() が各拡張ごとに設定する。
# 拡張側: `import state; state.extension_logger.info(...)`
extension_logger = None
