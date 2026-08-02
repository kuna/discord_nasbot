import logging

logger = logging.getLogger("nasbot")


def setup_logging(level=logging.INFO):
    """Configure timestamped log output for the bot."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )


def register_command_logger(bot):
    """Log every command invocation and completion."""

    @bot.event
    async def on_command(ctx):
        logger.info(
            "!%s invoked by %s in #%s: %s",
            ctx.command,
            ctx.author,
            getattr(ctx.channel, "name", "?"),
            ctx.message.content,
        )

    @bot.event
    async def on_command_completion(ctx):
        logger.info("!%s completed", ctx.command)
