import json
from datetime import datetime as dt

import asyncpg

from db_integration.create_scripts import create_tables
from domain import URL, Standby

bot_start_time = dt.now()

standby = Standby()


async def init_connection():
    standby.pg_pool = await asyncpg.create_pool(URL.DATABASE, ssl="prefer")
    async with standby.pg_pool.acquire() as con:
        await create_tables(con)


async def ensure_guild_existence(gid):
    guild = await standby.pg_pool.fetch(
        "SELECT * FROM guild WHERE guild.guild_id = $1;", gid
    )

    if not guild:
        await standby.pg_pool.execute("INSERT INTO guild (guild_id) VALUES ($1);", gid)


async def get_or_insert_usr(uid, gid):
    usr = await standby.pg_pool.fetch(
        "SELECT * FROM usr WHERE usr_id = $1 AND guild_id = $2;", uid, gid
    )

    if not usr:
        await standby.pg_pool.execute(
            "INSERT INTO usr (usr_id, guild_id) VALUES ($1, $2);",
            uid,
            gid,
        )

    return usr


async def ensured_get_usr(uid, gid):
    return await get_or_insert_usr(uid, gid) or await get_or_insert_usr(uid, gid)


async def get_note(key):
    notes = await standby.pg_pool.fetch(f"SELECT * FROM notes WHERE key = '{key}'")
    return notes[0]["value"] if notes else ""


async def log_or_update_note(key, value):
    note = await get_note(key)
    if note:
        await standby.pg_pool.execute(
            f"UPDATE notes SET value = '{value}' where key = '{key}'"
        )
    else:
        await standby.pg_pool.execute(
            f"INSERT INTO notes (key,  value) VALUES ('{key}', '{value}')"
        )


async def log_buttons(view, channel_id, message_id, params=None):
    view_type = view.__class__.__module__ + " " + view.__class__.__name__
    await standby.pg_pool.execute(
        "INSERT INTO buttons (type, channel_id, message_id, params) "
        "VALUES ($1, $2, $3, $4);",
        view_type,
        channel_id,
        message_id,
        json.dumps(params).replace("'", "''") if params else None,
    )


async def update_button_params(message_id, new_params):
    records = await standby.pg_pool.fetch(
        f"SELECT params FROM buttons WHERE message_id = {message_id}"
    )
    params = records[0]["params"]
    params = json.loads(params)
    params.update(new_params)
    params = json.dumps(params).replace("'", "''") if params else "{}"
    await standby.pg_pool.execute(
        f"UPDATE buttons SET params = '{params}' WHERE message_id = '{message_id}'"
    )
