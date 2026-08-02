from pathlib import Path

from botcmd.dispatcher import DiscordCommandDispatcher

PLUGIN_DIR = Path("plugins")


class PluginDownloaderDispatcher(DiscordCommandDispatcher):
    command = "plugin_download"

    async def handler(self, ctx, *args):
        """URL에서 플러그인을 받아 plugins/<name>/에 설치합니다.

        사용법: !plugin_download <name> <handler.py url>
        """
        if len(args) != 2:
            await ctx.send("Usage: `!plugin_download <name> <handler.py url>`")
            return

        name, url = args
        web = self.dep.web
        path = await web.download(PLUGIN_DIR / name / "handler.py", url)
        await ctx.send(f"✅ Plugin '{name}' installed at `{path}`. Restart the bot to load it.")
