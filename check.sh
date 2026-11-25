#!/usr/bin/env bash
# check.sh — agent-harness 纪律自检(2026-10-18 新增)
#
# 存在的理由:实测两个真实 harness 项目(clash_config_sync_service / vocab-app)后,
# 结论是「凡是没有机器强制的规则全部失效,凡是有 git diff 可查的规则都守住了」。
# init.sh 查的是**代码基线**;check.sh 查的是**harness 自身有没有烂**。
#
# 退出码:0 = 无硬错(可能带 warn),1 = 有硬错(见 stderr)
#
# 用法:bash check.sh [--quiet]

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; FAILED=1; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
FAILED=0

for f in feature_list.json progress.md; do
  if [ ! -f "$f" ]; then fail "缺 $f,先跑 /init"; exit 1; fi
done

echo "=== A. feature_list.json 结构 ==="
python3 - <<'PY' || FAILED=1
import json, sys, re
raw = json.load(open('feature_list.json'))
bad = 0
expected = {'schema', 'project', 'category_values', 'features'}
extra = set(raw) - expected
if extra:
    print(f"  \033[1;33m⚠\033[0m 顶层键漂移:多了 {sorted(extra)}(模板只定义 schema / project / category_values / features)")
missing = {'project', 'features'} - set(raw)
if missing:
    print(f"  \033[0;31m✗\033[0m 顶层键缺失: {sorted(missing)}"); bad = 1
if raw.get('schema') != 'agent-harness/feature-list@1':
    print(f"  \033[1;33m⚠\033[0m schema 标记缺失或不是 agent-harness/feature-list@1(实际 {raw.get('schema')!r})")
feats = raw.get('features') or []
if not isinstance(feats, list) or not feats:
    print("  \033[0;31m✗\033[0m features 为空或不是数组"); bad = 1
cats = raw.get('category_values')
if not isinstance(cats, list) or not cats:
    cats = ["core", "functional", "style", "ui", "integration", "performance", "security", "api", "docs"]
    print("  \033[1;33m⚠\033[0m 没有 category_values,按默认枚举校验")
odd = sorted({f.get('category') for f in feats} - set(cats))
if odd:
    print(f"  \033[1;33m⚠\033[0m 这些 category 不在 category_values 里: {odd}")
    print("      (要么改回白名单,要么把新值补进 category_values 并在 app_spec.md 写明)")
ids, seen = [], set()
for f in feats:
    fid = f.get('id')
    if not isinstance(fid, str) or not re.fullmatch(r'F\d{3,}', fid):
        print(f"  \033[0;31m✗\033[0m id 格式不对: {fid!r}(应为 F001 这种)"); bad = 1
    if fid in seen:
        print(f"  \033[0;31m✗\033[0m id 重复: {fid}"); bad = 1
    seen.add(fid); ids.append(fid)
    for k in ('passes', 'blocked'):
        if k in f and not isinstance(f[k], bool):
            print(f"  \033[0;31m✗\033[0m {fid}.{k} 必须是布尔,实际 {f[k]!r}"); bad = 1
    for k in ('description', 'steps'):
        if k not in f:
            print(f"  \033[0;31m✗\033[0m {fid} 缺不可改字段 {k}"); bad = 1
if not bad:
    print(f"  \033[0;32m✓\033[0m {len(feats)} 个 feature,id 唯一且格式正确")
json.dump(ids, open('/tmp/.ah_ids.json', 'w'))
sys.exit(bad)
PY

echo ""
echo "=== B. progress.md 引用闭合(硬错) ==="
python3 - <<'PY' || FAILED=1
import json, re, sys
ids = set(json.load(open('/tmp/.ah_ids.json')))
text = open('progress.md', encoding='utf-8').read()
# 只把形如 F012 / [F012] 的当成 feature 引用;排除 F0123 这种解析噪声
refs = set(re.findall(r'\bF\d{3,}\b', text))
dangling = sorted(refs - ids)
never = sorted(ids - refs)
bad = 0
if dangling:
    print(f"  \033[0;31m✗\033[0m progress.md 引用了不存在的 feature: {dangling}")
    print("      (真实事故:vocab-app 引用了 F069~F073 五个不存在的 id,实际最大 F068)")
    bad = 1
else:
    print(f"  \033[0;32m✓\033[0m progress.md 引用的 {len(refs)} 个 id 全部存在")
if ids and len(never) > len(ids) * 0.7:
    print(f"  \033[1;33m⚠\033[0m {len(never)}/{len(ids)} 个 feature 从没在 progress.md 里出现(记录流形同虚设)")
sys.exit(bad)
PY

echo ""
echo "=== C. session 编号/时间单调(硬错) ==="
python3 - <<'PY' || FAILED=1
import re, sys
text = open('progress.md', encoding='utf-8').read()
bad = 0
# 支持两种写法: `--- Session: 2026-10-03 01:30 ---` / `## Session 3: ...`
nums = [int(m) for m in re.findall(r'(?:^|\n)#{1,6}\s*Session\s+(\d+)\b', text)]
if nums:
    if len(set(nums)) != len(nums):
        dup = sorted({n for n in nums if nums.count(n) > 1})
        print(f"  \033[0;31m✗\033[0m session 编号重复: {dup}")
        print("      (真实事故:vocab-app 是 1 2 3 4 5 6 7 8 9 7 10 11 —— 重复 7、缺 12)")
        bad = 1
    elif nums != sorted(nums):
        print(f"  \033[0;31m✗\033[0m session 编号非递增: {nums}")
        bad = 1
    else:
        print(f"  \033[0;32m✓\033[0m {len(nums)} 个 session 段,编号 {nums[0]}..{nums[-1]} 严格递增无重复")
else:
    stamps = re.findall(r'---\s*Session:\s*(\d{4}-\d{2}-\d{2})', text)
    if not stamps:
        print("  \033[1;33m⚠\033[0m 找不到任何 session 段标记(模板约定 `--- Session N: YYYY-MM-DD HH:MM ---`)")
    elif stamps != sorted(stamps):
        print(f"  \033[0;31m✗\033[0m session 时间戳倒序: {stamps}")
        bad = 1
    else:
        print(f"  \033[0;32m✓\033[0m {len(stamps)} 个 session 段,时间戳单调")
sys.exit(bad)
PY

echo ""
echo "=== D. evidence / blocked 覆盖(warn) ==="
python3 - <<'PY'
import json, re
feats = json.load(open('feature_list.json')).get('features', [])
text = open('progress.md', encoding='utf-8').read()
no_ev = [f['id'] for f in feats if f.get('passes') and f['id'] not in text and not str(f.get('notes','')).strip()]
if no_ev:
    print(f"  \033[1;33m⚠\033[0m {len(no_ev)} 个已通过 feature 在 progress.md 与 notes 里都没有任何痕迹: {no_ev[:12]}")
    print("      (passes:true 之前必须有实际跑过的 evidence —— SKILL.md §6.2)")
else:
    print("  \033[0;32m✓\033[0m 所有已通过 feature 都能找到痕迹")
blk = [f['id'] for f in feats if f.get('blocked') or str(f.get('notes','')).startswith('⚠️ 待用户裁决')]
if blk:
    missing = [i for i in blk if i not in text]
    print(f"  \033[1;33m⚠\033[0m {len(blk)} 个 feature 待用户裁决: {blk}")
    print("      本 session 汇报时必须逐条重提(真实事故:F007 标了待裁决后没人再提,烂了 12 天)")
    if missing:
        print(f"  \033[1;33m⚠\033[0m 其中这些在 progress.md 里查不到: {missing}")
PY

echo ""
echo "=== E. description / steps 不可改(红线 1,git 可查) ==="
if git rev-parse --git-dir >/dev/null 2>&1 && git rev-parse HEAD >/dev/null 2>&1; then
  ROOT=$(git rev-list --max-parents=0 HEAD | tail -1)
  if [ -n "$ROOT" ] && git cat-file -e "$ROOT:feature_list.json" 2>/dev/null; then
    N=$(git diff "$ROOT"..HEAD -- feature_list.json 2>/dev/null \
        | grep -cE '^-[^-].*"(description|steps)"' || true)
    if [ "${N:-0}" -gt 0 ]; then
      warn "feature_list.json 自首个 commit 以来删改过 $N 行 description/steps —— 红线 1 被碰过,请人工核对:"
      echo "      git diff $ROOT..HEAD -- feature_list.json | grep -E '^-[^-].*\"(description|steps)\"'"
    else
      pass "description / steps 从未被删改(红线 1 完好)"
    fi
  else
    warn "首个 commit 里没有 feature_list.json,跳过红线 1 检查"
  fi
else
  warn "不是 git 仓库,红线 1 无法用 git 查证"
fi

echo ""
echo "=== F. 未提交改动(warn) ==="
if git rev-parse --git-dir >/dev/null 2>&1; then
  DIRTY=$(git status --porcelain -- app_spec.md feature_list.json progress.md init.sh check.sh AGENTS.md 2>/dev/null || true)
  if [ -n "$DIRTY" ]; then
    warn "harness 文件有未提交改动(收尾前应 commit):"
    echo "$DIRTY" | sed 's/^/      /'
  else
    pass "harness 文件全部已提交"
  fi
fi

echo ""
echo "=========================================="
if [ $FAILED -eq 0 ]; then
  echo -e "${GREEN}✓ check.sh 通过(硬错 0)${NC}"
  exit 0
else
  echo -e "${RED}✗ check.sh 发现硬错,先修上面红色项${NC}"
  exit 1
fi
