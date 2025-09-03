from __future__ import annotations
import logging
import warnings
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import RunResponse, TaskResult, Message, create_db_and_tables
from api import read_root, run_analysis, get_task_status, get_latest_results, list_all_tasks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore')

app = FastAPI(title="Quant Dashboard Backend")

# 初始化数据库
create_db_and_tables()
logger.info("Database initialized successfully")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return read_root()


@app.post("/run", response_model=RunResponse)
def run(top_n: int = 100) -> RunResponse:
    return run_analysis(top_n)


@app.get("/task/{task_id}", response_model=TaskResult)
def get_task(task_id: str) -> TaskResult:
    return get_task_status(task_id)


@app.get("/results", response_model=TaskResult | Message)
def get_results():
    return get_latest_results()


@app.get("/tasks", response_model=List[TaskResult])
def list_tasks() -> List[TaskResult]:
    return list_all_tasks()
