"""core/web_url.py の get_web_base_url() のテスト

.config の web.public_url が設定されていればそれを優先し、
未設定なら従来通り http://{web_ip}:{web_port} にフォールバックすることを確認する。
"""

from __future__ import annotations

from core.state import ctx
from core.web_url import get_web_base_url


def _set_web_state(monkeypatch, *, public_url, web_ip="203.0.113.1", web_port=8080):
    monkeypatch.setattr(ctx, "config", {"web": {"public_url": public_url}})
    monkeypatch.setattr(ctx, "web_ip", web_ip)
    monkeypatch.setattr(ctx, "web_port", web_port)


def test_uses_public_url_when_set(monkeypatch):
    _set_web_state(monkeypatch, public_url="https://mydomain.example")
    assert get_web_base_url() == "https://mydomain.example"


def test_strips_trailing_slash_from_public_url(monkeypatch):
    _set_web_state(monkeypatch, public_url="https://mydomain.example/")
    assert get_web_base_url() == "https://mydomain.example"


def test_falls_back_to_ip_port_when_public_url_none(monkeypatch):
    _set_web_state(monkeypatch, public_url=None, web_ip="203.0.113.1", web_port=8080)
    assert get_web_base_url() == "http://203.0.113.1:8080"


def test_falls_back_to_ip_port_when_public_url_empty_string(monkeypatch):
    _set_web_state(monkeypatch, public_url="", web_ip="203.0.113.1", web_port=8080)
    assert get_web_base_url() == "http://203.0.113.1:8080"


def test_falls_back_to_ip_port_when_config_missing(monkeypatch):
    monkeypatch.setattr(ctx, "config", None)
    monkeypatch.setattr(ctx, "web_ip", "203.0.113.1")
    monkeypatch.setattr(ctx, "web_port", 8080)
    assert get_web_base_url() == "http://203.0.113.1:8080"
