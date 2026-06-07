# Shouna (收纳) - 后端服务部署文档

本项目支持使用 `uv` 进行本地快速开发与调试，以及通过 `Docker` 容器化快速部署。

---

## 🛠 本地开发与调试 (使用 uv)

本地必须安装 [uv](https://github.com/astral-sh/uv) 依赖和虚拟环境管理器。

### 1. 初始化虚拟环境与安装依赖
在 `backend/` 目录下运行：
```bash
uv sync
```

### 2. 数据库迁移
在运行项目前，执行 Alembic 迁移以初始化/更新本地 SQLite 数据库结构：
```bash
.venv/bin/alembic upgrade head
```

### 3. 本地启动服务
```bash
uv run uvicorn app.main:app --reload --port 8000
```
启动后访问接口文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. 运行本地测试
```bash
uv run pytest
```

---

## 🐳 生产环境发布 (使用 Docker 部署)

生产部署采用极简、高效的多阶段构建 Docker 容器，并支持持久化卷挂载。

### 1. 构建 Docker 镜像
Dockerfile 使用官方 `ghcr.io/astral-sh/uv` 构建镜像和 BuildKit 的缓存/绑定挂载语法，在 `backend/` 目录下执行：
```bash
DOCKER_BUILDKIT=1 docker build -t shouna-backend:latest .
```

### 2. 启动 Docker 容器 (推荐使用持久化数据卷挂载 SQLite 和上传图片)
由于默认使用 SQLite 数据库和本地图片存储，容器重建后未挂载的数据会丢失。必须使用 `-v` 参数将主机目录挂载到容器的 `/app/data`，并显式把 `DATABASE_URL` 指向该挂载路径；默认图片上传目录为 `/app/data/uploads`。容器启动命令会先执行 `alembic upgrade head`，再启动 API 服务：

```bash
docker run -d \
  -p 8000:8000 \
  --name shouna-app \
  -v /path/to/host/data:/app/data \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=change-to-a-long-random-secret-at-least-32-bytes \
  -e DATABASE_URL=sqlite:////app/data/shouna.db \
  -e STORAGE_PROVIDER=local \
  -e LOCAL_STORAGE_ROOT=/app/data/uploads \
  -e BACKEND_CORS_ORIGINS='["https://your-frontend.example.com"]' \
  -e AI_PROVIDER=openai \
  -e AI_API_KEY=sk-your-openai-api-key-here \
  -e AI_MODEL=gpt-4o-mini \
  shouna-backend:latest
```

### 3. 一键切换到生产级 PostgreSQL 数据库
如果在生产部署时需要一键切换为 PostgreSQL 数据库，只需动态修改传入的环境变量 `DATABASE_URL` 即可，容器内代码无需做任何修改：

```bash
docker run -d \
  -p 8000:8000 \
  --name shouna-app-postgres \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=change-to-a-long-random-secret-at-least-32-bytes \
  -e DATABASE_URL=postgresql+psycopg://user:password@host:5432/shounadb \
  -e STORAGE_PROVIDER=local \
  -e LOCAL_STORAGE_ROOT=/app/data/uploads \
  -e BACKEND_CORS_ORIGINS='["https://your-frontend.example.com"]' \
  -e AI_PROVIDER=anthropic \
  -e AI_API_KEY=sk-ant-your-anthropic-key-here \
  -e AI_MODEL=claude-3-5-sonnet-latest \
  shouna-backend:latest
```
