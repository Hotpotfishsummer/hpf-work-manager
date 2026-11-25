#!/usr/bin/env bash
# init.sh — agent-harness 自检脚本
# 作用:每次开工前跑一次,确认基线干净 + 核心依赖能起 + 回归没炸
# 退出码:0 = 全绿,1 = 有问题(看 stderr)
#
# 用法:
#   bash init.sh          # 自检
#   bash init.sh --fix    # 尝试自动修复(可选,看具体项目)

set -euo pipefail

# ---- 配色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; FAILED=1; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }

FAILED=0

# ---- 1. pwd + 项目根确认 ----
echo "=== 1. 项目根确认 ==="
if [ -f "app_spec.md" ] && [ -f "feature_list.json" ] && [ -f "progress.md" ]; then
  pass "harness 三件套齐全 (app_spec.md / feature_list.json / progress.md)"
else
  fail "harness 三件套不全,先跑 /init"
  exit 1
fi

# ---- 2. git 仓库 ----
echo ""
echo "=== 2. Git 仓库 ==="
if git rev-parse --git-dir >/dev/null 2>&1; then
  pass "git 仓库已初始化"
  echo "  最近 5 个 commit:"
  git log --oneline -5 | sed 's/^/    /'
else
  fail "不是 git 仓库,跑:git init && git add -A && git commit -m 'chore: init agent-harness'"
  exit 1
fi

# ---- 3. feature_list.json 完整性 ----
echo ""
echo "=== 3. Feature List 完整性 ==="
TOTAL=$(python3 -c "import json; print(len(json.load(open('feature_list.json')).get('features',[])))" 2>/dev/null || echo "ERR")
PASSED=$(python3 -c "import json; print(sum(1 for f in json.load(open('feature_list.json')).get('features',[]) if f.get('passes')))" 2>/dev/null || echo "ERR")
BLOCKED=$(python3 -c "import json; print(sum(1 for f in json.load(open('feature_list.json')).get('features',[]) if f.get('blocked') or str(f.get('notes','')).startswith('⚠️ 待用户裁决')))" 2>/dev/null || echo "ERR")
if [ "$TOTAL" = "ERR" ] || [ "$PASSED" = "ERR" ] || [ "$BLOCKED" = "ERR" ]; then
  fail "feature_list.json 解析失败,检查 JSON 语法"
  exit 1
fi
# TOTAL=0 必须硬失败:0 个 feature 的 harness 毫无意义,且会让下面的百分比除零。
# (2026-10-18 前这里是 `$(( PASSED * 100 / TOTAL ))`:features 为空时 bash 除零报错打到 stderr,
#  但脚本**继续往下走并打印「全绿」退出 0** —— 假绿,已修。)
if [ "$TOTAL" -eq 0 ]; then
  fail "feature_list.json 的 features 是空的(/init 没写 feature,或被人清空)—— 先补 feature 再开工"
  exit 1
fi
pass "feature_list.json 可解析"
echo "  进度:$PASSED / $TOTAL ($(( PASSED * 100 / TOTAL ))%)"
if [ "$BLOCKED" -gt 0 ]; then
  warn "有 $BLOCKED 个 feature 处于 blocked / 待用户裁决 —— 本 session 汇报时必须重提(SKILL.md §4/§6.8)"
fi

# ---- 4. 核心依赖(项目特定,按需改)----
echo ""
echo "=== 4. 核心依赖 ==="
# 例:python3
if command -v python3 &>/dev/null; then
  PYVER=$(python3 --version | awk '{print $2}')
  pass "python3: $PYVER"
else
  fail "python3 不可用"
fi

# 例:docker
if command -v docker &>/dev/null; then
  pass "docker: $(docker --version 2>/dev/null | awk '{print $3}' | tr -d ',')"
else
  warn "docker 不可用(如果项目不需要可忽略)"
fi

# ---- 5. 自定义自检钩子(项目特定)----
echo ""
echo "=== 5. 项目特定自检 ==="
# 留这个 hook 给项目自己加,例:
#   [ -f "tests/smoke.sh" ] && bash tests/smoke.sh
#   [ -d "node_modules" ] || npm install
if [ -e frontend/node_modules ]; then pass "frontend/node_modules 就绪"; else fail "frontend/node_modules 缺失"; fi
if (cd frontend && npx vue-tsc --noEmit -p tsconfig.app.json); then pass "vue-tsc 0 error"; else fail "vue-tsc 报错"; fi

# ---- 总结 ----
echo ""
echo "=========================================="
if [ $FAILED -eq 0 ]; then
  echo -e "${GREEN}✓ init.sh 全绿,可以开工${NC}"
  exit 0
else
  echo -e "${RED}✗ init.sh 失败,请先修上面红色项${NC}"
  exit 1
fi
