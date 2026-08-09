#!/usr/bin/env bash
# Поднимает пайплайн целиком: шлюз (task13) + сервер цикла (task14).
# Проверка безопасности живёт внутри сервера цикла, отдельно не запускается.
#
# Ключ DeepSeek берётся из переменной окружения DEEPSEEK_API_KEY или из
# local.properties в корне репозитория. В код и логи он не попадает.
#
# Запуск:   bash challenge_advanced/task15/start_pipeline.sh
# Остановка: bash challenge_advanced/task15/start_pipeline.sh stop

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATEWAY="$REPO_ROOT/challenge_advanced/task13/harness/gateway_server.py"
LOOP="$REPO_ROOT/challenge_advanced/task14/harness/loop_server.py"
LOG_DIR="$REPO_ROOT/challenge_advanced/task15/run"
mkdir -p "$LOG_DIR"

if [ "${1:-start}" = "stop" ]; then
  pkill -f "gateway_server.py" 2>/dev/null && echo "шлюз остановлен"
  pkill -f "loop_server.py" 2>/dev/null && echo "сервер цикла остановлен"
  exit 0
fi

# частота поднята под серию вызовов цикла, дефолт был бы 20
python3 "$GATEWAY" --port 8091 --rate-limit 60 --stream-guard buffer \
  > "$LOG_DIR/gateway.log" 2>&1 &
python3 "$LOOP" --port 8092 --gateway http://127.0.0.1:8091 \
  > "$LOG_DIR/loop.log" 2>&1 &

sleep 3

echo "=== здоровье ==="
curl -s --max-time 3 http://127.0.0.1:8091/gateway/health && echo
curl -s --max-time 3 http://127.0.0.1:8092/loop/health && echo
echo
echo "шлюз       http://127.0.0.1:8091   логи $LOG_DIR/gateway.log"
echo "цикл       http://127.0.0.1:8092   логи $LOG_DIR/loop.log"
echo "остановить bash challenge_advanced/task15/start_pipeline.sh stop"
