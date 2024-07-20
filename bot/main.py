import logging
import os

from db_integration import db_functions as db
from domain import Format, Standby

DEBUG = os.getenv("DEBUG") == "True"
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format=Format.LOGGING_DEBUG if DEBUG else Format.LOGGING,
    datefmt=Format.YYYYMMDD_HHMMSS,
)
logging.getLogger("nextcord").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger("main")
logger.info(f"Running in {'debug' if DEBUG else 'prod'}")
logger.info("Running in debug" if DEBUG else "Running in prod")


standby = Standby()


@standby.bot.event
async def on_ready():
    standby.store_guild()
    await standby.set_status("Have a nice day!")
    await standby.reconnect_buttons()
    await standby.announce()

    logger.info("Bot ready!")


standby.load_cogs()

standby.bot.loop.run_until_complete(db.init_connection())

standby.bot.run(standby.token)
