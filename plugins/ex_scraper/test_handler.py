from types import SimpleNamespace

from bs4 import BeautifulSoup

from botcmd.testing import load_plugin_handler

handler = load_plugin_handler(__file__)


class FakeWeb:
    def __init__(self, html=""):
        self.html = html
        self.calls = []

    async def read_html(self, url, parser="lxml"):
        self.calls.append(url)
        return BeautifulSoup(self.html, parser)


def make_ctx(sent):
    async def send(msg):
        sent.append(msg)

    return SimpleNamespace(send=send)


def make_dispatcher(web):
    return handler.ExScraperDispatcher(None, SimpleNamespace(web=web, webproxy=None))


async def test_reports_title_and_links():
    web = FakeWeb("<html><title> Example </title><body><a href='/a'>a</a><a href='/b'>b</a>")
    sent = []

    await make_dispatcher(web).handler(make_ctx(sent), "http://example.com")

    assert web.calls == ["http://example.com"]
    assert "**Example**" in sent[0]
    assert "2 link(s)" in sent[0]
    assert "• /a" in sent[0] and "• /b" in sent[0]


async def test_truncates_long_link_lists():
    links = "".join(f"<a href='/{i}'>x</a>" for i in range(9))
    sent = []

    await make_dispatcher(FakeWeb(f"<title>T</title>{links}")).handler(
        make_ctx(sent), "http://example.com"
    )

    assert "9 link(s)" in sent[0]
    assert "… and 4 more" in sent[0]
    assert sent[0].count("• ") == handler.MAX_LINKS


async def test_page_without_title():
    sent = []

    await make_dispatcher(FakeWeb("<html><body>no title here")).handler(
        make_ctx(sent), "http://example.com"
    )

    assert "(no title)" in sent[0]


async def test_usage_without_args():
    web = FakeWeb()
    sent = []

    await make_dispatcher(web).handler(make_ctx(sent))

    assert web.calls == []
    assert "Usage" in sent[0]
