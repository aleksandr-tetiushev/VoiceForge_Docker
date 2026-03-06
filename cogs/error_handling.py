from discord.ext import commands
from discord import app_commands
import discord


class ErrorHandler(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self,ctx:commands.Context,error):
        if isinstance(error,commands.NotOwner):
            await ctx.reply("❌ This command is only available to the bot owner.")
        
        elif isinstance(error,commands.MissingPermissions):
            await ctx.reply("❌ You don’t have permission to use this command.")
        
        elif isinstance(error, commands.CommandNotFound):
            return  # silently ignore command not found
        
        else:
            # Log unexpected errors
            await ctx.reply("Some Error Occured!")
            raise error
    
   
        
async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))