from collections.abc import Mapping
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
    ) -> None:
        self._ua_by_host = dict(user_agent_by_host or {})
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout_s,
            follow_redirects=True,
            transport=transport or httpx.HTTPTransport(retries=retries),
        )

    def fetch(self, url: str) -> bytes:
        if not url.startswith(("https://", "http://")):
            msg = f"unsupported URL scheme: {url}"
            raise FetchError(msg)
        headers: dict[str, str] = {}
        host = urlsplit(url).hostname or ""
        if host in self._ua_by_host:
            headers["User-Agent"] = self._ua_by_host[host]
        try:
            resp = self._client.get(url, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            msg = f"fetch failed: {url} ({type(e).__name__})"
            raise FetchError(msg) from e
        return resp.content
