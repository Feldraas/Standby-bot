import asyncio
import io
import logging
import random
import re
import urllib.request

import nextcord
import requests
from nextcord import (
    Member,
    SelectOption,
    SlashOption,
    message_command,
    slash_command,
    ui,
    user_command,
)
from nextcord.ext.commands import Cog
from PIL import Image

import config.startup
from config.constants import (
    ID,
    URL,
    VALID_TEXT_CHANNEL,
    ChannelName,
    Permissions,
    RoleName,
)
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class Admin(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(
        description="Pong!", default_member_permissions=Permissions.MODS_AND_GUIDES
    )
    async def ping(self, interaction):
        logger.info("Pinging")
        await interaction.send("Ponguu!")

    @slash_command(
        description="Sends a message through the bot to a chosen channel",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def say(
        self,
        interaction,
        channel: VALID_TEXT_CHANNEL = SlashOption(description="The channel to send to"),
        message: str = SlashOption(description="The message to send"),
    ):
        await channel.send(message)
        await interaction.send(
            f"Message successfully sent in {channel.mention}.", ephemeral=True
        )

    @slash_command(
        description="Commands to edit bot messages",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def edit(self, interaction):
        pass

    @edit.subcommand(description="Edits the full text of a bot message")
    async def full(
        self,
        interaction,
        channel: VALID_TEXT_CHANNEL = SlashOption(description="The channel to send to"),
        message_id: str = SlashOption(description="ID of the message to edit"),
        text: str = SlashOption(description="The new text of the message"),
        type_: str = SlashOption(
            name="in",
            description="where to make the edit",
            choices=["message body", "embed title", "embed description"],
            default="message body",
        ),
    ):
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
                    "Could not edit embed description", ephemeral=True
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

        else:
            try:
                await message.edit(content=text)
                await interaction.send("Message successfully edited", ephemeral=True)
            except:
                logger.warning("Could not edit message")
                await interaction.send("Could not edit message", ephemeral=True)

    @edit.subcommand(description="Replaces a part of a bot message with new text")
    async def part(
        self,
        interaction,
        channel: VALID_TEXT_CHANNEL = SlashOption(description="The channel to send to"),
        message_id: str = SlashOption(description="ID of the message to edit"),
        old: str = SlashOption(description="The phrase to remove"),
        new: str = SlashOption(description="The phrase to insert in its place"),
        type_: str = SlashOption(
            name="in",
            description="Where to make the edit",
            choices=["message body", "embed title", "embed description"],
            default="message body",
        ),
    ):
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
                    "Could not edit embed description", ephemeral=True
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
        description="Replies to a message (pings the author)",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def reply(
        self,
        interaction,
        channel: VALID_TEXT_CHANNEL = SlashOption(description="The channel to send to"),
        message_id: str = SlashOption(description="ID of the message to reply to"),
        message: str = SlashOption(description="The message to send"),
    ):
        try:
            reply_msg = await channel.fetch_message(int(message_id))
            await channel.send(message, reference=reply_msg)
            await interaction.send(
                f"Reply successfully sent in {channel.mention}", ephemeral=True
            )
        except nextcord.NotFound:
            await interaction.send("No message found with that ID", ephemeral=True)

    @slash_command(
        description="Leaves several ghost pings for a user",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def punish(
        self, interaction, user: Member = SlashOption(description="The user to punish")
    ):
        logger.info(f"{interaction.user} is punishing {user}")
        guild = interaction.guild
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
            channel = uf.get_channel(guild, ch)
            if channel:
                ping = await channel.send(user.mention)
                await ping.delete()
                await asyncio.sleep(2)
            else:
                logger.warning(self.bot, f"Channel {ch} could not be found")

        await asyncio.sleep(45)

        for ch in ch_list:
            channel = uf.get_channel(guild, ch)
            if channel:
                ping = await channel.send(user.mention)
                await ping.delete()
                await asyncio.sleep(2)
            else:
                logger.warning(self.bot, f"Channel {ch} could not be found")

    @user_command(
        name="Punish",
        guild_ids=[ID.GUILD],
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def punish_context(self, interaction, user):
        await uf.invoke_slash_command("punish", self, interaction, user)

    @slash_command(
        description="Reacts to a message (only emote from this server or default set)",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def react(
        self,
        interaction,
        channel: VALID_TEXT_CHANNEL = SlashOption(
            description="The channel of the message"
        ),
        message_id: str = SlashOption(description="ID of the message to react to"),
        emotes: str = SlashOption(description="Emotes to react with"),
    ):
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
        interaction,
        number: int = SlashOption(
            description="Number of messages to delete", min_value=1, max_value=20
        ),
        user: Member = SlashOption(
            description="Only delete a certain user's messages", required=False
        ),
    ):
        deleted = 0
        await interaction.send(
            f"Working (0/{number})... Do not dismiss this message", ephemeral=True
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
                    "Do not dismiss this message"
                )

        await interaction.edit_original_message(
            content=f"✅ Deleted the last {deleted} messages! ✅"
        )

    @slash_command(
        description="Move a post from one channel to another",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def move(
        self,
        interaction,
        message_id: str = SlashOption(description="ID of the message to edit"),
        from_channel: VALID_TEXT_CHANNEL = SlashOption(
            name="from", description="Channel to move from"
        ),
        to_channel: VALID_TEXT_CHANNEL = SlashOption(
            name="to", description="Channel to move to"
        ),
    ):
        await move_or_copy_message(interaction, message_id, from_channel, to_channel)

    @slash_command(
        description="Copy a post from one channel to another",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def copy(
        self,
        interaction,
        message_id: str = SlashOption(description="ID of the message to edit"),
        from_channel: VALID_TEXT_CHANNEL = SlashOption(
            name="from", description="Channel to move from"
        ),
        to_channel: VALID_TEXT_CHANNEL = SlashOption(
            name="to", description="Channel to move to"
        ),
    ):
        await move_or_copy_message(interaction, message_id, from_channel, to_channel)

    @slash_command(
        description="Reposts the last obit message to a channel",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def obit(
        self,
        interaction,
        channel: VALID_TEXT_CHANNEL = SlashOption(description="Channel to post in"),
    ):
        maint = uf.get_channel(interaction.guild, ChannelName.ERRORS)
        if not maint:
            logger.error(self.bot, "Could not find maintenance channel")
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
        interaction,
        offender: Member = SlashOption(description="The user to jail"),
    ):
        roles = [role.name for role in offender.roles]
        if any(mod_role_name in roles for mod_role_name in RoleName.mod_role_names()):
            await interaction.send(
                file=uf.simpsons_error_image(
                    dad=interaction.guild.me,
                    son=interaction.user,
                    text="You can't jail mods!",
                    filename="nope.png",
                )
            )
            return

        jailed_role = uf.get_role(interaction.guild, "Jailed")
        muted_role = uf.get_role(interaction.guild, "Muted")
        jail_channel = uf.get_channel(interaction.guild, "jail")
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
                    "and pay your debt to the void."
                )
                await interaction.send(
                    f"{offender.mention} has been jailed successfully", ephemeral=True
                )
        else:
            logger.error("Error processing roles or channel")
            await interaction.send("Error processing roles or channel", ephemeral=True)

    @user_command(name="Jail", default_member_permissions=Permissions.MODS_AND_GUIDES)
    async def jail_context(self, interaction, offender):
        await uf.invoke_slash_command("jail", self, interaction, offender)

    @slash_command(
        description="Release a user from jail",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def release(
        self,
        interaction,
        prisoner: Member = SlashOption(description="The user to release"),
    ):
        jailed_role = uf.get_role(interaction.guild, "Jailed")
        muted_role = uf.get_role(interaction.guild, "Muted")
        if jailed_role and muted_role:
            await prisoner.remove_roles(jailed_role, muted_role)
            await interaction.send(
                f"{prisoner.mention} has been released successfully", ephemeral=True
            )
        else:
            await interaction.send(
                f"{prisoner.mention} is not currently jailed", ephemeral=True
            )

    @user_command(
        name="Release", default_member_permissions=Permissions.MODS_AND_GUIDES
    )
    async def release_context(self, interaction, prisoner):
        await uf.invoke_slash_command("release", self, interaction, prisoner)

    @slash_command(
        description="Voidifies a user's avatar.",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def voidify(
        self,
        interaction,
        target: Member = SlashOption(description="The user to be voidified"),
    ):
        if interaction.user.id != ID.JORM:
            await interaction.send(
                "Jorm alone controls the void. Access denied.", ephemeral=True
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
    async def emoji(self, interaction):
        pass

    @emoji.subcommand(description="Adds an external emoji to the server")
    async def add(
        self,
        interaction,
        emoji: str = SlashOption(
            description="The emoji to add - can be the actual emoji "
            "(if you have Nitro) or an image link"
        ),
        name: str = SlashOption(description="The name to use for the emoji"),
    ):
        if new_emoji := await add_external_emoji(interaction, emoji, name):
            await interaction.send(f"Successfully added {new_emoji}", ephemeral=True)
        else:
            await interaction.send("Invalid emoji source", ephemeral=True)

    @emoji.subcommand(description="Removes an emoji from the server")
    async def delete(
        self,
        interaction,
        emoji=SlashOption(
            description="The emoji to remove - can be the actual emoji or just the name"
        ),
    ):
        if name := await delete_emoji(interaction, emoji):
            await interaction.send(f":{name}: successfully deleted", ephemeral=True)
        else:
            await interaction.send("Invalid emoji", ephemeral=True)

    @emoji.subcommand(description="Rename an emoji")
    async def rename(
        self,
        interaction,
        emoji: str = SlashOption(
            description="The emoji to remove (the actual emoji or just the name)"
        ),
        to: str = SlashOption(description="The new name for the emoji"),
    ):
        if match := re.search(r":(.*):", emoji):  # noqa: SIM108
            name = match.group(1)
        else:
            name = emoji

        if not (old_emoji := uf.get_emoji(interaction.guild, name)):
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
                f"Emoji successfully renamed to {added}", ephemeral=True
            )
        else:
            await interaction.send("Invalid emoji")

    @message_command(
        name="Steal emoji(s)", default_member_permissions=Permissions.MANAGE_EMOJIS
    )
    async def steal(self, interaction, message):
        emojis = re.findall(r"<a?:[^:]*:\d+>", message.content)

        if not emojis:
            await interaction.send("No emojis in message")
            return

        emoji_pattern = r"(?P<full_string><a?:(?P<name>[^:]*):(?P<id>\d+)>)"
        emojis = [re.search(emoji_pattern, emoji).groupdict() for emoji in emojis]

        class ChooseEmojiView(ui.View):
            def __init__(self):
                super().__init__()

            @ui.select(
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
            async def add_selected(self, select, interaction):
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
    async def on_guild_role_update(self, before, after):  # noqa: ARG002
        logger.info("Roles updated")
        await config.startup.reconnect_buttons(self.bot)


async def move_or_copy_message(interaction, message_id, from_channel, to_channel):
    try:
        msg = await from_channel.fetch_message(int(message_id))
    except nextcord.NotFound:
        await interaction.send("No message found with that ID", ephemeral=True)
        return

    cmd = interaction.application_command.name

    verb = "moving" if cmd == "move" else "copying"
    logger.info(
        f"{interaction.user} is {verb} message {message_id} from channel "
        f"#{from_channel.name} to channel #{to_channel.name}"
    )

    embed = uf.message_embed(msg, cmd, interaction.user)

    await to_channel.send(embed=embed)

    if cmd == "move":
        await msg.delete()
        await interaction.send("Message successfully moved", ephemeral=True)
    else:
        await interaction.send("Message successfully copied", ephemeral=True)


def is_leave_message(message):
    return (
        message.author.id == ID.BOT
        and message.embeds
        and message.embeds[0].title == "The void grows smaller..."
    )


async def add_external_emoji(interaction, emoji, name):
    if "https" in emoji:
        link = emoji
    elif match := re.search(r"<:.*:(\d+)>", emoji):
        emoji_id = match.group(1)
        link = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
    else:
        emoji_id = emoji
        link = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"

    logger.info(f"Fetching emoji from {link}")
    try:
        request = urllib.request.Request(link, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(request)
        logger.info("Emoji successfully fetched")
    except:
        return False
    else:
        try:
            logger.info("Creating emoji")
            return await interaction.guild.create_custom_emoji(
                name=name, image=response.read()
            )
        except:
            logger.exception("Could not create emoji")
            return False


async def delete_emoji(interaction, emoji):
    if match := re.search(r":(.*):", emoji):  # noqa: SIM108
        name = match.group(1)
    else:
        name = emoji
    emoji = uf.get_emoji(interaction.guild, name)
    logger.info(f"Deleting emoji {name}")

    try:
        await interaction.guild.delete_emoji(emoji)
    except:
        return False
    else:
        return name


def setup(bot):
    bot.add_cog(Admin(bot))
