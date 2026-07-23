"""Задача A - генерация фичи, как в Дне 1. Один и тот же промпт всем моделям.

Протокол: первый ход - весь промпт; дальше «продолжай, не хватает вот этих файлов», пока набор не полон.
Число ходов - это и есть метрика «справилась с первого раза».

Запуск: python3 run_taskA.py
Результат: artifacts/generated/<model>/..., raw/taskA_<model>.md, results/taskA.json
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codegen_lib
import ollama_lib as ollama
import taskA_runner

TASK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.dirname(TASK_ROOT))
RULES_FILE = os.path.join(PROJECT_ROOT, ".continue", "rules", "01-kotlin-conventions.md")
PROMPT_FILE = os.path.join(TASK_ROOT, "harness", "prompts", "taskA_feature.md")

MODELS = sys.argv[1:] or ["qwen3-coder:30b", "devstral:24b", "qwen2.5-coder:14b"]
OPTIONS = {
    "temperature": 0.1,
    "top_p": 0.9,
    "top_k": 40,
    "seed": 42,
    "num_ctx": 16384,
    "num_predict": 8192,
}


def main():
    with open(RULES_FILE, encoding="utf-8") as file:
        rules = file.read()
    with open(PROMPT_FILE, encoding="utf-8") as file:
        prompt = file.read()

    summary = []
    for model in MODELS:
        print(f"\n=== {model} ===", flush=True)
        ollama.unload(model)
        files, stats = taskA_runner.run(model, rules, prompt, OPTIONS, max_turns=25,
                                        log=lambda line: print(line, flush=True))

        slug = model.replace(":", "-")
        with open(os.path.join(TASK_ROOT, "raw", f"taskA_{slug}.md"), "w", encoding="utf-8") as file:
            file.write("\n\n---- ход ----\n\n".join(stats.pop("transcript")))
        target = os.path.join(TASK_ROOT, "artifacts", "generated", slug)
        codegen_lib.write_files(files, target)

        report = codegen_lib.grade(files)
        report.update({"model": model, "run": stats})
        summary.append(report)
        print(f"  итог: файлов {report['files']:3} | строк {report['lines']:5} | ходов {stats['turns']} "
              f"| нарушений {report['violations_total']:3} | обязательных {report['required_hit']}/6 "
              f"| каталогов {report['directories_hit']}/11 | {stats['seconds']} с", flush=True)
        if report["violations"]:
            print(f"  нарушения: {report['violations']}", flush=True)
        if stats["missing"]:
            print(f"  не выдала: {stats['missing']}", flush=True)
        ollama.unload(model)

    name = "taskA.json" if len(MODELS) > 1 else f"taskA_{MODELS[0].replace(':', '-')}.json"
    with open(os.path.join(TASK_ROOT, "results", name), "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
    print("\ndone -> results/taskA.json")


if __name__ == "__main__":
    main()
