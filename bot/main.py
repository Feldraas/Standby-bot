"""Activate the bot."""

import logging
import os

from domain import Format, Standby
from postgres.setup import init_connection

ENV = os.getenv("ENV")

logging.basicConfig(
    level=logging.DEBUG if ENV == "dev" else logging.INFO,
    format=Format.LOGGING_DEV if ENV == "dev" else Format.LOGGING,
    datefmt=Format.YYYYMMDD_HHMMSS,
)
logging.getLogger("nextcord").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger("main")
logger.info(f"Running in {ENV}")

standby = Standby()


@standby.bot.event
async def on_ready() -> None:
    """Startup preparations."""
    standby.store_guild()
    await standby.set_status("Have a nice day!")
    await standby.recreate_views()
    await standby.announce()

    logger.info("Bot ready!")


standby.load_cogs()
standby.bot.loop.run_until_complete(init_connection())
standby.bot.run(standby.token)
