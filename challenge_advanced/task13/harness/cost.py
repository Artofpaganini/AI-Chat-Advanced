"""Оценка токенов по длине текста и расчёт стоимости запроса.

Тарифы приходят из spec13 - там же, где их фиксировал раздел 11 контракта, а не заново
здесь. Оценка длины используется только когда апстрим не вернул usage.
"""

from spec13 import CHARS_PER_TOKEN_ESTIMATE, PRICE_PER_1M_INPUT, PRICE_PER_1M_OUTPUT, TOKENS_PER_MILLION

COST_DECIMALS = 6


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(round(len(text) / CHARS_PER_TOKEN_ESTIMATE)))


def compute_cost(tokens_in: int, tokens_out: int) -> float:
    input_cost = max(tokens_in, 0) * PRICE_PER_1M_INPUT / TOKENS_PER_MILLION
    output_cost = max(tokens_out, 0) * PRICE_PER_1M_OUTPUT / TOKENS_PER_MILLION
    return round(input_cost + output_cost, COST_DECIMALS)
