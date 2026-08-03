import discord
from discord.ext import commands

from botcmd.errors import register_error_handler
from botcmd.loader import load_plugins
from botcmd.logs import logger, register_command_logger, setup_logging
from botcmd.scheduler import CronScheduler
from config import load_config
from depend import Dependency


def main():
    setup_logging()
    config = load_config()

    # 인텐트 설정 (디스코드 개발자 포털에서 Message Content Intent가 켜져 있어야 합니다)
    intents = discord.Intents.default()
    intents.message_content = True

    # 봇 객체 생성 (접두사로 ! 사용)
    bot = commands.Bot(command_prefix="!", intents=intents)

    scheduler = CronScheduler(bot)

    @bot.event
    async def on_ready():
        logger.info("Logged in as %s (ID: %s)", bot.user.name, bot.user.id)
        # 채널 조회가 가능한 시점에 시작 (재접속 시 중복 실행되지 않음)
        scheduler.start()

    # 커맨드 실행/완료 로깅, 실패 시 채널에 에러를 알림
    register_command_logger(bot)
    register_error_handler(bot)

    # 플러그인 로드 및 커맨드 등록 (공용 의존성 주입)
    dep = Dependency(config)
    _ = load_plugins(bot, config.DISABLED_PLUGINS, dep=dep, scheduler=scheduler)

    logger.info("Starting bot...")
    try:
        bot.run(config.DISCORD_API_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bye!")


if __name__ == "__main__":
    main()
