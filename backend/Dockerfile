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

# 启动时先执行数据库迁移，再启动 API。
# --proxy-headers：经 nginx 反代后从 X-Forwarded-For 恢复真实客户端 IP，
# 否则 slowapi 按 remote_address 限流会退化为"全站共享一个桶"；
# 仅信任内网网段（后端 8000 不对外发布，X-Forwarded-For 只能来自 compose 网络）。
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"]
