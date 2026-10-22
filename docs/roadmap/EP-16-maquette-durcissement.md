---
id: EP-16
titre: Le contrat figé — ses mineurs soldés, la reprise de la spécification du 2026-10-22 au contrat, au faux back et aux écrans, et des parcours joués contre le front construit
statut: à planifier
depend_de: EP-15
famille: front
issue:
---

# EP-16 — Maquette et contrat : durcissement

## Objet

EP-15 réalise les ajustements que la validation de l'auteur a décidés. EP-16 **fige le contrat**
avant les EPIC de domaine, qui le serviront tel quel : tout ce qui touche le contrat, ou peut le
toucher, y est soldé, et le reste sort (décision de l'auteur du 2026-10-22, au cadrage). Il y a
trois parts :
- les mineurs du contrat et du faux back reportés d'EP-14 et d'EP-15 ;
- ce que la reprise de la spécification du 2026-10-22 (#1306, constats C-366 à C-375, #1304)
  ajoute au modèle, pour le contrat, le faux back et les écrans : le nom de l'entreprise, le client
  d'un projet, le code borné d'un sous-projet, la correspondance de l'extraction des coûts réels, le
  poste d'une ligne de coût ;
- en exception au principe, des parcours de bout en bout joués contre le front construit pour la
  production, parce qu'il faut une file de fusion stable pour livrer (#1262).

Il vient après EP-15, parce qu'on ne fige pas un contrat que les ajustements changent encore, et
avant EP-05, le premier EPIC de domaine, qui doit servir un contrat qui ne bouge plus. Le service de
chaque point de #1304 va à son EPIC de domaine, qui le reçoit dans ses « Constats reçus » :
- EP-05, la correspondance stockée et ses règles, et le nom de l'entreprise demandé par l'amorçage ;
- EP-04, le client d'un projet et le code borné d'un sous-projet ;
- EP-06, la description d'une tâche dans les notes MS Project ;
- EP-09, la lecture de l'extraction selon la correspondance, et le poste d'une ligne de coût.

## Ce qui en fait partie

- les parcours de bout en bout, faux back et service, joués contre `next build` puis `next start`,
  en local comme dans la chaîne, sur un seul build partagé entre les parts (#1262, #1265) —
  US-0590 ;
- le nom de l'entreprise utilisatrice, réglage du référentiel commun sous `cost_settings.write`, à
  côté de la devise (C-371, #1304 point 1) — US-0600 ;
- le client d'un projet et le code borné d'un sous-projet (C-372, D-7 ; #1304 points 2 et 6) —
  US-0610 ;
- la correspondance de l'extraction des coûts réels, page propre du référentiel, et le refus de
  l'import tant qu'elle est incomplète (C-374, C-373 ; #1304 points 3 et 5) — US-0620 ;
- le poste d'une ligne de coût (D-4, #1304 point 4) — US-0630 ;
- les mineurs du contrat et du faux back reportés d'EP-14 et d'EP-15 (« Constats reçus ») — US-0640 ;
- la résolution d'un numéro de ligne en nœud pour les prédécesseurs, et la préférence des colonnes
  connues (#1288, #1260) — US-0650 ;
- l'adoption par les écrans de ce qu'EP-14/L42s a écrit au contrat, qui peut encore y faire
  apparaître un manque (#1142, #779) — US-0660.

## Ce qui n'en fait pas partie

- le service de chaque point de #1304 : EP-04, EP-05, EP-06, EP-09 (« Objet ») ;
- la description d'une tâche dans les notes MS Project (C-375, #1304 point 7) : le contrat la porte
  déjà (`description` de la facette de la tâche), seul le service change — EP-06 ;
- les fichiers Excel eux-mêmes et leur présentation, qui nomment l'entreprise et le client : EP-07
  et EP-09 ;
- les finitions hors contrat, reportées le 2026-10-22 vers EP-17 (« Maquette : finitions et
  accessibilité ») :
  - le harnais d'accessibilité aux dialogues, aux menus et aux éditeurs (#782, #784, #819 point 1) ;
  - les mineurs des composants partagés et des écrans ;
  - la stabilité restante des e2e (#1263, #1230, #776, #1264) ;
  - le cosmétique ;
- les navigateurs et les largeurs d'affichage (US-0290, #92), et les dépendances sans version
  corrigée (#1291) : EP-13, reportés le 2026-10-22.

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-EXP-0020-A` | Amorçage d'une installation neuve | début — close en EP-04 | US-0600 |
| `WF-PRJ-0080-A` | Attributs d’un projet | début — close en EP-04 | US-0610 |
| `WF-PRJ-0050-A` | Sous-projets | début — close en EP-04 | US-0610 |
| `WF-REF-0190-A` | Correspondance de l’extraction des coûts réels | début — close en EP-09 | US-0620 |

Les autres travaux ne réalisent aucune exigence en propre. Comme en EP-14 et en EP-15, leurs tests
citent les exigences du domaine dont le Vérif tient côté front, et l'EPIC du domaine les clôt.

## Opérations du contrat

Ajoutées au contrat :
- la lecture et la modification de la correspondance de l'extraction des coûts réels (US-0620) ;
- la lecture de résolution d'un numéro de ligne en nœud (US-0650).

Leurs noms se fixent à la conception.

Modifiées :
- `reference` : `getReferenceSettings`, `updateReferenceSettings` — le nom de l'entreprise
  (US-0600) ;
- `projects` : `createProject`, `getProject`, `updateProject`, `listProjects` — le client ;
  `createSubproject`, `updateSubproject`, `listSubprojects` — le code borné (US-0610) ;
- `exchanges` : `openImport`, `getImport` — le refus tant que la correspondance est incomplète, la
  colonne exigée absente, les colonnes ignorées, le poste (US-0620, US-0630) ;
- `costs` : `listActualCosts` — le poste (US-0630) ;
- `me` : `updateMyPreferences` — les colonnes connues (US-0650) ;
- les opérations que touchent les constats d'US-0640, sans en ajouter : la liste se fixe à la
  conception.

## Préalables

EP-15 livré.

## Définition de fini

- chaque constat reçu est soldé : appliqué dans `docs/api`, le faux back ou le front, ou écarté dans
  `DECISIONS.md` ou dans l'issue, avec sa raison ;
- chaque modification du contrat a son entrée dans `docs/api/DECISIONS.md` et ses exemples, et le
  faux back et le témoin sont régénérés par l'outillage (`make mock-data`) ;
- les EPIC de domaine nomment, dans leurs « Constats reçus », le service de chaque point de #1304 ;
- `make check` passe sur la branche de l'EPIC ; les parcours de bout en bout s'y jouent contre le
  front construit, en local comme dans la chaîne.

## Constats reçus

Les issues à rattacher à l'issue de l'EPIC à son ouverture, chacune sous l'US qui la règle.

Venus de la reprise de la spécification du 2026-10-22 :

- #1304 — contrat, back, front : ce que la reprise ajoute au modèle — sa part contrat, faux back et
  écrans (US-0600 à US-0630) ; son service va à EP-04, EP-05, EP-06 et EP-09.

Reportés d'EP-15 le 2026-10-22, en exception au principe (#1262), ou parce qu'ils touchent le
contrat :

- #1262 — e2e : le serveur de développement sert les quatre workers en série — US-0590 ;
- #1265 — e2e : le guide du préchauffage, un avertissement en mode service, une citation, « corrigé
  avec #1262 » — US-0590 ;
- #1288 — contrat : une lecture de résolution d'un numéro de ligne en nœud (#1257, point 1) —
  US-0650 ;
- #1260 — contrat : une préférence des colonnes connues — US-0650.

Reportés d'EP-14 par la décision de l'auteur du 2026-10-11, puis d'EP-15 au cadrage du 2026-10-18
— US-0640 :

- #774 [ex-EP-14/L42t] — contrat : les exemples manquants et les mineurs des relectures de L42p,
  L42q et L42r ; ses sous-issues #747, #752, #764, #768, #777 ;
- #785 — contrat : le délai de paiement d'une ligne de main-d'œuvre n'est pas saisissable
  (WF-DEV-0020) ;
- #788 — contrat : l'horizon et le cycle de liaisons n'ont pas de refus décrit pour la fusion ; la
  part « saisies » a été faite en EP-15 (US-0460/L2) ;
- #789 — contrat : les comptes rendus d'import et de fusion ne signalent ni la ligne de provision
  déplacée ni la tâche rangée ailleurs ;
- #790 — contrat : une fusion sans révision en cours n'en crée pas une au préalable (WF-REV-0050) ;
- #792 — outil : `is_active_provision` et le point fixe de `make mock-data` ;
- #795 — contrat : les mineurs de la relecture 2 de L42s ;
- #803 — contrat : les exemples manquants des refus des chronologies et du 412 du lotissement ;
- #817 — front : réduit au point 2b, un exemple de refus à deux motifs, qui est du contrat.

Relevés au cadrage d'EP-15 (2026-10-18) et reportés d'EP-14 — US-0660 :

- #1142 — front : l'adoption par les écrans de ce qu'EP-14/L42s a écrit au contrat ;
- #779 — front : le refus d'une saisie qui laisserait une tâche sans heure ne nomme ni les rôles ni
  la tâche.

Les autres constats du label `EP-16` passent à EP-17 ou à EP-13 (« Ce qui n'en fait pas partie ») :
leur label et leur titre changent au cadrage, et le fichier de leur EPIC les liste.

## Conception

À écrire à l'étape 2 du cadrage.

---

## US-0590 — Les parcours de bout en bout joués contre le front construit

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** que tous les parcours de bout en bout se jouent contre le
front construit pour la production, en local comme dans la chaîne, **afin que** la file de fusion
ne rejette plus un lot parce que le serveur de développement sert quatre workers en série (#1262).

**Critères d'acceptation.**

- propre à l'US : `make e2e` et `make e2e-service` jouent tous leurs parcours contre le front
  construit (`next build` puis `next start`) ; aucun parcours ne se joue plus contre `next dev` ;
- propre à l'US : dans la chaîne, le front est construit une seule fois par exécution, et chaque part
  des parcours, la mesure de la seconde et la part du service jouent ce même build ;
- propre à l'US : trois passages successifs du palier complet local, à quatre workers, ne montrent
  aucun des échecs que #1262 attribue au débit du serveur de développement : `remaining`,
  `planning`, `admin`, `context`, `navigation`, `review`. Le parcours d'accessibilité
  d'`/admin/access-roles` et le rendu serveur du Kanban relèvent de #1263, en EP-17 ;
- propre à l'US : le guide dit contre quel serveur les parcours se jouent, et ce que deviennent le
  préchauffage des routes et la règle provisoire de #1145 ; les trois points de #1265 sont corrigés.

**Notes de réalisation.**
- Le harnais construit déjà le front pour la mesure de la seconde (US-0110/L2, port 3101) : l'US
  étend ce build à tous les parcours ; elle ne le crée pas.
- Le front construit refuse l'authentification simulée hors du harnais (`WATERFALL_E2E`).
- Les parcours du service passent par le canal de retour de Keycloak, qui exige d'écouter sur toutes
  les interfaces.
- Décision de l'auteur du 2026-10-22, sur #1262 : EP-16, en tête, tout le harnais, parcours du
  service compris, un seul build partagé entre les parts de la chaîne.

**Hors périmètre.** #1263, #1230, #776 et #1264 : EP-17.

---

## US-0600 — Le nom de l'entreprise utilisatrice

- **statut** : à faire
- **exigences** : `WF-EXP-0020-A`
- **opérations** : `getReferenceSettings`, `updateReferenceSettings`
- **issue** :

**En tant que** manager, **je veux** lire et corriger le nom de l'entreprise que l'installation
connaît, **afin que** les fichiers exportés disent de quelle entreprise ils viennent.

**Critères d'acceptation.**

- écart : `WF-EXP-0020-A` — « Après installation, un administrateur fixe son mot de passe par le
  lien produit, se connecte, porte le rôle « administrateur », et trouve les trois rôles prédéfinis
  et le catalogue des permissions. » : constaté par EP-03 (US-0420), livré ;
- écart : `WF-EXP-0020-A` — « La création d'un projet est refusée et nomme les prérequis manquants,
  jusqu'à ce qu'une catégorie de coût de main-d'œuvre et un rôle de ressource aient été saisis. » :
  le service du projet — EP-04, qui clôt l'exigence ;
- écart : `WF-EXP-0020-A` — « Une seconde exécution de l'installation ne crée ni compte, ni
  calendrier, ni nature supplémentaire ; elle produit un nouveau lien, qui remplace le précédent,
  tant que l'administrateur n'a pas fixé son mot de passe, et aucun lien ensuite. » : constaté par
  EP-03 (US-0420) ;
- écart : `WF-EXP-0020-A` — « Le lien produit à l'installation est accepté plus d'une heure après
  sa production. » : constaté par EP-03 (US-0420) ;
- écart : `WF-EXP-0020-A` — « Sur une installation neuve, les bornes de probabilité valent 25 %,
  50 % et 75 %, celles de gravité 1 %, 5 % et 10 %, les seuils 0,9 et 0,8, le délai six semaines,
  et le calendrier par défaut compte huit heures du lundi au vendredi et aucune le week-end. » :
  l'amorçage du référentiel — EP-05 ;
- écart : `WF-EXP-0020-A` — « Le nom de l'entreprise saisi à l'installation figure sur un devis
  exporté ; modifié, il figure sur le suivant. » :
  - l'amorçage qui demande le nom et la base qui le garde : EP-05 ;
  - le devis exporté qui le porte : EP-07 ;
  - EP-16 en donne le réglage, au contrat et à l'écran (ci-dessous) ;
- propre à l'US : les paramètres communs (`ReferenceSettings`) portent le nom de l'entreprise, que
  l'écran des paramètres de coûts montre à côté de la devise ;
- propre à l'US : qui porte `cost_settings.write` modifie le nom de l'entreprise à cet écran ; qui
  ne la porte pas le lit sans commande de modification, et une modification qu'il enverrait malgré
  tout est refusée par 403, `PERMISSION_MISSING` nommant `cost_settings.write` ;
- propre à l'US : un nom vide est refusé par champ (422), et rien n'est écrit.

**Notes de réalisation.**
- Décision de l'auteur du 2026-10-22 : le nom se range sous `cost_settings.write`, dans
  `ReferenceSettings`, à côté de la devise (WF-REF-0140, FBS-3.1).
- `updateReferenceSettings` a déjà le modèle d'une permission par champ : la matrice relève de
  `risk_settings.write`, les seuils d'`indicator_settings.write`.
- Le nom ne va pas dans `Installation` : `getInstallation` se lit sans session, et le nom n'est
  utile qu'aux fichiers exportés.

---

## US-0610 — Le client d'un projet et le code d'un sous-projet

- **statut** : à faire
- **exigences** : `WF-PRJ-0080-A`, `WF-PRJ-0050-A`
- **opérations** : `createProject`, `getProject`, `updateProject`, `listProjects`,
  `createSubproject`, `updateSubproject`, `listSubprojects`, `openImport`, `getImport`
- **issue** :

**En tant que** chef de projet, **je veux** nommer le client de mon projet, et que le code d'un
sous-projet puisse nommer un onglet Excel, **afin que** le devis remis au client le nomme, et que
le fichier de reste à engager range chaque sous-projet dans son onglet.

**Critères d'acceptation.**

- écart : `WF-PRJ-0080-A` — « La création d'un projet sans libellé est refusée. » : constaté par
  EP-14 contre le faux back ; le service — EP-04 ;
- écart : `WF-PRJ-0080-A` — « La date de réception de la commande est saisissable à tout moment et
  n'est exigée par aucune transition. » : non touchée ici — EP-04 ;
- écart : `WF-PRJ-0080-A` — « Le nom du client est saisissable à tout moment, n'est exigé par aucune
  transition, et figure sur la présentation d'un devis exporté. » :
  - EP-16 rend le client saisissable au contrat et à l'écran (ci-dessous) ;
  - les transitions qui ne l'exigent pas : le service, EP-04 ;
  - la présentation du devis exporté : EP-07 ;
- écart : `WF-PRJ-0050-A` — « Un projet se chiffre sans aucun sous-projet. » : constaté par EP-02 ;
  EP-04 clôt ;
- écart : `WF-PRJ-0050-A` — « La création de deux sous-projets de même code dans un même projet est
  refusée. » : le service — EP-04 ;
- écart : `WF-PRJ-0050-A` — « La création d'un sous-projet de code « SP/01 », « Synthèse » ou de
  plus de trente et un caractères est refusée. » :
  - EP-16 en écrit au contrat la borne, le motif et le refus, et le formulaire le dit
    (ci-dessous) ;
  - le refus par le service : EP-04 ;
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet portant des coûts réels est refusée. » :
  constaté par EP-14 contre le faux back ; EP-04 clôt ;
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet cité par une révision marquée est
  refusée. » : constaté par EP-14/L42l ; EP-04 clôt ;
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet que porte une ligne de devis de la
  révision en cours est refusée ; elle aboutit une fois cette ligne passée à un autre
  sous-projet. » : la seconde moitié demande le service — EP-04 ;
- écart : `WF-PRJ-0050-A` — « Le passage à un autre sous-projet d'une ligne d'une tâche démarrée,
  dont le sous-projet a reçu des coûts réels, est refusé et nomme ce sous-projet ; celui d'une ligne
  d'une tâche non démarrée aboutit, comme celui de la ligne de provision d'un risque identifié. » :
  constaté par EP-15 (US-0480) ; EP-04 clôt ;
- propre à l'US : un projet porte le nom de son client, facultatif.
  - `createProject` et `updateProject` l'écrivent, `getProject` le lit.
  - Le formulaire de création et l'écran des paramètres du projet le saisissent et l'effacent, quel
    que soit l'état du projet, tant que le projet n'est pas terminal.
- propre à l'US : au contrat, le code d'un sous-projet compte au plus 31 caractères, sans `:`, `\`,
  `/`, `?`, `*`, `[` ni `]`, et ne vaut ni « Synthèse » ni « Hors sous-projet ».
  - Un code qui ne l'est pas est refusé par champ (422), avec son motif.
  - Le formulaire du sous-projet dit ce motif.
- propre à l'US : l'exemple `import_remaining_subproject_held` nomme l'onglet du sous-projet par son
  code, et non plus par son libellé, et chaque code de sous-projet du témoin respecte la borne.

**Notes de réalisation.**
- La spécification veut le client « facultatif » (introduction du §3.4.5.2) : nul par défaut,
  exigé par aucune transition.
- La borne du code suit la décision D-7 de la reprise du 2026-10-22. Le contrat passe de 50 à 31.
- Le code d'un sous-projet lu dans un élément d'OTP (`ActualCostLine.subproject_code`) garde sa
  propre borne : un code inconnu y est conservé tel quel (WF-CRE-0020). Que la borne suive ou non se
  tranche à la conception.

---

## US-0620 — La correspondance de l'extraction des coûts réels

- **statut** : à faire
- **exigences** : `WF-REF-0190-A`
- **opérations** : la lecture et la modification de la correspondance, ajoutées au contrat ;
  `getProject`, `openImport`, `getImport`
- **issue** :

**En tant que** manager, **je veux** déclarer les intitulés sous lesquels l'extraction de notre ERP
nomme les colonnes que Waterfall lit, et les colonnes qu'il conserve, **afin d'** importer les coûts
réels quels que soient l'ERP, son paramétrage et la langue de qui l'extrait, sans faire entrer dans
Waterfall une colonne que nous n'avons pas choisie.

**Critères d'acceptation.**

- écart : `WF-REF-0190-A` — « Sur une installation neuve, l'import d'un fichier de coûts réels est
  refusé et nomme la correspondance à régler. » :
  - le refus par le service : EP-09, qui clôt ;
  - la correspondance vide à l'installation : EP-05 ;
  - EP-16 écrit le refus au contrat, et l'écran le dit (ci-dessous) ;
- écart : `WF-REF-0190-A` — « Après déclaration de « Elément d'OTP », « Nº pièce référence »,
  « Date de la pièce » et « Val./Devise objet », une extraction dont l'en-tête est « Élément
  d'OTP » s'importe. » :
  - la lecture de l'extraction selon la correspondance : EP-09 ;
  - la comparaison sans égard à la casse, aux accents et aux espaces en bout : EP-05 ;
- écart : `WF-REF-0190-A` — « Une colonne « Nom Matricule » non déclarée n'est pas conservée, et le
  compte rendu la nomme ; déclarée conservée, elle est restituée à la consultation des lignes
  importées ensuite. » :
  - le service : EP-09 ;
  - EP-16 donne au compte rendu la liste des colonnes ignorées (ci-dessous) ;
- écart : `WF-REF-0190-A` — « Une extraction à laquelle manque une colonne exigée est refusée, et le
  message nomme la colonne attendue. » :
  - le refus par le service : EP-09 ;
  - EP-16 écrit au contrat le paramètre qui nomme la colonne, et l'écran le dit (ci-dessous) ;
- propre à l'US : une page propre du référentiel, avec son entrée de menu sous les paramètres de
  coûts (FBS-3.1), montre la correspondance.
  - Pour chaque colonne lue (élément d'OTP, numéro de pièce, poste, date de pièce, montant), elle
    montre ses intitulés admis.
  - Elle montre aussi la liste des colonnes conservées, déclarées une à une.
  - Une correspondance vide dit les quatre colonnes exigées qui n'ont aucun intitulé : toutes sauf
    le poste.
- propre à l'US : qui porte `cost_settings.write` ajoute, modifie et retire un intitulé, déclare et
  retire une colonne conservée ; qui porte seulement `cost_settings.read` lit la page sans commande
  de modification ;
- propre à l'US : tant que l'une des quatre colonnes exigées n'a aucun intitulé, la commande
  `import_actual_costs` d'un projet est indisponible et nomme la condition
  `actual_cost_mapping_complete`.
  - Un `openImport` de coûts réels envoyé malgré tout est refusé par 409 `STATE_FORBIDS_OPERATION`,
    `params.missing_condition` à `actual_cost_mapping_complete`.
  - `params.columns` y nomme les colonnes sans intitulé, et l'écran des échanges le dit.
- propre à l'US : un fichier de coûts réels auquel manque une colonne exigée est refusé par 422
  `FILE_FORMAT_UNREADABLE`, un paramètre nommant la colonne attendue, et l'écran le dit ;
- propre à l'US : le compte rendu d'un import de coûts réels nomme chaque colonne du fichier ni lue
  ni déclarée conservée, que l'import ignore ;
- propre à l'US : les éléments d'OTP des exemples de coûts réels portent le code projet, préfixe
  compris, suivi facultativement d'une barre oblique et du code sous-projet (WF-CRE-0020, C-373).

**Notes de réalisation.**
- Décisions de l'auteur du 2026-10-22 :
  - une page propre, par exemple `/reference/costs/actual-cost-mapping`, avec son entrée de menu ;
  - le refus de l'import par 409 `STATE_FORBIDS_OPERATION`, `actual_cost_mapping_complete` et
    `params.columns`, la commande `import_actual_costs` nommant la condition d'avance ;
  - le service : EP-05 stocke la correspondance et applique ses règles, EP-09 lit l'extraction selon
    elle et clôt WF-REF-0190.
- La permission découle de la spécification : WF-REF-0190 relève de FBS-3.1, dont la permission de
  modifier est `cost_settings.write` (WF-ADM-0100).
- Une modification de la correspondance ne change aucune ligne déjà importée (WF-REF-0190) : le
  contrat le dit, le service le tient (EP-09).
- L'exemple de l'auteur (« Elément d'OTP », « Nº pièce référence », « Date de la pièce »,
  « Val./Devise objet ») est celui du Vérif. Les exemples du contrat le reprennent.

---

## US-0630 — Le poste d'une ligne de coût

- **statut** : à faire
- **exigences** : aucune en propre ; le service clôt WF-INTF-0140, WF-CRE-0010 et WF-DAT-0110 en
  EP-09
- **opérations** : `listActualCosts`, `getImport`
- **issue** :

**En tant que** chef de projet, **je veux** voir le poste de chaque ligne de coût, **afin de**
distinguer les postes d'une même pièce de l'ERP, qu'une facture ventilée sur deux éléments d'OTP
donne en deux lignes.

**Critères d'acceptation.**

- propre à l'US : une ligne de coût porte son numéro de poste, nul quand l'extraction n'en donne
  pas ; la consultation des coûts réels le montre à côté du numéro de pièce ;
- propre à l'US : le compte rendu d'un import de coûts réels désigne une ligne par sa pièce et son
  poste. Deux lignes du fichier de même pièce et de même poste y sont rejetées, avec un motif que
  l'écran dit, sur un exemple du contrat.

**Notes de réalisation.**
- Décision D-4 de la reprise du 2026-10-22 : une ligne de coût est identifiée par le projet, le
  numéro de pièce et le numéro de poste.
- La contrainte d'unicité, sa migration et l'idempotence de WF-DAT-0110 sur ce triplet sont le
  service : EP-09.

---

## US-0640 — Les mineurs du contrat et du faux back

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : celles que les constats touchent, sans en ajouter ; la liste se fixe à la
  conception
- **issue** :

**En tant que** développeur, **je veux** solder les mineurs du contrat et du faux back que les
relectures d'EP-14 ont relevés, **afin que** les EPIC de domaine servent un contrat figé, aux
exemples complets et aux refus décrits.

**Critères d'acceptation.**

- propre à l'US : chaque constat de contrat reçu (« Constats reçus », US-0640) est soldé, point par
  point.
  - Appliqué : dans `docs/api`, avec son entrée dans `DECISIONS.md` et ses exemples.
  - Ou caduc : un ajustement d'EP-15 l'a rendu sans objet, et l'issue le dit.
  - Ou écarté : avec sa raison, dans `DECISIONS.md` ou dans l'issue.
- propre à l'US : chaque refus que le contrat décrit a un exemple, et les tests du front qui
  l'éprouvent passent par cet exemple, non par une enveloppe écrite dans le test (#803, #764,
  #817 point 2b) ;
- propre à l'US : deux exécutions de suite de `make mock-data` donnent les mêmes exemples (#792), et
  les indices d'un portefeuille sans projet en cours sont non calculables, avec leur motif, jamais
  une erreur (#777).

**Notes de réalisation.**
- Plusieurs points datent d'avant EP-15, qui a découpé `mockcore.py` et `mockwitness.py` (#1281) et
  réécrit les refus de la structure : chaque point se relit sur `epic/EP-15` livré avant d'être
  appliqué.
- #785 rend le délai de paiement saisissable sur une ligne de main-d'œuvre (WF-DEV-0020). La cellule
  du devis suit `editable_fields`, sans code propre.

---

## US-0650 — La résolution d'un numéro de ligne, et les colonnes connues d'une grille

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : la lecture de résolution d'un numéro de ligne, ajoutée au contrat ;
  `setPredecessors`, `getMe`, `updateMyPreferences`
- **issue** :

**En tant que** chef de projet, **je veux** saisir comme prédécesseur le numéro d'une tâche que ma
recherche a écartée, et ne voir apparaître une colonne nouvelle, masquée par défaut, que si je la
demande, **afin que** filtrer une grille ne m'empêche pas de la saisir, et qu'une colonne ajoutée
par une version ne bouscule pas la grille que j'ai réglée.

**Critères d'acceptation.**

- propre à l'US : un numéro de ligne absent des lignes lues, mais porté par une tâche de la structure
  lue, se saisit dans la colonne des prédécesseurs.
  - Le front le résout en nœud par la lecture du contrat, et la liaison s'écrit en
    `predecessor_node_id`.
  - Un numéro qu'aucune tâche de la structure ne porte est refusé comme inconnu.
- propre à l'US : une colonne masquée par défaut, que la grille ne connaissait pas, l'est aussi pour
  un compte qui a déjà réglé cette grille ; une colonne que le compte a choisi d'afficher reste
  affichée.

**Notes de réalisation.** Décisions de l'auteur :
- #1288 : une lecture de résolution au contrat ; l'écriture reste en `predecessor_node_id`
  (2026-10-22, #1257 point 1) ;
- #1260 : une préférence des « colonnes connues » au contrat des préférences (2026-10-21, #1232).

---

## US-0660 — Ce qu'EP-14/L42s a écrit au contrat, adopté par les écrans

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : celles des six points de #1142, et celles des saisies que refuse
  `TASK_WITHOUT_WORKING_HOURS`
- **issue** :

**En tant que** chef de projet, **je veux** que les écrans disent les règles que le contrat décrit
déjà, **afin que** chaque refus et chaque indisponibilité me nomment ce qui les cause.

**Critères d'acceptation.**

- propre à l'US : les six points de #1142 sont montrés par les écrans, chacun sur un exemple du
  contrat :
  - la réactivation d'une catégorie sous une nature désactivée, et la désactivation d'une nature en
    cascade sur ses catégories ;
  - les catégories nommées par le refus d'un changement de type ;
  - l'import rejeté entier ;
  - le lot sans tâche rattachée, présenté sans total ;
  - la saisie du lotissement indisponible pendant un traitement de fond ;
  - les tâches nommées par le refus d'un poste hors du sous-arbre de son lot.
- propre à l'US : le refus d'une saisie qui laisserait une tâche sans heure travaillée
  (`TASK_WITHOUT_WORKING_HOURS`) nomme la tâche par son libellé et les rôles par leur libellé (#779).
- propre à l'US : un manque du contrat que cette adoption révèle est corrigé au contrat, dans l'US.

**Notes de réalisation.** Ces deux constats ne demandent que le front, mais ils peuvent révéler un
manque du contrat, comme EP-15 l'a souvent constaté : c'est ce qui les garde en EP-16 (principe de
l'auteur du 2026-10-22).
