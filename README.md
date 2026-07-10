# server-bot

## 対応言語

This bot supports English and Japanese.(このbotは英語と日本語をサポートしています。)

## 目的

サーバー管理のための Discord bot / web ツールです。

Discord を用いて特定のサーバーを管理できます。  
ここでの管理とは起動/停止/ログ取得/入出力などを行うことを指します。

## 必要なもの

- 現在使用していない Discord bot トークン

> [!WARNING]
> [discord developers](https://discord.com/developers/applications) にて該当のbotの Settings > Bot > Privileged Gateway Intents > **Message Content Intent** を許可してください。

- 言語: **Python 3.12.x**
- ライブラリ: `pip install -r requirements.txt`

## クイックスタート

1. `server.py` を任意の場所に配置して実行する
2. 生成された `.token` に Discord bot のトークンを記入する
3. `.config` の `server_path` にサーバー本体のディレクトリパスを、`server_name` にサーバーファイル名を記入する
4. `server.py` を再起動する

> [!NOTE]
> `.token` が未記入または無効なトークンの場合、起動時にエラーメッセージを表示してキー入力待ちになります。

> [!NOTE]
> 推奨ディレクトリは実行する `server.[exe/jar]` が存在する階層です。その場所が rootディレクトリとなり、一部の権限を持つ Discord ユーザーはファイル操作を行えます。

詳細な使い方・コマンド一覧・`.config` リファレンスは **[ドキュメントサイト](https://sleeping-mikan.github.io/server-bot-docs/)** を参照してください。

## web 上での操作

ホストIPアドレス:`.config`で設定したポート番号 でアクセスできます。

アクセス時にトークンが要求されるため、Discord で `/tokengen` を実行してトークンを入手してください。

https 運用する場合はリバースプロキシを利用してください。

## 動作確認済み環境

<details>
<summary>クリックして確認済み環境例を表示</summary>
<table>
    <thead>
        <th>確認バージョン</th>
        <th>日時</th>
        <th>確認時のOS</th>
        <th>python</th>
        <th>備考</th>
    </thead>
    <tbody>
        <tr>
            <td>Minecraft Java vanilla 1.9.4</td>
            <td>2024/06/26</td>
            <td>Windows 11</td>
            <td>python 3.12.1</td>
            <td>下記に示すbatを利用</td>
        </tr>
        <tr>
            <td>Minecraft Java vanilla 1.19</td>
            <td>2024/06/26</td>
            <td>Windows 11</td>
            <td>python 3.12.1</td>
            <td>下記に示すbatを利用</td>
        </tr>
        <tr>
            <td>Minecraft Java vanilla 1.19.4</td>
            <td>2024/07/31</td>
            <td>Windows 11</td>
            <td>python 3.12.1</td>
            <td>下記に示すbatを利用</td>
        </tr>
        <tr>
            <td>Minecraft Java fabric 1.20.1</td>
            <td>2024/06/26</td>
            <td>Windows 11</td>
            <td>python 3.12.1</td>
            <td>下記に示すbatを利用</td>
        </tr>
        <tr>
            <td>Minecraft Bedrock dedicated server 1.21</td>
            <td>2025/01/30</td>
            <td>Windows 11 &amp; Ubuntu(wsl2)</td>
            <td>python 3.12.1</td>
            <td></td>
        </tr>
        <tr>
            <td>TShock-5.2.1-for-Terraria-1.4.4.9</td>
            <td>2025/01/25</td>
            <td>Windows 11</td>
            <td>python 3.12.1</td>
            <td>.configのserver_argsに<code>-world /path/to/world.wld</code>を指定</td>
        </tr>
    </tbody>
</table>
</details>

- 想定環境
  - os : ubuntu(wsl2) / windows11 / windows10
  - python : 3.12.x
  - server : 任意

## 拡張機能

`server.py` と同じディレクトリの `mikanassets/extension` に配置してください。

実装仕様は [server-bot-extensions](https://github.com/sleeping-mikan/server-bot-extensions) で確認できます。
