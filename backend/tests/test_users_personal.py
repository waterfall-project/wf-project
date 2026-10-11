# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the holder of an account sets alone: its preferences and its avatar (US-0400).

Each person is an account written around the service, who calls the API with a token of the realm
of test; every answer is checked against the contract. The realm of test serves keys and nothing
of the administration API: a change of the language, which Keycloak is told of, fails there (503)
— its success is tried against the platform (``test_keycloak_personal.py``).
"""

import threading
from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from realm import KEY, TestRealm
from sqlalchemy import insert, select, update
from support import ContractClient, bearer, wait_for_a_lock

from waterfall.core.users.interface import image_type
from waterfall.core.users.personal import merged
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database, utc_now
from waterfall.platform.installation import THE_ROW, Installation

ME = "/api/v1/me"
PREFERENCES = "/api/v1/me/preferences"
AVATAR = "/api/v1/me/avatar"
INSTALLATION = "/api/v1/installation"
# The bound of an avatar the installation of these tests sets, in bytes.
BOUND = 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
JPEG = b"\xff\xd8\xff\xe0" + b"\x01" * 24
# The settings of the table of the accounts, as its grid keeps them (WF-IHM-0060).
USERS_GRID = {"hidden_columns": ["origin"], "column_widths": {"email": 240}, "sort": None}
ROLES_GRID = {"column_widths": {"label": 180}, "filters": {"is_predefined": "true"}}


def person(database: Database, realm: TestRealm, *roles: UUID, **columns: object) -> Any:
    """Write an account with the roles it is given; give its identifier and its token's header."""
    subject = f"subject-{uuid4()}"
    user_id = account(
        database,
        "Martin",
        f"Claire-{uuid4().hex[:6]}",
        roles=roles,
        idp_subject=subject,
        **columns,
    )
    return user_id, bearer(realm.token(subject, KEY))


def installed(database: Database, *, avatar_max_bytes: int = BOUND) -> None:
    """Write the row of the installation, as its bootstrap does (US-0420)."""
    with database.transaction() as session:
        session.execute(
            insert(Installation).values(
                id=THE_ROW,
                default_language="en",
                avatar_max_bytes=avatar_max_bytes,
                external_backup_max_bytes=2**40,
                installed_at=utc_now(),
            )
        )


def preferences_of(database: Database, user_id: UUID) -> dict[str, Any]:
    """Read the preferences an account holds in the base."""
    with database.transaction() as session:
        return session.scalars(
            select(UserAccount.display_preferences).where(UserAccount.id == user_id)
        ).one()


def avatar_of(database: Database, user_id: UUID) -> tuple[bytes | None, str | None]:
    """Read the avatar an account holds in the base, and its type."""
    with database.transaction() as session:
        row = session.execute(
            select(UserAccount.avatar, UserAccount.avatar_media_type).where(
                UserAccount.id == user_id
            )
        ).one()
    return row.avatar, row.avatar_media_type


def put(api: ContractClient, headers: dict[str, str], image: Any, kind: str) -> Any:
    """Put an image as the caller's avatar, said to be of ``kind``."""
    return api.request("PUT", AVATAR, headers={**headers, "Content-Type": kind}, content=image)


def refusal(response: Any) -> tuple[int, str, list[dict[str, Any]]]:
    """Give the status, the code and the fields of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("fields", [])


@pytest.mark.requirement("WF-ADM-0040-A")
def test_a_user_changes_his_preferences_and_cannot_change_those_of_another(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    # « Un utilisateur modifie ses préférences et ne peut pas modifier celles d'un autre. »
    administration = role(
        database, "Gestion des comptes", permissions=("users.read", "users.write")
    )
    claire, hers = person(database, realm, administration)
    other, his = person(database, realm, display_preferences={"theme": "light"})
    changed = api.patch(
        PREFERENCES, headers=hers, json={"theme": "dark", "grids": {"users": USERS_GRID}}
    )
    assert changed.status_code == 200, changed.text
    assert changed.json() == {"theme": "dark", "grids": {"users": USERS_GRID}}
    assert api.get(ME, headers=hers).json()["display_preferences"] == changed.json()
    # Hers changed, not his: the operation changes the caller's own.
    assert api.get(ME, headers=his).json()["display_preferences"] == {"theme": "light"}
    # No operation changes those of another: no address of his, outside of the contract, and not
    # even for whom may change his account, whose writes do not carry them.
    outside = api.client.patch(f"/api/v1/users/{other}/preferences", headers=hers, json={})
    assert (outside.status_code, outside.json()["code"]) == (404, "NOT_FOUND")
    response = api.patch(
        f"/api/v1/users/{other}",
        headers=hers,
        json={"display_preferences": {"theme": "dark"}, "lock_version": 0},
    )
    assert response.status_code == 200, response.text
    assert preferences_of(database, other) == {"theme": "light"}
    assert preferences_of(database, claire) == changed.json()


def test_a_change_of_the_preferences_changes_only_what_it_carries(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    # In ``grids``, only the grids it names, each replaced whole; a grid sent null finds its
    # settings by default again.
    kept = {"theme": "dark", "grids": {"users": USERS_GRID, "roles": ROLES_GRID}}
    _, headers = person(database, realm, display_preferences=kept)
    response = api.patch(
        PREFERENCES,
        headers=headers,
        json={
            "highlight_tasks_added_after_reference": True,
            "grids": {"roles": None, "tasks": {"hidden_columns": []}},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "theme": "dark",
        "highlight_tasks_added_after_reference": True,
        "grids": {"users": USERS_GRID, "tasks": {"hidden_columns": []}},
    }
    replaced = api.patch(
        PREFERENCES,
        headers=headers,
        json={"grids": {"users": {"sort": {"column": "email", "order": "desc"}}}},
    )
    assert replaced.json()["grids"]["users"] == {"sort": {"column": "email", "order": "desc"}}
    # Nothing sent, nothing changed.
    assert api.patch(PREFERENCES, headers=headers, json={}).json() == replaced.json()


def test_the_preferences_merge_what_a_change_carries_into_what_they_were() -> None:
    current = {"language": "fr", "grids": {"users": USERS_GRID}}
    assert merged(current, {"theme": "light"}) == {**current, "theme": "light"}
    assert merged(current, {"grids": {"users": None}}) == {"language": "fr", "grids": {}}
    assert merged({}, {"grids": {"roles": ROLES_GRID}}) == {"grids": {"roles": ROLES_GRID}}
    assert merged(current, {}) == current


@pytest.mark.parametrize(
    ("sent", "pointer"),
    [
        ({"language": None}, "/language"),
        ({"theme": None}, "/theme"),
        ({"grids": None}, "/grids"),
        ({"grids": {"users": {"hidden_columns": None}}}, "/grids/users/hidden_columns"),
        ({"grids": {"a/b": {"filters": None}}}, "/grids/a~1b/filters"),
        (
            {"grids": {"users": {"column_widths": {"email": 19}}}},
            "/grids/users/column_widths/email",
        ),
    ],
)
def test_a_value_the_contract_refuses_is_refused_on_its_field_and_nothing_is_written(
    api: ContractClient, database: Database, realm: TestRealm, sent: dict[str, Any], pointer: str
) -> None:
    user_id, headers = person(database, realm, display_preferences={"theme": "dark"})
    response = api.patch(PREFERENCES, headers=headers, json=sent)
    assert refusal(response)[:2] == (422, "VALIDATION_FAILED")
    assert [field["pointer"] for field in refusal(response)[2]] == [pointer]
    assert preferences_of(database, user_id) == {"theme": "dark"}


# The bounds of the preferences (#874), each passed by one: where the fault is pointed at.
LONG = "x" * 65
BOUNDS_PASSED: list[tuple[dict[str, Any], tuple[str, str]]] = [
    ({"grids": {f"g{rank}": None for rank in range(101)}}, ("/grids", "VALUE_TOO_LONG")),
    (
        {"grids": {"users": {"hidden_columns": [f"c{rank}" for rank in range(65)]}}},
        ("/grids/users/hidden_columns", "VALUE_TOO_LONG"),
    ),
    (
        {"grids": {"users": {"hidden_columns": [LONG]}}},
        ("/grids/users/hidden_columns/0", "VALUE_TOO_LONG"),
    ),
    (
        {"grids": {"users": {"column_widths": {f"c{rank}": 40 for rank in range(65)}}}},
        ("/grids/users/column_widths", "VALUE_TOO_LONG"),
    ),
    (
        {"grids": {"users": {"sort": {"column": LONG, "order": "asc"}}}},
        ("/grids/users/sort/column", "VALUE_TOO_LONG"),
    ),
    (
        {"grids": {"users": {"filters": {f"f{rank}": "1" for rank in range(21)}}}},
        ("/grids/users/filters", "VALUE_TOO_LONG"),
    ),
    (
        {"grids": {"users": {"filters": {"search": "x" * 501}}}},
        ("/grids/users/filters/search", "VALUE_TOO_LONG"),
    ),
    (
        {"grids": {"users": {"filters": {"is_predefined": True}}}},
        ("/grids/users/filters/is_predefined", "VALIDATION_FAILED"),
    ),
]


@pytest.mark.parametrize(("sent", "fault"), BOUNDS_PASSED)
def test_preferences_that_pass_a_bound_are_refused_and_nothing_is_written(
    api: ContractClient,
    database: Database,
    realm: TestRealm,
    sent: dict[str, Any],
    fault: tuple[str, str],
) -> None:
    # The preferences are read with the account at each request: their size is bounded (#874).
    user_id, headers = person(database, realm, display_preferences={"theme": "dark"})
    response = api.patch(PREFERENCES, headers=headers, json=sent)
    assert refusal(response)[:2] == (422, "VALIDATION_FAILED")
    assert [(field["pointer"], field["code"]) for field in refusal(response)[2]] == [fault]
    assert preferences_of(database, user_id) == {"theme": "dark"}


@pytest.mark.parametrize(
    ("sent", "pointer"),
    [
        ({"grids": {LONG: None}}, "/grids"),
        ({"grids": {"users": {"column_widths": {LONG: 40}}}}, "/grids/users/column_widths"),
        ({"grids": {"users": {"filters": {LONG: "1"}}}}, "/grids/users/filters"),
    ],
)
def test_a_name_longer_than_its_bound_is_refused_at_its_object_and_nothing_is_written(
    api: ContractClient, database: Database, realm: TestRealm, sent: dict[str, Any], pointer: str
) -> None:
    # A key is no field of its own: its fault is pointed at the object that holds it.
    user_id, headers = person(database, realm, display_preferences={"theme": "dark"})
    response = api.patch(PREFERENCES, headers=headers, json=sent)
    assert refusal(response)[:2] == (422, "VALIDATION_FAILED")
    assert [(field["pointer"], field["code"]) for field in refusal(response)[2]] == [
        (pointer, "VALUE_TOO_LONG")
    ]
    assert preferences_of(database, user_id) == {"theme": "dark"}


def test_preferences_at_their_bounds_are_written(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    user_id, headers = person(database, realm)
    name = "x" * 64
    grid = {
        "hidden_columns": [f"{rank:064d}" for rank in range(64)],
        "column_widths": {f"{rank:064d}": 40 for rank in range(64)},
        "sort": {"column": name, "order": "asc"},
        "filters": {f"{rank:064d}": "y" * 500 for rank in range(20)},
    }
    sent: dict[str, Any] = {
        "grids": {name: grid, **{f"g{rank}": {"hidden_columns": []} for rank in range(99)}}
    }
    response = api.patch(PREFERENCES, headers=headers, json=sent)
    assert response.status_code == 200, response.text
    assert preferences_of(database, user_id) == sent


# A key that holds ``/`` or ``~``, and where its fault is pointed at.
ESCAPED: list[tuple[dict[str, Any], tuple[str, str]]] = [
    (
        {"grids": {"tasks": {"filters": {"a/b": "\x00"}}}},
        ("/grids/tasks/filters/a~1b", "VALIDATION_FAILED"),
    ),
    (
        {"grids": {"tasks": {"column_widths": {"a~b": "x"}}}},
        ("/grids/tasks/column_widths/a~0b", "NUMBER_INVALID"),
    ),
    (
        {"grids": {"~/": {"column_widths": {"/": 1}}}},
        ("/grids/~0~1/column_widths/~1", "VALUE_OUT_OF_RANGE"),
    ),
]


@pytest.mark.parametrize(("sent", "fault"), ESCAPED)
def test_the_pointer_of_a_fault_escapes_a_key_as_rfc_6901_does(
    api: ContractClient,
    database: Database,
    realm: TestRealm,
    sent: dict[str, Any],
    fault: tuple[str, str],
) -> None:
    # A key sent with a ``/`` is one place, not two: ``~`` is written ``~0``, ``/`` ``~1`` (#750).
    _, headers = person(database, realm)
    response = api.patch(PREFERENCES, headers=headers, json=sent)
    assert refusal(response)[:2] == (422, "VALIDATION_FAILED")
    assert [(field["pointer"], field["code"]) for field in refusal(response)[2]] == [fault]


def test_a_language_chosen_is_written_only_once_the_identity_provider_has_it(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    # The realm of test answers nothing of the administration API: the change is refused as a
    # component unavailable, and nothing is written — never presented as done.
    user_id, headers = person(database, realm, display_preferences={"language": "fr"})
    response = api.patch(PREFERENCES, headers=headers, json={"language": "en", "theme": "dark"})
    assert (response.status_code, response.json()["code"]) == (503, "COMPONENT_UNAVAILABLE")
    assert response.json()["params"] == {"component": "identity_provider"}
    assert preferences_of(database, user_id) == {"language": "fr"}
    # The language it has already, sent again, is given to the provider all the same: the
    # provider's may differ — another tab, the language picker of the sign-in page — and choosing
    # the language shown again is what repairs it.
    kept = api.patch(PREFERENCES, headers=headers, json={"language": "fr", "theme": "dark"})
    assert (kept.status_code, kept.json()["code"]) == (503, "COMPONENT_UNAVAILABLE")
    assert preferences_of(database, user_id) == {"language": "fr"}
    # A change without a language — a theme, a grid — does not ask it.
    themed = api.patch(PREFERENCES, headers=headers, json={"theme": "dark"})
    assert themed.status_code == 200, themed.text
    assert preferences_of(database, user_id) == {"language": "fr", "theme": "dark"}


def test_the_language_of_an_account_of_a_directory_is_not_asked_of_the_provider(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    # Its attributes are the directory's, federated read only: the provider is not asked, and the
    # realm of test, which would fail, is not reached.
    user_id, headers = person(database, realm, origin="directory")
    response = api.patch(PREFERENCES, headers=headers, json={"language": "en"})
    assert response.status_code == 200, response.text
    assert preferences_of(database, user_id) == {"language": "en"}


def test_two_changes_at_once_of_two_grids_each_keep_the_other(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    # The account is locked, then its preferences read under the lock: a change committed while
    # another waited is not lost by the second.
    user_id, headers = person(database, realm)
    answers: list[Any] = []
    with database.transaction() as session:
        session.execute(select(UserAccount.id).where(UserAccount.id == user_id).with_for_update())
        waiting = threading.Thread(
            target=lambda: answers.append(
                api.patch(PREFERENCES, headers=headers, json={"grids": {"users": USERS_GRID}})
            )
        )
        waiting.start()
        wait_for_a_lock(database)
        session.execute(
            update(UserAccount)
            .where(UserAccount.id == user_id)
            .values(display_preferences={"grids": {"roles": ROLES_GRID}})
        )
    waiting.join()
    assert answers[0].json() == {"grids": {"roles": ROLES_GRID, "users": USERS_GRID}}
    assert preferences_of(database, user_id) == answers[0].json()


@pytest.mark.requirement("WF-ADM-0080-A")
def test_a_user_puts_replaces_and_withdraws_his_avatar_alone(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    # « Un utilisateur ajoute, remplace et retire son avatar sans intervention d'un
    # administrateur. » : an account without any role does it.
    installed(database)
    user_id, headers = person(database, realm)
    assert put(api, headers, PNG, "image/png").status_code == 204
    assert api.get(ME, headers=headers).json()["has_avatar"] is True
    served = api.get(f"/api/v1/users/{user_id}/avatar", headers=headers)
    assert (served.status_code, served.headers["content-type"], served.content) == (
        200,
        "image/png",
        PNG,
    )
    assert put(api, headers, JPEG, "image/jpeg").status_code == 204
    assert avatar_of(database, user_id) == (JPEG, "image/jpeg")
    assert api.delete(AVATAR, headers=headers).status_code == 204
    assert avatar_of(database, user_id) == (None, None)
    assert api.get(ME, headers=headers).json()["has_avatar"] is False
    # Withdrawn, it is withdrawn already.
    assert api.delete(AVATAR, headers=headers).status_code == 204


@pytest.mark.requirement("WF-ADM-0080-A")
def test_a_user_cannot_change_the_avatar_of_another(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    # « Il ne peut pas modifier celui d'un autre. » : his own changes alone, and no operation
    # reaches another's, not even for whom may change the accounts.
    installed(database)
    administration = role(
        database, "Gestion des comptes", permissions=("users.read", "users.write")
    )
    claire, hers = person(database, realm, administration)
    other, his = person(database, realm)
    assert put(api, his, PNG, "image/png").status_code == 204
    assert put(api, hers, JPEG, "image/jpeg").status_code == 204
    assert api.delete(AVATAR, headers=hers).status_code == 204
    assert avatar_of(database, other) == (PNG, "image/png")
    assert avatar_of(database, claire) == (None, None)
    address = f"/api/v1/users/{other}/avatar"
    sent = {**hers, "Content-Type": "image/jpeg"}
    # Outside of the contract, which serves the avatar of another to read only.
    assert api.client.put(address, headers=sent, content=JPEG).status_code == 404
    assert api.client.delete(address, headers=hers).status_code == 404
    assert avatar_of(database, other) == (PNG, "image/png")
    # Any caller reads it, where the account is cited.
    assert api.get(address, headers=hers).content == PNG


def test_an_image_is_kept_with_the_type_its_content_shows_whatever_its_request_says(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    installed(database)
    user_id, headers = person(database, realm)
    assert put(api, headers, JPEG, "image/png").status_code == 204
    assert avatar_of(database, user_id) == (JPEG, "image/jpeg")
    served = api.get(f"/api/v1/users/{user_id}/avatar", headers=headers)
    assert served.headers["content-type"] == "image/jpeg"
    assert (image_type(PNG), image_type(JPEG), image_type(b"GIF89a")) == (
        "image/png",
        "image/jpeg",
        None,
    )


# An image an avatar cannot be, said to be of a type, and its refusal.
UNFIT: list[tuple[tuple[Any, str], tuple[int, str, list[dict[str, str]]]]] = [
    (
        (b"GIF89a" + b"\x00" * 10, "image/png"),
        (422, "VALIDATION_FAILED", [{"pointer": "", "code": "VALIDATION_FAILED"}]),
    ),
    ((PNG, "image/gif"), (400, "MALFORMED_REQUEST", [])),
    ((PNG, "application/octet-stream"), (400, "MALFORMED_REQUEST", [])),
    ((b"", "image/png"), (400, "MALFORMED_REQUEST", [])),
    ((PNG + b"\x00" * (BOUND - len(PNG) + 1), "image/png"), (413, "FILE_TOO_LARGE", [])),
    # Without its length, the bound passed while it is read.
    ((iter([PNG, b"\x00" * BOUND]), "image/png"), (413, "FILE_TOO_LARGE", [])),
]


@pytest.mark.parametrize(("sent", "refused"), UNFIT)
def test_an_image_the_avatar_cannot_be_is_refused_and_the_avatar_kept(
    api: ContractClient,
    database: Database,
    realm: TestRealm,
    sent: tuple[Any, str],
    refused: tuple[int, str, list[dict[str, str]]],
) -> None:
    # Neither a PNG nor a JPEG by its content, a type the contract does not declare, nothing, or
    # beyond the bound of the installation — said by its length, or passed while it is read.
    installed(database)
    user_id, headers = person(database, realm, avatar=PNG, avatar_media_type="image/png")
    assert refusal(put(api, headers, *sent)) == refused
    assert avatar_of(database, user_id) == (PNG, "image/png")


def test_an_image_of_the_bound_of_the_installation_is_admitted(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    installed(database)
    user_id, headers = person(database, realm)
    image = PNG + b"\x00" * (BOUND - len(PNG))
    assert put(api, headers, image, "image/png").status_code == 204
    assert avatar_of(database, user_id) == (image, "image/png")


def test_an_avatar_is_not_read_for_a_request_without_a_session(
    api: ContractClient, database: Database
) -> None:
    installed(database)
    response = put(api, {}, PNG, "image/png")
    assert refusal(response)[:2] == (401, "SESSION_REQUIRED")
    assert api.get(f"/api/v1/users/{uuid4()}/avatar").status_code == 401


def test_an_account_without_avatar_or_unknown_has_none_to_serve(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    user_id, headers = person(database, realm)
    for named in (user_id, uuid4(), "not-an-identifier"):
        response = api.get(f"/api/v1/users/{named}/avatar", headers=headers)
        assert refusal(response)[:2] == (404, "NOT_FOUND")


def test_the_installation_is_read_without_a_session(
    api: ContractClient, database: Database
) -> None:
    installed(database, avatar_max_bytes=512 * 1024)
    response = api.get(INSTALLATION)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "default_language": "en",
        "avatar_max_bytes": 524288,
        "external_backup_max_bytes": 2**40,
    }


def test_an_installation_not_bootstrapped_is_not_ready_to_serve_its_settings(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    # Its row is the bootstrap's (US-0420): no value nobody chose is served, nor applied.
    response = api.get(INSTALLATION)
    assert (response.status_code, response.json()["code"]) == (503, "COMPONENT_UNAVAILABLE")
    assert response.json()["params"] == {"component": "database"}
    user_id, headers = person(database, realm)
    assert refusal(put(api, headers, PNG, "image/png"))[:2] == (503, "COMPONENT_UNAVAILABLE")
    assert avatar_of(database, user_id) == (None, None)
