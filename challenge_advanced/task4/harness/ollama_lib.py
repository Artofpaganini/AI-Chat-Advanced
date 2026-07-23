"""Тонкая обвязка над HTTP API ollama для воспроизводимых замеров.

Все метрики берутся из полей ответа самого ollama (load_duration, prompt_eval_*, eval_*),
а не измеряются секундомером снаружи - так в числа не попадает наш собственный оверхед.
"""

import json
import time
import urllib.request

BASE_URL = "http://localhost:11434"
NANOS_IN_SECOND = 1_000_000_000
NANOS_IN_MILLI = 1_000_000


def _post(path, payload, timeout=3600):
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def unload(model):
    """Выгрузить модель из памяти, чтобы соседний замер не мерил чужой резидент."""
    try:
        _post("/api/generate", {"model": model, "keep_alive": 0, "prompt": ""}, timeout=120)
    except Exception:
        pass
    time.sleep(2)


def loaded_models():
    with urllib.request.urlopen(f"{BASE_URL}/api/ps", timeout=30) as response:
        return json.loads(response.read().decode("utf-8")).get("models", [])


def generate(model, prompt, system=None, options=None, timeout=3600):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": options or {},
        "keep_alive": "5m",
    }
    if system:
        payload["system"] = system
    return _post("/api/generate", payload, timeout=timeout)


def chat(model, messages, tools=None, options=None, timeout=3600):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options or {},
        "keep_alive": "5m",
    }
    if tools:
        payload["tools"] = tools
    return _post("/api/chat", payload, timeout=timeout)


def metrics(response):
    """Достаём из ответа только то, что нужно для таблиц."""
    prompt_tokens = response.get("prompt_eval_count", 0)
    prompt_nanos = response.get("prompt_eval_duration", 0)
    eval_tokens = response.get("eval_count", 0)
    eval_nanos = response.get("eval_duration", 0)
    load_nanos = response.get("load_duration", 0)
    total_nanos = response.get("total_duration", 0)
    return {
        "prompt_tokens": prompt_tokens,
        "prompt_eval_tps": round(prompt_tokens / (prompt_nanos / NANOS_IN_SECOND), 1) if prompt_nanos else 0.0,
        "eval_tokens": eval_tokens,
        "eval_tps": round(eval_tokens / (eval_nanos / NANOS_IN_SECOND), 2) if eval_nanos else 0.0,
        "load_ms": round(load_nanos / NANOS_IN_MILLI),
        "ttft_ms": round((load_nanos + prompt_nanos) / NANOS_IN_MILLI),
        "total_s": round(total_nanos / NANOS_IN_SECOND, 1),
    }


def save_raw(path, payload):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
