import zipfile
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from utils.doh import DoHResolver

CHUNK_SIZE = 1 << 16
# lxml is lenient with malformed markup and much faster than html.parser
DEFAULT_HTML_PARSER = "lxml"

# Sent instead of aiohttp's "Python/3.x aiohttp/3.y" User-Agent, which plenty of
# sites reject outright. This is what a desktop Chrome sends when you open a URL.
# Accept-Encoding is deliberately left out: aiohttp sets it from the codecs it can
# actually decode, and claiming e.g. brotli without support yields unreadable bodies.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _filename_from_url(url, fallback):
    return Path(urlparse(url).path).name or fallback


class Web:
    """Plain web accessor. See utils.webproxy.WebProxy for the proxied variant.

    Pass doh_url to resolve hostnames over DNS-over-HTTPS instead of the system
    resolver. When proxy is set, both the requests and the DoH lookups go
    through it.

    Requests carry BROWSER_HEADERS so servers don't reject them as a bot; pass
    headers to add to or override individual entries.
    """

    def __init__(self, doh_url=None, proxy=None, headers=None):
        self._proxy = proxy
        self._resolver = DoHResolver(doh_url, proxy=proxy) if doh_url else None
        self._headers = {**BROWSER_HEADERS, **(headers or {})}

    def _session(self):
        # the resolver is shared across sessions; aiohttp only closes a resolver
        # it created itself, so closing a session leaves ours intact
        connector = aiohttp.TCPConnector(resolver=self._resolver) if self._resolver else None
        return aiohttp.ClientSession(connector=connector, headers=self._headers)

    async def close(self):
        """Release the DoH resolver's own connection, if any."""
        if self._resolver:
            await self._resolver.close()

    async def read(self, url):
        """Return the response body of url as text."""
        async with self._session() as session:
            async with session.get(url, proxy=self._proxy) as resp:
                resp.raise_for_status()
                return await resp.text()

    async def read_binary(self, url):
        """Return the response body of url as binary."""
        async with self._session() as session:
            async with session.get(url, proxy=self._proxy) as resp:
                resp.raise_for_status()
                return await resp.read()

    async def read_html(self, url, parser=DEFAULT_HTML_PARSER):
        """Fetch url and return it as a BeautifulSoup document.

        Supports the usual soup API, e.g.
            soup = await dep.web.read_html(url)
            soup.title.string
            [a["href"] for a in soup.select("a[href]")]
        """
        return BeautifulSoup(await self.read(url), parser)

    async def download(self, path, url):
        """Download url into the file at path (parent dirs are created). Returns the Path."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with self._session() as session:
            async with session.get(url, proxy=self._proxy) as resp:
                resp.raise_for_status()
                with path.open("wb") as f:
                    async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                        f.write(chunk)
        return path

    async def archive(self, path, urls):
        """Download urls and store them as a zip archive at path. Returns the Path.

        Archive member names are taken from each URL's filename; duplicates are
        prefixed with their index to keep every member.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with self._session() as session:
            with zipfile.ZipFile(path, "w") as zf:
                seen = set()
                for i, url in enumerate(urls):
                    async with session.get(url, proxy=self._proxy) as resp:
                        resp.raise_for_status()
                        name = _filename_from_url(url, fallback=f"file_{i}")
                        if name in seen:
                            name = f"{i}_{name}"
                        seen.add(name)
                        zf.writestr(name, await resp.read())
        return path
