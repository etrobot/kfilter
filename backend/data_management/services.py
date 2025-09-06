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
from .analysis_task_runner import run_analysis_task

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