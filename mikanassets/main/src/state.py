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

さらに、サーバープロセスについては単なる値(生のsubprocess.Popen)を置くのではなく、
`ServerProcess`クラス(server_process.py)のインスタンスを置くことで、
「起動する/コマンドを送る/状態を確認する」といった操作そのものもこのクラスに集約している。

現時点では server_process(サーバープロセス) のみをここに移行済み。
他の共有グローバル変数(config/token/lang/use_stop 等)は段階的に移行予定
(MIGRATION.md参照)。
"""

from server_process import ServerProcess
from paths import BotPaths

# Minecraft(等)サーバーのプロセスを管理するインスタンス(プロセス全体で1つだけ)
server_process = ServerProcess()

# server.pyを基準とした各種パス。main.py起動時にinit_paths()で初期化される。
paths: BotPaths | None = None


def init_paths(base_dir) -> None:
    global paths
    paths = BotPaths(base_dir)

