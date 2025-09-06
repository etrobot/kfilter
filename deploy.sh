#!/bin/bash

# Deployment script for Quant Dashboard

set -e

echo "🚀 Starting deployment of Quant Dashboard..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data

# Create Traefik network if it doesn't exist
echo "🌐 Creating Traefik network..."
docker network create traefik 2>/dev/null || echo "Network 'traefik' already exists"

# Build and start services
echo "🔨 Building and starting services..."
docker-compose down --remove-orphans
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "✅ Checking service status..."
docker-compose ps

echo "🎉 Deployment completed!"
echo ""
echo "📊 Application:"
echo "  - Local URL: http://localhost:61125"
echo "  - Local API Docs: http://localhost:61125/docs"
echo "  - Production URL: https://a.subx.fun"
echo ""
echo "📁 Data persistence:"
echo "  - Database: ./data/stock_data.db"
echo ""
echo "🔧 Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart: docker-compose restart"