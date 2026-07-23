"""Проверка параметров на большой задаче. Маленькая задача температуру не различает - большая различает.

Тот же промпт задачи A и тот же протокол продолжения, четыре связки temperature/top_p, один сид.

Запуск: python3 params_taskA_ab.py [model]
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

CONFIGS = [
    {"temperature": 0.0, "top_p": 1.0},
    {"temperature": 0.1, "top_p": 0.9},
    {"temperature": 0.4, "top_p": 0.95},
    {"temperature": 0.8, "top_p": 0.95},
]


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen3-coder:30b"
    with open(RULES_FILE, encoding="utf-8") as file:
        rules = file.read()
    with open(PROMPT_FILE, encoding="utf-8") as file:
        prompt = file.read()

    ollama.unload(model)
    ollama.generate(model, "ok", system=rules, options={"num_predict": 8, "num_ctx": 16384})

    results = []
    for config in CONFIGS:
        options = dict(config)
        options.update({"top_k": 40, "seed": 42, "num_ctx": 16384, "num_predict": 8192})
        files, stats = taskA_runner.run(model, rules, prompt, options, max_turns=25, log=lambda line: None)
        report = codegen_lib.grade(files)
        row = {
            "model": model,
            "temperature": config["temperature"],
            "top_p": config["top_p"],
            "files": report["files"],
            "turns": stats["turns"],
            "seconds": stats["seconds"],
            "violations_total": report["violations_total"],
            "violations": report["violations"],
            "required_hit": report["required_hit"],
            "directories_hit": report["directories_hit"],
            "missing": len(stats["missing"]),
        }
        results.append(row)
        print(f"  t={config['temperature']:<4} p={config['top_p']:<5} файлов {report['files']:3} "
              f"ходов {stats['turns']:3} нарушений {report['violations_total']:3} "
              f"обяз. {report['required_hit']}/6 каталогов {report['directories_hit']}/11 "
              f"за {stats['seconds']} с {report['violations']}", flush=True)

    with open(os.path.join(TASK_ROOT, "results", "params_taskA.json"), "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    ollama.unload(model)
    print("done -> results/params_taskA.json")


if __name__ == "__main__":
    main()
