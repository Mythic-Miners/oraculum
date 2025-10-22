from os import environ


"""
========== ENVIRONMENT VARIABLES ==========
"""
DISCORD_TOKEN = environ["DISCORD_TOKEN"]
REDIS_CLOUD_URI = environ["REDIS_CLOUD_URI"]
MONGODB_URI = environ["MONGODB_URI"]

"""
========== CONSTANTS ==========
"""
# Leveling
XP_POINTS_PREFIX = "EP"
XP_POINTS_NAME = "Engagement Points"
LEVEL_PREFIX = "EL"
LEVEL_NAME = "Engagement Level"
XP_FOR_MESSAGE = 2
XP_FOR_VOICE_MINUTE = 0.3
XP_FOR_REACT = 0.5
INITIAL_XP_FOR_LEVEL_UP = 100
XP_PERCENTAGE_INCREASE_PER_LEVEL = 0.05

# Economy
MONEY_PREFIX = "EC"
MONEY_NAME = "Engagement Coins"
STARTING_BALANCE = 0
DAILY_REWARD = 10
WEEKLY_REWARD = 70

# Emojis
XP_EMOJI = "✨"
MONEY_EMOJI = "🪙"
LEVEL_UP_EMOJI = "🎉"
STATS_EMOJI = "📊"

# Database
USERS_COLLECTION_NAME = "discord_users"