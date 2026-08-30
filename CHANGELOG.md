# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循语义化版本（SemVer）。

## [0.2.0] - 2026-08-26

### 安全加固
- `SECRET_KEY` 在非 dev 环境下 fail-fast：默认值或长度 <32 直接拒绝启动
- 登录 / 注册 / API Key 兑换 5/min/IP 限流，SSE 流 60/min/IP（slowapi + nginx limit_req 双层）
- MCP 工具补齐枚举校验（status/priority 白名单），与 REST 对齐；非法日期返回明确错误
- 任务关联跨项目里程碑被拒绝（REST 与 MCP 双侧校验归属）
- CSV 导出防公式注入（`=+-@` 前缀单元格加单引号）；导出文件名净化
- nginx 增加 CSP、X-Content-Type-Options、X-Frame-Options、HSTS、Referrer-Policy 安全头
- 基础镜像 digest 级 pin（python:3.12.6-slim-bookworm / node:22.11-alpine / nginx:1.27-alpine / postgres:16.6-alpine）
- 后端依赖从 `>=` 收敛为 `~=`，移除未使用的 sass-embedded

### 正确性修复
- 修复 token 过期后 401 无限重定向循环（拦截器同步清空 Pinia store）
- 全局异常处理器：IntegrityError→409、DataError/ValueError→422，不再泄露 500
- 注册并发冲突返回 409 而非 500
- 批量更新 ids 上限 100；批量更新 SSE 广播真实任务 id（此前恒为 0）
- 甘特图"今天"标记改用本地时区（此前 UTC 导致东八区凌晨日期错位）

### 可靠性与可观测性
- `/api/health` 升级为 DB 感知探活（SELECT 1 失败返回 503），接入 compose healthcheck
- backend / frontend 增加 healthcheck；frontend 等 backend healthy 后才启动
- 新增结构化 JSON 请求日志中间件（request_id、latency_ms、X-Request-ID）

### 性能
- ECharts 改按需引入（echarts/core），chunk 由 ~1.0MB 降至 ~0.5MB
- Inter 字体仅加载 latin 子集
- nginx 开启 gzip；静态资源 immutable 长缓存；index.html no-cache

### 工程化
- 后端测试 pytest 化（pytest-asyncio + httpx），新增 auth/pagination/errors/enums 用例
- 前端新增 Vitest（csv/auth/pagination 用例）
- GitHub Actions CI：ruff + pytest + alembic --sql + vue-tsc + build + bundle 体积门槛
- 新增 pg_dump 每日备份 sidecar（保留 7 天）与 scripts/restore.sh 一键恢复
- docker-compose 支持 image 标签（TAG 变量）；frontend/.dockerignore 补齐 node_modules/dist
- 文档失真修复（部署指南健康状态描述、依赖锁定说明等）

## [0.1.0] - 初始版本

- 项目 / 里程碑 / 任务 / 依赖管理，进度追踪（甘特图、燃尽图、延期预警）
- JWT 认证与 API Key（MCP Server 34 工具接入）、SSE 实时推送
- DevLog / DevSession 开发过程记录
