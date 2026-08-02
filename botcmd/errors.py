from discord.ext import commands

from botcmd.logs import logger


def register_error_handler(bot):
    """Report command failures to the invoking channel.

    discord.py already isolates command errors from the event loop (a failing
    command never crashes the bot); this handler additionally reports the error
    back to the channel where the command was invoked.
    """

    @bot.event
    async def on_command_error(ctx, error):
        # someone typed an unknown !command — stay silent
        if isinstance(error, commands.CommandNotFound):
            return
        # command not allowed here (e.g. wrong channel) — stay silent
        if isinstance(error, commands.CheckFailure):
            return

        original = getattr(error, "original", error)
        logger.error("!%s failed", ctx.invoked_with, exc_info=original)
        try:
            await ctx.send(f"⚠️ `!{ctx.invoked_with}` failed: {original}")
        except Exception:
            logger.warning("Could not report the '%s' failure to the channel", ctx.invoked_with)

    return on_command_error
