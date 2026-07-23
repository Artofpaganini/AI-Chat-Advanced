#!/bin/bash
# Очередь замеров. Строго последовательно - две модели в памяти одновременно исказят цифры.
set -u
HARNESS="$(cd "$(dirname "$0")" && pwd)"
TASK_ROOT="$(dirname "$HARNESS")"
LOG_DIR="$TASK_ROOT/raw"

# ждём, пока закончится уже запущенный замер скорости
while [ ! -f "$TASK_ROOT/results/speed.json" ]; do sleep 20; done

cd "$HARNESS" || exit 1
for step in bench_fim params_sweep run_taskA; do
  echo "=== $step $(date +%H:%M:%S) ==="
  python3 "$step.py" > "$LOG_DIR/$step.log" 2>&1
  echo "=== $step done rc=$? $(date +%H:%M:%S) ==="
done
