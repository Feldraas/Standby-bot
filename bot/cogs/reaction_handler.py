"""Monitor the server for user reactions."""

from nextcord import RawReactionActionEvent
from nextcord.ext.commands import Bot, Cog

from cogs.services import urban_handler
from domain import Standby


class ReactionHandler(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        """Called when a user adds a reaction."""
        await urban_handler(payload)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(ReactionHandler())
