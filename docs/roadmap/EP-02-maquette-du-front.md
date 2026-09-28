---
id: EP-02
titre: Tous les écrans, navigables, alimentés par le faux back, avant toute règle métier
statut: à planifier
depend_de: EP-01
issue:
---

# EP-02 — Maquette du front sur contrat simulé

## Objet

Construire l'application web entière contre le faux back d'EP-01 : la navigation, les
composants d'interface de PBS-1.3, les onze exigences du §3.6, les deux langues, et un écran
par fonction. Rien n'est calculé par le front — c'est le mock qui répond.

La maquette a deux résultats, et le second est le plus précieux. Elle donne des écrans ; elle
donne surtout la liste de ce que le contrat a mal prévu. Un champ qu'aucun écran ne sait
afficher, une vue qui demanderait deux appels et une jointure dans le front (interdite par
WF-ARC-0020), un état qu'on ne peut pas distinguer : chacun de ces constats coûte une
modification du contrat aujourd'hui, et une migration de base dans deux ans.

## Ce qui en fait partie

- les dépendances d'affichage de l'annexe C — Tailwind CSS, shadcn/ui, les icônes Lucide,
  TanStack Table, Apache ECharts —, installées avec le premier écran qui s'en sert ;
- la coquille : navigation, projet ouvert qui le reste d'un écran à l'autre, bandeau de
  contexte de lecture ;
- la grille dense — le composant qui porte le planning, le devis, le reste à engager et les
  risques : lecture, tri, colonnes, saisie au clavier seul, collage depuis un tableur,
  annulation et rétablissement ;
- la distinction visuelle entre valeur calculée et valeur saisie ;
- l'échelle de signalement commune, lisible sans couleur ;
- le suivi des traitements longs, les commandes indisponibles et les refus ;
- l'accessibilité minimale : clavier, contraste AA, libellés, agrandissement à 150 % ;
- les deux langues, les catalogues, et le contrôle de complétude par la chaîne ;
- un écran par fonction de l'arborescence FBS, en lecture, alimenté par le mock ;
- la preuve que le front n'appelle l'API que par le client engendré.

## Ce qui n'en fait pas partie

- toute règle et tout calcul : le mock les rend, le front les affiche. Un écran qui aurait
  besoin de calculer est un endpoint qui manque au contrat, donc un constat, pas du code ;
- le comportement réel des écrans, qui arrive avec l'EPIC de leur domaine : ici, une commande
  aboutit parce que le mock répond, pas parce qu'une règle a été évaluée ;
- l'authentification réelle — EP-03 : la maquette part d'une session que le mock accorde ;
- les imports et exports réels — EP-09 pour les coûts réels, EP-12 pour les autres flux :
  l'écran d'import en deux temps est maquetté, le traitement ne l'est pas ;
- le diagramme de Gantt et l'arborescence de tâches sont rendus en lecture seule, ce qui est
  définitif et non un provisoire de maquette.

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-ARC-0020-A` | Le contrat est le seul contrat | entière | US-0270 |
| `WF-IHM-0010-A` | Navigation et contexte du projet | entière | US-0090 |
| `WF-IHM-0020-A` | Contexte de lecture affiché | entière | US-0100 |
| `WF-IHM-0030-A` | Valeur calculée et valeur saisie | entière | US-0150 |
| `WF-IHM-0040-A` | Saisie au clavier dans les grilles | entière | US-0120 |
| `WF-IHM-0050-A` | Collage depuis un tableur | entière | US-0130 |
| `WF-IHM-0060-A` | Lecture d'une grille | entière | US-0110 |
| `WF-IHM-0070-A` | Une échelle de signalement commune, lisible sans couleur | entière | US-0160 |
| `WF-IHM-0080-A` | Traitements longs | entière | US-0180 |
| `WF-IHM-0090-A` | Refus et commandes indisponibles | entière | US-0170 |
| `WF-IHM-0100-A` | Accessibilité minimale | entière | US-0200 |
| `WF-IHM-0110-A` | Annulation et rétablissement des saisies | début — close en EP-06 | US-0140 |
| `WF-INTF-0160-A` | Choix de la langue de l'interface | début — close en EP-03 | US-0190 |
| `WF-INTF-0170-A` | Ce qui est traduit et ce qui ne l'est pas | entière | US-0190 |
| `WF-INTF-0180-A` | Formats indépendants de la langue | début — close en EP-12 | US-0190 |
| `WF-ADM-0040-A` | Préférences d'affichage | début — close en EP-03 | US-0110, US-0190 |
| `WF-QUA-0070-A` | Complétude des traductions | entière | US-0190 |
| `WF-CMP-0010-A` | Navigateurs et affichage | entière | US-0290 |

Dix des onze exigences du §3.6 sont closes par cet EPIC : elles portent sur l'interface, et
l'interface existe ici pour de bon. Quatre exigences ne le sont qu'en partie, et leurs US le
disent : WF-IHM-0110 (l'annulation porte sur des saisies que le mock accepte sans les
conserver ; close en EP-06, première grille dont les saisies le sont), WF-ADM-0040 et
WF-INTF-0160 (la conservation des préférences et de la langue dans le compte attend EP-03),
et WF-INTF-0180 (le format des fichiers d'échange attend EP-12 ; seul l'affichage est ici).

## Opérations du contrat

Toutes celles que les écrans lisent, servies par le faux back. Les familles, avec l'US qui
les consomme : `session` et `system` (US-0090), `projects` et `revisions` (US-0210),
`revisions` pour le planning et le devis (US-0220), `risks`, `costs` et la partie « reste à
engager » d'`analysis` (US-0230), `analysis` et `portfolio` (US-0240), `reference` et
`access` (US-0250), `exchanges` (US-0260).

Une opération qui manque se note dans cet EPIC et se corrige dans `docs/api` : c'est une
modification du contrat, donc un travail qui précède l'écran qui l'attend.

## Préalables

EP-01 livré : le client engendré, le faux back, les fixtures et le harnais de bout en bout.

## Définition de fini

- chaque fonction de l'arborescence FBS a son écran, atteignable depuis la navigation ;
- les onze exigences du §3.6 ont chacune au moins un test de bout en bout qui les cite ;
- un contrôle automatisé de contraste ne relève aucun écart au niveau AA ;
- le parcours de bout en bout s'exécute et aboutit en français comme en anglais ;
- la chaîne échoue sur un appel http au serveur hors du client engendré, sur un texte
  destiné à l'utilisateur écrit en dur, et sur une clé de traduction manquante ou orpheline ;
- les constats faits sur le contrat sont écrits — soit appliqués dans `docs/api`, soit ouverts
  en issue « Interface contract issue » — et aucun n'est resté dans une tête.

---

## US-0090 — Coquille de l'application et contexte de projet

- **statut** : à faire
- **exigences** : `WF-IHM-0010-A`
- **opérations** : `getCurrentSession`, `getMe`, `listProjects`, `getProject`, `getSystemStatus`
- **issue** :

**En tant que** chef de projet, **je veux** que le projet que j'ai ouvert le reste d'un écran
à l'autre, et que les fonctions hors projet restent atteignables sans en ouvrir un,
**afin de** ne pas repasser par une liste à chaque changement de sujet.

**Critères d'acceptation.**

- `WF-IHM-0010-A` — « Un utilisateur qui n'a ouvert aucun projet atteint le portefeuille, le
  référentiel, l'administration et l'écran d'état. »
- `WF-IHM-0010-A` — « Dans un projet, le passage du reste à engager aux risques puis aux
  indicateurs conserve la révision affichée et le sous-projet filtré. »
- `WF-IHM-0010-A` — « Le retour au projet précédent depuis une fonction hors projet retrouve
  le même contexte. »

**Notes de réalisation.** Le contexte de lecture — projet, révision, sous-projet filtré, date
de calcul — est l'état que porte la coquille, et tout écran le lit. C'est lui que le bandeau
de l'US-0100 affiche et que les filtres des grilles restreignent : le décider ici évite que
chaque écran s'invente le sien.

## US-0100 — Bandeau de contexte de lecture

- **statut** : à faire
- **exigences** : `WF-IHM-0020-A`
- **opérations** : `getRevision`, `listRevisions`
- **issue** :

**En tant que** chef de projet, **je veux** lire sur chaque écran dans quelle révision je
suis, si elle est marquée, si elle est la référence, et ce qu'un filtre actif restreint,
**afin de** ne jamais prendre une valeur d'une révision pour celle d'une autre.

**Critères d'acceptation.**

- `WF-IHM-0020-A` — « Chaque écran de données de projet nomme le projet et la révision
  affichée. »
- `WF-IHM-0020-A` — « L'ouverture d'une révision marquée présente cet état et ne propose
  aucune commande de modification. »
- `WF-IHM-0020-A` — « Un indicateur affiché porte sa date de calcul. »
- `WF-IHM-0020-A` — « Un filtre actif est visible sans avoir à ouvrir le panneau de
  filtres. »

## US-0110 — Grille dense : lecture, tri, colonnes et préférences

- **statut** : à faire
- **exigences** : `WF-IHM-0060-A`, `WF-ADM-0040-A`
- **opérations** : `listNodes`, `updateMyPreferences`
- **issue** :

**En tant que** chef de projet, **je veux** une grille qui se trie, se filtre, dont je choisis
les colonnes et leur largeur, et qui garde mes en-têtes et mes totaux sous les yeux quand je
défile, **afin de** travailler sur mille tâches sans perdre le fil de ce que je lis.

**Critères d'acceptation.**

- `WF-IHM-0060-A` — « Chaque colonne d'une grille se trie dans les deux sens. »
- `WF-IHM-0060-A` — « Après défilement de mille lignes, en-têtes et totaux sont toujours
  visibles, de même que la colonne de libellé après défilement horizontal. »
- `WF-IHM-0060-A` — « Les colonnes masquées et les largeurs choisies sont retrouvées à la
  réouverture, et un autre utilisateur ouvrant la même grille voit ses propres réglages. »
- propre à l'US : l'ouverture d'une grille de mille tâches tient l'objectif d'une seconde du
  §4.6.2, mesuré contre le faux back.

**Notes de réalisation.** Composant propre fondé sur TanStack Table (annexe C). C'est le
composant le plus réutilisé de l'application — planning, devis, reste à engager, risques,
coûts réels — et les US-0120 à US-0150 en sont la suite. Les réglages sont une préférence
d'affichage (WF-ADM-0040), donc personnels et sans effet sur les données.

- écart : la conservation des préférences dans le compte passe par `updateMyPreferences`, que
  le mock accepte sans rien garder ; elle n'est vraie qu'en EP-03.
- écart : `WF-ADM-0040-A` — « Deux utilisateurs ouvrant le même projet voient les mêmes
  données présentées selon leurs réglages respectifs. » demande deux comptes réels — EP-03.
- écart : `WF-ADM-0040-A` — « Un utilisateur modifie ses préférences et ne peut pas modifier
  celles d'un autre. » est l'affaire de l'US-0190, et demande des comptes réels — EP-03.

## US-0120 — Grille dense : saisie au clavier seul

- **statut** : à faire
- **exigences** : `WF-IHM-0040-A`
- **opérations** : `updateEstimateLine`, `updateTaskFacet`
- **issue** :

**En tant que** chef de projet, **je veux** saisir une ligne entière sans toucher la souris,
**afin de** chiffrer plusieurs centaines de lignes à la vitesse à laquelle je les lis.

**Critères d'acceptation.**

- `WF-IHM-0040-A` — « Une ligne de devis complète — libellé, catégorie, rôle, quantité,
  charge — se saisit sans toucher la souris, et la validation de la dernière cellule place le
  curseur sur la ligne suivante. »
- `WF-IHM-0040-A` — « L'abandon d'une saisie en cours laisse la cellule à sa valeur
  antérieure. »
- `WF-IHM-0040-A` — « Les cellules calculées sont traversées sans entrer en saisie. »
- propre à l'US : le recalcul qui suit une saisie tient l'objectif d'une seconde du §4.6.2.

## US-0130 — Grille dense : collage depuis un tableur

- **statut** : à faire
- **exigences** : `WF-IHM-0050-A`
- **opérations** : `previewPaste`, `applyPaste`
- **issue** :

**En tant que** chef de projet, **je veux** coller un bloc de cellules venu d'un tableur et
voir ce qui sera écrit et ce qui sera refusé avant que quoi que ce soit ne change, **afin de**
reprendre un chiffrage préparé ailleurs sans le ressaisir et sans risquer d'abîmer le devis.

**Critères d'acceptation.**

- `WF-IHM-0050-A` — « Un bloc de trois lignes et quatre colonnes collé depuis un tableur
  produit un compte rendu avant écriture, puis les trois lignes attendues après
  confirmation. »
- `WF-IHM-0050-A` — « Un bloc dont une cellule porte une catégorie inconnue signale cette
  ligne et, en cas d'abandon, ne modifie aucune ligne. »
- `WF-IHM-0050-A` — « Un collage plus large que la grille est refusé en le disant. »

**Notes de réalisation.** Le contrat sépare déjà les deux temps, `previewPaste` puis
`applyPaste` : le front ne juge rien du contenu collé, il présente le compte rendu que le
serveur produit. C'est la même forme que l'import en deux temps de WF-ARC-0100.

## US-0140 — Annulation et rétablissement des saisies

- **statut** : à faire
- **exigences** : `WF-IHM-0110-A`
- **opérations** : `undoLastChange`, `redoLastUndo`
- **issue** :

**En tant que** chef de projet, **je veux** annuler mes saisies une par une et rétablir ce que
je viens d'annuler, **afin de** corriger une fausse manœuvre sans reconstruire à la main ce
qu'elle a défait.

**Critères d'acceptation.**

- `WF-IHM-0110-A` — « La suppression d'une tâche puis son annulation restituent la tâche, ses
  lignes et ses liaisons. »
- `WF-IHM-0110-A` — « Cinquante modifications successives s'annulent une par une, puis se
  rétablissent dans l'ordre. »
- `WF-IHM-0110-A` — « L'annulation d'une modification qu'un autre contributeur a depuis
  reprise est refusée en nommant l'objet en conflit. »
- `WF-IHM-0110-A` — « Aucune commande n'annule un marquage, un import appliqué ou une
  exclusion de ligne de coût. »

**Notes de réalisation.** L'annulation est portée par le serveur (`undoLastChange`), non par
une pile dans le navigateur : c'est ce qui permet le refus en cas de conflit, et ce que
WF-ARC-0070 impose. Le front ne fait qu'appeler et rafraîchir.

- écart : le conflit entre contributeurs et le refus qu'il déclenche ne se constatent qu'avec
  un serveur réel — le mock répond ce qu'on lui demande de répondre. La vérification complète
  revient à EP-06, où la grille de planning conserve ses saisies.

## US-0150 — Valeur calculée contre valeur saisie

- **statut** : à faire
- **exigences** : `WF-IHM-0030-A`
- **opérations** : aucune en propre
- **issue** :

**En tant que** chef de projet, **je veux** distinguer d'un coup d'œil ce que Waterfall
calcule de ce que j'ai saisi, **afin de** ne pas chercher à corriger un nombre dont la cause
est ailleurs.

**Critères d'acceptation.**

- `WF-IHM-0030-A` — « Dans une grille de devis, le montant d'une ligne de main-d'œuvre n'est
  pas saisissable, et son apparence diffère de celle de la charge en heures. »
- `WF-IHM-0030-A` — « La gravité et la provision d'un risque ne sont pas saisissables. »
- `WF-IHM-0030-A` — « La tentative de modifier la date de fin d'une tâche récapitulative est
  refusée en nommant ses subordonnées. »

**Notes de réalisation.** Le contrat sépare déjà les schémas de lecture et d'écriture pour
interdire l'envoi d'une valeur calculée, et porte une enveloppe `Computable`
(`docs/api/DECISIONS.md`) : le front n'a pas à tenir sa propre liste de ce qui est calculé, il
la lit du contrat.

## US-0160 — Échelle de signalement commune, lisible sans couleur

- **statut** : à faire
- **exigences** : `WF-IHM-0070-A`
- **opérations** : aucune en propre
- **issue** :

**En tant que** manager, **je veux** que le même état porte le même signalement partout, et
qu'aucun ne repose sur la seule couleur, **afin de** lire un tableau de bord imprimé en noir
et blanc, ou vu par quelqu'un qui distingue mal le rouge du vert.

**Critères d'acceptation.**

- `WF-IHM-0070-A` — « Une copie d'écran en niveaux de gris laisse identifier chaque
  signalement. »
- `WF-IHM-0070-A` — « La même zone d'indice porte la même couleur dans la liste des projets,
  dans les indicateurs du projet et dans la performance du portefeuille. »
- `WF-IHM-0070-A` — « Aucun écran ne distingue deux états par la seule couleur. »

**Notes de réalisation.** Un seul composant de signalement, alimenté par les zones que le
référentiel fixe (WF-REF-0170) : la matrice de risques, les dépassements de budget, la charge
des rôles et les signaux de santé du pilotage l'emploient tous.

## US-0170 — Refus et commandes indisponibles

- **statut** : à faire
- **exigences** : `WF-IHM-0090-A`
- **opérations** : `getProjectNextState`, `listProjectStateTransitions`, `listPermissions`
- **issue** :

**En tant que** chef de projet, **je veux** qu'une commande momentanément impossible me dise
ce qui manque, et qu'une commande que je n'ai pas le droit d'exercer ne me soit pas proposée,
**afin de** savoir quoi faire plutôt que de me heurter à un refus sans motif.

**Critères d'acceptation.**

- `WF-IHM-0090-A` — « Sur un projet en chiffrage, la commande de terminaison est présentée
  indisponible en nommant la condition manquante. »
- `WF-IHM-0090-A` — « Un utilisateur sans la permission de marquer une révision ne voit pas
  cette commande. »
- `WF-IHM-0090-A` — « Un refus de saisie sur un projet dont l'utilisateur n'est pas
  contributeur nomme cette condition. »

**Notes de réalisation.** Les conditions manquantes viennent du serveur, jamais d'une règle
recopiée dans le front (WF-ARC-0020) : `getProjectNextState` dit ce qui bloque, et
l'enveloppe d'erreur porte un code et ses paramètres que le front rend en phrase
(WF-ARC-0110). Griser un bouton reste une commodité de lecture, pas une protection.

## US-0180 — Traitements longs : suivi et signalement

- **statut** : à faire
- **exigences** : `WF-IHM-0080-A`
- **opérations** : `getBackgroundTask`, `getBackgroundTaskResult`, `markRevision`
- **issue** :

**En tant que** chef de projet, **je veux** qu'une action longue me rende la main et me
signale son aboutissement même si j'ai changé d'écran, **afin de** continuer à travailler
pendant qu'un marquage ou un import se fait.

**Critères d'acceptation.**

- `WF-IHM-0080-A` — « Le marquage d'une révision de dix mille objets laisse l'écran utilisable
  et présente son avancement. »
- `WF-IHM-0080-A` — « Un utilisateur qui change d'écran pendant un import est informé de son
  aboutissement. »
- `WF-IHM-0080-A` — « L'échec d'un traitement de fond est signalé avec son motif, et le même
  traitement peut être relancé. »

**Notes de réalisation.** Le contrat répond 202 avec une référence de tâche de fond
(WF-ARC-0090) : le suivi est un composant de la coquille, commun à toutes les tâches, et non
un morceau d'écran par action longue.

## US-0190 — Langue de l'interface, catalogues et formats d'affichage

- **statut** : à faire
- **exigences** : `WF-INTF-0160-A`, `WF-INTF-0170-A`, `WF-INTF-0180-A`, `WF-ADM-0040-A`, `WF-QUA-0070-A`
- **opérations** : `getMe`, `updateMyPreferences`
- **issue** :

**En tant que** chef de projet, manager ou administrateur, **je veux** l'interface dans ma
langue, choisie par mon navigateur puis par moi, sans que cela change une donnée ni un
montant, **afin de** travailler dans la langue que je lis et de partager les mêmes projets
que mes collègues.

**Critères d'acceptation.**

- `WF-INTF-0160-A` — « Un utilisateur dont le navigateur demande l'anglais obtient l'interface
  en anglais à sa première connexion, un autre demandant le français l'obtient en français. »
- `WF-INTF-0160-A` — « Un utilisateur qui force le français le retrouve en se connectant
  depuis un autre poste dont le navigateur demande l'anglais. »
- `WF-INTF-0160-A` — « Le changement de langue s'applique sans reconnexion. »
- `WF-INTF-0170-A` — « Deux utilisateurs de langues différentes ouvrant le même projet voient
  les mêmes libellés de tâches et de lignes, et des intitulés de colonnes et des libellés
  d'états différents. »
- `WF-INTF-0170-A` — « Aucun écran ne propose de saisir un libellé dans une seconde langue. »
- `WF-INTF-0170-A` — « Un projet créé par l'un est lisible par l'autre sans mention d'absence
  de traduction. » Il se vérifie sur le faux back : un projet saisi en français, ouvert dans
  une session en anglais, n'affiche aucune marque de traduction manquante sur ses textes
  saisis.
- `WF-INTF-0180-A` — « Le même montant s'affiche « 1 234,56 » en français et « 1,234.56 » en
  anglais, et le total du projet est le même. »
- `WF-QUA-0070-A` — « L'ajout d'une clé dans un seul catalogue fait échouer la chaîne. »
- `WF-QUA-0070-A` — « Un texte destiné à l'utilisateur écrit en dur dans le code fait échouer
  la chaîne. »
- `WF-QUA-0070-A` — « Le parcours de bout en bout s'exécute et aboutit en français comme en
  anglais. »

**Notes de réalisation.** Cette US écrit les sections du guide de développement qu'EP-01 a
ouvertes sans pouvoir les remplir : l'ajout d'une clé de traduction, et l'ajout d'un code
d'erreur côté front (US-0300). L'API ne renvoie aucune phrase (WF-ARC-0110) : les messages
d'erreur et les comptes rendus sont des codes que le front rend par son catalogue. C'est
cette US qui fixe le catalogue de codes d'erreur, et tout EPIC ultérieur y ajoute les siens.

- écart : `WF-ADM-0040-A` — « Un utilisateur modifie ses préférences et ne peut pas modifier
  celles d'un autre. » demande des comptes réels — EP-03.
- écart : `WF-ADM-0040-A` — « Deux utilisateurs ouvrant le même projet voient les mêmes
  données présentées selon leurs réglages respectifs. » est l'affaire de l'US-0110, et
  demande deux comptes réels — EP-03.
- écart : la conservation du choix dans le compte attend EP-03, de même que `WF-INTF-0160-A`
  — « Un utilisateur dont le navigateur demande une langue non offerte obtient la langue par
  défaut de l'installation. », cette langue étant un paramètre de l'installation.
- écart : `WF-INTF-0180-A` — « Un devis exporté par un utilisateur en français et réimporté
  par un utilisateur en anglais donne un devis identique, sans avertissement de format. » et
  « Le fichier Excel exporté porte les mêmes en-têtes quelle que soit la langue de celui qui
  l'exporte. » attendent les échanges de fichiers — EP-12 ; ici, seul l'affichage.

## US-0200 — Accessibilité minimale

- **statut** : à faire
- **exigences** : `WF-IHM-0100-A`
- **opérations** : aucune en propre
- **issue** :

**En tant que** chef de projet, manager ou administrateur, **je veux** atteindre toute action
au clavier, lire les textes sans effort et agrandir l'affichage sans rien perdre, **afin
d'**utiliser Waterfall toute la journée sans que l'outil me coûte plus que le travail.

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste
  visible. »
- `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau
  AA. »
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. »
- propre à l'US : chaque champ de saisie porte un libellé associé, et chaque image porteuse
  d'information une description — le quatrième point du corps de WF-IHM-0100, que son Vérif
  ne reprend pas ; un contrôle automatisé d'accessibilité le vérifie dans la chaîne.

**Notes de réalisation.** Le contrôle de contraste est exécuté par la chaîne, sinon il n'est
fait qu'une fois. Aucune conformité complète à un référentiel n'est visée ni déclarée
(§2.2) : ces quatre points, et rien de plus.

**Hors périmètre.** L'aide en ligne, qui n'est pas dans cet EPIC.

## US-0210 — Écrans du projet, des révisions et des contributeurs

- **statut** : à faire
- **exigences** : aucune en propre — les exigences de ces fonctions sont réalisées en EP-04
- **opérations** : `listProjects`, `createProject`, `getProject`, `updateProject`,
  `listProjectStateTransitions`, `exitProject`, `listSubprojects`, `listContributors`,
  `setContributors`, `listRevisions`, `getRevision`, `createRevision`, `markRevision`,
  `designateReferenceRevision`, `compareRevisions`
- **issue** :

**En tant que** chef de projet, **je veux** les écrans de la liste des projets, du projet, de
ses sous-projets, de ses contributeurs et de ses révisions, **afin de** voir si le contrat
sait dire tout ce qu'ils ont à montrer.

**Critères d'acceptation.**

- propre à l'US : chaque écran s'alimente du faux back par le client engendré, sans qu'aucune
  donnée soit écrite dans le front ;
- propre à l'US : l'écran de comparaison de deux révisions présente ce que `compareRevisions`
  renvoie, sans rapprochement calculé dans le front ;
- propre à l'US : tout manque du contrat constaté ici est écrit dans cet EPIC, puis corrigé
  dans `docs/api` ou ouvert en issue.

## US-0220 — Écrans du planning et du devis

- **statut** : à faire
- **exigences** : aucune en propre — EP-06 et EP-07
- **opérations** : `getWorkBreakdown`, `listNodes`, `createNode`, `updateTaskFacet`,
  `setPredecessors`, `moveNodes`, `generatePlanningSkeleton`, `listTimelines`,
  `listCostStructures`, `updateEstimateLine`, `getEstimateIndicators`, `getMissingRates`
- **issue** :

**En tant que** chef de projet, **je veux** la grille de planning, le diagramme de Gantt en
lecture seule, l'arborescence de tâches et la grille de devis, **afin d'**éprouver sur le
plus gros volume de l'application — mille tâches, cinq lignes par tâche — la grille dense et
les objectifs de temps de réponse.

**Critères d'acceptation.**

- propre à l'US : la grille de planning et celle de devis sont deux configurations du même
  composant, non deux composants ;
- propre à l'US : le Gantt et l'arborescence se lisent et ne proposent aucune modification ;
- propre à l'US : sur mille tâches servies par le faux back, l'ouverture d'une grille tient
  l'objectif d'une seconde du §4.6.2.

## US-0230 — Écrans des risques, du reste à engager et des coûts réels

- **statut** : à faire
- **exigences** : aucune en propre — EP-08 et EP-09
- **opérations** : `listRisks`, `getRisk`, `listRiskReviews`, `getProjectRiskMatrix`,
  `getRemainingIndicators`, `setLineRemaining`, `listStartableTasks`, `setTaskProgress`,
  `listActualCosts`, `setActualCostTrackedScope`, `listCostImports`
- **issue** :

**En tant que** chef de projet, **je veux** les écrans des risques et de leur matrice, du
reste à engager, de l'avancement et des coûts réels, **afin de** vérifier que la maquette
porte le cycle d'une revue mensuelle de bout en bout.

**Critères d'acceptation.**

- propre à l'US : la matrice de risques emploie le composant de signalement de l'US-0160 ;
- propre à l'US : la gravité et la provision d'un risque sont présentées comme calculées
  (US-0150) ;
- propre à l'US : l'écran d'avancement ne propose aucun pourcentage à saisir — une tâche est
  terminée ou elle ne l'est pas.

## US-0240 — Écrans des indicateurs et du portefeuille

- **statut** : à faire
- **exigences** : aucune en propre — EP-10 et EP-11
- **opérations** : `getProjectIndicators`, `getCostCurve`, `getEarnedValueCurves`,
  `getProjectCashOut`, `getMilestoneTracking`, `getProjectWorkload`, `getPortfolioProjects`,
  `getPortfolioValue`, `getPortfolioPerformance`, `getPortfolioWorkload`,
  `getPortfolioCostStructure`, `getPortfolioRisks`, `getPortfolioCashOut`,
  `getPortfolioPilotHealth`
- **issue** :

**En tant que** manager, **je veux** les courbes et les tableaux d'indicateurs du projet et du
portefeuille, **afin de** voir si les endpoints d'agrégation renvoient ce qu'une vue demande,
sans que le front ait à sommer quoi que ce soit.

**Critères d'acceptation.**

- propre à l'US : aucune somme, aucune moyenne, aucun ratio n'est calculé dans le front ; une
  vue qui en aurait besoin est un constat sur le contrat ;
- propre à l'US : chaque indicateur affiché porte sa date de calcul (US-0100) ;
- propre à l'US : les zones d'indice emploient le composant de signalement de l'US-0160.

**Notes de réalisation.** Courbes en Apache ECharts (annexe C).

## US-0250 — Écrans du référentiel et de l'administration

- **statut** : à faire
- **exigences** : aucune en propre — EP-03 et EP-05
- **opérations** : `getReferenceReadiness`, `getReferenceSettings`, `listOrgNodes`,
  `listResourceRoles`, `listCalendars`, `listCostTypes`, `listCostCategories`,
  `listHourlyRates`, `setHourlyRate`, `listUsers`, `createUser`, `setUserAccessRoles`,
  `listAccessRoles`, `listPermissions`, `getSystemStatus`
- **issue** :

**En tant qu'**administrateur, **je veux** les écrans du référentiel, des comptes, des rôles
d'habilitation et de l'état du système, **afin de** vérifier qu'ils s'atteignent sans projet
ouvert et que la matrice des permissions se lit.

**Critères d'acceptation.**

- propre à l'US : ces écrans sont atteignables sans qu'aucun projet ne soit ouvert (US-0090) ;
- propre à l'US : la grille des taux horaires, qui porte quinze ans de valeurs pour cent
  cinquante rôles, emploie le composant de grille dense ;
- propre à l'US : l'écran des rôles d'habilitation présente les permissions par fonction de
  second niveau, telles que `listPermissions` les renvoie.

## US-0260 — Écran d'import en deux temps

- **statut** : à faire
- **exigences** : aucune en propre — EP-09 et EP-12
- **opérations** : `uploadFile`, `openImport`, `getImport`, `abandonImport`, `applyImport`,
  `listImports`, `requestExport`
- **issue** :

**En tant que** chef de projet, **je veux** l'écran qui dépose un fichier, présente le compte
rendu d'analyse, et applique ou abandonne l'import, **afin de** vérifier que la forme en deux
temps du contrat se tient à l'écran.

**Critères d'acceptation.**

- propre à l'US : le compte rendu est celui que `getImport` renvoie, rendu par le catalogue de
  l'US-0190 — aucune phrase ne vient de l'API (WF-ARC-0110) ;
- propre à l'US : l'application est une tâche de fond suivie par le composant de l'US-0180 ;
- propre à l'US : rien n'est appliqué sans confirmation, et un abandon laisse l'écran de
  départ.

## US-0270 — Le front n'appelle l'API que par le client engendré

- **statut** : à faire
- **exigences** : `WF-ARC-0020-A`
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** que la chaîne rejette tout appel au serveur écrit à
la main dans le front, **afin que** la règle « le contrat est le seul contrat » ne dépende pas
de la relecture.

**Critères d'acceptation.**

- `WF-ARC-0020-A` — « Le front ne contient aucun appel http vers l'API hors du client
  engendré. »
- `WF-ARC-0020-A` — « Le diagramme de déploiement (§4.3.1) ne montre aucun composant entre le
  front et l'API. » Il se vérifie sur la spécification, et la revue d'un lot qui ajouterait
  un intermédiaire le refuse.
- `WF-ARC-0020-A` — « Les montants, dates et indices affichés sont ceux que l'API renvoie,
  sans recalcul. »
- propre à l'US : une règle d'analyse statique interdit `fetch` et les clients http hors du
  module du client engendré, et elle est bloquante (WF-QUA-0030).

**Notes de réalisation.** La seconde phrase de la Vérif ne se contrôle pas par une règle
d'outil : elle se tient par la revue, et par le fait qu'aucun écran de cet EPIC n'a de raison
de calculer — le mock répond déjà les valeurs. Les constats de l'EPIC sont l'endroit où se
note un écran qui aurait été tenté de le faire.

## US-0290 — Navigateurs et largeurs d'affichage

- **statut** : à faire
- **exigences** : `WF-CMP-0010-A`
- **opérations** : aucune en propre
- **issue** :

**En tant que** chef de projet, **je veux** que les grilles, le Gantt et les courbes
fonctionnent sur le navigateur de mon poste, et consulter les indicateurs depuis mon
téléphone, **afin de** ne rien installer et de répondre à une question sur un projet loin de
mon bureau.

**Critères d'acceptation.**

- `WF-CMP-0010-A` — « Les grilles, le diagramme de Gantt et les courbes s'affichent et
  s'utilisent sur chacun des quatre navigateurs, dans leurs deux dernières versions majeures,
  à 1366 points de large. »
- `WF-CMP-0010-A` — « Les vues d'indicateurs se lisent sur un écran de 360 points de large et
  n'y proposent aucune saisie. »
- `WF-CMP-0010-A` — « Aucune fonction n'exige une installation sur le poste. »

**Notes de réalisation.** La matrice des navigateurs est celle du harnais de bout en bout
d'EP-01 (US-0080) : le parcours témoin et ceux de cet EPIC s'y jouent sur les quatre
navigateurs, à 1366 points, puis les vues d'indicateurs à 360.
