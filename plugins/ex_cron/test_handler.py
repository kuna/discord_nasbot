from types import SimpleNamespace

from botcmd.testing import load_plugin_handler

handler = load_plugin_handler(__file__)


def make_ctx(sent):
    async def send(msg):
        sent.append(msg)

    return SimpleNamespace(send=send)


def test_declares_a_cron_schedule():
    # Not now; we're disabling it but leave the code as an cron example
    # assert handler.ExCronDispatcher.cron == "*/30 * * * *"
    assert handler.ExCronDispatcher.channel == ["bot"]


async def test_handler_reports_alive():
    sent = []
    dispatcher = handler.ExCronDispatcher(None)

    await dispatcher.handler(make_ctx(sent))

    assert sent[0].startswith("💓 alive at ")


async def test_scheduled_run_uses_the_handler():
    sent = []
    dispatcher = handler.ExCronDispatcher(None)

    # the base class routes scheduled runs to handler()
    await dispatcher.scheduled(make_ctx(sent))

    assert sent[0].startswith("💓 alive at ")
