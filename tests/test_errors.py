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


async def test_command_failure_is_reported_to_channel(capsys):
    handler = make_handler()
    sent = []

    error = commands.CommandInvokeError(RuntimeError("boom"))
    await handler(make_ctx(sent, invoked_with="echo"), error)

    assert sent == ["⚠️ `!echo` failed: boom"]
    # the traceback is still printed for server-side logs
    assert "RuntimeError: boom" in capsys.readouterr().err


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


async def test_send_failure_does_not_propagate(capsys):
    handler = make_handler()

    async def broken_send(msg):
        raise RuntimeError("cannot send")

    ctx = SimpleNamespace(send=broken_send, invoked_with="echo")
    error = commands.CommandInvokeError(RuntimeError("boom"))

    # must not raise even when reporting to the channel fails
    await handler(ctx, error)
    assert "Could not report" in capsys.readouterr().out
