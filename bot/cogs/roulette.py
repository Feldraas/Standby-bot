"""Void roulette."""

import logging
import random
from datetime import datetime, timedelta

from nextcord import Interaction, Member, slash_command
from nextcord.errors import Forbidden
from nextcord.ext.commands import Bot, Cog

from domain import Standby
from utils import util_functions as uf

logger = logging.getLogger(__name__)

ROULETTE_TIMEOUT = timedelta(minutes=30)


class Roulette(Cog):
    def __init__(self) -> None:
        self.standby = Standby()
        self.timed_out_mods: dict[Member, datetime] = {}

    @slash_command(description="Do you feel lucky?")
    async def roulette(self, interaction: Interaction) -> None:
        """Play Void roulette.

        Losing results in a timeout. Winning streaks are recorded.

        Args:
            interaction (Interaction): Invoking interaction
        """
        if interaction.user in self.timed_out_mods:
            expires = self.timed_out_mods[interaction.user]
            if expires > uf.now():
                await interaction.send(
                    "You have been timed out from using this command. "
                    "You will be able to use it again "
                    f"{uf.dynamic_timestamp(expires, 'relative')}",
                    ephemeral=True,
                )
                return
            del self.timed_out_mods[interaction.user]

        win = random.randint(1, 6) != 6  # noqa: PLR2004
        await record_roulette_result(interaction.user, win=win)

        if not win:
            lose_message = (
                f"Not all risks pay off, {interaction.user.mention}. "
                "Your streak has been reset and you have been timed out."
            )
            try:
                await interaction.user.timeout(ROULETTE_TIMEOUT)
            except Forbidden:
                lose_message = lose_message[:-1] + " from using this command."
                self.timed_out_mods[interaction.user] = uf.now() + ROULETTE_TIMEOUT
            finally:
                await interaction.send(lose_message)

            return

        streaks = await get_streaks(interaction.user)
        current_streak, max_streak, server_current_max, server_alltime_max = streaks

        plural_suffix = "s" if current_streak > 1 else ""
        win_message = (
            "Luck is on your side! You have now survived for "
            f"{current_streak} round{plural_suffix} in a row"
        )

        if current_streak > server_alltime_max:
            win_message += ", a new all-time record for the server!"
        elif current_streak > server_current_max and current_streak > max_streak:
            win_message += (
                ", the highest currently active streak and a new personal best!"
            )
        elif current_streak > server_current_max:
            win_message += ", the highest currently active streak!"
        elif current_streak > max_streak:
            win_message += ", a new personal best!"
        else:
            win_message += "."

        await interaction.send(win_message)


async def record_roulette_result(user: Member, *, win: bool) -> None:
    """Record result in database."""
    standby = Standby()
    await standby.pg_pool.execute(
        f"""
        INSERT INTO
            {standby.schema}.roulette (user_id, played_at, win)
        VALUES
            ($1, $2, $3)
        """,
        user.id,
        uf.now(),
        win,
    )


async def get_streaks(user: Member) -> tuple[int, int, int, int]:
    """Get streaks for the provided user and for the server.

    Args:
        user (Member): User to look up

    Returns:
        tuple[int, int, int, int]: Current and maximum streaks for
            the provided user, current and all-time highest streaks
            for the server.
    """
    standby = Standby()
    records = await standby.pg_pool.fetch(f"""
        SELECT
            user_id,
            win
        FROM
            {standby.schema}.roulette
        ORDER BY
            played_at,
            user_id
        """)
    user_current = user_max = server_current = 0
    server_max = 40  # Carried over

    user_ids = {record["user_id"] for record in records}
    for user_id in user_ids:
        results = [record["win"] for record in records if record["user_id"] == user_id]
        current, maximum = parse_results(results)
        if user_id == user.id:
            user_current = current
            user_max = maximum
        else:
            server_current = max(server_current, current)
            server_max = max(server_max, maximum)

    return user_current, user_max, server_current, server_max


def parse_results(results: list[bool]) -> tuple[int, int]:
    """Find current and maximum streak lengths.

    Args:
        results (list[bool]): List of outcomes

    Returns:
        tuple[int, int]: Current and maximum streak
    """
    false_indices = [i for i, res in enumerate(results) if res is False]
    false_indices = [-1, *false_indices, len(results)]
    streaks = [
        false_indices[i] - false_indices[i - 1] - 1
        for i in range(1, len(false_indices))
    ]

    return streaks[-1], max([0, *streaks[:-1]])


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Roulette())
