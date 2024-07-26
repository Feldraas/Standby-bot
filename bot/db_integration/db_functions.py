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
