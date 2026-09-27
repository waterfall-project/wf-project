---
revue_du: 2026-09-27
sur: waterfall-spec.md généré le 2026-09-27 (commit f454d13)
revue_par: Claude Opus 5
perimetre: >-
  ce que l'écriture du contrat d'interface (docs/api) a révélé de la spécification.
  Périmètre involontaire : ces constats ne viennent pas d'une relecture mais de la
  tentative d'écrire 150 opérations sans rien inventer.
---

# Revue du 2026-09-27 — ce que le contrat a révélé

## Suivi des revues précédentes

Les huit revues précédentes sont soldées ; aucun constat n'est resté « à traiter ».

## D'où viennent ces constats

Écrire un contrat OpenAPI force à nommer chaque champ, chaque énumération et chaque erreur.
On ne peut pas y écrire « le cas échéant ». Sur cent cinquante opérations, sept endroits ont
demandé une décision que la spécification ne portait pas : les voici, avec ce que le contrat
a supposé. Trois sont majeurs, et le premier touche un objet central du modèle.

Le reste s'est écrit sans trou : le contrat cite cent soixante-seize des deux cent deux
exigences, et les vingt-six restantes n'ont pas de surface d'interface — architecture
interne, exploitation, migrations, invariants d'interface, chaîne de vérification.

## Constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-083 | majeur | §3.2.3, §3.4.5.1 | La structure de coûts n'a pas d'exigence : sa composition n'est que dans le glossaire | intégré |
| C-084 | majeur | §3.4.5.1, WF-REV-0050 | La fusion d'un différentiel ne dit pas qu'elle marque la révision, ni d'où vient le nom de version | intégré |
| C-085 | majeur | §3.4.2.1, WF-ADM-0140 | Le premier mot de passe d'un compte local créé par un administrateur n'est pas prévu | intégré |
| C-086 | mineur | §3.4.5.3, WF-PLA-0130 | Trois valeurs calculées d'une tâche manquent à ses attributs | intégré |
| C-087 | mineur | §3.4.2.2, §3.6 | Rien ne dit que ses permissions sont connues de l'utilisateur, alors que WF-IHM-0090 le suppose | intégré |
| C-088 | mineur | §3.4.3.2, WF-PTF-0060 | Le seuil de sous-charge : préférence d'affichage ou paramètre de vue ? | intégré |
| C-089 | mineur | §4.6.1, WF-SEC-0030 | Le journal s'intitule « actions irréversibles » et contient une action réversible | intégré |

---

## C-083 — La structure de coûts n'a pas d'exigence : sa composition n'est que dans le glossaire

- **gravité** : majeur
- **emplacement** : §3.2.3 ; §3.4.5.1 ; annexe A, entrée « Structure de coûts »
- **citation** : « Une révision porte une structure principale, et le cas échéant des différentiels et des devis de risques. » (glossaire)

**Constat.** Tous les objets centraux du modèle ont leur exigence d'attributs : la tâche
(WF-PLA-0130), la ligne de devis (WF-DEV-0020), la révision (WF-REV-0090), le projet
(WF-PRJ-0080), le risque (WF-RIS-0010), la ligne de coût (WF-CRE-0010). La **structure de
coûts** n'en a pas. Ce qu'on sait d'elle est réparti entre le §3.2.3, qui la décrit en
prose, et le glossaire, qui énonce la règle de composition citée ci-dessus.

Or c'est la règle dont tout dépend : le contrat a dû décider que les nœuds vivent sous une
structure, et donc écrire `/projects/{p}/revisions/{r}/structures/{s}/nodes`. Trois
questions restaient sans réponse, que le contrat a tranchées seul :

- **qui crée un différentiel, et quand ?** Le glossaire dit qu'un avenant « se prépare comme
  un différentiel » ; aucune exigence ne dit que l'utilisateur en crée un, ni dans quelle
  révision ;
- **combien peut-il en exister à la fois ?** Deux avenants préparés en parallèle sont-ils
  permis ?
- **le devis propre d'un risque est-il une structure de la révision en cours seulement, ou
  de chaque révision ?** WF-RIS-0030 dit que « chaque révision en fige une version », ce qui
  suggère la seconde réponse, mais ne la donne pas.

Le document s'est donné pour règle qu'un concept a un propriétaire, et que les attributs
sont portés par une exigence. C'est le seul objet du modèle qui y échappe.

**Proposition.** Une exigence dans le §3.4.5.1, à la suite de WF-REV-0090 :

> **WF-REV-0100-A — Structures de coûts d'une révision.** Une révision porte une structure
> de coûts principale, et le cas échéant des structures différentielles et une structure
> propre par risque. Chaque structure porte une nature — principale, différentielle, ou
> devis de risque —, un libellé, et l'arbre de tâches et de lignes qui la compose. La
> structure principale existe dès la création de la révision. Une structure différentielle
> est créée par un utilisateur habilité pour préparer un avenant ; plusieurs peuvent
> coexister, et chacune est fusionnée ou abandonnée indépendamment. Une structure propre de
> risque existe tant que le risque existe, et chaque révision en fige une version.
>
> Motif : c'est la seule règle de composition du modèle qui ne figurait que dans le
> glossaire, alors que tout en dépend — ce qu'un import modifie, ce qu'une fusion consomme,
> et ce qu'une révision copie. Permettre plusieurs différentiels à la fois est ce qui rend
> possible la préparation de deux avenants en parallèle, cas courant sur un projet long.
>
> Vérif : une révision nouvellement créée comporte une structure principale et aucune autre.
> Deux structures différentielles coexistent dans une même révision, et la fusion de l'une
> laisse l'autre intacte. Un risque déclaré ajoute une structure propre, présente dans
> chaque révision marquée postérieure.

**Statut.** intégré

---

## C-084 — La fusion d'un différentiel ne dit pas qu'elle marque la révision, ni d'où vient le nom de version

- **gravité** : majeur
- **emplacement** : §3.4.5.1, WF-REV-0050 ; §3.4.5.6.2, WF-RIS-0060
- **citation** : « La révision marquée qui en résulte devient la référence. » (WF-REV-0050)

**Constat.** « La révision marquée qui en résulte » suppose une révision marquée, mais
l'exigence ne dit pas laquelle ni comment elle apparaît. Deux lectures, et elles ne
produisent pas le même produit :

- la fusion s'applique à la révision **en cours**, puis la marque — ce que suggère
  « les montants réestimés de toutes les lignes sont conservés », puisque ces réestimations
  ne vivent que dans la révision en cours ;
- la fusion produit une **révision nouvelle**, laissant la révision en cours de côté — et
  alors on ne sait pas ce que devient cette dernière.

Le contrat a retenu la première, ce qui a une conséquence immédiate : le marquage exige un
nom de version (WF-REV-0020, unique dans le projet), donc l'opération de fusion doit en
recevoir un. C'est pourquoi `StructureMerge` et `RiskOccurrence` portent un `version_name`
que nulle exigence ne réclame.

**Proposition.** Compléter le corps de WF-REV-0050, avant la dernière phrase :

> La fusion s'applique à la révision en cours et la marque dans la même opération ; elle
> exige à ce titre un nom de version, comme tout marquage (WF-REV-0020). Lorsque le projet
> ne comporte pas de révision en cours, elle en crée une au préalable.

Et ajouter à sa Vérif : « La fusion demande un nom de version et la révision produite porte
ce nom. Après fusion, le projet ne comporte plus de révision en cours. » WF-RIS-0060, qui
renvoie à WF-REV-0050, n'a alors rien à changer.

**Statut.** intégré

---

## C-085 — Le premier mot de passe d'un compte local créé par un administrateur n'est pas prévu

- **gravité** : majeur
- **emplacement** : §3.4.2.1, WF-ADM-0050 et WF-ADM-0140 ; §4.5.2, WF-EXP-0020
- **citation** : « Un utilisateur réinitialise son mot de passe par un lien envoyé à son adresse électronique, valable une heure et à usage unique. » (WF-ADM-0140)

**Constat.** WF-ADM-0050 crée un compte avec un nom, un prénom et une adresse.
WF-ADM-0140 décrit la politique de mot de passe et la réinitialisation. Aucune des deux ne
dit **comment un compte local nouvellement créé obtient son premier mot de passe**. Trois
voies sont possibles, et elles n'ont pas les mêmes conséquences de sécurité : un mot de
passe saisi par l'administrateur, qui le connaît donc ; un mot de passe engendré et
transmis, qui circule ; ou un lien d'activation envoyé à l'adresse du compte, qui ne fait
connaître le mot de passe à personne d'autre que son porteur.

WF-EXP-0020 a déjà tranché le cas du premier administrateur — « dont le mot de passe est
fixé à sa première connexion » — et pour la bonne raison, énoncée dans son Motif : éviter
qu'un mot de passe d'installation traîne dans une procédure. La même raison vaut pour tous
les comptes.

**Proposition.** Ajouter au corps de WF-ADM-0140 :

> Un compte local nouvellement créé n'a pas de mot de passe : son porteur en fixe un par le
> même lien que la réinitialisation, envoyé à son adresse à la création du compte. Un compte
> sans mot de passe ne peut pas se connecter, et le lien peut être renvoyé par un
> utilisateur habilité.

Et à sa Vérif : « Un compte créé par un administrateur ne peut pas se connecter avant que
son porteur n'ait fixé son mot de passe par le lien reçu. Aucun écran ne permet à un
administrateur de saisir le mot de passe d'un autre. »

**Statut.** intégré

---

## C-086 — Trois valeurs calculées d'une tâche manquent à ses attributs

- **gravité** : mineur
- **emplacement** : §3.4.5.3, WF-PLA-0130 ; WF-PLA-0100 ; §3.4.5.8.3, WF-IND-0060
- **citation** : « Une tâche porte un libellé, une description facultative, une durée, une date de début, une date de fin, un mode de planification et un état d'avancement. » (WF-PLA-0130)

**Constat.** L'énumération est complète pour ce qui se saisit, et muette sur trois valeurs
calculées que d'autres exigences réclament : l'**appartenance au chemin critique** et la
**marge totale** (WF-PLA-0100), et l'**avancement physique** d'une tâche récapitulative
(WF-IND-0060). Le contrat les expose comme attributs de la tâche, puisque c'est là qu'une
grille les lit ; WF-IHM-0030 suppose d'ailleurs qu'elles existent et se distinguent des
valeurs saisies.

**Proposition.** Ajouter à la fin du corps de WF-PLA-0130 :

> Elle porte en outre trois valeurs calculées, qui ne sont pas saisissables : sa marge
> totale et son appartenance au chemin critique (WF-PLA-0100), et, pour une récapitulative,
> son avancement physique (WF-IND-0060).

**Statut.** intégré

---

## C-087 — Rien ne dit que ses permissions sont connues de l'utilisateur

- **gravité** : mineur
- **emplacement** : §3.4.2.2, WF-ADM-0110 ; §3.6, WF-IHM-0090
- **citation** : « une commande que les habilitations de l'utilisateur ne permettent pas n'est pas présentée » (WF-IHM-0090)

**Constat.** Pour ne pas présenter une commande, le front doit savoir que l'utilisateur n'a
pas la permission correspondante. Aucune exigence ne dit que ses permissions effectives lui
sont communiquées ; WF-ADM-0110 décrit l'évaluation d'une action, pas la connaissance
préalable. Le contrat renvoie donc les permissions avec la session, ce qu'aucune exigence
n'impose et qu'un développeur pourrait tout aussi bien ne pas faire — en découvrant chaque
refus par un essai, ce qui donne une interface qui clignote.

**Proposition.** Ajouter au corps de WF-ADM-0110 :

> Les permissions effectives d'un utilisateur lui sont connues, de sorte que l'interface
> puisse ne pas présenter ce qu'il n'a pas le droit de faire (WF-IHM-0090). Les connaître ne
> dispense d'aucune évaluation : chaque action est évaluée au moment où elle est demandée.

**Statut.** intégré

---

## C-088 — Le seuil de sous-charge : préférence d'affichage ou paramètre de vue ?

- **gravité** : mineur
- **emplacement** : §3.4.3.2, WF-PTF-0060 ; §3.4.2.1, WF-ADM-0040
- **citation** : « en signalant les mois où il dépasse 100 % et ceux où il est inférieur à un seuil choisi par l'utilisateur » (WF-PTF-0060)

**Constat.** « Choisi par l'utilisateur » ne dit pas s'il s'agit d'un réglage conservé —
donc d'une préférence d'affichage au sens de WF-ADM-0040 — ou d'un paramètre de la vue,
choisi à chaque consultation. Le contrat en a fait un paramètre de requête, ce qui est le
choix le moins engageant, mais un développeur qui lirait « choisi par l'utilisateur » comme
une préférence l'écrirait ailleurs. Le même flou vaut pour l'horizon de la vue.

**Proposition.** Préciser dans WF-PTF-0060 : « … inférieur à un seuil que l'utilisateur
choisit à la consultation, comme l'horizon de la vue ; ni l'un ni l'autre n'est conservé. »
Ou, si le réglage doit être conservé, l'ajouter aux préférences d'affichage de WF-ADM-0040.

**Statut.** intégré

---

## C-089 — Le journal s'intitule « actions irréversibles » et contient une action réversible

- **gravité** : mineur
- **emplacement** : §4.6.1, WF-SEC-0030
- **citation** : titre « Journal d'audit des actions irréversibles » ; corps « l'exclusion ou la réintégration d'une ligne de coût »

**Constat.** Le corps dit « chaque action irréversible **ou structurante** », ce qui couvre
le cas ; le titre, lui, ne parle que d'irréversibilité, et l'exclusion d'une ligne de coût
est réversible par construction (WF-CRE-0030). WF-ADM-0100 emploie la même formule complète
pour le catalogue des permissions. C'est le titre qui est en retard.

**Proposition.** « Journal d'audit des actions irréversibles ou structurantes ».

**Statut.** intégré
