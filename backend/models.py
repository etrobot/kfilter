from __future__ import annotations

from datetime import date as dt_date, datetime as dt_datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, create_engine, Session
import pandas as pd
import secrets
import string
import os
from pathlib import Path


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float  # 0.0 to 1.0
    message: str
    created_at: str
    completed_at: Optional[str] = None
    top_n: int
    selected_factors: Optional[List[str]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RunRequest(BaseModel):
    top_n: int = 100
    selected_factors: Optional[List[str]] = None
    collect_latest_data: bool = True

class RunResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str


class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float
    message: str
    created_at: str
    completed_at: Optional[str]
    top_n: int
    selected_factors: Optional[List[str]] = None
    data: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = None
    error: Optional[str] = None


class Message(BaseModel):
    message: str


class AuthRequest(BaseModel):
    name: str
    email: str


class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str
    user: Optional[dict] = None


# 数据库模型

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: str = Field(default_factory=lambda: ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8)), primary_key=True)
    name: Optional[str] = None
    email: str
    image: Optional[str] = None
    is_admin: bool = Field(default=False, description="是否为管理员")
    created_at: dt_datetime = Field(default_factory=lambda: dt_datetime.now(timezone.utc))


class StockBasicInfo(SQLModel, table=True):
    """股票基本信息表"""
    __tablename__ = "stock_basic_info"
    
    code: str = Field(primary_key=True, description="股票代码")
    name: str = Field(description="股票名称")
    description: Optional[str] = Field(default=None, description="股票简介")
    tags: Optional[str] = Field(default=None, description="标签，用逗号分隔")
    created_at: dt_datetime = Field(default_factory=dt_datetime.now, description="创建时间")
    updated_at: dt_datetime = Field(default_factory=dt_datetime.now, description="更新时间")


class DailyMarketData(SQLModel, table=True):
    """日行情表"""
    __tablename__ = "daily_market_data"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="stock_basic_info.code", description="股票代码")
    date: dt_date = Field(description="日期")
    open_price: float = Field(description="开盘价")
    high_price: float = Field(description="最高价")
    low_price: float = Field(description="最低价")
    close_price: float = Field(description="收盘价")
    volume: float = Field(description="成交量")
    amount: Optional[float] = Field(description="成交额")
    change_pct: float = Field(description="涨跌百分比")
    limit_status: int = Field(default=0, description="涨跌停状态: -1跌停, 0正常, 1涨停")
    limit_up_text: Optional[str] = Field(default=None, description="涨停类型文本，换手板/T字板/一字板")


class WeeklyMarketData(SQLModel, table=True):
    """周行情表"""
    __tablename__ = "weekly_market_data"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="stock_basic_info.code", description="股票代码")
    date: dt_date = Field(description="周结束日期")
    open_price: float = Field(description="开盘价")
    high_price: float = Field(description="最高价")
    low_price: float = Field(description="最低价")
    close_price: float = Field(description="收盘价")
    volume: float = Field(description="成交量")
    amount: Optional[float] = Field(description="成交额")
    change_pct: float = Field(description="涨跌百分比")


class MonthlyMarketData(SQLModel, table=True):
    """月行情表"""
    __tablename__ = "monthly_market_data"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="stock_basic_info.code", description="股票代码")
    date: dt_date = Field(description="月结束日期")
    open_price: float = Field(description="开盘价")
    high_price: float = Field(description="最高价")
    low_price: float = Field(description="最低价")
    close_price: float = Field(description="收盘价")
    volume: float = Field(description="成交量")
    amount: Optional[float] = Field(description="成交额")
    change_pct: float = Field(description="涨跌百分比")


class ConceptInfo(SQLModel, table=True):
    """概念信息表"""
    __tablename__ = "concept_info"
    
    code: str = Field(primary_key=True, description="板块代码")
    name: str = Field(description="板块名称")
    market_cap: Optional[float] = Field(default=None, description="总市值")
    stock_count: int = Field(default=0, description="成分股数量")
    created_at: dt_datetime = Field(default_factory=dt_datetime.now, description="创建时间")
    updated_at: dt_datetime = Field(default_factory=dt_datetime.now, description="更新时间")


class ConceptStock(SQLModel, table=True):
    """概念成分股表"""
    __tablename__ = "concept_stock"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    concept_code: str = Field(foreign_key="concept_info.code", description="板块代码")
    stock_code: str = Field(foreign_key="stock_basic_info.code", description="股票代码")
    created_at: dt_datetime = Field(default_factory=dt_datetime.now, description="创建时间")


class ConceptTask(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float  # 0.0 to 1.0
    message: str
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ConceptTaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float
    message: str
    created_at: str
    completed_at: Optional[str]
    concepts_count: Optional[int] = None
    stocks_count: Optional[int] = None
    error: Optional[str] = None


# 数据库连接配置
# 使用环境变量配置数据库路径，支持Docker挂载
import os
BASE_DIR = Path(__file__).parent
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data_management" / "stock_data.db"))
# 确保数据库目录存在
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables():
    """创建数据库和表，并进行必要的轻量迁移（如新增列）"""
    # 先创建不存在的表
    SQLModel.metadata.create_all(engine)

    # 轻量迁移：为 daily_market_data 增加 limit_up_text 列（如不存在）
    try:
        with engine.connect() as conn:
            # 仅 SQLite 使用 PRAGMA; 若未来更换数据库需改为方言检测
            res = conn.exec_driver_sql("PRAGMA table_info(daily_market_data)")
            cols = [row[1] for row in res.fetchall()]  # 第二列是列名
            if 'limit_up_text' not in cols:
                conn.exec_driver_sql("ALTER TABLE daily_market_data ADD COLUMN limit_up_text VARCHAR NULL")
    except Exception as e:
        # 迁移失败不应阻断服务启动，打印警告即可
        import logging
        logging.getLogger(__name__).warning(f"Schema migration check failed: {e}")


# ---- Factor plugin types ----

class Factor(BaseModel):
    id: str
    name: str
    description: str = ""
    columns: List[Dict[str, Any]] = []  # ColumnSpec dicts
    # compute(history, top_spot) -> pd.DataFrame with '代码' and defined columns
    compute: Callable[[Dict[str, pd.DataFrame], Optional[pd.DataFrame]], pd.DataFrame]


def get_session():
    """获取数据库会话"""
    with Session(engine) as session:
        yield session