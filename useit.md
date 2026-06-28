# 使い方

## コマンド一覧

プログラムに含まれる Discord bot コマンドは以下の通りです。

なお必要権限レベルは各階層に生成される `.config` から変更できます。

|コマンド|実行結果|初期必要権限レベル|
|----|----|----|
|help|Discord 上に help と web リンクを表示します。web サイトへ外部からアクセスするには追加のポート開放が必要です。|0|
|ip|この bot(サーバー)が実行している IP アドレスを返します。|0(config によって有効/無効)|
|start|サーバーを開始します。なお、`server.py` 起動時には自動的に開始されます。|1|
|stop|サーバーを停止します。なお `server.py` は実行状態から遷移しないため、他のコマンドを使用できます。|1|
|exit|`server.py` を終了します(このコマンドを利用すると次回サーバー管理者が `server.py` を起動するまで bot を利用できません)。サーバー停止中にのみ使用できます。|2|
|backup create \<path\>|サーバーデータをバックアップします。|1|
|backup apply \<witch\> \<path(optional)\>|バックアップを指定したディレクトリに展開します。path が与えられない場合直上に展開します。|3|
|cmd serverin \<server command\>|サーバーに対してコマンドを送信します。|1|
|cmd stdin ls \<path\>|ディレクトリ内のファイル一覧を返します。root ディレクトリはサーバー直上になります。|2|
|cmd stdin mk \<path\> \<file(optional)\>|ファイルを作成または上書きします。file 引数を渡さない場合空のファイルを作成します。|3(*1)|
|cmd stdin rm \<path\>|指定されたファイルが存在した場合削除します。|2(*1)|
|cmd stdin rmdir \<path\>|指定されたディレクトリが存在した場合削除します。このコマンドは指定されたディレクトリ内に対して再帰的に適用されます。|2(*1)|
|cmd stdin mkdir \<path\>|指定されたディレクトリを作成します。|2(*2)|
|cmd stdin send-discord \<path\>|指定されたファイルを Discord に送信します。|2(*2)|
|cmd stdin wget \<url\> \<path(optional)\>|指定のパスのファイルを url から得られたデータで上書きします。path 引数を渡さない場合直上にファイルを生成します。|3(*1)|
|cmd stdin mv \<src\> \<dest\>|指定した path を dest に移動します。|3(*1)|
|cmd stdin unzip \<path\>|指定した .zip ファイルをそのディレクトリに展開します。|2(*2)|
|logs \<file(optional)\>|サーバーログを表示します。引数が与えられた場合には該当のファイルから、与えられない場合には現在のサーバーログを表示できる限り表示します。|1|
|lang \<"ja"/"en"\>|サーバーの言語を変更します。|2|
|permission change \<level\> \<user\>|ユーザーの bot 利用権限を操作します。|4|
|permission view \<user\> \<detail True/False\>|プレイヤーの権限を表示します。|0|
|tokengen|web アクセスのためのトークンを生成します。web ログイン画面で入力してください。|1|
|update \<is_force True/False\>|GitHub にアクセスして最新の本体をダウンロードします。is_force 引数を与えると強制的にダウンロードします。|3|
|announce embed \<file/txt\>|通常のテキストまたは [mimd](https://github.com/sleeping-mikan/server-bot-v2/blob/main/py-builder/mimd.md) 形式のテキストまたはファイルを指定して bot として Discord にメッセージを送信します。テキストの場合改行には \n を利用してください。|4|
|terminal set \<ch(optional)\>|Discord のチャンネル ID を与えるとサーバーのログを Discord に送信します。また標準入力を受け取ります。|1|
|terminal del|ターミナルの紐づけを解除します。|1|
|status|現在のサーバーの状態を表示します。|0|

*1 : 一部のファイル/ディレクトリに対した操作は行いません。ただし Discord 管理者権限を保持した上で、config 上の `enable_advanced_features` を `true` にすることで操作可能となります。

*2 : 一部のファイル/ディレクトリに対した操作は行いません。

これらコマンドの設定等は後述の使用方法を参照してください。

---

## 設置

`server.py` を任意の場所に配置します。

> [!NOTE]
> 推奨ディレクトリは実行する `server.[exe/jar]` が存在する階層です。その場所が root ディレクトリとなり、一部の権限を持つ Discord ユーザーはファイル操作を行えます。

> [!NOTE]
> ただし `server.exe` や `server.jar` 本体が存在する階層は root(Windows の場合 c:/ 直上など)でない必要があります。(何らかのディレクトリの中に入れてください。)これは初期状態では `../backup/` 内にバックアップが生成されるためです。

## 実行

ライブラリのインストール(`pip install -r requirements.txt`)後、`server.py` を実行します。

`server.py` を実行すると `server.py` と同じ階層に `.config` と `.token` が生成されます。

コンソール引数(これらは任意ですが、エラーが発生する場合などに利用してください)
- `-init` `update.py` などの一部 `server.py` からダウンロードされるファイルを再度ダウンロード

> [!NOTE]
> この際 `.token` が生成されない場合、`.config` 内の `server_path + server_name` が存在していないので、サーバーが存在するパス+拡張子を含むサーバーのファイル名に変更してください。

## 初期設定

`.token` に Discord bot のトークンを記述してください。

`.config` の操作は必須ではないので後述します。

このとき同時に `mikanassets` が生成されます。これは `/replace` を実行する際や web にアクセスするために必要なファイルです。

トークンを記述し、config の `server_path` に `server.[exe/bat(jar を実行するファイル)]` へのパスを記述後に再度 `server.py` を起動すると正常に起動するはずです。このプログラムは `server.py` がサーバー本体を呼び出すため、`server.[exe/jar/bat]` を自身で起動する必要はありません。

> [!WARNING]
> `server.jar`(Java edition) を起動する場合基本的には `java -Xmx4048M -Xms1024M -Dfile.encoding=UTF-8 -jar server.jar nogui` と記述した bat ファイル(Windows の場合)を作成し、`server_path` に記載してください。

---

## .config

`.config` は初期生成では以下のような内容で構成されています。

```json
{
    "allow": {
        "ip": true
    },
    "update": {
        "auto": true,
        "branch": "main"
    },
    "server_path": "path/to/serverdir/",
    "server_name": "bedrock_server.exe",
    "server_args": "",
    "server_char_encoding": "utf-8",
    "log": {
        "server": true,
        "all": false
    },
    "web": {
        "secret_key": "****",
        "port": 80,
        "use_front_page": true
    },
    "discord_commands": {
        "permission": {
            "commands_level": {
                "stop": 1,
                "start": 1,
                "exit": 2,
                "cmd serverin": 1,
                "cmd stdin mk": 3,
                "cmd stdin rm": 2,
                "cmd stdin mkdir": 2,
                "cmd stdin rmdir": 2,
                "cmd stdin ls": 2,
                "cmd stdin mv": 3,
                "cmd stdin send-discord": 2,
                "cmd stdin wget": 3,
                "cmd stdin unzip": 2,
                "help": 0,
                "backup create": 1,
                "backup apply": 3,
                "ip": 0,
                "logs": 1,
                "permission view": 0,
                "permission change": 4,
                "lang": 2,
                "tokengen": 1,
                "terminal set": 1,
                "terminal del": 1,
                "update": 3,
                "announce embed": 4,
                "status": 0
            }
        },
        "ip": {
            "address": {
                "prefix": "",
                "suffix": "",
                "body": null
            }
        },
        "cmd": {
            "stdin": {
                "sys_files": [
                    ".config",
                    ".token",
                    "logs",
                    "mikanassets"
                ],
                "send_discord": {
                    "bits_capacity": 2147483648
                }
            },
            "serverin": {
                "allow_mccmd": [
                    "list",
                    "whitelist",
                    "tellraw",
                    "w",
                    "tell"
                ]
            }
        },
        "terminal": {
            "discord": false,
            "capacity": "inf"
        },
        "stop": {
            "submit": "stop"
        },
        "backup": {
            "path": "path/to/backup/"
        },
        "admin": {
            "members": {}
        },
        "lang": "en"
    },
    "enable_advanced_features": false
}
```

|項目|説明|
|---|---|
|allow|各コマンドの実行を許可するかどうか(現在は /ip にのみ実装されています)|
|update.auto|サーバー本体を自動更新するか否か|
|update.branch|自動更新時に参照する GitHub ブランチ名|
|server_path|server 本体のパス(例えば `D:\\a\\server.jar` に配置されていれば `D:\\a\\` または `D:/a/`)|
|server_name|server 本体の名前。Java 版 Minecraft の場合サーバー起動に利用する `server.bat` 等を入力してください(GUI 起動させないでください)|
|server_args|server 起動時のコンソール引数。例えば Terraria を起動する場合 `-world /path/to/world.wld` を入力してください|
|server_char_encoding|server のコンソール出力を受け取る際に使用する文字コードを入力します|
|log|各種ログを保存するか否か。server を true にすると mc サーバーの実行ログを mcserver と同じディレクトリに保存し、all を true にするとすべてのログを server.py と同じディレクトリに保存します|
|web.secret_key|Flask で利用する鍵を設定します(app.secret_key)。十分に強固な文字列を設定してください。|
|web.port|web サーバーのポート番号を入力します。なお /cmd stdin send-discord においてもこのポート番号を利用します|
|web.use_front_page|web サーバーページからの操作を許可するか否か(False の場合にもファイルダウンロードはできます)|
|discord_commands.permission.commands_level|すべてのコマンドについて、必要な権限を定義するためのリスト(コマンド実行には書き込まれた値以上の権限が必要)|
|discord_commands.ip.address.prefix|/ip で表示するアドレスの前に付加する文字列|
|discord_commands.ip.address.suffix|/ip で表示するアドレスの後に付加する文字列|
|discord_commands.ip.address.body|null の場合は外部 IP を自動取得して表示する。文字列を設定するとその値を固定で表示する(自動取得しない)|
|discord_commands.cmd.stdin.sys_files|/cmd stdin \<mv/rmdir/rm/wget/mv\> において、権限を持っていても操作を拒否するファイルのリスト|
|discord_commands.cmd.stdin.send_discord.bits_capacity|/cmd stdin send-discord において、送信を許可するファイルの最大容量|
|discord_commands.cmd.serverin.allow_mccmd|/cmd で標準入力を許可するコマンド名のリスト|
|discord_commands.terminal.discord|コンソールとして扱うチャンネル id を指定します。通常 config を直接操作しませんが、指定されたチャンネルではサーバー起動中の入出力が可能になります(ただし allow_mccmd で許可された命令のみ)|
|discord_commands.terminal.capacity|Discord にコンソール出力する予定の文字列長の最大を設定します。デフォルトでは送信に時間がかかったとしてもデータを捨てません。|
|discord_commands.stop.submit|/stop コマンドが入力された際にサーバーの標準入力へ送信するコマンドを設定します|
|discord_commands.backup.path|ワールドデータのバックアップパス(例えば `D:\\server\\backup` に保存するなら `D:\\server\\backup\\` または `D:/server/backup/`)|
|discord_commands.admin.members|サーバー内の管理者権限を操作します。通常 config を直接操作しませんが、`permission change` コマンドを用いて bot 管理者を設定できます。|
|discord_commands.lang|Discord に送信するメッセージの言語を選択します(en : 英語, ja : 日本語)|
|enable_advanced_features|Discord 上で管理者権限を持っている場合に、`discord_commands.cmd.stdin.sys_files` に含まれるファイルを操作可能にするか否か|

---

## web 上での操作

ホスト IP アドレス:`.config` で設定したポート番号 を用いて操作することができます。

アクセス時にトークンが要求されるため、Discord で `/tokengen` を実行し、トークンを入手してください。

https を用いて実行する場合(推奨)リバースプロキシを利用してください。

---

## 拡張機能

拡張機能を追加する場合 `server.py` と同じディレクトリの `mikanassets/extension` に配置してください。

構造は `mikanassets/extension/拡張機能名/拡張機能を実装したファイル群` となります。

拡張機能の実装仕様は [server-bot-extensions](https://github.com/sleeping-mikan/server-bot-extensions) で確認できます。

> [!WARNING]
> v3 では拡張機能 API のインポート方法が変更されています。
> ```python
> # 旧 (v2)
> from main import extension_commands_group, extension_logger
>
> # 新 (v3)
> from core.state import ctx
> # ctx.extension_commands_group, ctx.extension_logger を使用する
> ```

---

## Java 版サーバーの起動について

Java 版サーバーを Windows で起動する際、一般的に利用されるような以下の内容の bat を `config` の `server_name` に設定してください。`nogui` オプションが無い場合現在 `/stop` 等を利用できません。(fabric : start.bat , forge : run.bat)

> [!WARNING]
> `-Dfile.encoding=UTF-8` が存在しない場合一部環境で特殊文字等が正常に表示されません。また `pause` のようなコマンドを記載しないでください。(このプログラムはサーバーを制御するプログラムであり、以外のコマンドを実行しないでください。)

```
java -Xmx4048M -Xms1024M -Dfile.encoding=UTF-8 -jar server.jar nogui
```
