"""Create and manage timers."""

import logging
from datetime import datetime, timedelta
from enum import IntFlag, auto

from asyncpg import Record
from nextcord import Interaction, SlashOption, slash_command
from nextcord.ext.commands import Bot, Cog

from domain import Standby
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class ReminderLocation(IntFlag):
    CHANNEL = auto()
    DM = auto()
    BOTH = CHANNEL & DM


class Timers(Cog):
    def __init__(self) -> None:
        self.standby = Standby()
        self.check_reminders.start()

    @slash_command(description="Commands for setting reminders")
    async def remindme(self, interaction: Interaction) -> None:
        """Command group for setting reminders."""

    @remindme.subcommand(description="Reminds you after a specified time", name="in")
    async def remindme_in(
        self,
        interaction: Interaction,
        days: int = SlashOption(description="Days until the reminder", min_value=0),
        hours: int = SlashOption(description="Hours until the reminder", min_value=0),
        minutes: int = SlashOption(
            description="Minutes until the reminder",
            min_value=0,
        ),
        message: str = SlashOption(description="A message for the reminder"),
        location: int = SlashOption(
            description="Where to send the reminder",
            choices={
                "This channel": ReminderLocation.CHANNEL,
                "DM": ReminderLocation.DM,
                "Both": ReminderLocation.BOTH,
            },
            default=ReminderLocation.CHANNEL,
        ),
    ) -> None:
        """Create a reminder that triggers after the specified delay.

        Args:
            interaction (Interaction): Invoking interaction
            days (int): Days until the reminder
            hours (int): Hours until the reminder
            minutes (int): Minutes until the reminder
            message (str): A message for the reminder
            location (ReminderLocation, optional): Where to send the
                reminder. Can be in the interaction channel, as a DM,
                or both.
        """
        if days + hours + minutes == 0:
            await interaction.send(
                ephemeral=True,
                file=uf.simpsons_error_image(
                    dad=interaction.guild.me,
                    son=interaction.user,
                    text="Invalid time format",
                ),
            )
            return

        logger.debug(f"Creating reminder for {interaction.user}")
        now = uf.now()
        expires = now + timedelta(days=days, hours=hours, minutes=minutes)

        await create_reminder(
            interaction,
            expires,
            message,
            location,
        )

    @remindme.subcommand(
        description="Reminds you at a specified date and time",
        name="at",
    )
    async def remindme_at(
        self,
        interaction: Interaction,
        year: int = SlashOption(description="Year of the reminder"),
        month: int = SlashOption(description="Month of the reminder"),
        day: int = SlashOption(description="Day of the reminder"),
        hour: int = SlashOption(description="Hour of the reminder"),
        minute: int = SlashOption(description="Minute of the reminder"),
        message: str = SlashOption(description="A message for the reminder"),
        location: int = SlashOption(
            description="Where to send the reminder",
            choices={
                "This channel": ReminderLocation.CHANNEL,
                "DM": ReminderLocation.DM,
                "Both": ReminderLocation.BOTH,
            },
            default=ReminderLocation.CHANNEL,
        ),
    ) -> None:
        """Create a reminder that triggers at a specified point in time.

        Args:
            interaction (Interaction): Invoking interaction.
            year (int): Year of the reminder
            month (int): Month of the reminder
            day (int): Day of the reminder
            hour (int): Hour of the reminder
            minute (int): Minute of the reminder
            message (str): A message for the reminder
            location (str, optional): Where to send the reminder. Can be
                in the interaction channel, as a DM, or both.
        """
        now = uf.now()
        try:
            expires = datetime(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                tzinfo=now.tzinfo,
            )
        except ValueError:
            await interaction.send(
                "Please input a valid date and time.",
                ephemeral=True,
            )
            return

        if expires < now:
            await interaction.send(
                "You must choose a time that's in the future "
                f"(current bot time is {now.strftime('%H:%M')}).",
                ephemeral=True,
            )
            return

        logger.debug(f"Creating reminder for {interaction.user}")
        await create_reminder(
            interaction,
            expires,
            message,
            location,
        )

    @uf.delayed_loop(seconds=10)
    async def check_reminders(self) -> None:
        """Check if any reminder timers have expired."""
        expired_reminders = await get_expired_reminders()

        for reminder in expired_reminders:
            logger.info("Reminder timer expired")

            creation_time = uf.dynamic_timestamp(
                reminder["created_at"],
                "date and time",
            )
            if reminder["channel_id"]:
                channel = self.standby.bot.get_channel(reminder["channel_id"])
                original_message = await channel.fetch_message(reminder["message_id"])

                mention = uf.id_to_mention(reminder["user_id"])
                await channel.send(
                    f"Reminder for {mention}, created at {creation_time}:\n"
                    f"{reminder['message']}\n",
                    reference=original_message,
                )

            if reminder["send_dm"]:
                user = await self.standby.guild.fetch_member(reminder["user_id"])
                await user.send(
                    f"Your reminder, created at {creation_time}, "
                    f"has expired:\n{reminder['message']}",
                )

            await delete_reminder(reminder["reminder_id"])


async def create_reminder(
    interaction: Interaction,
    expires: datetime,
    message: str,
    location: ReminderLocation,
) -> None:
    """Store the reminder in the database.

    Args:
        interaction (Interaction): Invoking interaction
        expires (datetime): Reminder expiration time
        message (str): Reminder message
        location (str): Where to send the reminder
    """
    expire_string = uf.dynamic_timestamp(expires, "date and time")
    response = await interaction.send(
        "Your reminder has been registered "
        f"and you will be reminded on {expire_string}",
        ephemeral=location == ReminderLocation.DM,
    )

    location = ReminderLocation(location)  # Discord returns it as an int

    if location in ReminderLocation.CHANNEL:
        response = await response.fetch()
        channel_id = response.channel.id
        message_id = response.id
    else:
        channel_id = message_id = None

    send_dm = location in ReminderLocation.DM

    standby = Standby()
    await standby.pg_pool.execute(
        f"""
        INSERT INTO
            {standby.schema}.reminder (
                user_id,
                created_at,
                expires_at,
                message,
                channel_id,
                message_id,
                send_dm
            )
        VALUES
            ($1, $2, $3, $4, $5, $6, $7)
        """,
        interaction.user.id,
        uf.now(),
        expires,
        message,
        channel_id,
        message_id,
        send_dm,
    )


async def get_expired_reminders() -> list[Record]:
    """Fetch expired reminders from database."""
    standby = Standby()
    return await standby.pg_pool.fetch(f"""
        SELECT
            *
        FROM
            {standby.schema}.reminder
        WHERE
            expires_at < '{uf.now()}'
        """)


async def delete_reminder(reminder_id: int) -> None:
    """Delete a reminder from the database."""
    standby = Standby()
    return await standby.pg_pool.execute(f"""
        DELETE FROM
            {standby.schema}.reminder
        WHERE
            reminder_id = {reminder_id}
        """)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Timers())
