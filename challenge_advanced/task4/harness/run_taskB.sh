#!/bin/bash
# Задача B на трёх моделях, каждая в своей песочнице. Последовательно - иначе gradle и инференс дерутся.
set -u
HARNESS="$(cd "$(dirname "$0")" && pwd)"
TASK_ROOT="$(dirname "$HARNESS")"
SANDBOX_ROOT="${1:?укажи каталог с песочницами}"

declare -a PAIRS=(
  "qwen3-coder:30b agent-qwen3"
  "devstral:24b agent-devstral"
  "qwen2.5-coder:14b agent-qwen25"
)

cd "$HARNESS" || exit 1
for pair in "${PAIRS[@]}"; do
  model="${pair%% *}"
  sandbox="$SANDBOX_ROOT/${pair##* }"
  echo "=== $model в $sandbox $(date +%H:%M:%S) ==="
  git -C "$sandbox" checkout -- . 2>/dev/null
  git -C "$sandbox" clean -fdq 2>/dev/null
  python3 agent_loop.py "$model" "$sandbox" > "$TASK_ROOT/raw/taskB_${model//:/-}.log" 2>&1
  echo "=== $model done rc=$? $(date +%H:%M:%S) ==="
done
echo "=== задача B закончена ==="
