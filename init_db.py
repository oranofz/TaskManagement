"""Database initialization script.

This script creates all database tables based on SQLAlchemy models.
Run this script once before starting the application for the first time.

Usage:
    python init_db.py
"""
import asyncio
import sys
from loguru import logger
from sqlalchemy import text
from app.shared.database import engine, Base
from app.config import settings

# Import all models to ensure they're registered with Base
from app.auth.domain.models import User, RefreshToken
from app.task.domain.models import Task, Comment, AuditLogEntry
from app.tenant.domain.models import Tenant, Department, Team, Project


async def init_database() -> None:
    """Initialize database by creating all tables."""
    logger.info("Starting database initialization...")
    logger.info(f"Database URL: {settings.database_url}")

    try:
        # Test database connection
        logger.info("Testing database connection...")
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection successful")

        # Create all tables
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ All tables created successfully")

        # Verify tables were created
        logger.info("Verifying tables...")
        async with engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            ))
            tables = [row[0] for row in result]

        logger.info(f"✓ Found {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table}")

        logger.info("✓ Database initialization completed successfully!")
        return True

    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        return False
    finally:
        await engine.dispose()


async def drop_all_tables() -> None:
    """Drop all tables. Use with caution!"""
    logger.warning("⚠ Dropping all database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("✓ All tables dropped successfully")
    except Exception as e:
        logger.error(f"✗ Failed to drop tables: {e}")
    finally:
        await engine.dispose()


async def reset_database() -> None:
    """Drop and recreate all tables. Use with caution!"""
    logger.warning("⚠ Resetting database (drop and recreate)...")
    await drop_all_tables()
    await init_database()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "drop":
            logger.warning("⚠ You are about to DROP all database tables!")
            response = input("Type 'yes' to confirm: ")
            if response.lower() == 'yes':
                asyncio.run(drop_all_tables())
            else:
                logger.info("Operation cancelled")
        elif command == "reset":
            logger.warning("⚠ You are about to RESET the database (drop and recreate all tables)!")
            response = input("Type 'yes' to confirm: ")
            if response.lower() == 'yes':
                asyncio.run(reset_database())
            else:
                logger.info("Operation cancelled")
        else:
            logger.error(f"Unknown command: {command}")
            logger.info("Available commands: drop, reset")
            sys.exit(1)
    else:
        # Default: just create tables
        success = asyncio.run(init_database())
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

