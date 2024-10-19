"""Service type commands - server statistics etc."""

import json
import logging
import re
from dataclasses import dataclass

import aiohttp
from asyncpg import Record
from nextcord import (
    Embed,
    Interaction,
    Member,
    RawReactionActionEvent,
    SlashOption,
    slash_command,
    user_command,
)
from nextcord.ext.commands import Bot, Cog

import utils.util_functions as uf
from domain import ID, Color, Standby

logger = logging.getLogger(__name__)


# TODO: Rework


@dataclass
class LeaderboardSettings:
    title: str
    stat_name: str
    stat_col_name: str
    user_name: str = "User"
    color: str = Color.VIE_PURPLE
    table: str = "usr"
    stat_embed_header: str = None


ALL_LEADERBOARDS = {
    "Stars": LeaderboardSettings(
        title="Stars leaderboard",
        stat_name="Stars",
        stat_embed_header="⭐",
        stat_col_name="stars",
        color=Color.STARBOARD,
        table="starboard",
    ),
    "Voids": LeaderboardSettings(
        title="Voids leaderboard",
        stat_name="Voids",
        stat_embed_header="Voids",
        stat_col_name="thanks",
    ),
    "Skulls": LeaderboardSettings(
        title="Skulls leaderboard",
        stat_name="Skulls",
        stat_col_name="skulls",
        stat_embed_header="💀",
        user_name="Metalhead",
    ),
    "Roulette (current)": LeaderboardSettings(
        title="Roulette leaderboard (current)",
        stat_name="Current roulette streak",
        stat_col_name="current_roulette_streak",
        stat_embed_header="Rounds",
    ),
    "Roulette (all-time)": LeaderboardSettings(
        title="Roulette leaderboard (all-time)",
        stat_name="All-time best roulette streak",
        stat_col_name="max_roulette_streak",
        stat_embed_header="Rounds",
    ),
    "Burgers": LeaderboardSettings(
        title="Burger leaderboard",
        stat_name="Burgers",
        stat_col_name="burgers",
        stat_embed_header="🍔",
    ),
    "Moldy burgers": LeaderboardSettings(
        title="Moldy burger leaderboard",
        stat_name="Moldy burgers",
        stat_col_name="moldy_burgers",
        stat_embed_header="🦠🍔",
    ),
    "Orbs": LeaderboardSettings(
        title="Orb leaderboard",
        stat_name="Orbs",
        stat_col_name="orbs",
        stat_embed_header="🔮",
        user_name="Oracle",
    ),
}


class Services(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @slash_command(description="Displays a user's profile picture.")
    async def avatar(
        self,
        interaction: Interaction,
        user: Member = SlashOption(description="The target user"),
    ) -> None:
        """Send a full version of the user's avatar."""
        await interaction.send(embed=avatar_embed(user))

    @user_command(name="Avatar")
    async def avatar_context(self, interaction: Interaction, user: Member) -> None:
        """Invoke the avatar command through the user context menu."""
        await uf.invoke_slash_command("avatar", interaction, user)

    @slash_command(
        description="Returns the Urban Dictionary definition of a word or phrase",
    )
    async def urban(
        self,
        interaction: Interaction,
        query: str = SlashOption(description="The word or phase to look up"),
    ) -> None:
        """Look up a word or phrase in Urban Dictionary."""
        response = await urban_embed(query, 1)
        if isinstance(response, Embed):
            await interaction.send(embed=response)
            message = await interaction.original_message()
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")
            await message.add_reaction("🇽")
        elif isinstance(response, str):
            await interaction.send(response)

    @slash_command(description="Displays the leaderboards")
    async def leaderboard(
        self,
        interaction: Interaction,
        stat: str = SlashOption(
            name="leaderboard",
            description="The leaderboard to display",
            choices=sorted(ALL_LEADERBOARDS),
        ),
    ) -> None:
        """Return the leaderboard for a certain statistic.

        Args:
            interaction (Interaction): Invoking interaction.
            stat (str): The leaderboard to display
        """
        settings = ALL_LEADERBOARDS[stat]

        leaderboard = await create_leaderboard(settings)

        embed = build_leaderboard_embed(interaction, leaderboard, settings)

        await interaction.send(embed=embed)

    @slash_command(description="Look up a user's stats")
    async def stats(
        self,
        interaction: Interaction,
        user: Member = SlashOption(description="User to look up"),
        stat: str = SlashOption(
            description="Stat to look up",
            choices=["Everything", *ALL_LEADERBOARDS],
        ),
    ) -> None:
        """Look up a user's recorded statistics.

        Args:
            interaction (Interaction): Invoking interaction
            user (Member, optional): Target user
            stat (str, optional): Stat to look up
        """
        if user == interaction.user:
            subject, possessive, has = "You", "Your", "have"
        else:
            subject, possessive, has = user.mention, user.mention + "'s", "has"

        if stat != "Everything":
            settings = ALL_LEADERBOARDS[stat]
            stats = await create_leaderboard(settings, filter_by_user=user)
            if not stats:
                await interaction.send(
                    f"{subject} currently {has} no {settings.stat_name.lower()}.",
                )
            elif "Roulette" in stat:
                await interaction.send(
                    f"{possessive} {settings.stat_name.lower()} "
                    f"is {stats[0]['total']} rounds.",
                )
            else:
                await interaction.send(
                    f"{subject} currently {has} "
                    f"{stats[0]['total']} {settings.stat_name.lower()}.",
                )
        else:
            message = f"{possessive} current stats are:\n"
            for settings in ALL_LEADERBOARDS.values():
                stats = await create_leaderboard(settings, filter_by_user=user)
                message += (
                    f"{settings.stat_name}: {stats[0]['total'] if stats else 0}\n"
                )
            await interaction.send(message)

    @Cog.listener()
    async def on_raw_reaction_add(self, event: RawReactionActionEvent) -> None:
        """Manipulate Urban Dictionary embeds using reactions."""
        channel = Standby().bot.get_channel(event.channel_id)
        try:
            message = await channel.fetch_message(event.message_id)
            if (
                event.user_id != ID.BOT
                and not event.member.bot
                and message.embeds
                and message.embeds[0]
                and str(message.embeds[0].title).startswith("Page")
                and event.emoji.name in ["⬅️", "➡️", "🇽"]
            ):
                if event.emoji.name == "🇽":
                    await message.clear_reaction("⬅️")
                    await message.clear_reaction("➡️")
                    await message.clear_reaction("🇽")
                else:
                    embed = message.embeds[0]
                    title = embed.title
                    match = re.search(r"Page (\d+)/(\d+)", title)
                    page, pages = int(match.group(1)), int(match.group(2))
                    query = re.search(r"\[(.*)\]", embed.fields[0].value).group(1)
                    user = message.guild.get_member(event.user_id)
                    if event.emoji.name == "⬅️" and page > 1:
                        embed = await urban_embed(query, page - 1)
                    elif event.emoji.name == "➡️" and page < pages:
                        embed = await urban_embed(query, page + 1)
                    await message.remove_reaction(event.emoji, user)
                    await message.edit(embed=embed)
        except Exception:
            logger.exception("Unexpected error")


async def create_leaderboard(
    settings: LeaderboardSettings,
    filter_by_user: Member | None = None,
) -> list[Record]:
    """Get recorded statistics from the database.

    Args:
        settings (LeaderboardSettings): Type of leaderboard to get
            data for
        filter_by_user (Member | None, optional): If provided, get only
            the user's statistics. Otherwise, get everyone's.

    Returns:
        list[Record]: _description_
    """
    filter_condition = (
        "AND usr_id = " + str(filter_by_user.id) if filter_by_user else ""
    )
    standby = Standby()
    return await standby.pg_pool.fetch(f"""
        SELECT
            usr_id,
            SUM({settings.stat_col_name}) as total
        FROM
            {settings.table}
        WHERE
            usr_id IN (
                SELECT
                    usr_id
                FROM
                    usr
                WHERE
                    guild_id = {standby.guild.id}{filter_condition}
            )
        GROUP BY
            usr_id
        HAVING
            SUM({settings.stat_col_name}) > 0
        ORDER BY
            total DESC
        """)


def build_leaderboard_embed(
    interaction: Interaction,
    leaderboard: list[Record],
    settings: LeaderboardSettings,
    count_col_name: str = "total",
    usr_col_name: str = "usr_id",
    max_print: int = 12,
) -> Embed:
    """Create a leaderboard embed.

    Args:
        interaction (Interaction): Invoking interaction
        leaderboard (list[Record]): User statistics
        settings (LeaderboardSettings): Type of leaderboard
        count_col_name (str, optional): Name for the count column.
            Defaults to "total".
        usr_col_name (str, optional): Name for the user column.
            Defaults to "usr_id".
        max_print (int, optional): Maximum number of entries to print.
            Defaults to 12.

    Returns:
        Embed: Embed containing top users.
    """
    if not leaderboard:
        return Embed(
            color=settings.color,
            description=f"The {settings.title} is currently empty.",
        )

    users = []
    scores = []

    for rec in leaderboard:
        if (
            len(users) < max_print
            or rec[count_col_name] == scores[-1]
            or rec[usr_col_name] == interaction.user.id
        ):
            users.append(uf.id_to_mention(rec[usr_col_name]))
            scores.append(str(rec[count_col_name]))

    embed = Embed(color=settings.color)
    embed.add_field(name=settings.stat_embed_header, value="\n".join(scores))
    embed.add_field(name=settings.user_name, value="\n".join(users))
    embed.title = settings.title
    return embed


def avatar_embed(user: Member) -> Embed:
    """Create an embed holding a user avatar."""
    embed = Embed(color=Color.PALE_GREEN)
    link = user.display_avatar.url
    embed.set_image(url=link)
    embed.title = user.display_name + " (" + str(user) + ")"
    text = "Direct Link"
    embed.description = f"[{text}]({link})"
    return embed


async def urban_embed(query: str, page: int) -> Embed | str:
    """Create an embed for an Urban Dictionary definition.

    Args:
        query (str): Phrase to look up
        page (int): Page to display

    Returns:
        Embed | str: Embed containing the definition (if found).
            Otherwise, an error message.
    """
    async with aiohttp.ClientSession() as cs:
        api_link = f"https://api.urbandictionary.com/v0/define?term={query}"
        async with cs.get(api_link) as r:
            data = await r.json()
            if "error" in data:
                return "Server is not responding, please try again later."
            if len(data["list"]) > 0:
                entries = data["list"]
                pages = len(entries)
                entry = entries[page - 1]
                embed = Embed(color=Color.DARK_ORANGE)
                embed.title = f"Page {page}/{pages}"
                word = entry["word"]
                web_link = f"https://www.urbandictionary.com/define.php?term={word}"
                web_link = re.sub(" ", "%20", web_link)
                embed.add_field(
                    name="Word",
                    value=f"[{word}]({web_link})",
                    inline=False,
                )
                embed.add_field(
                    name="Definition",
                    value=entry["definition"][:1018] + " [...]",
                    inline=False,
                )
                embed.add_field(name="Example", value=entry["example"], inline=False)
                embed.add_field(name="Author", value=entry["author"], inline=False)
                embed.add_field(
                    name="Rating",
                    inline=False,
                    value=f"{entry['thumbs_up']} :thumbsup: / "
                    f"{entry['thumbs_down']} :thumbsdown:",
                )
                return embed
            return "No definition found."


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(Services())
