# Règles de codage — SQL et migrations

Pour la base du service (PostgreSQL), ses tables, ses requêtes et ses migrations. Ce fichier
complète le [guide](README.md), qui décrit l'écriture d'une migration (« Migrations »), et les
règles de [Python](python.md), qui disent comment le code parle à la base. Il ne recopie ni la
spécification (§4.4.1, WF-DAT-0060 à WF-DAT-0140), ni les décisions de la conception d'EP-03
(« Tables et migrations ») : il y renvoie.

Une règle qu'un outil contrôle nomme son contrôle. Une règle que rien ne contrôle le dit :
c'est la revue qui la tient, et l'agent de revue cherche nommément les défauts de la dernière
section.

## Ce que les outils tiennent

| Règle | Où | Contrôle |
|---|---|---|
| Les contraintes portent le nom que la convention leur donne, déclarée une fois | `NAMING_CONVENTION` de `waterfall.platform.database` | le test de `tests/test_migrations.py` qui migre une base, en crée une seconde par `Base.metadata.create_all`, et compare dans le catalogue de PostgreSQL les contraintes (`pg_constraint`, noms et définitions), les index et les colonnes (type, nullité, défaut du serveur), puis les colonnes, clés et index par `compare_metadata` |
| Les migrations forment une chaîne, appliquée une fois, dont chaque descente défait sa montée | `backend/src/waterfall/migrations/` | `make test-back` (`tests/test_migrations.py`) |
| L'image de PostgreSQL des tests est celle de la plateforme de service, à la même empreinte | `back.yml`, `compose.service.yaml` | `tests/test_platform_images.py` |
| Le SQL est du PostgreSQL : les tests tournent sur lui | `WATERFALL_TEST_DATABASE_URL` | `make test-back` ; sans base, les tests de base échouent en le disant |
| Un SQL construit par concaténation ou par gabarit de chaîne | règle `S608` de Ruff | `make lint-back` |

## Règles

### Nommage

- Les tables et les colonnes sont en anglais, en `snake_case`, au singulier pour une table
  (`user_account`, `installation`) : le nom d'un objet du domaine est celui du tableau de
  correspondance du §4.4.1.
- Une clé étrangère porte le nom de ce qu'elle désigne, suffixé `_id` (`org_node_id`) ; la
  clé de l'auteur d'une ligne fait exception, `created_by` et `updated_by`, qui portent
  l'auteur et non son identifiant.
- Une association de deux tables se nomme d'après les deux (`user_access_role`) et n'a pas
  d'identifiant propre : sa clé primaire est la paire.
- Une contrainte reçoit son nom de la convention (`pk_<table>`, `fk_<table>_<colonne>_<table
  désignée>`, `uq_<table>_<colonne>`, `ck_<table>_<nom>`, `ix_<table>_<colonne>`) ; on ne
  nomme à la main que la partie `<nom>` d'une contrainte de vérification, par ce qu'elle
  garantit (`state_known`, `avatar_size`), et un index d'expression, que la convention ne
  sait pas nommer (`uq_user_account_email_lower`).

*Pourquoi* : un nom prévisible permet à une migration de défaire une contrainte sans la
chercher, et à un test de dire laquelle a refusé. *Contrôle* : le test qui compare les
migrations aux tables du code ; le reste, la revue.

### Types

- Un montant, une quantité, un taux, une durée mesurée — toute grandeur — est un `numeric` à
  la précision de la colonne, **jamais** un `float`, un `real` ni un `double precision`
  (WF-DAT-0100). Côté Python, c'est un `Decimal`.
- Un horodatage est un `timestamptz`, conservé en temps universel : la session de la
  connexion est en UTC (`options=-c timezone=UTC`, `create_database_engine`), et le type
  `UtcDateTime` de `waterfall.platform.database` refuse un instant sans fuseau.
- Une date de planning est un `date`, sans heure ni fuseau (WF-DAT-0100).
- Un identifiant est un `uuid` de version 7, engendré par le service (`new_id()` de
  `waterfall.platform.identifiers`), **sans défaut dans la base** : jamais un entier ni une
  séquence, qu'une URL laisserait deviner (WF-DAT-0060).
- Un texte est un `text`, borné par une contrainte de vérification quand le contrat le
  borne (`char_length(last_name) BETWEEN 1 AND 100`), pas par un `varchar(n)`.
- Une énumération est un `text` avec une contrainte de vérification, pas un type `enum` de
  PostgreSQL : ajouter une valeur est alors une migration ordinaire, et la retirer aussi.
- Un document JSON (`jsonb`) ne porte que ce que la base n'a pas à contraindre ni à joindre.

*Pourquoi* : `0,10` additionné dix fois doit donner exactement `1,00`, une tâche du 30 juin
doit rester au 30 juin sur tout poste. *Contrôle* : la règle `DTZ` de Ruff pour les dates
sans fuseau, les tests de WF-DAT-0060 et WF-DAT-0100 pour les identifiants et les instants ;
le choix du type d'une grandeur, la revue.

### Contraintes déclarées

Ce que la base peut garantir, elle le garantit, avant toute règle des services (WF-DAT-0090) :

- une clé primaire sur chaque table ;
- une contrainte `NOT NULL` sur chaque colonne qui ne peut pas manquer — une colonne
  nullable se justifie dans la conception ;
- une unicité par un index ou une contrainte unique, **sans égard à la casse** pour une adresse
  (`lower(email)`) ;
- un état, une origine, une nature, par une contrainte de vérification qui énumère les valeurs ;
- une borne, par une contrainte de vérification (`octet_length(avatar) <= 8388608`) ;
- une ligne unique, par une clé constante vérifiée (`installation` : `id = 1`).

Un service qui vérifie la même règle ne la remplace pas : il la dit avec un code, la base la
tient. Un test écrit la ligne qui l'enfreint **en passant autour du service** et attend le
nom de la contrainte qui la refuse.

*Contrôle* : un test par contrainte, qui cite l'exigence (`tests/test_database_constraints.py`).

### Les clés étrangères refusent par défaut

Toute relation entre deux tables est une clé étrangère déclarée, en `ON DELETE RESTRICT` et
`ON UPDATE NO ACTION` — le refus. Une suppression en cascade est une décision de la
conception de l'EPIC, écrite dans sa table de tables, avec les lignes qu'elle entraîne et
rien d'autre ; une relation sans clé étrangère n'existe pas (WF-DAT-0090).

*Pourquoi* : une cascade qu'on n'a pas décidée efface en silence ce qu'une autre table
conservait. *Contrôle* : le test qui lit `pg_constraint` et refuse tout autre mode que le
refus ; la revue pour une cascade décidée.

### Ni suppression physique, ni mise à jour de ce qu'on garde

Les tables du régime « plateforme » (§4.4.1) ne perdent aucune ligne : un compte est
désactivé, un rôle marqué supprimé (WF-DAT-0080). Le module qui les possède n'offre aucune
fonction qui les supprime, et les clés étrangères en refus protègent les lignes référencées.
Une table d'association qui ne porte que ses deux clés se supprime ligne à ligne.

*Contrôle* : les tests de WF-DAT-0080 ; la revue.

### Migrations : deux temps, et chacune compatible avec le code voisin

Chaque migration est compatible avec le code qui la précède et celui qui la suit
(WF-DAT-0140) : l'ancien code tourne sur le nouveau schéma, le nouveau sur l'ancien le temps
d'une mise à jour. Donc :

1. **Ajouter, puis retirer.** Une colonne, une table ou une contrainte s'ajoute dans une
   migration, en acceptant l'absence de valeur ; le code qui la remplit et la lit suit ; une
   migration **ultérieure**, dans une version suivante, impose le `NOT NULL` ou retire l'ancienne
   colonne.
2. **Renommer, c'est ajouter, copier, puis retirer** : jamais un `RENAME` que l'ancien code
   ne connaît pas.
3. **Une donnée change dans sa propre migration**, séparée de celle du schéma, avec sa
   descente quand elle est possible.
4. **Une migration appliquée ne se modifie pas** : on en écrit une nouvelle. Le journal de
   la chaîne est l'histoire de la base de chaque installation.
5. **Chaque migration a sa descente**, miroir de la montée, qui défait ce que la montée a
   fait tant que rien d'écrit depuis n'en dépend ; une migration qui perd des données le dit
   dans la docstring de sa descente. La descente sert aux tests (celui qui la rejoue) et au
   poste de développement, jamais à une installation : la spécification veut que « le retour
   arrière porte sur le code, jamais sur le schéma : une migration ne se défait pas »
   (`docs/spec/waterfall-spec.md`, §4.5.3), et le retour arrière d'une installation ne touche
   que le code.
6. **Un verrou long se prévoit** : un index sur une grande table se crée `CONCURRENTLY`, hors
   de la transaction d'une migration ; une contrainte se pose `NOT VALID` puis se valide à part.
7. **Une migration écrite à la main**, relue comme le code ; l'autogénération d'Alembic
   produit un brouillon qu'on relit ligne à ligne, jamais une migration validée telle quelle.

*Pourquoi* : une mise à jour sans interruption (WF-DAT-0140) ne tient que si deux versions
voisines du code partagent un schéma. *Contrôle* : `tests/test_migrations.py` pour la chaîne,
la descente et l'accord avec les tables du code ; la compatibilité avec le code voisin, la
revue.

### Le SQL en texte ne nomme pas la table d'un autre module

Une requête écrite en texte (`text("…")`) n'emploie que les tables du module qui l'écrit. Pour
lire ou écrire une table d'un autre module, on passe par son `interface` : le module, pas son
voisin, choisit comment sa table se lit. L'analyse des imports ne voit pas un nom de table dans
une chaîne ; c'est la revue qui le cherche, dans le diff et dans le code voisin.

Une jointure entre modules se fait en deux lectures, ou par une opération que l'interface du
module propriétaire offre. Une migration, elle, voit toute la base : c'est le seul endroit où
le nom d'une table d'un autre module peut figurer.

*Pourquoi* : WF-ARC-0010 veut qu'un module s'extraie en service sans réécrire ses voisins.
*Contrôle* : la revue.

### Verrous

- Une écriture qui dépend de l'état d'une ligne partagée la verrouille **avant** de la lire
  (`SELECT … FOR UPDATE`), relit sous le verrou l'objet déjà chargé, et ne fait aucun
  traitement lent verrou tenu (`python.md`, « Une transaction lit sous le verrou qu'elle
  tient »).
- Une règle qui porte sur un ensemble de lignes — le dernier administrateur — prend un verrou
  consultatif de transaction (`pg_advisory_xact_lock`), toujours le même pour la même règle.
- Une modification qui porte un `lock_version` le teste **dans l'écriture même** :
  `UPDATE … WHERE id = :id AND lock_version = :lu RETURNING …`, qui n'écrit rien si la version
  n'est plus la bonne (412) — jamais une lecture suivie d'une comparaison en Python.
- Les migrations d'une même base s'appliquent l'une après l'autre : l'environnement d'Alembic
  prend un verrou consultatif de session, pour que deux instances qui démarrent ensemble
  n'appliquent pas la même migration deux fois.

*Contrôle* : la revue, qui vérifie aussi les routes sœurs de celle modifiée ; un test de
concurrence pour chaque règle d'ensemble.

## Défauts déjà rencontrés

1. **Colonne sans contrainte.** L'état, l'origine ou l'unicité d'une valeur n'est vérifié que
   par le service : une écriture qui le contourne — un import, une migration de données — la
   viole sans être refusée.
2. **Unicité sensible à la casse.** Deux adresses qui ne diffèrent que par la casse passent
   un index unique sur la colonne brute.
3. **Cascade non décidée.** Une clé étrangère laissée à `ON DELETE CASCADE` par un outil
   efface plus que prévu.
4. **`float` pour une grandeur.** Un montant stocké en `double precision` ne s'additionne pas
   exactement.
5. **Instant sans fuseau.** Un `timestamp` sans fuseau est lu comme le temps local de chacun.
6. **Identifiant engendré par la base.** Il n'est connu qu'après l'insertion, et une séquence
   se devine dans une URL.
7. **Migration qui défait ce qu'une version voisine emploie.** Une colonne retirée, ou rendue
   `NOT NULL`, dans la même version que le code qui cesse de l'employer.
8. **Descente qui n'est pas le miroir de la montée**, ou qui échoue sur PostgreSQL parce qu'un
   test ne l'a jamais jouée.
9. **Version testée en Python.** Un `lock_version` lu, puis comparé dans le code : une écriture
   concurrente passe entre la lecture et l'écriture.
10. **Requête en texte qui nomme la table d'un autre module.**
