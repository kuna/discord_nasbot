from pathlib import Path
from types import SimpleNamespace

import pytest

from botcmd.testing import load_plugin_handler

handler = load_plugin_handler(__file__)


class FakeWeb:
    def __init__(self, content="fake content"):
        self.content = content
        self.download_calls = []
        self.read_calls = []

    async def download(self, path, url):
        self.download_calls.append((Path(path), url))
        return Path(path)

    async def read(self, url):
        self.read_calls.append(url)
        return self.content


def make_ctx(sent):
    async def send(msg):
        sent.append(msg)

    return SimpleNamespace(send=send)


def make_dispatcher(web=None, webproxy=None, download_folder="downloads"):
    config = SimpleNamespace(DOWNLOAD_FOLDER=download_folder)
    dep = SimpleNamespace(web=web, webproxy=webproxy, config=config)
    return handler.ExDownloaderDispatcher(None, dep)


async def test_downloads_through_proxy_only():
    web, webproxy = FakeWeb(), FakeWeb()
    dispatcher = make_dispatcher(web=web, webproxy=webproxy)
    sent = []

    await dispatcher.handler(make_ctx(sent), "http://example.com/files/movie.mkv")

    assert webproxy.download_calls == [
        (Path("downloads/movie.mkv"), "http://example.com/files/movie.mkv")
    ]
    assert web.download_calls == []
    assert sent == ["✅ Downloaded to `downloads/movie.mkv`"]


async def test_downloads_into_configured_folder():
    webproxy = FakeWeb()
    dispatcher = make_dispatcher(webproxy=webproxy, download_folder="nas/incoming")

    await dispatcher.handler(make_ctx([]), "http://example.com/movie.mkv")

    assert webproxy.download_calls == [
        (Path("nas/incoming/movie.mkv"), "http://example.com/movie.mkv")
    ]


async def test_stdout_reads_through_proxy():
    webproxy = FakeWeb(content="proxied body")
    dispatcher = make_dispatcher(webproxy=webproxy)
    sent = []

    await dispatcher.handler(make_ctx(sent), "http://example.com/page.html", "stdout")

    assert webproxy.read_calls == ["http://example.com/page.html"]
    assert sent == ["Content: proxied body"]


async def test_raises_when_proxy_not_configured():
    web = FakeWeb()
    dispatcher = make_dispatcher(web=web, webproxy=None)

    # the raised error is reported to the channel by the bot's error handler
    with pytest.raises(Exception, match="Proxy is not ready"):
        await dispatcher.handler(make_ctx([]), "http://example.com/a.txt")

    assert web.download_calls == []


async def test_usage_without_args():
    dispatcher = make_dispatcher(webproxy=FakeWeb())
    sent = []

    await dispatcher.handler(make_ctx(sent))

    assert "Usage" in sent[0]
