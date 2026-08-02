class DiscordCommandDispatcher:
    """Base class for plugin command dispatchers.

    Subclass this in a plugin's handler.py and set:
        command: the command name, invoked as `!<command>`
        channel: channel names the command is allowed in (empty = all channels)

    The bot instance is available as `self.bot` inside the handler.

    Declare the handler as `async def handler(self, ctx, *args)` to receive the
    command arguments (space-split, quoted strings kept together), e.g.
    `!cmd hello world` -> args = ("hello", "world"). A handler declared as
    `async def handler(self, ctx)` ignores any arguments.
    """

    command: str = ""
    channel: list[str] = []

    def __init__(self, bot):
        self.bot = bot

    async def handler(self, ctx, *args):
        raise NotImplementedError
