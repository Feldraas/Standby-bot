"""Award features."""

import logging
from enum import StrEnum

from nextcord import Embed, Interaction, Member, SlashOption, slash_command
from nextcord.ext.commands import Bot, Cog

from domain import ID, Color, Standby, ValidTextChannel
from utils import util_functions as uf

logger = logging.getLogger(__name__)
standby = Standby()


class Award(StrEnum):
    """Enum for award types."""

    THANKS = "thanks"
    SKULL = "skulls"
    BURGER = "burgers"
    MOLDY_BURGER = "moldy_burgers"
    ORB = "orbs"
    STAR = "stars"
    BRAIN = "brains"
    REE = "reposts"

    @classmethod
    def giveable(cls) -> list["Award"]:
        """Awards that users may give to each other."""
        return [cls.THANKS, cls.SKULL]


class Awards(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command()
    async def award(self, interaction: Interaction) -> None:
        """Command group for giving and receiving awards."""

    @award.subcommand(description="Give someone an award")
    async def give(
        self,
        interaction: Interaction,
        recipient: Member = SlashOption(description="The person to give the award to"),
        award: str = SlashOption(
            description="The type of award you want to give",
            choices={
                award.rstrip("s").replace("thank", "thanks"): award
                for award in Award.giveable()
            },
        ),
    ) -> None:
        """Give an award to a user.

        Awards are aesthetic and only stored as an incrementing counter.
        """
        await give_award(
            giver=interaction.user,
            recipient=recipient,
            award=Award(award),
            channel=interaction,
        )

    @award.subcommand(description="Check your own awards")
    async def check(
        self,
        interaction: Interaction,
        award: str = SlashOption(
            description="The type of award to check",
            choices={award.capitalize().replace("_", " "): award for award in Award},
        ),
    ) -> None:
        """Check award count."""
        count = await get_award_count(interaction.user, Award(award))
        noun = award.lower().replace("_", " ")
        if count == 1:
            noun = noun.rstrip("s")
        await interaction.send(f"You currently have {count} {noun}.", ephemeral=True)

    @award.subcommand(description="Check leaderboard for an award")
    async def leaderboard(
        self,
        interaction: Interaction,
        award: str = SlashOption(
            description="The type of award to check",
            choices=Award,
        ),
    ) -> None:
        """Reply with a leaderboard for the requested award."""
        stats = await get_all_award_counts(award)
        embed = create_leaderboard_embed(award, stats, interaction.user.id)
        await interaction.send(embed=embed)


def create_leaderboard_embed(
    award: Award,
    stats: dict[int, int],
    requesting_user_id: int,
) -> Embed:
    """Creates an Embed containing the top ranking users.

    Args:
        award (Award): Award type to create leaderboard for
        stats (dict[int, int]): User data
        requesting_user_id (int): ID of user requesting the leaderboard
            (included regardless of ranking)
    """
    title = award.capitalize().replace("_", " ").rstrip("s").replace("Thank", "Thanks")
    if not stats:
        return Embed(description=f"The {title} leaderboard is currently empty.")

    max_size = 12
    users = []
    scores = []

    for user_id, score in stats.items():
        if score == 0:
            continue
        if (
            len(users) < max_size  # Add until max size
            or score == scores[-1]  #  Include ties at the end
            or user_id == requesting_user_id  # Include requesting user
        ):
            users.append(uf.id_to_mention(user_id))
            scores.append(str(score))

    color_map = {
        Award.STAR: Color.STARBOARD,
        Award.SKULL: Color.GREY,
        Award.MOLDY_BURGER: Color.PUKE_GREEN,
    }
    embed = Embed(
        color=color_map.get(award, Color.VIE_PURPLE),
        title=title + " leaderboard",
    )
    embed.add_field(name="User", value="\n".join(users))
    embed.add_field(name=award.capitalize().replace("_", " "), value="\n".join(scores))
    return embed


async def get_all_award_counts(award: Award) -> dict[int, int]:
    """Get dict of user IDs and award counts."""
    records = await standby.pg_pool.fetch(f"""
        SELECT
            user_id, {award}
        FROM
            {standby.schema}.award
        ORDER BY
            {award} DESC
        """)
    return {record["user_id"]: record[award] or 0 for record in records}


async def get_award_count(user: Member, award: Award) -> int:
    """Check award count for a user and award type."""
    counts = await get_all_award_counts(award)
    return counts.get(user.id, 0)


async def give_award(
    giver: Member,
    recipient: Member,
    award: Award,
    channel: ValidTextChannel | Interaction,
) -> None:
    """Increment the corresponding award counter in the database.

    Flexible implementation so it can be called without an interaction.
    """
    if award == Award.SKULL and giver.id != ID.JORM:
        await channel.send(
            file=uf.simpsons_error_image(
                dad=Standby().guild.me,
                son=giver,
                text="You're not Jorm!",
                filename="jormonly.png",
            ),
        )
        return

    if giver == recipient:
        if isinstance(channel, Interaction):
            await channel.send(
                f"You can't give awards to yourself, {giver.mention}",
                ephemeral=True,
            )
        else:
            await channel.send(f"You can't give awards to yourself, {giver.mention}")
        return

    await increment_award_count(recipient, award)

    award_text = f"a {award.lower()}" if award != Award.THANKS else "their thanks"
    await channel.send(
        f"{giver.mention} has given {recipient.mention} {award_text}",
    )


async def increment_award_count(user: Member, award: Award) -> None:
    """Increase award count for a user."""
    await standby.pg_pool.execute(f"""
        INSERT INTO
            {standby.schema}.simple_award (user_id, {award})
        VALUES
            ({user.id}, 1)
        ON CONFLICT ON CONSTRAINT award_pkey DO UPDATE
        SET
            {award} = simple_award.{award} + 1
        WHERE
            simple_award.user_id = {user.id}
        """)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Awards())
