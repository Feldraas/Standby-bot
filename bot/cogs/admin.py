"""Admin commands."""

import asyncio
import io
import logging
import random
import re
import urllib.request

import nextcord
import requests
from nextcord import (
    Emoji,
    Interaction,
    Member,
    Message,
    Role,
    SelectOption,
    SlashOption,
    message_command,
    slash_command,
    user_command,
)
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import StringSelect, View, select
from PIL import Image

from domain import (
    ID,
    URL,
    ChannelName,
    Permissions,
    RoleName,
    Standby,
    ValidTextChannel,
)
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class Admin(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command(
        description="Pong!",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def ping(self, interaction: Interaction) -> None:
        """Ping the bot and receive a response.

        Args:
            interaction (Interaction): Invoking interaction.
        """
        logger.info("Pinging")
        await interaction.send("Ponguu!")

    @slash_command(
        description="Sends a message through the bot to a chosen channel",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def say(
        self,
        interaction: Interaction,
        channel: ValidTextChannel = SlashOption(description="The channel to send to"),
        message: str = SlashOption(description="The message to send"),
        reply_to: str | None = SlashOption(
            description="ID of the message to reply to",
            required=False,
        ),
    ) -> None:
        """Make the bot send a message in a channel.

        Args:
            interaction (Interaction): Invoking interaction.
            channel (ValidTextChannel): _The channel to send to.
            message (str): The message to send.
            reply_to (str | None): Message ID to reply to (optional)
        """
        reply_message = None
        if reply_to is not None:
            try:
                reply_message = await channel.fetch_message(int(reply_to))
            except nextcord.NotFound:
                await interaction.send(
                    "Invalid ID to reply to. Message was not sent",
                    ephemeral=True,
                )
                return

        await channel.send(message, reference=reply_message)
        await interaction.send(
            f"Message successfully sent in {channel.mention}.",
            ephemeral=True,
        )

    @slash_command(
        description="Commands to edit bot messages",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def edit(self, interaction: Interaction) -> None:
        """Command group for editing bot messages."""

    @edit.subcommand(description="Edits the full text of a bot message")
    async def full(
        self,
        interaction: Interaction,
        channel: ValidTextChannel = SlashOption(description="The message channel"),
        message_id: str = SlashOption(description="ID of the message to edit"),
        text: str = SlashOption(description="The new text of the message"),
        type_: str = SlashOption(
            name="in",
            description="where to make the edit",
            choices=["message body", "embed title", "embed description"],
            default="message body",
        ),
    ) -> None:
        """Replace the full text of a bot message.

        Args:
            interaction (Interaction): Invoking interaction.
            channel (ValidTextChannel): The message channel.
            message_id (str, optional): ID of the message to edit.
            text (str): The new text.
            type_ (str, optional): Which part of the message to edit
                (body, embed title or embed description).
                Defaults to "message body".
        """
        try:
            message = await channel.fetch_message(int(message_id))
        except nextcord.NotFound:
            await interaction.send("No message found with that ID", ephemeral=True)
            return

        if type_ == "embed description":
            try:
                embed = message.embeds[0]
                embed.description = text
                await message.edit(embed=embed)
                await interaction.send("Embed successfully edited", ephemeral=True)
            except:
                logger.warning("Could not edit embed description")
                await interaction.send(
                    "Could not edit embed description",
                    ephemeral=True,
                )

        elif type_ == "embed title":
            try:
                embed = message.embeds[0]
                embed.title = text
                await message.edit(embed=embed)
                await interaction.send("Embed successfully edited", ephemeral=True)
            except:
                logger.warning("Could not edit embed title")
                await interaction.send("Could not edit embed title", ephemeral=True)

        else:  # type_ == "message body"
            try:
                await message.edit(content=text)
                await interaction.send("Message successfully edited", ephemeral=True)
            except:
                logger.warning("Could not edit message")
                await interaction.send("Could not edit message", ephemeral=True)

    @edit.subcommand(description="Replaces a part of a bot message with new text")
    async def part(
        self,
        interaction: Interaction,
        channel: ValidTextChannel = SlashOption(description="The channel to send to"),
        message_id: str = SlashOption(description="ID of the message to edit"),
        old: str = SlashOption(description="The phrase to remove"),
        new: str = SlashOption(description="The phrase to insert in its place"),
        type_: str = SlashOption(
            name="in",
            description="Where to make the edit",
            choices=["message body", "embed title", "embed description"],
            default="message body",
        ),
    ) -> None:
        """Edit part of a bot message.

        Args:
            interaction (Interaction): Invoking interaction.
            channel (ValidTextChannel): The message channel.
            message_id (str, optional): ID of the message to edit.
            old (str): Phrase to remove
            new (str):Phrase to insert in its place.
            type_ (str): Which part of the message to edit (body,
                embed title or embed description).
                Defaults to "message body".
        """
        try:
            message = await channel.fetch_message(int(message_id))
        except nextcord.NotFound:
            await interaction.send("No message found with that ID", ephemeral=True)
            return

        if type_ == "embed description":
            try:
                embed = message.embeds[0]
                embed.description = embed.description.replace(old, new, 1)
                await message.edit(embed=embed)
                await interaction.send("Embed successfully edited", ephemeral=True)
            except:
                logger.warning("Could not edit embed description")
                await interaction.send(
                    "Could not edit embed description",
                    ephemeral=True,
                )

        elif type_ == "embed title":
            try:
                embed = message.embeds[0]
                embed.title = embed.title.replace(old, new, 1)
                await message.edit(embed=embed)
                await interaction.send("Embed successfully edited", ephemeral=True)
            except:
                logger.warning("Could not edit embed title")
                await interaction.send("Could not edit embed title", ephemeral=True)

        else:
            try:
                await message.edit(content=message.content.replace(old, new, 1))
                await interaction.send("Message successfully edited", ephemeral=True)
            except:
                logger.warning("Could not edit message")
                await interaction.send("Could not edit message", ephemeral=True)

    @slash_command(
        description="Leaves several ghost pings for a user",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def punish(
        self,
        interaction: Interaction,
        user: Member = SlashOption(description="The user to punish"),
    ) -> None:
        """Punish a user by leaving ghost pings in different channels.

        Args:
            interaction (Interaction): Invoking interaction
            user (Member): The user to punish
        """
        logger.info(f"{interaction.user} is punishing {user}")
        ch_list = [
            "general",
            "legs-and-cows-and-whatever",
            "off-topic",
            "shit-post",
            "animu",
            "bot-spam",
        ]
        await interaction.send("Punishment in progress", ephemeral=True)
        for ch in ch_list:
            channel = uf.get_channel(ch)
            if channel:
                ping = await channel.send(user.mention)
                await ping.delete()
                await asyncio.sleep(2)
            else:
                logger.warning(f"Channel {ch} could not be found")

        await asyncio.sleep(45)

        for ch in ch_list:
            channel = uf.get_channel(ch)
            if channel:
                ping = await channel.send(user.mention)
                await ping.delete()
                await asyncio.sleep(2)
            else:
                logger.warning(f"Channel {ch} could not be found")

    @user_command(
        name="Punish",
        guild_ids=[ID.GUILD],
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def punish_context(self, interaction: Interaction, user: Member) -> None:
        """Invoke the Punish command through the user context menu."""
        await uf.invoke_slash_command("punish", interaction, user)

    @slash_command(
        description="Reacts to a message (only emotes from this server or default set)",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def react(
        self,
        interaction: Interaction,
        channel: ValidTextChannel = SlashOption(
            description="The channel of the message",
        ),
        message_id: str = SlashOption(description="ID of the message to react to"),
        emotes: str = SlashOption(description="Emotes to react with"),
    ) -> None:
        """Add reaction(s) to a message.

        Emotes must be from the server or the default set.

        Args:
            interaction (Interaction): Invoking interaction
            channel (ValidTextChannel): The channel of the message
            message_id (str): ID of the message to react to
            emotes (str): Emote(s) to react with
        """
        try:
            msg = await channel.fetch_message(int(message_id))
        except nextcord.NotFound:
            await interaction.send("No message found with that ID", ephemeral=True)
            return

        emotes = re.split("(<[^>]*>)", emotes)
        clean_emotes = []
        for emote in emotes:
            if re.search("^<.*>$", emote):
                clean_emotes.append(emote)
            else:
                clean_emotes.extend([char for char in emote if char != " "])

        at_least_one = False
        all_ = True
        invalid = []
        for emote in clean_emotes:
            try:
                await msg.add_reaction(emote)
                at_least_one = True
            except:
                invalid.append(emote)
                all_ = False
        if all_:
            await interaction.send("All reactions successfully added", ephemeral=True)
        elif at_least_one:
            await interaction.send(
                "Invalid reactions skipped, valid reactions successfully added",
                ephemeral=True,
            )
        else:
            await interaction.send("Invalid emote(s)", ephemeral=True)

    @slash_command(
        description="Clears the last X messages sent in the channel",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def clear(
        self,
        interaction: Interaction,
        number: int = SlashOption(
            description="Number of messages to delete",
            min_value=1,
            max_value=20,
        ),
        user: Member = SlashOption(
            description="Only delete a certain user's messages",
            required=False,
        ),
    ) -> None:
        """Clear the last messages in the channel.

        Args:
            interaction (Interaction): Invoking interaction
            number (int): Number of messages to delete (1-20)
            user (Member, optional): Only delete message from
                the provided user
        """
        deleted = 0
        await interaction.send(
            f"Working (0/{number})... Do not dismiss this message",
            ephemeral=True,
        )
        response = await interaction.original_message()

        async for msg in interaction.channel.history(limit=25):
            if msg.id == response.id:
                continue
            if user == msg.author or user is None:
                await msg.delete()
                deleted += 1
                if deleted == number:
                    break
                await interaction.edit_original_message(
                    content=f"Working ({deleted}/{number})... "
                    "Do not dismiss this message",
                )

        await interaction.edit_original_message(
            content=f"✅ Deleted the last {deleted} messages! ✅",
        )

    @slash_command(
        description="Move a post from one channel to another",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def move(
        self,
        interaction: Interaction,
        message_id: str = SlashOption(description="ID of the message to edit"),
        from_channel: ValidTextChannel = SlashOption(
            name="from",
            description="Channel to move from",
        ),
        to_channel: ValidTextChannel = SlashOption(
            name="to",
            description="Channel to move to",
        ),
    ) -> None:
        """Move a message to a different channel.

        The bot deletes the message, then send an Embed containing
        the message details to a different channel.

        Args:
            interaction (Interaction): Invoking interaction
            message_id (str): ID of the message to edit
            from_channel (ValidTextChannel): Channel to move from
            to_channel (ValidTextChannel): Channel to move to
        """
        await move_or_copy_message(interaction, message_id, from_channel, to_channel)

    @slash_command(
        description="Copy a post from one channel to another",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def copy(
        self,
        interaction: Interaction,
        message_id: str = SlashOption(description="ID of the message to edit"),
        from_channel: ValidTextChannel = SlashOption(
            name="from",
            description="Channel to move from",
        ),
        to_channel: ValidTextChannel = SlashOption(
            name="to",
            description="Channel to move to",
        ),
    ) -> None:
        """Copy a message to a different channel.

        Like the move command, but the message is not deleted from the
        original channel.
        """
        # TODO: Deprecate when Discord fully implements forwarding
        await move_or_copy_message(interaction, message_id, from_channel, to_channel)

    @slash_command(
        description="Reposts the last obit message to a channel",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def obit(
        self,
        interaction: Interaction,
        channel: ValidTextChannel = SlashOption(description="Channel to post in"),
    ) -> None:
        """Notify users about recent 'obit' messages (users who left).

        Args:
            interaction (Interaction): Invoking interaction
            channel (ValidTextChannel): Channel to post in
        """
        maint = uf.get_channel(ChannelName.ERRORS)
        if not maint:
            logger.error("Could not find maintenance channel")
            await interaction.send("Could not find maintenance channel", ephemeral=True)
            return

        async for msg in maint.history(limit=6):
            if is_leave_message(msg):
                await channel.send(embed=msg.embeds[0])
                await interaction.send("Obit sent", ephemeral=True)
                return

        await interaction.send("No recent obit messages", ephemeral=True)

    @slash_command(
        description="Send a user to jail",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def jail(
        self,
        interaction: Interaction,
        offender: Member = SlashOption(description="The user to jail"),
    ) -> None:
        """Send a user to jail.

        The offending user loses the ability to see all channels except
        the jail channel.

        Args:
            interaction (Interaction): Invoking interaction
            offender (Member): The user to send to jail
        """
        roles = [role.name for role in offender.roles]
        if any(mod_role_name in roles for mod_role_name in RoleName.mod_role_names()):
            await interaction.send(
                file=uf.simpsons_error_image(
                    dad=interaction.guild.me,
                    son=interaction.user,
                    text="You can't jail mods!",
                    filename="nope.png",
                ),
            )
            return

        jailed_role = uf.get_role("Jailed")
        muted_role = uf.get_role("Muted")
        jail_channel = uf.get_channel("jail")
        if jailed_role and muted_role:
            await offender.add_roles(jailed_role, muted_role)
            if jail_channel:
                public_lines = [
                    "Stop right there, criminal scum! Nobody breaks the law "
                    "on my watch! I'm confiscating your stolen memes.",
                    "Stop! You violated the law. Your stolen memes are now forfeit.",
                    "It's all over, lawbreaker! Your spree is at an end. "
                    "I'll take any stolen memes you have.",
                ]
                await interaction.send(URL.GITHUB_STATIC + "/images/stop.jpg")
                await interaction.channel.send(random.choice(public_lines))
                await jail_channel.send(
                    f"Serve your time peaceably, {offender.mention}, "
                    "and pay your debt to the void.",
                )
                await interaction.send(
                    f"{offender.mention} has been jailed successfully",
                    ephemeral=True,
                )
        else:
            logger.error("Error processing roles or channel")
            await interaction.send("Error processing roles or channel", ephemeral=True)

    @user_command(name="Jail", default_member_permissions=Permissions.MODS_AND_GUIDES)
    async def jail_context(self, interaction: Interaction, offender: Member) -> None:
        """Invoke the jail command through the user context menu."""
        await uf.invoke_slash_command("jail", interaction, offender)

    @slash_command(
        description="Release a user from jail",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def release(
        self,
        interaction: Interaction,
        prisoner: Member = SlashOption(description="The user to release"),
    ) -> None:
        """Release a user from the jail channel.

        Args:
            interaction (Interaction): Invoking interaction
            prisoner (Member): The user to release
        """
        jailed_role = uf.get_role("Jailed")
        muted_role = uf.get_role("Muted")
        if jailed_role and muted_role and jailed_role in prisoner.roles:
            await prisoner.remove_roles(jailed_role, muted_role)
            await interaction.send(
                f"{prisoner.mention} has been released successfully",
                ephemeral=True,
            )
        else:
            await interaction.send(
                f"{prisoner.mention} is not currently jailed",
                ephemeral=True,
            )

    @user_command(
        name="Release",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def release_context(self, interaction: Interaction, prisoner: Member) -> None:
        """Invoke the release command through the user context menu."""
        await uf.invoke_slash_command("release", interaction, prisoner)

    @slash_command(
        description="Voidifies a user's avatar.",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def voidify(
        self,
        interaction: Interaction,
        target: Member = SlashOption(description="The user to be voidified"),
    ) -> None:
        """Add a Void border to a user's avatar.

        Can only be used by Jorm.

        Args:
            interaction (Interaction): Invoking interaction
            target (Member): Target user
        """
        if interaction.user.id != ID.JORM:
            await interaction.send(
                "Jorm alone controls the void. Access denied.",
                ephemeral=True,
            )
            return

        avatar_url = target.display_avatar.url if target.display_avatar else ""
        avatar = Image.open(requests.get(avatar_url, stream=True).raw)
        avatar = avatar.convert("RGBA")
        border = Image.open(requests.get(URL.GINNY_TRANSPARENT, stream=True).raw)
        border = border.resize(avatar.size, Image.ANTIALIAS)
        avatar.paste(border, (0, 0), border)

        new_image = []
        border_white = Image.open(requests.get(URL.GINNY_WHITE, stream=True).raw)
        border_white = border_white.resize(avatar.size, Image.ANTIALIAS)
        white_data = border_white.getdata()
        avatar_data = avatar.getdata()
        for i in range(len(white_data)):
            if white_data[i] == (255, 255, 255, 255):
                new_image.append((0, 0, 0, 0))
            else:
                new_image.append(avatar_data[i])
        avatar.putdata(new_image)

        obj = io.BytesIO()
        avatar.save(obj, "png")
        obj.seek(0)

        await interaction.send(file=nextcord.File(obj, filename="pic.png"))

    @slash_command(
        description="Emoji commands",
        default_member_permissions=Permissions.MANAGE_EMOJIS,
    )
    async def emoji(self, interaction: Interaction) -> None:
        """Command group for managing server emojis."""

    @emoji.subcommand(description="Adds an external emoji to the server")
    async def add(
        self,
        interaction: Interaction,
        emoji: str = SlashOption(
            description="The emoji to add - can be the actual emoji "
            "(if you have Nitro) or an image link",
        ),
        name: str = SlashOption(description="The name to use for the emoji"),
    ) -> None:
        """Add an emoji to the server.

        Args:
            interaction (Interaction): Invoking interaction
            emoji (str): The emoji to add.
            name (str): The name to use for the emoji
        """
        if new_emoji := await add_external_emoji(interaction, emoji, name):
            await interaction.send(f"Successfully added {new_emoji}", ephemeral=True)
        else:
            await interaction.send("Invalid emoji source", ephemeral=True)

    @emoji.subcommand(description="Removes an emoji from the server")
    async def delete(
        self,
        interaction: Interaction,
        emoji: str = SlashOption(
            description="The emoji to remove - (the actual emoji or just the name)",
        ),
    ) -> None:
        """Delete an emoji from the server.

        Args:
            interaction (Interaction): Invoking interaction
            emoji (str): The emoji to remove
        """
        if deleted_emoji := await delete_emoji(interaction, emoji):
            await interaction.send(
                f":{deleted_emoji.name}: successfully deleted",
                ephemeral=True,
            )
        else:
            await interaction.send("Invalid emoji", ephemeral=True)

    @emoji.subcommand(description="Rename an emoji")
    async def rename(
        self,
        interaction: Interaction,
        emoji: str = SlashOption(
            description="The emoji to rename (the actual emoji or just the name)",
        ),
        to: str = SlashOption(description="The new name for the emoji"),
    ) -> None:
        """Rename an emoji.

        Args:
            interaction (Interaction): Invoking interaction
            emoji (str): "The emoji to rename
            to (str): The new name for the emoji
        """
        if match := re.search(r":(.*):", emoji):  # noqa: SIM108
            name = match.group(1)
        else:
            name = emoji

        if not (old_emoji := uf.get_emoji(name)):
            await interaction.send("Invalid emoji", ephemeral=True)
            return

        added = await add_external_emoji(
            interaction,
            emoji=f"https://cdn.discordapp.com/emojis/{old_emoji.id}.png",
            name=to,
        )
        if added:
            await delete_emoji(interaction, emoji)
            await interaction.send(
                f"Emoji successfully renamed to {added}",
                ephemeral=True,
            )
        else:
            await interaction.send("Invalid emoji")

    @message_command(
        name="Steal emoji(s)",
        default_member_permissions=Permissions.MANAGE_EMOJIS,
    )
    async def steal(self, interaction: Interaction, message: Message) -> None:
        """Add emojis contained in a message using the context menu.

        Clicking the buttons creates a dropdown menu letting the user
        choose which emoji(s) contained in the target should be added.

        Args:
            interaction (Interaction): Invoking interaction
            message (Message): Message containing the emoji
        """
        emojis = re.findall(r"<a?:[^:]*:\d+>", message.content)

        if not emojis:
            await interaction.send("No emojis in message")
            return

        emoji_pattern = r"(?P<full_string><a?:(?P<name>[^:]*):(?P<id>\d+)>)"
        emojis = [re.search(emoji_pattern, emoji).groupdict() for emoji in emojis]

        class ChooseEmojiView(View):
            @select(
                placeholder="Choose emoji(s) to steal",
                options=[
                    SelectOption(
                        label=emoji["name"],
                        emoji=emoji["full_string"],
                        value=emoji["full_string"][2:-1],
                    )
                    for emoji in emojis
                ],
                max_values=len(emojis),
            )
            async def add_selected(
                self,
                select: StringSelect,
                interaction: Interaction,
            ) -> None:
                """Callback function for the dropdown menu.

                Args:
                    select (StringSelect): The dropdown menu object
                    interaction (Interaction): Invoking interaction
                """
                added = []
                for emoji in select.values:
                    name, emoji_id = emoji.split(":")
                    added.append(await add_external_emoji(interaction, emoji_id, name))

                await interaction.edit(
                    content="Added "
                    + " ".join([str(emoji) for emoji in added if emoji]),
                    view=None,
                )

        await interaction.send(view=ChooseEmojiView(), ephemeral=True)

    @Cog.listener()
    async def on_guild_role_update(self, before: Role, after: Role) -> None:  # noqa: ARG002
        """Recreates buttons after roles are updated.

        Args:
            before (Role): The role before the change
            after (Role): The role after the change
        """
        logger.debug("Roles updated")
        await self.standby.reconnect_buttons()


async def move_or_copy_message(
    interaction: Interaction,
    message_id: str,
    from_channel: ValidTextChannel,
    to_channel: ValidTextChannel,
) -> None:
    """Common functionality for the move and copy commands.

    Args:
        interaction (Interaction): Invoking interaction
        message_id (str): ID of the message
        from_channel (ValidTextChannel): Original channel
        to_channel (ValidTextChannel): Destination channel
    """
    try:
        msg = await from_channel.fetch_message(int(message_id))
    except nextcord.NotFound:
        await interaction.send("No message found with that ID", ephemeral=True)
        return

    cmd = interaction.application_command.name

    verb = "moving" if cmd == "move" else "copying"
    logger.info(
        f"{interaction.user} is {verb} message {message_id} from channel "
        f"#{from_channel.name} to channel #{to_channel.name}",
    )

    embed = uf.message_embed(msg, cmd, interaction.user)

    await to_channel.send(embed=embed)

    if cmd == "move":
        await msg.delete()
        await interaction.send("Message successfully moved", ephemeral=True)
    else:
        await interaction.send("Message successfully copied", ephemeral=True)


def is_leave_message(message: Message) -> bool:
    """Check whether a message is a user leave event announcement.

    Args:
        message (Message): Message to check

    Returns:
        bool: True if it is a leave message
    """
    return (
        message.author.id == ID.BOT
        and message.embeds
        and message.embeds[0].title == "The void grows smaller..."
    )


async def add_external_emoji(
    interaction: Interaction,
    emoji: str,
    name: str,
) -> Emoji | None:
    """Add an emoji to the server from an external source.

    Args:
        interaction (Interaction): Invoking interaction
        emoji (str): Emoji to add (external link or "<:abcd:12345678>")
        name (str): New name

    Returns:
        Emoji | None: The created emoji, if successful
    """
    if "https" in emoji:
        link = emoji
    elif match := re.search(r"<:.*:(\d+)>", emoji):
        emoji_id = match.group(1)
        link = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
    else:
        emoji_id = emoji
        link = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"

    logger.debug(f"Fetching emoji from {link}")
    try:
        request = urllib.request.Request(link, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(request)
        logger.debug("Emoji successfully fetched")
    except:
        return None
    else:
        try:
            logger.info("Creating emoji")
            return await interaction.guild.create_custom_emoji(
                name=name,
                image=response.read(),
            )
        except:
            logger.exception("Could not create emoji")
            return None


async def delete_emoji(interaction: Interaction, emoji_str: str) -> Emoji | None:
    """Delete an emoji from the server.

    Args:
        interaction (Interaction): Invoking interaction
        emoji_str (str): Emoji name or string (<:abcd:12345678>)

    Returns:
        Emoji | None: The deleted emoji, if successful
    """
    if match := re.search(r":(.*):", emoji_str):  # noqa: SIM108
        name = match.group(1)
    else:
        name = emoji_str
    emoji = uf.get_emoji(name)
    logger.info(f"Deleting emoji {name}")

    try:
        await interaction.guild.delete_emoji(emoji)
    except:
        return None
    else:
        return emoji


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Admin())
