"""Burger features."""

import json
import logging
import random
from datetime import datetime, timedelta
from enum import StrEnum

import requests
from nextcord import (
    ButtonStyle,
    Interaction,
    Member,
    SlashOption,
    slash_command,
    user_command,
)
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import Button, View

from domain import (
    ID,
    URL,
    RoleName,
    Standby,
)
from utils import util_functions as uf

logger = logging.getLogger(__name__)

BURGER_TIMEOUT = timedelta(weeks=1)
YOINK_COOLDOWN = timedelta(days=30)


class Burger(Cog):
    def __init__(self) -> None:
        self.standby = Standby()
        self.check_burger.start()

    @slash_command(description="Burger someone")
    async def burger(
        self,
        interaction: Interaction,
        target: Member = SlashOption(description="The person you want to burger"),
    ) -> None:
        """Burger another user."""
        user = interaction.user
        logger.info(f"{user} is attempting to burger {target}")
        burgered = uf.get_role("Burgered") or interaction.guild.create_role("Burgered")

        if user not in burgered.members:
            if burgered.members:
                await interaction.send(
                    f"{burgered.members[0].mention} holds the burger - "
                    "only they may burger others.",
                    ephemeral=True,
                )
                return

            general = uf.get_channel("general")
            await interaction.send(
                "The burger is currently free for the taking - to burger others, you "
                f"must first claim it by answering the question in {general.mention}.",
                ephemeral=True,
            )
            return

        if target == interaction.user:
            await interaction.send(
                "You can't burger yourself - you are already burgered!",
                ephemeral=True,
            )
            return

        if target.bot:
            await interaction.send(
                "Fool me once, shame on — shame on you. "
                "Fool me — you can't get fooled again.",
                ephemeral=True,
            )
            return

        await record_burger_transfer(from_=user, to=target, reason=TransferReason.GIVE)
        await interaction.user.remove_roles(burgered)
        await target.add_roles(burgered)

        await interaction.response.send_message(target.mention)
        await interaction.channel.send(
            URL.GITHUB_STATIC + "/images/burgered.png",
        )

    @user_command(name="Burger")
    async def burger_context(self, interaction: Interaction, user: Member) -> None:
        """Burger a user through the user context menu."""
        await uf.invoke_slash_command("burger", self, interaction, user)

    @slash_command(description="Yoink the burger")
    async def yoink(self, interaction: Interaction) -> None:
        """Yoink the burger. Limited to one yoink per month."""
        logger.info(f"{interaction.user} is attempting to yoink the burger")

        burgered_role = uf.get_role("Burgered")
        if not burgered_role.members:
            general = uf.get_channel("general")
            await interaction.send(
                "The burger is currently free for the taking - to burger others, you "
                f"must first claim it by answering the question in {general.mention}.",
                ephemeral=True,
            )
            return

        current_holder = burgered_role.members[0]

        birthday_role = uf.get_role(RoleName.BIRTHDAY)
        if birthday_role in current_holder.roles:
            await interaction.send(
                f"{interaction.user.mention} has shamelessly attempted to yoink the "
                f"burger from the {current_holder.mention}. The punishment for such a "
                "heinous crime is jail.",
            )
            await uf.invoke_slash_command("jail", self, interaction, interaction.user)
            return

        last_yoink = get_last_transfer_time(
            to=interaction.user,
            reason=TransferReason.YOINK,
        )
        if last_yoink and uf.now() - last_yoink < YOINK_COOLDOWN:
            logger.info("Not enough time has passed since last yoink - disallowing")
            await interaction.send(
                "You have yoinked the burger too recently and cannot do so again until "
                f"{uf.dynamic_timestamp(last_yoink + YOINK_COOLDOWN)}",
                ephemeral=True,
            )
            return

        await record_burger_transfer(
            from_=current_holder,
            to=interaction.user,
            reason=TransferReason.YOINK,
        )

    @slash_command(
        name="burger-history",
        description="See who previously held the burger",
    )
    async def history(self, interaction: Interaction) -> None:
        """H."""
        holders = await get_last_holders(n=10)
        holder_string = " -> ".join(holder.mention for holder in reversed(holders))
        await interaction.send(
            f"The last people to hold the burger are {holder_string}",
            ephemeral=True,
        )

    @uf.delayed_loop(minutes=1)
    async def check_burger(self) -> None:
        """Check whether the burger holding period has expired."""
        logger.debug("Checking burger")

        last_transfer = await get_last_transfer_time()
        if last_transfer is None:
            return

        expiration = last_transfer + BURGER_TIMEOUT

        if expiration > uf.now():
            return

        logger.info("Burger has expired")

        already_sent = await check_if_already_sent()
        if already_sent:
            return

        burgered = uf.get_role("Burgered")
        holder = None
        for holder in burgered.members:
            await holder.remove_roles(burgered)

        params = get_trivia_question()
        params["attempted"] = []

        general = await self.standby.guild.fetch_channel(ID.GENERAL)

        if holder:
            await record_burger_transfer(
                from_=holder,
                to=None,
                reason=TransferReason.MOLD,
            )
            params["last_owner_id"] = holder.id
            view = BurgerView(params)

            mold_count = await get_mold_count(holder)

            message = await general.send(
                f"After its {mold_count}{uf.ordinal_suffix(mold_count)} bout of "
                f"fending off the mold in {holder.mention}'s fridge for a full week, "
                f"the burger yearns for freedom!\n"
                "To claim it, answer the following question:\n \n"
                f"{params['question']}",
                view=view,
            )
        else:
            params["last_owner_id"] = None

            view = BurgerView(params)

            message = await general.send(
                "Somehow, the burger was lost and is now looking for a new owner.\n"
                "To claim it, answer the following question:\n \n"
                f"{params['question']}",
                view=view,
            )

        await uf.record_view(view, general.id, message.id)


class BurgerView(View):
    """Trivia question buttons when the burger expires for a user."""

    params: dict

    def __init__(self, params: dict | None = None) -> None:
        super().__init__(timeout=None)
        self.params = params or {}
        answers = [*params["correct"], *params["wrong"]]

        for index in self.params["ordering"]:
            self.add_item(self.BurgerButton(label=answers[index]))

    class BurgerButton(Button):
        """Button for each answer option."""

        def __init__(self, label: str) -> None:
            """Set label."""
            super().__init__(style=ButtonStyle.blurple, label=label)
            self.standby = Standby()

        async def callback(self, interaction: Interaction) -> None:
            """Action when a button is pressed."""
            if interaction.user.id == self.view.params["last_owner_id"]:
                await interaction.send(
                    "The burger refuses to be held hostage by you any longer!",
                    ephemeral=True,
                )
                return
            if interaction.user.id in self.view.params["attempted"]:
                await interaction.send(
                    "You may only attempt to answer once",
                    ephemeral=True,
                )
                return

            if self.label not in self.view.params["correct"]:
                await interaction.send(
                    f"{self.label} is not the correct answer - better luck next time!",
                    ephemeral=True,
                )
                self.view.params["attempted"].append(interaction.user.id)
                await uf.record_view(
                    self.view,
                    interaction.channel.id,
                    interaction.message.id,
                )
                return

            await interaction.response.defer()

            burgered = uf.get_role("Burgered")
            await interaction.user.add_roles(burgered)

            from cogs.burger import TransferReason, record_burger_transfer

            await record_burger_transfer(
                from_=None,
                to=interaction.user,
                reason=TransferReason.QUESTION,
            )

            for child in self.view.children:
                child.disabled = True
            await interaction.edit(view=self.view)
            await interaction.send(
                f"{interaction.user.mention} has claimed the burger! "
                "Now use it wisely.",
            )
            await uf.delete_view_record(interaction.message.id)


class TransferReason(StrEnum):
    GIVE = "give"
    YOINK = "yoink"
    MOLD = "mold"
    QUESTION = "question"


async def record_burger_transfer(
    from_: Member | None,
    to: Member | None,
    reason: TransferReason,
) -> None:
    """Add an entry to the burger table recording the transfer.

    Args:
        from_ (Member | None): Burger holder before transfer
        to (Member | None): Burger holder after transfer
        reason (TransferReason): Reason for transfer
    """
    pg_pool = Standby().pg_pool
    schema = Standby().schema
    giver_id = from_.id if from_ else None
    recipient_id = to.id if to else None
    await pg_pool.execute(
        f"""
        INSERT INTO
            {schema}.burger (giver_id, recipient_id, transferred_at, reason)
        VALUES
            ($1, $2, $3, $4)
        """,
        giver_id,
        recipient_id,
        uf.now(),
        reason,
    )


async def get_last_transfer_time(
    *,
    from_: Member | None = None,
    to: Member | None = None,
    reason: TransferReason | None = None,
) -> datetime | None:
    """Get the last time the burger was transferred.

    Provided keyword arguments will filter the selection.
    """
    pg_pool = Standby().pg_pool
    schema = Standby().schema

    query = f"""
        SELECT
            MAX(transferred_at)
        FROM
            {schema}.burger
        WHERE recipient_id IS NOT NULL
        """

    if from_:
        query += f" AND giver_id = {from_.id}"
    if to:
        query += f" AND recipient_id = {to.id}"
    if reason:
        query += f" AND reason = '{reason}'"

    return await pg_pool.fetchval(query)


async def get_mold_count(user: Member) -> int:
    """Get number of times user has let the burger expire."""
    pg_pool = Standby().pg_pool
    schema = Standby().schema
    return await pg_pool.fetchval(f"""
        SELECT
            COUNT(*)
        FROM
            {schema}.burger
        WHERE
            giver_id = {user.id}
            AND reason = '{TransferReason.MOLD}'
        """)


def get_trivia_question() -> dict[str, str | list[str]]:
    """Fetch trivia question from API.

    In case of error, return a random pre-set question.
    """
    try:
        response = requests.get(
            "https://the-trivia-api.com/v2/questions?limit=1",
        )
        data = json.loads(response.text)[0]
        question = {
            "question": data["question"]["text"],
            "correct": [data["correctAnswer"]],
            "wrong": data["incorrectAnswers"],
        }
    except:
        logger.warning(
            "Invalid response from Trivia API, using random default question",
        )
        questions = [
            {
                "question": "How much does the average American ambulance trip cost?",
                "correct": ["$1200"],
                "wrong": ["$200", "$800"],
            },
            {
                "question": "How many Americans think the sun revolves around the earth?",  # noqa: E501
                "correct": ["1 in 4"],
                "wrong": ["1 in 2", "1 in 3", "1 in 5"],
            },
            {
                "question": "How many avocados do Americans eat a year combined?",
                "correct": ["4.2 bn"],
                "wrong": ["2 bn", "6.5 bn"],
            },
            {
                "question": "How many Americans get injuries related to a TV falling every year?",  # noqa: E501
                "correct": ["11 800"],
                "wrong": ["5 200", "13 900"],
            },
        ]
        question = random.choice(questions)

    answers = [*question["correct"], *question["wrong"]]
    shuffled = answers.copy()
    random.shuffle(shuffled)
    question["ordering"] = [answers.index(elem) for elem in shuffled]

    return question


async def check_if_already_sent() -> bool:
    """C."""
    pg_pool = Standby().pg_pool
    schema = Standby().schema
    await uf.clean_view_table()
    view = await pg_pool.fetchval(f"""
        SELECT
            *
        FROM
            {schema}.view
        WHERE
            class = 'BurgerView'
        """)
    return view is not None


async def get_last_holders(n: int = 10) -> list[Member]:
    """G."""
    standby = Standby()
    records = await standby.pg_pool.fetch(f"""
        SELECT
            recipient_id
        FROM
            {standby.schema}.burger
        WHERE
            recipient_id IS NOT NULL
        ORDER BY
            transferred_at DESC
        LIMIT
            {n}
        """)

    users = []
    for record in records:
        user = await standby.bot.fetch_user(record["recipient_id"])
        users.append(user)
    return users


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Burger())
