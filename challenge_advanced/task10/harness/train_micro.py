"""Обучение micro-model и экспорт весов по контракту WEIGHTS_FORMAT.md.

Что делает по порядку:
  1. читает обучающий корпус в чат-формате и вытаскивает пару текст -> маршрут
  2. проверяет пересечение с оценочным набором, точное и по близости Жаккара
  3. строит словарь, обучает softmax-регрессию, режет словарь по важности и переобучается
  4. подбирает пороги на валидационном срезе, cases.jsonl при этом не трогается
  5. обучает финальные веса на всём корпусе и пишет results/micro_model.json

Запуск: python3 harness/train_micro.py
"""

import argparse
import json
import math
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import micro_model
import spec10

Vector = List[Tuple[int, float]]

VOCABULARY_ENTRY_OVERHEAD = 27
WEIGHT_ENTRY_OVERHEAD = 46
HEADER_BYTES = 900
BUDGET_SAFETY = 0.94


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def route_of_assistant(content: str) -> Optional[str]:
    try:
        parsed = json.loads(content)
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    route = parsed.get("route")
    if route in spec10.LABELS:
        return route
    return None


def load_corpus(path: str) -> List[Tuple[str, str]]:
    samples: List[Tuple[str, str]] = []
    for row in read_jsonl(path):
        messages = row.get("messages")
        if not isinstance(messages, list):
            continue
        text = ""
        route = None
        for message in messages:
            if message.get("role") == "user":
                text = str(message.get("content", ""))
            elif message.get("role") == "assistant":
                route = route_of_assistant(str(message.get("content", "")))
        if text and route:
            samples.append((text, route))
    return samples


def load_cases(path: str) -> List[Dict[str, Any]]:
    return read_jsonl(path)


def word_set(text: str) -> frozenset:
    return frozenset(micro_model.normalize(text).split(micro_model.SPACE))


def jaccard(left: frozenset, right: frozenset) -> float:
    if not left or not right:
        return 0.0
    union = len(left | right)
    if union == 0:
        return 0.0
    return len(left & right) / union


def overlap_report(
    samples: Sequence[Tuple[str, str]], cases: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    """Утечка train -> eval: точные совпадения нормализованного текста и близкие пары."""
    normalized_train = [micro_model.normalize(text) for text, _ in samples]
    train_index: Dict[str, List[int]] = {}
    for position, value in enumerate(normalized_train):
        train_index.setdefault(value, []).append(position)
    train_word_sets = [word_set(text) for text, _ in samples]

    exact: List[Dict[str, Any]] = []
    near: List[Dict[str, Any]] = []
    for case in cases:
        case_text = str(case.get("text", ""))
        normalized_case = micro_model.normalize(case_text)
        if normalized_case in train_index:
            exact.append(
                {"case_id": case.get("id"), "train_rows": train_index[normalized_case]}
            )
        case_words = word_set(case_text)
        best_score = 0.0
        best_row = -1
        for position, candidate in enumerate(train_word_sets):
            score = jaccard(case_words, candidate)
            if score > best_score:
                best_score = score
                best_row = position
        if best_score >= spec10.JACCARD_NEAR_DUPLICATE:
            near.append(
                {
                    "case_id": case.get("id"),
                    "train_row": best_row,
                    "jaccard": round(best_score, 4),
                }
            )
    return {
        "train_rows": len(samples),
        "eval_cases": len(cases),
        "exact_matches": exact,
        "near_duplicates": near,
        "exact_count": len(exact),
        "near_count": len(near),
        "jaccard_threshold": spec10.JACCARD_NEAR_DUPLICATE,
    }


def stratified_split(
    labels: Sequence[str], validation_share: float, seed: int
) -> Tuple[List[int], List[int]]:
    by_label: Dict[str, List[int]] = {}
    for position, label in enumerate(labels):
        by_label.setdefault(label, []).append(position)
    generator = random.Random(seed)
    train_positions: List[int] = []
    validation_positions: List[int] = []
    for label in sorted(by_label):
        bucket = list(by_label[label])
        generator.shuffle(bucket)
        cut = int(round(len(bucket) * validation_share))
        validation_positions.extend(bucket[:cut])
        train_positions.extend(bucket[cut:])
    return sorted(train_positions), sorted(validation_positions)


def document_frequencies(texts: Sequence[str]) -> Dict[str, int]:
    frequencies: Dict[str, int] = {}
    for text in texts:
        for term in set(micro_model.extract_terms(text)):
            frequencies[term] = frequencies.get(term, 0) + 1
    return frequencies


def min_df_for(term: str) -> int:
    if term.startswith(spec10.CHAR_PREFIX):
        return spec10.MIN_DF_CHAR
    return spec10.MIN_DF_WORD


def build_vocabulary(
    texts: Sequence[str], max_terms: int
) -> Tuple[micro_model.Vocabulary, Dict[str, int]]:
    frequencies = document_frequencies(texts)
    kept = [term for term, count in frequencies.items() if count >= min_df_for(term)]
    kept.sort(key=lambda term: (-frequencies[term], term))
    if len(kept) > max_terms:
        kept = kept[:max_terms]
    kept.sort()
    total = len(texts)
    vocabulary = micro_model.Vocabulary()
    for index, term in enumerate(kept):
        vocabulary.index_of[term] = index
        vocabulary.idf_of[term] = math.log((1.0 + total) / (1.0 + frequencies[term])) + 1.0
    return vocabulary, frequencies


def vocabulary_from_terms(
    terms: Sequence[str], frequencies: Dict[str, int], total: int
) -> micro_model.Vocabulary:
    ordered = sorted(terms)
    vocabulary = micro_model.Vocabulary()
    for index, term in enumerate(ordered):
        vocabulary.index_of[term] = index
        vocabulary.idf_of[term] = math.log((1.0 + total) / (1.0 + frequencies[term])) + 1.0
    return vocabulary


def vectorize_all(texts: Sequence[str], vocabulary: micro_model.Vocabulary) -> List[Vector]:
    return [micro_model.vectorize(text, vocabulary) for text in texts]


def train_softmax(
    vectors: Sequence[Vector],
    targets: Sequence[int],
    feature_count: int,
    class_count: int,
    learning_rate: float,
    momentum: float,
    epochs: int,
    l2_lambda: float,
) -> Tuple[List[List[float]], List[float]]:
    """Полный batch, градиентный спуск с моментом. Веса стартуют нулями - обучение детерминировано."""
    weights = [[0.0] * feature_count for _ in range(class_count)]
    bias = [0.0] * class_count
    velocity = [[0.0] * feature_count for _ in range(class_count)]
    bias_velocity = [0.0] * class_count
    sample_count = max(len(vectors), 1)
    scale = 1.0 / sample_count
    for _ in range(epochs):
        gradient = [[0.0] * feature_count for _ in range(class_count)]
        gradient_bias = [0.0] * class_count
        for position in range(len(vectors)):
            vector = vectors[position]
            scores = list(bias)
            for index, value in vector:
                for klass in range(class_count):
                    scores[klass] += value * weights[klass][index]
            probs = micro_model.softmax(scores)
            probs[targets[position]] -= 1.0
            for klass in range(class_count):
                error = probs[klass]
                if error == 0.0:
                    continue
                gradient_bias[klass] += error
                row = gradient[klass]
                for index, value in vector:
                    row[index] += error * value
        for klass in range(class_count):
            row = weights[klass]
            grad_row = gradient[klass]
            velocity_row = velocity[klass]
            for index in range(feature_count):
                step = grad_row[index] * scale + l2_lambda * row[index]
                velocity_row[index] = momentum * velocity_row[index] - learning_rate * step
                row[index] += velocity_row[index]
            bias_velocity[klass] = (
                momentum * bias_velocity[klass] - learning_rate * gradient_bias[klass] * scale
            )
            bias[klass] += bias_velocity[klass]
    return weights, bias


def predict_probs(
    vectors: Sequence[Vector], weights: Sequence[Sequence[float]], bias: Sequence[float]
) -> List[List[float]]:
    class_count = len(bias)
    outputs: List[List[float]] = []
    for vector in vectors:
        scores = list(bias)
        for index, value in vector:
            for klass in range(class_count):
                scores[klass] += value * weights[klass][index]
        outputs.append(micro_model.softmax(scores))
    return outputs


def accuracy_of(probs: Sequence[Sequence[float]], targets: Sequence[int]) -> float:
    if not probs:
        return 0.0
    hits = 0
    for position, row in enumerate(probs):
        best = max(range(len(row)), key=lambda klass: (row[klass], -klass))
        if best == targets[position]:
            hits += 1
    return hits / len(probs)


def importance_of(
    weights: Sequence[Sequence[float]],
    vocabulary: micro_model.Vocabulary,
    frequencies: Dict[str, int],
    total: int,
) -> List[Tuple[float, str]]:
    scored: List[Tuple[float, str]] = []
    for term, index in vocabulary.index_of.items():
        column = [weights[klass][index] for klass in range(len(weights))]
        spread = max(column) - min(column)
        coverage = math.sqrt(frequencies.get(term, 1) / max(total, 1))
        scored.append((spread * coverage, term))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored


def estimate_bytes(terms: Sequence[str]) -> int:
    total = HEADER_BYTES
    for term in terms:
        total += len(term.encode("utf-8")) + VOCABULARY_ENTRY_OVERHEAD + WEIGHT_ENTRY_OVERHEAD
    return total


def fit_terms_to_budget(ranked: Sequence[Tuple[float, str]], budget: int, cap: int) -> List[str]:
    limit = min(cap, len(ranked))
    terms = [term for _, term in ranked[:limit]]
    while terms and estimate_bytes(terms) > budget * BUDGET_SAFETY:
        terms = terms[: int(len(terms) * spec10.VOCAB_SHRINK_FACTOR)]
    return terms


def sparse_weights(
    weights: Sequence[Sequence[float]], feature_count: int
) -> Dict[int, List[float]]:
    rows: Dict[int, List[float]] = {}
    for index in range(feature_count):
        column = [weights[klass][index] for klass in range(len(weights))]
        if max(abs(value) for value in column) < spec10.WEIGHT_EPSILON:
            continue
        rows[index] = column
    return rows


def build_model(
    texts: Sequence[str],
    targets: Sequence[int],
    settings: argparse.Namespace,
    log: Any,
) -> Tuple[micro_model.MicroModel, Dict[str, Any]]:
    """Два прохода: широкий словарь -> обучение -> обрезка по важности -> переобучение."""
    started = time.time()
    wide_vocabulary, frequencies = build_vocabulary(texts, settings.max_vocab_pretrain)
    log("широкий словарь: %d признаков" % wide_vocabulary.size())
    wide_vectors = vectorize_all(texts, wide_vocabulary)
    wide_weights, wide_bias = train_softmax(
        wide_vectors,
        targets,
        wide_vocabulary.size(),
        len(spec10.LABELS),
        settings.learning_rate,
        settings.momentum,
        settings.epochs,
        settings.l2_lambda,
    )
    wide_accuracy = accuracy_of(predict_probs(wide_vectors, wide_weights, wide_bias), targets)
    log("широкая модель обучена, точность на своих данных %.4f" % wide_accuracy)

    ranked = importance_of(wide_weights, wide_vocabulary, frequencies, len(texts))
    kept_terms = fit_terms_to_budget(ranked, spec10.MAX_MODEL_BYTES, settings.max_vocab_final)
    log("после обрезки осталось %d признаков" % len(kept_terms))

    attempt = 0
    while True:
        attempt += 1
        narrow_vocabulary = vocabulary_from_terms(kept_terms, frequencies, len(texts))
        narrow_vectors = vectorize_all(texts, narrow_vocabulary)
        narrow_weights, narrow_bias = train_softmax(
            narrow_vectors,
            targets,
            narrow_vocabulary.size(),
            len(spec10.LABELS),
            settings.learning_rate,
            settings.momentum,
            settings.epochs,
            settings.l2_lambda,
        )
        model = micro_model.MicroModel(
            labels=spec10.LABELS,
            vocabulary=narrow_vocabulary,
            weights=sparse_weights(narrow_weights, narrow_vocabulary.size()),
            bias=list(narrow_bias),
            confident_min_prob=0.0,
            confident_min_margin=0.0,
            always_escalate_labels=spec10.ALWAYS_ESCALATE_LABELS,
            meta={"train_size": len(texts)},
        )
        size = micro_model.model_bytes(model)
        if size <= spec10.MAX_MODEL_BYTES or attempt >= spec10.MAX_BUDGET_ATTEMPTS:
            break
        kept_terms = kept_terms[: int(len(kept_terms) * spec10.VOCAB_SHRINK_FACTOR)]
        log("не влезли в бюджет (%d байт), режем до %d признаков" % (size, len(kept_terms)))

    narrow_probs = predict_probs(narrow_vectors, narrow_weights, narrow_bias)
    stats = {
        "wide_vocabulary": wide_vocabulary.size(),
        "final_vocabulary": narrow_vocabulary.size(),
        "wide_train_accuracy": round(wide_accuracy, 4),
        "final_train_accuracy": round(accuracy_of(narrow_probs, targets), 4),
        "model_bytes": micro_model.model_bytes(model),
        "seconds": round(time.time() - started, 1),
        "budget_attempts": attempt,
    }
    return model, stats


def evaluate_thresholds(
    probs: Sequence[Sequence[float]],
    targets: Sequence[int],
    model: micro_model.MicroModel,
    min_prob: float,
    min_margin: float,
) -> Dict[str, Any]:
    probe = micro_model.MicroModel(
        labels=model.labels,
        vocabulary=model.vocabulary,
        weights=model.weights,
        bias=model.bias,
        confident_min_prob=min_prob,
        confident_min_margin=min_margin,
        always_escalate_labels=model.always_escalate_labels,
    )
    ok_count = 0
    ok_hits = 0
    for position, row in enumerate(probs):
        prediction = micro_model.decide(list(row), probe)
        if prediction.status != spec10.STATUS_OK:
            continue
        ok_count += 1
        if model.labels.index(prediction.label) == targets[position]:
            ok_hits += 1
    total = max(len(probs), 1)
    return {
        "confident_min_prob": min_prob,
        "confident_min_margin": min_margin,
        "coverage": round(ok_count / total, 4),
        "ok_count": ok_count,
        "precision_on_ok": round(ok_hits / ok_count, 4) if ok_count else 0.0,
    }


def pick_thresholds(
    probs: Sequence[Sequence[float]], targets: Sequence[int], model: micro_model.MicroModel
) -> Tuple[float, float, List[Dict[str, Any]]]:
    grid: List[Dict[str, Any]] = []
    for min_prob in spec10.PROB_GRID:
        for min_margin in spec10.MARGIN_GRID:
            grid.append(evaluate_thresholds(probs, targets, model, min_prob, min_margin))
    passing = [row for row in grid if row["precision_on_ok"] >= spec10.MIN_PRECISION_ON_OK]
    pool = passing if passing else grid
    key = (
        (lambda row: (-row["coverage"], -row["precision_on_ok"], row["confident_min_prob"]))
        if passing
        else (lambda row: (-row["precision_on_ok"], -row["coverage"], row["confident_min_prob"]))
    )
    best = sorted(pool, key=key)[0]
    return best["confident_min_prob"], best["confident_min_margin"], grid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Обучение micro-model для каскада task10")
    parser.add_argument("--train", dest="train_path", default=spec10.TRAIN_PATH)
    parser.add_argument("--cases", dest="cases_path", default=spec10.CASES_PATH)
    parser.add_argument("--out", dest="out_path", default=spec10.MODEL_PATH)
    parser.add_argument("--report", dest="report_path", default=spec10.TRAIN_REPORT_PATH)
    parser.add_argument("--seed", type=int, default=spec10.SEED)
    parser.add_argument("--epochs", type=int, default=spec10.EPOCHS)
    parser.add_argument("--learning-rate", dest="learning_rate", type=float, default=spec10.LEARNING_RATE)
    parser.add_argument("--momentum", type=float, default=spec10.MOMENTUM)
    parser.add_argument("--l2", dest="l2_lambda", type=float, default=spec10.L2_LAMBDA)
    parser.add_argument(
        "--max-vocab-pretrain", dest="max_vocab_pretrain", type=int, default=spec10.MAX_VOCAB_PRETRAIN
    )
    parser.add_argument(
        "--max-vocab-final", dest="max_vocab_final", type=int, default=spec10.MAX_VOCAB_FINAL
    )
    parser.add_argument(
        "--exclude-eval-overlap", dest="exclude_overlap", action="store_true",
        help="выкинуть из обучения строки, пересекающиеся с cases.jsonl",
    )
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    def log(message: str) -> None:
        if not args.quiet:
            print(message)

    if not os.path.isfile(args.train_path):
        print("нет обучающего корпуса: %s" % args.train_path)
        return 2
    if not os.path.isfile(args.cases_path):
        print("нет оценочного набора: %s" % args.cases_path)
        return 2

    samples = load_corpus(args.train_path)
    cases = load_cases(args.cases_path)
    log("корпус: %d примеров, оценочный набор: %d кейсов" % (len(samples), len(cases)))

    overlap = overlap_report(samples, cases)
    log(
        "пересечение train и eval: точных %d, близких %d"
        % (overlap["exact_count"], overlap["near_count"])
    )

    excluded_rows = sorted(
        {row for entry in overlap["exact_matches"] for row in entry["train_rows"]}
        | {entry["train_row"] for entry in overlap["near_duplicates"]}
    )
    if args.exclude_overlap and excluded_rows:
        keep = set(range(len(samples))) - set(excluded_rows)
        samples = [samples[position] for position in sorted(keep)]
        log("исключено %d пересекающихся строк, осталось %d" % (len(excluded_rows), len(samples)))

    texts = [text for text, _ in samples]
    labels = [label for _, label in samples]
    targets = [spec10.LABELS.index(label) for label in labels]

    train_positions, validation_positions = stratified_split(
        labels, spec10.VALIDATION_SHARE, args.seed
    )
    log(
        "разбиение %d / %d (обучение / валидация)"
        % (len(train_positions), len(validation_positions))
    )

    fold_texts = [texts[position] for position in train_positions]
    fold_targets = [targets[position] for position in train_positions]
    log("--- фолд для подбора порогов ---")
    fold_model, fold_stats = build_model(fold_texts, fold_targets, args, log)

    validation_texts = [texts[position] for position in validation_positions]
    validation_targets = [targets[position] for position in validation_positions]
    validation_vectors = vectorize_all(validation_texts, fold_model.vocabulary)
    validation_weights = [
        [fold_model.weights.get(index, [0.0] * len(spec10.LABELS))[klass]
         for index in range(fold_model.vocabulary.size())]
        for klass in range(len(spec10.LABELS))
    ]
    validation_probs = predict_probs(validation_vectors, validation_weights, fold_model.bias)
    validation_accuracy = accuracy_of(validation_probs, validation_targets)
    log("точность фолда на валидации: %.4f" % validation_accuracy)

    min_prob, min_margin, grid = pick_thresholds(validation_probs, validation_targets, fold_model)
    log("выбранные пороги: prob >= %.2f, margin >= %.2f" % (min_prob, min_margin))

    log("--- финальная модель на всём корпусе ---")
    final_model, final_stats = build_model(texts, targets, args, log)
    final_model.confident_min_prob = min_prob
    final_model.confident_min_margin = min_margin

    try:
        micro_model.check_invariant(
            final_model.labels, final_model.always_escalate_labels
        )
    except micro_model.InvalidWeightsError as invariant_error:
        print("веса не прошли инвариант раздела 5.3, файл не записан: %s" % invariant_error)
        return 3
    size = micro_model.save_model(final_model, args.out_path)
    log("инвариант раздела 5.3 пройден, веса годны")
    log("записан %s, %d байт (%.1f КБ)" % (args.out_path, size, size / 1024.0))

    report = {
        "train_path": os.path.relpath(args.train_path, spec10.CHALLENGE_DIR),
        "cases_path": os.path.relpath(args.cases_path, spec10.CHALLENGE_DIR),
        "seed": args.seed,
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "momentum": args.momentum,
        "l2_lambda": args.l2_lambda,
        "excluded_overlap_rows": excluded_rows if args.exclude_overlap else [],
        "overlap": overlap,
        "split": {
            "train": len(train_positions),
            "validation": len(validation_positions),
            "validation_share": spec10.VALIDATION_SHARE,
        },
        "fold_model": fold_stats,
        "fold_validation_accuracy": round(validation_accuracy, 4),
        "threshold_grid": grid,
        "thresholds": {
            "confident_min_prob": min_prob,
            "confident_min_margin": min_margin,
            "min_precision_on_ok": spec10.MIN_PRECISION_ON_OK,
        },
        "final_model": final_stats,
        "model_bytes": size,
        "model_kb": round(size / 1024.0, 1),
        "label_counts": {
            label: labels.count(label) for label in spec10.LABELS
        },
    }
    directory = os.path.dirname(args.report_path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(args.report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    log("отчёт обучения: %s" % args.report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
