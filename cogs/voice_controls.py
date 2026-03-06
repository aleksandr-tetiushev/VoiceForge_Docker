import discord
from discord.ext import commands
from discord import app_commands
from cogs.voice_manager import VoiceManager
from typing import Optional
from config import RENAME_COOLDOWN , CLAIM_COOLDOWN


# all voice control commands
class VoiceControls(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    # slash commands 
    @app_commands.command(name="rename", description="Rename your voice channel")
    @app_commands.checks.cooldown(1, RENAME_COOLDOWN,key=lambda i: i.user.voice.channel.id)
    async def rename(self, interaction: discord.Interaction, name: str):
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
        
        if channel.name == name:
            await interaction.response.send_message("❌ Channel already has this name.",ephemeral=True)
            return
        
        await channel.edit(name=name) #changing voice channel name
        await interaction.response.send_message("✅ Voice channel name changed successfully.",ephemeral=True)
        return
    
    @app_commands.command(name="claim", description="claim current voice channel")
    @app_commands.checks.cooldown(1, CLAIM_COOLDOWN,key=lambda i: i.user.voice.channel.id)
    async def claim(self,interaction:discord.Interaction):
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

        if owner_id == interaction.user.id: # making sure the command isnt run by owner itself
            await interaction.response.send_message("You are already Voice Channel's owner.",ephemeral=True)
            return 
        
        owner = interaction.guild.get_member(owner_id) if owner_id else None 
        
        if owner and owner in channel.members: # checking if owner is in channel or not
            await interaction.response.send_message("❌ Owner is already in voice channel.",ephemeral=True)
            return
        
        if owner_id: # making sure if old owner is still in dataset it get removed if its not in voice channel to avoid 2 owner condition
            voice_manager.channel_to_owners.pop(channel.id,None)
            voice_manager.owners_to_channel.pop(owner_id, None)
        
        voice_manager.channel_to_owners[channel.id] = interaction.user.id
        voice_manager.owners_to_channel[interaction.user.id] = channel.id
        
        await channel.edit(name=f"{interaction.user.display_name}'s VC")
        await interaction.response.send_message("✅ You are owner of voice channel.",ephemeral=True)
        return
    


# Setup function to load the cog
async def setup(bot:commands.Bot):
    await bot.add_cog(VoiceControls(bot))