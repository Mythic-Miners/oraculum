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


async def sync_all_messages_to_mongodb():
    """Sync all Redis message data to MongoDB and delete from Redis (called periodically)"""
    try:
        # Get all message keys from Redis
        message_keys = await redis_client.get_keys("message:*")
        
        if not message_keys:
            print("📭 No messages to sync")
            return 0
        
        sync_count = 0
        keys_to_delete = []
        
        for key in message_keys:
            try:
                # Get message data from Redis
                cached_data = await redis_client.get(key)
                if cached_data:
                    message_data = loads(cached_data)
                    
                    # Extract message_id from key (format: "message:123456789")
                    message_id = key.decode('utf-8').split(':')[1] if isinstance(key, bytes) else key.split(':')[1]
                    message_data["message_id"] = int(message_id)
                    
                    # Insert into MongoDB
                    mongo_client.db.discord_messages.insert_one(message_data)
                    sync_count += 1
                    
                    # Add key to deletion list
                    keys_to_delete.append(key)
                        
            except Exception as e:
                print(f"❌ Error syncing message {key}: {e}")
        
        # Delete all synced messages from Redis
        if keys_to_delete:
            deleted_count = await redis_client.delete_keys(keys_to_delete)
            print(f"🗑️ Deleted {deleted_count} messages from Redis")
                
        print(f"💬 Synced {sync_count} messages to MongoDB")
        return sync_count
        
    except Exception as e:
        print(f"❌ Error during message sync: {e}")
        return 0