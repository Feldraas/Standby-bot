import re
from datetime import datetime as dt

from nextcord.ext.commands import Cog

from cogs.error_handler import unhandled_error_embed
from config.constants import *
from db_integration import db_functions as db
from utils import util_functions as uf
from utils.regex import (
    RegexResponse,
    WednesdayResponse,
    regex_responses,
    wednesday_responses,
)

last_messages = {}


def get_response_command(message):  # noqa: C901
    for resp in regex_responses + wednesday_responses:
        if message.channel.name in NO_RESPONSE_CHANNELS and not resp.prio:
            continue
        if not re.search(resp.trigger, message.content, resp.flags):
            continue
        if not resp.accepts(message):
            continue

        if type(resp) is RegexResponse:
            return resp.response

        if type(resp) is WednesdayResponse:

            async def resp_command(bot, msg, resp=resp):  # noqa: ARG001
                if dt.now().weekday() == resp.trigger_day:
                    await msg.channel.send(resp.response)
                    scream = 10 * resp.a
                    if resp.a != resp.a.upper():
                        scream += 10 * resp.a.upper()
                    scream += "**" + 5 * resp.a.upper() + "**"
                    if resp.a == "א":
                        scream = scream[:-2] + "ה**"
                    await msg.channel.send(scream)
                else:
                    await msg.channel.send(resp.wrong_day_response)

            return resp_command
    return None


class MessageHandler(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not isinstance(message.channel, VALID_TEXT_CHANNEL):
            await db.log(
                self.bot,
                f"Unexpected message in channel {message.channel} "
                f"of type {message.channel.type}",
            )
            return
        if message.content == "":
            return
        response_command = get_response_command(message)

        if response_command:
            try:
                await response_command(self.bot, message)
            except Exception as e:
                await db.log(
                    self.bot,
                    "Error when executing regex command "
                    f"{response_command.__name__}(): {e}",
                )
                if message.guild.id == GUILD_ID:
                    channel = uf.get_channel(message.guild, ERROR_CHANNEL_NAME)
                    if channel is not None:
                        await channel.send(
                            embed=unhandled_error_embed(
                                message.content, message.channel, e
                            )
                        )
                    else:
                        await db.log(self.bot, "Could not find error channel")
            return

        if (
            last_messages.get(message.channel, (None, None))[0]
            == message.content.lower()
        ):
            if (
                "<:BlobWave:" not in message.content
                and message.author != last_messages[message.channel][1]
            ):
                await message.channel.send(message.content)
                last_messages.pop(message.channel)
        else:
            last_messages[message.channel] = (message.content, message.author)


def setup(bot):
    bot.add_cog(MessageHandler(bot))
