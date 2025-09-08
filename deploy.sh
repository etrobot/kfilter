#!/bin/bash

# Deployment script for Quant Dashboard
set -e

command_exists() { command -v "$1" >/dev/null 2>&1; }

info() { echo -e "\033[0;34m$1\033[0m"; }
success() { echo -e "\033[0;32m$1\033[0m"; }
warn() { echo -e "\033[1;33m$1\033[0m"; }
error() { echo -e "\033[0;31m$1\033[0m"; }

info "🚀 Starting deployment of Quant Dashboard..."

# Read user info from env or prompt
info "👤 Setting up user information..."
if [ -z "$ADMIN_USERNAME" ]; then
  read -p "请输入用户名 (Username): " ADMIN_USERNAME
fi
if [ -z "$ADMIN_EMAIL" ]; then
  read -p "请输入邮箱 (Email): " ADMIN_EMAIL
fi

# Validate email format (basic validation)
case "$ADMIN_EMAIL" in
  *[@]*.*) : ;;  # looks ok
  *) error "❌ 邮箱格式无效，请输入有效的邮箱地址"; exit 1;;
esac

success "✅ 用户信息设置完成:"
echo "  - 用户名: $ADMIN_USERNAME"
echo "  - 邮箱: $ADMIN_EMAIL"
echo ""

export ADMIN_USERNAME
export ADMIN_EMAIL

# Create necessary directories
info "📁 Creating directories..."
mkdir -p data

# Backup existing database if it exists
backup_database() {
  local db_path="./data/stock_data.db"
  local backup_path="./data/stock_data.db.backup.$(date +%Y%m%d_%H%M%S)"
  
  if [ -f "$db_path" ]; then
    info "💾 Backing up existing database..."
    cp "$db_path" "$backup_path"
    success "✅ Database backed up to: $backup_path"
    echo "$backup_path" > ./data/.last_backup_path
    return 0
  else
    info "ℹ️  No existing database found to backup"
    return 1
  fi
}

# Restore database from backup if needed
restore_database() {
  local backup_path_file="./data/.last_backup_path"
  
  if [ -f "$backup_path_file" ]; then
    local backup_path=$(cat "$backup_path_file")
    if [ -f "$backup_path" ]; then
      info "🔄 Checking if database restore is needed..."
      
      # Check if current database exists and is valid
      if [ ! -f "./data/stock_data.db" ]; then
        warn "⚠️  Database not found after deployment, restoring from backup..."
        cp "$backup_path" "./data/stock_data.db"
        success "✅ Database restored from backup"
      else
        # Check if database is accessible (basic validation)
        if ! docker exec quant-dashboard sqlite3 /app/data_management/stock_data.db ".tables" >/dev/null 2>&1; then
          warn "⚠️  Database appears corrupted, restoring from backup..."
          cp "$backup_path" "./data/stock_data.db"
          success "✅ Database restored from backup due to corruption"
        else
          success "✅ Database is healthy, backup not needed"
        fi
      fi
    fi
  fi
}

# Backup database before deployment
backup_database

# If docker is not available, run local validation to test routes
if ! command_exists docker || ! command_exists docker-compose; then
  warn "⚠️  未检测到 Docker 或 docker-compose，进入本地测试模式（不启动容器）..."

  # Validate backend/static and routing definitions
  if [ -f "backend/static/index.html" ]; then
    success "✅ 检测到 backend/static/index.html"
  else
    error "❌ 未找到 backend/static/index.html，请先构建前端并同步到 backend/static"
    echo "   提示: cd frontend && npm ci && npm run build && cp -r dist/* ../backend/static/"
    exit 1
  fi

  # Check root route is explicitly defined
  if grep -q "@app.get(\"/\"" backend/main.py; then
    success "✅ 后端已显式定义根路由 / 返回 index.html"
  else
    error "❌ 未检测到根路由 / 定义，请检查 backend/main.py"
    exit 1
  fi

  # Check static mounts
  [ -d "backend/static/assets" ] && success "✅ 检测到静态资源目录 backend/static/assets" || warn "⚠️  未检测到 backend/static/assets"
  [ -d "backend/static/icons" ] && success "✅ 检测到图标目录 backend/static/icons" || warn "⚠️  未检测到 backend/static/icons"
  [ -f "backend/static/manifest.json" ] && success "✅ 检测到 PWA 文件 manifest.json" || warn "⚠️  未检测到 manifest.json"
  [ -f "backend/static/sw.js" ] && success "✅ 检测到 PWA 文件 sw.js" || warn "⚠️  未检测到 sw.js"

  success "🎉 本地路由检查通过：根路径将返回前端 index.html"
  echo ""
  info "👉 你可以在安装 Docker 后再次运行本脚本进行完整部署"
  exit 0
fi

# Create Traefik network if it doesn't exist
info "🌐 Creating Traefik network..."
docker network create traefik 2>/dev/null || echo "Network 'traefik' already exists"

# Build and start services
info "🔨 Building and starting services..."
docker-compose down --remove-orphans
if [ "$NO_CACHE" = "1" ]; then
  docker-compose build --no-cache
else
  docker-compose build
fi
docker-compose up -d

# Wait for services to be ready
info "⏳ Waiting for services to start..."
sleep 12

# Check service status
success "✅ Checking service status..."
docker-compose ps

# Restore database if needed
restore_database

# Optional: quick health check via curl if available
if command_exists curl; then
  info "🔍 Verifying root path returns index.html..."
  if curl -sSf "http://localhost:61125/" | grep -qi "<div id=\"root\">"; then
    success "✅ Root path served frontend index.html"
  else
    warn "⚠️  Root path content did not match expected HTML"
  fi
fi

success "🎉 Deployment completed!"
echo ""
info "📊 Application:"
echo "  - Local URL: http://localhost:61125"
echo "  - Local API Docs: http://localhost:61125/docs"
echo "  - Production URL: https://a.subx.fun"
echo ""
info "📁 Data persistence:"
echo "  - Database: ./data/stock_data.db"
echo ""
info "🔧 Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart: docker-compose restart"
