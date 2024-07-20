import io
import json
import logging
import random
import re
from datetime import datetime as dt
from datetime import timedelta
from itertools import permutations
from pathlib import Path

import aiohttp
import nextcord
import requests
from nextcord import (
    ButtonStyle,
    Embed,
    Member,
    SlashOption,
    slash_command,
    ui,
    user_command,
)
from nextcord.ext.commands import Cog
from PIL import Image, ImageDraw, ImageFont
from transliterate import translit
from transliterate.base import TranslitLanguagePack, registry

from db_integration import db_functions as db
from domain import (
    EMPTY_STRING,
    ID,
    URL,
    Duration,
    RoleName,
    Standby,
    Threshold,
    TimerType,
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


def add(lhs: int, rhs: int, pstr: str):
    return lhs + rhs, pstr + "+" + str(rhs)


def sub(lhs: int, rhs: int, pstr: str):
    return lhs - rhs, pstr + "-" + str(rhs)


def mult(lhs: int, rhs: int, pstr: str):
    if rhs == 0:
        return 0, ""
    return lhs * rhs, "(" + pstr + ")*" + str(rhs)


def div(lhs: int, rhs: int, pstr: str):
    return lhs / rhs, "(" + pstr + ")/" + str(rhs)


operations = [add, sub, mult, div]


def create_concat_combinations(digits):
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


async def dfs(target, current_target, current_digits, current_str):
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
    def __init__(self):
        self.standby = Standby()
        self.check_burger.start()

    def cog_unload(self):
        self.check_burger.cancel()

    @slash_command(description="YEE")
    async def yee(self, interaction):
        await interaction.send(YEEE)

    @slash_command(description="Gives a user a hug")
    async def hug(
        self,
        interaction,
        user: Member = SlashOption(description="The user you want to send a hug to"),
    ):
        if user == interaction.user:
            await interaction.send(URL.GITHUB_STATIC + "/images/selfhug.png")
        else:
            await interaction.send(
                f"{user.mention}, {interaction.user.mention} sent you a hug!"
            )
            hug = uf.get_emoji("BlobReachAndHug")
            if hug:
                await interaction.channel.send(hug)

    @user_command(name="Hug")
    async def hug_context(self, interaction, user):
        await uf.invoke_slash_command("hug", self, interaction, user)

    @slash_command(description="Pay your respects")
    async def f(
        self,
        interaction,
        target: str = SlashOption(
            description="What do you want to pay your respects to?", required=False
        ),
    ):
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
        interaction,
        meme: str = SlashOption(
            description="Start typing to see suggestions or enter `list` to "
            "see a list of all available memes"
        ),
    ):
        if meme == "list":
            help_text = (
                f"```Currently available memes:\n{"\n".join(["list", *ALL_MEMES])}```"
            )
            await interaction.response.send_message(help_text, ephemeral=True)
            return

        if "horny" in meme.lower() and interaction.user.id == ID.JORM:
            link = URL.GITHUB_STATIC + "/images/memes/Horny [DD].png"
            await interaction.response.send_message(link)
        elif meme in ALL_MEMES:
            meme_dir = Path(URL.LOCAL_STATIC) / "images/memes"
            matches = list(meme_dir.glob(f"{meme}*"))
            file = random.choice(matches)
            link = (
                URL.GITHUB_STATIC
                + "/images/memes/"
                + file.with_stem(file.stem.replace(", ", "%20")).name
            )
            await interaction.response.send_message(link)
        else:
            await interaction.response.send_message(
                f"No match found for '{meme}' - use `/meme list` "
                "to see a list of all available memes.",
                ephemeral=True,
            )

    @meme.on_autocomplete("meme")
    async def suggest_meme(self, interaction, user_input):
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
        self, interaction, text: str = SlashOption(description="Text to cyrillify")
    ):
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

    @slash_command(description="Burger someone")
    async def burger(
        self,
        interaction,
        target: Member = SlashOption(description="The person you want to burger"),
    ):
        logger.info(f"{interaction.user} is attempting to burger {target}")
        burgered = uf.get_role("Burgered")
        if burgered and burgered in interaction.user.roles:
            if target == interaction.user:
                await interaction.send(
                    "You can't burger yourself - you are already burgered!",
                    ephemeral=True,
                )
            elif target.bot:
                await interaction.send(
                    "Fool me once, shame on — shame on you. "
                    "Fool me — you can't get fooled again.",
                    ephemeral=True,
                )
            else:
                logger.info("Transferring burger")
                await interaction.user.remove_roles(burgered)
                await target.add_roles(burgered)

                logger.info("Sending message")
                await interaction.response.send_message(target.mention)
                await interaction.channel.send(
                    URL.GITHUB_STATIC + "/images/burgered.png"
                )

                logger.info("Setting timer")
                expires = dt.now() + Duration.BURGER_TIMEOUT
                await db.get_or_insert_usr(target.id, interaction.guild.id)
                await self.standby.pg_pool.execute(
                    f"DELETE FROM tmers WHERE ttype = {TimerType.BURGER};"
                )
                await self.standby.pg_pool.execute(
                    "INSERT INTO tmers (usr_id, expires, ttype) VALUES ($1, $2, $3);",
                    target.id,
                    expires,
                    TimerType.BURGER,
                )

                logger.info("Updating history")
                await self.standby.pg_pool.execute(
                    f"UPDATE usr SET burgers = burgers + 1 WHERE usr_id = {target.id}"
                )
                history = await db.get_note("burger history")
                if history:
                    history = json.loads(history)
                    history = [target.id, *history[:4]]
                else:
                    history = [target.id]
                await db.log_or_update_note("burger history", history)

        elif burgered.members:
            await interaction.send(
                f"{burgered.members[0].mention} holds the burger - "
                "only they may burger others.",
                ephemeral=True,
            )
        else:
            general = uf.get_channel("general")
            await interaction.send(
                "The burger is currently free for the taking - to burger others, you "
                f"must first claim it by answering the question in {general.mention}.",
                ephemeral=True,
            )

    @user_command(name="Burger")
    async def burger_context(self, interaction, user):
        await uf.invoke_slash_command("burger", self, interaction, user)

    @slash_command(description="Yoink the burger")
    async def yoink(self, interaction):
        logger.info(f"{interaction.user} is attempting to yoink the burger")
        await db.get_or_insert_usr(interaction.user.id, interaction.guild.id)

        burgered_role = uf.get_role("Burgered")
        holders = [
            member
            for member in interaction.guild.members
            if burgered_role in member.roles
        ]
        current_holder = holders[0]

        birthday_role = uf.get_role(RoleName.BIRTHDAY)
        if birthday_role in current_holder.roles:
            await interaction.send(
                f"{interaction.user.mention} has shamelessly attempted to yoink the "
                f"burger from the {birthday_role.mention}. The punishment for such a "
                "heinous crime is jail."
            )
            await uf.invoke_slash_command("jail", self, interaction, interaction.user)
            return

        recs = await self.standby.pg_pool.fetch(
            f"SELECT last_yoink FROM usr WHERE usr_id = {interaction.user.id}"
        )
        last_yoink = recs[0]["last_yoink"]
        if last_yoink and dt.now() - last_yoink < timedelta(days=30):
            logger.info("Not enough time has passed since last yoink - disallowing")
            await interaction.send(
                "You have yoinked the burger too recently and cannot do so again until "
                f"{uf.dynamic_timestamp(last_yoink + timedelta(days=30))}",
                ephemeral=True,
            )
            return

        logger.info("Yoinking")
        await current_holder.remove_roles(burgered_role)
        await self.standby.pg_pool.execute(
            f"DELETE FROM tmers WHERE ttype = {TimerType.BURGER}"
        )
        await interaction.user.add_roles(burgered_role)
        expires = dt.now() + Duration.BURGER_TIMEOUT
        await self.standby.pg_pool.execute(
            "INSERT INTO tmers (usr_id, expires, ttype) VALUES ($1, $2, $3);",
            interaction.user.id,
            expires,
            TimerType.BURGER,
        )
        await self.standby.pg_pool.execute(
            f"UPDATE usr SET last_yoink = '{dt.now()}', burgers = burgers + 1 "
            f"WHERE usr_id = {interaction.user.id}"
        )

        history = await db.get_note("burger history")
        if history:
            history = json.loads(history)
            history = [interaction.user.id, *history[:4]]
        else:
            history = [interaction.user.id]
        await db.log_or_update_note("burger history", history)
        await interaction.send(
            f"{interaction.user.mention} has yoinked the burger "
            f"from {current_holder.mention}!"
        )

    @uf.delayed_loop(minutes=1)
    async def check_burger(self):
        try:
            gtable = await self.standby.pg_pool.fetch(
                f"SELECT * FROM tmers WHERE ttype = {TimerType.BURGER}"
            )
        except AttributeError:
            logger.info("Bot hasn't loaded yet - pg_pool doesn't exist")
        except Exception:
            logger.exception("Unexpected exception - will retry in one minute")
            return

        for rec in gtable:
            timenow = dt.now()
            if timenow <= rec["expires"]:
                continue

            logger.info("Burger timer has expired")

            general = await self.standby.guild.fetch_channel(ID.GENERAL)
            user = await self.standby.guild.fetch_member(rec["usr_id"])
            burgered = uf.get_role("Burgered")
            if len(burgered.members) > 1:
                logger.warning("Multiple burgers detected.")
                maint = await self.standby.guild.fetch_channel(ID.ERROR_CHANNEL)
                await maint.send(
                    "Multiple burgers detected: "
                    f"{', '.join([usr.mention for usr in burgered.members])}"
                )

            await user.remove_roles(burgered)
            try:
                response = requests.get(
                    "https://the-trivia-api.com/v2/questions?limit=1"
                )
                data = json.loads(response.text)[0]
                params = {
                    "question": data["question"]["text"],
                    "correct": [data["correctAnswer"]],
                    "wrong": data["incorrectAnswers"],
                }
            except:
                logger.warning(
                    "Invalid response from Trivia API, using random default question"
                )
                questions = [
                    dict(
                        question="How much does the average "
                        "American ambulance trip cost?",
                        correct=["$1200"],
                        wrong=["$200", "$800"],
                    ),
                    dict(
                        question="How many Americans think the sun "
                        "revolves around the earth?",
                        correct=["1 in 4"],
                        wrong=["1 in 2", "1 in 3", "1 in 5"],
                    ),
                    dict(
                        question="How many avocados do Americans "
                        "eat a year combined?",
                        correct=["4.2 bn"],
                        wrong=["2 bn", "6.5 bn"],
                    ),
                    dict(
                        question="How many Americans get injuries "
                        "related to a TV falling every year?",
                        correct=["11 800"],
                        wrong=["5 200", "13 900"],
                    ),
                ]
                params = random.choice(questions)

            answers = [*params["correct"], *params["wrong"]]
            shuffled = answers.copy()
            random.shuffle(shuffled)
            params["ordering"] = [answers.index(elem) for elem in shuffled]
            params["attempted"] = []
            params["last_owner_id"] = user.id
            view = BurgerView(**params)

            recs = await self.standby.pg_pool.fetch(
                f"SELECT moldy_burgers FROM usr WHERE usr_id = {user.id}"
            )
            count = (recs[0]["moldy_burgers"] + 1) if recs else 1

            await self.standby.pg_pool.execute(
                f"UPDATE usr SET moldy_burgers = {count} WHERE usr_id = {user.id}"
            )

            msg = await general.send(
                f"After its {count}{uf.ordinal_suffix(count)} bout of fending off "
                f"the mold in {user.mention}'s fridge for a full week, the burger "
                f"yearns for freedom!\n"
                "To claim it, answer the following question:\n \n"
                f"{params['question']}",
                view=view,
            )
            await db.log_buttons(view, general.id, msg.id, params)
            await self.standby.pg_pool.execute(
                f"DELETE FROM tmers WHERE ttype = {TimerType.BURGER};"
            )

    @slash_command(description="Make predictions")
    async def prediction(self, interaction):
        pass

    @prediction.subcommand(description="Make a prediction")
    async def make(
        self,
        interaction,
        label: str = SlashOption(description="A label to identify your prediction"),
        text: str = SlashOption(description="The text of your prediction"),
    ):
        predictions = await uf.get_user_predictions(interaction.user)

        if label in predictions:
            num = len([key for key in predictions if key.startswith(label + "_")])
            label = f"{label}_{num + 2}"

        predictions[label] = {
            "timestamp": uf.dynamic_timestamp(uf.now(), "date and time"),
            "text": text,
        }

        logger.info(f"Adding prediction for {interaction.user}")
        await uf.update_user_predictions(interaction.user, predictions)
        await interaction.send(
            f"Prediction saved with label '{label}'!",
            ephemeral=True,
        )

        await interaction.channel.send(
            f"{interaction.user.mention} just made a prediction!"
        )

    @prediction.subcommand(description="Reveal a prediction")
    async def reveal(
        self,
        interaction,
        label: str = SlashOption(description="Label of the prediction to reveal"),
    ):
        predictions = await uf.get_user_predictions(interaction.user)
        if label in predictions:
            logger.info(f"Adding prediction '{label}' for {interaction.user}")
            params = {
                "owner_id": interaction.user.id,
                "votes_for": [],
                "votes_against": [],
            }
            view = PredictionView(**params)
            await interaction.send(
                f"On {predictions[label]['timestamp']}, {interaction.user.mention} "
                f"made the following prediction:\n{EMPTY_STRING}\n"
                f"{predictions[label]['text']}\n{EMPTY_STRING}\n"
                f"Does this prediction deserve an 🔮? Vote below!",
                view=view,
            )
            msg = await interaction.original_message()
            await db.log_buttons(view, interaction.channel.id, msg.id, params)
            predictions.pop(label)
            await uf.update_user_predictions(interaction.user, predictions)
        else:
            await interaction.send(
                f"No prediction found for the label '{label}'. "
                "You can use `/prediction list` "
                "to see a list of your active predictions.",
                ephemeral=True,
            )

    @prediction.subcommand(description="Check a prediction (privately)")
    async def check(
        self,
        interaction,
        label: str = SlashOption(
            description="Label of the prediction you want to check"
        ),
    ):
        predictions = await uf.get_user_predictions(interaction.user)
        if label in predictions:
            await interaction.send(
                f"Prediction '{label}' made on {predictions[label]['timestamp']}:"
                f"\n{EMPTY_STRING}\n"
                f"{predictions[label]['text']}",
                ephemeral=True,
            )
        else:
            await interaction.send(
                f"No prediction found for the label '{label}'. You can use "
                "`/prediction list` to see a list of your active predictions.",
                ephemeral=True,
            )

    @prediction.subcommand(name="list", description="List your predictions (privately)")
    async def list_(self, interaction):
        predictions = await uf.get_user_predictions(interaction.user)
        if not predictions:
            await interaction.send("You have not made any predictions!", ephemeral=True)
        else:
            for label, prediction in predictions.items():
                await interaction.send(
                    f"Prediction '{label}' made on {prediction['timestamp']}:"
                    f"\n{EMPTY_STRING}\n"
                    f"{prediction['text']}",
                    ephemeral=True,
                )

    @prediction.subcommand(description="Delete a prediction")
    async def delete(
        self,
        interaction,
        label: str = SlashOption(description="Label of the prediction to delete"),
    ):
        predictions = await uf.get_user_predictions(interaction.user)
        if label in predictions:
            logger.info(f"Removing prediction for {interaction.user}")
            predictions.pop(label)
            await uf.update_user_predictions(interaction.user, predictions)
            await interaction.send(
                f"Prediction '{label}' successfully deleted!", ephemeral=True
            )
        else:
            await interaction.send(f"No prediction found for the label '{label}'!")

    class VanityView(ui.View):
        def __init__(self, creator):
            super().__init__()
            self.value = None
            self.creator = creator

        @ui.select(placeholder="Pick a vanity role")
        async def select_role(self, select: ui.Select, interaction):
            if self.creator == interaction.user and select.values:
                self.value = select.values[0]

        @ui.button(label="Pick", style=ButtonStyle.blurple)
        async def press(self, button, interaction):  # noqa: ARG002
            if self.creator == interaction.user and self.value:
                self.stop()

    @slash_command(description="Pick a vanity role")
    async def vanity(self, interaction):
        view = self.VanityView(interaction.user)
        vanity_roles = uf.get_roles_by_type(interaction.guild, "Vanity")
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
        interaction,
        caption: str = SlashOption(description="The caption to use"),
        template: str = SlashOption(
            description="The base template to caption", choices=["Farquaad", "Megamind"]
        ),
    ):
        await interaction.response.defer()

        if template == "Farquaad":
            query, font_size, align = "Farquaad pointing", 100, "bottom"
        else:  # template == "Megamind":
            query, font_size, align = "Megamind no bitches", 125, "top"

        logger.info(f"Captioning {template=} for {interaction.user}")

        logger.info("Fetching base image")
        img = Image.open(
            requests.get(
                URL.GITHUB_STATIC + f"/images/memes/{query}.png", stream=True
            ).raw
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
        name="8ball", description="Provides a Magic 8-Ball answer to a yes/no question"
    )
    async def eightball(
        self,
        interaction,
        question=SlashOption(description="What is your question?"),  # noqa: ARG002
    ):
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
    async def praise(self, interaction):
        await interaction.send(TOUCAN_PRAISE)

    @slash_command(description="Do you feel lucky?")
    async def roulette(self, interaction):
        logger.info(f"{interaction.user} is feeling lucky")
        cooldown = await self.standby.pg_pool.fetch(
            "SELECT * FROM tmers "
            f"WHERE usr_id = {interaction.user.id} AND ttype = {TimerType.ROULETTE}"
        )

        if cooldown:
            expires = cooldown[0]["expires"]
            if dt.now() >= expires:
                logger.info("Cooldown expired, removing timer")
                await self.standby.pg_pool.execute(
                    f"DELETE FROM tmers WHERE usr_id = {interaction.user.id} "
                    f"AND ttype = {TimerType.ROULETTE}"
                )
            else:
                logger.info("User is timed out")
                await interaction.send(
                    "You have been timed out from using this command. "
                    "You will be able to use it again "
                    f"{uf.dynamic_timestamp(expires, 'relative')}",
                    ephemeral=True,
                )
                return

        await interaction.response.defer()

        stats = await db.ensured_get_usr(interaction.user.id, ID.GUILD)
        lose = random.randint(1, 6) == 6  # noqa: PLR2004

        if lose:
            logger.info(f"{interaction.user} has lost.")
            await self.standby.pg_pool.execute(
                "UPDATE usr SET current_roulette_streak = 0 "
                f"WHERE usr_id = {interaction.user.id}"
            )

            message = (
                f"Not all risks pay off, {interaction.user.mention}. "
                "Your streak has been reset."
            )
            try:
                logger.info(f"Setting full timeout for {interaction.user}")
                await interaction.user.timeout(Duration.ROULETTE_TIMEOUT)
                message = message[:-1] + " and you have been timed out."
            except nextcord.errors.Forbidden:
                logger.info(
                    f"Setting roulette timeout for privileged user {interaction.user}"
                )
                expires = dt.now() + Duration.ROULETTE_TIMEOUT
                await self.standby.pg_pool.execute(
                    "INSERT INTO tmers (usr_id, expires, ttype) VALUES ($1, $2, $3);",
                    interaction.user.id,
                    expires,
                    TimerType.ROULETTE,
                )
            await interaction.send(message)

        else:
            logger.info(f"{interaction.user} has won")
            current_streak = stats[0]["current_roulette_streak"]
            max_streak = stats[0]["max_roulette_streak"]

            server_current_max = await self.standby.pg_pool.fetch(
                "SELECT MAX(current_roulette_streak) from usr"
            )
            server_current_max = server_current_max[0]["max"]

            server_alltime_max = await self.standby.pg_pool.fetch(
                "SELECT MAX(max_roulette_streak) from usr"
            )
            server_alltime_max = server_alltime_max[0]["max"]

            await self.standby.pg_pool.execute(
                "UPDATE usr SET current_roulette_streak = current_roulette_streak + 1,"
                "max_roulette_streak = "
                "GREATEST(current_roulette_streak + 1, max_roulette_streak) "
                f"WHERE usr_id = {interaction.user.id}"
            )
            current_streak += 1

            plural_suffix = "s" if current_streak > 1 else ""

            message = (
                "Luck is on your side! You have now survived for "
                f"{current_streak} round{plural_suffix} in a row"
            )

            if current_streak > server_alltime_max:
                message += ", a new all-time record for the server!"
            elif current_streak > server_current_max and current_streak > max_streak:
                message += (
                    ", the highest currently active streak and a new personal best!"
                )
            elif current_streak > server_current_max:
                message += ", the highest currently active streak!"
            elif current_streak > max_streak:
                message += ", a new personal best!"
            else:
                message += "."

            await interaction.send(message)

    @slash_command(
        description="Calculates how to 'math' a target number from given digits"
    )
    async def fabricate_number(
        self, interaction, wanted_result, comma_separated_digits
    ):
        try:
            target = int(wanted_result)
            digits = [int(i) for i in comma_separated_digits.split(",")]
        except Exception as e:
            await interaction.send(f"Bad input {e}")
            return

        if not digits or target == 0:
            await interaction.send(
                "Bad input - target must be non-zero and "
                "at least one digit must be provided"
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
                f"Nothing found in {attempt_limit}/{num_digit_combinations} combinations"  # noqa: E501
            )
        else:
            await interaction.send(
                f"Nothing found in {num_digit_combinations} combinations"
            )

    class YesOrNo(ui.View):
        def __init__(self, intended_user):
            super().__init__()
            self.value = None
            self.yes = None
            self.intended_user = intended_user

        @ui.button(label="Yes", style=ButtonStyle.green)
        async def yes_button(self, button, interaction):  # noqa: ARG002
            if interaction.user == self.intended_user:
                self.yes = True
                self.stop()
            else:
                await interaction.send(
                    URL.GITHUB_STATIC + "/images/bobby.gif", ephemeral=True
                )

        @ui.button(label="No", style=ButtonStyle.red)
        async def no_button(self, button, interaction):  # noqa: ARG002
            if interaction.user == self.intended_user:
                self.yes = False
                self.stop()
            else:
                await interaction.send(
                    URL.GITHUB_STATIC + "/images/bobby.gif", ephemeral=True
                )

    @user_command(name="Thank", guild_ids=[ID.GUILD])
    async def thank_context(self, interaction, user):
        if user == interaction.user:
            await interaction.send(
                "Thanking yourself gives no reputation.", ephemeral=True
            )
            return

        await db.get_or_insert_usr(user.id, interaction.guild.id)
        await self.standby.pg_pool.execute(
            f"UPDATE usr SET thanks = thanks + 1 WHERE usr_id = {user.id}"
        )
        await interaction.send(f"Gave +1 Void to {user.mention}")

    @slash_command(description="Posts a random animal image")
    async def animal(
        self,
        interaction,
        animal=SlashOption(
            description="Choose a type of animal", choices={"Cat", "Dog", "Fox"}
        ),
    ):
        args = {
            "Cat": (
                "https://api.thecatapi.com/v1/images/search?size=full",
                "Meow",
                "https://thecatapi.com",
                "url",
            ),
            "Dog": (
                "https://dog.ceo/api/breeds/image/random",
                "Woof",
                "https://dog.ceo",
                "message",
            ),
            "Fox": (
                "https://randomfox.ca/floof/",
                "What does the fox say",
                "https://randomfox.ca",
                "image",
            ),
        }
        api_url, title, url, json_key = args[animal]
        async with aiohttp.ClientSession() as cs, cs.get(api_url) as r:
            data = await r.json()
            if not isinstance(data, dict):
                data = data[0]

            embed = Embed(title=title)
            embed.set_image(url=data[json_key])
            embed.set_footer(text=url)

            await interaction.send(embed=embed)

    @slash_command(description="Movie rating features")
    async def movie(self, interaction):
        pass

    @movie.subcommand(description="Rate a movie")
    async def rate(
        self,
        interaction,
        title,
        rating: int = SlashOption(
            description="Your rating",
            choices={
                "1 (Horrible)": 1,
                "2 (Bad)": 2,
                "3 (Decent)": 3,
                "4 (Good)": 4,
                "5 (Great)": 5,
            },
        ),
        review=SlashOption(description="Review or comment (optional)", required=False),
    ):
        title = uf.titlecase(title)
        exists = await self.standby.pg_pool.fetch(
            "SELECT * FROM movies "
            f"WHERE usr_id = '{interaction.user.id}' AND title = '{title}'"
        )
        if exists:
            await self.standby.pg_pool.execute(
                f"UPDATE movies SET rating = {rating}, review = '{review}' "
                f"WHERE usr_id = {interaction.user.id} AND title = '{title}'"
            )
            msg = (
                f"{interaction.user.mention} has updated their rating of {title}!\n"
                f"New rating: {rating}/5"
            )
            if review:
                msg += f"\nNew review: {review}"
            await interaction.send(msg)
        else:
            await self.standby.pg_pool.execute(
                "INSERT INTO movies (usr_id, title, rating, review) "
                "VALUES ($1, $2, $3, $4);",
                interaction.user.id,
                title,
                rating,
                review,
            )
            msg = f"{interaction.user.mention} has rated {title}!\nRating: {rating}/5"
            if review:
                msg += f"\nReview: {review}"
            await interaction.send(msg)

    @movie.subcommand(description="Check a movie's average score")
    async def score(self, interaction, title):
        title = uf.titlecase(title)
        ratings = await self.standby.pg_pool.fetch(
            f"SELECT COUNT(rating) AS count, ROUND(AVG(rating), 1) AS score "
            f"FROM movies WHERE title = '{title}'"
        )
        count, score = ratings[0]
        if count == 0:
            await interaction.send(f"{title} has not been rated yet.")
        else:
            await interaction.send(
                f"{title} currently has an average score of {score} "
                f"based off {count} rating(s)."
            )

    @movie.subcommand(description="Read all reviews for a movie")
    async def reviews(self, interaction, title):
        title = uf.titlecase(title)
        recs = await self.standby.pg_pool.fetch(
            f"SELECT usr_id, rating, review FROM movies WHERE title = '{title}'"
        )
        if not recs:
            await interaction.send(f"{title} has not been rated yet.")
            return

        for rec in recs:
            await interaction.send(f"Reviews currently on file for {title}:")
            msg = f"{uf.id_to_mention(rec['usr_id'])} rated it {rec['rating']}/5."
            if rec["review"]:
                msg = msg[:-1] + f" with the review:\n{rec['review']}"
            await interaction.send(msg)


class BurgerView(ui.View):
    def __init__(self, **params):
        super().__init__(timeout=None)
        self.last_owner_id = params["last_owner_id"]
        self.correct = params["correct"]
        self.attempted = params["attempted"]
        self.ordering = params["ordering"]
        answers = [*params["correct"], *params["wrong"]]

        for index in self.ordering:
            self.add_item(self.BurgerButton(label=answers[index]))

    class BurgerButton(ui.Button):
        def __init__(self, label):
            super().__init__(style=ButtonStyle.blurple, label=label)
            self.standby = Standby()

        async def callback(self, interaction):
            if interaction.user.id == self.view.last_owner_id:
                await interaction.send(
                    "The burger refuses to be held hostage by you any longer!",
                    ephemeral=True,
                )
                return
            if interaction.user.id in self.view.attempted:
                await interaction.send(
                    "You may only attempt to answer once", ephemeral=True
                )
                return

            if self.label in self.view.correct:
                await interaction.response.defer()
                burgered = uf.get_role("Burgered")
                await interaction.user.add_roles(burgered)
                for child in self.view.children:
                    child.disabled = True
                await interaction.edit(view=self.view)
                await interaction.send(
                    f"{interaction.user.mention} has claimed the burger! "
                    "Now use it wisely."
                )
                await self.standby.pg_pool.execute(
                    f"DELETE from buttons WHERE channel_id = {interaction.channel.id} "
                    f"AND message_id = {interaction.message.id}",
                )

                await db.get_or_insert_usr(interaction.user.id, interaction.guild.id)
                await self.standby.pg_pool.execute(
                    f"UPDATE usr SET burgers = burgers + 1 "
                    f"WHERE usr_id = {interaction.user.id}"
                )

                history = await db.get_note("burger history")
                if history:
                    history = json.loads(history)
                    mentions = [f"<@{user_id}>" for user_id in history]
                    if len(mentions) == 1:
                        msg = f"The last person to hold the burger is {mentions[0]}"
                    else:
                        msg = (
                            "The last people to hold the burger are "
                            f"{','.join(mentions[:-1])} and {mentions[-1]}"
                        )
                    await interaction.send(msg, ephemeral=True)
                    history = [interaction.user.id, *history[:4]]
                else:
                    history = [interaction.user.id]
                await self.standby.pg_pool.execute(
                    "INSERT INTO tmers (usr_id, expires, ttype) VALUES ($1, $2, $3);",
                    interaction.user.id,
                    dt.now() + Duration.BURGER_TIMEOUT,
                    TimerType.BURGER,
                )
                await db.log_or_update_note("burger history", history)

            else:
                await interaction.send(
                    f"{self.label} is not the correct answer - better luck next time!",
                    ephemeral=True,
                )
                self.view.attempted.append(interaction.user.id)
                await db.update_button_params(
                    interaction.message.id, {"attempted": self.view.attempted}
                )


class PredictionView(ui.View):
    def __init__(self, **params):
        super().__init__(timeout=None)
        self.standby = Standby()
        self.owner_id = params["owner_id"]
        self.votes_for = params["votes_for"]
        self.votes_against = params["votes_against"]

    @ui.button(emoji="🔮", style=ButtonStyle.blurple)
    async def award_orb(self, button, interaction):  # noqa: ARG002
        if interaction.user.id == self.owner_id:
            await interaction.send(
                "You can not award orbs to your own prediction!", ephemeral=True
            )
            return

        if interaction.user.id in self.votes_for:
            await interaction.send(
                "You have already voted for this prediction!", ephemeral=True
            )
            return

        if interaction.user.id in self.votes_against:
            self.votes_against.remove(interaction.user.id)

        self.votes_for.append(interaction.user.id)
        await interaction.send("Vote recorded!", ephemeral=True)

        if len(self.votes_for) >= Threshold.PREDICTIONS:
            await interaction.send(
                f"{uf.id_to_mention(self.owner_id)} has been awarded an orb!"
            )
            await self.standby.pg_pool.execute(
                f"DELETE FROM buttons WHERE message_id = {interaction.message.id}"
            )
            new_text = re.sub(
                "Does this prediction.*$",
                f"{uf.id_to_mention(self.owner_id)} was awarded an 🔮 "
                "for this prediction!",
                interaction.message.content,
            )
            await interaction.message.edit(content=new_text, view=None)
        else:
            await db.update_button_params(
                interaction.message.id,
                {"votes_for": self.votes_for, "votes_against": self.votes_against},
            )

    @ui.button(emoji="❌", style=ButtonStyle.blurple)
    async def deny_orb(self, button, interaction):  # noqa: ARG002
        if interaction.user.id == self.owner_id:
            await self.standby.pg_pool.execute(
                f"DELETE FROM buttons WHERE message_id = {interaction.message.id}"
            )
            new_text = re.sub(
                "Does this prediction.*$",
                f"{interaction.user.mention} has marked their prediction as incorrect.",
                interaction.message.content,
            )
            await interaction.message.edit(content=new_text, view=None)
            return

        if interaction.user.id in self.votes_against:
            await interaction.send(
                "You have already voted against this prediction!", ephemeral=True
            )
            return

        if interaction.user.id in self.votes_for:
            self.votes_for.remove(interaction.user.id)

        self.votes_against.append(interaction.user.id)
        await interaction.send("Vote recorded!", ephemeral=True)

        if len(self.votes_against) >= Threshold.PREDICTIONS:
            await interaction.send(
                f"{uf.id_to_mention(self.owner_id)}'s prediction has been deemed "
                "unworthy of an 🔮!"
            )
            await self.standby.pg_pool.execute(
                f"DELETE FROM buttons WHERE message_id = {interaction.message.id}"
            )
            new_text = re.sub(
                "Does this prediction.*$",
                f"{uf.id_to_mention(self.owner_id)} was not awarded an 🔮 "
                "for this prediction!",
                interaction.message.content,
            )
            await interaction.message.edit(content=new_text, view=None)
        else:
            await db.update_button_params(
                interaction.message.id,
                {"votes_for": self.votes_for, "votes_against": self.votes_against},
            )


def setup(bot):
    bot.add_cog(Fun())
