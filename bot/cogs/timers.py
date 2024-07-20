"""Create and manage timers."""

import json
import logging
from datetime import datetime, timedelta

from nextcord import Interaction, SlashOption, slash_command
from nextcord.ext.commands import Bot, Cog

from db_integration import db_functions as db
from domain import Standby, TimerType
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class Timers(Cog):
    def __init__(self) -> None:
        self.standby = Standby()
        self.check_reminders.start()

    @uf.delayed_loop(seconds=10)
    async def check_reminders(self) -> None:
        """Check if any reminder timers have expired."""
        try:
            gtable = await self.standby.pg_pool.fetch(
                f"SELECT * FROM tmers WHERE ttype={TimerType.REMINDER}",
            )
        except AttributeError:
            logger.exception("Bot hasn't loaded yet - pg_pool doesn't exist")
            return
        except Exception:
            logger.exception("Unexpected error")
            return

        for rec in gtable:
            timenow = datetime.now()
            if timenow <= rec["expires"]:
                continue

            logger.info("Reminder timer expired")

            params_dict = json.loads(rec["params"])
            if "msg" not in params_dict or "channel" not in params_dict:
                logger.warning(f"Deleting invalid json: {params_dict}")
                await self.standby.pg_pool.execute(
                    "DELETE FROM tmers WHERE tmer_id = $1;",
                    rec["tmer_id"],
                )
                continue

            channel = self.standby.bot.get_channel(params_dict["channel"])
            if not channel:
                logger.warning(f"Could not find {channel=}")

            location = params_dict.get("location", "This channel")
            message = (
                f"<@{rec['usr_id']}> "
                f"{uf.dynamic_timestamp(rec['expires'], 'date and time')}: "
                f"{params_dict['msg']}"
            )
            try:
                confirmation_id = params_dict["confirmation_id"]
                confirmation = await channel.fetch_message(confirmation_id)
                message += " " + confirmation.jump_url
            except Exception:
                logger.exception("Could not find confirmation mesage id")

            if location in ["This channel", "Both"]:
                await channel.send(message)

            if location == "DM":
                user = await self.standby.guild.fetch_member(rec["usr_id"])
                await user.send(message)

            await self.standby.pg_pool.execute(
                "DELETE FROM tmers WHERE tmer_id = $1;",
                rec["tmer_id"],
            )

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
        location: str = SlashOption(
            description="Where to send the reminder",
            choices=["This channel", "DM", "Both"],
            default="This channel",
        ),
    ) -> None:
        """Create a reminder that triggers after the specified delay.

        Args:
            interaction (Interaction): Invoking interaction
            days (int): Days until the reminder
            hours (int): Hours until the reminder
            minutes (int): Minutes until the reminder
            message (str): A message for the reminder
            location (str, optional): Where to send the reminder. Can be
                in the interaction channel, as a DM, or both.
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

        logger.info(f"Creating reminder for {interaction.user}")
        now = datetime.now()
        delta = timedelta(days=days, hours=hours, minutes=minutes)
        expires = now + delta
        expires = expires.replace(microsecond=0)

        confirmation = await interaction.send(
            f"{uf.dynamic_timestamp(now, 'short time')}: Your reminder has been "
            "registered and you will be reminded "
            f"on {uf.dynamic_timestamp(expires, 'date and time')}.",
        )
        full_confirmation = await confirmation.fetch()
        await create_reminder(
            interaction,
            expires,
            message,
            full_confirmation.id,
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
        location: str = SlashOption(
            description="Where to send the reminder",
            choices=["This channel", "DM", "Both"],
            default="This channel",
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
        now = datetime.now()
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

        logger.info(f"Creating reminder for {interaction.user}")
        confirmation = await interaction.send(
            f"{uf.dynamic_timestamp(now, 'short time')}: Your reminder has been "
            "registered and you will be reminded "
            f"on {uf.dynamic_timestamp(expires, 'date and time')}.",
        )
        full_confirmation = await confirmation.fetch()
        await create_reminder(
            interaction,
            expires,
            message,
            full_confirmation.id,
            location,
        )


async def create_reminder(
    interaction: Interaction,
    tfuture: datetime,
    message: str,
    confirmation_id: int,
    location: str,
) -> None:
    """Store the reminder in the database.

    Args:
        interaction (Interaction): Invoking interaction
        tfuture (datetime): Reminder time
        message (str): Reminder message
        confirmation_id (int): ID of the confirmation message.
            Used to send the reminder as a reply
        location (str): Where to send the reminder
    """
    await db.ensure_guild_existence(interaction.guild.id)
    await db.get_or_insert_usr(interaction.user.id)

    params_dict = {
        "msg": message,
        "channel": interaction.channel.id,
        "confirmation_id": confirmation_id,
        "location": location,
    }
    params_json = json.dumps(params_dict)

    await Standby().pg_pool.execute(
        "INSERT INTO tmers (usr_id, expires, ttype, params) VALUES ($1, $2, $3, $4);",
        interaction.user.id,
        tfuture,
        TimerType.REMINDER,
        params_json,
    )


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Timers())
