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

    