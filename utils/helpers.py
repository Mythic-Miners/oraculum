from services.redis_client import RedisClient
from services.db_client import DBClient
from json import loads, dumps
import config # type: ignore


redis_client = RedisClient()
mongo_client = DBClient()

async def get_user_data(user_id):
    """Get user data from cache first, then database"""
    # Try Redis first (fast)
    cached_data = await redis_client.get(f"user:{user_id}")
    if cached_data:
        return loads(cached_data)
        
    # Fallback to MongoDB
    user_doc = mongo_client.find("discord_users", {"user_id": user_id})
    user_list = list(user_doc)
    
    if user_list:
        user_data = user_list[0]
        # Remove ObjectId before caching (not JSON serializable)
        if "_id" in user_data:
            del user_data["_id"]
        # Cache for next time
        await redis_client.insert(f"user:{user_id}", dumps(user_data))
        return user_data
        
    return None


def calculate_level(xp):
    """Calculate level based on XP"""
    required_xp = config.INITIAL_XP_FOR_LEVEL_UP
    level = 1
    
    while xp >= required_xp:
        xp -= required_xp
        level += 1
        required_xp = int(required_xp * (1 + config.XP_PERCENTAGE_INCREASE_PER_LEVEL))
    
    return level


async def update_user_xp(user_id, xp_gain):
    """Update XP only in Redis cache (fast operations)"""
    user_data = await get_user_data(user_id)
    if not user_data:
        # Create new user
        user_data = {
            "user_id": user_id,
            config.XP_POINTS_PREFIX.lower(): 0,
            config.LEVEL_PREFIX.lower(): 1,
            config.MONEY_PREFIX.lower(): config.STARTING_BALANCE
        }
    
    # Update XP
    old_level = user_data.get(config.LEVEL_PREFIX.lower(), 1)
    user_data[config.XP_POINTS_PREFIX.lower()] += xp_gain

    # Calculate new level
    new_level = calculate_level(user_data[config.XP_POINTS_PREFIX.lower()])
    leveled_up = new_level > old_level
    user_data[config.LEVEL_PREFIX.lower()] = new_level
    
    # Update only Redis (fast)
    await redis_client.insert(f"user:{user_id}", dumps(user_data))
    
    return leveled_up, new_level