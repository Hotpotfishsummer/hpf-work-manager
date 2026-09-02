"""Enum validation tests for task status, priority, dev_log types, etc."""

import os

import pytest
from pydantic import ValidationError

_mcp_disabled = os.environ.get("MCP_ENABLED", "true").lower() == "false"
_requires_mcp = pytest.mark.skipif(_mcp_disabled, reason="MCP_ENABLED=false in this test run")


class TestTaskEnums:
    """Test task-related enum validations."""

    def test_task_status_valid(self):
        """Test valid task status values."""
        from app.schemas.task import TASK_STATUS, TaskCreate

        for status in TASK_STATUS:
            task = TaskCreate(name="Test", status=status)
            assert task.status == status

    def test_task_status_invalid(self):
        """Test invalid task status raises error."""
        from app.schemas.task import TaskCreate

        with pytest.raises(ValidationError, match="status 必须为"):
            TaskCreate(name="Test", status="invalid")

    def test_task_priority_valid(self):
        """Test valid task priority values."""
        from app.schemas.task import TASK_PRIORITY, TaskCreate

        for priority in TASK_PRIORITY:
            task = TaskCreate(name="Test", priority=priority)
            assert task.priority == priority

    def test_task_priority_invalid(self):
        """Test invalid task priority raises error."""
        from app.schemas.task import TaskCreate

        with pytest.raises(ValidationError, match="priority 必须为"):
            TaskCreate(name="Test", priority="invalid")

    def test_task_progress_bounds(self):
        """Test task progress bounds validation."""
        from app.schemas.task import TaskCreate

        # Valid bounds
        task = TaskCreate(name="Test", progress=0)
        assert task.progress == 0

        task = TaskCreate(name="Test", progress=100)
        assert task.progress == 100

        task = TaskCreate(name="Test", progress=50)
        assert task.progress == 50

        # Invalid bounds
        with pytest.raises(ValidationError):
            TaskCreate(name="Test", progress=-1)

        with pytest.raises(ValidationError):
            TaskCreate(name="Test", progress=101)

    def test_task_update_partial(self):
        """Test TaskUpdate allows partial updates."""
        from app.schemas.task import TaskUpdate

        update = TaskUpdate(status="done")
        assert update.status == "done"
        assert update.priority is None
        assert update.progress is None

        update = TaskUpdate(priority="high", progress=75)
        assert update.priority == "high"
        assert update.progress == 75
        assert update.status is None


class TestDevLogEnums:
    """Test dev log enum validations."""

    def test_dev_log_entry_type_valid(self):
        """Test valid dev log entry types."""
        from app.schemas.dev_log import DEV_LOG_TYPES, DevLogCreate

        for entry_type in DEV_LOG_TYPES:
            log = DevLogCreate(entry_type=entry_type, title="Test")
            assert log.entry_type == entry_type

    def test_dev_log_entry_type_invalid(self):
        """Test invalid dev log entry type raises error."""
        from app.schemas.dev_log import DevLogCreate

        with pytest.raises(ValidationError, match="entry_type 必须为"):
            DevLogCreate(entry_type="invalid", title="Test")

    def test_dev_log_status_valid(self):
        """Test valid dev log status values."""
        from app.schemas.dev_log import DEV_LOG_STATUS, DevLogCreate

        for status in DEV_LOG_STATUS:
            log = DevLogCreate(entry_type="todo", title="Test", status=status)
            assert log.status == status

    def test_dev_log_status_invalid(self):
        """Test invalid dev log status raises error."""
        from app.schemas.dev_log import DevLogCreate

        with pytest.raises(ValidationError, match="status 必须为"):
            DevLogCreate(entry_type="todo", title="Test", status="invalid")

    def test_dev_log_severity_valid(self):
        """Test valid dev log severity values."""
        from app.schemas.dev_log import SEVERITY, DevLogCreate

        for severity in SEVERITY:
            log = DevLogCreate(entry_type="difficulty", title="Test", severity=severity)
            assert log.severity == severity

    def test_dev_log_severity_invalid(self):
        """Test invalid dev log severity raises error."""
        from app.schemas.dev_log import DevLogCreate

        with pytest.raises(ValidationError, match="severity 必须为"):
            DevLogCreate(entry_type="difficulty", title="Test", severity="invalid")

    def test_dev_log_severity_only_for_difficulty_blocker(self):
        """Test severity only allowed for difficulty/blocker types."""
        from app.schemas.dev_log import DevLogCreate

        # Valid for difficulty
        log = DevLogCreate(entry_type="difficulty", title="Test", severity="high")
        assert log.severity == "high"

        # Valid for blocker
        log = DevLogCreate(entry_type="blocker", title="Test", severity="high")
        assert log.severity == "high"

        # Invalid for progress
        with pytest.raises(ValidationError, match="severity 仅可用于"):
            DevLogCreate(entry_type="progress", title="Test", severity="high")

        # Invalid for todo
        with pytest.raises(ValidationError, match="severity 仅可用于"):
            DevLogCreate(entry_type="todo", title="Test", severity="high")

        # Invalid for decision
        with pytest.raises(ValidationError, match="severity 仅可用于"):
            DevLogCreate(entry_type="decision", title="Test", severity="high")

        # Invalid for note
        with pytest.raises(ValidationError, match="severity 仅可用于"):
            DevLogCreate(entry_type="note", title="Test", severity="high")

    def test_dev_log_status_done_only_for_todo_blocker(self):
        """Test status=done only allowed for todo/blocker types."""
        from app.schemas.dev_log import DevLogCreate

        # Valid for todo
        log = DevLogCreate(entry_type="todo", title="Test", status="done")
        assert log.status == "done"

        # Valid for blocker
        log = DevLogCreate(entry_type="blocker", title="Test", status="done")
        assert log.status == "done"

        # Invalid for progress
        with pytest.raises(ValidationError, match="status 仅可用于"):
            DevLogCreate(entry_type="progress", title="Test", status="done")

        # Invalid for difficulty
        with pytest.raises(ValidationError, match="status 仅可用于"):
            DevLogCreate(entry_type="difficulty", title="Test", status="done")

        # Invalid for decision
        with pytest.raises(ValidationError, match="status 仅可用于"):
            DevLogCreate(entry_type="decision", title="Test", status="done")

        # Invalid for note
        with pytest.raises(ValidationError, match="status 仅可用于"):
            DevLogCreate(entry_type="note", title="Test", status="done")

    def test_dev_log_update_partial(self):
        """Test DevLogUpdate allows partial updates."""
        from app.schemas.dev_log import DevLogUpdate

        update = DevLogUpdate(status="done")
        assert update.status == "done"
        assert update.severity is None
        assert update.entry_type is None

        update = DevLogUpdate(severity="high", content="Updated")
        assert update.severity == "high"
        assert update.content == "Updated"
        assert update.status is None


class TestProjectEnums:
    """Test project-related enum validations."""

    def test_project_status_valid(self):
        """合法项目状态（模型层仅 active/archived，P5 起端点层校验枚举）。"""
        from app.schemas.project import ProjectUpdate

        for status in ["active", "archived"]:
            proj = ProjectUpdate(name="Test", status=status)
            assert proj.status == status


class TestMilestoneEnums:
    """Test milestone enum validations."""

    def test_milestone_status_valid(self):
        """Test valid milestone status values."""
        from app.schemas.milestone import MilestoneUpdate

        for status in ["pending", "completed", "cancelled"]:
            ms = MilestoneUpdate(name="Test", status=status)
            assert ms.status == status


class TestMCPToolEnums:
    """Test MCP tool parameter enum validations."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("MCP_ENABLED", "true").lower() == "false", reason="no MCP"
    )
    async def test_mcp_create_task_status_enum(self, mcp_client, test_project):
        """Test MCP create_task validates status enum."""
        sid = await test_mcp_auth_initialize(mcp_client)
        headers = {**mcp_client.headers, "mcp-session-id": sid}

        # Valid status
        resp = await mcp_client.post(
            "/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "create_task",
                    "arguments": {"project_id": test_project.id, "name": "Test", "status": "todo"},
                },
            },
        )
        assert resp.status_code == 200

        # Invalid status - should return error in JSON-RPC response
        resp = await mcp_client.post(
            "/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "create_task",
                    "arguments": {"project_id": test_project.id, "name": "Test", "status": "invalid"},
                },
            },
        )
        data = parse_sse_text(resp.text)
        result = (data or {}).get("result") or {}
        assert resp.status_code != 200 or "error" in data or result.get("isError")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("MCP_ENABLED", "true").lower() == "false", reason="no MCP"
    )
    async def test_mcp_create_task_priority_enum(self, mcp_client, test_project):
        """Test MCP create_task validates priority enum."""
        sid = await test_mcp_auth_initialize(mcp_client)
        headers = {**mcp_client.headers, "mcp-session-id": sid}

        # Valid priority
        for priority in ["low", "medium", "high"]:
            resp = await mcp_client.post(
                "/mcp/",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "create_task",
                        "arguments": {
                            "project_id": test_project.id,
                            "name": f"Test {priority}",
                            "priority": priority,
                        },
                    },
                },
            )
            assert resp.status_code == 200

        # Invalid priority
        resp = await mcp_client.post(
            "/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "create_task",
                    "arguments": {
                        "project_id": test_project.id,
                        "name": "Test",
                        "priority": "invalid",
                    },
                },
            },
        )
        data = parse_sse_text(resp.text)
        result = (data or {}).get("result") or {}
        assert resp.status_code != 200 or "error" in data or result.get("isError")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("MCP_ENABLED", "true").lower() == "false", reason="no MCP"
    )
    async def test_mcp_log_difficulty_severity_enum(self, mcp_client, test_project):
        """Test MCP log_difficulty validates severity enum."""
        sid = await test_mcp_auth_initialize(mcp_client)
        headers = {**mcp_client.headers, "mcp-session-id": sid}

        # Valid severity
        for severity in ["low", "medium", "high"]:
            resp = await mcp_client.post(
                "/mcp/",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "log_difficulty",
                        "arguments": {
                            "project_id": test_project.id,
                            "title": f"Test {severity}",
                            "severity": severity,
                        },
                    },
                },
            )
            assert resp.status_code == 200

        # Invalid severity
        resp = await mcp_client.post(
            "/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "log_difficulty",
                    "arguments": {
                        "project_id": test_project.id,
                        "title": "Test",
                        "severity": "invalid",
                    },
                },
            },
        )
        data = parse_sse_text(resp.text)
        result = (data or {}).get("result") or {}
        assert resp.status_code != 200 or "error" in data or result.get("isError")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("MCP_ENABLED", "true").lower() == "false", reason="no MCP"
    )
    async def test_mcp_log_blocker_severity_enum(self, mcp_client, test_project):
        """Test MCP log_blocker validates severity enum."""
        sid = await test_mcp_auth_initialize(mcp_client)
        headers = {**mcp_client.headers, "mcp-session-id": sid}

        # Valid severity
        for severity in ["low", "medium", "high"]:
            resp = await mcp_client.post(
                "/mcp/",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "log_blocker",
                        "arguments": {
                            "project_id": test_project.id,
                            "title": f"Test {severity}",
                            "severity": severity,
                        },
                    },
                },
            )
            assert resp.status_code == 200

        # Invalid severity
        resp = await mcp_client.post(
            "/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "log_blocker",
                    "arguments": {
                        "project_id": test_project.id,
                        "title": "Test",
                        "severity": "invalid",
                    },
                },
            },
        )
        data = parse_sse_text(resp.text)
        result = (data or {}).get("result") or {}
        assert resp.status_code != 200 or "error" in data or result.get("isError")


def parse_sse_text(txt: str) -> dict | None:
    import json
    for line in txt.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


async def test_mcp_auth_initialize(mcp_client):
    """Helper to initialize MCP session."""
    resp = await mcp_client.post(
        "/mcp/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "1"},
            },
        },
    )
    assert resp.status_code == 200
    return resp.headers.get("mcp-session-id")

@pytest.mark.asyncio
async def test_project_update_status_enum_rejected(auth_client, test_project):
    """ProjectUpdate.status 枚举校验：任意字符串 → 422。"""
    resp = await auth_client.put(
        f"/api/projects/{test_project.id}", json={"status": "bogus"}
    )
    assert resp.status_code == 422
    resp = await auth_client.put(
        f"/api/projects/{test_project.id}", json={"status": "archived"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"
