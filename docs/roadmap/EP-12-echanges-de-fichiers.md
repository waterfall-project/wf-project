---
id: EP-12
titre: Échanger le planning avec MS Project, le devis et le reste à engager avec Excel
statut: abandonné : chaque aller-retour se valide dans son bloc fonctionnel — MS Project en EP-06, le devis en EP-07, le reste à engager en EP-09
depend_de: EP-09
famille: front, back
issue:
---

# EP-12 — Échanges de fichiers (FLX-01 à FLX-06)

## Objet

Cet EPIC portait l'import et l'export du planning au format MS Project, du devis et du reste à
engager aux formats Excel de l'annexe B, une fois toutes les données échangées construites.

## Pourquoi il est abandonné

Revue de la ventilation, décision de l'auteur du 2026-10-09. Un échange se valide avec la
fonction qu'il alimente : l'aller-retour MS Project avec le planning, celui du devis avec le
chiffrage, celui du reste à engager avec l'estimation du reste. Les reporter en fin de parcours
faisait attendre jusqu'au dixième EPIC l'import du premier planning, qui « vient souvent de MS
Project » (motif de WF-INTF-0040), et laissait les blocs fonctionnels se livrer sans leur
format d'échange. La mécanique d'import en deux temps se construit avec le premier import,
celui de MS Project (EP-06), et non plus avec celui des coûts réels (EP-09).

## Où sont allées ses exigences

| Exigence | Va à |
|---|---|
| WF-INTF-0040-A, WF-INTF-0050-A, WF-INTF-0060-A — MS Project et sa réversibilité | EP-06, entières |
| WF-ARC-0100-A — import en deux temps | EP-06, entière (auparavant EP-09) |
| WF-ARC-0110-A — compte rendu d'import lu dans la langue du lecteur | close en EP-06, amorcée en EP-03 |
| WF-DAT-0120-A — contenu et purge du stockage objet | close en EP-06, amorcée en EP-03 (auparavant EP-09, EP-13) |
| WF-INTF-0080-A — contrôle et confirmation des imports | amorcée en EP-06, close en EP-07 |
| WF-INTF-0090-A — imports et révisions marquées | amorcée en EP-06, close en EP-07 |
| WF-INTF-0100-A, WF-INTF-0110-A — import et export du devis | EP-07, entières |
| WF-INTF-0180-A — formats indépendants de la langue | close en EP-07, amorcée en EP-02 |
| WF-INTF-0070-A — formats Excel de l'annexe B | amorcée en EP-07, close en EP-09 |
| WF-DAT-0110-A — idempotence garantie par la base | amorcée en EP-07, close en EP-09 |
| WF-INTF-0120-A, WF-INTF-0130-A — import et export du reste à engager | EP-09, entières |
| WF-INTF-0010-A — usages du chef de projet | close en EP-10, dernière fonction de son Vérif |
| WF-INTF-0150-A — liste fermée des échanges externes | EP-11, entière : le dernier EPIC qui ajoute un export |

Les opérations d'échange — `uploadFile`, `listImports`, `openImport`, `getImport`,
`abandonImport`, `applyImport`, `requestExport` — sont servies d'abord par EP-03 (le dépôt
d'une sauvegarde) et EP-06, puis reprises par EP-07 et EP-09.

## Exigences réalisées

Aucune : voir ci-dessus.

## Opérations du contrat

Aucune : voir ci-dessus.
