# CODEBUDDY.md

This file contains information for AI assistants working on this codebase.

## Project Overview

This is a fullstack quantitative analysis dashboard application called "kfilter" that provides stock market analysis and factor-based ranking. The project is a monorepo with:

- **Backend**: Python FastAPI application with UV dependency management
- **Frontend**: React/TypeScript SPA with Vite build system
- **Database**: SQLite with SQLModel ORM
- **Architecture**: RESTful API with real-time task management and SSE streaming

## Development Commands

### Setup and Installation
```bash
# Install all dependencies (frontend and backend)
pnpm run install:all

# Backend only (from project root)
cd backend && uv sync --quiet

# Frontend only (from project root)  
cd frontend && pnpm install
```

### Development Servers
```bash
# Start both frontend and backend concurrently
pnpm run dev

# Start backend only (from backend/)
uv run uvicorn main:app --reload

# Start frontend only (from frontend/)
pnpm dev
```

### Build Commands
```bash
# Build both frontend and backend
pnpm run build

# Build frontend only (from frontend/)
pnpm build

# Backend build (placeholder - not fully implemented)
pnpm run build:backend
```

### Testing and Quality
```bash
# Backend testing (from backend/)
uv run pytest

# Backend linting and formatting (from backend/)
uv run black .
uv run ruff check .
```

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# Deploy script
./deploy.sh
```

## Code Architecture

### Backend Structure (`backend/`)

**Core Application Files:**
- `main.py` - FastAPI application entry point with CORS, static file serving, and route definitions
- `api.py` - API endpoint implementations and business logic
- `models.py` - SQLModel database models and Pydantic schemas
- `config.py` - Configuration management for ZAI and OpenAI credentials
- `utils.py` - Task management utilities and helper functions

**Key Modules:**
- `factors/` - Factor calculation modules (momentum, support indicators)
- `data_management/` - Data services, analysis runners, and database management
  - `services.py` - Core analysis task creation and management
  - `stock_data_manager.py` - Market data collection and storage
  - `concept_service.py` - Stock concept data management
  - `dashboard_service.py` - Dashboard analytics
  - `llm_client.py` - OpenAI/LLM integration
- `market_data/` - Market data fetching and processing

**Database:**
- SQLite database (`data_management/stock_data.db`)
- SQLModel ORM with automatic table creation
- Task management with background processing
- User authentication system

### Frontend Structure (`frontend/`)

**Main Application:**
- `app/main.tsx` - Root React component with routing and state management
- `app/components/` - Reusable UI components
- `app/services/api.ts` - API client and polling utilities
- `app/types.ts` - TypeScript type definitions

**Key Features:**
- PWA support with service worker
- Real-time task progress tracking
- Mobile-responsive design with dedicated navigation
- Chart.js and D3.js for data visualization
- Tailwind CSS with Radix UI components

### Task Management System

The application uses a sophisticated background task system:

1. **Task Creation**: API endpoints create tasks via `data_management/services.py`
2. **Background Processing**: Tasks run in separate threads with progress tracking
3. **Real-time Updates**: Frontend polls task status and receives SSE streams
4. **State Management**: Tasks stored in memory with SQLite persistence for results

### API Architecture

**Main Endpoints:**
- `/run` - Start comprehensive stock analysis
- `/concepts/collect` - Start concept data collection
- `/extended-analysis/run` - Run sector-focused analysis
- `/dashboard/kline-amplitude` - Dashboard analytics
- `/config/zai` - Configuration management
- `/api/auth/login` - User authentication

**Real-time Features:**
- Task polling with automatic cleanup
- Server-Sent Events (SSE) for streaming progress
- Background task cancellation support

## Environment Configuration

### Required Environment Variables
- `ADMIN_USERNAME` - Admin user name
- `ADMIN_EMAIL` - Admin email  
- `DATABASE_PATH` - SQLite database path (defaults to `data_management/stock_data.db`)

### Configuration Files
- `.env` - Environment variables (not committed)
- `backend/config.json` - Runtime configuration for API keys
- `components.json` - Shadcn/ui component configuration

### API Integration
- OpenAI API for LLM-powered analysis
- ZAI (Zero-AI) service integration
- AkShare for Chinese market data

## Development Notes

### Backend Development
- Uses UV for fast Python dependency management
- FastAPI with automatic OpenAPI documentation at `/docs`
- SQLModel provides type-safe database operations
- Background tasks use threading with stop event coordination

### Frontend Development  
- Vite for fast development and building
- React 18 with TypeScript
- PWA-ready with offline support
- Mobile-first responsive design
- Real-time updates via polling and SSE

### Data Flow
1. User triggers analysis via frontend
2. API creates background task
3. Task runner fetches market data and calculates factors
4. Results stored in database and returned via polling
5. Frontend displays results with charts and tables

### Key Integrations
- Market data via AkShare (Chinese stocks)
- AI analysis via OpenAI API
- Real-time communication via SSE
- Docker deployment with Traefik reverse proxy