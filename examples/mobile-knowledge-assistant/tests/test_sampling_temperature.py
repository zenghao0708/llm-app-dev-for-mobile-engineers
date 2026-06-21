import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from argparse import ArgumentTypeError

from sampling_temperature_experiment import (
    DEFAULT_CANDIDATES,
    positive_float,
    positive_int,
    run_experiment,
    softmax_with_temperature,
)


class SamplingTemperatureTest(unittest.TestCase):
    def test_probabilities_sum_to_one(self):
        distribution = softmax_with_temperature(DEFAULT_CANDIDATES, temperature=0.7)

        self.assertAlmostEqual(sum(probability for _, probability in distribution), 1.0)

    def test_low_temperature_makes_top_token_more_likely(self):
        low = dict(softmax_with_temperature(DEFAULT_CANDIDATES, temperature=0.2))
        high = dict(softmax_with_temperature(DEFAULT_CANDIDATES, temperature=1.5))

        self.assertGreater(low["检查"], high["检查"])

    def test_sampling_is_reproducible_with_seed(self):
        first = run_experiment(temperature=0.8, rounds=20, seed=42)
        second = run_experiment(temperature=0.8, rounds=20, seed=42)

        self.assertEqual(first, second)

    def test_sampling_count_matches_rounds(self):
        counts = run_experiment(temperature=0.8, rounds=20, seed=42)

        self.assertEqual(sum(counts.values()), 20)

    def test_temperature_must_be_positive(self):
        with self.assertRaises(ValueError):
            softmax_with_temperature(DEFAULT_CANDIDATES, temperature=0)

    def test_temperature_must_be_finite(self):
        with self.assertRaises(ValueError):
            softmax_with_temperature(DEFAULT_CANDIDATES, temperature=float("nan"))
        with self.assertRaises(ValueError):
            softmax_with_temperature(DEFAULT_CANDIDATES, temperature=float("inf"))

    def test_rounds_must_be_positive(self):
        with self.assertRaises(ValueError):
            run_experiment(temperature=0.8, rounds=0, seed=42)

    def test_cli_temperature_type_rejects_non_positive_values(self):
        with self.assertRaises(ArgumentTypeError):
            positive_float("0")

    def test_cli_temperature_type_rejects_non_finite_values(self):
        with self.assertRaises(ArgumentTypeError):
            positive_float("nan")
        with self.assertRaises(ArgumentTypeError):
            positive_float("inf")

    def test_cli_rounds_type_rejects_non_positive_values(self):
        with self.assertRaises(ArgumentTypeError):
            positive_int("-5")


if __name__ == "__main__":
    unittest.main()
