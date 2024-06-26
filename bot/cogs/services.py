import json
import logging
import re
from dataclasses import dataclass

import aiohttp
from nextcord import (
    Embed,
    Member,
    RawReactionActionEvent,
    SlashOption,
    slash_command,
    user_command,
)
from nextcord.ext.commands import Cog

import utils.util_functions as uf
from config.constants import ID, Color
from db_integration import db_functions as db

logger = logging.getLogger(__name__)


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
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Displays a user's profile picture.")
    async def avatar(
        self, interaction, user: Member = SlashOption(description="The target user")
    ):
        await interaction.send(embed=avatar_embed(user))

    @user_command(name="Avatar")
    async def avatar_context(self, interaction, user):
        await uf.invoke_slash_command("avatar", self, interaction, user)

    @slash_command(
        description="Returns the Urban Dictionary definition of a word or phrase"
    )
    async def urban(
        self, interaction, query=SlashOption(description="The word or phase to look up")
    ):
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
        interaction,
        stat=SlashOption(
            name="leaderboard",
            description="The leaderboard to display",
            choices=sorted(["Burger history", *ALL_LEADERBOARDS]),
        ),
    ):
        if stat == "Burger history":
            history = await db.get_note(self.bot, "burger history")
            if history:
                history = json.loads(history)
                mentions = [f"<@{user_id}>" for user_id in history]
                if len(mentions) == 1:
                    msg = f"The last person to hold the burger is {mentions[0]}"
                else:
                    msg = (
                        f"The last people to hold the burger are "
                        f"{','.join(mentions[:-1]) + ' and ' + mentions[-1]}"
                    )
            else:
                msg = "Burger history has not yet been recorded."
            await interaction.send(msg, ephemeral=True)
            return

        settings = ALL_LEADERBOARDS[stat]

        leaderboard = await create_leaderboard(self.bot, settings, interaction.guild.id)

        embed = build_leaderboard_embed(interaction, leaderboard, settings)

        await interaction.send(embed=embed)

    @slash_command(description="Award a skull.")
    async def skull(
        self,
        interaction,
        recipient: Member = SlashOption(description="The user to award a skull to"),
    ):
        if interaction.user.id != ID.JORM:
            await interaction.send(
                file=uf.simpsons_error_image(
                    dad=interaction.guild.me,
                    son=interaction.user,
                    text="You're not Jorm!",
                    filename="jormonly.png",
                )
            )
            return

        await db.get_or_insert_usr(self.bot, recipient.id, recipient.guild.id)

        await self.bot.pg_pool.execute(
            f"UPDATE usr SET skulls = skulls + 1 WHERE usr_id = {recipient.id}"
        )
        await interaction.send(f"Gave a 💀 to {recipient.mention}")

    @user_command(name="Give skull", guild_ids=[ID.GUILD])
    async def skull_context(self, interaction, user):
        await uf.invoke_slash_command("skull", self, interaction, user)

    @slash_command(description="Look up a user's stats")
    async def stats(
        self,
        interaction,
        user: Member = SlashOption(description="User to look up"),
        stat=SlashOption(
            description="Stat to look up", choices=["Everything", *ALL_LEADERBOARDS]
        ),
    ):
        if user == interaction.user:
            subject, possessive, has = "You", "Your", "have"
        else:
            subject, possessive, has = user.mention, user.mention + "'s", "has"

        if stat != "Everything":
            settings = ALL_LEADERBOARDS[stat]
            stats = await create_leaderboard(self.bot, settings, filter_by_user=user)
            if not stats:
                await interaction.send(
                    f"{subject} currently {has} no {settings.stat_name.lower()}."
                )
            elif "Roulette" in stat:
                await interaction.send(
                    f"{possessive} {settings.stat_name.lower()} "
                    f"is {stats[0]['total']} rounds."
                )
            else:
                await interaction.send(
                    f"{subject} currently {has} "
                    f"{stats[0]['total']} {settings.stat_name.lower()}."
                )
        else:
            message = f"{possessive} current stats are:\n"
            for settings in ALL_LEADERBOARDS.values():
                stats = await create_leaderboard(
                    self.bot, settings, filter_by_user=user
                )
                message += (
                    f"{settings.stat_name}: {stats[0]['total'] if stats else 0}\n"
                )
            await interaction.send(message)


async def create_leaderboard(bot, settings, guild_id=ID.GUILD, filter_by_user=None):
    filter_condition = (
        "AND usr_id = " + str(filter_by_user.id) if filter_by_user else ""
    )

    return await bot.pg_pool.fetch(
        f"SELECT usr_id, SUM({settings.stat_col_name}) as total "
        f"FROM {settings.table} "
        f"WHERE usr_id IN "
        f"(SELECT usr_id FROM usr WHERE guild_id = {guild_id}{filter_condition}) "
        f"GROUP BY usr_id "
        f"HAVING SUM({settings.stat_col_name}) > 0"
        f"ORDER BY total DESC ;"
    )


def build_leaderboard_embed(
    interaction,
    leaderboard,
    settings,
    count_col_name="total",
    usr_col_name="usr_id",
    max_print=12,
):
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


async def urban_handler(bot, payload):
    if not isinstance(payload, RawReactionActionEvent):
        return

    channel = bot.get_channel(payload.channel_id)
    try:
        message = await channel.fetch_message(payload.message_id)
        if (
            payload.user_id != ID.BOT
            and not payload.member.bot
            and message.embeds
            and message.embeds[0]
            and str(message.embeds[0].title).startswith("Page")
            and payload.emoji.name in ["⬅️", "➡️", "🇽"]
        ):
            if payload.emoji.name == "🇽":
                await message.clear_reaction("⬅️")
                await message.clear_reaction("➡️")
                await message.clear_reaction("🇽")
            else:
                embed = message.embeds[0]
                title = embed.title
                match = re.search(r"Page (\d+)/(\d+)", title)
                page, pages = int(match.group(1)), int(match.group(2))
                query = re.search(r"\[(.*)\]", embed.fields[0].value).group(1)
                user = message.guild.get_member(payload.user_id)
                if payload.emoji.name == "⬅️" and page > 1:
                    embed = await urban_embed(query, page - 1)
                elif payload.emoji.name == "➡️" and page < pages:
                    embed = await urban_embed(query, page + 1)
                await message.remove_reaction(payload.emoji, user)
                await message.edit(embed=embed)
    except Exception:
        logger.exception("Unexpected error")


def avatar_embed(user: Member) -> Embed:
    embed = Embed(color=Color.PALE_GREEN)
    link = user.display_avatar.url
    embed.set_image(url=link)
    embed.title = user.display_name + " (" + str(user) + ")"
    text = "Direct Link"
    embed.description = f"[{text}]({link})"
    return embed


async def urban_embed(query, page):
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
                    name="Word", value=f"[{word}]({web_link})", inline=False
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


def setup(bot):
    bot.add_cog(Services(bot))
