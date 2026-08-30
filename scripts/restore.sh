#!/usr/bin/env bash
# restore.sh — 从 pg_dump 备份恢复 HPF Work Manager 数据库
# 用法：./scripts/restore.sh <backup-file.sql.gz|backup-file.sql>
# 示例：./scripts/restore.sh backups/hpf_2026-08-26_03-00-00.sql.gz

set -euo pipefail

BACKUP_FILE="${1:-}"
COMPOSE_FILE="docker-compose.yml"

if [[ -z "$BACKUP_FILE" ]]; then
  echo "用法: $0 <backup-file.sql.gz|backup-file.sql>"
  echo "示例: $0 backups/hpf_2026-08-26_03-00-00.sql.gz"
  exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "错误: 备份文件不存在: $BACKUP_FILE"
  exit 1
fi

# 加载 .env 变量（若存在）
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-hpf}"
POSTGRES_DB="${POSTGRES_DB:-hpf_work}"

echo "=== HPF Work Manager 数据库恢复 ==="
echo "备份文件: $BACKUP_FILE"
echo "数据库用户: $POSTGRES_USER"
echo "数据库名: $POSTGRES_DB"
echo ""

read -rp "这将清空当前数据库并从备份恢复，确定继续？[y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "已取消"
  exit 0
fi

echo ""
echo "1. 停止应用服务（保留 postgres）..."
docker compose -f "$COMPOSE_FILE" stop backend frontend

echo "2. 确保 postgres 运行中..."
docker compose -f "$COMPOSE_FILE" up -d postgres

# 等待 postgres 健康
echo "   等待 postgres 就绪..."
for i in {1..30}; do
  if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "3. 清空并重建 public schema..."
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "4. 从备份恢复..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
  gunzip -c "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
else
  docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_FILE"
fi

echo "5. 启动所有服务（会自动对齐迁移）..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo ""
echo "=== 恢复完成 ==="
echo "请验证："
echo "  curl http://localhost:8080/api/health"
echo "  docker compose ps"