"""Инференс micro-model - буквальный перевод разделов 2-5 контракта WEIGHTS_FORMAT.md в код.

Этот файл читают и обучение, и замер. Kotlin-реализация повторяет ровно эти шаги, поэтому любая
правка здесь - правка контракта, а не оптимизация.

Только стандартная библиотека. Никакого numpy: в системе его нет, и на устройстве его тоже не будет.
"""

import json
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import spec10

DIGIT_PLACEHOLDER = "0"
SPACE = " "


def normalize(text: str) -> str:
    """Шаги 1-5 раздела 2 контракта, порядок менять нельзя."""
    if not text:
        return ""
    lowered = text.lower().replace("ё", "е")
    pieces: List[str] = []
    for symbol in lowered:
        if symbol.isdecimal():
            pieces.append(DIGIT_PLACEHOLDER)
        elif symbol.isalpha() or symbol == SPACE:
            pieces.append(symbol)
        else:
            pieces.append(SPACE)
    return SPACE.join("".join(pieces).split())


def word_terms(normalized: str) -> List[str]:
    if not normalized:
        return []
    tokens = normalized.split(SPACE)
    terms = [spec10.WORD_PREFIX + token for token in tokens]
    for position in range(len(tokens) - 1):
        terms.append(spec10.WORD_PREFIX + tokens[position] + SPACE + tokens[position + 1])
    return terms


def char_terms(normalized: str) -> List[str]:
    if not normalized:
        return []
    terms: List[str] = []
    length = len(normalized)
    for size in range(spec10.CHAR_NGRAM_MIN, spec10.CHAR_NGRAM_MAX + 1):
        for start in range(length - size + 1):
            terms.append(spec10.CHAR_PREFIX + normalized[start : start + size])
    return terms


def extract_terms(text: str) -> List[str]:
    normalized = normalize(text)
    return word_terms(normalized) + char_terms(normalized)


def term_frequencies(terms: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for term in terms:
        counts[term] = counts.get(term, 0) + 1
    return counts


@dataclass
class Vocabulary:
    index_of: Dict[str, int] = field(default_factory=dict)
    idf_of: Dict[str, float] = field(default_factory=dict)

    def size(self) -> int:
        return len(self.index_of)


@dataclass
class MicroModel:
    labels: Tuple[str, ...]
    vocabulary: Vocabulary
    weights: Dict[int, List[float]]
    bias: List[float]
    confident_min_prob: float
    confident_min_margin: float
    always_escalate_labels: Tuple[str, ...]
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Prediction:
    label: str
    prob: float
    margin: float
    status: str
    probs: List[float]


def vectorize(text: str, vocabulary: Vocabulary) -> List[Tuple[int, float]]:
    """Шаги 1-3 раздела 4: tf * idf по словарю, затем L2-нормировка."""
    counts = term_frequencies(extract_terms(text))
    pairs: List[Tuple[int, float]] = []
    for term, count in counts.items():
        index = vocabulary.index_of.get(term)
        if index is None:
            continue
        pairs.append((index, count * vocabulary.idf_of[term]))
    return l2_normalize(pairs)


def l2_normalize(pairs: List[Tuple[int, float]]) -> List[Tuple[int, float]]:
    norm = math.sqrt(sum(value * value for _, value in pairs))
    if norm <= 0.0:
        return sorted(pairs)
    return sorted((index, value / norm) for index, value in pairs)


def raw_scores(
    vector: List[Tuple[int, float]], weights: Dict[int, List[float]], bias: List[float]
) -> List[float]:
    scores = list(bias)
    for index, value in vector:
        row = weights.get(index)
        if row is None:
            continue
        for position in range(len(scores)):
            scores[position] += value * row[position]
    return scores


def softmax(scores: List[float]) -> List[float]:
    top = max(scores)
    exponents = [math.exp(score - top) for score in scores]
    total = sum(exponents)
    if total <= 0.0:
        share = 1.0 / len(scores)
        return [share for _ in scores]
    return [value / total for value in exponents]


def decide(probs: List[float], model: MicroModel) -> Prediction:
    """Раздел 5 контракта: top1, margin, порог, принудительная эскалация EMERGENCY."""
    ordered = sorted(range(len(probs)), key=lambda position: (-probs[position], position))
    top1 = ordered[0]
    top2 = ordered[1] if len(ordered) > 1 else top1
    prob = probs[top1]
    margin = prob - probs[top2]
    label = model.labels[top1]
    confident = prob >= model.confident_min_prob and margin >= model.confident_min_margin
    status = spec10.STATUS_OK if confident else spec10.STATUS_UNSURE
    if label in model.always_escalate_labels:
        status = spec10.STATUS_UNSURE
    return Prediction(label=label, prob=prob, margin=margin, status=status, probs=probs)


def predict(text: str, model: MicroModel) -> Prediction:
    vector = vectorize(text, model.vocabulary)
    probs = softmax(raw_scores(vector, model.weights, model.bias))
    return decide(probs, model)


def normalizer_block() -> Dict[str, Any]:
    return {
        "lowercase": True,
        "yo_to_e": True,
        "collapse_whitespace": True,
        "strip_chars": "non_letter_non_digit_non_space",
        "digit_placeholder": DIGIT_PLACEHOLDER,
    }


def vectorizer_analyzers() -> List[Dict[str, Any]]:
    return [
        {"kind": "word", "ngram_min": spec10.WORD_NGRAM_MIN, "ngram_max": spec10.WORD_NGRAM_MAX},
        {"kind": "char", "ngram_min": spec10.CHAR_NGRAM_MIN, "ngram_max": spec10.CHAR_NGRAM_MAX},
    ]


def to_json_document(model: MicroModel) -> Dict[str, Any]:
    vocabulary_block: Dict[str, Any] = {}
    for term, index in sorted(model.vocabulary.index_of.items(), key=lambda item: item[1]):
        vocabulary_block[term] = {
            "i": index,
            "idf": round(model.vocabulary.idf_of[term], spec10.IDF_DECIMALS),
        }
    weights_block: Dict[str, Any] = {}
    for index in sorted(model.weights):
        weights_block[str(index)] = [
            round(value, spec10.WEIGHT_DECIMALS) for value in model.weights[index]
        ]
    document: Dict[str, Any] = {
        "format_version": spec10.FORMAT_VERSION,
        "trained_on": spec10.TRAIN_RELATIVE_NAME,
        "train_size": int(model.meta.get("train_size", 0)),
        "seed": spec10.SEED,
        "labels": list(model.labels),
        "normalizer": normalizer_block(),
        "vectorizer": {
            "kind": "tfidf",
            "norm": "l2",
            "analyzers": vectorizer_analyzers(),
            "vocabulary": vocabulary_block,
        },
        "classifier": {
            "kind": "logreg_softmax",
            "bias": [round(value, spec10.WEIGHT_DECIMALS) for value in model.bias],
            "weights": weights_block,
        },
        "thresholds": {
            "confident_min_prob": model.confident_min_prob,
            "confident_min_margin": model.confident_min_margin,
            "always_escalate_labels": list(model.always_escalate_labels),
        },
    }
    return document


def dumps_model(model: MicroModel) -> str:
    return json.dumps(to_json_document(model), ensure_ascii=False, sort_keys=False)


class InvalidWeightsError(Exception):
    """Веса не прошли инвариант раздела 5.3 контракта и негодны целиком."""


def check_invariant(labels: Sequence[str], always_escalate: Sequence[str]) -> None:
    """Раздел 5.3: без EMERGENCY в always_escalate защита отключается молча, это недопустимо."""
    missing = [label for label in spec10.LABELS if label not in labels]
    if missing:
        raise InvalidWeightsError(
            "в labels нет обязательных маршрутов: %s" % ", ".join(missing)
        )
    if spec10.LABEL_EMERGENCY not in always_escalate:
        raise InvalidWeightsError(
            "в thresholds.always_escalate_labels нет %s, защита экстренных случаев отключена"
            % spec10.LABEL_EMERGENCY
        )


def from_json_document(document: Dict[str, Any]) -> MicroModel:
    labels = tuple(document["labels"])
    vocabulary = Vocabulary()
    raw_vocabulary = document["vectorizer"]["vocabulary"]
    for term, entry in raw_vocabulary.items():
        vocabulary.index_of[term] = int(entry["i"])
        vocabulary.idf_of[term] = float(entry["idf"])
    weights: Dict[int, List[float]] = {}
    for key, row in document["classifier"]["weights"].items():
        weights[int(key)] = [float(value) for value in row]
    thresholds = document["thresholds"]
    check_invariant(labels, tuple(thresholds["always_escalate_labels"]))
    return MicroModel(
        labels=labels,
        vocabulary=vocabulary,
        weights=weights,
        bias=[float(value) for value in document["classifier"]["bias"]],
        confident_min_prob=float(thresholds["confident_min_prob"]),
        confident_min_margin=float(thresholds["confident_min_margin"]),
        always_escalate_labels=tuple(thresholds["always_escalate_labels"]),
        meta={
            "train_size": int(document.get("train_size", 0)),
            "format_version": int(document.get("format_version", 0)),
        },
    )


def load_model(path: str) -> MicroModel:
    with open(path, "r", encoding="utf-8") as handle:
        return from_json_document(json.load(handle))


def save_model(model: MicroModel, path: str) -> int:
    check_invariant(model.labels, model.always_escalate_labels)
    payload = dumps_model(model)
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return len(payload.encode("utf-8"))


def model_bytes(model: MicroModel) -> int:
    return len(dumps_model(model).encode("utf-8"))


def label_index(labels: Tuple[str, ...], label: str) -> Optional[int]:
    if label not in labels:
        return None
    return labels.index(label)
