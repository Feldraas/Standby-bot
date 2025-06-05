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
    "rating": {
        "columns": {
            "user_id": "BIGINT",
            "category": "TEXT",
            "title": "TEXT",
            "score": "INTEGER",
            "review": "TEXT",
        },
        "constraints": {
            "rating_pkey": "PRIMARY KEY (user_id, category, title)",
        },
    },
    "starboard": {
        "columns": {
            "user_id": "BIGINT",
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
            "prediction_pkey": "PRIMARY KEY (user_id, label)",
        },
    },
    "roulette": {
        "columns": {
            "user_id": "BIGINT",
            "played_at": "TIMESTAMPTZ",
            "win": "BOOLEAN",
        },
    },
    "simple_award": {
        "columns": {
            "user_id": "BIGINT PRIMARY KEY",
            "thanks": "INTEGER DEFAULT 0",
            "skulls": "INTEGER DEFAULT 0",
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

    await con.execute(f"""
        CREATE OR REPLACE VIEW {schema}.award AS
        SELECT
            COALESCE(
                sa.user_id,
                brg.recipient_id,
                mbrg.giver_id,
                prd.user_id,
                sb.user_id
            ) AS user_id,
            thanks,
            skulls,
            burgers,
            moldy_burgers,
            orbs,
            stars
        FROM
            {schema}.simple_award AS sa
            FULL OUTER JOIN (
                SELECT
                    recipient_id,
                    COUNT(*) AS burgers
                FROM
                    {schema}.burger
                WHERE
                    reason != 'mold'
                GROUP BY
                    recipient_id
            ) AS brg ON brg.recipient_id = sa.user_id
            FULL OUTER JOIN (
                SELECT
                    giver_id,
                    COUNT(*) AS moldy_burgers
                FROM
                    {schema}.burger
                WHERE
                    reason = 'mold'
                GROUP BY
                    giver_id
            ) AS mbrg ON mbrg.giver_id = sa.user_id
            FULL OUTER JOIN (
                SELECT
                    user_id,
                    COUNT(*) AS orbs
                FROM
                    {schema}.prediction
                WHERE
                    status = 'Confirmed'
                GROUP BY
                    user_id
            ) AS prd ON prd.user_id = sa.user_id
            FULL OUTER JOIN (
                SELECT
                    user_id,
                    SUM(stars) AS stars
                FROM
                    {schema}.starboard
                GROUP BY
                    user_id
            ) AS sb ON sb.user_id = sa.user_id
        """)

    logger.info("Database creation complete")
