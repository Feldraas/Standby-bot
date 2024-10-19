"""Generate leaderboards for various stats."""

import logging
from enum import StrEnum

from nextcord import Embed, Interaction, SlashOption, slash_command
from nextcord.ext.commands import Bot, Cog

import utils.util_functions as uf
from cogs.predictions import PredictionStatus
from cogs.roulette import get_streaks
from domain import Color, Standby

logger = logging.getLogger(__name__)


class Item(StrEnum):
    STARS = "Stars"
    THANKS = "Thanks"
    SKULLS = "Skulls"
    BURGERS = "Burgers"
    MOLDY_BURGERS = "Moldy burgers"
    ROULETTE = "Roulette (current)"
    ROULETTE_MAX = "Roulette (all-time)"
    ORBS = "Orbs"


async def get_item_counts(item: Item) -> dict[int, int]:
    """Get each user's item count.

    Args:
        item (Item): Item to lookup

    Returns:
        dict[int, int]: Keys are user ID's, values are counts.
    """
    standby = Standby()
    schema = standby.schema
    if item in (Item.STARS, Item.SKULLS, Item.THANKS):
        column = item.lower()
        table = {
            Item.STARS: "starboard",
            Item.SKULLS: "awards",
            Item.THANKS: "awards",
        }.get(item)
        records = await standby.pg_pool.fetch(f"""
            SELECT
                user_id,
                SUM({column}) as total
            FROM
                {schema}.{table}
            GROUP BY
                user_id
            ORDER BY
                total DESC
            """)
        return {record["user_id"]: record["total"] for record in records}

    if item == Item.BURGERS:
        records = await standby.pg_pool.fetch(f"""
            SELECT
                recipient_id as user_id,
                COUNT(*) as total
            FROM
                {schema}.burger
            GROUP BY
                user_id
            ORDER BY
                total DESC
            """)
        return {record["user_id"]: record["total"] for record in records}

    if item == Item.MOLDY_BURGERS:
        records = await standby.pg_pool.fetch(f"""
            SELECT
                giver_id as user_id,
                COUNT(*) as total
            FROM
                {schema}.burger
            WHERE
                reason = 'mold'
            GROUP BY
                user_id
            ORDER BY
                total DESC
            """)
        return {record["user_id"]: record["total"] for record in records}

    if item in (Item.ROULETTE, Item.ROULETTE_MAX):
        records = await standby.pg_pool.fetch(f"""
            SELECT DISTINCT
                user_id
            FROM
                {schema}.roulette
            WHERE
                win
            """)
        counts = {}

        for record in records:
            user_id = record["user_id"]
            current, maximum, _, _ = await get_streaks(user_id)
            counts[user_id] = current if item == Item.ROULETTE else maximum
        return counts

    if item == Item.ORBS:
        records = await standby.pg_pool.fetch(f"""
            SELECT
                user_id,
                COUNT(*) as total
            FROM
                {schema}.prediction
            WHERE
                status = '{PredictionStatus.CONFIRMED}'
            GROUP BY
                user_id
            ORDER BY
                total DESC
            """)
        return {record["user_id"]: record["total"] for record in records}

    return {}


def create_leaderboard_embed(
    item: Item,
    stats: dict[int, int],
    requesting_user_id: int,
) -> Embed:
    """Creates an Embed containing the top ranking users.

    Args:
        item (Item): Item to create leaderboard for
        stats (dict[int, int]): User data
        requesting_user_id (int): ID of user requesting the leaderboard
            (included regardless of ranking)
    """
    if not stats:
        return Embed(description=f"The {item} leaderboard is currently empty.")

    max_size = 12
    users = []
    scores = []

    for user_id, score in stats.items():
        if (
            len(users) < max_size  # Add until max size
            or score == scores[-1]  #  Include ties at the end
            or user_id == requesting_user_id  # Include requesting user
        ):
            users.append(uf.id_to_mention(user_id))
            scores.append(str(score))

    embed = Embed(
        color=Color.STARBOARD if item == Item.STARS else Color.VIE_PURPLE,
        title=item + " leaderboard",
    )
    embed.add_field(name="User", value="\n".join(users))
    embed.add_field(name=item, value="\n".join(scores))
    return embed


class Leaderboard(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command(description="Displays the leaderboards")
    async def leaderboard(
        self,
        interaction: Interaction,
        item: str = SlashOption(
            name="leaderboard",
            description="The leaderboard to display",
            choices=Item,
        ),
    ) -> None:
        """Send an embed with the top ranking users for an item."""
        stats = await get_item_counts(item)
        await interaction.send(
            embed=create_leaderboard_embed(item, stats, interaction.user.id),
        )


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Leaderboard())
