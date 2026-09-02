"""任务评论端点测试（B7）。"""

import pytest

pytestmark = pytest.mark.asyncio


async def _create_task(auth_client, test_project, name="带评论的任务") -> int:
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/tasks", json={"name": name}
    )
    return resp.json()["id"]


async def test_comment_crud(auth_client, test_project):
    tid = await _create_task(auth_client, test_project)

    # 创建
    resp = await auth_client.post(
        f"/api/tasks/{tid}/comments", json={"content": "第一版实现完成"}
    )
    assert resp.status_code == 201
    cid = resp.json()["id"]
    assert resp.json()["content"] == "第一版实现完成"
    assert resp.json()["author_username"] == "testuser"

    # 列表（升序）
    await auth_client.post(f"/api/tasks/{tid}/comments", json={"content": "修复评审意见"})
    resp = await auth_client.get(f"/api/tasks/{tid}/comments")
    assert resp.status_code == 200
    contents = [c["content"] for c in resp.json()]
    assert contents == ["第一版实现完成", "修复评审意见"]

    # 删除
    resp = await auth_client.delete(f"/api/comments/{cid}")
    assert resp.status_code == 204
    resp = await auth_client.get(f"/api/tasks/{tid}/comments")
    assert [c["content"] for c in resp.json()] == ["修复评审意见"]


async def test_comment_validation(auth_client, test_project):
    tid = await _create_task(auth_client, test_project)
    resp = await auth_client.post(f"/api/tasks/{tid}/comments", json={"content": ""})
    assert resp.status_code == 422
    resp = await auth_client.post(
        f"/api/tasks/{tid}/comments", json={"content": "x" * 2001}
    )
    assert resp.status_code == 422


async def test_comment_isolation(other_auth_client, test_task, db_session):
    """用户 B 不能读写用户 A 的任务评论。"""
    from app.models import Comment

    db_session.add(
        Comment(task_id=test_task.id, author_id=None, author_username="testuser", content="A 的评论")
    )
    await db_session.commit()

    resp = await other_auth_client.get(f"/api/tasks/{test_task.id}/comments")
    assert resp.status_code == 404

    resp = await other_auth_client.post(
        f"/api/tasks/{test_task.id}/comments", json={"content": "越权"}
    )
    assert resp.status_code == 404

    resp = await other_auth_client.delete("/api/comments/1")
    assert resp.status_code == 404


async def test_task_delete_cascades_comments(auth_client, test_project, db_session):
    """删除任务后评论级联删除。"""
    from sqlalchemy import func, select

    from app.models import Comment

    tid = await _create_task(auth_client, test_project)
    await auth_client.post(f"/api/tasks/{tid}/comments", json={"content": "x"})
    db_session.expire_all()
    count = (
        await db_session.execute(select(func.count(Comment.id)))
    ).scalar_one()
    assert count == 1

    resp = await auth_client.delete(f"/api/tasks/{tid}")
    assert resp.status_code == 204
    db_session.expire_all()  # REST 在另一会话提交，需刷新本会话快照
    count = (
        await db_session.execute(select(func.count(Comment.id)))
    ).scalar_one()
    assert count == 0
