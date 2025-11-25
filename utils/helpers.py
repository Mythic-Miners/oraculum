from services.redis_client import RedisClient
from services.db_client import DBClient
from json import loads, dumps
from config import *


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
    required_xp = INITIAL_XP_FOR_LEVEL_UP
    level = 1
    
    while xp >= required_xp:
        xp -= required_xp
        level += 1
        required_xp = int(required_xp * (1 + XP_PERCENTAGE_INCREASE_PER_LEVEL))
    
    return level


async def update_user_xp(user_id, xp_gain):
    """Update XP only in Redis cache (fast operations)"""
    user_data = await get_user_data(user_id)
    if not user_data:
        # Create new user
        user_data = {
            "user_id": user_id,
            XP_POINTS_PREFIX.lower(): 0,
            LEVEL_PREFIX.lower(): 1,
            MONEY_PREFIX.lower(): STARTING_BALANCE
        }
    
    # Update XP
    old_level = user_data.get(LEVEL_PREFIX.lower(), 1)
    user_data[XP_POINTS_PREFIX.lower()] += xp_gain

    # Calculate new level
    new_level = calculate_level(user_data[XP_POINTS_PREFIX.lower()])
    leveled_up = new_level > old_level
    user_data[LEVEL_PREFIX.lower()] = new_level
    
    # Update only Redis (fast)
    await redis_client.insert(f"user:{user_id}", dumps(user_data))
    
    return leveled_up, new_level


async def sync_all_users_to_mongodb():
    """Sync all Redis data to MongoDB (called periodically)"""
    try:
        # Get all user keys from Redis
        user_keys = await redis_client.get_keys("user:*")
        
        sync_count = 0
        for key in user_keys:
            try:
                # Get user data from Redis
                cached_data = await redis_client.get(key)
                if cached_data:
                    user_data = loads(cached_data)
                    user_id = user_data.get("user_id")
                    
                    if user_id:
                        # Update MongoDB
                        mongo_client.db.discord_users.update_one(
                            {"user_id": user_id}, 
                            {"$set": user_data}, 
                            upsert=True
                        )
                        sync_count += 1
                        
            except Exception as e:
                print(f"❌ Error syncing user {key}: {e}")
                
        print(f"📊 Synced {sync_count} users to MongoDB")
        return sync_count
        
    except Exception as e:
        print(f"❌ Error during bulk sync: {e}")
        return 0