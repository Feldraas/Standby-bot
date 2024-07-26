"""PostgreSQL database interactions."""

import json

from asyncpg import Record, create_pool
from nextcord.ui import View

from db_integration.create_scripts import create_tables
from domain import URL, Standby
from postgres.architecture import setup_database
from utils import util_functions as uf

bot_start_time = uf.now()
standby = Standby()


async def init_connection() -> None:
    """Initialize the connection and store a reference to it."""
    standby.pg_pool = await create_pool(URL.DATABASE, ssl="prefer")

    async with standby.pg_pool.acquire() as con:
        await create_tables(con)
        await setup_database(con)


async def ensure_guild_existence(guild_id: int) -> None:
    """Insert a guild ID into the guild table (if not already there).

    Args:
        guild_id (int): Guild ID
    """
    guild = await standby.pg_pool.fetch(
        "SELECT * FROM guild WHERE guild.guild_id = $1;",
        guild_id,
    )

    if not guild:
        await standby.pg_pool.execute(
            "INSERT INTO guild (guild_id) VALUES ($1);",
            guild_id,
        )


async def get_or_insert_usr(user_id: int) -> Record | None:
    """Get user data from the usr table. Can return None.

    Args:
        user_id (int): User ID

    Returns:
        Record | None: User's row in the usr table (if present)
    """
    usr = await standby.pg_pool.fetch(
        "SELECT * FROM usr WHERE usr_id = $1 AND guild_id = $2;",
        user_id,
        standby.guild.id,
    )

    if not usr:
        await standby.pg_pool.execute(
            "INSERT INTO usr (usr_id, guild_id) VALUES ($1, $2);",
            user_id,
            standby.guild.id,
        )
        return None

    return usr[0]


async def ensured_get_usr(user_id: int) -> Record:
    """Get user data from the usr table. Always returns a Record.

    Args:
        user_id (int): User ID

    Returns:
        Record: User's row in the usr table
    """
    return await get_or_insert_usr(user_id) or await get_or_insert_usr(user_id)


async def get_note(key: str) -> str | None:
    """Gets the text of the note with the provided key.

    Args:
        key (str): Note key

    Returns:
        str | None: Note text
    """
    notes = await standby.pg_pool.fetch(f"SELECT * FROM notes WHERE key = '{key}'")
    return notes[0]["value"] if notes else None


async def log_or_update_note(key: str, value: str) -> None:
    """Log a note to the database. If the key exists, replace it.

    Args:
        key (str): Note key
        value (str): Note text
    """
    note = await get_note(key)
    if note:
        await standby.pg_pool.execute(
            f"UPDATE notes SET value = '{value}' where key = '{key}'",
        )
    else:
        await standby.pg_pool.execute(
            f"INSERT INTO notes (key,  value) VALUES ('{key}', '{value}')",
        )


async def log_buttons(
    view: View,
    channel_id: int,
    message_id: int,
    params: dict | None = None,
) -> None:
    """Log button data in the database so that they may be reconnected.

    Args:
        view (View): View object containing the buttons
        channel_id (int): ID of the channel
        message_id (int): ID of the message
        params (dict | None, optional): Extra arguments to pass to
            the View constructor. Defaults to None.
    """
    view_type = view.__class__.__module__ + " " + view.__class__.__name__
    await standby.pg_pool.execute(
        "INSERT INTO buttons (type, channel_id, message_id, params) "
        "VALUES ($1, $2, $3, $4);",
        view_type,
        channel_id,
        message_id,
        json.dumps(params).replace("'", "''") if params else None,
    )


async def update_button_params(message_id: int, new_params: dict) -> None:
    """Update params for a logged button.

    Args:
        message_id (int): ID of the message
        new_params (dict): New param values
    """
    records = await standby.pg_pool.fetch(
        f"SELECT params FROM buttons WHERE message_id = {message_id}",
    )
    params = records[0]["params"]
    params: dict = json.loads(params)
    params.update(new_params)
    params = json.dumps(params).replace("'", "''") if params else "{}"
    await standby.pg_pool.execute(
        f"UPDATE buttons SET params = '{params}' WHERE message_id = '{message_id}'",
    )
