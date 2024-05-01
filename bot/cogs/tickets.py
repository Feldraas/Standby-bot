from nextcord import ButtonStyle, Embed, PermissionOverwrite, slash_command, ui
from nextcord.ext.commands import Cog

from config.constants import CategoryName, ChannelName, Color, Permissions, RoleName
from db_integration import db_functions as db
from utils import util_functions as uf

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
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Mark your ticket as resolved")
    async def resolve(self, interaction):
        if interaction.channel.category.name != CategoryName.ACTIVE_TICKETS:
            await interaction.send(
                "This command can only be used in an active ticket channel",
                ephemeral=True,
            )
            return

        resolved_ticket_cat = await get_or_create_resolved_cat(interaction)
        await interaction.channel.edit(category=resolved_ticket_cat)

        claimable_channel = uf.get_channel(interaction.guild, ChannelName.CLAIMABLE)
        view = ResolvedTicketView()
        await interaction.send(
            RESOLVED_MESSAGE.replace("XXX", claimable_channel.mention), view=view
        )
        await interaction.channel.set_permissions(
            interaction.user, read_messages=True, send_messages=False
        )
        msg = await interaction.original_message()
        await db.log_buttons(self.bot, view, interaction.channel.id, msg.id)

    @slash_command(
        description="Initiates ticket system - creates categories, channels etc",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def initiate_ticket_system(self, interaction):
        claimable_ticket_cat = await get_or_create_claimable_cat(interaction)
        if not claimable_ticket_cat.channels:
            await create_claimable_channel(self.bot, claimable_ticket_cat)
        await get_or_create_active_cat(interaction)
        await get_or_create_resolved_cat(interaction)
        await get_or_create_tickets_log(interaction)
        await interaction.send("Ticket system succesfully initiated", ephemeral=True)


def get_tickets_log_embed(message):
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


async def create_claimable_channel(bot, cat):
    chnl = await cat.create_text_channel(
        name=ChannelName.CLAIMABLE, reason="Making a claimable channel."
    )
    muted_role = uf.get_role(cat.guild, "Muted")
    if muted_role:
        await chnl.set_permissions(muted_role, send_messages=True)
    view = OpenTicketView()
    msg = await chnl.send(CLAIMABLE_CHANNEL_MESSAGE, view=view)
    await db.log_buttons(bot, view, chnl.id, msg.id)


async def get_or_create_tickets_log(interaction):
    resolved_cat = await get_or_create_resolved_cat(interaction)
    tickets_log = uf.get_channel(interaction.guild, ChannelName.TICKETS_LOG)
    if tickets_log is None:
        overwrites = {
            interaction.guild.default_role: PermissionOverwrite(read_messages=False)
        }

        tickets_log = await resolved_cat.create_text_channel(
            name=ChannelName.TICKETS_LOG,
            reason="Making a channel for ticket logs.",
            overwrites=overwrites,
        )
        for mod_role_name in RoleName.mod_role_names():
            role = uf.get_role(interaction.guild, mod_role_name)
            if role is not None:
                await tickets_log.set_permissions(role, read_messages=True)
    return tickets_log


async def get_or_create_claimable_cat(interaction):
    guild = interaction.guild
    claimable_ticket_cat = uf.get_category(guild, CategoryName.CLAIMABLE_TICKETS)
    if claimable_ticket_cat is None:
        claimable_ticket_cat = await guild.create_category(
            name=CategoryName.CLAIMABLE_TICKETS,
            reason="Making a category for claimable tickets.",
        )
    return claimable_ticket_cat


async def get_or_create_active_cat(interaction):
    active_ticket_cat = uf.get_category(interaction.guild, CategoryName.ACTIVE_TICKETS)
    if active_ticket_cat is None:
        active_ticket_cat = await interaction.guild.create_category(
            name=CategoryName.ACTIVE_TICKETS,
            reason="Making a category for claimable tickets.",
        )
    return active_ticket_cat


async def get_or_create_resolved_cat(interaction):
    resolved_ticket_cat = uf.get_category(
        interaction.guild, CategoryName.RESOLVED_TICKETS
    )
    if resolved_ticket_cat is None:
        resolved_ticket_cat = await interaction.guild.create_category(
            name=CategoryName.RESOLVED_TICKETS,
            reason="Making a category for claimable tickets.",
        )
    return resolved_ticket_cat


async def get_highest_num(interaction):
    active_ticket_cat = await get_or_create_active_cat(interaction)
    resolved_ticket_cat = await get_or_create_resolved_cat(interaction)

    num = 0
    for x in active_ticket_cat.channels:
        lst = x.name.split("-")
        try:
            if int(lst[-1]) > num:
                num = int(lst[-1])
        except Exception:
            print(f"debug: {lst} has no number")  # noqa: T201

    for x in resolved_ticket_cat.channels:
        lst = x.name.split("-")
        try:
            if int(lst[-1]) > num:
                num = int(lst[-1])
        except Exception:
            print(f"debug: {lst} has no number")  # noqa: T201

    return num


class OpenTicketView(ui.View):
    def __init__(self, **params):  # noqa: ARG002
        super().__init__(timeout=None)

    @ui.button(style=ButtonStyle.green, label="Open ticket")
    async def create(self, button, interaction):  # noqa: ARG002
        claimable_channel = uf.get_channel(interaction.guild, ChannelName.CLAIMABLE)
        if interaction.channel != claimable_channel:
            await interaction.send(
                f"This command can only be used in {claimable_channel.mention}.",
                ephemeral=True,
            )
            return

        issue_num = await get_highest_num(interaction) + 1

        active_ticket_cat = await get_or_create_active_cat(interaction)
        overwrites = {
            interaction.guild.default_role: PermissionOverwrite(read_messages=False)
        }

        ticket_chnl = await active_ticket_cat.create_text_channel(
            name=f"{interaction.user.name}-{issue_num}",
            reason="Making a ticket.",
            overwrites=overwrites,
        )
        await ticket_chnl.set_permissions(interaction.user, read_messages=True)
        for mod_role_name in RoleName.mod_role_names():
            role = uf.get_role(interaction.guild.roles, name=mod_role_name)
            if role is not None:
                await ticket_chnl.set_permissions(role, read_messages=True)

        await ticket_chnl.send(f"<@{interaction.user.id}> {CLAIMED_MESSAGE}")
        await interaction.send(
            f"You can now head over to {ticket_chnl.mention}.", ephemeral=True
        )


class ResolvedTicketView(ui.View):
    def __init__(self, *, disabled=False, **params):  # noqa: ARG002
        super().__init__(timeout=None)
        if disabled:
            self.reopen.disabled = True
            self.scrap.disabled = True

    @ui.button(style=ButtonStyle.green, label="Reopen ticket")
    async def reopen(self, button, interaction):  # noqa: ARG002
        active_ticket_cat = await get_or_create_active_cat(interaction)
        await interaction.channel.edit(category=active_ticket_cat)
        await interaction.edit(view=ResolvedTicketView(disabled=True))
        await interaction.send(REOPENED_MESSAGE)
        for user in interaction.channel.members:
            await interaction.channel.set_permissions(
                user, read_messages=True, send_messages=True
            )

    @ui.button(style=ButtonStyle.red, label="Scrap ticket")
    async def scrap(self, button, interaction):  # noqa: ARG002
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.send("Only moderators can scrap tickets", ephemeral=True)
            return

        await interaction.send("Scrapping in progress", ephemeral=True)
        tickets_log = await get_or_create_tickets_log(interaction)
        msg_list = await interaction.channel.history(
            limit=500, oldest_first=True
        ).flatten()
        for msg in msg_list:
            emb = get_tickets_log_embed(msg)
            await tickets_log.send(embed=emb)

        await interaction.channel.delete()


def setup(bot):
    bot.add_cog(Tickets(bot))
