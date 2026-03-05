import discord
from discord.ext import commands
from discord import app_commands
from cogs.voice_manager import VoiceManager
from typing import Optional


# all voice control commands
class VoiceControls(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    # slash commands 
    @app_commands.command(name="rename", description="Rename your voice channel")
    async def rename(self, interaction: discord.Interaction, new_name: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You are not in a voice channel.",ephemeral=True)
            return
        
        channel = interaction.user.voice.channel 
        
        voice_manager:Optional[VoiceManager] = self.bot.get_cog("VoiceManager") # get VoiceManager cog

        if voice_manager is None:
            await interaction.response.send_message("Voice manager not available.", ephemeral=True)
            return
        
        if voice_manager.category_id != channel.category_id: # making sure command runs only in custom voice channels 
            await interaction.response.send_message("❌ This commands works in custom voice channels only.",ephemeral=True)
            return
        
        owner_id =  voice_manager.channel_to_owners.get(channel.id)

        if owner_id is None: # making sure channel have a owner or else indicating user to register first 
            await interaction.response.send_message("❌ This channel has no registered owner. Use `/claim` to take ownership.",ephemeral=True)
            return 
        
        if interaction.user.id != owner_id: # verify if user is voice owner 
            await interaction.response.send_message("❌ You are not Voice Channel Owner",ephemeral=True)
            return
        
        await channel.edit(name=new_name) #changing voice channel name
        await interaction.response.send_message("✅ Voice channel name changed successfully.",ephemeral=True)
        return


# Setup function to load the cog
async def setup(bot:commands.Bot):
    await bot.add_cog(VoiceControls(bot))