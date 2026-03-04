import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
import asyncio


load_dotenv()
TOKEN = os.getenv("VOICE_BOT_TOKEN")

if not TOKEN:
    raise ValueError("VOICE_BOT_TOKEN not found in environment variables.") # prevent silent error for token not found

os.makedirs("Logs", exist_ok=True)
log_path = os.path.join("Logs","VOICE_BOT.log")
voice_bot_log_handler = logging.FileHandler(filename=log_path,encoding="utf-8",mode='w')

# Bot config class
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        await self.load_extension("cogs.voice_controls")
        await self.load_extension("cogs.error_handling")
        await self.load_extension("cogs.sync_command")

bot = MyBot()



if __name__ == "__main__":
    bot.run(TOKEN,log_handler=voice_bot_log_handler,log_level=logging.DEBUG)
