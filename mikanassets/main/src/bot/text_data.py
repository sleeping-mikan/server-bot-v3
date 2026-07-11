"""
text_data.py — テキストデータ(JSON)の読み込み

main.py から切り出したモジュール。
従来 get_text_dat() がPythonの辞書リテラルとして直接埋め込んでいたテキストデータを、
mikanassets/main/assets/text/ 以下の言語別ファイル (ja.json, en.json など) に
外出しした上で読み込む。ファイル名 (拡張子を除いた部分) がそのまま言語コードになる。

各言語ファイルのJSON構造:
    {
        "command_description": {...},
        "command_args_description": {...},
        "response_msg": {...},
        "activity_name": {...},
        "send_help": "..."
    }

元のコードとの互換性のため、main.py側の変数の形は変えていない:
    - COMMAND_DESCRIPTION / COMMAND_ARGS_DESCRIPTION は
      言語をキーとした辞書のまま (COMMAND_DESCRIPTION[lang][...])
    - RESPONSE_MSG / ACTIVITY_NAME は「現在の言語の」辞書そのもの (RESPONSE_MSG[...])
"""

import json
from pathlib import Path

# このファイル(mikanassets/main/src/bot/text_data.py)から見て assets/text/ の位置
_TEXT_DIR = Path(__file__).parent / ".." / ".." / "assets" / "text"


def available_languages() -> list[str]:
    """assets/text/ に存在する言語コード (ファイル名の語幹) の一覧を返す。"""
    return sorted(path.stem for path in _TEXT_DIR.glob("*.json"))


def load_text_data(lang: str):
    """
    text/*.json を読み込み、
    (COMMAND_DESCRIPTION, COMMAND_ARGS_DESCRIPTION, RESPONSE_MSG, ACTIVITY_NAME, send_help初期値) を返す。

    lang に対応するファイルがない場合は en にフォールバックする。
    """
    langs: dict[str, dict] = {}
    for path in sorted(_TEXT_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as f:
            langs[path.stem] = json.load(f)

    current = langs.get(lang, langs["en"])
    command_description = {lang_key: data["command_description"] for lang_key, data in langs.items()}
    command_args_description = {lang_key: data["command_args_description"] for lang_key, data in langs.items()}
    response_msg = current["response_msg"]
    activity_name = current["activity_name"]
    send_help_initial = current["send_help"]

    return command_description, command_args_description, response_msg, activity_name, send_help_initial
