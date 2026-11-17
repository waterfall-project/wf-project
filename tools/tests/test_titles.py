# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the reading of the titles of the TypeScript tests (US-2440)."""

import pytest

from wftools import coverage, titles

pytestmark = pytest.mark.requirement("WF-QUA-0010-A")


def cited(source: str, path: str = "frontend/src/a.test.ts") -> list[tuple[str, str, bool]]:
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
    assert cited(source, "frontend/src/a.test.tsx") == [("WF-QUA-0050-A", "6", True)]


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


def test_a_title_after_a_tagged_template_table_is_read() -> None:
    source = """\
it.each`
  a | b
  ${1} | ${"x [WF-PLA-0170-A]"}
`("adds $a [WF-PLA-0030-A]", ({ a }) => {});
it.skip.each`a|b`("sorts [WF-PLA-0040-A]", () => {});
"""
    assert cited(source) == [
        ("WF-PLA-0170-A", "3", True),
        ("WF-PLA-0030-A", "4", True),
        ("WF-PLA-0040-A", "5", False),
    ]


def test_a_conditional_skip_of_vitest_is_read_and_counts_as_run() -> None:
    source = """\
it.skipIf(isCi)("sorts [WF-QUA-0010-A]", () => {});
it.runIf(!isCi)("filters [WF-QUA-0020-A]", () => {});
it.concurrent.skipIf(isCi).each([1, 2])("groups [WF-QUA-0030-A]", () => {});
"""
    assert cited(source) == [
        ("WF-QUA-0010-A", "1", True),
        ("WF-QUA-0020-A", "2", True),
        ("WF-QUA-0030-A", "3", True),
    ]


def test_the_modes_of_a_group_of_playwright_are_read() -> None:
    source = """\
test.describe.serial("a [WF-QUA-0010-A]", () => {
  test("one", async () => {});
});
test.describe.parallel("b [WF-QUA-0020-A]", () => {
  test("two", async () => {});
});
test.describe.serial.skip("c [WF-QUA-0030-A]", () => {
  test("three [WF-QUA-0040-A]", async () => {});
});
test.describe.serial.fixme("d", () => {
  test("four [WF-QUA-0050-A]", async () => {});
});
"""
    assert cited(source, "frontend/e2e/a.spec.ts") == [
        ("WF-QUA-0010-A", "1", True),
        ("WF-QUA-0020-A", "4", True),
        ("WF-QUA-0030-A", "7", False),
        ("WF-QUA-0040-A", "8", False),
        ("WF-QUA-0050-A", "11", False),
    ]


def test_an_annotation_of_playwright_in_a_body_is_no_test() -> None:
    source = """\
test("walks [WF-QUA-0010-A]", async () => {
  test.fail(isFirefox, "known [WF-QUA-0020-A]");
  test.fail();
  test.slow();
});
test.fail("is expected to fail [WF-QUA-0030-A]", async () => {});
"""
    assert cited(source, "frontend/e2e/a.spec.ts") == [
        ("WF-QUA-0010-A", "1", True),
        ("WF-QUA-0030-A", "6", True),
    ]


@pytest.mark.parametrize("call", ["it.parallel", "test.sometimes", "describe.sometimes"])
def test_a_call_of_a_form_not_known_fails_naming_the_file_and_the_line(call: str) -> None:
    source = f'\n\n{call}("x [WF-QUA-0010-A]", () => {{}});\n'
    with pytest.raises(titles.UnreadableError, match=r"frontend/src/a\.test\.ts:3: "):
        coverage.typescript_citations("frontend/src/a.test.ts", source, "front")


def test_the_calls_the_front_uses_that_declare_nothing_are_not_read() -> None:
    source = """\
test.use({ locale: "fr" });
test.beforeEach(async () => {});
test.setTimeout(60_000);
test.describe.configure({ mode: "serial" });
test.slow();
test.info().annotations.push({ type: "x" });
"""
    assert cited(source, "frontend/e2e/a.spec.ts") == []


def test_a_group_with_no_test_in_it_does_not_run() -> None:
    source = """\
describe("empty [WF-QUA-0010-A]", () => {
  const helper = () => 1;
});
"""
    assert cited(source) == [("WF-QUA-0010-A", "1", False)]
