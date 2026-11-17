# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Read the titles of the tests of a TypeScript file, and whether each test runs (US-2440).

The coverage of the requirements reads the citations of a TypeScript test in its title alone
(``wftools.coverage``): this module finds the titles without running the file. It reads the
source as tokens — names, punctuation, strings —, leaving out the comments, the regular
expressions and the text of JSX, so that neither a comment nor an apostrophe in a paragraph is
taken for a title; then it finds the calls of Vitest and Playwright that declare a test or a group
of tests: ``it(``, ``test(``, ``describe(``, ``test.describe(``, with their variants (``.each``,
``.only``, ``.skip``…).

A test declared ``.skip``, ``.fixme`` or ``.todo``, or held by a group declared ``.skip`` or
``.fixme``, does not run. A group runs if one of its tests runs. A call of ``test.skip`` or
``test.fixme`` whose first argument is no title is a skip that the test, or the group, decides as
it runs, and it is attached to the test that holds it (to the group, failing a test). Its first
argument exactly ``inService`` or ``!inService`` is the platform skip of the end-to-end paths,
which the report reads as run; any other argument (``true``, a compound condition…) makes the test
not run, and so does a test that carries both forms. ``it.skipIf`` and ``it.runIf`` are not seen:
the test counts as run, as with ``test.fail(condition)``, an annotation of Playwright, which is no
test.

A call on ``it``, ``test`` or ``describe`` that this module knows neither as a declaration nor as
something that declares nothing (``test.use``, ``test.step``…) is not skipped over:
the reading fails (``UnreadableError``), naming the file and the line, so that a form of
declaration it does not read is never lost without a word. It fails only in a file that imports
``it``, ``test`` or ``describe`` (Vitest, Playwright, the fixtures of the front): elsewhere the name
is a variable, which only the file knows the members of.
"""

import re
from dataclasses import dataclass

_HEADS = frozenset({"it", "test", "describe"})
_NOT_RUN = frozenset({"skip", "fixme", "todo"})
_VARIANTS = frozenset(
    {
        "each",
        "for",
        "only",
        "concurrent",
        "sequential",
        "shuffle",
        "fails",
        "fail",
        "skipIf",
        "runIf",
    }
    | _NOT_RUN
)
_GROUPING = frozenset({"describe", "serial", "parallel"})
"""What a group adds: ``test.describe``, and the ``.serial`` and ``.parallel`` modes."""
_CALLED = frozenset({"each", "for", "skipIf", "runIf"})
"""The variants called before the title is: ``it.each(table)("title", …)``, ``it.skipIf(c)(…)``."""
_ANNOTATIONS = frozenset({"skip", "fixme", "fail"})
"""The members that, called with no title, annotate the test they sit in."""
_DECLARING_NOTHING = frozenset(
    {"use", "beforeEach", "afterEach", "beforeAll", "afterAll", "step", "extend", "info", "slow"}
    | {"setTimeout", "configure", "expect", "scoped"}
)
"""The members of ``it``, ``test`` and ``describe`` that declare no test."""
_KEYWORDS = frozenset(
    {"return", "typeof", "case", "in", "of", "delete", "void", "throw", "new", "else", "do"}
    | {"yield", "await", "instanceof"}
)
_NAME = re.compile(r"[\w$]+")
_TAG = re.compile(r"[\w$.:-]*")
_GENERIC = re.compile(r"[\w$]+\s*(?:,|extends\b)")


@dataclass(frozen=True, slots=True)
class Token:
    """A token of the source, as written, and where it starts.

    Its kind is ``name``, ``string``, ``value`` — a number, a regular expression, an element — or
    ``punct``.
    """

    kind: str
    text: str
    start: int


class _Lexer:
    """Cut a TypeScript source into tokens, the text of JSX left out when ``jsx`` is set."""

    def __init__(self, source: str, *, jsx: bool) -> None:
        self.source = source
        self.jsx = jsx
        self.at = 0
        self.tokens: list[Token] = []

    def run(self) -> list[Token]:
        self._code(closing=False)
        return self.tokens

    def _push(self, kind: str, start: int) -> None:
        self.tokens.append(Token(kind, self.source[start : self.at], start))

    def _operand_expected(self) -> bool:
        """Tell whether a ``/`` or a ``<`` here opens a regular expression or an element."""
        if not self.tokens:
            return True
        last = self.tokens[-1]
        if last.kind == "punct":
            return last.text not in ")]}"
        return last.kind == "name" and last.text in _KEYWORDS

    def _code(self, *, closing: bool) -> None:
        """Read code to the end, or, ``closing``, past the brace that closes the one before it."""
        source, depth = self.source, 0
        while self.at < len(source):
            char, start = source[self.at], self.at
            if char.isspace():
                self.at += 1
            elif source.startswith("//", start):
                end = source.find("\n", start)
                self.at = len(source) if end < 0 else end
            elif source.startswith("/*", start):
                end = source.find("*/", start + 2)
                self.at = len(source) if end < 0 else end + 2
            elif char in "'\"":
                self._string(char)
                self._push("string", start)
            elif char == "`":
                self._template()
            elif char == "/" and self._operand_expected() and self._regex():
                self._push("value", start)
            elif char == "<" and self.jsx and self._operand_expected() and self._element_opens():
                self._element()
                self._push("value", start)
            elif char.isalnum() or char in "_$":
                match = _NAME.match(source, start)
                self.at = match.end() if match else start + 1
                self._push("value" if char.isdigit() else "name", start)
            else:
                if char == "{":
                    depth += 1
                elif char == "}":
                    if closing and depth == 0:
                        self.at += 1
                        return
                    depth -= 1
                self.at += 1
                self._push("punct", start)

    def _string(self, quote: str) -> None:
        """Pass a string between quotes, which ends at its quote or at the end of the line."""
        source = self.source
        self.at += 1
        while self.at < len(source) and source[self.at] not in (quote, "\n"):
            self.at += 2 if source[self.at] == "\\" else 1
        self.at += 1

    def _template(self) -> None:
        """Read a template literal: each of its texts a string, each ``${…}`` code."""
        source = self.source
        start = self.at
        self.at += 1
        while self.at < len(source):
            if source[self.at] == "\\":
                self.at += 2
            elif source[self.at] == "`":
                self.at += 1
                self._push("string", start)
                return
            elif source.startswith("${", self.at):
                self._push("string", start)
                self.at += 2
                # What follows ``${`` is an operand, as after an opening brace.
                self._push("punct", self.at - 2)
                self._code(closing=True)
                start = self.at
            else:
                self.at += 1
        self._push("string", start)

    def _regex(self) -> bool:
        """Pass a regular expression; tell whether one was there, on the line, to pass."""
        source, at, in_class = self.source, self.at + 1, False
        while at < len(source) and source[at] != "\n":
            char = source[at]
            if char == "\\":
                at += 1
            elif char == "[":
                in_class = True
            elif char == "]":
                in_class = False
            elif char == "/" and not in_class:
                match = _NAME.match(source, at + 1)
                self.at = match.end() if match else at + 1
                return True
            at += 1
        return False

    def _element_opens(self) -> bool:
        """Tell an element from the type parameters of an arrow (``<T extends …>``, ``<T,>``)."""
        following = self.source[self.at + 1 : self.at + 2]
        if following == ">":
            return True
        if not following.isalpha():
            return False
        return _GENERIC.match(self.source, self.at + 1) is None

    def _element(self) -> None:
        """Pass an element of JSX, its attributes and its children; read the code in braces."""
        source = self.source
        match = _TAG.match(source, self.at + 1)
        self.at = match.end() if match else self.at + 1
        while self.at < len(source):
            char = source[self.at]
            if source.startswith("/>", self.at):
                self.at += 2
                return
            if char == ">":
                self.at += 1
                self._children()
                return
            if char == "{":
                self.at += 1
                self._code(closing=True)
            elif char in "'\"":
                self._string(char)
            else:
                self.at += 1

    def _children(self) -> None:
        source = self.source
        while self.at < len(source):
            if source.startswith("</", self.at):
                end = source.find(">", self.at)
                self.at = len(source) if end < 0 else end + 1
                return
            if source[self.at] == "<":
                self._element()
            elif source[self.at] == "{":
                self.at += 1
                self._code(closing=True)
            else:
                self.at += 1


def tokens(source: str, *, jsx: bool) -> list[Token]:
    """Cut a TypeScript source into its tokens, comments and the text of JSX left out."""
    return _Lexer(source, jsx=jsx).run()


class UnreadableError(ValueError):
    """A call on ``it``, ``test`` or ``describe`` of a form not known, with its file and line."""

    def __init__(self, path: str, line: int, call: str, unknown: set[str]) -> None:
        super().__init__(
            f"{path}:{line}: {call}(…) is a call that is not known ({', '.join(sorted(unknown))}): "
            "teach wftools.titles to read it"
        )


@dataclass(frozen=True, slots=True)
class Title:
    """A call that declares a test or a group, and what it says of itself.

    ``strings`` are the strings of its title, ``span`` the tokens of its call, its body included.
    """

    strings: tuple[Token, ...]
    span: range
    group: bool
    not_run: bool


def _closing(found: list[Token]) -> dict[int, int]:
    """Return, for each opening parenthesis, the index of the one that closes it."""
    pairs: dict[int, int] = {}
    opened: list[int] = []
    for index, token in enumerate(found):
        if token.text == "(":
            opened.append(index)
        elif token.text == ")" and opened:
            pairs[opened.pop()] = index
    return pairs


def _first_argument(found: list[Token], opening: int, closing: int) -> list[Token]:
    """Return the tokens of the first argument of the call between these parentheses."""
    depth = 0
    for index in range(opening + 1, closing):
        text = found[index].text
        if text in "([{" and found[index].kind == "punct":
            depth += 1
        elif text in ")]}" and found[index].kind == "punct":
            depth -= 1
        elif text == "," and depth == 0:
            return found[opening + 1 : index]
    return found[opening + 1 : closing]


def _past_type_arguments(found: list[Token], at: int) -> int:
    """Return the index past the type arguments that open here (``it.each<T>(``), if any."""
    if at >= len(found) or found[at].text != "<":
        return at
    depth = 0
    for index in range(at, len(found)):
        text = found[index].text
        if text == "<":
            depth += 1
        elif text == ">" and found[index - 1].text != "=":
            depth -= 1
            if depth == 0:
                return index + 1
    return at


def _called(
    found: list[Token], pairs: dict[int, int], at: int, member: str
) -> tuple[int, list[Token]] | None:
    """Read what a member called before the title is — ``each``, ``skipIf`` — takes.

    Return the index past it and, for a table (``each``, ``for``), its tokens: the title is formed
    from each row, so a citation in a row is in the title. The table is an array, or a template
    literal tagged by the member (``it.each`a|b`(…)``); a condition (``skipIf``) is no title.
    """
    at = _past_type_arguments(found, at)
    if at >= len(found):
        return None
    table = member in {"each", "for"}
    if found[at].text == "(" and at in pairs:
        return pairs[at] + 1, found[at + 1 : pairs[at]] if table else []
    if table and found[at].kind == "string" and found[at].text.startswith("`"):
        end = next((i for i in range(at, len(found)) if _ends_template(found[i])), None)
        if end is not None:
            return end + 1, found[at : end + 1]
    return None


def _ends_template(token: Token) -> bool:
    """Tell whether this token is the last text of a template literal."""
    return token.kind == "string" and token.text.endswith("`")


def _imports_heads(found: list[Token]) -> bool:
    """Tell whether the file imports ``it``, ``test`` or ``describe``, the names it declares by.

    A file that does not — ``const it = list.values()`` — owns a variable of that name, whose
    members are none of the test runner's to know.
    """
    for index, token in enumerate(found):
        if token.kind == "name" and token.text == "import":
            for clause in found[index + 1 :]:
                if clause.kind == "string" or clause.text == ";":
                    break
                if clause.kind == "name" and clause.text in _HEADS:
                    return True
    return False


def _declaration(
    found: list[Token], pairs: dict[int, int], index: int, source: str, path: str
) -> Title | None:
    """Read the call that starts at this token, if it declares a test or a group."""
    if found[index].text not in _HEADS or (index and found[index - 1].text == "."):
        return None
    members: list[str] = []
    table: list[Token] = []
    at = index + 1
    while at + 1 < len(found) and found[at].text == "." and found[at + 1].kind == "name":
        member = found[at + 1].text
        members.append(member)
        at += 2
        if member in _CALLED:
            read = _called(found, pairs, at, member)
            if read is None:
                return None
            at, rows = read
            table += rows
    at = _past_type_arguments(found, at)
    if at >= len(found) or found[at].text != "(" or at not in pairs:
        return None
    if _DECLARING_NOTHING & set(members):
        return None
    group = found[index].text == "describe" or "describe" in members
    if unknown := set(members) - _VARIANTS - (_GROUPING if group else set()):
        line = source.count("\n", 0, found[index].start) + 1
        call = ".".join([found[index].text, *members])
        raise UnreadableError(path, line, call, unknown)
    first = _first_argument(found, at, pairs[at])
    # A skip or a failure whose first argument is no title is no test: it annotates the test it
    # sits in, which decides as it runs whether it is skipped.
    if not group and _ANNOTATIONS & set(members) and not (first and first[0].kind == "string"):
        return None
    strings = tuple(token for token in [*table, *first] if token.kind == "string")
    return Title(strings, range(index, pairs[at] + 1), group, bool(_NOT_RUN & set(members)))


def _skips_in_body(found: list[Token], pairs: dict[int, int]) -> list[tuple[int, bool]]:
    """Return each ``test.skip(…)``/``test.fixme(…)`` with no title.

    Each comes with its index and whether it leaves the test run: ``inService`` and ``!inService``
    do, any other first argument does not.
    """
    skips: list[tuple[int, bool]] = []
    for index, token in enumerate(found):
        if token.text not in {"it", "test"} or (index and found[index - 1].text == "."):
            continue
        at = index + 3
        if not (
            at < len(found)
            and found[index + 1].text == "."
            and found[index + 2].text in {"skip", "fixme"}
            and found[at].text == "("
            and at in pairs
        ):
            continue
        first = _first_argument(found, at, pairs[at])
        if first and first[0].kind == "string":
            continue
        skips.append((index, tuple(t.text for t in first) in {("inService",), ("!", "inService")}))
    return skips


def declarations(source: str, *, jsx: bool, path: str = "") -> list[tuple[Title, bool]]:
    """Return the tests and the groups of a file, each with whether it runs.

    A call on ``it``, ``test`` or ``describe`` of an unknown form fails, naming ``path`` and line.
    """
    found = tokens(source, jsx=jsx)
    pairs = _closing(found)
    imported = _imports_heads(found)

    def read(index: int) -> Title | None:
        try:
            return _declaration(found, pairs, index, source, path)
        except UnreadableError:
            if imported:
                raise
            return None

    titles = [title for index in range(len(found)) if (title := read(index))]
    groups = [title for title in titles if title.group]

    def held(title: Title) -> bool:
        """Tell whether a group that holds the title does not run, by its declaration."""
        return any(
            group.not_run and group is not title and title.span.start in group.span
            for group in groups
        )

    # A skip decided in a body belongs to the innermost test that holds it, else to the innermost
    # group; only one that is not the platform skip stops the test, or the tests of the group.
    stopped: set[int] = set()
    for index, platform in _skips_in_body(found, pairs):
        if platform:
            continue
        around = [title for title in titles if index in title.span]
        owner = min(
            (title for title in around if not title.group),
            key=lambda title: len(title.span),
            default=None,
        ) or min(around, key=lambda title: len(title.span), default=None)
        if owner is not None:
            stopped.add(id(owner))

    def group_stops(title: Title) -> bool:
        return any(
            id(group) in stopped and group is not title and title.span.start in group.span
            for group in groups
        )

    tests = {
        id(title): not title.not_run
        and id(title) not in stopped
        and not held(title)
        and not group_stops(title)
        for title in titles
        if not title.group
    }

    def runs(title: Title) -> bool:
        if not title.group:
            return tests[id(title)]
        return any(
            tests[id(test)] for test in titles if not test.group and test.span.start in title.span
        )

    return [(title, runs(title)) for title in titles]
