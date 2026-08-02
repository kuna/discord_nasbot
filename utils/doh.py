import socket
import time

import aiohttp
from aiohttp.abc import AbstractResolver

# https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-json
DEFAULT_DOH_URL = "https://1.1.1.1/dns-query"
DNS_JSON_ACCEPT = "application/dns-json"

# DNS record types in the JSON answer
TYPE_A = 1
TYPE_AAAA = 28

_QUERY_TYPES = {
    socket.AF_INET: ("A",),
    socket.AF_INET6: ("AAAA",),
    socket.AF_UNSPEC: ("A", "AAAA"),
}
_RECORD_FAMILY = {TYPE_A: socket.AF_INET, TYPE_AAAA: socket.AF_INET6}

MIN_TTL = 30
MAX_TTL = 3600


class DoHResolver(AbstractResolver):
    """aiohttp resolver that looks names up over DNS-over-HTTPS.

    Answers are cached until their TTL expires. Prefer a DoH URL with an IP
    literal host (the default): aiohttp resolves IP literals without calling a
    resolver, so the lookups never need plaintext DNS to bootstrap themselves.

    Pass proxy to send the lookups through an HTTP proxy as well. The lookup
    session always uses the system resolver, so resolving the proxy's own
    hostname cannot recurse back into DoH (give the proxy as an IP to avoid
    that lookup entirely).
    """

    def __init__(self, url=DEFAULT_DOH_URL, timeout=5, proxy=None):
        self._url = url
        self._proxy = proxy
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = None
        self._cache = {}

    async def _get_session(self):
        if self._session is None or self._session.closed:
            # plain session: this is the lookup channel itself, it must not
            # recurse back into DoH
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def _query(self, host, qtype):
        session = await self._get_session()
        params = {"name": host, "type": qtype}
        async with session.get(
            self._url, params=params, headers={"accept": DNS_JSON_ACCEPT}, proxy=self._proxy
        ) as resp:
            resp.raise_for_status()
            # some resolvers answer with content-type application/dns-json
            payload = await resp.json(content_type=None)

        if payload.get("Status") != 0:
            raise OSError(f"DoH lookup for {host} failed with status {payload.get('Status')}")

        addresses, ttl = [], MAX_TTL
        for answer in payload.get("Answer", []):
            family = _RECORD_FAMILY.get(answer.get("type"))
            if family is None:
                # CNAME and friends: the resolver already followed them
                continue
            addresses.append((answer["data"], family))
            ttl = min(ttl, answer.get("TTL", MAX_TTL))
        return addresses, max(ttl, MIN_TTL)

    async def resolve(self, host, port=0, family=socket.AF_INET):
        key = (host, family)
        cached = self._cache.get(key)
        if cached and cached[1] > time.monotonic():
            addresses = cached[0]
        else:
            addresses = []
            for qtype in _QUERY_TYPES.get(family, ("A",)):
                found, ttl = await self._query(host, qtype)
                addresses.extend(found)
            if not addresses:
                raise OSError(f"DoH lookup for {host} returned no address")
            self._cache[key] = (addresses, time.monotonic() + ttl)

        return [
            {
                "hostname": host,
                "host": address,
                "port": port,
                "family": addr_family,
                "proto": 0,
                "flags": socket.AI_NUMERICHOST | socket.AI_NUMERICSERV,
            }
            for address, addr_family in addresses
        ]

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
