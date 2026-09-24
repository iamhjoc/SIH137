import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.base import Base

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Exclude PostGIS tiger_geocoder / topology extension tables from
    autogenerate diffs — they live in the DB but aren't declared in our
    SQLAlchemy models, so without this filter Alembic tries to drop them."""
    if type_ == "table":
        if getattr(object, "schema", None) == "tiger":
            return False
        if name in (
            "topology",
            "layer",
            "spatial_ref_sys",
            "loader_platform",
            "loader_variables",
            "loader_lookuptables",
            "geocode_settings",
            "geocode_settings_default",
            "pagc_gaz",
            "pagc_lex",
            "pagc_rules",
            "addr",
            "addrfeat",
            "edges",
            "faces",
            "featnames",
            "county",
            "county_lookup",
            "countysub_lookup",
            "cousub",
            "direction_lookup",
            "place",
            "place_lookup",
            "secondary_unit_lookup",
            "state",
            "state_lookup",
            "street_type_lookup",
            "bg",
            "tract",
            "tabblock",
            "tabblock20",
            "zcta5",
            "zip_lookup",
            "zip_lookup_all",
            "zip_lookup_base",
            "zip_state",
            "zip_state_loc",
        ):
            return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url, target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())