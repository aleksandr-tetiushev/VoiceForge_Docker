from __future__ import annotations
import discord
from discord.ext import commands
from typing import Optional

class VoiceManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        
        # channel_id -> owner_id
        self.voice_owners: dict[int, int] = {}

        # convert env IDs to int once
        self.category_id: int = int(bot.category_id)
        self.create_channel_id: int = int(bot.create_channel_id)

    @commands.Cog.listener()
    async def on_voice_state_update(self,member: discord.Member,before: discord.VoiceState,after: discord.VoiceState) -> None:

        # check if joined channel is create vc channel
        if after.channel and after.channel.id == self.create_channel_id:
            guild: discord.Guild = member.guild

            category = guild.get_channel(self.category_id)
            if not isinstance(category, discord.CategoryChannel):
                return

            new_channel: discord.VoiceChannel = await guild.create_voice_channel(
                name=f"{member.display_name}'s VC",
                category=category
            )

            # Store ownership
            self.voice_owners[new_channel.id] = member.id

            await member.move_to(new_channel)

        # Delete empty channels & remove ownership
        if before.channel:
            if before.channel.id in self.voice_owners:
                if len(before.channel.members) == 0:
                    del self.voice_owners[before.channel.id]
                    await before.channel.delete()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceManager(bot))