from __future__ import annotations
import logging
from datetime import date, timedelta
from typing import List
from collections import defaultdict

logger = logging.getLogger(__name__)


def get_stock_concepts(stock_code: str, session) -> List[tuple[str, str]]:
    """Get all concepts for a single stock
    
    Returns:
        List of (concept_code, concept_name) tuples
    """
    from sqlmodel import select
    from models import ConceptInfo, ConceptStock
    
    try:
        # Get concept codes for this stock
        concept_stocks = session.exec(
            select(ConceptStock).where(ConceptStock.stock_code == stock_code)
        ).all() or []
        
        if not concept_stocks:
            return []
        
        concept_codes = [cs.concept_code for cs in concept_stocks]
        
        # Get concept names
        concepts = session.exec(
            select(ConceptInfo).where(ConceptInfo.code.in_(concept_codes))
        ).all() or []
        
        concept_map = {c.code: c.name for c in concepts}
        return [(code, concept_map.get(code, code)) for code in concept_codes]
        
    except Exception as e:
        logger.warning(f"Failed to get concepts for stock {stock_code}: {e}")
        return []


def get_top_limit_up_stocks_in_sectors(latest_trade_date: date, session) -> List[dict]:
    """Get stocks with most limit-ups within top sectors
    
    Returns:
        List of stock info with limit-up counts and concept information
    """
    from sqlmodel import select
    from models import ConceptInfo, ConceptStock, DailyMarketData
    
    try:
        # Get top 10 concepts by stock count
        top_concepts = session.exec(
            select(ConceptInfo).order_by(ConceptInfo.stock_count.desc()).limit(10)
        ).all() or []
        
        if not top_concepts:
            return []
            
        concept_codes = [c.code for c in top_concepts]
        concept_map = {c.code: c.name for c in top_concepts}
        
        # Get all stocks in these concepts
        stocks = session.exec(
            select(ConceptStock).where(ConceptStock.concept_code.in_(concept_codes))
        ).all() or []
        
        # Count limit-up occurrences in recent 180 days
        today = latest_trade_date
        window_start = today - timedelta(days=180)
        
        stock_codes_in_concepts = list({s.stock_code for s in stocks})
        if not stock_codes_in_concepts:
            return []
        
        # Query limit-up records
        rows = session.exec(
            select(DailyMarketData.code, DailyMarketData.date)
            .where(
                DailyMarketData.code.in_(stock_codes_in_concepts),
                DailyMarketData.date >= window_start,
                DailyMarketData.date <= today,
                DailyMarketData.limit_status == 1,
            )
        ).all() or []
        
        # Count limit-ups per stock
        counts = {}
        for code_val, _ in rows:
            counts[code_val] = counts.get(code_val, 0) + 1
        
        # Build stock-to-concepts mapping
        stock_concepts = defaultdict(list)
        for s in stocks:
            concept_name = concept_map.get(s.concept_code)
            if concept_name:
                stock_concepts[s.stock_code].append((s.concept_code, concept_name))
        
        # Build result list
        result = []
        for stock_code, limit_count in counts.items():
            if limit_count <= 0:
                continue
                
            stock_concept_list = stock_concepts.get(stock_code, [])
            if not stock_concept_list:
                continue
            
            concept_codes = [cc for cc, _ in stock_concept_list]
            concept_names = [cn for _, cn in stock_concept_list]
            
            result.append({
                "code": stock_code,
                "limit_up_count": int(limit_count),
                "concept_codes": concept_codes,
                "concept_names": concept_names
            })
        
        # Sort by limit_up_count desc
        result.sort(key=lambda x: x["limit_up_count"], reverse=True)
        return result
        
    except Exception as e:
        logger.warning(f"Failed to get top limit-up stocks: {e}")
        return []


def build_extended_analysis(latest_trade_date: date, data: List[dict]) -> dict:
    """Build extended analysis including limit-up ranking within top concepts"""
    extended = {}
    try:
        from sqlmodel import Session, select
        from models import engine, ConceptInfo
        
        with Session(engine) as session:
            # Get top concept codes
            top_concepts = session.exec(
                select(ConceptInfo).order_by(ConceptInfo.stock_count.desc()).limit(10)
            ).all() or []
            concept_codes = [c.code for c in top_concepts]
            extended["top_sector_codes"] = concept_codes

            if concept_codes:
                # Get stocks with most limit-ups in these sectors
                stock_rankings = get_top_limit_up_stocks_in_sectors(latest_trade_date, session)
                
                # Add stock names from current data and build final ranking
                name_map = {r.get("代码"): r.get("名称") for r in data if r.get("代码")}
                final_ranking = []
                
                for stock_info in stock_rankings:
                    final_ranking.append({
                        "code": stock_info["code"],
                        "name": name_map.get(stock_info["code"]),
                        "limit_up_count": stock_info["limit_up_count"],
                        "concept_codes": stock_info["concept_codes"],
                        "concept_names": stock_info["concept_names"],
                        "concept_display": ", ".join(stock_info["concept_names"]),
                    })
                
                extended["limit_up_ranking"] = final_ranking
    except Exception as e:
        logger.warning(f"Extended analysis failed: {e}")
    
    return extended