"""Прогон задачи A с продолжением.

Локальные модели обрывают длинную выдачу на первом же блоке кода: `done_reason: stop` после одного
файла. Поэтому протокол такой: один и тот же промпт, а дальше - «продолжай, не хватает вот этих файлов».
Число ходов до полного набора и есть ответ на вопрос «справилась ли с первого раза».
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codegen_lib
import ollama_lib as ollama

EXPECTED_FILES = [
    "TranslateRequestModel", "TranslateMessageRequestModel", "TranslateResponseModel",
    "TranslateChoiceResponseModel", "TranslateMessageResponseModel",
    "TranslateResponseMapper",
    "TranslateRemoteDataSource", "TranslateRemoteDataSourceImpl",
    "TranslateRepositoryImpl",
    "TranslationModel", "TargetLanguage",
    "TranslateRepository",
    "TranslateTextUseCase",
    "TranslateAction", "TranslateState", "TranslateEvent", "TranslateUiModel",
    "TranslateUiMapper",
    "TranslateViewModel", "TranslateScreen",
    "TranslateModule",
]


def missing_files(files):
    present = set()
    for path in files:
        name = os.path.basename(path).replace(".kt", "")
        present.add(name)
    return [name for name in EXPECTED_FILES if name not in present]


def run(model, rules, prompt, options, max_turns=8, log=print):
    messages = [
        {"role": "system", "content": rules},
        {"role": "user", "content": prompt},
    ]
    files = {}
    turns = 0
    tokens = 0
    started = time.time()
    transcript = []

    while turns < max_turns:
        turns += 1
        response = ollama.chat(model, messages, options=options)
        content = response.get("message", {}).get("content", "")
        tokens += response.get("eval_count", 0)
        transcript.append(content)
        before = len(files)
        files.update(codegen_lib.parse_files(content))
        gained = len(files) - before
        missing = missing_files(files)
        log(f"    ход {turns}: +{gained} файлов, всего {len(files)}, не хватает {len(missing)} "
            f"({response.get('eval_count', 0)} токенов)")
        if not missing:
            break
        if gained == 0 and turns > 1:
            break
        messages.append({"role": "assistant", "content": content})
        messages.append({
            "role": "user",
            "content": "Продолжай. Не хватает файлов: " + ", ".join(missing) +
                       ". Выдавай тем же форматом: блок кода, первая строка `// path: <путь>`. Без пояснений.",
        })

    return files, {
        "turns": turns,
        "eval_tokens": tokens,
        "seconds": round(time.time() - started),
        "missing": missing_files(files),
        "transcript": transcript,
    }
