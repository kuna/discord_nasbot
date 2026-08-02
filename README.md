Discord bot
===========

A discord bot for personal use.

## How to use

Provide necessary tokens from `.env.template`, invite your bot in the discord server, then turn on the script.

In the discord channel, say `!ping`, then the bot will respond.

## Plugin

This discord bot is extensible with plugins. Below is the usage.

### Add a plugin

Put a python file `handler.py` under `plugins/` folder like below:
```py
# example: plugins/downloader/handler.py
# Below bot will triggered with `!ping` command, only under `bot` channel.

from cmd.dispatcher import DiscordCommandDispatcher

class PingDispatcher(DiscordCommandDispatcher):
    command = "ping"
    channel = ["bot"]

    def handler(ctx):
        await ctx.send(f'🏓 Pong! {round(bot.latency * 1000)}ms')
```

### Add a private plugin

For putting a private plugin, put the plugin under `plugins_priv/` folder. This won't be tracked by git.

### Enabling a plugin

Just putting a plugin will be fine.

### Disabling a plugin

Add a environment variable `DISABLE_PLUGINS=` in `.env` file like following:
```
DISABLE_PLUGINS=bot,downloader
```
