"""Create and manage giveaways (legacy)."""

import asyncio
import logging
import random
import re
from datetime import datetime, timedelta

from nextcord import (
    Embed,
    Interaction,
    Member,
    Message,
    RawReactionActionEvent,
    SlashOption,
    slash_command,
)
from nextcord.ext.commands import Bot, Cog

from domain import (
    EMPTY_STRING,
    ID,
    URL,
    ChannelName,
    Color,
    Permissions,
    Standby,
)
from utils import util_functions as uf

logger = logging.getLogger(__name__)

GIVEAWAY_LOCK = asyncio.Lock()
TADA = "🎉"


class Giveaways(Cog):
    def __init__(self) -> None:
        self.standby = Standby()
        self.check_giveaways.start()

    @slash_command(description="Start a giveaway in the #giveaways channel")
    async def giveaway(
        self,
        interaction: Interaction,
        days: int = SlashOption(description="Days until the giveaway finishes"),
        hours: int = SlashOption(description="Hours until the giveaway finishes"),
        minutes: int = SlashOption(description="Minutes until the giveaway finishes"),
        winners: int = SlashOption(description="Number of winners"),
        title: str = SlashOption(description="The title of your giveaway"),
    ) -> None:
        """Start a giveaway in the giveaway channel.

        Permissions for this command must be set manually through the
        Discord integrations men.

        Args:
            interaction (Interaction): Invoking interaction
            days (int): Days until the giveaway finishes
            hours (int): Hours until the giveaway finishes
            minutes (int): Minutes until the giveaway finishes
            winners (int): Number of winners
            title (str): The title of your giveaway
        """
        if days + hours + minutes == 0:
            await interaction.send(
                "Invalid time format, please try again",
                ephemeral=True,
            )
            return

        logger.info("Starting giveaway")
        end_time = uf.utcnow() + timedelta(days=days, hours=hours, minutes=minutes)
        embed = giveaway_embed(end_time, winners, interaction.user, title)
        giveaway_channel = uf.get_channel(ChannelName.GIVEAWAYS)
        giveaway = await giveaway_channel.send(embed=embed)
        await giveaway.add_reaction(TADA)
        await interaction.send(
            f"Giveaway started in {giveaway_channel.mention}!",
            ephemeral=True,
        )

    @slash_command(
        description="Mod commands for editing giveaways",
        default_member_permissions=Permissions.MODS_AND_GUIDES,
    )
    async def giveaway_tools(self, interaction: Interaction) -> None:
        """Command group for managing running giveaways."""

    @giveaway_tools.subcommand(description="Manually end a giveaway")
    async def finish(
        self,
        interaction: Interaction,
        message_id: int = SlashOption(
            description="ID of the giveaway (leave blank to use last active giveaway)",
            default=0,
        ),
    ) -> None:
        """Finish a giveaway early.

        Args:
            interaction (Interaction): Invoking interaction
            message_id (int, optional): ID of the giveaway message.
                Defaults to the last active giveaway)
        """
        logger.info(f"Finishing giveaway with {message_id=}")
        channel = uf.get_channel(ChannelName.GIVEAWAYS)

        if message_id != 0:
            try:
                giveaway = await channel.fetch_message(message_id)
                if is_active_giveaway(giveaway):
                    await finish_giveaway(giveaway)
                    await interaction.send("Giveaway finished", ephemeral=True)
            except Exception:
                await interaction.send(
                    "No active giveaway found with that ID",
                    ephemeral=True,
                )

        else:
            await GIVEAWAY_LOCK.acquire()
            try:
                async for message in channel.history(limit=50):
                    if is_active_giveaway(message):
                        await finish_giveaway(message)
                        await interaction.send("Giveaway finished", ephemeral=True)
                        return
            finally:
                GIVEAWAY_LOCK.release()

    @giveaway_tools.subcommand(description="Draw a new winner for a giveaway")
    async def redraw(  # noqa: C901, PLR0912
        self,
        interaction: Interaction,
        number: int = SlashOption(description="number of winners to redraw"),
        message_id: int = SlashOption(
            description="ID of the giveaway (leave blank to use the last giveaway)",
            default=0,
        ),
    ) -> None:
        """Draw new winner(s) for a finished giveaway.

        Args:
            interaction (Interaction): Invoking interaction
            number (int): Number of winners to redraw
            message_id (int, optional): ID of the giveaway message.
                Defaults to the last active giveaway
        """
        logger.info(f"Redrawing {number} winners for giveaway with {message_id=}")
        channel = uf.get_channel(ChannelName.GIVEAWAYS)
        giveaway = None
        if message_id == 0:
            async for message in channel.history():
                if (
                    message.embeds
                    and len(message.embeds[0].fields) >= 4  # noqa: PLR2004
                    and (message.embeds[0].fields[3].name == "Winner #1")
                ):
                    giveaway = message
                    break
        else:
            try:
                message = await channel.fetch_message(id)
                if (
                    message.embeds
                    and len(message.embeds[0].fields) >= 4  # noqa: PLR2004
                    and (message.embeds[0].fields[3].name == "Winner #1")
                ):
                    giveaway = message
                else:
                    await interaction.send(
                        "No finished giveaway found with that ID",
                        ephemeral=True,
                    )
                    return
            except Exception:
                await interaction.send("No message found with that ID", ephemeral=True)
                return

        if giveaway is not None:
            winners = [
                field.value
                for field in giveaway.embeds[0].fields
                if field.name.startswith("Winner") and field.value != "None"
            ]

            users = await who_reacted(giveaway, TADA)

            eligible = [user.mention for user in users if user.mention not in winners]

            if len(eligible) == 0:
                await giveaway.channel.send(
                    "All who entered the giveaway won a prize - "
                    "there are no more names to draw from.",
                )
                return
            if number > len(eligible):
                if len(eligible) == 1:
                    await giveaway.channel.send(
                        "There is only 1 entrant left to draw from.",
                    )
                else:
                    await giveaway.channel.send(
                        f"There are only {len(eligible)} entrants left to draw from.",
                    )
                number = len(eligible)

            new_winners = random.sample(eligible, number)

            if len(new_winners) == 1:
                await giveaway.channel.send(
                    f"{TADA} The new winner is {new_winners[0]}! Congratulations!",
                )
            else:
                await giveaway.channel.send(
                    f"{TADA} The new winners are {', '.join(new_winners[:-1])} and "
                    f"{new_winners[-1]}! Congratulations!",
                )

            await interaction.send("Winner(s) successfully redrawn", ephemeral=True)

    @giveaway_tools.subcommand(description="Edits the number of winners for a giveaway")
    async def change(
        self,
        interaction: Interaction,
        new_number: int = SlashOption(
            description="The number of winners the giveaway should have",
            min_value=1,
        ),
        message_id: int = SlashOption(
            description="ID of the giveaway (leave blank to use the last giveaway)",
            default=0,
        ),
    ) -> None:
        """Edit the number of winners in a running giveaway.

        Args:
            interaction (Interaction): Invoking interaction
            new_number (int): New number of winners.
            message_id (int, optional): ID of the giveaway message.
                Defaults to the last active giveaway
        """
        logger.info(f"Changing number of winners for giveway with {message_id=}")
        channel = uf.get_channel(ChannelName.GIVEAWAYS)
        giveaway = None

        if message_id != 0:
            try:
                message = await channel.fetch_message(message_id)
                if is_finished_giveaway(message):
                    giveaway = message
                else:
                    await interaction.send(
                        "No finished giveaway found with that ID",
                        ephemeral=True,
                    )
                    return
            except Exception:
                await interaction.send("No message found with that ID", ephemeral=True)

        else:
            async for message in channel.history():
                if is_active_giveaway(message):
                    giveaway = message
                    break

        if giveaway is not None:
            embed = giveaway.embeds[0]
            text = embed.footer.text
            old_num = int(re.search(r"(\d+) winner", text).group(1))
            text = re.sub(r"(\d+) winner", f"{new_number} winner", text)
            if old_num == 1:
                text = re.sub("winner", "winners", text)
            elif new_number == 1:
                text = re.sub("winners", "winner", text)
            embed.set_footer(text=text)
            await giveaway.edit(embed=embed)
            await interaction.send("Number of winners successfully changed")

    @uf.delayed_loop(minutes=1)
    async def check_giveaways(self) -> None:
        """Check if any giveaway has finished."""
        giveaway_channel = uf.get_channel(ChannelName.GIVEAWAYS)
        if not giveaway_channel:
            logger.exception("Giveaway channel not found")
            return

        await GIVEAWAY_LOCK.acquire()
        active_giveaway_field_count = 3
        try:
            async for message in giveaway_channel.history(limit=25):
                if (
                    message.embeds
                    and len(message.embeds[0].fields) >= active_giveaway_field_count
                    and (message.embeds[0].fields[2].name == "Time remaining")
                ):
                    await update_giveaway(message)
        finally:
            GIVEAWAY_LOCK.release()


async def who_reacted(message: Message, emoji: str) -> list[Member]:
    """Get users who reacted to the message with the provided emoji.

    Args:
        message (Message): Message to check
        emoji (str): Emoji to check

    Returns:
        list[Member]: Users who reacted to the message with that emoji
    """
    reactions = message.reactions
    users = []
    for reaction in reactions:
        if reaction.emoji == emoji:
            async for user in reaction.users():
                if user.id != ID.BOT:
                    users.append(user)  # noqa: PERF401
    return users


async def giveaway_handler(payload: RawReactionActionEvent) -> None:
    """Remove TADA reactions from finished events."""
    if not isinstance(payload, RawReactionActionEvent):
        return
    channel = Standby().bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    if (
        payload.emoji.name == TADA
        and payload.user_id != ID.BOT
        and message.embeds
        and (re.search("finished", message.embeds[0].description))
    ):
        await message.remove_reaction(TADA, payload.member)


async def update_giveaway(giveaway: Message) -> None:
    """Update a giveaway message's remaining time."""
    embed = giveaway.embeds[0]
    end_time = embed.timestamp
    delta = end_time - uf.utcnow()
    if delta == timedelta(seconds=0) or delta.days < 0:
        await finish_giveaway(giveaway)
    else:
        embed.set_field_at(2, name="Time remaining", value=delta_to_text(delta))
        await giveaway.edit(embed=embed)


async def finish_giveaway(giveaway: Message) -> None:
    """Finish a giveaway."""
    embed = giveaway.embeds[0]
    embed.description = EMPTY_STRING + "\nThe giveaway has finished!\n" + EMPTY_STRING
    embed.set_field_at(1, name=EMPTY_STRING, value=EMPTY_STRING)
    embed.set_field_at(2, name=EMPTY_STRING, value=EMPTY_STRING)
    embed.set_footer(text=re.sub("Ends", "Ended", embed.footer.text))
    embed.timestamp = uf.utcnow()

    num_winners = int(re.search("^(.+) winner", embed.footer.text).group(1))
    message = f"{giveaway.jump_url}\n"
    users = await who_reacted(giveaway, TADA)
    if len(users) == 0:
        message += "No winner could be determined."
    else:
        message += "Congratulations"
        if len(users) >= num_winners:
            winners = random.sample(users, num_winners)
        else:
            winners = users
            random.shuffle(winners)
        for winner in winners:
            embed.add_field(
                name=f"Winner #{winners.index(winner) + 1}",
                value=winner.mention,
            )
            message += f" {winner.mention}"
        for i in range(len(users), num_winners):
            embed.add_field(name=f"Winner #{i + 1}", value="None")
        message += (
            f"!\nYou have won the {embed.title[8:-8].lower().strip()}!\n"
            f"Contact {embed.fields[0].value} for your prize."
        )

    await giveaway.edit(embed=embed)
    await giveaway.channel.send(message)


def is_active_giveaway(message: Message) -> bool:
    """Check if a message contains an active giveaway."""
    return (
        message.embeds
        and len(message.embeds[0].fields) > 2  # noqa: PLR2004
        and message.embeds[0].fields[2].name == "Time remaining"
    )


def is_finished_giveaway(message: Message) -> bool:
    """Check if a message contains a finished giveaway."""
    return (
        message.embeds
        and len(message.embeds[0].fields) >= 4  # noqa: PLR2004
        and message.embeds[0].fields[3].name == "Winner #1"
    )


def giveaway_embed(
    end_time: datetime,
    winners: int,
    author: Member,
    title: str,
) -> Embed:
    """Create a giveaway embed.

    Args:
        end_time (datetime): Giveaway finish time
        winners (int): Number of winners
        author (Member): Giveaway author
        title (str): Giveaway title

    Returns:
        Embed: Embed containing giveaway details.
    """
    embed = Embed(color=Color.LIGHT_BLUE)
    embed.title = ":tada:**   " + title.upper() + " GIVEAWAY   **:tada:"
    remaining = delta_to_text(end_time - uf.utcnow())
    embed.description = EMPTY_STRING + "\nReact with :tada: to enter!\n" + EMPTY_STRING

    winner_text = f"{winners} winner"
    if winners > 1:
        winner_text += "s"

    embed.set_footer(text=winner_text + "  •  Ends at")
    embed.timestamp = end_time
    embed.add_field(name="Hosted by", value=author.mention)
    embed.add_field(name=EMPTY_STRING, value=EMPTY_STRING)
    embed.add_field(name="Time remaining", value=remaining)
    embed.set_thumbnail(URL.GITHUB_STATIC + "/images/presents.png")
    return embed


def delta_to_text(delta: timedelta) -> str:
    """Convert a timedelta to human readable text.

    Args:
        delta (timedelta): Timedelta

    Returns:
        str: Text in the format "5 days, 3 hours, 2 minutes"
    """
    parts = []
    if delta.days != 0:
        day_text = f"**{delta.days}** day"
        if delta.days > 1:
            day_text += "s"
        parts.append(day_text)

    hours, seconds = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if hours > 0:
        hour_text = f"**{hours}** hour"
        if hours > 1:
            hour_text += "s"
        parts.append(hour_text)

    if minutes > 0:
        minute_text = f"**{minutes}** minute"
        if minutes > 1:
            minute_text += "s"
        parts.append(minute_text)

    if seconds > 0:
        second_text = f"**{seconds}** second"
        if seconds > 1:
            second_text += "s"
        parts.append(second_text)

    return ", ".join(parts)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Giveaways())
