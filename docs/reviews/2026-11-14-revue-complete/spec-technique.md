# Revue — spécification, architecture technique et annexes (`docs/spec/waterfall-spec.md`, l. 3417-5045)

## Synthèse

Le chapitre 4 et les annexes sont dans un état rare : dix-sept revues passées (≈ 376 constats, presque
tous intégrés), un index des exigences exact (218 lignes, 0 écart avec le corps), des nombres de
volumétrie qui se recalculent tous, des durées de session identiques entre le texte et le royaume
Keycloak. Le code livré tient très largement ce que le §4 demande, souvent mieux que le texte ne
l'exige (gardes d'immuabilité par déclencheur, propriétaire compris ; `NULLS NOT DISTINCT` pour
l'idempotence ; file reconstituée depuis `background_task`).

Ce qui inquiète est ailleurs : **la spécification n'a pas suivi l'architecture réellement livrée**.
La restauration est exécutée par un quatrième processus, avec son flux Redis, son état de maintenance
tenu dans Redis seul et un volume partagé avec un service `keycloak-realm` permanent ; rien de cela
n'est au PBS, à la figure 18, au tableau des flux ni dans WF-ARC-0040/0090. Deux exigences du §4.7 et
du §4.4.1 sont déclarées closes sans être tenues en entier (WF-QUA-0010 : la porte de publication
n'est branchée sur rien et la version 0.3.0 a été posée ; WF-DAT-0070 : la liste des contributeurs
s'écrit sans auteur ni date). Plusieurs phrases de corps ne sont vérifiées par aucun Vérif, et c'est
précisément par là que des exigences se sont closes sans leur objet (fuseau de l'installation, purge
des tâches de fond, mise à nul « en base »).

Aucun constat bloquant : rien ici ne perd de donnée ni n'ouvre de faille.

## Constats bloquants

Aucun.

## Constats majeurs

### SPT-01 — WF-QUA-0010 est déclarée close, mais la chaîne publie des versions sans sa porte

- **Suite** : sans issue propre, vérifié le 2026-11-21 — tombera avec US-3000 (#4077, EP-13, `à
  faire`) et #3725 (finding, EP-13, rattachée à #4077) ; US-2440 (EP-28) pour les tests non
  exécutés, livrée.
- **Où** : spec l. 4533-4535 (WF-QUA-0010, corps et Vérif) ; `docs/roadmap/EP-01-socle-de-developpement.md:72`
  (« entière ») et `:80` (« Seules WF-QUA-0010 et WF-QUA-0030 sont closes ») ; `Makefile:255-256`
  (`requirements-release`) ; `.github/workflows/images.yml:57-60` (`make images PUSH=yes`) ;
  `tools/src/wftools/images.py:10-18` (étiquette de version posée sur `main`) ;
  `tools/src/wftools/coverage.py:27-29` et `:218-219` ; `docs/dev/README-fr.md:3923-3926` ;
  `backend/tests/test_msproject_corpus.py:356-361`, `test_msproject_export.py:410`, `test_msproject.py:243`.
- **Quoi** : trois phrases du corps ne sont pas tenues. (a) « La publication d'une version est refusée
  s'il reste une exigence F0 sans test » : `make requirements-release` existe, mais aucun workflow ne
  l'appelle (`grep -rn requirements-release .github` : rien) ; `images.yml` pose l'étiquette de
  version sur les trois images sans la consulter. (b) Le procès-verbal de recette « versionné, daté,
  cité par son identifiant », et le refus d'un procès-verbal périmé : l'outil dit lui-même « until the
  form of such a report is defined ». (c) « Un test qui se déclare non exécuté ne couvre pas
  l'exigence » : le relevé lit les citations dans les sources, sans exécuter ; les trois tests du
  schéma MSPDI font `pytest.skip` sans `WATERFALL_MSPDI_SCHEMA_PATH`, variable que ni le Makefile ni
  aucun workflow ne pose — ils sont donc toujours « non exécutés » dans la chaîne et comptés couverts.
- **Scénario** : la version 0.3.0 a été posée le 2026-11-12 (`docs/roadmap/EP-24-consolidation-apres-v0-3-0.md:14`)
  alors qu'EP-08, EP-10, EP-11 et EP-13 ne sont pas livrés : WF-OBS-0010, WF-OBS-0030, WF-EXP-0060,
  WF-CMP-0020… n'ont aucune citation dans `backend/tests`, `tools/tests` ni `frontend/e2e/service`
  (comptage par `grep`). La commande de publication aurait échoué en les nommant ; elle n'a pas été
  jouée, et rien dans la chaîne ne l'impose.
- **Proposition** : faire porter la porte par ce qui pose l'étiquette — `wftools.images` refuse de
  poser la version (`takes_version`) si `coverage --release` échoue, ou `images.yml` joue
  `make requirements-release` avant `make images` sur `main` ; test dans `tools/tests` : une exigence
  F0 non couverte laisse les étiquettes de commit et de branche et ne pose pas la version. Définir la
  forme du procès-verbal (fichier versionné, date, indice de l'exigence) ou retirer la phrase du
  corps. Pour (c), nourrir le relevé du rapport d'exécution (JUnit) ou fournir le schéma à la chaîne.
  Si les versions 0.x sont voulues hors de la règle, l'écrire dans WF-QUA-0010 (« à partir de la
  version 1.0 ») et rouvrir l'exigence dans la roadmap (close en EP-13 ou EP-28).
- **Confiance** : confirmé (workflow, Makefile, outil et roadmap lus ; je n'ai pas exécuté
  `make requirements-release`).
- **Déjà connu** : en partie — les titres `test.skip`/`test.fixme` comptés couverts (#975, EP-13) ;
  la forme du procès-verbal « pas encore définie » est dite au guide. La porte non branchée et les
  `pytest.skip` à l'exécution ne figurent dans aucun EPIC.
- Au sens strict du cahier (« exigence déclarée close et non tenue »), ce constat relèverait du
  bloquant ; je le classe majeur parce qu'il ne touche ni les données ni la sécurité.

### SPT-02 — WF-DAT-0070 close, mais la liste des contributeurs s'écrit sans auteur ni date

- **Issue** : #3356 (fermée).
- **Où** : spec l. 3974 (§4.4.1 « Audit ») et l. 4006 (WF-DAT-0070, corps : « Toute table dont les
  lignes peuvent être modifiées porte la date de création et son auteur, la date de dernière
  modification et son auteur ») ; `backend/src/waterfall/core/projects/tables.py:169-184` (`contributor` :
  `project_id`, `user_account_id`, `kind`, rien d'autre) ;
  `backend/src/waterfall/core/projects/interface/contributors.py:389-405` (`_replace` : `row.kind = …`
  en place, l. 400) et `:442-443` (seul `project.contributors_lock_version` bouge) ;
  `docs/roadmap/EP-04-projets-et-revisions.md:468` (« colonnes d'audit et `lock_version` sur chaque
  table dont les lignes se modifient ») contre `:475` (la table conçue sans elles) ;
  `docs/roadmap/EP-09-couts-reels-et-reste-a-engager.md:106` (« fin »).
- **Quoi** : une inscription de contributeur se crée, change de qualité et se retire sans qu'aucune
  ligne ne dise qui ni quand : la table n'a pas de colonnes d'audit, `set_contributors` n'estampille
  pas `project.updated_at/updated_by`, et l'action n'est pas de celles que WF-SEC-0030 inscrit au
  journal. La conception d'EP-04 se contredit elle-même (règle l. 468, table l. 475) et l'écart n'y
  est pas décidé.
- **Scénario** : un utilisateur habilité « au secours » (ou un chef de projet) passe B de participant
  à chef de projet — la qualité qui « décide de ce qui engage l'affaire » — puis retire C. Six mois
  plus tard, le diagnostic que le motif de WF-DAT-0070 promet (« qui a touché une ligne en dernier »)
  n'a que les journaux techniques, s'ils existent encore.
- **Proposition** : migration ajoutant les quatre colonnes à `contributor` (ou, à défaut,
  `contributors_updated_at/by` sur `project`), renseignées dans `_replace` ; test citant
  `WF-DAT-0070-A` : après `setContributors` par A, la ligne changée porte A et l'instant, la ligne
  inchangée garde les siens. Côté spécification, ajouter au Vérif : « Après un changement de qualité
  d'un contributeur, son inscription porte le compte qui l'a changée. » Vérifié par ailleurs : les
  liaisons (`task_link`) et la facette `task` n'ont pas non plus de colonnes, mais leur écriture
  estampille le nœud (`core/planning/interface/predecessors.py:113`) — ce n'est pas le même défaut.
- **Confiance** : confirmé (table, écriture, route `api/contributors.py` et conception lues ; aucune
  estampille ni inscription d'audit dans le chemin).

### SPT-03 — La restauration livrée n'est pas celle du §4 : un quatrième processus, un état dans Redis, un volume partagé

- **Issue** : #3380 (fermée).
- **Où** : spec l. 3576 (PBS-2.2 : le worker exécute « sauvegardes et leur copie externe »), l. 3894
  (WF-ARC-0090 : « sauvegarde et restauration […] sont exécutés par le worker »), l. 3711 (« trois
  processus applicatifs »), figure 18 (l. 3715-3756), tableau 8 (l. 3764-3782), l. 3495 et l. 3588
  (Redis porte le cache, la session et la file, « et rien d'autre »), l. 3689 (WF-ARC-0040 : Redis ne
  porte que du reconstructible) ; `deploy/compose/compose.prod.yaml:313-330` (service `restore`),
  `:423-439` (`keycloak-realm` permanent, volume `realm-requests`), `:162` (Redis `--save ''`) ;
  `backend/src/waterfall/platform/maintenance.py:1-12, 73-105` ; `backend/src/waterfall/api/maintenance.py:32-40` ;
  `backend/src/waterfall/platform/queue.py:9-10, 75-77` ; `backend/src/waterfall/worker/runner.py:15-18, 293-295` ;
  `backend/src/waterfall/platform/settings.py:159-176` ; `docs/roadmap/EP-03-comptes-et-habilitations.md:545-547, 822-866, 1167`.
- **Quoi** : par décision de l'auteur (#953, #954, #955, consignée dans la Conception d'EP-03), la
  restauration est exécutée par un service à part (`waterfall-restore`), seul à tenir les
  propriétaires des deux bases ; elle a son propre flux Redis, que le worker ne lit ni ne redépose ;
  l'état de maintenance — et la tâche de restauration elle-même, dont la ligne disparaît avec la base
  remplacée — vit dans une clé Redis ; le service demande la réapplication du royaume à un service
  `keycloak-realm` devenu permanent, par un dossier d'un volume qu'ils partagent. La décision est
  saine et documentée ; le constat est que **la spécification ne l'a pas suivie** en sept endroits, et
  que deux de ses propriétés F0 ne tiennent plus telles qu'écrites : « ce que Redis porte se
  reconstruit » (la maintenance et la tâche de restauration ne se reconstruisent pas), « aucun flux
  hors du tableau 8 » (le volume partagé et les connexions du service de restauration n'y sont pas).
- **Scénario** : (1) Redis redémarre pendant une restauration (il tourne sans persistance) : la clé
  de maintenance disparaît, l'API ressert et le worker reprend sur une base en cours de remplacement,
  et le service de restauration ne retrouve plus sa tâche. (2) Redis est seulement injoignable :
  `in_maintenance` rend `False` sur `RedisError`, et un appel direct à l'API porteur d'un jeton valide
  est servi contre la base en cours de remplacement — ce que le tableau 12 présente comme un mode
  dégradé normal. (3) EP-13 écrit le chart d'après le §4 : il lui manque un déploiement, un flux
  Redis, et un volume partagé entre deux pods (accès multiple en écriture), que WF-CMP-0020 interdit
  de faire dépendre d'un greffon d'hébergeur.
- **Proposition** : réviser le §4 avant EP-13 — un code PBS neuf pour le service de restauration
  (PBS-2.6, « un composant nouveau prend le prochain code libre »), WF-ARC-0090 et PBS-2.2 corrigés,
  figure 18 et tableau 8 complétés (service de restauration → PostgreSQL en propriétaire des deux
  bases, Redis, stockage objet, API d'administration ; `keycloak-realm` → fournisseur d'identité),
  WF-ARC-0040 disant où vit la maintenance. Pour le fond, prendre la seconde voie de #956 : tenir la
  maintenance hors de Redis (table d'un schéma que la restauration ne remplace pas, ou verrou
  consultatif de session du service de restauration) — la première voie, « donner à Redis une
  persistance », contredit PBS-3.2 (« rien n'y est durable ») ; et remplacer le dossier partagé par un
  échange que le chart sait porter. Test : vider Redis pendant une restauration d'essai, l'API reste
  en 503 jusqu'à la fin.
- **Confiance** : confirmé pour l'écart entre le texte et le livré (code, compose et conception lus) ;
  plausible pour le scénario (2) — je n'ai pas lu comment `pg_restore` verrouille la base pendant le
  remplacement, qui peut faire échouer ces requêtes plutôt que les servir.
- **Déjà connu** : le scénario (1) seul (#956, EP-13). L'écart de la spécification, le cas « Redis
  injoignable » et le volume partagé face au chart ne figurent dans aucun EPIC.

### SPT-04 — Le fuseau de l'installation est au corps de trois exigences et au Vérif d'aucune

- **Issue** : #3382 (fermée).
- **Où** : spec l. 2326 (WF-PLA-0130, corps), l. 4043 (WF-DAT-0100 : « Le jour courant […] s'entend
  dans le fuseau horaire de l'installation (WF-EXP-0020) »), l. 4233 et l. 4241 (§4.5.2 et WF-EXP-0020 :
  l'amorçage fixe « son fuseau horaire ») ; Vérif l. 4045 et l. 4243, où le mot n'apparaît que pour le
  fuseau du poste client ; `backend/src/waterfall/platform/installation.py:52-55` (aucune colonne de
  fuseau) ; `docs/roadmap/EP-07-chiffrage-et-devis.md:88, 124` (WF-DAT-0100 et WF-EXP-0020 « fin »)
  et `:242-247`.
- **Quoi** : aucune phrase de Vérif n'éprouve le jour courant dans le fuseau de l'installation, ni que
  l'amorçage le fixe. Les deux exigences ont donc été closes par EP-07 Vérif tenu, alors que le back
  prend le jour en temps universel.
- **Scénario** : installation à Paris ; à 0 h 30, heure locale, un utilisateur termine une tâche : la
  date proposée et conservée est celle de la veille.
- **Proposition** : ajouter à WF-DAT-0100 (ou WF-PLA-0130) : « Sur une installation au fuseau de
  Paris, une saisie datée faite à 0 h 30, heure de Paris, porte le jour de Paris. » et à WF-EXP-0020 :
  « Le fuseau choisi à l'installation est celui de l'écran d'état ; une seconde exécution ne le
  change pas. » ; rouvrir les deux exigences dans la roadmap jusqu'à US-2200.
- **Confiance** : confirmé.
- **Déjà connu** : le défaut du code, oui (#2527, EP-25 US-2200, critère « tâche terminée à 0 h 30 »).
  Le trou des Vérif et les deux exigences restées « closes » ne sont relevés nulle part.

## Constats mineurs

### SPT-05 — WF-CMP-0020 tait deux contraintes que le livré impose à un PostgreSQL fourni par l'exploitant

- **Issue** : #3383 (fermée).
- **Où** : spec l. 4503-4505 (WF-CMP-0020 : « PostgreSQL dans une version au moins égale à 18 » ;
  Vérif : « échoue […] si un composant est d'une version antérieure ») et l. 3702 (WF-ARC-0050 :
  remplacés « par simple paramétrage ») ; `deploy/compose/compose.prod.yaml:140-143`,
  `compose.service.yaml:96` (`max_locks_per_transaction=1024`, avec sa raison) ;
  `backend/Dockerfile:61` (`postgresql-client-18=18.*`) ; `backend/src/waterfall/worker/backup.py:131`.
- **Quoi** : (1) le partitionnement par projet crée neuf partitions par projet (5 400 à six cents
  projets, tableau 14) ; la restauration, qui refait le schéma en une transaction, échoue en
  « out of shared memory » avec le réglage par défaut de 64 verrous « dès quelques centaines de
  projets » — le commentaire du compose est la seule trace de cette exigence. (2) La sauvegarde
  emploie le `pg_dump` 18 de l'image : il refuse un serveur de version majeure supérieure ; « au
  moins égale à 18 » promet donc une compatibilité que le livré n'a pas.
- **Scénario** : EP-13 installe le chart sur le PostgreSQL 18 de la DSI, réglages par défaut : tout
  fonctionne jusqu'à la première restauration à volume, qui échoue en maintenance. Ou la DSI fournit
  un PostgreSQL 19 : chaque sauvegarde échoue.
- **Proposition** : WF-CMP-0020, corps : « PostgreSQL de la version majeure 18, réglé pour au moins
  1 024 verrous par transaction » ; Vérif : « Le démarrage échoue en le disant si le serveur est d'une
  autre version majeure ou si ce réglage est inférieur. » ; une ligne « Partitions » au tableau 14.
  Sonde au démarrage du worker (`SHOW max_locks_per_transaction`, `server_version_num`) et test.
- **Confiance** : confirmé pour les faits du dépôt ; la règle de `pg_dump` est celle de sa
  documentation, non éprouvée ici. À lever avant EP-13, qui clôt l'exigence.

### SPT-06 — Le tableau des flux et la figure 18 ignorent trois flux livrés

- **Issue** : #3384 (fermée), #3389 (fermée), #3963 (fermée).
- **Où** : spec l. 3764-3782 (tableau 8), l. 3715-3756 (figure 18), l. 3606 (PBS-5.3), l. 3702
  (« images de conteneurs — front, API, worker ») ; `deploy/keycloak/realm/waterfall.yaml:126-127` et
  `frontend/src/app/auth/backchannel-logout/route.ts:20` ; `deploy/compose/compose.prod.yaml:281-301`
  et `backend/src/waterfall/worker/main.py:203-229` ; `deploy/compose/compose.prod.yaml:26-27`.
- **Quoi** : (1) le fournisseur d'identité appelle le front (déconnexion par le canal arrière, dont
  dépend « sur tous ses postes » de WF-SEC-0020) : aucun TFX, et la figure n'a que Front → IdP.
  (2) Le planificateur exécute lui-même la purge (`waterfall-worker purge`) : il supprime en base et
  sur le stockage objet sans passer par la file, alors que PBS-5.3 et TFX-10 ne lui donnent que
  PostgreSQL et Redis, pour « inscrire une tâche ». (3) Les images livrées sont `front`, `waterfall`
  (API, worker, planificateur, migrations, restauration) et `keycloak` (avec une extension Java), non
  « front, API, worker ».
- **Scénario** : une politique réseau écrite d'après le tableau 8 coupe la déconnexion par le canal
  arrière et la purge du stockage ; les exports et les fichiers d'import expirés s'accumulent.
- **Proposition** : TFX-17 « Fournisseur d'identité → Front, HTTPS, jeton de déconnexion signé » ;
  TFX-10 étendu au stockage objet, et PBS-5.3 nommant la purge des expirations (WF-DAT-0120,
  WF-ARC-0100) ; WF-ARC-0050 : « front, services (API et worker, une même image), fournisseur
  d'identité ».
- **Confiance** : confirmé.

### SPT-07 — WF-DAT-0090 (close) : trois phrases du corps que le schéma livré ne suit pas

- **Issue** : #3385 (fermée).
- **Où** : spec l. 3986 et l. 4030 ; `backend/src/waterfall/core/planning/tables.py:242-247`
  (`order_item_id`, `work_package_id` en `RESTRICT`), `:325` (`tracking_entry.timeline_id` en
  `CASCADE`), `:66-88` (cascade de la structure vers ses nœuds et ses liaisons, du parent vers ses
  enfants), `:323` (`lineage_id` sans clé) ; `docs/roadmap/EP-06-planification.md:376, 460`.
- **Quoi** : le corps dit que la suppression physique d'un lot ou d'un poste « met à nul, en base, le
  rattachement » : c'est le service qui le retire (`detach_work_breakdown_item`), la clé refuse. Il
  dit que la cascade « n'est autorisée qu'à l'intérieur d'une révision en cours, d'une tâche vers ses
  lignes et ses liaisons » : une chronologie emporte ses inscriptions (régime projet), une structure
  son contenu, un nœud ses enfants. Il dit que « toute relation du modèle conceptuel est une clé
  étrangère » : l'inscription désigne sa tâche par lignée, sans clé possible. Le Vérif est tenu ; ce
  sont des choix de la Conception d'EP-06, que la spécification n'a pas repris.
- **Proposition** : corps : « […] la suppression en cascade n'est autorisée que d'une chronologie
  vers ses inscriptions et, à l'intérieur d'une révision en cours, d'une structure vers son contenu,
  d'une tâche vers ses sous-tâches, ses lignes et ses liaisons. Le rattachement d'une tâche à un lot
  ou à un poste supprimé est retiré par les services. Une référence par lignée n'est pas une clé. »
- **Confiance** : confirmé.

### SPT-08 — Le tableau 10, les régimes et l'amorçage décrits ne sont plus ceux du schéma livré

- **Issue** : #3386 (fermée).
- **Où** : spec l. 3930-3968 (tableau 10), l. 3920-3926 (régimes), l. 3984 et l. 4018 (« cinq lignes
  techniques »), l. 3990-3994 (WF-DAT-0060 : « Toute ligne […] un UUID »), l. 4233 et l. 4241
  (amorçage), l. 4932 (glossaire, « Référentiel commun ») ; `backend/src/waterfall/core/users/tables.py:98`
  (`display_preferences`, colonne `jsonb`) ; `backend/src/waterfall/platform/uploads.py` et
  `migrations/versions/0024_purge_file_upload.py` ; `backend/src/waterfall/bootstrap.py:326-340` ;
  `backend/src/waterfall/platform/installation.py:34-55`.
- **Quoi** : (1) « Préférences d'affichage | display_preference » : c'est une colonne de
  `user_account`, il n'y a ni table ni ligne à supprimer « à la demande de son porteur ». (2) Le dépôt
  d'un fichier (`file_upload`) est une sixième ligne technique, supprimée physiquement par la purge,
  que ni le §4.4.1 ni WF-DAT-0080 ne nomment. (3) Sans ligne au tableau : `installation`,
  `identity_sync_report`, `duration_unit` (les trois constantes de WF-PLA-0160),
  `actual_cost_mapping`. (4) L'amorçage livré crée aussi la devise (WF-REF-0140, « choisie à
  l'installation »), les constantes d'unités à 8, 40 et 20 et la correspondance vide : WF-EXP-0020,
  qui se veut limitative (« Elle ne crée aucun autre objet du référentiel »), n'en cite aucune, et le
  glossaire non plus. (5) Quatre tables à ligne unique ont une clé entière (`installation`,
  `reference_setting`, `actual_cost_mapping`, `duration_unit`), contre la lettre de WF-DAT-0060.
- **Proposition** : tableau 10 : « Préférences d'affichage | attribut de user_account », et quatre
  lignes ajoutées ; §4.4.1 et WF-DAT-0080 : « six lignes techniques […] un dépôt de fichier à son
  expiration » ; WF-EXP-0020 et « Référentiel commun » : la devise, les constantes d'unités et la
  correspondance ; WF-DAT-0060 : « hors les tables à ligne unique ».
- **Confiance** : confirmé.

### SPT-09 — L'avatar est « livré à 512 Ko » ; l'amorçage livre 2 Mio, et ce n'est pas un réglage de déploiement

- **Issue** : #3387 (fermée), #3965 (ouverte).
- **Où** : spec l. 3928 ; `docs/api/components/schemas/platform.yaml:97` (« shipped at 512 KB,
  `524288` ») ; `backend/src/waterfall/bootstrap.py:98-101, 302` ; `docs/api/DECISIONS.md:9707-9708`
  (« Le témoin a ses valeurs livrées, sauf l'avatar, porté à 2 Mio ») ; spec l. 4204 (définition du
  paramètre d'exploitation).
- **Quoi** : la décision ne dérogeait que pour le témoin ; or `waterfall-api install` écrit 2 Mio
  dans toute installation neuve. Et la valeur est une constante du code écrite une fois dans la ligne
  `installation` : l'exploitant ne la fixe ni dans le Compose ni dans le chart, contre le §4.5.1.
- **Scénario** : l'écran d'état d'une installation neuve présente 2 097 152 là où la spécification
  et la description du contrat annoncent 524 288.
- **Proposition** : trancher la valeur (512 Ko dans `bootstrap.py`, ou « 2 Mio » dans le §4.4.1 et
  la description du contrat) et lire la borne d'un réglage de l'amorçage ; test de l'amorçage citant
  la valeur livrée.
- **Confiance** : confirmé.

### SPT-10 — WF-DAT-0080 (close) : la rétention des tâches de fond n'a ni purge ni Vérif

- **Issue** : #3388 (fermée).
- **Où** : spec l. 3984 (« une tâche de fond au terme de la rétention de son résultat — […] trente
  jours ») et l. 4018-4020 ; `backend/src/waterfall/worker/main.py:203-229` (la purge ne touche pas
  `background_task`) ; `docs/roadmap/EP-07-chiffrage-et-devis.md:91` (« fin »).
- **Quoi** : le quatrième régime n'a aucune phrase de Vérif ; l'exigence s'est close sans que la
  table des tâches soit jamais purgée. Elle croît sans borne (sans gravité à ce volume).
- **Proposition** : Vérif : « Une tâche de fond terminée depuis plus que la rétention n'est plus dans
  la base ; un dépôt, un compte rendu et un plan de collage expirés non plus. »
- **Confiance** : confirmé. **Déjà connu** pour la purge (#921, EP-13) ; le Vérif muet ne l'est pas.

### SPT-11 — Figure 19 : l'abandon d'un import passe par la file ; le contrat et le livré le font dans la requête

- **Issue** : #3389 (fermée).
- **Où** : spec l. 3843-3851 (« inscrit la tâche », « met en file la suppression ») ;
  `docs/api/paths/exchanges.yaml:436-452` (`abandonImport`, 204) ; `backend/src/waterfall/api/imports.py:319-324` ;
  `backend/src/waterfall/platform/tasks.py:44-54` (aucun genre de tâche pour l'abandon).
- **Quoi** : l'abandon supprime le fichier dans la requête et répond 204 ; il n'existe pas de tâche
  d'abandon. L'expiration, elle, est le fait de la purge planifiée (SPT-06), non du worker.
- **Proposition** : figure : « U->>A : abandonne l'import ; A->>S : supprime le fichier ; A->>B :
  passe l'import à abandonné », et une note « à l'expiration, la purge planifiée (PBS-5.3) ».
- **Confiance** : confirmé.

### SPT-12 — Deux énumérations du §4 en retard sur le contrat

- **Issue** : #3390 (fermée).
- **Où** : spec l. 4334 (WF-SEC-0030) contre `backend/src/waterfall/platform/audit.py:49-72` et
  `docs/api/DECISIONS.md:3076-3083` ; spec l. 3894 (WF-ARC-0090) contre
  `backend/src/waterfall/platform/tasks.py:44-54`.
- **Quoi** : le journal inscrit la réactivation d'un compte et la production d'un lien de mot de
  passe, que la liste de WF-SEC-0030 ne porte pas (son Vérif dit « chacune des actions énumérées ») ;
  la fusion d'un différentiel et la survenance d'un risque sont des tâches de fond au contrat, hors
  de la liste de WF-ARC-0090, dont le Vérif dit « aucun de ces traitements ».
- **Proposition** : ajouter « la réactivation » et « la production d'un lien de fixation du mot de
  passe » à WF-SEC-0030 ; « la fusion d'un différentiel, la survenance d'un risque » à WF-ARC-0090.
- **Confiance** : confirmé.

### SPT-13 — WF-ARC-0030 : l'API « n'en tire que l'identité » ; le livré en tire aussi la date et la session de connexion

- **Issue** : #3391 (fermée).
- **Où** : spec l. 3677 et l. 4321 (WF-SEC-0020 : la déconnexion prend effet « à la requête
  suivante » parce que « le fournisseur d'identité révoque ses jetons ») ;
  `backend/src/waterfall/platform/keycloak.py:178-179` ; `backend/src/waterfall/api/authentication.py:139-141, 145-154`.
- **Quoi** : un jeton d'accès validé par les seules clés publiques reste valable cinq minutes après
  une révocation chez le fournisseur ; le mécanisme écrit ne peut pas tenir « à la requête suivante ».
  Le livré le tient autrement, et bien : `user_account.sessions_closed_at` comparé à `auth_time`.
- **Proposition** : WF-ARC-0030 : « n'en tire que l'identité de l'appelant, l'instant et la session
  de sa connexion » ; WF-SEC-0020 : « […] Waterfall conserve l'instant de la dernière fermeture des
  sessions du compte et refuse tout jeton d'une connexion antérieure ».
- **Confiance** : confirmé.

### SPT-14 — « L'exploitant » : dix-huit emplois, aucune définition, et un compte dont rien ne dit où il vit

- **Issue** : #3392 (fermée).
- **Où** : spec l. 3781 (TFX-15, « Compte de l'exploitant »), l. 4447 (WF-OBS-0030 : le tableau de
  bord « reste servi lorsque PostgreSQL ou Redis sont indisponibles »), l. 4271 (tableau 12 :
  PostgreSQL indisponible, « Rien » ne continue), l. 4850 (glossaire, « Acteur »).
- **Quoi** : l'exploitant n'est ni un acteur ni une entrée du glossaire. Si son compte est un compte
  du fournisseur d'identité, il tombe avec PostgreSQL (TFX-12), et l'alerte que WF-EXP-0040 lui
  destine n'est plus lisible ; le tableau 12 dit par ailleurs que rien ne continue.
- **Proposition** : entrée de glossaire ; TFX-15 : « compte propre au tableau de bord, hors du
  fournisseur d'identité » ; tableau 12 : « Le tableau de bord de l'exploitant et ses alertes ».
- **Confiance** : confirmé pour le texte ; sans objet livré (EP-13) — à trancher avant lui.

### SPT-15 — WF-DAT-0120 : « téléchargement complet » ne s'observe qu'au bord de l'API

- **Issue** : #3393 (fermée), #3977 (ouverte).
- **Où** : spec l. 4162-4164 ; `backend/src/waterfall/api/exports.py:127-131` ; `frontend/src/api/relay.ts:51-60`.
- **Quoi** : le fichier est supprimé quand l'API a remis son dernier octet au front, qui le relaie
  au navigateur derrière le mandataire ; une coupure côté navigateur après ce moment perd le fichier,
  contre « un téléchargement interrompu le laisse disponible ».
- **Proposition** : corps : « […] à l'issue de sa première remise complète par l'API » et « un
  export perdu se redemande », ou ne supprimer qu'à l'expiration.
- **Confiance** : plausible — non éprouvé ; dépend de ce que les tampons retiennent d'un fichier de
  quelques mégaoctets.

### SPT-16 — WF-QUA-0050 : « le seul chemin d'écriture asynchrone » ne l'est pas, et « trois parcours » en énumère cinq

- **Issue** : #3394 (fermée).
- **Où** : spec l. 4593-4595.
- **Quoi** : le motif dit des flux par fichier qu'ils sont « le seul chemin d'écriture asynchrone du
  produit » ; WF-ARC-0090 y met aussi le marquage, la sauvegarde et la restauration. Le corps annonce
  « le parcours des trois acteurs » puis cinq propositions ; le Vérif compte « trois parcours ».
- **Proposition** : motif : « avec le marquage, ce sont les chemins d'écriture asynchrones » ; corps :
  « le parcours de chacun des trois acteurs — chef de projet : […] ; manager : […] ; administrateur :
  […] ».
- **Confiance** : confirmé.

### SPT-17 — Annexes B et C en retard sur le dépôt

- **Issue** : #3395 (fermée).
- **Où** : spec l. 5011-5038 (annexe C, « avec quoi les propriétés du §4.7 sont obtenues
  aujourd'hui ») et l. 4982 (annexe B) ; `frontend/package.json` (`vitest`, `next-intl`) ;
  `backend/pyproject.toml` (`import-linter`, `openapi-core`) ; `docs/roadmap/EP-01-socle-de-developpement.md:664`
  (« que l'annexe C ne nomme pas encore — Vitest ») ; `backend/src/waterfall/core/estimate/excel/writer.py:406, 569`
  et `remaining/excel/layout.py:215`.
- **Quoi** : l'annexe C ne nomme ni Vitest (tests du front, WF-QUA-0010 et 0020), ni import-linter
  (WF-ARC-0010), ni l'outil de conformité au contrat (WF-ARC-0060), ni next-intl (WF-QUA-0070), et
  cite au présent Helm, k6 et la bibliothèque Prometheus, absents du dépôt. L'annexe B donne pour
  liste des fonctions employées six fonctions ; les classeurs emploient aussi SOMME, N et OU.
- **Proposition** : compléter l'annexe C et marquer « à venir » ce qui l'est ; annexe B : ajouter
  « SOMME, N, OU ».
- **Confiance** : confirmé.

## Points forts

- **Index des exigences** : 218 exigences au corps et à l'index (210 F0, 8 F1), identifiants,
  sections, titres et flexibilités identiques ; seul l'exemple `WF-EXA-0010-A` du §1.3.1 en est
  absent, à dessein. Les numéros sautés (WF-CYC-0040, 0070, WF-IND-0120) ne sont cités nulle part.
- **Volumétrie** : tous les nombres des tableaux 13 à 15 se recalculent (36 M d'objets-versions par
  an, 7,2 M et 10,8 M de lignes de coût, 600 projets, 15 000 et 30 000 inscriptions, « huit
  premières » opérations) et s'accordent avec le §4.4.2, le §4.5.1 et WF-QUA-0040.
- **Session** : cinq minutes, deux heures, douze heures, rotation du jeton de rafraîchissement —
  `deploy/keycloak/realm/waterfall.yaml:73-77` est la spécification.
- **Immuabilité par la base** (WF-DAT-0020, WF-SEC-0030) : déclencheurs sur chaque table révisionnée,
  troncature comprise, propriétaire compris ; le marquage prend la révision `FOR UPDATE`, ce qui
  ferme la course avec les gardes en `FOR KEY SHARE`. La migration `0023`, qui désarme une garde, ne
  fait qu'emplir une colonne neuve : conforme à WF-DAT-0140.
- **Tâches de fond** (WF-ARC-0090) : la table fait foi, la file se reconstitue (`redeposit`), une
  tâche interrompue repart sous verrou consultatif, trois tentatives au plus.
- **Idempotence** (WF-DAT-0110) : `UNIQUE NULLS NOT DISTINCT` sur projet, pièce et poste.
- **Annexe C** : chaque outil cité et présent est bien celui du dépôt ; versions planchers de
  WF-CMP-0020 tenues par le Compose (PostgreSQL 18, Redis 8, Keycloak 26.8.1).

## Couverture

- **Lu en entier** : `docs/spec/waterfall-spec.md` l. 3417-5045, dont les trois figures Mermaid, les
  tableaux 7 à 16, l'index, les annexes A à D (les définitions du glossaire au-delà de 400 caractères
  ont été tronquées à la lecture, sauf celles citées) ; `docs/spec/revue/PROMPT.md` ; les titres des
  dix-sept fichiers de `docs/spec/revue/constats/`, et le texte de C-342.
- **Lu en entier, côté code** : `platform/tasks.py`, `queue.py`, `maintenance.py`, `keycloak.py`,
  `correlation.py`, `identifiers.py`, `installation.py`, `decimals.py`, `database.py` ; `api/app.py`,
  `middleware.py`, `authentication.py`, `maintenance.py`, `exports.py` ; `worker/runner.py`,
  `worker/main.py` ; migration `0023` ; `core/costs/tables.py`.
- **Échantillonné** : `platform/settings.py` (l. 95-241), `platform/audit.py`, `audit_columns.py` ;
  migrations `0020`, `0022`, `0024` (en-têtes et gardes) ; `core/planning/tables.py`,
  `core/projects/tables.py` et `interface/contributors.py`, `core/users/tables.py`,
  `core/estimate/tables.py` ; `restore/main.py`, `restore/runner.py` (en-têtes) ; `bootstrap.py`
  (constantes et `install_reference`) ; `deploy/compose/compose.prod.yaml` ; le royaume Keycloak ;
  `images.yml` ; `tools/src/wftools/coverage.py` ; `frontend/src/session/store.ts` (en-tête),
  `frontend/src/api/relay.ts` ; les tableaux « Exigences réalisées » et les passages de Conception
  cités d'EP-01, 03, 04, 06, 07, 09, 13, 24, 25.
- **Non lu** : `platform/storage.py`, `uploads.py`, `logs.py`, `errors.py`, `registry.py`,
  `restoration.py`, `keycloak_admin.py` ; `worker/backup.py`, `restore.py`, `identity_sync.py`,
  `marking.py`, `exchanges.py` ; `api/problems.py`, `uploads.py` ; les autres migrations ; les
  autres fichiers Compose ; les tests du back (seules des citations ont été cherchées).
- **Non vérifié contre le code** : WF-ARC-0020, WF-ARC-0060, WF-ARC-0100, WF-ARC-0110, WF-DAT-0150,
  WF-QUA-0030, WF-QUA-0070, toutes closes — je n'ai constaté que l'existence de leur mécanique, pas
  leur Vérif. La matrice FBS–PBS (tableau 7) et les champs PBS n'ont pas été recalculés : plusieurs
  constats passés (C-068, C-319, C-339…) les ont déjà repris.
- **Tu, parce que dû par EP-13** : flux internes en clair du Compose de production (WF-SEC-0010),
  métriques, alertes, chart, mise à jour sans interruption, modes dégradés, test de restauration.
- **Aucune commande lourde** n'a été lancée ; ni `make requirements` ni aucun test.
