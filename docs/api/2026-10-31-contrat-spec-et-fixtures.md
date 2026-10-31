---
revue_du: 2026-10-31
sur: >-
  le contrat d'interface docs/api sur epic/EP-16 (c3d080fb, info.version 1.0.0-draft : 168
  opérations, 130 chemins, 13 familles), ses fixtures (fixtures/api, 724 fichiers dont 20 de
  volume, 723 références depuis le contrat) et la spécification waterfall-spec.md en révision
  1.0.1 du 2026-10-30
revue_par: Claude Code (Fable 5.1) — neuf relectures par famille, une transversale, une de cohérence des fixtures, une consolidation
perimetre: >-
  le contrat entier, trois jours après la revue du 2026-10-28 et après la livraison d'US-0701,
  US-0702, US-0680, US-0700, US-0640/L6 et US-0660 ; hors ce que portent les lots encore ouverts
  (US-0640/L5 #1333 le gel, US-0640/L6b #1594, la part écran d'US-0703)
---

# Revue du 2026-10-31 — le contrat, la spécification 1.0.1 et les fixtures

## Pourquoi cette revue, et comment elle a été faite

La revue du 2026-10-28 (`2026-10-28-contrat-avant-gel.md`) concluait que le contrat ne pouvait pas
être figé sans rompre avec la spécification 1.0.0 : 4 bloquants, 83 majeurs, 87 mineurs. Le
recadrage du même jour a ouvert US-0701 (le modèle et les règles de calcul), US-0702 (la forme des
refus) et US-0703 (les écrans) ; US-0701 et US-0702 sont livrées, US-0703 est en cours et ne touche
pas le contrat. La spécification est passée en 1.0.1 le 2026-10-30 (cinq exigences : WF-IHM-0110,
WF-PLA-0130, WF-RAE-0020, WF-REV-0080, WF-SEC-0020). Le gel (US-0640/L5) vient en dernier.

Cette revue repart du contrat entier, sans se limiter au suivi de la précédente : chaque opération
est relue contre les exigences qu'elle cite et contre les sections de la spécification de son
domaine, chaque fixture référencée est ouverte et confrontée à sa description, à l'opération et à
l'univers témoin de `DECISIONS.md`, et chaque constat de la revue du 2026-10-28 reçoit un état
(réglé, partiellement réglé, non réglé, sans objet).

La revue part d'un contrat formellement sain : `make lint-openapi` passe (le jeu de règles
`recommended-strict` de Redocly valide chaque exemple référencé contre son schéma, aucune fixture
n'est donc invalide au sens du schéma), `make check-fixtures` passe (chaque exemple numérique cité
existe), `make inventory` est à jour (168 opérations, 189 des 212 exigences citées), et une seule
fixture n'est référencée par aucun fichier du contrat (`risk_matrix_no_basis.json`).

Onze relectures ont été menées en parallèle :

- neuf par famille — A système, compte courant, comptes et habilitations ; B sauvegarde,
  restauration, paramètres de plateforme et journal d'audit ; C référentiel ; D projets ; E révisions
  et structures ; F arbre commun ; G indicateurs et portefeuille ; H risques ; I coûts réels et
  échanges ;
- une transversale (J) : composants partagés, conventions du README, relevé par script des codes,
  conditions et paramètres d'erreur sur les 168 opérations, couverture des exigences, delta 1.0.1,
  décisions annoncées sans réalisation, opérations qu'aucun écran n'appelle ;
- une de cohérence des fixtures (V) : identifiants, totaux, dates, états et commandes, enveloppes
  d'erreur, volumes, descriptions, exemples numériques, croisés par script sur les 724 fichiers.

Les gravités sont celles de la revue précédente : **bloquant**, le contrat contredit frontalement la
spécification ou ne peut pas être servi tel quel ; **majeur**, un changement incompatible à prévoir
après le gel si on ne le fait pas maintenant, ou un implémenteur se tromperait ; **mineur**, clarté,
exemple ou description, corrigible sans rompre le contrat.

## Ce que la revue exclut

La version `1.0.0` et la règle d'après-gel (US-0640/L5 #1333) ; `project_create` et
`revision_abandon` dans `AuditAction` et leurs paramètres (US-0640/L6b #1594) ; la part écran des
constats (US-0703). Ne sont pas signalés non plus les choix que `DECISIONS.md` assume quand ils ne
contredisent pas la spécification 1.0.1.

## Ce qui ressort

### 1. Le rattrapage a eu lieu : les bloquants et les majeurs du 28 octobre sont réglés

C'est le constat qui domine, et il est positif. Sur les 198 lignes de suivi des onze annexes (les
174 constats du 2026-10-28 et leurs doublons K, L, M suivis sous leur propre numéro), **177 sont
réglées, 10 partiellement, 9 non réglées, 2 sans objet**. Les quatre bloquants (inflation comprise,
date de début de planning, sortie du cycle de vie, coût à la survenance) et les 83 majeurs sont tous
réglés ou en voie de l'être, à la ligne et le plus souvent exactement comme la revue le proposait :
`ProjectExit` porte le sort de la révision en cours ; `CostStructure` sa date de début de planning ;
`Risk.occurrence_cost` est exigé et sommé par la couverture ; les courbes sont au pas du mois et
conservées au marquage ; le journal des imports compte quatre nombres ; le projet terminal est un 409
`project_not_terminal` sur chaque écriture ; les codes morts ont quitté le catalogue ; chaque
opération déclare son 500. Les fixtures ont suivi : l'annexe V recalcule au centime les totaux, les
parts et vingt-cinq égalités croisées du témoin sur 724 fichiers, sans un identifiant qui désigne deux
objets.

Les 9 non réglés et les 10 partiels sont tous repris comme constats de cette revue, sous leur nouveau
numéro : les compteurs de version du témoin (E-16 → E-09), la chronologie des sauvegardes de 14 h 04
(B-07 → B-05), le corps anonyme d'`applyRateUpdate` (E-21 → E-03), la révision en cours dans la
comparaison (E-23 → E-07), le résumé de `merge_revision_marked_refused` (E-17 → E-08), la fixture
orpheline `risk_matrix_no_basis` (J-21 → H-08), le pointeur `/body` (J-14 → J-10), `StructureCreate.kind`
sans `type` (J-19 → J-09), `Limit`/`Offset`/`Year` muets (J-20 → J-07), l'exemple du 409 d'`applyPaste`
(F-17 → F-10), le résidu des champs exigés (G-02 → G-03), `may_create_revision` (H-09 → H-04),
l'enveloppe des tâches fusionnées (M-05 → H-03), l'abandon d'un import appliqué (I-18 → I-02), les
exemples des imports (I-20 → I-07), `listRiskReviews` sans pages (J-12 → J-11), `task_not_milestone`
sans exemple (J-18 → J-12), trois résumés sur « le budget de référence » (C-04 → C-03), la proposition
de taux après acceptation (E-18 → E-06).

### 2. Aucun bloquant ; 31 majeurs, dont la plupart demandent une décision plutôt qu'un travail

Le contrat ne contredit plus frontalement la spécification 1.0.1 sur aucun point. Les 31 majeurs se
rangent en six thèmes.

- **Des règles de la spécification que le contrat ne porte pas encore.** Les lignes d'une tâche
  terminée restent saisissables (`editable_fields` les nomme, `updateEstimateLine` et `deleteNode` ne
  les refusent pas) quand WF-DEV-0050 et WF-RAE-0040 les ferment (F-01, à la frontière du bloquant) ;
  une sous-tâche créée ou déplacée sous un jalon n'a aucun refus, WF-PLA-0050 (F-04) ; les lignes
  propres ouvertes d'une récapitulative dont toutes les subordonnées sont terminées n'ont aucun
  attribut, WF-PLA-0040 et WF-IHM-0070 (F-05) ; le registre des risques ne se filtre que par état et
  zone quand WF-IHM-0130 veut chaque colonne et que les totaux sont ceux du serveur (H-01) ; une ligne
  nouvelle importée sous une tâche terminée n'a aucun motif de rejet au compte rendu, WF-INTF-0100 et
  WF-INTF-0120 (I-05) ; la révision suivante ne reprend pas le différentiel fusionné de la référence,
  contre « toutes les structures » de WF-REV-0100, et le contrat ne le dit pas (E-04) ; « conserve les
  taux de la révision source » oublie « projetés par l'inflation jusqu'à la nouvelle année de
  référence », WF-REV-0060 (E-05) ; l'écart par clé de la comparaison n'est pas défini pour une ligne
  qui change de nature ou de sous-projet, et le témoin en dépend tout entier (E-01).
- **Deux décisions que la spécification 1.0.1 contredit.** La modification d'un risque est, au
  contrat, une saisie de la révision en cours, créée au besoin et annulable (décision 1548–1551), quand
  WF-RIS-0020 et le §4.4.1 rangent libellé, description et mitigation dans les données du projet et que
  WF-IHM-0110 ne les annule pas — `abandonRevision` le dit déjà à l'inverse d'`undoLastChange` (H-02).
  `getIndexHistory` promet un point « non calculable, jamais omis » pour une révision marquée avant
  l'état En cours, quand WF-IND-0130, WF-DAT-0040, son propre schéma et sa fixture n'en donnent aucun
  (G-01).
- **Le delta 1.0.1.** WF-IHM-0110 (annulation tenue par le serveur), WF-RAE-0020 (marge, signe) et
  WF-PLA-0130 (date de la revue du fichier) étaient déjà portés : la spécification a rejoint le
  contrat. WF-SEC-0020 (adresse de retour) n'a pas de surface d'API. WF-REV-0080 reste à compléter :
  la règle du `reestimated_delta` « après une fusion » a perdu « de même année de référence » et
  contredit mot pour mot la fixture témoin, offre de 2025 comparée à la référence de 2026 (E-02).
- **Des refus sans forme, reste d'US-0702.** La règle unique des refus d'état est appliquée partout,
  sauf : deux refus qu'une commande dit d'avance et que l'API refuse par un code propre
  (`CURRENT_REVISION_EXISTS`, `REFERENCE_NOT_CORRECTABLE`), seule contradiction restante du README,
  assumée par une décision d'EP-15 qu'US-0702/L1 n'a pas réécrite ; `no_current_revision` est la seule
  des 58 conditions qu'aucune opération ne nomme (J-01) ; l'application d'un import expiré ou déjà
  appliqué sans condition, et l'import refusé dont le fichier est supprimé laissé `analysed` (I-01) ;
  l'abandon d'un import appliqué, que le contrat déclare lui-même laisser sans forme (I-02) ; le
  « fichier déjà consommé », 409 sans condition qu'une autre phrase dit 404 (I-03) ;
  `no_background_task_running` et `may_create_revision`, annoncés par les commandes `import_*` et
  absents du 409 d'`openImport` (I-04) ; `getIndexHistory` et `getMilestoneTracking` sans le 409 d'un
  projet antérieur à En cours que les trois autres lectures déclarent (G-02) ; la planification des
  sauvegardes écrite sans refus pendant une restauration, quand le marquage est refusé pour la raison
  même que la base va être remplacée (B-02) ; le lien de fixation et le renvoi de l'invitation refusés
  par `is_local_account`/`is_active_account` qu'aucune commande d'`UserCommand` ne dit d'avance (A-04).
- **Qui lit, qui écrit.** `createUser` attribue des rôles sans la permission `access_roles.write`
  qu'exige `setUserAccessRoles` pour le même geste (A-01) ; `listUsers` emprunte `IncludeInactive`,
  dont la description promet un 403 que l'opération ne déclare pas et que WF-ADM-0060 n'appelle pas
  (A-03) ; six lectures du référentiel déclarent un 404 « faute de permission de consultation » sans la
  nommer, ou dit inatteignable par leur propre description, et trois permissions de consultation
  n'ouvrent plus rien depuis que la devise se lit par toute session — question qu'US-0702/L2 a
  explicitement laissée ouverte (C-01) ; `PortfolioStates`, paramètre partagé, dit qu'un projet créé,
  perdu ou abandonné nommé dans `states` est « sans effet », et `listProjects` s'en sert pour l'accueil
  qui liste les six états (D-01).
- **Compteurs, corps, énumérations et exigés : ce qui ne se change plus après le gel.**
  `deleteAccessRole` et `deleteTimeline` sont des suppressions sans `lock_version` ni 412, contre la
  convention (A-02) ; `applyRateUpdate` laisse `lock_version` facultatif, sa liste sans borne et son
  corps anonyme (E-03) ; la création d'une tâche datée exige les heures que le front ne connaît pas,
  `TaskFacetWrite.start` restant un `WorkInstant` quand la modification est en `WorkInstantWrite`
  (F-03) ; `AuditUserField` ne peut pas nommer le rattachement à un nœud d'organisation qu'`updateUser`
  change (B-01) ; un résidu de champs toujours rendus mais facultatifs que la règle de G-02 n'a pas
  atteints — huit colonnes de `PortfolioProjectRow`, les deux écarts de `RemainingIndicators`,
  `Computable.value` (G-03) ; `max_length`, promis par `ProjectCode` (50) et `Problem.params` (31), que
  les cinq fixtures `VALUE_TOO_LONG` ne portent pas (J-02).

Deux majeurs tiennent à une fixture plutôt qu'au contrat : la suppression `node_deleted_provision_moved`
termine une récapitulative non démarrée et la date dans le passé, contre « rien ne se termine seul »
(F-02) ; la seule image du résultat d'une survenance, `nodes_risk_occurred`, place les tâches
fusionnées sous une tâche d'enveloppe 541 que ni WF-RIS-0060 ni l'opération ne connaissent, quand le
compte rendu du risque 751 les met directement sous la porteuse (H-03).

### 3. Les mineurs : des exemples, des descriptions, et un mécanisme qui tourne à vide

Les 89 mineurs se répartissent en quatre groupes. **Les exemples manquants** : 24 opérations déclarent
le 412 sans exemple, la réponse partagée `PreconditionFailed` n'en portant aucun (J-03) ; une
vingtaine de 409 déclarés n'ont pas l'exemple du code ou de la condition qu'ils nomment (J-04, D-02,
A-08, C-05, E-11, F-10, G-06, H-07, I-07) ; des variantes de lecture sans exemple (G-08, E-18). **Les
descriptions** : 110 propriétés nullables sans règle de nullité dite (J-14) ; `Limit`, `Offset`,
`Year`, `PaginationMeta` muets (J-07) ; des champs toujours rendus non exigés (D-11, E-10, A-05, I-06) ;
des paramètres sans défaut dit (`finished_since`, `ExportRequest.depth`, `revision_id` de trois
opérations, `as_of` hors période) ; l'arrondi au centime des montants inflation comprise, que les
fixtures font au pair sans qu'aucune règle le dise (F-06) ; le même nom `delta_to_reference` pour une
marge et pour un écart de signes opposés, que la 1.0.1 nomme désormais « marge » (G-04, V-05). **Les
fixtures** : les compteurs de version se contredisent d'une fixture à l'autre (E-09, V-03) ; la
chronologie des sauvegardes du 3 juin à 14 h 04 se contredit toujours (B-05, V-04) ; deux fixtures du
portefeuille ignorent le monteur câbleur que le témoin emploie depuis EP-02/L27 (G-10) ; le journal du
témoin n'inscrit pas les premiers rôles des comptes créés avec eux (B-03) ; `risk_matrix_no_basis.json`
reste orpheline alors qu'un test du front la lit (H-08) ; un 409 `STATE_FORBIDS_OPERATION` sans aucun
paramètre, seul de ses 75 (V-02). **Le mécanisme des exemples numériques** : `fixtures/examples.json`
liste 92 exemples des Vérif, aucune fixture n'en cite un, et `make check-fixtures` passe à vide —
dix exemples sont reproduits par le témoin sans être cités, deux ne le sont pas (V-01, H-10, I-10) ; le
mécanisme est prévu pour les fixtures du cœur (WF-QUA-0020), mais rien ne le dit.

### 4. Ce que la revue n'a pas trouvé

Aucune référence de fixture cassée, aucun statut de fixture différent de sa réponse, aucun code hors
catalogue, aucun code mort, 57 des 58 conditions nommées par une opération, 0 `type: number`, 404 sur
les 130 chemins paramétrés, `explode: false` partout, 161 des 168 opérations appelées par le front et
les 7 autres justifiées (sondes, lectures unitaires doublées par leur liste, `undo`/`redo` que la part
écran d'US-0703 branche). Les décisions d'EP-16 annoncées dans `DECISIONS.md` sont toutes dans le
contrat, à un écart de mots près (J-15). Les 23 exigences non citées ont chacune une raison qui tient,
sauf WF-EXP-0030, qui a une surface (`SystemStatus.version`) que personne ne cite (J-16).

## Ce qu'il faut trancher avant le gel

Les points que la revue ne peut pas décider seule, par ordre de conséquence sur la forme du contrat.
Chacun change un statut, une énumération, un exigé ou le sens d'un champ : après le gel, ce sont des
changements incompatibles.

1. **La modification d'un risque** (H-02) : suivre la spécification (le libellé, la description et la
   mitigation sont des données du projet, hors de la révision et de l'historique annulable ; seule la
   part provision est une saisie de la révision) ou faire écrire à la spécification la forme du
   contrat ; dans les deux cas, réécrire la décision 1548–1551.
2. **Les lignes d'une tâche terminée** (F-01) : `editable_fields` vide, ou le seul libellé ; le 409
   `task_not_completed` sur `updateEstimateLine` et `deleteNode`.
3. **La reprise du différentiel fusionné** (E-04) : la révision suivante le reprend, `is_merged`,
   et `structures.json` reçoit l'avenant 1 ; ou le contrat dit l'exception et WF-REV-0100 est à
   corriger.
4. **Les deux codes propres** (J-01) : `STATE_FORBIDS_OPERATION` avec `no_current_revision` et
   `reference_correctable`, les deux codes retirés du catalogue ; ou l'exception écrite au README.
5. **Qui lit les objets actifs du référentiel** (C-01) : toute session ouverte, et le 404 quitte les
   six lectures ; ou `resource_settings.read`/`cost_settings.read` nommées et le 404 gardé.
6. **Les énumérations** : `UserCommand` avec `create_password_link` et `resend_invitation` (A-04) ;
   `AuditUserField` avec `org_node_id` (B-01) ; le motif d'une ligne importée sous une tâche terminée
   (I-05 : `STATE_FORBIDS_OPERATION`/`task_not_completed` ou un code propre) ; le refus d'une
   sous-tâche sous un jalon (F-04 : 422 sur `/parent_id` ou 409 `parent_not_milestone`).
7. **Les imports** : la condition d'un compte rendu expiré ou déjà appliqué et l'état d'un import
   refusé dont le fichier est supprimé (I-01 : condition `import_applicable` ou 404, statut `refused`
   ou `expires_at` nul) ; l'abandon d'un import appliqué (I-02) ; le « fichier déjà consommé » en 404
   (I-03).
8. **Les lignes propres ouvertes d'une récapitulative** (F-05) : un booléen calculé sur `TaskFacet`,
   ou une autre forme.
9. **La planification des sauvegardes pendant une restauration** (B-02) : refusée par
   `no_restore_running`, ou gardée à travers la restauration, ce que la spécification ne dit pas.
10. **`createUser` et les rôles** (A-01) : exiger `access_roles.write` pour une liste non vide, ou
    retirer `access_role_ids` du corps. **`listUsers` et les désactivés** (A-03) : lisibles sous
    `users.read`, ou 403 déclaré.
11. **`PortfolioStates`** (D-01) : un paramètre propre à `listProjects`, ou la phrase « sans effet »
    renvoyée aux vues.
12. **Le nom `delta_to_reference`** (G-04, V-05) : `margin_to_reference` sur les indicateurs du
    reste à engager, ou le double sens consigné.
13. **L'enveloppe 541 de la survenance du témoin** (H-03) : tâche racine du devis propre, à
    renommer et à montrer avant la fusion, ou enveloppe à retirer.
14. **Le 409 sans paramètre** de `getProjectIndicators` sur une offre (V-02) ; et l'écart par clé de
    la comparaison (E-01), où le générateur a fait le seul choix qui donne un sens à « par
    sous-projet » et où le contrat doit le dire.

## Recommandation

Le contrat est prêt à être figé sur le fond : il ne contredit plus la spécification 1.0.1, et ses
fixtures racontent un seul univers. Il ne l'est pas encore sur la forme de 31 points, qui changeraient
tous un statut, une énumération, un exigé, un corps ou le sens d'un champ après le gel. La revue
propose :

- **un lot de contrat avant le gel**, dans la lignée d'US-0701 et d'US-0702, en deux parts qui ne
  touchent pas les mêmes fichiers : le modèle et les règles (F-01, F-03, F-04, F-05, H-01, H-02, E-01,
  E-02, E-04, E-05, G-01, G-03, I-05, B-01, A-04) et les refus, compteurs et permissions (I-01 à I-04,
  G-02, B-02, J-01, J-02, A-01, A-02 avec `deleteTimeline`, A-03, C-01, D-01, E-03) ; chaque part
  réécrit les décisions contredites (1548–1551, 7087, 7285, 2407) et régénère les fixtures en cause
  (F-02, H-03, J-02, E-09, B-05, G-10) ;
- **les mineurs après le gel**, en issues « contrat », sauf ceux d'un fichier que le lot modifie déjà
  (les exemples manquants des 412 et des 409 se règlent d'un coup dans les générateurs, J-03 et J-04 ;
  les champs exigés, D-11, E-10, A-05, I-06, avec G-03) ;
- **les quatorze questions ci-dessus**, à poser à l'auteur en une fois, parce que plusieurs changent
  la forme du lot (H-02, F-01, E-04, J-01, C-01) ; et, côté spécification, trois points à ouvrir :
  WF-REV-0100 si la reprise exclut les différentiels fusionnés (E-04), WF-RIS-0020 si la modification
  reste une saisie de la révision (H-02), et la conservation de la planification des sauvegardes à
  travers une restauration (B-02).

Le gel (US-0640/L5) vient après ce lot, comme la décision du 2026-10-28 le prévoit déjà pour les
derniers lots de l'EPIC.

## Le suivi de la revue du 2026-10-28

Chaque annexe porte une table « Suivi des constats du 2026-10-28 » qui donne, constat par constat,
l'état et l'emplacement de la correction. Le total :

| État | Lignes de suivi |
|---|---|
| réglé | 177 |
| partiellement réglé | 10 |
| non réglé | 9 |
| sans objet | 2 |

Les deux sans objet sont des choix assumés par `DECISIONS.md` que la spécification ne contredit pas :
`labor` et `LABOUR` coexistent (C-08, « Vocabulaire ») ; `cycle` et `link` restent des paramètres
ouverts (E-25, US-0640/L3). Les partiels et les non réglés sont les constats de cette revue nommés au
§ 1 de « Ce qui ressort ».

## Tableau général des constats

Un constat par ligne, fusionné quand plusieurs relectures l'ont trouvé (« aussi » nomme les
doublons, dont le détail figure dans leur annexe) : **127 constats bruts, 120 après fusion — 0
bloquant, 31 majeurs, 89 mineurs.** L'emplacement est le premier que l'annexe cite ; l'annexe donne
les autres, la citation de la spécification, ce que dit le contrat, ce que dit la fixture, la
proposition et la décision de `DECISIONS.md`. Neuf majeurs ont été vérifiés une seconde fois, à la
ligne, par la consolidation (A-02, D-01, E-02, E-03, F-01, F-03, G-01, J-01, J-02) : tous tiennent.

### Majeurs (31)

| # | Famille | Emplacement | Constat | Exigence |
|---|---|---|---|---|
| A-01 | A | `paths/access.yaml:157-217` | `createUser` attribue des rôles sans la permission de modifier les rôles | WF-ADM-0090, WF-ADM-0120 |
| A-02 | A | `paths/access.yaml:949-976` | `deleteAccessRole` sans `lock_version` ni 412 | WF-IHM-0110 |
| A-03 | A | `paths/access.yaml:39` | `listUsers` emprunte `IncludeInactive`, dont la description promet un 403 que l'opération ne déclare pas | WF-ADM-0060, WF-REF-0150 |
| A-04 | A | `components/schemas/access.yaml:80-103` | Le lien de fixation et le renvoi de l'invitation refusent par des conditions qu'aucune commande du compte ne dit d'avance | WF-IHM-0090, WF-ADM-0140 |
| B-01 | B | `components/schemas/audit.yaml:294-299` | `AuditUserField` ne sait pas nommer le rattachement à un nœud d'organisation | WF-SEC-0030, WF-ADM-0050, WF-ADM-0030 |
| B-02 | B | `paths/platform.yaml:328-383` | La planification des sauvegardes s'écrit sans refus pendant une restauration | WF-ADM-0160, WF-ADM-0170, WF-EXP-0040 |
| C-01 | C | `paths/reference.yaml:224` | Qui lit les objets actifs du référentiel : trois 404 sans permission nommée, trois 404 inatteignables, trois permissions de consultation qui n'ouvrent rien | WF-ADM-0100, WF-ADM-0110 |
| D-01 | D | `components/parameters.yaml:789-803` (`PortfolioStates`) | `PortfolioStates` dit qu'un projet créé, perdu ou abandonné nommé dans `states` est « sans effet », et `listProjects` s'en sert pour l'accueil qui les liste | WF-IHM-0120, WF-PRJ-0060, WF-PTF-0010 |
| E-01 | E | `components/schemas/revisions.yaml:2367-2397` | Une ligne qui change de nature ou de sous-projet : l'écart par clé n'est pas défini | WF-REV-0080 |
| E-02 (aussi J-17) | E | `components/schemas/revisions.yaml:2409-2419` | Le réestimé « après une fusion » a perdu « de même année de référence », et contredit le témoin | WF-REV-0080, WF-REV-0060 |
| E-03 | E | `paths/revisions.yaml:381-393` | `applyRateUpdate` : `lock_version` facultatif, liste sans borne, corps anonyme | WF-IHM-0110 |
| E-04 | E | `paths/revisions.yaml:58-60` | Le différentiel fusionné n'est pas repris par la révision suivante, et le contrat ne le dit pas | WF-REV-0100, WF-REV-0010, WF-DAT-0010 |
| E-05 | E | `components/schemas/revisions.yaml:274-279` | « Conserve les taux de la révision source » : il manque « projetés » | WF-REV-0060, WF-REV-0010, WF-DEV-0030 |
| F-01 | F | `components/schemas/revisions.yaml:658-680` | Les lignes d'une tâche terminée restent saisissables au contrat | WF-DEV-0050, WF-RAE-0030, WF-RAE-0040 |
| F-02 | F | `fixtures/api/node_deleted_provision_moved.json:9` | Une suppression du témoin termine une récapitulative et la date dans le passé | WF-RAE-0030, WF-PLA-0130, WF-PLA-0020, WF-PLA-0070 |
| F-03 | F | `components/schemas/revisions.yaml:1822-1825` | La création d'une tâche datée exige les heures que le front ne connaît pas | WF-PLA-0010, WF-ARC-0020, WF-PLA-0020 |
| F-04 | F | `paths/revisions.yaml:1117-1145` | Une sous-tâche créée ou déplacée sous un jalon n'a aucun refus | WF-PLA-0050 |
| F-05 | F | `components/schemas/revisions.yaml:1342-1523` | Les lignes propres ouvertes d'une récapitulative n'ont aucun attribut | WF-PLA-0040, WF-IHM-0070, WF-ARC-0020 |
| G-01 | G | `paths/analysis.yaml:448-450` (`getIndexHistory`) | `getIndexHistory` : un point « jamais omis » pour une révision marquée avant l'état En cours | WF-IND-0130, WF-DAT-0040, WF-IND-0090 |
| G-02 | G | `paths/analysis.yaml:279-306` | `getIndexHistory` et `getMilestoneTracking` sans 409 pour un projet antérieur à l'état En cours | WF-IND-0010 |
| G-03 | G | `components/schemas/portfolio.yaml:42` | Des champs toujours rendus restent facultatifs : le résidu de G-02 | WF-PTF-0040, WF-RAE-0020, WF-PTF-0010 |
| H-01 | H | `paths/risks.yaml:13-39` | Le registre ne se filtre pas sur ses colonnes de nombres ni sur la date du dernier réexamen | WF-IHM-0130, WF-IHM-0060, WF-RIS-0040, WF-RIS-0020 |
| H-02 | H | `paths/risks.yaml:186-206` | La modification d'un risque est une saisie de la révision en cours, quand la spécification en fait une donnée du projet | WF-RIS-0020, WF-IHM-0110, WF-RIS-0030 |
| H-03 | H | `fixtures/api/nodes_risk_occurred.json:2` | La structure obtenue par la survenance du témoin enveloppe les tâches fusionnées sous une tâche que la règle ne prévoit pas | WF-RIS-0060 |
| I-01 | I | `paths/exchanges.yaml:459-479` (`applyImport`, 409) | L'application refusée : ni condition pour un compte rendu expiré ou déjà appliqué, ni état pour l'import refusé dont le fichier est supprimé | WF-ARC-0100 |
| I-02 | I | `paths/exchanges.yaml:402-422` | L'abandon d'un import appliqué ou en cours d'application est laissé sans forme par le contrat lui-même | WF-ARC-0100, WF-INTF-0080 |
| I-03 | I | `paths/exchanges.yaml:298-300` | « Fichier déjà consommé » : un 409 sans code ni condition, qu'une autre phrase dit 404 | WF-DAT-0120 |
| I-04 | I | `paths/exchanges.yaml:298-317` | `openImport` ne déclare pas les conditions que ses commandes annoncent : `no_background_task_running` et `may_create_revision` | WF-INTF-0090, WF-IHM-0090 |
| I-05 | I | `components/schemas/exchanges.yaml:487-542` | La ligne nouvelle sous une tâche terminée n'a aucun motif de rejet au compte rendu | WF-INTF-0100, WF-INTF-0080, WF-INTF-0120, WF-RAE-0050 |
| J-01 | J | `paths/revisions.yaml:88-107` | Deux refus que la commande dit d'avance, refusés par un code propre | WF-IHM-0090, WF-REV-0010, WF-REV-0040 |
| J-02 | J | `components/schemas/projects.yaml:544-558` | `max_length` promis par deux descriptions, porté par aucune fixture | WF-PRJ-0010, WF-PRJ-0050, WF-ARC-0110 |

### Mineurs (89)

| # | Famille | Emplacement | Constat | Exigence |
|---|---|---|---|---|
| A-05 | A | `components/schemas/access.yaml:510-523` | Trois champs facultatifs que toute fixture porte | WF-ADM-0130, WF-CMP-0020, WF-ADM-0100 |
| A-06 | A | `components/schemas/platform.yaml:88-93` | `OperatingParameters.avatar_max_bytes` sans la borne d'`Installation.avatar_max_bytes` | §4.4.1 l. 3863 — « La taille d'un avatar est bornée par un p |
| A-07 | A | `paths/system.yaml:1-35` (`'503': ServiceUnavailable`). | `getLiveness` déclare un 503 que sa description rend impossible | WF-ADM-0160, WF-EXP-0040 |
| A-08 | A | `paths/access.yaml:229-236` | Refus et variantes déclarés sans exemple | WF-OBS-0030, WF-EXP-0040 |
| A-09 | A | `fixtures/api/users.json:2` | Résumés de fixtures qui ne disent pas ce que la valeur suppose | WF-ADM-0060, WF-ADM-0100 |
| A-10 | A | `fixtures/api/me.json:32` | Le compteur du compte et les écritures de `me` | WF-IHM-0110, WF-ADM-0040, WF-ADM-0080 |
| A-11 | A | `paths/access.yaml:741-858` | Permissions que les opérations ne nomment pas, et le 404 de l'avatar | WF-ADM-0100, WF-ADM-0110, WF-ADM-0080 |
| A-12 | A | `paths/system.yaml:166-171` (`finished_since`), `:149-157` | `finished_since` sans défaut dit ; `BackgroundTaskRef.kind` à moitié décrit | WF-ARC-0090, WF-IHM-0080 |
| A-13 | A | `components/schemas/access.yaml:212-223` | Schémas d'écriture sans description | WF-ADM-0050, WF-ADM-0030 |
| B-03 | B | `fixtures/api/audit_events.json` | Le journal du témoin n'inscrit pas les premiers rôles des comptes, ni celui de l'installation | WF-SEC-0030, WF-EXP-0020, WF-ADM-0070 |
| B-04 | B | `paths/audit.yaml:126-141` | Ni inscription `restore`, ni projet disparu, ni quatre actions dans les exemples | WF-ADM-0160, WF-ADM-0190, WF-SEC-0030 |
| B-05 (aussi V-04) | B | `fixtures/api/task_restore_queued.json` | La chronologie du 3 juin à 14 h 04 se contredit toujours, et `backups_unverified` réécrit la nuit sans le dire | WF-ADM-0150, WF-ADM-0160 |
| B-06 | B | `paths/platform.yaml:195-236` | `retainBackup` écrit sans compteur, et l'exception n'est écrite nulle part | WF-IHM-0110 |
| B-07 | B | `paths/platform.yaml:358-371` (422 de `setBackupSchedule`) | Le 422 de `setBackupSchedule` se lit exhaustif et ne l'est pas | WF-ADM-0170 |
| B-08 | B | `paths/audit.yaml:12-15` | Le journal « hors du périmètre » de la restauration, quand la spécification le dit « relu et réinscrit » | WF-ADM-0160, WF-SEC-0030 |
| C-02 | C | `fixtures/api/reference_settings.json:8-13` | L'amorçage du témoin : des paramètres non livrés sous un audit de la seule plateforme, et des objets de l'installation créés par un compte | WF-EXP-0020, WF-REF-0030, WF-DAT-0070 |
| C-03 | C | `fixtures/api/reference_settings.json:2` | Trois résumés disent encore « du budget de référence » (suite de C-04) | WF-REF-0160 |
| C-04 | C | `components/common.yaml:730-828` | `params.cost_categories` n'est pas typé dans `ProblemParams` | WF-ARC-0110, WF-REF-0030 |
| C-05 | C | `paths/reference.yaml:546` | Cinq refus déclarés sans exemple ni description propre | WF-REF-0150, WF-ADM-0100, WF-IHM-0110 |
| C-06 | C | `components/schemas/reference.yaml:166-220` | Ce qu'une image figée conserve de `is_active`, `audit` et `lock_version` n'est dit que dans DECISIONS | WF-REF-0130, WF-REV-0030 |
| C-07 | C | `paths/reference.yaml:1872-1887` | `setHourlyRate` : l'année du chemin hors de 2000–2100 n'a pas de refus dit | WF-REF-0050, WF-REF-0060, WF-ARC-0110 |
| C-08 | C | `paths/reference.yaml:291-313` | `updateOrgNode` : un déplacement change la profondeur et le parent des descendants, que la réponse ne porte pas | WF-REF-0070 |
| C-09 | C | `paths/reference.yaml:1711-1715` | Les années de la grille « quels que soient les filtres », sauf `is_active` faux | WF-REF-0050, WF-REF-0060, WF-IHM-0130 |
| D-02 | D | `paths/projects.yaml:227-242` | Le refus `project_not_terminal` est déclaré sans exemple sur six écritures du projet ; d'autres refus déclarés n'en ont pas non plus | WF-CYC-0100 |
| D-03 | D | `fixtures/api/project_creation_refused.json:12-14` | `project_creation_refused` rend `/code` trop long sans `params.max_length`, que `ProjectCode` promet | WF-PRJ-0010 |
| D-04 | D | `components/schemas/projects.yaml:129-131` | La description de `project_in_progress` omet `import_actual_costs` et `exclude_cost_lines`, que cinq fixtures et `costs.yaml` lui font nommer | WF-PRJ-0010 |
| D-05 | D | `components/schemas/projects.yaml:690-697` | Un sort de révision envoyé à un projet sans révision en cours : ignoré ou refusé ? | WF-CYC-0090 |
| D-06 | D | `components/schemas/projects.yaml:600-601` | `code: null` sur un projet En cours : le contrat ne dit toujours pas s'il efface le code | WF-PRJ-0010, WF-CRE-0020, WF-DAT-0060 |
| D-07 | D | `paths/projects.yaml:336-345` | La sortie différée par un marquage : le compteur du projet n'est pas dit pendant ni après | WF-IHM-0110, WF-CYC-0090 |
| D-08 | D | `paths/projects.yaml:77` | `listProjects` déclare un 404 sur une collection sans objet à ne pas trouver | WF-ADM-0110 |
| D-09 | D | `components/schemas/projects.yaml:1068-1084` | Un compte inscrit deux fois dans une liste de contributeurs : aucun refus dit | WF-PRJ-0060 |
| D-10 | D | `paths/projects.yaml:710-718` | `updateSubproject` dit recoder « à tout moment, coûts réels imputés ou non » sans dire le sort des lignes imputées par l'ancien code | WF-CRE-0020, WF-INTF-0140, WF-DAT-0060 |
| D-11 | D | `components/schemas/projects.yaml:12-21` | Les champs toujours rendus de `Project` ne sont pas exigés par le schéma de lecture | WF-PRJ-0080, WF-CYC-0090 |
| E-06 | E | `components/schemas/revisions.yaml:318-350` | `RateUpdateProposal` : `target_year` facultatif, trois champs sans description, proposition après acceptation et sur une révision marquée | WF-REV-0060 |
| E-07 | E | `paths/revisions.yaml:428-430` | `compareRevisions` : la révision en cours, la révision d'un autre projet, deux paramètres sans description | WF-REV-0080 |
| E-08 | E | `fixtures/api/merge_revision_marked_refused.json:2` | `merge_revision_marked_refused.json` : le résumé nomme toujours `revision_marked` | WF-REV-0050, WF-DAT-0020 |
| E-09 (aussi V-03) | E | `components/common.yaml:92-103` | Le compteur : valeur initiale non dite, offre marquée à 1, ce qui fait avancer `Revision.lock_version` | WF-IHM-0110 |
| E-10 | E | `components/schemas/revisions.yaml:15-28` | `version_name`, `description`, `marked_at` toujours rendus mais non exigés | WF-REV-0090 |
| E-11 | E | `paths/revisions.yaml:703` | `updateCostStructure` : refus par réponses partagées sans exemple, un seul 200 | WF-PLA-0020, WF-PLA-0150, WF-IHM-0110 |
| E-12 | E | `paths/revisions.yaml:294-304` | Le 400 `CONFIRMATION_REQUIRED` de la désignation n'a pas d'exemple | WF-REV-0040, WF-ARC-0110 |
| E-13 | E | `paths/revisions.yaml:242-257` | Le marquage pendant une restauration : `no_restore_running` manque à `mark` et au 409 | WF-ADM-0160, WF-IHM-0090 |
| E-14 | E | `fixtures/api/revision_importing.json` | `revision_importing.json` : le résumé dit « ne manque que de son marquage », la valeur en nomme deux | WF-REV-0040, WF-IHM-0090 |
| E-15 | E | `paths/revisions.yaml:846-852` | Fusionner une structure qui n'est pas un différentiel non fusionné : la condition nommée est celle de la révision | WF-REV-0050, WF-REV-0100, WF-IHM-0090 |
| E-16 | E | `paths/revisions.yaml:148-162` | L'abandon sans révision marquée et l'ouverture qui passe le projet en Chiffrage ne sont pas dits | WF-REV-0010, WF-CYC-0020 |
| E-17 | E | `paths/revisions.yaml:2199-2233` | Annulation : le traitement de fond qui court, la permission, ne sont pas dits | WF-IHM-0110, WF-IHM-0090 |
| E-18 | E | `components/schemas/revisions.yaml:94-101` | Deux variantes sans exemple : la révision d'un projet terminal, l'ordre de l'historique | WF-CYC-0100, WF-CYC-0110, WF-IHM-0060 |
| F-06 | F | `components/common.yaml:18-22` | L'arrondi au centime des montants inflation comprise n'est pas dit, et les fixtures arrondissent au pair | WF-DAT-0100, WF-DEV-0030, WF-DEV-0050 |
| F-07 | F | `components/schemas/revisions.yaml:1663-1665` | L'année de consommation d'une ligne d'une tâche à cheval sur deux années | WF-DEV-0040 |
| F-08 | F | `components/schemas/revisions.yaml:1399-1404` | La date de terminaison d'une récapitulative n'est pas décrite | WF-PLA-0130 |
| F-09 | F | `components/schemas/revisions.yaml:2074-2075` | `RemainingUpdate` : un `reason` sans règle, des grandeurs sans règle de champ absent, un 422 incomplet | WF-RAE-0040, WF-DEV-0010, WF-DEV-0020 |
| F-10 | F | `paths/revisions.yaml:1489` | Trois 409 génériques, un 409 sans exemple | WF-IHM-0090 |
| F-11 | F | `components/parameters.yaml:154-157` | Paramètres et défauts muets | WF-DEV-0020, WF-IHM-0130 |
| F-12 | F | `fixtures/api/nodes_amendment.json:9` | Deux fixtures qui disent moins juste que le contrat | WF-REV-0100, WF-PLA-0170 |
| G-04 (aussi V-05) | G | `components/schemas/indicators.yaml:231-237` | Deux `delta_to_reference` de signes opposés, pour une grandeur que la spécification 1.0.1 nomme « marge » | WF-RAE-0020, WF-IND-0050, WF-PTF-0040 |
| G-05 | G | `fixtures/api/workload_marked_remaining.json:5` | Le plan de charge d'une révision marquée, calculé à son marquage, est dit non conservé | WF-DAT-0040, WF-DEV-0070 |
| G-06 | G | `paths/portfolio.yaml:144-152` | Le 422 du plan de charge agrégé n'a aucun exemple | WF-PTF-0060 |
| G-07 | G | `paths/analysis.yaml:19-21` | `revision_id` sans description sur trois opérations, et le reste à engager d'une révision marquée | WF-DAT-0040, WF-DEV-0060, WF-RAE-0020 |
| G-08 | G | `paths/analysis.yaml:233-236` | Des variantes sans exemple : la maille d'un sous-projet sur les indicateurs et le devis, une révision marquée sur une courbe | WF-IND-0020, WF-DEV-0060, WF-DAT-0040 |
| G-09 | G | `components/parameters.yaml:753-762` (`AsOf`) | `as_of` avant toute révision marquée En cours, ou dans l'avenir : refus non dits | WF-IND-0010, WF-DAT-0040 |
| G-10 | G | `fixtures/api/portfolio_workload.json:2` | Deux fixtures du portefeuille ignorent le monteur câbleur que le témoin emploie depuis EP-02/L27 | WF-PTF-0080, WF-PTF-0060 |
| G-11 | G | `components/schemas/indicators.yaml:249-277` | Trois zones que le serveur classe sans que le contrat dise la règle | WF-RAE-0020, WF-PTF-0110, WF-IHM-0070 |
| G-12 | G | `components/schemas/indicators.yaml:463-481` | Deux descriptions ambiguës : les rôles du plan d'un projet, et le filtre `zones` qui « place d'abord » | WF-DEV-0070, WF-PTF-0040 |
| H-04 | H | `paths/risks.yaml:104-124` | `may_create_revision` manque aux 409 des quatre saisies des risques | WF-RIS-0020, WF-IHM-0090 |
| H-05 | H | `paths/risks.yaml:456-458` | Le 409 du compte rendu préalable ne nomme que `risk_identified` | WF-RIS-0060, WF-IHM-0090 |
| H-06 | H | `paths/risks.yaml:322-334` (`listRiskReviews`) | L'historique ne dit pas que la déclaration et la survenance en sont des entrées, et `actor` n'est pas exigé | WF-RIS-0010, WF-RIS-0040 |
| H-07 | H | `paths/risks.yaml:131-157` | Refus déclarés et variantes sans exemple | WF-RIS-0010, WF-RIS-0060 |
| H-08 (aussi J-13) | H | `fixtures/api/risk_matrix_no_basis.json` | `risk_matrix_no_basis.json` est toujours orpheline | WF-REF-0160, WF-RIS-0040 |
| H-09 | H | `components/schemas/risks.yaml:262-298` | Descriptions à aligner : `RiskWrite` parle de la modification, `RiskRevision` oublie l'écarté | WF-RIS-0040 |
| I-06 | I | `components/schemas/exchanges.yaml:155-218` | `Import.report` et `Import.task` sont facultatifs sans que le contrat dise où ils manquent ; trois comptes rendus n'ont pas de `task` | WF-INTF-0080, WF-IHM-0080 |
| I-07 | I | `paths/exchanges.yaml:475-479` | Exemples manquants : les 409 d'`applyImport` hors `import_file_accepted`, `project_in_progress` de l'exclusion, la période inversée et le projet terminal d'`openImport` | WF-ARC-0100, WF-CRE-0030, WF-CRE-0050, WF-CYC-0100 |
| I-08 | I | `components/schemas/exchanges.yaml:20` | `FileUpload.expires_at` ne dit pas sa valeur | WF-DAT-0120, WF-ARC-0100 |
| I-09 | I | `components/schemas/exchanges.yaml:730-732` | `ExportRequest.depth` : ni défaut, ni portée, ni borne haute | WF-PLA-0120 |
| J-03 | J | `components/responses.yaml:65-72` | Vingt-quatre opérations déclarent le 412 sans exemple | WF-IHM-0110, WF-QUA-0020 |
| J-04 | J | `paths/revisions.yaml:703` | Des 409 déclarés sans exemple, ou nommant un code sans son exemple | WF-DAT-0020, WF-CYC-0100, WF-QUA-0020 |
| J-05 | J | `paths/revisions.yaml:2079-2089` | `previewPaste` ne nomme pas `PASTE_TOO_WIDE` | WF-IHM-0050, WF-ARC-0110 |
| J-06 | J | `fixtures/api/task_import_analysis_failed.json` | Les `problem` des tâches de fond échouées sont sans `correlation_id` | WF-OBS-0020, WF-IHM-0080 |
| J-07 | J | `components/parameters.yaml:3-11` (`Limit`, `Offset`) | `Limit`, `Offset`, `Year`, `PaginationMeta` sans description (J-20 du 2026-10-28) | WF-IHM-0060 |
| J-08 | J | `components/common.yaml:155-366` | `Problem.params` : `risks` omis, `missing_rates` et `subordinate_node_ids` dits « ouverts » |  |
| J-09 | J | `components/schemas/revisions.yaml:467-469` | `StructureCreate.kind` : la seule énumération sans `type` (J-19) |  |
| J-10 | J | `components/common.yaml:713-722` | Le pointeur `/body` n'est pas une forme de `FieldProblem.pointer` (J-14) |  |
| J-11 | J | `paths/risks.yaml:322-348`. | `listRiskReviews` sans pages, sans tri, sans justification (J-12, part restante) | WF-IHM-0060 |
| J-12 | J | `components/schemas/projects.yaml:381` | `task_not_milestone` : la seule condition sans exemple (J-18, part restante) |  |
| J-14 | J | relevé sur les 255 `anyOf: [{…}, { type: 'null' }]` des `schemas/` et de `common.yaml` : 110 n' | Cent dix propriétés nullables sans règle de nullité dite | WF-ARC-0060 |
| J-15 | J | `README-fr.md:18-30` | Le README ne tient pas toutes les conventions que le contrat applique, et son plan oublie des fichiers |  |
| J-16 | J | `tools/inventory.py:64-66` | `inventory.py` : deux entrées mortes ; WF-EXP-0030 a une surface que personne ne cite | WF-EXP-0030 |
| V-01 (aussi H-10, I-10) | V | `fixtures/examples.json` (92 exemples) | Aucune fixture ne cite un exemple numérique du Vérif : `make check-fixtures` passe à vide | WF-QUA-0020 |
| V-02 | V | `fixtures/api/project_indicators_offer.json:4-6` | `project_indicators_offer.json` : un 409 `STATE_FORBIDS_OPERATION` sans aucun paramètre | WF-IHM-0090, WF-ARC-0110 |
| V-06 | V | `fixtures/api/dependencies_entered.json:9` | Une corrélation hors du schéma d'identifiants du témoin | — (convention du témoin) |
| V-07 | V | `fixtures/api/volume/*.json` (20 fichiers) | Les volumes du §4.6.2 ne sont tenus que pour une partie des grandeurs | §4.6.2 — 300 projets, 1 000 tâches et 5 000 lignes, 30 risqu |

## Annexes — le détail par relecture

Les scripts de relevé (annexes J et V) ont été écrits hors du dépôt, dans le dossier de travail de la
revue (`revue/`) ; leurs résultats sont dans les sections « Relevé » des annexes.

## Annexe A — Système, compte courant, comptes et habilitations

Périmètre. Lu ligne à ligne : `docs/api/README-fr.md` (94 l., « Conventions » en entier) ; `docs/api/paths/system.yaml`
(299 l., 8 opérations), `paths/me.yaml` (205 l., 5), `paths/access.yaml` (976 l., 20) ; `components/schemas/access.yaml`
(562 l.) ; `components/schemas/platform.yaml` l. 1–200 (`SystemStatus`, `OperatingParameters`, `ComponentHealth`,
`PlatformComponent`, `StorageUsage`, `OperationOutcome`, `Alert`), l. 307–357 (`BackupSchedule`, pour la symétrie),
l. 528–678 (`IdentitySyncSchedule`, `IdentitySyncReport`, `IdentitySyncSkipped`) ; `components/schemas/reference.yaml`
l. 744–774 (`Installation`) ; `components/common.yaml` l. 82–140 (`Language`, `LockVersion`, `Audit`, `ActorRef`),
l. 141–200 (`Problem`), l. 394–708 (`ErrorCode`, les codes de la famille et leurs commentaires), l. 730–745
(`ProblemParams`), l. 905–991 (`SortOrder`, `PaginationMeta`, `BackgroundTaskStatus`, `BackgroundTaskRef`) ;
`components/responses.yaml` (138 l., en entier) ; `components/parameters.yaml` (les paramètres que la famille
référence : `Limit`, `Offset`, `Search`, `SortOrder`, `IncludeInactive`, `IsActive`, `UserId`, `AccessRoleId`, `TaskId`,
les huit paramètres d'audit) ; `components/schemas/projects.yaml` l. 106–425 (`CommandCondition`) ;
`components/schemas/audit.yaml` (`AuditAction`, pour les actions des comptes) ; `openapi.yaml` (étiquettes).
Fixtures ouvertes : **118** — les 31 de `system.yaml`, les 28 de `me.yaml`, les 59 d'`access.yaml`, toutes, plus
`permissions.json` croisé par programme avec `PermissionCode` et avec les `permissions` des douze `me*.json`
(unions recalculées depuis `access_roles.json`) ; tri des listes vérifié par programme.
Spécification 1.0.1 : §3.1.3 (WF-INTF-0010 à 0030, l. 377–417), §3.1.5 (WF-INTF-0160 à 0180, l. 555–597), §3.4.2 en
entier (l. 1182–1440 : WF-ADM-0050, 0060, 0070, 0140, 0180, 0030, 0040, 0080, 0010, 0020, 0090, 0100, 0110, 0120, 0130,
0150 à 0170 pour ce que `SystemStatus` en porte, 0190), §3.4.3 WF-PTF-0030 (l. 1474), §3.6 (l. 3174–3352), §4.2.2
WF-ARC-0030/0040 (l. 3608–3632), §4.3.4 WF-ARC-0090 (l. 3825), §4.4.1 (table et audit, l. 3849–3946, WF-DAT-0070),
§4.4.4 WF-DAT-0120, §4.4.5 WF-DAT-0130 (l. 4072–4104), §4.5 (l. 4120–4215 : §4.5.1, WF-EXP-0010 à 0040),
§4.6.1 (WF-SEC-0010 à 0030, l. 4217–4258), §4.6.3 (WF-OBS-0010 à 0030, l. 4329–4367), §4.6.4–4.6.5 (WF-EXP-0050/0060,
WF-CMP-0020/0030). Décisions : `DECISIONS.md` l. 9445–9550 (US-0701/L8), 9649–9776 (US-0702/L1), 9777–9868
(US-0702/L2), 9869–9910 (US-0702/L3), et par `grep` : l. 158–168, 3188–3223, 3962–3978, 4015–4032, 5727, 6150–6162,
6183–6195, 879. Revue précédente : annexe A (l. 432–771), K-01, K-02, K-09, K-10 (l. 3105–3214), tableau K
(l. 3083–3100). `INVENTORY.md` (lignes de la famille et « Exigences que le contrat ne cite pas »).

### Synthèse

La famille a été reprise en profondeur depuis le 28 octobre : les quatre majeurs de l'annexe A (Manager du témoin,
périodicité de la lecture des comptes, paramètres d'exploitation, renvoi de l'invitation) et les sept mineurs sont
réglés, à la lettre de la décision US-0701/L8, et les cinq opérations nouvelles (`/identity-syncs`,
`/identity-syncs/latest`, `/identity-sync-schedule` GET/PUT, `/users/{id}/invitation`) sont conformes à WF-ADM-0070,
WF-ADM-0140 et WF-EXP-0040, avec des fixtures cohérentes entre elles (livrée à `01:30`, achevée à 2 h, `last_identity_sync`
à 2 h). `SystemStatus` porte maintenant tout ce que WF-ADM-0130 énumère ; le catalogue des permissions (51) est
égal à `PermissionCode`, toute permission nommée par une opération du contrat entier y existe, et les trois rôles
prédéfinis du témoin couvrent WF-INTF-0010/0020/0030. Les douze `me*.json` portent exactement l'union des permissions
de leurs rôles, dans l'ordre du catalogue ; les tris des listes sont ceux que les descriptions annoncent.

Ce qui reste tient à quatre points où un implémenteur se tromperait : `createUser` attribue des rôles sans la
permission qu'exige `setUserAccessRoles` pour le même geste (A-01) ; `deleteAccessRole` est une suppression sans
corps sans `lock_version` ni 412, contre la convention du README (A-02) ; `listUsers` emprunte un paramètre partagé
dont la description promet un 403 que l'opération ne déclare pas (A-03) ; le lien de fixation et le renvoi de
l'invitation refusent par des `CommandCondition` qu'aucune commande du compte ne dit d'avance (A-04). Le reste est
de la clarté : champs facultatifs que toute fixture porte, exemples manquants, résumés de fixtures imprécis, un 503
impossible sur la sonde de vivacité, le compteur du compte que les écritures de `me` font avancer ou non selon la
fixture.

**13 constats : 0 bloquant, 4 majeurs, 9 mineurs. Suivi : 15 réglés (A-01 à A-11, K-01, K-02, K-09, K-10),
0 partiel, 0 non réglé, 0 sans objet.**

### Constats

#### A-01 — `createUser` attribue des rôles sans la permission de modifier les rôles
- **gravité** : majeur
- **emplacement** : `docs/api/paths/access.yaml:157-217` (`createUser`, `'403'` partagé sans permission nommée),
  `docs/api/components/schemas/access.yaml:212-223` (`UserCreate.access_role_ids`, sans description) ; à comparer à
  `docs/api/paths/access.yaml:422-427` (`setUserAccessRoles`) et `components/schemas/access.yaml:92-95`
  (`UserCommand`).
- **spécification** : `WF-ADM-0090-A` — « Un utilisateur habilité peut créer, modifier, renommer et supprimer des
  rôles, et attribuer ou retirer des rôles aux comptes. » ; `WF-ADM-0120-A` — « Au moins un compte actif porte
  toujours les permissions de modifier la gestion des utilisateurs et celle des rôles d'habilitation ».
- **le contrat dit** : `setUserAccessRoles` « exige, outre la permission de modifier les comptes (`users.write`),
  celle de modifier les rôles d'habilitation (`access_roles.write`) ; sans elle, 403 `PERMISSION_MISSING` — qui ne
  porte que `users.write` ne se donne pas le rôle administrateur » (l. 423–427). `createUser` reçoit
  `access_role_ids` et ne dit rien de plus que son 403 partagé : un porteur de `users.write` seul crée un compte
  porteur du rôle « Administrateur », ce que la phrase de `setUserAccessRoles` veut empêcher.
- **la fixture dit** : `user_created.json` et `user_created_invited.json` créent sans rôle ; aucune ne montre une
  création avec rôle ni son refus.
- **décision** : `DECISIONS.md:6157` « une création avec premier rôle qu'aucun exemple de `createUser` ne répond —
  … le compte de `user_created` reçoit « Chiffreur » de la requête qui le crée » assume le champ ; `:3188-3200`
  et `:423-427` du contrat décident la permission de l'attribution — aucune décision sur `createUser`.
- **proposition** : dire dans `createUser` et `UserCreate.access_role_ids` qu'une liste non vide exige aussi
  `access_roles.write`, le 403 `PERMISSION_MISSING` nommant `access_roles.write` dans `params.missing_permission`,
  avec un exemple (`user_create_roles_forbidden`) ; ou retirer `access_role_ids` du corps et laisser l'attribution à
  `setUserAccessRoles`. À trancher — la première forme garde le contrat.

#### A-02 — `deleteAccessRole` sans `lock_version` ni 412
- **gravité** : majeur
- **emplacement** : `docs/api/paths/access.yaml:949-976` (`deleteAccessRole` : paramètres `AccessRoleId` seul,
  réponses 204/401/403/404/409/500/503) ; `components/schemas/access.yaml:527,541` (`AccessRole.lock_version`
  exigé).
- **spécification** : `WF-IHM-0110-A` (compteur des écritures concurrentes) par la convention du README.
- **le contrat dit** : `README-fr.md:49` — « `lock_version` sur les écritures concurrentes, refus par 412
  `STALE_LOCK_VERSION` … ; une suppression sans corps le passe en paramètre (`lock_version`) » ; la seule exception
  écrite est `setActualCostTrackedScope`. `deleteRisk`, `deleteSubproject`, `abandonRevision`, `deleteNode` le
  portent (`risks.yaml:278-286`, `projects.yaml:792-800`, `revisions.yaml:166-174`, `:1320-1328`) ; `deleteAccessRole`
  non, alors que le rôle porte un compteur que `updateAccessRole` exige.
- **la fixture dit** : `access_role_delete_refused.json` ne porte que l'`ACCESS_ROLE_IN_USE` ; rien sur le compteur.
- **décision** : `DECISIONS.md:9784-9797` (US-0702/L2) nomme les cinq écritures corrigées — `deleteAccessRole` n'y est
  pas ; `:4022-4024` (« La suppression d'un rôle est logique ») ne parle pas du compteur. Aucune décision ne
  l'exempte.
- **proposition** : paramètre `lock_version` exigé (`LockVersion`, « le compteur du rôle supprimé, tel que la table
  l'a lu »), `'412': PreconditionFailed`, `'422': LockVersionInvalid`, comme `deleteRisk` ; un paramètre exigé ajouté
  après le gel serait un changement incompatible. Aussi : `deleteTimeline` (`projects.yaml:1105-1150`) est dans le
  même cas — hors de cette annexe, à porter au consolidateur (annexe D).

#### A-03 — `listUsers` emprunte `IncludeInactive`, dont la description promet un 403 que l'opération ne déclare pas
- **gravité** : majeur
- **emplacement** : `docs/api/paths/access.yaml:39` (`$ref: IncludeInactive`), `:40-47` (`is_active`, local),
  `:117-156` (réponses : 401, 404, 422, aucun 403) ; `docs/api/components/parameters.yaml:38-45` (`IncludeInactive`).
- **spécification** : `WF-ADM-0060-A` — « Un compte désactivé … reste affiché partout où il a agi » ; Vérif :
  « Une révision marquée par un compte depuis désactivé affiche toujours son auteur » ; `WF-REF-0150-A` ne vaut que
  pour le référentiel.
- **le contrat dit** : `IncludeInactive` — « Inclut les objets désactivés (WF-REF-0150), sous la permission de
  modification que l'opération exige : sans elle, la demande est refusée par 403 (`PERMISSION_MISSING`), comme pour
  `is_active` faux » ; `listUsers` — « les comptes désactivés s'ajoutant aux actifs par `include_inactive` »,
  « Comptes, les désactivés restant lisibles (WF-ADM-0060) » (l. 119), sans 403. Un implémenteur du service qui suit
  le paramètre refuse `include_inactive` à qui n'a que `users.read` ; un implémenteur du front qui suit l'opération
  ne s'y attend pas.
- **la fixture dit** : `users_inactive.json`, `users_by_access_role.json`, `users_search.json`,
  `users_created_by_platform.json`, `users_by_created_at.json` lisent les désactivés « (include_inactive=true) » sans
  parler de permission ; aucune fixture de 403.
- **décision** : `DECISIONS.md:9857-9861` (US-0702/L2) déclare le 403 d'`include_inactive` sur `listOrgNodes`,
  `listCalendars`, `listCostTypes` seulement ; rien sur les comptes.
- **proposition** : un paramètre local `include_inactive` pour `listUsers` (« Inclut les comptes désactivés, lisibles
  sous la même permission que les actifs, `users.read` : un compte désactivé reste affiché partout, WF-ADM-0060 »),
  ou déclarer le 403 avec `users.write` et son exemple. À trancher ; la première lecture suit WF-ADM-0060.

#### A-04 — Le lien de fixation et le renvoi de l'invitation refusent par des conditions qu'aucune commande du compte ne dit d'avance
- **gravité** : majeur (à trancher)
- **emplacement** : `docs/api/components/schemas/access.yaml:80-103` (`UserCommand` : `deactivate`, `reactivate`,
  `anonymize`, `set_access_roles`), `:45-60` (`available_commands`, `maxItems: 3`) ; `docs/api/paths/access.yaml:505-519`
  (`createPasswordSetupLink` 409), `:548-559` (`resendInvitation` 409) ; `components/schemas/projects.yaml:259-263`
  (`is_local_account`, `is_active_account`).
- **spécification** : `WF-IHM-0090-A` — « Une commande qu'un état du projet, d'une révision ou d'une tâche rend
  momentanément impossible est présentée indisponible, avec la condition qui manque » ; `WF-ADM-0140-A` — « ce lien,
  qu'un utilisateur habilité peut renvoyer. Un utilisateur habilité peut aussi obtenir ce lien depuis Waterfall ».
- **le contrat dit** : `README-fr.md:48` — le 409 nomme « la condition qui manque, celle que l'objet dit d'avance de
  sa commande (`available_commands`) » ; `UserCommand` — « Le front ne rapproche pas les rôles des comptes … : le
  compte le dit ». Les deux opérations refusent un compte désactivé par `is_active_account` — un état momentané, la
  réactivation existant — sans qu'aucune commande du compte ne la liste ; la grille des comptes a pourtant une colonne
  `password_link` (`me_grid_settings.json:94`, `preferences_page_size.json`) que le front doit rendre indisponible en
  déduisant lui-même de `origin` et `is_active`.
- **décision** : `DECISIONS.md:3193-3200` (« Un compte porte ses commandes … `UserCommand` vaut `deactivate`,
  `reactivate` … et `set_access_roles` ») date d'avant l'opération du lien ; `:9464-9471` (US-0701/L8) ajoute
  `resendInvitation` sans toucher `UserCommand`. Aucune décision n'écarte une commande du lien.
- **proposition** : deux valeurs d'`UserCommand`, `create_password_link` et `resend_invitation`, listées pour un compte
  local seulement (un compte de l'annuaire ne l'aura jamais : non listée, comme une sortie terminale), disponibles
  s'il est actif, indisponibles `is_active_account` sinon ; `maxItems: 5`. Ou une décision écrite qui dit que la
  nature et l'état du compte, portés par `origin` et `is_active`, tiennent lieu de commande — mais une valeur
  d'énumération ajoutée après le gel est un changement incompatible : à trancher maintenant.

#### A-05 — Trois champs facultatifs que toute fixture porte
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/access.yaml:510-523` (`Permission.required: [code, kind]`,
  `fbs_code` facultatif) ; `components/schemas/platform.yaml:142-149` (`OperationOutcome.required: [at, succeeded]`,
  `problem` facultatif), `:117-126` (`ComponentHealth.required: [component, is_available, checked_at]`, `version`
  facultatif).
- **spécification** : `WF-ADM-0130-A` — « la version de chaque composant employé (WF-CMP-0020) » ; `WF-ADM-0100-A`.
- **le contrat dit** : trois champs nullables mais omissibles ; `BackgroundTaskRef` et `UserAccount` ont été resserrés
  pour le même motif (A-08, A-09 du 28 octobre).
- **la fixture dit** : les 51 entrées de `permissions.json` portent `fbs_code` (nul pour les dix dernières) ; les
  quatre `system_status*.json` portent `problem` dans leurs seize `OperationOutcome` et `version` dans leurs
  vingt-huit `ComponentHealth` (nul pour `object_storage`), `readiness.json` de même.
- **décision** : `DECISIONS.md:9532-9535` applique A-08/A-09 ; rien sur ces trois.
- **proposition** : `fbs_code`, `problem`, `version` dans `required`, nullables comme aujourd'hui — compatible pour
  tout lecteur.

#### A-06 — `OperatingParameters.avatar_max_bytes` sans la borne d'`Installation.avatar_max_bytes`
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/platform.yaml:88-93` (`minimum: 1`, sans `maximum`) ;
  `components/schemas/reference.yaml:752-762` (`minimum: 1, maximum: 8388608`).
- **spécification** : §4.4.1 l. 3863 — « La taille d'un avatar est bornée par un paramètre d'exploitation, livré à
  512 Ko. »
- **le contrat dit** : « La même valeur que `Installation.avatar_max_bytes`, que le front lit sans session » — deux
  schémas pour une même valeur, l'un borné à 8 Mio (`DECISIONS.md:879`, #233), l'autre non.
- **décision** : `DECISIONS.md:879` fixe la borne ; `:9472-9486` ajoute le paramètre sans la reprendre.
- **proposition** : `maximum: 8388608` sur `OperatingParameters.avatar_max_bytes`, ou `allOf` vers un schéma commun.

#### A-07 — `getLiveness` déclare un 503 que sa description rend impossible
- **gravité** : mineur
- **emplacement** : `docs/api/paths/system.yaml:1-35` (`'503': ServiceUnavailable`).
- **spécification** : `WF-ADM-0160-A` (maintenance), `WF-EXP-0040-A`.
- **le contrat dit** : « Répond dès que le processus est démarré, sans toucher aucun composant de données » ; « Une
  plateforme en maintenance est vivante : la sonde répond 200 » ; `ServiceUnavailable` : « toute opération répond
  ainsi … sauf `getLiveness`, qui dit la maintenance ». Un 503 déclaré sur la seule opération qui promet de ne jamais
  le rendre : un orchestrateur qui lit le contrat le croirait possible.
- **décision** : `DECISIONS.md:6183-6191` — « La sonde reste à 200 en maintenance : la plateforme est vivante, et un
  orchestrateur qui la redémarrerait interromprait la restauration. » Tenue ; le 503 la contredit.
- **proposition** : retirer `'503'` de `getLiveness` (la règle `rule/protected-operation-declares-503` ne vise que les
  opérations gardées), ou dire quand il viendrait.

#### A-08 — Refus et variantes déclarés sans exemple
- **gravité** : mineur
- **emplacement** : `docs/api/paths/access.yaml:229-236` (`getUser` 200 : `deactivated`, `anonymized`, aucun compte
  actif) ; `:318-325` (`setUserActivation` 200 : `deactivated` seul, aucune réactivation) ; `:701-714`
  (`setIdentitySyncSchedule` 422 : « donné à une quotidienne, `/weekday` par le motif `VALIDATION_FAILED` » sans
  exemple) ; `:141-154` (`listUsers` 422 : `origins`/`access_role_ids` refusés, décrits l. 51–55 et 72–75, sans
  exemple) ; `:535-539,561` et `:364-365,407` (503 `identity_provider` de `resendInvitation` et `anonymizeUser`, décrits,
  sans exemple) ; `docs/api/paths/me.yaml:113-142` (`VALUE_TOO_LONG`, #874/#1235, sans exemple), `:191`
  (`putMyAvatar` 422 « ni un PNG ni un JPEG, pointeur `""` », réponse partagée sans exemple), `:160-161` et
  `system.yaml:46-48` (503 `database` avant l'amorçage, sans exemple) ; `docs/api/paths/system.yaml:191-200`
  (`listBackgroundTasks` 422 : `/query/finished_since` par `DATE_INVALID`, sans exemple) ;
  `components/schemas/platform.yaml:158-167` (`Alert.code` : `identity_sync_failed`, `task_queue_stalled`,
  `error_rate_abnormal` — aucune fixture du dépôt ne les porte, `grep` sur `fixtures/api` et `volume/`).
- **spécification** : `WF-OBS-0030-A` — « échec d'une lecture des comptes … file de tâches dont la plus ancienne
  attend plus longtemps qu'un seuil … taux d'erreur … au-delà d'un seuil » ; `WF-EXP-0040-A` — « refusée en nommant
  le composant indisponible ».
- **le contrat dit** : les refus sont décrits avec leur code et leurs paramètres ; aucun `COMPONENT_UNAVAILABLE` n'est
  servi en réponse directe par une fixture (le seul est dans le `problem` de `system_status_backup_failed.json`).
- **décision** : `DECISIONS.md:9677-9689` (J-03, J-11 : « chaque code est porté par un exemple ») — tenue au niveau du
  code ; les variantes de réponse et les alertes ne sont pas couvertes.
- **proposition** : engendrer (`wftools.mockrefusals`/`mockdeclared`) `user.json` (Lucas Petit actif),
  `user_reactivated.json`, `identity_sync_schedule_weekday_daily.json`, `users_origins_invalid.json`,
  `invitation_provider_unavailable.json` (503 `identity_provider`), `installation_not_bootstrapped.json` (503
  `database`), `preferences_too_many_grids.json`, `avatar_not_image.json`, `tasks_finished_since_invalid.json`, et
  trois variantes `system_status_*` pour les trois alertes manquantes.

#### A-09 — Résumés de fixtures qui ne disent pas ce que la valeur suppose
- **gravité** : mineur
- **emplacement** : `fixtures/api/users.json:2` (résumé), `:130-133` (Alix Moreau, `is_active: false`) et `:317`
  (`meta.total: 7`) ; `fixtures/api/users_page.json:2`, `:52` et `:104` (Alix Moreau en page 2, `total: 7`) ;
  `fixtures/api/access_roles.json:2` (« Pilotage de projet », « le catalogue hors administration ») et `:256-300`.
- **spécification** : `WF-ADM-0060-A` ; `WF-ADM-0100-A` (« consulter tous les projets », permission structurante).
- **le contrat dit** : `IncludeInactive.schema.default: false` (`parameters.yaml:45`) — la liste par défaut ne rend pas
  les désactivés ; `users.json` dit « désactivés compris » sans nommer `include_inactive=true`, que toutes les autres
  fixtures de la liste nomment : un lecteur croit que le défaut les rend. « Pilotage de projet » n'a ni les
  permissions d'administration ni `all_projects_read` ni `platform_restore` — « hors administration » ne dit que les
  premières, `all_projects_read` étant structurante.
- **décision** : aucune.
- **proposition** : « désactivés compris (`include_inactive=true`) » dans `users.json` et `users_page.json` ;
  « le catalogue hors administration, restauration et consultation de tous les projets » dans `access_roles.json`.

#### A-10 — Le compteur du compte et les écritures de `me`
- **gravité** : mineur
- **emplacement** : `fixtures/api/me.json:32` (`lock_version: 3`), `me_english.json:32` (3), `me_grid_settings.json:32`
  (3), `me_dark.json:32` (4), `me_with_avatar.json:32` (4) ; `docs/api/paths/me.yaml:76-144` (`updateMyPreferences`),
  `:146-205` (`putMyAvatar`, `deleteMyAvatar`) ; `components/schemas/access.yaml:190` (`UserAccount.lock_version`).
- **spécification** : `WF-IHM-0110-A` par la convention ; `WF-ADM-0040-A`, `WF-ADM-0080-A`.
- **le contrat dit** : rien sur l'effet d'une écriture de préférence ou d'avatar sur `UserAccount.lock_version`, que
  `updateUser`, `setUserActivation`, `anonymizeUser` et `setUserAccessRoles` exigent et que `LockVersion` dit « suit
  les écritures de l'utilisateur ».
- **la fixture dit** : « Le même compte, qui a choisi l'anglais » garde 3 ; « Le même compte, qui a choisi le mode
  sombre » passe à 4 ; l'avatar déposé passe à 4 ; l'`audit.updated_at` reste à 14 h 05 dans tous. Deux règles pour
  un même geste.
- **décision** : `DECISIONS.md:3962-3978` renomme les exemples sans dire la règle ; aucune autre.
- **proposition** : dire dans `LockVersion` ou `UserAccount.lock_version` si les préférences et l'avatar le font
  avancer (un administrateur qui modifie le compte pendant que son porteur change de thème reçoit-il 412 ?), et
  accorder les cinq fixtures. Proposition : non — les préférences et l'avatar sont au porteur seul (WF-ADM-0040),
  et ne concourent pas avec l'administration ; `me_dark` et `me_with_avatar` à 3.

#### A-11 — Permissions que les opérations ne nomment pas, et le 404 de l'avatar
- **gravité** : mineur
- **emplacement** : `docs/api/paths/access.yaml:741-858` (`listAccessRoles`), `:886-907` (`getAccessRole`), `:859-884`
  (`createAccessRole`), `:908-948` (`updateAccessRole`), `:949-976` (`deleteAccessRole`), `:718-739`
  (`listPermissions`), `:1-156` (`listUsers`), `:219-240` (`getUser`), `:241-297` (`updateUser`), `:299-348`
  (`setUserActivation`), `:563-583` (`getUserAvatar`).
- **spécification** : `WF-ADM-0100-A` — « deux niveaux — consulter, modifier » ; `WF-ADM-0110-A` — « L'interface
  présente le même écran pour un objet inexistant et pour un objet dont la consultation n'est pas permise » ;
  `WF-ADM-0080-A` — « Un compte sans avatar est affiché avec une image par défaut. »
- **le contrat dit** : `access_roles.read` n'est nommée par aucune opération du contrat (`grep` sur `paths/*.yaml` :
  `users.write` ×7, `users.read` ×2, `access_roles.write` ×1, `access_roles.read` ×0, `system_status.read` ×1) ; les
  cinq opérations des rôles et `listPermissions` déclarent 403/404 sans dire quelle permission les gouverne, ni si
  le catalogue se lit par toute session (il n'a pas de 404) ; `getUserAvatar` déclare un 404 sans dire qu'un compte
  sans avatar (`has_avatar` faux) en est un, ni sous quelle permission l'image d'un autre compte se lit (elle est
  « citée partout », colonnes d'audit comprises). Toute permission nommée existe dans `PermissionCode` et dans
  `permissions.json` ; c'est l'inverse qui manque.
- **décision** : `DECISIONS.md:158-168` — « Les autres fonctions — rôles, sauvegarde — n'ont pas de conditions à
  nommer : leurs commandes suivent la permission de modification de la fonction » ; `:2951` range `audit_log.read`.
  Rien n'écrit `access_roles.read` ni la lecture du catalogue.
- **proposition** : une phrase par opération (« Lisible sous `access_roles.read` ; 404 sans elle », « Sous
  `access_roles.write` »), « lisible par toute session » sur `listPermissions`, et sur `getUserAvatar` : « 404 pour un
  compte inconnu, invisible, ou sans avatar (`has_avatar` faux) ; lisible par toute session, l'avatar étant cité
  partout où le compte l'est ».

#### A-12 — `finished_since` sans défaut dit ; `BackgroundTaskRef.kind` à moitié décrit
- **gravité** : mineur
- **emplacement** : `docs/api/paths/system.yaml:166-171` (`finished_since`), `:149-157` ;
  `docs/api/components/common.yaml:939-961` (`kind`).
- **spécification** : `WF-ARC-0090-A` — « conservés pendant la rétention des tâches de fond (§4.4.1) » ;
  `WF-IHM-0080-A`.
- **le contrat dit** : « Ne retient, des tâches finies, que celles qui ont abouti ou échoué depuis cette date » —
  absent, rien n'est dit : toutes les tâches finies de la rétention (`background_task_retention_days`, trente jours),
  ou aucune ? `tasks_none.json` parle d'« aucune n'a fini depuis la date demandée ». La description de `kind` dit
  `backup`, `restore`, `identity_sync`, `revision_mark` et tait `import_analysis`, `import_apply`, `structure_merge`,
  `risk_occurrence`, `export`.
- **décision** : aucune.
- **proposition** : « absente, toutes les tâches finies encore conservées (`background_task_retention_days`) » ;
  une phrase par nature manquante, avec l'opération qui la crée (`openImport`, `applyImport`, `mergeCostStructure`,
  `declareRiskOccurrence`, `requestExport`).

#### A-13 — Schémas d'écriture sans description
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/access.yaml:212-223` (`UserCreate` et ses cinq propriétés),
  `:240-245` (`UserActivationWrite`), `:254-261` (`UserRolesWrite`), `:543-550` (`AccessRoleWrite`), `:510-523`
  (`Permission`).
- **spécification** : `WF-ADM-0050-A` (les attributs), `WF-ADM-0030-A` (« Ce rattachement n'accorde aucune
  permission »).
- **le contrat dit** : les règles vivent dans les descriptions des opérations (`createUser` 409/422) ; les schémas, que
  le client engendré documente, n'en portent aucune — `access_role_ids` d'`UserCreate` ne renvoie ni à
  `UNKNOWN_ACCESS_ROLE` ni à la permission d'A-01, `org_node_id` ni à WF-ADM-0030 ni à `UNKNOWN_ORG_NODE`.
- **décision** : aucune.
- **proposition** : une description par schéma et par propriété d'écriture, reprenant la règle de l'opération.

### Ce qui est juste

- **Les cinq opérations nouvelles.** `getIdentitySyncSchedule`/`setIdentitySyncSchedule` (`access.yaml:650-716`,
  `platform.yaml:528-560`) : `is_enabled`, `frequency`, `at_time` UTC, `weekday` ISO nul pour une quotidienne,
  `lock_version` ; livrée activée, quotidienne, `01:30` — « quotidienne par défaut, comme celle des sauvegardes »
  (WF-ADM-0070), à la lettre de `DECISIONS.md:9455-9463` ; `users.read`/`users.write` ; 422 symétriques de
  `BackupSchedule` avec deux exemples ; `identity_sync_schedule.json` (livrée), `_set.json` (lundi, compteur 2) ;
  la lecture de 01:30 achevée à 2 h est celle d'`identity_sync_report.json` et de `last_identity_sync` des quatre
  `system_status*.json`. `resendInvitation` (`access.yaml:521-561`) : 204, 409 `is_local_account`/`is_active_account`
  avec exemples, 503 `identity_provider` « jamais présenté comme parti » (WF-EXP-0040), journal `password_link_create`
  (`audit.yaml:33`), à la lettre de `:9464-9471`. `startIdentitySync`/`getLatestIdentitySync` : 202 `BackgroundTaskRef`
  de `kind: identity_sync`, `result_url` `/api/v1/identity-syncs/latest` (`identity_sync_succeeded.json`), compte rendu
  conforme à WF-ADM-0070 (créés, mis à jour, désactivés, dernier administrateur gardé actif et signalé
  `LAST_ADMINISTRATOR`, compte anonymisé ni modifié ni recréé, #920), 404 avant la première lecture.
- **`SystemStatus`** (`platform.yaml:3-115`) porte tout WF-ADM-0130 : disponibilité et `checked_at` par composant,
  `version` par composant (WF-CMP-0020), stockage, version installée (WF-EXP-0030), `operating_parameters` exigé —
  sept paramètres, chacun avec sa valeur livrée dans sa description (cache 600, rétention 30, avatar 524288, seuils
  900/0.85/0.05/300), exactement ceux que la spécification cite avec une valeur (l. 3863, 3916, 4099, WF-OBS-0030)
  —, les quatre derniers résultats exigés, alertes ; la description dit d'où vient chaque valeur (WF-OBS-0010). Les
  quatre fixtures sont cohérentes entre elles et avec `installation.json` (avatar 2 Mio, dit « porté par
  l'exploitant »), `readiness.json` et `identity_sync_report.json` ; `storage_full` : 220 117 073 920 /
  (220 117 073 920 + 9 663 676 416) = 95,8 % > 85 %, alerte `watch` avec ses `params` ; `copy_failed` : `problem` nul
  et motif dans l'alerte, comme `last_backup_copy` le dit ; `backup_failed` : deux alertes, `COMPONENT_UNAVAILABLE`
  `object_storage` dans `last_backup.problem`, copie externe restée à la veille.
- **Catalogue et rôles.** `PermissionCode` (51) = `permissions.json` (51, même ordre, `kind` et `fbs_code` justes :
  lecture seule pour FBS-1.3, FBS-1.5, FBS-2.1 à 2.7 ; huit irréversibles ; deux structurantes). Toute permission
  nommée dans `paths/*.yaml` (18 codes distincts) existe dans l'énumération et dans la fixture. Les trois prédéfinis
  : « Administrateur » = FBS-1 entier + `platform_restore` (WF-INTF-0030) ; « Chef de projet » = FBS-4 lecture et
  écriture, lectures FBS-3, `portfolio_projects.read`, les sept irréversibles hors `platform_restore`,
  `project_create`, sans `all_projects_read` (WF-INTF-0010) ; « Manager » = portefeuille entier, FBS-3 lecture et
  écriture — `risk_settings.write` et `indicator_settings.write` compris —, lectures FBS-4, `all_projects_read`
  (WF-INTF-0020) ; même liste dans `access_role.json`, `access_role_updated.json`, `access_role_renamed.json`,
  `access_roles_by_updated_by.json`, `me_manager.json`, `me_directory.json`. Dans les douze `me*.json`, `permissions`
  est exactement l'union des permissions des rôles d'`access_roles.json`, dans l'ordre du catalogue (vérifié par
  programme), `access_role_labels` suit `access_role_ids`. `holder_count` compte les désactivés (Chef de projet : Alix
  Moreau). Tri par libellé en points de code, tri `updated_by` comptes puis plateforme, vérifiés.
- **Comptes.** `User`/`UserSelf`/`UserCreated`, `available_commands` dans l'ordre d'`UserCommand`, `last_administrator`
  sur Camille Martin seule, `is_not_anonymized` sur Alix Moreau anonymisée (`reactivate`, `anonymize`),
  `set_access_roles` toujours listée ; les six `CommandCondition` des comptes sont dans l'énumération et décrites
  (`projects.yaml:255-268`) ; refus 409 (`STATE_FORBIDS_OPERATION`, `ALREADY_EXISTS` avec `conflicting_object_id`,
  `LAST_ADMINISTRATOR`, `ACCESS_ROLE_IN_USE`), 412, 422 (`UNKNOWN_ACCESS_ROLE`, `UNKNOWN_ORG_NODE`,
  `FIELD_READ_ONLY`) déclarés avec exemples ; compteurs des fixtures cohérents (Noé Vidal 1→2→3, Alix Moreau 4→5,
  Lucas Petit 1→2) ; `listUsers` trié nom puis prénom (vérifié), `sort_by=created_at` à égalité par nom (Bernard avant
  Martin) ; recherche « ines roux » par le prénom suivi du nom ; filtres d'audit `_from`/`_to` avec leur 422.
  `AuditAction` porte `user_create`, `user_update`, `user_deactivate`, `user_reactivate`, `user_anonymize`,
  `password_link_create`, `access_role_create/update/delete`, `user_access_roles_set` : WF-SEC-0030 pour la famille.
- **Compte courant et session.** `getMe` : permissions évaluées à chaque requête (WF-ARC-0030, WF-ADM-0110), 401
  `ACCOUNT_DEACTIVATED`/`ACCOUNT_NOT_ADMITTED` distingués avec exemples ; `closeMySessions` « sur tous ses postes »
  et `SESSION_REVOKED` (#855, WF-SEC-0020) ; `session_expired.json` « cinq minutes » = WF-SEC-0020/WF-ARC-0030. La
  phrase ajoutée par la 1.0.1 à WF-SEC-0020 (adresse de retour) n'a aucune surface d'API : la connexion refaite et
  l'adresse visée sont du front, qui obtient les jetons côté serveur (WF-ARC-0030) ; rien à porter au contrat.
  `DisplayPreferences` : langue (WF-INTF-0160, `default`/`fr`/`en`), thème, `highlight_tasks_added_after_reference`
  décrit pour les deux usages (A-06), `grids` avec `page_size` ∈ {10, 25, 50, 100} (WF-IHM-0060), `known_columns`
  (US-0650), `filters.states` de la grille `projects` (#1401 ; `preferences_project_states.json` cohérent avec sa
  description, le défaut « Chiffrage et En cours » dit « que le contrat ne porte pas » — il n'est en effet écrit
  nulle part dans la spécification, grep), chronologies et graphiques ; bornes #874/#1235 identiques entre
  description, schéma et les trois fixtures de refus. `putMyAvatar` : 400/413/422/503 décrits, `Installation` lisible
  sans session (WF-INTF-0160), borne ≤ 8 Mio.
- **Tâches de fond.** `BackgroundTaskRef` exige ses huit champs, `result_url` `uri-reference` ; les 31 fixtures de
  tâches sont cohérentes (`finished_at` nul pendant la course, `problem` sur tout échec, `progress` 100 sur tout
  succès) ; `getBackgroundTaskResult` : 404 pour un résultat supprimé ou une tâche sans fichier, 409 `task_succeeded`
  avec exemple (A-05), `Content-Disposition` avec `filename*` ; `listBackgroundTasks` paginé, filtré, 422 exemplifié.
  `getMetrics` : HTTP, interne au cluster, 404 expliqué (K-11), disponibilité sondée à chaque collecte (K-10).
- **Conventions tenues** : 401 et 503 sur toute opération gardée, `security: []` sur les quatre publiques, 500
  partout, 400/422 sur toute opération à corps, `pattern: '\S'` sur noms, prénoms et libellés, `format: email` et
  `maxLength: 254`, 404 pour la consultation refusée et 403 pour l'écriture.

### Doutes

- **`startIdentitySync` sans 409 de concurrence** (repris du 28 octobre) : `startBackup` refuse une seconde sauvegarde ;
  deux lectures simultanées écriraient les mêmes comptes. Rien dans la spécification ; aucune décision.
- **`task_interrupted_by_restore.json`** : la lecture des comptes « encore en file » est soumise le 2 juin à
  `01:00:00Z`, l'heure de la sauvegarde livrée, quand la lecture planifiée est à `01:30`. Une lecture demandée à la
  main à une heure du matin ? Le résumé ne le dit pas ; variante déclarée contrefactuelle, je ne la compte pas.
- **Deux formes pour une même garde** : `LAST_ADMINISTRATOR` (code propre, `setUserAccessRoles`, `updateAccessRole`,
  `IdentitySyncSkipped.code`) à côté de `last_administrator` (condition, `setUserActivation`) ; `ACCESS_ROLE_IN_USE`
  pour un état (rôle porté) que la règle unique d'US-0702/L1 rendrait par `STATE_FORBIDS_OPERATION`. `DECISIONS.md:
  3215-3219` les garde parce que « le refus dépend des rôles envoyés, qu'aucune commande ne dit d'avance » ; US-0702/L1
  ne les a pas retirés. La spécification ne tranche pas : non compté.
- **`updateUser` d'un compte local** : le fournisseur d'identité est-il mis à jour dans la requête (503
  `identity_provider`, rien n'est écrit) ou seulement par la lecture suivante, qui « rétablit dans le fournisseur
  l'identité que Waterfall tient » (#919) ? Entre deux lectures, le fournisseur montrerait un autre nom.
- **`getBackgroundTask` d'une tâche lancée par un autre utilisateur** : la liste l'exclut ; la lecture unitaire ne dit
  pas si elle est 404 ou 200. `no_background_task_running` suppose que le front ne la suit pas.
- **`Installation.external_backup_max_bytes`**, réglage de l'installation, n'est pas dans `OperatingParameters` quand
  `avatar_max_bytes` y est : la règle de `DECISIONS.md:9473-9476` (« chaque paramètre que la spécification cite avec
  sa valeur par défaut ») l'exclut, la spécification ne lui donnant pas de valeur. Cohérent, mais deux réglages de
  même nature sont rendus différemment.
- **`listPermissions` sans 404** et lisible par toute session (repris) ; **`listAccessRoles` sans pagination**, décidé
  (J-12, `access.yaml:762-764`) ; **`BackgroundTaskRef` sans objet ni projet** (repris), qu'un champ facultatif
  ajouterait sans rompre.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| A-01 | réglé | `fixtures/api/access_roles.json` (« Manager », `risk_settings.write`, `indicator_settings.write`), même liste dans `access_role.json`, `access_role_updated.json`, `access_role_renamed.json`, `access_roles_by_updated_by.json`, `me_manager.json`, `me_directory.json` ; `DECISIONS.md:9487-9493` |
| A-02 | réglé | `paths/access.yaml:650-716` (`getIdentitySyncSchedule`, `setIdentitySyncSchedule`), `schemas/platform.yaml:528-560` (`IdentitySyncSchedule`, livrée quotidienne `01:30`), fixtures `identity_sync_schedule*.json` (4) ; `DECISIONS.md:9455-9463` |
| A-03 | réglé | `schemas/platform.yaml:27,56-115` (`SystemStatus.operating_parameters` exigé, sept paramètres avec valeur livrée, `cache_validity_seconds` nommé par la Vérif), quatre `system_status*.json` ; `DECISIONS.md:9472-9486` |
| A-04 | réglé | `paths/access.yaml:521-561` (`resendInvitation`, 204/409/503), `invitation_not_local.json`, `invitation_deactivated.json`, `AuditAction.password_link_create` ; `DECISIONS.md:9464-9471` |
| A-05 | réglé | `paths/system.yaml:288-297` (409 `STATE_FORBIDS_OPERATION`, `task_succeeded`), `CommandCondition.task_succeeded`, `task_result_not_succeeded.json` ; `DECISIONS.md:9851-9856` |
| A-06 | réglé | `schemas/access.yaml:300-305` (description : tâches ajoutées après la référence **et** lignes à budget nul, WF-RAE-0040 ; « Absente, faux ») |
| A-07 | réglé | `components/common.yaml:115-139` (`ActorRef` `if kind: user then required: [kind, user_id, display_name]`) |
| A-08 | réglé | `schemas/access.yaml:121-135` (`org_node_id`, `has_avatar` dans `required`) |
| A-09 | réglé | `components/common.yaml:933` (huit champs exigés), `:980-984` (`result_url` `format: uri-reference`, description) |
| A-10 | réglé | `fixtures/api/access_role_delete_refused.json` (`ACCESS_ROLE_IN_USE` sur « Chef de projet », porté par Alix Moreau désactivée), `access_role.json`, `readiness.json` (sept composants, cohérents avec `system_status.json`), `tasks_status_invalid.json` |
| A-11 | réglé | `schemas/access.yaml:553-555` (« rôle d'habilitation ») ; `common.yaml:578-581` (`TASK_INTERRUPTED_BY_RESTORE` : « dont le `problem` porte le statut 409 … et non 422 ») |
| K-01 (aussi) | réglé | = A-02 |
| K-02 (aussi) | réglé | = A-03 ; forme retenue : l'objet typé, non la liste de codes (`DECISIONS.md:9473-9475`) |
| K-09 (aussi) | réglé | = A-01 |
| K-10 (aussi) | réglé | `schemas/platform.yaml:15-20` (« Les disponibilités, espaces, taux et âges viennent des métriques … les dates et résultats … sont lus dans la base »), `paths/system.yaml:95-98` (disponibilité sondée à chaque collecte) |
| Doutes du 28/10 | — | `listAccessRoles` sans pagination : décidé et dit (`access.yaml:762-764`, J-12) ; `getMetrics` 404 : expliqué (K-11) ; `installation.json` 2 Mio : assumé (`DECISIONS.md:9483`) ; `startIdentitySync` 409, `BackgroundTaskRef` sans projet, `listPermissions` sans 404 : toujours ouverts (voir « Doutes ») |

## Annexe B — Sauvegarde, restauration, paramètres de plateforme et journal d'audit

**Périmètre.** Lu en entier : `docs/api/README-fr.md` (94 l., tableau « Conventions ») ;
`docs/api/paths/platform.yaml` (584 l., 10 opérations), `docs/api/paths/audit.yaml` (190 l., 2) ;
`docs/api/components/schemas/platform.yaml` (678 l., `SystemStatus`, `OperatingParameters` et `Alert`
lus parce que `BackupSchedule` et `startRestore` les touchent), `docs/api/components/schemas/audit.yaml`
(346 l.) ; dans `components/common.yaml` (991 l.) : `Audit` et `ActorRef` (105–139), `ErrorCode`
(394–708, les codes de la famille), `ProblemParams` (730–830), `BackgroundTaskStatus` et
`BackgroundTaskRef` (924–991) ; `components/parameters.yaml` (`Limit`, `Offset`, `Search`, `BackupId`,
`ExternalBackupLocationName`), `components/responses.yaml` (en entier) ; `schemas/projects.yaml#/CommandCondition`
(106–220), `schemas/access.yaml` (`UserOrigin`, `UserCreate`, `UserUpdate`, `PermissionCode`, `AccessRole`),
`schemas/exchanges.yaml` (`FileUpload`, `FileUploadPurpose`, `ExchangeKind`), `paths/system.yaml#getLiveness`,
`paths/access.yaml#updateUser`, `paths/reference.yaml` (nom de l'entreprise, lignes 63 et 122),
`schemas/reference.yaml#/Installation` (`external_backup_max_bytes`). **62 fixtures ouvertes, toutes** :
les 44 de `platform.yaml` (`backup*`, `backups*`, `backup_schedule*`, `external_backup_location*`,
`restore_*`, `task_backup_queued`, `task_restore_queued`) et les 18 d'`audit.yaml` (15 `audit_events*`,
`audit_events_period_inverted`, 2 `audit_facets*`), plus `users.json`, `access_roles.json`, `risks.json`
pour l'univers témoin. Générateur : `tools/src/wftools/mockaudit.py` (`Inscription`, `_revisions`,
`_accounts`, `_given`, `_backuper`), `tools/tests/test_mockaudit.py` (noms des tests).
Spécification 1.0.1 : §3.3.1 (884–902), §3.4.2.2 WF-ADM-0050/0060/0100/0110 (1196–1360), §3.4.2.3 à
§3.4.2.5 (1368–1440), §4.4.1 table 10 (3849–3912), WF-DAT-0080 à 0140 (3946–4118), §4.5 (4120–4215),
WF-SEC-0030 (4249–4257), §4.6.3 (4328–4370), §4.6.4 (4369–4397), et WF-ADM-0140, WF-CYC-0090/0130,
WF-REV-0050, WF-RIS-0060, WF-CRE-0030, WF-INTF-0080/0090, WF-IHM-0060/0130, WF-ADM-0070, WF-EXP-0020.
`DECISIONS.md` : EP-02/L42 (2784–2960, journal 2887–2955), L42d (3185–3260), L43c (4083), EP-14/L42h
(4122–4200), L42m (4550), L42o (4809), EP-03/US-0410/L2 #706 (6124–6167), US-0440/L1 #705 (6169),
US-0440/L2 #604/#892 (6181–6230), US-0600 (7925–7960), US-0640/L6 (8540), US-0701/L8 (9445–9560),
US-0701/L9 (9551–9640), US-0702/L1 (9649–9775), US-0702/L2 (9777–9830). `INVENTORY.md` : lignes 66–90 et
271–300. Revue du 2026-10-28 : annexe B (771–1171), K-03 et K-04 (3145–3180), tableau général (258, 320).

### Synthèse

La famille a été reprise en profondeur depuis le 2026-10-28 : des treize constats de l'annexe B et de
K-03/K-04, douze sont réglés — `AuditProject.code` nul et `can_open` exigé, `AuditParams` complété
(`to_state`, `reason`, `backup_taken_at`, `import_kind`), `structure_merge`, `BackupSchedule` exigeant
fréquence, heure et jour avec ses deux refus du jour, la rétention qui compte toutes les sauvegardes non
marquées, `confirmed` laissé à la garde du 400, les permissions nommées partout, `AuditEvent` gardé par
décision écrite —, et un seul reste tel quel, la chronologie contradictoire du 3 juin à 14 h 04 (B-07),
que la décision dit n'avoir pas touchée. `AuditAction` couvre chaque action de WF-SEC-0030 et de
WF-ADM-0100 dans l'ordre de la spécification ; les cinq filtres de WF-ADM-0190, le tri sur chaque colonne,
la lecture sous la seule `audit_log.read`, les 409 `STATE_FORBIDS_OPERATION` des sauvegardes cohérents avec
`BackupCommand` et `CommandCondition`, la maintenance dite par la sonde, les 422 de la planification et
de la copie externe, et les 37 inscriptions du témoin tiennent, exemples compris.

Ce qui reste est de second rang. Deux majeurs, l'un et l'autre à trancher : `AuditUserField` ne peut
pas nommer le rattachement à un nœud d'organisation qu'`updateUser` change (une énumération ne s'étend
pas après le gel) ; et la planification des sauvegardes s'écrit sans refus pendant une restauration, quand
le marquage d'une sauvegarde est refusé pour la raison même que la base va être remplacée. Six mineurs :
le journal du témoin n'inscrit pas les premiers rôles des comptes créés avec eux, ni le rôle
« Administrateur » que l'installation donne (WF-EXP-0020) ; aucun exemple d'inscription `restore`, ni de
projet disparu après restauration (Vérif de WF-ADM-0190) ; B-07 et une variante non dite telle
(`backups_unverified`) ; `retainBackup` sans compteur ni exception écrite ; le 422 de `setBackupSchedule`
qui se lit exhaustif sans l'être ; deux descriptions du journal qui disent « hors du périmètre » là où la
spécification 1.0.1 dit « relues et réinscrites ». Le nom de l'entreprise (US-0600) vit dans
`ReferenceSettings`, hors de cette famille : rien à signaler ici.

**8 constats : 0 bloquant, 2 majeurs, 6 mineurs. Suivi des 13 constats du 2026-10-28 (B-01 à B-11, K-03,
K-04) : 12 réglés, 0 partiel, 1 non réglé (B-07, repris en B-05), 0 sans objet.**

### Constats

#### B-01 — `AuditUserField` ne sait pas nommer le rattachement à un nœud d'organisation

- **gravité** : majeur
- **emplacement** : `docs/api/components/schemas/audit.yaml:294-299` (`AuditUserField`,
  `enum: [last_name, first_name, email]`), `:246-251` (`AuditParams.fields`) ;
  `docs/api/components/schemas/access.yaml:225-238` (`UserUpdate`, `org_node_id` nullable, l. 236-237) ;
  `docs/api/paths/access.yaml` (`updateUser`, qui écrit `UserUpdate`)
- **spécification** : `WF-SEC-0030-A` (4254) — « la création, la modification, la désactivation et
  l'anonymisation d'un compte » sont inscrites ; `WF-ADM-0050-A` (1201) — « Un compte utilisateur porte :
  un nom, un prénom, une adresse électronique …, un rattachement facultatif à un nœud d'organisation
  (WF-ADM-0030) … »
- **le contrat dit** : `AuditParams.fields` : « `user_update` : les champs de l'identité que la
  modification a changés, dans l'ordre du compte » ; `AuditUserField` : « Un champ de l'identité d'un
  compte qu'une modification change (`user_update`), nommé comme la colonne de la table des comptes » —
  trois valeurs, aucune pour `org_node_id`, qu'`updateUser` accepte pourtant (donner, changer ou retirer
  le rattachement).
- **la fixture dit** : `audit_events_administration.json` ne montre que des `fields: ["last_name"]`
  (Lucas Petit-Laurent, Noé Vidal-Roux) ; aucun exemple ne change un nœud.
- **décision** : `DECISIONS.md:6124-6140` (#706) « les champs d'une identité modifiée … ; les valeurs
  d'une identité modifiée, avant et après, [écartées] » — la décision ne parle que de l'identité et ne
  tranche pas le rattachement ; aucune décision ne dit qu'une modification du seul nœud ne nomme rien.
  Rien dans la spécification ne s'oppose à l'une ou l'autre lecture.
- **proposition** : à trancher avant le gel, l'énumération ne s'étendant plus ensuite. Soit ajouter
  `org_node_id` à `AuditUserField` (« le rattachement au nœud d'organisation, donné, changé ou retiré ;
  la valeur n'y est pas, comme pour les autres champs ») et élargir la description de `fields` (« les
  champs du compte que la modification a changés ») ; soit écrire dans `AuditParams.fields` qu'une
  modification du seul rattachement est inscrite avec `fields` vide, et pourquoi (le nœud n'est pas une
  donnée personnelle, et l'écran le relit du compte). La première est celle qui dit après coup « qui a
  rattaché ce compte à ce service », dans l'esprit de #706 (« dire après coup qui a donné quel droit »).

#### B-02 — La planification des sauvegardes s'écrit sans refus pendant une restauration

- **gravité** : majeur
- **emplacement** : `docs/api/paths/platform.yaml:328-383` (`setBackupSchedule`, aucun 409 déclaré) ;
  contre `:224-233` (`retainBackup` 409 : « Une restauration s'exécute, qui remplace la base où le
  marquage s'écrirait : `STATE_FORBIDS_OPERATION`, `no_restore_running` ») et `:501-504` (`startRestore` :
  « Pendant qu'une restauration s'exécute, de sa mise en file à la mise en maintenance, toute autre
  écriture des sauvegardes est refusée de même par 409 — en déclencher une (`startBackup`), en marquer une
  (`retainBackup`), en restaurer une autre — »)
- **spécification** : `WF-ADM-0160-A` (1407) — « La restauration remplace l'intégralité des deux bases …
  par leur contenu sauvegardé … ses inscriptions absentes du journal restauré sont relues … et réinscrites
  après lui, de même que la liste des sauvegardes » — la planification (`BackupSchedule`) n'est pas dans ce
  que la restauration conserve ; `WF-ADM-0170-A` (1419) — la planification est « choisie par un utilisateur
  habilité » ; `WF-EXP-0040-A` (4210) — une action « n'est jamais présentée comme réussie » si elle ne peut
  aboutir.
- **le contrat dit** : le marquage est refusé pendant une restauration parce qu'il « s'écrirait » dans la
  base remplacée ; la planification, qui s'écrit dans la même base, est acceptée en 200 pendant la même
  fenêtre, puis remplacée par celle de la sauvegarde — un 200 qui ne tient pas, sans que rien ne le dise.
  `startRestore` annonce « toute autre écriture des sauvegardes » et n'en nomme que trois.
- **la fixture dit** : aucun exemple de `setBackupSchedule` pendant une restauration ; `backup_retain_refused`
  (14 h 04 min 40 s) montre le refus voisin.
- **décision** : `DECISIONS.md:4147-4168` (EP-14/L42h) décide `no_restore_running` pour la restauration, le
  déclenchement et le marquage, « qui s'écrirait dans la base que la restauration remplace » ; rien sur la
  planification (grep « planification » × « restaur » : aucune).
- **proposition** : à trancher. Soit déclarer sur `setBackupSchedule` le 409 `STATE_FORBIDS_OPERATION`,
  `params.missing_condition` à `no_restore_running`, avec un exemple engendré (`backup_schedule_refused_during_restore`,
  14 h 04 min 40 s comme ses voisins), et l'ajouter à la liste de `startRestore` (« en régler la
  planification (`setBackupSchedule`) ») ; soit écrire que la planification est gardée à travers la
  restauration comme la liste des sauvegardes — mais alors c'est la spécification qui ne le dit pas, et
  le motif du refus du marquage s'affaiblit d'autant. La première suit la lettre de WF-ADM-0160 et la
  règle que le contrat s'est donnée.

#### B-03 — Le journal du témoin n'inscrit pas les premiers rôles des comptes, ni celui de l'installation

- **gravité** : mineur
- **emplacement** : `fixtures/api/audit_events.json` (37 inscriptions, une seule `user_access_roles_set`,
  Camille Martin, 2025-09-01 09:30, « Direction de projet ») et toutes les lectures du même journal
  (`audit_events_by_actor`, `_by_object_label`, `_page`, `_exited`, `_revision_abandoned`,
  `_import_applied`) ; `tools/src/wftools/mockaudit.py:299-330` (`_given` : n'inscrit que les rôles
  créés après le compte) ; `fixtures/api/users.json` (Alix Moreau « Chef de projet », Lucas Petit
  « Chiffreur », Inès Roux « Pilotage de projet », Noé Vidal « Auditeur », Dominique Bernard « Manager »,
  Camille Martin « Direction de projet » seul) ; `fixtures/api/access_roles.json` (« Administrateur »,
  `holder_count: 0`)
- **spécification** : `WF-SEC-0030-A` (4254, 4256) — « l'attribution et le retrait d'un rôle à un compte »
  ; Vérif : « Chacune des actions énumérées produit une inscription datée et attribuée » ; `WF-EXP-0020-A`
  (4162) — l'installation crée « un unique compte administrateur local, porteur du rôle prédéfini
  « administrateur » » ; `WF-ADM-0070-A` (1225) — « La lecture n'attribue aucun rôle d'habilitation ».
- **le contrat dit** : `AuditParams.access_roles_granted` (`audit.yaml:280-286`) : « À la création d'un
  compte, ses premiers rôles » ; `DECISIONS.md:6144-6158` (#706) : « un compte créé avec son premier rôle,
  que la requête de la création inscrit après lui sous sa corrélation » (`audit_events_administration`,
  Léa Garnier).
- **la fixture dit** : quatre comptes créés par Camille Martin avec un rôle qu'elle n'a pu leur donner
  qu'à la création ou après (les rôles « Chef de projet », « Chiffreur », « Pilotage de projet »,
  « Auditeur » existent avant eux) n'ont aucune `user_access_roles_set` ; Dominique Bernard, lu de
  l'annuaire, porte « Manager » que personne n'a inscrit ; Camille Martin, créée par l'installation à
  09:00, ne porte pas « Administrateur » (`holder_count` 0) et n'en a jamais reçu ni perdu la trace. Le
  journal compte donc 37 inscriptions quand l'univers en demande au moins 43.
- **décision** : `DECISIONS.md:2887-2912` (EP-02/L42, « `test_mockaudit.py` tient la complétude ») — la
  complétude tenue est celle des révisions ; `test_an_account_is_given_the_roles_created_after_it_once_they_exist`
  (`test_mockaudit.py:172`) ne tient que le cas de `_given`. Aucune décision n'assume l'absence.
- **proposition** : `mockaudit._accounts` inscrit, pour chaque compte qui porte des rôles, une
  `user_access_roles_set` à sa création (même instant, même corrélation que `user_create`, par son créateur
  — la plateforme pour l'installation), `access_roles_granted` ses rôles dans l'ordre où il les tient ;
  pour Camille Martin, « Administrateur » donné par la plateforme à 09:00, puis à 09:30 « Direction de
  projet » donné et « Administrateur » retiré (`access_roles_withdrawn`), ce qui rend la fixture conforme
  à WF-EXP-0020 et à `holder_count` 0 — ou `users.json` lui laisse les deux rôles (aussi annexe A).
  `meta.total` passe de 37 à 43 ou 44 dans les lectures du journal entier ; `audit_events_page` (11 à 20)
  change de contenu.

#### B-04 — Ni inscription `restore`, ni projet disparu, ni quatre actions dans les exemples

- **gravité** : mineur
- **emplacement** : `docs/api/paths/audit.yaml:126-141` (quinze exemples de `listAuditEvents`) ;
  `docs/api/components/schemas/audit.yaml:228-233` (`AuditParams.backup_taken_at`), `:48-67`
  (`AuditObjectKind.external_backup_upload`), `:138-147` (`AuditProject.can_open` : « faux … pour un projet
  qui n'existe plus »)
- **spécification** : `WF-ADM-0160-A` Vérif (1409) — « la dernière inscription est la restauration
  elle-même » ; `WF-ADM-0190-A` Vérif (1437) — « Après une restauration, une inscription qui cite un projet
  créé après la sauvegarde s'affiche avec le libellé et le code de ce projet, sans mener à lui » ;
  `WF-SEC-0030-A` Vérif (4256) — « la suppression d'un rôle produi[t] … une inscription qui nomme l'action
  et l'objet ».
- **le contrat dit** : `restore` a ses paramètres (`backup_taken_at`), son objet (`backup` ou
  `external_backup_upload`, « son libellé le nom du fichier déposé »), sa date (« la fin de la
  restauration ») ; `can_open` est faux pour un projet qui n'existe plus.
- **la fixture dit** : le seul exemple qui filtre `actions=restore` est `audit_events_empty` (« la
  plateforme n'a jamais été restaurée ») ; aucun exemple ne porte `restore`, `cost_line_reinstate`,
  `access_role_delete`, `password_link_create`, `user_reactivate`, ni un objet `external_backup_upload`,
  ni un projet dont `can_open` est faux parce qu'il n'existe plus (`audit_events_auditor` le met faux par
  la permission seulement).
- **décision** : `DECISIONS.md:9494-9506` (US-0701/L8) ajoute `audit_events_auditor` et les paramètres,
  sans exemple de restauration ; la revue du 2026-10-28 (K-03, l. 3160) proposait « le projet disparu de
  la Vérif de WF-ADM-0190 ». Aucune décision n'écarte ces exemples.
- **proposition** : une variante contrefactuelle engendrée, « après la restauration de la sauvegarde du
  2 juin » : en tête l'inscription `restore` (auteur Camille Martin, objet `backup` 0906 sans libellé,
  `params.backup_taken_at` à `2026-06-02T01:00:00Z`, `occurred_at` la fin de la restauration, corrélation
  de `task_restore_queued`), puis une inscription `project_create` d'un projet créé le 3 juin et disparu,
  `project.can_open: false`, code et libellé gardés ; et, dans `audit_events_administration` ou une
  variante voisine, une `access_role_delete` (« Contrôle de gestion », `params` vide), une
  `password_link_create`, une `user_reactivate`, une `cost_line_reinstate` sur FA-2026-0295. Rien ne
  change au contrat.

#### B-05 — La chronologie du 3 juin à 14 h 04 se contredit toujours, et `backups_unverified` réécrit la nuit sans le dire

- **gravité** : mineur
- **emplacement** : `fixtures/api/task_restore_queued.json` (restauration « confirmée aujourd'hui à 14 h 04
  min 30 s et mise en file »), `backup_pending.json` et `backups_during_backup.json` (sauvegarde manuelle
  « mise en file aujourd'hui à 14 h 04 …, prise à 14 h 04 min 50 s »), `restore_during_backup_refused.json`
  (« confirmée à 14 h 04 min 20 s, pendant que la sauvegarde manuelle mise en file à 14 h 04 s'exécute …
  refusée, `no_backup_running` »), `backup_start_during_restore_refused.json` et `backup_retain_refused.json`
  (14 h 04 min 40 s, « pendant que la restauration mise en file à 14 h 04 min 30 s s'exécute ») ;
  `backups_unverified.json` (0907 `verification: failed`, 0909 manuelle de 14 h `pending`, `total: 3`)
  contre `backups.json` et `backup.json` (0907 `passed`, huit sauvegardes) et `backup_pending.json`
  (0908, la manuelle du jour, 14 h 04 min 50 s)
- **spécification** : `WF-ADM-0150-A`, `WF-ADM-0160-A`
- **le contrat dit** : `startBackup` (`platform.yaml:140-143`) : « Une sauvegarde s'exécute de sa mise en
  file à la production du fichier » ; `BackupCommand` (`schemas/platform.yaml:222-226`) : la restauration
  est indisponible « pendant qu'une sauvegarde s'exécute, `no_backup_running` manquante » ; « une
  sauvegarde prise pendant une restauration ne serait d'aucun état cohérent » (`platform.yaml:159-161`).
- **la fixture dit** : à 14 h 04 min 20 s la restauration est refusée parce que la sauvegarde de 14 h 04
  s'exécute ; à 14 h 04 min 30 s une restauration est acceptée alors que cette sauvegarde n'est prise qu'à
  14 h 04 min 50 s, pendant la restauration. Et `backups_unverified` donne à la sauvegarde 0907 une
  vérification échouée et une manuelle 0909 de 14 h, sans se dire « variante contrefactuelle » comme
  `external_backup_location_test_failed`, `audit_events_anonymized_actor` ou `audit_facets_anonymized`
  le font.
- **décision** : `DECISIONS.md:4089-4091` (EP-02/L43c : « Chacun ne vaut que pour la réponse de son
  écriture ») et `9545` (US-0701/L8 : « B-07 n'est pas touché : ses exemples ne le sont pas ») — tient
  pour la règle, mais la revue reste debout : la décision n'a pas tranché B-07, elle l'a laissé.
- **proposition** : celle de B-07 — décaler la restauration et ses trois refus liés après la production
  du fichier (14 h 05 min 30 s, 35 s, 40 s), ou avancer `backup_pending.taken_at` avant 14 h 04 min
  20 s, et accorder les résumés ; qualifier `backups_unverified` de « Variante contrefactuelle » dans son
  `summary`, puisqu'elle contredit `backups` sur le même identifiant.

#### B-06 — `retainBackup` écrit sans compteur, et l'exception n'est écrite nulle part

- **gravité** : mineur
- **emplacement** : `docs/api/paths/platform.yaml:195-236` (`retainBackup`, `PATCH`, corps `BackupRetain`,
  aucun 412) ; `docs/api/components/schemas/platform.yaml:301-305` (`BackupRetain`,
  `required: [is_retained]`) et `:255-299` (`Backup`, sans `lock_version`) ; `docs/api/README-fr.md:49`
- **spécification** : `WF-IHM-0110-A` (3311) — les écritures concurrentes
- **le contrat dit** : README : « `lock_version` sur les écritures concurrentes, refus par 412
  `STALE_LOCK_VERSION` … Le `PUT` idempotent du périmètre suivi d'une ligne de coût réel
  (`setActualCostTrackedScope`) n'en porte pas, par exception décidée : il pose l'état visé sans dépendre
  d'aucune autre valeur » — une seule exception nommée ; `retainBackup` pose de même un booléen, sans
  compteur ni 412, et ni sa description ni le README ne le disent.
- **la fixture dit** : `backup_retained`, `backup_released` : rien d'autre que `is_retained` ne change.
- **décision** : `DECISIONS.md:9784-9796` (US-0702/L2) : l'auteur veut le compteur sur les cinq écritures
  qui n'en avaient pas et écrit l'exception du périmètre suivi (« il pose l'état visé … deux requêtes
  concurrentes ne peuvent que donner le même état ou le dernier demandé ») ; `retainBackup` n'y est ni
  listé ni excepté — tient par analogie, mais n'est pas écrit.
- **proposition** : écrire l'exception, dans la description de `retainBackup` (« sans compteur ni 412 :
  le marquage pose l'état visé, comme le périmètre suivi d'une ligne de coût ») et dans la ligne du
  README (« … et le `PATCH` du marquage d'une sauvegarde (`retainBackup`), pour la même raison »). Si
  l'auteur préfère un compteur, c'est `Backup.lock_version` exigé et `BackupRetain.lock_version`, à
  faire avant le gel.

#### B-07 — Le 422 de `setBackupSchedule` se lit exhaustif et ne l'est pas

- **gravité** : mineur
- **emplacement** : `docs/api/paths/platform.yaml:358-371` (422 de `setBackupSchedule`) ;
  `docs/api/components/schemas/platform.yaml:318-327` (`frequency` énumérée, `at_time` à motif
  `^([01]\d|2[0-3]):[0-5]\d$`), `:357-359` (`BackupExternalCopy`, quatre champs exigés)
- **spécification** : `WF-ADM-0170-A` (1419) — « à une fréquence et une heure choisies »
- **le contrat dit** : le 422 énumère la rétention hors bornes, le jour hors bornes, nul ou en trop,
  l'emplacement inconnu, le chemin invalide, la rétention externe moindre — et rien de l'heure mal formée
  (`/at_time`), d'une fréquence hors de `daily`/`weekly` (`/frequency`), d'un champ exigé absent
  (`/retained_count`, `/external_copy/is_enabled`…), qui sont pourtant les refus les plus probables d'un
  formulaire ; l'opération ne renvoie pas à la réponse partagée `UnprocessableEntity` ni à la convention
  « `VALIDATION_FAILED` et les codes par champ » du README (l. 61).
- **la fixture dit** : six exemples, tous conformes à ce que la description nomme ; aucun pour l'heure ou
  la fréquence.
- **décision** : `DECISIONS.md:4644-4648` (EP-14/L42m, bornes) et `9514-9521` (US-0701/L8, le jour) :
  tiennent ; rien sur l'heure ni la fréquence.
- **proposition** : ouvrir la description par la règle générale (« `VALIDATION_FAILED`, `fields` désignant
  chaque champ en défaut par son motif — exigé absent, `VALUE_REQUIRED` ; heure hors de `HH:MM` ou
  fréquence hors de l'énumération, `VALIDATION_FAILED` — ; et, propres à la planification : … »), sans
  changer les refus.

#### B-08 — Le journal « hors du périmètre » de la restauration, quand la spécification le dit « relu et réinscrit »

- **gravité** : mineur
- **emplacement** : `docs/api/paths/audit.yaml:12-15` (`listAuditEvents` : « une restauration ne le
  remplace pas : il est hors du périmètre qu'elle restaure ») ; `docs/api/components/schemas/audit.yaml:157-159`
  (`AuditEvent` : « le journal est hors du périmètre qu'elle remplace ») ; contre
  `docs/api/components/schemas/platform.yaml:270-272` (`Backup` : « une restauration réinscrit celles de
  ses inscriptions qui suivent la date de la sauvegarde (WF-ADM-0160) ») et `paths/platform.yaml:472-473`,
  `508-510`
- **spécification** : `WF-ADM-0160-A` (1407) — « Le journal d'audit (WF-SEC-0030) est conservé à travers la
  restauration : ses inscriptions absentes du journal restauré sont relues avant le remplacement des bases
  et réinscrites après lui, de même que la liste des sauvegardes » ; `WF-SEC-0030-A` (4254) — « une
  inscription reste lisible et réinscriptible (WF-ADM-0160) ».
- **le contrat dit** : deux mécanismes pour un même fait dans le même contrat — le journal n'est pas
  remplacé (`audit.yaml`), le journal est réinscrit (`platform.yaml`). Pour le client, le résultat est le
  même ; pour qui implémente le service, la première formule laisse croire qu'une table peut être tenue
  hors du vidage des deux bases, ce que la spécification a précisément écarté en écrivant la relecture.
- **décision** : `DECISIONS.md:2913-2922` (EP-02/L42, #539 : « le journal est hors du périmètre qu'une
  restauration remplace ») — antérieure ; la spécification a depuis écrit le mécanisme (1.0.x), et
  `Backup` le reprend : la formule de la décision est dépassée par la lettre de WF-ADM-0160, sans que le
  fond change.
- **proposition** : dire la même chose aux trois endroits, dans les mots de la spécification : « une
  restauration ne le perd pas : ses inscriptions absentes du journal restauré sont relues avant le
  remplacement des bases et réinscrites après lui (WF-ADM-0160), et l'inscription de la restauration
  s'écrit une fois celle-ci faite » ; ajouter une note à EP-02/L42.

### Ce qui est juste

- **Énumérations et catalogue.** `AuditAction` (22 valeurs) couvre, dans l'ordre de WF-SEC-0030, chacune des
  actions que la spécification fait inscrire — les neuf de WF-ADM-0100 (`project_create`, `revision_mark`,
  `revision_abandon`, `reference_designate`, `structure_merge`, `project_exit`, `risk_occurrence`,
  `cost_line_exclude`, `restore`), celles que WF-SEC-0030 ajoute (`cost_line_reinstate`, `import_apply`,
  les comptes, les rôles, `user_access_roles_set`, `backup`) et celles que WF-ADM-0060 et WF-ADM-0140
  nomment (`user_anonymize`, `password_link_create`) ; `user_reactivate` tranché en EP-02/L42. Aucune
  autre exigence ne dit « inscrit au journal » (grep `inscri` sur les corps : 1213, 4254, 1407 seuls).
  `AuditObjectKind` nomme l'objet de chacune, le dépôt compris. `PermissionCode` porte `backups.read`,
  `backups.write`, `audit_log.read`, `platform_restore` ; `CommandCondition` porte `backup_verified`,
  `no_backup_running`, `no_restore_running` et les décrit ; `ErrorCode` porte `CONFIRMATION_REQUIRED`,
  `UPLOAD_PURPOSE_MISMATCH`, `BACKUP_FROM_NEWER_VERSION`, `TASK_INTERRUPTED_BY_RESTORE`,
  `UNKNOWN_EXTERNAL_BACKUP_LOCATION`, `PATH_INVALID`, `COMPONENT_UNAVAILABLE`, chacun nommé par une
  opération de la famille et porté par un exemple (`backup_schedule_unknown_location`, `_path_invalid`,
  `restore_upload_purpose_mismatch`, `restore_confirmation_mismatch`…) ; `BackgroundTaskRef.kind` porte
  `backup` et `restore` et dit `BACKUP_FROM_NEWER_VERSION` ; `ProblemParams` dit `location`,
  `backup_version`, `installed_version`.
- **Les constats réglés de la revue précédente, vérifiés à la ligne.** `AuditProject.code` nullable et
  rangé après les autres au tri (`audit.yaml:131-136`, `paths/audit.yaml:101-102`) ; `can_open` exigé,
  évalué dans les inscriptions et les facettes, faux par la permission dans `audit_events_auditor`
  (`audit.yaml:138-147`) ; `AuditParams` : `to_state`, `reason`, `backup_taken_at`, `import_kind`
  (`audit.yaml:216-239`), portés par `audit_events_exited` (`completed`, `reason: null`) et par chaque
  `import_apply` (`actual_costs`, `estimate`) ; `structure_merge` à son rang, description et fixtures
  accordées ; `BackupSchedule.required` à six champs, `weekday` nul pour une quotidienne, `VALUE_REQUIRED`
  et `VALIDATION_FAILED` sur `/weekday` dits et exemplifiés (`backup_schedule_weekday_missing`) ;
  `retained_count` « manuelles ou planifiées, celles qui sont marquées exceptées », et `backup_released`
  qui le dit de la manuelle du 30 janvier (« la plus ancienne des huit sauvegardes non marquées ») ;
  `SystemStatus` exige ses quatre dernières opérations ; `confirmed` sans `const` ni `required`, 400
  `CONFIRMATION_REQUIRED` pour absent, faux ou date d'une autre sauvegarde, 422 pour deux désignations ou
  aucune (`RestoreRequest`, `startRestore` 400/422) ; `AuditObject.label` distingue `backup` et `restore`,
  `AuditEvent.project` nomme le dépôt ; `getBackup` et `getBackupSchedule` nomment `backups.read` ;
  `AuditEvent`/`audit_event_id` gardés par décision écrite (DECISIONS 9507-9513).
- **Conventions.** `from`/`to` sur `taken_at` et `occurred_at` (fin exclue, 422 `/query/to`
  `VALUE_OUT_OF_RANGE` avec `params.minimum`, `DATE_INVALID`), exemples conformes ; `size_bytes_min/_max`
  et son 422 (`backups_bounds_inverted`, `minimum` entier) ; listes `explode: false` (`origins`,
  `verifications`, `actions`) ; tri sur chaque colonne des deux tables (WF-IHM-0060) avec départage par
  l'ordre sans tri puis l'identifiant, textes en points de code, nuls après (`audit_events_by_actor`,
  `_by_object_label` vérifiés ligne à ligne : « Référence » après « Retard », minuscules après
  majuscules, plateforme et sauvegardes en queue) ; recherche sans casse ni accents
  (`audit_events_search`) ; 401 et 503 partout, 500 partout, 400 et 422 sur chaque corps, 412 sur
  `setBackupSchedule` ; 404 pour la lecture refusée, 403 pour `backups.write` et `platform_restore` ;
  409 `STATE_FORBIDS_OPERATION` + `missing_condition` sur `startBackup`, `retainBackup`,
  `downloadBackup`, `startRestore`, chacun avec ses exemples, cohérents avec `BackupCommand`
  (`backups_during_backup` : `restore` seule indisponible ; `backup_pending` et `backups_unverified` :
  `download` et `restore` sous `backup_verified`, marquage disponible ; `backups_reader` : liste vide
  sous `backups.read` seule) ; tâche de fond pour la sauvegarde et la restauration, maintenance dite par
  `getLiveness` à 200 et le reste à 503 `database` (#604) ; aucune phrase localisée.
- **Spécification → contrat.** WF-ADM-0150 (liste datée, taille, vérification ; copie hors plateforme par
  `downloadBackup`, nommé et mesuré ; une seule sauvegarde à la fois) ; WF-ADM-0160 (deux bases, confirmation
  par la date — de la liste ou du manifeste du dépôt —, journal et liste des sauvegardes conservés, tâches
  restaurées en échec `TASK_INTERRUPTED_BY_RESTORE`, inscription de la restauration, aucune restauration
  partielle, dépôt gardé jusqu'à la fin de la tâche) ; WF-ADM-0170 (fréquence, heure UTC, jour ISO,
  rétention 1–365, marquage, copie externe vers un emplacement déclaré par l'installation sans secret,
  alertes `scheduled_backup_failed` et `scheduled_backup_copy_failed`, planification livrée quotidienne
  et jamais 404) ; WF-EXP-0050 (rétention externe ≥ plateforme, `params.minimum` la rétention de la
  plateforme : `backup_schedule_retention_too_short`) ; WF-ADM-0190 (cinq filtres, récent d'abord, lien
  par `can_open`, nommé par code et libellé sinon, seule permission, lecture seule, sans projet ouvert) ;
  WF-SEC-0030 (action, date, auteur, objet, projet ; libellés gardés au moment de l'action ;
  anonymisation seule modification : `audit_events_anonymized_object`, `_anonymized_actor`,
  `audit_facets_anonymized` cohérents avec le compte …303 ; une action qui en produit d'autres sous une
  corrélation : fusion → marquage → désignation, sortie → abandon) ; WF-ARC-0110 (codes et libellés,
  jamais de phrase : `ExternalBackupFailure`, `AuditParams`) ; WF-OBS-0020 (`correlation_id` de
  l'inscription et son filtre) ; WF-DAT-0120 (dépôt d'un jour : `restore_not_found`) ; §4.4.1 (régime
  plateforme, références sans clé étrangère : `AuditObject`/`AuditProject` par identifiant et libellé).
- **Univers témoin.** Sept planifiées du 28 mai au 3 juin à `01:00Z` ⇔ `at_time` `01:00`, rétention 7 ;
  manuelle du 30 janvier marquée ; tailles croissantes (`backups_by_size`) ; période de juin à Paris
  (`backups_period`, `2026-05-31T22:00:00Z`) ; copie de Lyon, trente copies, `secours-lyon` déclaré dans
  `external_backup_locations` ; 37 inscriptions datées de leurs sources (`marked_at`, `taken_at`, audits des
  comptes et des rôles), `occurred_at` des sauvegardes = `taken_at`, auteur `platform` des planifiées et
  de l'installation ; `risk_occurrence` nomme la révision en cours 102 sans nom, `structure_merge` la
  révision « Référence », l'import du devis la 102 (`audit_events_import_applied`) ; `audit_events_page`
  (11 à 20 sur 37) ; facettes sans la plateforme, ordre par nom puis identifiant.

### Doutes

- **« Et leur code pour un projet ou un rôle de ressource »** (WF-SEC-0030, 4254). Aucune action inscrite
  n'a un rôle de ressource pour objet, et le contrat n'en garde donc aucun code ; si la spécification
  visait le rôle d'habilitation, celui-ci n'a pas de code (`AccessRole`, `AuditAccessRole` : identifiant
  et libellé). Je tiens la phrase pour un reste de la troisième passe (commit 7dc06e9d) et ne compte
  pas de constat ; à confirmer par l'auteur de la spécification.
- **Les tâches que la restauration garde** (`startRestore`, l. 504-508, #987) : « la sienne, celles des
  sauvegardes » reprennent l'état gardé quand WF-ADM-0160 dit « les traitements en attente ou en cours dans
  les bases restaurées sont terminés en échec ». La liste des sauvegardes survivant par la spécification
  même, les tâches qui la produisent ne sont pas « dans les bases restaurées » ; je ne tranche pas, comme
  la revue précédente.
- **Ce qu'« une sauvegarde s'exécute » veut dire pour le front.** `no_backup_running` cesse de manquer à
  la production du fichier (`startBackup`, L42h), tandis que la tâche `backup` « prend la sauvegarde …
  et la vérifie » (`BackgroundTaskRef.kind`) et reste `running` pendant la vérification : un front qui
  lirait l'état de la tâche pour griser « Sauvegarder maintenant » contredirait le serveur. Le contrat le
  dit, mais à deux endroits ; une phrase dans `BackgroundTaskRef.kind` (« la tâche court encore quand la
  sauvegarde ne s'exécute plus au sens des commandes ») lèverait le doute.
- **Une modification de rôle qui ne change rien est inscrite, une attribution qui ne change rien ne l'est
  pas** (#706, `audit_events_administration` : « Contrôle de gestion » enregistré sans changement, granted
  et withdrawn vides). Asymétrie décidée ; notée seulement.
- **`startRestore` 404** nomme « la permission de consulter les sauvegardes » comme ce dont le défaut cache
  une sauvegarde à qui restaure : un porteur de `platform_restore` sans `backups.read` ne voit donc rien à
  restaurer. Cohérent avec la liste (404) ; la spécification ne dit pas si restaurer suppose de lire.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| B-01 | réglé | `schemas/audit.yaml:131-136` : `code` `anyOf [string, null]`, « nul pour un projet qui n'en avait pas encore » ; tri `paths/audit.yaml:101-102` ; DECISIONS 9494-9496 |
| B-02 | réglé | `schemas/audit.yaml:216-239` : `to_state`, `reason`, `backup_taken_at`, `import_kind` ; « jusqu'à l'EPIC qui les réalise » retiré ; `audit_events_exited`, `audit_events_import_applied` ; DECISIONS 9498-9501 |
| B-03 (aussi K-03) | réglé | `schemas/audit.yaml:138-147` : `can_open` exigé, inscriptions et facettes, faux pour un projet disparu ; `audit_events_auditor` ; DECISIONS 9494-9506. L'exemple du projet disparu manque encore : B-04 ici |
| B-04 | réglé | `schemas/platform.yaml:309` (`required` à six), `:328-337` (`weekday`) ; `paths/platform.yaml:364-366` ; `backup_schedule_weekday_missing` ; DECISIONS 9514-9518 |
| B-05 | réglé | `schemas/platform.yaml:343-347` « manuelles ou planifiées, celles qui sont marquées à conserver exceptées » ; `paths/platform.yaml:334-336` ; `backup_released` ; DECISIONS 9518-9520 |
| B-06 | réglé | décision écrite, nom gardé : DECISIONS 9507-9513 (« `event` est le mot des journaux structurés … la table vaut pour les tables de la base ») |
| B-07 | non réglé | fixtures inchangées (DECISIONS 9545 : « B-07 n'est pas touché ») ; repris en B-05 de cette annexe, avec `backups_unverified` |
| B-08 | réglé | `schemas/platform.yaml:5-14` : les quatre dernières opérations exigées ; DECISIONS 9485 |
| B-09 | réglé | `schemas/platform.yaml:497-502, 520-526` ; `paths/platform.yaml:526-532` (400), `569-577` (422) ; DECISIONS 9537-9538, US-0702/L3 (#1664) |
| B-10 | réglé | `schemas/audit.yaml:86-88` (« pour l'action `backup` … pour `restore`, … `params.backup_taken_at` »), `:186-187` (« dépôt d'une sauvegarde ») |
| B-11 | réglé | `paths/platform.yaml:177-178` (`getBackup`), `:312-313` (`getBackupSchedule`) |
| K-03 | réglé | voir B-03 |
| K-04 | réglé | `schemas/audit.yaml:9, 22` (`structure_merge`), `:52` (« la structure différentielle fusionnée »), `:161` ; fixtures `audit_events*` ; DECISIONS 2936-2941, 9530-9531 (US-0640/L6b #1594) |

## Annexe C — Référentiel (paramètres de coûts, de ressources, de risques, d'indicateurs)

**Périmètre.** Lu en entier : `docs/api/README-fr.md` (94 l., les Conventions) ; `docs/api/paths/reference.yaml` (1 989 l., 31 opérations) ; `docs/api/components/schemas/reference.yaml` (1 122 l.) ; dans `common.yaml` (991 l.) les types élémentaires (`Decimal`, `Money`, `Hours`, `Percent`, `Year`, `LockVersion`, `Audit`, `ActorRef`), `Problem`, `ErrorCode` (394–707), `FieldProblem`, `ProblemParams` (730–828) ; `parameters.yaml` (`Limit`, `Offset`, `Search`, `SortOrder`, `IncludeInactive`, `IsActive`, les identifiants de chemin, `RateYear`) ; `responses.yaml` en entier ; `CommandCondition` (`projects.yaml:106-230`), `PermissionCode` (`access.yaml:433-490`), `EmployedReference` et `RevisionSnapshot` (`revisions.yaml:226-265`), `getRateUpdateProposal`/`applyRateUpdate` (`revisions.yaml:342-380`), `RiskMatrixLevel` (`risks.yaml:523-537`) ; `INVENTORY.md` (lignes 92–128). Spécification 1.0.1 : §3.2.2 (642–682), §3.4.4 en entier (1608–1900), WF-INTF-0160 (563), WF-CYC-0120 (892), WF-ADM-0100 et 0110 (1334–1360), WF-PLA-0010 (2232), WF-PLA-0160 (2268), WF-DEV-0010 (2487), WF-RIS-0040 (2769), WF-IND-0070/0080/0130 (seuils, 3012–3050), WF-IHM-0060 (3246), WF-IHM-0130 (3330), §4.4.1 (3849–3935), WF-DAT-0070 (3934), WF-DAT-0090 (3958), WF-EXP-0020 (4157), §4.6.2 (4259–4330), annexe B (4896–4908). `DECISIONS.md` : « Le référentiel (US-0250/L1) » (708–743), « L'univers témoin » (1777–1800, 1940–1985, 2000–2008, 2380–2396), EP-02/L42a (3058–3080), EP-02/L42g (3664–3680), US-0600 (7925–7960), US-0620 (8009–8091), US-0640/L1 (8208–8336), L2 (8337–8430), L6 (8540–8685), US-0701/L2 (9124–9127), US-0701/L8 (9445–9550), US-0702/L1 (9649–9776), L2 (9777–9868), US-0660/L1 (9995–10025), « Vocabulaire » (10117–10128). **117 fixtures ouvertes** (les 122 références de `reference.yaml` renvoient à 117 fichiers distincts) : les 110 petites lues une à une, les sept de `volume/` (`cost_categories*` ×4, `hourly_rate_grid*` ×3, plus `hourly_rates`) par un contrôle programmé (`revue/check_volume.py` : unicité des codes et codes comptables, tri, `meta`, états et commandes, `years` croissantes, cellules alignées sur `years` et sur la catégorie de la ligne, bornes incluses, `hourly_rates` = ligne MO-001 de la grille, 150 lignes = 150 catégories de main-d'œuvre).

### Synthèse

La famille est en bon état : les neuf constats de la revue du 28 octobre et les trois constats M qui la croisaient sont réglés ou assumés, à l'exception des résumés de trois fixtures restés sur « le budget de référence » (C-04, partiel). Les refus ont une seule forme (409 `STATE_FORBIDS_OPERATION` avec sa condition, 409 `ALREADY_EXISTS` avec `fields[]` et `conflicting_object_id`, `_label` pour les nœuds et les rôles, 412 partout, 422 par champ dans l'ordre dit), les six listes portent le même 403 d'`include_inactive`, la devise se lit par toute session, les objets uniques ont leur `audit`, `labor`/`LABOUR` est assumé au Vocabulaire. Les fixtures racontent un univers cohérent : rattachements des rôles vers des objets lus, un seul calendrier par défaut, cascades et conditions conformes aux descriptions, grille de 150 × 15 sans décalage, bornes incluses, 103 tâches de câblage du monteur câbleur derrière le refus du calendrier.

Ce qui domine : une question laissée ouverte par US-0702/L2 et que le gel ne peut pas emporter telle quelle — **qui lit les objets actifs du référentiel**. Trois listes gardent un 404 « faute de la permission de consultation » sans nommer cette permission, deux listes dites « lisibles sans la permission du référentiel » et la grille déclarent un 404 qu'elles ne peuvent pas produire, et trois des quatre permissions de consultation de FBS-3 n'ouvrent rien de nommé dans le contrat (C-01, majeur). Le reste est de la clarté : l'amorçage du témoin que les fixtures attribuent à un compte et à des valeurs non livrées sous un audit de la seule plateforme (C-02), trois résumés en retard sur la spécification (C-03), `params.cost_categories` non typé (C-04), cinq refus sans exemple (C-05), ce que les images figées conservent (C-06), l'année de chemin hors bornes (C-07), deux précisions de lecture (C-08, C-09).

**9 constats : 0 bloquant, 1 majeur, 8 mineurs. Suivi des 13 constats du 2026-10-28 (C-01 à C-09, J-08, M-12 à M-14) : 11 réglés, 1 partiel (C-04), 0 non réglé, 1 sans objet (C-08, assumé par décision).**

### Constats

#### C-01 — Qui lit les objets actifs du référentiel : trois 404 sans permission nommée, trois 404 inatteignables, trois permissions de consultation qui n'ouvrent rien
- **gravité** : majeur
- **emplacement** : `docs/api/paths/reference.yaml:224` (`listOrgNodes`, `'404': NotFound`, description 150–169 muette sur qui lit les nœuds actifs), `:921` (`listCalendars`, idem, 846–863), `:1255` (`listCostTypes`, idem, 1188–1200) ; `:547` (`listResourceRoles`, `'404'`) contre `:446-447` (« Les rôles actifs se lisent sans la permission du référentiel : quiconque consulte un projet… ») ; `:1498` (`listCostCategories`, `'404'`) contre `:1443-1444` (« Les catégories actives se lisent sans la permission du référentiel ») ; `:1771` (`getHourlyRateGrid`, `'404'`, description 1703–1715 qui ne dit que le 403 d'`include_inactive`) ; `docs/api/components/responses.yaml` (`NotFound` : « invisible faute de la permission de consultation ») ; `docs/api/components/schemas/access.yaml:433-490` (`PermissionCode` : `cost_settings.read`, `resource_settings.read`, `risk_settings.read`, `indicator_settings.read`) — `grep` sur `docs/api/paths` et `components` : seule `cost_settings.read` est nommée par une opération (`getActualCostMapping`, `reference.yaml:1898`).
- **spécification** : `WF-ADM-0100-A` — « Les permissions sont définies par fonction de second niveau […] à deux niveaux — consulter, modifier » ; Vérif : « Chaque fonction de second niveau de l'arborescence est représentée par ses deux permissions » ; `WF-ADM-0110-A` — « L'interface présente le même écran pour un objet inexistant et pour un objet dont la consultation n'est pas permise » ; README : « 404 lorsque la permission de consultation manque ».
- **le contrat dit** : six lectures de collections sans paramètre de chemin déclarent le 404 partagé. Pour les nœuds, les calendriers et les natures, c'est le seul indice qu'une permission de consultation garde la liste, et aucune description ne la nomme (`resource_settings.read` ? `cost_settings.read` ?). Pour les rôles et les catégories, la description dit la liste ouverte à quiconque consulte un projet : le 404 déclaré n'a alors aucune cause possible — une collection sans identifiant ne peut être ni inexistante ni invisible. Pour la grille, ni l'un ni l'autre n'est dit. `getReferenceSettings` (32–54), lisible « par toute session ouverte, sans permission », et `getDurationUnits` (772–790, « lisibles par quiconque consulte un projet ») n'ont pas de 404 : la famille connaît donc la forme d'une lecture ouverte, et ne l'applique pas aux listes qu'elle dit ouvertes. Conséquence : `risk_settings.read` et `indicator_settings.read` ne gardent plus rien depuis US-0701/L8, et `resource_settings.read` rien de nommé ; le catalogue les garde (WF-ADM-0100 l'exige) sans qu'une description dise ce qu'elles ouvrent.
- **la fixture dit** : `org_nodes_reader`, `calendars_reader`, `cost_types_reader`, `resource_roles_reader`, `volume/cost_categories_reader` décrivent toutes « une session qui ne peut pas modifier » la fonction — jamais une session qui ne peut pas la *consulter* ; aucun exemple de 404 n'existe pour ces six lectures.
- **décision** : `DECISIONS.md:9857-9861` (US-0702/L2) « La question « qui lit les objets actifs », que la revue laissait au passage, n'est pas tranchée ici : le 404 reste tel qu'il était » — ouverte, non assumée ; `:9522-9526` (US-0701/L8, C-02) ouvre `getReferenceSettings` à toute session sans dire ce que deviennent `risk_settings.read` et `indicator_settings.read` ; `:3074-3075` (EP-02/L42a) : « la liste est vide pour qui lit le référentiel sans [la permission de modification], l'estimateur qui choisit le rôle d'une ligne ». Aucune ne nomme la permission de consultation d'une liste.
- **proposition** : à trancher avant le gel, car un 404 qui apparaît ou disparaît sur une lecture est un changement du contrat. Deux formes cohérentes : **(a)** les objets actifs des six listes et de la grille se lisent par toute session ouverte — le libellé d'un nœud sert à l'en-tête du plan de charge (`indicators.yaml:446`), celui d'un calendrier au rôle, le type d'une nature au formulaire de catégorie — : retirer le `'404'` de `listOrgNodes`, `listResourceRoles`, `listCalendars`, `listCostTypes`, `listCostCategories`, `getHourlyRateGrid`, écrire dans chacune « Les objets actifs se lisent par toute session ouverte ; les désactivés et toute écriture relèvent de `<fonction>.write` », et dire dans `PermissionCode` que `resource_settings.read`, `risk_settings.read` et `indicator_settings.read` n'ouvrent, aujourd'hui, rien que toute session ne lise déjà (le catalogue les garde pour WF-ADM-0100) ; **(b)** les actifs des nœuds, des calendriers et des natures relèvent de `resource_settings.read`/`cost_settings.read` : garder leur 404 et l'écrire (« lue sous `resource_settings.read`, 404 sans elle, comme `getActualCostMapping` »), retirer le 404 des rôles, des catégories et de la grille, ou les ranger aussi sous la permission et corriger leurs descriptions. La forme (a) est celle que les fixtures `*_reader` et les décisions L42a/US-0250 supposent déjà.

#### C-02 — L'amorçage du témoin : des paramètres non livrés sous un audit de la seule plateforme, et des objets de l'installation créés par un compte
- **gravité** : mineur
- **emplacement** : `fixtures/api/reference_settings.json:8-13` (`probability_bounds` `0.1`, `0.3`, `0.6`), `:43` (`max_weeks_between_reviews: 8`), `:44-54` (`audit` : `created_by` et `updated_by` `platform`, `2025-09-01T09:00:00Z`, `lock_version: 1`) ; `fixtures/api/calendars.json:49` (« Semaine standard », par défaut, huit heures du lundi au vendredi) et `:72-75` (`created_by` Camille Martin, `2025-09-01T09:00:00Z`) ; `fixtures/api/cost_types.json:81,101` (nature `PRV`, `created_by` Camille Martin) ; `fixtures/api/volume/cost_categories.json` (PRV-001 « Provisions pour risques », `created_by` `user`) ; `fixtures/api/reference_readiness_incomplete.json:2` (« l'amorçage a créé le calendrier par défaut […] et la nature et la catégorie de provision pour risques »).
- **spécification** : `WF-EXP-0020-A` — « L'installation […] crée […] un calendrier actif désigné par défaut, livré à huit heures travaillées du lundi au vendredi […], une nature de coût de type provision pour risques et sa catégorie (WF-REF-0030), les bornes de la matrice de risques, les seuils d'alerte des indices et le délai maximal entre deux revues, avec des valeurs livrées — 25 %, 50 % et 75 % pour les bornes de probabilité, 1 %, 5 % et 10 % pour les bornes de gravité, 0,9 et 0,8 pour les seuils de chaque indice, six semaines pour le délai — modifiables ensuite » ; `WF-DAT-0070-A` — « l'auteur étant le compte à l'origine de l'action, ou la plateforme pour un traitement automatique » ; `common.yaml:105-108` (`Audit` : « `platform` désigne un traitement automatique »).
- **le contrat dit** : `ReferenceSettings.audit` (`schemas/reference.yaml:808-813`) : « la plateforme à l'amorçage (WF-EXP-0020), puis l'auteur de chaque écriture, quel que soit le champ qu'elle porte ».
- **la fixture dit** : des bornes de probabilité à 10/30/60 % et huit semaines — ni les valeurs livrées, ni celles d'une écriture : l'audit dit que personne n'a écrit depuis l'amorçage (`updated_by` `platform`, version 1). Et le calendrier, la nature et la catégorie que l'installation crée portent un compte pour auteur, au même instant que l'amorçage de la plateforme (`2025-09-01T09:00:00Z`), là où `reference_settings`, `duration_units` et `actual_cost_mapping` portent bien la plateforme.
- **décision** : `DECISIONS.md:734-735` (US-0250/L1) assume « huit semaines entre deux revues, que dépasse le projet témoin de `pilot_health` » — la valeur est voulue ; `:2000-2004` date « l'installation, son référentiel et ses comptes » au 1er septembre 2025 sans nommer l'auteur des objets d'amorçage ; `:7948-7956` (US-0600) : les `reference_settings*` sont « écrits à la main ». Aucune décision sur l'auteur ni sur la version des paramètres communs du témoin.
- **proposition** : garder les valeurs et corriger l'histoire — `reference_settings` : `updated_by` Camille Martin à une date postérieure à l'amorçage (le 1er septembre 2025 à 9 h 30, ou le 5 janvier 2026 que les audits portaient avant #372), `lock_version: 2` ; `reference_settings_thresholds_updated`, `_matrix_updated`, `_company_updated` à la version 3, `reference_settings_stale` à `expected_lock_version: 3` (et leurs résumés « version 2 » → « version 3 ») ; ou, à trancher, remettre le témoin aux valeurs livrées sauf le délai. Pour le calendrier par défaut, la nature `PRV` et sa catégorie PRV-001 : `created_by: { kind: platform }` à l'amorçage, `updated_by` de même ou Camille si leur libellé a été repris (WF-EXP-0020 : « modifiables ensuite comme tout libellé saisi ») — dans `mockreference`/`mockcalendar` et les fixtures écrites à la main qui les reprennent (`calendars*`, `cost_types*`, `calendar_default*`, `calendar_deactivation_refused`).

#### C-03 — Trois résumés disent encore « du budget de référence » (suite de C-04)
- **gravité** : mineur
- **emplacement** : `fixtures/api/reference_settings.json:2` (« à 1, 5 et 10 % du budget de référence »), `fixtures/api/reference_settings_matrix_updated.json:2` (« les gravités à 2, 5 et 10 % du budget de référence »), `fixtures/api/reference_settings_bounds_refused.json:2` (« gravités bornées à 5, 1 et 10 % du budget de référence »).
- **spécification** : `WF-REF-0160-A` — « trois bornes de gravité, exprimées en pourcentage de l'assiette du projet — son budget de référence ou, tant qu'il n'en a pas, le total hors provisions du devis de sa révision courante ».
- **le contrat dit** : `schemas/reference.yaml:858-862` (`RiskMatrixSettings`) a été corrigé : « en pourcentage de l'assiette du projet — son budget de référence ou, tant qu'il n'en a pas, le total hors provisions du devis de sa révision courante » ; `RiskMatrixLevel` (`risks.yaml:527-532`) dit de même.
- **la fixture dit** : l'ancienne assiette, dans trois résumés écrits à la main.
- **décision** : `DECISIONS.md:9530-9548` (US-0701/L8) liste les mineurs repris (C-05, C-06, C-07, C-09, M-12, M-13) sans C-04 ; le schéma l'a suivi par ailleurs (H-06), les résumés non. Aucune ne les assume.
- **proposition** : « 1, 5 et 10 % de l'assiette du projet — son budget de référence ou, avant lui, le total hors provisions de son devis courant » dans les trois résumés.

#### C-04 — `params.cost_categories` n'est pas typé dans `ProblemParams`
- **gravité** : mineur
- **emplacement** : `docs/api/components/common.yaml:730-828` (`ProblemParams`, propriétés typées : `state_enum`, `subordinate_node_ids`, `missing_rates`, `resource_roles`, `projects`, `tasks`, `estimate_lines`, `risks`, `subproject`, `columns`, `missing_columns`) ; `:224-230` (`Problem.params`, description : « `cost_categories` quand `missing_condition` nomme `cost_type_unused` ou `cost_type_unrated` […] chacune par son identifiant, son code et son libellé (`cost_category_id`, `code`, `label`) ») ; `docs/api/paths/reference.yaml:1341-1366` (`updateCostType`, 409) ; `fixtures/api/cost_type_kind_refused.json:7-20`.
- **spécification** : `WF-ARC-0110-A` (un code et ses paramètres, jamais une phrase) ; `WF-REF-0030-A`.
- **le contrat dit** : « Ceux que plusieurs refus partagent sont déclarés ici, facultatifs et typés » (`ProblemParams`, description). `resource_roles` l'est, pour `cost_type_without_role` et `cost_category_without_role` ; `cost_categories`, de même forme, porté par deux conditions du même 409 (`cost_type_unused`, `cost_type_unrated`), reste ouvert : le client engendré le reçoit en `unknown`, quand il reçoit `resource_roles` typé pour le même écran.
- **la fixture dit** : `cost_categories` à deux éléments `{cost_category_id, code, label}`, dans l'ordre du code — conforme à la description, invérifiable par le schéma.
- **décision** : `DECISIONS.md:8351-8370` (US-0640/L2) : « ceux que plusieurs refus partagent », la liste typée ne le compte pas ; `:5849` (EP-14/L42s) crée le paramètre sans forme. Aucune n'écarte son typage.
- **proposition** : dans `ProblemParams`, `cost_categories: { type: array, items: { $ref: '#/ProblemCostCategory' } }` avec `ProblemCostCategory` (`cost_category_id`, `code`, `label`, requis), sur le modèle de `ProblemResourceRole` ; compatible, aucun exemple ne change.

#### C-05 — Cinq refus déclarés sans exemple ni description propre
- **gravité** : mineur
- **emplacement** : `docs/api/paths/reference.yaml:546` (`listResourceRoles`, `'403': Forbidden` générique), `:1497` (`listCostCategories`), `:1770` (`getHourlyRateGrid`) — à comparer à `:214-223`, `:911-920`, `:1245-1254` (les trois listes corrigées par US-0702/L2, 403 décrit et exemplifié `*_inactive_forbidden`) ; `:1366` (`updateCostType`, `'412': PreconditionFailed` générique), `:1614` (`updateCostCategory`, idem) — à comparer aux douze autres 412 de la famille, chacun avec son `*_stale`.
- **spécification** : `WF-REF-0150-A`, `WF-ADM-0100-A` (le 403 d'`include_inactive`) ; `WF-IHM-0110-A` (le 412) ; README « Vérifier, assembler, simuler » : le faux back sert les exemples du contrat.
- **le contrat dit** : les descriptions de `listResourceRoles` (446–450) et `listCostCategories` (1443–1446) nomment le refus par 403, celle de `getHourlyRateGrid` (1707–1709) aussi ; aucune réponse 403 ne le reprend ni ne l'illustre. `updateCostType` et `updateCostCategory` renvoient à `PreconditionFailed` seul.
- **décision** : `DECISIONS.md:9857-9861` (US-0702/L2) a donné un exemple aux trois listes qui n'avaient pas le 403, pas aux trois qui l'avaient ; `:6047` (EP-03 #799/#827, section « Le 412 et le 422 de chaque opération qui peut les rendre ») : « Le 412 et le 422 de chaque opération qui peut les rendre ». Aucune n'exempte ces cinq réponses.
- **proposition** : `resource_roles_inactive_forbidden`, `cost_categories_inactive_forbidden` (`resource_settings.write`, `cost_settings.write`), `hourly_rate_grid_inactive_forbidden` (`cost_settings.write`), engendrés par `wftools.mockdeclared` comme les trois existants, avec la même description de réponse ; `cost_type_update_stale` et `cost_category_update_stale` (la version 2 de `cost_type_updated`/`cost_category_updated`), le 412 décrit comme sur les activations.

#### C-06 — Ce qu'une image figée conserve de `is_active`, `audit` et `lock_version` n'est dit que dans DECISIONS
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/reference.yaml:166-220` (`ResourceRoleImage` : `is_active`, `audit`, `lock_version` requis ; `org_node_label`, `cost_category_label`, `calendar_label` « résolu à la lecture, actif ou désactivé »), `:333-355` (`CalendarImage` : `is_default`, `is_active`, `audit`, `lock_version`), `:553-613` (`CostCategoryImage` : `cost_type_label`, `cost_type_kind`, `cost_type_is_active` « résolu à la lecture », `is_active`, `audit`, `lock_version`), `:667-676` (`HourlyRateImage` : « sa valeur seule, sans l'audit ni le compteur du taux du référentiel, qui bougent après le marquage sans rien changer à la révision ») ; `docs/api/components/schemas/revisions.yaml:246-265` (`EmployedReference` : « Images des objets du référentiel employés, figées au marquage […] sans les commandes »).
- **spécification** : `WF-REF-0130-A` — « n'affecte aucune révision marquée, qui conserve les valeurs employées au moment de son marquage […] une révision marquée est toujours lue […] comme à travers l'organigramme courant (§3.4.4.2.1) » ; `WF-REV-0030-A`.
- **le contrat dit** : les trois images disent « l'image seule, sans commandes : celle qu'une révision marquée fige » et, champ par champ, des libellés « résolus à la lecture » ; rien ne dit si, dans une image figée, `is_active`, `audit`, `lock_version`, `is_default`, `cost_type_is_active` et les libellés de rattachement sont ceux du marquage ou ceux d'aujourd'hui — quand `HourlyRateImage` exclut les deux premiers précisément parce qu'ils bougent.
- **la fixture dit** : `revision_marked.json` (`snapshot.employed_reference`, marquée le 1er février 2026) : ING-ELEC `is_active` vrai, `lock_version` 1, `audit` du 1er septembre 2025 ; « Semaine standard » `is_default` vrai — indiscernable, aucun objet employé n'ayant changé depuis.
- **décision** : `DECISIONS.md:9124-9127` (US-0701/L2, E-11) : « Les trois autres images gardent les leurs, celles de l'objet tel qu'il était au marquage » — tient, mais le contrat ne le dit pas, et « résolu à la lecture » laisse lire l'inverse pour les libellés.
- **proposition** : une phrase dans les trois images, à la suite de « celle qu'une révision marquée fige » : « Dans une image figée (`EmployedReference`), chaque champ — libellés des rattachements, état, `audit` et `lock_version` compris — est celui de l'objet au marquage (WF-REF-0130) ; « résolu à la lecture » ne vaut que pour l'objet lu aujourd'hui. » À l'annexe E de dire si l'organigramme courant (WF-REF-0130, « comme à travers l'organigramme courant ») doit au contraire faire d'`org_node_label` un libellé d'aujourd'hui.

#### C-07 — `setHourlyRate` : l'année du chemin hors de 2000–2100 n'a pas de refus dit
- **gravité** : mineur
- **emplacement** : `docs/api/paths/reference.yaml:1872-1887` (`setHourlyRate`, 422 : le montant et la catégorie hors main-d'œuvre seulement) ; `docs/api/components/parameters.yaml:729-733` (`RateYear` → `Year`) ; `common.yaml:87-90` (`Year` : 2000–2100) ; `common.yaml:709-720` (`FieldProblem.pointer` : « un paramètre de chemin qui n'est pas un identifiant, sous `/path` suivi de son nom, `/path/year` »).
- **spécification** : `WF-REF-0050-A`, `WF-REF-0060-A` ; `WF-ARC-0110-A` (chaque refus a son code).
- **le contrat dit** : le pointeur `/path/year` est l'exemple même que le catalogue donne, et `resolveRowNumber` (`revisions.yaml:1254`, `1423`) décrit le sien ; `setHourlyRate` ne dit pas ce que reçoit `PUT …/hourly-rates/1999` — 404 (chemin inconnu), 422 `/path/year`, ou le 400 d'une requête mal formée. Le `sort_by` de la grille borne la même année par son motif (`^rate\.(20[0-9]{2}|2100)$`).
- **décision** : aucune.
- **proposition** : dans le 422 de `setHourlyRate` : « une année hors de 2000 à 2100, `/path/year` par `VALUE_OUT_OF_RANGE`, `fields[].params.minimum` ou `maximum` la seule borne franchie (`Year`) » ; sans exemple nouveau si l'on juge la forme déjà montrée par `resolveRowNumber`.

#### C-08 — `updateOrgNode` : un déplacement change la profondeur et le parent des descendants, que la réponse ne porte pas
- **gravité** : mineur
- **emplacement** : `docs/api/paths/reference.yaml:291-313` (`updateOrgNode`, description et 200 : « Nœud modifié ; les révisions marquées sont inchangées ») ; `schemas/reference.yaml:99-110` (`OrgNode.parent_label` et `level`, « résolus à la lecture »).
- **spécification** : `WF-REF-0070-A` — « ses descendants et les rôles qui y sont rattachés le suivent, et rien d'autre ne change » ; Vérif : « Le déplacement d'un nœud sous un autre emporte ses descendants et ses rôles ».
- **le contrat dit** : la réponse est le nœud déplacé seul ; `level` de chaque descendant et `parent_label` de ses enfants (si le nœud a aussi été renommé) changent sans qu'aucune réponse les porte. Les opérations voisines le disent (« L'écriture change la disponibilité des commandes d'autres objets […] le client relit les listes », `setOrgNodeActivation` 375–377, `setDefaultCalendar`, `updateCostCategory`) ; celle-ci non, et `org_node_updated` (« il passe du troisième au deuxième niveau ») ne montre que lui.
- **décision** : aucune.
- **proposition** : dans la description d'`updateOrgNode` : « La réponse porte le nœud seul : la profondeur de ses descendants, et le libellé de parent de ses enfants s'il est renommé, changent avec lui, et le client relit l'arbre. »

#### C-09 — Les années de la grille « quels que soient les filtres », sauf `is_active` faux
- **gravité** : mineur
- **emplacement** : `docs/api/paths/reference.yaml:1711-1715` (`getHourlyRateGrid` : « l'état se filtre (`is_active`) […] les années restent celles de toute la grille, quels que soient la page, la recherche, les filtres et le tri ») ; `schemas/reference.yaml` (`HourlyRateGrid.years` : « les années où une catégorie active porte un taux, et où une catégorie active ou désactivée en porte un quand `include_inactive` est vrai ou `is_active` faux. Elles ne dépendent jamais d'`is_active` vrai, de la recherche, des bornes, du tri ni de la page »).
- **spécification** : `WF-REF-0050-A`, `WF-REF-0060-A`, `WF-IHM-0130-A`.
- **le contrat dit** : deux phrases qui ne disent pas la même chose — la description de l'opération range `is_active` parmi les filtres puis dit les années indépendantes des filtres ; le schéma fait dépendre les années d'`is_active` faux (et d'`include_inactive`). C'est le schéma qui a raison, puisqu'une catégorie désactivée peut seule porter une année.
- **la fixture dit** : aucune fixture ne lit la grille avec `include_inactive` ou `is_active` faux (`volume/hourly_rate_grid*` : 150 lignes actives) ; rien ne départage.
- **décision** : `DECISIONS.md:713-718` (US-0250/L1) : « les années restent celles de toute la grille, pour qu'une colonne ne disparaisse pas d'une recherche à l'autre » — tient, pour la recherche.
- **proposition** : dans l'opération : « les années restent celles de toute la grille lue — celles des catégories actives, et des désactivées quand `include_inactive` est vrai ou `is_active` faux —, quels que soient la page, la recherche, les bornes du taux et le tri ».

### Ce qui est juste

- **Attributs et énumérations** : tout attribut des WF-REF-0030 à 0120 et 0160 à 0190 est porté par son schéma, avec `pattern: '\S'` sur chaque code, libellé et code comptable reçus ou lus (C-03 réglé) ; `CostTypeKind` à trois valeurs ; `WeeklyHours` sept jours ; `RoleCapacity` sans date ; six bornes, seize zones, quatre seuils, délai 1–104 ; cinq colonnes lues dans l'ordre fixe d'`ActualCostSourceColumn`, `required` et `is_complete`/`missing_columns` calculés ; `ReferenceReadiness.missing` dans l'ordre de WF-CYC-0120. Les `Percent` des bornes sont des rapports (`0.1` = 10 %), comme la probabilité d'un risque (`risk.json` : `0.4`) et le taux d'inflation (`project.json` : `0.03`) : une seule convention.
- **Refus** : une seule forme pour chaque refus d'état (`org_node_parent_active`, `org_node_active`, `calendar_not_default`, `calendar_active`, `cost_type_active`, `cost_type_unused`/`unrated`/`without_role`, `cost_category_unused`/`unrated`/`without_role`), chaque condition dite d'avance par `available_commands` et nommée par son 409 avec `conflicting_object_id` ou `resource_roles`/`cost_categories` ; `ALREADY_EXISTS` avec `fields[]` et `conflicting_object_id` partout, `_label` pour les nœuds et les rôles (README), sans `fields` pour `setHourlyRate` ; 412 sur chaque écriture versionnée, `setDefaultCalendar` compris ; `FIELD_READ_ONLY` sur le nœud d'un rôle (C-09 réglé) ; `TASK_WITHOUT_WORKING_HOURS` sur `updateCalendar`, `setDefaultCalendar` (`resource_role_ids` vide) et `updateResourceRole`, avec `params.projects` par libellé et code (WF-PLA-0010, WF-ADM-0110) ; bornes `_min`/`_max` refusées par 422 sur `/query/<colonne>_max` avec `params.minimum` du type de la colonne (`3`, `"1000"`, `"100"`) ; `rate_year` exigée avec une borne ; `BOUNDS_NOT_ORDERED`, `THRESHOLD_NOT_BELOW_WATCH`, `THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE`, `DURATION_UNIT_NOT_POSITIVE`, `DUPLICATE_COLUMN_LABEL` avec `duplicate_of` ; `labor`/`LABOUR` assumé (C-08, Vocabulaire 10117–10128).
- **Permissions et lectures** : les six listes déclarent et décrivent le même 403 d'`include_inactive`/`is_active` faux (C-01/J-08 réglés), les trois nouvelles avec leur exemple ; `getReferenceSettings` lisible par toute session, sans 404 (C-02 réglé) ; `updateReferenceSettings` par champ et par fonction, `company_name` sous `cost_settings.write` (US-0600) ; `getActualCostMapping` nomme `cost_settings.read`.
- **Objets uniques** : `ReferenceSettings`, `DurationUnits` et `ActualCostMapping` portent `audit` et `lock_version` (C-06 réglé), les fixtures la plateforme à l'amorçage et Camille Martin aux écritures du jour.
- **Descriptions** : `listHourlyRates` cite WF-DEV-0010 et `getMissingRates`, et dit l'année de référence du projet (C-05 réglé) ; `CostCategoryImage.accounting_code` dit les fichiers de devis et de reste à engager (M-12 réglé) ; `IndexThresholds` dit les bornes des zones avec l'exemple 0,9/0,8 (M-13 réglé) ; `RiskMatrixSettings` dit l'assiette (C-04, schéma) ; `IndexValue.zone` (`indicators.yaml:377-378`) dit la zone recalculée sur les seuils courants (M-14 réglé).
- **Exemples** : les six refus de C-07 ont le leur (`org_nodes_bounds_inverted`, `calendar_default_without_hours`, `cost_type_activation_stale`, `cost_category_activation_stale`, `actual_cost_mapping_permission_missing`, `cost_type_code_taken` cité sous la modification avec un résumé « à sa création comme à sa modification »). **Fixtures cohérentes** avec l'univers témoin : rattachements des cinq rôles vers des nœuds, catégories et calendriers lus (l'automaticien sur la semaine de trente-neuf heures, désactivée, que la liste ne rend pas) ; capacités à l'échelle du portefeuille et `monthly_hours / headcount` = 173,33 ou 169,00 (DECISIONS 2383–2396) ; un seul calendrier par défaut, sa désactivation indisponible, `set_default` listée sur les autres ; cascades de `org_node_deactivated` (le monteur câbleur, `org_node_active` manquante) et de `cost_types_with_inactive`/`volume/cost_categories_type_deactivated` (49 catégories, version 2, `cost_type_active`) ; `cost_types` et `volume/cost_categories` d'accord sur ce qui est employé (ACH-001, ACH-002, PRV-001), taxé (150) et rattaché à un rôle (MO-001, MO-002) ; grille 150 × 15, années croissantes, cellules alignées, aucun taux nul, `hourly_rates` identique à la ligne MO-001, `bounded` 39 lignes toutes ≥ 99,12 en 2026, `by_rate` décroissante de 119,92 à 92,30 ; MO-003 sans taux avant 2016 et 86,98 en 2016, ce que `hourly_rate_entered`, `_corrected`, `_already_entered`, `_stale`, `_amount_refused` et `cost_category_rated_kind_refused` racontent ensemble ; `hourly_rate_added_year` sur 2011, année absente de la grille ; le refus du calendrier du monteur câbleur nomme un seul rôle parce qu'il travaille seul sur les 103 tâches de câblage de la structure engendrée (DECISIONS 5340–5344) ; les zones de `risk_matrix` monotones, la case (p1, g4) passée de `watch` à `alert` dans `_matrix_updated` ; `actual_cost_mapping` versions 2 → 3 → `stale` 3.
- **Listes et volumes** : quatre tables plates et la grille paginées (`Limit` ≤ 500) avec `meta.total`, tri à égalité départagé, chaque colonne filtrée ou bornée (les heures des jours exceptées, WF-IHM-0130) ; l'arbre non paginé, les ancêtres rendus avec les nœuds retenus ; 200 catégories, 150 lignes, 15 ans (§4.6.2).

### Doutes

- **La catégorie porte deux codes exigés et uniques.** `CostCategoryWrite` exige `code` et `accounting_code`, tous deux uniques ; la spécification ne nomme que le code comptable (§3.2.2 : « porte un code comptable et un libellé » ; WF-REF-0040 ; WF-DAT-0090 : « code de nature de coût, code comptable de catégorie de coût » ; annexe B l. 4902 : « une catégorie est désignée par son code comptable »). `DECISIONS.md:3671-3680` (EP-02/L42g) a aligné le code comptable « comme le code » sans décider du code lui-même. La spécification ne le contredit pas, mais un utilisateur doit inventer un second code (MO-001…) qu'aucune exigence ne demande ; rendre `code` facultatif après le gel serait compatible, l'inverse non. À assumer dans DECISIONS ou à trancher.
- **`weekly_hours`, colonne de tri des calendriers, sans filtre.** `listCalendars.sort_by` offre la somme des heures ; WF-IHM-0130 n'excepte du filtre que « les heures de chaque jour ». `DECISIONS.md:3063-3065` (#533) l'a ajoutée « pour une colonne qui la montrerait » sans dire son filtre. Lecture probable : la somme relève de la même exception ; à écrire si on la garde.
- **`RoleCapacity.headcount` en `Decimal`** (doute du 28 octobre maintenu) : la spécification dit « l'effectif », les fixtures des entiers, DECISIONS 2392 tient `monthly_hours / headcount` égal aux heures d'une personne. Un `integer` ne serait plus possible après le gel.
- **WF-REF-0060, Vérif « L'ajout d'une colonne pour une année déjà présente est refusé »** (maintenu) : sans surface d'API, une année existant par son premier taux ; `INVENTORY.md:124-125` compte l'exigence portée par la grille et la liste. À confirmer comme choix assumé.
- **`setHourlyRate` et `listHourlyRates` sur une catégorie désactivée** (maintenu) : ni refus ni 403 dits, quand la grille cache les désactivées sans permission. La réponse dépend de C-01.
- **`risk_settings.read` et `indicator_settings.read`** ne gardent plus rien depuis que `getReferenceSettings` est ouvert à toute session ; WF-ADM-0100 exige leur existence au catalogue, pas leur emploi. Traité dans C-01, à dire dans `PermissionCode` quelle que soit la forme retenue.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| C-01 (aussi J-08) | réglé | `paths/reference.yaml:167-170, 214-223` (`listOrgNodes`), `:859-863, 911-920` (`listCalendars`), `:1198-1201, 1245-1254` (`listCostTypes`) : 403 décrit, `resource_settings.write`/`cost_settings.write` nommées, exemples `*_inactive_forbidden` ; `IncludeInactive` (`parameters.yaml:38-45`) dit la règle. La question laissée « au passage » (qui lit les actifs) redevient C-01 de cette revue. |
| C-02 | réglé | `paths/reference.yaml:32-54` : `getReferenceSettings` « Lus par toute session ouverte, sans permission », plus de 404 ; `Installation` sans devise, écarté par l'auteur (DECISIONS 9522–9526). |
| C-03 | réglé | `schemas/reference.yaml:86-93` (`OrgNode.code`), `:453-456` (`CostType.code`), `:572-575`, `:600-610` (`CostCategoryImage.code`, `accounting_code`), `:633-640` (`CostCategoryWrite.accounting_code`) : `pattern: '\S'` ; les 422 de `createCostCategory` (1536–1546) et `updateCostCategory` (1613–1623) disent « faits seulement de blancs ». |
| C-04 (aussi H-06) | partiellement réglé | Schéma corrigé (`schemas/reference.yaml:858-862`, `risks.yaml:527-532`) ; les résumés de `reference_settings`, `_matrix_updated`, `_bounds_refused` disent encore « du budget de référence » → C-03 de cette revue. |
| C-05 | réglé | `paths/reference.yaml:1793-1797` : « le taux de l'année de référence du projet (WF-DEV-0010, `getMissingRates`) ; une année s'ajoute par son premier taux (`setHourlyRate`, WF-REF-0060) ». |
| C-06 | réglé | `schemas/reference.yaml:775-814` (`ReferenceSettings.audit` requis, décrit), `:925-948` (`DurationUnits.audit`) ; fixtures `reference_settings*`, `duration_units*` avec la plateforme puis Camille Martin. |
| C-07 | réglé | `org_nodes_bounds_inverted` (`:234`), `calendar_default_without_hours` (`:1124`), `cost_type_activation_stale` (`:1431`), `cost_category_activation_stale` (`:1692`), `actual_cost_mapping_permission_missing` (`:1954`), `cost_type_code_taken` cité sous le 409 d'`updateCostType` (`:1365`) avec résumé « à sa création comme à sa modification ». |
| C-08 | sans objet | `DECISIONS.md:10125-10128` (Vocabulaire) : « `labor` et `LABOUR` coexistent (C-08, US-0701/L8) […] Les deux restent » — choix assumé, la spécification ne le contredit pas. |
| C-09 | réglé | `schemas/reference.yaml:271-277` (`ResourceRoleUpdate.org_node_id`, facultatif, `FIELD_READ_ONLY` si différent), `paths/reference.yaml:682-685` (422 d'`updateResourceRole`), `common.yaml` (`FIELD_READ_ONLY` : « un nœud autre que celui d'un rôle de ressource à sa modification »). |
| J-08 | réglé | Même correction que C-01. |
| M-12 | réglé | `schemas/reference.yaml:605-610` : « ni dans l'import des coûts réels, qui ne ventile pas par nature (WF-INTF-0140) ; les fichiers de devis et de reste à engager désignent par lui la catégorie d'une ligne hors main-d'œuvre (WF-REF-0040, annexe B) ». |
| M-13 | réglé | `schemas/reference.yaml:892-905` (`IndexThresholds`) : « Un indice supérieur ou égal au seuil de vigilance est nominal […] à 0,9 et 0,8, un indice de 0,9 est nominal, un indice de 0,8 en vigilance ». |
| M-14 | réglé | `schemas/indicators.yaml:364-378` (`IndexValue.zone`) : « Un indice conservé l'est aussi : sa valeur ne change pas, sa zone peut changer avec les seuils (WF-REF-0130) » ; `:680`. |
| Doutes du 28 octobre (WF-REF-0060, `headcount`, `setHourlyRate` et `listHourlyRates` sur une catégorie désactivée) | maintenus | Aucune décision ni description nouvelle ; repris ci-dessus. |

## Annexe D — Projets : cycle de vie, paramètres, sous-projets, lotissement, contributeurs, chronologies

Périmètre. Lu : `docs/api/README-fr.md` (94 lignes, le tableau « Conventions » entier) ;
`docs/api/paths/projects.yaml` (1 135 lignes, les 19 opérations, ligne à ligne) ;
`docs/api/components/schemas/projects.yaml` (1 127 lignes, entier) ; `components/common.yaml`
(`Problem` 141–386, `StateEnumeration` 386, `ErrorCode` 394–707, `ProblemParams` 730–829,
`ProblemProject` 839, `ProblemSubproject` 891, `Percent`, `LockVersion`, `Audit`, `ActorRef`,
`BackgroundTaskRef` 931) ; `components/parameters.yaml` (`Limit`, `Offset`, `Search`, `SortOrder`,
`ProjectId`, `SubprojectId`, `TimelineId`, `PortfolioStates` 789–803) ; `components/responses.yaml`
(entier, 140 lignes) ; `schemas/revisions.yaml` (`Timeline`, `TimelineCreate` 1761–1776, le 409 de
`createRevision` 82–104 de `paths/revisions.yaml`) ; `paths/costs.yaml:140-150` et
`paths/exchanges.yaml:298-317` pour les conditions que le projet dit d'avance ;
`schemas/reference.yaml` (`ReferenceReadiness` 1095–1122) ; `INVENTORY.md` 130–154.
**88 fixtures ouvertes**, toutes celles que `paths/projects.yaml` référence, plus `revisions.json`
(chronologie des révisions 100, 101, 102) pour l'univers témoin. Spécification 1.0.1 : §3.2.3
(682–752), §3.3.1 (WF-CYC-0120, 886–900), §3.3.2 (902–1069, les dix exigences WF-CYC), §3.4.3 et
§3.4.3.1 (1440–1512), §3.4.5.2 entier (2032–2197, WF-PRJ-0010 à 0090), WF-PLA-0130, WF-PLA-0170,
WF-PLA-0060, WF-PLA-0140 (2316–2378), WF-REV-0010/0020/0030/0040 (1910–1962), WF-CRE-0020/0030
(2825–2853), WF-IND-0010 (2922–2936), WF-ADM-0060, WF-ADM-0100, WF-ADM-0110 (1204–1356),
§3.6 WF-IHM-0060 à 0130 (3242–3345), WF-ARC-0090 (3821–3835), §4.4.1 entier (3849–3980),
WF-DAT-0020 (4004–4020). Décisions : « L'univers témoin » (1777–1870), US-0540 (7728, par grep),
US-0610 (7961–8009), EP-15/US-0490/L4 (7274–7292), US-0701/L9 (9551–9649), US-0702/L1 (9649–9777),
US-0702/L2 (9777–9869), US-0702/L3 (9869–9911), US-0660/L2 (10026–10076). Revue du 2026-10-28 :
Annexe D (1280–1670) et L-02, L-03, L-17 (3358–3369, 3448–3453).

### Synthèse

La famille est celle que la revue du 28 octobre avait le plus chargée (un bloquant, six majeurs),
et c'est celle où le travail de US-0701/L9 et US-0702/L1 à L3 a le plus porté : les treize
constats D et les trois constats L qui la croisaient sont **tous réglés**, à la ligne — la sortie
reçoit le sort de la révision en cours en deux variantes typées, rend 200 ou 202 et porte son
compteur ; `lose` n'est plus listée dès En cours et un projet clos ne liste plus rien ; le
non-contributeur qui porte le paramétrage et « consulter tous les projets » inscrit un chef de
projet, et trois exemples le montrent ; `ProjectCode` est borné par en bas et sans barre oblique ;
le projet terminal est un 409 `project_not_terminal` sur les dix-neuf opérations ; le 404 manquant,
le `\S` de la chronologie, le code mort du catalogue ont disparu. Les 88 fixtures racontent un
seul univers, dont la chronologie tient (offre 100 marquée le 15 décembre, désignée le 15 janvier,
avenant 101 marqué le 1er février et devenu référence, 102 ouverte le 2 février), et les
compteurs, les états et les commandes se répondent d'un exemple à l'autre. Ce qui reste est de
second ordre : une description partagée (`PortfolioStates`) qui dit le contraire de ce que
`listProjects` en fait ; des refus déclarés sans exemple ; une condition dont la description omet
deux des commandes qui la nomment ; trois points que les décisions ont laissés ouverts (un sort
envoyé sans révision en cours, `code: null` en cours, la sortie différée et le compteur). Rien ne
contredit la spécification 1.0.1.

**11 constats : 0 bloquant, 1 majeur, 10 mineurs. Suivi des 16 constats du 2026-10-28 (D-01 à
D-13, L-02, L-03, L-17) : 16 réglés, 0 partiel, 0 non réglé, 0 sans objet ; des six « Doutes » de
l'annexe D du 28 octobre, un est réglé (le compteur de la sortie), un redevient constat (`code:
null`), quatre restent des doutes.**

### Constats

#### D-01 — `PortfolioStates` dit qu'un projet créé, perdu ou abandonné nommé dans `states` est « sans effet », et `listProjects` s'en sert pour l'accueil qui les liste
- **gravité** : majeur
- **emplacement** : `docs/api/components/parameters.yaml:789-803` (`PortfolioStates`) ;
  `docs/api/paths/projects.yaml:27` (`listProjects` le référence), `:18-22` (« un accueil qui
  liste tous les projets ouvrables nomme les six états. `meta.states` dit toujours les états
  retenus ») ; `docs/api/paths/portfolio.yaml:18,87,118,169,203,238,275,324` (les huit vues du
  portefeuille, où la description est juste) ; fixtures `fixtures/api/projects.json`,
  `projects_empty.json`, `projects_search_code.json`, `projects_period.json` (`meta.states` à six
  valeurs, dont `created`, `lost`, `abandoned`).
- **spécification** : `WF-IHM-0120-A` — « À la connexion, l'utilisateur voit la liste des projets
  dont il est contributeur. Ce filtre est visible et peut être levé pour voir les projets que ses
  habilitations lui permettent d'ouvrir » ; `WF-PRJ-0060-A`, Vérif — « La liste d'un projet
  nouvellement créé comporte son créateur, chef de projet » (le projet créé est à l'état Créé,
  `project_created.json`) ; `WF-PTF-0010-A` ne vaut que pour « toute vue du portefeuille ».
- **le contrat dit** : le paramètre partagé — « Une vue du portefeuille ne retient que les projets
  en cours, ceux en chiffrage qu'elle ajoute et les projets terminés de la période : un projet
  créé, perdu ou abandonné que `states` nomme y est sans effet, comme tout état que la vue dit
  ne pas compter (WF-PTF-0010). À une date passée (`as_of`)… » ; `listProjects` n'a pas d'`as_of`
  et dit l'inverse : les six états nommés retiennent les six états.
- **la fixture dit** : `projects.json`, « Lus comme l'accueil les demande, les six états nommés,
  que `meta.states` rend » — aucun exemple ne montre pourtant un projet `created`, `lost` ou
  `abandoned` retenu par la liste (le projet créé aujourd'hui, `project_created.json`, n'y figure
  dans aucune lecture).
- **décision** : aucune sur ce point ; la décision de partager le paramètre (`listProjects`,
  « le défaut du périmètre du portefeuille (WF-PTF-0010) que le paramètre partage ») ne dit rien de
  la phrase « sans effet ». Tient pour le défaut (en cours seuls), pas pour la portée.
- **proposition** : soit un paramètre propre à la liste, `ProjectStates` (`name: states`, même
  schéma, « États retenus ; absents, les projets en cours seuls, le défaut du portefeuille
  (WF-PTF-0010) ; tout état nommé est retenu — l'accueil nomme les six »), référencé par
  `listProjects` seul ; soit, dans `PortfolioStates`, ôter « un projet créé, perdu ou abandonné que
  `states` nomme y est sans effet » et renvoyer la règle à chaque vue du portefeuille, qui la dit
  déjà. Ajouter à `listProjects` un exemple qui retient le projet créé aujourd'hui sous les six
  états (`projects_with_created`), pour que le front voie qu'un projet Créé s'y lit. À trancher
  entre les deux formes ; la première est la plus sûre pour le client engendré, dont la
  documentation du paramètre est celle du composant partagé.

#### D-02 — Le refus `project_not_terminal` est déclaré sans exemple sur six écritures du projet ; d'autres refus déclarés n'en ont pas non plus
- **gravité** : mineur
- **emplacement** : `docs/api/paths/projects.yaml:227-242` (`updateProject` 409 : exemples
  `code_taken`, `win_probability_frozen` seulement), `:545-560` (`setWorkBreakdown` 409 :
  `background_task` seul), `:678-689` (`createSubproject` 409 : `code_taken` seul), `:737-748`
  (`updateSubproject` 409 : `code_taken` seul), `:806-836` (`deleteSubproject` 409 : `cited`,
  `refused`, `estimated` — aucun `project_not_terminal`), `:972-981` (`setContributors` 409 :
  `without_manager` seul) ; `:132-147` et `:244-259` (422 de `createProject` et `updateProject` :
  aucun exemple de `/code` blanc par `VALIDATION_FAILED`, de `/client` vide ou trop long, de
  `/label` trop long) ; `:690-706` et `:750-765` (422 des sous-projets : aucun exemple du code trop
  long, `VALUE_TOO_LONG` avec `max_length` à `31`).
- **spécification** : `WF-CYC-0100-A` — « Toute modification d'un projet terminal est refusée » ;
  méthode de la revue (brief, point 4 : « un refus déclaré sans exemple »).
- **le contrat dit** : chacune de ces six descriptions nomme `project_not_terminal` ; seuls
  `exitProject` (`project_exit_terminal`), `createTimeline` (`timeline_create_terminal`) et
  `deleteTimeline` (`timeline_delete_terminal`) l'exemplifient dans la famille.
- **décision** : `DECISIONS.md:9869-9893` (US-0702/L3) — « Un appel direct reste refusé par la
  règle unique : 409 … (`timeline_create_terminal`, `timeline_delete_terminal`,
  `project_exit_terminal`, `actual_cost_scope_terminal`) » : quatre exemples décidés, aucun pour
  les six écritures ci-dessus. Tient ; le manque est d'exemples, pas de règle.
- **proposition** : engendrer (`wftools.mockrefusals`) un exemple par opération, la suite du
  projet terminé aujourd'hui (`project_completed`) : `project_update_terminal`,
  `work_breakdown_terminal`, `subproject_create_terminal`, `subproject_update_terminal`,
  `subproject_delete_terminal` — ce dernier précieux, parce que l'ordre décidé y met
  `project_not_terminal` en dernier, après les conditions du sous-projet, et que
  `subprojects_completed` le dit sans qu'aucun refus le montre —, `contributors_set_terminal`. Et
  un `project_code_blank` (« /  » → `PROJECT_CODE_INVALID`, la barre oblique d'abord, D-07 de
  US-0701/L9 ; «   » → `VALIDATION_FAILED`), un `subproject_code_too_long` (`max_length: 31`).

#### D-03 — `project_creation_refused` rend `/code` trop long sans `params.max_length`, que `ProjectCode` promet
- **gravité** : mineur
- **emplacement** : `fixtures/api/project_creation_refused.json:12-14` (`{"pointer": "/code",
  "code": "VALUE_TOO_LONG"}`, sans `params`) ; `docs/api/components/schemas/projects.yaml:557-558`
  (`ProjectCode` : « trop long, par `VALUE_TOO_LONG`, `fields[].params.max_length` à `50` ») ;
  `docs/api/paths/projects.yaml:137-139` et `:250-251` (les 422 de `createProject` et
  `updateProject` ne nomment pas `max_length` pour `/code`, quand `createSubproject:693` le nomme
  pour le sien) ; `docs/api/components/common.yaml` (`Problem.params`, « `max_length`, dans
  `fields[].params`, le plus grand nombre de caractères qu'admet le code d'un sous-projet trop
  long (`VALUE_TOO_LONG`, `31`, WF-PRJ-0050) » — rien pour le code projet).
- **spécification** : `WF-PRJ-0010-A` (le code projet) ; convention README (« Une seule enveloppe
  d'erreur, portant un code machine et ses paramètres »).
- **le contrat dit** : trois choses différentes — le schéma promet le paramètre, les opérations ne
  le nomment pas, l'enveloppe commune ne le connaît que pour le sous-projet.
- **la fixture dit** : un `VALUE_TOO_LONG` nu, qui contredit le schéma qu'elle illustre.
- **décision** : `DECISIONS.md:9629-9638` (US-0701/L9, « Le code projet borné ») — dit `VALUE_REQUIRED`,
  `VALIDATION_FAILED`, `PROJECT_CODE_INVALID`, et rien du `max_length`. Aucune ne tranche.
- **proposition** : une seule règle, et l'écrire aux trois endroits : `fields[].params.max_length`
  à `50` sur `/code` (comme `31` sur le code d'un sous-projet, que le formulaire dit au champ) —
  l'ajouter à la fixture (écrite à la main), aux 422 de `createProject` et `updateProject`, et à
  `Problem.params` ; ou retirer la promesse de `ProjectCode`. La première forme est celle du
  sous-projet.

#### D-04 — La description de `project_in_progress` omet `import_actual_costs` et `exclude_cost_lines`, que cinq fixtures et `costs.yaml` lui font nommer
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/projects.yaml:129-131` (`CommandCondition` :
  « `project_in_progress` manque hors de l'état En cours à ce qui ne se fait qu'en réalisation :
  la sortie vers Terminé (`complete`, WF-CYC-0060), la saisie du reste à engager (plus bas) ») ;
  `:476-480` (`ProjectCommand` : « `import_actual_costs` nomme `actual_cost_mapping_complete` …
  après les conditions de l'état du projet (WF-REF-0190) —, exclure une ligne du périmètre suivi
  (WF-CRE-0030) » — les conditions d'état ne sont pas nommées) ; fixtures `project_pricing.json`,
  `project_created.json`, `project_revision_opened.json`, `projects.json`, `projects_search_code.json`,
  `projects_period.json` (`import_actual_costs` et `exclude_cost_lines` indisponibles,
  `project_in_progress`) ; `docs/api/paths/costs.yaml:144-148` (le 409 de `setActualCostTrackedScope`
  nomme `project_not_terminal` puis `project_in_progress`).
- **spécification** : §3.2.3 — « avant la commande, il n'y a aucun coût réel à rapprocher » ;
  `WF-PRJ-0010-A`, motif — « sans lui, aucun coût réel ne peut être imputé au projet ».
- **le contrat dit** : la condition est nommée par les exemples et par une opération d'une autre
  famille ; la description de la condition, qui prétend énumérer ce qui la nomme, ne la rattache
  qu'à `complete` et à `edit_remaining`.
- **décision** : `DECISIONS.md:9693-9696` (US-0702/L1 : « `project_in_progress` … employés et
  désormais décrits »). Tient ; la description est incomplète.
- **proposition** : dans `CommandCondition`, après « la saisie du reste à engager (plus bas) » :
  « , l'import des coûts réels et l'exclusion d'une ligne du périmètre suivi
  (`ProjectCommand.import_actual_costs`, `exclude_cost_lines` ; WF-CRE-0020, WF-CRE-0030), que
  `setActualCostTrackedScope` nomme dans son 409 après `project_not_terminal` » ; dans
  `ProjectCommand`, nommer `project_in_progress` comme « les conditions de l'état du projet » de
  ces deux commandes. Voir aussi les Doutes : `openImport` (famille I) ne déclare pas ce refus pour
  un import de coûts réels avant En cours.

#### D-05 — Un sort de révision envoyé à un projet sans révision en cours : ignoré ou refusé ?
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/projects.yaml:690-697` (`ProjectExit.current_revision` :
  « Absent ou nul quand le projet n'en porte pas (D-01, US-0701/L9) ») ;
  `docs/api/paths/projects.yaml:424-439` (le 422 d'`exitProject` ne nomme que l'absence du sort
  et l'absence du nom de version).
- **spécification** : `WF-CYC-0090-A` — « Lorsque le projet porte une révision en cours, la
  confirmation demande de la marquer … ou de l'abandonner » ; rien sur un projet qui n'en porte pas.
- **le contrat dit** : ce que le client doit envoyer, pas ce que le serveur fait d'un sort envoyé
  à tort — `CurrentRevisionMark` emporte un nom de version qui n'a rien à nommer. Un service
  l'ignorera, un autre le refusera par `FIELD_NOT_ACCEPTED` ; le front ne saura pas lequel.
- **décision** : `DECISIONS.md:9591-9593` (US-0701/L9) — « Restent à US-0702 : … les codes des
  autres refus d'`exitProject` (D-03), dont un sort envoyé à un projet sans révision en cours, que
  ni la spécification ni la revue ne disent » ; US-0702/L2 (`:9798-9807`) a traité D-03 sans ce
  point. Ouvert.
- **proposition** : à trancher. La forme la plus proche du contrat : 422 `VALIDATION_FAILED`,
  `fields` désignant `/current_revision` par `FIELD_NOT_ACCEPTED` (« un champ que le nœud
  n'accepte pas », déjà au catalogue pour une valeur sans objet), rien n'étant écrit — un sort
  envoyé trahit un écran lu avant l'abandon de la révision, et le refus vaut mieux que le silence.
  L'autre forme, l'ignorer, est à écrire aussi si elle est retenue.

#### D-06 — `code: null` sur un projet En cours : le contrat ne dit toujours pas s'il efface le code
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/projects.yaml:600-601` (`ProjectUpdate.code:
  anyOf: [ProjectCode, null]`, sans description) ; `docs/api/paths/projects.yaml:183-195`
  (`updateProject` : le client « s'y saisit et s'y efface à tout moment », rien du code) ;
  `:244-252` (422 : « `/code` refusé comme à la création »).
- **spécification** : `WF-PRJ-0010-A` — « Il peut être renseigné à tout moment, et il est exigé
  pour le passage du projet à l'état En cours » ; `WF-CRE-0020-A` — « Le projet et le sous-projet
  d'une ligne de coût sont déduits de son élément d'OTP, qui porte le code projet » ;
  `WF-DAT-0060-A` — « un code se corrige », Vérif : « La modification du code d'un projet …
  n'affecte aucune ligne qui les référence ».
- **le contrat dit** : le schéma admet `null` à tout état ; effacer n'est pas corriger, et un
  projet En cours sans code ne reçoit plus aucune ligne de coût (WF-CRE-0020 rejette toute ligne
  « d'un autre projet »).
- **décision** : `DECISIONS.md:9637-9638` (US-0701/L9) — « Le doute de la revue sur `code: null`
  d'un projet en cours n'est pas tranché ici. » Ouvert depuis le 28 octobre.
- **proposition** : à trancher. Proposition : « `null` efface le code tant que le projet n'a pas
  atteint En cours ; dès En cours, où le code a été exigé (WF-PRJ-0010) et impute les coûts réels
  (WF-CRE-0020), il se corrige mais ne s'efface plus : `null` est refusé par 409
  `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `project_before_in_progress` », la
  condition qui existe déjà pour la probabilité de gain ; l'écrire dans `ProjectUpdate.code` et
  dans le 409 d'`updateProject`, avec un exemple. L'autre lecture — l'effacement admis, le projet
  restant En cours sans code — est à écrire si elle est retenue.

#### D-07 — La sortie différée par un marquage : le compteur du projet n'est pas dit pendant ni après
- **gravité** : mineur
- **emplacement** : `docs/api/paths/projects.yaml:336-345` (`exitProject` : « La sortie s'applique
  quand la tâche réussit … le projet passe à l'état visé ») et `:347-349` (« elle porte son
  compteur lu (`ProjectExit.lock_version`) : deux chefs de projet qui sortent le même projet ne
  sortent pas l'un sur l'autre ») ; `docs/api/components/schemas/projects.yaml:698-702`
  (`ProjectExit.lock_version` : « périmé, la sortie est refusée par 412 ») ; fixtures
  `project_background_task_running.json` (`update`, `manage_contributors`, `manage_timelines`
  restent disponibles pendant le marquage), `task_exit_mark_queued.json` (« le projet reste en
  cours, sa révision en cours avec lui »), `project_completed.json` (`lock_version: 8` après une
  sortie qui abandonne, envoyée avec `7`).
- **spécification** : `WF-IHM-0110-A` (le compteur rend l'écriture sûre à plusieurs
  contributeurs) ; `WF-CYC-0090-A` (« la sortie n'est appliquée qu'avec ce choix, dans la même
  opération »).
- **le contrat dit** : le compteur est vérifié à la requête (412) ; pendant le marquage, `update`
  reste disponible et peut avancer le compteur ; rien ne dit si l'application différée revérifie
  le compteur (et que fait-elle sinon : échec de la tâche, `problem` à `STALE_LOCK_VERSION` ?) ni
  que le compteur avance à l'application, comme il avance (7 → 8) à une sortie synchrone.
- **décision** : `DECISIONS.md:9563-9579` (US-0701/L9) décide le 202 et « la sortie s'appliquant
  quand la tâche réussit, rien quand elle échoue » ; `:9784-9796` (US-0702/L2) décide le compteur
  dans le corps. Aucune ne dit le cas d'une écriture du projet entre la requête et l'application.
- **proposition** : écrire dans `exitProject` : « Le compteur est vérifié à la requête ; la sortie
  différée s'applique sans le revérifier, le marquage n'écrivant pas le projet et ses écritures
  restantes (`update`, `manage_contributors`, `manage_timelines`) ne touchant pas à ce que la
  sortie fige ; elle fait avancer le compteur du projet comme une sortie dans la requête. » Ou
  l'inverse — la tâche échoue par `STALE_LOCK_VERSION` dans `problem` — ; à trancher, la première
  forme étant la plus simple et la seule que les exemples laissent lire.

#### D-08 — `listProjects` déclare un 404 sur une collection sans objet à ne pas trouver
- **gravité** : mineur
- **emplacement** : `docs/api/paths/projects.yaml:77` (`'404': { $ref: …/NotFound }` sous
  `GET /projects`) ; contre `listUsers` (`paths/access.yaml:3-…`), `listAccessRoles`
  (`access.yaml:743-…`), `listBackups` (`platform.yaml:3-…`), sans 404 ; `listRisks`, `listImports`,
  `listOrgNodes` en ont un parce que leur chemin porte un identifiant ou un filtre d'objet.
- **spécification** : convention README — « 404 lorsque la permission de consultation manque »
  (WF-ADM-0110) : la permission de consulter les projets manquante sur `/projects` est un 403
  (`PERMISSION_MISSING`) ou une liste vide, jamais un objet introuvable.
- **le contrat dit** : un 404 que rien ne peut produire, que le client engendré type et que le
  front devra traiter.
- **décision** : aucune.
- **proposition** : retirer le `'404'` de `listProjects` ; si un 403 est voulu pour l'appelant sans
  la permission de consulter les projets, le déclarer (`Forbidden`), comme `listOrgNodes` déclare
  le sien (US-0702/L2, C-01).

#### D-09 — Un compte inscrit deux fois dans une liste de contributeurs : aucun refus dit
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/projects.yaml:1068-1084` (`ContributorsWrite` :
  `contributors`, `minItems: 1`, items `ContributorWrite` `{user_id, kind}`, sans `uniqueItems`
  — qui ne porterait d'ailleurs que sur le couple) ; `docs/api/paths/projects.yaml:983-998`
  (422 : `UNKNOWN_USER`, `USER_INACTIVE`, `/lock_version`).
- **spécification** : `WF-PRJ-0060-A` — « chacun avec sa qualité : chef de projet ou participant »
  — une qualité par contributeur.
- **le contrat dit** : rien d'un même `user_id` envoyé chef de projet à une ligne et participant
  à une autre ; le service choisira (la dernière ligne ? la première ? un refus ?), et le front ne
  saura pas rendre ce qu'il reçoit.
- **décision** : `DECISIONS.md:9823-9827` (US-0702/L2) a réglé le cas voisin des prédécesseurs
  (`DUPLICATE_PREDECESSOR`, « chaque occurrence après la première ») et du lotissement
  (`DUPLICATE_WORK_BREAKDOWN_ITEM`) ; rien pour les contributeurs.
- **proposition** : à trancher sur le code : 422 `VALIDATION_FAILED`, `fields` désignant
  `/contributors/<n>/user_id` de chaque occurrence après la première — par un motif nouveau
  `DUPLICATE_CONTRIBUTOR`, dans la forme des deux précédents, ou par `ALREADY_EXISTS` en motif de
  champ (l'unicité d'un objet, que les deux précédents ont écartée). L'écrire dans
  `setContributors` et `ContributorsWrite`, avec un exemple.

#### D-10 — `updateSubproject` dit recoder « à tout moment, coûts réels imputés ou non » sans dire le sort des lignes imputées par l'ancien code
- **gravité** : mineur
- **emplacement** : `docs/api/paths/projects.yaml:710-718` (`updateSubproject` : « son code et son
  libellé, à tout moment, coûts réels imputés ou non ») ; `docs/api/components/schemas/projects.yaml:998-1008`
  (`SubprojectUpdate`, qui exige `code` et `label` — un `PATCH` à champs tous exigés, quand
  `ProjectUpdate` les rend facultatifs) ; `:948-955` (`DeclaredSubprojectCode` : « Le code lu dans
  l'élément d'OTP d'une ligne de coût réel (`ActualCostLine.subproject_code`) n'est pas celui-ci »).
- **spécification** : `WF-CRE-0020-A` — « La création d'un sous-projet portant ce code lui impute
  aussitôt les lignes qui l'attendaient, et la mise à jour d'une ligne par un réimport
  (WF-INTF-0140) recalcule son imputation » ; `WF-DAT-0060-A` — « un code se corrige, une clé
  non », Vérif : « La modification du code d'un projet … n'affecte aucune ligne qui les
  référence ».
- **le contrat dit** : le recodage est permis ; `createSubproject` dit que la création impute les
  lignes au code ; rien ne dit qu'un recodage garde les lignes imputées (référence par
  identifiant, WF-DAT-0060) et n'en capte pas d'autres avant un réimport — ni que les lignes
  imputées au seul projet sous l'ancien code, s'il y en a, ne suivent pas. Deux implémentations
  divergeraient : l'une réimpute par le code, l'autre par l'identifiant.
- **décision** : `DECISIONS.md:7961-8009` (US-0610) borne le code et ne traite pas le recodage.
- **proposition** : écrire dans `updateSubproject` : « Un recodage ne change l'imputation
  d'aucune ligne : les lignes imputées au sous-projet le restent (WF-DAT-0060), celles qui
  attendaient l'ancien code ou le nouveau ne bougent qu'à leur réimport (WF-CRE-0020,
  WF-INTF-0140) » — ou la règle inverse, si l'auteur la veut ; à trancher. Le `PATCH` à champs
  exigés est un choix à confirmer avant le gel (le passer facultatif ensuite serait compatible, le
  rendre exigé ne le serait pas : il l'est déjà, donc sans risque).

#### D-11 — Les champs toujours rendus de `Project` ne sont pas exigés par le schéma de lecture
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/projects.yaml:12-21` (`Project.required` :
  `project_id`, `label`, `state`, `inflation_rate`, `win_probability`, `available_commands`,
  `audit`, `lock_version`) ; `:25-60` (`description`, `client`, `code`, `order_received_on`,
  `reference_revision_id`, `current_revision_id`, nullables et facultatifs) ; `:690-697`
  (`ProjectExit.current_revision`, « exigé quand le projet en porte une
  (`Project.current_revision_id`) ») ; les 27 fixtures de `Project` rendent les six champs,
  toujours ; `:1035-1040` (`Contributor.is_active`, « Toujours rendu : l'écran ne devine rien
  d'une valeur absente »).
- **spécification** : `WF-PRJ-0080-A` — les attributs du projet ; `WF-CYC-0090-A` — le sort de la
  révision en cours, que le front ne peut poser que s'il lit `current_revision_id`.
- **le contrat dit** : `code?: string | null`, `current_revision_id?: string | null` dans le
  client engendré — trois états (absent, nul, valeur) pour deux sens ; le front doit traiter
  l'absence, que le serveur ne produit jamais.
- **décision** : `DECISIONS.md:7974` (US-0610) — « Il n'est pas exigé dans la lecture, comme
  la description et le code du projet » : la décision assume le choix ; la spécification ne le
  contredit pas. Signalé pour la seule cohérence du contrat (`Contributor.is_active`,
  `WorkPackageReading.attached_task` et `StateTransition.reason` sont exigés et nullables pour la
  même raison) : rendre exigés six champs toujours rendus est compatible pour tout client, et ne
  l'est plus après le gel pour le serveur. À confirmer ou à faire maintenant.
- **proposition** : ajouter `description`, `client`, `code`, `order_received_on`,
  `reference_revision_id`, `current_revision_id` au `required` de `Project` (nullables
  inchangés) ; `ProjectCreate` et `ProjectUpdate` restent tels quels.

### Ce qui est juste

- **Cycle de vie.** `ProjectState` porte les six codes du tableau 6 et aucun autre ;
  `LifecycleTrigger` les deux faits de la figure 8 ; `NextState` et ses cinq exemples (Créé →
  `first_revision_created` sans condition ; Chiffrage avec code → `reference_revision_designated`
  seule ; Chiffrage sans code, référence désignée → `project_code_set` seule, la Vérif de
  WF-PRJ-0010 ; En cours et Terminé → nuls, sans condition) ; `StateTransition` (`from_state` nul
  à la création, `actor`, `reason` nul hors sortie manuelle) et ses deux fixtures (le témoin ;
  l'offre perdue le 15 mars avec son motif, la Vérif de WF-CYC-0130).
- **La sortie** (D-01, D-03, L-02 réglés) : `ProjectExit` porte `to_state`, `confirmed` laissé à la
  garde (400 `CONFIRMATION_REQUIRED`, `project_exit_unconfirmed`), `reason`, `current_revision`
  en `oneOf` discriminé (`CurrentRevisionMark` exige `version_name` borné `\S`/100 comme
  `markRevision` ; `CurrentRevisionAbandon` sans rien), `lock_version` (412 `project_exit_stale`,
  `expected_lock_version: 7`) ; 200 `Project` pour l'abandon ou sans révision en cours
  (`project_exit_abandoning` → `project_completed`, 102 abandonnée, compteur 7 → 8, `updated_at`
  14 h 05), 202 `BackgroundTaskRef` `revision_mark` pour le marquage (`project_exit_marking` →
  `task_exit_mark_queued`, tâche 955 en file à 14 h 05 min 30 s) ; 409 dans l'ordre de la
  commande — `project_not_terminal` (`project_exit_terminal`), `project_in_progress`,
  `project_in_pricing` (`project_exit_lost_in_progress`), `no_background_task_running` —, puis
  `ALREADY_EXISTS` sur `/current_revision/version_name` (`project_exit_version_name_taken`, la 101
  « Référence ») ; 422 `/current_revision` et `/current_revision/version_name` par `VALUE_REQUIRED`
  (`project_exit_revision_required`, `project_exit_version_name_required`). Les trois exemples
  disent mot pour mot la Vérif de WF-CYC-0090.
- **Les commandes** (D-02, L-03 réglés) : `ProjectCommand` dit la règle de présence des sorties ;
  `lose` est disponible à Chiffrage (`project_pricing`, `project_revision_opened`), indisponible à
  Créé (`project_created`, `project_in_pricing`), absente des sept lectures En cours ; `complete`
  indisponible avant En cours (`project_in_progress`, la Vérif de WF-IHM-0090) ; un projet clos ne
  liste rien (`project_completed`, `subprojects_completed`, US-0702/L3), et le README le dit. La
  qualité vient avant l'état (`project_participant` : `is_project_manager` puis
  `project_before_in_progress` ; `project_rescue` : `is_contributor` puis `is_project_manager`) ;
  `project_reader` est vide ; `project_pricing_estimator` ne liste que l'import qu'une permission
  lui donne, `may_create_revision` manquante ; `project_background_task_running` nomme
  `no_background_task_running` aux seules commandes que le marquage rend caduques, l'import des
  coûts réels restant disponible. L'ordre des fixtures est celui de l'énumération.
- **Les paramètres.** `Project` porte chaque attribut de WF-PRJ-0080 (le client depuis US-0610,
  « Papeteries de la Vienne » dans les treize lectures de PRJ-001, nul pour PRJ-002 et le projet
  créé) ; `inflation_rate` et `win_probability` en rapports `0`–`1` avec `minimum`/`maximum`
  (`project_rates_out_of_range`) ; la probabilité figée dès En cours par 409
  `project_before_in_progress`, que la description d'`updateProject` dit désormais (D-04 réglé,
  `project_win_probability_frozen`) ; `ProjectCode` (D-07 réglé) de 1 à 50, `\S`, sans barre
  oblique, `PROJECT_CODE_INVALID` avec `forbidden_characters: ["/"]` (`project_code_invalid`,
  « PRJ-003/A ») ; `ALREADY_EXISTS` sur `/code` avec `conflicting_object_id` et
  `conflicting_object_label` (`project_code_taken`) ; `REFERENCE_INCOMPLETE` avec
  `missing_prerequisites` dans l'ordre de `ReferenceReadiness.missing`, les quatre prérequis de
  WF-CYC-0120 énumérés, les deux exemples de sa Vérif (`project_reference_incomplete`,
  `project_reference_without_provision`) ; le 403 d'`updateProject` nomme la qualité
  (`project_update_not_manager`, `project_update_not_contributor`).
- **La liste.** `listProjects` : `is_contributor` (WF-IHM-0120), `search` sur libellé et code
  (`projects_search_code`), période `from`/`to` sur `audit.updated_at` début inclus fin exclue
  (`projects_period`, les jours de Paris en instants) et son 422 (`projects_period_inverted`,
  `/query/to`, `minimum` le début donné) ; sans `states`, les projets en cours seuls et
  `meta.states` à `["in_progress"]` (`projects_default_states`) ; tri par défaut `updated_at`
  décroissant, que `projects.json` respecte (16 mars avant 2 février).
- **Lotissement** (D-09, D-11 réglés) : lot → poste → livrable, `WorkBreakdownKind` dans l'ordre du
  §4.4.1 ; `minItems: 1` et 422 `/work_packages` ; le défaut suit le libellé du projet
  (`work_breakdown_default`, 714/715, compteur 0) ; `is_match` et le compte des retenus
  (`work_breakdown_order_items` : un poste, aucun lot, #574) ; compteur nul des lectures filtrées
  (`work_breakdown_search`) ; `attached_task` (la 551 « Poste de commande » porte « Lot 1 », le
  poste 1.1 n'est porté par rien) ; la saisie entière, les identifiants engendrés (716, 717), le
  compteur 1 → 2 (`work_breakdown_entered` → `work_breakdown_saved`) et son 412
  (`work_breakdown_stale`, `expected_lock_version: 2`) ; `UNKNOWN_`/`DUPLICATE_WORK_BREAKDOWN_ITEM`
  aux bons pointeurs ; le déplacement d'un poste sous un autre lot qui retire le rattachement sans
  refus (WF-PLA-0170, dernière phrase) ; 409 `project_not_terminal` puis
  `no_background_task_running` (`work_breakdown_background_task`, et la commande le dit d'avance
  depuis US-0660/L2).
- **Sous-projets** (D-08, D-10 réglés) : « des lignes de devis … jamais une tâche » ; le 404 ;
  `DeclaredSubprojectCode` (31, les sept caractères, « Synthèse »/« Hors sous-projet » sans égard
  à la casse — `subproject_code_invalid` « SP/01 », `subproject_code_reserved` « synthèse » →
  `reserved_name: "Synthèse"`, les codes de la Vérif de WF-PRJ-0050) ; `ALREADY_EXISTS` avec le
  libellé ; les trois conditions de `delete` dans l'ordre décidé puis `project_not_terminal`
  (`subprojects`, `subproject_delete_cited`, `subproject_delete_refused`,
  `subproject_delete_estimated` avec `params.estimate_lines` typés, lignes 10 et 11 de la
  structure principale) ; `has_actual_costs` vrai dès la création quand des lignes attendaient le
  code (`subproject_created`, la facture FA-2026-0295, WF-CRE-0020) ; `lock_version` en paramètre
  de la suppression, 412 (`subproject_delete_stale`) et 422 `LockVersionInvalid` ; le risque dont
  la provision désignait le sous-projet supprimé (`Risk.provision_subproject_id` à nul, #732).
- **Contributeurs** (D-06, L-17 réglés) : `LAST_PROJECT_MANAGER` sans paramètre ; `UNKNOWN_USER`/
  `USER_INACTIVE` à la ligne (`contributors_accounts_refused`) ; compteur propre à la liste, nul
  en lecture filtrée (`contributors_search`, `contributors_inactive`), inchangé par
  l'anonymisation (`contributors_anonymized`, `display_name` nul rangé après les noms, #870) ; le
  tri par défaut (chefs de projet, puis nom de famille : Martin ; Moreau, Petit, Roux) ; le sauvetage
  en trois exemples cohérents (`contributors_without_active_manager` : Camille Martin désactivée
  reste cheffe de projet, compteur 4 ; `contributors_set_by_rescuer` : Inès Roux cheffe de projet,
  compteur 5 ; `project_rescue` : `manage_contributors` seule disponible) ; `ProjectCommand` et
  `CommandCondition` disent l'exception ; les suggestions nomment nœud et rôles
  (`contributor_suggestions`, Sacha Lefèvre, atelier de câblage, monteur câbleur 454).
- **Chronologies** (D-05, D-12 réglés) : `TimelineCreate` nommé, `\S`, 200 ; 409
  `project_not_terminal` sur la création et la suppression (`timeline_create_terminal`,
  `timeline_delete_terminal`, passé de 403 à 409) ; suppression physique sans compteur ni révision
  qui retienne (WF-DAT-0080) ; `manage_timelines` gardée par `planning.write`, non réservée aux
  chefs de projet (`project_participant` la liste disponible).
- **Transversal.** Les 18 opérations sous `/projects/{project_id}` déclarent le 404 ; les 19 le
  401, le 500 et le 503 ; les 10 opérations à corps le 400 et le 422 ; `PROJECT_CODE_REQUIRED`,
  `PROJECT_TERMINAL`, `WIN_PROBABILITY_FROZEN` ont quitté `ErrorCode` (D-13 réglé) ; chaque valeur
  de `CommandCondition` est décrite dans sa description et portée par au moins une fixture (grep
  sur les 58 valeurs) ; les codes que la famille est seule à porter — `REFERENCE_INCOMPLETE`,
  `LAST_PROJECT_MANAGER`, `CONFIRMATION_REQUIRED` (avec `startRestore`), `PROJECT_CODE_INVALID`,
  `SUBPROJECT_CODE_INVALID`, `UNKNOWN_USER`, `USER_INACTIVE`, `UNKNOWN_WORK_BREAKDOWN_ITEM`,
  `DUPLICATE_WORK_BREAKDOWN_ITEM`, `NOT_PROJECT_MANAGER`, `NOT_CONTRIBUTOR` — ont chacun une
  opération et un exemple. L'univers témoin tient : offre 100 marquée le 15 décembre, désignée le
  15 janvier (passage à En cours, `state_transitions`), avenant 101 marqué le 1er février et devenu
  référence (WF-REV-0040), 102 ouverte le 2 février (`project.json`, `revisions.json`) ; les
  sous-projets déclarés le 20 janvier, après la commande du 15 ; Lucas Petit inscrit le 3 novembre,
  Inès Roux le 15 janvier, la liste à sa quatrième version.

### Doutes

- **`createRevision` et `no_current_revision` (famille E, `paths/revisions.yaml:88-96`).** La
  commande `create_revision` du projet dit d'avance `no_current_revision` (dix fixtures de cette
  famille), et le 409 de `createRevision` refuse par `CURRENT_REVISION_EXISTS`, « sans
  paramètre » : deux formes pour un même fait, quand le README (« Conventions ») et US-0702/L1
  (`DECISIONS.md:9657-9676`) veulent un 409 `STATE_FORBIDS_OPERATION` nommant la condition que
  l'objet dit d'avance. EP-15/US-0490/L4 (`:7285-7290`) a gardé le code « au catalogue depuis
  EP-02 » sans se mesurer à la règle unique, postérieure. La spécification ne fixe pas les codes :
  pas un constat de cette annexe ; à signaler à l'annexe E, et au relecteur de la règle unique.
  Aucune opération ne nomme `no_current_revision` (grep sur `paths/`).
- **`openImport` et l'import de coûts réels avant En cours (famille I, `paths/exchanges.yaml:298-317`).**
  La commande `import_actual_costs` est indisponible avant En cours, `project_in_progress`
  (`project_pricing`, `project_created`) ; le 409 d'`openImport` ne nomme que `project_before_in_progress`
  (devis) et `actual_cost_mapping_complete`, et « Projet terminal » sans condition. L'appel direct
  d'un import de coûts réels sur un projet en chiffrage n'a pas de refus écrit. À l'annexe I.
- **Un chef de projet qui laisse la liste sans chef de projet actif.** `LAST_PROJECT_MANAGER`
  refuse « une liste qui ne garderait aucun chef de projet » ; un chef de projet qui se passe
  participant en ne laissant qu'un chef de projet désactivé en garde un. WF-PRJ-0060 n'exige
  qu'« au moins un chef de projet » et prévoit le sauvetage ; le contrat suit la lettre. Est-ce
  voulu que la saisie puisse créer l'état que le sauvetage répare ? À confirmer.
- **`ContributorKind.contributor` pour « participant ».** La spécification nomme la qualité
  « chef de projet ou participant » (WF-PRJ-0060, WF-ADM-0110, WF-IHM-0090) ; le contrat
  `project_manager`/`contributor`, décidé le 2026-10-03 (`DECISIONS.md:291-295`). Même mot pour
  l'inscrit et pour la qualité de l'inscrit non chef ; renommer après le gel ne se pourra plus.
  Décision à confirmer, pas un constat.
- **Propositions de contributeurs.** Le corps de WF-PRJ-0070 propose « les utilisateurs rattachés
  aux nœuds d'organisation des rôles … employés », la Vérif ne les propose que pour « un service
  dont aucun utilisateur n'est contributeur ». Le contrat suit le corps (tout compte actif du nœud
  non encore inscrit, `contributor_suggestions`). Deux lectures ; la plus large est servie.
- **Export PNG d'une chronologie** (WF-PLA-0140, WF-IHM-0130) : aucune opération ; vraisemblablement
  un rendu du front, comme les autres images du §3.6. Rien ne l'écrit.
- **Une chronologie ne se renomme pas** : `Timeline` n'a ni `lock_version` ni écriture ; WF-PLA-0140
  n'exige que le nom, la conservation et la suppression. Conforme ; noté parce qu'un `PATCH`
  après le gel serait un ajout compatible, et qu'un compteur ne le serait pas.
- **`conflicting_object_label` absent du nom de version pris** (`project_exit_version_name_taken`,
  comme `markRevision`) : la convention le veut « quand le formulaire ne connaît pas la liste qui
  le porte » ; la confirmation de sortie connaît-elle l'historique des révisions ? Choix de
  US-0701/L9 (« comme `markRevision` »), cohérent avec la famille E.
- **`:` dans `DeclaredSubprojectCode`.** La spécification 1.0.1 écrit toujours « sans aucun des
  caractères : \\ / ? * [ ] », où le deux-points se lit aussi comme ponctuation ; US-0610 l'inclut
  (Excel l'interdit). Confirmé par la décision, pas par la lettre.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| D-01 (bloquant, sort de la révision en cours) | réglé | `schemas/projects.yaml:665-744` (`ProjectExit.current_revision`, `CurrentRevisionFate` `oneOf` discriminé, `CurrentRevisionMark`, `CurrentRevisionAbandon`) ; `paths/projects.yaml:325-439` (200/202, 409 `ALREADY_EXISTS`, 422 `VALUE_REQUIRED`) ; fixtures `project_exit_abandoning`, `project_exit_marking`, `task_exit_mark_queued`, `project_completed` (la 102 abandonnée, dite) ; `DECISIONS.md:9551-9593` |
| D-02 (`lose` listée En cours ; conditions des sorties) | réglé | `schemas/projects.yaml:463-472` (`ProjectCommand` : règle de présence et conditions des trois sorties) ; `lose` absente des sept lectures En cours, `project_completed` sans commande ; `DECISIONS.md:9594-9606`, `:9869-9893` |
| D-03 (refus d'`exitProject` non décrits) | réglé | `paths/projects.yaml:379-390` (400 `CONFIRMATION_REQUIRED`, `project_exit_unconfirmed`), `:393-414` (409 : ordre, codes, trois exemples), `:424-439` (422, deux exemples) ; `DECISIONS.md:9798-9807` |
| D-04 (`updateProject` dit « 422 » pour la probabilité figée) | réglé | `paths/projects.yaml:188-192` (« refusée par 409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `project_before_in_progress` ») |
| D-05 (403 `PROJECT_TERMINAL` sur les chronologies) | réglé | `paths/projects.yaml:1080-1089`, `:1124-1133` (409 `project_not_terminal`, `timeline_create_terminal`, `timeline_delete_terminal` à 409) ; `PROJECT_TERMINAL` hors d'`ErrorCode` ; README « Conventions » ; `DECISIONS.md:9657-9676` |
| D-06 (inscription d'un chef de projet par un non-contributeur) | réglé | `paths/projects.yaml:928-948` (`setContributors`), `:972-981` (409) ; `schemas/projects.yaml:61-86` (`Project.available_commands`), `:106-118` (`CommandCondition`), `:451-458` (`ProjectCommand.manage_contributors`) ; fixtures `contributors_without_active_manager`, `contributors_set_by_rescuer`, `project_rescue` ; `DECISIONS.md:9607-9618` |
| D-07 (code projet sans `\S` ni interdit de `/`) | réglé | `schemas/projects.yaml:544-560` (`ProjectCode`, 1–50, motif sans `/`, partagé par les quatre schémas) ; `common.yaml` (`PROJECT_CODE_INVALID`) ; `paths/projects.yaml:132-147`, `:244-252` ; fixture `project_code_invalid` ; `DECISIONS.md:9629-9638`. Le doute associé (`code: null` En cours) redevient D-06 de cette revue |
| D-08 (« regroupent des tâches ») | réglé | `paths/projects.yaml:601-603` (« codes de l'ERP sous lesquels les lignes de devis se ventilent et les coûts réels s'imputent — jamais une tâche ») |
| D-09 (« découpage fonctionnel et produit ») | réglé | `paths/projects.yaml:499-500` (« qui reproduit le bon de commande ») |
| D-10 (`createSubproject` sans 404) | réglé | `paths/projects.yaml:677` ; `DECISIONS.md:9861` |
| D-11 (saisie sans lot ; défaut suit le libellé) | réglé | `schemas/projects.yaml:746-768` (`minItems: 1`, « Tant qu'aucune saisie ne l'a écrit, le lot et le poste par défaut portent le libellé du projet, et le suivent quand il change ») ; `paths/projects.yaml:571-575` (422 `/work_packages` par `VALUE_REQUIRED`) ; `DECISIONS.md:9642-9647` |
| D-12 (nom de chronologie sans `\S`, schéma anonyme) | réglé | `schemas/revisions.yaml:1769-1776` (`TimelineCreate`, `\S`) ; `paths/projects.yaml:1067`, `:1090-1103` (422 nommant le nom blanc, `timeline_label_required`) |
| D-13 (`PROJECT_CODE_REQUIRED` au catalogue) | réglé | absent de `common.yaml` (grep) ; `DECISIONS.md:9700-9703` (US-0702/L1 : « Retirés aussi : `PROJECT_CODE_REQUIRED`, que rien ne refuse ») |
| L-02 (sortie marque ou abandonne dans la même opération) | réglé | comme D-01 ; `ProjectCommand.complete/lose/abandon` nomment `no_background_task_running` pendant un marquage (`project_background_task_running`, `task_exit_mark_queued`) |
| L-03 (« Déclarer perdu » En cours) | réglé | comme D-02 ; `project_exit_lost_in_progress` pour l'appel direct |
| L-17 (non-contributeur inscrit un chef de projet) | réglé | comme D-06 ; la condition `project_manager_active` proposée a été écartée (`DECISIONS.md:9613-9614`), une commande disponible n'ayant rien à nommer |
| Doute « `exitProject` sans `lock_version` » | réglé | `schemas/projects.yaml:698-702`, `paths/projects.yaml:415-423`, `project_exit_stale` ; `DECISIONS.md:9784-9796` |
| Doute « `code: null` sur un projet En cours » | non réglé → D-06 | `DECISIONS.md:9637-9638` le laisse ouvert ; redevient constat mineur |
| Doutes « participant », « propositions », « export PNG », « `:` » | sans objet (restent des doutes) | repris ci-dessus, inchangés ; aucun n'est contredit par la 1.0.1 |

## Annexe E — Révisions et structures de coûts

Périmètre. Lu : `docs/api/README-fr.md` (94 lignes, « Conventions » en entier) ; `docs/api/paths/revisions.yaml`
lignes 1–895 (`listRevisions` … `mergeCostStructure`, quatorze opérations) et 2164–2345 (`undoLastChange`,
`redoLastUndo`, `generatePlanningSkeleton`) sur 2 345 ; `docs/api/components/schemas/revisions.yaml` lignes
1–596, 699–716 (`NodeDifference`), 1061–1194 (`NodeListMeta`, `NodeTotals`, `NodesWritten`), 2090–2167
(`UndoResult`, `UndoneKind`), 2336–2456 (`RevisionComparison`, `Compared*`) sur 2 456 ;
`components/parameters.yaml` (909 lignes : `ProjectId`, `RevisionId`, `StructureId`, `Limit`, `Offset`,
`Search`, `NodeKinds`, `NodeSubtreeOf`, `NodeDifferenceFilter`, `NodeFields`, `NodeSortBy`, `SortOrder`,
`SubprojectFilter`) ; `components/common.yaml` (991 lignes : types élémentaires 18–120, `Problem` 141–393,
`ErrorCode` 394–729, `ProblemParams` 730–800, `BackgroundTaskRef` 931–991) ; `components/responses.yaml`
(138) ; `schemas/projects.yaml` (`CommandCondition`, `ProjectCommand`, `Project` 10–60) ;
`schemas/exchanges.yaml` (`ImportCompletedTask` 409–430, `ReportRefusal`, `ImportDifference`,
`ImportDifferenceField` 544–700) ; `schemas/reference.yaml#/HourlyRateImage` (667–680) ;
`schemas/access.yaml#/PermissionCode` (433–510) ; `schemas/platform.yaml` 220–230. **73 fixtures ouvertes**,
toutes celles que ces dix-sept opérations référencent, `volume/comparison_volume.json` (6 019 lignes) et
`volume/structure_planning_start_advanced.json` (1 139) lues par leurs totaux, leurs compteurs et leurs
écarts ; `project.json`, `project_created.json`, `project_revision_opened.json`, `project_pricing.json`
ouverts pour l'univers témoin. Spécification 1.0.1 : §3.2.5 (795), §3.4.5.1 (1906–2032, WF-REV-0010 à
0100), §4.4.2 (3980–4060, WF-DAT-0010, 0020, 0040), WF-IHM-0020, WF-IHM-0090, WF-IHM-0110 (1.0.1),
WF-IHM-0130, WF-DEV-0010, 0020, 0030, 0070, WF-PLA-0020, WF-PLA-0150, WF-PRJ-0030, WF-RIS-0020, WF-RIS-0030,
WF-CYC-0020, WF-CYC-0090, WF-REF-0130, WF-ADM-0100, WF-INTF-0050 ; le `git diff` de la 1.0.1 sur WF-REV-0080
et WF-IHM-0110. `DECISIONS.md` : l'univers témoin (1777–2723, « Révisions et risques »), 8431 (fusion,
US-0640/L3), 8545–8560 (#1351), 8686–8790 (inflation comprise, deux écarts, M-08), 9066–9162 (US-0701/L2),
9649–9976 (US-0702/L1 à L3, US-0700/L1), 10076–10101 (« Collage et annulation »), 6829–6840 (#791), 7074–7077 (C-363), 7121–7126 (#1352),
et un `grep` de chaque constat E-nn et L-nn de la revue du 2026-10-28. Revue précédente : annexe E
(1670–2200) et L-04, L-05, L-06, L-14, L-15, L-18 (3370–3465).

### Synthèse

La famille a été profondément reprise depuis le 2026-10-28 : les quatre constats qui touchaient le modèle
(date de début de planning, deux écarts de la comparaison, taux d'inflation et probabilité conservés,
révision source) sont réglés exactement comme la revue le proposait, l'historique annulable est tenu par
le serveur et la spécification 1.0.1 l'a suivi (WF-IHM-0110), les refus d'état ont tous leur code, leur
condition et un exemple engendré, et les compteurs manquants (`abandonRevision`, `designateReferenceRevision`)
sont là. Les fixtures, désormais engendrées pour l'essentiel, racontent la même chronologie — offre 2025,
référence du 1er février, révision courante du 2 février — et leurs compteurs se tiennent (3 et 1 au compte
rendu sans révision en cours, 1 et 2 aujourd'hui, 7 pour le projet). Ce qui reste est de second rang mais
pas anodin : la comparaison ne dit pas comment un écart par nature ou par sous-projet compte une ligne qui a
changé de clé entre les deux révisions, alors que le témoin en dépend tout entier (l'offre sans sous-projet) ;
la règle du réestimé « après une fusion » a perdu le qualificatif « de même année de référence » que la 1.0.1
a ajouté, et contredit mot pour mot la fixture témoin ; le corps d'`applyRateUpdate` laisse `lock_version`
facultatif contre la convention ; la copie d'une révision ne reprend pas le différentiel fusionné, ce que la
spécification exige et que le contrat ne dit pas ; et « conserve les taux de la révision source » oublie
« projetés ». Quatre mineurs de la revue précédente n'ont pas été traités (E-16, E-17, E-21, E-23) et un
cinquième ne l'est qu'à moitié (E-18). **18 constats : 0 bloquant, 5 majeurs, 13 mineurs. Suivi des 31
constats du 2026-10-28 : 25 réglés, 1 partiellement réglé, 4 non réglés, 1 sans objet.**

### Constats

#### E-01 — Une ligne qui change de nature ou de sous-projet : l'écart par clé n'est pas défini
- **gravité** : majeur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:2367-2397` (`RevisionComparison.amount_deltas`,
  description), `:2398-2419` (`budgeted_delta`, `reestimated_delta`) ; `fixtures/api/comparison.json`
  (`amount_deltas`, dimension `subproject`), `fixtures/api/volume/comparison_volume.json` (idem, trois clés)
- **spécification** : `WF-REV-0080-A` — « les écarts de montants budgétés et de montants réestimés, par
  nature de coût et par sous-projet » ; `DECISIONS.md:9939-9943` (US-0700/L1) : « Une ligne dont seul le
  sous-projet change reste `unchanged` […] et ses écarts par sous-projet, que la comparaison lue entière
  compte, n'y sont pas (relevé hors de ce lot) »
- **le contrat dit** : « L'écart se compte par ligne retenue, selon son parent dans la révision comparée
  (`to_revision_id`) : chaque ligne retenue y apporte ses écarts entiers, ses montants dans la révision
  comparée moins ceux de la révision de base, où qu'elle fût dans celle-ci » — une règle de **fenêtre**
  (sous-arbre), qui ne dit rien de la **clé** (`dimension`, `key`) sous laquelle compte une ligne dont la
  nature ou le sous-projet n'est pas le même dans les deux révisions. Lue à la lettre pour la dimension
  `subproject`, elle attribue l'écart entier de la ligne à sa clé dans la révision comparée.
- **la fixture dit** : `comparison.json`, « Poste de commande » `budgeted_delta` 18 300,00 =
  3 000 (« Assistance aux essais de câblage », ajoutée) + 9 420 (« Câblage sur site ») + 5 880 (« Mise en
  service sur site »), et `unassigned` 584 350,00 = 600 000 − 350 − 9 420 − 5 880 : les deux lignes
  existantes, dont le budgété ne change pas (9 420 → 9 420, 5 880 → 5 880), comptent **leur montant entier**
  en sortie de l'ensemble hors sous-projet et en entrée du « Poste de commande », parce que l'offre ne
  portait aucun sous-projet. La règle du contrat appliquée à la lettre donnerait 3 000 + 180 + 120 = 3 300
  réestimés et 3 000 budgétés au « Poste de commande », et 599 650 à `unassigned`. Le générateur fait
  l'autre choix, le seul qui donne un sens à « par sous-projet » ; le contrat ne le dit pas, et le résumé de
  la fixture est le seul texte qui l'explique (« ses lignes passent de l'ensemble hors sous-projet au sien »).
- **décision** : `DECISIONS.md:8737-8751` (E-02) fixe les deux écarts et leur sens, non l'attribution par
  clé ; `9939-9943` relève le cas comme « hors de ce lot » — aucune décision ne le tranche
- **proposition** : une phrase dans `amount_deltas` : « Une ligne compte sous la clé qu'elle porte dans
  chaque révision : son montant dans la révision comparée sous sa nature et son sous-projet d'alors, moins
  son montant dans la révision de base sous les siens d'alors ; une ligne qui change de nature ou de
  sous-projet entre les deux compte donc son montant entier en moins sous l'ancienne clé et en plus sous la
  nouvelle, même quand son montant ne change pas — l'offre sans sous-projet comparée à la référence en est
  l'exemple (`comparison`) ». Un test de `test_mockcomparison.py` qui tient la somme des écarts par
  sous-projet à celle par nature (ici 602 650 budgétés des deux côtés).

#### E-02 — Le réestimé « après une fusion » a perdu « de même année de référence », et contredit le témoin
- **gravité** : majeur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:2409-2419` (`amount_deltas[].reestimated_delta`,
  description) ; `fixtures/api/comparison.json` (lignes 17 et 20 de l'arbre, « Câblage sur site », « Mise en
  service sur site », `changes: [reestimated_amount]`)
- **spécification** : `WF-REV-0080-A` (Vérif, **1.0.1**) — « La comparaison d'une révision obtenue par fusion
  d'un différentiel avec la révision marquée qui la précède, **de même année de référence**, lorsqu'aucune
  autre modification n'a été faite entre les deux, restitue exactement les tâches et les montants budgétés
  de ce différentiel. Les montants réestimés n'y diffèrent que par les lignes que le différentiel ajoute ou
  retire […] **Entre deux révisions d'années de référence différentes, les montants réestimés diffèrent en
  outre sur chaque ligne dont le taux a été mis à jour ou projeté jusqu'à la nouvelle année de référence
  (WF-REV-0060) ; les tâches et les montants budgétés restent ceux du différentiel.** »
- **le contrat dit** : « Après une fusion, il ne vient que des lignes que le différentiel ajoute ou retire, de
  celles des tâches démarrées qu'il termine et de celles dont il change l'année de consommation : une ligne
  existante dont le différentiel ne modifie que le montant budgété n'y apporte rien. » — sans la condition
  d'année de référence, ni la seconde phrase.
- **la fixture dit** : le témoin est précisément le cas d'années différentes (offre 2025 → référence 2026 par
  la fusion de l'avenant 1) : « Câblage sur site » et « Mise en service sur site », que l'avenant ne désigne
  pas, portent un écart réestimé (9 420 → 9 600, 5 880 → 6 000, taux 2026) et « Main-d'œuvre » rend
  `reestimated_delta` 3 300,00 contre `budgeted_delta` 3 000,00. Un implémenteur qui suit la description
  tiendrait l'exemple pour faux, ou l'inverse. Le résumé de la fixture le dit juste (« réestimées au taux de
  2026 de leur catégorie »), la description du schéma non.
- **décision** : `DECISIONS.md:8737-8751` (E-02) — tient, mais écrite avant la 1.0.1 ; la spécification l'a
  précisée, pas contredite
- **proposition** : reprendre la 1.0.1 : « Entre deux révisions **de même année de référence**, il ne vient,
  après une fusion, que des lignes que le différentiel ajoute ou retire, de celles des tâches démarrées
  qu'il termine et de celles dont il change l'année de consommation […] ; entre deux révisions d'années de
  référence différentes, il vient aussi de chaque ligne dont le taux a été mis à jour ou projeté jusqu'à la
  nouvelle année (WF-REV-0060), les montants budgétés restant ceux du différentiel — l'offre de 2025 comparée
  à la référence de 2026 (`comparison`) ». Même complément à `budgeted_delta` (« quelle que soit l'année »).

#### E-03 — `applyRateUpdate` : `lock_version` facultatif, liste sans borne, corps anonyme
- **gravité** : majeur
- **emplacement** : `docs/api/paths/revisions.yaml:381-393` (corps de `applyRateUpdate` :
  `required: [cost_category_ids]`, `lock_version` non exigé, pas de `minItems`), `:421` (412
  `PreconditionFailed` déclaré)
- **spécification** : `WF-IHM-0110-A` ; README « Conventions » : « `lock_version` sur les écritures
  concurrentes, refus par 412 `STALE_LOCK_VERSION` […] et rien d'autre » ; `LockVersion`
  (`common.yaml:92-103`) : « Toute modification le porte et l'exige »
- **le contrat dit** : la mise à jour « rechiffre » la révision et rend « la révision, une version de plus »
  (200) ; elle déclare le 412 ; mais son corps n'exige que `cost_category_ids`, et `lock_version` peut
  manquer sans que rien ne dise ce qu'un corps sans compteur reçoit (écrit sans contrôle ? 422 ?). Toutes les
  autres écritures de la famille l'exigent (`RevisionMark`, `ReferenceDesignation`, `StructureUpdate`,
  `StructureMerge` par ses deux compteurs). `cost_category_ids` admet la liste vide, qui ne changerait rien,
  et rien ne dit ce que reçoit une catégorie absente de la proposition (422 `VALIDATION_FAILED` sur
  `/cost_category_ids/<n>` ?). Le corps est le seul de la famille sans schéma nommé (E-21), ce que le client
  engendré et les modèles du service reçoivent comme un type anonyme.
- **la fixture dit** : `rate_update_applied.json`, `lock_version` 2 après une création à 1 : le compteur est
  bien porté.
- **décision** : `DECISIONS.md:8545-8560` (#1351) fixe la permission et les conditions, pas le corps ;
  `9784-9797` (US-0702/L2) n'a repris que les cinq écritures sans compteur de la revue — celle-ci en avait un,
  facultatif, et n'y figurait pas. Aucune décision n'écarte le compteur ici.
- **proposition** : un schéma `RateUpdateApply` dans `schemas/revisions.yaml`, après `RateUpdateProposal` :
  `required: [cost_category_ids, lock_version]`, `cost_category_ids` à `minItems: 1`, décrit « les
  catégories acceptées parmi celles que la proposition présente ; une catégorie qu'elle ne présente pas est
  refusée par 422 `VALIDATION_FAILED`, `fields` sur `/cost_category_ids/<n>` » ; `lock_version` décrit comme
  « le compteur lu de la révision (`Revision.lock_version`) ». Rendre `lock_version` exigé est un changement
  d'exigé/facultatif : à faire avant le gel.

#### E-04 — Le différentiel fusionné n'est pas repris par la révision suivante, et le contrat ne le dit pas
- **gravité** : majeur
- **emplacement** : `docs/api/paths/revisions.yaml:58-60` (`createRevision` : « sa création copie les
  structures de la dernière révision marquée ») ; `fixtures/api/structures.json` (révision 102 : cinq
  structures, 201, 203, 204, 205, 206) contre `fixtures/api/structures_amendments.json` (révision 101 : six,
  dont 212 « Avenant 1 — extension du poste », `is_merged: true`)
- **spécification** : `WF-REV-0100-A` (Vérif) — « une révision créée à partir d'une révision marquée en
  reprend **toutes** les structures, différentielles et propres des risques comprises (WF-REV-0010) » ;
  `WF-REV-0010-A` — « Sa création reprend les structures de la dernière révision marquée » ; `WF-DAT-0010-A`
  (Vérif) — « le nombre de lignes de chaque table portant l'identifiant de la nouvelle révision égale celui
  de la révision marquée »
- **le contrat dit** : « copie les structures », sans exception ; `CostStructure.is_merged` reste un attribut
  de la structure (« Vrai lorsque le différentiel a été fusionné »), donc un différentiel fusionné est une
  structure de sa révision, que `listCostStructures` liste (212 dans `structures_amendments`).
- **la fixture dit** : la révision 102, copie de 101 (`source_revision_id` 101), n'a pas d'avenant 1 :
  `structures.json` le dit en creux (« l'avenant 2 […] que la révision a repris de la révision de référence,
  où il coexistait avec l'avenant 1 ») ; `DECISIONS.md:6829-6832` (#791) ne parle que de l'avenant 2.
  Soit la copie omet les différentiels fusionnés — alors le contrat doit le dire, et le Vérif de WF-REV-0100
  et celui de WF-DAT-0010 (égalité des nombres de lignes) sont contredits ; soit elle les reprend, inertes,
  `is_merged` vrai — alors la fixture est fausse. Un implémenteur de `createRevision` tranchera seul, et
  l'historique des avenants (relire ce qu'un avenant contenait, motif de WF-REV-0100) en dépend.
- **décision** : aucune (`#791` à `6829`, US-0701/L2 à `9066` : rien sur la reprise d'un différentiel
  fusionné)
- **proposition** : à trancher par l'auteur. Au plus près de la spécification : la copie reprend toutes les
  structures, `is_merged` compris, et `structures.json` reçoit l'avenant 1 (`is_merged: true`, saisie
  indisponible ou absente — à dire aussi : un différentiel fusionné se saisit-il encore ? `structures_amendments`
  le liste avec `edit_planning`/`edit_estimate`, indisponibles par `revision_draft` seulement). Sinon, une
  phrase dans `createRevision` et `WF-REV-0100` à corriger : « sauf les différentiels déjà fusionnés, que la
  structure principale porte désormais ».

#### E-05 — « Conserve les taux de la révision source » : il manque « projetés »
- **gravité** : majeur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:274-279` (`RevisionCreate.apply_rate_update`) ;
  `docs/api/paths/revisions.yaml:55-66` (`createRevision`, description)
- **spécification** : `WF-REV-0060-A` — « Une catégorie non encore présentée, refusée, ou sans taux pour la
  nouvelle année, conserve son taux précédent, **projeté par le taux d'inflation du projet jusqu'à la
  nouvelle année de référence** » ; `WF-REV-0010-A` (Vérif) — « pour chaque catégorie dont la mise à jour de
  WF-REV-0060 n'a pas été acceptée, le taux précédent projeté par le taux d'inflation du projet jusqu'à la
  nouvelle année de référence » ; `WF-DEV-0030-A` — « taux du référentiel accepté, ou taux conservé projeté »
- **le contrat dit** : « Applique la mise à jour des taux proposée par WF-REV-0060. Jamais imposée : la valeur
  par défaut conserve les taux de la révision source. » — lu seul, le service garde les taux de 2025 sur une
  révision de 2026 ; `mergeCostStructure` (`paths:815-816`) et `StructureMergeReport.creates_current_revision`
  disent, eux, « chiffrée aux taux conservés, projetés ». La description ne dit pas non plus ce que le
  booléen applique : toutes les catégories que la proposition présenterait (`reference_rate`), d'un coup,
  sans la présentation « catégorie par catégorie » que WF-REV-0060 décrit — admissible, puisque la
  présentation reste proposée ensuite, mais à dire ; ni ce qu'il fait d'une catégorie `inflated_previous`,
  pour laquelle il n'y a rien à appliquer.
- **la fixture dit** : `rate_update_applied.json` et `revision_rate_update_offered.json` racontent la bonne
  règle (« qui lui a appliqué les taux de l'offre projetés jusqu'en 2026 »).
- **décision** : `DECISIONS.md:8553-8555` (#1351 : « `createRevision`, qui applique déjà la mise à jour à la
  création ») — tient ; rien sur la projection par défaut
- **proposition** : « Faux ou absent, la révision est chiffrée aux taux de la révision source projetés par le
  taux d'inflation du projet jusqu'à son année de référence (WF-REV-0060, WF-REV-0010), la mise à jour
  restant proposée (`getRateUpdateProposal`) ; vrai, chaque catégorie que la proposition présenterait au taux
  du référentiel de l'année (`reference_rate`) est chiffrée à ce taux, comme `applyRateUpdate` sur toutes ;
  jamais imposée. » Une phrase de même dans `createRevision`.

#### E-06 — `RateUpdateProposal` : `target_year` facultatif, trois champs sans description, proposition après acceptation et sur une révision marquée
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:318-350` (`required: [categories]` ; `target_year`
  :327 ; `previous_amount` :346, `proposed_amount` :347, `source` :348-350 sans description) ;
  `fixtures/api/rate_update_none.json` (sans `target_year`) ; `docs/api/paths/revisions.yaml:342-365`
  (`getRateUpdateProposal`, 200 seul)
- **spécification** : `WF-REV-0060-A` — « présente, catégorie par catégorie, le taux conservé et le taux du
  référentiel pour la nouvelle année » ; « la présentation reste proposée depuis la révision en cours tant
  qu'elle n'est pas marquée »
- **le contrat dit** : l'année visée « est l'année de référence de la révision créée », toujours connue, mais
  facultative et absente de l'exemple ; `previous_amount` ne dit pas s'il est le taux de l'année précédente
  tel quel (78,50 dans `rate_update`) ou le taux conservé que la révision applique déjà, projeté (78,50 ×
  1,03) — la spécification nomme « le taux conservé » ; `proposed_amount` et `source` ne disent pas ce qu'est
  une catégorie `inflated_previous` dans une proposition (un taux déjà appliqué, qu'il n'y a rien à
  accepter ?). Ce que la proposition rend d'une catégorie acceptée depuis n'est dit qu'en creux par
  `RevisionCommand.apply_rate_update` et `CommandCondition.rate_update_available` (« chaque catégorie
  présentée a déjà été acceptée » → aucune catégorie présentée). Sur une révision marquée, où la commande
  « n'est pas jugée », `getRateUpdateProposal` rend-il la liste vide, les catégories du marquage, un 409 ?
- **décision** : `DECISIONS.md:8545-8560` (#1351) — tient, ne traite ni `target_year` ni le contenu
- **proposition** : `required: [target_year, categories]`, `rate_update_none.json` avec `target_year: 2026` ;
  décrire `previous_amount` (« le taux de l'année de référence de la révision copiée, avant projection »),
  `proposed_amount` (« le taux du référentiel pour l'année visée, ou, sans taux, le précédent projeté par
  l'inflation ») et `source` ; une phrase : « Une catégorie acceptée n'est plus présentée ; sur une révision
  marquée, la proposition est vide ». E-18 de la revue précédente, non réglé.

#### E-07 — `compareRevisions` : la révision en cours, la révision d'un autre projet, deux paramètres sans description
- **gravité** : mineur
- **emplacement** : `docs/api/paths/revisions.yaml:428-430` (résumé « Comparer deux révisions marquées »),
  `:476-483` (`from_revision_id`, `to_revision_id` : `required`, `schema`, aucune `description`), `:557-577`
  (404 et 422 seuls refus)
- **spécification** : `WF-REV-0080-A` — « Deux révisions marquées d'un même projet peuvent être comparées »
- **le contrat dit** : rien de ce que reçoit une révision en cours donnée en `from` ou en `to` — 409
  `STATE_FORBIDS_OPERATION`, `revision_marked`, ou une lecture (l'écart du brouillon à la référence serait
  utile, mais hors spécification) —, rien d'une révision d'un autre projet (404 ?), et les deux paramètres
  ne disent pas lequel est la base et lequel est la comparée, ce que seule la description longue explique.
- **décision** : aucune
- **proposition** : décrire les deux paramètres (« la révision de base, marquée », « la révision comparée,
  marquée, dont l'arbre est rendu ») ; déclarer le 409 (`revision_marked`) ou admettre la révision en cours
  et le dire ; dire qu'une révision qui n'est pas du projet est un 404. E-23 de la revue précédente, non
  réglé.

#### E-08 — `merge_revision_marked_refused.json` : le résumé nomme toujours `revision_marked`
- **gravité** : mineur
- **emplacement** : `fixtures/api/merge_revision_marked_refused.json:2` (« Refusée par la condition que la
  commande merge_structure de la référence dit manquer (revision_marked) ») et `:7`
  (`"missing_condition": "revision_draft"`)
- **spécification** : `WF-REV-0050-A`, `WF-DAT-0020-A`
- **le contrat dit** : `mergeCostStructure` 409 — « `revision_draft` pour un différentiel d'une révision marquée
  qui n'est pas la dernière, ou d'un projet qui a une révision en cours » ; la valeur est juste, le résumé
  dit la condition inverse. Exemple écrit à la main (pas de `description` « engendré »).
- **décision** : `DECISIONS.md:8486-8495` (« C'est le refus […] `revision_draft` ») — tient
- **proposition** : `revision_marked` → `revision_draft` dans le résumé. E-17 de la revue précédente, non
  réglé.

#### E-09 — Le compteur : valeur initiale non dite, offre marquée à 1, ce qui fait avancer `Revision.lock_version`
- **gravité** : mineur
- **emplacement** : `docs/api/components/common.yaml:92-103` (`LockVersion`, sans valeur initiale) ;
  `docs/api/components/schemas/revisions.yaml:105` (`Revision.lock_version`, sans description) ;
  `fixtures/api/revisions.json` (offre 100 : `lock_version: 1` ; 101 : 3 ; 102 : 4),
  `fixtures/api/revision_offer.json` (1), `fixtures/api/revisions_designation_open.json` (« la 101,
  brouillon à sa version 2, voit son marquage porter la version 3 »), `fixtures/api/revision_created.json`
  (103 : 1), `fixtures/api/structures_without_tasks.json` (207 : 0), `fixtures/api/amendment_created.json`
  (213 : 1)
- **spécification** : `WF-IHM-0110-A`
- **le contrat dit** : `CostStructure.lock_version` est décrit (ce qui le fait avancer) ; `Revision.lock_version`
  ne l'est pas : une saisie de grille dans la révision le fait-elle avancer ? Si oui, tout marquage demandé
  après la saisie d'un autre contributeur est refusé par 412 ; si non, il ne suit que `mark`,
  `apply_rate_update`, l'abandon et ce que le serveur écrit sur la révision (la survenance ? le 2 mars à
  9 h 15 de `revision.json`, qui porte 4 sans qu'aucun récit ne dise quoi). La valeur initiale n'est pas
  dite : une révision naît à 1 (103, et 101 : 1 → 2 par la mise à jour → 3 par le marquage), une structure
  principale neuve à 0 (207, « son compteur à 0 », 0 → 1 par le squelette), un différentiel neuf à 1 (213).
  Avec « création à 1, marquage une version de plus » (#1352), l'offre 100, créée puis marquée sans autre
  écriture, devrait porter 2 ; elle porte 1 dans deux fixtures.
- **décision** : `DECISIONS.md:7121-7126` (#1352, « son marquage porte une version de plus ») — tient ; rien
  sur la valeur initiale ni sur ce que `Revision.lock_version` suit
- **proposition** : dans `LockVersion` : « Un objet créé naît à 1 » (ou 0, et aligner 103, 213, 101) ; dans
  `Revision.lock_version` : « avance à chaque écriture de la révision elle-même — mise à jour des taux,
  marquage, et ce qu'un traitement de fond y écrit —, jamais par une saisie de grille, que le compteur de la
  structure suit » ; l'offre à 2 (`revisions`, `revisions_marked`, `revisions_designation_open`,
  `revision_offer`), ou le récit de ce qui lui manque. E-16 de la revue précédente, non réglé.

#### E-10 — `version_name`, `description`, `marked_at` toujours rendus mais non exigés
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:15-28` (`Revision.required` : douze propriétés,
  sans `version_name` :31, `description` :36, `marked_at` :39)
- **spécification** : `WF-REV-0090-A` — « Une révision porte un nom de version, une description facultative,
  son état […], la date de son marquage » ; Vérif : « Chacun de ces attributs est présent dans l'historique
  des révisions »
- **le contrat dit** : les trois sont nullables (« Nul tant que la révision est en cours ») et toutes les
  fixtures les rendent, nuls ou non ; le schéma permet de les omettre, ce qu'un client engendré lit comme
  `version_name?: string | null`. `source_revision_id` et `source_version_name`, nullables de même, sont
  exigés (US-0701/L2) : la règle n'est pas une.
- **décision** : `DECISIONS.md:9102-9108` (US-0701/L2, « exigés et nuls pour la première révision ») pour les
  deux champs source — le même traitement manque aux trois autres
- **proposition** : les ajouter à `required` ; une description pour `description` et `marked_at` (« nul tant
  que la révision est en cours »).

#### E-11 — `updateCostStructure` : refus par réponses partagées sans exemple, un seul 200
- **gravité** : mineur
- **emplacement** : `docs/api/paths/revisions.yaml:703` (409 `Conflict` partagé), `:704` (412 partagé),
  `:705-718` (422 : `non_working_day` seul exemple ; `PROJECT_HORIZON_EXCEEDED` et le libellé vide sans
  exemple), `:689-698` (200 : `volume/structure_planning_start_advanced` seul) ;
  `docs/api/components/schemas/revisions.yaml:2115-2120` (`UndoResult.undone.node_ids` : « vide pour une
  saisie de risque »)
- **spécification** : `WF-PLA-0020-A`, `WF-PLA-0150-A`, `WF-IHM-0110-A`
- **le contrat dit** : la description nomme ses refus (« refusée comme elle sur une révision marquée ou pendant
  un traitement de fond », 412 du compteur, horizon, libellé vide) ; seul `NON_WORKING_DAY` a un exemple.
  Toutes les autres écritures de la famille ont désormais un exemple engendré de leur 409 `revision_draft`
  et de leur 412 (`mark_revision_marked`, `revision_abandon_stale`…). Le seul 200 est une variante
  contrefactuelle à mille tâches : un changement de libellé seul — `nodes`, `rescheduled`, `reinflated`
  vides, le compteur qui avance — n'a pas d'exemple. `node_ids` est aussi vide pour `structure_update`, que
  la description ne nomme pas.
- **décision** : `DECISIONS.md:9076-9101` (US-0701/L2) — tient ; rien sur les exemples des refus
- **proposition** : `structure_update_revision_marked` (409), `structure_update_stale` (412),
  `structure_label_updated` (200, sur la structure principale du témoin, `structure_lock_version` 2) ; « vide
  pour une saisie de risque et pour l'écriture d'une structure » dans `node_ids`.

#### E-12 — Le 400 `CONFIRMATION_REQUIRED` de la désignation n'a pas d'exemple
- **gravité** : mineur
- **emplacement** : `docs/api/paths/revisions.yaml:294-304` (`designateReferenceRevision`, 400 : schéma seul)
- **spécification** : `WF-REV-0040-A` ; `WF-ARC-0110-A`
- **le contrat dit** : « une désignation sans sa confirmation, `confirmed` absent ou faux :
  `CONFIRMATION_REQUIRED`, sans paramètre, comme la sortie (`exitProject`, `project_exit_unconfirmed`) » — la
  sortie a son exemple, la désignation renvoie à celui de la sortie sans en déclarer un.
- **décision** : `DECISIONS.md:9899-9910` (US-0702/L3, « `designateReferenceRevision` décrit son 400 ») —
  tient ; `9677-9680` (US-0702/L1 : « chaque code est porté par un exemple ») est satisfaite par
  `project_exit_unconfirmed`, pas sous cette opération
- **proposition** : `reference_designate_unconfirmed`, engendré (`mockrefusals`).

#### E-13 — Le marquage pendant une restauration : `no_restore_running` manque à `mark` et au 409
- **gravité** : mineur
- **emplacement** : `docs/api/paths/revisions.yaml:242-257` (409 de `markRevision` : `revision_draft`,
  `no_background_task_running`), `docs/api/components/schemas/revisions.yaml:212-217`
  (`RevisionCommand`, alinéa `mark` et `abandon`) ; contre `schemas/projects.yaml` (`CommandCondition` :
  « `no_restore_running` manque, pendant qu'une restauration s'exécute — de sa mise en file à la déconnexion
  des utilisateurs —, à la restauration, au déclenchement d'une sauvegarde **et au marquage**
  (WF-ADM-0160) ») et `schemas/platform.yaml:225-226` (« le marquage l'est pendant une restauration, qui
  remplace la base où il s'écrirait »)
- **spécification** : `WF-ADM-0160-A` (famille B), `WF-IHM-0090-A`
- **le contrat dit** : deux schémas disent que le marquage manque de `no_restore_running` pendant une
  restauration ; ni la commande `mark` de la révision ni le 409 de `markRevision` ne la nomment, et aucun
  exemple ne la montre sur un marquage. Un front qui lit `mark` disponible pendant la fenêtre entre la mise
  en file de la restauration et la maintenance envoie un marquage que le serveur refuse par une condition
  que la commande n'a pas dite.
- **décision** : aucune dans la famille ; la règle est portée par la famille B
- **proposition** : dans `RevisionCommand` (`mark`) et le 409 de `markRevision` : « puis `no_restore_running`
  pendant qu'une restauration est en file ou s'exécute (WF-ADM-0160) » ; ou retirer la mention du marquage
  de `CommandCondition` et de `BackupCommand` si l'auteur juge le 503 de la maintenance suffisant.

#### E-14 — `revision_importing.json` : le résumé dit « ne manque que de son marquage », la valeur en nomme deux
- **gravité** : mineur
- **emplacement** : `fixtures/api/revision_importing.json` (résumé : « la désignation de la référence ne manque
  que de son marquage » ; valeur : `designate_reference` → `["revision_marked", "reference_correctable"]`) ;
  `docs/api/components/schemas/revisions.yaml:218-222` (`RevisionCommand` : « `designate_reference` nomme
  […] `no_background_task_running` pendant un traitement de fond qui court sur la révision »)
- **spécification** : `WF-REV-0040-A`, `WF-IHM-0090-A`
- **le contrat dit** : la valeur est cohérente avec `CommandCondition` (pendant l'application d'un import, les
  seules commandes suspendues sont celles qui écrivent dans la révision ; pendant un marquage, « toutes les
  commandes qui la modifient », la désignation comprise — `revision_marking.json` l'ajoute, `revision_importing`
  non) ; mais le résumé contredit la valeur, et l'alinéa de `RevisionCommand` dit « un traitement de fond qui
  court sur la révision », ce qu'un import appliqué est aussi.
- **décision** : `CommandCondition` (US-0702/L1) — tient
- **proposition** : résumé : « la désignation de la référence ne manque que de son marquage et de la
  correction de la référence, non du traitement en cours » ; `RevisionCommand` : « `no_background_task_running`
  pendant le marquage de la révision, seul traitement qui la rendrait désignable ».

#### E-15 — Fusionner une structure qui n'est pas un différentiel non fusionné : la condition nommée est celle de la révision
- **gravité** : mineur
- **emplacement** : `docs/api/paths/revisions.yaml:846-852` (409 de `mergeCostStructure` :
  « `unmerged_amendment_exists` pour une structure qui n'est pas un différentiel non fusionné ») ; `:769-779`
  (409 de `getStructureMergeReport`, « comme au 409 de sa fusion ») ; `schemas/projects.yaml` (`CommandCondition.
  unmerged_amendment_exists` : « manque à la fusion tant qu'aucun différentiel **de la révision** n'est à
  fusionner, et la révision la nomme »)
- **spécification** : `WF-REV-0050-A`, `WF-REV-0100-A`, `WF-IHM-0090-A` (« Tout refus nomme la condition
  manquante »)
- **le contrat dit** : la condition se juge sur la révision ; la révision courante du témoin porte l'avenant 2
  non fusionné, et sa commande `merge_structure` est disponible. Une fusion demandée sur la structure
  principale 201, le devis propre 204 ou l'avenant 1 déjà fusionné (212, dans 101) recevrait
  `unmerged_amendment_exists` — une condition que la révision dit satisfaite. Le front rendrait « aucun
  différentiel à fusionner » quand il y en a un : la phrase est fausse, et aucune commande de la **structure**
  ne dit d'avance qu'elle se fusionne (`StructureCommand` n'a que les trois saisies).
- **décision** : `DECISIONS.md:8486-8495` (#790, « Le 409 ») nomme `revision_draft` et `may_create_revision`,
  pas ce cas
- **proposition** : à trancher. Soit un 422 `VALIDATION_FAILED` sans `fields`, ou un 404 (le chemin ne
  désigne pas un différentiel fusionnable, comme un nœud qui n'est pas de la structure) ; soit une condition
  propre, `structure_is_unmerged_amendment`, portée par une commande `merge` de la structure
  (`StructureCommand`), qui dirait aussi d'avance qu'un différentiel fusionné ne se fusionne plus.

#### E-16 — L'abandon sans révision marquée et l'ouverture qui passe le projet en Chiffrage ne sont pas dits
- **gravité** : mineur
- **emplacement** : `docs/api/paths/revisions.yaml:148-162` (`abandonRevision`, description : « Le projet
  revient à son état à la dernière révision marquée »), `:55-66` (`createRevision`, description)
- **spécification** : `WF-REV-0010-A` — « Lorsqu'il n'existe aucune révision marquée, l'abandon laisse le
  projet sans révision ; il reste à l'état Chiffrage (WF-CYC-0020), et une nouvelle révision peut être
  créée » ; Vérif : « L'abandon de l'unique révision d'un projet en chiffrage le laisse sans révision, à l'état
  Chiffrage, et la création d'une révision y est de nouveau proposée » ; `WF-CYC-0020-A` — « Les transitions
  vers Chiffrage et En cours sont déclenchées par les faits métier »
- **le contrat dit** : l'abandon « revient à la dernière révision marquée », sans le cas où il n'y en a pas
  (`revisions_empty` : « Un projet sans révision, comme le projet en chiffrage ») ; `createRevision` ne dit
  pas que l'ouverture de la première révision fait passer le projet de Créé à Chiffrage, ce que
  `project_revision_opened.json` affirme (« il passe à l'état Chiffrage (WF-CYC-0020) ») et que le 201 ne
  rend pas (la révision, non le projet).
- **décision** : `DECISIONS.md:7074-7077` (C-363) sur l'irréversibilité — tient ; rien sur ces deux phrases
- **proposition** : dans `abandonRevision` : « Sans révision marquée, l'abandon laisse le projet sans révision,
  à l'état Chiffrage, et `ProjectCommand.create_revision` redevient disponible (WF-REV-0010) » ; dans
  `createRevision` : « La première révision d'un projet Créé le fait passer à Chiffrage (WF-CYC-0020) :
  l'écran relit le projet (`project_revision_opened`) ».

#### E-17 — Annulation : le traitement de fond qui court, la permission, ne sont pas dits
- **gravité** : mineur
- **emplacement** : `docs/api/paths/revisions.yaml:2199-2233` (409 de `undoLastChange`), `:2256-2281`
  (`redoLastUndo`), `:2197` et `:2254` (403 `Forbidden` partagé)
- **spécification** : `WF-IHM-0110-A` (1.0.1) — « Une annulation est une modification comme une autre : elle
  passe par l'API, subit les mêmes règles » ; `WF-IHM-0090-A`
- **le contrat dit** : les 409 nomment `UNDO_CONFLICT`, `undo_history_not_empty`, `restored_subproject_exists`,
  `at_least_one_task`, `active_provision_category` ; rien sur une annulation demandée pendant un marquage, une
  fusion, une survenance ou un import de la révision — une écriture de la révision, que `CommandCondition`
  suspend toutes (« ce sont toutes les commandes qui la modifient ») —, ni sur la permission que le 403
  exige : celle de la saisie défaite (`planning.write` pour une cellule de planning, `risks.write` pour un
  risque) ou une autre. La pile étant par utilisateur, c'est son auteur qui annule, qui a eu la permission ;
  mais une permission retirée depuis, ou l'annulation d'une saisie de risque par la grille, laissent la
  question ouverte.
- **décision** : `DECISIONS.md:9142-9153` (US-0701/L2), `9719-9728` (E-07, US-0702/L1) — tiennent ; rien sur
  ces deux points
- **proposition** : au 409 : « ou un traitement de fond qui écrit dans la révision ou la fige,
  `STATE_FORBIDS_OPERATION`, `no_background_task_running` » ; dans la description : « refusée par 403 à qui
  n'a plus la permission de la saisie qu'elle défait (`PERMISSION_MISSING`) ».

#### E-18 — Deux variantes sans exemple : la révision d'un projet terminal, l'ordre de l'historique
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:94-101` (`Revision.available_commands` : « Une
  révision d'un projet terminal ne liste que ses exports ») ; `docs/api/paths/revisions.yaml:32` (`listRevisions`
  200 : « Révisions, de la plus récente à la plus ancienne »)
- **spécification** : `WF-CYC-0100-A`, `WF-CYC-0110-A` ; `WF-IHM-0060-A` (tri)
- **le contrat dit** : la règle du projet clos est décrite (US-0702/L3), et `project_completed.json` existe
  dans la famille D ; aucune des dix fixtures de `getRevision` ni des cinq de `listRevisions` ne montre une
  révision d'un projet terminal, aux quatre exports seuls. « De la plus récente à la plus ancienne » ne dit
  pas la colonne : la date de création (ce que les fixtures suivent : 102, 101, 100) ou celle du marquage,
  la révision en cours, sans marquage, venant alors où ?
- **décision** : `DECISIONS.md:9869-9890` (US-0702/L3) — tient ; `7124` (« trié de la plus récente à la plus
  ancienne, comme le dit le contrat ») ne dit pas la colonne non plus
- **proposition** : `revision_completed_project` (la dernière révision marquée du projet terminé de
  `project_completed`, quatre exports) ; « par date de création décroissante, la révision en cours d'abord ».

### Ce qui est juste

- **La date de début de planning** (E-01, L-06 du 2026-10-28) : `CostStructure.planning_start_on` exigé
  (`schemas:359-384`), avec la règle du défaut, de la copie et du différentiel ; `updateCostStructure`
  (`paths:662-719`) sous `edit_planning` de la structure, `StructureUpdate` (`minProperties: 2`, compteur
  exigé), 200 `NodesWritten` sans nœud écrit, 422 `NON_WORKING_DAY` sur `/planning_start_on` jugé sur le
  calendrier par défaut, `next_working_day` rendu (`structure_start_non_working_day` : samedi 19 → lundi 21
  décembre 2026), horizon (`PROJECT_HORIZON_EXCEEDED`, `params.task`), historique annulable
  (`UndoneKind.structure_update`) ; la variante `structure_planning_start_advanced` tient le Vérif de
  WF-PLA-0020 (958 redatées, 40 récapitulatives, 126 réinflatées, compteur 1 → 2, `nodes` vide) ; le témoin
  date la principale et ses différentiels au 2 mars 2026, les devis propres au 12 janvier, la structure neuve
  au 3 juin (`structures*`, `amendment_created`). `ImportDifferenceField.planning_start_on` et
  `NodeListMeta.scheduled_at` la connaissent.
- **La révision source** (L-05, WF-IHM-0020) : `source_revision_id` et `source_version_name` exigés, nuls pour
  la première révision, conservés une fois marquée ; 102 ← 101 « Référence », 101 ← 100 « Offre v1.0 »,
  100 ← nul, 103 ← nul dans toutes les fixtures.
- **Le taux d'inflation et la probabilité conservés** (E-03, L-04) : `Revision.inflation_rate`,
  `win_probability` exigés, lecture seule, avec la règle du brouillon (suit le projet) et de la marquée
  (figée) ; `RevisionSnapshot` réduit à `employed_reference`, `snapshot` rendu par `getRevision` sur une
  marquée seulement (`revision_marked`, `revision_offer`, `revision_marked_merge_offered` le portent, tous
  les brouillons et la liste l'omettent) ; `EmployedReference.hourly_rates` en `HourlyRateImage` (E-11) —
  80,00 et 75,00 de 2026 pour la référence, 78,50 et 73,50 de 2025 pour l'offre, 4 catégories sans provision
  à l'offre et 5 à la référence : l'instantané raconte la chronologie.
- **La fusion** (E-04, E-05, E-10, L-14) : `StructureMerge.description` ; la règle des grandeurs de référence
  et courantes mot pour mot (WF-REV-0050) dans `mergeCostStructure` et `StructureMerge`, le compte rendu qui
  ne distingue pas les deux cas (M-08) ; `ALREADY_EXISTS` sur `/version_name` au dépôt
  (`merge_version_name_taken`, `conflicting_object_id` 101) ; compteurs 3 et 1 du compte rendu sans révision
  en cours contre `structures_amendments` ; 1 et 2 aujourd'hui contre `structures` ; 412 sur le compteur du
  différentiel (`merge_report_stale`, 2) ; `may_create_revision` en 409 ; les cinq motifs d'échec et de compte
  rendu (`ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, `TASK_WITHOUT_WORKING_HOURS`, `LINK_CYCLE` sans horizon,
  `LINK_FORBIDDEN` la récapitulative d'abord, `PROJECT_HORIZON_EXCEEDED` la tâche qui finit la dernière), les
  huit comptes rendus cohérents avec `nodes_amendment` (lignées 664, 665, 666) ; la tâche démarrée conservée
  et terminée (`kept` + `completed_tasks`, `completed_on` nul).
- **L'historique annulable** (E-06, E-07, E-08, L-18) : tenu par le serveur, par révision et par utilisateur,
  le temps du jeton, fini au marquage et à l'abandon, cinquante niveaux ; **la spécification 1.0.1 dit
  désormais la même chose** (WF-IHM-0110 : « il est tenu par le serveur, par révision et par utilisateur, et ne
  survit ni à la fin de la session, ni au marquage, ni à l'abandon ») — la contradiction de L-18 est levée ;
  `UNDO_CONFLICT` avec `conflicting_object_id`/`conflicting_object_label` (`undo_later_change`,
  `redo_later_change`, « Raccordement des borniers ») ; `undo_history_not_empty`/`redo_history_not_empty` ;
  `UndoResult.written` en `NodesWritten`, nul pour un risque ; `UndoneKind` énuméré ; la liste des actions hors
  annulation complète (abandon, réintégration, C-363) ; les refus #732/#795 dans l'ordre de l'énumération,
  leurs quatre exemples.
- **Les refus d'état** (E-12, E-13, E-14, US-0702) : `markRevision`, `abandonRevision`, `createCostStructure`,
  `applyRateUpdate`, `generatePlanningSkeleton` nomment `revision_draft` puis `no_background_task_running`,
  chacun avec son exemple engendré sur la référence 101 ; `createRevision` nomme `project_not_terminal` et
  `no_background_task_running` (`revision_create_background_running`, sur « Extension de la ligne d'essais »,
  bien un projet en chiffrage sans révision) ; `designateReferenceRevision` : `revision_marked` →
  `revision_has_tasks_and_lines` → `REFERENCE_NOT_CORRECTABLE` → `no_background_task_running`, trois exemples ;
  `abandonRevision` porte `lock_version` en paramètre, 412 et `LockVersionInvalid` ;
  `ReferenceDesignation.lock_version` est celui du projet, 412 (`reference_designate_stale`, 6 contre 7 :
  `project.json` porte 7) ; `confirmed` laissé à la garde (400). `RevisionCommand` décrit `mark`, `abandon`,
  `designate_reference`, `merge_structure`, `apply_rate_update`, `generate_skeleton`, `edit_risks`,
  `declare_risk` et les exports ; les fixtures `revision_marking` et `revision_importing` suivent exactement
  `CommandCondition` (le marquage suspend tout, l'import ce qui écrit, les exports restent).
- **`StructureCreate.kind` réduit à `amendment`**, `risk_id` retiré, le devis propre naît avec `createRisk`
  (E-09) ; `is_merged` vrai par survenance (E-22, structure 205) ; `getRateUpdateProposal` « que le référentiel
  ait changé ou non » (E-19) ; `pattern: '\S'` sur les deux noms de version (E-20) ; l'offre v1.0 liste ses
  quatre exports dans `revision_offer` comme dans `revisions` (E-15).
- **La comparaison** (E-02, L-15) : `budgeted_delta` et `reestimated_delta`, comparée moins base, clé nulle
  omise (`comparison_identical` : `[]`) ; les cinq écarts de `comparison.json` recalculés ligne à ligne
  (3 000/3 300, −350/−350, 600 000/600 000 ; 18 300/18 600 et 584 350/584 350) ; `comparison_differences`
  (5 ajoutés, 2 retirés, 5 ancêtres, totaux de la référence entière = ceux de `comparison_volume`, écarts des
  seules lignes retenues : 850 060 = 60 + 250 000 + 600 000) ; `comparison_moved` (`parent` dans `changes`,
  la récapitulative `dates`, `duration`) ; `NodeDifferenceFilter` partagé avec `listNodes` (US-0700/L1) ;
  `ComparedNodeRead` par ancre YAML, `difference` et `changes` toujours rendus ; la paire identique « jamais
  un refus ».
- **Le squelette** : `skeleton_generated` suit WF-PRJ-0030 sur le lotissement par défaut (récapitulative de
  lot rattachée à 714, récapitulative de poste rattachée à 715, deux jalons de fin, le jalon du lot
  prédécesseur fin-début du jalon du poste, nœud 573), compteur 0 → 1, `ancestors`/`rescheduled` vides comme
  le 201 l'annonce ; `main_structure_without_tasks` puis `no_background_task_running` ; `revision_draft` sur
  la référence.
- **La mise à jour des taux** : `rate_update` engendré depuis la grille (78,50 → 80,00 ; 73,50 → 75,00,
  `reference_rate`, `target_year` 2026), `rate_update_none` pour 102 (même année que 101),
  `rate_update_applied` à la version 2, `revision_rate_update_offered` à la version 1 avec
  `apply_rate_update` disponible ; `rate_update_available` et `revision_draft` avec leurs exemples ; la
  permission `revisions.write` dite et motivée (#1351).
- **Les permissions propres** (`revision_mark`, `revision_abandon`, `reference_designate`, `structure_merge`)
  existent dans `PermissionCode` dans l'ordre de WF-ADM-0100 ; `revision_reader` et `revision_estimator`
  montrent la présence/absence par permission.

### Doutes

- **`risk_update` dans l'historique annulable.** WF-IHM-0110 (1.0.1) énumère « création, réexamen et
  suppression de risques », et WF-RIS-0020 fait du libellé, de la description et de la note de mitigation
  des données du projet, que l'abandon d'une révision ne touche pas (`abandonRevision` le dit). Le contrat
  inscrit la modification d'un risque (`updateRisk`) à l'historique (`UndoneKind.risk_update`,
  `undoLastChange` : « création, modification, réexamen, suppression »), ce qui se défend pour la catégorie,
  le sous-projet et la tâche de la provision, qui sont de la révision, moins pour un libellé du projet. À
  trancher par l'auteur, avec la famille H : annuler un `updateRisk` défait-il le libellé ?
- **Le libellé d'un devis propre de risque.** `structures.json` donne à chaque structure `risk` le libellé de
  son risque ; `updateCostStructure` écrit « le libellé » de toute structure, `updateRisk` celui du risque.
  Lequel suit l'autre, et une structure `risk` renommée garde-t-elle son nom ? Rien ne le dit.
- **Le compteur de la structure 201 à 1.** La survenance du 20 février a fusionné un sous-arbre dans la
  structure principale de 102, et `structure_planning_start_advanced` (le 20 février, après la fusion) la lit
  encore à 1, comme `structures` aujourd'hui : une fusion par survenance ne fait donc pas avancer le compteur
  de la structure, ce que la description de `CostStructure.lock_version` (« une cellule, un collage, un
  déplacement, une création, une suppression ») ne dit ni n'exclut. Famille H ; je ne le compte pas.
- **Le compte rendu de fusion lu sans `revisions.write`.** Sur la dernière révision marquée d'un projet sans
  révision en cours, la commande `merge_structure` nomme `may_create_revision` à qui ne peut pas créer la
  révision ; `getStructureMergeReport` dit « Une autre structure est refusée par 409, comme sa fusion » sans
  dire si la lecture du compte rendu est, elle aussi, refusée par `may_create_revision` ou servie (une lecture,
  qui n'écrit rien). Les deux se tiennent ; l'écran n'offre pas la confirmation dans les deux cas.
- **La même année de référence dans le témoin.** `DECISIONS.md:8719-8724` (#1628, US-0701/L2b #1641) dit
  que l'offre et la référence recevront la même année de référence, ce qui retirerait au témoin le récit de
  la mise à jour des taux (`rate_update`) et l'écart réestimé de `comparison` (E-02 ci-dessus). Le raccourci
  reste déclaré ; si #1641 est livré, E-02 perd son exemple témoin, pas sa raison.
- **`listCostStructures` en tableau nu** et **`/revisions/comparison` sous `/revisions/{revision_id}`** : les
  deux doutes du 2026-10-28 restent tels, sans problème constaté.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| E-01 | réglé | `schemas/revisions.yaml:359-384` (`CostStructure.planning_start_on` exigé, :375-384), `paths/revisions.yaml:662-719` (`updateCostStructure`, `StructureUpdate` :472-486, `NodesWritten`, 422 `NON_WORKING_DAY`) ; `DECISIONS.md:9076-9101` |
| E-02 | réglé | `schemas/revisions.yaml:2398-2419` (`budgeted_delta`, `reestimated_delta`, `delta` disparu) ; `comparison*.json` régénérés ; `DECISIONS.md:8737-8751` — mais voir E-01 et E-02 de cette revue pour ce que la description ne dit pas |
| E-03 | réglé | `schemas/revisions.yaml:58-73` (`inflation_rate`, `win_probability` exigés, lecture seule), `:234-244` (`RevisionSnapshot` réduit), `:86-93` (`snapshot` : quand il est rendu) ; `revision_marked`, `revision_offer` portent l'instantané |
| E-04 | réglé | `schemas/revisions.yaml:513-517` (`StructureMerge.description`) |
| E-05 | réglé | `paths/revisions.yaml:861-867` (409 `ALREADY_EXISTS` sur `/version_name`, jugé au dépôt), `merge_version_name_taken.json` |
| E-06 | réglé | `paths/revisions.yaml:2169-2176` (pile serveur, par révision et par utilisateur, session = jeton, fin au marquage et à l'abandon, cinquante) ; **WF-IHM-0110 1.0.1 dit la même chose** ; `DECISIONS.md:9142-9153`, `10095-10101` |
| E-07 | réglé | `paths/revisions.yaml:2199-2206`, `:2256-2263` (`UNDO_CONFLICT`, `conflicting_object_id`/`_label` ; `undo_history_not_empty`, `redo_history_not_empty`) ; `undo_later_change`, `redo_later_change`, `undo_history_empty`, `redo_history_empty` ; `common.yaml:443-447` |
| E-08 | réglé | `schemas/revisions.yaml:2090-2167` (`UndoResult.written` en `NodesWritten`, `UndoneKind` énuméré, `remaining_depth`) |
| E-09 | réglé | `schemas/revisions.yaml:459-470` (`StructureCreate.kind` enum `[amendment]`, sans `risk_id`), `paths/revisions.yaml:610-620` (« Ouvrir un différentiel », le devis propre naît avec `createRisk`) |
| E-10 | réglé | `structure_merge_report_without_current_revision.json:4-5` (3 et 1), égaux à `structures_amendments.json` (211 : 3, 213 : 1) |
| E-11 | réglé | `schemas/revisions.yaml:246-265` (`EmployedReference.hourly_rates` → `HourlyRateImage`), `reference.yaml:667-680` |
| E-12 | réglé | `paths/revisions.yaml:242-257` (409 : `ALREADY_EXISTS` ; `revision_draft` puis `no_background_task_running`, deux exemples), `schemas/revisions.yaml:212-222` (`mark`, `abandon`, `designate_reference` décrits) |
| E-13 | réglé | `paths/revisions.yaml:163-203` (`lock_version` en paramètre :166-174, 409 nommé avec exemple, 412, 422 `LockVersionInvalid`), `:88-106` (`createRevision` 409 : `project_not_terminal`, `no_background_task_running`, `revision_create_background_running`) |
| E-14 | réglé | `paths/revisions.yaml:613-619` (copie de la principale, `unchanged`), `:642-655` (409 nommé, libellé non unique, `structure_create_revision_marked`) |
| E-15 | réglé | `revision_offer.json` liste `export_planning`, `export_estimate`, `export_remaining`, `export_task_tree_image`, comme l'item 100 de `revisions.json` ; engendré (`mocksnapshot`) |
| E-16 | non réglé | `common.yaml:92-103` sans valeur initiale ; offre 100 à 1 dans `revisions.json`, `revisions_marked.json`, `revisions_designation_open.json`, `revision_offer.json` quand 101 passe 2 → 3 au marquage ; aucune décision — **E-09 de cette revue** |
| E-17 | non réglé | `merge_revision_marked_refused.json:2` dit toujours « (revision_marked) » pour une valeur `revision_draft` — **E-08 de cette revue** |
| E-18 | partiellement réglé | ce que la proposition rend après acceptation se lit en creux dans `RevisionCommand.apply_rate_update` et `CommandCondition.rate_update_available` (« chaque catégorie présentée a déjà été acceptée ») ; `target_year` reste facultatif (`schemas:320`) et absent de `rate_update_none.json` — **E-06 de cette revue** |
| E-19 | réglé | `paths/revisions.yaml:345-349` (« que le référentiel ait changé ou non ») |
| E-20 | réglé | `schemas/revisions.yaml:289` (`RevisionMark.version_name`), `:512` (`StructureMerge.version_name`) : `pattern: '\S'` |
| E-21 | non réglé | `paths/revisions.yaml:381-393` : corps en ligne, seul de la famille sans schéma nommé — repris dans **E-03 de cette revue**, avec le compteur facultatif |
| E-22 | réglé | `schemas/revisions.yaml:388-392` (« ou lorsque le devis propre d'un risque l'a été par sa survenance (WF-RIS-0060) ») |
| E-23 | non réglé | `paths/revisions.yaml:428-483` : rien sur une révision en cours en `from`/`to` — **E-07 de cette revue** |
| E-24 | réglé | `schemas/revisions.yaml:311-317` (`ReferenceDesignation.lock_version` exigé, celui du projet), `paths/revisions.yaml:327-335` (412, `reference_designate_stale`) ; `DECISIONS.md:9784-9797` |
| E-25 | sans objet | `DECISIONS.md:8453-8455` et `8533` (US-0640/L3) : « `cycle` reste un paramètre ouvert de `ProblemParams` […] `link` reste ouvert, comme `cycle` et `task` » — décision explicite, que la spécification ne contredit pas ; `Problem.params` (`common.yaml:141-393`) les décrit en prose |
| L-04 | réglé | comme E-03 |
| L-05 | réglé | `schemas/revisions.yaml:74-85` (`source_revision_id`, `source_version_name` exigés, nuls pour la première révision, conservés une fois marquée) ; `listRevisions` les nomme (`paths:6-12`) ; `CalculationContext` écarté par décision (`DECISIONS.md:9108-9111`) |
| L-06 | réglé | comme E-01 |
| L-14 | réglé | `paths/revisions.yaml:783-790` et `schemas/revisions.yaml:494-498` (grandeurs de référence, et courantes pour une ligne non démarrée jamais réestimée) ; `StructureMergeReport.differences` dit que le compte rendu ne distingue pas (M-08) |
| L-15 | réglé | comme E-02 |
| L-18 | réglé | la spécification 1.0.1 a été corrigée vers le serveur (WF-IHM-0110 : « tenu par le serveur, par révision et par utilisateur ») et le contrat la suit mot pour mot (`paths/revisions.yaml:2169-2176`) ; `DECISIONS.md:9142-9153` |

## Annexe F — L'arbre commun : nœuds, lecture de la grille, écritures de grille, dépendances d'une valeur calculée, résolution d'un numéro de ligne

**Périmètre.** Lu : `docs/api/README-fr.md` (94 lignes, les Conventions en entier) ; `docs/api/paths/revisions.yaml` lignes 896–2165 (les 14 opérations `listNodes`, `createNode`, `resolveRowNumber`, `deleteNode`, `getComputedValueDependencies`, `updateTaskFacet`, `updateEstimateLine`, `setPredecessors`, `setTaskProgress`, `setLineRemaining`, `setNodeTracking`, `moveNodes`, `previewPaste`, `applyPaste`) ; `docs/api/components/schemas/revisions.yaml` lignes 597–2089 (`NodeKind` → `RemainingUpdate`) et 2168–2335 (`PastePreview` → `PasteApply`) ; `docs/api/components/parameters.yaml` lignes 1–36 et 77–613 (`NodeId`, `RowNumber`, `NodeFields`, `NodeKinds`, les filtres de nœud et de colonne, `NodeSortBy`) ; `docs/api/components/common.yaml` lignes 6–104 (types, `WorkInstant`, `WorkInstantWrite`, `LockVersion`), 141–200 (`Problem`), 394–911 (`ErrorCode`, `FieldProblem`, `ProblemParams`, `ProblemTask`, `ProblemEstimateLine`, `ProblemRisk`, `ProblemMissingColumn`) ; `docs/api/components/responses.yaml` (138 lignes) ; `CommandCondition` de `schemas/projects.yaml` lignes 106–330. Spécification 1.0.1 : §3.2.4–3.2.5 (752–838), §3.4.5.3 (2197–2454), §3.4.5.4 (2456–2595), §3.4.5.5 (2597–2696), §3.5.1 (3100–3116), WF-IHM-0030/0040/0050/0060/0070/0090/0100/0110/0130, WF-DAT-0030/0100, WF-ARC-0020. `DECISIONS.md` : « Arbre commun » et « Calculé contre saisi » (30–93), « Les tâches qu'une écriture redate » (560–594), « L'univers témoin » (1777–1900, 1916–1995, 2457–2660), « Les heures d'une date saisie… » (7639–7699), « Les montants inflation comprise » (8686–8735), « Le réestimé d'une ligne non réestimée » (8753–8787), « L'arbre commun : récapitulatives, liaisons, colonnes… (US-0701/L3) » (9245–9372), « Une seule forme pour chaque refus (US-0702/L1) » (9649–9776, grep ciblé), « Les refus sans code ni exemple… (US-0702/L2) » (9777–9867), « Les tâches qu'un reste à engager termine » (9976–9993), « La catégorie sous une nature désactivée… (US-0660/L1) » (9995–10024), « Collage et annulation » (10076–10100), la décision C-359 (6538–6552). Revue du 2026-10-28 : annexe F (2200–2377), L-07 à L-13 (3388–3429), M-08 (3854–3870), Doutes de L (3512–3519). Générateurs : `tools/src/wftools/mockdeclared.py` (140–190). **Fixtures ouvertes : 136**, toutes celles que les 14 opérations référencent (`fixtures/api/`, dont `volume/nodes_thousand.json`, `volume/summary_dependencies.json`, `volume/task_lengthened.json`), avec un script de cohérence (`revue/digest.py`) : totaux de `NodeTotals` contre la somme des lignes rendues, montants des tâches contre leurs lignes et subordonnées, marge et criticité des récapitulatives contre leurs subordonnées, `started_on`/`completed_on` contre l'état, `computed_fields`/`editable_fields` contre la nature des lignes, `remaining_entry` des provisions et des lignes de tâches terminées, recoupements `nodes`/`ancestors`/`rescheduled`/`reinflated` des 38 `NodesWritten`, et montants « inflation comprise » recalculés à 3 % depuis 2026 sur les 5 000 lignes du volume.

### Synthèse

La famille a changé de visage depuis le 28 octobre : les dix-neuf constats de l'annexe F et leurs doublons L-07 à L-13 et M-08 sont réglés, à une exception partielle (F-17, l'exemple du 409 d'`applyPaste`). `TaskFacet` exige la marge, la criticité et `link_conflicts` ; `NodeColumn` porte les dates de démarrage et de terminaison et a perdu `progress` ; `listNodes` filtre chacune des colonnes des trois grilles selon la convention du README ; le libellé composé, la catégorie tenue du rôle, la provision non réestimable, `DUPLICATE_PREDECESSOR`, `task_not_started`, `at_least_one_task`, `UNKNOWN_TIMELINE`, `SUMMARY_TASK_DERIVED` sur `setTaskProgress` et le jalon terminé daté sont dans le contrat avec leurs exemples. Les 136 fixtures sont cohérentes entre elles au centime : chaque `NodeTotals` somme exactement les lignes rendues (le décompte ignore les ancêtres rendus pour la lisibilité), chaque tâche somme ses lignes et ses subordonnées, chaque récapitulative porte la plus petite marge et la criticité de ses subordonnées, les 38 enveloppes `NodesWritten` ne rendent aucun nœud à deux places interdites, et le réestimé des 3 937 lignes du volume consommées après 2026 vaut le montant de base composé à 3 % par an — au cent près sur 71 lignes, par un arrondi au pair que rien ne prescrit.

Ce qui reste tient à quatre règles de la spécification que le contrat ne porte pas ou qu'une fixture contredit : les lignes d'une tâche terminée restent saisissables au contrat (`editable_fields`, `updateEstimateLine`, `deleteNode`) quand WF-DEV-0050 et WF-RAE-0040 les refusent ; une suppression du témoin (`node_deleted_provision_moved`) termine une récapitulative non démarrée et la date dans le passé, contre « rien ne se termine seul » ; la création d'une tâche datée exige encore les heures que le front ne connaît pas (`TaskFacetWrite.start` en `WorkInstant`), alors que la modification les complète ; le jalon qui recevrait une sous-tâche n'a aucun refus ; les lignes propres ouvertes d'une récapitulative dont toutes les subordonnées sont terminées, signalement de WF-PLA-0040 et WF-IHM-0070, n'ont aucun attribut. Le reste est de description : arrondi des montants, année de consommation d'une tâche à cheval, date de terminaison d'une récapitulative, `RemainingUpdate.reason`, 409 génériques, paramètres muets.

**12 constats : 0 bloquant, 5 majeurs, 7 mineurs. Suivi des 27 constats du 2026-10-28 (F-01 à F-19, L-07 à L-13, M-08) : 26 réglés, 1 partiellement réglé (F-17), 0 non réglé, 0 sans objet.**

### Constats

#### F-01 — Les lignes d'une tâche terminée restent saisissables au contrat
- **gravité** : majeur (à la frontière du bloquant : le sens d'`editable_fields` est contraire à la règle)
- **emplacement** : `docs/api/components/schemas/revisions.yaml:658-680` (`Node.editable_fields` : la seule règle liée à l'état d'une tâche est le sous-projet d'une ligne d'une tâche démarrée ou terminée), `:1678-1686` (`remaining_entry`, la seule saisie que l'état terminé ferme) ; `docs/api/paths/revisions.yaml:1536-1554` et `:1584` (`updateEstimateLine`, 409 commun `Conflict`, aucune condition nommée), `:1288-1314` et `:1345-1361` (`deleteNode` : `task_not_started` ne vaut que pour une tâche ; rien pour une ligne dont la tâche est terminée), `:2168-2201`, `:2238-2286` (`PastePreview`, `PasteRejection` : aucun motif pour une cellule collée sur une ligne d'une tâche terminée) ; `fixtures/api/nodes.json:8` (« Ingénierie de détail », ligne des « Études de détail » terminées : `editable_fields` à `label, cost_category_id, quantity, unit_disbursement, payment_delay_days, subproject_id`), de même `nodes_estimate.json` (« Frais de relance », « Affrètement » sous des tâches terminées), `nodes_core.json`, `volume/nodes_thousand.json`
- **spécification** : `WF-DEV-0050-A` (2536) — « Elle permet de créer, modifier, déplacer et supprimer des lignes — sauf sous une tâche terminée, qui se rouvre d'abord depuis le Kanban (WF-RAE-0030) » ; `WF-RAE-0040-A` (2681) — « Les lignes des tâches terminées ne sont pas modifiables » ; Vérif (2683) : « La modification d'une ligne portée par une tâche terminée est refusée »
- **le contrat dit** : la création sous une tâche terminée et le déplacement vers elle ou depuis elle sont refusés par 409 `task_not_completed` (`createNode:1175-1190`, `moveNodes:1968-1982`, exemples `estimate_line_completed_refused`, `nodes_move_completed_refused`) ; la réestimation l'est par `remaining_entry` ; mais la modification (`updateEstimateLine`) et la suppression (`deleteNode`) d'une ligne d'une tâche terminée n'ont aucun refus déclaré, et le nœud dit d'avance qu'il accepte tous ses champs
- **la fixture dit** : « Ingénierie de détail » (`nodes.json:8`), sous une tâche `completed`, nomme six champs saisissables et `remaining_entry.missing_conditions: [task_not_completed]` : la grille de devis offrirait le libellé, la quantité, le débours, le délai et le sous-projet, et la grille de reste à engager refuserait la charge — deux lectures d'une même règle
- **décision** : `DECISIONS.md:79-80` « une ligne de devis dit si elle accepte une réestimation (`remaining_entry`) : sous une tâche terminée, elle ne l'accepte plus » et `:6544-6545` « une tâche terminée retient ses lignes comme une tâche démarrée » (sous-projet) — les deux décisions ne traitent que la réestimation et le sous-projet ; aucune n'assume la saisie des autres champs d'une ligne d'une tâche terminée, et la spécification 1.0.1 la refuse sans réserve
- **proposition** : dire dans `Node.editable_fields` qu'une ligne dont la tâche est terminée n'en nomme aucun (ou le seul libellé, à trancher avec l'auteur : WF-DEV-0050 dit « modifier » sans réserve) ; déclarer dans le 409 d'`updateEstimateLine` et de `deleteNode` la condition `task_not_completed` (déjà dans `CommandCondition`) pour une ligne dont la tâche est terminée, « qui se rouvre d'abord depuis le Kanban », avec un exemple engendré (`estimate_line_completed_update_refused`, `node_delete_line_completed_refused`) ; dans `PastePreview`/`PasteRejection`, dire le motif d'une cellule non vide collée sur une telle ligne (`FIELD_NOT_ACCEPTED`, ses `editable_fields` étant vides, à confirmer) ; régénérer les lectures (`mockcore`) pour que les lignes des tâches terminées portent des `editable_fields` conformes

#### F-02 — Une suppression du témoin termine une récapitulative et la date dans le passé
- **gravité** : majeur
- **emplacement** : `fixtures/api/node_deleted_provision_moved.json:9` (ancêtre « Installation sur site » : `progress: completed`, `started_on: 2026-03-02`, `completed_on: 2026-03-13`, `start/finish` du 2 au 13 mars 2026, `physical_progress.value: "1"`), `:11` (`rescheduled` : « Mise en service » replanifiée du 2 au 13 mars 2026), `:2` (résumé : « les totaux de la structure, 4 998 lignes, 116110 h, … inchangés ») ; contre `fixtures/api/nodes_installation.json:6,10` (« Installation sur site » et « Mise en service » `not_started`, du 1er juillet 2026 au 1er janvier 2027) ; `docs/api/paths/revisions.yaml:1288-1314`, `:1329-1341` (`deleteNode`, exemple `provision_moved`) ; générateur `tools/src/wftools/mockdeclared.py:148-190`
- **spécification** : `WF-RAE-0030-A` (2663) — « rien ne se termine seul » ; `WF-PLA-0130-A` (2321) — les dates de démarrage et de terminaison sont « renseignées lors du changement d'état » ; `WF-PLA-0020-A` (2249) — « Une tâche en mode automatique sans prédécesseur commence à cette date [de début de planning] » ; `WF-PLA-0070-A` (2309)
- **le contrat dit** : « Les lignes de provision … passent sur la tâche parente … `nodes` les rend écrites sous leur tâche nouvelle, `ancestors` cette tâche et ses ancêtres » ; `NodesWritten.ancestors` : les ancêtres « recalculés : montants, dates, durée, avancement » (`schemas:1140-1152`) ; l'invariant du témoin (`DECISIONS.md:1975-1976`) « interdit à toute écriture engendrée de changer l'avancement ou les dates d'une tâche démarrée ou terminée »
- **la fixture dit** : la suppression du montage retire à la « Mise en service » son seul prédécesseur ; elle revient au 2 mars 2026, date de début de planning, dans le passé ; le générateur (`mockcore.current`, « le générateur tient chaque fin automatique passée pour un geste fait à sa date », `DECISIONS.md:2485-2489`) la tient alors pour terminée, et la récapitulative « Installation sur site », non démarrée dans le témoin, est rendue terminée, datée, avancement physique à 1 : une suppression qui termine deux tâches et acquiert de la valeur. Le résumé dit les totaux « inchangés » alors qu'ils perdent les 12 600,00 (160 h) des deux lignes du montage (66 105 223,89 → 66 092 623,89) — le mot vise sans doute le budget de la provision, mais il contredit les chiffres qu'il précède
- **décision** : `DECISIONS.md:9829-9836` (US-0702/L2 : « Le déplacement a son exemple engendré, `node_deleted_provision_moved` (L-11) : variante contrefactuelle du témoin … `nodes` rend la ligne sous sa tâche parente ») — la décision fixe la forme, pas ces dates ; elle est tenue, la fixture ne l'est pas
- **proposition** : régénérer la variante en gardant à la « Mise en service » un prédécesseur (la réception usine, comme `predecessor_set`) ou en figeant son avancement à `not_started`, pour que l'ancêtre reste non démarré et qu'aucune date passée ne naisse d'une suppression ; corriger le résumé (« les totaux de la structure diminuent des deux lignes du montage, 12 600,00 ; le budget de la provision ne bouge pas ») ; ajouter au test d'invariant (`DECISIONS.md:1975`) qu'une écriture engendrée ne change l'avancement d'aucune tâche, démarrée ou non

#### F-03 — La création d'une tâche datée exige les heures que le front ne connaît pas
- **gravité** : majeur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:1822-1825` (`TaskFacetWrite.start`, `finish` : `WorkInstant`), `:1806-1811` (« le début et la fin, saisissables en mode manuel, sont une date et des heures de travail écoulées (WF-DAT-0100) ») ; `docs/api/components/common.yaml:44-55` (`WorkInstant`, `required: [date, hours]`), `:57-80` (`WorkInstantWrite`, `hours` facultatif, « Le client ne connaît pas le calendrier applicable (WF-PLA-0010) : sans `hours`, le serveur les complète ») ; `:1880-1883` (`TaskFacetUpdate.start`, `finish` : `WorkInstantWrite`) ; `docs/api/paths/revisions.yaml:1141-1145` (`createNode` : une date chômée « est refusée comme à la modification (`updateTaskFacet`) ») ; fixture `node_create_non_working_day.json` (refus sur `/task/start/date`), aucune création datée acceptée en exemple
- **spécification** : `WF-PLA-0010-A` (2237) — le calendrier applicable est celui des rôles des lignes de la tâche, résolu par le serveur ; `WF-ARC-0020-A` (3601) — « Il ne porte aucune règle métier, aucun calcul » ; `WF-PLA-0020-A` (2249) — « En mode manuel, l'utilisateur saisit ses dates »
- **le contrat dit** : à la modification, « le début et la fin se saisissent par leur seule date : le serveur en complète les heures sur le calendrier applicable » (`updateTaskFacet:1448-1450`) ; à la création, `hours` est exigé — le front doit inventer `0` et les heures de fin d'un jour dont il ne connaît pas le calendrier (une tâche créée avec une ligne de main-d'œuvre au même instant n'a pas encore de calendrier connu du client), et des heures hors du jour sont refusées par `VALUE_OUT_OF_RANGE` sans qu'il puisse les prévoir
- **décision** : `DECISIONS.md:7641-7651` (#1244) — « L'entrée de `updateTaskFacet` prend un schéma propre, `WorkInstantWrite` … `WorkInstant` reste celui des lectures » : la création n'est pas traitée ; la revue du 28 octobre (annexe F, Doutes) le signalait au consolidateur, et #1345 (`createNode`, jour chômé) a touché `createNode` sans la reprendre ; aucune décision n'assume la différence
- **proposition** : `TaskFacetWrite.start` et `finish` en `WorkInstantWrite`, avec la même phrase que `TaskFacetUpdate` (« sans leurs heures, que le serveur complète sur le calendrier de la tâche — le calendrier par défaut pour une tâche créée sans ligne ») et le même 422 (`/task/start/hours` par `VALUE_OUT_OF_RANGE`) ; un exemple de création en mode manuel daté (`node_created_manual`). Passer `hours` d'exigé à facultatif est compatible pour les clients ; le laisser exigé jusqu'au gel fige la règle contraire

#### F-04 — Une sous-tâche créée ou déplacée sous un jalon n'a aucun refus
- **gravité** : majeur
- **emplacement** : `docs/api/paths/revisions.yaml:1117-1145` (`createNode` : « Une tâche créée sous une feuille en mode manuel fait de celle-ci une récapitulative » ; rien sur un jalon), `:1191-1227` (son 422), `:1916-1940`, `:1984-2020` (`moveNodes` et son 422) ; `docs/api/components/schemas/revisions.yaml:1778-1800` (`NodeCreate.parent_id`), `:1988-2030` (`NodeMove.parent_id`) ; `common.yaml:394-707` (aucun code pour ce refus)
- **spécification** : `WF-PLA-0050-A` (2297) — « Un jalon est une tâche feuille de durée nulle. Il ne porte pas de sous-tâches, mais il peut porter des lignes de devis » ; Vérif (2299) : « Une tâche feuille de durée nulle ne peut recevoir de sous-tâche »
- **le contrat dit** : `parent_id` est « le nœud sous lequel le nœud créé prend place » ; les refus déclarés tiennent au frère (`NODE_NOT_SIBLING`), au lotissement, à la boucle, à l'horizon, aux heures ; une tâche créée ou déplacée sous un jalon ferait de lui une récapitulative — ce que `moveNodes` décrit pour toute feuille (« une feuille en mode manuel qui reçoit une subordonnée devient une récapitulative ») sans excepter le jalon
- **la fixture dit** : aucune fixture ne crée ni ne déplace sous un jalon
- **décision** : aucune (grep « jalon » × « sous-tâche », « recevoir » : seules les lignes 8818 et 9423 disent qu'un jalon porteur de provision « reste un jalon sans sous-tâche » à la survenance, règle du serveur, pas un refus de saisie)
- **proposition** : à trancher entre un 422 `VALIDATION_FAILED`, `fields` sur `/parent_id`, motif nouveau `MILESTONE_HAS_NO_SUBTASK` (`createNode`, `moveNodes`, et le motif d'une ligne importée qui placerait une tâche sous un jalon), et un 409 `STATE_FORBIDS_OPERATION`, condition nouvelle `parent_not_milestone` ; la première forme suit les refus de placement voisins (`NODE_NOT_SIBLING`) ; un exemple engendré, la « Note de calcul des protections » créée sous la « Réception des études »

#### F-05 — Les lignes propres ouvertes d'une récapitulative n'ont aucun attribut
- **gravité** : majeur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:1342-1523` (`TaskFacet` : aucun champ ne dit qu'une récapitulative démarrée n'attend plus que ses lignes propres), `:1678-1686` (`EstimateLineFacet.remaining_entry` : ouvert ou fermé, sans dire que la ligne est l'une des « seules lignes ouvertes de la phase ») ; `docs/api/components/parameters.yaml:164-174` (`NodeProgressFilter` : la grille de reste à engager « ne montre par défaut que leurs lignes [des tâches démarrées] »)
- **spécification** : `WF-PLA-0040-A` (2285) — « Tant que ce reste n'est pas nul, elle reste démarrée et ses lignes propres hors provision sont exposées à la réestimation, signalées, dans la grille de reste à engager et dans le Kanban, comme seules lignes ouvertes de la phase » ; Vérif : « Une récapitulative dont toutes les subordonnées sont terminées et dont une ligne propre porte un reste à engager de 500 est démarrée et signalée » ; `WF-IHM-0070-A` (3263) compte « lignes propres hors provision d'une récapitulative dont toutes les subordonnées sont terminées (WF-PLA-0040) » parmi les signalements de l'échelle commune ; `WF-ARC-0020-A` (3601)
- **le contrat dit** : rien ; la grille devrait déduire le signalement de l'état des subordonnées — que la lecture par défaut du reste à engager (`progress=started`) ne rend pas, les subordonnées terminées en étant écartées — et le Kanban (`KanbanTask`, `analysis.yaml`) n'en porte pas davantage
- **la fixture dit** : aucune récapitulative du témoin n'est dans ce cas ; la lecture `nodes_estimate` montre « Risque survenu — Retard de livraison des armoires », terminée sans ligne propre, seule situation voisine
- **décision** : aucune ; la revue du 28 octobre le tenait pour un doute « à confirmer par la famille RAE » (`2026-10-28-contrat-avant-gel.md:3516`) ; US-0701/L3 (`DECISIONS.md:9245-9372`) n'en parle pas
- **proposition** : un booléen calculé, toujours rendu, sur `TaskFacet` — `awaiting_own_lines` : « vrai pour une récapitulative démarrée dont toutes les subordonnées sont terminées et dont une ligne propre hors provision garde un reste à engager (WF-PLA-0040) ; la grille de reste à engager et le Kanban la signalent selon l'échelle commune (WF-IHM-0070) » —, repris par `NodeSchedule` ou `ancestors` pour qu'une réestimation qui termine la dernière subordonnée le fasse paraître ; `KanbanTask` le porte par sa facette. Forme à trancher (un `CommandCondition` sur `remaining_entry` ne dirait pas le signalement d'une ligne ouverte, qui est disponible)

#### F-06 — L'arrondi au centime des montants inflation comprise n'est pas dit, et les fixtures arrondissent au pair
- **gravité** : mineur
- **emplacement** : `docs/api/components/common.yaml:18-22` (`Money`, « à deux décimales », sans règle d'arrondi) ; `docs/api/components/schemas/revisions.yaml:1622-1639` (`EstimateLineFacet.reestimated_amount` : « composé une fois par année écoulée »), `:1608-1621` (`budgeted_amount`) ; `README-fr.md`, convention « Une part, un avancement ou un taux calculé … arrondi au plus proche, une demie s'éloignant de zéro » (les rapports seulement) ; `fixtures/api/volume/nodes_thousand.json:1402` (« Matériel », base `8603.50`, 2027 : 8 603,50 × 1,03 = 8 861,605 rendu `8861.60`) et 70 autres lignes du volume (`4982.6250` → `4982.62`, `12207.0450` → `12207.04`…), budgété comme réestimé
- **spécification** : `WF-DAT-0100-A` (3975) — « Les montants sont des décimaux exacts à deux chiffres après la virgule » ; `WF-DEV-0030-A` (2552) — « projeté … par application composée du taux d'inflation » ; Vérif de WF-DEV-0050 (4,04 %)
- **le contrat dit** : le mode de calcul (composition annuelle, chaque part d'une tâche à cheval projetée sur son année), mais pas la règle qui ramène le produit au centime
- **la fixture dit** : sur les 3 937 lignes du volume consommées après 2026, le réestimé vaut exactement `base × 1,03^n` arrondi ; 71 cas tombent sur une demie et sont tous rendus au pair (`ROUND_HALF_EVEN`), aucun à la demie supérieure : un serveur qui appliquerait la règle du README aux montants rendrait un centime de plus sur ces 71 lignes, et les totaux (`68923691.06`) différeraient des fixtures
- **décision** : `DECISIONS.md:8686-8735` (L-01) fixe les trois montants et leur projection, sans arrondi ; aucune décision sur l'arrondi d'un `Money`
- **proposition** : dire dans `Money` (ou dans `reestimated_amount`/`budgeted_amount`) la règle de l'arrondi au centime du montant projeté — au plus proche, une demie s'éloignant de zéro, comme les parts du README —, et aligner `mockdating.price` ; ou documenter l'arrondi au pair si c'est le choix retenu

#### F-07 — L'année de consommation d'une ligne d'une tâche à cheval sur deux années
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:1663-1665` (`EstimateLineFacet.consumption_year` : « Année de consommation, déduite du planning (WF-DEV-0040) », un seul `Year`), `:1274-1278` (`NodeInflation.consumption_year`), `:921` (`NodeColumn.consumption_year`) ; `docs/api/components/parameters.yaml:368-383` (`consumption_year_min/_max`) ; `fixtures/api/volume/nodes_thousand.json` (23 tâches feuilles à cheval sur deux années, dont toutes les lignes portent l'année du début de la tâche)
- **spécification** : `WF-DEV-0040-A` (2564) — « Lorsque la tâche s'étend sur plusieurs années, le montant de la ligne est réparti entre ces années au prorata de ses heures travaillées dans chaque année … et chaque part est projetée sur son année »
- **le contrat dit** : `reestimated_amount` (1634-1636) connaît « chaque part d'une tâche à cheval sur plusieurs années projetée sur la sienne », mais la colonne et le filtre `consumption_year` ne portent qu'une année, sans dire laquelle (celle du début ? de la plus grande part ?) ; une ligne à cheval sur 2026 et 2027 est retenue ou non par `consumption_year_min=2027` selon une règle que personne ne lit
- **la fixture dit** : l'année du début de la tâche, par la simplification déclarée du générateur (`DECISIONS.md:1962-1964` : « une ligne est consommée l'année où sa tâche commence »)
- **décision** : `DECISIONS.md:1962-1964` (simplification du témoin, déclarée) ; aucune décision sur la valeur rendue par le contrat pour une ligne à cheval
- **proposition** : dire dans `consumption_year` : « l'année de la première part de la ligne — celle du début de la tâche — quand la tâche s'étend sur plusieurs années, ses montants étant projetés part par part (WF-DEV-0040) ; le filtre retient la ligne sur cette année », ou rendre les années de la ligne en liste (à trancher ; une liste change la colonne et le filtre, à décider avant le gel)

#### F-08 — La date de terminaison d'une récapitulative n'est pas décrite
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:1399-1404` (`TaskFacet.completed_on` : « Date de terminaison, qui situe la valeur acquise dans le temps (WF-IND-0030), nulle pour une tâche qui n'est pas terminée ») ; `:1389-1398` (`started_on` dit la règle de la récapitulative : « celle de la première de ses subordonnées démarrées »)
- **spécification** : `WF-PLA-0130-A` (2321) — « une tâche récapitulative prend … pour date de terminaison la plus tardive de celles de ses subordonnées et de la mise à zéro de ses lignes propres » ; Vérif : « une récapitulative porte la date de terminaison de sa dernière subordonnée »
- **le contrat dit** : la règle du démarrage, pas celle de la terminaison ; les fixtures la suivent (« Risque survenu — Retard de livraison des armoires » terminée le 15 mai, date du « Transport exceptionnel », `nodes_estimate.json`)
- **décision** : `DECISIONS.md:9343-9350` (US-0701/L3, F-13) décrit `started_on` ; rien sur `completed_on`
- **proposition** : compléter `completed_on` : « Une récapitulative porte la plus tardive des dates de terminaison de ses subordonnées et de la mise à zéro de ses lignes propres hors provision (WF-PLA-0130) »

#### F-09 — `RemainingUpdate` : un `reason` sans règle, des grandeurs sans règle de champ absent, un 422 incomplet
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:2074-2075` (`RemainingUpdate.reason`, chaîne nullable sans description), `:2065-2073` (`reestimated_amount_basis` : `quantity`, `hours`, `unit_disbursement`, aucun `required`, « Les grandeurs saisies dont le montant réestimé est recalculé ») ; `docs/api/paths/revisions.yaml:1824-1833` (422 de `setLineRemaining` : `COMPLETION_DATE_REQUIRED` seul)
- **spécification** : `WF-RAE-0040-A` (2681) — « La réestimation se saisit sur les grandeurs, et le montant suit » ; aucune exigence ne nomme un motif de réestimation ; `WF-DEV-0010-A` (2492) — « Le calcul d'un devis ou d'un reste à engager est refusé tant qu'une catégorie de coût de main-d'œuvre … n'a pas de taux horaire » ; `WF-DEV-0020-A` Vérif — « Une ligne de main-d'œuvre refuse la saisie d'un débours »
- **le contrat dit** : `reason` n'est ni décrit, ni cité par une opération, ni relu nulle part (`EstimateLineFacet` ne le rend pas ; aucune fixture ne l'envoie) ; une grandeur absente de `reestimated_amount_basis` garde-t-elle sa valeur, comme « seul ce qui est envoyé change » le dit pour `EstimateLineUpdate` ? Un débours envoyé pour une ligne de main-d'œuvre, une quantité négative, une catégorie sans taux : les motifs `FIELD_NOT_ACCEPTED`, `VALUE_OUT_OF_RANGE` et `HOURLY_RATE_MISSING`, déclarés par `updateEstimateLine` (1586-1609), ne le sont pas ici, et la description du 422 n'a même pas la phrase commune « ou une valeur hors règle, `fields` la localisant »
- **décision** : aucune (grep `reason` : seuls `NotComputableReason` et `StateTransition.reason`)
- **proposition** : décrire `reason` (le motif libre de la réestimation, conservé par la revue, relu où ?) ou le retirer avant le gel ; dire que `reestimated_amount_basis` suit la règle de la cellule (un champ absent reste ce qu'il était ; un champ que la ligne n'accepte pas est refusé par `FIELD_NOT_ACCEPTED`) ; compléter le 422 par `HOURLY_RATE_MISSING`, `FIELD_NOT_ACCEPTED`, `VALUE_OUT_OF_RANGE` et la phrase commune

#### F-10 — Trois 409 génériques, un 409 sans exemple
- **gravité** : mineur
- **emplacement** : `docs/api/paths/revisions.yaml:1489` (`updateTaskFacet`, `'409': Conflict`), `:1584` (`updateEstimateLine`), `:1662` (`setPredecessors`), `:2139-2149` (`applyPaste` : 409 décrit, sans exemple) ; `docs/api/components/responses.yaml:53-63` (`Conflict`, description générique, aucun exemple)
- **spécification** : `WF-IHM-0090-A` (3287) — « Tout refus nomme la condition manquante » ; README, convention du 409 : « `params.missing_condition` nommant la condition qui manque, celle que l'objet dit d'avance de sa commande »
- **le contrat dit** : `createNode`, `deleteNode`, `setTaskProgress`, `setLineRemaining`, `setNodeTracking`, `moveNodes` et `applyPaste` nomment leurs conditions dans l'ordre (`revision_draft`, `no_background_task_running`, puis la condition propre) ; `updateTaskFacet`, `updateEstimateLine` et `setPredecessors`, écrits sous `edit_planning` et `edit_estimate`/`edit_remaining`, renvoient à la réponse commune, sans dire quelle commande ni quelles conditions (pour `updateEstimateLine`, la tâche terminée de F-01 s'y ajoute) ; le 409 d'`applyPaste` est le seul des quatorze sans exemple, et le faux back ne le sert pas
- **décision** : `DECISIONS.md:9649-9776` (US-0702/L1, « une seule forme pour chaque refus ») a traité les refus nommés par la revue ; ces trois 409 n'y sont pas ; `:9763` « Le 409 d'`applyPaste` est décrit » — décrit, non exemplifié (reste de F-17)
- **proposition** : décrire les trois 409 comme ceux de `setNodeTracking` (`revision_draft`, `no_background_task_running`, et pour `updateEstimateLine` `task_not_completed`), chacun avec un exemple engendré (`task_update_marked_refused`, `estimate_line_update_marked_refused`, `predecessors_marked_refused`), et un exemple du 409 d'`applyPaste` (`paste_apply_marked_refused`)

#### F-11 — Paramètres et défauts muets
- **gravité** : mineur
- **emplacement** : `docs/api/components/parameters.yaml:154-157` (`NodeCostCategoryFilter`), `:159-162` (`NodeResourceRoleFilter`), `:176-179` (`NodeCriticalFilter`) : les trois seuls paramètres de `listNodes` sans description ; `docs/api/components/schemas/revisions.yaml:1930-1931` (`EstimateLineWrite.payment_delay_days`, nullable, sans défaut dit pour une ligne hors main-d'œuvre), `:1923` (`quantity`, exigée, sans dire qu'une ligne de main-d'œuvre la porte à `1` par défaut à l'écran)
- **spécification** : `WF-DEV-0020-A` (2504) — « un délai de paiement, en jours, qui vaut zéro par défaut pour une ligne de main-d'œuvre et reste saisissable sur toute ligne autre qu'une ligne de provision » ; `WF-IHM-0130-A` (3335)
- **le contrat dit** : un filtre par catégorie ou par rôle « retient les lignes » (description de `listNodes:921-923`), un filtre `is_critical` les tâches, mais le paramètre lu seul ne le dit pas, et ne cite aucune exigence ; `EstimateLineUpdate:1947-1949` dit le défaut nul de la main-d'œuvre, `EstimateLineWrite` non ; absent sur une ligne hors main-d'œuvre, le délai vaut-il `null` ou `0` ? Les fixtures tirées portent 30 jours (`DECISIONS.md:2490-2492`), valeur du générateur, non du contrat
- **décision** : `DECISIONS.md:9282-9308` (US-0701/L3, filtres) décrit les filtres nouveaux, pas les trois anciens
- **proposition** : une description par paramètre (« Restreint aux lignes de cette catégorie de coût (WF-DEV-0050) », « … de ce rôle de ressource (WF-DEV-0050) », « Vrai, restreint aux tâches du chemin critique, faux aux autres ; absent, ne restreint rien (WF-PLA-0080, WF-PLA-0100) ») ; dire dans `EstimateLineWrite.payment_delay_days` le défaut d'une ligne absente (`0` pour toute ligne, ou `null` hors main-d'œuvre : à trancher)

#### F-12 — Deux fixtures qui disent moins juste que le contrat
- **gravité** : mineur
- **emplacement** : `fixtures/api/nodes_amendment.json:9` (« Assistance aux essais de câblage », `difference: removed`, `editable_fields: []`, mais `remaining_entry: {is_available: true, missing_conditions: []}`), de même `nodes_amendment_differences.json` ; `fixtures/api/nodes_estimate.json:2` (résumé : « rattachée au lot « Lot 1 » du lotissement (WF-PLA-0130) ») ; `docs/api/components/schemas/revisions.yaml:699-714` (`NodeDifference.removed` : « en lecture seule (`editable_fields` vide) »), `:1678-1686` (`remaining_entry`)
- **spécification** : `WF-REV-0100-A` (différentiel) ; `WF-PLA-0170-A` (2333), qui porte seule le rattachement depuis la passe du 10 octobre
- **le contrat dit** : un nœud retiré « n'accepte aucun champ » et le collage le refuse entier (`PASTE_TARGET_REMOVED`) ; sa `remaining_entry` dit pourtant la réestimation disponible, sans condition : la grille de reste à engager d'un différentiel offrirait la cellule d'une ligne que le différentiel a retirée. Le résumé de `nodes_estimate` cite WF-PLA-0130 pour le rattachement, que WF-PLA-0130 renvoie désormais à WF-PLA-0170
- **décision** : `DECISIONS.md:6927` (nœuds retirés, #1205) ; rien sur `remaining_entry` d'un nœud retiré
- **proposition** : `remaining_entry.is_available: false` pour un nœud retiré, avec une condition à nommer (à trancher : `node_not_removed`, ou réemployer `revision_draft` est faux) et une phrase dans `NodeDifference` ; corriger la citation du résumé (`mockcore`/`mocktext`) en WF-PLA-0170

### Ce qui est juste

Vérifié conforme, en particulier ce que la revue du 28 octobre relevait :
- **`TaskFacet`** exige `total_float`, `is_critical` et `link_conflicts` (1344-1360) ; les récapitulatives du témoin portent la plus petite marge et la criticité de leurs subordonnées (« Études » 0 j, critique ; « Risque survenu » 858,5 j, non critique ; « Installation sur site » 597,5 j), et `ComputedDependency.subordinates` le dit. Le mode d'une récapitulative est dans `computed_fields` (`task.scheduling_mode`) et refusé par `COMPUTED_VALUE` ; `started_on` d'un jalon terminé vaut `completed_on` (`milestone_completed`), un jalon rouvert perd les deux (`milestone_reopened`) ; `calendar_id` nul pour une intersection (`estimate_line_redated`), `calendar_hours` porte le moins généreux des calendriers (montage : lundi–jeudi 8 h, vendredi 0).
- **Le conflit d'une liaison** (`LinkConflict`, `task_dates_conflicting`) : la tâche manuelle « Préparation 1.2.17 » et son prédécesseur « Reprise 1.2.14 » nomment la même liaison, le prédécesseur porte −6 j et est critique, la chaîne qui le précède (8 tâches, les études comprises) est dans `rescheduled` avec −6 j, et les récapitulatives au-dessus portent −6 j.
- **`NodeColumn`** : `started_on`, `completed_on` après `is_critical`, `progress` retiré ; `paste_too_wide` compte juste 16 colonnes de `label` à `previous_reestimated_amount` ; `max_columns` à 16 pour 17 collées.
- **`listNodes`** : les 43 filtres de colonne existent avec leur description, leur exigence et leur type (décimaux en chaîne, `Hours`, `Money`, `Year`, `PlanningDate`) ; les deux refus `nodes_bounds_inverted` (`/query/reestimated_amount_max`, `minimum: "10000.00"`) et `nodes_period_inverted` (`/query/start_to`, `minimum: "2026-05-01"`) suivent le README ; `fields` inconnu est un 422 `FIELD_NOT_ACCEPTED` sur `/query/fields`, et le 400 a disparu des deux lectures à paramètres ; `nodes_estimate_filtered` retient deux lignes, leurs tâches pour la lisibilité et des totaux de 2 234,56 ; `kinds` n'est pas un filtre (`nodes_planning` : totaux de la ligne non rendue) ; `nodes_timeline` sans ancêtres ; `summary_depth` 3 quel que soit `max_level` (`nodes_summaries`), 0 sans récapitulative.
- **Les totaux** : sur les 19 lectures, `NodeTotals` somme exactement les heures et les trois montants des lignes rendues et compte les tâches et lignes retenues hors ancêtres de lisibilité ; `nodes_amendment_differences` garde les totaux du différentiel entier (1 002 tâches, 5 000 lignes) ; chaque tâche somme ses lignes et ses subordonnées (`nodes_estimate` : 502 434,56 = 502 234,56 + 200) ; la provision budgétée à 250 000,00 et réestimée à 500 000,00 compte aux deux totaux ; `physical_progress` 0 pour « Poste de commande » (rien d'acquis hors provision), non calculable sans budget pour « Risque survenu », 1 pour « Études » puis 0 quand les études de détail sont rouvertes (`task_reopened`).
- **Les 38 `NodesWritten`** : les nœuds écrits avancent seuls de version, `structure_lock_version` suit les suites (`estimate_line_entered` 3 → `paste_applied` 4, `task_attached` 2 → `milestone_completed` 3, `node_created` 2 → `node_created_child` 3 → `node_summary_emptied` 4) ; `nodes` ∩ `ancestors`, `nodes` ∩ `rescheduled`, `ancestors` ∩ `reinflated` sont vides partout ; `estimate_line_redated` rend le montage dans `ancestors` et `rescheduled` comme le contrat l'autorise désormais, et `reinflated` porte la mise en service et sa ligne à 6 180,00 (6 000 × 1,03), budgété 5 880,00 inchangé ; `task_dates_entered` et `volume/task_lengthened` de même ; `predecessor_set` (2 j de décalage, montage du 3 juillet au 22 décembre), `predecessors_entered` (SS + 1 sem, départ le 8 juillet), `task_duration_entered` (3 sem = 15 j, fin le 21 juillet), `task_mode_changed` (le prédécesseur devient critique) ont des dates exactes au calendrier ; `node_deleted` et `node_summary_deleted` retirent 1 234,56 et 18 600,00 des totaux ; `node_summary_emptied` rend la feuille redevenue automatique d'un jour, `editable_fields` rouverts ; `node_tracked` remplace les inscriptions.
- **Les 59 refus** : chacun avec le code, le statut, le pointeur et les paramètres que sa description annonce — `DUPLICATE_PREDECESSOR` sur `/predecessors/1/predecessor_node_id`, `task_not_started` (« Câblage des armoires »), `at_least_one_task` avec `params.risks`, `UNKNOWN_TIMELINE`, `VALUE_REQUIRED` et `MILESTONE_REQUIRED` sur `/entries/<n>/…`, `SUMMARY_TASK_DERIVED` avec ses cinq subordonnées dans l'ordre du plan, `COMPUTED_VALUE` sur `/estimate_line/cost_category_id`, `FIELD_NOT_ACCEPTED` (débours d'une ligne de main-d'œuvre, durée d'un jalon), `RESOURCE_ROLE_REQUIRED`, `HOURLY_RATE_MISSING` avec `missing_rates`, `TASK_WITHOUT_WORKING_HOURS` sur `createNode`, `updateEstimateLine`, `moveNodes` et le collage (deux rôles et la tâche), `NON_WORKING_DAY` avec `next_working_day`, `VALUE_OUT_OF_RANGE` des heures (`minimum: "0"`, `maximum: "8"`), `LINK_CYCLE` ordonné, `PROVISION_LINE_MOVED_BY_RISK` avec le risque, les cinq refus du rattachement, `PASTE_TARGET_REMOVED` à la ligne 0, `STALE_LOCK_VERSION` du collage jugé sur une autre version.
- **Le collage** : `PastePreview` et `PasteRejection` disent le saut des nœuds retirés et le refus entier de l'ancre retirée, les fixtures le montrent (`paste_plan_amendment_skipping`, `paste_plan_amendment_target_removed`) ; `paste_applied_rejudged` rejuge la catégorie désactivée et marque `uses_inactive_object` ; `paste_plan_subproject_held` refuse la cellule qui quitterait le sous-projet et accepte celle qui le nomme.
- **`resolveRowNumber`** et ses trois exemples (tâche, ligne, 6001 inconnu sur 6 000) ; **`getComputedValueDependencies`** et ses dix exemples (dont `labour_category` → `resource_role`, `manual_float` → `manual_mode`, `provision_subproject` → `risk`, `entered` → `params.field`).
- **La réestimation** : `remaining_reestimated` (10 h → 800,00, budgété 1 000,00), `remaining_provision_refused` (`line_not_provision`), `remaining_completed_refused` (`task_not_completed`), `remaining_completion_date_required` (`/completed_on`, `task_node_id`) ; `reestimated_amount` d'une ligne jamais réestimée décrit selon M-08 et WF-RAE-0010.
- **Les codes retirés** : `TASK_ALREADY_STARTED` et `TASK_COMPLETED` ne sont plus au catalogue ; `inflated_amount` a disparu ; `Lag.value` en `percent` dit « 50 pour la moitié ».

### Doutes

- **`task.progress` dans les `editable_fields` des tâches d'un différentiel** (`nodes_amendment` : « Mise en service » nomme `task.progress`) : `setTaskProgress` est « le geste d'une carte du Kanban », qui ne lit que la structure principale (WF-RAE-0030), sous `edit_remaining` de la structure principale ; une tâche d'un différentiel ou du devis propre d'un risque peut-elle changer d'état ? Le contrat ne le dit ni dans un sens ni dans l'autre. À poser à l'auteur.
- **`setTaskProgress` rejoué** (`started` sur une tâche démarrée, `completed` sur une tâche terminée) : refusé par 409 ou accepté sans effet ? Les conditions du 409 ne le couvrent pas.
- **`TaskFacet.start` et `finish` nullables** (1379-1382) : aucune description ne dit quand une tâche est rendue sans dates ; les fixtures n'en ont aucune.
- **La durée négative, la quantité négative** : aucun refus nommé (`Duration.value` « jamais négative pour la durée d'une tâche », sans `minimum`) ; probablement « une valeur hors règle, `fields` la localisant » par `VALUE_OUT_OF_RANGE`, non compté.
- **Les lignes du devis propre d'un risque** nomment `estimate_line.subproject_id` (`nodes_risk_estimate`) : un sous-projet sur une ligne qui n'entre au reste à engager qu'à la survenance, où la fusion « conserve ses grandeurs » (WF-RIS-0060) — garde-t-elle son sous-projet ? Hors de mon périmètre (famille risques), à signaler au consolidateur.
- **Le schéma sous `fields`** : `Node.required` et ceux des facettes ne tiennent pas d'une lecture qui nomme `fields` (`listNodes:966-969`) ; la décision `DECISIONS.md:232-245` l'assume (« la seule réponse du contrat dont le schéma ne dit pas tout, et la vérification des réponses du service (WF-ARC-0060) devra le savoir »). Je ne le compte pas, la spécification ne le contredit pas, mais le client engendré typera ces propriétés non optionnelles.
- **`is_critical` d'une récapitulative dont une subordonnée est en mode manuel** : fausse par la règle ; non dit, non compté.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| F-01 (L-10) | réglé | `schemas/revisions.yaml:1344-1360` (`total_float`, `is_critical` exigés), `:1431-1448` (règle de la récapitulative) ; fixtures : « Études » `0 d`, critique |
| F-02 (L-07) | réglé | `schemas/revisions.yaml:1234-1248` (`LinkConflict`), `:1449-1461`, `:1224-1227` ; `fixtures/api/task_dates_conflicting.json` |
| F-03 (L-08) | réglé | `schemas/revisions.yaml:1724-1737` ; `paths/revisions.yaml:1672-1675` ; `common.yaml:566-569` (`DUPLICATE_PREDECESSOR`) ; `predecessors_duplicate.json` |
| F-04 (L-11, H-05) | réglé | `paths/revisions.yaml:1288-1314`, `:1345-1361` (`task_not_started`, `at_least_one_task`, `params.risks`) ; `node_delete_started_refused`, `node_delete_last_provision_task_refused`, `node_deleted_provision_moved` ; `TASK_ALREADY_STARTED`/`TASK_COMPLETED` retirés — la fixture du déplacement fait l'objet de F-02 ci-dessus |
| F-05 | réglé | `paths/revisions.yaml:1757-1767` (`SUMMARY_TASK_DERIVED`, `params.subordinate_node_ids`) ; `task_progress_summary_refused.json` ; `common.yaml:745-751` |
| F-06 | réglé | `paths/revisions.yaml:1009-1051` (43 paramètres), `:1093-1110` (422) ; `parameters.yaml:229-594` ; `nodes_estimate_filtered`, `nodes_bounds_inverted`, `nodes_period_inverted` |
| F-07 (L-12) | réglé | `schemas/revisions.yaml:878-928` (`started_on`, `completed_on` après `is_critical`, `progress` retiré) ; `paste_too_wide` à 16 |
| F-08 | réglé | `schemas/revisions.yaml:1907-1917` (`label` facultatif, composé « — ») ; `paths/revisions.yaml:1125-1128` ; `estimate_line_created_labelled.json` |
| F-09 | réglé | `schemas/revisions.yaml:1900-1905`, `:1918-1922`, `:1949-1954` ; `ComputedField`/`ComputedValueField` (`estimate_line.cost_category_id`), `ComputedDependency.resource_role` ; `estimate_line_category_mismatch`, `dependencies_labour_category` ; lignes de main-d'œuvre : catégorie dans `computed_fields` |
| F-10 | réglé | `schemas/revisions.yaml:1678-1686` (`line_not_provision`) ; `paths/revisions.yaml:1808-1822` ; `projects.yaml:314-317` ; `remaining_provision_refused.json` ; provision du témoin `is_available: false` |
| F-11 | réglé | `paths/revisions.yaml:1879-1907` (409 `edit_planning`, 422 `VALUE_REQUIRED`/`UNKNOWN_TIMELINE`/`FIELD_NOT_ACCEPTED`) ; `schemas/revisions.yaml:1739-1759` ; `node_tracking_marked_refused`, `node_tracking_timeline_required`, `node_tracking_timeline_unknown` |
| F-12 | réglé | `schemas/revisions.yaml:1165-1168` (`rescheduled` : une tâche rendue entière dans `ancestors` y paraît aussi) ; `DECISIONS.md:9365-9366` |
| F-13 (L-13) | réglé | `schemas/revisions.yaml:1389-1398`, `:2044-2048`, `:2084-2086` ; `paths/revisions.yaml:1696-1700`, `:1780-1782` ; `milestone_completed.json` (`started_on` = `completed_on` = 2026-06-03) |
| F-14 (L-09, F-15) | réglé | `schemas/revisions.yaml:816-834` (`task.scheduling_mode`), `:1843-1845` (`COMPUTED_VALUE`) ; `common.yaml:469-475` ; « Études » : `computed_fields` avec `task.scheduling_mode` |
| F-15 | réglé | `paths/revisions.yaml:1301-1307` (`deleteNode`), `:1922-1927` (`moveNodes`) ; `schemas/revisions.yaml:1147-1151` (`ancestors`) ; `node_summary_emptied.json` |
| F-16 | réglé | `schemas/revisions.yaml:1334-1339` (`Lag.value` : « 50 pour la moitié ») ; l'absence d'exemple en `percent` est assumée (`DECISIONS.md:9366-9367`) |
| F-17 | partiellement réglé | exemples ajoutés : `node_create_without_hours`, `estimate_line_without_hours`, `nodes_move_without_hours`, `node_create_field_not_accepted`, `estimate_line_field_not_accepted`, `task_milestone_duration_refused`, `estimate_line_rate_missing`, `estimate_line_role_required`, `estimate_line_provision_reserved`, `remaining_completed_refused` ; `COMPUTED_VALUE` nommé dans le 422 d'`updateEstimateLine` (1600-1602) ; **reste** : le 409 d'`applyPaste` est décrit (2139-2149) mais sans exemple — repris dans F-10 ci-dessus |
| F-18 | réglé | `parameters.yaml:111-120` (`NodeKinds` : « ce n'est pas un filtre ») ; `schemas/revisions.yaml:1411-1417` (`calendar_id` nul pour une intersection) |
| F-19 | réglé | `paths/revisions.yaml:1417-1424` (422 sur `/query/field`, « pas de 400 »), `:1252-1254` ; le 400 retiré des deux lectures |
| L-07 | réglé | = F-02 |
| L-08 | réglé | = F-03 |
| L-09 | réglé | = F-14, F-15 |
| L-10 | réglé | = F-01 |
| L-11 | réglé | = F-04 (le déplacement des lignes de provision est décrit et exemplifié ; la fixture est reprise en F-02) |
| L-12 | réglé | = F-07 |
| L-13 | réglé | = F-13 |
| M-08 | réglé | `schemas/revisions.yaml:1622-1639` (`reestimated_amount` d'une ligne jamais réestimée : grandeurs de la référence ou de l'avenant, taux conservés, année de consommation courante) ; `DECISIONS.md:8753-8787` ; `volume/nodes_thousand.json` (lignes tirées : budgété aux taux de 2025 projeté, réestimé aux taux de 2026) |

## Annexe G — Indicateurs d'un projet et portefeuille

**Périmètre.** `docs/api/README-fr.md` (94 l., tableau « Conventions » en entier) ; `docs/api/paths/analysis.yaml`
(478 l., 10 opérations) et `docs/api/paths/portfolio.yaml` (338 l., 8 opérations) en entier ;
`docs/api/components/schemas/indicators.yaml` (690 l.) et `docs/api/components/schemas/portfolio.yaml` (417 l.) en
entier ; dans `components/parameters.yaml` (909 l.) `Limit`, `Offset`, `Search`, `SortOrder`, `IndicatorsRevision`
(735–751), `AsOf` (753–762), `Scope` (764–777), `WorkloadBasis` (779–787), `PortfolioStates` (789–801), `PortfolioFrom`
(803–814), `PortfolioTo` (816–825), `PortfolioOrgNode` (827–834) ; `responses.yaml` `UnprocessableEntity` (89–93),
`PortfolioPeriodRefused` (95–113) ; `common.yaml` `Decimal`, `Money`, `Hours`, `Percent`, `PaginationMeta`,
`ProblemParams.state/state_enum` ; `reference.yaml` `AlertZone`, `IndexThresholds`, `ResourceRoleImage` ; `risks.yaml`
`RiskCoverageTotals`, `RiskMatrix` ; `revisions.yaml` `KanbanTask`, `KanbanCommand`, `KanbanCommandAvailability`,
`NotStartedTask`, `TaskFacet.physical_progress` ; `projects.yaml` `ProjectState`. Spécification 1.0.1 : §3.4.3
(1440–1608, WF-PTF-0010 à 0110), §3.4.4.4 (1872–1900, WF-REF-0170, WF-REF-0180), §3.4.5.5 (2597–2698, WF-RAE-0010 à
0050), §3.4.5.8 (2875–3096, WF-IND-0010 à 0130), §4.4.2 (3980–4060, WF-DAT-0040), §4.6.2 (4259–4330), plus
WF-DEV-0010 (2487), WF-DEV-0060 (2515), WF-DEV-0070 (2587), WF-DEV-0080 (2571), WF-RIS-0050 (2785), WF-PRJ-0090 (2187),
WF-CYC-0130 (1035), WF-IHM-0060 (3246), WF-IHM-0070 (3258), WF-IHM-0130 (3330). **48 fixtures ouvertes** (les 35 de
`analysis.yaml`, les 13 de `portfolio.yaml`, dont les 7 de `fixtures/api/volume/`), toutes relues et vérifiées par
script (`revue/check_g.py`) : totaux = somme des parts, parts d'une répartition sommant à 1 avec le reste
d'arrondi sur la plus grande, cumuls monotones, points aux fins de mois, formules des quatorze indicateurs du témoin,
sommes des sous-projets, capacités et totaux mensuels des plans de charge, cohérence liste du portefeuille ↔ valeur
↔ performance ↔ structure des coûts ↔ risques. `make check-fixtures` exécuté (0 exemple cité par une fixture).
Décisions : « L'univers témoin » (1777–2723, en particulier 2083–2202 et 2315–2457), #247 (1170–1182), #466
(1620–1665), US-0240/L2–L5 (641–870), EP-15/US-0550 (7578–7640), US-0701/L5 (8888–9014), US-0701/L6 (9014–9066),
US-0703/L7 (9976–9995), #1691 (issue GitHub, close). Revue du 2026-10-28 : annexe G (2377–2556), L-16, L-24, M-02,
M-03, M-06, M-07, M-09, M-10, M-11, M-13 à M-16.

### Synthèse

Le lot US-0701/L5–L6 a fait ce que la revue du 2026-10-28 demandait, et les fixtures le prouvent : les courbes du
projet sont au pas du mois (46 points de fin de mois et non 756, la marche d'avenant en deux points, la date de calcul
en point de plus), les courbes et indicateurs d'une révision marquée sont dits conservés (`is_stored` vrai), le projet
sans révision en cours a ses indicateurs du jour (fixture nouvelle, formules exactes), les décaissements laissent le
coût réel à ses dates (la somme des décaissements à venir égale le reste à engager au centime), la revue précédente
est une révision marquée En cours, le temps/temps n'a plus le point de l'offre, le portefeuille a son horizon, sa
période sur les projets terminés, sa couverture « en cours et terminés » et la contribution d'une offre. La spécification
1.0.1 a de son côté aligné WF-RAE-0020 sur le contrat (marge = budget − projection, −50) : le sens est juste partout.
Les quatorze indicateurs du témoin, les parts, les sommes par sous-projet, les capacités et les totaux mensuels se
recalculent exactement. Ce qui reste : une phrase de `getIndexHistory` qui contredit la spécification, son propre schéma
et sa fixture (un point « jamais omis » pour une révision marquée en chiffrage) ; deux lectures d'indicateurs projets
sans 409 pour un projet antérieur à En cours ; un résidu de champs toujours rendus mais facultatifs, que la règle de
G-02 n'a pas atteints (huit colonnes de la liste du portefeuille, la période du périmètre, la zone des mois du plan
d'un projet…) ; et des mineurs de description et d'exemple, dont deux fixtures du portefeuille qui ignorent encore le
monteur câbleur que l'univers témoin emploie depuis EP-02/L27.

**12 constats : 0 bloquant, 3 majeurs, 9 mineurs. Suivi des 28 constats croisés du 2026-10-28 : 27 réglés,
1 partiellement réglé (G-02), 0 non réglé, 0 sans objet.**

### Constats

#### G-01 — `getIndexHistory` : un point « jamais omis » pour une révision marquée avant l'état En cours
- **gravité** : majeur
- **emplacement** : `docs/api/paths/analysis.yaml:448-450` (`getIndexHistory`) ; contre
  `docs/api/components/schemas/indicators.yaml:639-644` (`IndexHistory`), `:677-683` (`IndexHistoryPoint`) et
  `fixtures/api/index_history.json` (résumé et `points`)
- **spécification** : `WF-IND-0130-A` (l. 3038) Vérif — « une révision marquée pendant le chiffrage n'en donne aucun
  (WF-DAT-0040) » ; `WF-DAT-0040-A` (l. 4032) — « Une révision marquée avant l'état En cours ne conserve que les
  indicateurs de devis » ; `WF-IND-0090-A` (l. 3054), même règle pour le temps/temps — « Les révisions marquées
  avant l'état En cours ne donnent aucun point »
- **le contrat dit** : « Un indice qu'une révision n'a pas su calculer — marquée avant l'état En cours — est un point
  non calculable, jamais omis » (analysis.yaml:448-450) ; le schéma dit l'inverse : « un point par révision marquée
  à partir de l'état En cours » (indicators.yaml:640) et « Sur un projet de trois révisions marquées à partir de
  l'état En cours, chaque courbe porte quatre points » (:643-644)
- **la fixture dit** : `index_history.json` — « l'offre, marquée pendant le chiffrage, n'a conservé que son devis
  (WF-DAT-0040, #468) » ; deux points par maille (la référence du 1er février, le jour courant), aucun pour l'offre du
  15 décembre 2025
- **décision** : `DECISIONS.md:8920-8966` (« Les courbes au pas du mois… », M-03) tient pour le dernier point ; aucune
  décision n'assume le point non calculable d'une révision marquée en chiffrage — la phrase est un reste de l'état
  antérieur au 2026-10-09, que la spécification contredit. Tient : rien ; **contredite par la spécification 1.0.1**
- **proposition** : remplacer la phrase par « Une révision marquée avant l'état En cours n'a conservé aucun indicateur
  projet (WF-DAT-0040) : elle ne donne aucun point ; un indice qu'une révision marquée En cours n'a pas su calculer —
  sans coût réel, sans valeur planifiée — est un point non calculable, jamais omis (WF-IND-0010) », ce qui est
  exactement ce que la fixture montre (la référence du 1er février, `no_actual_cost`, `no_planned_value`).

#### G-02 — `getIndexHistory` et `getMilestoneTracking` sans 409 pour un projet antérieur à l'état En cours
- **gravité** : majeur (un statut HTTP à ajouter : incompatible après le gel)
- **emplacement** : `docs/api/paths/analysis.yaml:279-306` (`getMilestoneTracking`, réponses 200/401/404/500/503),
  `:436-478` (`getIndexHistory`, réponses 200/401/404/422/500/503) ; en regard `:253-263` (409 de
  `getProjectIndicators`), `:362-370` (`getCostCurve`), `:412-420` (`getEarnedValueCurves`)
- **spécification** : `WF-IND-0010-A` (l. 2926) — « Les indicateurs projets ne sont calculés qu'à partir de l'état En
  cours ; avant, seuls les indicateurs de devis sont disponibles » ; Vérif « Sur un projet à l'état Chiffrage, aucun
  indicateur projet n'est proposé » ; FBS-4.8.5 (l. 3038) et FBS-4.8.6 (l. 3054) sont des indicateurs projets
- **le contrat dit** : les trois autres lectures d'indicateurs projets refusent par 409 `STATE_FORBIDS_OPERATION`,
  `params.state` et `params.state_enum`, « projet antérieur à l'état En cours » (exemple
  `project_indicators_not_in_progress`) ; l'évolution des indices et le diagramme temps/temps ne déclarent rien : sur
  un projet en chiffrage, un service rend soit un 200 vide (aucune révision marquée En cours, et un « point du jour
  courant » qui n'existe pas), soit un 409 que le contrat n'annonce pas
- **la fixture dit** : aucune fixture d'un projet en chiffrage pour ces deux opérations ; `milestone_tracking_none`
  est un projet en cours sans jalon inscrit
- **décision** : `DECISIONS.md:1170-1182` (#247) a étendu le 409 aux trois lectures `revision_id` ; aucune décision
  sur ces deux opérations. Aucune
- **proposition** : déclarer sur les deux opérations le 409 `STATE_FORBIDS_OPERATION`, `params.state` et
  `params.state_enum`, avec l'exemple `project_indicators_not_in_progress` déjà existant ; dire dans la description
  « sur un projet antérieur à l'état En cours, seuls les indicateurs de devis existent (WF-IND-0010) ». Si l'auteur
  préfère un 200 vide (`milestones: []`, `scopes` sans point), le dire — mais le 409 est la forme des trois autres.

#### G-03 — Des champs toujours rendus restent facultatifs : le résidu de G-02
- **gravité** : majeur (resserrer `required` après le gel resserre le contrat côté producteur — la règle de G-02 du
  2026-10-28, `DECISIONS.md:8888-8905`)
- **emplacement** : `docs/api/components/schemas/portfolio.yaml:42` (`PortfolioProjectRow.required: [project_id,
  label, state, can_open, last_marked_at]` — `code`, `reference_budget`, `current_estimate`, `win_probability`,
  `project_manager_projection`, `delta_to_reference`, `cost_index`, `schedule_index` facultatifs) ; `:11`
  (`PortfolioScope.required` sans `from`, `to`, `org_node_id`) ; `indicators.yaml:201` (`RemainingIndicators.required`
  sans `delta_to_reference` ni `delta_to_previous_revision`) ; `:128` (`EstimateIndicators.required` sans
  `provisions_identified` ni `delta_to_previous_revision`) ; `:507-512` (`MilestoneTracking.milestones[]` sans
  `completed_on`) ; `:467-481` (`WorkloadPlan.roles[]` sans `org_node_id`, `roles[].months[].required: [month, hours]`
  sans `zone`) ; `:588` (`CurveSeries.steps`) ; `:8`, `:34` (`Computable`, `ComputableMoney` : `value` et `reason`
  facultatifs) ; `:189`, `:284` (`label` d'`AmountByKey`/`ComputableAmountByKey`)
- **spécification** : `WF-PTF-0040-A` (l. 1490) Vérif — « Chacune des colonnes citées est présente » ;
  `WF-RAE-0020-A` (l. 2642) Vérif — « l'écart correspondant est absent plutôt que nul ; sur un projet sans révision
  de référence, la marge sur le budget l'est aussi » (absent = `null`, que le client doit distinguer d'un champ omis) ;
  `WF-PTF-0010-A` — « `scope.from` et `scope.to` disent la période retenue » (`PortfolioFrom`, parameters.yaml:812-813)
- **le contrat dit** : les descriptions font de chacun un champ toujours rendu (« nul hors d'un projet en cours »,
  « nulle quand le projet n'a pas de révision de référence », « nul sans nœud », « un point par révision… ») mais le
  schéma admet qu'il manque ; le client engendré les voit `?` et le service les engendre `Optional`
- **la fixture dit** : toutes les fixtures les portent (les 300 lignes de `volume/portfolio_projects.json` portent
  les treize clés ; `workload*.json` portent `zone` et `org_node_id` sur chaque rôle et chaque mois ;
  `remaining_indicators*.json` portent les deux écarts) : aucun exemple à toucher
- **décision** : `DECISIONS.md:8888-8905` (G-02) liste ce qui a été rendu exigé et s'arrête là ; `:8906-8908` a fait
  de même pour `share` (EP-14/L55). Tient pour ce qu'elle nomme ; muette sur le reste
- **proposition** : ajouter aux `required` — `PortfolioProjectRow` : les huit colonnes (nullables déjà) ;
  `PortfolioScope` : `from`, `to`, `org_node_id` ; `RemainingIndicators` : `delta_to_reference`,
  `delta_to_previous_revision` ; `EstimateIndicators` : `provisions_identified`, `delta_to_previous_revision` ;
  `MilestoneTracking.milestones[]` : `completed_on` ; `WorkloadPlan.roles[]` : `org_node_id` (exigé dans
  `ResourceRoleImage`, reference.yaml:166-180) et `roles[].months[]` : `zone` (comme `PortfolioWorkload`) ;
  `CurveSeries` : `steps` (vide, non absent — la fixture `cost_curve_subproject_empty` le rend `[]`) ; `Computable` et
  `ComputableMoney` : `value`, `reason`. Pour `label`, trancher : exigé et nul pour `unassigned` (comme
  `IndexHistoryScope.label`, indicators.yaml:667-669), ou facultatif partout — les fixtures l'omettent aujourd'hui pour
  `unassigned` et le rendent `null` dans `index_history`.

#### G-04 — Deux `delta_to_reference` de signes opposés, pour une grandeur que la spécification 1.0.1 nomme « marge »
- **gravité** : mineur (le sens est juste et dit ; le nom seul est en cause, et il ne se change qu'avant le gel)
- **emplacement** : `docs/api/components/schemas/indicators.yaml:231-237` (`RemainingIndicators.delta_to_reference` :
  « La marge sur le budget de référence … budget 1 000, coût réel 500, reste à engager 550, marge -50 »), `:212-218` ;
  `docs/api/components/schemas/portfolio.yaml:72-77` (`PortfolioProjectRow.delta_to_reference` : « positif quand elle
  le dépasse : … écart 50 »)
- **spécification** : `WF-RAE-0020-A` (l. 2642, **1.0.1**) — « une marge et un écart : la marge sur le budget de
  référence, budget de référence moins la projection du chef de projet (WF-IND-0050) …, positive quand il en reste ;
  et l'écart à la revue précédente » ; Vérif « la marge sur le budget vaut − 50 » ; `WF-PTF-0040-A` (l. 1490) Vérif —
  « un écart de 50 »
- **le contrat dit** : le même nom `delta_to_reference` pour la marge du reste à engager (−50) et pour l'écart de la
  liste du portefeuille (+50) ; `RemainingIndicators` consacre six lignes (212–218) à prévenir du contresens
- **la fixture dit** : `remaining_indicators.json` `delta_to_reference: "-641535.13"` et
  `volume/portfolio_projects.json` (PRJ-001) `delta_to_reference: "641535.13"` — la même grandeur, le signe opposé,
  le même nom
- **décision** : `DECISIONS.md:1628-1655` (#466, « La marge du reste à engager a un seul sens ») — « Deux mots, deux
  sens … le reste à engager parle de **marge** (`delta_to_reference`, `SubprojectBalance.variance`, que le front nomme
  « marge »), … le portefeuille et les projections parlent d'**écart** ». Tient : la spécification 1.0.1 a rejoint le
  sens de la décision, et ne nomme aucun champ. Le nom reste un choix assumé ; il n'est signalé ici que parce qu'un
  renommage est impossible après le gel
- **proposition** : à trancher avant le gel — soit renommer `RemainingIndicators.delta_to_reference` en
  `margin_to_reference` (et laisser `SubprojectBalance.variance`, qui ne partage son nom avec rien), le front adaptant
  son libellé déjà « Marge sur le budget de référence » ; soit garder le nom et le consigner une fois de plus dans
  DECISIONS comme choix définitif. La première forme ôte un piège que la description seule retient.

#### G-05 — Le plan de charge d'une révision marquée, calculé à son marquage, est dit non conservé
- **gravité** : mineur
- **emplacement** : `fixtures/api/workload_marked_remaining.json:5` (`context`: `revision_status: marked`,
  `computed_at: 2026-02-01T09:00:00Z`, `is_stored: false`) ; `docs/api/components/schemas/indicators.yaml:117-124`
  (`CalculationContext.is_stored` : « Vrai pour ce que le marquage d'une révision a conservé — ses indicateurs et ses
  courbes ») ; `docs/api/paths/analysis.yaml:95-96` (« Sur une révision marquée, la date de calcul est sa date de
  marquage ») ; `fixtures/api/workload_reference_budget.json:5` (`revision_status: marked`, `computed_at` du jour,
  `is_stored: false`)
- **spécification** : `WF-DAT-0040-A` (l. 4032) — « Sont conservés de même la charge par rôle de ressource et par
  mois (WF-DEV-0070) … c'est ce que lisent, à une date passée, le plan de charge agrégé » ; `WF-DEV-0070-A`
  (l. 2587) Vérif — « sur une révision marquée, la date de calcul est sa date de marquage »
- **le contrat dit** : `is_stored` ne parle que des indicateurs et des courbes ; `WorkloadPlan` ne dit pas que la
  charge d'une révision marquée est celle que son marquage a conservée, et la fixture la rend `is_stored: false` alors
  qu'elle est calculée à la date de marquage et invariable depuis (c'est précisément ce que WF-DAT-0040 conserve pour
  le plan agrégé à une date passée)
- **la fixture dit** : voir emplacement ; `workload_reference_budget` lit la référence marquée sur son budget, au jour
  courant, `is_stored` faux — cohérent (la charge budgétée ne dépend d'aucune date), mais le lecteur ne le sait pas
- **décision** : `DECISIONS.md:665-690` (US-0240/L4) décrit les trois exemples sans parler de conservation ;
  `:8920-8940` (M-02) étend `is_stored` aux courbes, pas à la charge. Aucune
- **proposition** : `is_stored` : « Vrai pour ce que le marquage d'une révision a conservé — ses indicateurs, ses
  courbes et sa charge par rôle et par mois (`marked_remaining`) » ; `WorkloadPlan` : « Sur `marked_remaining`, le plan
  est celui que le marquage a conservé, `context.computed_at` sa date de marquage et `is_stored` vrai (WF-DAT-0040) ;
  sur `reference_budget`, la charge budgétée de la référence, sans date de calcul, `is_stored` faux » ; régénérer
  `workload_marked_remaining` (`is_stored: true`).

#### G-06 — Le 422 du plan de charge agrégé n'a aucun exemple
- **gravité** : mineur
- **emplacement** : `docs/api/paths/portfolio.yaml:144-152` (`getPortfolioWorkload`, `'422'` : description, schéma
  `Problem`, pas d'`examples`) ; en regard `paths/analysis.yaml:135-145` (`getProjectWorkload`, 422 avec
  `workload_revision_refused`)
- **spécification** : `WF-PTF-0060-A` (l. 1518) — « un seuil que l'utilisateur choisit … un horizon choisi » ;
  convention README « Toute opération … déclare … le 422 d'un champ manquant ou refusé » ; brief : « un refus
  déclaré sans exemple »
- **le contrat dit** : trois refus nommés — `/query/org_node_id` inconnu, `/query/under_load_threshold` et
  `/query/horizon_months` par `VALUE_OUT_OF_RANGE` — et aucun exemple ; c'est le seul 422 propre de la famille sans
  fixture (`getPortfolioPilotHealth` partage `UnprocessableEntity`, lui-même sans exemple, responses.yaml:89-93)
- **décision** : `DECISIONS.md:9777` (US-0702/L2, « Les refus sans code ni exemple ») vise ce cas ; `:9055-9056`
  (G-13) a nommé les champs du 422 sans exemple. Aucune n'écarte l'exemple
- **proposition** : une fixture `portfolio_workload_threshold_refused` (`VALIDATION_FAILED`, `fields[]`
  `/query/under_load_threshold` par `VALUE_OUT_OF_RANGE`, `params.minimum: "0"`, `params.maximum: "1"`) ; au besoin
  `portfolio_workload_org_node_unknown`.

#### G-07 — `revision_id` sans description sur trois opérations, et le reste à engager d'une révision marquée
- **gravité** : mineur
- **emplacement** : `docs/api/paths/analysis.yaml:19-21` (`getEstimateIndicators`), `:60-62` (`getMissingRates`),
  `:157-159` (`getRemainingIndicators`) — `name: revision_id, in: query, schema: Uuid`, sans `description` ; en regard
  `parameters.yaml:735-751` (`IndicatorsRevision`, qui dit tout)
- **spécification** : `WF-DAT-0040-A` (l. 4032) — « Sont conservés de même … les totaux par nature de coût et, pour la
  main-d'œuvre, par nœud d'organisation (WF-DEV-0060, WF-RAE-0020) » ; `WF-RAE-0020-A` — « la révision marquée
  précédente … avant celle qui est lue »
- **le contrat dit** : rien du sens du paramètre (absent : la révision en cours, ou la dernière marquée ? une révision
  marquée : les totaux conservés, `is_stored` vrai ?), ni de ce que rend `getRemainingIndicators` sur une révision
  marquée avant l'état En cours (le reste à engager d'une offre est son devis ; `coverage` sans référence ?), ni du
  refus d'un `revision_id` qui n'est pas du projet (404 ?). Les fixtures le montrent pourtant :
  `estimate_indicators_breakdown` lit l'offre marquée (`is_stored: true`), `estimate_indicators` la révision en cours
- **la fixture dit** : `remaining_indicators*.json` ne lisent que la révision en cours
- **décision** : `DECISIONS.md:1170-1182` (#247, « comme les indicateurs de devis ») suppose le même sens que
  `IndicatorsRevision` sans l'écrire sur ces trois paramètres. Aucune
- **proposition** : une description commune, par exemple « La révision lue : absente, la révision courante — en cours,
  ou la dernière marquée quand il n'en a pas (WF-IND-0010) — ; une révision marquée, les totaux que son marquage a
  conservés, `is_stored` vrai (WF-DAT-0040) ; une révision qui n'est pas du projet, 404 », et pour
  `getRemainingIndicators` dire ce que vaut la lecture d'une révision marquée avant l'état En cours (le reste à engager
  égal au devis, `delta_to_reference` et `coverage` sans référence — ou un 409 comme les indicateurs projets : à
  trancher).

#### G-08 — Des variantes sans exemple : la maille d'un sous-projet sur les indicateurs et le devis, une révision marquée sur une courbe
- **gravité** : mineur
- **emplacement** : `docs/api/paths/analysis.yaml:233-236` (`getProjectIndicators`, `Scope`), `:245-248` (trois
  exemples, tous `scope: project`) ; `:22` (`getEstimateIndicators`, `Scope`), `:27-32` (cinq exemples, tous
  `project`) ; `:393-394` (`getEarnedValueCurves`, `Scope`, un seul exemple) ; `:346-359` (`getCostCurve`, aucun
  exemple avec `revision_id` ou `as_of`, `is_stored` vrai)
- **spécification** : `WF-IND-0020-A` (l. 2938) Vérif — « La somme des valeurs acquises des sous-projets, ensemble
  « hors sous-projet » compris, égale celle du projet, de même pour le budget de référence, le coût réel, la valeur
  planifiée et le reste à engager » ; `WF-DEV-0060-A` (l. 2515) — totaux « par sous-projet » ; `WF-DAT-0040-A` —
  courbes conservées
- **le contrat dit** : `Scope` sur `getEstimateIndicators` sans dire ce que deviennent `by_subproject` (une seule clé ?)
  et `by_work_package` (le sous-arbre du lot croisé au sous-projet ?) — le doute de la revue précédente, non levé ;
  `ProjectIndicators` restreint à un sous-projet n'a aucun exemple alors que `index_history` et `remaining_indicators`
  donnent déjà les grandeurs de « Poste de commande » (coût réel 2 400,00, indice de coût 0) ; aucune courbe lue
  `is_stored` vrai
- **décision** : `DECISIONS.md:8965-8966` — « Aucun exemple ne lit une courbe d'une révision marquée : le témoin ne
  modélise pas la date d'import d'une pièce » (assumé) ; rien sur `scope` des indicateurs de devis. Partiellement
  assumé
- **proposition** : `project_indicators_subproject` (« Poste de commande » : budget 23 251 897,56, coût réel 2 400,00,
  reste 23 314 197,53, valeur acquise 0, indices 0 en alerte — les nombres existent déjà dans trois fixtures) ;
  une phrase dans `getEstimateIndicators` sur l'effet de `scope` sur les trois ventilations, ou le retrait du paramètre
  si la maille n'a pas de sens pour un devis (à trancher).

#### G-09 — `as_of` avant toute révision marquée En cours, ou dans l'avenir : refus non dits
- **gravité** : mineur
- **emplacement** : `docs/api/components/parameters.yaml:753-762` (`AsOf`) ; `docs/api/paths/analysis.yaml:253-263`
  (409 de `getProjectIndicators` : « projet antérieur à l'état En cours … ou révision nommée par `revision_id` marquée
  avant lui »)
- **spécification** : `WF-IND-0010-A` — « seuls les indicateurs de devis sont disponibles » avant l'état En cours ;
  `WF-DAT-0040-A` — « Une révision marquée avant l'état En cours ne conserve que les indicateurs de devis »
- **le contrat dit** : `as_of` lit « la dernière révision marquée antérieure ou égale » ; si cette révision est l'offre
  marquée en chiffrage (un `as_of` entre le 15 décembre 2025 et le 1er février 2026 sur le témoin), rien n'est
  conservé — le 409 n'est décrit que pour `revision_id`. Un `as_of` postérieur au jour courant n'est ni admis ni
  refusé
- **décision** : `DECISIONS.md:1170-1182` (#247) ne traite que `revision_id`. Aucune
- **proposition** : `AsOf` : « Une date qui ne retient qu'une révision marquée avant l'état En cours, ou aucune, est
  refusée par 409 `STATE_FORBIDS_OPERATION`, sans `params.state` comme pour `revision_id` ; une date postérieure au
  jour courant est refusée par 422, `/query/as_of` par `VALUE_OUT_OF_RANGE` » (à trancher pour le futur : l'admettre
  comme « le jour courant » est l'autre forme).

#### G-10 — Deux fixtures du portefeuille ignorent le monteur câbleur que le témoin emploie depuis EP-02/L27
- **gravité** : mineur (exemples contre l'univers témoin)
- **emplacement** : `fixtures/api/portfolio_workload.json:2` (résumé : « le monteur câbleur, 1 250 personnes, sans
  charge — aucun projet ne l'emploie ») ; `fixtures/api/volume/portfolio_cost_structure.json` (`labor_by_org_node` :
  « Bureau d'études électricité » seul, part `1` ; résumé « leur main-d'œuvre par nœud d'organisation de ses rôles »)
- **spécification** : `WF-PTF-0080-A` (l. 1550) — « la ventilation de la main-d'œuvre par nœud d'organisation » ;
  `WF-PTF-0060-A` — « la somme des charges des projets du périmètre »
- **le contrat dit** : la ventilation par nœud est celle des rôles des lignes de main-d'œuvre
- **la fixture dit** : `workload.json`, `workload_reference_budget.json` et `workload_org_node.json` donnent au rôle
  « Monteur câbleur » (nœud 472, « Atelier de câblage ») 13 352,00 h du témoin, de septembre 2027 à avril 2028, au
  budget de référence comme au reste à engager ; la structure des coûts du portefeuille, qui compte le témoin
  (`project_count: 269`, budget agrégé 2 665 431 068,05 = carnet), ne porte aucune main-d'œuvre de l'atelier de
  câblage, et le plan agrégé dit qu'aucun projet n'emploie ce rôle — vrai sur l'horizon juin–novembre 2026 (ses heures
  sont en 2027–2028), faux dans l'absolu
- **décision** : `DECISIONS.md:2407-2412` (EP-02/L26 : « aucun projet ne l'emploie … La main-d'œuvre de la structure
  des coûts reste tout entière au bureau d'études électricité, le nœud des deux rôles qui travaillent ») est antérieure
  à EP-02/L27 (`:2466-2467` : « le câblage est confié au monteur câbleur, toutes ses heures de main-d'œuvre, et ses
  103 tâches ») qui l'a rendue fausse sans la réécrire. **Contredite par l'univers témoin**, non par la spécification
- **proposition** : `mockportfolio` : porter la part de main-d'œuvre du témoin relevant du nœud 472 dans
  `labor_by_org_node` (deux nœuds, parts sommant à 1) ; résumé de `portfolio_workload` : « sans charge sur l'horizon —
  le témoin ne l'emploie qu'à partir de septembre 2027 » ; réécrire `DECISIONS.md:2407-2412`.

#### G-11 — Trois zones que le serveur classe sans que le contrat dise la règle
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/indicators.yaml:249-277` (`SubprojectBalance.zone` : « Le serveur
  classe le dépassement dans l'échelle commune des signalements ») ; `docs/api/components/schemas/portfolio.yaml:376-379`,
  `:396` (`PilotHealth.signals[].zone` : « Chacun porte sa zone … que le serveur classe ») ; `:168-174`
  (`PortfolioWorkload.roles[].months[].zone` : la règle est dite, mais pas le cas d'un `load_ratio` non calculable,
  `no_capacity`)
- **spécification** : `WF-RAE-0020-A` — « Un code de couleur signale les sous-projets dont le budget est dépassé » ;
  `WF-PTF-0110-A` (l. 1598) — quatre signaux « qui se constatent sans jugement » ; `WF-IHM-0070-A` (l. 3258) — une
  même échelle, « Chaque signalement est porté par au moins un indice non coloré »
- **le contrat dit** : le front ne déduit rien (juste), mais le serveur doit connaître la règle et le contrat ne la
  porte pas : un sous-projet dépassé est-il `alert` (la fixture), et un sous-projet à 99 % `nominal` ou `watch` ? un
  signal de revue en retard est-il `watch` (la fixture) et un jalon dépassé `alert` ?
- **la fixture dit** : `remaining_indicators.json` : trois sous-projets dépassés, tous `alert` ; `pilot_health.json` :
  133 + 29 + 30 signaux `watch`, 20 jalons `alert`
- **décision** : `DECISIONS.md:2434-2435` — « Zones : un jalon dépassé en alerte, les trois autres signaux en
  vigilance — WF-IHM-0070 ne fixe pas de niveau » : assumée pour le faux back, jamais écrite au contrat ; rien pour
  `SubprojectBalance.zone`. Tient, à porter au contrat
- **proposition** : `SubprojectBalance.zone` : « `alert` quand le sous-projet dépasse son budget (`is_over_budget`),
  `nominal` sinon ; jamais `watch` » (ou dire le seuil de vigilance s'il en est un) ; `PilotHealth.signals[].zone` :
  « `alert` pour un jalon contractuel dépassé, `watch` pour les trois autres signaux » ; `PortfolioWorkload` : « un
  rôle sans capacité (`no_capacity`) est `alert` dès qu'il a une charge, `watch` sinon » (à trancher).

#### G-12 — Deux descriptions ambiguës : les rôles du plan d'un projet, et le filtre `zones` qui « place d'abord »
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/indicators.yaml:463-481` (`WorkloadPlan.roles`, sans description) ;
  `docs/api/paths/portfolio.yaml:26-33` (`getPortfolioProjects`, `zones` : « Restreint aux projets dont l'indice de
  coût ou l'indice de délai est dans l'une de ces zones : les projets en alerte, d'abord »)
- **spécification** : `WF-DEV-0070-A` — « La capacité de chaque rôle y est présentée en regard de sa charge … Le filtre
  par nœud d'organisation ne laisse voir que les rôles qui en relèvent » ; `WF-PTF-0040-A` — « Le tri par indice de
  coût place les projets en alerte en tête » (un tri, pas un filtre)
- **le contrat dit** : `PortfolioWorkload.capacity_monthly_hours` dit quels rôles le plan agrégé liste (« tous les
  rôles actifs sans filtre, ceux du nœud avec lui », portfolio.yaml:122-124) ; `WorkloadPlan.roles` ne dit pas si le
  plan d'un projet liste les seuls rôles que ses lignes emploient, tous les rôles actifs, ou ceux du nœud — la décision
  US-0240/L4 montrait « le technicien de mise en service … n'a pas de charge, et sa capacité seule », la fixture
  d'aujourd'hui ne liste que des rôles chargés. « Les projets en alerte, d'abord » dans un filtre se lit comme un ordre
  que `sort_by` (défaut `label`) ne donne pas
- **la fixture dit** : `workload.json` : trois rôles, tous chargés ; aucun rôle sans charge
- **décision** : `DECISIONS.md:665-690` (US-0240/L4), `:7584-7592` (#375, option b : « Le plan d'un projet ne change
  pas ») — ni l'une ni l'autre ne dit la liste des rôles du plan d'un projet. Aucune
- **proposition** : `WorkloadPlan.roles` : « Les rôles qu'emploie une ligne de main-d'œuvre de la base lue, chargés ou
  non sur l'horizon, restreints au nœud avec `org_node_id` » (ou « tous les rôles actifs », à trancher, et le dire) ;
  `zones` : « Restreint aux projets dont l'indice de coût ou l'indice de délai est dans l'une de ces zones
  (WF-IHM-0130) ; le tri reste celui de `sort_by` ».

### Ce qui est juste

- **Les formules, au centime et à la quatrième décimale** (`revue/check_g.py`). `project_indicators.json` :
  avancement financier 0,0205 = AC/(AC+RAE), consommation 0,0207 = AC/BR, avancement physique 0,0212 = EV/BR, CPI
  1,0261 = EV/AC (nominal), SPI 0,8674 = EV/PV (vigilance aux seuils 0,9/0,8), CV 36 888,13, SV −221 599,80, projection
  au budget 68 204 679,92 = AC + (BR − EV), chef de projet 68 883 103,18 = AC + RAE, rythme constaté 66 505 326,80 =
  BR·AC/EV, les trois écarts au budget ; `project_indicators_marked` (indices non calculables `no_actual_cost`,
  `no_planned_value`, zone nulle, écart au rythme constaté nul) et `project_indicators_without_current_revision`
  (`revision_status: marked`, `is_stored: false`, `computed_at` du jour, coût réel du jour, CPI 0 calculable en alerte,
  rythme constaté `no_earned_value`) exacts tous deux — M-03 réalisé, WF-IND-0010 Vérif tenu.
- **Les répartitions.** Parts du devis et du reste à engager à quatre décimales, sommant exactement à 1 par nature et
  par sous-projet, le reste d'arrondi porté sur la plus grande (Débours 0,8544 pour 0,85449…, « hors sous-projet »
  0,3473 pour 0,34737…), plancher `0.00003` pour 0,0000296 (`estimate_indicators_breakdown`), la part d'un lot sans
  reste d'arrondi (0,0073) ; totaux = somme des natures = somme des sous-projets (68 923 691,06 ; 67 470 132,98) ;
  `by_subproject` du reste à engager : budgets, coûts réels, restes et marges somment au projet (68 241 568,05 ;
  1 412 970,20 ; 67 470 132,98 ; −641 535,13 = `delta_to_reference`), chaque marge = budget − coût réel − reste ;
  couverture 850 060 − 500 000 − 200 = 349 860. L'écart du devis −349 860,00 est bien devis lu moins devis de la
  référence provisions comprises (69 273 551,06, le reste à engager de la référence à son marquage) — L-24 réalisé.
  `estimate_indicators_missing_rates` : le total, les écarts, les montants et les parts des natures touchées
  `hourly_rate_missing` avec `params.missing_rates`, les montants des autres natures calculés et leur part non — exact
  à WF-DEV-0010 ; `estimate_indicators_work_package_without_task` : « Lot 2 » `work_package_without_task`, « absents
  plutôt que nuls » (WF-DEV-0060).
- **Les courbes au pas du mois** (G-01 du 2026-10-28 réalisé). `cost_curve` : budget 46 points, tous à une fin de mois
  sauf la marche du 1er février en deux points (0,00 → 0,00, `steps[].amount` 2 865,00), premier point nul à la fin du
  mois qui précède, dernier 68 241 568,05 au 31 août 2029 ; coût réel aux fins de mois puis au 3 juin (1 412 970,20) ;
  projection partant de ce point jusqu'à 68 883 103,18 ; cumuls monotones partout. `cost_curve_amendment` : seconde
  marche du 10 mars, 23 333,33 → 26 833,33 ; `cost_curve_payment_delays` : budget et projection translatés d'un mois
  (fin au 30 septembre 2029), coût réel **identique** à la courbe non décalée (M-06), `cash_out_by_month` 43 mois
  contigus, passé = 1 412 970,20 = coût réel, à venir = 67 470 132,98 = reste à engager (Vérif de WF-IND-0100), le mois
  de la date de calcul seul à porter les deux ; `cost_curve_subproject` (`context.scope` nommé, marche = tout le budget
  du sous-projet), `_empty` (trois séries vides, `steps: []`), `_unbudgeted` (budget sans point, coût réel et projection
  tracés), `_empty_payment_delays` (`cash_out_by_month: []`) — conformes au texte de `getCostCurve`.
  `earned_value_curves` : PV 0 au 28 février, 73 333,33 au 31 mars (22 jours ouvrés sur 30), prolongée au budget au
  31 août 2029 ; EV par marches aux fins de mois des terminaisons ; AC aux dates de pièce ; les trois aux fins de mois
  puis au 3 juin (WF-IND-0110).
- **Le temps/temps** (M-10 réalisé) : aucun point de l'offre ; « Réception des études » deux points, le second à sa
  terminaison en abscisse (`2026-04-24T00:00:00Z`) comme en ordonnée ; « Réception usine » horizontale au 30 juin,
  dernier point à l'instant du calcul ; `marked_at` décrit comme l'abscisse (date de marquage, terminaison à minuit,
  instant du calcul) — le doute de la revue précédente est levé.
- **L'évolution des indices** : un point conservé (la référence, non calculable) et le point du jour, par maille
  (projet, deux sous-projets, « hors sous-projet »), seuils courants rendus (`thresholds`), `version_name` nul au jour
  courant, `scope` restreint à une maille (`index_history_subproject`) ; les indices des mailles se recomposent en
  ceux du projet (EV ≈ 851 721 + 598 158 + 0 = 1 449 858).
- **Le plan de charge** (L-16 réalisé) : les trois bases décrites, 409 pour la seule base absente, 422 pour
  `marked_remaining` sans révision marquée (fixtures `workload_no_reference`, `workload_revision_refused`) ; la
  répartition au prorata des heures travaillées et la règle du reste après la date de calcul écrites
  (indicators.yaml:417-425) et tenues par `workload.json` (juin 2026 → août 2029, aucun mois passé, 67 153,50 h
  contre 68 841,00 h au budget) ; `monthly_totals` = somme des rôles sur chaque mois, contigus ; `org_node_label`
  résolu (« Atelier de câblage ») ; `WorkloadBasis` parle de charge (L-16, point 3).
- **Le Kanban** (WF-RAE-0030) : 925/8/27 tâches, aucune récapitulative ; `start` listé sur toute tâche non démarrée
  qui n'est pas un jalon, `complete` indisponible pour elle par `task_is_milestone` puis `task_without_lines`, dans cet
  ordre ; les 28 jalons sans ligne terminables directement ; sur les démarrées, `complete` disponible pour la seule
  tâche sans ligne hors provision ; `reopen` sur les terminées, `completed_on` jamais nul ; `predecessors_completed`
  tous faux dans le témoin, un vrai dans `startable_tasks_milestone` ; `progress` que chaque geste envoie.
- **Le portefeuille.** Liste : les treize clés sur 300 lignes, 269 en cours et 31 offres, `can_open` faux pour un
  projet sur sept, PRJ-001 aux valeurs de ses indicateurs, PRJ-002 sans devis (sans révision) ni indice ; page 51–100
  (`limit 50, offset 50, total 300`) ; `portfolio_projects_empty` (`completed`, `project_count: 0`). Valeur : carnet
  2 665 431 068,05 = somme des budgets des 269 projets en cours = `PortfolioPerformance.reference_budget` = budget
  agrégé de la structure des coûts ; pipeline brut 317 939 400,00 = somme des devis des offres, pondéré
  146 660 510,00 = somme des devis × probabilités ; `conversion_rate` 0,4 (Vérif WF-PTF-0050, abandons exclus — M-15).
  Performance : projection chef de projet = somme des projections des lignes (2 795 577 473,18), écart = somme des
  écarts (130 146 405,13), projection au budget = BR − CV, rythme constaté = BR/CPI (M-16), répartition par zone égale
  au décompte des lignes (169/47/53 ; 152/58/59), indices à quatre décimales (0,941, 0,9088 — G-08), `scope.from/to`
  rendus et cinq trimestres 2025-Q2 → 2026-Q2, le dernier égal aux indices du jour (G-03). Structure des coûts :
  budget hors provision (G-15), reste provisions comprises, parts sommant à 1. Risques : 429 points = 429 cases =
  somme des provisions 104 325 697,03 = `identified_total`, dix plus lourds triés décroissants, couverture
  103 703 525,80 − 104 325 697,03 − 4 605 324,00 = −5 227 495,23, `can_open` sur les points et les plus lourds.
  Courbe en S : 18 mois (12 passés + horizon 6) aux fins de mois, le 3 juin en point de plus sur coût réel et
  projection, décaissements par mois dont l'à-venir (748 025 749,43) égale la hausse de la projection, le mois de la
  date de calcul seul à porter passé et avenir ; `_credit` au 31 décembre 2025, 13 mois, période par défaut
  2025-01-01 → 2025-12-31, 198 projets alors en cours, décembre net négatif admis. Plan agrégé : capacité du périmètre
  = somme des trois rôles (1 360 640,5), totaux mensuels = somme des rôles, `load_ratio` à quatre décimales, zones
  conformes à la règle écrite (alerte > 1, vigilance < 0,5, rôle sans charge en vigilance), `under_load_threshold`
  rendu ; filtre « Direction technique » retenant les trois rôles. Santé du pilotage : les quatre codes, `params`
  conformes à la description (17 semaines pour le témoin marqué le 1er février au 3 juin, délai 8 semaines ;
  `lineage_id`/`milestone_label`/`reference_date` sur un jalon), aucune période (`from/to` nuls), états autres qu'en
  cours dits sans effet — `pricing` nommé (#1691 vise l'écran, non le contrat).
- **Les descriptions des décisions récentes sont au contrat** : horizon (`horizon_months` décrit, défaut 6, les douze
  mois passés de la courbe en S) ; période des projets terminés sur la structure des coûts et la courbe en S, « sans
  effet » sur le plan agrégé et la santé du pilotage ; couverture « en cours et terminés » ; contribution d'une offre
  (hors provisions au budget, provisions comprises au reste et à la projection, risques non pondérés, exemple 40/60) ;
  `PortfolioStates` (états hors périmètre sans effet, état à la date de calcul) ; `IndexValue.zone` avec ses bornes et
  classée à la lecture pour un indice conservé (M-13, M-14) ; `actual_cost` « antérieure ou égale » (G-09) ;
  `PortfolioProjectRow.delta_to_reference` cité partout (G-12) ; `earned_value` et `SubprojectBalance.budget` hors
  provisions, `TaskFacet.physical_progress` réécrit (M-11) ; `delta_to_previous_revision` « marquée à l'état En
  cours » (M-09) ; `is_stored` vrai pour une révision marquée, `IndicatorsRevision` sans « connues aujourd'hui »
  (M-02).

### Doutes

- **`RemainingIndicators` n'a pas de forme `hourly_rate_missing`** : WF-DEV-0010 dit « Le calcul d'un devis ou d'un
  reste à engager est refusé tant qu'une catégorie … n'a pas de taux horaire pour l'année de référence de sa révision,
  ou de taux conservé projeté pour celle-ci » ; `RemainingIndicators.total` est un `Money`, non un `ComputableMoney`.
  Si tout reste à engager se calcule aux taux conservés par la révision courante (WF-REV-0060 ; `EstimateLineFacet.reestimated_amount`),
  le cas ne se présente jamais après la première révision — mais rien ne le dit. Non tranché.
- **`getPortfolioProjects` prend `PortfolioOrgNode`** (portfolio.yaml:22) : « Restreint les seules lignes de
  main-d'œuvre » — sur une liste de projets, le budget, la projection et les indices d'une ligne changent-ils, ou le
  filtre ne remplit-il que `scope.org_node_id` ? Le doute de la revue précédente demeure ; `DECISIONS.md:1164-1166`
  ne dit que « relever d'un nœud ».
- **`getPortfolioCostCurve` et `getPortfolioRisks` n'ont pas `PortfolioOrgNode`** : WF-PTF-0010 décrit l'effet du
  filtre pour « toute vue » ; l'absence se justifie par WF-DAT-0040, qui ne conserve par nœud que la main-d'œuvre des
  totaux et de la charge, pas des courbes — à dire dans la description de la courbe en S si c'est la raison.
- **`PilotHealth.signals` n'est ni paginé ni filtrable** : 212 signaux dans la fixture, de l'ordre du millier possible
  à 300 projets ; la spécification ne demande rien, le §4.6.2 vise 2 s.
- **`project_indicators_offer` : un 409 `STATE_FORBIDS_OPERATION` sans `params`** (ni `state`, ni
  `missing_condition`) — forme assumée par `DECISIONS.md:1176-1179` (« le projet est ici en cours, c'est la révision
  qui est antérieure »), hors de la convention README qui veut `missing_condition` pour « une commande » : les
  lectures ne sont pas des commandes. Cohérent, mais le seul 409 du contrat sans aucun paramètre.
- **`win_probability: "1"` pour les 269 projets en cours** de la liste et `project.json` : WF-PRJ-0090 dit qu'elle
  « n'a plus d'effet à partir de l'état En cours, où le projet compte pour tout » ; la fixture rend 1 plutôt que la
  valeur figée à la contractualisation. Cohérent entre fixtures ; le schéma ne dit pas lequel des deux un service rend.
- **`PortfolioRisks.period_outcome`** (provisions survenues et écartées de la période) n'est dans aucune exigence du
  §3.4.3.5 ; assumé par `DECISIONS.md:826-830` (US-0240/L3). Rien à signaler.
- **Les exemples numériques des Vérif** : `make check-fixtures` rend « 92 numeric examples, 0 cited by a fixture » —
  aucune fixture du dépôt ne cite d'exemple, pas seulement WF-IND-0030 à 0100 : le mécanisme (clé `examples` d'une
  fixture écrite à la main, WF-QUA-0020) attend les fixtures du cœur, et les fixtures d'API sont engendrées du témoin,
  dont les nombres (68 241 568,05…) ne sont pas ceux des Vérif (1 000/500/550). C'est donc normal ; les Vérif de
  WF-IND-0060, WF-RAE-0020, WF-IND-0090 et WF-IND-0100 sont tenus par `tools/tests/test_mockcurves.py`
  (`DECISIONS.md:9008-9012`), hors du mécanisme. Un jour, les lier (`examples` sur ces tests ou des fixtures de cœur).
- **WF-PLA-0140 et WF-IHM-0050**, nommées par le brief, ne concernent pas la famille (chronologies nommées, collage
  depuis un tableur) : `INVENTORY.md` les porte ailleurs ; WF-IHM-0130 n'a de part API que les filtres de la liste et
  le contexte de calcul que l'export PNG affiche (`CalculationContext`, `PortfolioScope`), tous deux rendus.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| G-01 (pas du mois) | réglé | `indicators.yaml:538-556` (`CurveSeries`) ; `cost_curve.json` 46 points de fin de mois, `earned_value_curves.json` 43 ; `DECISIONS.md:8920-8940` |
| G-02 (indicateurs exigés) | partiellement réglé | `indicators.yaml:107`, `:296-310`, `:381-388`, `:467` ; `portfolio.yaml:107`, `:149`, `:160`, `:177-187` ; `share` exigé `:181`, `:281`. Reste : `PortfolioProjectRow`, `PortfolioScope`, les écarts du reste à engager, `completed_on`, `zone`/`org_node_id` du plan d'un projet, `steps`, `Computable.value/reason` → **G-03 de cette revue** |
| G-03 (trimestres) | réglé | `portfolio.yaml:228-242` (`quarterly`) ; `volume/portfolio_performance.json` : `from/to` rendus, cinq trimestres, le dernier aux indices du jour |
| G-04 (`horizon_months`) | réglé | `paths/portfolio.yaml:121-126`, `:279-286` (description, `default: 6`, les douze mois passés) ; fixtures 6 et 18 mois, `_credit` 13 |
| G-05 (projets terminés sans période) | réglé | `paths/portfolio.yaml:196-203`, `:259-273` (`PortfolioFrom/To`, `PortfolioPeriodRefused`) ; `:110-115`, `:317-321` (« sans effet », pas de période) ; `scope.from/to` dans les fixtures |
| G-06 (couverture et terminés) | réglé | `portfolio.yaml:277-283`, `:309-316` ; `paths/portfolio.yaml:227-236` |
| G-07 (sens de la marge) | réglé | côté spécification : `WF-RAE-0020-A` 1.0.1 (l. 2647-2649), « marge … − 50 » ; le contrat n'a pas bougé. Le nom du champ : **G-04 de cette revue** (mineur, à trancher) |
| G-08 (précision des indices) | réglé | `indicators.yaml:366-369` (« à quatre décimales ») ; `volume/portfolio_performance.json` 0,941 / 0,9088 |
| G-09 (« antérieure ou égale ») | réglé | `indicators.yaml:331-335` |
| G-10 (prorata des heures) | réglé | `indicators.yaml:317-323` (`planned_value`), `:416-425` (`WorkloadPlan`) |
| G-11 (états hors périmètre, état à la date) | réglé | `parameters.yaml:789-801` (`PortfolioStates`) |
| G-12 (`PortfolioProject`) | réglé | `indicators.yaml:218`, `:400`, `:405`, `:410` nomment `PortfolioProjectRow` |
| G-13 (zone du plan agrégé, 422) | réglé | `portfolio.yaml:168-174` ; `paths/portfolio.yaml:144-152` nomme les trois champs — l'exemple manquant est **G-06 de cette revue** |
| G-14 (performance sur les en cours) | réglé | `paths/portfolio.yaml:161-166` ; `portfolio.yaml:188-190` ; `PortfolioScope.states` « les états demandés » `:19-22` |
| G-15 (« Provision » au budget agrégé) | réglé | `volume/portfolio_cost_structure.json` : deux natures au budget, parts 0,55/0,45 |
| L-16 (plan de charge : base marquée, reste après la date) | réglé | `paths/analysis.yaml:84-96`, `:124-146` ; `indicators.yaml:416-425` ; `parameters.yaml:779-787` (« charge ») |
| L-24 (écart au devis de référence) | réglé | `indicators.yaml:166-172` ; fixture −349 860,00 vérifiée provisions comprises |
| M-02 (courbes conservées, `is_stored`) | réglé | `parameters.yaml:735-751` ; `indicators.yaml:117-124` ; `paths/analysis.yaml:324-328`, `:393-396` |
| M-03 (projet sans révision en cours) | réglé | `parameters.yaml:735-762` ; `paths/analysis.yaml:231-235`, `:444-447` ; `indicators.yaml:122-123`, `:640-642`, `:679-683` ; `portfolio.yaml:1-7`, `:12-16` ; fixture `project_indicators_without_current_revision` |
| M-06 (décaissements) | réglé | `paths/analysis.yaml:314-325` ; `indicators.yaml:559-565`, `:608-620` ; `cost_curve_payment_delays.json` (coût réel identique, à-venir = reste à engager) |
| M-07 (contribution d'une offre) | réglé | `paths/portfolio.yaml:196-203`, `:227-236`, `:261-268` ; `portfolio.yaml:255-269`, `:277-290`, `:327-338` |
| M-09 (revue précédente En cours) | réglé | `indicators.yaml:238-245` |
| M-10 (temps/temps) | réglé | `indicators.yaml:494-536` ; `paths/analysis.yaml:285-292` ; `milestone_tracking.json` sans le point du 15 décembre 2025 |
| M-11 (provisions hors EV, avancement, budget d'un sous-projet) | réglé | `indicators.yaml:324-330`, `:258-269` ; `revisions.yaml:1462-1470` (`TaskFacet.physical_progress`) |
| M-13 (bornes des zones) | réglé | `reference.yaml:892-903` ; `indicators.yaml:370-378` |
| M-14 (zone d'un indice conservé) | réglé | `indicators.yaml:373-378`, `:647-651`, `:679-681` |
| M-15 (taux de transformation) | réglé | `portfolio.yaml:97-103` ; `indicators.yaml:83-84` |
| M-16 (rythme constaté agrégé) | réglé | `portfolio.yaml:209-216` ; fixture BR/CPI vérifié |

## Annexe H — Risques et provisions

Périmètre : `docs/api/paths/risks.yaml` (634 l., en entier, 11 opérations) ; `docs/api/components/schemas/risks.yaml` (718 l., en entier) ; `docs/api/README-fr.md` (94 l., « Conventions » en entier) ; `components/parameters.yaml` (`RiskId`, `RiskRevision` 663–677, `Search`, `Limit`, `Offset`, `SortOrder`) ; `components/common.yaml` (`Decimal`, `Money`, `Percent`, `PlanningDate`, `LockVersion`, `ErrorCode` 394–700 et ses commentaires sur les provisions, `ProblemParams` 730–830, `ProblemRisk` 883–889, `BackgroundTaskRef.kind` 957) ; `components/responses.yaml` (`Forbidden`, `NotFound`, `Conflict`, `PreconditionFailed`, `LockVersionInvalid`, `UnprocessableEntity`) ; `schemas/projects.yaml` (`CommandCondition` 106–420, `ProjectCommand` 420–530) ; `schemas/revisions.yaml` (`RevisionCommand` 100–185, `StructureKind` 352, `StructureCreate` 459–470, `ComputedDependency` 957–1000, `EstimateLineFacet.budgeted_amount` 1608–1621, `UndoResult` 2094–2112) ; `schemas/exchanges.yaml` (`ReportRefusal` 544, `ImportDifference` 564–640) ; `schemas/reference.yaml` (`RiskMatrixSettings` 855–880, `AlertZone` 1088) ; `schemas/portfolio.yaml` (`PortfolioRisks` 274–322) et `paths/portfolio.yaml` (`getPortfolioRisks` 224–249) ; `schemas/indicators.yaml` (`RemainingIndicators` 199–235) ; `paths/revisions.yaml` (`abandonRevision` 145–205, `deleteNode` 1285–1370, `getStructureMergeReport` 744–778). **37 fixtures ouvertes** : les 32 que `risks.yaml` référence (`risks`, `risks_page`, `risks_empty`, `risk_created`, `risk_without_provision_category`, `risk_without_task`, `risk_provision_refused`, `risk_provision_task_refused`, `risk_probability_out_of_range`, `risk`, `risk_occurred_detail`, `risk_dismissed_category_deactivated`, `risk_uncited`, `risk_updated`, `risk_provision_frozen`, `risk_delete_cited`, `risk_delete_stale`, `risk_reviews`, `risk_reviews_reviewed`, `risk_reviewed`, `risk_dismissed`, `risk_reidentified`, `risk_review_occurred`, `risk_review_without_task`, `risk_review_probability_out_of_range`, `risk_occurrence_report`, `risk_occurrence_not_identified`, `risk_occurrence_sent`, `task_occurrence_queued`, `risk_occurrence_report_stale`, `risk_coverage`, `risk_matrix`), plus `risk_matrix_no_basis` (orpheline), `nodes_risk_occurred`, `nodes_risk_estimate`, `node_deleted_provision_moved`, `node_delete_last_provision_task_refused` ; `fixtures/examples.json` (clés `WF-RIS-*`) et la sortie de `make check-fixtures`. Spécification 1.0.1 : §3.2.6 (840–878), §3.4.3.5 WF-PTF-0090 (1560–1580), §3.4.3.7 WF-PTF-0110 (1594–1605), §3.4.4.3 WF-REF-0160 (1856–1872), §3.4.5.1 (1906–1950 : WF-REV-0010/0020/0030 ; WF-REV-0100 2022–2030), WF-PLA-0070 (2304), WF-DEV-0020 (2499), WF-RAE-0020 (2642), §3.4.5.6 en entier (2698–2807), WF-IHM-0030/0060/0090/0110/0130 (3210–3340), §4.4.1 (3847–3905), §4.4.2 (3980–4030), glossaire (4780–4848). `DECISIONS.md` : 596–640 (US-0230/L2), 1079 (EP-02/L17), 1511–1562 (EP-02/L30 : commandes des risques, saisie de la révision en cours), 2036–2050 (les risques engendrés), 5780–5796 (EP-14/L42s), 8264–8282, 8540–8590 (US-0640/L6), 8789–8830 (US-0680/L1), 9374–9440 (US-0701/L4), 9649, 9777, 9869 (US-0702/L1–L3), 9911 (US-0700/L1). Générateurs : `tools/src/wftools/mockwitnessrisks.py` (100–215), `mockhistory.py` (250–480, 836), `mockwitness.py` (548–585), `examples.py` (60–145). Front : `frontend/src/components/risks/address.ts`, `risk-bubble-chart.dom.test.tsx` (327, 341). Revue précédente : annexe H (2556–2693), M-01 (3626), M-04 (3732), M-05 (3760), J-21 (3045). Exclu : la version `1.0.0` et la règle d'après-gel (US-0640/L5), la part écran (US-0703).

### Synthèse

La famille a absorbé la passe de cohérence de la spécification : le coût à la survenance est un attribut du risque (`Risk.occurrence_cost`, exigé, nul hors survenu) que la couverture somme, la provision d'un survenu ou d'un écarté est celle de la référence, la probabilité ne s'écrit que par le réexamen, la réserve est un cumul à travers les références, l'abandon de la révision en cours défait les saisies des risques survenance comprise, et la place des tâches fusionnées est écrite sur `declareRiskOccurrence` et `RiskOccurrence`. Les onze opérations suivent les conventions du README : 404/403, 409 `STATE_FORBIDS_OPERATION` avec la première condition qui manque dans l'ordre des commandes, 412 et `lock_version` en paramètre sur `deleteRisk`, 400/422 sur toute écriture à corps, 401/503/500 partout, `pattern: '\S'` sur les libellés, décimaux en chaînes. Les fixtures sont arithmétiquement justes et cohérentes entre elles (réserve 850 060, couverture 349 860, cases de matrice sur les bornes du référentiel, `severity_ratio` au premier chiffre significatif, totaux de page sur les trois risques retenus).

Ce qui reste : le registre ne se filtre que par état, zone et libellé quand WF-IHM-0130 veut chaque colonne, et la revue périodique n'a rien pour trouver les risques non réexaminés (H-01) ; la modification d'un risque est une saisie de la révision en cours, créée au besoin et annulable, alors que la spécification 1.0.1 range libellé, description et mitigation dans les données du projet et ne la compte pas parmi les saisies de la révision — et `abandonRevision` le dit déjà à l'inverse d'`undoLastChange` (H-02) ; la seule image du résultat d'une survenance, `nodes_risk_occurred`, place les tâches fusionnées sous une tâche d'enveloppe « Risque survenu — … » que ni WF-RIS-0060 ni l'opération ne connaissent (H-03). Le reste est de la clarté : `may_create_revision` oubliée des 409 de quatre saisies, le 409 du compte rendu préalable réduit à `risk_identified`, l'historique qui ne dit pas que la déclaration et la survenance en sont des entrées, des exemples de refus et de variantes manquants, `risk_matrix_no_basis` toujours orpheline, des descriptions de `RiskWrite` qui parlent encore de la modification, et aucune fixture ne citant les exemples chiffrés des Vérif de WF-RIS-0010/0050/0060.

**10 constats : 0 bloquant, 3 majeurs, 7 mineurs. Suivi des 14 constats du 2026-10-28 (H-01 à H-10, M-01, M-04, M-05, J-21) : 11 réglés, 2 partiellement réglés (H-09, M-05), 1 non réglé (J-21), 0 sans objet.**

### Constats

#### H-01 — Le registre ne se filtre pas sur ses colonnes de nombres ni sur la date du dernier réexamen
- **gravité** : majeur
- **emplacement** : `docs/api/paths/risks.yaml:13-39` (`listRisks`, paramètres : `RiskRevision`, `Limit`, `Offset`, `states`, `zones`, `Search`, `sort_by`, `SortOrder`) ; `docs/api/components/parameters.yaml:663-677` (aucun paramètre de borne pour les risques) ; `frontend/src/components/risks/address.ts:4-24` (l'écran ne lit de son adresse que la recherche, le tri, la page et `states`).
- **spécification** : WF-IHM-0130 — « Toute table se filtre sur chacune de ses colonnes, et le filtre s'applique aux totaux qu'elle présente » ; WF-IHM-0060 — « Toute grille se filtre sur chacune de ses colonnes (WF-IHM-0130) » ; WF-RIS-0040 — « présente, pour chaque risque du projet : son libellé, sa probabilité, sa gravité, le montant de sa provision, son état et la date de son dernier réexamen … Elle se trie par montant de provision et se filtre par état » ; WF-RIS-0020, Vérif — « La revue périodique présente les risques dont la probabilité n'a pas été réexaminée » ; README, « Conventions » — « Une colonne de nombres se filtre par deux bornes, `<colonne>_min` et `<colonne>_max` … Une période se filtre par `from` et `to` … une date de planning sa fin incluse ».
- **le contrat dit** : « Le tri et les filtres sont faits par le serveur, et les totaux sont ceux des risques retenus (WF-IHM-0130) » (l. 9–10) ; `sort_by` offre les six colonnes (`label, probability, severity, provision_amount, state, last_review_on`), les filtres n'en offrent que deux (`states`, `zones`) et la recherche sur le libellé. Rien ne filtre `probability`, `severity`, `provision_amount` ni `last_review_on`.
- **la fixture dit** : —
- **décision** : `DECISIONS.md:302-312` « Toute liste se filtre sur ce que son écran présente (WF-IHM-0130). Les listes qui n'avaient que la recherche gagnent les filtres que la spécification nomme pour leur grille : … la zone des risques … Les totaux suivent les filtres » ; `:8574-8581` (#1367) n'ajoute que la pagination. Aucune décision n'exclut les autres colonnes ; la spécification 1.0.1 les exige (WF-IHM-0130, F0), et la règle « les totaux sont ceux des risques retenus » interdit au front de filtrer seul.
- **proposition** : ajouter à `listRisks`, par les conventions du README, `probability_min`/`probability_max` (`Percent`), `severity_min`/`severity_max` et `provision_amount_min`/`provision_amount_max` (`Money`), `last_review_on_from`/`last_review_on_to` (`PlanningDate`, fin incluse), avec les refus 422 `NUMBER_INVALID`, `DATE_INVALID` et `VALUE_OUT_OF_RANGE` sur `/query/<colonne>_max` ou `/query/last_review_on_to` ; dire que `last_review_on_to` est ce que la revue périodique emploie pour présenter les risques « dont la probabilité n'a pas été réexaminée » depuis le dernier marquage (WF-RIS-0020, WF-PTF-0110). Un exemple `risks_filtered` (par exemple `provision_amount_min=100000`, un seul retenu, totaux de ce seul risque). Ajout compatible, mais la règle des totaux fait du serveur le seul endroit où le mettre.

#### H-02 — La modification d'un risque est une saisie de la révision en cours, quand la spécification en fait une donnée du projet
- **gravité** : majeur (à trancher)
- **emplacement** : `docs/api/paths/risks.yaml:186-206` (`updateRisk`, description : « Une saisie de la révision en cours, créée au besoin et annulable (WF-RIS-0020, WF-IHM-0110) ») ; `docs/api/components/schemas/revisions.yaml:146-149` (`RevisionCommand.edit_risks` : « déclarer, modifier, réexaminer, supprimer un risque … une saisie de la révision en cours comme les trois autres, annulable ») et `:2097-2100` (`UndoResult` : « Les saisies de risque — création, modification, réexamen, suppression — sont dans le même historique ») ; `docs/api/paths/revisions.yaml:151-153` (`abandonRevision` : « Le libellé, la description et les actions de mitigation d'un risque qui reste sont des données du projet, que l'abandon ne change pas (WF-RIS-0020) »).
- **spécification** : WF-RIS-0020 — « Un risque appartient au projet : son libellé, sa description et sa note de mitigation sont des données du projet. Son évaluation — probabilité, état, structure propre et ligne de provision — est portée par chaque révision … La création, le réexamen, la suppression et la survenance d'un risque sont des saisies de la révision en cours ; lorsque le projet n'en comporte pas, la saisie en crée une au préalable » ; WF-IHM-0110 — « L'annulation porte sur les saisies directes : … création, réexamen et suppression de risques (WF-RIS-0020) » ; §4.4.1 (l. 3855) — régime **projet** : « les risques — identité, description et note de mitigation (WF-RIS-0020) » ; WF-RIS-0030 — « Le devis propre … chaque révision en fige une version » (le devis propre, pas le libellé).
- **le contrat dit** : la modification du libellé, de la description ou des actions de mitigation crée la révision en cours quand le projet n'en a pas (`ProjectCommand.edit_risks`, `projects.yaml:490-494` : « la saisie d'un risque crée la révision en cours ») et s'annule par `undoLastChange` ; `abandonRevision`, lui, dit que ces trois attributs sont « des données du projet, que l'abandon ne change pas ». Deux lectures incompatibles d'un même acte : annulable par l'historique de la révision, mais hors de ce que l'abandon de cette révision défait.
- **la fixture dit** : `risk_updated.json` modifie les actions de mitigation et déplace la ligne de provision dans la même écriture (version 2).
- **décision** : `DECISIONS.md:1524-1551` « La saisie des risques est une saisie de la révision en cours … Deux formes du contrat, que la spécification ne dictait pas mot pour mot : la modification d'un risque (`updateRisk`) est, comme le réexamen et la suppression, une saisie de la révision en cours, annulable et créatrice de la révision au besoin — chaque révision fige une version des risques, libellé et devis propre compris (WF-RIS-0030) » — **contredite par la spécification 1.0.1** : WF-RIS-0030 ne fige que le devis propre, WF-RIS-0020 et §4.4.1 rangent le libellé dans les données du projet, et WF-IHM-0110 n'annule pas la modification. La catégorie, le sous-projet et la tâche de la provision, eux, sont bien une saisie de la révision (la ligne de provision est révisionnée).
- **proposition** : à trancher. (a) Suivre la spécification : `updateRisk` écrit le libellé, la description et les actions de mitigation comme données du projet — sans créer de révision, hors de l'historique d'annulation, sans effet de l'abandon —, et seule la part provision (`provision_cost_category_id`, `provision_subproject_id`, `provision_task_id`) est une saisie de la révision en cours, créée au besoin et annulable ; la description, `RevisionCommand.edit_risks`, `ProjectCommand.edit_risks` et `UndoResult` le disent, et `may_create_revision` ne manque à `update` que si la provision change. Ou (b) garder la forme et faire écrire à la spécification que la modification est une saisie de la révision (WF-RIS-0020, WF-IHM-0110, §4.4.1), en retirant d'`abandonRevision` la phrase sur les données du projet. Dans les deux cas, réécrire la décision 1548–1551.

#### H-03 — La structure obtenue par la survenance du témoin enveloppe les tâches fusionnées sous une tâche que la règle ne prévoit pas
- **gravité** : majeur (fixture d'une autre famille, `listNodes`, mais seule image du résultat de `declareRiskOccurrence`)
- **emplacement** : `fixtures/api/nodes_risk_occurred.json:2` (summary : « ses deux tâches, terminées en mai — la relance … le transport … ») et `value` (541 « Risque survenu — Retard de livraison des armoires », parent 551, `automatic` ; 542 « Relance du fournisseur », parent 541, `manual` ; 544 « Transport exceptionnel », parent 541) ; `tools/src/wftools/mockwitness.py:561-563` (`Task(N.MERGED, "Risque survenu — Retard de livraison des armoires", children=(…))`) ; `docs/api/paths/risks.yaml:488-492` (`declareRiskOccurrence`).
- **spécification** : WF-RIS-0060 — « Les tâches de premier niveau du devis propre sont placées, dans leur ordre, en dernière position sous la tâche qui portait la ligne de provision ; leurs subordonnées, leurs liaisons internes, leurs durées et leurs modes sont conservés » ; Vérif — « Les tâches fusionnées se trouvent sous la tâche qui portait la provision ».
- **le contrat dit** : « Les tâches de premier niveau du devis propre sont placées, dans leur ordre, en dernière position sous la tâche qui portait la ligne de provision » (l. 488–490) ; `RiskOccurrenceReport.differences` (schémas l. 477–493) : « ses tâches de premier niveau en dernière position sous la tâche qui porte la ligne de provision … la tâche porteuse modifiée (`updated`), devenue la récapitulative de ces tâches ». Le compte rendu de 751 (`risk_occurrence_report.json:9-13`) le fait : « Diagnostic des défauts de câblage » et « Reprise du câblage des armoires » ajoutées directement sous le « Câblage des armoires », sans enveloppe.
- **la fixture dit** : pour 752, les deux tâches du devis propre (542, 544) ne sont pas sous le « Poste de commande » (551), porteur de la provision, mais sous une tâche 541 « Risque survenu — Retard de livraison des armoires » que rien ne rattache au devis propre — son libellé dit l'état du risque, pas une tâche chiffrée avant la survenance — et dont le « Poste de commande » n'est pas devenu la récapitulative directe. Aucune fixture ne montre la structure 205 (le devis propre de 752) avant la fusion pour trancher.
- **décision** : `DECISIONS.md:9421-9434` (US-0701/L4, M-05) « Le témoin tient la règle de placement : le sous-arbre fusionné (541, « Risque survenu — Retard de livraison des armoires ») est le dernier enfant du « Poste de commande » (551) » — la décision prend 541 pour le sous-arbre fusionné sans dire qu'il était une tâche du devis propre ; si c'est une enveloppe, elle contredit WF-RIS-0060 et le texte même de l'opération.
- **proposition** : à trancher dans le générateur. Soit 541 est la tâche racine unique du devis propre de 752 : lui donner un libellé de devis propre (« Retard de livraison des armoires », comme 531/533 pour 751), le dire dans le summary, et ajouter l'exemple `nodes_risk_estimate_occurred` (structure 205 lue dans la référence 101, qui la fige avant la fusion, WF-RIS-0030) pour que la correspondance se lise. Soit c'est une enveloppe : la retirer, placer 542 et 544 en dernière position sous 551, et dire dans le summary que le « Poste de commande » est devenu leur récapitulative (`fields` `duration`, `start`, `finish` au compte rendu). Dans les deux cas, réécrire la ligne 9432 de la décision.

#### H-04 — `may_create_revision` manque aux 409 des quatre saisies des risques
- **gravité** : mineur
- **emplacement** : `docs/api/paths/risks.yaml:104-124` (`createRisk`, 409 : `project_not_terminal`, `no_background_task_running`, `at_least_one_task`, `active_provision_category`), `:224-238` (`updateRisk`), `:292-304` (`deleteRisk`), `:394-414` (`reviewRisk`) ; `:540-556` (`declareRiskOccurrence`, qui la nomme : « puis `may_create_revision`, sans révision en cours, pour qui n'a pas `revisions.write` »).
- **spécification** : WF-RIS-0020 — « lorsque le projet n'en comporte pas, la saisie en crée une au préalable » ; WF-IHM-0090 — « Tout refus nomme la condition manquante ».
- **le contrat dit** : `ProjectCommand.edit_risks` (`projects.yaml:490-494`) : « la saisie d'un risque crée la révision en cours (WF-RIS-0020), et nomme `may_create_revision` à qui n'a pas la permission de la créer » ; `ProjectCommand.declare_risk` (`:496-499`) : « puis `at_least_one_task` et `active_provision_category`, puis `may_create_revision` » ; `CommandCondition` (`:177-181`) : « `may_create_revision` manque … à la saisie des risques (`ProjectCommand.edit_risks`), la déclaration d'un risque (`ProjectCommand.declare_risk`) ». Les 409 de `createRisk`, `updateRisk`, `reviewRisk` et `deleteRisk` ne la nomment pas : un serveur qui suit l'opération ne saurait pas quoi rendre à un chiffreur sans `revisions.write` sur un projet sans révision en cours.
- **la fixture dit** : aucun exemple de ce refus pour les risques (`merge_may_create_revision_refused` existe pour la fusion).
- **décision** : `DECISIONS.md:5780-5790` (EP-14/L42s) « puis les autres conditions d'`edit_risks`, `may_create_revision` sur le projet » ; `:1533-1534`. Tient ; le 409 des opérations ne la reprend pas (H-09 de la revue précédente, réglé pour `project_not_terminal` et `no_background_task_running` seulement).
- **proposition** : dans les quatre 409, après les conditions propres : « puis `may_create_revision`, quand le projet n'a pas de révision en cours, pour qui n'a pas `revisions.write` (WF-RIS-0020 ; `ProjectCommand.edit_risks`) », dans l'ordre que `ProjectCommand.declare_risk` donne ; un exemple engendré `risk_may_create_revision_refused` (le chiffreur de `project_pricing_estimator`, projet sans révision en cours).

#### H-05 — Le 409 du compte rendu préalable ne nomme que `risk_identified`
- **gravité** : mineur
- **emplacement** : `docs/api/paths/risks.yaml:456-458` (« Refusée par 409 pour un risque qui n'est pas identifié, comme sa survenance ») et `:472-483` (409 : « `params.missing_condition` à `risk_identified`, la condition que la commande `declare_occurrence` du risque dit manquer ») ; comparer `docs/api/paths/revisions.yaml:767-771` (`getStructureMergeReport`, 409 : « la première condition qui manque, comme au 409 de sa fusion (`mergeCostStructure`) »).
- **spécification** : WF-RIS-0060 ; WF-IHM-0090 — « Tout refus nomme la condition manquante ».
- **le contrat dit** : `declareRiskOccurrence` (l. 540–556) juge, dans l'ordre, `project_not_terminal`, `reference_revision_designated`, `no_background_task_running`, `risk_identified`, `may_create_revision` ; le compte rendu, « sur le modèle de `getStructureMergeReport` », n'en déclare qu'une. Sur un projet terminal, sans révision de référence ou pendant une survenance qui court, le compte rendu rend-il 200 (un compte rendu d'une survenance que la confirmation refusera) ou 409 ? Le modèle qu'il cite rend 409 pour toute condition de la fusion.
- **la fixture dit** : `risk_occurrence_not_identified.json`, partagé par les deux opérations (bien).
- **décision** : `DECISIONS.md:8800-8803` (US-0680/L1) « sur le modèle de `getStructureMergeReport` : sans 403, comme toute lecture du projet » — rien sur les conditions du 409. Aucune.
- **proposition** : aligner sur le modèle : « `STATE_FORBIDS_OPERATION`, `params.missing_condition` la première condition qui manque, dans l'ordre où le 409 de la survenance les juge (`declareRiskOccurrence`) : celles du projet, puis celles du risque ; un compte rendu ne se lit pas d'une survenance qui ne s'appliquerait pas ». Un exemple de plus n'est pas nécessaire si l'on garde `not_identified`.

#### H-06 — L'historique ne dit pas que la déclaration et la survenance en sont des entrées, et `actor` n'est pas exigé
- **gravité** : mineur
- **emplacement** : `docs/api/paths/risks.yaml:322-334` (`listRiskReviews`) ; `docs/api/components/schemas/risks.yaml:342-353` (`RiskReview` : « l'acte par lequel un utilisateur confirme ou modifie la probabilité et l'état d'un risque » ; `actor` hors de `required`) ; `:135-140` (`Risk.last_review_on` : « sa déclaration, un réexamen (`reviewRisk`) ou sa survenance »).
- **spécification** : WF-RIS-0010 — « Il conserve l'historique de ses réexamens : la date de chacun, et la probabilité, la gravité et l'état retenus » ; WF-RIS-0040 — « l'historique de ses réexamens, qui montre l'évolution de sa probabilité et de sa gravité ».
- **le contrat dit** : `RiskReview.state` admet `occurred` (par `RiskState`), `last_review_on` compte la déclaration et la survenance, mais `listRiskReviews` et `RiskReview` ne disent pas que l'identification est la première entrée ni que la survenance est la dernière, à l'état `occurred`, sa gravité retenue étant le coût à la survenance. `actor` est rendu par les sept entrées des deux fixtures et n'est pas exigé : le client généré le typera optionnel.
- **la fixture dit** : `risk_reviews.json:7` — l'entrée du 12 janvier 2026 (déclaration de 751, 25 %, 1 000 000,00) ; aucun historique d'un risque survenu (752) alors que `risk_occurred_detail` en est l'autre face.
- **décision** : `DECISIONS.md:2041-2042` « leurs réexamens datés — l'identification la première, la survenance la dernière » ; `:9391` « la gravité que retient le réexamen de sa survenance ». Tient ; le contrat ne le dit pas.
- **proposition** : `listRiskReviews` : « La déclaration est la première entrée, à la probabilité et à la gravité déclarées ; la survenance la dernière, à l'état `occurred`, sa gravité retenue étant le coût à la survenance (`Risk.occurrence_cost`) ; un réexamen refusé n'en ajoute aucune. » `RiskReview.actor` dans `required`. Exemple engendré `risk_reviews_occurred` (752 : 12 janvier identifié 0,3/200,00 ; 20 février `occurred` 0,3/200,00).

#### H-07 — Refus déclarés et variantes sans exemple
- **gravité** : mineur
- **emplacement** : `docs/api/paths/risks.yaml:131-157` (`createRisk` 422 : trois exemples pour sept motifs) ; `:224-242` (`updateRisk` 409 : `provision_frozen` seul, rien pour `risk_not_occurred`) et `:244-256` (`updateRisk` 422 : aucun exemple) ; `:292-306` (`deleteRisk` 409 : `cited` seul, rien pour `risk_not_occurred` qui « l'emporte ») ; `:394-417` (`reviewRisk` 409 : rien pour `active_provision_category`) et `:419-430` (422 : rien pour `/provision_cost_category_id` au retour d'un écarté) ; `:540-557` (`declareRiskOccurrence` 409 : rien pour `reference_revision_designated` ni `may_create_revision`) ; `:463-471` (`getRiskOccurrenceReport` 200 : `witness` seul — ni `refusals` non vide, ni `creates_current_revision` vrai, ni jalon porteur).
- **spécification** : WF-RIS-0010, Vérif — « Avec deux catégories actives de type provision pour risques, la déclaration d'un risque demande laquelle porte sa provision » ; « Un risque écarté dont la catégorie a été désactivée redevient identifié avec la catégorie active choisie » ; WF-RIS-0060, Vérif — « La survenance d'un risque dont la provision était portée par un jalon place ses tâches après ce jalon ».
- **le contrat dit** : chaque motif est décrit (`VALUE_REQUIRED` omise parmi plusieurs, `UNKNOWN_COST_CATEGORY`, `INACTIVE_REFERENCE_OBJECT`, `/label` vide ou trop long ; `risk_not_occurred` sur `updateRisk` et `deleteRisk` ; `active_provision_category` sur `reviewRisk`) sans exemple sous l'opération qui le rend. Le catalogue est couvert ailleurs (`test_contract_catalogue.py`, US-0702/L1), mais l'implémenteur de chaque opération n'a rien à lire pour ces variantes, et `risk_dismissed_category_deactivated` (l. 2 : « son retour à l'état identifié en demande une autre ») annonce un réexamen dont aucun exemple ne montre le corps ni le refus.
- **la fixture dit** : —
- **décision** : `DECISIONS.md:9677-9681` (US-0702/L1 : « chaque code est porté par un exemple, sans liste d'attente ») — tient pour le catalogue, pas par opération.
- **proposition** : engendrer (`wftools.mockriskwrites`) : `risk_category_required` (deux catégories actives, 422 `VALUE_REQUIRED` sur `/provision_cost_category_id`), `risk_category_inactive` (422 `INACTIVE_REFERENCE_OBJECT`), `risk_update_occurred` (409 `risk_not_occurred` de `updateRisk` sur 752), `risk_update_label_blank` (422 `/label` `VALUE_REQUIRED`), `risk_delete_occurred` (409 `risk_not_occurred` sur 752), `risk_review_without_provision_category` (409), `risk_reidentified_category_chosen` (corps `RiskReviewWrite` avec `provision_cost_category_id`, pendant de `risk_dismissed_category_deactivated`), `risk_occurrence_without_reference` (409 `reference_revision_designated`), `risk_occurrence_report_refused` (`refusals` à `TASK_WITHOUT_WORKING_HOURS`) et, si le témoin le permet, `risk_occurrence_report_milestone` (jalon porteur). Au moins les refus 409 des deux états.

#### H-08 — `risk_matrix_no_basis.json` est toujours orpheline
- **gravité** : mineur
- **emplacement** : `fixtures/api/risk_matrix_no_basis.json` ; `docs/api/paths/risks.yaml:623-631` (`getProjectRiskMatrix`, un seul exemple, `witness`) ; engendrée par `tools/src/wftools/mockhistory.py:836-846` (`matrix(reference_rows(), Decimal(0))`) ; lue par `frontend/src/components/risks/risk-bubble-chart.dom.test.tsx:327,341` (`example("risk_matrix_no_basis")`).
- **spécification** : WF-REF-0160 — l'assiette « son budget de référence ou, tant qu'il n'en a pas, le total hors provisions du devis de sa révision courante » ; WF-RIS-0040.
- **le contrat dit** : `RiskMatrixCell` (schémas l. 509–521) et `RiskMatrixPoint.severity_ratio` (l. 564–577) décrivent l'assiette nulle (`no_reference_budget`, niveau 1, bulle non tracée, #1240) sans qu'aucune réponse n'en montre un exemple : c'est la seule fixture de `fixtures/api/` que le contrat ne référence pas (brief, 705 fixtures). Elle existe parce que US-0230/L2 (#1240, `DECISIONS.md:7809`) l'a engendrée comme « variante contrefactuelle » et que le test du front la consomme par `example()`, qui lit le fichier et non le contrat ; US-0700/L1 (`DECISIONS.md:9972`) l'a régénérée (une case comptée, les trois points) sans la référencer. Le faux back ne la sert donc pas, et un front qui ne lit que le contrat ne sait pas à quoi ressemble une matrice sans assiette.
- **la fixture dit** : cohérente avec le schéma et `risk_matrix` (mêmes niveaux, zones, totaux ; `cells` (3,1) à 1 pour le seul identifié ; `severity_ratio` non calculable, `zone` `nominal` pour les trois).
- **décision** : `DECISIONS.md:7809` « `risk_matrix_no_basis`, variante contrefactuelle, le registre du témoin lu sur une assiette nulle » — tient ; J-21 de la revue précédente non réglé.
- **proposition** : `no_basis: { $ref: ../../../fixtures/api/risk_matrix_no_basis.json }` sous le 200 de `getProjectRiskMatrix` ; la retirer n'est pas une option tant que le test du front la lit. Le summary peut en profiter pour dire que le cas est celui d'un projet en chiffrage dont le devis ne porte encore que des provisions, et non du témoin.

#### H-09 — Descriptions à aligner : `RiskWrite` parle de la modification, `RiskRevision` oublie l'écarté
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/risks.yaml:262-298` (`RiskWrite.provision_cost_category_id` : « À la modification, omise, elle reste celle du risque ; `INACTIVE_REFERENCE_OBJECT` ne vaut que si la valeur change la catégorie du risque … une autre, envoyée pour un risque qui n'est pas identifié, est refusée par 409 » ; `provision_subproject_id` : « À la modification, omis, il reste celui du risque ; `null` retire … » ; `provision_task_id` : « À la modification, omise, elle reste celle du risque … Changée pour un risque qui n'est pas identifié … ») ; `docs/api/components/parameters.yaml:675-676` (`RiskRevision` : « La provision d'un risque survenu est celle qu'il avait dans la révision de référence (WF-RIS-0050) ») ; `fixtures/api/risk_occurrence_not_identified.json:2` (« nomme la condition qui manque (risks) »).
- **spécification** : WF-RIS-0040 — « les risques survenus, et les risques écartés, chacun pour la provision qu'ils portaient dans la révision de référence ».
- **le contrat dit** : `RiskWrite` n'est le corps que de `createRisk` depuis que `RiskUpdate` (l. 299–340) est défini en propre (H-04 de la revue précédente, US-0701/L4) ; ses trois descriptions gardent les règles de la modification, que `RiskUpdate` redit (l. 316–339) : un lecteur du corps de création y lit des règles qui ne le concernent pas, et deux textes à maintenir. `RiskRevision` ne parle que du survenu quand `Risk.provision_amount` (l. 55–62) dit « survenu ou écarté ». Le summary de `risk_occurrence_not_identified` porte un « (risks) » qui ne désigne rien.
- **la fixture dit** : —
- **décision** : `DECISIONS.md:9403-9408` (H-04 : « `RiskUpdate` est défini en propre ») — tient ; le nettoyage n'a pas suivi.
- **proposition** : dans `RiskWrite`, couper les phrases « À la modification … » et renvoyer : « À la modification, voir `RiskUpdate` » ; `RiskRevision` : « La provision d'un risque survenu ou écarté est celle qu'il avait dans la révision de référence (`Risk.provision_amount`, WF-RIS-0040, WF-RIS-0050) » ; retirer « (risks) » du summary (générateur `mockriskwrites.py:576`).

#### H-10 — Les exemples chiffrés des Vérif de WF-RIS-0010, 0050 et 0060 ne sont cités par aucune fixture
- **gravité** : mineur
- **emplacement** : `fixtures/examples.json:294-333` (`WF-RIS-0010-A#bd03f92aacb4`, `#43948c17123a`, `WF-RIS-0050-A#ba9e53e8bcb3`, `#ac2fca05619d`, `#b4385225e6ae`, `#921a20810dcf`, `#f3002ed87630`, `WF-RIS-0060-A#474d7bce167a`) ; sortie de `make check-fixtures` : les huit sont « not covered » ; `fixtures/api/nodes_risk_occurred.json`, `risk_occurred_detail.json`, `risk_coverage.json`, `node_deleted_provision_moved.json` (aucune clé `examples`).
- **spécification** : WF-QUA-0020 (« Les exemples chiffrés du document sont des cas de test ») ; WF-RIS-0060, Vérif — « deux lignes de 120 et 80 … montants budgétés nuls et … réestimés de 120 et 80 ; la ligne de provision a disparu … le reste à engager a augmenté de 200 moins la provision retirée » ; WF-RIS-0050, Vérif — « un risque de gravité 200 à 30 %, le devis totalise 1 060, le budget de référence 1 000 et la réserve 60 … » ; WF-RIS-0010, Vérif — « La suppression de la tâche qui porte une provision de 40 laisse le devis inchangé, la provision étant passée sur la tâche parente » ; « Un risque déclaré sur le sous-projet S2 porte sa provision au reste à engager de S2 ».
- **le contrat dit** : les fixtures citent un exemple par une clé `examples: [...]` (`tools/src/wftools/examples.py:82-90`) ; aucune fixture des risques n'en porte. Or le témoin réalise l'exemple de WF-RIS-0060 à la lettre (752 : lignes de 120 et 80, budgété nul, réestimé 120 et 80, provision retirée — `nodes_risk_occurred`, `risk_occurred_detail`, `mockwitnessrisks.py:148` « the delay at the figures of its Vérif ») sans le citer ; la règle de WF-RIS-0010 (report sur la parente, devis inchangé) est réalisée par `node_deleted_provision_moved` avec 500 000,00 au lieu de 40 ; les exemples de WF-RIS-0050 (projet à 1 000) ne sont réalisés nulle part, le témoin étant à l'échelle 1 000 (`RISK_SCALE`, `mockwitness.py:247`) et n'ayant qu'une référence (`DECISIONS.md:9414-9416`).
- **la fixture dit** : —
- **décision** : `DECISIONS.md:9385-9395` « `tools/tests/test_mockriskcoverage.py` tient le Vérif de WF-RIS-0050 » — le test le tient, la fixture ne le cite pas. Aucune décision sur la citation.
- **proposition** : citer `WF-RIS-0060-A#474d7bce167a` dans `nodes_risk_occurred` et `risk_occurred_detail` (clé `examples`, engendrée) ; citer `WF-RIS-0010-A#bd03f92aacb4` dans `node_deleted_provision_moved` si l'on admet qu'un exemple se cite à une autre échelle, sinon le dire dans son summary ; pour WF-RIS-0050, soit une fixture contrefactuelle `risk_coverage_verif` (réserve 60, provisions restantes 0, coût des survenus 250, écart −190 : un projet à 1 000, `CalculationContext` d'une autre révision) qui cite les cinq clés, soit accepter la liste « not covered » et le dire dans `DECISIONS.md`. À trancher.

### Ce qui est juste

- **Le coût à la survenance** (H-01, H-02 de la revue précédente) : `Risk.occurrence_cost` (schémas l. 63–71) exigé, nul hors survenu, « que ni les réestimations ni la terminaison des tâches fusionnées ne changent » ; `RiskCoverageTotals.occurred_cost` (l. 695–700) en est la somme ; `getProjectRiskCoverage` (paths l. 579–590) et `risk_coverage.json` (200,00 « que la terminaison de ses tâches fusionnées ne change pas ») le disent ; `computed_fields` le nomme (`occurrence_estimate`, `ComputedDependency` revisions.yaml l. 980–982) ; `declareRiskOccurrence` (l. 500–502) le fixe ; `PortfolioRisks.coverage` le reprend.
- **La provision d'un survenu ou d'un écarté** (H-03) : `Risk.provision_amount` (l. 55–62) tranchée — provision de référence, `0.00` hors référence — ; les fixtures suivent (`risk_dismissed` : 751 écarté à 250 000,00, sa provision au 1er février, non 500 000,00 ; `reference_provision` dans `mockwitnessrisks.py:180-188`) ; `computed_fields` dit `reference_provision` pour les deux états ; `ProvisionTotals` somme des grandeurs homogènes.
- **La probabilité par le seul réexamen** (H-04) : `RiskUpdate` (l. 299–340) sans `probability`, `updateRisk` (l. 189–192) et `Risk` (l. 42–43) le disent ; `reviewRisk` « seule écriture de la probabilité » ; la confirmation sans modification produit un réexamen daté (`risk_reviewed`, `risk_reviews_reviewed` : entrée du 3 juin, version 5).
- **La réserve cumulée** (M-01) : `RiskCoverageTotals.reserve` (l. 680–690) dit la règle une fois (« à chaque nouvelle référence, la réserve garde ce qu'elle devait aux risques sortis de l'état identifié. Un avenant ne la diminue jamais ») ; `ProvisionTotals.reserve` (l. 665–667) et `EstimateLineFacet.budgeted_amount` (revisions.yaml l. 1616–1618) y renvoient ; 850 060,00 = 250 000 + 60 + 600 000, les provisions au marquage du 1er février (`risk_reviews` à l'appui) ; couverture 850 060 − 500 000 − 200 = 349 860.
- **L'abandon** (M-04) : `abandonRevision` (revisions paths l. 148–153) et `RiskState` (l. 3–10), `RiskOccurrence` (l. 401–403), `declareRiskOccurrence` (l. 505–507) disent la survenance définitive « sauf par l'abandon », le survenu « identifié avec sa ligne de provision, sans coût à la survenance », conformes à la Vérif de WF-RIS-0020.
- **La place des tâches fusionnées** (M-05, règle) : `declareRiskOccurrence` (l. 488–499) et `RiskOccurrenceReport.differences` (l. 477–493) disent la dernière position sous la porteuse, le jalon porteur « qui reste un jalon sans sous-tâche », la conservation des subordonnées, liaisons, durées et modes, le mode manuel d'une tâche sans prédécesseur aux dates du devis propre, le réestimé « que ses grandeurs et ses dates donnent », l'absence de rattachement au lotissement (WF-PLA-0170) ; `nodes_risk_occurred` rend 542 « Relance du fournisseur » en `manual` du 4 au 8 mai 2026 (mot pour mot la décision 9427–9430).
- **La suppression de la tâche porteuse** (H-05) : `deleteNode` (revisions paths l. 1294–1301, 409 l. 1352–1360) : la ligne passe sur la parente ou la première tâche de premier niveau restante, `nodes` la rend écrite, le total du devis inchangé, le risque voit sa tâche et son compteur changer ; refus `at_least_one_task` avec `params.risks[]` (`ProblemParams.risks`, common.yaml l. 797–805, `ProblemRisk`) ; `node_deleted_provision_moved`, `node_delete_last_provision_task_refused`.
- **Le 409 de la survenance** (H-08) : `declareRiskOccurrence` (l. 540–556) nomme les cinq conditions dans l'ordre des deux commandes (`ProjectCommand.declare_risk_occurrence`, `RiskCommand.declare_occurrence`), exemple `risk_occurrence_not_identified` ; `reference_revision_designated` décrite dans `CommandCondition` (projects.yaml l. 135–136).
- **`states`, et les conditions d'état des trois saisies** (H-09, pour l'essentiel) : `states` décrit ; les 409 d'`updateRisk`, `reviewRisk`, `deleteRisk` nomment `project_not_terminal` puis `no_background_task_running` « jugées avant celles du risque, comme à la déclaration ».
- **Les champs exigés de `Risk`** (H-07) : `description`, `mitigation_notes`, `provision_node_id`, `matrix_cell`, `last_review_on` dans `required` (l. 14–37), nullables où il faut.
- **L'assiette** (H-06) : `RiskMatrixLevel` (l. 523–537), `RiskMatrix.severity_levels` (l. 616–623), `getProjectRiskMatrix` (l. 610–615), `RiskMatrixSettings` (reference.yaml l. 858–862) : « l'assiette du projet — son budget de référence ou, avant lui, le total hors provisions du devis de sa révision courante ».
- **Le portefeuille** (H-10) : `PortfolioRisks` (l. 277–283, 309–316) et `getPortfolioRisks` (l. 234–236) : « en cours et terminés du périmètre » ; `identified_total` décrit comme `ProvisionTotals.identified` de chaque projet, sans pondération.
- **Le compte rendu préalable** (US-0680) : `RiskOccurrenceReport` et `RiskOccurrence` portent les deux compteurs et `creates_current_revision`, le 412 de la confirmation rend le compteur du risque « et rien d'autre, comme tout 412 (#296) » ; `Risk.lock_version` avance à toute saisie du devis propre (l. 167–175), ce que le compte rendu exploite ; `risk_occurrence_report` (compteurs 1 et 4, comme `structures` et `risk`), `risk_occurrence_sent`, `risk_occurrence_report_stale` (`expected_lock_version` 4) sont cohérents ; les `differences` suivent l'ordre déclaré (ajouts dans l'ordre du plan, porteuse `updated` par `duration`, `start`, `finish`, provision `removed`).
- **La matrice** (US-0700/L1) : `cells` ne compte que les identifiés (une case à 1 pour 751, l. 624–638), `points` rend les trois avec leur état, `totals` sur les trois états ; cases recalculées sur les bornes 0,1/0,3/0,6 et 1 %/5 %/10 % (« égale à une borne relève du niveau supérieur », 752 à 30 % au niveau 3) ; `severity_ratio` 0,000003 pour 200/68 241 568,05 (premier chiffre significatif, README) ; `RiskMatrixPoint` nomme son projet dans le portefeuille seulement.
- **Les commandes et leurs conditions** : `RiskCommand` (l. 187–212) : `update_provision` « toujours listée avec `update` », ne nomme que `risk_identified` ; un survenu n'a aucune commande disponible (`risk_occurred_detail`) ; `delete` liste `risk_not_occurred` puis `risk_not_cited`, le 409 n'en nomme qu'une, `risk_not_occurred` l'emportant ; un projet terminal n'en liste aucune (US-0702/L3) ; `risk_uncited` montre la suppression disponible ; toutes les conditions nommées (`risk_identified`, `risk_not_occurred`, `risk_not_cited`, `at_least_one_task`, `active_provision_category`, `restored_subproject_exists`, `may_create_revision`, `reference_revision_designated`, `no_background_task_running`, `project_not_terminal`) sont dans `CommandCondition` ; la préséance 409 avant 422 (#747) est écrite sur les trois saisies ; `createRisk` promet la structure propre (`structure_id`), la ligne de provision (`provision_node_id`) et sa tâche (`provision_task`), et `StructureCreate` (revisions.yaml l. 459–470, `kind` restreint à `amendment`) renvoie à lui pour le devis propre « qui naît avec lui et disparaît avec lui » : les deux textes concordent.
- **Les conventions** : `lock_version` en paramètre exigé sur `deleteRisk`, 412 déclaré avec exemple (`risk_delete_stale`), 422 `LockVersionInvalid` ; 412 sur `updateRisk` et `reviewRisk` ; 400/422 sur les quatre écritures à corps ; 401/503/500 sur les onze ; `pattern: '\S'` et `maxLength: 300` sur `label` ; `probability` un rapport 0–1 (`VALUE_OUT_OF_RANGE`, `params.maximum` « 1 ») ; `explode: false` sur `states` et `zones` ; pagination `limit`/`offset`/`meta` et totaux sur tous les retenus (`risks_page` : deux risques, `meta.total` 3, totaux des trois) ; `BackgroundTaskRef.kind` connaît `risk_occurrence` ; `INVENTORY.md:213-227` cite les bonnes exigences pour les onze opérations ; la catégorie de la provision : `provision_cost_category_is_active` calculé à la lecture, la désactivation d'une nature désactivant ses catégories (C-291), le retour d'un écarté avec `RiskReviewWrite.provision_cost_category_id` ignorée quand la catégorie est encore valable, hors sous-projet quand il a été supprimé (#732), sur la première tâche de premier niveau quand la sienne a disparu (#1227) — `risk_reidentified` (753 sur « Mise en service », ligne 586).

### Doutes

- **La réserve « sur les risques retenus »** (`ProvisionTotals`, l. 649–667 : « calculés par le serveur sur les risques retenus — tous ceux que les filtres retiennent » ; `risks_empty.json` : `reserve` à `0.00` « dont les filtres n'en retiennent aucun »). WF-RIS-0040 présente « la réserve pour risques (WF-RIS-0050) … en regard » et WF-RIS-0050 en fait une grandeur de la référence, un seul chiffre ; WF-IHM-0130 veut que le filtre s'applique « aux totaux qu'elle présente ». La décision `DECISIONS.md:624-629` (auteur, 2026-10-06) a choisi la réserve sur les retenus, et M-01 l'a laissée : avec une réserve désormais cumulée à travers les références, la part de réserve d'un risque sorti de l'état identifié avant la référence précédente n'est définie nulle part, et un filtre `states=identified` montrerait 250 000,00 là où la couverture dit 850 060,00. À confirmer ou à préciser (la réserve une fois, non filtrée, comme la couverture).
- **`reference_revision_designated` pour la survenance** (`declareRiskOccurrence` l. 544–545 ; `CommandCondition` projects.yaml l. 135–136 : « tant que le projet n'a pas de révision de référence, à la déclaration d'un risque survenu (`declare_risk_occurrence`, WF-RIS-0060) »). WF-RIS-0060 ne pose pas cette condition ; elle refuse la survenance d'un risque d'un projet en chiffrage, où le devis propre pourrait pourtant rejoindre le devis. La décision `DECISIONS.md:1511-1521` ne la nomme pas (« les conditions du projet restent sur `ProjectCommand.declare_risk_occurrence` »), et aucune autre ne l'explique. Si elle tient (le coût à la survenance n'a de sens que face à une réserve), le dire dans la spécification ou dans `DECISIONS.md` ; sinon la retirer.
- **La couverture d'un projet sans révision de référence** (`getProjectRiskCoverage`, `RiskCoverageTotals` exige quatre `Money`) : `reserve` à `0.00` et l'écart négatif de toutes les provisions, ou couverture non calculable comme la marge sur le budget (WF-RAE-0020, Vérif : « sur un projet sans révision de référence, la marge sur le budget l'est aussi [absente] ») ? Non dit ; aucun exemple. Le portefeuille (`PortfolioRisks.coverage`) exclut les projets en chiffrage pour cette raison.
- **Le compte rendu préalable d'un projet sans référence** : avec H-05 non tranché, `getRiskOccurrenceReport` rend 200 là où `declareRiskOccurrence` refuserait par `reference_revision_designated`.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| H-01 | réglé | `schemas/risks.yaml:669-700` (`RiskCoverageTotals.occurred_cost` : coût à la survenance, « que ni les réestimations ni la terminaison … ne changent ») ; `paths/risks.yaml:579-590` ; `risk_coverage.json:2` ; `DECISIONS.md:9385-9392`. |
| H-02 | réglé | `schemas/risks.yaml:22,63-71` (`Risk.occurrence_cost`, exigé, nul hors survenu) ; `risks.json`, `risk_occurred_detail.json` à `"200.00"`, les autres à `null` ; `ComputedDependency.occurrence_estimate`. |
| H-03 | réglé | `schemas/risks.yaml:55-62` (`Risk.provision_amount` : provision de référence pour survenu et écarté, `0.00` hors référence) ; `risk_dismissed.json` à 250 000,00 ; `mockhistory.py:293`. Reste `RiskRevision` qui ne dit que « survenu » (H-09 de cette revue). |
| H-04 | réglé | `schemas/risks.yaml:299-340` (`RiskUpdate` en propre, sans `probability`) ; `paths/risks.yaml:189-192` ; `risk_update_probability_out_of_range` retiré ; `DECISIONS.md:9403-9408`. |
| H-05 | réglé | `paths/revisions.yaml:1294-1301,1352-1360` (`deleteNode` : report sur la parente, `at_least_one_task` + `params.risks`) ; `common.yaml:797-805` ; `node_deleted_provision_moved.json`, `node_delete_last_provision_task_refused.json` (US-0702/L2). |
| H-06 | réglé | `schemas/risks.yaml:523-537,616-623`, `paths/risks.yaml:610-615`, `reference.yaml:858-862` : « l'assiette du projet ». |
| H-07 | réglé | `schemas/risks.yaml:14-37` (`Risk.required` : `description`, `mitigation_notes`, `provision_node_id`, `matrix_cell`, `last_review_on`). |
| H-08 | réglé | `paths/risks.yaml:540-557` (409 de `declareRiskOccurrence`, cinq conditions dans l'ordre des commandes, exemple `risk_occurrence_not_identified`). |
| H-09 | partiellement réglé | `paths/risks.yaml:20` (`states` décrit) ; `:224-230,292-298,394-399` (les trois 409 nomment `project_not_terminal` et `no_background_task_running`). Reste `may_create_revision`, absente des quatre 409 → H-04 de cette revue. |
| H-10 | réglé | `portfolio.yaml:277-283,286-290,309-316` ; `paths/portfolio.yaml:234-236` : « en cours et terminés », `identified_total` décrit comme `ProvisionTotals.identified`. |
| M-01 (aussi) | réglé | `schemas/risks.yaml:680-690` (`RiskCoverageTotals.reserve`, règle du cumul), `:665-667` (`ProvisionTotals.reserve` y renvoie), `revisions.yaml:1616-1618` (`EstimateLineFacet.budgeted_amount`), `paths/risks.yaml:583-588`, `portfolio.yaml:312-314`. |
| M-04 (aussi) | réglé | `paths/revisions.yaml:148-153` (`abandonRevision` : risque créé disparu, réexamen défait, survenu redevenu identifié sans coût à la survenance) ; `schemas/risks.yaml:3-10` (`RiskState`), `:401-403` (`RiskOccurrence`), `paths/risks.yaml:505-507`. Sans exemple, assumé (`DECISIONS.md:9419-9420`). |
| M-05 (aussi) | partiellement réglé | La règle est écrite (`paths/risks.yaml:488-499`, `schemas/risks.yaml:477-493`) et 542 est en `manual` ; mais `nodes_risk_occurred.json` garde l'enveloppe 541 « Risque survenu — … » sous la porteuse → H-03 de cette revue. |
| J-21 (aussi) | non réglé | `risk_matrix_no_basis.json` toujours sans référence dans `paths/risks.yaml:623-631` → H-08 de cette revue. |

Doutes de l'annexe H du 2026-10-28 : « `RiskMatrix.totals` et `points` sur les risques retenus » — réglé par US-0700/L1 (`cells` compte les identifiés, `points` les trois états, `totals` les trois états ; `risk_matrix_no_basis` régénérée, une case à 1) ; « la survenance ajoute-t-elle un réexamen ? » — oui par la décision 2042, non dit par le contrat → H-06 ; « filtre sur `last_review_on` » → H-01 ; « couverture sans référence » — toujours ouvert (Doutes) ; « `RiskOccurrence` : réestimé du devis propre » — réglé (« le montant que ses grandeurs et ses dates donnent »).

## Annexe I — Coûts réels et échanges par fichier

Périmètre : `docs/api/paths/costs.yaml` (191 l., 3 opérations) et `docs/api/paths/exchanges.yaml`
(545 l., 10 opérations) en entier ; `docs/api/components/schemas/costs.yaml` (167 l.) et
`schemas/exchanges.yaml` (739 l.) en entier ; dans `common.yaml`, `ErrorCode` (394–690),
`FieldProblem`, `ProblemParams` (730–829), `ProblemImportedTask` (860–868),
`ProblemMissingColumn`, `PaginationMeta`, `BackgroundTaskRef` (931–991) ; dans `parameters.yaml`,
`Limit`, `Offset`, `SortOrder`, `SubprojectFilter`, `ProjectId`, `ImportId`, `CostLineId`,
`ChunkedUploadId`, `ChunkedUploadPartNumber` ; `responses.yaml` ; `reference.yaml` (`ActualCost*`,
969–1087) ; `projects.yaml` (`CommandCondition` 140–416, `ProjectCommand` 419–500) ;
`revisions.yaml` (`RevisionCommand`, `StructureCommand`, `NodeColumn`, `external_id`,
`mergeCostStructure` 850–875) ; `system.yaml` (`getBackgroundTaskResult` 246–299) ;
`access.yaml` et `audit.yaml` (`cost_line_exclude`). **51 fixtures ouvertes**, toutes celles que les
deux fichiers de chemins référencent (13 + 38) ; les 28 lignes d'`actual_costs.json` et
d'`actual_costs_after_exclusion.json` resommées (`python3 -I`) : les trois totaux et l'union des
colonnes conservées sont exacts. Spécification 1.0.1 : §3.1.2 WF-INTF-0150 (367), §3.1.3
WF-INTF-0010 à 0030, §3.1.4 (417–555), §3.1.5 WF-INTF-0160 à 0180, WF-CYC-0100 (1047),
WF-REF-0190 (1752), WF-PLA-0020/0070/0130/0150/0170 (2244–2352), WF-PLA-0120 (2446), §3.4.5.5
(2597–2697), §3.4.5.7 (2807–2875), WF-IHM-0060 (3246), WF-IHM-0130 (3330), WF-ARC-0040 (3620),
§4.3.4 (3737–3846, WF-ARC-0090/0100), WF-DAT-0020/0110/0120 (4008–4095), §4.6.2 (4283–4322),
annexes A à D (4756–4953). `DECISIONS.md` : 302, 684, 774, 887, 2202–2330, 8009–8130, 8092–8135,
8337–8400, 9163–9238, 9245–9253, 9649–9700, 9777–9830, 9976–9995. Revue du 2026-10-28 : annexe I
(2693–2877), K-05/K-06/K-07 (3169–3197), L-19 (3460–3465), tableau général (303–313, 394–402).

### Synthèse

La famille a été reprise de bout en bout depuis le 2026-10-28 : les vingt constats de l'annexe I et
leurs doublons K-05, K-06, K-07 et L-19 sont réglés ou presque (22 réglés, 2 partiels), par
US-0701/L7, US-0702/L1-L2, US-0703/L7 et US-0630/US-0620. Le journal compte quatre nombres, les
rejets d'une ligne de coût ont leurs codes et leurs exemples, le compte rendu MS Project porte la
date de début de planning et la récapitulative manuelle, les provisions ignorées ou conservées se
signalent, la lecture d'un import rend ce que l'ouverture a reçu, la date de terminaison par import
est la date de la revue que porte le fichier — ce que la 1.0.1 de WF-PLA-0130 confirme —, le format
se contrôle à l'ouverture, l'export est stocké vingt-quatre heures ou jusqu'au premier
téléchargement complet, `setActualCostTrackedScope` a son 409 et son exception écrite au
`lock_version`. Les fixtures racontent l'univers témoin sans contradiction : journal et liste des
imports concordent (identifiants, instants, périodes, comptes), les totaux somment, les lignées
nommées sont celles du cœur.

Ce qui reste tient à une même règle, celle d'US-0702 : chaque refus a un statut, un code, sa
condition et un exemple. Cinq refus de la famille des imports ne l'ont pas encore — l'application
d'un import expiré ou déjà appliqué, et l'état d'un import refusé à l'application dont le fichier
est supprimé ; l'abandon d'un import appliqué ou en cours d'application, laissé ouvert dans le
contrat lui-même ; le « fichier déjà consommé » d'`openImport`, qu'une autre phrase dit 404 ; les
conditions `no_background_task_running` et `may_create_revision` que les commandes `import_*`
annoncent et qu'`openImport` ne déclare pas ; la ligne nouvelle sous une tâche terminée, que
WF-INTF-0100 et WF-INTF-0120 rejettent au compte rendu sans qu'aucun motif d'`ImportRejection` ne
la porte. Chacun demande une valeur d'énumération ou un statut qu'il vaut mieux fixer avant le gel.

**10 constats : 0 bloquant, 5 majeurs, 5 mineurs. Suivi : 22 réglés, 2 partiellement réglés,
0 non réglé, 0 sans objet.**

### Constats

#### I-01 — L'application refusée : ni condition pour un compte rendu expiré ou déjà appliqué, ni état pour l'import refusé dont le fichier est supprimé
- **gravité** : majeur
- **emplacement** : `docs/api/paths/exchanges.yaml:459-479` (`applyImport`, 409) ;
  `docs/api/components/schemas/exchanges.yaml:199-209` (`Import.status`) ;
  `docs/api/components/schemas/projects.yaml:368-416` (`CommandCondition`, seule condition d'import :
  `import_file_accepted`, l. 411)
- **spécification** : `WF-ARC-0100-A` — « Un compte rendu non confirmé expire sans effet au terme de
  vingt-quatre heures, et le fichier est supprimé dès que l'import est appliqué, refusé à
  l'application, abandonné ou expiré » ; Vérif : « Un compte rendu expiré ne peut plus être appliqué »
  et « Un import confirmé par un utilisateur dont la permission est retirée avant l'exécution n'est
  pas appliqué, le refus nomme la condition manquante et son fichier n'est plus sur le stockage
  objet » ; README « Conventions » : le refus d'un état est un 409 `STATE_FORBIDS_OPERATION`,
  `params.missing_condition` nommant la condition qui manque.
- **le contrat dit** : le 409 d'`applyImport` : « Compte rendu expiré, déjà appliqué, ou condition
  de droits ou d'état qui a cessé d'être vraie depuis l'analyse (WF-ARC-0100). […] Un compte rendu
  expiré ou déjà appliqué l'emporte — il n'y a plus rien à appliquer —, puis `import_file_accepted`,
  puis les conditions de droits et d'état revérifiées. Refusé, le fichier est supprimé » — aucune
  condition n'est nommée pour « expiré » ni pour « déjà appliqué », et `CommandCondition` n'en porte
  aucune (`import_file_accepted` seule). `Import.status` : « `analysed`, son compte rendu attend la
  décision de l'utilisateur jusqu'à `expires_at` — une application refusée par 409 le laisse ainsi,
  seul l'abandon restant offert » : un import `analysed`, `expires_at` à venir, dont le fichier est
  supprimé, sans rien qui le dise au lecteur (`Import` n'a pas d'`available_commands`).
- **la fixture dit** : `fixtures/api/import_apply_rejected.json` ne montre que
  `import_file_accepted` ; aucun exemple d'un 409 pour expiré, appliqué, ou état cessé.
- **décision** : `DECISIONS.md:9240-9243` (US-0701/L7) « Restent au gel : d'I-20, […] le 409 d'une
  application refusée pour l'état » ; `DECISIONS.md:9677-9680` (US-0702/L1) « chaque valeur de
  `CommandCondition` dite par sa description et nommée par une opération » — tient, mais n'a pas
  été appliquée à ce 409. Aucune décision sur la condition d'un compte rendu expiré ou appliqué.
- **proposition** : à trancher entre deux formes. (a) Une condition nouvelle `import_applicable`
  (`CommandCondition`) : « manque à l'application d'un import qui n'est plus `analysed` — appliqué,
  en cours d'application, abandonné, expiré, échoué — ou dont le fichier a été supprimé par un refus
  à l'application » ; `applyImport` la nomme en premier dans son 409, puis `import_file_accepted`,
  puis les conditions revérifiées ; exemple `import_apply_expired`. (b) Le 404 pour un import qui
  n'est plus applicable, comme le résultat d'une tâche supprimé (`getBackgroundTaskResult`). Dans
  les deux cas, dire l'état d'un import refusé par 409 à l'application : soit une valeur
  `refused` de `Import.status` (« refusé à l'application, son fichier supprimé ; seul l'abandon
  reste offert », WF-ARC-0100), soit `expires_at` passé à `null` et la phrase « seul l'abandon
  restant offert » remplacée par ce que le lecteur peut voir.

#### I-02 — L'abandon d'un import appliqué ou en cours d'application est laissé sans forme par le contrat lui-même
- **gravité** : majeur
- **emplacement** : `docs/api/paths/exchanges.yaml:402-422` (`abandonImport` : 204, 401, 403, 404,
  500, 503), description l. 409-411
- **spécification** : `WF-ARC-0100-A` — « L'application, demandée depuis ce compte rendu, écrit en
  une seule transaction » ; `WF-INTF-0080-A` — « Un import abandonné ou interrompu laisse le projet
  inchangé » ; README « Conventions » (règle unique des refus d'état).
- **le contrat dit** : « Le contrat ne dit rien de l'abandon d'un import appliqué ou en cours
  d'application : la spécification n'en dit rien, et la forme de ce refus est celle des refus
  d'US-0702. » Une opération qui déclare ne rien dire d'un cas que le front rencontrera (le bouton
  « Abandonner » sur un compte rendu `applying` ou `applied`) ; US-0702/L1 à L3 sont livrés et ne
  l'ont pas réglé.
- **la fixture dit** : aucun exemple (`abandonImport` n'a pas de corps de réponse).
- **décision** : `DECISIONS.md:9240-9243` (US-0701/L7) « Pour un import appliqué ou en cours
  d'application, la spécification ne dit rien : le refus, qui demanderait une condition nouvelle de
  `CommandCondition`, reste à la forme des refus d'US-0702 » — tient, mais le renvoi n'a pas été
  honoré par US-0702.
- **proposition** : la même condition qu'I-01 si (a) est retenue, ou une condition propre
  `import_not_applied` : « manque à l'abandon d'un import appliqué ou en cours d'application
  (`applying`, `applied`) : ce qu'il a écrit ne se défait pas par l'abandon » ; 409
  `STATE_FORBIDS_OPERATION`, exemple `import_abandon_applied` ; retirer la phrase « Le contrat ne dit
  rien… ». Un import `failed` : abandon idempotent (204), comme `abandoned` et `expired`, à dire.

#### I-03 — « Fichier déjà consommé » : un 409 sans code ni condition, qu'une autre phrase dit 404
- **gravité** : majeur
- **emplacement** : `docs/api/paths/exchanges.yaml:298-300` (`openImport`, 409 : « Projet terminal,
  ou fichier déjà consommé (WF-CYC-0100) ») ; `docs/api/components/schemas/exchanges.yaml:130-134`
  (`ImportRequest.upload_id` : « un dépôt inconnu, déjà supprimé ou expiré est refusé par 404 ») ;
  `paths/exchanges.yaml:277-278` (« Un dépôt inconnu ou expiré […] refusés par 404 »)
- **spécification** : `WF-DAT-0120-A` — « Un fichier en cours d'import est supprimé dès que l'import
  est appliqué, refusé, abandonné ou expiré » (un dépôt consommé n'existe plus) ; README
  « Conventions » : un 409 d'état nomme sa condition.
- **le contrat dit** : deux statuts pour le même fait — un dépôt déjà employé par un import est
  « déjà consommé » (409, sans `missing_condition` nommée, et sous la citation de WF-CYC-0100 qui
  ne parle que des projets terminaux) et « déjà supprimé » (404). Un implémenteur du service choisira
  l'un, le front attendra l'autre. La même phrase laisse « Projet terminal » sans nommer
  `project_not_terminal`, que la convention impose.
- **la fixture dit** : `import_estimate_main_in_progress.json` et
  `import_actual_cost_mapping_incomplete.json` seuls ; aucun exemple de projet terminal ni de dépôt
  consommé sur `openImport`.
- **décision** : `DECISIONS.md:887-898` (le dépôt dit son usage), `DECISIONS.md:9233-9237`
  (US-0701/L7, « les champs de l'ouverture et leurs refus décrits ») — aucune ne tranche le statut
  d'un dépôt déjà consommé.
- **proposition** : retirer « ou fichier déjà consommé » du 409 et dire dans `ImportRequest.upload_id`
  et dans le 404 : « un dépôt inconnu, expiré ou déjà employé par un import, donc supprimé
  (WF-DAT-0120), est un 404 » ; écrire le 409 du projet terminal en forme : « `STATE_FORBIDS_OPERATION`,
  `params.missing_condition` à `project_not_terminal` (WF-CYC-0100) », avec un exemple engendré
  (`import_open_terminal`, comme `actual_cost_scope_terminal`).

#### I-04 — `openImport` ne déclare pas les conditions que ses commandes annoncent : `no_background_task_running` et `may_create_revision`
- **gravité** : majeur
- **emplacement** : `docs/api/paths/exchanges.yaml:298-317` (`openImport`, 409 : `project_before_in_progress`,
  `actual_cost_mapping_complete`, projet terminal) ; `docs/api/components/schemas/projects.yaml:146-180`
  (`CommandCondition` : « `no_background_task_running` […] et les imports du projet » ;
  « `may_create_revision` manque, quand le projet n'a pas de révision en cours, à qui n'a pas la
  permission de créer une révision (`revisions.write`) pour une commande qui la créerait : les
  imports d'un planning, d'un devis ou d'un reste à engager (WF-INTF-0090) ») ;
  `projects.yaml:478-485` (`ProjectCommand.import_*` « nomment alors `may_create_revision` à qui ne
  peut pas la créer ») ; `docs/api/paths/revisions.yaml:858-860` (`mergeCostStructure` : « un 409
  et non un 403, comme pour les imports et `declare_risk` »)
- **spécification** : `WF-INTF-0090-A` — « Lorsque le projet n'en comporte pas, l'import en crée
  une, à partir de la dernière révision marquée s'il en existe une, puis s'y applique » ;
  `WF-IHM-0090-A` et README « Conventions » : le refus d'une commande indisponible nomme la
  condition que la commande dit d'avance.
- **le contrat dit** : la commande `import_planning`/`import_estimate`/`import_remaining` du projet
  nomme d'avance `no_background_task_running` (fixture `project_background_task_running`, US-0660/L2)
  et `may_create_revision` ; `mergeCostStructure` renvoie à la forme « des imports » ; mais le 409
  d'`openImport` ne nomme ni l'une ni l'autre, et aucune fixture ne les montre. Un implémenteur du
  service rendrait pour `may_create_revision` un 403 (c'est une permission) là où la fusion rend un
  409, et le client engendré ne saurait pas lequel attendre — le défaut qu'I-06 relevait pour
  `exclude_cost_lines`.
- **la fixture dit** : `fixtures/api/project_background_task_running.json` (les trois imports
  indisponibles, `no_background_task_running`) sans le refus correspondant.
- **décision** : `DECISIONS.md:9657-9675` (US-0702/L1, règle unique) et la description de
  `CommandCondition` — tiennent ; `openImport` ne les reflète pas.
- **proposition** : compléter le 409 d'`openImport` : « Ou, pour un planning, un devis ou un reste à
  engager, `no_background_task_running` pendant un traitement de fond qui écrit dans la révision en
  cours ou la fige, et `may_create_revision` à qui n'a pas `revisions.write` quand l'import créerait
  la révision en cours — un 409 et non un 403, comme pour la fusion (`mergeCostStructure`) —, dans
  l'ordre où `ProjectCommand.import_*` les nomme » ; deux exemples engendrés
  (`import_open_background_running`, `import_open_may_create_revision`). Dire aussi la condition
  revérifiée par `applyImport` (`no_background_task_running` au dépôt de la tâche).

#### I-05 — La ligne nouvelle sous une tâche terminée n'a aucun motif de rejet au compte rendu
- **gravité** : majeur
- **emplacement** : `docs/api/components/schemas/exchanges.yaml:487-542` (`ImportRejection`, motifs
  énumérés : `TASK_WITHOUT_WORKING_HOURS`, `PROVISION_CATEGORY_RESERVED`, `SUBPROJECT_HAS_ACTUAL_COSTS`,
  `DUPLICATE_COST_LINE`, `WBS_ELEMENT_*`, `UNKNOWN_*`, `AMBIGUOUS_TASK_LABEL`) ;
  `docs/api/components/common.yaml:394-690` (`ErrorCode`, aucun code d'une tâche terminée depuis le
  retrait de `TASK_COMPLETED` par US-0702/L1) ; `docs/api/components/schemas/projects.yaml:310-314`
  (`task_not_completed`, condition de `createNode` et `moveNodes`)
- **spécification** : `WF-INTF-0100-A` — « une ligne sans identifiant, ou dont la lignée n'existe pas
  dans la révision en cours, devient une ligne nouvelle, portée par la tâche qu'elle désigne — une
  ligne nouvelle sous une tâche terminée est rejetée au compte rendu (WF-INTF-0080) » ;
  `WF-INTF-0120-A` — « une ligne sans identifiant crée une ligne non anticipée (WF-RAE-0050),
  portée par la tâche qu'elle désigne, sauf si cette tâche est terminée : la ligne est alors rejetée
  au compte rendu (WF-INTF-0080) ».
- **le contrat dit** : `ImportRejection.code` est un `ErrorCode` ; ni le catalogue ni la description
  d'`ImportRejection` ne portent ce rejet, que les deux imports Excel doivent produire. Un
  implémenteur devra inventer un code — modification du contrat après le gel — ou détourner
  `UNKNOWN_TASK`, qui dirait faux.
- **la fixture dit** : aucun exemple (`import_analysed`, `import_remaining_*` ne portent que des tâches
  non terminées ou démarrées).
- **décision** : `DECISIONS.md:9696-9698` (US-0702/L1) retire `TASK_ALREADY_STARTED` et
  `TASK_COMPLETED` « doublons de `STATE_FORBIDS_OPERATION` sous la règle unique — le refus de
  `deleteNode` […] sera une condition » ; `task_not_completed` est née pour `createNode` et
  `moveNodes` (#1184, #1214). Rien pour la ligne importée. La décision tient ; le compte rendu n'a
  pas suivi.
- **proposition** : à trancher. Forme la plus proche de la règle unique : un `ImportRejection` de
  code `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `task_not_completed`, `params.tasks`
  la tâche par sa lignée et son libellé (`ProblemImportedTask`), comme la saisie la refuse
  (`createNode`) ; `ImportRejection` et `CommandCondition.task_not_completed` le disent ; un exemple
  engendré (`import_estimate_completed_task`, une ligne nouvelle sous les « Études de détail »,
  terminées le 10 avril). Autre forme : un code propre (`TASK_COMPLETED_REJECTS_LINE`) — moins
  cohérent avec le catalogue sans code mort.

#### I-06 — `Import.report` et `Import.task` sont facultatifs sans que le contrat dise où ils manquent ; trois comptes rendus n'ont pas de `task`
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/exchanges.yaml:155-218` (`Import.required` sans
  `report` ni `task` ; `status` l. 207-209 : « `failed`, la tâche de son analyse ou de son
  application a échoué (`task.problem`) ») ; `docs/api/paths/exchanges.yaml:215-230` (`listImports`),
  `376-397` (`getImport`)
- **spécification** : `WF-INTF-0080-A` (le compte rendu), `WF-IHM-0080-A` (le suivi d'une tâche de
  fond).
- **le contrat dit** : le même schéma `Import` sert la liste et la lecture ; la liste omet `report`
  et `task` (fixtures `imports.json`, `imports_page.json`), la lecture les rend — rien ne le dit.
  Le client engendré les type facultatifs partout, et l'écran du compte rendu doit distinguer
  « absent » de « nul » pour `report`, ce que la description d'`ImportReport` dit vouloir éviter
  pour ses tableaux.
- **la fixture dit** : `fixtures/api/import_planning_mismatch.json:3-113`,
  `import_planning_provision_moved.json:3-78`, `import_planning_rejected.json:3-81` : réponses de
  `getImport` sans `task`, alors que les quatorze autres l'ont ; un `status: analysed` sans la tâche
  qui l'a produit.
- **décision** : `DECISIONS.md:774-787` (US-0260/L1, `Import.filename`) et `9163` (US-0701/L7) ne
  parlent pas de `report` ni de `task` — aucune.
- **proposition** : décrire sur `Import` : « `report` et `task`, rendus par `openImport` et
  `getImport` ; `report` nul tant que l'analyse court ou a échoué ; omis l'un et l'autre par
  `listImports`, qui ne rend que l'état » ; compléter les trois fixtures écrites à la main d'un
  `task` `import_analysis` abouti. Une forme plus franche — `required` sur `getImport` par un schéma
  dérivé `ImportDetail` — est à trancher avant le gel si on la veut.

#### I-07 — Exemples manquants : les 409 d'`applyImport` hors `import_file_accepted`, `project_in_progress` de l'exclusion, la période inversée et le projet terminal d'`openImport`
- **gravité** : mineur
- **emplacement** : `docs/api/paths/exchanges.yaml:475-479` (`applyImport` 409 : un seul exemple) ;
  `docs/api/paths/costs.yaml:149-153` (`setActualCostTrackedScope` 409 : `project_terminal` seul,
  `project_in_progress` décrit l. 147-148 sans exemple) ; `docs/api/paths/exchanges.yaml:332-341`
  (`openImport` 422 : la période extraite inversée décrite l. 332-333, sans exemple) ;
  `paths/exchanges.yaml:298-317` (`openImport` 409 : projet terminal sans exemple)
- **spécification** : `WF-ARC-0100-A` (Vérif : la permission retirée, le projet passé terminal
  entre-temps), `WF-CRE-0030-A`, `WF-CRE-0050-A`, `WF-CYC-0100-A`.
- **le contrat dit** : quatre refus décrits en toutes lettres et déclarés, sans l'exemple que la
  règle d'US-0702/L1 (« chaque code est porté par un exemple ») et le faux back demandent ;
  `tools/tests/test_contract_catalogue.py` ne tient que le code, pas la condition par opération.
- **la fixture dit** : —
- **décision** : `DECISIONS.md:9240-9243` (US-0701/L7) « Restent au gel : […] le 409 d'une
  application refusée pour l'état » — tient ; c'est ici.
- **proposition** : quatre fixtures engendrées (`wftools.mockdeclared`) :
  `import_apply_main_in_progress` (`project_before_in_progress` à l'application),
  `actual_cost_scope_before_in_progress` (le projet au chiffrage, `project_in_progress`),
  `import_period_inverted` (`/period_to`, `VALUE_OUT_OF_RANGE`, `params.minimum`),
  `import_open_terminal` (`project_not_terminal`, le projet de `project_completed`).

#### I-08 — `FileUpload.expires_at` ne dit pas sa valeur
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/exchanges.yaml:20` (`expires_at: { $ref: Timestamp }`,
  sans description) ; `docs/api/paths/exchanges.yaml:9-20` (`uploadFile`) ; à comparer à
  `ChunkedUpload.expires_at` l. 102-106 (« Vingt-quatre heures après l'ouverture »)
- **spécification** : `WF-DAT-0120-A` — Vérif : « Un fichier déposé et jamais confirmé disparaît au
  terme du délai d'expiration » ; `WF-ARC-0100-A` (vingt-quatre heures pour le compte rendu).
- **le contrat dit** : rien du délai d'un dépôt d'import ni de ce qu'il devient quand l'import
  s'ouvre (le compte rendu a son propre `expires_at`, « vingt-quatre heures après l'analyse ») : un
  dépôt fait à 8 h 40 expire-t-il à 8 h 40 le lendemain même si l'import analysé court jusqu'à
  8 h 41 ?
- **la fixture dit** : `fixtures/api/file_upload.json:8-9` (`uploaded_at` 08:40, `expires_at`
  lendemain 08:40) ; `import_analysed.json` : `expires_at` lendemain 08:41.
- **décision** : `DECISIONS.md:887-898` (le dépôt dit son usage) — rien sur l'expiration ; aucune.
- **proposition** : « `expires_at` : vingt-quatre heures après le dépôt ; au-delà, un dépôt qu'aucun
  import n'a ouvert est supprimé et `openImport` le refuse par 404 (WF-DAT-0120). Un dépôt ouvert
  suit son import : il vit jusqu'à l'application, l'abandon ou l'expiration du compte rendu
  (WF-ARC-0100) ». Même phrase sur `uploadFile`.

#### I-09 — `ExportRequest.depth` : ni défaut, ni portée, ni borne haute
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/exchanges.yaml:730-732` (`depth`, « Niveau retenu
  pour l'image d'arborescence (WF-PLA-0120) ») ; `docs/api/paths/exchanges.yaml:534-543` (422
  `/depth`, `minimum` à 1)
- **spécification** : `WF-PLA-0120-A` — « Aucune pagination ni réduction automatique n'est
  appliquée : l'image a la taille que son contenu exige, et c'est le niveau de profondeur qui règle
  l'encombrement » ; Vérif : « Le contenu ne dépend que du niveau demandé ».
- **le contrat dit** : `depth` nullable, sans dire ce que vaut `null` pour `task_tree_image` (toute
  la profondeur ? le premier niveau ?), ni qu'il est ignoré pour les trois autres natures comme
  `review_date` le dit pour les siennes.
- **la fixture dit** : `export_depth_out_of_range.json` (niveau 0 refusé) ; aucun exemple de requête.
- **décision** : aucune (grep `depth`, « arborescence » dans les entrées d'export).
- **proposition** : « Le niveau de profondeur retenu pour l'image d'arborescence (`task_tree_image`),
  à partir de 1, le premier niveau ; nul, toute la profondeur de la structure (WF-PLA-0120). Sans
  objet pour une autre nature, qui l'ignore. »

#### I-10 — L'exemple numérique de WF-CRE-0020 (code projet à points) n'est cité par aucune fixture, et la forme de l'élément d'OTP ne dit pas les points
- **gravité** : mineur
- **emplacement** : `fixtures/examples.json:335-337` (`WF-CRE-0020-A#05375b7a17e8`) ; aucune fixture
  de `fixtures/api/` ne porte de clé `examples` (grep `WF-[A-Z]*-[0-9]*-A#` : 0 fichier) ;
  `docs/api/components/schemas/exchanges.yaml:516-521` (`ImportRejection`, `WBS_ELEMENT_INVALID` :
  « un élément qui n'a pas la forme d'un code projet suivi facultativement d'une barre oblique et
  d'un code de sous-projet — vide, ou sans rien avant la barre oblique ») ;
  `docs/api/components/common.yaml:662-668` (mêmes mots)
- **spécification** : `WF-CRE-0020-A` — corps : « seule la barre oblique sépare les deux codes, et
  le code projet peut contenir des points » ; Vérif : « Sur le projet de code A.ABC.26001, une
  ligne d'élément A.ABC.26001/10001 est imputée au sous-projet 10001, et une ligne d'élément
  A.ABC.26002/10001 est rejetée comme d'un autre projet » ; `WF-QUA-0020-A` (chaque exemple chiffré
  est un cas de test).
- **le contrat dit** : les exemples de l'univers témoin n'emploient que `PRJ-001`, `PRJ-002/SP-CAB`
  et `/SP-CAB` ; le seul code projet à points de la spécification n'apparaît nulle part, et la
  description des deux codes de rejet ne reprend pas « le code projet peut contenir des points » —
  un implémenteur qui lirait l'OTP par un découpage sur le point se tromperait sans que le contrat
  l'arrête.
- **la fixture dit** : `import_actual_costs_first.json` (`PRJ-002/SP-CAB`, `project_code` `PRJ-002`),
  `import_actual_costs_wbs_invalid.json` (`/SP-CAB`).
- **décision** : `DECISIONS.md:8009-8130` (US-0620, C-373 : l'élément d'OTP du témoin sans préfixe
  `WF.`) — tient ; rien sur l'exemple à points.
- **proposition** : ajouter aux descriptions de `WBS_ELEMENT_INVALID`/`WBS_ELEMENT_OUTSIDE_PROJECT`
  « seule la barre oblique sépare les deux codes, et le code projet peut porter des points
  (A.ABC.26001/10001) » ; une variante contrefactuelle écrite à la main
  (`import_actual_costs_dotted_code`) sur un projet de code `A.ABC.26001`, qui cite
  `WF-CRE-0020-A#05375b7a17e8` dans `examples` — la première fixture à le faire.

### Ce qui est juste

- **Le journal et le compte rendu** : `CostImport` porte `created_count`, `updated_count`,
  `unchanged_count`, `rejected_count`, `period_from`/`period_to` exigés et nullables
  (`schemas/costs.yaml:124-167`) ; `cost_imports.json` concorde avec `imports.json` (cinq imports
  appliqués a06/a07/a08/a09/a14 ↔ c11/c12/c13/c14/c15, instants d'application dans les cinq minutes
  de l'analyse, périodes identiques), avec `import_actual_costs_first` (3 créées, 1 rejetée,
  1er–30 avril) et avec les lignes d'`actual_costs.json` (6 lignes au 6 mai = 6 inchangées de c13 ;
  6 mises à jour le 11 mai = les six `updated_at` 2026-05-11T09:00 ; 22 créées le 3 juin = 21 tâches
  tirées + FA-2026-0521 ; 28 lignes au total) ; `last_import_at` = `cost_imports[0].imported_at`
  partout, nul sur le projet vide.
- **La consultation** : 28 lignes resommées, `tracked` 1 412 970,20 + `excluded` 650,00 = `overall`
  1 413 620,20 ; après exclusion de FA-2026-0412 (1 800,00) : 1 411 170,20 / 2 450,00 / inchangé ;
  `passthrough_columns` = union exacte des clés `passthrough` (« Fournisseur », « Texte de
  commande ») ; FA-2026-0301 ventilée en postes 10 et 20, AV-2026-0388 sans poste, l'avoir négatif ;
  codes inconnus SP-AUT/SP-CAB/SP-REC imputés au seul projet avec leur code, SP-CMD résolu ; tri par
  défaut les pièces les plus récentes d'abord ; `from`/`to`/`in_tracked_scope`/`sort_by` décrits ;
  422 période inversée (`/query/to`, `minimum`) et `UNKNOWN_SUBPROJECT` (`/query/subproject_id`)
  conformes aux conventions. L'absence de `amount_min/_max` et de `search` suit la décision
  `DECISIONS.md:302` (toute liste se filtre sur ce que la spécification nomme pour sa grille ;
  WF-CRE-0040 nomme sous-projet, période, exclusion) sans contredire la 1.0.1.
- **Le périmètre suivi** : `setActualCostTrackedScope` déclare le 409 (`project_not_terminal`,
  `project_in_progress`, dans l'ordre d'`exclude_cost_lines`) avec `actual_cost_scope_terminal` ;
  l'exception au `lock_version` est écrite dans l'opération et le README (US-0702/L2,
  `DECISIONS.md:9784-9797`), et la permission `cost_line_exclude` (`access.yaml:505`) et l'action
  d'audit (`audit.yaml:25`) existent ; `actual_cost_excluded`/`_reinstated` cohérents avec
  `actual_costs_after_exclusion` (même ligne c01, `updated_at` 14:05).
- **Les rejets d'une ligne de coût** : `WBS_ELEMENT_INVALID` (`/SP-CAB`), `WBS_ELEMENT_OUTSIDE_PROJECT`
  (`PRJ-002/SP-CAB`, `project_code`), `DUPLICATE_COST_LINE` (`params.rows`, chacune rejetée,
  `sheet` nul), `requires_confirmation_reasons` (`lines_outside_project`, `unknown_subproject`) ;
  `read_count` = ajoutées + rejetées (4 = 3 + 1) ; les lignes désignées par pièce et poste
  (`label`, `document_item`), `subproject` et `passthrough.Fournisseur` comme champs d'écart
  (`ActualCostColumn`).
- **La correspondance** : 409 `actual_cost_mapping_complete` + `params.columns` (quatre colonnes,
  ordre d'`ActualCostSourceColumn`), 422 `FILE_FORMAT_UNREADABLE` + `missing_columns`
  (`ProblemMissingColumn`, sans `expected_version`), `ImportIgnoredKind.columns` (« Nom Matricule »),
  « le compte rendu analysé est ce qui s'applique » dit par `openImport` et `applyImport` ;
  `format_version` nul pour les quatre comptes rendus de coûts réels, « 1 » pour les Excel (annexe B,
  version 1), nul pour MS Project.
- **Le compte rendu MS Project** (WF-INTF-0040, WF-PLA-0020) : `cost_structure`/`planning_start_on`
  (le 23 février contre le 2 mars), `SUMMARY_TASK_DERIVED` sur `scheduling_mode` avec les dates du
  fichier et l'écart recalculé dans `date_mismatches`, `NON_WORKING_DAY` (le samedi 19 décembre
  2026, lundi 21 nommé — dates vérifiées), `kept` pour la tâche terminée absente, `link` avec
  `predecessor_label`, `ignored` (ressources, calendriers, avancement), `refusals`
  (`ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, `PROJECT_HORIZON_EXCEEDED`) avec `import_apply_rejected`, la
  provision déplacée (`parent`, #789), `unchanged_count` juste dans les cinq comptes rendus
  (4−1=3 ; 1000−1=999 ; 1000−2=998 ; 999 ; 3−2−1 ignorée=0).
- **Les imports Excel** : `AMBIGUOUS_TASK_LABEL` (`params.label`, `params.tasks` par lignée),
  `UNKNOWN_TASK`/`UNKNOWN_RESOURCE_ROLE` avec `params.value`, `SUBPROJECT_HAS_ACTUAL_COSTS` avec
  `sheet` « SP-ESS » et `params.subproject`, `TASK_WITHOUT_WORKING_HOURS` avec `resource_roles` et
  `tasks` (`ProblemImportedTask`), `provision_lines` ignorées et nommées, les onglets fixes
  (WF-INTF-0180) ; `completed_tasks` à la date de la revue du fichier (1er juin 2026), non au jour de
  l'import, la tâche non démarrée démarrée et terminée à cette date — conforme à WF-PLA-0130 **1.0.1**
  et à WF-INTF-0120/0130 ; `ExportRequest.review_date` écrite en « Synthèse ».
- **La lecture d'un import** : `structure_id`, `revision_id`, `period_from`, `period_to` exigés,
  nullables ; nuls pour les coûts réels, la structure principale résolue pour le planning, le
  différentiel 203 pour le devis de l'avenant ; `status` décrit, `expires_at` nul en `analysing`
  (`import_analysing.json`), vingt-quatre heures après l'analyse sinon ; la liste du plus récent au
  plus ancien.
- **Le format à l'ouverture** : `openImport` lit l'en-tête et refuse par 422 avant la file
  (`FILE_FORMAT_UNREADABLE`, `expected_format`, `expected_version` « 1 » = annexe B) ; l'analyse « ne
  refuse plus de format » ; cohérent avec WF-INTF-0070 et le sens de WF-ARC-0100 (décision de
  l'auteur, `DECISIONS.md:9223-9227`).
- **Les exports** : stockés jusqu'au premier téléchargement complet ou vingt-quatre heures
  (`requestExport`, `ExportRequest`, `getBackgroundTaskResult`, `result_url` nul ensuite, 404 d'un
  résultat supprimé, 409 `task_succeeded`) — WF-DAT-0120, WF-ARC-0040 ; `ExportKind` nommé, les
  commandes `export_*` de `RevisionCommand` ; aucun 409 (« il n'a pas de 409 », I-17) ; 404 d'une
  révision d'un autre projet avec `export_revision_not_found` ; `revision_id` exigé ; la date de début
  de planning écrite dans la date de début du projet (WF-INTF-0050, WF-PLA-0020) ; l'identifiant de
  lignée, les notes et le calendrier de tâche nommés.
- **Les dépôts** : 10 Mio ≥ « 10 Mo » du §4.6.2, `UPLOAD_PURPOSE_MISMATCH` des deux côtés, le dépôt par
  morceaux (5–10 Mio, 10 000 morceaux, 413, 422 `/size_bytes` et `/body`, 409 `missing_parts`, 422
  manifeste) avec un exemple par refus ; `backup_taken_at` nul pour un import.
- **Transverse** : 401/503 sur toute opération, 400/422 sur toute opération à corps, 500 partout ;
  les noms du §4.4.1 (`cost_line`, `cost_import`, `estimate_line`, `lineage_id`) ; `INVENTORY.md`
  cite WF-INTF-0040 à 0140, WF-CRE-0010 à 0050, WF-DAT-0110/0120, WF-ARC-0090/0100, WF-REF-0190,
  WF-PLA-0020/0150/0170 sur les bonnes opérations ; WF-INTF-0010/0020/0030/0170 sans surface,
  motivées (l. 283).

### Doutes

- **L'abandon, tâche de fond ou non.** La figure 19 du §4.3.4 fait de l'abandon une tâche mise en
  file (« inscrit la tâche, met en file la suppression ») ; `abandonImport` rend 204 sans
  `BackgroundTaskRef`. WF-ARC-0090 ne compte pas la suppression d'un fichier parmi les traitements
  longs ; le diagramme est illustratif. Rien à changer, sauf si l'auteur veut que l'abandon se suive.
- **`ScopeExclusion.reason`** : sans borne de longueur ni règle du blanc (`pattern: '\S'` vaut pour
  « un libellé, un nom ou un code ») ; un motif fait seulement de blancs est-il conservé tel quel
  (« tel que l'utilisateur l'a saisi ») ou ramené à `null` ? La spécification ne le dit pas.
- **Le journal et le compte rendu ne se lient pas** : `CostImport.cost_import_id` (c15) et
  `Import.import_id` (a14) sont deux identifiants, sans champ de l'un vers l'autre ; l'écran du
  journal ne peut pas ouvrir le compte rendu de l'import qu'il liste. WF-CRE-0050 ne le demande pas.
- **`requires_confirmation_reasons: unknown_subproject`** reste global : WF-CRE-0020 dit la ligne
  « signalée », et l'écart `added` d'une ligne de coût ne porte pas le code inconnu ; la Vérif renvoie
  à la consultation « avec son code ». Même doute qu'au 2026-10-28.
- **`uploadFile` sans 403** : tout compte authentifié peut déposer 10 Mio ; la permission n'est jugée
  qu'à `openImport`. La spécification ne dit rien du dépôt lui-même.
- **`expected_version` d'un planning MS Project** : `openImport` dit « `params.expected_version` sa
  version » pour tout `ExchangeKind` sauf les coûts réels ; un fichier XML MS Project n'a pas de
  version au sens de l'annexe B (WF-INTF-0040 : « versions 2010 et suivantes »). Quelle valeur ?
  Probablement à dire « sans `expected_version` » comme pour `actual_costs`.
- **Les tâches nommées par `ReportRefusal.params`** (`task`, `work_package_task`, `order_item_tasks`)
  ont la forme `{node_id, label}` dans toutes les fixtures (`import_planning_rejected`,
  `predecessors_horizon_exceeded`, `task_horizon_exceeded`), cohérente entre elles mais non typée
  dans `ProblemParams`, qui type `tasks` par `ProblemTask` (`project_id` exigé). Transversal (J) ;
  cohérent, donc pas un constat ici.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| I-01 | réglé | `schemas/costs.yaml:124-167` : `unchanged_count`, `rejected_count`, `period_*` exigés nullables ; `ImportReport.unchanged_count` (`schemas/exchanges.yaml:269-280`) ; `cost_imports.json` concorde |
| I-02 | réglé | `common.yaml:662-668` `WBS_ELEMENT_INVALID`/`WBS_ELEMENT_OUTSIDE_PROJECT` ; `ImportRejection` l. 516-521 ; fixtures `import_actual_costs_first`, `import_actual_costs_wbs_invalid` |
| I-03 (aussi K-05) | réglé | `ImportDifference.target` `cost_structure` (l. 588), `ImportDifferenceField.planning_start_on` (l. 653-661) ; `import_planning_mismatch.json:21-30` |
| I-04 (aussi K-05) | réglé | `ImportSignal.code` `enum: [NON_WORKING_DAY, SUMMARY_TASK_DERIVED]` (l. 477-484) ; `import_planning_mismatch.json:99-110` |
| I-05 (aussi K-06) | réglé | `ImportIgnoredKind.provision_lines` (l. 376, 384-387), `kept` étendu (l. 579-582), « vide pour Excel » retiré ; `import_remaining_analysed.json:40-47` |
| I-06 | réglé | `paths/costs.yaml:142-153` : 409 `project_not_terminal`/`project_in_progress`, `actual_cost_scope_terminal` ; `project_in_progress` sans exemple → I-07 de cette revue |
| I-07 (aussi K-07, L-19) | réglé | `paths/exchanges.yaml:493-497`, `ExportRequest` l. 712-716, `system.yaml:249-257` (404 du résultat supprimé, `result_url` nul, 409 `task_succeeded`) |
| I-08 | réglé | `Import.structure_id`, `revision_id`, `period_from`, `period_to` exigés, nullables, décrits (l. 157-198) ; toutes les fixtures les portent |
| I-09 | réglé | `ImportCompletedTask.completed_on` = date de la revue du fichier, jamais nulle d'un import (l. 418-426) ; `ExportRequest.review_date` (l. 733-739) ; WF-PLA-0130 **1.0.1** le dit ; `import_remaining_completed_tasks` |
| I-10 | réglé | `openImport` l. 241-247 : l'ouverture lit l'en-tête et refuse par 422, l'analyse ne refuse plus de format ; `ImportRequest` l. 122-127 |
| I-11 | réglé | `AMBIGUOUS_TASK_LABEL` (`common.yaml:669-672`, `ImportRejection` l. 527-530) ; `params.value` des `UNKNOWN_*` ; `import_analysed.json:19-35`, `import_remaining_ambiguous_label` |
| I-12 | réglé | `format_version` nul dans les quatre comptes rendus de coûts réels ; décrit l. 256-261 |
| I-13 | réglé | `ImportReport.required` (l. 222-233), `ImportDifference.required: [change, target, label]` (l. 566), `ActualCostLine.required` avec `excluded_reason`, `passthrough` (`schemas/costs.yaml:5-17`) |
| I-14 | réglé | `Import.status` décrit (l. 199-209), `expires_at` nullable « nul tant que l'analyse court » (l. 211-215) ; `import_analysing.json:13` `null` |
| I-15 | réglé | `ImportRequest` l. 130-153 (dépôt 404, structure 404, période propre aux coûts réels, fin inversée 422) ; `openImport` l. 277-278, 332-333 ; l'exemple de la période inversée manque → I-07 |
| I-16 | réglé | `ExportKind` (l. 696-707) ; `ExportRequest.structure_id` décrit (l. 725-729) |
| I-17 | réglé | `requestExport` l. 504-506 : « il n'a pas de 409 » ; aucun 409 déclaré (l. 515-545) |
| I-18 | partiellement réglé | Abandon idempotent déclaré pour abandonné/expiré (l. 407-411) ; appliqué/en cours d'application laissé sans forme par le contrat lui-même → I-02 de cette revue |
| I-19 | réglé | `paths/costs.yaml:19-35` : `from`/`to` sur la date de pièce, fin incluse, `in_tracked_scope` décrit |
| I-20 | partiellement réglé | `import_actual_costs_first` (added, `lines_outside_project`), `import_remaining_completed_tasks`, `export_revision_not_found` ; manque le 409 d'application pour droits ou état → I-07 de cette revue |
| K-05 | réglé | Comme I-03 et I-04 ; la forme retenue est celle d'I-03 (écart `cost_structure`), `planning_start_change` écarté (`DECISIONS.md:9189-9199`) |
| K-06 | réglé | Comme I-05 |
| K-07 | réglé | Comme I-07 ; le 409 générique de `getBackgroundTaskResult` est devenu `task_succeeded` (US-0702/L2, A-05) |
| L-19 | réglé | Comme I-07 ; `result_url` « nul une fois le fichier supprimé » (`common.yaml:980-991`) |

## Annexe J — Transversal : composants partagés, conventions, relevé par script, couverture, delta 1.0.1

Périmètre : `docs/api/openapi.yaml` (343 l.), `components/common.yaml` (991 l., intégralement),
`components/parameters.yaml` (909 l.), `components/responses.yaml` (138 l.), `redocly.yaml` (96 l.),
`.redocly.lint-ignore.yaml` (12 l.), `README-fr.md` (94 l., « Conventions » en entier),
`INVENTORY.md` (284 l.), `tools/inventory.py` (319 l.) ; les 13 fichiers `paths/` (9 913 l.) et les
11 `schemas/` (9 022 l.) parcourus par script, lus à la ligne sur chaque point relevé. Un script
(`revue/releve_j.py`, sortie `releve_j.out`, 731 l., tableaux `releve_tables.md`) a chargé le
contrat par PyYAML et les **724 fixtures** (705 dans `fixtures/api/`, 20 dans `volume/`, la 705ᵉ
étant un en-tête) : 168 opérations, 130 chemins, 89 codes d'`ErrorCode`, 58 conditions de
`CommandCondition`, 11 paramètres typés de `ProblemParams`, 236 schémas objet, 255 propriétés
nullables, 723 références d'exemples. Fixtures ouvertes à la main : 31 (`project*`, `task_*`,
`*_stale`, `*_too_long`/`*_refused` de `VALUE_TOO_LONG`, `pilot_health`, `system_status_*`,
`remaining_indicators`, `paste_too_wide`, `current_revision_exists`, `reference_not_correctable`).
Spécification : §1.3 (WF-INTF-0010 à 0170), §3.6, §4.1, §4.4.1, §4.5, §4.6 et les cinq exigences
changées par la 1.0.1 (`git diff a735115c..HEAD -- docs/spec/waterfall-spec.md`), les 23 exigences
non citées une par une. `DECISIONS.md` : « Forme des chemins » (7), « Session et erreurs » (122),
« Listes et grilles » (215), US-0290/EP-15 (7080–7100, 7274–7292), « La marge du reste à engager »
(1628), US-0702/L1 (9649), US-0702/L2 (9777), US-0702/L3 (9869), « Collage et annulation » (10076),
« Organisation des fichiers » (10102), « Vocabulaire » (10117) ; la section EP-16 (7917–10075)
balayée décision par décision pour chaque écriture annoncée au contrat. Front : `frontend/src`
(`openapi-fetch` + `openapi-typescript`, `make generate-client`), appels relevés par méthode et chemin.

### Synthèse

Le transversal est **sain** : la base formelle tient (89 codes tous nommés hors `common.yaml` et tous
portés par une fixture, 58 conditions toutes décrites, 57 nommées par une opération, aucune
référence cassée, aucun statut de fixture différent de sa réponse, aucun `type: number`, aucun
`format` de date hors `common.yaml`, aucun `nullable`, `explode: false` partout, 404 sur les 130
chemins paramétrés, `operationId` uniques et `camelCase`, 18 étiquettes toutes employées, `security:
[]` sur les quatre publiques seules). Quinze des vingt-et-un constats du 2026-10-28 sont réglés —
la règle unique des refus d'état, le 500 partagé, le catalogue sans code mort, les sept codes
morts, `fields` en 422, le 404 de `createSubproject`, les 403 du référentiel, le `/body`… non. Ce
qui domine aujourd'hui : **deux refus que la commande dit d'avance et que l'API refuse par un code
propre** (`CURRENT_REVISION_EXISTS`, `REFERENCE_NOT_CORRECTABLE`), seule contradiction du README
« une seule forme pour chaque refus » qui reste, assumée par une décision d'EP-15 que US-0702/L1 n'a
pas réécrite ; et **`max_length`, promis par `ProjectCode` et `Problem.params`, qu'aucune des cinq
fixtures `VALUE_TOO_LONG` ne porte**. Le reste est de la clarté : 24 opérations déclarent le 412
sans exemple, 9 un 409 sans exemple du code qu'elles nomment, les `problem` des tâches de fond
n'ont pas de `correlation_id`, quatre types partagés restent muets, 110 propriétés nullables ne
disent pas quand elles le sont, le README ne tient pas toutes les conventions que le contrat
applique. Le delta 1.0.1 est porté pour quatre exigences sur cinq (WF-IHM-0110 et WF-RAE-0020 : le
contrat était en avance sur la spécification ; WF-PLA-0130 : porté ; WF-SEC-0020 : sans surface) ;
WF-REV-0080 manque sa phrase sur l'année de référence. Le front appelle 161 des 168 opérations ;
les sept restantes ont une raison. **17 constats : 0 bloquant, 2 majeurs, 15 mineurs. Suivi : 15
réglés, 2 partiels, 4 non réglés, 0 sans objet.**

### Constats

#### J-01 — Deux refus que la commande dit d'avance, refusés par un code propre
- **gravité** : majeur
- **emplacement** : `docs/api/paths/revisions.yaml:88-107` (`createRevision`, 409 : « Une révision en
  cours existe déjà : `CURRENT_REVISION_EXISTS`, sans paramètre ») ; `:306-327`
  (`designateReferenceRevision`, 409 : « `REFERENCE_NOT_CORRECTABLE`, sans paramètre, le code disant
  la condition que la commande nomme `reference_correctable` ») ; `docs/api/components/common.yaml:441-442`
  (les deux codes au catalogue) ; `docs/api/components/schemas/projects.yaml:370,373`
  (`no_current_revision`, `reference_correctable`) ; `fixtures/api/project.json:44-48`
  (`create_revision` → `missing_conditions: [no_current_revision]`) ; `docs/api/README-fr.md:48`.
- **spécification** : WF-IHM-0090 — « Tout refus nomme la condition manquante » ; WF-REV-0010,
  WF-REV-0040 (les deux règles) ; la forme du code n'est pas fixée par la spécification.
- **le contrat dit** : README l. 48, « Le refus d'une commande qu'un état rend indisponible est un
  409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` nommant la condition qui manque, celle
  que l'objet dit d'avance de sa commande » ; `Conflict` (`responses.yaml:53-60`) : « Toute commande
  qu'un état rend indisponible se refuse ainsi, comme l'objet la dit d'avance ». Or `create_revision`
  dit d'avance `no_current_revision` (10 fixtures d'`available_commands`) et l'appel reçoit
  `CURRENT_REVISION_EXISTS` ; `designate_reference` dit d'avance `reference_correctable` (8 fixtures)
  et l'appel reçoit `REFERENCE_NOT_CORRECTABLE`. Relevé : `no_current_revision` est la **seule des 58
  conditions qu'aucune opération ne nomme** ; les deux codes sont les seuls 409 du catalogue à
  doubler une condition qu'une commande liste (`LAST_ADMINISTRATOR`, `LAST_PROJECT_MANAGER`,
  `ACCESS_ROLE_IN_USE`, `REFERENCE_INCOMPLETE`, `UNDO_CONFLICT` ne doublent aucune commande listée ;
  `common.yaml:448-451` le dit pour le dernier administrateur). Le front rend donc deux textes pour
  un même fait — celui de la condition sur le bouton, celui du code au refus — et changer le code
  après le gel est incompatible.
- **décision** : `DECISIONS.md:7087-7097` (EP-15/US-0290) : « Écartée : l'enveloppe commune,
  `STATE_FORBIDS_OPERATION` à `reference_correctable`. Le catalogue porte ce code depuis EP-02, comme
  `CURRENT_REVISION_EXISTS` pour `createRevision` » ; `:7285-7290` (« le code est
  `CURRENT_REVISION_EXISTS`, sans paramètre, au catalogue depuis EP-02 »). Antérieure à US-0702/L1
  (`:9656-9660`, « La règle d'EP-02/L42a […] devient celle de tout le contrat, et le README la dit »),
  qui ne la réécrit pas et ne nomme ni l'un ni l'autre : les deux décisions se contredisent, et le
  README tranche pour la règle unique.
- **proposition** : à trancher. (a) La règle unique : les deux 409 deviennent `STATE_FORBIDS_OPERATION`,
  `missing_condition` à `no_current_revision` / `reference_correctable`, les deux codes sortent
  d'`ErrorCode`, `current_revision_exists.json` et `reference_not_correctable.json` sont réengendrés,
  `DECISIONS.md:7087` et `:7285` réécrits en citant la décision du 2026-10-28. (b) Garder les deux
  codes : le README écrit l'exception (« deux conditions ont un code propre, … ») et la décision
  US-0702/L1 la cite. La forme (a) est celle que le contrat applique partout ailleurs.

#### J-02 — `max_length` promis par deux descriptions, porté par aucune fixture
- **gravité** : majeur
- **emplacement** : `docs/api/components/schemas/projects.yaml:544-558` (`ProjectCode` : « trop long,
  par `VALUE_TOO_LONG`, `fields[].params.max_length` à `50` ») ; `docs/api/components/common.yaml:342-343`
  (`Problem.params` : « `max_length`, dans `fields[].params`, le plus grand nombre de caractères
  qu'admet le code d'un sous-projet trop long (`VALUE_TOO_LONG`, `31`, WF-PRJ-0050) »), `:683-684`
  (`SUBPROJECT_CODE_INVALID` : « Un code trop long est `VALUE_TOO_LONG`, `fields[].params.max_length`
  à `31` ») ; `fixtures/api/project_creation_refused.json` (`/code` par `VALUE_TOO_LONG`, sans
  `params`), `cost_type_creation_refused.json`, `cost_category_update_refused.json`,
  `actual_cost_mapping_labels_refused.json`, `actual_cost_mapping_kept_columns_too_many.json`.
- **spécification** : WF-PRJ-0010 (code de 1 à 50 caractères), WF-PRJ-0050 (code de sous-projet),
  WF-ARC-0110 (« un code machine et ses paramètres »).
- **le contrat dit** : `ProjectCode` promet `max_length` à `50` ; `Problem.params` et le catalogue le
  promettent à `31` pour le code d'un sous-projet ; `VALUE_TOO_LONG` est au catalogue comme « motif
  par champ » sans paramètre nommé (`common.yaml:518-521`).
- **la fixture dit** : `project_creation_refused.json` — « sous un code de cinquante-et-un
  caractères » — rend `{"pointer": "/code", "code": "VALUE_TOO_LONG"}` **sans `params`** : la
  fixture contredit la description de la propriété qu'elle illustre. Relevé : `grep -l
  '"max_length"' fixtures/api/*.json` ne trouve **aucun** fichier ; les cinq fixtures de
  `VALUE_TOO_LONG` n'ont aucun paramètre ; aucune fixture ne montre un code de sous-projet trop
  long (`subproject_code_invalid`, `_reserved`, `_taken` seulement). Le front qui lit `ProjectCode`
  attend `max_length` et le faux back ne le sert jamais ; le service peut l'omettre sans qu'aucun
  test le voie.
- **décision** : `DECISIONS.md:9629-9633` (US-0702/L1, « Le code projet borné ») et
  `:7961` (US-0610, le code borné d'un sous-projet, `max_length` à 31) décident le paramètre ; aucune
  n'a produit la fixture.
- **proposition** : les générateurs (`wftools.mockrefusals`/`mockdeclared`) posent
  `fields[].params.max_length` sur chaque `VALUE_TOO_LONG` (50 pour `ProjectCode`, 31 pour le code de
  sous-projet, la borne du schéma pour les autres champs) ; `Problem.params` et le catalogue disent
  que `max_length` accompagne **tout** `VALUE_TOO_LONG` (la borne `maxLength` du champ), et non le
  seul code de sous-projet ; un exemple `subproject_code_too_long` sur `createSubproject`.

#### J-03 — Vingt-quatre opérations déclarent le 412 sans exemple
- **gravité** : mineur
- **emplacement** : `docs/api/components/responses.yaml:65-72` (`PreconditionFailed`, sans
  `examples`) ; 47 déclarations de `'412'` dans `paths/`, 23 fixtures `*_stale.json` attachées. Sans
  exemple : `updateUser`, `setUserActivation`, `anonymizeUser`, `setUserAccessRoles`,
  `setIdentitySyncSchedule`, `updateAccessRole` (`access.yaml`), `setBackupSchedule`
  (`platform.yaml`), `updateProject`, `updateSubproject`, `setContributors` (`projects.yaml`),
  `updateCostType`, `updateCostCategory` (`reference.yaml`), `markRevision`, `applyRateUpdate`,
  `updateCostStructure` (`revisions.yaml:704`), `updateTaskFacet` (`:1490`), `updateEstimateLine`
  (`:1585`), `setPredecessors` (`:1663`), `setTaskProgress`, `setLineRemaining`, `setNodeTracking`,
  `moveNodes`, `updateRisk`, `reviewRisk`.
- **spécification** : WF-IHM-0110 ; WF-QUA-0020 (les exemples du contrat sont les jeux du faux back).
- **le contrat dit** : README l. 49, « `lock_version` sur les écritures concurrentes, refus par 412
  `STALE_LOCK_VERSION` » ; chaque écriture à compteur déclare bien le 412 (relevé : aucune écriture
  avec `lock_version` dans son corps ou en paramètre sans 412 ; `mergeCostStructure` et
  `declareRiskOccurrence` le portent sous `main_structure_lock_version`/`amendment_lock_version` et
  `risk_lock_version`). Mais la réponse partagée n'a pas d'exemple, et 24 des 47 opérations n'en
  donnent aucun : le faux back ne rejoue le 412 que sur 23 écritures.
- **décision** : `DECISIONS.md:9666-9669` (US-0702/L1) tient « que chaque code est porté par un
  exemple » — par code, non par opération ; aucune décision n'exige un exemple par 412.
- **proposition** : un exemple sur `PreconditionFailed` même (comme `Unauthorized` et `InternalError`
  en portent), qui couvre les 24 ; ou un `*_stale` engendré par opération, à l'auteur de choisir.

#### J-04 — Des 409 déclarés sans exemple, ou nommant un code sans son exemple
- **gravité** : mineur
- **emplacement** : `docs/api/paths/revisions.yaml:703` (`updateCostStructure`), `:1489`
  (`updateTaskFacet`), `:1584` (`updateEstimateLine`), `:1662` (`setPredecessors`) — `'409': Conflict`
  partagé, sans description propre ni exemple ; `:2139-2149` (`applyPaste`, 409 décrit, sans
  exemple) ; `docs/api/paths/projects.yaml:678` (`createSubproject`), `:737` (`updateSubproject`) —
  nomment `STATE_FORBIDS_OPERATION`/`project_not_terminal`, exemples `ALREADY_EXISTS` seuls ;
  `:972` (`setContributors`, nomme `STATE_FORBIDS_OPERATION`, exemple `LAST_PROJECT_MANAGER` seul) ;
  `docs/api/paths/access.yaml:269` (`updateUser`, nomme `ALREADY_EXISTS`, exemple
  `STATE_FORBIDS_OPERATION` seul).
- **spécification** : WF-DAT-0020, WF-CYC-0100, WF-QUA-0020.
- **le contrat dit** : `createNode` (`revisions.yaml:1175`) montre le 409 d'une révision marquée
  (`node_create_marked_refused`) ; les quatre autres saisies de grille déclarent le même 409 par la
  réponse partagée seulement. `Conflict` dit la règle, non l'ordre des conditions de chaque
  opération (« la première que sa commande dit manquer », `applyPaste`), que `createNode`,
  `moveNodes`, `setTaskProgress` disent et exemplifient.
- **décision** : `DECISIONS.md:9887-9890` (US-0702/L3) : seuls quatre exemples nomment
  `project_not_terminal`, « dans l'ordre que chaque opération dit » — la décision explique
  l'absence sur `createSubproject`/`updateSubproject`/`setContributors` ; rien pour les cinq saisies
  de grille ni pour `updateUser`.
- **proposition** : une variante `*_marked_refused` sur les quatre saisies (la référence 101, comme
  `node_create_marked_refused`) et sur `applyPaste` ; `user_email_taken` cité aussi par `updateUser`,
  comme `project_code_taken` l'est par `createProject` et `updateProject`.

#### J-05 — `previewPaste` ne nomme pas `PASTE_TOO_WIDE`
- **gravité** : mineur
- **emplacement** : `docs/api/paths/revisions.yaml:2079-2089` (422 : « Bloc plus large que les
  colonnes de la facette à partir de la colonne visée (`NodeColumn`) : `params.max_columns` dit
  combien il en reste ») ; `docs/api/components/schemas/revisions.yaml:2199-2201` (`PastePreview`,
  qui nomme le code) ; `fixtures/api/paste_too_wide.json` (`code: PASTE_TOO_WIDE`).
- **spécification** : WF-IHM-0050 ; WF-ARC-0110.
- **le contrat dit** : relevé des 89 codes — `PASTE_TOO_WIDE` est le seul code dont la fixture est
  attachée à une opération (`too_wide`, 422 de `previewPaste`) sans que le texte de cette opération
  le nomme ; sept autres codes ne sont nommés que par un schéma (`UNKNOWN_RESOURCE_ROLE`,
  `EMAIL_MISSING`, `WORK_BREAKDOWN_ITEMS_EXCLUSIVE`, `WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED`,
  `WORK_BREAKDOWN_MAIN_STRUCTURE_ONLY`, `SESSION_REQUIRED`, `SESSION_EXPIRED`), mais leur schéma ou
  leur réponse partagée est ce que l'opération référence.
- **décision** : `DECISIONS.md:10082-10088` (« Collage et annulation ») : « Le code et son paramètre
  existaient sans qu'aucune réponse de `previewPaste` ne les déclare » — la décision veut qu'il se
  dise ; la réponse le porte en exemple, pas en mots.
- **proposition** : « … est refusé par 422 `PASTE_TOO_WIDE`, `params.max_columns` … ».

#### J-06 — Les `problem` des tâches de fond échouées sont sans `correlation_id`
- **gravité** : mineur
- **emplacement** : `fixtures/api/task_import_analysis_failed.json` (`problem: {code: INTERNAL_ERROR,
  status: 500}`), et les huit autres `task_*` à `problem` (`task_failed`, `task_interrupted_by_restore`,
  `task_merge_horizon_exceeded`, `task_merge_link_cycle`, `task_merge_link_forbidden`,
  `task_merge_outside_work_package`, `task_restore_backup_newer_version`,
  `task_restore_verification_failed`) ; `docs/api/components/common.yaml:141-143` (`Problem.required:
  [code, status]`), `:376-384` (`correlation_id` : « engendré par la plateforme, jamais vide […] Le
  front l'affiche comme référence d'une erreur inattendue »), `:975-979` (`BackgroundTaskRef.problem`) ;
  `docs/api/components/responses.yaml:115-121` (`InternalError` : « son `correlation_id` la référence
  que le front affiche ») ; `docs/api/components/schemas/audit.yaml:188-194` (`AuditEvent.correlation_id`
  : « que la tâche de fond qu'elle déclenche reprend »).
- **spécification** : WF-OBS-0020 (corrélation des journaux), WF-IHM-0080 (« l'échec nomme ce qui a
  échoué »).
- **le contrat dit** : les 274 fixtures `Problem` de premier niveau portent toutes `correlation_id` ;
  les 9 `Problem` imbriqués dans une tâche, aucun. `task_import_analysis_failed` est une « défaillance
  du service » : l'écran des tâches n'a aucune référence à afficher, alors que l'audit de la tâche en
  a une.
- **décision** : aucune (`grep correlation_id` dans la section EP-16 : rien sur les tâches).
- **proposition** : `BackgroundTaskRef.problem` dit que le `correlation_id` est celui de la requête
  qui a mis la tâche en file (celui de l'audit) ; les générateurs le posent ; ou `Problem.required`
  reçoit `correlation_id` — à trancher, le second rend la promesse vérifiable (WF-ARC-0060).

#### J-07 — `Limit`, `Offset`, `Year`, `PaginationMeta` sans description (J-20 du 2026-10-28)
- **gravité** : mineur
- **emplacement** : `docs/api/components/parameters.yaml:3-11` (`Limit`, `Offset`) ;
  `docs/api/components/common.yaml:87-90` (`Year`), `:916-922` (`PaginationMeta`).
- **spécification** : WF-IHM-0060 (« 10, 25, 50 et 100 — 50 par défaut »).
- **le contrat dit** : les quatre seuls composants partagés muets du contrat ; `Limit.maximum: 500`
  et `PaginationMeta.limit.maximum: 500` ne disent pas la règle des pages ni la raison du 500 (les
  listes de choix lues par la plus grande page, `DECISIONS.md:2802`).
- **décision** : `DECISIONS.md:2802-2803` donne la raison ; elle n'est pas au contrat.
- **proposition** : quatre phrases ; inchangé depuis le 2026-10-28.

#### J-08 — `Problem.params` : `risks` omis, `missing_rates` et `subordinate_node_ids` dits « ouverts »
- **gravité** : mineur
- **emplacement** : `docs/api/components/common.yaml:155-366` (`Problem.params.description`, qui
  énumère chaque paramètre), `:797-805` (`ProblemParams.risks`, typé, décrit) ;
  `fixtures/api/node_delete_last_provision_task_refused.json`.
- **le contrat dit** : la description de `Problem.params` se donne pour l'inventaire des paramètres
  (« ceux que plusieurs refus partagent sont typés par `ProblemParams`, les autres restent ouverts :
  … ») et nomme `risk` (singulier, `PROVISION_LINE_MOVED_BY_RISK`) mais pas `risks`
  (`at_least_one_task`, `deleteNode`), le seul des 11 paramètres typés qu'elle omet ; à l'inverse,
  elle range `missing_rates` (`:163-164`) et `subordinate_node_ids` (`:165-166`) parmi « les autres
  [qui] restent ouverts » alors que `ProblemParams` les type (`:745-758`) : l'inventaire se contredit
  lui-même sur trois des onze paramètres typés. Relevé : les 54
  clés de `params` que les fixtures portent sont toutes décrites, hormis celles des signaux et
  alertes qui ne sont pas des `Problem` (`PilotHealth.signals[].params`, `SystemStatus.alerts[].params`).
- **décision** : `DECISIONS.md:9820-9826` (US-0702/L2, H-05) décide `params.risks`.
- **proposition** : une incise dans `Problem.params`.

#### J-09 — `StructureCreate.kind` : la seule énumération sans `type` (J-19)
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/revisions.yaml:467-469` (`kind: allOf:
  [{ $ref: '#/StructureKind' }], enum: [amendment]`).
- **le contrat dit** : toujours l'unique `enum` posé à côté d'un `allOf` sans `type` ; la valeur
  unique `amendment` (depuis que le devis d'un risque naît avec lui) en fait presque une constante.
- **décision** : aucune.
- **proposition** : `kind: { type: string, enum: [amendment] }` (ou `const: amendment`), que
  `openapi-typescript` et `datamodel-codegen` rendent de la même façon.

#### J-10 — Le pointeur `/body` n'est pas une forme de `FieldProblem.pointer` (J-14)
- **gravité** : mineur
- **emplacement** : `docs/api/components/common.yaml:713-722` (trois formes : corps RFC 6901,
  `/query/<nom>`, `/path/<nom>` ; « un pointeur ne désigne ainsi qu'un seul champ ») ;
  `docs/api/paths/exchanges.yaml:106,137` (`uploadChunk` : « `fields` désignant `/body` »).
- **décision** : `DECISIONS.md:3847` (EP-14/L42h) décide `/body` ; la description générale n'a pas
  suivi, inchangée depuis le 2026-10-28.
- **proposition** : « un corps qui n'est pas un objet — un fichier ou un morceau déposé —, `/body` ».

#### J-11 — `listRiskReviews` sans pages, sans tri, sans justification (J-12, part restante)
- **gravité** : mineur
- **emplacement** : `docs/api/paths/risks.yaml:322-348`.
- **spécification** : WF-IHM-0060 ; §4.6.2 (revues mensuelles sur quinze ans : jusqu'à 180 réexamens
  par risque).
- **le contrat dit** : `listAccessRoles` a reçu sa phrase (« Sans pagination : une installation compte
  quelques dizaines de rôles au plus », `access.yaml:762-764`) ; `listRiskReviews` rend un tableau nu,
  « du plus récent au plus ancien », sans `sort_by`, sans `limit`, sans phrase. `listSubprojects` et
  `listContributors` disent pourquoi elles n'ont pas de pages.
- **décision** : aucune (`grep listRiskReviews` dans `DECISIONS.md` : rien sur la pagination).
- **proposition** : la phrase « Sans pagination : … » avec le volume, ou `Limit`/`Offset`/`meta`.

#### J-12 — `task_not_milestone` : la seule condition sans exemple (J-18, part restante)
- **gravité** : mineur
- **emplacement** : `docs/api/components/schemas/projects.yaml:381` ; `docs/api/paths/revisions.yaml`
  (`setTaskProgress`, 409).
- **le contrat dit** : relevé des 58 conditions — 57 sont portées par une fixture
  (`missing_condition(s)` ou `available_commands`) ; `task_not_milestone` par aucune.
  `is_contributor` et `is_project_manager` ont reçu les leurs (`project_update_not_manager`,
  `project_participant`).
- **décision** : `DECISIONS.md:9627-9628` (US-0702/L1) : « `task_not_milestone` (J-18) reste sans
  exemple : il tient à `setTaskProgress`, hors des fichiers du lot » — l'absence est connue, non
  soldée.
- **proposition** : un 409 de `setTaskProgress` pour un jalon envoyé à `started`.

#### J-13 — `risk_matrix_no_basis.json`, toujours orphelin (J-21)
- **gravité** : mineur
- **emplacement** : `fixtures/api/risk_matrix_no_basis.json` ; `docs/api/paths/risks.yaml`
  (`getProjectRiskMatrix`, un seul exemple).
- **le contrat dit** : relevé des 723 références — c'est la seule fixture de `fixtures/api/` que ni
  une opération ni une réponse partagée ni un en-tête ne référence (`task_result_disposition.json`,
  que le script croyait orpheline, est l'exemple d'un en-tête, `system.yaml:278`).
- **décision** : `DECISIONS.md:7809` et `:9972` la présentent comme un exemple ; aucun fichier du
  contrat ne la cite.
- **proposition** : `no_basis: { $ref: … }` sous `getProjectRiskMatrix`.

#### J-14 — Cent dix propriétés nullables sans règle de nullité dite
- **gravité** : mineur
- **emplacement** : relevé sur les 255 `anyOf: [{…}, { type: 'null' }]` des `schemas/` et de
  `common.yaml` : 110 n'ont ni description ni mot sur la nullité (liste dans `releve_j.out:345-455`).
  Vérifiées à la ligne, sans règle : `docs/api/components/schemas/projects.yaml:654`
  (`NextState.next_state`), `:622` (`StateTransition.from_state`), `:53` (`Project.order_received_on`) ;
  `revisions.yaml:39` (`Revision.marked_at`), `:639,641` (`Node.task`, `Node.estimate_line`) ;
  `portfolio.yaml:60-73` (`PortfolioProjectRow.reference_budget`, `win_probability`, `cost_index`,
  `schedule_index`, `last_marked_at`) ; `indicators.yaml:687` (`IndexHistoryPoint.version_name`) ;
  `risks.yaml:536` (`RiskMatrixLevel.upper`) ; `access.yaml:167,219` (`UserCreate.org_node_id`,
  `UserUpdate.org_node_id`), `:408` (`GridPreferences.sort`).
- **spécification** : WF-ARC-0060 (le contrat fait foi : un implémenteur doit savoir quand rendre
  `null`).
- **le contrat dit** : pour la moitié, la règle est évidente ou dite à côté (`trigger` : « nul avec
  lui », pour `next_state` ; `reason` dit la sienne et `from_state` non) ; pour l'autre, deux
  lectures sont possibles — `marked_at` nul tant que non marquée (sûr), `from_state` nul pour la
  première transition (probable), `RiskMatrixLevel.upper` nul pour le dernier niveau (à confirmer),
  `PortfolioProjectRow.cost_index` nul sans référence ou sans coût réel (à dire).
- **décision** : aucune règle générale.
- **proposition** : une incise par propriété (« nul quand … »), au moins sur les quinze nommées.

#### J-15 — Le README ne tient pas toutes les conventions que le contrat applique, et son plan oublie des fichiers
- **gravité** : mineur
- **emplacement** : `docs/api/README-fr.md:18-30` (« Organisation », 7 lignes), `:34-67`
  (« Conventions »).
- **le contrat dit** (relevé par `grep` sur le README) : absents du tableau « Organisation » —
  `DECISIONS.md` (10 128 l.), `README.md`/`README-fr.md`, `redocly.yaml`, `.redocly.lint-ignore.yaml`
  (que les conventions citent pourtant par leur nom), `tools/inventory.py`,
  `2026-10-28-contrat-avant-gel.md`. Conventions appliquées par le contrat et absentes des
  conventions du README : `confirmed` absent ou faux → 400 `CONFIRMATION_REQUIRED`
  (`common.yaml:403-407`, décidé US-0702/L2–L3) ; `state` et `state_enum` qui « voyagent toujours
  ensemble » (`common.yaml:826-828`) ; les pages `limit`/`offset`/`meta` et la borne 500 ; `sort_by`
  accompagné de `sort_order`, le tri à égalité étant dit ; `/path/<nom>` et « un identifiant mal
  formé est un 404 » (`common.yaml:718-720`, `DECISIONS.md:190`) ; le 404 d'une collection lue sans
  la permission de consultation (`listUsers`, `listBackups`, `listAuditEvents`…, 27 lectures sans
  paramètre de chemin le déclarent) ; `available_commands` ne liste que les commandes permises à
  l'appelant (`DECISIONS.md:148-150`). Aucune convention écrite n'est contredite par une opération,
  hors J-01.
- **décision** : « Organisation des fichiers » (`DECISIONS.md:10102-10116`) et « Vocabulaire »
  (`:10117-10128`) sont conformes aux fichiers réels (13 fichiers de `paths/`, 13 familles ;
  `CostTypeKind: [labor, non_labor, provision]`, `LABOUR_CATEGORY_REQUIRED`).
- **proposition** : six lignes au tableau « Organisation » ; une ligne de convention pour chacun des
  six points, avec son exigence (WF-CYC-0090/WF-ADM-0160, WF-ARC-0110, WF-IHM-0060, WF-ADM-0110,
  WF-IHM-0090).

#### J-16 — `inventory.py` : deux entrées mortes ; WF-EXP-0030 a une surface que personne ne cite
- **gravité** : mineur
- **emplacement** : `docs/api/tools/inventory.py:64-66` (`REASONS["REF"]` : « Pas encore au contrat :
  la correspondance de l'extraction des coûts réels […] y entre par #1304 ») ; `:70-72`
  (`NO_REQUIREMENT["getLiveness"]` : « ne réalise rien ») ; `docs/api/INVENTORY.md:18` (`getLiveness`
  cite WF-ADM-0160), `:281` (EXP : « Aucune n'est une opération d'API ») ;
  `docs/api/components/schemas/platform.yaml:6,22` (`SystemStatus.version`, exigé, sans description).
- **spécification** : WF-EXP-0030 — « Le front, l'API et le worker d'une installation portent
  toujours le même numéro de version, affiché par l'écran d'état du système ».
- **le contrat dit** : WF-REF-0190 est citée par cinq opérations, la raison « REF » ne s'imprime plus
  mais reste dans le code ; `getLiveness` cite WF-ADM-0160 dans ses propres mots, l'entrée qui
  l'exempte ne sert plus. `getSystemStatus` rend `version` sans dire que c'est le numéro commun des
  trois composants ni citer WF-EXP-0030 : l'inventaire la range parmi les 23 sans surface, à tort
  pour cette moitié de l'exigence. Les 22 autres raisons tiennent (lues une par une : WF-ARC-0010/
  0070/0080, WF-CMP-0010, WF-DAT-0050/0140, WF-EXP-0010, WF-IHM-0010/0100/0140, WF-INTF-0010/0020/
  0030/0170, WF-QUA-0010 à 0080) — réserve sur WF-IHM-0140 en « Doutes ». Le compte « 212 » est
  juste : `inventory.py:95` exclut l'exemple WF-EXA-0010 du §1.3.1 ; les 213 identifiants de la
  spécification existent tous, aucune citation ne vise une exigence absente, aucune ne porte le
  suffixe `-A`. Les 15 exigences citées seulement par un paramètre, un corps ou un schéma
  (`releve_j.out:719`) sont comptées dans la couverture, comme l'en-tête d'`INVENTORY.md` le dit.
- **décision** : aucune.
- **proposition** : retirer les deux entrées ; `SystemStatus.version` : « Le numéro de version
  commun au front, à l'API et au worker (WF-EXP-0030) », et `getSystemStatus` le cite.

#### J-17 — WF-REV-0080 (1.0.1) : la comparaison ne dit pas l'effet de l'année de référence
- **gravité** : mineur (la forme ne change pas ; annexe E pour le détail)
- **emplacement** : `docs/api/paths/revisions.yaml:428-470` (`compareRevisions`) ;
  `docs/api/components/schemas/revisions.yaml:716-727` (`NodeChange`).
- **spécification** : WF-REV-0080-A, Vérif 1.0.1 — « Entre deux révisions d'années de référence
  différentes, les montants réestimés diffèrent en outre sur chaque ligne dont le taux a été mis à
  jour ou projeté jusqu'à la nouvelle année de référence (WF-REV-0060) ; les tâches et les montants
  budgétés restent ceux du différentiel. »
- **le contrat dit** : `grep "année de référence"` sur `compareRevisions` et `NodeChange` : rien. Une
  ligne dont seul le taux change sera `modified` par `reestimated_amount`, ce que le schéma permet,
  mais ni l'opération ni `NodeChange` ne disent qu'un changement d'année de référence suffit à la
  marquer, ni que le budgété n'en bouge pas.
- **décision** : `DECISIONS.md:8737` (« Les deux écarts de la comparaison », US-0701/L1, E-02) traite
  des écarts, pas de l'année de référence.
- **proposition** : une phrase dans `compareRevisions` et dans `NodeChange.reestimated_amount`.

### Le delta 1.0.1, exigence par exigence

| Exigence | Ce qui change | Ce que le contrat porte | Verdict, emplacement |
|---|---|---|---|
| WF-IHM-0110 | L'historique annulable est « tenu par le serveur, par révision et par utilisateur », « pendant sa session de travail », « ne survit ni à la fin de la session, ni au marquage, ni à l'abandon » | `undoLastChange` (`revisions.yaml:2170-2185`) le dit mot pour mot depuis US-0701/L2 ; `UNDO_CONFLICT` nomme l'objet ; `undo_history_not_empty`/`redo_history_not_empty` | **Porté** — la spécification a rejoint le contrat (`DECISIONS.md:10094-10100`). Réserve en « Doutes » : « sa session — le jeton `bearer` » |
| WF-PLA-0130 | Une tâche terminée par un import de reste à engager est datée « de la date de la revue que porte le fichier », non du jour de l'application ; la fusion reste au jour de l'application | `openImport` (`exchanges.yaml:360`), `ImportReport`/`ImportApply` (`schemas/exchanges.yaml:328,424`), `ExportRequest.review_date` (`:733-736`) ; aucune mention restante de « jour de l'application » pour l'import | **Porté** (US-0703/L7, `DECISIONS.md:9976`) |
| WF-RAE-0020 | « Écart au budget » devient « marge sur le budget » (budget − projection, positive quand il en reste), par sous-projet aussi ; l'écart à la revue précédente garde son sens | `RemainingIndicators.delta_to_reference` (`indicators.yaml:233-237`, « marge -50 »), `SubprojectBalance.variance` (`:270-275`), `remaining_indicators.json` (`-641535.13`, sommes des sous-projets conformes en signe) | **Porté** — contrat en avance (`DECISIONS.md:1628-1648`, #466). Nom `delta_to_reference` à deux sens : « Doutes » |
| WF-REV-0080 | Vérif : « de même année de référence » ; entre deux années, les réestimés diffèrent sur chaque ligne au taux mis à jour ou projeté | Rien dans `compareRevisions` ni `NodeChange` | **À compléter** — J-17 |
| WF-SEC-0020 | « ou à l'accueil lorsque l'adresse de retour ne désigne pas un écran de Waterfall » ; Vérif : `//`, barre oblique inverse, caractère de contrôle | Aucune surface (`grep "adresse de retour\|return_to\|redirect"` dans `paths/` et `schemas/` : rien) ; la connexion est côté front (`DECISIONS.md:124-135`) | **Sans objet pour le contrat** — propriété du front (US-0703) |

### Les décisions d'EP-16 confrontées au contrat

Section « Le contrat figé (EP-16) » (`DECISIONS.md:7917-10075`), 31 sous-sections, lues pour chaque
élément annoncé au contrat (schéma, propriété, code, condition, fixture, statut) et vérifié par `grep`.

Résultat (balayage délégué, puis vérifié à la ligne sur chaque écart rapporté) : **aucun manque
franc** — chaque schéma, propriété, code, condition, statut ou fixture qu'une décision annonce au
contrat existe (≈ 700 éléments vérifiés, dont les 40 filtres `*_min`/`*_max`/`*_from`/`*_to` de
l'arbre commun et le `'500'` sur 168/168 opérations), et chaque élément annoncé retiré est absent
(`PROJECT_TERMINAL`, `REVISION_MARKED`, `amendment_merge`, `inflated_amount`, `is_reestimated`,
`own_structure_lock_version`, `ignored_count`, `planning_start_change`, `Predecessor.is_conflicting`,
`reference_provision_amount`, `RiskUpdate.probability`, `Installation.currency_code`,
`CurrentRevisionFateAction`, `project_manager_active`, `provision_task_remaining`, le 409 de
`requestExport`, le compteur de `setActualCostTrackedScope`, `const: true`/`required` de `confirmed`
sur `ProjectExit`, `ReferenceDesignation`, `RestoreRequest`). Les trois contradictions internes de la
section (403 → 409 de `timeline_delete_terminal` et des saisies de grille, `UNDO_CONFLICT` « sans
paramètre » puis avec) portent toutes leur note de remplacement et le contrat suit la forme récente.
Deux écarts de mots, pas d'écriture :
- `DECISIONS.md:9894-9895` : « `ProblemParams.missing_condition` est une `CommandCondition` » —
  `ProblemParams` (`common.yaml:730-828`) n'a pas de propriété `missing_condition` ; elle n'est qu'un
  paramètre « ouvert », décrit par `Problem.params` (`common.yaml:159-160`). La condition n'est donc
  **pas** « typée » : le typage que la décision invoque pour garder `project_not_terminal` dans
  l'énumération n'existe pas (la raison tient quand même : la description de `Problem.params` dit
  « une `CommandCondition` »). À réécrire, ou à réaliser (`missing_condition: { $ref:
  schemas/projects.yaml#/CommandCondition }` dans `ProblemParams`, ce qui la rendrait vérifiable).
- `common.yaml:158-166` range `missing_rates` et `subordinate_node_ids` parmi « les autres [qui]
  restent ouverts » alors qu'ils sont typés dans `ProblemParams` (`:745-758`) depuis US-0702/L1
  (`DECISIONS.md:9708,9733`) → J-08.

Décisions nommées par la mission :
- « Une seule forme pour chaque refus » (9649) : réalisée — `PROJECT_TERMINAL`, `REVISION_MARKED`,
  `TASK_ALREADY_STARTED`, `TASK_COMPLETED`, `PROJECT_CODE_REQUIRED`, `at_least_one_estimate_line`,
  `hourly_rates_set` absents du contrat ; `project_update_not_manager`, `next_state_pricing_without_code`,
  `undo_later_change`, `redo_later_change`, `undo_history_empty`, `redo_history_empty`,
  `estimate_line_rate_missing`, `estimate_line_role_required`, `task_progress_summary_refused`,
  `task_summary_date_refused`, `internal_error`, `nodes_fields_unknown` présents et référencés ;
  `rule/operation-declares-500` (`redocly.yaml:77-82`) ; `test_contract_catalogue.py` existe
  (`tools/tests/`). **Non réalisée sur un point** : « devient celle de tout le contrat » laisse
  `CURRENT_REVISION_EXISTS` et `REFERENCE_NOT_CORRECTABLE` (J-01) ; la décision 7087 qu'elle
  contredit n'est pas réécrite.
- « Les refus sans code ni exemple, et le compteur des écritures concurrentes » (9777) : réalisée —
  `abandonRevision`, `deleteRisk`, `deleteSubproject` portent `lock_version` en paramètre et le 412
  (`revision_abandon_stale`, `risk_delete_stale`, `subproject_delete_stale`) ; `ProjectExit.lock_version`,
  `ReferenceDesignation.lock_version` (`project_exit_stale`, `reference_designate_stale`) ;
  `setActualCostTrackedScope` sans compteur, l'exception au README l. 49 ; `LockVersionInvalid`
  (`responses.yaml:74-81`) ; `DUPLICATE_PREDECESSOR`, `UNKNOWN_TIMELINE`, `task_not_started`,
  `task_succeeded`, `params.risks`, `*_inactive_forbidden`, `createSubproject` 404 : tous présents.
- « Un projet clos ne liste aucune commande » (9869) : réalisée — `project_completed.json` :
  `available_commands: []` ; `project_not_terminal` reste dans `CommandCondition` (`projects.yaml:364`)
  et n'est plus listée par aucune commande (relevé : 0 fixture d'`available_commands`, 4 de
  `missing_condition`) ; `confirmed` sans `const`/`required` sur `ProjectExit`, `ReferenceDesignation`,
  `RestoreRequest` (`exitProject`, `designateReferenceRevision`, `startRestore` déclarent le 400) ;
  README l. 48 le dit.
- « Session et erreurs » (122) : conforme — `bearer` JWT, `getMe` porte les permissions, catalogues
  énumérés, 404/403, 412 distinct du 409, `/path/<nom>` (`common.yaml:718-720`), `AlertZone`.
- « Forme des chemins » (7) : conforme — `/activation`, `/reference-revision`, `/tracked-scope` en
  `PUT` ; `mark`/`merge`/`occurrence` en `POST` ; `/api/v1` au seul `servers`.
- « Listes et grilles » (215) : conforme — `sort_by`/`sort_order` sur 14 listes, `listNodes` sans
  pages avec `meta`, `fields` en 422 (`parameters.yaml:92-100`), `row_number`, `is_contributor`.

### Le front

Le client est engendré par `openapi-typescript` depuis le contrat assemblé (`Makefile:365-366`,
`frontend/src/api/generated/schema.d.ts`) et appelé par `openapi-fetch` (`client.GET("/chemin",
…)`) : les appels se relèvent par **méthode et chemin**, non par `operationId`. Relevé sur
`frontend/src` hors tests et hors `generated/` : **161 couples méthode-chemin distincts, tous dans
le contrat, soit 161 des 168 opérations** ; aucun appel vers un chemin hors contrat.

| Opération non appelée | Justification probable |
|---|---|
| `GET /access-roles/{access_role_id}` (`getAccessRole`) | L'écran des rôles lit la liste (`admin/access-roles/page.tsx:99-102`) et modifie par `PATCH`/`DELETE` sur le même chemin ; la fiche se compose depuis la liste |
| `GET /backups/{backup_id}` (`getBackup`) | L'écran lit `GET /backups`, copie par `GET …/content`, conserve par `PATCH` ; la fiche n'a pas d'écran propre |
| `GET /reference/cost-categories/{cost_category_id}/hourly-rates` (`listHourlyRates`) | L'écran des coûts lit la grille entière (`GET /reference/hourly-rates`, `reference/costs/page.tsx:227`) et écrit par `PUT …/hourly-rates/{year}` |
| `POST …/revisions/{revision_id}/undo` (`undoLastChange`) | `components/grid/undo-commands.tsx` ne porte que les raccourcis et le menu (Ctrl+Z, « indisponible et pourquoi ») ; aucun appel dans `src/api/actions` — part écran d'US-0703, hors de cette revue |
| `POST …/revisions/{revision_id}/redo` (`redoLastUndo`) | idem |
| `GET /health/ready` (`getReadiness`) | Sonde d'orchestration, pas une opération du front |
| `GET /metrics` (`getMetrics`) | Prometheus, réseau interne (`system.yaml`) |

### Ce qui est juste

- **Catalogue** : 89 codes, chacun nommé par une opération, un schéma ou une réponse partagée hors
  `common.yaml`, chacun porté par au moins une fixture (J-03, J-17 du 2026-10-28 réglés) ; aucune
  fixture ne porte un code hors catalogue (les « codes » `ACHATS`, `DEB`, `MO`… relevés sont des
  codes de nœuds et de natures, non des `Problem`) ; aucun identifiant `MAJUSCULES_SOULIGNÉ` du
  contrat hors catalogue ; aucune fixture d'erreur dont le `status` diffère de la réponse qui la
  porte ; les 18 fixtures d'erreur attachées à une opération dont le texte ne nomme pas le code de
  premier niveau sont toutes des `VALIDATION_FAILED` dont l'opération nomme les motifs par champ, ou
  le 401 de `getMe` qui renvoie à `Unauthorized` — hormis J-05.
- **Conditions** : 58, toutes décrites (J-11 réglé : `project_in_pricing`, `no_current_revision`,
  `project_code_set` décrites, `at_least_one_estimate_line` et `hourly_rates_set` retirées) ; 57
  portées par une fixture ; aucune condition hors énumération dans les 724 fixtures ;
  `project_not_terminal` n'est plus listée par aucune commande (US-0702/L3) et reste rendue par
  quatre 409.
- **`ProblemParams`** : les 11 paramètres typés sont tous portés par une fixture ; `state`/`state_enum`
  toujours ensemble (2 fixtures) ; les 54 clés de `params` relevées sont décrites par `Problem.params`
  (J-08 excepté) ; `conflicting_object_label` est porté par les quatre seuls `ALREADY_EXISTS` que le
  README nomme (projet, sous-projet, nœud d'organisation, rôle de ressource) et par aucun autre ;
  `hourly_rate_already_entered` est le seul `ALREADY_EXISTS` sans `fields`, comme le README le dit.
- **Conventions mécaniques** : 404 sur les 130 chemins paramétrés (J-09 réglé) ; `explode: false` sur
  tout paramètre de tableau ; `security: []` sur `getLiveness`, `getReadiness`, `getInstallation`,
  `getMetrics` seuls ; aucune opération `deprecated` ; `operationId` uniques et `camelCase` ; 18
  étiquettes déclarées, 18 employées, une par opération ; `summary` et `description` présents et
  distincts sur les 168 ; aucun `type: number` (décimaux tous `Decimal`/`Money`/`Hours`/`Percent`) ;
  aucun `format: date`/`date-time` hors `PlanningDate`/`Timestamp` ; aucune propriété `*_at`, `*_on`,
  `start`, `finish`, `from`, `to` sans type de date ; aucun `nullable: true`, aucun `type: [x,
  'null']` ; aucun `required` nommant une propriété absente ; `pattern: '\S'` sur tout libellé, nom
  ou code d'écriture (`createTimeline.label` compris, J-13 réglé ; `SubprojectWrite.code` par
  `DeclaredSubprojectCode`).
- **Listes** : 15 listes paginées rendent `meta` avec `limit`/`offset` ; `listNodes` et
  `compareRevisions` sans pages par décision ; `getHourlyRateGrid` a `limit`/`offset` et un `meta`
  propre ; `sort_by` toujours avec `sort_order` ; chaque colonne de `sort_by` existe dans le schéma
  rendu, directement ou dans un objet imbriqué décrit (`audit.created_at`, `org_node.label`,
  `Calendar.hours.monday`, `AuditEvent.object.kind`, `Project.audit.updated_at`) ; `search` partout
  `minLength 1`/`maxLength 200` et décrite sans casse ni accents, par la description partagée ou
  par renvoi au README.
- **412** : toute écriture dont le corps ou la requête porte un compteur déclare le 412, et aucun 412
  n'est déclaré sans compteur (`mergeCostStructure` et `declareRiskOccurrence` portent les leurs
  sous d'autres noms) ; les cinq écritures du doute du 2026-10-28 ont leur compteur (US-0702/L2).
- **Fixtures** : 723 références, 0 cassée ; 22 fixtures citées par deux opérations ou plus, toutes à
  bon droit (même objet lu et créé, même refus partagé — `indicators_scope_unknown` sur cinq
  lectures, `nodes_*` sur `listNodes`/`compareRevisions` par #1193) ; aucune dont `summary` répète
  `description` ; `correlation_id` sur les 274 `Problem` de premier niveau.
- **500, 401, 503, 400/422** : règles `redocly` en place (`redocly.yaml:48-96`), `InternalError` avec
  exemple (J-07 réglé) ; `getMetrics` dit son 404 (J-16 réglé).
- **Delta 1.0.1** : quatre exigences sur cinq portées ou sans objet (tableau ci-dessus).
- **Fichiers et vocabulaire** : 13 fichiers de `paths/`, 13 familles déclarées par `inventory.py`,
  130 chemins tous renvoyés par `openapi.yaml` ; `estimate_line`/`cost_line`, `org_node`, `labor`/
  `LABOUR` comme « Vocabulaire » le dit.

### Doutes

- **`delta_to_reference`, un nom, deux sens.** `RemainingIndicators.delta_to_reference` est une marge
  (budget − projection, `-50` sur l'exemple de la spécification) ; `PortfolioProjectRow.delta_to_reference`
  un écart (projection − budget, `50` sur le même exemple, `portfolio.yaml:72-76`). Décidé
  (`DECISIONS.md:1628-1648`), descriptions explicites, conforme à la 1.0.1 — mais un implémenteur
  qui lit le nom se trompe de signe. Renommer `margin_to_reference` ne coûte rien avant le gel et
  n'est plus possible après ; à l'auteur.
- **La « session » de l'historique annulable.** `undoLastChange` borne la pile à « sa session — le
  jeton `bearer` qui porte ses requêtes » (`revisions.yaml:2170-2172`) ; WF-SEC-0020 fait vivre le
  jeton d'accès cinq minutes au plus. Si la pile suit le jeton d'accès, elle ne survit pas cinq
  minutes ; si elle suit la session du fournisseur d'identité (le `sid`), il faut le dire. Annexe E.
- **`additionalProperties: false`** sur deux schémas seulement (`AuditParams`, `audit.yaml:196-198` ;
  `IdentitySyncSkipped`, `platform.yaml:620-622`) sur 236 objets, `ProblemParams: true` étant explicite.
  Un schéma fermé rend incompatible toute propriété que le service ajouterait ; les 234 autres sont
  ouverts par défaut. Cohérent ou non, selon l'intention — à dire dans le README.
- **WF-IHM-0140 et `getComputedValueDependencies`.** L'aide en ligne « vit dans le front » ; mais
  « chaque valeur calculée porte une infobulle qui dit […] de quoi elle dépend » est exactement ce que
  `getComputedValueDependencies` rend (WF-IHM-0030 citée seule). Citer WF-IHM-0140 la ferait sortir
  des 23 ; la raison d'INVENTORY tient pour les trois autres points de l'exigence.
- **Suppressions sans compteur restantes** : `deleteTimeline`, `deleteAccessRole`, `abandonImport`,
  `retainBackup`, `updateMyPreferences`, `deleteMyAvatar` (relevé). US-0702/L2 a tranché « le compteur
  partout » par la négative pour `tracked-scope` et donné le compteur aux cinq écritures du doute ;
  ces six-là n'ont été ni nommées ni écartées. Les objets sont à écrivain unique ou sans
  `lock_version` : cohérent, mais non dit.
- **`listStartableTasks`** sans pages ni filtre (jusqu'à mille tâches), inchangé.
- **La seconde forme de citation des exigences.** 15 exigences ne sont citées que par un paramètre,
  un corps ou un schéma (`WF-ARC-0020`, `WF-ARC-0050`, `WF-ARC-0060`, `WF-CMP-0020`, `WF-DAT-0060`,
  `WF-DAT-0100`, `WF-DEV-0080`, `WF-EXP-0060`, `WF-IND-0040` à `0070`, `WF-INTF-0150`, `WF-OBS-0020`,
  `WF-RAE-0010`) : la couverture les compte, le tableau ne les montre pas. Une exigence de calcul
  (`WF-DEV-0080`, `WF-IND-0040` à `0070`, `WF-RAE-0010`) portée par un schéma seul est juste ; la
  règle « dans ses propres mots » la rend invisible de l'opération.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| J-01 (403 `PROJECT_TERMINAL` / 409) | réglé | `PROJECT_TERMINAL` absent d'`ErrorCode` ; `deleteTimeline`, `createTimeline` 409 (`timeline_delete_terminal` passé en 409) ; `common.yaml:422-424`, `responses.yaml:39-40` ; `DECISIONS.md:9656` |
| J-02 (`REVISION_MARKED`) | réglé | absent du catalogue ; `createNode` (`revisions.yaml:1119,1175`, `node_create_marked_refused`), `generatePlanningSkeleton` (`skeleton_marked_refused`) en 409 |
| J-03 (sept codes morts) | réglé | `NOT_PROJECT_MANAGER` (`project_update_not_manager`), `UNDO_CONFLICT` (`undo_later_change`), `SUMMARY_TASK_DERIVED` (3 fixtures), `RESOURCE_ROLE_REQUIRED` (`estimate_line_role_required`) rendus ; `TASK_ALREADY_STARTED`, `TASK_COMPLETED`, `PROJECT_CODE_REQUIRED` retirés |
| J-04 (récapitulative « sans paramètre ») | réglé | `common.yaml:476-481`, `ProblemParams.subordinate_node_ids` (`:745-751`), `task_summary_date_refused`, `task_progress_summary_refused` |
| J-05 (annulation sans code) | réglé | `revisions.yaml:2203-2208` : `UNDO_CONFLICT` + `conflicting_object_id/label`, `undo_history_not_empty` ; `undo_later_change`, `undo_history_empty`, `redo_*` |
| J-06 (taux manquant, rôle absent) | réglé | `common.yaml:495-508` ; `estimate_line_rate_missing`, `estimate_line_role_required`, `task_failed` ; `missing_rates` typé (`:752-758`) |
| J-07 (aucun 500) | réglé | `InternalError` (`responses.yaml:115-126`), `'500'` sur les 168, `rule/operation-declares-500` (`redocly.yaml:77-82`) |
| J-08 (`include_inactive` 403) | réglé | `listOrgNodes`, `listCalendars`, `listCostTypes` déclarent 403 (`*_inactive_forbidden`) |
| J-09 (`createSubproject` sans 404) | réglé | `projects.yaml` : `'404'` déclaré (relevé : 130/130 chemins paramétrés) |
| J-10 (`fields` en 400) | réglé | `parameters.yaml:92-100` (422 `FIELD_NOT_ACCEPTED`) ; plus aucun `'400'` sur `listNodes`/`compareRevisions` |
| J-11 (`CommandCondition`) | réglé | 58 conditions décrites ; `project_code_set` rendu (`next_state_pricing_without_code`) ; deux conditions retirées |
| J-12 (tables sans pages) | partiellement réglé | `listAccessRoles` : « Sans pagination : … » (`access.yaml:762-764`) ; `listRiskReviews` : rien → **J-11 de cette revue** |
| J-13 (`createTimeline.label`) | réglé | `TimelineCreate.label` `pattern: '\S'` (`schemas/revisions.yaml:1776`, cite J-13) |
| J-14 (`/body`) | non réglé | `common.yaml:713-722` inchangé ; `exchanges.yaml:106,137` → **J-10** |
| J-15 (`listActualCosts` muette) | réglé | `costs.yaml:19-33` : `document_date`, bornes incluses, `in_tracked_scope` décrits |
| J-16 (`getMetrics` 404) | réglé | `system.yaml` : « l'entrée publique ne le route pas et répond 404 » ; 404 décrit ; sans 503, l'exposition ne dépend d'aucun composant |
| J-17 (treize codes sans exemple) | réglé | 89/89 codes avec fixture (`session_required`, `avatar_malformed`, `access_roles_bounds_*`, `*_inactive_forbidden`…) |
| J-18 (trois conditions sans exemple) | partiellement réglé | `is_contributor` (3 fixtures), `is_project_manager` (5) ; `task_not_milestone` : 0 → **J-12** |
| J-19 (`StructureCreate.kind`) | non réglé | `schemas/revisions.yaml:467-469` → **J-09** |
| J-20 (`Limit`, `Offset`, `Year`) | non réglé | `parameters.yaml:3-11`, `common.yaml:87-90`, `:916-922` → **J-07** |
| J-21 (`risk_matrix_no_basis`) | non réglé | toujours orpheline → **J-13** |
| Doute « suppressions sans `lock_version` » | réglé pour cinq | US-0702/L2 (`DECISIONS.md:9783-9796`) ; six écritures restent sans compteur ni décision (« Doutes ») |
| Doute « `Forbidden` et `NOT_PROJECT_MANAGER` » | réglé | `responses.yaml:32-40`, `project_update_not_manager` |
| Doutes « `listStartableTasks` », « `PaginationMeta.limit` 500 » | inchangés | sans décision nouvelle |

### Relevé

Tableaux bruts du script (`revue/releve_j.py` ; sortie complète `releve_j.out`). Les colonnes
« Opérations » comptent les opérations dont le texte complet (résumé, description, paramètres,
réponses) nomme le code ou la condition.

#### Relevé 1 — Catalogue `ErrorCode` : opérations qui nomment le code (texte complet de l'opération, paramètres compris) et fixtures qui le portent

| Code | Opérations (n) | Fixtures (n) | Fixtures |
|---|---|---|---|
| `MALFORMED_REQUEST` | designateReferenceRevision, exitProject, putMyAvatar, startRestore (4) | 1 | avatar_malformed |
| `CONFIRMATION_REQUIRED` | designateReferenceRevision, exitProject, startRestore (3) | 3 | project_exit_unconfirmed, restore_confirmation_mismatch, restore_external_date_mismatch |
| `SESSION_REVOKED` | closeMySessions, setUserAccessRoles, setUserActivation (3) | 1 | session_revoked |
| `ACCOUNT_DEACTIVATED` | getMe (1) | 1 | account_deactivated |
| `ACCOUNT_NOT_ADMITTED` | getMe (1) | 1 | account_not_admitted |
| `PERMISSION_MISSING` | listCalendars, listCostTypes, listOrgNodes, setActualCostMapping, setUserAccessRoles, updateReferenceSettings (6) | 5 | actual_cost_mapping_permission_missing, calendars_inactive_forbidden, cost_types_inactive_forbidden, org_nodes_inactive_forbidden, … (+1) |
| `NOT_CONTRIBUTOR` | setContributors, updateProject (2) | 1 | project_update_not_contributor |
| `NOT_PROJECT_MANAGER` | updateProject (1) | 1 | project_update_not_manager |
| `NOT_FOUND` | getMetrics, requestExport, resolveRowNumber, startRestore (4) | 3 | export_revision_not_found, restore_not_found, row_number_unknown |
| `STATE_FORBIDS_OPERATION` | abandonRevision, anonymizeUser, applyImport, applyPaste, applyRateUpdate, completeChunkedUpload, … (+52) (58) | 76 | actual_cost_scope_terminal, backup_download_refused, backup_retain_refused, backup_start_during_restore_refused, … (+72) |
| `ALREADY_EXISTS` | createCalendar, createCostCategory, createCostType, createOrgNode, createProject, createResourceRole, … (+14) (20) | 15 | calendar_label_taken, cost_category_accounting_code_taken, cost_category_codes_taken, cost_type_code_taken, … (+11) |
| `CURRENT_REVISION_EXISTS` | createRevision (1) | 1 | current_revision_exists |
| `REFERENCE_NOT_CORRECTABLE` | designateReferenceRevision (1) | 1 | reference_not_correctable |
| `UNDO_CONFLICT` | redoLastUndo, undoLastChange (2) | 2 | redo_later_change, undo_later_change |
| `LAST_ADMINISTRATOR` | setUserAccessRoles, updateAccessRole (2) | 3 | access_role_update_refused, identity_sync_report_flagged, user_access_roles_refused |
| `LAST_PROJECT_MANAGER` | setContributors, setUserAccessRoles (2) | 1 | contributors_without_manager_refused |
| `ACCESS_ROLE_IN_USE` | deleteAccessRole (1) | 1 | access_role_delete_refused |
| `REFERENCE_INCOMPLETE` | createProject (1) | 2 | project_reference_incomplete, project_reference_without_provision |
| `STALE_LOCK_VERSION` | abandonRevision, applyPaste, declareRiskOccurrence, deleteNode, deleteRisk, deleteSubproject, … (+17) (23) | 23 | actual_cost_mapping_stale, calendar_activation_stale, calendar_default_stale, calendar_update_stale, … (+19) |
| `FILE_TOO_LARGE` | openChunkedUpload, putMyAvatar, uploadFile (3) | 1 | avatar_too_large |
| `VALIDATION_FAILED` | createCalendar, createCostCategory, createCostType, createNode, createOrgNode, createProject, … (+61) (67) | 114 | access_roles_bounds_inverted, access_roles_date_invalid, access_roles_number_invalid, access_roles_period_inverted, … (+110) |
| `COMPUTED_VALUE` | createNode, updateEstimateLine, updateTaskFacet (3) | 2 | estimate_line_category_mismatch, task_date_computed_refused |
| `SUMMARY_TASK_DERIVED` | setTaskProgress, updateTaskFacet (2) | 3 | import_planning_mismatch, task_progress_summary_refused, task_summary_date_refused |
| `LINK_CYCLE` | mergeCostStructure, moveNodes, setPredecessors (3) | 4 | nodes_move_cycle_refused, predecessors_cycle_refused, structure_merge_report_link_cycle, task_merge_link_cycle |
| `LINK_FORBIDDEN` | mergeCostStructure, moveNodes, setPredecessors (3) | 4 | nodes_indent_forbidden, predecessors_forbidden, structure_merge_report_link_forbidden, task_merge_link_forbidden |
| `RESOURCE_ROLE_REQUIRED` | createNode, updateEstimateLine (2) | 1 | estimate_line_role_required |
| `LABOUR_CATEGORY_REQUIRED` | createResourceRole, setHourlyRate, updateResourceRole (3) | 2 | hourly_rate_non_labour_refused, resource_role_attachments_refused |
| `HOURLY_RATE_MISSING` | createNode, markRevision, updateEstimateLine (3) | 2 | estimate_line_rate_missing, task_failed |
| `PASTE_TARGET_REMOVED` | applyPaste, previewPaste (2) | 1 | paste_plan_amendment_target_removed |
| `FILE_FORMAT_UNREADABLE` | completeChunkedUpload, openImport (2) | 3 | chunked_upload_unreadable, import_actual_costs_column_missing, import_format_unreadable |
| `TASK_WITHOUT_WORKING_HOURS` | createNode, mergeCostStructure, moveNodes, previewPaste, setDefaultCalendar, updateCalendar, … (+2) (8) | 7 | calendar_default_without_hours, calendar_update_without_hours, estimate_line_without_hours, import_estimate_task_without_hours, … (+3) |
| `VALUE_REQUIRED` | createCalendar, createCostCategory, createCostType, createNode, createOrgNode, createProject, … (+21) (27) | 15 | actual_cost_mapping_labels_refused, backup_schedule_weekday_missing, cost_category_creation_refused, cost_category_without_type_refused, … (+11) |
| `VALUE_TOO_LONG` | createCalendar, createCostCategory, createCostType, createOrgNode, createProject, createResourceRole, … (+13) (19) | 5 | actual_cost_mapping_kept_columns_too_many, actual_cost_mapping_labels_refused, cost_category_update_refused, cost_type_creation_refused, … (+1) |
| `VALUE_OUT_OF_RANGE` | compareRevisions, createCalendar, createNode, createResourceRole, createRisk, getHourlyRateGrid, … (+26) (32) | 36 | access_roles_bounds_inverted, access_roles_period_inverted, actual_costs_period_inverted, audit_events_period_inverted, … (+32) |
| `NUMBER_INVALID` | compareRevisions, getHourlyRateGrid, listAccessRoles, listBackups, listNodes, listOrgNodes, … (+2) (8) | 1 | access_roles_number_invalid |
| `DATE_INVALID` | compareRevisions, listAccessRoles, listActualCosts, listAuditEvents, listBackgroundTasks, listBackups, … (+3) (9) | 1 | access_roles_date_invalid |
| `UNKNOWN_COST_CATEGORY` | createResourceRole, createRisk, updateResourceRole (3) | 2 | paste_applied_partial, paste_plan_unknown_category |
| `UNKNOWN_COST_TYPE` | createCostCategory, updateCostCategory (2) | 1 | cost_category_creation_refused |
| `UNKNOWN_CALENDAR` | createResourceRole, updateResourceRole (2) | 1 | resource_role_calendar_unknown |
| `UNKNOWN_ACCESS_ROLE` | createUser, setUserAccessRoles (2) | 2 | user_access_roles_unknown, user_creation_refused |
| `UNKNOWN_ORG_NODE` | createOrgNode, createResourceRole, createUser, updateOrgNode, updateUser (5) | 2 | resource_role_attachments_refused, user_creation_refused |
| `FIELD_READ_ONLY` | updateResourceRole, updateUser (2) | 1 | user_external_update_refused |
| `UNKNOWN_SUBPROJECT` | createRisk, getCostCurve, getEarnedValueCurves, getEstimateIndicators, getIndexHistory, getProjectIndicators, … (+1) (7) | 3 | actual_costs_subproject_unknown, indicators_scope_unknown, risk_provision_refused |
| `UNKNOWN_TASK` | createRisk (1) | 2 | import_analysed, risk_provision_task_refused |
| `INACTIVE_REFERENCE_OBJECT` | createCostCategory, createOrgNode, createResourceRole, createRisk, createUser, updateCostCategory, … (+4) (10) | 6 | org_node_creation_refused, org_node_move_refused, paste_applied_rejudged, resource_role_attachments_refused, … (+2) |
| `ORG_NODE_CYCLE` | updateOrgNode (1) | 1 | org_node_move_cycle_refused |
| `NODE_NOT_SIBLING` | createNode, moveNodes (2) | 2 | node_create_after_not_sibling, nodes_move_after_not_sibling |
| `MILESTONE_REQUIRED` | setNodeTracking (1) | 1 | node_tracking_milestone_refused |
| `UNKNOWN_TIMELINE` | setNodeTracking (1) | 1 | node_tracking_timeline_unknown |
| `DUPLICATE_PREDECESSOR` | setPredecessors (1) | 1 | predecessors_duplicate |
| `UPLOAD_PURPOSE_MISMATCH` | openImport, startRestore, uploadFile (3) | 2 | import_upload_purpose_mismatch, restore_upload_purpose_mismatch |
| `BACKUP_FROM_NEWER_VERSION` | startRestore (1) | 1 | task_restore_backup_newer_version |
| `TASK_INTERRUPTED_BY_RESTORE` | startRestore (1) | 1 | task_interrupted_by_restore |
| `PROVISION_CATEGORY_RESERVED` | createNode, updateEstimateLine (2) | 2 | estimate_line_provision_refused, estimate_line_provision_reserved |
| `PROVISION_CATEGORY_REQUIRED` | createRisk (1) | 1 | risk_provision_refused |
| `PROVISION_LINE_MOVED_BY_RISK` | moveNodes (1) | 1 | nodes_move_provision_refused |
| `COMPLETION_DATE_REQUIRED` | setLineRemaining (1) | 1 | remaining_completion_date_required |
| `UNKNOWN_USER` | setContributors (1) | 1 | contributors_accounts_refused |
| `USER_INACTIVE` | setContributors (1) | 1 | contributors_accounts_refused |
| `UNKNOWN_EXTERNAL_BACKUP_LOCATION` | setBackupSchedule (1) | 1 | backup_schedule_unknown_location |
| `PATH_INVALID` | setBackupSchedule, testExternalBackupLocation (2) | 2 | backup_schedule_path_invalid, external_backup_location_test_path_invalid |
| `BOUNDS_NOT_ORDERED` | updateReferenceSettings (1) | 1 | reference_settings_bounds_refused |
| `THRESHOLD_NOT_BELOW_WATCH` | updateReferenceSettings (1) | 1 | reference_settings_thresholds_refused |
| `THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE` | updateReferenceSettings (1) | 1 | reference_settings_out_of_range |
| `DURATION_UNIT_NOT_POSITIVE` | setDurationUnits (1) | 1 | duration_units_zero |
| `UNKNOWN_WORK_BREAKDOWN_ITEM` | setWorkBreakdown (1) | 1 | work_breakdown_unknown_item |
| `ORDER_ITEM_OUTSIDE_WORK_PACKAGE` | mergeCostStructure, moveNodes, openImport (3) | 5 | import_planning_rejected, nodes_move_outside_work_package, structure_merge_report_refused, task_attach_outside_work_package, … (+1) |
| `DUPLICATE_WORK_BREAKDOWN_ITEM` | setWorkBreakdown (1) | 1 | work_breakdown_duplicate_item |
| `PROJECT_HORIZON_EXCEEDED` | createNode, mergeCostStructure, moveNodes, openImport, setPredecessors, updateCostStructure, … (+1) (7) | 6 | import_planning_rejected, node_create_horizon_exceeded, predecessors_horizon_exceeded, structure_merge_report_horizon_exceeded, … (+2) |
| `FIELD_NOT_ACCEPTED` | createNode, listNodes, updateEstimateLine (3) | 4 | estimate_line_field_not_accepted, node_create_field_not_accepted, nodes_fields_unknown, task_milestone_duration_refused |
| `NON_WORKING_DAY` | createNode, updateCostStructure, updateTaskFacet (3) | 4 | import_planning_non_working_day, node_create_non_working_day, structure_start_non_working_day, task_date_non_working_day |
| `WBS_ELEMENT_INVALID` | getImport (1) | 1 | import_actual_costs_wbs_invalid |
| `WBS_ELEMENT_OUTSIDE_PROJECT` | getImport (1) | 1 | import_actual_costs_first |
| `AMBIGUOUS_TASK_LABEL` | getImport (1) | 1 | import_remaining_ambiguous_label |
| `SUBPROJECT_HAS_ACTUAL_COSTS` | openImport, previewPaste, updateEstimateLine (3) | 3 | estimate_line_subproject_has_actual_costs, import_remaining_subproject_held, paste_plan_subproject_held |
| `SUBPROJECT_CODE_INVALID` | createSubproject, updateSubproject (2) | 2 | subproject_code_invalid, subproject_code_reserved |
| `PROJECT_CODE_INVALID` | createProject (1) | 1 | project_code_invalid |
| `DUPLICATE_COLUMN_LABEL` | setActualCostMapping (1) | 2 | actual_cost_mapping_duplicate, actual_cost_mapping_labels_refused |
| `DUPLICATE_COST_LINE` | getImport (1) | 1 | import_actual_costs_duplicate_line |
| `COMPONENT_UNAVAILABLE` | getInstallation, getLiveness, putMyAvatar, resendInvitation, startRestore (5) | 1 | system_status_backup_failed |
| `SESSION_REQUIRED` | — (0) | 1 | session_required |
| `SESSION_EXPIRED` | — (0) | 1 | session_expired |
| `PASTE_TOO_WIDE` | — (0) | 1 | paste_too_wide |
| `UNKNOWN_RESOURCE_ROLE` | — (0) | 1 | import_analysed |
| `EMAIL_MISSING` | — (0) | 1 | identity_sync_report_flagged |
| `WORK_BREAKDOWN_ITEMS_EXCLUSIVE` | — (0) | 2 | task_attach_exclusive, task_attach_exclusive_attached |
| `WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED` | — (0) | 2 | task_attach_exclusive_attached, task_attach_refused |
| `WORK_BREAKDOWN_MAIN_STRUCTURE_ONLY` | — (0) | 1 | task_attach_main_structure_only |
| `INTERNAL_ERROR` | — (0) | 2 | internal_error, task_import_analysis_failed |

#### Relevé 2 — `CommandCondition` : opérations qui nomment la condition, fixtures qui la portent en `missing_condition(s)`, fixtures qui la listent dans `available_commands`

| Condition | Opérations | `missing_condition(s)` (n) | `available_commands` (n) |
|---|---|---|---|
| `is_contributor` | listProjects, updateProject | 2 | 1 |
| `is_project_manager` | updateProject | 3 | 2 |
| `project_not_terminal` | createRevision, createRisk, createSubproject, createTimeline, declareRiskOccurrence, … (+11) | 4 | 0 |
| `project_in_progress` | exitProject, setActualCostTrackedScope, setTaskProgress | 7 | 7 |
| `project_in_pricing` | exitProject | 2 | 1 |
| `project_code_set` | getProjectNextState | 1 | 0 |
| `reference_revision_designated` | declareRiskOccurrence, getProjectNextState | 7 | 6 |
| `at_least_one_task` | createRisk, deleteNode, redoLastUndo, reviewRisk, undoLastChange | 12 | 8 |
| `revision_draft` | abandonRevision, applyPaste, applyRateUpdate, createCostStructure, createNode, … (+5) | 15 | 7 |
| `revision_marked` | designateReferenceRevision, getRevision | 10 | 10 |
| `reference_correctable` | designateReferenceRevision | 8 | 8 |
| `revision_has_tasks_and_lines` | designateReferenceRevision | 4 | 3 |
| `unmerged_amendment_exists` | mergeCostStructure | 6 | 6 |
| `rate_update_available` | applyRateUpdate | 10 | 9 |
| `task_not_completed` | createNode, moveNodes, setLineRemaining | 11 | 0 |
| `task_not_started` | deleteNode | 1 | 0 |
| `line_not_provision` | setLineRemaining | 10 | 0 |
| `task_is_milestone` | setTaskProgress | 2 | 2 |
| `task_not_milestone` | setTaskProgress | 0 | 0 |
| `task_without_lines` | setTaskProgress | 2 | 2 |
| `completed_milestone` | setTaskProgress | 1 | 0 |
| `no_background_task_running` | abandonRevision, applyPaste, applyRateUpdate, createCostStructure, createNode, … (+17) | 5 | 3 |
| `may_create_revision` | declareRiskOccurrence, mergeCostStructure | 2 | 1 |
| `restored_subproject_exists` | deleteRisk, redoLastUndo, undoLastChange, updateRisk | 1 | 0 |
| `risk_not_cited` | deleteRisk | 9 | 8 |
| `risk_not_occurred` | deleteRisk, reviewRisk, updateRisk | 4 | 3 |
| `risk_identified` | declareRiskOccurrence, getRiskOccurrenceReport, updateRisk | 7 | 5 |
| `active_provision_category` | createRisk, redoLastUndo, reviewRisk, setCostTypeActivation, undoLastChange | 2 | 0 |
| `org_node_parent_active` | setCostCategoryActivation, setOrgNodeActivation | 3 | 2 |
| `org_node_active` | setResourceRoleActivation | 3 | 2 |
| `calendar_not_default` | setCalendarActivation | 4 | 3 |
| `calendar_active` | setDefaultCalendar | 3 | 2 |
| `cost_type_active` | setCostCategoryActivation | 2 | 1 |
| `cost_type_unused` | updateCostType | 5 | 4 |
| `cost_type_unrated` | setHourlyRate, updateCostType | 2 | 2 |
| `cost_type_without_role` | updateCostType | 2 | 2 |
| `cost_category_unused` | updateCostCategory | 6 | 5 |
| `cost_category_unrated` | setHourlyRate, updateCostCategory | 3 | 2 |
| `cost_category_without_role` | updateCostCategory, updateResourceRole | 3 | 2 |
| `last_administrator` | setUserActivation | 5 | 4 |
| `backup_verified` | downloadBackup, startRestore | 5 | 2 |
| `no_backup_running` | startBackup, startRestore | 3 | 1 |
| `no_restore_running` | retainBackup, startBackup, startRestore | 3 | 0 |
| `project_before_in_progress` | applyImport, openImport, updateProject | 14 | 12 |
| `subproject_not_cited` | deleteSubproject | 6 | 5 |
| `subproject_without_actual_costs` | deleteSubproject | 7 | 6 |
| `subproject_without_estimate_lines` | deleteSubproject | 6 | 5 |
| `main_structure_without_tasks` | generatePlanningSkeleton | 9 | 8 |
| `import_file_accepted` | applyImport | 1 | 0 |
| `is_local_account` | createPasswordSetupLink, resendInvitation | 2 | 0 |
| `is_active_account` | createPasswordSetupLink, resendInvitation | 2 | 0 |
| `is_deactivated_account` | anonymizeUser | 1 | 0 |
| `is_not_anonymized` | anonymizeUser, setUserActivation, updateUser | 5 | 2 |
| `actual_cost_mapping_complete` | openImport | 2 | 1 |
| `undo_history_not_empty` | undoLastChange | 1 | 0 |
| `redo_history_not_empty` | redoLastUndo | 1 | 0 |
| `task_succeeded` | getBackgroundTask, getBackgroundTaskResult | 1 | 0 |
| `no_current_revision` | — | 10 | 10 |

#### Relevé 3 — Opérations → statuts déclarés

| Méthode | Chemin | `operationId` | Statuts |
|---|---|---|---|
| GET | `/users` | `listUsers` | 200 401 404 422 500 503 |
| POST | `/users` | `createUser` | 201 400 401 403 409 422 500 503 |
| GET | `/users/{user_id}` | `getUser` | 200 401 404 500 503 |
| PATCH | `/users/{user_id}` | `updateUser` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/users/{user_id}/activation` | `setUserActivation` | 200 400 401 403 404 409 412 422 500 503 |
| POST | `/users/{user_id}/anonymization` | `anonymizeUser` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/users/{user_id}/access-roles` | `setUserAccessRoles` | 200 400 401 403 404 409 412 422 500 503 |
| POST | `/users/{user_id}/password-link` | `createPasswordSetupLink` | 201 401 403 404 409 500 503 |
| POST | `/users/{user_id}/invitation` | `resendInvitation` | 204 401 403 404 409 500 503 |
| GET | `/users/{user_id}/avatar` | `getUserAvatar` | 200 401 404 500 503 |
| POST | `/identity-syncs` | `startIdentitySync` | 202 401 403 500 503 |
| GET | `/identity-syncs/latest` | `getLatestIdentitySync` | 200 401 404 500 503 |
| GET | `/identity-sync-schedule` | `getIdentitySyncSchedule` | 200 401 404 500 503 |
| PUT | `/identity-sync-schedule` | `setIdentitySyncSchedule` | 200 400 401 403 412 422 500 503 |
| GET | `/permissions` | `listPermissions` | 200 401 500 503 |
| GET | `/access-roles` | `listAccessRoles` | 200 401 404 422 500 503 |
| POST | `/access-roles` | `createAccessRole` | 201 400 401 403 422 500 503 |
| GET | `/access-roles/{access_role_id}` | `getAccessRole` | 200 401 404 500 503 |
| PATCH | `/access-roles/{access_role_id}` | `updateAccessRole` | 200 400 401 403 404 409 412 422 500 503 |
| DELETE | `/access-roles/{access_role_id}` | `deleteAccessRole` | 204 401 403 404 409 500 503 |
| GET | `/projects/{project_id}/estimate-indicators` | `getEstimateIndicators` | 200 401 404 422 500 503 |
| GET | `/projects/{project_id}/estimate-indicators/missing-rates` | `getMissingRates` | 200 401 404 422 500 503 |
| GET | `/projects/{project_id}/workload` | `getProjectWorkload` | 200 401 404 409 422 500 503 |
| GET | `/projects/{project_id}/remaining-indicators` | `getRemainingIndicators` | 200 401 404 422 500 503 |
| GET | `/projects/{project_id}/remaining-indicators/startable-tasks` | `listStartableTasks` | 200 401 404 500 503 |
| GET | `/projects/{project_id}/indicators` | `getProjectIndicators` | 200 401 404 409 422 500 503 |
| GET | `/projects/{project_id}/indicators/milestone-tracking` | `getMilestoneTracking` | 200 401 404 500 503 |
| GET | `/projects/{project_id}/indicators/cost-curve` | `getCostCurve` | 200 401 404 409 422 500 503 |
| GET | `/projects/{project_id}/indicators/earned-value-curves` | `getEarnedValueCurves` | 200 401 404 409 422 500 503 |
| GET | `/projects/{project_id}/indicators/index-history` | `getIndexHistory` | 200 401 404 422 500 503 |
| GET | `/audit-events` | `listAuditEvents` | 200 401 404 422 500 503 |
| GET | `/audit-events/facets` | `listAuditFacets` | 200 401 404 500 503 |
| GET | `/projects/{project_id}/actual-costs` | `listActualCosts` | 200 401 404 422 500 503 |
| PUT | `/projects/{project_id}/actual-costs/{cost_line_id}/tracked-scope` | `setActualCostTrackedScope` | 200 400 401 403 404 409 422 500 503 |
| GET | `/projects/{project_id}/cost-imports` | `listCostImports` | 200 401 404 422 500 503 |
| POST | `/file-uploads` | `uploadFile` | 201 400 401 413 422 500 503 |
| POST | `/chunked-uploads` | `openChunkedUpload` | 201 400 401 403 413 422 500 503 |
| PUT | `/chunked-uploads/{chunked_upload_id}/parts/{part_number}` | `uploadChunk` | 200 400 401 403 404 422 500 503 |
| POST | `/chunked-uploads/{chunked_upload_id}/completion` | `completeChunkedUpload` | 201 401 403 404 409 422 500 503 |
| GET | `/projects/{project_id}/imports` | `listImports` | 200 401 404 422 500 503 |
| POST | `/projects/{project_id}/imports` | `openImport` | 202 400 401 403 404 409 422 500 503 |
| GET | `/projects/{project_id}/imports/{import_id}` | `getImport` | 200 401 404 500 503 |
| DELETE | `/projects/{project_id}/imports/{import_id}` | `abandonImport` | 204 401 403 404 500 503 |
| POST | `/projects/{project_id}/imports/{import_id}/apply` | `applyImport` | 202 400 401 403 404 409 422 500 503 |
| POST | `/projects/{project_id}/exports` | `requestExport` | 202 400 401 403 404 422 500 503 |
| GET | `/me` | `getMe` | 200 401 500 503 |
| DELETE | `/me/sessions` | `closeMySessions` | 204 401 500 503 |
| PATCH | `/me/preferences` | `updateMyPreferences` | 200 400 401 422 500 503 |
| PUT | `/me/avatar` | `putMyAvatar` | 204 400 401 413 422 500 503 |
| DELETE | `/me/avatar` | `deleteMyAvatar` | 204 401 500 503 |
| GET | `/backups` | `listBackups` | 200 401 404 422 500 503 |
| POST | `/backups` | `startBackup` | 202 401 403 409 500 503 |
| GET | `/backups/{backup_id}` | `getBackup` | 200 401 404 500 503 |
| PATCH | `/backups/{backup_id}` | `retainBackup` | 200 400 401 403 404 409 422 500 503 |
| GET | `/backups/{backup_id}/content` | `downloadBackup` | 200 401 403 404 409 500 503 |
| GET | `/backup-schedule` | `getBackupSchedule` | 200 401 404 500 503 |
| PUT | `/backup-schedule` | `setBackupSchedule` | 200 400 401 403 412 422 500 503 |
| GET | `/external-backup-locations` | `listExternalBackupLocations` | 200 401 404 500 503 |
| POST | `/external-backup-locations/{location_name}/test` | `testExternalBackupLocation` | 200 400 401 403 404 422 500 503 |
| POST | `/restores` | `startRestore` | 202 400 401 403 404 409 422 500 503 |
| GET | `/portfolio/projects` | `getPortfolioProjects` | 200 401 404 422 500 503 |
| GET | `/portfolio/value` | `getPortfolioValue` | 200 401 404 422 500 503 |
| GET | `/portfolio/workload` | `getPortfolioWorkload` | 200 401 404 422 500 503 |
| GET | `/portfolio/performance` | `getPortfolioPerformance` | 200 401 404 422 500 503 |
| GET | `/portfolio/cost-structure` | `getPortfolioCostStructure` | 200 401 404 422 500 503 |
| GET | `/portfolio/risks` | `getPortfolioRisks` | 200 401 404 422 500 503 |
| GET | `/portfolio/cost-curve` | `getPortfolioCostCurve` | 200 401 404 422 500 503 |
| GET | `/portfolio/pilot-health` | `getPortfolioPilotHealth` | 200 401 404 422 500 503 |
| GET | `/projects` | `listProjects` | 200 401 404 422 500 503 |
| POST | `/projects` | `createProject` | 201 400 401 403 409 422 500 503 |
| GET | `/projects/{project_id}` | `getProject` | 200 401 404 500 503 |
| PATCH | `/projects/{project_id}` | `updateProject` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/state-transitions` | `listProjectStateTransitions` | 200 401 404 500 503 |
| GET | `/projects/{project_id}/next-state` | `getProjectNextState` | 200 401 404 500 503 |
| POST | `/projects/{project_id}/exit` | `exitProject` | 200 202 400 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/work-breakdown` | `getWorkBreakdown` | 200 401 404 422 500 503 |
| PUT | `/projects/{project_id}/work-breakdown` | `setWorkBreakdown` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/subprojects` | `listSubprojects` | 200 401 404 422 500 503 |
| POST | `/projects/{project_id}/subprojects` | `createSubproject` | 201 400 401 403 404 409 422 500 503 |
| PATCH | `/projects/{project_id}/subprojects/{subproject_id}` | `updateSubproject` | 200 400 401 403 404 409 412 422 500 503 |
| DELETE | `/projects/{project_id}/subprojects/{subproject_id}` | `deleteSubproject` | 204 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/contributors` | `listContributors` | 200 401 404 422 500 503 |
| PUT | `/projects/{project_id}/contributors` | `setContributors` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/contributors/suggestions` | `listContributorSuggestions` | 200 401 404 500 503 |
| GET | `/projects/{project_id}/timelines` | `listTimelines` | 200 401 404 500 503 |
| POST | `/projects/{project_id}/timelines` | `createTimeline` | 201 400 401 403 404 409 422 500 503 |
| DELETE | `/projects/{project_id}/timelines/{timeline_id}` | `deleteTimeline` | 204 401 403 404 409 500 503 |
| GET | `/reference/readiness` | `getReferenceReadiness` | 200 401 500 503 |
| GET | `/reference/settings` | `getReferenceSettings` | 200 401 500 503 |
| PATCH | `/reference/settings` | `updateReferenceSettings` | 200 400 401 403 412 422 500 503 |
| GET | `/reference/org-nodes` | `listOrgNodes` | 200 401 403 404 422 500 503 |
| POST | `/reference/org-nodes` | `createOrgNode` | 201 400 401 403 409 422 500 503 |
| PATCH | `/reference/org-nodes/{org_node_id}` | `updateOrgNode` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/reference/org-nodes/{org_node_id}/activation` | `setOrgNodeActivation` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/reference/resource-roles` | `listResourceRoles` | 200 401 403 404 422 500 503 |
| POST | `/reference/resource-roles` | `createResourceRole` | 201 400 401 403 409 422 500 503 |
| PATCH | `/reference/resource-roles/{resource_role_id}` | `updateResourceRole` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/reference/resource-roles/{resource_role_id}/activation` | `setResourceRoleActivation` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/reference/duration-units` | `getDurationUnits` | 200 401 500 503 |
| PUT | `/reference/duration-units` | `setDurationUnits` | 200 400 401 403 412 422 500 503 |
| GET | `/reference/calendars` | `listCalendars` | 200 401 403 404 422 500 503 |
| POST | `/reference/calendars` | `createCalendar` | 201 400 401 403 409 422 500 503 |
| PATCH | `/reference/calendars/{calendar_id}` | `updateCalendar` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/reference/calendars/{calendar_id}/default` | `setDefaultCalendar` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/reference/calendars/{calendar_id}/activation` | `setCalendarActivation` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/reference/cost-types` | `listCostTypes` | 200 401 403 404 422 500 503 |
| POST | `/reference/cost-types` | `createCostType` | 201 400 401 403 409 422 500 503 |
| PATCH | `/reference/cost-types/{cost_type_id}` | `updateCostType` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/reference/cost-types/{cost_type_id}/activation` | `setCostTypeActivation` | 200 400 401 403 404 412 422 500 503 |
| GET | `/reference/cost-categories` | `listCostCategories` | 200 401 403 404 422 500 503 |
| POST | `/reference/cost-categories` | `createCostCategory` | 201 400 401 403 409 422 500 503 |
| PATCH | `/reference/cost-categories/{cost_category_id}` | `updateCostCategory` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/reference/cost-categories/{cost_category_id}/activation` | `setCostCategoryActivation` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/reference/hourly-rates` | `getHourlyRateGrid` | 200 401 403 404 422 500 503 |
| GET | `/reference/cost-categories/{cost_category_id}/hourly-rates` | `listHourlyRates` | 200 401 404 500 503 |
| PUT | `/reference/cost-categories/{cost_category_id}/hourly-rates/{year}` | `setHourlyRate` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/reference/actual-cost-mapping` | `getActualCostMapping` | 200 401 404 500 503 |
| PUT | `/reference/actual-cost-mapping` | `setActualCostMapping` | 200 400 401 403 412 422 500 503 |
| GET | `/projects/{project_id}/revisions` | `listRevisions` | 200 401 404 422 500 503 |
| POST | `/projects/{project_id}/revisions` | `createRevision` | 201 400 401 403 404 409 422 500 503 |
| GET | `/projects/{project_id}/revisions/{revision_id}` | `getRevision` | 200 401 404 500 503 |
| DELETE | `/projects/{project_id}/revisions/{revision_id}` | `abandonRevision` | 204 401 403 404 409 412 422 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/mark` | `markRevision` | 202 400 401 403 404 409 412 422 500 503 |
| PUT | `/projects/{project_id}/reference-revision` | `designateReferenceRevision` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/revisions/{revision_id}/rate-update` | `getRateUpdateProposal` | 200 401 404 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/rate-update` | `applyRateUpdate` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/revisions/comparison` | `compareRevisions` | 200 401 404 422 500 503 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures` | `listCostStructures` | 200 401 404 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures` | `createCostStructure` | 201 400 401 403 404 409 422 500 503 |
| PATCH | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}` | `updateCostStructure` | 200 400 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge` | `getStructureMergeReport` | 200 401 404 409 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge` | `mergeCostStructure` | 202 400 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes` | `listNodes` | 200 401 404 422 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes` | `createNode` | 201 400 401 403 404 409 422 500 503 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/rows/{row_number}` | `resolveRowNumber` | 200 401 404 422 500 503 |
| DELETE | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}` | `deleteNode` | 200 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/dependencies` | `getComputedValueDependencies` | 200 401 404 422 500 503 |
| PATCH | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task` | `updateTaskFacet` | 200 400 401 403 404 409 412 422 500 503 |
| PATCH | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line` | `updateEstimateLine` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/predecessors` | `setPredecessors` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/progress` | `setTaskProgress` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/remaining` | `setLineRemaining` | 200 400 401 403 404 409 412 422 500 503 |
| PUT | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/tracking` | `setNodeTracking` | 200 400 401 403 404 409 412 422 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/move` | `moveNodes` | 200 400 401 403 404 409 412 422 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste-preview` | `previewPaste` | 200 400 401 403 404 413 422 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste` | `applyPaste` | 200 400 401 403 404 409 412 422 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/undo` | `undoLastChange` | 200 401 403 404 409 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/redo` | `redoLastUndo` | 200 401 403 404 409 500 503 |
| POST | `/projects/{project_id}/revisions/{revision_id}/skeleton` | `generatePlanningSkeleton` | 201 401 403 404 409 500 503 |
| GET | `/projects/{project_id}/risks` | `listRisks` | 200 401 404 422 500 503 |
| POST | `/projects/{project_id}/risks` | `createRisk` | 201 400 401 403 404 409 422 500 503 |
| GET | `/projects/{project_id}/risks/{risk_id}` | `getRisk` | 200 401 404 422 500 503 |
| PATCH | `/projects/{project_id}/risks/{risk_id}` | `updateRisk` | 200 400 401 403 404 409 412 422 500 503 |
| DELETE | `/projects/{project_id}/risks/{risk_id}` | `deleteRisk` | 204 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/risks/{risk_id}/reviews` | `listRiskReviews` | 200 401 404 422 500 503 |
| POST | `/projects/{project_id}/risks/{risk_id}/reviews` | `reviewRisk` | 201 400 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/risks/{risk_id}/occurrence` | `getRiskOccurrenceReport` | 200 401 404 409 500 503 |
| POST | `/projects/{project_id}/risks/{risk_id}/occurrence` | `declareRiskOccurrence` | 202 400 401 403 404 409 412 422 500 503 |
| GET | `/projects/{project_id}/risks/coverage` | `getProjectRiskCoverage` | 200 401 404 422 500 503 |
| GET | `/projects/{project_id}/risks/matrix` | `getProjectRiskMatrix` | 200 401 404 422 500 503 |
| GET | `/health` | `getLiveness` | 200 500 503 |
| GET | `/installation` | `getInstallation` | 200 500 503 |
| GET | `/health/ready` | `getReadiness` | 200 500 503 |
| GET | `/metrics` | `getMetrics` | 200 404 500 |
| GET | `/system/status` | `getSystemStatus` | 200 401 404 500 503 |
| GET | `/tasks` | `listBackgroundTasks` | 200 401 422 500 503 |
| GET | `/tasks/{task_id}` | `getBackgroundTask` | 200 401 404 500 503 |
| GET | `/tasks/{task_id}/result` | `getBackgroundTaskResult` | 200 401 404 409 500 503 |


## Annexe V — La cohérence des fixtures entre elles et avec l'univers témoin, par script

Périmètre : les 724 fixtures de `fixtures/api/**/*.json` (704 dans `fixtures/api/`, 20 dans
`fixtures/api/volume/` ; 396 portent `summary` et `value`, 328 aussi une `description`), lues et
croisées par neuf scripts Python (`python3 -I`, listés au « Relevé »), puis par lecture ciblée de
quelque soixante fixtures. Lu en entier : `docs/api/DECISIONS.md` « L'univers témoin » (l. 1777–2723),
`docs/api/README-fr.md` (94 l., tableau « Conventions » en entier), `tools/src/wftools/mockids.py`
(familles d'identifiants, l. 60–140), `tools/tests/test_mockwitness.py` (l. 285–400, la table clé →
famille), `tools/src/wftools/examples.py` (188 l.), `tools/src/wftools/mockwitness.py:53`
(`TODAY = 2026-06-03 14:05 UTC`), `fixtures/examples.json` (92 exemples), `common.yaml` (`LockVersion`
l. 92, `Problem` l. 141–240, `ErrorCode` l. 394–620, `ProblemParams` l. 730–935), les schémas
`NodeTotals` (revisions.yaml:1089–1117), `RevisionComparison.amount_deltas` (2367–2381),
`finish_overdue` (1228, 1384), `Revision.version_name` (31–35), `RiskCommand` (risks.yaml:187–212),
`RemainingIndicators`/`EstimateIndicators`/`PortfolioProjectRow.delta_to_reference`
(indicators.yaml:160–240, portfolio.yaml:68–85), `getProjectIndicators` 409 (analysis.yaml:240–264),
`completeChunkedUpload` 409 (exchanges.yaml:180–188) ; spécification §4.6.2 (l. 4259–4329) ; décisions
#487 (DECISIONS 1686), #1398 (9930–9946), #1352/#421 (7118–7124), EP-02/L25 « Les tâches de fond sont
les suites d'écritures faites aujourd'hui » (C5). Suivi : les constats de la revue du 2026-10-28 qui
portent sur les fixtures (section « 5. Les fixtures », l. 158–170, et le tableau général).

### Synthèse

Le témoin est arithmétiquement et chronologiquement juste : sur 13 562 identifiants (62 347
occurrences, 6 585 présents dans plusieurs fixtures), aucun ne désigne deux objets ; toutes les
parts somment à 1 selon la règle du README (reste sur la plus grande), tous les totaux recalculables
le sont exactement (indicateurs, couverture, matrice, coûts réels, plan de charge, décaissements,
`meta` contre `items`), et vingt-cinq égalités croisées entre `project_indicators`,
`remaining_indicators`, `risk_coverage`, `risks`, `risk_matrix`, `index_history`, `cost_curve*`,
`earned_value_curves`, `actual_costs`, `revisions` et la ligne du témoin dans `portfolio_projects`
tiennent au centime. Les 8 662 horodatages sont en `Z`, les 3 907 audits ordonnés, les 4 167 tâches
`start ≤ finish`, aucun instant n'est antérieur à l'installation ni postérieur à 14 h 05 hors les
suites de tâches (dix minutes) et les expirations déclarées ; les 7 018 commandes sont cohérentes
(`is_available` ⇔ `missing_conditions` vide), le seul projet terminal ne liste aucune commande, les
274 enveloppes `Problem` portent les paramètres de leur code et un `summary` qui dit le même refus.
Les écarts qu'un script relève se résolvent tous par une variante déclarée, une écriture, un instant
antérieur, une règle du schéma (#487, #1398, `finish_overdue` des seules tâches démarrées) ou une
session sans permission. Ce qui reste : **7 constats, 0 bloquant, 0 majeur, 7 mineurs** — le
mécanisme des exemples numériques cités (`examples`) qu'aucune fixture n'emploie (92 exemples,
0 cité), un 409 sans aucun paramètre, deux chronologies d'exemples qui se contredisent (celle des
sauvegardes et celle des compteurs de version), un même nom de champ (`delta_to_reference`) de signe
opposé dans deux fixtures, une corrélation hors du schéma du témoin, et les volumes du §4.6.2 que
les fixtures de `volume/` ne couvrent qu'en partie. Suivi des constats du 2026-10-28 sur les
fixtures : 9 réglés, 1 partiel, 3 non réglés, 0 sans objet.

### Constats

#### V-01 — Aucune fixture ne cite un exemple numérique du Vérif : `make check-fixtures` passe à vide
- **gravité** : mineur
- **emplacement** : `fixtures/examples.json` (92 exemples) ; `tools/src/wftools/examples.py:83-93`
  (`cited`, qui cherche une clé `examples` dans chaque fixture) ; `fixtures/api/**/*.json` (aucune ne
  porte la clé)
- **spécification** : WF-QUA-0020 — chaque exemple numérique d'un Vérif « est un cas de test du noyau »
  (docstring d'`examples.py`, l. 7–9) ; brief : « `make check-fixtures` vérifie que chaque fixture qui
  cite un exemple cite un existant »
- **le contrat dit** : `python -m wftools.examples` → « 92 numeric examples, 0 cited by a fixture », puis
  92 lignes « not covered » ; le contrôle réussit (code 0) parce qu'il n'a rien à vérifier
- **la fixture dit** : `grep -rl '"examples"' fixtures --include=*.json` ne trouve que `examples.json`.
  Pourtant dix exemples sont reproduits en valeur sans être cités : WF-RIS-0060 (lignes de 120 et 80
  budgétées à zéro, `nodes_estimate.json`, `risk_occurred_detail.json`) ; WF-RIS-0050 (200 à 30 % →
  provision 60, `risks.json` risque 752) ; WF-DEV-0020 (12,5 h × 80 = 1 000, `nodes_estimate.json`
  ligne 10) ; WF-INTF-0180 (1 234,56, `nodes_estimate.json` ligne 11) ; WF-PLA-0160 (8 h/j, 40 h/sem,
  20 j/mois → 2 j = 16 h, 1 sem = 40 h, 1 m = 160 h, `duration_units.json`) ; WF-PTF-0050 (dix offres
  sorties, quatre gagnées → `conversion_rate` 0,4, `volume/portfolio_value.json`) ; WF-REF-0160 (bornes
  1, 5 et 10 %, `reference_settings.json`, `risk_matrix.json`) ; WF-IND-0050 et WF-IND-0070/0080
  (projections et indices, formules vérifiées sur `project_indicators.json`, cf. relevé H) ;
  WF-RAE-0020 (marge = budget − coût réel − reste, signe négatif au-delà, `remaining_indicators.json:17`) ;
  WF-PRJ-0050 (« SP/01 » et « Synthèse », `subproject_code_invalid.json`, `subproject_code_reserved.json`).
  Deux exemples ne sont reproduits par aucune fixture : WF-EXP-0020 (installation neuve : probabilités
  25/50/75 %, six semaines — le témoin porte 10/30/60 % et 8 semaines dans `reference_settings.json`) et
  WF-CRE-0020 (`A.ABC.26001/10001` — le témoin dit `PRJ-002/SP-CAB`, `import_actual_costs_first.json`).
- **décision** : `DECISIONS.md` ne parle pas de la clé `examples` ; aucune
- **proposition** : soit faire citer par les générateurs (`mocktext`, `mockdata`) la clé de l'exemple que
  chaque fixture reproduit (`"examples": ["WF-RIS-0050-A#ba9e53e8bcb3"]`), au moins pour les dix
  ci-dessus, et faire échouer `check-fixtures` quand un exemple F0 n'est cité par aucune fixture ; soit
  retirer le mécanisme et la phrase du brief/README qui le décrit. À trancher.

#### V-02 — `project_indicators_offer.json` : un 409 `STATE_FORBIDS_OPERATION` sans aucun paramètre
- **gravité** : mineur (à trancher)
- **emplacement** : `fixtures/api/project_indicators_offer.json:4-6` ; `docs/api/paths/analysis.yaml:254-264`
  (`getProjectIndicators`, 409, réemployé l. 371 et 421 par les courbes) ; à côté,
  `fixtures/api/project_indicators_not_in_progress.json:7-8` (`state: pricing`, `state_enum: ProjectState`)
- **spécification** : WF-IHM-0090 — le refus nomme ce qui manque ; WF-ARC-0110 — « code et paramètres
  suffisent au front pour rendre le texte »
- **le contrat dit** : README-fr.md:48 — « le refus d'une commande qu'un état rend indisponible est un
  409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` nommant la condition qui manque » ;
  `Problem.params` (common.yaml:168–175) — `state` et `state_enum` pour « l'état d'un projet qui n'a
  pas atteint l'état En cours, dont on demande les indicateurs ». `analysis.yaml:256-258` déclare
  pourtant la variante : « révision nommée par `revision_id` marquée avant lui, **sans `params.state`**,
  le projet étant en cours »
- **la fixture dit** : `{"code": "STATE_FORBIDS_OPERATION", "status": 409, "correlation_id": …}` — ni
  `params`, ni `missing_condition`, ni `state`. Des 75 fixtures `STATE_FORBIDS_OPERATION`, c'est la seule
  sans condition ni état (la 74e, `chunked_upload_incomplete.json`, porte `missing_parts`, que
  `exchanges.yaml:181-183` déclare). Le front reçoit deux refus du même code sur la même opération,
  l'un avec `state`, l'autre nu : il ne peut pas phraser le second autrement que « état interdit ».
- **décision** : aucune trouvée sur cette variante (`grep -n "project_indicators_offer" DECISIONS.md`)
- **proposition** : donner à ce refus une condition, comme toute commande : `params.missing_condition:
  revision_marked_in_progress` (à ajouter à `CommandCondition`), ou rendre `state`/`state_enum` de
  l'état du projet au marquage (`pricing`) ; et aligner `analysis.yaml:256-258`. À trancher.

#### V-03 — Les compteurs de version se contredisent d'une fixture à l'autre : le marquage compte pour la 101, pas pour la 100
- **gravité** : mineur (reprise de E-16, non réglé)
- **emplacement** : `fixtures/api/revisions.json:245-363` (offre 100, `marked`, `lock_version: 1`) contre
  `:242` (101, `marked`, `lock_version: 3`) ; `revision_offer.json:34` (v1) ;
  `revisions_designation_open.json:6` (101 brouillon à la version 2) ; `revision_created.json:121`
  (révision neuve à 1), `amendment_created.json:22` (différentiel neuf à 1),
  `structures_without_tasks.json:30` (structure principale neuve à 0), `work_breakdown_default.json:8`
  (lotissement par défaut à 0) ; `common.yaml:92-100` (`LockVersion`, `minimum: 0`, « une création n'en
  a pas »)
- **spécification** : WF-IHM-0110 — la version suit chaque écriture
- **le contrat dit** : `DECISIONS.md:7118-7124` (#1352, US-0640/L4) — la 101 « brouillon à sa version 2
  […] son marquage porte une version de plus, la 3 » ; `LockVersion` — « toute modification le porte
  […] une création n'en a pas »
- **la fixture dit** : l'offre 100 est créée le 3 novembre 2025 et marquée le 15 décembre, et reste à la
  version 1 dans `revisions.json`, `revisions_marked.json`, `revision_offer.json` et
  `revisions_designation_open.json` : son marquage n'a pas compté, quand celui de la 101 compte. Et un
  objet neuf est à 1 (révision, différentiel, nœud créé) ou à 0 (structure principale, lotissement par
  défaut) selon la fixture, le schéma disant qu'« une création n'en a pas ».
- **décision** : `DECISIONS.md:7118-7124` tient pour la 101 ; rien ne dit pourquoi la 100 y échappe
- **proposition** : porter l'offre 100 à la version 2 dans les quatre fixtures (créée à 1, marquée à 2),
  et fixer dans `LockVersion` la valeur d'un objet neuf (0 partout, ou 1 partout) en alignant
  `structures_without_tasks` et `work_breakdown_default`, ou `revision_created`/`amendment_created`.

#### V-04 — La chronologie des sauvegardes de 14 h 04 se contredit toujours
- **gravité** : mineur (reprise de B-07, non réglé)
- **emplacement** : `fixtures/api/task_backup_queued.json:8` (sauvegarde mise en file à 14:04:00) ;
  `backup_pending.json:5` (prise à 14:04:50) ; `restore_during_backup_refused.json:7` (restauration de
  14:04:20 refusée, `no_backup_running`) ; `task_restore_queued.json:8` (restauration acceptée et mise en
  file à 14:04:30) ; `backup_start_during_restore_refused.json:7` (sauvegarde de 14:04:40 refusée,
  `no_restore_running`) ; `backup_retain_refused.json` (14:04:40, même motif)
- **spécification** : WF-ADM-0150, WF-ADM-0160 — une sauvegarde et une restauration ne s'exécutent pas
  en même temps
- **le contrat dit** : les cinq résumés s'enchaînent explicitement l'un à l'autre (« pendant que la
  sauvegarde manuelle mise en file à 14 h 04 s'exécute (task_backup_queued) », « pendant que la
  restauration mise en file à 14 h 04 min 30 s s'exécute (task_restore_queued) »)
- **la fixture dit** : la sauvegarde court de 14:04:00 à 14:04:50 ; à 14:04:20 une restauration est
  refusée parce qu'elle court ; à 14:04:30 une restauration est acceptée alors qu'elle court encore ; à
  14:04:40 une sauvegarde est refusée parce que la restauration court ; à 14:04:50 la sauvegarde est
  prise pendant cette restauration. Deux refus et deux acceptations incompatibles sur cinquante secondes.
- **décision** : `DECISIONS.md:2275-2290` (EP-02/L25, C5) — « chaque exemple de tâche de fond est une
  suite possible, indépendante des autres, et non un moment d'une seule séquence » : la décision couvre
  des exemples indépendants, pas des résumés qui se citent l'un l'autre comme une seule séquence
- **proposition** : décaler la restauration acceptée après la fin de la sauvegarde (par exemple
  `task_restore_queued` à 14:05:30, `backup_start_during_restore_refused` et `backup_retain_refused` à
  14:05:40), ou retirer des résumés les renvois qui enchaînent les exemples.

#### V-05 — `delta_to_reference` : le même nom, le même témoin, deux signes
- **gravité** : mineur (déclaré par le contrat ; à trancher)
- **emplacement** : `fixtures/api/remaining_indicators.json:17` (`"delta_to_reference": "-641535.13"`) ;
  `fixtures/api/volume/portfolio_projects.json:7` (ligne PRJ-001, `"delta_to_reference": "641535.13"`) ;
  `project_indicators.json:18` (`variance_project_manager: 641535.13`) ;
  `docs/api/components/schemas/indicators.yaml:211-218, 231-236`, `portfolio.yaml:72-77`
- **spécification** : WF-RAE-0020 (1.0.1) — « la marge sur le budget vaut − 50 » pour budget 1 000, coût
  réel 500, reste 550 ; WF-PTF-0040 — « une projection de 1 050 et un écart de 50 » pour les mêmes nombres
- **le contrat dit** : `indicators.yaml:213-218` — « le reste à engager parle de marge […] le budget moins
  la somme du coût réel et du reste à engager […] Le portefeuille et les projections parlent d'écart,
  positif au-delà du budget » : les deux sens sont décrits, chacun suit son exigence
- **la fixture dit** : −641 535,13 ici, +641 535,13 là, pour la même grandeur du même projet au même
  instant (vérifié : `reference_budget − actual_cost − remaining` = −641 535,13 ; `project_manager −
  reference_budget` = +641 535,13). Un implémenteur du front qui réemploie le composant d'une vue dans
  l'autre inverse le signe sans qu'aucun type ne l'arrête.
- **décision** : EP-02/L35 (#466, vocabulaire « marge » / « écart »), US-0701/L1 (WF-RAE-0020, signe
  inversé) — tient ; la spécification 1.0.1 porte elle-même les deux sens
- **proposition** : nommer la marge autrement que l'écart — `RemainingIndicators.margin_to_reference`
  (et `SubprojectBalance.margin`) contre `PortfolioProjectRow.delta_to_reference` — ; un renommage avant
  le gel ne coûte rien, après il romprait le contrat. À trancher avec l'auteur.

#### V-06 — Une corrélation hors du schéma d'identifiants du témoin
- **gravité** : mineur
- **emplacement** : `fixtures/api/dependencies_entered.json:9`
  (`"correlation_id": "4f1c2b9e-6a1d-4c8e-9b7a-2d5e8f0a1c33"`)
- **spécification** : — (convention du témoin)
- **le contrat dit** : `DECISIONS.md:1842-1851` (EP-02/L20) — « une famille d'identifiants par nature
  d'objet, sur des plages disjointes » ; `mockids.py` — corrélations 960–989, 1010–1199, 1300–1599,
  1600–1999 ; `test_mockwitness.py:395` vérifie chaque identifiant qui **commence** par le préfixe
- **la fixture dit** : des 13 562 identifiants des fixtures, 6 n'ont pas le préfixe
  `01926f3a-7c00-7000-8000-` : les 5 `subject` de l'annuaire (`identity_sync_report_*.json`, externes,
  légitimes) et cette corrélation, écrite à la main, que le test ne voit pas parce qu'il ne retient que
  les identifiants préfixés
- **décision** : EP-02/L21 — « `dependencies_entered`, un refus sans nœud, reste écrit à la main » ; rien
  sur son identifiant
- **proposition** : lui donner une corrélation de la famille (`01926f3a-7c00-7000-8000-000000001nnn`), et
  faire relever par `test_mockwitness` tout UUID non préfixé hors des clés `subject`.

#### V-07 — Les volumes du §4.6.2 ne sont tenus que pour une partie des grandeurs
- **gravité** : mineur
- **emplacement** : `fixtures/api/volume/*.json` (20 fichiers) ; `docs/spec/waterfall-spec.md:4263-4288`
  (tableau 13), `4292-4307` (tableau 14)
- **spécification** : §4.6.2 — 300 projets, 1 000 tâches et 5 000 lignes, 30 risques par projet « portant
  chacun un devis propre d'une vingtaine de tâches », 10 sous-projets, 150 rôles, 200 catégories,
  15 années de taux, 40 nœuds d'organisation, 500 comptes, 50 contributeurs par projet, 18 000 lignes de
  coût réel, 130 révisions marquées
- **le contrat dit** : chaque résumé de `volume/` se réclame « du §4.6.2 »
- **la fixture dit** : tenus — 300 projets (`portfolio_projects.json` : 269 en cours + 31 en chiffrage,
  `meta.total: 300`), 1 000 tâches dont 15 du cœur, 9 phases, 27 lots, 922 tâches de travail, 27 jalons,
  et 5 000 lignes (`nodes_thousand.json`, décomptes exacts), 200 catégories dont 150 de main-d'œuvre
  (`cost_categories.json`, `hourly_rate_grid.json` : 150 lignes × 15 ans, 2012–2026), 5 999 nœuds de la
  comparaison (`comparison_volume.json` : 998 tâches + 5 001 lignes, dont 1 tâche et 1 ligne retirées,
  totaux 997/5 000 ✓). Non tenus ou absents — `portfolio_risks.json` porte **429** risques identifiés pour
  269 projets en cours (1,6 par projet) là où l'hypothèse en donne 30 par projet, chacun avec un devis
  propre d'une vingtaine de tâches ; aucune fixture de volume pour 150 rôles (`resource_roles.json` : 5),
  500 comptes (`users.json` : 7), 40 nœuds d'organisation (`org_nodes.json` : 4), 10 sous-projets
  (`subprojects.json` : 2), 50 contributeurs (`contributors.json` : 4), 18 000 lignes de coût
  (`actual_costs.json` : 27), 130 révisions marquées (`revisions.json` : 2). Le §4.6.2 n'est pas une
  exigence (« ce ne sont pas des exigences »), mais les objectifs de temps de réponse du tableau 15 se
  mesurent « aux volumes ci-dessus » : les listes paginées des comptes, des rôles et des contributeurs
  n'ont pas d'exemple à cette échelle.
- **décision** : EP-02/L26 (le portefeuille), EP-02/L27 (la structure) — tiennent pour ce qu'elles
  couvrent ; rien sur les risques à 30 par projet ni sur les listes du référentiel et des comptes
- **proposition** : dire dans les résumés de `volume/` ce que chaque fixture tient du §4.6.2 et ce
  qu'elle ne tient pas (les risques du portefeuille), et, si le front doit éprouver ses listes
  paginées, ajouter `volume/users.json` (500), `volume/resource_roles.json` (150),
  `volume/org_nodes.json` (40) et `volume/contributors.json` (50).

### Ce qui est juste

- **Identifiants** : 13 562 UUID distincts ; chaque identifiant qui apparaît dans plusieurs fixtures
  (6 585) y porte le même libellé, code, nom ou adresse, aux seules exceptions déclarées : les écritures
  qui renomment (`cost_category_updated`, `resource_role_updated`, `cost_type_updated`,
  `calendar_updated`, `org_node_renamed_under_inactive`, `subproject_updated`, `access_role_renamed`,
  `user_renamed`, `user_renamed_deactivated`, que `audit_events_administration` reprend aux libellés du
  moment), les variantes d'anonymisation (`*_anonymized`), de désactivation (`risk_dismissed_category_
  deactivated`, `volume/cost_categories_type_deactivated`) et le rattachement du poste 712 « Poste 1.1 »
  à la « Réception usine » (`task_attached`, `milestone_completed`, écritures que `work_breakdown` ne
  connaît pas encore : « qu'aucune tâche ne porte »). La révision 101 à `version_name: null` dans
  `rate_update_applied`, `revision_rate_update_offered` et `revisions_designation_open` est un
  brouillon (« nul tant que la révision est en cours », revisions.yaml:35). Toutes les familles de
  `mockids.IDENTIFIERS` sont respectées (test existant, rejoué). Les identifiants référencés absents
  des listes sont tous attendus : objets que l'écriture crée (projet 3, révision 103, structures 207–216,
  compte 308, catégorie 406, rôle 456, nature 464, nœud 476, calendrier 484, rôle d'habilitation 708,
  risque 754, sous-projet 803, chronologie 1002, postes 714–718), objets inactifs que la liste par défaut
  omet (nœuds 474–475, calendrier 483 — celui de l'automaticien désactivé, que `resource_roles.json`
  cite —, sauvegardes 908–909 en variante).
- **Totaux et parts** : 17 répartitions (`by_cost_type`, `by_subproject`, `budget_by_cost_type`,
  `remaining_by_cost_type`, `labor_by_org_node`) somment exactement à 1 avec le reste sur la plus grande,
  chaque part égale à `amount / Σ` à quatre décimales ; les 3 parts de lot (`by_work_package`) sont
  `amount / total` sans reste, comme le README le veut. `remaining_indicators*.by_subproject` :
  `variance = budget − actual_cost − remaining`, `is_over_budget` et `zone` cohérents, Σ `remaining` =
  `total`, Σ `budget` = `reference_budget`, Σ `actual_cost` = `actual_cost` du projet.
  `risks`/`risk_matrix`/`portfolio_risks` : `total = identified + occurred + dismissed`, les totaux par
  état égalent la somme des provisions des points, Σ `cells.count` = nombre de points identifiés, la
  case et la zone de chaque point suivent les bornes (`risk_matrix_no_basis` déclare son cas : gravité
  non calculable, niveau 1). `actual_costs*` : `tracked + excluded = overall`, Σ lignes = totaux.
  `meta.total` contre `items` : 75 listes justes. `project_indicators`, `project_indicators_marked`,
  `portfolio_performance` : `cost_index = EV/AC`, `schedule_index = EV/PV`, écarts, `at_budget = AC +
  B − EV`, `project_manager = AC + RAE`, `at_observed_rate = B·AC/EV`, `financial_progress =
  AC/(AC+RAE)`, `budget_consumption = AC/B`, les trois `variance_*` = projection − budget, à quatre
  décimales (G-08 réglé : 0,941 et 0,9088). `zone_distribution` : 269 projets par indice. Couverture :
  `coverage_variance = reserve − remaining_provisions − occurred_cost` (4 fixtures). Plan de charge :
  `monthly_totals` = Σ rôles, `load_ratio = hours/capacity`, zone `alert` au-delà de la capacité,
  capacité agrégée = Σ rôles (6 fixtures) ; les sommes que les résumés citent (67 153,50 h ; 13 352 ;
  68 841) sont celles des mois. Décaissements : Σ `forecast` = 67 470 132,98 = reste à engager,
  Σ `past` = 1 412 970,20 = coût réel. Comptes rendus d'import : `unchanged_count = read_count −
  rejected − écarts de tâches ajoutées/mises à jour` (15 fixtures, règle de exchanges.yaml:269-280).
  `NodeTotals` : 24 lectures ; les onze écarts bruts sont tous une règle écrite — totaux de la lecture
  sans `kinds` (#487 : `nodes_planning`, `nodes_timeline`, `nodes_nested`), sans `difference` (#1398 :
  `comparison_differences`, `nodes_amendment_differences`), ancêtres rendus pour la lisibilité hors
  décompte (`nodes_milestone`, `nodes_estimate_filtered`), lignes retirées rendues à leur place hors
  totaux (`comparison*`, `nodes_amendment`, `comparison_volume` : 5 001 lignes rendues, 5 000 comptées).
  Les `amount_deltas` d'une comparaison suivent la règle de revisions.yaml:2373-2376 (sous-arbre :
  602 650 ; `difference` : 852 710 ; entière : 852 925, ce que chaque résumé dit).
- **Égalités croisées du témoin** (25, toutes vraies) : `project_indicators.remaining` =
  `remaining_indicators.total` ; `remaining_indicators.coverage` = `risk_coverage` ;
  `risk_matrix.totals` = `risks.totals` ; `reserve` 850 060 partout ; `provisions_identified` =
  `risks.totals.identified` = 500 000 ; ligne PRJ-001 de `portfolio_projects` = `project_indicators`
  (budget, projection, écart, indices) et `last_marked_at` = `revisions.json` 101 `marked_at` ;
  dernier point d'`index_history` = indices du jour ; derniers points de `cost_curve` (budget
  68 241 568,05 au 31 août 2029 ; coût réel) et d'`earned_value_curves` (PV, EV, AC) = indicateurs ;
  `estimate_indicators.delta_to_reference` = −`coverage_variance` = −349 860 ; `portfolio_value.
  order_book` = `portfolio_performance.reference_budget` ; `actual_costs.totals.tracked` = coût réel ;
  `pilot_health` : 133 + 29 + 30 + 20 = 212 signaux, 17 semaines depuis le 1er février ;
  `hourly_rate_corrected` 87,20 contre 86,98 dans la grille (MO-003, 2016) ; FA-2026-0412 à 1 800 dans
  `actual_costs` et « 1 850 au lieu de 1 800 » dans `import_actual_costs_analysed` ; les numéros de
  ligne cités (10, 11, 28, 29, 30) sont ceux de `nodes_estimate` et `nodes_thousand`.
- **Dates** : 8 662 horodatages en `Z` ; 3 907 audits `created_at ≤ updated_at` ; 4 167 tâches
  `start ≤ finish` ; 118 `started_on ≤ completed_on` ; 205 `started_on` et 118 `completed_on` ≤ 3 juin ;
  3 164 `progress` cohérents avec `started_on`/`completed_on` ; `finish_overdue` = « démarrée et fin
  < date de calcul » sur 3 164 tâches (le seul écart est `structure_planning_start_advanced`, variante
  datée du 20 février) ; 8 révisions `status`/`marked_at`/`created_at` cohérentes et ≤ aujourd'hui ;
  31 périodes `from ≤ to` ; aucun instant avant le 1er septembre 2025 ; après 14 h 05 seulement les
  tâches de fond (jusqu'à 14:10, dont l'audit `audit_events_import_applied` à 14:08:30) et les
  `expires_at` (dépôts, imports, lien de mot de passe). La chronologie du témoin est celle de
  DECISIONS : projet créé le 6 octobre 2025 à 9 h, en chiffrage le 3 novembre à 8 h 30, en cours le
  15 janvier 2026 à 11 h, modifié le 2 février ; offre 100 créée le 3 novembre, marquée le 15 décembre
  à 16 h ; 101 créée le 12 janvier à 10 h, marquée le 1er février à 9 h ; 102 ouverte le 2 février ;
  risques 751–753 créés le 12 janvier à 10 h, 10 h 30 et 11 h, 752 survenu le 20 février, 753 écarté le
  2 février, 751 réexaminé le 2 février (25 %, 1 250 000) et le 2 mars (40 %) ; sauvegardes du 28 mai
  au 3 juin à 1 h plus la manuelle du 30 janvier ; annuaire relu à 2 h, test de restauration le 1er juin
  à 3 h ; imports aux instants de L25 ; `rate_update` 78,50 → 80,00 et 73,50 → 75,00.
- **États et commandes** : 7 018 commandes `is_available` ⇔ `missing_conditions == []` ;
  `project_completed` (seul projet terminal) et `subprojects_completed` sans aucune commande ;
  révisions marquées : écritures indisponibles par `revision_draft`, exports disponibles ; risque
  survenu sans saisie (`risk_not_occurred`), écarté modifiable et réexaminable (risks.yaml:205) ;
  566 objets `is_active` cohérents avec `deactivate`/`reactivate`/`update` ; 18 212 `lock_version`
  ≥ 0 (trois à 0 sur des objets neufs, admis par `LockVersion`). Liste contre lecture unitaire : 152
  paires (projets, révisions, risques, comptes, rôles, sous-projets, catégories, natures, nœuds
  d'organisation, calendriers, structures, sauvegardes, chronologies, lignes de coût, imports, tâches) ;
  les 7 qui diffèrent sont des variantes déclarées (sauvegarde non vérifiée, ligne exclue, inactifs,
  instant antérieur, anonymisation) ; `revision_offer.json` et l'item 100 de `revisions.json` sont
  identiques, commandes comprises (E-15 réglé) ; 305 paires d'un même objet à la même version avec
  commandes : les 216 différences sont toutes des sessions sans permission (`*_reader`, `*_estimator`,
  `*_auditor`), un instant antérieur (`revisions_designation_open`) ou le projet clos.
- **Enveloppes d'erreur** : 274 fixtures `Problem`, 33 codes ; chaque `STALE_LOCK_VERSION` (23) porte
  `expected_lock_version` seul ; chaque `ALREADY_EXISTS` (13) porte `fields[]` avec
  `conflicting_object_id`, sauf `hourly_rate_already_entered` (clé du chemin, exception du README) ;
  les 113 `VALIDATION_FAILED` portent `fields[]` sauf `dependencies_entered` (`params.field`, déclaré
  par `Problem.params`) ; 143 pointeurs commencent par `/` ; `PERMISSION_MISSING` → `missing_permission`,
  `NOT_CONTRIBUTOR`/`NOT_PROJECT_MANAGER` → `is_contributor`/`is_project_manager`,
  `REFERENCE_INCOMPLETE` → `missing_prerequisites`, `HOURLY_RATE_MISSING` → `missing_rates`,
  `SUMMARY_TASK_DERIVED` → `subordinate_node_ids`, `UNDO_CONFLICT` → objet et libellé en conflit. Les
  274 résumés disent le refus de leur code (lecture intégrale de la liste code / condition / champs /
  résumé).
- **Résumés et descriptions** : 1 299 nombres et 779 libellés cités ont été cherchés dans les valeurs ;
  les 117 nombres et 312 libellés absents sont tous des entrées de la requête refusée, des numéros de
  version ou de statut (101, 102, 201, 409, 412), des renvois à une autre fixture (vérifiés ci-dessus),
  des sommes de mois ou des formats (« 1 360 640,50 » pour `1360640.5`, 205 Gio pour
  220 117 073 920 octets). Aucun résumé ne contredit sa valeur.
- **Constats de la revue précédente trouvés corrigés** : A-01 (« Manager » porte `risk_settings.write`
  et `indicator_settings.write`), F-01 (les récapitulatives portent `total_float` et `is_critical`),
  E-10 (compteurs 3 et 1), E-15, I-12 (`format_version: null` sur les extractions), G-08, G-15 (plus de
  nature « Provision » dans le budget agrégé), M-10 (aucun point à l'offre dans `milestone_tracking`),
  D-02 (`lose` absente de `project.json`).

### Doutes

- `cost_imports.json:7-8` : la réextraction du 11 mai rejette **12 345** lignes d'autres projets et le
  fichier sans période **37**, quand l'extraction d'avril n'en rejette qu'une (`import_actual_costs_first`)
  et que DECISIONS (EP-02/L25) ne parle que d'une ligne d'un autre projet. Aucune fixture de compte rendu
  ne montre ces deux imports ; le résumé est cohérent avec la valeur. Nombre vraisemblable pour une
  extraction de tout l'ERP, ou reliquat d'un exemple ? À confirmer par l'auteur du générateur
  (`mockwitnesscosts`).
- `nodes_planning.json`, `nodes_timeline.json`, `nodes_nested.json` : les totaux comptent des lignes que
  `kinds=task` ne rend pas ; #487 et parameters.yaml:116 le décident, mais `NodeTotals`
  (revisions.yaml:1100-1101) dit encore « les montants et les heures sont ceux des seules lignes de devis
  retenues par les filtres » sans nommer `kinds` parmi les filtres qui ne retiennent pas : une phrase à
  compléter plutôt qu'un constat.
- `volume/portfolio_risks.json` : `totals.occurred` (2 739 060) et `totals.dismissed` (5 537 000) ne se
  recalculent pas depuis `points`, qui ne porte que les identifiés (429) ; le résumé le dit (« chaque
  risque identifié compté dans sa case et placé en point ») et `period_outcome` porte les mêmes nombres.
  Le front ne peut pas vérifier ces deux totaux ; c'est le contrat qui le veut.
- `milestone_tracking.json` : la « Réception usine » a un point au 3 juin 14 h 05 (révision courante,
  non marquée) après celui de la référence ; le résumé dit « un point par révision marquée à l'état En
  cours » puis décrit ce point du jour. Cohérent avec `index_history` (dernier point au jour), mais la
  phrase du résumé mériterait de nommer le point du jour.
- `reference_settings.json` : probabilités 10/30/60 %, 8 semaines entre revues ; WF-EXP-0020 donne
  25/50/75 % et six semaines à une installation neuve. Le témoin n'est pas neuf et peut les avoir
  changées ; aucune fixture ne montre les valeurs par défaut.

### Suivi des constats du 2026-10-28

| Constat | État | Où / pourquoi |
|---|---|---|
| A-01 | réglé | `access_roles.json`, rôle « Manager » : `risk_settings.write` et `indicator_settings.write` présents |
| F-01 (aussi L-10) | réglé | les récapitulatives portent `total_float` et `is_critical` (`nodes.json` « Études » : `total_float` 0, `is_critical` vrai ; `comparison.json` « Installation sur site » : 597,5 j) |
| E-10 | réglé | `structure_merge_report_without_current_revision.json` : `main_structure_lock_version: 3`, `amendment_lock_version: 1` |
| E-15 | réglé | `revision_offer.json` et l'item 100 de `revisions.json` : mêmes commandes, exports compris, même version |
| E-16 | non réglé | V-03 : offre marquée à 1 quand la 101 marquée passe à 3 ; objets neufs à 0 ou à 1 selon la fixture |
| B-07 | non réglé | V-04 : restauration acceptée à 14:04:30 pendant la sauvegarde de 14:04:00–14:04:50 ; la décision C5 ne couvre pas des résumés qui s'enchaînent |
| I-12 | réglé | `import_actual_costs_analysed.json` : `format_version: null` pour `kind: actual_costs` |
| G-08 | réglé | `volume/portfolio_performance.json` : `cost_index` 0,941 (= 0,9410), `schedule_index` 0,9088 |
| G-15 | réglé | `volume/portfolio_cost_structure.json` : `budget_by_cost_type` main-d'œuvre 0,55 et débours 0,45, sans nature « Provision » |
| M-10 | réglé | `milestone_tracking.json` : la réception usine n'a pas de point à l'offre ; la réception des études finit sur la diagonale au 24 avril |
| M-05 | partiellement réglé | `nodes_risk_occurred.json` : les tâches fusionnées gardent leur mode (« Relance du fournisseur » en manuel, les deux autres automatiques) ; la description de leur placement relève de l'annexe H |
| D-02 (aussi L-03) | réglé | `project.json` : `lose` n'est plus listée sur le projet en cours (`complete`, `abandon` seules sorties) |
| J-21 | non réglé | `risk_matrix_no_basis.json` toujours référencée par aucune opération (seule fixture orpheline, brief) |

### Relevé

Scripts (tous sous `revue/v/`,
exécutés par `python3 -I`, sorties `.out` à côté) : `common.py` (chargement et parcours), `s1_ids.py`
(table uuid → champs voisins, conflits, préfixe), `s1b_dangling.py` (familles, références absentes des
listes), `s2_sums.py` (parts, totaux, formules, égalités croisées), `s3_dates.py` et `s3b_rules.py`
(dates, `finish_overdue`, `unchanged_count`), `s4_states.py` et `s4b_cmds.py` (commandes, liste contre
unitaire), `s5_problems.py` (enveloppes `Problem`), `s6_volume.py` (tailles des volumes), `s7_text.py`
(nombres et libellés des résumés), `s8_targeted.py` et `s9_universe.py` (vérifications ciblées et
chronologie du témoin), `peek.py` (lecture tronquée d'une fixture).

| Vérification | Testées | En écart brut | Après lecture |
|---|---|---|---|
| 1. UUID distincts / occurrences / dans plusieurs fixtures | 13 562 / 62 347 / 6 585 | 23 conflits de voisinage | 0 (écritures, variantes, `ProblemTask`) |
| 1. UUID hors préfixe témoin | 13 562 | 6 | 1 (V-06 ; 5 `subject` externes) |
| 1. Références absentes des listes (15 familles) | 15 registres | 29 identifiants | 0 (créations, inactifs, variantes) |
| 2. Parts d'une répartition / parts de lot | 17 / 3 | 0 / 0 | 0 |
| 2. `by_subproject` du reste à engager (variance, zone, Σ) | 2 | 0 | 0 |
| 2. Totaux des risques / cases de la matrice | 6 / 3 | 1 / 1 | 0 (points identifiés seuls ; `no_basis` déclaré) |
| 2. Coûts réels (tracked + excluded, Σ lignes) | 5 | 0 | 0 |
| 2. `meta.total` contre `items` | 75 | 0 | 0 |
| 2. `NodeTotals` contre Σ lignes / récapitulatives contre Σ enfants | 24 / 24 | 11 / 9 | 0 (#487, #1398, ancêtres, retirés) |
| 2. Plan de charge (Σ, `load_ratio`, zones, capacité) | 6 | 0 | 0 |
| 2. Indicateurs projet / portefeuille (10 formules) ; `zone_distribution` | 4 ; 1 | 0 | 0 |
| 2. Couverture des risques | 4 | 0 | 0 |
| 2. Comptes rendus d'import (`unchanged_count`) | 15 | 0 | 0 |
| 2. Égalités croisées du témoin | 25 | 0 | 0 |
| 3. Horodatages en `Z` | 8 662 | 0 | 0 |
| 3. `created_at ≤ updated_at` | 3 907 | 0 | 0 |
| 3. `start ≤ finish` ; `started_on ≤ completed_on` ; ≤ aujourd'hui | 4 167 ; 118 ; 323 | 0 | 0 |
| 3. `progress` contre dates ; `finish_overdue` | 3 164 ; 3 164 | 0 ; 1 | 0 (variante du 20 février) |
| 3. Révisions (`status`, `marked_at`, `created_at`) ; périodes | 8 ; 31 | 0 | 0 |
| 3. Instants après 14 h 05 / avant l'installation | 8 662 | 43 / 0 | 0 (tâches de fond, expirations) |
| 4. `is_available` ⇔ conditions vides | 7 018 | 0 | 0 |
| 4. `lock_version ≥ 1` | 18 212 | 3 à 0 | V-03 (objets neufs, règle flottante) |
| 4. Projet terminal sans commande / révisions / risques / actifs | 1 / 8 / 5 / 566 | 0 / 0 / 1 / 0 | 0 (écarté modifiable, risks.yaml:205) |
| 4. Liste contre unitaire (champs) ; même objet même version (commandes) | 152 ; 305 | 7 ; 216 | 0 (variantes, sessions) |
| 5. `Problem` : paramètres du code ; pointeurs ; résumé contre code | 274 ; 143 ; 274 | 4 ; 0 ; 0 | 1 (V-02) |
| 6. Volumes contre §4.6.2 | 20 fixtures, 13 grandeurs | 7 grandeurs sans fixture, 1 hors échelle | V-07 |
| 7. Nombres / libellés des résumés absents de la valeur | 1 299 / 779 | 117 / 312 | 0 |
| 8. Exemples numériques cités / reproduits (échantillon) | 92 / 12 | 0 cité | V-01 (10 reproduits, 2 non) |

