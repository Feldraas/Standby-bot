"""Quiz docstring."""

import logging

from nextcord import ButtonStyle, Interaction, slash_command
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import Button, View

import utils.util_functions as uf
from cogs.awards import Award, increment_award_count
from domain import Standby

logger = logging.getLogger(__name__)


class TriviaView(View):
    def __init__(self, params: dict) -> None:
        super().__init__()
        self.params = params or {}
        self.question = params["question"]
        self.options = params["options"]
        self.answer = params["correct"]

        for i in range(4):
            self.add_item(self.AnswerButton(label=self.options[i]))

    class AnswerButton(Button):
        """Button with one answer as label."""

        def __init__(self, label: str) -> None:
            """Set label."""
            super().__init__(style=ButtonStyle.blurple, label=label)
            self.standby = Standby()

        async def callback(self, interaction: Interaction) -> None:
            """Check answer."""
            if interaction.user.id in self.view.params["attempted"]:
                await interaction.send(
                    "You may only attempt to answer once",
                    ephemeral=True,
                )
                return

            if self.label == self.view.answer:
                await interaction.send(
                    f"`{self.label}` is not the correct answer - "
                    "better luck next time!",
                    ephemeral=True,
                )
                self.view.params["attempted"].append(interaction.user.id)
                await uf.record_view(
                    self.view,
                    interaction.channel.id,
                    interaction.message.id,
                )
                return

            for child in self.view.children:
                child.disabled = True
            await interaction.edit(view=self.view)
            await interaction.send(
                f"{interaction.user.mention} has answered the question correctly"
                " and has been awarded a brain 🧠",
            )
            await increment_award_count(interaction.user, Award.BRAIN)
            await uf.delete_view_record(interaction.message.id)


class Quiz(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command(description="asdf")
    async def quiz(self, interaction: Interaction) -> None:
        """Post a trivia question."""
        params = uf.get_trivia_question()
        params["attempted"] = []

        view = TriviaView(params)
        await interaction.send(content=params["question"], view=view)
        msg = await interaction.original_message()
        await uf.record_view(view, interaction.channel.id, msg.id)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Quiz())
