import traceback

from discord.ext import commands


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
        traceback.print_exception(type(original), original, original.__traceback__)
        try:
            await ctx.send(f"⚠️ `!{ctx.invoked_with}` failed: {original}")
        except Exception:
            print(f"Could not report the '{ctx.invoked_with}' failure to the channel")

    return on_command_error
