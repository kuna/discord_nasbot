import discord
from discord.ext import commands

from botcmd.errors import register_error_handler
from botcmd.loader import load_plugins
from config import load_config
from depend import Dependency


def main():
    config = load_config()

    # 인텐트 설정 (디스코드 개발자 포털에서 Message Content Intent가 켜져 있어야 합니다)
    intents = discord.Intents.default()
    intents.message_content = True

    # 봇 객체 생성 (접두사로 ! 사용)
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
        print("------")

    # 커맨드 실패 시 채널에 에러를 알림
    register_error_handler(bot)

    # 플러그인 로드 및 커맨드 등록 (공용 의존성 주입)
    dep = Dependency(config)
    loaded = load_plugins(bot, config.DISABLED_PLUGINS, dep=dep)
    print(f"Loaded plugins ({len(loaded)}): {', '.join(loaded) or 'none'}")

    print("Starting bot...")
    try:
        bot.run(config.DISCORD_API_TOKEN)
    except KeyboardInterrupt:
        print("Bye!")


if __name__ == "__main__":
    main()
