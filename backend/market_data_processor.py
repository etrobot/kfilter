from __future__ import annotations

import logging
from typing import List

import pandas as pd
from sqlmodel import Session, select
from models import (
    engine, DailyMarketData, WeeklyMarketData, MonthlyMarketData
)

logger = logging.getLogger(__name__)


def calculate_and_save_weekly_data(stock_codes: List[str], task_id: str = None):
    """从日K数据计算并保存周K数据"""
    total_saved = 0
    
    with Session(engine) as session:
        for code in stock_codes:
            # 获取该股票的所有日K数据
            stmt = select(DailyMarketData).where(
                DailyMarketData.code == code
            ).order_by(DailyMarketData.date)
            
            daily_records = session.exec(stmt).all()
            if not daily_records:
                continue
            
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
    
    logger.info(f"Calculated and saved {total_saved} weekly market data records")
    return total_saved


def calculate_and_save_monthly_data(stock_codes: List[str], task_id: str = None):
    """从日K数据计算并保存月K数据"""
    total_saved = 0
    
    with Session(engine) as session:
        for code in stock_codes:
            # 获取该股票的所有日K数据
            stmt = select(DailyMarketData).where(
                DailyMarketData.code == code
            ).order_by(DailyMarketData.date)
            
            daily_records = session.exec(stmt).all()
            if not daily_records:
                continue
            
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
    
    logger.info(f"Calculated and saved {total_saved} monthly market data records")
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


def calculate_technical_indicators(df: pd.DataFrame, periods: List[int] = [5, 10, 20, 60]) -> pd.DataFrame:
    """计算技术指标"""
    if df.empty or "收盘" not in df.columns:
        return df
    
    df = df.copy()
    df = df.sort_values("日期")
    
    # 移动平均线
    for period in periods:
        df[f"MA{period}"] = df["收盘"].rolling(window=period).mean()
    
    # RSI
    def calculate_rsi(prices, period=14):
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    df["RSI"] = calculate_rsi(df["收盘"])
    
    # 布林带
    df["BB_MIDDLE"] = df["收盘"].rolling(window=20).mean()
    bb_std = df["收盘"].rolling(window=20).std()
    df["BB_UPPER"] = df["BB_MIDDLE"] + (bb_std * 2)
    df["BB_LOWER"] = df["BB_MIDDLE"] - (bb_std * 2)
    
    return df