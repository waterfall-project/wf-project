---
id: EP-11
titre: Voir l'ensemble des projets : valeur, charge, performance, risques, courbe en S, santé
statut: en cours
depend_de: EP-08
famille: front, back
issue: 3856
---

# EP-11 — Portefeuille

## Objet

Les vues du portefeuille (FBS-2), en consultation seule, calculées sur un périmètre et à une
date : la liste des projets, la valeur et le pipeline pondéré, le plan de charge agrégé, les
indices et projections, la structure des coûts, les risques, la courbe en S et la santé du
pilotage. Une grandeur de portefeuille est une somme, un indice un rapport de sommes — jamais
une moyenne d'indices —, et un projet en chiffrage compte au prorata de sa probabilité de gain.

C'est le dernier calcul. Deux exigences d'EP-01 s'y closent donc : chaque exemple chiffré du
document a son test (WF-QUA-0020), et la « seule implémentation » de chaque calcul se constate
sur un dépôt qui les porte tous (WF-ARC-0010).

## Ce qui en fait partie

- le périmètre choisi — projets en cours, en chiffrage, terminés d'une période — et la date de
  calcul ;
- à une date passée, la lecture des indicateurs conservés, sans rien recalculer, et ce que le
  marquage conserve de plus pour elle : la charge par rôle et par mois, les totaux par nature et
  par nœud d'organisation, les risques ;
- la règle d'agrégation et la pondération par la probabilité de gain ;
- les vues de FBS-2.1 à FBS-2.7, et le filtre par nœud d'organisation ;
- les filtres de la liste des projets sur chacune de ses colonnes, par une modification du contrat
  (décision de l'auteur du 2026-11-17) ;
- la santé du pilotage, avec le délai maximal entre deux revues ;
- les usages du manager sur le portefeuille (WF-INTF-0020) ;
- les écrans du portefeuille de la maquette, branchés sur le service ;
- l'aide en ligne de chaque écran, infobulle de la colonne corrigée de l'inflation comprise
  (WF-IHM-0140), parce que c'est ici que le dernier écran se branche ;
- sa tranche du jeu de données de référence (WF-QUA-0040) — une dizaine de projets à côté de
  PRJ-001 et de PRJ-002, pour que chaque vue ait de quoi sommer : des offres, un projet terminé, une
  offre perdue, des projets en cours — chargée par `waterfall-api load-witness` (décision de
  l'auteur du 2026-11-17) ;
- les constats reçus, soldés, ou reportés à l'EPIC qui touche leur code (« Reprise du 2026-11-21
  soir »).

## Ce qui n'en fait pas partie

- tout export du portefeuille : aucun flux du tableau ne le prévoit (WF-INTF-0150) ;
- les trois cents projets du jeu de données de référence, et la mesure des vues à cette échelle —
  EP-13, qui rejoue dessus l'outil d'EP-26 (WF-QUA-0060) et les tests de la lecture conservée ;
- la reprise des révisions marquées avant cet EPIC : elles ne conservent pas ce que le portefeuille
  lit de plus, et rien ne le recalcule (décision de l'auteur du 2026-11-17) ;
- reportés le 2026-11-21 soir (« Reprise du 2026-11-21 soir ») : les tests du harnais qui manquent
  aux exemples chiffrés et le contrôle qui échoue sur un exemple sans test (US-2780/L2, EP-36) ; la
  reprise des doublons du noyau (US-2780/L4, retiré : EP-35 et EP-34) ; la mesure des huit vues
  (US-2790, EP-40).

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
WF-DAT-0040 est commencée par EP-04 et EP-10 et close ici : son Vérif demande une vue de
portefeuille à une date passée sur trois cents projets, risques compris, qui ne lit ni ligne de
tâche ni ligne de devis — EP-10 conserve au marquage les indicateurs et les courbes, EP-11 conserve
de plus ce que le portefeuille lit, la charge par rôle et par mois, les totaux par nature et par
nœud d'organisation et les risques, par un second enregistrement de `register_indicators` (cadrage
d'EP-10, décision de l'auteur du 2026-11-07). WF-QUA-0020 se clôt sur les calculs du noyau, que le
corps de l'exigence nomme : les exemples chiffrés qui n'en sont pas — exploitation, observabilité,
front — sont déclarés hors du harnais, chacun avec sa raison et l'EPIC qui le prouve autrement
(décision de l'auteur du 2026-11-17). WF-QUA-0040 entre au tableau en portée « début », comme en
EP-10 et en EP-08 : cet EPIC charge une tranche du jeu de données de référence, qu'EP-13 clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-INTF-0020-A` | Usages du manager | fin — amorcée en EP-05 | US-2770 |
| `WF-DAT-0040-A` | Conservation des indicateurs des révisions marquées | fin — amorcée en EP-04, EP-10 | US-2680 |
| `WF-PTF-0010-A` | Périmètre et date de calcul du portefeuille | entière | US-2670 |
| `WF-PTF-0020-A` | Règle d’agrégation | entière | US-2670 |
| `WF-PTF-0030-A` | Vues en consultation seule | entière | US-2670 |
| `WF-PTF-0040-A` | Liste des projets | entière | US-2690 |
| `WF-PTF-0050-A` | Valeur du portefeuille | entière | US-2690 |
| `WF-PTF-0060-A` | Plan de charge agrégé | fin — amorcée en EP-15 | US-2700 |
| `WF-PTF-0070-A` | Indices et projections du portefeuille | entière | US-2710 |
| `WF-PTF-0080-A` | Structure des coûts du portefeuille | entière | US-2720 |
| `WF-PTF-0090-A` | Risques du portefeuille | entière | US-2730 |
| `WF-PTF-0100-A` | Courbe en S du portefeuille | entière | US-2740 |
| `WF-PTF-0110-A` | Santé du pilotage | entière | US-2750 |
| `WF-REF-0180-A` | Délai maximal entre deux revues | fin — amorcée en EP-05 | US-2750 |
| `WF-PRJ-0090-A` | Probabilité de gain | fin — amorcée en EP-04 | US-2670 |
| `WF-ARC-0010-A` | Un noyau, un service, un worker | fin — amorcée en EP-01 | US-2780 |
| `WF-QUA-0020-A` | Les exemples chiffrés du document sont des cas de test | fin — amorcée en EP-01 | US-2780 |
| `WF-IHM-0130-A` | Filtrage des tables et export des graphiques | fin — amorcée en EP-02, EP-03, EP-15, EP-25 | US-2760 |
| `WF-IHM-0140-A` | Aide en ligne | fin — amorcée en EP-15, poursuivie en EP-16 | US-2760 |
| `WF-INTF-0150-A` | Liste fermée des échanges externes | entière | US-2780 |
| `WF-REF-0070-A` | Arbre d'organisation | fin — amorcée en EP-05 | US-2700 |
| `WF-REF-0100-A` | Capacité d'un rôle | fin — amorcée en EP-05, EP-10 | US-2700 |
| `WF-CYC-0130-A` | Datation des transitions | fin — amorcée en EP-04 | US-2670 |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13, amorcée aussi en EP-05, EP-04, EP-06, EP-07, EP-09, EP-10, EP-08 | US-2770 |

## Opérations du contrat

Une modification du contrat précède le code qui la consomme : `getPortfolioProjects` reçoit un
filtre par colonne de sa liste — le code, les bornes des montants, de la probabilité de gain et des
indices, la période de la dernière révision marquée —, sur le modèle des tables plates (décision de
l'auteur du 2026-11-17, contre le gel du contrat par EP-16 ; WF-IHM-0130). Aucune opération ne
manque.

Servies ici pour la première fois (8) :

- `portfolio` : `getPortfolioProjects`, `getPortfolioValue`, `getPortfolioWorkload`, `getPortfolioPerformance`, `getPortfolioCostStructure`, `getPortfolioRisks`, `getPortfolioCostCurve`, `getPortfolioPilotHealth`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute :

- `reference` : `getReferenceSettings`, `updateReferenceSettings` (le délai maximal entre deux
  revues), `updateOrgNode` (le déplacement d'un nœud, devant le plan de charge agrégé) ;
- `projects` : `listProjects`, `updateProject`, `listProjectStateTransitions` ;
- `revisions` : `markRevision`, `mergeCostStructure` — ce que le marquage conserve de plus ;
- `me` : `getMe`, `updateMyPreferences` — le seuil, le filtre et l'horizon du plan de charge agrégé.

## Constats reçus

- #301 — les tables du référentiel n'offrent aucun filtre ; WF-IHM-0130, les filtres de toute
  table, se clôt ici, reportée d'EP-02 (2026-10-07).
- #313 — la liste du portefeuille n'offre pas le filtre par zone (WF-IHM-0130), reportée
  d'EP-02 (2026-10-07), puis rangée dans EP-02/L41 (2026-10-08) : fait par EP-02/L41, qui offre
  le filtre par zone au-dessus de la grille des projets, porté par l'adresse (`zones`).
- #1714 — contrat : aucun exemple de `getPortfolioWorkload` ni de `getPortfolioPilotHealth` ne
  retient `completed`, l'avis de G-05 à vérifier sur le service réel, qui sert ici ces deux
  opérations. Reporté d'EP-04 par l'auteur le 2026-11-06 : EP-04 ne sert aucune des deux.
- #2867 — front : la copie privée d'`identifierOf` dans `components/portfolio/address.ts` laisse
  passer un identifiant de l'adresse qui n'est pas un UUID, que le service refuse par 422. Relevé au
  cadrage d'EP-23, qui corrige la fonction du référentiel (US-1770, #2269) ; reporté ici par
  l'auteur le 2026-11-11, rattaché à EP-23 (#2858) jusqu'à l'ouverture de l'issue d'EP-11.
- #3341 — back : `ALL_PROJECTS_READ` défini deux fois, dans `access_roles` et dans l'interface des
  projets. Relevé par la revue d'US-2210/L1 d'EP-26 ; reporté ici par l'auteur le 2026-11-15 :
  l'EPIC qui lit l'ensemble des projets sur un périmètre.
- #3549 — back : la table `revision_indicator` d'EP-10 engage EP-11 : son déclencheur différé
  refuse une ligne dont `computed_at` n'est pas le `marked_at` de sa révision (un document conservé
  au marquage se calcule à l'instant du marquage, `act.at`), et son contrôle `kind_known` borne
  `kind` aux natures d'EP-10, qu'une migration devra élargir pour admettre des natures nouvelles.
  Relevé par la revue d'US-1660/L1 d'EP-10 (#2437) ; reporté ici le 2026-11-15 (2026-11-16 selon
  epic/EP-10), noté au cadrage du 2026-11-17, rattaché à US-1660/L1 (#2437) jusqu'à l'ouverture de
  l'issue d'EP-11.
- #3355 — back : le rôle prédéfini « chef de projet » porte `portfolio_projects.read`, que
  WF-INTF-0010 ne lui donne pas : le jour où la liste du portefeuille est servie, tout chef de
  projet lirait le libellé, le code, l'état, le budget et les indices de tous les projets. Relevé
  par la revue complète du 2026-11-14 (SPA-06) ; décision de l'auteur du 2026-11-18, au tri des
  constats de spécification : le chef de projet ne lit pas le portefeuille, et le rôle amorcé perd
  cette permission (US-2690).
- #3351 — spécification : la santé du pilotage prenait son repère « depuis la dernière révision
  marquée », après les actes qu'il doit constater, si bien que tout projet sain y figurait deux
  fois. Relevé par la revue complète du 2026-11-14 (SPA-03) ; décision de l'auteur du 2026-11-18 :
  les deux signaux se mesurent entre l'avant-dernière et la dernière révision marquée (spécification
  1.0.7, WF-PTF-0110 ; US-2750).

## Préalables

`epic/EP-11` se tire d'`epic/EP-08`, dès la fusion de son socle, US-2550/L1 (#3822), qui lui donne
la migration des risques, `core/risks` et son interface déclarée : c'est l'exception du README
(« Branches »), décidée par l'auteur au cadrage du 2026-11-17. Elle reprend `epic/EP-08` à chaque
lot que celui-ci fusionne, chaîne sa migration sur la dernière qu'elle y trouve, et se fusionne dans
`main` après EP-08, jamais avant. Ses lots qui lisent les risques attendent par leur numéro les lots
d'EP-08 qui les servent : le registre et la matrice, la réserve et la couverture, les réexamens.
EP-10 et EP-27 sont dans `main` avant qu'`epic/EP-08` ne se tire : le portefeuille agrège les
indicateurs, conservés ou calculés, et les risques, leurs provisions et leur couverture.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.3, de WF-PRJ-0090, de WF-CYC-0130 et de WF-REF-0100 sont
  des tests qui passent ;
- un portefeuille calculé à une date passée ne change pas quand une révision est marquée
  après cette date, et aucune de ses vues ne lit alors de ligne de tâche ni de ligne de devis ;
- le parcours de bout en bout ouvre chacune des vues du portefeuille, contre le service réel, sur le
  témoin chargé avec la tranche du portefeuille, et le manager y ouvre un projet dont il n'est pas
  contributeur ;
- le témoin se charge une fois par session des tests du back, dans une base modèle que chaque test
  copie, et chaque part de `back.yml` tient sous son délai de 20 minutes, mesuré en CI (US-2770/L2b,
  #4653 ; reformulé le 2026-11-22, #4674).

## Conception

Écrite au cadrage du 2026-11-17, sur le code de `main` et d'`epic/EP-10` à cette date, et sur la
conception d'EP-08, dont aucun lot n'est encore livré. Elle dit ce qu'un lot devrait sinon décider
seul ; ce qui relève d'un lot reste au lot.

### Ce que le cadrage décide

Décisions de l'auteur du 2026-11-17, chacune avec l'option écartée :

- **Treize US, le socle en lot technique de la première** : la migration, le module
  `core/portfolio` à vide avec son interface déclarée, les huit routeurs vides, les fabriques des
  tests. Tout lot du back en dépend.
- **`epic/EP-11` se tire d'`epic/EP-08` dès son socle**, US-2550/L1 (« Préalables »). Écartée : la
  règle, qui mettait deux EPIC en série quand les vues qui ne lisent aucun risque n'attendent rien
  d'EP-08.
- **Le module est `core/portfolio`** (FBS-2), au sommet des modules du domaine : il importe les
  interfaces des indicateurs, des risques, du devis, des coûts, du planning, des révisions, des
  projets et des réglages, et aucun ne l'importe. Écartés : étendre `core/indicators`, qui est
  FBS-4.8 et mêlerait le projet à l'ensemble, contre le découpage par bloc de WF-ARC-0010 ; une
  requête d'agrégation sur les tables des autres modules, que le guide interdit.
- **Le portefeuille somme des contributions, il ne lit jamais les lignes d'un projet** : chaque
  projet donne, par révision, des documents — ceux d'EP-10 et ceux qu'ajoute cet EPIC —, conservés
  au marquage et, au jour courant, calculés une fois et gardés par le cache d'EP-10. Les huit vues
  ne font que choisir, pondérer et sommer ces documents, de la même façon aux deux dates. Écartés :
  un calcul d'ensemble par vue, qui lirait cinq mille lignes par projet à chaque ouverture ; une
  table d'agrégats du portefeuille tenue à l'écriture, que chaque saisie d'un projet devrait
  mettre à jour.
- **Les documents nouveaux vont dans `revision_indicator`**, sous des natures nouvelles qu'une
  migration admet (#3549), écrits par `core/indicators` à la demande de `core/portfolio`. Écartée :
  une table propre au portefeuille, un second mécanisme d'immuabilité et de refus hors marquage.
- **Une révision marquée avant cet EPIC ne reçoit rien** : ni reprise, ni repli sur un calcul à la
  lecture. Écartés : étendre au portefeuille le repli d'EP-10 (#3612, décision du 2026-11-17), qui
  ferait lire des lignes de tâche et de devis à une date passée, contre le Vérif de WF-DAT-0040 ;
  une reprise au déploiement, qui demanderait d'écrire dans `revision_indicator` hors d'un marquage
  et calculerait sur les coûts d'aujourd'hui.
- **Le contrat change sur un point, contre le gel d'EP-16** (décision du 2026-10-22) : les filtres
  par colonne de `getPortfolioProjects`. Écartés : tenir le seul Vérif de WF-IHM-0130 avec un constat
  de spécification ; filtrer dans le front une liste que le serveur pagine.
- **Le filtre par nœud d'organisation ne change aucun montant de la liste, de la valeur ni de la
  performance** : il y est retenu dans le périmètre rendu, et ne restreint que le plan de charge et
  la main-d'œuvre de la structure des coûts. La description de `PortfolioOrgNode` le dit. Écartés :
  restreindre ce qui se ventile par ligne, qui rapporterait une valeur acquise restreinte à un coût
  réel entier ; retirer le paramètre de ces trois vues, un changement d'écran de plus.
- **La tranche du témoin vit hors du contrat** : sa description et ses lectures attendues sont dans
  `fixtures/witness/portfolio/`, engendrées par `make mock-data`. Écartés : dix lignes de la liste à
  trois cents projets, dont il faudrait reproduire au centime les formules du générateur par un vrai
  saisi ; des exemples de plus au contrat figé.
- **Pas de préchauffage du cache** : la première lecture calcule ce qui manque ; US-2790 mesure à
  froid et à chaud, et EP-13 décide sur le jeu aux volumes. Écartés : une tâche planifiée du
  worker ; une durée de validité propre au portefeuille.
- **WF-QUA-0020 se clôt sur les calculs du noyau** : les autres exemples chiffrés du relevé sont
  déclarés hors du harnais. Écartés : déplacer la clôture à EP-13 ; clore sans le rattrapage des
  EPIC livrés.
- **Une somme de portefeuille est une somme de montants déjà arrondis** : chaque contribution est
  arrondie une fois, par projet, comme EP-10 l'arrondit — la part pondérée d'une offre au centime,
  un demi loin de zéro —, et le portefeuille n'arrondit que ses rapports, à quatre décimales. C'est
  ce qui tient « chaque point de la courbe agrégée égale la somme des points » au centime. Écarté :
  sommer des montants exacts et arrondir le total, qui s'écarterait de la somme des projets.
- **La main-d'œuvre est conservée par rôle, et groupée par nœud à la lecture**, sur l'arbre
  courant : un nœud déplacé emporte ses rôles dans le plan de charge agrégé (WF-REF-0070), et le
  libellé du nœud est résolu à la lecture, comme le contrat le dit de `PortfolioScope`. Écarté :
  conserver des totaux par nœud, qu'un déplacement laisserait sous l'ancien parent.
- **La case d'un risque et la zone d'un indice se classent à la lecture**, sur les bornes et les
  seuils courants du référentiel, pour un document conservé comme pour le jour courant (la règle
  d'EP-10 pour les zones). Écarté : conserver la case, qu'une borne déplacée rendrait fausse.
- **Le chef de projet ne lit pas le portefeuille** (décision de l'auteur du 2026-11-18, #3355) :
  le rôle prédéfini « chef de projet » perd `portfolio_projects.read`, à l'amorçage et, par une
  migration, sur une plateforme déjà installée ; le portefeuille reste au manager (WF-INTF-0020).
  WF-INTF-0010 ne nomme aucune vue du portefeuille parmi les usages du chef de projet, et la
  spécification fait foi. Écarté : garder la permission, les projets qu'il n'ouvre pas ne figurant
  que sous leur libellé et leur code (WF-PTF-0030) — ils y figureraient avec leur budget et leurs
  indices.

### Décisions de l'auteur du 2026-11-19

Prises pendant la livraison, sur les constats que les revues ont relevés ; chacune dit le lot ou la
section qui la porte, et rien d'autre dans la conception ne change.

- **Une liste lue sans période ne retient aucun projet terminé** (#4020 point 1, #4136) : voir « Les
  vues ». Déjà appliquée par US-2690/L2 (`docs/api/DECISIONS.md`). Le point 2 de #4020, les états
  que chaque vue compte, n'est pas tranché ici : chaque lot de vue fixe ses états d'après les
  documents, la liste suivant `PortfolioStates`.
- **Toute vue lit par `PortfolioReading(at, cache)`** (#4194) : voir « Les vues ».
- **`win_probability` vaut `null` pour un projet qui n'est pas une offre** (#4137) : un projet en
  cours ou terminé n'a pas de probabilité de gain dans la liste. L'exemple `portfolio_projects` du
  contrat, qui montre `"1"` pour un projet en cours, est aligné par US-2760/L2 #3884, avec les
  exemples qu'il touche déjà (#1714).
- **La période de `getPortfolioPerformance` est bornée par le contrat** (#4176) : au-delà de la durée
  maximale, 422 `VALUE_OUT_OF_RANGE` sur la période, au lieu d'une lecture par trimestre touché sans
  limite. Écartées : lire les documents conservés de tous les trimestres en une requête ; laisser
  tel quel et attendre la mesure. Porté par US-2670/L4 #3873, qui éprouve la règle des périodes sur
  les six vues. Le lot a proposé cinq ans (commentaire de #3873), **confirmés par l'auteur le
  2026-11-21** : `PERIOD_YEARS = 5`.
- **Un exemple de 422 de `getPortfolioProjects` sur la période du périmètre** (#4164) : période
  inversée avec `as_of`, champs `/query/from` et `/query/to`, au contrat, que le test de l'écran lit
  au lieu de composer ses champs. Porté par US-2760/L2 #3884.
- **L'empreinte de la contribution d'un projet couvre ce que la contribution lit** (#4158) : le nœud
  courant d'un rôle et la probabilité de gain d'une offre entrent dans l'empreinte par US-2680/L2
  #3880 ; les compteurs des risques par US-2680/L3 #3881. Aucune entrée ne tient plus que sa durée de
  validité là où une valeur change (WF-DAT-0130-A).
- **Une seule règle « qui peut ouvrir un projet »** (#4131) : `access_roles/evaluation.py` lit la
  règle de `Viewer.sees_all`, et non plus sa copie ; le jugement d'accès d'un projet et `can_open`
  du portefeuille ne peuvent plus diverger (WF-PTF-0030). Porté par US-2670/L4 #3873.
- **La copie d'`IDENTIFIER` de la navigation est corrigée** (#4160, `frontend/src/navigation/
  context.ts`) : un identifiant qui n'est pas un UUID est ignoré comme un identifiant absent, par la
  fonction du référentiel. Porté par US-2760/L2 #3884. La copie du registre des risques
  (`components/risks/address.ts`) reste à EP-08.
- **Le coût de la lecture du jour projet par projet est laissé à la mesure** (#4165, #4177) :
  `day_documents_of` (neuf requêtes par projet au cache chaud) et la performance au jour courant
  (`current_day_reading`, `day_indicators`) ne changent pas avant US-2790 ; si une vue du jour
  dépasse son objectif, le groupement des empreintes se fait en lot neuf. Écarté : grouper
  maintenant, ce qui toucherait les interfaces de cinq modules hors d'un lot de correction.
- **Les tests tiennent les fabriques du portefeuille** (#4051) : le PostgreSQL des tests monte
  `max_locks_per_transaction` (`deploy/compose/compose.test.yaml`, et le service de `back.yml`), et
  `drop_partitions` supprime les partitions projet par projet, une transaction chacun. Les deux
  leviers, non l'un des deux. Porté par US-2680/L2 #3880, que les lots de vue qui écrivent des
  tests sur les fabriques attendent tous, directement ou non.
- **Les exemples à barre oblique de WF-CRE-0020 et WF-PRJ-0050** (#4022) entrent au harnais avec le
  lot qui réalise #3966 : voir US-2780.

### Décisions de l'auteur du 2026-11-21

Prises sur les constats ouverts, en commentaire de leur issue ; chacune dit le lot qui la porte, et
rien d'autre dans la conception ne change.

- **Un lot neuf, US-2780/L4 « L'unique implémentation, reprise du noyau »** (#4372, #4373, #4363),
  après US-2780/L3 #3878, qui a posé le contrôle, et avant US-2790 #3868 et US-2770/L3 #3887, qui en
  dépendent désormais ; « pas avec » US-2770/L2 #3886, qui peut toucher les mêmes fichiers du noyau.
  Il fait tenir par le dépôt ce que le contrôle de L3 ne pouvait encore constater :
  - le calendrier des mois de `core/portfolio/aggregation/periods.py` importe celui de
    `core/indicators/series/months.py` par l'interface d'`indicators`, et l'exemption `[[duplicate]]`
    de `tools/implementations.toml` est retirée (#4372) ;
  - les trois calculs écrits deux fois dans le noyau n'ont plus qu'une définition, importée par
    l'interface : `quality_conditions` (`core/projects/commands.py`, `core/revisions/commands.py`),
    `month_of` (`core/estimate/disbursing.py`, `core/indicators/series/months.py`), `CENT`
    (`core/estimate/pricing/amounts.py`, `core/indicators/formulas/rounding.py`) (#4373) ;
  - **les arrondis de `api/nodes.py` (`_money`) et d'`api/comparison.py`** — `quantize(CENT)`, demi
    pair — **face à `round_to_cent`, demi supérieur** : le lot commence par un test qui dit si cela
    change une valeur réelle. Si oui, c'est un constat de contrat à ouvrir à part, non corrigé dans
    le lot sans décision (#4373) ;
  - les motifs `\d` d'`api/problems.py`, de `core/costs/extraction.py` et de
    `core/planning/interface/paste.py` n'acceptent plus les chiffres Unicode (`[0-9]` ou `re.ASCII`),
    un test par chemin (#4363).

  Écarté : corriger dans US-2780/L3, déjà fusionné ; un lot neuf garde la revue de ces reprises du
  noyau, qui changent des interfaces qu'EP-09 et EP-10 partagent, séparée de celle du contrôle.
- **La durée maximale de la performance est de cinq ans** (#4176, `PERIOD_YEARS = 5`) : voir
  « Décisions de l'auteur du 2026-11-19 ».
- **Le test des familles d'identifiants reconnaît la corrélation dérivée** d'un exemple d'erreur de
  `fixtures/api` (#4361, issue de #1007) : corrigé par US-2770/L3 #3887.
- **La courbe en S du jour ne re-choisit pas la révision que le périmètre a retenue** (#4339) :
  corrigé par US-2790 #3868.
- **Les trois gardes du test de la lecture conservée sont durcies** (#4360) : corrigé par
  US-2770/L2 #3886.

### Reprise du 2026-11-21 soir

Décisions de l'utilisateur, le pilote arrêté : la fusion d'EP-11 retient EP-30, EP-36, EP-37 et
EP-38, qui l'attendent ; ce qui ne tient pas à une fonction du portefeuille se reporte à l'EPIC
née de la ventilation du 2026-11-21 qui touche son code. Chaque issue reportée porte le label de
son EPIC et un commentaire ; son cadreur la rattache à un lot.

- **US-2770/L2** (#3886) est fusionné (#4571) avec un palliatif de la chaîne : `back.yml` en huit
  parts, délai de 25 minutes. Les tests du back coûtent treize fois plus qu'au 2026-11-07 (#4653).
- **Un lot neuf, US-2770/L2b** (#4657, #4653) : mesurer en CI le coût du témoin, et le charger une
  fois par session dans une base modèle, que chaque test copie (`CREATE DATABASE … TEMPLATE`), avec
  un délai par test (`pytest-timeout`) qui nomme un test figé ; la tranche reste chargée partout, sans
  variante optionnelle ; `back.yml` est ramené à ce que la mesure justifie (décision de l'utilisateur
  du 2026-11-21, #4657, options 1 et 4). Avant US-2770/L3, qui en dépend ; US-2760/L2, du front, part
  en parallèle.

### Reprise du 2026-11-22

Décisions de l'utilisateur, le pilote arrêté sur #4688 :

- **#4688** : les durées des parcours du service sont rafraîchies sur `epic/EP-11` par la reprise,
  depuis les journaux de la file de #4668 ; US-2770/L2b reprend ensuite sa chaîne.
- **#4674** : la conception de L2b est mise au texte de la décision du 2026-11-21 ; le critère de
  coût de la définition de fini se reformule — le témoin chargé une fois par session dans une base
  modèle, chaque part de `back.yml` sous son délai de 20 minutes —, et la mesure de L2b le constate.
  Le retour aux quatre parts d'US-1910 n'est plus visé par EP-11.
- **US-2760** : ses critères partis le 2026-11-21 soir (#1714, #4164, #4137 → EP-38 ; #4160 →
  EP-37) restent écrits, marqués reportés.
- **Sortis d'EP-11** : US-2780/L2 (#3877, avec #4021) → EP-36 ; US-2790 (#3868, avec #4165, #4177,
  #4313, #4339) → EP-40 ; US-2780/L4 (#4494) retiré avant tout commencement, #4372 et #4373 →
  EP-35, #4363 → EP-34. Les exigences WF-QUA-0020 et WF-ARC-0010 ne se closent donc plus ici.
- **Constats reportés** : #4547, #4374, #4361, #4163, #4548 → EP-36 ; #4507 (décidé : par libellé
  puis identifiant), #4164, #1714, #4137 → EP-38 ; #4349, #4160 → EP-37. US-2760/L2 et US-2770/L3
  n'en portent plus, hors #4513, qui fait partie du parcours du manager.

### Tables et migrations

Aucune table. Une migration, dans le socle, chaînée sur la dernière d'`epic/EP-08` au tirage de la
branche (celle de son socle), sans donnée à reprendre : le contrôle `kind_known` de
`revision_indicator` admet cinq natures de plus, toutes à la maille `project` :

| Nature | Ce qu'elle conserve | Pour |
|---|---|---|
| `portfolio_workload` | les heures par rôle de ressource et par mois chargé — sur le reste à engager d'un projet en cours, sur le devis d'une offre —, sans pondération | US-2700 |
| `portfolio_cost_structure` | les totaux par nature de coût du budget de référence, hors lignes de provision, et du reste à engager, provisions comprises ; la main-d'œuvre de l'un et de l'autre par rôle, groupée par nœud à la lecture, sur l'arbre courant ; pour une offre, son devis tient lieu des deux | US-2720 |
| `portfolio_risks` | chaque risque de la révision : son identifiant, son libellé, sa probabilité, sa gravité, sa provision, son état, l'assiette de son projet ; le coût à la survenance et le réestimé d'un survenu | US-2730 |
| `portfolio_milestones` | les jalons inscrits au suivi temps/temps : la lignée, le libellé, la date de référence, la date de terminaison | US-2750 |
| `portfolio_offer_curves` | pour une offre : les séries au pas du mois de son devis, hors provisions et provisions comprises, sans et avec les délais de paiement | US-2740 |

Le déclencheur qui refuse une ligne dont `computed_at` n'est pas le `marked_at` de sa révision ne
change pas : ces documents sont calculés à l'`Act` du marquage (#3549). Les droits du rôle du
service sont ceux de la table. La descente rétablit le contrôle d'EP-10, et échoue tant qu'une ligne
de ces natures existe. La réserve et la couverture ne sont pas reprises ici : EP-08 les conserve
dans le document `remaining`.

Les tests : `test_migrations.py` (le contrôle élargi), `test_database_constraints.py`,
`test_revision_immutability.py` étendu aux natures nouvelles.

### Modules

| Module | Ce qu'il reçoit | Ce qu'il expose |
|---|---|---|
| `core/portfolio` (nouveau, FBS-2) | le périmètre et sa résolution ; la contribution d'un projet ; les huit vues ; le sous-paquet pur `aggregation/` — la pondération, les sommes, les rapports de sommes, les parts, le taux de transformation, la répartition par zone, les trimestres | son interface, un fichier par vue, réexportés par le module ; `store_contribution(session, revision_id, act)`, qu'il enregistre à `register_indicators` après `store_indicators` |
| `core/indicators` | les cinq natures ; l'écriture d'un document conservé pour un autre module ; la lecture conservée et la lecture du jour de plusieurs projets à la fois ; l'entrée du cache de la contribution d'un projet, sous la même empreinte | `keep_document`, `kept_documents_of` (plusieurs révisions, une requête), `day_documents_of` (plusieurs projets, par le cache), `offer_curves` (les séries d'un devis, par `series/`) ; `formulas/` sert tel quel |
| `core/estimate` | les totaux par nature et la main-d'œuvre par rôle d'une révision, dans un fichier nouveau de son interface | `portfolio_totals` ; `workload` (EP-07, EP-10) sert tel quel |
| `core/risks` (EP-08) | les risques d'une révision tels que le portefeuille les lit, et les changements d'état d'une période, dans un fichier nouveau de son interface | `portfolio_risks`, `outcomes_between`, `not_reviewed_since` (groupé, #4294) ; le registre, la matrice, la réserve et la couverture servent tels quels |
| `core/planning` | rien | `tracked_milestones`, `milestone_forecasts` (EP-10) servent tels quels |
| `core/costs` | l'instant du dernier import de plusieurs projets, dans un fichier nouveau de son interface | `last_imports` |
| `core/revisions` | la dernière révision marquée de plusieurs projets à un instant, et leur révision courante | `last_marked_at_instant`, en une requête ; `marked_revisions_of` (US-2750) |
| `core/projects` | les projets retenus par leur état à une date ; les offres sorties du chiffrage dans une période ; ce que l'appelant peut ouvrir, pour plusieurs projets | `projects_in_states_on`, `offers_closed_between`, `openable` ; `ALL_PROJECTS_READ` relu d'une seule définition (#3341) |
| `core/resource_settings`, `core/indicator_settings`, `core/risk_settings` | rien | les rôles, leur capacité calculée et leur nœud ; le sous-arbre d'un nœud ; les seuils, le délai entre deux revues ; la matrice |

- **La couche** : `portfolio` entre au contrat de couches d'import-linter, au-dessus
  d'`indicators` et de `risks` ; `api`, `worker` et `witness` l'importent — c'est son import qui
  remplit le registre, et `test_registries.py` s'étend à lui.
- **L'unique définition d'`ALL_PROJECTS_READ`** descend dans `platform`, que `projects` et
  `access_roles` importent tous deux (#3341).
- **Chaque fichier nouveau d'une interface d'un autre module** est créé à vide et réexporté par le
  socle, pour que deux lots sans dépendance n'écrivent pas le même `__init__`.

### La contribution d'un projet

- **Au marquage**, `store_contribution` écrit, par `keep_document`, les natures du tableau que
  l'état du projet appelle : un projet en cours, les quatre premières ; une offre, les mêmes moins
  ce qui demande une référence, et ses courbes. Une exception remonte au marquage, qui échoue
  entier (la politique d'EP-10).
- **Au jour courant**, la même fonction de calcul donne les mêmes documents pour la révision
  courante du projet — la révision en cours ou, à défaut, la dernière marquée —, gardés par le cache
  d'EP-10 sous l'empreinte du projet, que les compteurs des risques complètent (EP-08). Les
  indicateurs du jour, les courbes et le reste à engager sont ceux d'EP-10, lus par le même cache.
- **À une date passée**, la révision retenue d'un projet est sa dernière révision marquée dont
  l'instant du marquage ne dépasse pas la fin du jour demandé, dans le fuseau de l'installation ;
  ses documents se lisent en une requête pour tous les projets du périmètre. Une nature absente —
  une révision antérieure à cet EPIC, une offre sans référence — ne contribue pas.
- **Le poids d'un projet** : un pour un projet en cours ou terminé ; pour une offre, la probabilité
  de gain que sa révision a gardée au marquage (EP-07), ou celle du projet au jour courant. Il ne
  s'applique ni au pipeline brut ni aux risques.

### Les vues

Chaque vue résout le périmètre par une seule fonction — les états à la date, par les transitions ;
la période, celle par défaut comprise, et son refus ; le nœud et son libellé —, lit les
contributions des projets retenus et rend `PortfolioScope`.

- **Toute vue lit par `PortfolioReading(at, cache)`** (décision du 2026-11-19, #4194) : l'instant de
  la lecture et le cache des indicateurs du jour, passés ensemble, comme US-2690/L2 l'introduit
  (`core/portfolio/interface/scope.py`) ; une lecture partagée évite la dérive de #4193. Les lots
  d'US-2700 à US-2750 adaptent leur squelette, où `at: datetime` tient aujourd'hui lieu des deux.
- **La liste et la valeur** (US-2690) : les documents `project`, `estimate` et `remaining` d'EP-10.
  Le filtre, le tri et la pagination se font sur les lignes formées, en mémoire : trois cents
  projets, et des colonnes calculées qu'aucune table ne porte. Le taux de transformation lit les
  transitions de la période, périmètre ou non. **Une liste lue sans période ne retient aucun projet
  terminé** (décision du 2026-11-19, #4020 point 1 et #4136) : sans `from` ni `to`, il n'y a pas de
  période où un projet aurait été terminé ; la liste retient les projets en cours et en chiffrage,
  qu'un état `completed` soit demandé ou non, et `scope.from` et `scope.to` sont nuls. Avec l'un des
  deux, la période par défaut complète l'autre et le projet terminé dans la période est retenu. Écarté :
  retenir par défaut les projets terminés de la période par défaut, que le contrat (« ne retient
  aucune période ») ne dit pas.
- **Le plan de charge** (US-2700) : `portfolio_workload`, pondéré, sommé par rôle et par mois ; les
  rôles retenus et leur capacité par `core/resource_settings` ; la zone de chaque mois.
- **La performance** (US-2710) : les grandeurs du document `project` sommées, puis les formules
  d'EP-10 appliquées aux sommes ; chaque trimestre passé est une lecture à son dernier jour.
- **La structure des coûts** (US-2720) : `portfolio_cost_structure`, pondéré ; les parts arrondies
  de façon que leur somme soit un ; la main-d'œuvre groupée par le nœud courant du rôle.
- **Les risques** (US-2730) : `portfolio_risks`, sans pondération ; la couverture, du document
  `remaining` ; les issues de la période, par `outcomes_between`.
- **La courbe en S** (US-2740) : les documents `cost_curve` et `cost_curve_payment_delays` d'EP-10,
  et `portfolio_offer_curves` pondéré, sommés mois par mois sur la fenêtre demandée.
- **La santé du pilotage** (US-2750) : l'instant du dernier marquage face au délai du référentiel ;
  `not_reviewed_since` ; `last_imports` ; `portfolio_milestones`.

### Le contrat

Modifié par un lot, avant le code qui le consomme, et le client réengendré :

- **`getPortfolioProjects`** reçoit un filtre par colonne, nommé comme ceux des tables plates
  (README du contrat) : le code ; des bornes `_min` et `_max` pour le budget de référence, le devis
  courant, la probabilité de gain, la projection du chef de projet, l'écart à la référence, l'indice
  de coût et l'indice de délai ; une période pour l'instant de la dernière révision marquée. Une
  borne inversée est refusée par 422 `VALUE_OUT_OF_RANGE` sur la borne haute, une période inversée
  par la règle des périodes. Un projet dont la colonne est nulle n'est retenu par aucune borne de
  cette colonne.
- **`PortfolioOrgNode`** dit que le nœud ne change aucun montant de la liste, de la valeur ni de la
  performance.
- **Un exemple** de la liste filtrée est engendré par `make mock-data` depuis les trois cents
  projets ; le faux back le sert.
- `docs/api/DECISIONS.md` reçoit ces deux décisions, et celle des révisions marquées avant l'EPIC.

Aucun schéma de réponse ne change.

### Le service d'API et le worker

Un routeur par vue, huit, créés vides par le socle, avec leurs aides de test (`asked_portfolio_*`).
Chaque route est gardée par la permission de sa fonction au catalogue d'EP-03 — la valeur par celle
de la liste, FBS-2.1 — et par elle seule : ni la qualité de contributeur ni « consulter tous les
projets » n'y entrent, sinon pour `can_open`. Chaque réponse est validée contre le contrat dans les
tests. Le worker importe l'interface du portefeuille pour que le marquage qu'il exécute conserve ses
documents ; il ne reçoit aucune tâche.

### Le témoin

`fixtures/witness/portfolio/` porte la description de la tranche — une dizaine de projets en petits
nombres, chacun avec ses tâches, ses lignes, ses coûts, ses risques, ses marquages et ses
transitions, dans la forme des schémas du contrat, que ses modèles valident — et les huit lectures
attendues. Un générateur de `wftools` les calcule de cette description et des lectures de PRJ-001,
sans rien réemployer du back ; `make mock-data` les écrit, `make mock-data-up-to-date` les garde.

Le chargeur insère la tranche dans la marche des événements, après celle des risques et des
avenants d'EP-08, par les interfaces des modules et aux instants de sa chronologie. Les lectures
sont comparées à la date du témoin, le 3 juin 2026, par `as_of` : c'est la lecture conservée qui est
ainsi comparée. Le jour courant, qui dépend de l'horloge, est prouvé par les tests du back à horloge
fixée, et par des invariants dans le parcours — la ligne de PRJ-001 égale ses indicateurs, chaque
total égale la somme de ses lignes.

### Le front

Les écrans existent. Quatre changements de code : le panneau des filtres par colonne de la liste,
porté par l'adresse ; l'identifiant de l'adresse lu par la fonction du référentiel (#2867) ; la
levée des gardes `inService` des parcours du portefeuille, ceux qui affirment trois cents projets
restant joués contre le faux back seul ; le parcours du manager. Le guide de l'utilisateur est mis à
jour.

### Les tests et les contrôles

- **Les exemples chiffrés** du §3.4.3, de WF-PRJ-0090, de WF-CYC-0130 et de WF-REF-0100 sont des
  tests sans base d'`aggregation/` (`tests/examples`), chacun citant son exigence, et les mêmes sur
  le service.
- **Les fabriques** du socle donnent aux lots un projet en cours, une offre à 40 %, un projet
  terminé dans la période, une offre perdue, chacun marqué.
- **La lecture conservée** : un test relève les requêtes de chaque vue lue avec `as_of` et refuse
  toute lecture des tables des nœuds, des tâches et des lignes de devis.
- **`wftools.examples`** reçoit la liste versionnée des exemples hors du harnais, chacun avec sa
  raison et l'EPIC qui le prouve, et échoue sur un exemple qui n'a ni test ni déclaration.
- **La constante modifiée** : pour chaque famille de calcul que WF-QUA-0020 nomme, un test change
  une constante nommée du noyau et constate qu'un exemple du harnais échoue.
- **L'unique implémentation** : une table versionnée nomme, pour chaque calcul que WF-ARC-0010 cite,
  son module du noyau ; un contrôle constate que l'API, le worker et `core/portfolio` l'importent
  de là et n'en définissent aucun.
- **La liste fermée des échanges** : un test des outils confronte les opérations du contrat qui
  déposent ou rendent un fichier au tableau des flux de la spécification.

### La mesure

Reportée à EP-40 avec US-2790 (« Reprise du 2026-11-21 soir ») ; ce qui suit est la conception que
son cadreur reprend. Les huit vues entrent au parcours de `make measure` et de `make measure-version`, au jour courant, à
cache froid puis chaud, et à une date passée ; `make measure-core` relève leur durée et le nombre de
leurs requêtes dans le noyau. Le rapport dit que le témoin ne porte pas trois cents projets.

### L'ordre de construction

1. **Le socle, et ce qui ne l'attend pas**, en parallèle : le socle (US-2670) ; le contrat
   (US-2690) ; les outils des exemples, de l'unique implémentation et des échanges (US-2780), qui ne
   touchent pas le portefeuille.
2. **La contribution** : ce que le marquage conserve et ce que le jour courant garde (US-2680). Sa
   part des risques attend le registre et la couverture d'EP-08 (US-2600/L1, US-2610/L1).
3. **Les vues**, sans dépendance entre elles : la liste et la valeur (US-2690), le plan de charge
   (US-2700), la performance (US-2710), la structure des coûts (US-2720), la courbe en S (US-2740) ;
   puis celles qui lisent les risques, les risques (US-2730) et la santé du pilotage (US-2750), qui
   attendent aussi les réexamens d'EP-08 (US-2590/L1).
4. **Le périmètre éprouvé sur toutes les vues** (US-2670, dernier lot), puis **les écrans**
   (US-2760).
5. **Le témoin** (US-2770), qui attend tout le back et le témoin d'EP-08 (US-2650/L1), puis son
   coût dans la chaîne (US-2770/L2b) et **la vérification d'ensemble**, seule : le parcours du
   manager, la définition de fini. La mesure (US-2790) est reportée à EP-40.

---

## US-2670 — Le périmètre, la date de calcul et la règle d'agrégation

- **statut** : fini
- **exigences** : `WF-PTF-0010-A`, `WF-PTF-0020-A`, `WF-PTF-0030-A`, `WF-CYC-0130-A`,
  `WF-PRJ-0090-A`
- **opérations** : `getPortfolioProjects`, `getPortfolioValue`, `getPortfolioWorkload`,
  `getPortfolioPerformance`, `getPortfolioCostStructure`, `getPortfolioRisks`,
  `getPortfolioCostCurve`, `getPortfolioPilotHealth`, `listProjectStateTransitions`, `updateProject`
- **issue** : #3857

**En tant que** manager, **je veux** que toute vue du portefeuille se calcule sur le périmètre et à
la date que je choisis, par les mêmes règles de somme et de pondération, sans rien y saisir, **afin
de** comparer les vues entre elles et de retrouver le portefeuille tel qu'il était.

**Critères d'acceptation.**

- `WF-PTF-0010-A` — « Le même portefeuille calculé avec et sans les projets en chiffrage donne des
  valeurs différentes, et la différence égale la contribution de ces projets, pondérée par leur
  probabilité de gain, hors le pipeline brut et la vue des risques, où elle ne l'est pas
  (WF-PTF-0020). » : éprouvé sur chaque vue qui retient le chiffrage — la valeur, le plan de charge,
  la structure des coûts, la courbe en S, les risques — lue avec `states` valant `in_progress`, puis
  `in_progress,pricing` ;
- `WF-PTF-0010-A` — « Calculé à une date passée, il ne change pas quand une révision est marquée
  après cette date. » : chacune des huit vues, lue avec `as_of`, rend la même réponse avant et après
  un marquage, un import de coûts réels et une transition d'état postérieurs à cette date ;
- `WF-PTF-0010-A` — « Un projet terminé aujourd'hui, en cours à une date passée, compte parmi les
  projets en cours du portefeuille calculé à cette date. » : l'état d'un projet à une date est celui
  de sa dernière transition datée de ce jour ou d'avant (WF-CYC-0130) ;
- `WF-PTF-0010-A` — « Le filtre par nœud laisse inchangés les totaux hors main-d'œuvre. » :
  `org_node_id` ne restreint que les lignes de main-d'œuvre dont le rôle relève du nœud ou de l'un de
  ses descendants, au plan de charge et dans la structure des coûts ; sur la liste, la valeur et la
  performance, il est retenu dans le périmètre rendu et ne change aucun montant (décision de
  l'auteur du 2026-11-17) ; un nœud inconnu est refusé par 422 sur `/query/org_node_id` ;
- `WF-PTF-0010-A` — « Un projet dont la revue vient d'être marquée et qui n'a pas de révision en
  cours contribue par cette revue. » : au jour courant, par sa dernière révision marquée, recalculée
  avec le coût réel du jour (WF-IND-0010, la sélection d'EP-10) ;
- `WF-PTF-0020-A` — « Deux projets de valeur acquise 100 et 1 000, de coût réel 200 et 1 000,
  donnent un indice de coût de portefeuille de 0,917, et non de 0,75. » : un test du harnais, sans
  base ;
- `WF-PTF-0020-A` — « Une offre à 40 % de probabilité et 100 000 de devis contribue pour 40 000 à la
  valeur du pipeline. » : un test du harnais, sans base ;
- `WF-PTF-0030-A` — « Un utilisateur habilité au portefeuille mais contributeur d'aucun projet
  consulte toutes les vues. » : chaque vue est gardée par la permission de sa fonction au catalogue
  (EP-03), et par elle seule ;
- `WF-PTF-0030-A` — « Aucune vue ne propose de modifier une donnée. » : les huit opérations sont des
  lectures, et aucun écran du portefeuille ne porte de commande de saisie ;
- `WF-PTF-0030-A` — « Un utilisateur habilité au portefeuille sans « consulter tous les projets »,
  contributeur d'un seul projet du périmètre, voit les totaux de tous et n'ouvre que le sien. » :
  `can_open` est vrai pour son seul projet, dans la liste, dans les risques les plus lourds et dans
  les signaux de la santé du pilotage ; les autres y figurent sous leur libellé et leur code ;
- `WF-CYC-0130-A` — « Après passage d'un projet à En cours puis à Terminé, l'historique présente
  les deux transitions avec leur date. » : tenu par EP-04 (US-0980), non touché ici ;
- `WF-CYC-0130-A` — « Un projet passé à Perdu le 15 mars compte parmi les offres closes de mars et
  d'aucun autre mois. » : une statistique de période retient une transition par sa date, bornes
  comprises : l'offre perdue le 15 mars entre au dénominateur du taux de transformation d'une
  période qui contient ce jour, et d'aucune autre ;
- `WF-CYC-0130-A` — « Une sortie à Perdu confirmée avec un motif présente ce motif dans
  l'historique ; une transition automatique n'en porte aucun. » : tenu par EP-04 (US-0980), non
  touché ici ;
- `WF-PRJ-0090-A` — « Une offre à 40 % de probabilité et 100 000 € de devis pèse 40 000 € dans le
  pipeline pondéré et 40 % de sa charge dans le plan de charge agrégé pondéré. » : un test du
  harnais, et le même sur le service ;
- `WF-PRJ-0090-A` — « Le devis et les indicateurs du projet lui-même sont identiques à 0 % et à
  100 %. » : `getEstimateIndicators`, `getRemainingIndicators` et, sur un projet en cours marqué à
  chacune, `getProjectIndicators` rendent les mêmes montants à 0 % et à 100 % ;
- `WF-PRJ-0090-A` — « La modification de la probabilité est refusée à partir de l'état En cours. »
  : tenu par EP-04 (US-0920), non touché ici ;
- propre à l'US : chaque vue rend le périmètre retenu (`PortfolioScope`) — les états demandés ou,
  sans eux, les projets en cours ; la date de calcul, le jour courant du fuseau de l'installation
  sans `as_of` ; la période, celle par défaut comprise, nulle pour une vue qui n'en retient pas ; le
  nœud et son libellé ; le nombre de projets retenus ; un état que la vue ne compte pas est sans
  effet, jamais refusé ;
- propre à l'US : une période inversée, ou qui commence après sa fin par défaut, est refusée par
  422 (`PortfolioPeriodRefused`), par une seule règle pour les six vues qui prennent une période ;
- propre à l'US : au jour courant, chaque projet contribue par ses indicateurs du jour, lus par le
  cache d'EP-10 ; à une date passée, par les documents que sa dernière révision marquée à cette date
  a conservés, la probabilité de gain étant celle que ce marquage a gardée (EP-07) ; un projet sans
  révision marquée à cette date est retenu selon son état, figure dans la liste sans montant et ne
  contribue à aucune somme ;
- propre à l'US : une révision marquée avant cet EPIC ne contribue, à une date passée, que par ce
  qu'elle a conservé ; rien n'est recalculé ni repris (décision de l'auteur du 2026-11-17, écrite
  dans `docs/api/DECISIONS.md`) ;
- propre à l'US : `ALL_PROJECTS_READ` n'a plus qu'une définition, que `projects` et `access_roles`
  lisent tous deux (#3341) ;
- propre à l'US : la règle « qui peut ouvrir un projet » n'est écrite qu'une fois : `access_roles`
  (`evaluation.py`) lit celle de `Viewer.sees_all`, et un test éprouve que le jugement d'accès d'un
  projet et `can_open` du portefeuille s'accordent (#4131, décision du 2026-11-19 ; US-2670/L4) ;
- propre à l'US : la période de `getPortfolioPerformance` est bornée par le contrat : au-delà d'une
  durée maximale, 422 `VALUE_OUT_OF_RANGE` ; le lot propose la durée dans son issue (#4176, décision
  du 2026-11-19 ; US-2670/L4) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « Le portefeuille : horizon, projets terminés,
couverture, offres » (G-03 à G-06, G-11, G-14, M-07), « Les lignes du portefeuille disent si le
projet s'ouvre » (#389), « Les vues du portefeuille déclarent le refus d'une période » (#560). Les
critères de cette US se ferment à mesure que les vues arrivent : son dernier lot les éprouve sur
toutes.

**Hors périmètre.** Ce que chaque vue somme (US-2690 à US-2750) ; ce que le marquage conserve
(US-2680) ; les écrans (US-2760).

---

## US-2680 — Ce que le marquage conserve pour le portefeuille

- **statut** : fini
- **exigences** : `WF-DAT-0040-A`
- **opérations** : `markRevision`, `mergeCostStructure` (la conservation), `getPortfolioProjects`,
  `getPortfolioValue`, `getPortfolioWorkload`, `getPortfolioPerformance`,
  `getPortfolioCostStructure`, `getPortfolioRisks`, `getPortfolioCostCurve`,
  `getPortfolioPilotHealth` (avec `as_of`)
- **issue** : #3860

**En tant que** manager, **je veux** que chaque révision marquée garde ce que le portefeuille lira
d'elle, **afin de** retrouver le portefeuille d'une date passée à coût constant, sans que rien ne
soit recalculé.

**Critères d'acceptation.**

- `WF-DAT-0040-A` — « Le marquage d'une révision échoue entièrement si le calcul de ses indicateurs
  échoue. » : tenu par EP-10 (US-1670) ; l'enregistrement du portefeuille s'exécute dans la même
  transaction, et une exception de son calcul fait échouer le marquage de la même façon ;
- `WF-DAT-0040-A` — « Aucune vue de portefeuille à une date passée, sur trois cents projets — plan
  de charge agrégé, structure des coûts et risques compris —, ne lit de ligne de tâche ni de ligne
  de devis. » : un test relève les requêtes de chacune des huit vues lue avec `as_of` : aucune ne
  touche les tables des nœuds, des tâches ni des lignes de devis ;
- écart : les trois cents projets du jeu de données de référence (WF-QUA-0040) sont à EP-13, qui
  rejoue ce test dessus ; ici, il porte sur le témoin chargé avec la tranche du portefeuille ;
- `WF-DAT-0040-A` — « Les indicateurs conservés d'une révision marquée sont identiques avant et
  après un import de coûts réels postérieur. » : tenu par EP-10 (US-1670) ; les documents du
  portefeuille ne changent pas davantage ;
- `WF-DAT-0040-A` — « Le marquage d'une offre, sur un projet en chiffrage, aboutit et conserve le
  total du devis sans aucun indicateur projet. » : tenu par EP-10 (US-1670) ; l'offre marquée
  conserve de plus ce que le portefeuille lit d'une offre ;
- `WF-DAT-0040-A` — « La courbe de coût réel d'une révision marquée est identique avant et après
  l'exclusion d'une ligne de coût connue à son marquage. » : tenu par EP-10 (US-1690), non touché
  ici ;
- écart : `WF-DAT-0040-A` — « Une lecture conservée d’un sous-projet créé après le marquage de la
  révision est refusée, la révision ne conservant pas ses indicateurs. » : ajouté par la
  spécification 1.0.7 (#3736) ; tenu par EP-10 (US-2430/L3, #3649) ;
- propre à l'US : le marquage conserve de plus, pour le projet : la charge par rôle de ressource et
  par mois — sur le reste à engager d'un projet en cours, sur le devis d'une offre — ; les totaux
  par nature de coût du budget de référence, hors lignes de provision, et du reste à engager,
  provisions comprises, et la main-d'œuvre par nœud d'organisation ; pour chaque risque, sa
  probabilité, sa gravité, sa provision et son état, avec la réserve et la couverture ; pour une
  offre, les courbes de son devis, hors provisions et provisions comprises ; et ce que la santé du
  pilotage constate d'une révision — ses jalons inscrits au suivi, leur date de référence et leur
  terminaison ;
- propre à l'US : ces documents sont calculés à l'instant du marquage et écrits dans sa
  transaction, sous des natures nouvelles de `revision_indicator`, qu'une migration admet (#3549) ;
  ils suivent l'immuabilité de la révision ;
- propre à l'US : la fusion d'un différentiel (EP-08), qui marque, les conserve de même, et le
  chargeur du témoin par `load_marking` ;
- propre à l'US : chaque vue lue à une date passée ne lit que ces documents, ceux d'EP-10, les
  projets, leurs transitions et les révisions ; elle rend `is_stored` partout où le contrat le
  porte ;
- propre à l'US : une révision marquée avant cet EPIC n'a pas ces documents, et n'en reçoit pas
  (décision de l'auteur du 2026-11-17) ;
- propre à l'US : l'empreinte sous laquelle le cache garde la contribution d'un projet couvre ce que
  la contribution lit : le nœud courant d'un rôle et la probabilité de gain d'une offre (US-2680/L2),
  les compteurs des risques (US-2680/L3) ; un changement de l'une de ces valeurs n'est pas servi
  d'après l'entrée ancienne (WF-DAT-0130-A ; #4158, décision du 2026-11-19) ;
- propre à l'US : le PostgreSQL des tests monte `max_locks_per_transaction`, et la fixture
  `database` supprime les partitions projet par projet, une transaction chacun, pour que les lots de
  vue écrivent leurs tests sur les fabriques sans épuiser les verrous (#4051, décision du
  2026-11-19 ; US-2680/L2, que ces lots attendent).

**Notes de réalisation.** Le registre `register_indicators` est déclaré par `core/revisions`
(EP-04) et reçoit l'`Act` du marquage (EP-10) ; le déclencheur de `revision_indicator` refuse une
ligne dont `computed_at` n'est pas le `marked_at` de sa révision (#3549). La décision d'EP-10 sur
les révisions marquées avant lui — le repli sur le calcul à la lecture, `is_stored` faux (#3612) —
ne s'étend pas au portefeuille.

**Hors périmètre.** Les sommes de chaque vue (US-2690 à US-2750) ; la lecture conservée d'un projet
(EP-10) ; les trois cents projets (EP-13).

---

## US-2690 — La liste des projets et la valeur du portefeuille

- **statut** : fini
- **exigences** : `WF-PTF-0040-A`, `WF-PTF-0050-A`
- **opérations** : `getPortfolioProjects`, `getPortfolioValue`
- **issue** : #3858

**En tant que** manager, **je veux** la liste des projets du périmètre, triée et filtrée par le
serveur sur chacune de ses colonnes, et ce que le portefeuille vaut — le carnet, le pipeline, le
réalisé, le taux de transformation —, **afin de** voir d'un regard ce qui est signé, ce qui pourrait
l'être et ce qui dérive.

**Critères d'acceptation.**

- `WF-PTF-0040-A` — « Chacune des colonnes citées est présente. » : le libellé, le code, l'état, le
  budget de référence ou le devis courant et la probabilité de gain, la projection du chef de projet
  et son écart au budget, les indices de coût et de délai avec leur zone, l'instant de la dernière
  révision marquée ;
- `WF-PTF-0040-A` — « Le tri par indice de coût place les projets en alerte en tête. » : `sort_by`
  sur l'indice de coût, croissant ; un projet sans indice est à la place que dit le contrat ;
- `WF-PTF-0040-A` — « Un projet en chiffrage affiche son devis et sa probabilité là où un projet en
  cours affiche son budget de référence. » : `current_estimate` et `win_probability` pour l'un,
  `reference_budget` pour l'autre, l'autre champ nul ;
- `WF-PTF-0040-A` — « Un projet en cours de budget 1 000, de coût réel 500 et de reste à engager
  550 affiche une projection de 1 050 et un écart de 50. » : un test du harnais, et le même sur le
  service ; l'écart est positif au-delà du budget ;
- `WF-PTF-0050-A` — « Le carnet ne compte que les projets en cours, le pipeline que les projets en
  chiffrage. » ;
- `WF-PTF-0050-A` — « Une offre à 40 % de probabilité contribue pour tout au pipeline brut et pour
  40 % au pipeline pondéré. » : un test du harnais, et le même sur le service ;
- `WF-PTF-0050-A` — « Sur dix offres sorties de l'état Chiffrage dans la période vers En cours ou
  vers Perdu, dont quatre passées à En cours, le taux de transformation vaut 40 % ; une onzième,
  abandonnée dans la période, ne le change pas. » : un test du harnais, et le même sur le service ;
  les offres comptent qu'elles soient ou non du périmètre ; sans offre sortie, le taux n'est pas
  calculable (`no_offer_out_of_pricing`) ;
- propre à l'US : le contrat change avant le code : `getPortfolioProjects` reçoit un filtre par
  colonne — le code, les bornes du budget de référence, du devis courant, de la probabilité de gain,
  de la projection, de l'écart et des deux indices, la période de la dernière révision marquée —, à
  côté de l'état, de la période, de la zone et de la recherche sur le libellé (WF-IHM-0130 ;
  décision de l'auteur du 2026-11-17, contre le gel du contrat par EP-16) ; une borne inversée est
  refusée par 422 ; `docs/api/DECISIONS.md` reçoit la décision, et le client est réengendré ;
- propre à l'US : la liste se trie sur chaque colonne dans les deux sens, par le serveur ;
  `meta.total` compte les projets retenus par les filtres, et la pagination est celle du contrat ;
- propre à l'US : le réalisé est la somme des coûts réels des projets terminés dans la période ;
  la période par défaut est celle des douze mois qui finissent à la date de calcul ;
- propre à l'US : la liste et la valeur sont gardées par la permission de la liste des projets du
  portefeuille (FBS-2.1) ; chaque réponse est validée contre le contrat dans les tests du service ;
- propre à l'US : le rôle prédéfini « chef de projet » ne porte plus `portfolio_projects.read`
  (#3355) : l'amorçage ne la lui donne plus, une migration la lui retire sur une plateforme
  installée, sans toucher aux autres rôles ni à un rôle que l'entreprise a créé ; un chef de projet
  reçoit 404 sur la liste et sur la valeur, le manager les lit ; les exemples du contrat qui
  montrent ce rôle suivent.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « Les exemples du portefeuille » (la période par
défaut), « La liste des projets du portefeuille porte l'écart à la référence », « Les lignes du
portefeuille disent si le projet s'ouvre » (#389). Le filtre par colonne suit le README du contrat
(« A period… », les bornes d'une colonne de nombres).

**Hors périmètre.** Le panneau des filtres de l'écran (US-2760) ; la performance (US-2710).

---

## US-2700 — Le plan de charge agrégé

- **statut** : fini
- **exigences** : `WF-PTF-0060-A`, `WF-REF-0100-A`, `WF-REF-0070-A`
- **opérations** : `getPortfolioWorkload`, `updateOrgNode`, `getMe`, `updateMyPreferences`
- **issue** : #3861

**En tant que** manager, **je veux** la charge de tous les projets par rôle et par mois, en regard
de la capacité de chaque rôle, **afin de** savoir où embaucher, sous-traiter ou arbitrer.

**Critères d'acceptation.**

- `WF-PTF-0060-A` — « Sur deux projets en cours dont les restes à engager portent 100 et 150 heures
  d'un même rôle le même mois, le plan agrégé porte 250 heures. » : un test du harnais, et le même
  sur le service ;
- `WF-PTF-0060-A` — « Une offre à 50 % avec 100 heures ajoute 50 heures quand le chiffrage est
  inclus, rien sinon. » : un test du harnais, et le même sur le service ;
- `WF-PTF-0060-A` — « Un mois à 120 % de la capacité est signalé. » : la zone du mois est `alert`
  au-delà de la capacité, `watch` sous le seuil de sous-charge, `nominal` sinon ; un rôle sans
  capacité est `alert` s'il a de la charge, `watch` sinon, son taux non calculable (`no_capacity`) ;
- `WF-REF-0100-A` — « Un rôle ne porte qu'une capacité, sans date de validité. » : tenu par EP-05
  (US-0850), non touché ici ;
- `WF-REF-0100-A` — « Un rôle de deux personnes sur un calendrier de 35 heures par semaine dispose
  de 2 × 35 × 52 / 12, soit environ 303,33 heures par mois ; un effectif de 0,5 sur le même
  calendrier en dispose de 75,83. » : tenu par EP-10 (US-2410), non touché ici ;
- `WF-REF-0100-A` — « Le plan de charge agrégé compare la charge mensuelle de chaque rôle à ces
  heures. » : `capacity_monthly_hours` de chaque rôle est ses heures calculées (EP-10), et le taux
  de charge de chaque mois le rapport de la charge à ces heures ;
- `WF-REF-0070-A` — « Un arbre de six niveaux peut être créé. » : tenu par EP-05 (US-0840), non
  touché ici ;
- `WF-REF-0070-A` — « La création d'un nœud dont le code existe déjà est refusée. » : tenu par EP-05
  (US-0840), non touché ici ;
- `WF-REF-0070-A` — « Le déplacement d'un nœud sous un autre emporte ses descendants et ses rôles ;
  le plan de charge agrégé filtré sur le nœud d'arrivée inclut désormais ces rôles, et les valeurs
  par rôle sont inchangées. » : le déplacement est tenu par EP-05 ; ici, le plan de charge agrégé lu
  avec `org_node_id` du nœud d'arrivée, avant et après le déplacement ;
- `WF-REF-0070-A` — « Le déplacement sous un nœud désactivé est refusé. » : tenu par EP-05
  (US-0840), non touché ici ;
- propre à l'US : seuls les projets en cours et, s'ils sont demandés, en chiffrage y contribuent ;
  un autre état que `states` nomme — terminé compris — est sans effet, et la vue ne prend pas de
  période (#1714, éprouvé sur le service avec `states` valant `completed`) ;
- propre à l'US : les mois vont de celui de la date de calcul sur `horizon_months`, six par défaut,
  sans trou ; chaque rôle retenu porte un mois par mois, un rôle sans charge compris ; la capacité du
  périmètre est la somme des capacités des rôles retenus — tous les rôles actifs, ou ceux du nœud ;
- propre à l'US : `under_load_threshold` est toujours rendu, 0,5 sans demande ; un horizon ou un
  seuil hors de ses bornes est refusé par 422 ;
- propre à l'US : les parts d'une ligne s'arrondissent de façon que leur somme soit son total,
  comme au plan de charge d'un projet (EP-10), et le plan agrégé somme des heures déjà arrondies ;
- propre à l'US : à une date passée, la vue lit la charge par rôle et par mois que les révisions
  marquées ont conservée (US-2680), et la capacité courante des rôles ;
- propre à l'US : la lecture est sous `portfolio_workload.read` ; chaque réponse est validée contre
  le contrat dans les tests du service.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « Le seuil de sous-charge retenu », « Les mois
du plan de charge agrégé sont en tête de la réponse » (#326), « Le périmètre d'une vue du
portefeuille nomme son nœud » (#327). Le seuil, le filtre et l'horizon sont des préférences
d'affichage que l'écran garde déjà (`kept-workload`, EP-15) : le service n'en ajoute aucune.

**Hors périmètre.** Le détail par tâche, que seul le plan de charge d'un projet rend (EP-10) ;
l'écran et son export (US-2760).

---

## US-2710 — La performance du portefeuille

- **statut** : fini
- **exigences** : `WF-PTF-0070-A`
- **opérations** : `getPortfolioPerformance`, `getReferenceSettings`
- **issue** : #3862

**En tant que** manager, **je veux** les indices de coût et de délai de l'ensemble des projets en
cours, leurs projections, la répartition des projets par zone et l'évolution par trimestre, **afin
de** savoir où en est l'entreprise, combien de projets tirent vers le bas et si cela s'améliore.

**Critères d'acceptation.**

- `WF-PTF-0070-A` — « L'indice de coût agrégé est le rapport de la somme des valeurs acquises à la
  somme des coûts réels des projets du périmètre. » : de même l'indice de délai, rapport à la somme
  des valeurs planifiées ; à quatre décimales ; non calculable, avec sa raison, quand la somme au
  dénominateur est nulle ;
- `WF-PTF-0070-A` — « La répartition par zone compte chaque projet une fois. » : une fois par
  indice ; un projet dont l'indice n'est pas calculable n'est compté dans aucune zone de cet
  indice ;
- `WF-PTF-0070-A` — « L'évolution trimestrielle à une date passée ne change pas quand une révision
  est marquée après cette date. » : chaque trimestre passé se lit des documents conservés, à son
  dernier jour ;
- `WF-PTF-0070-A` — « Sur deux projets de budget 1 000, de valeur acquise 400 et 500 et de coût
  réel 500 et 500, la projection au rythme constaté agrégée vaut 2 222 et non 2 250. » : un test du
  harnais, et le même sur le service ;
- propre à l'US : seuls les projets en cours du périmètre y contribuent ; `scope.states` nomme les
  états demandés ;
- propre à l'US : les écarts de coût et de délai sont les sommes des écarts des projets ; la
  projection au budget et celle du chef de projet les sommes des projections ; la projection au
  rythme constaté n'est pas calculable tant que l'indice de coût agrégé ne l'est pas ;
- propre à l'US : l'évolution porte un point par trimestre civil que la période touche, du plus
  ancien au plus récent, chaque indice lu au dernier jour du trimestre, et à la date de calcul pour
  celui qui la contient, dont les indices égalent ceux du jour ; un trimestre sans projet en cours
  est non calculable ;
- propre à l'US : la zone de chaque indice se classe à la lecture sur les seuils courants du
  référentiel, pour un indice conservé comme pour un indice du jour (EP-10) ;
- propre à l'US : la lecture est sous `portfolio_performance.read` ; chaque réponse est validée
  contre le contrat dans les tests du service.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « Le portefeuille : horizon, projets terminés,
couverture, offres » (G-03, G-08, G-14, M-16). Les ratios et les projections sont ceux de
`formulas/` d'EP-10, appliqués à des sommes : aucune formule n'est récrite.

**Hors périmètre.** Les indices d'un projet (EP-10) ; l'écran (US-2760).

---

## US-2720 — La structure des coûts du portefeuille

- **statut** : fini
- **exigences** : `WF-PTF-0080-A`
- **opérations** : `getPortfolioCostStructure`
- **issue** : #3863

**En tant que** manager, **je veux** la part de main-d'œuvre, de matière, de sous-traitance et de
provisions de ce qui a été budgété et de ce qui reste à engager, **afin de** savoir de quoi dépend
la production de l'entreprise.

**Critères d'acceptation.**

- `WF-PTF-0080-A` — « La somme des parts par nature vaut cent pour cent, sur le budget comme sur le
  reste à engager. » : les parts s'arrondissent de façon que leur somme soit un ;
- `WF-PTF-0080-A` — « La ventilation par nœud ne porte que sur la main-d'œuvre. » :
  `labor_by_org_node` somme les lignes de main-d'œuvre par le nœud du rôle ;
- `WF-PTF-0080-A` — « Aucune vue ne propose de ventilation du coût réel par nature. » : ni la
  réponse ni l'écran n'en portent ;
- `WF-PTF-0080-A` — « Une offre à 40 % dont le devis porte 100 de main-d'œuvre ajoute 40 à la
  main-d'œuvre du budget agrégé lorsqu'elle est incluse. » : un test du harnais, et le même sur le
  service ;
- `WF-PTF-0080-A` — « Une offre incluse, à 40 %, dont le devis porte une ligne de provision pour
  risques de 50 n'ajoute rien à la nature de cette ligne dans le budget agrégé, et ajoute 20 à cette
  nature dans le reste à engager agrégé. » : un test du harnais, et le même sur le service ;
- `WF-PTF-0080-A` — « Une ligne de 50 d'une nature hors main-d'œuvre, une provision pour aléas par
  exemple, ajoute 20 à sa nature dans l'un et dans l'autre. » : un test du harnais, et le même sur
  le service ;
- propre à l'US : les projets en cours et terminés du périmètre contribuent pour tout, les
  terminés étant ceux de la période, celle par défaut comprise ;
- propre à l'US : `org_node_id` ne restreint que la main-d'œuvre : les totaux des autres natures
  sont inchangés ;
- propre à l'US : à une date passée, la vue lit les totaux par nature et par nœud que les révisions
  marquées ont conservés (US-2680) ;
- propre à l'US : la lecture est sous `portfolio_cost_structure.read` ; chaque réponse est validée
  contre le contrat dans les tests du service.

**Notes de réalisation.** Une ligne de provision se reconnaît à sa catégorie, par `core/estimate`
seul (EP-08, « Ce qui reconnaît une ligne de provision »). `docs/api/DECISIONS.md` : G-15 (le budget
de référence agrégé sans nature « Provision »), M-07 (la contribution d'une offre).

**Hors périmètre.** La courbe en S (US-2740) ; l'écran (US-2760).

---

## US-2730 — Les risques du portefeuille

- **statut** : fini
- **exigences** : `WF-PTF-0090-A`
- **opérations** : `getPortfolioRisks`
- **issue** : #3865

**En tant que** manager, **je veux** voir ensemble les risques de tous les projets — ce qu'ils
provisionnent, les plus lourds, la matrice, la couverture —, **afin d'** en discuter au niveau de
l'entreprise et de savoir si elle provisionne juste.

**Critères d'acceptation.**

- `WF-PTF-0090-A` — « Le total des provisions identifiées égale la somme des provisions des risques
  identifiés des projets du périmètre. » : ceux d'un projet en chiffrage inclus comptent sans
  pondération ;
- `WF-PTF-0090-A` — « La matrice compte chaque risque identifié une fois. » : dans la case de ses
  niveaux de probabilité et de gravité, classés sur l'assiette de son projet (EP-08) ;
- `WF-PTF-0090-A` — « La réserve agrégée est la somme des réserves des projets en cours et terminés
  du périmètre, et l'écart de couverture agrégé la différence des sommes. » : un projet en chiffrage
  n'y entre pas ;
- `WF-PTF-0090-A` — « Un projet terminé inclus dans le périmètre compte dans la réserve agrégée et
  dans l'écart de couverture agrégé. » : un test déclare un projet terminé dans la période ;
- propre à l'US : les risques les plus lourds sont les dix premiers par provision, tous projets
  confondus, chacun avec son projet et `can_open` ;
- propre à l'US : la couverture rend, à côté du coût des survenus, la somme des réestimés des
  lignes qui en sont issues ; un test les sépare, sur un projet où ils diffèrent (#2002) ;
- propre à l'US : `period_outcome` somme, sur la période, les provisions des risques survenus et
  celles des risques écartés, par la date du réexamen qui les a fait changer d'état ;
- propre à l'US : à une date passée, la vue lit les risques que les révisions marquées ont
  conservés (US-2680) ;
- propre à l'US : la lecture est sous `portfolio_risks.read` ; chaque réponse est validée contre le
  contrat dans les tests du service.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « Les risques à l'échelle et le Kanban de toute
la structure », la matrice du portefeuille et ses trois champs (#1053), G-06 (la couverture
agrégée). Les lectures d'un projet sont celles de `core/risks` (EP-08) : le registre, la matrice, la
réserve et la couverture.

**Hors périmètre.** Le registre d'un projet (EP-08) ; l'écran (US-2760).

---

## US-2740 — La courbe en S du portefeuille

- **statut** : fini
- **exigences** : `WF-PTF-0100-A`
- **opérations** : `getPortfolioCostCurve`
- **issue** : #3864

**En tant que** manager, **je veux** la somme, mois par mois, des courbes de coûts cumulés des
projets, et sur demande leurs décaissements, **afin de** piloter la tenue du budget et la trésorerie
au niveau de l'entreprise.

**Critères d'acceptation.**

- `WF-PTF-0100-A` — « Chaque point de la courbe agrégée égale la somme des points de ce mois sur
  les projets du périmètre, pour chacune des trois courbes et en mode décaissement. » : rien n'est
  recalculé : la vue somme les séries que `getCostCurve` rend de chaque projet (EP-10) ;
- `WF-PTF-0100-A` — « Un projet en chiffrage à 40 % contribue pour 40 % de ses courbes lorsqu'il
  est inclus. » : les courbes de son devis courant ;
- `WF-PTF-0100-A` — « Une offre incluse à 40 %, dont le devis porte 100 hors provisions et une
  provision de 50, apporte 40 au budget cumulé final et 60 à la projection. » : un test du harnais,
  et le même sur le service ;
- propre à l'US : la courbe court sur les douze mois qui précèdent celui de la date de calcul, puis
  sur `horizon_months` mois à partir de lui, six par défaut ; la période ne borne pas ses mois, elle
  choisit les projets terminés ;
- propre à l'US : le coût réel s'arrête à la date de calcul, la projection du chef de projet
  commence après elle ;
- propre à l'US : avec `payment_delays`, les séries sont celles des décaissements de chaque projet,
  et `cash_out_by_month` en rend le détail par mois, un mois pouvant être négatif ; sans lui, ce
  champ est nul ;
- propre à l'US : à une date passée, la vue somme les courbes que les révisions marquées ont
  conservées (EP-10, et US-2680 pour une offre) ;
- propre à l'US : la lecture est sous `portfolio_cost_curve.read` ; chaque réponse est validée
  contre le contrat dans les tests du service.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « La courbe en S du portefeuille est une seule
opération », G-04 (l'horizon), M-07 (la contribution d'une offre). Les séries au pas du mois et les
décaissements sont ceux de `series/` d'EP-10.

**Hors périmètre.** Les courbes de valeur acquise, propres à un projet (EP-10) ; l'écran (US-2760).

---

## US-2750 — La santé du pilotage

- **statut** : fini
- **exigences** : `WF-PTF-0110-A`, `WF-REF-0180-A`
- **opérations** : `getPortfolioPilotHealth`, `getReferenceSettings`, `updateReferenceSettings`
- **issue** : #3866

**En tant que** manager, **je veux** savoir quels projets en cours n'ont pas fait leur revue, n'ont
pas réexaminé leurs risques, n'ont pas importé leurs coûts ou ont un jalon suivi en retard, **afin
de** savoir si je peux me fier aux autres vues.

**Critères d'acceptation.**

- `WF-PTF-0110-A` — « Un projet en cours sans révision marquée depuis plus que le délai maximal
  apparaît dans la vue, et en disparaît au marquage suivant. » : le signal `review_overdue`, avec le
  nombre de semaines écoulées depuis la dernière révision marquée ;
- `WF-PTF-0110-A` — « Un jalon contractuel dont la date de référence est passée et qui n'est pas
  terminé apparaît, et disparaît à sa terminaison. » : le signal `contractual_milestone_overdue`,
  en zone `alert`, pour un jalon inscrit au suivi temps/temps, avec sa lignée, son libellé et sa
  date de référence ;
- `WF-REF-0180-A` — « Le délai est saisissable en semaines. » : tenu par EP-05 (US-0810), non
  touché ici ;
- `WF-REF-0180-A` — « Un projet dont la dernière révision marquée date de plus que ce délai est
  signalé ; il ne l'est plus après un marquage. » : le délai lu est celui du référentiel au moment
  de la lecture ; un délai modifié change les signaux à la lecture suivante ;
- `WF-PTF-0110-A` — « Un projet dont la revue marquée ce jour a réexaminé chaque risque et importé
  des coûts n’apparaît pour aucun de ces deux signaux ; un projet dont la dernière revue n’a importé
  aucun coût apparaît. » : `risks_not_reviewed` signale un projet dont un risque identifié n'a aucun
  réexamen entre l'avant-dernière et la dernière révision marquée — depuis le passage à En cours, à
  défaut d'avant-dernière — ; `no_actual_cost_since_last_review`, un projet sans import de coûts
  réels dans le même intervalle (spécification 1.0.7, #3351) ; la description des deux signaux au
  contrat le dit, par une issue `contract` ouverte au lot ;
- propre à l'US : les trois signaux autres que le jalon sont en zone `watch` ;
- propre à l'US : seuls les projets en cours du périmètre sont examinés ; un autre état que
  `states` nomme — terminé compris — est sans effet, et la vue ne prend pas de période (#1714,
  éprouvé sur le service avec `states` valant `completed`) ;
- propre à l'US : chaque signal nomme son projet et dit s'il s'ouvre (`can_open`) ;
- propre à l'US : la lecture est sous `portfolio_pilot_health.read` ; chaque réponse est validée
  contre le contrat dans les tests du service.

**Notes de réalisation.** Les jalons inscrits au suivi et leurs dates se lisent par `core/planning`
(`tracked_milestones`, `milestone_forecasts`, EP-10) ; les réexamens par `core/risks` (EP-08) ; les
imports par `core/costs` (EP-09). À une date passée, les jalons se lisent de ce que le marquage a
conservé (US-2680).

**Hors périmètre.** Le suivi temps/temps d'un projet (EP-10) ; l'écran (US-2760).

---

## US-2760 — Les écrans du portefeuille, branchés sur le service

- **statut** : fini
- **exigences** : `WF-IHM-0130-A`, `WF-IHM-0140-A`
- **opérations** : `getPortfolioProjects`, `getPortfolioValue`, `getPortfolioWorkload`,
  `getPortfolioPerformance`, `getPortfolioCostStructure`, `getPortfolioRisks`,
  `getPortfolioCostCurve`, `getPortfolioPilotHealth`, `getMe`, `updateMyPreferences`
- **issue** : #3867

**En tant que** manager, **je veux** les sept écrans du portefeuille sur les données du service,
avec leurs filtres, leurs exports et leur aide, **afin de** m'en servir comme la maquette me les a
montrés.

**Critères d'acceptation.**

- `WF-IHM-0130-A` — « La liste des projets filtrée sur un état ne compte que les projets de cet état
  dans ses totaux. » : tenu par EP-25 (US-2080) pour la liste des projets ; ici, la liste du
  portefeuille filtrée sur un état, contre le service ;
- `WF-IHM-0130-A` — « Le plan de charge d'un projet exporté est une image PNG qui porte le nom du
  projet, la révision et la date de calcul ; le plan de charge agrégé exporté porte le périmètre et
  la date de calcul. » : le plan de charge d'un projet est tenu par EP-25 (US-2160) et EP-10 ; ici,
  le plan de charge agrégé, exporté contre le service ; la courbe en S, la performance et la matrice
  des risques portent de même le périmètre et la date de calcul ;
- `WF-IHM-0130-A` — « La table des calendriers ne propose aucun filtre sur les heures de ses jours ;
  elle se filtre sur ses autres colonnes. » : tenu par EP-15 (US-0570), non touché ici ;
- `WF-IHM-0140-A` — « Chaque écran ouvre une aide qui le concerne. » : tenu par EP-16 (US-0670) ;
  ici, constaté contre le service sur chaque écran de la table des fonctions, les sept du
  portefeuille compris ;
- `WF-IHM-0140-A` — « Dans la grille de devis, l'intitulé de la colonne du montant corrigé de
  l'inflation porte une infobulle qui nomme l'année de référence et le taux d'inflation. » : tenu
  par EP-15 (US-0580) contre le faux back ; ici, constaté contre le service, l'année et le taux
  étant ceux de la révision lue ;
- `WF-IHM-0140-A` — « L'aide s'affiche dans la langue de l'utilisateur. » : tenu par EP-16
  (US-0670b), non touché ici ;
- propre à l'US : la liste des projets offre dans son panneau un filtre par colonne — ceux
  qu'US-2690 ajoute au contrat —, portés par l'adresse, chacun dit par sa pastille, panneau fermé ;
- propre à l'US : les parcours du portefeuille se jouent contre le service sur le témoin chargé
  avec la tranche du portefeuille ; ce qui affirmait les trois cents projets du faux back reste joué
  contre lui seul, et se rejoue contre le service en EP-13 ;
- reporté → EP-38 (décision de l'utilisateur du 2026-11-21 soir) : un périmètre qui nomme
  `completed` se lit sur le plan de charge agrégé et la santé du pilotage, avec l'avis que ces
  projets y sont sans effet (#1714) ;
- propre à l'US : un identifiant de l'adresse qui n'est pas un UUID est ignoré comme un identifiant
  absent, par la fonction du référentiel et non plus par une copie (#2867) ; reporté → EP-37
  (décision de l'utilisateur du 2026-11-21 soir) : la copie d'`IDENTIFIER` de la navigation
  (`navigation/context.ts`) corrigée de même (#4160, décision du 2026-11-19) ; celle du registre
  des risques reste à EP-08 ;
- reporté → EP-38 (décision de l'utilisateur du 2026-11-21 soir) : le contrat reçoit l'exemple d'un
  422 de `getPortfolioProjects` sur la période du périmètre (#4164), que le test de l'écran lit, et
  l'exemple `portfolio_projects` montre une probabilité de gain nulle pour un projet en cours
  (#4137), décisions du 2026-11-19 ;
- propre à l'US : un projet que l'appelant ne peut pas ouvrir est nommé sans lien, dans la liste,
  les risques les plus lourds et les signaux ; aucun écran ne porte de commande de saisie ;
- propre à l'US : le guide de l'utilisateur dit ce que le service sert désormais.

**Notes de réalisation.** Les écrans existent (EP-02, EP-14, EP-15, EP-17) dans la mise en page
d'EP-25 (US-2150) : le travail est la levée des gardes `inService` des parcours, le panneau des
filtres de la liste, et ce que le service rend autrement que le faux back. Le client est engendré
(`make generate-client`).

**Hors périmètre.** Toute refonte d'un écran ; un export de données du portefeuille
(WF-INTF-0150).

---

## US-2770 — Le témoin : la tranche du portefeuille, et le parcours du manager

- **statut** : fini
- **exigences** : `WF-QUA-0040-A`, `WF-INTF-0020-A`
- **opérations** : les huit opérations du portefeuille ; `getReferenceSettings`,
  `updateReferenceSettings`, `listProjects`, `getProject`
- **issue** : #3869

**En tant que** manager, **je veux** un jeu de données où le portefeuille a de quoi sommer, et y
mener mon parcours de bout en bout, **afin de** constater mes usages sur le service et de rejouer
les mêmes lectures à chaque version.

**Critères d'acceptation.**

- écart : `WF-QUA-0040-A` — « L'engendrement du jeu aboutit sur une plateforme neuve et produit les
  volumes annoncés. » : les volumes du §4.6.2 sont d'EP-13, qui clôt ; ici, `waterfall-api
  load-witness` charge sur une plateforme neuve la tranche du portefeuille à côté de PRJ-001 et de
  PRJ-002 ;
- `WF-QUA-0040-A` — « Deux engendrements successifs donnent des données identifiantes identiques. »
  : les identifiants de la tranche sont imposés par le témoin ; un second chargement ne change
  rien ;
- `WF-QUA-0040-A` — « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. » :
  les projets de la tranche portent les libellés engendrés du témoin, et leurs comptes le domaine
  `waterfall.test` ;
- `WF-INTF-0020-A` — « Un utilisateur porteur du rôle prédéfini « manager » mène à leur terme le
  paramétrage de chacune des fonctions FBS-3.1 à FBS-3.4 — nœuds d'organisation, rôles de
  ressources, calendriers, natures et catégories de coût, taux horaires, correspondance de
  l'extraction des coûts réels, bornes de la matrice de risques, seuils d'alerte, délai maximal
  entre deux revues —, ouvre les vues du portefeuille (FBS-2), lesquelles portent sur l'ensemble des
  projets, et ouvre un projet dont il n'est pas contributeur. » : le paramétrage est tenu par EP-05
  (US-0900) ; ici, un parcours de bout en bout, contre le service, où le manager ouvre chacune des
  sept vues du portefeuille, puis, depuis la liste, un projet dont il n'est pas contributeur ;
- propre à l'US : la tranche compte une dizaine de projets — des offres de probabilités
  différentes, dont une marquée, un projet terminé dans la période par défaut, une offre perdue et
  une abandonnée, des projets en cours dont un en alerte et un dont la revue est en retard —,
  chargés par les interfaces des modules du noyau, jamais par un `INSERT` ;
- propre à l'US : les lectures attendues des huit vues sur le témoin ainsi chargé sont engendrées
  par `make mock-data`, par un calcul que le back ne réemploie pas, et comparées aux réponses du
  service ; un désaccord est arbitré par la spécification ;
- écart : les exemples du contrat à trois cents projets (`volume/portfolio_*`, `portfolio_workload`,
  `portfolio_cost_curve`, `pilot_health`) ne sont pas comparés ici, et ne le seront pas : EP-13
  charge les trois cents projets, mais le témoin reste l'oracle des valeurs, et ces exemples
  restent ceux du faux back (décision de l'auteur du 2026-11-18, au cadrage d'EP-13, « Conception »,
  qui remplace « EP-13 […] les compare ») ;
- propre à l'US : le README de la roadmap nomme cette tranche (« Le jeu de données de référence »).

**Notes de réalisation.** La tranche s'insère dans la marche des événements du chargeur
(`witness`), après celle des risques et des avenants d'EP-08. Le parcours du manager prolonge celui
du paramétrage (`reference-*.spec.ts`).

**Hors périmètre.** Les trois cents projets et les volumes du §4.6.2 (EP-13).

---

## US-2780 — Les exemples chiffrés ont tous leur test, chaque calcul une seule implémentation

- **statut** : fini dans EP-11 — L2 reporté à EP-36, L4 retiré (« Reprise du 2026-11-21 soir »)
- **exigences** : `WF-QUA-0020-A`, `WF-ARC-0010-A`, `WF-INTF-0150-A`
- **opérations** : aucune en propre
- **issue** : #3859

**En tant que** développeur, **je veux** que la chaîne refuse un exemple chiffré sans test, un
calcul écrit deux fois et un échange hors du tableau des flux, **afin qu'** une réécriture ne défasse
pas en silence ce que le document a décidé.

**Critères d'acceptation.**

- `WF-QUA-0020-A` — « Pour chacun des exemples chiffrés du document, un test porte les mêmes entrées
  et attend la même valeur. » : chaque exemple du relevé (`fixtures/examples.json`) qui est un
  calcul du noyau a un test du harnais qui le cite ; les tests qui manquent aux exemples des EPIC
  livrés sont écrits ici ; `make check-fixtures` échoue sur un exemple qui n'a ni test ni
  déclaration hors harnais ;
- `WF-QUA-0020-A` — « La modification d'une constante de calcul fait échouer au moins un de ces
  tests. » : éprouvé par mutation sur les constantes de chaque famille de calcul que le corps de
  l'exigence nomme — dates et chemin critique, montants et inflation, reste à engager, provisions,
  valeur acquise, indices et projections, agrégations de portefeuille ;
- `WF-QUA-0020-A` — « Leur exécution complète ne demande ni base de données ni navigateur. » : tenu
  par EP-01 (US-0040) ; le harnais, étendu, bloque toujours le réseau ;
- `WF-ARC-0010-A` — « Le dépôt ne contient qu'une implémentation de la machine d'état, des calculs
  de planning, de chiffrage et d'indicateurs, partagée par l'API et le worker. » : un contrôle de la
  chaîne constate que l'API et le worker n'importent ces calculs que du noyau, que ni l'un ni
  l'autre n'en définit, et que le portefeuille applique à des sommes les formules d'EP-10 sans les
  récrire ; les générateurs du faux back (`wftools`), qui ne sont pas livrés, restent un calcul
  indépendant, par la règle du jeu de données de référence ;
- `WF-ARC-0010-A` — « Un module qui lit une table d'un autre module est rejeté par les contrôles de
  la chaîne CI/CD. » : tenu par EP-01 (US-0010) ; le module du portefeuille entre au contrat de
  couches ;
- `WF-ARC-0010-A` — « L'API et le worker d'une installation portent la même version. » : tenu par
  EP-01 (US-0010), non touché ici ;
- `WF-INTF-0150-A` — « Chaque fonction d'import ou d'export de données de projet présente dans
  Waterfall correspond à un flux du tableau et à l'exigence que ce tableau lui associe ; les exports
  d'images et les sauvegardes sont les seules fonctions d'échange hors tableau. » : un test
  confronte les opérations du contrat qui déposent ou rendent un fichier au tableau des flux de la
  spécification ; aucune opération du portefeuille n'en est ;
- propre à l'US : les exemples chiffrés du relevé qui ne sont pas un calcul du noyau —
  exploitation, observabilité, front — sont déclarés hors du harnais dans une liste versionnée,
  chacun avec sa raison et l'EPIC qui le prouve autrement (décision de l'auteur du 2026-11-17) ;
- propre à l'US : `make requirements` ne laisse sans test du back aucune des exigences que cet EPIC
  clôt.

**Les exemples à barre oblique** (#4022, décision du 2026-11-19). WF-CRE-0020-A#327d63bf4748,
WF-CRE-0020-A#80d94ea6d2fe et WF-PRJ-0050-A#38958d887e9a entrent au harnais avec le lot qui réalise
#3966 (l'élément d'OTP comparé en entier, spécification 1.0.7), non avec un lot de cet EPIC : le
noyau refuse encore ces codes. **Aucun lot de l'EPIC ni d'un autre EPIC ne réalise #3966 à ce
jour** (issue sans EPIC) ; ce lot reste à nommer quand #3966 sera planifié, et c'est lui qui écrit
ces trois exemples dans `backend/tests/examples/test_wbs_element_examples.py`. Ils restent hors de la
liste versionnée des exemples hors du harnais, qui ne reçoit que ce que le noyau ne calcule pas.

**La reprise du noyau** (#4372, #4373, #4363, décision du 2026-11-21) : le contrôle de L3 constate ce
que le noyau ne tenait pas encore ; US-2780/L4 reprend les doublons que L3 a trouvés, retire
l'exemption de `tools/implementations.toml` et ferme les motifs `\d` : voir « Décisions de l'auteur
du 2026-11-21 ». Il ne ferme aucun critère de plus : il tient celui de `WF-ARC-0010-A` sur « qu'une
implémentation ».

**Notes de réalisation.** Le relevé compte 98 exemples au cadrage ; les exemples d'EP-10 et d'EP-08
entrent au harnais par leurs propres lots. Le harnais est `backend/tests/examples`, l'outil
`wftools.examples`.

**Hors périmètre.** Les exemples d'exigences qu'EP-13 clôt et qui ne sont pas des calculs du
noyau ; la traçabilité des exigences par les tests (WF-QUA-0010, EP-13).

---

## US-2790 — Les vues du portefeuille sont mesurées

- **statut** : reporté → EP-40 (« Reprise du 2026-11-21 soir »)
- **exigences** : aucune en propre — l'outil de WF-QUA-0060, que clôt US-2300 (EP-26)
- **opérations** : `getPortfolioProjects`, `getPortfolioValue`, `getPortfolioWorkload`,
  `getPortfolioPerformance`, `getPortfolioCostStructure`, `getPortfolioRisks`,
  `getPortfolioCostCurve`, `getPortfolioPilotHealth`
- **issue** : #3868

**En tant qu'** exploitant, **je veux** les durées des vues du portefeuille dans le rapport de
mesures, **afin de** savoir si elles tiennent leur objectif avant de publier la version.

**Critères d'acceptation.**

- propre à l'US : `make measure` et `make measure-version` mesurent, sur le témoin chargé avec la
  tranche du portefeuille, l'ouverture de chacune des sept vues, du clic à l'affichage, au jour
  courant et à une date passée, face à l'objectif de deux secondes du tableau 15 (« Afficher une vue
  de portefeuille sur trois cents projets ») ;
- propre à l'US : `make measure-core` relève la durée de chaque vue dans le noyau, et le nombre de
  ses requêtes ;
- propre à l'US : le rapport de la version porte ces durées ; la ligne « non servie : portefeuille
  (EP-11) » en disparaît ;
- écart : les trois cents projets de l'objectif sont à EP-13, qui rejoue la mesure sur le jeu aux
  volumes ; le rapport le dit ;
- propre à l'US : les mesures existantes tiennent leurs objectifs et ne se dégradent pas de plus
  d'un quart ; un dépassement documenté passe, non documenté il fait échouer la chaîne (US-2300) ;
- propre à l'US : la mesure décide du coût de la lecture du jour projet par projet (`day_documents_of`,
  neuf requêtes par projet au cache chaud ; la performance au jour courant, #4165 et #4177, décision du
  2026-11-19) : aucune vue ne change avant elle, et une vue du jour qui dépasse son objectif ouvre un
  lot neuf de groupement des empreintes.

**Notes de réalisation.** La mesure prend le poste pour elle seule (`docs/dev/agents.md`, « Une
mesure prend le poste »). Le rapport est versionné dans `docs/measures/`.

**Hors périmètre.** Un objectif nouveau ; la mesure à l'échelle (EP-13).
