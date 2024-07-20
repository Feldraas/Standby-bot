import importlib
import json
import logging
import os
from datetime import datetime as dt
from datetime import timedelta
from pathlib import Path

import aiohttp
import nextcord
from nextcord import Game
from sqlalchemy import create_engine, text

from config.domain import BOT_TZ, ID, URL, Format

logger = logging.getLogger(__name__)


def load_cogs(bot):
    logger.info("Loading cogs")
    for file in Path().glob("bot/cogs/*.py"):
        bot.load_extension(f"cogs.{file.stem}")


async def set_status(bot, status):
    await bot.change_presence(activity=Game(name=status))


async def announce(bot):
    channel = bot.get_channel(ID.ERROR_CHANNEL)
    if not channel:
        logger.error("Could not find error channel")
        return

    logger.info("Fetching commit history")
    async with aiohttp.ClientSession() as cs, cs.get(URL.GITHUB_COMMITS) as r:
        data = await r.json()
        time_now = dt.now().astimezone(BOT_TZ)
        commit_time = dt.strptime(
            data["commit"]["committer"]["date"], Format.YYYYMMDD_HHMMSSZ
        ).astimezone(BOT_TZ)
        time_past = time_now - timedelta(minutes=15)
        if time_past < commit_time:
            author = data["author"]["login"]
            message = data["commit"]["message"]
            link = data["html_url"]
            reason = f"commit from {author} with message `{message}`. Link: <{link}>"
        else:
            reason = "Heroku restart or crash."
    reboot_message = f"Reboot complete. Caused by {reason}"
    await channel.send(reboot_message)


async def reconnect_buttons(bot):
    logger.info("Checking buttons")
    guild = bot.get_guild(ID.GUILD)
    buttons = await bot.pg_pool.fetch("SELECT * FROM buttons")
    for button in buttons:
        try:
            channel = await bot.fetch_channel(button["channel_id"])
            message = await channel.fetch_message(button["message_id"])
            if len(message.components) == 0:
                raise nextcord.errors.NotFound  # noqa: TRY301
        except nextcord.errors.NotFound:
            logger.info("Deleting record for deleted message button")
            await bot.pg_pool.execute(
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
            view = create_view(button["type"], bot=bot, guild=guild, **params)
            await message.edit(view=view)


def create_view(view_type, **params):
    package_name, view_class_name = view_type.split(" ")
    package = importlib.import_module(package_name)
    view_class = getattr(package, view_class_name)
    return view_class(**params)


class DBHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__()
        self.formatter = logging.Formatter(
            fmt="%(asctime)s | " + Format.LOGGING,
            datefmt=Format.YYYYMMDD_HHMMSS,
        )
        self.engine = create_engine(
            URL.DATABASE.replace("postgres://", "postgresql://")
        )
        self.setLevel(logging.WARNING)
        self.set_name("DBHandler")

    def emit(self, record):
        self.format(record)
        query = f"""
        INSERT INTO logs(timestamp, module, function, message)
        VALUES (
            '{record.asctime}',
            '{record.name}',
            '{record.funcName}',
            '{record.message.replace("'", "''")}')
        """
        with self.engine.connect() as con:
            con.execute(text(query))
            con.commit()


def setup_logging():
    debug = os.getenv("DEBUG")
    stream_handler = logging.StreamHandler()
    stream_handler.set_name("stream")
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format=Format.LOGGING,
        handlers=[stream_handler, DBHandler()],
    )
    logging.getLogger("nextcord").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
