---
id: EP-12
titre: Échanger le planning avec MS Project, le devis et le reste à engager avec Excel
statut: à planifier
depend_de: EP-09
issue:
---

# EP-12 — Échanges de fichiers (FLX-01 à FLX-06)

## Objet

L'import et l'export du planning au format MS Project, de 2007 à 2024, et leur
réversibilité ; l'import et l'export du devis et du reste à engager aux formats Excel de
l'annexe B. Un import s'applique à la révision en cours, et en crée une s'il le faut ; il suit la
mécanique en deux temps construite en EP-09.

Il vient une fois que les données échangées existent. Il clôt les usages du chef de projet, qui
vont jusqu'aux sept flux (WF-INTF-0010), le rendu des comptes rendus d'import dans la langue du
lecteur (WF-ARC-0110), et les formats d'échange indépendants de la langue (WF-INTF-0180).

## Ce qui en fait partie

- l'import et l'export MS Project (FLX-01, FLX-02) et leur réversibilité ;
- l'import et l'export du devis (FLX-03, FLX-04) et du reste à engager (FLX-05, FLX-06) ;
- les formats de l'annexe B, leur version, et le refus d'un format ou d'une version inconnus ;
- le compte rendu et la confirmation de chaque import, et l'idempotence de leur application ;
- l'application à la révision en cours, créée au besoin depuis la dernière révision marquée ;
- les écrans d'import et d'export de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- l'import des coûts réels (FLX-07) — EP-09 ;
- tout autre échange : la liste des flux est fermée (WF-INTF-0150).

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-INTF-0150-A` | Liste fermée des échanges externes | entière | — |
| `WF-INTF-0010-A` | Usages du chef de projet | fin — amorcée en EP-06 | — |
| `WF-INTF-0040-A` | Imports MS Project | entière | — |
| `WF-INTF-0050-A` | Exports MS Project | entière | — |
| `WF-INTF-0060-A` | Réversibilité de l’échange MS Project | entière | — |
| `WF-INTF-0070-A` | Formats d’échange Excel | fin — amorcée en EP-09 | — |
| `WF-INTF-0080-A` | Contrôle et confirmation des imports Excel | fin — amorcée en EP-09 | — |
| `WF-INTF-0090-A` | Imports et révisions marquées | entière | — |
| `WF-INTF-0100-A` | Import du devis (FLX-03) | entière | — |
| `WF-INTF-0110-A` | Export du devis (FLX-04) | entière | — |
| `WF-INTF-0120-A` | Import du reste à engager (FLX-05) | entière | — |
| `WF-INTF-0130-A` | Export du reste à engager (FLX-06) | entière | — |
| `WF-INTF-0180-A` | Formats indépendants de la langue | fin — amorcée en EP-02 | — |
| `WF-ARC-0110-A` | Le texte est rendu au plus près du lecteur | fin — amorcée en EP-03 | — |
| `WF-DAT-0110-A` | Idempotence garantie par la base | fin — amorcée en EP-09 | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (0) :

aucune.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (6) :

- `exchanges` : `listImports`, `openImport`, `getImport`, `abandonImport`, `applyImport`, `requestExport`.

## Préalables

EP-09 livré : la mécanique d'import en deux temps, et les données du reste à engager.

## Définition de fini

- un fichier conforme à chacun des formats de l'annexe B est accepté ; un fichier sans version,
  ou d'une version inconnue, est refusé en nommant le format et la version attendus ;
- un planning exporté vers MS Project puis réimporté satisfait la réversibilité de
  WF-INTF-0060 ;
- un import sur un projet dont toutes les révisions sont marquées crée une révision en cours
  et s'y applique ;
- un compte rendu d'import produit en français se relit en anglais ;
- chaque fonction d'import ou d'export correspond à un flux du tableau ;
- le parcours de bout en bout joue les sept flux, contre le service réel.
