import discord
from discord.ext import commands

class SyncCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="syncguild")
    @commands.is_owner()
    async def sync_guild(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.reply("This command works in server only.")
            return

        self.bot.tree.copy_global_to(guild=ctx.guild)
        synced = await self.bot.tree.sync(guild=ctx.guild)

        embed = discord.Embed(
            title="Command Sync Status",
            description=f"`✅ Guild synced` : {len(synced)}",
            color=0x5865F2
        )
        await ctx.reply(embed=embed)

    @commands.command(name="syncglobal")
    @commands.is_owner()
    async def sync_global(self, ctx: commands.Context):
        synced = await self.bot.tree.sync()

        embed = discord.Embed(
            title="Command Sync Status",
            description=f"`🌍 Global synced` : {len(synced)}",
            color=0x5865F2
        )
        await ctx.reply(embed=embed)


async def setup(bot:commands.Bot):
    await bot.add_cog(SyncCommands(bot))