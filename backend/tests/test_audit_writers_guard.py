# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The guard of the writers of the journal sees every form of call, on small sources (#932).

``test_audit_params.py`` compares the modules that inscribe, and the actions they inscribe, to the
ones the tests try and to the contract. A guard that missed a form of import would let a writer
through unseen: each form is read here on a source of a few lines, and the actions of each.
"""

import pytest
from audit_writers import Writer, contract_actions, inscriptions_of

pytestmark = pytest.mark.story("US-2980")

CONTRACT = frozenset({"user_create", "user_update", "backup", "restore", "project_create"})
MODULE = "waterfall.core.example"


def read(source: str, module: str = MODULE, *, is_package: bool = False) -> Writer | None:
    """Read a source as a module of the service, against a small contract."""
    return inscriptions_of(source, module, CONTRACT, is_package=is_package)


@pytest.mark.parametrize(
    "lines",
    [
        (
            "from waterfall.platform.audit import record, Inscription",
            "def f(s): record(s, Inscription('backup', 1, 2, 3))",
        ),
        (
            "from waterfall.platform import audit",
            "def f(s): audit.record(s, audit.Inscription('backup', 1, 2, 3))",
        ),
        (
            "from waterfall.platform import audit as journal",
            "def f(s): journal.record(s, journal.Inscription('backup', 1, 2, 3))",
        ),
        (
            "from waterfall.platform.audit import record as write, Inscription as Entry",
            "def f(s): write(s, Entry('backup', 1, 2, 3))",
        ),
        (
            "import waterfall.platform.audit",
            "def f(s):",
            "    entry = waterfall.platform.audit.Inscription('backup')",
            "    waterfall.platform.audit.record(s, entry)",
        ),
        (
            "import waterfall.platform.audit as journal",
            "def f(s): journal.record(s, journal.Inscription('backup', 1, 2, 3))",
        ),
        (
            "from waterfall.platform.audit import record_all, Inscription",
            "def f(s): record_all(s, [Inscription('backup', 1, 2, 3)])",
        ),
    ],
    ids=["from", "module", "module-alias", "name-alias", "dotted", "dotted-alias", "all"],
)
def test_a_writer_is_seen_by_each_form_of_import_and_its_action_read(
    lines: tuple[str, ...],
) -> None:
    assert read("\n".join(lines)) == Writer(frozenset({"backup"}), is_unresolved=False)


def test_a_relative_import_of_the_journal_is_a_writer_too() -> None:
    sibling = "from .audit import Inscription, record\nrecord(1, Inscription('restore'))\n"
    assert read(sibling, "waterfall.platform.restoration") == Writer(
        frozenset({"restore"}), is_unresolved=False
    )
    parent = "from ..audit import Inscription\ndef f(): return Inscription('restore')\n"
    assert read(parent, "waterfall.platform.sub.deeper") == Writer(
        frozenset({"restore"}), is_unresolved=False
    )
    package = "from .audit import Inscription\ndef f(): return Inscription('backup')\n"
    assert read(package, "waterfall.platform", is_package=True) == Writer(
        frozenset({"backup"}), is_unresolved=False
    )


def test_the_inscription_of_the_accounts_takes_its_action_second_and_by_name() -> None:
    source = (
        "from waterfall.core.users.identity import inscribe\n"
        "def f(s, account, act):\n"
        "    inscribe(s, 'user_create', account, act, {})\n"
        "    inscribe(s, action='user_update', account=account, act=act, params={})\n"
    )
    assert read(source) == Writer(frozenset({"user_create", "user_update"}), is_unresolved=False)


def test_a_module_that_names_no_writer_of_the_journal_is_no_writer() -> None:
    own = (
        "from waterfall.platform.audit import AuditEntry\n"
        "def record(session): return 'backup'\n"
        "def f(s): return record(s)\n"
    )
    assert read(own) is None
    assert read("import waterfall.platform.audit\nBACKUP = 'backup'\n") is None


def test_the_module_that_defines_a_writer_reads_its_own_calls_of_it() -> None:
    # The definition is no use of the writer; its own call, by name, is one.
    defined = "def inscribe(s, action, account, act, params): ...\ninscribe(1, 'backup', 2, 3, 4)\n"
    assert read(defined, "waterfall.core.users.identity") == Writer(
        frozenset({"backup"}), is_unresolved=False
    )
    assert read(defined.splitlines()[0], "waterfall.core.users.identity") is None


def test_an_action_is_read_through_a_conditional_a_binding_and_a_literal_annotation() -> None:
    source = (
        "from typing import Literal\n"
        "from waterfall.platform.audit import Inscription\n"
        "def conditional(on):\n"
        "    return Inscription('user_create' if on else 'user_update')\n"
        "def bound(on):\n"
        "    action = 'backup' if on else 'restore'\n"
        "    return Inscription(action)\n"
        "def annotated(action: Literal['project_create', 'backup']):\n"
        "    return Inscription(action)\n"
        "def keyword():\n"
        "    return Inscription(action='restore')\n"
    )
    assert read(source) == Writer(
        frozenset({"user_create", "user_update", "backup", "restore", "project_create"}),
        is_unresolved=False,
    )


def test_an_action_of_a_literal_the_contract_does_not_enumerate_is_read_all_the_same() -> None:
    # The comparison with the contract is the test's: the guard gives what the module inscribes.
    source = "from waterfall.platform.audit import Inscription\nInscription('user_purge')\n"
    assert read(source) == Writer(frozenset({"user_purge"}), is_unresolved=False)


def test_an_action_the_module_does_not_bind_is_read_as_the_contract_actions_it_spells() -> None:
    # A parameter typed by the whole enumeration, and a tuple unpacked, name no literal: the
    # module is flagged, and gives the actions of the contract it writes out — not the others.
    source = (
        "from waterfall.platform.audit import AuditAction, Inscription\n"
        "FOUND = [('backup', 1), ('user_purge', 2)]\n"
        "def f(action: AuditAction): return Inscription(action)\n"
        "def g(found):\n"
        "    return [Inscription(action) for action, _ in found]\n"
        "NAME = 'project_create'\n"
    )
    assert read(source) == Writer(frozenset({"backup", "project_create"}), is_unresolved=True)


def test_the_enumeration_of_the_contract_is_that_of_the_schema_of_the_actions() -> None:
    actions = contract_actions()
    assert {"project_create", "reference_designate", "project_manager_change", "restore"} <= actions
