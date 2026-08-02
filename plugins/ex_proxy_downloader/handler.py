from pathlib import Path
from urllib.parse import urlparse

from botcmd.dispatcher import DiscordCommandDispatcher


class ExDownloaderDispatcher(DiscordCommandDispatcher):
    command = "ex_proxy_download"

    async def handler(self, ctx, *args):
        """URL의 파일을 프록시로 다운로드합니다.

        사용법: !ex_proxy_download <url> [filename|stdout]
        """
        if not args:
            await ctx.send("Usage: `!ex_proxy_download <url> [filename|stdout]`")
            return

        url = args[0]
        filename = args[1] if len(args) > 1 else Path(urlparse(url).path).name
        if not filename:
            await ctx.send("Cannot infer a filename from the URL; pass one explicitly.")
            return

        web = self.dep.webproxy
        if not web:
            raise Exception("Proxy is not ready")
        if filename == "stdout":
            content = await web.read(url)
            content_trunc = content[:200]
            await ctx.send(f"Content: {content_trunc}")
        else:
            download_dir = Path(self.dep.config.DOWNLOAD_FOLDER)
            path = await web.download(download_dir / filename, url)
            await ctx.send(f"✅ Downloaded to `{path}`")
