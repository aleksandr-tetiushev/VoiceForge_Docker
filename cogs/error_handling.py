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
    
    @commands.Cog.listener()
    async def on_app_command_error(self,interaction: discord.Interaction,error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.",ephemeral=True)

        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message("⏳ Command is on cooldown.",ephemeral=True)    
        else:
            await interaction.response.send_message("⚠️ An unexpected error occurred.",ephemeral=True)
            raise error
        
async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))