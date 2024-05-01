import importlib
import json
import os
from datetime import datetime as dt
from datetime import timedelta

import aiohttp
import nextcord
from nextcord import Game

from config.constants import BOT_TZ, ID, URL, Format
from db_integration import db_functions as db


def load_cogs(bot):
    for filename in os.listdir("bot/cogs"):
        if filename.endswith(".py"):
            bot.load_extension(f"cogs.{filename[:-3]}")


async def set_status(bot, status):
    await bot.change_presence(activity=Game(name=status))


async def log_restart_reason(bot):
    channel = bot.get_channel(ID.ERROR_CHANNEL)
    if not channel:
        await db.log(bot, "Could not find error channel")
        return
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
    await db.log(bot, reboot_message)


async def reconnect_buttons(bot):
    guild = bot.get_guild(ID.GUILD)
    buttons = await bot.pg_pool.fetch("SELECT * FROM buttons")
    for button in buttons:
        try:
            channel = await bot.fetch_channel(button["channel_id"])
            message = await channel.fetch_message(button["message_id"])
            if len(message.components) == 0:
                raise nextcord.errors.NotFound  # noqa: TRY301
        except nextcord.errors.NotFound:
            await bot.pg_pool.execute(
                f"DELETE from buttons WHERE channel_id = {button['channel_id']} "
                f"AND message_id = {button['message_id']}"
            )
        else:
            disabled = [
                child.disabled
                for component in message.components
                for child in component.children
            ]
            if all(disabled):
                continue

            params = json.loads(button["params"]) if button["params"] else {}
            view = create_view(button["type"], bot=bot, guild=guild, **params)
            await message.edit(view=view)


def create_view(view_type, **params):
    package_name, view_class_name = view_type.split(" ")
    package = importlib.import_module(package_name)
    view_class = getattr(package, view_class_name)
    return view_class(**params)
