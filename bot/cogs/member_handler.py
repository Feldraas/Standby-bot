"""Monitor the server for member events."""

import asyncio
import logging
import random

from nextcord import Embed, Member
from nextcord.ext.commands import Bot, Cog

from domain import URL, ChannelName, Color, Standby
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class MemberHandler(Cog):
    def __init__(self) -> None:
        self.standby = Standby()

    @Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        """Called when a member leaves the server."""
        await leave_message(member)

    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        """Called when a member joins the server."""
        await welcome_message(member)

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:
        """Called when a member is updated."""
        await level3_handler(before, after)


async def welcome_message(member: Member) -> None:
    """Send a welcome message to #general when a user joins the server.

    Args:
        member (Member): The new member
    """
    logger.info(f"{member} has joined the guild")
    general = uf.get_channel(ChannelName.GENERAL)
    rules_ch = uf.get_channel(ChannelName.RULES)
    rules_text = rules_ch.mention if rules_ch else f"#{ChannelName.Rules}"
    if not general:
        logger.error("Could not find general channel")
        return
    message = (
        f"Welcome {member.mention}!\n"
        "Wondering why the server seems so void of channels?\n"
        f"Please read the rules in {rules_text} to unlock the full server!\n"
        "https://www.youtube.com/watch?v=67h8GyNgEmA"
    )

    await general.send(message)
    await asyncio.sleep(30 * 60)
    if (
        not member.bot
        and member.guild.get_member(member.id)
        and (uf.get_role("Alliance") not in member.roles)
        and (uf.get_role("Community") not in member.roles)
    ):
        logger.info(f"Sending reminder to {member}")
        await general.send(
            f"Hey {member.mention} - I see you still haven't unlocked "
            f"the full server. Make sure you read {rules_ch.mention} "
            "and use the buttons so you can access all of our channels!",
        )


async def leave_message(member: Member) -> None:
    """Send an message to the maintenance channel when a user leaves.

    Args:
        member (Member): The user who left
    """
    channel = uf.get_channel(ChannelName.ERRORS)
    if not channel:
        logger.error("Could not find error channel")
        return

    logger.info(f"Sending obit message for {member}")
    name = member.name
    time = uf.utcnow()
    time = time.strftime("%b %d, %H:%M")
    embed = Embed(color=Color.GREY)
    embed.title = "The void grows smaller..."
    embed.set_thumbnail(url=URL.GITHUB_STATIC + "/images/grave.png")
    embed.description = f":rocket: {name} has left the void :rocket:"
    causes = [
        "ded",
        "Couldn't find their socks fast enough",
        "Yeeted themselves off a very high chair",
        "Forgot how to breathe",
        "Stickbugged one time too many",
        "Disrespected the pedestal",
        "Terminal case of being horny",
        "Sacrificed at the altar of Tzeentch",
        "Critical paper cut",
        "Executed by the ICC for their numerous war crimes in Albania",
    ]
    animu = uf.get_channel("animu")
    if animu:
        causes.append(f"Too much time spent in {animu.mention}")
    embed.add_field(name="Time of death", value=time)
    embed.add_field(
        name="Cause of death",
        value=causes[random.randint(1, len(causes)) - 1],
    )
    await channel.send(embed=embed)


async def level3_handler(before: Member, after: Member) -> None:
    """Check if a member reached level 3.

    Args:
        before (Member): The member before the event
        after (Member): The member after the event
    """
    if len(after.roles) - len(before.roles) != 1:
        return

    lv3 = uf.get_role("Level 3")
    alliance = uf.get_role("Alliance")

    if lv3 not in before.roles and lv3 in after.roles and alliance in after.roles:
        giveaways = uf.get_role("Giveaways")
        await after.add_roles(giveaways)


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(MemberHandler())
