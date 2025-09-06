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

# 缓存最新交易日和涨停数据，避免重复API调用
_latest_trade_date_cache = None
_limit_map_cache = None


def get_latest_trade_date_and_limit_map(use_cache: bool = True):
    """统一获取最新交易日和涨停数据，并更新到数据库。
    Args:
        use_cache: 是否使用缓存，默认True。设为False时强制重新获取。
    Returns:
        (交易日期, 涨停映射)
    """
    global _latest_trade_date_cache, _limit_map_cache
    
    # 如果已有缓存且允许使用缓存，直接返回
    if use_cache and _latest_trade_date_cache is not None and _limit_map_cache is not None:
        return _latest_trade_date_cache, _limit_map_cache
    
    try:
        ths_df = uplimit10jqka("")
        if not ths_df.empty and "first_limit_up_time" in ths_df.columns:
            # 获取最新交易日
            timestamps = ths_df["first_limit_up_time"].dropna()
            if not timestamps.empty:
                latest_timestamp = timestamps.iloc[0]
                trade_date = pd.to_datetime(int(latest_timestamp), unit='s').date()
                
                # 构建涨停映射
                limit_map = build_limit_up_map(ths_df)
                
                # 更新到数据库（当日涨停数据）
                if limit_map:
                    _update_limit_data_to_db(trade_date, limit_map)
                
                # 缓存结果
                _latest_trade_date_cache = trade_date
                _limit_map_cache = limit_map
                
                logger.info(f"Got latest trade date {trade_date} with {len(limit_map)} limit-up stocks")
                return trade_date, limit_map
    except Exception as e:
        logger.warning(f"Failed to get latest trade date from THS: {e}")
    
    # API失败，从数据库获取最新交易日
    with Session(engine) as session:
        latest_db_date = session.exec(
            select(DailyMarketData.date)
            .order_by(DailyMarketData.date.desc())
            .limit(1)
        ).first()
        if latest_db_date:
            _latest_trade_date_cache = latest_db_date
            _limit_map_cache = {}
            logger.info(f"Using latest trade date from database: {latest_db_date}")
            return latest_db_date, {}
    
    raise Exception("无法获取最新交易日期：THS API 失败且数据库无数据。请检查 THS API 连接或先导入基础数据。")


def _update_limit_data_to_db(trade_date: date, limit_map: dict):
    """将当日涨停数据更新到数据库"""
    if not limit_map:
        return
        
    updated = 0
    with Session(engine) as session:
        # 获取当日所有记录
        day_records = session.exec(
            select(DailyMarketData).where(DailyMarketData.date == trade_date)
        ).all()
        
        for record in day_records:
            if record.code in limit_map:
                # 涨停股票
                if record.limit_status != 1 or record.limit_up_text != limit_map[record.code]:
                    record.limit_status = 1
                    record.limit_up_text = limit_map[record.code]
                    updated += 1
            else:
                # 非涨停股票
                if record.limit_status != 0:
                    record.limit_status = 0
                    record.limit_up_text = None
                    
        if updated > 0:
            session.commit()
            logger.info(f"Updated {updated} limit-up records for {trade_date}")


def clear_trade_date_cache():
    """清除交易日缓存，强制下次重新获取"""
    global _latest_trade_date_cache, _limit_map_cache
    _latest_trade_date_cache = None
    _limit_map_cache = None


def save_spot_as_daily_data(spot_data: pd.DataFrame) -> int:
    """将实时行情保存为日K数据，并补充同花顺涨停类型文本。
    - spot_data: 包含日期字段和 ['代码','名称','最新价','涨跌幅','最高','最低','今开','成交量','成交额'] 的 DataFrame
    """
    if spot_data is None or spot_data.empty:
        return 0

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

            # 使用数据中的日期
            if "日期" not in row or pd.isna(row["日期"]):
                logger.warning(f"No date found for {code}, skipping")
                continue
            trade_date = pd.to_datetime(row["日期"]).date()

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
    
    # 获取最新交易日
    latest_trade_date, _ = get_latest_trade_date_and_limit_map()
    
    with Session(engine) as session:
        for code in stock_codes:
            # 查询该股票最新的日期
            stmt = select(DailyMarketData.date).where(
                DailyMarketData.code == code
            ).order_by(DailyMarketData.date.desc()).limit(1)
            
            result = session.exec(stmt).first()
            
            if result is None:
                # 该股票没有任何数据，从60天前开始获取
                missing_data[code] = latest_trade_date - timedelta(days=60)
            else:
                # 检查最新日期是否是最新交易日
                latest_date = result
                if latest_date < latest_trade_date:
                    # 数据不是最新的，从最新日期的下一天开始补充
                    missing_data[code] = latest_date + timedelta(days=1)
    
    return missing_data


def save_daily_data(history_data: Dict[str, pd.DataFrame]):
    """保存日K数据到数据库"""
    total_saved = 0

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
                        limit_status=0,  # 默认非涨停，后续通过专门函数回填
                        limit_up_text=None,
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
    """回填最近若干天内所有交易日的涨停状态和文本。
    检查哪些交易日没有处理过涨停信息，逐日调用同花顺接口获取涨停数据并更新数据库。

    返回更新的记录总数。
    """
    from datetime import timedelta
    updated = 0
    # 获取最新交易日
    today, _ = get_latest_trade_date_and_limit_map()
    
    start_date = today - timedelta(days=lookback_days)

    with Session(engine) as session:
        # 找出数据库中存在的所有交易日期（在时间窗口内）
        all_trading_dates = session.exec(
            select(DailyMarketData.date).where(
                DailyMarketData.date >= start_date,
                DailyMarketData.date <= today
            ).group_by(DailyMarketData.date).order_by(DailyMarketData.date.asc())
        ).all()

        if not all_trading_dates:
            logger.info("No trading dates found in the specified window")
            return 0

        # 检查哪些日期没有limit_up_text数据需要回填
        # 找出已经有limit_up_text的所有日期（去重）
        dates_with_limit_text = session.exec(
            select(DailyMarketData.date).where(
                DailyMarketData.date >= start_date,
                DailyMarketData.date <= today,
                DailyMarketData.limit_up_text.is_not(None)
            ).group_by(DailyMarketData.date)
        ).all()
        
        dates_with_limit_text_set = set(dates_with_limit_text)
        
        # 需要回填的日期 = 所有交易日期 - 已有limit_up_text的日期
        unprocessed_dates = [d for d in all_trading_dates if d not in dates_with_limit_text_set]

        if not unprocessed_dates:
            logger.info("All trading dates have been processed for limit-up status")
            return 0

        logger.info(f"Found {len(unprocessed_dates)} unprocessed trading date(s) for limit-up backfill")

        # 逐日处理未处理的交易日
        for d in unprocessed_dates:
            ds = d.isoformat()
            try:
                ths_df = uplimit10jqka(ds)
                limit_map = build_limit_up_map(ths_df)
            except Exception as e:
                logger.warning(f"Skip backfill for {ds} due to error: {e}")
                continue

            # 获取该日期的所有股票记录
            day_records = session.exec(
                select(DailyMarketData).where(DailyMarketData.date == d)
            ).all()
            
            for record in day_records:
                if record.code in limit_map:
                    # 涨停股票
                    record.limit_status = 1
                    record.limit_up_text = limit_map[record.code]
                    updated += 1
                else:
                    # 非涨停股票
                    record.limit_status = 0
                    record.limit_up_text = None
                    
            session.commit()
            logger.info(f"Processed {len(day_records)} records for {ds}, found {len(limit_map)} limit-up stocks")

    logger.info(f"Backfilled limit-up data for {updated} record(s) across {len(unprocessed_dates)} day(s)")
    return updated


def load_daily_data_for_analysis(stock_codes: List[str], limit: int = 60) -> Dict[str, pd.DataFrame]:
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