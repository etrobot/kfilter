from __future__ import annotations
import logging
import threading
import time as t
from datetime import datetime
from uuid import uuid4
from typing import Dict, List, Optional
from sqlmodel import Session, select

import pandas as pd
import akshare as ak

from models import ConceptTask, TaskStatus, ConceptInfo, ConceptStock, engine
from utils import (
    get_concept_task, 
    add_concept_task, 
    handle_concept_task_error, 
    update_concept_task_progress,
    set_last_completed_concept_task
)

logger = logging.getLogger(__name__)


def collect_concepts_task(task_id: str):
    """Background task for collecting concept data"""
    task = get_concept_task(task_id)
    if not task:
        logger.error(f"Concept task {task_id} not found")
        return
    
    task.status = TaskStatus.RUNNING
    update_concept_task_progress(task_id, 0.0, "开始采集概念数据")
    
    logger.info("Starting concept data collection...")
    
    concepts_data = []
    concept_stocks_data = []
    
    try:
        # Step 1: Get concept data
        update_concept_task_progress(task_id, 0.1, "获取板块概念数据")
        stock_board_concept_name_em_df = ak.stock_board_concept_name_em()
        logger.info(f"获取到 {len(stock_board_concept_name_em_df)} 个板块概念")
        
        # Sort by market cap
        stock_board_concept_name_em_df.sort_values(by='总市值', ascending=True, inplace=True)
        
        total_concepts = len(stock_board_concept_name_em_df)
        processed_concepts = 0
        
        for idx, concept_row in stock_board_concept_name_em_df.iterrows():
            update_concept_task_progress(
                task_id, 
                0.1 + 0.8 * processed_concepts / total_concepts, 
                f"处理板块: {concept_row['板块名称']} ({processed_concepts + 1}/{total_concepts})"
            )
            
            # Filter out very large concepts and those with '昨日' in name
            if int(concept_row['总市值']) > 10000000000000 or '昨日' in concept_row['板块名称']:
                logger.debug(f"跳过板块: {concept_row['板块名称']} (市值过大或包含'昨日')")
                processed_concepts += 1
                continue
            
            # Get constituent stocks
            try:
                concept_stocks_df = ak.stock_board_concept_cons_em(symbol=concept_row['板块代码'])
                
                # Skip concepts with too many stocks
                if len(concept_stocks_df) > 99:
                    logger.debug(f"跳过板块: {concept_row['板块名称']} (成分股过多: {len(concept_stocks_df)})")
                    processed_concepts += 1
                    continue
                
                logger.info(f"板块 {concept_row['板块名称']} 包含 {len(concept_stocks_df)} 只股票")
                
                # Add concept info
                concepts_data.append({
                    'code': concept_row['板块代码'],
                    'name': concept_row['板块名称'],
                    'market_cap': float(concept_row['总市值']),
                    'stock_count': len(concept_stocks_df)
                })
                
                # Add constituent stocks
                for _, stock_row in concept_stocks_df.iterrows():
                    concept_stocks_data.append({
                        'concept_code': concept_row['板块代码'],
                        'stock_code': stock_row['代码']
                    })
                
                # Rate limiting
                if processed_concepts % 20 == 0 and processed_concepts > 0:
                    logger.info("暂停15秒避免请求过于频繁")
                    t.sleep(15)
                
            except Exception as e:
                logger.warning(f"获取板块 {concept_row['板块名称']} 成分股失败: {e}")
            
            processed_concepts += 1
        
        # Step 2: Save to database
        update_concept_task_progress(task_id, 0.9, "保存数据到数据库")
        
        with Session(engine) as session:
            # Clear existing data
            existing_stocks = session.exec(select(ConceptStock)).all()
            for stock in existing_stocks:
                session.delete(stock)
            
            existing_concepts = session.exec(select(ConceptInfo)).all()
            for concept in existing_concepts:
                session.delete(concept)
            
            # Insert concept info
            for concept_data in concepts_data:
                concept = ConceptInfo(**concept_data)
                session.add(concept)
            
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
            "stocks_count": len(concept_stocks_data)
        }
        
        set_last_completed_concept_task(task)
        logger.info(f"Concept data collection completed. Found {len(concepts_data)} concepts, {len(concept_stocks_data)} stocks")
        
    except Exception as e:
        logger.error(f"Concept collection task {task_id} failed: {e}")
        handle_concept_task_error(task_id, e)


def collect_concepts_wrapper(task_id: str):
    """Wrapper to handle task errors properly"""
    error_occurred = False
    try:
        collect_concepts_task(task_id)
    except Exception as e:
        logger.error(f"Concept task {task_id} failed: {e}")
        handle_concept_task_error(task_id, e)
        error_occurred = True
    
    if error_occurred:
        logger.error(f"Concept task {task_id} encountered an error and was marked as failed")


def create_concept_collection_task() -> str:
    """Create and start a new concept collection task"""
    task_id = str(uuid4())
    
    task = ConceptTask(
        task_id=task_id,
        status=TaskStatus.PENDING,
        progress=0.0,
        message="概念数据采集任务已创建，等待开始",
        created_at=datetime.now().isoformat()
    )
    
    add_concept_task(task)
    
    # Start background thread with error wrapper
    thread = threading.Thread(target=collect_concepts_wrapper, args=(task_id,))
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
                "created_at": concept.created_at.isoformat() if concept.created_at else None,
                "updated_at": concept.updated_at.isoformat() if concept.updated_at else None
            }
            for concept in concepts
        ]