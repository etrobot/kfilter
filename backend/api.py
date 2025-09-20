from __future__ import annotations
from typing import List
from fastapi import HTTPException
from models import RunRequest, RunResponse, TaskResult, TaskStatus, Message, ConceptTaskResult, AuthRequest, AuthResponse, User, get_session
from sqlmodel import select, func
from utils import (
    get_task, get_all_tasks, get_last_completed_task,
    get_concept_task, get_all_concept_tasks, get_last_completed_concept_task,
    EXTENDED_ANALYSIS_THREADS, EXTENDED_ANALYSIS_STOP_EVENTS,
    add_extended_analysis_task, update_extended_analysis_task, 
    get_extended_analysis_task, get_running_extended_analysis_task,
    complete_extended_analysis_task, get_all_extended_analysis_tasks
)
from data_management.services import create_analysis_task
from utils import TASK_STOP_EVENTS, get_task

from data_management.concept_service import create_concept_collection_task, get_concepts_from_db
from config import get_zai_credentials, is_zai_configured, get_openai_config, is_openai_configured, set_system_config
from datetime import datetime
import json
import threading
import logging

logger = logging.getLogger(__name__)


def read_root():
    """Root endpoint with comprehensive system status"""
    from datetime import datetime
    
    # Get configuration status
    zai_configured = is_zai_configured()
    openai_configured = is_openai_configured()
    system_configured = zai_configured and openai_configured
    
    # Basic system info
    status_info = {
        "service": "quant-dashboard-backend",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "configured": system_configured,
        "configuration": {
            "zai_configured": zai_configured,
            "openai_configured": openai_configured,
            "system_ready": system_configured
        }
    }
    
    return status_info


def get_system_health():
    """Comprehensive system health check endpoint"""
    from datetime import datetime
    import os
    from pathlib import Path
    
    # Get configuration status
    zai_configured = is_zai_configured()
    openai_configured = is_openai_configured()
    system_configured = zai_configured and openai_configured
    
    # Check file system status
    backend_dir = Path(__file__).parent
    config_file_exists = (backend_dir / 'config.json').exists()
    
    # Check database connectivity (basic check)
    db_status = "unknown"
    try:
        from models import get_session
        from sqlmodel import text
        with get_session() as session:
            # Simple query to test DB connectivity
            session.exec(text("SELECT 1")).first()
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Get OpenAI config details (non-sensitive)
    _, openai_base_url = get_openai_config()
    
    health_info = {
        "service": "quant-dashboard-backend",
        "status": "healthy" if system_configured else "configuration_required",
        "timestamp": datetime.now().isoformat(),
        "ready": system_configured,
        "configuration": {
            "zai_configured": zai_configured,
            "openai_configured": openai_configured,
            "system_ready": system_configured,
            "config_file_exists": config_file_exists,
            "openai_base_url": openai_base_url or "default"
        },
        "infrastructure": {
            "database": db_status,
            "config_storage": "available" if config_file_exists else "missing"
        },
        "version": "1.0.0"  # You can add version info here
    }
    
    return health_info


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
        error=task.error
    )


def get_latest_results() -> TaskResult | Message:
    """Get the latest completed task results"""
    import os
    import json
    
    last_task = get_last_completed_task()
    if last_task:
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
    
    # If no task in memory, try to load from JSON file
    json_file = "ranking.json"
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                cached_result = json.load(f)
            
            # Mark as from cache
            cached_result['from_cache'] = True
            
            return TaskResult(
                task_id=cached_result.get("task_id", "cached"),
                status=cached_result.get("status", "completed"),
                progress=cached_result.get("progress", 1.0),
                message=cached_result.get("message", "从缓存加载的分析结果"),
                created_at=cached_result.get("created_at", ""),
                completed_at=cached_result.get("completed_at", ""),
                top_n=cached_result.get("top_n", 0),
                selected_factors=cached_result.get("selected_factors", []),
                data=cached_result.get("data", []),
                count=cached_result.get("count", 0),
                extended=cached_result.get("extended"),
                error=None
            )
        except Exception as e:
            logger.warning(f"Failed to load ranking results from {json_file}: {e}")
    
    return Message(message="No results yet. POST /run to start a calculation.")


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


def get_kline_amplitude_dashboard(n_days: int = 30):
    """Get K-line amplitude analysis data for dashboard"""
    from data_management.dashboard_service import get_kline_amplitude_analysis
    return get_kline_amplitude_analysis(n_days)


def get_random_stocks_dashboard(n_days: int = 30):
    """Get random 5 stocks for dashboard chart"""
    from data_management.dashboard_service import get_random_stocks_analysis
    return get_random_stocks_analysis(n_days)


def run_extended_analysis():
    """Run standalone extended analysis focusing on sector analysis.
    Behavior: always compute a fresh result on manual trigger, cache it, and return it.
    Cache is for other consumers or future reads, and will be cleared when a new main analysis task completes.
    """
    from data_management.services import (
        cache_extended_analysis,
    )
    from extended_analysis import run_standalone_extended_analysis

    # Always compute fresh on manual trigger
    result = run_standalone_extended_analysis()
    if result and 'error' not in result:
        result['from_cache'] = False
        cache_extended_analysis(result)
    return result


def get_extended_analysis_results():
    """Get cached extended analysis results or load from JSON file"""
    from data_management.services import get_cached_extended_analysis
    import os
    import json
    
    # First try to get from memory cache
    cached_result = get_cached_extended_analysis()
    if cached_result:
        cached_result['from_cache'] = True
        return cached_result
    
    # If not in cache, try to load from JSON file
    json_file = "extended_analysis_results.json"
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            result['from_cache'] = True
            # Cache it for future requests
            from data_management.services import cache_extended_analysis
            cache_extended_analysis(result)
            return result
        except Exception as e:
            logger.warning(f"Failed to load extended analysis results from {json_file}: {e}")
    
    return {"message": "No extended analysis results found. Run analysis first."}


def run_extended_analysis_stream():
    """SSE endpoint: stream progress while running extended analysis.
    Sends events: start, progress (heartbeat), complete, error.
    """
    from fastapi.responses import StreamingResponse
    from data_management.services import cache_extended_analysis
    from extended_analysis import run_standalone_extended_analysis
    from data_management.chart_data_generator import generate_category_based_sunburst_chart_data
    from uuid import uuid4

    # Check if there's already a running task
    running_task = get_running_extended_analysis_task()
    if running_task:
        # Return existing task stream or error
        return {"error": f"扩展分析任务已在运行中 (任务ID: {running_task['task_id']})"}

    # Generate a unique task ID for this extended analysis
    task_id = str(uuid4())
    result_holder = {"done": False, "result": None, "error": None, "last_msg": None, "task_id": task_id}

    # Add task to tracking system
    add_extended_analysis_task(task_id, "running", "开始扩展分析")

    # Create stop event for cancellation
    stop_event = threading.Event()
    EXTENDED_ANALYSIS_STOP_EVENTS[task_id] = stop_event

    def worker():
        try:
            def _on_progress(msg: str):
                # 使用队列或直接yield不方便，这里简单地更新最近消息，由主循环按tick发出
                result_holder["last_msg"] = msg
                update_extended_analysis_task(task_id, message=msg)
            
            res = run_standalone_extended_analysis(on_progress=_on_progress, stop_event=stop_event)
            
            if stop_event.is_set():
                # Task was cancelled
                complete_extended_analysis_task(task_id, error="任务已被取消")
                result_holder["error"] = "任务已被取消"
            elif isinstance(res, dict) and 'error' in res:
                complete_extended_analysis_task(task_id, error=res.get('error'))
                result_holder["error"] = res.get('error')
            else:
                # Generate sunburst data and add to result
                if res and 'sectors' in res and res['sectors']:
                    try:
                        sunburst_data = generate_category_based_sunburst_chart_data(res['sectors'])
                        res['sunburst_data'] = sunburst_data
                        result_holder["last_msg"] = "生成旭日图数据完成"
                        update_extended_analysis_task(task_id, message="生成旭日图数据完成")
                    except Exception as e:
                        logger.warning(f"Failed to generate sunburst data: {e}")
                        res['sunburst_data'] = None
                complete_extended_analysis_task(task_id, result=res)
                result_holder["result"] = res
        except Exception as e:
            complete_extended_analysis_task(task_id, error=str(e))
            result_holder["error"] = str(e)
        finally:
            result_holder["done"] = True
            # Cleanup
            EXTENDED_ANALYSIS_THREADS.pop(task_id, None)
            EXTENDED_ANALYSIS_STOP_EVENTS.pop(task_id, None)

    def format_event(event: str, data: dict) -> str:
        import json as _json
        return f"event: {event}\n" + f"data: {_json.dumps(data, ensure_ascii=False)}\n\n"

    import threading as _threading
    import time as _time
    from datetime import datetime as _dt

    thread = _threading.Thread(target=worker, daemon=True)
    EXTENDED_ANALYSIS_THREADS[task_id] = thread
    thread.start()

    def event_stream():
        yield format_event("start", {"time": _dt.now().isoformat(), "message": "开始扩展分析", "task_id": task_id})
        # Heartbeat/progress ticks while worker runs
        i = 0
        while not result_holder["done"]:
            i += 1
            msg = result_holder.get("last_msg") or "正在计算扩展分析..."
            yield format_event("progress", {"time": _dt.now().isoformat(), "message": msg, "tick": i, "task_id": task_id})
            _time.sleep(1.0)
        # Completed
        if result_holder["error"] is not None:
            yield format_event("error", {"ok": False, "error": result_holder["error"], "task_id": task_id})
        else:
            result = result_holder["result"] or {}
            try:
                cache_extended_analysis(result)
            except Exception:
                pass
            yield format_event("complete", {"ok": True, "result": result, "task_id": task_id})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def stop_extended_analysis(task_id: str) -> dict:
    """Signal a running extended analysis task to stop and return its status"""
    stop_event = EXTENDED_ANALYSIS_STOP_EVENTS.get(task_id)
    if not stop_event:
        raise HTTPException(status_code=404, detail="Extended analysis task not found or already finished")

    # Signal cancellation
    stop_event.set()
    
    # Update task status
    update_extended_analysis_task(task_id, status="stopping", message="已请求停止扩展分析，正在清理...")

    return {
        "task_id": task_id,
        "status": "stopping",
        "message": "已请求停止扩展分析，正在清理..."
    }


def get_extended_analysis_task_status(task_id: str) -> dict:
    """Get status of a specific extended analysis task"""
    task = get_extended_analysis_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Extended analysis task not found")
    
    return task


def get_running_extended_analysis_status() -> dict:
    """Get status of currently running extended analysis task"""
    running_task = get_running_extended_analysis_task()
    if not running_task:
        return {"status": "idle", "message": "没有正在运行的扩展分析任务"}
    
    return running_task


# Configuration API functions

def get_zai_config():
    """Return current system configuration state (mask sensitive values)."""
    _, base_url = get_openai_config()
    
    return {
        "configured": is_zai_configured() and is_openai_configured(),
        "OPENAI_BASE_URL": base_url,  # Base URL is not sensitive, show full value
        # Individual configuration status
        "zai_configured": is_zai_configured(),
        "openai_configured": is_openai_configured(),
    }


def update_zai_config(config_data: dict) -> dict:
    """Update and persist system configuration (ZAI + OpenAI) into backend/config.json."""
    # Get current values to merge with
    current_bearer, current_cookie = get_zai_credentials()
    current_api_key, current_base_url = get_openai_config()

    current_config = {
        "ZAI_BEARER_TOKEN": current_bearer,
        "ZAI_COOKIE_STR": current_cookie,
        "OPENAI_API_KEY": current_api_key,
        "OPENAI_BASE_URL": current_base_url
    }

    new_config = current_config.copy()

    # Update values from payload, but only if they are not empty strings for secrets.
    if config_data.get('ZAI_BEARER_TOKEN'):
        new_config['ZAI_BEARER_TOKEN'] = config_data['ZAI_BEARER_TOKEN']
    if config_data.get('ZAI_COOKIE_STR'):
        new_config['ZAI_COOKIE_STR'] = config_data['ZAI_COOKIE_STR']
    if config_data.get('OPENAI_API_KEY'):
        new_config['OPENAI_API_KEY'] = config_data['OPENAI_API_KEY']
    
    # OPENAI_BASE_URL is not a secret and can be updated to an empty string.
    if 'OPENAI_BASE_URL' in config_data:
        new_config['OPENAI_BASE_URL'] = config_data.get('OPENAI_BASE_URL', '')

    # Validate required fields are present in the final config
    required_fields = ['ZAI_BEARER_TOKEN', 'ZAI_COOKIE_STR', 'OPENAI_API_KEY']
    missing_fields = [field for field in required_fields if not new_config.get(field, '').strip()]
    
    if missing_fields:
        raise HTTPException(
            status_code=400, 
            detail=f"缺少必填字段: {', '.join(missing_fields)}"
        )
    
    try:
        set_system_config(new_config)
        return {"success": True, "message": "系统配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {e}")


def login_user(request: AuthRequest) -> AuthResponse:
    """User authentication - only existing users can login"""
    try:
        # Basic validation
        if not request.name or not request.name.strip():
            return AuthResponse(
                success=False,
                message="用户名不能为空"
            )
        
        if not request.email or not request.email.strip():
            return AuthResponse(
                success=False,
                message="邮箱不能为空"
            )
        
        # Simple email format check
        if "@" not in request.email:
            return AuthResponse(
                success=False,
                message="邮箱格式不正确"
            )
        
        with get_session() as session:
            # Check if user exists with matching name and email
            statement = select(User).where(
                User.name == request.name.strip(),
                User.email == request.email.strip().lower()
            )
            user = session.exec(statement).first()
            
            if user:
                # User exists, generate token
                token = f"token_{user.id}"
                return AuthResponse(
                    success=True,
                    token=token,
                    message="认证成功",
                    user={
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "is_admin": user.is_admin
                    }
                )
            else:
                # Check if this is the first user (no users exist)
                user_count_statement = select(func.count(User.id))
                user_count = session.exec(user_count_statement).first()
                is_empty_table = user_count == 0
                
                if is_empty_table:
                    # Create the first user using the provided credentials
                    first_user = User(
                        name=request.name.strip(), 
                        email=request.email.strip().lower(),
                        is_admin=True  # First user becomes admin
                    )
                    session.add(first_user)
                    session.commit()
                    session.refresh(first_user)
                    
                    token = f"token_{first_user.id}"
                    return AuthResponse(
                        success=True,
                        token=token,
                        message="管理员账户创建成功，认证通过",
                        user={
                            "id": first_user.id,
                            "name": first_user.name,
                            "email": first_user.email,
                            "is_admin": first_user.is_admin
                        }
                    )
                
                # User does not exist - reject authentication
                return AuthResponse(
                    success=False,
                    message="用户不存在，请联系管理员"
                )
                
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return AuthResponse(
            success=False,
            message=f"认证失败: {str(e)}"
        )