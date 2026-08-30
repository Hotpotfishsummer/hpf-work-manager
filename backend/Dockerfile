# ---------- 构建阶段：安装项目与依赖（含原生编译） ----------
FROM python:3.12.6-slim-bookworm AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install .

# ---------- 运行阶段：剥离构建产物，镜像更小 ----------
FROM python:3.12.6-slim-bookworm
WORKDIR /app

# curl 供 compose healthcheck 探测 /api/health；非 root 运行
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin appuser

COPY --from=builder /install /usr/local
COPY alembic ./alembic
COPY alembic.ini ./
COPY app ./app

USER appuser
EXPOSE 8000

# 启动时先执行数据库迁移，再启动 API
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
