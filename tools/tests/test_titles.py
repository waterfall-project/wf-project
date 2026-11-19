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
    import_ = 'import { it, test, describe } from "vitest";'
    source = f'{import_}\n\n{call}("x [WF-QUA-0010-A]", () => {{}});\n'
    with pytest.raises(titles.UnreadableError, match=r"frontend/src/a\.test\.ts:3: "):
        coverage.typescript_citations("frontend/src/a.test.ts", source, "front")


@pytest.mark.parametrize(
    "source",
    [
        "const it = list.values();\nit.next();\n",
        "function f(test: Test) {\n  test.sometimes(1);\n}\nconst describe = { parallel: 1 };\n",
        "import { expect } from 'vitest';\nconst it = list.values();\nit.next();\n",
    ],
)
def test_a_variable_named_like_a_test_function_is_not_a_call_not_known(source: str) -> None:
    # #3753: only a file that imports the name owns a call of the runner it does not know.
    assert cited(source) == []


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


def runs(source: str) -> dict[str, bool]:
    return {r: ok for r, _line, ok in cited(source)}


@pytest.mark.story("US-2440")
@pytest.mark.parametrize(
    "call",
    [
        "test.skip(inService, 'x');",
        "test.skip(!inService, 'x');",
        "test.skip( ! inService ,\n    'x',\n  );",
        "test.skip(\n    inService,\n    SERVICE_ONLY,\n  );",
    ],
)
def test_a_skip_on_the_platform_leaves_the_test_executed(call: str) -> None:
    source = f'test("a [WF-QUA-0050-A]", async () => {{\n  {call}\n}});\n'
    assert runs(source) == {"WF-QUA-0050-A": True}


@pytest.mark.story("US-2440")
@pytest.mark.parametrize(
    "call",
    [
        "test.skip(true, SERVICE_ONLY);",
        "test.skip(!inService || manager === undefined, SERVICE_ONLY);",
        "test.skip(browserName === 'webkit', 'x');",
        "test.fixme(cond, 'x');",
        "test.fixme(\n    !inService || x,\n    'x',\n  );",
    ],
)
def test_any_other_skip_in_the_body_makes_the_test_not_executed(call: str) -> None:
    source = f'test("a [WF-QUA-0050-A]", async () => {{\n  {call}\n}});\n'
    assert runs(source) == {"WF-QUA-0050-A": False}


@pytest.mark.story("US-2440")
def test_a_test_with_both_forms_is_not_executed() -> None:
    source = """\
test("a [WF-QUA-0050-A]", async () => {
  test.skip(inService, "x");
  test.skip(!inService || manager === undefined, "y");
});
"""
    assert runs(source) == {"WF-QUA-0050-A": False}


@pytest.mark.story("US-2440")
def test_a_skip_stops_its_own_test_only() -> None:
    source = """\
test("a [WF-QUA-0050-A]", async () => { test.skip(true, "x"); });
test("b [WF-QUA-0060-A]", async () => {});
"""
    assert runs(source) == {"WF-QUA-0050-A": False, "WF-QUA-0060-A": True}


@pytest.mark.story("US-2440")
def test_a_skip_in_a_group_outside_any_test_stops_the_tests_of_the_group() -> None:
    source = """\
test.describe("in", () => {
  test.beforeEach(() => { test.skip(true, "x"); });
  test("a [WF-QUA-0050-A]", async () => {});
});
test.describe("out", () => {
  test("b [WF-QUA-0060-A]", async () => {});
});
"""
    assert runs(source) == {"WF-QUA-0050-A": False, "WF-QUA-0060-A": True}


@pytest.mark.story("US-2440")
def test_a_skip_in_an_outer_group_stops_the_tests_of_an_inner_group_without_skip() -> None:
    source = """\
test.describe("outer", () => {
  test.beforeEach(() => { test.skip(true, "x"); });
  test.describe("inner", () => {
    test("a [WF-QUA-0050-A]", async () => {});
  });
});
test.describe("other", () => {
  test("b [WF-QUA-0060-A]", async () => {});
});
"""
    assert runs(source) == {"WF-QUA-0050-A": False, "WF-QUA-0060-A": True}


@pytest.mark.story("US-2440")
def test_the_platform_skip_in_a_group_hook_does_not_stop_the_tests_of_the_group() -> None:
    source = """\
test.describe("in", () => {
  test.beforeEach(() => { test.skip(!inService, SERVICE_ONLY); });
  test("a [WF-QUA-0050-A]", async () => {});
});
"""
    assert runs(source) == {"WF-QUA-0050-A": True}


@pytest.mark.story("US-2440")
def test_fail_and_the_declaration_of_a_skipped_test_read_as_before() -> None:
    source = """\
test("a [WF-QUA-0050-A]", async () => { test.fail(true, "x"); });
test.skip("b [WF-QUA-0060-A]", async () => {});
test("c [WF-QUA-0070-A]", async () => { test.skip(inService, "x"); });
"""
    assert runs(source) == {
        "WF-QUA-0050-A": True,
        "WF-QUA-0060-A": False,
        "WF-QUA-0070-A": True,
    }
