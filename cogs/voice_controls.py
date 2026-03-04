import discord
from discord.ext import commands
from discord import app_commands


# all voice control commands
class VoiceControls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # slash commands 
    @app_commands.command(name="rename", description="Rename your voice channel")
    async def rename(self, interaction: discord.Interaction, new_name: str):
        await interaction.response.send_message("Done!")
        


# Setup function to load the cog
async def setup(bot:commands.Bot):
    await bot.add_cog(VoiceControls(bot))