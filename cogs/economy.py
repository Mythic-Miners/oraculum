from utils.helpers import get_user_data, redis_client
from services.db_client import mongo_client
from discord.ext import commands
from json import dumps
from time import time
from config import *
import discord


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='daily')
    async def claim_daily_reward(self, ctx):
        """Claim your daily reward (once every 24 hours)"""
        # Check if command is in the correct channel
        if ctx.channel.id != COMMANDS_CHANNEL_ID:
            await ctx.message.add_reaction("❌")
            await ctx.message.delete(delay=3)
            return
        
        user_id = ctx.author.id
        current_time = int(time())
        cooldown = 86400  # 24 hours in seconds
        
        # Check last daily claim from MongoDB first (source of truth)
        last_claim_doc = mongo_client.db.economy_claims.find_one(
            {"user_id": user_id, "claim_type": "daily"},
            sort=[("claim_time", -1)]
        )
        
        if last_claim_doc:
            last_claim_time = last_claim_doc["claim_time"]
            time_diff = current_time - last_claim_time
            
            if time_diff < cooldown:
                # Calculate remaining time
                remaining = cooldown - time_diff
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                
                embed = discord.Embed(
                    title=f"⏰ Daily Reward on Cooldown",
                    description=f"You can claim your daily reward again in **{hours}h {minutes}m**",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
        
        # Get user data
        user_data = await get_user_data(user_id)
        if not user_data:
            # Create new user
            user_data = {
                "user_id": user_id,
                XP_POINTS_PREFIX.lower(): 0,
                LEVEL_PREFIX.lower(): 1,
                MONEY_PREFIX.lower(): STARTING_BALANCE
            }
        
        # Add daily reward
        reward_amount = DAILY_REWARD + int(DAILY_REWARD * LEVEL_MULTIPLIER * user_data.get(LEVEL_PREFIX.lower(), 1))
        user_data[MONEY_PREFIX.lower()] = user_data.get(MONEY_PREFIX.lower(), 0) + reward_amount
        
        # Update Redis cache
        await redis_client.insert(f"user:{user_id}", dumps(user_data))
        
        # Store claim in Redis temporarily (will be synced to MongoDB)
        claim_key = f"claim:daily:{user_id}:{current_time}"
        claim_data = {
            "user_id": user_id,
            "claim_type": "daily",
            "claim_time": current_time,
            "amount": reward_amount
        }
        await redis_client.insert(claim_key, dumps(claim_data))
        # Set expiration to 25 hours
        await redis_client.client.expire(claim_key, 90000)
        
        # Send success message
        embed = discord.Embed(
            title=f"{MONEY_EMOJI} Daily Reward Claimed!",
            description=f"You received **{reward_amount} {MONEY_PREFIX}**!",
            color=0x00ff00
        )
        embed.add_field(
            name="New Balance",
            value=f"{user_data[MONEY_PREFIX.lower()]} {MONEY_PREFIX}",
            inline=False
        )
        embed.set_footer(text="Come back tomorrow for another reward!")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='weekly')
    async def claim_weekly_reward(self, ctx):
        """Claim your weekly reward (once every 7 days)"""
        # Check if command is in the correct channel
        if ctx.channel.id != COMMANDS_CHANNEL_ID:
            await ctx.message.add_reaction("❌")
            await ctx.message.delete(delay=3)
            return
        
        user_id = ctx.author.id
        current_time = int(time())
        cooldown = 604800  # 7 days in seconds
        
        # Check last weekly claim from MongoDB first (source of truth)
        last_claim_doc = mongo_client.db.economy_claims.find_one(
            {"user_id": user_id, "claim_type": "weekly"},
            sort=[("claim_time", -1)]
        )
        
        if last_claim_doc:
            last_claim_time = last_claim_doc["claim_time"]
            time_diff = current_time - last_claim_time
            
            if time_diff < cooldown:
                # Calculate remaining time
                remaining = cooldown - time_diff
                days = remaining // 86400
                hours = (remaining % 86400) // 3600
                minutes = (remaining % 3600) // 60
                
                embed = discord.Embed(
                    title=f"⏰ Weekly Reward on Cooldown",
                    description=f"You can claim your weekly reward again in **{days}d {hours}h {minutes}m**",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
        
        # Get user data
        user_data = await get_user_data(user_id)
        if not user_data:
            # Create new user
            user_data = {
                "user_id": user_id,
                XP_POINTS_PREFIX.lower(): 0,
                LEVEL_PREFIX.lower(): 1,
                MONEY_PREFIX.lower(): STARTING_BALANCE
            }
        
        # Add weekly reward
        reward_amount = WEEKLY_REWARD + int(WEEKLY_REWARD * LEVEL_MULTIPLIER * user_data.get(LEVEL_PREFIX.lower(), 1))
        user_data[MONEY_PREFIX.lower()] = user_data.get(MONEY_PREFIX.lower(), 0) + reward_amount
        
        # Update Redis cache
        await redis_client.insert(f"user:{user_id}", dumps(user_data))
        
        # Store claim in Redis temporarily (will be synced to MongoDB)
        claim_key = f"claim:weekly:{user_id}:{current_time}"
        claim_data = {
            "user_id": user_id,
            "claim_type": "weekly",
            "claim_time": current_time,
            "amount": reward_amount
        }
        await redis_client.insert(claim_key, dumps(claim_data))
        # Set expiration to 8 days
        await redis_client.client.expire(claim_key, 691200)
        
        # Send success message
        embed = discord.Embed(
            title=f"{MONEY_EMOJI} Weekly Reward Claimed!",
            description=f"You received **{reward_amount} {MONEY_PREFIX}**!",
            color=0x00ff00
        )
        embed.add_field(
            name="New Balance",
            value=f"{user_data[MONEY_PREFIX.lower()]} {MONEY_PREFIX}",
            inline=False
        )
        embed.set_footer(text="Come back next week for another reward!")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='balance')
    async def check_balance(self, ctx, member: discord.Member = None):
        """Check your balance or another user's balance"""
        # Check if command is in the correct channel
        if ctx.channel.id != COMMANDS_CHANNEL_ID:
            await ctx.message.add_reaction("❌")
            await ctx.message.delete(delay=3)
            return
        
        # If no member specified, check command author
        target = member if member else ctx.author
        
        # Don't allow checking bot balances
        if target.bot:
            await ctx.send("❌ Bots don't have balances!")
            return
        
        user_data = await get_user_data(target.id)
        
        if not user_data:
            if target == ctx.author:
                await ctx.send("❌ You don't have a balance yet! Send some messages to get started.")
            else:
                await ctx.send(f"❌ {target.mention} doesn't have a balance yet!")
            return
        
        balance = user_data.get(MONEY_PREFIX.lower(), 0)
        
        embed = discord.Embed(
            title=f"{MONEY_EMOJI} Balance",
            description=f"{'Your' if target == ctx.author else f'{target.name}\'s'} current balance",
            color=0x00ff00
        )
        embed.add_field(
            name=MONEY_NAME,
            value=f"**{balance} {MONEY_PREFIX}**",
            inline=False
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Economy(bot))