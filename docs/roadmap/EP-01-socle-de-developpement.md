---
id: EP-01
titre: Rendre le dépôt capable de porter du code, sans en écrire une ligne de métier
statut: en cours
depend_de: rien
issue: 3
---

# EP-01 — Socle de développement

## Objet

La structure du dépôt et les outils de l'annexe C, le client engendré du contrat, un faux
back tiré de ce même contrat, les fixtures issues des champs Vérif, et les contrôles que la
chaîne rend bloquants. Aucune règle métier, aucune table.

Il vient en premier pour une raison qui n'est pas de commodité : le typage strict, l'analyse
statique et la couverture des exigences par les tests sont bloquants par exigence
(WF-QUA-0010, WF-QUA-0030). Installés après, ils se heurteraient à du code écrit sans eux,
et la première chose qu'on ferait serait de les assouplir.

Les US de cet EPIC n'ont pas d'acteur du §3.1.3 : leur bénéficiaire est celui qui développe.

Il se mène de près, et non en autonomie : ses premiers lots fixent les conventions par
l'exemple — l'arborescence, le premier test, la première règle d'analyse —, et tout ce qui
suivra les imitera. Les agents de l'US-0280 prennent le relais à partir d'EP-02.

## Ce qui en fait partie

- le guide de développement et les règles de codage Python et TypeScript, que les personnes
  comme les agents lisent avant d'écrire ;
- la chaîne d'intégration sur GitHub Actions, sur toute pull request, vers une branche
  d'EPIC comme vers `main`, et la commande qui mesure la taille réelle d'un lot ;
- la structure du dépôt : front (PBS-1), service d'API et worker (PBS-2.1, PBS-2.2), noyau
  métier (PBS-2.3), et le contrôle qui interdit à un module du noyau de lire les tables d'un
  autre ;
- le client TypeScript engendré du contrat (PBS-1.2), régénéré par une commande, jamais
  retouché à la main ;
- un faux back servi par prism depuis le bundle du contrat, et le fichier Compose qui le
  démarre avec le front ;
- l'outil qui extrait les exemples chiffrés des champs Vérif et les écrit en fixtures ;
- le lint, le contrôle de typage et le contrôle de format, front et back, bloquants et sans
  avertissement toléré ; le lint des workflows, des scripts shell et des Dockerfile ;
- le rapport de couverture des exigences par les tests, et le refus de publier tant qu'une
  exigence F0 n'est couverte par aucun test ;
- l'outil de couverture de la roadmap : quelle exigence n'est citée par aucune US ;
- le harnais de tests de bout en bout, avec un parcours témoin contre le faux back ;
- les agents : celui qui cadre un EPIC jusqu'à ses issues, celui qui en livre les lots, et
  pour chaque langage celui qui développe et celui qui relit ; et les règles communes qu'ils
  lisent tous.

## Ce qui n'en fait pas partie

- toute règle métier, tout calcul, toute table : il n'y a pas encore de base — EP-03 ;
- les écrans — EP-02 ; seul le parcours témoin du harnais touche le front ;
- le jeu de données de référence de WF-QUA-0040, qui demande le modèle : il naît en EP-04 et
  grossit avec chaque EPIC ;
- les sept flux de bout en bout de WF-QUA-0050 — EP-12 ;
- la livraison continue — la construction et la publication des images, le chart Helm, tout
  déploiement — et les tests de charge de WF-QUA-0060 — EP-13 : la chaîne d'EP-01 intègre
  et contrôle, elle ne publie rien ;
- le contrôle de complétude des catalogues de traduction (WF-QUA-0070), qui attend qu'il y
  ait des catalogues — EP-02.

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-ARC-0010-A` | Un noyau, un service, un worker | début — close en EP-11 | US-0010 |
| `WF-ARC-0060-A` | Contrat OpenAPI | début — close en EP-03 | US-0020 |
| `WF-QUA-0010-A` | Traçabilité des exigences par les tests | entière | US-0060 |
| `WF-QUA-0020-A` | Les exemples chiffrés du document sont des cas de test | début — close en EP-11 | US-0040 |
| `WF-QUA-0030-A` | Typage et analyse statique bloquants | entière | US-0050 |
| `WF-QUA-0050-A` | Tests de bout en bout | début — close en EP-13 | US-0080 |

Quatre de ces six ne sont réalisées qu'en partie, et chaque US dit laquelle de ses phrases
de Vérif attend un autre EPIC : il n'y a ici ni règle métier à tester (WF-ARC-0010,
WF-QUA-0020), ni service dont on puisse comparer les réponses au schéma (WF-ARC-0060), ni
plateforme complète à parcourir (WF-QUA-0050). Seules WF-QUA-0010 et WF-QUA-0030 sont closes
par cet EPIC.

## Opérations du contrat

Aucune n'est servie : le faux back sert le contrat entier tel qu'il est, sans en choisir.
`make mock-spec` en dérive la variante que prism sert. Le parcours témoin (US-0080) consomme
`listProjects`, `getProject`, `listRevisions`, `listCostStructures` et `listNodes`, et ce sont
les seules opérations auxquelles EP-01 ajoute des exemples : c'est sa seule modification du
contrat. `listCostStructures`, absente de la conception, s'est révélée nécessaire en
livrant l'US-0030 : les nœuds se lisent par structure, et aucune des quatre autres ne la
donne.

## Préalables

Rien. Le contrat est écrit et `make lint-openapi` passe.

## Définition de fini

- les contrôles qui existent déjà — projection de la spécification, lint du contrat,
  inventaire — tournent dans la chaîne ;
- une commande régénère le client du contrat, et le dépôt est inchangé après ;
- `make mock` sert le faux back, et le front démarre contre lui par le Compose de
  développement ;
- une faute de typage, une violation de règle d'analyse et un écart de format introduits
  exprès font chacun échouer la chaîne ;
- le rapport de couverture des exigences liste les 195 exigences F0 et celles que nul test
  ne couvre ;
- le relevé de couverture de code donne les lignes et les branches du back et du front, et
  un seuil manqué empêche la fusion ;
- l'outil de la roadmap liste les exigences qu'aucune US ne cite ;
- le parcours témoin de bout en bout aboutit contre le faux back ;
- la chaîne exécute tout ce qui précède, chaque contrôle à son palier et seulement pour ce
  que la pull request touche, et échoue sur chacun de ces points ;
- une pull request dont la chaîne échoue ne peut pas être fusionnée ;
- `make lot-size` donne la taille d'un lot hors code engendré, production et tests séparés ;
- le guide de développement et les règles de codage Python et TypeScript existent, et
  chacune de leurs règles qu'un outil peut contrôler nomme ce contrôle ;
- les deux agents de revue, lancés sur une pull request piégée, relèvent à eux deux chacun
  des pièges ; l'agent de cadrage, lancé à blanc sur EP-02, rend la conception et le plan de lots
  qu'il proposerait, sans rien publier. Ces deux essais se jouent à la main : la chaîne
  n'exécute pas d'agent.

## Conception

EP-01 n'a ni table ni migration, ni module métier : sa conception est celle de l'outillage.
Elle fixe où chaque chose vit, quel outil tient quel contrôle, et comment la chaîne les
enchaîne. Les versions ne sont pas fixées ici : elles vivent dans les fichiers de
dépendances et leurs verrous.

### Arborescence

| Chemin | Contenu | PBS |
|---|---|---|
| `backend/` | un seul projet Python, un seul paquet `waterfall` | PBS-2 |
| `backend/src/waterfall/core/` | le noyau : un sous-paquet par module, calqué sur un bloc FBS | PBS-2.3 |
| `backend/src/waterfall/api/` | le service d'API | PBS-2.1 |
| `backend/src/waterfall/worker/` | le worker | PBS-2.2 |
| `backend/tests/` | les tests du back, rangés comme le code qu'ils éprouvent | — |
| `frontend/` | l'application Next.js et ses tests | PBS-1.1, PBS-1.3 |
| `frontend/src/api/` | le client engendré, versionné, jamais retouché | PBS-1.2 |
| `frontend/e2e/` | les parcours de bout en bout | — |
| `fixtures/` | le relevé engendré des exemples chiffrés, et les fixtures qui s'y rattachent | — |
| `tools/` | les outils du dépôt, en Python, avec leurs tests | PBS-5.2 |
| `.github/workflows/` | la chaîne | PBS-5.2 |
| `docs/dev/` | le guide et les règles de codage | — |
| `deploy/compose/` | les fichiers Compose : celui du développement dès EP-01, celui d'une installation sur une machine seule en EP-13 | PBS-5.1 |
| `deploy/helm/` | le chart Helm, en EP-13 | PBS-5.1 |

À la racine : le Makefile, `REUSE.toml`, et `tools/paths.toml`, qui déclare les chemins
engendrés et les tests (US-0310). Un Dockerfile reste à côté du composant qu'il construit,
qui est son contexte de construction.

Décisions :

- **Un seul paquet Python pour l'API, le worker et le noyau**, avec deux points d'entrée.
  L'API et le worker portent ainsi la même version par construction, ce que demande la
  troisième phrase du Vérif de WF-ARC-0010 : il n'existe qu'un numéro de version à publier.
  Écarté : un paquet par processus et un paquet partagé pour le noyau — trois versions à
  tenir alignées, et un alignement qui se vérifie au lieu d'être impossible à rompre.
- **Les modules du noyau naissent avec l'EPIC qui les remplit**, et non en squelette vide
  dès EP-01. Leur nom est celui du bloc FBS de second niveau, en anglais. Écarté : créer
  aujourd'hui une vingtaine de paquets vides, qui figeraient un découpage que seul le
  premier code éprouvera.
- **Les outils du dépôt vivent dans `tools/`**, un paquet Python unique dont un module lit la
  projection de la spécification pour tous : couverture des exigences, couverture de la
  roadmap, relevé des exemples chiffrés, taille des fichiers, taille d'un lot. `inventory.py`
  s'y rallie pour lire les exigences, au lieu d'avoir son propre lecteur. Écarté : un script
  par contrôle, chacun avec sa lecture du Markdown — cinq lecteurs divergeraient.
- **L'empaquetage vit dans `deploy/`**, un sous-répertoire par empaquetage du PBS-5.1 —
  Compose et Helm. Le Makefile porte le chemin des fichiers, et personne n'a à le retenir.
  Écarté : le fichier Compose à la racine, qui mêlerait l'empaquetage aux sources, et
  `infra/`, qui désigne d'habitude le provisionnement des machines, que Waterfall ne fait
  pas.
- **Les outils sont du code, et les règles de l'US-0050 s'y appliquent** : un contrôle qui
  échoue à ses propres règles ne peut pas les faire tenir aux autres. Les outils de
  `docs/spec/tools` et `docs/api/tools` y sont mis à niveau dans un lot à part, sans rien
  changer à ce qu'ils produisent — la projection et l'inventaire restent identiques.

### Back

- **uv** gère le projet Python, son environnement et son verrou. Écarté : Poetry et
  pip-tools, plus lents, alors que la durée de la chaîne est une contrainte (US-0310).
- Ruff pour le lint et le format, Pyright en mode strict, Pytest et pytest-cov : les outils
  de l'annexe C, et rien d'autre dans EP-01 — FastAPI, SQLAlchemy et le reste arrivent en
  EP-03 avec le premier service.
- **Frontières du noyau : import-linter.** Chaque module n'est importable par un autre que
  par son interface publique ; ses tables et son accès aux données sont privés ; le noyau
  n'importe ni l'API ni le worker. Les contrats sont déclaratifs et se lisent dans la
  configuration. Écarté : un contrôle écrit pour le dépôt, qui referait mal ce que l'outil
  fait. Limite : une requête SQL écrite en texte, qui nommerait la table d'un autre module,
  échappe à l'analyse des imports ; elle est interdite par les règles SQL d'EP-03 et
  cherchée par la revue. Faute de module en EP-01, le contrôle s'éprouve sur un paquet
  d'essai dans les tests de `tools/` : un module qui lit les tables d'un autre y est rejeté.
- Coverage.py n'applique qu'un seuil unique, qui mêle lignes et branches : les deux seuils
  de l'US-0060 sont appliqués par l'outil de couverture de `tools/`, qui lit le relevé de
  coverage.py.

### Front

- **pnpm** gère le projet et son verrou. Écarté : npm, plus lent à installer et plus
  permissif sur les dépendances non déclarées.
- Next.js et TypeScript en mode strict ; ESLint et Prettier ; **Vitest** et son module de
  couverture pour les tests unitaires, que l'annexe C ne nomme pas et qu'il faut pour
  l'US-0060 ; Playwright pour le bout en bout.
- **Les dépendances d'affichage de l'annexe C** — Tailwind CSS, shadcn/ui, les icônes
  Lucide, TanStack Table et Apache ECharts — ne sont pas du code du dépôt, mais ce sont des
  dépendances : elles se déclarent et se verrouillent comme les autres, et suivent les mêmes
  mises à jour. Elles s'installent en EP-02, avec le premier écran qui s'en sert, et non en
  EP-01 : une dépendance que rien n'importe n'est éprouvée par rien, et l'analyse du front la
  signalerait comme inutilisée. Les pages du parcours témoin n'en ont pas besoin.
- **Client : openapi-typescript et openapi-fetch.** Le premier engendre les seuls types, le
  second est un appel typé de quelques lignes. Écarté : orval et hey-api, qui engendrent une
  fonction par opération — beaucoup de code engendré, et la tentation de l'envelopper à la
  main, ce qui recrée le client écrit à la main que WF-ARC-0020 interdit.
- **Aucun appel réseau hors du client** : une règle ESLint refuse `fetch` hors de
  `frontend/src/api/`. Elle prépare WF-ARC-0020, qu'EP-02 réalise, pour un coût nul
  aujourd'hui.
- **Le parcours témoin s'appuie sur trois pages minimales** — liste des projets, projet,
  grille —, sans mise en forme ni texte propre, qu'EP-02 remplace en gardant le test. Écarté :
  un parcours qui ne touche aucune page, qui n'éprouverait pas le harnais.

### Contrat, faux back et fixtures

- Le contrat ne porte aujourd'hui aucun exemple : prism, sans exemple, ne répond que des
  valeurs tirées des types. **Les jeux de données du faux back sont des exemples du
  contrat**, comme le prévoit l'US-0030 ; EP-01 en ajoute aux seules opérations du parcours
  témoin, EP-02 aux autres. C'est la seule modification du contrat que prévoit EP-01.
- **Relevé des exemples chiffrés.** L'outil relève dans la projection chaque phrase de Vérif
  qui porte un exemple chiffré, et l'écrit dans `fixtures/` sous une clé faite de
  l'identifiant de l'exigence et de l'empreinte du texte de la phrase. Ce relevé est
  engendré. Une fixture est un fichier de données écrit à la main qui cite la clé de sa
  phrase : l'outil signale une phrase qu'aucune fixture ne cite, et fait échouer la chaîne
  sur une fixture dont la clé n'existe plus — sa phrase a changé ou disparu. Le rang de la
  phrase n'entre pas dans la clé : une phrase insérée avant une autre la décalerait, et la
  fixture d'une phrase inchangée échouerait à tort. Écarté : tirer les valeurs de la prose automatiquement —
  « deux projets de valeur acquise 100 et 1 000… » ne se structure pas sans le comprendre,
  et un analyseur de phrases se tromperait en silence.
- Un exemple du contrat reprend une fixture par référence, et le bundle l'embarque : les
  nombres que sert le faux back sont alors ceux du document, sans copie.
- **Compose de développement**, dans `deploy/compose/` : deux services, le faux back servi par prism depuis le
  bundle et le front en mode développement, leurs images épinglées par empreinte ; le front
  ne connaît que l'adresse de l'API, qui désignera le vrai service en EP-03 sans autre
  changement.

### Citation des exigences par les tests

- Pytest : un marqueur `requirement` qui porte l'identifiant complet, indice de révision
  compris, déclaré pour que Pytest refuse un marqueur mal écrit.
- Vitest et Playwright : l'identifiant entre crochets dans le titre du test,
  `[WF-QUA-0050-A]` ; Playwright en fait aussi une étiquette de sélection.
- Un seul outil de rapport lit les trois relevés — la collecte de Pytest, les relevés JSON de
  Vitest et de Playwright — et les confronte aux exigences F0 de la projection. Un
  identifiant inconnu, ou d'un indice de révision périmé, le fait échouer, comme l'outil de la
  roadmap. Écarté : une étiquette différente par outil, lue par trois rapports.

### Chaîne

- Un workflow par famille — back, front, contrat, spécification, roadmap, dépôt (REUSE,
  actionlint, shellcheck, hadolint, taille des fichiers). Chaque étape appelle une commande du
  Makefile.
- **Déclencheurs** : `pull_request` pour le palier rapide, `merge_group` — la file de fusion
  de GitHub — pour le palier complet. La file de fusion éprouve la pull request fusionnée
  avant d'accepter la fusion, ce qui est exactement « au moment de fusionner ». Elle se règle
  par un jeu de règles qui vise `main` et `epic/*` ; que ce jeu couvre bien les branches
  `epic/*` se vérifie au premier lot de la chaîne. S'il ne le fait pas, l'agent de livraison
  déclenche le palier complet sur la pull request avant de fusionner.
- **Sélection par côté** : un premier travail calcule ce que la pull request touche, par
  une commande du Makefile qui lit `tools/paths.toml`, et les travaux suivants ne
  s'exécutent que pour ce qui est touché. Un dernier travail, **toujours exécuté**, réunit
  les résultats, et c'est le seul que la protection des branches exige. Écarté : filtrer par
  chemins au déclenchement des workflows — un contrôle exigé qui ne s'exécute pas faute de
  fichier touché reste « en attente » et bloque la fusion, défaut connu de GitHub.
- Actions tierces épinglées par empreinte, et **Dependabot** pour les tenir à jour, une fois
  par mois, les actions seulement : une action épinglée qu'on ne met jamais à jour garde ses
  failles.
- Cache des dépendances d'uv et de pnpm, et des navigateurs de Playwright ; annulation de
  l'exécution en cours d'une pull request à chaque nouvelle poussée.

### Makefile

Les commandes se nomment `<action>-<côté>` : `lint-back`, `test-front`, `e2e`… Deux
commandes composées servent les agents et les personnes : `check` lance le palier rapide de
ce que le diff touche, `check-all` les deux paliers de tout. Les noms exacts sont fixés par
le premier lot de chaque US et consignés au guide : `make roadmap` vérifie ensuite que les
agents n'en citent aucun qui n'existe pas (US-0280).

### Ordre de construction

1. Le squelette du guide, l'arborescence, `tools/` et son lecteur de la projection,
   `REUSE.toml` et les en-têtes.
2. La chaîne minimale : le workflow du dépôt, ceux de la spécification et du contrat avec
   les contrôles qui existent déjà, le travail de sélection et le travail de synthèse, la
   protection des branches.
3. Le back vide et ses contrôles — lint, typage, format, complexité, frontières.
4. Le front vide et ses contrôles, et Vitest.
5. Le client engendré.
6. Le faux back, les exemples du parcours témoin et le Compose.
7. Le relevé des exemples chiffrés et les premières fixtures.
8. La couverture des exigences et du code.
9. L'outil de la roadmap.
10. Le harnais de bout en bout et le parcours témoin, au palier complet.
11. `make lot-size` et la mise à niveau des outils existants.
12. Les règles de codage, puis les agents.

Le guide s'écrit tout du long : chaque étape y ajoute la section qu'elle établit.

### Sections du guide qu'EP-01 ne peut pas écrire

Trois sujets que l'US-0300 demande au guide n'ont pas encore de matière en EP-01, et c'est
l'EPIC qui les établit qui en écrit la section : l'ajout d'une clé de traduction (US-0190,
EP-02, qui choisit la bibliothèque et crée les catalogues), l'ajout d'un code d'erreur côté
front (US-0190 également) et côté service (EP-03), l'écriture d'une migration (EP-03). EP-01
ouvre ces sections, avec le renvoi à l'US qui les écrira.

---

## US-0300 — Guide de développement et règles de codage

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #4
**En tant que** développeur, **je veux** un guide qui fixe l'arborescence et les conventions
du dépôt, et des règles de codage qui disent comment s'écrit le Python et comment s'écrit le
TypeScript, **afin que** le premier lot et le centième se ressemblent, qu'une personne ou un
agent les ait écrits.

**Critères d'acceptation.**

- propre à l'US : le guide couvre au moins l'arborescence et le rôle de chaque répertoire ; le
  nommage, en anglais et selon le tableau du §4.4.1 ; la forme d'un test qui cite son
  exigence, et celle d'un test qui reprend un exemple chiffré ; l'enveloppe d'erreur et
  l'ajout d'un code ; l'ajout d'une clé de traduction ; les branches, les lots et les pull
  requests ;
- écart : l'ajout d'une clé de traduction et l'ajout d'un code d'erreur côté front
  s'écrivent avec l'US-0190 (EP-02), qui choisit la bibliothèque et crée les catalogues ;
  l'ajout d'un code d'erreur côté service, avec EP-03, qui crée le service. EP-01 ouvre ces
  sections dans le guide, chacune avec le renvoi à l'US ou à l'EPIC qui l'écrira ; une
  section vide sans renvoi laisse l'US inachevée ;
- propre à l'US : `docs/dev/` porte un fichier de règles de codage par langage, l'un pour
  Python, l'autre pour TypeScript. Chacun nomme d'abord les jeux de règles d'analyse, de
  typage et de format activés, en renvoyant à leur configuration sans la recopier ; puis il
  énonce les règles de conception qu'aucun outil ne contrôle — la découpe d'un module, la
  forme d'une route, d'un schéma ou d'un composant, le traitement des erreurs, l'accès aux
  données et à l'API, la forme des tests —, chacune avec sa raison ;
- propre à l'US : chaque fichier de règles de codage tient la liste des défauts déjà
  rencontrés dans son langage, chacun avec le scénario qui le déclenche ; c'est elle que
  l'agent de revue de ce langage cherche nommément (US-0280), et un défaut relevé en revue
  qui se reproduira s'y ajoute ;
- propre à l'US : le guide dit ce qu'un commentaire doit porter et que nul outil ne
  vérifie : la raison d'un choix, non la paraphrase du code ; l'anglais, comme le code ; et
  il renvoie à l'US-0050 pour les en-têtes, les docstrings, le code commenté et les `TODO` ;
- propre à l'US : chaque règle qu'un outil peut contrôler l'est, et le guide nomme le
  contrôle ; une règle que rien ne contrôle le dit ;
- propre à l'US : le guide ne recopie ni la spécification, ni le contrat, ni CONTRIBUTING, ni
  la roadmap : il y renvoie ; et les agents (US-0280) renvoient au guide et aux règles de
  codage au lieu de les répéter.

**Notes de réalisation.** Le guide et les règles de codage vivent dans `docs/dev/`, et la
section « Changing the code » de CONTRIBUTING y renvoie. Le guide s'ouvre avant le premier
lot, en squelette, et chaque US de cet EPIC y écrit la section qu'elle établit : une
convention se fixe en l'appliquant, pas avant. Les règles de codage partent des conventions
des agents qui existent déjà hors du dépôt (US-0280), après un tri : ce qui contredit la
spécification ou le contrat n'est pas repris — identifiants entiers au lieu d'UUID, erreurs
rendues en phrase au lieu de l'enveloppe à code, tests sur une autre base que PostgreSQL,
client d'API écrit à la main, textes de l'interface écrits en dur hors des catalogues,
absence de Prettier. Les défauts qu'y relevaient les relecteurs — une réponse construite
après la validation de la transaction, un agrégat recalculé par une route et pas par sa
voisine, une réponse périmée qui écrase la sélection courante, un statut terminal oublié —
ne dépendent pas de ce code-là : ils amorcent la liste des défauts déjà rencontrés.

**Hors périmètre.** Les règles d'écriture du SQL et des migrations : elles se fixent avec la
première table, en EP-03, dans un troisième fichier de règles de codage.

## US-0010 — Structure du dépôt et frontières du noyau

- **statut** : fini
- **exigences** : `WF-ARC-0010-A`
- **opérations** : aucune
- **issue** : #5
**En tant que** développeur, **je veux** un dépôt où chaque composant du PBS a sa place et
où les frontières entre modules du noyau sont contrôlées par la chaîne, **afin que** la
règle « une seule implémentation » ne repose pas sur la vigilance de chacun.

**Critères d'acceptation.**

- `WF-ARC-0010-A` — « Un module qui lit une table d'un autre module est rejeté par les
  contrôles de la chaîne CI/CD. »
- `WF-ARC-0010-A` — « L'API et le worker d'une installation portent la même version. »
- propre à l'US : le dépôt porte le front, le service d'API, le worker et le noyau, les
  modules du noyau sont calqués sur les blocs FBS, et les outils de l'annexe C sont
  installés avec leurs versions dans les fichiers de dépendances.
- écart : « Le dépôt ne contient qu'une implémentation de la machine d'état, des calculs de
  planning, de chiffrage et d'indicateurs, partagée par l'API et le worker. » ne se vérifie
  qu'à mesure que ces calculs arrivent, d'EP-04 à EP-11, et se constate en EP-11 — il n'y a
  encore aucun calcul.

**Notes de réalisation.** Le contrôle des frontières est une règle d'analyse statique, donc
bloquante au même titre que le reste (WF-QUA-0030) : les modules du noyau ne s'importent
entre eux que par leur interface publique.

## US-0310 — Chaîne d'intégration sur GitHub Actions, branches protégées, mesure des lots

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #6
**En tant que** développeur, **je veux** une chaîne d'intégration sur GitHub Actions qui
s'exécute sur toute pull request,
vers une branche d'EPIC comme vers `main`, qu'aucune de ces branches n'accepte ce qu'elle n'a
pas validé, qu'elle ne lance que ce que la modification touche, et qu'une commande mesure
la taille réelle d'un lot, **afin que** chaque branche d'intégration soit constructible à
tout moment, qu'une modification ne paie en attente que les contrôles qui la concernent, et
que l'écart entre un lot et son estimation se lise au lieu de se deviner.

**Critères d'acceptation.**

- propre à l'US : la chaîne s'exécute sur toute pull request vers `main` ou vers une branche
  `epic/*`, et une pull request dont la chaîne échoue ne peut pas être fusionnée ;
- propre à l'US : la chaîne est faite de workflows GitHub Actions, un par famille de
  contrôles — back, front, contrat, spécification, roadmap, dépôt — ; chaque étape appelle une
  commande du Makefile et aucune logique de contrôle n'est écrite dans un workflow, si bien
  qu'un échec de la chaîne se reproduit sur un poste par la même commande ;
- propre à l'US : les contrôles qui existent déjà y entrent dès le premier lot — la
  projection de la spécification sans avertissement (`make build-doc-strict`), le lint du
  contrat (`make lint-openapi`) et l'inventaire (`make inventory`) ;
- propre à l'US : les dépendances sont mises en cache d'une exécution à l'autre, et une
  nouvelle poussée sur une pull request annule l'exécution encore en cours pour elle ;
- propre à l'US : chaque action tierce est épinglée par son empreinte et non par une
  étiquette ; chaque workflow déclare les seules permissions de son jeton dont il a besoin ;
  aucun secret n'est exposé à une pull request venue d'un fork ;
- propre à l'US : aucune poussée directe n'est acceptée sur `main` ni sur une branche
  `epic/*` ;
- propre à l'US : la chaîne a deux paliers. Le palier rapide s'exécute à chaque poussée sur
  une pull request : format, analyse, typage et tests unitaires. Le palier complet — tests
  d'intégration, tests de bout en bout et seuils de couverture de code (US-0060) —
  s'exécute au moment de fusionner la pull request, et non à chaque poussée ; son échec
  empêche la fusion ;
- propre à l'US : chaque palier ne lance que les contrôles de ce que la pull request touche.
  Une pull request qui ne touche que le front ne lance rien du back, et inversement ; un
  changement du contrat, des dépendances partagées ou de la chaîne elle-même lance les deux
  côtés ; les contrôles de la spécification, du contrat et de la roadmap ne s'exécutent que si
  leurs fichiers sont touchés ;
- propre à l'US : les mêmes sélections existent sur un poste — une commande du Makefile par
  côté et par palier, et une qui lance le palier rapide de ce que le diff touche ;
- propre à l'US : `make lot-size` mesure le diff d'une branche de lot par rapport à la
  branche de son EPIC, hors code engendré, en séparant le code de production des tests ; elle
  informe et n'échoue jamais sur un dépassement ;
- propre à l'US : les chemins engendrés et ceux des tests sont déclarés dans un fichier du
  dépôt, chacun avec ce qui l'engendre ou ce qui le reconnaît comme test.

**Notes de réalisation.** La protection des branches est un réglage de GitHub que seul le
propriétaire du dépôt peut faire : la chaîne ne se l'accorde pas, et l'US n'est finie que
lorsqu'il est fait. Sur une branche `epic/*`, la protection n'exige pas d'approbation
humaine : l'agent de livraison y fusionne un lot dont la revue locale et la chaîne sont au vert
(US-0280). Sur `main`, la fusion est faite par une personne. La taille visée vient de la
section « Lots » du README de la roadmap : la mesure ne la reprend pas, elle donne un nombre
que l'agent de livraison met en regard de l'estimation. Le fichier des chemins engendrés et
des tests sert aussi à la limite de taille des fichiers de l'US-0050. « Au moment de
fusionner » veut dire avant que la fusion soit acceptée, sur le résultat de la fusion : la
file de fusion de GitHub fait exactement cela ; si elle ne s'applique pas aux branches
`epic/*`, l'agent de livraison déclenche le palier complet sur la pull request avant de
fusionner. Un palier complet exécuté après la fusion laisserait la branche de l'EPIC cassée
pendant qu'on s'en aperçoit : c'est ce que la règle « un lot se fusionne seul, la chaîne au
vert » interdit. Le dépôt est public : l'épinglage des actions et la retenue des
permissions ne sont pas des précautions de principe, une action dont l'étiquette est
déplacée exécute le code de quelqu'un d'autre dans la chaîne. La durée des paliers ne porte
pas de seuil : elle croîtra avec le code, et un chiffre fixé aujourd'hui serait ou trop
facile, ou bientôt faux. Elle se lit au relevé de l'agent de livraison (US-0280), EPIC après
EPIC, et un seuil se fixera quand il y aura de quoi le fonder.

## US-0020 — Client d'API engendré du contrat

- **statut** : en cours
- **exigences** : `WF-ARC-0060-A`
- **opérations** : toutes, par engendrement
- **issue** : #7
**En tant que** développeur, **je veux** que le client TypeScript du front soit engendré du
contrat par une commande, **afin qu'**aucun écart entre le contrat et ce que le front appelle
ne puisse s'installer.

**Critères d'acceptation.**

- `WF-ARC-0060-A` — « Le client du front est régénéré à partir du contrat sans retouche à la
  main. »
- propre à l'US : la régénération est une commande du Makefile, et la chaîne échoue si le
  client versionné diffère de celui que le contrat produit.
- écart : « Une réponse de l'API qui ne correspond pas au schéma déclaré fait échouer la
  chaîne. » et « Aucun endpoint ne répond qui ne figure au contrat. » attendent un service
  réel — EP-03.

## US-0030 — Faux back tiré du contrat

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : toutes, servies par prism depuis le bundle
- **issue** : #8
**En tant que** développeur, **je veux** un faux back servi depuis le bundle du contrat,
démarré avec le front par un fichier Compose, **afin de** construire les écrans avant qu'il
existe un service, et d'éprouver le contrat pendant qu'il est encore gratuit de le corriger.

**Critères d'acceptation.**

- propre à l'US : `make mock` sert le bundle, et le front démarre contre lui sans autre
  réglage qu'une adresse ;
- propre à l'US : aucun mock n'est écrit à la main — une réponse qui manque est un exemple
  ajouté au contrat, jamais un fichier de réponse dans le front ;
- propre à l'US : le faux back sert les jeux de données de l'US-0040.

**Notes de réalisation.** La règle « les mocks sont engendrés du contrat, jamais écrits à la
main » vient de `docs/api/README.md` : un mock écrit à la main dérive et ne valide plus rien.
Le faux back survit à la maquette : il sert aux lots de front qui précèdent leur lot de back,
et aux tests du front qui ne font que lire. Il ne sert à rien qui écrive, puisqu'il ne garde
aucun état. En EP-03, le même outil, en mode proxy, contrôle les réponses du service réel
contre le contrat (WF-ARC-0060).

## US-0040 — Fixtures engendrées des exemples chiffrés du document

- **statut** : fini
- **exigences** : `WF-QUA-0020-A`
- **opérations** : aucune
- **issue** : #9
**En tant que** développeur, **je veux** un outil qui relève les exemples chiffrés des champs
Vérif et les écrit en fixtures, **afin que** les jeux de données du faux back et des tests
soient ceux du document, et non des nombres inventés pour la circonstance.

**Critères d'acceptation.**

- `WF-QUA-0020-A` — « Leur exécution complète ne demande ni base de données ni navigateur. »
- propre à l'US : l'outil lit les champs Vérif de la projection Markdown ; un exemple chiffré
  ajouté au document apparaît comme fixture non couverte, plutôt que de passer inaperçu ;
- propre à l'US : les fixtures alimentent le faux back de l'US-0030.
- écart : « Pour chacun des exemples chiffrés du document, un test porte les mêmes entrées et
  attend la même valeur. » et « La modification d'une constante de calcul fait échouer au
  moins un de ces tests. » ne se closent qu'avec les calculs — chaque EPIC de calcul reprend
  ses propres exemples (EP-06 à EP-11), et EP-11 constate les deux phrases sur l'ensemble.

## US-0050 — Lint, typage et format bloquants

- **statut** : fini
- **exigences** : `WF-QUA-0030-A`
- **opérations** : aucune
- **issue** : #10
**En tant que** développeur, **je veux** que le typage strict, le lint et le format soient
contrôlés par la chaîne et bloquants des deux côtés, **afin qu'**aucun
avertissement ne s'accumule jusqu'à ne plus rien signifier.

**Critères d'acceptation.**

- `WF-QUA-0030-A` — « Une modification introduisant une erreur de typage, une violation de
  règle d'analyse ou un écart de format fait échouer la chaîne. »
- `WF-QUA-0030-A` — « La chaîne n'émet aucun avertissement sur une version publiée. »
- `WF-QUA-0030-A` — « Le jeu de règles est lisible dans le dépôt et son historique montre
  chaque retrait. »
- propre à l'US : le lint porte aussi sur ce qui n'est pas du code applicatif et casse
  pourtant la chaîne ou l'installation — les workflows de GitHub Actions, les scripts shell,
  les Dockerfile —, bloquant comme le reste ;
- propre à l'US : la complexité cyclomatique de chaque fonction, back et front, tests
  compris, est inférieure à 15 ; une fonction qui atteint 15 fait échouer la chaîne en la
  nommant, avec sa valeur ;
- propre à l'US : aucun fichier source Python ou TypeScript, tests compris, ne dépasse
  1 000 lignes ; un fichier qui en compte 1 001 fait échouer la chaîne en le nommant, avec
  son nombre de lignes. Les fichiers engendrés, que déclare le fichier de l'US-0310, en sont
  exclus ;
- propre à l'US : aucune règle d'analyse, de typage ou de format ne s'écarte par un
  commentaire dans le code ; un tel commentaire fait échouer la chaîne. Une exception, s'il en
  faut une, s'écrit dans la configuration de l'outil, avec sa raison, là où le jeu de règles
  se lit et où son historique la montre ;
<!-- REUSE-IgnoreStart -->
- propre à l'US : chaque fichier source porte en tête deux lignes SPDX, le titulaire et la
  licence — `SPDX-FileCopyrightText: 2026 waterfall-project` et
  `SPDX-License-Identifier: AGPL-3.0-only` — ; les fichiers qui ne peuvent pas porter de
  commentaire, ou dont l'en-tête n'apporterait rien, sont déclarés dans le `REUSE.toml` du
  dépôt ; `reuse lint` fait échouer la chaîne sur un fichier qui n'est couvert ni par l'un ni
  par l'autre ;
<!-- REUSE-IgnoreEnd -->
- propre à l'US : chaque module, classe et fonction publics portent une docstring dont la
  première ligne résume ce qu'ils font ; ce qui est privé et les tests n'en demandent pas.
  Aucune section ne répète ce que la signature dit déjà — ni les types, ni la liste des
  paramètres ; une section ne s'écrit que pour une unité, un invariant ou un cas limite ;
- propre à l'US : aucun code commenté ne reste dans un fichier, et un `TODO` cite le
  numéro de l'issue qui le porte ; l'un et l'autre font échouer la chaîne.

**Notes de réalisation.** Le lint est ce que la spécification appelle analyse statique
(WF-QUA-0030) : Ruff et Pyright en mode strict pour le back, ESLint et Prettier pour le
front (annexe C) ; actionlint pour les workflows, shellcheck pour les scripts, hadolint pour
les Dockerfile. yamllint et markdownlint ne sont pas retenus : sur des fichiers écrits en
français, aux tableaux larges, ils produiraient surtout du bruit de mise en forme. Si l'un
d'eux sert un jour, ce sera sur une liste de fichiers déclarée, jamais sur tout le dépôt. Ce
qui n'est pas bloquant se retire du jeu de règles au lieu de rester en avertissement.

La complexité se mesure sans outil de plus : règle `C901` de Ruff, règle `complexity`
d'ESLint. Toutes deux signalent une valeur qui dépasse le maximum réglé : le maximum est donc
14, pour que 15 échoue. La taille des fichiers se compte en lignes physiques, blancs et
commentaires compris, la même mesure des deux côtés : la règle `max-lines` d'ESLint la
contrôle pour le front ; Ruff n'a pas d'équivalent, et le back demande un contrôle du dépôt,
qui lit la même liste de fichiers engendrés.

Les commentaires d'exemption visés sont ceux qui font taire un outil sur une ligne ou un
fichier — `# noqa`, `# type: ignore`, `# pyright: ignore`, `# fmt: off`,
`# pragma: no cover`, `eslint-disable`, `@ts-ignore`, `@ts-expect-error`,
`prettier-ignore`, `v8 ignore` ; les outils savent en partie les ignorer ou les refuser
d'eux-mêmes, et le reste se cherche. Si l'interdiction se révèle intenable, elle se retire
comme toute autre règle, et l'historique le montre.

Les deux lignes SPDX remplacent le bloc de licence que la GNU recommande en tête de chaque
fichier, une quinzaine de lignes que le code d'un petit module ne dépasserait pas. Le nom du
fichier n'y figure pas : il deviendrait faux au premier renommage, et rien ne le vérifierait ;
la première ligne de la docstring du module, qui dit à quoi il sert, en tient lieu.
`REUSE.toml` couvre en une fois la documentation, le document Word et les figures, et le code
engendré. Les docstrings se contrôlent par les règles `D1` de Ruff et par
`jsdoc/require-jsdoc` limitée aux exports ; `jsdoc/no-types` interdit de répéter en
commentaire un type que TypeScript porte déjà, et les règles qui exigeraient une section par
paramètre restent désactivées — c'est ce qui empêche les commentaires de dépasser le code.
Le code commenté se détecte par la règle `ERA001` de Ruff et les `TODO` par ses règles `TD` ;
ESLint n'a pas d'équivalent fiable, et le front demande un contrôle du dépôt. Ce qui ne se
vérifie pas — un commentaire dit pourquoi, non ce que fait le code ; il est en anglais,
comme le code — est au guide (US-0300).

## US-0060 — Couverture des exigences et du code par les tests

- **statut** : fini
- **exigences** : `WF-QUA-0010-A`
- **opérations** : aucune
- **issue** : #11
**En tant que** développeur, **je veux** que chaque test cite par identifiant l'exigence
qu'il couvre, que la chaîne en publie le relevé, et qu'elle mesure la part du code que les
tests exécutent, **afin qu'**une exigence F0 sans test, ou du code qu'aucun test n'exécute,
soit constaté par la chaîne et non découvert à la recette.

**Critères d'acceptation.**

- `WF-QUA-0010-A` — « Le rapport de couverture cite chacune des exigences F0 du document,
  avec les tests qui la couvrent. »
- `WF-QUA-0010-A` — « Le retrait d'un test fait apparaître son exigence parmi les non
  couvertes. »
- `WF-QUA-0010-A` — « Une tentative de publication avec une exigence F0 non couverte échoue
  en la nommant. »
- propre à l'US : la couverture de code se mesure en lignes et en branches, pour le back et
  pour le front, hors code engendré ; au-dessous de 90 % des lignes ou de 85 % des branches,
  d'un côté ou de l'autre, la fusion échoue en nommant les fichiers les moins couverts ;
  aucune ligne ne s'exclut de la mesure par un commentaire (US-0050).

**Notes de réalisation.** La liste des exigences se lit dans la projection Markdown, avec
leur champ de flexibilité : le rapport n'a pas de liste à tenir à jour de son côté. Il porte
sur les 195 exigences F0 ; les huit exigences F1 et F2 y figurent sans compter dans l'échec
(WF-QUA-0010). Tant qu'il n'y a pas de code métier, presque toutes sortent comme non
couvertes — seules le sont celles que les tests d'EP-01 citent —, c'est le résultat attendu,
et c'est ce qui décroît EPIC par EPIC. L'exemple du §1.3.1, `WF-EXAMP-0010-A`,
illustre la forme d'une exigence et n'en est pas une du produit : le rapport l'exclut, comme
le fait déjà `docs/api/tools/inventory.py`, faute de quoi il bloquerait toute publication.

La spécification ne demande que la couverture des exigences ; la couverture de code est une
règle du dépôt, qui trouve ce que la première ne voit pas — un chemin d'erreur jamais
exécuté, du code mort, de l'infrastructure qui ne relève d'aucune exigence. Les seuils
s'éprouvent au palier complet de l'US-0310, où tous les tests s'exécutent : les tests
d'intégration couvrent ce que les tests unitaires ne touchent pas, et un seuil vérifié sur les
seuls tests unitaires échouerait à tort. Le front demande un outil de tests unitaires et de
couverture que l'annexe C ne nomme pas encore — Vitest. Un seuil pousse à écrire des tests qui
passent sur les lignes sans rien vérifier : c'est un défaut à inscrire d'emblée dans les
règles de codage des deux langages (US-0300), que les agents de revue cherchent nommément.

## US-0070 — Couverture des exigences par la roadmap

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #12
**En tant que** développeur, **je veux** un outil qui confronte les US de `docs/roadmap` aux
exigences du document, **afin qu'**une exigence qu'aucun travail ne porte se voie avant
qu'on s'aperçoive, à la fin, qu'elle n'a jamais été prévue.

**Critères d'acceptation.**

- propre à l'US : l'outil liste les exigences F0 qu'aucune US ne cite, et les exceptions
  déclarées dans l'outil avec leur raison — comme le fait `tools/inventory.py` pour le
  contrat ;
- propre à l'US : une US qui cite un identifiant inexistant, ou un indice de révision périmé,
  fait échouer l'outil ;
- propre à l'US : une exigence citée dans le tableau d'un EPIC mais par aucune de ses US fait
  échouer l'outil, sauf dans un EPIC `à planifier`, dont les US ne sont pas encore écrites ;
- propre à l'US : pour chaque exigence qu'une US cite, chaque phrase de son Vérif figure mot
  pour mot dans l'US, en critère ou en écart ; une phrase absente ou tronquée fait échouer
  l'outil en nommant l'US, l'exigence et la phrase ;
- propre à l'US : une exigence close par aucun EPIC, ou par plus d'un, fait échouer l'outil ;
  l'exemple du §1.3.1, `WF-EXAMP-0010-A`, qui n'est pas une exigence du produit, en est
  exclu, comme dans `docs/api/tools/inventory.py` ;
- propre à l'US : `make roadmap` produit le relevé, et la chaîne l'exécute.

**Hors périmètre.** Aucun rapprochement avec les issues GitHub : l'outil ne lit que le
dépôt, et l'état des travaux n'est pas son affaire.

## US-0080 — Harnais de tests de bout en bout

- **statut** : fini
- **exigences** : `WF-QUA-0050-A`
- **opérations** : celles que le parcours témoin traverse
- **issue** : #13
**En tant que** développeur, **je veux** un harnais de bout en bout qui sache démarrer le
front contre le faux back et jouer un parcours, **afin que** les EPIC suivants aient où
écrire leurs parcours au lieu d'en inventer le cadre chacun.

**Critères d'acceptation.**

- propre à l'US : un parcours témoin — ouvrir la liste des projets, ouvrir un projet, lire
  une grille — aboutit contre le faux back, dans la chaîne comme sur un poste ;
- propre à l'US : l'échec du parcours fait échouer la chaîne ; le parcours s'exécute au
  palier complet de l'US-0310, au moment de fusionner, et non à chaque poussée.
- écart : « Chacun des sept flux et chacun des trois parcours fait l'objet d'un test de bout
  en bout qui aboutit. » attend EP-12, où les sept flux existent ;
- écart : « L'ensemble s'exécute sur une plateforme déployée à partir des images publiées de
  la version. » et « L'échec de l'un empêche la publication. » attendent EP-13, qui publie
  les images et la version. Ici, l'échec du parcours témoin fait échouer la chaîne, ce qui en
  est la première moitié.

## US-0280 — Agents de cadrage, de livraison, de développement et de revue

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #14
**En tant que** développeur, **je veux** des agents versionnés dans le dépôt — un agent de
cadrage qui mène un EPIC jusqu'à ses issues, un agent de livraison qui part de ces issues, et
pour chaque langage un agent qui réalise un lot et un agent qui le relit —, **afin que** les
règles de ce dépôt soient appliquées par construction à chaque travail, qu'un EPIC se cadre
pendant que le précédent se développe, et que ses lots avancent sans qu'une personne ait à
être présente à chaque fusion dans sa branche.

**Critères d'acceptation.**

- propre à l'US : six agents vivent dans `.claude/agents/` — l'agent de cadrage ; l'agent de
  livraison ; un agent de développement Python et un TypeScript ; un agent de revue Python et
  un TypeScript. Un lot qui touche les deux langages est confié aux deux agents de
  développement, chacun sur sa part, et relu par les deux agents de revue ;
- propre à l'US : les règles communes aux agents sont écrites une seule fois, dans un fichier
  que chacun lit ; aucun agent ne les recopie. Elles comprennent au moins : le fichier de
  l'EPIC fait foi et l'issue porte l'état ; les critères d'acceptation reprennent le Vérif
  mot pour mot ; chaque test cite l'exigence qu'il couvre (WF-QUA-0010) ; le contrat d'abord,
  et une opération qui manque est une modification du contrat qui précède ; aucun mock ni
  client écrit à la main ; les modules du noyau ne se lisent que par leur interface ; le
  code en anglais, la documentation en français ; un lot par pull request, vers la branche de
  son EPIC, estimé selon la taille visée au README de la roadmap ; un constat hors du
  périmètre d'un lot devient une issue et ne s'y corrige pas. Pour le reste, elles renvoient au guide
  et aux règles de codage de l'US-0300 ;
- propre à l'US : l'agent de cadrage mène les quatre premières étapes de la procédure
  « Démarrer un EPIC » du README de la roadmap : il détaille les US, écrit la conception,
  établit le plan de lots, et s'arrête pour validation après chacune de ces trois étapes ;
  puis il ouvre les issues — EPIC, US, et lots en sous-issues —, reporte les numéros dans le
  fichier, et prend les statuts parmi ceux du README et aucun autre. Il ne tire pas la
  branche de l'EPIC et n'écrit aucun code : ses modifications de la roadmap partent de
  `main`, sur une branche courte, et y reviennent par une pull request que fusionne une
  personne. Lancé à blanc sur EP-02, il rend la conception et le plan de lots qu'il
  proposerait, sans rien publier ;
- propre à l'US : l'agent de cadrage réunit le contexte avant de poser une question — le
  fichier de l'EPIC, les exigences citées et leur Vérif, le contrat et ses décisions, les EPIC
  voisins, le code de `main` et celui de la branche de l'EPIC en cours dont il dépend —, puis
  interroge l'utilisateur par petites séries de questions jusqu'à ce qu'il ne reste aucune
  ambiguïté. Une réponse qui contredit une décision déjà prise — dans la spécification, dans
  `docs/api/DECISIONS.md`, dans un EPIC livré ou en cours — est énoncée avec sa source et
  tranchée par l'utilisateur, jamais résolue en silence ;
- propre à l'US : l'agent de livraison prend en entrée les issues de lots d'un EPIC `en
  cours`, et lit dans le fichier de l'EPIC les critères et la conception auxquels elles
  renvoient. Il tire `epic/EP-nn` de `main` au premier lot, et refuse de le faire tant qu'un
  EPIC dont celui-ci dépend n'est pas livré. Une issue incomplète, ou qui contredit le fichier,
  l'arrête : il renvoie au cadrage au lieu de deviner ;
- propre à l'US : l'agent de livraison livre les lots dans l'ordre de leurs dépendances, sans
  attendre une personne entre deux lots. Pour chacun, il le confie à l'agent de développement
  de son langage, puis enchaîne revue locale, correction et nouvelle revue jusqu'à ce que la
  dernière revue ne rende plus aucun constat sur le périmètre du lot et que la chaîne passe ;
  alors seulement il fusionne la pull request dans la branche de l'EPIC, après y avoir
  inscrit la taille réelle du lot à côté de son estimation. Un constat hors du
  périmètre du lot n'est pas corrigé sur place : il devient une issue rattachée à l'EPIC. Au
  delà d'un plafond d'itérations fixé dans sa définition, le lot reste non fusionné, il est
  signalé bloqué avec son dernier constat, et l'agent passe au lot suivant qui n'en dépend
  pas ;
- propre à l'US : à la fin d'une série de lots, l'agent de livraison rend un relevé — lots
  fusionnés, avec leur taille réelle et leur estimation, et ceux qui la dépassent nettement
  mis en avant ; issues ouvertes pour des constats hors périmètre ; lots bloqués et ce qu'il
  reste à trancher ; durée des paliers de la chaîne ; état de la branche de l'EPIC. Quand toutes les US sont finies, il constate la
  définition de fini sur la branche de l'EPIC et demande sa fusion dans `main`, qu'une
  personne fait à la main ;
- propre à l'US : un agent de développement prend un lot par son issue, travaille sur une
  branche `lot/…` tirée de celle de son EPIC, applique les règles de codage de son langage,
  et ne rend son travail que lorsque le palier rapide du Makefile passe pour ce qu'il a
  touché. Il ne
  modifie ni la spécification, ni le contrat hors de ce que la conception prévoit, ni les
  critères d'acceptation ;
- propre à l'US : un agent de revue relit une pull request contre l'US qu'elle cite, les
  exigences et leur Vérif, le contrat, les règles communes et les règles de codage de son
  langage, dont il cherche nommément les défauts déjà rencontrés ; chaque constat porte un
  emplacement, le scénario qui le déclenche, une gravité et une proposition, et il ne modifie
  aucun fichier. Lancés sur une pull request piégée qui touche les deux langages — un test qui
  ne cite pas d'exigence, une réponse de mock écrite à la main, un critère d'acceptation
  reformulé, un module qui lit la table d'un autre —, les deux agents de revue relèvent à eux
  deux chacun des pièges ;
- propre à l'US : aucun agent ne fusionne dans `main`, ni ne pousse sur `main` ou sur une
  branche `epic/*` ; sur une branche d'EPIC, seul
  l'agent de livraison fusionne, et seulement la pull request d'un lot dont la revue locale
  et la chaîne sont au vert ;
- propre à l'US : chaque agent dit où il s'arrête et rend la main plutôt que de trancher —
  une exigence ambiguë devient une issue « Specification finding », un écart au contrat une
  issue « Interface contract issue » ;
- propre à l'US : chaque commande qu'un agent exécute existe dans le Makefile ; une cible
  renommée qui laisserait un agent appeler une commande disparue fait échouer
  `make roadmap`.

**Notes de réalisation.** Des agents de ce type existent déjà hors du dépôt — cadrage par
interview, orchestration d'un EPIC, livraison d'une série d'issues sans surveillance,
développement et revue par langage : ils sont repris et adaptés plutôt que réécrits. La
frontière entre cadrage et livraison est celle des issues : le premier les écrit, le second
les consomme, et c'est ce qui permet de cadrer l'EPIC suivant pendant que le précédent se
livre. Les conventions de code des agents existants partent dans les règles de codage de
l'US-0300, et leurs listes de défauts avec elles. La revue de la spécification
(`docs/spec/revue/PROMPT.md`) reste à part — elle relit le document, ceux-ci relisent du
code. Les commandes que les agents citent viennent des US-0050 à US-0070, et leurs règles du
guide de l'US-0300 : cette US se termine après elles, mais rien n'empêche de la commencer plus
tôt.

**Hors périmètre.** Le choix du modèle, le coût d'une exécution et la reprise après une
limite d'usage : ils se règlent dans la définition de chaque agent et changeront plus vite
que ce fichier.
