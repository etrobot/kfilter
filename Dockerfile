# Multi-stage build for fullstack app
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package.json and install dependencies directly
COPY frontend/package.json ./
RUN npm install

# Copy frontend source code (excluding node_modules)
COPY frontend/app ./app
COPY frontend/public ./public
COPY frontend/index.html ./index.html
COPY frontend/vite.config.ts ./vite.config.ts
COPY frontend/tsconfig.json ./tsconfig.json
COPY frontend/tailwind.config.js ./tailwind.config.js
COPY frontend/postcss.config.js ./postcss.config.js
COPY frontend/components.json ./components.json

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

# Copy backend files with correct structure
COPY backend/ ./

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