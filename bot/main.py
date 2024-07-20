import logging
import os

from nextcord import Intents
from nextcord.ext.commands import Bot

from config import startup
from config.domain import Token
from db_integration import db_functions as db

bot = Bot(intents=Intents.all(), case_insensitive=True)

startup.setup_logging()
logger = logging.getLogger("main")


DEBUG = os.getenv("DEBUG", default=False)
if DEBUG:
    logger.info("Running in debug")
else:
    logger.info("Running in prod")


@bot.event
async def on_ready():
    await startup.set_status(bot, "Have a nice day!")

    await startup.reconnect_buttons(bot)

    await startup.announce(bot)

    logger.info("Bot ready!")


startup.load_cogs(bot)

bot.loop.run_until_complete(db.init_connection(bot))

bot.run(Token.BOT)
