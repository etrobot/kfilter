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

# Load environment variables at startup
try:
    from dotenv import load_dotenv
    from pathlib import Path
    # Load .env file from project root
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    logging.info(f"Loaded environment variables from {env_path}")
except ImportError:
    logging.warning("python-dotenv not installed, using system environment variables only")
except Exception as e:
    logging.warning(f"Failed to load .env file: {e}")

from models import RunRequest, RunResponse, TaskResult, Message, ConceptTaskResult, AuthRequest, AuthResponse, create_db_and_tables, User, get_session
from sqlmodel import select
from api import (
    read_root, run_analysis, get_task_status, get_latest_results, list_all_tasks,
    collect_concepts, get_concept_task_status, get_latest_concept_results, 
    list_all_concept_tasks, get_concepts_list, stop_analysis, get_kline_amplitude_dashboard,
    run_extended_analysis, login_user, get_zai_config, update_zai_config
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

def create_admin_user():
    """Create admin user from environment variables if provided"""
    admin_username = os.getenv('ADMIN_USERNAME')
    admin_email = os.getenv('ADMIN_EMAIL')
    
    if admin_username and admin_email:
        try:
            with next(get_session()) as session:
                # Check if admin user already exists
                statement = select(User).where(
                    User.name == admin_username,
                    User.email == admin_email
                )
                existing_user = session.exec(statement).first()
                
                if not existing_user:
                    # Create new admin user
                    admin_user = User(name=admin_username, email=admin_email)
                    session.add(admin_user)
                    session.commit()
                    logger.info(f"Admin user created: {admin_username} ({admin_email})")
                else:
                    logger.info(f"Admin user already exists: {admin_username} ({admin_email})")
        except Exception as e:
            logger.error(f"Failed to create admin user: {e}")
    else:
        logger.info("No admin user credentials provided in environment variables")

# Create admin user if credentials are provided
create_admin_user()

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
    # Mount specific static folders used by the SPA
    assets_dir = os.path.join(static_dir, "assets")
    icons_dir = os.path.join(static_dir, "icons")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    if os.path.isdir(icons_dir):
        app.mount("/icons", StaticFiles(directory=icons_dir), name="icons")

    # Backward compatible mount (optional)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Direct file endpoints for PWA files
    @app.get("/manifest.json", include_in_schema=False)
    async def serve_manifest():
        path = os.path.join(static_dir, "manifest.json")
        if os.path.isfile(path):
            return FileResponse(path)
        return {"detail": "manifest.json not found"}

    @app.get("/sw.js", include_in_schema=False)
    async def serve_sw():
        path = os.path.join(static_dir, "sw.js")
        if os.path.isfile(path):
            return FileResponse(path)
        return {"detail": "sw.js not found"}

    @app.get("/favicon.ico", include_in_schema=False)
    async def serve_favicon():
        path = os.path.join(static_dir, "favicon.ico")
        if os.path.isfile(path):
            return FileResponse(path)
        return {"detail": "favicon.ico not found"}

# Explicit root route: return index.html
@app.get("/", include_in_schema=False)
async def root_index():
    if os.path.exists(static_dir):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
    return {"message": "Quant Dashboard API", "docs": "/docs"}


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


# Extended Analysis route

@app.post("/extended-analysis/run")
def run_extended_analysis_endpoint():
    """Run standalone extended analysis focusing on sector analysis"""
    return run_extended_analysis()


@app.delete("/extended-analysis/cache")
def clear_extended_analysis_cache_endpoint():
    """Clear extended analysis cache to force fresh analysis"""
    from data_management.services import clear_extended_analysis_cache
    clear_extended_analysis_cache()
    return {"message": "Extended analysis cache cleared"}


# Authentication routes

@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: AuthRequest) -> AuthResponse:
    """User login/register with username and email"""
    return login_user(request)


# Configuration routes

@app.get("/config/zai")
def get_config_zai():
    """Get masked ZAI configuration and configured flag"""
    return get_zai_config()


@app.post("/config/zai")
def post_config_zai(payload: dict):
    """Save ZAI configuration to backend/config.json"""
    bearer = str(payload.get("ZAI_BEARER_TOKEN", ""))
    cookie = str(payload.get("ZAI_COOKIE_STR", ""))
    return update_zai_config(bearer, cookie)


# Serve frontend for production
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend files for production"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    
    # If static directory doesn't exist, return API info
    if not os.path.exists(static_dir):
        return {"message": "Quant Dashboard API", "docs": "/docs"}
    
    # Handle root path - serve index.html
    if full_path == "":
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        # Fallback to API info if frontend not built
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
