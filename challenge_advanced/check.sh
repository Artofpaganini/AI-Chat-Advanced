#!/bin/bash
# Проверка задач 7 и 8. Без аргументов - только чтение готовых цифр, бесплатно и мгновенно.
# С аргументом live - живые прогоны, около 2 центов.

set -u
cd "$(dirname "$0")"

echo "=============================================================="
echo " ЗАДАЧА 7 - контроль уверенности"
echo "=============================================================="
(cd task7 && python3 harness/report.py 2>&1 | sed -n '1,30p')

echo
echo "=============================================================="
echo " ЗАДАЧА 8 - роутинг между моделями"
echo "=============================================================="
(cd task8 && python3 harness/router_report.py raw 2>&1 | sed -n '1,20p')

if [ "${1:-}" != "live" ]; then
  echo
  echo "Это готовые цифры. Чтобы прогнать вживую: ./check.sh live"
  exit 0
fi

echo
echo "=============================================================="
echo " ЖИВОЙ ПРОГОН"
echo "=============================================================="

echo
echo "-- механизмы контроля, 5 сценариев --"
(cd task7 && python3 harness/smoke.py 2>&1 | tail -5)

echo
echo "-- задача 7 на 50 кейсах --"
(cd task7 && python3 harness/run_eval.py --mode both --workers 6 >/dev/null 2>&1 && python3 harness/report.py 2>&1 | sed -n '5,20p')

if curl -s -o /dev/null --max-time 3 http://127.0.0.1:8081/v1/models; then
  echo
  echo "-- роутинг на 50 кейсах --"
  (cd task8 && for s in only_cheap only_strong route_all; do
     python3 harness/run_router.py --strategy $s --workers 3 >/dev/null 2>&1
   done && python3 harness/router_report.py raw 2>&1 | sed -n '5,16p')
else
  echo
  echo "-- роутинг пропущен: локальная модель не поднята --"
  echo "   запустить: ~/mlxenv/bin/mlx_lm.server --model mlx-community/Qwen3-1.7B-4bit --port 8081"
fi

echo
echo "Готово."
