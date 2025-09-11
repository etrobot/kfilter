from __future__ import annotations
import logging
import os
from datetime import date, timedelta
from typing import List, Dict, Optional, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


def get_concept_analysis_with_deepsearch(concept_code: str, concept_name: str, on_progress: Optional[Callable[[str], None]] = None) -> Optional[str]:
    """Use deepsearch to analyze a specific concept"""
    try:
        from data_management.deepsearch import ZAIChatClient
        from config import is_zai_configured, get_zai_credentials
        
        # Check if credentials are properly configured
        if not is_zai_configured():
            logger.warning("ZAI credentials not properly configured, skipping deepsearch analysis")
            return None
            
        # Get credentials from config
        bearer_token, cookie_str = get_zai_credentials()
            
        client = ZAIChatClient(bearer_token=bearer_token, cookie_str=cookie_str)
        
        # Create search query for the concept
        search_query = f"A股{concept_name}概念分析"
        
        messages = [
            {
                'role': 'user',
                'content': search_query
            }
        ]
        
        # Stream the response and collect it
        full_response = ""
        if on_progress:
            on_progress(f"深度搜索：开始分析板块 {concept_name}")
        for chunk in client.stream_chat_completion(messages, model="0727-360B-API"):
            if on_progress and chunk:
                on_progress(f"深度搜索输出 {len(chunk)} 字符")
            full_response += chunk
            
        return full_response.strip() if full_response else None
        
    except Exception as e:
        logger.warning(f"Failed to get deepsearch analysis for concept {concept_name}: {e}")
        return None


def get_sector_analysis_for_latest_day(latest_trade_date: date, session, on_progress: Optional[Callable[[str], None]] = None) -> dict:
    """Get sector-based analysis for the latest trading day only
    
    Returns:
        Dict with sector codes as keys and their stock analysis as values
    """
    from sqlmodel import select
    from models import ConceptInfo, ConceptStock, DailyMarketData, StockBasicInfo
    
    try:
        # Get all daily market data for the latest trade date only
        latest_day_data = session.exec(
            select(DailyMarketData)
            .where(DailyMarketData.date == latest_trade_date)
        ).all() or []
        
        if not latest_day_data:
            logger.warning(f"No market data found for latest trade date: {latest_trade_date}")
            return {}
        
        # Get all concepts
        all_concepts = session.exec(select(ConceptInfo)).all() or []
        concept_map = {c.code: c.name for c in all_concepts}
        
        # Get all concept-stock relationships
        concept_stocks = session.exec(select(ConceptStock)).all() or []
        
        # Build sector -> stocks mapping
        sector_stocks = defaultdict(set)
        stock_sectors = defaultdict(list)
        
        for cs in concept_stocks:
            sector_stocks[cs.concept_code].add(cs.stock_code)
            stock_sectors[cs.stock_code].append((cs.concept_code, concept_map.get(cs.concept_code, cs.concept_code)))
        
        # Get stock names
        stock_names = session.exec(select(StockBasicInfo)).all() or []
        stock_name_map = {s.code: s.name for s in stock_names}
        
        # Analyze by sectors
        result = {}
        
        for sector_code, stock_codes in sector_stocks.items():
            sector_name = concept_map.get(sector_code, sector_code)
            
            # Get market data for stocks in this sector for latest day
            sector_day_data = [d for d in latest_day_data if d.code in stock_codes]
            
            if not sector_day_data:
                continue
            
            # Count limit-ups for this sector on latest day
            limit_up_stocks = []
            total_stocks = len(sector_day_data)
            if on_progress:
                on_progress(f"分析板块 {sector_name}（{sector_code}）… 共 {total_stocks} 只，统计涨停中")
            limit_up_count = 0
            
            for data in sector_day_data:
                if data.limit_status == 1:  # limit up
                    limit_up_count += 1
                    
                    # Get historical limit-up count for this stock (past 180 days)
                    historical_count = get_stock_historical_limit_ups(data.code, latest_trade_date, session)
                    
                    limit_up_stocks.append({
                        "code": data.code,
                        "name": stock_name_map.get(data.code, data.code),
                        "limit_up_count": historical_count,
                        "price": float(data.close_price) if data.close_price else 0
                    })
            
            # Sort stocks by historical limit-up count
            limit_up_stocks.sort(key=lambda x: x["limit_up_count"], reverse=True)
            
            if limit_up_count > 0:  # Only include sectors with limit-ups today
                # Get deepsearch analysis for this concept
                concept_analysis = get_concept_analysis_with_deepsearch(sector_code, sector_name, on_progress=on_progress)
                
                # Evaluate the analysis using LLM if we have content
                llm_evaluation = None
                if concept_analysis:
                    try:
                        from data_management.llm_client import evaluate_content_with_llm
                        if on_progress:
                            on_progress(f"LLM评估：分析板块 {sector_name} 的搜索结果")
                        llm_evaluation = evaluate_content_with_llm(concept_analysis)
                    except Exception as e:
                        logger.warning(f"Failed to evaluate concept analysis with LLM for {sector_name}: {e}")
                
                result[sector_code] = {
                    "sector_code": sector_code,
                    "sector_name": sector_name,
                    "total_stocks": total_stocks,
                    "limit_up_count_today": limit_up_count,
                    "limit_up_ratio": round(limit_up_count / total_stocks * 100, 2),
                    "stocks": limit_up_stocks,
                    "concept_analysis": concept_analysis,
                    "llm_evaluation": llm_evaluation
                }
        
        return result
        
    except Exception as e:
        logger.warning(f"Failed to get sector analysis: {e}")
        return {}


def get_stock_historical_limit_ups(stock_code: str, latest_date: date, session) -> int:
    """Get historical limit-up count for a stock in past 180 days"""
    from sqlmodel import select
    from models import DailyMarketData
    
    try:
        window_start = latest_date - timedelta(days=180)
        
        count = session.exec(
            select(DailyMarketData)
            .where(
                DailyMarketData.code == stock_code,
                DailyMarketData.date >= window_start,
                DailyMarketData.date <= latest_date,
                DailyMarketData.limit_status == 1
            )
        ).all() or []
        
        return len(count)
        
    except Exception as e:
        logger.warning(f"Failed to get historical limit-ups for {stock_code}: {e}")
        return 0


def get_top_limit_up_stocks_in_sectors(latest_trade_date: date, session) -> List[dict]:
    """Get stocks with most limit-ups in sectors for a given date"""
    from sqlmodel import select
    from models import ConceptInfo, ConceptStock, DailyMarketData
    
    try:
        # Get all daily market data for the latest trade date only
        latest_day_data = session.exec(
            select(DailyMarketData)
            .where(DailyMarketData.date == latest_trade_date)
        ).all() or []
        
        if not latest_day_data:
            return []
        
        # Get all concepts
        all_concepts = session.exec(select(ConceptInfo)).all() or []
        concept_map = {c.code: c.name for c in all_concepts}
        
        # Get all concept-stock relationships
        concept_stocks = session.exec(select(ConceptStock)).all() or []
        
        # Build sector -> stocks mapping
        sector_stocks = defaultdict(set)
        
        for cs in concept_stocks:
            sector_stocks[cs.concept_code].add(cs.stock_code)
        
        # Find stocks with limit up status
        limit_up_stocks = [d for d in latest_day_data if d.limit_status == 1]
        limit_up_stock_codes = {d.code for d in limit_up_stocks}
        
        # For each limit-up stock, get its concepts
        stock_concepts = defaultdict(list)
        for cs in concept_stocks:
            if cs.stock_code in limit_up_stock_codes:
                concept_name = concept_map.get(cs.concept_code, cs.concept_code)
                stock_concepts[cs.stock_code].append((cs.concept_code, concept_name))
        
        # Get historical limit-up counts for limit-up stocks
        stock_limit_up_counts = {}
        for stock_data in limit_up_stocks:
            historical_count = get_stock_historical_limit_ups(stock_data.code, latest_trade_date, session)
            stock_limit_up_counts[stock_data.code] = historical_count
        
        # Build result with stock info
        result = []
        for stock_data in limit_up_stocks:
            concepts = stock_concepts.get(stock_data.code, [])
            concept_codes = [c[0] for c in concepts]
            concept_names = [c[1] for c in concepts]
            
            result.append({
                "code": stock_data.code,
                "limit_up_count": stock_limit_up_counts[stock_data.code],
                "concept_codes": concept_codes,
                "concept_names": concept_names,
                "price": float(stock_data.close_price) if stock_data.close_price else 0
            })
        
        # Sort by historical limit-up count
        result.sort(key=lambda x: x["limit_up_count"], reverse=True)
        
        return result
        
    except Exception as e:
        logger.warning(f"Failed to get top limit-up stocks in sectors: {e}")
        return []


def run_standalone_extended_analysis(on_progress: Optional[Callable[[str], None]] = None) -> dict:
    """Run standalone extended analysis focusing on latest day sector analysis"""
    try:
        from sqlmodel import Session, select
        from models import engine, DailyMarketData
        
        with Session(engine) as session:
            # Get the latest trade date
            latest_data = session.exec(
                select(DailyMarketData).order_by(DailyMarketData.date.desc()).limit(1)
            ).first()
            
            if not latest_data:
                return {"error": "No market data found"}
            
            latest_date = latest_data.date
            
            # Get sector analysis for latest day
            if on_progress:
                on_progress(f"开始按板块分析 {latest_date.isoformat()} 的涨停数据")
            sector_analysis = get_sector_analysis_for_latest_day(latest_date, session, on_progress=on_progress)
            
            # Sort sectors by limit-up ratio
            sorted_sectors = sorted(
                sector_analysis.values(),
                key=lambda x: x["limit_up_ratio"],
                reverse=True
            )
            
            # Count sectors with successful analysis
            sectors_with_analysis = sum(1 for sector in sorted_sectors if sector.get("concept_analysis"))
            sectors_with_llm_evaluation = sum(1 for sector in sorted_sectors if sector.get("llm_evaluation"))
            
            return {
                "analysis_date": latest_date.isoformat(),
                "total_sectors_with_limit_ups": len(sorted_sectors),
                "sectors_with_deepsearch_analysis": sectors_with_analysis,
                "sectors_with_llm_evaluation": sectors_with_llm_evaluation,
                "sectors": sorted_sectors
            }
            
    except Exception as e:
        logger.error(f"Standalone extended analysis failed: {e}")
        return {"error": str(e)}
