from services.redis_client import redis_client
from services.db_client import mongo_client
from json import loads


async def sync_all_users_to_mongodb():
    """Sync all Redis user data to MongoDB (called periodically)"""
    try:
        user_keys = await redis_client.get_keys("user:*")
        
        if not user_keys:
            print("📭 No users to sync")
            return 0
        
        sync_count = 0
        for key in user_keys:
            try:
                cached_data = await redis_client.get(key)
                if cached_data:
                    user_data = loads(cached_data)
                    user_id = user_data.get("user_id")
                    
                    if user_id:
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
        print(f"❌ Error during user sync: {e}")
        return 0


async def sync_all_messages_to_mongodb():
    """Sync all Redis message data to MongoDB and delete from Redis (called periodically)"""
    try:
        message_keys = await redis_client.get_keys("message:*")
        
        if not message_keys:
            print("📭 No messages to sync")
            return 0
        
        sync_count = 0
        keys_to_delete = []
        
        for key in message_keys:
            try:
                cached_data = await redis_client.get(key)
                if cached_data:
                    message_data = loads(cached_data)
                    
                    # Extract message_id from key (format: "message:123456789")
                    message_id = key.decode('utf-8').split(':')[1] if isinstance(key, bytes) else key.split(':')[1]
                    message_data["message_id"] = int(message_id)
                    
                    mongo_client.db.discord_messages.insert_one(message_data)
                    sync_count += 1
                    
                    keys_to_delete.append(key)
                        
            except Exception as e:
                print(f"❌ Error syncing message {key}: {e}")
        
        if keys_to_delete:
            deleted_count = await redis_client.delete_keys(keys_to_delete)
            print(f"🗑️ Deleted {deleted_count} messages from Redis")
                
        print(f"💬 Synced {sync_count} messages to MongoDB")
        return sync_count
        
    except Exception as e:
        print(f"❌ Error during message sync: {e}")
        return 0


async def sync_all_reactions_to_mongodb():
    """Sync all Redis reaction data to MongoDB and delete from Redis (called periodically)"""
    try:
        reaction_keys = await redis_client.get_keys("reaction:*")
        
        if not reaction_keys:
            print("👍 No reactions to sync")
            return 0
        
        sync_count = 0
        keys_to_delete = []
        
        for key in reaction_keys:
            try:
                cached_data = await redis_client.get(key)
                if cached_data:
                    reaction_data = loads(cached_data)
                    
                    # Extract info from key (format: "reaction:message_id:user_id:emoji")
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    parts = key_str.split(':')
                    if len(parts) >= 4:
                        reaction_data["message_id"] = int(parts[1])
                        reaction_data["emoji"] = ':'.join(parts[3:])
                    
                    mongo_client.db.discord_reactions.insert_one(reaction_data)
                    sync_count += 1
                    
                    keys_to_delete.append(key)
                        
            except Exception as e:
                print(f"❌ Error syncing reaction {key}: {e}")
        
        if keys_to_delete:
            deleted_count = await redis_client.delete_keys(keys_to_delete)
            print(f"🗑️ Deleted {deleted_count} reactions from Redis")
                
        print(f"👍 Synced {sync_count} reactions to MongoDB")
        return sync_count
        
    except Exception as e:
        print(f"❌ Error during reaction sync: {e}")
        return 0


async def sync_all_voice_sessions_to_mongodb():
    """Sync all Redis voice session data to MongoDB and delete from Redis (called periodically)"""
    try:
        voice_keys = await redis_client.get_keys("voice:*")
        
        if not voice_keys:
            print("🎤 No voice sessions to sync")
            return 0
        
        sync_count = 0
        keys_to_delete = []
        
        for key in voice_keys:
            try:
                cached_data = await redis_client.get(key)
                if cached_data:
                    voice_data = loads(cached_data)
                    
                    mongo_client.db.discord_voice_sessions.insert_one(voice_data)
                    sync_count += 1
                    
                    keys_to_delete.append(key)
                        
            except Exception as e:
                print(f"❌ Error syncing voice session {key}: {e}")
        
        if keys_to_delete:
            deleted_count = await redis_client.delete_keys(keys_to_delete)
            print(f"🗑️ Deleted {deleted_count} voice sessions from Redis")
                
        print(f"🎤 Synced {sync_count} voice sessions to MongoDB")
        return sync_count
        
    except Exception as e:
        print(f"❌ Error during voice session sync: {e}")
        return 0


async def sync_economy_claims_to_mongodb():
    """Sync all Redis economy claims (daily/weekly) to MongoDB and delete from Redis"""
    try:
        claim_keys = await redis_client.get_keys("claim:*")
        
        if not claim_keys:
            print("💰 No economy claims to sync")
            return 0
        
        sync_count = 0
        keys_to_delete = []
        
        for key in claim_keys:
            try:
                cached_data = await redis_client.get(key)
                if cached_data:
                    claim_data = loads(cached_data)
                    
                    mongo_client.db.economy_claims.insert_one(claim_data)
                    sync_count += 1
                    
                    keys_to_delete.append(key)
                        
            except Exception as e:
                print(f"❌ Error syncing economy claim {key}: {e}")
        
        if keys_to_delete:
            deleted_count = await redis_client.delete_keys(keys_to_delete)
            print(f"🗑️ Deleted {deleted_count} economy claims from Redis")
                
        print(f"💰 Synced {sync_count} economy claims to MongoDB")
        return sync_count
        
    except Exception as e:
        print(f"❌ Error during economy claims sync: {e}")
        return 0


async def sync_marketplace_purchases_to_mongodb():
    """Sync all Redis marketplace purchases to MongoDB and delete from Redis"""
    try:
        purchase_keys = await redis_client.get_keys("purchase:*")
        
        if not purchase_keys:
            print("🛒 No marketplace purchases to sync")
            return 0
        
        sync_count = 0
        keys_to_delete = []
        
        for key in purchase_keys:
            try:
                cached_data = await redis_client.get(key)
                if cached_data:
                    purchase_data = loads(cached_data)
                    
                    mongo_client.db.discord_marketplace_purchases.insert_one(purchase_data)
                    sync_count += 1
                    
                    keys_to_delete.append(key)
                        
            except Exception as e:
                print(f"❌ Error syncing marketplace purchase {key}: {e}")
        
        if keys_to_delete:
            deleted_count = await redis_client.delete_keys(keys_to_delete)
            print(f"🗑️ Deleted {deleted_count} marketplace purchases from Redis")
                
        print(f"🛒 Synced {sync_count} marketplace purchases to MongoDB")
        return sync_count
        
    except Exception as e:
        print(f"❌ Error during marketplace purchases sync: {e}")
        return 0


async def sync_all_data_to_mongodb():
    """Sync all data types from Redis to MongoDB"""
    try:
        print("🔄 Starting full data synchronization...")
        
        user_count = await sync_all_users_to_mongodb()
        message_count = await sync_all_messages_to_mongodb()
        reaction_count = await sync_all_reactions_to_mongodb()
        voice_count = await sync_all_voice_sessions_to_mongodb()
        economy_count = await sync_economy_claims_to_mongodb()
        purchase_count = await sync_marketplace_purchases_to_mongodb()
        
        total = user_count + message_count + reaction_count + voice_count + economy_count + purchase_count
        print(f"✅ Full synchronization completed! Total: {total} items synced")
        return total
        
    except Exception as e:
        print(f"❌ Error during full sync: {e}")
        return 0
