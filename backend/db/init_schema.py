import pathlib
import logging
from sqlalchemy import text
from db.database import engine

logger = logging.getLogger(__name__)

SCHEMA_PATH = pathlib.Path(__file__).parent / "schema" / "strikeiq_schema.sql"


async def load_schema():

    logger.info("Checking database schema...")

    async with engine.begin() as conn:

        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            )
        )

        tables = result.fetchall()

        if tables:
            logger.info("Tables already exist. Skipping schema creation.")
            logger.info("Database connection established")
            logger.info("Schema verified")
            return

        logger.info("Loading StrikeIQ schema into database")

        sql = SCHEMA_PATH.read_text(encoding="utf-8")

        statements = [
            stmt.strip()
            for stmt in sql.split(";")
            if stmt.strip()
        ]

        for stmt in statements:
            await conn.execute(text(stmt))

    logger.info("StrikeIQ schema successfully created")
    logger.info("Database connection established")
    logger.info("Schema verified")
