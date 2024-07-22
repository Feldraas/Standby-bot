"""Miscellaneous support functions used throughout the project."""

import asyncio
import io
import json
import re
from collections.abc import Callable, Sequence
from datetime import datetime, time, timedelta
from typing import Literal

import nextcord
import requests
from discord import CategoryChannel
from nextcord import Embed, Emoji, File, Guild, Interaction, Member, Message, Role
from nextcord.ext.commands import Cog
from nextcord.ext.tasks import LF, Loop
from nextcord.utils import MISSING
from PIL import Image, ImageDraw, ImageFont

from domain import (
    BOT_TZ,
    EMPTY_STRING,
    URL,
    Color,
    RoleName,
    Standby,
    ValidTextChannel,
)

standby = Standby()


def get_emoji(name: str) -> Emoji | None:
    """Wrapper for the built-in get function."""
    return nextcord.utils.get(standby.guild.emojis, name=name)


def get_role(name: str) -> Role | None:
    """Wrapper for the built-in get function."""
    return nextcord.utils.find(
        lambda r: r.name.lower() == name.lower(),
        standby.guild.roles,
    )


def get_category(guild: Guild, name: str) -> CategoryChannel | None:
    """Wrapper for the built-in get function."""
    return nextcord.utils.get(guild.categories, name=name)


def mention_role(name: str) -> str:
    """Get a mention string for a role."""
    role = get_role(standby.guild, name)
    if role:
        return role.mention
    return "@" + name


def get_channel(name: str) -> ValidTextChannel:
    """Find a channel matching a name or mention string."""
    match = re.search(r"(\d+)", name)
    if match:
        return nextcord.utils.get(
            standby.guild.text_channels
            + standby.guild.threads
            + standby.guild.voice_channels,
            id=int(match.group(1)),
        )
    name = name.replace("#", "")
    channel = nextcord.utils.get(standby.guild.text_channels, name=name)
    return channel or nextcord.utils.get(
        standby.guild.threads + standby.guild.voice_channels,
        name=name,
    )


def get_user(guild: Guild, query: str) -> Member | None:
    """Get a user from a uniquely identifying query."""
    if re.search(r".*#\d{4}$", query):
        query, tag = re.split(" ?#", query)
    else:
        tag = None

    if tag:
        users = [
            user
            for user in standby.guild.members
            if (user.name.lower() == query.lower() and user.discriminator == tag)
        ]
    else:
        users = [
            user
            for user in guild.members
            if re.search(query, f"{user.name}|{user.display_name}", re.IGNORECASE)
        ]

    if len(users) == 1:
        return users[0]
    return None


def int_to_emoji(num: int) -> str:
    """Convert a one-digit number to an emoji.

    Args:
        num (int): Number (0-9)

    Returns:
        str: Emoji
    """
    emojis = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    return emojis[num]


def dynamic_timestamp(time: datetime, frmat: str = "f") -> str:  # TODO: Rewrite
    """Convert a timestamp to a dynamic Discord timestamp.

    Args:
        time (datetime): Timestamp to convert
        frmat (str, optional): Representation format. Defaults to "f".

    Returns:
        str: Timestamp string that Discord can represent dynamically
    """
    codes = {
        "short time": "t",
        "long time": "T",
        "short date": "d",
        "long date": "D",
        "date and time": "f",
        "date and time with weekday": "F",
        "relative": "R",
    }
    mod = codes[frmat] if frmat in codes else frmat if frmat in codes.values() else "f"
    return f"<t:{int(datetime.timestamp(time))}:{mod}>"


def int_to_month(num: int) -> str:
    """Convert an integer 1-12 to a month name.

    Args:
        num (int): Month number

    Returns:
        str: Month name
    """
    return datetime.strptime(str(num), "%m").strftime("%B")


def month_to_int(month: str) -> int:
    """Convert a month name to an integer 1-12.

    Args:
        month (str): Month name

    Returns:
        int: Month number
    """
    return datetime.strptime(month, "%B").month


def get_mentioned_ids(text: str) -> list[int]:
    """Get a list of all mentioned IDs.

    Args:
        text (str): Text to parse

    Returns:
        list[int]: List of IDs
    """
    raw_ids = re.findall(r"<\D*\d+>", text)
    return [int(re.sub(r"\D", "", id_)) for id_ in raw_ids]


async def get_mentioned_users(text: str) -> list[Member]:
    """Get a list of all mentioned users.

    Args:
        text (str): Text to scan
        guild (Guild): Guild to scan for users.

    Returns:
        list[Member]: List of mentioned users
    """
    ids = get_mentioned_ids(text)
    return [await standby.guild.fetch_member(id_) for id_ in ids]


def get_roles_by_type(type_: str) -> list[Role]:
    """Get all roles of.

    Args:
        type_ (str): _description_

    Returns:
        list[Role]: _description_
    """
    try:
        start, stop = [
            i
            for i in range(len(standby.guild.roles))
            if standby.guild.roles[i].name.lower() == type_.lower()
        ][0:2]
    except ValueError:
        return []
    roles = standby.guild.roles[start + 1 : stop]
    roles.sort(key=lambda role: role.name)
    return roles


def id_to_mention(
    id_: int,
    id_type: Literal["user", "channel", "role"] = "user",
) -> str:
    """Convert an ID to a mention string.

    Args:
        id_ (_type_): ID to convert
        id_type ({"user", "channel", "role"}, optional): ID Type.
            Defaults to "user".

    Returns:
        str: A Discord mention string
    """
    id_ = str(id_)

    if id_type == "user":
        return "<@" + id_ + ">"

    if id_type == "channel":
        return "<#" + id_ + ">"

    return "<@&" + id_ + ">"


def simpsons_error_image(
    dad: Member,
    son: Member,
    text: str | None = None,
    filename: str = "error.png",
) -> File:
    """Generate an 'error' image using the Simpsons template.

    Args:
        dad (Member): User to put in the dad's place
        son (Member): User to put in the son's place
        text (str, optional): Text to caption image with.
        filename (str, optional): Name of generated file.
            Defaults to "error.png".

    Returns:
        File: Discord File object containing the image
    """
    dad_url = dad.display_avatar.url
    son_url = son.display_avatar.url

    template_url = URL.GITHUB_STATIC + "/images/simpsons.png"

    template = Image.open(requests.get(template_url, stream=True).raw)

    dad = (
        Image.open(requests.get(dad_url, stream=True).raw)
        .convert("RGBA")
        .resize((300, 300))
    )
    son = (
        Image.open(requests.get(son_url, stream=True).raw)
        .convert("RGBA")
        .resize((225, 225))
    )
    son = son.rotate(-35, expand=True, fillcolor=(255, 255, 255, 0))

    template.paste(dad, (310, 30), dad)
    template.paste(son, (655, 344), son)

    if text:
        text = text.upper()

        draw = ImageDraw.Draw(template)

        font_path = URL.LOCAL_STATIC + "/fonts/impact.ttf"
        font = ImageFont.truetype(font=str(font_path), size=40)
        width, height = get_text_dimensions(text, font)

        if width <= 370:  # noqa: PLR2004
            x_coord = 565
            y_coord = 280

            draw.text((x_coord - 3, y_coord - 3), text, (0, 0, 0), font=font)
            draw.text((x_coord + 3, y_coord - 3), text, (0, 0, 0), font=font)
            draw.text((x_coord + 3, y_coord + 3), text, (0, 0, 0), font=font)
            draw.text((x_coord - 3, y_coord + 3), text, (0, 0, 0), font=font)
            draw.text((x_coord, y_coord), text, (255, 255, 255), font=font)
        else:
            rows = []
            num_rows = width // 280 + 1
            row_width = width / num_rows
            curr_string = ""
            for word in re.split(r"(\W+)", text):
                curr_string += word
                curr_width, _ = get_text_dimensions(curr_string, font)
                if curr_width >= row_width:
                    rows.append(curr_string)
                    curr_string = ""

            if curr_string:
                rows.append(curr_string)

            x_coord = 615
            y_coord = 280

            for row in reversed(rows):
                draw.text((x_coord - 3, y_coord - 3), row, (0, 0, 0), font=font)
                draw.text((x_coord + 3, y_coord - 3), row, (0, 0, 0), font=font)
                draw.text((x_coord + 3, y_coord + 3), row, (0, 0, 0), font=font)
                draw.text((x_coord - 3, y_coord + 3), row, (0, 0, 0), font=font)
                draw.text((x_coord, y_coord), row, (255, 255, 255), font=font)

                y_coord -= height + 5

    obj = io.BytesIO()
    template.save(obj, "png")
    obj.seek(0)
    return File(obj, filename=filename)


def get_text_dimensions(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """Get dimensions for the text in the provided font.

    Args:
        text (str): Text to measure
        font (ImageFont.FreeTypeFont): Text font

    Returns:
        tuple[int, int]: Width and height (in pixels)
    """
    ascent, descent = font.getmetrics()

    width = font.getmask(text).getbbox()[2]
    height = font.getmask(text).getbbox()[3] + descent

    return width, height


async def invoke_slash_command(
    name: str,
    interaction: Interaction,
    *args: tuple,
    **kwargs: dict,
) -> None:
    """Invoke named slash command.

    Args:
        name (str): Name of the command
        interaction (Interaction): Invoking interaction
        args (tuple): Extra arguments for the invoked command
        kwargs (dict): Extra keyword arguments for the invoked command
    """
    slash_command = next(
        command
        for command in standby.bot.get_all_application_commands()
        if command.name == name
    )
    await slash_command.invoke_callback(interaction, *args, **kwargs)


def utcnow() -> datetime:
    """Wrapper for the built-in utcnow function."""
    return nextcord.utils.utcnow()


def now() -> datetime:
    """Get the current timestamp in the bot's time zone."""
    return datetime.now(tz=BOT_TZ)


def role_priority(role: Role) -> str:
    """Get role priority.

    Used for sorting roles in the rules channel dropdown menus.
    Roles explicitly specified as priority roles show up first,
    followed by roles with have a provided description.

    Args:
        role (Role): Role

    Returns:
        str: The role's name with an appropriate prefix
    """
    if role.name in RoleName.prio_role_names():
        return "0" + role.name
    if role.name in RoleName.descriptions():
        return "1" + role.name
    return "2" + role.name


def message_embed(
    message: Message,
    command_type: Literal["move", "copy", "link"],
    trigger_author: Member,
) -> Embed:
    """Create an Embed showcasing the provided message.

    Additional data is added to the Embed based on context.

    Args:
        message (Message): Message to create Embed from
        command_type ({"move", "copy", "link"}): Creation context
        trigger_author (Member): _description_

    Returns:
        Embed: _description_
    """
    embed_titles = {
        "copy": "Copied message",
        "move": "Moved message",
        "link": "Message preview",
    }

    trigger_field_titles = {
        "move": "Moved by",
        "copy": "Copied by",
        "link": "Linked by",
    }

    embed = nextcord.Embed(color=Color.PALE_BLUE)
    embed.title = embed_titles[command_type]
    if message.author.display_avatar:
        embed.set_thumbnail(url=message.author.display_avatar.url)
    embed.description = message.content
    embed.add_field(name="Channel", value=message.channel.mention)
    timestamp = message.created_at + timedelta(hours=2)
    if (utcnow() - timestamp).days > 11 * 30:
        timestamp = timestamp.strftime("%b %d, %Y")
    else:
        timestamp = timestamp.strftime("%b %d, %H:%M")
    embed.add_field(name="Sent at", value=timestamp)
    embed.add_field(name=EMPTY_STRING, value=EMPTY_STRING)
    embed.add_field(name="Original poster", value=message.author.mention)

    embed.add_field(
        name=trigger_field_titles[command_type],
        value=trigger_author.mention,
    )

    if command_type in ["copy", "link"]:
        embed.add_field(
            name="Link to message",
            value=f"[Click here]({message.jump_url})",
        )

    if message.attachments:
        embed.set_image(url=message.attachments[0].url)
    else:
        link = re.search(r"(https:.*\.(jpe?g|png|gif))", message.content)
        if link:
            embed.set_image(url=link.group(1))

    return embed


def delayed_loop(
    *,
    seconds: float = MISSING,
    minutes: float = MISSING,
    hours: float = MISSING,
    time: time | Sequence[time] = MISSING,
    count: int | None = None,
    reconnect: bool = True,
    loop: asyncio.AbstractEventLoop = MISSING,
) -> Callable[[LF], Loop[LF]]:
    """Delayed version of the nextcord.ext.tasks.loop decorator.

    Nextcord loops start running before all bot functionality has been
    initialized, leading to unexpected behavior. This wrapper delays the
    beginning of the loops until the bot is ready.
    """

    def decorator(func: LF) -> Loop[LF]:
        inner_loop = Loop[LF](
            func,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            time=time,
            count=count,
            reconnect=reconnect,
            loop=loop,
        )

        @inner_loop.before_loop
        async def impr(self: Cog) -> None:
            await self.standby.bot.wait_until_ready()

        return inner_loop

    return decorator


async def get_user_predictions(user: Member) -> dict[str, str]:
    """Fetch all predictions made by a user from the database.

    Args:
        user (Member): Target user

    Returns:
        dict: Prediction labels and their full texts
    """
    query = f"SELECT predictions FROM usr WHERE usr_id = {user.id}"
    recs = await standby.pg_pool.fetch(query)
    predictions = recs[0]["predictions"]
    return json.loads(predictions) if predictions else {}


async def update_user_predictions(user: Member, predictions: dict[str, str]) -> None:
    """Sets a user's predictions in the database to the provided values.

    Args:
        user (Member): _description_
        predictions (dict[str, str]): _description_
    """
    sql_string = json.dumps(predictions).replace("'", "''")
    query = f"UPDATE usr SET predictions = '{sql_string}' WHERE usr_id = {user.id}"
    await Standby().pg_pool.execute(query)


def ordinal_suffix(n: int) -> Literal["st", "nd", "rd", "th"]:
    """Generate the suffix for an ordinal number.

    Args:
        n (int): Number

    Returns:
        str: The number's suffix
    """
    if (n % 100) in [11, 12, 13]:
        return "th"
    return ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]


def titlecase(s: str) -> str:
    """Modified version of the str.title() method.

    Does not capitalize letters following apostrophes.

    Args:
        s (str): String

    Returns:
        str: Titlecased version of the string
    """
    as_list = list(s.replace("'", "x").title())
    for index, char in enumerate(s):
        if char == "'":
            as_list[index] = "'"
    return "".join(as_list)
