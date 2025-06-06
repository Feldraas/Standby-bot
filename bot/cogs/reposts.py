"""Punish users who repost memes."""

import logging
from datetime import timedelta

from nextcord import RawReactionActionEvent
from nextcord.ext.commands import Bot, Cog

from domain import Standby
from utils import util_functions as uf

logger = logging.getLogger(__name__)

DURATION = timedelta(hours=8)
THRESHOLD = 4
EMOJI = "FEELSREEE"
ROLE = "REE-poster"


class Reposts(Cog):
    def __init__(self) -> None:
        self.standby = Standby()
        self.check_reposters.start()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        """Trigger when users add a REEPOSTER emoji react."""
        reemoji = uf.get_emoji(EMOJI)
        reeposter = uf.get_role(ROLE)

        if not (
            isinstance(payload, RawReactionActionEvent) and payload.emoji == reemoji
        ):
            return
        logger.info(f"Reeposter emoji added to {reeposter}'s post")
        channel = self.standby.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        message_age = uf.utcnow() - message.created_at

        if message_age > DURATION / 3:
            logger.info("Message is too old - ignoring")
            return

        rees = 0
        for emoji in message.reactions:
            if emoji.emoji == reemoji:
                rees = emoji.count

        if rees < THRESHOLD:
            return

        await message.author.add_roles(reeposter)
        expires = message.created_at + DURATION
        expires = expires.replace(microsecond=0, tzinfo=None)

        await self.standby.pg_pool.execute(
            f"""
            INSERT INTO
                {self.standby.schema}.repost (user_id, message_id, expires_at)
            VALUES
                ($1, $2, $3)
            ON CONFLICT ON CONSTRAINT repost_pkey
                DO NOTHING
            """,
            message.author.id,
            message.id,
            expires,
        )

    @uf.delayed_loop(minutes=1)
    async def check_reposters(self) -> None:
        """Check if a user's reposter status should be removed."""
        logger.info("Checking reposts")
        records = await self.standby.pg_pool.fetch(f"""
            SELECT
                user_id, message_id
            FROM
                {self.standby.schema}.repost
            WHERE
                expires_at < NOW()
                AND NOT processed
            """)
        for rec in records:
            logger.info("Repost timer expired - removing role")
            user = await self.standby.guild.fetch_member(rec["user_id"])
            reeposter = uf.get_role(ROLE)
            await user.remove_roles(reeposter)
            await self.standby.pg_pool.execute(f"""
                UPDATE {self.standby.schema}.repost
                SET
                    processed = TRUE
                WHERE
                    user_id = {rec["user_id"]}
                    AND message_id = {rec["message_id"]}
                """)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Reposts())
