import asyncio
from datetime import datetime

from croniter import croniter

from botcmd.logs import logger


def next_delay(expression, now=None):
    """Seconds from now until the next time expression fires."""
    now = now or datetime.now().astimezone()
    return max((croniter(expression, now).get_next(datetime) - now).total_seconds(), 0)


class ScheduledContext:
    """Stand-in for a discord Context for runs that nobody invoked.

    A scheduled run has no message behind it, so `send` posts to the first
    channel named in the dispatcher's `channel` list. With no channel configured
    there is nowhere to post, and the output is logged instead.
    """

    def __init__(self, bot, channel_names=(), label=""):
        self.bot = bot
        self._channel_names = list(channel_names)
        self._label = label

    @property
    def channel(self):
        for name in self._channel_names:
            for guild in self.bot.guilds:
                found = next((c for c in guild.text_channels if c.name == name), None)
                if found:
                    return found
        return None

    async def send(self, message):
        channel = self.channel
        if channel is None:
            logger.info("[%s] (no channel configured) %s", self._label, message)
            return None
        return await channel.send(message)


class CronScheduler:
    """Runs dispatchers that declare a `cron` expression."""

    def __init__(self, bot):
        self.bot = bot
        self._dispatchers = []
        self._tasks = []

    def add(self, dispatcher):
        """Register a dispatcher; invalid expressions are skipped, not fatal."""
        expression = dispatcher.cron
        if not croniter.is_valid(expression):
            logger.error(
                "Plugin '%s' has an invalid cron expression %r, not scheduling",
                type(dispatcher).__name__,
                expression,
            )
            return False
        self._dispatchers.append(dispatcher)
        return True

    @property
    def scheduled(self):
        return list(self._dispatchers)

    def start(self):
        """Start one loop per dispatcher. Safe to call again (e.g. on reconnect)."""
        if self._tasks:
            return
        for dispatcher in self._dispatchers:
            self._tasks.append(asyncio.create_task(self._run(dispatcher)))
        if self._tasks:
            logger.info("Scheduled %d cron plugin(s)", len(self._tasks))

    async def stop(self):
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks = []

    async def _run(self, dispatcher):
        label = type(dispatcher).__name__
        ctx = ScheduledContext(self.bot, dispatcher.channel, label)
        while True:
            delay = next_delay(dispatcher.cron)
            logger.info("%s (cron %s) runs in %.0fs", label, dispatcher.cron, delay)
            await asyncio.sleep(delay)
            try:
                await dispatcher.scheduled(ctx)
                logger.info("%s scheduled run completed", label)
            except asyncio.CancelledError:
                raise
            except Exception:
                # one bad run must not kill the schedule
                logger.exception("%s scheduled run failed", label)
