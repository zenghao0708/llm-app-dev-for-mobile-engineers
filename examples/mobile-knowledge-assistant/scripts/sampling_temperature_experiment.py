from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateToken:
    text: str
    logit: float


DEFAULT_CANDIDATES = [
    CandidateToken("检查", 4.8),
    CandidateToken("修复", 4.1),
    CandidateToken("删除", 2.2),
    CandidateToken("重启", 1.8),
    CandidateToken("忽略", 0.5),
]


def softmax_with_temperature(candidates: list[CandidateToken], temperature: float) -> list[tuple[str, float]]:
    """Convert logits to probabilities after temperature scaling.

    Lower temperature makes the largest logit dominate. Higher temperature
    flattens the distribution, which is why generation becomes more diverse
    and less stable.
    """

    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be a finite number greater than 0")

    scaled = [item.logit / temperature for item in candidates]
    max_logit = max(scaled)
    exps = [math.exp(value - max_logit) for value in scaled]
    total = sum(exps)
    return [(item.text, value / total) for item, value in zip(candidates, exps)]


def sample_token(distribution: list[tuple[str, float]], rng: random.Random) -> str:
    cursor = rng.random()
    cumulative = 0.0
    # Pick the token whose cumulative probability interval contains cursor.
    for token, probability in distribution:
        cumulative += probability
        if cursor <= cumulative:
            return token
    return distribution[-1][0]


def run_experiment(temperature: float, rounds: int, seed: int) -> dict[str, int]:
    if rounds <= 0:
        raise ValueError("rounds must be greater than 0")

    rng = random.Random(seed)
    distribution = softmax_with_temperature(DEFAULT_CANDIDATES, temperature)
    counts = {token: 0 for token, _ in distribution}
    for _ in range(rounds):
        counts[sample_token(distribution, rng)] += 1
    return counts


def positive_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than 0")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Show how temperature changes token sampling.")
    parser.add_argument("--temperature", type=positive_float, default=0.3)
    parser.add_argument("--rounds", type=positive_int, default=50)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    distribution = softmax_with_temperature(DEFAULT_CANDIDATES, args.temperature)
    counts = run_experiment(args.temperature, args.rounds, args.seed)

    print(f"temperature={args.temperature}, rounds={args.rounds}, seed={args.seed}")
    print("probabilities:")
    for token, probability in distribution:
        print(f"  {token}: {probability:.3f}")
    print("sampled counts:")
    for token, count in counts.items():
        print(f"  {token}: {count}")


if __name__ == "__main__":
    main()
