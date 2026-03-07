import discord
from discord.ext import commands
from discord import app_commands
from cogs.voice_manager import VoiceManager
from typing import Optional
from config import * 
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
        
    async def send(self,interaction:discord.Interaction, msg:str , ephemeral:bool = True)-> None: # sends message or send followup if response is already sent
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
            
    @app_commands.command(name="lock",description="Lock current voice channel")
    @app_commands.checks.cooldown(1,LOCK_AND_UNLOCK_COOLDOWN)
    async def lock(self,interaction:discord.Interaction):
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="You are not in a voice channel.")
            return
        
        voice_manager = self.get_voice_manager() # get VoiceManager cog

        if not await self.verify_ownership(voice_manager,interaction):
            return

        channel = interaction.user.voice.channel 
        everyone = interaction.guild.default_role
        overwrite = channel.overwrites_for(everyone)

        if overwrite.connect is False: # verifying if voice channel isnt locked already to avoid unnecessary api calls
            await self.send(interaction, "Voice channel is already locked.")
            return        
        
        overwrite.connect = False
        await channel.set_permissions(everyone, overwrite=overwrite)
        await self.send(interaction, "🔒 Voice channel locked.")
        return
    
    @app_commands.command(name="unlock",description="Unlock current voice channel")
    @app_commands.checks.cooldown(1,LOCK_AND_UNLOCK_COOLDOWN)
    async def unlock(self,interaction:discord.Interaction):
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="You are not in a voice channel.")
            return
        
        voice_manager = self.get_voice_manager() # get VoiceManager cog

        if not await self.verify_ownership(voice_manager,interaction):
            return

        channel = interaction.user.voice.channel 
        everyone = interaction.guild.default_role
        overwrite = channel.overwrites_for(everyone)

        if overwrite.connect is True: # verifying if voice channel isnt unlocked already to avoid unnecessary api calls
            await self.send(interaction, "Voice channel is already unlocked.")
            return        
        
        overwrite.connect = True
        await channel.set_permissions(everyone, overwrite=overwrite)
        await self.send(interaction, "🔓 Voice channel unlocked.")
        return
    
    @app_commands.command(name="delete",description="Delete current voice channel")
    @app_commands.checks.cooldown(1,DELETE_COOLDOWN) # cooldown in this command prevents user from using same command for 2 different voice channel withing small interval and prevents rate limitng
    async def delete(self,interaction:discord.Interaction):
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="You are not in a voice channel.")
            return
        
        channel = interaction.user.voice.channel 
        
        voice_manager = self.get_voice_manager() # get VoiceManager cog

        if not await self.verify_ownership(voice_manager,interaction):
            return
        
        owner_id =  voice_manager.channel_to_owners.get(channel.id)

        if not owner_id:
            return
        
        voice_manager.owners_to_channel.pop(owner_id,None)
        voice_manager.channel_to_owners.pop(interaction.user.voice.channel.id,None)
        await self.send(interaction=interaction,msg="Voice channel deleted.")
        await channel.delete()
        return
    
    @app_commands.command(name="invite",description="Send invite to user for your voice channel (max 5 invites at a time)")
    @app_commands.checks.cooldown(1,INVITE_COOLDOWN)
    async def invite(self, interaction: discord.Interaction,
                   member1: discord.Member,
                   member2: discord.Member|None=None,
                   member3: discord.Member|None=None,
                   member4: discord.Member|None=None,
                   member5: discord.Member|None=None):

        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction, "You are not in a voice channel.")
            return
        
        members = [member1,member2,member3,member4,member5]
        channel = interaction.user.voice.channel

        voice_manager = self.get_voice_manager() # get VoiceManager cog

        if not await self.verify_ownership(voice_manager,interaction):
            return
        
        guild = interaction.guild
        invite_link = f"https://discord.com/channels/{guild.id}/{channel.id}"
        members = set(members) # making sure there are no repeated users
        
        for member in members:
            if not member:
                continue
            try: 
                if member.id == interaction.user.id:
                    await self.send(interaction=interaction,msg="You cannot invite yourself to the voice channel.")
                    continue
                 
                if self.user_in_same_voice_channel(interaction, member):
                    await self.send(interaction=interaction,msg=f"{member.mention} is already in your voice channel.")
                    continue
      
                await member.send(f"You were invited to join **{channel.name}**.\n"f"Click to join: {invite_link}")
                await self.send(interaction, f"📩 Invite sent to {member.mention}")
            
            except discord.Forbidden:
                await self.send(interaction,f"❌ Could not DM {member.mention}. Their DMs are closed.")

    @app_commands.command(name="hide",description="Hide current voice channel from everyone. Only trusted users can see.")
    @app_commands.checks.cooldown(1, HIDE_COOLDOWN)
    async def hide(self, interaction: discord.Interaction):

        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction, msg="You are not in a voice channel.")
            return

        voice_manager = self.get_voice_manager()

        if not await self.verify_ownership(voice_manager, interaction):
            return

        channel = interaction.user.voice.channel
        everyone = interaction.guild.default_role

        if not channel.permissions_for(everyone).view_channel:
            await self.send(interaction, "Voice channel is already hidden.")
            return

        overwrite = channel.overwrites_for(everyone)
        overwrite.view_channel = False

        await channel.set_permissions(everyone, overwrite=overwrite)
        await self.send(interaction, "🚫 Voice channel hidden.")

    @app_commands.command(name="unhide",description="Make the current voice channel visible to everyone.")
    @app_commands.checks.cooldown(1, HIDE_COOLDOWN)
    async def unhide(self, interaction: discord.Interaction):

        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction, msg="You are not in a voice channel.")
            return

        voice_manager = self.get_voice_manager()

        if not await self.verify_ownership(voice_manager, interaction):
            return

        channel = interaction.user.voice.channel
        everyone = interaction.guild.default_role

        if channel.permissions_for(everyone).view_channel:
            await self.send(interaction, "Voice channel is already visible.")
            return

        overwrite = channel.overwrites_for(everyone)
        overwrite.view_channel = None # restore default visibility according to server settings

        await channel.set_permissions(everyone, overwrite=overwrite)
        await self.send(interaction, "👁️ Voice channel is now visible.")
        return

# Setup function to load the cog
async def setup(bot:commands.Bot):
    await bot.add_cog(VoiceControls(bot))