import discord
from discord.ext import commands
from discord import app_commands

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
            await ctx.reply(f"This command only works in servers.",mention_author=True)
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

    @app_commands.command(name="help", description="Shows a list of all available commands.")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Help Menu", color=discord.Color.blue())
        # Iterate over all registered slash commands
        for command in self.bot.tree.walk_commands():
            # Add command name and description to the embed
            embed.add_field(name=f"/{command.qualified_name}", value=command.description, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # The custom prefix help command to list slash commands
    @commands.command(name="help", description="Shows this help message for slash commands.")
    async def help_command(self,ctx: commands.Context):
        embed = discord.Embed(title="Slash Commands Help",description="List of all available slash commands:",color=discord.Color.blurple())
    
        # Iterate over all registered application commands using walk_commands()
        for command in self.bot.tree.walk_commands():
            
            # Check if the command is a top-level command and not part of a group
            if isinstance(command, app_commands.Command):
                name = f"**/{command.name}**"
                value = command.description if command.description else "No description provided."
                embed.add_field(name=name, value=value, inline=False)
        
        await ctx.send(embed=embed)


async def setup(bot:commands.Bot):
    await bot.add_cog(SyncCommands(bot))