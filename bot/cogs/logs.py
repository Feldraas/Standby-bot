"""Log server events."""

import logging

from nextcord import (
    ApplicationCommandOptionType,
    ApplicationCommandType,
    Embed,
    File,
    Interaction,
    InteractionType,
    Member,
    MessageType,
    RawMessageDeleteEvent,
    RawMessageUpdateEvent,
    VoiceChannel,
    VoiceState,
)
from nextcord.errors import NotFound
from nextcord.ext.commands import Bot, Cog

from domain import EMPTY_STRING, ChannelName, Color, Standby
from utils import util_functions as uf

EMBED_DESCRIPTION_LIMIT = 950

logger = logging.getLogger(__name__)


class Logs(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        """Log the text and any attachments of the deleted message.

        Called any time a user deletes a message.
        """
        channel = self.standby.bot.get_channel(payload.channel_id)
        logger.info(f"Message deleted in {channel.name}")
        if channel.name == ChannelName.LOGS:
            return
        embed, files = await deleted_embed(payload)
        if embed:
            logs = uf.get_channel(ChannelName.LOGS)
            if logs:
                main = await logs.send(embed=embed)
                for file in files:
                    await logs.send(file=file, reference=main)

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent) -> None:
        """Log the text before and after the edit.

        Called any time a user edits a message.
        """
        embed = await edited_embed(payload)
        logs = uf.get_channel(ChannelName.LOGS)

        if embed and logs:
            await logs.send(embed=embed)

    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState,
    ) -> None:
        """Log when a users enters or leaves a voice channel.

        Called anytime a user's voice state changes.
        """
        if before.channel == after.channel:
            return
        logger.debug(f"{member} has changed voice channels")
        embed = await voice_embed(member, before.channel, after.channel)

        logs = uf.get_channel(ChannelName.LOGS)
        if logs:
            await logs.send(embed=embed)

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction) -> None:
        """Log user interactions.

        Currently logged interactions:
            - Slash command usage
            - Component usage (buttons, dropdowns etc)

        Called any time a user interaction is detected.
        """
        logs = uf.get_channel(ChannelName.LOGS)

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


async def deleted_embed(payload: RawMessageDeleteEvent) -> tuple[Embed, list[File]]:
    """Create an embed for a deleted message.

    Args:
        payload (RawMessageDeleteEvent): The deleted message

    Returns:
        tuple[Embed, list[File]]: Embed containing the message details,
            and any attachments the message had
    """
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
                    logger.debug("Attachment not found in cache")
            attachment_text = "[See below]" if files else "[Not found in cache]"
            embed.add_field(name="Attachments", value=attachment_text, inline=False)
    else:
        embed.description = "[Message not found in cache]"
        channel = await Standby().bot.fetch_channel(payload.channel_id)
        embed.add_field(
            name="Channel",
            value=channel.mention,
        )
    embed.timestamp = uf.utcnow()
    return embed, files


async def edited_embed(payload: RawMessageUpdateEvent) -> Embed:  # noqa: C901, PLR0912, PLR0915
    """Create an embed for an edited message.

    Args:
        payload (RawMessageUpdateEvent): The edited message

    Returns:
        Embed: Embed containing the message details
    """
    before = payload.cached_message
    after = payload.data
    if "content" in after:
        after_message = after["content"]
    else:
        logger.debug("Message has no content - ignoring")
        return None

    if before:
        author = before.author
        if author.bot:
            logger.debug("Message is a bot message - ignoring")
            return None

        before_message = before.content
        if before_message == after_message:
            logger.debug("Message content is unchanged - ignoring")
            return None

        logger.debug("Message edit detected")
        channel = before.channel
        jump_url = before.jump_url
        avatar_url = before.author.display_avatar.url

        attachment_url = before.attachments[0].url if before.attachments else None

    else:
        before_message = "[Message not found in cache]"

        author_id = after["author"]["id"]
        channel_id = after["channel_id"]
        message_id = after["id"]

        standby = Standby()
        author = await standby.guild.fetch_member(author_id)
        if author.bot or not author:
            return None
        channel = await standby.bot.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)
        jump_url = message.jump_url
        avatar_url = author.display_avatar.url
        attachment_url = message.attachments[0].url if message.attachments else None

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


async def voice_embed(
    member: Member,
    before: VoiceChannel | None,
    after: VoiceChannel | None,
) -> Embed:
    """Create an embed for a user leaving/joining a voice channel.

    Args:
        member (Member): User
        before (VoiceChannel | None): Channel before user action
        after (VoiceChannel | None): Channel after user action

    Returns:
        Embed: Embed containing channel details
    """
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


async def command_embed(interaction: Interaction) -> Embed:  # noqa: C901, PLR0912, PLR0915
    """Create an embed for when a user triggers a command.

    Can be a slash (subcommand), user command or message command

    Args:
        interaction (Interaction): The interaction

    Returns:
        Embed: Embed with interaction details
    """
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
            name="Target user",
            value=uf.id_to_mention(interaction.data["target_id"]),
        )

    elif cmd_type == "Message command":
        message_id = interaction.data["target_id"]
        message = await interaction.channel.fetch_message(message_id)

        embed.add_field(
            name="Target messsage",
            value=f"[Click here]({message.jump_url})",
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


async def component_embed(interaction: Interaction) -> Embed:
    """Create an embed for when a user interacts with a component.

    Args:
        interaction (Interaction): The interaction

    Returns:
        Embed: Embed containing interaction details
    """
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
            name="Button",
            value=labels[0] if len(labels) == 1 else "Unknown",
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


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Logs())
