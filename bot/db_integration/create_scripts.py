"""SQL queries for creating all necessary tables."""

import logging

from asyncpg import Pool

logger = logging.getLogger(__name__)

CREATE_USER = """
CREATE TABLE IF NOT EXISTS "usr" (
    "usr_id" BIGINT NOT NULL,
    "thanks" integer NOT NULL DEFAULT '0',
    "guild_id" BIGINT NOT NULL,
    CONSTRAINT "usr_pk" PRIMARY KEY ("usr_id")
) WITH (
  OIDS=FALSE
);
"""

CREATE_STARBOARD = """CREATE TABLE IF NOT EXISTS "starboard" (
    "msg_id" BIGINT NOT NULL,
    "sb_id" BIGINT NOT NULL,
    "usr_id" BIGINT NOT NULL,
    "stars" integer NOT NULL DEFAULT '0',
    CONSTRAINT "starboard_pk" PRIMARY KEY ("msg_id")
) WITH (
  OIDS=FALSE
);
"""

CREATE_GUILD = """
CREATE TABLE IF NOT EXISTS "guild" (
    "guild_id" BIGINT NOT NULL,
    CONSTRAINT "guild_pk" PRIMARY KEY ("guild_id")
) WITH (
  OIDS=FALSE
);
"""

ALTER_USER = """
DO $$
BEGIN
IF NOT EXISTS (
    SELECT * FROM information_schema.constraint_column_usage
    WHERE table_name = 'guild' AND constraint_name = 'usr_fk0'
) THEN
ALTER TABLE "usr"
ADD CONSTRAINT "usr_fk0" FOREIGN KEY ("guild_id") REFERENCES "guild"("guild_id");
END IF;
END;
$$;
"""

ALTER_USER_ADD_SKULLS = 'ALTER TABLE "usr" ADD IF NOT EXISTS "skulls" integer DEFAULT 0'

ALTER_USER_ADD_ROULETTE = """
ALTER TABLE "usr" ADD IF NOT EXISTS "current_roulette_streak" integer DEFAULT 0;
ALTER TABLE "usr" ADD IF NOT EXISTS "max_roulette_streak" integer DEFAULT 0;
"""

ALTER_USER_ADD_BURGERS = (
    'ALTER TABLE "usr" ADD IF NOT EXISTS "burgers" integer DEFAULT 0'
)
ALTER_USER_ADD_MOLDY_BURGERS = (
    'ALTER TABLE "usr" ADD IF NOT EXISTS "moldy_burgers" integer DEFAULT 0'
)

ALTER_USER_ADD_PREDICTIONS = """
ALTER TABLE "usr" ADD IF NOT EXISTS "predictions" TEXT;
ALTER TABLE "usr" ADD IF NOT EXISTS "orbs" integer DEFAULT 0;
"""

ALTER_STARBOARD = """
DO $$
BEGIN
IF NOT EXISTS (
    SELECT * FROM information_schema.constraint_column_usage
    WHERE table_name = 'usr' AND constraint_name = 'starboard_fk0'
) THEN
ALTER TABLE "starboard"
ADD CONSTRAINT "starboard_fk0" FOREIGN KEY ("usr_id") REFERENCES "usr"("usr_id");
END IF;
END;
$$;
"""

CREATE_TMERS = """
CREATE TABLE IF NOT EXISTS "tmers" (
    "tmer_id" SERIAL PRIMARY KEY,
    "usr_id" BIGINT NOT NULL,
    "expires" TIMESTAMP NOT NULL,
    "ttype" BIGINT NOT NULL,
    "params" TEXT
) WITH (
  OIDS=FALSE
);
"""

ALTER_TMERS = """
DO $$
BEGIN
IF NOT EXISTS (
    SELECT * FROM information_schema.constraint_column_usage
    WHERE table_name = 'usr' AND constraint_name = 'tmers_fk0'
) THEN
ALTER TABLE "tmers"
ADD CONSTRAINT "tmers_fk0" FOREIGN KEY ("usr_id") REFERENCES "usr"("usr_id");
END IF;
END;
$$;
"""

ALTER_GUILD_ADD_PERMS = """
ALTER TABLE "guild" ADD IF NOT EXISTS "config" TEXT;
"""

CREATE_BDAYS = """
CREATE TABLE IF NOT EXISTS "bdays" (
    "usr_id" BIGINT NOT NULL,
    "month" SMALLINT NOT NULL,
    "day" SMALLINT NOT NULL,
    CONSTRAINT "bdays_pk" PRIMARY KEY ("usr_id")
) WITH (
  OIDS=FALSE
);
"""

ALTER_BDAYS = """
DO $$
BEGIN
IF NOT EXISTS (
    SELECT * FROM information_schema.constraint_column_usage
    WHERE table_name = 'usr' AND constraint_name = 'bdays_fk0'
) THEN
ALTER TABLE "bdays"
ADD CONSTRAINT "bdays_fk0" FOREIGN KEY ("usr_id") REFERENCES "usr"("usr_id");
END IF;
END;
$$;
"""

CREATE_BUTTONS = """
CREATE TABLE IF NOT EXISTS "buttons" (
    "type" TEXT,
    "channel_id" BIGINT NOT NULL,
    "message_id" BIGINT NOT NULL,
    "params" TEXT
) WITH (
    OIDS=FALSE
);
"""

CREATE_NOTES = """
CREATE TABLE IF NOT EXISTS "notes" (
    "key" TEXT,
    "value" TEXT
) WITH (
    OIDS=FALSE
);
"""

CREATE_LOGS = """
CREATE TABLE IF NOT EXISTS "logs" (
    "timestamp" TIMESTAMP,
    "module" TEXT,
    "function" TEXT,
    "message" TEXT
) WITH (
    OIDS=FALSE
);
"""

CREATE_MOVIES = """
CREATE TABLE IF NOT EXISTS "movies" (
    "usr_id" BIGINT NOT NULL,
    "title" TEXT NOT NULL,
    "rating" INTEGER NOT NULL,
    "review" TEXT
) WITH (
    OIDS=FALSE
);
"""

ALTER_USER_ADD_YOINK = 'ALTER TABLE "usr" ADD IF NOT EXISTS "last_yoink" timestamp'


async def create_tables(con: Pool) -> None:  # noqa: PLR0915
    """Create all tables.

    Args:
        con (Pool): asyncpg connection pool
    """
    no_errors = True
    try:
        await con.execute(CREATE_USER)
        await con.execute(CREATE_STARBOARD)
        await con.execute(CREATE_GUILD)
        await con.execute(ALTER_USER_ADD_SKULLS)
        await con.execute(ALTER_USER_ADD_ROULETTE)
        await con.execute(ALTER_USER_ADD_BURGERS)
        await con.execute(ALTER_USER_ADD_MOLDY_BURGERS)
        await con.execute(ALTER_USER)
        await con.execute(ALTER_STARBOARD)
        await con.execute(ALTER_USER_ADD_PREDICTIONS)
        await con.execute(ALTER_USER_ADD_YOINK)
    except Exception:
        logger.exception("Error when executing db script batch 1")
        no_errors = False

    try:
        await con.execute(CREATE_TMERS)
        await con.execute(ALTER_TMERS)
    except Exception:
        logger.exception("Error when executing db script batch 2")
        no_errors = False
    try:
        await con.execute(CREATE_BDAYS)
        await con.execute(ALTER_BDAYS)
    except Exception:
        logger.exception("Error when executing db script batch 3")
        no_errors = False
    try:
        await con.execute(CREATE_BUTTONS)
    except Exception:
        logger.exception("Error when executing db script batch 4")
        no_errors = False
    try:
        await con.execute(CREATE_NOTES)
    except Exception:
        logger.exception("Error when executing db script batch 5")
        no_errors = False
    try:
        await con.execute(CREATE_LOGS)
    except Exception:
        logger.exception("Error when executing db script batch 6")
        no_errors = False
    try:
        await con.execute(CREATE_MOVIES)
    except Exception:
        logger.exception("Error when executing db script batch 7")
        no_errors = False

    if no_errors:
        logger.info("All db scripts executed successfully!")
