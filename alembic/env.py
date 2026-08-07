"""Cấu hình môi trường Alembic.

URL database lấy từ src.config (đọc .env), KHÔNG hardcode trong alembic.ini —
để không có mật khẩu nào bị commit vào git.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from src.config import get_settings

# Import qua src.db để Base.metadata thấy đủ 48 bảng.
from src.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Sinh SQL ra stdout mà không cần kết nối (alembic upgrade head --sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
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
            # Bắt cả thay đổi kiểu cột và server_default, nếu không autogenerate
            # sẽ bỏ sót khi ta sửa NUMERIC(12,2) hay đổi giá trị mặc định.
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
