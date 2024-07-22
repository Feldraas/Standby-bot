"""Monitor changes to the guild (server)."""

from nextcord import Guild
from nextcord.ext.commands import Bot, Cog

from db_integration import db_functions as db
from domain import Standby


class GuildEvents(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @Cog.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        """Called when the bot joins a guild."""
        await db.ensure_guild_existence(guild.id)

    @Cog.listener()
    async def on_guild_update(self, before: Guild, after: Guild) -> None:  # noqa: ARG002
        """Called when the guild is updated."""
        await db.ensure_guild_existence(after.id)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(GuildEvents())
