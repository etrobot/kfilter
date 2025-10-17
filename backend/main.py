from __future__ import annotations
import logging
import warnings
from typing import List
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, List
from fastapi.middleware.cors import CORSMiddleware

# Suppress verbose SQLAlchemy logging IMMEDIATELY
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.engine.Engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

from config import load_config_json,set_system_config
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

def load_startup_config():
    """Load configuration from config.json and set environment variables at startup"""
    try:
        config_data = load_config_json()
        if config_data:
            # Load all configuration values into environment variables
            set_system_config(config_data)
            
            # Count valid configurations
            valid_configs = []
            
            # Check ZAI configuration
            zai_keys = ['ZAI_BEARER_TOKEN', 'ZAI_USER_ID']
            zai_values = [config_data.get(key, '').strip() for key in zai_keys]
            if all(val and val not in ['your_bearer_token_here', 'your_user_id_here'] for val in zai_values[:2]) and zai_values[2]:
                valid_configs.append("ZAI")
            
            # Check OpenAI configuration  
            openai_key = config_data.get('OPENAI_API_KEY', '').strip()
            if openai_key and openai_key != 'your_openai_api_key_here':
                valid_configs.append("OpenAI")
            
            config_status = f"Loaded configuration from config.json: {len(config_data)} settings"
            if valid_configs:
                config_status += f" (Valid: {', '.join(valid_configs)})"
            
            logging.info(config_status)
            return True
        else:
            logging.info("No config.json found or empty, using environment variables only")
            return False
    except Exception as e:
        logging.warning(f"Failed to load config.json: {e}")
        logging.info("System will start with environment variables only")
        return False

# Load configuration at startup
load_startup_config()


from models import RunRequest, RunResponse, TaskResult, Message, ConceptTaskResult, AuthRequest, AuthResponse, create_db_and_tables, User, get_session
from sqlmodel import select
from api import (
    read_root, run_analysis, get_task_status, get_latest_results, list_all_tasks,
    collect_concepts, get_concept_task_status, get_latest_concept_results,
    list_all_concept_tasks, get_concepts_list, stop_analysis, get_kline_amplitude_dashboard,
    run_extended_analysis, stop_extended_analysis, login_user, get_zai_config, update_zai_config,
    get_extended_analysis_task_status, get_running_extended_analysis_status, get_system_health,
    get_random_stocks_dashboard
)
from factors import list_factors

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import scheduler functions
from scheduler import start_daily_scheduler

# Suppress warnings
warnings.filterwarnings('ignore')

app = FastAPI(title="Quant Dashboard")

# 初始化数据库
create_db_and_tables()
logger.info("Database initialized successfully")

# Admin user will be automatically created as the first user to register
logger.info("Admin user will be automatically assigned to the first user who registers")

# Check and log final system configuration status after startup loading
def check_system_configuration():
    """Check and log the current system configuration status"""
    try:
        from config import is_zai_configured, is_openai_configured, get_zai_credentials, get_openai_config
        
        # Check configuration status
        zai_config = is_zai_configured()
        openai_config = is_openai_configured()
        system_ready = zai_config and openai_config
        
        logger.info("=" * 50)
        logger.info("SYSTEM CONFIGURATION STATUS")
        logger.info("=" * 50)
        
        # ZAI Configuration details
        bearer, cookie, user_id = get_zai_credentials()
        logger.info(f"ZAI Configuration:")
        logger.info(f"  - Bearer Token: {'✓ Set' if bearer and bearer != 'your_bearer_token_here' else '✗ Not configured'}")
        logger.info(f"  - Cookie String: {'✓ Set' if cookie else '✗ Not set'}")
        logger.info(f"  - User ID: {'✓ Set' if user_id and user_id != 'your_user_id_here' else '✗ Not configured'}")
        logger.info(f"  - ZAI Status: {'✓ CONFIGURED' if zai_config else '✗ NOT CONFIGURED'}")
        
        # OpenAI Configuration details
        api_key, base_url, model = get_openai_config()
        logger.info(f"OpenAI Configuration:")
        logger.info(f"  - API Key: {'✓ Set' if api_key and api_key != 'your_openai_api_key_here' else '✗ Not configured'}")
        logger.info(f"  - Base URL: {base_url if base_url else 'Default (https://api.openai.com/v1)'}")
        logger.info(f"  - Model: {model}")
        logger.info(f"  - OpenAI Status: {'✓ CONFIGURED' if openai_config else '✗ NOT CONFIGURED'}")
        
        # Overall system status
        logger.info(f"Overall System Status: {'✓ READY FOR OPERATION' if system_ready else '✗ REQUIRES CONFIGURATION'}")
        
        if not system_ready:
            logger.warning("⚠ SYSTEM NOT FULLY CONFIGURED")
            logger.warning("  Please configure missing components via the /config/zai endpoint")
            if not zai_config:
                logger.warning("  - ZAI credentials are required for market data access")
            if not openai_config:
                logger.warning("  - OpenAI API key is required for LLM analysis")
        else:
            logger.info("✅ SYSTEM FULLY CONFIGURED AND READY")
            
        logger.info("=" * 50)
        return system_ready
        
    except Exception as e:
        logger.error(f"Failed to check configuration status: {e}")
        return False

# Check system configuration after startup loading
check_system_configuration()

# Start daily scheduler for automated analysis
start_daily_scheduler()

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


@app.get("/health")
def health_check():
    """System health check endpoint"""
    return get_system_health()


@app.get("/status")
def status_check():
    """Simple status endpoint (alias for health check)"""
    return get_system_health()


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


@app.get("/dashboard/random-stocks")
def get_dashboard_random_stocks(n_days: int = 30):
    """Get random 5 stocks for dashboard chart"""
    return get_random_stocks_dashboard(n_days)


# Extended Analysis route

@app.get("/extended-analysis/results")
def get_extended_analysis_results_endpoint():
    """Get cached extended analysis results or load from JSON file"""
    from api import get_extended_analysis_results
    return get_extended_analysis_results()


@app.post("/extended-analysis/run")
def run_extended_analysis_endpoint():
    """Run standalone extended analysis focusing on sector analysis"""
    return run_extended_analysis()


@app.get("/extended-analysis/stream")
def run_extended_analysis_stream_endpoint():
    """Run extended analysis and stream progress via SSE"""
    from api import run_extended_analysis_stream
    return run_extended_analysis_stream()


@app.delete("/extended-analysis/cache")
def clear_extended_analysis_cache_endpoint():
    """Clear extended analysis cache to force fresh analysis"""
    from data_management.services import clear_extended_analysis_cache
    clear_extended_analysis_cache()
    return {"message": "Extended analysis cache cleared"}


@app.post("/extended-analysis/{task_id}/stop")
def stop_extended_analysis_endpoint(task_id: str):
    """Stop a running extended analysis task"""
    return stop_extended_analysis(task_id)


@app.get("/extended-analysis/{task_id}/status")
def get_extended_analysis_task_status_endpoint(task_id: str):
    """Get status of a specific extended analysis task"""
    return get_extended_analysis_task_status(task_id)


@app.get("/extended-analysis/status")
def get_running_extended_analysis_status_endpoint():
    """Get status of currently running extended analysis task"""
    return get_running_extended_analysis_status()


# Authentication routes

@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: AuthRequest) -> AuthResponse:
    """User login/register with username and email"""
    return login_user(request)


# Configuration routes

@app.get("/config/zai")
def get_config():
    """Get masked configuration and configured flag"""
    return get_zai_config()


@app.post("/config/zai")
def post_config(payload: dict):
    """Save configuration (ZAI + OpenAI) to backend/config.json"""
    print("\n" + "=" * 60)
    print("POST /config/zai ENDPOINT HIT")
    print(f"Payload received: {payload}")
    print("=" * 60 + "\n")
    logger.info(f"POST /config/zai received with payload keys: {list(payload.keys())}")
    print("About to call update_zai_config...")
    result = update_zai_config(payload)
    print(f"update_zai_config returned: {result}")
    logger.info(f"POST /config/zai returning: {result}")
    return result


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
