"""update/selfupdate.py の resolve_update_branch() のテスト

.config の update.branch が GitHub 上に存在しない場合、release ブランチへ
フォールバックする挙動を確認する。GitHub API へは requests.get をモックして到達しない。
"""

from __future__ import annotations

import update.selfupdate as selfupdate
from core.state import ctx


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_body = json_body or {}
        self.text = text

    def json(self):
        return self._json_body


def _set_branch(monkeypatch, branch: str | None):
    if branch is None:
        monkeypatch.setattr(ctx, "config", None)
    else:
        monkeypatch.setattr(ctx, "config", {"update": {"branch": branch}})


def test_resolve_update_branch_uses_configured_branch_when_found(monkeypatch):
    _set_branch(monkeypatch, "beta")
    requested_urls = []

    def fake_get(url):
        requested_urls.append(url)
        return _FakeResponse(200, {"sha": "abc123"})

    monkeypatch.setattr(selfupdate.requests, "get", fake_get)

    branch, commit, error = selfupdate.resolve_update_branch()

    assert (branch, commit, error) == ("beta", "abc123", "")
    assert requested_urls == [
        "https://api.github.com/repos/sleeping-mikan/server-bot-v3/commits/beta"
    ]


def test_resolve_update_branch_falls_back_to_release_when_branch_missing(monkeypatch):
    _set_branch(monkeypatch, "no-such-branch")
    requested_urls = []

    def fake_get(url):
        requested_urls.append(url)
        if url.endswith("/no-such-branch"):
            return _FakeResponse(422, text="not found")
        assert url.endswith("/release")
        return _FakeResponse(200, {"sha": "release-sha"})

    monkeypatch.setattr(selfupdate.requests, "get", fake_get)

    branch, commit, error = selfupdate.resolve_update_branch()

    assert (branch, commit, error) == ("release", "release-sha", "")
    assert len(requested_urls) == 2  # 元のブランチ + release の2回だけ問い合わせる


def test_resolve_update_branch_does_not_loop_when_release_itself_missing(monkeypatch):
    _set_branch(monkeypatch, "release")

    def fake_get(url):
        return _FakeResponse(422, text="not found")

    monkeypatch.setattr(selfupdate.requests, "get", fake_get)

    branch, commit, error = selfupdate.resolve_update_branch()

    assert branch == "release"
    assert commit is None


def test_resolve_update_branch_does_not_fall_back_on_non_branch_errors(monkeypatch):
    # ネットワークエラー等(422以外)はフォールバックしても同じ理由で失敗する可能性が高いため、
    # 素直にエラーを返す(GitHubへの余計なリクエストを増やさない)。
    _set_branch(monkeypatch, "beta")
    requested_urls = []

    def fake_get(url):
        requested_urls.append(url)
        return _FakeResponse(500, text="internal error")

    monkeypatch.setattr(selfupdate.requests, "get", fake_get)

    branch, commit, error = selfupdate.resolve_update_branch()

    assert branch == "beta"
    assert commit is None
    assert len(requested_urls) == 1


def test_resolve_update_branch_uses_fallback_when_config_missing(monkeypatch):
    _set_branch(monkeypatch, None)
    requested_urls = []

    def fake_get(url):
        requested_urls.append(url)
        return _FakeResponse(200, {"sha": "release-sha"})

    monkeypatch.setattr(selfupdate.requests, "get", fake_get)

    branch, commit, error = selfupdate.resolve_update_branch()

    assert (branch, commit, error) == ("release", "release-sha", "")
    assert requested_urls == [
        "https://api.github.com/repos/sleeping-mikan/server-bot-v3/commits/release"
    ]
