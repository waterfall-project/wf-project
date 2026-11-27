# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The guard of the writers of the journal of audit: who inscribes in it, and which actions.

A module of the service inscribes when it names one of the functions that write the journal,
by whichever form of import reaches it — ``from waterfall.platform.audit import record``,
``from waterfall.platform import audit`` then ``audit.record(...)``, an alias of either, a
relative import, ``import waterfall.platform.audit`` — and the actions it inscribes are the
literals it passes where those functions take the action: directly, through a conditional, through
a name bound in the function or typed ``Literal[...]`` by it. A name the module does not bind to
literals — a parameter typed by the whole enumeration, a tuple unpacked — is read as the actions
of the contract that the module spells out: the guard cannot follow a value across functions, and
reads what the module says of the contract.

It reads the source, never runs it: a writer to come is seen as these are (#932).
"""

import ast
from dataclasses import dataclass
from pathlib import Path

import yaml

CONTRACT_SCHEMAS = Path(__file__).resolve().parents[2] / "docs" / "api" / "components" / "schemas"
# Where each function that writes the journal takes the action, by position and by name; ``None``
# for the ones that take an inscription, whose action its own construction says.
ACTION_OF: dict[str, tuple[int, str] | None] = {
    "waterfall.platform.audit.Inscription": (0, "action"),
    "waterfall.platform.audit.record": None,
    "waterfall.platform.audit.record_all": None,
    "waterfall.core.users.identity.inscribe": (1, "action"),
    "waterfall.core.revisions.interface.shared.inscribe_revision": (2, "action"),
}
LITERAL = "typing.Literal"


@dataclass(frozen=True, slots=True)
class Writer:
    """What a module inscribes: its actions, and whether it spells them or the guard reads them."""

    actions: frozenset[str]
    is_unresolved: bool


def contract_actions() -> frozenset[str]:
    """Read the actions of the journal in the contract: the enumeration of ``AuditAction``."""
    text = (CONTRACT_SCHEMAS / "audit.yaml").read_text(encoding="utf-8")
    return frozenset(yaml.safe_load(text)["AuditAction"]["enum"])


def module_name(path: Path, root: Path) -> str:
    """Give the dotted name of a source file, the package's for its ``__init__``."""
    parts = path.relative_to(root.parent).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def bindings_of(tree: ast.Module, module: str, *, is_package: bool) -> dict[str, str]:
    """Give, for each name a module imports or defines, the dotted name it stands for."""
    package = module if is_package else module.rpartition(".")[0]
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound[alias.asname or alias.name.partition(".")[0]] = (
                    alias.name if alias.asname else alias.name.partition(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            base = ".".join(package.split(".")[: len(package.split(".")) - node.level + 1])
            origin = ".".join(part for part in (base if node.level else "", node.module) if part)
            for alias in node.names:
                bound[alias.asname or alias.name] = f"{origin}.{alias.name}"
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            bound[node.name] = f"{module}.{node.name}"
    return bound


def dotted(expression: ast.expr, bound: dict[str, str]) -> str | None:
    """Give the dotted name an expression of names and attributes stands for, by the imports."""
    if isinstance(expression, ast.Name):
        return bound.get(expression.id)
    if isinstance(expression, ast.Attribute):
        owner = dotted(expression.value, bound)
        return None if owner is None else f"{owner}.{expression.attr}"
    return None


def literal_members(annotation: ast.expr | None, bound: dict[str, str]) -> set[str] | None:
    """Give the strings a ``Literal[...]`` annotation admits, ``None`` for any other annotation."""
    if not isinstance(annotation, ast.Subscript) or dotted(annotation.value, bound) != LITERAL:
        return None
    chosen = annotation.slice
    members = chosen.elts if isinstance(chosen, ast.Tuple) else [chosen]
    return {
        each.value
        for each in members
        if isinstance(each, ast.Constant) and isinstance(each.value, str)
    }


def resolved(
    expression: ast.expr, scope: ast.FunctionDef | None, bound: dict[str, str]
) -> set[str] | None:
    """Give the literals an action expression can be, ``None`` where the module does not say."""
    if isinstance(expression, ast.Constant):
        return {expression.value} if isinstance(expression.value, str) else None
    if isinstance(expression, ast.IfExp):
        both = (resolved(expression.body, scope, bound), resolved(expression.orelse, scope, bound))
        return None if None in both else (both[0] or set()) | (both[1] or set())
    if not isinstance(expression, ast.Name) or scope is None:
        return None
    found: set[str] = set()
    for argument in scope.args.args + scope.args.kwonlyargs:
        if argument.arg == expression.id:
            members = literal_members(argument.annotation, bound)
            if members is None:
                return None
            found |= members
    for node in ast.walk(scope):
        if not isinstance(node, ast.Assign | ast.AnnAssign) or node.value is None:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(each, ast.Name) and each.id == expression.id for each in targets):
            continue
        assigned = resolved(node.value, scope, bound)
        if assigned is None:
            return None
        found |= assigned
    return found or None


def enclosing_functions(tree: ast.Module) -> dict[ast.AST, ast.FunctionDef]:
    """Map each node to the innermost function that holds it."""
    holder: dict[ast.AST, ast.FunctionDef] = {}
    for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
        for node in ast.walk(function):
            holder[node] = function
    return holder


def action_argument(call: ast.Call, where: tuple[int, str]) -> ast.expr | None:
    """Give the expression a call passes as the action, by its position or its name."""
    position, name = where
    if len(call.args) > position and not isinstance(call.args[position], ast.Starred):
        return call.args[position]
    return next((each.value for each in call.keywords if each.arg == name), None)


def inscriptions_of(
    source: str, module: str, contract: frozenset[str], *, is_package: bool = False
) -> Writer | None:
    """Read what a module inscribes, ``None`` if it names no function that writes the journal."""
    tree = ast.parse(source)
    bound = bindings_of(tree, module, is_package=is_package)
    # What the module reaches by an import, or calls — its own definition of one is no use of it.
    reached = any(
        isinstance(node, ast.Name | ast.Attribute)
        and (target := dotted(node, bound)) in ACTION_OF
        and target.rpartition(".")[0] != module
        for node in ast.walk(tree)
    )
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and dotted(node.func, bound) in ACTION_OF
    ]
    if not reached and not calls:
        return None
    holder = enclosing_functions(tree)
    actions: set[str] = set()
    is_unresolved = False
    for call in calls:
        where = ACTION_OF[dotted(call.func, bound) or ""]
        expression = None if where is None else action_argument(call, where)
        if expression is None:
            continue
        literals = resolved(expression, holder.get(call), bound)
        if literals is None:
            is_unresolved = True
        else:
            actions |= literals
    if is_unresolved:
        actions |= spelled(tree) & contract
    return Writer(frozenset(actions), is_unresolved)


def spelled(tree: ast.Module) -> set[str]:
    """Give every string a module writes as a literal."""
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def writers_of(root: Path, contract: frozenset[str]) -> dict[str, Writer]:
    """Read every module of the service under ``root``: the ones that inscribe, and what."""
    found: dict[str, Writer] = {}
    for path in sorted(root.rglob("*.py")):
        name = module_name(path, root)
        read = inscriptions_of(
            path.read_text(encoding="utf-8"),
            name,
            contract,
            is_package=path.name == "__init__.py",
        )
        if read is not None:
            found[name] = read
    return found
