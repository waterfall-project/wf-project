# Règles de codage — Python

Pour le back (`backend/`) et les outils du dépôt (`tools/`, `docs/*/tools/`). Ce fichier
complète le [guide](README.md) : il dit comment s'écrit le Python ici. Il ne recopie ni la
spécification, ni le contrat, ni les jeux de règles des outils ; il y renvoie.

Une règle qu'un outil contrôle nomme son contrôle. Une règle que rien ne contrôle le dit :
c'est la revue qui la tient, et l'agent de revue cherche nommément les défauts de la
dernière section.

## Ce que les outils tiennent

Ces règles ne se recopient pas ici : leur texte fait foi, et il suffit de le lire.

| Jeu de règles | Où | Contrôle |
|---|---|---|
| Lint et format — toutes les règles de Ruff, chaque retrait avec sa raison | `ruff.toml` | `make lint-back`, `make lint-tools` |
| Typage strict, `# type: ignore` non honoré | `[tool.pyright]` de `backend/pyproject.toml` et `tools/pyproject.toml` | `make typecheck-back`, `make typecheck-tools` |
| Frontières du noyau | `[tool.importlinter]` de `backend/pyproject.toml` | `make imports-back` |
| Aucun commentaire d'exemption ; 1 000 lignes au plus | `tools/src/wftools/sources.py` | `make sources` |
| Couverture du code : 90 % des lignes, 85 % des branches | seuils dans `tools/src/wftools/codecoverage.py` ; mesure réglée par `[tool.coverage]` de `backend/pyproject.toml` | `make coverage-back` |

Une règle qui gêne se discute et se retire du jeu, avec sa raison ; elle ne se contourne
jamais dans le code.

## Règles de conception

### Le noyau calcule, il ne lit ni n'écrit

Un calcul du noyau — dates, montants, indicateurs, agrégations — est une fonction pure :
des valeurs en entrée, une valeur en sortie, ni base, ni réseau, ni horloge lue en cachette.
La date du jour se passe en argument.

*Pourquoi* : les exemples chiffrés du document sont des tests unitaires exécutés sans base
ni navigateur (WF-QUA-0020) ; un calcul qui lit la base ne se teste pas ainsi, et un calcul
qui lit l'horloge ne se rejoue pas. *Contrôle* : les tests d'exemples tournent sockets
fermées (`backend/tests/examples`) ; le reste, la revue.

### Un module parle aux autres par son interface

Ce qu'un module du noyau offre aux autres est dans son module `interface` ; ses tables, ses
requêtes et ses objets de persistance lui restent. Une requête SQL écrite en texte ne nomme
jamais la table d'un autre module.

*Pourquoi* : c'est ce qui garde possible l'extraction d'un module en service (WF-ARC-0010).
*Contrôle* : `make imports-back` pour les imports ; le SQL en texte, la revue — ses règles
viennent avec EP-03.

### Les grandeurs ont leur type, jamais un `float`

- Un montant, une quantité, un taux sont des `Decimal`, avec la précision de la colonne qui
  les porte ; ils voyagent en chaîne dans l'API (`Money`, `Decimal` du contrat).
- Une date de planning est une `date`, sans heure. Un horodatage est un `datetime` en temps
  universel, toujours conscient de son fuseau.
- Un identifiant est un UUID engendré par le serveur, jamais un entier ni une valeur venue
  du client.

*Pourquoi* : `0,10` additionné dix fois doit donner exactement `1,00` (WF-DAT-0100) ; un
identifiant séquentiel dans une URL se devine (WF-DAT-0060). *Contrôle* : Pyright pour les
types déclarés, la règle `DTZ` de Ruff pour les dates sans fuseau ; le choix du type, la
revue.

### Une erreur est un code, jamais une phrase

Une règle métier refusée lève une exception typée du noyau, qui porte un code machine et
ses paramètres. Seule l'API la traduit dans l'enveloppe d'erreur du contrat — `code`,
`status`, `params`, `fields`, `correlation_id` —, et le front en fait une phrase dans la
langue de l'utilisateur, avec l'identifiant de corrélation qui permet de suivre l'erreur
dans les journaux (WF-OBS-0020). Le statut suit le contrat : `404` quand la lecture est interdite, `403`
quand c'est l'écriture ou la qualité de contributeur, `409` pour un conflit d'état, `412`
pour un `lock_version` périmé.

*Pourquoi* : l'API ne localise rien (WF-ARC-0110), et une phrase ne se teste pas ;
le détail des statuts est dans `docs/api/DECISIONS.md`, « Session et erreurs ».
*Contrôle* : la comparaison des réponses au schéma, à partir d'EP-03 ; la revue.

### Ce que l'API lit, ce qu'elle écrit

Les schémas Pydantic suivent ceux du contrat : un de lecture, un d'écriture, un de
modification, jamais le même pour les trois. Une valeur calculée n'apparaît que dans le
schéma de lecture ; une valeur qui peut ne pas se calculer passe par l'enveloppe
`Computable`. Une modification porte le `lock_version` lu.

*Pourquoi* : un client ne doit pas pouvoir envoyer une valeur calculée (WF-IHM-0030), ni
écraser une modification qu'il n'a pas vue — le contrat rattache `lock_version` à
WF-IHM-0110 ; `docs/api/DECISIONS.md`, « Calculé contre saisi ». *Contrôle* : le contrat,
puis la comparaison des réponses au schéma (EP-03).

### Ce qui est long part en tâche de fond

Une opération que le contrat déclare longue — marquage, fusion, import, export,
sauvegarde — dépose une tâche et répond `202` avec sa référence ; le worker l'exécute. Elle
ne rend jamais son résultat dans la réponse.

*Pourquoi* : WF-ARC-0090. *Contrôle* : le contrat ; la revue.

### Une transaction lit sous le verrou qu'elle tient

Quand une écriture dépend de l'état d'une ligne partagée — l'état d'un projet, la
révision courante —, la ligne se verrouille *avant* d'être lue, et l'objet déjà chargé se
relit sous le verrou. Aucun traitement lent — lecture de fichier, analyse — ne se fait
verrou tenu : on prépare d'abord, on verrouille ensuite. La réponse se construit avant de
valider la transaction.

*Pourquoi* : sans cela, deux écritures concurrentes décident chacune sur un état périmé ;
c'est le défaut le plus souvent trouvé dans le code qui a précédé celui-ci. *Contrôle* : la
revue, qui vérifie aussi les routes sœurs de celle modifiée.

### Journaliser

Les services écrivent des journaux structurés, par structlog, jamais par `print`. Chaque
enregistrement porte l'identifiant de corrélation, engendré à l'entrée de la plateforme et
transmis au worker par la tâche qu'il déclenche, l'auteur de l'action, le projet concerné
s'il y en a un, et la gravité. Aucun journal ne contient de mot de passe, de jeton de
session ni de secret : un objet qui en porte ne se journalise pas entier.

*Pourquoi* : WF-OBS-0020, que la roadmap fait commencer en EP-03 (#51), pour que le premier
code l'applique au lieu d'être repris en EP-13. *Contrôle* : la règle `T201` de Ruff refuse `print` dans le back ;
les champs et l'absence de secrets, la revue, puis la recherche des secrets de WF-OBS-0020.

### Les tests

- Un test cite l'exigence dont il éprouve le Vérif (`@pytest.mark.requirement`), et son nom
  dit ce qu'il vérifie : `test_a_module_that_reads_the_tables_of_another_is_rejected`.
- Un test d'exemple chiffré reprend les entrées et la valeur de sa phrase, par sa fixture ;
  il ne recalcule pas l'attendu.
- Un test vérifie quelque chose : une assertion sur le résultat, pas le simple fait qu'une
  ligne s'exécute. Une branche d'erreur a son test, comme le cas nominal.
- Pas de base de données dans un test du noyau ; la base réelle, PostgreSQL, pour un test
  d'intégration — jamais une autre base à sa place.

*Pourquoi* : WF-QUA-0010, WF-QUA-0020 ; une base de substitution accepte ce que PostgreSQL
refuse. *Contrôle* : `make requirements`, `make coverage-back` ; la valeur d'une assertion,
la revue.

## Défauts déjà rencontrés

Chacun a été trouvé dans du code réel, souvent par une revue automatique, et se
reproduira. L'agent de revue les cherche nommément, dans le diff et dans le code voisin qui
partage le même invariant. Un défaut trouvé en revue et qui peut revenir s'ajoute ici.

1. **Lecture avant le verrou.** Une route lit une ligne, puis la verrouille, et décide sur
   ce qu'elle a lu : un écrivain concurrent a changé l'état entre les deux. Variante : le
   verrou est pris, mais l'objet déjà en mémoire n'est pas relu.
2. **Protocole de verrouillage appliqué à une route, pas à ses sœurs.** Le verrou est ajouté
   à la route modifiée ; celle qui crée ou supprime les mêmes lignes reste sans lui.
3. **Réponse construite après la validation.** La transaction est validée, puis la réponse
   relit la ligne : un autre écrivain a pu passer entre les deux, et la réponse décrit un
   état que cette requête n'a pas produit.
4. **Verrou tenu pendant un traitement lent.** Un fichier est lu et analysé verrou tenu, et
   tous les autres écrivains attendent.
5. **Erreur hors de l'enveloppe.** Une route laisse passer une exception de la plateforme,
   ou la validation automatique répond `422` là où le contrat promet `400` : le corps et le
   statut ne sont pas ceux du contrat.
6. **Contrainte qui ne contraint pas ce qu'elle dit.** `min_length=1` sur une liste d'entiers
   limite la longueur de la liste, pas chaque entier : une contrainte par élément se met
   sur le type de l'élément.
7. **Valeur dérivée recalculée sur un chemin, pas sur les autres.** Un total, une durée
   récapitulative, un indicateur est recalculé à la création, mais pas au déplacement ni à
   la suppression d'un enfant.
8. **Arithmétique de dates naïve.** Une durée calculée en jours de calendrier là où la règle
   veut des jours ouvrés du calendrier applicable : juste sur un cas simple, faux dès qu'un
   week-end ou un calendrier propre s'en mêle.
9. **Valeur comparée hors de son périmètre.** Une `position` n'a de sens que parmi les
   enfants d'un même parent ; la trier entre parents mélange des éléments sans rapport.
10. **Message qui ne dit pas la vraie cause.** Une vérification élargie à un nouveau cas
    garde le code d'erreur de l'ancien.
11. **Migration mal chaînée.** Deux migrations partent du même parent, une descente n'est
    pas le miroir de la montée, ou une migration ne s'applique pas sur PostgreSQL.
12. **Test qui passe sur les lignes sans rien vérifier.** Il exécute le code, fait monter la
    couverture, et n'affirme rien du résultat.
