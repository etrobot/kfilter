from __future__ import annotations
import logging
import warnings
from typing import List
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, List
from fastapi.middleware.cors import CORSMiddleware
import os

from models import RunRequest, RunResponse, TaskResult, Message, ConceptTaskResult, create_db_and_tables
from api import (
    read_root, run_analysis, get_task_status, get_latest_results, list_all_tasks,
    collect_concepts, get_concept_task_status, get_latest_concept_results, 
    list_all_concept_tasks, get_concepts_list, stop_analysis, get_kline_amplitude_dashboard
)
from factors import list_factors

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore')

app = FastAPI(title="Quant Dashboard")

# 初始化数据库
create_db_and_tables()
logger.info("Database initialized successfully")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://a.subx.fun"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if they exist (for production)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def root():
    return read_root()


@app.post("/run", response_model=RunResponse)
def run(request: RunRequest) -> RunResponse:
    return run_analysis(request)


@app.get("/task/{task_id}", response_model=TaskResult)
def get_task(task_id: str) -> TaskResult:
    return get_task_status(task_id)


@app.post("/task/{task_id}/stop", response_model=TaskResult)
def stop_task(task_id: str) -> TaskResult:
    return stop_analysis(task_id)


@app.get("/results", response_model=TaskResult | Message)
def get_results():
    return get_latest_results()


@app.get("/tasks", response_model=List[TaskResult])
def list_tasks() -> List[TaskResult]:
    return list_all_tasks()


@app.get("/factors")
def get_factors() -> Dict[str, object]:
    """Return factor metadata for frontend dynamic rendering"""
    factors = list_factors()
    # Normalize to simple JSON metadata
    items = []
    for f in factors:
        items.append({
            "id": f.id,
            "name": f.name,
            "description": f.description,
            "columns": f.columns,
        })
    return {"items": items}


# Concept routes

@app.post("/concepts/collect", response_model=RunResponse)
def collect_concept_data() -> RunResponse:
    """Start concept data collection"""
    return collect_concepts()


@app.get("/concepts/task/{task_id}", response_model=ConceptTaskResult)
def get_concept_task(task_id: str) -> ConceptTaskResult:
    """Get concept task status"""
    return get_concept_task_status(task_id)


@app.get("/concepts/results", response_model=ConceptTaskResult | Message)
def get_concept_results():
    """Get latest concept collection results"""
    return get_latest_concept_results()


@app.get("/concepts/tasks", response_model=List[ConceptTaskResult])
def list_concept_tasks() -> List[ConceptTaskResult]:
    """List all concept tasks"""
    return list_all_concept_tasks()


@app.get("/concepts")
def get_concepts():
    """Get list of all concepts"""
    return get_concepts_list()


# Dashboard routes

@app.get("/dashboard/kline-amplitude")
def get_dashboard_kline_amplitude(n_days: int = 30):
    """Get K-line amplitude analysis for dashboard"""
    return get_kline_amplitude_dashboard(n_days)


# Serve frontend for production
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend files for production"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    
    # If static directory doesn't exist, return API info
    if not os.path.exists(static_dir):
        return {"message": "Quant Dashboard API", "docs": "/docs"}
    
    # Try to serve the requested file
    file_path = os.path.join(static_dir, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # For SPA routing, serve index.html for non-API routes
    if not full_path.startswith("api/") and not full_path.startswith("docs"):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
    
    # Return 404 for API routes or missing files
    return {"detail": "Not found"}
