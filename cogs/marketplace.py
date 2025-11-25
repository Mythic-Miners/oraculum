from utils.helpers import get_user_data, redis_client
from services.db_client import mongo_client
from discord.ext import commands
from time import gmtime, strftime
from json import dumps
from config import *
import discord


class GameWalletModal(discord.ui.Modal, title="Enter Your Game Wallet"):
    wallet = discord.ui.TextInput(
        label="Game Wallet Address",
        placeholder="Enter your in-game wallet address here...",
        required=True,
        max_length=100
    )
    
    def __init__(self, bot, user_id, username, item_name, item_price, new_balance, timestamp):
        super().__init__()
        self.bot = bot
        self.user_id = user_id
        self.username = username
        self.item_name = item_name
        self.item_price = item_price
        self.new_balance = new_balance
        self.timestamp = timestamp
    
    async def on_submit(self, interaction: discord.Interaction):
        wallet_address = self.wallet.value
        
        # Create ticket in claimed rewards channel with wallet
        claimed_channel = self.bot.get_channel(CLAIMED_REWARDS_CHANNEL_ID)
        if claimed_channel:
            ticket_embed = discord.Embed(
                title="🎟️ New Purchase Claim",
                description="A user has made a purchase and provided their game wallet",
                color=0x00ff00
            )
            ticket_embed.add_field(name="User", value=f"{interaction.user.mention} ({self.username})", inline=False)
            ticket_embed.add_field(name="Discord User ID", value=str(self.user_id), inline=True)
            ticket_embed.add_field(name="Game Wallet", value=f"`{wallet_address}`", inline=False)
            ticket_embed.add_field(name="Item Purchased", value=self.item_name, inline=True)
            ticket_embed.add_field(name="Price Paid", value=f"{self.item_price} {MONEY_PREFIX}", inline=True)
            ticket_embed.add_field(name="Timestamp", value=self.timestamp, inline=False)
            ticket_embed.add_field(
                name="⚠️ Status", 
                value="Pending - Waiting for delivery confirmation",
                inline=False
            )
            ticket_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            ticket_embed.set_footer(text=f"Purchase ID: {int(self.timestamp.replace('-', '').replace(':', '').replace(' ', ''))}")
            
            # Create buttons view
            view = TicketButtonsView(
                self.bot,
                self.user_id,
                self.username,
                self.item_name,
                self.item_price,
                wallet_address,
                self.timestamp
            )
            
            await claimed_channel.send(embed=ticket_embed, view=view)
        
        # Confirm to user
        await interaction.response.send_message(
            f"✅ Thank you! Your wallet has been submitted. An admin will process your reward for **{self.item_name}** soon!",
            ephemeral=True
        )


class CancelModal(discord.ui.Modal, title="Cancel Ticket"):
    reason = discord.ui.TextInput(
        label="Cancellation Reason",
        placeholder="Enter the reason for cancelling this ticket...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    def __init__(self, bot, original_message, user_id, username, item_name):
        super().__init__()
        self.bot = bot
        self.original_message = original_message
        self.user_id = user_id
        self.username = username
        self.item_name = item_name
    
    async def on_submit(self, interaction: discord.Interaction):
        cancel_reason = self.reason.value
        
        # Update ticket embed
        embed = self.original_message.embeds[0]
        embed.color = 0xff0000
        embed.set_field_at(
            len(embed.fields) - 1,
            name="❌ Status",
            value=f"Cancelled by {interaction.user.mention}\nReason: {cancel_reason}",
            inline=False
        )
        
        # Remove buttons
        await self.original_message.edit(embed=embed, view=None)
        
        # Notify user in notifications channel
        notifications_channel = self.bot.get_channel(NOTIFICATIONS_CHANNEL_ID)
        if notifications_channel:
            user = self.bot.get_user(self.user_id)
            if user:
                notify_embed = discord.Embed(
                    title="❌ Purchase Cancelled",
                    description=f"Your purchase of **{self.item_name}** has been cancelled.",
                    color=0xff0000
                )
                notify_embed.add_field(name="Reason", value=cancel_reason, inline=False)
                notify_embed.add_field(
                    name="Note",
                    value="If you believe this is an error, please contact an administrator.",
                    inline=False
                )
                
                await notifications_channel.send(f"{user.mention}", embed=notify_embed)
        
        await interaction.response.send_message("✅ Ticket cancelled successfully!", ephemeral=True)


class TicketButtonsView(discord.ui.View):
    def __init__(self, bot, user_id, username, item_name, item_price, wallet, timestamp):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.username = username
        self.item_name = item_name
        self.item_price = item_price
        self.wallet = wallet
        self.timestamp = timestamp
    
    @discord.ui.button(label="✅ Mark as Delivered", style=discord.ButtonStyle.success, custom_id="delivered")
    async def delivered_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update ticket embed
        embed = interaction.message.embeds[0]
        embed.color = 0x00ff00
        embed.set_field_at(
            len(embed.fields) - 1,
            name="✅ Status",
            value=f"Delivered by {interaction.user.mention}\nCompleted at: {strftime('%Y-%m-%d %H:%M:%S', gmtime())}",
            inline=False
        )
        
        # Remove buttons
        await interaction.message.edit(embed=embed, view=None)
        
        # Notify user in notifications channel
        notifications_channel = self.bot.get_channel(NOTIFICATIONS_CHANNEL_ID)
        if notifications_channel:
            user = self.bot.get_user(self.user_id)
            if user:
                notify_embed = discord.Embed(
                    title="✅ Reward Delivered!",
                    description=f"Your purchase has been successfully delivered!",
                    color=0x00ff00
                )
                notify_embed.add_field(name="Item", value=self.item_name, inline=True)
                notify_embed.add_field(name="Price", value=f"{self.item_price} {MONEY_PREFIX}", inline=True)
                notify_embed.add_field(name="Wallet", value=f"`{self.wallet}`", inline=False)
                notify_embed.add_field(
                    name="🎉 Thank you!",
                    value="Your reward has been sent to your game wallet. Enjoy!",
                    inline=False
                )
                notify_embed.set_footer(text=f"Processed by: {interaction.user}")
                
                await notifications_channel.send(f"{user.mention}", embed=notify_embed)
        
        await interaction.response.send_message("✅ Ticket marked as delivered and user notified!", ephemeral=True)
    
    @discord.ui.button(label="❌ Cancel Ticket", style=discord.ButtonStyle.danger, custom_id="cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show modal for cancellation reason
        modal = CancelModal(self.bot, interaction.message, self.user_id, self.username, self.item_name)
        await interaction.response.send_modal(modal)


class Marketplace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='shop')
    async def view_shop(self, ctx):
        """View all available items in the marketplace
        Usage: /shop
        """
        # Check if command is in the correct channel
        if ctx.channel.id != COMMANDS_CHANNEL_ID:
            await ctx.message.add_reaction("❌")
            await ctx.message.delete(delay=3)
            return
        
        # Get all available items
        items = list(mongo_client.db.marketplace_items.find({"available": True}))
        
        if not items:
            embed = discord.Embed(
                title="🛒 Marketplace",
                description="No items available at the moment. Check back later!",
                color=0xff9900
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🛒 Marketplace - Available Items",
            description="Use `/buy \"Item Name\"` to purchase an item",
            color=0x00ff00
        )
        
        for item in items:
            embed.add_field(
                name=f"{item['name']} - {item['price']} {MONEY_PREFIX}",
                value=item.get('description', 'No description'),
                inline=False
            )
        
        embed.set_footer(text=f"Your balance: Use /balance to check")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='buy')
    async def buy_item(self, ctx, *, item_name: str):
        """Buy an item from the marketplace
        Usage: /buy Item Name
        """
        # Check if command is in the correct channel
        if ctx.channel.id != COMMANDS_CHANNEL_ID:
            await ctx.message.add_reaction("❌")
            await ctx.message.delete(delay=3)
            return
        
        user_id = ctx.author.id
        
        # Get item from database
        item = mongo_client.db.marketplace_items.find_one({"name": item_name})
        
        if not item:
            await ctx.send(f"❌ Item **{item_name}** not found in marketplace!")
            return
        
        if not item.get("available", True):
            await ctx.send(f"❌ Item **{item_name}** is currently unavailable!")
            return
        
        # Get user data
        user_data = await get_user_data(user_id)
        
        if not user_data:
            await ctx.send("❌ You don't have any money yet! Send some messages to earn coins.")
            return
        
        current_balance = user_data.get(MONEY_PREFIX.lower(), 0)
        item_price = item['price']
        
        # Check if user has enough money
        if current_balance < item_price:
            embed = discord.Embed(
                title="❌ Insufficient Funds",
                description=f"You need **{item_price} {MONEY_PREFIX}** to buy **{item_name}**",
                color=0xff0000
            )
            embed.add_field(
                name="Your Balance",
                value=f"{current_balance} {MONEY_PREFIX}",
                inline=True
            )
            embed.add_field(
                name="Missing",
                value=f"{item_price - current_balance} {MONEY_PREFIX}",
                inline=True
            )
            await ctx.send(embed=embed)
            return
        
        # Deduct money
        user_data[MONEY_PREFIX.lower()] = current_balance - item_price
        
        # Update Redis cache
        await redis_client.insert(f"user:{user_id}", dumps(user_data))
        
        # Store purchase in Redis temporarily (will be synced to MongoDB)
        from time import time
        current_timestamp = int(time())
        purchase_key = f"purchase:{user_id}:{current_timestamp}"
        timestamp_str = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        purchase_data = {
            "user_id": user_id,
            "username": str(ctx.author),
            "item_name": item_name,
            "item_price": item_price,
            "timestamp": timestamp_str,
            "new_balance": user_data[MONEY_PREFIX.lower()]
        }
        await redis_client.insert(purchase_key, dumps(purchase_data))
        # Set expiration to 30 days
        await redis_client.client.expire(purchase_key, 2592000)
        
        # Show modal to get game wallet
        modal = GameWalletModal(
            self.bot,
            user_id,
            str(ctx.author),
            item_name,
            item_price,
            user_data[MONEY_PREFIX.lower()],
            timestamp_str
        )
        await ctx.send(
            f"✅ Purchase successful! Please provide your Game Wallet to claim your reward.",
            view=discord.ui.View().add_item(
                discord.ui.Button(
                    label="� Enter Game Wallet",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"wallet_modal_{user_id}_{current_timestamp}"
                )
            )
        )
        
        # Wait for button click and show modal
        def check(interaction: discord.Interaction):
            return interaction.user.id == user_id and interaction.data.get("custom_id", "").startswith("wallet_modal_")
        
        try:
            interaction = await self.bot.wait_for("interaction", timeout=300.0, check=check)
            await interaction.response.send_modal(modal)
        except Exception:
            pass
        

    
    @commands.command(name='history')
    async def purchase_history(self, ctx):
        """View your purchase history
        Usage: /history
        """
        # Check if command is in the correct channel
        if ctx.channel.id != COMMANDS_CHANNEL_ID:
            await ctx.message.add_reaction("❌")
            await ctx.message.delete(delay=3)
            return
        
        user_id = ctx.author.id
        
        # Get user's purchase history (last 10 purchases)
        purchases = list(mongo_client.db.discord_marketplace_purchases.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(10))
        
        if not purchases:
            await ctx.send("📭 You haven't made any purchases yet! Use `/shop` to browse items.")
            return
        
        embed = discord.Embed(
            title="🧾 Your Purchase History",
            description="Your last 10 purchases",
            color=0x0099ff
        )
        
        for purchase in purchases:
            embed.add_field(
                name=f"{purchase['item_name']} - {purchase['item_price']} {MONEY_PREFIX}",
                value=f"Date: {purchase.get('timestamp', 'Unknown')}",
                inline=False
            )
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Marketplace(bot))