"""Starboard functionality."""

import asyncio
import logging

from nextcord import (
    Embed,
    Message,
    RawReactionActionEvent,
    RawReactionClearEmojiEvent,
    RawReactionClearEvent,
)

from db_integration import db_functions as db
from domain import ID, ChannelName, Color, Standby, Threshold
from utils import util_functions as uf

logger = logging.getLogger(__name__)

ReactionEvent = (
    RawReactionActionEvent | RawReactionClearEmojiEvent | RawReactionClearEvent
)
starboard_lock = asyncio.Lock()
standby = Standby()


async def get_starboard_message(message_id: int) -> Message:
    """Get a starboard message.

    Args:
        message_id (int): ID of the message that was added to
            the starboard

    Returns:
        Message: The corresponding starboard message.
    """
    record = await standby.pg_pool.fetchrow(
        f"SELECT * FROM starboard WHERE msg_id = {message_id};",
    )
    starboard_channel = uf.get_channel(ChannelName.STARBOARD)
    return await starboard_channel.fetch_message(record["sb_id"])


def starboard_embed(message: Message, stars: int) -> Embed:
    """Create an Embed for the starboard.

    Args:
        message (Message): Message to create Embed from
        stars (int): Number of stars currently on the message

    Returns:
        Embed: Embed containing relevant data fields.
    """
    embed = Embed(color=Color.STARBOARD)
    if message.attachments:
        embed.set_image(url=message.attachments[0].url)
    content_msg = "[Link to message]"
    if len(message.content) > 0:
        content_msg = message.content
        max_length = 950
        if len(content_msg) > max_length:
            content_msg = content_msg[0:max_length]
            content_msg += " [Click the link to see more]"
    if message.author.display_avatar:
        embed.set_thumbnail(url=message.author.display_avatar.url)
    embed.title = message.author.name
    embed.description = f"[{content_msg}]({message.jump_url})"
    embed.add_field(name="Channel", value=message.channel.mention)
    embed.add_field(name="Stars", value=stars)
    return embed


async def edit_stars(message: Message, stars: int) -> None:
    """Edit a starboard Embed with a new number of stars.

    Args:
        message (Message): Starboard message to edit
        stars (int): New number of stars
    """
    await message.edit(
        embed=message.embeds[0].set_field_at(1, name="Stars", value=stars),
    )


async def handle_added_star(event: RawReactionActionEvent) -> None:
    """Handler for when a star emoji is added to a message.

    Args:
        event (RawReactionActionEvent): Triggering event
    """
    logger.info("Star react added")
    chnl = standby.bot.get_channel(event.channel_id)
    msg = await chnl.fetch_message(event.message_id)
    await db.get_or_insert_usr(msg.author.id)
    stars = 0
    for emoji in msg.reactions:
        if emoji.emoji == "⭐":
            stars = emoji.count

    await starboard_lock.acquire()
    try:
        existcheck = await standby.pg_pool.fetchrow(
            f"SELECT sb_id FROM starboard WHERE msg_id = {event.message_id};",
        )
        sb_channel = standby.bot.get_channel(ID.STARBOARD)

        if stars >= Threshold.STARBOARD:  # add to SB
            if existcheck is None:
                sb_msg = await sb_channel.send(embed=starboard_embed(msg, stars))
                await standby.pg_pool.execute(
                    "INSERT INTO starboard (msg_id, sb_id, stars, usr_id) VALUES "
                    f"({event.message_id},{sb_msg.id},{stars},{msg.author.id});",
                )
            else:
                sb_msg = await sb_channel.fetch_message(existcheck["sb_id"])
                await edit_stars(sb_msg, stars)
                await standby.pg_pool.execute(
                    f"UPDATE starboard SET stars = {stars} "
                    f"WHERE msg_id = {event.message_id};",
                )
        elif existcheck is not None:
            sb_msg = await sb_channel.fetch_message(existcheck["sb_id"])
            await sb_msg.delete()
            await standby.pg_pool.execute(
                f"DELETE FROM starboard WHERE msg_id = {event.message_id};",
            )
    except Exception:
        logger.exception("Unexpected error")
    finally:
        starboard_lock.release()


async def handle_cleared_stars(event: RawReactionClearEvent) -> None:
    """Handler for when all star emojis are removed from a message.

    Args:
        event (RawReactionActionEvent): Triggering event
    """
    msg = await get_starboard_message(event.message_id)
    if msg is None:
        return
    await starboard_lock.acquire()
    try:
        await msg.delete()
        await standby.pg_pool.execute(
            f"DELETE FROM starboard WHERE msg_id = {event.message_id};",
        )
    except Exception:
        logger.exception("Unexpected error")
    finally:
        starboard_lock.release()


async def starboard_handler(event: ReactionEvent) -> None:
    """Dispatch star reaction events.

    Args:
        event (ReactionEvent): Triggering event
    """
    if isinstance(event, RawReactionActionEvent) and event.emoji.name == "⭐":
        await handle_added_star(event)

    elif isinstance(event, RawReactionClearEvent) or (
        isinstance(event, RawReactionClearEmojiEvent) and event.emoji.name == "⭐"
    ):
        await handle_cleared_stars(event)
