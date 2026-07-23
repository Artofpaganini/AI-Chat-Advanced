"""Сколько итераций нужно локальной модели, чтобы довести свой код до сборки.

Берём код модели из задачи A, компилируем, ошибки компилятора отдаём обратно модели,
она правит файлы, снова компилируем. До зелёного или до лимита раундов.

Запуск: python3 repair_taskA.py <sandbox> [model ...]
"""

import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codegen_lib
import compile_taskA
import ollama_lib as ollama

TASK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.dirname(TASK_ROOT))
RULES_FILE = os.path.join(PROJECT_ROOT, ".continue", "rules", "01-kotlin-conventions.md")
GENERATED_ROOT = os.path.join(TASK_ROOT, "artifacts", "generated")

MODEL_BY_SLUG = {
    "qwen3-coder-30b": "qwen3-coder:30b",
    "devstral-24b": "devstral:24b",
    "qwen2.5-coder-14b": "qwen2.5-coder:14b",
    "deepseek-coder-v2-16b": "deepseek-coder-v2:16b",
}
MAX_ROUNDS = 3
OPTIONS = {"temperature": 0.1, "top_p": 0.9, "top_k": 40, "seed": 42, "num_ctx": 32768, "num_predict": 8192}


def load_files(root):
    files = {}
    for dirpath, _, names in os.walk(root):
        for name in names:
            if name.endswith(".kt"):
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as file:
                    files[os.path.relpath(path, root)] = file.read()
    return files


def compile_files(sandbox, files, task):
    target = os.path.join(sandbox, "feature", "translate")
    shutil.rmtree(target, ignore_errors=True)
    for path, body in files.items():
        full = os.path.join(target, path.replace("feature/translate/", "", 1)
                            if path.startswith("feature/translate/") else path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as file:
            file.write(body)
    with open(os.path.join(target, "build.gradle.kts"), "w", encoding="utf-8") as file:
        file.write(compile_taskA.MODULE_BUILD_FILE)
    settings = os.path.join(sandbox, "settings.gradle.kts")
    with open(settings, encoding="utf-8") as file:
        content = file.read()
    if ":feature:translate" not in content:
        with open(settings, "w", encoding="utf-8") as file:
            file.write(content + '\ninclude(":feature:translate")\n')
    result = compile_taskA.gradle(sandbox, [f":feature:translate:{task}", "--offline"])
    output = result.stdout + result.stderr
    errors = [re.sub(r"file://\S*?/feature/translate/", "", line) for line in
              re.findall(r"^e: .*$", output, re.MULTILINE)]
    return result.returncode == 0, errors


def main():
    sandbox = os.path.abspath(sys.argv[1])
    slugs = sys.argv[2:] or list(MODEL_BY_SLUG)
    task = compile_taskA.detect_build_task(sandbox)
    with open(RULES_FILE, encoding="utf-8") as file:
        rules = file.read()

    results = []
    for slug in slugs:
        model = MODEL_BY_SLUG[slug]
        print(f"\n=== {model} ===", flush=True)
        ollama.unload(model)
        files = load_files(os.path.join(GENERATED_ROOT, slug))
        history = []
        green = False
        rounds = 0

        for round_index in range(MAX_ROUNDS + 1):
            compile_taskA.reset(sandbox)
            green, errors = compile_files(sandbox, files, task)
            history.append({"round": round_index, "green": green, "errors": len(errors)})
            print(f"  раунд {round_index}: {'ЗЕЛЁНО' if green else 'ошибок ' + str(len(errors))}", flush=True)
            if green or round_index == MAX_ROUNDS:
                rounds = round_index
                break

            broken = sorted({error.split(":")[0] for error in errors})
            listing = "\n\n".join(
                f"// path: {path}\n{body}" for path, body in files.items()
                if any(name in path for name in broken))
            prompt = (
                "Твой код не компилируется. Вот ошибки компилятора Kotlin:\n\n"
                + "\n".join(errors[:40])
                + "\n\nВот текущее содержимое файлов с ошибками:\n\n```kotlin\n" + listing[:20000] + "\n```\n\n"
                + "Выдай исправленные версии ТОЛЬКО этих файлов. Каждый файл отдельным блоком, "
                  "первая строка блока `// path: <тот же путь>`. Полное содержимое файла, без сокращений, без пояснений."
            )
            response = ollama.chat(model, [
                {"role": "system", "content": rules},
                {"role": "user", "content": prompt},
            ], options=OPTIONS)
            answer = response.get("message", {}).get("content", "")
            with open(os.path.join(TASK_ROOT, "raw", f"repair_{slug}_r{round_index}.md"), "w", encoding="utf-8") as dump:
                dump.write(answer)
            fixed = codegen_lib.parse_files(answer)
            print(f"    прислала исправлений: {len(fixed)} файлов", flush=True)
            if not fixed:
                rounds = round_index + 1
                break
            for path, body in fixed.items():
                key = next((existing for existing in files if os.path.basename(existing) == os.path.basename(path)), path)
                files[key] = body

        report = codegen_lib.grade(files)
        results.append({
            "model": model,
            "green": green,
            "rounds_used": rounds,
            "history": history,
            "violations_total": report["violations_total"],
            "violations": report["violations"],
        })
        ollama.unload(model)

    compile_taskA.reset(sandbox)
    with open(os.path.join(TASK_ROOT, "results", "repair.json"), "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    print("\ndone -> results/repair.json")


if __name__ == "__main__":
    main()
