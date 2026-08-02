import subprocess

from botcmd.dispatcher import DiscordCommandDispatcher


class WarpDispatcher(DiscordCommandDispatcher):
    command = "warp"

    async def handler(self, ctx, *args):
        """Warp handler

        NOTE: You must install cloudflare warp CLI in your system to use this plugin.
        If not, please install it from https://pkg.cloudflareclient.com/
        """
        if len(args) == 0:
            await ctx.send("Supported commands: on, off, status")
            return
        if args[0] == "on":
            result = subprocess.run(["warp-cli", "connect"], capture_output=True, text=True)
        elif args[0] == "off":
            result = subprocess.run(["warp-cli", "disconnect"], capture_output=True, text=True)
        elif args[0] == "status":
            result = subprocess.run(["warp-cli", "status"], capture_output=True, text=True)
        else:
            raise Exception(f"Unknown command {args[0]}")
        sout = result.stdout.strip()
        serr = result.stderr.strip()
        if sout:
            await ctx.send(f"Result: {result.stdout.strip()}")
        if serr:
            await ctx.send(f"Error: {result.stderr.strip()}")
