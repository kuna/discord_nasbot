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

### Example usage

This solution could be used with NAS after linking with it, e.g. NFS
```sh
mount -t nfs <addr>:/ /mnt/nas
```

Then you can make some integration scripts triggered by Discord NAS Bot like ...
* Reorganizing files
* Print file status
* Download some files from given arguments

etc ...

## Deploy with Docker

The image bundles [SpoofDPI](https://github.com/xvzc/SpoofDPI) as a local proxy, so
`self.dep.webproxy` works out of the box — no proxy setup on the host.

```
docker compose up -d --build
```

or without compose:

```
make docker-build
make docker-run
```

Credentials are never baked into the image; `.env` is passed at runtime
(`--env-file .env` / compose `env_file`). Downloads are written to the `/data`
volume, which compose maps to `./downloads`.

Proxy behaviour is controlled by these variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `SPOOFDPI_ENABLED` | `1` | start the bundled proxy and point the bot at it |
| `SPOOFDPI_LISTEN_ADDR` | `127.0.0.1:8080` | address the bundled proxy listens on |
| `SPOOFDPI_LOG_LEVEL` | `info` | spoofdpi log level |
| `PROXY_HOST` / `PROXY_PORT` | the bundled proxy | set to use a different proxy instead |

Set `SPOOFDPI_ENABLED=0` without `PROXY_HOST` to run with no proxy at all; the
proxy-only commands then report `Proxy is not ready` instead of failing silently.

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

### Using dependencies

Every dispatcher receives the shared dependencies from `depend.py` as `self.dep`:

* `self.dep.web` — web accessor with `read(url)`, `download(path, url)`, `archive(path, urls)`
* `self.dep.webproxy` — same interface, but routed through the DPI proxy; `None` unless
  `PROXY_HOST` (and optionally `PROXY_PORT`) is set in `.env`
* `self.dep.config` — the app config

Working examples:

* `plugins/ex_downloader` — `!ex_download <url> [filename|stdout]` downloads a file
  (or shows its content with `stdout`)
* `plugins/ex_proxy_downloader` — `!ex_proxy_download <url> [filename|stdout]`, same
  but through the DPI proxy (fails if `PROXY_HOST` is not configured)
* `plugins/plugin_downloader` — `!plugin_download <name> <handler.py url>` installs a
  plugin's `handler.py` from a URL

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
