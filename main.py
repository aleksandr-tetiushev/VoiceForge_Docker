from __future__ import annotations
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from discord import app_commands 

load_dotenv()
TOKEN = os.getenv("VOICE_BOT_TOKEN")
CATEGORY_ID = os.getenv("CUSTOM_VOICE_CATEGORY_ID")
CREATE_CHANNEL_ID = os.getenv("CUSTOM_VOICE_CHANNEL_ID")

if not TOKEN:
    raise ValueError("VOICE_BOT_TOKEN not found in environment variables.") # prevent silent error for token not found

os.makedirs("Logs", exist_ok=True)
log_path = os.path.join("Logs","VOICE_BOT.log")
voice_bot_log_handler = logging.FileHandler(filename=log_path,encoding="utf-8",mode='w')

# Bot config class
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.category_id: int = int(CATEGORY_ID)
        self.create_channel_id: int = int(CREATE_CHANNEL_ID)

    async def setup_hook(self):
        await self.load_extension("cogs.voice_manager")
        await self.load_extension("cogs.voice_controls")
        await self.load_extension("cogs.error_handling")
        await self.load_extension("cogs.sync_command")

bot = MyBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):

    msg = "⚠️ An unexpected error occurred."

    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ You don't have permission to use this command."

    elif isinstance(error, app_commands.CommandOnCooldown):
        retry_after = round(error.retry_after)
        msg = f"⏳ Command on cooldown. Try again in **{retry_after}s**."

    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


if __name__ == "__main__":
    bot.run(TOKEN,log_handler=voice_bot_log_handler,log_level=logging.DEBUG)
