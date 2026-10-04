#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Regenerate INVENTORY.md from the contract.

One row per operation, with the requirements its own summary and description cite
— not those its parameters, bodies or responses happen to mention — then the
coverage: how many requirements of the specification the contract cites, and
which ones it does not, with for each domain the reason it has no reason to.

Fails when an operation cites no requirement and is not declared below as one
that realises none, so that the traceability rule is checked and not merely asked
for in CONTRIBUTING.

The document itself is written in French, like the specification it mirrors; only
this program and its console output are in English.
"""

import re
import sys
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from wftools import projection

ROOT = Path(__file__).resolve().parent.parent

FAMILIES: list[tuple[str, str]] = [
    ("system", "Système, métriques et traitements de fond"),
    ("session", "Session, compte courant et préférences"),
    ("access", "Comptes, rôles et permissions"),
    ("platform", "Sauvegarde et restauration"),
    ("reference", "Référentiel commun"),
    ("projects", "Projets, cycle de vie, lotissement, contributeurs"),
    ("revisions", "Révisions, structures et arbre commun"),
    ("analysis", "Indicateurs de devis, de reste à engager et de projet"),
    ("risks", "Risques et provisions"),
    ("costs", "Coûts réels"),
    ("exchanges", "Échanges par fichier"),
    ("portfolio", "Portefeuille"),
]

# Why a whole requirement domain legitimately has no surface in the contract.
REASONS: dict[str, str] = {
    "ARC": "Choix d'architecture interne : noyau unique, rôles des composants de données, "
    "empaquetage, autorité du serveur, absence d'état. Ils se vérifient sur le dépôt "
    "et le déploiement.",
    "CMP": "Compatibilité des navigateurs et largeurs d'affichage : propriété du front.",
    "DAT": "Partitionnement et migrations : propriétés du schéma, invisibles du contrat.",
    "EXP": "Exploitation : environnements, amorçage, mise à jour, perte maximale. Aucune "
    "n'est une opération d'API.",
    "IHM": "Invariants d'interface : navigation, saisie au clavier, accessibilité. Ils "
    "vivent dans le front.",
    "IND": "WF-IND-0130, l'évolution des indices, attend la mise à jour du contrat qui suit "
    "la revue de la spécification du 2026-10-03 : une lecture des courbes d'indices y "
    "entrera, et la projection de décaissement, devenue la lecture en décaissements de la courbe en S (WF-IND-0100), y est rattachée.",
    "PLA": "WF-PLA-0160, les unités de durée, attend la même mise à jour : les constantes "
    "de conversion de l'installation entrent dans le référentiel du contrat.",
    "INTF": "Les trois usages d'acteurs décrivent le contenu des rôles prédéfinis, servi par "
    "le catalogue des permissions ; la règle de traduction vit dans le front.",
    "QUA": "Chaîne de vérification : tests, analyse statique, jeu de données, mesures. Elle "
    "s'exerce sur le contrat, elle n'y figure pas.",
}

# Operations that legitimately realise no requirement: they exist because HTTP or a
# supervision tool needs them, not because the specification asked for them.
NO_REQUIREMENT: dict[str, str] = {
    "getLiveness": "Sonde de vivacité : elle ne touche à rien et ne réalise rien.",
}

# Where an operation stops describing itself and starts describing its interface.
RE_HEAD = re.compile(r"\n    (?:parameters|requestBody|responses|security|tags):")
RE_OPERATION = re.compile(
    r"^  (get|post|put|patch|delete):\n(.*?)(?=\n  [a-z]+:\n|\Z)", re.DOTALL | re.MULTILINE
)
RE_OWN_WORDS = re.compile(r"\n    (?:summary|description): [^\n]*(?:\n      [^\n]*)*")
RE_REQUIREMENT = re.compile(r"WF-[A-Z]+-\d{4}")


@dataclass(frozen=True, slots=True)
class Operation:
    """An operation of the contract, and the requirements its own words cite."""

    family: str
    path: str
    method: str
    identifier: str
    operation: str
    requirements: tuple[str, ...]


def _first(pattern: str, text: str) -> str:
    found = re.search(pattern, text)
    return found.group(1) if found else ""


def operations() -> Iterator[Operation]:
    """Yield every operation of the contract, by family then by path."""
    for family, _ in FAMILIES:
        path_file = ROOT / "paths" / f"{family}.yaml"
        for block in re.split(r"\n(?=/)", path_file.read_text(encoding="utf-8")):
            header = re.match(r"^(/[^\s:]*):", block)
            if not header:
                continue
            for found in RE_OPERATION.finditer(block):
                body = found.group(2)
                # Only the operation's own words count: a requirement cited by a shared
                # response or schema says nothing about what this operation realises.
                head = "".join(RE_HEAD.split("\n" + body)[:1] + RE_OWN_WORDS.findall(body))
                identifier = _first(r"operationId: (\w+)", body)
                yield Operation(
                    family=family,
                    path=header.group(1),
                    method=found.group(1).upper(),
                    identifier=identifier,
                    operation=_first(r"summary: (.*)", body).strip().strip("'") or identifier,
                    requirements=tuple(sorted(set(RE_REQUIREMENT.findall(head)))),
                )


def requirements_of_the_document() -> dict[str, str]:
    """Return the key and the title of every requirement, the example of §1.3.1 excepted."""
    return {r.key: r.title for r in projection.read() if not r.is_example}


def _table(ops: list[Operation]) -> list[str]:
    lines: list[str] = []
    for family, title in FAMILIES:
        of_family = [o for o in ops if o.family == family]
        lines += [
            f"## {title}",
            "",
            f"`paths/{family}.yaml` — {len(of_family)} opérations",
            "",
            "| Méthode | Chemin | Opération | Exigences citées |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| {o.method} | `{o.path}` | {o.operation} | {', '.join(o.requirements) or '—'} |"
            for o in of_family
        ]
        lines.append("")
    return lines


def _document(ops: list[Operation], cited: set[str], everything: dict[str, str]) -> list[str]:
    missing: dict[str, list[str]] = defaultdict(list)
    for identifier in sorted(set(everything) - cited):
        missing[identifier.split("-")[1]].append(identifier)
    lines = [
        "# Inventaire des endpoints",
        "",
        "Établi depuis `openapi.yaml` par `tools/inventory.py`, et régénérable par",
        "`make inventory`. La colonne « Exigences » ne donne que celles que l'opération",
        "cite dans ses propres mots, résumé ou description ; les paramètres, les corps et",
        "les réponses en citent d'autres, comptées dans la couverture ci-dessous mais pas",
        "dans le tableau.",
        "",
        (
            f"**{len(ops)} opérations sur {len({o.path for o in ops})} chemins, "
            f"dans {len(FAMILIES)} familles.**"
        ),
        (
            f"Le contrat cite **{len(cited & set(everything))} des {len(everything)} exigences** "
            "de la spécification."
        ),
        "",
        *_table(ops),
        "## Exigences que le contrat ne cite pas",
        "",
        (
            f"{sum(len(v) for v in missing.values())} sur {len(everything)}. Aucune n'est un "
            "oubli : ce sont celles qui n'ont pas de"
        ),
        "surface d'interface, et il vaut mieux qu'elles n'en aient pas.",
        "",
        "| Domaine | Exigences | Pourquoi aucune surface d'API |",
        "|---|---|---|",
    ]
    lines += [
        f"| {domain} | {', '.join(missing[domain])} | {REASONS.get(domain, 'à expliquer')} |"
        for domain in sorted(missing)
    ]
    return lines


def main() -> int:
    """Regenerate INVENTORY.md, and fail on an undeclared silence."""
    if not projection.PROJECTION.exists():
        print(f"specification not found: {projection.PROJECTION}", file=sys.stderr)
        return 1
    ops = list(operations())
    contract = "".join(f.read_text(encoding="utf-8") for f in ROOT.rglob("*.yaml"))
    cited = set(RE_REQUIREMENT.findall(contract))
    everything = requirements_of_the_document()
    lines = _document(ops, cited, everything)
    (ROOT / "INVENTORY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"INVENTORY.md — {len(ops)} operations, "
        f"{len(cited & set(everything))}/{len(everything)} requirements cited"
    )
    uncited_domains = {identifier.split("-")[1] for identifier in set(everything) - cited}
    undeclared = sorted(domain for domain in uncited_domains if domain not in REASONS)
    silent = [o for o in ops if not o.requirements and o.identifier not in NO_REQUIREMENT]
    for domain in undeclared:
        print(f"  ! domain with no declared reason: {domain}", file=sys.stderr)
    for o in silent:
        print(
            f"  ! operation citing no requirement: {o.identifier} ({o.method} {o.path})",
            file=sys.stderr,
        )
    return 1 if undeclared or silent else 0


if __name__ == "__main__":
    sys.exit(main())
