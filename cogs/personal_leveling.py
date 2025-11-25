from utils.helpers import get_user_data, update_user_xp
from services.redis_client import redis_client
from time import strftime, gmtime
from discord.ext import commands
from json import dumps, loads
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
        
        # Store message info in Redis for later deletion tracking
        message_data = {
            "user_id": user_id,
            "xp_value": XP_FOR_MESSAGE,
            "timestamp": strftime("%Y-%m-%d %H:%M:%S", gmtime())
        }
        await redis_client.insert(f"message:{message.id}", dumps(message_data))
        # Set expiration to 7 days (604800 seconds) to avoid filling Redis
        await redis_client.client.expire(f"message:{message.id}", 604800)
        
        # Add XP
        leveled_up, new_level = await update_user_xp(user_id, XP_FOR_MESSAGE)
        
        # Check if leveled up
        if leveled_up:
            notifications_channel = self.bot.get_channel(NOTIFICATIONS_CHANNEL_ID)
            if notifications_channel:
                await notifications_channel.send(
                    f"{LEVEL_UP_EMOJI} {message.author.mention} leveled up to **{LEVEL_PREFIX} {new_level}**!"
                )
            else:
                # Fallback to current channel if notifications channel not found
                await message.channel.send(
                    f"{LEVEL_UP_EMOJI} {message.author.mention} leveled up to **{LEVEL_PREFIX} {new_level}**!"
                )
    
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        """Event when a message is deleted - works for old messages too"""
        # Try to get message info from Redis
        message_key = f"message:{payload.message_id}"
        cached_message = await redis_client.get(message_key)
        
        if cached_message:
            message_data = loads(cached_message)
            user_id = message_data.get("user_id")
            xp_value = message_data.get("xp_value", XP_FOR_MESSAGE)
            
            if user_id:
                # Decrease XP
                await update_user_xp(user_id, -xp_value)
                
                # Clean up Redis
                await redis_client.client.delete(message_key)

    # Example command to check stats
    @commands.command(name='stats')
    async def check_stats(self, ctx):
        """Command to check current stats"""
        # Check if command is in the correct channel
        if ctx.channel.id != COMMANDS_CHANNEL_ID:
            await ctx.message.add_reaction("❌")
            return
        
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
            name=f"{LEVEL_UP_EMOJI} {LEVEL_NAME}", 
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