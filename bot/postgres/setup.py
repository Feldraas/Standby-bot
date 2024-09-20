"""PostgreSQL database interactions."""

from asyncpg import create_pool

from domain import URL, Standby
from postgres.architecture import setup_database
from utils import util_functions as uf

bot_start_time = uf.now()
standby = Standby()


async def init_connection() -> None:
    """Initialize the connection and store a reference to it."""
    standby.pg_pool = await create_pool(URL.DATABASE, ssl="prefer")

    async with standby.pg_pool.acquire() as con:
        await setup_database(con)
