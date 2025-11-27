from services.sync_manager import sync_all_data_to_mongodb
from services.cache_manager import cleanup_all_expired_keys
from discord.ext import commands, tasks


class SyncEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sync_mongodb_redis.start()
        self.cleanup_redis_cache.start()

    def cog_unload(self):
        self.sync_mongodb_redis.cancel()
        self.cleanup_redis_cache.cancel()

    @tasks.loop(minutes=10)
    async def sync_mongodb_redis(self):
        """Perform the actual synchronization from Redis to MongoDB every 10 minutes"""
        try:
            print("🔄 Starting periodic synchronization...")
            total_synced = await sync_all_data_to_mongodb()
            print(f"✅ Periodic sync completed! Total items synced: {total_synced}")
            
        except Exception as e:
            print(f"❌ Periodic sync error: {e}")

    @tasks.loop(hours=1)
    async def cleanup_redis_cache(self):
        """Clean up expired Redis cache keys every hour"""
        try:
            print("🧹 Starting periodic cache cleanup...")
            total_cleaned = await cleanup_all_expired_keys()
            print(f"✅ Periodic cleanup completed! Total keys processed: {total_cleaned}")
            
        except Exception as e:
            print(f"❌ Periodic cleanup error: {e}")

    @sync_mongodb_redis.before_loop
    async def before_sync(self):
        """Wait for the bot to be ready before starting the sync loop"""
        await self.bot.wait_until_ready()
    
    @cleanup_redis_cache.before_loop
    async def before_cleanup(self):
        """Wait for the bot to be ready before starting the cleanup loop"""
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(SyncEvents(bot))