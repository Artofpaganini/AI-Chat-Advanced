"""Разбор ответа модели на файлы и проверка кода на конвенции проекта.

Проверки объективные и скриптуемые - никаких «на глаз».
"""

import os
import re

FILE_BLOCK = re.compile(r"```(?:kotlin|kt)?\s*\n(.*?)```", re.DOTALL)
PATH_COMMENT = re.compile(r"^\s*(?://|/\*)\s*(?:path|file)\s*:\s*(\S+)", re.IGNORECASE)
PACKAGE_LINE = re.compile(r"^\s*package\s+([\w.]+)", re.MULTILINE)
# без отступа в начале строки - иначе вложенные члены класса считались бы за отдельные сущности
TOP_LEVEL_NAME = re.compile(
    r"^(?:internal\s+|public\s+|private\s+)?"
    r"(?:sealed\s+|abstract\s+|open\s+|data\s+|enum\s+|value\s+)*"
    r"(?:class|interface|object|fun|val)\s+(\w+)",
    re.MULTILINE,
)

# сущность = класс/интерфейс/объект/функция верхнего уровня. Константы не в счёт.
ENTITY_NAME = re.compile(
    r"^(?:internal\s+|public\s+|private\s+)?"
    r"(?:sealed\s+|abstract\s+|open\s+|data\s+|enum\s+|value\s+)*"
    r"(?:class|interface|object|fun)\s+(\w+)",
    re.MULTILINE,
)

VIOLATIONS = [
    ("dto", re.compile(r"\bDto\b|\bDTO\b")),
    ("ui_state_class", re.compile(r"(?:class|interface)\s+\w*UiState\b")),
    ("state_value_assign", re.compile(r"_state\.value\s*=|stateFlow\.value\s*=")),
    ("not_null_assert", re.compile(r"(?<![!=<>])!!")),
    ("any_type", re.compile(r":\s*Any\b|<Any>")),
    ("implicit_it", re.compile(r"\{\s*(?:[^{}\n]*\W)?\bit\b")),
    ("comment", re.compile(r"^\s*(?://(?!\s*path:)|/\*\*)", re.MULTILINE)),
    ("bare_request_response", re.compile(r"(?:class|interface)\s+\w+(?:Request|Response)\b(?!Model)")),
    ("hardcoded_key", re.compile(r"\"sk-[A-Za-z0-9]")),
]

REQUIRED = [
    ("udf_generic_order", re.compile(r"UdfBaseViewModel<\s*\w*Action\s*,\s*\w*UiModel\s*,\s*\w*State\s*,\s*\w*Event\s*>")),
    ("update_state", re.compile(r"updateState\s*\{")),
    ("ui_mapper_class", re.compile(r"class\s+\w*UiMapper\s*:\s*UiMapper<")),
    ("extension_mapper", re.compile(r"fun\s+\w*ResponseModel\.to\w*Model\s*\(")),
    ("sealed_action", re.compile(r"sealed\s+interface\s+\w*Action")),
    ("koin_module", re.compile(r"\bmodule\s*\{")),
]

EXPECTED_DIRECTORIES = [
    "data/model", "data/mapper", "data/datasource", "data/repository",
    "domain/model", "domain/repository", "domain/usecase",
    "presentation/model", "presentation/mapper", "presentation", "di",
]


def parse_files(answer, package_root="com.jarvis.chat.feature"):
    """Достаём из ответа пары (путь, содержимое). Путь берём из комментария, иначе выводим из package."""
    files = {}
    for block in FILE_BLOCK.findall(answer):
        body = block.strip("\n")
        lines = body.split("\n")
        path = None
        matched = PATH_COMMENT.match(lines[0])
        if matched:
            path = matched.group(1)
            body = "\n".join(lines[1:]).strip("\n")
        if path is None:
            package_match = PACKAGE_LINE.search(body)
            name_match = TOP_LEVEL_NAME.search(body)
            if not package_match or not name_match:
                continue
            package = package_match.group(1)
            if not package.startswith(package_root):
                continue
            feature = package.split(".")[4] if len(package.split(".")) > 4 else "unknown"
            tail = package.replace(f"{package_root}.{feature}", "").strip(".").replace(".", "/")
            path = f"feature/{feature}/src/commonMain/kotlin/{package.replace('.', '/')}/{name_match.group(1)}.kt"
        files[path.strip()] = body + "\n"

    # модель может отдать файлы без ```-фенсов, одними маркерами `// path:` - разбираем и такое
    leftovers = FILE_BLOCK.sub("", answer)
    markers = list(re.finditer(r"^\s*//\s*(?:path|file)\s*:\s*(\S+)\s*$", leftovers, re.MULTILINE))
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(leftovers)
        body = leftovers[marker.end():end].strip("\n")
        if PACKAGE_LINE.search(body):
            files.setdefault(marker.group(1).strip(), body + "\n")
    return files


def grade(files):
    joined = "\n".join(files.values())
    violations = {}
    for name, pattern in VIOLATIONS:
        found = pattern.findall(joined)
        if found:
            violations[name] = len(found)
    required = {name: bool(pattern.search(joined)) for name, pattern in REQUIRED}
    directories = {directory: any(f"/{directory}/" in path for path in files) for directory in EXPECTED_DIRECTORIES}
    one_entity_per_file = all(len(ENTITY_NAME.findall(body)) <= 2 for body in files.values())
    return {
        "files": len(files),
        "lines": sum(body.count("\n") for body in files.values()),
        "violations": violations,
        "violations_total": sum(violations.values()),
        "required": required,
        "required_hit": sum(1 for value in required.values() if value),
        "directories": directories,
        "directories_hit": sum(1 for value in directories.values() if value),
        "one_entity_per_file": one_entity_per_file,
    }


def write_files(files, root):
    for path, body in files.items():
        safe = path.lstrip("/")
        target = os.path.join(root, safe)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as file:
            file.write(body)
