from utils.helpers import get_user_data, update_user_xp
from discord.ext import commands
from config import *
import discord


class PersonalLeveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return
            
        user_id = message.author.id
        
        # Add XP
        leveled_up, new_level = await update_user_xp(user_id, XP_FOR_MESSAGE)
        
        # Check if leveled up
        if leveled_up:
            await message.channel.send(
                f"{LEVEL_UP_EMOJI} {message.author.mention} leveled up to **{LEVEL_PREFIX} {new_level}**!"
            )
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Event when a message is deleted and XP is decreased
        """
        if message.author.bot:
            return

        print(f"Message deleted from {message.author}: {message.content}")

    # Example command to check stats
    @commands.command(name='stats')
    async def check_stats(self, ctx):
        """Command to check current stats"""
        user_data = await get_user_data(ctx.author.id)
        
        if not user_data:
            await ctx.send("❌ You don't have any stats yet! Send some messages first.")
            return
        
        embed = discord.Embed(
            title=f"{STATS_EMOJI} Your Stats",
            color=0x00ff00
        )
        embed.add_field(
            name=f"{XP_EMOJI} {XP_POINTS_NAME}", 
            value=f"{user_data[XP_POINTS_PREFIX.lower()]} {XP_POINTS_PREFIX}", 
            inline=True
        )
        embed.add_field(
            name=f"{LEVEL_NAME}", 
            value=f"{LEVEL_PREFIX} {user_data[LEVEL_PREFIX.lower()]}",
            inline=True
        )
        embed.add_field(
            name=f"{MONEY_EMOJI} {MONEY_NAME}", 
            value=f"{user_data.get(MONEY_PREFIX.lower(), 0)} {MONEY_PREFIX}", 
            inline=True
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)

# Function to load the cog
async def setup(bot):
    await bot.add_cog(PersonalLeveling(bot))