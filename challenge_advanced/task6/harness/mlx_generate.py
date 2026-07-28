# -*- coding: utf-8 -*-
"""Прогон примеров ALVA через локальную MLX-модель (mlx-lm 0.31.3).

Берёт первые N примеров из artifacts/eval.jsonl, подаёт в модель только system и user
(эталонный assistant в промпт не идёт) и складывает ответы в raw/mlx_responses_<tag>.jsonl.
Формат строки повторяет baseline_run.py, чтобы сравнение шло по одним и тем же полям.

Без --adapter-path грузится чистая база, с ним - та же база плюс LoRA-адаптер.
Тег по умолчанию: base без адаптера и tuned с адаптером.

Генерация детерминированная: sampler из mlx_lm.sample_utils.make_sampler(temp=0.0),
при нулевой температуре это argmax, то есть greedy. Промпт собирается через
tokenizer.apply_chat_template(messages, add_generation_prompt=True).

Флаг --thinking управляет режимом размышлений (по умолчанию off): off даёт
enable_thinking=False, on даёт True, auto не передаёт параметр вовсе и оставляет
поведение токенизатора. У thinking-моделей вроде Qwen3 mlx-lm по умолчанию включает
размышления, и в ответ приезжает блок <think>...</think>.

ВНИМАНИЕ: замеры base и tuned обязаны сниматься с ОДИНАКОВЫМ значением --thinking.
Иначе сравнение нечестное: у одной модели в ответе будут рассуждения, у другой нет.

Режим --dry-run модель не грузит и в сеть не ходит.

Запуск: /private/tmp/claude-503/-Users-Victor/73faef96-e5bc-4be5-9599-8edbcd893e7e/scratchpad/mlxenv/bin/python harness/mlx_generate.py --model mlx-community/Qwen3-1.7B-4bit --dry-run
        /private/tmp/claude-503/-Users-Victor/73faef96-e5bc-4be5-9599-8edbcd893e7e/scratchpad/mlxenv/bin/python harness/mlx_generate.py --model mlx-community/Qwen3-1.7B-4bit --n 20
        /private/tmp/claude-503/-Users-Victor/73faef96-e5bc-4be5-9599-8edbcd893e7e/scratchpad/mlxenv/bin/python harness/mlx_generate.py --model mlx-community/Qwen3-1.7B-4bit --adapter-path adapters --n 20
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HARNESS_DIR)
ARTIFACTS_DIR = os.path.join(TASK_DIR, "artifacts")
RAW_DIR = os.path.join(TASK_DIR, "raw")

if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

try:
    from spec import SYSTEM_PROMPT as SPEC_SYSTEM_PROMPT
except ImportError:
    SPEC_SYSTEM_PROMPT = None

EVAL_FILE_NAME = "eval.jsonl"
OUTPUT_TEMPLATE = "mlx_responses_%s.jsonl"

PROVIDER_NAME = "mlx"
TAG_BASE = "base"
TAG_TUNED = "tuned"

DEFAULT_EXAMPLES = 20
DEFAULT_MAX_TOKENS = 900
TEMPERATURE = 0.0

THINKING_OFF = "off"
THINKING_ON = "on"
THINKING_AUTO = "auto"
THINKING_CHOICES = (THINKING_OFF, THINKING_ON, THINKING_AUTO)
THINKING_FLAGS = {THINKING_OFF: False, THINKING_ON: True}

ADAPTER_CONFIG_FILE = "adapter_config.json"
ADAPTER_WEIGHTS_FILE = "adapters.safetensors"

MILLISECONDS_IN_SECOND = 1000.0
PREVIEW_CHARS = 48
STATUS_ERROR_CHARS = 80

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2


class EvalDatasetError(Exception):
    """Файл eval.jsonl не соответствует контракту: битый JSON или нет нужных ролей."""


class ModelLoadError(Exception):
    """Модель или адаптер не удалось загрузить."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Прогон eval.jsonl через локальную MLX-модель с LoRA-адаптером или без него.",
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--adapter-path", dest="adapter_path", default=None)
    parser.add_argument("--n", type=int, default=DEFAULT_EXAMPLES)
    parser.add_argument("--eval", dest="eval_path", default=None)
    parser.add_argument("--out", dest="out_path", default=None)
    parser.add_argument("--max-tokens", dest="max_tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--thinking", choices=list(THINKING_CHOICES), default=THINKING_OFF)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    return parser


def describe_thinking(thinking_mode: str) -> str:
    if thinking_mode == THINKING_AUTO:
        return "auto (параметр не передаётся, как решит токенизатор)"
    return "%s (enable_thinking=%s)" % (thinking_mode, THINKING_FLAGS[thinking_mode])


def resolve_tag(raw_value: Optional[str], adapter_path: Optional[str]) -> str:
    if raw_value:
        return raw_value
    return TAG_TUNED if adapter_path else TAG_BASE


def resolve_eval_path(raw_value: Optional[str]) -> str:
    if raw_value:
        return os.path.abspath(raw_value)
    return os.path.join(ARTIFACTS_DIR, EVAL_FILE_NAME)


def resolve_out_path(raw_value: Optional[str], tag: str) -> str:
    if raw_value:
        return os.path.abspath(raw_value)
    return os.path.join(RAW_DIR, OUTPUT_TEMPLATE % tag)


def resolve_adapter_path(raw_value: Optional[str]) -> Optional[str]:
    if not raw_value:
        return None
    return os.path.abspath(raw_value)


def extract_role(messages: List[Dict[str, Any]], role: str) -> Optional[str]:
    for message in messages:
        if isinstance(message, dict) and message.get("role") == role:
            content = message.get("content")
            if isinstance(content, str):
                return content
    return None


def load_eval_examples(eval_path: str, limit: int) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    with open(eval_path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except ValueError as parse_error:
                raise EvalDatasetError(
                    "Строка %d в %s не парсится как JSON: %s"
                    % (line_number, eval_path, parse_error)
                )
            messages = record.get("messages")
            if not isinstance(messages, list) or not messages:
                raise EvalDatasetError(
                    "Строка %d в %s без ключа messages" % (line_number, eval_path)
                )
            user_text = extract_role(messages, "user")
            if user_text is None:
                raise EvalDatasetError(
                    "Строка %d в %s без роли user" % (line_number, eval_path)
                )
            system_text = extract_role(messages, "system")
            if system_text is None:
                system_text = SPEC_SYSTEM_PROMPT
            examples.append(
                {
                    "index": len(examples),
                    "system": system_text,
                    "user": user_text,
                    "reference": extract_role(messages, "assistant") or "",
                }
            )
            if len(examples) >= limit:
                break
    return examples


def build_messages(example: Dict[str, Any]) -> List[Dict[str, str]]:
    messages = []
    if example["system"]:
        messages.append({"role": "system", "content": example["system"]})
    messages.append({"role": "user", "content": example["user"]})
    return messages


def check_adapter_dir(adapter_path: Optional[str]) -> Optional[str]:
    if adapter_path is None:
        return None
    if not os.path.isdir(adapter_path):
        return "каталог адаптера не найден: %s" % adapter_path
    config_file = os.path.join(adapter_path, ADAPTER_CONFIG_FILE)
    if not os.path.isfile(config_file):
        return "в каталоге адаптера нет файла %s: %s" % (ADAPTER_CONFIG_FILE, adapter_path)
    weights_file = os.path.join(adapter_path, ADAPTER_WEIGHTS_FILE)
    if not os.path.isfile(weights_file):
        return "в каталоге адаптера нет файла %s: %s" % (ADAPTER_WEIGHTS_FILE, adapter_path)
    return None


def load_model_and_tokenizer(model_name: str, adapter_path: Optional[str]) -> Tuple[Any, Any, Any]:
    try:
        from mlx_lm import load, stream_generate
        from mlx_lm.sample_utils import make_sampler
    except ImportError as import_error:
        raise ModelLoadError(
            "не импортируется mlx_lm, запускайте скрипт python-ом из venv с mlx-lm: %s"
            % import_error
        )
    try:
        model, tokenizer = load(model_name, adapter_path=adapter_path)
    except Exception as load_error:
        raise ModelLoadError(
            "не удалось загрузить модель %s%s: %s"
            % (
                model_name,
                "" if adapter_path is None else " с адаптером %s" % adapter_path,
                load_error,
            )
        )
    return model, tokenizer, (stream_generate, make_sampler)


def build_prompt(
    tokenizer: Any, example: Dict[str, Any], thinking_mode: str
) -> Tuple[Any, Optional[bool]]:
    messages = build_messages(example)
    if thinking_mode == THINKING_AUTO:
        return tokenizer.apply_chat_template(messages, add_generation_prompt=True), None
    try:
        prompt = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            enable_thinking=THINKING_FLAGS[thinking_mode],
        )
        return prompt, True
    except Exception:
        return tokenizer.apply_chat_template(messages, add_generation_prompt=True), False


def generate_one(
    stream_generate: Any,
    model: Any,
    tokenizer: Any,
    prompt: Any,
    max_tokens: int,
    sampler: Any,
) -> Tuple[str, Optional[int], Optional[int]]:
    text_parts: List[str] = []
    last_response = None
    for response in stream_generate(
        model,
        tokenizer,
        prompt,
        max_tokens=max_tokens,
        sampler=sampler,
    ):
        text_parts.append(response.text)
        last_response = response
    if last_response is None:
        return "".join(text_parts), None, None
    prompt_tokens = getattr(last_response, "prompt_tokens", None)
    completion_tokens = getattr(last_response, "generation_tokens", None)
    return "".join(text_parts), prompt_tokens, completion_tokens


def print_dry_run(
    model_name: str,
    adapter_path: Optional[str],
    adapter_problem: Optional[str],
    tag: str,
    thinking_mode: str,
    eval_path: str,
    out_path: str,
    max_tokens: int,
    requested: int,
    examples: List[Dict[str, Any]],
    eval_problem: Optional[str],
) -> None:
    sys.stdout.write("DRY-RUN: модель не загружается, генерации нет.\n")
    sys.stdout.write("Провайдер:        %s\n" % PROVIDER_NAME)
    sys.stdout.write("Модель:           %s\n" % model_name)
    sys.stdout.write(
        "Адаптер:          %s\n" % (adapter_path if adapter_path else "нет, чистая база")
    )
    if adapter_problem is not None:
        sys.stdout.write("ВНИМАНИЕ:         %s\n" % adapter_problem)
    sys.stdout.write("Тег:              %s\n" % tag)
    sys.stdout.write("Размышления:      %s\n" % describe_thinking(thinking_mode))
    sys.stdout.write("Сэмплер:          make_sampler(temp=%s), это greedy argmax\n" % TEMPERATURE)
    sys.stdout.write("max_tokens:       %d\n" % max_tokens)
    sys.stdout.write("Шаблон промпта:   apply_chat_template(add_generation_prompt=True)\n")
    sys.stdout.write("Файл eval:        %s\n" % eval_path)
    sys.stdout.write("Файл вывода:      %s\n" % out_path)
    if eval_problem is not None:
        sys.stdout.write("\nПримеры прочитать не удалось: %s\n" % eval_problem)
        sys.stdout.write("Примеров было бы прогнано: 0.\n")
        return
    sys.stdout.write("Запрошено примеров: %d, доступно: %d\n" % (requested, len(examples)))
    sys.stdout.write("\nПлан прогона:\n")
    sys.stdout.write("%-5s %-12s %-12s %s\n" % ("idx", "user_chars", "ref_chars", "начало реплики"))
    for example in examples:
        preview = example["user"].replace("\n", " ")[:PREVIEW_CHARS]
        sys.stdout.write(
            "%-5d %-12d %-12d %s\n"
            % (example["index"], len(example["user"]), len(example["reference"]), preview)
        )
    sys.stdout.write("\nВсего примеров: %d.\n" % len(examples))


def run_live(
    model_name: str,
    adapter_path: Optional[str],
    tag: str,
    thinking_mode: str,
    examples: List[Dict[str, Any]],
    out_path: str,
    max_tokens: int,
) -> int:
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    sys.stdout.write("Модель: %s\n" % model_name)
    sys.stdout.write("Адаптер: %s\n" % (adapter_path if adapter_path else "нет, чистая база"))
    sys.stdout.write("Размышления: %s\n" % describe_thinking(thinking_mode))
    sys.stdout.write("Тег: %s, примеров: %d, max_tokens: %d\n" % (tag, len(examples), max_tokens))
    sys.stdout.write("Вывод: %s\n" % out_path)
    sys.stdout.write("Загружаю модель, это может занять время...\n\n")
    sys.stdout.flush()

    try:
        model, tokenizer, helpers = load_model_and_tokenizer(model_name, adapter_path)
    except ModelLoadError as model_error:
        sys.stderr.write("%s\n" % model_error)
        return EXIT_CONFIG_ERROR
    stream_generate, make_sampler = helpers
    sampler = make_sampler(temp=TEMPERATURE)

    succeeded = 0
    failed = 0
    total_ms = 0
    total_completion_tokens = 0
    tokens_known = True
    thinking_rejected = 0

    sys.stdout.write("%-5s %-8s %-12s %s\n" % ("idx", "chars", "latency_ms", "статус"))
    sys.stdout.flush()

    with open(out_path, "w", encoding="utf-8") as handle:
        for example in examples:
            response_text = ""
            prompt_tokens: Optional[int] = None
            completion_tokens: Optional[int] = None
            thinking_applied: Optional[bool] = None
            error_text: Optional[str] = None
            started = time.time()
            try:
                prompt, thinking_applied = build_prompt(tokenizer, example, thinking_mode)
                response_text, prompt_tokens, completion_tokens = generate_one(
                    stream_generate, model, tokenizer, prompt, max_tokens, sampler
                )
            except Exception as generate_error:
                error_text = "%s: %s" % (type(generate_error).__name__, generate_error)
            latency_ms = int((time.time() - started) * MILLISECONDS_IN_SECOND)
            total_ms += latency_ms
            if thinking_applied is False:
                thinking_rejected += 1
            if error_text is None:
                succeeded += 1
                status_label = "ok"
                if isinstance(completion_tokens, int):
                    total_completion_tokens += completion_tokens
                else:
                    tokens_known = False
            else:
                failed += 1
                status_label = "ошибка: %s" % error_text[:STATUS_ERROR_CHARS]
            record = {
                "index": example["index"],
                "provider": PROVIDER_NAME,
                "model": model_name,
                "tag": tag,
                "adapter": adapter_path,
                "thinking": thinking_mode,
                "thinking_applied": thinking_applied,
                "user": example["user"],
                "reference": example["reference"],
                "response": response_text,
                "latency_ms": latency_ms,
                "tokens": {"prompt": prompt_tokens, "completion": completion_tokens},
                "error": error_text,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            sys.stdout.write(
                "%-5d %-8d %-12d %s\n"
                % (example["index"], len(response_text), latency_ms, status_label)
            )
            sys.stdout.flush()

    total_seconds = total_ms / MILLISECONDS_IN_SECOND
    sys.stdout.write(
        "\nУспешно: %d, с ошибкой: %d, всего: %d\n" % (succeeded, failed, len(examples))
    )
    sys.stdout.write("Суммарное время: %.1f с\n" % total_seconds)
    if thinking_rejected:
        sys.stdout.write(
            "Токенизатор не принял enable_thinking в %d примерах, промпт собран без него "
            "(в строках thinking_applied=false)\n" % thinking_rejected
        )
    if tokens_known and succeeded > 0 and total_seconds > 0:
        sys.stdout.write(
            "Средняя скорость: %.1f токенов в секунду (%d токенов ответа)\n"
            % (total_completion_tokens / total_seconds, total_completion_tokens)
        )
    else:
        sys.stdout.write("Средняя скорость: нет данных по токенам\n")
    sys.stdout.write("Ответы записаны в %s\n" % out_path)
    return EXIT_OK if failed == 0 else EXIT_DATA_ERROR


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    adapter_path = resolve_adapter_path(args.adapter_path)
    tag = resolve_tag(args.tag, adapter_path)
    eval_path = resolve_eval_path(args.eval_path)
    out_path = resolve_out_path(args.out_path, tag)

    if args.n <= 0:
        sys.stderr.write("Значение --n должно быть больше нуля.\n")
        return EXIT_CONFIG_ERROR
    if args.max_tokens <= 0:
        sys.stderr.write("Значение --max-tokens должно быть больше нуля.\n")
        return EXIT_CONFIG_ERROR

    adapter_problem = check_adapter_dir(adapter_path)

    examples: List[Dict[str, Any]] = []
    eval_problem: Optional[str] = None
    if not os.path.isfile(eval_path):
        eval_problem = "файл %s не найден (его собирает build_dataset.py)" % eval_path
    else:
        try:
            examples = load_eval_examples(eval_path, args.n)
        except EvalDatasetError as dataset_error:
            eval_problem = str(dataset_error)
        except OSError as os_error:
            eval_problem = "не читается %s: %s" % (eval_path, os_error)
        if eval_problem is None and not examples:
            eval_problem = "файл %s пустой" % eval_path

    if args.dry_run:
        print_dry_run(
            args.model,
            adapter_path,
            adapter_problem,
            tag,
            args.thinking,
            eval_path,
            out_path,
            args.max_tokens,
            args.n,
            examples,
            eval_problem,
        )
        return EXIT_OK

    if adapter_problem is not None:
        sys.stderr.write(
            "Не могу взять LoRA-адаптер: %s\n"
            "Укажите каталог, который сделал mlx_lm.lora (в нём лежат %s и %s), "
            "или запустите без --adapter-path.\n"
            % (adapter_problem, ADAPTER_CONFIG_FILE, ADAPTER_WEIGHTS_FILE)
        )
        return EXIT_CONFIG_ERROR

    if eval_problem is not None:
        sys.stderr.write("Не могу прочитать примеры: %s\n" % eval_problem)
        return EXIT_DATA_ERROR

    if len(examples) < args.n:
        sys.stdout.write(
            "В eval нашлось только %d примеров из запрошенных %d.\n" % (len(examples), args.n)
        )

    return run_live(
        args.model, adapter_path, tag, args.thinking, examples, out_path, args.max_tokens
    )


if __name__ == "__main__":
    sys.exit(main())
