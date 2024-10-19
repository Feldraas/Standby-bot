"""Service type commands - server statistics etc."""

import logging
import re

import aiohttp
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
