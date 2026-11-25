# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""No answer of the back depends on a state its process keeps in memory (US-2850).

The pendant of ``test_stateless_files.py`` for memory (#4352). WF-ARC-0080-A holds that no state of
a process changes the answer to a request, so that any instance answers as another does and a
rolling update runs two versions side by side. This control reads the sources of the back
(``memory_states.py`` says what it counts as *a state written after the start*: a module container a
function changes, a name a function declares ``global`` and assigns, a ``cache``, an attribute of a
class) and requires each state to be declared below, with the reason it changes no answer. A state
that is not declared — a new registry, a new cache — fails here until it is; a declaration that
matches no state any more fails too, so that the list stays exact.
"""

from pathlib import Path

import pytest
from memory_states import states

SOURCE = Path(__file__).resolve().parents[1] / "src" / "waterfall"

pytestmark = [pytest.mark.requirement("WF-ARC-0080-A"), pytest.mark.story("US-2850")]

REGISTRY = (
    "filled when its module is imported, by the interface of the module above, and the same in "
    "every process of a version: a request registers nothing"
)

# Every state the back writes after it started, and why no answer depends on it.
DECLARED = {
    "core/cost_settings/employment.py:_EMPLOYMENTS": REGISTRY,
    "core/estimate/interface/remaining_indicators.py:_COVERAGE": REGISTRY,
    "core/history/interface/undoable.py:_UNDOABLE": REGISTRY,
    "core/estimate/reading.py:_editable": "a pure function of its arguments, which it keeps the "
    "answers of: it gives the same answer cached or not",
    "core/exchanges/interface/exports.py:_EXPORTERS": REGISTRY,
    "core/exchanges/interface/imports.py:_FORMATS": REGISTRY,
    "core/exchanges/unchanged.py:_GUARDS": REGISTRY,
    "core/planning/interface/facets.py:_FACETS": REGISTRY,
    "core/planning/interface/open_lines.py:_OPEN_LINES": REGISTRY,
    "core/planning/interface/open_lines.py:_ZEROED_AT": REGISTRY,
    "core/planning/interface/physical_progress.py:_PHYSICAL_PROGRESS": REGISTRY,
    "core/planning/provisioning.py:_OWNERS": REGISTRY,
    "core/planning/task_tree_image.py:_font_bytes": "the bytes of a font file of the package, "
    "read-only: they are the same in every process of a version",
    "core/projects/interface/attachments.py:_ATTACHMENTS": REGISTRY,
    "core/projects/interface/estimate_facts.py:_FACTS": REGISTRY,
    "core/projects/interface/skeleton.py:_OPENING_MAIN": REGISTRY,
    "core/projects/interface/risk_designations.py:_DESIGNATIONS": REGISTRY,
    "core/projects/interface/subprojects.py:_COSTS": REGISTRY,
    "core/resource_settings/interface/extensions.py:_GUARDS": REGISTRY,
    "core/resource_settings/interface/extensions.py:_RECALCULATIONS": REGISTRY,
    "core/revisions/interface/closing.py:_CLOSINGS": REGISTRY,
    "core/revisions/interface/marking.py:_INDICATORS": REGISTRY,
    "core/revisions/interface/marking.py:_MARKINGS": REGISTRY,
    "core/revisions/interface/merging.py:_ENDS": REGISTRY,
    "core/revisions/interface/merging.py:_MERGES": REGISTRY,
    "core/revisions/interface/rates.py:_PROPOSALS": REGISTRY,
    "core/revisions/interface/rebasing.py:_ENDS": REGISTRY,
    "core/revisions/interface/rebasing.py:_REBASES": REGISTRY,
    "core/revisions/interface/reference.py:_DESIGNATIONS": REGISTRY,
    "core/revisions/interface/reference.py:_MAIN_TASK": REGISTRY,
    "core/revisions/interface/reference.py:_TASKS_AND_LINES": REGISTRY,
    "core/revisions/interface/revisions.py:_COPIES": REGISTRY,
    "core/revisions/interface/structures.py:_OWN_ESTIMATES": REGISTRY,
    "platform/cache.py:_reported": "the causes already logged, to write one record per cause: it "
    "changes the logs, and a read of the cache that fails is answered as a miss, whoever logged",
    "platform/registry.py:_REGISTRIES": "the registries by name, listed for the tests of the "
    "processes: added to when a registry is created at an import, and read by no request",
    "platform/settings.py:_time_zones": "the names of the IANA database, read once from the "
    "system: the same in every process of an image",
    "platform/installation.py:TIME_ZONE": "the time zone of the installation, read once from the "
    "database by the first request that needs it and kept: the bootstrap fixes it and nothing "
    "changes it. Its limit: a restoration replaces the database without restarting the processes "
    "(#4695), so a process that has read the zone keeps it after the restoration of a backup of an "
    "installation in another time zone, until it restarts",
    "witness/revisions.py:_FILLERS": REGISTRY,
}
FAKE = "fake/module.py"


def sources() -> dict[str, str]:
    """Read every module of the back, by its path under the package."""
    return {
        str(path.relative_to(SOURCE)): path.read_text(encoding="utf-8")
        for path in sorted(SOURCE.rglob("*.py"))
    }


def test_every_state_written_after_the_start_is_declared_without_effect_on_an_answer() -> None:
    # « Aucun état en mémoire d'un processus ne change la réponse d'une requête » (US-2850) :
    # what the sources write after the start is what the list declares, no more and no less.
    found = states(sources())
    assert sorted(found - DECLARED.keys()) == [], "a state written after the start is not declared"
    assert sorted(DECLARED.keys() - found) == [], "a declaration matches no state any more"
    assert all(len(reason) > 30 for reason in DECLARED.values())


def test_a_state_that_is_not_declared_fails_the_control() -> None:
    # The control is tried on sources it did not meet: a registry filled by a function, which no
    # declaration names, is found.
    fake = {FAKE: "_SEEN = {}\n\ndef remember(key):\n    _SEEN[key] = True\n"}
    assert states(fake) == {f"{FAKE}:_SEEN"}
    assert states({**sources(), **fake}) - DECLARED.keys() == {f"{FAKE}:_SEEN"}


def test_a_declaration_that_matches_no_state_fails_the_control() -> None:
    # A state removed from the sources and left in the list: the list is no longer exact.
    declared = {**DECLARED, "platform/cache.py:_gone": "a state that was removed from the sources"}
    assert declared.keys() - states(sources()) == {"platform/cache.py:_gone"}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("_SEEN: list[int] = []\ndef add(x):\n    _SEEN.append(x)\n", {"_SEEN"}),
        ("_SEEN = {}\ndef drop(k):\n    del _SEEN[k]\n", {"_SEEN"}),
        (
            "_REGISTRY = Registry('a')\ndef on(x):\n    return _REGISTRY.register(x)\n",
            {"_REGISTRY"},
        ),
        (
            "_client = None\ndef open_it():\n    global _client\n    _client = object()\n",
            {"_client"},
        ),
        ("from functools import cache\n@cache\ndef zones():\n    return 1\n", {"zones"}),
        ("import functools\n@functools.lru_cache(maxsize=4)\ndef f(x):\n    return x\n", {"f"}),
        (
            "class A:\n    seen = []\n    @classmethod\n    def on(cls):\n        cls.latest = 1\n",
            {"A.latest"},
        ),
        ("class A:\n    seen = []\ndef on(x):\n    A.seen.append(x)\n", {"A.seen"}),
        (
            (
                "class M:\n def __init__(self):\n  self._v = None\n"
                " def get(self):\n  self._v = 1\nX = M()\n"
            ),
            {"X"},
        ),
        ("from collections import deque\n_Q = deque()\ndef take():\n    _Q.popleft()\n", {"_Q"}),
        ("import collections\n_N = collections.Counter()\ndef on(k):\n    _N.update(k)\n", {"_N"}),
        ("from collections import Counter\n_N = Counter()\ndef on(k):\n    _N.update(k)\n", {"_N"}),
    ],
    ids=[
        "list",
        "deletion",
        "registry",
        "global",
        "cache",
        "lru_cache",
        "cls",
        "class-container",
        "instance-written-after-init",
        "popleft",
        "collections-counter",
        "counter-by-name",
    ],
)
def test_the_control_sees_each_form_of_state_it_counts(source: str, expected: set[str]) -> None:
    assert states({FAKE: source}) == {f"{FAKE}:{name}" for name in expected}


@pytest.mark.parametrize(
    "source",
    [
        "_NAMES = ['a']\ndef read():\n    return list(_NAMES)\n",
        "_NAMES = []\ndef build():\n    _NAMES = []\n    _NAMES.append(1)\n    return _NAMES\n",
        "def build(seen):\n    seen.append(1)\n    return seen\n",
        "class M:\n def __init__(self):\n  self._v = None\nX = M()\n",
        "from prometheus_client import Counter\n_N = Counter('a')\ndef on():\n    _N.update(1)\n",
        "LIMIT = 3\ndef read():\n    return LIMIT\n",
    ],
    ids=["read-only", "shadowed", "parameter", "init-only-instance", "metric-counter", "constant"],
)
def test_the_control_ignores_what_a_function_only_reads_or_builds_locally(source: str) -> None:
    assert states({FAKE: source}) == set()


def test_a_state_changed_from_another_module_that_imports_it_is_the_state_of_its_owner() -> None:
    owner = "fake/owner.py"
    user = "fake/user.py"
    found = states(
        {
            owner: "_SEEN = []\n",
            user: "from waterfall.fake.owner import _SEEN\ndef add(x):\n    _SEEN.append(x)\n",
        }
    )
    assert found == {f"{owner}:_SEEN"}
