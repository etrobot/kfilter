from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
from sqlmodel import Session, select
from models import engine, DailyMarketData, StockBasicInfo, get_session
from config import CATEGORY
import os
import json

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
            
            # Get all hot stocks sorted by trading amount (highest first)
            hot_stocks_by_amount = sorted(amplitude_results, key=lambda x: x.get("amount", 0), reverse=True)
            
            # Get top 5 by trading amount (highest amount) from the hot stocks
            top_5 = hot_stocks_by_amount[:5]

            # Get last 5 by trading amount (lowest amount) from the hot stocks
            last_5 = sorted(amplitude_results, key=lambda x: x.get("amount", 0))[:5]

            return {
                "stocks": amplitude_results,  # Sorted by amplitude for bar chart
                "hot_stocks": hot_stocks_by_amount,  # Sorted by trading amount for line chart pagination
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


def get_top_30_stocks_for_analysis() -> List[Dict[str, Any]]:
    """Get top 30 stocks by composite score from latest results with price change data
    
    Returns:
        List of dictionaries containing stock name, sector, and price changes
    """
    try:
        # Try to load from ranking.json
        ranking_file = "ranking.json"
        if not os.path.exists(ranking_file):
            logger.warning("ranking.json not found")
            return []
        
        with open(ranking_file, 'r', encoding='utf-8') as f:
            ranking_data = json.load(f)
        
        stocks_data = ranking_data.get('data', [])
        if not stocks_data:
            logger.warning("No data in ranking.json")
            return []

        # Refresh sector info and price change data to match API behavior
        stocks_data = _refresh_sector_info(stocks_data)
        stocks_data = _replace_factors_with_price_changes(stocks_data)
        
        # Sort by composite score and get top 30
        sorted_stocks = sorted(
            stocks_data, 
            key=lambda x: x.get('综合评分', 0), 
            reverse=True
        )[:30]
        
        # Extract required fields
        result = []
        for stock in sorted_stocks:
            result.append({
                '股票名称': stock.get('名称', ''),
                # '股票代码': stock.get('代码', ''),
                '最新价': stock.get('最新价', ''),
                '所属板块': stock.get('所属板块', ''),
                '近12个月涨跌幅': stock.get('近12个月涨跌幅'),
                '近1个月涨跌幅': stock.get('近1个月涨跌幅'),
                '近1周涨跌幅': stock.get('近1周涨跌幅'),
                '综合评分': stock.get('综合评分', 0)
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get top 30 stocks: {e}")
        return []


def _refresh_sector_info(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Refresh sector info using extended_analysis_results.json mapping."""
    if not data:
        return data

    try:
        from data_management.concept_service import get_stocks_sectors_from_extended_analysis
    except ImportError as exc:
        logger.warning(f"Failed to import sector refresh helper: {exc}")
        return data

    stock_codes = [record.get('代码') for record in data if record.get('代码')]
    sectors_map = get_stocks_sectors_from_extended_analysis(stock_codes)

    for record in data:
        stock_code = record.get('代码')
        if stock_code and stock_code in sectors_map:
            sector_name, rank = sectors_map[stock_code]
            record['所属板块'] = f"{rank:02d}-{sector_name}"

    return data


def _calculate_price_changes(stock_code: str) -> Dict[str, float | None]:
    """Calculate price change percentages for multiple periods."""
    result = {
        "近12个月涨跌幅": None,
        "近1个月涨跌幅": None,
        "近1周涨跌幅": None,
        "最新价": None,
    }

    try:
        with get_session() as session:
            stmt = (
                select(DailyMarketData)
                .where(DailyMarketData.code == stock_code)
                .order_by(DailyMarketData.date.desc())
                .limit(252)
            )
            records = list(session.exec(stmt).all())
            if not records:
                return result

            latest_record = records[0]
            latest_price = latest_record.close_price
            result["最新价"] = round(latest_price, 2) if latest_price is not None else None

            if len(records) >= 250:
                price_12m_ago = records[-1].close_price
                if price_12m_ago and price_12m_ago > 0:
                    result["近12个月涨跌幅"] = round(((latest_price - price_12m_ago) / price_12m_ago) * 100, 2)

            if len(records) >= 21:
                price_1m_ago = records[min(20, len(records) - 1)].close_price
                if price_1m_ago and price_1m_ago > 0:
                    result["近1个月涨跌幅"] = round(((latest_price - price_1m_ago) / price_1m_ago) * 100, 2)

            if len(records) >= 5:
                price_1w_ago = records[min(4, len(records) - 1)].close_price
                if price_1w_ago and price_1w_ago > 0:
                    result["近1周涨跌幅"] = round(((latest_price - price_1w_ago) / price_1w_ago) * 100, 2)

    except Exception as exc:
        logger.warning(f"Failed to calculate price changes for {stock_code}: {exc}")

    return result


def _replace_factors_with_price_changes(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove raw factor columns and add price change data."""
    if not data:
        return data

    raw_factor_fields = ["动量因子", "支撑因子", "MACD绝对值和", "最新MACD"]

    for record in data:
        stock_code = record.get('代码')
        if not stock_code:
            continue

        for field in raw_factor_fields:
            record.pop(field, None)

        record.update(_calculate_price_changes(stock_code))

    return data


def generate_market_cycle_analysis() -> Dict[str, Any]:
    """Generate market cycle analysis using LLM for top 30 stocks
    
    Returns:
        Dictionary containing analysis text and metadata
    """
    try:
        from .llm_client import get_llm_client
        from config import get_openai_config
        
        # Get top 30 stocks
        top_stocks = get_top_30_stocks_for_analysis()
        if not top_stocks:
            return {
                "success": False,
                "error": "无法获取股票数据",
                "analysis": ""
            }
        
        # Prepare data summary for LLM
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        
        # Build stock data table
        stock_summary = []
        for i, stock in enumerate(top_stocks, 1):
            change_12m = stock['近12个月涨跌幅']
            change_1m = stock['近1个月涨跌幅']
            change_1w = stock['近1周涨跌幅']
            
            change_12m_str = f"{change_12m:+.2f}%" if change_12m is not None else "N/A"
            change_1m_str = f"{change_1m:+.2f}%" if change_1m is not None else "N/A"
            change_1w_str = f"{change_1w:+.2f}%" if change_1w is not None else "N/A"
            
            stock_summary.append(
                f"{stock['股票名称']}（{stock['所属板块']}）最新价{stock['最新价']} 近12月: {change_12m_str} | 近1月: {change_1m_str} | 近1周: {change_1w_str}\n"
            )
        
        # Build prompt for LLM
        prompt = f"""当前时间：{current_time}
{CATEGORY}
{stock_summary}
你是一位善于分析热钱炒作路径的A股研究员。请基于以上股票数据，结合你印象中A股过去各板块的炒作周期和持续性，分析当前市场的炒作周期走向和短线热点趋势，得出明确的周策略最优解: 下周有可能持续强势或呼之欲出或反转的板块及板块内的潜力个股（注意获利盘风险）。不要编造资讯，不要输出表格，不要罗列股票数据，纯文字分析。
"""
        # Call LLM
        _, _, model = get_openai_config()
        client = get_llm_client()
        
        logger.info("Calling LLM for market cycle analysis...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        analysis_text = response.choices[0].message.content
        
        # Save to analysis.md
        analysis_file = "analysis.md"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            f.write(analysis_text)
        
        logger.info(f"Market cycle analysis saved to {analysis_file}")
        
        return {
            "success": True,
            "analysis": analysis_text,
            "generated_at": current_time,
            "stocks_analyzed": len(top_stocks),
            "file_path": analysis_file
        }
        
    except Exception as e:
        logger.error(f"Failed to generate market cycle analysis: {e}")
        return {
            "success": False,
            "error": str(e),
            "analysis": ""
        }


def get_market_analysis() -> Dict[str, Any]:
    """Get market cycle analysis from file (no caching, always read from disk)
    
    Returns:
        Dictionary containing the analysis and metadata
    """
    analysis_file = "analysis.md"
    
    # Always read from file, no caching
    if os.path.exists(analysis_file):
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis_text = f.read()
            
            # Get file modification time
            file_mtime = os.path.getmtime(analysis_file)
            file_time = datetime.fromtimestamp(file_mtime).strftime("%Y年%m月%d日 %H:%M")
            
            logger.info(f"Reading analysis from file (last updated: {file_time})")
            
            return {
                "success": True,
                "analysis": analysis_text,
                "last_updated": file_time,
                "file_exists": True
            }
        except Exception as e:
            logger.error(f"Failed to read analysis file: {e}")
            return {
                "success": False,
                "error": f"读取分析文件失败: {str(e)}",
                "analysis": "",
                "file_exists": True
            }
    else:
        logger.warning("Analysis file does not exist")
        return {
            "success": False,
            "error": "分析文件不存在，请先生成分析",
            "analysis": "",
            "file_exists": False
        }