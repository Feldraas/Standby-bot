"""Punish users who repost memes."""

import logging

from nextcord import RawReactionActionEvent
from nextcord.ext.commands import Bot, Cog

from domain import Duration, Emoji, RoleName, Standby, Threshold, TimerType
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class Reposts(Cog):
    def __init__(self) -> None:
        self.standby = Standby()
        self.check_reposters.start()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        """Trigger when users adda REEPOSTER emoji react."""
        reemoji = uf.get_emoji(Emoji.REEPOSTER)
        reeposter = uf.get_role(RoleName.REEPOSTER)

        if not (
            isinstance(payload, RawReactionActionEvent) and payload.emoji == reemoji
        ):
            return
        logger.info(f"Reeposter emoji added to {reeposter}'s post")
        channel = self.standby.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        message_age = uf.utcnow() - message.created_at

        if message_age > Duration.REPOSTER / 3:
            logger.info("Message is too old - ignoring")
            return

        rees = 0
        for emoji in message.reactions:
            if emoji.emoji == reemoji:
                rees = emoji.count

        if rees >= Threshold.REEPOSTER:
            await message.author.add_roles(reeposter)
            exists = await self.standby.pg_pool.fetch(
                "SELECT * FROM tmers "
                f"WHERE ttype={TimerType.REPOST} AND usr_id = {message.author.id}",
            )

            if not exists:
                logger.info(f"Adding reeposter role to {reeposter}")
                expires = message.created_at + Duration.REPOSTER
                expires = expires.replace(microsecond=0, tzinfo=None)
                await self.standby.pg_pool.execute(
                    "INSERT INTO tmers (usr_id, expires, ttype) VALUES ($1, $2, $3)",
                    message.author.id,
                    expires,
                    TimerType.REPOST,
                )

    @uf.delayed_loop(seconds=60)
    async def check_reposters(self) -> None:
        """Check if a user's reposter status should be removed."""
        gtable = await self.standby.pg_pool.fetch(
            f"SELECT * FROM tmers WHERE ttype={TimerType.REPOST}",
        )
        for rec in gtable:
            timenow = uf.utcnow()
            if timenow.replace(tzinfo=None) <= rec["expires"]:
                continue

            logger.info("Reepost timer expired")
            user = await self.standby.guild.fetch_member(rec["usr_id"])
            reeposter = uf.get_role(RoleName.REEPOSTER)
            await user.remove_roles(reeposter)
            await self.standby.pg_pool.execute(
                f"DELETE FROM tmers WHERE tmer_id = {rec['tmer_id']};",
            )


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Reposts())
