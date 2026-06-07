# ==========================================
# 阶段 1: 依赖构建阶段 (Builder)
# ==========================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# 禁用 uv 遥测和缓存行为，启用独立构建
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# 拷贝项目定义文件并锁版本安装
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

# ==========================================
# 阶段 2: 最终极简运行阶段 (Runner)
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# 设置环境变量，确保 Python 输出流畅无缓存，并指定系统运行路径
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
ENV LOCAL_STORAGE_ROOT=/app/data/uploads

# 创建专用于持久化挂载本地 SQLite 数据和上传图片的目录
RUN mkdir -p /app/data/uploads

# 从构建器中直接拷贝预编译好的虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 拷贝应用程序代码
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

# 声明对外暴露的端口
EXPOSE 8000

# 声明持久化数据卷挂载点 (用于本地挂载 SQLite 数据文件和上传图片)
# 默认 SQLite 文件应通过 DATABASE_URL 指向 /app/data/shouna.db
# 默认本地上传图片目录由 LOCAL_STORAGE_ROOT 指向 /app/data/uploads
VOLUME ["/app/data"]

# 默认启动指令：先执行数据库迁移，再运行 Uvicorn 服务
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
