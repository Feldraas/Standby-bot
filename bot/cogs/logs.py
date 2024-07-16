import logging

from nextcord import (
    ApplicationCommandOptionType,
    ApplicationCommandType,
    Embed,
    InteractionType,
    MessageType,
)
from nextcord.errors import NotFound
from nextcord.ext.commands import Cog

from config.constants import EMPTY_STRING, ChannelName, Color
from utils import util_functions as uf

EMBED_DESCRIPTION_LIMIT = 950

logger = logging.getLogger(__name__)


class Logs(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_raw_message_delete(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        logger.info(f"Message deleted in {channel.name}")
        if channel.name == ChannelName.LOGS:
            return
        embed, files = await deleted_embed(payload, channel)
        if embed:
            logs = uf.get_channel(channel.guild, ChannelName.LOGS)
            if logs:
                main = await logs.send(embed=embed)
                for file in files:
                    await logs.send(file=file, reference=main)

    @Cog.listener()
    async def on_raw_message_edit(self, payload):
        embed = await edited_embed(self.bot, payload)
        if embed:
            channel = self.bot.get_channel(payload.channel_id)
            logs = uf.get_channel(channel.guild, ChannelName.LOGS)
            if logs:
                await logs.send(embed=embed)

    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel:
            return
        logger.info(f"{member} has changed voice channels")
        embed = await voice_embed(member, before.channel, after.channel)

        logs = uf.get_channel(member.guild, ChannelName.LOGS)
        if logs:
            await logs.send(embed=embed)

    @Cog.listener()
    async def on_interaction(self, interaction):
        logs = uf.get_channel(interaction.guild, ChannelName.LOGS)

        if not logs:
            logger.error("Log channel not found")
            return

        if interaction.type == InteractionType.application_command:
            embed = await command_embed(interaction)
            await logs.send(embed=embed)
        elif interaction.type == InteractionType.component:
            embed = await component_embed(interaction)
            await logs.send(embed=embed)
        elif interaction.type == InteractionType.application_command_autocomplete:
            pass
        else:
            logger.warning(
                f"Unknown interaction in {interaction.channel.name} "
                f"with {interaction.type=}",
            )
            await logs.send(f"Unknown interaction in {interaction.channel.mention}.")


async def deleted_embed(payload, channel):
    embed = Embed(color=Color.SOFT_RED)
    embed.title = "Message deleted"
    files = []
    if payload.cached_message is not None:
        message = payload.cached_message
        if message.author.bot or message.type == MessageType.pins_add:
            return None, None
        embed.description = message.content
        if len(embed.description) > EMBED_DESCRIPTION_LIMIT:
            embed.description = embed.description[0:EMBED_DESCRIPTION_LIMIT]
            embed.description += "[Message had to be shortened]"

        if message.author.display_avatar:
            embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.add_field(name="Author", value=message.author.mention)
        embed.add_field(name="Channel", value=message.channel.mention)
        if message.attachments:
            for attachment in message.attachments:
                try:
                    file = await attachment.to_file()
                    files.append(file)
                except NotFound:
                    logger.info("Attachment not found in cache")
            attachment_text = "[See below]" if files else "[Not found in cache]"
            embed.add_field(name="Attachments", value=attachment_text, inline=False)
    else:
        embed.description = "[Message not found in cache]"
        embed.add_field(name="Channel", value=channel.mention)
    embed.timestamp = uf.utcnow()
    return embed, files


async def edited_embed(bot, payload):  # noqa: C901, PLR0912, PLR0915
    before = payload.cached_message
    after = payload.data
    if "content" in after:
        after_message = after["content"]
    else:
        logger.info("Message has no content - ignoring")
        return None

    if before:
        author = before.author
        if author.bot:
            logger.info("Message is a bot message - ignoring")
            return None

        before_message = before.content
        if before_message == after_message:
            logger.info("Message content is unchanged - ignoring")
            return None

        logger.info("Message edit detected")
        channel = before.channel
        jump_url = before.jump_url
        avatar_url = before.author.display_avatar.url

        attachment_url = before.attachments[0].url if before.attachments else None

    else:
        before_message = "[Message not found in cache]"

        guild_id = after["guild_id"]
        author_id = after["author"]["id"]
        channel_id = after["channel_id"]
        message_id = after["id"]

        guild = await bot.fetch_guild(guild_id)
        author = await guild.fetch_member(author_id)
        if author.bot or not author:
            return None
        channel = await bot.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)
        jump_url = message.jump_url
        avatar_url = author.display_avatar.url
        attachment_url = message.attachments[0].url if message.attachments else None

    logger.info("Creating embed")
    embed = Embed(color=Color.LIGHT_BLUE)
    embed.title = "Message edited"

    if len(before_message) > EMBED_DESCRIPTION_LIMIT:
        before_message = before_message[0:EMBED_DESCRIPTION_LIMIT]
        before_message += " [Message had to be shortened]"
    if len(after_message) > EMBED_DESCRIPTION_LIMIT - 350:
        after_message = after_message[0:EMBED_DESCRIPTION_LIMIT]
        after_message += " [Message had to be shortened]"
    if len(before_message) <= 0:
        before_message = "[empty]"
    if len(after_message) <= 0:
        after_message = "[empty]"

    embed.add_field(name="Before", value=before_message, inline=False)
    embed.add_field(name="After", value=after_message, inline=False)
    embed.add_field(name="Author", value=author.mention)
    embed.add_field(name="Channel", value=channel.mention)
    embed.add_field(name="Link to Message", value=f"[Click here]({jump_url})")

    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    if attachment_url:
        embed.add_field(name="Attachment", value=f"[Click here]({attachment_url})")

    embed.timestamp = uf.utcnow()

    return embed


async def voice_embed(member, before, after):
    embed = Embed(color=Color.PALE_BLUE)
    embed.title = "Voice channel update"

    discriminator = f"#{member.discriminator}" if member.discriminator != "0" else ""

    if before and after:
        embed.description = (
            f"{member.mention} ({member.name}{discriminator}) switched"
            f" voice channels from {before.mention} to {after.mention}"
        )
    elif before:
        embed.description = (
            f"{member.mention} ({member.name}{discriminator}) left"
            f" voice channel {before.mention}"
        )
    else:
        embed.description = (
            f"{member.mention} ({member.name}{discriminator}) joined"
            f" voice channel {after.mention}"
        )
    embed.timestamp = uf.utcnow()
    return embed


async def command_embed(interaction):  # noqa: C901, PLR0912, PLR0915
    if interaction.application_command.type == ApplicationCommandType.chat_input:
        cmd_type = "Slash command"
        cmd_prefix = "/"
    elif (
        interaction.application_command.type == ApplicationCommandOptionType.sub_command
    ):
        cmd_type = "Slash subcommand"
        cmd_prefix = "/"
    elif interaction.application_command.type == ApplicationCommandType.user:
        cmd_type = "User command"
        cmd_prefix = "Apps > "
    elif interaction.application_command.type == ApplicationCommandType.message:
        cmd_type = "Message command"
        cmd_prefix = "Apps > "
    else:
        cmd_type = "Unknown command type"
        cmd_prefix = "?"

    logger.info(f"Creating {cmd_type.lower()} embed")

    embed = Embed(color=Color.VIE_PURPLE)
    embed.title = f"{cmd_type} triggered"

    try:
        parent_name = interaction.application_command.parent_cmd.name + " "
    except AttributeError:
        parent_name = ""

    full_command_name = cmd_prefix + parent_name + interaction.application_command.name
    embed.add_field(name="Command", value=full_command_name, inline=False)
    embed.add_field(name="Triggered by", value=interaction.user.mention)
    embed.add_field(name="In channel", value=interaction.channel.mention)

    if cmd_type == "User command":
        embed.add_field(
            name="Target user", value=uf.id_to_mention(interaction.data["target_id"])
        )

    elif cmd_type == "Message command":
        message_id = interaction.data["target_id"]
        message = await interaction.channel.fetch_message(message_id)

        embed.add_field(
            name="Target messsage", value=f"[Click here]({message.jump_url})"
        )

    elif "options" in interaction.data:  # Slash
        embed.add_field(name=EMPTY_STRING, value=EMPTY_STRING)

        arg_data = interaction.data["options"]
        if "options" in arg_data[0]:
            arg_data = arg_data[0]["options"]
        user_type, channel_type, role_type = 6, 7, 8
        for arg in arg_data:
            if arg["type"] == user_type:
                formatted_value = uf.id_to_mention(arg["value"], "user")
            elif arg["type"] == channel_type:
                formatted_value = uf.id_to_mention(arg["value"], "channel")
            elif arg["type"] == role_type:
                formatted_value = uf.id_to_mention(arg["value"], "role")
            elif full_command_name.startswith("/prediction") and arg["name"] in [
                "label",
                "text",
            ]:
                formatted_value = "[REDACTED]"
            else:
                formatted_value = arg["value"]

            embed.add_field(name=arg["name"], value=formatted_value)

    avatar_url = interaction.user.display_avatar.url
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    embed.timestamp = uf.utcnow()

    return embed


async def component_embed(interaction):
    logger.info("Creating component embed")
    embed = Embed(color=Color.VIE_PURPLE)

    avatar_url = interaction.user.display_avatar.url
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    data = interaction.data
    button_type, select_type = 2, 3  # From Discord API

    if data["component_type"] == button_type:
        embed.title = "Button pressed"
        labels = []
        for row in interaction.message.components:
            for child in row.children:
                if child.custom_id != data["custom_id"]:
                    continue
                if child.label:
                    labels.append(child.label)
                elif child.emoji:
                    labels.append(child.emoji)
        embed.add_field(
            name="Button", value=labels[0] if len(labels) == 1 else "Unknown"
        )
        embed.add_field(name="Pressed by", value=interaction.user.mention)
        embed.add_field(name="In channel", value=interaction.channel.mention)

    elif data["component_type"] == select_type:
        embed.title = "Dropdown menu used"
        embed.add_field(name="Used by", value=interaction.user.mention)
        embed.add_field(name="In channel", value=interaction.channel.mention)
        name = "Value" + ("s" if len(data["values"]) > 1 else "")
        value = ", ".join(data["values"])
        if not value:
            value = "[Menu cleared]"
        embed.add_field(name=name, value=value)

    else:
        embed.title = f"Unknown component type {data['component_type']}"
        embed.add_field(name="Used by", value=interaction.user.mention)
        embed.add_field(name="In channel", value=interaction.channel.mention)

    embed.add_field(
        name="Link to message",
        value=f"[Click here]({interaction.message.jump_url})",
        inline=False,
    )

    return embed


def setup(bot):
    bot.add_cog(Logs(bot))
