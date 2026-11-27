# Guide de développement

> Ce document est la version française de référence ; [README.md](README.md) en est la traduction
> anglaise.

Ce guide fixe ce qui doit se ressembler d'un lot à l'autre, qu'une personne ou un agent
l'ait écrit : où chaque chose vit, comment elle se nomme, et la forme des pièces qui se
répètent. Il ne recopie ni la spécification (`docs/spec`), ni le contrat (`docs/api`), ni
[CONTRIBUTING](../../CONTRIBUTING.md), ni la [roadmap](../roadmap/README-fr.md) : il y renvoie.

Chaque règle qu'un outil peut contrôler l'est, et la règle nomme son contrôle ; une règle
que rien ne contrôle le dit. Le guide s'écrit en même temps que le socle (EP-01) : chaque US
y ajoute la section qu'elle établit, et une section encore vide nomme celle qui l'écrira.

## Arborescence

| Chemin                                     | Contenu                                                                                                                                                                                                       | PBS     |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `backend/`                                 | un seul projet Python, un seul paquet `waterfall` : le noyau (`core/`, un sous-paquet par module, calqué sur un bloc FBS), le service d'API (`api/`), le worker (`worker/`) ; les tests dans `backend/tests/` ; à côté du paquet, `backend/measure/`, la mesure du cœur (`make measure-core`), hors de l'image et de la couverture | PBS-2   |
| `frontend/`                                | l'application Next.js ; le client engendré dans `frontend/src/api/` ; les parcours de bout en bout dans `frontend/e2e/`                                                                                       | PBS-1   |
| `fixtures/`                                | le relevé engendré des exemples chiffrés des Vérif, et les fixtures qui s'y rattachent                                                                                                                        | —       |
| `tools/`                                   | les outils du dépôt, un seul paquet Python, `wftools`, et leurs tests                                                                                                                                         | PBS-5.2 |
| `deploy/compose/`, `deploy/helm/`          | l'empaquetage : Compose, puis le chart Helm en EP-13                                                                                                                                                          | PBS-5.1 |
| `deploy/keycloak/`                         | l'image de Keycloak : l'extension Java (`extension/`), les thèmes, le royaume `waterfall` (`realm/`), et ce que la plateforme de développement lui ajoute (`development/`)                                    | PBS-5.4 |
| `.github/workflows/`                       | la chaîne                                                                                                                                                                                                     | PBS-5.2 |
| `docs/spec/`, `docs/api/`, `docs/roadmap/` | la spécification, le contrat, la roadmap                                                                                                                                                                      | —       |
| `docs/dev/`                                | ce guide, et les règles de codage par langage                                                                                                                                                                 | —       |
| `LICENSES/`, `REUSE.toml`                  | les textes des licences, et la licence des fichiers qui ne portent pas d'en-tête                                                                                                                              | —       |
| `docs/legal/`                              | l'accord de licence de contribution, et les engagements envers l'édition communautaire                                                                                                                        | —       |

Un répertoire naît avec le lot qui y met le premier fichier : `backend/`, `frontend/`,
`fixtures/` et `deploy/` n'existent pas encore tous. La conception d'EP-01 dit pourquoi
chaque chose est là (`docs/roadmap/EP-01-socle-de-developpement.md`, « Conception »).

## Le back et les frontières du noyau

Le back est un seul paquet, `waterfall`, et deux processus : `waterfall-api` et
`waterfall-worker`, deux points d'entrée d'une même distribution. Ils portent donc la même
version par construction, celle de `backend/pyproject.toml` (WF-ARC-0010).
Une troisième commande de la même distribution, `waterfall-migrate`, applique les migrations de
la base (voir « Migrations ») et s'arrête : ce n'est pas un processus du service, mais elle
porte la même version et se lance avec la même image.
Une quatrième, `waterfall-restore`, est le service de la restauration (US-0440, #953) : seul
lecteur du flux des restaurations, seul à tenir les propriétaires des deux bases, il applique les
migrations comme l'amorçage, et son module, `waterfall.restore`, est comme lui au sommet des
couches, importé par aucun.

Un verbe de `waterfall-api`, `load-witness` (EP-05), charge le témoin : l'univers que décrivent les
exemples du contrat, `fixtures/api/`, que `make mock-data` tient et que le faux back sert. Il lit
`WATERFALL_DATABASE_URL`, le rôle du service — il écrit par les interfaces des modules, avec les
identifiants du témoin, la plateforme pour auteur et l'instant du chargement pour date —, et
`WATERFALL_WITNESS_PATH`, le répertoire de la description ; un réglage absent, ou un chemin qui
n'est pas un répertoire, l'arrête au départ en le nommant (2). Chaque fichier se lit dans la forme
du contrat, par ses modèles (`api/contract/models.py`) : un fichier qui s'en écarte l'arrête. Il
écrit en une transaction, sous un verrou consultatif qui lui est propre, une tranche par objet,
dans l'ordre de leurs dépendances (`waterfall.witness.loader`) : les paramètres communs, les unités
de durée, les natures, les catégories, les taux, les calendriers (`calendars_with_inactive.json` :
tous créés, puis ceux que le témoin dit désactivés désactivés) et le calendrier par défaut, les
nœuds puis la désactivation de ceux que le témoin dit désactivés, les rôles puis la leur, la
correspondance de l'extraction des coûts réels ; puis, par une seule entrée
(`waterfall.witness.chronology`), la tranche des projets (EP-04) : les projets et les comptes locaux
de leurs contributeurs, les contributeurs, les sous-projets, le lotissement, les révisions et les
événements de la chronologie du témoin, aux instants qu'elle impose — chaque révision ouverte par
les règles de l'ouverture, marquée par la transaction même du worker (`load_marking`), sous le nom
de version et la description de `revisions.json`, que la chronologie ne fait qu'ordonner.
Après eux, la tranche du portefeuille (EP-11, `waterfall.witness.portfolio`) : les dix projets de
`fixtures/witness/portfolio/projects/`, lus à côté du répertoire de la description
(`../witness/portfolio`), écrits un à un par les interfaces des modules aux instants qu'ils datent —
création, révisions ouvertes et marquées, risques et réexamens, imports de coûts réels, désignation
de la référence, sorties —, le chef de projet du témoin pour contributeur de chacun, les
identifiants du témoin imposés et les autres dérivés d'eux. Une tranche n'écrit rien de ce que la
plateforme tient déjà : relancé, il n'écrit rien et réussit, en disant le témoin là
(`witness.already_loaded`) ; un refus ou une erreur n'écrit rien et l'arrête en échec (1). Chaque US
du référentiel et des projets remplit sa tranche, dans son fichier de `waterfall.witness`, sans
toucher l'ordre. Son module,
`waterfall.witness`, est au sommet des couches, importé par aucun : `waterfall-api` commence par
lui, qui passe à l'amorçage tout autre argument. Le Compose de service l'offre (service `witness`,
`make service-witness`), celui de production non : une installation réelle ne porte pas le témoin.
`make service-witness` ne prend aucune variable propre : le Compose de service passe au service
`witness` le rôle du service (`WATERFALL_DATABASE_URL`, par `WATERFALL_POSTGRES_PASSWORD`, qu'il
faut exporter comme pour `make service-up`) et monte `fixtures/api/` et `fixtures/witness/` en
lecture seule, `WATERFALL_WITNESS_PATH` étant `/fixtures/api` : la tranche du portefeuille (`fixtures/witness/portfolio/`) se lit à côté des
exemples ; la plateforme doit être démarrée et amorcée
(`make service-install`), car la commande n'écrit pas ce que l'amorçage écrit — la ligne de
l'installation, les paramètres communs, les unités, la correspondance, le calendrier par défaut
et la provision —, elle règle ce qu'il a posé. Les tests font de même, une fois par exécution, sur
une base modèle (`backend/tests/witness_template.py`) : ils installent d'abord ce que l'amorçage
écrit, puis lancent la commande ; la fixture `witness` donne à chaque test une copie de cette base.
`backend/tests/test_witness.py` éprouve le témoin entier : ses volumes, deux plateformes
neuves chargées identiques, une seconde exécution qui n'écrit rien, les dates et les auteurs de la
plateforme, l'arrêt en le disant sur un témoin que les règles refusent, et les listes du service
comparées aux exemples du contrat, aux colonnes d'audit près. `fixtures/api/` et Prism restent les
exemples du contrat et le faux back des écrans que le service ne sert pas.

**Le jeu de référence (EP-13, US-2950).** `waterfall-api load-reference` charge le jeu de données de
référence de WF-QUA-0040 : le témoin d'abord, comme `load-witness` le charge (ou rien, sur une
plateforme qui le porte), puis ce que la graine (`waterfall.witness.reference_draw`, SHA-256, jamais
`random`) tire à côté de lui — le référentiel du tableau 13 : quarante nœuds, cent cinquante rôles,
cinq cents comptes, en une transaction ; les projets, un par transaction, jusqu'à trois cents dans le
portefeuille (`--projects N`), étroits (trois à huit tâches, leur chef de projet pour seul
contributeur, aucun sous-projet), écrits comme ceux de la tranche du portefeuille ; enfin l'histoire
de PRJ-001, le projet de mille tâches du témoin (`waterfall.witness.reference_history`) : un mois
par transaction, le premier lundi de chaque mois à compter de juillet 2026, qui applique l'import des
coûts réels du mois, marque la révision en cours sous le nom du mois (« Revue de juillet 2026 ») par
la transaction même du worker (`load_marking`) et ouvre la suivante par la copie de celle qu'il vient
de marquer — cent quatre-vingts révisions marquées en tout (`--revisions N`, le témoin comptant
les siennes) et dix-huit mille lignes de coût (`--cost-lines N`), que les mois se partagent, cent par
mois à une ligne près. Tout passe par les interfaces des modules, jamais par un `INSERT` ; les
identifiants qu'un module tire le sont dans l'ordre (`drawn_in_order`), sous un instant propre à chaque
transaction. Arrêtée, la commande se reprend là où elle s'est arrêtée : un projet que la plateforme
porte est passé, et les révisions marquées de PRJ-001 disent le mois où l'histoire en est — jamais
une transaction à moitié écrite. Le jeu complet prend près d'une heure (un mois : une quinzaine de
secondes, le marquage d'une révision de mille tâches en étant l'essentiel) : il s'engendre une fois
par version, et les tests n'en jouent que la forme, sur un projet tiré par combinaison de vie et
trois mois d'histoire (`backend/tests/test_witness_reference.py`,
`backend/tests/test_witness_reference_history.py`).

`waterfall-api check-reference` en vérifie les volumes sur la plateforme qui le porte, sans
jamais le comparer aux exemples du contrat à trois cents projets (`fixtures/api/volume/`), qui restent
ceux du faux back : le témoin reste l'oracle des valeurs, le jeu celui des volumes. Il compte ce que
le produit compte d'une sauvegarde (projets, révisions marquées, lignes de coût, comme l'inventaire du
manifeste) contre ce que la graine et le témoin annoncent ; il cherche chaque identifiant et chaque
libellé que la graine dérive — nœuds, rôles, comptes, projets, révisions de l'histoire de PRJ-001 —,
ce qui est la reproductibilité : un jeu engendré deux fois, ou restauré, est le même ; et il tient les
sommes du portefeuille : son décompte égal aux projets qu'il liste, le budget de référence de chaque
ligne de projet en cours égal à celui que l'estimation (`portfolio_totals`) lit du projet, et son
carnet de commandes égal à la somme de ces budgets. Il écrit les volumes comptés puis chaque défaut
(`fault: …`), et se termine par 0, par 1 au premier défaut, par 2 sur un réglage qui manque ou une
histoire dont les lignes n'auraient aucun mois ; une histoire qui demande moins de révisions ou de
lignes que le témoin n'en porte n'écrit rien, et le dit sur la sortie d'erreur (`warning: …`), comme
`load-reference`. Une reprise sur un PRJ-001 dont les révisions marquées au-delà du témoin ne portent
pas les noms des premiers mois de l'histoire est refusée. `make service-reference` charge le jeu sur la plateforme de service
démarrée et amorcée (`REFERENCE_PROJECTS`, `REFERENCE_REVISIONS`, `REFERENCE_COST_LINES` pour moins,
par exemple pour un essai), `make service-reference-check` le vérifie ; l'un et l'autre lancent le
service `witness` du Compose de service sous une autre commande.

**Le jeu gardé en sauvegarde (US-2950/L2b, #4114).** Engendré une fois par version, le jeu se garde
en sauvegarde, et ce qui s'en sert — parcours, mesure, exercice de reprise — le restaure au lieu de
le réengendrer, sans acteur, sans route et sans jeton d'administrateur.
`waterfall-api backup-reference --into <dossier>` (mêmes `--projects`, `--revisions`,
`--cost-lines`) refuse d'abord une plateforme dont la planification règle une copie externe non
suspendue — la copie porterait l'archive, secrets du domaine compris, sur son emplacement —, puis une
plateforme qui ne porte pas le jeu entier, comme `check-reference` le lit : une installation réelle,
qui ne porte pas le témoin, est refusée. Il dépose ensuite une sauvegarde comme la planification la
dépose, sans demandeur (`deposit_backup` de `waterfall.worker.schedule`, sous ses verrous et ses
conditions) : le worker la prend, la vérifie et écrit son manifeste comme toute sauvegarde que la
plateforme prend d'elle-même. C'est voulu : d'origine `scheduled`, inscrite au nom de la plateforme,
elle fait tourner la liste sous la rétention de la planification — une rétention d'une sauvegarde
supprime la sauvegarde planifiée qui la précède —, elle est celle que le test de restauration élit
ensuite, et elle sert l'occurrence de la planification qu'elle suit (`backup_is_due`) ; sur une
plateforme qui porte le jeu de référence, aucune installation réelle, ces sauvegardes sont du jeu
aussi. Vérifiée, son archive est relue du compartiment des sauvegardes sous les verrous d'un dépôt —
aucune sauvegarde en cours ni déposée entre-temps, dont la rotation la supprimerait —, vérifiée de
nouveau comme le worker l'a vérifiée — un objet tronqué ne laisse rien —, et écrite dans le dossier,
son manifeste à côté (`.manifest.json`), sous le nom
`reference-<version>-<graine>-<projets>-<révisions>-<lignes>`, lisibles de leur seul propriétaire : l'archive porte la base du fournisseur d'identité, secrets des clients
compris, en clair comme toute sauvegarde. `waterfall-api restore-reference --from <dossier>` (mêmes
volumes) la restaure sur une plateforme neuve avant son démarrage (`waterfall.restore.fresh`), comme
le test de restauration d'US-2930 restaure sur sa plateforme éphémère : l'archive relue, chaque vidage
contre son empreinte, les deux bases remplacées par leurs propriétaires puis celle de Waterfall
migrée ; et, parce que la plateforme vit ensuite, ce qu'une restauration réécrit est réécrit — les
droits du rôle du service, la planification livrée, aucune sauvegarde ni aucun dépôt de la source, les
autres tâches que le vidage a prises en cours en échec (#892). Les tâches de sauvegarde qu'il a
prises en cours — celle qui l'a pris comprise — sont oubliées au contraire, avec celles qui étaient
terminées : la plateforme restaurée n'a planifié aucune sauvegarde, et ne dit pas sa dernière en échec
(`last_scheduled_outcome`, que son alerte lit) ; une restauration par un compte les fait toujours
échouer. Rien n'est inscrit au journal, et aucune ligne de sauvegarde n'est créée. Une plateforme
dont le fournisseur d'identité a déjà démarré (une table dans sa base), ou dont la base de Waterfall
porte ce que ses migrations n'écrivent pas (une inscription, une sauvegarde, un dépôt, une tâche),
n'est pas neuve, et est refusée avant tout changement. `make service-reference-backup` lance la
première commande sur la plateforme de service, dans un conteneur du worker, sous l'utilisateur du poste ; `make service-reference-restore`
retire les données de la plateforme du créneau, fait ses bases, y restaure l'archive dans un conteneur
du service de restauration, puis démarre la plateforme. L'archive et son manifeste sont dans
`REFERENCE_ARCHIVES`, `~/.local/share/waterfall/reference` par défaut : un dossier du poste, hors de
toute plateforme et de tout worktree, que les worktrees se partagent ; un consommateur le retrouve par
la version de sa branche et les volumes qu'il demande. Une archive d'une version suivante est refusée,
et une archive prise sur un schéma plus récent que celui de la branche ne se migre pas : le jeu se
réengendre alors (`backend/tests/test_witness_reference_archive.py` en joue la forme sur un mois).

**La tranche des projets (EP-04, US-0990).** Chargée après celle du référentiel, par les interfaces
des modules, elle écrit PRJ-001 et PRJ-002 avec leurs attributs et leur client (chacun créé par les
règles de la création, référentiel minimal compris), les comptes locaux de leurs contributeurs —
les quatre du témoin, dont un désactivé : créés dans Waterfall seul, par l'interface des comptes,
sans fournisseur d'identité, sous une adresse de `waterfall.test` ; ils ne se connectent pas —, les
contributeurs, les sous-projets, le lotissement, puis les révisions 100, 101 et 102 de PRJ-001, leur
structure principale et leurs transitions. Elle s'arrête où les règles s'arrêtent sans tâche ni
ligne : PRJ-001 reste en Chiffrage (le passage En cours est de l'EPIC qui sert l'offre et la
commande, EP-07) ; la 100 est marquée « Offre v1.0 », la 101 « Référence », la 102 est ouverte ; la
désignation de la 100 est tentée et refusée faute de tâches (`revision_has_tasks_and_lines`, notée
dans la sortie, `witness.designation_refused` : une désignation qui aboutit, ou tout autre refus,
est un défaut qui arrête la commande), si bien que PRJ-001 n'a pas de référence ; le code de PRJ-001
est saisi après ce refus. Le chargeur ne pose ni `inflation_rate` ni `win_probability` (la commande
reçue pose la seconde, EP-07). Ce que la tranche n'atteint pas, par objet, est listé dans
`backend/tests/test_witness_projects.py` (`UNREACHED`), chaque entrée avec l'EPIC qui la lève, et
ses lectures du témoin chargé sont comparées aux exemples du contrat (`projects.json`,
`revisions.json`, `contributors.json`, `subprojects.json`, `work_breakdown.json`, les transitions)
à ces états près.

La chronologie est un fichier de la tranche, `fixtures/api/project_state_transitions.json`, que
`make mock-data` écrit à côté des exemples (`wftools.mockchronology`, de `CHRONOLOGY` de
`wftools.mockwitness`, US-0990/L1) : les événements du témoin dans leur ordre, chacun avec son
instant en temps universel, son libellé et la liste de ce que la tranche y écrit — le projet créé,
une révision ouverte, une révision marquée sous son nom de version, la désignation tentée et son
refus, le code saisi, une transition d'état —, un événement que la tranche n'écrit pas (installation,
saisies de risques et de coûts, imports ; EP-06 à EP-09) gardant sa place. Le back le lit par un
modèle qui lui est propre (`waterfall.witness.timeline`) et n'importe jamais `wftools` : un fichier
qui s'en écarte — un genre inconnu, un champ de trop ou de moins, un instant sans fuseau, des
événements hors d'ordre — arrête la commande avant toute écriture. Les dates sont de deux sortes :
celles du référentiel sont celles du chargement (WF-DAT-0070) ; celles des projets, des révisions
et des transitions sont celles de la chronologie, que le chargeur impose à chaque écriture
(`Act.at`, WF-CYC-0130), la plateforme en étant l'auteur — deux chargements donnent donc les mêmes
dates de projet, de révision et de transition. Une collision d'identifiant, ou un refus ailleurs qu'à
la désignation, arrête la commande, rien n'étant écrit ; relancée sur une plateforme chargée, elle
réussit en disant le témoin là.

Le noyau, `waterfall.core`, a un sous-paquet par module, nommé d'après son bloc FBS de
second niveau, en anglais. Un module expose ce que les autres peuvent utiliser dans son
module `interface` — un paquet d'un fichier par objet, que `interface/__init__.py`
réexporte, pour les modules du référentiel (EP-05) —, et rien d'autre : ses tables et son accès
aux données lui sont privés. Les projets et leurs révisions (EP-04) sont deux modules :
`waterfall.core.projects` (FBS-4.2, et le cycle de vie du §3.3.2, qui n'a pas de bloc FBS) — le
projet, l'historique de ses états, ses contributeurs, ses sous-projets, son lotissement — et
`waterfall.core.revisions` (FBS-4.1) — les révisions et leurs structures de coûts. Leur interface est
un paquet d'un fichier par sujet (`projects`, `contributors`, `subprojects`, `work_breakdown`,
`lifecycle` ; `revisions`, `structures`, `marking`, `reference`), où chaque fonction de la
conception est déclarée dès le socle, sans effet, pour qu'aucune US ne rouvre `interface/__init__.py`
pour remplir la sienne.

Le planning (EP-06) en a trois : `waterfall.core.planning` (FBS-4.3) — les
nœuds et leur facette tâche, les liaisons, les chronologies et les inscriptions —,
`waterfall.core.history` — l'historique annulable et les plans de collage — et
`waterfall.core.exchanges` (FBS-4.3.4) — les imports, les exports et leurs formats —, dont
l'interface est de même un paquet d'un fichier par US ou par sujet, chaque fonction déclarée par le
socle (US-1380/L1). Un module du haut étend un module du bas sans que celui-ci l'importe, par un
registre ordonné (`Registry`, `waterfall.platform.registry`) que l'interface du bas offre de
remplir et que celle du haut remplit à son import (EP-06, « Les points d'extension ») ; un point
d'entrée qui en dépend importe l'interface qui enregistre, et `test_registries.py` le vérifie pour
l'API, le worker et le chargeur (#2180).

Une table révisionnée est partitionnée par liste sur `project_id`, une
partition par projet (WF-DAT-0050), que crée dans la transaction de la création du projet la
fonction `create_project_partitions` du propriétaire des tables (`SECURITY DEFINER`), que le rôle du
service seul peut exécuter, sans autre droit de DDL. Elle lit les tables révisionnées dans le
catalogue (migration `0026`) : une table qu'un EPIC ajoute, avec sa fonction
`<table>_refuse_truncate`, y entre sans la remplacer ; elle s'appelle avant toute écriture de la
transaction ([sql.md](sql.md), « Verrous »). Deux déclencheurs du module des révisions refusent,
propriétaire compris, ce qu'une révision marquée interdit (migration `0020`). Celui d'une table
révisionnée verrouille la révision de la ligne `FOR KEY SHARE` quel que soit son état, puis la lit,
et le marquage verrouille la révision `FOR UPDATE` avant de la marquer : un écrivain venu pendant le
marquage l'attend, puis se voit refusé, et le marquage attend l'écrivain commencé avant lui (#2104).
Chaque EPIC qui ajoute une table révisionnée lui donne un déclencheur de cette forme. Les verrous se
prennent dans un seul ordre : la révision, puis son projet, jamais le projet avant la révision.
Un module en importe un autre par `waterfall.core.<module>.interface`, jamais par ses
tables. Le noyau n'importe ni l'API ni le worker, qui ne s'importent pas l'un l'autre.

Ce qui n'est pas une fonction du métier — réglages et secrets, journaux, corrélation, exceptions
typées — vit dans `waterfall.platform`, sous le noyau : le noyau, l'API et le worker l'importent,
il n'importe aucun d'eux, et aucun de ses modules ne connaît une table du noyau. Le contrat de
couches de `backend/pyproject.toml` le garde.

_Contrôle_ : `make imports-back` (import-linter, contrats dans `backend/pyproject.toml`) ;
un test les éprouve sur un paquet d'essai (`backend/tests/test_boundaries.py`). Une requête
SQL écrite en texte, qui nommerait la table d'un autre module, échappe à l'analyse des
imports : elle relève des règles SQL d'EP-03 et de la revue.

**Une seule implémentation de chaque calcul** (WF-ARC-0010, US-2780/L3). La machine d'état, le
planning, le chiffrage et les indicateurs ne s'écrivent qu'une fois, dans leur module du noyau, que
l'API, le worker et le portefeuille importent. La table versionnée `tools/implementations.toml` nomme,
pour chaque fichier du noyau qui porte l'un de ces calculs, les noms par lesquels on l'appelle — ses
fonctions qui calculent, les constantes qui en fixent le résultat —, et pour chaque fichier du
portefeuille, les formules d'EP-10 qu'il applique à des sommes. Un fichier hors de `core/` et de
`migrations/` — l'API, le worker, les autres points d'entrée, la plateforme — ou du portefeuille ne
définit aucun de ces noms (ni fonction, à toute profondeur, ni affectation au niveau du module), et
ne les importe que du module du noyau qui les porte ; un fichier du portefeuille importe et appelle
les formules que la table lui donne. Un calcul nouveau d'un de ces quatre ajoute ses noms à la table.
Deux déclarations y gardent un écart dit sans échouer : un homonyme (`[[homonym]]`), autre calcul d'un
module du noyau sous un nom de la table, qui peut s'importer de ce module, et un doublon connu
(`[[duplicate]]`), dit à chaque passage avec sa raison jusqu'à ce qu'il disparaisse ; chacune échoue
quand elle ne tient plus ; un doublon peut copier un nom de la table sous un autre (`of`, et `of_file`
pour un nom privé que la table ne porte pas). « Appliquer » une formule, c'est l'appeler ou la passer
pour qu'on l'appelle (`map(cost_index, …)`) ; le contrôle ne vérifie pas que l'argument est une somme,
ce qui relève de la revue. Le contrôle juge par le nom : un calcul récrit sous un autre nom lui
échappe, et relève de la revue — l'arrondi d'un montant récrit par `quantize`, sans nom de la table,
en est un (le cas de `_money` de l'API est ouvert à part, #4373) ; les générateurs du faux back, qui
ne sont pas livrés, en sont hors. Un fichier tenu qui nomme `schedule`, `advance`, `margin`,
`balances`, `distribution` ou `cumulative` autre chose qu'un calcul de la table n'a pas
d'échappatoire : il renomme sa méthode.

_Contrôle_ : `make implementations` (`wftools.implementations`, famille `repo`, qui s'exécute sur
toute modification).

**Les tâches de fond** (WF-ARC-0090). Une tâche vit dans la table `background_task`
(`waterfall.platform.tasks`), qui fait foi ; le flux Redis (`waterfall.platform.queue`) n'en porte
que l'identifiant. Une route la dépose par `submit(session, queue, genre, demandeur)`, dans sa
transaction, sous la corrélation de la requête : le dépôt dans le flux suit la validation, et une
tâche dont le dépôt s'est perdu reste `queued`, que le worker redépose au démarrage puis
périodiquement. Le worker (`waterfall.worker.runner`) exécute la tâche dans une seule transaction,
sous un verrou consultatif qui lui est propre, par le traitement de son genre — une fonction
`(session, tâche)` que `handlers(réglages)` (`waterfall.worker.main`) enregistre, et qui refuse par
une exception typée du noyau, dont le code devient le motif de l'échec. Arrêté pendant une tâche, il
ne laisse rien de son travail : un autre la reprend depuis le début, et elle échoue après trois
tentatives ; une tâche d'un genre qu'aucun traitement n'exécute échoue sans s'exécuter. Une
restauration (`restore`) n'est jamais celle du worker : `startRestore` la dépose dans un second
flux, `waterfall:tasks:restores`, que le service de la restauration lit seul, dans son groupe de
consommateurs ; il pose la maintenance, que l'API lit (503 hors `/health` et `/metrics`), et le worker
n'exécute rien tant qu'elle y est (EP-03, « Sauvegarde et restauration »). La maintenance et l'état
de la restauration qui la tient vivent dans le schéma `platform` de la base de Waterfall, une ligne
au plus dans chacune de ses deux tables, que le rôle du service lit et que le propriétaire seul
écrit (`waterfall.platform.maintenance`, migration `0048`) : une sauvegarde ne vide que `public`, et
une restauration ne remplace que lui, si bien que vider Redis pendant une restauration ne lève pas
la maintenance (EP-13, US-2830, #956). Chaque requête de l'API lit donc la maintenance en base, une
lecture de plus par requête (la sonde de vie la lit pour la dire), bornée par `CONNECT_TIMEOUT` pour la
connexion à la base — celle que l'adresse déclare par `?connect_timeout=` l'emporte — et par `POOL_TIMEOUT` pour le
réservoir (#4189, #4190) ; une
base qui ne répond pas ou dont le réservoir est épuisé dit « pas de maintenance » et la sonde répond.
Une maintenance posée dont l'état manque reste posée, comme une restauration abandonnée. Les tâches planifiées se déposent par `waterfall-worker schedule`, la seule commande que les
planificateurs appellent : elle inscrit et met en file ce qui est dû — la lecture des comptes et la sauvegarde à
l'heure que disent leurs planifications, que l'administrateur règle à l'écran et que la base garde
(`identity_sync_schedule`, `backup_schedule` ; une lecture quotidienne à 01:30 UTC par défaut), la
purge à l'intervalle de `WATERFALL_PURGE_INTERVAL`, dix minutes par défaut — et n'en dépose pas une quand une
tâche du même genre est en file ou en cours ; elle n'atteint que PostgreSQL et Redis (TFX-10). Le
service `scheduler` de Compose l'appelle toutes les `WATERFALL_SCHEDULE_INTERVAL` secondes, cinq
minutes par défaut, la CronJob du chart de même ; un intervalle qui n'est pas un entier positif
arrête le service avec 2. La purge épargne la dernière tâche de chaque genre planifié, si bien qu'une planification plus espacée que la rétention ne rend pas la lecture due à chaque purge ; sous Helm, la première lecture peut partir avant que le royaume Keycloak soit appliqué (le crochet suit l'installation) : elle échoue, et la suivante est due à l'occurrence suivante de la planification. La purge est une tâche du worker (`worker/purge.py`) : ce qui a expiré —
comptes rendus d'import, dépôts, exports, historique annulable, et leurs objets sur le stockage
(EP-06, « La purge ») —, puis les tâches terminées depuis plus que `WATERFALL_BACKGROUND_TASK_RETENTION_DAYS`,
trente jours par défaut, la tâche d'une sauvegarde encore listée épargnée. Un genre de plus se
planifie par une ligne de `planned` (`worker/schedule.py`).
Qui ouvre la file dit combien il attend Redis : une requête ou le planificateur
`TaskQueue.connect(adresse, timeout=DEPOSIT_TIMEOUT)`, une seconde, pour qu'un Redis muet ne
retienne pas la réponse ; le worker `WORKER_TIMEOUT`, plus long que chacune de ses lectures. Une
erreur que le worker n'attend pas — Redis ou PostgreSQL hors d'atteinte — l'arrête en échec (1),
dite dans ses journaux par `worker.failed`, secrets masqués.
Une tâche d'un genre que le worker ne connaît pas — celle qu'une version plus récente a déposée,
pendant une mise à jour progressive — reste en attente : le worker n'acquitte pas son entrée, ne compte
aucune tentative et journalise `task.left` ; une entrée au repos depuis `claim_after` est reprise, par un
worker plus récent qui en a le traitement. Elle n'échoue (`INTERNAL_ERROR`, `kind_unhandled`) qu'une fois
`WATERFALL_UNKNOWN_KIND_WAIT_SECONDS` secondes écoulées depuis son dépôt, 3600 par défaut (#809).

**Le marquage, premier traitement du métier** (US-0970). Une tâche qui vise un projet le nomme dans
sa charge, sous `project_id` (`PROJECT` de `waterfall.platform.tasks`) : tant qu'elle est en file
ou en cours, `no_background_task_running` de l'interface des projets est faux, et les commandes
qui écriraient dans le projet nomment cette condition. `markRevision` juge le marquage sous le
verrou de la révision — 404, 412, `revision_draft`, `no_background_task_running`, puis
`ALREADY_EXISTS` sur `/version_name` —, et dépose sa tâche `revision_mark` dans la transaction de
la requête (`submit_marking`), 202 ; le front la suit par `getBackgroundTask`. Le worker
(`waterfall.worker.marking`) refait le jugement dans la transaction de la tâche (`mark_revision`),
calcule les indicateurs (`compute_indicators`, qu'EP-10 remplit), marque la révision, la retire du
projet et inscrit `revision_mark` au journal, son auteur le demandeur ; un refus, ou un calcul qui
lève, fait échouer la tâche avec son code (`BackgroundTask.problem`), rien n'étant écrit, et un
nouveau `markRevision` la relance.

Toute opération servie que le contrat garde déclare, sur sa route, les permissions qu'elle demande :
`dependencies=[Depends(Requires(...))]` (`waterfall.api.evaluation`), évaluées avant la validation
des paramètres et du corps, après sa lecture : un corps illisible est refusé d'abord (400). La
permission de consulter vient la première — sans elle, l'objet n'existe pas pour l'appelant, 404
`NOT_FOUND` ; sans une autre, 403 `PERMISSION_MISSING`, `params.missing_permission` la nommant
(WF-ADM-0110). Qu'une permission soit une consultation, le catalogue le déclare
(`CONSULTATION`, `waterfall.core.access_roles.predefined`), non son suffixe : `all_projects_read`
en est une (#754). L'évaluation elle-même, `require(actor, permission)`, est celle du module
`waterfall.core.access_roles`. Une opération d'un projet déclare à la place
`RequiresProject(...)`, qui lit `project_id` du chemin et évalue de même un second terme, la
qualité de l'appelant sur le projet, lue par l'interface des projets (`contributor_kind`) :
`require_project`. Le projet n'existe pour l'appelant que s'il porte la permission de consulter et
en est contributeur, ou porte `all_projects_read` ; sinon, ou s'il n'existe pas, le même 404
`NOT_FOUND`. Une écriture demande en plus la qualité de contributeur (403 `NOT_CONTRIBUTOR`), une
action réservée aux chefs de projet (`manager=True`) la leur (403 `NOT_PROJECT_MANAGER`),
`params.missing_condition` la nommant (WF-PRJ-0060). _Contrôle_ :
`backend/tests/test_access_evaluation.py` liste les permissions de chaque opération servie, et la
qualité sur son projet de chaque opération d'un projet (`ON_PROJECT` des fichiers `asked_*.py`), et
vérifie que le contrat déclare le refus qu'elles peuvent donner — une route nouvelle s'y ajoute.

## Le front

### L'outillage : Next, pnpm et Vitest

Le front est une application Next.js en TypeScript strict (`frontend/tsconfig.json`, avec
`noUncheckedIndexedAccess` et `exactOptionalPropertyTypes`). pnpm en gère les dépendances,
à la version que nomme `packageManager` dans `package.json`, installé une fois par
`npm install --global pnpm` ; le verrou, `pnpm-lock.yaml`, fait foi et la chaîne installe
avec `--frozen-lockfile`. Les tests unitaires sont des fichiers `*.test.ts` ou `*.test.tsx`
à côté du code qu'ils éprouvent, lancés par Vitest en deux projets (`vitest.config.ts`),
que le nom du fichier départage : `node` pour les `*.test.ts` et `*.test.tsx` — la logique,
et les composants serveur de `src/app/`, qui se rendent sans document comme en production —,
`dom` pour les `*.dom.test.ts` et `*.dom.test.tsx` — les composants client, que Testing
Library rend dans le document de happy-dom. Un `*.dom.test.tsx` peut vivre sous `src/app/` quand
il éprouve ce qu'une page compose avec ses composants client : la page se lit comme en production,
sur le serveur, et l'arbre qu'elle rend se monte dans un document, où seul un rendu montre ce que
la bannière et la grille partagent (`structure-screens.dom.test.tsx`). Un tel test n'éprouve pas
le Vérif d'une exigence et n'en cite pas : il tient en non-régression le défaut n° 20 de
`typescript.md` et #819.3, les mêmes écrans ayant leurs parcours sous `e2e/`. Un test du projet
`dom` qui écrit sur la sortie d'erreur — `console.error`, `console.warn`, `console.trace` —
échoue une fois son document nettoyé (`frontend/src/test/stderr.ts`, appelé par `setup-dom.ts`) :
un avertissement de React ou d'ECharts, une réponse que le faux back n'a pas, sont des défauts du
test ou du code, pas un bruit à lire en passant. Un test qui prouve qu'une erreur se dit sur la
console la fait taire lui-même par un espion (`vi.spyOn(console, "error")`), et vérifie ce qui fut
dit. happy-dom ne mesure rien : un test qui monte une courbe donne à son dessin la place qu'une
page lui donne (`roomForCharts`, `frontend/src/test/chart-room.ts`), faute de quoi ECharts avertit
qu'il n'a ni largeur ni hauteur (EP-02/L37). Un test de grille donne à l'élément qui défile sa
boîte (`offsetHeight`, `offsetWidth`), et `setup-dom.ts` mesure l'intérieur de tout élément
(`clientHeight`, `clientWidth`) par sa boîte : TanStack Virtual mesure la fenêtre des lignes par
l'intérieur depuis sa 3.19, et un élément que happy-dom ne met pas en page n'a ni bord ni barre de
défilement (US-1170/L3).

### La navigation : la table des fonctions et ses routes

La coquille (`frontend/src/components/shell/`) tire sa navigation de
`frontend/src/navigation/functions.json` : pour chaque fonction de second niveau de la FBS,
son code, la clé de son libellé, sa route, sa portée et la permission qui la laisse
consulter ; une fonction dont la session n'a pas la permission `<fonction>.read` n'y figure
pas. La table porte aussi les feuilles de la FBS, chacune adressée de l'une de deux façons. Une
feuille qui a son propre écran est une feuille (`leaves`) de sa fonction, de même portée et de même
permission : la correspondance de l'extraction des coûts réels, FBS-3.1.3, sous les paramètres de
coûts (`/reference/costs/actual-cost-mapping`, US-0620), les chronologies, FBS-4.3.1, les imports
et exports, FBS-4.3.4, et l'arborescence de tâches, FBS-4.3.5, sous le planning
(`/projects/[projectId]/revisions/[revisionId]/timelines`, `…/exchanges`, `…/task-tree`), le plan
de charge du projet, FBS-4.4.4, sous le devis (`…/workload`), et le Kanban, FBS-4.5.3, sous le
reste à engager (`…/kanban`). La navigation la montre, en retrait sous sa fonction, dans une liste
imbriquée dans l'élément de celle-ci, avec la garde de la feuille et dans le même contexte ; l'écran
de sa fonction y mène aussi. Le menu de plateforme rend de même les feuilles de ses fonctions, la
feuille courante marquée `aria-current`. Le lien courant, `aria-current="page"`, est celui de la
feuille ; sa fonction, qui est le chemin, porte `aria-current="true"`. Repliée en icônes, la barre
ne montre que la fonction, marquée ainsi quand la page est l'une de ses feuilles. `readContext` la
lit comme sa fonction, et le fil d'Ariane la place après elle, y compris une feuille de portée
`platform`, dans son bloc de la FBS. Une feuille
que l'écran de sa fonction montre lui-même, là où l'ergonomie l'a rangée, est une section
(`sections`) de sa fonction, adressée par la route de celle-ci : son `code`, le rôle de ce qui la
montre (`role` : `region`, `grid`, `treegrid`, `columnheader` ou `heading`) et la clé de son nom
(`name`) — le lotissement, FBS-4.2.1, est la région « Lotissement » des paramètres du projet ; le
Gantt, FBS-4.3.3, la colonne « Gantt » de la grille de planning ; l'avancement financier,
FBS-4.8.1, le titre de sa carte. Seul un fait d'une liste nommée se passe de rôle — un terme ne
prend pas son nom de ce qu'il dit — : il se trouve par son texte dans la liste que nomme la clé
`within`, comme le taux d'inflation, FBS-4.2.2, dans les « Paramètres du projet » ;
`functions.test.ts` refuse toute autre section sans rôle.

_Contrôle_ : `make screens` (`wftools.screens`, famille `repo`, qui s'exécute sur toute
modification, puisqu'il lit la projection comme le front) confronte la table aux fonctions de la FBS
de la projection — les boîtes des figures de l'arborescence et de chaque bloc, qui les nomment
toutes, et les titres de leurs paragraphes, lus en protection ; une flèche dont l'enfant ne prolonge
pas le code de son parent fait échouer la lecture — et aux pages de `frontend/src/app` ; il échoue,
en nommant la feuille ou la route, sur une feuille sans route dans la table, sur un code de la table
qui n'est pas une fonction de la FBS ou une feuille rangée sous une autre fonction que la sienne,
sur une route à laquelle aucune page ne répond — la page de `[...path]`, qui dit « introuvable », ne
répond à aucune —, et sur une feuille à écran propre que la page de sa fonction ne nomme pas par
`leafOf("FBS-…")`, et ne peut donc pas mener. Une feuille qui n'a pas encore d'écran se déclarerait,
avec sa raison et l'issue qui la suit, dans `WITHOUT_SCREEN` de `tools/src/wftools/screens.py`, vide
aujourd'hui ; la déclaration échoue dès que la table adresse la feuille. Le parcours
`frontend/e2e/screens.spec.ts` (`make e2e`, palier complet) prouve les liens dans un navigateur, un
parcours par route, tiré de la table : une fonction s'atteint par un clic sur un lien de la
navigation — depuis l'écran d'une autre fonction de son bloc, ou d'une révision pour une fonction
d'un projet —, une feuille à écran propre par un clic sur un lien de l'écran de sa fonction ; le
lien doit être visible, la route est compilée d'avance (`compile`), et un écran de projet de départ
s'ouvre hydraté (`openHydrated`). Chaque écran atteint nomme sa fonction et montre ses sections. Une
route ajoutée à la table a donc son parcours. Trois portées : hors projet ; `project`, les fonctions
du projet lui-même — révisions, paramètres, cycle de vie —, sous `/projects/[projectId]/…`, qu'un
projet sans révision offre ; `revision`, les autres, sous
`/projects/[projectId]/revisions/[revisionId]/…`. Le contexte de lecture est dans l'adresse : le
projet dans le chemin, la révision dans le chemin ou, sur une fonction du projet, en paramètre
`revision_id` ; sous-projet filtré et date de calcul en paramètres, `subproject_id` et `as_of`,
comme le contrat les nomme. Les liens entre fonctions d'un projet les reportent, et un témoin du
front, `wf_last_project`, garde le dernier, dont la coquille tire le « retour au projet »
(WF-IHM-0010) ; il ne ramène qu'à un écran de projet de la table, fonction ou feuille qui a son
écran. Chaque route de la table a sa page, ce que `frontend/src/app/[...path]/page.test.tsx` vérifie
; toute autre adresse mène, par `frontend/src/app/[...path]/page.tsx`, à l'écran « introuvable ».
Les pages du compte (`/account`, `/account/avatar`, `frontend/src/navigation/account.ts`) ont leurs
écrans (US-0320) : les informations du compte et ses préférences d'affichage — la langue et le mode,
les mêmes champs que le menu du compte écrit, enregistrés ensemble — et l'avatar. Aucun écran de
Waterfall ne demande, n'affiche ni ne change un mot de passe : le fournisseur d'identité les tient
(WF-ADM-0140), et l'écran du compte mène un compte local à sa page du compte du royaume
(`realmAccountPage`, `src/session/settings.ts`), dans un autre onglet ; un compte de l'annuaire ou
d'un fournisseur externe n'y a pas de mot de passe, ni le faux back de royaume. Il n'envoie la
langue que si elle a changé : l'API la reporte au fournisseur d'identité, et un changement du seul
mode n'attend pas Keycloak (#877). L'image de l'avatar, servie par l'API seule, est lue par le
serveur de Next en rendant la page et écrite dans la page en adresse `data:` (`avatar-source.ts`) :
ni appel du navigateur à l'API, ni relais ; l'écran de l'avatar seul la montre, le menu du compte
garde les initiales.

### Le nom d'un compte

Un nom de compte ne s'affiche que par `useAccountNaming`
(`frontend/src/components/account/account-name.ts`) : `person` pour un compte par ses prénom et
nom, `kept` pour le nom qu'une réponse a gardé de lui — l'auteur et l'objet d'une inscription du
journal, l'auteur d'une transition, les colonnes d'audit d'un objet. L'API rend nuls les noms
d'un compte anonymisé, sans phrase à leur place (WF-ADM-0060, WF-ARC-0110) : un nom nul se dit
par le libellé neutre du catalogue (`accountName.anonymized`, « Compte anonymisé »), jamais par
un vide ni par l'identifiant du compte. Dans une cellule, ce libellé a un seul rendu,
`AnonymizedName` (`KeptName` pour un nom gardé qui peut être nul, dans `anonymized-name.tsx`),
grisé et marqué `data-anonymized` ; une option de `<select>`, qui ne porte que du texte, prend
`kept(null)`.

### La coquille : barre latérale, barre du haut et menu du compte

La coquille se compose ainsi (`shell.tsx`, mise en page de la charte) : à gauche la barre latérale
(`navigation.tsx`), le logo et le choix du projet en tête, les fonctions en trois groupes — la
plateforme, par bloc de la FBS repliable ; le projet, avec la liste des projets et le « retour au
projet » ; la révision lue —, le bouton qui la replie au pied ; au-dessus de la page, la barre
(`top-bar.tsx`) : le bouton qui replie la barre latérale, le fil d'Ariane
(`frontend/src/navigation/breadcrumbs.ts`), la recherche — en place, sans fonction encore —, le
bouton du panneau des tâches et des messages et le menu du compte. La barre latérale repliée garde
son état dans un témoin du front, `wf_sidebar_state`, que le layout racine lit pour la rendre telle
côté serveur. Le layout, rendu une fois, ne connaît pas l'adresse : le libellé du projet vient de
l'écran, qui l'a déjà lu pour son bandeau — `ContextBanner` le remet à la coquille par `ShowProject`
(`shown-project.tsx`), qui ne le nomme que tant que l'adresse montre ce même projet. Le menu du
compte (`account-menu.tsx`) porte les préférences d'affichage — langue et mode, chacune un choix
dans un sous-menu, écrit au compte à la sélection, le parcours au clavier n'envoyant rien —, les
pages du compte et la déconnexion. La déconnexion (`closeMySessions`, qui ferme toutes les sessions
du compte ; un 401 valant session déjà close, le compte désactivé ou non admis compris) oublie ce
que le navigateur gardait de la session — le témoin `wf_last_project`, les tâches du stockage
`wf_background_tasks` et du suivi, l'historique des messages (`wf_messages`) — puis charge en
document entier l'adresse que rend l'action : `/login`, d'ordinaire. `/login?next=…` est un
gestionnaire de route (`src/app/login/route.ts`), non une page : Waterfall n'a ni formulaire de
connexion, ni liste de fournisseurs, ni mot de passe oublié, le fournisseur d'identité tenant ses
écrans. Sur le faux back (`WATERFALL_AUTH=mock`), qui accorde la session, il mène droit à l'écran
visé (`returnTarget(next)`, `frontend/src/navigation/login.ts`) — sans lui, ou hors du front,
l'accueil — : le layout relit la session, et le suivi reprend les tâches qu'une session perdue avait
interrompues. Hors de ce mode, il démarre le flux du code d'autorisation du royaume `waterfall`
(US-0350) — voir « La session du front » ci-dessous. La session est `getMe`
(`src/session/request.ts`) : le compte à plat, ses préférences d'affichage et ses permissions. Un
401 `ACCOUNT_DEACTIVATED` ou `ACCOUNT_NOT_ADMITTED` n'est pas une session absente : l'écran le dit
(la panne `failure.deactivated` ou `failure.notAdmitted`, le refus d'une action), et ne renvoie pas
à la connexion, qui bouclerait (#664). Sans compte (401), il n'y a ni menu du compte ni barre
latérale ; quand la session est illisible, la barre latérale est rendue avec l'écran d'état seul,
son bloc ouvert, et sans menu du compte. La barre latérale est un repère (`<aside>` nommé) ; sur
écran étroit, c'est une feuille modale qui se ferme dès que l'adresse change ; Ctrl+B ne la plie que
si elle est rendue, et la plier rend le focus de ce que le rail cache au bouton du bloc ou au
déclencheur.

### La session du front

**La session du front** (US-0350, `frontend/src/session/`). Le navigateur ne détient aucun jeton
(WF-ARC-0030) : le serveur de Next les tient dans Redis, sous un identifiant opaque que le témoin
`__Host-wf_session` porte seul (`HttpOnly`, `Secure`, `Path=/`, sans `Domain`, `SameSite=Lax`, sans
échéance) : son préfixe empêche un sous-domaine voisin d'en poser un à lui, que `/login` lirait le
premier (#887) ; le navigateur le prend aussi de `http://localhost` ou `http://127.0.0.1`, où
tournent les parcours et le poste, comme tout témoin `Secure`. `/login?next=…` tire un `state`, un
nonce et un vérificateur PKCE (S256), les garde dans Redis avec l'écran visé — déjà passé par
`returnTarget` — quinze minutes au plus, donne au navigateur un témoin lié à ce `state`
(`wf_sign_in_<state>`, limité à `/auth/callback`, quinze minutes), et l'envoie à la page de
connexion de Keycloak. `/auth/callback` exige ce témoin — un retour porté à un autre navigateur n'y
ouvre aucune session et recommence la connexion, sans toucher à la demande (RFC 9700, §4.7) —,
reprend la demande par son `state`, une seule fois, échange le code, vérifie le nonce du jeton
d'identité, ouvre la session — ses jetons dans Redis pour la durée que Keycloak donne à sa session,
`refresh_expires_in` — et mène à l'écran visé, son adresse entière ; un `state` inconnu, déjà
employé ou trop vieux recommence la connexion ; une connexion que le royaume refuse — une erreur au
retour, un code refusé, un nonce faux — mène à l'accueil sans session, jamais à `/login`, que la
session de Keycloak bouclerait, et laisse un témoin court (`wf_sign_in_refused`, quelques minutes,
`HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`) qu'une connexion réussie efface (#2914). Keycloak ou
Redis injoignable, ou Keycloak muet au-delà du délai, `/login` et `/auth/callback` mènent à
`/login/unavailable` en oubliant le témoin `__Host-wf_session` — la page relirait sinon Redis pour
lui —, qui dit le service injoignable et offre de recommencer vers l'écran visé, jamais à une erreur
500 nue (#687). `/login` efface aussi le témoin `__Host-wf_session` : la déconnexion y mène sans y
toucher (#724). `serverClient()` est le seul endroit qui porte le jeton à l'API
(`src/session/tokens.ts`) : à chaque requête, il lit la session du témoin et rafraîchit un jeton
d'accès qui expire dans moins de trente secondes, sous un verrou Redis par session qui vit deux fois
le délai d'une requête au royaume (`REFRESH_TIMEOUT`, cinq secondes), pour que deux requêtes ne
présentent jamais le même jeton de rafraîchissement. Un rafraîchissement qui échoue une fois parti —
refusé, sans réponse dans ce délai, la connexion coupée pendant la réponse, un mandataire qui répond
à sa place — ferme la session : Keycloak a pu prendre le jeton, qui n'est jamais présenté deux fois
(#687). Seule une requête qui n'a pu partir (Keycloak injoignable : connexion refusée, hôte inconnu
ou hors d'atteinte, certificat refusé) ne la ferme pas : le jeton d'accès sert tant qu'il vit, puis
la requête est le service injoignable (`Unreachable`), que l'écran dit comme tel. Redis injoignable
pendant une requête ordinaire l'est de même, un composant de la plateforme hors d'atteinte
(WF-EXP-0040) : `requestBearer` change le `StoreUnreachable` du magasin en `Unreachable`, et l'écran
dit le service injoignable, jamais une erreur inattendue (#861). Quand la session que nomme le
témoin ne vit plus, ou qu'il n'y a aucun témoin (WF-SEC-0020, #2914), la requête ne part pas
(`SessionLost`) : une lecture mène à la connexion aussitôt, sans clic — l'écran de panne charge
`/login?next=<écran>` —, une écriture n'est pas appliquée, et l'écran le dit avant d'y mener par un
lien (`decode`) ; c'est `requestBearer` qui en décide, une fois pour les écrans, les lectures de la
coquille — le compte de la mise en page, l'installation qui décide la langue — exceptées :
`serverClient({ session: "optional" })` les fait partir sans jeton, pour que la page « service
injoignable » (`/login/unavailable`) se rende au lieu de mener à la connexion, qui bouclerait. Seul
le témoin `wf_sign_in_refused`, laissé par une connexion que le royaume a refusée, fait partir sans
jeton une requête sans témoin de session, et un 401 de l'API (`SignedOut`), comme le refus d'un
jeton vivant, offre la connexion par un lien sans y mener seul : y mener bouclerait. Sur un 401
`SESSION_REVOKED` seulement — un jeton d'une connexion antérieure à la fermeture des sessions du
compte —, ce lien, l'écran de panne (`failure.revoked`) comme l'avis d'une action, mène à
`/login?next=…&reauthenticate=1`, que `/login` envoie au royaume avec `prompt=login` : Keycloak,
dont la session a pu survivre à une fermeture manquée, redemande les identifiants et renouvelle
`auth_time` ; un `SESSION_EXPIRED` ne les redemande pas (#855). La déconnexion (`signOut`) ferme les
sessions du compte par `closeMySessions`, puis efface celles que le front garde de ce compte, sans
attendre Keycloak — l'API d'administration ferme aussi la session de Keycloak du navigateur, et
`/login` redemande les identifiants. Elle ne touche pas au témoin : une action serveur qui change un
témoin fait rendre à nouveau la page dans sa réponse, qui lirait l'API sans session (#724) ;
`/login` l'efface. Un compte non admis garde une session de Keycloak que l'API ne ferme pas : le
navigateur va au point de déconnexion du royaume. La coquille ne lui offre ni barre ni menu du
compte : la panne `failure.notAdmitted` offre « Se déconnecter », un lien vers `/auth/sign-out`, qui
mène au même point (`signOutAddress`) ; le royaume, sans jeton d'identité, demande de confirmer,
puis mène à `/login`, qui redemande les identifiants (#664). Quand la session que nomme le témoin ne
vit plus, la requête ne part pas, et le navigateur passe par une connexion silencieuse
(`/login?sign_out=<ticket>`, `prompt=none`). Seule l'action `signOut` l'arme : un ticket tiré au
hasard, gardé une minute dans Redis et lié à l'identifiant que porte le témoin `__Host-wf_session`
de la requête, sans toucher au témoin (`armRequestSignOut`, `armSignOut`) ; `/login` ne le prend,
une seule fois, que si le témoin du navigateur porte ce même identifiant (`takeSignOut`). Un ticket
inconnu, déjà pris ou trop vieux — un lien d'un autre site, qu'une navigation de premier niveau
envoie avec le témoin `SameSite=Lax` —, ou lié à un autre témoin, ou un navigateur sans témoin, font
une connexion ordinaire, qui ne ferme rien et laisse le ticket : l'identifiant de l'action est
public, et un tiers qui l'appelle depuis son serveur, avec un témoin à lui, obtient un ticket qui ne
déconnecte que ce témoin. Son retour ferme les sessions du compte par `closeMySessions`, avec le
jeton qu'elle a obtenu (`tokenClient`), sur tous ses postes, puis mène à `/login` ; sans session de
Keycloak non plus, il n'y a plus de poste à fermer (#689). Un jeton que l'API refuse alors par
`SESSION_REVOKED` — la session de Keycloak a survécu à une fermeture manquée — mène, comme le refus
de `closeMySessions` par ce code dans `signOut`, à `/login?…&reauthenticate=1`, qui redemande les
identifiants : jamais une nouvelle connexion silencieuse, qui ramènerait le même refus (#855). Un
clic sur un lien du front attend les écritures de la page (`holdNavigation`, `useNavigationHold`) :
une cellule validée, un collage appliqué, une commande — le bouton d'une commande (`Command`), d'une
liste ou d'un formulaire du référentiel, l'enregistrement des préférences, l'envoi ou le retrait de
l'avatar, la demande d'un export, la relance d'une tâche, l'envoi d'un fichier à importer, qui
passent tous par `useHeldCommand` (`components/commands/held.ts`) ; une refusée — la session perdue
comprise —, la navigation n'a pas lieu, et l'écran dit le refus là où l'écriture a été faite (#688).
La retenue appartient à qui dit le refus : un formulaire ou une ligne d'une liste du référentiel
prend celle de la liste (`held` de `useListReport`), qui dit au-dessus d'elle le refus d'un dialogue
fermé pendant l'envoi ; fermer le dialogue ne libère donc pas son écriture. La liste ne dit un refus
que sur la lecture d'où il est parti : lue autrement — une recherche, un filtre d'état —, elle
libère ses écritures, dont le refus n'est plus dit par la liste, ni au retour sur cette lecture,
dont les clics ne sont plus retenus — une lecture quittée puis retrouvée en est une autre
(`useHeldCommand(generation)`) ; encore en route et refusées ensuite, l'avis de la barre les dit,
comme celles d'un écran quitté (ci-dessous). Tout refus retient le clic, même dit ailleurs que sur
l'écran quitté : la relance d'une tâche refusée retient la navigation, bien que son refus soit dit
dans le panneau des tâches de la coquille, qui survit à l'écran — une règle sans exception plutôt
qu'une écriture à juger une à une. Le clic se juge par son geste, qui commence quand le pointeur
descend ou qu'une touche est pressée : il attend les écritures encore en cours et celles parties
depuis le début du geste, même déjà répondues — la cellule validée quand le pointeur descend sur le
lien, dont la session perdue répond avant le clic, retient ce clic. Seul le dernier clic retenu est
refait ; un écran quitté libère ses écritures, qui ne retiennent rien de l'écran suivant. Ne sont
pas retenus : une navigation programmatique (`router.push`), « Précédent » et « Suivant » du
navigateur, un lien qui ouvre ailleurs — autre onglet, touche de modification, téléchargement, autre
site. « Précédent » et « Suivant » changent l'adresse aussitôt, mais depuis Next 16.4 le routeur ne
montre l'entrée retrouvée qu'une fois répondue l'action en cours (vercel/next.js#99612, entrée de la
16.4.0) : `runAction` (`next/dist/client/components/app-router-instance.js`) applique désormais
l'état de la traversée dans la transition qu'ouvre `traverse`, où la 16.3 l'appliquait une
microtâche plus tard, hors d'elle ; et React donne à une transition demandée pendant une action
asynchrone la voie de cette action (`requestTransitionLane`, `currentEntangledLane` de `react-dom`),
qui ne se valide qu'à sa réponse — ici l'écriture attendue dans `startTransition(async …)`. L'écran
quitté reste donc affiché jusqu'à la réponse, et une écriture refusée pendant qu'il est quitté vers
un autre chemin — faite avant la traversée ou après — va à la barre, même quand ce qui l'a demandée
dit le dire encore (`told`), puisqu'il s'en va avec l'écran (`away` de `holdNavigation`,
`useHeldWrites`) ; ramené à son chemin avant le refus, l'écran le dit lui-même. Ramené après le
refus, avant que le routeur n'ait montré l'entrée traversée — « Suivant » pressé pendant qu'il la
lit —, l'écran, qui n'est jamais parti, le dit aussi, et la barre retire ce qu'elle en disait
(`broughtBack`, #1476) : le refus est dit deux fois, l'un après l'autre, jamais en même temps, et
noté une fois dans l'historique des messages, par l'identité de sa réponse — pour un refus porté par
un `outcome` ; une réponse booléenne n'a pas d'identité, et l'historique la note à part de ce que
l'écran en dit. Jusqu'à sa réponse, l'écriture attendue dans la transition retient encore les clics
: l'écran quitté par « Précédent », toujours affiché, ne la libère qu'en partant. Cela tient tant
que le routeur garde cet ordre, peut-être un défaut amont. Une écriture encore en route quand son
écran s'en va, et refusée ensuite, n'est dite par aucun écran : la barre de la coquille, qui survit
à chacun, le dit par un avis qu'on ferme (`LeftRefusals`, `refusedLeft` de `held-writes.ts`, #863),
et l'inscrit dans l'historique des messages avec son refus et l'écran d'où elle était partie ; une
écriture refusée avant le départ de son écran y a été dite, et ne l'est pas deux fois. Keycloak,
lui, notifie la fermeture des sessions d'un compte — déconnexion, désactivation, retrait des rôles —
par le canal de retour, `/auth/backchannel-logout`, une route du front et non une opération de
l'API, qui vérifie le jeton de déconnexion par les clés du royaume et efface les sessions Redis du
compte qu'il nomme. Seuls `src/session/provider.ts` (`openid-client`, `jose`) et
`src/session/store.ts` (`@redis/client`) atteignent Keycloak et Redis, chacun les siennes seulement
: ESLint refuse ces bibliothèques ailleurs, et chacun des deux modules celles de l'autre
(`src/api/network-guard.test.ts`).

Le front, hors du mode `mock`, lit : `WATERFALL_KEYCLOAK_ADDRESS`, l'adresse de Keycloak pour le
navigateur, dont relève l'émetteur des jetons (`https://<hôte>/auth`) ;
`WATERFALL_KEYCLOAK_BACKCHANNEL`, celle par laquelle le serveur de Next l'atteint, la même par
défaut ; `WATERFALL_FRONT_ADDRESS`, l'adresse du front, sous laquelle est l'adresse de retour ;
`WATERFALL_FRONT_CLIENT_SECRET`, le secret du client `waterfall-front` ; `WATERFALL_REDIS_URL`,
le Redis des sessions. Une variable qui manque fait échouer la première connexion, en la nommant ;
`next build` et le mode `mock` n'en lisent aucune. `openid-client` refuse toute adresse de
Keycloak qui n'est pas en HTTPS, celle de la page de connexion comprise : sur la plateforme de
service, Keycloak est servi en HTTPS par un frontal à autorité locale, à laquelle le front se fie
par `NODE_EXTRA_CA_CERTS` (« Commandes », #680).

### Les pages système : lecture, panne et « introuvable »

Les pages système sont des pièces de la coquille (`frontend/src/app/`,
`frontend/src/components/system/`). Une lecture dont un écran ne peut se passer passe par
`readOrFail` de `frontend/src/api/problem.ts`, qui rend ses données ou lève : un 404 mène à l'écran
« introuvable » unique (`not-found.tsx`), qu'une adresse inexistante et une lecture refusée
atteignent sans distinction (WF-ADM-0110) ; l'API injoignable lève `Unreachable` — `fetch` rejeté,
ou une passerelle qui répond 502, 503 ou 504 sans l'enveloppe du contrat — ; un 503
`COMPONENT_UNAVAILABLE` dont l'enveloppe nomme un composant du contrat (`params.component`, un
`PlatformComponent`) lève `ComponentUnavailable`, la panne de ce composant (WF-EXP-0040, #2265) ; et
toute autre réponse — une enveloppe 503 sans composant reconnu comprise — `UnexpectedAnswer`. Une
lecture dont l'écran se passe passe par `readUnlessRefused`, à côté
: elle ne rend rien sur les refus qu'il attend — un statut, et le `code` de l'enveloppe quand le
statut ne dit pas lequel —, et suit la même règle pour le reste. L'écran de panne (`error.tsx` dans
la coquille, `global-error.tsx` quand le layout racine échoue) ne reçoit en production que le
`digest` de l'erreur levée côté serveur : `Unreachable` porte `UNREACHABLE_DIGEST`, qu'il annonce
comme tel, `SessionLost` `SESSION_LOST_DIGEST`, qui mène à la connexion sans clic, `SignedOut`
(un 401) `SESSION_REQUIRED_DIGEST`, qui y mène par un lien (`loginHref`), `ComponentUnavailable`
le composant, préfixé de `WATERFALL_COMPONENT_UNAVAILABLE;` (`componentDigest`), que l'écran nomme
dans les mots du catalogue (`enums.PlatformComponent`) — un digest dont le composant n'est pas du
contrat reste l'erreur inattendue —, `UnexpectedAnswer` l'identifiant de corrélation de l'enveloppe, préfixé de `WATERFALL_CORRELATION;` pour qu'aucune
valeur de l'API ne prenne un sens pour Next (`NEXT_REDIRECT;…`), et qu'il affiche en référence sans
le préfixe (`failure.ts`). Sans enveloppe, ou sans `correlation_id`, la référence affichée est le
digest que Next calcule, celui de ses propres journaux. Un écran ne dit jamais « vide » sur une
réponse qu'il n'a pas lue. Quand la session est illisible, la navigation garde l'écran d'état
(WF-ADM-0130). Chaque segment qui lit l'API a son `loading.tsx`, le squelette `ScreenSkeleton`, à la
densité de ses écrans, que le `loading.tsx` lit dans la table des densités — un écran d'une autre
famille que son segment a le sien, et l'écran aéré ne saute pas à son arrivée (#3269) —, qui
porte un `role="status"` nommé — un lecteur d'écran ne l'annonce pas toujours ; la réponse est alors
diffusée, et « introuvable » répond 200 et non 404 — un 404 doux, que Next marque `noindex` : le
statut part avec le squelette, avant que la page sache l'objet introuvable. Il est le même pour
toute adresse introuvable, ce qui compte ici. Chaque état vide — aucun projet, projet sans révision,
référentiel incomplet — se montre sur un exemple nommé du contrat (`empty`, `incomplete`).

### L'accueil : la liste des projets

L'accueil, `/`, est la liste des projets (`frontend/src/app/(home)/`, un groupe de routes pour qu'il
ait son squelette sans en donner un à toutes les pages) : filtrée par défaut sur les projets dont
l'utilisateur est contributeur, par le filtre du contrat (`is_contributor`) : un filtre, jamais une
restriction de lecture (WF-PRJ-0060). L'écran est aéré (`PageHeader` en densité `airy`) et sa table
tient dans une carte, `SectionCard` « Liste des projets », dont « Créer un projet » est la commande
principale, pleine, à la droite du titre — pour la session qui porte la permission de créer un
projet, aucune autre n'en a l'offre. Le filtre est une pastille « Mes projets (par défaut) » sous la
barre de la table, que l'on ôte, et un champ « Projets » du panneau des filtres ; l'ôter écrit
`?is_contributor=false`, sous le nom du contrat (`frontend/src/navigation/home.ts`), et une adresse
qui ne dit rien vaut le filtre. Il n'est jamais gardé, ni dans l'adresse ni dans les préférences de
la grille : à la connexion, l'utilisateur voit ses projets (WF-IHM-0120). La pastille et le champ ne
sont offerts qu'à une session qui porte `all_projects_read` (WF-ADM-0110) : levé pour un autre, le
filtre rendrait la même liste, et la pastille promettrait ce qu'elle ne fait pas (WF-IHM-0090,
#522) ; sans cette permission, l'accueil reste filtré quoi que dise l'adresse —
`?is_contributor=false` compris, la page demandant `is_contributor=true` —, sans pastille ni champ,
et la description de la carte dit seule que la liste tient les projets dont la session est
contributeur ; le choix du projet mène alors à l'accueil plutôt qu'à la liste levée. La barre
latérale et le fil d'Ariane mènent à la liste filtrée, le choix du projet à la liste levée, « Tous
les projets » ; `/projects`, l'ancienne adresse, renvoie à l'accueil. Les projets sont une
configuration de plus de la grille dense (`project-list-grid.tsx`, préférences sous la clé
`projects`) : le libellé, lien qui ouvre le projet, le code, l'état par sa pastille et la date de
modification, chaque colonne triée par le serveur (`sort_by`), cherchée par lui sur le libellé et le
code (`search`), filtrée par état — un champ du panneau qui n'écrit que l'adresse (`states`) — et
par période sur la dernière modification (`from`, `to`, EP-02/L42e) : deux jours saisis dans l'heure
locale du lecteur, envoyés comme les instants du début du premier et du début du lendemain du
dernier, la fin exclue. Les états se disent comme le filtre des projets, par des pastilles : une
adresse qui ne nomme aucun état demande ceux que le compte a gardés, à défaut les états par défaut,
Créé, Chiffrage et En cours, dits « (par défaut) » ; `states=all` les lève et demande les six,
là où le contrat, sans `states`, ne rendrait que les projets en cours (WF-PTF-0010) : l'adresse fait
foi. Une période que le serveur refuse — une fin qui précède le début, 422 `VALUE_OUT_OF_RANGE` sur
`/query/to`, `params.minimum` le début donné — est dite à son champ, le début nommé par son jour
local, qui prend le focus chaque fois que la liste revient refusée, comme une borne d'une colonne de
nombres (`range-filter.tsx`) ; la liste n'est pas lue, et une phrase tient la place de la grille. Sa
ligne de totaux dit combien de projets le serveur retient, et elle mène aux autres pages par
`ListPages` ; une page demandée au-delà de sa fin le dit, et ramène à sa dernière page : seule une
liste qui ne tient aucun projet, sans état, période ni
recherche, se dit vide. Les écrans du projet lui-même — le projet, ses paramètres avec ses
sous-projets et ses contributeurs, son cycle de vie — exercent la sortie du cycle de vie
(`ExitCommand`), irréversible, confirmée dans la page avant que son action serveur ne la demande, la
modification du projet, sur ses paramètres (EP-02/L44a, plus bas), et, sur ses paramètres encore,
les commandes de ses sous-projets et de ses contributeurs (EP-02/L44b, plus bas). Les tables de
données des paramètres sont trois grilles denses (#301, `settings-grids.tsx`), chacune avec sa clé
de préférences et ses noms dans l'adresse (`breakdown_`, `subproject_`, `contributor_`) : le
lotissement, une grille arborescente — chaque lot, ses postes sous lui, leurs livrables sous eux —,
dans l'ordre saisi, qui ne se trie pas et se plie, cherchée par le serveur sur ses libellés
(`breakdown_search`) et filtrée par nature (`breakdown_kinds`, EP-02/L42f) — lue ainsi, sans
compteur (`lock_version` nul, `WorkBreakdownReading`), ses lots et ses postes ne montrent que ce qui
est retenu, ce qu'elle dit, et une telle lecture ne se renvoie jamais à `setWorkBreakdown` ; sa
ligne de totaux compte les seuls éléments retenus, par nature (`is_match`, #574), et il se saisit
dans sa grille comme le projet liste `update_work_breakdown`, indisponible aussi pendant un
traitement de fond (EP-14/L42s ; `breakdown-commands.tsx`, EP-14/L44c) : chaque geste — un élément
ajouté, renommé ou supprimé, du menu d'une cellule sur sa ligne ou de la barre sur la ligne de la
cellule active (`RowCommands` de `DenseGrid`) — envoie le lotissement entier depuis sa lecture
entière, que la page relit quand la grille le lit filtré, l'élément ajouté sans identifiant ; une
suppression se confirme, celle d'un lot ou d'un poste en disant que les tâches qui le portent
restent et perdent leur rattachement (WF-PLA-0170) ; un refus par champ qui vise l'élément du
dialogue est dit à son champ, celui qui en vise un autre le nomme ; les sous-projets, cherchés par
le serveur sur leur code et leur libellé (`subproject_search`), triés par lui sur chaque colonne
(`subproject_sort_by`) et filtrés sur leurs coûts réels (`subproject_has_actual_costs`) ; les
contributeurs, cherchés par le serveur sur le nom du compte (`contributor_search`), triés par lui
sur chaque colonne (`contributor_sort_by`), filtrés sur leur qualité (`contributor_kinds`, `kinds`
du contrat), un bouton pressé par qualité (`ValuesFilter`, `filters.ts`), et sur l'état du compte
(`contributor_is_active`) — une colonne booléenne se filtre par un choix (`ChoiceFilter`), `true` ou
`false`, aucun retenant toutes les lignes (`readBoolean`) ; chaque table plate se filtre ainsi sur
chacune de ses colonnes (WF-IHM-0130, EP-02/L42e). Les volumes du §4.6.2 — dix sous-projets,
cinquante contributeurs par projet — tiennent en une page. L'historique des états, une liste de
lecture, reste une table simple. Les sous-projets offrent leurs commandes comme le projet liste
`update` (`subproject-commands.tsx`) — absente, rien ; indisponible, « Nouveau sous-projet »
présenté `aria-disabled` avec ses conditions ; disponible ou non, sur chaque ligne, la modification
et la suppression comme la ligne les liste (`Subproject.available_commands`, EP-14/L44e) — absente,
rien ; indisponible, présentée `aria-disabled`, décrite par ses conditions, et un appui les dit dans
la région de la liste (`UnavailableCellCommand`) : un projet clos ne liste plus aucune commande, ni
la sienne ni celles de ses lignes (US-0702/L3), et l'écran n'en présente aucune ; le refus d'un
appel direct, `project_not_terminal`, reste au serveur (WF-IHM-0090). La création et la modification
ouvrent le formulaire du référentiel (`ReferenceForm`), le code et le libellé exigés, un code déjà
porté (409 `ALREADY_EXISTS`, `fields[]`) dit au champ, son porteur nommé par le libellé que le refus
donne (`conflicting_object_label`) ; la suppression, confirmée dans la page, est indisponible — ou
refusée par le serveur, 409 `STATE_FORBIDS_OPERATION` nommant la première condition qui manque, dit
au-dessus de la liste (`Reactivations`) — pour un sous-projet qu'une révision marquée cite
(`subproject_not_cited`, §4.4.1), auquel des coûts réels sont imputés
(`subproject_without_actual_costs`, WF-PRJ-0050) ou que portent des lignes de devis de la révision
en cours (`subproject_without_estimate_lines`, EP-14/L42q) ; l'écran n'en déduit rien de
`has_actual_costs`. Lue indisponible faute de cette seule dernière condition, la suppression mène de
plus, à une session qui lit le devis, au devis de la révision en cours filtré sur le sous-projet
(`subproject_id`, `leadsToEstimate`), le lien dit dans la région de la liste avec ses conditions ;
il n'est pas offert quand manque aussi la citation ou les coûts, qu'aucune ligne déplacée ne lève.
Il atteint les lignes de la structure principale, jamais celles d'une autre structure, la structure
propre d'un risque. Les lignes ne sont nommées une à une que lorsque le serveur refuse une
suppression lue disponible (`params.estimate_lines`) : chacune par son numéro dans sa structure, tel
que la grille le montre, et son libellé, dans la phrase jusqu'à cinq, en liste sous elle au-delà,
une liste nommée qui défile, hors de l'alerte, qui la lirait d'un trait, et décrite par sa phrase
(`LINES_IN_SENTENCE`, `OutcomeNotice`, #765), et le refus rappelle qu'une ligne de provision change
de sous-projet par son risque (`problemMessage`, WF-DAT-0080) ; le refus donne la structure d'une
ligne par son identifiant (`structure_id`), non par son libellé, que l'écran ne lit pas
(`structure_label`, demandé dans #764). Les contributeurs, comme le projet liste
`manage_contributors` (`contributor-commands.tsx`), se modifient en une liste entière dans un
dialogue (`setContributors`) : la qualité de chacun, son retrait, et l'inscription, une à une, des
propositions du serveur (`listContributorSuggestions`, WF-PRJ-0070), chacune avec le nœud et les
rôles qui la font proposer (`org_node_label`, `resource_role_labels`), inscrite active comme le
serveur le dit (`is_active`), rien n'étant écrit avant l'enregistrement ; une liste sans chef de
projet est refusée avant toute demande (WF-PRJ-0060), un refus par champ (`/contributors/<n>/…`) —
un compte inconnu (`UNKNOWN_USER`) ou désactivé (`USER_INACTIVE`) — dit à la ligne du compte qu'il
désigne, en le nommant. L'écriture part d'une lecture entière, avec son compteur : quand la grille
lit la liste filtrée, la page la relit entière pour le dialogue, et la grille garde ce que sa
lecture retient. Une modification répondue remplace sa ligne, une suppression l'ôte, une liste
répondue remplace celle d'une lecture entière, tant que leur compteur est plus récent, la page relue
disant ce que le service a gardé ;
une création n'ajoute aucune ligne, la page relue la range. Une réponse ne ferme que le formulaire, la confirmation ou le
dialogue d'où elle est partie, jamais un autre ouvert depuis (compteur d'ouvertures, `key`, #672).
La commande qui ouvre une modification attend, inactive, `aria-busy` et décrite par « Enregistrement
en cours… », la réponse d'une écriture du dialogue fermé, quelle qu'elle soit, pour que le dialogue
s'ouvre sur la version qu'elle apporte (#661, #734) : celle d'un sous-projet tant que la
modification de ce sous-projet est en route, les autres lignes restant offertes (`onWriting` de
`ReferenceForm`, `writing` de `SubprojectCommands`, la description cachée mais pour un lecteur
d'écran dans la cellule, son titre la disant à l'œil) ; celle des contributeurs tant que la liste
s'écrit — le compteur d'ouvertures y reste en garde-fou. Les pièces communes du référentiel
(`CommandedList`, `useAnswered`) étant liées à ses natures d'objet, ces deux listes ont les leurs,
sur les mêmes pièces : le formulaire, la commande d'une cellule, la région des refus.

### La création et la modification du projet

Le projet se crée et se modifie dans la maquette (EP-02/L44a, décision de l'auteur du 2026-10-08,
#513, #524 ; `project-form.tsx`), par le formulaire du référentiel (`ReferenceForm`, qui écrit aussi
un autre objet que ceux du référentiel et saisit une date de planning). L'accueil offre « Créer un
projet » à une session qui porte la permission de le créer (`project_create`, `platformOffer`,
WF-ADM-0100), indisponible, décrite par le refus qu'elle rencontrerait, tant que le référentiel
minimal est incomplet (`getReferenceReadiness`, WF-CYC-0120) — l'accueil nomme chaque prérequis
manquant, la catégorie de main-d'œuvre active et, depuis EP-14/L42p, la catégorie de provision pour
risques active (`active_provision_category`) comprises, et mène aux paramètres de coûts, comme le
refus `REFERENCE_INCOMPLETE` les nomme sous le formulaire ; le formulaire prend ce que
`ProjectCreate` prend — le libellé, exigé (WF-PRJ-0080), le code, qui peut attendre la commande
(WF-PRJ-0010), la description — et mène à l'écran du projet que le serveur a créé, que le faux back
sert à son adresse, avec ses propres exemples — le projet « created », sans révision —, tant que
l'accueil est encore montré : une réponse arrivée après qu'on l'a quitté ne remplace pas la
navigation choisie. Une réponse arrivée après « Annuler », le dialogue fermé mais l'accueil toujours
montré, y mène quand même : c'est la seule façon de dire le succès, que la liste simulée ne montre
pas, et fermé pendant l'attente, le dialogue ne fait rien taire. Les paramètres du projet présentent
son identité et ses faits — le libellé, le code, la date de réception de la commande, la
description, le taux d'inflation et la probabilité de gain — et leur modification (`updateProject`)
comme le projet liste sa commande (`update`) : absente, disponible, ou indisponible avec ses
conditions — un projet terminal (WF-CYC-0100). Les deux taux se saisissent en pourcentages et
partent en rapports du contrat, la virgule déplacée sans flottant (`editablePercent`,
`percentRatio`) ; la probabilité de gain suit sa propre commande (`update_win_probability`,
EP-14/L44e) : indisponible — à partir de En cours, `project_before_in_progress` manquante
(WF-PRJ-0090) —, elle est montrée figée (`control: "fixed"`), ses conditions dites sous elle, et
n'est pas envoyée ; une date ou un texte laissés vides partent nuls, une date à moitié saisie, que
son champ rend vide (`validity.badInput`), est refusée avant tout appel. Une réponse ne ferme que
l'ouverture du formulaire d'où elle est partie : arrivée après que le dialogue a été fermé puis
rouvert, elle s'affiche et laisse le nouveau dialogue ouvert (#660) ; et tant qu'une modification
envoyée d'un dialogue fermé est en route, « Modifier le projet » est inactive (`aria-disabled`,
`aria-busy`, décrite par « Enregistrement en cours… », `WritingNote` ; `onWriting` du formulaire) :
rouvert, le formulaire écrirait depuis la version que sa propre réponse remplace, et le serveur le
refuserait (412) — il s'ouvre sur la version qu'elle apporte (#661, #673). Elle se libère à la
réponse, quelle qu'elle soit — un succès, un refus, une action serveur rejetée, l'API injoignable —
; une action serveur qui ne répond jamais la laisse inactive jusqu'au rechargement de la page. Le
compteur d'ouvertures reste, en garde-fou : la commande attendant l'écriture, aucune autre ouverture
ne vient avant la réponse. La réponse prend la place des faits lus tant qu'elle est plus récente que
le projet lu (`lock_version`), la page relue ; la section est remontée quand
l'écran montre un autre projet. Un refus par champ se dit au champ, tout autre sous le formulaire —
la probabilité figée entre-temps (409 `STATE_FORBIDS_OPERATION`, la condition nommée), la version
périmée avec l'offre de relire ; un taux hors de ses bornes (422 `VALUE_OUT_OF_RANGE`,
`params.minimum` ou `maximum`, en rapports) se dit au champ, la borne en pourcentage comme le champ
la saisit (`ratioPercent`) ; le code déjà porté par un autre projet (409 `ALREADY_EXISTS`,
`fields[]`) se dit au champ, le projet qui le porte nommé par le libellé que le refus donne
(`conflicting_object_label`), l'écran ne montrant pas les autres projets — génériquement sans lui
(`kind="project"`, EP-02/L42g). Le cycle de vie dit le prochain état du projet, son déclencheur et
les conditions qui lui restent, une par une (`getProjectNextState`, `NextStateFacts`, WF-CYC-0050),
qu'aucune commande ne mène à Chiffrage ni à En cours (WF-CYC-0020) ; le déclencheur est l'un des
deux faits que le contrat énumère (`LifecycleTrigger`), dit par son catalogue
(`enums.LifecycleTrigger`). Un projet qu'aucun fait ne mène plus loin — le serveur répond sans
prochain état ni déclencheur — le dit : en cours, seules ses sorties restent ; terminal — un état où
mène une sortie (`EXIT_STATES`) —, il est clos, et aucun état ne le suit (WF-CYC-0080). Le prochain
état et l'historique des états sont chacun une carte de section, dans la colonne aérée (US-2130) ;
les sorties restent à droite du titre de l'écran, à contour. L'écran des révisions suit la même
présentation sans changer de structure (EP-27 la refond) : une carte par section, « Ouvrir une
révision en cours » — la commande pleine, que `RevisionHistory` reçoit par `creation` — à droite du
titre de la carte de l'historique, les commandes de la révision lue à droite du titre de l'écran.

### Les périodes d'une liste

Une période d'une liste prend l'une des trois formes du contrat (`period.ts`), toutes saisies dans
le même filtre (`PeriodFilter` de `frontend/src/components/grid/`) : deux jours de planning, bornes
incluses, que le serveur reçoit tels quels — les pièces des coûts réels — ; deux jours locaux tirés
en instants, la fin exclue — l'accueil — ; deux instants saisis à la minute en heure locale, la fin
exclue — le journal d'audit. Seul le navigateur connaît son fuseau : les champs d'instants montrent
l'adresse, et le bouton envoie, une fois la page hydratée ; un côté laissé intact part tel que
l'adresse le nomme. Le refus d'une période inversée, la règle de toute période du contrat, est dit
au champ de la fin, le début nommé tel que son champ le montre.

### Le contexte d'un écran de projet

Un écran de données de projet lit son contexte par `readAddress` de
`frontend/src/components/context/reading.ts` — projet, révision, filtres actifs, lus une
fois par requête — et le montre par `ContextBanner`, au-dessus de son `<main>`
(WF-IHM-0020). La lecture porte `edits`, les commandes `edit_*` de la révision que
l'appelant peut exercer (`read-only.ts`), qu'un écran reçoit plutôt que de les déduire. Ce qu'une
grille offre — la saisie, les gestes, le collage — ne se lit pourtant pas là, mais dans la
structure qu'elle lit (`screen.commands`, de `grid-screen.ts`, d'après
`available_commands`) : sa propre commande — `edit_planning` pour le planning —, car la phase du
projet n'est pas celle de la révision (le devis de la principale d'un projet En cours est en
lecture seule, le reste à engager non, le devis d'un différentiel ou d'un risque non plus) et qu'un
chiffreur peut saisir le devis sans toucher au planning. Le planning et le devis lisent la
structure que nomme l'adresse (`structure`, `components/context/structure.ts`) — la principale
par défaut, un différentiel d'avenant, le devis propre d'un risque —, que la révision liste
(`listCostStructures`), une autre étant introuvable ; le reste à engager, les chronologies et
l'arborescence, la seule principale (`GridReading.chooses`). Le bandeau nomme la structure lue,
sa nature quand ce n'est pas la principale, et offre les autres de la révision
(`StructureChoice`) ; ce paramètre est celui de la grille : les liens entre fonctions ne le portent
que du planning au devis et du devis au planning, qui lisent la même structure, et jamais vers un
autre écran, qui retombe sur la principale (`readsStructure`, `navigation/context.ts`, #1220). La
grille se monte par structure (`key`), et le squelette ne s'offre que sur la principale
(US-0500). `readOnly` —
révision marquée, ou aucune commande `edit_*` disponible — ne sert qu'à l'avis du bandeau. Une
valeur sous enveloppe `Computable` s'affiche par `ComputedIndicator`, jamais sans la date de son
`CalculationContext`, et non calculable avec son motif, un code que le catalogue rend
(`enums.NotComputableReason.*`, `indicator.tsx`).

### Les courbes

Une courbe est une figure de `Chart` (`frontend/src/components/chart/`, US-0240) : Apache ECharts,
importé pièce à pièce et dessiné en SVG, son option `aria` active ; sa légende la nomme, le dessin
est une image que décrit une phrase du catalogue, et ses valeurs sont un tableau sous lui,
l'alternative textuelle (WF-IHM-0100). Le composant client propre à la courbe (`index-chart.tsx`,
`milestone-chart.tsx`, `curve-series-chart.tsx`, `workload-chart.tsx`) lui remet son option,
construite dans une palette : ECharts écrit ses couleurs dans les attributs de son SVG, où une
variable CSS n'atteint pas, et les jetons `--chart-1` à `--chart-4`, `--muted-foreground`,
`--foreground`, `--input`, `--border`, `--background` et `--card` y arrivent par des sondes cachées que le
navigateur peint dans le mode affiché ; un changement de mode, du poste ou forcé par le compte
(`data-theme`), redessine la courbe. Elle se dessine d'un coup, sans animation, et une légende y est
inerte : un clic, à la souris seule, ne cache aucune série. `curve` nomme chaque courbe à son
dernier point tracé, quel que soit leur nombre — pas de légende, qu'une entrée par sous-projet
ferait déborder sur le tracé —, les noms qui se chevaucheraient écartés, et la distingue aussi par
sa couleur et son trait, et par son symbole quand le compte demande les motifs ; un plan de charge est un histogramme empilé (`stackedRoles`
de `workload/stacked-load.ts` : une barre par mois, divisée par rôle), dont
l'infobulle d'un mois liste les rôles et leurs heures (`monthTooltip`, libellés échappés) ; celui du
projet n'a pas de droite de capacité (#375) mais porte au sommet de chaque barre le total du mois
que le serveur rend (`monthly_totals`, `monthTotals`), comme celui du portefeuille qui porte aussi,
en pointillés, la capacité du périmètre (`capacity_monthly_hours`), la table des rôles, de leur taux
et de leurs signaux étant sous le graphique ; les liens vers le plan de charge ouvrent une base
(`basis`, `workload/workload-basis.ts`) : le reste à engager `current_remaining`, le devis
`reference_budget` d'un projet en cours ou terminé qui a une référence, `current_remaining` sinon ;
le lien du reste à engager vers ce plan est une icône seule (`aria-label`, `title`), le titre de
l'écran et les totaux de sa grille ne tenant dans la fenêtre de 1280 points qu'à ce prix
(`remaining.spec.ts`) ; une courbe sans point tracé n'a pas de nom sur le dessin, son tableau la
nomme ; une série de barres (`bars`) porte le motif du symbole de son rang, que la légende montre, quand
le compte le demande ; `timeAxis` gradue un axe de temps au premier de chaque mois que `monthTicks` tire
des instants qu'il montre — tous les deux, trois, six mois ou chaque année sur une longue plage,
l'année seule alors, ou tous les deux, cinq, dix ans, sur les années multiples du pas (#415) —,
écrits dans la langue du poste, dans son fuseau ou en UTC pour un axe de dates de planning, que
`planningInstant` place à leur minuit UTC, l'option de la figure disant alors `useUTC`. Une courbe
trace les chaînes de l'API telles quelles — ECharts en tire une position —, une valeur non
calculable étant un trou, un cumul d'événements datés — valeur acquise, coût réel — en escalier
(`step`), une marche verticale par deux points à la même date, et le tableau les écrit par
`src/i18n/format.ts`, les zones par `Signal`. La matrice des risques est un nuage de bulles
(`risks/risk-bubble-chart.tsx`, `RiskBubbleChart`, partagé par le projet et le portefeuille) : un
`scatter` par état de risque — le cercle, le losange, le triangle, que la légende montre —, sur
seize `markArea` d'une série à part, une par case, que `ChartPalette.zones` colore des jetons des
zones (`ZoneProbes` de `signal/signal.tsx`, le seul fichier qui nomme ces jetons) ; une zone se
nomme dans son aire quand sa bande a la place d'une ligne, et son bord a un trait à elle (plein,
tireté, pointillé), la couleur ne la portant jamais seule. Les axes vont du zéro à la fin du dernier
niveau — que le serveur laisse sans borne haute, et qu'ECharts ne prolonge pas pour une aire —, à la
bulle la plus haute près ; une bulle est à la probabilité et à la part de gravité exactes de son
point, et sa taille, bornée, suit la gravité en montant ; l'infobulle dit le risque, son projet au
portefeuille, et le clic (`onPoint` de `Chart`, par l'`id` de la donnée) ouvre le détail du risque
dans l'adresse d'un projet, ou le projet d'un point que `can_open` permet d'ouvrir. La table du
décompte par case (`RiskCountsTable`, `cells`) est celle des valeurs de la figure. Aucune bulle
n'est atteignable au clavier, et c'est dit : la grille des risques, sur le même écran (projet),
donne au clavier l'accès aux mêmes données, par le lien du libellé de chaque ligne, et au
portefeuille le tableau des plus lourds et `/portfolio/projects` y suffisent (#1253). Les axes
restent linéaires, aux valeurs exactes (WF-IHM-0100), même si la bande de 0 à 1 % de gravité n'y
mesure qu'une quinzaine de points : une échelle par morceaux fausserait la lecture des positions.
`folded` de `Chart` ne vaut que pour l'état initial du dessin — un bouton l'affiche et le replie
ensuite —, et un changement ultérieur de la prop ne le plie ni ne le déplie. Une figure qui reçoit
`exported` offre la commande « Exporter en PNG » (WF-IHM-0130) : `exportPng` la redessine dans une
instance hors écran, en rendu canvas, à la taille d'une image, son titre et sa provenance
(`useProvenance`) — projet, révision du calcul, ce sur quoi la figure est calculée par ailleurs
(`detail` : la base et le nœud d'organisation filtré du plan de charge), date de calcul, écrite dans
l'heure du poste au moment de l'export — en tête, repliés à la largeur de l'image (`wrapLines`), la
figure descendue de la hauteur de leurs lignes, sur le fond de la charte, puis libère l'instance. Un
choix qui change ce qu'une courbe lit — les délais de paiement, la base et le nœud d'organisation du
plan de charge — est un paramètre de l'adresse, que le serveur envoie à l'API : le front ne filtre
ni ne décale rien.

**La présentation commune** (US-2160, #3097) : couleurs pleines ; barres minces (`bars` : la moitié
de la place du mois, 28 points au plus), chaque part arrondie et séparée des voisines par un filet
de la couleur de la page ; axe des valeurs sans trait ni graduation, lu par une grille horizontale
en tirets clairs (`valueAxis`), aucune ligne verticale (`timeAxis`) ; légende en haut à gauche, une
pastille de la couleur de chaque série ; infobulle en carte (le jeton `--card`, la bordure et
l'ombre au ton de `--border`) ; la série sous le pointeur ressort, les autres s'estompent. `Chart`
pose la légende et l'infobulle (`presented`), à l'écran comme dans l'image exportée ; les axes et
les séries viennent des fonctions communes que chaque graphique appelle. L'échelle ne se rompt ni
ne se zoome : l'infobulle et la table donnent les valeurs qu'un mois très chargé tasse. **Les
motifs** — ceux des barres, les symboles des points, et la légende qui les montre — ne se dessinent
que si le compte les demande (`chart_series_patterns` de `DisplayPreferences`, réglé sur « Mon
compte », désactivé par défaut) : la mise en page racine lit la préférence avec le compte et la
passe par `ChartPatternsProvider` (`chart/patterns.tsx`) ; `Chart` la lit seul et la met dans la
palette (`ChartPalette.patterns`) que reçoit l'option, ce qui fait suivre l'export à la préférence
de qui exporte. Le Gantt et les chronologies gardent leurs marques (`readPalette` sans préférence).

Le plan de charge du projet (`…/workload`, FBS-4.4.4) est branché sur le service (EP-07, US-1520) :
la page ne porte plus la note de la maquette (`MockupNotice`), `getProjectWorkload` rend la charge,
la capacité de chaque rôle, les totaux sans trou et la zone de chaque mois, et l'écran n'offre que
les bases que le projet admet — celle de la référence quand il a une révision de référence, celle
d'une révision marquée quand il en a une, la révision en cours toujours, seule sans l'un ni
l'autre ; l'étalement et la date de calcul sont ceux du service, le front ne calcule rien. Les
parcours de `workload.spec.ts` portent `@shared`, et `frontend/help/fr/FBS-4.4.4.md` dit ce que le
service fait.

### L'écran des indicateurs

L'écran des indicateurs d'un projet lit ses indicateurs et ses courbes dans la révision de sa route
(`revision_id`) — ceux d'une révision marquée tels que son marquage les a conservés —, ou à la date
que l'adresse demande (`as_of`), jamais les deux, que l'API refuse ensemble ; une offre marquée
avant l'état En cours, qui n'en a conservé aucun, est refusée comme un projet qui n'est pas en
cours, et l'écran le dit. Un avis en tête nomme, des indicateurs et de l'évolution des indices,
celui qui est calculé sur une autre révision que celle du bandeau, et laquelle — l'évolution,
toujours au jour sur la révision en cours (`ComputedElsewhere`) ; une courbe nomme la sienne dans
l'image qu'elle exporte. Le sous-projet de l'adresse, celui que le bandeau montre (WF-IHM-0020),
restreint ce que l'API lit pour lui (`scope`, WF-IND-0020) — les indicateurs, l'évolution des
indices, les coûts cumulés et les courbes de valeur acquise (EP-02/L42e) —, sauf le diagramme
temps/temps, calculé pour le seul projet : il suit des jalons, qu'un sous-projet n'a pas
(WF-IND-0020). La pastille du bandeau le dit (`restricts` de `ContextBanner`, comme pour la grille
du reste à engager, #459), et le suivi des jalons dit qu'il porte sur le projet entier
(`WholeProject`). Un sous-projet que le projet n'a pas, refusé par 422 `UNKNOWN_SUBPROJECT` sur
`/query/scope`, est dit comme les indicateurs d'un projet qui n'est pas en cours, jamais lu comme
des indicateurs nuls ; une courbe sans point dit qu'elle n'a rien à tracer plutôt que de tracer un
zéro, et une série sans point parmi d'autres qui en ont le dit sous le graphique — le budget de
référence d'une maille qu'aucune référence ne budgète — ; une courbe vide non décalée n'offre pas de
la décaler, et, décalée, garde la commande qui retire le décalage.

Contre le service (US-1730, WF-ARC-0070-A), `e2e/indicators.spec.ts`, étiqueté `@shared`, tient
l'écran à ce que l'API répond pour PRJ-001 : le parcours lit par l'API, sous le jeton du compte de la
course (`e2e/indicator-answers.ts`), les opérations que l'écran lit — pour la révision en cours, la
révision 101 marquée, un sous-projet, « hors sous-projet », une date `as_of`, les délais de paiement —
et compare chaque chiffre des cartes (montants, parts, indices, zones, projections), les points des
tableaux de l'évolution des indices, des coûts cumulés et de la valeur acquise à la réponse, dans
chacune de ces lectures — la révision en cours (projet entier, sous-projet, hors sous-projet), la
révision 101, la date `as_of` (l'évolution des indices est celle du projet, quelle que soit la date),
les délais de paiement, dont les décaissements par mois doivent exister — et ceux du temps/temps, du
projet entier quel que soit le périmètre ; chaque comparaison exige d'abord que la réponse porte au
moins un point, pour qu'un tableau vide face à une réponse vide ne passe jamais. Les chiffres sont
écrits par `src/i18n/format.ts` sans somme ni arrondi du parcours. L'offre 100 et une date
avant tout marquage, refusées 409, sont dites ; les trois exports PNG nomment le projet. Le faux
back sert un exemple quelle que soit l'adresse : ces parcours n'y jouent pas (`inService`).

### Les chiffres clés en cartes

Les chiffres clés d'un écran se présentent par `FiguresCard` (`src/components/figures-card.tsx`),
jamais en ligne dans un `<dl className="flex …">` posé sur la page : une carte est une région nommée
par son titre (`role="region"`, `aria-label` du titre), qui porte la date de calcul quand la réponse
a un contexte (`context`, `CalculationDate`, WF-IHM-0020) et ses chiffres dans une liste de termes
(`FiguresList`, un `dl`) — le nom, puis la valeur, pour un lecteur d'écran. Les cartes d'un écran
sont rangées dans `FiguresGrid`, qui passe à la ligne selon la largeur ; les cartes y partagent la
largeur, et une carte seule s'étire sur toute la rangée. La date de calcul se répète sur chaque
carte d'une réponse qui en a une : chaque région se lit seule, avec son titre et sa date, sans qu'il
faille remonter à une autre. Elle se place sous le titre, jamais à sa suite sur la même ligne :
écrite après l'hydratation (`LocalTime`), elle ferait sauter la carte d'une ligne. Une carte porte
un bloc de chiffres qui se lit ensemble — les totaux, une ventilation en liste, la couverture des
risques —, jamais la page entière. Les valeurs, leur format et leurs signaux (`Signal`, WF-IHM-0070)
sont ceux que l'écran avait : la carte n'ajoute que l'encadré. `IndicatorCard` (écran des
indicateurs) la réemploie en gardant son aspect d'avant (`spacious`), les courbes et les tableaux
qu'elle porte ayant besoin de la place ; les autres cartes sont compactes, pour que la grille garde
ses totaux dans la fenêtre. Les six écrans qui la suivent sont les risques, le devis, le reste à
engager, les coûts réels et les deux vues du portefeuille, performance et risques d'une part, valeur
de l'autre ; le bandeau du contexte de lecture, une bande d'information, n'en est pas. Sur un écran
rempli (`Screen fill`), la ligne des totaux de la grille reste dans la fenêtre sous les cartes, à
1366 et à 911 de large sur 768 de haut : `e2e/grid-frame.spec.ts` le vérifie, risques compris : le
graphique de leur matrice, entre les cartes et la grille, démarre replié (`folded` de `Chart`), un
bouton l'affiche et le replie, car dépliée sa hauteur (288 points, `h-72`) ne laisse pas les totaux
dans la fenêtre à 768 de haut (#1252). _Contrôle_ : la revue ;
`src/components/figures-card.dom.test.tsx`, `e2e/accessibility.spec.ts`.

### Les grilles

Une grille est la grille dense de `frontend/src/components/grid/` (US-0110), configurée par écran :
une `GridConfig` (`columns.ts`) nomme la clé de ses préférences, stable, ses colonnes — clé, libellé
du catalogue (`grid.columns.*`), format, alignement, largeur par défaut, celles de ses cellules que
le serveur calcule, figée ou non, la colonne du contrat qu'elle montre (`contract`) — celle par
laquelle le serveur la trie et sur laquelle un collage la vise —, et, pour une colonne étroite,
l'icône qui tient lieu d'en-tête et que son libellé nomme, ou ce que rend sa cellule en place de la
valeur formatée (`render`) — et, s'il y en a un, son arbre (niveau, icône de nature par
`RowNatureIcon`). Trier est d'abord l'affaire de la grille : une grille arborescente dont les lignes
gardent l'ordre du plan n'en trie aucune (`sorts: false`), et son adresse n'en demande aucun — le
planning (§3.4, WF-IHM-0060, #525). Le devis et le reste à engager, dont le serveur ne trie que les
lignes sous chaque tâche, les tâches gardant l'ordre de l'arbre (WF-IHM-0060, #526), ne trient pas
par une colonne de la seule tâche, que le contrat accepte mais dont le tri ne changerait rien : la
colonne le dit elle-même (`GridColumn.sorts: false`), en gardant sa colonne du contrat, que vise un
collage là où la grille en prend un (le planning, le devis) — l'avancement et la fin au reste à
engager, qui n'offre ainsi que ce qui agit (dans l'esprit de WF-IHM-0090). Ni son en-tête ni
l'adresse n'en offrent le tri, et un tri par elle, dans l'adresse ou gardé par le compte, est ignoré
comme un tri inconnu (`sortColumns`). La configuration lit les lignes par des fonctions : elle se
remet à `DenseGrid` dans un composant client propre à l'écran (`estimate-grid.tsx`,
`planning-grid.tsx`), et la page, serveur, ne lui passe que des données — la structure lue et, de
chaque nœud, les seuls champs que la grille lit : ceux de toute grille (identité, version, champs
calculés, numéro, niveau, parent, nature, libellé) et ceux de ses colonnes, que nomme sa
configuration (`ESTIMATE_FIELDS`, `PLANNING_FIELDS`). La page les demande à `listNodes` (`fields`,
`nodeFieldNames` : un champ d'une facette sous son nom, `task.label`) et les projette encore
(`projectNodes`) : un serveur peut rendre plus qu'on ne lui demande — le faux back rend son exemple
entier —, et les six mille nœuds entiers pèsent six mégaoctets et demi dans la page, projetés, de
quarante-huit à soixante-cinq pour cent — le parent, par lequel l'arbre se plie, y a ajouté quatre
points ; la lecture de l'écran (`readGridScreen`) ne rend que les lignes projetées et les totaux,
jamais la réponse entière. Un champ d'une ligne qui ne dit rien — nul, ou faux pour un drapeau
(`SPARSE_LINE_FIELDS`) — ne traverse pas, la cellule le lisant comme nul, et l'identifiant du
sous-projet d'une ligne ne traverse que vers une grille qui le saisit (`withoutSubprojectIds`). Une
colonne qui lit un champ nouveau l'ajoute à cette liste : le typage de la ligne le demande, et
`projection.test.tsx` vérifie que la grille lit la même chose de la ligne projetée que du nœud
entier, et que la page demande ce qu'elle projette. Le calculé se lit cellule par cellule
(WF-IHM-0030, `computed-nodes.ts`) : un champ qu'aucune écriture ne porte — les montants, la marge —
l'est dans chaque ligne qui le porte, et sa colonne a Σ en en-tête ; un champ saisissable l'est là
où le nœud le nomme dans `computed_fields`, jamais d'après son mode ni sa nature. Une cellule
calculée est grisée, marquée Σ et nommée « Calculé » — la marque se lit sans la couleur — ; c'est un
bouton qui, cliqué ou pressé au clavier, refuse la saisie dans un Popover (`ComputedCell`,
`ComputedRefusal`) en disant ce dont sa valeur dépend, que le serveur dit : chaque colonne calculée
nomme le champ du contrat de chacune de ses cellules, et le refus appelle
`getComputedValueDependencies` pour le nœud et ce champ, par une action serveur
(`readComputedDependencies`) que la grille reçoit de son écran (`nodeDependencies`, un lecteur par
lecture de la page) — tant qu'il est ouvert seulement, et une fois par question : la lecture de la
page, le nœud et le champ. Un refus fermé ne demande rien ; rouvert après une relecture de la page,
il redemande, car les lignes qu'il nomme ont pu changer de numéro ou de libellé sans que le nœud
change de version ; un échec se redemande à l'ouverture suivante, seule une réponse est gardée. Dans
une seule région annoncée (`role="status"`, `aria-live="polite"`), présente dès l'ouverture et
`aria-busy` pendant la lecture, il dit qu'il la lit, puis les règles qui la calculent
(`enums.ComputedDependency.*`) et les lignes dont elle vient, nommées par leur numéro et leur
libellé, que la grille les montre ou non ; un refus du serveur, ou l'API injoignable, se disent par
`OutcomeNotice`. Une ligne qui dit elle-même ce dont sa valeur dépend — un risque, sa gravité et sa
provision (`Risk.computed_fields`) — le donne à sa colonne (`dependsOn`), et le refus en nomme les
règles d'emblée, sans rien demander. Le front ne lit aucune règle du noyau. Le Popover ne se monte
qu'au premier essai : une racine de Radix par cellule calculée alourdirait l'hydratation du premier
écran. La grille de planning et celle de devis sont deux configurations de ce seul composant
(`planning.tsx`, `estimate.ts`), qui partagent l'arbre, le numéro et le libellé d'un nœud
(`nodes.tsx`) et la lecture de la structure que nomme l'adresse (`grid-screen.ts`) ; le planning
demande au serveur les seules tâches (`kinds=task`). Le devis présente, d'une ligne comme d'une
tâche, récapitulative comprise, et en total, le montant à l'année de référence, avant inflation
(`base_amount`), tel que le serveur le rend, jamais le budgété ni le réestimé, inflation comprise
(WF-DEV-0020, WF-DEV-0050) ; il nomme la catégorie et le rôle d'une ligne par les libellés que le
serveur résout, l'objet actif ou désactivé (`cost_category_label`, `resource_role_label`, #305) ; le
sous-projet d'une ligne de provision, celui que son risque désigne, y est une cellule calculée, que
le nœud nomme (`estimate_line.subproject_id` de `computed_fields`, EP-14/L42p), et son refus demande
au serveur ce dont il dépend, comme ses grandeurs — les listes du référentiel ne servent qu'au choix
d'une saisie, offerte seulement sur un objet qu'elles connaissent ; elles ne demandent les objets
désactivés (`include_inactive`) qu'à une session qui porte la permission d'écriture de leur partie
du référentiel, que le contrat exige (#2084, option A), et un chiffreur sans elle saisit sur les
objets actifs (#351).
Ce qu'une écriture rend se lit comme la grille le lit (`nodesWritten`) : les nœuds écrits et leurs
ancêtres entiers, des tâches redatées la part de leur calendrier qu'elle montre (`rescheduled`), des
lignes et des tâches déplacées dans le temps la part de leurs montants qu'elle montre (`reinflated`)
— chaque part ne pose que ses champs : celles d'une même ligne, d'une écriture ou de plusieurs, se
posent l'une sur l'autre dans l'ordre des réponses (`answers.ts`). Le mode de planification et
l'avancement s'y montrent par une icône nommée, le chemin critique par une icône et le gras sur la
marge, jamais par la seule couleur ; une date se montre dans sa forme courte. Le tri et la recherche
sont dans l'adresse, sous les noms du contrat (`sort_by`, `sort_order`, `search`, `query.ts`) : un
en-tête cliqué ou une recherche saisie change l'adresse, la page relit l'opération avec eux, et la
grille rend les lignes dans l'ordre reçu, les totaux de la réponse en pied — TanStack Table n'y
enregistre aucun modèle trié, filtré ni groupé. Au clavier, la grille est un seul arrêt de
tabulation, sa cellule active, que les flèches déplacent, l'en-tête compris — ses boutons et ses
poignées hors de la tabulation — : Entrée ou Espace sur un en-tête trie sa colonne, Maj et les
flèches l'élargissent ou la rétrécissent (motif `grid` d'ARIA, #182). Un refus d'écriture reste dit
jusqu'à ce que l'utilisateur ferme son avis (`OutcomeNotice`, `dismissible`), quoi qui réussisse
après lui. Seules les lignes visibles sont rendues (`row-window.ts`, sur `@tanstack/virtual-core`) :
le virtualiseur est lu comme un magasin dont l'instantané est une donnée, qui ne change que quand la
fenêtre bouge. Le React Compiler n'est pas activé dans ce front, mais le lint de React refuse
l'adaptateur de TanStack Virtual, dont un rendu compilé figerait les réponses
(`react-hooks/incompatible-library`). La hauteur d'une ligne suit la taille de la police racine
(1,75 rem). L'en-tête et les totaux sont collés au haut et au pied de la grille, le numéro et le
libellé à son début. La ligne d'en-tête de toute table, liste comme grille dense, est sur le fond
`muted` de la charte : `TableHead` le pose à l'en-tête d'une colonne, dans le `<thead>`, non à celui
d'une ligne, et un `<thead>` écrit à la main le prend de même (#508), ce que
`frontend/src/components/thead-guard.test.ts` vérifie dans les sources. La grille prend la hauteur
que lui laisse son écran : un écran de grille est un `Screen` qui remplit la fenêtre (`fill`), la
page bornée à sa hauteur (`ShellFrame`), et la grille s'y réduit de la hauteur de ses lignes jusqu'à
un plancher, dix rem au plus et jamais plus que son contenu
(`min(10rem, 2 × EDGE_REM + max(lignes, 1) × ROW_REM)`, `grid-floor.ts`, #1041) — aucune hauteur n'y
est calculée d'après ce qui la précède ; une fenêtre trop basse pour ce plancher fait défiler la
page. L'enveloppe de la grille et de sa barre porte ce plancher, plus la barre, en hauteur minimale
: les enveloppes de l'écran, qui rétrécissent à ce qui reste (`min-h-0`), ne poussent pas le cadre
sous son plancher sur ce qui le suit dans la même enveloppe — les filtres au-dessus, les pages en
dessous. Le plancher ne remonte pas plus haut : une enveloppe en `min-h-0` peut rester plus basse
que le cadre, ce que la page absorbe en défilant, tant que rien ne la suit. Un écran qui a du
contenu sous l'enveloppe de sa grille, hors de la chaîne qui la contient — fût-ce seulement dans une
fenêtre étroite, où le contenu voisin se range dessous (les coûts réels, les risques) —, ne remplit
pas la fenêtre là où il l'a dessous (`fillWide`, `lg:min-h-0`), de même que `/admin/backups` et le
référentiel des ressources et des coûts, qui empilent leurs grilles, ne la remplissent pas : la
grille déborderait sur lui (#1033). `frontend/e2e/grid-frame.spec.ts` le mesure sur les huit écrans
qui remplissent la fenêtre, dans une fenêtre basse, aux deux largeurs du harnais : le cadre ne
chevauche rien. La largeur d'une table est du CSS, sans mesure en script (`table-width.ts`, US-2080,
#3075) : le cadre a la largeur de sa carte, la table la plus grande de la carte et de la somme de ses
colonnes, et la colonne du libellé (`label`) — à défaut, la dernière avant une colonne figée à la
fin — prend ce que les autres laissent, la largeur choisie pour elle devenant son minimum : sa
poignée et ses flèches règlent ce minimum, sans que la colonne rétrécisse sous ce que la carte lui
donne ; un pas qui ne change rien à l'écran n'écrit rien, si bien que, tant que la carte est large,
ce minimum ne peut que monter (#3280). Elle n'est plus large que sa largeur que quand la table ne
défile pas de côté : les décalages des colonnes figées, tirés des largeurs choisies, restent justes.
Aucun trait entre les colonnes, sauf à côté d'une colonne figée ; les cellules du corps prennent le
fond de la carte qui porte la table (`CELL_BACKGROUND`, `bg-card`, #3277), opaque pour les colonnes
figées, et la ligne sous le pointeur est teinte d'un jeton (`--row-hover`, `ROW_HOVER`), qu'une
cellule calculée, une ligne choisie ou marquée d'un différentiel gardent sous leur propre teinte. Les
commandes d'une ligne (variante `row` de `Button`) ont un bord à elles, `--row-command-border`, à
3:1 sur la carte, le survol et la ligne choisie ; `--border`, qui ne fait que séparer, reste clair
(#3332). Dans la ligne de total, le libellé du nombre s'étend sur les colonnes sans
chiffre qui le suivent (`colSpan`) au lieu de se tronquer ; figé, il ne reste collé que sur les
colonnes figées, ses mots au début de sa colonne (#3072). Les tables simples (`ui/table.tsx`) ont
le texte, l'en-tête et l'absence de traits des grilles. La barre et le bouton « Colonnes » ont la
largeur du cadre, celle de ce qui les tient, sans la dépasser, et jamais moins que ce que la barre
tient sur une ligne (`min-w-min`, la recherche rétrécissant avant que rien
ne s'enroule, hors la liste de commandes d'un écran, qui s'enroule d'elle-même) ; les avis — refus,
collage appliqué, colonnes non montrées, problème de saisie — gardent toute la largeur (#1042).
Colonnes masquées, largeurs et tri sont une préférence d'affichage (`settings.ts`, WF-IHM-0060) :
lues de la session, la grille remplacée entière à chaque écriture et ce qu'elle ne règle pas renvoyé
tel quel. Elle écrit aussi les clés de toutes les colonnes qu'elle offre (`known_columns`,
`gridShape`, US-0650) : une colonne masquée par défaut que la grille ne connaissait pas à la
dernière écriture est masquée, une colonne que le compte a choisi d'afficher le reste ; des réglages
écrits avant cette liste n'en connaissent aucune, et une colonne masquée par défaut y est masquée
(`docs/api/DECISIONS.md`). Une grille garde dans le compte son tri et ses colonnes — celles qu'elle
masque, et leurs largeurs —, jamais sa page (règle validée par l'auteur le 2026-10-09). Ses filtres,
une grille qui les déclare (`GridConfig.filters`) les garde en préférence, comme le veut le critère
d'US-0380, qui fait foi (#836, confirmée par l'auteur le 2026-10-11) : ils sont retrouvés à
l'ouverture d'une adresse qui ne dit rien de la grille ; la page et les filtres d'une adresse qui
les dit vivent dans l'adresse. Une autre grille ne garde aucun filtre. Une colonne ou une largeur
s'écrit après une pause, avec le tri gardé tel quel ; ce qui attend part quand la page est quittée
ou cachée, avant une recherche et au démontage — au mieux : une action serveur ne porte pas
`keepalive`, et la fermeture d'un onglet peut l'interrompre. Seul un clic d'en-tête écrit le tri,
une fois que la page le montre (`recordShown`), avec les réglages de ce moment — une largeur changée
pendant la navigation comprise : Next porte une action serveur dans l'état de son routeur, et une
navigation ne se montre pas avant que les actions lancées après elle aient répondu — écrite au clic,
la préférence retenait le tri d'un aller-retour, et de chaque action en file avant elle. Jusque-là,
elle attend comme le reste, et part avec lui si la page est quittée, cachée ou démontée, ou avant
une recherche. L'adresse fait foi : un tri levé y reste, `sort_by` vide, et le tri gardé ne sert que
quand elle ne dit rien du tri. Chaque grille est à la route de sa fonction,
`…/revisions/[r]/planning` et `…/revisions/[r]/estimate` ; la révision elle-même mène à la première
fonction d'une révision que la session peut lire, dans l'ordre de la FBS et de la barre latérale —
le planning, ou le devis pour un chiffreur qui ne lit pas le planning. L'écran du devis dit
au-dessus de sa grille les taux horaires qui manquent à son calcul, avec le chemin du référentiel
pour qui le lit, et ses indicateurs, avec leur date de calcul, ou qu'ils sont indisponibles quand
l'API ne les trouve pas ou les refuse faute de taux horaire (`HOURLY_RATE_MISSING`, #159) — ces deux
cas ne font pas tomber l'écran ; toute autre réponse suit la règle des lectures (`EstimateSummary`).

La barre de toute grille suit un seul ordre (`GridToolbar`, US-2080, décision de l'auteur du
2026-11-14) : les commandes de l'écran, la recherche, « Filtres » — les menus d'une grille
arborescente, ou le bouton du panneau d'une table plate —, « Colonnes », « Arbre » pour une grille
arborescente, puis, à la fin, l'annulation et le rétablissement. Elle ne dit aucun nombre de lignes :
la ligne de total le dit seule, ce qu'un filtre retient compris (#3072). La raison pour laquelle
l'annulation attend, coupée à la place que laisse la barre, s'ouvre en entier quand on la presse — au
clic, au toucher ou au clavier —, dans un Popover (#3150). Chaque filtre actif d'une table plate est
une pastille dans la teinte de la couleur primaire (`bg-accent`, son texte en `text-primary`, la
paire mesurée par `contrast.test.ts`), avec son libellé et sa croix (#3077). Les pages d'une liste
(`ListPages`) sont à droite sous la table, au texte de la table, atténué : « Lignes par page »,
l'intervalle des lignes montrées (« 1–50 sur 150 »), « Précédent », « Page n sur m » et « Suivant »,
ces deux liens à place fixe, inertes en bout de liste (`aria-disabled`, sans adresse) ; tout se lit
d'`offset`, `limit` et `meta.total` (`pageSpan`), sans saut de page ni première ou dernière page, et
la navigation porte le nom de sa liste (#3073).

Une grille qui lit un différentiel (`CostStructure.kind` = `amendment`) est un diff avec la
structure principale, que le serveur calcule (`Node.difference`, rendu sur chaque nœud, avec les
nœuds retirés à leur place) : elle reçoit `GridConfig.difference` (`withDifference`, `nodes.tsx`) et
une colonne `DiffMark` en tête (`diff-mark.tsx`, `DIFF_MARK_KEY`), avant le numéro. Le caractère dit
la différence — `+` un ajout, `-` un retrait, `M` une modification, une récapitulative dont le
contenu change comprise —, la couleur le double, la marque dans le vert, le rouge ou le jaune de son
jeton et la ligne teintée du même (`--diff-added`, `--diff-removed`, `--diff-modified` et leurs
`-mark`, avec leurs valeurs sombres), jamais la couleur seule : le mot — « Ajouté », « Retiré », «
Modifié » — est lu par qui ne voit ni l'un ni l'autre, et un nœud inchangé ne porte rien. Les jetons
sont mesurés dans les deux modes (`contrast.test.ts`), et les grilles du planning et du devis sur
l'avenant 2 sont des écrans du harnais d'accessibilité (`DIFFERENTIAL_SCREENS`, `e2e/routes.ts`). Un
nœud retiré se lit et ne se touche pas : aucun geste de structure ne lui est offert, ni « Insérer »
ni « Supprimer » ni Ctrl+Suppr, il ne se déplace pas, rien ne se dépose à côté de lui (`isRemoved`,
`structure-rules.ts`, #1185), et la cellule des prédécesseurs suit `editable_fields`
(`task.predecessors`) : celle d'une tâche retirée, qui ne le nomme pas, n'est pas saisissable
(#1257).

La comparaison de deux révisions (`/revisions?from_revision_id=…&to_revision_id=…`) est la même
grille, en lecture seule (`comparison-grid.tsx`, `components/revisions/`) : les nœuds de
`compareRevisions` — l'arbre de la révision comparée, les nœuds retirés à leur place —, chacun avec
la marque que le serveur rend (`difference`, `changes`, une tâche déplacée sous une autre
récapitulative marquée modifiée, WF-REV-0080), la colonne `DiffMark` en tête, puis le numéro, le
libellé indenté par son niveau sous l'icône de sa nature, et ce qui change du nœud, nommé comme le
serveur le nomme. La comparaison ne se pagine pas, comme `listNodes` (#1201) : l'écran demande
l'arbre entier, réduit par `fields` aux colonnes qu'il montre (`COMPARISON_FIELDS`, `kind`,
`task.label`, `estimate_line.label`) et projeté (`comparisonRows`) ; le serveur rend toujours le
numéro, le niveau, la version et la marque. Faute de parent dans ces champs, l'arbre ne se plie
pas ; rien ne se trie ni ne se cherche, l'ordre est celui du plan. Les 5 999 nœuds de l'exemple de
volume (`volume/comparison_volume.json`, dont 2 770 modifiés) ne montent qu'une fenêtre de lignes,
et l'écran garde la borne d'un écran de grille (`WORKING`, 15 s, `revisions.spec.ts`) ; le parcours
joue l'exemple de la fenêtre contre le faux back, qui sert le premier exemple de l'opération, et
toute la structure contre le service, où celle de PRJ-001 compte 5 966 nœuds, la volumétrie de 5 999
nœuds restant au faux back jusqu'à EP-13 (#2696). Les écarts de montants restent une table sous la
grille, et l'écran est l'un de ceux du harnais d'accessibilité (`DIFFERENTIAL_SCREENS`).

Une table plate peut laisser choisir ses lignes une à une (`DenseGrid.selecting`, désactivé par
défaut, #2916/L4) : Ctrl ou Cmd et un clic sur la poignée du numéro, Espace seul au clavier
(Ctrl+Espace en alias), Ctrl ou Cmd et A pour toutes les lignes affichées (hors d'une cellule en
saisie), la case de l'en-tête des poignées, et, dès qu'une ligne l'est, une barre sombre
(`SelectionBar`) qui recouvre la barre de la grille à la même place et à la même hauteur, sans
décaler le cadre ni recalculer sa hauteur : la sélection prime, la recherche, « Colonnes » et les
commandes de l'écran sont inertes et masquées tant qu'elle dure (leur état, la recherche saisie
comprise, est gardé), et « Annuler la sélection » ou Échap les rend. Le focus qui était dans l'une
des deux barres quand l'autre la remplace revient à la cellule active (`useBarFocus`). Une grille
arborescente garde la sélection contiguë, son glisser-déposer et son clavier.

### La grille de planning et le Gantt

Au-dessus de la grille, la date de début de planning de la structure lue
(`CostStructure.planning_start_on`, WF-PLA-0020), telle que le serveur la donne (`PlanningStart`,
`planning-start.tsx`) ; là où la structure liste `edit_planning`, une commande confirmée la change
(`updateCostStructure`, `updateStructure`) avec le compteur de la structure, la page relue pour les
tâches que le serveur redate, et la date répondue montrée tant que la page lue est plus ancienne ;
un jour sans heure travaillée est refusé par `NON_WORKING_DAY`, dit sous le champ avec le jour
travaillé suivant. L'écriture compte parmi celles de la grille (`StructureAccount.writing`). La
grille présente les dates de démarrage et de terminaison (`started_on`, `completed_on`), en lecture
seule, après la marge, et nomme la liaison en conflit (`link_conflicts`) par une icône dans la
colonne des prédécesseurs — sur la tâche manuelle comme sur son prédécesseur — et dans le nom de la
barre du Gantt : la ligne du prédécesseur, le type de la liaison, la ligne de la tâche quand la
grille la lit (`link-conflicts.tsx`). La grille de planning présente aussi la description d'une
tâche et l'avancement physique d'une récapitulative, un pourcentage calculé ou non calculable, son
motif en titre ; puis le Gantt (FBS-4.3.3, `frontend/src/components/gantt/`), sa dernière colonne,
en lecture seule, épinglée à droite (`GridColumn.pinned: "end"`, `pinning.ts`, US-0530) : elle
glisse sur les colonnes qui la précèdent quand elle s'élargit, et la grille les fait défiler hors de
dessous elle (`scroll-padding-inline-end`). Sa poignée, sur son bord gauche — la souris, ou Maj et
les flèches, la flèche gauche l'élargissant —, règle sa largeur, celle de `gantt` dans
`column_widths`, et ne modifie aucune tâche, d'un minimum jusqu'à la place du cadre à sa plus grande
largeur (`useFrameRoom`), moins les colonnes épinglées en tête et la plus large des autres, où se
montre la cellule active (`endMaxOf`). Chaque cellule dessine en SVG la ligne de sa tâche — sa
barre, les morceaux des liaisons qui la quittent, la longent ou l'atteignent, les mois de l'axe — :
le dessin est aligné ligne à ligne sur la grille, rendu avec ses seules lignes visibles, et suit la
largeur de sa colonne, en part de cette largeur. La disposition (`ganttLayout`, `layout.ts`) se
calcule une fois pour les lignes que la grille montre, écritures comprises, que `DenseGrid` remet à
ce qu'un écran met autour d'elle (`around`, `GanttRows`) — jamais en prop de chaque ligne ;
l'en-tête dessine l'axe (`GridColumn.axis`), son libellé ne nommant plus la colonne qu'aux lecteurs
d'écran. Rien n'y est planifié : une tâche va de son début à sa fin, chacun placé à son jour plus ses
heures rapportées aux heures de ce jour sur le calendrier de la tâche (`calendar_hours`) — deux
tâches de 4 h enchaînées le même jour de 8 h se suivent, la liaison arrive à droite de son départ,
et l'image exportée suit le même placement —, et, sans calendrier (la frise d'une chronologie) ou un
jour sans heure, du début de son premier jour à la fin du dernier, une fin à l'heure 0 étant le
début de son jour ; un jalon se tient à sa fin, et l'axe va du premier du
mois du plus tôt au premier du mois qui suit le plus tard (`monthTicks`, `chart/ticks.ts`, sans
ECharts). Une liaison joint l'endroit que son type nomme sur le prédécesseur à celui qu'il nomme sur
la tâche ; un prédécesseur hors de la réponse n'en dessine aucune. Une récapitulative est un
crochet, un jalon un losange, une tâche une barre, pleine sur le chemin critique et creuse ailleurs,
et chaque barre est une image nommée par ses dates et « critique » : rien ne se lit à la seule
couleur. Aucune cellule du Gantt ne prend de saisie, et seul le bouton qui précède le crochet d'une
récapitulative y prend le pointeur, pour la plier ou la déplier. Son niveau le plus fin divise
chaque jour en heures travaillées, numérotées dans leur jour, que la page lit de `getDurationUnits`
: `hoursOfDay` (`scale.ts`) arrondit `hours_per_day` à l'heure entière la plus proche, la demi-heure
vers le haut, de 1 à 24, sur les chiffres de la chaîne, jamais par un flottant (#1393). « Exporter
en PNG », après le zoom dans le coin de l'en-tête et au menu d'une cellule, dessine sur un canevas
(`gantt-image.ts`) toute l'étendue au niveau montré — la largeur du dessin zoomé, celle de la
colonne une fois ajusté au projet —, une ligne par tâche que la grille montre, pliée comme elle, les
jours chômés du même hachurage que l'écran (`DAY_OFF_HATCH`, lu par les classes de ses jetons) et
leur légende, la provenance en tête comme pour toute courbe (`useProvenance`, `provenanceOf` de
`grid-screen.ts`) ; deux fois plus dense que l'écran tant qu'un canevas le tient, aussi dense sinon,
et indisponible, son motif dit, au-delà des bornes des navigateurs (32 767 points de côté, 268
millions en tout). Sa colonne « Rattachement » présente le lot ou le poste que porte une tâche, par
le libellé que le serveur résout (`work_breakdown_label`) ; là où la structure lue liste
`edit_planning`, la cellule le choisit parmi les lots et les postes du lotissement lu entier, ou
rien, écrit par `updateTaskFacet` — le champ choisi, et l'autre mis à `null` dans la même écriture
quand la tâche le porte (`planning-attachment.ts`) —, son refus dit par le motif de son champ, en
nommant la tâche qui porte déjà l'élément ou celles qui sortiraient du sous-arbre de leur lot
(WF-PLA-0170) ; comme tout refus de l'écriture d'une cellule, il est dit au-dessus de la grille, et
sa cellule, marquée, en est décrite (`aria-invalid`, `aria-describedby`). Là aussi, la tâche se
saisit au clavier, cellule par cellule, par `updateTaskFacet` (US-0470, `planning.tsx`) : le
libellé, la description — vidée, elle est nulle —, le mode (une liste), la durée avec le suffixe de
son unité et les dates, chacune là où le nœud porte sa tâche, nomme son champ parmi ceux qu'il
accepte (`editable_fields`) et ne le calcule pas (`computed_fields`) : les dates d'une tâche
automatique, la durée d'une récapitulative sont traversées sans entrer en saisie (WF-PLA-0020). La
durée se lit dans la langue de l'interface (`parseDuration`, `cell-values.ts`), sans égard à la
casse, un nombre seul en jours : les suffixes que nomme WF-PLA-0160 sont lus en toutes langues — « m
» un mois, « min » une minute, « h », « j », « sem », et leurs pareils écoulés préfixés d'un « e »
—, plus ceux que le catalogue écrit dans la langue courante (`enums.DurationUnit`), et aucun autre :
en anglais « d », « wk », « mo » sont lus, en français ils ne le sont pas. Elle part dans son unité,
que le serveur garde. Une date se tape dans la forme courte de la langue, ou sous sa forme ISO
(`parsePlanningDate`), et part seule, sans heures : le front ne connaît pas le calendrier, le
serveur complète les heures — le début au début du jour ouvré, la fin au bout de ses heures —, et la
cellule montre ce qu'il rend (#1244). Les prédécesseurs d'une tâche se saisissent comme dans MS
Project, « 3FD+2 j ; 5DD » (`predecessors-entry.ts`) : le numéro de ligne, le code du type de la
liaison dans la langue de l'interface — FD, DD, FF, DF en français, FS, SS, FF, SF en anglais, rien
pour une fin à début —, puis le décalage, positif ou négatif, avec l'unité d'une durée (les suffixes
de `parseDuration`) ou en pourcentage de la durée du prédécesseur ; la liste entière part en place
de celle de la tâche, par `setPredecessors`, avec la version du nœud lu. Le numéro se résout sur les
lignes que la grille a lues (celles d'un prédécesseur qu'une recherche a écarté se retrouvent par
les liaisons d'une ligne lue) ; un numéro qu'elles ne connaissent pas se demande au serveur, dans la
numérotation de toute la structure (`resolveRowNumber`, US-0650), la saisie en lecture seule et
`aria-busy` tant qu'il n'a pas répondu (`EntryKind.ask`, `useRowNames`), puis validée à nouveau. Un
numéro qu'aucune tâche ne porte — une ligne de devis, ou aucun nœud (404) — laisse la saisie
ouverte, qui le dit, sans rien envoyer ; un serveur qui n'a pu répondre aussi, en disant de valider
à nouveau. Quittée par un clic ailleurs pendant la demande, la saisie se valide à la réponse, ou
s'abandonne. Un refus du serveur se dit à la cellule par son code — une boucle de liaisons, avec les
tâches qu'elle traverse (`cycle`, `problemDetails`), une liaison entre une récapitulative et sa
subordonnée, un projet qui dépasserait quinze ans —, et les lignes écrites, avec les tâches que le
serveur redate, prennent la place des lignes lues, le Gantt suivant ; le front ne date rien. La
validation de la dernière cellule saisissable d'une ligne place le curseur sur la ligne suivante, à
la cellule d'où la ligne a été commencée. Toute écriture de cellule, de toute grille, dit un refus
par champ par le motif de son champ (`byField` de `cell-writes.ts`, #817.1) ; seul un refus de la
valeur (422) marque la cellule, l'API hors d'atteinte, une version périmée ou une session perdue ne
disant rien de ce qui a été saisi (#819.2) ; une valeur que la ligne répondue porte déjà n'écrit
rien, faute de quoi le corps ne porterait que la version (#819.8), et lève le refus de sa cellule,
avec l'avis qui le dit. Au-dessus de la grille du planning et de celle du devis, un filtre choisit
un lot ou un poste parmi le même lotissement lu entier (`BreakdownFilterChoice`, `readGridScreen`
avec `byBreakdown`), écrit dans l'adresse sous le nom du contrat — `work_package_id` ou
`order_item_id`, l'un levant l'autre, un identifiant mal formé ignoré — et envoyé à `listNodes`, qui
retient le sous-arbre de la tâche rattachée ; le bandeau le montre actif et le lève
(`breakdownChip`), au devis sur la grille seulement, ses indicateurs restant ceux du projet. Un
lotissement que l'API refuse (404, 422, 503) n'ôte que le filtre, sauf là où le rattachement se
saisit, qui ne s'en passe pas (`needsBreakdown`). Dans la grille vide, le squelette s'offre comme la
révision liste `generate_skeleton`, indisponible avec sa condition dès que la structure comporte une
tâche (WF-PRJ-0030) ; engendré, ses tâches remplissent la grille tant que le compteur de la
structure qu'il rend est plus récent que celui de la lecture (EP-14/L44d). Les autres feuilles du
planning ont leur écran, où son en-tête mène : l'arborescence de tâches (FBS-4.3.5, `…/task-tree`,
`frontend/src/components/tree/`), un `tree` d'ARIA sous la racine du projet, le premier niveau côte
à côte, les suivants sous leur parent, un seul arrêt de tabulation que les flèches parcourent, la
profondeur dans l'adresse (`depth`) ; et les chronologies (FBS-4.3.1, `…/timelines`), une par lien
(`timeline`), chacune une frise à couloirs, distincte du Gantt (`gantt/timeline-chart.tsx`, US-0530,
#1068) : sur l'axe du Gantt, à ses niveaux et à son zoom (`GanttRows`, `GanttAxis`), une tâche est
un rectangle de son début à sa fin, son nom tronqué et entier dans l'infobulle et le nom accessible
— la tâche, ses dates, son couloir —, un jalon une ligne verticale sur toute la hauteur, son nom et
sa date au pied. Les rectangles s'empilent en couloirs (`lanes.ts`, un calcul de présentation) :
chacun dans celui où l'utilisateur l'a placé tant qu'il y tient, les autres, dans l'ordre du plan,
au premier couloir où ils n'en chevauchent aucun, les couloirs vides refermés. Un rectangle se
glisse à la souris d'un couloir à l'autre, ou se déplace par Alt et les flèches haut et bas sur
celui que le clavier désigne — la frise est un seul arrêt de tabulation, les flèches gauche et
droite passant d'un rectangle à l'autre (`aria-activedescendant`). Un couloir où il en chevaucherait
un autre est refusé, le refus dit, et rien ne bouge ; sous le dernier couloir s'en offre toujours un
vide, jamais au-dessus d'un autre, et le clavier vise le plus proche couloir où le rectangle tient,
passant ceux où il chevaucherait, pour atteindre tout ce qu'atteint la souris. La disposition est
une préférence d'affichage par chronologie (`DisplayPreferences.timelines`, WF-ADM-0040), écrite
après une pause comme les réglages d'une grille (`useKeptWriter`, `updateTimelinePreferences`) : les
couloirs de tous les rectangles montrés, le déplacé d'abord, dans la borne de 64 du contrat, pour
qu'un déplacement ne déplace rien d'autre ; « Disposition automatique » l'oublie (`null`). La
lecture en table, sous la frise, dit chaque tâche, ses dates et son couloir ; elles se créent par
leur nom et la chronologie montrée se supprime après confirmation, comme le projet liste
`manage_timelines` (`timeline-commands.tsx`, EP-14/L44c). Le serveur sélectionne ce que chacune
dessine (#463) : l'arborescence demande les récapitulatives jusqu'au niveau de l'adresse
(`summaries_only`, `max_level`), une chronologie les tâches qui y sont inscrites (`timeline_id`). Le
service les tient pour les chronologies (US-1400) et pour l'arborescence (US-1440) : l'écran
dessine ce qu'il rend, sans appliquer de critère à la réponse, et le repli de `listNodes` (#496,
`summaryTree`, `inscribedTo`) n'existe plus. Contre le faux back, qui rend le premier exemple
quelle que soit la requête, l'arborescence dessine toute la structure du témoin, et l'écran des
chronologies tous les rectangles du volume : ce que chacune sélectionne se prouve contre le service
(`task-tree.spec.ts`, `timelines.spec.ts`), la requête de l'écran par ses tests de composants. La
profondeur que le parcours de l'arborescence demande au service est celle de l'écran
(`DEFAULT_DEPTH`, `summaries.ts`, #2551), non un nombre recopié.
L'arborescence offre exactement les niveaux que la structure a, du premier à celui de sa plus
profonde récapitulative, que le serveur dit quels que soient les filtres (`meta.summary_depth`,
#494), et montre le niveau demandé, ou le plus profond quand on lui en demande un au-delà
(`depthShown`).

Le planning est branché sur le service (EP-06, US-1470) : la page ne porte plus la note de la
maquette (`MockupNotice`), chaque cellule s'écrit par `updateTaskFacet`, les prédécesseurs par
`setPredecessors` (`resolveRowNumber` pour un numéro que la recherche a écarté), la date de début
par `updateCostStructure`, et le rattachement, la création, l'indentation, le déplacement et la
suppression par les opérations de l'arbre ; les tâches redatées, les liaisons en conflit, la marge
et le chemin critique sont ceux que le serveur rend. Un compte qui voit le projet sans en être
contributeur lit le planning et reçoit `NOT_CONTRIBUTOR` à chaque écriture et à `openImport`
(`e2e/service/planning-readers.spec.ts`, WF-ADM-0110-A). Le témoin de PRJ-001 a ses mille tâches dans
le service (US-1480), et le compte de la course n'en est pas contributeur (#2193) : un parcours qui
le lit se joue des deux côtés, `@shared`, et un parcours qui écrit se joue sur son propre projet
(`e2e/planning-seed.ts` : le projet créé depuis l'accueil, sa révision ouverte, six tâches écrites
par l'API, et, selon le parcours, leurs liaisons dont une en conflit, un lotissement de deux
postes). Les parcours de `planning-service.spec.ts`, `structure.spec.ts`, `computed.spec.ts`,
`keyboard.spec.ts`, `grid.spec.ts` (le Gantt épinglé) et `context.spec.ts` qui jouent contre le
service portent `@shared`, comme, dans `planning.spec.ts`, ceux qui lisent le témoin : l'ouverture
de la grille — ses icônes, les états « démarrée » et « terminée » d'une tâche du témoin
(WF-PLA-0080-A, #2595) —, ses totaux, le filtre sur un poste, l'absence de squelette, le Gantt, ses
jours chômés, le pli d'une récapitulative, le zoom et l'export PNG ; avec `navigation.spec.ts` (le
projet qui mène à son planning). Ils ne comptent pas sur un numéro de ligne : le service numérote
les tâches seules, les lignes du témoin, qui font avancer les numéros du faux back (7, 39, 311),
attendant US-1570 (EP-07) ; ils trouvent la ligne par son libellé et lisent le numéro qu'un
prédécesseur doit porter dans la grille. Le report d'une grille à l'autre (#1057, #2590) se joue
depuis la grille de devis (EP-07, US-1560, `structure.spec.ts`), sur la structure qu'elle partage
avec le planning : la tâche créée dans le devis, et une ligne sous elle, sont lues dans le
planning — automatique, d'un jour, sans prédécesseur —, et son indentation depuis le devis avec
elle. Le parcours du compte « chef de projet » joue la planification et FLX-02 ; FLX-01, l'analyse
de l'export relu, puis l'import confirmé et suivi dans la coquille, se joue contre le service
(`exchanges.spec.ts`, #2589, #2683). Ce qui ne se rejoue pas contre le service reste sur le faux
back, gardé par `inService` ou sans étiquette, la liste des entrées étant celle de « Un parcours de
bout en bout » : les parcours de `planning.spec.ts` qui écrivent sur le témoin — le rattachement,
la saisie d'une cellule, la durée et les prédécesseurs, la date de début — ont chacun leur jumeau
dans `planning-service.spec.ts`, sur un projet de la course ; les lignes, les montants et le devis
se jouent contre le service sur un projet de la course (EP-07, US-1560), ceux qui lisent le témoin
attendant ses lignes (US-1570) ; le reste à engager relève d'EP-09, les risques et les structures
différentielles d'EP-08 (US-2640 : le parcours de `context.spec.ts` qui ouvre l'avenant et ceux de
l'écran des risques se jouent contre le service, les marques de l'avenant étant celles qu'il rend) ;
les indicateurs, d'EP-10, se jouent contre le
service (US-1730, `indicators.spec.ts`). La mesure d'une validation de cellule (#196) et celle du déplacement de
la cellule active sur mille tâches (#620) sont au relevé de livraison d'US-1470.

### L'écran des risques

L'écran des risques, `…/revisions/[r]/risks` (`frontend/src/components/risks/`), lit chacune de ses
opérations dans la révision de sa route (`revision_id`) : les totaux des provisions des risques
retenus, par état et le total général, tels que le serveur les rend ; le filtre par état, des
boutons pressés qui n'écrivent que l'adresse (`states`, sous le nom et la forme du contrat) ; la
grille dense, une configuration de plus (`risk-grid.tsx`), en lecture, où la gravité et la provision
sont des colonnes calculées entières — aucun champ de nœud à demander (`field` rend `undefined`),
leur refus nomme les règles que le risque porte pour chacune (`computed_fields`, `dependsOn`) — et
la case de matrice une colonne de `Signal` ; la matrice des risques, un nuage de bulles
(`RiskBubbleChart`, « Les courbes ») sur toute la largeur entre les cartes et la grille — la colonne
de droite n'existe plus —, dont les bulles sont les risques des états du filtre, et sous lui la
table du décompte par case, ses axes nommés par les bornes que rend le serveur, chaque case par son
signal et son nombre de risques ; et, quand l'adresse nomme un risque (`risk`) — d'un clic sur sa
bulle ou sur son libellé —, son détail, dans une colonne à côté de la grille qui garde de quoi le
lire (la page défile dans une fenêtre trop basse) : notes, ligne de provision présente ou retirée à
la survenance, avec la catégorie et le sous-projet que le risque désigne pour elle, par les libellés
que le serveur résout — la catégorie dite désactivée quand elle ou sa nature l'est
(`provision_cost_category_is_active`), la provision hors sous-projet quand il n'en désigne aucun
(EP-14/L42p) —, historique des réexamens. « Identifier un risque » (`risk-commands.tsx`), dans
l'en-tête de l'écran, suit `declare_risk` comme la révision de la route le liste : absente, rien ;
indisponible, décrite par la condition qui manque (`at_least_one_task`, `active_provision_category`)
; disponible, elle ouvre le formulaire `risk-form.tsx` (`ReferenceForm`) — libellé, description,
actions de mitigation, probabilité en pourcentage envoyée en rapport, catégorie de la provision
demandée seulement quand plusieurs catégories actives de type provision se proposent, sous-projet et
tâche porteuse facultatifs, lus par la page quand une commande les demande (`provision-options.ts`)
—, dit le 409 sous le formulaire et, la création faite, ouvre le devis propre du risque
(`structure_id`) dans la grille de devis, pour une session qui lit le devis. « Modifier », dans le
détail, suit `update`, et la provision `update_provision` : indisponible, la catégorie, le
sous-projet et la tâche se montrent fixes et ne sont pas envoyés. Les deux commandes attendent,
inactives, qu'une écriture de leur formulaire fermé soit répondue (défaut n° 24 de `typescript.md`).
Les commandes du détail (`RiskCommands`) partagent par risque l'écriture en route et la réponse la
plus récente. « Réexaminer » (`risk-review.tsx`, `review`) part de la probabilité et de l'état que
le risque porte — le confirmer sans rien changer produit un réexamen daté (`reviewRisk`), que
l'historique montre à la relecture — et offre les états que le contrat laisse retenir (identifié,
écarté) ; un risque écarté dont la catégorie n'est plus active (`provision_cost_category_is_active`)
en demande une autre, parmi plusieurs actives, au retour à l'état identifié. « Supprimer le risque »
(`risk-lifecycle.tsx`, `delete`) demande une confirmation, est indisponible pour un risque cité
(`risk_not_cited`) et, supprimé, quitte le détail par l'adresse sans le risque. « Déclarer survenu »
(`declare_occurrence`) confirme, met la survenance en file (202) et la remet au suivi des tâches de
fond (`Following`) ; il lit d'abord le compte rendu de la survenance (`getRiskOccurrenceReport`,
US-0680), le présente dans les marques `+`, `-`, `M` comme celui d'une fusion
(`occurrence-report.tsx`), dit le retrait de la provision et les refus, et confirme avec les
compteurs lus ; une version périmée (412) propose de le relire. Une tâche échouée ne se rejoue pas
depuis le suivi, qui confirmerait des compteurs anciens : son entrée dit de repartir de l'écran du
risque, où la commande relit le compte rendu. Un risque survenu liste toutes ses commandes
indisponibles. Le registre se pagine comme toute table plate (`limit`, `offset`, `meta`) : « Lignes
par page » et les pages sous la grille (`ListPages`, `RISKS_LIST`), les totaux restant ceux de tous
les risques retenus. Le libellé d'un risque est un lien hors de la tabulation : la grille suit le
lien d'une cellule qui n'est pas saisie à Entrée (`grid-keyboard.ts`).

### L'écran du reste à engager

L'écran du reste à engager, `…/revisions/[r]/remaining` (`frontend/src/components/remaining/`,
`remaining.tsx` de la grille), lit ses indicateurs dans la révision de sa route
(`getRemainingIndicators`, `revision_id`) — le total, la marge sur le budget de référence et
l'écart à la revue précédente, absent plutôt que nul sans elle, les totaux par nature et, par
sous-projet, le reste à engager et la marge sur son budget avec le `Signal` de la zone que le
serveur donne, et la couverture des risques (`RiskCoverageSummary`) —, ou les dit indisponibles
quand l'API ne les trouve pas ; et la
grille dense, une configuration de plus, sur les lignes des seules tâches démarrées, à moins que
l'adresse ne demande aussi les non démarrées (`progress`, sous le nom et la forme du contrat, qu'un
lien de son en-tête écrit). Le montant budgété, les grandeurs et le réestimé au reste à engager
précédent, puis les grandeurs et le réestimé courants (WF-RAE-0040) ; les trois montants y sont des
colonnes calculées, les grandeurs précédentes des valeurs conservées, jamais saisies ; les grandeurs
d'une ligne se réestiment une par une par `setLineRemaining`,
là où la ligne dit l'accepter (`remaining_entry`) et où son nœud accepte le champ — jamais d'après
l'avancement de sa tâche —, la commande `edit_remaining` de la structure lue (`screen.commands`)
posant Annuler et Rétablir, et la grille, en lecture seule quand elle ne la liste pas ; elle se
filtre aussi par un lot ou un poste du lotissement lu entier, comme le planning et le devis
(`order_item_id`, `work_package_id`, restreignant la grille seule) ; la fin d'une
tâche s'y montre sans se saisir, et la fin dépassée par une marque propre, que le serveur dit
(`finish_overdue`). Les sous-projets du projet (`listSubprojects`, lus avec le bandeau, une fois par
requête) ne sont lus que là où la structure liste `edit_remaining` disponible, et refusés ils ne
donnent pas le sous-menu « Sous-projet » ; la colonne et le sous-menu sont ceux du devis, décrits
avec le menu contextuel des cellules (`choice-menu.tsx`). Son bandeau ne montre que le
sous-projet, seul paramètre de contexte que ses lectures prennent, et dit qu'il ne restreint que la
grille, ses indicateurs étant ceux du projet entier (`gridOnly` de `ContextBanner`, #459). Une ligne
qui emploie un objet du référentiel désactivé depuis (`uses_inactive_object`) porte la marque du
devis et reste lisible (WF-REF-0010). Une saisie qui termine la tâche — le reste nul de sa dernière
ligne ouverte — est refusée par le service sans la date (422, `COMPLETION_DATE_REQUIRED` sur
`/completed_on`) : la grille demande alors la date de terminaison dans un dialogue (`completion-date.tsx`,
le jour du poste proposé), rejoue la saisie à la même version avec `completed_on`, et, le dialogue
quitté, dit le refus à la cellule. La suppression d'une tâche démarrée, refusée `task_not_started`,
se dit dans les grilles de planning, de devis et de reste à engager avec un lien vers la ligne de la
tâche dans la grille de reste à engager de la même révision (`taskRemainingHref`, WF-PLA-0070) ; pour une
récapitulative, que le refus ne dit pas quelle subordonnée cause, le lien porte `progress=started,completed`
(jamais les non démarrées, qui ne causent aucun refus), et le front ne déduit rien de ce que le service sait
(#2819). Le dialogue de la date de terminaison se nomme par un compteur, non par `crypto.randomUUID()`, que
ne fournit pas une page servie en HTTP hors localhost (#2818). L'écran ne porte plus `MockupNotice` : la
grille, les indicateurs et le Kanban sont ceux du service. `e2e/remaining.spec.ts` entier porte `@shared`
(la grille et le Kanban) ; le parcours qui écrit se joue sur un projet que la course crée
(`seedPlanning`, `bringInProgress`, #2193), et ceux qui lisent le témoin de volume restent gardés par
`inService` jusqu'à **EP-13**. Le
Kanban du démarrage des tâches, FBS-4.5.3, est une feuille de la fonction,
`…/revisions/[r]/kanban`, où l'en-tête de la grille mène : toutes les tâches non démarrées, les
démarrées et les terminées avec leur date, telles que les rend
`listStartableTasks`, chacune une carte, un jalon non démarré dont les prédécesseurs sont terminés
signalé à terminer (`predecessors_completed`, un texte et une icône), et toute tâche non démarrée
dont ils sont terminés signalée « prête à démarrer » de même ; aucun pourcentage. Deux filtres,
qui vivent dans l'adresse seule (`q`, le libellé, sans égard à la casse ni aux accents ; `ready`,
`1`), la lisent par `remaining/address.ts` et l'écrivent par `router.replace` : `Kanban` en
filtre ce que le serveur rend (`kanban-filter.ts`) — le libellé dans les trois colonnes, les tâches
prêtes dans la colonne Non démarrée seule —, l'en-tête d'une colonne dont des cartes sont
masquées dit « n sur N », et une carte choisie qu'un filtre masque perd le choix. La page
découpe les cartes (`kanban-cards.ts` : ce que la carte montre et ses gestes, jamais le nœud entier
d'un millier de tâches) et lit la structure principale de la révision (`listCostStructures`), où les
gestes s'écrivent. Une carte se choisit au clic ou aux flèches (haut et bas dans la colonne, gauche
et droite d'une colonne à l'autre ; un seul arrêt de tabulation) et fait les gestes que sa tâche
liste (`available_commands`, jamais déduits de la nature de la tâche ni de ses lignes) : par son
menu, qui garde les gestes indisponibles avec leurs conditions, par glisser-déposer sur une
colonne, ou au clavier — Maj et flèche droite ou gauche portent la carte à la colonne voisine,
et à elle seule : un glisser vers une colonne plus loin n'a pas de touche. Le menu de la carte,
ouvert par Entrée, offre tous les gestes que la tâche liste : c'est lui l'équivalent clavier
complet du glisser (WF-IHM-0100). Le glisser pose un type qui lui est propre
(`application/x-waterfall-card`), non `text/plain`, qu'un champ de texte où l'on dépose
insérerait. Le geste qui mène à l'état de la colonne visée est celui que la carte liste avec cet
état (`progress`) ; sans lui, la carte le dit. Une carte qui demande sa date n'est pas
glissable, et aucune autre demande ne s'ouvre tant qu'elle l'attend : la saisie n'est jamais
perdue en silence.
Démarrer et terminer demandent la date de l'événement, celle du jour proposée ; « Saisir le reste à
engager » est un lien vers la grille du reste à engager, cherchée sur le libellé de la tâche
(`remainingHref`). La réponse de `setTaskProgress` remplace la carte dans la colonne de son nouvel
état, tant que la lecture qui suit n'a pas le nœud à sa version ou à une plus récente (le
compteur du nœud départage, `replaced`) ; la carte répondue ne liste aucun geste avant cette
lecture. Le focus suit la carte, un refus se dit sur elle (`OutcomeNotice`), et une écriture à la
fois. L'opération lit la révision en cours : sur une révision marquée, l'écran le dit et ne
demande rien.

### L'écran des coûts réels

L'écran des coûts réels, `…/revisions/[r]/actual-costs` (`frontend/src/components/costs/`), lit ceux
du projet — ils ne sont pas versionnés, la révision de la route n'est que le contexte du bandeau —
page par page, comme le serveur les pagine (`offset`, `listActualCosts`) : les trois totaux des
lignes retenues et la date du dernier import, tels que le serveur les rend ; les filtres par
périmètre, par sous-projet — celui du contexte de lecture, `subproject_id` — et par période des
pièces, qui n'écrivent que l'adresse, sous les noms du contrat, et ramènent à la première page ; la
grille dense en lecture (`cost-grid.tsx`), sans recherche — l'opération n'en a pas : une
configuration la retire par `searched: false` —, chaque ligne avec son sous-projet nommé par le
serveur, son périmètre en mots et chaque colonne conservée du fichier comme une colonne, sous le nom
que le fichier lui donne, ses valeurs telles qu'importées (`passthrough.<colonne>`), chaque colonne
triée par le serveur — les colonnes conservées sont celles de toutes les lignes retenues, dans
l'ordre où le serveur les nomme (`meta.passthrough_columns`, #414) : les mêmes d'une page à l'autre
— ; et le journal des imports, paginé à part (`imports_offset`, `imports_limit`), avec son « Lignes
par page » et sa clé de grille (`cost_imports`, `KeptListSize` de `grid/kept-list-size.tsx`, qui
enregistre la taille comme une grille dense : le journal n'est pas une grille). Les imports d'un
projet (`imports`) font de même. Quand le projet liste l'exclusion de ses lignes
(`exclude_cost_lines`), le numéro de pièce d'une ligne est un lien hors de la tabulation, que la
grille suit à Entrée, vers la même adresse nommant la ligne (`line`) : sa place dans le périmètre
suivi s'y montre (`CostLineScope`), avec la commande qui l'exclut, sur le motif saisi, ou la
réintègre (`setActualCostTrackedScope`, WF-CRE-0040) ; l'écriture faite, la page relit la ligne et
les trois totaux, que le serveur tient (#291). Des filtres que le serveur refuse (422 : une période
qui finit avant de commencer, un sous-projet que le projet n'a pas) se disent à la place des lignes,
les filtres gardés pour être changés. Un tri ou une recherche changés ramènent toute liste paginée à
sa première page (`sortHref`, `searchHref`). Un lien de page, comme le libellé d'un risque, part de
la dernière adresse demandée (`usePendingLink`) ; quand elle lit les coûts autrement que la page
montrée — un filtre ou un tri en attente —, il mène à leur première page.

L'écran est servi par le service (EP-09, US-1620) : il ne porte plus de note de maquette
(`MockupNotice`), et le filtre des lignes imputées au seul projet passe par `unassigned`, que le
contrat accepte comme `SubprojectFilter`. `last_import_at` est la date du dernier import du projet,
quels que soient les filtres, nulle sans import ; les trois totaux, la date et les colonnes conservées
(`meta.passthrough_columns`) sont ceux du service, l'écran n'en calcule aucun. Le parcours
`e2e/actual-costs.spec.ts` porte `@shared` : il se joue contre le service sur un projet que la course
crée (#2193), les lignes que sert le faux back étant celles du témoin, que le service charge à
US-1650. L'aide de la correspondance de l'extraction (FBS-3.1.3) dit ce que l'import en fait : refusé
par 409 `actual_cost_mapping_complete` tant qu'elle est incomplète, 422 `FILE_FORMAT_UNREADABLE` pour
une colonne exigée que le fichier n'a pas, les colonnes ni lues ni conservées comptées comme ignorées
au compte rendu.

### Les écrans du référentiel

Les écrans du référentiel (`frontend/src/app/reference/`, `frontend/src/components/reference/`,
US-0250) sont hors projet, aux routes de leurs fonctions. Les paramètres de coûts disent la devise
de l'installation et présentent la grille des taux horaires — une configuration de plus de la grille
dense (`rate-grid.tsx`), la troisième section de l'écran, sous les natures et les catégories, une
ligne par catégorie de main-d'œuvre, son état, une colonne par année de toute la grille, quelle que
soit la page, dont l'en-tête est l'année elle-même (`GridColumn.heading`) —, cherchée, filtrée par
état et sur les bornes du taux d'une année (`RateFilterBar`, #545), triée et paginée par le serveur
sous les noms du contrat (`search`, `is_active`, `rate_year`, `rate_min`, `rate_max`, `sort_by`,
`offset`, #509) : chaque colonne se trie, le taux d'une année par `rate.<année>`, que la page
accepte pour toute année que `Year` prend (`RATE_SORTS`), avant de connaître celles de la réponse ;
sa ligne de totaux dit combien de catégories le serveur retient, et la devise. Une cellule saisie
part seule par `setHourlyRate`, sans version au premier taux d'une année, avec celle du taux lu pour
une correction, et le taux répondu prend sa place. La saisie n'est offerte qu'à une session qui
porte `cost_settings.write` (`platformOffer`), comme l'ajout de la colonne d'une année que la grille
n'a pas (WF-REF-0060, #299) : le contrat n'a aucune opération pour la créer — une année entre dans
la grille par son premier taux —, si bien que la colonne est celle de la grille, vide, à sa place
parmi les années, jusqu'à ce que la saisie d'une de ses cellules écrive ce premier taux, et elle se
retire tant qu'aucun taux n'y est saisi ni en cours d'écriture ; une année déjà présente, ou hors
des bornes de `Year`, est refusée dans la page ; la colonne ajoutée se trie comme les autres, le
serveur laissant l'ordre du code pour une année sans taux. Au-dessus d'elle, les natures puis les
catégories de coût, deux grilles denses (`cost-grids.tsx`, #510), triées sur chaque colonne,
cherchées, filtrées — les natures par type (`kinds`, `ValuesFilter`) et par état, les catégories par
nature, offerte parmi toutes celles que la session lit, et par état — et paginées par le serveur —
les trois sections s'empilent comme celles des paramètres de ressources, dans une page qui défile
(`Screen` sans `fill`, US-0570/L3, #1044), chaque grille plafonnée à la fenêtre (`max-h-svh` de
`DenseGrid`). Les paramètres de ressources présentent trois grilles denses (#301, #511, #533) :
l'organisation, une grille arborescente qui ne se trie pas et ne se pagine pas, dans l'ordre de
`listOrgNodes`, chaque nœud par son libellé décalé de sa profondeur (`level`), qui plie ce qui est
sous lui comme les grilles de tâches (`GridTree.parent`, `fold.tsx`), son code et son niveau,
filtrée par code (`code`), par niveau (`level`, offert parmi ceux de l'arbre entier) et par état, le
serveur rendant les nœuds retenus et leurs ancêtres, qu'un filtre déplie une fois ; les rôles,
chacun par son libellé et son code (EP-14/L42r), triés par le serveur sur chacune de leurs colonnes,
cherchés par lui sur le libellé et le code, filtrés par code (`code`, comme celui des nœuds), par
nœud (`org_node_id`, offert dans l'ordre de l'arbre entier), par catégorie (`cost_category_id`), par
calendrier (`calendar_id`) — chacun offert parmi tous ceux que la session lit, lus comme une liste
de choix (#303), les catégories absentes quand l'API les refuse — et par état, et paginés ; les
calendriers, triés sur chacune de leurs colonnes, les heures de chaque jour comprises, cherchés,
filtrés par état et paginés, sans filtre sur les heures de leurs jours (WF-IHM-0130-A, #1047). Les
colonnes de nombres se bornent (#545, WF-IHM-0130) : les heures mensuelles et l'effectif d'un rôle,
le taux d'une année de la grille des taux — l'année choisie parmi celles de la grille, écrite avec
ses bornes (`rate_year`) —, sous la convention du contrat pour toute liste, `<colonne>_min` et
`<colonne>_max`, incluses (`docs/api/DECISIONS.md`). Le filtre est un composant de la grille,
réutilisable pour les montants des lots suivants (`RangeFilter` de
`components/grid/range-filter.tsx`, `boundsHref` et `readBounds` de `filters.ts`) : un formulaire
par liste, chaque borne saisie comme la langue écrit un nombre (`parseDecimal`) et écrite comme le
contrat l'écrit, ramenant la liste à sa première page ; une saisie qui n'est pas un nombre, ou un
montant de plus de deux décimales, se dit à son champ, qui prend le focus, sans rien demander. Le
serveur seul juge les bornes : celle qu'il refuse (422) — pas un nombre de son type
(`NUMBER_INVALID`), une borne supérieure sous l'inférieure, qu'il nomme (`VALUE_OUT_OF_RANGE`),
l'année du taux manquante (`VALUE_REQUIRED`) — se dit à son champ, qui prend le focus
(`refusedBounds`, `refusedSides`), et la liste n'est pas lue (`shownPage` d'`address.ts`,
`BoundsRefused`) ; le reste de l'écran l'est. Chaque champ se nomme par sa colonne et son côté, tous
deux écrits à côté de lui (« Heures par mois, min. », WCAG 2.5.3). L'arbre se borne aussi sur la
profondeur (`level_min`, `level_max`), à côté du choix d'une profondeur (`level`) ; le taux ne se
borne qu'avec une année que le contrat prend, sans quoi la page ne présente pas sa borne. Chacune
des grilles du référentiel est cherchée par le serveur, a sa clé de préférences, où son tri se
garde, et écrit son tri, sa recherche, ses filtres et sa page dans l'adresse sous ses propres noms,
ceux du contrat après son préfixe (`org_`, `role_`, `calendar_`, `type_`, `category_` :
`role_search`, `role_sort_by`, `role_cost_category_id`, `role_is_active`, `role_offset` ;
`prefixedAddress` de `query.ts`, `GridConfig.address`) — la grille des taux, celle de la fonction,
garde les noms du contrat — : les grilles d'un même écran ne se lisent pas l'une l'autre, et la page
demande l'API sous les noms du contrat ; l'arbre entier est relu quand une recherche ou un filtre le
restreint, pour les filtres des rôles. Un tri, une recherche ou un filtre ramènent leur liste à sa
première page ; un lien de page part de la dernière adresse demandée, et mène à la première page
quand elle lit la liste autrement que celle montrée — le tri d'une autre liste de l'écran n'y
comptant pas (`ListPages` de `components/grid/list-pages.tsx`, nommé d'après sa liste, la seule
règle de « même liste » de `readingOf`) ; la ligne des totaux dit combien le serveur en retient
(`meta.total`). Les unités de durée suivent : trois constantes, que la commande « Modifier les
unités de durée » — offerte à qui porte `resource_settings.write`, comme les calendriers — ouvre en
formulaire (`DurationUnitSettings` de `settings-forms.tsx`, `setDurationUnits`), en décimaux de la
langue ; le refus (422) se dit au champ, la version périmée (412) propose de relire, la réponse
prend la place des valeurs lues, et une phrase sous les champs dit que le changement vaut pour tous
les projets, les plannings des révisions en cours étant recalculés et une révision marquée gardant
ses heures (WF-PLA-0160, WF-REF-0130, #1049). Les paramètres des risques présentent les bornes de la
matrice et la zone de chaque case, placée par son rang dans l'ordre du contrat, ceux des indicateurs
les seuils des indices et le délai entre deux revues : des matrices de taille fixe, qui restent des
tables simples, sans tri ni filtre (décision de l'auteur du 2026-10-08, #508). Un objet rattaché se
nomme par le libellé que le serveur résout à la lecture, actif ou désactivé — jamais en rapprochant
des listes dans le front ; une section se nomme par `aria-label` (#251).

Chaque liste du référentiel dit ce qu'elle montre des objets désactivés par son propre filtre
d'état (`is_active` sous le préfixe de sa grille, `StateFilter`, WF-REF-0150, US-2090), un filtre
par défaut de la grille comme les états de la liste des projets (#1747) : absent de l'adresse et des
réglages du compte, il vaut « Actifs », dit par la pastille « État : Actifs (par défaut) » ;
« Désactivés » les montre seuls ; la pastille ôtée les montre tous, l'adresse écrivant alors `all`
pour que ni le compte ni le défaut ne reprennent la place (`stateOf`, `EVERY_STATE` d'`address.ts`).
Le front envoie `is_active=true`, `is_active=false`, ou `include_inactive=true` sans `is_active`
(`stateQuery`). Le choix se garde avec les réglages de la grille, par compte, dès qu'il diffère du
défaut (`keptState`, `GridConfig.defaulted`, `kept-filters.ts`). L'écran n'a plus d'interrupteur
« Afficher aussi les désactivés », et `include_inactive` dans son adresse n'est plus lu (#3076). Le
filtre n'est offert qu'à une session qui porte la permission d'écriture de leur partie du
référentiel, sans laquelle le contrat refuse les désactivés (403 ; décision #2084, option A,
`docs/api/DECISIONS.md`) : une autre ne lit que les actifs, comme les listes du devis (#351). Les
listes de choix des formulaires n'offrent que les actifs, quoi que montrent les tables. Un objet
désactivé s'y dit par une marque et un mot, et s'y réactive comme le serveur liste sa commande
(`available_commands`, #532, WF-IHM-0090) — le serveur ne la liste qu'à qui peut modifier cette
partie, et le front n'en déduit rien : disponible, par la commande d'activation de sa nature
(`setActivation`, une action serveur, depuis la version lue), puis la page relit ses listes ;
indisponible — un nœud sous un parent désactivé, un rôle sous un nœud désactivé (WF-REF-0080) —,
présentée `aria-disabled`, décrite par ses conditions, et un appui les dit dans la région de la
liste sans rien demander, comme la suppression d'un rôle porté (#515) ; absente, rien. Un objet ne
porte que la commande qui change son état, `deactivate` sur un objet actif, `reactivate` sur un
désactivé, l'une et l'autre par la même cellule (`StateCell` de `commands.tsx`, EP-02/L43,
ci-dessous) ; la désactivation du calendrier par défaut est indisponible (WF-REF-0120). Le refus du
serveur — le conflit (409), qui nomme le nœud à réactiver d'abord d'après la ligne qui le connaît,
ou la version périmée (412), avec l'offre de relire — se dit au-dessus de la liste
(`Reactivations`), qu'une cellule de grille n'a pas la place de dire, jusqu'à ce qu'on ferme son
avis — un refus arrivé pendant qu'un autre est dit s'ajoute à lui, sans le remplacer, sauf celui de
la même commande sur le même objet, qui prend sa place ; un succès après lui ne l'efface pas, et le
focus revient au contrôle qui a écrit quand le refus en nomme un (`back`, une case de la matrice des
permissions), sinon à la cellule active de la grille, ou à la liste —, et seulement tant que la
liste se lit comme au moment de la commande : les paramètres qu'elle lit (`listReads`), le tri d'une
autre liste de l'écran n'y comptant pas. Dans une grille, la commande est hors de la tabulation, et
Entrée sur sa cellule la presse (`CELL_COMMAND`, `grid-keyboard.ts`). Le faux back ignorant les
filtres, les pages et `include_inactive`, et ne gardant rien (« Ce que le faux back ne fait pas »),
les tests éprouvent ce que l'écran demande ; le service le tiendra en EP-05.

### Les paramètres de coûts : natures et catégories

Les paramètres de coûts offrent les commandes d'écriture des natures et des catégories (EP-02/L43a,
décision de l'auteur du 2026-10-08, #512 ; `commands.tsx`, `reference-form.tsx`, `cost-form.tsx`),
pour projeter la mise en page et éprouver le contrat de chaque écriture ; ceux des ressources les
leurs (EP-02/L43b, plus bas), par les mêmes pièces. À une session qui porte `cost_settings.write`
(`platformOffer`), chaque liste offre « Nouvelle nature » ou « Nouvelle catégorie » à côté de son
titre — liste vide comprise —, et chaque ligne « Modifier », dans une colonne à elle ; l'état de la
ligne porte la désactivation ou la réactivation comme l'objet la liste (`available_commands`,
`StateCell`), et la présente indisponible avec ses conditions quand elle l'est — la dernière nature
de type provision pour risques et sa dernière catégorie se désactivent comme les autres depuis
EP-14/L42p, qui retire la règle de #578 ; aucune commande ne supprime (WF-REF-0010, WF-DAT-0080).
Une autre session n'en voit aucune. La création et la modification ouvrent un dialogue
(`ReferenceForm`, `ui/dialog.tsx`), que chaque liste rend par celui de sa nature (`CostDialog`,
`useListForm`) : le code, le libellé et le type d'une nature, choisi parmi les trois du contrat ; le
code, le libellé, la nature — parmi les actives, et celle de la catégorie modifiée, marquée
désactivée — et le code comptable d'une catégorie, exigé, d'un à vingt caractères (WF-REF-0040,
décision de l'auteur du 2026-10-09). Ce qu'une modification change suit les commandes de l'objet
(EP-02/L42g, WF-IHM-0090) : le type d'une nature n'est offert que si elle liste `change_kind`
disponible, et se présente sinon figé, en lecture seule (`control: "fixed"` d'un `FormField`), ses
conditions dites sous lui (`note`) — une catégorie employée (`cost_type_unused`) —, la description
du dialogue le disant aussi ; une catégorie ne se voit proposer une nature d'un autre type que si
elle liste `change_cost_type` disponible, et sinon les natures de son type seules, ses conditions
dites sous le choix — employée, porteuse de taux (#577), rattachée à un rôle (EP-14/L42r) ; le refus
du serveur d'un changement de type, la condition levée depuis la lecture, nomme les rôles en cause,
par leur libellé et leur code, à rattacher d'abord à une autre catégorie de main-d'œuvre — d'une
autre nature, pour une nature — (`params.resource_roles`, `problemMessage`, WF-IHM-0090), que
l'écran des coûts ne lit pas. Le type se compare par le `kind` de chaque nature, désactivées
comprises : pour une session qui écrit, la page lit toutes les natures avec `include_inactive=true`
(`every` de `CostDialog`), une lecture entière distincte des choix du filtre, qu'elle ne fait pas
quand ceux-ci comprennent déjà les désactivées ; une catégorie sous une nature désactivée se voit
ainsi proposer les natures actives de son type, et sa nature désactivée se nomme par son code, que
cette lecture donne. Une nature qu'aucune lecture ne donne — une session qui écrit sans pouvoir lire
les désactivées, à qui le contrat refuserait `include_inactive` (403), et pour qui la page ne la
demande pas — laisse à la catégorie sa seule nature, et la note le dit à part (« Le type de la
nature désactivée n'est pas lisible : seule elle est proposée. »). `costs/page.test.tsx` éprouve ce
que la page passe au formulaire, les natures servies par `cost_types_with_inactive`, la lecture avec
les désactivées, qui ne vaut que pour elle. Un nœud dont le code est pris est nommé de même, d'après
l'arbre ou la liste, sinon par le libellé que le refus donne (`OrgNodeDialog`). Le formulaire refuse
à son champ ce qui manque, ou un nombre qui n'en est pas un dans la langue du lecteur
(`parseDecimal`), avant toute demande, et le champ prend le focus ; le serveur juge le reste : un
refus par champ (422, `fields[]`, convention #293) se dit au champ qu'il désigne, par la phrase de
son code et de ses paramètres — `problemMessage` d'un `FieldProblem`, le premier champ refusé
prenant le focus —, comme une valeur déjà portée (409 `ALREADY_EXISTS`, `fields[]`), qui nomme
l'objet qui la porte (`fields[].params.conflicting_object_id`) par son code et son libellé quand la
liste le montre (`names` de `ReferenceForm`), de façon générique sinon ; le décodeur en tire aussi
l'objet du refus (`conflictingObjectId`) quand l'enveloppe n'en nomme pas. Tout autre refus se dit
sous le formulaire (`OutcomeNotice`), qui reste ouvert — un état qui interdit l'écriture (409
`STATE_FORBIDS_OPERATION`) avec sa condition, la version périmée (412) avec l'offre de relire la
page ; un refus par champ que le formulaire ne montre pas y reste seul, sans répéter ce qui est dit
aux champs. Le bouton d'envoi dit l'écriture en cours ; fermé pendant l'attente, le dialogue ne fait
rien taire : le succès se dit dans la région de la liste, le refus au-dessus d'elle, sur la lecture
d'où il est parti. Fermé, il rend le focus à la cellule de la ligne — la grille est un seul arrêt —
ou à la commande de création. `problemMessage` lit aussi les paramètres des refus par champ d'une
enveloppe : le minimum d'un taux refusé se dit avec le refus de la cellule, écrit dans la langue du
lecteur (« Valeur minimale : 0,01. »). Toute écriture répondue relit la page (`refresh`) : les
natures sont ce par quoi les catégories se filtrent et se rattachent, les catégories de main-d'œuvre
les lignes de la grille des taux, et un choix qui offrirait encore une nature désactivée serait une
commande que le serveur refuserait (WF-REF-0010) ; une écriture change aussi les commandes d'autres
objets — le rattachement d'une catégorie le type de l'ancienne et de la nouvelle nature (#577) —,
que sa réponse ne porte pas. Un taux ne relit la page qu'à sa première saisie : la catégorie qui
porte des taux ne se rattache plus à une nature d'un autre type (`cost_category_unrated`) ; une
première saisie refusée comme un second taux de l'année (409 `ALREADY_EXISTS`) relit aussi la page,
et la cellule montre le taux de l'année avec sa version, que la saisie suivante corrige ; une
correction ne change aucune commande. Cette relecture, à la même adresse, n'abandonne rien de la
grille des taux : un taux parti avant elle reste en attente, le refus dit le reste, et un taux
répondu, avant ou après elle, garde sa cellule tant qu'il est plus récent que la cellule relue, par
le `lock_version` du taux — la réponse est le changement d'une cellule, trouvée par son année parmi
celles de la ligne relue et reposée sur elle (`RowPart.versioned`, `rate-cells.ts`), une ligne de la
grille n'ayant pas de compteur à elle ; ailleurs, une réponse se juge en bloc par le compteur de ce
qu'elle a écrit (`GridConfig.fresher`, le `lock_version` d'un nœud) : plus récente que la relecture,
elle garde tout ce qu'elle a rendu, les récapitulatives recalculées et les totaux compris, une
réponse plus récente l'emportant toujours sur une plus ancienne pour une même ligne ; rattrapée,
elle cède tout ; là où le compteur ne dit rien — même version, ligne sans compteur, faux back —,
chaque valeur reste tant que la relecture lit sa ligne, ou ses totaux, comme avant. Seule une
lecture à une autre adresse — un tri, une recherche, un filtre, une page de la grille — abandonne
les réponses en cours ; une lecture qui rend les mêmes lignes dans le même ordre, une autre liste de
l'écran triée ou l'adresse réécrite par `history.replaceState`, est la même (`cell-writes.ts`,
défaut n° 22). Cette dernière règle suppose que le contenu d'une ligne ne dépend pas de l'adresse :
le jour où une grille calcule ses lignes d'après un paramètre de l'adresse — une devise, une date de
valeur —, deux lectures aux mêmes lignes ne sont plus la même, et la règle devient fausse. Une
modification ou une activation répondue remplace sa ligne par ce que le serveur rend, tant que la
réponse est plus récente que la ligne lue (`lock_version`, `useAnswered`) — face au faux back, qui
ne garde rien, elle survit donc aux relectures — ; une création n'ajoute aucune ligne, la page relue
la range où le serveur la retient. Ce qu'une écriture a fait se dit dans la région de sa liste (« «
Débours » désactivée. ») ; le refus d'une activation, au-dessus de la liste comme celui d'une
réactivation (`useListReport`). Le service garde ce qui s'écrit (EP-05, US-0820 à US-0830) : l'écran
des coûts ne porte plus `MockupNotice`, et un succès est ce que le service a gardé, relu. Le faux
back, qui ne garde rien, reste joué par les parcours, qui n'affirment contre lui que ce qu'il répond ;
la relecture après rechargement ne s'affirme qu'en service (`inService` de `e2e/mode.ts`), et les
tests de `reference-costs.spec.ts` portent l'étiquette `@shared`, sauf ceux qui jouent aussi des
écrans pas encore servis (les rôles, US-0850). La saisie d'un taux reste celle de
la grille : le parcours en saisit un contre le service, qui répond ce qui a été saisi. Une année
ajoutée par la grille n'est qu'une colonne du front, vide, jusqu'au premier taux (aucune opération
ne crée une colonne, #299) : celle d'une année que la grille a déjà est refusée par la grille
elle-même (WF-REF-0060-A), contre le service comme contre le faux back.

La correspondance de l'extraction des coûts réels (US-0620/L2, WF-REF-0190, FBS-3.1.3) a sa page,
`/reference/costs/actual-cost-mapping`, que l'en-tête des paramètres de coûts offre par
`leafOf("FBS-3.1.3")` (`components/reference/actual-cost-mapping.tsx`) : les intitulés admis de
chacune des cinq colonnes lues et les colonnes conservées, en listes éditables, et une barre qui dit
les colonnes exigées sans intitulé d'après `is_complete` et `missing_columns` du serveur, jamais
recalculés. Sous `cost_settings.write`, un seul formulaire remplace la correspondance entière avec
le `lock_version` lu (`setActualCostMapping`) ; sous `cost_settings.read` seul, les listes se lisent
sans commande. Le serveur juge seul : un refus 422 se dit au champ par son pointeur
(`/columns/<rang>/labels/<rang>`, `/kept_columns/<rang>`), le doublon (`DUPLICATE_COLUMN_LABEL`)
nommant l'intitulé qu'il double (`params.duplicate_of`) ; la version périmée (412) se dit sous le
formulaire, avec l'offre de relire.

### Les paramètres de ressources : organisation, rôles et calendriers

Les paramètres de ressources offrent de même les commandes de l'organisation, des rôles et des
calendriers (EP-02/L43b, #512 ; `resource-commands.tsx`, `calendar-default.tsx`), à une session qui
porte `resource_settings.write` : « Nouveau nœud », « Nouveau rôle », « Nouveau calendrier », la
modification de chaque ligne, la désactivation ou la réactivation comme l'objet la liste — un nœud
avec ses descendants, que la réponse remplace dans l'arbre (WF-REF-0080), les rôles qu'elle
désactive avec lui étant ceux de l'autre liste, que la page relue montre. Un nœud s'écrit par son
code, son libellé et son parent — nul pour une racine, envoyé à la modification comme à la création
(`OrgNodeUpdate`) —, choisi dans l'ordre de l'arbre, chaque nœud décalé de sa profondeur
(`treeLabel`) : parmi les nœuds actifs seuls, que le nœud soit actif ou désactivé (WF-REF-0070,
EP-14/L43g), jamais sous lui-même ni sous l'un de ses descendants, qu'il emmène ; son parent est
toujours offert, d'après `parent_id` et `parent_label`, marqué désactivé quand il l'est, et la liste
le montre choisi — le contrat ne refuse un parent désactivé que si la modification le change ;
désactivé, il garde sa profondeur quand le nœud au-dessus de lui est offert, ou qu'il est une
racine, et alors sa place — dans l'arbre lu, le front ne réordonnant rien, ou sous son propre parent
quand la ligne de la liste le nomme — ; à la fin sans décalage sinon. Un rôle s'écrit par son code,
unique, désactivés compris (EP-14/L42r), son libellé, son nœud, une catégorie de main-d'œuvre et son
calendrier — parmi les actifs, celui du rôle modifié marqué désactivé quand il l'est (WF-REF-0090),
nommé sans marque quand la liste n'est pas lue, faute de savoir s'il l'est, ou quand toutes les
catégories lues le disent actif, une catégorie dont la nature a quitté la main-d'œuvre (`read`
d'`offered`, #714) : un garde-fou seul, le contrat interdisant ce cas depuis EP-14/L42r
(`docs/api/DECISIONS.md`, la mention de L42r dans la section de L42j) — et sa capacité, heures par
mois et effectif, saisis dans la langue du lecteur (WF-REF-0100) ; son nœud se fixe à la création,
et sa modification le nomme sans l'offrir : un rôle se recrée sous un autre nœud (§3.4.4.2.1). La
catégorie de main-d'œuvre se reconnaît au type de sa nature, que chaque catégorie dit
(`cost_type_kind`, `labourOf` de `kinds.ts`, EP-14/L43g) : la page ne lit pas les natures pour cela.
Une session à qui l'API refuse les catégories ne peut en choisir aucune : « Nouveau rôle » ne lui
est pas offert (WF-IHM-0090), et la modification nomme la catégorie du rôle comme sa ligne la nomme.
Un code pris se dit au champ, le rôle qui le porte nommé par le libellé que le refus donne
(`conflicting_object_label`), la liste lue sans les désactivés pouvant ne pas le montrer. La
modification d'un objet répondue pour un autre objet est une panne du service (`INTERNAL_ERROR`),
dite sous le formulaire comme la réponse d'une cellule pour une autre ligne. Un calendrier s'écrit
par son libellé et ses sept valeurs d'heures, du lundi au dimanche, rien d'autre (WF-REF-0110). Un
calendrier se désigne par défaut depuis sa ligne comme il en liste la commande
(`CalendarCommand.set_default`, `setDefaultCalendar`, WF-REF-0120, EP-14/L43g), depuis la version
lue, la page relue montrant le précédent sans la désignation : absente — sur le calendrier par
défaut, ou pour une session qui ne modifie pas —, rien, le front ne déduisant rien de l'état de la
ligne ; indisponible pour un calendrier désactivé, présentée `aria-disabled`, décrite par sa
condition (`calendar_active`), et un appui la dit dans la région de la liste sans rien demander
(`UnavailableCellCommand`) ; le refus du serveur — le calendrier désactivé entre-temps (409), la
version périmée (412), avec l'offre de relire — se dit au-dessus de la liste. Un refus par champ se
dit au champ (`ReferenceForm`) : une référence inconnue (`UNKNOWN_ORG_NODE`,
`UNKNOWN_COST_CATEGORY`, `UNKNOWN_CALENDAR`), un nœud placé sous lui-même ou l'un de ses descendants
(`ORG_NODE_CYCLE`), une catégorie hors main-d'œuvre (`LABOUR_CATEGORY_REQUIRED`), un parent, un nœud
ou un rattachement désactivé entre-temps (`INACTIVE_REFERENCE_OBJECT`), des heures hors de 0 à 24 ou
une capacité négative, avec la borne franchie (`VALUE_OUT_OF_RANGE`) ; le libellé déjà porté d'un
calendrier, désactivés compris, nomme son porteur d'après la page, par son identifiant, de façon
générique sinon ; le reste comme pour les coûts, la version périmée sous le formulaire avec l'offre
de relire ; l'écran ne porte plus `MockupNotice` depuis US-0850 : le service garde ce qui s'écrit,
et ses parcours sont étiquetés `@shared` (les unités de durée aussi, avec `@serial`).
Une écriture qui laisserait une tâche sans heure travaillée — un calendrier
modifié ou désigné par défaut, un rôle modifié — est refusée (`TASK_WITHOUT_WORKING_HOURS`, « Une
tâche n'aurait plus aucune heure travaillée dans la semaine. ») en disant pourquoi et en nommant
chaque projet en cause par son libellé et son code, par son seul libellé sans code
(`params.projects`, WF-PLA-0010), jusqu'à cinq dans la phrase, en liste hors de l'alerte au-delà,
comme les lignes d'un sous-projet. La cause est celle de `params.resource_roles` : les rôles dont
les calendriers ne se recoupent aucun jour, que le refus nomme lui-même par leur code et leur
libellé, partout où il se dit, le planning compris, la page n'en lisant aucun ; une liste vide
désigne le calendrier par défaut, vidé ou désigné, quand seules des tâches sans ligne de
main-d'œuvre perdent leurs heures.

Le service sert les rôles depuis US-0850 (`api/resource_roles.py`, le fichier `resource_roles` de
l'interface de `resource_settings`) : les actifs se lisent par toute session ouverte, les désactivés
(`include_inactive`, `is_active` faux) et toute écriture sous `resource_settings.write` (décision
de l'auteur, #2084). Un rôle naît actif, sous un nœud actif, et ne se réactive que sous un nœud
actif ; la création, l'activation d'un rôle et celle d'un nœud se font sous le verrou consultatif de
l'arbre, que la cascade tient aussi : la désactivation d'un nœud désactive, dans la même
transaction, ses descendants et les rôles rattachés à lui ou à l'un d'eux, chacun son compteur
avancé et son auteur, et la réponse les porte. `resource_settings` ne lit pas `cost_settings`, qui
le lit (`category_has_roles`, `roles_of_categories`, #2114) : la route demande aux paramètres de
coûts ce qu'un rôle sait de sa catégorie — main-d'œuvre, active —, sous le verrou consultatif des
natures, partagé et pris avant tout autre — celui de l'arbre, la ligne du rôle —, comme les
écritures des paramètres de coûts le prennent avant leurs lignes, et le libellé de chaque catégorie
nommée ou triée (`category_labels`, `category_label_of`). La tranche du témoin
(`witness/resource_roles.py`) crée les rôles de `resource_roles.json` par la même interface, puis
désactive ceux qu'il dit désactivés ; un rôle ne naît ni sous un nœud ni avec un calendrier
désactivés : le calendrier d'un rôle, que la tranche des calendriers a désactivé
(`calendars_with_inactive.json`, #2131), et le nœud de son rattachement, que celle des nœuds a
désactivé en cascade, sont rouverts le temps de l'écrire, puis refermés.

### Les paramètres des risques et des indicateurs

Les paramètres des risques et des indicateurs se modifient chacun dans un formulaire (EP-14/L43e,
#512 ; `settings-forms.tsx`), offert par « Modifier la matrice de risques » à une session qui porte
`risk_settings.write`, par « Modifier les seuils et le délai » à une session qui porte
`indicator_settings.write` (`platformOffer`) ; une autre session lit les tables seules. Servis par
le service depuis US-0810/L2, ils ne portent aucun avis de la maquette : un succès est ce que le
service a gardé, relu. L'un saisit les six bornes, en pourcentages (`editablePercent`,
`percentRatio`), et les seize zones, un choix par case ; l'autre les quatre seuils, en valeurs de
l'indice, et le délai, en semaines entières (`control: "whole"`, un nombre entier, signe compris,
ses bornes au serveur, jugé au champ avec les autres, dit par le texte propre au champ, `invalid`).
Chaque écran suit sa seule permission : une session qui porte l'une sans l'autre lit l'autre écran
sans commande ni avis. Chacun envoie par `updateReferenceSettings` le seul sous-objet de son écran
et la version lue (`RiskMatrixWrite`, `IndicatorWrite`), jamais un champ de l'autre écran, que garde
une autre permission ; ni la devise (WF-REF-0140) ni la langue de l'installation, qui est à EP-03,
n'y sont offertes. Le formulaire du référentiel range côte à côte, sous une légende, les champs qui
vont ensemble (`group` d'un `FormField`, un `fieldset` qui se replie sur deux colonnes dans une
fenêtre étroite) : les bornes d'un axe, les zones d'un niveau de probabilité, les deux seuils d'un
indice, chaque champ nommé par la légende de son groupe puis par son libellé (`aria-labelledby`),
que les groupes répètent ; et il juge, dans le même envoi que les champs, sur ceux qui sont passés,
les règles qui lient des champs entre eux (`rules`), avant toute demande — un champ refusé n'a pas
de valeur, qu'une règle laisse sans jugement, et son propre refus l'emporte ; tout ce qui est refusé
se dit en une fois (EP-14/L52) — : chaque borne qui n'est pas strictement au-dessus de la
précédente, à son rang (`BOUNDS_NOT_ORDERED`), chaque seuil d'alerte qui n'est pas sous son seuil de
vigilance (`THRESHOLD_NOT_BELOW_WATCH`), dits au champ que le serveur désignerait, les décimaux
comparés sans flottant (`compareDecimals`). Le refus du serveur se dit de même : par champ au champ,
la permission manquante (403) et la version périmée (412, les deux écrans partageant le compteur)
sous le formulaire. La réponse prend la place des paramètres lus tant qu'elle est plus récente
qu'eux, la page relue, comme les paramètres du projet, et ne ferme que le dialogue d'où elle est
partie, jamais un dialogue rouvert depuis ; la commande qui l'ouvre attend, inactive, la réponse
d'une écriture d'un dialogue fermé (#661) ; face au faux back, qui répond par le premier exemple de
l'opération quoi qu'on écrive, la matrice montrée est celle de l'exemple, et le parcours
(`e2e/reference-settings.spec.ts`, étiqueté `@shared`) n'affirme la relecture que par `inService`.

### Les écrans de l'administration

Les écrans de l'administration (`frontend/src/app/admin/`, `frontend/src/app/system/`,
`frontend/src/components/admin/`, US-0250) sont hors projet eux aussi, et en lecture seule hors
celui des rôles, branché sur le service (plus bas) : les comptes, désactivés compris par défaut
(`include_inactive`), chacun avec ses rôles et son nœud nommés par le serveur, sur la grille dense
(#514, `admin-grids.tsx`), triés sur chaque colonne, cherchés, filtrés par origine (`origins`,
`ValuesFilter`), par nœud d'organisation (`org_node_id`, offert dans l'ordre de l'arbre,
`OrgNodeFilter`), par rôle d'habilitation (`access_role_ids`, les rôles que `listAccessRoles` rend,
aucun à une session qui ne les lit pas ; tous choisis filtrent encore, un compte sans rôle n'étant
retenu par aucun, `exhaustive: false`, EP-02/L42f) et par état, un seul choix (`is_active`) — tous,
les actifs seuls, les désactivés seuls —, qui dit ce que la grille montre : la page demande toujours
les désactivés aussi (`include_inactive=true`, le contrat les masquant par défaut), une adresse
d'avant qui les masquait (`include_inactive=false`) se lit « Actif » (`readAccountState`),
un filtre de la grille, gardé avec ses réglages comme les autres (`USER_FILTERS`, #2916) — seul
dans l'adresse, il n'est donc pas remplacé par les filtres gardés —, et tout choix lève ce paramètre ancien (`lifts` de `ChoiceFilter`) — et paginés par le serveur, sous
les noms du contrat — un tri, une recherche ou un filtre ramenant à la première page —, la ligne des
totaux disant combien le serveur en retient (`meta.total`), l'écran remplissant la fenêtre ; la
recherche porte sur le nom, le prénom, l'adresse et le nom affiché, sans égard à la casse ni aux
accents, comme toute recherche du contrat. Les rôles d'habilitation sont sur la grille dense eux
aussi (#515), triés sur chaque colonne, cherchés et filtrés par le serveur — leur nature
(`is_predefined`, `ChoiceFilter`), leurs porteurs entre deux bornes incluses (`holder_count_min`,
`holder_count_max`, `RangeFilter` de forme `count`, un entier depuis zéro ; une borne refusée dite à
son champ, la liste non lue) —, sans pagination — le §4.6.2 ne compte aucun rôle, trois sont
prédéfinis, et le contrat ne les pagine pas —, et la matrice des permissions montre les rôles que la
table retient, dans son ordre (US-0380) — une ligne par permission dans l'ordre du catalogue, les
permissions consécutives d'une même fonction de second niveau, ou d'une même nature hors fonction,
groupées sous un en-tête de groupe (`scope="rowgroup"`) qui nomme la fonction — jamais par son code
de la FBS, une clé interne qu'aucun écran ne montre (décision de l'auteur du 2026-10-08, #515) —,
une colonne par rôle, accordée ou non dite par un mot ; l'état du système ; les sauvegardes et leur
planification, dont les commandes sont branchées au contrat (EP-02/L43c, plus bas). Les tables des
comptes et des rôles finissent sur leurs colonnes d'audit (#936, `audit-columns.tsx`) : « Créé le »,
« Créé par », « Modifié le », « Modifié par », chacune triée par le serveur sous le nom de son champ
(`created_at`, `created_by`…), un instant en heure locale (`LocalTime`), un auteur par le nom que la
ligne garde du compte — désactivé depuis, toujours nommé ; anonymisé, le libellé neutre — ou la
plateforme par son propre libellé (`ActorCell`). Chacune se filtre (`audit-address.ts`,
`audit-filters.tsx`) : une période de jours locaux par colonne de dates (`PeriodFilter` de forme
`day`, sous `created_at_from` et `created_at_to`, `updated_at_from` et `updated_at_to`), une fin
refusée dite à son champ, la liste non lue ; un auteur par colonne d'auteurs (`AuthorFilter`), un
seul choix qui écrit un compte (`created_by_user_id`) ou une sorte d'auteur — un compte quel qu'il
soit, ou la plateforme (`created_by_kind`) —, chaque choix levant le paramètre des autres (`name`
d'un `Choice` de `ChoiceFilter`). Le contrat n'a pas de liste des auteurs : les rôles offrent ceux
de la liste sans filtre, relue à part quand la grille la restreint ; les comptes, ceux de la page
montrée, et ceux qu'une recherche des comptes trouve (`findAccounts`, `listUsers` cherché, vingt au
plus). Ces filtres sont gardés avec les réglages des deux grilles, comme les autres. La recherche et
les filtres de la table des rôles sont gardés avec les réglages de sa grille (`GridConfig.filters`,
`kept-filters.ts`, sous `filters` de `GridPreferences`, tels que l'adresse les écrit) : enregistrés
dès que la page en montre d'autres que ceux gardés — une lecture levée comprise —, et retrouvés
seulement sur une adresse qui ne dit rien de la grille, ni tri, ni recherche, ni filtre, que la
page, sur le serveur et avant toute lecture, redirige vers celle des filtres gardés
(`restoredAddress`, `kept-address.ts`), comme elle prend le tri gardé quand l'adresse n'en dit rien
— d'où qu'on vienne, le lien de la barre latérale suivi depuis l'écran compris. La levée du dernier
filtre se dit dans l'adresse, la recherche écrite vide (`search=`, `spokenHref`, que pose le
`PendingAddress` d'un écran qui nomme ce que garde sa grille), comme un tri levé écrit `sort_by`
vide : la préférence se vide, et la page ne retrouve pas les filtres gardés (#836). L'écran des
rôles est branché sur le service (US-0380/L2, #380) : à une session qui porte `access_roles.write`,
la table crée un rôle par son seul libellé, dans le dialogue que « Nouveau rôle » ouvre — le bouton plein, à droite du titre de la carte (`role-commands.tsx`, `role-creation.tsx`) —, le renomme dans sa
cellule — la saisie de la grille, écrite par `updateAccessRole` avec les permissions du rôle — et le
supprime depuis sa ligne, après une confirmation qui nomme le rôle et dit la suppression définitive
(`AlertDialog`, hors de la grille, Échap l'abandonnant) — une suppression logique (#456), que rien
ne restaure, un rôle prédéfini compris —, indisponible, `aria-disabled` et décrite par sa condition,
tant qu'un compte porte le rôle (`ACCESS_ROLE_IN_USE`, WF-ADM-0090) ; la matrice est le lieu de la
modification des permissions, une case à cocher par permission et par rôle
(`permission-matrix.tsx`), qui écrit le rôle entier, ses permissions dans l'ordre du catalogue, les
autres cases du rôle attendant la réponse. La table et la matrice lisent une seule source du rôle
répondu le plus récent par sa `lock_version` (`RoleAnswers`, `role-answers.tsx`), et des rôles en
écriture : tant qu'une écriture d'un rôle — son renommage, une case de la matrice ou sa suppression
confirmée — est en route, la ligne de ce rôle est occupée, la cellule de son libellé, ses cases et «
Supprimer » marquées `aria-busy` et `aria-disabled` et n'envoyant rien, et l'écriture suivante part
de la version répondue, sans 412 (une saisie du libellé ouverte avant l'écriture ne part pas et
reste ouverte ; une confirmation de suppression ouverte avant elle reste ouverte, sa commande
occupée) ; une écriture d'un autre rôle n'attend pas (#2261). Une relecture plus ancienne que la
réponse ne la défait pas ; l'en-tête de la colonne d'un rôle renommé et le nom de chacune de ses
cases prennent eux aussi le libellé répondu (`RoleLabel`, `PermissionCell`), sans attendre la
relecture (#976). Ce que fait une commande de la table se dit dans sa région, nommée «
Commandes des rôles d'habilitation » ; un refus, par le catalogue des codes d'erreur au-dessus de la
table ou de la matrice, sur la lecture d'où il est parti (`Reactivations`) — le dernier
administrateur (`LAST_ADMINISTRATOR`), la version périmée avec l'offre de relire —, le focus rendu,
le refus fermé, à la case qui a écrit ; un libellé refusé par le serveur, ou blanc, refusé sans
appel comme la saisie de la grille (`parsedEntry`), se dit à son champ ; toute écriture répondue
relit la page. Pour les comptes (US-0360, #379), la table est sa propre saisie, à une session qui
porte `users.write` (`platformOffer`) : le nom et le prénom d'un compte local dans leurs cellules
(`updateUser`), ceux d'un compte de l'annuaire ou d'un fournisseur restant en lecture (WF-ADM-0050)
; l'état sur un interrupteur, son mot à côté (`setUserActivation`) ; les rôles dans une liste à
choix multiple des rôles de l'installation, quel que soit le rattachement (`setUserAccessRoles`,
`user-cells.tsx`) — chacun tel que le compte liste sa commande (`User.available_commands`) : une
commande absente n'est pas présentée, une indisponible l'est avec sa condition, et un clic la dit
sans la lancer — la cellule des rôles aussi (`RolesCell`, par `useUnmet` et `CommandTooltip`, #2262)
: attribution indisponible, son déclencheur est `aria-disabled` et la liste ne s'ouvre pas. La
désactivation du dernier compte actif qui porte les permissions de modifier les comptes et les rôles
est indisponible, `last_administrator` manquante (WF-ADM-0120, #540) — le front ne pourrait pas le
trouver seul, la liste étant paginée ; l'attribution de ses rôles reste
disponible, le serveur jugeant les rôles envoyés, et refusant par `LAST_ADMINISTRATOR` ceux qui lui
retireraient ces permissions — un refus dit comme tout autre. Le lien de fixation d'un compte local
(`createPasswordSetupLink`) se remet dans un dialogue, entier et en lecture seule, avec l'heure où
il cesse de valoir, jamais relu ; indisponible pour un compte désactivé (`is_active_account`),
absent d'un compte qui n'est pas local ou qui est anonymisé. « Créer un compte local », en tête de
la table, ouvre le dialogue du nom, du prénom et de l'adresse (`user-dialogs.tsx`) : un champ blanc
est refusé à son champ sans appel, l'adresse déjà portée dite à son champ ; quand aucune invitation
n'est partie (`invitation_sent` faux), le compte créé le dit et offre aussitôt son lien de fixation
(#816). La colonne « Anonymisation » porte la commande `anonymize` d'un compte désactivé
(`anonymizeUser`), après une confirmation qui nomme le compte et dit l'action irréversible
(`AlertDialog`, comme la suppression d'un rôle) ; un compte anonymisé est nommé par le libellé
neutre du catalogue, et ses nom et prénom ne se saisissent pas, son origine fût-elle locale
(WF-ADM-0060). Aucune suppression (WF-ADM-0060). Comme pour les rôles, une seule source du compte
répondu le plus récent par sa `lock_version` (`UserCommands`, `user-commands.tsx`) : l'écriture
suivante d'une ligne, quelle que soit sa cellule, part de sa version. Les écritures d'une ligne
passent l'une après l'autre : un nom saisi pendant qu'une autre écriture de sa ligne est en route
attend sa réponse et part de la version qu'elle a répondue, et l'interrupteur, les rôles et
l'anonymisation de la ligne se marquent occupés et indisponibles (`aria-busy`, `aria-disabled`) tant
qu'une écriture y est en route — l'anonymisation aussi tant qu'une réactivation demandée n'a pas
répondu. Ce que fait une écriture — un renommage compris — se dit dans la région « Commandes des
comptes » ; un refus de l'interrupteur, des rôles ou de l'anonymisation, au-dessus de la table, sur
la lecture d'où il est parti (`Reactivations`), celui d'un nom, à sa cellule. La recherche et les
filtres se gardent avec les réglages de la grille et se retrouvent quand l'adresse ne dit rien de la
table (`USER_KEPT`), comme pour les rôles. Sans la permission, rien ne s'écrit et aucune commande ne
se présente. Dans une carte sous la table, à droite de son titre une commande à contour, « Lire les comptes », et son état en corps, la lecture des comptes du fournisseur d'identité (US-0370,
WF-ADM-0070, US-2100, `identity-sync.tsx`) montre le compte rendu de la dernière lecture achevée
(`getLatestIdentitySync`), ou dit qu'aucune n'a encore abouti (404) : ses comptes créés, mis à jour,
désactivés, ceux dont elle a rétabli l'identité dans le fournisseur, les comptes locaux qu'elle en
retire, et, à la demande, ce qu'elle a laissé tel quel, chacun avec le motif du catalogue — un
compte nommé tel qu'il se lit à la consultation, sous le libellé neutre s'il est anonymisé depuis
(`useAccountNaming`, `AnonymizedName`) ; une personne du fournisseur par son nom et son identifiant
chez lui (#918) ; celle dont un compte porte l'adresse (`ALREADY_EXISTS`) par son identifiant et ce
compte, tel qu'il se lit, ou par son seul identifiant quand aucun ne la portait plus (#920). À une
session qui porte `users.write`, « Lire les comptes » (`startIdentitySync`) rend la main dès la
tâche en file et la confie au suivi, qui l'annonce achevée et offre de relire l'écran, sans jamais
le relire de lui-même. Une liste que le serveur pagine — comptes, sauvegardes — dit combien elle en
porte et mène aux pages voisines par `offset` (`ListPages`, pour les comptes comme pour les
sauvegardes), les autres paramètres de l'adresse gardés, sans jamais montrer une page pour le tout ;
elle ne se dit vide que si elle ne tient rien (`meta.total`) et que rien ne la restreint, et une
page demandée au-delà de sa fin le dit et ramène à la dernière — une seule règle pour toutes les
listes paginées, `pageOffsets` de `frontend/src/navigation/pages.ts` (#317). L'heure d'une
sauvegarde planifiée s'affiche telle quelle, en UTC, comme le contrat la donne : une heure du jour
n'a pas de date d'où tirer le décalage d'un fuseau à heure d'été. Son formulaire la saisit de même,
et dit à côté l'heure du poste qu'elle donne la semaine où il est ouvert — l'heure seule pour une
planification quotidienne, le jour local aussi pour une hebdomadaire, qui peut être la veille ou le
lendemain du jour universel (`localTimeOfDay` de `format.ts`, dans le navigateur) : rien n'est
converti à l'envoi.

### L'écran des sauvegardes

L'écran des sauvegardes (FBS-1.4, `/admin/backups`, EP-02/L43c, #519, EP-14/L43f, EP-14/L43d)
présente leur planification (`backup-schedule.tsx`) et une page de leur liste sur la grille dense
(`backup-columns.tsx`, `backup-grid.tsx`, préférences sous la clé `backups`) : la date, en heure
locale, la taille, la vérification, le déclenchement et la conservation, dans l'ordre du serveur, la
ligne des totaux disant combien il en retient (`meta.total`). Le serveur trie chaque colonne dans
les deux sens (WF-IHM-0060), les plus récentes d'abord quand l'adresse et le compte ne disent rien,
et le tri ne se lève jamais, comme celui du journal ; il filtre sur chaque colonne (WF-IHM-0130,
`backup-address.ts`), sous les noms du contrat : la période de la prise, deux jours du lecteur tirés
en instants, `from` compris et `to` exclu, comme l'accueil (`PeriodFilter`, `day`) ; le
déclenchement et la vérification, par leurs valeurs (`origins`, `verifications`, `ValuesFilter`) ;
la conservation, par un choix (`is_retained`, `ChoiceFilter`) ; la taille, par ses deux bornes en
octets, incluses (`size_bytes_min`, `size_bytes_max`, `RangeFilter`, sorte `bytes` : un entier qui a
plus de chiffres qu'un compte). Une liste filtrée ne se dit jamais vide, et une borne que le serveur
refuse (422) — une fin avant le début, un maximum sous le minimum — laisse la liste non lue, les
filtres gardés, la borne dite à son champ. « Sauvegarder maintenant », dans la tête de la liste,
liste vide comprise — une tâche de fond remise au suivi avec sa commande —, suit la permission
`backups.write` (WF-ADM-0100, `platformOffer`) ; les autres commandes sont celles que chaque
sauvegarde liste (`Backup.available_commands`, WF-IHM-0090, `backup-commands.tsx`), le front n'en
déduisant rien de la session ni de l'état de la sauvegarde : « Conserver » ou « Ne plus conserver »,
celle des deux qui change son marquage, dans la colonne de la conservation ; « Télécharger » et «
Restaurer », chacune dans sa colonne dès qu'une sauvegarde de la page la liste — le serveur ne liste
le marquage que sous `backups.write`, le téléchargement que sous `backups.read` et `backups.write`
(décision de l'auteur du 2026-10-10, #705, qui remplace celle du 2026-10-09, #588), la restauration
que sous `platform_restore` —, et aucune ne supprime. Une commande absente n'est pas présentée ; une
indisponible l'est, `aria-disabled` et décrite par la condition qui lui manque
(`enums.CommandCondition`) — `backup_verified` au téléchargement et à la restauration d'une
sauvegarde non vérifiée, `no_backup_running` à la restauration pendant qu'une sauvegarde court,
`no_restore_running` au marquage et à la restauration pendant qu'une restauration court —, et un
clic la dit dans la tête de la liste sans rien demander, comme les activations du référentiel. La
tête de la liste dit ce que la dernière commande a fait dès qu'une commande est offerte. Une
sauvegarde n'ayant pas de compteur, la réponse d'un marquage reste montrée tant que chaque relecture
lit la sauvegarde comme la précédente ; une relecture qui l'a changée l'emporte pour de bon, et une
démarque par un tiers que la relecture ne montre pas reste invisible (#588). Le téléchargement est
un lien vers la route `/admin/backups/[backupId]/content`, qui relaie `downloadBackup` en flux comme
le résultat d'une tâche (`src/api/relay.ts`, commun aux deux routes) : des octets, seul type que le
contrat déclare, sous le nom que l'API donne (`Content-Disposition`, que le contrat exige :
`waterfall-backup-`, l'instant de la sauvegarde et l'extension de son archive), avec sa longueur
quand le corps arrive sans `Content-Encoding` — tout autre type, ou un fichier sans nom, renvoie
l'erreur d'une mauvaise passerelle (502). Un refus — 403, 404 sans distinction (WF-ADM-0110), 409
d'une sauvegarde non vérifiée, 502, l'API injoignable — renvoie à l'écran des sauvegardes, sa page
et ses filtres gardés, l'adresse nommant la sauvegarde et le refus (`refused_backup`, `refusal`, les
noms paramétrés de `result-refusal.ts`) : l'écran le dit au-dessus de la liste jusqu'à ce qu'on
ferme son avis — le téléchargement nommé, la sauvegarde par sa date quand la page la porte —, et
l'avis, rendu avec la page, prend le focus au montage, sans quoi aucun lecteur d'écran ne
l'annoncerait ; l'adresse est rendue sans le refus une fois la page révélée (`afterReveal`), l'avis
fermé ou non. « Restaurer » ouvre un dialogue (`restore-dialog.tsx`) qui énonce la date de la
sauvegarde et sa vérification, la perte sans retour de ce qui a été saisi depuis, la déconnexion des
utilisateurs et l'inscription au journal d'audit (WF-ADM-0160, WF-SEC-0030) ; le bouton ne s'active
qu'une fois l'identifiant de la sauvegarde saisi, sans égard à la casse, et la demande énonce la
date dite (`acknowledged_backup_taken_at`). Pendant la demande, ni Échap, ni un clic au-dehors, ni «
Annuler » ne ferment le dialogue : un refus s'y dit — un état qui l'interdit (409), la condition
nommée comme tout refus ; une date confirmée qui n'est pas celle de la sauvegarde (400,
`CONFIRMATION_REQUIRED`, EP-03/US-0440/L2), dite à la date que le dialogue énonce, la liste lue
n'étant plus celle de la sauvegarde, et la page relue —, et rien ne part qu'on croie abandonné. Mise
en file, la restauration fait place à l'écran de sa maintenance (`restoration.tsx`,
`maintenance.tsx`, US-0440), qui suit sa tâche tant que la plateforme sert, puis la sonde de vie, et
dit la déconnexion des utilisateurs, puis la fin ; le suivi de la coquille ne la reçoit pas : une
restauration ne se relance que depuis cette confirmation. Le refus d'une commande de la liste se dit
au-dessus d'elle (`Reactivations`), la condition nommée pour un 409. La restauration depuis un fichier
passe par le dépôt par morceaux d'EP-03 (#350, `completeChunkedUpload`), offert à qui porte
`platform_restore` sous la liste, dont la date lue dans le manifeste est celle que la confirmation
nomme : le même dialogue, l'identifiant du dépôt saisi, sa vérification dite en attente — sa
restauration la fait (EP-14/L42o). La planification et les emplacements externes, que le service ne
sert pas encore (404), sont laissés de côté sans emporter la liste.

La planification se modifie, à une session qui porte `backups.write` (`platformOffer`), dans le
formulaire du référentiel (`ReferenceForm`), qui la renvoie **entière** depuis la version où il
s'est ouvert (`setBackupSchedule` est un `PUT`) : activée ou suspendue, la fréquence et l'heure en
UTC (un champ `time` : une heure à moitié saisie, que son champ rend vide, `validity.badInput`, est
refusée avant tout appel par la phrase propre à son champ, `invalid`, jamais envoyée comme « aucune
heure ») — exigées d'une planification activée seulement, le contrat ne les exigeant pas d'une
suspendue —, le jour — exigé d'une planification hebdomadaire, nul d'une quotidienne —, le nombre de
sauvegardes conservées, un nombre entier dont le serveur juge les bornes, signe compris ; un champ
exigé selon le brouillon le dit (`required` d'un `FormField`, une fonction du brouillon, qui donne
aussi `aria-required`, #678) ; puis la copie externe, offerte quand l'installation déclare un
emplacement ou que la planification en règle une : l'emplacement, choisi parmi ceux que la page lit
pour cette seule session (`listExternalBackupLocations`) par son nom et sa nature, sa description
sous le champ, jamais un secret ni une adresse — un emplacement réglé que l'installation ne déclare
plus reste offert par son nom, refusé au champ avant l'envoi (`UNKNOWN_EXTERNAL_BACKUP_LOCATION`)
plutôt que retiré en silence —, « Aucune copie » la retirant ; le dossier relatif ; le nombre de
copies, au moins celui des sauvegardes conservées (WF-EXP-0050), vérifié avant l'envoi et dit au
champ avec ce minimum, comme le serveur le dirait — pour une rétention dans ses bornes, de 1 à 365
(`RETENTION`), le reste revenant au serveur, qui donne alors le minimum des copies à 1 — ; la copie
active ou suspendue. Les règles entre champs passent par `rules` du formulaire, une note qui suit la
saisie par une fonction du brouillon (`note`), et ce qui suit les champs sans en être un par `after`
: « Tester l'emplacement » (`testExternalBackupLocation`), offert pour un emplacement que
l'installation déclare, qui dit l'emplacement éprouvé, l'instant du test en heure locale, le dossier
ou la racine, et la réussite ou le motif de l'échec (`enums.ExternalBackupFailure`) dans une région
annoncée ; un dossier refusé (422, `/path`) se dit sous le bouton par la phrase de son propre code ;
seule la réponse du dernier test demandé est dite, tant que le dossier saisi est celui qu'il a
éprouvé, et un autre emplacement choisi fait tomber le test en route. La réponse d'un enregistrement
remplace la planification affichée tant que son `lock_version` est plus récent que la lecture, la
page relue, et ne ferme que le dialogue ouvert d'où elle est partie (compteur d'ouvertures, comme
les paramètres du référentiel), la commande attendant, inactive, la réponse d'une écriture d'un
dialogue fermé (#661, #678) ; un refus par champ (422 : emplacement inconnu, chemin invalide,
rétention trop courte) se dit au champ, tout autre sous le formulaire, la version périmée (412) avec
l'offre de relire.

### Le journal d'audit

Le journal d'audit (FBS-1.5, WF-SEC-0030, `/admin/audit-log`, `frontend/src/components/audit/`,
#517) est un écran de l'administration à lui ; la table « Dernières opérations » de l'état du
système, trois faits de la plateforme (WF-ADM-0130), reste telle quelle. C'est une fonction en
lecture seule, qui n'a que sa permission de consulter (WF-ADM-0100) : `FunctionPermission` nomme
toute fonction par sa permission de consulter, et `WritableFunction` celles qui ont aussi la
permission de modifier, seules que `platformOffer` accepte. L'écran est gardé par `audit_log.read`,
introuvable sans elle comme une adresse qui ne mène nulle part (WF-ADM-0110). Il présente une page
des inscriptions de `listAuditEvents` sur la grille dense, en lecture seule (`audit-columns.tsx`,
préférences sous la clé `audit_log`) : la date, en heure locale, l'auteur, l'action et, sous elle,
ce qu'elle a fait à son objet — composé par le front dans la langue du lecteur à partir des codes et
des paramètres que l'inscription garde (`AuditEvent.params`, `useAuditDetails`), l'API ne rendant
aucune phrase (WF-ARC-0110) ; une seconde ligne dans la cellule de l'action, qui se trie par le code
de l'action — jamais une colonne à elle, que le serveur ne trierait pas (WF-IHM-0060) —, la nature
et le libellé de l'objet — une sauvegarde, qui n'en a pas, par sa nature, jamais par son identifiant
—, le projet et la corrélation, chacun tel que l'inscription le garde, et un lien vers l'histoire de
l'objet — le journal filtré sur sa nature et son identifiant, toute son histoire : les autres
filtres et la recherche levés, le tri gardé —, la corrélation menant de même aux inscriptions de sa
seule requête. Le `title` de la cellule de l'action n'est posé que si le texte y est tronqué, et il
porte alors l'instant de la sauvegarde restaurée ; la seconde ligne dit aussi une modification de
rôle sans changement. Le serveur trie sur chaque colonne (#550), dans les deux sens. Les plus
récentes d'abord quand l'adresse ne dit rien, et le tri ne se lève jamais (`GridConfig.lifts`) :
l'en-tête de la date demande d'abord le décroissant (`GridColumn.descendingFirst`), et ramène ainsi,
depuis un autre tri, à l'ordre par défaut. Un objet ne mène à son écran propre que si la session lit
sa fonction — les risques, le planning dont les échanges sont une feuille, les révisions —, sinon à
sa révision, qui mène à la première fonction lisible, et à rien sans fonction de révision à lire
(`auditReach`). La corrélation saisie ne part que sous la forme que le contrat accepte (`pattern` du
champ, que le navigateur dit). La recherche de la grille porte sur le libellé de l'objet (`search`).
Les filtres n'écrivent que l'adresse, sous les noms du contrat, et ramènent à la première page
(`audit-filters.tsx`) : la période, deux instants saisis en heure locale et envoyés en temps
universel — seul le navigateur connaît son fuseau, si bien que les champs montrent ceux de l'adresse
une fois la page hydratée ; une borne laissée telle quelle repart comme l'adresse la nomme, et une
saisie est datée par la période de l'adresse, le formulaire jamais remonté —, la nature de l'auteur
(`ValuesFilter`), l'auteur et le projet parmi ceux que nomme le journal entier (`listAuditFacets`,
que la seule consultation du journal lit : un auditeur sans `users.read` filtre par auteur) — sans
auteur à choisir ni auteur choisi, le filtre d'auteur n'est pas offert —, les actions dans un menu,
la nature de l'objet, l'objet dont l'adresse demande l'histoire, nommé et levé, et la corrélation,
saisie (`TextFilter`) ; un auteur ou un projet que l'adresse nomme sans qu'aucun choix ne l'offre
reste choisi sous le nom que les inscriptions lui donnent, et un auteur qu'aucune ligne lue ne nomme
est lu par `getUser`, au plus une fois, et nommé comme partout (`naming.person`), jamais par son
identifiant (#1010). Le projet et l'objet sont des liens là où la session peut les consulter — un
projet que le serveur dit qu'elle peut ouvrir (`AuditProject.can_open`, que rendent les inscriptions
et `listAuditFacets`, qui nomme les projets du journal entier, même ceux qu'elle ne peut pas ouvrir) — :
le projet, une révision d'un tel projet, et un objet qui vit dans une révision, vers son écran
propre dans celle que l'inscription nomme (`AuditObject.revision`) — un risque vers les risques de
la révision, son détail ouvert (`risk`), l'import d'un planning, d'un devis ou d'un reste à engager
vers ses échanges, son compte rendu montré (`import`), le différentiel d'un avenant vers les
structures de coûts de l'écran des révisions lu dans elle (`revision_id`) ; une ligne de coût réel
et l'import des coûts réels ne vivent dans aucune révision, et un compte, un rôle ou une sauvegarde
n'ont pas d'écran à eux : leur nom reste seul. Une période que l'API refuse (422, la fin désignée
hors de ses bornes) se dit à la place des inscriptions, les filtres gardés, et tout autre refus des
filtres par son enveloppe (`problemMessage`) ; aucune commande n'est offerte.

### L'écran des imports et exports

L'écran des imports et exports, `…/revisions/[r]/exchanges` (`frontend/src/components/exchanges/`,
US-0260), est la feuille FBS-4.3.4 du planning, dont l'en-tête y mène dans le même contexte, comme
celui de l'écran des coûts réels ; un import s'applique pourtant à la révision en cours, créée au
besoin (WF-INTF-0090), quelle que soit la révision lue. Un import se fait en deux temps
(WF-ARC-0100) : la commande de sa nature ouvre dans la page le choix du fichier — et, pour une
extraction de coûts réels, la période qu'elle couvre —, qu'une action serveur dépose pour un import
(`uploadFile`, `purpose: import`) puis analyse (`openImport`) ; un fichier de plus de 10 Mio, la
borne que le contrat donne au dépôt d'un import, est refusé dans la page, et la borne des actions
serveur de Next est réglée un peu au-dessus (`next.config.ts`). La tâche de l'analyse va au suivi de
la coquille, et l'adresse nomme l'import (`import`, un identifiant ou rien), dont la page lit le
compte rendu (`getImport`) — lignes lues, motifs de confirmation, lignes rejetées par leur place —
leur onglet quand le fichier en a, et leur rang — et leur motif, rendu comme un refus depuis son
code et ses paramètres (`problemMessage`), écarts avec les champs qu'ils changent, nommés par le
catalogue de leurs colonnes (`NodeColumn`, `ActualCostColumn`), tâches que le fichier date autrement
que Waterfall ne les recalcule (`date_mismatches`, WF-INTF-0040) —, dans l'ordre reçu. Les commandes
d'un compte rendu sont les siennes : un autre import montré les remplace. L'application n'est
offerte qu'à un import analysé, et ne part qu'une fois confirmée dans la page ; sa tâche va au
suivi. L'abandon ramène à l'adresse de départ, si l'écran montre encore cet import. Le compte rendu
nomme aussi ce que l'import ignore (`report.ignored`), les colonnes d'une extraction de coûts réels
par leur intitulé tel que le fichier le porte. Chaque import est offert comme le projet offre sa
commande (`importOffers`) : `import_planning`, `import_estimate`, `import_remaining`,
`import_actual_costs`, avec ou sans révision en cours — sans elle, qui ne peut pas créer la révision
voit l'import indisponible, `may_create_revision` nommée. Celui des coûts réels, indisponible faute
de correspondance (`actual_cost_mapping_complete`), dit en plus les colonnes exigées sans intitulé
et mène à la page de la correspondance (FBS-3.1.3) : les colonnes viennent de
`getActualCostMapping`, que la page lit (`readMappingGap`) pour qui porte `cost_settings.read`, les
autres lisant la condition seule. Les refus d'`openImport` — le 409 qui nomme les colonnes
(`columns`), le 422 `FILE_FORMAT_UNREADABLE` qui nomme chaque colonne absente avec ses intitulés
(`missing_columns`) — se disent par `problemMessage`. Un projet sans révision, qu'aucune adresse de
révision n'atteint, offre les mêmes imports sur son propre écran (`ImportPart`), et y montre le
compte rendu de l'import que son adresse nomme (#332). L'écran est gardé par les commandes qu'il
exerce, et non par la seule lecture du planning (#521) : il se montre à une session qui lit le
planning, dont il est la feuille, ou à laquelle le projet liste un import (`listsAnImport`) — un
chiffreur, que le devis et le reste à engager y mènent quand le projet liste leur import, disponible
ou non, l'écran le présentant alors avec ses conditions (`ExchangesLink`, WF-IHM-0090) ; il est
introuvable pour tout autre. La liste des imports, paginée par le serveur (`offset`, `ListPages` de
`components/grid/list-pages.tsx`), mène au compte rendu de chacun ; la demande d'export n'offre que
les natures que la révision lue offre d'exporter (`exportOffers`, `export_*`) — un export, gardé par
la permission de consulter sa nature, est présent ou absent —, et part pour cette révision — l'image
de l'arborescence au niveau demandé —, et le suivi n'offre de télécharger que le résultat d'un
export réussi (`givesFile` de `tracking.ts`), celui des autres tâches se lisant sur leur écran : le
serveur de Next le lit (`getBackgroundTaskResult`) et le transmet en flux, sans le tenir entier en
mémoire et hors de la file des actions serveur, à la route `/tasks/[taskId]/result`, que le
navigateur suit comme un lien, sans `download` : un type que le contrat déclare pour sa nature, et
la pièce jointe nommée du nom de base que le contrat promet (`Content-Disposition`,
`attachmentName`), sans sa longueur, que `fetch` a décodée, et que rien ne garde en cache
(`private, no-store`). Ce que la route ne transmet pas — un refus de l'API, dont le résultat expiré
ou pas encore prêt (409), l'API injoignable, une réponse qui ne nomme pas le fichier ou dont le type
n'est pas déclaré, l'erreur inattendue d'une mauvaise passerelle (502) — renvoie le navigateur, par
une adresse relative, à l'écran d'où il partait (`from`), l'adresse nommant la tâche et le refus
(`refused_task`, `refusal`, `result-refusal.ts`) : le suivi relit la tâche, la suit et dit le refus
dans son entrée (`OutcomeNotice`) — ou, la tâche illisible, dans un avis de son panneau —, et l'ôte
de l'adresse une fois la page révélée, le routeur de Next rendant à neuf une page dont l'adresse
change (#416).

L'écran est branché sur le service (EP-06, US-1430) : la page ne porte plus la note de la maquette
(`MockupNotice`). Le planning MS Project s'importe en deux temps (`openImport`, `getImport`,
`applyImport`, `expected_format` à `ms_project_schedule`) et s'exporte (`requestExport`,
`kind: ms_project_schedule`) ; le fichier de l'export se télécharge par la route
`/tasks/[taskId]/result`, que le service vide à la fin du premier téléchargement complet (`result_url`
nul, 404 ensuite, que la route rend par son refus). Le parcours de `exchanges.spec.ts` qui exporte le
planning d'un projet que la course crée, le télécharge, puis le réimporte sans écart (FLX-01 et FLX-02
du compte « chef de projet », WF-INTF-0010-A), et ceux de `tasks.spec.ts` qui jouent la route et le
refus d'un résultat sur l'export qu'elle a fait, portent `@shared`. Le devis s'importe (`kind:
estimate`) et s'exporte (`kind: estimate`, fichier `…-devis.xlsx`) par le même écran ; son parcours
`@shared`, sur un projet que la course crée, l'importe en deux temps (US-1550, #2687) : il exporte et
télécharge le devis, voit refuser à l'analyse un fichier qui n'en est pas un (format et version
attendus nommés), puis réimporte le classeur téléchargé, lit le compte rendu sans écart, confirme
l'application, qu'il suit dans la coquille jusqu'à sa réussite, et retrouve les mêmes lignes.
L'écart de calendrier d'un import (US-2000) a lui aussi son parcours `@shared`, sur un projet que la
course crée : le planning synthétique à sept heures par jour
(`fixtures/msproject/14-calendar-gap-seven-hours.xml`) montre son écart sur le compte rendu avant
toute confirmation, garde les durées par défaut, analyse de nouveau quand les dates sont gardées et
se suit jusqu'au nouveau compte rendu, et son abandon laisse le projet inchangé ; la règle déjà en
vigueur, que le serveur de Next envoie et que le navigateur ne voit pas, se lit par le même appel
fait à l'API (200). Les lignes rejetées d'un compte rendu et l'abandon d'un import sans écart
restent sur le faux back, comme le reste à engager et les coûts réels (EP-09) et le parcours du
marquage.

La page d'un projet propose de démarrer son planning par l'encart « Démarrer le projet »
(`ProjectStart`, `components/projects/project-start.tsx`, US-0490) tant que la structure principale
de la révision en cours n'a aucune tâche. La condition est lue au serveur (`startOffers`,
`start-offers.ts`) : la révision en cours liste `generate_skeleton` — l'appelant peut modifier le
planning — sans qu'il lui manque `main_structure_without_tasks` ; le front n'en déduit rien d'autre.
La page la prend dans la liste de ses révisions, dont chaque élément est une révision entière, sans
la relire. Ce que la génération produit (une récapitulative par lot et par poste, leurs jalons de
fin) est l'affaire du back : le front envoie la commande et mène à la grille, et le critère de
`WF-PRJ-0030-A` sur le résultat se porte au test du back, non à l'encart. « Planning automatique
depuis le lotissement » mène au lotissement (`settings?start=skeleton`), où « Engendrer le planning
» (`GeneratePlanning`) appelle `generatePlanningSkeleton`, relit la page après la génération comme
après un 409 (#819.5, #819.6) et mène à la grille. « Importer un fichier MS Project » ouvre la zone
de dépôt (`FileDrop`, `components/exchanges/file-drop.tsx`) : un bouton qui ouvre le sélecteur, la
zone nommée et décrite, le type (`.xml`) et la taille vérifiés avant l'envoi ; elle envoie comme le
formulaire de l'écran des imports (`useOpenImport`, `open-import.ts`), le compte rendu s'affichant
sur la page, et l'application confirmée mène à la grille. « Plus tard » replie l'encart pour la
session de l'onglet (`start-fold.ts`, `sessionStorage`) ; un bouton le rouvre. Le faux back, sans
état, sert au témoin une structure à mille tâches : l'encart n'y paraît jamais, et les deux parcours
de bout en bout (lotissement puis génération ; dépôt puis compte rendu) ne se jouent qu'aux tests
des composants, contre les exemples du contrat (`project-start.dom.test.tsx`, #1350).

### Les écrans du portefeuille

Les écrans du portefeuille, `/portfolio/…` (`frontend/src/components/portfolio/`, FBS-2), sont hors
projet : chacun lit sa vue sur le périmètre de l'adresse, sous les noms du contrat — les états
retenus (`states`), la période (`from`, `to`), la date de calcul (`as_of`) et le nœud d'organisation
(`org_node_id`), qui retient aussi ses descendants, offert dans l'ordre de l'arbre que rend
`listOrgNodes`, chaque nœud décalé de sa profondeur (`treeLabel`, comme le filtre du plan de charge
d'un projet) —, de ce périmètre ce que l'opération prend (`perimeterQuery`, `Takes`). Un état se
montre pressé comme l'adresse le demande, ou, quand elle n'en nomme aucun, comme le serveur les a
retenus (`scope.states`) : le front ne suppose aucun défaut. Sous le titre, le périmètre que le
serveur a retenu et la date de calcul de la vue, `scope.as_of` (`PortfolioHeader`), que portent tous
ses chiffres, et le nœud retenu, nommé par le serveur (`scope.org_node_label`). Une période que le
serveur refuse — une fin qui précède le début, `PortfolioPeriodRefused`, EP-02/L42f — est dite au
champ de la fin, le début nommé, comme les coûts réels la disent (`usePeriodProblem`) — une borne
seule se complétant par la période par défaut, un début postérieur à la fin complétée est dit au
champ du début, la fin nommée (`params.maximum`) — ; la vue n'est pas lue, son titre reste sans
périmètre retenu et une phrase tient sa place (`RefusedView` de
`frontend/src/app/portfolio/refused.tsx`) ; ses états sont pressés comme l'adresse les nomme, et,
sans état nommé, le filtre des états n'est pas offert, rien ne disant ce que le serveur retiendrait.
Le plan de charge agrégé et la santé du pilotage, où un projet terminé est sans effet (G-05), le
disent par une note du périmètre (`completedWithoutEffect` de `PerimeterBar`) dès que le serveur
retient `completed`, lu sur `scope.states` et jamais sur l'adresse (US-0703/L9). La liste des
projets (FBS-2.1) est une configuration de plus de la grille dense, triée, cherchée et paginée par
le serveur, sa ligne de totaux le nombre de projets retenus (`meta.total`), sous la valeur du
portefeuille. Les six autres vues (FBS-2.2 à FBS-2.7) montrent ce que le serveur calcule : le plan
de charge agrégé et les décaissements prennent en outre l'horizon (`horizon_months`) et, pour le
premier, le seuil de sous-charge (`under_load_threshold`), paramètres de la vue et non préférences
(WF-PTF-0060) : le menu propose quelques valeurs, mais toute valeur de l'adresse que le contrat
prend — un horizon de 1 à 240 mois, un seuil en `Percent` — est envoyée et se montre choisie ; sans
seuil dans l'adresse, le menu montre celui que le serveur a retenu (`under_load_threshold` de la
réponse), comme les états ; les colonnes du plan de charge sont les mois de la réponse (`months`),
que chaque rôle porte dans le même ordre. Un signal de santé dit ce qu'il nomme (`params` : les
semaines sans revue, le jalon dépassé et sa date de référence), comme une alerte de l'état du
système le composant indisponible. Chaque projet nommé — libellé de la liste, risque le plus lourd,
signal de santé — ouvre le projet (WF-PTF-0030). Les zones d'indice, de charge et de santé sont
celles du serveur, par `Signal` ; l'évolution trimestrielle des indices, la courbe en S et les
décaissements sont des figures de `Chart`, exportées en PNG avec la provenance de leur vue
(`usePortfolioExport`) : le périmètre que le serveur a retenu — états, nombre de projets, période,
nœud d'organisation — et sa date de calcul, `scope.as_of`, la phrase même de l'en-tête (#312).

### Les grilles : le collage d'un bloc de tableur

Un bloc copié d'un tableur se colle sur la cellule active, en deux temps (WF-IHM-0050, `paste.ts`) :
le bloc se lit à l'événement `paste`, écouté sur le document — le navigateur le vise où un clic a
laissé le curseur, la cellule est celle qui a le focus dans la grille, et une saisie en cours garde
le collage pour son champ —, jamais par `navigator.clipboard`, qui demande une permission ; en
valeurs séparées par des tabulations, une cellule entre guillemets gardant ses tabulations et ses
fins de ligne (`readBlock`). Le serveur remplit, à partir de la colonne visée, les colonnes de la
facette du nœud visé dans l'ordre de `NodeColumn`, sans connaître celles que la grille montre (#200)
: le front mesure donc le bloc sur ces colonnes-là (`GridPaste.span`, `pasteSpan`, #223), et refuse
aussitôt, sans rien demander, un bloc plus large qu'elles à partir de la cellule — comme le serveur
le refuserait (`PASTE_TOO_WIDE`) — et un bloc dont la portée, de la colonne visée à la dernière
colonne remplie dans cet ordre, atteint une colonne que la grille ne montre pas, masquée ou absente
de sa configuration, qu'il nomme — par son en-tête, ou par son libellé du catalogue
(`enums.NodeColumn`) ; il refuse de même un bloc dont une ligne ne tomberait pas sur celle que le
serveur écrit : le serveur remplit les lignes du plan sous la ligne visée, que la grille connaît par
leur numéro dans toute la structure (`row_number`), non les lignes affichées après elle. Une seule
garde compare, de la cible à la dernière ligne du bloc, le numéro de chaque ligne affichée à celui
qu'elle aurait dans l'ordre du plan (sur un différentiel, le serveur saute les nœuds que l'avenant
retire et remplit les suivants : la garde ne compte ni leur rang ni leur ligne, comme l'aperçu,
#1278) — une grille qui colle lit tous les genres de nœud, et ses numéros se suivent — ; pliée
(`fold.tsx`), déplacée par un tri, ou cachée par la recherche ou un filtre, la cause dite est celle que
l'utilisateur lève d'abord (L40, #527) ; un bloc plus haut que les lignes montrées n'est plus refusé :
ses lignes au-delà du dernier nœud de la structure créent des tâches (voir plus bas). Sinon
`previewPaste` rend le plan, que montre une boîte de dialogue de shadcn (`PasteDialog`,
`ui/dialog.tsx`), dans une seule région annoncée — combien de lignes seront écrites, combien de tâches seront créées (`created`, quand il y en a),
chaque ligne refusée par sa place dans le bloc, ses cellules telles que copiées et son motif, une ligne refusée
pour plusieurs cellules comptée une fois —, et `applyPaste` l'applique sur confirmation, en une
seule opération : les lignes valides sont écrites, les lignes refusées ne le sont pas (WF-IHM-0050,
EP-14/L42q). Un plan qui refuse des lignes et en écrit d'autres le dit, et se confirme ; un plan qui
n'écrit aucune ligne n'offre que l'abandon. La confirmation attend toute autre écriture de la grille
en cours — une cellule saisie, un geste — et la relecture qui suit un geste : elle porterait la
version de la structure que leur réponse va avancer, et serait refusée (412) ; « Appliquer le
collage » reste offert, inactif, occupé et décrit par l'attente, jusqu'à leur réponse (`busy` de
`useGridPaste`, #1224). Ce que la confirmation rend prend la place de ce qui était lu
(`CellWrites.applied`), comme les lignes qu'écrit un choix du menu d'une cellule ; une écriture de
cellule partie avant elles et répondue après se prend comme toute réponse, le compteur de la
structure décidant laquelle des deux une ligne montre (`answers.ts`, #202, #421), et seul son refus
se tait quand elles ont écrit sa ligne depuis. Ce que le collage n'a pas écrit
(`PasteApplied.rejected`) — les refus de l'aperçu, et ceux que le serveur ajoute en jugeant de
nouveau les lignes acceptées, une catégorie ou un rôle désactivés entre-temps — est dit au-dessus de
la grille avec la cellule d'où le bloc a été collé et le nombre de lignes écrites
(`PasteAppliedNotice`), chaque refus comme à l'aperçu, lu dans la réponse et jamais dans le plan,
jusqu'à ce que l'utilisateur ferme l'avis ou colle à nouveau ; les refus y sont une région nommée,
atteinte au clavier, dont la hauteur est bornée — ils défilent, la grille reste dans la fenêtre
(défaut n° 13), la phrase et la fermeture hors du défilement —, hors de l'alerte, qui ne dit que la
cellule, le nombre de lignes écrites et celui des lignes refusées, « listées ci-dessous » — une
phrase à elle, l'aperçu gardant la sienne —, et qui la décrit (#765). Un collage entièrement écrit
ne dit rien de plus que sa grille. Échap abandonne, une réponse arrivée après l'abandon est ignorée,
et le focus revient à la cellule. Le front ne juge rien du contenu : la colonne visée part sous son
nom de colonne du contrat (`NodeColumn`), que la grille la trie ou non, et la confirmation porte la
version de la structure lue (`structureVersion`), le serveur refusant par 412 un plan jugé sur une
structure qui a changé depuis l'aperçu (#200, #201). Le faux back ne sert que le premier exemple de
chaque opération, le plan qui ne refuse rien : le collage partiel n'est éprouvé que par les tests de
la grille (`paste-applied.dom.test.tsx`, `paste-dialog.dom.test.tsx`), et la hauteur réelle de
l'avis ne se prouvera qu'en parcours. Une grille sans `paste` dans sa configuration, en lecture
seule, ne prend aucun collage.

**Le collage qui crée (planning, US-1450/L6, #2559).** Le service du planning crée une tâche pour
chaque ligne du bloc qui tombe au-delà du dernier nœud de la structure : sœur de ce nœud, du genre
du nœud visé, dans l'ordre du bloc, son libellé requis (la ligne sans libellé est refusée,
`VALIDATION_FAILED` sur la colonne `label`). La garde locale ne compare donc plus le bloc à la
hauteur de la grille : elle garde ses refus pour les colonnes masquées ou absentes, les lignes
pliées, le tri, la recherche et le filtre — une lecture restreinte par la recherche ou un filtre
refuse un bloc qui dépasse sa dernière ligne, le front ne pouvant dire si des lignes cachées la
suivent. L'aperçu dit combien de tâches seront créées (`PastePlan.created`, comptées aussi parmi les
lignes écrites, en une phrase de plus de la même région annoncée, `grid.paste.created`) ; la
confirmation rend les tâches créées dans `nodes` (`PasteApplied`, `NodesWritten`), et la grille du
planning, qui ne sait pas où ces lignes se rangent, lit sa page à nouveau quand le plan en créait
(`router.refresh`, comme après la création d'une tâche) ; les lignes écrites prennent la place des
lignes lues, comme à l'ordinaire. Un bloc dont la cible est une ligne de devis voit ses lignes
au-delà du dernier nœud créées comme des lignes de devis, sœurs de ce nœud, sous la tâche qui le
porte (le libellé requis, les autres cellules jugées comme celles d'une ligne écrite) ; sans tâche
pour les porter — le dernier nœud est une tâche à la racine —, la ligne entière est refusée en
`UNKNOWN_TASK`, sur aucune colonne (`paste_plan_creating_lines`) : le refus se lit dans la liste
des lignes refusées de l'aperçu, comme tout refus. Annuler le collage supprime les tâches qu'il a créées, le rétablir les recrée : une seule
entrée d'historique (`undone.kind` reste `paste`, `undone.node_ids` nomme les nœuds écrits et
créés). Le parcours `paste.spec.ts` le joue contre le service (`@shared`), les tests de la grille
sur les exemples `paste_plan_creating` et `paste_applied_creating`.

### Les grilles : annuler et rétablir

Annuler et Rétablir sont posées par toute grille dont la structure lue liste sa commande `edit_*`
disponible (WF-IHM-0110, US-0140, `undo-commands.tsx` ; `undoable` de `DenseGrid`) — le devis par
`edit_estimate`, le planning par `edit_planning`, le reste à engager par `edit_remaining` (#115) ;
aucune grille hors d'une révision en cours ne les pose : ni le marquage, ni un import appliqué, ni
l'exclusion d'une ligne de coût ne s'annulent. Une telle grille les montre en boutons dans sa barre
et dans le menu contextuel de ses cellules (clic droit, Maj+F10, touche Menu — `CellMenu`, sans
arrêt de tabulation de plus), avec leurs raccourcis, et prend Ctrl+Z et Ctrl+Maj+Z — Cmd sur un Mac —
dans la grille ou sa barre, hors d'un menu ou d'une boîte qu'elle ouvre. Un champ en cours de saisie
— l'éditeur d'une cellule, la recherche — garde Ctrl+Z pour lui : l'annulation du navigateur y reste. Un bouton de filtre de la barre
(lot ou poste, « Écarts seulement », risque survenu) n'est pas un champ : Ctrl+Z y annule la grille,
comme sur Colonnes ou sur le menu du plan, sans défaire le filtre (#2916).

**Branchées (planning, US-1450).** La grille de planning les branche sur `undoLastChange` et
`redoLastUndo` (`src/api/actions/history.ts`) par `useUndoRedo` (`undo-run.ts`), que `DenseGrid`
reçoit en `undo` (`UndoControl`) : une annulation est portée par le serveur, qui garde la pile par
révision, par compte et par session de connexion, jamais une pile dans le navigateur. Les boutons,
le menu et les touches sont alors disponibles — ni `aria-disabled`, ni raison à lire. Une annulation
est une écriture de la structure comme les autres : elle se compte dans le compte de la structure
(`useStructureVersion`), les gestes et la confirmation d'un collage l'attendent et elle les attend,
la grille se dit occupée, et une commande donnée pendant une écriture est sans effet. L'action lit la
page à nouveau une fois le serveur répondu — les lignes rendues, créées ou supprimées, sont celles du
serveur — et la version que la structure a atteinte (`written.structure_lock_version`) est dite au
compte pour l'écriture suivante ; `remaining_depth` est dit avec le succès, dans une région annoncée
(`grid.undo.done.undo` et `grid.undo.done.redo` : « Modification annulée. 3 modifications restent à
annuler. »). Un refus se dit comme tout refus, par `OutcomeNotice` au-dessus de la grille,
sa phrase tirée du catalogue d'après son code et ses paramètres : `UNDO_CONFLICT` nomme l'objet repris
depuis (`conflicting_object_label`), `STATE_FORBIDS_OPERATION` la condition qui manque
(`undo_history_not_empty`, `redo_history_not_empty`, `restored_subproject_exists`),
`SESSION_ID_MISSING` un jeton sans session de connexion. Il reste dit jusqu'à ce qu'on le ferme ou
que la commande suivante parte. Le succès se joue contre le service (`e2e/undo.spec.ts`, cinquante saisies annulées puis
rétablies par la grille, `@shared`), les refus et l'annonce du succès sur les exemples
(`undo-wired.dom.test.tsx`).

**Le devis.** La grille de devis reçoit `undoable` comme celle du planning, là où la structure lue liste
`edit_estimate` disponible (EP-07, US-1450/L3) : cinquante saisies d'une ligne s'annulent puis se
rétablissent par la grille contre le service, et la suppression d'une tâche s'annule avec ses
lignes (`e2e/undo.spec.ts`, `@shared`). **Posées seulement.** Le reste à engager ne reçoit pas
d'`undo` : ses saisies, servies par EP-09, n'ont pas encore d'historique, et ses commandes restent
indisponibles, `aria-disabled`, décrites par leur raison ; le raccourci la dit dans une région
annoncée.

### Les grilles : créer et supprimer des tâches et des lignes

Une grille se saisit, et offre ses gestes de structure, selon la commande de la structure qu'elle
lit (`CostStructure.available_commands`, WF-IHM-0090) : `readGridScreen` rend celles qui sont
disponibles (`commands`), le planning lit `edit_planning`, le devis `edit_estimate`, le reste à
engager `edit_remaining`. Le front ne déduit jamais la phase du projet : sur la structure principale
d'un projet En cours le devis est en lecture seule, le reste à engager l'est avant (WF-DEV-0050,
WF-RAE-0040). Les gestes — « Insérer au-dessous », « Insérer une sous-tâche », « Insérer une
ligne », « Indenter », « Désindenter », « Monter », « Descendre », « Supprimer » — sont dans le menu
contextuel des cellules et aux touches Insert, Alt+Insert, Ctrl+Insert, Alt+Maj+→, Alt+Maj+←,
Alt+Maj+↑, Alt+Maj+↓ et Ctrl+Suppr (`structure-gestures.tsx`, règles pures dans
`structure-rules.ts`) ; la barre, tenue sur une ligne, n'offre que la première tâche d'une grille
sans ligne. Une création passe par un dialogue qui la nomme, et nomme la ligne sous laquelle il agit
(libellé ; pour une ligne, catégorie et quantité, que le contrat exige), `createNode` et
`deleteNode` sont les actions de `src/api/actions/nodes.ts`. Une création désigne sa place par le
nœud qu'elle suit parmi ses frères (`after_node_id`), jamais par un rang qu'une grille filtrée ne
saurait compter : la ligne active pour « Insérer au-dessous » et pour une ligne sous une ligne ;
sans lui, une sous-tâche va après la dernière sous-tâche, une ligne sous une tâche après sa dernière
ligne, les lignes d'une tâche précédant toujours ses sous-tâches (#1183, #1187).

La cellule du numéro de chaque ligne en est la poignée (`row-selection.tsx`), dans une grille dont
l'écran déplace des lignes (`RowCommands.drag`) : nommée par le numéro de sa ligne, décrite par la
façon de sélectionner et de déplacer, elle se traverse aux flèches comme les autres cellules. Un
clic la sélectionne seule, Maj et un clic étendent la sélection depuis son ancre ; au clavier, sur
la colonne des poignées, Espace sélectionne, Maj+↑ et Maj+↓ étendent la sélection avec la cellule
active, Échap la lève. La sélection est faite de lignes contiguës, gardées par leur identité : une
relecture qui les déplace les garde sélectionnées, et la cellule active les suit ; une relecture qui
ne montre plus l'une de ses extrémités — un filtre, un pliage — la lève. Plier une ligne qui porte
une extrémité de la sélection, son parent par exemple, la lève donc, sans le dire ; plier des lignes
sous la sélection, ses extrémités restant montrées, la garde. La cellule active suit aussi la ligne
qu'un geste a déplacée, sélectionnée ou non (`RowCommands.moved`), à l'arrivée de la relecture, qui
lui rend le focus s'il était dans la grille. Chaque ligne dit si elle l'est (`aria-selected`), la
grille qu'elle en prend plusieurs (`aria-multiselectable`), un statut combien — les lignes montrées
: les subordonnées pliées sous une récapitulative sélectionnée la suivent sans être comptées. Une
cellule calculée sélectionnée garde son ombre. Un geste de déplacement porte sur la sélection quand
la ligne d'où il part en est, sur cette ligne seule sinon, et sur les nœuds qui portent les autres
(`topsOf`) : une récapitulative emporte ses subordonnées. La suppression ne porte que sur une ligne
seule.

« Indenter » place les tâches sous celle qui précède la première parmi ses frères, en dernière place
(`after_node_id` absent) ; « Désindenter » les place après leur parent, sous le parent de celui-ci
(`after_node_id` = l'ancien parent) ; « Descendre » les place après la sœur de leur genre qui suit
la dernière, et « Monter » place la sœur qui précède la première après la dernière — le même ordre,
sans reposer sur une ligne que la grille ne montre pas. Les lignes que la grille montre ne sont pas
toujours l'arbre : une recherche, un filtre, le reste à engager, qui ne lit par défaut que les
tâches commencées, ou le planning, qui ne lit aucune ligne, en laissent. Un déplacement n'est donc
offert, au menu comme à la touche, que si les nœuds déplacés sont des frères de rang en rang, d'un
même genre, et que la voisine sur laquelle il repose est rendue : son rang (`Node.position`, à
partir de 1, les lignes d'une tâche comptant avant ses sous-tâches) est celui de la première moins
un, ou de la dernière plus un ; « Indenter » ne l'est pas sous un jalon, ni sous une ligne. «
Désindenter » ne dépend d'aucune ligne masquée, la place étant celle du parent (`parent_id`,
`node_id`), mais n'est pas offerte si la grille ne montre pas ce parent, ni à la racine. Alt+Maj et
une flèche, là où le déplacement n'est pas offert, sont pris sans effet : la cellule active ne bouge
pas (AltGr, qui est Ctrl et Alt, reste à la grille). Une écriture en cours — un geste, une cellule
saisie, un collage appliqué, toute écriture de la grille (décision de l'auteur du 2026-10-21, #1224)
—, puis la relecture qui suit un geste, retiennent les gestes et la confirmation d'un collage, la
grille se disant occupée (`aria-busy`) : le suivant part des voisines que la relecture a rendues,
jamais de celles d'avant avec une version déjà avancée. La grille dit ses propres écritures aux
commandes de son écran (`RowCommands.writing`), qui les comptent avec les leurs
(`useStructureVersion`), chacune pour la structure où elle est partie : une réponse arrivée quand la
grille en montre une autre n'en avance pas la version et ne la relit pas.

La poignée glisse la sélection — ou sa seule ligne, qui n'en est pas — à côté d'une autre ligne :
avant elle ou après elle, à son niveau, par le quart haut ou bas de la ligne, ou sous elle, en
dernière place de son genre, par son milieu ; entre deux lignes, c'est avant celle du bas, et au
bas de la dernière ligne de la grille, après elle. La cellule active suit la première des lignes
glissées (`RowCommands.moved`) ; quand la relecture ne la montre pas — glissée sous une
récapitulative pliée, ou hors d'un filtre —, la cellule active reste à son indice et le focus lui
revient, comme après une suppression, au lieu de tomber sur la page ; ce focus n'est rendu qu'à une
cellule de la grille, jamais à un élément hors d'elle. Une ligne se glisse sous une
tâche qui porte des lignes, une tâche sous une tâche qui n'est pas un jalon. Avant une ligne, la
place est celle qui suit la sœur de rang moins un, rendue, ou la tête (`after_node_id` nul) au
rang 1 : le planning, qui ne lit aucune ligne, n'offre donc pas de dépôt avant la première
sous-tâche d'une tâche qui porte des lignes, sa sœur de rang moins un étant une ligne qu'il ne rend
pas ; la glisser sous la tâche la met en dernière place. L'indicateur — un trait entre les lignes,
ou la ligne grisée — ne paraît qu'où le dépôt est accepté (`dropOf`) : jamais parmi les lignes
glissées ni sous elles, ni à côté d'une ligne d'un autre genre, ni tant que la grille est occupée
(`RowCommands.busy`, qu'exige `drag`). Le glisser ne porte que son type
(`application/x-waterfall-rows`) : un dépôt venu d'ailleurs, un texte par exemple, ne déplace rien.
Le glisser a son équivalent au clavier, Alt+Maj et les flèches sur la sélection ; mais une place
éloignée, ou une sélection qui n'est pas faite de frères, y demandent plusieurs gestes, là où un
seul dépôt suffit.

`moveNodes` s'appelle pour la liste des nœuds dans l'ordre de la grille. La version de la structure
qu'il porte est celle d'un suivi unique par grille (`useStructureVersion`, `structure-version.ts`) :
la plus haute entre celle de la page et celles que les écritures ont rendues
(`NodesWritten.structure_lock_version`), cellule saisie, création, déplacement, suppression ou
collage, car le contrat fait avancer `CostStructure.lock_version` à chaque écriture de l'arbre. Ce
suivi tient la version et les écritures en cours par structure : ce qu'une réponse applique — la
version qu'elle a atteinte, la ligne que la cellule active suit, la relecture — l'est pour la
structure où elle a été envoyée, et rien n'est relu pour elle une fois que la grille en montre une
autre (défaut n° 1). Un
refus par champ se dit par la raison du champ (`byField`), pour toute écriture du hook — création,
déplacement et `deleteNode`, dont le contrat ne cite aucun champ, son refus se disant alors par son
code —, comme celui d'une cellule ; `NODE_NOT_SIBLING`, qui vient d'une lecture périmée, relit en
outre la grille, le focus rendu à la grille si la relecture retire la cellule qui l'avait. La
suppression d'une récapitulative est confirmée, celle d'une feuille ou d'une ligne ne l'est pas, et
le focus revient alors à la cellule active de la grille. La grille est relue après une écriture, la
lecture du serveur faisant foi pour les numéros et les niveaux (#1160), et la version que la
structure a atteinte est dite à la grille, que porte le collage suivant. Les gestes de tâche du
devis exigent `edit_planning` (`tasksEditable` de `estimate-grid.tsx`) en plus de `edit_estimate` :
créer ou supprimer une tâche écrit le planning, et un chiffreur qui ne peut que saisir le devis n'en
crée pas. Un refus — tâche terminée, par exemple — est dit au-dessus de la grille en nommant la
ligne en cause, dont l'étiquette est marquée et décrite par lui ; celui d'une création sans ligne
(la première tâche d'une grille vide) nomme la tâche tentée. Le succès se dit par `useSaid` et le
refus par `OutcomeNotice`, tous deux notés dans l'historique des messages.

Le menu contextuel des cellules offre deux sous-menus de plus (`choice-menu.tsx`, règles pures dans
`row-choices.ts`, US-0480). « Chronologies » : une case par chronologie du projet (`listTimelines`),
cochée quand la tâche y est inscrite, et « Suivi temps/temps » pour un jalon ; la tâche l'offre
quand elle nomme `task.tracking` dans ses `editable_fields`. « Sous-projet » : des boutons radio, «
Aucun sous-projet » et chaque sous-projet du projet (`listSubprojects`), nommé par son code et son
libellé — le code seul est unique dans un projet —, celui de la ligne coché ; la ligne l'offre quand
elle nomme `estimate_line.subproject_id`, ce que ne fait ni une ligne de provision, ni celle d'une
tâche démarrée dont le sous-projet a reçu des coûts réels (`SUBPROJECT_HAS_ACTUAL_COSTS`) : le front
ne déduit aucune de ces gardes. Dans le devis, le choix se fait tant que le projet n'est pas En
cours, dans le reste à engager ensuite, selon ce que la ligne nomme. Un sous-menu s'applique à la
sélection, ou à la ligne seule : un appel par ligne qui nomme le champ, avec la version de cette
ligne — `setNodeTracking` avec la liste complète de ses inscriptions, `updateEstimateLine` avec
`subproject_id` —, dans l'ordre de la grille — sans écriture pour une ligne déjà dans l'état visé —
et jusqu'au premier refus, dit pour sa ligne comme celui d'un geste : les lignes écrites avant lui
le restent, celles d'après ne sont pas écrites. Chaque réponse prend la place de la ligne lue
(`applied` de `RowCommands.menu`), puis la grille est relue comme après un geste. Un projet sans
chronologie propose « Créer une chronologie… » (`createTimeline`), nommée dans un dialogue, à
laquelle les tâches sont inscrites, selon l'offre `manage_timelines` du projet : absente, l'entrée
n'est pas présentée ; indisponible, elle l'est grisée avec sa condition. Les colonnes « Chronologies
» du planning et « Sous-projet » du devis et du reste à engager sont en lecture et masquées
(`GridColumn.hidden`) tant que le compte n'a gardé aucune liste de colonnes masquées
(`initialSettings`) ; il les montre par le choix des colonnes.

### Les grilles arborescentes : plier et déplier

Les grilles arborescentes — planning, devis, reste à engager — se plient et se déplient
(WF-PLA-0080, WF-PLA-0090, EP-02/L40, `frontend/src/components/grid/fold.tsx`) : une grille dont
l'arbre nomme le parent de chaque ligne (`GridTree.parent`, `parent_id` de `listNodes`) est un
`treegrid`, chaque ligne portant `aria-level`, `aria-posinset`, `aria-setsize` et, quand la réponse
tient des lignes sous elle, `aria-expanded`. Une ligne pliée sort ses subordonnées des lignes de la
grille : la virtualisation ne les rend plus, le clavier ne les parcourt plus, et le Gantt, une
colonne de la même grille, les perd avec elle ; la cellule active reste sur sa ligne, ou passe à
celle qui la porte. Le bouton du libellé — ou celui qui précède le crochet d'une récapitulative dans
le Gantt — plie ou déplie sa ligne, hors de l'ordre de tabulation ; au clavier, comme dans Microsoft
Project, Alt et moins plie la ligne de la cellule active — celle qui la porte, depuis une ligne
sous laquelle rien ne se plie —, Alt et plus la déplie, Alt et * déplie tout, Maj ou non selon ce
que la disposition du clavier demande pour taper le caractère, sur le pavé numérique aussi ; le
caractère est celui que la touche a tapé, et, quand il ne nomme aucune commande, celui que la
touche porte dans la disposition que le navigateur dit (`navigator.keyboard.getLayoutMap`) —
jamais la seule place de la touche, qui porte un autre caractère sur une autre disposition. Ctrl
et AltGr sont exclus ; Alt+Maj et les flèches déplacent les tâches. Ces raccourcis
ne sont que des accélérateurs : sans `getLayoutMap`, sous Safari et Firefox pour Mac, Option et une
touche tapent un autre caractère, et ils ne sont pas reconnus. Le menu contextuel des cellules
(Maj+F10, touche Menu, clic droit), offert dans toute grille arborescente, Annuler et Rétablir ou
non, les remplace partout : « Plier la ligne » — « Plier « libellé » », qui nomme la ligne qui
la porte, depuis une ligne sous laquelle rien ne se plie —, « Déplier la ligne » quand elle l'est,
« Tout déplier », offert même hors d'une cellule, si bien que le menu n'est jamais vide ; le focus
revient à la cellule active. Les touches se disent par `aria-keyshortcuts` — Maj+F10 sur chaque
cellule, celles du pliage sur le libellé d'une ligne qui se plie, dans le menu et dans la barre —,
autant que le navigateur les reconnaît (`useFoldReach`, lu après l'hydratation) : toutes hors d'un
Mac ; sur un Mac, Alt et moins, Alt et plus quand `getLayoutMap` existe, aucune sinon ; Alt et *
hors d'un Mac seulement. Un
bloc collé qui s'étendrait, à partir
de la ligne visée, sur une ligne pliée est refusé sans rien demander, comme celui qui atteint une
colonne masquée. Le menu « Arbre » de
la barre plie tout, déplie tout, ou plie jusqu'à un niveau. Une recherche ou un filtre qui retient
une ligne pliée déplie ses ancêtres, une fois pour cette recherche. L'état plié se garde dans le
stockage de session de l'onglet (`sessionStorage`), par grille et par révision, sans rien envoyer
au serveur : le serveur rend l'arbre déplié, que le navigateur replie une fois hydraté. Une adresse
du planning qui nomme une tâche (`task`, son `node_id`, `planning-target.ts`) — là où mène une
tâche du détail du plan de charge (US-2040) — déplie, une fois hydratée, les lignes au-dessus d'elle
depuis les plis que garde la session, et y pose la cellule active et le focus, une fois pour la
grille montée : un tri ou une relecture de la même adresse ne vise plus rien. Un paramètre de
l'écran, comme `structure` ou `depth`, jamais envoyé à l'API ; une tâche que la lecture ne tient pas
ne vise rien.

Quand la grille lit une comparaison, « Écarts seulement », dans sa barre, replie les lignes sans
écart (WF-IHM-0170, US-2360, `difference-fold.ts`, `folded-runs.tsx`) : un état de `fold.tsx`, gardé
avec les plis, sous la même clé, hors de l'adresse et sans rien demander au serveur. La grille retire
de ses lignes rendues chaque nœud que le serveur marque inchangé et sous lequel aucun ne l'est
autrement — sur ses seules marques, sans comparer de valeur —, et pose à la place de chaque suite
une ligne de marque qui en dit le nombre de lignes. Cette ligne est comptée parmi celles de la
grille (`aria-rowindex`, `aria-rowcount`, la fenêtre de la virtualisation), sans être une ligne de
la réponse : aucune commande, saisie, sélection ni collage ne l'atteint. Les flèches s'y arrêtent,
entre les lignes qui l'entourent, la cellule active restant le seul arrêt de tabulation ; Entrée,
Espace ou Alt et plus la déplient, comme le clic sur son bouton, et sa première ligne devient la
cellule active. Une suite dépliée le reste tant que le repli est actif, relectures comprises ; une
ligne qu'une écriture fait différer reparaît à la relecture, et une ligne que la grille écrit —
saisie, collée, ou la ligne de la cellule active à une annulation — reste montrée, même relue
inchangée, tant que le repli est actif : le focus ne la quitte pas. Home, End et les pages, d'une
ligne de marque, partent de la ligne voisine ; les autres touches y restent inertes. Les totaux sont
ceux de la réponse. Limite du Gantt (#3785, à trancher) : un lien vertical est coupé sur la hauteur
d'une ligne de marque. Sur un différentiel, « Écarts seulement » reste le filtre du serveur
(`difference`, US-0700).

### Les commandes

Une commande s'affiche par `Command` de `frontend/src/components/commands/` (WF-IHM-0090) : absente
quand l'objet ne la liste pas dans `available_commands` — le serveur n'y met que celles que
l'appelant a la permission d'exercer, et le front ne sait pas quelle permission garde quelle
commande ; seule exception, décidée par l'utilisateur le 2026-10-05, un import sans révision en
cours que l'appelant ne pourrait pas créer, listé indisponible, `may_create_revision` manquante —,
présente et disponible, ou présente et indisponible, marquée `aria-disabled` et décrite par le texte
visible des conditions qui lui manquent (`enums.CommandCondition.*`). `LifecycleCommands` rend, dans
l'ordre du serveur, les sorties du cycle de vie d'un projet — les autres commandes du projet
appartiennent aux formulaires de leur domaine, sa modification à celui de ses paramètres
(`ProjectIdentity`) —, et `RevisionCommands` celles d'une révision, chacune selon son `is_available`
et ses conditions — une révision marquée les liste indisponibles, faute d'être en cours
d'élaboration —, ses exports laissés à l'écran des imports et exports, qui les offre (`ExportForm`),
ses saisies (`edit_*`) à leurs grilles et le squelette à la grille de planning vide (EP-14/L44d) ;
`findOffer` en tire une seule, et les formulaires disent ce qui leur manque comme les autres
commandes, par `CommandTooltip` et, pressées, `PressRefusal` ; `UnmetConditions` ne reste que pour
les commandes des chronologies (#3290). Hors projet — comptes, rôles, référentiel, sauvegarde —, `platformOffer`
suit la permission de modification d'une fonction de portée `platform` (`PlatformFunction`) dans
`Session.permissions`, ou `project_create` pour la création d'un projet, qu'aucun projet ne liste ;
les commandes d'une sauvegarde sont celles qu'elle liste (`Backup.available_commands`, EP-14/L43f),
le téléchargement et la restauration comprises. Griser n'est qu'une commodité : une commande
disponible lance son action serveur, et le refus du serveur est dit par `OutcomeNotice`. Pressée,
elle attend ce qu'elle a lancé — sa requête, écriture lente faite dans la requête comprise
(l'ouverture d'une révision), ou la tâche de fond qu'elle a remise au suivi, jusqu'à sa fin
(`useTaskRunning`) — de la même façon partout (`waiting.tsx`, #3103) : inerte (`aria-disabled`,
une seconde pression ne relance rien), `aria-busy`, une roue à la place de son icône, à côté de son
libellé, qui reste ; une réponse, un échec compris, la rend. L'attente se retrouve au remontage, dans
l'onglet : le bouton remet sa tâche au suivi avec ce qu'il vise (`aim`, composé par `taskAim` de sa
nature et de son objet — la révision marquée ou exportée, le projet d'un import, l'installation pour
une sauvegarde ou une lecture des comptes), que le suivi garde avec elle dans la session de l'onglet
(`storage.ts`) ; remonté — l'onglet rechargé, l'écran quitté puis retrouvé —, il attend sur la tâche
qu'il vient de lancer ou, à défaut, sur celle qui court pour ce qu'il vise (`useRunningTask`, #3404).
Une tâche lancée d'un autre onglet ou d'un autre poste n'a pas d'objet : aucun bouton ne l'attend.

### Les infobulles des commandes

Un bouton porte `CommandTooltip` (`frontend/src/components/commands/command-tooltip.tsx`, US-0580,
#1071), jamais un attribut `title=`, que le navigateur montre tard, sans mise en forme ni thème
sombre, et jamais au focus du clavier. Un lien dessiné comme un bouton et un article de menu le
portent de même. L'infobulle dit :

- **le nom** de la commande, celui que le contrôle porte déjà ;
- **une phrase d'aide**, la prop `help`, déjà traduite : pour une commande,
  `commands.<commande>.help`, dans les deux langues, tenue par `make catalogs` et lue par
  `t("commands.<commande>.help")`, que le typage du catalogue refuse pour une commande qui n'en a
  pas (`CommandHelp` nomme celles qui en ont, pour une table de commandes) ; pour l'en-tête d'une
  colonne, sa définition (`columns.<grille>.<colonne>.help`) ; ou une phrase à paramètres
  (`helpValues`). `help` et `unavailable` ne prennent jamais un littéral (`make lint-front`) ;
- **ses touches**, en `<kbd>`, écrites selon le poste — ⌘ sur un Mac, Ctrl ailleurs —, chaque touche
  par son nom du catalogue (`commands.keys`, `commands.macKeys`). Elles n'ont qu'une source : la
  prop `keys`, écrite comme `aria-keyshortcuts` la nomme (`"Control+Z Meta+Z"`), que
  `CommandTooltip` pose sur le contrôle et montre à la fois (`shortcut.ts`) ;
- **la condition qui manque**, pour une commande indisponible (WF-IHM-0090) : `unavailable`, qui
  marque le contrôle `aria-disabled` — jamais `disabled`, qui l'ôterait du survol et du clavier. La
  condition décrit le contrôle, infobulle fermée comme ouverte : par le texte qui la dit déjà à côté
  de la commande, que `describedBy` désigne, ou, l'écran ne la disant nulle part ailleurs, par un
  texte caché de `CommandTooltip` lui-même.

Un article de menu s'écrit par `MenuCommand` (`menu-command.tsx`), qui prend l'article
(`item={ContextMenuItem}` ou `DropdownMenuItem`), le nom, l'aide, les touches, la condition, l'icône
et `onSelect` : le nom est à la fois le texte de l'article et celui de l'infobulle, et les touches
sont posées sur l'article, montrées à sa fin et dans l'infobulle, d'une seule saisie. Un article qui
mène ailleurs prend `href` au lieu d'`onSelect` — l'un ou l'autre, jamais les deux —, et s'y rend en
lien. Un article indisponible suit la règle de `Command` (#3430) : la condition qui lui manque
(`unavailable`) se lit dans son infobulle, au pointeur comme au clavier, et le décrit, sans s'écrire
sous son nom ; pressé, il ne lance rien, et l'écran qui tient le menu dit ce qui manque dans sa
région des refus, depuis son `onSelect` — la carte du Kanban, par l'alerte de la carte, le menu
refermé.

L'infobulle suit WCAG 1.4.13 : elle s'ouvre au survol, après un court repos, et au focus du clavier,
aussitôt — dans un menu, après le même repos, pour qu'Échap pressé aussitôt ferme le menu (`inMenu`,
que `MenuCommand` pose) ; elle se ferme par Échap sans déplacer le focus — dans un menu, le premier
Échap ferme l'infobulle, le second le menu —, et reste ouverte tant que le pointeur passe dessus,
même dans un menu modal, qui ôte le pointeur au reste de la page (`pointer-events-auto` de
`TooltipContent`). Ouverte, elle décrit en outre le contrôle (`aria-describedby`) par sa phrase
d'aide : elle ne porte jamais seule ce qu'il faut savoir, le nom restant celui du contrôle et la
condition sa description. Le contrôle est un seul élément, qui reçoit les attributs et les
événements de l'infobulle : il ne pose lui-même ni `aria-keyshortcuts`, ni `aria-disabled`, ni
`aria-describedby`, que `CommandTooltip` pose ; il ne fait rien, pressé indisponible. Les infobulles
partagent un seul `TooltipProvider`, à la racine de la coquille (`shell.tsx`) : l'une fermée, la
suivante que le pointeur atteint s'ouvre sans attendre ; chacune dit son délai (`delayDuration` de
`Tooltip`), et une infobulle rendue hors de la coquille, dans le test d'un composant, apporte le
sien.

_Contrôle_ : `src/components/button-title-guard.test.ts` (`make test-front`) lit chaque composant
par l'analyseur de TypeScript et refuse un `title=` sur un bouton — `<button>`, `Button`,
`CellCommand`, `Command`, un interrupteur, un article de menu, coché ou au choix, ou un déclencheur,
un élément de rôle `button`, un lien dessiné par `buttonVariants`, écrit en place ou par une
constante du même fichier —, et un `title` passé par la décomposition d'un objet écrit ou nommé dans
le fichier. Restent à la revue : des classes ou des props importées d'un autre module, la
décomposition des props qu'un composant reçoit (`{...props}`), et un composant à nous qui dessine un
bouton sous un autre nom. Les commandes d'objet passent à `CommandTooltip` avec US-0580/L2 (#1137),
et la garde ne tolère plus aucun `title=` sur un bouton : `Command` et `ConfirmedCommand` prennent
`help` (pour une commande d'objet, `commands.project.<commande>.help` ou
`commands.revision.<commande>.help`, d'après les énumérations du contrat), `CellCommand` et
`UnavailableCellCommand` prennent le nom (`label`), `help` et la condition qui manque
(`unavailable`), que `CommandTooltip` pose en `aria-disabled` et en description, sans texte caché
écrit à la main. L'en-tête d'une colonne porte sa définition de la même façon (`GridColumn.help`,
clé `<grille>.<colonne>` du catalogue `columns`, et `helpValues` pour une phrase à paramètres). La
garde suit les noms liés dans le bloc le plus proche du bouton qui les lie, non plus dans le fichier
entier. Les boutons de validation et d’annulation d’un formulaire ou d’un dialogue, dont le libellé
est l’action, ne portent pas de phrase d’aide. Les tests du composant sont dans
`command-tooltip.dom.test.tsx` (survol, focus, Échap dans un menu, touches, condition, fournisseur
partagé, axe) ; `help-keys.test.ts` échoue pour toute clé `commands.*.help` du catalogue qu’aucun
composant ne lit, et `column-help.test.ts` pour toute colonne de devis, de planning, de reste à
engager ou du registre des risques sans définition.

### L'aide en ligne

Chaque écran que la table des fonctions connaît ouvre son aide (WF-IHM-0140, US-0580) : le bouton «
Aide » de son en-tête (`PageHeader`) — une icône seule, nommée, au plus de la hauteur d'une ligne du
titre, qui suit son dernier mot dans le même flux de texte : à droite, parmi les commandes, il
rétrécirait le titre ; élément d'une rangée qui passe à la ligne, il prendrait une ligne à lui sous
un titre sur deux lignes, celui du reste à engager en 1280 × 720 ; dans les deux cas, l'en-tête
grandirait et pousserait les totaux d'une grille hors d'une fenêtre basse (`grid-frame.spec.ts`,
`remaining.spec.ts`). Il ne passe à la ligne que si la dernière ligne du titre est pleine, et il y
est alors sans retrait : une espace le sépare du titre, non une marge —, ou F1 partout sur l'écran,
ouvre à côté de lui un panneau latéral (`shell/help-panel.tsx`, un `Sheet`) sur la page de son code
de la FBS — celui de la route que suit l'adresse (`helpCodeAt`, `src/help/help.ts`) : une fonction,
une feuille, la liste des projets (FBS-4). Une page est un fichier Markdown,
`frontend/help/<langue>/<code>.md` ; une notion de la méthode,
`frontend/help/<langue>/notions/<notion>.md` — les mêmes fichiers, sous les mêmes noms, en français
et en anglais (US-0670b). Le serveur les lit à l'ouverture du panneau, dans la langue de
l'interface, par l'action `readHelp` (`src/api/actions/help.ts`, `src/help/read.ts`, `server-only`),
qui ne nomme aucun fichier d'après la requête sans avoir confronté la page aux codes de la table ou
à la forme d'un nom de notion, et la langue aux langues de l'interface (`LOCALES`), et dont la
lecture refuse, là où le chemin s'écrit, tout fichier hors du dossier de l'aide (#1462) ; le
standalone les emporte par `outputFileTracingIncludes` (`next.config.ts`). Le panneau les rend par
`react-markdown` et `remark-gfm`, sans HTML brut (`skipHtml`) et dans les seuls éléments d'un texte
; un code entre accents graves s'y lit comme une touche (`<kbd>`). Un lien relatif vers un code ou
une notion (`FBS-4.4.md`, `notions/valeur-acquise.md`, `../FBS-4.3.md` depuis une notion) montre sa
page dans le panneau ; tout autre lien se lit comme du texte. La recherche porte sur les titres des
pages écrites dans la langue lue, que l'action rend avec la page ; le serveur garde un index par
langue. Aucune page ne se lit dans une autre langue à la place de la sienne : une page anglaise
manquante est un échec, comme une page française manquante. Le panneau tient le focus, se ferme par
Échap et rend le focus à ce qui l'avait — le bouton, ou la cellule où F1 a été pressée ; une page
suivie par un lien donne le focus à son titre. Une réponse arrivée après une autre demande est
ignorée.

La page d'un écran suit la structure de #1075, ses titres de second niveau dans cet ordre, dits dans
sa langue (`SCREEN_HEADINGS`) : « Ce que montre l'écran », « Ses commandes », « Ses colonnes et ses
valeurs calculées », « Les gestes au clavier », « Voir aussi » ; « What the screen shows », « Its
commands », « Its columns and computed values », « Keyboard gestures », « See also » en anglais. Les
définitions des colonnes ne s'y écrivent pas : le panneau les rend après la troisième section,
depuis la configuration de la grille de l'écran et les clés de ses en-têtes
(`columns.<grille>.<colonne>.help`, `COLUMNS` de `read.ts`), une seule source avec leurs infobulles.
Une notion cite le glossaire de l'annexe A mot pour mot, sans les identifiants d'exigence entre
parenthèses (« (WF-RIS-0050) »), qui ne disent rien à qui lit l'aide, et que `help.test.ts` ignore
dans sa comparaison (#1440), une citation par terme (`> **Terme** — définition`), sous « Ce que dit
le glossaire », puis « Dans Waterfall » et « Voir aussi » (`NOTION_HEADINGS`). La spécification
n'existant qu'en français, une notion anglaise traduit ses citations, sous la même forme et en même
nombre, sous « What the glossary says », « In Waterfall » et « See also ». La page anglaise est la
traduction fidèle de la française : ses exemples de saisie sont ceux de l'interface anglaise (« 2 d
», « 1 wk », « 3FS+2 d; 5SS », #1441), et les libellés qu'elle cite, ceux du catalogue `en`. Le
panneau dit la langue où la page a été lue (`lang`) sur la page rendue (`WrittenPage`), le titre du
panneau et les titres que la recherche trouve : les messages de l'interface du corps (lecture,
échec, nombre de résultats) n'en portent pas (#1442).

_Contrôle_ : `src/help/help.test.ts` (`make test-front`) exige, dans chaque langue, une page par
code de la table qui a un écran, ou sa place dans la liste des pages à venir avec le lot qui l'écrit
(`SCREENS_TO_COME`, `NOTIONS_TO_COME`) — liste qui échoue dès qu'un code qu'elle nomme reçoit son
fichier —, et les mêmes fichiers en anglais qu'en français ; il tient la structure des pages dans
chaque langue, les citations du glossaire — mot pour mot en français, en même nombre en anglais —,
les liens, qui mènent à une page écrite ou à venir, les mêmes en anglais qu'en français, les
libellés cités en gras, pris au catalogue `en` là où la page française cite le catalogue `fr`, et
l'absence de HTML brut. Une page à venir se dit telle dans le panneau. `help-panel.dom.test.tsx`
éprouve le panneau dans les deux langues, et `e2e/accessibility.spec.ts` l'audite ouvert par F1 sur
le planning, en français et en anglais.

### Les actions longues et le suivi des tâches de fond

Une action longue rend la main à la réception de sa tâche de fond (WF-ARC-0090) : son action serveur
passe par `decodeTask` de `frontend/src/api/problem.ts`, qui tient le motif d'un échec à la règle du
catalogue, et l'écran remet la référence au suivi de la coquille par `useTrackTask()`
(`frontend/src/components/tasks/`), avec la commande qui l'a lancée et, s'il y en a un, le nom que
l'utilisateur lui a donné (WF-IHM-0080). Le suivi est commun aux neuf genres de tâche : il relit la
tâche toutes les deux secondes tant qu'elle court, par l'action serveur `readBackgroundTask`, en
montre l'avancement, ajoute sa fin à un journal (`role="log"`) lu quel que soit l'écran, relit de
lui-même l'écran montré quand une tâche qui le concerne aboutit ou échoue — un écran du projet d'où
elle est partie, ou, hors projet, cet écran même (`readsAnew`) —, offre de recharger l'écran quand
elle a abouti, et rejoue la commande d'une tâche échouée. La lecture suivante part de la réponse de
la précédente, non d'une entrée nouvelle : une lecture qui trouvait la tâche où elle en était laissait
l'entrée telle quelle (#180), et le suivi s'arrêtait là — une tâche lue deux fois, aboutie, plus
jamais lue (#3103). Son panneau est une feuille (`Sheet`) le long du bord droit de la fenêtre, qui
porte aussi l'historique des messages (ci-dessous) : un dialogue modal titré « Tâches et messages »,
qui garde le focus tant qu'il est ouvert et que ferment Échap, son bouton de fermeture, un clic hors
du panneau ou « Recharger l'écran », le focus rendu au bouton de la barre. Le bouton de la barre
(`TasksButton`) l'ouvre et dit, dans son nom et ses pastilles, le nombre des tâches suivies et celui
des refus non lus. Rien ne l'ouvre de lui-même, sauf le refus d'un résultat au retour du navigateur,
dont le téléchargement est parti du panneau. Une tâche remise se dit sous la barre, dans le flux de
la page, sur l'écran où l'on est : la dernière, en une ligne courte qui reste jusqu'à la suivante,
sans annonce ; son bouton la ferme, au clavier comme à la souris, et rend le focus au bouton de la
barre, la tâche restant suivie (décision de l'auteur, #1179). La ligne ne dit pas une fin que porte
une carte d'aboutissement — un succès, un échec — : la carte, qui reste et porte l'action, la dit
seule, avec le journal des fins et le panneau, et la ligne de la tâche remise se ferme à son
arrivée ; elle ne dit plus qu'un suivi interrompu, qui n'a pas de carte (décision de l'auteur du
2026-11-14, #3292). Chaque succès et chaque échec se dit par une carte flottante au coin bas droit
de la fenêtre (`EndCards`,
`end-cards.tsx`, US-2170), montée par la coquille au-dessus de la page, qu'elle ne déplace pas : la
phrase de la fin, le motif d'un échec, l'action qui suit — « Télécharger » le fichier d'un export, la
tâche relue d'abord comme depuis le panneau, sinon « Ouvrir » l'écran d'où elle est partie — et sa
croix. Elle reste jusqu'à ce qu'on l'ouvre — « Ouvrir » d'un clic simple, pas d'un clic qui ouvre
un autre onglet — ou la ferme (`Tracking.cards`, faites avant que le journal soit tronqué) ;
plusieurs s'empilent, la dernière en tête, dans une colonne bornée à la fenêtre, qui défile. Ce
n'est pas une région vivante : le journal des fins l'annonce, sans prendre le focus, et l'inscrit à
l'historique des messages, que le panneau garde. Un suivi interrompu n'a pas de carte ; une tâche
retrouvée, son écran inconnu, n'a que sa croix. Fermée — par sa croix ou par son action — alors que
le focus était dans la pile, le focus passe à la croix de la suivante, sinon de la précédente, sinon
au bouton de la barre. Le fichier d'un export part de lui-même quand sa tâche aboutit et que l'écran
qui l'a demandé est encore ouvert (`useDownloadWhenTaskSucceeds`, `ExportForm`, `TaskTreeExport`,
#3103), la tâche relue d'abord ; l'écran quitté, la carte l'offre. Parti de lui-même, sans geste de
l'utilisateur, il ne quitte ni ne recharge jamais l'écran : il passe par un cadre caché, sans
scripts (`sandbox`), un refus de la route lu à l'adresse où elle renvoie le cadre et dit par la carte
(`downloadWhenThere`, `result-download.tsx`) — pas par `fetch`, que la garde du réseau réserve au
client de l'API et qui tiendrait le fichier en mémoire. Servi une fois (WF-DAT-0120), le fichier n'est
plus offert par la carte, qui garde sa phrase et sa croix — ni quand la relecture avant un clic le
dit parti. Fermé, le panneau suit
encore ses tâches — la coquille les relit (`TaskPolling`), hors des entrées — et son journal parle
toujours, hors du panneau, ou dedans tant qu'il est ouvert, où le focus est gardé. Une relance
refusée comme périmée (412) perd sa commande, qui le serait encore, et une relecture refusée
(404, 401) interrompt le suivi, qui le dit. Aucun écran ne suit ses tâches lui-même. Une réponse ne
s'applique qu'à la tâche pour laquelle elle a été demandée, jamais à celle qu'une relance a mise à
sa place. Les actions serveur de Next partent une à une, dans une seule file : suivre k tâches
ajoute k actions toutes les deux secondes, dans la file même des écritures de l'écran, qu'une
relecture lente retarde d'autant. Le stockage de session de l'onglet garde les tâches qui courent
pour un rechargement complet, sans leur commande mais avec le nom que l'utilisateur leur a donné ;
et, pour une session ouverte, le layout racine demande côté serveur les tâches de son utilisateur
qui courent (`listBackgroundTasks`), lancées d'un autre onglet ou d'un autre poste — plutôt que par
une action serveur au montage de la coquille, que `StrictMode` lançait deux fois en développement.
Il ne les attend pas : il passe leur promesse au suivi (`running`), qui la lit par `use()` sous un
`Suspense` qui ne rend rien, et le document part sans elles ; sans session, rien n'est demandé. Le
suivi les redemande par une action (`listRunningTasks`) chaque fois que l'onglet redevient visible
(`visibilitychange`, `signedIn`) ; il suit celles qu'il ne suivait pas — une liste refusée ou
injoignable le laisse tel qu'il est, et la promesse ne rejette jamais. Une tâche retrouvée par le
stockage ou par la liste ne se relance pas du suivi : échouée, son entrée dit de la relancer depuis
l'écran de son objet. La commande `mark` d'une révision (`MarkCommand`) en est le premier emploi :
elle ouvre, dans la page, la saisie du nom de version. « Contractualiser l'avenant »
(`MergeAmendmentCommand`, `revisions/`) en est un autre : offerte par la grille de planning d'un
différentiel non fusionné, comme la révision liste `merge_structure`, elle lit le compte rendu à
l'ouverture (`getStructureMergeReport`), le présente dans les marques `+`, `-`, `M` de la grille,
demande le nom de version et confirme avec les deux compteurs lus ; une version périmée (412)
propose de relire le compte rendu, et l'abandon n'envoie rien. La fusion remise au suivi,
`useWhenTaskSucceeds` dit à l'écran qu'elle a abouti, et il énonce la nouvelle référence. « Préparer
un avenant » (`create_structure`) demande un libellé et ouvre le différentiel créé dans la grille de
planning.

### L'historique des messages

L'historique des messages (#1043, `components/notices/message-history.ts`) garde chaque issue d'une
commande que les écrans ont dite, succès comme refus, pour qu'un avis fermé ou laissé sur un autre
écran se relise. Ce n'est pas le journal d'audit (WF-SEC-0030) : une aide à l'utilisateur, pour lui
seul, propre à la session de navigation — le stockage de session de l'onglet (`wf_messages`), les
cent dernières, effacé à la déconnexion —, sans opération du contrat. Le panneau des tâches et des
messages le montre, la dernière en tête (`MessageList`) ; ouvert, il les a toutes montrées, et le
compte des refus non lus retombe à zéro.

Une entrée (`Message`) garde :

- **l'heure** où l'avis a été dit, un instant du poste, montré par `LocalTime` ;
- **le ton** — `success` ou `refusal`, dit en mots, jamais par la seule couleur ; le service
  injoignable, une tâche échouée ou interrompue, des lignes refusées d'un collage sont des refus ;
- **la phrase de l'avis**, telle qu'elle a été dite, dans la langue du moment : l'historique répète,
  il ne réécrit pas ; et, pour une tâche échouée, **le motif** en seconde phrase (`detail`) ;
- **l'objet**, quand l'avis en nomme un : celui que l'écran donne — `subject` d'`OutcomeNotice`, de
  `Command`, de `DoneNotice` et de `ReferenceForm` (l'objet modifié : une ligne du référentiel, un
  projet, un sous-projet ; le projet d'une sortie du cycle de vie, la révision d'une commande de
  révision), `object` de `useSaid` —, sinon l'objet en conflit, la tâche — son genre et le nom que
  l'utilisateur lui a donné —, la copie externe éprouvée ;
- **la référence de corrélation** d'une erreur inattendue (`INTERNAL_ERROR`, WF-OBS-0020) ;
- **l'écran** : son adresse, où ramène un lien, et le projet qu'il montrait (`useShownProjectLabel`)
  ; le lien se nomme comme la fin du fil d'Ariane (`crumbsOf`), suivi du projet ; un écran que le
  fil ne nomme pas est « Écran d'origine ». La fin d'une tâche garde l'écran d'où elle a été lancée
  ; une tâche retrouvée — par la liste de l'API, après un rechargement — l'écran où sa fin est dite.

Ce qui l'alimente — l'issue de chaque commande, succès comme refus :

- **les refus** : `OutcomeNotice`, pour chaque refus qu'il dit — les avis de la grille compris, qui
  passent par lui —, `UnshownNotice` de la grille ; un refus dit hors d'un avis, par
  `useNoteRefusal`, dans la phrase même qu'un avis lui donnerait : un refus dit aux champs d'un
  formulaire (`ReferenceForm`, la création d'un compte, d'un rôle, la liste des contributeurs, le
  découpage), la date refusée d'une restauration, le refus d'une écriture partie d'un écran quitté,
  que dit la barre (`LeftRefusals`) avec l'écran d'où elle était partie, et celui du suivi d'une
  tâche, inscrit par `TaskPolling`, monté avec la coquille, panneau fermé ;
- **les succès** : chaque statut d'un écran qui dit ce qu'une écriture a fait, par `useSaid`
  (`components/notices/said.ts`), seul point d'entrée de ces statuts, qui le dit et l'inscrit ;
  `DoneNotice` (son `of` : l'issue qu'il dit, une par enregistrement) ; le squelette engendré, le
  dépôt d'une sauvegarde, le test d'une copie externe (`LocationTest`) ;
- **les collages** : `PasteAppliedNotice`, un succès quand toutes les lignes sont écrites — rien ne
  se dit alors sur place, la grille les montre —, un refus sinon, le nombre des lignes refusées en
  seconde phrase ;
- **le suivi** : une tâche remise (`useTrackTask`) et chaque fin de son journal.

Chacun y inscrit l'issue une fois, quelle que soit la fréquence de ses rendus (l'identité de
l'issue, `noteMessage`), sans rien annoncer : l'avis sur place reste l'alerte (`role="alert"`) ou le
statut, et l'historique n'est pas une région vivante. Un refus dit en partie aux champs est inscrit
entier, et la part que dit l'avis sous le formulaire n'est pas inscrite une seconde fois (`parts`).
Sur place, rien ne change. N'y entrent pas, faute d'une commande partie : ce qu'une commande
indisponible pressée n'a pas — ses conditions, que redit un statut (`noted: false` de `useSaid`,
`ToldConditions` des listes du référentiel) —, et le refus d'une saisie que l'écran juge avant
d'envoyer quoi que ce soit (un champ requis, un fichier trop lourd, une cellule mal tapée). Ni le
statut « Sauvegarde lancée », dont la tâche remise est déjà inscrite par le suivi.

### L'image de développement

L'image de développement (`frontend/Dockerfile`) part d'une image épinglée par son
empreinte, et tourne sous un utilisateur non privilégié, désigné par son numéro.

### Le client de l'API

Le client de l'API est engendré du contrat (PBS-1.2, WF-ARC-0060) : `make generate-client`
écrit ses types dans `frontend/src/api/generated/schema.d.ts`, que personne ne retouche, et
`frontend/src/api/client.ts` en fait des appels typés par openapi-fetch, une liste de la requête
écrite en un seul paramètre, ses valeurs séparées par des virgules, comme le contrat les déclare
toutes (`explode: false`, que `make lint-openapi` exige de chaque paramètre de tableau :
`rule/array-parameter-explode-declared` et `rule/array-parameter-not-exploded` de
`docs/api/redocly.yaml`). Il écrit à côté `examples.d.ts`, les exemples de `fixtures/api/` que
le contrat cite par opération et par statut (`wftools.exampleroutes`), qui type les réponses du
faux client des tests. Une opération qui
manque au client est une modification du contrat, suivie d'un `make generate-client` ; le
fichier engendré se versionne avec elle.

Le client garde ses connexions ouvertes, et la suivante réutilise celle qu'une réponse a libérée.
L'API ferme une connexion inactive après un délai à elle — cinq secondes pour Prism comme pour
uvicorn —, et undici, le `fetch` du serveur de Next, ne réutilise la sienne qu'en deçà d'une marge
sous ce délai ; mais son minuteur est celui de la boucle du serveur, qu'une charge retient plus
longtemps que la marge : la requête part alors sur une connexion que l'API vient de fermer, et
`fetch` la rejette (`UND_ERR_SOCKET`, `other side closed`, ou `ECONNRESET`), sans qu'aucun délai
plus court n'y change rien, retenu de même. Une lecture (`GET`, `HEAD`) ainsi coupée part une
seconde fois, sur une connexion nouvelle, et la coupure s'écrit au journal du serveur
(`console.warn`) ; coupée encore, c'est l'API hors d'atteinte (`Unreachable`), jamais un silence.
Une écriture ne repart jamais : l'API a pu la faire avant de fermer. Une écriture qui n'est pas
partie — le rejet de `fetch` nomme `ECONNREFUSED`, `ENOTFOUND`, `EAI_AGAIN`, `ENETUNREACH`,
`EHOSTUNREACH` ou `UND_ERR_CONNECT_TIMEOUT` — et toute lecture gardent « Le service est
injoignable ; réessayez dans un instant. ». Tout autre rejet d'une écriture — sa connexion perdue
(`UND_ERR_SOCKET`, `ECONNRESET`), sa réponse attendue au-delà du délai d'undici, un code que cette
liste ne nomme pas, ou aucun — la fait `Dropped`, dont le décodeur fait une issue `unreachable` avec
`sent` : `OutcomeNotice` dit que l'opération a pu aboutir, et relit l'écran (`router.refresh`), la
commande indisponible jusqu'au retour de la relecture (US-2240). La liste est celle des codes qui
disent que rien n'est parti : dire de recommencer une écriture peut-être faite est l'erreur évitée. `WATERFALL_API_CONNECTIONS` dit
comment le serveur tient ses connexions : `kept`, ou rien, en production comme en développement ;
`closed`, une connexion par requête, fermée une fois répondue (`Connection: close`), que seul le
harnais pose (« Un parcours de bout en bout »), et que le serveur, démarré ainsi hors du harnais du
faux back (`WATERFALL_E2E`), signale une fois au journal ; aucun fichier de `deploy/` ni l'image du
front ne la nomme, ce que `src/api/server.test.ts` vérifie. Toute autre valeur arrête le serveur à
son démarrage (`src/startup.ts`), plutôt que de répondre une erreur à chaque requête. La coupure
écrite au journal n'en dit que la méthode et le chemin, jamais la recherche.
`src/api/client.test.ts`, `src/api/connections.test.ts` — contre un serveur sur une vraie socket,
qui coupe la connexion réutilisée — et `src/api/server.test.ts` l'éprouvent. Aucun appel réseau ne
s'écrit hors de `frontend/src/api/client.ts`, et seul le serveur Next appelle l'API : un composant
client n'importe de `src/api/` que ses actions serveur (`src/api/actions/`) et des types.

_Contrôles_ : `make client-up-to-date` échoue si le client versionné n'est pas celui que le
contrat produit ; une modification du contrat réveille donc la famille front. ESLint refuse
hors de `src/api/client.ts` les moyens connus d'atteindre le réseau — `fetch`,
`XMLHttpRequest`, `WebSocket`, `EventSource`, un client http importé —, et, dans un fichier
`"use client"`, l'import direct de `src/api/` hors des actions serveur, qui s'ouvrent sur
`"use server"` ; `src/api/network-guard.test.ts` l'éprouve sur des extraits piégés, et fige
la liste des dépendances de `package.json`, pour qu'une nouvelle soit examinée pour la
garde avant d'entrer. Le cas transitif — un module sans directive qui importe
`@/api/server`, et qu'un composant client importe — échappe à ESLint : `client.ts` et
`server.ts` importent `server-only`, le filet de `next build`, que `make build-front` lance au
palier rapide, sans API joignable : une page qui lirait l'API à la construction, pré-rendue
au lieu d'être rendue à la requête, le fait échouer (#131) ; au palier complet, les parcours de
bout en bout le lancent avant de jouer contre le front construit (`make e2e`, `make e2e-measure`,
et le travail `front-build` de `ci.yml` dans la chaîne). Après l'une ou l'autre
construction, `make prerendered-front` affirme qu'elle n'a prérendu aucune page (« Chaîne »).
`make typecheck-front`, `make test-front` ;
`make lint-docker` (hadolint).

## Le faux back

Le faux back sert le contrat par prism, sans une ligne de réponse écrite à la main : ce qu'il
répond, ce sont les **exemples du contrat**. Une réponse qui manque est un exemple ajouté au
contrat, jamais un fichier dans le front ; un exemple invalide au regard de son schéma fait
échouer `make lint-openapi`.

Un exemple long se range sous `fixtures/api/`, en objet Example d'OpenAPI (`summary`,
`value`), et le contrat le cite par `$ref` ; le bundle l'embarque. Ses nombres reprennent
ceux des Vérif là où ils ont un sens — probabilité de gain, inflation, montants.

**L'univers témoin.** Les exemples décrivent un seul univers, à un seul instant, aujourd'hui :
le 3 juin 2026 à 14 h 05 UTC (`docs/api/DECISIONS.md`, « L'univers témoin »). Le premier
exemple de chaque opération est le projet témoin, PRJ-001, ou le portefeuille qui le compte, à
cet instant ; un autre exemple nommé en est une autre lecture, un instant antérieur de la même
chronologie, la suite d'une écriture faite aujourd'hui, ou une variante contrefactuelle déclarée.

**Ce qui s'engendre ne s'écrit pas à la main.** `make mock-data` (`wftools.mockdata`) écrit,
sans lire ni l'horloge ni le hasard — chaque valeur tirée vient de l'empreinte d'une graine fixe
et de ce qu'elle décrit, et deux engendrements écrivent les mêmes octets :

- dans `fixtures/api/volume/`, qu'on ne retouche pas, les volumes du §4.6.2 : la structure du
  témoin, mille tâches et cinq mille lignes, son cœur lisible en tête et relié aux tâches tirées
  autour de lui, datée en heures sur le calendrier de chaque tâche et lue aujourd'hui
  (`wftools.mockstructure`, datée et émise par `wftools.mockcore`), premier exemple de
  `listNodes`, les indicateurs de son devis, ce dont dépend sa première récapitulative et une
  durée allongée qui pousse une tâche en 2027 (`task_lengthened`) ; la comparaison de l'offre et
  de la référence sur toute cette structure, lue avec `fields`, deuxième exemple de
  `compareRevisions` (`wftools.mockcomparisons`, #1201) ; les trois cents projets de
  `getPortfolioProjects` et les vues qui se somment de leurs lignes — valeur, performance,
  structure des coûts, risques et couverture (`wftools.mockportfolio`) — ; les deux cents
  catégories de coût et quinze ans de taux horaires, en une page et par pages, la grille triée
  aussi par le taux d'une année (`wftools.mockreference`) ;
- sous `fixtures/api/`, par leur nom, les exemples du témoin, déclarés engendrés dans
  `tools/paths.toml` : les lectures de son cœur (`wftools.mockcore`, décrit une fois dans
  `wftools.mockwitness`, ses heures de travail dans `wftools.mockcalendar`, ses lignes triées sous
  chaque tâche, ou filtrées par les bornes d'une colonne, par `wftools.mocksort`) ; les réponses des
  écritures de grille, différence de deux lectures (`wftools.mockwrites`), dont celles des gestes de
  structure et de la saisie des tâches, avec leurs refus (`wftools.mockgestures`, la place d'un nœud
  et les boucles qu'un geste fermerait dans `wftools.mocktree`, les gestes du devis faits sur
  l'avenant 2, et la saisie et le collage qu'y font les parcours, dans
  `wftools.mockamendmentwrites` ; le collage qui crée les tâches au-delà de la dernière ligne, et
  l'annulation et le rétablissement d'un renommage, dans `wftools.mockundoable`, #2559, #2564), les
  gestes des cartes du Kanban et leurs réponses
  (`wftools.mockkanban`), et les refus d'un collage et d'un import qu'un sous-projet ou la phase du
  projet commandent (`wftools.mockexchanges`), et une date manuelle sur un jour chômé, refusée à la
  saisie et signalée à l'import (`wftools.mocknonworking`, #1271) ; son histoire
  (`wftools.mockhistory`), ses révisions lues avant la désignation de l'offre, quand elle est encore
  proposée (`wftools.mockcycle`), ses révisions marquées lues avec leur instantané
  (`wftools.mocksnapshot`), ses révisions comparées (`wftools.mockcomparisons`) et ses risques, et
  les réponses des saisies d'un risque, avec le devis propre du risque 751 et le compte rendu
  préalable de sa survenance (`wftools.mockriskwrites`) ; ses indicateurs, ses courbes, son plan
  de charge détaillé par tâche et sa projection de dépenses aujourd'hui, sur toute la structure de
  mille tâches, chaque ligne étalée par ses parts arrondies (`wftools.mocktoday`,
  `wftools.mockindicators`, `wftools.mockcurves`, `wftools.mockspending`) ; ses coûts réels — ceux
  que le témoin décrit et les factures de ses tâches tirées terminées — et le journal de leurs
  imports (`wftools.mockcosts`) ; et les vues du portefeuille dans le temps — plan de charge
  agrégé, courbe en S et sa variante au 31 décembre 2025, santé du pilotage —, qui somment le témoin
  à ses propres lectures et les autres projets par des formules simples
  (`wftools.mockportfoliotime`) ; et le journal d'audit de l'installation, tiré de la chronologie du
  témoin et des exemples qui datent ses comptes, ses rôles et ses sauvegardes (`wftools.mockaudit`,
  tenu par `tools/tests/test_mockaudit.py`), avec les chefs de projet qu'une liste des contributeurs
  inscrit, change ou retire (`wftools.mockauditmanagers`, US-2980) ; et les
  lectures des listes écrites à la main — les projets de l'accueil, les sous-projets et les
  contributeurs du témoin, les comptes et les rôles d'habilitation, les sauvegardes — et du
  lotissement du témoin, triées, cherchées et filtrées comme leurs écrans les demandent, avec la
  saisie du lotissement, sa réponse et ses refus (`wftools.mocklists`, tenu par
  `tools/tests/test_mocklists.py`) ; et les contributeurs du témoin une fois un compte anonymisé
  (`wftools.mockanonymized`, tenu par `tools/tests/test_mockfindings.py`) ; et la sortie du témoin,
  qui marque ou abandonne sa révision en cours, son code refusé, et ses lectures selon la qualité du
  lecteur — participant, ou non-contributeur qui inscrit un chef de projet quand aucun n'a de compte
  actif — ou pendant le marquage de sa révision en cours (`wftools.mockproject`, tenu par
  `tools/tests/test_mockexit.py`) ; et les refus d'une seule forme (`wftools.mockrefusals`, tenu par
  `tools/tests/test_mockrefusals.py`), avec ceux que le contrat déclarait sans code, condition ni
  exemple (`wftools.mockdeclared`, tenu par `tools/tests/test_mockdeclared.py`) ; et les exemples
  des majeurs de la revue du contrat du 2026-10-31 — la liste des projets avec le projet créé, le
  code d'un sous-projet trop long, la mise à jour des taux d'une catégorie non proposée, une tâche
  refusée sous un jalon, la récapitulative qui n'attend plus que ses lignes propres, les saisies
  d'une ligne d'une tâche terminée refusées sur la structure principale, le devis propre du risque
  survenu tel que la référence 101 le fige et les nœuds issus de sa survenance, le registre filtré
  sur ses colonnes, le cycle de vie d'un import et ses refus — (`wftools.mockreview`, tenu par
  `tools/tests/test_mockreview.py`).

Ce que la même commande engendre ne se relit jamais sur le disque : les indicateurs, les risques
et les courbes du témoin, que le portefeuille somme, lui sont passés en mémoire, pour qu'une seule
exécution de `make mock-data` atteigne son point fixe.

**La tranche du portefeuille**, hors du contrat, s'écrit sous `fixtures/witness/portfolio/` : la
description des dix projets que le chargeur du témoin ajoute à PRJ-001 et à PRJ-002, chaque écriture
dans la forme de son schéma du contrat (`projects/`, `wftools.mockslice`), et les lectures attendues
des huit vues du portefeuille au 3 juin 2026, lues par `as_of` (`readings/`,
`wftools.mockslicereadings` et `wftools.mocksliceviews`), calculées sans rien importer du back
(EP-11, US-2770 ; tenues par `tools/tests/test_mockslice.py` et
`backend/tests/test_witness_portfolio_slice.py`, chargées et comparées aux réponses du service par
`backend/tests/test_witness_portfolio.py` et `backend/tests/test_witness_portfolio_readings.py`).

**Ce qui reste écrit à la main** — sessions, comptes et rôles, référentiel (rôles de ressources et
leurs effectifs, calendriers, nœuds d'organisation), le projet, ses révisions et ses transitions,
imports et leurs comptes rendus, tâches de fond, état du système et sauvegardes, variantes
contrefactuelles — est lu par les générateurs, jamais recopié, et confronté à ce qui est engendré :
`tools/tests/test_mockhistory.py` pour la chronologie, `tools/tests/test_mockuniverse.py` pour le
reste (les heures mensuelles d'un rôle, tout son effectif compris, valent son effectif par les
heures hebdomadaires de son calendrier × 52 / 12, la ligne du témoin au portefeuille est celle de
ses indicateurs, toute vue du portefeuille est calculée aujourd'hui…). Un exemple de volume s'écrit
une ligne par élément, pour qu'un changement se lise dans le diff. Les repères que lisent les
parcours de bout en bout — numéros de ligne, libellés, totaux — sont fixés par
`test_the_marks_the_journeys_read` (`tools/tests/test_mockstructure.py`) pour la structure,
`test_the_marks_the_portfolio_journey_reads` (`tools/tests/test_mockdata.py`) pour le portefeuille
et `test_the_marks_the_review_journey_reads` (`tools/tests/test_mocktoday.py`) pour la revue
mensuelle : un changement du générateur qui les déplace échoue là, avant les parcours. Les tests de
grille ne vérifient que des lignes qui restent dans la fenêtre que la grille virtualisée rend. Les
tests du front lisent l'adresse d'un nœud du témoin dans l'exemple — son identifiant, son index ou
son numéro trouvés par son libellé —, jamais un numéro écrit en dur, sauf là où le numéro est ce que
le test éprouve (#400).

`make mock-spec` dérive du contrat la variante que prism sert : chemins sous le préfixe du serveur,
`/api/v1`, que prism ignorerait, et aucune sécurité exigée (`security` retiré) — le faux back
accorde la session dont part la maquette (EP-02), et Prism n'exige donc pas le jeton. Une troisième
différence : Prism sert le premier exemple d'une opération quel que soit son chemin, si bien que
`listNodes` de l'avenant aurait rendu la structure principale. La variante répète donc les chemins
de `listNodes`, `updateEstimateLine`, `previewPaste` et `applyPaste` pour chaque structure de nature
`amendment` que liste le premier exemple de `listCostStructures`, son identifiant écrit dans le
chemin, et y place l'exemple `amendment` de chaque opération en tête (`wftools.mock`, #1219, #1277)
: la lecture de l'installation sur l'avenant, la charge de sa ligne ajoutée saisie, et un bloc collé
sur ses lignes 7 à 9, aperçu puis appliqué (`wftools.mockamendmentwrites`). Prism classe un chemin
par ses segments écrits, devant celui qui les laisse en gabarit. Aucune réponse n'est écrite à la
main : le choix suit l'identifiant du chemin. Les autres chemins de l'avenant — ses gestes, son
planning — répondent comme ceux de la principale ; les avenants 212 et 213 et les structures de
risque ne sont pas aiguillés (EP-16). **Où jouent les parcours d'écriture.** La structure principale
du projet en cours liste le devis en lecture seule (#1176) : un parcours qui écrit le devis ne le
lit donc pas là. Celui de la saisie d'une ligne (`entry.spec.ts`) et celui du collage
(`paste.spec.ts`) jouent sur l'avenant 2, structure 203, dont le faux back sert les trois exemples
`amendment` ; le collage y retrouve `[WF-IHM-0050-A]`, les trois lignes du bloc de
`paste_applied_amendment` écrites après la confirmation. Les parcours qui n'ont pas d'exemple propre
à l'avenant restent sur la structure qui les sert, le devis propre du risque du recâblage (structure
204, qui reçoit le premier exemple de chaque opération) : le collage d'une catégorie inconnue, le
collage d'un bloc trop large, et la ligne de provision, que l'avenant ne porte pas. Un parcours qui
écrit sur un autre différentiel attend ses exemples, à EP-16. Rien d'autre ne change. Le contrat
garde le schéma `bearer`, et le front l'envoie quand même : en mode `WATERFALL_AUTH=mock`,
`serverClient()` pose `Authorization: Bearer` avec un jeton fixe (`MOCK_TOKEN`, `src/api/server.ts`,
sans valeur secrète), que seul le serveur de Next tient — le navigateur n'en détient aucun. Ce mode
est refusé quand `NODE_ENV` est `production`, sauf si `WATERFALL_E2E=1` : le harnais Playwright joue
ses parcours contre le front de production, et pose les deux variables à son front
(`playwright.config.ts`) ; `make dev` pose `WATERFALL_AUTH=mock` au front (`compose.dev.yaml`),
`make build-front` n'en a pas besoin. Contre une API que l'environnement nomme
(`WATERFALL_API_ADDRESS`), le harnais ne pose que `WATERFALL_E2E=1`, qui n'y admet aucun jeton fixe
(#1265).

- `make mock` : le faux back seul, sur `http://localhost:4010`.
- `make dev` : le front (`http://localhost:3000`) contre le faux back, par
  `deploy/compose/compose.dev.yaml`. Le front ne connaît que l'adresse de l'API,
  `WATERFALL_API_ADDRESS` : à partir d'EP-03, la même variable désigne le vrai service.
  `make dev-down` l'arrête. Le faux back garde le cache de npm, où `npx` a mis prism, dans
  le volume nommé `mock-npm`, monté sur le répertoire de l'utilisateur 1000 de l'image, qui
  en est propriétaire : prism n'est téléchargé qu'au premier démarrage.
  `docker volume rm waterfall-dev_mock-npm`, la plateforme arrêtée, l'oublie.
- Le front s'ouvre à `localhost` et à `127.0.0.1`. Pour l'ouvrir depuis un autre poste, à
  l'adresse de celui-ci sur le réseau, la déclarer dans `WATERFALL_DEV_ORIGINS` (des hôtes
  séparés par des virgules), à l'appel ou dans `deploy/compose/.env`, que git ignore :
  `WATERFALL_DEV_ORIGINS=127.0.0.1,192.168.1.210 make dev`. Sans elle, `next dev` refuse ses
  ressources à cette origine, et la page s'affiche sans s'hydrater (#481).

Le faux back sert des lectures. Il ne garde aucun état : un projet créé n'apparaît pas dans
la liste suivante. Il sert aux lots de front qui précèdent leur lot de back et aux tests du
front qui ne font que lire, jamais à éprouver une écriture.

### Ce que le faux back ne fait pas

Prism rend le premier exemple de l'opération quelle que soit la requête : il ne lit aucun paramètre.
Sur un écran de `make dev`, il n'applique donc ni filtre, ni recherche, ni tri, ni pagination
(`limit` et `offset` partent bien, mais la barre se calcule sur le `meta` de l'exemple, qui conclut
à une seule page), ni `kinds`, ni `fields`, ni `include_inactive` — et il ne garde rien. Un écran
qui en dépend se juge mal en maquette (#1399) : juger ces gestes revient aux tests du front, qui
éprouvent la requête que l'écran fait, et au service. Les écrans de listes et de grilles le disent
par `MockupNotice` avec `lists` (`mockup.notFiltered`), en une seule note sous l'en-tête. Les écrans
dont le service est livré ne portent pas la note, même si `make dev` les sert par Prism et que les
mêmes limites s'y appliquent : l'administration (EP-03), le référentiel (EP-05) et, d'EP-04,
l'accueil connecté (US-0920/L2), les révisions (US-0960, US-0970) et les paramètres du projet
(US-1000), puis, d'EP-06, les chronologies (US-1400), les échanges (US-1430), l'arborescence
(US-1440) et le planning (US-1470), d'EP-07, le plan de charge (US-1520), la comparaison des
révisions (US-1530), les contributeurs proposés (US-1540), l'import et l'export du devis (US-1550)
et le devis (US-1560), et, d'EP-09, les coûts réels (US-1620), la grille du reste à engager et le
Kanban (US-1640, qui en retire `MockupNotice`), et, d'EP-08, les risques (US-2640, qui en retire
`MockupNotice`) ; un succès y est ce que le service a gardé, relu.
Contre le faux back, l'écran des chronologies dessine tout le volume que Prism rend pour
`listNodes`, quelle que soit la chronologie : les parcours de la frise et du focus n'y jugent que la
disposition, et leur sélection se prouve contre le service.

_Contrôles_ : `make lint-openapi` (exemples conformes aux schémas, volumes compris),
`make mock-data-up-to-date` (les volumes versionnés sont ceux que l'outil écrit, dans la
famille contract, que `fixtures/api/` réveille comme le contrat), `make lint-compose`.

## Commandes

Tout se lance par le Makefile, sur un poste comme dans la chaîne : `make help` les liste.
Une commande que la chaîne exécute existe dans le Makefile, et un workflow n'écrit aucune
logique de contrôle de son côté ; un échec de la chaîne se reproduit donc par la même
commande.

| Commande                                                                | Ce qu'elle fait                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make check BASE=origin/epic/EP-nn`                                     | les contrôles de ce que la modification touche, fichiers non commités compris : à lancer avant de pousser                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `make check-all`                                                        | toutes les familles de contrôles                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `make check-<famille>`                                                  | une famille : `repo`, `spec`, `contract`, `back`, `front`, `front-image`, `roadmap`, `keycloak`, `service`, `production`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `make changes BASE=…`                                                   | les familles qu'une modification touche                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `make test-back TESTS=…`, `make test-front TESTS=…`, `make e2e TESTS=…` | un seul fichier de tests, pendant le développement ; sans `TESTS`, tous, comme dans la chaîne                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `make service-install`                                                  | amorce la plateforme de service démarrée, son royaume appliqué (`waterfall-api install`, US-0420) : applique les migrations sous le propriétaire des tables, crée l'installation, ses trois rôles prédéfinis et son administrateur local, `WATERFALL_ADMIN_EMAIL` (`administrateur@waterfall.test` par défaut), dans la langue `WATERFALL_DEFAULT_LANGUAGE` (`fr` par défaut), et son référentiel minimal (EP-05) : les paramètres communs, avec la devise `WATERFALL_CURRENCY` (`EUR` par défaut) et le nom de l'entreprise `WATERFALL_COMPANY_NAME` (`Delmas Automatismes` par défaut, ceux du témoin), et le fuseau horaire `WATERFALL_TIME_ZONE` (`UTC` si la variable est vide, à la première écriture seulement, un nom de la base IANA, refusé s'il est inconnu, dans lequel s'entend le jour courant, US-2200), les unités de durée, la correspondance des coûts réels, vide, le calendrier par défaut, la nature et la catégorie de provision pour risques ; écrit seul sur sa sortie le lien qui fixe son mot de passe, valable jusqu'à son emploi ; relancée, elle ne crée rien, dit ignorés une autre devise, un autre nom ou un autre fuseau — relancée sans fuseau, rien n'est dit —, et écrit un nouveau lien, qui remplace le précédent, tant que l'administrateur n'a pas de mot de passe, aucun ensuite                                                                                                                                                                                              |
| `make service-witness`                                                  | charge le témoin sur la plateforme de service démarrée et amorcée (`waterfall-api load-witness`, service `witness`, EP-05) : les exemples du contrat, `fixtures/api/`, montés en lecture seule, écrits par le rôle du service ; relancée, elle n'écrit rien ; une tranche par objet, dans l'ordre des dépendances, en une transaction (« Le back et les frontières du noyau »)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `make service-reference`                                                | charge le jeu de référence (`waterfall-api load-reference`, EP-13, US-2950) sur la plateforme de service démarrée et amorcée : le témoin, trois cents projets, l'histoire de PRJ-001 à cent quatre-vingts révisions marquées et dix-huit mille lignes de coût ; reprise là où elle s'est arrêtée ; près d'une heure ; `REFERENCE_PROJECTS`, `REFERENCE_REVISIONS`, `REFERENCE_COST_LINES` en demandent moins |
| `make service-reference-check`                                          | vérifie le jeu de référence que la plateforme de service porte (`waterfall-api check-reference`) : volumes, identifiants, sommes du portefeuille égales à celles de ses projets (budgets lus par l'estimation) ; échoue (1) sur un défaut ; mêmes `REFERENCE_*` |
| `make service-reference-backup`                                         | garde en sauvegarde le jeu de référence que la plateforme de service porte (`waterfall-api backup-reference`, US-2950/L2b) : vérifié entier, sauvegardé par la plateforme comme sa planification le fait, son archive et son manifeste lus dans `REFERENCE_ARCHIVES` (`~/.local/share/waterfall/reference`), nommés par la version, la graine et les volumes ; mêmes `REFERENCE_*` |
| `make service-reference-restore`                                        | retire les données de la plateforme de service du créneau, y restaure avant son démarrage le jeu gardé dans `REFERENCE_ARCHIVES` (`waterfall-api restore-reference`), puis la démarre ; `make service-reference-check` le vérifie ensuite ; mêmes `REFERENCE_*` |
| `make service-purge`                                                    | dépose à la main la purge de ce qui a expiré sur la plateforme de service démarrée (`waterfall-worker schedule`, dans le conteneur du service `scheduler`, avec un intervalle de purge d'une seconde, qui ne règle que la purge : une lecture des comptes dont la dernière a plus d'un jour est déposée aussi) : le worker l'exécute — comptes rendus d'import échus, dépôts échus, exports de plus de vingt-quatre heures, historique des sessions de plus de `WATERFALL_UNDO_RETENTION_HOURS` heures (12 par défaut), tâches terminées depuis plus de `WATERFALL_BACKGROUND_TASK_RETENTION_DAYS` jours (30 par défaut), et les objets que plus aucune ligne ne désigne sous `uploads/` et `exports/` ; aucune purge n'est déposée tant qu'une autre est en file ou en cours |
| `make measure-core`                                                     | lance la mesure du cœur dans le processus (`backend/measure/`, US-2210, EP-26), sans HTTP ni Keycloak, sur la base de la plateforme de service du créneau, qu'elle remet d'abord à zéro — arrêtée, ses données supprimées (`service-down WATERFALL_RESET_DATA=yes`), puis démarrée, amorcée et le témoin chargé (`service-up`, `service-install`, `service-witness`), les secrets de `service-up` attendus dans l'environnement — : une lecture entière de PRJ-001 seule, puis avec `kinds=task` ; la même sous profil, par étape (lecture, corps, sérialisation), avec la part de PostgreSQL ; par plusieurs fils et par plusieurs processus ; le rapport d'une saisie — un libellé, une durée qui redate — à une lecture ; l'ouverture d'une révision ; la dernière révision marquée lue entière depuis ses lignes, puis gardée et lue depuis ce qui est gardé, entière et projetée, la taille gardée et le volume qu'en garderait une plateforme aux volumes du §4.6.2, et le marquage de la révision en cours suivi de la garde de sa structure principale (US-2270) ; la comparaison de la révision en cours à la révision marquée qu'elle copie — ce qu'elle vérifie —, entière depuis les lignes des deux structures (avant l'option 1 de #3168, la quantité sur laquelle se lit son seuil), entière depuis la lecture gardée de la base (après l'option 1, comme la grille du devis la demande) et sur ses tâches depuis les lignes (`kinds=task`, comme la grille du planning la demande), découpée en la part de ses deux lectures, de l'union — par soustraction, les deux chronométrées dans un ordre qui alterne, leurs dispersions données et une union sous zéro signalée — et du corps, et le compte des nœuds qui diffèrent, par nature et par marque, sur ceux de l'union (US-2390, l'option 3 de #3168) ; ce que coûtent les entrées du cache des indicateurs du jour, une par maille, dans le Redis du créneau (`WATERFALL_REDIS_PASSWORD`, `WATERFALL_REDIS_PORT`) — leur taille, la lecture de la maille du projet contre celle de toutes les mailles, à froid et à chaud, celle de toutes extrapolée linéairement à 10, 50 et 100 sous-projets (US-2420, #3628) ; la fusion d'un différentiel que la mesure ouvre elle-même, une durée saisie dedans, dans la révision en cours, puis la survenance d'un risque identifié du projet, relevées sans objectif (US-2650/L2, EP-08). Les identifiants des structures se lisent dans la base ; chaque écriture est annulée, la mesure suivante part du même témoin. Le rapport s'écrit lisible, et en JSON avec `JSON=<fichier>` ; `RUNS=<n>` règle les passages identiques de la lecture entière, de la saisie et de l'ouverture de révision (cinq : leur dispersion dit ce qu'un écart doit dépasser pour être un gain), chacun après un passage d'échauffement qu'on ne compte pas ; le profil et les vagues de lectures par fils et par processus n'ont qu'un passage, ce que le rapport dit, et les vagues échauffent chaque fil et chaque processus et assurent une lecture à chacun ; `ONLY="read profile parallel write revision kept current indicators merge occurrence"` n'en joue qu'une part. Les saisies annulées laissent des tuples morts dans les tables du témoin, ce qu'une longue série peut montrer : la mesure suivante repart d'un témoin rechargé. Elle prend le poste pour elle seule (`$(exclusive)`, « Le poste pour une mesure seule ») : toutes les exécutions lourdes des autres livreurs attendent sa fin. Elle n'échoue jamais sur une durée et la chaîne ne la joue pas. Le paquet est typé et analysé comme `src/waterfall` (Ruff, Pyright), absent de l'image du back et de la couverture |
| `make measure-reference`                                                | assemble `docs/measures/reference.json` depuis le JSON de `make measure-core` (`CORE=<fichier>`) et celui de `make measure` (`JOURNEY=<fichier>`), sans toucher une durée, avec la cible de l'API pour ouvrir une grille, le commit mesuré et la date de prise (« La référence, et le gain d'un lot ») ; refuse l'absence de `CORE` ou de `JOURNEY` |
| `make measure-workbooks`                                                | mesure ce qu'un classeur engendré coûte à son lecteur (`backend/measure/workbooks.py`, US-3190/L2b, EP-33, « Les bornes des classeurs »), sur les seuls classeurs qu'elle engendre — ceux de `backend/tests/workbook_bombs.py`, des writers d'export, des supports de tests et les prototypes de la spécification —, jamais un fichier déposé : sans `VECTOR`, les vecteurs de ces classeurs (chaînes partagées, éléments d'une chaîne, texte, listes de `styles.xml`, noms définis, lignes et cellules) et le temps qu'ajoute le jugement de l'archive sur l'export de 10 000 lignes et l'extraction de 18 000 lignes ; `VECTOR=<vecteur> COUNTS="<nombre>…"`, le pic de la lecture d'un devis enflé le long d'un vecteur, chaque point dans un processus neuf (taille résidente de crête, et `tracemalloc` à part). Une ligne JSON par point ; elle prend le poste pour elle seule (`$(exclusive)`), n'échoue jamais sur un chiffre et la chaîne ne la joue pas |
| `make service-up`, `make service-down`                                  | démarre, arrête la plateforme de service (`deploy/compose/compose.service.yaml` : PostgreSQL, Redis, le stockage objet Garage et ses compartiments, les migrations, l'API, le worker et le planificateur de ses tâches, le service de la restauration, Keycloak derrière son frontal HTTPS et son royaume, appliqué de nouveau à chaque démarrage par `keycloak-realm`, qui reste démarré pour le réappliquer après une restauration, OpenLDAP, Mailpit) ; elle exige ses secrets dans l'environnement (ci-dessous), et `service-down WATERFALL_RESET_DATA=yes` supprime aussi ses bases, son stockage, son annuaire et l'autorité de son frontal ; `service-up` refuse un volume PostgreSQL d'une autre majeure que 18, en affichant le refus de `postgres-volume`, qui dit ce remède (US-1130)                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `make keycloak-authority`                                               | copie hors de la plateforme la racine de l'autorité du frontal de Keycloak, dans `deploy/compose/.authority/root.crt`, que git ignore ; `service-up` et `test-keycloak` le font à chaque démarrage                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `make e2e-service`                                                      | les parcours du projet Playwright `service` (`frontend/e2e/service/`), et ceux de `shared` (l'étiquette `@shared`), contre le vrai service, par Prism en mandataire (« Un parcours de bout en bout ») ; mêmes secrets que `service-up`, et le navigateur de `make e2e-browsers` ; il charge le témoin après l'amorçage, comme `make service-witness` ; `TESTS=<arguments de playwright test>` : un fichier seul joue aussi `installation`, et, s'il porte un parcours `@realm-wide` ou `@platform-wide`, les projets dont dépend le sien (`service`, `shared`, `shared-serial`) ; `TESTS="--no-deps --project=shared --project=realm e2e/reference-resources.spec.ts e2e/service/reference-manager.spec.ts"` ne joue que ces fichiers, sans `installation` (sur une installation déjà jouée) ; `SHARD=i/N` (N d'au moins 2, pas avec `TESTS`) ne joue que le i-ième de N morceaux, sur sa plateforme : les N-1 premiers se partagent `service` et `shared` par durée mesurée (`tools/e2e-service-durations.json`), le dernier joue `shared-serial`, `realm` et `restoration`, seuls                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `make service-logs`                                                     | les journaux des services de la plateforme, ceux de `SERVICES` (`SERVICES="keycloak openldap"`), tous par défaut                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `make service-logs-search`                                              | les journaux des services de la plateforme et le journal du front des parcours (`frontend/.e2e/front.log`), où il cherche les secrets et les jetons connus — les variables de `service-up`, sous leurs écritures brute, JSON et URL, et la forme d'un JWT ou d'un en-tête `Bearer` — et échoue s'il en trouve un ; `CORRELATION=<identifiant>` donne à la place l'histoire de cet identifiant : ses lignes, celles du dépôt, de l'import et de la tâche qu'elles nomment (WF-OBS-0020, US-2900)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `make service-logs-fields`                                              | vérifie que chaque enregistrement des journaux de l'API, du worker, de son ordonnanceur et du service de restauration porte l'identifiant de corrélation, l'auteur et la gravité (WF-OBS-0020, US-2900)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `make test-services`, `make test-services-down`                         | démarre, retire les services des tests (`deploy/compose/compose.test.yaml` : PostgreSQL 18, Redis, Garage, en mémoire) pour le créneau du worktree, sur ses ports (`SERVICES=redis` n'en démarre que certains) ; `test-services` attend qu'ils répondent et ne fait rien de plus s'ils tournent, `test-services-down` les retire avec leurs volumes ; `make test-back` et les autres tests qui en ont besoin les démarrent d'eux-mêmes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `make migrate`                                                          | applique les migrations à la base que désigne `WATERFALL_DATABASE_URL`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `make build-keycloak`                                                   | construit l'image de Keycloak (`deploy/keycloak/`) : l'extension compilée et ses tests JUnit passés, les thèmes, le royaume ; aucune JVM n'est demandée au poste                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `make save-keycloak`                                                    | écrit l'image de Keycloak, construite par `build-keycloak`, dans `KEYCLOAK_ARCHIVE` : le job `keycloak-image` de `ci.yml` la construit une fois par passage et la publie en artefact                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `make load-keycloak`                                                    | charge l'image de Keycloak depuis `KEYCLOAK_ARCHIVE` (`$RUNNER_TEMP/keycloak-image.tar` par défaut), sans la construire : les parts de `service.yml` la chargent puis lancent la plateforme avec `WATERFALL_KEYCLOAK_LOADED=1`, que le Makefile traduit en `compose.keycloak-loaded.yaml`. Piège : posée sur un poste, cette variable fait que `service-up` ne construit plus l'image de Keycloak et échoue faute d'image ; elle n'est faite que pour la chaîne                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `make test-keycloak`                                                    | démarre Keycloak sur la plateforme — et Mailpit, où il envoie ses courriels et où ses tests les lisent —, applique son royaume et lance les tests du marqueur `keycloak` (`backend/tests/test_keycloak_*.py`), que les autres tests du back écartent : le royaume et l'extension, et l'API qui valide ses jetons, servie dans le processus des tests sur une base qu'ils créent sur le PostgreSQL de la plateforme, sauf si `WATERFALL_TEST_DATABASE_URL` en nomme un autre ; il mesure la couverture du client de l'API d'administration de Keycloak et de l'amorçage, `waterfall-api install` (« Couverture du code ») ; mêmes secrets que `service-up`. Ses tests changent le royaume le temps d'un test — la durée d'une session inactive, celle des liens, le verrouillage, l'annuaire et le fournisseur désactivés, l'annuaire non synchronisé (`UNSYNCED`) —, et l'un d'eux redémarre Keycloak (#852) : il ne se lance jamais en même temps qu'un autre usage de la plateforme, `make e2e-service` ou les tests d'un autre agent, pas plus que `make check-keycloak` ni `make check` quand il éprouve la famille `keycloak` ou `service`                                                                                                 |
| `make check-keycloak`                                                   | la famille `keycloak` : `build-keycloak`, `test-keycloak`, puis `test-openldap`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `make images`                                                           | construit les trois images que la chaîne publie — `front`, `waterfall`, `keycloak` —, chacune l'étape `production` de son Dockerfile, sous `ghcr.io/waterfall-project/<image>`, étiquetées par le commit (son empreinte entière), par la branche mise en forme d'étiquette (`epic/EP-03` donne `epic-EP-03`) et, sur `main`, par la version de la distribution du back (`backend/pyproject.toml`), que le front porte aussi, une seule fois et pour les trois ensemble : l'étiquette de version est immuable ; la branche et le commit sont ceux du dépôt, sauf si `IMAGE_BRANCH` et `IMAGE_COMMIT` les nomment ; `PUSH=yes` les publie, depuis `main` ou une branche `epic/…` seulement, d'un dépôt propre au commit nommé, une fois les trois construites et fouillées (`wftools.images`, « Chaîne »)                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `make prerendered-front`                                                | lit le manifeste que la dernière construction de production du front a écrit (`frontend/.next/prerender-manifest.json`) et affirme qu'elle n'a prérendu que `/_global-error` et `/icon.svg`, sans Docker : la famille `front` l'enchaîne après `build-front` au palier rapide, après les parcours au palier complet (`wftools.frontimage --manifest`, « Chaîne »)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `make check-front-image`                                                | la famille `front-image` : construit l'étape `production` du front (`frontend/Dockerfile`), la démarre, et affirme que `/` répond avec les réglages du service `front` du Compose de production, que le front s'arrête sans chacune des variables dont il ne se passe pas en la nommant (#825), que `WATERFALL_AUTH=mock` sans `WATERFALL_E2E` est refusé, et que `next build` n'a prérendu que `/_global-error` et `/icon.svg` (`wftools.frontimage`, « Chaîne »)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `make production-trial`                                                 | démarre la plateforme de production (`deploy/compose/compose.prod.yaml`, US-0430) sur les images de l'étiquette `WATERFALL_IMAGE_TAG` — le commit du dépôt par défaut —, sous un nom local (`WATERFALL_DOMAIN`, `waterfall.localhost` par défaut, avec `compose.prod.local.yaml`), l'amorce, affirme la sonde de vie de l'API, que le propriétaire des tables, `waterfall`, n'est pas superutilisateur, le renvoi de HTTP à la même page sur l'adresse publiée, port compris, les en-têtes de Caddy en HTTPS, HSTS d'abord, que la console de Keycloak et le royaume `master` répondent 404, et que le premier administrateur fixe son mot de passe par le lien, se connecte par le front et Keycloak et que le front le nomme ; avec `WATERFALL_TRIAL_RESTORATION=1`, une sauvegarde puis sa restauration demandées par l'API, la restauration suivie par la sonde de vie jusqu'à `ok` (`wftools.restoration_trial`, US-0440, #948), que la chaîne demande (`production.yml`, `images.yml`) ; puis la retire avec ses volumes (`wftools.production`) ; ses secrets viennent de l'environnement, comme `deploy/compose/production.env.example` les nomme ; son projet Compose est `WATERFALL_PRODUCTION_PROJECT` (`waterfall-production-trial`) |
| `make check-production`                                                 | la famille `production`, au palier complet seulement : `make images`, sans poussée, puis `make production-trial` sur les images construites                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `make kube-tools` | télécharge Helm, kind, kubectl, promtool, amtool et alertmanager — ceux des versions de Prometheus et d'Alertmanager que la plateforme fait tourner, dont les tests du chart éprouvent les règles d'alerte et la configuration (US-2880), et dont le premier pèse près de 100 Mo ; les essais de notification démarrent le serveur `alertmanager` (`tools/tests/test_notificationlive.py`) — aux versions et aux empreintes que `wftools.kubetools` épingle — PyPI ne les tient pas comme il tient actionlint, hadolint et shellcheck —, et les garde sous `~/.cache/waterfall/bin` (`XDG_CACHE_HOME`), un dossier par version, que les worktrees partagent ; un téléchargement d'une autre empreinte est refusé (US-2800) |
| `make lint-chart` | contrôle le chart (`deploy/helm/waterfall`) par `helm lint --strict`, avec les valeurs de la chaîne (`wftools.chart`, US-2800) |
| `make test-chart` | rend le chart par Helm et affirme ce que ses objets disent, contre le Compose de production : les déploiements distincts, la multiplication de l'API et du worker par une valeur, les services, l'ingress, le secret et les volumes, les crochets, les CronJobs, les mêmes images et les mêmes fichiers, `HOSTNAME` posé pour le front (#826) ; les tests du marqueur `chart`, que `make test-tools` écarte |
| `make chart-trial` | installe le chart sur un cluster kind jetable, `WATERFALL_CHART_CLUSTER` (`waterfall-chart-s<créneau>`), avec Traefik pour l'ingress, à partir des images de l'étiquette `WATERFALL_IMAGE_TAG` — le commit par défaut, `make images` d'abord —, sous `waterfall.localhost` sur un port libre de la boucle locale ; affirme que l'installation aboutit, ses crochets compris — migrations, royaume, amorçage —, que la sonde de vie de l'API répond et que le premier administrateur se connecte, par les fonctions de `wftools.production`, puis supprime le cluster (`wftools.charttrial`) ; une exécution lourde, qui attend son tour |
| `make chart-upgrade` | met à jour le chart sous charge, sur un cluster kind jetable à lui (`waterfall-upgrade-s<créneau>`) : installe la version N — la dernière version publiée qui porte le chart, à défaut `BASE` ou son plus proche premier parent dont les images sont publiées, son chart extrait du commit —, la met à jour vers la branche (images de `WATERFALL_IMAGE_TAG`, `make images` d'abord), revient à N, puis remet à jour ; sous des requêtes du premier administrateur dont aucune ne doit échouer, affirme les migrations avant les instances, aucun pod de PostgreSQL, de Redis ou du stockage redémarré, le retour arrière sur le schéma de N+1 et aucune migration rejouée ; sans base qui porte le chart, se déclare non exécuté (`wftools.chartupgrade`, US-2850) ; une exécution lourde |
| `make check-chart` | la famille `chart` : `lint-chart` et `test-chart` à chaque palier ; au palier complet, `make images`, sans poussée, puis `make chart-trial` et `make chart-upgrade` |
| `make migrations-tests` | joue les tests du back de la dernière version publiée, extraits de son étiquette, sur le schéma des migrations de la branche, ses propres tests de migrations écartés (`wftools.migrationtests`, US-2850), jugés contre les échecs connus de `tools/migrations-known.toml` ; `SHARD=i/N` en joue un morceau ; une exécution lourde, sur les services des tests du back ; sans version publiée, se déclare non exécuté |
| `make migrations-backup` | démarre le Compose de production de la dernière version publiée depuis ses images, sous un projet du créneau qui ne publie aucun port, l'amorce, charge son témoin et lui fait prendre une sauvegarde (`EARLIER_BACKUP`, `wftools.migrationbackup`), puis la restaure et la migre par la branche (`backend/tests/test_earlier_backup.py`) : aucune ligne perdue, les lignes de ses révisions marquées inchangées (US-2850), jugé contre les échecs connus ; une exécution lourde, sur les services des tests du back |
| `make check-migrations` | la famille `migrations`, au palier complet seulement : `make migrations-tests` puis `make migrations-backup`, chacun jugé contre les échecs connus de `tools/migrations-known.toml` |
| `make mirror`                                                           | vérifie que ghcr.io tient, par leur empreinte, les images de Docker Hub que les fichiers nomment derrière le miroir ; `PUSH=yes` copie celles qui manquent (`wftools.mirror`, « Chaîne »)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `make mirror-sync`                                                      | recopie le manifeste des images de Docker Hub, `deploy/images/Dockerfile`, que Dependabot suit, dans les `Dockerfile`, les fichiers Compose et les workflows, étiquette et empreinte, sans toucher au préfixe du miroir, ancres YAML comprises ; relancée, elle ne change rien ; échoue en nommant ce que la recopie ne règle pas (image absente du manifeste, ligne du manifeste inutilisée ou mal formée ; `wftools.mirror sync`, « Chaîne »)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

La plateforme de service refuse de démarrer sans ses secrets, qu'aucun fichier ne porte :

| Variable                               | Ce qu'elle protège                                                                                                                                                                                                                                                                                  |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `WATERFALL_POSTGRES_PASSWORD`          | le rôle `waterfall` de PostgreSQL, propriétaire des tables, par lequel passent les migrations ; en lettres et en chiffres seulement, puisqu'il s'écrit dans une URL                                                                                                                                 |
| `WATERFALL_SERVICE_DATABASE_PASSWORD`  | le rôle `waterfall_service`, nommé d'après la base, par lequel l'API et le worker se connectent, qui ne tient que ce que les tables lui accordent (sql.md, « Le rôle du service ») ; en lettres et en chiffres seulement                                                                            |
| `WATERFALL_BACKUP_DATABASE_PASSWORD`   | le rôle `waterfall_backup`, membre de `pg_read_all_data`, par lequel le worker sauvegarde les deux bases, qui lit toutes les tables et ne peut ni écrire ni couper un déclencheur (#895) ; en lettres et en chiffres seulement                                                                      |
| `WATERFALL_REDIS_PASSWORD`             | Redis                                                                                                                                                                                                                                                                                               |
| `WATERFALL_KEYCLOAK_DATABASE_PASSWORD` | le rôle `keycloak`, propriétaire de la base de Keycloak, distincte sur le même serveur                                                                                                                                                                                                              |
| `WATERFALL_STORAGE_SECRET`             | la clé de la plateforme sur son stockage objet, Garage, dont l'identifiant, qui n'est pas un secret, est `WATERFALL_STORAGE_ACCESS_KEY` (`GK000000000000000000000001` par défaut)                                                                                                                   |
| `WATERFALL_STORAGE_RPC_SECRET`         | le canal interne de Garage ; 64 chiffres hexadécimaux (`openssl rand -hex 32`), Garage refusant toute autre forme                                                                                                                                                                                   |
| `WATERFALL_KEYCLOAK_ADMIN_PASSWORD`    | l'administrateur `admin` du royaume `master`, par lequel keycloak-config-cli applique le royaume `waterfall`, et que lisent les tests de `make test-keycloak` ; il n'est lu qu'au premier démarrage, qui crée le royaume `master` : en changer demande `make service-down WATERFALL_RESET_DATA=yes` |
| `WATERFALL_FRONT_CLIENT_SECRET`        | le client `waterfall-front` du royaume                                                                                                                                                                                                                                                              |
| `WATERFALL_SERVICE_CLIENT_SECRET`      | le client `waterfall-service`, le compte de service de l'API et du worker                                                                                                                                                                                                                           |
| `WATERFALL_INSTALLATION_CLIENT_SECRET` | le client `waterfall-installation`, celui de l'amorçage seul, dont les liens valent jusqu'à leur emploi (#652), et qui donne au royaume la langue de l'installation (`manage-realm`, #873) : ni l'API ni le worker ne le tiennent                                                                   |

Sur un poste, des valeurs de poste suffisent — celles de `.github/workflows/keycloak.yml` par
exemple. Keycloak répond en HTTPS sur `https://localhost:8443/auth`, sa console d'administration
sous `/auth/admin`, par un frontal Caddy (`deploy/compose/Caddyfile.service`) que le navigateur
et le serveur de Next joignent tous deux, et qui le sert aussi sur `https://127.0.0.1:8443/auth`,
une seconde adresse pour les tests de la plateforme (#680) ; son adresse,
`WATERFALL_KEYCLOAK_ADDRESS`, est `https://localhost:<port>/auth` : le frontal ne sert que les
hôtes `localhost` et `127.0.0.1`, et seul le port se déplace, par `WATERFALL_KEYCLOAK_PORT` :
le Makefile et Compose la déduisent de lui, et ne lisent aucune adresse exportée (#735).
Les certificats viennent de l'autorité propre de Caddy (`tls internal`) : sa racine, gardée
dans le volume du frontal, est copiée à chaque démarrage dans
`deploy/compose/.authority/root.crt` ; le front s'y fie par `NODE_EXTRA_CA_CERTS`, qui l'ajoute
aux autorités qu'il connaît, les tests de `make test-keycloak` par `SSL_CERT_FILE`, qui en fait
leur seule autorité, un navigateur en l'important, ou en acceptant l'avertissement. uv lit aussi
`SSL_CERT_FILE` : `make test-keycloak` synchronise l'environnement du back sans elle, puis lance
les tests sans le resynchroniser (`uv run --no-sync`) — sinon, sur un poste ou un runner sans
cache, uv ne se fierait plus à GitHub pour télécharger Python ou les paquets (#737). L'API, dans
le réseau de la plateforme, joint Keycloak en HTTP sur `keycloak:8080` ; le chiffrement de ce
lien relève d'EP-13 (WF-SEC-0010).
Redis est publié sur `127.0.0.1:6379` (`WATERFALL_REDIS_PORT`), pour un front lancé sur le poste
(#681), qui l'atteint par `redis://:<mot de passe>@127.0.0.1:6379/0`. Keycloak notifie la
fermeture des sessions à ce front par le canal de retour, à l'adresse
`WATERFALL_FRONT_BACKCHANNEL` (`http://host.docker.internal:3000` par défaut, l'hôte vu de son
conteneur), distincte de `WATERFALL_FRONT_ADDRESS`, celle du navigateur : le front écoute alors
sur toutes les interfaces du poste, pas sur la seule boucle locale. Les deux adresses s'écrivent
dans le royaume quand il s'applique, et `make e2e-service` les remplace par celles du front de ses
parcours, jusqu'au `service-up` suivant. Mailpit
montre les courriels sur `http://127.0.0.1:8025`. Le royaume de développement ajoute un annuaire
OpenLDAP de test et un second royaume, `external`, qui joue le fournisseur externe : leurs comptes
et leurs mots de passe, des valeurs de développement, sont dans `deploy/keycloak/development/`. Il
ajoute aussi `waterfall-test`, un client public qui accepte un mot de passe hors de la page du
royaume, pour les jetons dont les tests de la plateforme ont besoin : `admin-cli`, que Keycloak
crée dans chaque royaume, n'en accepte plus (#644), et ses jetons ne sont pas pour l'API, faute de
l'audience `waterfall-api`. Ces fichiers s'appliquent après le royaume, sous un état distant à eux
(`--import.cache.key=development`, service `keycloak-realm`) : keycloak-config-cli supprime les
clients que son état nomme et que les fichiers qu'il applique ne déclarent pas, et sans cela le
client de test emporterait ceux du royaume.
L'annuaire est une image que le dépôt construit, `deploy/openldap/Dockerfile`, sur le `slapd` de
Debian (US-1150) : à son premier démarrage, son script d'entrée crée sa configuration et y charge
`deploy/keycloak/development/directory.ldif`, puis ne recharge plus rien. Il garde ses données dans
un volume, comme les bases : réamorcé, il donnerait à ses personnes d'autres identifiants que ceux
que Keycloak garde ; `WATERFALL_RESET_DATA=yes` le supprime avec elles. Avant de charger l'amorce,
le script pose un repère, `.seeding`, dans le volume des données, et ne le retire qu'une fois la
configuration copiée dans son volume ; un repère resté auprès de la configuration (arrêt entre la
copie et le retrait) est retiré au démarrage suivant. Un premier démarrage interrompu avant cette
copie laisse le repère : les données n'ont jamais servi, et au démarrage suivant le script les vide
et recharge l'amorce, comme il le fait sur deux volumes vides. Des données sans repère et sans
configuration sont celles d'un annuaire qui a servi, dont le volume de configuration a disparu : le
script refuse (code 1) de les réamorcer, ce qui donnerait d'autres identifiants à ses personnes, et
dit le remède, `make service-down WATERFALL_RESET_DATA=yes`. Cela vaut aussi pour un volume laissé
par une amorce interrompue sans repère (ancienne version du script) : il est refusé, et le remède
le supprime. Les volumes de l'image précédente, celle d'`osixia`, servent tels quels : leurs
personnes gardent leurs identifiants.

Les ports cités ici sont ceux du dépôt principal, au créneau 0 ; un worktree de lot a ceux du
bloc de son créneau (« Les créneaux des worktrees », ci-dessous).

`BASE` vaut `origin/main` par défaut ; un lot se compare à la branche de son EPIC.

`make lot-size BASE=origin/epic/EP-nn` mesure un lot : les lignes de son diff, séparées en
code de production, tests et le reste (documentation, configuration, contrat), les fichiers
engendrés mis à part. La pull request met ce nombre à côté de l'estimation de son issue ; un
dépassement ne fait rien échouer (README de la roadmap, section « Lots »).

`make check-measures` confronte les rapports de mesures des versions
(`docs/measures/<version>.json`, WF-QUA-0060-A) : la chaîne ne mesure pas, les durées d'un runner
variant du simple au double, elle lit ce qu'un poste a mesuré et que le dépôt versionne. Un rapport
nomme chacune des onze opérations du tableau 15 avec son objectif, sa médiane, sa pire durée, sa
dispersion (l'écart-type de l'échantillon, n − 1, des passages identiques, en secondes ; seule la
médiane est confrontée) et, si elle dépasse son objectif ou se dégrade, un `note` qui le documente ;
une opération que le service ne sert pas encore porte `unserved`, l'EPIC qui la mesurera, et aucune
durée. La commande compare les deux derniers rapports (`reference.json`, pris avant toute
correction, n'en est pas un) et affiche, pour chaque opération servie, sa médiane et celle de la
version précédente, lue dans le rapport précédent et non recopiée : un objectif dépassé, une médiane
de plus d'un quart au-dessus de celle de la version précédente ou une opération servie par celle-ci
et qui ne l'est plus est un avertissement de la chaîne (`::warning::`), et un échec si le rapport ne
le documente pas. Sans rapport précédent, seuls les objectifs comptent ; sans aucun rapport, elle
passe. Famille `measures` de la chaîne, dans `make check-all`.

`make measure-version` prend le rapport de mesures d'une version (US-2300,
`frontend/e2e/measure/version.measure.ts`), sur un poste, le poste pour elle seule (`$(exclusive)`,
« Le poste pour une mesure seule ») : elle retire les données de la plateforme de service du
créneau et y restaure le jeu de référence aux trois cents projets (US-2970, `make
service-reference-restore` : l'archive de `make service-reference-backup`, jamais réengendrée ici —
sans elle, la mesure s'arrête en le disant ; `MEASURE_FROM=witness` charge le témoin à neuf, comme
`make measure`, pour un essai), redemande le lien du premier administrateur — l'archive porte un
administrateur qui n'a posé aucun mot de passe —, puis mesure sur PRJ-001, sous la charge de
cinquante utilisateurs, chaque opération d'écran du tableau 15 que le service sert. Le jeu restauré
a cent quatre-vingts révisions marquées sur PRJ-001 : la révision en cours n'est plus celle du
témoin, la préparation la lit (`listRevisions`, `measuredRevision` de `steps.ts`) et les grilles, la
charge et l'export s'ouvrent sur elle. La préparation, hors de la mesure, crée par les
opérations du contrat cinquante et un comptes (`accounts.ts`) — cinquante pour la charge, un pour le
navigateur —, les inscrit sur PRJ-001, prend au fournisseur d'identité les jetons des utilisateurs
de la charge, par le flux du front (`frontTokens`), et choisit la tâche que chacun écrit — en mode
automatique, non démarrée, ni récapitulative ni jalon, réparties sur la seconde moitié du planning,
loin de celle du navigateur — ; elle écrit le tout dans `frontend/.e2e/load/load.json`, lisible de
son seul propriétaire, effacé une fois la charge arrêtée. La charge est k6, dans le service `load`
de la plateforme (profil `load`, image épinglée par son empreinte), qui joue
`frontend/bench/load.ts` : un fichier TypeScript du front, typé et analysé avec lui (`@types/k6`),
dont le tirage (`bench/draw.ts`) et les requêtes (`bench/screens.ts`) ont leurs tests unitaires.
Chaque utilisateur virtuel fait un geste toutes les dix secondes en moyenne, après une pause tirée
entre cinq et quinze, et une saisie dans chaque suite de dix gestes, à une place tirée : neuf
lectures pour une saisie, exactement ; le tirage part d'une graine fixe et du numéro de
l'utilisateur, le même d'une mesure à l'autre. Une lecture demande à l'API ce que porte un écran du
parcours des grilles — les structures et les nœuds de la grille de planning, de devis ou de reste à
engager, avec les champs, les genres et les filtres par défaut que demande sa page (le test les
confronte à `nodeFieldNames`), le devis filtré par un lot, trié, cherché, le plan de charge — ; une
saisie écrit le libellé de sa tâche, ou une durée qui la redate, au compteur lu, repris du refus
`412` quand une autre saisie l'a périmé. Les requêtes que le serveur de Next fait à côté pour chaque
écran (session, projet, navigation) ne sont pas rejouées. k6 parle à l'API et renouvelle chaque
jeton par son jeton de rafraîchissement, une minute avant son expiration, sur le canal arrière de
Keycloak, dans le réseau de la plateforme. Sous cette charge, le navigateur joue le parcours des
grilles de `make measure` (`steps.ts`) puis ouvre par la navigation le plan de
charge, la projection de dépenses et les indicateurs de la révision en cours (`project-screens.ts`,
chaque écran utilisable quand ses sections sont là, ses graphiques hydratés et dessinés, le haut de
la première dans la fenêtre ; le plan de charge et la projection sont les échantillons d'une seule
opération du tableau 15, `workload-or-projection`, dont la `note` ne dit rien de cela : elle n'est posée que sur une médiane au-dessus de l'objectif), un passage non mesuré puis `MEASURE_PASSES` (cinq) ; puis, `MEASURE_TASK_PASSES`
fois (trois), l'export du planning, l'analyse et l'application d'un import de dix-huit mille lignes
de coût réel, aux pièces propres à chaque passage, et le marquage de la révision en cours, rouverte
(`createRevision`, hors de la mesure) avant chaque passage après le premier, chacun lu à sa tâche de
fond (`getBackgroundTask`), de sa soumission à sa fin. Le marquage vient en dernier : il fige la
révision que la charge écrit, dont les saisies sont dès lors refusées. Le rapport
(`frontend/e2e/measure/version.ts`) a la forme que `make check-measures` confronte, plus `taken_at`
et `conditions`, dont les volumes lus à la préparation (tâches, lignes de devis) et le résumé de la charge (gestes, lectures et saisies refusées, durée, gestes attendus) ; ouvrir une grille regroupe les quatre
ouvertures du parcours, filtrer, trier ou chercher les trois gestes sur le devis, recalculer la
durée saisie (le libellé ne recalcule rien) ; la médiane et la pire durée sont celles de toutes les
mesures, la dispersion l'écart-type (n − 1) des médianes des passages. Il s'écrit dans
`MEASURE_VERSION_REPORT` (`frontend/.e2e/measures/<version>.json`, la version de
`frontend/package.json` sauf `MEASURE_VERSION`), jamais de lui-même sous `docs/measures/`, où le
versionne le lot de la version, avec les `note` de ses dépassements. La mesure n'échoue sur aucune
durée : seulement sur un compte qu'elle ne peut créer, des volumes inférieurs à ceux du §4.6.2 (mille
tâches, cinq lignes de devis par tâche en moyenne, à l'arrondi près du témoin : 4,9 au moins), une tâche
de fond qui échoue, ou une charge qui n'a pas tourné comme demandé (`load-check.ts`) : sans résumé,
un utilisateur refusé faute de jeton, plus d'un dixième de lectures ou de saisies refusées — de un à dix pour cent, au-delà de ce que tolère la mesure, c'est la saturation de l'API (#5158) : la mesure ne s'en arrête pas et le rapport la dit, `conditions.load.saturation` — (un refus isolé par catégorie est toléré s'il est nommé au rapport, lu dans le journal de k6 avant l'arrêt ; un refus que le résumé compte et que le journal ne nomme pas, survenu pendant l'arrêt, n'est pas toléré), hors
les gestes que le marquage refuse — le `409` `STATE_FORBIDS_OPERATION`, seul attendu, et non tout
`409` : une saisie sur la révision marquée, la lecture du plan de charge sur la révision en cours
d'un projet qui n'en a plus —, comptés à part (`reads_frozen`, `writes_frozen`) : ceux-là ne
comptent qu'après le premier marquage demandé, et que dans la part de la charge où la révision est
restée gelée, à une marge de dix pour cent près (une charge gelée pendant toute sa durée les
accepte toutes) ; ou moins de la moitié des
gestes que promettent les pauses (utilisateurs × durée ÷ 10 s). Les passages d'import ne sont pas à
volume constant : le deuxième importe ses dix-huit mille lignes à côté des dix-huit mille du
premier, le troisième à côté de trente-six mille, comme le ferait un projet qui reçoit des coûts, et
le rapport le dit. Le conteneur de la charge s'arrête à la fin de la mesure, réussie ou non ; après
une interruption, `make e2e-down` ou `make service-down` l'arrête. `E2E_LOAD_USERS` (cinquante) est
réservé aux essais — `make measure-version exclusive= E2E_LOAD_USERS=3 MEASURE_PASSES=2
MEASURE_TASK_PASSES=2` —, et un rapport de version se prend à cinquante : le rapport consigne
`users`. Mêmes secrets que `make
service-up`, et le navigateur de `make e2e-browsers` ; le projet Playwright `measure-version`, que
pose `E2E_PART=measure-version`, n'est joué par aucune cible de la chaîne. L'entrée du cache des indicateurs ne se mesure pas ici :
`make measure-core ONLY=indicators JSON=frontend/.e2e/measure-core-indicators.json` la mesure à part,
sur son propre témoin, et `make measure-version` en lit le JSON (`MEASURE_CACHE`, sa valeur par défaut
est ce fichier, que la cible exporte en `E2E_MEASURE_CACHE`) pour porter l'objet `cache` sur
l'opération `indicators` ; les deux repartent d'un témoin neuf et prennent le poste seules, elles se
suivent et ne s'imbriquent pas, et la seconde refuse de partir sans le fichier de la première, avant
toute installation ou construction. Un objectif dépassé s'écrit dans une note, sans que la mesure
échoue : la médiane d'une opération dans la `note` de l'opération ; la maille lue seule à froid,
dans la `note` de l'objet `cache` de `indicators` (elle cite #3802, où se décide son calcul) ; une issue
à trancher s'ensuit (US-2420). De même une étape que le navigateur ne mène pas à sa fin sous la
charge (US-2970, #4117) : elle est comptée à sa borne (`STEP_BOUND` de `steps.ts`, 180 s), un
échantillon censuré, marquée `unreached` — l'étape et le nombre de passages manqués — sur l'opération
du rapport, dont la `note` la dit ; l'opération dépasse alors son objectif, et la mesure n'échoue
pas, même quand une étape n'est atteinte à aucun passage. Les appels de la préparation et du
suivi des tâches (pas les lectures mesurées) attendent `PREPARATION_CALL` (deux minutes), l'API mettant
en file ses réponses à cette charge (#5158).

**La mesure aux volumes (US-2970/L2).** Avant la charge, la préparation ouvre la vue de portefeuille
(`/portfolio/projects`, `portfolio-screen.ts` : de la requête à la valeur du portefeuille et à un
premier projet affichés) une fois à froid — la première lecture après le démarrage, le cache des
indicateurs vide — puis cinq fois à chaud, et lit les indicateurs conservés à cinq dates passées, celles
du marquage de révisions réparties sur l'histoire de PRJ-001 (`getProjectIndicators?as_of=`,
WF-DAT-0040 ; `volumes.ts`) : une première lecture à part, puis cinq. Le rapport porte ces
lectures à côté de ses opérations — `portfolio` (à froid, à chaud, et la décision sur le préchauffage
du cache, `portfolioReading` de `scale.ts` : à chaud au-dessus de l'objectif, le cache n'est pas ce qui
coûte ; à froid au-dessus et à chaud en dessous, le préchauffage est retenu ; à froid dans l'objectif,
il ne l'est pas) et `kept` —, que `make check-measures` ne lit pas ; la vue de portefeuille est aussi
l'opération `portfolio-view` du tableau, ouverte à chaque passe sous la charge. La décision se consigne
dans les notes de réalisation d'US-2970 du fichier de l'EPIC ; un préchauffage retenu devient une issue,
il ne s'implémente pas ici.

`make measure-scale` (US-2970/L2, WF-DAT-0050-A, seconde phrase :
`frontend/e2e/measure/scale.measure.ts`, projet Playwright `measure-scale`) lit les mêmes révisions
marquées de PRJ-001 sur le témoin chargé à neuf puis sur le jeu de référence restauré à six cents
projets (`SCALE_PROJECTS`, l'archive de `make service-reference-backup REFERENCE_PROJECTS=600`), par la
lecture des nœuds de leur structure principale, une première lecture à part et `SCALE_PASSES` (neuf)
après elle : la durée est celle de l'API de la requête à la réponse entière, planification comprise,
jamais un `EXPLAIN`. Il écrit l'écart de chaque lecture et de leur somme dans `SCALE_REPORT`
(`frontend/.e2e/scale/scale.json`) : un écart de plus d'un quart, dans un sens ou dans l'autre, est
un constat que le rapport signale, sans que la mesure échoue ; PRJ-001 porte en outre sur le grand jeu
cent quatre-vingts révisions que le témoin n'a pas, ce que le rapport dit. Hors de la chaîne, comme
toute mesure, le poste pour elle seule.

`make tracking ISSUE=<n>` change une ligne du tableau de suivi du corps de l'issue de l'EPIC, par
`gh`, et ne touche à rien d'autre : `LOT=<identifiant>` (`US-1080` pour une US d'un seul lot,
`US-1120/L2` pour le lot d'une US qui en a plusieurs) avec `STATE`, `PR` ou `MODEL`, les seuls
donnés changeant ; `US=<identifiant> STATUS=…` ; `FINDING=<n> ATTACHED=… DECISION=…`, qui ajoute
le constat (le titre de son issue sans le `[EP-nn]`, `à trancher` en gras), le change s'il est
déjà là, ou le retire quand son issue est fermée. `LOT=<identifiant> NOT_WITH=<liste>` remplace la
cellule « Pas avec » de ce lot, et d'aucun autre : la symétrie de la colonne (README de la roadmap,
« Suivi sur GitHub ») se déclare par un appel pour chaque lot de la paire. Le lot coupé à la demande
du relecteur s'écrit par elle aussi, jamais à la main : `LOT=<identifiant> DEPENDS=<liste>` remplace
la cellule « Dépend de » ; `ADD_LOT=<identifiant> AFTER=<lot> [DEPENDS=<liste>] [NOT_WITH=<liste>]
[MODEL=…] [LOT_ISSUE=<n>]` insère, sous le lot `AFTER` et dans la même US, la ligne du lot nouveau
(`US-0820b` pour la part détachée d'une US à lot unique, `US-1270/L3` pour une US à plusieurs ;
cellules `#`, `US`, « Statut » vides, « Dépend de » et « Pas avec » la liste ou `—`, « État du lot »
`à faire`) et refuse un lot déjà là ;
`ADD_US=<US-nnnn> AFTER=<US-mmmm> [US_ISSUE=<n>] [FIRST_LOT=<Ln>] [LOT_ISSUE=<n>] [DEPENDS=<liste>]
[NOT_WITH=<liste>] [MODEL=…]` insère la ligne de l'US nouvelle sous la dernière ligne d'`AFTER` (US
et lots) : son rang est celui d'`AFTER` plus 1, les US suivantes sont renumérotées, sa cellule « Lot »
vaut `lot unique` sans `FIRST_LOT` et `<Ln>` avec (`LOT_ISSUE`, l'issue de ce premier lot, ne va
qu'avec `FIRST_LOT` : un `lot unique` n'a pas d'issue propre), et une US déjà là est refusée ;
`REPLACE_DEPENDENCY='<ancien>=<nouveau>'` remplace la mention de l'ancien lot dans « Dépend de » de
toutes les lignes où elle paraît, sauf celle du lot nouveau lui-même, retire avec elle le ` #n` qui
la suit (l'issue de l'ancien lot ne reste jamais sur le nouveau), dit combien de lignes ont changé
et refuse quand aucune ne porte l'ancien. `LOT` reconnaît `US-0820b`, `US-1270/L2b` et une cellule
`lot unique (#1840)` ou `lot unique — en dernier`. Les colonnes se repèrent par leur en-tête ; la
cible refuse, code non nul et corps inchangé, une ligne qu'elle ne trouve pas, une valeur vide ou à
saut de ligne et une ligne du tableau plus courte que son en-tête ; un `|` d'une valeur est
échappé. Elle ne prend une variable que sur la ligne de commande de make (une `PR` exportée sur le
poste ne change rien), et ignore une valeur vide (`STATE=`). Elle relit le corps sous un verrou du
poste propre à l'issue, `waterfall-tracking-<issue>.lock` du répertoire des verrous du poste (plus
bas), juste avant de l'écrire : deux appels simultanés gardent chacun leur changement.

`make merge-queue-check EPIC=EP-nn` vérifie qu'un jeu de règles actif vise `refs/heads/epic/EP-nn`
avec une règle `merge_queue` (`wftools.mergequeue`, par `gh api`), et échoue en disant ce qui
manque : aucun jeu, pas de règle de file, jeu inactif, ou aucun contrôle exigé. Elle passe dès
qu'un des jeux visant la branche est actif avec une règle `merge_queue` et qu'un jeu actif qui la
vise — le même ou un autre, comme « epic protection », qui vise `epic/*` — exige le contrôle
`gate` (`required_status_checks`) : une file qui fusionne sans contrôle exigé fusionne ce que rien
n'a éprouvé. Elle dit aussi l'écart entre les types de règles du jeu de la file et ceux du
modèle (`required_signatures`, que portent les jeux d'EP-10, d'EP-26 et d'EP-27, y est).
Un jeu qui exclut la branche ne la vise pas. Les références de `include` et d'`exclude` se lisent
comme des motifs, par `fnmatch` avec `FNM_PATHNAME`, comme GitHub les lit (`refs/heads/epic/*`,
`~ALL`) : un `*` ou un `?` s'arrête à un `/`, donc `refs/heads/*` ne vise pas
`refs/heads/epic/EP-nn` ; seul un `**/` en début de segment franchit des répertoires, zéro ou plus
(`refs/heads/**/*`), un autre `**` vaut `*`, et `refs/heads/**` ne vise pas plus la branche ; les
accolades se lisent telles quelles, GitHub n'acceptant pas `FNM_EXTGLOB` ; `~DEFAULT_BRANCH` n'est
pas résolu. `make merge-queue EPIC=EP-nn` crée ce jeu, « merge queue epic/EP-nn », depuis le modèle
`.github/rulesets/merge-queue.json` (la copie du jeu d'EP-05, sans identifiants ni dates), et refuse
quand un jeu vise déjà la branche ou quand `EPIC` manque ou n'a pas la forme `EP-nn`. Elle est
réservée à une personne : un livreur ne la lance jamais, il lance la vérification et, en échec, pose
la question ; le garde (`guard.py`) refuse la cible `merge-queue` à un agent.

`make queue-report BRANCH=epic/EP-nn [LAST=<n>] [SINCE=AAAA-MM-JJ]` relève, du poste et jamais
dans la chaîne, les passages de la file de fusion d'une branche (`chain`, événement `merge_group`,
lus par `gh` ; `wftools.queue`, US-1880) : leur nombre par conclusion, leurs échecs par job et par
étape — avec la cible du Makefile que nomme `make: ***` —, les parcours et les tests en échec avec
leur fichier et leur ligne, lus au journal du job (Playwright, pytest, Vitest), la durée de mur des
passages réussis où le palier complet a tourné en entier — un passage *complet* est un passage où un
job de `service` et un job de `e2e` ont réussi, `ci.yml` sautant dans la file les familles que le
changement ne touche pas —, en médiane et au 90e centile (au rang le plus proche), avec le nombre de
passages que la mesure retient, et les minutes-runner, la
somme des durées des jobs. Sans `BRANCH`, toutes les branches comptent ; `SINCE` garde les passages
créés ce jour-là ou après (en UTC), `LAST` les n plus récents ; sans l'un ni l'autre, les 50
derniers. Chaque échec se classe contre `tools/queue-known.toml`, une entrée par instabilité connue
— des motifs de job, d'étape, de test ou de message, sa famille, l'issue qui la suit, sa fréquence,
sa cause établie ou son hypothèse — : instabilité connue, infrastructure, ou régression, qui ne
s'écrit qu'après la relecture du passage et le nomme. Ce qu'aucune entrée ne reconnaît sort « à
classer » (`to classify`) : l'outil ne décide jamais seul. `gate`, qui échoue parce qu'un autre job
a échoué, ne compte que s'il échoue seul. Le fichier porte aussi la référence — 370 passages et 88
échecs du 2026-11-05 au 2026-11-12, dont 68 dans `service / paths` ; 16 minutes de mur en médiane
les 10 et 11 novembre —, que le rapport rappelle à sa fin ; la pull request d'un lot de la chaîne
cite la sortie avant et après. La commande lit les jobs de chaque passage et le journal de chaque
job en échec : comptez quelques secondes par passage, davantage quand `service / paths` échoue, son
journal pesant plusieurs mégaoctets.

Le poste n'admet que `WATERFALL_SLOTS` exécutions lourdes à la fois — les tests entiers et la
couverture du back et du front, `make test-tools`, la construction du front pour la production,
les parcours de bout en bout —, tous dépôts et worktrees confondus. Cette variable de
l'environnement, celle du profil de l'utilisateur, est un entier de 1 à 9 ; absente, elle vaut 1 ;
toute autre valeur est refusée, en le disant. L'admission est
`tools/src/wftools/slots.py run --heavy -- <commande>` (bibliothèque standard seule, et
`heavyturns.py` à côté, qui prend les tours ; lancée par `python3` sans `uv`, au travers de
`tools/src/wftools/launch.py slots` : sous un `python3` antérieur à 3.14, le lanceur dit que l'outil
n'a pas tourné et quelle version il attend, et le Makefile relaie ce message au lieu de refuser
`WATERFALL_SLOTS`, US-2450), que le Makefile place devant chaque exécution lourde : elle prend le
premier de N fichiers de verrou du répertoire des verrous du poste (plus bas) —
`waterfall-heavy.lock`, puis `waterfall-heavy.2.lock` à `waterfall-heavy.<N>.lock` —, dit une fois
que tous sont pris et réessaie chaque seconde, garde le verrou jusqu'à la fin de la commande, sans le
transmettre à ses enfants (un serveur resté derrière ne garde pas le créneau), relaie les signaux et
rend le code de la commande.
Une exécution d'un seul fichier (`TESTS`) n'attend pas. Elle pose aussi `WATERFALL_PROCESSORS`, les
processeurs divisés par N, au moins 1 : les workers de pytest (`-n`, huit au plus pour le back), de
Vitest et de Playwright s'y règlent, sauf `WORKERS`. À N = 1, la part est le poste entier : rien ne
change.

**Le poste pour une mesure seule** (US-2210). `slots.py run --exclusive -- <commande>`, que la
variable `exclusive` du Makefile pose devant une commande, prend tous les tours des exécutions
lourdes : d'abord la barrière `waterfall-heavy.exclusive.lock`, puis les neuf fichiers de verrou,
`waterfall-heavy.lock` à `waterfall-heavy.9.lock` — les neuf, quel que soit son N, pour retenir
aussi un livreur dont le N est plus grand —, toujours dans cet ordre : deux commandes exclusives
passent l'une après l'autre, jamais chacune avec une moitié des tours. Elle dit une fois qu'elle
attend la fin des exécutions lourdes en cours, garde tout jusqu'à la fin de la commande, et rend
tout aussi quand on l'interrompt (`SIGINT`, `SIGTERM`, une exception). Une exécution lourde lancée
pendant ce temps attend, en le disant une fois : elle prend un verrou partagé de la barrière, sans
attendre, le temps de chercher un tour. Un outil plus ancien, qui ignore la barrière, est attendu
comme toute exécution en cours, mais il n'attend pas la barrière à son tour : il sonde les tours
chaque seconde et peut en reprendre un avant la mesure, sans fin. Une mesure ne tient donc le poste
contre les autres livreurs qu'une fois ce mode repris par leurs branches, et le pilote ne la lance
pas avant. La commande reçoit le marqueur `WATERFALL_SLOTS_HELD=exclusive:<jeton>` : un `make`
qu'elle lance et qui passe par `$(heavy)`, ou une autre commande exclusive, ne prend aucun tour — ce
sont ceux de la mesure —, le dit, et s'exécute ; sans cela il attendrait sans fin la barrière que
tient son parent. Le jeton — le PID de l'exécution exclusive et l'instant où elle a pris la
barrière — s'écrit dans le fichier de la barrière. Le marqueur n'est cru que tant qu'une exécution
exclusive tient la barrière **et** que son fichier porte ce jeton : celui d'une mesure finie n'est
pas cru quand une autre mesure tient la barrière (US-2460). Un marqueur sans jeton, posé par un
outil d'avant, est cru tant que la barrière est tenue. La commande
reçoit aussi `WATERFALL_PROCESSORS` du poste entier, mais une recette qui l'écrit après
`$(exclusive)`, comme `WATERFALL_PROCESSORS=$(WATERFALL_PROCESSORS)`, l'emporte avec la part de N
que make a calculée avant : une cible de mesure tire la variable du mode, sans la réécrire. Les
travaux légers des autres livreurs — un fichier de tests (`TESTS`), le lint, le typage — continuent.

**Les créneaux des worktrees** (US-1100). Chaque worktree d'un lot prend un créneau de 1 à N — le
même `WATERFALL_SLOTS` —, qui lui donne ses ports, ses projets Compose et les étiquettes de ses
images : deux livreurs jouent ensemble les parcours de bout en bout, les tests de Keycloak ou les
parcours contre le service sans se heurter. Le dépôt principal, comme chaque runner de la chaîne,
est au créneau 0 : ses ports et ses noms sont ceux d'avant les créneaux.

**Un worktree ne se tire jamais sous `/tmp`** (#2953). Le tmpfs de `/tmp` a manqué d'inodes le
2026-11-12 sous les `node_modules` de worktrees tirés dans des scratchpads : un worktree se tire
sous le dépôt (`.claude/worktrees/`) ou ailleurs sur le disque, jamais dans `/tmp` ni dans un
scratchpad. Aucun outil ne le contrôle : `make slot` et `make slots` ne comptent pas les inodes.

| Commande            | Ce qu'elle fait                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make slot`         | prend pour le worktree où elle est lancée le premier créneau libre de 1 à N, ou dit le sien ; avec `LOT=<identifiant>`, elle y écrit le lot, et si N sont pris, elle reprend celui qu'un autre worktree tient pour ce même lot, jamais celui d'un autre ; si N sont pris et qu'aucun n'est à reprendre, elle échoue, porteurs nommés ; dans le dépôt principal (son `.git` est un répertoire), elle dit le créneau 0, sans en prendre |
| `make slot-release` | arrête les serveurs de l'e2e du créneau, retire ses conteneurs et ses volumes — la plateforme de service, les services de test —, puis le libère ; si Docker ne peut les retirer, le créneau reste pris, et elle le dit                                                                                                                                                                                                               |
| `make e2e-down`     | arrête les processus de l'utilisateur qui écoutent sur les ports de l'e2e du créneau — le faux back, les fronts des parcours (au créneau 0, 4110 et 3100 à 3139) —, chacun trouvé par son port dans `/proc`, arrêté par son PID : `SIGTERM`, puis `SIGKILL` après cinq secondes ; elle dit ce qu'elle arrête, et rien quand rien n'écoute                                                                                             |
| `make slots`        | écrit N, puis chaque créneau pris sur le poste, tous dépôts confondus, avec son worktree, son lot s'il a été pris avec `LOT`, et l'instant de sa prise                                                                                                                                                                                                                                                                                |

**Le répertoire des verrous du poste** porte le registre des créneaux, les verrous des exécutions
lourdes, ceux des services de test et ceux du tableau de suivi : `/run/user/<uid>` s'il existe,
`/tmp` sinon (WSL, un runner) ; une seule fonction de `tools/src/wftools/heavyturns.py`
(`runtime_directory`) le donne à `slots.py` et à `tracking.py` (US-2460). `XDG_RUNTIME_DIR` n'est
pas lue : une session sans elle — une tâche planifiée, `su`, le terminal d'un éditeur — verrouillait
sous `/tmp` pendant que les autres verrouillaient sous `/run/user/<uid>`, et deux exécutions se
croyaient chacune seules sur le poste (PLC-13). Sous une session systemd, `XDG_RUNTIME_DIR` vaut
`/run/user/<uid>` : le répertoire est celui d'avant, et les outils d'une branche qui n'a pas
US-2460 s'excluent encore avec ceux qui l'ont. Là où elle pointe ailleurs (WSLg,
`/mnt/wslg/runtime-dir` ; une session sans systemd), un outil d'une branche qui n'a pas ce lot
verrouille sous `XDG_RUNTIME_DIR`, un outil qui l'a sous `/run/user/<uid>` ou `/tmp` : ils ne
s'excluent pas tant que la branche n'a pas repris le lot. `WATERFALL_RUNTIME_DIR`, que seuls les
tests posent, le remplace : aucun test ne touche les verrous du poste.

Le registre du poste est `waterfall-slots/` de ce répertoire, comme les verrous des exécutions
lourdes : un fichier `<i>` par créneau pris, qui porte le chemin du worktree (`git rev-parse
--show-toplevel`), l'instant de la prise et, pris avec `LOT`, le lot en troisième ligne, écrit
sous un verrou exclusif du registre (`tools/src/wftools/slots.py claim`, `release`, `list`) ; un
fichier de deux lignes, écrit sans `LOT` ou par l'outil d'une branche plus ancienne, n'a pas de lot.
Un créneau dont le worktree n'existe plus est libre. Les N pris, `make slot LOT=<identifiant>`
reprend celui qu'un autre worktree, même encore là, tient pour le même lot : le pilote ne lance
qu'un livreur par lot, et l'autre s'est arrêté sans `make slot-release` — une limite d'usage, un
livreur planté (US-2460) ; le créneau d'un autre lot, ou sans lot, n'est jamais repris. Celui qui
prend un créneau, libre ou repris, en retire d'abord ce qu'un porteur y a laissé (`docker
compose -p <projet> down --volumes`, pour chacun de ses deux projets), le verrou du registre tenu
jusqu'à ce que ce retrait ait réussi, comme le tient `make slot-release` : un `make slot` lancé
entre-temps attend, en le disant, et si Docker échoue, le créneau n'est pas pris, et le `make slot`
suivant refait le retrait. Avant ce retrait, l'un et l'autre arrêtent les serveurs de l'e2e que le
créneau a laissés (`make e2e-down`). `slots.py which` dit le créneau du worktree courant.

Un créneau libre se prend avant tout : la reprise n'a lieu que si les N sont pris, et un créneau
tenu pour un lot ne s'ajoute donc pas aux créneaux libres que le pilote compte. Celui que l'arrêté
tenait, quand un libre a été pris, reste pris, au nom de son ancien worktree, jusqu'au retrait de
ce worktree. Limites connues : la clé de la reprise n'est que l'identifiant du lot, alors que le
registre est commun à tous les dépôts du poste — deux dépôts qui portent un même identifiant de lot
pourraient se reprendre un créneau — ; et la reprise ne regarde pas si l'ancien worktree a encore
un livreur vivant : elle suppose, comme le pilote le garantit, un seul livreur vivant par lot.

Au créneau i de 1 à 9, les ports sont ceux du bloc `20000 + 100·i`, sous la plage des ports
éphémères de Linux ; au créneau 0, ceux d'avant :

| Ce qui écoute                                    | Variable                                                                                          | Créneau 0              | Créneau i                      |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------- | ---------------------- | ------------------------------ |
| PostgreSQL, Redis et Garage des services de test | `WATERFALL_TEST_POSTGRES_PORT`, `WATERFALL_TEST_REDIS_PORT`, `WATERFALL_TEST_STORAGE_PORT`        | 20000, 20001, 20002    | `20000 + 100·i`, `+ 1`, `+ 2`  |
| PostgreSQL et Redis de la plateforme de service  | `WATERFALL_POSTGRES_PORT`, `WATERFALL_REDIS_PORT`                                                 | 5432, 6379             | `+ 10`, `+ 11`                 |
| l'API, Keycloak, Mailpit, le mandataire de Prism | `WATERFALL_API_PORT`, `WATERFALL_KEYCLOAK_PORT`, `WATERFALL_MAILPIT_PORT`, `WATERFALL_PROXY_PORT` | 8000, 8443, 8025, 4210 | `+ 12`, `+ 13`, `+ 14`, `+ 15` |
| le faux back des parcours                        | `E2E_API_PORT`                                                                                    | 4110                   | `+ 20`                         |
| les fronts des parcours, un par worker           | `E2E_FRONT_PORT`, le premier                                                                      | 3100 et les suivants   | `+ 40` à `+ 79`                |
| le front et le point de métriques du parcours des métriques | `E2E_METRICS_FRONT_PORT`, `E2E_METRICS_PORT` | 3180, 3181 | `+ 80`, `+ 81` |

Les noms portent le numéro du créneau : au créneau i, les projets Compose `waterfall-service-s<i>`
(`WATERFALL_SERVICE_PROJECT`) et `waterfall-test-s<i>` (`WATERFALL_TEST_PROJECT`), les images
`waterfall-keycloak-s<i>` (`WATERFALL_KEYCLOAK_IMAGE`) et `waterfall-openldap-s<i>`
(`WATERFALL_OPENLDAP_IMAGE`), que `compose.service.yaml` lit, et `waterfall-front:check-s<i>`
(`WATERFALL_FRONT_CHECK_IMAGE`, que lit `wftools.frontimage`) ; au créneau 0, `waterfall-service`,
`waterfall-test`, `waterfall-keycloak`, `waterfall-openldap` et `waterfall-front:check`.
Le Makefile donne à chaque cible ce dont elle a besoin, sauf ce que l'environnement donne déjà :
la plateforme de service — `service-up`, `service-install`, `service-logs`, `service-down`,
`keycloak-authority`, `test-keycloak`, `e2e-service` — reçoit son projet, les images de Keycloak et
de l'annuaire et ses six ports ; `build-keycloak`, l'image de Keycloak ; `e2e`, `e2e-measure` et
`e2e-service`, les ports du faux back et des fronts ; `check-front-image`, l'image du front. Dans un
worktree lié qui ne tient pas de créneau, ces cibles échouent avant de rien lancer, en disant
`make slot` ; les autres ne le demandent pas. `make production-trial`, hors des créneaux — ports 80
et 443, projet `waterfall-production-trial` —, ne tourne qu'au créneau 0 : depuis le worktree d'un
lot, il échoue d'emblée, en le disant.

**Les services des tests** (US-1110). Les tests du back ont besoin de PostgreSQL, de Redis et du
stockage objet, ceux du front de Redis (« Tests »). `make test-services` démarre les trois pour le
créneau du worktree — `deploy/compose/compose.test.yaml`, sous le projet `waterfall-test-s<i>`, aux
images épinglées de la plateforme (PostgreSQL 18 compris), leurs données en mémoire, publiés sur
`127.0.0.1` aux ports 0, 1 et 2 du bloc du créneau — et attend leurs contrôles de santé ; relancée,
elle ne fait rien de plus. `make test-services-down` les retire avec leurs volumes. On ne les lance
pas à la main : `make test-back`, `make coverage-back`, `make test-front` et `make coverage-front`
passent par `slots.py run --services db,redis,storage` (le front : `redis`), `TESTS` compris. Une
fois le créneau lourd pris, s'il y en a un — après l'attente, jamais avant, de sorte que ce qu'on a
retiré entre-temps est redémarré —, l'outil lance `make test-services` pour les services dont la
variable `WATERFALL_TEST_DATABASE_URL`, `WATERFALL_TEST_REDIS_URL` ou `WATERFALL_TEST_STORAGE_URL`
n'est pas posée, et la pose sur leur port ; une variable que l'environnement donne déjà l'emporte,
son service n'est pas démarré, et le travail de la chaîne, qui pose les trois, n'en est pas changé.
`make slot-release` les retire avec la plateforme de service. Deux exécutions lancées ensemble
dans un worktree ne font qu'un `make test-services` à la fois, sous un verrou du créneau
(`waterfall-test-services.<créneau>.lock` du répertoire des verrous du poste) : la seconde attend,
en le disant, puis trouve les services démarrés. Dans un worktree lié sans créneau, ces cibles et
`make e2e-down` échouent en disant `make slot`.

**Les serveurs de l'e2e.** `make e2e`, `make e2e-service` et `make check-front` lancent un faux back
et des fronts (`next-server`) qu'un arrêt brutal peut laisser à l'écoute, un cœur occupé, des
heures durant. `make e2e-down` les arrête pour le créneau du worktree, par leur port et par leur
PID, jamais par leur nom : à lancer dès qu'une de ces cibles s'interrompt, et avant
`make slot-release` (qui l'appelle de toute façon). Elle ne touche pas aux conteneurs, que
`make service-down` et `make slot-release` retirent, ni aux serveurs de `make dev` et de
`make mock` lancés à la main.

**L'essai à N = 4** (EP-19, hors de l'EPIC). La preuve d'EP-19 se joue à N = 2, sur le poste actuel.
Quatre livreurs ensemble ne s'essaient qu'à l'arrivée de la nouvelle machine, et c'est l'auteur qui
les joue ; N reste un nombre qu'il fixe, aucune admission ne le déduit de la mémoire libre. Les
étapes :

1. **Poser N.** `WATERFALL_SLOTS` est une variable de l'environnement du profil de l'utilisateur
   (`export WATERFALL_SLOTS=4` dans `~/.profile` ou `~/.bashrc`), un entier de 1 à 9, et elle se
   lit dans toutes les sessions : celle du pilote, ses livreurs, et les commandes `make` de chacun.
   Ouvrir de nouvelles sessions après le changement ; `make slots` écrit le N qu'elles voient.
2. **Partir à vide.** Aucun conteneur d'un lot précédent (`docker ps`), aucun créneau pris
   (`make slots`), le dépôt principal à jour. Noter la mémoire et les processeurs du poste.
3. **Monter par paliers**, N = 2 puis 3 puis 4, en rejouant à chacun l'étape 4 ; ne passer au palier
   suivant que si le précédent est propre.
4. **Jouer N livreurs ensemble**, sur des lots d'un EPIC sans « Pas avec » entre eux, ou à la main :
   N worktrees, chacun son `make slot`, et dans chacun, ensemble, `make test-back`, puis
   `make coverage-front` et `make e2e` sans `TESTS` — les exécutions lourdes —, enfin
   `make check BASE=origin/epic/EP-nn`. Un `make slot-release` à la fin de chacun.
5. **Mesurer**, à chaque palier :
   - la mémoire du poste au plus haut (`free -m` toutes les dix secondes pendant l'essai) et
     l'usage de l'espace d'échange : c'est elle qui a fait s'effondrer le poste (2026-10-19, 21,
     22) ;
   - la durée de chaque exécution lourde, comparée à celle d'un livreur seul ; la part des
     processeurs, `WATERFALL_PROCESSORS` (le poste divisé par N), est-elle trop étroite, ou trop
     large ?
   - l'attente de l'admission : les exécutions qui disent attendre un créneau lourd, et combien de
     temps ; à N livreurs et N exécutions lourdes admises, elle devrait être courte ;
   - les ports et les noms : `make slots` montre chaque créneau pris par un worktree différent,
     aucun test n'échoue sur un port ou un projet Compose déjà pris (`docker ps` : un projet par
     créneau), et `make slot-release` laisse le créneau sans conteneur ni volume ;
   - les services de test (`tmpfs`) : pas de base ni de Redis partagés entre créneaux, aucune
     collision de données entre deux livreurs ;
   - la file de fusion et le tableau de suivi : aucune ligne du tableau écrasée (`make tracking`),
     aucun conflit que le plan n'avait pas prévu (« Pas avec ») ;
   - le coût des livreurs : le contexte et les tokens par lot, comparés à N = 1.
6. **Relever N, ou le garder.** Garder le N du palier tant qu'aucune de ces mesures ne signale un
   début d'effondrement : mémoire proche de la limite ou échange en cours, durée d'un palier plus
   que multipliée par N, attente d'admission qui s'allonge. Au premier symptôme, redescendre d'un
   cran (`WATERFALL_SLOTS=<N − 1>`) et ouvrir une issue `outil` avec les mesures. N = 4 fixé, le
   pilote lance jusqu'à quatre livreurs ; au-delà, N ne dépasse pas 9, la borne des ports.
7. **Écrire le résultat** dans l'issue de l'essai : le N retenu, les mesures, ce qu'il faudra
   régler (la part des processeurs, le nombre de workers).

## Chaîne

La chaîne est faite de workflows GitHub Actions (`.github/workflows/`) :

- `ci.yml` décide des familles qu'une pull request touche (`make changes`), appelle le
  workflow de chacune, et termine par la **porte** (`gate`), qui juge le tout
  (`make gate`) : elle échoue si un travail a échoué ou a été annulé, et un travail sauté
  parce que sa famille n'est pas touchée n'est pas un échec. La porte est le seul contrôle
  que la protection des branches exige : un contrôle exigé qui ne s'exécute pas faute de
  fichier touché resterait « en attente » et bloquerait la fusion.
- un workflow par famille — `repo.yml`, `spec.yml`, `contract.yml`… —, qui installe ses outils et
  appelle `make check-<famille>`. `repo` s'exécute sur toute modification. Le front en a deux, qui
  tournent côte à côte (#492) : `front.yml`, tout sauf les parcours de bout en bout
  (`make check-front-code`), et `e2e.yml`, les parcours et la mesure du §4.6.2, au palier complet
  seulement (`make e2e`, `make e2e-measure` et `make prerendered-front`, sur le build que le travail
  `front-build` de `ci.yml` a fait, « sur un seul build du front ») ; sur un poste,
  `make check-front` enchaîne les deux moitiés, `check-front-code` puis `check-front-e2e`.
  `front.yml` répartit son travail sur plusieurs runners. L'un tient le client, le lint, les types,
  les catalogues et, au palier rapide, la construction de production (`make check-front-static`).
  Trois jouent les tests unitaires, qui occupent tous les cœurs d'un runner
  (`make check-front-tests`) : les gardes qui lancent ESLint, une minute ou plus chacune, sur l'un
  (`SHARD=lint`, le projet `lint` de `frontend/vitest.config.ts`), les autres tests en deux moitiés
  sur les deux autres (`SHARD=1/2`, `SHARD=2/2`). Vitest répartit des fichiers entiers par
  l'empreinte de leur chemin, et les trois gardes tombaient dans le même morceau. Les gardes ne sont
  jamais mesurées, à aucun palier : elles ne couvrent rien de `src/`, et mesurées elles prenaient
  trois minutes au lieu d'une, le premier test d'une garde épuisant sa minute pendant que les trois
  construisaient à la fois le programme du projet sous la couverture ; chacune le construit
  désormais dans son `beforeAll`, sur un budget à elle (#2015). Vitest y prend un worker par
  processeur moins un, comme il le fait de lui-même hors du mode veille, quatre au plus (`workers`,
  `frontend/vitest.config.ts`, #1474) : le processeur laissé est celui du processus principal, qui
  rassemble les résultats et la couverture des workers ; un runner, quatre processeurs, en joue donc
  trois. Le poste, douze processeurs, ne gagnait rien au-delà de quatre, et chaque test y tournait
  plus lentement, un test de la grille, moins d'une seconde seul, au-delà de ses cinq secondes sous
  la couverture. Sur quatre cœurs du poste, la couverture de la moitié `2/2` prenait 121 s sur
  quatre workers et 131 s sur trois, mais 29 de ses tests dépassaient la seconde sur quatre, 11 sur
  trois. `structure-busy.dom.test.tsx` et `planning-entry.dom.test.tsx` cachent les colonnes qu'ils
  n'éprouvent pas, le Gantt d'abord : la grille entière, rendue deux ou trois fois à chaque geste,
  doublait leur durée. Au palier complet, un dernier runner rassemble la couverture des deux moitiés
  et la tient à ses seuils (`make coverage-front-merge`). ESLint garde son cache, par le contenu de
  chaque fichier (`pnpm lint`, `actions/cache`) : sans lui, il prend une minute. `front-cache.yml`
  écrit ce cache et le magasin de pnpm après chaque fusion, sur la branche dont les pull requests et
  la file de fusion lisent les caches : sans lui, elles ne trouveraient rien.
  `back.yml` répartit de même le back : un runner tient le lint, les types et les frontières du
  cœur (`make check-back-static`), six jouent chacun le sixième des tests, avec leurs services
  (`make check-back-tests`, `SHARD=1/6` à `SHARD=6/6`), et au palier complet un dernier rassemble
  leur couverture et la tient à ses seuils (`make coverage-back-merge`). Un sixième est un test sur
  six dans l'ordre de leur collecte (`--shard`, `backend/tests/conftest.py`), plutôt que des
  fichiers entiers : les fichiers qui chargent le témoin, les plus longs, sont répartis sur les
  six.
  Le témoin n'est chargé par la commande qu'une fois par part, dans une base modèle que copie
  chaque test qui le demande (`backend/tests/witness_template.py`, #4653, « Un test contre
  PostgreSQL ») : les huit parts de 10 à 17 minutes, dont plusieurs figées, sont passées à 6 à
  10 minutes (passages 44945620214, puis 44957647502), puis les six parts de 7 à 14 minutes (passage 44958967745), chacune sous 20 minutes. `keycloak.yml`
  construit l'image de Keycloak et l'éprouve sur la plateforme de service, son royaume appliqué
  (`make check-keycloak`), aux deux paliers : la famille `keycloak` se réveille sur
  `deploy/keycloak/`, sur les fichiers de la plateforme qui la démarrent, sur ses tests, sur tout le
  code du back, dont ses tests servent l'API, et sur le contrat, auquel ils confrontent ses réponses
  (#671) ; en échec, le travail imprime les journaux de Keycloak (`make service-logs`).
  `service.yml` joue les parcours contre le vrai service, au palier complet seulement
  (`make check-service`, soit `make e2e-service`, sur le build du front que partagent les parcours
  d'`e2e.yml`) : la famille `service` se réveille sur le front, le back, le contrat et les fichiers
  de la plateforme. Ils se jouent en quatre morceaux (US-1910), chacun sur son runner et sa
  plateforme (`make check-service SHARD=i/4`), par une matrice dont aucun morceau n'annule les
  autres : les trois premiers se partagent les projets `service` et `shared`, répartis comme ceux
  d'`e2e.yml` par durée mesurée (`wftools.e2eparts`, `tools/e2e-service-durations.json`) ; le
  quatrième joue `shared-serial`, `realm` et `restoration`, qui se jouent un à un après les autres,
  seuls sur sa plateforme, où ils n'attendent plus rien (`E2E_SERVICE_SERIAL`,
  `playwright.config.ts`). La liste d'un morceau nomme le projet de chaque ligne
  (`[service] › service/x.spec.ts`) : un fichier sans son projet ferait jouer à `realm` ses tests
  dans le morceau, et avec eux, sans filtre, chaque projet dont il dépend. Joués entiers sur un
  runner, ils tenaient le chemin critique du palier complet : 22 minutes, dont 5,5 avant le premier
  parcours. Chaque morceau repaie ces 5,5 minutes. Mesuré une fois, sur un passage de la branche
  au palier complet, pas encore de la file (43511917976) : 13,5 minutes de mur pour le passage
  entier ; les morceaux ont pris 8,8, 11,5, 12,0 et 8,2 minutes, soit 40,5 minutes-runner contre
  22, et `back / tests (4/4)`, 11,4 minutes, est désormais au coude à coude. Que `service / paths`
  quitte le chemin critique, et que la médiane de la file tombe à 12 minutes, se constate sur 100
  passages de la file par `make queue-report`, après la fusion ; les 18,5 minutes-runner de plus
  sont le prix du découpage, que l'auteur tranche (le commentaire de `service.yml` cite le
  passage). La plateforme, le front et `playwright test` tournent sur le runner même, par le
  Makefile ; seul le navigateur tourne dans l'image de travail des parcours (ci-dessous), en
  serveur de Playwright (`run-server`), sur le réseau du runner, et `playwright test` s'y connecte
  (`PW_TEST_CONNECT_WS_ENDPOINT`). `E2E_IMAGE=<référence>` le demande à `make e2e-service`, qui
  lance ce serveur par `wftools.e2eimage` (`docker run --network host`, le dépôt monté à son
  propre chemin) : un conteneur de travail ne verrait pas les ports que Docker publie sur le
  runner. Aucun paquet d'Ubuntu ne s'y installe (#2913). Les parcours joués entiers dans l'image
  prenaient 17,3 minutes de `playwright test` en médiane de quatre passages, contre 14,2 en trois
  le navigateur seul dans l'image, la médiane d'avant sur le runner (le commentaire de
  `service.yml` cite les passages). Un téléchargement s'y lit par `download.createReadStream()`,
  jamais par `download.path()`, que Playwright refuse à un navigateur distant. `wftools.e2eimage
  run` est fait pour la chaîne : root dans l'image, la socket de Docker à son chemin d'un runner,
  `DOCKER_HOST` non lu. Sur un poste, sans `E2E_IMAGE`, les parcours se jouent sur le poste, avec
  le navigateur de `make e2e-browsers`. `front-image.yml` construit et démarre l'image de
  production du front, que `images.yml` ne publie qu'après la fusion, aux deux paliers
  (`make check-front-image`) : la famille `front-image` se réveille sur ce qui la fait —
  `frontend/Dockerfile` et son `.dockerignore`, `next.config.ts`, `package.json`, `pnpm-lock.yaml`,
  `pnpm-workspace.yaml`, et ce que son serveur vérifie au démarrage, `src/instrumentation.ts`,
  `src/startup.ts`, `src/session/settings.ts`, `src/api/server.ts` —, et non sur le code du front,
  que la famille `front` construit déjà ; elle coûte une construction d'environ une minute et demie.
  Ce qui est prérendu, c'est le code des pages qui le décide — un `layout.tsx` qui cesserait de lire
  les cookies, une page qui ne lirait aucune valeur de la requête — : la famille `front` l'affirme
  donc elle-même, sans Docker, sur le manifeste de sa propre construction
  (`make prerendered-front`), après `make build-front` au palier rapide et après la construction de
  la mesure au palier complet ; cette construction prérend comme celle de l'image, dont la sortie
  autonome (`WATERFALL_STANDALONE=1`) ne change que l'empaquetage. La famille `front-image` affirme
  que `/` répond avec les réglages du service `front` de `compose.prod.yaml`, des valeurs de
  remplacement pour ses secrets ; que le front, démarré sans l'une des variables dont il ne se passe
  pas, s'arrête en la nommant dans ses journaux (#825) ; que le faux back de la maquette
  (`WATERFALL_AUTH=mock`) est refusé sans `WATERFALL_E2E` — le serveur s'arrête au démarrage, et dit
  pourquoi —, et que `next build` n'a prérendu (`.next/prerender-manifest.json`) que
  `/_global-error` et `/icon.svg` : aucune page qui lirait l'environnement n'est figée à la
  construction.

Hors des pull requests, `images.yml` publie les images (US-0430) : à chaque poussée sur `main` ou
sur une branche `epic/**` — à chaque fusion, que la file a déjà éprouvée —, il construit `front`,
`waterfall` (l'API, le worker, sa planification et les migrations, commandes d'une même
distribution) et `keycloak` (l'extension, les thèmes et le royaume, sans rien de
`deploy/keycloak/development/`), et les pousse sur `ghcr.io/waterfall-project/…`
(`make images PUSH=yes`). Son seul travail demande `packages: write` ; le jeton ne va qu'à la
connexion au registre, et aucune construction ne reçoit d'argument ni de secret (WF-SEC-0010) :
`tools/tests/test_images.py` le garde, avec les déclencheurs et les étiquettes.

- **Les trois d'abord.** Les trois images sont construites avant toute poussée, et rien n'est
  poussé si l'une échoue ; puis toutes les étiquettes du commit, et seulement ensuite celles qui
  bougent — la branche, la version —, pour qu'une étiquette mobile ne désigne jamais des images
  de deux commits.
- **L'étiquette de version est immuable.** Elle ne se pose que depuis `main`, une seule fois, et
  pour les trois images ensemble, qui viennent alors d'un même commit : avant de la poser,
  l'outil demande au registre, image par image, s'il a déjà `<image>:<version>`
  (`docker buildx imagetools inspect`). S'il ne l'a pour aucune, les trois la prennent ; s'il
  l'a pour les trois, aucune ne la reprend, et les étiquettes du commit et de la branche se
  publient seules : une fusion dans `main` qui ne monte pas la version ne la republie donc pas,
  et c'est en montant `version` de `backend/pyproject.toml` (et du front) qu'une publication en
  pose une nouvelle. Tout autre cas — le registre l'a pour certaines seulement, après une
  publication interrompue, ou ne répond pas clairement qu'il ne l'a pas, comme le `403` de ghcr
  pour un paquet absent ou illisible — ne la pose sur aucune : l'outil publie les étiquettes du
  commit et de la branche, puis échoue en nommant chaque image et ce que le registre en a dit ;
  la version se règle alors à la main, ou en la montant. Une branche d'EPIC, qui porte la même
  version, ne la pose jamais ; le label `org.opencontainers.image.version` d'une image qui ne
  prend pas l'étiquette de version le dit (`0.1.0+epic-EP-03` hors de `main`, `0.1.0+main` sur
  `main` une fois la version publiée). Chaque image porte aussi son propre `title` et son `url`,
  qui remplacent ceux de son image de base. Cette immuabilité est tenue par l'outil, non par le
  registre : ghcr.io ne la garantit pas, et laisse réécrire une étiquette à tout jeton qui peut
  écrire les paquets du dépôt — celui d'`images.yml`, mais aussi celui du travail `mirror` d'une
  pull request (plus bas) —, par un code qui n'appellerait pas l'outil (PLC-10). L'épinglage de la
  production par empreinte, qui ne dépendrait plus de l'étiquette, est reporté à EP-13.
- **Ce qui refuse une poussée.** Une branche autre que `main` ou `epic/…` ; un dépôt dont le
  commit n'est pas celui que nomme `IMAGE_COMMIT`, ou qui n'est pas propre dans les contextes des
  images (`git status --porcelain -- frontend backend deploy/keycloak`) ; une image construite
  dont le système de fichiers (`docker export`) contient une valeur de développement connue — la
  marque `development-only`, que portent toutes celles de `deploy/keycloak/development/`, et les
  secrets de poste de `.github/workflows/keycloak.yml`. L'outil nomme alors la valeur trouvée,
  jamais la valeur elle-même. La fouille lit l'archive du conteneur telle quelle : une valeur
  dans un fichier compressé lui échappe.
- **La dernière fusion gagne.** Une publication attend celle de la fusion précédente sur sa
  branche, sans l'annuler ; mais GitHub ne garde qu'une exécution en attente par groupe, et une
  troisième fusion annule celle qui attend : l'étiquette de la branche finit sur la dernière, et
  un commit intermédiaire peut ne pas avoir d'image.
- **La plateforme de production sur les images publiées.** Le travail `trial` d'`images.yml`, après
  la publication, tire du registre les images du commit, par son empreinte, et y joue
  `make production-trial` (`packages: read` pour les tirer) : la plateforme de production démarre,
  s'amorce, et laisse entrer son premier administrateur (WF-ARC-0050). Un échec y dit qu'une image
  publiée ne fait pas une plateforme ; il ne défait pas la publication.

La famille `production` (`production.yml`) fait le même essai avant la fusion, au palier complet
seulement, dans la file : `make check-production` construit les trois images comme `images.yml`,
sans les pousser, puis démarre la plateforme sur elles. Elle se réveille sur les fichiers de la
plateforme de production — `compose.prod.yaml`, `compose.prod.local.yaml`, `Caddyfile.prod`,
`production.env.example` —, sur ceux qu'elle monte de `deploy/compose/`, et sur l'essai lui-même,
`tools/src/wftools/production.py` ; un changement de ce
dont les images sont faites n'est éprouvé ainsi qu'après la fusion, par `images.yml`. Elle coûte la
construction des trois images, celle de Keycloak et de son extension surtout, puis le démarrage de
Keycloak et l'application de son royaume.

La famille `chart` (`chart.yml`, US-2800) éprouve le chart Helm `deploy/helm/waterfall`, qui
déploie la même plateforme sur Kubernetes. Aux deux paliers, `make lint-chart` le lint en mode strict
et `make test-chart` le rend par Helm et tient ses objets contre `compose.prod.yaml` ; au palier
complet seulement, `make check-chart` construit les trois images comme `images.yml`, sans les
pousser, puis installe le chart sur un cluster de kind fait pour l'essai, l'amorce, affirme la sonde
de vie de l'API, que la console de Keycloak et le royaume `master` ne sont pas servis, et laisse
entrer le premier administrateur (`make chart-trial`, `wftools.charttrial`) ; puis, sur un cluster à
lui, met à jour sous charge la version N vers ces images, revient en arrière et remet à jour
(`make chart-upgrade`, `wftools.chartupgrade`, US-2850), à partir de la base de la pull request ou
de la file, que `chart.yml` lui passe (`BASE`). Helm, kind et kubectl
sont téléchargés aux versions et aux empreintes que `wftools.kubetools` épingle.

La famille `migrations` (`migrations.yml`, US-2850, #4089) éprouve les migrations de la branche
contre la dernière version publiée — la plus haute étiquette `vX.Y.Z` que le commit atteint, sans
le chart —, au palier complet seulement, sur un runner à elle : `make migrations-tests` extrait le
back de son étiquette, pose par-dessus les migrations de la branche, écarte ses propres tests de
migrations et joue ses tests sur le schéma ainsi migré (`wftools.migrationtests`) ;
`make migrations-backup` démarre son Compose de production depuis ses images publiées, l'amorce, y
charge son témoin, lui fait prendre une sauvegarde, puis la branche la restaure et la migre, et
affirme qu'aucune ligne n'est perdue et que les lignes de ses révisions marquées — montants et
indicateurs conservés — sont inchangées (`wftools.migrationbackup`,
`backend/tests/test_earlier_backup.py`). Elle ne se réveille qu'aux migrations et à ses propres
outils ; sans version publiée, elle se déclare non exécutée. Les tests de la version se jouent en
trois morceaux (`SHARD=i/N`), chacun sur un runner, et la sauvegarde sur un autre : la porte compte
chaque job de la matrice, comme ceux de l'e2e.

Une incompatibilité déjà trouvée ne bloque pas la file (décision du 2026-11-27, #4961). Chaque
échec attendu de la version N est écrit dans `tools/migrations-known.toml`, sous sa version et sa
partie (`tests` ou `backup`), avec le constat qui le suit (`issue`) ou la catégorie `frozen schema`
— un test de N qui fige son propre schéma : le nom d'une contrainte, un catalogue, un plan d'index —,
et sa cause. Une entrée reconnaît un échec par les tests qu'elle nomme (un nœud de pytest, ou un
fichier entier), par un motif de son message, ou par les deux ; sans tests, elle tient une cause
commune à beaucoup de tests, une même erreur de mise en place. Un greffon de pytest
(`wftools.migrationreport`) écrit l'issue de chaque test, et `wftools.migrationknown` la juge :
la partie échoue sur un échec qu'aucune entrée ne reconnaît, et sur une entrée qui n'échoue plus
— un test nommé qui passe, ou une entrée sans tests qui n'a rien reconnu —, comme un
`xfail(strict=True)` : la liste se vide à mesure que les constats se règlent, et aucune entrée ne
reste masquer la régression du test qu'elle nomme. Le lot qui règle un constat retire ses
entrées ; un test qu'un morceau ne joue pas n'est pas jugé, une entrée sans tests ne l'est que sur
la suite entière (sans `SHARD`), une partie où aucun test n'a passé ni échoué — tous sautés — échoue,
et les entrées d'une autre version ne sont pas jugées, ce que l'outil dit quand N passe à la
suivante. Le motif est cherché dans tout le texte de l'échec, journaux capturés compris, et une
entrée sans `message` reconnaît tout échec de ses tests : l'en-tête du fichier dit ces limites. Les issues des tests
restent dans `.waterfall/migrations-tests.jsonl` et `.waterfall/migrations-backup.jsonl`, et la
chaîne les garde en artefact d'un job en échec : c'est d'elles qu'une entrée s'écrit.

Les familles, les chemins qui les réveillent, les chemins engendrés et ceux des tests sont
déclarés dans `tools/paths.toml`, et nulle part ailleurs. Un chemin de `shared` — le
Makefile, `ci.yml`, la déclaration elle-même et le code qui la lit — réveille toutes les
familles. Le reste des outils réveille les familles qui s'en servent : chacune nomme parmi ses
chemins son workflow, les actions locales qu'il prend et les modules de `wftools` que ses
contrôles lancent. `tools/tests/test_families.py` les tient contre le Makefile, les workflows
et le harnais de Playwright, imports compris : un module lancé par une famille sans la
réveiller fait échouer `make check-repo-tools`. La famille `repo`, qui tourne à chaque modification,
ne tient que les contrôles de quelques secondes (`make check-repo`) ; la famille `tools` teste tous
les outils (`make check-repo-tools`), quand change ce dont ils sont faits ou ce que leurs tests
lisent : une modification de la feuille de route ou d'un guide seule ne la réveille pas.

Deux paliers : le rapide à chaque poussée sur une pull request (`pull_request`), le complet
dans la file de fusion (`merge_group`), sur le résultat de la fusion, avant qu'elle soit
acceptée. Le palier complet ajoute ce qui est lent — la couverture du code, puis les tests de
bout en bout ; sur un poste, `make check-back TIER=full`. Une pull request entre dans la file par
le bouton « Merge when ready », ou par la mutation `enqueuePullRequest` de l'API GraphQL :
`gh pr merge` ne sait pas le faire tant que la fusion automatique est désactivée sur le
dépôt. Une branche sans file de fusion fait tourner le palier complet à la main sur la
branche d'un lot, avant de le fusionner : `gh workflow run chain --ref <branche>`.

**Les constructions périmées de la file.** La file construit une pull request sur une ref à elle,
`gh-readonly-queue/<base>/pr-<N>-<sha>`, et la reconstruit sur un autre sha quand elle retire une
entrée ou se reforme. Le groupe de concurrence de `chain` ne rattrape pas l'ancien passage (la ref
change, et `cancel-in-progress` ne vaut que pour `pull_request`) : le 2026-11-27, des constructions
périmées ont occupé les quelque vingt places du parc, les nouvelles ont attendu, expiré, et la file
les a reconstruites (#5122). Sur un `merge_group` seulement, le job `cancel-stale` de `ci.yml`
(`make queue-cancel`, `wftools.queuecancel`) annule les passages de `chain` en attente (`queued`,
`waiting`, `pending`, `requested`) ou en cours dont la ref est celle d'une construction précédente
de la même pull request dans la file de la même base (même base, même N, autre sha, et un passage
plus ancien que le sien : un plus récent est la construction vivante), et ceux d'une
pull request qui n'est plus dans la file (`mergeQueue(branch:)` de l'API GraphQL ; si la file ne se
lit pas, ou si elle dépasse les cent entrées lues, seules les constructions précédentes de la même
pull request sont annulées ; les passages sont lus avant la file). Il n'annule
jamais un passage d'une autre base, d'un `pull_request`, d'un `workflow_dispatch` ou d'un `push`, ni
le sien, écrit chaque annulation au journal (passage, pull request, ref), n'échoue jamais (un échec de
lecture ou d'annulation devient une annotation `::warning::`), et aucun job ne
l'attend ; il est le seul à porter `actions: write`. **Lire l'état des runners** : compter les jobs
(`gh run view <passage> --json jobs`, ceux `in_progress` et `queued`), pas les passages, car un
passage reste `queued` tant qu'un de ses jobs attend ; un palier complet compte environ 45 jobs.

Les images tierces de Docker Hub — PostgreSQL, Redis, Caddy, Mailpit, Garage, curl, k6, Node, Python,
Debian, Maven, Keycloak et son `keycloak-config-cli` — restent nommées, dans les fichiers Compose et
les `Dockerfile`, comme sur Docker Hub, par leur empreinte : le poste, la production et la démonstration
n'en changent pas. Seule la chaîne les tire d'un miroir, `ghcr.io/waterfall-project/mirror/` :
un pull de Docker Hub (« failed to fetch oauth token », `toomanyrequests`) a fait échouer quatre
passages de la file avant leur premier test (US-1900). Les fichiers lisent le préfixe du miroir dans
`WATERFALL_MIRROR` (`${WATERFALL_MIRROR:-}postgres:18-trixie@sha256:…` en Compose, `ARG
WATERFALL_MIRROR=` avant le `FROM` dans un `Dockerfile`, que `--build-arg WATERFALL_MIRROR` ou
`args: [WATERFALL_MIRROR]` remplit depuis l'environnement) ; vide, c'est Docker Hub. Dependabot ne lit
pas une référence préfixée (`${WATERFALL_MIRROR:-}…`, `FROM ${WATERFALL_MIRROR}…`) : sa veille des
images ne trouvait plus rien depuis le miroir (#3025). Il suit à la place le **manifeste des images**,
`deploy/images/Dockerfile`, qu'aucune construction ne lit : une ligne `FROM <image>:<étiquette>@sha256:…`
sans préfixe par image de Docker Hub que le dépôt épingle (US-2490) : une image, une version dans le
dépôt, le manifeste refuse un chemin nommé deux fois. Un test des outils
(`tools/tests/test_mirror_manifest.py`) échoue quand une référence des `Dockerfile`, des fichiers
Compose ou des workflows, préfixée ou non, n'est pas celle du manifeste, étiquette et empreinte, ou
quand le manifeste porte une image que rien n'emploie. Une montée de Dependabot ne change que le
manifeste, et sa chaîne échoue sur ce test jusqu'aux deux gestes d'une personne, poussés sur la
branche de sa pull request : `make mirror-sync`, qui recopie le manifeste dans les références sans
toucher au préfixe, ancres YAML comprises, puis `make mirror PUSH=yes`, qui copie la nouvelle
empreinte dans le miroir. Le repli sur Docker Hub quand le miroir ne tient pas toutes les empreintes
(#3025) n'est pas fait : la pull request d'une montée attend ces gestes. Les workflows qui
construisent ou lancent Compose (`back.yml`, `keycloak.yml`, `front-image.yml`, `service.yml`,
`production.yml`, `chart.yml`, `images.yml`) posent `WATERFALL_MIRROR: ghcr.io/waterfall-project/mirror/` et s'y
connectent ; les services de `back.yml` et de `front.yml` nomment le miroir en toutes lettres.
Le miroir est tenu par `make mirror PUSH=yes` (`wftools.mirror`) : il lit ces références, demande à
ghcr.io si l'empreinte y est — présente, rien d'autre n'est lu, Docker Hub non plus —, et copie
celles qui manquent de Docker Hub, par empreinte (`docker buildx imagetools create` écrit le
manifeste tel quel, l'empreinte est vérifiée après), sous une étiquette qui porte le début de
l'empreinte : une même étiquette de Docker Hub a pu avoir deux empreintes dans nos fichiers (Caddy,
avant le manifeste). Une copie que ghcr.io refuse (`denied`) est refaite une fois avant d'échouer :
il a refusé une fois la création d'un paquet qu'il a acceptée au passage suivant (#3028). Quand il
refuse de répondre, le message nomme ses deux causes : la connexion à ghcr.io, ou un paquet pas
encore copié (`make mirror PUSH=yes`). Le travail `mirror` de `ci.yml`, que tout travail qui tire
une image attend, le fait à chaque passage, au palier rapide comme au complet : `images.yml` passe
après la fusion, donc après le premier passage qui a besoin d'une image ajoutée ou d'une empreinte
relevée (`images.yml` le refait avant de construire, une consultation). Chaque demande est refaite
quatre fois au plus (`wftools.registry`, #2530) ; une image que ni le miroir ni Docker Hub ne
donnent fait échouer ce travail en nommant Docker Hub, et saute les travaux qui en dépendent, ce que
la porte compte. Pour changer une image tierce : changer sa ligne du manifeste, puis `make
mirror-sync` ; le premier passage copie la nouvelle empreinte. Une image nouvelle prend sa ligne
dans le manifeste, et sa référence dans les fichiers derrière `${WATERFALL_MIRROR:-}`. Les travaux
qui tirent du miroir demandent `packages: read` et s'y connectent (`docker/login-action`, ou
`credentials:` d'un service) : un paquet que GitHub crée est privé, et rien hors de la chaîne ne le
lit. Le travail `mirror`, lui, garde `packages: write`, au palier rapide aussi : il lui faut pour
remplir le miroir avant la fusion, puisque le premier passage qui a besoin d'une image ajoutée ou
d'une empreinte relevée est celui de la pull request qui la change, et que ni la file ni
`images.yml` ne viennent avant. C'est le seul travail d'une pull request qui le garde, et il exécute
le code de la pull request — les outils et leurs dépendances de `tools/uv.lock` — avec un jeton qui
peut écrire tous les paquets du dépôt, images publiées comprises (PLC-10) ; le jeton d'une pull
request venue d'un fork n'a que la lecture. La publication de l'image de travail des parcours, elle,
ne se fait qu'au palier complet (plus bas).

Quatre autres sources réseau de la chaîne, que l'inventaire d'origine d'US-1900 ne nommait pas
(#2981, #3015), sont traitées chacune à sa mesure :

- **le binaire d'actionlint** (GitHub Releases) : `actionlint-py` n'a pas de roue sur PyPI, seulement
  des sources, et sa construction télécharge l'archive du binaire (empreinte vérifiée, quelques essais
  refaits). Il quitte le groupe `dev` des outils pour un groupe `workflows` (`tools/pyproject.toml`) que
  seul `make lint-workflows` installe : `contract / check` et le serveur web de l'e2e ne le construisent
  plus. Le travail `repo / check` le construit, une fois, puis lit la roue construite dans le cache d'uv
  (`setup-uv`) tant que `tools/uv.lock` ne change pas ; sur un cache absent et GitHub Releases muet,
  il échoue en nommant l'adresse (`download failed for https://github.com/rhysd/actionlint/…`) ;
- **la clé du dépôt PGDG** (`www.postgresql.org`) : versionnée dans `backend/pgdg.asc`, copiée dans
  l'image `waterfall` et vérifiée à la construction par son empreinte SHA-256, écrite dans le
  `Dockerfile` avec l'empreinte de la clé. Plus aucun téléchargement de clé. Monter la clé, c'est
  remplacer le fichier et l'empreinte ensemble ; `tools/tests/test_networksources.py` les tient
  l'un à l'autre ;
- **`azure.archive.ubuntu.com`** dans `back / tests` : le job ne lance plus apt. L'image des runners,
  `ubuntu-26.04`, porte déjà `postgresql-client-18` (apt répondait « already the newest version ») ; le
  job le vérifie et, si l'image le retirait un jour, s'arrête en le disant au lieu de l'installer.
  Pas d'image de travail publiée pour cela : elle ne ferait que recopier ce que le runner a ;
- **`deb.debian.org` et `apt.postgresql.org`**, tirés par les images `openldap` et `waterfall` quand le
  cache de couches manque : les `Dockerfile` posent `Acquire::Retries "5"` à apt, et le cache de couches
  que `images.yml` écrit après chaque fusion (`make build-cache`) reste ce qui évite le plus souvent la
  source. Une source qui ne répond toujours pas fait échouer la construction à l'étape d'apt, qui nomme
  l'adresse (`Failed to fetch http://deb.debian.org/…`). Une couche de base publiée sur ghcr.io
  demanderait deux images de plus à étiqueter et à publier, et ferait dépendre la construction du poste
  de ghcr.io : elle n'est pas faite.

Le palier complet vise moins de huit minutes dans la file pour son travail le plus long
(#492). Les parcours de bout en bout, la moitié la plus longue, s'y prennent ainsi :

- **dans l'image de travail des parcours** (`deploy/e2e/Dockerfile`, US-1900), bâtie de l'image de
  Playwright (`mcr.microsoft.com/playwright`) à la version de `@playwright/test` que résout
  `frontend/pnpm-lock.yaml`, épinglée par son empreinte, avec `make`, le Python de
  `tools/.python-version` en `python3`, pnpm à la version de `packageManager` et le client de
  Docker : Chromium et ses paquets système y sont, rien ne vient du miroir d'Ubuntu, dont le débit
  et la réponse ne sont pas les nôtres (#472, #2913). Elle est construite pour amd64 seulement,
  l'architecture des runners et des postes. Elle est publiée sur `ghcr.io/waterfall-project/e2e`,
  étiquetée par l'empreinte de son répertoire, et demandée au registre (`make e2e-image`), dès
  qu'`e2e` ou `service` peuvent tourner, à côté de `front-build`, par l'un de deux travaux de
  `ci.yml`, un par palier (US-2490). Au palier rapide, `e2e-image` n'a que `packages: read` :
  présente, il la trouve ; absente, il la construit sans la publier, pour qu'une construction qui
  échoue arrête la pull request avant la file. Au palier complet — la file, ou le palier complet
  lancé à la main sur une branche, jamais une pull request —, `e2e-image-publish` en donne la
  référence par l'empreinte que le registre lui connaît, que les morceaux (`container:` d'`e2e.yml`)
  et `service.yml` tirent ; absente, il la construit et la publie (`PUSH=yes`), une fois, au premier
  passage qui en a besoin, d'où ses `packages: write`. `e2e` et `service`, tous deux du palier
  complet, ne nomment que lui. `images.yml` ne la publie pas : il passe après la fusion, donc après
  le premier passage de la file qui en a besoin.

  Chaque demande au registre, la construction et la publication se refont quatre fois au plus,
  à vingt secondes d'intervalle (#2530) ; une construction refaite repart des couches déjà
  construites. Un registre qui ne répond toujours pas fait échouer l'un ou l'autre travail en le
  nommant, et saute les parcours, ce que la porte compte ; une image qui ne se tire pas fait échouer
  l'initialisation du morceau, en nommant le registre, avant toute étape. Deux passages de la
  file qui ne trouvent pas l'étiquette peuvent la publier chacun : la construction n'est pas
  reproductible à l'octet, mais chacun tire l'image qu'il a publiée, par son empreinte, et le
  contenu que nomme l'étiquette est le même.

  `tools/tests/test_e2eimage.py` tient les versions de l'image, ses sources épinglées,
  l'absence de paquet d'Ubuntu dans `ci.yml`, `e2e.yml` et `service.yml`, et les droits des deux
  travaux ; `tools/tests/test_gate.py`, que la porte attend chaque travail de `ci.yml`.

  Le travail appelle `make e2e`, qui trouve le navigateur de
  l'image (`PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`), et non `make check-front-e2e`, qui en
  installerait un. Monter `@playwright/test` monte l'image avec lui, étiquette et empreinte : sinon
  les parcours s'arrêtent d'emblée sur un navigateur introuvable, et
  `tools/tests/test_playwrightimage.py` échoue avant eux, dans `make check-repo-tools`. L'empreinte est
  celle de l'index multi-architecture de l'étiquette, que donne la ligne `Digest:` de
  `docker buildx imagetools inspect mcr.microsoft.com/playwright:v<X>-noble`, ou l'en-tête
  `docker-content-digest` de
  `curl -sI -H 'Accept: application/vnd.oci.image.index.v1+json' https://mcr.microsoft.com/v2/playwright/manifests/v<X>-noble`.
  Le paquet `make` d'Ubuntu noble, l'archive du client de Docker et celles de pnpm et de son
  binaire ne se téléchargent qu'à la construction de l'image, épinglés et vérifiés par leur
  empreinte, le Python par sa version, que uv vérifie par l'empreinte qu'il en porte ;
- **répartis sur cinq runners** (`make e2e SHARD=i/5`), la mesure du §4.6.2 sur un sixième,
  seule (`make e2e-measure`), par une matrice dont aucun morceau n'annule les autres ; le résultat
  d'`e2e` est un échec dès qu'un morceau échoue ou est annulé, et la porte avec lui. `--shard`
  de Playwright répartit des fichiers entiers, à nombre de tests égal, et les plus longs pèsent :
  le quatrième de cinq jouait environ 260 s de parcours, les autres environ 150 s. Les morceaux
  sont donc pesés par durée mesurée (`wftools.e2eparts`, US-1910) : `make e2e SHARD=i/N` liste les
  tests (`playwright test --list`), les répartit — le plus long d'abord, dans le morceau le moins
  chargé — et ne joue que ceux du sien (`--test-list`). L'unité est le fichier, ou le test pour un
  fichier joué test par test (`mode: "parallel"`), comme `accessibility.spec.ts` et
  `grid-frame.spec.ts` ; les secondes de chaque unité sont gardées dans `tools/e2e-durations.json`.
  Comme la liste vient de Playwright et non du fichier des durées, aucun test n'est perdu ni joué
  deux fois, et une unité que le fichier ignore pèse la moyenne des unités connues de son genre.
  Chaque morceau paie environ 75 s d'image, d'installation et de serveurs (#2015). Le fichier des
  durées se rafraîchit, quand les parcours changent, depuis le journal d'un passage réel
  (`make e2e-durations LOG=<fichier>` : le journal du job d'un morceau, ou la sortie de
  `make e2e-service`, dont les durées vont dans `tools/e2e-service-durations.json`, ou celle de
  `make e2e`, au rapporteur `list` ; l'entrée standard sans `LOG`, par exemple
  `gh run view <passage> --log --job <job> | make e2e-durations`, les journaux des cinq morceaux
  mis bout à bout) ; un journal qui ferait disparaître des unités connues est refusé, sauf
  `python -m wftools.e2eparts refresh --drop`. Une liste que la ligne `Total: N tests` de Playwright
  ne confirme pas, ou un morceau vide, fait échouer le morceau au lieu de ne rien jouer ;
- **sur un seul build du front par exécution** (US-0590) : le travail `front-build` de `ci.yml`,
  qui tourne dès qu'`e2e` ou `service` tourne, lance `make build-front` et téléverse
  `frontend/.next` sans son cache (`.next/cache`, que seul un build suivant lirait). Les cinq
  morceaux, la mesure et les parcours du service l'attendent, le téléchargent là où le build l'a
  écrit et jouent avec `E2E_BUILT=1`, sans rien reconstruire. Il vit dans `ci.yml` et non dans
  l'un des deux workflows : `e2e.yml` et `service.yml` sont deux workflows appelés, et un `needs`
  ne joint pas les travaux de l'un à ceux de l'autre ; ni l'un ni l'autre n'a d'autre
  déclencheur que cet appel, si bien qu'aucun ne construit le front. Un build en échec saute les
  deux, et la porte, qui l'attend aussi, échoue. Il construit sur le runner, comme `front.yml`, en
  Node 26 : les morceaux le démarrent dans l'image de travail des parcours, bâtie de celle de
  Playwright, en Node 24 (son
  `NODE_VERSION`, que le lot de Node 26 ne change pas ; `next start` y exécute les fichiers
  construits, et Next 16 accepte Node 24, tandis que pnpm 12 ne s'arrête pas sur `engines` sans
  `engine-strict`, que le front ne pose pas), sur la même Ubuntu noble en amd64, et à un autre
  chemin de l'espace de travail (`/__w/…` au lieu de `/home/runner/work/…`) ; `service.yml`, sur le
  runner. Le build ne dépend pas de ce chemin : seul `required-server-files.json`, que lit la
  sortie autonome de l'image et non `next start`, le nomme, et un build déplacé ailleurs, son
  dossier d'origine retiré, sert ses pages (vérifié le 2026-10-25 sur le poste, en déplaçant le
  build ; la preuve dans la chaîne viendra d'une exécution de `chain` sur la branche du lot).

Le back suit le même modèle (#492, levier 5) :

- PostgreSQL tourne en service du travail (`services:` de `back.yml`), dans l'image de la
  version que vise la plateforme — celle de `compose.service.yaml` —, épinglée par son
  empreinte, avec sa sonde de santé : les tests d'intégration le joignent sur `localhost`, sans
  Compose, par `WATERFALL_TEST_DATABASE_URL` ; l'empreinte est écrite dans `back.yml` et dans
  `compose.service.yaml`, et `tests/test_platform_images.py` échoue si elles divergent ;
- la couverture, plus lente, ne tourne qu'au palier complet, à la place des tests simples
  (`full-else` du Makefile) ;
- les tests se répartissent sur les cœurs du runner, huit processus au plus (`PYTEST_WORKERS`
  du Makefile, pytest-xdist) : 7 minutes en série sur la chaîne en octobre 2026, moins de deux
  sur quatre cœurs. Chaque processus crée sa propre base, son rôle et son bucket, de nom unique,
  et prend la base de Redis qui suit celle de `WATERFALL_TEST_REDIS_URL` selon son rang
  (`tests/conftest.py`). Les processus doivent collecter les mêmes tests : un paramètre de test
  n'est jamais tiré au hasard (un `uuid4()` dans `parametrize`), il est fixé. Les tests de
  Keycloak restent sur un processus : l'un d'eux redémarre Keycloak.

Les images se construisent depuis un cache de GitHub Actions (`type=gha`) : l'extension de
Keycloak compilée par Maven, les dépendances du front et du back ne se refont pas à chaque
travail. Le job `cache` d'`images.yml` l'écrit après chaque fusion (`make build-cache`), sur la
branche dont les pull requests lisent les caches ; `keycloak.yml`, `service.yml`,
`production.yml`, `chart.yml` et `front-image.yml` le lisent (`build-keycloak`, `wftools.images`,
`wftools.frontimage`). L'action locale `.github/actions/build-cache` le leur ouvre : elle active
le magasin d'images de containerd, sans lequel le builder de Docker n'importe ni n'exporte un tel
cache, et redémarre Docker — jamais dans un travail qui a des `services:`
(`tools/tests/test_images.py`) ; puis elle passe aux étapes suivantes l'adresse et le jeton du
cache, que le runner ne donne qu'à une action (`.github/actions/actions-runtime`, sans rien
afficher). Sur un poste, Docker ignore un cache `type=gha`. La publication (`publish`) n'en lit
aucun : sur le magasin de containerd, une image se pousserait avec ses attestations, dans un
autre format que celui publié aujourd'hui.

Règles des workflows :

- une action tierce est épinglée par l'empreinte de son commit, la version en commentaire ;
  Dependabot propose chaque mois leur mise à jour (`.github/dependabot.yml`) ;
- chaque workflow déclare `permissions: contents: read`, et n'en demande pas plus sans
  raison écrite ;
- `actions/checkout` ne garde pas le jeton (`persist-credentials: false`) ;
- un outil téléchargé hors d'une action est épinglé par sa version et vérifié par son
  empreinte, comme pandoc dans `spec.yml`.
- Dependabot propose chaque mois, par une pull request par écosystème, les mises à jour de
  ce qu'il suit : les Actions — celles des workflows et celles des actions locales,
  `.github/actions/*` —, uv (`/backend`, `/tools`), npm (`/frontend`), Maven (l'extension de
  Keycloak) et les images de Docker Hub par leur manifeste, `deploy/images` (plus haut) — avec
  `deploy/e2e`, l'image de travail des parcours, qui n'a pas de préfixe — ; les mineures et les
  correctifs d'un écosystème arrivent groupés, chaque majeure dans la sienne, sous le préfixe
  `Chaîne :`. Les dépendances `org.keycloak` et `jakarta.ws.rs-api` de l'extension sont
  ignorées : elles suivent l'image de Keycloak. La majeure de TypeScript n'a pas de règle
  d'ignorance : l'auteur ferme sa pull request tant que `typescript-eslint` ne la tient pas.
- Dependabot ne suit pas, et l'auteur relève à la main, à la pull request mensuelle de
  Dependabot : une action ou une image épinglée dans un répertoire qu'aucune entrée de
  `.github/dependabot.yml` ne nomme (un test des outils tient que ceux des actions et de
  `deploy/e2e` le sont, et qu'une action a la même empreinte partout), `packageManager` du
  front, l'uv et le client PostgreSQL de l'image `waterfall`
  (et sa clé, `backend/pgdg.asc`), les runners et le pandoc de la chaîne, et
  `maven.compiler.release` du `pom.xml` de l'extension,
  qui reste à 21 exprès (le Java de l'image de Keycloak, pas le JDK de construction) : il se
  relève quand cette image change de Java.
- Un parcours de bout en bout ou de service qui échoue verse ce que Playwright a gardé
  (`frontend/test-results/` : traces, captures, `error-context.md`) en artefact, sur échec
  seulement, pour sept jours, sous le nom `test-results-e2e-<n>` ou `test-results-service-<n>`
  (`<n>` est l'indice de la part).

_Contrôle_ : `make lint-workflows` (actionlint) ; l'épinglage et les permissions, la revue.

La protection des branches est un réglage de GitHub, fait par le propriétaire du dépôt :
sur `epic/*`, pas de poussée directe, la porte exigée, la file de fusion ; sur `main`, la
porte n'est exigée qu'à partir de la livraison d'EP-01 — GitHub lit les workflows dans la
branche d'une pull request, et une pull request vers `main` tirée d'avant la chaîne ne la
déclencherait pas.

## Nommage

Le code, les tables, les colonnes, les variables, les chemins et les messages de console
sont en anglais ; la documentation est en français, comme la spécification. Les noms des
objets du domaine sont ceux du tableau de correspondance du §4.4.1 de la spécification
(`estimate_line`, `cost_line`, `revision`…), et les conventions du contrat — `snake_case`,
`operationId` en `camelCase`, identifiants UUID — sont dans `docs/api/README-fr.md`.

_Contrôle_ : aucun outil ne vérifie la langue d'un nom ; la revue le fait.

## En-têtes et licences

Chaque fichier de code commence par deux lignes, après la ligne `#!` s'il en a une :

<!-- REUSE-IgnoreStart -->

```text
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only
```

<!-- REUSE-IgnoreEnd -->

dans la syntaxe de commentaire du langage. Le nom du fichier n'y figure pas : il deviendrait
faux au premier renommage ; la première ligne de la docstring du module dit à quoi il sert.
Ce qui ne peut pas porter de commentaire, ou n'y gagnerait rien — documentation, figures,
contrat, gabarits, images, fichiers engendrés — est déclaré dans `REUSE.toml`. La
spécification y est déclarée sous CC BY-SA 4.0 et le contrat d'interface sous Apache-2.0
(`docs/legal/README-fr.md`, « Les décisions prises ») ; le code de conduite garde sa propre
licence, CC BY 4.0.

Un document qui cite ces deux lignes, comme celui-ci, les encadre de
`REUSE-IgnoreStart` et `REUSE-IgnoreEnd`, faute de quoi l'outil les lirait comme la licence
du document.

_Contrôle_ : `make reuse` échoue sur un fichier couvert ni par un en-tête ni par
`REUSE.toml`.

## Outils du dépôt

Les outils vivent dans `tools/`, en Python, avec leurs tests (`make test-tools`, qui exige Docker :
le test du Compose de service lance `docker compose config` et échoue sans lui). Il tourne sous un
plafond de mémoire, `TOOLS_MEMORY` (24G par défaut) : sous systemd utilisateur, le noyau tue le run
qui le dépasse, non la session ; sans systemd utilisateur (un runner de la chaîne), il n'y a pas de
plafond. Les tests de l'entrypoint de l'annuaire, qui démarrent son image sur des volumes jetables,
en sont écartés (marqueur `openldap`) : `make test-openldap` les lance, et la famille `keycloak`,
que `deploy/openldap` réveille, les éprouve. Tout outil qui a besoin des exigences les lit par
`wftools.projection`, qui lit la projection `docs/spec/waterfall-spec.md` : un seul lecteur, pour
que deux outils ne puissent pas diverger sur ce qu'une exigence dit. Il compare les textes après
normalisation — apostrophes et espaces typographiques rendus simples —, et découpe un Vérif en
phrases. L'exemple du §1.3.1, `WF-EXA-0010-A`, n'est pas une exigence du produit : les outils
l'excluent.

Le garde des commandes des agents (`tools/src/wftools/guard.py`, avec `guardgit.py` et
`guardoptions.py`, lancé par le hook `PreToolUse` de `.claude/settings.json`) refuse les formes
que dit [`agents.md`](agents.md), « Un agent n'arrête que ce qu'il a lancé ». Il lit le texte de
la commande, non ce que le shell en calcule. Ses limites connues, qu'il ne code pas (US-2450) :

- une cible calculée : `rm -rf $(git rev-parse --git-dir)`, `find "$GIT" | xargs rm`, ou une liste
  écrite dans un fichier puis relue, `find .git … > liste; xargs rm < liste` ;
- le script de `xargs sh -c`, dont les arguments viennent du tube ;
- après un `cd .git`, il ne garde que les verrous : `cd .git && rm -rf *` passe ;
- le texte lu par un autre interpréteur, ou encodé : `source /dev/stdin`, `. /dev/stdin`,
  `while read l; do eval "$l"`, `python <<EOF` qui appelle `os.system`, `uvx` et `uv tool run`,
  les shells hors de la liste (`fish`…), le texte obscurci (`printf '\x70kill'`, `base64 | bash`) ;
- `bash /dev/stdin` et `bash /dev/fd/0` : l'opérande est pris pour un script, et l'entrée fournie
  n'est pas jugée (`echo 'pkill x' | bash /dev/stdin` passe) (US-2500) ;
- les écritures destructrices autres que `rm`, `mv`, `truncate` et `find` : `shred`,
  `rsync --delete`, `cp /dev/null .git/index`, `: > .git/index`, `ln -sf x .git` ;
- un événement qu'il ne sait pas lire — JSON illisible, entrée vide, sans `command` — sort en
  code 0, et la commande passe sans être jugée ; le hook n'a pas de `timeout` ;
- `gh api graphql` est permis plus largement que la seule mise en file : décision consignée, et
  maintenue le 2026-11-16 ([`agents.md`](agents.md), « La mise en file »).

_Contrôle_ : `make test-tools`.

## La roadmap et les exigences

Les US de `docs/roadmap` citent les exigences qu'elles réalisent, et leurs critères
d'acceptation reprennent le Vérif de chacune **mot pour mot**, en critère ou en écart : ce
sont les cas de test à venir. `make roadmap` confronte la roadmap au document, et échoue :

- sur un identifiant inconnu, ou d'un indice de révision que le document a dépassé, dans un
  tableau d'EPIC comme dans une US ;
- sur une phrase du Vérif d'une exigence citée, absente de l'US ou tronquée — une phrase se
  cite entière, point final compris ; les apostrophes et les espaces typographiques ne
  comptent pas ;
- sur une exigence du tableau d'un EPIC qu'aucune de ses US ne cite, sauf si l'EPIC est
  `à planifier` ;
- sur une exigence qu'aucun EPIC ne close, ou que plusieurs closent.

Il liste, sans échouer, les exigences F0 qu'aucune US ne cite encore : leur nombre décroît à
mesure que les US des EPIC suivants s'écrivent. L'outil ne lit que le dépôt : l'état des
issues n'est pas son affaire.

Il échoue aussi sur une commande `make` que cite un agent (`.claude/agents/`,
`docs/dev/agents.md`, `.claude/skills/`, dont le skill `pilote`) et que le Makefile n'a pas : une
cible renommée ne laisse pas un agent appeler une commande disparue.

_Contrôle_ : `make roadmap`, famille `roadmap` de la chaîne, réveillée aussi par un
changement de la projection, des agents ou d'un skill.

## Commentaires

Un commentaire dit pourquoi, pas ce que fait le code : la raison d'un choix, un invariant,
un cas limite. Il est en anglais, comme le code.

_Contrôle_ : aucun outil ne juge ce qu'un commentaire dit ; la revue le fait. La forme des
docstrings, le code commenté et les `TODO` — toujours `TODO(#12): …`, avec le numéro de
l'issue — sont contrôlés : voir « Lint, typage et format ».

## Lint, typage et format

Ce que la spécification appelle analyse statique (WF-QUA-0030) : tout est bloquant, et aucun
avertissement n'est toléré ; ce qui ne mérite pas de bloquer se retire du jeu de règles.

**Python** — le back et les outils du dépôt partagent un seul jeu de règles,
`ruff.toml`, à la racine :

- toutes les règles de Ruff sont actives ; celles qui sont retirées sont listées, chacune
  avec sa raison, et l'historique du fichier montre chaque retrait ;
- complexité cyclomatique inférieure à 15 par fonction (`C901`, maximum 14) ;
- l'en-tête SPDX (`CPY001`), une docstring d'une ligne pour ce qui est public (`D1`,
  convention PEP 257 ; ni les tests ni les méthodes spéciales n'en demandent), pas de code
  commenté (`ERA001`), un `TODO` qui cite son issue (`TD003`) ;
- Pyright en mode strict (`[tool.pyright]` de chaque projet), `# type: ignore` non honoré.

**Aucune règle ne s'écarte par un commentaire dans le code.** Une exception, s'il en faut
une, s'écrit dans la configuration de l'outil — `per-file-ignores` de `ruff.toml` —, avec sa
raison. Aucun fichier source ne dépasse 1 000 lignes, lignes vides et commentaires compris ;
les fichiers engendrés en sont exclus.

_Contrôles_ : `make lint-back`, `make typecheck-back`, `make lint-tools`,
`make typecheck-tools` ; `make sources` pour les commentaires d'exemption — ceux de flake8, de
Ruff, d'isort, de couverture (`pragma`, avec ou sans deux-points, `no cover` et `no branch`) et,
dans un `Dockerfile` ou un `*.Dockerfile`, de hadolint — et la taille des fichiers, sur tout le
dépôt. Les outils de `docs/spec/tools` et `docs/api/tools` suivent
les mêmes règles que ceux de `tools/` ; une exception, s'il en faut une, se déclare dans
`tools/paths.toml`, avec sa raison et ce qui la lèvera.

**TypeScript** — le front a son jeu de règles dans `frontend/eslint.config.mjs` :

- les configurations recommandées d'ESLint, de Next.js (`core-web-vitals`) et de
  typescript-eslint en mode strict, avec les informations de type ; ce qui leur est ajouté
  ou retiré est écrit dans le fichier, avec sa raison ;
- complexité cyclomatique inférieure à 15 (`complexity`, maximum 14) ; 1 000 lignes au plus
  par fichier (`max-lines`) ;
- une docstring JSDoc pour ce qui est exporté, sans type — TypeScript les porte
  (`jsdoc/no-types`) — et sans section par paramètre, qui répéterait la signature ;
- aucun des moyens connus d'appeler le réseau hors de `src/api/client.ts` — `fetch`,
  `XMLHttpRequest`, `WebSocket`, `EventSource`, ni un client http importé —, et aucun
  import de `src/api/` dans un composant client hors des actions serveur : l'API ne
  s'appelle que par le client engendré, depuis le serveur
  (WF-ARC-0020) ;
- aucun texte destiné à l'utilisateur écrit dans le code (WF-QUA-0070) : voir « Clés de
  traduction » ;
- Prettier pour le format (`frontend/.prettierrc.json`) ; ESLint s'exécute avec
  `--max-warnings 0`.

Les commentaires de configuration dans le code ne sont pas honorés (`noInlineConfig`) et
`make sources` les refuse. Un `TODO` cite son issue, sous la même forme qu'en Python :
`TODO(#12): …` ; les autres étiquettes d'attente sont refusées — c'est `make sources` qui le
vérifie, ESLint n'ayant pas d'équivalent aux règles `TD` et `FIX` de Ruff.

_Contrôles_ : `make lint-front` (ESLint, Prettier), `make typecheck-front`, `make sources`.

**Contrat** — `docs/api/redocly.yaml` étend `recommended-strict` : toute règle de Redocly
bloque. Une opération à laquelle une règle ne s'applique pas — une sonde sans réponse 4xx,
une redirection OIDC sans réponse 2xx — est déclarée dans `docs/api/.redocly.lint-ignore.yaml`,
avec sa raison.

_Contrôle_ : `make lint-openapi`.

## Règles de codage

Comment s'écrit chaque langage : [Python](python.md), pour le back et les outils,
[TypeScript](typescript.md), pour le front, et [Java](java.md), pour l'extension Keycloak.
Chacun nomme d'abord les jeux de règles des outils, par renvoi, puis les règles de conception
qu'aucun outil ne contrôle, chacune avec sa raison, et finit par les défauts déjà rencontrés,
que la revue cherche nommément. Le
SQL et les migrations ont le leur : [SQL](sql.md), pour les tables, les types, les contraintes,
les migrations et les verrous.

## Tests

- **Un test qui cite son exigence** — voir ci-dessous.
- **Un test qui reprend un exemple chiffré** — voir ci-dessous.
- **Un parcours de bout en bout** — voir ci-dessous.
- **Un test contre PostgreSQL** — voir ci-dessous.
- **Un test contre Redis** — voir ci-dessous.
- **Un test contre le stockage objet** — voir ci-dessous.

Les réponses du faux back sont les exemples du contrat, tels quels. Deux exceptions, et seulement
elles. Un test peut retirer une permission d'une session d'exemple pour éprouver une combinaison
qu'aucun compte du témoin ne porte (décision de l'auteur, 2026-10-09) ; il n'ajoute ni ne réécrit
rien d'autre. Il la retire de la session que lit la page (`requestSession` doublé, comme le fait
L43c pour les sauvegardes, `app/reference/costs/page.test.tsx`), jamais en réécrivant une réponse du
client. Et un test peut rendre un composant sur une variante contrefactuelle d'une ligne d'exemple —
une valeur changée, le reste de la ligne gardé —, quand aucun exemple du contrat ne porte le cas
qu'il éprouve : la variante se passe en prop au composant, jamais servie comme réponse du client, et
le test dit de quel exemple elle vient et ce qu'il change (EP-14/L45a). Précédents : « SP-REC », le
sous-projet créé, qu'aucune révision marquée ne cite, déchargé de ses coûts réels, sa suppression
listée disponible comme le serveur la listerait alors, pour la suppression d'un sous-projet, les
deux du témoin étant cités et chargés (EP-14/L42l) ; les commandes des sous-projets ôtées d'une
ligne (EP-14/L44e, `subproject-commands.dom.test.tsx`) — celles d'un projet clos, aucune depuis
US-0702/L3, ont leur exemple depuis L42o (`subprojects_completed`), qui remplace la variante
(EP-14/L52) — ; et l'écart à la revue précédente absent du reste à engager
(`remaining-summary.test.tsx`).

### Un test qui cite son exigence

Chaque exigence F0 est couverte par au moins un test qui la cite par son identifiant complet,
indice de révision compris (WF-QUA-0010).

- **Python** : le marqueur `@pytest.mark.requirement("WF-ARC-0010-A")`, sur le test, sur sa
  classe, ou sur le module (`pytestmark = pytest.mark.requirement(...)`) quand tout le
  fichier porte la même exigence. Le marqueur est déclaré : une faute de frappe dans son nom
  fait échouer Pytest.
- **TypeScript** — Vitest ou Playwright : l'identifiant entre crochets dans le titre,
  `it("lit une grille [WF-QUA-0050-A]", …)`.

Un test cite l'exigence dont il éprouve le Vérif, pas celle dont il parle. Un test qui ne
couvre aucune exigence — un outil, un détail de réalisation — n'en cite aucune.

**Un critère propre à une US** — qu'aucune exigence ne porte, parce que le Vérif de l'exigence
voisine n'est pas ce que le test éprouve — se cite par l'US : `[US-2160]` dans le titre d'un test
TypeScript, `@pytest.mark.story("US-2160")` en Python (marque déclarée dans `backend/pyproject.toml`
et `tools/pyproject.toml`). Le relevé range ces citations à part, « Critères propres aux US », hors
du compte des exigences, et échoue sur une US qu'aucun fichier de `docs/roadmap` ne porte, comme sur
un identifiant d'exigence inconnu.

**Un test non exécuté** ne couvre rien, et le relevé le sait sans lancer les tests, à ce que le test
déclare : en TypeScript, un `.skip`, `.fixme` ou `.todo`, ou un appel sous un `describe.skip` ou un
`describe.fixme` ; en Python, la marque `@pytest.mark.unexecuted("<raison>")`, sur le test, sa
classe (`pytestmark` compris) ou son module, qu'un test qui peut se sauter — faute du XSD MSPDI,
d'un service — porte, et qu'un crochet des `conftest.py` rend obligatoire : un test qui se saute
sans la porter échoue. Le relevé liste ses citations sous leur exigence, « non exécuté », sans les
compter : une exigence que seuls des tests non exécutés citent est non couverte, et `make
requirements-release` la nomme. Un `test.skip(` ou `test.fixme(` sans titre, appelé dans le corps
d'un test (dans le groupe, à défaut), laisse le test exécuté quand son premier argument est
`inService` ou `!inService`, et le sort « non exécuté » pour tout autre (`true`, `!inService ||
manager === undefined`…), comme un test qui porte les deux formes ; `it.skipIf(` et `it.runIf(` ne
sont pas vus : le test compte comme exécuté. Une citation dans un commentaire n'est pas une citation
: seuls les titres des `it(` et `test(` sont lus, et une forme d'appel que le relevé ne connaît pas
le fait échouer en nommant le fichier et la ligne.

_Contrôles_ : `make requirements` lit les citations dans les fichiers de test, sans les lancer, et
publie le relevé — chaque exigence F0 avec les tests qui la couvrent et leur famille, celle que
`tools/paths.toml` déclare pour leur chemin dans sa table `[tests]` : bout en bout contre le service
(`frontend/e2e/service/**`, qui prime sur les autres parcours), bout en bout (`frontend/e2e/**`, qui
prime sur le reste de `frontend/`), front, back, keycloak (les tests JUnit de l'extension, qui ne
citent aucune exigence), outils — dans le résumé du travail de la chaîne ; une citation d'un
identifiant inconnu, ou d'un indice de révision que le document a dépassé, le fait échouer. Les
tests du front citent des exigences que d'autres EPIC clôturent, par la phrase du Vérif qu'ils
éprouvent ; une exigence que seuls le front et le bout en bout citent, et qu'un EPIC clôt sans avoir
`front` pour seule famille — d'après la table « Exigences réalisées » de la roadmap et le champ
`famille` de son front matter —, est comptée à part, « couverte par le front seul », et ne compte
pas comme couverte. Un parcours joué contre le service, lui, traverse le back : il prouve ce que le
back clôt, comme ses propres tests (US-0340). `make requirements-release` échoue en plus sur toute
exigence F0 non couverte, ou couverte par le front seul, en la nommant : c'est la commande de la
publication d'une version. Une exigence dont le Vérif s'ouvre par « Vérifiée en recette » attend un
procès-verbal, dont la forme n'est pas encore définie : le relevé le dit.

### Un test contre PostgreSQL

Un test d'intégration du back joint la vraie base, PostgreSQL, jamais une autre à sa place
(`python.md`, « Les tests »). La variable `WATERFALL_TEST_DATABASE_URL` désigne un serveur et un
rôle qui peut créer des bases et des rôles, un superutilisateur
(`postgresql://rôle@hôte:5432/postgres`) : à chaque session de tests, c'est-à-dire pour chaque
processus, la fixture `process_database_url` (`backend/tests/conftest.py`) y crée une base de nom
unique, y applique les migrations, et la supprime à la fin, avec le rôle du service que les
migrations lui ont créé. `database_url` et `service_database_url` désignent la base du test : celle
du processus, sauf pour un test sur le témoin. La fixture `database` rend cette base telle que le
service la voit — par un rôle de connexion membre du rôle du service de cette base, créé pour la
session (sql.md, « Le rôle du service ») —, et en supprime après chaque test les lignes de toutes
les tables que la `Base` déclare, en propriétaire, journal d'audit compris, que son déclencheur ne
protège pas d'un superutilisateur qui coupe les déclencheurs — sauf celles qu'une migration écrit,
le catalogue des permissions, que sa table marque (`WRITTEN_BY_MIGRATION` dans son `info`) —,
puis récrit aux valeurs livrées la ligne unique qu'une migration écrit et que le service change,
une planification, que sa table donne (`SHIPPED_ROW` dans son `info`, `empty_database` de
`tests/project_rows.py`) ; `session` rend une session que le test défait.

Le témoin se charge une fois par exécution, par un processus à lui, dans une base modèle
(`backend/tests/witness_template.py`, #4653) : le premier processus dont les tests le demandent
lance ce chargement dès leur collecte, et ces tests passent après les autres, le temps qu'il se
fasse. Un test sur le témoin (`witness`, `witness_logged`) reçoit une base à lui, copie du modèle
(`CREATE DATABASE … TEMPLATE`, 0,2 à 0,4 s pour la créer, 0,1 s pour la supprimer, mesurées sur un poste), supprimée après lui : lignes,
identifiants, partitions des projets et séquences sont ceux que la commande a écrits, et aucune
ligne n'est reposée ni aucune partition supprimée. Le service y entre par un rôle de connexion
membre du rôle du service du modèle, dont la copie garde les droits. Le témoin chargé par chaque
processus, puis reposé et ses partitions supprimées autour de chaque test (#2157), prenait le
tiers du temps des tests. Un test qui change la façon dont la commande le charge le charge
lui-même, sur la base du processus (`witness_loaded`).

Un test qui se fige échoue au bout de huit minutes, nommé, sa trace là où il s'est arrêté
(`pytest-timeout`, `timeout` de `backend/pyproject.toml`, par `SIGALRM`) : son processus passe au
suivant, au lieu de figer sa part de la chaîne jusqu'à l'annulation du travail (#4653). Le plus
long test qui ne se fige pas charge le témoin lui-même : 216 secondes au plus sur un runner
(passage 44957647502), et un runner est jusqu'à deux fois plus lent qu'un autre. Le chargement du
modèle a son échéance, sept minutes (`LOADING_TIMEOUT`, pour 134 à 290 secondes mesurées), sous
celle d'un test : passé ce délai, le test qui l'attend échoue avec ce que le chargement a dit, le
chargement s'arrête et la fin de pytest ne l'attend plus. Le délai d'un test couvre l'item entier, démontage compris :
un démontage qui suit un gel peut se figer à son tour, et le délai du travail (20 minutes) reste
le filet.

Un pytest tué (`SIGTERM`, `SIGKILL`) avant sa fin laisse la base `waterfall_witness_*` (et ses
copies), les rôles `waterfall_witness_*_signing` et `waterfall_witness_*_service` et le répertoire
`waterfall-witness-*` du répertoire temporaire du système ; le chargement, lui, s'arrête seul à
son échéance. Rien ne les balaie : supprime à la main les bases (`DROP DATABASE … WITH (FORCE)`),
puis les rôles (`DROP ROLE`), puis le répertoire. Le service d'un créneau, en mémoire, les perd
avec `make test-services-down`.

- **Dans la chaîne**, `back.yml` démarre PostgreSQL en service du travail et pose la variable.
- **Sur un poste**, le Makefile s'en charge : `make test-back` et `make coverage-back` démarrent
  PostgreSQL, pour le créneau du worktree (« Commandes »), quand la variable n'est pas déjà posée —
  après l'attente d'un créneau lourd, `TESTS` compris —, et la posent sur lui. `make test-services`
  le démarre seul (`deploy/compose/compose.test.yaml` : PostgreSQL 18, à l'image de la plateforme,
  en mémoire, sur `127.0.0.1:<port du créneau>`, `20000` dans le dépôt principal), sans rien faire
  de plus s'il tourne, et `make test-services-down` le retire avec ses volumes ; `make slot-release`
  le retire aussi. Aucun `docker run` à la main. Une variable que l'environnement pose déjà
  l'emporte, et son service n'est pas démarré : la chaîne n'est pas changée.
- **Le client PostgreSQL du poste** est celui de la majeure du serveur, 18 : `pg_dump` et
  `pg_restore` dans `/usr/bin` (`postgresql-client-18` : celui de l'archive d'Ubuntu 26.04 sur un
  poste, celui du dépôt PGDG sur le runner, que l'image `ubuntu-26.04` porte déjà), que les tests
  des sauvegardes et des restaurations appellent ; `make check-tools` avertit d'un autre. Un client
  plus récent que le serveur lui pose des réglages qu'il ne connaît pas, et aucune restauration
  n'aboutit (#982) ; un client plus ancien refuse de vider la base.
- **Sans la variable**, un test qui a besoin de la base **échoue** en le disant, et ne passe pas
  en silence. Les tests d'`examples/`, sockets fermées, n'en ont pas besoin.
- Un test qui a besoin de deux instances du service lance deux processus (`subprocess`), chacun
  sur sa connexion : l'environnement d'Alembic, lui, n'est pas rentrant, et se joue dans un
  processus à la fois.

### Un test contre le stockage objet

Une sauvegarde se teste contre un vrai stockage objet, Garage, l'image de la plateforme de service
(PBS-3.3) : la variable `WATERFALL_TEST_STORAGE_URL` le désigne avec une clé qui peut créer un
compartiment, `http://<clé>:<secret>@127.0.0.1:3900`. La fixture `backups_bucket`
(`backend/tests/conftest.py`) y crée un compartiment pour la session de tests, et le vide puis le
supprime à la fin. Les sauvegardes appellent `pg_dump` et `pg_restore` dans `/usr/bin`, ceux de
Debian et d'Ubuntu, de la majeure du serveur, 18 (« Un test contre PostgreSQL »). Elles vident les
bases comme le worker de la plateforme, par un rôle de sauvegarde que la fixture `backup_role`
(`backend/tests/conftest.py`) crée pour la session, membre de `pg_read_all_data` (#895).

- **Dans la chaîne**, `back.yml` démarre Garage par `docker run` — un service du travail ne
  reçoit pas les arguments qu'il demande — et pose la variable.
- **Sur un poste**, le Makefile démarre Garage comme PostgreSQL (« Un test contre PostgreSQL ») :
  `make test-back` ou `make test-services`, qui lui donnent l'image et le `garage.toml` de la
  plateforme, une clé et un secret propres aux tests, et la variable
  `http://<clé>:<secret>@127.0.0.1:<port du créneau>` (`20002` dans le dépôt principal) ;
  `make test-services-down` le retire. Aucun `docker run` à la main.
- **Sans la variable**, un test qui a besoin du stockage **échoue** en le disant.

### Un test contre Redis

La session du front et la file des tâches du back se testent contre un vrai Redis, jamais un
double : la variable `WATERFALL_TEST_REDIS_URL` le désigne (`redis://127.0.0.1:6379/0`), une base
que les tests sont seuls à employer. Côté front, `withTestRedis()` (`frontend/src/test/session.ts`)
y pointe le magasin des sessions pour la durée d'un fichier de test ; chaque clé est tirée au
hasard : les fichiers qui tournent ensemble ne se rencontrent pas, et les clés expirent
d'elles-mêmes. Côté back, la fixture `queue` (`backend/tests/conftest.py`) ouvre la file sur un flux
à elle, supprimé après le test, et `platform_queue` sur celui de toute installation, que les
commandes de la plateforme emploient, vidé avant et après. Les tests du back tournant sur
plusieurs processus, chacun prend la base qui suit celle de la variable selon son rang (`gw0` la
sienne, `gw7` la septième après) : le flux de toute installation n'est jamais vidé sous les pieds
d'un autre. Aucun test ne vide le serveur.

Le cache des indicateurs du jour (US-1720) se teste de même, contre ce Redis. Il est dans la base de
la file, sous le préfixe `waterfall:indicators:`, une entrée par projet sous une clé qui porte
l'empreinte de ce dont les indicateurs dépendent (`core/indicators/caching.py`) : un test qui écrit
change la clé, et ne vide rien. La fixture `cache` de `backend/tests/test_indicators_day_cache.py`
supprime après le test les entrées du préfixe dans la base du processus. Le test du vidage complet,
seul à lancer `FLUSHDB`, le fait sur une base propre à lui, la huitième après celle du processus,
qu'aucun processus de tests ne prend (huit au plus, `--maxprocesses 8`) ; un Redis indisponible se
simule par une adresse où rien n'écoute (`redis://127.0.0.1:1/0`), jamais en arrêtant le service.

- **Dans la chaîne**, `front.yml` et `back.yml` démarrent Redis en service du travail et posent la
  variable.
- **Sur un poste**, le Makefile démarre Redis comme PostgreSQL (« Un test contre PostgreSQL ») :
  `make test-back`, `make test-front` et leurs couvertures, ou `make test-services` ; l'image est
  celle de la plateforme, sur `127.0.0.1:<port du créneau>` (`20001` dans le dépôt principal) ;
  `make test-services-down` le retire. Aucun `docker run` à la main.
- **Sans la variable**, un test qui a besoin de Redis **échoue** en le disant, et ne passe pas en
  silence.

Keycloak, lui, n'est pas dans les tests du front : `frontend/src/test/identity-provider.ts` répond
au serveur de Next comme le royaume `waterfall` — code à usage unique pour son vérificateur, jeton
de rafraîchissement tourné à chaque emploi et refusé au second, jetons signés d'une clé à lui.
`make test-keycloak` prouve contre le vrai royaume l'échange du code avec son vérificateur, le
refus d'un jeton de rafraîchissement déjà employé et la fermeture des sessions d'un compte ; le
jeton de déconnexion que Keycloak poste au front, le parcours contre le service d'US-0340
(`frontend/e2e/service/session.spec.ts`) ; `refresh_expires_in`, les deux heures d'une session
inactive, et ce qu'US-0350 demande d'autre au royaume — chaque nature de compte, le mot de passe,
le verrouillage, le lien —, `backend/tests/test_keycloak_sign_in.py` ; le retour à l'écran visé,
les parcours contre le service d'US-0350/L5b (#849).

### Un parcours de bout en bout

Un parcours s'écrit sous `frontend/e2e/`, en Playwright, et cite dans son titre l'exigence
qu'il couvre : `test("… [WF-QUA-0050-A]", …)`. Il trouve les éléments par leur rôle et leur
nom accessible (`getByRole`), comme un utilisateur les voit, jamais par une classe CSS.

Une page ouverte par son adresse s'affiche avant que React l'ait hydratée : un lien suivi charge
alors son écran en document entier, mais un clic sur un bouton, une touche dans une cellule, se
perdent (#471). Un parcours ouvre donc un écran de projet par `openHydrated`
(`frontend/e2e/hydration.ts`), qui attend le témoin de l'hydratation : le cookie `wf_last_project`,
que la coquille n'écrit que dans un effet. Hors projet, rien n'en témoigne : le geste se répète
jusqu'à ce que React y réponde, sans défaire celui qu'il a déjà reçu (`setExpanded`, `openMenu`, et
`sortUntilAddress` pour un tri, qui ne se presse jamais à l'aveugle). Un écran de grille s'attend à
la borne des écrans de grille, quinze secondes (`WORKING`, #315, #419 ; elle, `MARKING` et les
autres bornes des parcours sont écrites, avec les mesures qui les justifient, dans
`frontend/e2e/bounds.ts`, US-2290), qu'un clic l'atteigne ou le relise (un tri, un filtre, une
recherche, le détail d'une ligne). Un écran de grille est une grille dense — devis, planning, reste
à engager, risques, coûts réels, portefeuille —, ou un écran qui lit la structure de mille tâches :
l'arborescence et les chronologies, par `listNodes`, et le Kanban, par `listStartableTasks` — la
mesure de #646 sur PRJ-001, contre le service : environ 1,3 seconde
pour les 960 cartes et leurs 1,8 mégaoctet, et deux secondes du clic ou de l'adresse à la première
carte, loin sous cette borne. La
comparaison de deux révisions s'y ajoute, le temps d'une décision : elle rend ses 2 770
modifications en une table simple, rendue au serveur, qui dépasse cinq secondes en développement
(constat #624 d'EP-14/L45a, à trancher — admise, ou portée sur la grille dense) : du clic à
l'adresse, pour cinq mégaoctets de réponse, environ quatre secondes au serveur, jusqu'à dix quand un
autre parcours le charge, et trois ou quatre au navigateur, le faux back répondant en quelques
dizaines de millisecondes (#729). Un parcours qui rend ainsi des milliers de lignes hors d'une
grille virtualisée peut garder sa trace sans instantanés du DOM (`snapshots: false`), et seulement
après une mesure qui montre ce qu'ils coûtent dans la borne — pour la comparaison, deux secondes
environ, qui la portaient jusqu'à onze secondes sur quinze sur un poste au repos. La trace perd le
DOM, le réseau, l'arbre d'accessibilité et la capture de chaque action, et ne garde que les actions,
leurs sources et le film de l'écran : le parcours dit lui-même, en annotation, la durée de ce qu'il
attend (`test.info().annotations`). Le remède atténue, il ne solde rien : le reste tient à l'écran.
Les risques et les coûts réels, relus, ont dépassé cinq secondes sous charge : les mesures sont
consignées dans #500, qui reste à trancher. Tout autre écran garde les cinq secondes d'une assertion
sur un poste, dix dans la chaîne, où deux workers et leurs fronts partagent les quatre processeurs
d'un runner : un écran qui y répond en une seconde a dépassé les cinq sous charge, et fait échouer
un passage de la file de fusion environ une fois par semaine sans défaut derrière (#2015,
`expect.timeout` de `playwright.config.ts`). Un parcours qui enchaîne trois de ces bornes, ouverture
comprise, dépasse les trente secondes d'un test, et prend `test.slow()`. Une ligne de grille
vérifiée est dans la fenêtre : au-delà des lignes en vue à l'ouverture, le parcours défile jusqu'à
elle (`scrollToPosition`, `frontend/e2e/scroll.ts`) plutôt que de compter sur la marge que la grille
rend autour de la fenêtre.

**Un parcours lent** — qui dépasse sa borne dans la chaîne sans régression derrière — se traite en
trois degrés, dans cet ordre (US-1890). D'abord, la cause se mesure dans la chaîne, sous la charge de
la file, jamais sur un poste seul : le parcours écrit à son journal et en annotation la durée de
chaque étape de ce qu'il attend, et le journal du service dit le reste (`make service-logs`, versé au
job quand un parcours échoue). Puis :

1. **corriger la lecture**, ou l'écriture, que la mesure désigne, au back ou au front : #2924 a
   ramené `getRemainingIndicators` de 2 845 requêtes à 58 ; la création d'un projet par deux workers
   à la fois finissait en 500 sur un verrou mortel de PostgreSQL entre les créations de partitions
   (`create_project_partitions`), et le parcours attendait quinze secondes une adresse qui ne venait
   jamais (famille A d'EP-24, dix-sept passages de la file du 8 au 11 novembre, tous sans la
   migration `0026` d'US-1560/L3, qui les met l'une après l'autre ; aucun depuis) ;
2. **sinon, isoler le parcours** — un compte, un projet, un réglage à lui, ce qu'il n'éprouve pas
   préparé par l'API sous jeton (`inscribe`, `employRole` d'`own-project.ts`) —, **ou le
   sérialiser** : `@serial`, joué par le projet `shared-serial`, quand il écrit un objet unique de
   l'installation ;
3. **n'élargir une attente qu'en dernier recours**, la mesure dans le commentaire qui l'élargit — le
   passage de la chaîne, les durées relevées —, et `test.slow()` de même.

`createOwnProject` (`frontend/e2e/own-project.ts`) en est l'exemple : chaque création écrit au
journal « Own project created », l'accueil, la boîte, puis, depuis « Créer », l'action serveur
demandée et répondue, l'écran du projet demandé, répondu et fini, et l'adresse atteinte ; manquée,
ce que la boîte affiche. Sur les 52 créations du passage complet 43386149437, la création entière
prend 2,2 s en médiane et 5,8 s au plus, l'adresse 0,7 s après « Créer », et l'API répond `POST
/projects` en 0,24 s en médiane, 1,9 s au plus : rien n'y justifie d'élargir `WORKING`.

`ScreenSteps` (`frontend/e2e/screen-steps.ts`) fait de même pour un écran que le serveur relit :
chaque étape, et les requêtes RSC en vol pendant elle. Sur le parcours de WF-REV-0080-A, elle a
montré une attente déjà vraie avant son geste : après « Comparer », l'adresse gardait `difference=`
comme celle d'avant, et le filtre levé aussitôt faisait lire deux comparaisons de PRJ-001 ensemble
à l'API, qui n'est qu'un processus (2,2 s pour une seule) ; il arrivait en 15 s au lieu de 8 sous
six workers (#2942). Une attente qui suit un geste attend ce que ce geste change.

`make e2e` : Redocly et Prism sont des dépendances de développement du front, à version exacte
(`frontend/package.json`, verrouillées par `pnpm-lock.yaml`) : `make install-front`, que la cible
joue d'abord, les met dans le magasin de pnpm (le cache de la chaîne), d'où le `Makefile` les lit,
sans `npx --yes` ni registre de npm à chaque passage — leur installation par `npx` comptait dans
les 120 s que Playwright donne au faux back (#1901), et un registre muet faisait échouer le passage
avant son premier test (#2913). Les cibles qui lancent Redocly ou Prism sans `install-front`
(`lint-openapi`, `mock-spec`) installent quand `package.json` ou le verrou sont plus récents que
`node_modules/.modules.yaml` : un relèvement de version s'installe au passage suivant. Un registre
qui refuse la connexion fait échouer l'installation en 70 s environ, sur une erreur qui nomme
l'adresse du paquet demandé ; elle n'a pas d'autre borne, et un registre muet attend celle du
réseau. `make e2e-measure` et `make e2e-service` lancent `install-front`, puisque
Playwright y démarre aussi le faux back. Playwright démarre le faux back (`make mock`) et le front,
joue les parcours dans Chromium, puis arrête les deux — il signale leur groupe de processus entier,
sans quoi les serveurs que `make` et `pnpm` lancent survivraient. Il démarre toujours ses propres
serveurs, sur des ports à lui — ceux du créneau du worktree (« Commandes », « Les créneaux des
worktrees ») : 4110 pour le faux back et 3100 pour le front dans le dépôt principal, au créneau 0,
`20000 + 100·i + 20` et `+ 40` au créneau i d'un worktree de lot, qui fait d'abord `make slot` —,
jamais ceux de `make dev`, et son faux back sert une variante du contrat écrite sous
`frontend/.e2e/`, que `make dev` ne lit pas : un port déjà pris fait échouer le lancement en le
disant. Deux worktrees à deux créneaux jouent donc leurs parcours en même temps, avec
`WATERFALL_SLOTS` d'au moins 2, sans quoi le second attend que le premier ait fini. `E2E_API_PORT`
et `E2E_FRONT_PORT`, posés dans l'environnement, l'emportent sur ceux du créneau — le front des
parcours en prend autant qu'il a de workers, à partir de lui (ci-dessous), quarante au plus dans
un bloc ; un port qui n'est pas un entier de 1 à 65535 est refusé. `make e2e-browsers` installe le
navigateur. `make e2e SHARD=i/N` ne joue que le i-ième de N morceaux des parcours, répartis par durée
mesurée (`tools/e2e-durations.json`, que rafraîchit `make e2e-durations`) — `SHARD` ne se combine pas
avec `TESTS=<fichier>`, que la recette refuse : le fichier peut être dans un autre morceau ;
`SHARD=lint` ne vaut que pour `make check-front-tests` et `make test-front`, et `check`,
`check-front`, `check-all` et `e2e` le refusent —, comme
chacun des runners de la chaîne (« Chaîne »), et `make e2e WORKERS=<n>` les joue sur `n` workers
(`E2E_WORKERS`, que lit `playwright.config.ts` ; un entier de 1 à 40, rien d'autre : un front par
worker, et le bloc d'un créneau n'en porte que quarante), moins que Playwright n'en prend de
lui-même — la moitié des processeurs, plafonnée à quarante — sur un poste chargé, où
des parcours échouent par délai (#736). `make e2e-service` a son défaut à lui (#2890) : les trois
quarts de `WATERFALL_PROCESSORS`, la part de processeurs du créneau, au moins 1 et au plus 40 — 6 sur
8 processeurs —, et non la moitié des processeurs du poste, 16 sur 32, où 18 à 23 parcours échouaient
à naviguer (`toHaveURL`) ; mesuré à 8, 10 et 12 workers sur 8 processeurs, quatre créneaux pris,
ils échouaient encore à naviguer, à 6 aucun échec de navigation sur deux passages. `WORKERS=<n>` ne vaut
que pour `make e2e` ; `make e2e-service` prend `E2E_WORKERS=<n>`, dans l'environnement ou sur la
ligne de commande, qui l'emporte (vide, il est ignoré, sur la ligne de commande comme dans
l'environnement) ; un `WATERFALL_PROCESSORS` qui n'est pas un entier positif est refusé avant toute
commande. Avec `WATERFALL_API_ADDRESS`, le harnais joue contre l'API qu'elle nomme et ne démarre aucun
faux back.

**Les parcours se jouent contre le front construit pour la production** (US-0590), celui
qu'ouvrent les utilisateurs : un serveur `next start` par worker des parcours, sur `E2E_FRONT_PORT`
et les ports qui le suivent, chaque worker jouant contre celui de sa place parmi les workers
(`TEST_PARALLEL_INDEX`) ; un seul pour la mesure de la seconde, jouée sur un worker, pour les
parcours du service, dont le royaume ne connaît l'adresse que d'un front, et pour le serveur de
développement. Le serveur de développement rendait en série les pages des quatre workers, au-delà
des cinq secondes d'une assertion (#1262), et montait à plus de 9 Go après avoir compilé chaque
route (#1309). Un seul front construit, un processus, les rendait en série lui aussi, plus vite :
occupé les trois quarts du temps sous six workers, il laissait l'écran des risques en chargement
cinq secondes après le clic, trois fois sur soixante (#1477) ; un front par worker, aucune sur
soixante. Playwright démarre les fronts l'un après l'autre, et le premier construit le front quand
il ne l'est pas. Il en démarre autant que de workers même pour un seul fichier
(`make e2e TESTS=…`) ou un morceau : chacun répond en une seconde environ sur le poste, si bien
qu'un rejeu sous quatre workers attend trois ou quatre secondes de plus son premier parcours. Le
harnais ne sait pas, en lisant sa configuration, combien de workers le rejeu occupera : un plafond
au nombre de fichiers donnerait un seul front aux quatre workers d'un fichier joué test par test
(`mode: "parallel"`, `accessibility.spec.ts`), l'engorgement de #1477 ; `WORKERS=1` en démarre un
seul. `make e2e`, `make e2e-measure` et
`make e2e-service` construisent d'abord le front comme `make build-front`, sans API joignable
(#131) — un même build sert donc le faux back et le vrai service —, puis lancent Playwright, qui le
démarre ; en local, le cache de Next (`frontend/.next/cache`) abrège les builds suivants.
`E2E_BUILT=1` dit le front déjà construit : ni la cible ni le harnais ne le reconstruisent, ce que
fait la chaîne, qui le construit une fois par exécution pour toutes ses parts — les morceaux des
parcours, la mesure et les parcours du service (`front-build`, « Chaîne »). Sans elle, le
harnais lancé hors du Makefile (`pnpm exec playwright test`) construit lui-même le front avant de
le démarrer.

`E2E_DEV_SERVER=1` rejoue en local les parcours contre le serveur de développement (`next dev`),
sans reconstruire le front à chaque rejeu : `make e2e E2E_DEV_SERVER=1 TESTS=e2e/<fichier>`, ou
`make e2e-service E2E_DEV_SERVER=1`. La mesure ne la suit jamais : elle se joue toujours contre le
front construit, si bien que `make e2e E2E_DEV_SERVER=1` la laisse de côté, et que
`make e2e-measure` construit le front quand même. Posée dans la chaîne (`CI` défini), elle fait
échouer le lancement, avec un message qui le dit. Rien ne préchauffe les routes pour elle : un
rejeu local se joue sur peu de fichiers, et le serveur de développement compile une route à sa
première demande, que la première assertion qui l'attend peut dépasser. `compile`
(`frontend/e2e/compile.ts`) reste pour un parcours qui compile d'abord ce qu'il atteint.

Le préchauffage des routes (`e2e/warm-up.ts`, #1145), qui demandait chaque route au serveur de
développement avant le premier parcours, est retiré avec ses tests : le front construit ne compile
rien à la demande. Une panne de l'API, du royaume ou de Redis se lit donc au premier parcours qui
l'atteint, et non plus avant lui (#1265).

**Aucun échec n'est toléré** (US-0590b, #1460) : au palier complet local comme dans la chaîne,
l'échec d'un parcours est un échec, même s'il passe rejoué seul. La règle provisoire de #1145, qui
laissait fusionner un lot dont les parcours de #1145 et de #1263 tombaient au palier local puis
passaient rejoués seuls, a disparu avec US-0590b, qui a corrigé ces échecs à leur cause : le front
construit, un par worker (ci-dessus), et le parcours au clavier allégé (ci-dessous). Un parcours
qui tombe se corrige à sa cause, jamais par une attente plus longue, un `retries`, un `fixme` ni un
`skip`.

Le front du harnais ouvre une connexion à lui pour chaque requête à l'API
(`WATERFALL_API_CONNECTIONS=closed`, « Le client de l'API ») : l'API y est toujours Prism, faux back
ou mandataire du contrat, qui ferme une connexion inactive depuis cinq secondes, et le serveur de
développement chargé envoyait une requête sur une connexion que Prism venait de fermer
(`UND_ERR_SOCKET: other side closed`, puis `Unreachable` dans `readOrFail`, #1145). Le harnais pose
aussi `WATERFALL_E2E=1` au front, contre le faux back comme contre le service : le front construit
n'admet qu'à cette condition le jeton fixe du faux back, et ne signale pas les connexions `closed`
(#1265).

`make e2e-service` joue contre le vrai service les parcours du projet Playwright `service`
(`frontend/e2e/service/`, US-0340), à côté de ceux du faux back, qui restent. Il démarre la
plateforme de service (`make service-up`), sous le projet et sur les ports du créneau du worktree («
Commandes »), son royaume appliqué avec l'adresse du front des parcours, `http://127.0.0.1:3100` au
créneau 0 (`WATERFALL_FRONT_ADDRESS`, que suit `E2E_FRONT_PORT`), et celle par laquelle Keycloak le
joint depuis son conteneur, `http://host.docker.internal:3100` (`WATERFALL_FRONT_BACKCHANNEL`),
quelles que soient celles que l'environnement exporte ; puis Prism en mandataire entre le front et
l'API (`prism proxy --errors`, service `contract-proxy`, sur `127.0.0.1:4210` au créneau 0, que
déplace `WATERFALL_PROXY_PORT`), qui sert la variante du faux back écrite dans
`docs/api/waterfall.proxy.json` : une réponse hors de son schéma devient une erreur 500
(`VIOLATIONS`), une adresse hors du contrat un 404 (`NO_PATH_MATCHED_ERROR`), une requête hors du
contrat un 422, et Prism écrit chacune à son journal sous sa requête. Prism n'y exige aucun jeton :
le service authentifie, et son refus passe tel quel, confronté au contrat. Il lance enfin Playwright
avec, dans son environnement — jamais en ligne de commande, où le mot de passe de Redis se lirait —,
`E2E_PART=service`, `WATERFALL_API_ADDRESS` (le mandataire), `E2E_CONTRACT_PROXY` (son conteneur),
`E2E_SERVICE_DATABASE` (celui de PostgreSQL), `E2E_SERVICE_CACHE` (celui de Redis),
`E2E_SERVICE_DIRECTORY` (celui d'OpenLDAP), `E2E_SERVICE_WORKER` (celui du worker), `WATERFALL_KEYCLOAK_ADDRESS`,
`WATERFALL_FRONT_ADDRESS`, `WATERFALL_REDIS_URL` (le Redis de la plateforme) et
`NODE_EXTRA_CA_CERTS` (la racine de l'autorité du frontal de Keycloak) ; le secret du client du
front, et celui de l'administrateur de Keycloak, viennent de l'environnement. La plateforme reste
démarrée : `make service-down` l'arrête. Avant Playwright, il amorce la plateforme
(`waterfall-api install`, service `install`, US-0420) : le premier administrateur,
`administrateur@waterfall.test` (`E2E_ADMIN_EMAIL`), porte le rôle « Administrateur », et le lien
qui fixe son mot de passe, valable jusqu'à son emploi, est dans `E2E_INSTALLATION_LINK` — vide dès
qu'un parcours l'a employé, l'administrateur se connectant ensuite avec le mot de passe constant des
parcours (`LOCAL_PASSWORD`, `frontend/e2e/service/realm.ts`). Une précondition : `E2E_ADMIN_EMAIL`
doit être l'adresse avec laquelle la plateforme a été amorcée la première fois. Une relance
n'installe rien de nouveau et ignore une autre adresse (`installation.admin_email_ignored` dans ses
journaux) : sur une plateforme amorcée avec une autre, par `make service-install` et un autre
`WATERFALL_ADMIN_EMAIL`, les parcours chercheraient un administrateur qui n'existe pas. Il faut
alors donner la première adresse à `E2E_ADMIN_EMAIL`, ou repartir d'une plateforme vide
(`make service-down WATERFALL_RESET_DATA=yes`).
L'amorçage fait, il charge le témoin (service `witness`, comme `make service-witness`, EP-05) : les
écrans du référentiel que le service sert y lisent ce que disent les exemples du contrat ; une
plateforme qui le porte déjà n'en reçoit rien de plus.

Une fois les parcours joués, `make e2e-service` cherche, dans les journaux de tous les services de la
plateforme, Keycloak compris, sous tous les profils de Compose, et dans celui du front des parcours
(`frontend/.e2e/front.log`, que git ignore : le serveur de Next est un serveur web de Playwright,
que Compose ne tient pas), et dans ceux de l'amorçage et du témoin, qu'il lance par `run --rm` et
garde dans `frontend/.e2e/install.log` et `witness.log` — de l'amorçage, son journal seul : sa
sortie standard est le lien du premier administrateur, imprimé exprès (#4395) —, les secrets et les
jetons connus (`make service-logs-search`, WF-OBS-0020, US-2900) ; il échoue s'il en trouve un, ou
si les journaux n'ont pas pu être lus ou sont vides. Il cherche aussi, dans chaque fichier que git
suit, les secrets de la plateforme de service (`python -m wftools.logsearch repository`,
WF-SEC-0010, US-2840), et échoue s'il en trouve un. Cette recherche-là a une portée plus étroite que
celle des journaux : les seules valeurs que la plateforme reçoit pour ses secrets — les variables de
`SECRET_VARIABLES` —, telles qu'elles sont écrites, échappées en JSON ou citées dans une URL. Elle ne
cherche ni les formes des jetons, que des tests écrivent exprès, ni le mot de passe des comptes des
parcours (`FIXED_SECRETS`), constante du dépôt écrite dans `frontend/e2e/service/realm.ts`, ni une
valeur qu'un workflow de `.github/workflows/` fixe en clair pour l'une de ces variables
(`chain_values`) : les valeurs de poste de la chaîne, publiques et nommées comme telles, que les
images ne doivent pas porter (`wftools.images`) et qu'un poste reprend de `keycloak.yml`
(`INSTALL.md`) ; aucune n'est un secret d'une plateforme. Sous la chaîne, et sur un poste qui a
repris ces valeurs, toutes en sont : la recherche le dit, ne cherche rien et passe ; elle mord sur
un poste qui a ses propres valeurs, ou chez un exploitant. Elle ne dit rien d'un secret
d'exploitation qu'aucune de ces variables ne tient. Il vérifie
ensuite que chaque ligne des journaux de l'API, du worker, de son ordonnanceur et du service de
restauration est un enregistrement qui porte son identifiant de corrélation, son auteur et sa
gravité (`make service-logs-fields`). Un import qui échoue dans le worker se suit dans ces journaux
par l'identifiant que son message donne (`frontend/e2e/service/import-trace.spec.ts`).

Les parcours se jouent en six projets Playwright. `installation` d'abord
(`installation.setup.ts`, WF-EXP-0020) : le lien ne sert qu'une fois, et ce parcours fixe le mot de
passe de l'administrateur, se connecte, et constate son rôle, les trois rôles prédéfinis et le
catalogue. `service` ensuite, sur plusieurs workers (#730) : chaque parcours se connecte avec un
compte local à lui, que l'administrateur crée par l'API (`createUser`, `createPasswordSetupLink`) et
dont il fixe le mot de passe par le lien rendu, ou avec un compte dont aucun autre parcours ne ferme
les sessions — l'administrateur lui-même, pour les écrans des comptes et des rôles et pour le
journal d'audit (`accounts.spec.ts`, `roles.spec.ts`, `audit.spec.ts`). L'administrateur donne leurs
rôles aux comptes locaux par l'API ; la personne de l'annuaire de test,
`dominique.annuaire@waterfall.test`, et celle du fournisseur externe, `camille.externe`
(`deploy/keycloak/development/`), que l'API admet sans rôle à leur première requête (WF-ADM-0180) et
que seul `sign-in.spec.ts` emploie, reçoivent le leur par une écriture dans la base de la plateforme
(`grantRole`), une fois admises. Aucun parcours ne donne à un autre compte que l'administrateur les
deux permissions d'administration — `give` le refuse —, et aucun ne renomme ni ne change un rôle
prédéfini : les refus `LAST_ADMINISTRATOR` de l'écran des rôles et de celui des comptes en dépendent
(`roles.spec.ts`). Le jeton de l'administrateur, qui vit cinq minutes, se redemande quand il en a
plus de quatre. `shared` à côté de `service`, après `installation` : les parcours partagés avec
le faux back (ci-dessous).

Tous les workers connectent l'administrateur, et le royaume refuse les identifiants d'un compte
qu'il est déjà en train de vérifier, comme s'il était verrouillé (`user_temporarily_disabled`, sans
échec compté) : une connexion attend son tour (`oneAtATime`, `realm.ts`), sous un verrou — un
répertoire du dossier temporaire du système, nommé d'après la course et le compte —, qu'elle tient
jusqu'à la réponse du royaume, attendue quinze secondes au plus, bien en deçà des trente que les
autres workers attendent le verrou. Un écran de table de l'administration s'ouvre par une adresse
qui dit sa recherche, vide au besoin (`?search=`) : une adresse muette rétablirait la recherche ou
les filtres que l'administrateur a gardés sur un autre parcours, puisqu'il est le même sur tous.
`realm` ensuite, sur un seul worker, une fois `service` et `shared` finis : les parcours marqués
`@realm-wide`, qui raccourcissent une durée du royaume, que lit chaque compte. `restoration` après
eux, seul : les parcours marqués `@platform-wide`, qui restaurent la plateforme entière et en
ferment toutes les sessions (US-0440, `backups.spec.ts`). `contract` enfin, le démontage
de `installation` : la garde du contrat de toute la course.

Le projet `service` ne joue que `frontend/e2e/service/`, que les autres projets laissent : contre
le front construit, comme les autres, sans `WATERFALL_AUTH=mock` — la vraie connexion, par le
royaume —, à l'écoute de toutes les interfaces du poste, d'où Keycloak joint son canal de
retour (#681), et avec la clé des actions serveur sans laquelle le front construit ne démarre pas
hors du faux back (`NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`, tirée pour la course si l'environnement
n'en donne pas) ; le navigateur accepte le certificat du frontal de Keycloak
(`ignoreHTTPSErrors`), que le serveur de Next tient de `NODE_EXTRA_CA_CERTS`. Ces requêtes vers
l'API, le serveur de Next les fait, hors de la vue du navigateur, et un écran peut survivre à
l'une d'elles : un fichier de ces parcours se tient au contrat par `heldToTheContract()`
(`frontend/e2e/service/contract.ts`), qui lit par Docker le journal du mandataire et échoue sur
toute ligne où Prism écrit `Request terminated with error:` — ses propres erreurs comme celles du
mandataire, corps illisible ou API injoignable (WF-ARC-0060). Prism écrit sa ligne une fois la
réponse rendue, et le serveur de Next lit encore l'API après la dernière assertion : chaque worker
lit chaque ligne une fois — par `docker logs --since`, à partir du moment où il s'était arrêté, et
du début de son premier fichier — ; un parcours échoue sur les erreurs écrites jusqu'à sa fin, une
erreur plus tardive fait échouer le suivant du worker. Le journal ne dit pas quel worker a demandé
quoi : une erreur fait échouer le parcours de chaque worker qui la lit, celui qui l'a causée parmi
eux. Le projet `contract` (`contract.teardown.ts`) relit enfin tout le journal de la course, depuis
son début (`E2E_SERVICE_STARTED`, que pose `playwright.config.ts`), une fois le mandataire tu —
rien d'autre que le contrôle de santé pendant deux secondes, la dernière ligne d'une réponse, qui
ne nomme pas sa requête, n'en étant que si elle suit celle de la réponse d'un contrôle (#735) — :
les erreurs d'après le dernier parcours d'un worker le font échouer, et celles qu'un parcours a
déjà dites, de nouveau. Ce début est la dernière ligne que le mandataire a écrite avant la course
(`docker logs --timestamps --tail 1`, `frontend/e2e/service/proxy-log.ts`), et chaque moment que les
parcours comparent est celui que Docker a donné à une ligne, jamais l'horloge du poste, qu'une
machine virtuelle laisse dériver de la sienne ; la garde prouve sa fenêtre : une ligne lue au moins
— le contrôle de santé en écrit une toutes les deux secondes —, et le refus de l'adresse hors du
contrat quand son parcours a joué. Un parcours le montre (`contract.spec.ts`) : une adresse hors du
contrat (`OUTSIDE`), que la garde lit, seule, refusée ; tout autre lecteur la lui laisse. Un statut
que l'opération ne déclare pas n'en est pas une pour Prism : la réponse passe, avec l'en-tête
`sl-violations` de sévérité `Warning`, que son journal ne rattache pas à sa requête — ce sont
aujourd'hui les 404 des opérations que lit la coquille et que le service ne sert pas encore. Les
tests du service tiennent ses statuts au contrat (`ContractClient`), les parcours ses corps
(#726). Les parcours de la connexion s'y jouent (US-0350) : se connecter, se déconnecter sur tous
ses postes, la session du front perdue comprise, aucun jeton dans le navigateur, la fermeture des
sessions par le royaume (`session.spec.ts`) ; chaque sorte de compte qui agit selon ses rôles, la
session inactive qui ramène à la connexion puis à l'écran visé, le compte non admis
(`sign-in.spec.ts`) ; le compte local créé, son lien de fixation, les règles du mot de passe et le
verrouillage (`password.spec.ts`) ; la langue décidée par le navigateur jusqu'à ce que le compte en
choisisse une, puis retrouvée d'un poste à l'autre, appliquée sans reconnexion, l'avatar déposé,
remplacé et retiré, les colonnes masquées, les largeurs et les filtres des tables retrouvés à la
réouverture, chaque compte voyant les siens (`account.spec.ts`, US-0400) — ces réglages lus dans la
base (`gridPreferences`), où le front les écrit après une pause ; une attribution de rôle faite par
le service, que le journal d'audit, filtré sur son auteur et son action, présente à chaque lecteur
dans sa langue (`audit.spec.ts`) ; l'amorçage (`installation.setup.ts`), l'écran des comptes
(`accounts.spec.ts`) et celui des rôles (`roles.spec.ts`). Ils règlent le royaume par son API
d'administration, en administrateur du royaume `master` (`WATERFALL_KEYCLOAK_ADMIN_PASSWORD`) — une
durée raccourcie le temps d'un parcours, que `service-up` rend de toute façon au royaume suivant —,
et demandent un jeton pour l'API par le flux du client du front (`WATERFALL_FRONT_CLIENT_SECRET`).

Un parcours dont le service sert l'écran se joue des deux côtés : contre le faux back par
`chromium`, comme avant, et contre le service par le projet `shared` (EP-05). Il importe `test` de
`frontend/e2e/mode.ts` et non de `@playwright/test`, et porte l'étiquette `@shared` — dans son
titre, ou par `tag`, comme `@realm-wide` : le `grep` du projet lit les deux —, dans quelque fichier
de `frontend/e2e/` qu'il soit, ceux de la mesure exceptés, et ceux de `frontend/e2e/service/`, que
le projet `service` joue déjà (l'étiquette ne s'y pose pas : le parcours serait joué deux fois) ;
aucune liste de fichiers ne le nomme.
Chaque US étiquette ses parcours quand le service sert son écran. Contre le faux back, `test` ne
change rien : le faux back accorde la session. Avec `WATERFALL_API_ADDRESS`, `inService` est vrai,
et deux fixtures de `mode.ts` font ce qu'un fichier de `frontend/e2e/service/` demande par ses
crochets : chaque worker obtient une fois un compte local de la course qui porte les rôles
prédéfinis « Manager » et « Chef de projet » (US-0970), que crée l'administrateur de l'installation
(`accountAdministrator`, `localAccount`), et chaque parcours se connecte d'abord avec lui (`signIn`,
sur `/account`), puis se tient au contrat, comme `heldToTheContract()` y tient un fichier
(`startReading`, `expectNothingRefused`, `contract.ts`). Des fixtures plutôt que des crochets : un
crochet déclaré dans un module que les fichiers importent ne se déclare qu'une fois par worker, pour
le premier de ses fichiers seul. Un parcours dont l'assertion diffère entre les deux — une écriture
que le faux back ne garde pas — lit `inService`.

Un parcours de l'administration ou de l'état porte `@administration` à côté de `@shared`, dans son
titre comme `@shared` : la fixture `administration` de `mode.ts` le connecte alors avec un compte de
la course, un par worker, qui porte le rôle « Administrateur (parcours) » — `users.read`,
`access_roles.read`, `system_status.read`, `audit_log.read`, `backups.read`, et ni `users.write` ni
`access_roles.write` —, que `installation.setup.ts` crée seul et en premier. Le « Manager » ne
reçoit ni `users.*` ni `system_status.read` ; et `give` refuse toujours les deux permissions
d'administration à un autre compte que l'administrateur de l'installation, dont les refus
`LAST_ADMINISTRATOR` de `roles.spec.ts` dépendent : le rôle ne porte que des lectures. Chaque
parcours `@shared` remet aussi à zéro les préférences de grille du compte qui s'y connecte
(`resetGridPreferences`, `updateMyPreferences`), qu'un tri ou un filtre d'un parcours précédent
aurait laissées (#2282), ce que `service/grid-reset.spec.ts` éprouve.

Le projet `shared` joue ainsi les parcours du projet contre le témoin chargé, tranches des projets,
des tâches et des lignes comprises (« Le back et les frontières du noyau ») : PRJ-001 En cours, son
code posé et l'offre 100 désignée pour référence, ses révisions 100 et 101 marquées, la 102 ouverte.
La tranche des tâches (`waterfall-api load-witness`, EP-06, US-1480) charge, pour la structure
principale de chacune des trois révisions, les mille tâches de PRJ-001 avec leurs liaisons, leurs
modes et leurs durées, leurs états et leurs dates de démarrage et de terminaison, leurs
inscriptions, les deux chronologies et la date de début de planning. La tranche des lignes (EP-07,
US-1570) vient après les tâches de chaque révision et avant son marquage : elle charge les lignes de
devis des trois révisions (cinq mille pour la structure principale de la 102), avec leurs rôles,
leurs catégories, leurs grandeurs, leurs délais de paiement et leurs sous-projets, et les
calendriers de rôles qui donnent leurs dates aux 103 tâches à calendrier 4×10 h de la frise
(#2594) ; puis elle rejoue la mise à jour des taux de la 101 (le 12 janvier 2026), désigne l'offre
100 pour référence (le 15 janvier 2026), et le passage En cours que cette désignation produit
s'écrit aux transitions du témoin. La tranche des coûts (EP-09, US-1650/L2, `witness/costs.py`)
suit la chronologie, appelée par la marche des événements de `witness/revisions.py` pour chaque
écriture de coûts : les cinq imports de coûts réels de PRJ-001 (les 3 avril, 4, 6 et 11 mai, 3 juin),
chacun avec sa ligne du journal des imports des échanges et son entrée du journal des coûts (période,
colonnes conservées, comptes), les vingt-huit lignes de coût qu'ils ont apportées ou mises à jour,
chacune avec son poste, son imputation que le service calcule, ses colonnes conservées et l'audit
de ses imports, l'exclusion de la réception du client (le 6 avril à 9 h 15, avec son motif) et
l'extraction d'avril rejouée, analysée le 2 juin ; aux identifiants et aux instants du
témoin, le chef de projet du témoin pour compte, par les interfaces de `core/exchanges` et de
`core/costs`, sans fichier Excel ni worker. Les imports viennent de `fixtures/api/witness_costs.json`,
que `make mock-data` écrit à côté des exemples (`wftools.mockwitnesscosts`) et que le back lit par un
modèle strict qui lui est propre, sans importer `wftools`. Le reste à engager n'a pas de tranche : les
lignes de la révision 102 portent `previous_*` de la copie de la référence 101, et leurs états
viennent d'EP-06. Le générateur des exemples répartit une ligne de devis à cheval sur deux années
comme le service (WF-DEV-0040, #2838) : le calculé est l'attendu, et les chiffres des exemples sont
ceux du service. La tranche d'EP-08 y a mis les provisions, l'avenant 1 fusionné — qui fait de la 101
la référence —, les risques et l'avenant 2 (US-2650). Ce qu'elle n'a pas : les volumes entiers
(**EP-13**, qui clôt : les trois cents projets et les dix-huit mille lignes de coût du §4.6.2).
Les indicateurs n'ont pas de tranche : le marquage rejoué par le chargeur
(`load_marking`, EP-10, US-1670) conserve ceux de la révision 101 de PRJ-001 — le projet, ses deux
sous-projets et « hors sous-projet » — à son instant, le 1er février 2026 à 9 h, l'offre 100 ne
gardant aucun indicateur projet, et le service calcule ceux du jour sur la 102 (US-1740) ; les provisions et
les risques d'EP-08 changent la référence ; **EP-11** y ajoute le portefeuille,
**EP-13** les révisions marquées suivantes et les volumes entiers. En service, la structure de
PRJ-001 compte 5 966 nœuds, non les 5 999 du volume que le faux back sert. Ce que lisent PRJ-001 En
cours, sa référence et ses lignes se joue donc contre le service, aux attendus des exemples près que
la liste ci-dessous nomme. Les assertions d'écriture affirment ce qui a été écrit, relu, par
`inService`.

La liste consolidée de ce qu'un parcours ne rejoue pas encore contre le service tient ici : il se
saute par `inService` (`test.skip(inService, …)`) quand il est étiqueté, ou reste sans étiquette,
chaque entrée nommant l'EPIC qui la lève ; cet EPIC retire la garde et son entrée :

- `revisions.spec.ts` — la volumétrie (5 999 nœuds) seule (`NO_VOLUME_IN_SERVICE`) : le projet de
  volume n'existe qu'au faux back, jusqu'aux volumes d'EP-13 (#2696) ; **EP-13** retire la garde. La
  révision en cours et ses parties, la comparaison et « Écarts seulement » se jouent contre le
  service depuis US-1570/L2 (#2385), dont le chargeur donne au témoin ses tâches et ses lignes (le
  service sert `compareRevisions` et `getRateUpdateProposal`) ; la comparaison y est celle de toute
  la structure de PRJ-001, 5 966 nœuds en service, là où le faux back rend la fenêtre de son
  exemple. L'écran d'une révision en cours lit la proposition des taux comme toute lecture
  (`readOrFail`), non plus par `readUnlessRefused` : le service sert `getRateUpdateProposal`
  (#2173). L'historique se joue contre le service dès US-0960, avec les révisions 100 et 101 du
  témoin marquées dès US-0970.
- `revision-cycle.spec.ts` — les commandes de la révision 102 de PRJ-001 et l'ouverture indisponible
  (`NOT_REPLAYED_IN_SERVICE`) : le compte de la course n'est pas inscrit chef de projet des projets
  du témoin, par décision (#2193, option A) que nul EPIC ne renverse, si bien que le service ne lui
  liste pas les commandes de PRJ-001 ; les parcours qui écrivent créent leur propre projet. La
  désignation de l'offre 100 de PRJ-001 est celle du chargeur (EP-07), et le projet est En cours.
  L'abandon de la 102 (`WITNESS_KEPT`) ne se joue jamais contre le service, qui l'ôterait à tous les
  autres parcours. Le cycle (#1350) se joue contre le service seul (`SERVICE_ONLY`), sur un projet
  que le compte de la course crée (`own-project.ts`), chef de projet comme créateur : une révision
  ouverte puis marquée par le worker, la désignation refusée faute de tâches et de lignes, une autre
  ouverte puis abandonnée, rouverte, le code saisi, le projet sorti à Perdu. Le parcours qui suit
  dans le fichier est celui qui aboutit (US-1540) : une référence qui porte une tâche et une ligne
  est désignée, le projet reste en Chiffrage tant que le code manque, et le code saisi le passe En
  cours ; `pricing.spec.ts` y ajoute le chiffrage par la grille (voir plus bas). Il se joue depuis
  qu'**US-0850** (EP-05) sert les rôles de ressources : le référentiel minimal est complet, et le
  service crée un projet (#2194). Le parcours de restauration (`service/backups.spec.ts`) en crée un
  avant la sauvegarde, marque sa révision et en crée un second après, et ne les retrouve plus une
  fois la restauration faite (WF-ADM-0160-A) ; rejoué sur une même installation, il y laisse un
  compte et un projet de plus, la restauration reprenant tout le reste.
- `project-start.spec.ts` — aucune entrée : le départ vers le planning se joue contre le service
  (`BEFORE_EP06` levée par US-1460), sur un projet que le compte de la course crée, qui liste
  `import_planning` (US-1430) et sert les structures et `generatePlanningSkeleton`. Le lotissement
  d'un projet créé, écrit puis relu, se joue dès US-0950 (parcours jumeau, `SERVICE_ONLY`), le fond
  mémoire ne gardant rien du lotissement qu'on lui donne (`FAKE_BACK_FORGETS`) (#2543).
- `context.spec.ts` — le bandeau du contexte sur les risques et sur une structure différentielle
  se joue contre le service depuis US-2640 (les gardes `BEFORE_THE_RISKS` et
  `BEFORE_THE_DIFFERENTIALS` sont levées, l'avenant 2 marquant ses tâches comme le service les rend),
  comme celui des indicateurs depuis US-1730. Le bandeau du planning (EP-06), du devis (US-1560, EP-07), des écrans d'un projet créé, de
  ses paramètres et de ses révisions se joue contre le service.
- `review.spec.ts` — les chiffres des indicateurs (le reste à engager, le budget de référence, la
  valeur planifiée, l'écart et les indices de délai et de coût, la date du calcul) sont ceux de la
  révision 101 des exemples, que la fusion de l'avenant 1 fait la référence du témoin chargé : le
  parcours les lit contre le service depuis US-2640.
- `planning.spec.ts`, `structure.spec.ts`, `computed.spec.ts`, `keyboard.spec.ts` — les parcours
  qui écrivent sur le témoin de PRJ-001, dont le compte de la course n'est pas contributeur (#2193) :
  chacun a son jumeau contre le service sur un projet de la course (`planning-service.spec.ts`,
  `structure.spec.ts`, `computed.spec.ts`, `keyboard.spec.ts`), que nul EPIC ne renverse ; les
  parcours de ces fichiers qui lisent le témoin se jouent des deux côtés. Les parcours du reste à
  engager de `structure.spec.ts` qui écrivent sur PRJ-001 (l'ajout d'une tâche, l'insertion d'une
  ligne nommée, avec catégorie et quantité) restent sur le faux back ; leurs jumeaux
  `@shared` de `remaining.spec.ts` les rejouent contre le service sur un projet de la course porté
  En cours (`bringInProgress`, US-1950, #2909). Celui qui lit — le filtre par poste — se joue des
  deux côtés (EP-09).
- `planning.spec.ts` — la lecture de la date de début de planning, de ses en-têtes « Démarrée le » et
  « Terminée le » se joue des deux côtés ; seule son écriture (`updateCostStructure`) reste sur le
  faux back, comme les autres écritures du témoin ci-dessus.
- `entry.spec.ts`, `computed.spec.ts`, `keyboard.spec.ts`, `paste.spec.ts`, `undo.spec.ts`,
  `grid.spec.ts`, `structure.spec.ts`, `workload.spec.ts` — le devis (US-1560, EP-07) et le plan de
  charge (US-1520) : les parcours qui écrivent se jouent contre le service sur un projet que la
  course crée, une phase, une tâche et une ligne écrites par l'API (`e2e/estimate-seed.ts`), et
  portent `@shared` ; ceux qui lisent le témoin de PRJ-001 En cours s'y jouent depuis US-1570/L3 (la
  lecture seule de la structure principale, `structure.spec.ts` ; les montants calculés et les dates
  des récapitulatives, `computed.spec.ts` ; la grille, ses indicateurs par lot, son filtre, son tri,
  ses colonnes et son clavier ; les quatre parcours du plan de charge). Ne se jouent pas, faute de
  ce que le service sert : le volume de 5 999 nœuds et ses marques, que seul le faux back porte
  jusqu'aux volumes d'**EP-13** (#2696) : l'ouverture et le défilement de la grille, ses fenêtres
  basse et étroite, son pli par niveau, et le défilement du clavier jusqu'à la six millième ligne
  (`grid.spec.ts`, `keyboard.spec.ts`). Les parcours sans étiquette du reste à
  engager de PRJ-001 ne se rejouent pas, le compte de la course n'étant pas contributeur de PRJ-001
  (#2193), et leur jumeau n'est pas toujours celui qu'on croit : le tri après une écriture de
  `grid.spec.ts` n'a pas de jumeau contre le service ; l'ajout d'une tâche ou d'une ligne de
  `structure.spec.ts` a le sien dans `remaining.spec.ts` (US-1950) ; le parcours d'`undo.spec.ts`
  n'écrit rien, il affirme l'historique indisponible, ce que dit le faux back, et le service est couvert par les
  trois parcours d'annulation `@shared` du même fichier (planning, ligne du devis, tâche
  supprimée). Le passage d'un projet En cours
  se joue : le devis de la structure principale en lecture seule contre PRJ-001
  (`structure.spec.ts`), et le chiffrage jusqu'au passage En cours (`pricing.spec.ts`) ; une ligne
  sous une tâche terminée, refusée, ne s'écrit que dans le reste à engager, la structure principale
  d'un projet En cours étant en lecture seule.
- `actual-costs.spec.ts` — les coûts réels (US-1620) : le fichier entier porte `@shared`. Les deux
  parcours qui lisent PRJ-001 — les lignes et leurs trois totaux, la date du dernier import, le
  journal, le tri et le filtre ; le nombre de lignes par page — lisent la tranche des coûts du
  témoin (US-1650/L2, plus haut), dont les montants et les imputations sont ceux que le service
  calcule. Le troisième, l'exclusion d'une ligne du témoin depuis la liste, reste gardé par
  `inService` : le compte de la course n'est pas chef de projet de PRJ-001 (#2193), l'exclusion
  écrirait le témoin, et nul EPIC ne le renverse ; le parcours qui écrit exclut une ligne qu'il
  importe. Les deux qui écrivent le font sur un
  projet que la course crée (`bringInProgress`, `importActualCosts` d'`in-progress.ts`, #2193) : aucun
  import, puis l'import d'une extraction suivi de l'exclusion d'une ligne, aux totaux relus (filtre
  compris) et à la date du dernier import.
- `remaining.spec.ts` — la grille du reste à engager et le Kanban (US-1640) : le fichier entier porte
  `@shared`. Le parcours qui écrit — une tâche démarrée et un jalon terminé au Kanban, les lignes de la
  tâche démarrée dans la grille, les non démarrées à la demande — se joue contre le service sur un projet
  que la course crée (`seedPlanning`, `bringInProgress`, #2193). Ceux qui lisent le témoin de volume
  (mille tâches, `NO_VOLUME_IN_SERVICE`, levé par **EP-13**), dont la couverture des risques qu'il
  lit, restent gardés par `inService` ; les gestes sur le Kanban du faux
  back, qui ne garde rien, et le sous-menu « Sous-projet » (`FAKE_BACK_KEEPS_NOTHING`) ne se rejouent
  qu'en faux back, leur équivalent contre le service étant le parcours qui écrit.
- `timelines.spec.ts` — la frise et le focus (WF-IHM-0100-A) se jouent contre le service depuis
  US-1570/L3 : les lignes du témoin donnent leurs calendriers de rôles aux tâches (#2594). Restent
  sans étiquette trois parcours qui écrivent sur le témoin de PRJ-001, dont le compte de la course
  n'est pas contributeur (#2193) : l'inscription d'une tâche à une chronologie (`:52`, sur le
  premier nœud du faux back, dont le jumeau `:415`, sur un projet de la course, joue le service), le
  suivi temps/temps d'un jalon inscrit (`:104`) et la création puis la suppression d'une chronologie
  (`:300`) ; nul EPIC ne les renverse. La navigation depuis le planning, l'export PNG, les deux
  sélections et l'inscription sur un projet de la course se jouent contre le service.
- `exchanges.spec.ts` — l'import en deux étapes de PRJ-001 (`:93`), qui lit les lignes qu'un rapport
  rejette et l'abandon : le service joue l'import d'un devis, exporté puis réimporté et confirmé,
  sur un projet de la course (`:321`, US-1550), dont le classeur n'a nulle ligne à rejeter ; le
  refus d'un fichier trop gros (`:163`), qui ouvre l'écran des imports de PRJ-001 dont le compte de
  la course n'est pas contributeur (#2193) ; les deux écrans qui mènent à l'écran des imports depuis
  le devis et le reste à engager (`:192`), qui ouvre l'écran des imports de PRJ-001 dont le compte de
  la course n'est pas contributeur (#2193) : il reste sans étiquette, comme le refus d'un fichier trop
  gros ; l'import d'un reste à engager se joue contre le service sur un projet de la course (`:451`),
  celui d'une extraction dans `actual-costs.spec.ts`, par l'API.
  L'export du planning, relu par l'import et confirmé, se joue contre le service sur un projet de la
  course (US-1430, #2683), comme l'export du reste à engager, réimporté en deux étapes et quitté
  pendant son application (`:451`, US-1630).
- `projects.spec.ts` — les parcours qui écrivent sur PRJ-001 ou y mènent par son planning : l'écran
  du projet, ses paramètres et son cycle de vie, la sortie, les sous-projets et les contributeurs,
  le lotissement (`FAKE_BACK_ONLY`) : le compte de la course n'est pas chef de projet de PRJ-001,
  par décision (#2193, option A), que nul EPIC ne renverse — ce que rejouent les jumeaux —, et le
  planning vers lequel mène sa page, que le service sert depuis EP-06, ne s'écrit pas non plus sous
  ce compte. Chacun a son jumeau, joué contre le service
  seul sur un projet que le compte crée (`SERVICE_ONLY`, `own-project.ts`) : paramètres, cycle de
  vie, sous-projets, lotissement, contributeurs (un second compte, inscrit par l'API puisque l'écran
  ne propose que les comptes du devis, WF-PRJ-0070-A ; la qualité de ce compte est changée par
  l'écran, puis relue après rechargement) et une sortie à Perdu depuis Chiffrage, relue. La lecture
  de PRJ-001 — la liste, les tris et les filtres de l'accueil, les listes de ses paramètres — se
  joue des deux côtés.

La définition de fini d'EP-07 se constate par des parcours contre le service, joués par le compte
« chef de projet » de la course : un projet chiffré par la grille puis passé En cours — la quantité
d'une ligne saisie, son montant calculé par le service, la révision marquée par le worker, désignée
pour référence, le code saisi (`pricing.spec.ts`, WF-INTF-0010-A, FBS-4.4), puis la lecture des
indicateurs de la révision marquée (`service/project-manager-indicators.spec.ts`, WF-INTF-0010-A,
FBS-4.8) ; un devis exporté en Excel, réimporté sans écart et confirmé (`exchanges.spec.ts`, FLX-03
et FLX-04) ; cinquante saisies d'une ligne annulées une à une puis rétablies dans l'ordre
(`undo.spec.ts`, WF-IHM-0110-A).

La définition de fini d'EP-08, qui clôt WF-INTF-0010-A, se constate par le parcours du même compte
(`service/project-manager-risks.spec.ts`, WF-INTF-0010-A, FBS-4.6, US-2650) : sur un projet qu'il crée
et porte En cours, il déclare un risque, chiffre son devis propre (une tâche et une ligne), le
réexamine, le déclare survenu — la tâche du worker suivie jusqu'à sa réussite —, prépare un avenant
et le contractualise, la fusion faisant de sa révision la référence. Les gestes de l'avenant
(`prepare`, `contractualise`) sont ceux d'`amendment-flow.ts`, que rejoue aussi
`amendment-service.spec.ts`. Les parcours de FBS-4.1 à 4.9 et de FLX-01 à FLX-07 se jouent tous
contre le service, dans la même course (`make e2e-service`), chacun dans son fichier : FBS-4.1
`revision-cycle.spec.ts` et `pricing.spec.ts` ; 4.2 `projects.spec.ts` ; 4.3, FLX-01 et FLX-02
`planning-service.spec.ts` et `exchanges.spec.ts` ; 4.4 `pricing.spec.ts` ; 4.5 `remaining.spec.ts` ;
4.6 `service/project-manager-risks.spec.ts` ; 4.7 `actual-costs.spec.ts` ; 4.8
`service/project-manager-indicators.spec.ts` ; 4.9 `revision-cycle.spec.ts` et `projects.spec.ts` ;
FLX-03 à FLX-06 `exchanges.spec.ts` ; FLX-07 `service/actual-costs-import.spec.ts` (l'extraction
des coûts réels déposée par l'écran des échanges, en deux temps, `analyseActualCosts` et
`applyReport` d'`in-progress.ts`, que joue l'écran ; les parcours qui écrivent sans en faire leur objet
l'importent par l'API, `importActualCosts`). Chacun cite son flux, et chacun des trois parcours
de WF-QUA-0050-A (chef de projet, manager, administrateur) le sien, dans le titre du test.
EP-08 n'a laissé aucune garde `inService` à lever dans ces listes : celles qui restent, et les
EPIC qui les lèvent, sont celles de la liste ci-dessous.

Les deux lecteurs d'un projet (`service/project-readers.spec.ts`, WF-ADM-0040-A) se jouent contre le
service seul : deux comptes locaux qui portent « Manager » et « Chef de projet », l'un lisant en
français et gardant toutes les colonnes, l'autre en anglais avec une colonne masquée, lisent le même
projet, ses contributeurs et ses révisions ; le premier le crée et ouvre une révision par les
écrans, et inscrit l'autre par l'API sous son jeton.

**La liste des entrées non rejouées**, confirmée telle quelle à la clôture d'EP-08 (US-2650), par l'EPIC qui retire
la garde et l'entrée ci-dessus :

- **EP-11** — l'ouverture, depuis `/`, du portefeuille de `navigation.spec.ts`.
- **EP-13** — les volumes : le projet de 5 999 nœuds et ses marques (`NO_VOLUME_IN_SERVICE` de
  `revisions.spec.ts` et de `remaining.spec.ts`, l'ouverture et le défilement de la grille, ses fenêtres
  et son pli, le clavier jusqu'à la six millième ligne), les trois cents projets et les dix-huit mille
  lignes de coût du §4.6.2, et l'écran d'état du système.
- **Aucun EPIC ne les renverse** — les parcours qui écrivent PRJ-001, dont le compte de la course n'est
  pas contributeur (#2193) : leurs jumeaux jouent le service sur un projet de la course
  (`FAKE_BACK_ONLY`, `FAKE_BACK_KEEPS_NOTHING`, `NOT_REPLAYED_IN_SERVICE`, `WITNESS_KEPT`), ceux qui
  saisissent ou collent dans le devis propre d'un risque ou dans la douzième ligne du devis, la provision
  d'un risque (`entry.spec.ts` et `paste.spec.ts`, non étiquetés ; leurs jumeaux `@shared`, en fin de
  chacun des fichiers, jouent la provision d'un risque identifié et le collage dans son devis propre
  sur un projet de la course), le parcours de `risks.spec.ts` qui identifie, réexamine et déclare
  survenu un risque de PRJ-001 (ses jumeaux sont dans `risks-service.spec.ts`, sur un projet de la
  course : identification, réexamen, devis propre saisi, survenance), les
  parcours sans étiquette du reste à engager (`undo.spec.ts` : fond mémoire sans historique, le service
  étant couvert par ses parcours d'annulation `@shared` ; `grid.spec.ts`) et l'écran des imports de PRJ-001
  (`exchanges.spec.ts`), qui ne fait que lire cet écran : le parcours `@shared` d'export et de
  réimport du reste à engager couvre un autre geste, sur un projet de la course.

La tranche des coûts rend les coûts réels, leur journal et l'exclusion jouables ; elle compte,
depuis EP-08, les provisions, les avenants et les risques ; EP-13 y ajoute les volumes entiers.

Ne se rejouent pas contre le service, faute d'être étiquetés, les parcours qui dépendent de ce qu'il
ne fait pas encore ou ne sert pas ; chacun reste joué contre le faux back, par `chromium`. Ce qui
dépend de l'horloge : rien dans le référentiel, dont les dates sont celles du chargement
(WF-DAT-0070) et que les parcours n'attendent pas. D'un écran que le service ne sert pas :
l'ouverture, depuis `/`, du portefeuille de `navigation.spec.ts`, levée par **EP-11**. L'état du
système, servi par EP-13 (`getSystemStatus`, #2307), se lit et s'ouvre des deux côtés, comme
l'administration, sous `@administration` (le compte de la course n'y porte pas le rôle « Manager » mais
« Administrateur (parcours) ») : les parcours d'`admin.spec.ts` qui lisent sont
`@shared @administration`. Ne se rejouent pas ceux d'`admin.spec.ts` qui écrivent — les sauvegardes
(lancer, garder, restaurer), l'horaire des sauvegardes, les comptes et les rôles : chacun écrit un
objet unique de l'installation, ou demande `users.write` ou `access_roles.write`, que le compte de
`@administration` n'a pas, et que les parcours de `frontend/e2e/service/` (`backups.spec.ts`,
`accounts.spec.ts`, `roles.spec.ts`, et `administrator-path.spec.ts`, qui porte WF-INTF-0030-A)
éprouvent sous l'administrateur de l'installation. L'accueil
est servi depuis US-0920/L2 et se joue des deux côtés (`projects.spec.ts`, et l'icône de l'onglet de
`navigation.spec.ts`), de même que les écrans d'un projet depuis US-1000 (dont, dans
`navigation.spec.ts`, le passage des paramètres au cycle de vie). Depuis EP-08, se joue des deux côtés, dans
`navigation.spec.ts`, le retour au projet précédent depuis une fonction hors projet, qui rouvre le
reste à engager puis les risques de PRJ-001, qu'il quitte par
les paramètres de coûts, le portefeuille étant celui d'EP-11 ; l'adresse du projet
qui mène à son planning, avec son contexte de lecture, se joue des deux côtés depuis EP-06. De ce
que leur US n'étiquette pas encore : la lecture des réglages hors projet (`reference-costs.spec.ts`,
US-0250). La modification des unités de durée (`reference-resources.spec.ts`), qui écrit l'objet
unique de l'installation, se joue en `@serial` dans le projet `shared-serial`, comme les autres
parcours qui écrivent un objet unique. Les gardes `inService` des parcours étiquetés ne sont pas des
parcours non rejoués : le parcours se joue des deux côtés, et seule l'assertion d'une écriture
diffère (ce qui a été saisi, relu après un rechargement ; un code et un libellé propres à la course,
que le service garde ; un état laissé comme on l'a trouvé) — `reference-costs.spec.ts`,
`reference-resources.spec.ts`, `reference-settings.spec.ts`,
`reference-actual-cost-mapping.spec.ts`.

Un parcours `@shared` n'écrit que des objets qu'il crée lui-même, sous un code et un libellé propres
à la course, et les laisse désactivés ou retirés à sa fin : les workers `shared` jouent en parallèle
contre une même installation, et un objet du témoin qu'un parcours modifie, même le temps de son
déroulement, change sous les yeux de ceux qui le lisent ou le comparent à ses exemples (état,
`lock_version`, dates d'audit — #2087). Les parcours qui modifient un objet unique de l'installation
— les réglages, les unités de durée, la correspondance des coûts réels — portent l'étiquette
`@serial` à côté de `@shared` : le projet `shared-serial` les joue seuls, sur un worker, après
`shared` et avant `realm` et `restoration`, et `shared` les laisse (`grepInvert`) ; ils affirment
leur relecture par `inService` comme les autres (#2211). Un parcours qui doit en réactiver un du
témoin le fait dans un `finally` qui le remet comme il l'a trouvé, et c'est une exception qu'il dit,
non la règle.

L'attente du verrou des rôles composés (`giveRoles`, `ROLES_WAIT`) est de 25 s, sous les 30 s d'un
test : son message dit le verrou et le nombre de workers qui font la queue derrière lui (#2214).

Les corps qui ne sont pas du JSON traversent le mandataire du contrat octet pour octet (US-1550/L7,
#973, #1025, #2687, #2695). Prism lit tout corps comme du texte et réécrit chaque octet au-delà de
`0x7f` en U+FFFD ; deux jambes de `frontend/bench/contract-proxy.ts`, que le Node de son conteneur
lance, l'entourent : l'entrée, sur le port publié, garde les octets d'une requête dont le corps
n'est pas du JSON et en donne à Prism une copie sans le bit de poids fort, de même longueur ; la
sortie, où Prism transmet, envoie à l'API les octets gardés, et garde ceux d'une réponse qui n'est
pas du JSON, que l'entrée rend au front à la place de ceux que Prism a réécrits. Une réponse de
Prism en JSON — son refus — passe telle quelle ; une réponse qui n'est pas du JSON et ne nomme plus
d'octets gardés est refusée par un 502, jamais rendue réécrite. Chaque échange passe donc encore par
Prism, confronté au contrat et écrit à son journal ; le Content-Type de la requête et celui de la
réponse décident chacun pour leur corps, le téléchargement d'un classeur étant un GET sans corps. Le
fichier vit dans le front pour que son lint, son typage et ses tests le tiennent ; la garde du
réseau d'ESLint laisse `frontend/bench/` seul appeler le réseau hors du client engendré. Son test,
`frontend/bench/contract-proxy.test.ts`, le place entre de vrais serveurs `node:http` — un faux
Prism qui réécrit les corps comme Prism et une fausse API — et prouve l'aller-retour octet pour
octet, le JSON et les refus de Prism rendus tels quels, l'échec des octets gardés trop longtemps ou
dont le nom ne revient pas, vingt échanges à la fois, et une archive de plus de 5 Mio coupée en
parts sur un octet de continuation (#2695). Sur le service, le classeur exporté se réimporte tel
quel (`exchanges.spec.ts`), le parcours de l'avatar de `service/account.spec.ts` compare l'image
relue à celle déposée, et `backups.spec.ts` compare chaque vidage de l'archive téléchargée à
l'empreinte que donne son manifeste, la dépose, voit le service l'accepter avec sa date, puis
restaure la sauvegarde de la liste (WF-ADM-0160) ; l'archive d'une installation neuve (environ 0,5
Mio) part en une seule part, et la coupure en parts n'est prouvée que par le test des jambes. La
restauration d'un dépôt reste prouvée par les tests du service (`backend/tests/test_uploads.py`).
Écartés : envoyer ces échanges directement à l'API, ce qu'un GET ne permet pas de décider avant sa
réponse et qui les soustrairait au contrat ; un correctif des sources compilées de Prism, à refaire
à chaque version.

La seconde du §4.6.2 — ouvrir une grille de mille tâches — se mesure dans
`frontend/e2e/opening.spec.ts` (US-0110, US-0220), sur la structure de volume que sert le faux back,
pour la grille de devis et pour celle de planning ; le faux back sert le planning sans tenir compte
de `kinds=task`, et sa mesure est pessimiste : elle porte sur six mille lignes, et non sur les mille
tâches que le service rendra. Une ouverture va de son début — le début de la navigation pour une
grille ouverte par son adresse, le clic pour une grille ouverte depuis la barre latérale — jusqu'à
la grille utilisable, c'est-à-dire dessinée et hydratée : dessinée, la première image où l'en-tête
de ses colonnes, la légende de ses totaux et la première ligne de la réponse sont entièrement dans
la fenêtre ; hydratée, la première image où la grille entière est rendue par React — le serveur en
rend le premier écran, qui peut s'afficher avant qu'un clic n'y fasse rien —, que le parcours
reconnaît aux clés que React pose, en l'hydratant, sur le dernier élément de la grille, la dernière
cellule de ses totaux (`__reactProps$…`) : un détail interne de React, lu par le test seul. Le plus
tardif des deux instants se compare à la seconde. Un script remis à chaque document guette chaque
image et note les instants sur l'horloge du système (`performance.timeOrigin`), qu'un document
remplacé ne perd pas : ni les allers-retours de Playwright ni son attente n'y comptent. Elle se joue
contre le front construit pour la production, celui des parcours, et jamais contre le serveur de
développement, même sous `E2E_DEV_SERVER=1` : celui-ci compile une route à sa première demande et
rend avec les contrôles de React en développement — il dirait la vitesse du poste du développeur.
Avant chaque série de cinq ouvertures — cinq par l'adresse, cinq depuis la barre latérale, pour
chaque grille —, une ouverture n'est pas mesurée : le premier chargement des modules du serveur ne
compte pas, et le cache du navigateur est chaud, comme pour un utilisateur qui a déjà ouvert
l'application. Chaque ouverture ne commence qu'une fois la précédente entièrement servie,
préchargements compris — la grille hydratée, ses liens de la barre latérale demandent encore au
serveur les écrans où ils mènent, et une navigation lancée avant leur réponse les couperait pendant
que le serveur les rend, dans le temps de l'ouverture suivante — : le parcours suit les requêtes de
la page, qu'elles partent d'un document nouveau ou d'une navigation dans la même page, et attend,
hors de la mesure, qu'aucune ne soit en cours depuis une demi-seconde, en quinze secondes au plus ;
le journal écrit combien étaient en cours au départ de chaque ouverture mesurée, et il n'en faut
aucune. Chaque ouverture se compare à la seconde, sans arrondi ; le journal du parcours, et le
résumé du travail dans la chaîne, sous le titre « The second of §4.6.2 », écrivent la médiane et la
pire, utilisable, dessinée et hydratée, et, pour l'ouverture par l'adresse, où va le temps : les
instants médians où le serveur a fini d'envoyer le document et où le navigateur l'a lu. **La mesure
ne fait rien échouer sur la seconde** : une ouverture qui la dépasse est un avertissement — du test,
et de la chaîne —, jamais un échec, ni de `make e2e`, ni de la chaîne, ni de la file de fusion.
Contre le faux back, pour un utilisateur seul, sur une machine partagée de la chaîne, elle ne dit
pas ce que tiendra le service : ses chiffres variaient d'un run à l'autre du simple au double sur
une même révision. C'est un écart déclaré d'US-0110 et d'US-0220 ; la seconde se tient, bloquante,
en EP-13, sur le jeu de référence, avec cinquante utilisateurs, contre le vrai service. Le parcours
garde seulement des bornes de fonctionnement, loin de la seconde, qui ne mesurent rien : quinze
secondes pour qu'une grille devienne utilisable et qu'une page se pose (`WORKING`), les cinq
secondes de Playwright pour chaque assertion : l'adresse après un clic, puis ce que la grille montre
; trois minutes pour chaque test. Passé l'une d'elles, le parcours ne fonctionne plus — une grille
jamais utilisable, une page qui ne se pose jamais — et il échoue, quelle que soit la seconde. Le
parcours vérifie enfin que le document ne porte aucun champ d'un nœud que la grille ne lit pas
(`lineage_id`). Son projet Playwright, `measure`, dépend du projet `chromium` : il tourne après tous
les autres parcours, seul sur la machine — et ne tourne pas quand l'un d'eux échoue —, et sans
trace. Dans la chaîne, au palier complet, elle tourne seule sur un runner à elle, à côté des
morceaux des parcours (« Chaîne ») : `make e2e-measure`, qui ne démarre que le faux back et le front
construit — le harnais n'en réutilise aucun —, et que l'échec d'un parcours n'empêche plus. Sur un
poste, `make e2e` la joue après les parcours, et `make e2e-measure` seule. `E2E_PART` dit au harnais
ce qu'il joue : `paths`, les parcours sans la mesure, que `make e2e SHARD=i/N` pose ; `measure`, la
mesure seule, que pose `make e2e-measure` ; `service`, les parcours contre le service seuls, que
pose `make e2e-service` et qui exige `WATERFALL_API_ADDRESS` ; absente, le tout, sans les parcours
contre le service. Sans elle, Playwright ne saurait pas répartir les parcours : la mesure, qui les
attend tous, les entraînerait tous dans chaque morceau.

Le projet `measure` mesure aussi ce que coûte au navigateur de quitter une grille de mille tâches
(`frontend/e2e/departure.spec.ts`, US-0800) : le planning, ouvert hydraté et posé, quitté pour
l'écran des révisions par le lien de la navigation, le processeur de la page ralenti quatre fois,
le ralentissement sous lequel #1218 avait mesuré ce départ. Le travail est celui du fil principal
de la page, que Chromium compte lui-même (`Performance.getMetrics`), du clic à l'écran atteint,
moins celui de Playwright ; il se ventile en script, styles, mise en page et travail natif. Cinq
départs sont mesurés après un qui ne l'est pas, et leur médiane doit tenir sous une seconde :
celle-ci fait échouer le parcours, avec une marge de cinq contre un sur un poste, où l'ouverture
mesure ce qu'elle mesure dans la chaîne. Les fichiers du projet se jouent l'un après l'autre
(`workers: 1`) : chacun pèserait sur ce que l'autre mesure. `opening.spec.ts` dit en outre, à
part, ce que le faux back met à servir l'exemple des lignes que lisent les grilles (`listNodes`,
mille tâches et leurs lignes), demandé directement, hors de toute ouverture : la part de Prism dans
une ouverture, que le service ne paiera pas. Mesurée, jamais confrontée à rien (US-2210).

**La mesure du parcours des grilles contre le service** (US-2210, `make measure`,
`frontend/e2e/measure/`) joue sur PRJ-001 le parcours des grilles : ouvrir le planning par son
adresse, passer au devis par la navigation, le filtrer par un lot, le trier, le chercher, passer au
reste à engager puis au planning, saisir un libellé, puis une durée qui redate sa tâche. Chaque
étape va du geste — le début de la navigation, le clic, la touche Entrée qui envoie — à la grille
utilisable, dessinée et hydratée, selon la définition de la mesure de la seconde, dont les fonctions
vivent dans `frontend/e2e/usable.ts` ; une grille changée sur place l'est quand elle ne lit plus,
montre ce que le geste demandait — l'adresse de la lecture, la cellule écrite — et, pour une
écriture, quand son action serveur a répondu. Le temps de l'étape se partage en trois : l'API, lue
dans son journal (`duration_ms`, l'acteur) et rapprochée de l'étape par le compte de l'utilisateur
et la fenêtre de l'étape — le front ne transmet aucun identifiant de corrélation —, l'horloge de
l'API recalée une fois sur une requête de santé à l'identifiant de corrélation propre ; Next, par
différence, le temps où le serveur de Next répondait au navigateur — document, arbre de composants,
action serveur, préchargement demandé avant l'étape et qu'elle attend — ou l'API à Next, moins
celui de l'API ; le navigateur, le reste. Le poids de la réponse est ce que Next a envoyé au
navigateur pour l'étape. Temps de Next et poids retiennent les mêmes requêtes : pas les
préchargements que l'étape lance elle-même pour un autre écran, qu'elle n'attend pas — leur
temps est celui du navigateur, qui travaille pendant ce temps — ; celui qu'elle lance pour l'écran
où elle finit — même chemin et même requête (filtre, tri, recherche) —, quand le routeur le demande
de nouveau, elle l'attend, et il compte ; un préchargement du même chemin sous une autre requête
sert une étape à venir, et ne compte pas. La part de
l'API ne compte les requêtes du compte que pendant une requête de Next que l'étape attend : celles
d'un tel préchargement hors d'elle ne comptent pour rien. Limite : celles qui sont faites pendant
elle restent, le journal rattachant une requête à un compte et à un instant, non à la requête de
Next qui l'a faite. Le navigateur n'appelle jamais l'API lui-même (ses composants passent par
des actions serveur) : une telle requête, hors de Next, tomberait dans la part du navigateur. Un
poids de 0 à côté d'une API qui a répondu n'est pas un téléchargement qui n'a pas eu lieu : sous
charge, une étape attend une requête que le routeur a coupée (un préchargement qu'une navigation
reprend, que Playwright dit échoué) ou dont les tailles ne sont jamais venues, et ses octets sont
inconnus. Une telle requête est marquée `weighed: false`, l'étape la compte (`unweighed`), le poids
de son échantillon reste hors de la statistique — ses temps restent — et le journal du passage dit
combien d'échantillons ont été écartés. Le rapport de l'étape porte ce nombre (`unweighed`) et
rend `bytes` à `null` quand aucun échantillon n'a de poids : ni un 0 qui se lirait comme un
téléchargement qui n'a pas eu lieu, ni un silence. Une étape servie par le cache du routeur, sans requête,
n'a pas non plus de temps d'API. Le
parcours se
joue à un, quatre et huit utilisateurs à la fois (`MEASURE_USERS`, qui nomme toujours `1` : seul un utilisateur seul fait échouer la mesure), un compte chacun, chacun dans
son contexte de navigateur, et la durée de `getMe` est relevée pendant ce temps, dans le journal de
l'API et par un client qui la demande chaque seconde, avec un compte à lui, sans rôle, qui ne joue
pas le parcours et dont les requêtes n'entrent dans aucune étape ; ses demandes sans réponse de
succès sont comptées (`lost`). Les comptes sont créés par la préparation de
la mesure, par les opérations du contrat, jamais par un `INSERT` : l'administrateur de
l'installation crée chaque compte, donne son lien et ses rôles « Manager » et « Chef de projet » ;
puisque les chefs de projet du témoin n'ont pas de mot de passe, il les désactive le temps que le
premier utilisateur, détenteur des paramètres de projets et de « voir tous les projets », inscrive
les utilisateurs de la mesure en chefs de projet de PRJ-001 — la seule inscription que le contrat
ouvre à un non-contributeur —, puis les réactive. Leurs connexions, la remise à leurs réglages par
défaut des grilles de chaque compte et la recherche des tâches qu'ils écrivent, une chacun, en mode
automatique, non démarrées et éloignées l'une de l'autre, sont hors de la mesure. Chaque niveau
joue un passage non mesuré, puis cinq (`MEASURE_PASSES`) ; le rapport, un JSON
(`frontend/.e2e/measure.json` par défaut, `MEASURE_REPORT`), dit pour chaque niveau et chaque
étape le nombre de mesures et d'étapes inachevées, puis la médiane, la pire et la dispersion —
l'écart entre la plus haute et la plus basse des médianes d'un passage, absente (`null`) quand
moins de deux passages ont une mesure, où elle dirait 0 comme un passage stable — de la durée, de ses trois parts,
des octets de Next et des requêtes de l'API ; et de même pour `getMe`. Chaque médiane se prend
sur sa grandeur : la médiane d'une part n'est pas la part de l'étape médiane, et les médianes des
trois parts ne somment pas à celle de la durée. Sa forme est déclarée par
`MeasureReport` (`frontend/e2e/measure/report.ts`), dont les calculs ont leurs tests unitaires ; il
ne dit jamais un écart un gain. La mesure n'échoue sur aucune durée : seul un parcours qui ne
fonctionne plus la fait échouer — un compte qu'elle ne peut créer, un utilisateur qu'elle ne peut
connecter, ou une étape qu'un utilisateur seul ne mène pas à sa fin : un lien renommé, une grille
qui ne s'affiche plus ; la mesure échoue alors à la fin, une fois le rapport écrit, en nommant ces
étapes. À quatre et huit utilisateurs, une étape qui n'atteint pas sa fin est le fait de la
charge : elle est comptée inachevée, et ne fait rien échouer. Le front est construit
pour la production et parle à l'API directement, sans le proxy du contrat, en gardant ses connexions
comme le front des utilisateurs ; la plateforme est démarrée, amorcée et le témoin chargé comme pour
`make e2e-service`. `make measure` prend le poste pour elle seule, une fois le front construit
(`$(exclusive)`, « Le poste pour une mesure seule ») : elle attend la fin des exécutions lourdes en
cours, retient les suivantes, et part d'un témoin fraîchement chargé — la plateforme est arrêtée et
ses données supprimées (`service-down WATERFALL_RESET_DATA=yes`), puis redémarrée, amorcée et le
témoin chargé —, parce qu'un témoin qu'on ne recharge pas cumulerait d'une mesure à l'autre les
comptes inscrits sur PRJ-001 et les durées saisies, qui redatent le planning mesuré ensuite. Une
mesure retient donc les exécutions lourdes des autres livreurs dix à quinze minutes : elle se joue
une fois réussie, non en boucle. Le projet Playwright `measure-service` n'existe que sous `E2E_PART=measure-service`, que
pose `make measure` seule : aucune cible de la chaîne ne le joue, et les autres projets laissent
`frontend/e2e/measure/` de côté.

**La référence, et le gain d'un lot** (US-2210/L4, EP-26). `docs/measures/reference.json` est la
mesure d'avant toute correction des grilles, prise sur les écrans que la branche d'EPIC portait
alors, par `make measure-core` et `make measure` (un, quatre et huit utilisateurs, cinq passages)
dans la même session, que `make measure-reference CORE=<JSON de measure-core> JOURNEY=<JSON de measure>` assemble. Il garde tel quel ce que les deux outils écrivent — `core`, le JSON de
`make measure-core`, et `journey`, celui de `make measure` — sans durée retouchée, et ajoute
`targets` : la cible de l'API pour ouvrir une grille de devis et une grille de planning, en
millisecondes (`api_target_ms`), soit la seconde du tableau 15 (§4.6.2) moins les parts de Next et du
navigateur de l'étape, médianes pour un utilisateur seul ; US-2220/L1 et US-2280/L1 la lisent. Leurs
clés : `targets.api_target_ms.planning` et `targets.api_target_ms.estimate` (millisecondes), et
`targets.from`, qui nomme pour chacune l'étape source — celle du planning est `planning.by-address`,
celle du devis `estimate.from-planning`, la navigation depuis le planning. L'en-tête dit aussi le
commit d'`epic/EP-26` sur lequel la mesure a été prise (`commit`, `MEASURED_COMMIT=` pour en nommer un
autre que la base du lot) et sa date (`taken_at`, celle du parcours).
C'est la référence d'avant correction, non un rapport de version : les rapports de
version, `docs/measures/<version>.json`, sont ceux qu'US-2300 confronte, et ils ne reprennent pas
ce fichier. Un lot de correction du back mesure son gain par `make measure-core`, avant et après
lui, dans le même passage exclusif — deux mesures de suite, sans que rien ne les sépare sur le
poste — et l'écrit dans sa pull request, les médianes et la dispersion de chaque ; un écart sous la
dispersion n'est pas un gain. Le parcours entier ne se rejoue qu'à quatre moments : la référence, le
réglage des processus (US-2230), les bornes des parcours (US-2290) et le rapport de la version
(US-2300).

Le parcours témoin — liste des projets, projet, grille — traverse trois pages minimales,
sans texte propre, qu'EP-02 remplace en gardant le parcours. Elles lisent l'API côté
serveur (`frontend/src/api/server.ts`) ; leurs tests unitaires reçoivent les exemples du
contrat par `frontend/src/test/fixtures.ts`, les mêmes données que sert le faux back.

L'accessibilité minimale de chaque écran (US-0200, WF-IHM-0100) se contrôle dans
`frontend/e2e/accessibility.spec.ts`, sur les écrans de `frontend/e2e/routes.ts` : ceux de la table
de `functions.json`, que lit aussi `screens.spec.ts`, et ceux qu'aucune table ne nomme — le projet
lui-même, les pages du compte, la connexion et le mot de passe oublié, l'écran « introuvable ».
`frontend/src/app/screens.test.ts` (`make test-front`) confronte chaque page de `frontend/src/app`
à ces écrans et aux pages qui ne font que rediriger (`REDIRECTS`) : une page ajoutée sans son écran
le fait échouer, comme une page de `REDIRECTS` qui ne fait pas que rediriger, ou une route qui en
intercepte une autre. Chaque écran s'ouvre par son adresse dans une fenêtre de 1366 × 768 points,
hydraté (`untilHydrated`, qui attend les clés que React pose sur chaque élément qu'atteint le
clavier — ceux que le parcours atteint, un seul sélecteur, `REACHABLE`, partagé avec la sonde du
focus), puis se rétrécit à 911 × 512 — ce qu'un agrandissement de 150 % laisse de 1366 points, la
page remise en page comme le navigateur la remet quand on agrandit ; un facteur d'échelle de
l'appareil changerait les pixels, pas la mise en page. Trois contrôles par écran, joués chacun
en mode clair et en mode sombre (`colorScheme`) — six tests —, portent chacun sur les deux
largeurs :

- les règles d'axe pour WCAG A et AA (`axeAudit`, `frontend/e2e/axe.ts`) — axe n'est pas WCAG —,
  contraste compris, une fois en mode clair et une fois en mode sombre (`colorScheme`), chaque test
  constatant d'abord le mode peint — aucun `data-theme`, le fond de la charte. Un texte qu'axe
  laisse « incomplet » avec ses deux couleurs mesurées et une mesure qui échoue — un seul caractère
  sous le rapport attendu, qu'il ne veut pas appeler un texte, ou un texte de la couleur de son fond
  — est un écart, ses couleurs dites ; ce qu'axe laisse sans mesure (`unmeasured`), le test le note
  en annotation, raison par raison (`elmPartiallyObscured`, `bgOverlap`…), les figures de courbe à
  part — un caractère seul dont axe n'a pas mesuré les couleurs y compte sous sa brièveté, axe
  l'écrivant par-dessus la raison qui l'a empêché de mesurer. Ce que les autres règles laissent «
  incomplet » — une cible trop petite, un lien dans un texte qu'axe ne sait pas juger… — est noté de
  même, règle par règle, sans verdict (`undecided`, #784). En mode clair, les règles des libellés
  des champs et des descriptions des images — `label`, `image-alt` et leurs parentes — sont dites à
  part ;
- le parcours au clavier (`walkByTab`, `frontend/e2e/tab-walk.ts`, la mesure dans la page par
  `frontend/e2e/focus-probe.ts`), dans les deux modes, l'indicateur du focus peint dans chacun
  (#784) : à 1366 points, Tab depuis le haut de la page, à 911 points depuis là où le premier
  parcours s'est arrêté, chaque fois jusqu'au retour au premier élément atteint. Chaque élément
  atteint est vu — affiché, non transparent, et le milieu de ce qui en reste — de sa première boîte,
  pour un lien replié sur deux lignes, dont la boîte englobante a son milieu entre les deux (#784)
  —, coupé par la fenêtre et par la boîte de remplissage de chaque boîte qui le rogne le long de ses
  blocs conteneurs, est l'élément lui-même : rien qui peigne n'est dessiné par-dessus, une couche
  que le pointeur traverse comprise —, et rien d'autre n'y prend le pointeur, une couche
  transparente qui capte les clics comprise (`covered`). Il porte un indicateur du focus : un
  contour ou une ombre qu'il ne portait pas avant le parcours, quand rien n'avait le focus — ou,
  pour un élément né depuis, qu'il ne porte plus une fois quitté ; un élément né depuis et disparu
  une fois quitté ne se juge pas, et se dit (`unjudged`) —, non transparent, un côté au moins hors
  de ce que coupent les boîtes qui le rognent et, à l'intérieur, pas sous ce qui le recouvre : ce
  que l'élément contient pour une ombre intérieure, un élément positionné pour un contour. Un
  élément atteint deux fois avant le retour au premier est un piège, comme un élément qui garde le
  focus d'un Tab à l'autre plus longtemps qu'un champ fait de champs — le jour, le mois et l'année
  d'une date. Chaque élément que Tab peut atteindre — affiché, actif, d'ordre clavier non négatif —
  doit être atteint lui-même, ou, pour un widget qui déplace lui-même le focus (grille, arbre, menu,
  liste, groupe de radios, onglets, barre d'outils), le focus doit entrer en lui ; chacun de ces
  widgets doit être entré (`stopless`) ; aucun élément ne doit se trouver entier au-delà du bord
  d'une boîte qui cache ce qui la déborde, que le navigateur fait défiler au focus mais que le
  pointeur n'atteint pas — une boîte que l'utilisateur fait défiler n'est jamais un bord : ce
  qu'elle cache, elle le montre en défilant, et c'est elle qui doit être dans les boîtes autour
  d'elle ; ce qu'elle montre reste jugé contre elles ; aucun lien ni bouton — ni rien qui en dise le
  rôle, ou celui d'une case à cocher (`[role=button]`, `link`, `checkbox`) — n'est sorti de l'ordre
  du clavier hors d'un tel widget. Enfin, tout ce que Tab atteint à 1366 points, il l'atteint encore
  à 911 (`lost`). Pour voir ce qui peint par-dessus un élément, le parcours fait prendre le
  pointeur, le temps de la mesure, aux seuls éléments qui ne le prennent pas et dont la boîte touche
  celle de l'élément ou de l'un de ses enfants — chaque point que la mesure demande au navigateur
  est dans l'une d'elles —, puis les rend tels qu'ils étaient ; il lit tous les éléments d'abord,
  puis écrit ceux qu'il a trouvés, jamais l'un après l'autre, `pointer-events` étant héritée. Une
  feuille posée sur tous (`* { pointer-events: auto }`) et retirée à chaque Tab faisait recalculer
  deux fois le style de la page entière — les trois cinquièmes du temps d'un Tab sur une page de
  deux mille éléments, et le parcours des rôles d'habilitation, plus de 350 Tab à chaque largeur, à
  84 des 90 secondes de son délai sous quatre workers, 69 une fois les seuls éléments sans pointeur
  changés, tous, à chaque Tab, 54 une fois changés ceux qui touchent l'élément (#1263). Le reste est
  celui de la page et des allers-retours : seul, chaque largeur du parcours occupe le navigateur 12
  de ses 16 secondes, 10 sans aucune mesure du pointeur. Le parcours presse Tab par lots (`BATCH`,
  seize touches) et lit d'un seul `evaluate`, après chaque lot, ce que la page a mesuré de chaque
  touche : il ne reste qu'un aller-retour par élément, celui de la touche, qu'impose le clavier ;
  une lecture après chaque touche en faisait un second, et le poste chargé en faisait passer le
  parcours des rôles au-delà de ses 90 secondes (#1540). La sonde entend chaque Tab à son `keyup` —
  le focus a bougé, ou il est resté, le piège que le parcours doit voir — et prend la mesure, par le
  même code, au moment où le parcours la prenait : quand la page entend de nouveau le parcours, la
  touche suivante avant qu'aucun écouteur posé par la page après la sonde ne la voie, ou la lecture
  du lot. `focusin` ne suffit pas : il ne se déclenche ni quand le focus reste, ni quand il quitte
  le document. Revenu au premier élément, la page cesse de mesurer, et les touches qui restent du
  lot n'atteignent ni les écouteurs posés par la page après la sonde ni le focus, si bien que le
  focus est revenu au premier élément quand le parcours suivant commence ; ce que la page a mesuré
  au-delà d'un piège n'est pas lu, ni compté dans ce que Tab n'a pas atteint. Le décompte des
  éléments atteints et des pièges reste du côté du test. Les tests qui parcourent au Tab — l'écran,
  et ce qu'un geste ouvre —, et eux seuls, gardent leur trace sans instantanés du DOM
  (`withoutSnapshots`) : un instantané par touche pesait plus que le parcours lui-même sous charge
  (#1540), et ses fautes se lisent dans ses relevés. `test.use({ trace })` ne vaut pas pour un seul
  test — un groupe refuse une option qui impose un nouveau worker : le test relance la trace que le
  harnais a ouverte, avec les mêmes options, sans les instantanés ;
- ce qu'un geste ouvre (US-0710, `frontend/e2e/opened.ts`) : sur chaque écran, les déclencheurs d'un
  dialogue ou d'un menu — `aria-haspopup="dialog"` ou `"menu"`, que pose chaque commande qui ouvre
  un dialogue et chaque déclencheur d'un menu —, affichés et actifs, reçoivent le focus et Entrée ;
  ceux de la coquille — projet, compte, tâches, aide : tout ce qui est hors de `main`, et le bouton
  de l'aide, que `data-shell` marque — ne se jouent que sur l'écran de référence, la liste des
  révisions d'un projet (US-1220, #1840) : ils sont les mêmes sur chaque écran, et les rejouer
  coûtait 38 à 67 % du chemin critique de la chaîne ; la première cellule saisissable de chaque
  grille — une cellule de `DenseGrid`, que `data-column` situe et que rien ne dit en lecture seule
  (`aria-readonly`) — reçoit le focus et F2. Un dialogue ouvert est parcouru au Tab borné à lui
  (`walkByTab(page, dialogue)`) : ce que Tab peut atteindre, les widgets et les bords se jugent dans
  le dialogue seul, le retour à son premier élément est le piège qu'il veut — un dialogue d'un seul
  élément le garde —, et tout élément atteint hors de lui est une faute (`escaped`). Un menu déplace
  le focus aux flèches et un éditeur valide au Tab : le test y vérifie que le focus est entré. Ce
  qui s'est ouvert est ensuite audité par axe — la cellule, pour un éditeur —, et le reste de la
  page par la seule règle dont l'ouverture change le verdict hors de lui (`aria-hidden-focus` : un
  menu ou un dialogue modal cache la page au lecteur d'écran) ; la page entière, que son propre
  audit juge, n'est pas auditée de nouveau à chaque ouverture, ce qui dépassait le délai d'un test
  sur le Kanban et le référentiel, huit secondes l'audit. Puis Échap le ferme et le focus revient au
  déclencheur, ou à la cellule — celle qui tient le déclencheur, pour une commande d'une ligne de
  grille. Les déclencheurs se découvrent à chaque largeur et se jouent l'un après l'autre dans un
  seul test par écran et par mode, chaque contrôle dit à part, nommé par le déclencheur et la
  largeur (`expect.soft`) ; une commande qu'une grille répète de ligne en ligne n'est jouée que pour
  la première ligne, et un contrôle en échec rouvre l'écran avant le déclencheur suivant.

`frontend/e2e/tab-walk.spec.ts` et `frontend/e2e/axe.spec.ts` éprouvent le parcours et l'audit d'axe
eux-mêmes, sur des pages écrites pour eux (`page.setContent`) : chaque défaut qu'ils doivent nommer
y est nommé, et ce qu'ils doivent laisser passer passe. Les outils du serveur de développement de
Next (`nextjs-portal`), que le front construit n'a pas, sont écartés d'axe et du parcours. Le
fichier se joue test par test (`mode: "parallel"`) : Playwright répartit ses tests un à un entre les
workers et les morceaux de la chaîne, et non le fichier en bloc ; chacun prend `test.slow()`, car il
ouvre un écran puis le contrôle deux fois, ce qui dépasse le délai par défaut sur un poste chargé ;
la compilation à froid d'un écran n'ajoute à ce temps que sous `E2E_DEV_SERVER=1`, le front
construit n'en ayant pas. Un écart relevé se corrige dans l'écran, jamais en écartant une règle.

Ce que le harnais ne prouve pas, et ce qui le couvre ailleurs (US-0200, US-0710 ; la note
d'US-0200 dans le fichier d'EP-14 le dit aussi) :

- ce qu'un geste ouvre sans déclencheur que le harnais joue : le Popover d'un refus — d'une cellule
  calculée, ou d'une écriture refusée —, qui ne s'ouvre qu'une fois le serveur a refusé ; un menu
  ou un dialogue ouvert depuis un menu — le menu d'une cellule (Maj+F10), et les dialogues qu'il
  ouvre, l'insertion d'une tâche par exemple — ; le collage d'un bloc, ouvert par Ctrl+V ; les
  dialogues qu'un geste ouvre sans bouton — `TimelineForm` et `GestureDialog` de
  `structure-gestures.tsx` —, que le harnais ne trouve pas faute de commande qui dise
  `aria-haspopup="dialog"` : le test `dialog-command-guard.test.ts` les exempte de la règle et les
  nomme (chaque entrée avec sa raison), et fait échouer toute autre source qui rend plus de
  dialogues pilotés par un état que de commandes qui le disent. Les tests de composants les
  tiennent (`expectAccessible`, axe sous happy-dom, sans contraste ni mise en page ; le focus que
  Radix rend) ;
- la coquille sur chaque écran : ses menus et ses dialogues (projet, compte, tâches, aide) ne se
  jouent que sur la liste des révisions d'un projet, en clair et en sombre, aux deux largeurs
  (US-1220) ; un défaut propre à la coquille d'un autre écran — un en-tête que la page change — ne
  se verrait qu'à son audit d'axe et à son parcours au Tab, qui, eux, se jouent sur chaque écran ;
- le panneau d'aide de chaque écran : il n'est ouvert et audité par axe que sur l'écran de
  référence de la coquille, la liste des révisions, ses pages partageant leur rendu — un seul
  composant, `ScreenHelp` de `help-panel.tsx`, une seule charte — ; le contenu de chaque page
  d'aide se relit ailleurs (`help.test.ts`) (#1985, option 1, décision de l'auteur du 2026-11-14) ;
- la liste ou le popover qu'un éditeur de cellule rendrait dans un portail hors de la cellule :
  l'audit d'un éditeur porte sur la cellule, et aucun éditeur d'aujourd'hui n'en rend un ;
- le contenu d'un `details` fermé — le tableau des valeurs d'une courbe — et un état qu'un geste
  atteint — un refus affiché, une adresse `?import=` — : le harnais ouvre chaque écran à son
  adresse, et n'y joue que les déclencheurs ;
- l'écran de panne (`error.tsx`, `global-error.tsx`), qu'aucune adresse n'ouvre : seuls ses tests
  le rendent (`system-pages.test.tsx`, et `expectAccessible` dans `system.dom.test.tsx`) ;
- dans un widget qui déplace lui-même le focus, l'entrée seule est vérifiée : atteindre chacun de
  ses éléments aux flèches reste aux tests de composants (#784) ;
- les textes qu'axe ne mesure pas : posés sur le dessin d'une courbe, du Gantt ou d'une chronologie
  — des images pour axe —, en partie hors de la boîte qui les fait défiler, sous un autre ; le test
  les compte en annotation, raison par raison, mais ce compte n'est comparé à rien : un texte qui
  devient non mesurable ne change aucun verdict (#784). Les textes indicatifs des champs
  (`placeholder`, la recherche de la barre du haut et celle d'une grille) ne sont pas jugés par
  axe : seule la paire de jetons `muted-foreground`/`background` de `contrast.test.ts` les couvre ;
- le contraste de l'indicateur du focus (WCAG 1.4.11), mesuré par les seuls jetons de
  `contrast.test.ts`, pas sur les écrans.

_Contrôle_ : `make e2e`, au palier complet de la chaîne ; l'échec d'un parcours la fait
échouer, une ouverture de grille qui dépasse la seconde n'y est qu'un avertissement.

### Couverture du code

La spécification ne demande que la couverture des exigences ; la couverture du code est une règle du
dépôt, qui trouve ce que la première ne voit pas — un chemin d'erreur jamais exécuté, du code mort.
Le back et le front doivent chacun couvrir **90 % des lignes et 85 % des branches** : les branches
comptent, parce qu'un `if` sans son `else` couvre toutes ses lignes et la moitié des cas. Le code
engendré en est exclu. Le client de l'API d'administration de Keycloak
(`waterfall.platform.keycloak_admin`), que seul Keycloak sert, la lecture des comptes du worker
(`waterfall.worker.identity_sync`), qui le demande à chaque pas, et l'amorçage
(`waterfall.bootstrap`), qui crée en lui le premier administrateur, sont mesurés par
`make test-keycloak`, aux mêmes seuils (`backend/coverage-keycloak.toml`), et écartés par leur
chemin de la mesure du back, `make coverage-back`, qui mesure tout le reste du back. Aucune ligne ne
s'exclut de la mesure par un commentaire ; une exclusion s'écrit dans la configuration, avec sa
raison (`[tool.coverage.report]` de `backend/pyproject.toml`, `coverage` de
`frontend/vitest.config.ts`). Un test qui passe sur des lignes sans rien vérifier est un défaut, que
la revue relève.

_Contrôles_ : `make coverage-back`, `make coverage-front`, au palier complet : ils nomment
les fichiers les moins couverts quand un seuil n'est pas atteint.

### Un test qui reprend un exemple chiffré

Chaque phrase chiffrée d'un champ Vérif est un cas de test du noyau, avec les mêmes entrées
et la même valeur attendue (WF-QUA-0020). `make fixtures` les relève dans
`fixtures/examples.json` — fichier engendré, qu'on ne retouche pas —, chacune sous une clé
faite de l'exigence et de l'empreinte de son texte : `WF-PTF-0020-A#ab12cd34ef56`.

Pour éprouver un exemple :

1. écrire une fixture sous `fixtures/`, un fichier JSON qui cite dans `examples` la clé de
   la phrase, et porte ses données, recopiées de la phrase ;
2. écrire le test sous `backend/tests/examples/` : la fixture `example` le charge par la
   clé, le test appelle le noyau et compare à la valeur de la phrase.

Un exemple du contrat (`fixtures/api/`) dont la valeur reproduit une phrase en cite la clé dans
`x-examples`, un Example Object d'OpenAPI n'admettant pas de clé `examples` ; un générateur la
passe à `mocktext.example`. `make check-fixtures` le compte comme les autres.

Les sockets y sont fermées : un exemple qui passe ne demande ni base, ni service, ni
navigateur. Une phrase modifiée dans le document change de clé ; la fixture de l'ancienne
fait alors échouer la chaîne, et on la réécrit d'après la nouvelle phrase.

_Contrôles_ : `make check-fixtures` — le relevé est à jour, chaque clé citée existe, et les
exemples qu'aucune fixture ne cite encore sont listés, sans échec : leur nombre décroît avec
les EPIC de calcul (EP-06 à EP-11).

## Enveloppe d'erreur et codes d'erreur

L'enveloppe est fixée par le contrat (`docs/api/README-fr.md`, WF-ARC-0110) : un code machine et
ses paramètres, jamais une phrase.

- **Un composant tombé côté back** — une base qui ne répond pas à une requête, parce que la connexion
  échoue ou se perd, que le serveur s'arrête ou démarre, ou que le réservoir reste pris au-delà de
  `POOL_TIMEOUT`, est refusée par le 503 `COMPONENT_UNAVAILABLE` qui nomme `database`, non par un 500
  (`is_unreachable` de `waterfall.platform.database`, lu par le middleware de la corrélation,
  US-2860) ; une instruction que le serveur a jugée — un verrou refusé, un interblocage — reste ce
  qu'elle était. Les autres composants se nomment là où ils sont atteints (`platform/storage.py`,
  `platform/keycloak.py`) ; les essais d'un composant arrêté à la fois, derrière une porte que le test
  ferme et rouvre (`backend/tests/degraded_platform.py`), sont dans `test_degraded_mode.py`.

- **Ajouter un code côté front** — un code nouveau est d'abord une modification du contrat
  (`ErrorCode`, `docs/api/components/common.yaml`), suivie de `make generate-client`. Le
  front lui donne sa phrase, `errors.<CODE>`, dans les deux catalogues : ce qui est refusé,
  sans rien de ce que les paramètres nomment. Un paramètre nouveau qu'un lecteur doit
  connaître reçoit la sienne, `problemDetails.<param>`, et sa lecture dans `DETAILS` de
  `frontend/src/i18n/problem.ts`, qui nomme une valeur codée — une permission, une
  condition — par son libellé du catalogue ; un paramètre qui ne dit rien à un lecteur —
  un identifiant, un compteur d'écriture — n'en reçoit pas. Un composant rend un refus par
  `problemMessage(problem, { locale, messages })`, jamais en écrivant la phrase.

  _Contrôles_ : `make typecheck-front` échoue sur un code d'`ErrorCode` sans clé dans le
  catalogue français, que `problem.ts` lit par `errors.${code}` ; `make catalogs`, sur un
  code sans clé dans l'un des deux, ou sur une clé `errors.` que le contrat n'a plus.

- **Réagir à un refus côté front** — une action serveur ne rend jamais la réponse brute de
  l'API : elle appelle le client par `decode` de `frontend/src/api/problem.ts`, le seul
  décodeur, et rend son `Outcome` — `done` ; `refused`, un `Problem` à dire tel quel ;
  `stale` (412) ; `conflict` (409) ; `signed_out` (401) ; `unreachable`, l'API qui n'a pas
  répondu du tout, distinct de tout `Problem` — le rejet de `fetch` lui-même, que
  `client.ts` marque `Unreachable` (une autre `TypeError` est un défaut et remonte), ou un
  502, 503 ou 504 sans enveloppe `Problem`, qu'une passerelle rend quand le service est
  tombé. Une réponse d'erreur sans enveloppe, ou dont le `code` manque au catalogue — un
  service plus récent que le front —, vaut `INTERNAL_ERROR`, « erreur inattendue », au
  statut reçu, avec le `correlation_id` de l'enveloppe quand il a la forme du contrat, que l'avis
  présente en référence (WF-OBS-0020, #2264) : l'écran n'affiche jamais une clé brute. Le composant le dit par
  `OutcomeNotice` (`frontend/src/components/commands/`), en alerte : la phrase de
  `problemMessage`, qui nomme aussi les objets que le refus ne donne que par leurs identifiants
  quand l'écran les a lus (`names`) ; les lignes ou les projets nommés au-delà de la phrase, hors de
  l'alerte et décrits par sa phrase (#765) ; sur 412, l'offre de recharger l'écran ; l'objet en
  conflit (`params.conflicting_object_id`, ou à défaut celui du premier refus par champ qui en nomme
  un, `fields[].params.conflicting_object_id` d'un 409 `ALREADY_EXISTS` — `conflictingOf` de
  `frontend/src/api/problem.ts`) nommé quand l'écran le connaît, par `names`, ou à défaut par le
  libellé que le refus lui donne (`conflicting_object_label`) — un projet, un sous-projet que
  l'écran ne montre pas, dont le code pris revient le dialogue fermé (#714) ; sur 401, le lien vers
  la connexion ; l'API injoignable annoncée, jamais un écran blanc ; l'erreur inattendue avec sa
  référence (`correlation_id`), comme l'écran de panne. Une action serveur
  dont la promesse est rejetée n'a rendu aucun `Outcome` : le composant le tient par `rejected`
  (`frontend/src/components/commands/rejection.ts`), une règle pour tous les écrans (#330) —
  une `TypeError` est l'API injoignable : c'est ce que lève le `fetch` du navigateur rejeté, et
  le navigateur ne la distingue pas d'une `TypeError` levée ailleurs, qui passe donc aussi pour
  « injoignable » ; tout autre rejet se classe par son `digest`, comme l'écran de panne le classe
  (`failureOf`) — l'API injoignable, la session perdue avec le lien vers la connexion, ou
  l'erreur inattendue avec sa référence, celle-ci gardée seulement si elle a la forme d'un
  `correlation_id` du contrat. La connexion
  est `/login?next=<chemin et requête de l'écran visé>` (`loginHref`,
  `frontend/src/navigation/login.ts`) : la route de connexion (US-0320), la session rouverte,
  mène à `returnTarget(next)`, qui ne suit qu'un chemin du front — ni `//hôte`, ni une
  adresse d'un autre site — et ramène sinon à l'accueil. Un 401 `ACCOUNT_DEACTIVATED` n'y mène
  pas, il bouclerait : `kindOf` le range en `refused`, et une lecture lève `AccountDeactivated`.

  _Contrôles_ : `make test-front` (`problem.test.ts`, `login.test.ts`, `rejection.test.ts`) ;
  qu'une action serveur passe par `decode`, et qu'un rejet passe par `rejected`, la revue.

- **Ajouter un code côté service** — le code existe d'abord au contrat (`ErrorCode`), puis dans
  les modèles du service que `make generate-server-models` en engendre
  (`backend/src/waterfall/api/contract/models.py`, versionnés ; `make server-models-up-to-date`,
  dans `make check-contract`, échoue s'ils ne sont plus ceux du contrat). Une adresse y est un
  simple texte (`--type-mappings email=string`) : le service la rend telle qu'il la tient, et les
  modèles ne valident pas les adresses ; le noyau les valide selon la règle du contrat (#665,
  `is_address` de `waterfall.core.users.identity`). Le noyau lève ensuite
  l'exception de `waterfall.platform.errors` qui porte le statut du contrat — `NotFoundError`
  404, `ForbiddenError` 403, `ConflictError` 409, `PreconditionFailedError` 412,
  `UnprocessableError` 422, `UnavailableError` 503… — avec le code, en chaîne, et ses paramètres ;
  un refus par champ se dit par des `FieldError(pointer, code, params)`, le pointeur étant celui
  du contrat (`/label` dans le corps, `/query/from` dans la requête) ; une clé envoyée par le
  client s'y échappe comme RFC 6901 le veut, `~` en `~0` et `/` en `~1` (`json_pointer` de
  `waterfall.platform.errors`, #750). Il ne construit jamais
  de `Problem` ni de réponse : un seul gestionnaire (`waterfall.api.problems`) rend toute
  erreur dans l'enveloppe, avec l'identifiant de corrélation de la requête, dans le corps et
  dans l'en-tête `X-Correlation-ID`. Le gestionnaire range de même, sans que la route y pense :
  une requête illisible (corps absent, `null`, qui n'est pas du JSON ou pas un objet, en-tête
  ou témoin illisible) en 400 `MALFORMED_REQUEST` ; une valeur refusée en 422
  `VALIDATION_FAILED`, un champ par faute — un `model_validator` sur un corps lisible en est
  une, au pointeur `""` — (`VALUE_REQUIRED` pour une valeur vide quand une au moins est
  demandée, `VALUE_TOO_LONG`, `VALUE_OUT_OF_RANGE` avec `minimum` ou `maximum` pour une borne
  incluse, `NUMBER_INVALID`, `DATE_INVALID`, sinon `VALIDATION_FAILED` : une borne exclusive,
  une longueur minimale dépassée par une valeur non vide) ; un identifiant du chemin qui n'est
  pas un UUID en 404 `NOT_FOUND`, comme un objet inexistant ou invisible, tandis qu'un autre
  paramètre de chemin refusé est un 422 par champ, au pointeur `/path/<nom>`
  (`docs/api/DECISIONS.md`, « Session et erreurs ») ; une route inconnue, ou une méthode que la
  route ne sert pas, en 404, sans redirection d'une barre finale ; toute exception inattendue
  en 500 `INTERNAL_ERROR`, attrapée par `CorrelationMiddleware` : journalisée une fois avec sa
  trace, sa corrélation et l'auteur de la requête, sans rien en rendre.
  Un code que le contrat ne connaît pas est un défaut : le gestionnaire le rend en 500.
  Un texte reçu qui contient le caractère NUL, que PostgreSQL refuse dans une colonne comme dans
  un `jsonb`, est une valeur refusée — 422 `VALIDATION_FAILED` au pointeur du champ —, jamais un
  500 de la base (#743) : chaque modèle engendré hérite de `ContractModel`
  (`waterfall.api.contract.base`, que `[tool.datamodel-codegen]` de `backend/pyproject.toml`
  donne au générateur), qui cherche le NUL dans chacun de ses champs, élément d'une liste, clé ou
  valeur d'un objet compris ; un paramètre de requête ou de chemin en texte se type `Text`, du
  même module. La même base refuse de même un décimal du contrat — un type dont la racine porte
  le motif de `Decimal` ou de `Money`, `Percent` et `Hours` compris — écrit avec un chiffre autre
  que 0 à 9 (#2238) : le motif est une expression de JSON Schema, où `\d` ne vaut que 0 à 9, que
  les modèles engendrés lisent en Unicode ; une borne de requête lue à la main s'écrit donc
  `[0-9]`, jamais `\d`.
  Les seuils des indices et les bornes de la matrice des risques s'écrivent avec dix décimales
  au plus, comptées telles qu'écrites, zéro final compris, et dix chiffres avant la virgule
  (#2234) : au-delà, 422 `VALIDATION_FAILED` à leur champ, jamais un débordement de la base.

  _Contrôles_ : `make server-models-up-to-date` ; `make test-back` (`test_api_problems.py`,
  `test_access_roles_guard.py` pour le NUL, `test_contract_digits.py` pour les chiffres) ; que
  tout paramètre en texte est un `Text`, que le code et le statut sont ceux du contrat pour
  l'opération, la revue, puis la validation des réponses des tests d'API contre le contrat.

- **Un verrou refusé est un 503, sur toute route** — le gestionnaire d'`OperationalError` de
  `backend/src/waterfall/api/problems.py` répond 503 `COMPONENT_UNAVAILABLE` (`params.component`
  = `database`) à tout verrou que PostgreSQL refuse (`LockNotAvailable`) dans le délai qu'une
  transaction s'est donné par `lock_timeout` : ce n'est pas une erreur interne, la base ne laisse
  pas passer l'opération, qui n'a rien écrit. La règle vaut pour toute route, celles qui posent
  leur propre borne (`bound_lock_waits`, `platform/database.py`) comme les autres ; toute autre
  erreur de la base reste le 500 du middleware. Une route d'administration qui prend le verrou de
  la règle des administrateurs ouvre sa transaction par `bounded_transaction`
  (`api/authentication.py`, #924) ; l'inventaire de `test_users_under_load.py` échoue sur une
  opération d'écriture de `/users` ou de `/access-roles` qui n'y est pas.

  _Contrôles_ : `make test-back` (`test_users_under_load.py`, `test_api_problems.py`).

- **Journaux et réponses des tests d'API** — un test d'API passe par `ContractClient`
  (`backend/tests/support.py`), qui valide chaque réponse contre le contrat avec openapi-core :
  une réponse hors schéma fait échouer le test. Les journaux sont ceux de structlog en JSON
  (`waterfall.platform.logs`) : un enregistrement porte `level`, `timestamp`, `actor` et, dans
  une requête, `correlation_id` ; tout champ dont le nom contient `password`, `token`,
  `secret`, `authorization` ou `cookie` en est retiré. La valeur de chaque secret des
  réglages (`Settings.secret_values()`, mot de passe d'une URL compris) est de plus remplacée par
  `***` dans tout le texte rendu d'un enregistrement — message, trace, `repr` —, y compris ceux
  des bibliothèques. La limite : un secret que les réglages ne connaissent pas (un jeton de
  session, un mot de passe reçu dans une requête) n'est ni retiré sous un autre nom ni masqué
  par sa valeur : on ne le journalise pas, ni ne le met dans le message d'une exception. Une
  forme décodée du mot de passe d'une URL n'est retenue que si elle fait au moins quatre
  caractères, faute de quoi elle masquerait tout texte qui la contient ; l'URL entière et la
  forme encodée restent masquées dans tous les cas.

- **Accéder aux données d'un module** — les tables d'un module sont des classes sur la `Base` de
  `waterfall.platform.database`, dans son `tables.py`, privé ; son accès aux données, des
  fonctions de son module qui prennent une `Session`, privé lui aussi ; l'`interface` n'offre aux
  autres que ce qu'elle déclare, en objets simples et non en lignes de la table. Une écriture
  reçoit en argument qui écrit et à quel moment (`Stamp(author, at)`, l'auteur étant `None` pour
  la plateforme) : le noyau ne lit pas l'horloge. Un identifiant se tire de `new_id()`
  (`waterfall.platform.identifiers`), un instant de `UtcDateTime`, qui refuse un instant sans
  fuseau. Une requête, une transaction : `Database.transaction()` la valide à la fin du bloc et
  la défait si une exception le traverse, la réponse étant construite avant. Une modification qui
  porte un `lock_version` le teste dans l'écriture même et lève `PreconditionFailedError` si la
  version n'est plus la bonne.

  _Contrôles_ : `make test-back` (`tests/test_users_data_access.py`) ; `make imports-back` pour
  les frontières ; que l'écriture teste son `lock_version` dans la requête, la revue.

- **Connaître l'appelant** — une route gardée prend `Caller` et, si elle lit ou écrit la base,
  `Transaction` (`waterfall.api.authentication`) : la première valide le jeton d'accès par les
  clés du royaume (`waterfall.platform.keycloak`) et lit le compte par `idp_subject` à chaque
  requête, la seconde ouvre la transaction de la requête, validée quand la route a construit sa
  réponse et avant qu'elle parte. Aucun appel à Keycloak ne se fait dans une transaction (#669) :
  l'appelant est lu, puis au besoin admis, et ses permissions lues (`Acting`), chacun dans une
  transaction courte à lui, et une route qui appelle Keycloak — `closeMySessions`, `createUser`,
  `setUserActivation` et `setUserAccessRoles`, qui ferment les sessions d'un compte désactivé ou
  privé de tous ses rôles une fois l'écriture validée, `createPasswordSetupLink`, qui fait faire le
  lien par l'extension et ne l'inscrit au journal, sans son jeton, qu'une fois fait,
  `updateMyPreferences`, qui donne la langue choisie au compte chez Keycloak avant de l'écrire et
  n'écrit rien tant qu'il ne répond pas, `updateUser`, qui reporte chez Keycloak l'identité d'un
  compte local entre deux transactions courtes (vérifier, `carry_identity`, écrire) et la défait
  (`restore_identity`) si l'écriture est refusée — ne prend pas `Transaction`, mais ouvre les siennes avant
  et après l'appel. Un jeton absent ou invalide est
  un 401 `SESSION_REQUIRED`, un jeton expiré un 401 `SESSION_EXPIRED`, un jeton dont la
  connexion (`auth_time`, à défaut `iat`) précède la dernière fermeture des sessions du compte, ou
  tombe dans sa seconde, un 401 `SESSION_REVOKED` — `closeMySessions`, la désactivation et le
  retrait de tous les rôles en notent l'heure, `sessions_closed_at`, avant d'appeler Keycloak
  (#668, #835, #855) —, un compte désactivé un 401
  `ACCOUNT_DEACTIVATED` ; un compte que Waterfall ne connaît pas encore est créé sans rôle s'il
  vient de l'annuaire ou d'un fournisseur externe, refusé sinon par un 401
  `ACCOUNT_NOT_ADMITTED` (#664), sa cause écrite au seul journal. L'appelant devient l'auteur
  (`actor`) de chaque journal de la requête. L'API lit `WATERFALL_KEYCLOAK_ADDRESS`, l'adresse
  du navigateur, qui nomme l'émetteur des jetons, `WATERFALL_KEYCLOAK_BACKCHANNEL`, celle où elle
  joint Keycloak si elle en a une autre, et le secret `WATERFALL_SERVICE_CLIENT_SECRET`. Un test
  signe ses jetons par des clés qu'il engendre et sert comme le royaume sert les siennes
  (`tests/realm.py`) ; ce qui demande l'API d'administration de Keycloak
  (`waterfall.platform.keycloak_admin`) s'éprouve contre la plateforme (`make test-keycloak`).

  _Contrôles_ : `make test-back` (`tests/test_api_authentication.py`, qui compte aussi les
  connexions prises pendant l'appel à Keycloak, `Watching` de `tests/support.py`),
  `make test-keycloak` (`tests/test_keycloak_authentication.py`) ; qu'une route gardée prenne
  `Caller`, la revue.

## Clés de traduction

Les textes de l'interface vivent dans deux catalogues jumeaux, que lit next-intl :
`frontend/messages/fr.json`, la référence, et `frontend/messages/en.json`. La langue
n'apparaît pas dans l'adresse — un lien partagé s'ouvre chez chacun dans la sienne
(WF-INTF-0170) — : le serveur la résout à chaque requête (`frontend/src/i18n/request.ts`),
d'après la préférence du compte si elle vaut `fr` ou `en`, sinon la première langue offerte
que demande `Accept-Language`, sinon la langue par défaut de l'installation
(`getInstallation`). Un `*` placé devant toute langue offerte dans `Accept-Language` laisse
décider l'installation ; une installation illisible ou injoignable donne `fr`, la langue du
catalogue de référence. Sans compte — pas de session, ou une API injoignable — il n'y a pas
de préférence : le navigateur décide, et la coquille n'offre pas le menu du compte, où la
langue se choisit.

- **Une clé est hiérarchique, en anglais.** Un texte propre à l'interface se range sous le
  composant ou l'écran qui l'emploie, en camelCase (`languageSelector.label`). Ce que le
  contrat énumère garde ses noms, et chaque valeur a sa clé :
  - `enums.<Schéma>.<valeur>` pour une énumération nommée (`enums.ProjectState.in_progress`),
    `enums.<Schéma>.<propriété>.<valeur>` pour une énumération déclarée dans une propriété
    (`enums.BackgroundTaskRef.kind.revision_mark`), les `items` d'un tableau ne comptant pas
    (`enums.ReferenceReadiness.missing.active_cost_category`) : toutes les énumérations de
    `components.schemas`, sauf les deux suivantes ;
  - `errors.<CODE>` pour chaque code d'`ErrorCode`, `permissions.<code>` pour chaque
    `PermissionCode` ;
  - `enums.<Paramètre>.<valeur>` pour une énumération d'un paramètre partagé de
    `components.parameters` (`enums.Scope.unassigned`) : son nom partage le niveau des
    schémas, et un paramètre qui énumère des valeurs ne porte pas le nom d'un schéma ;
  - aucune énumération ne s'écrit en ligne, faute d'un nom pour ranger ses clés : celle d'un
    paramètre d'opération devient un paramètre partagé de
    `docs/api/components/parameters.yaml` ; celle d'un corps de requête ou de réponse, ou
    d'un en-tête — sous `paths` comme sous `components.responses`, `requestBodies` et
    `headers` —, un schéma nommé de `components.schemas`. Deux exceptions, sans clé :
    `sort_by`, dont les valeurs sont des colonnes que l'en-tête de la grille libelle déjà, et
    les corps des sondes, `/health` et les chemins qui en partent, qu'aucun écran n'affiche ;
  - un `const` n'a pas de clé : le contrat ne s'en sert que pour l'accord qu'une requête
    donne (`confirmed: true`), qui ne s'affiche pas ;
  - une valeur qui porte un point se lit comme un niveau, next-intl réservant le point au
    chemin : `permissions.users.write`, `enums.ComputedField.task.start`.
- **Une valeur est un message ICU** — `{max_columns, plural, one {…} other {…}}` —, avec les mêmes
  arguments dans les deux catalogues, ce que `make catalogs` vérifie ; le libellé d'une valeur
  d'énumération ou d'une permission est du texte sans argument. Le français suit sa typographie :
  espace insécable avant les deux-points, fine insécable avant le point-virgule et les points
  d'exclamation et d'interrogation, apostrophe typographique ; l'anglais suit l'orthographe
  britannique.
- **Ajouter une clé**, c'est l'écrire dans les deux catalogues, au même endroit, et la lire par
  `useTranslations` — composant client, ou serveur sans `await` — ou par `createTranslator`
  et `requestLanguage()` dans un composant serveur asynchrone. Une valeur ajoutée à une
  énumération du contrat ajoute sa clé dans la même modification.
- **Ce que l'utilisateur a saisi ne se traduit pas** : un libellé de tâche, un nom de projet
  s'affichent tels quels (WF-INTF-0170).
- **Les formats** sont ceux de `frontend/src/i18n/format.ts`, par la langue : un montant, un
  décimal, des heures depuis la chaîne exacte du contrat (`formatMoney`, `formatDecimal`),
  jamais par un flottant ; une date de planning telle quelle, sans fuseau
  (`formatPlanningDate`) ; un horodatage en heure locale du poste, écrit dans le navigateur
  (`LocalTime`) ; un rapport saisi ou réglé — un taux, une probabilité, une borne — en
  pourcentage, depuis sa chaîne exacte, chaque chiffre gardé (`formatPercent`) ; une part que le
  serveur calcule — la part d'une nature ou d'un poste, un avancement, un taux de charge — au
  centième de pourcentage (`formatShare`) : une part non nulle que l'arrondi dirait nulle se dit
  « < 0,01 % », ou « > -0,01 % », par le catalogue (`share`) ; une part nulle, quel que soit le
  nombre de ses zéros, se lit « 0 % » ; près de 100 %, l'arrondi ordinaire (EP-14/L51). Une part
  que le contrat donne nulle l'est : une part non nulle n'est jamais donnée nulle, mais à son
  premier chiffre significatif (EP-14/L42o, #694), et le pont de L51, qui jugeait une part nulle
  par son montant, est retiré (EP-14/L52). En français, `Intl` sépare les milliers par une fine
  insécable (U+202F) : « 1 234,56 » ne se coupe pas en fin de ligne. L'anglais se formate en anglais
  britannique (`en-GB`), comme ses catalogues s'écrivent : « 31 May 2026, 16:30 », les
  nombres restant « 1,234.56 ».

_Contrôles_ : `make typecheck-front` — next-intl est typé par le catalogue français, et une
clé que le code emploie sans qu'il l'ait casse le typage, comme une clé qui manque au
catalogue anglais (`frontend/src/i18n/catalogues.ts`) ; `make lint-front` —
`react/jsx-no-literals` refuse le texte écrit dans le JSX, et `no-restricted-syntax` un
littéral dans un attribut lu — `aria-label`, `aria-description`, `aria-roledescription`,
`aria-valuetext`, `aria-placeholder`, `title`, `alt`, `placeholder` (sauf `blur`, `empty` et
une adresse `data:image/`, les formes de next/image), `label`, la `value` d'un `input`
bouton —, ou dans une branche ou une concaténation d'un enfant ou d'un de ces attributs ;
restent à la revue les autres props de nos propres composants, et une chaîne bâtie par une
fonction ou une méthode (`.join`, `.concat`), dans le JSX ou hors de lui ;
`frontend/src/i18n/text-guard.test.ts` l'éprouve sur des extraits piégés, à côté de la garde
réseau qui partage la règle ; `make catalogs`, dans `check-front`, qui lit le
contrat qu'il vient d'assembler (`wftools.catalogs`) — les deux catalogues ont les mêmes
clés, chaque valeur est un texte non vide, chaque valeur d'énumération, chaque code d'erreur
et chaque permission du contrat a la sienne, et aucune clé sous `enums`, `errors` ou
`permissions` ne survit à la valeur que le contrat a retirée ; un texte emploie les mêmes
arguments ICU que celui du catalogue français, une clé ne s'écrit qu'une fois par fichier, et
aucune énumération ne s'écrit en ligne, hors `sort_by` et les sondes. Il demande au moins
deux catalogues, et nomme chaque clé qui manque et le catalogue qui la porte.

## Charte graphique

La charte vit dans `frontend/src/theme/globals.css`, et nulle part ailleurs (hors les pages de connexion, ci-dessous) : les couleurs,
la typographie, les espacements et les rayons y sont des jetons — des variables CSS que
Tailwind et les composants de shadcn/ui lisent par le thème (`bg-primary`,
`text-muted-foreground`, `rounded-md`). La charte est celle d'EP-25 (US-2070, d'après la maquette
de l'auteur, #3079) : une barre latérale bleu nuit (`#0f1b2d`, l'entrée courante `#22324b`, son
texte clair) dans les deux modes, une page gris pâle (`#f3f5f8`) sous des cartes blanches, la
couleur primaire bleu nuit (`#14233b`) ; le mode sombre a les mêmes formes et ses propres valeurs.
Les bleus des logos de `docs/assets` (`#027dc6`, `#1195e1`) ne servent plus qu'au logo et à
l'anneau du focus ; la police est Geist, celle du logo.

- **Clair et sombre par les mêmes jetons.** Chaque jeton de couleur porte ses deux valeurs,
  `light-dark(claire, sombre)`. Le document suit le poste (`color-scheme: light dark`) ; quand
  le compte force un mode (`DisplayPreferences.theme`), le layout racine pose
  `data-theme="light"` ou `data-theme="dark"` sur `<html>`, résolu côté serveur comme la
  langue. Aucun composant ne se demande quel mode s'affiche : la variante `dark:` de
  Tailwind, qui ne suivrait que le poste et ignorerait le mode forcé, est refusée. Un état
  qui change de couleur — survol, page courante — a son propre jeton (`--primary-hover`),
  mesuré comme les autres.
- **Ajouter une couleur, c'est ajouter un jeton** : sa valeur claire et sa valeur sombre dans
  `:root`, son nom dans `@theme inline` (`--color-<nom>: var(--<nom>)`), et chaque paire texte et
  fond qu'il forme dans `frontend/src/theme/contrast.test.ts` ; un composant emploie ensuite sa
  classe (`bg-<nom>`). Jamais une couleur dans un composant : ni une classe de la palette de
  Tailwind, retirée du thème — `bg-blue-500` ne produit rien —, ni une valeur arbitraire d'un
  utilitaire de couleur (`bg-[#027dc6]`, `bg-[red]`) — une longueur ou un nombre passent,
  `ring-[3px]` —, ni une variable entre parenthèses (`bg-(--x)`, `font-(family-name:--x)`), que
  personne n'a mesurée, ni une propriété arbitraire qui peint ou une variable (`[color:…]`,
  `[--primary:…]`), ni `color-mix(`, ni une couleur écrite dans une chaîne, dans un `style` ou dans
  l'attribut d'un SVG. Une police s'ajoute de même, par un jeton `--font-<nom>`.
- **La marque d'un différentiel** (US-0500) a trois jetons de ligne et trois jetons de marque,
  `--diff-added`, `--diff-removed`, `--diff-modified` et leurs `-mark` — un vert, un rouge, un jaune
  —, que `DiffMark` pose (`frontend/src/components/grid/diff-mark.tsx`) ; la couleur double le
  caractère `+`, `-` ou `M` et le mot, elle ne les remplace jamais. Le texte de la page et la marque
  atteignent 4,5:1 sur chaque teinte dans les deux modes (`contrast.test.ts`).
- **Le contraste** d'un texte sur son fond atteint 4,5:1, celui de ce qui montre un contrôle —
  bord d'un champ, anneau du focus — 3:1, dans les deux modes (WCAG AA, §3.6).
- **Un signalement passe par `Signal`** (`frontend/src/components/signal/`), et seulement par lui
  (WF-IHM-0070) : il reçoit une `AlertZone` du contrat et la rend par une forme Lucide, son libellé
  du catalogue (`enums.AlertZone.<zone>`) et son jeton, `--signal-<zone>`, dans une seule table
  typée sur `AlertZone`. **Une zone vient du serveur**, qui classe selon les seuils du référentiel :
  le front n'en déduit jamais une d'une valeur (WF-ARC-0020). Une zone nulle ou absente ne rend
  aucun `Signal` ; la valeur dit qu'elle manque (`ComputedIndicator`) ; jamais `?? "nominal"`. Les
  jetons de signalement sont mesurés comme les autres, et de plus en niveaux de gris et vus d'un
  protanope et d'un deutéranope (`contrast.test.ts`) ; l'alerte y ressort le plus de la page dans
  les deux modes — la plus sombre en clair, la plus lumineuse en sombre —, le nominal le moins. Hors
  de `src/components/signal/`, un utilitaire de couleur qui nomme un jeton de zone
  (`bg-signal-alert`, `text-signal-watch`) est refusé : `SIGNAL_SYNTAX` de
  `frontend/eslint.config.mjs`, `make lint-front`, éprouvé par `colour-guard.test.ts`. Qu'aucun
  écran ne distingue deux états par la seule couleur — une pastille, une ligne teintée sans forme ni
  texte —, c'est pour le reste la revue qui le tient ; les tests de `Signal` le prouvent pour le
  composant.
- **L'état d'un projet passe par `ProjectStateBadge`** (`frontend/src/components/projects/`,
  #523), partout où un écran le montre — l'accueil, la liste du portefeuille, la page, les
  paramètres et le cycle de vie d'un projet : une pastille remplie du jeton de son état,
  `--state-<état>`, son texte du jeton `--state-<état>-foreground`, dans la palette que l'auteur
  a validée — gris clair pour Créé, bleu pour Chiffrage, vert pour En cours, gris foncé pour
  Terminé, orange pour Perdu, rouge sourd pour Abandonné —, et toujours le mot de l'état et son
  icône, propre à chacun et distincte des formes de `Signal`. `contrast.test.ts` mesure le texte
  de chaque état sur sa pastille, et tient chaque jeton d'état à l'écart des jetons de zone :
  un état ne se lit pas comme une alerte.
- **shadcn/ui partout où un composant existe** : un composant s'ajoute en copiant son source
  dans `frontend/src/components/ui/` (`frontend/components.json` en donne les chemins), et
  seulement quand un écran l'emploie ; ce qu'il offre et qu'aucun écran n'emploie — une
  variante, une pièce — ne se copie pas. Copié, il est du code du dépôt, soumis à toutes ses
  règles : en-tête, lint, JSDoc, couverture, textes par le catalogue, couleurs par les jetons
  — ses classes se récrivent sur les jetons de la charte (`bg-popover`, `bg-sidebar-accent`),
  et un jeton qu'il attend et que la charte n'a pas s'y ajoute, mesuré. Une variable CSS ne se
  pose pas dans un `style` : la charte la déclare (`--sidebar-width`). Radix, son socle, vient
  du paquet `radix-ui`, un seul, examiné pour la garde réseau. Un composant qui en passe un
  autre à un composant client depuis un composant serveur lui passe un élément, jamais une
  fonction — une icône se remet dessinée (`commandIcon`).
- **La mise en page** suit la maquette validée par l'auteur (EP-02, puis EP-25) : la barre
  latérale est le Sidebar de shadcn/ui, sombre dans les deux modes, repliable en rail d'icônes dont
  chaque entrée garde son nom et le montre en infobulle ; à l'intérieur, les jetons que nomment ses
  entrées (`muted-foreground`, `primary`, `ring`…) prennent les valeurs de la barre
  (`[data-sidebar="sidebar"]` de `globals.css`), et la tuile du choix du projet, pâle, y porte son
  icône bleu nuit. La barre du haut, sans fond propre, est posée sur le gris de la page ; elle
  porte le fil d'Ariane, la recherche, le bouton du panneau des tâches et des messages et, à
  droite, le bouton de l'avatar qui déroule le menu du compte (DropdownMenu). Un écran se construit
  sur le gabarit de `frontend/src/components/shell/page-header.tsx` : `Screen`, son `<main>`, et
  `PageHeader`, le titre et l'icône de sa fonction, une ligne dessous, ses commandes à droite.
- **Deux familles d'écrans, dites par `Screen`** (EP-25, #3075, #3090). Un écran de travail —
  planning, devis, reste à engager, arbre des tâches, coûts réels, Kanban, chronologies, registre
  des risques, journal d'audit — est serré (`dense`) et prend toute la largeur de la fenêtre, et sa
  hauteur quand il porte une grille (`fill`) ; un écran de réglage ou de consultation — tous les
  autres — est une colonne centrée, bornée à 96rem (`--container-column`), en densité aérée
  (`airy`). Chaque fonction a sa famille, dans une table typée (`FUNCTION_DENSITY`, et
  `LEAF_DENSITY` pour une feuille qui a son écran, `function-display.ts`), que `Screen` et
  `PageHeader` reçoivent ; `function-display.test.ts` tient la liste des écrans de travail.
  `Screen` n'a pas de densité par défaut, et l'écran d'une fonction ne l'écrit jamais en
  littéral (`src/app/screen-density.test.ts`, qui nomme les écrans hors de la table : l'accueil,
  l'écran d'un projet, le compte, une page introuvable… ; le compte et l'écran d'un projet restent
  serrés jusqu'à leur recomposition, US-2130). Ce contrôle et la largeur de `main` mesurée sur un
  écran de chaque famille dans une fenêtre large (`e2e/theme.spec.ts`) tiennent les deux familles.
  Écartées : une largeur en pourcentage, et un plafond de 72rem.
- **Une section d'écran est une carte**, `SectionCard`
  (`frontend/src/components/shell/section-card.tsx`, sur la `Card` de shadcn/ui) : une région
  nommée par son titre, un titre de
  niveau 2, ses commandes à droite du titre, puis son corps. Ses commandes passent à la ligne sous
  le titre plutôt que de déborder : à 150 % d'agrandissement, aucune ne devient inatteignable. Un
  écran ne compose pas sa carte lui-même. La grille d'un écran de travail, qui n'a pas de titre de
  section — celui de l'écran le dit —, et un graphique qui se nomme lui-même ont la carte de grille,
  `GridCard` (`frontend/src/components/shell/grid-card.tsx`, #3421, #3446) : sans titre ni
  commandes, elle remplit la place que l'écran lui laisse (`fill`) ; `SectionCard` garde son titre
  exigé. Une section vide dit sa phrase à la place de son corps (`empty` de `ReferenceCard`).
- **La règle des commandes** (#3088, règles 2 à 4) : une carte a au plus une commande principale,
  la dernière à droite de son titre (`principal`), pleine quand elle crée ou déclenche, à contour
  quand elle modifie — l'écran dit à la carte ce qu'elle fait (`does`) et lui donne la commande
  comme une fonction de sa variante (`command: (variant) => …`), que la carte appelle avec la
  variante de ce mot (`principalVariant`) : aucun écran ne la choisit. Une fonction ne passe pas
  d'un composant serveur à un composant client (défaut n° 12 de `docs/dev/typescript.md`) : un
  écran serveur rend la carte lui-même. Ses autres commandes sont à contour, comme les commandes
  d'un écran à droite de son titre. Le plein est réservé à la commande principale : un choix
  courant se dit autrement. `expectCommandRule` (`frontend/src/test/command-rule.ts`) la lit dans
  ce qu'un test a rendu — un bouton est plein quand il porte les classes de la variante pleine de
  `buttonVariants` que la variante à contour n'a pas, et le module refuse de se charger si elles
  n'en ont aucune qui les distingue — ; un écran recomposé en cartes l'appelle dans ses tests.
- **Une icône Lucide sur chaque entrée de navigation, chaque bouton et chaque nature de ligne.**
  Pour les fonctions, les blocs, les commandes, les pages du compte, les natures de ligne, les modes
  de planification et les états d'avancement, elle est tirée d'une table typée sur ce qu'elle
  représente — `FUNCTION_ICONS`, `GROUP_ICONS`, `PROJECT_COMMAND_ICONS` et `REVISION_COMMAND_ICONS`,
  `ACCOUNT_ICONS`, `ROW_NATURE_ICONS`, `SCHEDULING_MODE_ICONS` et `PROGRESS_ICONS` —, de sorte
  qu'une valeur ajoutée sans icône casse le typage ; ailleurs — un bouton de la coquille, un avis,
  une page système —, elle est posée en ligne. Une icône à côté de son texte est `aria-hidden` ; une
  icône seule porte un nom — le bouton qui la porte, ou l'icône elle-même (`role="img"`), la nature
  d'une ligne dans sa cellule.
- **La sobriété** : aucun ornement hors des icônes — ni dégradé, ni ombre décorative, ni transition,
  ni animation, hors la pulsation du squelette de chargement et la roue d'un bouton qui attend
  (`waiting.tsx`), qui disent un état et s'arrêtent quand le poste demande moins de mouvement ; une seule ombre, `shadow-md`, sur ce qui flotte au-dessus de la
  page (un menu), pour l'en détacher. `src/components/ui/sobriety.test.ts` le vérifie pour les
  composants copiés. Un état se dit en mots — un badge, une pastille —, jamais par la seule couleur.
- **Le logo et le favicon** sont les fichiers de `docs/assets`, copiés à l'octet près dans
  `frontend/public/` et `frontend/src/app/icon.svg`. Sur la barre latérale, sombre dans les deux
  modes, le logo est toujours dans sa variante pour fond sombre (`BarLogo`) ; posé sur la page —
  la barre du haut, sans barre latérale —, il prend sa variante sombre là où le mode sombre
  s'applique (`Logo`).

_Contrôles_ : `make lint-front` — `no-restricted-syntax` (`COLOUR_SYNTAX` de
`frontend/eslint.config.mjs`) refuse, dans toute chaîne du code, une classe de couleur de la
palette, une valeur arbitraire d'un utilitaire de couleur qui n'est ni une longueur ni un nombre,
une variable passée à un utilitaire de couleur ou de police, une police arbitraire, une propriété
arbitraire qui peint, pose une police ou une variable, `color-mix(`, une couleur écrite en chaîne
entière et la variante `dark:` ; dans un `style`, quelle que soit sa valeur, une propriété qui
peint, borde, ombre ou pose une police, et une variable, que la clé soit un nom ou une chaîne ; et,
pour `fill`, `stroke`, `color` et les couleurs d'un SVG, tout littéral ou gabarit sans expression
autre que `currentColor`, `none` ou `url(…)`, où qu'il soit dans la valeur, une branche comprise.
`frontend/src/theme/colour-guard.test.ts` l'éprouve sur des extraits piégés, et vérifie qu'aucune
feuille de style ne vit hors de `src/theme/`. `make test-front` — `contrast.test.ts` mesure chaque
paire de jetons dans les deux modes, `brand.test.ts` compare les logos et l'icône à ceux de
`docs/assets`. Le contraste des écrans rendus se contrôle dans le navigateur, sur chaque écran de
l'application et sur ce qu'un geste y ouvre, en clair et en sombre
(`frontend/e2e/accessibility.spec.ts`, US-0200, US-0710) ; le reste de l'accessibilité d'un
composant, dans ses tests, par `expectAccessible` (`frontend/src/test/axe.ts`, axe-core sous
happy-dom, qui ne calcule pas les couleurs). Reste à la revue : une couleur bâtie par un gabarit à
expressions ou par une fonction, et un `style` ou un attribut de SVG qui reçoit une variable plutôt
qu'un objet ou un littéral écrit sur place ; et, pour la mise en page, qu'un bouton ou une entrée
porte son icône hors des tables typées — un bouton écrit à la main —, qu'aucune ombre, aucun dégradé
ni aucune animation n'orne un composant copié, qu'un écran prenne le gabarit et la famille de sa
fonction, que ses sections soient des cartes et que ses tests appellent `expectCommandRule`, et
qu'un composant copié n'entre qu'avec l'écran qui l'emploie.

**Les pages de connexion.** Keycloak sert les siennes, et aucun fichier du front : le thème
`waterfall` (`deploy/keycloak/themes/waterfall/login/`) les habille de la charte par sa propre
feuille, `resources/css/waterfall.css`, posée sur celles de `keycloak.v2`. Elle recopie les jetons
dont elle a besoin, en clair et en sombre — la seule copie de la charte hors du front : un jeton
changé dans `globals.css` s'y reporte à la main —, et le thème garde ses copies de la police Geist,
du logo et de la bannière (`docs/assets/waterfall-banniere.png`, en WebP, recadrée sur mobile).
Pour l'essayer sans reconstruire l'image, monter le dossier du thème sur
`/opt/keycloak/themes/waterfall` et couper le cache des thèmes (`KC_SPI_THEME__CACHE_THEMES`,
`KC_SPI_THEME__CACHE_TEMPLATES` à `false`, `KC_SPI_THEME__STATIC_MAX_AGE` à `-1`) : la page
rechargée suit le fichier.

## Migrations

Le schéma de la base est l'histoire de ses migrations : Alembic, dans
`backend/src/waterfall/migrations/` (`versions/0001_….py`, `0002_….py`…), une chaîne de
révisions numérotées, **écrites à la main** et relues comme le code. Les règles — nommage, types,
contraintes, deux temps, verrous — sont dans [sql.md](sql.md) ; cette section dit comment s'en
écrit une.

**Écrire une migration.**

1. Déclarer la table ou la colonne dans les tables du module qui la possède
   (`waterfall/core/<module>/tables.py`), sur la `Base` de `waterfall.platform.database` : sa
   `MetaData` porte la convention de nommage des contraintes, déclarée une fois. Ne la décrire
   nulle part ailleurs.
2. Créer le fichier de la révision, avec le numéro suivant :
   `cd backend && uv run alembic revision --rev-id 0002 -m "ce qui change"`. L'environnement
   d'Alembic (`waterfall/migrations/env.py`) lit `WATERFALL_DATABASE_URL`, comme le service ;
   aucune base n'est nécessaire pour créer le fichier vide.
3. Écrire `upgrade()` et `downgrade()` à la main avec `op.create_table`, `op.add_column`… : les
   contraintes se déclarent **sans nom**, sauf la partie `<nom>` d'une contrainte de vérification
   et un index d'expression (sql.md, « Nommage »). Un brouillon d'autogénération se relit ligne à
   ligne ; il n'est jamais validé tel quel. Le fichier créé est un gabarit : `ruff check --fix` et
   `ruff format` (dans `backend/`) le mettent aux règles du dépôt. Une table nouvelle accorde ses
   droits au rôle du service dans la même migration, le rôle nommé par la base où elle s'applique
   (`format('GRANT … ON <table> TO %I', current_database() || '_service')`, dans un bloc `DO` ; un
   nom de base de 55 octets au plus), et les déclare, avec leur raison, dans `SERVICE_RIGHTS`
   (`tests/test_migrations.py`) (sql.md, « Le rôle du service ») : sans eux, l'API ne la lit pas,
   et les tests du service non plus ; sans leur déclaration, le test des droits échoue.
4. Ajouter ou ajuster le test : le test de `tests/test_migrations.py` qui compare une base migrée
   à une base créée par les tables du code (contraintes, index, colonnes et défauts, lus dans le
   catalogue de PostgreSQL) échoue tant que les deux ne disent pas la même chose, et
   un test de `tests/test_database_constraints.py` éprouve chaque contrainte nouvelle.
5. Appliquer : `make migrate` sur la base de `WATERFALL_DATABASE_URL`, ou
   `make service-up`, dont le service `migrate` applique les migrations avant l'API.

**Appliquer.** `waterfall-migrate` (le service `migrate` de `compose.service.yaml`, ou
`make migrate`) applique, dans l'ordre, les révisions que la base n'a pas encore ; Alembic note
la dernière dans la table `alembic_version`. Une migration déjà appliquée ne se rejoue pas
(WF-DAT-0140), et deux instances qui démarrent ensemble n'appliquent pas la même deux fois : un
verrou consultatif les met à la queue. La commande s'arrête, avec le nom de la variable, si
`WATERFALL_DATABASE_URL` manque (WF-SEC-0010).

**Une seule tête.** Deux migrations qui partent du même parent forment deux têtes : la seconde à
être fusionnée se rebase sur la première et prend le numéro suivant. Le test de la chaîne échoue
sur deux têtes.

**Une table partitionnée par projet.** Une migration qui partitionne une table nouvelle par
l'identifiant d'un projet crée la partition des projets qui existent, comme `0031`, `0035` et
`0044`, et aussi celle des jeux de la réserve (`project_partition_reserve`, migration `0055`,
US-2830/L4) : un jeu à qui il manque une partition n'est jamais pris, et la création d'un projet
retombe alors sur la création synchrone de ses partitions, qui attend un marquage en cours.
`tests/test_migration_partition_reserve.py` le vérifie : un jeu fait en `0055` est entier à la tête.

**Les lignes que la migration écrit.** Le catalogue des permissions, par exemple, est une
migration de données, séparée de celle du schéma. Les lignes de l'installation, elles, sont
celles de l'installateur : l'amorçage les écrit, pas une migration (US-0420).

**Les écarts connus.** Une migration appliquée ne se réécrit pas (WF-DAT-0140) : un écart trouvé
après coup se consigne ici, et ne se corrige que par une migration nouvelle, si une décision la
demande. La migration `0016`, publiée depuis la v0.1.0, en porte deux, laissés tels quels (#979,
décision de l'auteur du 2026-11-14) : à la montée, une ancienne entrée `LAST_ADMINISTRATOR` du
compte rendu d'une lecture des comptes est rattachée au compte qui porte son adresse à la
migration, qui a pu changer depuis cette lecture — jusqu'à la lecture suivante, dont le compte
rendu est juste ; à la descente, elle garde les entrées `EMAIL_MISSING`, que l'`ErrorCode` d'avant
elle n'a pas — un poste de développement seulement, aucune installation ne redescendant sous une
version publiée.

**Taille d'un lot.** Les migrations sont écrites à la main : elles comptent dans la taille d'un
lot, et seules les révisions qu'un outil engendre seul seraient déclarées dans
`tools/paths.toml`.

_Contrôles_ : `make test-back` (`tests/test_migrations.py` : une seule tête, une migration
appliquée ne se rejoue pas, la descente est le miroir de la montée, le schéma — contraintes de
vérification et défauts compris — est celui des tables du code, quatre instances ensemble ;
`tests/test_migrations_as_owner.py` : toutes s'appliquent en tant que le propriétaire `NOSUPERUSER`
que fait le script de la production, `deploy/compose/waterfall-database.sql`, et une migration qui
exige le superutilisateur y échoue, #958), contre PostgreSQL (voir « Tests ») ; la compatibilité
avec le code voisin, la revue.

## Agents

Les agents de `.claude/agents/` — cadrage, livraison, développement et revue par langage —
suivent ce guide comme une personne, et leurs règles propres sont dans
[agents.md](agents.md) : ce qui fait foi, comment un lot se fait, où un agent s'arrête.

## Branches, lots et pull requests

Les règles sont dans le [README de la roadmap](../roadmap/README-fr.md), sections « Lots » et
« Branches », et dans [CONTRIBUTING](../../CONTRIBUTING.md) : un lot, une issue, une branche
`lot/<identifiant>` tirée de `epic/EP-nn`, une pull request qui y revient.

Chaque branche `epic/EP-nn` a sa file de fusion, un jeu de règles par branche (GitHub n'en accepte
pas sur un motif). Le livreur du premier lot lance `make merge-queue-check EPIC=EP-nn` après avoir
poussé la branche ; si elle échoue, une personne lance `make merge-queue EPIC=EP-nn`, qui crée le
jeu depuis le modèle `.github/rulesets/merge-queue.json` (voir « Commandes »). Cette cible lui est
réservée.

Chaque répertoire de `docs/` a son README en anglais, `README.md`, à côté de son original
français, `README-fr.md`, qui fait foi. Un lot qui modifie un `README-fr.md` porte la même
modification, traduite, dans le `README.md` voisin, dans la même pull request : un titre
ajouté, retiré ou déplacé dans l'un l'est dans l'autre, au même rang et au même niveau. Le
contrôle ne juge pas la traduction ; il prouve que sa structure suit l'original.

_Contrôle_ : `make readmes` (`wftools.readmes`, famille `repo`), qui échoue sur un
`README-fr.md` de `docs/` sans son `README.md`, ou l'inverse, et sur une paire dont les titres
diffèrent, un pour un — en nombre, ou en niveau à un rang donné.

### Reprendre `main` dans une branche d'EPIC

Une branche `epic/EP-nn` vit plusieurs jours pendant que `main` reçoit d'autres EPIC : la reprendre
de `main` évite que les conflits n'apparaissent à la fusion de l'EPIC, ou à la livraison d'un lot.

- **Qui.** Une personne : ni un livreur, ni un développeur, ni le pilote n'y touche
  de lui-même.
- **Quand.** Après chaque fusion dans `main`, et avant qu'un lot ne parte d'une branche en retard.
- **Comment.** Une branche `sync/EP-nn-main-k` (`k` numérote les synchronisations de l'EPIC),
  tirée de `epic/EP-nn` à jour ; `git merge origin/main` ; les conflits se résolvent en gardant les
  deux faits, jamais l'un des deux ; `make check BASE=origin/epic/EP-nn` passe ; une pull request
  vers `epic/EP-nn`, mise en file comme celle d'un lot. Les conflits se règlent là, dans cette
  pull request, et non à la livraison d'un lot qui les découvrirait. Les lots en vol reprennent la
  nouvelle pointe de `epic/EP-nn` (`git merge origin/epic/EP-nn`) avant leur mise en file.
- **Ce que cela a coûté, les 6 et 7 novembre 2026.** Une synchronisation a été remise en file deux
  fois : des lots ont été fusionnés dans `epic/EP-nn` pendant sa chaîne, et la file la refaisait à
  chaque fois sur une pointe qui avait changé. Elle se met en file quand aucun lot n'est en revue,
  ou elle se refait.

## Signature des commits

Les commits qui arrivent sur `main` sont signés : la règle « Require signed commits » de
GitHub protège `main`, et un commit qu'elle ne reconnaît pas bloque la fusion. Ce que GitHub
crée lui-même (le merge commit d'une pull request, un squash, un commit de Dependabot) est
signé par GitHub ; ce qu'une personne ou un agent commite est signé par la clé de cette
personne.

**Configurer sa machine** (clé SSH, la plus simple) :

```bash
ssh-keygen -t ed25519 -C "<adresse des commits>" -f ~/.ssh/id_ed25519_signing
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_signing.pub
git config --global commit.gpgsign true
```

Puis ajouter le contenu de `~/.ssh/id_ed25519_signing.pub` dans GitHub, *Settings → SSH and
GPG keys → New SSH key*, avec le type **Signing Key** et l'adresse des commits. La clé ne doit
pas demander sa phrase secrète à chaque commit, faute de quoi un agent s'arrête : la charger
dans `ssh-agent` (`ssh-add`) ou dans le trousseau du système. Se vérifier avec
`git log --show-signature -1`, puis lire le badge « Verified » sur GitHub après un push.

**Les agents** (`.claude/agents/`) commitent avec la configuration git de la machine où ils
tournent : lancés sur la machine d'une personne dont la clé est enregistrée, leurs commits sont
signés et vérifiés. Lancés dans une session cloud, ils signent avec une clé d'environnement
que GitHub ne connaît pas : leurs commits ne sont pas « Verified » et ne doivent pas arriver
sur `main` tels quels.

**Fusions.** `main` reçoit les branches d'EPIC par merge commit, qui porte leurs commits : il faut
donc qu'ils soient tous vérifiés. Pour ne pas bloquer une fusion, ne commiter sur `epic/EP-nn` et
`lot/*` qu'avec une clé enregistrée, et mettre une branche à jour depuis `main` par le bouton «
Update branch » de la pull request ou par un merge local signé. Éviter le « Rebase and merge » :
GitHub réécrit alors les commits sans les signer.

**Mise en place sur `main`.** La règle ne s'active qu'une fois l'EPIC en cours, EP-15,
fusionné, car il contient des commits non signés et la règle ne revérifie pas l'historique
déjà fusionné. Ordre : la clé enregistrée et vérifiée, la fusion d'EP-15, puis « Require signed
commits » sur `main` (*Settings → Rules*), avant de tirer la branche de l'EPIC suivant. La règle
ne vise ni `epic/*` ni `lot/*`. Aucun contrôle de la chaîne ne la double : c'est GitHub qui
refuse, d'où cette section.
