from types import SimpleNamespace

import discord
from discord.ext import commands

from botcmd.builtin import MAX_MESSAGE, _format_delay, build_status, register_bot_command
from botcmd.dispatcher import DiscordCommandDispatcher
from botcmd.loader import load_plugins
from botcmd.scheduler import CronScheduler

PLUGIN = """
from botcmd.dispatcher import DiscordCommandDispatcher


class Dispatcher(DiscordCommandDispatcher):
    command = "greet"
    channel = ["bot"]

    async def handler(self, ctx, *args):
        \"\"\"Says hello.\"\"\"
        await ctx.send("hi")
"""

CRON_PLUGIN = """
from botcmd.dispatcher import DiscordCommandDispatcher


class Dispatcher(DiscordCommandDispatcher):
    cron = "*/30 * * * *"
    channel = ["bot"]

    async def handler(self, ctx, *args):
        await ctx.send("tick")
"""


def make_bot():
    return commands.Bot(command_prefix="!", intents=discord.Intents.default())


def write_plugin(root, name, source):
    plugin_dir = root / "plugins" / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "handler.py").write_text(source)


def test_format_delay():
    assert _format_delay(45) == "45s"
    assert _format_delay(90) == "1m"
    assert _format_delay(3700) == "1h01m"
    assert _format_delay(90000) == "1d01h"


def test_lists_commands_with_channel_and_summary(tmp_path):
    write_plugin(tmp_path, "greeter", PLUGIN)
    bot = make_bot()
    load_plugins(bot, root=tmp_path)

    status = build_status(bot)

    assert "**Commands**" in status
    assert "`!greet`" in status
    assert "#bot" in status
    assert "Says hello." in status


def test_lists_scheduled_crons(tmp_path):
    write_plugin(tmp_path, "ticker", CRON_PLUGIN)
    bot = make_bot()
    scheduler = CronScheduler(bot)
    load_plugins(bot, root=tmp_path, scheduler=scheduler)

    status = build_status(bot, scheduler)

    assert "**Scheduled**" in status
    assert "`ticker`" in status
    assert "`*/30 * * * *`" in status
    assert "→ #bot" in status
    assert "next in " in status
    # registered but start() was never called
    assert "not started yet" in status


def test_started_scheduler_has_no_warning(tmp_path):
    write_plugin(tmp_path, "ticker", CRON_PLUGIN)
    bot = make_bot()
    scheduler = CronScheduler(bot)
    load_plugins(bot, root=tmp_path, scheduler=scheduler)
    scheduler._tasks = ["pretend-running"]

    assert "not started yet" not in build_status(bot, scheduler)


def test_reports_no_crons(tmp_path):
    write_plugin(tmp_path, "greeter", PLUGIN)
    bot = make_bot()
    scheduler = CronScheduler(bot)
    load_plugins(bot, root=tmp_path, scheduler=scheduler)

    assert "**Scheduled**\n(none)" in build_status(bot, scheduler)


def test_reports_missing_scheduler():
    assert "(scheduler unavailable)" in build_status(make_bot())


def test_long_output_is_truncated(tmp_path):
    for i in range(120):
        write_plugin(tmp_path, f"p{i}", PLUGIN.replace('"greet"', f'"greet{i}"'))
    bot = make_bot()
    load_plugins(bot, root=tmp_path)

    status = build_status(bot)

    assert len(status) <= MAX_MESSAGE + len("\n… truncated")
    assert status.endswith("… truncated")


async def test_bot_command_is_registered_and_sends_status(tmp_path):
    write_plugin(tmp_path, "greeter", PLUGIN)
    bot = make_bot()
    scheduler = CronScheduler(bot)
    load_plugins(bot, root=tmp_path, scheduler=scheduler)
    register_bot_command(bot, scheduler)

    assert bot.get_command("bot") is not None

    sent = []

    async def send(msg):
        sent.append(msg)

    await bot.get_command("bot").callback(SimpleNamespace(send=send))

    assert "**Commands**" in sent[0]
    # it lists itself too
    assert "`!bot`" in sent[0]
    assert "`!greet`" in sent[0]


def test_command_without_channel_shows_no_restriction(tmp_path):
    write_plugin(tmp_path, "greeter", PLUGIN.replace('channel = ["bot"]', ""))
    bot = make_bot()
    load_plugins(bot, root=tmp_path)

    line = next(line for line in build_status(bot).splitlines() if "!greet" in line)
    assert "#" not in line


def test_cron_falls_back_to_class_name_without_plugin_name():
    class Anonymous(DiscordCommandDispatcher):
        cron = "0 * * * *"

    scheduler = CronScheduler(make_bot())
    scheduler.add(Anonymous(None))

    assert "`Anonymous`" in build_status(make_bot(), scheduler)
