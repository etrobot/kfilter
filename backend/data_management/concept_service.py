from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from uuid import uuid4
from typing import Dict, List
from sqlmodel import Session, select, delete


from models import ConceptTask, TaskStatus, ConceptInfo, ConceptStock, engine
from utils import (
    get_concept_task,
    add_concept_task,
    handle_concept_task_error,
    update_concept_task_progress,
    set_last_completed_concept_task,
)
from market_data.concept10jqka import collect_concept_data

logger = logging.getLogger(__name__)


def clear_concept_tables_for_testing():
    """清空概念相关表（仅用于测试），用于验证新数据源"""
    try:
        with Session(engine) as session:
            # 先删除 ConceptStock，再删除 ConceptInfo（外键关系）
            session.exec(delete(ConceptStock))
            session.exec(delete(ConceptInfo))
            session.commit()
            logger.info("Concept tables cleared for testing")
    except Exception as e:
        logger.error(f"Failed to clear concept tables: {e}")
        raise


def collect_concepts_task(task_id: str, clear_db: bool = False):
    """Background task for collecting concept data from 10jqka

    Args:
        task_id: Task ID
        clear_db: If True, clear existing concept data before collecting (testing only)
    """
    task = get_concept_task(task_id)
    if not task:
        logger.error(f"Concept task {task_id} not found")
        return

    task.status = TaskStatus.RUNNING
    message = "开始采集概念数据（已清空旧数据）" if clear_db else "开始采集概念数据"
    update_concept_task_progress(task_id, 0.0, message)

    # Clear database if testing
    if clear_db:
        try:
            update_concept_task_progress(task_id, 0.05, "清空旧数据中")
            clear_concept_tables_for_testing()
        except Exception as e:
            logger.error(f"Failed to clear database for task {task_id}: {e}")
            handle_concept_task_error(task_id, e)
            return

    logger.info("Starting concept data collection from 10jqka...")

    concepts_data = []
    concept_stocks_data = []

    try:
        # Only collect concept boards from 10jqka (gn = 概念)
        url = "http://q.10jqka.com.cn/gn"

        update_concept_task_progress(task_id, 0.1, "正在采集概念板块")
        logger.info(f"Collecting concepts from {url}...")

        # Run async collection
        concepts_data, concept_stocks_data = asyncio.run(collect_concept_data(url))
        logger.info(
            f"采集到 {len(concepts_data)} 个概念，{len(concept_stocks_data)} 只成分股"
        )

        # Step 2: Upsert to database
        update_concept_task_progress(task_id, 0.9, "保存数据到数据库")

        with Session(engine) as session:
            # Upsert concept info
            for concept_data in concepts_data:
                existing = session.exec(
                    select(ConceptInfo).where(ConceptInfo.code == concept_data["code"])
                ).first()

                if existing:
                    # Update existing
                    existing.name = concept_data["name"]
                    existing.stock_count = concept_data["stock_count"]
                    existing.updated_at = datetime.now()
                else:
                    # Insert new
                    concept = ConceptInfo(**concept_data)
                    session.add(concept)

            # Delete old stocks for updated concepts, then insert new
            concept_codes = [c["code"] for c in concepts_data]
            old_stocks = session.exec(
                select(ConceptStock).where(ConceptStock.concept_code.in_(concept_codes))
            ).all()
            for old_stock in old_stocks:
                session.delete(old_stock)

            # Insert concept stocks
            for stock_data in concept_stocks_data:
                concept_stock = ConceptStock(**stock_data)
                session.add(concept_stock)

            session.commit()

        # Complete task
        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        task.message = f"采集完成，共采集 {len(concepts_data)} 个概念，{len(concept_stocks_data)} 个成分股"
        task.completed_at = datetime.now().isoformat()
        task.result = {
            "concepts_count": len(concepts_data),
            "stocks_count": len(concept_stocks_data),
        }

        set_last_completed_concept_task(task)
        logger.info(
            f"Concept data collection completed. Found {len(concepts_data)} concepts, {len(concept_stocks_data)} stocks"
        )

    except Exception as e:
        logger.error(f"Concept collection task {task_id} failed: {e}")
        handle_concept_task_error(task_id, e)


def collect_concepts_wrapper(task_id: str, clear_db: bool = False):
    """Wrapper to handle task errors properly

    Args:
        task_id: Task ID
        clear_db: If True, clear existing concept data before collecting (testing only)
    """
    error_occurred = False
    try:
        collect_concepts_task(task_id, clear_db=clear_db)
    except Exception as e:
        logger.error(f"Concept task {task_id} failed: {e}")
        handle_concept_task_error(task_id, e)
        error_occurred = True

    if error_occurred:
        logger.error(
            f"Concept task {task_id} encountered an error and was marked as failed"
        )


def create_concept_collection_task(clear_db: bool = False) -> str:
    """Create and start a new concept collection task

    Args:
        clear_db: If True, clear existing concept data before collecting (testing only)

    Returns:
        Task ID
    """
    task_id = str(uuid4())

    message = (
        "概念数据采集任务已创建，等待开始（将清空旧数据）"
        if clear_db
        else "概念数据采集任务已创建，等待开始"
    )
    task = ConceptTask(
        task_id=task_id,
        status=TaskStatus.PENDING,
        progress=0.0,
        message=message,
        created_at=datetime.now().isoformat(),
    )

    add_concept_task(task)

    # Start background thread with error wrapper
    thread = threading.Thread(target=collect_concepts_wrapper, args=(task_id, clear_db))
    thread.daemon = True
    thread.start()

    return task_id


def get_concepts_from_db() -> List[Dict]:
    """Get all concepts from database"""
    with Session(engine) as session:
        concepts = session.exec(select(ConceptInfo)).all()
        return [
            {
                "code": concept.code,
                "name": concept.name,
                "market_cap": concept.market_cap,
                "stock_count": concept.stock_count,
                "created_at": (
                    concept.created_at.isoformat() if concept.created_at else None
                ),
                "updated_at": (
                    concept.updated_at.isoformat() if concept.updated_at else None
                ),
            }
            for concept in concepts
        ]


def get_stocks_sectors_from_extended_analysis(
    stock_codes: List[str],
    extended_results_path: str = "extended_analysis_results.json",
) -> Dict[str, tuple[str, int]]:
    """从扩展分析结果中获取股票所属板块及其评分排名"""
    import json
    import os

    try:
        # 读取扩展分析结果文件
        if not os.path.exists(extended_results_path):
            logger.warning(
                f"Extended analysis results file not found: {extended_results_path}"
            )
            return {}

        with open(extended_results_path, "r", encoding="utf-8") as f:
            extended_data = json.load(f)

        # 获取所有板块
        sectors = extended_data.get("sectors", [])

        # 构建股票到板块的映射
        stock_to_sector_map = {}

        # 按评分顺序处理每个板块（排名从1开始）
        for rank, sector_info in enumerate(sectors, 1):
            sector_name = sector_info["sector_name"]

            # 处理该板块的所有股票
            for stock_code in sector_info["stocks"]:
                # 确保股票代码格式一致
                clean_code = (
                    stock_code[2:]
                    if len(stock_code) == 8 and stock_code[:2] in ["sz", "sh"]
                    else stock_code
                )
                if clean_code in stock_codes:
                    # 如果股票已经在更高排名的板块中，跳过（只保留最高排名板块）
                    if clean_code not in stock_to_sector_map:
                        stock_to_sector_map[clean_code] = (sector_name, rank)

        return stock_to_sector_map

    except Exception as e:
        logger.error(f"Error reading extended analysis results: {e}")
        return {}
