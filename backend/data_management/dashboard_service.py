from __future__ import annotations
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import numpy as np
import random
from sqlmodel import Session, select
from models import engine, DailyMarketData, StockBasicInfo

logger = logging.getLogger(__name__)


def get_kline_amplitude_analysis(n_days: int = 30) -> Dict[str, Any]:
    """Calculate K-line body amplitude for hot spot stocks over past N days"""
    
    try:
        with Session(engine) as session:
            # Get latest trade date from database
            latest_date_result = session.exec(
                select(DailyMarketData.date)
                .order_by(DailyMarketData.date.desc())
                .limit(1)
            ).first()
            
            if latest_date_result:
                end_date = latest_date_result
            else:
                # 获取最新交易日
                try:
                    from .stock_data_manager import get_latest_trade_date_and_limit_map
                    end_date, _ = get_latest_trade_date_and_limit_map()
                except Exception as e:
                    raise Exception(f"无法获取最新交易日期：{e}")
            
            start_date = end_date - timedelta(days=n_days * 2)  # Get more data to ensure we have enough trading days
            
            latest_date = end_date
            
            # Get top stocks by trading amount on latest date
            hot_stocks = session.exec(
                select(DailyMarketData)
                .where(DailyMarketData.date == latest_date)
                .where(DailyMarketData.volume > 0)
                .order_by(DailyMarketData.amount.desc())
                .limit(100)
            ).all()
            
            if not hot_stocks:
                logger.warning("No hot stocks found")
                return {"stocks": [], "top_5": [], "last_5": []}
            
            # Extract clean stock codes and create amount mapping (remove exchange prefix if exists)
            hot_stock_codes = []
            stock_amount_map = {}  # Map stock code to trading amount
            for stock in hot_stocks:
                code = stock.code
                # Remove exchange prefix (sh/sz) if it exists
                if code.startswith(('sh', 'sz')):
                    code = code[2:]
                hot_stock_codes.append(code)
                stock_amount_map[code] = stock.amount
            
            # Get historical data for these stocks
            historical_data = session.exec(
                select(DailyMarketData)
                .where(DailyMarketData.code.in_(hot_stock_codes))
                .where(DailyMarketData.date >= start_date)
                .where(DailyMarketData.date <= end_date)
                .order_by(DailyMarketData.code, DailyMarketData.date)
            ).all()
            
            # Group by stock code
            stock_data_map = {}
            for record in historical_data:
                if record.code not in stock_data_map:
                    stock_data_map[record.code] = []
                stock_data_map[record.code].append(record)
            
            # Calculate amplitude for each stock
            amplitude_results = []
            filtered_count = 0
            
            logger.info(f"开始处理 {len(hot_stock_codes)} 只热门股票")
            
            for stock_code in hot_stock_codes:
                stock_records = stock_data_map.get(stock_code, [])
                if len(stock_records) < n_days // 2:  # Need minimum data
                    filtered_count += 1
                    logger.debug(f"股票 {stock_code} 历史数据不足，跳过 (需要至少 {n_days // 2} 天，实际 {len(stock_records)} 天)")
                    continue
                
                # Sort by date
                stock_records.sort(key=lambda x: x.date)
                
                # Take only recent N trading days
                recent_records = stock_records[-n_days:] if len(stock_records) >= n_days else stock_records
                
                if not recent_records:
                    continue
                
                # Calculate K-line body amplitudes (close - open) / open * 100
                max_amplitude = 0
                trend_data = []
                dates = []
                
                first_close_price = None
                for i, record in enumerate(recent_records):
                    if record.open_price and record.open_price > 0:
                        amplitude = (record.close_price - record.open_price) / record.open_price * 100
                        if abs(amplitude) > abs(max_amplitude):
                            max_amplitude = amplitude
                    
                    # Set first close price as baseline
                    if i == 0:
                        first_close_price = record.close_price
                    
                    # Calculate percentage change relative to first close price
                    if first_close_price and first_close_price > 0:
                        percentage_change = ((record.close_price - first_close_price) / first_close_price) * 100
                        trend_data.append(percentage_change)
                    else:
                        trend_data.append(0)
                    
                    dates.append(record.date.strftime('%Y-%m-%d'))
                
                if trend_data:
                    # Get stock name from stock info table
                    stock_info = session.exec(
                        select(StockBasicInfo).where(StockBasicInfo.code == stock_code)
                    ).first()
                    stock_name = stock_info.name if stock_info else stock_code
                    
                    amplitude_results.append({
                        "code": stock_code,
                        "name": stock_name,
                        "amplitude": max_amplitude,
                        "trend_data": trend_data,
                        "dates": dates,
                        "amount": stock_amount_map.get(stock_code, 0)
                    })
            
            # Sort by amplitude (ascending - from negative to positive)
            amplitude_results.sort(key=lambda x: x["amplitude"])
            
            logger.info(f"数据筛选完成：原始热门股票 {len(hot_stock_codes)} 只，过滤掉 {filtered_count} 只，最终有效股票 {len(amplitude_results)} 只")
            
            # Get top 5 by trading amount (highest amount) from the hot stocks
            top_5 = sorted(amplitude_results, key=lambda x: x.get("amount", 0), reverse=True)[:5]

            # Get last 5 by trading amount (lowest amount) from the hot stocks
            last_5 = sorted(amplitude_results, key=lambda x: x.get("amount", 0))[:5]

            return {
                "stocks": amplitude_results,
                "top_5": top_5,
                "last_5": last_5,
                "n_days": n_days,
                "analysis_date": end_date.isoformat(),
                "total_stocks": len(amplitude_results)
            }
            
    except Exception as e:
        logger.error(f"Error in K-line amplitude analysis: {e}")
        return {
            "stocks": [],
            "top_5": [],
            "last_5": [],
            "error": str(e)
        }


def get_random_stocks_analysis(n_days: int = 30) -> Dict[str, Any]:
    """Get random 5 stocks for dashboard chart"""

    try:
        with Session(engine) as session:
            # Get latest trade date from database
            latest_date_result = session.exec(
                select(DailyMarketData.date)
                .order_by(DailyMarketData.date.desc())
                .limit(1)
            ).first()

            if latest_date_result:
                end_date = latest_date_result
            else:
                # 获取最新交易日
                try:
                    from .stock_data_manager import get_latest_trade_date_and_limit_map
                    end_date, _ = get_latest_trade_date_and_limit_map()
                except Exception as e:
                    raise Exception(f"无法获取最新交易日期：{e}")

            start_date = end_date - timedelta(days=n_days * 2)  # Get more data to ensure we have enough trading days

            latest_date = end_date

            # Get all stocks with volume > 0 on latest date
            all_stocks = session.exec(
                select(DailyMarketData)
                .where(DailyMarketData.date == latest_date)
                .where(DailyMarketData.volume > 0)
            ).all()

            if not all_stocks:
                logger.warning("No stocks found")
                return {"random_5": []}

            # Extract clean stock codes (remove exchange prefix if exists)
            stock_codes = []
            for stock in all_stocks:
                code = stock.code
                # Remove exchange prefix (sh/sz) if it exists
                if code.startswith(('sh', 'sz')):
                    code = code[2:]
                stock_codes.append(code)

            # Randomly select 5 stocks
            random_codes = random.sample(stock_codes, min(5, len(stock_codes)))

            # Get historical data for these stocks
            historical_data = session.exec(
                select(DailyMarketData)
                .where(DailyMarketData.code.in_(random_codes))
                .where(DailyMarketData.date >= start_date)
                .where(DailyMarketData.date <= end_date)
                .order_by(DailyMarketData.code, DailyMarketData.date)
            ).all()

            # Group by stock code
            stock_data_map = {}
            for record in historical_data:
                if record.code not in stock_data_map:
                    stock_data_map[record.code] = []
                stock_data_map[record.code].append(record)

            # Calculate trend data for each stock
            random_stocks = []

            for stock_code in random_codes:
                stock_records = stock_data_map.get(stock_code, [])
                if len(stock_records) < n_days // 2:  # Need minimum data
                    continue

                # Sort by date
                stock_records.sort(key=lambda x: x.date)

                # Take only recent N trading days
                recent_records = stock_records[-n_days:] if len(stock_records) >= n_days else stock_records

                if not recent_records:
                    continue

                trend_data = []
                dates = []
                first_close_price = None

                for i, record in enumerate(recent_records):
                    # Set first close price as baseline
                    if i == 0:
                        first_close_price = record.close_price

                    # Calculate percentage change relative to first close price
                    if first_close_price and first_close_price > 0:
                        percentage_change = ((record.close_price - first_close_price) / first_close_price) * 100
                        trend_data.append(percentage_change)
                    else:
                        trend_data.append(0)

                    dates.append(record.date.strftime('%Y-%m-%d'))

                if trend_data:
                    # Get stock name from stock info table
                    stock_info = session.exec(
                        select(StockBasicInfo).where(StockBasicInfo.code == stock_code)
                    ).first()
                    stock_name = stock_info.name if stock_info else stock_code

                    random_stocks.append({
                        "code": stock_code,
                        "name": stock_name,
                        "trend_data": trend_data,
                        "dates": dates
                    })

            return {
                "random_5": random_stocks[:5],  # Ensure we only return 5
                "n_days": n_days,
                "analysis_date": end_date.isoformat(),
                "total_stocks": len(random_stocks)
            }

    except Exception as e:
        logger.error(f"Error in random stocks analysis: {e}")
        return {
            "random_5": [],
            "error": str(e)
        }