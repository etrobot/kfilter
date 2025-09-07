#!/bin/bash

# Deployment script for Quant Dashboard
set -e

command_exists() { command -v "$1" >/dev/null 2>&1; }

info() { echo -e "\033[0;34m$1\033[0m"; }
success() { echo -e "\033[0;32m$1\033[0m"; }
warn() { echo -e "\033[1;33m$1\033[0m"; }
error() { echo -e "\033[0;31m$1\033[0m"; }

usage() {
  cat <<EOF
Usage: $0 [deploy|redeploy|watch] [options]

Commands:
  deploy                初次部署（默认）。会提示输入管理员信息并保存到 .env
  redeploy              修改后重新部署。读取 .env 或环境变量，不会强制交互输入
  watch                 监视 Git 远程分支变更，自动 git pull 并执行 redeploy（需要 git）

Options:
  --no-cache            构建时不使用缓存（等效于环境变量 NO_CACHE=1）
  -y, --non-interactive 非交互模式；若缺少必要环境变量会直接报错退出
  -h, --help            显示帮助

环境变量：
  ADMIN_USERNAME        管理员用户名
  ADMIN_EMAIL           管理员邮箱
  NO_CACHE=1            构建时不使用缓存
EOF
}

# Load env from .env if present
load_env_file() {
  if [ -f .env ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env | sed -e 's/\r$//' | xargs -0 echo 2>/dev/null || true)
  fi
}

write_env_var() {
  key="$1"; value="$2"
  if [ -z "$key" ]; then return; fi
  if [ -f .env ]; then
    if grep -q "^${key}=" .env; then
      sed -i.bak "s|^${key}=.*|${key}=${value}|" .env
    else
      echo "${key}=${value}" >> .env
    fi
  else
    echo "${key}=${value}" > .env
  fi
}

ensure_user_info() {
  local require_prompt="$1" # 'yes' or 'no'

  if [ -z "$ADMIN_USERNAME" ] || [ -z "$ADMIN_EMAIL" ]; then
    if [ "$require_prompt" = "yes" ] && [ "$NON_INTERACTIVE" != "1" ]; then
      info "👤 Setting up user information..."
      if [ -z "$ADMIN_USERNAME" ]; then
        read -p "请输入用户名 (Username): " ADMIN_USERNAME
      fi
      if [ -z "$ADMIN_EMAIL" ]; then
        read -p "请输入邮箱 (Email): " ADMIN_EMAIL
      fi
    else
      if [ -z "$ADMIN_USERNAME" ] || [ -z "$ADMIN_EMAIL" ]; then
        error "❌ 缺少管理员信息: ADMIN_USERNAME/ADMIN_EMAIL 未设置。可在 .env 中设置或以环境变量传入，或移除 --non-interactive 以交互输入。"
        exit 1
      fi
    fi
  fi

  # Validate email format (basic validation)
  case "$ADMIN_EMAIL" in
    *[@]*.*) : ;;  # looks ok
    *) error "❌ 邮箱格式无效，请输入有效的邮箱地址"; exit 1;;
  esac

  export ADMIN_USERNAME
  export ADMIN_EMAIL

  success "✅ 用户信息设置完成:"; echo "  - 用户名: $ADMIN_USERNAME"; echo "  - 邮箱: $ADMIN_EMAIL"; echo ""
}

local_validation_when_no_docker() {
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
  echo ""; info "👉 你可以在安装 Docker 后再次运行本脚本进行完整部署"
}

create_traefik_network() {
  info "🌐 Creating Traefik network..."
  docker network create traefik 2>/dev/null || echo "Network 'traefik' already exists"
}

build_and_start() {
  info "🔨 Building and starting services..."
  docker-compose down --remove-orphans
  if [ "$NO_CACHE" = "1" ]; then
    docker-compose build --no-cache
  else
    docker-compose build
  fi
  docker-compose up -d

  info "⏳ Waiting for services to start..."; sleep 12

  success "✅ Checking service status..."; docker-compose ps

  if command_exists curl; then
    info "🔍 Verifying root path returns index.html..."
    if curl -sSf "http://localhost:61125/" | grep -qi "<div id=\"root\">"; then
      success "✅ Root path served frontend index.html"
    else
      warn "⚠️  Root path content did not match expected HTML"
    fi
  fi

  success "🎉 Deployment completed!"
  echo ""; info "📊 Application:"; echo "  - Local URL: http://localhost:61125"; echo "  - Local API Docs: http://localhost:61125/docs"; echo "  - Production URL: https://a.subx.fun"; echo "";
  info "📁 Data persistence:"; echo "  - Database: ./data/stock_data.db"; echo "";
  info "🔧 Useful commands:"; echo "  - View logs: docker-compose logs -f"; echo "  - Stop services: docker-compose down"; echo "  - Restart: docker-compose restart"
}

run_deploy() {
  info "🚀 Starting deployment of Quant Dashboard..."
  mkdir -p data

  if ! command_exists docker || ! command_exists docker-compose; then
    local_validation_when_no_docker
    return 0
  fi

  create_traefik_network
  build_and_start
}

run_redeploy() {
  info "🔁 Redeploying Quant Dashboard (rebuild + restart)..."
  mkdir -p data

  if ! command_exists docker || ! command_exists docker-compose; then
    warn "⚠️  未检测到 Docker 或 docker-compose，无法重新部署。"
    exit 1
  fi

  create_traefik_network
  build_and_start
}

run_watch() {
  if ! command_exists git; then
    error "❌ watch 模式需要 git，可改用：$0 redeploy"
    exit 1
  fi

  info "👀 正在监视 Git 远程分支变更，发现新提交将自动 git pull 并重新部署（每 10s 检查一次）"

  # 初次执行一次 redeploy
  run_redeploy

  LAST_LOCAL=$(git rev-parse HEAD 2>/dev/null || echo "")
  while true; do
    sleep 10
    # 更新远程信息
    git fetch --all --prune >/dev/null 2>&1 || true
    LOCAL=$(git rev-parse HEAD 2>/dev/null || echo "")
    UPSTREAM=$(git rev-parse @{u} 2>/dev/null || echo "$LOCAL")

    if [ -n "$UPSTREAM" ] && [ "$UPSTREAM" != "$LOCAL" ]; then
      info "📥 检测到远程分支有更新，执行 git pull ..."
      git pull --ff-only || {
        warn "⚠️  git pull 失败，跳过此次自动重新部署"
        continue
      }
      LAST_LOCAL=$(git rev-parse HEAD 2>/dev/null || echo "")
      run_redeploy
    elif [ "$LOCAL" != "$LAST_LOCAL" ]; then
      info "📝 检测到本地提交变更，执行重新部署 ..."
      LAST_LOCAL="$LOCAL"
      run_redeploy
    fi
  done
}

# ---- Main ----
ACTION="deploy"
NON_INTERACTIVE=0

# Parse args
while [ $# -gt 0 ]; do
  case "$1" in
    deploy) ACTION="deploy"; shift;;
    redeploy|-r|--redeploy) ACTION="redeploy"; shift;;
    watch|-w|--watch) ACTION="watch"; shift;;
    --no-cache) NO_CACHE=1; shift;;
    -y|--non-interactive) NON_INTERACTIVE=1; shift;;
    -h|--help) usage; exit 0;;
    *) warn "未知参数: $1"; shift;;
  esac
done

# Load .env values (if any) before prompting
load_env_file

case "$ACTION" in
  deploy)
    # For first-time deploy, allow interactive prompt and persist to .env
    ensure_user_info yes
    write_env_var ADMIN_USERNAME "$ADMIN_USERNAME"
    write_env_var ADMIN_EMAIL "$ADMIN_EMAIL"
    run_deploy
    ;;
  redeploy)
    # For redeploy, try to be non-interactive if env is available
    if [ "$NON_INTERACTIVE" = "1" ]; then
      ensure_user_info no
    else
      # If missing, still prompt interactively and persist
      ensure_user_info yes
      write_env_var ADMIN_USERNAME "$ADMIN_USERNAME"
      write_env_var ADMIN_EMAIL "$ADMIN_EMAIL"
    fi
    run_redeploy
    ;;
  watch)
    # In watch mode, ensure we have env; prompt if allowed
    if [ "$NON_INTERACTIVE" = "1" ]; then
      ensure_user_info no
    else
      ensure_user_info yes
      write_env_var ADMIN_USERNAME "$ADMIN_USERNAME"
      write_env_var ADMIN_EMAIL "$ADMIN_EMAIL"
    fi
    run_watch
    ;;
  *)
    usage; exit 1;;
fi
