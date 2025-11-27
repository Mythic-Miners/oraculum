from services.redis_client import redis_client
from json import loads


async def cleanup_expired_messages():
    """Clean up expired messages from Redis"""
    try:
        message_keys = await redis_client.get_keys("message:*")
        
        if not message_keys:
            print("📭 No messages to clean up")
            return 0
        
        # Redis TTL will automatically delete expired keys
        # This function can be used for manual cleanup if needed
        cleaned_count = 0
        for key in message_keys:
            ttl = await redis_client.client.ttl(key)
            if ttl == -2:  # Key doesn't exist
                cleaned_count += 1
            elif ttl == -1:  # Key has no expiration
                # Set expiration to 7 days if missing
                await redis_client.client.expire(key, 604800)
        
        if cleaned_count > 0:
            print(f"🗑️ Cleaned up {cleaned_count} expired messages")
        return cleaned_count
        
    except Exception as e:
        print(f"❌ Error during message cleanup: {e}")
        return 0


async def cleanup_expired_reactions():
    """Clean up expired reactions from Redis"""
    try:
        reaction_keys = await redis_client.get_keys("reaction:*")
        
        if not reaction_keys:
            print("👍 No reactions to clean up")
            return 0
        
        cleaned_count = 0
        for key in reaction_keys:
            ttl = await redis_client.client.ttl(key)
            if ttl == -2:  # Key doesn't exist
                cleaned_count += 1
            elif ttl == -1:  # Key has no expiration
                # Set expiration to 30 days if missing
                await redis_client.client.expire(key, 2592000)
        
        if cleaned_count > 0:
            print(f"🗑️ Cleaned up {cleaned_count} expired reactions")
        return cleaned_count
        
    except Exception as e:
        print(f"❌ Error during reaction cleanup: {e}")
        return 0


async def cleanup_expired_voice_sessions():
    """Clean up expired voice sessions from Redis"""
    try:
        voice_keys = await redis_client.get_keys("voice:*")
        
        if not voice_keys:
            print("🎤 No voice sessions to clean up")
            return 0
        
        cleaned_count = 0
        for key in voice_keys:
            ttl = await redis_client.client.ttl(key)
            if ttl == -2:  # Key doesn't exist
                cleaned_count += 1
            elif ttl == -1:  # Key has no expiration
                # Set expiration to 30 days if missing
                await redis_client.client.expire(key, 2592000)
        
        if cleaned_count > 0:
            print(f"🗑️ Cleaned up {cleaned_count} expired voice sessions")
        return cleaned_count
        
    except Exception as e:
        print(f"❌ Error during voice session cleanup: {e}")
        return 0


async def cleanup_expired_economy_claims():
    """Clean up expired economy claims from Redis"""
    try:
        claim_keys = await redis_client.get_keys("claim:*")
        
        if not claim_keys:
            print("💰 No economy claims to clean up")
            return 0
        
        cleaned_count = 0
        for key in claim_keys:
            ttl = await redis_client.client.ttl(key)
            if ttl == -2:  # Key doesn't exist
                cleaned_count += 1
            elif ttl == -1:  # Key has no expiration
                # Determine expiration based on claim type
                cached_data = await redis_client.get(key)
                if cached_data:
                    claim_data = loads(cached_data)
                    claim_type = claim_data.get("claim_type")
                    if claim_type == "daily":
                        await redis_client.client.expire(key, 90000)  # 25 hours
                    elif claim_type == "weekly":
                        await redis_client.client.expire(key, 691200)  # 8 days
        
        if cleaned_count > 0:
            print(f"🗑️ Cleaned up {cleaned_count} expired economy claims")
        return cleaned_count
        
    except Exception as e:
        print(f"❌ Error during economy claims cleanup: {e}")
        return 0


async def cleanup_expired_purchases():
    """Clean up expired marketplace purchases from Redis"""
    try:
        purchase_keys = await redis_client.get_keys("purchase:*")
        
        if not purchase_keys:
            print("🛒 No marketplace purchases to clean up")
            return 0
        
        cleaned_count = 0
        for key in purchase_keys:
            ttl = await redis_client.client.ttl(key)
            if ttl == -2:  # Key doesn't exist
                cleaned_count += 1
            elif ttl == -1:  # Key has no expiration
                # Set expiration to 30 days if missing
                await redis_client.client.expire(key, 2592000)
        
        if cleaned_count > 0:
            print(f"🗑️ Cleaned up {cleaned_count} expired marketplace purchases")
        return cleaned_count
        
    except Exception as e:
        print(f"❌ Error during marketplace purchases cleanup: {e}")
        return 0


async def cleanup_all_expired_keys():
    """Clean up all expired keys from Redis cache"""
    try:
        print("🧹 Starting Redis cache cleanup...")
        
        message_count = await cleanup_expired_messages()
        reaction_count = await cleanup_expired_reactions()
        voice_count = await cleanup_expired_voice_sessions()
        economy_count = await cleanup_expired_economy_claims()
        purchase_count = await cleanup_expired_purchases()
        
        total = message_count + reaction_count + voice_count + economy_count + purchase_count
        print(f"✅ Cache cleanup completed! Total: {total} keys processed")
        return total
        
    except Exception as e:
        print(f"❌ Error during cache cleanup: {e}")
        return 0
