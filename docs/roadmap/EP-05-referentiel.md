---
id: EP-05
titre: Décrire l'entreprise que les projets emploient : organisation, ressources, calendriers, coûts
statut: à planifier
depend_de: EP-03
famille: front, back
issue:
---

# EP-05 — Référentiel de l'entreprise

## Objet

Le référentiel commun (FBS-3) : l'arbre d'organisation, les rôles de ressources et leur
capacité, les calendriers, les natures et catégories de coût, les taux horaires annuels, la
matrice de risques, les seuils d'alerte des indices, le délai maximal entre deux revues et la
devise. Aucun de ces objets ne se supprime : il se désactive.

Il vient avant les projets parce qu'un projet ne se crée pas sans lui (WF-CYC-0120) : il y faut
un calendrier par défaut, une catégorie de coût et un rôle de ressource. Plusieurs de ses
exigences ne se vérifient pourtant que sur des révisions chiffrées — la désactivation et la
modification sans effet sur les projets (WF-REF-0020, WF-REF-0130) : elles s'écrivent ici et se
closent en EP-07.

## Ce qui en fait partie

- l'arbre d'organisation, sa désactivation en cascade, et le rattachement d'un compte à un
  nœud, qui n'accorde aucune permission ;
- les rôles de ressources, leurs rattachements et leur capacité ;
- les calendriers, le calendrier par défaut, et celui que crée l'installation (WF-EXP-0020) ;
- les natures et catégories de coût, les taux horaires annuels et le taux de l'année en cours ;
- la matrice de risques, les seuils d'alerte des indices, le délai maximal entre deux revues et
  la devise de l'installation ;
- la désactivation à la place de la suppression, et l'affichage des objets désactivés ;
- les usages du manager sur le référentiel (WF-INTF-0020) ;
- les écrans du référentiel de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- l'emploi de ces objets par les projets : leur conservation dans une révision, l'absence
  d'effet d'une désactivation ou d'une modification sur une révision marquée — EP-07, où les
  révisions portent des montants ;
- l'application des seuils aux indices — EP-10 ; le signalement des projets en retard de
  revue — EP-11 ; le portefeuille, second usage du manager — EP-11 ;
- l'import du référentiel par fichier : aucun flux du tableau ne le prévoit (WF-INTF-0150).

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-INTF-0020-A` | Usages du manager | début — close en EP-11 | — |
| `WF-ADM-0030-A` | Rattachement d’un utilisateur à l’organisation | entière | — |
| `WF-REF-0010-A` | Désactivation plutôt que suppression | entière | — |
| `WF-REF-0020-A` | Désactivation sans effet sur les projets | début — close en EP-07 | — |
| `WF-REF-0130-A` | Modification sans effet rétroactif | début — close en EP-07 | — |
| `WF-REF-0150-A` | Affichage des objets désactivés | entière | — |
| `WF-REF-0140-A` | Devise de l’installation | début — close en EP-07 | — |
| `WF-REF-0030-A` | Natures de coût | entière | — |
| `WF-REF-0040-A` | Catégories de coût | entière | — |
| `WF-REF-0050-A` | Taux horaires annuels | entière | — |
| `WF-REF-0060-A` | Taux de l’année en cours | entière | — |
| `WF-REF-0070-A` | Arbre d’organisation | entière | — |
| `WF-REF-0080-A` | Désactivation en cascade | entière | — |
| `WF-REF-0090-A` | Rattachements d’un rôle de ressource | entière | — |
| `WF-REF-0100-A` | Capacité d’un rôle | entière | — |
| `WF-REF-0110-A` | Contenu d’un calendrier | entière | — |
| `WF-REF-0120-A` | Calendrier par défaut | entière | — |
| `WF-REF-0160-A` | Matrice de risques | entière | — |
| `WF-REF-0170-A` | Seuils d’alerte des indices | début — close en EP-10 | — |
| `WF-REF-0180-A` | Délai maximal entre deux revues | début — close en EP-11 | — |
| `WF-EXP-0020-A` | Amorçage d'une installation neuve | début — close en EP-04 | — |
| `WF-ADM-0020-A` | Aucune action réservée à un acteur | fin — amorcée en EP-03 | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (25) :

- `reference` : `getReferenceSettings`, `updateReferenceSettings`, `listOrgNodes`, `createOrgNode`, `updateOrgNode`, `setOrgNodeActivation`, `listResourceRoles`, `createResourceRole`, `updateResourceRole`, `setResourceRoleActivation`, `listCalendars`, `createCalendar`, `updateCalendar`, `setDefaultCalendar`, `setCalendarActivation`, `listCostTypes`, `createCostType`, `updateCostType`, `setCostTypeActivation`, `listCostCategories`, `createCostCategory`, `updateCostCategory`, `setCostCategoryActivation`, `listHourlyRates`, `setHourlyRate`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (2) :

- `access` : `listUsers`, `getUser`.

## Constats reçus

- #351 — un chiffreur sans permission du référentiel ne peut saisir ni catégorie ni rôle :
  la garde de `include_inactive` sur les lectures du référentiel, reportée d'EP-03 par son
  cadrage (2026-10-07).
- #299 — ajouter une année à la grille des taux horaires (WF-REF-0060) : la commande appartient
  au référentiel réel, reportée d'EP-02 (2026-10-07).
- #300 — les écrans du référentiel ne montrent ni ne réactivent les objets désactivés
  (WF-REF-0150), reportée d'EP-02 (2026-10-07).

## Préalables

EP-03 livré : chaque écriture du référentiel est évaluée contre une permission.

## Définition de fini

- chaque objet du référentiel se crée, se modifie et se désactive depuis son écran, et aucune
  commande ne le supprime ;
- la désactivation d'un nœud d'organisation se propage comme WF-REF-0080 le fixe ;
- un objet désactivé reste affiché là où il est employé et n'est plus proposé à la saisie ;
- un compte rattaché à un nœud n'y gagne aucun accès ;
- les exemples chiffrés des Vérif du §3.4.4 sont des tests qui passent (WF-QUA-0020) ;
- le parcours de bout en bout traverse le référentiel contre le service réel.
