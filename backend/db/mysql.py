import mysql.connector
from mysql.connector import pooling

from backend.config import settings

_pool: pooling.MySQLConnectionPool | None = None


def get_pool() -> pooling.MySQLConnectionPool:
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="app_pool",
            pool_size=10,
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset='utf8mb4',
            use_unicode=True,
        )
    return _pool


def get_connection() -> mysql.connector.MySQLConnection:
    return get_pool().get_connection()
