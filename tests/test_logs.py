import logging
from types import SimpleNamespace

import discord
from discord.ext import commands

from botcmd.logs import register_command_logger


def make_bot():
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
    register_command_logger(bot)
    return bot


def make_ctx():
    return SimpleNamespace(
        command="echo",
        author="dkang#1234",
        channel=SimpleNamespace(name="bot"),
        message=SimpleNamespace(content="!echo hello world"),
    )


async def test_command_invocation_is_logged(caplog):
    bot = make_bot()

    with caplog.at_level(logging.INFO, logger="nasbot"):
        await bot.on_command(make_ctx())

    assert "!echo invoked by dkang#1234 in #bot: !echo hello world" in caplog.text


async def test_command_completion_is_logged(caplog):
    bot = make_bot()

    with caplog.at_level(logging.INFO, logger="nasbot"):
        await bot.on_command_completion(make_ctx())

    assert "!echo completed" in caplog.text
