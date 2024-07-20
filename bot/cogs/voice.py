import logging

from nextcord.channel import VoiceChannel
from nextcord.ext.commands import Cog

from config.domain import Standby
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class Voice(Cog):
    def __init__(self):
        self.standby = Standby()

    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel:
            return

        if before.channel:
            role = uf.get_role(member.guild, before.channel.name)
            if role:
                await member.remove_roles(role)

        if after.channel:
            role = uf.get_role(member.guild, after.channel.name)
            if not role:
                role = await member.guild.create_role(
                    name=after.channel.name, mentionable=True
                )
            await member.add_roles(role)

    @Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if isinstance(after, VoiceChannel):
            logger.info(f"Voice channel renamed from {before.name} to {after.name}")
            role = uf.get_role(after.guild, before.name)
            if role:
                logger.info("Renaming voice channel role")
                await role.edit(name=after.name)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel):
        logger.info(f"Channel {channel.name} deleted")
        role = uf.get_role(channel.guild, channel.name)
        if role:
            logger.info(f"Deleting voice channel role for {channel.name}")
            await role.delete()


def setup(bot):
    bot.add_cog(Voice())
