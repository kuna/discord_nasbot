import socket
import zipfile

import pytest
from aiohttp import web as aioweb
from aiohttp.test_utils import TestServer

from utils.doh import DoHResolver
from utils.web import BROWSER_HEADERS, Web
from utils.webproxy import WebProxy


@pytest.fixture
async def server():
    app = aioweb.Application()
    received = []

    async def endpoint(request):
        received.append(dict(request.headers))
        return aioweb.Response(text=f"content of {request.match_info['name']}")

    app.router.add_get("/{name}", endpoint)
    server = TestServer(app)
    await server.start_server()
    server.received_headers = received
    yield server
    await server.close()


@pytest.fixture
async def html_server():
    app = aioweb.Application()
    received = []
    pages = {
        "page": "<html><head><title> Example </title></head><body>"
        "<a href='/a'>a</a><a href='/b'>b</a></body></html>",
        "broken": "<html><body><p>unclosed<div><span>",
    }

    async def endpoint(request):
        received.append(dict(request.headers))
        return aioweb.Response(text=pages[request.match_info["name"]], content_type="text/html")

    app.router.add_get("/{name}", endpoint)
    server = TestServer(app)
    await server.start_server()
    server.received_headers = received
    yield server
    await server.close()


async def test_read(server):
    web = Web()
    assert await web.read(str(server.make_url("/hello.txt"))) == "content of hello.txt"


async def test_download_creates_parent_dirs(server, tmp_path):
    web = Web()
    dest = tmp_path / "sub" / "dir" / "hello.txt"

    path = await web.download(dest, str(server.make_url("/hello.txt")))

    assert path == dest
    assert dest.read_text() == "content of hello.txt"


async def test_archive_bundles_urls_into_zip(server, tmp_path):
    web = Web()
    dest = tmp_path / "bundle.zip"
    urls = [str(server.make_url("/a.txt")), str(server.make_url("/b.txt"))]

    await web.archive(dest, urls)

    with zipfile.ZipFile(dest) as zf:
        assert sorted(zf.namelist()) == ["a.txt", "b.txt"]
        assert zf.read("a.txt").decode() == "content of a.txt"
        assert zf.read("b.txt").decode() == "content of b.txt"


async def test_archive_keeps_duplicate_names(server, tmp_path):
    web = Web()
    dest = tmp_path / "bundle.zip"
    urls = [str(server.make_url("/a.txt")), str(server.make_url("/a.txt"))]

    await web.archive(dest, urls)

    with zipfile.ZipFile(dest) as zf:
        assert sorted(zf.namelist()) == ["1_a.txt", "a.txt"]


def test_webproxy_builds_proxy_url():
    assert WebProxy("dpi.local")._proxy == "http://dpi.local"
    assert WebProxy("dpi.local", "8080")._proxy == "http://dpi.local:8080"
    assert WebProxy("http://dpi.local")._proxy == "http://dpi.local"
    assert WebProxy("http://dpi.local", "8080")._proxy == "http://dpi.local:8080"


def test_plain_web_has_no_proxy():
    assert Web()._proxy is None


async def test_read_html_returns_a_soup(html_server):
    soup = await Web().read_html(str(html_server.make_url("/page")))

    assert soup.title.get_text(strip=True) == "Example"
    assert [a["href"] for a in soup.select("a[href]")] == ["/a", "/b"]


async def test_read_html_repairs_malformed_markup(html_server):
    """lxml closes the unclosed tags that html.parser would leave broken."""
    soup = await Web().read_html(str(html_server.make_url("/broken")))

    assert soup.select_one("p").get_text(strip=True) == "unclosed"


async def test_read_html_accepts_another_parser(html_server):
    soup = await Web().read_html(str(html_server.make_url("/page")), parser="html.parser")

    assert soup.title.get_text(strip=True) == "Example"


async def test_read_html_sends_browser_headers(html_server):
    await Web().read_html(str(html_server.make_url("/page")))

    assert html_server.received_headers[0]["User-Agent"] == BROWSER_HEADERS["User-Agent"]


async def test_read_sends_browser_headers(server):
    await Web().read(str(server.make_url("/hello.txt")))

    headers = server.received_headers[0]
    assert headers["User-Agent"] == BROWSER_HEADERS["User-Agent"]
    assert "aiohttp" not in headers["User-Agent"]
    assert "Python" not in headers["User-Agent"]
    assert headers["Sec-Fetch-Mode"] == "navigate"
    assert headers["sec-ch-ua-platform"] == '"macOS"'


async def test_download_sends_browser_headers(server, tmp_path):
    await Web().download(tmp_path / "hello.txt", str(server.make_url("/hello.txt")))

    assert server.received_headers[0]["User-Agent"] == BROWSER_HEADERS["User-Agent"]


async def test_archive_sends_browser_headers(server, tmp_path):
    await Web().archive(tmp_path / "b.zip", [str(server.make_url("/a.txt"))])

    assert server.received_headers[0]["User-Agent"] == BROWSER_HEADERS["User-Agent"]


async def test_accept_encoding_is_left_to_aiohttp(server):
    """aiohttp advertises only codecs it can decode, so we must not override it."""
    assert "Accept-Encoding" not in BROWSER_HEADERS

    await Web().read(str(server.make_url("/hello.txt")))

    # aiohttp still sends one of its own
    assert server.received_headers[0]["Accept-Encoding"]


async def test_custom_headers_override_defaults(server):
    web = Web(headers={"User-Agent": "custom-agent", "X-Extra": "1"})
    await web.read(str(server.make_url("/hello.txt")))

    headers = server.received_headers[0]
    assert headers["User-Agent"] == "custom-agent"
    assert headers["X-Extra"] == "1"
    # untouched defaults survive
    assert headers["Accept-Language"] == BROWSER_HEADERS["Accept-Language"]


def test_webproxy_uses_browser_headers_too():
    assert WebProxy("dpi.local")._headers == BROWSER_HEADERS
    assert WebProxy("dpi.local", headers={"User-Agent": "x"})._headers["User-Agent"] == "x"


def test_no_resolver_without_doh_url():
    assert Web()._resolver is None
    assert WebProxy("dpi.local")._resolver is None


def test_doh_url_installs_resolver():
    web = Web(doh_url="https://1.1.1.1/dns-query")
    assert isinstance(web._resolver, DoHResolver)
    assert WebProxy("dpi.local", doh_url="https://1.1.1.1/dns-query")._resolver is not None


def test_webproxy_sends_doh_lookups_through_the_proxy():
    web = WebProxy("dpi.local", "8080", doh_url="https://1.1.1.1/dns-query")
    assert web._resolver._proxy == "http://dpi.local:8080"
    assert web._resolver._proxy == web._proxy


def test_plain_web_does_not_proxy_doh_lookups():
    assert Web(doh_url="https://1.1.1.1/dns-query")._resolver._proxy is None


async def test_requests_resolve_through_doh(server, tmp_path):
    """The DoH resolver is actually consulted for the hostname of a real request."""
    queried = []
    port = server.port

    class RecordingResolver(DoHResolver):
        async def resolve(self, host, port_=0, family=socket.AF_INET, **kwargs):
            queried.append(host)
            return [
                {
                    "hostname": host,
                    "host": "127.0.0.1",
                    "port": kwargs.get("port", port_),
                    "family": socket.AF_INET,
                    "proto": 0,
                    "flags": 0,
                }
            ]

    web = Web(doh_url="https://1.1.1.1/dns-query")
    web._resolver = RecordingResolver("https://1.1.1.1/dns-query")

    # "localhost" is not an IP literal, so aiohttp must ask the resolver
    body = await web.read(f"http://localhost:{port}/hello.txt")
    await web.close()

    assert body == "content of hello.txt"
    assert queried == ["localhost"]


async def test_close_without_resolver_is_safe():
    await Web().close()
