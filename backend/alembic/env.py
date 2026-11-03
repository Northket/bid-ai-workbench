"""Alembic 环境：目标库由 database.py 决定（尊重 BID_DB_PATH / BID_TEST_MODE）。"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 保证可以 import 项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import DB_PATH  # noqa: E402
from models import Base  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 以 database.py 计算出的实际路径为准（Windows 反斜杠转 URL）
config.set_main_option("sqlalchemy.url", f"sqlite:///{DB_PATH.as_posix()}")

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite 修改表结构需要
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
