# Revue complète de Waterfall — `main` au 2026-11-14

Commit relu : `29785cc` (« Roadmap : EP-25 cadré », #3246). Périmètre : ce qui est **livré** —
EP-01 à EP-07, EP-09, EP-14 à EP-24. Les parties non implémentées (EP-08, EP-10, EP-11, EP-13,
EP-25 à EP-28) sont exclues : aucune absence due par l'un de ces EPIC n'est comptée comme défaut.

## 1. Synthèse

**Le dépôt est mécaniquement très tenu.** Tous les contrôles que j'ai pu lancer sont verts, le
contrat et le service coïncident opération par opération, la traçabilité est exacte au mot près,
l'immuabilité des révisions est tenue par la base, et aucune des 23 relectures n'a trouvé de
commentaire d'exemption, de `float` sur un montant, de SQL concaténé ni de route d'écriture sans
garde.

**Les défauts sérieux ne sont pas diffus : ils se rangent en six foyers.**

1. **Le moteur de planning sur les liaisons de récapitulatives** — marges négatives et chemin
   critique faux sur un planning tout automatique, passe arrière quadratique, règle absente de la
   spécification (BPL-01, 03, 04, 06, 07 ; SPB-04).
2. **Les allers-retours de fichiers** — rapprochement MS Project qui peut échanger deux tâches,
   application d'un import qui ignore le compte rendu confirmé, en-tête absent lu comme cellules
   vides, classeurs sans borne de décompression (BEX-01, 02, 03 ; BCH-03).
3. **La saisie en grille et le suivi des tâches de fond, côté front** — collage du planning écrit
   sur des lignes de devis non affichées, suivi qui cesse d'interroger, courses entre saisies
   (FGR-01 à 06 ; FPL-01 ; FCO-01).
4. **Les habilitations de l'administration** — prise d'un compte par le lien de mot de passe sous
   `users.write` seul, garde du dernier administrateur contournable (BAC-01, BAC-02).
5. **« Close » n'est pas « prouvée »** — une exigence est dite close sur la présence de sa phrase
   dans une US ; `make requirements-release` n'a aucun appelant ; plusieurs exigences closes ne
   tiennent pas leur corps (RMP-01 à 07 ; SPT-01, 04 ; PLC-02).
6. **La spécification n'a pas suivi le livré** — des décisions prises dans `DECISIONS.md` ou dans
   les Conceptions contredisent des exigences closes sans que la spécification ait été révisée
   (SPA-01, SPT-03, SPT-07, SPT-08, DON-10).

**Décompte**, après recoupement des doublons entre relecteurs :

| Gravité | Nombre | Dont revérifiés par moi |
|---|---|---|
| Bloquant | 6 | 6 (1 rejoué par exécution, 5 relus sur le chemin) |
| Majeur | 54 | 18 (4 rejoués, 14 relus) |
| Mineur | ≈ 200 | échantillon |

S'y ajoutent une vingtaine de défauts **déjà connus et planifiés** (EP-25, EP-26, EP-13…), rappelés
au § 11 sans être recomptés.

**Ce que je recommande de traiter d'abord** (détail au § 13) : les six bloquants ; puis le lien de
mot de passe et la garde du dernier administrateur ; puis la borne de décompression des classeurs et
la garde de péremption à l'application d'un import ; puis brancher `requirements-release` sur la
pose d'une version.

## 2. Méthode, et ce que valent les constats

- **23 relectures indépendantes**, une par périmètre, sur le modèle des agents de revue du dépôt
  (`python-reviewer`, `typescript-reviewer`) étendu au fond : logique, calcul, concurrence, sécurité,
  intégrité. Chaque relecteur a rendu un rapport détaillé (annexe).
- **Contrôles exécutés par moi sur `main`, tous verts** : `make lint-back` (619 fichiers),
  `typecheck-back` (pyright strict, 0 erreur), `imports-back` (3 contrats tenus), `lint-front`
  (ESLint à 0 avertissement, Prettier), `typecheck-front`, `lint-openapi`, `roadmap` (0 problème),
  `requirements` (173 exigences F0 couvertes sur 210, 15 citées par le front seul), `readmes`,
  `sources`, `reuse` (3 110 fichiers sur 3 110), et **les tests unitaires du front : 334 fichiers,
  5 168 tests, tous passants**.
- **Non exécuté** : les tests du back, les parcours de bout en bout et les tests de Keycloak — cet
  environnement n'a pas de démon Docker, donc ni PostgreSQL 18, ni Garage, ni Keycloak. Les
  constats du back viennent de la lecture, sauf ceux du moteur de planning, pur, rejoués par
  exécution.
- **Revérification** : j'ai repris moi-même les six bloquants et un tiers des majeurs. La colonne
  « Vérif. » dit comment : **rejoué** (exécuté par moi), **relu** (chemin relu par moi dans le
  code), **relecteur** (établi par le seul relecteur ; sa confiance est entre parenthèses —
  *confirmé* = chemin lu de bout en bout, *plausible* = une pièce non vérifiée).
- **Les réglages de GitHub** (jeux de règles réels, protection de `main`) et l'état des issues
  n'ont pas été consultés : « déjà connu » s'entend au sens des fichiers de `docs/roadmap/`.

## 3. Constats bloquants

### B1 — Une liaison DD ou DF qui part d'une récapitulative fausse les marges et le chemin critique (BPL-01)

- **Issue** : #3335, `[EP-06]`, sous le lot d'origine US-1390/L1 (#2329) — décision : à trancher.
- **Où** : `backend/src/waterfall/core/planning/scheduling/engine.py:275-288` et `:301-331`.
- **Quoi** : en passe avant, la liaison compte depuis le début agrégé de la récapitulative ; en
  passe arrière, elle borne le début de **chaque** feuille. Juste pour une liaison qui part de la
  fin, faux pour le début.
- **Scénario rejoué** : récapitulative S = {A 1 j → B 1 j}, T 5 j lié à S en début-à-début, tout
  automatique. Dates correctes, mais A, B et S sortent à **−1 j de marge, « critiques »**, sans
  aucun conflit signalé ; attendu A 0, B 3 j. Les marges sont conservées en base et figées au
  marquage. L'import MS Project admet ces liaisons.
- **Preuve** : exécuté sur le moteur (script en annexe du rapport `back-planning`). Aucun test ni
  le corpus MS Project ne compare ces marges.
- **Correction** : en passe arrière, une liaison portée par un ancêtre et comptée depuis le début
  ne borne que les feuilles qui portent ce début. Test de propriété : « une structure sans tâche
  manuelle ne rend aucune marge négative ».

### B2 — Une feuille démarrée qui reçoit une sous-tâche perd son état et devient supprimable (BPL-02)

- **Issue** : #3336, `[EP-06]`, sous le lot d'origine US-1380/L2 (#2335) — décision : à trancher.
- **Où** : `core/planning/interface/nodes.py:368-380` (`_judge_parent`), `core/planning/views.py:162-204`
  (`_derived`, `state_of`), `shaping.py:60-74`, garde de `deleteNode` à `nodes.py:827`.
- **Quoi** : `createNode` et `moveNodes` acceptent comme parent une feuille démarrée ou terminée.
  Devenue récapitulative, son état ne se lit plus que dans ses subordonnées : elle se lit « non
  démarrée », sa date de démarrage disparaît, la garde de WF-PLA-0070 ne la retient plus, et
  l'état constaté est effacé de la facette au retour en feuille.
- **Scénario** : P démarrée, avec des lignes réestimées ; un contributeur indente sous elle la
  tâche suivante (geste ordinaire de la grille). P quitte la colonne « démarrées » du Kanban ;
  `deleteNode(P)` aboutit et emporte ses lignes.
- **Preuve** : relu de la route au noyau ; le relecteur a exécuté les fonctions d'état sur un
  arbre construit à la main. Non rejoué par HTTP.
- **À trancher** : la spécification est muette sur cette transition (refuser la sous-tâche, ou
  faire entrer l'état propre dans l'état dérivé).

### B3 — À la réimportation MS Project, une tâche ajoutée peut prendre l'identité d'une tâche existante (BEX-01)

- **Issue** : #3337, `[EP-06]`, sous le lot d'origine US-1430/L3 (#2342) — décision : à trancher.
- **Où** : `core/planning/importing.py:260-280` (`_matched`).
- **Quoi** : une seule passe dans l'ordre du fichier, « par la lignée, sinon par l'`UID` ». Une
  tâche ajoutée dans MS Project (sans lignée) dont l'`UID` égale l'`external_id` gardé d'une tâche
  existante la prend — lignée, lignes de devis, état, rattachement — et la vraie tâche, lue plus
  bas avec sa lignée, est recréée vide.
- **Précondition** : des `external_id` supérieurs au nombre de tâches, c'est-à-dire un fichier
  d'origine dont les `UID` avaient des trous (le cas ordinaire d'un planning MS Project qui a
  vécu), et l'export renumérote les `UID` de 1 à n (`exporting.py:194`).
- **Preuve** : logique relue ; le relecteur l'a exécutée sur `_matched`. Pièce non vérifiée : que
  MS Project numérote une tâche ajoutée « plus grand `UID` + 1 ». Le test qui cite « retravaillé »
  réimporte un fichier non modifié.
- **Correction** : deux passes — toutes les lignées d'abord, les `UID` ensuite sur ce qui reste.

### B4 — Une grandeur saisie avec plus de décimales que sa colonne donne un montant qui change sans saisie (BCH-01)

- **Issue** : #3338, `[EP-07]`, sous le lot d'origine US-1490/L3 (#2372) — décision : à trancher.
- **Où** : `core/estimate/entries.py:167-176, 252-274` ; `platform/decimals.py:29-43` ;
  `core/estimate/tables.py:46-49`.
- **Quoi** : la garde ne refuse qu'au-delà de **dix** décimales ; les colonnes en gardent 2
  (heures, débours) ou 4 (quantité). Le montant est calculé sur la saisie, puis PostgreSQL arrondit
  la grandeur.
- **Scénario** : 7,333 h × 100 donne 733,30, stocké avec 7,33 h ; au premier rechiffrage sans
  saisie, 733,00. Le classeur d'origine réimporté présente la ligne « modifiée » à chaque fois.
  Voies : API, collage, import Excel.
- **Preuve** : garde et précisions relues ; l'écriture en base n'a pas été jouée. L'amplitude est
  faible (quelques centimes par ligne), mais le montant conservé ne se recalcule plus de ses
  propres grandeurs.
- **Correction** : juger les décimales contre l'échelle de la colonne (422), ou arrondir la
  grandeur avant le calcul.

### B5 — Un bloc collé dans le planning écrit sur les lignes de devis que la grille ne montre pas (FGR-01)

- **Issue** : #3339, `[EP-06]`, sous le lot d'origine US-1450/L6 (#2577) — décision : à trancher.
- **Où** : `frontend/src/components/grid/paste.ts:324-354` ; `planning.tsx:90` ;
  `backend/src/waterfall/core/planning/interface/paste.py:735-742`.
- **Quoi** : le serveur remplit « le nœud à la même distance, dans l'ordre du plan », tâches **et
  lignes** ; la garde du front suppose qu'une grille qui colle lit tous les genres de nœud, or le
  planning ne lit que les tâches. Une lecture non restreinte laisse donc passer.
- **Scénario** : tâche 1 portant trois lignes de devis, puis tâche 2. Coller deux libellés sur la
  tâche 1 pour renommer les deux tâches renomme la tâche 1 et **la première ligne de devis** ;
  l'aperçu ne donne que des comptes, la grille ne montre rien de ce qui a été écrit.
- **Preuve** : branche finale de la garde et ordre du plan côté service relus. Non exécuté. Les
  tests collent dans le planning d'un projet sans ligne de devis.
- **Correction** : faire porter au collage les genres que la grille lit, ou rendre à l'aperçu les
  rangs écrits.

### B6 — Le suivi d'une tâche de fond cesse d'interroger à la première lecture inchangée (FPL-01)

- **Issue** : #3103 (EP-25, US-2170), **fermée le 2026-11-14** : corrigé sur `epic/EP-25` par US-2170/L2
  (#3331), qui réarme la lecture à chaque réponse et nomme cette même cause. Le défaut reste dans
  `main` jusqu'à la fusion d'EP-25 ; aucune issue nouvelle.
- **Où** : `frontend/src/components/tasks/tracking.ts:290` ; `task-entry.tsx:291-314`.
- **Quoi** : le minuteur n'est réarmé que par l'effet qui dépend de `entry` ; une lecture qui
  trouve la tâche inchangée rend l'état tel quel, donc l'effet ne repart pas. Le worker n'écrivant
  `progress` qu'à 0 puis 100 (`worker/runner.py:109`), toute tâche encore `running` à la deuxième
  lecture n'est plus jamais lue : fin jamais annoncée, « Télécharger » jamais offert.
- **Preuve** : relu. **Symptôme déjà connu** (#3103, EP-25 US-2170), dont la cause était dite « à
  établir » : la voici. WF-IHM-0080-A est close et non tenue.
- **Correction** : réarmer le minuteur à chaque réponse, changée ou non.

## 4. Spécification

**État** : le texte est solide. Tous les exemples chiffrés des Vérif ont été recalculés (FBS-4 en
entier, référentiel, chapitre 4) : **aucun n'est faux**. L'index est exact (218 exigences, 0 écart
avec le corps), la volumétrie se recalcule. Les défauts sont des silences et un retard sur le
livré.

### Majeurs

| ID | Où | Défaut | Vérif. |
|---|---|---|---|
| SPB-01 = BPR-02 | WF-REV-0040 ; `core/revisions/interface/reference.py:77-99` | La référence se corrige encore après la réception d'un coût réel : seule « aucune révision marquée depuis » est jugée. EP-04 renvoyait la condition à EP-09, qui ne la porte pas ; EP-08, qui clôt, ne la nomme pas. | relu |
| SPB-02 | spec:1984-1986, 2557 ; `core/estimate/keeping.py:191-232` | Au changement d'année de référence, le taux horaire est projeté mais rien n'est dit du débours unitaire : un débours de 8 000 consommé en 2028 à 3 % vaut 8 487,20 en révision 2026 et 8 240,00 en révision 2027. À trancher par l'auteur. | relecteur (confirmé, calculé) |
| SPB-03 | spec:2710, 2314 ; `core/planning/interface/nodes.py:803-816` | Une tâche non démarrée ou une ligne budgétée se supprime en revue sur un projet En cours ; la référence la garde, donc la valeur acquise ne peut plus atteindre le budget (Vérif de WF-IND-0030 faux à l'arrivée d'EP-10). | relecteur (confirmé) |
| SPB-04 | spec:2254, 2266 ; `scheduling/engine.py` | Aucune règle ne dit ce qu'impose une liaison portée par une récapitulative ; le moteur a tranché seul (voir B1, BPL-06, BPL-07). | rejoué |
| SPA-01 | WF-ADM-0020, 0070, 0090, 0180 ; `api/org_nodes.py:48-50` et quatre autres | Un compte sans aucun rôle lit tout le référentiel actif. C'est la décision du 2026-11-01 (`DECISIONS.md:10448-10476`), qui contredit le Vérif de WF-ADM-0180 (« elle n'a aucun droit »), close par EP-03 ; la spécification n'a pas été révisée. | relecteur (confirmé) |
| SPA-02 ≈ BAC-08 | WF-ADM-0110, WF-PRJ-0060 ; `api/actual_costs.py:155` | « Action structurante » n'a pas d'extension définie : l'exclusion d'une ligne de coût est ouverte à tout contributeur, quand marquage, abandon et désignation exigent un chef de projet. Aucune décision consignée. | relu (la route) |
| SPT-02 = SPA-07 | WF-DAT-0070 ; `core/projects/tables.py:169-184` | La liste des contributeurs se crée, change et se retire sans auteur ni date : ni colonnes d'audit, ni inscription au journal. Exigence close par EP-09. | relu |
| SPT-03 | §4 ; `compose.prod.yaml:313-330`, `platform/maintenance.py:73-105` | La restauration livrée (service à part, maintenance tenue dans Redis seul) n'est nulle part au chapitre 4 : PBS-2.2, WF-ARC-0090, figure 18 et tableau 8 décrivent autre chose. | relecteur (confirmé) |
| SPT-04 | spec:2326, 4043, 4241 | Le fuseau de l'installation est au **corps** de WF-PLA-0130, WF-DAT-0100 et WF-EXP-0020 et au **Vérif** d'aucune : c'est ce qui a laissé clore les deux dernières alors que le jour courant est pris en UTC (défaut de code connu, #2527). | relecteur (confirmé) |

SPA-03 (santé du pilotage, WF-PTF-0110) est un défaut de texte sur le portefeuille, non livré : noté
pour EP-11, hors décompte.

### Mineurs

- **Silences du texte que le contrat ou le code ont dû trancher** : arrondi d'un montant calculé
  écrit dans le seul contrat (SPB-05) ; interdiction de la barre oblique et longueur du code projet
  (SPB-06) ; codes de sous-projet réservés et casse (SPB-07) ; phase du reste à engager et du Kanban
  (SPB-08) ; « année de consommation » scalaire ici, répartition là (SPB-09) ; tâche sans heure
  travaillée qui n'est pas un jalon (SPB-10) ; avance qui place une tâche avant le début du
  planning (SPB-11) ; six règles de saisie du référentiel (SPA-14) ; purge des tâches de fond sans
  Vérif (SPT-10).
- **Contradictions et imprécisions** : deux règles de terminaison dans WF-INTF-0120 (SPA-12) ;
  « le refus nomme la condition » contre le 404 uniforme, dans la même exigence (SPA-05) ; le rôle
  « chef de projet » livré porte cinq permissions que WF-INTF-0010 ne nomme pas (SPA-06) ; la
  lignée voyage dans `Text1`, pas dans « le champ d'identifiant unique », et l'import relit un
  champ personnalisé (SPA-11) ; Vérif de WF-IHM-0100 qui ne constate que trois points sur quatre
  (SPB-16) ; WF-QUA-0050, « trois parcours » pour cinq propositions (SPT-16) ; vocabulaire —
  « chef de projet » a trois sens, « l'exploitant » n'est pas défini (SPA-15, SPT-14).
- **Spécification en retard sur le livré** : WF-DAT-0090, trois phrases que le schéma ne suit pas
  (SPT-07) ; tableau 10 et amorçage (SPT-08) ; avatar « 512 Ko » quand `bootstrap.py:100` livre
  2 Mio (SPT-09) ; figure 19 sur l'abandon d'import (SPT-11) ; énumérations de WF-SEC-0030 et
  WF-ARC-0090 (SPT-12) ; WF-ARC-0030 (SPT-13) ; tableau 8 et figure 18 (SPT-06) ; annexes B et C
  (SPT-17) ; WF-CMP-0020 tait `max_locks_per_transaction=1024`, sans lequel la restauration échoue
  dès quelques centaines de projets (SPT-05).
- **Comportements livrés à trancher** : la garde du dernier administrateur compte un compte qui ne
  peut pas se connecter (SPA-08) ; un rôle de ressource actif peut reposer sur une catégorie ou un
  calendrier désactivés (SPA-10) ; liste des contributeurs figée sur un projet terminal (SPA-13) ;
  le code d'un projet En cours peut être effacé — D-06, « reste ouvert », sans porteur (SPA-04 =
  BPR-07).
- Non encore réalisés, pour mémoire : SPB-13, SPB-14, SPB-15.

## 5. Conception des EPIC et roadmap

**État** : mécanique irréprochable — chacune des 218 exigences est close par un seul EPIC, les
1 628 phrases de Vérif citées par les US sont mot pour mot dans la spécification, toutes les US des
EPIC livrés sont `fini`, le README concorde avec les front matter. Les Conceptions du back sont
celles du code (migrations 0018 à 0028, 21 registres d'extension, aucun import de tables entre
modules). **Le défaut de fond est unique : une exigence est dite close sur la présence de sa phrase
dans une US, pas sur sa preuve.**

### Majeurs

| ID | Où | Défaut | Vérif. |
|---|---|---|---|
| RMP-02 | `EP-02:80, 86` | WF-IHM-0010-A et 0070-A restent « entières, closes par EP-02 » alors qu'une phrase de Vérif ajoutée par la 1.0.6 attend EP-27 et EP-25, dont les tableaux ne les portent pas — contre `README-fr.md:58-62`. | relecteur (confirmé) |
| RMP-03 | `EP-09:1654-1655` | WF-IHM-0080-A close sans que le marquage « de dix mille objets » ait été constaté ; les renvois tournent en rond entre EP-02, EP-04 et EP-09. | relecteur (confirmé) |
| RMP-04 | `EP-04:110` | WF-ADM-0160-A close par EP-04 alors que deux phrases ont un défaut reporté à EP-13, dont le tableau n'a pas l'exigence (déjà connu : #1743, #2229). | relecteur (confirmé) |
| RMP-05 = FTE-01 | `EP-06:116` ; `tools/paths.toml:778` | WF-PLA-0090-A (Gantt), close par EP-06, n'est comptée que « front seul » : ses parcours contre le service vivent dans `planning-service.spec.ts`, hors de `e2e/service/**`. C'est la seule des 15 « front seul » close par un EPIC livré. | relecteur (confirmé) |
| RMP-06 | `EP-07:1113`, `EP-09:1436` | Deux phrases closes par « constaté par EP-06 », qui ne porte ni WF-DAT-0100-A ni WF-DAT-0070-A ; aucun test ne les prouve. | relecteur (confirmé) |
| RMP-07 | `EP-24:64-67`, `EP-05:968` | La reprise de la capacité d'un rôle (WF-REF-0100-A) est dite reportée à EP-10 (#2978) ; le fichier d'EP-10 n'en dit rien. | relecteur (confirmé) |

Voir aussi SPT-01 = PLC-02 au § 10 (`requirements-release` sans appelant) et CTC-01 au § 6
(WF-ADM-0070 close sans son opération).

### Mineurs

« Portée » dont l'autre bout ne répond pas (RMP-08) ; WF-IHM-0030/0040/0050 closes par EP-02 seul
alors que le back d'EP-06 et d'EP-07 les réalise (RMP-09) ; compteurs `lock_version` nés à 0 ou à 1
selon la table, dette remise « à la v1 » sans EPIC (RMP-10 = BPR-04) ; EP-10 `en cours` sur une
conception périmée — sa migration `0028` est prise par EP-24 (RMP-11) ; EP-07 `livré` avec un point
de sa définition de fini non tenu (RMP-12, connu) ; incohérences documentaires — « 212 exigences »
au README pour 218, ordre d'EP-21 (RMP-13) ; EP-26 annonce clore WF-QUA-0060 avant le jeu de
volumes d'EP-13 (RMP-14) ; écarts décidés dans des Conceptions et jamais remontés à la
spécification (DON-10).

## 6. Contrat d'API

**État** : excellent. 170 opérations au contrat, **132 servies, toutes conformes** en méthode,
chemin, `operationId` et statut de succès. Les 38 non servies relèvent d'EP-08, EP-10, EP-11 et
EP-13, sauf deux (CTC-01). Aucun `$ref` cassé sur 3 915, `required` cohérent partout, **les 1 587
exemples valident leur schéma**, les 73 codes d'erreur levés par le back sont tous énumérés,
`lock_version` et 412 sur chaque écriture hors exceptions décidées. Le front n'a qu'un `fetch`, dans
le client. Les défauts sérieux sont de conception, écrits au contrat et suivis fidèlement.

| Famille | Contrat | Servies | Non servies | Dues par |
|---|---|---|---|---|
| system | 8 | 5 | 3 | EP-13 |
| me | 5 | 5 | 0 | — |
| access | 20 | 18 | 2 | aucun EPIC (CTC-01) |
| platform | 10 | 5 | 5 | EP-13 |
| audit | 2 | 2 | 0 | — |
| reference | 31 | 31 | 0 | — |
| projects | 19 | 19 | 0 | — |
| revisions | 31 | 28 | 3 | EP-08 |
| analysis | 10 | 5 | 5 | EP-10 |
| risks | 12 | 0 | 12 | EP-08 |
| costs | 3 | 3 | 0 | — |
| exchanges | 11 | 11 | 0 | — |
| portfolio | 8 | 0 | 8 | EP-11 |

### Majeurs

| ID | Où | Défaut | Vérif. |
|---|---|---|---|
| CTA-01 = BAC-01 | `paths/access.yaml:527-528` | Voir § 7, sécurité : `createPasswordSetupLink` sous `users.write` seul. | relu |
| CTA-02 = BAC-02 | `schemas/access.yaml:109-118` | Voir § 7 : la garde du dernier administrateur. | relu |
| CTC-01 = CTA-03 | `paths/access.yaml:708-776` ; `frontend/src/app/admin/users/page.tsx:172-176` | `getIdentitySyncSchedule` et `setIdentitySyncSchedule` sont au contrat et appelées par l'écran livré ; le service répond 404, aucun EPIC ne les doit, et le front retire la section sans rien dire. WF-ADM-0070-A (« périodicité choisie par un utilisateur habilité ») est pourtant close. | relecteurs ×2 (confirmé) |
| CTB-01 = BEX-02 | `schemas/exchanges.yaml:1009-1019` ; `core/planning/interface/msproject.py:113-116` | `applyImport` n'a aucune garde de péremption ; l'application d'un planning jette le compte rendu (`del report`) et rebâtit le plan : une tâche créée entre l'analyse et la confirmation (jusqu'à 24 h) est supprimée avec ses lignes sans avoir figuré au compte rendu confirmé. Le contrat dit « the confirmed report is what applies ». | relu |
| CTB-02 = BAC-09 | `paths/exchanges.yaml:4-45` ; `api/imports.py:148-151` | `uploadFile` est la seule écriture sans permission : tout compte authentifié, même sans rôle, dépose 10 Mio par requête, gardés 24 h, sans quota. | relecteurs ×2 (confirmé) |
| CTB-03 | `schemas/access.yaml:416-433` ; `frontend/src/components/gantt/timeline-chart.tsx:132` | Les couloirs d'une chronologie sont rangés par `node_id` ; la copie d'une révision donne un identifiant neuf à chaque nœud : la disposition retombe en empilement automatique à chaque nouvelle révision (WF-PLA-0140). | relecteur (confirmé) |

### Mineurs

- **Bornes d'entrée absentes** : `payment_delay_days` sans maximum, 500 plausible au-delà de 2³¹
  (CTB-04) ; textes libres sans `maxLength` (CTB-05) ; listes d'écriture sans `maxItems` (CTB-06) ;
  entiers et décimaux sans borne haute (CTA-10) ; le 413 de `previewPaste`, seule borne de hauteur
  d'un collage selon la Conception d'EP-06, n'est jamais émis (CTC-03).
- **Statuts non déclarés ou non décrits** : `undoLastChange` et `redoLastUndo` peuvent répondre 422
  (CTC-02) ; plan de collage expiré sans `expires_at` ni 404 (CTB-07) ; tâche d'un autre compte
  = 404 non dit (CTA-08) ; `setHourlyRate` (CTA-09) ; `revision_id` non décrit sur trois
  opérations, 404 ici et 422 ailleurs (CTB-08).
- **Écarts du service** : `getProjectWorkload` répond 500 pour tous les projets tant qu'un rôle a
  une capacité sous 10⁻⁶ — `str()` rend `'1E-7'` (CTC-04, conversion relue) ; `VALUE_TOO_LONG` avec
  `maximum` au lieu de `max_length` (BAC-06) ; une archive non vérifiée échoue en
  `FILE_FORMAT_UNREADABLE` quand le contrat dit `STATE_FORBIDS_OPERATION` (BSO-02) ; `getImport`
  répond 500 sur un import sans tâche (BEX-07) ; corps redéclarés à la main qui doublent des
  modèles engendrés (CTC-05).
- **Cohérence** : `ProblemParams` non typé pour quatre paramètres (CTA-04) ; `correlation_id`
  facultatif bien que toujours rendu (CTA-05) ; pointeur `""` pour l'avatar (CTA-06) ; `Conflict`,
  `ActiveFlag` et `ProjectSummary` définis, jamais employés (CTA-07, CTB-14) ; champs nullables
  hors `required` (CTB-09) ; listes sans pagination non justifiées (CTB-10) ; deux vocabulaires
  pour une notion (CTB-12) ; `WorkloadPlan.roles` (CTB-13) ; filtres de `listActualCosts`
  (CTB-11).

## 7. Backend

**État** : solide dans sa structure. Cadre d'écriture unique (révision, verrou, une transaction
pour écriture et recalcul), versions jugées sous verrou, moteur en fractions exactes, `Decimal`
partout avec un arrondi unique par ligne, somme des parts égale au total, authentification stricte
(signature, `iss`, `aud`, `exp`, RS256 imposé), XML durci (XXE, entités, DTD vérifiés par
exécution), formules coupées à l'export Excel, frontières du noyau tenues. **Tableau des 132 routes
dressé : toutes authentifiées sauf `/health` et `/installation`, aucune écriture sans garde, aucun
IDOR trouvé.**

### Sécurité et habilitations

| ID | Où | Défaut | Vérif. |
|---|---|---|---|
| **BAC-01** = CTA-01 | `api/users.py:672-698` ; `PasswordSetupLinkResource.java:86-95` | Un porteur de `users.read` + `users.write` obtient le lien de fixation du mot de passe de n'importe quel compte local, administrateur compris — le lien est forgé même si le compte a déjà un mot de passe —, ou change son adresse puis passe par « mot de passe oublié ». Il prend le compte et ses droits. C'est l'élévation que #834 a fermée pour `setUserAccessRoles`. **Condition** : un rôle composé portant `users.write` sans `access_roles.write` ; avec les trois rôles livrés, seul l'administrateur porte `users.write`. Trois relecteurs l'ont relevé ; deux le tiennent pour bloquant. **Issue : #3342**, `[EP-03]`, sous US-0350/L5 (#447), à trancher. | relu |
| BAC-02 = CTA-02 | `core/access_roles/administrators.py:33` ; `api/access_roles.py:57-59` | La garde du dernier administrateur ne compte que `users.write` et `access_roles.write`, alors que les routes exigent aussi les deux `.read`. Décocher « consulter » sur le rôle Administrateur passe la garde et laisse l'installation sans personne capable d'attribuer un rôle : intervention en base. | relu |
| BRC-02 = BEX-03 = BCH-06 | `core/costs/extraction.py:93-109` ; `core/estimate/excel/reader.py:199` ; `core/exchanges/interface/imports.py:452` | Aucune borne de décompression des classeurs : un `.xlsx` de 68 Ko fait tenir 64 Mio à `load_workbook` (mesuré par le relecteur), 10 Mio en donnent environ 10 Gio, dès `openImport`, dans le processus de l'API et sous le verrou du projet. Exploitable par un contributeur portant `estimate.write`, `remaining.write` ou `actual_costs.write`. | relecteurs ×3 (mesuré) |

### Planification

| ID | Où | Défaut | Vérif. |
|---|---|---|---|
| BPL-03 | `scheduling/engine.py:150-171` | Une durée écoulée de moins d'un jour donne une marge négative sans conflit (A à −0,625 j). **Déclaré clos** par US-1820 d'EP-23 (#2816), qui n'éprouve que 1, 2, 3 et 5 ej. | rejoué |
| BPL-04 | `scheduling/engine.py:278-288` | Passe arrière quadratique sur une liaison entre récapitulatives : 3,6 s pour dix phases de 100 feuilles enchaînées contre 0,1 s pour une chaîne plate de 1 000, à chaque écriture, verrou de la structure tenu. | rejoué |
| BPL-05 | `core/planning/dating.py:152-158` | `TaskWithoutWorkingHoursError` du moteur n'est traduit nulle part : un changement de calendrier fait pendant qu'un projet n'a pas de révision en cours rend l'ouverture de la suivante en 500. | relecteur (plausible) |
| BRC-01 ≈ BCH-07 | `core/resource_settings/interface/calendars.py:446-450` ; `resource_roles.py:590-633` | Depuis EP-07 une tâche suit les calendriers des rôles de ses lignes, mais seul le calendrier par défaut déclenche le recalcul : modifier un calendrier de rôle laisse les dates et les montants projetés périmés jusqu'à une écriture sans rapport. Un test épingle l'ancien comportement d'EP-06. | relecteur (confirmé) |

### Projets, révisions, chiffrage, échanges, socle

| ID | Où | Défaut | Vérif. |
|---|---|---|---|
| BPR-01 | `core/projects/interface/work_breakdown.py:552` | `setWorkBreakdown` verrouille le projet puis écrit des tâches de la révision — l'ordre inverse de `submit_marking` et d'`abandon_revision` : interblocage possible, 500, aucune reprise sur `40P01`. Fenêtre étroite. | relecteur (confirmé) |
| BCH-02 | `core/estimate/costing.py:172-187` | Une tâche datée hors de 2000-2100 viole `ck_estimate_line_consumption_year_bound` : 500 au lieu de 422 sur la création d'une ligne et sur tout redatage. | relecteur (confirmé) |
| BCH-03 | `core/estimate/excel/reader.py:361-369` ; `remaining/analysing.py:369` | Un en-tête absent d'un onglet se lit comme des cellules vides ; `missing_headers` n'est lu par aucune analyse. Au reste à engager, « Jours restants » absent met les restes à zéro et **termine des tâches** ; « ID ligne » absent supprime et recrée tout, lignées et budgétés perdus. Le compte rendu montre cela comme des modifications ordinaires. | relu (le champ n'est jamais lu) |
| BCH-04 | `core/estimate/workloading.py:234, 323-325` | Le plan de charge de la référence, pourtant marquée, s'étale sur les calendriers du jour et non sur ses images : un changement de calendrier déplace la répartition (WF-REF-0130, WF-DEV-0080). | relecteur (confirmé) |
| BCH-05 | `core/estimate/applying.py:88-90` | À l'import du devis, chaque ligne absente est supprimée par une écriture d'arbre complète : 5 000 rejeux du moteur pour un devis de 5 000 lignes sans lignée, verrou tenu. | relecteur (plausible) |
| BSO-01 = BEX-06 | `core/exchanges/interface/purge.py:177-203` | La purge supprime dès son échéance le dépôt qu'une restauration acceptée désigne, contre le contrat (`platform.yaml:505-507`) : une reprise ne retrouve plus l'archive et la restauration s'abandonne en maintenance. | relecteurs ×2 (confirmé) |
| FGR-07 ≈ BCH-09 | `core/estimate/pasting.py:81-87` | Les nombres collés sont lus sans la langue de l'utilisateur : en interface anglaise, « 1,234 » est écrit 1,234 sans refus ; l'espace fine U+202F, que la grille affiche elle-même, est refusée. | relecteurs ×2 |

### Mineurs

- **Planification** : marge négative sans conflit quand la liaison vise la récapitulative d'une
  tâche manuelle (BPL-06, rejoué) ; FF et DF vers une récapitulative retardent chaque subordonnée
  (BPL-07, rejoué, règle à trancher) ; fin d'une tâche manuelle à durée écoulée non bornée aux
  heures du jour (BPL-08) ; récursions non bornées sur la profondeur de l'arbre, `RecursionError`
  vers 1 000 niveaux (BPL-09, BEX-08) ; l'abandon d'une révision laisse ses `tracking_entry`
  (BPL-10) ; ordre d'import fragile des modules privés (BPL-11) ; lectures de toute la structure
  pour une ligne (BPL-12).
- **Comptes et habilitations** : `undo`/`redo` révèlent l'existence et l'état d'une révision d'un
  autre projet par 404 contre 409 (BAC-03) ; un export reste téléchargeable après retrait des
  droits (BAC-04) ; avatar accepté sur trois octets de signature, EXIF gardé, sans `nosniff`
  (BAC-05) ; `setEmailVerified(true)` pour un lien remis à la main (BAC-07) ; comptes rendus des
  devis et des coûts lisibles sous `planning.read` seul (BAC-08, BEX-12) ; tests de sécurité sans
  exigence citée, un sans assertion (BAC-10) ; lecture des comptes qui ne désactive pas un compte
  désactivé dans l'annuaire (SPA-09, plausible).
- **Projets et révisions** : année de référence prise en UTC (BPR-03) ; `EXISTS` sans `project_id`
  et N+1 dans `listRevisions` (BPR-05, BPR-06 = DON-01) ; `updateProject(inflation_rate)` rechiffre
  pendant qu'un marquage est en file (BPR-08) ; l'API importe des fichiers privés du noyau, que
  import-linter ne voit pas (BPR-09, BRC-09) ; comparaison de deux horloges (BPR-10) ; fenêtre
  d'interblocage documentée et laissée ouverte (BPR-12).
- **Chiffrage** : coefficient de l'export d'une révision marquée au taux d'inflation courant
  (BCH-08) ; taux manquant jugé à l'application seulement (BCH-10) ; reste à engager importé en
  montant qui ne redonne pas le montant saisi — 100 sur une quantité 3 donne 99,99 (BCH-11) ;
  requêtes sur toutes les révisions du projet (BCH-12) ; critères `SOMME.SI.ENS` bâtis sur des
  libellés libres (BCH-13).
- **Référentiel et coûts** : analyse de l'en-tête d'un classeur sous le verrou du projet (BRC-03 =
  BEX-05) ; ligne rejetée en doublon à cause d'un autre projet du même fichier — décidé (#2724), à
  revoir (BRC-04) ; bornes de la matrice de risques acceptées hors de [0 ; 1] (BRC-05) ; `.one()`
  qui rend 500 au lieu de 503 (BRC-07) ; poste et motif d'exclusion sans borne (BRC-08) ;
  `test_cost_imports.py` vide (BRC-10).
- **Échanges** : l'écouteur `after_commit` part à la libération d'un point de sauvegarde — le
  fichier d'un import est supprimé avant le COMMIT de sa tâche (BEX-04 = BSO-04, mécanisme
  exécuté sur SQLite) ; valeurs hostiles qui finissent en 500 (BEX-08) ; tâche manuelle devenue
  automatique sans signal (BEX-09) ; panne passagère du stockage qui fait échouer l'import pour de
  bon (BEX-13) ; aucune borne au nombre de tâches importées — 90 000 tâches dans 6,6 Mio (BEX-14).
- **Socle** : après une restauration, `create_project_partitions` redevient exécutable par
  `PUBLIC` (BSO-03 = DON-06) ; ni `statement_timeout` ni `lock_timeout`, pool de 15 connexions pour
  40 fils (BSO-06) ; purge planifiée qui ignore la maintenance (BSO-07) ; jeton du compte de
  service demandé verrou tenu (BSO-08) ; restauration abandonnée après 90 s de Keycloak injoignable
  (BSO-05).

## 8. Modèles de données

**État** : le schéma est solide. Chaîne 0001 → 0028 linéaire, types exacts, unicités du § 4.4.1
toutes déclarées, immuabilité par déclencheurs sur les neuf tables révisionnées (`OLD` et `NEW`
jugés, `TRUNCATE` refusé), journal d'audit protégé, rôle de service sans DDL. **Aucune divergence
entre les 28 migrations et les 12 `tables.py`.** Le schéma final reconstitué table par table est en
annexe du rapport `donnees`. Ce qui inquiète est dans les requêtes, qui grandissent avec l'histoire
des révisions et non avec le projet ouvert.

### Majeurs

| ID | Où | Défaut | Vérif. |
|---|---|---|---|
| DON-01 | `core/planning/interface/nodes.py:209`, `lines.py:233`, `skeleton.py:150` | Des `EXISTS` sur `node` filtrés par la seule révision, sans `project_id` : aucune partition élaguée (WF-DAT-0050), joués 2 à 3 fois par révision listée. | relecteurs ×2 (confirmé) |
| DON-02 | `core/estimate/interface/calendars.py:41-72` | La garde des calendriers lit les lignes de devis de toutes les révisions de tous les projets, marquées comprises, puis filtre en Python — à chaque `updateCalendar`, `setDefaultCalendar`, `updateResourceRole`. | relu |
| DON-03 | `core/estimate/interface/employment.py:34-43` | « Catégorie employée ? » est un `DISTINCT … IN` sur toutes les lignes de devis de la plateforme, joué à chaque liste des natures et des catégories. | relu |

### Mineurs

Pas d'index sur `node.lineage_id` (DON-04) ; `import_report` jamais supprimé, contre le § 4.4.1 et
la Conception d'EP-06 (DON-05 = BEX-11) ; invariants simples laissés au service — ligne de devis
sans parent, nœud parent de lui-même, `is_reference` sur une révision `draft` (DON-07) ; clés qui
ne nomment pas le projet, rattachement entre deux projets admis par la base (DON-08, BPR-11) ;
colonnes `*_id` sans clé non justifiées (DON-09) ; le test de la « descente miroir » ne prouve que
la descente de la chaîne entière sur base vide (DON-11) ; `0005` et `0006` importent du code
applicatif (DON-12) ; purge qui verrouille tous les exports réussis de l'histoire (DON-13 =
BEX-10) ; droits inemployés du rôle de service (DON-14) ; `backup.task_id` en `RESTRICT` (DON-15,
connu en partie : #921).

## 9. Frontend

**État** : rigoureux. Aucun montant, total, marge ni pourcentage n'est calculé côté front — tout
passe par `i18n/format.ts` depuis la chaîne du contrat. Flux OIDC correct (state à usage unique,
nonce, PKCE S256), aucun jeton côté navigateur, pas de redirection ouverte. Gantt entièrement en
UTC. Commandes lues de `available_commands` partout. Catalogues fr et en à 2 879 clés jumelles,
aucun argument ICU divergent. Aucun `any`, `dangerouslySetInnerHTML`, `localStorage` ni commentaire
d'exemption ; aucun test sans assertion sur les 5 168. Parcours : `retries: 0`, aucun
`waitForTimeout`, et chaque domaine livré a un parcours contre le vrai service qui écrit puis
relit.

### Majeurs

| ID | Où | Défaut | Vérif. |
|---|---|---|---|
| FGR-02 | `components/grid/grid-keyboard.ts:503` | Une valeur retapée égale à la valeur **lue**, pendant qu'une écriture de la même cellule est en route, n'est pas envoyée : 10 → 100 → 10 enregistre 100. | relu |
| FGR-03 | `components/grid/undo-commands.tsx:494` | Le menu contextuel garde l'indice de sa ligne, pas son identité : une relecture arrivée menu ouvert le fait agir sur une autre ligne, et une feuille est supprimée sans confirmation. | relecteur (une pièce non vérifiée) |
| FGR-04 | `components/grid/cell-writes.ts:296-306` | Seuls les clics sur un lien attendent les écritures en route ; tri, recherche et filtres partent aussitôt : la réponse d'une écriture arrivée après est jetée, et son refus n'est dit nulle part. | relecteur (confirmé) |
| FGR-05 | `components/grid/structure-gestures.tsx:472-513` | Pendant la relecture qui suit un geste ou une annulation, les cellules restent saisissables avec une `lock_version` périmée : 412, saisie à refaire. | relecteur (confirmé) |
| FGR-06 | `components/grid/nodes.tsx:318` | `link_conflicts`, que le service rend pour chaque tâche redatée, n'est pas repris : la marque de conflit de la grille et du Gantt reste fausse jusqu'au rechargement. | relecteur (une pièce non vérifiée) |
| FCO-01 ≈ FPL-03 | `app/projects/…/estimate/page.tsx:322`, `remaining/page.tsx:285` ; `api/actions/nodes.ts:100-320` | Les cartes d'indicateurs du devis et du reste à engager ne sont pas relues après une saisie de cellule : la ligne des totaux est à jour à côté d'une carte d'avant la saisie. Au retour arrière, la page réemployée montre les lignes d'avant, puis 412. | relu (les actions ne relisent rien) |
| FCO-02 | `components/exchanges/report-commands.tsx:78-85` | « Relancer » est offert sur une application d'import échouée, alors que l'import est `failed` et son fichier supprimé : le bouton redonne toujours le même 409. | relecteur (confirmé) |
| FPL-02 | `components/projects/contributor-commands.tsx:332-595` | Le dialogue des contributeurs n'inscrit que les comptes suggérés : sur un projet sans ligne de devis, un chef de projet ne peut inscrire personne, et le contrat n'a pas d'opération de recherche de comptes pour lui (WF-PRJ-0060-A, 0070-A). C'est la Conception d'EP-14 qui est en cause. | relecteur (confirmé) |
| FAR-01 | `components/system/maintenance.tsx:108-122` | Le suivi d'une restauration s'arrête pour de bon au premier rejet d'une action serveur : une coupure réseau laisse l'écran de maintenance tourner sans fin. | relu |
| FAR-02 | `components/admin/user-cells.tsx:336-344` | La liste « Rattachement » d'un compte est inatteignable au clavier dans la grille (`<select tabIndex={-1}>`). | relecteur (confirmé) |
| FAR-03 | `app/reference/risks/page.tsx:41` et deux autres | Trois écrans du référentiel se présentent par adresse directe sans la permission `.read` que le contrat dit ouvrir « la présentation des écrans ». Pas de fuite au sens du contrat. | relecteur (confirmé) |
| FSO-01 | `app/auth/callback/route.ts:95-100` | Après une connexion refusée par le fournisseur d'identité, l'écran dit « Session requise » et non que la connexion a été refusée ; le critère d'US-1870 a réécrit le Vérif de WF-SEC-0020-A. Mineur si la lecture de l'EPIC est admise. | relecteur (confirmé) |
| FTE-02 | `frontend/e2e/reference-resources.spec.ts:284-331` | Le parcours des unités de durée écrit « l'autre de 7 et 8 » heures par jour et ne remet rien ; depuis EP-06 cela redate le témoin : un rejeu sur deux de `make e2e-service` lit un témoin redaté. | relecteur (plausible) |

### Mineurs

- **Grille** : pas de garde `beforeunload` pendant qu'une file d'écritures attend (FGR-08) ; marque
  « en attente » levée par la réponse de l'écriture précédente (FGR-09) ; saisie invalide quittée
  au clic abandonnée sans avis — « 12.5 » du pavé numérique en français (FGR-11) ; composition de
  caractères, Entrée d'un IME (FGR-12) ; rendus évitables à chaque déplacement du curseur (FGR-14).
- **Socle** : témoin de liaison sans préfixe `__Host-` (FSO-02) ; adresse mémorisée non contrôlée,
  `http:evil.example/projects/…` devient le lien « Retour au projet » (FSO-03, relu) ; sortie de
  projet et marquage sans retenue du refus (FSO-04, FSO-05) ; code de refus par champ inconnu
  affiché en clé brute (FSO-06) ; aucun délai sur les appels à l'API (FSO-07) ; `/login` anonyme
  écrit une clé Redis par requête sans limite de débit (FSO-08) ; champ de recherche inerte
  (FSO-09) ; catalogue entier de 199 Ko sérialisé dans chaque document (FSO-10).
- **Planning** : barres du Gantt au jour même au niveau « heures » (FPL-04) ; graduations de l'axe
  entier dessinées par ligne (FPL-05) ; pas de défilement temporel au clavier (FPL-06) ; révision
  abandonnée qui rend des écrans introuvables (FPL-07) ; listes qui ne suivent pas l'adresse
  (FPL-08).
- **Administration** : « Ajouter un rôle » groupé offert sans `access_roles.write` (FAR-04) ;
  boutons de dialogue sans `aria-haspopup` (FAR-06) ; chaînes bâties par `.join` (FAR-07, FCO-12) ;
  adresse d'un compte local non corrigeable (FAR-08) ; désactivations en cascade sans confirmation
  (FAR-09).
- **Coûts et échanges** : réponse d'un dépôt qui ferme un autre formulaire (FCO-03) ; 409 définitif
  qui ne relit pas l'écran (FCO-04) ; zone de dépôt verrouillée après un import abandonné
  (FCO-05) ; compte rendu rendu sans borne, jusqu'à 18 000 rangées (FCO-06) ; maquette —
  FCO-07 à FCO-11.
- **Tests** : tests qui citent une exigence dont ils n'éprouvent pas le Vérif (FAR-05, FTE-03 à
  FTE-05) ; citations `[WF-IHM-0020]` sans indice de révision, ignorées sans erreur par
  `make requirements` (FCO-13) ; le projet `node` de Vitest ne refuse pas `console.error`
  (FTE-06) ; deux clés mortes au catalogue (FTE-07) ; page de connexion Keycloak jamais auditée,
  écrans audités en français seulement (FTE-08) ; sélecteurs par classe CSS (FTE-09) ; attendu
  dépendant du fuseau du poste (FTE-11) ; 347 noms accessibles recopiés du catalogue (FTE-13).

## 10. Paramétrage de la plateforme

### Déploiement

**État** : sain. Aucun secret par défaut en production, aucun port de donnée publié, trois rôles
PostgreSQL au moindre privilège, royaume strict, extension Java propre avec un test par refus.
Chaque variable requise par `settings.py` est fournie par chaque Compose ; les cibles, fichiers et
variables d'`INSTALL.md` existent.

| ID | Où | Défaut | Vérif. |
|---|---|---|---|
| PLD-01 | `deploy/keycloak/realm/waterfall.yaml:27` | `resetPasswordAllowed: true` alors que `compose.prod.yaml` n'a aucune messagerie : « mot de passe oublié » mène à une page d'erreur pour un compte existant et à « courriel envoyé » pour une adresse inconnue — énumération des comptes depuis Internet. | relecteur (plausible, Keycloak non joué) |

Mineurs : mot de passe de Redis en argument de `redis-server`, lisible par `ps`, quand les en-têtes
disent l'éviter (PLD-02) ; mot de passe d'`admin` de `master` remis à chaque démarrage, contre
quatre commentaires (PLD-03) ; le planificateur dort avant de déposer — une plateforme redémarrée
chaque jour ne lit jamais les comptes (PLD-04) ; console cachée par une liste de refus (PLD-05) ;
`SECURITY.md` dit qu'aucun code ni version n'existe (PLD-06 = PLC-12) ; une autre empreinte de
Caddy dans `compose.prod.local.yaml` (PLD-07) ; `# syntax=docker/dockerfile:1` hors miroir et sans
empreinte, étape Maven hors du critère d'US-1180 (PLD-08) ; mot de passe du superutilisateur dans
une commande `psql -c` de la notice (PLD-09) ; faux back publié sur toutes les interfaces en
développement (PLD-10) ; textes en retard (PLD-11) ; Prism et uv installés hors verrou (PLD-12).

### Chaîne et outillage

**État** : sain. Aucune `pull_request_target`, actions épinglées par empreinte, `permissions`
déclarées partout, aucune interpolation d'événement dans un `run:`, caches écrits après fusion
seulement, aucun `continue-on-error` ni relance de test, fichiers de verrou versionnés.

| ID | Où | Défaut | Vérif. |
|---|---|---|---|
| PLC-02 = SPT-01 | `Makefile:255-256` ; `.github/workflows/images.yml:57-61` | WF-QUA-0010-A est close, mais `make requirements-release` n'a **aucun appelant** : la version est posée avec 37 exigences F0 non couvertes. Le relevé, statique, compte aussi les tests sautés (ceux du XSD MSPDI le sont à chaque passage). | relu |
| PLC-03 | `tools/src/wftools/guard.py:877` ; `.claude/settings.json:36` | Sous un `python3` antérieur à 3.14, le garde lève `NameError` à l'import et sort en code 1, que le harnais laisse passer : **toute commande passe, `pkill` compris, sans message**. C'est le cas de cette session (3.13). | rejoué |
| PLC-01 | `.github/rulesets/merge-queue.json` ; `tools/src/wftools/mergequeue.py:136-153` | Le modèle du jeu de règles de la file ne porte aucune `required_status_checks`, et `make merge-queue-check` passe sur une file sans contrôle exigé. L'exposition réelle dépend des réglages de GitHub, non lus. | relu (le modèle) |
| PLC-04 | `tools/src/wftools/slots.py:498-501` ; `.claude/agents/epic-deliverer.md:35-41` | À N = 1, le créneau d'un livreur arrêté sur limite d'usage reste pris tant que son worktree existe : la reprise rend « aucun créneau libre » sans fin. | relecteur (plausible) |

Mineurs : `make sources` laisse passer six formes d'exemption — aucune employée aujourd'hui
(PLC-05) ; fichiers qui ne réveillent pas la bonne famille de contrôles — `ruff.toml` ne réveille
pas `back` (PLC-06) ; formes que le garde laisse passer (PLC-07, connu en partie : #2417) ; cache
d'uv réécrit sur un changement du front seulement (PLC-08) ; `.github/actions/**` et `deploy/e2e`
non suivis par Dependabot (PLC-09) ; `packages: write` dans deux travaux de `pull_request`
(PLC-10) ; message trompeur de `make test-back` sous un autre `python3` (PLC-11) ; registre des
créneaux scindé selon `XDG_RUNTIME_DIR` (PLC-13) ; `make roadmap` ne lit pas le skill du pilote
(PLC-14) ; notice d'Arev absente (PLC-15).

## 11. Déjà connus et planifiés (rappel, hors décompte)

- **Le jour courant pris en UTC** au lieu du fuseau de l'installation — #2527, EP-25 US-2200.
  Relevé par six relecteurs (RMP-01, FCO-15, FPL-09, BEX-15, BPR-03). Ce qui est **nouveau** :
  WF-EXP-0020-A et WF-DAT-0100-A sont closes alors que leur corps n'est pas tenu (SPT-04), et
  l'année de référence d'une révision (BPR-03) n'est pas dans le périmètre d'US-2200.
- Aucun retour visible pendant un envoi ou un export — #3103, #3217, EP-25 US-2170 (cause établie :
  B6).
- `listBackups` ignore ses filtres et tris (#2231) ; les 409 de `startBackup` et `downloadBackup`
  ne sont jamais levés, une archive non vérifiée se télécharge (#1035) — EP-13.
- Capacité d'un rôle sans borne de précision — #2875, #2836, EP-10.
- Marge d'une révision marquée — EP-10 US-1670. Comparaison avec la révision en cours — #3176,
  EP-27.
- Quatre quarantaines de parcours contre le service — #3087, #3190, #3191, #3192.
- Performance mesurée sur le seul faux back — #3173, #3184, EP-26.
- Cinq défauts d'écran d'EP-25 US-2180 (#2260, #2266, #2267, #2268, #2270).

## 12. Ce qui n'a pas été couvert

- **Exécution** : tests du back, parcours de bout en bout, tests de Keycloak, aucune recette dans
  MS Project réel, aucune mesure de performance au volume du § 4.6.2.
- **Lecture partielle** : les tests du back et du front ont été échantillonnés bien en deçà du
  tiers demandé (noms, balayage mécanique des assertions, quelques corps) ; moins de la moitié des
  parcours `*.spec.ts` lus ligne à ligne ; `backend/src/waterfall/witness/` (6 fichiers sur 25) ;
  les filtres d'une table plate de la grille ; plusieurs primitives de `components/ui` ;
  `DECISIONS.md` consulté par recherche, jamais en entier ; les Conceptions des EPIC du front
  (EP-02, EP-14 à EP-17, EP-22) et de l'outillage (EP-01, EP-19 à EP-21).
- **Hors périmètre** : `tools/` (79 000 lignes) n'a été lu que pour les outils de la chaîne, pas
  les générateurs du faux back ; `fixtures/` validé par script seulement.
- **Non consultés** : les réglages réels de GitHub et l'état des issues.

Chaque rapport détaillé liste, à sa section « Couverture », ce qui a été lu en entier,
échantillonné ou non lu.

## 13. Ordre de traitement proposé

1. **B1, B3, B5** — résultats faux ou écritures au mauvais endroit, sans signal à l'utilisateur.
2. **B2** — après décision de la règle (une « Specification finding »).
3. **B6** — déjà corrigé sur `epic/EP-25` (US-2170/L2, #3331) : il arrive dans `main` avec EP-25.
4. **B4** — juger les décimales contre l'échelle de la colonne.
5. **BAC-01 et BAC-02** — reprendre la décision : exiger `access_roles.write` pour un lien sur un
   compte qui porte l'administration, et compter les quatre permissions dans la garde.
6. **BRC-02 / BEX-03 / BCH-06** — une borne de décompression dans la mécanique commune.
7. **CTB-01 / BEX-02 et BCH-03** — une garde de péremption à `applyImport`, et un refus sur
   en-tête manquant.
8. **PLC-02 et PLC-03** — brancher `requirements-release` sur la pose d'une version ; faire
   échouer le garde en fermé (code 2) quand il ne peut pas s'exécuter.
9. **SPB-04, puis BPL-03, BPL-04, BPL-06, BPL-07** — écrire la règle des liaisons de
   récapitulatives dans la spécification, puis reprendre le moteur d'un seul tenant, avec le test
   de propriété.
10. **Remonter à la spécification** ce que `DECISIONS.md` et les Conceptions ont tranché (SPA-01,
    SPT-03, SPT-07, SPT-08, DON-10) et ajouter le fuseau aux Vérif (SPT-04).

## 14. Suites au 2026-11-21

Chaque constat des 23 rapports porte désormais, sous son titre, une ligne **Issue** ou **Suite**.
Les 292 constats ont été recoupés avec les issues du dépôt, puis ceux qui n'en avaient pas — 2
bloquants, 50 majeurs, 170 mineurs — ont été relus un à un le 2026-11-21, par lecture du code et
sans exécution, contre `main` (`ac6464d13`) et les branches `epic/EP-08`, `epic/EP-11` et
`epic/EP-13`, pour ne garder que ce qui restera d'actualité après leur fusion.

| Suite | Constats |
|---|---|
| Issue ouverte le 2026-11-21, par la ventilation de ce jour (81 issues, #4411 à #4492) | 168 |
| Joint à une issue déjà ouverte | 7 |
| Issue antérieure à cette relecture, ouverte ou fermée (les six bloquants, la spécification, la chaîne) | 72 |
| Abandonné, par décision de l'auteur | 24 |
| Corrigé depuis la revue | 16 |
| Sans objet depuis la revue | 1 |
| Sans issue propre : tombera avec un lot prévu d'EP-13 | 4 |

Un mineur encore d'actualité n'a pas son issue à lui : il rejoint celle d'un majeur voisin, ou une
grappe de mineurs du même thème. Les issues ouvertes sont réparties par zone de code dans les EPIC
de correction EP-29 et EP-32 à EP-40 (`docs/roadmap/README-fr.md`, « Ordre des EPIC »). Les lieux
que les rapports citent valent pour le commit relu, `29785cc` ; chaque issue donne le lieu du jour.

## Annexe — les 23 rapports détaillés

Chaque constat y porte son lieu, son scénario, sa proposition de correction et de test, et sa
confiance. Un fichier par périmètre, dans [`2026-11-14-revue-complete/`](2026-11-14-revue-complete/) :

| Rapport | Périmètre |
|---|---|
| [`spec-a`](2026-11-14-revue-complete/spec-a.md) | Spécification, chapitres 1 à 3.4.4 |
| [`spec-b`](2026-11-14-revue-complete/spec-b.md) | Spécification, FBS-4 Projets et principes d'interface |
| [`spec-technique`](2026-11-14-revue-complete/spec-technique.md) | Spécification, architecture technique et annexes |
| [`roadmap-conception`](2026-11-14-revue-complete/roadmap-conception.md) | Roadmap et conception des EPIC livrés |
| [`contrat-a`](2026-11-14-revue-complete/contrat-a.md) | Contrat, socle commun, administration et référentiel |
| [`contrat-b`](2026-11-14-revue-complete/contrat-b.md) | Contrat, familles de projet |
| [`contrat-conformite`](2026-11-14-revue-complete/contrat-conformite.md) | Conformité au contrat : routes, modèles, client, faux back |
| [`back-socle`](2026-11-14-revue-complete/back-socle.md) | Back, socle : plateforme, coquille de l'API, worker, restauration |
| [`back-comptes`](2026-11-14-revue-complete/back-comptes.md) | Back, comptes, habilitations, audit ; tableau des 132 routes |
| [`back-projets`](2026-11-14-revue-complete/back-projets.md) | Back, projets, révisions et cycle de vie |
| [`back-planning`](2026-11-14-revue-complete/back-planning.md) | Back, planification ; reproduction des constats du moteur |
| [`back-chiffrage`](2026-11-14-revue-complete/back-chiffrage.md) | Back, chiffrage, devis et reste à engager |
| [`back-referentiel-couts`](2026-11-14-revue-complete/back-referentiel-couts.md) | Back, référentiel et coûts réels |
| [`back-echanges`](2026-11-14-revue-complete/back-echanges.md) | Back, échanges de fichiers et MS Project |
| [`donnees`](2026-11-14-revue-complete/donnees.md) | Modèles de données ; schéma final reconstitué |
| [`front-socle`](2026-11-14-revue-complete/front-socle.md) | Front, socle : client, session, navigation, coquille, i18n |
| [`front-grille`](2026-11-14-revue-complete/front-grille.md) | Front, grille |
| [`front-planning`](2026-11-14-revue-complete/front-planning.md) | Front, écrans de projet et de planning |
| [`front-admin-referentiel`](2026-11-14-revue-complete/front-admin-referentiel.md) | Front, administration, audit, système, référentiel |
| [`front-couts`](2026-11-14-revue-complete/front-couts.md) | Front, chiffrage, coûts, échanges, indicateurs, risques, portefeuille |
| [`front-tests`](2026-11-14-revue-complete/front-tests.md) | Front, tests, parcours, catalogues, aide, accessibilité |
| [`plateforme-deploiement`](2026-11-14-revue-complete/plateforme-deploiement.md) | Plateforme, déploiement, images, Keycloak |
| [`chaine-outillage`](2026-11-14-revue-complete/chaine-outillage.md) | Chaîne, Makefile, dépendances, outillage des agents |
