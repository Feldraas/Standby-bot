"""Standby class + various enums and constants."""

import importlib
import json
import logging
import os
from datetime import datetime, timedelta
from enum import Enum, IntEnum, StrEnum, auto
from pathlib import Path
from typing import Self

import aiohttp
import nextcord
from asyncpg import Pool
from nextcord import Guild, Intents
from nextcord.ext.commands import Bot
from nextcord.ui import View
from pytz import timezone

logger = logging.getLogger(__name__)

# Uncategorized
BOT_TZ = timezone(os.getenv("TZ", default="UTC"))
ValidTextChannel = nextcord.TextChannel | nextcord.VoiceChannel | nextcord.Thread
EMPTY_STRING = "\u200b"
EMPTY_STRING_2 = "᲼"


class Standby:
    """Singleton class wrapping the Bot instance.

    Holds a reference to the currently running Bot instance, as well as
    to the active Postgres connection pool. Can be instantiated at any
    time to obtain those references.
    """

    instance = None

    bot: Bot
    pg_pool: Pool
    guild: Guild
    token: str
    schema: str

    def __new__(cls) -> Self:
        """Instantiate the Bot object."""
        if cls.instance is None:
            cls.instance = super().__new__(cls)
            cls.instance.bot = Bot(intents=Intents.all(), case_insensitive=True)
            cls.instance.token = os.getenv("BOT_TOKEN")
        return cls.instance

    def load_cogs(self) -> None:
        """Load all cogs in the cogs/ directory.

        Most of the bot's functionality (slash commands etc.) is
        packaged in Cogs. Those need to be loaded to become available
        for use.
        """
        logger.info("Loading cogs")
        for file in Path().glob("bot/cogs/*.py"):
            self.bot.load_extension(f"cogs.{file.stem}")

    def store_guild(self) -> None:
        """Store a reference to the current guild."""
        self.guild = self.bot.get_guild(ID.GUILD)

    async def announce(self) -> None:
        """Announce that the bot has started running."""
        channel = self.bot.get_channel(ID.ERROR_CHANNEL)
        if not channel:
            logger.error("Could not find error channel")
            return

        logger.info("Fetching commit history")
        async with aiohttp.ClientSession() as cs, cs.get(URL.GITHUB_COMMITS) as r:
            data = await r.json()
            time_now = datetime.now().astimezone(BOT_TZ)
            commit_time = datetime.strptime(
                data["commit"]["committer"]["date"],
                Format.YYYYMMDD_HHMMSSZ,
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

    async def recreate_views(self) -> None:
        """Recreate all views.

        When the bot restarts, all previously created views stop
        functioning. Any view that needs to persist for longer than
        the bot's ~24-hour life cycle needs to be stored in the database
        and recreated on restart.
        """
        logger.debug("Checking views")

        from utils import util_functions as uf

        await uf.clean_view_table()

        records = await self.pg_pool.fetch(f"""SELECT * FROM {self.schema}.view""")
        for record in records:
            logger.debug(
                f"Processing button for message {record['message_id']} "
                f"in channel {record['channel_id']}",
            )
            channel = await self.bot.fetch_channel(record["channel_id"])
            message = await channel.fetch_message(record["message_id"])
            disabled = [
                child.disabled
                for component in message.components
                for child in component.children
            ]
            if all(disabled):
                logger.debug("All buttons disabled - ignoring")
                continue

            logger.debug("Recreating view")
            params = json.loads(record["params"])

            module = importlib.import_module(record["module"])
            view_class: type[View] = getattr(module, record["class"])

            await message.edit(view=view_class(params))

    async def set_status(self, status: str) -> None:
        """Set the bot's status message.

        Args:
            status (str): Status to set
        """
        await self.bot.change_presence(activity=nextcord.Game(name=status))


class ID(IntEnum):
    """Often occurring IDs and snowflakes (users, channels etc)."""

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


class URL(StrEnum):
    """Often occurring links and URLs."""

    DATABASE = os.getenv("DATABASE_URL")
    GINNY_TRANSPARENT = os.getenv("GINNY_TRANSPARENT_URL")
    GINNY_WHITE = os.getenv("GINNY_WHITE_URL")
    INVITE = "https://discord.gg/x7nsqEj"
    GITHUB_STATIC = (
        "https://raw.githubusercontent.com/Feldraas/Standby-bot/main/static/"
    )
    GITHUB_COMMITS = "https://api.github.com/repos/Feldraas/Standby-bot/commits/main"
    LOCAL_STATIC = str(Path(__file__).parent.parent / "static")
    WARFRAME_MODS = (
        "https://raw.githubusercontent.com/"
        "WFCD/warframe-items/master/data/json/Mods.json"
    )


class ChannelName(StrEnum):
    """Special channel names."""

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
    def no_response_channel_names(cls) -> list["ChannelName"]:
        """Channels where bot autoreplies should not trigger.

        Returns:
            list[ChannelName]: Names of excluded channels
        """
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
    """Often occurring channel category names."""

    CLAIMABLE_TICKETS = "Talk to mods"
    ACTIVE_TICKETS = "Active tickets"
    RESOLVED_TICKETS = "Resolved tickets"


class RoleName(StrEnum):
    """Often occuring role names."""

    REEPOSTER = "REE-poster"
    BIRTHDAY = "Birthday Haver"
    MOD = "Moderator"
    GUIDE = "Guides of the Void"
    UPDATE_SQUAD = "UpdateSquad"
    VFTV = "Vie for the Void"
    OFFERS = "Offers"

    @classmethod
    def mod_role_names(cls) -> list["RoleName"]:
        """Roles that have mod privileges.

        Returns:
            list[RoleName]: Role names
        """
        return [cls.MOD, cls.GUIDE]

    @classmethod
    def prio_role_names(cls) -> list["RoleName"]:
        """Roles that should show up first in dropdown menus.

        Returns:
            list[RoleName]: Role names
        """
        return [cls.UPDATE_SQUAD, cls.VFTV]

    @classmethod
    def descriptions(cls) -> dict["RoleName", str]:
        """Special descriptions for certain roles.

        Returns:
            list[RoleName]: Role names
        """
        return {
            cls.OFFERS: f"News about free or discounted games in #{ChannelName.OFFERS}",
            cls.UPDATE_SQUAD: "Get notified about server changes, giveaways, "
            "events, polls etc",
        }


class Permissions(IntEnum):
    """Permission types for various commands."""

    MODS_AND_GUIDES = nextcord.Permissions(kick_members=True).value
    MODS_ONLY = nextcord.Permissions(ban_members=True).value
    MANAGE_EMOJIS = nextcord.Permissions(manage_emojis=True).value


class TimerType(IntEnum):
    """Identifiers for different types of timers."""

    REMINDER = 1
    GIVEAWAY = 2
    REPOST = 3
    ROULETTE = 4
    BURGER = 5


class Color(IntEnum):
    """Color hexcodes."""

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
    """Durations for different events."""

    REPOSTER = timedelta(days=1)


class Threshold(IntEnum):
    """Thresholds for different events."""

    REEPOSTER = 4


class Format(StrEnum):
    """Format strings."""

    YYYYMMDD = "%Y-%m-%d"
    YYYYMMDD_HHMMSS = "%Y-%m-%d %H:%M:%S"
    YYYYMMDD_HHMMSSZ = "%Y-%m-%dT%H:%M:%S%z"
    LOGGING = "%(levelname)s | %(name)s:%(lineno)s | %(funcName)s | %(message)s"
    LOGGING_DEV = f"%(asctime)s | {LOGGING}"


class Emoji(StrEnum):
    """Special emoji names."""

    REEPOSTER = "FEELSREEE"


class SQLResult(Enum):
    """Result of executing an SQL query."""

    INSERT = auto()
    UPDATE = auto()
    DELETE = auto()
    NONE = auto()
