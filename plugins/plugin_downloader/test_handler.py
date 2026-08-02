from pathlib import Path
from types import SimpleNamespace

from botcmd.testing import load_plugin_handler

handler = load_plugin_handler(__file__)


class FakeWeb:
    def __init__(self):
        self.download_calls = []

    async def download(self, path, url):
        self.download_calls.append((Path(path), url))
        return Path(path)


def make_ctx(sent):
    async def send(msg):
        sent.append(msg)

    return SimpleNamespace(send=send)


def make_dispatcher(web):
    dep = SimpleNamespace(web=web, webproxy=None)
    return handler.PluginDownloaderDispatcher(None, dep)


async def test_installs_plugin_under_plugins_dir():
    web = FakeWeb()
    dispatcher = make_dispatcher(web)
    sent = []

    await dispatcher.handler(make_ctx(sent), "greeter", "http://example.com/handler.py")

    assert web.download_calls == [
        (Path("plugins/greeter/handler.py"), "http://example.com/handler.py")
    ]
    assert "Restart the bot" in sent[0]


async def test_usage_with_wrong_arg_count():
    web = FakeWeb()
    dispatcher = make_dispatcher(web)
    sent = []

    await dispatcher.handler(make_ctx(sent), "only-one-arg")

    assert web.download_calls == []
    assert "Usage" in sent[0]
