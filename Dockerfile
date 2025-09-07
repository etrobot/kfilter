# Multi-stage build for fullstack app
FROM node:18-alpine AS frontend-builder

# Copy the entire project for frontend build
COPY . /app
WORKDIR /app/frontend

# Install frontend dependencies
RUN npm install

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

# Set working directory
WORKDIR /app

# Copy backend files with correct structure
COPY backend/ ./

# Debug: Show file structure
RUN ls -la

# Set up proper Python environment and install dependencies
RUN uv sync --frozen

# Set PYTHONPATH to ensure modules can be found
ENV PYTHONPATH=/app

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./static

# Create data directory for database persistence with proper permissions
RUN mkdir -p /app/data_management && \
    chmod 755 /app/data_management

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]