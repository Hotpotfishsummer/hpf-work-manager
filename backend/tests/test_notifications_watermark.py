"""通知已读水位端点测试（B8）。"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_get_watermark_default_null(auth_client):
    resp = await auth_client.get("/api/notifications/watermark")
    assert resp.status_code == 200
    assert resp.json()["last_read_at"] is None


async def test_put_then_get_watermark(auth_client):
    resp = await auth_client.put(
        "/api/notifications/watermark",
        json={"last_read_at": "2026-09-03T00:05:00+00:00"},
    )
    assert resp.status_code == 200
    assert resp.json()["last_read_at"].startswith("2026-09-03T00:05:00")

    resp = await auth_client.get("/api/notifications/watermark")
    assert resp.json()["last_read_at"].startswith("2026-09-03T00:05:00")


async def test_watermark_never_regresses(auth_client):
    """多设备场景：旧时间戳不允许覆盖新水位。"""
    resp = await auth_client.put(
        "/api/notifications/watermark",
        json={"last_read_at": "2026-09-03T02:00:00+00:00"},
    )
    assert resp.status_code == 200

    resp = await auth_client.put(
        "/api/notifications/watermark",
        json={"last_read_at": "2026-09-03T00:05:00+00:00"},
    )
    assert resp.status_code == 200
    assert resp.json()["last_read_at"].startswith("2026-09-03T02:00:00")


async def test_watermark_accepts_naive_utc(auth_client):
    """无时区的时间戳按 UTC 解释。"""
    resp = await auth_client.put(
        "/api/notifications/watermark",
        json={"last_read_at": "2026-09-03T01:00:00"},
    )
    assert resp.status_code == 200
    assert resp.json()["last_read_at"].startswith("2026-09-03T01:00:00")


async def test_watermark_per_user_isolated(auth_client, other_auth_client):
    await auth_client.put(
        "/api/notifications/watermark",
        json={"last_read_at": "2026-09-03T01:00:00+00:00"},
    )
    # 用户 B 的水位仍是独立的 null
    resp = await other_auth_client.get("/api/notifications/watermark")
    assert resp.json()["last_read_at"] is None
