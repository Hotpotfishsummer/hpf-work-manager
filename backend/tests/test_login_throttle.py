"""登录账号级限流（login_throttle）测试（B3）。"""

import pytest


@pytest.fixture(autouse=True)
def _clean_throttle():
    from app.core import login_throttle

    login_throttle.reset()
    yield
    login_throttle.reset()


def test_throttle_triggers_after_max_failures():
    from app.core.login_throttle import MAX_FAILURES, check_throttled, record_failure

    for _ in range(MAX_FAILURES - 1):
        record_failure("alice")
        assert not check_throttled("alice")
    record_failure("alice")
    assert check_throttled("alice")


def test_success_resets_counter():
    from app.core.login_throttle import (
        MAX_FAILURES,
        check_throttled,
        record_failure,
        record_success,
    )

    for _ in range(MAX_FAILURES):
        record_failure("alice")
    assert check_throttled("alice")
    record_success("alice")
    assert not check_throttled("alice")


def test_failures_expire_outside_window():

    from app.core import login_throttle

    for _ in range(login_throttle.MAX_FAILURES):
        login_throttle.record_failure("alice")
    assert login_throttle.check_throttled("alice")
    # 时间快进越过窗口
    orig = login_throttle.time.monotonic
    login_throttle.time.monotonic = lambda: orig() + login_throttle.WINDOW_SECONDS + 1
    try:
        assert not login_throttle.check_throttled("alice")
        assert "alice" not in login_throttle._failures  # 空窗口已清理
    finally:
        login_throttle.time.monotonic = orig


def test_users_tracked_independently():
    from app.core.login_throttle import MAX_FAILURES, check_throttled, record_failure

    for _ in range(MAX_FAILURES):
        record_failure("alice")
    assert check_throttled("alice")
    assert not check_throttled("bob")


@pytest.mark.asyncio
async def test_login_returns_429_when_throttled(auth_client, test_user, monkeypatch):
    """接线验证：check_throttled 命中时登录端点直接 429，不校验凭证。"""
    import app.routers.auth as auth_router

    monkeypatch.setattr(auth_router, "check_throttled", lambda username: True)
    resp = await auth_client.post(
        "/api/auth/login",
        json={"username": test_user.username, "password": "wrong-password"},
    )
    assert resp.status_code == 429
