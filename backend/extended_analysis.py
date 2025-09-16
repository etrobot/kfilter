from __future__ import annotations
import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Callable
from collections import defaultdict
from data_management.llm_client import evaluate_content_with_llm


logger = logging.getLogger(__name__)


def get_concept_analysis_with_deepsearch(concept_code: str, concept_name: str, on_progress: Optional[Callable[[str], None]] = None, stop_event: Optional[object] = None) -> Optional[Dict]:
    """Use deepsearch to analyze a specific concept and evaluate it with LLM in one atomic operation
    
    Returns:
        Dict with 'concept_analysis' and 'llm_evaluation' keys, or None if failed
    """
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
    search_query = f"{datetime.now().year}A股{concept_name}概念投资机会分析"
    
    messages = [
        {
            'role': 'user',
            'content': search_query
        }
    ]
    
    # Stream the response and collect it
    full_response = ""
    if on_progress:
        on_progress(f"开始深度搜索板块 {concept_name}")
    for chunk in client.stream_chat_completion(messages, model="0727-360B-API"):
        # Check if cancellation was requested
        if stop_event and stop_event.is_set():
            if on_progress:
                on_progress(f"深度搜索已被取消：{concept_name}")
            return None
            
        if on_progress and chunk:
            on_progress(f"深度搜索输出：{chunk}")
        full_response += chunk
        
    concept_analysis = full_response.strip() if full_response else None
    
    # If we got search results, immediately evaluate them with LLM
    if concept_analysis:
        if on_progress:
            on_progress(f"深度搜索完成，开始LLM评估：{concept_name}")
        
        # Check if cancellation was requested before evaluation
        if stop_event and stop_event.is_set():
            if on_progress:
                on_progress(f"LLM评估已被取消：{concept_name}")
            return None
        
        llm_evaluation = evaluate_content_with_llm(concept_analysis)
        if on_progress:
            on_progress(f"LLM评估完成：{concept_name}")
        
        return {
            'concept_analysis': concept_analysis,
            'llm_evaluation': llm_evaluation
        }
    else:
        if on_progress:
            on_progress(f"深度搜索未获得有效结果：{concept_name}")
        return None                         
        

def get_sector_analysis_with_hotspot_stocks(session, top_n: int = 5, on_progress: Optional[Callable[[str], None]] = None, stop_event: Optional[object] = None) -> dict:
    """Get sector-based analysis using real-time hotspot stocks from fetch_hot_spot
    
    Args:
        session: Database session
        top_n: Number of top concepts by stock count to analyze
        on_progress: Progress callback function
        stop_event: Optional threading.Event to signal cancellation
    
    Returns:
        Dict with sector codes as keys and their stock analysis as values
    """
    from sqlmodel import select, func
    from models import ConceptInfo, ConceptStock
    from market_data.data_fetcher import fetch_hot_spot,fetch_dragon_tiger_data
    
    # Get real-time hotspot stocks
    if on_progress:
        on_progress("获取实时热点股票数据...")
    
    hot_spot_df = fetch_hot_spot()
    
    if hot_spot_df.empty:
        logger.warning("No hotspot data found")
        return {}
    
    codes=list(set(fetch_dragon_tiger_data()['代码'].tolist()+hot_spot_df['代码'].tolist()))
    
    if on_progress:
        on_progress(f"获取到 {len(codes)} 只热点股票")
    
    # Query database to get concept-stock relationships for hotspot stocks
    # This efficiently gets all concepts that contain hotspot stocks
    concept_stock_query = select(
        ConceptStock.concept_code,
        ConceptStock.stock_code
    ).where(ConceptStock.stock_code.in_(codes))
    
    concept_stocks = session.exec(concept_stock_query).all() or []
    
    # Build concept -> stocks mapping
    concept_stocks_dict = defaultdict(set)
    for cs in concept_stocks:
        concept_stocks_dict[cs.concept_code].add(cs.stock_code)
    
    if on_progress:
        on_progress(f"找到 {len(concept_stocks_dict)} 个包含热点股票的板块")
    
    # Get concept info for all concepts that have hotspot stocks
    concept_codes = list(concept_stocks_dict.keys())
    concepts_info = session.exec(
        select(ConceptInfo).where(ConceptInfo.code.in_(concept_codes))
    ).all() or []
    concept_map = {c.code: c.name for c in concepts_info}
    
    # Sort concepts by number of hotspot stocks (descending) and take top_n
    sorted_concepts = sorted(
        concept_stocks_dict.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:top_n]
    
    if on_progress:
        on_progress(f"选择前 {len(sorted_concepts)} 个热点股票最多的板块进行深度分析")
    
    # Analyze selected concepts
    result = {}
    
    for sector_code, stock_codes in sorted_concepts:
        # Check if cancellation was requested
        if stop_event and stop_event.is_set():
            if on_progress:
                on_progress("分析已被取消")
            break
            
        try:
            sector_name = concept_map.get(sector_code, sector_code)
            
            # Get total stocks in this concept (not just hotspot stocks)
            total_stocks_query = select(func.count(ConceptStock.stock_code)).where(
                ConceptStock.concept_code == sector_code
            )
            total_stocks_in_sector = session.exec(total_stocks_query).first() or 0
            
            hotspot_count = len(stock_codes)
            
            if on_progress:
                on_progress(f"分析板块 {sector_name}（{sector_code}）… 共 {total_stocks_in_sector} 只，热点股票 {hotspot_count} 只")
            
            # Get deepsearch analysis and LLM evaluation in one atomic operation
            analysis_result = get_concept_analysis_with_deepsearch(sector_code, sector_name, on_progress=on_progress, stop_event=stop_event)
            
            # Extract analysis and evaluation from the combined result
            concept_analysis = analysis_result.get('concept_analysis') if analysis_result else None
            llm_evaluation = analysis_result.get('llm_evaluation') if analysis_result else None
            
            result[sector_code] = {
                "sector_code": sector_code,
                "sector_name": sector_name,
                "total_stocks": total_stocks_in_sector,
                "hotspot_count": hotspot_count,
                "hotspot_ratio": round(hotspot_count / total_stocks_in_sector * 100, 2) if total_stocks_in_sector > 0 else 0,
                "stocks": list(stock_codes),
                "concept_analysis": concept_analysis,
                "llm_evaluation": llm_evaluation,
                "error": None
            }
        except Exception as e:
            error_msg = f"分析板块 {sector_code} 时出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if on_progress:
                on_progress(error_msg)
            
            # Still add the sector to results but with error information
            result[sector_code] = {
                "sector_code": sector_code,
                "sector_name": concept_map.get(sector_code, sector_code),
                "error": str(e),
                "stocks": list(stock_codes)  # Still include the stock codes we found
            }
    
    return result
        



def run_standalone_extended_analysis(on_progress: Optional[Callable[[str], None]] = None, output_file: str = "extended_analysis_results.json", stop_event: Optional[object] = None) -> dict:
    """Run standalone extended analysis using real-time hotspot stocks
    
    Args:
        on_progress: Optional callback for progress updates
        output_file: Output file path for results (default: extended_analysis_results.json)
        stop_event: Optional threading.Event to signal cancellation
    
    Returns:
        Dict with analysis results
    """
    try:
        from sqlmodel import Session
        from models import engine
        from datetime import datetime
        
        with Session(engine) as session:
            # Check if cancellation was requested
            if stop_event and stop_event.is_set():
                return {"error": "分析已被取消"}
            
            # Get current date for analysis
            current_date = datetime.now().date()
            
            # Get sector analysis using hotspot stocks
            if on_progress:
                on_progress("开始基于实时热点股票进行板块分析")
            sector_analysis = get_sector_analysis_with_hotspot_stocks(session, top_n=20, on_progress=on_progress, stop_event=stop_event)
            
            # Sort sectors by LLM evaluation overall_score (descending)
            sorted_sectors = sorted(
                sector_analysis.values(),
                key=lambda x: x.get("llm_evaluation", {}).get("overall_score", 0) if x.get("llm_evaluation") else 0,
                reverse=True
            )
            
            # Count sectors with successful analysis
            sectors_with_analysis = sum(1 for sector in sorted_sectors if sector.get("concept_analysis"))
            sectors_with_llm_evaluation = sum(1 for sector in sorted_sectors if sector.get("llm_evaluation"))
            
            result = {
                "analysis_date": current_date.isoformat(),
                "analysis_type": "hotspot_based",
                "total_sectors_with_hotspots": len(sorted_sectors),
                "sectors_with_deepsearch_analysis": sectors_with_analysis,
                "sectors_with_llm_evaluation": sectors_with_llm_evaluation,
                "sectors": sorted_sectors
            }
            
            # Check if cancellation was requested before generating sunburst data
            if stop_event and stop_event.is_set():
                result["cancelled"] = True
                if on_progress:
                    on_progress("分析已被取消")
                return result
            
            # Generate sunburst data for visualization
            try:
                if on_progress:
                    on_progress("生成旭日图数据...")
                from data_management.chart_data_generator import generate_category_based_sunburst_chart_data
                sunburst_data = generate_category_based_sunburst_chart_data(sorted_sectors)
                result["sunburst_data"] = sunburst_data
                if on_progress:
                    on_progress("旭日图数据生成完成")
            except Exception as e:
                logger.warning(f"Failed to generate sunburst data: {e}")
                result["sunburst_data"] = None
                if on_progress:
                    on_progress(f"旭日图数据生成失败: {e}")
            
            # Write results to file (overwrite completely)
            try:
                if on_progress:
                    on_progress(f"写入分析结果到文件: {output_file}")
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Extended analysis results written to {output_file}")
                if on_progress:
                    on_progress(f"分析结果已保存到: {output_file}")
                    
            except Exception as e:
                logger.warning(f"Failed to write results to file {output_file}: {e}")
                if on_progress:
                    on_progress(f"文件写入失败: {e}")
            
            return result
            
    except Exception as e:
        logger.error(f"Standalone extended analysis failed: {e}")
        return {"error": str(e)}
