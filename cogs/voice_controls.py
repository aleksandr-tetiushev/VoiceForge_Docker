import discord
from discord.ext import commands
from discord import app_commands
from cogs.voice_manager import VoiceManager
from typing import Optional
from config import * 
import asyncio
from . import databaseio as DB_SERVER_IO
from logger import log_error , log_info
import traceback
from . import database_channel_operations as DB_CHANNEL_IO

# all voice control commands
class VoiceControls(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    def is_guild(self,interaction: discord.Interaction) -> bool:
        return isinstance(interaction.guild, discord.Guild)
    
    def verify_ownership(self,interaction:discord.Interaction)-> bool: # verifying ownership 
        if not interaction.guild_id:
            return False
    
        if not self.user_in_voice_channel_check(interaction): # main command handles the user in voice but still to prevent crashes we check user's voice status
            return False

        channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

        if not isinstance(channel,DB_CHANNEL_IO.Channel):
            return False
        
        if interaction.user.id == channel.owner_id:
            return True
        
        return False

    def user_in_voice_channel_check(self,interaction:discord.Interaction) -> bool: # checks if user is in voice channel or not
        return bool(interaction.user.voice and interaction.user.voice.channel)
    
    def user_in_same_voice_channel(self, interaction: discord.Interaction, member: discord.Member) -> bool:
        return (member.voice and interaction.user.voice and member.voice.channel == interaction.user.voice.channel)
        
    async def send(self,interaction:discord.Interaction, msg:str , ephemeral:bool = True)-> None: # sends message or send followup if response is already sent
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(msg, ephemeral=ephemeral)

    async def send_embed(self,interaction:discord.Interaction, embed:discord.Embed , ephemeral:bool = True)-> None: # sends embed or send followup if response is already sent
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
 
    def get_voice_manager(self) -> Optional[VoiceManager]: # get VoiceManager cog
        return self.bot.get_cog("VoiceManager")
        
    # slash commands 
    @app_commands.command(name="rename", description="Rename your voice channel (max 32 characters)")
    @app_commands.checks.cooldown(1, RENAME_COOLDOWN)
    async def rename(self, interaction: discord.Interaction, name: str):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command works in servers only.",ephemeral=True)
            return
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="❌ You must be in a voice channel to use this command.")
            return
        name = name.strip()

        if not name:
            await self.send(interaction=interaction,msg="❌ Channel name cannot be empty.")
            return
        
        if len(name) > MAX_RENAME_CHARACTER_LIMIT:
            await self.send(interaction=interaction,msg=f"❌ Channel names cannot exceed {MAX_RENAME_CHARACTER_LIMIT} characters.")
            return

        channel = interaction.user.voice.channel 
        
        if not self.verify_ownership(interaction=interaction):
            await self.send(interaction=interaction,msg=f"❌ You are not the owner of this voice channel.")
            return
        
        if channel.name == name:
            await self.send(interaction=interaction,msg="❌ The channel already has this name.")
            return
        
        await channel.edit(name=name) #changing voice channel name
        await self.send(interaction=interaction,msg="✅ Voice channel renamed successfully.")
        return
    
    @app_commands.command(name="claim", description="claim current voice channel")
    @app_commands.checks.cooldown(1, CLAIM_TRANSFER_COOLDOWN)
    async def claim(self,interaction:discord.Interaction):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="❌ You must be in a voice channel to use this command.")
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
            await self.send(interaction=interaction,msg="❌ You are already the owner of this voice channel.")
            return 
        
        owner = interaction.guild.get_member(owner_id) if owner_id else None 
        
        if owner and owner in channel.members: # checking if owner is in channel or not
            await self.send(interaction=interaction,msg="❌ The current owner is still in the voice channel.")
            return
        
        if owner_id: # making sure if old owner is still in dataset it get removed if its not in voice channel to avoid 2 owner condition
            voice_manager.channel_to_owners.pop(channel.id,None)
            voice_manager.owners_to_channel.pop(owner_id, None)
        
        voice_manager.channel_to_owners[channel.id] = interaction.user.id
        voice_manager.owners_to_channel[interaction.user.id] = channel.id

        owner_overwrite = discord.PermissionOverwrite( # permission overwrites for voice channel owner 
            connect=True,
            read_message_history=True,
            speak=True,
            stream=True,
            use_voice_activation=True,
            view_channel=True
        )

        overwrites = {
            interaction.user : owner_overwrite,
            self.bot.user: discord.PermissionOverwrite( # bot's permissions 
                connect=True,
                view_channel=True,
                send_messages=True
            )
        }

        channel_edit = {
            'overwrites' : overwrites,
            'user_limit' : 0
        }
        
        if not channel.name == f"{interaction.user.display_name}'s VC": # renaming voice channel 
            channel_edit['name'] = f"{interaction.user.display_name}'s VC"

        await channel.edit(**channel_edit)

        await self.send(interaction=interaction,msg="✅ You are now the owner of this voice channel.")
        return
    
    @app_commands.command(name="limit", description="Change Limit for current Voice Channel between 1-99 or enter 0 to reset limit")
    @app_commands.checks.cooldown(1,LIMIT_CHANGE_COOLDOWN)
    async def limit(self,interaction:discord.Interaction,limit:int): 
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="❌ You must be in a voice channel to use this command.")
            return
        
        if not 0 <= limit <= 99: # making sure limit isnt more or less than limit by discord
            await self.send(interaction=interaction,msg="❌ Limit must be between 1–99, or 0 to remove the limit.")
            return
        
        voice_manager = self.get_voice_manager() # get VoiceManager cog

        channel = interaction.user.voice.channel 

        if not await self.verify_ownership(voice_manager,interaction):
            return
        
        if channel.user_limit == limit: # avoiding unnecessary api calls 
           await self.send(interaction, "❌ This channel already has that limit.")
           return
        
        if limit == 0: # vc limit reset
            await channel.edit(user_limit=0)
            await self.send(interaction=interaction,msg=f"✅ Voice channel limit removed.")
            return

        await channel.edit(user_limit=limit)
        await self.send(interaction=interaction,msg=f"✅ Voice channel limit set to `{limit}`.")
        return
        
    @app_commands.command(name="kick",description="Kick users from your voice channel (max 5 at a time)")
    @app_commands.checks.cooldown(1,KICK_MEMBER_COOLDOWN)
    async def kick(self,interaction:discord.Interaction,
                   member1: discord.Member,
                   member2: discord.Member|None=None,
                   member3: discord.Member|None=None,
                   member4: discord.Member|None=None,
                   member5: discord.Member|None=None):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="❌ You must be in a voice channel to use this command.")
            return
        
        members = [member1,member2,member3,member4,member5]

        voice_manager = self.get_voice_manager() # get VoiceManager cog

        if not await self.verify_ownership(voice_manager,interaction):
            return
        members = set(members) # making sure there are no repeated users
        kicked_members = []
        for member in members:

            if not member:
                continue
            
            if member.id == interaction.user.id:
                continue
            
            if not self.user_in_same_voice_channel(interaction, member):
                continue
            
            await member.move_to(None)

            kicked_members.append(member.mention)
            await asyncio.sleep(0.3)  # delay to avoid rate limit

        value = "\n".join(kicked_members) if kicked_members else "No users were kicked."

        embed = discord.Embed(
            title="Kicked Users",
            description="The following users were kicked from your voice channel.",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Kicked Members:",
            value=value,
            inline=False
        )

        embed.set_footer(
            text="Note: If a user you entered does not appear above, they were either not in your voice channel or could not be removed."
            )


        await self.send_embed(interaction=interaction,embed=embed)
        return
            
    @app_commands.command(name="lock",description="Lock current voice channel")
    @app_commands.checks.cooldown(1,LOCK_AND_UNLOCK_COOLDOWN)
    async def lock(self,interaction:discord.Interaction):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="❌ You must be in a voice channel to use this command.")
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
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="❌ You must be in a voice channel to use this command.")
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
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction,msg="❌ You must be in a voice channel to use this command.")
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
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return

        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction, "❌ You must be in a voice channel to use this command.")
            return
        
        members = {member1,member2,member3,member4,member5}
        members.discard(None)
        channel = interaction.user.voice.channel

        voice_manager = self.get_voice_manager() # get VoiceManager cog

        if not await self.verify_ownership(voice_manager,interaction):
            return
        
        guild = interaction.guild
        invite_link = f"https://discord.com/channels/{guild.id}/{channel.id}"

        invite_sent = []
        
        for member in members:
            if not member:
                continue

            if member.bot:
                continue

            try: 
                if member.id == interaction.user.id:
                    continue
                 
                if self.user_in_same_voice_channel(interaction, member):

                    continue
      
                await member.send(f"You were invited to join **{channel.name}**.\n"f"Click to join: {invite_link}") 
                invite_sent.append(member.mention)
            
            except discord.Forbidden:
                pass

        embed = discord.Embed(color=discord.Color.blurple())

        value = "\n".join(invite_sent) if invite_sent else "No users were invited."
        
        embed.add_field(
            name="✅ Invited:",
            value=value,
            inline=False
        )
        
        embed.set_footer(
            text="Note: If a user you entered does not appear above, the bot cannot invite them to this channel."
        )

        await self.send_embed(interaction=interaction, embed=embed)
        return

    @app_commands.command(name="hide",description="Hide current voice channel from everyone. Only trusted users can see.")
    @app_commands.checks.cooldown(1, HIDE_UNHIDE_COOLDOWN)
    async def hide(self, interaction: discord.Interaction):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return

        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction, msg="❌ You must be in a voice channel to use this command.")
            return

        voice_manager = self.get_voice_manager()

        if not await self.verify_ownership(voice_manager, interaction):
            return

        channel = interaction.user.voice.channel
        everyone = interaction.guild.default_role

        if not channel.permissions_for(everyone).view_channel:
            await self.send(interaction, "❌ This voice channel is already hidden.")
            return

        overwrite = channel.overwrites_for(everyone)
        overwrite.view_channel = False

        await channel.set_permissions(everyone, overwrite=overwrite)
        await self.send(interaction, "🚫 Voice channel hidden.")

    @app_commands.command(name="unhide",description="Make the current voice channel visible to everyone.")
    @app_commands.checks.cooldown(1, HIDE_UNHIDE_COOLDOWN)
    async def unhide(self, interaction: discord.Interaction):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return

        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction, msg="❌ You must be in a voice channel to use this command.")
            return

        voice_manager = self.get_voice_manager()

        if not await self.verify_ownership(voice_manager, interaction):
            return

        channel = interaction.user.voice.channel
        everyone = interaction.guild.default_role

        if channel.permissions_for(everyone).view_channel:
            await self.send(interaction, "❌ This voice channel is already visible.")
            return

        overwrite = channel.overwrites_for(everyone)
        overwrite.view_channel = None # restore default visibility according to server settings

        await channel.set_permissions(everyone, overwrite=overwrite)
        await self.send(interaction, "👁️ Voice channel is now visible.")
        return
    
    @app_commands.command(name="trust",description="Let selected users view and connect even if channel is locked or hidden (Max 5 at a time).")
    @app_commands.checks.cooldown(1, TRUST_UNTRUST_COOLDOWN)
    async def trust(self,interaction: discord.Interaction,
        member1: discord.Member,
        member2: discord.Member | None = None,
        member3: discord.Member | None = None,
        member4: discord.Member | None = None,
        member5: discord.Member | None = None
        ):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return

        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction, "❌ You must be in a voice channel to use this command.")
            return

        voice_manager = self.get_voice_manager()

        if not await self.verify_ownership(voice_manager, interaction):
            return

        channel = interaction.user.voice.channel
        overwrites = channel.overwrites

        members = {member1, member2, member3, member4, member5}
        members.discard(None)
        trusted = []

        for member in members:

            if member.bot:
                continue

            if member.id == interaction.user.id:
                continue
            
            overwrite = overwrites.get(member, discord.PermissionOverwrite())
            if (overwrite.connect is True and 
                overwrite.speak is True and 
                overwrite.stream is True and 
                overwrite.use_voice_activation is True and 
                overwrite.view_channel is True
                ): # preventing unnecessary overwrites
                 continue

            overwrite.view_channel = True
            overwrite.connect = True
            overwrite.stream = True
            overwrite.use_voice_activation = True
            overwrite.speak = True

            overwrites[member] = overwrite
            trusted.append(member.mention)
        
        view = "\n".join(trusted) if trusted else "No valid users were provided to trust."
        
        if trusted:
            await channel.edit(overwrites=overwrites)
            
        embed = discord.Embed(
            color=discord.Color.blurple()
            )

        embed.add_field(
            name="✅ Trusted :",
            value=view,
            inline=False
        )
        embed.set_footer(text="Note: If a user you entered does not appear above, the bot cannot Trust/Untrust them in this channel.")
        await self.send_embed(interaction=interaction,embed=embed)
        return
    
    @app_commands.command(name="trusted",description="Shows trusted users.")
    @app_commands.checks.cooldown(1,TRUSTED_BLOCKED_COOLDOWN)
    async def trusted(self,interaction:discord.Interaction):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction, "❌ You must be in a voice channel to use this command.")
            return

        voice_manager = self.get_voice_manager()

        if not await self.verify_ownership(voice_manager, interaction):
            return

        channel = interaction.user.voice.channel
        trusted_members = []

        for member , overwrite in channel.overwrites.items():
            if isinstance(member,discord.Member):
                if member.id == interaction.user.id: # its not possible for owner of voice channel to be added as trusted but still checking it doesnt add owner in trusted member list
                    continue
                
                if member.bot:
                    continue
                
                if (overwrite.connect is True and 
                    overwrite.speak is True and 
                    overwrite.stream is True and 
                    overwrite.use_voice_activation is True and 
                    overwrite.view_channel is True
                    ):
                    
                    trusted_members.append(member)
        
        value = "\n".join(member.mention for member in trusted_members) if trusted_members else "No trusted users found."

        embed = discord.Embed(
            title="Trusted Users",
            description="These are currently Trusted Users.",
            color=discord.Color.blurple()
            )

        embed.add_field(
            name="Currently Trusted :",
            value=value,
            inline=False
        )

        await self.send_embed(interaction=interaction,embed=embed)
        return
    
    @app_commands.command(name="untrust",description="Remove selected user from trusted user's list (Max 5 at a time).")
    @app_commands.checks.cooldown(1,TRUST_UNTRUST_COOLDOWN)
    async def untrust(self,interaction:discord.Interaction,
            member1: discord.Member,
            member2: discord.Member | None = None,
            member3: discord.Member | None = None,
            member4: discord.Member | None = None,
            member5: discord.Member | None = None
            ):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction, "❌ You must be in a voice channel to use this command.")
            return

        voice_manager = self.get_voice_manager()

        if not await self.verify_ownership(voice_manager, interaction):
            return

        channel = interaction.user.voice.channel
        overwrites = channel.overwrites

        members = {member1, member2, member3, member4, member5}
        members.discard(None)
        untrusted = []

        for member in members:

            if member.bot:
                continue

            if member.id == interaction.user.id:
                continue
            
            overwrite = overwrites.get(member, discord.PermissionOverwrite())
            if (overwrite.connect is not True and 
                    overwrite.speak is not True and 
                    overwrite.stream is not True and 
                    overwrite.use_voice_activation is not True and 
                    overwrite.view_channel is not True
                    ): # Skip users who are not currently trusted
                 continue
            
            # Reset permissions to inherit from role defaults
            overwrite.view_channel = None
            overwrite.connect = None
            overwrite.stream = None
            overwrite.use_voice_activation = None
            overwrite.speak = None

            overwrites[member] = overwrite
            untrusted.append(member.mention)

        view = "\n".join(untrusted) if untrusted else "No valid users were provided to untrust."

        if untrusted:
            await channel.edit(overwrites=overwrites)
        
        embed = discord.Embed(
            color=discord.Color.blurple()
            )

        embed.add_field(
            name="✅ Untrusted :",
            value=view,
            inline=False
        )
        
        embed.set_footer(text="Note: If a user you entered does not appear above, the bot cannot Trust/Untrust them in this channel.")
        await self.send_embed(interaction=interaction,embed=embed)
        return
    
    @app_commands.command(name="block",description="Kick and Block selected users from voice channel (Max 5 at a time).")
    @app_commands.checks.cooldown(1,BLOCK_UNBLOCK_COOLDOWN)
    async def block(self,interaction:discord.Interaction,
                    member1: discord.Member,
                    member2: discord.Member | None = None,
                    member3: discord.Member | None = None,
                    member4: discord.Member | None = None,
                    member5: discord.Member | None = None
                    ):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction, "❌ You must be in a voice channel to use this command.")
            return

        voice_manager = self.get_voice_manager()

        if not await self.verify_ownership(voice_manager, interaction):
            return

        channel = interaction.user.voice.channel
        overwrites = channel.overwrites

        members:set = {member1, member2, member3, member4, member5}
        members.discard(None)
        blocked = []

        for member in members:

            if member.bot:
                continue

            if member.id == interaction.user.id:
                continue

            overwrite = overwrites.get(member, discord.PermissionOverwrite())
            if overwrite.connect is False and overwrite.view_channel is False: # preventing unnecessary overwrites but setting it to false if any one of 2 required permissions is not False
                 continue
            
            overwrite.view_channel = False # will not show channel to blocked user
            overwrite.connect = False # will not let blocked user to connect
            overwrites[member] = overwrite

            if member in channel.members: # kicking user from voice channel 
                await member.move_to(None) 
            
            blocked.append(member.mention)

        view = "\n".join(blocked) if blocked else "No valid users were provided to block."
        
        await channel.edit(overwrites=overwrites)
        embed = discord.Embed(
            color=discord.Color.blurple()
            )

        embed.add_field(
            name="✅ Blocked :",
            value=view,
            inline=False
        )
        
        embed.set_footer(text="Note: If a user you entered does not appear above, the bot cannot block/unblock them in this channel.")
        await self.send_embed(interaction=interaction,embed=embed)
        return

    @app_commands.command(name="blocked",description="Shows blocked users.")
    @app_commands.checks.cooldown(1,TRUSTED_BLOCKED_COOLDOWN)
    async def blocked(self,interaction:discord.Interaction):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction, "❌ You must be in a voice channel to use this command.")
            return

        voice_manager = self.get_voice_manager()

        if not await self.verify_ownership(voice_manager, interaction):
            return

        channel = interaction.user.voice.channel
        blocked_members = []

        for member , overwrite in channel.overwrites.items():
            if isinstance(member,discord.Member):
                if member.id == interaction.user.id: # owner should never appear in blocked list
                    continue
                
                if member.bot:
                    continue
                
                if overwrite.view_channel is False and overwrite.connect is False:
                    blocked_members.append(member)
        
        value = "\n".join(member.mention for member in blocked_members) if blocked_members else "No blocked users found."

        embed = discord.Embed(
            title="Blocked Users",
            description="These users are currently blocked from the voice channel.",
            color=discord.Color.blurple()
            )

        embed.add_field(
            name="Currently Blocked :",
            value=value,
            inline=False
        )
        
        await self.send_embed(interaction=interaction,embed=embed)
        return
    
    @app_commands.command(name="unblock",description="Remove selected users from the blocked users list (Max 5 at a time).")
    @app_commands.checks.cooldown(1,BLOCK_UNBLOCK_COOLDOWN)
    async def unblock(self,interaction:discord.Interaction,
            member1: discord.Member,
            member2: discord.Member | None = None,
            member3: discord.Member | None = None,
            member4: discord.Member | None = None,
            member5: discord.Member | None = None
            ):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction, "❌ You must be in a voice channel to use this command.")
            return

        voice_manager = self.get_voice_manager()

        if not await self.verify_ownership(voice_manager, interaction):
            return

        channel = interaction.user.voice.channel
        overwrites = channel.overwrites

        members = {member1, member2, member3, member4, member5}
        members.discard(None)
        unblocked = []

        for member in members:

            if member.bot:
                continue

            if member.id == interaction.user.id:
                continue
            
            overwrite = overwrites.get(member, discord.PermissionOverwrite())
            if overwrite.connect is not False and overwrite.view_channel is not False: # preventing unnecessary overwrites but reseting if any one of 2 required permissions are False
                 continue

            # Reset permissions to inherit from role defaults
            overwrite.view_channel = None
            overwrite.connect = None

            overwrites[member] = overwrite
            unblocked.append(member.mention)

        view = "\n".join(unblocked) if unblocked else "No valid users were provided to unblock."
        
        await channel.edit(overwrites=overwrites)
        embed = discord.Embed(
            color=discord.Color.blurple()
            )

        embed.add_field(
            name="✅ Unblocked Users:",
            value=view,
            inline=False
        )
        
        embed.set_footer(text="Note: If a user you entered does not appear above, the bot cannot block/unblock them in this channel.")
        await self.send_embed(interaction=interaction,embed=embed)
        return
    
    @app_commands.command(name="transfer",description="Transfer your voice channel to another member in the channel.")
    @app_commands.checks.cooldown(1,CLAIM_TRANSFER_COOLDOWN)
    async def transfer(self,interaction:discord.Interaction,new_owner:discord.Member):
        if not self.is_guild(interaction):
            await interaction.response.send_message("❌ This command is works in server only",ephemeral=True)
            return
        if not self.user_in_voice_channel_check(interaction):
            await self.send(interaction=interaction, msg="❌ You must be in a voice channel to use this command.")
            return

        voice_manager = self.get_voice_manager()
        channel = interaction.user.voice.channel 
        
        if not await self.verify_ownership(voice_manager, interaction):
            return
        


        if new_owner.bot:
            await self.send(interaction,msg="❌ Invalid User.")
            return
        
        if interaction.user.id == new_owner.id:
            await self.send(interaction=interaction,msg="❌ You cannot transfer the voice channel to yourself.")
            return

        if new_owner not in channel.members: # checking if new_owner is in channel or not
            await self.send(interaction=interaction,msg="❌ Selected user is not in the voice channel.")
            return
        
        owner_id =  voice_manager.channel_to_owners.get(channel.id) # fetching owner id from ownership data

        if owner_id:
             # removing ownership data for current owner
            voice_manager.channel_to_owners.pop(channel.id,None)
            voice_manager.owners_to_channel.pop(owner_id, None)
        
        # adding ownership data for new owner
        voice_manager.channel_to_owners[channel.id] = new_owner.id
        voice_manager.owners_to_channel[new_owner.id] = channel.id

        owner_overwrite = discord.PermissionOverwrite( # permission overwrites for voice channel owner 
            connect=True,
            read_message_history=True,
            speak=True,
            stream=True,
            use_voice_activation=True,
            view_channel=True
        )

        overwrites = {
            new_owner : owner_overwrite,
            self.bot.user: discord.PermissionOverwrite( # bot's permissions 
                connect=True,
                view_channel=True,
                send_messages=True
            )
        }

        channel_edit = {
            'overwrites' : overwrites,
            'user_limit' : 0
        }
        
        if not channel.name == f"{new_owner.display_name}'s VC": # renaming voice channel 
            channel_edit['name'] = f"{new_owner.display_name}'s VC"

        await channel.edit(**channel_edit)
        
        await self.send(interaction=interaction,msg=f"✅ Transferred voice channel ownership to {new_owner.mention}.")
        return
    
    @app_commands.command(name="register",description="Registers voice channel and its category as creator channel and its category for temp channels.")
    async def register(self,interaction: discord.Interaction, channel: discord.VoiceChannel = None):
        try:
            if not self.is_guild(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ This command works inside server only.")
                return
            
            await interaction.response.defer()
            
            if not interaction.user.guild_permissions.administrator: # fallback if user is not admin of server
                await self.send(interaction=interaction,msg=f"❌ Permission Denied this command is avaliable to server administrators only.",ephemeral=False)
                return
            
            if not interaction.guild.me.guild_permissions.administrator: # fall back if bot dont have admin permission in server
                await self.send(interaction=interaction,msg=f"❌ I dont have administrator permission in this channel please grant my role administrator permissions to proceed with this command.",ephemeral=False)
                return
    
            if not channel or not isinstance(channel,discord.VoiceChannel):
                await self.send(interaction=interaction,msg=f"❌ Channel Invalid please pass a valid Voice Channel",ephemeral=False)
                return
            
            if not channel.category: # fallback on no category
                await self.send(interaction=interaction,msg=f"❌ This channel does not have any cateogry please pass channel with a valid category",ephemeral=False)
                return
    
            server_object , read_status = DB_SERVER_IO.server_read(interaction=interaction)
    
            if read_status: # fallback on already registered
                await self.send(interaction=interaction,msg=f"❌ This server already have registred creator channel please unregister that first using `/unregister`.")
                return
            
            write_status = DB_SERVER_IO.server_write(channel=channel)
    
            if not write_status:
                await self.send(interaction=interaction,msg=f"❌ Failed To register channel please retry.",ephemeral=False)
                return
            
            voice_manager = self.get_voice_manager()
            if not isinstance(voice_manager,VoiceManager):
                DB_SERVER_IO.server_delete(interaction=interaction) # remove server entry
                await self.send(interaction=interaction,msg=f"❌ Internal Server Error Please retry or contact developers.",ephemeral=False)
                return 

            voice_manager.creator_channels[channel.guild.id] = channel.id
            voice_manager.temp_channel_category[channel.guild.id] = channel.category.id # load current entry into voice_manager in-memory cache to start listening that channel also 
            await self.send(interaction=interaction,msg=f"✅ Channel registred successfully.",ephemeral=False)
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : register - filename : voice_controls.py - Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Internal Server Error Please retry or contact developers.")
            return 
        
    @app_commands.command(name="unregister",description="Unregisters the registred voice channel from server config.")
    async def unregister(self,interaction: discord.Interaction):
        try:
            if not self.is_guild(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ This command works inside server only.")
                return
            await interaction.response.defer()
            
            if not interaction.user.guild_permissions.administrator: # fallback if user is not admin of server
                await self.send(interaction=interaction,msg=f"❌ Permission Denied this command is avaliable to server administrators only.",ephemeral=False)
                return
            
            if not interaction.guild.me.guild_permissions.administrator: # fall back if bot dont have admin permission in server
                await self.send(interaction=interaction,msg=f"❌ I dont have administrator permission in this channel please grant my role administrator permissions to proceed with this command.",ephemeral=False)
                return
            
            server_object , read_status = DB_SERVER_IO.server_read(interaction=interaction)
    
            if not read_status: # fallback on no entry
                await self.send(interaction=interaction,msg=f"❌ This server don't have any registred creator channel please register first using `/register`.")
                return
            
            write_status = DB_SERVER_IO.server_delete(interaction=interaction)
    
            if not write_status:
                await self.send(interaction=interaction,msg=f"❌ Failed To delete channel please retry.",ephemeral=False)
                return
            
            voice_manager = self.get_voice_manager()
            if not isinstance(voice_manager,VoiceManager):
                await self.send(interaction=interaction,msg=f"❌ Internal Server Error Please retry or contact developers.",ephemeral=False)
                return 
            
            voice_manager.temp_channel_category.pop(interaction.guild_id,None)
            voice_manager.creator_channels.pop(interaction.guild_id,None) # remove from in-memory cache
            await self.send(interaction=interaction,msg=f"✅ Channel unregistred successfully {self.bot.user.mention} will still track existing temp voice channels.",ephemeral=False)
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : unregister - filename : voice_controls.py - Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Internal Server Error Please retry or contact developers.")
            return

# Setup function to load the cog
async def setup(bot:commands.Bot):
    await bot.add_cog(VoiceControls(bot))
