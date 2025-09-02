# PNPM + UV Demo Project

This is a monorepo demonstrating a fullstack application using pnpm for package management and UV for Python dependency management.

## Project Structure

- `backend/`: Python backend using FastAPI and Uvicorn, with UV for dependency management.
- `frontend/`: React frontend using Vite and pnpm for dependency management.

## Getting Started

### Prerequisites

- Node.js (with pnpm installed)
- Python (with UV installed)

### Installation

1. **Install all dependencies (frontend and backend):**

   ```bash
   pnpm run install:all
   ```

### Running the Development Servers

To run both the frontend and backend development servers concurrently:

```bash
pnpm run dev
```

This will start:
- The backend server (FastAPI/Uvicorn) with auto-reloading.
- The frontend development server (Vite).

### Building the Project

To build both the frontend and backend:

```bash
pnpm run build
```

This will:
- Build the frontend for production.
- (Note: Backend build step is currently a placeholder and not fully implemented.)
