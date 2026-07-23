"""Задача B - агентный режим, как в Дне 2. Модель сама ходит по репозиторию инструментами.

Песочница - клон проекта, у каждой модели свой чистый git-стейт.
Инструменты: list_dir, search, read_file, write_file, build.
Если модель не умеет tool-calling через API, включается текстовый протокол с теми же инструментами.

Запуск: python3 agent_loop.py <model> <sandbox>
"""

import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ollama_lib as ollama

TASK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.dirname(TASK_ROOT))
RULES_FILE = os.path.join(PROJECT_ROOT, ".continue", "rules", "01-kotlin-conventions.md")
PROMPT_FILE = os.path.join(TASK_ROOT, "harness", "prompts", "taskB_agent.md")

JAVA_HOME = "/Users/Victor/Library/Java/JavaVirtualMachines/corretto-21.0.9/Contents/Home"
BUILD_TASK = os.environ.get("BENCH_BUILD_TASK", ":feature:chat:compileCommonMainKotlinMetadata")
MAX_STEPS = 50
MAX_SECONDS = 2400
MAX_NUDGES = 3
MAX_FILE_CHARS = 12000

OPTIONS = {"temperature": 0.1, "top_p": 0.9, "top_k": 40, "seed": 42, "num_ctx": 32768, "num_predict": 4096}

TOOLS = [
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "Список файлов и папок по относительному пути в проекте.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "search",
        "description": "Поиск подстроки по исходникам проекта. Возвращает совпадения вида путь:строка.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Прочитать файл целиком по относительному пути.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Записать файл целиком по относительному пути. Существующий будет перезаписан.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "build",
        "description": "Собрать модуль чата. Возвращает успех и хвост лога компилятора.",
        "parameters": {"type": "object", "properties": {}}}},
]

TEXT_PROTOCOL = """
Ты работаешь инструментами. На каждом шаге выдавай РОВНО один вызов в блоке:

```json
{"tool": "list_dir", "args": {"path": "feature/chat"}}
```

Доступные инструменты: list_dir(path), search(query), read_file(path), write_file(path, content), build().
Когда работа закончена, вместо блока напиши строку DONE и список изменённых файлов.
"""


class Sandbox:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.calls = []
        self.build_runs = 0
        self.build_success = False

    def _resolve(self, path):
        target = os.path.abspath(os.path.join(self.root, path.lstrip("/")))
        if not target.startswith(self.root):
            raise ValueError("путь за пределами песочницы")
        return target

    def list_dir(self, path="."):
        target = self._resolve(path)
        if not os.path.isdir(target):
            return f"нет такой папки: {path}"
        entries = sorted(os.listdir(target))
        entries = [entry for entry in entries if entry not in (".git", "build", ".gradle", ".kotlin", ".idea")]
        return "\n".join(entries) or "(пусто)"

    def search(self, query):
        result = subprocess.run(
            ["grep", "-rn", "--include=*.kt", "--include=*.kts", query, "feature", "core", "composeApp"],
            cwd=self.root, capture_output=True, text=True, timeout=60)
        lines = result.stdout.splitlines()[:40]
        return "\n".join(lines) or "ничего не найдено"

    def read_file(self, path):
        target = self._resolve(path)
        if not os.path.isfile(target):
            return f"нет такого файла: {path}"
        with open(target, encoding="utf-8") as file:
            content = file.read()
        return content[:MAX_FILE_CHARS]

    def write_file(self, path, content):
        target = self._resolve(path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as file:
            file.write(content)
        return f"записано: {path} ({len(content)} символов)"

    def build(self):
        self.build_runs += 1
        environment = dict(os.environ, JAVA_HOME=JAVA_HOME)
        result = subprocess.run(
            ["./gradlew", BUILD_TASK, "--offline", "-q", "--console=plain"],
            cwd=self.root, capture_output=True, text=True, timeout=1800, env=environment)
        success = result.returncode == 0
        self.build_success = success
        tail = (result.stdout + result.stderr).strip().splitlines()
        errors = [line for line in tail if "e: " in line][:20]
        body = "\n".join(errors or tail[-25:])
        return f"{'СБОРКА ЗЕЛЁНАЯ' if success else 'СБОРКА УПАЛА'}\n{body}"

    def dispatch(self, name, arguments):
        started = time.time()
        try:
            handler = getattr(self, name, None)
            if handler is None:
                output = f"нет такого инструмента: {name}"
                ok = False
            else:
                output = handler(**arguments)
                ok = not str(output).startswith(("нет такой", "нет такого", "ничего не найдено", "путь за"))
        except Exception as error:
            output = f"ошибка инструмента: {error}"
            ok = False
        self.calls.append({
            "tool": name, "args": {key: str(value)[:120] for key, value in arguments.items()},
            "ok": ok, "seconds": round(time.time() - started, 1),
        })
        return str(output)


def parse_text_calls(content):
    """Вызовы инструментов, набранные текстом. Форматы: {"tool": ..., "args": ...} и {"name": ..., "arguments": ...}."""
    calls = []
    for block in re.findall(r"```(?:json)?\s*\n(.*?)```", content or "", re.DOTALL):
        try:
            parsed = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        entries = parsed if isinstance(parsed, list) else [parsed]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("tool") or entry.get("name")
            arguments = entry.get("args") or entry.get("arguments") or entry.get("parameters") or {}
            if name and isinstance(arguments, dict):
                calls.append({"function": {"name": name, "arguments": arguments}})
    return calls


def supports_tools(model):
    try:
        ollama.chat(model, [{"role": "user", "content": "ping"}], tools=TOOLS,
                    options={"num_predict": 1, "num_ctx": 2048}, timeout=300)
        return True
    except Exception as error:
        return "does not support tools" not in str(error)


def run(model, sandbox_root):
    with open(RULES_FILE, encoding="utf-8") as file:
        rules = file.read()
    with open(PROMPT_FILE, encoding="utf-8") as file:
        task = file.read()

    sandbox = Sandbox(sandbox_root)
    native_tools = supports_tools(model)
    system = rules if native_tools else rules + "\n" + TEXT_PROTOCOL
    messages = [{"role": "system", "content": system}, {"role": "user", "content": task}]

    started = time.time()
    steps = 0
    tokens = 0
    nudges = 0
    text_calls = 0
    finish = "max_steps"

    while steps < MAX_STEPS and time.time() - started < MAX_SECONDS:
        steps += 1
        response = ollama.chat(model, messages, tools=TOOLS if native_tools else None, options=OPTIONS, timeout=1800)
        message = response.get("message", {})
        tokens += response.get("eval_count", 0)
        calls = message.get("tool_calls") or []
        content = message.get("content", "")

        # модель может выдать вызов текстом вместо канала tool_calls - это тоже засчитываем
        if not calls:
            parsed_calls = parse_text_calls(content)
            if parsed_calls:
                text_calls += len(parsed_calls)
                calls = parsed_calls

        if not calls:
            messages.append({"role": "assistant", "content": content})
            if nudges < MAX_NUDGES:
                nudges += 1
                messages.append({
                    "role": "user",
                    "content": "Ты не вызвал ни одного инструмента. Работа не сделана. "
                               "Вызови инструмент: list_dir, search, read_file, write_file или build. "
                               "Не описывай план словами - выполняй.",
                })
                continue
            finish = "answered"
            break

        messages.append(message if message.get("tool_calls") else {"role": "assistant", "content": content})
        for call in calls:
            function = call.get("function", {})
            name = function.get("name", "")
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            output = sandbox.dispatch(name, arguments)
            print(f"  [{steps:02}] {name}({str(arguments)[:70]}) -> {output.splitlines()[0][:80] if output else ''}",
                  flush=True)
            messages.append({"role": "tool", "content": output[:6000], "name": name})

    diff = subprocess.run(["git", "diff", "--stat"], cwd=sandbox_root, capture_output=True, text=True)
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                               cwd=sandbox_root, capture_output=True, text=True)
    return {
        "model": model,
        "native_tools": native_tools,
        "steps": steps,
        "finish": finish,
        "nudges": nudges,
        "text_calls": text_calls,
        "seconds": round(time.time() - started),
        "eval_tokens": tokens,
        "tool_calls": sandbox.calls,
        "tool_calls_total": len(sandbox.calls),
        "tool_calls_failed": sum(1 for call in sandbox.calls if not call["ok"]),
        "build_runs": sandbox.build_runs,
        "build_success": sandbox.build_success,
        "diff_stat": diff.stdout.strip(),
        "untracked": untracked.stdout.split(),
        "final_answer": messages[-1].get("content", "")[:2000] if messages else "",
    }


if __name__ == "__main__":
    report = run(sys.argv[1], sys.argv[2])
    slug = sys.argv[1].replace(":", "-")
    ollama.save_raw(os.path.join(TASK_ROOT, "raw", f"taskB_{slug}.json"), report)
    print(json.dumps({key: value for key, value in report.items() if key != "tool_calls"},
                     ensure_ascii=False, indent=2))
