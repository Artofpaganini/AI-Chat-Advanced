"""Прогон пула из 10 простых задач на локальной модели.

Харнесс переиспользован от task4: инструменты и цикл живут в task4/harness/agent_loop.py,
здесь только оркестрация пула и сбор метрик.

Модель работает в песочнице-клоне, реальный репозиторий не трогается.
Задача считается сделанной, если модель добилась зелёной компиляции И реально изменила файлы.
Провалившаяся задача откатывается, чтобы мусор не тянулся в следующую.

Запуск: python3 local_pool_run.py <model> <sandbox>
"""

import json
import os
import subprocess
import sys
import time

TASK5_DIR = os.path.dirname(os.path.abspath(__file__))
HARNESS_DIR = os.path.join(os.path.dirname(TASK5_DIR), "task4", "harness")
sys.path.insert(0, HARNESS_DIR)

import agent_loop
import ollama_lib as ollama

RESULTS_PATH = os.path.join(TASK5_DIR, "local_results.json")
PROMPT_PATH = os.path.join(TASK5_DIR, ".local_task_prompt.md")

agent_loop.PROMPT_FILE = PROMPT_PATH
agent_loop.MAX_STEPS = 50
agent_loop.MAX_SECONDS = 2400

COMMON_RULES = """
Проект - чат с AI на Kotlin Multiplatform + Compose Multiplatform.
Модуль чата: feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/

Конвенции, которые нельзя нарушать:
- internal по умолчанию, публичным делать только то, что реально нужно снаружи;
- в лямбдах именованные параметры, неявный it запрещён;
- никаких magic numbers, все размеры и числа - именованными константами;
- никаких !! и Any;
- комментарии и KDoc не писать;
- размеры брать из уже существующего presentation/ui/ChatDimens.kt, новые добавлять туда же.

Порядок работы: сначала прочитай нужные файлы инструментом read_file, потом пиши.
Записывай файл целиком через write_file - он перезаписывает содержимое.
Обязательно вызови build в конце и добейся зелёной сборки.
"""

TASKS = [
    ("Счётчик символов",
     "Под полем ввода сообщения показывай текущее количество введённых символов. "
     "Правь feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/presentation/ui/MessageInputBar.kt"),
    ("Лимит длины сообщения",
     "Введи максимальную длину сообщения именованной константой. Если текст длиннее лимита, "
     "кнопка отправки должна быть неактивна. "
     "Правь feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/presentation/ui/MessageInputBar.kt"),
    ("Крестик очистки поля ввода",
     "Когда в поле ввода есть текст, показывай справа внутри поля иконку-крестик. "
     "Тап по ней очищает поле. Иконку бери из material-icons-extended. "
     "Правь feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/presentation/ui/MessageInputBar.kt"),
    ("Число сообщений в заголовке",
     "В заголовке верхней панели рядом со словом Jarvis показывай количество сообщений в чате. "
     "Заголовок задаётся в feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/presentation/ChatScreen.kt"),
    ("Плейсхолдер во время генерации",
     "Пока идёт генерация ответа, подсказка внутри поля ввода должна меняться на другой текст. "
     "Признак генерации уже есть в UI-модели. "
     "Правь feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/presentation/ui/MessageInputBar.kt"),
    ("Дизейбл экспорта и очистки на пустой истории",
     "Когда в чате нет сообщений, кнопки экспорта и очистки истории в верхней панели должны быть неактивны. "
     "Правь feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/presentation/ui/ChatTopBarActions.kt"),
    ("Кнопка наверх в топбаре",
     "Добавь в верхнюю панель кнопку, которая прокручивает список сообщений к самому первому сообщению. "
     "Правь ChatTopBarActions.kt и ChatScreen.kt в feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/presentation/"),
    ("Ограничить высоту поля ввода",
     "Поле ввода не должно расти бесконечно: ограничь его максимальным числом строк именованной константой. "
     "Правь feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/presentation/ui/MessageInputBar.kt"),
    ("Счётчик избранных у иконки фильтра",
     "Рядом с иконкой фильтра избранного в верхней панели показывай количество избранных сообщений. "
     "Количество уже считается в UI-модели. "
     "Правь feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/presentation/ui/ChatTopBarActions.kt"),
    ("Две новые подсказки в пустом состоянии",
     "Добавь две новые подсказки в список подсказок пустого состояния чата. "
     "Правь feature/chat/src/commonMain/kotlin/com/jarvis/chat/feature/chat/presentation/ui/ChatEmptyState.kt"),
]


def sandbox_reset(sandbox):
    subprocess.run(["git", "checkout", "--", "."], cwd=sandbox, capture_output=True)
    subprocess.run(["git", "clean", "-fd"], cwd=sandbox, capture_output=True)


def sandbox_lock_in(sandbox, index):
    subprocess.run(["git", "add", "-A"], cwd=sandbox, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", f"local task {index}"], cwd=sandbox, capture_output=True)


def changed_files(sandbox):
    tracked = subprocess.run(["git", "diff", "--name-only"], cwd=sandbox, capture_output=True, text=True)
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                               cwd=sandbox, capture_output=True, text=True)
    names = [line for line in (tracked.stdout + untracked.stdout).splitlines() if line.strip()]
    return [name for name in names if name.endswith((".kt", ".kts"))]


def load_previous():
    """Докат: подхватываем уже сделанные задачи, чтобы не переделывать их после обрыва."""
    if not os.path.exists(RESULTS_PATH):
        return [], 0.0
    with open(RESULTS_PATH, encoding="utf-8") as file:
        data = json.load(file)
    return data.get("results", []), data.get("total_minutes", 0.0)


def main(model, sandbox, start_index=1):
    results, spent_minutes = load_previous() if start_index > 1 else ([], 0.0)
    results = [entry for entry in results if entry["index"] < start_index]
    pool_started = time.time()

    for index, (title, body) in enumerate(TASKS, start=1):
        if index < start_index:
            continue
        with open(PROMPT_PATH, "w", encoding="utf-8") as file:
            file.write(f"{COMMON_RULES}\n\nЗАДАЧА {index}: {title}\n\n{body}\n")

        print(f"\n===== ЗАДАЧА {index}/10: {title} =====", flush=True)
        started = time.time()
        try:
            report = agent_loop.run(model, sandbox)
            crashed = None
        except Exception as error:
            report = {}
            crashed = str(error)[:300]

        touched = changed_files(sandbox)
        build_ok = bool(report.get("build_success"))
        done = build_ok and bool(touched) and crashed is None

        entry = {
            "index": index,
            "title": title,
            "done": done,
            "reason": crashed or ("ok" if done else
                                  "сборка красная" if touched else
                                  "файлы не изменены"),
            "steps": report.get("steps", 0),
            "tool_calls": report.get("tool_calls_total", 0),
            "tool_calls_failed": report.get("tool_calls_failed", 0),
            "build_runs": report.get("build_runs", 0),
            "eval_tokens": report.get("eval_tokens", 0),
            "finish": report.get("finish", "crash"),
            "nudges": report.get("nudges", 0),
            "changed_files": touched,
            "minutes": round((time.time() - started) / 60, 1),
        }
        results.append(entry)
        print(json.dumps(entry, ensure_ascii=False), flush=True)

        if done:
            sandbox_lock_in(sandbox, index)
        else:
            sandbox_reset(sandbox)

        with open(RESULTS_PATH, "w", encoding="utf-8") as file:
            json.dump({"model": model, "results": results,
                       "total_minutes": round(spent_minutes + (time.time() - pool_started) / 60, 1)},
                      file, ensure_ascii=False, indent=2)

    solved = sum(1 for entry in results if entry["done"])
    streak = 0
    for entry in results:
        if entry["done"]:
            streak += 1
        else:
            break
    print(f"\n===== ИТОГ: {solved}/10 сделано, подряд без провала {streak}, "
          f"{round(spent_minutes + (time.time() - pool_started) / 60, 1)} минут =====")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
