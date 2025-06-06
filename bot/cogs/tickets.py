"""Creation and managing of user tickets to the mod team."""

import logging

from nextcord import (
    ButtonStyle,
    CategoryChannel,
    Embed,
    Interaction,
    Message,
    PermissionOverwrite,
    TextChannel,
    slash_command,
)
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import Button, button

from domain import (
    CategoryName,
    ChannelName,
    Color,
    Permissions,
    RoleName,
    Standby,
)
from utils import util_functions as uf

logger = logging.getLogger(__name__)

CLAIMABLE_CHANNEL_MESSAGE = (
    "If you have an issue and want to talk to the mod team, this is the place.\n"
    "Press the button to open a ticket in a private channel "
    "visible only to you and the mod team."
)
CLAIMED_MESSAGE = (
    "You have successfully opened a ticket - please let us know "
    "what you want to discuss.\nYou can make sure you're talking only to the mod team"
    " by looking at the channel's current member list (right side of discord).\n"
    "Once this issue has been resolved, use the `/resolve` command."
)
RESOLVED_MESSAGE = (
    "This ticket has been marked as resolved. If this was a mistake or you have"
    " additional questions, use the button below to reopen the ticket.\n"
    "For other issues, please create a new ticket in XXX.\n Moderators can use "
    "the Scrap button to scrap this ticket. (Scrapping takes a while to complete)"
)
REOPENED_MESSAGE = (
    "This ticket has been reopened. Once it is resolved, "
    "use the `/resolve` command again."
)


class Tickets(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command(description="Mark your ticket as resolved")
    async def resolve(self, interaction: Interaction) -> None:
        """Mark a ticket as resolved."""
        if interaction.channel.category.name != CategoryName.ACTIVE_TICKETS:
            await interaction.send(
                "This command can only be used in an active ticket channel",
                ephemeral=True,
            )
            return

        logger.info(f"Resolving ticket {interaction.channel.name}")
        resolved_ticket_cat = await get_or_create_resolved_category(interaction)
        await interaction.channel.edit(category=resolved_ticket_cat)

        claimable_channel = uf.get_channel(ChannelName.CLAIMABLE)
        view = ResolvedTicketView()
        await interaction.send(
            RESOLVED_MESSAGE.replace("XXX", claimable_channel.mention),
            view=view,
        )
        await interaction.channel.set_permissions(
            interaction.user,
            read_messages=True,
            send_messages=False,
        )
        msg = await interaction.original_message()
        await view.record(msg)

    @slash_command(
        description="Initiates ticket system - creates categories, channels etc",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def initiate_ticket_system(self, interaction: Interaction) -> None:
        """Create ticket channels and categories."""
        logger.info("Initiaing ticket system")
        claimable_ticket_cat = await get_or_create_claimable_category(interaction)
        if not claimable_ticket_cat.channels:
            await create_claimable_channel(claimable_ticket_cat)
        await get_or_create_active_category(interaction)
        await get_or_create_resolved_category(interaction)
        await get_or_create_tickets_log(interaction)
        await interaction.send("Ticket system succesfully initiated", ephemeral=True)


def get_tickets_log_embed(message: Message) -> Embed:
    """Create an embed to log a finished ticket."""
    embed = Embed(color=Color.DARK_BLUE)
    if message.attachments:
        embed.set_image(url=message.attachments[0].url)
    content_msg = "[Empty message]"
    if len(message.content) > 0:
        content_msg = message.content
        max_length = 1800
        if len(content_msg) > max_length:
            content_msg = content_msg[0:max_length]
            content_msg += " [Message too long to be logged]"
    if message.author.display_avatar:
        embed.set_thumbnail(url=message.author.display_avatar.url)
    embed.title = message.author.name
    embed.description = content_msg
    embed.add_field(name="Channel", value=message.channel.name)
    embed.add_field(name="Date", value=message.created_at)
    return embed


async def create_claimable_channel(cat: CategoryChannel) -> None:
    """Create a ticket channel that a user can claim."""
    chnl = await cat.create_text_channel(
        name=ChannelName.CLAIMABLE,
        reason="Making a claimable channel.",
    )
    logger.info("Creating claimable channel")
    muted_role = uf.get_role("Muted")
    if muted_role:
        await chnl.set_permissions(muted_role, send_messages=True)
    view = OpenTicketView()
    msg = await chnl.send(CLAIMABLE_CHANNEL_MESSAGE, view=view)
    await view.record(msg)


async def get_or_create_tickets_log(interaction: Interaction) -> TextChannel:
    """Get the ticket log channel. Create it if missing."""
    resolved_cat = await get_or_create_resolved_category(interaction)
    tickets_log = uf.get_channel(ChannelName.TICKETS_LOG)
    if tickets_log is None:
        overwrites = {
            interaction.guild.default_role: PermissionOverwrite(read_messages=False),
        }

        logger.info("Creating ticket log")
        tickets_log = await resolved_cat.create_text_channel(
            name=ChannelName.TICKETS_LOG,
            reason="Making a channel for ticket logs.",
            overwrites=overwrites,
        )
        for mod_role_name in RoleName.mod_role_names():
            role = uf.get_role(mod_role_name)
            if role is not None:
                await tickets_log.set_permissions(role, read_messages=True)
    return tickets_log


async def get_or_create_claimable_category(interaction: Interaction) -> CategoryChannel:
    """Get the claimable tickets category. Create it if missing."""
    claimable_ticket_cat = uf.get_category(CategoryName.CLAIMABLE_TICKETS)
    if claimable_ticket_cat is None:
        logger.info("Creating claimable category")
        claimable_ticket_cat = await interaction.guild.create_category(
            name=CategoryName.CLAIMABLE_TICKETS,
            reason="Making a category for claimable tickets.",
        )
    return claimable_ticket_cat


async def get_or_create_active_category(interaction: Interaction) -> CategoryChannel:
    """Get the active ticket category. Create it if needed."""
    active_ticket_cat = uf.get_category(CategoryName.ACTIVE_TICKETS)
    if active_ticket_cat is None:
        logger.info("Creating active ticket category")
        active_ticket_cat = await interaction.guild.create_category(
            name=CategoryName.ACTIVE_TICKETS,
            reason="Making a category for claimable tickets.",
        )
    return active_ticket_cat


async def get_or_create_resolved_category(interaction: Interaction) -> CategoryChannel:
    """Get the resolved tickets category. Create it if needed."""
    resolved_ticket_cat = uf.get_category(CategoryName.RESOLVED_TICKETS)
    if resolved_ticket_cat is None:
        logger.info("Creating resolved ticket category")
        resolved_ticket_cat = await interaction.guild.create_category(
            name=CategoryName.RESOLVED_TICKETS,
            reason="Making a category for claimable tickets.",
        )
    return resolved_ticket_cat


async def get_highest_num(interaction: Interaction) -> int:
    """Get the current ticket number."""
    active_ticket_cat = await get_or_create_active_category(interaction)
    resolved_ticket_cat = await get_or_create_resolved_category(interaction)

    num = 0
    for x in active_ticket_cat.channels:
        lst = x.name.split("-")
        try:
            if int(lst[-1]) > num:  # noqa: PLR1730
                num = int(lst[-1])
        except Exception:
            logger.exception(f"debug: {lst} has no number")

    for x in resolved_ticket_cat.channels:
        lst = x.name.split("-")
        try:
            if int(lst[-1]) > num:  # noqa: PLR1730
                num = int(lst[-1])
        except Exception:
            logger.exception(f"debug: {lst} has no number")

    return num


class OpenTicketView(uf.PersistentView):
    """View to create a new ticket."""

    def __init__(self, params: dict | None = None) -> None:
        super().__init__(params)

    @button(style=ButtonStyle.green, label="Open ticket")
    async def create(self, button: Button, interaction: Interaction) -> None:  # noqa: ARG002
        """Button to create a new ticket."""
        claimable_channel = uf.get_channel(ChannelName.CLAIMABLE)
        if interaction.channel != claimable_channel:
            await interaction.send(
                f"This command can only be used in {claimable_channel.mention}.",
                ephemeral=True,
            )
            return

        issue_num = await get_highest_num(interaction) + 1

        active_ticket_cat = await get_or_create_active_category(interaction)
        overwrites = {
            interaction.guild.default_role: PermissionOverwrite(read_messages=False),
        }

        ticket_chnl = await active_ticket_cat.create_text_channel(
            name=f"{interaction.user.name}-{issue_num}",
            reason="Making a ticket.",
            overwrites=overwrites,
        )
        await ticket_chnl.set_permissions(interaction.user, read_messages=True)
        for mod_role_name in RoleName.mod_role_names():
            role = uf.get_role(name=mod_role_name)
            if role is not None:
                await ticket_chnl.set_permissions(role, read_messages=True)

        await ticket_chnl.send(f"<@{interaction.user.id}> {CLAIMED_MESSAGE}")
        await interaction.send(
            f"You can now head over to {ticket_chnl.mention}.",
            ephemeral=True,
        )


class ResolvedTicketView(uf.PersistentView):
    """View for resolved tickets."""

    def __init__(self, params: dict | None = None, *, disabled: bool = False) -> None:
        super().__init__(params)
        if disabled:
            self.reopen.disabled = True
            self.scrap.disabled = True

    @button(style=ButtonStyle.green, label="Reopen ticket")
    async def reopen(self, button: Button, interaction: Interaction) -> None:  # noqa: ARG002
        """Button to reopen a resolved ticket."""
        active_ticket_cat = await get_or_create_active_category(interaction)
        await interaction.channel.edit(category=active_ticket_cat)
        await interaction.edit(view=ResolvedTicketView(disabled=True))
        await interaction.send(REOPENED_MESSAGE)
        for user in interaction.channel.members:
            await interaction.channel.set_permissions(
                user,
                read_messages=True,
                send_messages=True,
            )

    @button(style=ButtonStyle.red, label="Scrap ticket")
    async def scrap(self, button: Button, interaction: Interaction) -> None:  # noqa: ARG002
        """Button to scrap a resolved ticket."""
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.send("Only moderators can scrap tickets", ephemeral=True)
            return

        await interaction.send("Scrapping in progress", ephemeral=True)
        tickets_log = await get_or_create_tickets_log(interaction)
        msg_list = await interaction.channel.history(
            limit=500,
            oldest_first=True,
        ).flatten()
        for msg in msg_list:
            emb = get_tickets_log_embed(msg)
            await tickets_log.send(embed=emb)

        await interaction.channel.delete()


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Tickets())
