"""Fun commands (memes etc)."""

import io
import logging
import random
import re
from itertools import permutations
from pathlib import Path
from urllib.parse import quote

import nextcord
import requests
from nextcord import (
    ButtonStyle,
    Embed,
    Interaction,
    Member,
    SlashOption,
    slash_command,
    user_command,
)
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import Button, Select, View, button, select
from PIL import Image, ImageDraw, ImageFont
from transliterate import translit
from transliterate.base import TranslitLanguagePack, registry

from domain import (
    ID,
    URL,
    Standby,
)
from utils import util_functions as uf

logger = logging.getLogger(__name__)

TOUCAN_PRAISE = """
░░░░░░░░▄▄▄▀▀▀▄▄███▄░░░░░░░░░░░░░░
░░░░░▄▀▀░░░░░░░▐░▀██▌░░░░░░░░░░░░░
░░░▄▀░░░░▄▄███░▌▀▀░▀█░░░░░░░░░░░░░
░░▄█░░▄▀▀▒▒▒▒▒▄▐░░░░█▌░░░░░░░░░░░░
░▐█▀▄▀▄▄▄▄▀▀▀▀▌░░░░░▐█▄░░░░░░░░░░░
░▌▄▄▀▀░░░░░░░░▌░░░░▄███████▄░░░░░░
░░░░░░░░░░░░░▐░░░░▐███████████▄░░░
░░░░░le░░░░░░░▐░░░░▐█████████████▄
░░░░toucan░░░░░░▀▄░░░▐█████████████▄
░░░░░░has░░░░░░░░▀▄▄███████████████
░░░░░arrived░░░░░░░░░░░░█▀██████░░
"""

YEEE = """
░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░▄███▄▄▄░░░░░░░
░░░░░░░░░▄▄▄██▀▀▀▀███▄░░░░░
░░░░░░░▄▀▀░░░░░░░░░░░▀█░░░░
░░░░▄▄▀░░░░░░░░░░░░░░░▀█░░░
░░░█░░░░░▀▄░░▄▀░░░░░░░░█░░░
░░░▐██▄░░▀▄▀▀▄▀░░▄██▀░▐▌░░░
░░░█▀█░▀░░░▀▀░░░▀░█▀░░▐▌░░░
░░░█░░▀▐░░░░░░░░▌▀░░░░░█░░░
░░░█░░░░░░░░░░░░░░░░░░░█░░░
░░░░█░░▀▄░░░░▄▀░░░░░░░░█░░░
░░░░█░░░░░░░░░░░▄▄░░░░█░░░░
░░░░░█▀██▀▀▀▀██▀░░░░░░█░░░░
░░░░░█░░▀████▀░░░░░░░█░░░░░
░░░░░░█░░░░░░░░░░░░▄█░░░░░░
░░░░░░░██░░░░░█▄▄▀▀░█░░░░░░
░░░░░░░░▀▀█▀▀▀▀░░░░░░█░░░░░
░░░░░░░░░█░░░░░░░░░░░░█░░░░
"""

ALL_MEMES = []
for file in Path("static/images/memes").iterdir():
    ending_brackets = r" \[.+\]$"
    ALL_MEMES.append(re.sub(ending_brackets, "", file.stem))
ALL_MEMES = sorted(set(ALL_MEMES), key=str.casefold)


def add(lhs: int, rhs: int, pstr: str) -> tuple[int, str]:
    """Support function for the fabricate_number command."""
    return lhs + rhs, pstr + "+" + str(rhs)


def sub(lhs: int, rhs: int, pstr: str) -> tuple[int, str]:
    """Support function for the fabricate_number command."""
    return lhs - rhs, pstr + "-" + str(rhs)


def mult(lhs: int, rhs: int, pstr: str) -> tuple[int, str]:
    """Support function for the fabricate_number command."""
    if rhs == 0:
        return 0, ""
    return lhs * rhs, "(" + pstr + ")*" + str(rhs)


def div(lhs: int, rhs: int, pstr: str) -> tuple[float, str]:
    """Support function for the fabricate_number command."""
    return lhs / rhs, "(" + pstr + ")/" + str(rhs)


operations = [add, sub, mult, div]


def create_concat_combinations(digits: list[int]) -> list[list[int]]:
    """Support function for the fabricate_number command."""
    combs = [digits.copy()]
    for tupling_sz in range(2, len(digits) + 1):
        for num_tupling in range(1, int(len(digits) / tupling_sz) + 1):
            perms = permutations(digits)
            for perm in perms:
                out = list(perm).copy()
                coupled = []
                for i in range(num_tupling):
                    to_merge = perm[i * tupling_sz : i * tupling_sz + tupling_sz]
                    merged = int("".join(map(str, to_merge)))
                    coupled.append(merged)
                    out = out[i * tupling_sz + tupling_sz :]
                out.extend(coupled)
                combs.append(out)

    for i in range(len(combs)):
        combs[i] = sorted(combs[i])

    filtered_combs = []
    for comb in combs:
        if comb not in filtered_combs:
            filtered_combs.append(comb)
    return filtered_combs


async def dfs(
    target: int,
    current_target: int,
    current_digits: list[int],
    current_str: str,
) -> str:
    """Support function for the fabricate_number command."""
    if current_target == target:
        return current_str

    if not current_digits:
        return ""

    for dig in current_digits:
        new_digits = current_digits.copy()
        new_digits.remove(dig)
        for op in operations:
            if op == div and dig == 0:
                continue
            new_target, new_str = op(current_target, dig, current_str)
            if op == div and not new_target.is_integer():
                continue
            res = await dfs(target, int(new_target), new_digits, new_str)
            if res:
                return res

    return ""


class Fun(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command(description="YEE")
    async def yee(self, interaction: Interaction) -> None:
        """Send ASCII art of the YEEE dinosaur."""
        await interaction.send(YEEE)

    @slash_command(description="Gives a user a hug")
    async def hug(
        self,
        interaction: Interaction,
        user: Member = SlashOption(description="The user you want to send a hug to"),
    ) -> None:
        """Hug another user.

        Args:
            interaction (Interaction): Invoking interaction
            user (Member): Hug target
        """
        if user == interaction.user:
            await interaction.send(URL.GITHUB_STATIC + "/images/selfhug.png")
        else:
            await interaction.send(
                f"{user.mention}, {interaction.user.mention} sent you a hug!",
            )
            hug = uf.get_emoji("BlobReachAndHug")
            if hug:
                await interaction.channel.send(hug)

    @user_command(name="Hug")
    async def hug_context(self, interaction: Interaction, user: Member) -> None:
        """Invoke the hug command through the user context menu."""
        await uf.invoke_slash_command("hug", self, interaction, user)

    @slash_command(description="Pay your respects")
    async def f(
        self,
        interaction: Interaction,
        target: str = SlashOption(
            description="What do you want to pay your respects to?",
            required=False,
        ),
    ) -> None:
        """Pay your respects to something.

        Args:
            interaction (Interaction): Invoking interaction
            target (str): Target
        """
        embed = Embed()

        embed.description = f"{interaction.user.mention} has paid their respects."

        if target:
            text = target.split(" ")
            for index, word in enumerate(text):
                if not re.search(r"^<..?\d+>$", word):
                    text[index] = " ".join(word)

            bolded_text = "**" + "  ".join(text) + "**"

            embed.description = embed.description[:-1] + f" to {bolded_text}."

        await interaction.response.send_message(embed=embed)
        rip = await interaction.original_message()
        await rip.add_reaction("🇫")

    @slash_command(description="Posts a meme.")
    async def meme(
        self,
        interaction: Interaction,
        meme: str = SlashOption(
            description="Start typing to see suggestions or enter `list` to "
            "see a list of all available memes",
        ),
    ) -> None:
        """Send a meme.

        Args:
            interaction (Interaction): Invoking interaction
            meme (str): Meme to send.
        """
        if meme == "list":
            help_text = (
                f"```Currently available memes:\n{"\n".join(["list", *ALL_MEMES])}```"
            )
            await interaction.response.send_message(help_text, ephemeral=True)
            return

        if "horny" in meme.lower() and interaction.user.id == ID.JORM:
            link = URL.GITHUB_STATIC + "/images/memes/Horny [DD].png"
            await interaction.response.send_message(quote(link, safe=":/"))
        elif meme in ALL_MEMES:
            meme_dir = Path(URL.LOCAL_STATIC) / "images/memes"
            matches = list(meme_dir.glob(f"{meme}*"))
            file = random.choice(matches)
            link = URL.GITHUB_STATIC + "/images/memes/" + file.name
            await interaction.response.send_message(quote(link, safe=":/"))
        else:
            await interaction.response.send_message(
                f"No match found for '{meme}' - use `/meme list` "
                "to see a list of all available memes.",
                ephemeral=True,
            )

    @meme.on_autocomplete("meme")
    async def suggest_meme(
        self,
        interaction: Interaction,
        user_input: str | None,
    ) -> None:
        """Autocomplete for user input in the meme command.

        Suggests memes with matching names.

        Args:
            interaction (Interaction): Invoking interaction
            user_input (str | None): Currently entered text
        """
        if user_input:
            matches = sorted(
                (meme for meme in ALL_MEMES if user_input.lower() in meme.lower()),
                key=lambda meme: meme.lower().startswith(user_input.lower()),
                reverse=True,
            )
            await interaction.response.send_autocomplete(matches[:25])
        else:
            await interaction.response.send_autocomplete([])

    @slash_command(description="Convert text into cyrillic")
    async def cyrillify(
        self,
        interaction: Interaction,
        text: str = SlashOption(description="Text to cyrillify"),
    ) -> None:
        """Convert a text to cyryllic script (badly).

        Args:
            interaction (Interaction): Invoking interaction
            text (str): Text to convert.
        """

        class ExampleLanguagePack(TranslitLanguagePack):
            language_code = "custom"
            language_name = "Custom"
            latin = "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwYyZz"
            cyrillic = "АаБбКкДдЕеФфГгХхИиЙйКкЛлМмНнОоПпКкРрСсТтУуВвУуЙйЗз"
            mapping = latin, cyrillic
            pre_processor_mapping = {
                "scht": "щ",
                "sht": "щ",
                "sh": "ш",
                "tsch": "ч",
                "tch": "ч",
                "sch": "ш",
                "zh": "ж",
                "tz": "ц",
                "ch": "ч",
                "yu": "ю",
                "ya": "я",
                "x": "кс",
                "ck": "к",
                "ph": "ф",
            }
            chars = list(pre_processor_mapping.keys())
            for lat in chars:
                cyr = pre_processor_mapping[lat]
                pre_processor_mapping[lat.capitalize()] = cyr.capitalize()

        registry.register(ExampleLanguagePack)

        await interaction.send(translit(text, "custom"))

    class VanityView(View):
        """Dropdown menu for selecting Vanity roles."""

        def __init__(self, creator: Member) -> None:
            super().__init__()
            self.value = None
            self.creator = creator

        @select(placeholder="Pick a vanity role")
        async def select_role(self, select: Select, interaction: Interaction) -> None:
            """Choose a role.

            Args:
                select (Select): Dropdown menu object
                interaction (Interaction): Invoking interaction
            """
            if self.creator == interaction.user and select.values:
                self.value = select.values[0]

        @button(label="Pick", style=ButtonStyle.blurple)
        async def press(self, button: Button, interaction: Interaction) -> None:  # noqa: ARG002
            """Disable the menu and send selection to the interaction.

            Args:
                button (_type_): _description_
                interaction (_type_): _description_
            """
            if self.creator == interaction.user and self.value:
                self.stop()

    @slash_command(description="Pick a vanity role")
    async def vanity(self, interaction: Interaction) -> None:
        """Choose a vanity role.

        Args:
            interaction (Interaction): Invoking interaction
        """
        view = self.VanityView(interaction.user)
        vanity_roles = uf.get_roles_by_type("Vanity")
        for role in vanity_roles:
            view.children[0].add_option(label=role.name)
        view.children[0].add_option(label="Remove my vanity role", value="remove")
        await interaction.send(view=view)
        await view.wait()
        if view.value:
            logger.info(f"Removing vanity roles for {interaction.user}")
            await interaction.user.remove_roles(*vanity_roles)
            text = "Your vanity role has been removed."
            if view.value != "remove":
                logger.info(f"Adding vanity role {role.name} to {interaction.user}")
                role = uf.get_role(view.value)
                await interaction.user.add_roles(role)
                text = f"You are now (a) {role.name}."
            msg = await interaction.original_message()
            await msg.edit(text, view=None, delete_after=10)

    @slash_command(description="Genererate a captioned meme")
    async def caption(
        self,
        interaction: Interaction,
        caption: str = SlashOption(description="The caption to use"),
        template: str = SlashOption(
            description="The base template to caption",
            choices=["Farquaad", "Megamind"],
        ),
    ) -> None:
        """Send a captioned meme template.

        Args:
            interaction (Interaction): Invoking interaction
            caption (str): Caption text
            template (str): Meme template to use
        """
        await interaction.response.defer()

        if template == "Farquaad":
            query, font_size, align = "Farquaad pointing", 100, "bottom"
        else:  # template == "Megamind":
            query, font_size, align = "Megamind no bitches", 125, "top"

        logger.info(f"Captioning {template=} for {interaction.user}")

        logger.info("Fetching base image")
        img = Image.open(
            requests.get(
                URL.GITHUB_STATIC + f"/images/memes/{query}.png",
                stream=True,
            ).raw,
        )
        draw = ImageDraw.Draw(img)

        logger.info("Drawing text")
        font_path = URL.LOCAL_STATIC + "/fonts/impact.ttf"

        font = ImageFont.truetype(font=str(font_path), size=font_size)
        text = caption.upper()
        width = draw.textlength(text, font, direction="rtl")
        height = draw.textlength(text, font, direction="ttb")

        x_coord = img.width / 2 - width / 2
        y_coord = img.height - height - 25 if align == "bottom" else 0

        draw.text((x_coord - 3, y_coord - 3), text, (0, 0, 0), font=font)
        draw.text((x_coord + 3, y_coord - 3), text, (0, 0, 0), font=font)
        draw.text((x_coord + 3, y_coord + 3), text, (0, 0, 0), font=font)
        draw.text((x_coord - 3, y_coord + 3), text, (0, 0, 0), font=font)
        draw.text((x_coord, y_coord), text, (255, 255, 255), font=font)

        logger.info("Saving captioned image")
        obj = io.BytesIO()
        img.save(obj, "png")
        obj.seek(0)

        logger.info("Sending image")
        await interaction.send(file=nextcord.File(obj, filename=f"{template}.png"))

    @slash_command(
        name="8ball",
        description="Provides a Magic 8-Ball answer to a yes/no question",
    )
    async def eightball(
        self,
        interaction: Interaction,
        question: str = SlashOption(description="What is your question?"),  # noqa: ARG002
    ) -> None:
        """Return a random Magic 8-Ball response.

        Args:
            interaction (Interaction): Invoking interaction
            question (str): Question text
        """
        answers = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes, definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful.",
        ]
        await interaction.send(random.choice(answers))

    @slash_command(description="Praise toucan")
    async def praise(self, interaction: Interaction) -> None:
        """Send Toucan ASCII art."""
        await interaction.send(TOUCAN_PRAISE)

    @slash_command(
        description="Calculates how to 'math' a target number from given digits",
    )
    async def fabricate_number(
        self,
        interaction: Interaction,
        wanted_result: str,
        comma_separated_digits: str,
    ) -> None:
        """Find a way to combine provided numbers to obtain a result.

        Args:
            interaction (Interaction): Invoking interaction
            wanted_result (str): Target number (user input)
            comma_separated_digits (str): Digits to user (user input)
        """
        try:
            target = int(wanted_result)
            digits = [int(i) for i in comma_separated_digits.split(",")]
        except Exception as e:
            await interaction.send(f"Bad input {e}")
            return

        if not digits or target == 0:
            await interaction.send(
                "Bad input - target must be non-zero and "
                "at least one digit must be provided",
            )
            return

        await interaction.response.defer()

        concatenations = create_concat_combinations(digits)
        num_digit_combinations = len(concatenations)
        did_cut = False
        attempt_limit = 50000
        if (
            num_digit_combinations > attempt_limit
        ):  # make sure someone doesn't super bomb it
            concatenations = concatenations[:attempt_limit]
            did_cut = True

        for concat_digits in concatenations:
            for dig in concat_digits:
                new_digits = concat_digits.copy()
                new_digits.remove(dig)
                res = await dfs(target, dig, new_digits, str(dig))
                if res:
                    msg = (
                        f"`{target}` from `{digits}` can be 'mathed' out "
                        f"this way:`{res}`"
                    )
                    await interaction.send(msg)
                    return

        if did_cut:
            await interaction.send(
                f"Nothing found in {attempt_limit}/{num_digit_combinations} combinations",  # noqa: E501
            )
        else:
            await interaction.send(
                f"Nothing found in {num_digit_combinations} combinations",
            )


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Fun())
