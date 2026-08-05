"""Кодек наборов кейсов: построчный base64, чтобы сканер секретов GitHub не спотыкался о
синтетические ключи в data/*.jsonl.b64, а детекторы получали на вход ту же строку, что и раньше.

Кодирование - не защита. Ключи в наборах поддельные с самого начала (см. README раздел про
секреты). Это способ не спорить со сканером секретов на формате, а не скрыть что-то настоящее.

Формат: одна строка исходного .jsonl -> одна строка base64 в .jsonl.b64, порядок и количество
строк не меняются, пустые строки исходника пропускаются - так же, как их пропускал read_jsonl
до кодирования.

CLI:
  python3 harness/case_codec.py encode data/cases.jsonl data/cases.jsonl.b64
  python3 harness/case_codec.py decode data/cases.jsonl.b64
"""

import base64
import sys
from typing import List

ENCODED_SUFFIX = ".b64"


def encode_line(raw_line: str) -> str:
    return base64.b64encode(raw_line.encode("utf-8")).decode("ascii")


def decode_line(encoded_line: str) -> str:
    return base64.b64decode(encoded_line.encode("ascii")).decode("utf-8")


def encode_file(src_path: str, dst_path: str) -> int:
    count = 0
    with open(src_path, "r", encoding="utf-8") as src, open(dst_path, "w", encoding="utf-8") as dst:
        for line in src:
            stripped = line.strip()
            if not stripped:
                continue
            dst.write(encode_line(stripped) + "\n")
            count += 1
    return count


def read_case_lines(path: str) -> List[str]:
    is_encoded = path.endswith(ENCODED_SUFFIX)
    lines: List[str] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            lines.append(decode_line(stripped) if is_encoded else stripped)
    return lines


def _main() -> int:
    if len(sys.argv) < 3:
        sys.stderr.write("usage: case_codec.py encode <src> <dst> | decode <path>\n")
        return 2
    command, path = sys.argv[1], sys.argv[2]
    if command == "encode":
        if len(sys.argv) < 4:
            sys.stderr.write("encode требует путь назначения\n")
            return 2
        out_path = sys.argv[3]
        count = encode_file(path, out_path)
        sys.stdout.write("закодировано строк: %d -> %s\n" % (count, out_path))
        return 0
    if command == "decode":
        for decoded_line in read_case_lines(path):
            sys.stdout.write(decoded_line + "\n")
        return 0
    sys.stderr.write("неизвестная команда: %s\n" % command)
    return 2


if __name__ == "__main__":
    sys.exit(_main())
