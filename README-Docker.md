# Docker 部署指南

这是一个前后端一体的量化分析项目，使用单个Docker容器部署，配合Traefik实现域名访问和SSL证书。

## 快速部署

### 前提条件
- 已安装Docker和Docker Compose
- 已安装并配置Traefik
- 域名 `a.subx.fun` 指向服务器

### 部署步骤

1. **运行部署脚本**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

2. **访问应用**
   - 本地测试: http://localhost:61125
   - 本地API文档: http://localhost:61125/docs
   - 生产环境: https://a.subx.fun

## 配置说明

### Docker配置
- **单容器部署**: 前端构建后集成到后端静态文件服务
- **数据持久化**: `./data/stock_data.db` 映射到容器内数据库
- **端口**: 容器内8000端口

### Traefik Labels
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.quant.rule=Host(`a.subx.fun`)"
  - "traefik.http.routers.quant.entrypoints=websecure"
  - "traefik.http.routers.quant.tls.certresolver=letsencrypt"
  - "traefik.http.services.quant.loadbalancer.server.port=8000"
```

## 管理命令

```bash
# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 重新构建
docker-compose build --no-cache
docker-compose up -d

# 进入容器
docker-compose exec app bash
```

## 数据备份

```bash
# 备份数据库
cp data/stock_data.db backups/stock_data_$(date +%Y%m%d).db
```

## 故障排除

### 服务无法启动
```bash
# 检查日志
docker-compose logs

# 检查网络
docker network ls | grep traefik
```

### SSL证书问题
确保Traefik已正确配置Let's Encrypt，并且域名DNS解析正确。

### 数据库问题
```bash
# 检查数据目录权限
ls -la data/

# 检查数据库文件
sqlite3 data/stock_data.db ".tables"
```