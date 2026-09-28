# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the check of the catalogues of the front."""

import json
import re
from pathlib import Path

import pytest

from wftools import REPOSITORY, catalogs

SCHEMAS: dict[str, object] = {
    "ErrorCode": {"type": "string", "enum": ["NOT_FOUND"]},
    "PermissionCode": {"type": "string", "enum": ["users.read"]},
    "ProjectState": {"type": "string", "enum": ["created", "in_progress"]},
    "ProjectExit": {
        "type": "object",
        "properties": {
            "to_state": {"type": "string", "enum": ["lost"]},
            "confirmed": {"const": True},
        },
    },
}
CONTRACT: dict[str, object] = {"components": {"schemas": SCHEMAS}}

TWIN: dict[str, object] = {
    "app": {"name": "Waterfall"},
    "errors": {"NOT_FOUND": "Introuvable."},
    "permissions": {"users": {"read": "Lire les comptes"}},
    "enums": {
        "ProjectState": {"created": "Créé", "in_progress": "En cours"},
        "ProjectExit": {"to_state": {"lost": "Perdu"}},
    },
}


def with_key(catalogue: dict[str, object], group: str, name: str) -> dict[str, object]:
    """Return a copy of a catalogue with one more key in a group of its root."""
    extended = json.loads(json.dumps(catalogue))
    extended.setdefault(group, {})[name] = "Texte"
    return extended


def run(tmp_path: Path, fr: object, en: object) -> int:
    """Write a contract and two catalogues, and run the command on them."""
    bundle, reference, twin = tmp_path / "bundle.json", tmp_path / "fr.json", tmp_path / "en.json"
    bundle.write_text(json.dumps(CONTRACT), encoding="utf-8")
    reference.write_text(json.dumps(fr), encoding="utf-8")
    twin.write_text(json.dumps(en), encoding="utf-8")
    return catalogs.main([str(bundle), str(reference), str(twin)])


def keys_of(schema: object, name: str = "Schema") -> set[str]:
    """Return, dotted, the keys the contract asks for one schema."""
    contract: dict[str, object] = {"components": {"schemas": {name: schema}}}
    return {catalogs.dotted(key) for key in catalogs.coded_keys(contract)}


@pytest.mark.requirement("WF-QUA-0070-A")
@pytest.mark.parametrize("alone", ["fr", "en"])
def test_a_key_added_to_one_catalogue_only_fails_the_chain(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], alone: str
) -> None:
    extended = with_key(TWIN, "languageSelector", "label")
    fr, en = (extended, TWIN) if alone == "fr" else (TWIN, extended)
    assert run(tmp_path, fr, en) == 1
    other = "en" if alone == "fr" else "fr"
    error = capsys.readouterr().err
    assert f"{tmp_path / other}.json: missing languageSelector.label, which " in error
    assert f"which {tmp_path / alone}.json has" in error


@pytest.mark.requirement("WF-QUA-0070-A")
def test_twin_catalogues_that_cover_the_contract_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path, TWIN, TWIN) == 0
    assert capsys.readouterr().out == "2 catalogues, twins; 5 coded values covered\n"


@pytest.mark.requirement("WF-QUA-0070-A")
def test_a_key_is_compared_down_to_its_leaf() -> None:
    fr = {"app": {"name": "Waterfall", "tagline": "Devis"}}
    en = {"app": {"name": "Waterfall"}}
    assert catalogs.problems({}, {"fr": fr, "en": en}) == ["en: missing app.tagline, which fr has"]


def test_every_value_the_contract_codes_needs_its_key_in_every_catalogue() -> None:
    lacking = json.loads(json.dumps(TWIN))
    del lacking["enums"]["ProjectState"]["in_progress"]
    del lacking["errors"]
    assert catalogs.problems(CONTRACT, {"fr": lacking, "en": lacking}) == [
        "fr: missing enums.ProjectState.in_progress, a value the contract codes",
        "fr: missing errors.NOT_FOUND, a value the contract codes",
        "en: missing enums.ProjectState.in_progress, a value the contract codes",
        "en: missing errors.NOT_FOUND, a value the contract codes",
    ]


def test_a_coded_key_one_catalogue_lacks_is_reported_once() -> None:
    lacking = json.loads(json.dumps(TWIN))
    del lacking["permissions"]
    assert catalogs.problems(CONTRACT, {"fr": TWIN, "en": lacking}) == [
        "en: missing permissions.users.read, a value the contract codes"
    ]


def test_a_coded_key_the_contract_no_longer_has_is_refused_without_asking_its_twin() -> None:
    orphan = with_key(TWIN, "errors", "WITHDRAWN")
    assert catalogs.problems(CONTRACT, {"fr": orphan, "en": TWIN}) == [
        "fr: errors.WITHDRAWN matches no value the contract codes"
    ]


def test_the_texts_of_the_interface_are_the_front_s_own() -> None:
    assert catalogs.problems(CONTRACT, {"fr": TWIN, "en": TWIN}) == []


def test_a_named_enumeration_is_keyed_by_its_schema_and_value() -> None:
    assert keys_of({"type": "string", "enum": ["in_progress"]}, "ProjectState") == {
        "enums.ProjectState.in_progress"
    }


def test_error_codes_and_permissions_have_their_own_roots() -> None:
    assert keys_of({"enum": ["NOT_FOUND"]}, "ErrorCode") == {"errors.NOT_FOUND"}
    assert keys_of({"enum": ["users.read"]}, "PermissionCode") == {"permissions.users.read"}


def test_a_value_with_a_dot_is_read_as_levels() -> None:
    contract: dict[str, object] = {"components": {"schemas": {"C": {"enum": ["task.start"]}}}}
    assert catalogs.coded_keys(contract) == {("enums", "C", "task", "start")}


def test_an_enumeration_in_a_property_is_keyed_by_the_names_of_the_properties() -> None:
    schema = {
        "type": "object",
        "properties": {
            "status": {"enum": ["running"]},
            "series": {
                "type": "array",
                "items": {"properties": {"name": {"enum": ["earned_value"]}}},
            },
            "missing": {"type": "array", "items": {"enum": ["active_cost_category"]}},
        },
    }
    assert keys_of(schema, "Ref") == {
        "enums.Ref.status.running",
        "enums.Ref.series.name.earned_value",
        "enums.Ref.missing.active_cost_category",
    }


def test_a_composition_or_a_map_adds_no_level() -> None:
    schema = {
        "allOf": [{"$ref": "#/components/schemas/Base"}, {"properties": {"a": {"enum": ["x"]}}}],
        "anyOf": [{"enum": ["y"]}, {"type": "null"}],
        "oneOf": [{"properties": {"b": {"enum": ["z"]}}}],
        "additionalProperties": {"enum": ["w"]},
    }
    assert keys_of(schema) == {
        "enums.Schema.a.x",
        "enums.Schema.y",
        "enums.Schema.b.z",
        "enums.Schema.w",
    }


def test_a_const_or_a_value_that_is_not_a_string_has_no_key() -> None:
    schema = {
        "properties": {
            "confirmed": {"const": True},
            "reason": {"type": ["string", "null"], "enum": ["late", None]},
            "open": {"additionalProperties": True},
        }
    }
    assert keys_of(schema) == {"enums.Schema.reason.late"}


def test_a_contract_without_schemas_codes_nothing() -> None:
    assert catalogs.coded_keys({}) == set()


@pytest.mark.parametrize(
    ("catalogue", "fault"),
    [
        ({"app": {"name": ""}}, "app.name is not a non-empty text"),
        ({"app": {"name": "  "}}, "app.name is not a non-empty text"),
        ({"app": {"name": 3}}, "app.name is not a non-empty text"),
        ({"app": {}}, "app is an empty group"),
        ({"app.name": "Texte"}, "app.name: a level empty or with a dot, which next-intl misreads"),
        (["Texte"], "is not an object of keys"),
    ],
)
def test_a_catalogue_holds_only_groups_and_non_empty_texts(catalogue: object, fault: str) -> None:
    assert catalogs.read_catalogue(catalogue).faults == [fault]


def test_a_faulty_leaf_keeps_its_key() -> None:
    reading = catalogs.read_catalogue({"app": {"name": "", "title": "Waterfall"}})
    assert reading.keys == {("app", "name"), ("app", "title")}
    assert reading.texts == {("app", "title"): "Waterfall"}


def test_an_empty_text_is_reported_once_and_not_as_missing() -> None:
    empty = json.loads(json.dumps(TWIN))
    empty["errors"]["NOT_FOUND"] = ""
    assert catalogs.problems(CONTRACT, {"fr": empty, "en": TWIN}) == [
        "fr: errors.NOT_FOUND is not a non-empty text"
    ]


def test_a_level_with_a_dot_is_reported_once_and_not_as_missing() -> None:
    fr = {"app": {"name": "Waterfall"}}
    assert catalogs.problems({}, {"fr": {"app.name": "Waterfall"}, "en": fr}) == [
        "fr: app.name: a level empty or with a dot, which next-intl misreads"
    ]


def test_a_key_written_twice_in_a_file_is_refused_and_named() -> None:
    catalogue = catalogs.parse_catalogue('{"app": {"name": "A", "title": "B", "name": "C"}}')
    assert catalogs.read_catalogue(catalogue).faults == ["app.name is written more than once"]


def test_a_key_written_twice_fails_the_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle, fr = tmp_path / "bundle.json", tmp_path / "fr.json"
    bundle.write_text("{}", encoding="utf-8")
    fr.write_text('{"app": "A", "app": "B"}', encoding="utf-8")
    assert catalogs.main([str(bundle), str(fr)]) == 1
    assert capsys.readouterr().err.startswith(f"{fr}: app is written more than once\n")


@pytest.mark.parametrize(
    ("message", "names"),
    [
        ("Waterfall", set[str]()),
        ("Permission requise : {permission}.", {"permission"}),
        ("{amount, number} le {day, date, short}", {"amount", "day"}),
        (
            "{max_columns, plural, one {# colonne} =0 {aucune} other {# colonnes de {grid}}}",
            {"max_columns", "grid"},
        ),
        ("{kind, select, task {Tâche {label}} other {Ligne}}", {"kind", "label"}),
        ("{count, selectordinal, offset:1 one {#st} other {#th}}", {"count"}),
        ("} {stray", {"stray"}),
        ("{open, plural, one {x}", {"open"}),
        ("{open, plural, one", {"open"}),
        ("{open, plural}", {"open"}),
    ],
)
def test_the_arguments_of_a_message_are_the_names_that_open_its_braces(
    message: str, names: set[str]
) -> None:
    assert catalogs.icu_arguments(message) == names


@pytest.mark.parametrize(
    ("fr", "en", "fault"),
    [
        (
            "{n, plural, one {# ligne} other {# lignes}}",
            "{n, plural, one {# line} other {# lines of {grid}}}",
            "en: app.lines uses the arguments {grid, n}, fr {n}",
        ),
        (
            "{n, plural, one {# ligne de {grid}} other {# lignes}}",
            "{n, plural, one {# line} other {# lines}}",
            "en: app.lines uses the arguments {n}, fr {grid, n}",
        ),
    ],
)
def test_a_text_uses_the_same_arguments_in_every_catalogue(fr: str, en: str, fault: str) -> None:
    assert catalogs.problems({}, {"fr": {"app": {"lines": fr}}, "en": {"app": {"lines": en}}}) == [
        fault
    ]


def test_a_fault_of_shape_names_its_catalogue() -> None:
    assert catalogs.problems({}, {"fr": {"app": {"name": ""}}}) == [
        "fr: app.name is not a non-empty text"
    ]


def test_a_shared_parameter_keys_its_values_by_its_name() -> None:
    contract: dict[str, object] = {
        "components": {
            "parameters": {
                "Scope": {
                    "name": "scope",
                    "schema": {"anyOf": [{"enum": ["project", "unassigned"]}, {"format": "uuid"}]},
                },
                "Limit": {"name": "limit", "schema": {"type": "integer"}},
            }
        }
    }
    assert {catalogs.dotted(key) for key in catalogs.coded_keys(contract)} == {
        "enums.Scope.project",
        "enums.Scope.unassigned",
    }


def test_a_shared_parameter_that_codes_values_may_not_bear_the_name_of_a_schema() -> None:
    contract: dict[str, object] = {
        "components": {
            "schemas": {"Scope": {"enum": ["x"]}, "SortOrder": {"enum": ["asc"]}},
            "parameters": {
                "Scope": {"name": "scope", "schema": {"enum": ["project"]}},
                "SortOrder": {"name": "sort_order", "schema": {"$ref": "#/SortOrder"}},
            },
        }
    }
    assert catalogs.contract_faults(contract) == [
        "components.parameters.Scope: also the name of a schema, whose keys it would share"
    ]


def test_a_parameter_of_an_operation_may_not_enumerate_its_values_in_line() -> None:
    enumerated = {"name": "basis", "in": "query", "schema": {"enum": ["estimate"]}}
    contract: dict[str, object] = {
        "paths": {
            "/workload": {"get": {"parameters": [enumerated]}},
            "/plans": {"parameters": [enumerated], "get": {}, "post": {"parameters": []}},
        }
    }
    advice = (
        ": the parameter basis enumerates its values in line; make it a shared parameter of "
        "docs/api/components/parameters.yaml, whose name keys its values"
    )
    assert catalogs.contract_faults(contract) == [
        f"GET /workload{advice}",
        f"GET /plans{advice}",
        f"POST /plans{advice}",
    ]


def test_sort_columns_shared_parameters_and_responses_may_stay_in_line() -> None:
    sort_by = {"name": "sort_by", "in": "query", "schema": {"enum": ["label", "state"]}}
    shared = {"$ref": "#/components/parameters/Scope"}
    probe = {"200": {"content": {"application/json": {"schema": {"enum": ["ok"]}}}}}
    contract: dict[str, object] = {
        "paths": {
            "/projects": {"get": {"parameters": [sort_by, shared]}},
            "/health": {"get": {"responses": probe}},
        }
    }
    assert catalogs.contract_faults(contract) == []
    assert catalogs.coded_keys(contract) == set()


def test_a_fault_of_the_contract_fails_the_check() -> None:
    contract: dict[str, object] = {
        "paths": {"/w": {"get": {"parameters": [{"name": "basis", "schema": {"enum": ["a"]}}]}}}
    }
    assert catalogs.problems(contract, {"fr": TWIN})[0].startswith("contract: GET /w: ")


def test_a_catalogue_that_is_not_json_fails_and_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle, broken = tmp_path / "bundle.json", tmp_path / "fr.json"
    bundle.write_text(json.dumps(CONTRACT), encoding="utf-8")
    broken.write_text("{", encoding="utf-8")
    assert catalogs.main([str(bundle), str(broken)]) == 1
    assert capsys.readouterr().err.startswith(f"{broken}: not readable as JSON: ")


def test_a_missing_bundle_fails_and_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "bundle.json"
    assert catalogs.main([str(missing), str(missing)]) == 1
    assert capsys.readouterr().err.startswith(f"{missing}: not readable as JSON: ")


def test_a_bundle_that_is_not_an_object_fails_with_a_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle, fr = tmp_path / "bundle.json", tmp_path / "fr.json"
    bundle.write_text("[]", encoding="utf-8")
    fr.write_text(json.dumps(TWIN), encoding="utf-8")
    assert catalogs.main([str(bundle), str(fr)]) == 1
    assert capsys.readouterr().err == f"{bundle}: not a contract, which is a JSON object\n"


def test_a_failure_points_to_the_guide(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(tmp_path, TWIN, {}) == 1
    assert "« Clés de traduction »" in capsys.readouterr().err


@pytest.mark.requirement("WF-QUA-0070-A")
def test_the_chain_runs_the_check_of_the_catalogues() -> None:
    makefile = (REPOSITORY / "Makefile").read_text(encoding="utf-8")
    rule = re.search(r"^check-front:([^#\n]*)", makefile, re.MULTILINE)
    assert rule is not None
    assert "catalogs" in rule.group(1).split()
    recipe = re.search(r"^catalogs:.*\n((?:\t.*\n)+)", makefile, re.MULTILINE)
    assert recipe is not None
    assert "$(WFTOOLS).catalogs $(JSON_BUNDLE) $(FRONT)/messages/fr.json" in recipe.group(1)
    workflow = (REPOSITORY / ".github/workflows/front.yml").read_text(encoding="utf-8")
    assert "run: make check-front" in workflow


def test_no_catalogue_leaves_only_the_contract_to_check() -> None:
    assert catalogs.problems({}, {}) == []
