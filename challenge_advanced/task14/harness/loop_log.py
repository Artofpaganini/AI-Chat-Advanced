"""Журнал прогонов цикла, JSONL, файл raw/loop/loop-YYYYMMDD.jsonl (LOOP_CONTRACT.md раздел 11).

Одна строка на прогон. Не хранит содержимое сгенерированного кода целиком - только имена
файлов, текст находок безопасности и уже отформатированные ошибки линта/сборки. Сырые ответы
модели, если их вообще нужно сохранить, уходят отдельными файлами в raw/loop/, а сюда - только
имя этого файла.
"""

import glob
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

FILE_PREFIX = "loop-"
FILE_SUFFIX = ".jsonl"
FILE_DATE_FORMAT = "%Y%m%d"


class LoopLog:
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


def build_record(
    run_id: str,
    task: str,
    iterations_used: int,
    stopped_at: Optional[str],
    stages: List[Dict[str, Any]],
    security_findings: List[Dict[str, Any]],
    gateway_calls: List[Dict[str, Any]],
    lint_errors: List[Dict[str, Any]],
    build_errors: List[Dict[str, Any]],
    commit: Optional[str],
    final_files: List[str],
    final_code_artifact: Optional[str],
    security_review_first_try: int,
    security_review_rescued: int,
    security_review_failed: int,
    security_malformed_blocks: List[Dict[str, Any]],
    security_attempt_discrepancies: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "run_id": run_id,
        "task": task,
        "iterations_used": iterations_used,
        "stopped_at": stopped_at,
        "stages": stages,
        "security_findings": security_findings,
        "security_review_first_try": security_review_first_try,
        "security_review_rescued": security_review_rescued,
        "security_review_failed": security_review_failed,
        "security_malformed_blocks": security_malformed_blocks,
        "security_attempt_discrepancies": security_attempt_discrepancies,
        "gateway_calls": gateway_calls,
        "lint_errors": lint_errors,
        "build_errors": build_errors,
        "commit": commit,
        "final_files": final_files,
        "final_code_artifact": final_code_artifact,
    }
