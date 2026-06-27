"""
text_data.py — テキストデータ(JSON)の読み込み

main.py から切り出したモジュール。
従来 get_text_dat() がPythonの辞書リテラルとして直接埋め込んでいたテキストデータを、
mikanassets/main/assets/text.json に外出しした上で読み込む。

JSON上の構造:
    {
        "help_msg": {"ja": {...}, "en": {...}},
        "command_description": {"ja": {...}, "en": {...}},
        "response_msg": {"ja": {...}, "en": {...}},
        "activity_name": {"ja": {...}, "en": {...}}
    }

元のコードとの互換性のため、main.py側の変数の形は変えていない:
    - HELP_MSG / COMMAND_DESCRIPTION は言語をキーとした辞書のまま (HELP_MSG[lang][...])
    - RESPONSE_MSG / ACTIVITY_NAME は「現在の言語の」辞書そのもの (RESPONSE_MSG[...])
"""

import os
import json


def _assets_path() -> str:
    # このファイル(mikanassets/main/src/text_data.py)から見て
    # mikanassets/main/assets/text.json の位置を求める
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "..", "assets", "text.json")


def load_text_data(lang: str, allow_cmd: str = ""):
    """
    text.json を読み込み、(HELP_MSG, COMMAND_DESCRIPTION, RESPONSE_MSG, ACTIVITY_NAME, send_help初期値) を返す。

    allow_cmd: HELP_MSGの "/cmd serverin" の説明文に埋め込む、許可されたMinecraftコマンドの一覧文字列
               (元コードでは f-string でその場で埋め込んでいたものを、JSON側では
               "{allow_cmd}" というプレースホルダにしてあるため、ここで.format()する)
    """
    with open(_assets_path(), "r", encoding="utf-8") as f:
        data = json.load(f)

    help_msg = data["help_msg"]
    command_description = data["command_description"]
    response_msg = data["response_msg"].get(lang, data["response_msg"]["en"])
    activity_name = data["activity_name"].get(lang, data["activity_name"]["en"])
    send_help_initial = data["send_help"].get(lang, data["send_help"]["en"])

    # allow_cmdプレースホルダの埋め込み(各言語分)
    for lang_key, msgs in help_msg.items():
        for key, value in list(msgs.items()):
            if isinstance(value, str) and "{allow_cmd}" in value:
                msgs[key] = value.format(allow_cmd=allow_cmd)

    return help_msg, command_description, response_msg, activity_name, send_help_initial
