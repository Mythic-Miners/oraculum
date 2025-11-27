from discord.ext import commands
from discord import Intents
from os import listdir
import importlib.util
import sys


def load_config(config_path):
    """Load configuration from a specified file path"""
    spec = importlib.util.spec_from_file_location("config", config_path)
    config_module = importlib.util.module_from_spec(spec)
    sys.modules['config'] = config_module
    spec.loader.exec_module(config_module)
    return config_module


def main(config_path="config.py"):
    # Load configuration
    config = load_config(config_path)
    
    intents = Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix=config.BOT_PREFIX, intents=intents)

    @bot.event
    async def setup_hook():
        for filename in listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                await bot.load_extension(f"cogs.{filename[:-3]}")

    @bot.event
    async def on_ready():
        print(f"🤖 Bot connected as {bot.user}")
        print(f"📁 Configuration loaded from: {config_path}")

    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    # Check if config file was passed as argument
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "config.py"
    
    print(f"🔧 Loading configuration from: {config_file}")
    main(config_file)