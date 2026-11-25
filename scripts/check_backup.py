#!/usr/bin/env python3
"""备份健康检查：确认最近一次 pg_dump 产物是有效备份，而不是空 gzip。

背景：2026-10-16 → 11-25 期间，backup 容器缺 PGPASSWORD，pg_dump 每次都失败，
但 `| gzip >` 仍会生成一个 20 字节的空 gzip 并成功退出，导致 9 天备份全部作废
却毫无告警。本脚本把"产物大小"和"能否解压出 SQL 头"作为硬判据。

用法：
    python3 scripts/check_backup.py                # 默认检查 backups/ 最新一份
    python3 scripts/check_backup.py --dir backups  # 指定目录
    python3 scripts/check_backup.py --max-age-hours 30

退出码：0 = 健康；1 = 异常（无备份 / 过旧 / 空文件 / 内容不完整）。
可挂到 cron 或 systemd timer，异常时由外部告警通道推送。
"""

from __future__ import annotations

import argparse
import gzip
import sys
import time
from pathlib import Path

MIN_BYTES = 1024  # 小于 1KB 必定是空 dump
DUMP_MAGIC = b"PostgreSQL database dump"


def find_latest(backup_dir: Path) -> Path | None:
    files = [p for p in backup_dir.glob("hpf_*.sql.gz") if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 HPF Work Manager 数据库备份是否健康")
    parser.add_argument("--dir", default="backups", help="备份目录（默认 backups）")
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=26.0,
        help="最新备份允许的最大年龄（小时）。默认 26，留 2 小时余量给每日一次的任务",
    )
    args = parser.parse_args()

    backup_dir = Path(args.dir)
    if not backup_dir.is_dir():
        print(f"[FAIL] 备份目录不存在: {backup_dir.resolve()}")
        return 1

    latest = find_latest(backup_dir)
    if latest is None:
        print(f"[FAIL] {backup_dir.resolve()} 下没有任何 hpf_*.sql.gz 备份")
        return 1

    problems: list[str] = []
    size = latest.stat().st_size
    age_hours = (time.time() - latest.stat().st_mtime) / 3600

    if size < MIN_BYTES:
        problems.append(f"产物只有 {size} 字节（< {MIN_BYTES}），是空 dump —— 检查 PGPASSWORD 是否注入")

    if age_hours > args.max_age_hours:
        problems.append(f"最新备份已 {age_hours:.1f} 小时未更新（阈值 {args.max_age_hours}h）")

    # 空文件之外，还要确认解压出来的确实是 pg_dump 的输出
    if not problems:
        try:
            with gzip.open(latest, "rb") as fh:
                head = fh.read(4096)
            if DUMP_MAGIC not in head:
                problems.append("解压后未发现 'PostgreSQL database dump' 头，文件可能已损坏")
        except (OSError, EOFError) as exc:
            problems.append(f"无法解压（gzip 损坏）：{exc}")

    if problems:
        print(f"[FAIL] {latest.name}（{size} 字节，{age_hours:.1f} 小时前）")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"[OK] {latest.name}：{size} 字节，{age_hours:.1f} 小时前，可正常解压")
    return 0


if __name__ == "__main__":
    sys.exit(main())
