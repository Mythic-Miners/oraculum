from discord.ext import commands
from discord import Intents
from os import listdir
import config


def main():
    intents = Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix="/", intents=intents)

    @bot.event
    async def setup_hook():
        for filename in listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                await bot.load_extension(f"cogs.{filename[:-3]}")

    @bot.event
    async def on_ready():
        print(f"🤖 Bot connected as {bot.user}")

    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()