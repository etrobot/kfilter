from __future__ import annotations
import logging
import threading
from datetime import datetime, date
from uuid import uuid4

import numpy as np
from models import Task, TaskStatus
from utils import (
    add_task, 
    get_task, 
    set_last_completed_task, 
    handle_task_error, 
    update_task_progress
)
from data_processor import fetch_spot, fetch_history, compute_factors
from stock_data_manager import (
    get_missing_daily_data,
    save_daily_data,
    save_stock_basic_info,
    load_daily_data_for_analysis
)
from market_data_processor import (
    calculate_and_save_weekly_data,
    calculate_and_save_monthly_data
)

logger = logging.getLogger(__name__)


def run_analysis_task(task_id: str, top_n: int, selected_factors: Optional[List[str]] = None):
    """Background task for running stock analysis with database integration"""
    task = get_task(task_id)
    if not task:
        logger.error(f"Task {task_id} not found")
        return
    
    task.status = TaskStatus.RUNNING
    update_task_progress(task_id, 0.0, "开始分析任务")
    
    logger.info(f"Starting stock analysis for top {top_n} stocks...")
    
    # Step 1: Fetch spot data
    update_task_progress(task_id, 0.05, "获取实时行情数据")
    spot = fetch_spot()
    
    # Step 2: Save/update basic stock info
    update_task_progress(task_id, 0.1, "保存股票基本信息")
    save_stock_basic_info(spot)
    
    # Step 3: Get top stocks by trading volume
    update_task_progress(task_id, 0.15, "筛选热门股票")
    columns_to_select = ["代码", "名称"] if "名称" in spot.columns else ["代码"]
    if "成交额" in spot.columns:
        top_spot = spot.nlargest(top_n, "成交额").copy()
    else:
        top_spot = spot.head(top_n).copy()
    
    logger.info(f"Selected top {len(top_spot)} stocks by trading volume")
    stock_codes = top_spot["代码"].tolist()
    
    # Step 4: Check for missing daily data
    update_task_progress(task_id, 0.2, "检查历史数据完整性")
    missing_data = get_missing_daily_data(stock_codes)
    
    if missing_data:
        update_task_progress(task_id, 0.25, f"需要补充 {len(missing_data)} 个股票的历史数据")
        logger.info(f"Found {len(missing_data)} stocks with missing data")
        
        # Step 5: Fetch missing historical data
        history = {}
        for code, start_date in missing_data.items():
            days_needed = (date.today() - start_date).days
            code_history = fetch_history([code], days=days_needed, task_id=task_id)
            history.update(code_history)
        
        # Step 6: Save historical data to database
        update_task_progress(task_id, 0.4, "保存历史数据到数据库")
        save_daily_data(history, task_id)
    else:
        update_task_progress(task_id, 0.4, "所有股票数据都是最新的")
        logger.info("All stock data is up to date")
    
    # Step 5a: Save today's spot into daily table with limit-up text
    try:
        from stock_data_manager import save_spot_as_daily_data
        save_spot_as_daily_data(top_spot)
    except Exception as e:
        logger.warning(f"Skip saving spot as daily due to error: {e}")

    # Step 5b: Backfill missing limit-up texts for recent trading days
    try:
        from stock_data_manager import backfill_limit_up_texts_using_ths
        update_task_progress(task_id, 0.45, "回填历史涨停板类型")
        backfilled = backfill_limit_up_texts_using_ths(lookback_days=180)
        logger.info(f"Backfilled {backfilled} limit_up_text records in recent history")
    except Exception as e:
        logger.warning(f"Skip backfilling limit-up texts due to error: {e}")

    # Step 5: Calculate and save weekly data
    update_task_progress(task_id, 0.5, "计算并保存周K线数据")
    calculate_and_save_weekly_data(stock_codes, task_id)
    
    # Step 6: Calculate and save monthly data
    update_task_progress(task_id, 0.6, "计算并保存月K线数据")
    calculate_and_save_monthly_data(stock_codes, task_id)
    
    # Step 7: Load data from database for factor calculation
    update_task_progress(task_id, 0.7, "从数据库加载数据进行因子计算")
    
    # Load historical data from database for factor computation
    history_for_factors = load_daily_data_for_analysis(stock_codes, limit=60)
    
    # Step 8: Compute factors
    factor_msg = f"计算{'选定' if selected_factors else '所有'}因子"
    update_task_progress(task_id, 0.85, factor_msg)
    df = compute_factors(top_spot, history_for_factors, task_id=task_id, selected_factors=selected_factors)
    
    update_task_progress(task_id, 0.95, "数据清理和格式化")
    
    # Clean data for JSON serialization
    if not df.empty:
        # Replace NaN values with None
        df = df.replace({np.nan: None})
        # Ensure all numeric values are properly formatted
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            df[col] = df[col].astype(float, errors='ignore')
    
    data = df.to_dict(orient="records") if not df.empty else []
    
    # Complete task
    task.status = TaskStatus.COMPLETED
    task.progress = 1.0
    task.message = f"分析完成，数据已保存到数据库，共 {len(data)} 条结果"
    task.completed_at = datetime.now().isoformat()
    task.result = {
        "data": data,
        "count": len(data)
    }
    
    set_last_completed_task(task)
    logger.info(f"Analysis completed successfully with database integration. Found {len(data)} results")


def run_analysis_wrapper(task_id: str, top_n: int, selected_factors: Optional[List[str]] = None):
    """Wrapper to handle task errors properly"""
    error_occurred = False
    try:
        run_analysis_task(task_id, top_n, selected_factors)
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        handle_task_error(task_id, e)
        error_occurred = True
    
    if error_occurred:
        logger.error(f"Task {task_id} encountered an error and was marked as failed")


def create_analysis_task(top_n: int = 100, selected_factors: Optional[List[str]] = None) -> str:
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
    
    # Start background thread with error wrapper
    thread = threading.Thread(target=run_analysis_wrapper, args=(task_id, top_n, selected_factors))
    thread.daemon = True
    thread.start()
    
    return task_id