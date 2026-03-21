from __future__ import annotations
import discord
from discord.ext import commands , tasks
from typing import Optional
import asyncio
from cogs.voice_interface import build_panel_embed, VoicePanelView

class VoiceManager(commands.Cog):
    def __init__(self,bot:commands.Bot) -> None:
        self.bot: commands.Bot = bot
        
        # channel_id -> owner_id
        self.channel_to_owners : dict[int, int] = {}
        # owner_id -> channel_id
        self.owners_to_channel : dict[int,int] = {}

        # convert env IDs to int once
        self.category_id:int = int(bot.category_id)
        self.create_channel_id:int = int(bot.create_channel_id)
        self.guild_id :int= int(bot.server_id)

        self.cleanup_empty_channels.start() # start cleanup
        
    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.get_creator_channel() # trigger 
        if not channel or not channel.members:
            return
        
        for member in channel.members:
            await self.create_temp_channel(member)
        
        return

    @tasks.loop(minutes=5)  # Run every 5 minutes
    async def cleanup_empty_channels(self): # 

        category = self.bot.get_channel(self.category_id)

        if category is None or not isinstance(category, discord.CategoryChannel):
            return

        for channel in category.channels:
    
            if isinstance(channel, discord.VoiceChannel):
                # Delete if empty and prevent bot from deleting creator channel
                if len(channel.members) == 0 and not channel.id == self.create_channel_id:
                    owner_id = self.channel_to_owners.pop(channel.id, None)
                    if owner_id:
                        self.owners_to_channel.pop(owner_id, None)
            
                    try:
                        await channel.delete()
                    except discord.Forbidden:
                        pass
    
    @cleanup_empty_channels.before_loop
    async def before_cleanup(self):
        """Wait for bot to be ready before running cleanup"""
        await self.bot.wait_until_ready()


    async def create_temp_channel(self,member:discord.Member):
        if member.bot:
            return
        guild: discord.Guild = member.guild
        category = guild.get_channel(self.category_id)

        if category is None or not isinstance(category, discord.CategoryChannel):
            return
        
        member_owned_channel = self.owners_to_channel.get(member.id)

        if member_owned_channel is not None: # Move user into their existing owned channel rather than creating a new one
            existing_channel = guild.get_channel(member_owned_channel)
            if isinstance(existing_channel,discord.VoiceChannel):
                return await member.move_to(existing_channel) 
            else:
                # Clean up stale data
                self.owners_to_channel.pop(member.id, None)
                self.channel_to_owners.pop(member_owned_channel, None)

        overwrites = {
            member: discord.PermissionOverwrite(
                connect=True,
                read_message_history=True,
                speak=True,
                stream=True,
                use_voice_activation=True,
                view_channel=True
            ),
            
            self.bot.user: discord.PermissionOverwrite(
                read_message_history=True,
                send_messages=True,
                connect=True,
                view_channel=True
            )
        }
        
        new_channel: discord.VoiceChannel = await guild.create_voice_channel(
            name=f"{member.display_name}'s Vc",
            category=category,
            user_limit=4,
            overwrites=overwrites
        )

        # Store ownership
        self.channel_to_owners[new_channel.id] = member.id
        self.owners_to_channel[member.id] = new_channel.id

        try:
            await new_channel.send(content=f"Welcome {member.mention} ❤️\n\n",embed=build_panel_embed(), view=VoicePanelView())
        except discord.Forbidden: # DM Closed
            pass

        await member.move_to(new_channel)

    def get_creator_channel(self) -> discord.VoiceChannel | None:
        guild = self.bot.get_guild(self.guild_id)

        if guild is None:
            return None

        creator_channel = guild.get_channel(self.create_channel_id)

        if isinstance(creator_channel, discord.VoiceChannel):
            return creator_channel

        return None
    


    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None: # Update data in case of manual deletion by server mods or other bots
        if isinstance(channel, discord.VoiceChannel):
            owner_id = self.channel_to_owners.pop(channel.id, None)
            if owner_id:
                self.owners_to_channel.pop(owner_id, None)

    @commands.Cog.listener()
    async def on_voice_state_update(self,member: discord.Member,before: discord.VoiceState,after: discord.VoiceState) -> None:
        if member.bot: # Ignore if a bot moves
          return
        
        if before.channel == after.channel: # Prevent processing if the channel didn't actually change 
            return
        
        # Check if the joined channel is the create VC channel
        if after.channel and after.channel.id == self.create_channel_id:
            guild: discord.Guild = member.guild

            category = guild.get_channel(self.category_id)
            
            if category is None or not isinstance(category, discord.CategoryChannel):
                return
                       
            member_owned_channel = self.owners_to_channel.get(member.id)
            
            if member_owned_channel is not None: # Move user into their existing owned channel rather than creating a new one
                existing_channel = guild.get_channel(member_owned_channel)
                if isinstance(existing_channel,discord.VoiceChannel):
                    return await member.move_to(existing_channel) 
                else:
                    # Clean up stale data
                    self.owners_to_channel.pop(member.id, None)
                    self.channel_to_owners.pop(member_owned_channel, None)
             
            overwrites = {
                member: discord.PermissionOverwrite(
                    connect=True,
                    read_message_history=True,
                    speak=True,
                    stream=True,
                    use_voice_activation=True,
                    view_channel=True
                ),
                
                self.bot.user: discord.PermissionOverwrite(
                    read_message_history=True,
                    send_messages=True,
                    connect=True,
                    view_channel=True
                )
            }

            new_channel: discord.VoiceChannel = await guild.create_voice_channel(
                name=f"{member.display_name}'s VC",
                category=category,
                user_limit=4,
                overwrites=overwrites
            )

            # Store ownership
            self.channel_to_owners[new_channel.id] = member.id
            self.owners_to_channel[member.id] = new_channel.id

            try:
                await new_channel.send(content=f"Welcome {member.mention} ❤️\n\n",embed=build_panel_embed(), view=VoicePanelView())
            except discord.Forbidden: # DM Closed
                pass

            await member.move_to(new_channel)

        # Delete empty channels and remove ownership
        if before.channel:
            if before.channel.id in self.channel_to_owners:
                if len(before.channel.members) == 0:
                    owner_id = self.channel_to_owners.pop(before.channel.id,None)
                    if owner_id is not None:
                        self.owners_to_channel.pop(owner_id,None)

                    await before.channel.delete()

# Setup function to load cog into the main module 
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceManager(bot))
