from __future__ import annotations
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

import numpy as np
from models import Task, TaskStatus
from utils import (
    add_task, 
    get_task, 
    set_last_completed_task, 
    handle_task_error, 
    update_task_progress,
    TASK_STOP_EVENTS,
    TASK_THREADS
)
from data_processor import fetch_spot, fetch_history, compute_factors
from stock_data_manager import (
    save_daily_data,
    save_stock_basic_info,
    load_daily_data_for_analysis
)
from market_data_processor import (
    calculate_and_save_weekly_data,
    calculate_and_save_monthly_data
)
from extended_analysis import build_extended_analysis

logger = logging.getLogger(__name__)

# In-memory storage for calculation results
ANALYSIS_RESULTS_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_LOCK = threading.Lock()


def get_cached_analysis_results(task_id: Optional[str] = None) -> Dict[str, Any]:
    """Get cached analysis results. If task_id is provided, get specific task results."""
    with CACHE_LOCK:
        if task_id:
            return ANALYSIS_RESULTS_CACHE.get(task_id, {})
        return dict(ANALYSIS_RESULTS_CACHE)


def get_latest_analysis_results() -> Optional[Dict[str, Any]]:
    """Get the most recent analysis results based on completion timestamp."""
    with CACHE_LOCK:
        if not ANALYSIS_RESULTS_CACHE:
            return None
        
        # Find the task with the most recent completion time
        latest_task_id = max(
            ANALYSIS_RESULTS_CACHE.keys(),
            key=lambda tid: ANALYSIS_RESULTS_CACHE[tid].get('completed_at', '')
        )
        return ANALYSIS_RESULTS_CACHE[latest_task_id]


def clear_analysis_cache(task_id: Optional[str] = None) -> None:
    """Clear cached analysis results. If task_id is provided, clear specific task only."""
    with CACHE_LOCK:
        if task_id:
            ANALYSIS_RESULTS_CACHE.pop(task_id, None)
        else:
            ANALYSIS_RESULTS_CACHE.clear()


def run_analysis_task(task_id: str, top_n: int, selected_factors: Optional[List[str]] = None, collect_latest_data: bool = True, stop_event: Optional[threading.Event] = None):
    """Background task for running stock analysis with database integration"""
    task = get_task(task_id)
    if not task:
        logger.error(f"Task {task_id} not found")
        return

    def check_cancel() -> bool:
        if stop_event is not None and stop_event.is_set():
            task.status = TaskStatus.CANCELLED
            task.message = "任务已取消"
            task.completed_at = datetime.now().isoformat()
            logger.info(f"Task {task_id} cancelled by user")
            return True
        return False
    
    task.status = TaskStatus.RUNNING
    update_task_progress(task_id, 0.0, "开始分析任务")
    if check_cancel():
        return
    
    logger.info(f"Starting stock analysis for top {top_n} stocks...")
    
    # 获取最新交易日和涨停数据（每次任务都重新获取）
    try:
        from stock_data_manager import get_latest_trade_date_and_limit_map
        update_task_progress(task_id, 0.02, "获取最新交易日和涨停数据")
        if check_cancel():
            return
        
        # 强制重新获取最新数据，不使用缓存
        latest_trade_date, _ = get_latest_trade_date_and_limit_map(use_cache=False)
        logger.info(f"Latest trade date: {latest_trade_date}")
    except Exception as e:
        error_msg = f"无法获取最新交易日期：{e}"
        logger.error(error_msg)
        task.status = TaskStatus.FAILED
        task.message = error_msg
        task.completed_at = datetime.now().isoformat()
        return
    
    if collect_latest_data:
        # Step 1: Fetch spot data
        update_task_progress(task_id, 0.05, f"获取实时行情数据 {latest_trade_date}")
        if check_cancel():
            return
        spot = fetch_spot()
        
        # Step 2: Save/update basic stock info
        update_task_progress(task_id, 0.1, "保存股票基本信息")
        if check_cancel():
            return
        save_stock_basic_info(spot)
        
        # Step 3: Get top stocks by trading volume
        update_task_progress(task_id, 0.15, "筛选热门股票")
        if check_cancel():
            return
        if "成交额" in spot.columns:
            top_spot = spot.nlargest(top_n, "成交额").copy()
        else:
            top_spot = spot.head(top_n).copy()
        
        logger.info(f"Selected top {len(top_spot)} stocks by trading volume")
        stock_codes = top_spot["代码"].tolist()
    else:
        # Skip hot spot data collection, use existing data from database
        update_task_progress(task_id, 0.15, "使用历史数据进行分析（跳过热点数据采集）")
        if check_cancel():
            return
        
        # Get stock codes from database (most recent stocks with data)
        from sqlmodel import Session, select, func
        from models import engine, StockBasicInfo, DailyMarketData
        
        with Session(engine) as session:
            # Get stocks with sufficient historical data (at least 35 days for factor calculation)
            # First, find stocks with enough data records
            stocks_with_data = session.exec(
                select(DailyMarketData.code, func.count(DailyMarketData.id).label('record_count'))
                .group_by(DailyMarketData.code)
                .having(func.count(DailyMarketData.id) >= 35)  # Minimum for factor calculation
                .order_by(func.count(DailyMarketData.id).desc())
                .limit(top_n * 2)  # Get more candidates
            ).all()
            
            if stocks_with_data:
                # Get the most recent date for these stocks
                candidate_codes = [code for code, _ in stocks_with_data]
                recent_date = session.exec(
                    select(func.max(DailyMarketData.date))
                    .where(DailyMarketData.code.in_(candidate_codes))
                ).first()
                
                if recent_date:
                    # Get top stocks by volume/amount from most recent trading day among candidates
                    recent_stocks = session.exec(
                        select(DailyMarketData.code, DailyMarketData.amount, StockBasicInfo.name)
                        .join(StockBasicInfo, DailyMarketData.code == StockBasicInfo.code)
                        .where(
                            DailyMarketData.date == recent_date,
                            DailyMarketData.code.in_(candidate_codes)
                        )
                        .order_by(DailyMarketData.amount.desc())
                        .limit(top_n)
                    ).all()
                    
                    if recent_stocks:
                        import pandas as pd
                        top_spot = pd.DataFrame([
                            {"代码": code, "名称": name, "成交额": amount}
                            for code, amount, name in recent_stocks
                        ])
                        stock_codes = top_spot["代码"].tolist()
                        logger.info(f"Selected top {len(top_spot)} stocks with sufficient data from database (date: {recent_date})")
                    else:
                        # Fallback: use first N stocks with sufficient data
                        import pandas as pd
                        fallback_stocks = session.exec(
                            select(StockBasicInfo.code, StockBasicInfo.name)
                            .where(StockBasicInfo.code.in_(candidate_codes))
                            .limit(top_n)
                        ).all()
                        top_spot = pd.DataFrame([
                            {"代码": code, "名称": name}
                            for code, name in fallback_stocks
                        ])
                        stock_codes = top_spot["代码"].tolist()
                        logger.info(f"Using fallback: selected {len(top_spot)} stocks with sufficient data")
                else:
                    raise Exception("No recent data found for stocks with sufficient history.")
            else:
                raise Exception("No stocks found with sufficient historical data (>=35 days). Please run with 'collect_latest_data=True' first.")
    
    # Step 4: Check database for existing historical data
    update_task_progress(task_id, 0.2, "检查数据库历史数据完整性")
    if check_cancel():
        return
        
    # Check if we have sufficient historical data in database for these stocks
    from sqlmodel import Session, select, func
    from models import engine, DailyMarketData
    
    need_fetch_history = False
    if collect_latest_data:
        # Check if we have recent data for all selected stocks
        with Session(engine) as session:
            # Check how many stocks have data in the last 7 days
            recent_cutoff = latest_trade_date - timedelta(days=7)
            stocks_with_recent_data = session.exec(
                select(func.count(func.distinct(DailyMarketData.code)))
                .where(
                    DailyMarketData.code.in_(stock_codes),
                    DailyMarketData.date >= recent_cutoff
                )
            ).first() or 0
            
            # If less than 80% of stocks have recent data, fetch from external API
            if stocks_with_recent_data < len(stock_codes) * 0.8:
                need_fetch_history = True
                logger.info(f"Only {stocks_with_recent_data}/{len(stock_codes)} stocks have recent data, will fetch from external API")
            else:
                logger.info(f"Database has sufficient recent data ({stocks_with_recent_data}/{len(stock_codes)} stocks), skipping external fetch")
    
    if need_fetch_history:
        update_task_progress(task_id, 0.25, "从外部API获取历史数据")
        if check_cancel():
            return
        
        # 直接获取所有股票的最近60天数据并upsert
        history = fetch_history(stock_codes, days=60, task_id=task_id)
        
        if history:
            update_task_progress(task_id, 0.35, "保存历史数据到数据库")
            if check_cancel():
                return
            save_daily_data(history)
            logger.info(f"Upserted historical data for {len(history)} stocks")
        else:
            logger.warning("No historical data fetched")
    else:
        # Skip external API call since database has sufficient data
        update_task_progress(task_id, 0.35, "使用数据库中的历史数据（跳过外部API调用）")
        logger.info("Using existing database historical data, skipping external API fetch")
    
    update_task_progress(task_id, 0.4, "历史数据更新完成")
    
    if check_cancel():
        return

    # Step 5b: Backfill missing limit-up texts for recent trading days
    try:
        from stock_data_manager import backfill_limit_up_texts_using_ths
        update_task_progress(task_id, 0.45, "回填历史涨停板类型")
        if check_cancel():
            return
        backfilled = backfill_limit_up_texts_using_ths(lookback_days=180)
        logger.info(f"Backfilled {backfilled} limit_up_text records in recent history")
    except Exception as e:
        logger.warning(f"Skip backfilling limit-up texts due to error: {e}")

    if check_cancel():
        return

    # Step 5: Calculate and save weekly/monthly data only when new data was fetched
    if need_fetch_history:
        # Step 5a: Calculate and save weekly data
        update_task_progress(task_id, 0.5, "计算并保存周K线数据")
        if check_cancel():
            return
        calculate_and_save_weekly_data(stock_codes, task_id)
        
        # Step 5b: Calculate and save monthly data
        update_task_progress(task_id, 0.6, "计算并保存月K线数据")
        if check_cancel():
            return
        calculate_and_save_monthly_data(stock_codes, task_id)
    else:
        # Skip weekly/monthly calculation when using existing data
        update_task_progress(task_id, 0.6, "使用现有数据，跳过周K线和月K线计算")
        logger.info("Skipping weekly/monthly data calculation since using existing database data")
    
    # Step 7: Load data from database for factor calculation
    update_task_progress(task_id, 0.7, "从数据库加载数据进行因子计算")
    if check_cancel():
        return
    
    # Load historical data from database for factor computation
    history_for_factors = load_daily_data_for_analysis(stock_codes, limit=120)
    
    # Step 8: Compute factors
    factor_msg = f"计算{'选定' if selected_factors else '所有'}因子"
    update_task_progress(task_id, 0.85, factor_msg)
    if check_cancel():
        return
    df = compute_factors(top_spot, history_for_factors, task_id=task_id, selected_factors=selected_factors)
    
    update_task_progress(task_id, 0.95, "数据清理和格式化")
    if check_cancel():
        return
    
    # Clean data for JSON serialization
    if not df.empty:
        # Replace NaN values with None
        df = df.replace({np.nan: None})
        # Ensure all numeric values are properly formatted
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            df[col] = df[col].astype(float, errors='ignore')
    
    data = df.to_dict(orient="records") if not df.empty else []

    if check_cancel():
        return

    # Extended analysis: build a limit-up ranking within top concepts
    extended = build_extended_analysis(latest_trade_date, data)

    # Complete task
    task.status = TaskStatus.COMPLETED
    task.progress = 1.0
    task.message = f"分析完成，数据已保存到数据库，共 {len(data)} 条结果"
    task.completed_at = datetime.now().isoformat()
    task.result = {
        "data": data,
        "count": len(data),
        "extended": extended or None,
    }

    # Store results in memory cache for frontend access
    with CACHE_LOCK:
        ANALYSIS_RESULTS_CACHE[task_id] = {
            "task_id": task_id,
            "status": task.status.value,
            "progress": task.progress,
            "message": task.message,
            "completed_at": task.completed_at,
            "created_at": task.created_at,
            "top_n": task.top_n,
            "selected_factors": task.selected_factors,
            "data": data,
            "count": len(data),
            "extended": extended or None,
        }

    set_last_completed_task(task)
    logger.info(f"Analysis completed successfully with database integration. Found {len(data)} results; extended={bool(extended)}")


def run_analysis_wrapper(task_id: str, top_n: int, selected_factors: Optional[List[str]] = None, collect_latest_data: bool = True, stop_event: Optional[threading.Event] = None):
    """Wrapper to handle task errors properly and cleanup registries"""
    error_occurred = False
    try:
        run_analysis_task(task_id, top_n, selected_factors, collect_latest_data, stop_event=stop_event)
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        handle_task_error(task_id, e)
        error_occurred = True
    finally:
        # Cleanup thread and stop event registries once task ends
        try:
            TASK_THREADS.pop(task_id, None)
            TASK_STOP_EVENTS.pop(task_id, None)
        except Exception:
            pass
    
    if error_occurred:
        logger.error(f"Task {task_id} encountered an error and was marked as failed")


def create_analysis_task(top_n: int = 100, selected_factors: Optional[List[str]] = None, collect_latest_data: bool = True) -> str:
    """Create and start a new analysis task"""
    task_id = str(uuid4())
    
    task = Task(
        task_id=task_id,
        status=TaskStatus.PENDING,
        progress=0.0,
        message="任务已创建，等待开始",
        created_at=datetime.now().isoformat(),
        top_n=top_n,
        selected_factors=selected_factors
    )
    
    add_task(task)
    
    # Prepare a stop event and thread, and register them
    stop_event = threading.Event()
    TASK_STOP_EVENTS[task_id] = stop_event
    
    # Start background thread with error wrapper
    thread = threading.Thread(target=run_analysis_wrapper, args=(task_id, top_n, selected_factors, collect_latest_data, stop_event))
    thread.daemon = True
    TASK_THREADS[task_id] = thread
    thread.start()
    
    return task_id