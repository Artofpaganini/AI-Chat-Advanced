"""Замер автокомплита: base-модели в режиме fill-in-the-middle на реальных дырках проекта.

Две схемы промпта:
  bare - только текущий файл (префикс + суффикс)
  repo - плюс два соседних файла через <|file_sep|>, как это делает Continue

Метрики: задержка полного цикла и точное совпадение с тем, что реально стоит в проекте.
Запуск: python3 bench_fim.py
"""

import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ollama_lib as ollama

TASK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.dirname(TASK_ROOT))
RAW_DIR = os.path.join(TASK_ROOT, "raw")
RESULTS_DIR = os.path.join(TASK_ROOT, "results")

FIM_MODELS = ["qwen2.5-coder:1.5b-base", "qwen2.5-coder:3b-base"]
REPEATS = 3

CHAT = "feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat"
AI = "feature/ai/src/commonMain/kotlin/com/jarvis/chat/feature/ai"
CORE = "core/viewmodel/src/commonMain/kotlin/com/jarvis/chat/core/viewmodel"

# (файл, первая строка дырки, последняя строка дырки, соседние файлы для repo-схемы)
HOLES = [
    (f"{CHAT}/presentation/mapper/ChatUiMapper.kt", 25, 25,
     [f"{CHAT}/presentation/model/ChatState.kt", f"{CHAT}/presentation/model/ChatUiModel.kt"]),
    (f"{AI}/data/mapper/ChatCompletionResponseMapper.kt", 10, 10,
     [f"{AI}/data/model/ChatCompletionResponseModel.kt", f"{AI}/domain/model/ChatMessageModel.kt"]),
    (f"{CHAT}/data/mapper/HistoryMessageDataMapper.kt", 26, 26,
     [f"{CHAT}/data/model/ChatHistoryDataModel.kt", f"{CHAT}/domain/model/HistoryMessageModel.kt"]),
    (f"{CHAT}/data/mapper/HistoryMessageDataMapper.kt", 16, 17,
     [f"{CHAT}/data/model/ChatMessageDataModel.kt", f"{AI}/domain/model/MessageAuthor.kt"]),
    (f"{CORE}/UdfBaseViewModel.kt", 45, 45,
     [f"{CORE}/UiMapper.kt", f"{CHAT}/presentation/ChatViewModel.kt"]),
    (f"{CHAT}/presentation/mapper/ChatUiMapper.kt", 19, 19,
     [f"{CHAT}/presentation/model/ChatMessageUiModel.kt", f"{CHAT}/domain/model/HistoryMessageModel.kt"]),
]

OPTIONS = {
    "temperature": 0.05,
    "top_p": 0.9,
    "num_predict": 96,
    "num_ctx": 8192,
    "seed": 42,
    "stop": ["<|endoftext|>", "<|fim_pad|>", "<|repo_name|>", "<|file_sep|>", "\n\n\n"],
}


def read_lines(relative_path):
    with open(os.path.join(PROJECT_ROOT, relative_path), encoding="utf-8") as file:
        return file.readlines()


def build_hole(hole):
    path, first, last, neighbours = hole
    lines = read_lines(path)
    prefix = "".join(lines[: first - 1])
    truth = "".join(lines[first - 1: last])
    suffix = "".join(lines[last:])
    return path, prefix, truth, suffix, neighbours


def fim_prompt(prefix, suffix, neighbours=None):
    head = ""
    if neighbours:
        head = "<|repo_name|>AI-Chat-Advanced\n"
        for neighbour in neighbours:
            content = "".join(read_lines(neighbour))
            head += f"<|file_sep|>{neighbour}\n{content}"
        head += "<|file_sep|>"
    return f"{head}<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>"


def normalize(text):
    return " ".join(text.split())


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    results = []

    for model in FIM_MODELS:
        print(f"\n=== {model} ===", flush=True)
        ollama.unload(model)
        ollama.generate(model, "<|fim_prefix|>val a = <|fim_suffix|>\n<|fim_middle|>", options=OPTIONS)

        for scheme in ("bare", "repo"):
            latencies = []
            hits = 0
            for index, hole in enumerate(HOLES):
                path, prefix, truth, suffix, neighbours = build_hole(hole)
                prompt = fim_prompt(prefix, suffix, neighbours if scheme == "repo" else None)
                best = None
                for repeat in range(REPEATS):
                    response = ollama.generate(model, prompt, options=OPTIONS, timeout=600)
                    numbers = ollama.metrics(response)
                    latencies.append(numbers["total_s"] * 1000)
                    if best is None:
                        best = response
                completion = best.get("response", "")
                matched = normalize(completion).startswith(normalize(truth)) or normalize(truth) in normalize(completion)
                hits += 1 if matched else 0
                results.append({
                    "model": model,
                    "scheme": scheme,
                    "hole": f"{os.path.basename(path)}:{hole[1]}",
                    "matched": matched,
                    "truth": truth.strip(),
                    "completion": completion.strip()[:400],
                    "latency_ms": round(ollama.metrics(best)["total_s"] * 1000),
                    "prompt_tokens": ollama.metrics(best)["prompt_tokens"],
                })
                print(f"  {scheme:5} {os.path.basename(path):32}:{hole[1]:3} "
                      f"{'HIT ' if matched else 'MISS'} {round(ollama.metrics(best)['total_s'] * 1000):6} ms", flush=True)
            print(f"  -> {scheme}: {hits}/{len(HOLES)} попаданий, медиана {round(statistics.median(latencies))} мс", flush=True)
        ollama.unload(model)

    ollama.save_raw(os.path.join(RESULTS_DIR, "fim.json"), results)
    print("\ndone -> results/fim.json")


if __name__ == "__main__":
    main()
