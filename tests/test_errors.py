import logging
from types import SimpleNamespace

import discord
from discord.ext import commands

from botcmd.errors import register_error_handler


def make_handler():
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
    return register_error_handler(bot)


def make_ctx(sent, invoked_with="cmd"):
    async def send(msg):
        sent.append(msg)

    return SimpleNamespace(send=send, invoked_with=invoked_with)


async def test_command_failure_is_reported_to_channel(caplog):
    handler = make_handler()
    sent = []

    error = commands.CommandInvokeError(RuntimeError("boom"))
    with caplog.at_level(logging.ERROR, logger="nasbot"):
        await handler(make_ctx(sent, invoked_with="echo"), error)

    assert sent == ["⚠️ `!echo` failed: boom"]
    # the original exception is still logged for server-side debugging
    assert "!echo failed" in caplog.text
    assert any(r.exc_info and isinstance(r.exc_info[1], RuntimeError) for r in caplog.records)


async def test_unknown_command_is_silent():
    handler = make_handler()
    sent = []

    await handler(make_ctx(sent), commands.CommandNotFound())

    assert sent == []


async def test_channel_check_failure_is_silent():
    handler = make_handler()
    sent = []

    await handler(make_ctx(sent), commands.CheckFailure())

    assert sent == []


async def test_send_failure_does_not_propagate(caplog):
    handler = make_handler()

    async def broken_send(msg):
        raise RuntimeError("cannot send")

    ctx = SimpleNamespace(send=broken_send, invoked_with="echo")
    error = commands.CommandInvokeError(RuntimeError("boom"))

    # must not raise even when reporting to the channel fails
    with caplog.at_level(logging.WARNING, logger="nasbot"):
        await handler(ctx, error)
    assert "Could not report" in caplog.text
