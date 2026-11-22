# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Find the states a process of the back writes after it started, in the sources (US-2850).

The control « ni mémoire » of WF-ARC-0080-A (``test_stateless_memory.py``) reads the sources with
``ast`` and asks this module for the states they hold. A *state written after the start* is one of
these, in a module of the package, written by the body of a function — which runs after the import
that started the process:

- a name of the module bound to a mutable container — a literal list, dict or set, a
  comprehension, a call of ``list``, ``dict``, ``set``, ``deque``, ``defaultdict``, ``OrderedDict``,
  ``Counter``, ``bytearray`` or of a class whose name ends with ``Registry`` — that a function
  changes: a method that changes it (``append``, ``add``, ``update``, ``pop``, ``clear``,
  ``register``…), an assignment or a deletion of one of its items, an augmented assignment; the
  function may be in another module that imports the name by ``from … import``;
- a name of the module that a function declares ``global`` and assigns;
- a function decorated with ``cache`` or ``lru_cache``, which keeps its answers;
- an attribute of a class of the module assigned through ``cls`` or the name of the class in a
  function, or a mutable container of the body of the class that a function changes through them;
- an instance of a class of the same module held by a name of the module (``X = M()``), when a
  method other than ``__init__`` assigns an attribute of ``self``: it keeps for the life of the
  process what it was given after the start (``ProcessTimeZone``).

``Counter`` is the one of ``collections``, whether it is imported by name or reached through the
module: the ``Counter`` of ``prometheus_client`` is a metric.

A name bound again in the function (a parameter, a local) is not the state. What it does not see:
an attribute of an instance that no name of the module holds (a service built at the start has its
attributes read from the settings or the database), an instance of a class of another module,
``os.environ[...] =``, ``setattr(module, …)``, an alias of import (``import x as m``), a container
returned by a factory of the package, a state reached by an alias or by ``getattr`` or held by a
library, and a ``ContextVar`` — which is sound, as it holds a value per context. The review reads
those.

A state is named ``path:name`` (``path:Class.attribute`` for a class), the path being that of the
module under ``waterfall``.
"""

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

CONTAINERS = {"list", "dict", "set", "deque", "defaultdict", "OrderedDict", "bytearray"}
CHANGERS = {
    "append",
    "extend",
    "insert",
    "add",
    "update",
    "pop",
    "popitem",
    "remove",
    "discard",
    "clear",
    "setdefault",
    "sort",
    "reverse",
    "register",
    "appendleft",
    "popleft",
    "extendleft",
    "rotate",
}
CACHES = {"cache", "lru_cache"}


def _module_of(path: str) -> str:
    parts = path.removesuffix(".py").split("/")
    return ".".join(["waterfall", *(parts[:-1] if parts[-1] == "__init__" else parts)])


def _called(node: ast.expr) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    function = node.func
    return function.id if isinstance(function, ast.Name) else getattr(function, "attr", None)


def _is_container(value: ast.expr | None, *, counter: bool = False) -> bool:
    if isinstance(value, ast.List | ast.Dict | ast.Set | ast.ListComp | ast.DictComp | ast.SetComp):
        return True
    called = _called(value) if value is not None else None
    if called is None:
        return False
    if called == "Counter":
        # Only ``collections.Counter``: ``counter`` says the module imports it by name.
        function = value.func if isinstance(value, ast.Call) else None
        return counter if isinstance(function, ast.Name) else _through_collections(function)
    return called in CONTAINERS or called.endswith("Registry")


def _through_collections(function: ast.expr | None) -> bool:
    return (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "collections"
    )


def _target_names(statement: ast.stmt) -> list[tuple[str, ast.expr | None]]:
    if isinstance(statement, ast.Assign):
        return [(t.id, statement.value) for t in statement.targets if isinstance(t, ast.Name)]
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return [(statement.target.id, statement.value)]
    return []


@dataclass(frozen=True)
class Module:
    """What one module holds that a function can change, and how its names are imported."""

    path: str
    tree: ast.Module
    containers: frozenset[str]
    imports: Mapping[str, tuple[str, str]]
    classes: Mapping[str, frozenset[str]]


def _imports(tree: ast.Module, path: str) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    package = _module_of(path).split(".")
    if not path.endswith("__init__.py"):
        package = package[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or node.level):
            base = package[: len(package) - node.level + 1] if node.level else []
            source = ".".join([*base, *([node.module] if node.module else [])])
            for alias in node.names:
                found[alias.asname or alias.name] = (source, alias.name)
    return found


def _module(path: str, source: str) -> Module:
    tree = ast.parse(source)
    imports = _imports(tree, path)
    counter = imports.get("Counter") == ("collections", "Counter")
    containers = {
        name
        for statement in tree.body
        for name, value in _target_names(statement)
        if _is_container(value, counter=counter)
    }
    classes = {
        node.name: frozenset(
            name
            for statement in node.body
            for name, value in _target_names(statement)
            if _is_container(value, counter=counter)
        )
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }
    return Module(path, tree, frozenset(containers), imports, classes)


def _functions(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node


def _bound(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Give the names a function binds itself: parameters, assignments, loops, ``with``."""
    arguments = function.args
    names = {a.arg for a in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]}
    names |= {a.arg for a in (arguments.vararg, arguments.kwarg) if a is not None}
    for node in ast.walk(function):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
    declared = {
        n for node in ast.walk(function) if isinstance(node, ast.Global) for n in node.names
    }
    return names - declared


def _changed(function: ast.FunctionDef | ast.AsyncFunctionDef) -> Iterator[ast.expr]:
    """Give each expression that a function changes: the object of a changer, an item, a name."""
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in CHANGERS
        ):
            yield node.func.value
        elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store | ast.Del):
            yield node.value
        elif isinstance(node, ast.AugAssign):
            yield node.target


def _dotted(node: ast.expr) -> tuple[str, str] | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id, node.attr
    return None


def states(sources: Mapping[str, str]) -> set[str]:
    """Give the states the sources write after the start, each as ``path:name``.

    ``sources`` maps the path of a module under ``waterfall`` to its text.
    """
    modules = {path: _module(path, text) for path, text in sources.items()}
    by_name = {_module_of(path): module for path, module in modules.items()}
    found: set[str] = set()
    for module in modules.values():
        found |= _found_in(module, by_name)
    return found


def _found_in(module: Module, by_name: Mapping[str, Module]) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(module.tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and any(
            _called_decorator(decorator) in CACHES for decorator in node.decorator_list
        ):
            found.add(f"{module.path}:{node.name}")
    for function in _functions(module.tree):
        bound = _bound(function)
        for node in ast.walk(function):
            if isinstance(node, ast.Global):
                assigned = {
                    n.id
                    for n in ast.walk(function)
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
                }
                found |= {f"{module.path}:{name}" for name in node.names if name in assigned}
        for target in _changed(function):
            found |= _state_of(module, by_name, target, bound)
        found |= _class_attributes(module, function)
    return found | _instances(module)


def _instances(module: Module) -> set[str]:
    """Give the names of the module that hold an instance of a class of it that writes itself."""
    writers = {
        node.name
        for node in module.tree.body
        if isinstance(node, ast.ClassDef) and _writes_itself(node)
    }
    return {
        f"{module.path}:{name}"
        for statement in module.tree.body
        for name, value in _target_names(statement)
        if isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in writers
    }


def _writes_itself(node: ast.ClassDef) -> bool:
    """Tell whether a method other than ``__init__`` assigns an attribute of ``self``."""
    for method in _functions(node):
        if method.name == "__init__":
            continue
        for inner in ast.walk(method):
            if isinstance(inner, ast.Assign | ast.AugAssign | ast.AnnAssign):
                targets = inner.targets if isinstance(inner, ast.Assign) else [inner.target]
                if any((_dotted(target) or ("", ""))[0] == "self" for target in targets):
                    return True
    return False


def _called_decorator(decorator: ast.expr) -> str | None:
    node = decorator.func if isinstance(decorator, ast.Call) else decorator
    return node.id if isinstance(node, ast.Name) else getattr(node, "attr", None)


def _state_of(
    module: Module, by_name: Mapping[str, Module], target: ast.expr, bound: set[str]
) -> set[str]:
    if isinstance(target, ast.Name) and target.id not in bound:
        if target.id in module.containers:
            return {f"{module.path}:{target.id}"}
        origin = module.imports.get(target.id)
        owner = by_name.get(origin[0]) if origin else None
        if origin and owner and origin[1] in owner.containers:
            return {f"{owner.path}:{origin[1]}"}
    dotted = _dotted(target)
    if dotted is not None and dotted[0] in module.classes:
        owner_class, attribute = dotted
        if attribute in module.classes[owner_class]:
            return {f"{module.path}:{owner_class}.{attribute}"}
    return set()


def _class_attributes(module: Module, function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Give the attributes of a class that a function assigns through ``cls`` or its name."""
    found: set[str] = set()
    owners = {
        method: node.name
        for node in module.tree.body
        if isinstance(node, ast.ClassDef)
        for method in _functions(node)
    }
    for node in ast.walk(function):
        if isinstance(node, ast.Assign | ast.AugAssign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                dotted = _dotted(target)
                if dotted is None:
                    continue
                holder, attribute = dotted
                name = module_class(module, holder, owners.get(function))
                if name is not None:
                    found.add(f"{module.path}:{name}.{attribute}")
    return found


def module_class(module: Module, holder: str, owner: str | None) -> str | None:
    """Give the class that ``holder`` stands for: its own name, or ``cls`` in its method."""
    if holder in module.classes:
        return holder
    return owner if holder == "cls" else None
