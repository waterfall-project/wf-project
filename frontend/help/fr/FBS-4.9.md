# Cycle de vie du projet

## Ce que montre l’écran

Où en est le projet dans son cycle de vie, et ce qui le fera avancer. Un projet a six états, et aucun autre : **Créé**, **Chiffrage**, **En cours**, **Terminé**, **Perdu** et **Abandonné**. Les passages à Chiffrage et à En cours suivent des faits : la première révision créée mène à Chiffrage ; une révision de référence désignée et un code projet renseigné, dans un ordre ou dans l’autre, mènent à En cours. Ils ne se commandent jamais. Les trois états terminaux sont irréversibles : le projet et toutes ses données — plannings, devis, restes à engager, coûts réels — y passent en lecture seule, et restent entièrement consultables et exportables.

Sous le titre, l’état du projet. Puis, de haut en bas :

- le **Prochain état**, pour un projet qui n’a pas atteint En cours : l’**État visé**, le **Déclencheur** et, une par une, les **Conditions restantes**. Un projet en cours le dit : seules ses sorties restent ; un projet clos, qu’aucun état ne le suit ;
- l’**Historique des états** : chaque transition, sa **Date**, la **Transition**, son auteur (**Par**) et le **Motif** d’une sortie. Rien n’y est modifiable.

## Ses commandes

En tête de l’écran, les trois sorties, les seules transitions que l’on commande, chacune disponible ou nommant la condition qui lui manque :

- **Terminer le projet**, depuis En cours (« projet en cours ») ;
- **Déclarer le projet perdu**, depuis Chiffrage (« projet en chiffrage ») ;
- **Abandonner le projet**, depuis tout état non terminal (« projet non clos »).

Chacune s’applique après une confirmation qui dit son caractère définitif et ce qu’elle rend non modifiable, et qui propose un **Motif (facultatif)**, conservé par la transition. Quand le projet porte une révision en cours, la confirmation demande, sous **Sort de la révision en cours**, de la marquer, sous un **Nom de version** et une **Description (facultative)**, ou de l’abandonner, sans retour ; la sortie ne s’applique qu’avec ce choix, dans la même opération. **Confirmer la sortie** l’applique ; **Annuler** n’applique rien.

## Ses colonnes et ses valeurs calculées

Le prochain état, son déclencheur et ses conditions sont ceux que le serveur calcule, lus sans rien tenter. Les dates de l’historique sont celles du jour où chaque transition s’est produite.

## Les gestes au clavier

- `Tab` parcourt les sorties, puis l’historique ; une sortie indisponible reste atteignable, et sa condition se lit dans sa description.
- Dans la confirmation, qui s’ouvre dans la page, `Tab` parcourt le sort de la révision, ses champs et les commandes ; **Annuler** la referme sans rien appliquer.
- `F1` ouvre cette aide.

## Voir aussi

- [La gestion des révisions](FBS-4.1.md), où se crée la première révision et se désigne la référence ;
- [les paramètres du projet](FBS-4.2.md), où se renseigne le code projet ;
- [la liste des projets](FBS-4.md), filtrée par état ;
- la notion : [les révisions](notions/revisions.md).
