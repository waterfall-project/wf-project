---
id: EP-01
titre: Rendre le dépôt capable de porter du code, sans en écrire une ligne de métier
statut: prêt
depend_de: rien
issue:
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

## Ce qui en fait partie

- la structure du dépôt : front (PBS-1), service d'API et worker (PBS-2.1, PBS-2.2), noyau
  métier (PBS-2.3), et le contrôle qui interdit à un module du noyau de lire les tables d'un
  autre ;
- le client TypeScript engendré du contrat (PBS-1.2), régénéré par une commande, jamais
  retouché à la main ;
- un faux back servi par prism depuis le bundle du contrat, et le fichier Compose qui le
  démarre avec le front ;
- l'outil qui extrait les exemples chiffrés des champs Vérif et les écrit en fixtures ;
- l'analyse statique, le contrôle de typage et le contrôle de format, front et back,
  bloquants et sans avertissement toléré ;
- le rapport de couverture des exigences par les tests, et le refus de publier tant qu'une
  exigence F0 n'est couverte par aucun test ;
- l'outil de couverture de la roadmap : quelle exigence n'est citée par aucune US ;
- le harnais de tests de bout en bout, avec un parcours témoin contre le faux back ;
- les agents qui développent, qui relisent et qui mènent un EPIC de bout en bout, et les
  règles communes qu'ils lisent tous.

## Ce qui n'en fait pas partie

- toute règle métier, tout calcul, toute table : il n'y a pas encore de base — EP-04 ;
- les écrans — EP-02 ; seul le parcours témoin du harnais touche le front ;
- le jeu de données de référence de WF-QUA-0040, qui demande le modèle : il naît en EP-04 et
  grossit avec chaque EPIC ;
- les sept flux de bout en bout de WF-QUA-0050 — EP-12 ;
- les tests de charge de WF-QUA-0060, les images publiées, le chart Helm — EP-13 ;
- le contrôle de complétude des catalogues de traduction (WF-QUA-0070), qui attend qu'il y
  ait des catalogues — EP-02.

## Exigences réalisées

| Exigence | Titre | US |
|---|---|---|
| `WF-ARC-0010-A` | Un noyau, un service, un worker | US-0010 |
| `WF-ARC-0060-A` | Contrat OpenAPI | US-0020 |
| `WF-QUA-0010-A` | Traçabilité des exigences par les tests | US-0060 |
| `WF-QUA-0020-A` | Les exemples chiffrés du document sont des cas de test | US-0040 |
| `WF-QUA-0030-A` | Typage et analyse statique bloquants | US-0050 |
| `WF-QUA-0050-A` | Tests de bout en bout | US-0080 |

Quatre de ces six ne sont réalisées qu'en partie, et chaque US dit laquelle de ses phrases
de Vérif attend un autre EPIC : il n'y a ici ni règle métier à tester (WF-ARC-0010,
WF-QUA-0020), ni service dont on puisse comparer les réponses au schéma (WF-ARC-0060), ni
plateforme complète à parcourir (WF-QUA-0050). Seules WF-QUA-0010 et WF-QUA-0030 sont closes
par cet EPIC.

## Opérations du contrat

Aucune n'est servie ni consommée : le faux back sert le contrat entier tel qu'il est, sans
en choisir. `make build-openapi` produit le bundle dont prism part.

## Préalables

Rien. Le contrat est écrit et `make lint-openapi` passe.

## Définition de fini

- une commande régénère le client du contrat, et le dépôt est inchangé après ;
- `make mock` sert le faux back, et le front démarre contre lui par le Compose de
  développement ;
- une faute de typage, une violation de règle d'analyse et un écart de format introduits
  exprès font chacun échouer la chaîne ;
- le rapport de couverture des exigences liste les 203 exigences et celles que nul test ne
  couvre ;
- l'outil de la roadmap liste les exigences qu'aucune US ne cite ;
- le parcours témoin de bout en bout aboutit contre le faux back ;
- la chaîne exécute tout ce qui précède sur une pull request, et échoue sur chacun de ces
  points ;
- l'agent de revue, lancé sur une pull request piégée, relève chacun des pièges ; l'agent
  d'EPIC, lancé à blanc sur EP-02, rend les issues qu'il ouvrirait et l'ordre des US sans
  rien publier. Ces deux essais se jouent à la main : la chaîne n'exécute
  pas d'agent.

---

## US-0010 — Structure du dépôt et frontières du noyau

- **statut** : à faire
- **exigences** : `WF-ARC-0010-A`
- **opérations** : aucune
- **issue** :

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
  planning, de chiffrage et d'indicateurs » ne se vérifie qu'à partir d'EP-04 — il n'y a
  encore aucun calcul.

**Notes de réalisation.** Le contrôle des frontières est une règle d'analyse statique, donc
bloquante au même titre que le reste (WF-QUA-0030) : les modules du noyau ne s'importent
entre eux que par leur interface publique.

## US-0020 — Client d'API engendré du contrat

- **statut** : à faire
- **exigences** : `WF-ARC-0060-A`
- **opérations** : toutes, par engendrement
- **issue** :

**En tant que** développeur, **je veux** que le client TypeScript du front soit engendré du
contrat par une commande, **afin qu'**aucun écart entre le contrat et ce que le front appelle
ne puisse s'installer.

**Critères d'acceptation.**

- `WF-ARC-0060-A` — « Le client du front est régénéré à partir du contrat sans retouche à la
  main. »
- propre à l'US : la régénération est une commande du Makefile, et la chaîne échoue si le
  client versionné diffère de celui que le contrat produit.
- écart : « Une réponse de l'API qui ne correspond pas au schéma déclaré fait échouer la
  chaîne » et « Aucun endpoint ne répond qui ne figure au contrat » attendent un service
  réel — EP-03.

## US-0030 — Faux back tiré du contrat

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : toutes, servies par prism depuis le bundle
- **issue** :

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

## US-0040 — Fixtures engendrées des exemples chiffrés du document

- **statut** : à faire
- **exigences** : `WF-QUA-0020-A`
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** un outil qui relève les exemples chiffrés des champs
Vérif et les écrit en fixtures, **afin que** les jeux de données du faux back et des tests
soient ceux du document, et non des nombres inventés pour la circonstance.

**Critères d'acceptation.**

- `WF-QUA-0020-A` — « Leur exécution complète ne demande ni base de données ni navigateur. »
- propre à l'US : l'outil lit les champs Vérif de la projection Markdown ; un exemple chiffré
  ajouté au document apparaît comme fixture non couverte, plutôt que de passer inaperçu ;
- propre à l'US : les fixtures alimentent le faux back de l'US-0030.
- écart : « Pour chacun des exemples chiffrés du document, un test porte les mêmes entrées et
  attend la même valeur » ne se clôt qu'avec les calculs — chaque EPIC de calcul reprend ses
  propres exemples (EP-06 à EP-11).

## US-0050 — Analyse statique, typage et format bloquants

- **statut** : à faire
- **exigences** : `WF-QUA-0030-A`
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** que le typage strict, l'analyse statique et le
format soient contrôlés par la chaîne et bloquants des deux côtés, **afin qu'**aucun
avertissement ne s'accumule jusqu'à ne plus rien signifier.

**Critères d'acceptation.**

- `WF-QUA-0030-A` — « Une modification introduisant une erreur de typage, une violation de
  règle d'analyse ou un écart de format fait échouer la chaîne. »
- `WF-QUA-0030-A` — « La chaîne n'émet aucun avertissement sur une version publiée. »
- `WF-QUA-0030-A` — « Le jeu de règles est lisible dans le dépôt et son historique montre
  chaque retrait. »

**Notes de réalisation.** Ruff et Pyright en mode strict pour le back, ESLint et Prettier
pour le front (annexe C). Ce qui n'est pas bloquant se retire du jeu de règles au lieu de
rester en avertissement.

## US-0060 — Rapport de couverture des exigences par les tests

- **statut** : à faire
- **exigences** : `WF-QUA-0010-A`
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** que chaque test cite par identifiant l'exigence
qu'il couvre et que la chaîne en publie le relevé, **afin qu'**une exigence F0 sans test soit
constatée par la chaîne et non découverte à la recette.

**Critères d'acceptation.**

- `WF-QUA-0010-A` — « Le rapport de couverture cite chacune des exigences F0 du document,
  avec les tests qui la couvrent. »
- `WF-QUA-0010-A` — « Le retrait d'un test fait apparaître son exigence parmi les non
  couvertes. »
- `WF-QUA-0010-A` — « Une tentative de publication avec une exigence F0 non couverte échoue
  en la nommant. »

**Notes de réalisation.** La liste des exigences se lit dans la projection Markdown, avec
leur champ de flexibilité : le rapport n'a pas de liste à tenir à jour de son côté. Tant
qu'il n'y a pas de code métier, les 203 sortent comme non couvertes — c'est le résultat
attendu, et c'est ce qui décroît EPIC par EPIC.

## US-0070 — Couverture des exigences par la roadmap

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** :

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
  échouer l'outil ;
- propre à l'US : `make roadmap` produit le relevé, et la chaîne l'exécute.

**Hors périmètre.** Aucun rapprochement avec les issues GitHub : l'outil ne lit que le
dépôt, et l'état des travaux n'est pas son affaire.

## US-0080 — Harnais de tests de bout en bout

- **statut** : à faire
- **exigences** : `WF-QUA-0050-A`
- **opérations** : celles que le parcours témoin traverse
- **issue** :

**En tant que** développeur, **je veux** un harnais de bout en bout qui sache démarrer le
front contre le faux back et jouer un parcours, **afin que** les EPIC suivants aient où
écrire leurs parcours au lieu d'en inventer le cadre chacun.

**Critères d'acceptation.**

- propre à l'US : un parcours témoin — ouvrir la liste des projets, ouvrir un projet, lire
  une grille — aboutit contre le faux back, dans la chaîne comme sur un poste ;
- propre à l'US : l'échec du parcours fait échouer la chaîne.
- écart : « s'exécutent contre une plateforme complète déployée par Compose (WF-ARC-0050),
  sur le jeu de données de référence » attend EP-13, et la couverture des sept flux FLX-01 à
  FLX-07 et des trois parcours d'acteurs attend EP-12.

## US-0090 — Agents de développement, de revue et de conduite d'un EPIC

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** trois agents versionnés dans le dépôt — un qui
réalise une US, un qui relit une pull request, un qui mène un EPIC `prêt` jusqu'à `livré` en
confiant chaque US au premier et chaque pull request au second —, **afin que** les règles de
ce dépôt soient appliquées par construction à chaque travail, et non redécouvertes à chaque
conversation.

**Critères d'acceptation.**

- propre à l'US : les règles communes aux trois agents sont écrites une seule fois, dans un
  fichier que chacun lit ; aucun agent ne les recopie. Elles comprennent au moins : le
  fichier de l'EPIC fait foi et l'issue porte l'état ; les critères d'acceptation reprennent
  le Vérif mot pour mot ; chaque test cite l'exigence qu'il couvre (WF-QUA-0010) ; le
  contrat d'abord, et une opération qui manque est une modification du contrat qui précède ;
  aucun mock ni client écrit à la main ; les modules du noyau ne se lisent que par leur
  interface ; le code en anglais, la documentation en français ;
- propre à l'US : l'agent de développement prend une US par son identifiant, travaille sur
  une branche qui le porte, et ne rend la main que lorsque les commandes de contrôle du
  Makefile passent ; il ne modifie ni la spécification, ni le contrat hors de ce que l'US
  prévoit, ni les critères d'acceptation ;
- propre à l'US : l'agent de revue relit une pull request contre l'US qu'elle cite, les
  exigences et leur Vérif, le contrat et les règles communes ; chaque constat porte un
  emplacement et une proposition, et il ne modifie aucun fichier. Lancé sur une pull request
  piégée — un test qui ne cite pas d'exigence, une réponse de mock écrite à la main, un
  critère d'acceptation reformulé, un module qui lit la table d'un autre —, il relève
  chacun des pièges ;
- propre à l'US : l'agent d'EPIC suit la procédure « Démarrer un EPIC » du README de la
  roadmap : issues au titre `[US-nnnn]`, numéros reportés dans le fichier, statuts pris
  parmi ceux du README et aucun autre, et la définition de fini constatée avant `livré`.
  Lancé à blanc sur EP-02, il rend les issues qu'il ouvrirait et l'ordre des US, sans rien
  publier ;
- propre à l'US : chaque agent dit où il s'arrête et rend la main plutôt que de trancher —
  une exigence ambiguë devient une issue « Specification finding », un écart au contrat une
  issue « Contract issue » ; aucun agent ne fusionne une pull request ni ne pousse sur
  `main` ;
- propre à l'US : chaque commande qu'un agent exécute existe dans le Makefile ; une cible
  renommée qui laisserait un agent appeler une commande disparue fait échouer
  `make roadmap`.

**Notes de réalisation.** Les agents vivent dans `.claude/agents/`. Des agents de ce type
existent déjà hors du dépôt : ils sont repris et adaptés plutôt que réécrits. La revue de la
spécification (`docs/spec/revue/PROMPT.md`) reste à part — elle relit le document, celui-ci
relit du code. Les commandes que les agents citent viennent des US-0050 à US-0070 : cette
US se termine après elles, mais rien n'empêche de la commencer plus tôt.

**Hors périmètre.** Le choix du modèle et le coût d'une exécution : ils se règlent dans
la définition de chaque agent et changeront plus vite que ce fichier.
