from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional

import pandas as pd
from sqlmodel import Session, select
from models import (
    engine, StockBasicInfo, DailyMarketData
)
from ths_api import uplimit10jqka, build_limit_up_map

logger = logging.getLogger(__name__)


def save_spot_as_daily_data(spot_data: pd.DataFrame, date_override: Optional[date] = None) -> int:
    """将实时行情保存为今日日K数据，并补充同花顺涨停类型文本。
    - spot_data: 包含 ['代码','名称','最新价','涨跌幅','最高','最低','今开','成交量','成交额'] 的 DataFrame
    - date_override: 覆盖写入的交易日期，默认使用今天
    """
    if spot_data is None or spot_data.empty:
        return 0

    trade_date = date_override or date.today()

    # 获取涨停类型映射
    limit_map: Dict[str, str] = {}
    try:
        ths_df = uplimit10jqka("")
        limit_map = build_limit_up_map(ths_df)
    except Exception as e:
        logger.warning(f"Failed to fetch limit-up map for spot: {e}")

    total_saved = 0
    with Session(engine) as session:
        for _, row in spot_data.iterrows():
            code = row.get("代码")
            if not code:
                continue

            # 检查是否已存在当日记录
            existing = session.exec(
                select(DailyMarketData).where(
                    DailyMarketData.code == code,
                    DailyMarketData.date == trade_date
                )
            ).first()

            if existing is not None:
                # 已存在则跳过（可考虑更新）
                continue

            change_pct = float(row.get("涨跌幅", 0)) if pd.notna(row.get("涨跌幅", None)) else 0
            # 直接使用同花顺涨停池数据判断涨停状态
            limit_status = 1 if code in limit_map else 0
            limit_text = limit_map.get(code) if limit_status == 1 else None

            daily = DailyMarketData(
                code=code,
                date=trade_date,
                open_price=float(row.get("今开", 0)),
                high_price=float(row.get("最高", 0)),
                low_price=float(row.get("最低", 0)),
                close_price=float(row.get("最新价", 0)),
                volume=float(row.get("成交量", 0)),
                amount=float(row.get("成交额", 0)),
                change_pct=change_pct,
                limit_status=limit_status,
                limit_up_text=limit_text,
            )
            session.add(daily)
            total_saved += 1

        session.commit()

    logger.info(f"Saved {total_saved} spot rows as daily data for {trade_date}")
    return total_saved


def get_missing_daily_data(stock_codes: List[str]) -> Dict[str, date]:
    """检查哪些股票的日K数据缺失或不完整，返回需要从哪个日期开始补充数据"""
    missing_data = {}
    today = date.today()
    
    with Session(engine) as session:
        for code in stock_codes:
            # 查询该股票最新的日期
            stmt = select(DailyMarketData.date).where(
                DailyMarketData.code == code
            ).order_by(DailyMarketData.date.desc()).limit(1)
            
            result = session.exec(stmt).first()
            
            if result is None:
                # 该股票没有任何数据，从60天前开始获取
                missing_data[code] = today - timedelta(days=120)
            else:
                # 检查最新日期是否是今天
                latest_date = result
                if latest_date < today:
                    # 数据不是最新的，从最新日期的下一天开始补充
                    missing_data[code] = latest_date + timedelta(days=1)
    
    return missing_data


def save_daily_data(history_data: Dict[str, pd.DataFrame], task_id: str = None):
    """保存日K数据到数据库，并补充同花顺涨停类型文本"""
    total_saved = 0

    # 尝试获取当天的涨停类型映射（仅用于最新交易日，历史数据通常不可回溯）
    limit_map: Dict[str, str] = {}
    today = date.today()
    try:
        ths_df = uplimit10jqka("")
        limit_map = build_limit_up_map(ths_df)
    except Exception as e:
        logger.warning(f"Failed to fetch limit-up map: {e}")

    with Session(engine) as session:
        for code, df in history_data.items():
            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                record_date = row["日期"].date()
                # 检查是否已存在
                existing = session.exec(
                    select(DailyMarketData).where(
                        DailyMarketData.code == code,
                        DailyMarketData.date == record_date
                    )
                ).first()

                if existing is None:
                    # 计算涨跌停状态 - 直接使用同花顺涨停池数据
                    limit_status = 0
                    if code in limit_map:
                        # 同花顺涨停池中的股票确认为涨停
                        limit_status = 1

                    # 仅当保存当天数据时，尝试补充涨停文本（并且记录日期是今天）
                    limit_text = None
                    if record_date == today and limit_status == 1 and code in limit_map:
                        limit_text = limit_map.get(code)

                    daily_data = DailyMarketData(
                        code=code,
                        date=record_date,
                        open_price=float(row.get("开盘", 0)),
                        high_price=float(row.get("最高", 0)),
                        low_price=float(row.get("最低", 0)),
                        close_price=float(row.get("收盘", 0)),
                        volume=float(row.get("成交量", 0)),
                        amount=float(row.get("成交额", 0)),
                        change_pct=float(row.get("涨跌幅", 0)),
                        limit_status=limit_status,
                        limit_up_text=limit_text,
                    )
                    session.add(daily_data)
                    total_saved += 1

        session.commit()

    logger.info(f"Saved {total_saved} daily market data records")
    return total_saved


def save_stock_basic_info(spot_data: pd.DataFrame):
    """保存股票基本信息"""
    total_saved = 0
    
    with Session(engine) as session:
        for _, row in spot_data.iterrows():
            code = row["代码"]
            name = row.get("名称", code)
            
            # 检查是否已存在
            existing = session.exec(
                select(StockBasicInfo).where(StockBasicInfo.code == code)
            ).first()
            
            if existing is None:
                stock_info = StockBasicInfo(
                    code=code,
                    name=name,
                    description=None,
                    tags=None
                )
                session.add(stock_info)
                total_saved += 1
            elif existing.name != name:
                # 更新股票名称
                existing.name = name
                existing.updated_at = datetime.now()
        
        session.commit()
    
    logger.info(f"Saved/updated {total_saved} stock basic info records")
    return total_saved


def backfill_limit_up_texts_using_ths(lookback_days: int = 180) -> int:
    """回填最近若干天（默认180天）内所有涨停日的 limit_up_text。
    从 daily_market_data 表中找出 limit_status=1 且 limit_up_text 为空的交易日，
    逐日调用同花顺接口获取涨停类型并更新数据库。

    返回更新的记录总数。
    """
    from datetime import timedelta
    updated = 0
    today = date.today()
    start_date = today - timedelta(days=lookback_days)

    with Session(engine) as session:
        # 找出需要回填的 distinct 日期
        stmt_dates = select(DailyMarketData.date).where(
            DailyMarketData.date >= start_date,
            DailyMarketData.date <= today,
            DailyMarketData.limit_status == 1,
            DailyMarketData.limit_up_text.is_(None)
        ).group_by(DailyMarketData.date).order_by(DailyMarketData.date.asc())
        missing_dates = [d for d in session.exec(stmt_dates).all()]

        if not missing_dates:
            logger.info("No limit-up text backfill needed in the recent window")
            return 0

        # 统计距离今天有多少个交易日（以数据库中存在的交易日为准）
        earliest_missing = min(missing_dates)
        trading_days_stmt = select(DailyMarketData.date).where(
            DailyMarketData.date >= earliest_missing,
            DailyMarketData.date <= today,
        ).group_by(DailyMarketData.date)
        trading_days = [d for d in session.exec(trading_days_stmt).all()]
        logger.info(
            f"Found {len(missing_dates)} date(s) with missing limit_up_text; "
            f"earliest {earliest_missing.isoformat()}, ~{len(trading_days)} trading day(s) to today"
        )

        for d in missing_dates:
            ds = d.isoformat()
            try:
                ths_df = uplimit10jqka(ds)
                limit_map = build_limit_up_map(ths_df)
            except Exception as e:
                logger.warning(f"Skip backfill for {ds} due to error: {e}")
                continue

            if not limit_map:
                logger.info(f"No limit-up map returned for {ds}")
                continue

            # 选出该交易日所有涨停记录
            day_stmt = select(DailyMarketData).where(
                DailyMarketData.date == d,
                DailyMarketData.limit_status == 1,
                DailyMarketData.limit_up_text.is_(None)
            )
            rows = session.exec(day_stmt).all() or []
            for row in rows:
                lut = limit_map.get(row.code)
                if lut:
                    row.limit_up_text = lut
                    updated += 1
            session.commit()

    logger.info(f"Backfilled {updated} limit_up_text record(s) across {len(missing_dates)} day(s)")
    return updated


def load_daily_data_for_analysis(stock_codes: List[str], limit: int = 120) -> Dict[str, pd.DataFrame]:
    """从数据库加载日K数据用于因子分析"""
    history_data = {}
    
    with Session(engine) as session:
        for code in stock_codes:
            stmt = select(DailyMarketData).where(
                DailyMarketData.code == code
            ).order_by(DailyMarketData.date.desc()).limit(limit)
            
            daily_records = session.exec(stmt).all()
            if daily_records:
                df = pd.DataFrame([{
                    "日期": pd.to_datetime(record.date),
                    "开盘": record.open_price,
                    "最高": record.high_price,
                    "最低": record.low_price,
                    "收盘": record.close_price,
                    "成交量": record.volume,
                    "成交额": record.amount,
                    "涨跌幅": record.change_pct,
                    "limit_up_text": record.limit_up_text
                } for record in daily_records])
                df = df.sort_values("日期")
                history_data[code] = df
    
    logger.info(f"Loaded daily data for {len(history_data)} stocks from database")
    return history_data