from __future__ import annotations
from typing import List
from fastapi import HTTPException
from models import RunRequest, RunResponse, TaskResult, TaskStatus, Message, ConceptTaskResult
from utils import (
    get_task, get_all_tasks, get_last_completed_task,
    get_concept_task, get_all_concept_tasks, get_last_completed_concept_task
)
from services import create_analysis_task
from concept_service import create_concept_collection_task, get_concepts_from_db
from factors import list_factors


def read_root():
    return {"service": "quant-dashboard-backend", "status": "running"}


def run_analysis(request: RunRequest) -> RunResponse:
    """Start comprehensive stock analysis as background task"""
    task_id = create_analysis_task(request.top_n, request.selected_factors)
    
    return RunResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="分析任务已启动"
    )


def get_task_status(task_id: str) -> TaskResult:
    """Get status of a specific task"""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResult(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        message=task.message,
        created_at=task.created_at,
        completed_at=task.completed_at,
        top_n=task.top_n,
        selected_factors=task.selected_factors,
        data=task.result["data"] if task.result else None,
        count=task.result["count"] if task.result else None,
        error=task.error
    )


def get_latest_results() -> TaskResult | Message:
    """Get the latest completed task results"""
    last_task = get_last_completed_task()
    if not last_task:
        return Message(message="No results yet. POST /run to start a calculation.")
    
    return TaskResult(
        task_id=last_task.task_id,
        status=last_task.status,
        progress=last_task.progress,
        message=last_task.message,
        created_at=last_task.created_at,
        completed_at=last_task.completed_at,
        top_n=last_task.top_n,
        selected_factors=last_task.selected_factors,
        data=last_task.result["data"] if last_task.result else None,
        count=last_task.result["count"] if last_task.result else None,
        error=last_task.error
    )


def list_all_tasks() -> List[TaskResult]:
    """List all tasks"""
    all_tasks = get_all_tasks()
    return [
        TaskResult(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            message=task.message,
            created_at=task.created_at,
            completed_at=task.completed_at,
            top_n=task.top_n,
            selected_factors=task.selected_factors,
            data=task.result["data"] if task.result else None,
            count=task.result["count"] if task.result else None,
            error=task.error
        ) for task in all_tasks.values()
    ]


# Concept API functions

def collect_concepts() -> RunResponse:
    """Start concept data collection as background task"""
    task_id = create_concept_collection_task()
    
    return RunResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="概念数据采集任务已启动"
    )


def get_concept_task_status(task_id: str) -> ConceptTaskResult:
    """Get status of a specific concept task"""
    task = get_concept_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Concept task not found")
    
    return ConceptTaskResult(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        message=task.message,
        created_at=task.created_at,
        completed_at=task.completed_at,
        concepts_count=task.result["concepts_count"] if task.result else None,
        stocks_count=task.result["stocks_count"] if task.result else None,
        error=task.error
    )


def get_latest_concept_results() -> ConceptTaskResult | Message:
    """Get the latest completed concept task results"""
    last_task = get_last_completed_concept_task()
    if not last_task:
        return Message(message="No concept collection results yet. POST /concepts/collect to start collection.")
    
    return ConceptTaskResult(
        task_id=last_task.task_id,
        status=last_task.status,
        progress=last_task.progress,
        message=last_task.message,
        created_at=last_task.created_at,
        completed_at=last_task.completed_at,
        concepts_count=last_task.result["concepts_count"] if last_task.result else None,
        stocks_count=last_task.result["stocks_count"] if last_task.result else None,
        error=last_task.error
    )


def list_all_concept_tasks() -> List[ConceptTaskResult]:
    """List all concept tasks"""
    all_tasks = get_all_concept_tasks()
    return [
        ConceptTaskResult(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            message=task.message,
            created_at=task.created_at,
            completed_at=task.completed_at,
            concepts_count=task.result["concepts_count"] if task.result else None,
            stocks_count=task.result["stocks_count"] if task.result else None,
            error=task.error
        ) for task in all_tasks.values()
    ]


def get_concepts_list():
    """Get list of all concepts with details"""
    concepts = get_concepts_from_db()
    return {
        "concepts": concepts,
        "total": len(concepts)
    }