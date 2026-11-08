# Le corpus de plannings MS Project (WF-QUA-0080)

Ce répertoire reçoit le corpus que WF-QUA-0080 exige : des plannings saisis dans MS Project
(2013 ou plus), enregistrés au format XML avec les dates que MS Project a calculées, et versionnés
avec le code. Il est fourni par l'auteur, avant le lot US-1430/L3 d'EP-06 (#2342) : pour chaque
fichier, un test donne au moteur de Waterfall les tâches, les liaisons, les calendriers de tâche et
les constantes du fichier, et vérifie qu'il calcule les mêmes dates de début et de fin ; un autre
test lit le manifeste et nomme tout cas du corps de WF-QUA-0080 qu'aucun fichier ne déclare
(conception d'EP-06, `docs/roadmap/EP-06-planification.md`, « Le format MS Project »).

Le schéma XSD de Microsoft n'est pas versionné : la variable `WATERFALL_MSPDI_SCHEMA_PATH` le
désigne (sur le poste de l'auteur, `$HOME/.local/share/waterfall/mspdi_pj15.xsd`), `make test-back`
la passe quand elle est dans l'environnement, et le test de validation d'un fichier exporté se
déclare non exécuté sans elle.

## Forme

- `NN-<cas>.xml` : un fichier par thème, enregistré par MS Project (« Enregistrer sous → XML »),
  tel quel, sans retouche à la main.
- `corpus.json` : le manifeste, écrit par l'auteur, un objet par fichier :

  ```json
  {
    "files": [
      {
        "file": "01-links-and-lags-days.xml",
        "cases": ["link_fs", "link_ss", "link_ff", "link_sf", "lag_positive_d", "lag_negative_d"],
        "project_start": "2026-03-02",
        "hours_per_day": 8,
        "hours_per_week": 40,
        "days_per_month": 20,
        "notes": "ce que le fichier éprouve, en une phrase"
      }
    ]
  }
  ```

  Les identifiants de `cases` sont ceux des tableaux ci-dessous ; le test des cas exige que chacun
  figure dans au moins un fichier.

## Réglages communs à tous les fichiers

Sans eux, les dates divergent pour une raison qui n'est pas la nôtre.

- Options → Planification : **nouvelles tâches planifiées automatiquement** (MS Project 2013 crée
  du manuel par défaut) ; **8 heures par jour, 40 par semaine, 20 jours par mois** ; début par
  défaut 08:00, fin 17:00 — sauf le fichier 10, qui éprouve d'autres constantes.
- Calendrier Standard **sans exception** — pas de jours fériés, Waterfall n'en connaît pas
  (WF-REF-0110) — : lundi à vendredi, 8:00–12:00 et 13:00–17:00.
- **Aucune ressource affectée**, sauf dans le fichier 09, qui éprouve qu'elles sont ignorées ; là,
  « La planification ignore les calendriers des ressources » coché sur chaque tâche affectée.
  Waterfall ne lit pas les ressources : les dates viennent des calendriers de tâche.
- Le calendrier d'une tâche se pose dans **Informations sur la tâche → Avancées → Calendrier** :
  c'est le seul calendrier que Waterfall lit.
- Pas de nivellement, pas de tâche fractionnée, pas de tâche répétitive, pas d'échéance, pas de
  « plusieurs chemins critiques », planification à partir du début du projet.
- Date de début du projet : un lundi — le **2 mars 2026**, celle du témoin, convient.
- Une description dans les **Notes** d'au moins une tâche par fichier (C-375 : la description
  d'une tâche voyage par ses notes).

Chronologies : rien à faire — celles de Waterfall n'existent pas dans MS Project, et la
« chronologie » de MS Project n'est pas écrite dans le XML. Ressources, coûts, avancement, champs
personnalisés : dans le fichier 09 seulement.

## Les fichiers

Dix fichiers petits, de 5 à 30 tâches ; un onzième pour l'import seul ; un douzième, plus gros,
facultatif.

| N° | Fichier | Cas | Contenu |
|---|---|---|---|
| 01 | `01-links-and-lags-days.xml` | `link_fs`, `link_ss`, `link_ff`, `link_sf`, `lag_positive_d`, `lag_negative_d` | ≈ 8 tâches automatiques de 1 à 5 j ; chaque type de liaison au moins une fois ; un décalage +2 j, une avance −1 j ; une tâche sans prédécesseur, qui commence à la date du projet |
| 02 | `02-lags-every-unit.xml` | `lag_min`, `lag_h`, `lag_w`, `lag_mo`, `lag_emin`, `lag_eh`, `lag_ed`, `lag_ew`, `lag_emo`, `lag_percent`, `lag_negative_w`, `lag_elapsed_over_weekend` | une chaîne où chaque liaison porte une unité : 30 min, 4 h, 1 sem, 1 m, 90 emin, 2 eh, 2 ej, 1 esem, 1 em, 50 %, et une avance en semaines ; et le cas critique : un prédécesseur qui finit **vendredi 17:00**, trois successeurs FD+2 ej, FD+2 eh, FD+2 j — le Vérif de WF-PLA-0160 attend lundi 8:00, lundi 8:00, mercredi 8:00 |
| 03 | `03-durations-every-unit.xml` | `duration_min`, `duration_h`, `duration_d`, `duration_w`, `duration_mo`, `duration_elapsed`, `sixteen_hours_standard` | des durées 90 min, 12 h, 2 j, 1 sem, 1 m, 3 ej, 36 eh ; « 2 j » vaut 16 h, « 1 sem » 40 h, « 1 m » 160 h ; une tâche de 16 h commencée lundi matin finit mardi |
| 04 | `04-calendars-uneven-days.xml` | `calendar_uneven`, `calendar_4x10`, `calendar_half_day`, `calendar_four_hours`, `task_calendar_chain` | trois calendriers de base en plus du Standard : « 4 × 10 » (lundi–jeudi 10 h, vendredi 0), « Vendredi court » (8/8/8/8/4), « Quatre heures » (4 h par jour) ; une tâche de 16 h sur chacun — sur « Quatre heures », elle finit jeudi — ; une chaîne qui change de calendrier d'une tâche à l'autre |
| 05 | `05-summaries-and-milestones.xml` | `summary`, `summary_nested`, `milestone`, `milestone_linked_ff`, `summary_single_milestone` | trois niveaux de récapitulatives ; des jalons de fin liés en FD ; un jalon avec un prédécesseur FF ; une récapitulative dont la seule subordonnée est un jalon |
| 06 | `06-manual-tasks.xml` | `manual`, `manual_with_auto_successor`, `manual_conflict_fs`, `manual_conflict_ss`, `manual_non_working_day`, `manual_summary` | des tâches manuelles datées ; un successeur automatique d'une manuelle ; une manuelle datée **avant** la fin calculée de son prédécesseur automatique (marge négative, conflit) ; une manuelle liée **DD** à un prédécesseur qui ne peut pas commencer avant elle ; une manuelle qui commence un **samedi** ; une récapitulative en mode manuel |
| 07 | `07-critical-path.xml` | `two_branches`, `float_equals_gap`, `summary_critical`, `summary_without_float` | deux branches parallèles de durées différentes vers un jalon commun : la longue critique, la courte avec une marge égale à l'écart ; une récapitulative dont une subordonnée est critique ; une récapitulative dont toutes les subordonnées sont manuelles, qui ne porte pas de marge |
| 08 | `08-constraints.xml` | `constraint_snet`, `constraint_mfo`, `constraint_fnlt` | une tâche « Début au plus tôt le », une « Doit finir le », une « Fin au plus tard le » : Waterfall les importe manuelles aux dates du fichier et les signale |
| 09 | `09-ignored-content.xml` | `resources_ignored`, `assignments_ignored`, `resource_calendar_ignored`, `progress_ignored`, `costs_ignored`, `custom_fields_ignored` | deux ressources, dont une avec un calendrier propre, affectées à des tâches avec « ignorer les calendriers des ressources » ; une tâche à 50 % d'avancement ; un coût fixe ; un champ personnalisé texte — le compte rendu nomme tout cela ignoré, et la tâche à 50 % est importée non démarrée |
| 10 | `10-other-constants.xml` | `constants_7_35_20` | 7 heures par jour, 35 par semaine, 20 jours par mois ; des durées en jours et semaines : importées avec les mêmes durées en heures, la différence signalée |
| 11 | `11-horizon-sixteen-years.xml` | `horizon_exceeded` | un planning de seize ans, rejeté au compte rendu (WF-PLA-0150) ; hors du test de datation — le manifeste le marque `"dating": false` |
| 12 | `12-mixed-large.xml` (facultatif) | — | ≈ 150 tâches, quatre niveaux, un mélange de tout ; pour la recette, aucun test ne l'exige |
| 13 | `13-resource-calendars-not-ignored.xml` | `resources_ignored`, `assignments_ignored`, `resource_calendar_ignored` | une première version du 04, dont les calendriers passent par des ressources affectées **sans** « ignorer les calendriers des ressources » : MS Project date par les ressources, et l'écart est attendu ; gardé pour les avertissements de l'import, hors du test de datation — `"dating": false` |

## Les cas critiques — ceux qui départagent deux moteurs

1. **Le week-end passé par un décalage écoulé** (02) : `2 ej` et `2 eh` après vendredi 17:00
   mènent à lundi 8:00 ; `2 j` à mercredi 8:00 — le Vérif de WF-PLA-0160 mot pour mot.
2. **Les minutes et heures écoulées dans la journée** (02) : `90 emin` après une fin à 12:00
   traverse la pause ; Waterfall compte sur une journée de vingt-quatre heures dont les heures
   travaillées occupent les premières positions, MS Project en horloge réelle. Un écart ici est une
   décision à prendre, pas un défaut : le cas doit être dans le corpus.
3. **Le pourcentage** (02) : 50 % d'un prédécesseur de dix jours vaut cinq jours de travail.
4. **Le mois** (02, 03) : `1 m` = 20 j = 160 h ; `1 em` = 30 jours civils.
5. **Les journées inégales** (04) : une tâche de 16 h qui enjambe un vendredi à 4 h ; sur
   « 4 × 10 », « 2 j » vaut toujours 16 h mais finit à un autre moment que sur le Standard.
6. **Le conflit manuel–automatique** (06) : marge négative du prédécesseur, criticité, le
   signalement ; et le même cas en début–début.
7. **La marge d'une récapitulative** (05, 07) : la plus petite de ses subordonnées qui en portent
   une, nulle ou négative ; aucune marge quand toutes ses subordonnées sont manuelles.
8. **Le jalon lié en fin–fin et le jalon seul sous une récapitulative** (05) : durée nulle, dates
   à la fin du prédécesseur ; la récapitulative garde une durée nulle et reste une récapitulative.
9. **Les contraintes** (08) : Waterfall ne les calcule pas, il fige la tâche en mode manuel aux
   dates que MS Project a calculées avec la contrainte, et doit les garder telles quelles.
10. **Les constantes différentes** (10) : « 2 j » à 7 h par jour vaut 14 h, la fin est celle de
    MS Project, le compte rendu signale la différence.

## À éviter

Ce que Waterfall ne modélise pas, et dont l'écart n'apprendrait rien : les exceptions de
calendrier ; une affectation sans « ignorer les calendriers des ressources » ; le nivellement ;
les tâches fractionnées ; un décalage sur une liaison vers ou depuis une récapitulative (refusé
chez nous, WF-PLA-0030) ; la planification à partir de la fin du projet ; une liaison en double
entre deux tâches (impossible dans MS Project aussi).
