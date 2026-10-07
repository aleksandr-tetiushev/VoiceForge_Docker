from discord.ext import commands
from discord import app_commands
import discord
from logger import log_error


class ErrorHandler(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self,ctx:commands.Context,error):
        if isinstance(error,commands.NotOwner):
            await ctx.reply("❌ Эта команда доступна только владельцу бота.")
        
        elif isinstance(error,commands.MissingPermissions):
            await ctx.reply("❌ У вас нет прав для использования этой команды.")
        
        elif isinstance(error, commands.CommandNotFound):
            return  # silently ignore command not found
        
        else:
            # Log unexpected errors
            await ctx.reply("Произошла ошибка!")
            log_error(message="Unexpected Error - Location : on_command_error",exc_info=error)
    
   
        
async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))
