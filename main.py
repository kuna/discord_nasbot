import os
import discord
from discord.ext import commands

from config import load_config

def main():
    # Load config
    config = load_config()
    print(f'Config loaded: {config}')

    # 인텐트 설정 (디스코드 개발자 포털에서 Message Content Intent가 켜져 있어야 합니다)
    intents = discord.Intents.default()
    intents.message_content = True

    # 봇 객체 생성 (접두사로 ! 사용)
    bot = commands.Bot(command_prefix='!', intents=intents)

    # 봇이 준비되었을 때 실행되는 이벤트
    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
        print('------')

    # "!ping" 명령어 정의
    @bot.command()
    async def ping(ctx):
        """봇의 응답 속도를 확인합니다."""
        await ctx.send(f'🏓 Pong! {round(bot.latency * 1000)}ms')

    # Start bot
    print('Starting bot...')
    try:
        bot.run(config.DISCORD_API_TOKEN)
    except KeyboardInterrupt:
        print('Bye!')

if __name__ == '__main__':
    main()
