import time
from collections.abc import Callable, Mapping
from urllib.parse import urlsplit

import httpx

from socioscope_core.ports.fetcher import FetchError


class HttpxFetcher:
    """SourceFetcher over HTTP(S). No credentials; public sources only.

    *user_agent* identifies this project. Some public sites (e.g. www.meti.go.jp) answer 403 to
    any non-browser User-Agent; *user_agent_by_host* maps such hosts to the UA to send there,
    so the exception is explicit and recorded (design/data-sources.md) instead of global.
    """

    def __init__(
        self,
        *,
        user_agent: str,
        timeout_s: float = 60.0,
        retries: int = 2,
        user_agent_by_host: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
        rate_limit_attempts: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._ua_by_host = dict(user_agent_by_host or {})
        self._rate_limit_attempts = rate_limit_attempts
        self._sleep = sleep
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout_s,
            follow_redirects=True,
            transport=transport or httpx.HTTPTransport(retries=retries),
        )

    def fetch(self, url: str) -> bytes:
        return self._do(url, None)

    def post_json(self, url: str, body: Mapping[str, object]) -> bytes:
        return self._do(url, dict(body))

    def _do(self, url: str, body: dict[str, object] | None) -> bytes:
        if not url.startswith(("https://", "http://")):
            msg = f"unsupported URL scheme: {url}"
            raise FetchError(msg)
        headers: dict[str, str] = {}
        host = urlsplit(url).hostname or ""
        if host in self._ua_by_host:
            headers["User-Agent"] = self._ua_by_host[host]
        try:
            resp = self._with_backoff(url, headers, body)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            msg = f"fetch failed: {url} ({type(e).__name__})"
            raise FetchError(msg) from e
        return resp.content

    def _with_backoff(
        self, url: str, headers: dict[str, str], body: dict[str, object] | None
    ) -> httpx.Response:
        """Retry 429 (Too Many Requests) honouring Retry-After (default 2 s, doubling)."""
        delay = 2.0
        for attempt in range(1, self._rate_limit_attempts + 1):
            resp = (
                self._client.get(url, headers=headers)
                if body is None
                else self._client.post(url, headers=headers, json=body)
            )
            if resp.status_code != 429 or attempt == self._rate_limit_attempts:
                return resp
            retry_after = resp.headers.get("Retry-After")
            wait = delay
            if retry_after is not None and retry_after.isdigit():
                wait = max(float(retry_after), 1.0)
            self._sleep(wait)
            delay = min(delay * 2, 30.0)
        return resp  # pragma: no cover - loop always returns
