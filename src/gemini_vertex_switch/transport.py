"""HTTP transport port and the default urllib adapter."""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Mapping
from http.client import HTTPMessage
from typing import IO, Protocol

from .errors import GeminiError


class Transport(Protocol):
    """Sends one POST request and returns ``(status, body)``."""

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        timeout: float,
    ) -> tuple[int, bytes]:
        """POST ``body`` to ``url`` and return the status code and response bytes."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirect handler that never follows a redirect."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        return None


class UrllibTransport:
    """Default transport: urllib with redirects disabled and a bounded body read."""

    def __init__(
        self,
        max_response_bytes: int,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        self._limit = max_response_bytes
        if opener is None:
            opener = urllib.request.build_opener(_NoRedirect())
        self._opener = opener

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        timeout: float,
    ) -> tuple[int, bytes]:
        """POST over https; reads at most ``max_response_bytes + 1`` bytes."""
        if not url.startswith("https://"):
            raise GeminiError("config", "only https URLs are allowed")
        request = urllib.request.Request(  # noqa: S310, RUF100
            url,
            data=body,
            headers=dict(headers),
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=timeout) as response:
                return int(response.status), bytes(response.read(self._limit + 1))
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, bytes(exc.read(self._limit + 1))
