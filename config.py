import os
from dotenv import load_dotenv

# En production (Railway), les variables sont injectées directement dans l'environnement.
# load_dotenv est un no-op si .env est absent ; override=False garantit que les vars
# Railway ne sont jamais écrasées par un éventuel .env présent sur le serveur.
load_dotenv(override=False)

# Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# YouTube Data API v3
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")

# Twitch API
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_CHANNEL_NAME = os.getenv("TWITCH_CHANNEL_NAME")

# Salons Discord (IDs)
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID", "0"))
LEVEL_UP_CHANNEL_ID = int(os.getenv("LEVEL_UP_CHANNEL_ID", "0"))
AI_CHANNEL_ID = int(os.getenv("AI_CHANNEL_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))

# XP — paramètres du système de niveaux
XP_MIN_PAR_MESSAGE = 8
XP_MAX_PAR_MESSAGE = 15
XP_COOLDOWN_SECONDES = 60  # anti-farm : délai minimum entre deux gains d'XP

# Anti-spam — seuils de détection
SPAM_MAX_MESSAGES = 5       # nombre de messages maximum
SPAM_FENETRE_SECONDES = 5   # dans cette fenêtre de temps
SPAM_MUTE_DUREE = 300       # durée du mute automatique en secondes (5 min)
