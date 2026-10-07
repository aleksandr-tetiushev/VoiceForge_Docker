from __future__ import annotations

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from discord import app_commands
from logger import log_error

load_dotenv()

TOKEN = os.getenv("VOICE_BOT_TOKEN")
if not TOKEN:
    raise ValueError("VOICE_BOT_TOKEN не найден в переменных окружения.")  # Защита от тихого сбоя, если токен не найден

os.makedirs("Logs", exist_ok=True)
log_path = os.path.join("Logs", "VOICE_BOT.log")
voice_bot_log_handler = logging.FileHandler(filename=log_path, encoding="utf-8", mode='w')


# Класс конфигурации бота
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all(), help_command=None)

    async def setup_hook(self):
        await self.load_extension("cogs.voice_manager")
        await self.load_extension("cogs.voice_interface")
        await self.load_extension("cogs.voice_controls")
        await self.load_extension("cogs.error_handling")
        await self.load_extension("cogs.sync_command")


bot = MyBot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):  # Обработка ошибок слэш-команд
    error_log = False

    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ У вас нет прав для использования этой команды."
    elif isinstance(error, app_commands.CommandOnCooldown):
        retry_after = round(error.retry_after)
        msg = f"⏳ Команда на перезарядке. Повторите через **{retry_after} с**."
    else:
        msg = "⚠️ Произошла непредвиденная ошибка."
        error_log = True

    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)

    if error_log:  # Логируем непредвиденные ошибки для отладки
        log_error(message="Unexpected Error - Location : on_app_command_error", exc_info=error)


if __name__ == "__main__":
    bot.run(TOKEN, log_handler=voice_bot_log_handler, log_level=logging.DEBUG)
