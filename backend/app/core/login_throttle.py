"""按用户名的登录失败慢速限流（内存实现，进程重启即清零）。

IP 级限流由 slowapi 承担（配合 uvicorn --proxy-headers 经反代后仍按真实 IP）；
此处补充账号维度：同一用户名在滑动窗口内失败超过阈值后暂时拒绝登录，
缓解绕过 IP 限流的账号级密码爆破。成功登录立即清零计数。
"""

import time

WINDOW_SECONDS = 300  # 滑动窗口
MAX_FAILURES = 10  # 窗口内最大失败次数
_MAX_TRACKED = 10_000  # 防 dict 无界增长（被刷大量用户名时）

_failures: dict[str, list[float]] = {}


def _prune(username: str, now: float) -> list[float]:
    window = [t for t in _failures.get(username, ()) if now - t < WINDOW_SECONDS]
    if window:
        _failures[username] = window
    else:
        _failures.pop(username, None)
    return window


def check_throttled(username: str) -> bool:
    now = time.monotonic()
    return len(_prune(username, now)) >= MAX_FAILURES


def record_failure(username: str) -> None:
    now = time.monotonic()
    _prune(username, now)
    if len(_failures) >= _MAX_TRACKED and username not in _failures:
        return  # 极端情况下放弃记账（可用性优先）
    _failures.setdefault(username, []).append(now)


def record_success(username: str) -> None:
    _failures.pop(username, None)


def reset() -> None:
    """仅测试使用：清空全部计数。"""
    _failures.clear()
