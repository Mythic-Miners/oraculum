from services.sync_manager import sync_all_data_to_mongodb
from services.cache_manager import cleanup_all_expired_keys
from services.db_client import mongo_client
from discord.ext import commands
import config # type: ignore
import discord


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def is_admin_channel(self, ctx):
        """Check if command is being executed in admin channel"""
        if ctx.channel.id != config.ADMIN_CHANNEL_ID:
            await ctx.message.add_reaction("❌")
            await ctx.message.delete(delay=3)
            return False
        return True
    
    @commands.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def sync_now_command(self, ctx):
        """Manual command to execute synchronization immediately"""
        if not await self.is_admin_channel(ctx):
            return
        
        await ctx.send("🔄 Starting manual synchronization...")
        
        try:
            total_synced = await sync_all_data_to_mongodb()
            await ctx.send(f"✅ **Synchronization completed!** Total items synced: {total_synced}")
            
        except Exception as e:
            await ctx.send(f"❌ Sync error: {e}")
    
    @commands.command(name="cleanup")
    @commands.has_permissions(administrator=True)
    async def cleanup_cache_command(self, ctx):
        """Manual command to clean up expired Redis cache"""
        if not await self.is_admin_channel(ctx):
            return
        
        await ctx.send("🧹 Starting cache cleanup...")
        
        try:
            total_cleaned = await cleanup_all_expired_keys()
            await ctx.send(f"✅ **Cleanup completed!** Total keys processed: {total_cleaned}")
            
        except Exception as e:
            await ctx.send(f"❌ Cleanup error: {e}")
    
    @commands.command(name="add_item")
    @commands.has_permissions(administrator=True)
    async def add_marketplace_item(self, ctx, name: str, price: int, *, description: str = "No description"):
        """Add a new item to the marketplace
        Usage: /add_item "Item Name" 100 Item description here
        """
        if not await self.is_admin_channel(ctx):
            return
        
        if price < 0:
            await ctx.send("❌ Price must be a positive number!")
            return
        
        # Check if item already exists
        existing_item = mongo_client.db.discord_marketplace.find_one({"name": name})
        
        if existing_item:
            await ctx.send(f"❌ Item **{name}** already exists in the marketplace!")
            return
        
        # Create item
        item_data = {
            "name": name,
            "price": price,
            "description": description,
            "available": True,
            "created_by": ctx.author.id,
            "created_at": ctx.message.created_at.isoformat()
        }
        
        mongo_client.db.discord_marketplace.insert_one(item_data)
        
        embed = discord.Embed(
            title="✅ Item Added to Marketplace",
            color=0x00ff00
        )
        embed.add_field(name="Name", value=name, inline=True)
        embed.add_field(name="Price", value=f"{price} {config.MONEY_PREFIX}", inline=True)
        embed.add_field(name="Description", value=description, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="remove_item")
    @commands.has_permissions(administrator=True)
    async def remove_marketplace_item(self, ctx, *, name: str):
        """Remove an item from the marketplace
        Usage: /remove_item Item Name
        """
        if not await self.is_admin_channel(ctx):
            return
        
        # Check if item exists
        result = mongo_client.db.discord_marketplace.delete_one({"name": name})
        
        if result.deleted_count == 0:
            await ctx.send(f"❌ Item **{name}** not found in marketplace!")
            return
        
        embed = discord.Embed(
            title="🗑️ Item Removed from Marketplace",
            description=f"**{name}** has been removed from the marketplace.",
            color=0xff0000
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="update_item")
    @commands.has_permissions(administrator=True)
    async def update_marketplace_item(self, ctx, name: str, price: int = None, *, description: str = None):
        """Update an item's price or description
        Usage: /update_item "Item Name" 150 New description
        Usage: /update_item "Item Name" 150  (only update price)
        """
        if not await self.is_admin_channel(ctx):
            return
        
        # Check if item exists
        existing_item = mongo_client.db.discord_marketplace.find_one({"name": name})
        
        if not existing_item:
            await ctx.send(f"❌ Item **{name}** not found in marketplace!")
            return
        
        # Prepare update data
        update_data = {}
        if price is not None:
            if price < 0:
                await ctx.send("❌ Price must be a positive number!")
                return
            update_data["price"] = price
        
        if description is not None:
            update_data["description"] = description
        
        if not update_data:
            await ctx.send("❌ No updates provided! Specify price and/or description.")
            return
        
        # Update item
        mongo_client.db.discord_marketplace.update_one(
            {"name": name},
            {"$set": update_data}
        )
        
        embed = discord.Embed(
            title="✏️ Item Updated",
            color=0x0099ff
        )
        embed.add_field(name="Item", value=name, inline=False)
        if price is not None:
            embed.add_field(name="New Price", value=f"{price} {config.MONEY_PREFIX}", inline=True)
        if description is not None:
            embed.add_field(name="New Description", value=description, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="toggle_item")
    @commands.has_permissions(administrator=True)
    async def toggle_item_availability(self, ctx, *, name: str):
        """Toggle item availability (enable/disable)
        Usage: /toggle_item Item Name
        """
        if not await self.is_admin_channel(ctx):
            return
        
        # Check if item exists
        existing_item = mongo_client.db.discord_marketplace.find_one({"name": name})
        
        if not existing_item:
            await ctx.send(f"❌ Item **{name}** not found in marketplace!")
            return
        
        # Toggle availability
        new_status = not existing_item.get("available", True)
        
        mongo_client.db.discord_marketplace.update_one(
            {"name": name},
            {"$set": {"available": new_status}}
        )
        
        status_text = "✅ Available" if new_status else "❌ Unavailable"
        embed = discord.Embed(
            title="🔄 Item Availability Updated",
            description=f"**{name}** is now {status_text}",
            color=0x00ff00 if new_status else 0xff0000
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="list_items")
    @commands.has_permissions(administrator=True)
    async def list_marketplace_items(self, ctx):
        """List all marketplace items
        Usage: /list_items
        """
        if not await self.is_admin_channel(ctx):
            return
        
        items = list(mongo_client.db.discord_marketplace.find())
        
        if not items:
            await ctx.send("📭 No items in marketplace yet!")
            return
        
        embed = discord.Embed(
            title="🛒 Marketplace Items",
            color=0x0099ff
        )
        
        for item in items:
            status = "✅" if item.get("available", True) else "❌"
            embed.add_field(
                name=f"{status} {item['name']} - {item['price']} {config.MONEY_PREFIX}",
                value=item.get('description', 'No description'),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="give_money")
    @commands.has_permissions(administrator=True)
    async def give_money(self, ctx, member: discord.Member, amount: int):
        """Give money to a user
        Usage: /give_money @user 100
        """
        if not await self.is_admin_channel(ctx):
            return
        
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return
        
        from utils.helpers import get_user_data, redis_client
        from json import dumps
        
        # Get user data
        user_data = await get_user_data(member.id)
        if not user_data:
            user_data = {
                "user_id": member.id,
                config.XP_POINTS_PREFIX.lower(): 0,
                config.LEVEL_PREFIX.lower(): 1,
                config.MONEY_PREFIX.lower(): config.STARTING_BALANCE
            }
        
        # Add money
        user_data[config.MONEY_PREFIX.lower()] = user_data.get(config.MONEY_PREFIX.lower(), 0) + amount
        
        # Update Redis
        await redis_client.insert(f"user:{member.id}", dumps(user_data))
        
        embed = discord.Embed(
            title=f"{config.MONEY_EMOJI} Money Given",
            description=f"Gave **{amount} {config.MONEY_PREFIX}** to {member.mention}",
            color=0x00ff00
        )
        embed.add_field(
            name="New Balance",
            value=f"{user_data[config.MONEY_PREFIX.lower()]} {config.MONEY_PREFIX}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="take_money")
    @commands.has_permissions(administrator=True)
    async def take_money(self, ctx, member: discord.Member, amount: int):
        """Take money from a user
        Usage: /take_money @user 50
        """
        if not await self.is_admin_channel(ctx):
            return
        
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return
        
        from utils.helpers import get_user_data, redis_client
        from json import dumps
        
        # Get user data
        user_data = await get_user_data(member.id)
        if not user_data:
            await ctx.send(f"❌ {member.mention} doesn't have any data yet!")
            return
        
        # Take money
        current_balance = user_data.get(config.MONEY_PREFIX.lower(), 0)
        user_data[config.MONEY_PREFIX.lower()] = max(0, current_balance - amount)
        
        # Update Redis
        await redis_client.insert(f"user:{member.id}", dumps(user_data))
        
        embed = discord.Embed(
            title=f"{config.MONEY_EMOJI} Money Taken",
            description=f"Took **{amount} {config.MONEY_PREFIX}** from {member.mention}",
            color=0xff0000
        )
        embed.add_field(
            name="New Balance",
            value=f"{user_data[config.MONEY_PREFIX.lower()]} {config.MONEY_PREFIX}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="set_level")
    @commands.has_permissions(administrator=True)
    async def set_level(self, ctx, member: discord.Member, level: int):
        """Set a user's level
        Usage: /set_level @user 10
        """
        if not await self.is_admin_channel(ctx):
            return
        
        if level < 1:
            await ctx.send("❌ Level must be at least 1!")
            return
        
        from utils.helpers import get_user_data, redis_client
        from json import dumps
        
        # Get user data
        user_data = await get_user_data(member.id)
        if not user_data:
            user_data = {
                "user_id": member.id,
                config.XP_POINTS_PREFIX.lower(): 0,
                config.LEVEL_PREFIX.lower(): 1,
                config.MONEY_PREFIX.lower(): config.STARTING_BALANCE
            }
        
        # Set level
        user_data[config.LEVEL_PREFIX.lower()] = level
        
        # Update Redis
        await redis_client.insert(f"user:{member.id}", dumps(user_data))
        
        embed = discord.Embed(
            title=f"{config.LEVEL_EMOJI} Level Set",
            description=f"Set {member.mention}'s level to **{config.LEVEL_PREFIX} {level}**",
            color=0x0099ff
        )
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Admin(bot))