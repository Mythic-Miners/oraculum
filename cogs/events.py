
from utils.helpers import sync_all_users_to_mongodb, sync_all_messages_to_mongodb, sync_all_reactions_to_mongodb, sync_all_voice_sessions_to_mongodb, sync_economy_claims_to_mongodb
from discord.ext import commands, tasks
from config import COMMANDS_CHANNEL_ID
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
            # Sync users
            user_sync_count = await sync_all_users_to_mongodb()
            print(f"✅ Successfully synced {user_sync_count} users to MongoDB")
            
            # Sync messages and delete from Redis
            message_sync_count = await sync_all_messages_to_mongodb()
            print(f"✅ Successfully synced {message_sync_count} messages to MongoDB")
            
            # Sync reactions and delete from Redis
            reaction_sync_count = await sync_all_reactions_to_mongodb()
            print(f"✅ Successfully synced {reaction_sync_count} reactions to MongoDB")
            
            # Sync voice sessions and delete from Redis
            voice_sync_count = await sync_all_voice_sessions_to_mongodb()
            print(f"✅ Successfully synced {voice_sync_count} voice sessions to MongoDB")
            
            # Sync economy claims and delete from Redis
            economy_sync_count = await sync_economy_claims_to_mongodb()
            print(f"✅ Successfully synced {economy_sync_count} economy claims to MongoDB")
            
        except ImportError:
            print("⚠️ Sync functions not found in utils.helpers")
        except Exception as e:
            print(f"❌ Sync error: {e}")

    @sync_mongodb_redis.before_loop
    async def before_sync(self):
        """Wait for the bot to be ready before starting the loop"""
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(SyncEvents(bot))