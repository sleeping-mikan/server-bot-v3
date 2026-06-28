"""
embeds.py — Discord埋め込み(Embed)の共通テンプレート

main.py から切り出したモジュール。
"""

import discord

bot_color = discord.Color.from_rgb(255, 242, 145)
embed_under_line_url = "https://www.dropbox.com/scl/fi/70b9ckjwrfilds65gbs11/gradient_bar.png?rlkey=922kwpi4t17lk0ju4ztbq6ofc&st=nb9saec1&dl=1"
embed_thumbnail_url = "https://www.dropbox.com/scl/fi/a21ptajqddfkhilx1e4st/mi-2025.png?rlkey=29x0wvk1np17a3nvddth0jnyk&st=s6r4f2kr&dl=1"


class ModifiedEmbeds:
    class DefaultEmbed(discord.Embed):
        def __init__(self, title: str, description: str | None = None, color: discord.Color = bot_color):
            super().__init__(title=title, description=description, color=color)
            self.set_image(url=embed_under_line_url)
            self.set_thumbnail(url=embed_thumbnail_url)

    class ErrorEmbed(discord.Embed):
        def __init__(self, title: str, description: str | None = None, color: int = 0xff0000):
            super().__init__(title=title, description=description, color=color)
            self.set_image(url=embed_under_line_url)
            self.set_thumbnail(url=embed_thumbnail_url)
