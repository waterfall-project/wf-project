# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The identifiers the service draws, and those the loader of the witness draws in order.

``new_id`` draws a version 7 identifier at random; within ``drawn_in_order``, the loader of the
witness draws the next of a count under a fixed instant, so that two loadings give the same
identifiers, in the order the rows are written (WF-QUA-0040; US-2650/L1).
"""

from datetime import UTC, datetime

import pytest

from waterfall.platform.identifiers import drawn_in_order, new_id, ordered_identifier

pytestmark = pytest.mark.requirement("WF-QUA-0040-A")

AT = datetime(2025, 9, 1, 9, 0, tzinfo=UTC)


def test_two_drawings_in_order_give_the_same_identifiers_in_the_order_they_are_drawn() -> None:
    # « Deux engendrements successifs donnent des données identifiantes identiques. »
    with drawn_in_order(AT):
        first = [new_id() for _ in range(5)]
    with drawn_in_order(AT):
        second = [new_id() for _ in range(5)]
    assert first == second
    assert first == sorted(first)
    assert len(set(first)) == 5
    assert all(each.version == 7 for each in first)
    # Under the instant given, before any the service draws afterwards.
    assert first[-1] < new_id()


def test_out_of_the_block_the_identifiers_are_drawn_at_random_again() -> None:
    with drawn_in_order(AT):
        ordered = new_id()
    drawn = {new_id() for _ in range(3)}
    assert ordered not in drawn
    assert len(drawn) == 3
    message = "raised"
    with pytest.raises(RuntimeError, match=message), drawn_in_order(AT):
        raise RuntimeError(message)
    assert new_id() != ordered


def test_an_identifier_in_order_is_that_of_its_instant_and_its_number() -> None:
    milliseconds = int(AT.timestamp() * 1000)
    assert ordered_identifier(milliseconds, 1) == ordered_identifier(milliseconds, 1)
    assert ordered_identifier(milliseconds, 1) < ordered_identifier(milliseconds, 2)
    assert ordered_identifier(milliseconds, 2) < ordered_identifier(milliseconds + 1, 1)
    with pytest.raises(ValueError, match="does not fit"):
        ordered_identifier(milliseconds, 1 << 62)
    with pytest.raises(ValueError, match="does not fit"):
        ordered_identifier(milliseconds, -1)
