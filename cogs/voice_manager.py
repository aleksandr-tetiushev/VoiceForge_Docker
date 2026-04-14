from __future__ import annotations
import discord
from discord.ext import commands , tasks
from typing import Optional
import asyncio
from cogs.voice_interface import build_panel_embed, VoicePanelView
from . import database_channel_operations as channel_db
from . import database_server_operations as server_db
from logger import log_error , log_info
import traceback

class VoiceManager(commands.Cog):
    def __init__(self,bot:commands.Bot) -> None:
        self.bot:commands.Bot = bot
        # server_id -> creator_channel_id
        self.creator_channels:dict[int,int] = {}
        # server_id -> category_id
        self.temp_channel_category:dict[int,int] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        # initialize databases on every ready to keep database avaliable if deleted
        channel_db.init_database()
        server_db.init_database()
        # clean all temp channels and its data stored in DB
        await self.clean_voice_channels()

    async def clean_voice_channels(self):
        channels = channel_db.read_all_channels()
    
        already_fetched_guild: dict[int, discord.Guild] = {}
    
        for channel in channels:
            try:
                server_id = channel.server_id
    
                guild = (
                    already_fetched_guild.get(server_id)
                    or self.bot.get_guild(server_id)
                )
    
                if not guild: # fetch only if we dont have guild in cache
                    guild = await self.bot.fetch_guild(server_id)
    
                if not isinstance(guild, discord.Guild):
                    continue
                
                already_fetched_guild[server_id] = guild
    
                
                guild_channel = (
                    guild.get_channel(channel.channel_id)
                    or await self.bot.fetch_channel(channel.channel_id)
                )
    
                if not isinstance(guild_channel, discord.VoiceChannel):
                    continue
                
                if len(guild_channel.members) == 0:
                    await guild_channel.delete(reason="Temp Channel Empty")
                    channel_db.channel_delete(server_id=server_id,channel_id=guild_channel.id)
    
            except discord.NotFound:
                # Channel doesn't exist → clean DB
                channel_db.channel_delete(server_id=channel.server_id,channel_id=channel.channel_id)
                continue
            
            except Exception as e:
                exception_traceback = traceback.format_exc()
                error_name = type(e).__name__
                log_error(message=f"Location : clean_voice_channels - file : voice_manager.py : Error Name - {error_name}",exc_info=exception_traceback)
                continue

    async def get_creator_channel(self, server: server_db.Server) -> discord.VoiceChannel | None:
        creator_channel_id = server.creator_channel_id
    
        creator_channel = self.bot.get_channel(creator_channel_id)
    
        if not creator_channel:
            try:
                creator_channel = await self.bot.fetch_channel(creator_channel_id)
            except discord.NotFound:
                return None
    
        return creator_channel if isinstance(creator_channel, discord.VoiceChannel) else None
    
    async def create_temp_voice_channel(self, member: discord.Member) -> bool:
        try:
            guild: discord.Guild = member.guild

            category_id = self.temp_channel_category.get(guild.id)
            if not category_id:
                return False

            category = guild.get_channel(category_id)

            if not category:
                try:
                    category = await self.bot.fetch_channel(category_id)
                except discord.NotFound:
                    return False

            if not isinstance(category, discord.CategoryChannel):
                return False

            overwrites = {
                member: discord.PermissionOverwrite(
                    connect=True,
                    read_message_history=True,
                    speak=True,
                    stream=True,
                    use_voice_activation=True,
                    view_channel=True,
                    send_messages=True
                ),
                self.bot.user: discord.PermissionOverwrite(
                    read_message_history=True,
                    send_messages=True,
                    connect=True,
                    view_channel=True,
                    embed_links=True
                )
            }

            new_channel: discord.VoiceChannel = await guild.create_voice_channel(
                name=f"{member.display_name}'s VC",
                category=category,
                user_limit=4,
                overwrites=overwrites
            )

            channel_object = channel_db.Channel(
                server_id=guild.id,
                owner_id=member.id,
                category=category.id,
                channel_id=new_channel.id
            )

            write_status = channel_db.channel_write(channel=channel_object)

            if not write_status:
                log_error(message="Location : create_temp_voice_channel - DB write failed")
                await new_channel.delete(reason="Internal Server error")
                return False

            try:
                await new_channel.send(
                    content=f"Welcome {member.mention} ❤️\n\n",
                    embed=build_panel_embed(),
                    view=VoicePanelView()
                )
            except discord.Forbidden: # DM Closed
                pass

            try:
                await member.move_to(channel=new_channel)
            except discord.HTTPException:
                log_error(message="Location : create_temp_voice_channel - move_to failed")

            return True

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(
                message=f"Location : create_temp_voice_channel - file : voice_manager.py : Error Name - {error_name}",
                exc_info=exception_traceback
            )
            return False
        
    def get_all_server_data(self):
       servers: list[server_db.Server] = server_db.read_all_servers()
    
       for server in servers:
           try:
               if not server.server_id:
                   continue
                
               if server.creator_channel_id:
                   self.creator_channels[server.server_id] = server.creator_channel_id
    
               if server.category_id:
                   self.temp_channel_category[server.server_id] = server.category_id
    
           except Exception as e:
               exception_traceback = traceback.format_exc()
               error_name = type(e).__name__
               log_error(
                   message=f"Location : get_all_server_data - file : voice_manager.py : Error Name - {error_name}",
                   exc_info=exception_traceback
               )
               continue