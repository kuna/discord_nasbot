from datetime import datetime

from botcmd.dispatcher import DiscordCommandDispatcher


class ExCronDispatcher(DiscordCommandDispatcher):
    """Runs every 30 minutes, and on demand with `!ex_heartbeat`."""

    command = "ex_heartbeat"
    # cron = "*/30 * * * *"
    # scheduled output goes to the first of these channels that exists
    channel = ["bot"]

    async def handler(self, ctx):
        """봇이 살아있는지 확인합니다."""
        now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        await ctx.send(f"💓 alive at {now}")
