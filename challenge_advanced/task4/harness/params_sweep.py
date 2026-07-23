"""Подбор temperature / top_p на маленькой, но конвенционно плотной задаче.

Каждая связка гоняется тремя сидами: смотрим не только качество, но и разброс -
для кода стабильность ответа важна не меньше, чем его правильность.

Запуск: python3 params_sweep.py
"""

import hashlib
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codegen_lib
import ollama_lib as ollama

TASK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.dirname(TASK_ROOT))
RULES_FILE = os.path.join(PROJECT_ROOT, ".continue", "rules", "01-kotlin-conventions.md")

MODELS = ["qwen3-coder:30b", "qwen2.5-coder:14b"]
CONFIGS = [
    {"temperature": 0.0, "top_p": 1.0},
    {"temperature": 0.1, "top_p": 0.9},
    {"temperature": 0.4, "top_p": 0.95},
    {"temperature": 0.8, "top_p": 0.95},
]
SEEDS = [1, 2, 3]

PROMPT = """Сгенерируй три файла экрана профиля пользователя фичи `profile` (пакет com.jarvis.chat.feature.profile).

1. `presentation/model/ProfileState.kt` - внутренний стейт: имя, email, флаг загрузки, флаг ошибки, список последних действий.
2. `presentation/model/ProfileUiModel.kt` - UI-модель: заголовок, подпись, признак видимости ошибки, счётчик действий, кнопка обновления активна.
3. `presentation/mapper/ProfileUiMapper.kt` - маппер State -> UiModel по конвенциям проекта.

Формат: только блоки кода, первая строка каждого блока - `// path: <путь>`. Без пояснений."""


def main():
    with open(RULES_FILE, encoding="utf-8") as file:
        rules = file.read()

    results = []
    for model in MODELS:
        print(f"\n=== {model} ===", flush=True)
        ollama.unload(model)
        ollama.generate(model, "ok", system=rules, options={"num_predict": 8, "num_ctx": 8192})
        for config in CONFIGS:
            violations = []
            required = []
            digests = set()
            speeds = []
            for seed in SEEDS:
                options = dict(config)
                options.update({"top_k": 40, "seed": seed, "num_ctx": 8192, "num_predict": 2000})
                response = ollama.generate(model, PROMPT, system=rules, options=options)
                answer = response.get("response", "")
                files = codegen_lib.parse_files(answer)
                report = codegen_lib.grade(files)
                violations.append(report["violations_total"])
                required.append(report["required_hit"])
                digests.add(hashlib.sha256("".join(sorted(files.values())).encode("utf-8")).hexdigest())
                speeds.append(ollama.metrics(response)["eval_tps"])
            row = {
                "model": model,
                "temperature": config["temperature"],
                "top_p": config["top_p"],
                "violations_mean": round(statistics.mean(violations), 2),
                "violations_max": max(violations),
                "required_mean": round(statistics.mean(required), 2),
                "distinct_outputs": len(digests),
                "eval_tps_mean": round(statistics.mean(speeds), 1),
            }
            results.append(row)
            print(f"  t={config['temperature']:<4} p={config['top_p']:<5} нарушений {row['violations_mean']:<5} "
                  f"обяз. {row['required_mean']:<5} разных ответов {row['distinct_outputs']}/3", flush=True)
        ollama.unload(model)

    with open(os.path.join(TASK_ROOT, "results", "params.json"), "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    print("\ndone -> results/params.json")


if __name__ == "__main__":
    main()
