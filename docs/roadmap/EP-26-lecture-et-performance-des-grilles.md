---
id: EP-26
titre: Ouvrir, filtrer et saisir dans une grille de mille tâches sans attendre
statut: en cours
depend_de: EP-25
famille: back, front
issue: 3299
---

# EP-26 — Lecture et performance des grilles

## Objet

Sur un projet aux volumes du §4.6.2 — mille tâches, cinq mille lignes —, ouvrir une révision prend
dix secondes, un filtre relit et recalcule la structure entière, et la file de fusion perd des
parcours dès que plusieurs lisent PRJ-001 ensemble sur l'API à un seul processus. L'analyse du
2026-11-14 (#3168 à #3174) en a relevé sept causes, chacune avec ce qu'il faut mesurer pour
trancher.

L'EPIC mesure d'abord, puis corrige ce qui pèse, et dit ce qui est réellement atteignable : c'est
lui qui fixe les bornes de temps des parcours lourds et qui clôt WF-QUA-0060. Il précède la
comparaison dans les grilles (EP-27), qui lit deux structures à la fois.

## Ce qui en fait partie

- la mesure du parcours — ouvrir une grille, filtrer, saisir, passer d'une grille à l'autre —,
dans le processus et contre le service, à plusieurs utilisateurs (#3173) : US-2210 ;
- le chemin de lecture d'une structure (#3174) : US-2220 ; ce qui se recalcule à chaque lecture
(#3170) : US-2280 ;
- l'API à plusieurs processus (#3172) : US-2230 ;
- l'ouverture d'une révision d'un projet chargé, et ce que le front dit pendant qu'elle dure
(#3102) : US-2240 ;
- la saisie qui ne déplace rien (#3169) : US-2250 ;
- les constats reçus du back des grilles (#2502, #2605, #2606, #2892, #3093, #3094) : US-2260 ;
- la lecture gardée d'une révision marquée (#3168, option 1) : US-2270 ;
- les bornes de temps des parcours lourds, et le parcours du reste à engager filtré par un poste,
en quarantaine contre le service, rejoué (#3087) : US-2290 ;
- le rapport de mesures d'une version, sur les objectifs du tableau 15 tels que la spécification
1.0.6 les allège (#3184), à cinquante utilisateurs : US-2300.

## Ce qui n'en fait pas partie

- une correction propre à un filtre, à un tri ou à une recherche (#3171) : ils profitent du chemin
de lecture (US-2220) et des valeurs stockées (US-2280), et se mesurent contre les deux secondes du
tableau 15 (US-2210, US-2300). Un dépassement qui resterait est documenté dans le rapport et
devient une issue à trancher, sans lot engagé d'avance (décision de l'auteur du 2026-11-14, au
cadrage). Écartés : filtrer dans le navigateur, contre la règle d'US-0110 (EP-02) — « rien n'est
ordonné ni sommé dans le front » — ; garder la lecture d'une révision en cours par version de
structure, un cache que WF-ARC-0040 ne prévoit pas ;
- l'ouverture d'une révision en tâche de fond : `createRevision` reste synchrone et répond 201
(décision de l'auteur du 2026-11-14, au cadrage) ;
- la différence tenue à l'écriture pour une révision en cours comparée (#3168, option 3) — instruite
ici, réalisée par EP-27 si la mesure la justifie ; le résultat d'une comparaison gardé par couple
de révisions (#3168, option 2), que la révision en cours comparée périme à chaque écriture ;
- la mesure d'une grille comparée, et de la saisie dans une grille comparée — EP-27, à leur
livraison, par l'outil écrit ici ; de même les indicateurs et la projection de dépenses (EP-10) et
les vues de portefeuille (EP-11) ;
- le jeu de données aux trois cents projets (WF-QUA-0040) — EP-13, qui rejoue la mesure dessus ;
- plusieurs instances de l'API sous Kubernetes, et le worker — EP-13.

## Exigences réalisées

WF-QUA-0060 passe d'EP-13 à cet EPIC, qui la clôt (décision de l'auteur du 2026-11-14). Les lignes
du tableau 15 qui portent sur des fonctions non encore livrées — les indicateurs, le portefeuille,
la comparaison, la projection de dépenses — se mesurent à leur livraison, par le même outil :
US-2300 le dit en écart.

Comme EP-23, EP-24 et EP-25, une US cite, avec tout son Vérif, l'exigence dont une phrase tient à
ce qu'elle change ; les phrases qu'elle ne touche pas sont des écarts qui disent qui les constate.
Leur portée reste celle des EPIC qui les ouvrent et les closent : `WF-ARC-0080-A` (EP-13),
`WF-REV-0010-A` (close par EP-07).

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-QUA-0060-A` | Tests de charge et non-régression des temps de réponse | entière | US-2300 |

## Opérations du contrat

Déjà servies, et reprises pour ce que l'EPIC change à leur durée, non à leur réponse : `listNodes`,
`compareRevisions` (US-2220, US-2270, US-2280) ; `updateTaskFacet`, `updateEstimateLine`,
`setLineRemaining`, `setTaskProgress`, `setNodeTracking`, `setPredecessors`, `createNode`,
`moveNodes`, `deleteNode`, `previewPaste`, `applyPaste`, `undoLastChange`, `redoLastUndo` (US-2250,
US-2260, US-2280) ; `createRevision`, `listRevisions` (US-2240) ; `markRevision` (US-2270) ;
`getProjectWorkload`, `openImport`, `applyImport`, `requestExport`, `getBackgroundTask` (US-2300) ;
`getMe` (US-2210, US-2230).

Aucune opération nouvelle, aucune réponse changée. Une seule modification du contrat, qui n'est
pas une forme : la règle générale des refus de débordement d'un montant dérivé, écrite dans
`docs/api/DECISIONS.md` (#3093, décision de l'auteur du 2026-11-14 ; US-2260).

## Préalables

Par exception (décision de l'auteur du 2026-11-14, au cadrage ; README, « Branches »),
`epic/EP-26` se tire d'`epic/EP-25` dès l'ouverture de ses issues, et la reprend à chaque lot
qu'EP-25 fusionne : ses lots de back et ses outils de mesure ne touchent aucun fichier de la
refonte, et avancent sur les créneaux libres. `epic/EP-26` se fusionne dans `main` après
`epic/EP-25`, jamais avant.

La mesure de référence précède tout lot de correction : sans elle, aucun lot ne sait ce qu'il
gagne. Elle se prend sur les écrans tels qu'`epic/EP-26` les porte à ce moment ; le rapport de la
version (US-2300), lui, attend les écrans de travail refondus (US-2140 d'EP-25).

## Définition de fini

L'EPIC est fini quand ses corrections sont livrées et leurs gains mesurés, non quand chaque
objectif du tableau 15 est tenu : le §4.6.2 dit que ces objectifs « ne sont pas des exigences », et
WF-QUA-0060 qu'un objectif dépassé est signalé et documenté (décision de l'auteur du 2026-11-14, au
cadrage).

- les durées de chaque opération du tableau 15 servie sont publiées, sur le jeu de référence, avec
leur dispersion (WF-QUA-0060), et chaque objectif encore dépassé est documenté dans le rapport ;
- chaque correction dit son gain par la mesure de référence, avant et après, au-delà de la
dispersion ;
- les bornes de temps des parcours lourds sont celles que la mesure justifie, et le parcours
`structure.spec.ts` en quarantaine est rejoué contre le service (#3087) ;
- la file de fusion échoue moins d'une fois sur dix sur cinquante passages ;
- `make check-all` passe.

La condition qu'EP-25 avait laissée ici — rejouer les deux parcours `reference-costs.spec.ts` si
leur cause était la charge de la file — est tombée : US-2060 a établi que la charge n'y est pour
rien, et les a rejoués (#3190, #3191).

## Constats reçus

Ventilation du reste à faire du 2026-11-14 (décision de l'auteur, à la livraison d'EP-24) : les
constats ouverts sont rattachés à l'EPIC qui touche leur code, et non plus au prochain EPIC ouvert.
Le cadrage les rattache à l'ouverture des issues de l'EPIC. #2212 et #2464, reçus à la ventilation,
ont été clos le même jour à la vérification des vieux constats, et ne sont plus à rattacher.

- #2502 — back : le rang des tâches placées parmi des lignes de devis, posé par US-1380/L3 ;
- #2605 — back : le collage qui crée relit calendrier et constantes à chaque ligne, sous le verrou ;
- #2606 — back : le refus d'horizon d'un collage nomme la première ligne, pas celle qui dépasse ;
- #2892 — back : la somme d'une révision indépendante de l'ordre est éprouvée sur sum_amounts, que
le service n'appelle pas ;
- #3087 — e2e : le parcours du reste à engager filtré par un poste (structure.spec.ts:335) échoue
par moments dans la file — en quarantaine contre le service ;
- #3093 — contrat : les refus de débordement d'un montant dérivé (#2996, #3035, #3039) ne sont pas
décrits par le contrat ;
- #3094 — back : la redatation d'une tâche et la copie d'une révision qui débordent un montant
répondent 422 sans champ ;
- #3102 — front, back : ouvrir une révision d'un projet de mille tâches prend dix secondes, et le
front dit « service injoignable » au bout de cinq alors qu'elle se crée (WF-REV-0010) ;
- #3138 — back : totals_of écrit deux fois sa garde « liste vide » ;
- #3168 — back, front : la comparaison de deux révisions marquées et la lecture de leurs grilles se
recalculent en entier à chaque affichage ;
- #3169 — back : une saisie qui ne peut déplacer aucune date rejoue le moteur sur la structure
entière ;
- #3170 — back : les états des récapitulatives et les montants des tâches se recalculent à chaque
lecture, et le planning lit les lignes de devis qu'il n'affiche pas ;
- #3171 — front, back : un filtre, un tri ou une recherche relit et recalcule la structure entière ;
- #3172 — back : l'API n'a qu'un processus, et le parcours de comparaison joué par plusieurs
utilisateurs s'y attend ;
- #3173 — outil : la mesure de la seconde ne couvre ni la comparaison ni le parcours comparaison →
grilles → comparaison ;
- #3174 — back : la lecture d'une structure charge chaque nœud en objet ORM, puis en vue, puis en
corps ;
- #3184 — spec : les objectifs de temps de réponse ne nomment ni la comparaison, ni un filtre, ni
les vues nouvelles (§4.6.2, WF-QUA-0060) — close, portée par la spécification 1.0.6.

## Conception

### La mesure

Quatre commandes du Makefile, que les lots ajoutent ; les trois premières prennent le poste pour
elles seules.

| Commande | Ce qu'elle fait | Où vit son code |
|---|---|---|
| `make measure-core` | mesure dans le processus, sans HTTP ni Keycloak : lecture entière, `kinds=task`, profil par étape, fils et processus, rapport d'une saisie à une lecture, ouverture d'une révision | `backend/measure/`, un paquet à part de `src/waterfall`, typé et analysé comme lui, absent de l'image |
| `make measure` | joue le parcours des grilles contre le service, à un, quatre et huit utilisateurs, en trois parts par étape | `frontend/e2e/measure/`, un projet Playwright `measure-service` |
| `make measure-version` | prend le rapport d'une version : le parcours par un navigateur sous la charge de cinquante utilisateurs, puis un marquage, un import et un export | la charge dans `frontend/bench/load.ts`, jouée par k6 |
| `make check-measures` | confronte les rapports versionnés ; la seule que la chaîne joue | `tools/src/wftools/measures.py` |

- **Le poste pour elle seule.** L'outil des créneaux (`tools/src/wftools/slots.py`) reçoit un mode
  exclusif, à côté de `--heavy` : il prend tous les tours des exécutions lourdes, dans un ordre
  fixe, attend ceux qui sont pris et les garde le temps de la commande. Les travaux légers des
  autres livreurs continuent : la dispersion des cinq passages dit ce qu'ils coûtent.
- **Le témoin fraîchement chargé.** Une mesure part d'une plateforme de service dont les données
  viennent d'être remises à zéro et le témoin rechargé : le marquage et la saisie d'une mesure ne
  changent pas la suivante.
- **L'API sans le proxy du contrat.** Le front de la mesure parle à l'API directement : Prism
  valide chaque réponse, et sur un corps de plusieurs mégaoctets ce coût est celui du harnais.
- **La part de l'API.** Elle se lit dans le journal de l'API (`duration_ms`, l'acteur), rapprochée
  d'une étape par le compte de l'utilisateur et la fenêtre de l'étape : le front ne transmet pas
  d'identifiant de corrélation, et chaque utilisateur de la mesure a son compte.
- **Les comptes.** Ils sont créés par la préparation de la mesure, par les opérations du contrat,
  jamais par un `INSERT` ; leurs jetons sont pris au fournisseur d'identité hors de la mesure.
- **La charge.** k6, que l'annexe C nomme, tourne en service Compose de la plateforme de service,
  son image épinglée. Son scénario est un fichier TypeScript de `frontend/bench/`, typé et analysé
  avec le front : cinquante utilisateurs virtuels, un geste toutes les dix secondes en moyenne
  (entre cinq et quinze, tirage reproductible), neuf lectures pour une saisie, tous sur PRJ-001.
- **Les rapports.** Des fichiers JSON sous `docs/measures/` : `reference.json`, pris avant toute
  correction, puis `<version>.json` à chaque version. Chaque opération y porte son objectif, sa
  médiane, sa pire durée, sa dispersion, et, si elle dépasse ou se dégrade, le texte qui le
  documente. Une opération non servie y est nommée, sans durée, avec son EPIC.
- **La confrontation.** `wftools.measures` lit les deux derniers rapports de version : il signale
  par un avertissement de la chaîne un objectif dépassé ou une durée de plus d'un quart au-dessus
  de la précédente, et échoue si ce signalement n'est pas documenté dans le rapport. Son test lui
  donne un rapport dont une durée est multipliée par 1,3. `make check-measures` entre dans
  `make check-all`.
- **Le gain d'un lot.** Un lot de correction du back mesure avant et après lui par
  `make measure-core`, dans le même passage exclusif, et l'écrit dans sa pull request. Le parcours
  entier ne se rejoue qu'à quatre moments : la référence, le réglage des processus (US-2230), les
  bornes des parcours (US-2290), le rapport de la version (US-2300).

### La lecture d'une structure

Trois US touchent le même chemin, et se suivent : US-2220 l'allège, US-2280 lui fait lire moins,
US-2270 le garde pour une révision marquée.

- **Deux chemins, un oracle** (US-2220). La lecture seule lit les colonnes en lignes ; les
  écritures gardent les objets, qu'elles modifient. Un test tient sur le témoin que les deux
  rendent le même arbre, et il reste dans la suite.
- **La forme du contrat reste dans `api/`.** Le dernier palier écrit le corps sans vue par nœud :
  le noyau rend alors des enregistrements à plat, et c'est `api/nodes.py` qui en fait le corps. Le
  noyau ne connaît pas la forme d'une réponse.
- **Les cibles.** L'API reçoit, pour l'ouverture d'une grille, la seconde du tableau 15 moins les
  parts de Next et du navigateur que donne `reference.json`, pour un utilisateur seul. US-2220
  s'arrête au palier qui l'atteint pour la grille de devis ; US-2280 rend son verdict sur la grille
  de planning.
- **L'agrégat d'abord** (US-2280). Un crochet de plus dans `FacetHooks` rend, par tâche porteuse,
  les sommes, le nombre et la tenue ouverte de ses nœuds d'un genre, lus par une requête groupée.
  Le planning lit ses tâches, ce crochet, et rien des lignes. Si le verdict manque la cible, le
  livreur ouvre le second lot : des colonnes sur la tâche, pour les seules valeurs que l'agrégat
  lit trop lentement, nulles pour une révision marquée avant lui. Le numéro de ligne et le niveau
  ne se stockent pas : une insertion renuméroterait toutes les lignes qui suivent.
- **Ce qui est gardé** (US-2270). Le corps entier de `listNodes` d'une structure, sans filtre ni
  projection, avec ses totaux et ce que la lecture dit de la structure, compressé. La projection
  `fields` s'y applique à la lecture.
- **Ce qui change encore après le marquage.** Le test de l'US en donne la liste. Ce qu'un geste
  courant change — une inscription de suivi — n'entre pas dans le document, et se joint à chaque
  lecture ; ce qu'un réglage change — le libellé d'un lot, un calendrier — périme les lectures
  gardées du projet, refaites à la demande.
- **Quand.** Au marquage, dans la transaction de sa tâche, par `register_marking`, pour la
  structure principale : comme les indicateurs d'une révision marquée, calculés une fois et
  conservés avec elle (§4.4.2). Les autres structures, et les révisions marquées avant le lot, à
  leur première lecture entière, écrite dans la transaction de la lecture ; deux processus qui la
  calculent ensemble écrivent la même, la seconde écriture ignorée.
- **Le format.** Une lecture gardée porte le format du code qui l'a écrite ; d'un autre format,
  elle est ignorée et refaite. Un champ ajouté au nœud change le format.
- **La comparaison.** `compareRevisions` de deux révisions marquées part des deux lectures gardées.
  Comment l'union les lit est au lot ; son critère est le corps identique à l'octet.

### Les écritures

- **Les colonnes inertes** (US-2250). Chaque facette déclare les siennes : la tâche dans
  `planning`, la ligne de devis par un attribut de plus de `FacetHooks`. Une écriture dont toutes
  les colonnes envoyées sont inertes prend le chemin court.
- **Le chemin court avance le compteur, non l'instant des dates.** Il verrouille la structure,
  écrit, inscrit l'historique et avance le compteur de la structure, auquel le front s'adosse.
  `scheduled_at` ne bouge plus pour ces saisies : le contrat le dit déjà « l'instant de la dernière
  écriture qui l'a redatée ». C'est le seul écart visible à la réponse d'aujourd'hui.
- **La copie d'une révision** (US-2240). Le profil d'abord : le lot dit où vont les dix secondes
  avant de réécrire. La copie reste dans une transaction, sous le verrou du projet, et le nombre de
  lignes par table reste celui de WF-DAT-0010.
- **La connexion perdue** (US-2240). `frontend/src/api/client.ts` distingue une requête qui n'est
  pas partie d'une connexion perdue après son envoi. Pour une écriture, la seconde a son message
  propre, dans les deux langues, et fait relire l'écran. La règle vaut pour toute écriture, non
  pour la seule ouverture d'une révision.

### Plusieurs processus

- **`workers` d'uvicorn.** `WATERFALL_API_PROCESSES` : la plateforme de service tourne désormais sur quatre
  processus, le back de développement et ses tests restent à un. L'application se construit par une fabrique, une fois par
  processus, qui ouvre et ferme ses propres services — la base, Keycloak, Redis.
- **Le nombre.** La mesure à un, deux et quatre processus fixe celui de la plateforme de service
  et celui que `production.env.example` conseille : autant que de cœurs, tant que la mémoire et
  les connexions tiennent.
- **Les connexions.** Chaque processus garde sa réserve de quinze ; `max_connections` de
  PostgreSQL est réglé pour les porter toutes, et le guide du déploiement dit le calcul.
- **L'état.** Le fuseau de l'installation, lu une fois par processus, est fixé à l'amorçage et ne
  change plus (US-2200 d'EP-25) : il est le même partout. Le lot inventorie le reste.

### Tables et migrations

| Table | US | Ce qu'elle porte |
|---|---|---|
| `structure_reading` | US-2270 | par structure : le projet, la révision, la structure, le format, le document compressé, l'instant où il a été gardé. Partitionnée par projet comme les tables du contenu d'une révision ; supprimée avec sa structure ; aucune règle d'immuabilité, puisqu'elle se refait |
| colonnes de `task` | US-2280, second lot, s'il a lieu | les sommes et l'état dérivé que l'agrégat lit trop lentement, nulles tant qu'aucune écriture ne les a posées |

Les migrations se chaînent après la dernière d'`epic/EP-25`. EP-25 entre le premier dans `main` :
si l'un de ses lots ajoute une migration après celle d'EP-26, c'est celle d'EP-26 qui se rechaîne,
à la reprise d'`epic/EP-25`.

### Modules touchés

| Module | US | Ce qui change, et ce qu'il expose |
|---|---|---|
| `core/planning` | US-2220, US-2250, US-2270, US-2280 | le chemin de lecture seule derrière `list_nodes` et `read_structure`, dont la signature ne change pas ; `FacetHooks` gagne la lecture en colonnes d'une facette, ses colonnes inertes et l'agrégat par tâche ; la table des lectures gardées |
| `core/estimate` | US-2220, US-2240, US-2260, US-2270, US-2280 | ses crochets nouveaux ; `compare` sur les lectures gardées ; la copie des lignes et des taux |
| `core/revisions` | US-2240, US-2250 | `copy_revision` ; une avance du compteur d'une structure sans son instant |
| `api` | US-2220, US-2230 | le corps écrit depuis des enregistrements à plat ; la fabrique de l'application |
| `platform/settings.py` | US-2230 | `WATERFALL_API_PROCESSES` |
| `frontend/src/api`, les catalogues | US-2240 | la connexion perdue d'une écriture |
| `frontend/e2e`, `frontend/bench` | US-2210, US-2290, US-2300 | le parcours de mesure, les bornes des parcours lourds, la charge |
| `tools/src/wftools` | US-2210, US-2300 | le mode exclusif des créneaux ; la confrontation des rapports |
| `deploy/compose` | US-2230, US-2300 | les processus de l'API, `max_connections`, le service de charge |

### Modifications du contrat

Aucune forme ne change. `docs/api/DECISIONS.md` reçoit une entrée : un montant dérivé qui déborde
sa colonne est refusé au champ qui le provoque (#3093), que les pointeurs de #3094 suivent.

### Ordre de construction

En six temps. Quatre livreurs avancent ensemble aux deux premiers ; ensuite, le back des grilles
est un couloir où les lots se suivent, à côté duquel avancent les processus, la charge et le front.

1. **Les outils, et ce qui ne mesure rien**, en parallèle : la mesure dans le processus, le mode
   exclusif, le parcours de mesure (US-2210) ; le format des rapports et leur confrontation
   (US-2300) ; la fabrique et le réglage des processus, à un processus par défaut (US-2230) ; les
   constats reçus (US-2260) ; la connexion perdue du front (US-2240).
2. **La mesure de référence** : `reference.json`, pris par le dernier lot d'US-2210 ; à côté, la
   charge des cinquante utilisateurs (US-2300).
3. **Les corrections du back, une à la fois** : le chemin de lecture (US-2220), la copie d'une
   révision (US-2240) et la saisie (US-2250) touchent toutes `core/planning/interface/nodes.py` —
   `list_nodes`, `copy_nodes`, `update_task_facet` —, et les deux premières les crochets de
   `FacetHooks` : aucune ne se livre en même temps qu'une autre. Le nombre de processus (US-2230)
   avance à côté.
4. **Ce qui s'appuie sur la lecture nouvelle**, dans le même couloir : l'agrégat (US-2280), puis
   la lecture gardée (US-2270).
5. **Les parcours lourds** (US-2290), corrections livrées et processus réglés.
6. **Le rapport de la version** (US-2300), en dernier, sur les écrans de travail refondus.

Deux lots ne s'ouvrent que si la mesure les demande, par le livreur du lot qui rend le verdict
(`make tracking ADD_LOT=…`) : le dernier palier du chemin de lecture, si les deux premiers manquent
la cible (US-2220) ; le stockage à l'écriture, si l'agrégat la manque (US-2280).

Le Makefile et le guide reçoivent une cible et son paragraphe de plusieurs lots : chacun n'y
écrit que les siens, et ils ne mettent pas deux lots « pas avec », comme les catalogues dans EP-25.

### Décisions

Prises par l'auteur le 2026-11-14, au cadrage, sauf mention.

- **L'EPIC finit sur ses corrections, non sur les objectifs.** Écarté : tenir chaque objectif
  d'écran avant de livrer, pour un utilisateur ou pour cinquante — un EPIC sans fin connue, quand
  WF-QUA-0060 demande de signaler et de documenter.
- **Les durées se prennent sur un poste, la chaîne confronte les rapports.** Écartés : mesurer sur
  un runner, dont les durées varient du simple au double, au-delà du quart à détecter ; les deux,
  un travail de chaîne de plus.
- **Le poste pour la mesure seule, par l'outil des créneaux.** Écartés : une mesure lancée par
  l'auteur, poste au calme, qui ferait attendre la livraison deux fois ; une mesure prise telle
  quelle sous quatre livreurs, dont les durées absolues ne vaudraient rien.
- **La référence se prend sur les écrans du moment.** Les préalables la voulaient sur les écrans
  refondus ; elle aurait attendu US-2140 d'EP-25, que la validation de l'écran de référence
  (#3196) retient, et quatre livreurs avec elle. Seul le rapport de la version les attend.
- **Cinquante utilisateurs actifs, non cinquante requêtes en vol.** Écartés : cinquante lectures
  simultanées sans pause, au-delà du §4.6.2 ; une répartition sur les petits projets du témoin, que
  le jeu aux trois cents projets (EP-13) changera.
- **L'ouverture d'une révision reste synchrone, bornée à deux secondes.** Écartée : la tâche de
  fond, qui modifiait `createRevision` dans un contrat figé et reprenait le front et les parcours
  qu'US-2170 d'EP-25 touche.
- **Aucune correction propre à un filtre** (#3171). Écartés : filtrer dans le navigateur, contre
  la règle d'US-0110 ; garder la lecture d'une révision en cours par version de structure, que
  chaque écriture périme.
- **L'agrégat avant le stockage, la mesure tranche.** Écartés : l'agrégat seul, sans recours ; le
  stockage d'emblée, que #3170 proposait — une migration, un invariant sur dix chemins d'écriture
  et un cas à part pour les révisions marquées, avant de savoir s'il le faut.
- **Le document gardé est le corps, non ses lignes d'origine** (cadrage). Écarté : garder les
  enregistrements lus de la base, qui n'épargnent que le chargement, un tiers d'une lecture, quand
  le corps gardé en épargne les neuf dixièmes pour la lecture entière.
- **Une lecture filtrée d'une révision marquée ne lit le document que si la mesure le justifie**
  (cadrage, règle de #3168). Écarté : y filtrer d'office, qui demande un second filtrage à tenir
  d'accord avec le premier.
- **La lecture gardée vit dans PostgreSQL.** Écartés : Redis, que WF-ARC-0040 réserve au
  reconstructible qu'il nomme, et qui la perdrait à chaque vidage ; le stockage objet, qui ne porte
  que les fichiers en transit, les exports et les sauvegardes.
- **`workers` d'uvicorn pour Compose** (cadrage). Écartés : plusieurs instances derrière un
  répartiteur, qui sont l'affaire de l'empaquetage Kubernetes d'EP-13 ; gunicorn, une dépendance
  de plus.
- **k6 en service Compose, son scénario en TypeScript dans le front** (cadrage). Écartés : un
  générateur de charge en Python, contre l'annexe C ; un script JavaScript hors de toute analyse.
- **Les exigences d'un autre EPIC citées sans changer leur portée** (cadrage, comme EP-25) :
  WF-ARC-0080 reste entière à EP-13, WF-REV-0010 close par EP-07.

---

## US-2210 — La mesure de référence des grilles : dans le processus, puis du clic à l'affichage contre le service, à un, quatre et huit utilisateurs

- **statut** : fini
- **exigences** : aucune en propre — l'outil de WF-QUA-0060, que clôt US-2300
- **opérations** : `listNodes`, `updateTaskFacet`, `updateEstimateLine`, `createRevision`, `getMe`
- **issue** : #3304

**En tant que** développeur, **je veux** une mesure commune du parcours des grilles, rejouable sur
un poste, **afin de** savoir ce que chaque correction gagne et à quelle part — l'API, Next ou le
navigateur — elle doit s'attaquer.

**Critères d'acceptation.**

- propre à l'US : une commande du dépôt mesure dans le processus, sans HTTP ni Keycloak, sur le
  témoin chargé : une lecture entière de PRJ-001, seule puis avec `kinds=task` ; la même sous
  profil, par étape ; la même par plusieurs fils et par plusieurs processus ; le rapport d'une
  saisie — un libellé, une durée qui redate — à une lecture ; l'ouverture d'une révision. Ce sont
  les scripts d'essai joints à #3173, réécrits en outil du dépôt ;
- propre à l'US : une commande du dépôt mesure le parcours contre le service, sur le front
  construit pour la production et sans le proxy du contrat dans le chemin : ouvrir la grille de
  planning, celle de devis, celle de reste à engager ; passer de l'une à l'autre ; filtrer, trier,
  chercher ; saisir un libellé, puis une durée qui redate ;
- propre à l'US : chaque étape se mesure du clic à la grille dessinée et hydratée — la définition
  d'`opening.spec.ts` —, en trois parts : l'API, lue dans ses journaux et rapprochée de l'étape
  par le compte de l'utilisateur et son instant ; Next, par différence ; le navigateur ; et le
  poids de la réponse ;
- propre à l'US : le parcours est joué par un, quatre et huit utilisateurs à la fois, un compte
  chacun, la connexion hors de la mesure ; la durée de `getMe` pendant ce temps est relevée ;
- propre à l'US : cinq passages identiques donnent la dispersion ; le rapport écrit, par étape, la
  médiane, la pire et la dispersion, et un écart sous la dispersion n'y est pas dit un gain ;
- propre à l'US : une mesure prend le poste pour elle seule : elle attend la fin des exécutions
  lourdes en cours et retient les suivantes tant qu'elle dure, quel que soit le nombre de
  livreurs ;
- propre à l'US : la mesure n'échoue jamais sur une durée, et ne tourne pas dans la chaîne ;
- propre à l'US : le rapport de référence est versionné avant tout lot de correction ;
- propre à l'US : `opening.spec.ts`, contre le faux back, reste ce qu'elle est, et dit à part la
  durée que le faux back met à servir l'exemple des lignes du témoin.

**Notes de réalisation.** Les durées à retenir sont celles d'un poste de développement, plateforme
de service lancée et témoin chargé (`make service-up`, `make service-witness`) ; celles de la
session cloud du 2026-11-14 ne sont que des rapports (#3173, « Contexte »). Le parcours visé par
#3173 — comparaison, grille de départ, grille d'arrivée, comparaison — n'existe plus depuis les
décisions du 2026-11-14 (#3176 à #3179) : ses étapes de comparaison se mesurent en EP-27, par cet
outil.

**Hors périmètre.** Les cinquante utilisateurs et le rapport d'une version (US-2300) ; la
comparaison (EP-27).

## US-2220 — Une structure se lit en colonnes, sans objet ORM ni vue intermédiaire par nœud

- **statut** : en cours
- **exigences** : aucune en propre — le gain se lit dans le rapport de WF-QUA-0060 (US-2300)
- **opérations** : `listNodes`, `compareRevisions`
- **issue** : #3315

**En tant que** chef de projet, **je veux** que la grille d'une révision en cours s'ouvre sans que
le service traite ses six mille nœuds un à un à chaque étape, **afin de** ne pas attendre une
lecture que rien ne permet de garder.

**Critères d'acceptation.**

- propre à l'US : les réponses ne changent pas : le SHA-256 des corps de `listNodes` de PRJ-001 —
  entier, avec `kinds=task`, avec `fields`, filtré — et de `compareRevisions` est le même avant et
  après ; un octet d'écart bloque le lot ;
- propre à l'US : le chemin de lecture seule se construit par paliers, le profil refait à chacun :
  l'arbre lu en colonnes ; puis les lignes de devis ; puis le corps écrit sans vue par nœud. Le lot
  s'arrête au palier qui laisse à l'API ce que la mesure de référence lui donne de la seconde,
  une fois retirées les parts de Next et du navigateur ; il va au dernier sinon ;
- propre à l'US : si les écritures gardent le chemin des objets, un test tient que les deux chemins
  rendent le même arbre sur le témoin ;
- propre à l'US : les requêtes d'une lecture sont examinées une à une ; une requête qui pèse à elle
  seule reçoit son index ou sa réécriture avant le reste ;
- propre à l'US : le gain est dit par la mesure d'US-2210, avant et après, au-delà de la
  dispersion ;
- propre à l'US : la garde « liste vide » écrite deux fois dans `totals_of` est retirée (#3138).

**Notes de réalisation.** Suite de #3140, qui a laissé `read_tree` et `rows_of` en ORM parce qu'ils
servent aussi les écritures. Aucune étape ne domine le profil (#3174) : le coût est celui d'un
travail par nœud, répété six mille fois.

**Hors périmètre.** Lire moins que la structure entière (US-2280) ; garder la lecture d'une
révision marquée (US-2270).

## US-2230 — L'API tourne sur plusieurs processus

- **statut** : fini
- **exigences** : `WF-ARC-0080-A`
- **opérations** : toutes celles que le service sert ; `getMe` pour la mesure
- **issue** : #3309

**En tant qu'** exploitant, **je veux** que l'API serve ses requêtes sur plusieurs processus,
**afin que** plusieurs utilisateurs qui lisent le même projet ne se partagent plus un seul cœur.

**Critères d'acceptation.**

- `WF-ARC-0080-A` — « Deux requêtes successives d’un même utilisateur, servies par deux instances
  différentes, donnent le même résultat sans qu’il ait à se reconnecter. » : éprouvé sur deux
  processus de l'API ;
- écart : `WF-ARC-0080-A` — « L’arrêt brutal d’une instance du worker pendant une tâche laisse la
  base inchangée, et la tâche est reprise par une autre instance. » : le worker n'est pas touché ;
  constaté par EP-13, qui clôt l'exigence ;
- écart : `WF-ARC-0080-A` — « Aucun service ne lit un fichier que lui-même a écrit sur son disque
  local lors d’une requête antérieure. » : constaté par EP-13 ;
- propre à l'US : un réglage de l'API dit le nombre de ses processus ; la plateforme de service et
  celle de production en lancent plusieurs ;
- propre à l'US : ce qu'un processus garde en mémoire entre deux requêtes est inventorié — les clés
  de Keycloak, l'état de maintenance, le fuseau de l'installation (US-2200 d'EP-25), tout cache de
  module — ; chaque état trouvé est rangé dans PostgreSQL ou dans Redis, ou établi identique d'un
  processus à l'autre ;
- propre à l'US : les connexions à PostgreSQL de tous les processus tiennent sous
  `max_connections` ;
- propre à l'US : `make e2e-service` passe avec deux processus ou plus ;
- propre à l'US : la mesure d'US-2210 est rejouée par un, quatre et huit utilisateurs, avec un,
  deux et quatre processus ; elle dit la durée de chaque étape et celle de `getMe` pendant ce
  temps.

**Notes de réalisation.** Rouvre l'option 1 de #3048, écartée le 2026-11-13 parce qu'elle touche le
déploiement. Les routes sont synchrones et une lecture est à 95 % du CPU Python (#3140) : six
lectures simultanées durent chacune six fois une lecture seule.

**Hors périmètre.** Plusieurs instances sous Kubernetes, et le worker — EP-13.

## US-2240 — Ouvrir une révision d'un projet de mille tâches en deux secondes, sans que le front la dise injoignable

- **statut** : à faire
- **exigences** : `WF-REV-0010-A`
- **opérations** : `createRevision`, `listRevisions`
- **issue** : #3312

**En tant que** chef de projet, **je veux** que la révision en cours d'un projet chargé s'ouvre
sans attente, et que l'écran ne me dise pas de réessayer une ouverture qui a abouti, **afin de** ne
pas croire à un échec à chaque revue.

**Critères d'acceptation.**

- `WF-REV-0010-A` — « Une révision créée à partir d’une révision marquée porte les mêmes tâches et
  les mêmes lignes, hors celles des structures qu’elle ne reprend pas (WF-REV-0100) ; à année de
  référence égale, elle porte aussi les mêmes valeurs de référentiel ; sinon, elle porte les mêmes
  rôles, calendriers et catégories, et, pour chaque catégorie dont la mise à jour de WF-REV-0060
  n’a pas été acceptée, le taux précédent projeté par le taux d’inflation du projet jusqu’à la
  nouvelle année de référence. » : la copie accélérée le tient, éprouvé sur PRJ-001 ;
- écart : `WF-REV-0010-A` — « La création d’une seconde révision en cours est refusée tant que la
  première n’est pas marquée. » : non touché ; constaté par EP-07, qui clôt l'exigence ;
- écart : `WF-REV-0010-A` — « Après abandon d’une révision en cours, le projet présente les données
  de la dernière révision marquée, et une nouvelle révision peut être créée. » : non touché ;
  constaté par EP-07 ;
- écart : `WF-REV-0010-A` — « L’abandon de l’unique révision d’un projet en chiffrage le laisse
  sans révision, à l’état Chiffrage, et la création d’une révision y est de nouveau proposée. » :
  non touché ; constaté par EP-07 ;
- propre à l'US : `createRevision` sur PRJ-001 répond en deux secondes au plus à l'API, pour un
  utilisateur seul, sur un poste (borne de l'auteur du 2026-11-14 : celle des opérations d'écran
  nouvelles du tableau 15, qui ne nomme pas l'ouverture d'une révision) ; mesurée par US-2210,
  avant et après ;
- propre à l'US : la cause de la rupture de l'appel du front au bout de cinq secondes est établie —
  uvicorn, le frontal, undici —, puis corrigée ou écrite ;
- propre à l'US : une connexion perdue une fois une écriture partie ne s'affiche plus « Le service
  est injoignable ; réessayez dans un instant. » : le message dit que l'opération a pu aboutir, et
  l'écran relit l'état avant d'offrir de recommencer.

**Notes de réalisation.** Une seule occurrence relevée, le 2026-11-13 : le `POST` a répondu 201 en
9 599 ms, le front avait rendu la main à 4,9 s. US-2170 d'EP-25 reprend l'attente du bouton et la
relecture de l'écran pour les traitements ; cette US en garde le message de la connexion perdue.

**Hors périmètre.** L'ouverture en tâche de fond, écartée au cadrage. Si la borne ne tient pas, le
dépassement est documenté (US-2300) et devient une issue à trancher.

## US-2250 — Une saisie qui ne déplace rien ne rejoue pas le moteur, et une écriture ne lit l'arbre qu'une fois

- **statut** : à faire
- **exigences** : aucune en propre — le gain se lit dans le rapport de WF-QUA-0060 (US-2300)
- **opérations** : `updateTaskFacet`, `updateEstimateLine`, `setLineRemaining`, `setTaskProgress`,
  `setNodeTracking`, `setPredecessors`
- **issue** : #3317

**En tant que** chef de projet, **je veux** que la saisie d'un libellé ne coûte pas une lecture
entière de la structure, **afin de** saisir plusieurs cellules de suite sans attendre chacune.

**Critères d'acceptation.**

- propre à l'US : les colonnes qui ne peuvent déplacer aucune date ni changer aucun montant sont
  établies par lecture — ce que le moteur lit d'une tâche, ce que la réévaluation lit d'une
  ligne — ; le libellé et la description en sont ; un doute laisse la colonne dans le chemin
  entier ;
- propre à l'US : pour chaque colonne saisissable, un test écrit sur le témoin et constate que la
  réponse ne porte ni tâche redatée ni montant réévalué ; seules les colonnes qui le passent
  prennent le chemin court ;
- propre à l'US : le chemin court ne relit pas l'arbre entier et ne rejoue pas le moteur ; le
  compteur de la structure avance toujours, la réponse et l'historique annulable ne changent pas ;
- propre à l'US : les autres écritures lisent l'arbre une seule fois ;
- propre à l'US : le gain est dit par la mesure d'US-2210 — un libellé, une durée qui redate —,
  avant et après, au-delà de la dispersion.

**Notes de réalisation.** Tous les chemins passent aujourd'hui par `Write`, `replayed` et
`redated_structure` : la cellule d'une tâche, une ligne de devis, l'avancement, le suivi, les
prédécesseurs, le collage (#3169). Le front s'adosse au compteur de la structure à chaque écriture
(`structure-version.ts`).

**Hors périmètre.** Le collage qui crée (US-2260) ; les valeurs dérivées stockées (US-2280).

## US-2260 — Les constats reçus du back des grilles sont soldés

- **statut** : à faire
- **exigences** : aucune en propre — les exigences de ces fonctions sont closes par EP-06 et EP-07
- **opérations** : `createNode`, `moveNodes`, `previewPaste`, `applyPaste`, `updateTaskFacet`,
  `createRevision`
- **issue** : #3300

**En tant que** développeur, **je veux** que les constats de revue rattachés au code des grilles
soient corrigés, **afin que** l'EPIC ne laisse pas derrière lui la dette qu'il a reçue.

**Critères d'acceptation.**

- propre à l'US : le placement mêlé de tâches et de lignes est éprouvé : une tâche créée ou
  déplacée après une ligne, une ligne déplacée après une sous-tâche, une sélection mêlée (#2502) ;
- propre à l'US : un collage qui crée lit le calendrier et les constantes une fois par collage, non
  à chaque ligne ; un collage de grande hauteur est mesuré avant et après (#2605) ;
- propre à l'US : le refus d'horizon d'un collage nomme la ligne qui porte la tâche hors horizon,
  une ligne créée comprise ; un test d'une création hors horizon l'éprouve (#2606) ;
- propre à l'US : un test lit le total d'une même révision, l'ordre de ses lignes renversé, sur le
  chemin que le service emprunte (#2892) ;
- propre à l'US : `docs/api/DECISIONS.md` porte la règle générale — un montant dérivé qui déborde
  sa colonne est refusé au champ qui le provoque —, sans toucher chaque opération (#3093, option
  (b), décision de l'auteur du 2026-11-14) ;
- propre à l'US : la redatation d'une tâche, la copie d'une révision et la copie des taux qui
  débordent un montant sont refusées au champ qui les provoque, un scénario mesuré et un pointeur
  par cause (#3094, décision de l'auteur du 2026-11-14).

**Hors périmètre.** #3138, corrigé par US-2220, qui touche son fichier.

## US-2270 — La lecture d'une structure marquée est calculée une fois et gardée

- **statut** : à faire
- **exigences** : aucune en propre — le gain se lit dans le rapport de WF-QUA-0060 (US-2300)
- **opérations** : `listNodes`, `compareRevisions`, `markRevision`
- **issue** : #3320

**En tant que** chef de projet, **je veux** que la grille d'une révision marquée, qui ne change
plus, ne se recalcule pas à chaque affichage, **afin de** relire une offre ou la base d'une
comparaison sans attendre.

**Critères d'acceptation.**

- propre à l'US : la lecture entière d'une structure d'une révision marquée est calculée une fois
  et gardée dans PostgreSQL ; `listNodes` d'une révision marquée et `compareRevisions` la lisent ;
- propre à l'US : elle est gardée au marquage, dans sa tâche de fond, si le marquage de PRJ-001
  reste loin de la minute du tableau 15 ; une révision marquée avant le lot la reçoit à sa première
  demande ;
- propre à l'US : ce qui change encore après le marquage est établi par un test — marquer une
  révision, garder le corps de `listNodes`, changer une inscription de suivi, le libellé d'un lot,
  un reste à engager tenu ouvert, un calendrier, relire et comparer octet pour octet — ; chaque
  champ qui diffère est joint à la lecture, ou cause d'invalidation ;
- propre à l'US : la lecture gardée sert la lecture entière, projetée par `fields` ou non ; elle
  ne sert une lecture filtrée que si filtrer le document coûte moins du tiers d'une lecture depuis
  les lignes (#3168), et une lecture filtrée garde sinon le chemin des lignes ; là où elle sert, le
  corps rendu est le même que depuis les lignes (SHA-256) ;
- propre à l'US : le volume gardé est mesuré, et rapproché des 150 à 200 Go du §4.6.2 ;
- propre à l'US : le gain est dit par la mesure — la grille d'une révision marquée,
  `compareRevisions` de deux révisions marquées —, avant et après, au-delà de la dispersion.

**Notes de réalisation.** La base d'une comparaison sera toujours marquée (#3176) : cette lecture
gardée est la moitié stable de toute comparaison d'EP-27, dont elle est le préalable. Rapports de
la session cloud, à refaire : relire un document gardé coûte un dixième d'une lecture depuis les
lignes ; il pèse 7,8 Mo, 0,46 Mo compressé.

**Hors périmètre.** « Écarts seulement », que la spécification 1.0.6 change en repli des branches
sans écart — EP-27 ; les options 2 et 3 de #3168.

## US-2280 — Le planning ne lit plus les lignes de devis : leurs sommes par tâche viennent d'un agrégat, ou sont stockées à l'écriture si la mesure le demande

- **statut** : à faire
- **exigences** : aucune en propre — le gain se lit dans le rapport de WF-QUA-0060 (US-2300)
- **opérations** : `listNodes`, et toutes les écritures d'une structure
- **issue** : #3318

**En tant que** chef de projet, **je veux** que le planning ne lise que ses mille tâches, **afin
de** l'ouvrir sans payer les cinq mille lignes de devis qu'il n'affiche pas.

**Critères d'acceptation.**

- propre à l'US : chaque valeur que la lecture dérive aujourd'hui pour tous les nœuds — les états
  des récapitulatives, l'attente des lignes propres, les sommes, le numéro de ligne, le niveau —
  est inventoriée, avec qui la lit et ce qu'une lecture partielle en demande ;
- propre à l'US : `listNodes` avec `kinds=task` ne charge plus les nœuds des lignes : les sommes,
  le nombre et la tenue ouverte des lignes de chaque tâche viennent d'un agrégat, le niveau et le
  numéro de ligne se déduisent des tâches et de ces nombres ; les réponses ne changent pas
  (SHA-256, comme US-2220) ;
- propre à l'US : le lot mesure l'ouverture du planning ainsi lue. Si elle tient la seconde du
  tableau 15 du clic à l'affichage, pour un utilisateur seul, l'US est finie ; sinon, un second lot
  stocke à l'écriture ce que l'agrégat lit trop lentement (décision de l'auteur du 2026-11-14, au
  cadrage : le lot essaie les deux voies et tranche par la mesure) ;
- propre à l'US, si le second lot a lieu : un test d'invariant tient, après chaque chemin
  d'écriture sur le témoin — une saisie, un geste de structure, un collage, l'annulation et le
  rétablissement, la copie d'une révision, un import, la mise à jour des taux, le chargement du
  témoin —, que les valeurs stockées égalent celles que la lecture dérive, gardée comme oracle ;
  aucune ligne d'une révision marquée n'est écrite (WF-REV-0020), une révision marquée avant le lot
  gardant la dérivation à la lecture ; le coût ajouté à une écriture est mesuré ;
- propre à l'US : le gain est dit par la mesure — l'ouverture du planning —, avant et après,
  au-delà de la dispersion.

**Notes de réalisation.** Dériver les états et les sommes pèse moins d'un dixième d'une lecture
entière (#3170) : le gain n'est pas là, mais dans ce qu'une lecture peut alors laisser de côté.
#3170 proposait le seul stockage ; l'agrégat, relevé au cadrage, lit les mêmes valeurs sans
migration ni invariant à tenir.

**Hors périmètre.** Une lecture par fenêtre de lignes : aucune opération nouvelle n'est prévue.

## US-2290 — Les parcours lourds contre le service ont des bornes de temps mesurées, et le parcours en quarantaine est rejoué

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : `listNodes`
- **issue** : #3323

**En tant que** développeur, **je veux** que les parcours qui lisent PRJ-001 contre le service
attendent ce que la mesure justifie, **afin que** la file de fusion ne perde plus un passage sur
une lecture lente.

**Critères d'acceptation.**

- propre à l'US : les bornes de temps des parcours qui lisent PRJ-001 contre le service sont
  fixées d'après les durées mesurées, corrections livrées, et écrites en un seul endroit, avec ce
  qui les justifie ;
- propre à l'US : la cause de l'échec de `structure.spec.ts:335` — un choix fait avant
  l'hydratation du menu, ou une navigation perdue sous la charge — est établie sur les journaux de
  la file ; le parcours est rejoué contre le service, sa quarantaine retirée (#3087) ;
- propre à l'US : les processus de l'API, les workers de Playwright et les cœurs du runner sont
  accordés (#3172, « L'effet dans la chaîne ») ;
- propre à l'US : `make queue-report` sur `epic/EP-26` montre moins d'un échec sur dix sur
  cinquante passages.

**Hors périmètre.** Le parcours de la comparaison de PRJ-001, en quarantaine (#3192) — EP-27.

## US-2300 — Le rapport de mesures d'une version : chaque opération du tableau 15, à cinquante utilisateurs, comparée à la version précédente

- **statut** : en cours
- **exigences** : `WF-QUA-0060-A`
- **opérations** : `listNodes`, `updateTaskFacet`, `updateEstimateLine`, `getProjectWorkload`,
  `markRevision`, `openImport`, `applyImport`, `requestExport`, `getBackgroundTask`
- **issue** : #3325

**En tant qu'** exploitant, **je veux** le rapport de mesures de chaque version, comparé à celui de
la précédente, **afin de** savoir avant de la publier si elle tient ses temps de réponse ou si elle
glisse.

**Critères d'acceptation.**

- `WF-QUA-0060-A` — « Le rapport de mesures d'une version cite chaque opération du tableau, sa
  durée et celle de la version précédente. » : le rapport est versionné dans le dépôt, une ligne
  par opération du tableau 15, avec son objectif, sa durée, sa dispersion et la durée de la version
  précédente ;
- `WF-QUA-0060-A` — « Un ralentissement artificiel de trente pour cent sur une opération est
  signalé par la chaîne. » : la chaîne confronte le rapport d'une version à celui de la précédente,
  et signale un objectif dépassé ou une dégradation de plus d'un quart ;
- `WF-QUA-0060-A` — « Les mesures sont faites aux volumes du §4.6.2. » : sur PRJ-001 du témoin
  chargé — mille tâches, cinq lignes de devis par tâche —, un marquage de cette révision, un import
  de dix-huit mille lignes de coût, l'export de son planning ;
- écart : les opérations du tableau 15 que le service ne sert pas encore figurent au rapport,
  nommées, sans durée, avec l'EPIC qui les mesurera à leur livraison par le même outil : les
  indicateurs et la projection de dépenses (EP-10), les vues de portefeuille (EP-11), la grille
  comparée et la saisie dans une grille comparée (EP-27) ;
- écart : les trois cents projets et les quinze ans de révisions du jeu de référence (WF-QUA-0040)
  sont à EP-13, qui rejoue la mesure dessus ;
- propre à l'US : les durées sont prises avec cinquante utilisateurs simultanés : cinquante
  utilisateurs virtuels jouent chacun le parcours des grilles sur PRJ-001, un geste toutes les dix
  secondes en moyenne, neuf lectures pour une saisie, pendant qu'un navigateur mesure chaque
  opération d'écran du clic à l'affichage (décision de l'auteur du 2026-11-14, au cadrage : le
  §4.6.2 dit cinquante utilisateurs actifs, non cinquante requêtes simultanées) ;
- propre à l'US : elles sont mesurées sur un poste, par une commande du dépôt, plateforme de
  service lancée et témoin chargé ; la chaîne ne mesure pas, elle confronte les rapports versionnés
  (décision de l'auteur du 2026-11-14, au cadrage : les durées d'un runner varient du simple au
  double) ;
- propre à l'US : un dépassement ou une dégradation signalés et non documentés dans le rapport font
  échouer la chaîne ; documentés, ils passent ;
- propre à l'US : le premier rapport est celui de la version que livre cet EPIC ; il documente
  chaque objectif encore dépassé, le filtre, le tri et la recherche contre leurs deux secondes
  compris (#3171).

**Notes de réalisation.** L'annexe C de la spécification nomme k6 pour les tests de charge. La
mesure d'US-0110, contre le faux back, renvoyait la seconde tenue à EP-13 : c'est ici qu'elle se
mesure contre le service.

**Hors périmètre.** Rendre un objectif bloquant : WF-QUA-0060 demande qu'un dépassement soit
signalé et documenté, non interdit.
