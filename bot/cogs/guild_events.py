from nextcord.ext.commands import Cog

from db_integration import db_functions as db
from domain import Standby


class GuildEvents(Cog):
    def __init__(self):
        self.standby = Standby()

    @Cog.listener()
    async def on_guild_join(self, guild):
        await db.ensure_guild_existence(guild.id)

    @Cog.listener()
    async def on_guild_update(self, before, after):  # noqa: ARG002
        await db.ensure_guild_existence(after.id)


def setup(bot):
    bot.add_cog(GuildEvents())
