import asyncio
import shlex
import sys
from types import SimpleNamespace

from discord.ext import commands

from botcmd.builtin import build_status

DEFAULT_CHANNEL = "bot"
PROMPT = "> "

HELP = """\
Type a command as you would in discord, e.g. `!ping` or `!echo hello`
(the leading ! is optional). Meta commands:
  /channel [name]  show or change the simulated channel
  /cron [name]     list cron plugins, or run one now
  /help            this message
  /quit            leave (Ctrl-D also works)"""


class CliBot(commands.Bot):
    """Bot that is never connected; used to register plugins for CLI runs."""

    @property
    def latency(self):
        # the real property is NaN without a gateway, which breaks round()
        return 0.0


class CliContext:
    """Stand-in for a discord Context that reads/writes the terminal."""

    def __init__(self, bot, channel_name, write):
        self.bot = bot
        self.channel = SimpleNamespace(name=channel_name)
        self.author = "cli"
        self.message = SimpleNamespace(content="")
        self.invoked_with = ""
        self._write = write

    async def send(self, message):
        self._write(str(message))
        return None


def _stdin_reader():
    async def read_line():
        if sys.stdin.isatty():
            sys.stdout.write(PROMPT)
            sys.stdout.flush()
        line = await asyncio.to_thread(sys.stdin.readline)
        return line or None  # "" means EOF

    return read_line


async def _run_command(bot, line, channel, write):
    try:
        parts = shlex.split(line)
    except ValueError as e:
        write(f"! could not parse input: {e}")
        return

    name, args = parts[0].lstrip("!"), parts[1:]
    command = bot.get_command(name)
    if command is None:
        write(f"! unknown command: {name} (try !bot)")
        return

    ctx = CliContext(bot, channel, write)
    ctx.invoked_with = name
    ctx.message.content = line

    for check in command.checks:
        if not await check(ctx):
            allowed = (command.extras or {}).get("channels") or []
            write(f"! `!{name}` is not allowed in #{channel} (allowed: {', '.join(allowed)})")
            return

    try:
        await command.callback(ctx, *args)
    except TypeError as e:
        # wrong argument count reads like a usage error, not a crash
        write(f"! `!{name}` did not accept those arguments: {e}")
    except Exception as e:
        write(f"! `!{name}` failed: {type(e).__name__}: {e}")


async def _run_cron(bot, scheduler, argument, channel, write):
    if scheduler is None or not scheduler.scheduled:
        write("! no cron plugins are registered")
        return

    def label(dispatcher):
        return getattr(dispatcher, "plugin_name", "") or type(dispatcher).__name__

    if not argument:
        for dispatcher in scheduler.scheduled:
            write(f"  {label(dispatcher)}  {dispatcher.cron}")
        write("run one with `/cron <name>`")
        return

    dispatcher = next((d for d in scheduler.scheduled if label(d) == argument), None)
    if dispatcher is None:
        write(f"! no cron plugin named {argument}")
        return

    # scheduled runs normally post through ScheduledContext; mimic that here
    ctx = CliContext(bot, channel, write)
    try:
        await dispatcher.scheduled(ctx)
    except Exception as e:
        write(f"! {argument} failed: {type(e).__name__}: {e}")


async def run_cli(bot, scheduler=None, channel=DEFAULT_CHANNEL, read_line=None, write=print):
    """Read commands from stdin and dispatch them to the loaded plugins."""
    read_line = read_line or _stdin_reader()
    write(f"CLI test mode — plugins loaded, no discord connection. Channel: #{channel}")
    write(HELP)

    while True:
        line = await read_line()
        if line is None:
            write("Bye!")
            return
        line = line.strip()
        if not line:
            continue

        if line.startswith("/"):
            meta, _, argument = line[1:].partition(" ")
            meta, argument = meta.strip(), argument.strip()
            if meta in ("quit", "exit"):
                write("Bye!")
                return
            if meta == "help":
                write(HELP)
            elif meta == "channel":
                if argument:
                    channel = argument
                write(f"channel: #{channel}")
            elif meta == "cron":
                await _run_cron(bot, scheduler, argument, channel, write)
            elif meta == "status":
                write(build_status(bot, scheduler))
            else:
                write(f"! unknown meta command: /{meta}")
            continue

        await _run_command(bot, line, channel, write)


__all__ = ["CliBot", "CliContext", "run_cli"]
