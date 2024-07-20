import importlib
import json
import logging
import os
from datetime import datetime, timedelta
from enum import IntEnum, StrEnum
from pathlib import Path

import aiohttp
import nextcord
from asyncpg import Pool
from nextcord import Intents
from nextcord.ext.commands import Bot
from pytz import timezone

logger = logging.getLogger(__name__)

# Uncategorized
BOT_TZ = timezone(os.getenv("TZ", default="UTC"))
VALID_TEXT_CHANNEL = nextcord.TextChannel | nextcord.VoiceChannel | nextcord.Thread
EMPTY_STRING = "\u200b"
EMPTY_STRING_2 = "᲼"


class Standby:
    instance = None

    bot: Bot
    pg_pool: Pool
    token: str

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
            cls.instance.bot = Bot(intents=Intents.all(), case_insensitive=True)
            cls.instance.token = os.getenv("BOT_TOKEN")
        return cls.instance

    def load_cogs(self):
        for file in Path().glob("bot/cogs/*.py"):
            logger.info(f"Loading cog {file.stem}")
            self.bot.load_extension(f"cogs.{file.stem}")

    async def announce(self):
        channel = self.bot.get_channel(ID.ERROR_CHANNEL)
        if not channel:
            logger.error("Could not find error channel")
            return

        logger.info("Fetching commit history")
        async with aiohttp.ClientSession() as cs, cs.get(URL.GITHUB_COMMITS) as r:
            data = await r.json()
            time_now = datetime.now().astimezone(BOT_TZ)
            commit_time = datetime.strptime(
                data["commit"]["committer"]["date"], Format.YYYYMMDD_HHMMSSZ
            ).astimezone(BOT_TZ)
            time_past = time_now - timedelta(minutes=15)
            if time_past < commit_time:
                author = data["author"]["login"]
                message = data["commit"]["message"]
                link = data["html_url"]
                reason = (
                    f"commit from {author} with message `{message}`. Link: <{link}>"
                )
            else:
                reason = "Heroku restart or crash."
        reboot_message = f"Reboot complete. Caused by {reason}"
        await channel.send(reboot_message)

    def create_view(self, view_type, **params):
        package_name, view_class_name = view_type.split(" ")
        package = importlib.import_module(package_name)
        view_class = getattr(package, view_class_name)
        return view_class(**params)

    async def reconnect_buttons(self):
        logger.info("Checking buttons")
        guild = self.bot.get_guild(ID.GUILD)
        buttons = await self.pg_pool.fetch("SELECT * FROM buttons")
        for button in buttons:
            try:
                channel = await self.bot.fetch_channel(button["channel_id"])
                message = await channel.fetch_message(button["message_id"])
                if len(message.components) == 0:
                    raise nextcord.errors.NotFound  # noqa: TRY301
            except nextcord.errors.NotFound:
                logger.info("Deleting record for deleted message button")
                await self.pg_pool.execute(
                    f"DELETE from buttons WHERE channel_id = {button['channel_id']} "
                    f"AND message_id = {button['message_id']}"
                )
            else:
                logger.info(
                    f"Processing button for message {button['message_id']} "
                    f"in channel {button['channel_id']}"
                )
                disabled = [
                    child.disabled
                    for component in message.components
                    for child in component.children
                ]
                if all(disabled):
                    logger.info("All buttons disabled - ignoring")
                    continue

                logger.info("Reconnecting button")
                params = json.loads(button["params"]) if button["params"] else {}
                view = self.create_view(
                    button["type"], bot=self.bot, guild=guild, **params
                )
                await message.edit(view=view)

    async def set_status(self, status):
        await self.bot.change_presence(activity=nextcord.Game(name=status))


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
    BURGER_TIMEOUT = timedelta(minutes=1)
    REPOSTER = timedelta(days=1)


class Threshold(IntEnum):
    STARBOARD = 4
    REEPOSTER = 4
    PREDICTIONS = 5


class Format(StrEnum):
    YYYYMMDD = "%Y-%m-%d"
    YYYYMMDD_HHMMSS = "%Y-%m-%d %H:%M:%S"
    YYYYMMDD_HHMMSSZ = "%Y-%m-%dT%H:%M:%S%z"
    LOGGING = "%(levelname)s | %(name)s:%(lineno)s | %(funcName)s | %(message)s"
    LOGGING_DEBUG = f"%(asctime)s | {LOGGING}"


class Emoji(StrEnum):
    REEPOSTER = "FEELSREEE"
