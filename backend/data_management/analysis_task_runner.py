from __future__ import annotations
import logging
import threading
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd
from sqlmodel import Session, select, func

from models import Task, TaskStatus, engine, DailyMarketData
from task_utils import (
    get_task, 
    update_task_progress,
)
from market_data import fetch_hot_spot, fetch_history, compute_factors, fetch_dragon_tiger_data
from .stock_data_manager import (
    save_daily_data,
    save_stock_basic_info,
    load_daily_data_for_analysis,
    save_spot_as_daily_data,
    backfill_limit_up_texts_using_ths
)
from .concept_service import get_stocks_sectors_from_extended_analysis
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
    spot = fetch_hot_spot()
    
    # 保存股票基本信息
    update_task_progress(task_id, 0.1, "保存股票基本信息")
    save_stock_basic_info(spot)
    
    stock_codes = spot["代码"].tolist()
    
    return spot, stock_codes, False


def check_and_upsert_spot_data(task_id: str,stock_codes: List[str], spot: pd.DataFrame, latest_trade_date) -> bool:
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

        # 检查是否所有代码都有数据
        has_all_codes_data = session.exec(
            select(func.count(DailyMarketData.id))
            .where(DailyMarketData.code.in_(stock_codes))
        ).all()
        logger.info(f"Found {has_all_codes_data} records for {stock_codes}")

        if len(has_all_codes_data) != len(stock_codes):
            should_upsert_spot = False
            logger.info(f"Not all codes have daily K data, will upsert spot data")
        
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
                # 从候选股票中获取最近交易日按成交额排序的股票（不依赖StockBasicInfo）
                recent_stocks = session.exec(
                    select(DailyMarketData.code, DailyMarketData.amount)
                    .where(
                        DailyMarketData.date == recent_date,
                        DailyMarketData.code.in_(candidate_codes)
                    )
                    .order_by(DailyMarketData.amount.desc())
                ).all()
                
                if recent_stocks:
                    top_spot = pd.DataFrame([
                        {"代码": code, "名称": code, "成交额": amount}
                        for code, amount in recent_stocks
                    ])
                    stock_codes = top_spot["代码"].tolist()
                    logger.info(f"Selected top {len(top_spot)} stocks with sufficient data from database (date: {recent_date})")
                    return top_spot, stock_codes, False
                else:
                    # 后备方案：直接使用候选股票代码
                    top_spot = pd.DataFrame([
                        {"代码": code, "名称": code}
                        for code in candidate_codes
                    ])
                    stock_codes = top_spot["代码"].tolist()
                    logger.info(f"Using fallback: selected {len(top_spot)} stocks with sufficient data")
                    return top_spot, stock_codes, False
            else:
                raise Exception("No recent data found for stocks with sufficient history.")
        else:
            raise Exception("No stocks found with sufficient historical data (>=35 days). Please run with 'collect_latest_data=True' first.")


def fetch_and_save_historical_data(task_id: str, stock_codes: List[str], should_upsert_spot: bool, collect_latest_data: bool, latest_trade_date: date, stop_event: Optional[threading.Event] = None) -> bool:
    """获取并保存历史数据 - 改进为批量处理，获取一批存一批"""
    if collect_latest_data:
        if not should_upsert_spot:
            # 如果没有最新交易日数据，获取历史数据进行回填
            update_task_progress(task_id, 0.25, "从外部API分批获取历史数据")
            
            end_date_str = latest_trade_date.strftime("%Y%m%d")
            total_stocks = len(stock_codes)
            
            logger.info(f"开始逐个获取历史数据，总共 {total_stocks} 个股票")
            
            successful_count = 0
            failed_count = 0
            
            for i, stock_code in enumerate(stock_codes):
                # 检查任务是否被取消
                if stop_event and stop_event.is_set():
                    logger.info(f"任务被取消，已处理 {successful_count} 个股票")
                    return True
                
                # 更新进度
                progress = 0.25 + (0.1 * i / total_stocks)  # 从0.25到0.35
                update_task_progress(task_id, progress, f"获取第 {i+1}/{total_stocks} 个股票历史数据: {stock_code}")
                
                try:
                    # 获取单个股票的历史数据（不传递task_id避免内部进度显示干扰）
                    stock_history = fetch_history([stock_code], end_date=end_date_str, days=365, task_id=None)
                    
                    if stock_history:
                        # 立即保存单个股票的数据
                        save_daily_data(stock_history)
                        logger.info(f"第 {i+1}/{total_stocks} 个股票 {stock_code} 历史数据保存完成，包含 {len(stock_history)} 条记录")
                        successful_count += 1
                    else:
                        logger.warning(f"第 {i+1}/{total_stocks} 个股票 {stock_code} 未获取到历史数据")
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"第 {i+1}/{total_stocks} 个股票 {stock_code} 历史数据获取/保存失败: {e}")
                    failed_count += 1
                    # 继续处理下一个股票，不中断整个流程
                    continue
            
            update_task_progress(task_id, 0.35, f"历史数据获取完成，成功 {successful_count} 个，失败 {failed_count} 个")
            logger.info(f"历史数据获取完成：成功 {successful_count}/{total_stocks} 个股票")
            
            # 如果失败股票过多，记录警告
            if failed_count > successful_count:
                logger.warning(f"历史数据获取失败股票较多: {failed_count}/{total_stocks}")
            
            # 只要有成功的股票就继续，不因为部分失败而终止
            if successful_count == 0:
                logger.error("所有股票都获取失败，无法继续分析")
                return True  # 返回错误
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


def compute_factors_and_analysis(task_id: str, stock_codes: List[str], 
                                latest_trade_date, selected_factors: Optional[List[str]] = None) -> Dict[str, Any]:
    """计算因子并进行分析"""
    # Step 7: 从数据库加载数据进行因子计算
    update_task_progress(task_id, 0.7, "从数据库加载数据进行因子计算")
    
    print(f"🔍 compute_factors_and_analysis: 分析 {len(stock_codes)} 个股票")
    
    # 从数据库加载历史数据用于因子计算
    history_for_factors = load_daily_data_for_analysis(stock_codes, limit=120)
    
    # 直接从数据库构建所有股票的spot数据
    print(f"🔧 从数据库构建 {len(stock_codes)} 个股票的spot数据...")
    
    from models import StockBasicInfo
    from sqlmodel import Session, select
    
    complete_spot_data = []
    
    # 从数据库获取所有股票的基本信息和最新价格
    with Session(engine) as session:
        for code in stock_codes:
            # 获取股票名称
            stock_info = session.exec(
                select(StockBasicInfo.name).where(StockBasicInfo.code == code)
            ).first()
            
            # 获取最新价格和成交额
            latest_data = session.exec(
                select(DailyMarketData.close_price, DailyMarketData.amount)
                .where(DailyMarketData.code == code)
                .order_by(DailyMarketData.date.desc())
                .limit(1)
            ).first()
            
            complete_spot_data.append({
                "代码": code,
                "名称": stock_info or code,
                "最新价": latest_data[0] if latest_data else 0,
                "成交额": latest_data[1] if latest_data else 0
            })
    
    # 创建完整的DataFrame
    complete_spot = pd.DataFrame(complete_spot_data)
    print(f"✅ 构建的spot数据包含 {len(complete_spot)} 个股票")
    
    # Step 8: 计算因子
    factor_msg = f"计算{'选定' if selected_factors else '所有'}因子"
    update_task_progress(task_id, 0.85, factor_msg)
    df = compute_factors(complete_spot, history_for_factors, task_id=task_id, selected_factors=selected_factors)
    
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
    
    # 添加板块信息和排名前缀（从扩展分析结果获取）
    if data:
        update_task_progress(task_id, 0.97, "添加板块信息和排名前缀")
        stock_codes_for_sectors = [record.get('代码') for record in data if '代码' in record]
        sectors_map = get_stocks_sectors_from_extended_analysis(stock_codes_for_sectors)
        
        # 为每条记录添加所属板块（带排名前缀）
        for record in data:
            stock_code = record.get('代码')
            if stock_code and stock_code in sectors_map:
                sector_name, rank = sectors_map[stock_code]
                # 在所属板块字段中添加排名前缀（如：#01英伟达概念）
                record['所属板块'] = f"{rank:02d}-{sector_name}"

    return {
        "data": data,
        "count": len(data),
    }


def complete_analysis_task(task_id: str, result: Dict[str, Any]) -> None:
    """完成分析任务"""
    import json
    import os
    from task_utils import set_last_completed_task
    from .services import ANALYSIS_RESULTS_CACHE, CACHE_LOCK
    
    task = get_task(task_id)
    if not task:
        return
    
    # 完成任务
    task.status = TaskStatus.COMPLETED
    task.progress = 1.0
    task.message = f"分析完成，数据已保存到数据库，共 {result['count']} 条结果"
    task.completed_at = datetime.now().isoformat()
    task.result = result

    # Prepare full result data for JSON and cache
    full_result = {
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
        "from_cache": False
    }

    # Store results in memory cache for frontend access
    with CACHE_LOCK:
        ANALYSIS_RESULTS_CACHE[task_id] = full_result.copy()

    # Save results to JSON file for persistence across server restarts
    try:
        json_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ranking.json")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(full_result, f, ensure_ascii=False, indent=2)
        logger.info(f"Analysis results saved to {json_file_path}")
    except Exception as e:
        logger.warning(f"Failed to save analysis results to JSON file: {e}")

    set_last_completed_task(task)
    logger.info(f"Analysis completed successfully with database integration. Found {result['count']} results")


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
        logger.info(f"热点股票数量: {len(stock_codes)}")
        
        dragon_tiger_data = fetch_dragon_tiger_data(
            page_number=1, page_size=100, statistics_cycle="04"
        )
        dragon_tiger_codes = dragon_tiger_data["代码"].tolist()
        logger.info(f"龙虎榜股票数量: {len(dragon_tiger_codes)}")
        
        # 保存龙虎榜股票的基本信息到StockBasicInfo
        save_stock_basic_info(dragon_tiger_data)
        
        # 合并前记录总数
        total_before_dedup = len(stock_codes) + len(dragon_tiger_codes)
        logger.info(f"合并前总股票数: {total_before_dedup} (热点:{len(stock_codes)} + 龙虎榜:{len(dragon_tiger_codes)})")
        
        # 合并并去重
        stock_codes = list(set(stock_codes + dragon_tiger_codes))
        logger.info(f"去重后最终股票数: {len(stock_codes)} (去除了 {total_before_dedup - len(stock_codes)} 个重复)")
        print('number:', len(stock_codes))
        
        if has_error or check_cancel():
            return
        
        # Step 3: 检查并upsert spot数据
        should_upsert_spot = check_and_upsert_spot_data(task_id, stock_codes, top_spot, latest_trade_date)
        if check_cancel():
            return
    else:
        # 跳过热点数据收集，使用数据库中的现有数据
        top_spot, stock_codes, has_error = get_stocks_from_database(task_id, top_n)
        if has_error or check_cancel():
            return

    
    # Step 4: 获取历史数据
    has_error = fetch_and_save_historical_data(task_id, stock_codes, should_upsert_spot, collect_latest_data, latest_trade_date, stop_event)
    if has_error or check_cancel():
        return

    update_task_progress(task_id, 0.4, "历史数据更新完成")
    if check_cancel():
        return

    # Step 5: 回填涨停板类型
    if collect_latest_data:
        has_error = backfill_limit_up_data(task_id)
        if has_error or check_cancel():
            return

    # Step 6: 计算周K线和月K线数据
    has_error = calculate_weekly_monthly_data(task_id, stock_codes, should_upsert_spot, collect_latest_data)
    if has_error or check_cancel():
        return
    
    # Step 7-8: 计算因子并进行分析
    result = compute_factors_and_analysis(task_id, stock_codes, latest_trade_date, selected_factors)
    if check_cancel():
        return

    # Step 9: 完成任务
    complete_analysis_task(task_id, result)