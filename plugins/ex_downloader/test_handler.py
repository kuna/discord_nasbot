from pathlib import Path
from types import SimpleNamespace

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


def make_dispatcher(web, download_folder="downloads"):
    config = SimpleNamespace(DOWNLOAD_FOLDER=download_folder)
    dep = SimpleNamespace(web=web, webproxy=None, config=config)
    return handler.ExDownloaderDispatcher(None, dep)


async def test_downloads_with_filename_from_url():
    web = FakeWeb()
    dispatcher = make_dispatcher(web)
    sent = []

    await dispatcher.handler(make_ctx(sent), "http://example.com/files/movie.mkv")

    assert web.download_calls == [
        (Path("downloads/movie.mkv"), "http://example.com/files/movie.mkv")
    ]
    assert sent == ["✅ Downloaded to `downloads/movie.mkv`"]


async def test_downloads_with_explicit_filename():
    web = FakeWeb()
    dispatcher = make_dispatcher(web)
    sent = []

    await dispatcher.handler(make_ctx(sent), "http://example.com/dl?id=42", "movie.mkv")

    assert web.download_calls == [(Path("downloads/movie.mkv"), "http://example.com/dl?id=42")]


async def test_downloads_into_configured_folder():
    web = FakeWeb()
    dispatcher = make_dispatcher(web, download_folder="nas/incoming")

    await dispatcher.handler(make_ctx([]), "http://example.com/movie.mkv")

    assert web.download_calls == [(Path("nas/incoming/movie.mkv"), "http://example.com/movie.mkv")]


async def test_stdout_sends_content_instead_of_downloading():
    web = FakeWeb(content="page body")
    dispatcher = make_dispatcher(web)
    sent = []

    await dispatcher.handler(make_ctx(sent), "http://example.com/page.html", "stdout")

    assert web.read_calls == ["http://example.com/page.html"]
    assert web.download_calls == []
    assert sent == ["Content: page body"]


async def test_stdout_truncates_content_to_200_chars():
    web = FakeWeb(content="x" * 500)
    dispatcher = make_dispatcher(web)
    sent = []

    await dispatcher.handler(make_ctx(sent), "http://example.com/big.txt", "stdout")

    assert sent == [f"Content: {'x' * 200}"]


async def test_usage_without_args():
    web = FakeWeb()
    dispatcher = make_dispatcher(web)
    sent = []

    await dispatcher.handler(make_ctx(sent))

    assert web.download_calls == []
    assert "Usage" in sent[0]


async def test_rejects_url_without_filename():
    web = FakeWeb()
    dispatcher = make_dispatcher(web)
    sent = []

    await dispatcher.handler(make_ctx(sent), "http://example.com/")

    assert web.download_calls == []
    assert "filename" in sent[0]
