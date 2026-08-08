import asyncio

import discord
from discord.ext import commands

from botcmd.builtin import register_bot_command
from botcmd.cli import CliBot, run_cli
from botcmd.errors import register_error_handler
from botcmd.loader import load_plugins
from botcmd.logs import logger, register_command_logger, setup_logging
from botcmd.scheduler import CronScheduler
from config import load_config
from depend import Dependency


def build_bot(config, dep, cli=False):
    """Create the bot, load the plugins and return it with its scheduler."""
    # 인텐트 설정 (디스코드 개발자 포털에서 Message Content Intent가 켜져 있어야 합니다)
    intents = discord.Intents.default()
    intents.message_content = True

    # 봇 객체 생성 (접두사로 ! 사용). CLI 모드에서는 접속하지 않는 CliBot 사용
    bot_class = CliBot if cli else commands.Bot
    bot = bot_class(command_prefix="!", intents=intents)
    scheduler = CronScheduler(bot)

    # 플러그인 로드 및 커맨드 등록 (공용 의존성 주입)
    load_plugins(bot, config.DISABLED_PLUGINS, dep=dep, scheduler=scheduler)

    # 기본 제공 커맨드 (!bot): 커맨드/크론 목록
    register_bot_command(bot, scheduler)
    return bot, scheduler


def main_bot_entry(config, dep):
    """Normal mode: connect to discord and serve commands."""
    bot, scheduler = build_bot(config, dep)

    @bot.event
    async def on_ready():
        logger.info("Logged in as %s (ID: %s)", bot.user.name, bot.user.id)
        # 채널 조회가 가능한 시점에 시작 (재접속 시 중복 실행되지 않음)
        scheduler.start()

    # 커맨드 실행/완료 로깅, 실패 시 채널에 에러를 알림
    register_command_logger(bot)
    register_error_handler(bot)

    logger.info("Starting bot...")
    try:
        bot.run(config.DISCORD_API_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bye!")


def main_cli_entry(config, dep):
    """Test mode: read commands from stdin, no discord connection."""
    bot, scheduler = build_bot(config, dep, cli=True)

    async def run():
        try:
            await run_cli(bot, scheduler)
        finally:
            # the CLI exits, so release the resolver sessions it opened
            await dep.close()

    logger.info("Starting CLI test mode...")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Bye!")


def main():
    setup_logging()
    config = load_config()
    # 공용 의존성은 모드와 무관하므로 여기서 한 번만 생성
    dep = Dependency(config)
    if config.TEST_CLI_MODE:
        main_cli_entry(config, dep)
    else:
        main_bot_entry(config, dep)


if __name__ == "__main__":
    main()
