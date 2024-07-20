"""Play hangman in a channel (legacy)."""

import asyncio
import re
from typing import Literal

from nextcord import Embed, Interaction, Member, SlashOption, slash_command
from nextcord.ext.commands import Bot, Cog

from domain import URL, Color, Standby, ValidTextChannel
from utils import util_functions as uf

IMAGE_LINKS = [URL.GITHUB_STATIC + f"/images/Hangman-{num}.png" for num in range(7)]
MAX_PHRASE_LENGTH = 85
MAX_WRONG_GUESSES = 6


class HangmanGame:
    def __init__(self) -> None:
        self.status = "Inactive"
        self.lock = asyncio.Lock()
        self.word = None
        self.progress = None
        self.wrong_guesses = None
        self.host = None
        self.channel = None
        self.embed = None

    def create_embed(self) -> Embed:
        """Create an embed for the game."""
        embed = Embed(color=Color.PALE_GREEN)
        title = re.sub(" ", "   ", self.progress)
        title = re.sub("_", r"\_ ", title)
        title = re.sub(r"(\w)", r"\1 ", title)
        embed.title = (
            title if len(self.wrong_guesses) < MAX_WRONG_GUESSES else self.word
        )
        if len(self.wrong_guesses) >= MAX_WRONG_GUESSES:
            desc = "Game over! Use `/hangman` to start another round."
        elif self.word == self.progress:
            desc = "Game won! Use `/hangman` to start another round."
        else:
            desc = (
                "Welcome to Void Hangman! "
                "Use `/hangman` to guess a letter or the whole word/phrase."
            )
        embed.description = desc
        embed.set_image(url=IMAGE_LINKS[len(self.wrong_guesses)])
        embed.add_field(
            name="Wrong guesses",
            value="None"
            if len(self.wrong_guesses) == 0
            else ", ".join(self.wrong_guesses),
            inline=False,
        )
        return embed

    def setup(self, word: str, host: Member, channel: ValidTextChannel) -> None:
        """Setup the game."""
        self.status = "Active"
        self.word = word.upper()
        self.progress = re.sub(r"\w", "_", self.word)
        self.wrong_guesses = []
        self.host = host
        self.channel = channel
        self.embed = self.create_embed()

    def check_letter(self, letter: str) -> bool:
        """Check if the word contains a letter."""
        letter = letter.upper()
        if letter in self.word:
            for match in re.finditer(letter, self.word):
                self.progress = (
                    self.progress[: match.start()]
                    + letter
                    + self.progress[match.start() + 1 :]
                )
            self.embed = self.create_embed()
            return True
        self.wrong_guesses.append(letter)
        self.embed = self.create_embed()
        return False

    def check_word(self, word: str) -> bool:
        """Check if a full word guess is correct."""
        word = word.upper()
        if word == self.word:
            self.progress = word
            self.embed = self.create_embed()
            return True
        self.wrong_guesses.append(word)
        self.embed = self.create_embed()
        return False

    def state(self) -> Literal["Game Over", "Game Won", "Still guessing"]:
        """Get current game state."""
        if len(self.wrong_guesses) == MAX_WRONG_GUESSES:
            return "Game Over"
        if self.progress == self.word:
            return "Game Won"
        return "Still guessing"


game = HangmanGame()


class Hangman(Cog, name="Void Hangman"):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command(description="Commands for running games of hangman")
    async def hangman(self, interaction: Interaction) -> None:
        """Command group for Hangman actions."""

    @hangman.subcommand(description="Start a game of Void Hangman")
    async def start(
        self,
        interaction: Interaction,
        phrase: str = SlashOption(
            description="The word or phrase to be guessed (max 85 characters)",
        ),
    ) -> None:
        """Start a game of Hangman."""
        await game.lock.acquire()

        if game.status != "Inactive":
            await interaction.send("A game is already running.", ephemeral=True)

        else:
            if len(phrase) > MAX_PHRASE_LENGTH:
                await interaction.send(
                    "Phrase is too long, please try again",
                    ephemeral=True,
                )
                return

            await interaction.send(
                "Phrase accepted - game is starting!",
                ephemeral=True,
            )
            await interaction.channel.send("Void Hangman has begun!")
            game.setup(phrase, interaction.user, interaction.channel)
            await interaction.channel.send(embed=game.embed)
            game.lock.release()

    @hangman.subcommand(description="Attempt a guess")
    async def guess(  # noqa: C901, PLR0912
        self,
        interaction: Interaction,
        guess: str = SlashOption(
            description="Your guess - either a letter or the whole word/phrase",
        ),
    ) -> None:
        """Guess a letter."""
        global game  # noqa: PLW0603

        if game.status == "Inactive":
            await interaction.send("No active game found.", ephemeral=True)
        elif game.channel != interaction.channel:
            await interaction.send(
                "You can only make guesses in the current game's channel, "
                f"please head over to {game.channel.mention}.",
                ephemeral=True,
            )
        elif game.host == interaction.user:
            await interaction.send("Hey, no cheating!", ephemeral=True)
        else:
            guess = guess.upper()

            if guess in game.progress or guess in game.wrong_guesses:
                await interaction.send(f"{guess} has already been guessed!")
                return

            if len(guess) == 1:
                if game.check_letter(guess):
                    await interaction.send(f"Ding ding ding - {guess} is a hit!")
                else:
                    await interaction.send(f"Sorry, no {guess}.")

            elif len(guess) == len(game.word):
                if not game.check_word(guess):
                    await interaction.send(f"{guess} isn't correct, sorry.")
            else:
                await interaction.send(
                    "You can only guess single letters or the entire word/phrase.",
                    ephemeral=True,
                )
                return

            if game.state() == "Game Over":
                await interaction.send(
                    "Game Over - better luck next time!",
                    embed=game.embed,
                )
                game = HangmanGame()
            elif game.state() == "Game Won":
                await interaction.send(
                    "Winner winner chicken dinner!",
                    embed=game.embed,
                )
                game = HangmanGame()
            else:
                await interaction.channel.send(embed=game.embed)

    @hangman.subcommand(description="Abort the current game of Void Hangman")
    async def abort(self, interaction: Interaction) -> None:
        """Abort the current game."""
        global game  # noqa: PLW0603

        if game.status != "Active":
            await interaction.send("No active game found.", ephemeral=True)
        elif (
            interaction.user != game.host
            or uf.get_role("Moderator") not in interaction.user.roles
        ):
            await interaction.send(
                "Only the person who started the game can stop it.",
                ephemeral=True,
            )
        else:
            await interaction.send("Game aborted. Use `/hangman` to start a new one.")
            game = HangmanGame()


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Hangman())
