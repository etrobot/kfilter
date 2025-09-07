# KFilter 量化投资分析平台

KFilter 是一个基于人工智能的量化投资分析平台，提供股票数据分析、因子选股、概念板块分析等功能，帮助投资者进行数据驱动的投资决策。

## 功能特点

- **多因子选股**：支持动量、支撑位等多种技术指标因子分析
- **K线振幅分析**：可视化展示股票K线走势及振幅
- **概念板块分析**：跟踪分析各行业概念板块表现
- **扩展分析**：提供行业、市场情绪等深度分析
- **响应式设计**：适配桌面和移动设备，支持PWA安装

## 技术栈

### 前端
- React 18 + TypeScript
- Vite 构建工具
- Recharts 数据可视化
- TailwindCSS 样式框架
- PWA 支持

### 后端
- Python 3.10+
- FastAPI 高性能Web框架
- Uvicorn ASGI服务器
- Pandas 数据处理
- SQLModel ORM

### 开发工具
- pnpm 包管理
- UV Python依赖管理
- Docker 容器化部署
- Traefik 反向代理

## 快速开始

### 环境要求

- Node.js 18+ (推荐使用nvm管理)
- Python 3.10+
- pnpm 8.x
- UV (Python包管理工具)
- Docker (可选，用于容器化部署)

### 安装依赖

```bash
# 安装前端依赖
cd frontend
pnpm install

# 安装后端依赖
cd ../backend
uv pip install -r requirements.txt
```

### 开发模式

启动前端开发服务器：

```bash
cd frontend
pnpm dev
```

启动后端开发服务器：

```bash
cd backend
uvicorn main:app --reload
```

### 生产构建

构建前端生产版本：

```bash
cd frontend
pnpm build
```

## 部署

### Docker 部署

1. 复制环境变量文件并配置：

```bash
cp .env.example .env
# 编辑.env文件配置环境变量
```

2. 启动服务：

```bash
docker-compose up -d
```

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| ADMIN_USERNAME | 管理员用户名 | admin |
| ADMIN_EMAIL | 管理员邮箱 | admin@example.com |
| DATABASE_URL | 数据库连接字符串 | sqlite:///data/kfilter.db |

## 项目结构

```
.
├── backend/               # 后端代码
│   ├── data_management/   # 数据管理模块
│   ├── factors/           # 量化因子实现
│   ├── market_data/       # 市场数据获取与处理
│   └── static/            # 静态文件
├── frontend/              # 前端代码
│   ├── app/               # 应用组件
│   └── public/            # 公共资源
├── data/                  # 数据存储目录
└── docker-compose.yml     # Docker编排配置
```

## 贡献指南

欢迎提交Issue和Pull Request。在提交代码前，请确保：

1. 代码符合PEP 8规范
2. 添加适当的单元测试
3. 更新相关文档

## 许可证

MIT
