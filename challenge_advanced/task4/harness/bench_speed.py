"""Замер скорости чат-моделей: генерация, TTFT, обработка длинного промпта, память.

Запуск: python3 bench_speed.py
Результат: raw/speed_<model>_<case>.json + results/speed.json
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ollama_lib as ollama

TASK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.dirname(TASK_ROOT))
RAW_DIR = os.path.join(TASK_ROOT, "raw")
RESULTS_DIR = os.path.join(TASK_ROOT, "results")
RULES_FILE = os.path.join(PROJECT_ROOT, ".continue", "rules", "01-kotlin-conventions.md")

CHAT_MODELS = sys.argv[1:] or ["qwen3-coder:30b", "devstral:24b", "qwen2.5-coder:14b"]
CONTEXT_TARGETS = [2000, 4000, 8000, 16000, 32000]
CHARS_PER_TOKEN = 3.4

BASE_OPTIONS = {"temperature": 0.1, "top_p": 0.9, "top_k": 40, "seed": 42}

SHORT_PROMPT = (
    "Напиши класс TranslateUiMapper: маппер TranslateState -> TranslateUiModel по конвенциям проекта. "
    "Затем напиши TranslateState и TranslateUiModel. Затем коротко объясни, почему маппер вынесен в отдельный класс."
)


def read_rules():
    with open(RULES_FILE, encoding="utf-8") as file:
        return file.read()


def collect_code(target_tokens):
    """Набираем реальный код проекта до нужного объёма - синтетический текст мерил бы не то."""
    budget = int(target_tokens * CHARS_PER_TOKEN)
    chunks = []
    size = 0
    for directory in ("feature", "core", "composeApp/src"):
        for root, _, files in os.walk(os.path.join(PROJECT_ROOT, directory)):
            if "build" in root.split(os.sep):
                continue
            for name in sorted(files):
                if not name.endswith(".kt"):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as file:
                    text = file.read()
                chunks.append(f"// file: {os.path.relpath(path, PROJECT_ROOT)}\n{text}\n")
                size += len(text)
                if size >= budget:
                    return "".join(chunks)[:budget]
    return "".join(chunks)[:budget]


def run_case(model, case, prompt, system, options, num_ctx):
    merged = dict(BASE_OPTIONS)
    merged.update(options)
    merged["num_ctx"] = num_ctx
    response = ollama.generate(model, prompt, system=system, options=merged)
    ollama.save_raw(os.path.join(RAW_DIR, f"speed_{model.replace(':', '-')}_{case}.json"), response)
    result = ollama.metrics(response)
    result["case"] = case
    result["model"] = model
    print(f"  {case:22} eval {result['eval_tps']:7.2f} tok/s | prompt {result['prompt_tokens']:6} @ "
          f"{result['prompt_eval_tps']:7.1f} tok/s | ttft {result['ttft_ms']:7} ms", flush=True)
    return result


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rules = read_rules()
    results = []

    for model in CHAT_MODELS:
        print(f"\n=== {model} ===", flush=True)
        ollama.unload(model)

        # холодный старт: сюда попадает реальное время загрузки весов с диска
        cold = run_case(model, "cold_start", SHORT_PROMPT, rules, {"num_predict": 64}, 8192)
        results.append(cold)

        # прогрев, в цифры не идёт
        ollama.generate(model, "ok", system=rules, options={**BASE_OPTIONS, "num_predict": 8, "num_ctx": 8192})

        results.append(run_case(model, "generation", SHORT_PROMPT, rules, {"num_predict": 800}, 8192))

        for target in CONTEXT_TARGETS:
            code = collect_code(target)
            prompt = f"Вот часть кодовой базы:\n\n{code}\n\nОтветь одним словом: сколько ViewModel ты видишь?"
            num_ctx = max(8192, int(target * 1.4))
            results.append(run_case(model, f"ctx_{target}", prompt, rules, {"num_predict": 16}, num_ctx))

        loaded = ollama.loaded_models()
        for entry in loaded:
            if entry["name"] == model:
                results.append({
                    "model": model,
                    "case": "memory",
                    "size_bytes": entry.get("size", 0),
                    "size_vram_bytes": entry.get("size_vram", 0),
                })
                print(f"  memory                 resident {entry.get('size', 0) / 1e9:.1f} GB", flush=True)
        ollama.unload(model)

    name = "speed.json" if len(CHAT_MODELS) > 1 else f"speed_{CHAT_MODELS[0].replace(':', '-')}.json"
    with open(os.path.join(RESULTS_DIR, name), "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    print("\ndone -> results/speed.json")


if __name__ == "__main__":
    main()
