from types import SimpleNamespace

from botcmd.testing import load_plugin_handler

handler = load_plugin_handler(__file__)


async def test_ping_responds_with_latency():
    sent = []

    async def send(msg):
        sent.append(msg)

    fake_bot = SimpleNamespace(latency=0.123)
    ctx = SimpleNamespace(send=send)

    dispatcher = handler.PingDispatcher(fake_bot)
    assert dispatcher.command == "ping"
    await dispatcher.handler(ctx)

    assert sent == ["🏓 Pong! 123ms"]
