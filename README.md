Discord NAS Bot
===========

A discord bot for personal use (NAS bot)

## How to use

Provide necessary tokens from `.env.template`, invite your bot in the discord server, then turn on the script as follows:

```
# Run uv sync --frozen if package is not yet initialized

uv run python main.py
```

In the discord channel, say `!ping`, then the bot will respond.

## Plugin

This discord bot is extensible with plugins. Below is the usage.

### Add a plugin

Put a python file `handler.py` under `plugins/` folder like below:
```py
# example: plugins/ping/handler.py
# Below bot will be triggered with `!ping` command, only under `bot` channel.

from botcmd.dispatcher import DiscordCommandDispatcher


class PingDispatcher(DiscordCommandDispatcher):
    command = "ping"
    channel = ["bot"]

    async def handler(self, ctx):
        await ctx.send(f"🏓 Pong! {round(self.bot.latency * 1000)}ms")
```

Leave `channel` unset to allow the command in every channel.

Declare the handler as `async def handler(self, ctx, *args)` to receive the command
arguments (space-split, quoted strings kept together):
```py
# example: plugins/echo/handler.py
# `!echo hello world` -> the bot replies: You typed "hello world"

from botcmd.dispatcher import DiscordCommandDispatcher

class EchoDispatcher(DiscordCommandDispatcher):
    command = "echo"

    async def handler(self, ctx, *args):
        await ctx.send(f'You typed "{" ".join(args)}"')
```

A handler declared as `async def handler(self, ctx)` simply ignores any arguments.

### Add a private plugin

For putting a private plugin, put the plugin under `plugins_priv/` folder. This won't be tracked by git.

### Enabling a plugin

Just putting a plugin will be fine.

### Testing a plugin

Put a `test_handler.py` next to the plugin's `handler.py`. Use `load_plugin_handler` to
import the handler under test:
```py
# example: plugins/ping/test_handler.py

from types import SimpleNamespace

from botcmd.testing import load_plugin_handler

handler = load_plugin_handler(__file__)


async def test_ping():
    sent = []

    async def send(msg):
        sent.append(msg)

    dispatcher = handler.PingDispatcher(SimpleNamespace(latency=0.123))
    await dispatcher.handler(SimpleNamespace(send=send))
    assert sent == ["🏓 Pong! 123ms"]
```

`uv run pytest` collects every plugin's tests (including `plugins_priv/`) together with
the framework tests under `tests/`. Async test functions work out of the box.

### Disabling a plugin

Add a environment variable `DISABLED_PLUGINS=` in `.env` file like following:
```
DISABLED_PLUGINS=bot,downloader
```

## Development

Lint and format with [ruff](https://docs.astral.sh/ruff/), run tests with pytest:
```
uv run ruff check .
uv run ruff format .
uv run pytest
```

CI runs all of the above on every push and pull request.
