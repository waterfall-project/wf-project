# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the metrics share: an exposition of Prometheus, read by the client library."""

from prometheus_client.parser import text_string_to_metric_families

type Samples = dict[tuple[str, frozenset[tuple[str, str]]], float]


def samples(exposition: str) -> Samples:
    """Read an exposition of Prometheus: the value of each sample, by its name and its labels."""
    return {
        (sample.name, frozenset(sample.labels.items())): sample.value
        for family in text_string_to_metric_families(exposition)
        for sample in family.samples
    }


def value(read: Samples, name: str, **labels: str) -> float | None:
    """Give the value of the sample of a name and labels, or ``None`` if there is none."""
    return read.get((name, frozenset(labels.items())))
