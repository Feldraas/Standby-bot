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
from nextcord.ext.commands import Bot, Cog

from domain import ID, Color, Standby
from utils import util_functions as uf

logger = logging.getLogger(__name__)

ReactionEvent = (
    RawReactionActionEvent | RawReactionClearEmojiEvent | RawReactionClearEvent
)
STARBOARD_THRESHOLD = 4

starboard_lock = asyncio.Lock()
standby = Standby()


class Starboard(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @Cog.listener()
    async def on_raw_reaction_add(self, event: RawReactionActionEvent) -> None:
        """Called any time a user adds a reaction."""
        logger.debug("react")
        if event.emoji.name != "⭐":  # or event.user_id == event.message_id:
            return
        logger.debug("star")
        await starboard_lock.acquire()

        logger.debug("Star react added")
        channel = standby.bot.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)

        stars = next(emoji.count for emoji in message.reactions if emoji.emoji == "⭐")
        if stars < STARBOARD_THRESHOLD:
            starboard_lock.release()
            return

        if stars == STARBOARD_THRESHOLD:
            starboard = standby.bot.get_channel(ID.STARBOARD)
            starboard_message = await starboard.send(
                embed=starboard_embed(message, stars),
            )
            await record_starboard_message(message, starboard_message, stars)
            starboard_lock.release()
            return

        starboard_message = await get_starboard_message(message.id)

        await edit_stars(starboard_message, stars)
        await record_starboard_message(message, starboard_message, stars)

        starboard_lock.release()

    @Cog.listener()
    async def on_raw_reaction_remove(self, event: RawReactionActionEvent) -> None:
        """Called any time a user removes a reaction."""
        if event.emoji.name != "⭐":  # or event.user_id == event.message_id:
            return

        await starboard_lock.acquire()

        logger.debug("Star react removed")
        channel = standby.bot.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)

        stars = 0
        for emoji in message.reactions:
            if emoji.emoji == "⭐":
                stars = emoji.count

        if stars < STARBOARD_THRESHOLD - 1:
            starboard_lock.release()
            return

        starboard_message = await get_starboard_message(message.id)

        if stars == STARBOARD_THRESHOLD - 1:
            await starboard_message.delete()
            await delete_recorded_starboard_message(message.id)
            starboard_lock.release()
            return

        await edit_stars(starboard_message, stars)
        await record_starboard_message(message, starboard_message, stars)

        starboard_lock.release()

    @Cog.listener()
    async def on_raw_reaction_clear(self, event: RawReactionClearEvent) -> None:
        """Called when all reactions are cleared from a message."""
        async with starboard_lock:
            await clear_starboard_message(event.message_id)

    @Cog.listener()
    async def on_raw_reaction_clear_emoji(
        self,
        event: RawReactionClearEmojiEvent,
    ) -> None:
        """Called when all reactions of a certain emoji are cleared."""
        if event.emoji.name != "⭐":
            return

        async with starboard_lock:
            await clear_starboard_message(event.message_id)


async def get_starboard_message(message_id: int) -> Message:
    """Get a starboard message.

    Args:
        message_id (int): ID of the message that was added to
            the starboard

    Returns:
        Message: The corresponding starboard message.
    """
    starboard_id = await standby.pg_pool.fetchval(
        f"""
        SELECT
            starboard_id
        FROM
            {standby.schema}.starboard
        WHERE
            message_id = {message_id}
        """,
    )
    starboard_channel = uf.get_channel("starboard")
    return await starboard_channel.fetch_message(starboard_id)


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


async def record_starboard_message(
    original_message: Message,
    starboard_message: Message,
    stars: int,
) -> None:
    """Add or update an entry to the starboard table."""
    standby = Standby()
    await standby.pg_pool.execute(f"""
        INSERT INTO
            {standby.schema}.starboard (user_id, message_id, starboard_id, stars)
        VALUES
            (
                {original_message.author.id},
                {original_message.id},
                {starboard_message.id},
                {stars}
            )
        ON CONFLICT ON CONSTRAINT starboard_pkey DO UPDATE
        SET
            stars = {stars}
        """)


async def delete_recorded_starboard_message(original_message_id: int) -> None:
    """Remove the database entry for the provided message."""
    standby = Standby()
    await standby.pg_pool.execute(f"""
        DELETE FROM {standby.schema}.starboard
        WHERE
            message_id = {original_message_id}
        """)


async def edit_stars(message: Message | None, stars: int) -> None:
    """Edit a starboard Embed with a new number of stars.

    Args:
        message (Message): Starboard message to edit
        stars (int): New number of stars
    """
    await message.edit(
        embed=message.embeds[0].set_field_at(1, name="Stars", value=stars),
    )


async def clear_starboard_message(original_message_id: int) -> None:
    """Delete entry from the starboard table and starboard channel."""
    starboard_message = await get_starboard_message(original_message_id)
    await starboard_message.delete()
    await delete_recorded_starboard_message()


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Starboard())
