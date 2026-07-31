"""Показывает один кейс насквозь: как его решил монолит и как цепочка из трёх этапов.

Читает готовое сырьё, сеть не трогает, денег не тратит.
Запуск: python3 harness/show_case.py borderline_01
"""

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
CASES_PATH = os.path.join(TASK_DIR, "..", "task7", "data", "cases.jsonl")

STAGE_TITLES = {
    "stage1_parse": "ЭТАП 1 - разбор и нормализация входа",
    "stage2_decide": "ЭТАП 2 - решение и классификация",
    "stage3_answer": "ЭТАП 3 - формирование результата",
}


def read_record(path, case_id):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("case_id") == case_id:
                return record
    return None


def read_case(case_id):
    with open(CASES_PATH, encoding="utf-8") as handle:
        for line in handle:
            case = json.loads(line)
            if case["id"] == case_id:
                return case
    return None


def print_case(case):
    if case is None:
        print("Кейс не найден в наборе.")
        return
    print("ВОПРОС РОДИТЕЛЯ")
    print(" ", case["text"])
    print("ГРУППА:", case["group"], "  ПРАВИЛЬНЫЙ МАРШРУТ:", case["expected_route"])
    if case.get("why_hard"):
        print("ЧЕМ СЛОЖЕН:", case["why_hard"])


def print_monolithic(record):
    print()
    print("=" * 78)
    print("ВАРИАНТ A - МОНОЛИТ: один большой запрос, один ответ")
    print("=" * 78)
    if record is None:
        print("Сырья нет, сначала прогони run_stages.py")
        return
    stage = record["stages"][0] if record.get("stages") else {}
    print("вызовов:", record["calls"], " время:", record["total_latency_ms"], "мс",
          " цена:", "%.8f" % record["total_cost_usd"], "USD")
    print("нарушения формата:", stage.get("violations") or "нет")
    print("-" * 78)
    print((stage.get("raw_text") or "").strip()[:900])
    print("-" * 78)
    print("ИТОГ:", record["route"])


def print_multistage(record):
    print()
    print("=" * 78)
    print("ВАРИАНТ B - ЦЕПОЧКА: три коротких запроса подряд")
    print("=" * 78)
    if record is None:
        print("Сырья нет, сначала прогони run_stages.py")
        return
    for stage in record.get("stages", []):
        title = STAGE_TITLES.get(stage["stage"], stage["stage"])
        usage = stage.get("usage") or {}
        print()
        print(title)
        print("  модель:", stage.get("model"), " время:", stage.get("latency_ms"), "мс",
              " цена:", "%.8f" % (stage.get("cost_usd") or 0), "USD")
        print("  токенов на входе:", usage.get("prompt_tokens"),
              " на выходе:", usage.get("completion_tokens"))
        print("  нарушения формата:", stage.get("violations") or "нет")
        print("  вывод модели:")
        for text_line in (stage.get("raw_text") or "").strip().splitlines()[:12]:
            print("   ", text_line[:200])
    print()
    print("-" * 78)
    print("ИТОГ:", record["route"], " вызовов:", record["calls"],
          " время:", record["total_latency_ms"], "мс",
          " цена:", "%.8f" % record["total_cost_usd"], "USD")


def print_verdict(case, monolithic, multistage):
    if case is None or monolithic is None or multistage is None:
        return
    gold = case["expected_route"]
    print()
    print("=" * 78)
    print("СРАВНЕНИЕ")
    print("=" * 78)
    print("правильный маршрут:      ", gold)
    print("монолит ответил:         ", monolithic["route"],
          "верно" if monolithic["route"] == gold else "НЕВЕРНО")
    print("цепочка ответила:        ", multistage["route"],
          "верно" if multistage["route"] == gold else "НЕВЕРНО")
    calls_ratio = multistage["calls"] / max(monolithic["calls"], 1)
    cost_ratio = multistage["total_cost_usd"] / max(monolithic["total_cost_usd"], 1e-12)
    time_ratio = multistage["total_latency_ms"] / max(monolithic["total_latency_ms"], 1)
    print("цепочка дороже в         ", "%.2f" % cost_ratio, "раз")
    print("цепочка медленнее в      ", "%.2f" % time_ratio, "раз")
    print("вызовов больше в         ", "%.0f" % calls_ratio, "раз")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id", nargs="?", default="borderline_01",
                        help="идентификатор кейса, например clean_01 или noisy_09")
    parser.add_argument("--runs", default="raw",
                        help="каталог с сырьём, по умолчанию raw")
    args = parser.parse_args()

    runs_dir = args.runs if os.path.isabs(args.runs) else os.path.join(TASK_DIR, args.runs)
    case = read_case(args.case_id)
    monolithic = read_record(os.path.join(runs_dir, "monolithic_runs.jsonl"), args.case_id)
    multistage = read_record(os.path.join(runs_dir, "multistage_runs.jsonl"), args.case_id)

    print_case(case)
    print_monolithic(monolithic)
    print_multistage(multistage)
    print_verdict(case, monolithic, multistage)


if __name__ == "__main__":
    main()
