import httpx
import pytest

from socioscope_core.adapters.http_fetcher import HttpxFetcher
from socioscope_core.ports.fetcher import FetchError


def make(seen: list[tuple[str, str]], **kw: object) -> HttpxFetcher:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.host, request.headers["User-Agent"]))
        if request.url.path == "/missing":
            return httpx.Response(404)
        return httpx.Response(200, content=b"ok")

    return HttpxFetcher(user_agent="socioscope/test", transport=httpx.MockTransport(handler), **kw)  # type: ignore[arg-type]


def test_sends_project_user_agent_by_default() -> None:
    seen: list[tuple[str, str]] = []
    assert make(seen).fetch("https://example.org/x") == b"ok"
    assert seen == [("example.org", "socioscope/test")]


def test_host_specific_user_agent_applies_only_to_that_host() -> None:
    seen: list[tuple[str, str]] = []
    f = make(seen, user_agent_by_host={"www.meti.go.jp": "Mozilla/5.0 (test)"})
    f.fetch("https://www.meti.go.jp/a.xlsx")
    f.fetch("https://example.org/x")
    assert seen == [("www.meti.go.jp", "Mozilla/5.0 (test)"), ("example.org", "socioscope/test")]


def test_http_error_and_bad_scheme_raise_fetch_error() -> None:
    f = make([])
    with pytest.raises(FetchError, match="fetch failed"):
        f.fetch("https://example.org/missing")
    with pytest.raises(FetchError, match="unsupported URL scheme"):
        f.fetch("ftp://example.org/x")
