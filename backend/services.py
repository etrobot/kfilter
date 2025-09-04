from __future__ import annotations
import logging
import threading
from datetime import datetime, date, timedelta
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


def run_analysis_task(task_id: str, top_n: int, selected_factors: Optional[List[str]] = None, stop_event: Optional[threading.Event] = None):
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
    
    # Step 1: Fetch spot data
    update_task_progress(task_id, 0.05, "获取实时行情数据")
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
    columns_to_select = ["代码", "名称"] if "名称" in spot.columns else ["代码"]
    if "成交额" in spot.columns:
        top_spot = spot.nlargest(top_n, "成交额").copy()
    else:
        top_spot = spot.head(top_n).copy()
    
    logger.info(f"Selected top {len(top_spot)} stocks by trading volume")
    stock_codes = top_spot["代码"].tolist()
    
    # Step 4: Check for missing daily data
    update_task_progress(task_id, 0.2, "检查历史数据完整性")
    if check_cancel():
        return
    missing_data = get_missing_daily_data(stock_codes)
    
    if missing_data:
        update_task_progress(task_id, 0.25, f"需要补充 {len(missing_data)} 个股票的历史数据")
        logger.info(f"Found {len(missing_data)} stocks with missing data")
        if check_cancel():
            return
        
        # Step 5: Fetch missing historical data
        history = {}
        for code, start_date in missing_data.items():
            if check_cancel():
                return
            days_needed = (date.today() - start_date).days
            code_history = fetch_history([code], days=days_needed, task_id=task_id)
            history.update(code_history)
        
        # Step 6: Save historical data to database
        update_task_progress(task_id, 0.4, "保存历史数据到数据库")
        if check_cancel():
            return
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

    # Step 5: Calculate and save weekly data
    update_task_progress(task_id, 0.5, "计算并保存周K线数据")
    if check_cancel():
        return
    calculate_and_save_weekly_data(stock_codes, task_id)
    
    # Step 6: Calculate and save monthly data
    update_task_progress(task_id, 0.6, "计算并保存月K线数据")
    if check_cancel():
        return
    calculate_and_save_monthly_data(stock_codes, task_id)
    
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
    extended = {}
    try:
        from sqlmodel import Session, select
        from models import engine, ConceptInfo, ConceptStock, DailyMarketData
        with Session(engine) as session:
            # 1) Top 10 concepts by stock_count desc (or market_cap if available)
            top_concepts = session.exec(
                select(ConceptInfo).order_by(ConceptInfo.stock_count.desc()).limit(10)
            ).all() or []
            concept_codes = [c.code for c in top_concepts]
            extended["top_sector_codes"] = concept_codes

            if concept_codes:
                # 2) For those concepts, get all constituent stocks
                stocks = session.exec(
                    select(ConceptStock).where(ConceptStock.concept_code.in_(concept_codes))
                ).all() or []
                concept_map = {c.code: c.name for c in top_concepts}

                # 3) Count limit-up occurrences for each stock in recent window
                # use already imported date, timedelta
                today = date.today()
                window_start = today - timedelta(days=180)
                # Build counts using DailyMarketData where limit_status == 1
                # We'll fetch all records for candidate stocks then count
                # Prepare per-stock counts
                counts = {}
                # Get distinct stock codes
                stock_codes = list({s.stock_code for s in stocks})
                if stock_codes:
                    # Query all limit-up rows for those stocks in the window
                    rows = session.exec(
                        select(DailyMarketData.code, DailyMarketData.date)
                        .where(
                            DailyMarketData.code.in_(stock_codes),
                            DailyMarketData.date >= window_start,
                            DailyMarketData.date <= today,
                            DailyMarketData.limit_status == 1,
                        )
                    ).all() or []
                    for code_val, _ in rows:
                        counts[code_val] = counts.get(code_val, 0) + 1

                # 4) For each concept, find the stock with max limit_up_count
                from collections import defaultdict
                concept_best = defaultdict(list)  # concept_code -> [(code, count)]
                for s in stocks:
                    cnt = counts.get(s.stock_code, 0)
                    concept_best[s.concept_code].append((s.stock_code, cnt))
                ranking_candidates = []
                for ccode, items in concept_best.items():
                    if not items:
                        continue
                    # Best stock in this concept by limit_up_count desc
                    best_code, best_cnt = sorted(items, key=lambda x: x[1], reverse=True)[0]
                    # Skip concepts whose best stock has 0 limit-ups in window
                    if best_cnt <= 0:
                        continue
                    ranking_candidates.append((best_code, best_cnt, ccode))

                # 5) Aggregate per stock: merge all concepts the stock belongs to (only those with >0)
                from collections import defaultdict
                agg: dict[str, dict] = {}
                for code_val, cnt, ccode in ranking_candidates:
                    if cnt <= 0:
                        continue
                    if code_val not in agg:
                        agg[code_val] = {
                            "code": code_val,
                            "limit_up_count": int(cnt),
                            "concept_codes": [ccode],
                            "concept_names": [concept_map.get(ccode)] if concept_map.get(ccode) else []
                        }
                    else:
                        # Same stock from another concept, keep the max cnt and append concept
                        agg[code_val]["limit_up_count"] = max(int(cnt), agg[code_val]["limit_up_count"])
                        if ccode not in agg[code_val]["concept_codes"]:
                            agg[code_val]["concept_codes"].append(ccode)
                            cname = concept_map.get(ccode)
                            if cname:
                                agg[code_val]["concept_names"].append(cname)

                # 6) Build final ranking list sorted by limit_up_count desc
                final_ranking = []
                # Resolve stock name from current data
                name_map = {r.get("代码"): r.get("名称") for r in data if r.get("代码")}
                for code_val, info in agg.items():
                    final_ranking.append({
                        "code": code_val,
                        "name": name_map.get(code_val),
                        "limit_up_count": info["limit_up_count"],
                        "concept_code": info["concept_codes"][0] if info.get("concept_codes") else None,
                        "concept_name": info["concept_names"][0] if info.get("concept_names") else None,
                        "concept_codes": info.get("concept_codes"),
                        "concept_names": info.get("concept_names"),
                    })

                extended["limit_up_ranking"] = final_ranking
    except Exception as e:
        logger.warning(f"Extended analysis failed: {e}")

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

    set_last_completed_task(task)
    logger.info(f"Analysis completed successfully with database integration. Found {len(data)} results; extended={bool(extended)}")


def run_analysis_wrapper(task_id: str, top_n: int, selected_factors: Optional[List[str]] = None, stop_event: Optional[threading.Event] = None):
    """Wrapper to handle task errors properly and cleanup registries"""
    error_occurred = False
    try:
        run_analysis_task(task_id, top_n, selected_factors, stop_event=stop_event)
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
    
    # Prepare a stop event and thread, and register them
    stop_event = threading.Event()
    TASK_STOP_EVENTS[task_id] = stop_event
    
    # Start background thread with error wrapper
    thread = threading.Thread(target=run_analysis_wrapper, args=(task_id, top_n, selected_factors, stop_event))
    thread.daemon = True
    TASK_THREADS[task_id] = thread
    thread.start()
    
    return task_id