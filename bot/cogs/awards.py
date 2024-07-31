"""Features for handing out simple awards."""

import logging
from enum import StrEnum

from nextcord import Interaction, Member, SlashOption, slash_command
from nextcord.ext.commands import Bot, Cog

from domain import ID, Standby, ValidTextChannel
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class Award(StrEnum):
    THANKS = "Thanks"
    SKULL = "Skull"


class Awards(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command()
    async def give(
        self,
        interaction: Interaction,
        recipient: Member = SlashOption(description="The person to give the award to"),
        award: str = SlashOption(
            description="The type of award you want to give",
            choices=Award,
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

    column_mapping = {
        Award.THANKS: "thanks",
        Award.SKULL: "skulls",
    }
    column = column_mapping[award]

    standby = Standby()
    await standby.pg_pool.execute(f"""
        INSERT INTO
            {standby.schema}.award (user_id, {column})
        VALUES
            ({recipient.id}, 1)
        ON CONFLICT ON CONSTRAINT award_pkey DO UPDATE
        SET
            {column} = award.{column} + 1
        WHERE
            award.user_id = {recipient.id}
        """)

    award_text = f"a {award.lower()}" if award != Award.THANKS else "their thanks"
    await channel.send(
        f"{giver.mention} has given {recipient.mention} {award_text}",
    )


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Awards())
