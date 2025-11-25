from config import REDIS_CLOUD_URI
import redis.asyncio as redis


class RedisClient(object):
    def __init__(self):
        self.pool = redis.ConnectionPool.from_url(REDIS_CLOUD_URI)
        self.client = redis.Redis.from_pool(self.pool)

    async def insert(self, key, value):
        await self.client.set(key, value)

    async def get(self, key):
        return await self.client.get(key)
    
    async def get_keys(self, pattern):
        """Get all keys matching the pattern"""
        return await self.client.keys(pattern)

    async def close(self):
        await self.client.close()


redis_client = RedisClient()