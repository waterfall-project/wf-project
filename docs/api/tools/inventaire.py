#!/usr/bin/env python3
"""Régénère INVENTAIRE.md depuis le contrat.

Une ligne par opération, avec les exigences que sa description cite, puis la
couverture : combien d'exigences de la spécification le contrat cite, et
lesquelles il ne cite pas — avec, pour chaque domaine, la raison pour laquelle
il n'a pas à les citer.
"""
import collections
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
SPEC = RACINE.parent / "spec" / "waterfall-spec.md"

FAMILLES = [
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

RAISONS = {
    "ARC": "Choix d'architecture interne : noyau unique, rôles des composants de données, "
           "empaquetage, autorité du serveur, absence d'état. Ils se vérifient sur le dépôt "
           "et le déploiement.",
    "CMP": "Compatibilité des navigateurs et largeurs d'affichage : propriété du front.",
    "DAT": "Partitionnement et migrations : propriétés du schéma, invisibles du contrat.",
    "EXP": "Exploitation : environnements, amorçage, mise à jour, perte maximale. Aucune "
           "n'est une opération d'API.",
    "IHM": "Invariants d'interface : navigation, saisie au clavier, accessibilité. Ils "
           "vivent dans le front.",
    "INTF": "Les trois usages d'acteurs décrivent le contenu des rôles prédéfinis, servi par "
            "le catalogue des permissions ; la règle de traduction vit dans le front.",
    "QUA": "Chaîne de vérification : tests, analyse statique, jeu de données, mesures. Elle "
           "s'exerce sur le contrat, elle n'y figure pas.",
}

RE_OPERATION = re.compile(
    r"^  (get|post|put|patch|delete):\n(.*?)(?=\n  [a-z]+:\n|\Z)", re.S | re.M
)


def operations():
    """Chaque opération du contrat, dans l'ordre des familles puis des chemins."""
    for famille, _ in FAMILLES:
        fichier = RACINE / "paths" / f"{famille}.yaml"
        for bloc in re.split(r"\n(?=/)", fichier.read_text(encoding="utf-8")):
            entete = re.match(r"^(/[^\s:]*):", bloc)
            if not entete:
                continue
            for trouve in RE_OPERATION.finditer(bloc):
                corps = trouve.group(2)
                lire = lambda motif: (re.search(motif, corps) or [None, ""])[1]
                yield {
                    "famille": famille,
                    "chemin": entete.group(1),
                    "methode": trouve.group(1).upper(),
                    "operation": lire(r"summary: (.*)").strip().strip("'")
                    or lire(r"operationId: (\w+)"),
                    "exigences": sorted(set(re.findall(r"WF-[A-Z]+-\d{4}", corps))),
                }


def exigences_du_document():
    """Identifiant et titre de chaque exigence, l'exemple du §1.3.1 excepté."""
    texte = SPEC.read_text(encoding="utf-8")
    trouvees = {}
    for bloc in re.findall(r"```yaml exigence\n(.*?)```", texte, re.S):
        lire = lambda champ: (re.search(rf'^{champ}: "(.*)"$', bloc, re.M) or [None, ""])[1]
        if lire("id") != "WF-EXAMP-0010-A":
            trouvees[lire("id")[:-2]] = lire("titre")
    return trouvees


def main():
    if not SPEC.exists():
        print(f"spécification introuvable : {SPEC}", file=sys.stderr)
        return 1

    ops = list(operations())
    citees = set(re.findall(r"WF-[A-Z]+-\d{4}", "".join(
        f.read_text(encoding="utf-8") for f in RACINE.rglob("*.yaml"))))
    toutes = exigences_du_document()
    manquantes = collections.defaultdict(list)
    for identifiant in sorted(set(toutes) - citees):
        manquantes[identifiant.split("-")[1]].append(identifiant)

    lignes = [
        "# Inventaire des endpoints",
        "",
        "Établi depuis `openapi.yaml` par `tools/inventaire.py`, et régénérable par",
        "`make inventaire`. La colonne « Exigences » donne celles que la description de",
        "l'opération cite ; les schémas en citent d'autres, comptées dans la couverture",
        "ci-dessous mais pas dans le tableau.",
        "",
        f"**{len(ops)} opérations sur {len({o['chemin'] for o in ops})} chemins, "
        f"dans {len(FAMILLES)} familles.**",
        f"Le contrat cite **{len(citees & set(toutes))} des {len(toutes)} exigences** "
        "de la spécification.",
        "",
    ]
    for famille, titre in FAMILLES:
        fam = [o for o in ops if o["famille"] == famille]
        lignes += [
            f"## {titre}", "", f"`paths/{famille}.yaml` — {len(fam)} opérations", "",
            "| Méthode | Chemin | Opération | Exigences citées |", "|---|---|---|---|",
        ]
        lignes += [
            f"| {o['methode']} | `{o['chemin']}` | {o['operation']} | "
            f"{', '.join(o['exigences']) or '—'} |" for o in fam
        ]
        lignes.append("")
    lignes += [
        "## Exigences que le contrat ne cite pas",
        "",
        f"{sum(len(v) for v in manquantes.values())} sur {len(toutes)}. Aucune n'est un "
        "oubli : ce sont celles qui n'ont pas de",
        "surface d'interface, et il vaut mieux qu'elles n'en aient pas.",
        "",
        "| Domaine | Exigences | Pourquoi aucune surface d'API |", "|---|---|---|",
    ]
    inconnus = [d for d in manquantes if d not in RAISONS]
    lignes += [
        f"| {domaine} | {', '.join(manquantes[domaine])} | "
        f"{RAISONS.get(domaine, 'à expliquer')} |" for domaine in sorted(manquantes)
    ]

    (RACINE / "INVENTAIRE.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"INVENTAIRE.md — {len(ops)} opérations, "
          f"{len(citees & set(toutes))}/{len(toutes)} exigences citées")
    for domaine in inconnus:
        print(f"  ! domaine sans raison déclarée : {domaine}", file=sys.stderr)
    return 1 if inconnus else 0


if __name__ == "__main__":
    sys.exit(main())
