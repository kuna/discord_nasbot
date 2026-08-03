from botcmd.dispatcher import DiscordCommandDispatcher

MAX_LINKS = 5


class ExScraperDispatcher(DiscordCommandDispatcher):
    command = "ex_scrape"

    async def handler(self, ctx, *args):
        """페이지의 제목과 링크를 보여줍니다. 사용법: !ex_scrape <url>"""
        if not args:
            await ctx.send("Usage: `!ex_scrape <url>`")
            return

        url = args[0]
        soup = await self.dep.web.read_html(url)

        title = soup.title.get_text(strip=True) if soup.title else "(no title)"
        links = [a["href"] for a in soup.select("a[href]")]

        lines = [f"**{title}**", f"{len(links)} link(s)"]
        lines += [f"• {link}" for link in links[:MAX_LINKS]]
        if len(links) > MAX_LINKS:
            lines.append(f"… and {len(links) - MAX_LINKS} more")
        await ctx.send("\n".join(lines))
