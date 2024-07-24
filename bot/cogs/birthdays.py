"""Congratulate users on their birthdays."""

import logging
from datetime import datetime

import nextcord.utils
from nextcord import Interaction, SlashOption, slash_command
from nextcord.ext.commands import Bot, Cog

from db_integration import db_functions as db
from domain import RoleName, Standby
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class Birthdays(Cog):
    def __init__(self) -> None:
        self.standby = Standby()
        self.check_bdays.start()

    @slash_command(description="Commands for accessing birthday functionality")
    async def birthday(self, interaction: Interaction) -> None:
        """Command group for birthday functionality."""

    @birthday.subcommand(description="Set your birthday")
    async def set(
        self,
        interaction: Interaction,
        month_name: str = SlashOption(
            name="month",
            description="Your birth month",
            choices=[
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ],
        ),
        day: int = SlashOption(
            min_value=1,
            max_value=31,
            description="Your birth date",
        ),
    ) -> None:
        """Store a user's birthday in the database.

        Args:
            interaction (Interaction): Invoking interaction
            month_name (str): Birth month.
            day (int): Birth day
        """
        month = uf.month_to_int(month_name)
        try:
            datetime(2000, month, day)
        except ValueError:
            await interaction.send("Invalid date - please try again.", ephemeral=True)
            return

        await db.ensure_guild_existence(interaction.guild.id)
        await db.get_or_insert_usr(interaction.user.id)

        exists = await self.standby.pg_pool.fetch(
            f"SELECT * FROM bdays WHERE usr_id = {interaction.user.id}",
        )

        if exists:
            logger.info(f"Updating {interaction.user}'s birthday to {day} {month_name}")
            await self.standby.pg_pool.execute(
                f"UPDATE bdays SET month = {month}, day = {day} "
                f"WHERE usr_id = {interaction.user.id}",
            )
        else:
            logger.info(f"Setting {interaction.user}'s birthday to {day} {month_name}")
            await self.standby.pg_pool.execute(
                "INSERT INTO bdays (usr_id, month, day) VALUES ($1, $2, $3);",
                interaction.user.id,
                month,
                day,
            )

        await interaction.send("Your birthday has been set.", ephemeral=True)

    @birthday.subcommand(description="Remove your birthday")
    async def remove(self, interaction: Interaction) -> None:
        """Remove a user's stored birthday.

        Args:
            interaction (Interaction): Invoking interaction
        """
        exists = await self.standby.pg_pool.fetch(
            f"SELECT * FROM bdays WHERE usr_id = {interaction.user.id}",
        )
        if not exists:
            await interaction.send("You have not set your birthday.", ephemeral=True)
        else:
            logger.info(f"Removing {interaction.user}'s birthday")
            await self.standby.pg_pool.execute(
                f"DELETE FROM bdays WHERE usr_id = {interaction.user.id};",
            )
            await interaction.send("Birthday removed.", ephemeral=True)

    @birthday.subcommand(description="Check your birthday (only visible to you)")
    async def check(self, interaction: Interaction) -> None:
        """Privately checks the user's set birthday.

        Args:
            interaction (Interaction): Invoking interaction
        """
        exists = await self.standby.pg_pool.fetch(
            f"SELECT * FROM bdays WHERE usr_id = {interaction.user.id}",
        )
        if not exists:
            await interaction.send("You have not set your birthday.", ephemeral=True)
        else:
            await interaction.send(
                "Your birthday is set to "
                f"{uf.int_to_month(exists[0]['month'])} {exists[0]['day']}.",
                ephemeral=True,
            )

    @uf.delayed_loop(hours=1)
    async def check_bdays(self) -> None:
        """Loop that checks whether it is any user's birthday.

        Triggers once a day between 8 and 9 AM (bot time)
        """
        now = uf.now()

        if now.hour != 8:  # noqa: PLR2004
            return

        logger.info("Checking birthdays")
        await self.standby.bot.wait_until_ready()

        bday_role = uf.get_role(RoleName.BIRTHDAY)

        async for member in self.standby.guild.fetch_members():
            if bday_role in member.roles:
                logger.info(f"Removing birthday role from {member}")
                await member.remove_roles(bday_role)

        gtable = await self.standby.pg_pool.fetch(
            f"SELECT * FROM bdays WHERE month = {now.month} AND day = {now.day}",
        )

        if not gtable:
            logger.info("No birthdays today")
            return

        bday_havers = []

        for rec in gtable:
            member = await self.standby.guild.fetch_member(rec["usr_id"])

            logger.info(f"Adding birthday role to {member}")
            await member.add_roles(bday_role)

            bday_havers.append(member.mention)

        if len(bday_havers) > 1:
            bday_havers = ", ".join(bday_havers[:-1]) + " and " + str(bday_havers[-1])
        else:
            bday_havers = bday_havers[0]
        general = nextcord.utils.get(self.bot.get_all_channels(), name="general")
        await general.send("🎂🎂🎂")
        await general.send(f"Happy Birthday {bday_havers}!")


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Birthdays())
