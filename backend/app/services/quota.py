import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import httpx

# CST 时区 (UTC+8)
CST = timezone(timedelta(hours=8))


class QuotaService:
    def __init__(self):
        self._cached_data: Dict[str, Any] | None = None
        self._last_fetched: float = 0
        self._cache_ttl: float = 10.0  # 10秒缓存避免频繁击穿
        # 密钥只从环境变量读取（docker compose 的 .env 注入）。
        # 代码里绝不写默认值：本仓库是公开的，硬编码 key 等于公开泄露。
        self.api_key = os.getenv("MINIMAX_API_KEY", "")

    async def get_quota_status(self) -> Dict[str, Any]:
        now = time.time()
        if self._cached_data and (now - self._last_fetched < self._cache_ttl):
            return self._cached_data

        # 未配置密钥时直接降级，不发出无凭证请求（否则表现为 401 而非"未配置"）
        if not self.api_key:
            return {
                "ok": False,
                "remaining_percent": 0,
                "minutes_left": 0,
                "reset_time_str": "--:--:--",
                "is_night_shift": False,
                "suggestion": "未配置 MINIMAX_API_KEY，算力雷达不可用（在 .env 中设置后重启 backend）",
                "error": "MINIMAX_API_KEY not configured",
            }

        url = "https://api.minimax.cn/v1/token_plan/remains"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "HarnessPilot-WorkManager/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    general = None
                    for m in data.get("model_remains", []):
                        if m.get("model_name") == "general":
                            general = m
                            break

                    if general:
                        remains_ms = general.get("remains_time", 0)
                        end_time_ms = general.get("end_time", 0)
                        remaining_percent = general.get("current_interval_remaining_percent", 0)
                        weekly_remaining_percent = general.get("current_weekly_remaining_percent", 0)

                        reset_dt = datetime.fromtimestamp(end_time_ms / 1000, tz=CST)
                        reset_time_str = reset_dt.strftime("%H:%M:%S")

                        minutes_left = max(0, int(remains_ms / 60000))

                        # 判断是否处于夜间闲时 (23:00 - 07:00)
                        current_hour = datetime.now(tz=CST).hour
                        is_night_shift = current_hour >= 23 or current_hour < 7

                        if remaining_percent <= 5:
                            if minutes_left <= 30:
                                suggestion = f"当前5h额度仅剩 {remaining_percent}%，即将于 {minutes_left} 分钟后（{reset_time_str}）刷新！建议先在看板规划挂单。"
                            else:
                                suggestion = f"当前5h额度已用尽（剩{remaining_percent}%），将在 {minutes_left} 分钟后（{reset_time_str}）重置。"
                        elif minutes_left <= 45 and remaining_percent >= 30:
                            suggestion = f"⚠️ 距窗口重置仅剩 {minutes_left} 分钟，尚有 {remaining_percent}% 额度！建议派遣保底海绵任务（如单元测试/文档重构）充分利用！"
                        elif is_night_shift:
                            suggestion = f"当前处于深夜闲时，5h额度充裕（{remaining_percent}%），适合安排长跑无人值守任务！"
                        else:
                            suggestion = f"5h额度状态良好（剩余 {remaining_percent}%），离下次刷新还有 {minutes_left} 分钟。"

                        res = {
                            "ok": True,
                            "remaining_percent": remaining_percent,
                            "weekly_remaining_percent": weekly_remaining_percent,
                            "remains_ms": remains_ms,
                            "minutes_left": minutes_left,
                            "end_time_ms": end_time_ms,
                            "reset_time_str": reset_time_str,
                            "is_night_shift": is_night_shift,
                            "suggestion": suggestion,
                            "fetched_at": int(now * 1000),
                        }
                        self._cached_data = res
                        self._last_fetched = now
                        return res
        except Exception as e:
            if self._cached_data:
                return {**self._cached_data, "stale": True, "error": str(e)}
            return {
                "ok": False,
                "remaining_percent": 0,
                "weekly_remaining_percent": 0,
                "minutes_left": 0,
                "reset_time_str": "--:--:--",
                "is_night_shift": False,
                "suggestion": f"配额状态异常: {e}",
                "error": str(e),
            }

        return {
            "ok": False,
            "remaining_percent": 0,
            "minutes_left": 0,
            "reset_time_str": "--:--:--",
            "suggestion": "未获取到 general 模型配额窗口",
        }

    async def get_driver_mode(self) -> Dict[str, Any]:
        """评估当前驱动模式：内部Token充足时为 DUAL_CERTIFIED（双重认证），耗尽时为 EXTERNAL_DRIVEN（外驱降级）"""
        status = await self.get_quota_status()
        remaining = status.get("remaining_percent", 0)
        ok = status.get("ok", False)
        # 判定是否有内部可用 Token：接口正常且剩余比例 > 5%
        has_internal_tokens = bool(ok and remaining > 5)

        if has_internal_tokens:
            mode = "DUAL_CERTIFIED"
            mode_desc = "双重认证协同模式 (Dual-Agent Consensus Active)"
            guidelines = (
                "内部 MiniMax 算力充足。外部 Agent 在此模式下提交的规划提案将经过内部架构师"
                "模型的交叉校验（Cross-Audit），消除幻觉并确保工程可行性；完成任务需附带 git 提交凭据以盖章封存。"
            )
        else:
            mode = "EXTERNAL_DRIVEN"
            mode_desc = "外部单驱降级模式 (External-Driven Safe Mode)"
            guidelines = (
                "内部 MiniMax 算力已耗尽或受限。管理器已切换为确定性安全护栏模式（零内部Token消耗）。"
                "外部 Agent 承担主要规划与执行职责，必须严格遵守任务契约规范（明确步骤、验收标准、合理工时），"
                "并提供真实 git_ref 进行任务核验与归档。"
            )

        return {
            "driver_mode": mode,
            "mode_desc": mode_desc,
            "has_internal_tokens": has_internal_tokens,
            "quota_status": status,
            "guidelines": guidelines,
        }


quota_service = QuotaService()
