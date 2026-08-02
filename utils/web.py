import zipfile
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from utils.doh import DoHResolver

CHUNK_SIZE = 1 << 16


def _filename_from_url(url, fallback):
    return Path(urlparse(url).path).name or fallback


class Web:
    """Plain web accessor. See utils.webproxy.WebProxy for the proxied variant.

    Pass doh_url to resolve hostnames over DNS-over-HTTPS instead of the system
    resolver. When proxy is set, both the requests and the DoH lookups go
    through it.
    """

    def __init__(self, doh_url=None, proxy=None):
        self._proxy = proxy
        self._resolver = DoHResolver(doh_url, proxy=proxy) if doh_url else None

    def _session(self):
        # the resolver is shared across sessions; aiohttp only closes a resolver
        # it created itself, so closing a session leaves ours intact
        connector = aiohttp.TCPConnector(resolver=self._resolver) if self._resolver else None
        return aiohttp.ClientSession(connector=connector)

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
