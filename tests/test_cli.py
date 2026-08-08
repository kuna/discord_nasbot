import discord

from botcmd.builtin import register_bot_command
from botcmd.cli import CliBot, CliContext, run_cli
from botcmd.loader import load_plugins
from botcmd.scheduler import CronScheduler

PLUGIN = """
from botcmd.dispatcher import DiscordCommandDispatcher


class Greet(DiscordCommandDispatcher):
    command = "greet"

    async def handler(self, ctx, *args):
        \"\"\"Greets.\"\"\"
        await ctx.send("hello " + " ".join(args))


class OnlyHere(DiscordCommandDispatcher):
    command = "here"
    channel = ["bot"]

    async def handler(self, ctx):
        await ctx.send("in the right channel")


class Boom(DiscordCommandDispatcher):
    command = "boom"

    async def handler(self, ctx):
        raise RuntimeError("kaboom")


class Latency(DiscordCommandDispatcher):
    command = "lat"

    async def handler(self, ctx):
        await ctx.send(f"{round(self.bot.latency * 1000)}ms")
"""

CRON_PLUGIN = """
from botcmd.dispatcher import DiscordCommandDispatcher


class Ticker(DiscordCommandDispatcher):
    cron = "*/5 * * * *"

    async def handler(self, ctx, *args):
        await ctx.send("tick")
"""


def write_plugin(root, name, source):
    plugin_dir = root / "plugins" / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "handler.py").write_text(source)


def build(tmp_path, sources=(("demo", PLUGIN),)):
    bot = CliBot(command_prefix="!", intents=discord.Intents.default())
    for name, source in sources:
        write_plugin(tmp_path, name, source)
    scheduler = CronScheduler(bot)
    load_plugins(bot, root=tmp_path, scheduler=scheduler)
    register_bot_command(bot, scheduler)
    return bot, scheduler


async def drive(bot, scheduler, lines, channel="bot"):
    """Feed lines to the CLI and return everything it wrote."""
    queued = list(lines)
    written = []

    async def read_line():
        return queued.pop(0) if queued else None

    await run_cli(bot, scheduler, channel=channel, read_line=read_line, write=written.append)
    return "\n".join(written)


async def test_runs_a_command(tmp_path):
    bot, scheduler = build(tmp_path)

    out = await drive(bot, scheduler, ["!greet world"])

    assert "hello world" in out


async def test_leading_bang_is_optional(tmp_path):
    bot, scheduler = build(tmp_path)

    assert "hello there" in await drive(bot, scheduler, ["greet there"])


async def test_quoted_arguments_stay_together(tmp_path):
    bot, scheduler = build(tmp_path)

    assert "hello a b" in await drive(bot, scheduler, ['!greet "a b"'])


async def test_unknown_command(tmp_path):
    bot, scheduler = build(tmp_path)

    assert "unknown command: nope" in await drive(bot, scheduler, ["!nope"])


async def test_channel_restriction_is_enforced(tmp_path):
    bot, scheduler = build(tmp_path)

    blocked = await drive(bot, scheduler, ["!here"], channel="general")
    assert "not allowed in #general" in blocked
    assert "allowed: bot" in blocked

    assert "in the right channel" in await drive(bot, scheduler, ["!here"], channel="bot")


async def test_channel_can_be_switched(tmp_path):
    bot, scheduler = build(tmp_path)

    out = await drive(bot, scheduler, ["/channel general", "!here"], channel="bot")

    assert "channel: #general" in out
    assert "not allowed in #general" in out


async def test_failing_command_is_reported_not_raised(tmp_path):
    bot, scheduler = build(tmp_path)

    out = await drive(bot, scheduler, ["!boom", "!greet still alive"])

    assert "`!boom` failed: RuntimeError: kaboom" in out
    # the loop keeps going
    assert "hello still alive" in out


async def test_wrong_argument_count_is_reported(tmp_path):
    bot, scheduler = build(tmp_path)

    out = await drive(bot, scheduler, ["!here too many args"])

    assert "did not accept those arguments" in out


async def test_latency_is_usable_without_a_connection(tmp_path):
    """The real Bot.latency is NaN offline, which would break round()."""
    bot, scheduler = build(tmp_path)

    assert "0ms" in await drive(bot, scheduler, ["!lat"])


async def test_status_meta_command(tmp_path):
    bot, scheduler = build(tmp_path)

    out = await drive(bot, scheduler, ["/status"])

    assert "**Commands**" in out
    assert "`!greet`" in out


async def test_cron_listing_and_manual_run(tmp_path):
    bot, scheduler = build(tmp_path, sources=[("ticker", CRON_PLUGIN)])

    listing = await drive(bot, scheduler, ["/cron"])
    assert "ticker" in listing
    assert "*/5 * * * *" in listing

    assert "tick" in await drive(bot, scheduler, ["/cron ticker"])


async def test_cron_run_with_unknown_name(tmp_path):
    bot, scheduler = build(tmp_path, sources=[("ticker", CRON_PLUGIN)])

    assert "no cron plugin named nope" in await drive(bot, scheduler, ["/cron nope"])


async def test_cron_without_any_registered(tmp_path):
    bot, scheduler = build(tmp_path)

    assert "no cron plugins are registered" in await drive(bot, scheduler, ["/cron"])


async def test_quit_stops_before_later_lines(tmp_path):
    bot, scheduler = build(tmp_path)

    out = await drive(bot, scheduler, ["/quit", "!greet unreachable"])

    assert "Bye!" in out
    assert "unreachable" not in out


async def test_eof_ends_the_loop(tmp_path):
    bot, scheduler = build(tmp_path)

    assert "Bye!" in await drive(bot, scheduler, [])


async def test_blank_lines_and_unknown_meta(tmp_path):
    bot, scheduler = build(tmp_path)

    out = await drive(bot, scheduler, ["", "   ", "/nope"])

    assert "unknown meta command: /nope" in out


async def test_unbalanced_quotes_are_reported(tmp_path):
    bot, scheduler = build(tmp_path)

    assert "could not parse input" in await drive(bot, scheduler, ['!greet "oops'])


async def test_cli_context_sends_to_the_writer():
    written = []
    ctx = CliContext(None, "bot", written.append)

    await ctx.send("hi")

    assert written == ["hi"]
    assert ctx.channel.name == "bot"
