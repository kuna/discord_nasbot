class DiscordCommandDispatcher:
    """Base class for plugin command dispatchers.

    Subclass this in a plugin's handler.py and set:
        command: the command name, invoked as `!<command>`
        channel: channel names the command is allowed in (empty = all channels)
        cron: 5-field cron expression to also run the plugin on a schedule,
              e.g. "*/10 * * * *". Scheduled output goes to the first channel
              named in `channel`; with none set it is logged instead.

    A plugin may set `cron` without `command` to be schedule-only.

    The bot instance is available as `self.bot` inside the handler, and shared
    dependencies (see depend.py) as `self.dep` — e.g. `self.dep.web` for web
    requests, `self.dep.webproxy` for proxied ones (None unless PROXY_HOST is
    configured), and `self.dep.config` for the app config.

    Declare the handler as `async def handler(self, ctx, *args)` to receive the
    command arguments (space-split, quoted strings kept together), e.g.
    `!cmd hello world` -> args = ("hello", "world"). A handler declared as
    `async def handler(self, ctx)` ignores any arguments.
    """

    command: str = ""
    channel: list[str] = []
    cron: str = ""

    def __init__(self, bot, dep=None):
        self.bot = bot
        self.dep = dep

    async def handler(self, ctx, *args):
        raise NotImplementedError

    async def scheduled(self, ctx):
        """Called when `cron` fires. Runs the handler with no arguments by
        default; override for behaviour specific to scheduled runs."""
        await self.handler(ctx)
