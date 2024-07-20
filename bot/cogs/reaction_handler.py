"""Monitor the server for user reactions."""

from nextcord import (
    RawReactionActionEvent,
    RawReactionClearEmojiEvent,
    RawReactionClearEvent,
)
from nextcord.ext.commands import Bot, Cog

from cogs.giveaways import giveaway_handler
from cogs.services import urban_handler
from domain import Standby
from utils.starboard import starboard_handler


class ReactionHandler(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        """Called when a user adds a reaction."""
        await starboard_handler(payload)
        await giveaway_handler(payload)
        await urban_handler(payload)

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent) -> None:
        """Called when a user removes a reaction."""
        await starboard_handler(payload)

    @Cog.listener()
    async def on_raw_reaction_clear(self, payload: RawReactionClearEvent) -> None:
        """Called when all reactions are cleared from a message."""
        await starboard_handler(payload)

    @Cog.listener()
    async def on_raw_reaction_clear_emoji(
        self,
        payload: RawReactionClearEmojiEvent,
    ) -> None:
        """Called when all reactions of a certain emoji are cleared."""
        await starboard_handler(payload)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(ReactionHandler())
