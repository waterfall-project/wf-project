---
revue_du: 2026-09-26
sur: waterfall-spec.md généré le 2026-09-26 (commit 90da46f)
revue_par: Claude Opus 5
perimetre: chapitre 4 — architecture technique, 38 exigences (ARC, DAT, EXP, SEC, OBS, CMP) et le texte qui les porte
---

# Revue du 2026-09-26 — l'architecture technique

## Suivi des revues précédentes

Les sept revues précédentes sont soldées : aucun constat n'est resté « à traiter ». Deux points
signalés hors constats lors de l'allocation des champs PBS sont repris ici, parce qu'ils
appartiennent au §4 : la couverture de la matrice (C-068) et la règle d'allocation (C-069).

## Ce que vaut le chapitre

Le §4 tient ses promesses sur l'essentiel : les trois principes se vérifient, les décisions
différées sont toutes tranchées et motivées, et les exigences de données disent ce qu'un
développeur a besoin de savoir avant d'écrire une ligne. Les renvois vers le §3 sont justes — j'ai
vérifié les vingt-sept renvois d'exigence du chapitre, aucun ne porte à faux.

Seize constats, dont huit majeurs. Aucun n'est bloquant, mais deux d'entre eux changent ce qu'un
développeur construirait :

- **le marquage d'une révision** : le texte et la figure du §4.3.4 lui font créer la révision
  suivante par copie, ce que WF-DAT-0010 exclut et que le §3 ne prévoit pas (C-070) ;
- **le mode dégradé de Redis** : la saisie ne peut pas continuer sans lui, puisque les sessions y
  vivent — et elles n'y ont pas leur place, puisqu'une session ne se reconstruit pas (C-074).

S'y ajoute un troisième trou, découvert en examinant la mise en œuvre des autorisations : rien ne
dit ce que devient un import confirmé dont l'auteur a perdu ses droits entre l'analyse et
l'application (C-082).

Le reste est de la précision : trois délais qu'aucune exigence ne fixe, une donnée — l'avatar —
qui n'a ni table ni stockage, et une matrice qui ne couvre que la moitié des codes FBS employés.

## Constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-067 | mineur | §1.2 | Onze acronymes du §4 manquent au tableau des abréviations | intégré |
| C-068 | majeur | §4.2.2 | La matrice ne couvre pas vingt-huit des codes FBS que citent les exigences du §3 | intégré |
| C-069 | majeur | §4.2.2 | La règle d'allocation du champ PBS ne décrit pas celle qui a été appliquée | intégré |
| C-070 | majeur | §4.3.4, figure 19 | Le marquage crée-t-il la révision suivante ? Le §4 dit oui et non | intégré |
| C-071 | majeur | WF-ARC-0100, WF-SEC-0020 | Trois délais qu'aucune exigence ne fixe ni ne rend paramétrables | intégré |
| C-072 | majeur | §4.4.1, WF-DAT-0120 | L'avatar n'a ni table ni stockage | intégré |
| C-073 | majeur | §4.4.2, WF-DAT-0040 | Ce qu'une révision marquée avant l'état En cours conserve n'est pas dit | intégré |
| C-074 | majeur | §4.5.4, WF-DAT-0130 | Redis indisponible : la saisie ne peut pas continuer, contrairement au tableau | intégré |
| C-075 | mineur | §4.4.1, WF-DAT-0090 | Une règle fonctionnelle n'existe qu'au §4 : l'unicité du nom de version | intégré |
| C-076 | mineur | §3.4.2.4, WF-ADM-0160 | La restauration ne dit pas que le cache est vidé | sans objet |
| C-077 | mineur | WF-SEC-0010, WF-OBS-0020, WF-CRE-0050, WF-SEC-0030 | Deux interdictions et deux journaux en double | intégré |
| C-078 | mineur | §4.6.4, WF-EXP-0060 | Le résultat du test de restauration n'a pas d'écran où paraître | intégré |
| C-079 | mineur | §4.6.5, WF-CMP-0020 | Rien n'est exigé pour l'empaquetage Compose | intégré |
| C-080 | mineur | §4.2.1.5, §4.3.2, PBS-5.3, TFX-10 | Comment une tâche planifiée est-elle déclenchée ? | intégré |
| C-081 | mineur | §4.2.1.5, §4.3.2, §1.3.1 | Coquilles et formes | intégré |
| C-082 | majeur | §4.3.4, WF-ARC-0100 | Un import confirmé s'applique-t-il quand les droits ont changé entre-temps ? | intégré |

---

## C-067 — Onze acronymes du §4 manquent au tableau des abréviations

- **gravité** : mineur
- **emplacement** : §1.2, tableau 1 Abréviations
- **citation** : « Role-Based Access Control » (dernière ligne du tableau)

**Constat.** Le tableau des abréviations couvre les codes du document et le vocabulaire de la
valeur acquise. Le §4 en emploie onze qu'il ne définit pas : API, CI/CD, DDL, HTTPS, JSON, LDAP,
LDAPS, OIDC, REST, S3, UUID. Le lecteur visé par le §4 les connaît ; le lecteur du document
entier, non, et c'est pour lui que le tableau existe.

**Proposition.** Onze lignes à ajouter, dans l'ordre alphabétique du tableau :

| Code | Signification |
|---|---|
| API | Interface de programmation (Application Programming Interface) |
| CI/CD | Intégration et livraison continues (Continuous Integration / Continuous Delivery) |
| DDL | Langage de définition de données (Data Definition Language) |
| HTTPS | Protocole HTTP chiffré par TLS |
| JSON | Format d'échange de données (JavaScript Object Notation) |
| LDAP | Protocole d'accès à un annuaire (Lightweight Directory Access Protocol) |
| LDAPS | LDAP chiffré par TLS |
| OIDC | Protocole d'authentification déléguée (OpenID Connect) |
| REST | Style d'interface fondé sur HTTP (Representational State Transfer) |
| S3 | Interface de stockage objet, devenue un standard de fait |
| UUID | Identifiant unique universel (Universally Unique Identifier) |

**Statut.** intégré

---

## C-068 — La matrice ne couvre pas vingt-huit des codes FBS que citent les exigences du §3

- **gravité** : majeur
- **emplacement** : §4.2.2, tableau 6 Correspondances FBS – PBS
- **citation** : « La matrice donne, pour chaque fonction de l'arborescence fonctionnelle, les composants qui la réalisent. »

**Constat.** La matrice compte vingt-six lignes ; l'arborescence fonctionnelle compte
soixante-et-un nœuds, et les exigences du §3 citent vingt-huit codes qui n'y figurent pas. Trois
familles :

- les **codes parents** qu'une exigence cite plutôt que leurs enfants : FBS-2, FBS-3, FBS-4.3,
  FBS-4.4, FBS-4.5, FBS-4.6, FBS-4.8. Quatorze exigences sont dans ce cas, dont WF-PLA-0010 à
  WF-PLA-0070, WF-DEV-0010, WF-DEV-0020, WF-IND-0010 à WF-IND-0030 ;
- les **feuilles absentes** alors que leurs sœurs sont présentes : FBS-2.2 à FBS-2.6, FBS-3.1.1,
  FBS-3.1.2, FBS-3.2.1 à FBS-3.2.3, FBS-3.3, FBS-4.2.1 à FBS-4.2.5, FBS-4.8.2 à FBS-4.8.4,
  FBS-4.8.7, FBS-4.8.8. La ligne « FBS-2.1 à FBS-2.7 » les couvre pour le portefeuille, celle
  « FBS-3.1 à FBS-3.4 » pour le référentiel, mais les paramètres de projets (FBS-4.2.x) n'ont
  qu'une ligne « FBS-4.2 » et les indicateurs sont couverts par intervalles ;
- les **imports et exports Excel du devis et du reste à engager** : WF-INTF-0100 à WF-INTF-0130
  se rattachent à FBS-4.4 et FBS-4.5, dont la matrice dit « — », alors que ces échanges passent
  par le worker et le stockage objet exactement comme FBS-4.3.4.

Le troisième cas est le seul qui fausse quelque chose : j'ai alloué PBS-2.2 et PBS-3.3 à ces
quatre exigences, ce que la matrice ne permet pas de justifier.

**Proposition.** Deux corrections.

1. Ajouter une ligne à la matrice, après FBS-4.3.5 : « FBS-4.4 et FBS-4.5 (imports et exports
   Excel du devis et du reste à engager) | PBS-2.2, PBS-3.3 ».
2. Poser la règle de lecture qui rend les autres cas inoffensifs, à la suite de la phrase citée :
   « Une fonction absente de la matrice est réalisée par le socle seul ; une exigence qui cite un
   code parent hérite de la ligne la plus large qui le couvre. »

**Statut.** intégré

---

## C-069 — La règle d'allocation du champ PBS ne décrit pas celle qui a été appliquée

- **gravité** : majeur
- **emplacement** : §4.2.2
- **citation** : « Le champ PBS d'une exigence du §3 reprend la ligne de sa fonction. »

**Constat.** Appliquée à la lettre, cette règle donne à WF-ADM-0040 « Préférences d'affichage » le
composant d'import de l'annuaire (PBS-2.2) et celui des tâches planifiées (PBS-5.3), parce que sa
fonction FBS-1.1 les porte pour WF-ADM-0070. Elle attribue de même le stockage objet à tous les
exports, que WF-DAT-0120 exclut d'y écrire.

Les cent quarante-deux champs PBS ont donc été remplis selon une règle plus fine : le socle, plus
les composants de la ligne de la fonction que l'exigence engage réellement. La matrice reste
vraie comme union des exigences de la fonction ; c'est la phrase qui ne l'est plus.

**Proposition.** « Le champ PBS d'une exigence du §3 reprend le socle et, parmi les composants de
la ligne de sa fonction, ceux qu'elle engage. La ligne de la matrice est l'union des composants
de ses exigences. »

**Statut.** intégré

---

## C-070 — Le marquage crée-t-il la révision suivante ? Le §4 dit oui et non

- **gravité** : majeur
- **emplacement** : §4.3.4 et figure 19 ; WF-DAT-0010 ; WF-REV-0010 et WF-INTF-0090
- **citation** : « Tout s'y passe dans une transaction unique : figer la révision, calculer et conserver ses indicateurs (WF-DAT-0040), puis créer la révision suivante par copie (WF-DAT-0010). » (§4.3.4) ; « le marquage ne copie rien » (WF-DAT-0010)

**Constat.** Le texte du §4.3.4 et la figure 19 font trois choses au marquage, dont la création de
la révision suivante par copie. WF-DAT-0010 dit l'inverse, dans la même page : « La création
d'une révision en cours copie ces lignes depuis la dernière révision marquée ; **le marquage ne
copie rien** ». Le §3 est du côté de WF-DAT-0010 : WF-REV-0010 fait de la création un acte
distinct, et WF-INTF-0090 prévoit explicitement le cas d'un projet « qui n'en comporte pas »,
c'est-à-dire d'un projet dont la dernière révision est marquée et qui n'a pas encore de révision
en cours. Si le marquage créait la suivante, ce cas n'existerait jamais et la phrase de
WF-INTF-0090 serait morte.

Ce n'est pas une nuance de rédaction. Copier dix mille objets dans la transaction de marquage la
rend deux fois plus longue, et surtout : un projet aurait toujours une révision en cours ouverte,
là où le §3 le laisse sans révision modifiable entre deux revues.

**Proposition.** Aligner le §4 sur le §3. Dans le texte du §4.3.4 : « Les deux écritures se font
dans une transaction unique : figer la révision, puis calculer et conserver ses indicateurs
(WF-DAT-0040). Si l'une échoue, aucune n'a eu lieu. La révision suivante n'est créée qu'à la
demande, ou par le premier import (WF-REV-0010, WF-INTF-0090), et c'est alors qu'a lieu la copie. »
Retirer de la figure `figures/marquage-revision.mmd` l'étape « crée la révision suivante par
copie », et y ajouter une note disant que la copie relève de la création suivante.

**Statut.** intégré

---

## C-071 — Trois délais qu'aucune exigence ne fixe ni ne rend paramétrables

- **gravité** : majeur
- **emplacement** : §4.3.4, WF-ARC-0100 ; §4.6.1, WF-SEC-0020
- **citation** : « Un compte rendu non confirmé expire sans effet au terme d'un délai » (WF-ARC-0100) ; « Une session authentifiée porte une durée de validité et une durée d'inactivité au terme desquelles elle expire. » (WF-SEC-0020)

**Constat.** Trois durées commandent un comportement observable et aucune n'est chiffrée ni
déclarée paramétrable. Un développeur choisira, et la Vérif ne pourra pas le contredire : « Un
compte rendu expiré ne peut plus être appliqué » est vrai avec une minute comme avec un mois.

Le document sait faire autrement. Les seuils d'indice et le délai entre revues sont au référentiel
(WF-REF-0170, WF-REF-0180) ; le verrouillage après dix échecs et la validité d'une heure du lien
de réinitialisation sont chiffrés dans WF-ADM-0140. Ces trois délais-ci doivent suivre l'un des
deux régimes.

**Proposition.** Les chiffrer, en laissant la porte ouverte au paramétrage d'exploitation :

- WF-ARC-0100 : « Un compte rendu non confirmé expire sans effet au terme de vingt-quatre
  heures » — un import préparé en fin de journée doit pouvoir être confirmé le lendemain matin, et
  au-delà l'extraction est de toute façon à refaire.
- WF-SEC-0020 : « Une session expire au terme de douze heures, et après deux heures sans
  activité. » Douze heures couvrent une journée de travail sans reconnexion ; deux heures
  d'inactivité ferment un poste laissé ouvert avant la fin de la journée.

Ajouter à chacune, en Vérif : « Le délai est vérifiable par un essai à sa borne. »

**Statut.** intégré

---

## C-072 — L'avatar n'a ni table ni stockage

- **gravité** : majeur
- **emplacement** : §4.4.1, tableau 9 ; WF-DAT-0120 ; WF-ADM-0080 ; WF-EXP-0010
- **citation** : « Le stockage objet porte deux compartiments : les fichiers en cours d'import et les sauvegardes. […] Aucun autre fichier n'y est conservé » (WF-DAT-0120)

**Constat.** WF-ADM-0080 donne à chaque compte une image, WF-ADM-0050 la porte dans ses attributs,
et WF-EXP-0010 exige de la remplacer lors d'une anonymisation : c'est donc une donnée durable. Or
le tableau des objets et des tables ne la mentionne pas, et WF-DAT-0120 interdit explicitement au
stockage objet de porter autre chose que les imports et les sauvegardes. L'avatar n'a nulle part
où vivre.

Deux conséquences pratiques, au-delà de l'omission : si l'avatar allait au stockage objet, la
sauvegarde de la seule base (WF-ADM-0150) ne le sauvegarderait pas, et le §3.4.2.4 redeviendrait
faux en affirmant que la base « contient tout ce que la plateforme sait ».

**Proposition.** Le porter en base, et le dire. Dans le paragraphe qui précède le tableau 9 :
« L'avatar d'un compte est conservé en base avec lui, et non sur le stockage objet : c'est ce qui
le fait entrer dans la sauvegarde. Sa taille est bornée par l'application. » Et une ligne au
tableau 9 : « Avatar | attribut de `user_account` | plateforme ».

**Statut.** intégré

---

## C-073 — Ce qu'une révision marquée avant l'état En cours conserve n'est pas dit

- **gravité** : majeur
- **emplacement** : §4.4.2, WF-DAT-0040 ; §3.4.5.8, WF-IND-0010
- **citation** : « Les indicateurs d'une révision sont calculés à son marquage, dans la transaction qui la marque, et conservés avec elle » (WF-DAT-0040) ; « Les indicateurs projets ne sont calculés qu'à partir de l'état En cours ; avant, seuls les indicateurs de devis sont disponibles. » (WF-IND-0010)

**Constat.** Pendant le chiffrage, un projet marque plusieurs révisions — les offres successives —
et aucune n'a d'indicateurs projets, faute de budget de référence. La Vérif de WF-DAT-0040 dit
pourtant que « le marquage d'une révision échoue entièrement si le calcul de ses indicateurs
échoue ». Lu ensemble, cela ferait échouer le marquage de toute offre.

Ce qu'il faut dire tient en une phrase : une révision marquée avant l'état En cours conserve les
indicateurs de devis (FBS-4.4.1), et rien d'autre ; les indicateurs projets apparaissent à partir
de la première révision marquée en état En cours. Le portefeuille en dépend directement :
WF-PTF-0050 somme les devis courants des projets en chiffrage, et WF-PTF-0010 calcule à une date
passée « par la dernière révision marquée antérieure ».

**Proposition.** Ajouter au corps de WF-DAT-0040, après la première phrase : « Une révision
marquée avant l'état En cours ne conserve que les indicateurs de devis (FBS-4.4.1) ; les
indicateurs projets sont calculés et conservés à partir de l'état En cours, conformément à
WF-IND-0010. » Et en Vérif : « Le marquage d'une offre, sur un projet en chiffrage, aboutit et
conserve le total du devis sans aucun indicateur projet. »

**Statut.** intégré

---

## C-074 — Redis indisponible : la saisie ne peut pas continuer, contrairement au tableau

- **gravité** : majeur
- **emplacement** : §4.5.4, tableau 11 Modes dégradés ; §4.4.5, WF-DAT-0130 ; §4.2 et §4.2.1.3 ; WF-ARC-0040
- **citation** : ligne « Redis » du tableau 11 — « La consultation et la saisie ; les permissions et les indicateurs sont recalculés à chaque requête » face à « Les sessions en cours, qui exigent une reconnexion ; la prise de nouvelles tâches » ; « Le cache porte les sessions et les jetons, les permissions effectives de chaque utilisateur, et les indicateurs de la révision en cours de chaque projet. » (WF-DAT-0130)

**Constat.** Si les sessions vivent dans Redis, son indisponibilité ne coûte pas une reconnexion :
elle interdit toute connexion, puisque la session nouvelle n'aurait nulle part où être écrite. La
colonne « ce qui continue » promet la consultation et la saisie, ce qu'aucun utilisateur ne pourra
faire. Le tableau se contredit d'ailleurs lui-même : il place la reconnexion du côté de ce qui
s'arrête, tout en laissant la saisie du côté de ce qui continue.

La cause est plus profonde qu'une ligne de tableau : WF-ARC-0040 pose que Redis « ne porte que des
données reconstructibles depuis PostgreSQL », et cite les sessions parmi elles. Or une session ne
se reconstruit pas — la perdre déconnecte tout le monde. Elle n'avait pas sa place dans un cache.
La distinction que le §4 doit tenir est celle-ci : un **cache** dégrade naturellement, puisque son
absence se recalcule ; un **magasin** ne dégrade pas. Redis ne doit porter que le premier.

Le cache des permissions effectives, lui, pose un autre problème : il n'est nécessaire à rien. Les
permissions d'un compte s'obtiennent par une jointure sur des tables minuscules — cinq cents
comptes, une dizaine de rôles, environ cent vingt permissions —, en permanence en mémoire, sur la
connexion qui sert déjà la requête. Le cacher coûte l'invalidation que WF-DAT-0130 décrit, et la
classe de défauts qui va avec : une permission retirée qui survit quelques secondes, contre ce
qu'exige WF-ADM-0090.

**Proposition.** Ramener Redis à ce que WF-ARC-0040 dit de lui, et rendre le mode dégradé vrai.

1. **WF-DAT-0130** : le cache ne porte plus que les indicateurs de la révision en cours de chaque
   projet. Retirer les sessions et les jetons, retirer les permissions effectives. L'invalidation
   se réduit à : « toute écriture dans une révision en cours invalide ses indicateurs, et le
   marquage d'une révision invalide les entrées du projet ». La durée de validité et la dernière
   phrase sont conservées.
2. **Les sessions passent en base** : une ligne au tableau 9 — « Session | `session` | plateforme » —
   et PBS-3.1 les reçoit. Le coût est une lecture indexée sur une table de cinquante lignes, sur
   une connexion déjà ouverte, et une écriture de dernière activité au plus une fois par minute et
   par session, pour l'expiration par inactivité de WF-SEC-0020.
3. **Les permissions sont lues à chaque requête**, sans cache, et mémoïsées pour la durée de la
   requête. WF-ADM-0090 est alors satisfaite sans mécanisme : il n'y a rien à invalider.
4. **§4.2 (« Trois composants de données »), §4.2.1.3 (PBS-3.2) et WF-ARC-0040** : Redis porte le
   cache des indicateurs de la révision en cours et la file de tâches, rien d'autre.
5. **Tableau 11, ligne Redis** : « Ce qui continue : tout, les indicateurs de la révision en cours
   étant recalculés à chaque requête | Ce qui s'arrête : la prise de nouvelles tâches ».

Le jeton signé, que j'avais d'abord envisagé, est écarté : il ne dispense d'une lecture que si l'on
renonce à la révocation immédiate de WF-SEC-0020, et il ajoute une clé de signature à faire
tourner. Il n'achèterait, pendant une panne, que la durée de vie d'un jeton.

**Statut.** intégré

---

## C-075 — Une règle fonctionnelle n'existe qu'au §4 : l'unicité du nom de version

- **gravité** : mineur
- **emplacement** : §4.4.1, WF-DAT-0090 ; §3.4.5.1, WF-REV-0020 et WF-REV-0090
- **citation** : « Les unicités imposées par le §3 — adresse électronique, code projet, code de sous-projet par projet, nom de version par projet, numéro de pièce par projet — sont déclarées en base. » (WF-DAT-0090)

**Constat.** Quatre de ces cinq unicités sont effectivement imposées par le §3. La cinquième non :
ni WF-REV-0020, qui exige un nom de version au marquage, ni WF-REV-0090, qui l'énumère parmi les
attributs, ne dit qu'il est unique dans le projet. Le §4 ajoute donc une règle fonctionnelle, et
la présente comme une reprise.

La règle est bonne — deux révisions nommées « v2.0 » dans un même projet rendraient l'historique
illisible. Elle doit juste être posée là où elle appartient.

**Proposition.** Ajouter au corps de WF-REV-0020 : « Le nom de version est unique parmi les
révisions marquées du projet. » Et à sa Vérif : « Le marquage d'une révision sous un nom de
version déjà employé dans le projet est refusé. » WF-DAT-0090 devient alors exact sans changer.

**Statut.** intégré

---

## C-076 — La restauration ne dit pas que le cache est vidé

- **gravité** : mineur
- **emplacement** : §3.4.2.4, WF-ADM-0160 ; §4.4.5, WF-DAT-0130
- **citation** : « La restauration remplace l'intégralité de la base par son contenu sauvegardé, déconnecte les utilisateurs pendant sa durée » (WF-ADM-0160)

**Constat.** Après une restauration, la base est celle d'hier et le cache celui de maintenant :
des permissions calculées pour des rôles qui n'existent plus, des indicateurs de révisions
disparues. WF-DAT-0130 énumère les écritures qui invalident une entrée ; la restauration n'en
fait pas partie, et c'est la plus radicale de toutes.

**Proposition.** Une phrase dans WF-DAT-0130, après l'énumération des invalidations : « Une
restauration (WF-ADM-0160) vide entièrement le cache. » Et dans la Vérif de WF-ADM-0160 : « Après
restauration, aucune valeur mise en cache avant elle n'est servie. »

**Statut.** sans objet — le cache ne portant plus que des indicateurs recalculables (C-074), une restauration n'a plus rien à invalider

---

## C-077 — Deux interdictions et deux journaux en double

- **gravité** : mineur
- **emplacement** : §4.6.1, WF-SEC-0010 et WF-SEC-0030 ; §4.6.3, WF-OBS-0020 ; §3.4.5.7, WF-CRE-0050
- **citation** : « ne figure dans le dépôt, dans une image de conteneur ni dans un journal » (WF-SEC-0010) ; « Aucun journal ne contient de mot de passe, de jeton de session ni de secret. » (WF-OBS-0020)

**Constat.** Deux redondances, de nature différente.

- **La même interdiction, deux fois.** WF-SEC-0010 et WF-OBS-0020 interdisent tous deux les
  secrets dans les journaux. Ce n'est pas contradictoire, mais le document s'est donné pour règle
  qu'un concept a un propriétaire : le jour où la liste s'allonge, elle s'allongera d'un côté
  seulement.
- **Deux journaux pour les imports.** WF-CRE-0050 journalise chaque import de coûts réels avec sa
  date, son auteur et ses comptes de lignes, pour le chef de projet ; WF-SEC-0030 inscrit
  « l'application d'un import » au journal d'audit, pour l'exploitant. Un développeur peut de
  bonne foi n'en écrire qu'un, ou deux qui divergent. Il faut dire qu'il y en a deux et pourquoi :
  l'un est une donnée du projet, consultable avec les coûts réels ; l'autre est une trace
  d'exploitation, non modifiable, conservée à part.

**Proposition.** Retirer « ni dans un journal » de WF-SEC-0010, dont le sujet est le transport et
les secrets, et laisser la règle à WF-OBS-0020, dont le sujet est le journal. Ajouter au Motif de
WF-SEC-0030 : « Le journal d'audit ne remplace pas le journal des imports de WF-CRE-0050 : celui-ci
est une donnée du projet, consultable avec ses coûts réels, celui-là une trace d'exploitation que
la plateforme ne peut pas réécrire. »

**Statut.** intégré

---

## C-078 — Le résultat du test de restauration n'a pas d'écran où paraître

- **gravité** : mineur
- **emplacement** : §4.6.4, WF-EXP-0060 ; §3.4.2.3, WF-ADM-0130
- **citation** : « Le résultat du test et sa date sont conservés et présentés à l'exploitant. » (WF-EXP-0060)

**Constat.** Le seul écran d'exploitation du produit est celui de WF-ADM-0130, et son contenu est
énuméré : disponibilité des composants, espace de stockage, version, dernière synchronisation
d'annuaire, dernière sauvegarde, alertes en cours. Le test de restauration n'y figure pas. Soit
l'exigence promet un affichage qui n'existe pas, soit il faut l'ajouter à l'écran.

**Proposition.** Ajouter « la date et le résultat du dernier test de restauration » à
l'énumération de WF-ADM-0130, et à sa Vérif : « L'écran indique la date du dernier test de
restauration. » C'est cohérent avec la ligne voisine sur la dernière sauvegarde, et cela donne à
WF-EXP-0060 l'endroit qui lui manque.

**Statut.** intégré

---

## C-079 — Rien n'est exigé pour l'empaquetage Compose

- **gravité** : mineur
- **emplacement** : §4.6.5, WF-CMP-0020 ; WF-ARC-0050
- **citation** : « Waterfall exige PostgreSQL dans une version au moins égale à 15, Redis dans une version au moins égale à 7, un stockage compatible avec l'interface S3, et, pour le déploiement par chart, Kubernetes dans une version au moins égale à 1.27. »

**Constat.** WF-ARC-0050 livre deux empaquetages ; WF-CMP-0020 n'annonce les prérequis que du
premier. Celui qui installe par Compose — un développeur, une recette, une petite installation —
ne sait ni quel moteur de conteneurs ni quelle mémoire lui sont demandés. C'est le cas d'emploi
le plus fréquent au début du projet.

**Proposition.** Compléter le corps : « Pour le déploiement par Compose, un moteur de conteneurs
compatible avec la spécification Compose v2, et une machine de quatre cœurs et huit gigaoctets de
mémoire pour la plateforme entière, composants de données compris. » Et en Vérif : « Le
déploiement par Compose aboutit sur une machine conforme à ces caractéristiques. »

**Statut.** intégré

---

## C-080 — Comment une tâche planifiée est-elle déclenchée ?

- **gravité** : mineur
- **emplacement** : §4.2.1.5, PBS-5.3 ; §4.3.2, TFX-10 ; WF-ARC-0080, WF-ARC-0090
- **citation** : « exécutées par le worker sur déclenchement de la plateforme » (PBS-5.3) ; « Déclenchement des tâches planifiées », ligne TFX-10 du tableau 7, dont la destination est « Worker »

**Constat.** « Sur déclenchement de la plateforme » laisse deux lectures : la plateforme appelle
le worker, ou elle dépose une tâche en file que le worker prend comme les autres. La première
suppose un worker joignable et donc nommé, ce qui contredit l'absence d'affinité de WF-ARC-0080 ;
la seconde est cohérente avec WF-ARC-0090, où toute tâche vient de la file.

Le flux TFX-10 hérite de l'ambiguïté : sa destination est « Worker », alors que dans la seconde
lecture la destination est Redis.

**Proposition.** Trancher pour la file. PBS-5.3 : « … déclenchées par la plateforme, qui dépose la
tâche en file à l'heure convenue ; le worker la prend comme les autres. » Et TFX-10 :
« Plateforme | Redis | Dépôt en file des tâches planifiées | Secret de la plateforme ».

**Statut.** intégré

---

## C-081 — Coquilles et formes

- **gravité** : mineur
- **emplacement** : §4.2.1.5 ; §4.3.2, TFX-09 ; §1.3.1
- **citation** : « une installation sur une machine seule. . **PBS-5.2 Chaîne CI/CD** »

**Constat.**
- §4.2.1.5 : un point et un espace en trop entre la fin de PBS-5.1 et le début de PBS-5.2.
- §4.3.2, TFX-09 : « http, point /metrics » en minuscules, quand les neuf autres lignes écrivent
  les protocoles en capitales.
- §1.3.1 : l'exemple d'exigence sépare ses deux codes PBS par une barre oblique
  (« PBS-2.4.5 / PBS-3.5.1 ») ; les cent quatre-vingts exigences du document les séparent par une
  virgule, comme les codes FBS. L'exemple est le seul endroit où un lecteur va chercher la forme.

**Proposition.** Retirer le point en trop ; « HTTP, point /metrics » ; et dans l'exemple,
« PBS-2.4.5, PBS-3.5.1 ».

**Statut.** intégré

---

## C-082 — Un import confirmé s'applique-t-il quand les droits ont changé entre-temps ?

- **gravité** : majeur
- **emplacement** : §4.3.4, WF-ARC-0100 ; §3.1.4, WF-INTF-0080 ; WF-ADM-0110 ; WF-CYC-0100
- **citation** : « L'application, demandée depuis ce compte rendu, écrit en une seule transaction. » (WF-ARC-0100)

**Constat.** L'analyse et l'application sont séparées par la décision de l'utilisateur, donc par un
délai qui peut atteindre des heures (C-071 propose vingt-quatre). Entre les deux, une permission a
pu être retirée, un contributeur désinscrit, un projet passé à Terminé. Rien ne dit ce qui se
passe alors : un développeur qui vérifie les droits à l'analyse et applique sans revérifier est
dans son droit, et il aurait écrit dans un projet terminal, ce que WF-CYC-0100 interdit « quel que
soit le point d'entrée ».

C'est le même défaut que C-071 par une autre porte : deux moments séparés par un long délai, et
rien qui dise ce qui arrive si le monde change entre les deux. Le cas n'est pas théorique — c'est
même le seul chemin d'écriture du produit qui ne soit pas synchrone.

**Proposition.** Ajouter au corps de WF-ARC-0100 : « L'application d'un import revérifie, au
moment où elle s'exécute, la permission et la qualité de contributeur de l'utilisateur qui l'a
demandée, ainsi que l'état du projet : un import confirmé n'est pas appliqué si l'une de ces
conditions a cessé d'être vraie depuis l'analyse. » Et à sa Vérif : « Un import confirmé par un
utilisateur dont la permission est retirée avant l'exécution n'est pas appliqué, et le refus nomme
la condition manquante. Il en va de même si le projet est passé dans un état terminal entre-temps. »

**Statut.** intégré

---

## Ce que la revue ne signale pas, et pourquoi

- **Le vocabulaire technique** — worker, noyau métier, file de tâches, empaquetage, identifiant de
  lignée, régime de données — n'est pas au glossaire. C'est volontaire : l'annexe A définit les
  objets métier que les exigences manipulent, et l'ajouter au glossaire mélangerait deux
  vocabulaires. Les acronymes, eux, relèvent du §1.2 (C-067).
- **Le choix de Redis, de Next.js, de FastAPI** : ce sont des choix de conception, que la revue
  ne discute pas.
- **La page draw.io « PBS »** est vide, la figure vient du texte alternatif Word. Le build le
  signale déjà ; ce n'est pas un défaut de la spécification.
