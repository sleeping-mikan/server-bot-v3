"""
core/web_url.py — Web コンソールへの外部アクセス用ベースURL解決

bot/ と web/ の両方から参照できる中立的な場所に置く(core/path_utils.py と同じ理由)。
依存: core.state (ctx) のみ。
"""

from __future__ import annotations

from core.state import ctx


def get_web_base_url() -> str:
    """Web コンソールへの外部アクセス用ベースURLを返す(末尾スラッシュなし)。

    .config の web.public_url が設定されていればそれをそのまま使う。
    リバースプロキシ配下で運用している場合、実際に外部からアクセスする
    スキーム・ドメイン・ポートは ctx.web_ip:ctx.web_port (bot が自分で
    bind しているアドレス) と一致しないため、この上書きが必要になる。

    未設定 (null) の場合は従来通り http://{ctx.web_ip}:{ctx.web_port} を使う。
    """
    public_url = ctx.config["web"].get("public_url") if ctx.config else None
    if public_url:
        return public_url.rstrip("/")
    return f"http://{ctx.web_ip}:{ctx.web_port}"
