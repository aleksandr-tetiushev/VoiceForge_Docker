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

        embed = discord.Embed(title="Command Sync Status",description=f"`✅ Guild synced` : {len(synced)}",color=0x5865F2)
        await ctx.reply(embed=embed)

    @commands.command(name="syncglobal")
    @commands.is_owner()
    async def sync_global(self, ctx: commands.Context):
        synced = await self.bot.tree.sync()

        embed = discord.Embed(title="Command Sync Status",description=f"`🌍 Global synced` : {len(synced)}",color=0x5865F2)
        await ctx.reply(embed=embed)

    @commands.command(name="clearguild")
    @commands.is_owner()
    async def clearguild(self,ctx:commands.Context):
        if ctx.guild is None:
            await ctx.reply(f"Mamu ye command sirf servers me kaam krti ha.",mention_author=True)
            return
        self.bot.tree.clear_commands(guild=ctx.guild)
        await self.bot.tree.sync(guild=ctx.guild)
        await ctx.reply("🧹 Cleared all guild slash commands.")
    
    @commands.command(name="clearglobal")
    @commands.is_owner()
    async def clearglobal(self,ctx:commands.Context):
        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync()
        await ctx.reply("⚠️ Cleared ALL global slash commands.")


async def setup(bot:commands.Bot):
    await bot.add_cog(SyncCommands(bot))