# Roadmap de Waterfall

## Principe

Les EPIC et les US vivent ici, en Markdown **écrit à la main**. Contrairement à la
spécification, aucun de ces fichiers n'est engendré : ils font foi tels quels.

Les issues GitHub ne sont ouvertes qu'au démarrage d'un EPIC, et le partage est le même
que partout ailleurs dans ce dépôt — un document fait foi, GitHub est une surface de
travail :

| Fait foi pour | Où |
|---|---|
| l'intention : périmètre, critères d'acceptation, exigences réalisées, opérations consommées | le fichier de l'EPIC |
| l'état : qui la prend, où elle en est, ce qui s'y discute | l'issue GitHub |

Une issue ne recopie donc pas les critères d'acceptation : elle renvoie au fichier et à
l'identifiant. Deux descriptions d'un même travail finissent toujours par diverger, et
c'est le fichier qu'on relira dans cinq ans.

**Les EPIC couvrent tout l'horizon ; les US ne sont détaillées qu'un EPIC à l'avance.**
Détailler aujourd'hui les US de la dernière tranche coûterait le prix de les réécrire :
ce que le premier incrément apprend change le découpage du suivant. Ce qui est fixé pour
tout l'horizon, ce sont les 203 exigences — pas leur découpage en travaux.

## Organisation

| Chemin | Contenu |
|---|---|
| `README.md` | ce fichier : les règles, et la liste ordonnée des EPIC |
| `MODELE.md` | la forme d'un EPIC et celle d'une US |
| `EP-nn-<intitulé>.md` | un EPIC, **ses US et sa conception comprises** |

Les US ne sont pas un fichier chacune : un EPIC est l'unité de travail — c'est lui qu'on
démarre, lui dont on ouvre les issues — et cinquante fichiers de vingt lignes se
reliraient moins bien que la douzaine de fichiers cohérents que voici. C'est la raison qui
groupe déjà les schémas du contrat par famille.

## Identifiants

Un EPIC porte `EP-nn`, une US porte `US-nnnn` au pas de dix. Comme les identifiants
d'exigence et les codes FBS et PBS, ils ne sont **jamais réutilisés et jamais
renumérotés** : une US insérée prend le prochain numéro libre, pas la place qu'elle occupe
dans la liste. Le titre d'une issue porte l'identifiant en tête — `[US-0130] …` — pour que
le lien se suive dans les deux sens.

## Traçabilité

Chaque US cite les exigences qu'elle réalise et les opérations du contrat qu'elle
consomme. Ses critères d'acceptation **reprennent le champ Vérif des exigences citées, mot
pour mot**, exemples chiffrés compris : ce sont eux qui deviendront les cas de test
(WF-QUA-0020), et un critère réécrit est un critère qui s'écarte de ce qui sera vérifié. Un
écart délibéré se note comme tel, avec sa raison.

Une exigence peut être réalisée par plusieurs EPIC : l'un la commence, un autre la finit,
parce que son Vérif cite ce qu'un EPIC ultérieur construit. Le tableau d'un EPIC le dit dans sa
colonne « Portée » — `entière`, `début — close en EP-nn` ou `fin — amorcée en EP-nn` —, et
chaque US dit laquelle de ses phrases de Vérif attend un autre EPIC. **Une exigence n'est close
que par un seul EPIC** : c'est lui qui la vérifie en entier.

Une exigence F0 que nulle US ne cite est soit un travail oublié, soit une exigence sans
surface — et dans ce cas la raison s'écrit. C'est la même mécanique que la couverture de
`make inventory` pour le contrat, et le pendant du rapport de couverture des exigences que
WF-QUA-0010 demande à la chaîne.

## Statuts

D'un EPIC, cinq valeurs et aucune autre :

| Statut | Signification |
|---|---|
| `à planifier` | l'EPIC est écrit, mais ses US ou sa conception ne sont pas arrêtées ; tant que ses US ne sont pas écrites, la colonne US de son tableau porte « — » |
| `prêt` | ses US sont détaillées et sa conception est validée ; rien n'empêche d'en découper les lots |
| `en cours` | son plan de lots est validé, et ses issues sont ouvertes sur GitHub ; sa branche d'intégration n'existe qu'à partir de son premier lot |
| `livré` | toutes ses US sont finies, sa définition de fini est vérifiée sur sa branche d'intégration, et celle-ci est fusionnée dans `main` |
| `abandonné : <pourquoi>` | reconnu, puis écarté ; le fichier reste |

D'une US, cinq également :

| Statut | Signification |
|---|---|
| `à faire` | état initial |
| `en cours` | prise par quelqu'un |
| `fini` | les critères d'acceptation sont vérifiés, et les tests qui les portent citent les exigences (WF-QUA-0010) |
| `reportée : <vers quel EPIC>` | sortie de cet EPIC, explicitement |
| `abandonnée : <pourquoi>` | le besoin ne tient plus |

Lire ce répertoire doit suffire à savoir où en est le projet, sans ouvrir GitHub.

## Ordre des EPIC

<!-- Un EPIC par ligne, dans l'ordre où ils se démarrent. -->

| EPIC | Titre | Statut | Dépend de |
|---|---|---|---|
| [EP-01](EP-01-socle-de-developpement.md) | Socle de développement | livré | rien |
| [EP-02](EP-02-maquette-du-front.md) | Maquette du front sur contrat simulé | prêt | EP-01 |
| [EP-03](EP-03-comptes-et-habilitations.md) | Comptes, authentification et habilitations | à planifier | EP-01 |
| [EP-05](EP-05-referentiel.md) | Référentiel de l'entreprise | à planifier | EP-03 |
| [EP-04](EP-04-projets-et-revisions.md) | Projets, révisions et cycle de vie | à planifier | EP-05 |
| [EP-06](EP-06-planification.md) | Planification | à planifier | EP-04 |
| [EP-07](EP-07-chiffrage-et-devis.md) | Chiffrage et devis | à planifier | EP-06 |
| [EP-09](EP-09-couts-reels-et-reste-a-engager.md) | Coûts réels, reste à engager et import des coûts | à planifier | EP-07 |
| [EP-08](EP-08-avenants-et-risques.md) | Avenants, risques et provisions | à planifier | EP-09 |
| [EP-10](EP-10-indicateurs.md) | Indicateurs de projet | à planifier | EP-08 |
| [EP-11](EP-11-portefeuille.md) | Portefeuille | à planifier | EP-10 |
| [EP-12](EP-12-echanges-de-fichiers.md) | Échanges de fichiers (FLX-01 à FLX-06) | à planifier | EP-09 |
| [EP-13](EP-13-exploitation.md) | Exploitation et mise en production | à planifier | EP-04 |

L'ordre de la liste n'est pas celui des numéros, et c'est voulu : un identifiant ne se
renumérote pas. La répartition des exigences a fait passer le référentiel avant les projets —
un projet ne se crée pas sans lui (WF-CYC-0120) —, l'import des coûts réels dans EP-09 — une
ligne de coût n'existe que par import (WF-CRE-0010) —, et les risques après le reste à
engager — la survenance se chiffre par lui, et fusionne comme un avenant.

EP-13 ne dépend que d'EP-04 : il peut commencer tôt, mais il clôt des exigences transverses
dont la dernière action arrive tard, et il finit en dernier.

Après EP-02, **un EPIC est une tranche verticale** : contrat, noyau, API, écran, tests.
Livrer « tout le back » puis « tout le front » ne donnerait rien à regarder avant la fin, et
c'est précisément ce que la maquette sur contrat simulé sert à éviter.

## Démarrer un EPIC

Cinq étapes, et un arrêt pour validation à la fin de chacune des trois premières : c'est ce
qui permet de confier le reste à un agent.

1. **Détailler les US**, jusqu'à ce que chacune porte des critères d'acceptation repris des
   champs Vérif. *Validation.*
2. **Écrire la conception** dans la section « Conception » du fichier de l'EPIC : les tables
   et les migrations, les modules du noyau touchés, les modifications du contrat, l'ordre de
   construction, et les décisions prises avec les options écartées. Une US dit ce qui doit
   être vrai ; la conception dit comment les pièces s'emboîtent, et sans elle chaque lot
   prendrait ses propres décisions de schéma. *Validation* ; l'EPIC passe `prêt`.
3. **Établir le plan de lots** : pour chaque lot, son périmètre, les critères d'acceptation
   qu'il ferme, les lots dont il dépend et sa taille estimée. *Validation.*
4. **Ouvrir les issues** : une issue pour l'EPIC, une par US, une par lot en sous-issue de
   son US ; reporter dans le fichier les numéros des issues de l'EPIC et des US. L'EPIC passe
   `en cours`.
5. **Livrer** : au premier lot, tirer `epic/EP-nn` de `main`, ce qui attend que les EPIC dont
   celui-ci dépend soient livrés ; livrer les lots ; quand toutes les US sont finies,
   constater la définition de fini sur la branche de l'EPIC, puis la fusionner dans `main` —
   une personne le fait, jamais un agent. L'EPIC passe `livré`.

Les quatre premières étapes ne demandent pas que les EPIC précédents soient livrés : un EPIC
se cadre pendant que celui dont il dépend se développe. Seule la cinquième les attend.

Une proposition de fonctionnalité n'est pas une US : elle passe par le gabarit d'issue
« Question or proposal », et ne devient une US que lorsqu'elle entre dans un EPIC.

## Lots

Un lot est l'unité de revue : **un lot, une issue, une branche, une pull request**. Une US
tient en un lot ou en plusieurs ; un lot qui ne ferme aucun critère d'acceptation se déclare
lot technique et nomme les US qu'il prépare.

| Règle | Pourquoi |
|---|---|
| le plan de lots vise 1 000 à 1 500 lignes de diff par lot, tests compris, dont 800 de code de production au plus | au-delà, une revue attentive décroche |
| le code engendré n'est pas compté : client du contrat, verrous de dépendances, fixtures extraites, migrations produites par l'outil | un lot qui régénère le client paraîtrait gros sans rien contenir à relire |
| la pull request met chaque critère fermé en regard du test qui le porte | c'est ce que la revue vérifie en premier |
| un lot se fusionne seul, la chaîne au vert | la branche de l'EPIC n'est jamais à moitié construite |
| un constat de revue hors du périmètre du lot devient une issue, et ne se corrige pas dans le lot | c'est ce qui fait grossir un lot pendant sa revue, et tourner la revue en boucle |
| la pull request donne la taille réelle du lot, mesurée par `make lot-size`, à côté de l'estimation de son issue ; un dépassement ne fait rien échouer | l'estimation se trompe, et une règle d'arrêt bloquerait un EPIC livré la nuit ; l'écart se lit au relevé de livraison, et le plan de lots suivant s'en corrige |

Ce tableau est la seule définition de la taille visée : le gabarit de pull request, celui
des lots et les agents y renvoient, et aucun ne la recopie.

Un lot porte le titre `[US-nnnn/Ln] …` ou, pour un lot technique, `[EP-nn/Ln] …` ; `Ln`
numérote les lots d'une même US ou d'un même EPIC, sans réemploi. Les lots vivent sur GitHub
et nulle part ailleurs : ils sont une façon de faire le travail, pas son intention, et le
fichier de l'EPIC ne les recopie pas.

## Branches

| Branche | Reçoit | Tirée de |
|---|---|---|
| `main` | la fusion d'une branche d'EPIC à sa livraison, et les modifications de la spécification, du contrat ou de la roadmap qui ne servent aucun EPIC en cours | — |
| `epic/EP-nn` | les pull requests des lots de cet EPIC, et les modifications du contrat que sa conception prévoit | `main`, au premier lot, une fois livrés les EPIC dont il dépend |
| `lot/<identifiant du lot>` | le travail d'un lot, et lui seul | la branche de son EPIC |

Un EPIC en cours a sa branche d'intégration dès son premier lot — entre l'ouverture de ses
issues et ce premier lot, il n'en a pas encore, et c'est normal : il peut attendre qu'un
EPIC dont il dépend soit livré. Plusieurs EPIC peuvent ainsi avancer en même temps sans que
la livraison de l'un emporte les lots à moitié faits d'un autre. `main` ne reçoit donc que
des EPIC livrés et des documents relus : elle n'est jamais dans un état intermédiaire. Après
chaque fusion dans `main`, les branches des EPIC encore en cours la reprennent, et c'est à
ce moment que se règlent leurs conflits, non à la livraison.

La chaîne s'exécute sur toute pull request, vers une branche d'EPIC comme vers `main`, et
aucune n'est fusionnée si elle échoue.
