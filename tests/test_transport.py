from __future__ import annotations

import io
import urllib.error
import urllib.request
from http.client import HTTPMessage

import pytest

from gemini_vertex_switch import GeminiError
from gemini_vertex_switch.transport import UrllibTransport, _NoRedirect

URL = "https://generativelanguage.googleapis.com/v1beta/models/m:generateContent"


class FakeResponse:
    def __init__(self, status, data):
        self.status = status
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return None

    def read(self, size=-1):
        return self.data[:size]


class FakeOpener:
    def __init__(self, result):
        self.result = result
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append((request, timeout))
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def test_post_sends_a_post_request_and_reads_at_most_limit_plus_one():
    opener = FakeOpener(FakeResponse(200, b"0123456789"))
    transport = UrllibTransport(5, opener=opener)
    status, data = transport.post(URL, {"x-goog-api-key": "k"}, b"{}", 3.0)
    assert (status, data) == (200, b"012345")
    request, timeout = opener.requests[0]
    assert request.get_method() == "POST"
    assert request.full_url == URL
    assert request.data == b"{}"
    assert request.get_header("X-goog-api-key") == "k"
    assert timeout == 3.0


def test_http_errors_return_status_and_bounded_body():
    error = urllib.error.HTTPError(URL, 400, "Bad", HTTPMessage(), io.BytesIO(b"abcdefghij"))
    transport = UrllibTransport(5, opener=FakeOpener(error))
    assert transport.post(URL, {}, b"{}", 1.0) == (400, b"abcdef")


@pytest.mark.parametrize(
    "url",
    [
        "http://generativelanguage.googleapis.com/x",
        "file:///etc/passwd",
        "ftp://example.org/x",
    ],
)
def test_non_https_urls_are_refused(url):
    opener = FakeOpener(FakeResponse(200, b""))
    with pytest.raises(GeminiError) as info:
        UrllibTransport(5, opener=opener).post(url, {}, b"{}", 1.0)
    assert info.value.code == "config"
    assert opener.requests == []


def test_other_os_errors_propagate_for_the_client_to_wrap():
    transport = UrllibTransport(5, opener=FakeOpener(urllib.error.URLError("down")))
    with pytest.raises(OSError):
        transport.post(URL, {}, b"{}", 1.0)


def test_default_opener_never_follows_redirects():
    transport = UrllibTransport(5)
    handlers = transport._opener.handlers
    redirects = [h for h in handlers if isinstance(h, urllib.request.HTTPRedirectHandler)]
    assert redirects
    assert all(isinstance(h, _NoRedirect) for h in redirects)
    request = urllib.request.Request(URL)
    result = _NoRedirect().redirect_request(
        request,
        io.BytesIO(b""),
        302,
        "Found",
        HTTPMessage(),
        "https://evil.example/",
    )
    assert result is None
