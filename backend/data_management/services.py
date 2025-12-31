from __future__ import annotations
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

import numpy as np
from models import Task, TaskStatus
from task_utils import (
    add_task, 
    get_task, 
    set_last_completed_task, 
    handle_task_error, 
    update_task_progress,
    TASK_STOP_EVENTS,
    TASK_THREADS
)
from .analysis_task_runner import run_analysis_task
from config import get_zai_credentials, is_zai_configured, get_zai_client_config as get_config_zai_client_config

logger = logging.getLogger(__name__)

# In-memory storage for calculation results
ANALYSIS_RESULTS_CACHE: Dict[str, Dict[str, Any]] = {}
EXTENDED_ANALYSIS_CACHE: Dict[str, Any] = {}  # 扩展分析缓存
CACHE_LOCK = threading.Lock()

# ZAI client configuration cache
_zai_client_config = None
_zai_config_lock = threading.Lock()

def get_zai_client_config() -> Optional[Dict[str, Any]]:
    """Get cached ZAI client configuration or load from config."""
    global _zai_client_config
    
    with _zai_config_lock:
        if _zai_client_config is None:
            try:
                if is_zai_configured():
                    # Get comprehensive configuration
                    _zai_client_config = get_config_zai_client_config()
                    logger.info("ZAI client configuration loaded from config")
                else:
                    logger.warning("ZAI credentials not configured")
                    _zai_client_config = {}
            except Exception as e:
                logger.error(f"Failed to load ZAI configuration: {e}")
                _zai_client_config = {}
        
        return _zai_client_config.copy() if _zai_client_config else None

def refresh_zai_client_config() -> None:
    """Refresh the cached ZAI client configuration."""
    global _zai_client_config
    
    with _zai_config_lock:
        _zai_client_config = None
        # Reload config directly without calling get_zai_client_config to avoid deadlock
        try:
            if is_zai_configured():
                # Get comprehensive configuration
                _zai_client_config = get_config_zai_client_config()
                logger.info("ZAI client configuration refreshed from config")
            else:
                logger.warning("ZAI credentials not configured during refresh")
                _zai_client_config = {}
        except Exception as e:
            logger.error(f"Failed to refresh ZAI configuration: {e}")
            _zai_client_config = {}


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


def get_cached_extended_analysis() -> Optional[Dict[str, Any]]:
    """Get cached extended analysis results."""
    with CACHE_LOCK:
        return EXTENDED_ANALYSIS_CACHE.copy() if EXTENDED_ANALYSIS_CACHE else None


def cache_extended_analysis(results: Dict[str, Any]) -> None:
    """Cache extended analysis results with timestamp."""
    with CACHE_LOCK:
        results['cached_at'] = datetime.now().isoformat()
        EXTENDED_ANALYSIS_CACHE.clear()
        EXTENDED_ANALYSIS_CACHE.update(results)


def clear_extended_analysis_cache() -> None:
    """Clear extended analysis cache."""
    with CACHE_LOCK:
        EXTENDED_ANALYSIS_CACHE.clear()


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


def create_analysis_task(top_n: int = 200, selected_factors: Optional[List[str]] = None, collect_latest_data: bool = True) -> str:
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