from collections.abc import Mapping
from typing import Protocol


class FetchError(Exception):
    """Raised by a SourceFetcher when the remote source cannot be read."""


class SourceFetcher(Protocol):
    def fetch(self, url: str) -> bytes:
        """Return the raw bytes at *url*. Raise FetchError on failure."""
        ...

    def post_json(self, url: str, body: Mapping[str, object]) -> bytes:
        """POST *body* as JSON to *url* and return the raw response bytes (for APIs that take
        their query in the request body, e.g. MOPS). Raise FetchError on failure."""
        ...
