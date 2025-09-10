from __future__ import annotations
import logging
import threading
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd
from sqlmodel import Session, select, func

from models import Task, TaskStatus, engine, DailyMarketData
from utils import (
    get_task, 
    update_task_progress,
)
from market_data import fetch_spot, fetch_history, compute_factors
from .stock_data_manager import (
    save_daily_data,
    save_stock_basic_info,
    load_daily_data_for_analysis,
    save_spot_as_daily_data,
    backfill_limit_up_texts_using_ths
)
from market_data import (
    calculate_and_save_weekly_data,
    calculate_and_save_monthly_data
)

logger = logging.getLogger(__name__)


def get_latest_trade_date_and_setup(task_id: str) -> tuple[Any, bool]:
    """获取最新交易日期并设置任务状态"""
    task = get_task(task_id)
    if not task:
        logger.error(f"Task {task_id} not found")
        return None, True
    
    task.status = TaskStatus.RUNNING
    update_task_progress(task_id, 0.0, "开始分析任务")
    
    logger.info(f"Starting stock analysis...")
    
    # 获取最新交易日和涨停数据（每次任务都重新获取）
    try:
        from .stock_data_manager import get_latest_trade_date_and_limit_map
        update_task_progress(task_id, 0.02, "获取最新交易日和涨停数据")
        
        # 强制重新获取最新数据，不使用缓存
        latest_trade_date, _ = get_latest_trade_date_and_limit_map(use_cache=False)
        logger.info(f"Latest trade date: {latest_trade_date}")
        return latest_trade_date, False
    except Exception as e:
        error_msg = f"无法获取最新交易日期：{e}"
        logger.error(error_msg)
        task.status = TaskStatus.FAILED
        task.message = error_msg
        task.completed_at = datetime.now().isoformat()
        return None, True


def collect_spot_data_and_select_stocks(task_id: str, top_n: int, latest_trade_date) -> tuple[pd.DataFrame, List[str], bool]:
    """收集实时数据并筛选热门股票"""
    update_task_progress(task_id, 0.05, f"获取实时行情数据 {latest_trade_date}")
    spot = fetch_spot()
    
    # 保存股票基本信息
    update_task_progress(task_id, 0.1, "保存股票基本信息")
    save_stock_basic_info(spot)
    
    # 筛选热门股票
    update_task_progress(task_id, 0.15, "筛选热门股票")
    if "成交额" in spot.columns:
        top_spot = spot.nlargest(top_n, "成交额").copy()
    else:
        top_spot = spot.head(top_n).copy()
    
    logger.info(f"Selected top {len(top_spot)} stocks by trading volume")
    stock_codes = top_spot["代码"].tolist()
    
    return top_spot, stock_codes, False


def check_and_upsert_spot_data(task_id: str, spot: pd.DataFrame, latest_trade_date) -> bool:
    """检查是否需要upsert spot数据到日K数据库"""
    update_task_progress(task_id, 0.18, "检查是否需要更新当日K线数据")
    
    should_upsert_spot = False
    with Session(engine) as session:
        # 检查是否有最新交易日的数据
        latest_data_count = session.exec(
            select(func.count(DailyMarketData.id))
            .where(DailyMarketData.date == latest_trade_date)
        ).first()
        # logger.info(f"Found {latest_data_count} records for latest_trade_date: {latest_trade_date}")
        
        # 获取前一个交易日并检查是否有数据
        previous_trade_date = latest_trade_date - timedelta(days=3 if latest_trade_date.weekday() == 0 else 1)
        # logger.info(f"latest_trade_date: {latest_trade_date} (weekday: {latest_trade_date.weekday()}), calculated previous_trade_date: {previous_trade_date}")
        previous_data_count = session.exec(
            select(func.count(DailyMarketData.id))
            .where(DailyMarketData.date == previous_trade_date)
        ).first()
        # logger.info(f"Found {previous_data_count} records for previous_trade_date: {previous_trade_date}")
        
        # 只有当今天有数据且前一个交易日也有数据时，才进行upsert
        if latest_data_count == 0:
            should_upsert_spot = False
            logger.info(f"No daily K data found for {latest_trade_date}, skipping spot data upsert, will fetch history instead")
        elif previous_data_count == 0:
            should_upsert_spot = False
            logger.info(f"No daily K data found for previous trading day {previous_trade_date}, skipping spot data upsert, will fetch history instead")
        else:
            should_upsert_spot = True
            logger.info(f"Found {latest_data_count} records for {latest_trade_date} and {previous_data_count} records for {previous_trade_date}, will upsert spot data")
    
    if should_upsert_spot:
        # 添加日期列到spot数据进行upsert
        spot_with_date = spot.copy()
        spot_with_date["日期"] = latest_trade_date
        
        update_task_progress(task_id, 0.2, "保存当日实时数据为K线数据")
        saved_count = save_spot_as_daily_data(spot_with_date)
        logger.info(f"Upserted {saved_count} spot records as daily K data for {latest_trade_date}")
    else:
        update_task_progress(task_id, 0.2, "跳过spot数据upsert，将通过fetch_history获取数据")
    
    return should_upsert_spot


def get_stocks_from_database(task_id: str, top_n: int) -> tuple[pd.DataFrame, List[str], bool]:
    """从数据库获取股票数据（当不收集最新数据时使用）"""
    update_task_progress(task_id, 0.15, "使用历史数据进行分析（跳过热点数据采集）")
    
    # 从数据库获取股票代码（最近有足够数据的股票）
    with Session(engine) as session:
        # 获取有足够历史数据的股票（至少35天用于因子计算）
        stocks_with_data = session.exec(
            select(DailyMarketData.code, func.count(DailyMarketData.id).label('record_count'))
            .group_by(DailyMarketData.code)
            .having(func.count(DailyMarketData.id) >= 35)  # 因子计算的最小值
            .order_by(func.count(DailyMarketData.id).desc())
            .limit(top_n * 2)  # 获取更多候选
        ).all()
        
        if stocks_with_data:
            # 获取这些股票的最新日期
            candidate_codes = [code for code, _ in stocks_with_data]
            recent_date = session.exec(
                select(func.max(DailyMarketData.date))
                .where(DailyMarketData.code.in_(candidate_codes))
            ).first()
            
            if recent_date:
                # 从候选股票中获取最近交易日按成交额排序的top股票
                from models import StockBasicInfo
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
                    top_spot = pd.DataFrame([
                        {"代码": code, "名称": name, "成交额": amount}
                        for code, amount, name in recent_stocks
                    ])
                    stock_codes = top_spot["代码"].tolist()
                    logger.info(f"Selected top {len(top_spot)} stocks with sufficient data from database (date: {recent_date})")
                    return top_spot, stock_codes, False
                else:
                    # 后备方案：使用前N个有足够数据的股票
                    from models import StockBasicInfo
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
                    return top_spot, stock_codes, False
            else:
                raise Exception("No recent data found for stocks with sufficient history.")
        else:
            raise Exception("No stocks found with sufficient historical data (>=35 days). Please run with 'collect_latest_data=True' first.")


def fetch_and_save_historical_data(task_id: str, stock_codes: List[str], should_upsert_spot: bool, collect_latest_data: bool, latest_trade_date: date) -> bool:
    """获取并保存历史数据"""
    if collect_latest_data:
        if not should_upsert_spot:
            # 如果没有最新交易日数据，获取历史数据进行回填
            update_task_progress(task_id, 0.25, "从外部API获取历史数据")
            
            # 直接获取所有股票的最近365天数据并upsert
            end_date_str = latest_trade_date.strftime("%Y%m%d")
            history = fetch_history(stock_codes, end_date=end_date_str, days=365, task_id=task_id)
            
            if history:
                update_task_progress(task_id, 0.35, "保存历史数据到数据库")
                save_daily_data(history)
                logger.info(f"Upserted historical data for {len(history)} stocks")
            else:
                logger.warning("No historical data fetched")
        else:
            # 如果upsert了spot数据，跳过外部API调用，因为我们有当前数据
            update_task_progress(task_id, 0.35, "跳过外部API调用（已upsert当日spot数据）")
            logger.info("Spot data upserted, skipping external API fetch for historical data")
    else:
        # 不收集最新数据时跳过外部API调用
        update_task_progress(task_id, 0.35, "使用数据库中的历史数据（跳过外部API调用）")
        logger.info("Using existing database historical data, skipping external API fetch")
    
    return False


def backfill_limit_up_data(task_id: str) -> bool:
    """回填历史涨停板类型"""
    try:
        update_task_progress(task_id, 0.45, "回填历史涨停板类型")
        backfilled = backfill_limit_up_texts_using_ths(lookback_days=180)
        logger.info(f"Backfilled {backfilled} limit_up_text records in recent history")
        return False
    except Exception as e:
        logger.warning(f"Skip backfilling limit-up texts due to error: {e}")
        return False


def calculate_weekly_monthly_data(task_id: str, stock_codes: List[str], should_upsert_spot: bool, collect_latest_data: bool) -> bool:
    """计算并保存周K线和月K线数据"""
    if collect_latest_data:
        if not should_upsert_spot:
            # 当我们获取了历史数据时计算周K线/月K线数据
            # Step 5a: 计算并保存周K线数据
            update_task_progress(task_id, 0.5, "计算并保存周K线数据")
            calculate_and_save_weekly_data(stock_codes, task_id)
            
            # Step 5b: 计算并保存月K线数据
            update_task_progress(task_id, 0.6, "计算并保存月K线数据")
            calculate_and_save_monthly_data(stock_codes, task_id)
        else:
            # 当我们只upsert了spot数据时跳过周K线/月K线计算
            update_task_progress(task_id, 0.6, "跳过周K线和月K线计算（仅upsert了spot数据）")
            logger.info("Skipping weekly/monthly data calculation since only spot data was upserted")
    else:
        # 使用现有数据时跳过周K线/月K线计算
        update_task_progress(task_id, 0.6, "使用现有数据，跳过周K线和月K线计算")
        logger.info("Skipping weekly/monthly data calculation since using existing database data")
    
    return False


def compute_factors_and_analysis(task_id: str, top_spot: pd.DataFrame, stock_codes: List[str], 
                                latest_trade_date, selected_factors: Optional[List[str]] = None) -> Dict[str, Any]:
    """计算因子并进行分析"""
    # Step 7: 从数据库加载数据进行因子计算
    update_task_progress(task_id, 0.7, "从数据库加载数据进行因子计算")
    
    # 从数据库加载历史数据用于因子计算
    history_for_factors = load_daily_data_for_analysis(stock_codes, limit=120)
    
    # Step 8: 计算因子
    factor_msg = f"计算{'选定' if selected_factors else '所有'}因子"
    update_task_progress(task_id, 0.85, factor_msg)
    df = compute_factors(top_spot, history_for_factors, task_id=task_id, selected_factors=selected_factors)
    
    update_task_progress(task_id, 0.95, "数据清理和格式化")
    
    # 清理数据用于JSON序列化
    if not df.empty:
        # 将NaN值替换为None
        df = df.replace({np.nan: None})
        # 确保所有数值都正确格式化
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            df[col] = df[col].astype(float, errors='ignore')
    
    data = df.to_dict(orient="records") if not df.empty else []

    return {
        "data": data,
        "count": len(data),
        "extended": extended or None,
    }


def complete_analysis_task(task_id: str, result: Dict[str, Any]) -> None:
    """完成分析任务"""
    from utils import set_last_completed_task
    from .services import ANALYSIS_RESULTS_CACHE, CACHE_LOCK, clear_extended_analysis_cache
    
    task = get_task(task_id)
    if not task:
        return
    
    # 完成任务
    task.status = TaskStatus.COMPLETED
    task.progress = 1.0
    task.message = f"分析完成，数据已保存到数据库，共 {result['count']} 条结果"
    task.completed_at = datetime.now().isoformat()
    task.result = result

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
            "data": result["data"],
            "count": result["count"],
            "extended": result["extended"],
        }

    # 新任务结果完成后，清除扩展分析缓存，确保下一次请求会重新计算
    try:
        clear_extended_analysis_cache()
    except Exception as e:
        logger.warning(f"Failed to clear extended analysis cache after task completion: {e}")

    set_last_completed_task(task)
    logger.info(f"Analysis completed successfully with database integration. Found {result['count']} results; extended={bool(result['extended'])}")


def run_analysis_task(task_id: str, top_n: int, selected_factors: Optional[List[str]] = None, 
                     collect_latest_data: bool = True, stop_event: Optional[threading.Event] = None):
    """主要的分析任务运行器"""
    
    def check_cancel() -> bool:
        if stop_event is not None and stop_event.is_set():
            task = get_task(task_id)
            if task:
                task.status = TaskStatus.CANCELLED
                task.message = "任务已取消"
                task.completed_at = datetime.now().isoformat()
            logger.info(f"Task {task_id} cancelled by user")
            return True
        return False
    
    # Step 1: 获取最新交易日期并设置任务
    latest_trade_date, has_error = get_latest_trade_date_and_setup(task_id)
    if has_error or check_cancel():
        return
    
    # 初始化是否需要upsert spot数据的标志
    should_upsert_spot = False
    
    if collect_latest_data:
        # Step 2: 收集实时数据并筛选股票
        top_spot, stock_codes, has_error = collect_spot_data_and_select_stocks(task_id, top_n, latest_trade_date)
        if has_error or check_cancel():
            return
        
        # Step 3: 检查并upsert spot数据
        should_upsert_spot = check_and_upsert_spot_data(task_id, top_spot, latest_trade_date)
        if check_cancel():
            return
    else:
        # 跳过热点数据收集，使用数据库中的现有数据
        top_spot, stock_codes, has_error = get_stocks_from_database(task_id, top_n)
        if has_error or check_cancel():
            return
    
    # Step 4: 获取历史数据
    has_error = fetch_and_save_historical_data(task_id, stock_codes, should_upsert_spot, collect_latest_data, latest_trade_date)
    if has_error or check_cancel():
        return

    update_task_progress(task_id, 0.4, "历史数据更新完成")
    if check_cancel():
        return

    # Step 5: 回填涨停板类型
    has_error = backfill_limit_up_data(task_id)
    if has_error or check_cancel():
        return

    # Step 6: 计算周K线和月K线数据
    has_error = calculate_weekly_monthly_data(task_id, stock_codes, should_upsert_spot, collect_latest_data)
    if has_error or check_cancel():
        return
    
    # Step 7-8: 计算因子并进行分析
    result = compute_factors_and_analysis(task_id, top_spot, stock_codes, latest_trade_date, selected_factors)
    if check_cancel():
        return

    # Step 9: 完成任务
    complete_analysis_task(task_id, result)