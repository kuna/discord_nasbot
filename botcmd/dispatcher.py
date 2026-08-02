class DiscordCommandDispatcher:
    """Base class for plugin command dispatchers.

    Subclass this in a plugin's handler.py and set:
        command: the command name, invoked as `!<command>`
        channel: channel names the command is allowed in (empty = all channels)

    The bot instance is available as `self.bot` inside the handler.
    """

    command: str = ""
    channel: list[str] = []

    def __init__(self, bot):
        self.bot = bot

    async def handler(self, ctx):
        raise NotImplementedError
