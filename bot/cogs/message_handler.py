"""Monitor messages sent in the server."""

import logging
import re
from collections.abc import Callable
from datetime import datetime as dt

from nextcord import Message
from nextcord.ext.commands import Bot, Cog

from domain import ChannelName, Standby, ValidTextChannel
from utils.regex import (
    RegexResponse,
    WednesdayResponse,
    regex_responses,
    wednesday_responses,
)

logger = logging.getLogger(__name__)
last_messages = {}


def get_response_command(message: Message) -> Callable:  # noqa: C901
    """Check if the message should trigger a response.

    Args:
        message (Message): Message to check

    Returns:
        Callable: Function to trigger in response.
    """
    for resp in regex_responses + wednesday_responses:
        if (
            message.channel.name in ChannelName.no_response_channel_names()
            and not resp.prio
        ):
            continue
        if not re.search(resp.trigger, message.content, resp.flags):
            continue
        if not resp.accepts(message):
            continue

        if type(resp) is RegexResponse:
            return resp.response

        if type(resp) is WednesdayResponse:

            async def resp_command(
                msg: Message,
                resp: WednesdayResponse = resp,
            ) -> None:
                """Respond to a wednesday message."""
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
    def __init__(self) -> None:
        self.standby = Standby()

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """Called when a message is sent in the server."""
        # Skip bot messages and empty messages
        if message.author.bot:
            return
        if not isinstance(message.channel, ValidTextChannel):
            await logger.warning(
                f"Unexpected message in channel {message.channel} "
                f"of type {message.channel.type}",
            )
            return

        if message.content == "":
            return

        # Check for regex responses
        response_command = get_response_command(message)
        if response_command:
            try:
                await response_command(message)
            except Exception:
                logger.exception(
                    f"Error when executing regex command {response_command.__name__}()",
                )
            return

        # Check for repeated messages
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


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(MessageHandler())
