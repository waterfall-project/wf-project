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
| `EP-nn-<intitulé>.md` | un EPIC, **ses US comprises** |

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

Une exigence F0 que nulle US ne cite est soit un travail oublié, soit une exigence sans
surface — et dans ce cas la raison s'écrit. C'est la même mécanique que la couverture de
`make inventory` pour le contrat, et le pendant du rapport de couverture des exigences que
WF-QUA-0010 demande à la chaîne.

## Statuts

D'un EPIC, cinq valeurs et aucune autre :

| Statut | Signification |
|---|---|
| `à planifier` | l'EPIC est écrit, ses US ne sont pas détaillées |
| `prêt` | ses US sont détaillées, rien n'empêche de l'ouvrir |
| `en cours` | ses issues sont ouvertes sur GitHub |
| `livré` | toutes ses US sont finies et sa définition de fini est vérifiée |
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
| [EP-01](EP-01-socle-de-developpement.md) | Socle de développement | prêt | rien |
| [EP-02](EP-02-maquette-du-front.md) | Maquette du front sur contrat simulé | prêt | EP-01 |
| EP-03 | Comptes, authentification et habilitations | à écrire | EP-01 |
| EP-04 | Projets, révisions et cycle de vie | à écrire | EP-03 |
| EP-05 | Référentiel de l'entreprise | à écrire | EP-04 |
| EP-06 | Planification | à écrire | EP-04, EP-05 |
| EP-07 | Chiffrage et devis | à écrire | EP-04, EP-05 |
| EP-08 | Risques et provisions | à écrire | EP-07 |
| EP-09 | Coûts réels et reste à engager | à écrire | EP-07 |
| EP-10 | Indicateurs de projet | à écrire | EP-06, EP-07, EP-08, EP-09 |
| EP-11 | Portefeuille | à écrire | EP-10 |
| EP-12 | Échanges de fichiers (FLX-01 à FLX-07) | à écrire | EP-06, EP-07, EP-09 |
| EP-13 | Exploitation et mise en production | à écrire | EP-04 |

`à écrire` n'est pas un statut d'EPIC : c'est l'absence de fichier. Le périmètre de ces onze
EPIC est arrêté — leur rang et les domaines d'exigences qu'ils portent — mais leur objet,
leurs exigences et leur définition de fini restent à rédiger.

Après EP-02, **un EPIC est une tranche verticale** : contrat, noyau, API, écran, tests.
Livrer « tout le back » puis « tout le front » ne donnerait rien à regarder avant la fin, et
c'est précisément ce que la maquette sur contrat simulé sert à éviter.

## Démarrer un EPIC

1. détailler ses US, jusqu'à ce que chacune porte des critères d'acceptation repris des
   champs Vérif ; l'EPIC passe `prêt` ;
2. ouvrir une issue pour l'EPIC, puis une par US, avec l'identifiant en tête du titre ;
3. reporter les numéros d'issue dans le fichier, en regard de chaque identifiant ;
4. l'EPIC passe `en cours`.

Une proposition de fonctionnalité n'est pas une US : elle passe par le gabarit d'issue
« Question or proposal », et ne devient une US que lorsqu'elle entre dans un EPIC.
