from __future__ import annotations

import logging
from typing import List

import pandas as pd
from sqlmodel import Session, select
from models import (
    engine, DailyMarketData, WeeklyMarketData, MonthlyMarketData
)
from utils.quotation import stock_zh_a_hist_tx_period

logger = logging.getLogger(__name__)


def calculate_and_save_weekly_data(stock_codes: List[str], task_id: str = None):
    """获取并保存周K数据，优先使用API获取，失败时从日K数据计算"""
    total_saved = 0
    
    for code in stock_codes:
        # 尝试从API获取周K数据
        try:
            weekly_df = stock_zh_a_hist_tx_period(
                symbol=code,
                period="weekly",
                start_date="19000101",
                end_date="20500101"
            )
            
            if not weekly_df.empty:
                # API获取成功，使用API数据
                saved_count = _save_weekly_data_from_df(code, weekly_df)
                total_saved += saved_count
                logger.info(f"Saved {saved_count} weekly data for {code} from API")
                continue
        except Exception as e:
            logger.warning(f"Failed to fetch weekly data from API for {code}: {e}")
        
        # API获取失败，从日K数据计算
        try:
            saved_count = _calculate_weekly_from_daily(code)
            total_saved += saved_count
            if saved_count > 0:
                logger.info(f"Calculated {saved_count} weekly data for {code} from daily data")
        except Exception as e:
            logger.error(f"Failed to calculate weekly data for {code}: {e}")
    
    logger.info(f"Total weekly market data records saved: {total_saved}")
    return total_saved


def _save_weekly_data_from_df(code: str, weekly_df: pd.DataFrame) -> int:
    """从DataFrame保存周K数据到数据库"""
    total_saved = 0
    
    with Session(engine) as session:
        for _, row in weekly_df.iterrows():
            week_date = row['date']
            
            # 检查是否已存在
            existing = session.exec(
                select(WeeklyMarketData).where(
                    WeeklyMarketData.code == code,
                    WeeklyMarketData.date == week_date
                )
            ).first()
            
            if existing is None:
                # 计算涨跌幅
                change_pct = 0
                if row['open'] > 0:
                    change_pct = (row['close'] - row['open']) / row['open'] * 100
                
                # 腾讯API返回的周K/月K数据：
                # - amount字段实际是成交量（单位：手）
                # - 没有返回成交额数据
                # 映射关系：API的amount -> 数据库的volume
                volume = float(row['amount']) if 'amount' in row and pd.notna(row['amount']) else 0.0
                # 成交额数据不可用，设为0
                amount = 0.0
                
                weekly_data = WeeklyMarketData(
                    code=code,
                    date=week_date,
                    open_price=float(row['open']),
                    high_price=float(row['high']),
                    low_price=float(row['low']),
                    close_price=float(row['close']),
                    volume=volume,
                    amount=amount,
                    change_pct=change_pct
                )
                session.add(weekly_data)
                total_saved += 1
        
        session.commit()
    
    return total_saved


def _calculate_weekly_from_daily(code: str) -> int:
    """从日K数据计算周K数据"""
    total_saved = 0
    
    with Session(engine) as session:
        # 获取该股票的所有日K数据
        stmt = select(DailyMarketData).where(
            DailyMarketData.code == code
        ).order_by(DailyMarketData.date)
        
        daily_records = session.exec(stmt).all()
        if not daily_records:
            return 0
        
        # 转换为DataFrame进行周K计算
        df = pd.DataFrame([{
            "date": record.date,
            "open": record.open_price,
            "high": record.high_price,
            "low": record.low_price,
            "close": record.close_price,
            "volume": record.volume,
            "amount": record.amount
        } for record in daily_records])
        
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        
        # 按周重采样
        weekly = df.resample('W').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'amount': 'sum'
        }).dropna()
        
        for week_end, row in weekly.iterrows():
            week_date = week_end.date()
            
            # 检查是否已存在
            existing = session.exec(
                select(WeeklyMarketData).where(
                    WeeklyMarketData.code == code,
                    WeeklyMarketData.date == week_date
                )
            ).first()
            
            if existing is None:
                # 获取本周第一天的收盘价来计算周涨跌幅
                week_start = week_end - pd.Timedelta(days=6)  # 一周前
                week_start_data = df[df.index >= week_start].iloc[0] if len(df[df.index >= week_start]) > 0 else None
                
                change_pct = 0
                if week_start_data is not None:
                    week_start_close = week_start_data['open']  # 周开盘价
                    if week_start_close > 0:
                        change_pct = (row['close'] - week_start_close) / week_start_close * 100
                
                weekly_data = WeeklyMarketData(
                    code=code,
                    date=week_date,
                    open_price=float(row['open']),
                    high_price=float(row['high']),
                    low_price=float(row['low']),
                    close_price=float(row['close']),
                    volume=float(row['volume']),
                    amount=float(row['amount']),
                    change_pct=change_pct
                )
                session.add(weekly_data)
                total_saved += 1
        
        session.commit()
    
    return total_saved


def calculate_and_save_monthly_data(stock_codes: List[str], task_id: str = None):
    """获取并保存月K数据，优先使用API获取，失败时从日K数据计算"""
    total_saved = 0
    
    for code in stock_codes:
        # 尝试从API获取月K数据
        try:
            monthly_df = stock_zh_a_hist_tx_period(
                symbol=code,
                period="monthly",
                start_date="19000101",
                end_date="20500101"
            )
            
            if not monthly_df.empty:
                # API获取成功，使用API数据
                saved_count = _save_monthly_data_from_df(code, monthly_df)
                total_saved += saved_count
                logger.info(f"Saved {saved_count} monthly data for {code} from API")
                continue
        except Exception as e:
            logger.warning(f"Failed to fetch monthly data from API for {code}: {e}")
        
        # API获取失败，从日K数据计算
        try:
            saved_count = _calculate_monthly_from_daily(code)
            total_saved += saved_count
            if saved_count > 0:
                logger.info(f"Calculated {saved_count} monthly data for {code} from daily data")
        except Exception as e:
            logger.error(f"Failed to calculate monthly data for {code}: {e}")
    
    logger.info(f"Total monthly market data records saved: {total_saved}")
    return total_saved


def _save_monthly_data_from_df(code: str, monthly_df: pd.DataFrame) -> int:
    """从DataFrame保存月K数据到数据库"""
    total_saved = 0
    
    with Session(engine) as session:
        for _, row in monthly_df.iterrows():
            month_date = row['date']
            
            # 检查是否已存在
            existing = session.exec(
                select(MonthlyMarketData).where(
                    MonthlyMarketData.code == code,
                    MonthlyMarketData.date == month_date
                )
            ).first()
            
            if existing is None:
                # 计算涨跌幅
                change_pct = 0
                if row['open'] > 0:
                    change_pct = (row['close'] - row['open']) / row['open'] * 100
                
                # 腾讯API返回的周K/月K数据：
                # - amount字段实际是成交量（单位：手）
                # - 没有返回成交额数据
                # 映射关系：API的amount -> 数据库的volume
                volume = float(row['amount']) if 'amount' in row and pd.notna(row['amount']) else 0.0
                # 成交额数据不可用，设为0
                amount = 0.0
                
                monthly_data = MonthlyMarketData(
                    code=code,
                    date=month_date,
                    open_price=float(row['open']),
                    high_price=float(row['high']),
                    low_price=float(row['low']),
                    close_price=float(row['close']),
                    volume=volume,
                    amount=amount,
                    change_pct=change_pct
                )
                session.add(monthly_data)
                total_saved += 1
        
        session.commit()
    
    return total_saved


def _calculate_monthly_from_daily(code: str) -> int:
    """从日K数据计算月K数据"""
    total_saved = 0
    
    with Session(engine) as session:
        # 获取该股票的所有日K数据
        stmt = select(DailyMarketData).where(
            DailyMarketData.code == code
        ).order_by(DailyMarketData.date)
        
        daily_records = session.exec(stmt).all()
        if not daily_records:
            return 0
        
        # 转换为DataFrame进行月K计算
        df = pd.DataFrame([{
            "date": record.date,
            "open": record.open_price,
            "high": record.high_price,
            "low": record.low_price,
            "close": record.close_price,
            "volume": record.volume,
            "amount": record.amount
        } for record in daily_records])
        
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        
        # 按月重采样
        monthly = df.resample('M').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'amount': 'sum'
        }).dropna()
        
        for month_end, row in monthly.iterrows():
            month_date = month_end.date()
            
            # 检查是否已存在
            existing = session.exec(
                select(MonthlyMarketData).where(
                    MonthlyMarketData.code == code,
                    MonthlyMarketData.date == month_date
                )
            ).first()
            
            if existing is None:
                # 获取本月第一天的收盘价来计算月涨跌幅
                month_start = month_end.replace(day=1)  # 月初
                month_start_data = df[df.index >= month_start].iloc[0] if len(df[df.index >= month_start]) > 0 else None
                
                change_pct = 0
                if month_start_data is not None:
                    month_start_close = month_start_data['open']  # 月开盘价
                    if month_start_close > 0:
                        change_pct = (row['close'] - month_start_close) / month_start_close * 100
                
                monthly_data = MonthlyMarketData(
                    code=code,
                    date=month_date,
                    open_price=float(row['open']),
                    high_price=float(row['high']),
                    low_price=float(row['low']),
                    close_price=float(row['close']),
                    volume=float(row['volume']),
                    amount=float(row['amount']),
                    change_pct=change_pct
                )
                session.add(monthly_data)
                total_saved += 1
        
        session.commit()
    
    return total_saved


def get_weekly_data(stock_codes: List[str], limit: int = None) -> pd.DataFrame:
    """获取周K线数据"""
    weekly_data = []
    
    with Session(engine) as session:
        for code in stock_codes:
            stmt = select(WeeklyMarketData).where(
                WeeklyMarketData.code == code
            ).order_by(WeeklyMarketData.date.desc())
            
            if limit:
                stmt = stmt.limit(limit)
            
            records = session.exec(stmt).all()
            for record in records:
                weekly_data.append({
                    "代码": record.code,
                    "日期": record.date,
                    "开盘": record.open_price,
                    "最高": record.high_price,
                    "最低": record.low_price,
                    "收盘": record.close_price,
                    "成交量": record.volume,
                    "成交额": record.amount,
                    "涨跌幅": record.change_pct
                })
    
    return pd.DataFrame(weekly_data)


def get_monthly_data(stock_codes: List[str], limit: int = None) -> pd.DataFrame:
    """获取月K线数据"""
    monthly_data = []
    
    with Session(engine) as session:
        for code in stock_codes:
            stmt = select(MonthlyMarketData).where(
                MonthlyMarketData.code == code
            ).order_by(MonthlyMarketData.date.desc())
            
            if limit:
                stmt = stmt.limit(limit)
            
            records = session.exec(stmt).all()
            for record in records:
                monthly_data.append({
                    "代码": record.code,
                    "日期": record.date,
                    "开盘": record.open_price,
                    "最高": record.high_price,
                    "最低": record.low_price,
                    "收盘": record.close_price,
                    "成交量": record.volume,
                    "成交额": record.amount,
                    "涨跌幅": record.change_pct
                })
    
    return pd.DataFrame(monthly_data)