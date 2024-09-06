"""Features for rating films, games etc."""

import logging
from enum import StrEnum

from asyncpg import Record
from nextcord import Interaction, Member, SlashOption, slash_command
from nextcord.ext.commands import Bot, Cog

from domain import Standby
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class Category(StrEnum):
    MOVIE = "movie"
    SERIES = "series"
    BOOK = "book"
    GAME = "game"
    OTHER = "other"


class Rating(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command(description="Rate something")
    async def rating(self, interaction: Interaction) -> None:
        """Command group for rating functionality."""

    @rating.subcommand(description="Rate something")
    async def add(
        self,
        interaction: Interaction,
        category: str = SlashOption(choices={cat.title(): cat for cat in Category}),
        title: str = SlashOption(description="Title of the work"),
        score: int = SlashOption(min_value=1, max_value=10),
        review: str | None = SlashOption(
            description="Review or comment (optional)",
            required=False,
        ),
    ) -> None:
        """Rate a movie or other work.

        Rating (and review, if provided) are stored in the database.

        Args:
            interaction (Interaction): Invoking interaction
            category (str): Type of media
            title (str): Title.
            score (int): Score (1-10)
            review (str | None): Review or comment
        """
        title = uf.titlecase(title)
        await insert_rating(interaction.user, category, title, score, review)
        category_str = "something" if category == Category.OTHER else f"a {category}"
        lines = [
            f"{interaction.user.mention} has rated {category_str}:",
            f"Title: {title}",
            f"Score: {score}/10",
        ]
        if review:
            lines.append(f"Review: {review}")
        await interaction.send("\n".join(lines))

    @rating.subcommand(description="Check a title's score and reviews")
    async def check(
        self,
        interaction: Interaction,
        category: str = SlashOption(choices={cat.title(): cat for cat in Category}),
        title: str = SlashOption(description="Title of the work"),
        details: int = SlashOption(  # has to be int, bool doesn't work for some reason
            description="Level of detail to include",
            choices={"Average score only": 0, "All ratings": 1},
        ),
    ) -> None:
        """Check a title's rating and reviews."""
        title = uf.titlecase(title)
        records = await get_ratings(category, title)

        if not records:
            await interaction.send(f"{title} has not been rated yet.")
            return

        count = len(records)
        score = sum(rec["score"] for rec in records) / count
        await interaction.send(
            f"{title} currently has an average score of {score} "
            f"based off {count} rating(s).",
        )

        if not details:
            return

        await interaction.channel.send(f"Reviews currently on file for {title}:")
        for rec in records:
            msg = f"{uf.id_to_mention(rec['user_id'])} rated it {rec['score']}/10"
            if rec["review"]:
                msg += f" with the review:\n{rec['review']}"
            await interaction.channel.send(msg)


async def insert_rating(
    user: Member,
    category: Category,
    title: str,
    score: int,
    review: str | None,
) -> None:
    """Insert or update a rating."""
    standby = Standby()
    await standby.pg_pool.execute(
        f"""
        INSERT INTO
            {standby.schema}.rating (user_id, category, title, score, review)
        VALUES
            ($1, $2, $3, $4, $5)
        ON CONFLICT ON CONSTRAINT rating_pkey
        DO UPDATE SET
            score = excluded.score,
            review = excluded.review
        """,
        user.id,
        category,
        title,
        score,
        review,
    )


async def get_ratings(category: Category, title: str) -> list[Record]:
    """Get all ratings for a title."""
    standby = Standby()
    return await standby.pg_pool.fetch(f"""
        SELECT
            user_id, score, review
        FROM
            {standby.schema}.rating
        WHERE
            category = '{category}'
            AND title = '{title}'
        """)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Rating())
