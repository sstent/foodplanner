from logging.config import fileConfig
import logging
import os
import sys
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the project root to the Python path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Use environment variable if available, otherwise fall back to config
    url = os.getenv('DATABASE_URL', config.get_main_option("sqlalchemy.url"))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    logging.info("DEBUG: Creating database engine for alembic")
    # Use environment variable for database URL if available
    db_url = os.getenv('DATABASE_URL', config.get_main_option("sqlalchemy.url"))
    connectable = engine_from_config(
        {'sqlalchemy.url': db_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    logging.info("DEBUG: Database engine created successfully")

    with connectable.connect() as connection:
        logging.info("DEBUG: Database connection established for alembic")
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        logging.info("DEBUG: Alembic context configured")

        with context.begin_transaction():
            logging.info("DEBUG: Starting alembic transaction")
            context.run_migrations()
            logging.info("DEBUG: Alembic migrations completed within transaction")


if context.is_offline_mode():
    logging.info("DEBUG: Running migrations in offline mode")
    run_migrations_offline()
else:
    logging.info("DEBUG: Running migrations in online mode")
    run_migrations_online()
    logging.info("DEBUG: Online migrations completed")
