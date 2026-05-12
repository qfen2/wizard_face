# coding: utf-8

"""
一个全新的数据库工具模块。

设计目标：
- 封装基于配置（如 config.DATABASES 或 conf/auto.yaml["databases"]）的连接创建逻辑
- 对外提供简洁的获取数据库实例的接口，而不是到处手工 new Database
- 支持 mysql / sqlite，两种引擎的创建方式与原来的 DbCfg 基本保持一致
- 默认使用 peewee3 及以上版本的连接池实现
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import peewee
from playhouse import pool # type: ignore[import]
from playhouse.sqlite_ext import SqliteExtDatabase # type: ignore[import]

try:
    # 优先使用项目内的配置
    from config import DATABASES as DEFAULT_DATABASES  # type: ignore
except Exception:  # pragma: no cover - 兜底处理
    DEFAULT_DATABASES: Dict[str, Dict[str, Any]] = {}

logger = logging.getLogger(__name__)


class DbCfg(object):
    """
    单个数据库配置的封装。

    参考了原始的 DbCfg，但对外只暴露最常用的字段。
    """

    def __init__(self, name: str, all_cfg: Dict[str, Dict[str, Any]]):
        super(DbCfg, self).__init__()
        db_cfg = all_cfg[name]

        self.name = name
        self.engine: str = db_cfg["engine"]
        self.database: str = db_cfg["database"]

        # 连接池和基础参数
        params: Dict[str, Any] = {}
        if self.engine == "mysql":
            # 默认值大体与原 DbCfg 保持一致
            params.update(
                stale_timeout=60 * 60,
                timeout=10,
                autorollback=True,
            )
            params.update(db_cfg.get("pool", {}))

        params.update(db_cfg.get("params", {}))
        self.params = params

        # 是否注册 request 结束自动关闭（主要面向 Flask 之类的 Web 框架）
        self.register_db_close: Optional[bool] = db_cfg.get(
            "register_db_close", None
        )

    def _create_db(self, enable_pool_proxy: bool = False) -> peewee.Database:
        """
        真正创建 peewee.Database 实例的地方。
        """
        if self.engine == "mysql":
            # peewee3 及以上的连接池实现
            db_cls: Any = pool.PooledMySQLDatabase
            db = db_cls(self.database, **self.params)
            if self.register_db_close is None:
                self.register_db_close = True
        elif self.engine == "sqlite":
            params = self.params.copy()
            ext = bool(params.pop("ext", None))
            db_cls = SqliteExtDatabase if ext else peewee.SqliteDatabase
            db = db_cls(self.database, **params)
            if self.register_db_close is None:
                self.register_db_close = False
        else:
            raise Exception('Unknown engine "%s"' % self.engine)

        return db

    def init_db(
        self, app: Optional[Any] = None, enable_pool_proxy: bool = False
    ) -> peewee.Database:
        """
        创建数据库实例，并在需要时为 Web 框架注册自动关闭钩子。
        """
        db = self._create_db(enable_pool_proxy=enable_pool_proxy)

        if app is not None and self.register_db_close:
            # 与原 DbCfg.init_db 的 Flask 集成方式保持一致
            @app.teardown_request
            def _db_close(_):  # type: ignore
                if not db.is_closed():
                    db.close()

        return db


class DatabaseManager(object):
    """
    管理多个命名数据库连接的高层工具。

    一般用法：

        from app.utils.db_tool import db_manager

        db = db_manager.get('zj3')
        class MyModel(peewee.Model):
            class Meta:
                database = db
    """

    def __init__(self, db_cfgs: Optional[Dict[str, Dict[str, Any]]] = None):
        db_cfgs = db_cfgs or DEFAULT_DATABASES
        self._cfgs: Dict[str, DbCfg] = {
            name: DbCfg(name, db_cfgs) for name in db_cfgs
        }
        self._db_instances: Dict[str, peewee.Database] = {}

    def get(
        self,
        name: str,
        app: Optional[Any] = None,
        enable_pool_proxy: bool = False,
    ) -> peewee.Database:
        """
        获取（或创建并缓存）指定名称的数据库。
        """
        if name not in self._cfgs:
            raise KeyError('Unknown database config name "%s"' % name)

        db = self._db_instances.get(name)
        if db is None or db.is_closed():
            logger.debug("init database %s", name)
            cfg = self._cfgs[name]
            db = cfg.init_db(app=app, enable_pool_proxy=enable_pool_proxy)
            self._db_instances[name] = db

        return db

    def close(self, name: Optional[str] = None) -> None:
        """
        关闭指定数据库，或在 name 为空时关闭全部已经创建的数据库。
        """
        if name is None:
            for n, db in list(self._db_instances.items()):
                if not db.is_closed():
                    db.close()
                self._db_instances.pop(n, None)
            return

        db = self._db_instances.get(name)
        if db and not db.is_closed():
            db.close()
        self._db_instances.pop(name, None)

    def ping(self, name: str) -> bool:
        """
        尝试对指定数据库执行一次 ping，用于健康检查。
        """
        db = self.get(name)
        try:
            # 大多数 MySQL 驱动都支持底层 conn.ping()
            conn = db.get_conn()
            if hasattr(conn, "ping"):
                conn.ping(reconnect=True)  # type: ignore[arg-type]
            else:
                # 对不支持 ping 的情况做一次无害查询
                db.execute_sql("SELECT 1")
        except Exception as exc:  # pragma: no cover - 主要用于运行时诊断
            logger.warning("ping database %s failed: %s", name, exc)
            return False
        return True


# 默认导出的全局实例，方便简单项目直接使用
db_manager = DatabaseManager()


__all__ = [
    "DbCfg",
    "DatabaseManager",
    "db_manager",
]


