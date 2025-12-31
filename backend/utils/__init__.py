"""
Utils module for backend utilities
"""

from .quotation import stock_zh_a_hist_tx_period, fetch_hot_spot

# Import all task management functions from task_utils.py in parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from task_utils import (
    get_task,
    get_all_tasks,
    get_last_completed_task,
    get_concept_task,
    get_all_concept_tasks,
    get_last_completed_concept_task,
    EXTENDED_ANALYSIS_THREADS,
    EXTENDED_ANALYSIS_STOP_EVENTS,
    add_extended_analysis_task,
    update_extended_analysis_task,
    get_extended_analysis_task,
    get_running_extended_analysis_task,
    complete_extended_analysis_task,
    get_all_extended_analysis_tasks,
    LAST_COMPLETED_EXTENDED_ANALYSIS,
    update_task_progress,
    handle_task_error,
    add_task,
    set_last_completed_task,
    update_concept_task_progress,
    handle_concept_task_error,
    add_concept_task,
    set_last_completed_concept_task,
    TASK_THREADS,
    TASK_STOP_EVENTS,
)

__all__ = [
    'stock_zh_a_hist_tx_period', 
    'fetch_hot_spot',
    'get_task',
    'get_all_tasks',
    'get_last_completed_task',
    'get_concept_task',
    'get_all_concept_tasks',
    'get_last_completed_concept_task',
    'EXTENDED_ANALYSIS_THREADS',
    'EXTENDED_ANALYSIS_STOP_EVENTS',
    'add_extended_analysis_task',
    'update_extended_analysis_task',
    'get_extended_analysis_task',
    'get_running_extended_analysis_task',
    'complete_extended_analysis_task',
    'get_all_extended_analysis_tasks',
    'LAST_COMPLETED_EXTENDED_ANALYSIS',
    'update_task_progress',
    'handle_task_error',
    'add_task',
    'set_last_completed_task',
    'update_concept_task_progress',
    'handle_concept_task_error',
    'add_concept_task',
    'set_last_completed_concept_task',
    'TASK_THREADS',
    'TASK_STOP_EVENTS',
]
