import zipfile

import pytest
from aiohttp import web as aioweb
from aiohttp.test_utils import TestServer

from utils.web import Web
from utils.webproxy import WebProxy


@pytest.fixture
async def server():
    app = aioweb.Application()

    async def endpoint(request):
        return aioweb.Response(text=f"content of {request.match_info['name']}")

    app.router.add_get("/{name}", endpoint)
    server = TestServer(app)
    await server.start_server()
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
