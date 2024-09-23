"""Congratulate users on their birthdays."""

import logging
from datetime import date, datetime

from asyncpg.exceptions import UniqueViolationError
from nextcord import Interaction, Member, SlashOption, slash_command
from nextcord.ext.commands import Bot, Cog

from domain import ChannelName, RoleName, SQLResult, Standby
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
        month: str = SlashOption(
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
            month (str): Birth month.
            day (int): Birth day
        """
        birthday_string = f"{day} {month} 2000"  # Leap year
        try:
            birthday = datetime.strptime(birthday_string, "%d %B %Y")
        except ValueError:
            await interaction.send("Invalid date - please try again.", ephemeral=True)
            return

        result = await set_user_birthday(interaction.user, birthday)

        if result == SQLResult.INSERT:
            logger.info(f"Setting {interaction.user}'s birthday to {month} {day}")
            await interaction.send("Your birthday has been set.", ephemeral=True)

        elif result == SQLResult.UPDATE:
            logger.info(f"Updating {interaction.user}'s birthday to {month} {day}")
            await interaction.send("Your birthday has been updated.", ephemeral=True)

        else:
            await interaction.send(
                "There was an error setting your birthday",
                ephemeral=True,
            )

    @birthday.subcommand(description="Remove your birthday")
    async def remove(self, interaction: Interaction) -> None:
        """Remove a user's stored birthday.

        Args:
            interaction (Interaction): Invoking interaction
        """
        status = await remove_user_birthday(interaction.user)
        if status == SQLResult.DELETE:
            logger.info(f"Removing {interaction.user}'s birthday")
            await interaction.send("Birthday removed.", ephemeral=True)
        else:
            await interaction.send("You have not set your birthday.", ephemeral=True)

    @birthday.subcommand(description="Check your birthday (only visible to you)")
    async def check(self, interaction: Interaction) -> None:
        """Privately checks the user's set birthday.

        Args:
            interaction (Interaction): Invoking interaction
        """
        birthday = await get_user_birthday(interaction.user)
        if birthday is None:
            await interaction.send("You have not set your birthday.", ephemeral=True)
        else:
            await interaction.send(
                f"Your birthday is set to {birthday.strftime('%B %-d')}",
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

        logger.debug("Checking birthdays")
        birthday_role = uf.get_role(RoleName.BIRTHDAY)

        async for member in self.standby.guild.fetch_members():
            if birthday_role in member.roles:
                await member.remove_roles(birthday_role)

        birthday_haver_ids = await get_birthday_havers()

        if not birthday_haver_ids:
            logger.info("No birthdays today")
            return

        mentions = []
        for user_id in birthday_haver_ids:
            member = await self.standby.guild.fetch_member(user_id)

            logger.info(f"Adding birthday role to {member}")
            await member.add_roles(birthday_role)

            mentions.append(member.mention)

        if len(mentions) > 1:
            congrats = ", ".join(mentions[:-1]) + " and " + str(mentions[-1])
        else:
            congrats = mentions[0]

        general = uf.get_channel("general")
        await general.send("🎂🎂🎂")
        await general.send(f"Happy Birthday {congrats}!")


async def set_user_birthday(user: Member, birthday: date) -> SQLResult:
    """Set or update birthday."""
    pg_pool = Standby().pg_pool
    schema = Standby().schema
    try:
        await pg_pool.execute(f"""
            INSERT INTO
                {schema}.birthday (user_id, birth_date)
            VALUES
                ({user.id}, '{birthday}')
            """)
        return SQLResult.INSERT
    except UniqueViolationError:
        await pg_pool.execute(f"""
            UPDATE {schema}.birthday
            SET
                birth_date = '{birthday}'
            WHERE
                user_id = {user.id}
            """)
        return SQLResult.UPDATE
    except Exception:
        logger.exception("Unknown exception when setting birthday")


async def remove_user_birthday(user: Member) -> SQLResult:
    """Remove birthday."""
    pg_pool = Standby().pg_pool
    schema = Standby().schema
    status = await pg_pool.execute(f"""
        DELETE FROM {schema}.birthday
        WHERE
            user_id = {user.id}
        """)
    if status == "DELETE 0":
        return SQLResult.NONE
    return SQLResult.DELETE


async def get_user_birthday(user: Member) -> datetime | None:
    """Get birthday (if set)."""
    pg_pool = Standby().pg_pool
    schema = Standby().schema
    record = await pg_pool.fetchrow(f"""
        SELECT
            birth_date
        FROM
            {schema}.birthday
        WHERE
            user_id = {user.id}
        """)
    if record:
        return record["birth_date"]
    return None


async def get_birthday_havers() -> list[int]:
    """Get today's birthday havers."""
    pg_pool = Standby().pg_pool
    schema = Standby().schema
    today_2000 = datetime.today().date().replace(year=2000)
    records = await pg_pool.fetch(f"""
        SELECT
            user_id
        FROM
            {schema}.birthday
        WHERE
            birth_date = '{today_2000}'
        """)
    if records:
        return [record["user_id"] for record in records]
    return []


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Birthdays())
