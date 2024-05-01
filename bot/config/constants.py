import os
from datetime import timedelta
from enum import IntEnum, StrEnum
from pathlib import Path

import nextcord
from dotenv import load_dotenv
from pytz import timezone

load_dotenv(".env.debug")

# Uncategorized
BOT_TZ = timezone(os.getenv("TZ", default="UTC"))
VALID_TEXT_CHANNEL = nextcord.TextChannel | nextcord.VoiceChannel | nextcord.Thread
EMPTY_STRING = "\u200b"
EMPTY_STRING_2 = "᲼"


class ID(IntEnum):
    GUILD = int(os.getenv("GUILD_ID"))
    BOT = int(os.getenv("BOT_ID"))
    STARBOARD = int(os.getenv("STARBOARD_ID"))
    ERROR_CHANNEL = int(os.getenv("ERROR_CHANNEL_ID"))
    GENERAL = int(os.getenv("GENERAL_ID"))
    GIVEAWAYS = int(os.getenv("GIVEAWAYS_ID"))
    TICKETS = int(os.getenv("TICKETS_ID"))
    RULES_MESSAGE = int(os.getenv("RULES_MESSAGE_ID"))
    BOT_SPAM = int(os.getenv("BOT_SPAM_ID"))
    FEL = 235055132843180032
    DER = 295553857054834690
    JORM = 168350377824092160
    DARKNESS = 238021076406370304
    AIRU = 378272190782504960
    ANA = 421039678481891348
    KROSS = 255653858095661057


class Token(StrEnum):
    BOT = os.getenv("BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class URL(StrEnum):
    DATABASE = os.getenv("DATABASE_URL")
    GINNY_TRANSPARENT = os.getenv("GINNY_TRANSPARENT_URL")
    GINNY_WHITE = os.getenv("GINNY_WHITE_URL")
    INVITE = "https://discord.gg/x7nsqEj"
    GITHUB_STATIC = (
        "https://raw.githubusercontent.com/Feldraas/Standby-bot/main/static/"
    )
    GITHUB_COMMITS = "https://api.github.com/repos/Feldraas/Standby-bot/commits/main"
    LOCAL_STATIC = str(Path(__file__).parent.parent.parent / "static")
    WARFRAME_MODS = (
        "https://raw.githubusercontent.com/"
        "WFCD/warframe-items/master/data/json/Mods.json"
    )


class ChannelName(StrEnum):
    GENERAL = "general"
    OFFERS = "offers"
    GIVEAWAYS = "giveaways"
    LOGS = "mod-log"
    RULES = "getting-started"
    ERRORS = "maintenance-channel"
    MOD_CHAT = "mod-chat"
    ALLIANCE_MOD_CHAT = "alliance-mod-chat"
    STARBOARD = "starboard"
    EVENTS = "events"
    EVENT_SUBMISSIONS = "event-submissions"
    CLAIMABLE = "ticket-channel"
    TICKETS_LOG = "tickets-log"

    @classmethod
    def no_response_channel_names(cls):
        return [
            cls.MOD_CHAT,
            cls.RULES,
            cls.GIVEAWAYS,
            cls.ALLIANCE_MOD_CHAT,
            cls.STARBOARD,
            cls.EVENTS,
            cls.EVENT_SUBMISSIONS,
        ]


class CategoryName(StrEnum):
    CLAIMABLE_TICKETS = "Talk to mods"
    ACTIVE_TICKETS = "Active tickets"
    RESOLVED_TICKETS = "Resolved tickets"


class RoleName(StrEnum):
    REEPOSTER = "REE-poster"
    BIRTHDAY = "Birthday Haver"
    MOD = "Moderator"
    GUIDE = "Guides of the Void"
    UPDATE_SQUAD = "UpdateSquad"
    VFTV = "Vie for the Void"
    OFFERS = "Offers"

    @classmethod
    def mod_role_names(cls):
        return [cls.MOD, cls.GUIDE]

    @classmethod
    def prio_role_names(cls):
        return [cls.UPDATE_SQUAD, cls.VFTV]

    @classmethod
    def descriptions(cls):
        return {
            cls.OFFERS: f"News about free or discounted games in #{ChannelName.OFFERS}",
            cls.UPDATE_SQUAD: "Get notified about server changes, giveaways, "
            "events, polls etc",
        }


class Permissions(IntEnum):
    MODS_AND_GUIDES = nextcord.Permissions(kick_members=True).value
    MODS_ONLY = nextcord.Permissions(ban_members=True).value
    MANAGE_EMOJIS = nextcord.Permissions(manage_emojis=True).value


class TimerType(IntEnum):
    REMINDER = 1
    GIVEAWAY = 2
    REPOST = 3
    ROULETTE = 4
    BURGER = 5


class Color(IntEnum):
    SOFT_RED = 0xCD6D6D
    STARBOARD = 0xFFAC33
    DARK_BLUE = 0x00008B
    DARK_ORANGE = 0xFF5E13
    PALE_GREEN = 0xBCF5BC
    PALE_YELLOW = 0xFDFF96
    GREY = 0x6A6866
    PALE_BLUE = 0xADD8E6
    LIGHT_BLUE = 0x1F75FE
    VIE_PURPLE = 0xA569BD


class Duration:
    ROULETTE_TIMEOUT = timedelta(minutes=30)
    BURGER_TIMEOUT = timedelta(weeks=1)
    REPOSTER = timedelta(days=1)


class Threshold(IntEnum):
    STARBOARD = 4
    REEPOSTER = 4
    PREDICTIONS = 5


class Format(StrEnum):
    YYYYMMDD = "%Y-%m-%d"
    YYYYMMDD_HHMMSS = "%Y-%m-%d %H:%M:%S"
    YYYYMMDD_HHMMSSZ = "%Y-%m-%dT%H:%M:%S%z"


class Emoji(StrEnum):
    REEPOSTER = "FEELSREEE"
