import nextcord
from nextcord.ext import commands
from settings import *
import aiohttp
from datetime import datetime, timedelta
from utils.util_functions import *

persistent_buttons = []


class Startup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def load_cogs(bot):
    for filename in os.listdir("bot/cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            bot.load_extension(f"cogs.{filename[:-3]}")


async def set_status(bot, status):
    await bot.change_presence(activity=nextcord.Game(name=status))


async def log_restart_reason(bot):
    channel = bot.get_channel(ERROR_CHANNEL_ID)
    if not channel:
        channel = bot.get_channel(740944936991457431)
    if channel:
        reason_found = "unkown reason"
        async with aiohttp.ClientSession() as cs:
            async with cs.get(
                "https://api.github.com/repos/Derevin/Standby-bot/commits/main"
            ) as r:
                data = await r.json()
                timenow = datetime.now().astimezone(BOT_TZ)
                format = "%Y-%m-%dT%H:%M:%S%z"
                dt_commit_time = datetime.strptime(
                    data["commit"]["committer"]["date"], format
                ).astimezone(BOT_TZ)
                timepast = timenow - timedelta(minutes=15)
                if timepast < dt_commit_time:
                    author = data["commit"]["committer"]["name"]
                    message = data["commit"]["message"]
                    link = data["html_url"]
                    reason_found = (
                        f"commit from {author} with message `{message}`. Link: <{link}>"
                    )
                else:
                    reason_found = "Heroku restart or crash (most likely)."

        await channel.send(f"Reboot complete. Caused by {reason_found}")


async def reconnect_buttons(bot):

    guild = await bot.fetch_guild(GUILD_ID)

    buttons = await bot.pg_pool.fetch(f"SELECT * FROM buttons")
    for button in buttons:
        try:
            channel = await bot.fetch_channel(button["channel_id"])
            message = await channel.fetch_message(button["message_id"])
        except nextcord.errors.NotFound:
            await bot.pg_pool.execute(
                f"DELETE from buttons WHERE channel_id = {button['channel_id']} AND message_id = {button['message_id']}"
            )
        else:
            view = createView(button["type"], channel)
            await message.edit(view=view)


def createView(type_, channel):
    if type_ == "open ticket":
        from cogs.tickets import OpenTicketButton

        return OpenTicketButton()

    elif type_ == "resolved ticket":
        from cogs.tickets import ResolvedTicketButton, RESOLVED_TICKETS_CAT_NAME

        return ResolvedTicketButton(
            disabled=channel.category.name != RESOLVED_TICKETS_CAT_NAME
        )

    return None


def setup(bot):
    bot.add_cog(Startup(bot))