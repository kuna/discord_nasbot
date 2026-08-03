import asyncio
import logging
from datetime import datetime
from types import SimpleNamespace

from botcmd.dispatcher import DiscordCommandDispatcher
from botcmd.scheduler import CronScheduler, ScheduledContext, next_delay


class Dispatcher(DiscordCommandDispatcher):
    cron = "*/5 * * * *"

    def __init__(self, bot=None, dep=None):
        super().__init__(bot, dep)
        self.runs = 0

    async def handler(self, ctx, *args):
        self.runs += 1
        await ctx.send(f"run {self.runs}")


def fake_bot(channels=()):
    guild = SimpleNamespace(
        text_channels=[SimpleNamespace(name=name, send=send) for name, send in channels]
    )
    return SimpleNamespace(guilds=[guild])


# --- next_delay ---------------------------------------------------------


def test_next_delay_counts_to_the_next_slot():
    now = datetime(2026, 8, 2, 10, 3, 30).astimezone()
    # next */5 slot is 10:05:00, i.e. 90 seconds away
    assert next_delay("*/5 * * * *", now) == 90


def test_next_delay_is_never_negative():
    now = datetime(2026, 8, 2, 10, 5, 0).astimezone()
    assert next_delay("* * * * *", now) > 0


# --- registration -------------------------------------------------------


def test_add_accepts_a_valid_expression():
    scheduler = CronScheduler(fake_bot())
    assert scheduler.add(Dispatcher()) is True
    assert len(scheduler.scheduled) == 1


def test_add_rejects_an_invalid_expression(caplog):
    class Broken(Dispatcher):
        cron = "not a cron"

    scheduler = CronScheduler(fake_bot())
    with caplog.at_level(logging.ERROR, logger="nasbot"):
        assert scheduler.add(Broken()) is False

    assert scheduler.scheduled == []
    assert "invalid cron expression" in caplog.text


async def test_start_is_idempotent():
    scheduler = CronScheduler(fake_bot())
    scheduler.add(Dispatcher())

    scheduler.start()
    scheduler.start()
    assert len(scheduler._tasks) == 1

    await scheduler.stop()
    assert scheduler._tasks == []


# --- the run loop -------------------------------------------------------


async def test_fires_the_dispatcher_on_schedule(monkeypatch):
    dispatcher = Dispatcher()
    scheduler = CronScheduler(fake_bot())
    scheduler.add(dispatcher)
    # collapse the wait so the loop fires immediately
    monkeypatch.setattr("botcmd.scheduler.next_delay", lambda *a, **k: 0)

    scheduler.start()
    await asyncio.sleep(0.05)
    await scheduler.stop()

    assert dispatcher.runs > 0


async def test_a_failing_run_does_not_stop_the_schedule(monkeypatch, caplog):
    class Failing(Dispatcher):
        async def handler(self, ctx, *args):
            self.runs += 1
            raise RuntimeError("boom")

    dispatcher = Failing()
    scheduler = CronScheduler(fake_bot())
    scheduler.add(dispatcher)
    monkeypatch.setattr("botcmd.scheduler.next_delay", lambda *a, **k: 0)

    with caplog.at_level(logging.ERROR, logger="nasbot"):
        scheduler.start()
        await asyncio.sleep(0.05)
        await scheduler.stop()

    assert dispatcher.runs > 1, "the loop should keep running after a failure"
    assert "scheduled run failed" in caplog.text


# --- ScheduledContext ---------------------------------------------------


async def test_context_sends_to_the_named_channel():
    posted = []

    async def send(msg):
        posted.append(msg)

    bot = fake_bot([("general", send), ("bot", send)])
    ctx = ScheduledContext(bot, ["bot"], "Test")

    assert ctx.channel.name == "bot"
    await ctx.send("hello")
    assert posted == ["hello"]


async def test_context_without_channel_logs_instead(caplog):
    ctx = ScheduledContext(fake_bot(), [], "Test")

    with caplog.at_level(logging.INFO, logger="nasbot"):
        assert await ctx.send("hello") is None

    assert "no channel configured" in caplog.text
    assert "hello" in caplog.text


async def test_context_falls_back_when_channel_is_missing(caplog):
    async def send(msg):
        raise AssertionError("should not be called")

    bot = fake_bot([("general", send)])
    ctx = ScheduledContext(bot, ["nonexistent"], "Test")

    assert ctx.channel is None
    with caplog.at_level(logging.INFO, logger="nasbot"):
        await ctx.send("hello")
    assert "no channel configured" in caplog.text
