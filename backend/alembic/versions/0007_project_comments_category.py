"""项目级评论（工作方向指示）+ 任务分类字段

Revision ID: 0007_project_comments
Revises: 0006_comments
Create Date: 2026-11-25

两件事：
1. comments 表从「只能挂在任务上」扩展为「任务或项目二选一」：
   - task_id 放开为可空，新增 project_id，CHECK 约束保证恰好一个非空
   - 新增 resolved_at：项目指示被落实后标记「已处理」，后续 Agent 不再重复读到
   已有行全部是任务评论，task_id 非空，天然满足约束。
2. tasks 新增 category（feature/bugfix/refactor/testing/docs/devops，可空）。
   存量行按标题关键词做一版保守回填（只是猜测，用户可随时改）；
   关键词按「测试 > 文档 > 排错 > 运维 > 重构 > 新功能」的先后匹配，一个都不中则保持未分类。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007_project_comments"
down_revision: Union[str, None] = "0006_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (分类, 关键词列表) —— 顺序即匹配优先级
_CATEGORY_KEYWORDS: Sequence[tuple[str, Sequence[str]]] = (
    ("testing", ("测试", "test", "pytest", "用例", "回归")),
    ("docs", ("文档", "docs", "readme", "changelog", "注释", "指南")),
    ("bugfix", ("修复", "排错", "bug", "fix", "报错", "故障", "失效")),
    ("devops", ("备份", "部署", "监控", "告警", "docker", "compose", "迁移", "脚本", "cicd", "ci")),
    ("refactor", ("重构", "解耦", "清理", "合并", "瘦身", "refactor")),
    # 兜底：明确写着是新功能的，别留在未分类
    ("feature", ("[feature]", "实现", "新增", "添加", "接入")),
)


def _backfill_sql() -> str:
    """按标题小写做 CASE 匹配；全部不中则为 NULL（未分类）。"""
    whens = []
    for category, keywords in _CATEGORY_KEYWORDS:
        conditions = " OR ".join(f"lower(name) LIKE '%{kw}%'" for kw in keywords)
        whens.append(f"        WHEN {conditions} THEN '{category}'")
    return (
        "UPDATE tasks SET category = CASE\n"
        + "\n".join(whens)
        + "\n        ELSE NULL\n    END\n    WHERE category IS NULL"
    )


def upgrade() -> None:
    # ---- 1. comments：项目锚点 + 已处理时间 ----
    with op.batch_alter_table("comments") as batch:
        batch.alter_column("task_id", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.create_foreign_key(
            "fk_comments_project_id_projects",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        # 恰好一个锚点非空（异或）
        # batch 模式下不需要再传表名
        batch.create_check_constraint(
            "ck_comments_exactly_one_anchor",
            "(task_id IS NOT NULL) <> (project_id IS NOT NULL)",
        )

    op.create_index("ix_comments_project_id", "comments", ["project_id"])
    op.create_index(
        "ix_comments_project_created", "comments", ["project_id", "created_at"]
    )

    # ---- 2. tasks：分类字段 ----
    op.add_column("tasks", sa.Column("category", sa.String(length=20), nullable=True))
    op.create_index("ix_tasks_project_category", "tasks", ["project_id", "category"])
    op.execute(_backfill_sql())


def downgrade() -> None:
    op.drop_index("ix_tasks_project_category", table_name="tasks")
    op.drop_column("tasks", "category")

    op.drop_index("ix_comments_project_created", table_name="comments")
    op.drop_index("ix_comments_project_id", table_name="comments")
    with op.batch_alter_table("comments") as batch:
        batch.drop_constraint("ck_comments_exactly_one_anchor", type_="check")
        batch.drop_constraint("fk_comments_project_id_projects", type_="foreignkey")
        batch.drop_column("resolved_at")
        batch.drop_column("project_id")
        # 回退前必须先清掉项目级评论，否则 NOT NULL 约束加不回去
        op.execute("DELETE FROM comments WHERE task_id IS NULL")
        batch.alter_column("task_id", existing_type=sa.Integer(), nullable=False)
