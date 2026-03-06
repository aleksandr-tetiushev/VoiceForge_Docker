import discord
from discord.ext import commands
from discord import app_commands
from cogs.voice_manager import VoiceManager
from typing import Optional
from config import RENAME_COOLDOWN , CLAIM_COOLDOWN , LIMIT_CHANGE_COOLDOWN , KICK_MEMBER_COOLDOWN , MAX_RENAME_CHARACTER_LIMIT
import asyncio

# all voice control commands
class VoiceControls(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    async def verify_ownership(self,voice_manager:VoiceManager,interaction:discord.Interaction)-> bool: # verifying ownership 
        if not self.user_in_voice_channel_check(interaction): # main command handles the user in voice but still to prevent crashes we check user's voice status
            return False

        channel = interaction.user.voice.channel 
        
        if voice_manager is None:
            await self.send(interaction=interaction,msg="Voice manager not available.")
            return False
        
        if voice_manager.category_id != channel.category_id: # making sure command runs only in custom voice channels 
            await self.send(interaction=interaction,msg="❌ This command works in custom voice channels only.")
            return False
        
        owner_id =  voice_manager.channel_to_owners.get(channel.id)

        if owner_id is None: # making sure channel have a owner or else indicating user to register first 
            await self.send(interaction=interaction,msg="❌ This channel has no registered owner. Use `/claim` to take ownership.")
            return False
        
        if interaction.user.id != owner_id: # verify if user is voice owner 
            await self.send(interaction=interaction,msg="❌ You are not Voice Channel Owner")
            return False
        
        return True

    def user_in_voice_channel_check(self,interaction:discord.Interaction) -> bool: # checks if user is in voice channel or not
        return bool(interaction.user.voice and interaction.user.voice.channel)
    
    def user_in_same_voice_channel(self,interaction:discord.Interaction,member:discord.Member) -> bool: # make sure the member is in same voice channel
        return member.voice and member.voice.channel == interaction.user.voice.channel
        
    async def send(self,interaction:discord.Interaction, msg , ephemeral:bool = True)-> None: # sends message or send followup if response is already sent
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(msg, ephemeral=ephemeral)
 
    def get_voice_manager(self) -> Optional[VoiceManager]: # get VoiceManager cog
        return self.bot.get_cog("VoiceManager")
        
    # slash commands 
    @app_commands.command(name="rename", description="Rename your voice channel (max 32 characters)")
    @app_commands.checks.cooldown(1, RENAME_COOLDOWN)
    async def rename(self, interaction: discord.Interaction, name: str):
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="You are not in a voice channel.")
            return
        name = name.strip()

        if not name:
            await self.send(interaction=interaction,msg="❌ Channel name cannot be empty.")
            return
        
        if len(name) > MAX_RENAME_CHARACTER_LIMIT:
            await self.send(interaction=interaction,msg="❌ Channel name cannot be longer than 32 characters.")
            return

        channel = interaction.user.voice.channel 
        
        voice_manager = self.get_voice_manager() # get VoiceManager cog

        if not await self.verify_ownership(voice_manager,interaction):
            return
        
        if channel.name == name:
            await self.send(interaction=interaction,msg="❌ Channel already has this name.")
            return
        
        await channel.edit(name=name) #changing voice channel name
        await self.send(interaction=interaction,msg="✅ Voice channel name changed successfully.")
        return
    
    @app_commands.command(name="claim", description="claim current voice channel")
    @app_commands.checks.cooldown(1, CLAIM_COOLDOWN)
    async def claim(self,interaction:discord.Interaction):
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="You are not in a voice channel.")
            return
        
        channel = interaction.user.voice.channel 
        
        voice_manager = self.get_voice_manager() # get VoiceManager cog

        if voice_manager is None:
            await self.send(interaction=interaction,msg="Voice manager not available.")
            return
        
        if voice_manager.category_id != channel.category_id: # making sure command runs only in custom voice channels 
            await self.send(interaction=interaction,msg="❌ This command works in custom voice channels only.")
            return

        owner_id =  voice_manager.channel_to_owners.get(channel.id)

        if owner_id == interaction.user.id: # making sure the command isnt run by owner itself
            await self.send(interaction=interaction,msg="You are already Voice Channel's owner.")
            return 
        
        owner = interaction.guild.get_member(owner_id) if owner_id else None 
        
        if owner and owner in channel.members: # checking if owner is in channel or not
            await self.send(interaction=interaction,msg="❌ Owner is already in voice channel.")
            return
        
        if owner_id: # making sure if old owner is still in dataset it get removed if its not in voice channel to avoid 2 owner condition
            voice_manager.channel_to_owners.pop(channel.id,None)
            voice_manager.owners_to_channel.pop(owner_id, None)
        
        voice_manager.channel_to_owners[channel.id] = interaction.user.id
        voice_manager.owners_to_channel[interaction.user.id] = channel.id
        
        await channel.edit(name=f"{interaction.user.display_name}'s VC")
        await self.send(interaction=interaction,msg="✅ You are owner of voice channel.")
        return
    
    @app_commands.command(name="limit", description="Change Limit for current Voice Channel between 1-99 or enter 0 to reset limit")
    @app_commands.checks.cooldown(1,LIMIT_CHANGE_COOLDOWN)
    async def limit(self,interaction:discord.Interaction,limit:int): 
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="You are not in a voice channel.")
            return
        
        if not 0 <= limit <= 99: # making sure limit isnt more or less than limit by discord
            await self.send(interaction=interaction,msg="Invalid value limit should be between 1-99 or enter 0 to reset limit.")
            return
        
        voice_manager = self.get_voice_manager() # get VoiceManager cog

        channel = interaction.user.voice.channel 

        if not await self.verify_ownership(voice_manager,interaction):
            return
        
        if channel.user_limit == limit: # avoiding unnecessary api calls 
           await self.send(interaction, "❌ Channel already has this limit.")
           return
        
        if limit == 0: # vc limit reset
            await channel.edit(user_limit=0)
            await self.send(interaction=interaction,msg=f"✅ Voice channel limit reset (unlimited).")
            return

        await channel.edit(user_limit=limit)
        await self.send(interaction=interaction,msg=f"✅ Voice channel limit set to `{limit}`.")
        return
        
    @app_commands.command(name="kick",description="Kick user from voice channel (max 5 at a time)")
    @app_commands.checks.cooldown(1,KICK_MEMBER_COOLDOWN)
    async def kick(self,interaction:discord.Interaction,
                   member1: discord.Member,
                   member2: discord.Member|None=None,
                   member3: discord.Member|None=None,
                   member4: discord.Member|None=None,
                   member5: discord.Member|None=None):
        
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="You are not in a voice channel.")
            return
        
        members = [member1,member2,member3,member4,member5]

        voice_manager = self.get_voice_manager() # get VoiceManager cog

        if not await self.verify_ownership(voice_manager,interaction):
            return
        members = set(members) # making sure there are no repeated users
        for member in members:

            if not member:
                continue
            
            if member.id == interaction.user.id:
                await self.send(interaction=interaction,msg="You cannot kick yourself from the voice channel.")
                continue
            
            if not self.user_in_same_voice_channel(interaction, member):
                await self.send(interaction=interaction,msg=f"{member.mention} is not in your voice channel.")
                continue
            
            await member.move_to(None)
            
            await self.send(interaction=interaction,msg=f"{member.mention} kicked from voice channel.")

            await asyncio.sleep(0.3)  # delay to avoid rate limit

        return
            



# Setup function to load the cog
async def setup(bot:commands.Bot):
    await bot.add_cog(VoiceControls(bot))