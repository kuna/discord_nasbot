from types import SimpleNamespace

from botcmd.testing import load_plugin_handler

handler = load_plugin_handler(__file__)


async def test_echo_repeats_arguments():
    sent = []

    async def send(msg):
        sent.append(msg)

    dispatcher = handler.EchoDispatcher(SimpleNamespace())
    await dispatcher.handler(SimpleNamespace(send=send), "hello")

    assert sent == ['You typed "hello"']


async def test_echo_joins_multiple_words():
    sent = []

    async def send(msg):
        sent.append(msg)

    dispatcher = handler.EchoDispatcher(SimpleNamespace())
    await dispatcher.handler(SimpleNamespace(send=send), "hello", "world")

    assert sent == ['You typed "hello world"']
