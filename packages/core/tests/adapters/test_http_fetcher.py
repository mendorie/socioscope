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


def test_retries_429_with_retry_after_then_succeeds() -> None:
    calls: list[int] = []
    waits: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200, content=b"ok")

    f = HttpxFetcher(user_agent="t", transport=httpx.MockTransport(handler), sleep=waits.append)
    assert f.fetch("https://example.org/x") == b"ok"
    assert len(calls) == 3 and waits == [3.0, 3.0]


def test_gives_up_on_429_after_the_configured_attempts() -> None:
    waits: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    f = HttpxFetcher(
        user_agent="t",
        transport=httpx.MockTransport(handler),
        rate_limit_attempts=3,
        sleep=waits.append,
    )
    with pytest.raises(FetchError, match="HTTPStatusError"):
        f.fetch("https://example.org/x")
    assert waits == [2.0, 4.0]  # default back-off doubles when no Retry-After


def test_post_json_sends_body_and_host_user_agent() -> None:
    seen: list[tuple[str, str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.headers["User-Agent"], request.content))
        return httpx.Response(200, content=b'{"ok": true}')

    f = HttpxFetcher(
        user_agent="t",
        transport=httpx.MockTransport(handler),
        user_agent_by_host={"mops.example": "browser"},
    )
    assert (
        f.post_json("https://mops.example/api", {"companyId": "9921", "year": "108"})
        == b'{"ok": true}'
    )
    method, ua, body = seen[0]
    assert method == "POST" and ua == "browser" and b'"companyId"' in body
