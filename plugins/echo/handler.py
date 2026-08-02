from botcmd.dispatcher import DiscordCommandDispatcher


class EchoDispatcher(DiscordCommandDispatcher):
    command = "echo"

    async def handler(self, ctx, *args):
        """입력한 내용을 그대로 보여줍니다."""
        await ctx.send(f'You typed "{" ".join(args)}"')
