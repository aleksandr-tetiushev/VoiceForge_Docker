from __future__ import annotations
import discord
from discord.ext import commands

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

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None: # update data incase of manual delete from server Mods or other bots
        if isinstance(channel, discord.VoiceChannel):
            owner_id = self.channel_to_owners.pop(channel.id, None)
            if owner_id:
                self.owners_to_channel.pop(owner_id, None)

    @commands.Cog.listener()
    async def on_voice_state_update(self,member: discord.Member,before: discord.VoiceState,after: discord.VoiceState) -> None:
        if member.bot: # Ignore If Bot Moves
          return
        
        if before.channel == after.channel: # prevent processing if channel did'nt actually changed 
            return
        
        # check if joined channel is create vc channel
        if after.channel and after.channel.id == self.create_channel_id:
            guild: discord.Guild = member.guild

            category = guild.get_channel(self.category_id)
            
            if category is None or not isinstance(category, discord.CategoryChannel):
                return
                       
            member_owned_channel = self.owners_to_channel.get(member.id)
            
            if member_owned_channel is not None: # moving user into existsing owned channel rather than creating new
                existing_channel = guild.get_channel(member_owned_channel)
                if isinstance(existing_channel,discord.VoiceChannel):
                    return await member.move_to(existing_channel) 
                else:
                    # stale data cleanup
                    self.owners_to_channel.pop(member.id, None)
                    self.channel_to_owners.pop(member_owned_channel, None)
             


            new_channel: discord.VoiceChannel = await guild.create_voice_channel(
                name=f"{member.display_name}'s VC",
                category=category,
                user_limit=4
            )

            # Store ownership
            self.channel_to_owners[new_channel.id] = member.id
            self.owners_to_channel[member.id] = new_channel.id

            
            await member.move_to(new_channel)

        # Delete empty channels & remove ownership
        if before.channel:
            if before.channel.id in self.channel_to_owners:
                if len(before.channel.members) == 0:
                    owner_id = self.channel_to_owners.pop(before.channel.id,None)
                    if owner_id is not None:
                        self.owners_to_channel.pop(owner_id,None)

                    await before.channel.delete()

# setup function to load cog in main module 
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceManager(bot))