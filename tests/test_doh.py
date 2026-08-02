import socket

import aiohttp
import pytest
from aiohttp import web as aioweb
from aiohttp.test_utils import TestServer

from utils.doh import DoHResolver


@pytest.fixture
async def doh():
    """A stub DoH endpoint that records the queries it receives."""
    state = {"queries": [], "answers": {}, "status": 0}

    async def endpoint(request):
        name = request.query["name"]
        qtype = request.query["type"]
        state["queries"].append((name, qtype))
        answers = state["answers"].get((name, qtype), [])
        return aioweb.json_response(
            {"Status": state["status"], "Answer": answers},
            content_type="application/dns-json",
        )

    app = aioweb.Application()
    app.router.add_get("/dns-query", endpoint)
    server = TestServer(app)
    await server.start_server()
    state["url"] = str(server.make_url("/dns-query"))
    yield state
    await server.close()


def a_record(name, ip, ttl=300):
    return {"name": name, "type": 1, "TTL": ttl, "data": ip}


def aaaa_record(name, ip, ttl=300):
    return {"name": name, "type": 28, "TTL": ttl, "data": ip}


async def test_resolves_ipv4(doh):
    doh["answers"][("example.com", "A")] = [a_record("example.com", "93.184.216.34")]
    resolver = DoHResolver(doh["url"])

    result = await resolver.resolve("example.com", 443)
    await resolver.close()

    assert result == [
        {
            "hostname": "example.com",
            "host": "93.184.216.34",
            "port": 443,
            "family": socket.AF_INET,
            "proto": 0,
            "flags": socket.AI_NUMERICHOST | socket.AI_NUMERICSERV,
        }
    ]


async def test_resolves_ipv6(doh):
    doh["answers"][("example.com", "AAAA")] = [aaaa_record("example.com", "2606:2800::1")]
    resolver = DoHResolver(doh["url"])

    result = await resolver.resolve("example.com", 443, family=socket.AF_INET6)
    await resolver.close()

    assert [r["host"] for r in result] == ["2606:2800::1"]
    assert result[0]["family"] == socket.AF_INET6


async def test_unspec_family_queries_both(doh):
    doh["answers"][("example.com", "A")] = [a_record("example.com", "93.184.216.34")]
    doh["answers"][("example.com", "AAAA")] = [aaaa_record("example.com", "2606:2800::1")]
    resolver = DoHResolver(doh["url"])

    result = await resolver.resolve("example.com", 80, family=socket.AF_UNSPEC)
    await resolver.close()

    assert doh["queries"] == [("example.com", "A"), ("example.com", "AAAA")]
    assert [r["host"] for r in result] == ["93.184.216.34", "2606:2800::1"]


async def test_multiple_addresses_are_all_returned(doh):
    doh["answers"][("example.com", "A")] = [
        a_record("example.com", "1.2.3.4"),
        a_record("example.com", "5.6.7.8"),
    ]
    resolver = DoHResolver(doh["url"])

    result = await resolver.resolve("example.com")
    await resolver.close()

    assert [r["host"] for r in result] == ["1.2.3.4", "5.6.7.8"]


async def test_non_address_records_are_skipped(doh):
    doh["answers"][("example.com", "A")] = [
        {"name": "example.com", "type": 5, "TTL": 300, "data": "cdn.example.net."},
        a_record("example.com", "1.2.3.4"),
    ]
    resolver = DoHResolver(doh["url"])

    result = await resolver.resolve("example.com")
    await resolver.close()

    assert [r["host"] for r in result] == ["1.2.3.4"]


async def test_answers_are_cached(doh):
    doh["answers"][("example.com", "A")] = [a_record("example.com", "1.2.3.4")]
    resolver = DoHResolver(doh["url"])

    await resolver.resolve("example.com")
    await resolver.resolve("example.com")
    await resolver.close()

    assert doh["queries"] == [("example.com", "A")]


async def test_expired_cache_is_refetched(doh):
    doh["answers"][("example.com", "A")] = [a_record("example.com", "1.2.3.4")]
    resolver = DoHResolver(doh["url"])

    await resolver.resolve("example.com")
    # force expiry
    addresses, _ = resolver._cache[("example.com", socket.AF_INET)]
    resolver._cache[("example.com", socket.AF_INET)] = (addresses, 0)
    await resolver.resolve("example.com")
    await resolver.close()

    assert doh["queries"] == [("example.com", "A")] * 2


async def test_failed_status_raises(doh):
    doh["status"] = 2  # SERVFAIL
    resolver = DoHResolver(doh["url"])

    with pytest.raises(OSError, match="status 2"):
        await resolver.resolve("example.com")
    await resolver.close()


async def test_empty_answer_raises(doh):
    resolver = DoHResolver(doh["url"])

    with pytest.raises(OSError, match="no address"):
        await resolver.resolve("nope.example.com")
    await resolver.close()


async def test_lookups_go_through_the_proxy(doh):
    """A DoH host that cannot resolve still works when reached via the proxy."""
    doh["answers"][("example.com", "A")] = [a_record("example.com", "1.2.3.4")]

    # nothing resolves doh.invalid, so the lookup can only succeed through the
    # proxy, which is where the stub server lives
    resolver = DoHResolver("http://doh.invalid/dns-query", proxy=doh["url"].rsplit("/", 1)[0])

    result = await resolver.resolve("example.com")
    await resolver.close()

    assert [r["host"] for r in result] == ["1.2.3.4"]
    assert doh["queries"] == [("example.com", "A")]


async def test_lookups_fail_without_the_proxy(doh):
    """Same unresolvable DoH host, but no proxy: the lookup must fail."""
    resolver = DoHResolver("http://doh.invalid/dns-query")

    with pytest.raises(aiohttp.ClientError):
        await resolver.resolve("example.com")
    await resolver.close()


async def test_close_is_idempotent(doh):
    resolver = DoHResolver(doh["url"])
    doh["answers"][("example.com", "A")] = [a_record("example.com", "1.2.3.4")]

    await resolver.resolve("example.com")
    await resolver.close()
    await resolver.close()
