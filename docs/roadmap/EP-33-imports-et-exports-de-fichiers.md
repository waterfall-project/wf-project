---
id: EP-33
titre: Fiabiliser les allers-retours de fichiers — rapprochement MS Project, bornes des classeurs, compte rendu confirmé, comptes rendus d'import et leur purge
statut: en cours
depend_de: EP-08
famille: front, back
issue: 4523
---

# EP-33 — Imports et exports de fichiers

## Objet

Les allers-retours de fichiers portent un bloquant et le plus grand nombre de majeurs de la revue du
2026-11-14 (foyer « les allers-retours de fichiers ») : à la réimportation d'un planning MS Project
une tâche ajoutée peut prendre l'identité d'une tâche existante, un classeur s'ouvre sans borne de
décompression, l'application d'un import ne tient pas le compte rendu confirmé, une colonne absente
se lit comme des cellules vides. Cet EPIC les corrige, avec les comptes rendus d'import que rien ne
supprime et l'écran des imports.

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Ses US, sa conception et son plan de lots
datent du cadrage du 2026-11-21, validés par l'auteur le même jour ; ses issues sont ouvertes
depuis.

## Ce qui en fait partie

- le rapprochement des tâches à la réimportation d'un planning MS Project, et les bornes de son
  lecteur, constantes d'unité comprises (US-3170, US-3180) ;
- une borne de décompression commune aux classeurs téléversés, tenue jusque dans l'analyse XML de
  leurs membres, et leur lecture hors du verrou du projet (US-3190) ;
- le refus d'un onglet dont une colonne lue manque (US-3200), et l'import du devis qui retire ses
  lignes en une écriture (US-3220) ;
- l'application d'un import liée au compte rendu que l'utilisateur a confirmé, par le compteur de
  la structure lue (US-3210) ;
- l'import du reste à engager : la terminaison d'une tâche selon la spécification 1.0.7, et le
  montant écrit dit au compte rendu (US-3230) ;
- `uploadFile` sous permission, avec un plafond de dépôts en attente par compte (US-3240) ;
- les comptes rendus d'import : leur suppression à l'échéance et à l'abandon, leur liste, la tâche
  qu'ils nomment et que la purge d'EP-13 supprime (US-3250) ;
- un import pendant une panne passagère du stockage (US-3260) ;
- l'élément d'OTP comparé en entier et le code de sous-projet libre (spécification 1.0.7), avec la
  reprise des codes déjà saisis (US-3270) ;
- l'écran des imports : la commande « Relancer », le refus de l'application, le formulaire pendant
  un envoi, la zone de dépôt, un long compte rendu (US-3280) ;
- le devis et le reste à engager exportés, qui s'affichent justes sans recalcul du tableur, et les
  colonnes d'heures du devis réduites aux codes comptables de ses rôles (US-3640, ajoutée le
  2026-11-22).

## Ce qui n'en fait pas partie

- le collage dans une grille — EP-34 ;
- l'export du devis selon l'annexe B (#4399) — EP-31 ; US-3640 ne corrige que le classeur
  d'aujourd'hui : ses valeurs en cache et le domaine de ses colonnes d'heures ;
- la restauration et son dépôt, et l'écouteur `after_commit` sous point de sauvegarde qui supprime
  le fichier d'un import avant la validation de sa tâche (BEX-04, #4476) — EP-39 ;
- la limite de mémoire du service dans le chart — EP-13 et EP-39 ;
- la mesure aux volumes du réimport d'un devis et de l'écran d'un compte rendu — EP-13 (US-2970) et
  EP-40 : EP-33 corrige sans mesure préalable (décision de l'auteur du 2026-11-21) ;
- la pagination d'un compte rendu au contrat — rien : l'écran borne son rendu (US-3280) ;
- une tâche inactive d'un fichier MS Project (`<Active>0</Active>`), importée comme une tâche
  vivante : la revue la dit plausible, sans fichier réel qui l'éprouve — à rejouer à la recette de
  l'aller-retour MS Project, hors de cet EPIC.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Comme EP-17,
EP-18 et EP-23 (décision de l'auteur du 2026-10-28), chaque US cite, avec tout leur Vérif, les
exigences dont ses tests relèvent ; les phrases qu'elle ne touche pas sont des écarts qui disent qui
les constate. Leur portée reste celle des EPIC qui les ouvrent et les closent : `WF-INTF-0040-A` et
`WF-INTF-0080-A` (closes par EP-07), `WF-INTF-0070-A` (EP-09), `WF-INTF-0100-A`, `WF-INTF-0120-A` et
`WF-PRJ-0050-A` (EP-08), `WF-ARC-0100-A` et `WF-DAT-0120-A` (EP-06), `WF-DAT-0080-A` (EP-07),
`WF-EXP-0040-A` (EP-13), `WF-CRE-0020-A` et `WF-IHM-0080-A` (EP-09), `WF-ADM-0020-A` (EP-05).

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

Déjà servies, et reprises ici pour ce que les constats y corrigent : `openImport`, `getImport`,
`applyImport` (US-3170, US-3180, US-3190, US-3200, US-3210, US-3220, US-3230, US-3260, US-3270) ;
`setImportDurationRule` (US-3210, US-3280) ; `uploadFile` (US-3240, US-3280) ;
`listImports`, `abandonImport` (US-3250, US-3280) ; `createProject`, `updateProject`,
`createSubproject`, `updateSubproject`, `listSubprojects`, `listActualCosts`, `requestExport`
(US-3270).

Le contrat change, par des modifications que la conception écrira avant le code qui les consomme,
chacune avec son entrée dans `docs/api/DECISIONS.md` :

- `applyImport` refuse un compte rendu que la structure a dépassé, par une condition nouvelle, et
  dit la règle pour les quatre natures (US-3210) ;
- `uploadFile` déclare son 403 et le refus du plafond de dépôts (US-3240) ;
- `ImportDetail.task` devient nul quand la tâche est purgée ; `listImports`, `getImport` et
  `abandonImport` disent la suppression des imports expirés et abandonnés (US-3250) ;
- `openImport` nomme, pour un devis et un reste à engager, les colonnes qui manquent à un onglet
  (US-3200) ;
- le compte rendu d'un reste à engager annonce le montant écrit quand il diffère du montant saisi
  (US-3230) ;
- l'élément d'OTP comparé en entier : `PROJECT_CODE_INVALID` tombe, `DeclaredSubprojectCode` perd sa
  borne de 31 caractères, ses caractères interdits et ses noms réservés et refuse le code du projet,
  `WBS_ELEMENT_INVALID`, `lines_outside_project`, `unknown_subproject` et
  `ActualCostLine.subproject_code` sont revus, le compte rendu nomme chaque élément inconnu et le
  nombre de ses lignes (US-3270).

## Préalables

EP-08 fusionné, qui a touché les imports (différentiels, cascades de `import_report`). Les comptes
rendus d'import (US-3250) sont à livrer avant la fusion d'EP-13 : sa purge des tâches de fond fait
répondre 500 à l'ouverture d'un import de plus de trente jours. Les exemples à barre oblique
d'US-3270 entrent au harnais des exemples, qu'EP-11 livre : ce lot attend EP-11 dans `main`.

Décisions de l'auteur du 2026-11-21, au cadrage, que les US portent : le compteur de la structure
gardé à l'analyse, pour le planning, le devis et le reste à engager, et l'import périmé refusé, à
redéposer (#4420) ; la spécification mène pour la suppression des comptes rendus, à la passe de
purge, les échoués et les refusés gardés comme les appliqués (#4425) ; un fichier dont un onglet a
perdu une colonne lue refusé à l'ouverture (#4421) ; les lignes de coût en attente d'un sous-projet
inconnu supprimées par la reprise (#3966) ; vingt dépôts en attente par compte (#4423) ; 10 000
tâches et 50 niveaux pour un planning importé (#4426) ; l'écart entre le montant saisi et le montant
écrit dit au compte rendu (#4428) ; pas de repli par `UID` dans un fichier exporté par Waterfall
(#3337) ; les suppressions de l'import du devis corrigées sans mesure préalable (#4422) ; le rendu
d'un long compte rendu borné dans l'écran seul (FCO-06) ; les doubles d'une extraction comparés dans
le projet seul (BRC-04).

## Conduite

Vague 1 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 3.

## Définition de fini

- le scénario de #3337 — une structure importée d'un fichier aux `UID` 1, 2, 3, 5, 8, 9, 12,
  exportée, une tâche insérée dans MS Project après la ligne 2, réimportée — garde à T5 sa lignée
  et ses lignes de devis, et ajoute la tâche nouvelle ;
- un fichier MS Project de plus de 10 000 tâches, de plus de 50 niveaux, ou portant une durée ou un
  entier hors bornes, ou une constante d'unité nulle ou négative (#4766), fait échouer son import
  sur `FILE_FORMAT_UNREADABLE`, jamais sur `INTERNAL_ERROR` ;
- un classeur de 68 515 octets dont un membre se décompresse en 64 Mio en annonçant moins est
  refusé à l'ouverture sans que la mémoire du service ne monte, de même un classeur de 13 705 octets
  dont une ligne porte 2 000 000 de cellules vides (#4734), et l'ouverture d'un import ne lit plus l'en-tête sous le
  verrou du projet ;
- un devis ou un reste à engager dont un onglet a perdu « ID ligne », « Débours restant » ou
  « Quantité » est refusé à l'ouverture, les colonnes nommées, et rien n'est analysé ;
- une tâche créée par `createNode` entre l'analyse et la confirmation d'un planning MS Project
  n'est pas supprimée : l'application est refusée en nommant la condition, l'import est `refused` ;
- le réimport d'un devis sans « ID ligne » rejoue le moteur une fois ;
- un compte sans permission d'import reçoit 403 de `uploadFile`, rien n'est écrit au stockage, et
  le vingt et unième dépôt en attente d'un compte est refusé ;
- un import expiré ou abandonné n'est plus dans la base après la passe de purge, et `getImport`
  d'un import dont la tâche est purgée répond 200, `task` nul ;
- un import dont la lecture du fichier rencontre une indisponibilité du stockage reste là où il en
  était, son fichier en place, et aboutit à la tentative suivante ;
- les exemples de WF-CRE-0020-A et de WF-PRJ-0050-A à barre oblique passent au harnais des exemples
  (#4022), et la migration de reprise laisse chaque ligne de coût imputée à un sous-projet imputée
  au même ;
- l'application échouée d'un import n'offre plus « Relancer », et un refus de l'application relit
  l'écran ;
- `make build-openapi`, `make inventory`, `make client-up-to-date` et
  `make server-models-up-to-date` passent, et `docs/api/DECISIONS.md` a ses entrées ;
- `make check` passe sur la branche de l'EPIC, la file de fusion est verte ; `make roadmap` et
  `make requirements` passent ;
- les dix-neuf constats reçus sont fermés par la fusion de leur lot.

## Constats reçus

Tous rattachés à leur lot, avec leur décision, à l'ouverture des issues de l'EPIC (#4523), le
2026-11-21.

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3337 — back : à la réimportation d'un planning MS Project, une tâche ajoutée peut prendre le nœud
  d'une tâche existante (WF-INTF-0040) → US-3170 ;
- #3978 — back : la terminaison d'une tâche par l'import du reste à engager, à confronter à
  WF-INTF-0120 (spécification 1.0.7) → US-3230 ;
- #3966 — contrat : l'élément d'OTP comparé en entier, le code de sous-projet libre (spécification
  1.0.7, WF-CRE-0020, WF-PRJ-0050) → US-3270.

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4419 — les classeurs téléversés ouverts sans borne de décompression, et l'en-tête lu sous le
  verrou du projet (BEX-03, BRC-02, BCH-06, BRC-03, BEX-05) → US-3190 ;
- #4420 — l'application d'un import MS Project n'est pas liée au compte rendu confirmé (BEX-02,
  CTB-01) — le contrat change → US-3210 ;
- #4421 — une colonne lue absente d'un onglet se lit comme des cellules vides (BCH-03) → US-3200 ;
- #4422 — import du devis : une suppression par ligne retirée, avec un rejeu du moteur chacune
  (BCH-05) → US-3220, sans mesure préalable ;
- #4423 — `uploadFile` : une écriture sans permission, sans 403 et sans quota (CTB-02, BAC-09) — le
  contrat change → US-3240 ;
- #4424 — « Relancer » offert pour l'application échouée d'un import, que le service refuse toujours
  (FCO-02, FCO-04) → US-3280 ;
- #4425 — les comptes rendus d'import : suppression à l'échéance, liste, tâche purgée, taille
  (BEX-07, BEX-10, BEX-11, DON-05, FCO-06) — avant la fusion d'EP-13 → US-3250, et US-3280 pour la
  taille du rendu (FCO-06) ;
- #4426 — le lecteur MS Project : bornes et replis (BEX-08, BEX-09, BEX-14) → US-3180, et US-3240
  pour le nom de fichier qui porte un octet NUL ;
- #4427 — un import pendant une panne passagère du stockage (BEX-13) → US-3260 ;
- #4428 — l'import du reste à engager : montant saisi, montant écrit (BCH-11) → US-3230 ;
- #4429 — l'écran des imports : formulaire et zone de dépôt après un envoi (FCO-03, FCO-05, FCO-14)
  → US-3280.

Constats de la même revue joints à une issue ci-dessus : BRC-04 (une ligne du projet rejetée
« doublée » à cause d'une ligne d'un autre projet du même fichier) et BPR-09 (`api/subprojects.py`
importe la borne du code de sous-projet de la table privée du module des projets), à #3966
→ US-3270.

Constats d'EP-08 reçus le 2026-11-22 (décision de l'utilisateur : « l'export du devis »), relevés à
l'essai de l'export sur `epic/EP-08` le 2026-11-20, rangés dans une US ajoutée le même jour :

- #4317 — back : l'export du devis affiche ses montants et ses totaux à zéro sans recalcul du
  tableur → US-3640 ;
- #4319 — back : l'export du devis porte une colonne d'heures par catégorie de main-d'œuvre, non par
  code des rôles → US-3640.

Constats relevés à la livraison d'US-3190/L1 et d'US-3180, tranchés par l'auteur le 2026-11-23 :

- #4734 — back : l'analyse XML d'openpyxl amplifie un classeur dans les bornes (13 Ko, 583 Mio) →
  US-3190/L1b, une pré-lecture en flux ; une limite de mémoire du conteneur est écartée ; à la
  question du livreur (2026-11-23), les chaînes partagées, les styles, les noms définis et le
  produit lignes × colonnes → US-3190/L2b, qui les a mesurés ; bornes fixées par l'auteur le
  2026-11-23 (« Les bornes des classeurs ») ;
- #4736 — spec : le classeur de 64 Mio du critère d'US-3190 contre la borne de 200 Mio déclarés →
  le critère est précisé dans le sens livré (un membre qui se décompresse au-delà de ce qu'il
  annonce), sans borne par membre ;
- #4766 — back : une constante d'unité nulle ou négative d'un fichier MS Project finit en
  `INTERNAL_ERROR` → US-3180b, refusée par `FILE_FORMAT_UNREADABLE`, sans borne haute.

Constats relevés à la livraison d'US-3190/L1b et à la mesure d'US-3190/L2b, confiés à US-3190/L2b :

- #4837 — back : la pré-lecture refuse le VML mal formé d'une feuille de graphique, qu'openpyxl ne
  lit pas ;
- #4838 — tests : la tolérance d'un VML mal formé n'est pas éprouvée pour `[Content_Types].xml` ni
  pour un membre en double ;
- #4848 — back : un élément qu'openpyxl rejette par `TypeError` (un `<fill/>` de `styles.xml`)
  finit en `INTERNAL_ERROR` → `TypeError` rattrapée à l'ouverture et à l'itération des lignes,
  dans `opened_workbook` seulement, pour qu'une erreur de programmation d'un lecteur ne devienne
  pas un refus du fichier (décision de l'auteur du 2026-11-23).

Constat d'EP-32 reporté le 2026-11-23 (décision de l'auteur : le fichier d'EP-32 laisse l'import
d'un planning MS Project à EP-33, qui écrit `core/planning/importing.py`) :

- #4799 — contrat : l'import MS Project rend 500 sur une tâche créée sans heure travaillée, le
  contrat ne sait pas la nommer → US-3210b, après la livraison d'EP-32 dans `main`, qui apporte
  `TASK_WITHOUT_WORKING_HOURS` (US-3330).

Constats relevés à la livraison d'US-3170, US-3180, US-3180b, US-3200 et US-3210, tranchés par
l'auteur le 2026-11-23 :

- #4759 — back : un fichier tiers qui range de vrais UUID dans `Text1` est pris pour un export de
  Waterfall — limite acceptée, rejouée à la recette de l'aller-retour MS Project ;
- #4779, #4813 — instabilités de la file (Keycloak, `test_partitions`), vues une fois — on attend ;
  vues deux fois, le pilote ouvre le lot correctif ;
- #4784 — back : un onglet de lignes qui perd « Tâche » ou « Rôle ou catégorie » n'est ni refusé ni
  lu, et ses lignes se lisent absentes → US-3200b : la liste de #4421 s'étend aux deux clés ;
- #4785 — contrat : aucun exemple d'un devis refusé pour une colonne absente → US-3280, un exemple
  engendré, sans changement de forme ;
- #4786 — back : le devis et le reste à engager lus deux fois à l'ouverture — écarté, hors verrou,
  la mémoire tenue par les bornes, de l'ordre de 0,4 s sur 10 000 lignes ;
- #4787 — front : une accolade ou une apostrophe dans le refus des colonnes absentes → US-3280, un
  test ;
- #4791 — back : la copie d'une révision ouverte qui rechiffre ses lignes fait refuser à tort un
  import analysé dans la révision marquée → faux refus accepté, du côté sûr, figé par un test dans
  US-3210b ; ni colonne ni migration ;
- #4826 — back : une constante d'installation infime s'exporte à 0, que le lecteur refuse →
  US-3210b : l'export écrit les constantes d'unité à 1 au moins ; la saisie n'est pas bornée ;
- #4830 — tests : la citation du Vérif des constantes d'unité non littérale → US-3210b.

Constat d'EP-11 que ce cadrage nomme : #4022 — les exemples de WF-CRE-0020 et de WF-PRJ-0050 à barre
oblique attendent #3966 pour entrer au harnais (décision de l'auteur du 2026-11-19 : « avec le lot
qui réalisera #3966, à nommer par le cadreur ») → US-3270.

## Conception

Écrite le 2026-11-21, après la validation des US par l'auteur le même jour, et validée par lui le
même jour, contre `main`
(19fdc30c9) et les branches `epic/EP-08` — dont elle suppose le code des imports, EP-08 se fusionnant
avant le premier lot — et `epic/EP-13`. Courte, comme celles d'EP-18 et d'EP-23 : chaque issue porte
sa proposition, ses fichiers et ses tests, et fait foi pour le détail ; ce qui suit ne dit que ce
qu'elles laissent ouvert, ce qui s'en écarte, et ce que les décisions de l'auteur du 2026-11-21 y
changent.

**Tables et migrations.** Deux migrations, numérotées à la suite de celles de `main` au moment du
lot (EP-08 et EP-13 en portent chacune de leur côté).

- `import_report.structure_lock_version`, entier, nul (US-3210), avec une contrainte « non
  négatif » : le compteur de la structure que l'analyse a lue. Nul pour une extraction de coûts
  réels, pour un import analysé sans structure, et pour les comptes rendus analysés avant la colonne.
- La reprise des codes (US-3270), migration de données : `subproject.code` et
  `cost_line.subproject_code` passent à 100 caractères au plus, les contraintes de caractères
  interdits et de noms réservés du code d'un sous-projet tombent ; chaque `subproject.code` devient
  le code de son projet, une barre oblique, puis l'ancien code, et `cost_line.subproject_code` des
  lignes imputées suit ; les lignes de coût qui portent un code et aucun sous-projet sont
  supprimées, et la migration journalise leur nombre par projet. L'unicité du code dans le projet
  tient après le préfixe. La migration descendante retire le préfixe et ne rend pas les lignes
  supprimées : elle le dit.
- Aucune migration pour US-3250 — le droit `DELETE` sur `import_report` est déjà accordé — ni pour
  US-3240, qui compte les lignes de `file_upload` par `uploaded_by`, déjà indexé.

**Modules du noyau touchés.**

- `core/exchanges` porte la mécanique commune. Un ouvreur de classeurs entre dans son interface, à
  côté de l'analyseur XML durci : il lit `infolist()` de l'archive, refuse au-delà de 200 Mio de
  tailles décompressées déclarées ou de 1 000 membres, puis seulement ouvre le classeur ; les trois
  lecteurs passent par lui et bornent les onglets lus à 200 000 lignes et 10 000 000 de cellules
  en cumul, chaque ligne à 500 colonnes (US-3190).
  Le protocole `Format` remplace `read_header(session, head)` par deux étapes : `parse_header(head)`,
  pure, appelée avant `lock_project`, qui garde son refus au lieu de le lever, et
  `judge_header(session, parsed)`, sous le verrou, à la place que le contrat donne à ce refus dans
  l'ordre de `openImport` — l'ordre des refus ne change pas. `running.py` garde le compteur à
  l'analyse et le compare à l'application (US-3210), et ne fait plus échouer l'import sur une
  lecture du stockage qui casse (US-3260). `purge.py` supprime les lignes expirées et abandonnées
  (US-3250).
- `core/planning` : `_matched` en deux passes, le modèle lu disant si le fichier déclare le champ
  des lignées (US-3170) ; les bornes dans `msproject/reader.py` et le repli de `calendar_of` sur
  « Standard » (US-3180) ; le retrait de plusieurs lignes dans l'écriture de `write_lines`, que
  l'interface du planning expose à `core/estimate` (US-3220) ; une fonction de l'interface qui dit
  si une structure n'a pas été écrite depuis sa copie (US-3210) ; `_replayed` traduit le refus
  d'une tâche sans heure travaillée dans les `refusals` du compte rendu (US-3210b, #4799).
- `core/estimate` : les deux lecteurs Excel rendent leurs colonnes manquantes à `parse_header`
  (US-3200) ; `applying.py` ne boucle plus sur `delete_node` (US-3220) ; `remaining/analysing.py`
  signale le montant écrit (US-3230) ; l'onglet d'un sous-projet nommé d'après son code, le code en
  tête (US-3270).
- `core/costs` : `extraction.py` compare l'élément en entier, `analysing.py` ne compare les doubles
  que dans le projet, `impute_waiting_lines` disparaît avec son enregistrement auprès des projets
  (US-3270).
- `core/projects` : les règles du code d'un projet et d'un sous-projet, la borne exportée par
  l'interface (US-3270, BPR-09).
- `platform/uploads.py` : le compte des dépôts en attente d'un compte (US-3240).
  `platform/storage.py` n'est pas touché.

**Modifications du contrat.** Faites avant le code qui les consomme, par deux lots de contrat, l'un
pour la famille des échanges, l'autre pour #3966 ; chacune a son entrée dans
`docs/api/DECISIONS.md`, `info.version` restant `1.0.0` (« La règle d'après le gel »).

- `CommandCondition` gagne `import_structure_unchanged` : `applyImport` la nomme en 409
  `STATE_FORBIDS_OPERATION` après `import_file_accepted`, parmi les refus définitifs, et la tâche
  d'application échoue sur le même motif ; la description dit la règle des quatre natures. Un
  exemple, `import_apply_structure_changed` (US-3210).
- `CommandCondition` gagne `pending_uploads_below_limit` : `uploadFile` déclare 403
  (`PERMISSION_MISSING`) et 409 `STATE_FORBIDS_OPERATION`, `params.maximum` à 20 (US-3240).
- `ProblemImportedTask.lineage_id` devient nullable pour une tâche que le fichier crée, comme
  `ImportDifference` l'accepte : le refus `TASK_WITHOUT_WORKING_HOURS` d'EP-32 nomme une tâche
  créée à l'import, qui n'a encore ni nœud ni lignée (US-3210b, #4799).
- `ImportDetail.task` devient `BackgroundTaskRef` ou nul ; `listImports`, `getImport`,
  `abandonImport` et les états `expired` et `abandoned` disent la suppression à la passe de purge ;
  les exemples de liste et le témoin ne portent plus d'import expiré ni abandonné (US-3250).
- `ProblemMissingColumn` nomme aussi une colonne d'un devis ou d'un reste à engager : son en-tête
  tel que le format l'écrit, et `sheet`, l'onglet, absent pour une extraction de coûts réels
  (US-3200).
- `ImportSignal` gagne le code `AMOUNT_ROUNDED`, entré au catalogue des codes : la ligne par sa
  lignée et son libellé, la colonne `unit_disbursement`, `params.typed_amount` et
  `params.written_amount` ; `signals` n'est plus dit vide pour les imports Excel (US-3230).
- `uploadFile` refuse un nom portant un octet NUL comme le contrat refuse déjà un NUL dans un
  texte, sur `/file` (US-3240).
- #3966 : `PROJECT_CODE_INVALID` sort du catalogue ; `DeclaredSubprojectCode` passe à 100
  caractères, sans motif ni nom réservé, et `SUBPROJECT_CODE_INVALID` ne reste que pour un code égal
  à celui du projet, sur `/code`, sans ses paramètres `forbidden_characters` et `reserved_name` — à
  la création et au recodage d'un sous-projet, et sur le code d'un projet recodé vers celui de l'un
  de ses sous-projets ; `WBS_ELEMENT_INVALID` sort,
  `WBS_ELEMENT_OUTSIDE_PROJECT` devient le rejet de tout élément qui n'est ni le code du projet ni
  celui d'un de ses sous-projets ; le compte rendu gagne `unknown_wbs_elements`, chaque élément
  inconnu et le nombre de ses lignes ; `requires_confirmation_reasons` perd `unknown_subproject` ;
  `ActualCostLine.subproject_code` devient le code du sous-projet d'imputation, nul pour une ligne
  imputée au seul projet (US-3270).

**Ordre de construction.**

1. Le contrat des échanges, puis US-3250 en tête : c'est elle qui doit être dans `main` avant EP-13.
2. US-3190 avant US-3200, qui lit les en-têtes dans l'étape hors verrou qu'elle crée. US-3170,
   US-3180, US-3210, US-3220, US-3230, US-3240 et US-3260 ne dépendent que du contrat, quand elles
   en dépendent.
3. US-3270 : son contrat, puis le service et la migration ensemble — le code nouveau ne lit pas les
   codes anciens —, puis le front, le témoin et le harnais des exemples, qui demande EP-11 dans
   `main`.
4. US-3280 en dernier : elle rend les refus et les états que les autres ajoutent.

Trois règles de cet ordre, arrêtées avec le plan de lots, validé par l'auteur le 2026-11-21 :

- le second lot de contrat, celui de #3966, suit le premier : ils modifient les mêmes schémas ;
- un lot de contrat laisse la chaîne verte : il ajoute et assouplit, le service rendant la valeur
  neutre d'un champ nouveau — nul, liste vide — là où la régénération l'impose ; un code ne sort du
  catalogue qu'avec le lot du service qui cesse de l'émettre, les tests du service validant chaque
  réponse contre le contrat ;
- le témoin change avec le lot du service, non avec celui du contrat : son chargeur lit
  `imports.json` et les codes des sous-projets, et ses exemples sont les réponses du service sur le
  témoin chargé. L'extraction expirée du témoin n'est pas remplacée (US-3250).

**Décisions prises.**

- **Le compteur est gardé par le service, et le client n'envoie rien** (US-3210). La décision de
  `setImportDurationRule` (« Pas de compteur : aucune opération d'import n'en porte »,
  `docs/api/DECISIONS.md`) est révisée : aucune opération n'en porte toujours, mais l'application en
  compare un. Écarté : `ImportApply.lock_version`, que le client ne ferait que recopier d'une
  réponse.
- **La comparaison se fait deux fois** : à la demande, pour refuser sans tâche, et à l'exécution
  sous le verrou de la structure. Une structure analysée dans la révision marquée et écrite dans sa
  copie est jugée « non écrite depuis sa copie », par l'interface du planning ; la révision que la
  tâche crée elle-même n'est pas comparée. Une ouverture de la copie qui avance son compteur
  au-delà de la redatation (des lignes rechiffrées, une provision réécrite) la fait juger écrite :
  l'import est refusé à tort, en 409, et l'utilisateur redépose — faux refus accepté, du côté sûr
  (#4791, décision de l'auteur du 2026-11-23), figé par un test (US-3210b). Écarté : garder le
  compteur de la copie à son ouverture, une colonne et une migration de plus. Un compte rendu au compteur nul — analysé avant la
  colonne, ou par un worker d'avant pendant une mise à jour — s'applique sans comparaison, pendant
  les vingt-quatre heures qu'il vit. Écarté : le refuser, sous une condition qui mentirait.
- **La purge supprime dans la passe qui constate l'échéance** (US-3250) : elle ne passe plus par
  l'écriture de `expired`, qui reste un état lu. L'abandon écrit `abandoned`, que la passe suivante
  supprime. Écarté : un délai de grâce, que la spécification ne donne pas.
- **Le plafond des dépôts n'est pas un invariant** (US-3240) : il se compte sans verrou, avant
  l'écriture au stockage ; deux dépôts simultanés peuvent le passer d'un. Écarté : un verrou par
  compte, pour une garde contre une boucle. Le refus est un 409 d'état, selon la règle unique des
  refus d'état (J-01) ; écarté : un 429 et un code propre.
- **La panne du stockage se reconnaît dans `core/exchanges`** (US-3260) : de la lecture du fichier,
  seul l'objet manquant fait échouer l'import ; toute autre erreur est rendue indisponibilité du
  stockage, et la tâche reprend. Écarté : mettre la lecture en flux sous `reached()` dans
  `platform/storage.py`, qu'EP-13 réécrit (US-2860).
- **Les bornes des classeurs** (US-3190) : 200 Mio déclarés, la valeur que la revue propose, vingt
  fois le fichier compressé ; 200 000 lignes, dix fois les 18 000 lignes de coût de §4.6.2 ; 500
  colonnes, pour les colonnes conservées d'une extraction. Les lignes et les cellules se comptent
  avant l'ouverture, par une pré-lecture en flux des membres XML (US-3190/L1b, décision de l'auteur
  du 2026-11-23, #4734) : openpyxl matérialise une ligne entière avant de la tronquer, et un
  classeur de 13 Ko le fait monter à 583 Mio. Écartée : une limite de mémoire du conteneur. La
  pré-lecture lit tous les membres XML du classeur, pas seulement les onglets que le format lit :
  un onglet non lu au-delà des bornes fait aussi échouer l'import ; le classeur s'ouvrant en
  `read_only`, l'écart ne coûte pas de mémoire et évite de résoudre d'abord les onglets lus
  (décision de l'auteur du 2026-11-23). Les autres vecteurs, mesurés par US-3190/L2b et bornés
  par décision de l'auteur du 2026-11-23 : 1 000 000 de chaînes partagées, 65 536 éléments (runs)
  par chaîne, et 32 Mio de texte décompressé dans `sharedStrings.xml`, comptés en caractères (le
  texte coûte jusqu'à quatre fois sa taille en mémoire) ; dans `styles.xml`, `numFmts` 1 000,
  `fonts`, `fills`, `borders`, `tableStyles` et `colors` 1 024 chacune, `cellStyleXfs`, `cellXfs`,
  `cellStyles` et `dxfs` 65 490 chacune, les limites d'Excel, pour qu'un classeur qu'Excel écrit ne
  soit jamais refusé (les items d'une liste sont ses enfants ; ceux de `colors`, les couleurs de ses
  listes, comptées avec elles) ; 10 000 noms définis. La pré-lecture les compte et refuse avant
  l'ouverture. Les listes de `styles.xml` et les noms définis se comptent par nom local, enfants
  directs de la racine du membre, comme openpyxl les lit, commentaires et instructions de
  traitement compris (openpyxl en fait des items) ; une partie qu'openpyxl lit et qui déclare un
  type de document (DOCTYPE) est refusée, une entité non déclarée sous un DOCTYPE externe
  échappant à la pré-lecture. Le produit lignes × colonnes coûte 8,3 octets par cellule et 140 par ligne
  explicite (790 Mio pour 200 000 × 500, d'un fichier de 7,9 Ko) : les onglets lus sont bornés en
  cumul à 200 000 lignes **et**
  10 000 000 de cellules, comptées dans `bounded_rows` à mesure que les lignes arrivent ; le refus
  vient donc après l'ouverture, la mémoire tenue dans la borne (≈ 105 Mio). Écarté : compter les
  `<c>` à la pré-lecture, plus lent (10 à 30 %) et au risque d'un écart avec ce qu'openpyxl
  matérialise. Toutes les bornes atteintes à la fois tiennent sous 330 Mio. Les tests de borne
  mesurent la mémoire réelle du processus (`ru_maxrss`, dans un sous-processus) : `tracemalloc` ne
  voit pas libxml2 et sous-estime les styles et les noms jusqu'à 2,4 fois. Les
  bornes du lecteur MS Project (US-3180) hors celles de l'auteur : un entier de 18 chiffres au plus,
  une durée d'un million d'heures au plus ; une constante d'unité (`MinutesPerDay`,
  `MinutesPerWeek`, `DaysPerMonth`) strictement positive, sans borne haute (US-3180b, #4766).
- **Le code d'un sous-projet à 100 caractères** (US-3270) : la reprise préfixe un code de 31
  caractères d'un code de projet de 50 et d'une barre oblique, soit 82. Écarté : 50, que la reprise
  dépasserait.
- **`cost_line.subproject_code` reste** (US-3270), et porte le code du sous-projet d'imputation :
  la colonne ne devient pas « l'élément d'OTP », pour ne renommer ni la colonne ni le champ du
  contrat. La suppression de lignes de coût fait reculer la somme des compteurs que lit la clé du
  cache des indicateurs (#3629) : le lot de la migration dit comment il l'invalide.
- **Deux lots de contrat et non un par US** : chaque modification du contrat régénère le client et
  les modèles, et gêne les lots en cours. Écarté : le contrat dans le lot de chaque US.

---

## US-3170 — Un planning réimporté de MS Project rapproche ses tâches par la lignée d'abord, et n'adopte aucune tâche par coïncidence d'UID

- **statut** : fini
- **exigences** : `WF-INTF-0040-A`
- **opérations** : `openImport`, `getImport`, `applyImport`
- **issue** : #4531

**En tant que** chef de projet, **je veux** qu'un planning exporté, retravaillé dans MS Project puis
réimporté retrouve chacune de ses tâches par l'identifiant que l'export y a écrit, et qu'une tâche
que j'ai ajoutée dans MS Project soit toujours une tâche nouvelle, **afin de** ne jamais voir une
tâche nouvelle hériter de la lignée, des lignes de devis et de l'avancement d'une autre (#3337).

**Critères d'acceptation.**

- `WF-INTF-0040-A` — « Un planning exporté, retravaillé dans MS Project puis réimporté conserve les lignes de devis et les lignées de ses tâches, et ses tâches démarrées. » :
  éprouvé contre le service par le scénario de #3337 — une structure importée d'un fichier dont les
  `UID` sont 1, 2, 3, 5, 8, 9 et 12, des lignes de devis sous T5 ; son export ; une tâche insérée
  après la ligne 2, qui reçoit l'`UID` 8, sans lignée ; le réimport. T5 garde sa lignée, ses lignes
  de devis, son état et son rattachement ; la tâche insérée est `added` ; aucune tâche n'est
  `removed` ni créée en double, et le compte rendu ne présente aucune mise à jour du libellé de T5.
- propre à l'US : le rapprochement se fait en deux passes. La première rapproche, dans l'ordre du
  fichier, toute ligne qui porte une lignée que la structure connaît ; la seconde ne replie par
  l'`UID` (`external_id`) que parmi les tâches que la première n'a pas prises.
- propre à l'US : dans un fichier qui déclare le champ des lignées — un export de Waterfall, dont les
  `UID` sont des rangs —, une ligne sans lignée, ou dont la lignée n'est pas celle d'une tâche de la
  structure, n'est jamais rapprochée par son `UID` : elle est ajoutée.
- propre à l'US : un fichier qui ne déclare pas le champ des lignées — celui de MS Project, remanié
  avant le premier export — rapproche toujours ses tâches par leur `UID`, comme le motif de
  WF-INTF-0040 le demande ; le test de rapprochement par `UID` d'aujourd'hui reste vert.
- écart : `WF-INTF-0040-A` — « Un fichier XML produit par MS Project 2013 est importé sans erreur. » : constaté par EP-06, inchangé ; US-3180 l'éprouve pour les bornes du lecteur.
- écart : `WF-INTF-0040-A` — « Après import, les tâches et leurs liaisons de prédécesseur — type FD, DD, FF ou DF, et décalage — sont identiques à celles du fichier source ; une tâche en mode manuel du fichier est en mode manuel aux mêmes dates ; une tâche portant une contrainte « Pas avant le » est en mode manuel et signalée ; une tâche à 50 % d'avancement est importée non démarrée ; aucune ressource et aucun calendrier présents dans le fichier n'a été créé dans Waterfall, et l'utilisateur est informé que ces éléments ont été ignorés. » : constaté par EP-06, inchangé.
- écart : `WF-INTF-0040-A` — « Un fichier qui place la tâche d'un poste hors du sous-arbre de la tâche de son lot est rejeté et le compte rendu nomme les deux tâches ; un fichier dont une tâche rattachée a disparu est appliqué et le compte rendu nomme le poste qu'elle portait ; une tâche rattachée réimportée conserve son rattachement. » : constaté par EP-06 et EP-07, inchangé ; le
  scénario ci-dessus affirme en plus que T5 garde son rattachement.

**Notes de réalisation.** La proposition de #3337 fait foi, avec le complément retenu par l'auteur le
2026-11-21 : pas de repli par `UID` dans un fichier qui déclare le champ des lignées. Écarté :
faire écrire à l'export `UID = external_id`, qui change le fichier exporté et laisse des collisions
avec les tâches créées dans Waterfall. La numérotation d'une tâche ajoutée par MS Project (« plus
grand `UID` + 1 ») n'a pas été vérifiée dans MS Project lui-même : le scénario se rejoue à la
recette de l'aller-retour, la correction n'en dépend pas.

**Hors périmètre.** Les bornes du lecteur (US-3180) ; le compte rendu périmé (US-3210).

---

## US-3180 — Le lecteur MS Project refuse un fichier hors bornes par le refus du format, et lit une tâche manuelle sans calendrier nommé

- **statut** : fini
- **exigences** : `WF-INTF-0040-A`
- **opérations** : `openImport`, `getImport`
- **issue** : #4532

**En tant que** chef de projet, **je veux** qu'un fichier MS Project démesuré ou malformé échoue en
me disant que son format n'est pas lisible, et qu'un fichier écrit par un autre outil que MS Project
garde ses tâches manuelles à leurs dates, **afin de** savoir quoi corriger plutôt que de lire une
« erreur interne », et de ne pas perdre des dates sans signal (#4426).

**Critères d'acceptation.**

- `WF-INTF-0040-A` — « Un fichier XML produit par MS Project 2013 est importé sans erreur. » : sa
  forme pour les bornes : le corpus de MS Project s'importe toujours, et un planning de 10 000
  tâches sur 50 niveaux est accepté ; au-delà de 10 000 tâches ou de 50 niveaux, l'import échoue à
  l'analyse sur `FILE_FORMAT_UNREADABLE`, `expected_format` à `ms_project_schedule`, sans que le
  moteur ne soit rejoué. De même une durée que le lecteur ne peut pas porter (`PT999…H`) et un
  entier au-delà de la borne de chiffres du lecteur, dont un `UID` que `external_id` ne garderait
  pas, et une constante d'unité — `MinutesPerDay`, `MinutesPerWeek`, `DaysPerMonth` — nulle ou
  négative (US-3180b, #4766). Aucun de ces fichiers ne finit en `INTERNAL_ERROR`, et aucun n'échoue après un compte rendu
  accepté.
- `WF-INTF-0040-A` — « Après import, les tâches et leurs liaisons de prédécesseur — type FD, DD, FF ou DF, et décalage — sont identiques à celles du fichier source ; une tâche en mode manuel du fichier est en mode manuel aux mêmes dates ; une tâche portant une contrainte « Pas avant le » est en mode manuel et signalée ; une tâche à 50 % d'avancement est importée non démarrée ; aucune ressource et aucun calendrier présents dans le fichier n'a été créé dans Waterfall, et l'utilisateur est informé que ces éléments ont été ignorés. » : sa
  forme pour un fichier sans calendrier nommé : un fichier qui ne nomme pas le calendrier de son
  projet, ou qui nomme un calendrier qu'il ne porte pas, se lit sur le calendrier « Standard » de
  MS Project, comme l'écart de calendrier le fait déjà ; sa tâche manuelle, ou à contrainte de date,
  est en mode manuel aux dates du fichier, et `date_mismatches` compare ses dates. Le reste de la
  phrase est constaté par EP-06, inchangé.
- écart : `WF-INTF-0040-A` — « Un planning exporté, retravaillé dans MS Project puis réimporté conserve les lignes de devis et les lignées de ses tâches, et ses tâches démarrées. » : US-3170.
- écart : `WF-INTF-0040-A` — « Un fichier qui place la tâche d'un poste hors du sous-arbre de la tâche de son lot est rejeté et le compte rendu nomme les deux tâches ; un fichier dont une tâche rattachée a disparu est appliqué et le compte rendu nomme le poste qu'elle portait ; une tâche rattachée réimportée conserve son rattachement. » : constaté par EP-06 et EP-07, inchangé.

**Notes de réalisation.** Les bornes sont de l'auteur (2026-11-21) : 10 000 tâches, dix fois le
dimensionnement de §4.6.2, et 50 niveaux, qui ferment aussi le `RecursionError` du moteur. Les
tests du lecteur sont unitaires, un par valeur hostile, comme #4426 le propose.

**Hors périmètre.** Une tâche inactive (`<Active>0</Active>`), que la revue dit plausible sans
fichier réel : à la recette de l'aller-retour. Le nom de fichier qui porte un octet NUL, la
quatrième valeur hostile de BEX-08, que `uploadFile` refuse avec sa permission et son plafond
(US-3240) : il se juge avec le dépôt, non dans le lecteur.

---

## US-3190 — Un classeur téléversé est borné avant d'être ouvert, et son en-tête se lit hors du verrou du projet

- **statut** : fini
- **exigences** : `WF-INTF-0070-A`
- **opérations** : `openImport`, `getImport`, `applyImport`
- **issue** : #4527

**En tant qu'** exploitant, **je veux** qu'un classeur dont le contenu décompressé dépasse une
borne soit refusé avant que le service ne l'ouvre, et que la lecture de son en-tête ne retienne
aucune écriture du projet, **afin qu'** un fichier de quelques kilo-octets ne puisse ni épuiser la
mémoire du service ni bloquer les saisies de tous (#4419).

**Critères d'acceptation.**

- `WF-INTF-0070-A` — « Un fichier de devis ou de reste à engager sans version, ou d'une version non reconnue, est refusé avec un message qui nomme le format et la version attendus ; un fichier de coûts réels auquel manque une colonne exigée par la correspondance est refusé avec un message qui la nomme. » : sa
  forme pour un classeur hors bornes : pour les trois formats Excel, un classeur dont la somme des
  tailles décompressées que ses membres déclarent, ou le nombre de ses membres, passe la borne de
  la conception est refusé par `openImport`, 422 `FILE_FORMAT_UNREADABLE`, le format attendu nommé,
  sans avoir été ouvert par le lecteur de classeurs : éprouvé sur un classeur de 68 515 octets dont
  un membre se décompresse en 64 Mio en annonçant moins (#4736), et sur une archive dont un membre annonce 1 Gio, la mémoire du
  processus ne montant pas. Les refus de version et de colonne exigée sont constatés par EP-07 et
  EP-09, inchangés.
- `WF-INTF-0070-A` — « Le projet est inchangé. » : et rien n'est mis en file : aucun import n'est
  ouvert, le dépôt reste utilisable.
- `WF-INTF-0070-A` — « Un fichier conforme à chacun des formats de ANNEXE B: Formats d'échanges Excel est accepté. » : les
  classeurs que Waterfall exporte et ceux du témoin passent la borne ; les allers-retours du devis,
  du reste à engager et des coûts réels restent verts.
- propre à l'US : l'ouverture d'un import lit et juge l'en-tête du fichier avant de prendre le
  verrou du projet, puis rejuge sous le verrou ce qui dépend du projet : une écriture qui verrouille
  le projet n'attend pas la lecture d'un classeur — éprouvé comme l'application l'est déjà
  (`test_imports_application.py`), pour l'ouverture.
- propre à l'US : à l'analyse et à l'application, un lecteur ne matérialise que les onglets que son
  format lit, et un onglet du classeur, lu ou non, dont les lignes ou les colonnes passent la
  borne de la conception fait échouer l'import sur `FILE_FORMAT_UNREADABLE` ; lignes et
  cellules, vides comprises, se comptent avant l'ouverture, et un classeur de 13 705 octets dont
  une ligne porte 2 000 000 de cellules vides est refusé sans que la mémoire du processus ne
  monte (US-3190/L1b, #4734).
- propre à l'US : les chaînes partagées (leur nombre, leurs runs, leur texte), les listes de
  `styles.xml` et les noms définis d'un classeur ont chacun la borne de la conception, au-delà de
  laquelle l'import échoue avant l'ouverture sur `FILE_FORMAT_UNREADABLE` ; le cumul des onglets
  lus, 200 000 lignes et 10 000 000 de cellules, se compte à la lecture et fait échouer l'import
  de même, après l'ouverture, sans que la mémoire réelle du processus ne passe la borne que le
  test fixe (US-3190/L2b).

**Notes de réalisation.** Un seul ouvreur commun aux classeurs, dans l'interface des échanges, à
côté de l'analyseur XML durci : les trois sites d'ouverture (`estimate/excel/reader.py`,
`estimate/remaining/excel/reader.py`, `costs/extraction.py`) passent par lui. Les valeurs des bornes
sont de la conception. La borne se juge sur `infolist()`, et chaque membre est vérifié, par pas
bornés, ne pas se décompresser au-delà de ce qu'il déclare : `ZipFile.read` décompresse un membre
en entier avant de le couper (L1). La pré-lecture en flux des membres XML est d'US-3190/L1b
(#4734) ; les bornes des autres vecteurs et le cumul des onglets lus sont d'US-3190/L2b, qui
versionne ses scripts de mesure et sa fabrique de classeurs démesurés (des classeurs engendrés,
ceux des tests et du témoin, aucun autre).

**Hors périmètre.** La limite de mémoire du service dans le chart (EP-13, EP-39) ; la colonne
absente d'un onglet (US-3200).

---

## US-3200 — Un devis ou un reste à engager dont un onglet a perdu une colonne lue est refusé, colonnes nommées

- **statut** : fini
- **exigences** : `WF-INTF-0070-A`, `WF-INTF-0120-A`
- **opérations** : `openImport`
- **issue** : #4530

**En tant que** chef de projet, **je veux** qu'un classeur dont une colonne lue a été supprimée ou
renommée soit refusé en me nommant l'onglet et la colonne, **afin qu'** une colonne perdue ne mette
pas des restes à zéro, ne termine pas des tâches et ne double pas des lignes sous l'apparence de
mises à jour ordinaires (#4421).

**Critères d'acceptation.**

- `WF-INTF-0070-A` — « Un fichier de devis ou de reste à engager sans version, ou d'une version non reconnue, est refusé avec un message qui nomme le format et la version attendus ; un fichier de coûts réels auquel manque une colonne exigée par la correspondance est refusé avec un message qui la nomme. » : sa
  forme pour une colonne absente : un devis dont un onglet de lignes n'a plus « ID ligne »,
  « Quantité », « Heures » ou « Débours unitaire », et un reste à engager dont un onglet n'a plus
  « ID ligne », « Jours restants » ou « Débours restant », sont refusés par `openImport`, 422
  `FILE_FORMAT_UNREADABLE`, le format et la version attendus nommés, et `params.missing_columns`
  nommant chaque colonne manquante avec son onglet, comme le format « Coûts réels » nomme les
  siennes. Un en-tête renommé (« Débours restant (€) ») est une colonne absente.
- `WF-INTF-0070-A` — « Le projet est inchangé. » : rien n'est analysé : aucun reste n'est mis à
  zéro, aucune tâche n'est terminée, aucune ligne n'est créée ni retirée.
- `WF-INTF-0070-A` — « Un fichier conforme à chacun des formats de ANNEXE B: Formats d'échanges Excel est accepté. » : un
  classeur exporté, toutes ses colonnes lues présentes, s'ouvre comme avant ; une colonne que le
  format ne lit pas peut manquer.
- `WF-INTF-0120-A` — « Une cellule de reste effacée sur une ligne connue la met à zéro. » : la
  règle vaut pour une cellule vide d'une colonne présente, inchangée ; elle ne vaut plus pour une
  colonne absente, que le refus ci-dessus écarte.
- écart : `WF-INTF-0120-A` — « Même critère que WF-INTF-0100, appliqué aux grandeurs réestimées ; les montants budgétés et les lignées de toutes les lignes sont inchangés après l'import, et une ligne absente du fichier conserve son reste à engager. » : constaté par EP-09, inchangé.
- écart : `WF-INTF-0120-A` — « Un reste à engager exporté d'une révision marquée puis réimporté dans la révision en cours met à jour les lignes de même lignée sans en créer aucune. » : idem.
- écart : `WF-INTF-0120-A` — « Avec huit heures par jour, une ligne de main-d'œuvre dont le fichier porte trois jours a un reste de vingt-quatre heures. » : idem.
- écart : `WF-INTF-0120-A` — « Une tâche démarrée dont toutes les lignes, celles absentes du fichier comprises, sont à zéro après l'import, et dont le fichier en met au moins une à zéro, est terminée à la date de la revue ; une tâche non démarrée dont les lignes sont laissées telles quelles reste non réestimée. » : US-3230.
- écart : `WF-INTF-0120-A` — « Un fichier qui recopie une ligne avec sa lignée voit les deux lignes rejetées, et la ligne existante inchangée. » : constaté par EP-09, inchangé.
- écart : `WF-INTF-0120-A` — « Un fichier sans date de revue applique les lignes qui ne terminent aucune tâche et rejette celles qui en termineraient une. » : idem.
- écart : `WF-INTF-0120-A` — « Un onglet renommé dans Excel garde son sous-projet. » : US-3270.

**Notes de réalisation.** Décision de l'auteur du 2026-11-21 : le fichier est refusé à l'ouverture.
Écarté : rejeter au compte rendu chaque ligne de l'onglet, qui rend des milliers de rejets pour une
seule cause. Les deux lecteurs calculent déjà `missing_headers` et `unread_sheets`, que rien ne
lit ; la liste des colonnes dont l'absence refuse le fichier est celle de #4421, que la conception
arrête, étendue le 2026-11-23 aux deux clés d'un onglet de lignes, « Tâche » et « Rôle ou
catégorie » : un onglet qui porte au moins un en-tête lu du format sans elles est refusé, un onglet
sans aucun en-tête lu reste ignoré (US-3200b, #4784). La lecture des en-têtes de tous les onglets se fait dans l'étape hors verrou d'US-3190.

**Hors périmètre.** Les colonnes d'une extraction de coûts réels, déjà refusées (EP-09).

---

## US-3210 — Un import ne s'applique que sur la structure que son compte rendu a lue

- **statut** : fini
- **exigences** : `WF-ARC-0100-A`, `WF-INTF-0080-A`
- **opérations** : `applyImport`, `getImport`, `openImport`, `setImportDurationRule`
- **issue** : #4533

**En tant que** chef de projet, **je veux** que l'application d'un import soit refusée quand la
structure a été écrite depuis que j'ai lu son compte rendu, **afin de** ne jamais voir un planning
réimporté supprimer la tâche qu'un collègue vient de créer, ni écraser ce que le compte rendu disait
inchangé (#4420).

**Critères d'acceptation.**

- `WF-ARC-0100-A` — « Entre l'analyse et la confirmation, aucune donnée du projet n'a changé. » : sa
  forme pour ce que la confirmation applique : l'analyse garde le compteur de la structure qu'elle a
  lue, et l'application ne s'exécute que si ce compteur n'a pas avancé. Éprouvé par le scénario de
  #4420 : un planning MS Project analysé, une tâche et ses lignes de devis créées par `createNode`,
  puis `applyImport` — la tâche existe toujours, rien n'est écrit.
- `WF-ARC-0100-A` — « Un import confirmé par un utilisateur dont la permission est retirée avant l'exécution n'est pas appliqué, le refus nomme la condition manquante et son fichier n'est plus sur le stockage objet. » : il
  en va de même d'un import dont la structure a été écrite depuis l'analyse : `applyImport` le refuse
  par 409 `STATE_FORBIDS_OPERATION`, une condition nouvelle nommée, l'import passe `refused`, son
  fichier n'est plus sur le stockage objet, et l'utilisateur redépose. La condition est rejugée à
  l'exécution, sous le verrou de la structure : une écriture arrivée entre la demande et la tâche
  fait échouer la tâche sur le même motif, l'import `refused`.
- propre à l'US : la règle vaut pour le planning MS Project, le devis et le reste à engager, toute
  écriture de l'arbre de la structure — une cellule, un collage, un déplacement, une création, une
  suppression — périmant le compte rendu ; elle ne vaut pas pour les coûts réels, qui n'écrivent
  dans aucune structure, et le contrat le dit pour les quatre natures.
- propre à l'US : un import analysé sur un projet sans révision en cours s'applique à la révision
  qu'il crée ; si une révision a été ouverte puis écrite entre-temps, il est refusé de même.
- `WF-INTF-0080-A` — « Pour un planning MS Project saisi sur un autre calendrier, le compte rendu propose de garder les durées ou les dates ; changer d'option rend un nouveau compte rendu, et le projet reste inchangé jusqu'à la confirmation. » : la
  nouvelle analyse que le changement de règle lance garde le compteur qu'elle lit : c'est celui-là
  que l'application compare. Le choix lui-même est constaté par EP-24 (US-2000), inchangé.
- propre à l'US : le catalogue du front dit la condition nouvelle, et l'écran du compte rendu la
  présente comme les autres refus définitifs (US-3280 relit l'écran).
- écart : `WF-ARC-0100-A` — « L'interruption de l'application laisse le projet dans son état antérieur. » : constaté par EP-06, inchangé.
- écart : `WF-ARC-0100-A` — « Un compte rendu expiré ne peut plus être appliqué, et son fichier n'est plus sur le stockage objet. » : constaté par EP-06 ; US-3250 en supprime la ligne.
- écart : `WF-ARC-0100-A` — « Il en va de même si le projet est passé dans un état terminal entre-temps. » : constaté par EP-06, inchangé.
- écart : `WF-ARC-0100-A` — « Une application refusée parce qu'un marquage est en cours sur le projet peut être redemandée après lui, sans nouveau dépôt. » : constaté par EP-08 (US-2660), inchangé : la
  structure écrite n'est pas une condition passagère.
- écart : `WF-ARC-0100-A` — « Après l'abandon d'un différentiel sur lequel un import a été analysé, cet import ne peut plus être appliqué, et son fichier n'est plus sur le stockage objet au terme du délai d'expiration. » : constaté par EP-08 (US-3060), inchangé.
- écart : `WF-INTF-0080-A` — « Pour un fichier qui contient des lignes invalides, le compte rendu les liste avec leur motif avant la confirmation. » : constaté par EP-06 et EP-07, inchangé.
- écart : `WF-INTF-0080-A` — « Si l'utilisateur abandonne à cette étape, le projet reste inchangé. » : idem.
- écart : `WF-INTF-0080-A` — « Si l'import est interrompu pendant son application, le projet revient à son état antérieur. » : idem.

**Notes de réalisation.** Décisions de l'auteur du 2026-11-21 : le compteur est gardé par le
service, à l'analyse, dans `import_report` — le client n'envoie rien, `ImportApply` ne change pas — ;
la règle vaut pour les trois natures qui écrivent une structure ; l'import périmé est refusé pour de
bon, à redéposer. Écartés : recalculer le compte rendu sous verrou et le comparer à celui confirmé ;
étendre au planning la règle du devis (« ce que le compte rendu n'a pas annoncé retiré ne l'est
pas »), qui laisse écraser un libellé ; réanalyser sur place. La décision de `setImportDurationRule`
(« Pas de compteur : aucune opération d'import n'en porte », `docs/api/DECISIONS.md`) est révisée
pour l'application : la conception l'écrit. Le devis et le reste à engager gardent en plus leur règle
de confirmation (`Confirmed`), que le compteur rend sans objet sans la contredire.

**Hors périmètre.** L'historique annulable, qui ne reçoit rien d'un import (WF-IHM-0110).

---

## US-3220 — L'import d'un devis retire les lignes absentes du fichier dans l'écriture qui pose les autres

- **statut** : fini
- **exigences** : `WF-INTF-0100-A`
- **opérations** : `applyImport`
- **issue** : #4534

**En tant que** chef de projet, **je veux** que le réimport d'un devis construit dans Excel, dont
toutes les lignes sont nouvelles et toutes les anciennes retirées, s'applique en une écriture de
l'arbre, **afin que** son application ne tienne pas le verrou de la structure le temps de milliers
de rejeux du moteur (#4422).

**Critères d'acceptation.**

- `WF-INTF-0100-A` — « Un second import du même fichier donne un devis identique. » : sa forme pour
  un fichier sans « ID ligne » : le second import retire les N lignes du premier et pose les N du
  fichier dans une seule écriture de l'arbre, le moteur rejoué une fois — un test du service compte
  les rejeux —, et le devis obtenu est identique à celui du premier import.
- propre à l'US : ce que la suppression d'une ligne faisait ligne à ligne reste fait : une ligne de
  provision sous une tâche retirée est reportée comme aujourd'hui (EP-08, US-2580), les lignes
  gardées sous une tâche démarrée ou terminée le restent, et le compte rendu appliqué ne change pas.
- écart : `WF-INTF-0100-A` — « On importe un fichier qui comporte des lignes de main-d'œuvre et des lignes hors main-d'œuvre. » : constaté par EP-07, inchangé.
- écart : `WF-INTF-0100-A` — « Chaque ligne se retrouve sous la tâche désignée, avec sa quantité, ses heures ou son débours, son rôle et, le cas échéant, son sous-projet. » : idem.
- écart : `WF-INTF-0100-A` — « Un fichier exporté, dont une charge a été modifiée, réimporté sur un projet qui porte une révision de référence sans être encore En cours met à jour cette ligne sans changer son montant budgété ni sa lignée. » : idem.
- écart : `WF-INTF-0100-A` — « Une ligne qui cite une tâche, un rôle ou un sous-projet inconnu, ou qui laisserait une tâche sans aucune heure travaillée dans la semaine (WF-PLA-0010), est rejetée et figure au compte rendu (WF-INTF-0080). » : idem.
- écart : `WF-INTF-0100-A` — « Une ligne d'une tâche démarrée dont le sous-projet a reçu des coûts réels, que le fichier place sous un autre sous-projet ou laisse sans sous-projet, est rejetée, et le compte rendu nomme ce sous-projet. » : idem.
- écart : `WF-INTF-0100-A` — « Un devis exporté d'une révision marquée puis réimporté dans la révision en cours met à jour les lignes de même lignée sans en créer aucune. » : idem.
- écart : `WF-INTF-0100-A` — « Un fichier d'où une ligne de provision a été retirée laisse cette ligne en place ; une ligne de catégorie de provision sans identifiant est rejetée au compte rendu. » : constaté par EP-08 (US-2580), inchangé.
- écart : `WF-INTF-0100-A` — « Sur un projet En cours, l'import d'un devis sur la structure principale est refusé et nomme la condition ; sur une structure différentielle, il aboutit. » : constaté par EP-07 et EP-08, inchangé.
- écart : `WF-INTF-0100-A` — « Un fichier qui recopie une ligne avec sa lignée voit les deux lignes rejetées, et la ligne existante inchangée. » : constaté par EP-07, inchangé.

**Notes de réalisation.** La proposition de #4422 fait foi : les lignes retirées entrent dans
l'écriture de `write_lines`, un seul rejeu. Décision de l'auteur du 2026-11-21 : corriger sans mesure
préalable ; ni test de durée ni mesure aux volumes dans ce lot — EP-13 (US-2970) et EP-40 mesurent.

**Hors périmètre.** La suppression d'un nœud par la grille (`deleteNode`), inchangée.

---

## US-3230 — L'import du reste à engager termine une tâche selon la spécification 1.0.7, et annonce le montant qu'il écrit

- **statut** : fini
- **exigences** : `WF-INTF-0120-A`
- **opérations** : `openImport`, `getImport`, `applyImport`
- **issue** : #4535

**En tant que** chef de projet, **je veux** qu'une tâche ne soit terminée par l'import que si aucune
de ses lignes ne garde de reste, celles que le fichier ne porte pas comprises, et que le compte rendu
me dise le montant qui sera écrit quand il n'est pas celui que j'ai saisi, **afin de** ne pas clore
une tâche qui a encore du reste, et de ne pas découvrir l'arrondi dans la grille (#3978, #4428).

**Critères d'acceptation.**

- `WF-INTF-0120-A` — « Une tâche démarrée dont toutes les lignes, celles absentes du fichier comprises, sont à zéro après l'import, et dont le fichier en met au moins une à zéro, est terminée à la date de la revue ; une tâche non démarrée dont les lignes sont laissées telles quelles reste non réestimée. » : éprouvé
  contre le service sur une tâche démarrée de deux lignes : une seule au fichier, mise à zéro,
  l'autre gardant un reste — la tâche n'est pas terminée, et le compte rendu ne la nomme pas ; la
  ligne absente déjà à zéro, l'autre mise à zéro par le fichier — la tâche est terminée à la date de
  la revue ; les deux déjà à zéro et laissées telles quelles — elle n'est pas terminée par l'import.
  Le livré d'EP-09 est corrigé s'il suivait l'ancienne phrase (« toutes les lignes du fichier »).
- propre à l'US : une ligne hors main-d'œuvre dont le montant que l'import écrira — le débours
  unitaire arrondi au centime, la quantité et le coefficient conservés — diffère du montant saisi
  est signalée au compte rendu, les deux montants donnés : 1 234,56 saisis sur une quantité de 1 000
  annoncent 1 230,00. Une ligne dont le montant se divise juste n'est pas signalée. La règle de
  calcul d'EP-09 ne change pas.
- écart : `WF-INTF-0120-A` — « Même critère que WF-INTF-0100, appliqué aux grandeurs réestimées ; les montants budgétés et les lignées de toutes les lignes sont inchangés après l'import, et une ligne absente du fichier conserve son reste à engager. » : constaté par EP-09, inchangé.
- écart : `WF-INTF-0120-A` — « Un reste à engager exporté d'une révision marquée puis réimporté dans la révision en cours met à jour les lignes de même lignée sans en créer aucune. » : idem.
- écart : `WF-INTF-0120-A` — « Avec huit heures par jour, une ligne de main-d'œuvre dont le fichier porte trois jours a un reste de vingt-quatre heures. » : idem.
- écart : `WF-INTF-0120-A` — « Un fichier qui recopie une ligne avec sa lignée voit les deux lignes rejetées, et la ligne existante inchangée. » : idem.
- écart : `WF-INTF-0120-A` — « Un fichier sans date de revue applique les lignes qui ne terminent aucune tâche et rejette celles qui en termineraient une. » : idem ; le rejet ne vise que les lignes
  dont la mise à zéro terminerait leur tâche selon la règle ci-dessus.
- écart : `WF-INTF-0120-A` — « Une cellule de reste effacée sur une ligne connue la met à zéro. » : constaté par EP-09 ; US-3200 en écarte la colonne absente.
- écart : `WF-INTF-0120-A` — « Un onglet renommé dans Excel garde son sous-projet. » : US-3270.

**Notes de réalisation.** #3978, confronté au livré le 2026-11-21 (`epic/EP-08`,
`core/estimate/remaining/analysing.py`, `_close`) : le service suit déjà la règle de la 1.0.7 — une
tâche n'est terminée que si le fichier met à zéro une ligne qu'elle porte déjà, et si aucune de ses
lignes, écrite ou laissée, ne garde de reste, hors lignes de provision (WF-RAE-0040). Il manque la
preuve : aucun test ne porte une ligne absente du fichier qui garde un reste, ni une tâche aux
lignes déjà à zéro laissées telles quelles, et le test de la terminaison cite encore l'ancienne
phrase du Vérif. L'US ajoute ces tests et corrige la citation ; aucune correction du service n'est
attendue. Pour #4428, décision de l'auteur du 2026-11-21 : dire l'écart au compte rendu, la forme du signal
étant de la conception. Écartés : ramener la quantité à 1, que la Conception d'EP-09 a déjà écartée ;
ne corriger que la phrase. La phrase de la décision #2797 dans le fichier d'EP-09 (« Le débours d'une
tâche à cheval sur deux années rend le montant saisi ») est corrigée par la pull request de ce
cadrage.

**Hors périmètre.** L'export du reste à engager d'une révision marquée au taux du jour (BCH-08,
#4441, EP-35).

---

## US-3240 — Déposer un fichier demande une permission d'import, et un compte ne garde pas plus de vingt dépôts en attente

- **statut** : fini
- **exigences** : `WF-ADM-0020-A`, `WF-DAT-0120-A`
- **opérations** : `uploadFile`
- **issue** : #4536

**En tant qu'** administrateur, **je veux** que seul un compte habilité à importer puisse déposer un
fichier, et qu'il ne puisse pas en accumuler sans fin, **afin qu'** un compte en lecture seule ne
remplisse pas le stockage objet, qui porte aussi les sauvegardes (#4423).

**Critères d'acceptation.**

- `WF-ADM-0020-A` — « Réciproquement, un rôle privé d'une permission empêche l'action correspondante, quel que soit l'acteur auquel l'utilisateur ressemble. » : un
  compte qui ne porte aucune des permissions d'import — `planning.write`, `estimate.write`,
  `remaining.write`, `actual_costs.write` — reçoit de `uploadFile` 403 `PERMISSION_MISSING`, et rien
  n'est écrit au stockage ni dans la base ; l'une d'elles suffit, et le contrat déclare le 403.
- `WF-DAT-0120-A` — « Un fichier déposé et jamais confirmé disparaît au terme du délai d'expiration. » : sa
  forme pour le plafond : un compte garde au plus vingt dépôts d'import qu'aucun import n'a
  employés ; le vingt et unième est refusé par un motif nommé, que le contrat déclare, et rien n'est
  écrit au stockage. Dès qu'un import en emploie un, ou que la purge en retire un à son échéance, un
  nouveau dépôt passe. L'expiration elle-même est constatée par EP-06, inchangée.
- propre à l'US (BEX-08, #4426) : un nom de fichier qui porte un octet NUL est refusé par
  `uploadFile`, 422 `VALIDATION_FAILED` désignant `/file`, et rien n'est écrit au stockage ni dans
  la base.
- propre à l'US : les formulaires d'import du front disent ces deux refus dans les mots du
  catalogue, sans page d'erreur.
- écart : `WF-ADM-0020-A` — « Un rôle d'habilitation composé sur mesure permet à un utilisateur de cumuler des permissions relevant de deux acteurs différents. » : constaté par EP-03 et EP-05, inchangé.
- écart : `WF-DAT-0120-A` — « Après application ou abandon d'un import, le fichier correspondant n'est plus sur le stockage objet. » : constaté par EP-06, inchangé.
- écart : `WF-DAT-0120-A` — « Un export téléchargé jusqu'au bout n'est plus sur le stockage objet ; un téléchargement interrompu le laisse disponible ; un export jamais téléchargé en disparaît au terme de vingt-quatre heures. » : idem.

**Notes de réalisation.** Décision de l'auteur du 2026-11-21 : la permission et un plafond de vingt
dépôts en attente par compte (200 Mio). Écarté : la permission seule, qui laisse la boucle à un
compte habilité. La forme du refus du plafond (son code et son statut) est de la conception. Le
plafond se juge avant l'écriture au stockage, que la route fait aujourd'hui avant d'enregistrer le
dépôt.

**Hors périmètre.** Le dépôt par morceaux d'une sauvegarde, déjà sous `platform_restore` ; la
qualité de contributeur, que `openImport` juge sur son projet.

---

## US-3250 — Les comptes rendus d'import : supprimés à l'échéance et à l'abandon, listés sans leur contenu, lisibles sans leur tâche

- **statut** : fini
- **exigences** : `WF-DAT-0080-A`, `WF-ARC-0100-A`
- **opérations** : `listImports`, `getImport`, `abandonImport`
- **issue** : #4524

**En tant qu'** exploitant, **je veux** qu'un compte rendu d'import expiré ou abandonné disparaisse
de la base, et qu'un import ancien se lise encore quand sa tâche de fond a été purgée, **afin que**
la table des imports ne croisse pas sans fin et qu'aucun import de plus de trente jours ne réponde
500 (#4425).

**Critères d'acceptation.**

- `WF-DAT-0080-A` — « Une tâche de fond terminée depuis plus que la rétention de son résultat n'est plus dans la base ; un compte rendu d'import et un plan de collage expirés non plus. » : la
  passe de purge supprime la ligne d'un import `expired` et celle d'un import `abandoned`, compte
  rendu compris ; un import `applied`, `failed` ou `refused` reste. `getImport` d'un import dont la
  tâche de fond a été purgée, ou qui n'en a jamais eu — ceux du témoin —, répond 200, `task` nul,
  jamais 500. Le plan de collage et la tâche de fond sont constatés par EP-06 et EP-13, inchangés.
- `WF-ARC-0100-A` — « Un compte rendu expiré ne peut plus être appliqué, et son fichier n'est plus sur le stockage objet. » : jusqu'à
  la passe de purge, l'import se lit `expired`, `applyImport` le refuse et l'abandon répond 204,
  comme aujourd'hui ; après elle, `getImport`, `applyImport` et `abandonImport` répondent 404, et
  `listImports` ne le liste ni ne le compte. De même pour un import abandonné.
- propre à l'US : `listImports` ne lit pas le compte rendu des lignes qu'il liste, et la purge ne
  relit ni ne verrouille les exports déjà consommés.
- propre à l'US : le contrat, ses exemples et le témoin suivent : `ImportDetail.task` nullable, les
  listes d'exemple sans import que la purge aurait supprimé, le témoin sans import `expired` gardé
  au-delà de sa purge ; l'écran des imports lit un import sans tâche sans la suivre.
- propre à l'US : la docstring de la table et le commentaire de la migration des clés d'EP-08 disent
  ce que la purge fait.
- écart : `WF-DAT-0080-A` — « La suppression d'un sous-projet non référencé le retire de la base. » : constaté par EP-04, inchangé.
- écart : `WF-DAT-0080-A` — « Celle d'un sous-projet que portent des lignes de devis de la révision en cours est refusée et nomme ces lignes ; elle aboutit une fois ces lignes passées hors sous-projet ou à un autre sous-projet. » : constaté par EP-07, inchangé.
- écart : `WF-DAT-0080-A` — « Celle d'un sous-projet référencé par une révision marquée est refusée, et le sous-projet reste proposé à la saisie. » : constaté par EP-04, inchangé.
- écart : `WF-DAT-0080-A` — « Celle d'un poste référencé par une révision marquée le marque supprimé : la révision l'affiche toujours, la saisie ne le propose plus. » : idem.
- écart : `WF-DAT-0080-A` — « Aucune commande ne supprime physiquement un rôle de ressource, un rôle d'habilitation ou un compte. » : constaté par EP-03 et EP-05, inchangé.
- écart : `WF-ARC-0100-A` — « Entre l'analyse et la confirmation, aucune donnée du projet n'a changé. » : US-3210.
- écart : `WF-ARC-0100-A` — « L'interruption de l'application laisse le projet dans son état antérieur. » : constaté par EP-06, inchangé.
- écart : `WF-ARC-0100-A` — « Un import confirmé par un utilisateur dont la permission est retirée avant l'exécution n'est pas appliqué, le refus nomme la condition manquante et son fichier n'est plus sur le stockage objet. » : idem ; l'import
  `refused` reste au journal des imports.
- écart : `WF-ARC-0100-A` — « Il en va de même si le projet est passé dans un état terminal entre-temps. » : idem.
- écart : `WF-ARC-0100-A` — « Une application refusée parce qu'un marquage est en cours sur le projet peut être redemandée après lui, sans nouveau dépôt. » : constaté par EP-08 (US-2660), inchangé.
- écart : `WF-ARC-0100-A` — « Après l'abandon d'un différentiel sur lequel un import a été analysé, cet import ne peut plus être appliqué, et son fichier n'est plus sur le stockage objet au terme du délai d'expiration. » : constaté par EP-08 (US-3060), dont la cascade emporte déjà le compte rendu.

**Notes de réalisation.** Décisions de l'auteur du 2026-11-21 : la spécification mène (§4.4.1,
WF-DAT-0080) et le contrat suit ; la ligne part à la passe de purge, non à l'abandon même, si bien
que l'idempotence de l'abandon (décision #1789) tient jusqu'à elle ; les échoués et les refusés sont
gardés comme les appliqués, que `cost_import` cite et que le journal nomme. Écartés : vider la seule
colonne `report`, qui amendait la spécification ; supprimer après la rétention des tâches de fond.
À livrer avant la fusion d'EP-13, dont la purge supprime les tâches de trente jours.

**Hors périmètre.** La purge des tâches de fond elle-même (EP-13, US-2830) ; le dépôt qu'une
restauration désigne (#4471, EP-39) ; le fichier d'un import emporté par une cascade (#4331, EP-08).

---

## US-3260 — Une panne passagère du stockage laisse l'import à reprendre, au lieu de le faire échouer pour de bon

- **statut** : fini
- **exigences** : `WF-EXP-0040-A`
- **opérations** : `openImport`, `applyImport`, `getImport`
- **issue** : #4537

**En tant que** chef de projet, **je veux** qu'une coupure de quelques secondes du stockage objet
pendant l'analyse ou l'application de mon import ne le fasse pas échouer, **afin de** ne pas perdre
un import confirmé, fichier supprimé, pour une panne que les tentatives de la tâche savent attendre
(#4427).

**Critères d'acceptation.**

- `WF-EXP-0040-A` — « Aucune donnée partiellement écrite ne subsiste après le rétablissement d'un composant tombé en cours d'écriture. » : sa
  forme pour le fichier d'un import : quand la lecture du fichier rencontre une indisponibilité du
  stockage — à l'ouverture du flux ou en cours de flux —, pendant l'analyse ou l'application,
  l'import reste là où il en était, son fichier en place, rien n'est écrit, et la tâche est reprise
  par ses tentatives : le stockage rétabli, l'import aboutit sans nouveau dépôt.
- propre à l'US : l'import n'échoue, son fichier supprimé, que si le fichier n'est plus sur le
  stockage, si le format le refuse, ou si le format casse ; les tentatives de la tâche épuisées
  pendant la panne, l'import se lit `failed` et le motif nomme le composant.
- écart : `WF-EXP-0040-A` — « Pendant l'arrêt du stockage objet, une demande d'import est refusée en nommant le composant, et la consultation comme la saisie continuent. » : constaté par EP-09, et EP-13
  (US-2860) clôt.
- écart : `WF-EXP-0040-A` — « Pendant l'arrêt du worker, un marquage demandé aboutit après le rétablissement, sans nouvelle demande. » : EP-13.

**Notes de réalisation.** La proposition de #4427 fait foi. EP-13 (US-2860/L1, #4090) réécrit
`platform/storage.py` : ce que l'US demande à la lecture en flux se décide dans la conception contre
la branche d'EP-13, pour ne pas toucher le même fichier.

**Hors périmètre.** Le mode dégradé du dépôt et de l'export (EP-13, US-2860).

---

## US-3270 — L'élément d'OTP d'une ligne de coût se compare en entier, et le code d'un sous-projet est libre

- **statut** : à faire
- **exigences** : `WF-CRE-0020-A`, `WF-PRJ-0050-A`
- **opérations** : `openImport`, `getImport`, `applyImport`, `createProject`, `updateProject`,
  `createSubproject`, `updateSubproject`, `listSubprojects`, `listActualCosts`, `requestExport`
- **issue** : #4538

**En tant que** chef de projet, **je veux** nommer mes sous-projets comme mon ERP les nomme, et que
chaque ligne de coût s'impute par son élément d'OTP comparé en entier au code du projet et à ceux de
ses sous-projets, **afin qu'** une extraction trop large ne pollue pas mon projet et que le compte
rendu me dise quels sous-projets déclarer avant de réimporter (#3966, spécification 1.0.7).

**Critères d'acceptation.**

- `WF-CRE-0020-A` — « Sur le projet de code A.ABC.26001, qui porte le sous-projet de code A.ABC.26001/10001, une ligne d'élément A.ABC.26001 est importée et imputée au seul projet, et une ligne d'élément A.ABC.26001/10001 est imputée à ce sous-projet. »
- `WF-CRE-0020-A` — « Une ligne d'élément A.ABC.26001/10002, une ligne d'élément 10001, une ligne d'élément A.ABC.26002 et une ligne d'élément vide sont rejetées, et le compte rendu nomme chacun de ces éléments et le nombre de ses lignes. »
- `WF-CRE-0020-A` — « Après création du sous-projet de code A.ABC.26001/10002, le réimport du même fichier lui impute ses lignes. » : la
  création d'un sous-projet n'impute plus rien d'elle-même : seul le réimport impute.
- `WF-CRE-0020-A` — « Une ligne réimportée avec un autre élément d'OTP change d'imputation. »
- `WF-PRJ-0050-A` — « La création de deux sous-projets de même code dans un même projet est refusée. » : inchangé,
  le code comparé en entier.
- `WF-PRJ-0050-A` — « Un sous-projet de code « A.ABC.26001/10001 », « Synthèse » ou de quarante caractères se crée, et le fichier de reste à engager lui donne un onglet qui porte son code en tête. » : l'onglet
  porte un nom tiré du code — les caractères qu'Excel refuse remplacés, coupé à 31 caractères,
  numéroté en cas de collision — et le code en tête ; l'import désigne le sous-projet par ce code,
  jamais par le nom de l'onglet, si bien qu'un onglet renommé dans Excel garde son sous-projet
  (WF-INTF-0120).
- `WF-PRJ-0050-A` — « La création d'un sous-projet dont le code est celui du projet est refusée. » : de
  même son recodage, et le recodage d'un projet vers le code de l'un de ses sous-projets.
- propre à l'US : le code d'un projet peut porter une barre oblique : `PROJECT_CODE_INVALID` tombe.
- propre à l'US (BRC-04) : dans une extraction, seules les lignes dont l'élément d'OTP est le code
  du projet importé ou de l'un de ses sous-projets se comparent entre elles pour `DUPLICATE_COST_LINE` ;
  une ligne d'un autre élément est rejetée pour son élément et ne fait rejeter aucune ligne du
  projet. Le motif de confirmation de la décision #2724 reste.
- propre à l'US : la reprise. Une migration préfixe les codes de sous-projets déjà saisis du code de
  leur projet et d'une barre oblique : chaque ligne de coût imputée à un sous-projet le reste, et le
  réimport de son extraction l'impute au même. Les lignes de coût importées sous un code de
  sous-projet inconnu, qui attendaient sa création, sont supprimées par la migration (décision de
  l'auteur du 2026-11-21) : la règle nouvelle les aurait rejetées, et le réimport les rend une fois
  le sous-projet déclaré.
- propre à l'US : les formulaires du projet et du sous-projet du front, leurs messages, le témoin et
  les exemples du contrat suivent ; les exemples de WF-CRE-0020-A et de WF-PRJ-0050-A à barre oblique
  entrent au harnais des exemples (#4022).
- propre à l'US (BPR-09) : `api/subprojects.py` ne lit plus de borne dans la table privée du module
  des projets.
- écart : `WF-PRJ-0050-A` — « Un projet se chiffre sans aucun sous-projet. » : constaté par EP-04, inchangé.
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet portant des coûts réels est refusée. » : constaté par EP-09, inchangé.
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet cité par une révision marquée est refusée. » : constaté par EP-04, inchangé.
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet que porte une ligne de devis de la révision en cours est refusée ; elle aboutit une fois cette ligne passée à un autre sous-projet. » : constaté par EP-07, inchangé.
- écart : `WF-PRJ-0050-A` — « Le passage à un autre sous-projet d'une ligne d'une tâche démarrée, dont le sous-projet a reçu des coûts réels, est refusé et nomme ce sous-projet ; celui d'une ligne d'une tâche non démarrée aboutit, comme celui de la ligne de provision d'un risque identifié. » : constaté par EP-07 et EP-08, inchangé.

**Notes de réalisation.** #3966 fait foi, avec la décision « Le tri des constats de spécification »
de `docs/api/DECISIONS.md` (#3370) : le contrat d'abord, puis le service (`core/costs/extraction.py`
sans `partition`, le compte rendu, l'export et l'import du reste à engager), la migration, le front.
Les Vérif de la 1.0.7 sont les critères. La suppression des lignes en attente révise ce que #3966
laissait « à dire » ; écartés : les garder imputées au seul projet, ou garder pour elles l'imputation
à la création. La migration touche des données saisies : elle dit ce qu'elle supprime dans son
journal, par projet.

**Hors périmètre.** L'export du devis selon l'annexe B (#4399, EP-31) ; les noms d'onglet du devis
(#3371), que le nom tiré du code règle pour le reste à engager.

---

## US-3280 — L'écran des imports : l'application échouée ou refusée, le formulaire pendant un envoi, la zone de dépôt, un long compte rendu

- **statut** : à faire
- **exigences** : `WF-IHM-0080-A`, `WF-INTF-0080-A`
- **opérations** : `uploadFile`, `openImport`, `getImport`, `listImports`, `applyImport`,
  `abandonImport`, `setImportDurationRule`
- **issue** : #4544

**En tant que** chef de projet, **je veux** que l'écran des imports ne m'offre que ce que le service
acceptera, me montre l'état réel d'un import après un refus, garde le formulaire que je remplis
pendant qu'un autre envoi aboutit, et reste lisible devant un compte rendu de milliers de lignes,
**afin de** ne pas répéter un geste voué au refus ni perdre une saisie (#4424, #4429, FCO-06 de
#4425).

**Critères d'acceptation.**

- `WF-IHM-0080-A` — « L'échec d'un traitement de fond est signalé avec son motif, et le même traitement peut être relancé. » : sa
  forme pour l'application d'un import, qui ne se relance pas — un import `failed` a son fichier
  supprimé, et `applyImport` le refuse toujours : le suivi des tâches signale l'échec avec son motif,
  n'offre pas « Relancer », et dit de repartir de l'écran (`tasks.relaunchFromScreen`). Un export
  échoué se relance toujours.
- propre à l'US (FCO-04) : un refus de `applyImport` par 409 relit l'écran : après un refus
  définitif, l'import se lit « Refusé », son explication paraît, et ni « Appliquer » ni le choix de
  la règle des durées ne restent offerts — la condition d'US-3210 comprise.
- propre à l'US (FCO-03, FCO-14) : tant que l'envoi d'un fichier est en route, les commandes des
  autres natures sont inactives et le bouton « Analyser » dit l'attente ; la réponse d'un dépôt ne
  ferme que le formulaire qui l'a envoyé. Pendant la requête qui change la règle des durées, le
  bouton radio montre la règle choisie.
- `WF-INTF-0080-A` — « Si l'utilisateur abandonne à cette étape, le projet reste inchangé. » : sa
  forme pour la zone de dépôt du démarrage d'un projet (FCO-05) : quand l'adresse ne nomme plus
  l'import envoyé — abandonné, ou refusé par son compte rendu —, la zone reprend un nouveau fichier,
  et ne dit plus que le précédent « est envoyé ».
- propre à l'US (FCO-06) : chaque tableau d'un compte rendu — écarts, rejets — rend ses 200
  premières rangées, dit combien il en reste, et offre de tout afficher ; le compte se fait sur le
  compte rendu reçu, sans changement du contrat.
- propre à l'US : une adresse qui nomme un import que la purge a supprimé (US-3250) mène à la liste
  des imports, qui le dit, sans page d'erreur.
- écart : `WF-IHM-0080-A` — « Le marquage d'une révision de dix mille objets laisse l'écran utilisable et présente son avancement. » : constaté par EP-02 et EP-04, inchangé.
- écart : `WF-IHM-0080-A` — « Un utilisateur qui change d'écran pendant un import est informé de son aboutissement. » : constaté par EP-09 et EP-25 (US-2170), inchangé.
- écart : `WF-INTF-0080-A` — « Pour un fichier qui contient des lignes invalides, le compte rendu les liste avec leur motif avant la confirmation. » : constaté par EP-06 et EP-07 ; le rendu borné
  ci-dessus les liste toutes à la demande.
- écart : `WF-INTF-0080-A` — « Si l'import est interrompu pendant son application, le projet revient à son état antérieur. » : le service, constaté par EP-06, inchangé.
- écart : `WF-INTF-0080-A` — « Pour un planning MS Project saisi sur un autre calendrier, le compte rendu propose de garder les durées ou les dates ; changer d'option rend un nouveau compte rendu, et le projet reste inchangé jusqu'à la confirmation. » : constaté par EP-24 (US-2000), inchangé ; seul
  le bouton radio pendant la requête change.

**Notes de réalisation.** Les propositions de #4424 et de #4429 font foi : ne pas remettre la
commande de l'application au suivi ; relire sur `conflict` comme `DurationRule` le fait ; tenir les
commandes de nature inactives pendant un envoi, comme `OpensForm` des risques ; libérer la zone
quand l'adresse ne nomme plus l'import. Pour FCO-06, décision de l'auteur du 2026-11-21 : la borne
est dans l'écran seul ; écartés : paginer le compte rendu au contrat, reporter à EP-40. Les tests
vont dans `exchanges.dom.test.tsx` et `project-start.dom.test.tsx`.

**Hors périmètre.** Les messages des refus nouveaux du contrat, que leur US ajoute au catalogue
(US-3200, US-3210, US-3240) ; la refonte des écrans (EP-37).

---

## US-3640 — Le devis et le reste à engager exportés s'affichent justes sans recalcul, et le devis ne porte de colonne d'heures que pour les codes de ses rôles

- **statut** : à faire
- **exigences** : `WF-INTF-0110-A`, `WF-INTF-0130-A`
- **opérations** : `requestExport`
- **issue** : #4730

**En tant que** chef de projet, **je veux** que le classeur du devis ou du reste à engager que
j'exporte montre ses montants et ses totaux dès son ouverture, dans un tableur qui ne recalcule pas
ou dans un aperçu, et que l'onglet « Devis » ne porte une colonne d'heures que pour un code que l'un
de mes rôles peut remplir, **afin de** diffuser le fichier sans qu'il se lise à zéro, et de ne pas
chercher mes heures parmi cent cinquante colonnes vides (#4317, #4319).

**Critères d'acceptation.**

- propre à l'US (#4317) : relu sans recalcul (`openpyxl`, `data_only=True`), chaque cellule calculée
  d'une ligne exportée du devis — Nature, Code comptable, Service, Taux horaire, Type, Heures
  totales, Main-d'œuvre, Débours, Montant, Description de la tâche — porte la valeur que sa formule
  rend, chaque « Montant » égal au « Montant Waterfall » ; une ligne préparée vide porte la valeur
  vide que sa formule rend, non 0 ; la ligne de totaux de chaque onglet, les onglets « Devis » et
  « Présentation » portent les leurs. Les formules restent : le classeur modifié dans un tableur se
  recalcule.
- propre à l'US (#4317) : le classeur du reste à engager, relu de même, porte la valeur de chacune de
  ses cellules calculées et de ses totaux.
- propre à l'US (#4319) : l'onglet « Devis » porte une colonne « Heures <code> » par code comptable
  des rôles de « Paramètres », dans l'ordre des codes, et aucune pour un code qu'aucun rôle ne
  porte : un référentiel de cinq rôles sur deux codes et de cent cinquante catégories de
  main-d'œuvre donne deux colonnes. La « Synthèse » du reste à engager, qui ventile ses jours par
  code comptable, suit le même domaine si elle a le même défaut.
- écart : `WF-INTF-0110-A` — « On exporte un devis, puis on le réimporte sans modification dans la révision en cours. Le compte rendu (WF-INTF-0080) ne signale aucun écart, et les lignes obtenues sont identiques. » : constaté par EP-07 ; le test d'aller-retour
  existant reste au vert avec les valeurs écrites et les colonnes réduites.
- écart : `WF-INTF-0130-A` — « Même critère d'aller-retour que WF-INTF-0110. » : constaté par EP-09 ; idem.

**Notes de réalisation.** Les propositions de #4317 et de #4319, retenues par l'utilisateur le
2026-11-20, font foi : écrire avec chaque formule la valeur que Waterfall connaît déjà
(`write_formula` avec sa valeur, `total_value` à côté de `total_function`), dans
`core/estimate/excel/writer.py` et `core/estimate/remaining/excel/writer.py` ; prendre pour domaine
des colonnes d'heures les codes comptables des rôles (`_summary_columns`). Écarté : forcer le
recalcul au chargement, que LibreOffice, Excel en mode protégé et les aperçus ignorent.

**Hors périmètre.** La refonte de l'export selon l'annexe B de la spécification 1.0.8 — « Devis »
allégé, onglet « Heures », heures dans « Présentation » (#4399, EP-31), sous laquelle le même domaine
des rôles fonde les lignes de l'onglet « Heures ».
