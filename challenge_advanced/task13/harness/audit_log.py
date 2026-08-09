"""Журнал аудита JSONL, один файл на день, файл gateway-YYYYMMDD.jsonl.

Пишет ровно то, что ему передали - не решает, что можно логировать, а что нет. Эта
проверка (никаких секретов, полного текста ответа, заголовка Authorization) лежит на
вызывающей стороне в gateway_server.py.
"""

import glob
import json
import os
import threading
import time
from typing import Any, Dict, List

FILE_PREFIX = "gateway-"
FILE_SUFFIX = ".jsonl"
FILE_DATE_FORMAT = "%Y%m%d"

# Значения verdict и source ниже - те же строковые константы, что gateway_server.py пишет
# в запись журнала (spec13.GATEWAY_VERDICT_* и spec13.SOURCE_*). Дублируются как литералы,
# а не импортом spec13, чтобы этот модуль остался про формат JSONL, а не про домен шлюза -
# как и raw-tail/stats выше, которые тоже не знают семантику verdict, кроме этих двух строк.
VERDICT_BLOCKED_INPUT = "blocked_input"
VERDICT_BLOCKED_OUTPUT = "blocked_output"
VERDICT_MASKED = "masked"
DEFAULT_SOURCE = "chat"


class AuditLog:
    def __init__(self, directory: str) -> None:
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, record: Dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False)
        with self._lock:
            with open(self._today_path(), "a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def tail(self, limit: int) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        return self._read_all()[-limit:]

    def stats(self) -> Dict[str, Any]:
        records = self._read_all()
        by_verdict: Dict[str, int] = {}
        by_source: Dict[str, Dict[str, int]] = {}
        masked_total = 0
        tokens_in_total = 0
        tokens_out_total = 0
        cost_total = 0.0
        latency_total = 0
        for record in records:
            verdict = record.get("verdict") or "unknown"
            by_verdict[verdict] = by_verdict.get(verdict, 0) + 1
            masked_total += int(record.get("masked_count") or 0)
            tokens_in_total += int(record.get("tokens_in") or 0)
            tokens_out_total += int(record.get("tokens_out") or 0)
            cost_total += float(record.get("cost_usd") or 0.0)
            latency_total += int(record.get("latency_ms") or 0)

            source = record.get("source") or DEFAULT_SOURCE
            source_bucket = by_source.setdefault(source, {"requests": 0, "blocked": 0, "masked": 0})
            source_bucket["requests"] += 1
            if verdict in (VERDICT_BLOCKED_INPUT, VERDICT_BLOCKED_OUTPUT):
                source_bucket["blocked"] += 1
            elif verdict == VERDICT_MASKED:
                source_bucket["masked"] += 1
        count = len(records)
        return {
            "requests_total": count,
            "by_verdict": by_verdict,
            "by_source": by_source,
            "masked_count_total": masked_total,
            "tokens_in_total": tokens_in_total,
            "tokens_out_total": tokens_out_total,
            "cost_usd_total": round(cost_total, 6),
            "avg_latency_ms": int(round(latency_total / count)) if count else 0,
        }

    def _today_path(self) -> str:
        return self._path_for(time.strftime(FILE_DATE_FORMAT))

    def _path_for(self, day: str) -> str:
        return os.path.join(self.directory, FILE_PREFIX + day + FILE_SUFFIX)

    def _all_paths(self) -> List[str]:
        pattern = os.path.join(self.directory, FILE_PREFIX + "*" + FILE_SUFFIX)
        return sorted(glob.glob(pattern))

    def _read_all(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for path in self._all_paths():
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            records.append(json.loads(line))
                        except ValueError:
                            continue
            except OSError:
                continue
        return records
