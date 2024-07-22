"""Voice related features."""

import logging

from nextcord import Member, VoiceChannel, VoiceState
from nextcord.ext.commands import Bot, Cog

from domain import Standby
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class Voice(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState,
    ) -> None:
        """Gives the user a pinglable role matching their voice channel.

        Called any time a member's voice state changes.
        """
        if before.channel == after.channel:
            return

        if before.channel:
            role = uf.get_role(before.channel.name)
            if role:
                await member.remove_roles(role)

        if after.channel:
            role = uf.get_role(after.channel.name)
            if not role:
                role = await member.guild.create_role(
                    name=after.channel.name,
                    mentionable=True,
                )
            await member.add_roles(role)

    @Cog.listener()
    async def on_guild_channel_update(
        self,
        before: VoiceChannel,
        after: VoiceChannel,
    ) -> None:
        """Rename a voice channel's associated role.

        Called any time a voice channel is updated.
        """
        if isinstance(after, VoiceChannel):
            logger.info(f"Voice channel renamed from {before.name} to {after.name}")
            role = uf.get_role(before.name)
            if role:
                logger.info("Renaming voice channel role")
                await role.edit(name=after.name)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: VoiceChannel) -> None:
        """Delete a voice channel's role when it is deleted.

        Called any time a channel is deleted.
        """
        if not isinstance(channel, VoiceChannel):
            return

        logger.info(f"Voice channel {channel.name} deleted")
        role = uf.get_role(channel.name)
        if role:
            logger.info(f"Deleting voice channel role for {channel.name}")
            await role.delete()


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Voice())
