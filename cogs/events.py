
from utils.helpers import sync_all_users_to_mongodb
from discord.ext import commands, tasks
import discord


class SyncEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sync_mongodb_redis.start()

    def cog_unload(self):
        self.sync_mongodb_redis.cancel()

    @tasks.loop(minutes=10)
    async def sync_mongodb_redis(self):
        """Perform the actual synchronization from Redis to MongoDB every 10 minutes"""
        try:
            sync_count = await sync_all_users_to_mongodb()
            print(f"✅ Successfully synced {sync_count} users to MongoDB")
        except ImportError:
            print("⚠️ sync_all_users_to_mongodb function not found in utils.helpers")
        except Exception as e:
            print(f"❌ Sync error: {e}")

    @sync_mongodb_redis.before_loop
    async def before_sync(self):
        """Wait for the bot to be ready before starting the loop"""
        await self.bot.wait_until_ready()

    @commands.command(name="sync_now")
    @commands.has_permissions(administrator=True)
    async def sync_now_command(self, ctx):
        """Manual command to execute synchronization immediately"""
        await ctx.send("🔄 Starting manual synchronization...")
        await self.sync_mongodb_redis()
        await ctx.send("✅ Synchronization completed!")


async def setup(bot):
    await bot.add_cog(SyncEvents(bot))