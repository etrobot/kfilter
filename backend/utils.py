from __future__ import annotations
import logging
import threading
from datetime import datetime
from typing import Dict, Optional
from models import Task, TaskStatus, ConceptTask

# Types
from typing import Optional as _Optional
import threading as _threading

# Configure logging
logging.basicConfig(level=logging.INFO)
# Suppress verbose SQLAlchemy logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Global task storage
TASKS: Dict[str, Task] = {}
LAST_COMPLETED_TASK: Optional[Task] = None

# Thread and cancellation management for analysis tasks
TASK_THREADS: Dict[str, _threading.Thread] = {}
TASK_STOP_EVENTS: Dict[str, _threading.Event] = {}

# Thread and cancellation management for extended analysis tasks
EXTENDED_ANALYSIS_THREADS: Dict[str, _threading.Thread] = {}
EXTENDED_ANALYSIS_STOP_EVENTS: Dict[str, _threading.Event] = {}

# Global concept task storage
CONCEPT_TASKS: Dict[str, ConceptTask] = {}
LAST_COMPLETED_CONCEPT_TASK: Optional[ConceptTask] = None


def update_task_progress(task_id: str, progress: float, message: str):
    """Update task progress"""
    if task_id in TASKS:
        TASKS[task_id].progress = progress
        TASKS[task_id].message = message
        logger.info(f"Task {task_id}: {progress:.1%} - {message}")


def handle_task_error(task_id: str, error: Exception):
    """Handle task errors by updating task status"""
    task = TASKS[task_id]
    task.status = TaskStatus.FAILED
    task.error = str(error)
    task.message = f"分析失败: {str(error)}"
    task.completed_at = datetime.now().isoformat()


def get_task(task_id: str) -> Optional[Task]:
    """Get task by ID"""
    return TASKS.get(task_id)


def add_task(task: Task) -> None:
    """Add task to storage"""
    TASKS[task.task_id] = task


def set_last_completed_task(task: Task) -> None:
    """Set the last completed task"""
    global LAST_COMPLETED_TASK
    LAST_COMPLETED_TASK = task


def get_last_completed_task() -> Optional[Task]:
    """Get the last completed task"""
    return LAST_COMPLETED_TASK


def get_all_tasks() -> Dict[str, Task]:
    """Get all tasks"""
    return TASKS


# Concept task management functions

def update_concept_task_progress(task_id: str, progress: float, message: str):
    """Update concept task progress"""
    if task_id in CONCEPT_TASKS:
        CONCEPT_TASKS[task_id].progress = progress
        CONCEPT_TASKS[task_id].message = message
        logger.info(f"Concept task {task_id}: {progress:.1%} - {message}")


def handle_concept_task_error(task_id: str, error: Exception):
    """Handle concept task errors by updating task status"""
    task = CONCEPT_TASKS[task_id]
    task.status = TaskStatus.FAILED
    task.error = str(error)
    task.message = f"概念数据采集失败: {str(error)}"
    task.completed_at = datetime.now().isoformat()


def get_concept_task(task_id: str) -> Optional[ConceptTask]:
    """Get concept task by ID"""
    return CONCEPT_TASKS.get(task_id)


def add_concept_task(task: ConceptTask) -> None:
    """Add concept task to storage"""
    CONCEPT_TASKS[task.task_id] = task


def set_last_completed_concept_task(task: ConceptTask) -> None:
    """Set the last completed concept task"""
    global LAST_COMPLETED_CONCEPT_TASK
    LAST_COMPLETED_CONCEPT_TASK = task


def get_last_completed_concept_task() -> Optional[ConceptTask]:
    """Get the last completed concept task"""
    return LAST_COMPLETED_CONCEPT_TASK


def get_all_concept_tasks() -> Dict[str, ConceptTask]:
    """Get all concept tasks"""
    return CONCEPT_TASKS