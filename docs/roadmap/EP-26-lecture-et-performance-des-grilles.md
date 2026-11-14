---
id: EP-26
titre: Ouvrir, filtrer et saisir dans une grille de mille tâches sans attendre
statut: à planifier
depend_de: EP-25
famille: back, front
issue:
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
refonte, et avancent sur les créneaux libres. Les durées de référence du parcours, elles, se
prennent sur les écrans de travail refondus (US-2140 d'EP-25) : les lots qui les mesurent
l'attendent. `epic/EP-26` se fusionne dans `main` après `epic/EP-25`, jamais avant.

La mesure de référence précède tout lot de correction : sans elle, aucun lot ne sait ce qu'il
gagne.

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

À écrire, après la validation des US.

---

## US-2210 — La mesure de référence des grilles : dans le processus, puis du clic à l'affichage contre le service, à un, quatre et huit utilisateurs

- **statut** : à faire
- **exigences** : aucune en propre — l'outil de WF-QUA-0060, que clôt US-2300
- **opérations** : `listNodes`, `updateTaskFacet`, `updateEstimateLine`, `createRevision`, `getMe`
- **issue** :

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
  d'`opening.spec.ts` —, en trois parts : l'API, lue dans ses journaux par l'identifiant de
  corrélation ; Next, par différence ; le navigateur ; et le poids de la réponse ;
- propre à l'US : le parcours est joué par un, quatre et huit utilisateurs à la fois, un compte
  chacun, la connexion hors de la mesure ; la durée de `getMe` pendant ce temps est relevée ;
- propre à l'US : cinq passages identiques donnent la dispersion ; le rapport écrit, par étape, la
  médiane, la pire et la dispersion, et un écart sous la dispersion n'y est pas dit un gain ;
- propre à l'US : la mesure n'échoue jamais sur une durée, et ne tourne pas dans la chaîne ;
- propre à l'US : le rapport de référence, pris sur les écrans de travail refondus (US-2140
  d'EP-25), est versionné avant tout lot de correction ;
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

- **statut** : à faire
- **exigences** : aucune en propre — le gain se lit dans le rapport de WF-QUA-0060 (US-2300)
- **opérations** : `listNodes`, `compareRevisions`
- **issue** :

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

- **statut** : à faire
- **exigences** : `WF-ARC-0080-A`
- **opérations** : toutes celles que le service sert ; `getMe` pour la mesure
- **issue** :

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
- **issue** :

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
- **issue** :

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
- **issue** :

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
- **issue** :

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
- propre à l'US : un filtre et la projection `fields` appliqués à la lecture gardée rendent le même
  corps que la lecture depuis les lignes (SHA-256), pour chaque filtre de `listNodes` ;
- propre à l'US : le volume gardé est mesuré, et rapproché des 150 à 200 Go du §4.6.2 ;
- propre à l'US : le gain est dit par la mesure — la grille d'une révision marquée,
  `compareRevisions` de deux révisions marquées —, avant et après, au-delà de la dispersion.

**Notes de réalisation.** La base d'une comparaison sera toujours marquée (#3176) : cette lecture
gardée est la moitié stable de toute comparaison d'EP-27, dont elle est le préalable. Rapports de
la session cloud, à refaire : relire un document gardé coûte un dixième d'une lecture depuis les
lignes ; il pèse 7,8 Mo, 0,46 Mo compressé.

**Hors périmètre.** « Écarts seulement », que la spécification 1.0.6 change en repli des branches
sans écart — EP-27 ; les options 2 et 3 de #3168.

## US-2280 — Sommes, états, numéros de ligne et niveaux sont stockés à l'écriture, et le planning ne lit plus les lignes de devis

- **statut** : à faire
- **exigences** : aucune en propre — le gain se lit dans le rapport de WF-QUA-0060 (US-2300)
- **opérations** : `listNodes`, et toutes les écritures d'une structure
- **issue** :

**En tant que** chef de projet, **je veux** que le planning ne lise que ses mille tâches, **afin
de** l'ouvrir sans payer les cinq mille lignes de devis qu'il n'affiche pas.

**Critères d'acceptation.**

- propre à l'US : sont stockés à l'écriture, par tâche, ses montants sommés et son état dérivé, et
  par nœud, son numéro de ligne et son niveau — et seulement ce qu'une lecture partielle demande :
  chaque valeur que la lecture dérive aujourd'hui est inventoriée, avec qui la lit ;
- propre à l'US : un test d'invariant tient, après chaque chemin d'écriture sur le témoin — une
  saisie, un geste de structure, un collage, l'annulation et le rétablissement, la copie d'une
  révision, un import, la mise à jour des taux, le chargement du témoin —, que les valeurs stockées
  égalent celles que la lecture dérive ; la dérivation reste dans les tests, comme oracle ;
- propre à l'US : `listNodes` avec `kinds=task` ne lit plus les nœuds des lignes ; les réponses ne
  changent pas (SHA-256, comme US-2220) ;
- propre à l'US : aucune ligne d'une révision marquée n'est écrite (WF-REV-0020) : une révision
  marquée avant le lot garde la dérivation à la lecture, qu'US-2270 ne fait qu'une fois ;
- propre à l'US : le coût ajouté à une écriture est mesuré — les lignes mises à jour par une
  saisie, la durée — ;
- propre à l'US : le gain est dit par la mesure — l'ouverture du planning —, avant et après,
  au-delà de la dispersion.

**Notes de réalisation.** Dériver les états et les sommes pèse moins d'un dixième d'une lecture
entière (#3170) : le gain n'est pas là, mais dans ce qu'une lecture peut alors laisser de côté. Les
sommes stockées par tâche serviront aussi le total de la base d'une comparaison (EP-27).

**Hors périmètre.** Une lecture par fenêtre de lignes : aucune opération nouvelle n'est prévue.

## US-2290 — Les parcours lourds contre le service ont des bornes de temps mesurées, et le parcours en quarantaine est rejoué

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : `listNodes`
- **issue** :

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

- **statut** : à faire
- **exigences** : `WF-QUA-0060-A`
- **opérations** : `listNodes`, `updateTaskFacet`, `updateEstimateLine`, `getProjectWorkload`,
  `markRevision`, `openImport`, `applyImport`, `requestExport`, `getBackgroundTask`
- **issue** :

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
- propre à l'US : les durées sont prises avec cinquante utilisateurs simultanés ;
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
