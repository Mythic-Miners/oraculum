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
        # Track voice channel join times
        self.voice_sessions = {}
    
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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Event when a reaction is added to a message"""
        # Ignore bot reactions
        if payload.member and payload.member.bot:
            return
        
        # Check if reaction is in announcements channel
        if payload.channel_id != SERVER_ANNOUNCEMENTS_CHANNEL_ID:
            return
        
        user_id = payload.user_id
        
        # Check if user already reacted to this message (any emoji)
        user_reactions_pattern = f"reaction:{payload.message_id}:{user_id}:*"
        existing_reactions = await redis_client.get_keys(user_reactions_pattern)
        
        # If user already has a reaction on this message, don't give XP
        if existing_reactions:
            return
        
        # Store reaction info in Redis
        reaction_key = f"reaction:{payload.message_id}:{user_id}:{payload.emoji}"
        reaction_data = {
            "user_id": user_id,
            "message_id": payload.message_id,
            "xp_value": XP_FOR_REACT,
            "timestamp": strftime("%Y-%m-%d %H:%M:%S", gmtime())
        }
        await redis_client.insert(reaction_key, dumps(reaction_data))
        # Set expiration to 30 days (2592000 seconds)
        await redis_client.client.expire(reaction_key, 2592000)
        
        # Add XP for reaction
        leveled_up, new_level = await update_user_xp(user_id, XP_FOR_REACT)
        
        # Check if leveled up
        if leveled_up:
            notifications_channel = self.bot.get_channel(NOTIFICATIONS_CHANNEL_ID)
            if notifications_channel:
                member = payload.member
                await notifications_channel.send(
                    f"{LEVEL_UP_EMOJI} {member.mention} leveled up to **{LEVEL_PREFIX} {new_level}**!"
                )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Event when a reaction is removed from a message"""
        # Check if reaction is in announcements channel
        if payload.channel_id != SERVER_ANNOUNCEMENTS_CHANNEL_ID:
            return
        
        user_id = payload.user_id
        
        # Try to get reaction info from Redis
        reaction_key = f"reaction:{payload.message_id}:{user_id}:{payload.emoji}"
        cached_reaction = await redis_client.get(reaction_key)
        
        if cached_reaction:
            reaction_data = loads(cached_reaction)
            xp_value = reaction_data.get("xp_value", XP_FOR_REACT)
            
            # Decrease XP
            await update_user_xp(user_id, -xp_value)
            
            # Clean up Redis
            await redis_client.client.delete(reaction_key)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Event when a user's voice state changes"""
        # Ignore bots
        if member.bot:
            return
        
        user_id = member.id
        from time import time
        current_time = time()
        
        # User joined a voice channel
        if before.channel is None and after.channel is not None:
            # Store join time
            self.voice_sessions[user_id] = {
                "join_time": current_time,
                "channel_id": after.channel.id
            }
        
        # User left a voice channel
        elif before.channel is not None and after.channel is None:
            if user_id in self.voice_sessions:
                session = self.voice_sessions[user_id]
                join_time = session["join_time"]
                
                # Calculate time spent in voice (in minutes)
                time_diff = current_time - join_time
                minutes_spent = int(time_diff / 60)
                
                if minutes_spent > 0:
                    # Calculate XP based on minutes
                    xp_gain = minutes_spent * XP_FOR_VOICE_MINUTE
                    
                    # Add XP
                    leveled_up, new_level = await update_user_xp(user_id, xp_gain)
                    
                    # Store voice session in Redis for tracking
                    voice_data = {
                        "user_id": user_id,
                        "minutes": minutes_spent,
                        "xp_value": xp_gain,
                        "timestamp": strftime("%Y-%m-%d %H:%M:%S", gmtime())
                    }
                    voice_key = f"voice:{user_id}:{int(join_time)}"
                    await redis_client.insert(voice_key, dumps(voice_data))
                    # Set expiration to 30 days (2592000 seconds)
                    await redis_client.client.expire(voice_key, 2592000)
                    
                    # Check if leveled up
                    if leveled_up:
                        notifications_channel = self.bot.get_channel(NOTIFICATIONS_CHANNEL_ID)
                        if notifications_channel:
                            await notifications_channel.send(
                                f"{LEVEL_UP_EMOJI} {member.mention} leveled up to **{LEVEL_PREFIX} {new_level}**!"
                            )
                
                # Remove session
                del self.voice_sessions[user_id]
        
        # User switched voice channels
        elif before.channel is not None and after.channel is not None:
            if before.channel.id != after.channel.id:
                # Update channel_id in session
                if user_id in self.voice_sessions:
                    self.voice_sessions[user_id]["channel_id"] = after.channel.id

    # Example command to check stats
    @commands.command(name='stats')
    async def check_stats(self, ctx):
        """Command to check current stats"""
        # Check if command is in the correct channel
        if ctx.channel.id != COMMANDS_CHANNEL_ID:
            await ctx.message.add_reaction("❌")
            await ctx.message.delete(delay=3)
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
            name=f"{LEVEL_EMOJI} {LEVEL_NAME}", 
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