"""PostgreSQL database architecture."""

import logging
import os

from asyncpg import Pool

from domain import Standby

logger = logging.getLogger(__name__)

STRUCTURE = {
    "birthday": {
        "columns": {
            "user_id": "BIGINT PRIMARY KEY",
            "birth_date": "DATE",
        },
    },
    "view": {
        "columns": {
            "channel_id": "BIGINT",
            "message_id": "BIGINT PRIMARY KEY",
            "module": "TEXT",
            "class": "TEXT",
            "params": "JSON",
        },
    },
    "movie": {
        "columns": {
            "user_id": "BIGINT",
            "title": "TEXT",
            "rating": "INTEGER",
            "review": "TEXT",
        },
        "constraints": {
            "movie_pkey": "PRIMARY KEY (user_id, title)",
        },
    },
    "starboard": {
        "columns": {
            "message_id": "BIGINT PRIMARY KEY",
            "starboard_id": "BIGINT",
            "stars": "INTEGER",
        },
    },
    "burger": {
        "columns": {
            "giver_id": "BIGINT",
            "recipient_id": "BIGINT",
            "transferred_at": "TIMESTAMPTZ",
            "reason": "TEXT",
        },
    },
    "reminder": {
        "columns": {
            "reminder_id": "SERIAL PRIMARY KEY",
            "user_id": "BIGINT",
            "created_at": "TIMESTAMPTZ",
            "expires_at": "TIMESTAMPTZ",
            "message": "TEXT",
            "channel_id": "BIGINT",
            "message_id": "BIGINT",
            "send_dm": "BOOLEAN",
        },
    },
    "prediction": {
        "columns": {
            "user_id": "BIGINT",
            "predicted_at": "TIMESTAMPTZ",
            "label": "TEXT",
            "text": "TEXT",
            "status": "TEXT",
        },
        "constraints": {
            "prediction_pk": "PRIMARY KEY (user_id, label)",
        },
    },
    "roulette": {
        "columns": {
            "user_id": "BIGINT",
            "played_at": "TIMESTAMPTZ",
            "win": "BOOLEAN",
        },
    },
    "awards": {
        "columns": {
            "user_id": "BIGINT PRIMARY KEY",
            "thanks": "INTEGER",
            "skulls": "INTEGER",
        },
    },
    "repost": {
        "columns": {
            "user_id": "BIGINT",
            "expires_at": "TIMESTAMPTZ",
        },
    },
}


async def setup_database(con: Pool) -> None:
    """Parse and setup database structure.

    Args:
        con (Pool): PostgreSQL connection
    """
    schema = os.getenv("DB_SCHEMA", "dev")
    Standby().schema = schema

    await con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    for table, table_spec in STRUCTURE.items():
        bad_keys = [key for key in table_spec if key not in ["columns", "constraints"]]
        if any(bad_keys):
            msg = f"Unrecognized keys {bad_keys} in specification for table {table}"
            raise ValueError(msg)

        await con.execute(f"CREATE TABLE IF NOT EXISTS {schema}.{table} ()")

        columns = table_spec.get("columns", {})
        for column_name, column_spec in columns.items():
            await con.execute(f"""
                ALTER TABLE {schema}.{table}
                ADD IF NOT EXISTS {column_name} {column_spec}
                """)

        constraints = table_spec.get("constraints", {})
        for constraint_name, constraint_spec in constraints.items():
            await con.execute(f"""
                ALTER TABLE {schema}.{table}
                DROP CONSTRAINT IF EXISTS {constraint_name}
                """)
            await con.execute(f"""
                ALTER TABLE {schema}.{table}
                ADD CONSTRAINT {constraint_name} {constraint_spec}
                """)

    logger.info("Database creation complete")
