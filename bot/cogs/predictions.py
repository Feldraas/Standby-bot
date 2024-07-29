"""Prediction features."""

import logging
from enum import StrEnum

from asyncpg import Record
from nextcord import (
    ButtonStyle,
    Interaction,
    Member,
    SlashOption,
    slash_command,
)
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import Button, View, button

from domain import EMPTY_STRING, SQLResult, Standby
from utils import util_functions as uf

logger = logging.getLogger(__name__)

ORB_VOTE_REQUIREMENT = 5


class Predictions(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command(description="Make predictions")
    async def prediction(self, interaction: Interaction) -> None:
        """Command group for prediction functionality."""

    @prediction.subcommand(description="Make a prediction")
    async def make(
        self,
        interaction: Interaction,
        label: str = SlashOption(description="A label to identify your prediction"),
        text: str = SlashOption(description="The text of your prediction"),
    ) -> None:
        """Make a prediction.

        Prediction is stored with a label so it can be fetched later.

        Args:
            interaction (Interaction): Invoking interaction
            label (str): Prediction label
            text (str): Prediction text
        """
        result = await record_prediction(interaction.user, label, text)

        if result == SQLResult.NONE:
            await interaction.send(
                f"You have already made a prediction with the label `{label}` - "
                "please choose a unique label.",
                ephemeral=True,
            )
            return

        await interaction.send(f"Prediction saved with label `{label}`", ephemeral=True)
        await interaction.channel.send(
            f"{interaction.user.mention} just made a prediction!",
        )

    @prediction.subcommand(description="Reveal an active prediction")
    async def reveal(
        self,
        interaction: Interaction,
        label: str = SlashOption(description="Label of the prediction to reveal"),
    ) -> None:
        """Reveal an active prediction.

        Other users can vote whether the prediction was correct and
        should be rewarded with an orb.

        Args:
            interaction (Interaction): Invoking interaction
            label (str): Label of the prediction to reveal
        """
        prediction = await get_prediction(interaction.user, label)

        if prediction is None or prediction["status"] != PredictionStatus.ACTIVE:
            await interaction.send(
                f"No active prediction found for the label `{label}`. "
                "You can use `/prediction list` "
                "to see a list of your active predictions.",
                ephemeral=True,
            )
            return

        params = {
            "label": label,
            "owner_id": interaction.user.id,
            "votes_for": [],
            "votes_against": [],
        }
        view = PredictionView(params)
        timestamp = uf.dynamic_timestamp(prediction["predicted_at"], "date and time")

        await interaction.send(
            f"On {timestamp}, {interaction.user.mention} made the following "
            f"prediction:\n{EMPTY_STRING}\n"
            f"{prediction['text']}\n{EMPTY_STRING}\n"
            f"Does this prediction deserve an 🔮? Vote below!",
            view=view,
        )
        msg = await interaction.original_message()
        await uf.record_view(view, interaction.channel.id, msg.id)

    @prediction.subcommand(description="Check a prediction (privately)")
    async def check(
        self,
        interaction: Interaction,
        label: str = SlashOption(
            description="Label of the prediction you want to check",
        ),
    ) -> None:
        """Check prediction details.

        Args:
            interaction (Interaction): Invoking interaction
            label (str): Label of the prediction you want to check
        """
        prediction = await get_prediction(interaction.user, label)

        if prediction:
            message_text = format_prediction(prediction)
            await interaction.send(message_text, ephemeral=True)
        else:
            await interaction.send(
                f"No prediction found for the label `{label}`. You can use "
                "`/prediction list` to see a list of your active predictions.",
                ephemeral=True,
            )

    @prediction.subcommand(name="list", description="List your predictions (privately)")
    async def list_(self, interaction: Interaction) -> None:
        """Privately list all your predictions (and their labels).

        Args:
            interaction (Interaction): Invoking interaction
        """
        predictions = await get_user_predictions(interaction.user)
        if not predictions:
            await interaction.send("You have not made any predictions!", ephemeral=True)
            return

        for prediction in predictions:
            message_text = format_prediction(prediction)
            await interaction.send(message_text, ephemeral=True)

    @prediction.subcommand(description="Delete a prediction")
    async def delete(
        self,
        interaction: Interaction,
        label: str = SlashOption(description="Label of the prediction to delete"),
    ) -> None:
        """Delete a prediction.

        Args:
            interaction (Interaction): Invoking interaction
            label (str, optional): Label of the prediction to delete
        """
        prediction = await get_prediction(interaction.user, label)

        if prediction is None:
            await interaction.send(f"No prediction found for the label `{label}`!")
            return

        if prediction["status"] != PredictionStatus.ACTIVE:
            await interaction.send(
                "You cannot delete a prediction after it has been resolved",
            )
            return

        await delete_prediction(interaction.user.id, label)


class PredictionStatus(StrEnum):
    CONFIRMED = "Confirmed"
    DEBUNKED = "Debunked"
    ACTIVE = "Active"


async def record_prediction(user: Member, label: str, text: str) -> SQLResult:
    """Record the prediction in the database."""
    standby = Standby()
    result = await standby.pg_pool.execute(f"""
        INSERT INTO
            dev.prediction (user_id, predicted_at, label, text, status)
        VALUES
            ({user.id}, '{uf.now()}', '{label}', '{text}', '{PredictionStatus.ACTIVE}')
        ON CONFLICT ON CONSTRAINT prediction_pk DO NOTHING
        """)
    if result == "INSERT 0 0":
        return SQLResult.NONE
    return SQLResult.INSERT


async def get_prediction(user: Member, label: str) -> Record | None:
    """Get the prediction with specified label."""
    standby = Standby()
    return await standby.pg_pool.fetchrow(f"""
        SELECT
            *
        FROM
            {standby.schema}.prediction
        WHERE
            user_id = {user.id}
            AND label = '{label}'
        """)


async def get_user_predictions(user: Member) -> list[Record]:
    """Get all predictions for a user."""
    standby = Standby()
    return await standby.pg_pool.fetch(f"""
        SELECT
            *
        FROM
            {standby.schema}.prediction
        WHERE
            user_id = {user.id}
        """)


def format_prediction(prediction: Record) -> str:
    """Format a prediction into a message to send to the user."""
    timestamp = uf.dynamic_timestamp(prediction["predicted_at"], "date and time")
    return (
        f"Label: {prediction['label']}\n"
        f"Made on: {timestamp}\n"
        f"Status: {prediction['status']}\n"
        f"Text: {prediction['text']}"
    )


async def delete_prediction(user_id: int, label: str) -> None:
    """Delete prediction with the specified label."""
    standby = Standby()
    await standby.pg_pool.execute(f"""
        DELETE FROM {standby.schema}.prediction
        WHERE
            user_id = {user_id}
            AND label = '{label}'
        """)


async def set_prediction_status(
    user_id: int,
    label: str,
    status: PredictionStatus,
) -> None:
    """Set a prediction's status to confirmed."""
    standby = Standby()
    await standby.pg_pool.execute(f"""
        UPDATE {standby.schema}.prediction
        SET
            status = '{status}'
        WHERE
            user_id = {user_id}
            AND label = '{label}'
        """)


class PredictionView(View):
    """Buttons for voting on whether a predFiction was correct."""

    def __init__(self, params: dict) -> None:
        super().__init__(timeout=None)
        self.standby = Standby()
        self.label = params["label"]
        self.owner_id = params["owner_id"]
        self.votes_for = params["votes_for"]
        self.votes_against = params["votes_against"]

    @button(emoji="🔮", style=ButtonStyle.blurple)
    async def award_orb(self, button: Button, interaction: Interaction) -> None:  # noqa: ARG002
        """Button to vote yes."""
        if interaction.user.id == self.owner_id:
            await interaction.send(
                "You can not award orbs to your own prediction!",
                ephemeral=True,
            )
            return

        if interaction.user.id in self.votes_for:
            await interaction.send(
                "You have already voted for this prediction!",
                ephemeral=True,
            )
            return

        if interaction.user.id in self.votes_against:
            self.votes_against.remove(interaction.user.id)

        self.votes_for.append(interaction.user.id)
        await interaction.send("Vote recorded!", ephemeral=True)

        if len(self.votes_for) >= ORB_VOTE_REQUIREMENT:
            await interaction.send(
                f"{uf.id_to_mention(self.owner_id)} has been awarded an orb!",
            )
            await set_prediction_status(
                self.owner_id,
                self.label,
                PredictionStatus.CONFIRMED,
            )
            old_lines = interaction.message.content.split("\n")
            old_lines[-1] = (
                f"{uf.id_to_mention(self.owner_id)} was awarded an 🔮 "
                "for this prediction!"
            )
            new_text = "\n".join(old_lines)
            await interaction.message.edit(content=new_text, view=None)
        else:
            await uf.record_view(self, interaction.channel.id, interaction.message.id)

    @button(emoji="❌", style=ButtonStyle.blurple)
    async def deny_orb(self, button: Button, interaction: Interaction) -> None:  # noqa: ARG002
        """Button to vote no."""
        if interaction.user.id == self.owner_id:
            await set_prediction_status(
                self.owner_id,
                self.label,
                PredictionStatus.DEBUNKED,
            )
            old_lines = interaction.message.content.split("\n")
            old_lines[-1] = (
                f"{interaction.user.mention} has marked their prediction as incorrect"
            )
            new_text = "\n".join(old_lines)
            await interaction.message.edit(content=new_text, view=None)
            return

        if interaction.user.id in self.votes_against:
            await interaction.send(
                "You have already voted against this prediction!",
                ephemeral=True,
            )
            return

        if interaction.user.id in self.votes_for:
            self.votes_for.remove(interaction.user.id)

        self.votes_against.append(interaction.user.id)
        await interaction.send("Vote recorded!", ephemeral=True)

        if len(self.votes_against) >= ORB_VOTE_REQUIREMENT:
            await interaction.send(
                f"{uf.id_to_mention(self.owner_id)}'s prediction has been deemed "
                "unworthy of an 🔮!",
            )
            await delete_prediction(self.owner_id, self.label)
            old_lines = interaction.message.content.split("\n")
            old_lines[-1] = (
                f"{uf.id_to_mention(self.owner_id)} was not awarded an 🔮 "
                "for this prediction!"
            )
            new_text = "\n".join(old_lines)
            await interaction.message.edit(content=new_text, view=None)
        else:
            await uf.record_view(self, interaction.channel.id, interaction.message.id)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Predictions())
