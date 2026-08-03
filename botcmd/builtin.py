from botcmd.scheduler import next_delay

# discord rejects messages over 2000 characters
MAX_MESSAGE = 1900


def _format_delay(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"
    return f"{seconds // 86400}d{(seconds % 86400) // 3600:02d}h"


def _command_lines(bot):
    lines = []
    for command in sorted(bot.commands, key=lambda c: c.name):
        if command.hidden:
            continue
        extras = command.extras or {}
        entry = f"• `!{command.name}`"
        channels = extras.get("channels") or []
        if channels:
            entry += " " + " ".join(f"#{c}" for c in channels)
        summary = (command.short_doc or "").strip()
        if summary:
            entry += f" — {summary}"
        lines.append(entry)
    return lines or ["(none)"]


def _cron_lines(scheduler):
    if scheduler is None:
        return ["(scheduler unavailable)"]

    lines = []
    for dispatcher in scheduler.scheduled:
        name = getattr(dispatcher, "plugin_name", "") or type(dispatcher).__name__
        entry = f"• `{name}` `{dispatcher.cron}`"
        if dispatcher.channel:
            entry += " → " + " ".join(f"#{c}" for c in dispatcher.channel)
        entry += f", next in {_format_delay(next_delay(dispatcher.cron))}"
        lines.append(entry)

    if not lines:
        return ["(none)"]
    if not scheduler.running:
        lines.append("_schedules are registered but not started yet_")
    return lines


def build_status(bot, scheduler=None):
    """Render the list of usable commands and active cron schedules."""
    lines = ["**Commands**", *_command_lines(bot), "", "**Scheduled**", *_cron_lines(scheduler)]

    message = "\n".join(lines)
    if len(message) > MAX_MESSAGE:
        message = message[:MAX_MESSAGE].rsplit("\n", 1)[0] + "\n… truncated"
    return message


def register_bot_command(bot, scheduler=None):
    """Register the built-in `!bot` command.

    This lives here rather than in a plugin because it needs the scheduler,
    which plugins are not given.
    """

    @bot.command(name="bot")
    async def bot_command(ctx):
        """사용 가능한 커맨드와 등록된 크론을 보여줍니다."""
        await ctx.send(build_status(bot, scheduler))

    return bot_command
