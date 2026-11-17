# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the reading of the titles of the TypeScript tests (US-2440)."""

import pytest

from wftools import coverage

pytestmark = pytest.mark.requirement("WF-QUA-0010-A")


def cited(source: str, path: str = "frontend/src/a.test.tsx") -> list[tuple[str, str, bool]]:
    found = coverage.typescript_citations(path, source, "front")
    return [(c.requirement, c.test.rsplit(":", 1)[1], c.executed) for c in found]


def test_a_title_after_a_regular_expression_a_template_or_a_text_of_jsx_is_read() -> None:
    source = """\
const sorted = (h: string) => `${/aria-sort="([^"]*)"/.exec(h)?.[1] ?? ""}`;
const links = (m: string) => m.matchAll(/<a [^>]*href="([^"]*)"[^>]*>/g);
const blank = <T extends { label?: string }>(items: readonly T[]) => items;
const page = <p className="x">Don't {"quote"} it's / not // a comment</p>;
const half = 1 / 2;
it("reads after them [WF-QUA-0050-A]", () => {});
"""
    assert cited(source) == [("WF-QUA-0050-A", "6", True)]


def test_a_title_built_from_a_table_cites_what_its_rows_say() -> None:
    source = """\
it.each<{ title: string }>([
  { title: "a lot [WF-PLA-0170-A]" },
  { title: "a post" },
])("refuses $title", ({ title }) => {});
it.each([["fr"], ["en"]])("shows, in %s [WF-PLA-0030-A]", () => {});
"""
    assert cited(source, "frontend/src/a.test.ts") == [
        ("WF-PLA-0170-A", "2", True),
        ("WF-PLA-0030-A", "5", True),
    ]


def test_a_title_on_its_own_line_is_placed_at_that_line() -> None:
    source = """\
describe("grid", () => {
  it(
    "reads [WF-QUA-0050-A]",
    () => {},
  );
});
"""
    assert cited(source) == [("WF-QUA-0050-A", "3", True)]


def test_a_call_that_declares_no_test_cites_nothing() -> None:
    source = """\
test.describe.configure({ mode: "serial" });
test("walks", async () => {
  await test.step("opens [WF-QUA-0010-A]", async () => {});
  expect(page).toHaveTitle("a title [WF-QUA-0020-A]");
  /x/.test("y [WF-QUA-0030-A]");
});
"""
    assert cited(source, "frontend/e2e/w.spec.ts") == []


def test_a_group_whose_tests_are_built_by_code_runs() -> None:
    source = """\
describe("each case [WF-QUA-0010-A]", () => {
  for (const each of CASES) it(each.name, () => {});
});
"""
    assert cited(source, "frontend/src/a.test.ts") == [("WF-QUA-0010-A", "1", True)]
