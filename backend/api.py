from __future__ import annotations
from typing import List
from fastapi import HTTPException
from models import RunRequest, RunResponse, TaskResult, TaskStatus, Message, ConceptTaskResult, AuthRequest, AuthResponse, User, get_session
from sqlmodel import select
from utils import (
    get_task, get_all_tasks, get_last_completed_task,
    get_concept_task, get_all_concept_tasks, get_last_completed_concept_task
)
from data_management.services import create_analysis_task
from utils import TASK_STOP_EVENTS, get_task

from data_management.concept_service import create_concept_collection_task, get_concepts_from_db
from factors import list_factors
from config import get_zai_credentials, set_zai_credentials, is_zai_configured


def read_root():
    return {"service": "quant-dashboard-backend", "status": "running"}


def run_analysis(request: RunRequest) -> RunResponse:
    """Start comprehensive stock analysis as background task"""
    task_id = create_analysis_task(request.top_n, request.selected_factors, request.collect_latest_data)
    
    return RunResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="分析任务已启动"
    )


def stop_analysis(task_id: str) -> TaskResult:
    """Signal a running task to stop and return its status"""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    stop_event = TASK_STOP_EVENTS.get(task_id)
    if not stop_event:
        raise HTTPException(status_code=400, detail="Task is not cancellable or already finished")

    # Signal cancellation
    stop_event.set()

    # Reflect status change immediately; the worker will mark completed/cancelled later.
    task.status = TaskStatus.RUNNING  # keep running until worker finalizes
    task.message = "已请求停止，正在清理..."
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
        extended=task.result.get("extended") if task.result else None,
        error=task.error
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
        extended=task.result.get("extended") if task.result else None,
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
        extended=last_task.result.get("extended") if last_task.result else None,
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
            extended=task.result.get("extended") if task.result else None,
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


def get_kline_amplitude_dashboard(n_days: int = 30):
    """Get K-line amplitude analysis data for dashboard"""
    from data_management.dashboard_service import get_kline_amplitude_analysis
    return get_kline_amplitude_analysis(n_days)


def run_extended_analysis():
    """Run standalone extended analysis focusing on sector analysis with caching"""
    from data_management.services import (
        get_cached_extended_analysis, 
        cache_extended_analysis, 
        is_extended_analysis_cache_valid
    )
    from extended_analysis import run_standalone_extended_analysis
    
    # Check if we have valid cached results
    if is_extended_analysis_cache_valid(max_age_minutes=30):
        cached_result = get_cached_extended_analysis()
        if cached_result:
            # Add cache indicator to response
            cached_result['from_cache'] = True
            return cached_result
    
    # Run fresh analysis
    result = run_standalone_extended_analysis()
    
    # Cache the result if successful
    if result and 'error' not in result:
        result['from_cache'] = False
        cache_extended_analysis(result)
    
    return result


# Configuration API functions

def get_zai_config():
    """Return current ZAI configuration state (mask sensitive values)."""
    bearer, cookie = get_zai_credentials()
    return {
        "configured": is_zai_configured(),
        # For security, do not expose full secrets. Only indicate presence and small preview.
        "ZAI_BEARER_TOKEN_preview": (bearer[:6] + "…" + bearer[-4:]) if bearer else "",
        "ZAI_COOKIE_STR_preview": (cookie[:6] + "…" + cookie[-4:]) if cookie else "",
    }


def update_zai_config(bearer_token: str, cookie_str: str) -> dict:
    """Update and persist ZAI credentials into backend/config.json."""
    if not bearer_token or not cookie_str:
        raise HTTPException(status_code=400, detail="Both bearer token and cookie string are required")
    try:
        set_zai_credentials(bearer_token, cookie_str)
        return {"success": True, "message": "ZAI 配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {e}")


def login_user(request: AuthRequest) -> AuthResponse:
    """User authentication with username and email"""
    try:
        with next(get_session()) as session:
            # Check if user exists with matching name and email
            statement = select(User).where(
                User.name == request.name,
                User.email == request.email
            )
            user = session.exec(statement).first()
            
            if user:
                # User exists, generate token
                token = f"token_{user.id}"
                return AuthResponse(
                    success=True,
                    token=token,
                    message="认证成功"
                )
            else:
                # Create new user
                new_user = User(name=request.name, email=request.email)
                session.add(new_user)
                session.commit()
                session.refresh(new_user)
                
                token = f"token_{new_user.id}"
                return AuthResponse(
                    success=True,
                    token=token,
                    message="用户创建成功，认证通过"
                )
                
    except Exception as e:
        return AuthResponse(
            success=False,
            message=f"认证失败: {str(e)}"
        )