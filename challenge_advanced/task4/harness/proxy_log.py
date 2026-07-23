"""Прокси между Continue и ollama. Пишет в лог то, что плагин реально отправляет.

Нужен как доказательство: какие роли работают, какая модель, какие параметры,
сколько токенов промпта уходит в автокомплит и в чат. Плагин смотрит на 11435, ollama на 11434.

Запуск: python3 proxy_log.py
Лог: raw/ide_traffic.jsonl
"""

import json
import os
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TASK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(TASK_ROOT, "raw", "ide_traffic.jsonl")
UPSTREAM = "http://localhost:11434"
PORT = 11435


def describe(path, body):
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"path": path, "raw_bytes": len(body)}
    prompt = payload.get("prompt", "")
    messages = payload.get("messages", [])
    record = {
        "path": path,
        "model": payload.get("model"),
        "options": payload.get("options"),
        "stream": payload.get("stream"),
        "prompt_chars": len(prompt) if isinstance(prompt, str) else 0,
        "messages": len(messages),
        "message_chars": sum(len(str(message.get("content", ""))) for message in messages),
        "fim": "<|fim_prefix|>" in prompt if isinstance(prompt, str) else False,
        "tools": len(payload.get("tools", []) or []),
        "prompt_head": prompt[:180] if isinstance(prompt, str) else "",
    }
    if messages:
        record["system_chars"] = sum(
            len(str(message.get("content", ""))) for message in messages if message.get("role") == "system")
        record["last_user"] = str(messages[-1].get("content", ""))[:180]
    return record


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _relay(self, body=None):
        request = urllib.request.Request(
            f"{UPSTREAM}{self.path}",
            data=body,
            headers={key: value for key, value in self.headers.items() if key.lower() != "host"},
            method=self.command,
        )
        try:
            with urllib.request.urlopen(request, timeout=1800) as response:
                payload = response.read()
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() in ("content-length", "transfer-encoding", "connection"):
                        continue
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        except Exception as error:
            self.send_response(502)
            self.send_header("Content-Length", "0")
            self.end_headers()
            with open(LOG_FILE, "a", encoding="utf-8") as file:
                file.write(json.dumps({"time": time.strftime("%H:%M:%S"), "error": str(error)[:200]}) + "\n")

    def do_GET(self):
        self._relay()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        record = describe(self.path, body)
        record["time"] = time.strftime("%H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._relay(body)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    print(f"proxy on :{PORT} -> {UPSTREAM}, log {LOG_FILE}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
