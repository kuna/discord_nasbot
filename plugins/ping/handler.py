from botcmd.dispatcher import DiscordCommandDispatcher


class PingDispatcher(DiscordCommandDispatcher):
    command = "ping"

    async def handler(self, ctx):
        """봇의 응답 속도를 확인합니다."""
        await ctx.send(f"🏓 Pong! {round(self.bot.latency * 1000)}ms")
