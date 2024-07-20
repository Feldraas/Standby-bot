import asyncio
import logging

from nextcord import (
    Embed,
    RawReactionActionEvent,
    RawReactionClearEmojiEvent,
    RawReactionClearEvent,
)

from config.domain import ID, Color, Threshold
from db_integration import db_functions as db

logger = logging.getLogger(__name__)
starboard_lock = asyncio.Lock()


async def get_starboard_msg(bot, msg_id):
    return await bot.pg_pool.fetchrow(
        f"SELECT * FROM starboard WHERE msg_id = {msg_id};"
    )


async def get_starboard_sbid(bot, msg_id):
    return await bot.pg_pool.fetchrow(
        f"SELECT sb_id FROM starboard WHERE msg_id = {msg_id};"
    )


def starboard_embed(message, stars) -> Embed:
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


async def edit_stars(message, stars):
    return await message.edit(
        embed=message.embeds[0].set_field_at(1, name="Stars", value=stars)
    )


async def starboard_handler(bot, payload):  # noqa: C901, PLR0912, PLR0915
    if isinstance(payload, RawReactionActionEvent) and payload.emoji.name == "⭐":
        logger.info("Star react added")
        chnl = bot.get_channel(payload.channel_id)
        msg = await chnl.fetch_message(payload.message_id)
        await db.get_or_insert_usr(bot, msg.author.id, payload.guild_id)
        stars = 0
        sb_channel = bot.get_channel(ID.STARBOARD)
        for emoji in msg.reactions:
            if emoji.emoji == "⭐":
                stars = emoji.count

        await starboard_lock.acquire()
        try:
            existcheck = await bot.pg_pool.fetchrow(
                f"SELECT sb_id FROM starboard WHERE msg_id = {payload.message_id};"
            )

            if stars >= Threshold.STARBOARD:  # add to SB
                if existcheck is None:
                    sb_msg = await sb_channel.send(embed=starboard_embed(msg, stars))
                    await bot.pg_pool.execute(
                        "INSERT INTO starboard (msg_id, sb_id, stars, usr_id) VALUES "
                        f"({payload.message_id},{sb_msg.id},{stars},{msg.author.id});"
                    )
                else:
                    sb_msg = await sb_channel.fetch_message(existcheck["sb_id"])
                    await edit_stars(sb_msg, stars)
                    await bot.pg_pool.execute(
                        f"UPDATE starboard SET stars = {stars} "
                        f"WHERE msg_id = {payload.message_id};"
                    )
            elif existcheck is not None:
                sb_msg = await sb_channel.fetch_message(existcheck["sb_id"])
                await sb_msg.delete()
                await bot.pg_pool.execute(
                    f"DELETE FROM starboard WHERE msg_id = {payload.message_id};"
                )
        except Exception:
            logger.exception("Unexpected error")
        finally:
            starboard_lock.release()

    elif isinstance(payload, RawReactionClearEvent):
        # if exists in starboard, do something about it, otherwise don't care
        msg = await get_starboard_msg(bot, payload.message_id)
        if msg is not None:
            await starboard_lock.acquire()
            try:
                await msg.delete()
                await bot.pg_pool.execute(
                    f"DELETE FROM starboard WHERE msg_id = {payload.message_id};"
                )
            except Exception as e:
                await db.log(bot, f"Unexpected error: {e}")
            finally:
                starboard_lock.release()

    elif isinstance(payload, RawReactionClearEmojiEvent):
        if payload.emoji.name == "⭐":
            # if exists in starboard, do something about it, otherwise don't care
            msg = await get_starboard_msg(bot, payload.message_id)
            if msg is not None:
                await starboard_lock.acquire()
                try:
                    await msg.delete()
                    await bot.pg_pool.execute(
                        f"DELETE FROM starboard WHERE msg_id = {payload.message_id};"
                    )
                except Exception:
                    logger.exception("Unexpected error")
                finally:
                    starboard_lock.release()
