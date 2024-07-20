import logging

from nextcord import RawReactionActionEvent
from nextcord.ext.commands import Cog

from config.domain import ID, Duration, Emoji, RoleName, Threshold, TimerType
from db_integration import db_functions as db
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class Reposts(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_reposters.start()

    def cog_unload(self):
        self.check_reposters.cancel()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild = await self.bot.fetch_guild(ID.GUILD)
        reemoji = uf.get_emoji(guild, Emoji.REEPOSTER)
        reeposter = uf.get_role(guild, RoleName.REEPOSTER)

        if not (
            isinstance(payload, RawReactionActionEvent) and payload.emoji == reemoji
        ):
            return
        logger.info(f"Reeposter emoji added to {reeposter}'s post")
        channel = self.bot.get_channel(payload.channel_id)
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
            await db.ensure_guild_existence(self.bot, message.guild.id)
            await db.get_or_insert_usr(self.bot, message.author.id, message.guild.id)
            await message.author.add_roles(reeposter)
            exists = await self.bot.pg_pool.fetch(
                "SELECT * FROM tmers "
                f"WHERE ttype={TimerType.REPOST} AND usr_id = {message.author.id}"
            )

            if not exists:
                logger.info(f"Adding reeposter role to {reeposter}")
                expires = message.created_at + Duration.REPOSTER
                expires = expires.replace(microsecond=0, tzinfo=None)
                await self.bot.pg_pool.execute(
                    "INSERT INTO tmers (usr_id, expires, ttype) VALUES ($1, $2, $3)",
                    message.author.id,
                    expires,
                    TimerType.REPOST,
                )

    @uf.delayed_loop(seconds=60)
    async def check_reposters(self):
        try:
            gtable = await self.bot.pg_pool.fetch(
                f"SELECT * FROM tmers WHERE ttype={TimerType.REPOST}"
            )
            for rec in gtable:
                timenow = uf.utcnow()
                if timenow.replace(tzinfo=None) <= rec["expires"]:
                    continue

                logger.info("Reepost timer expired")
                guild_id = await self.bot.pg_pool.fetchval(
                    f"SELECT guild_id FROM usr WHERE usr_id = {rec['usr_id']}"
                )
                guild = await self.bot.fetch_guild(guild_id)
                user = await guild.fetch_member(rec["usr_id"])
                reeposter = uf.get_role(guild, RoleName.REEPOSTER)
                await user.remove_roles(reeposter)
                await self.bot.pg_pool.execute(
                    f"DELETE FROM tmers WHERE tmer_id = {rec['tmer_id']};"
                )
        except AttributeError:
            logger.exception("Bot hasn't loaded yet - pg_pool doesn't exist")
        except Exception:
            logger.exception("Unknown exception")


def setup(bot):
    bot.add_cog(Reposts(bot))
