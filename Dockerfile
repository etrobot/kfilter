# Multi-stage build for fullstack app
FROM node:18-alpine as frontend-builder

WORKDIR /app/frontend

# Copy frontend package.json and install dependencies directly
COPY frontend/package.json ./
RUN npm install

# Copy frontend source code
COPY frontend/ ./

# Build frontend using npx to ensure vite is found
RUN npx vite build

# Python backend with frontend static files
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app

# Copy backend files
COPY backend/ ./
RUN uv sync --frozen

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./static

# Create data directory for database persistence
RUN mkdir -p /app/data_management

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]