---
id: EP-02
titre: Tous les écrans, navigables, alimentés par le faux back, avant toute règle métier
statut: en cours
depend_de: EP-01
issue: 72
---

# EP-02 — Maquette du front sur contrat simulé

## Objet

Construire l'application web entière contre le faux back d'EP-01 : la navigation, les
composants d'interface de PBS-1.3, les onze exigences du §3.6, les deux langues, et chaque
fonction adressable à l'écran. Rien n'est calculé par le front — c'est le mock qui répond.
Cet EPIC ne s'intéresse qu'à deux choses : l'ergonomie, qu'il constate, et le contrat, qu'il
fige ; tout ce qui exige un serveur réel se commence ici et se clôt dans l'EPIC de son
domaine.

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
- la charte graphique, en jetons dérivés des logos du dépôt, en clair et en sombre : aucun
  composant n'écrit une couleur ni une police en dur ;
- la grille dense — le composant qui porte le planning, le devis, le reste à engager et les
  risques : lecture, tri et filtres demandés au serveur, colonnes, saisie au clavier seul,
  collage depuis un tableur, et les commandes Annuler et Rétablir, présentes et
  positionnées ;
- la distinction visuelle entre valeur calculée et valeur saisie ;
- l'échelle de signalement commune, lisible sans couleur ;
- le suivi des traitements longs, les commandes indisponibles et les refus ;
- l'accessibilité minimale : clavier, contraste AA, libellés, agrandissement à 150 % ;
- les deux langues, les catalogues, et le contrôle de complétude par la chaîne ;
- chaque fonction feuille de l'arborescence FBS adressable — une page, une route ou un
  onglet, l'ergonomie décidant des regroupements —, en lecture, alimentée par le mock ; les
  seules commandes réelles sont celles que le §3.6 impose d'éprouver tôt : la saisie en
  grille, le collage, le marquage, la sortie du cycle de vie, l'import en deux temps, la
  langue et les préférences, la connexion et le compte personnel ;
- la connexion et le compte personnel, les écrans qu'EP-03 branchera sur l'authentification
  réelle ;
- les modifications du contrat déjà connues, faites avant les écrans (« Opérations du
  contrat ») ;
- la preuve que le front n'appelle l'API que par le client engendré.

## Ce qui n'en fait pas partie

- toute règle et tout calcul : le mock les rend, le front les affiche. Un écran qui aurait
  besoin de calculer est un endpoint qui manque au contrat, donc un constat, pas du code ;
- le comportement réel des écrans, qui arrive avec l'EPIC de leur domaine : ici, une commande
  aboutit parce que le mock répond, pas parce qu'une règle a été évaluée ;
- les formulaires de création et de modification — projets, révisions, comptes, rôles… :
  ils appartiennent à l'EPIC de leur domaine, et leurs opérations d'écriture avec eux ; la
  saisie d'un taux dans la grille des taux horaires, elle, est une saisie en grille (§3.6)
  et reste ;
- le fonctionnement de l'annulation : ses commandes se voient et se placent ici, elles
  n'agissent qu'en EP-06 ;
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
| `WF-IHM-0060-A` | Lecture d'une grille | début — close en EP-03 | US-0110 |
| `WF-IHM-0070-A` | Une échelle de signalement commune, lisible sans couleur | entière | US-0160 |
| `WF-IHM-0080-A` | Traitements longs | entière | US-0180 |
| `WF-IHM-0090-A` | Refus et commandes indisponibles | entière | US-0170 |
| `WF-IHM-0100-A` | Accessibilité minimale | entière | US-0200 |
| `WF-IHM-0110-A` | Annulation et rétablissement des saisies | début — close en EP-06 | US-0140 |
| `WF-INTF-0160-A` | Choix de la langue de l'interface | début — close en EP-03 | US-0190 |
| `WF-INTF-0170-A` | Ce qui est traduit et ce qui ne l'est pas | entière | US-0190 |
| `WF-INTF-0180-A` | Formats indépendants de la langue | début — close en EP-12 | US-0190 |
| `WF-ADM-0040-A` | Préférences d'affichage | début — close en EP-03 | US-0110, US-0190 |
| `WF-DAT-0100-A` | Types des grandeurs | début — close en EP-07 | US-0190 |
| `WF-QUA-0070-A` | Complétude des traductions | entière | US-0190 |
| `WF-CMP-0010-A` | Navigateurs et affichage | début — close en EP-13 | US-0290 |

Neuf des onze exigences du §3.6 sont closes par cet EPIC : elles portent sur l'interface,
et l'interface existe ici pour de bon. Sept exigences ne font que commencer, et leurs US
disent quelle phrase attend quoi : WF-IHM-0060 (le tri effectif et les réglages par compte —
EP-03), WF-IHM-0110 (l'annulation qui restitue — EP-06), WF-ADM-0040 et WF-INTF-0160 (la
conservation des préférences et de la langue dans le compte — EP-03), WF-INTF-0180 (le
format des fichiers d'échange — EP-12), WF-CMP-0010 (la version majeure précédente et le
Safari réel — EP-13, en recette), et WF-DAT-0100 (l'affichage des dates sans fuseau est
ici ; les sommes exactes sont au noyau — EP-03, closes en EP-07).

## Opérations du contrat

Toutes celles que les écrans lisent, servies par le faux back. Les familles, avec l'US qui
les consomme : `session` et `system` (US-0090, US-0320), `projects` et `revisions` (US-0210),
`revisions` pour le planning et le devis (US-0220), `risks`, `costs` et la partie « reste à
engager » d'`analysis` (US-0230), `analysis` et `portfolio` (US-0240), `reference` et
`access` (US-0250), `exchanges` (US-0260).

Une opération qui manque se note dans cet EPIC et se corrige dans `docs/api` : c'est une
modification du contrat, donc un travail qui précède l'écran qui l'attend.

Dix modifications sont déjà connues, décidées au cadrage, et se font en premier lot : les
commandes disponibles et leurs conditions manquantes, portées par le projet et par la
révision ; le catalogue des codes d'erreur, que `Problem.code` promet sans qu'il existe ;
l'énumération des codes de permission ; les deux genres manquants de tâche de fond — fusion
d'une structure, survenance d'un risque ; `listNodes` rendu sans pagination, une révision
portant au plus dix mille objets ; les champs calculés portés par chaque nœud
(`computed_fields`) ; la langue réduite à une seule préférence à trois états — `default`,
`fr`, `en` —, où `default` suit le navigateur, et la langue par défaut de l'installation
rendue lisible sans session (`getInstallation`), pour la page de connexion ; le tri et les filtres des grilles portés par
le contrat et exécutés par le serveur, qui rend les lignes et les totaux du périmètre
demandé ; le filtre « mes projets » de `listProjects` — les projets dont l'utilisateur
est contributeur —, qu'exige l'écran d'accueil ; et le thème, préférence de compte à trois
états — `default`, `light`, `dark` —, où `default` suit le poste, symétrique de la langue.

## Préalables

EP-01 livré : le client engendré, le faux back, les fixtures et le harnais de bout en bout.

## Définition de fini

- chaque fonction feuille de l'arborescence FBS est adressable — une page, une route ou un
  onglet — depuis la navigation, et un contrôle du dépôt le vérifie ;
- les onze exigences du §3.6 ont chacune au moins un test de bout en bout qui les cite ;
- un contrôle automatisé de contraste ne relève aucun écart au niveau AA, en clair comme
  en sombre ;
- le parcours de bout en bout s'exécute et aboutit en français comme en anglais ;
- la chaîne échoue sur un appel http au serveur hors du client engendré, sur un texte
  destiné à l'utilisateur écrit en dur, et sur une clé de traduction manquante ou orpheline ;
- les constats faits sur le contrat sont écrits — soit appliqués dans `docs/api`, soit ouverts
  en issue « Interface contract issue » — et aucun n'est resté dans une tête.

## Conception

EP-02 n'a ni table, ni migration, ni module du noyau : il écrit du front, des exemples du
contrat, et les dix modifications du contrat décidées au cadrage. Sa conception fixe qui
appelle l'API, où vit le contexte de lecture, comment un faux back sans état montre des
états différents, la charte graphique, la forme des composants partagés (PBS-1.3), les
langues, et ce que la chaîne contrôle. Les versions vivent dans `package.json` et son
verrou.

### Arborescence du front

| Chemin | Contenu |
|---|---|
| `frontend/src/app/` | les routes, en anglais : `/` (l'accueil), `/login`, `/me`, `/projects/[projectId]/revisions/[revisionId]/<fonction>` (`planning`, `estimate`, `remaining`, `risks`, `actual-costs`, `indicators`…), `/portfolio/…`, `/reference/…`, `/admin/…`, `/system`, et la page « introuvable » |
| `frontend/src/api/` | le client engendré ; `server.ts` ; `actions/`, les actions serveur d'écriture et de suivi, une par famille du contrat ; `problem.ts`, le décodeur de l'enveloppe d'erreur |
| `frontend/src/components/` | les composants partagés : `grid/`, `signal/`, `context/`, `commands/`, `tasks/`, `charts/`, `gantt/`, `tree/` |
| `frontend/src/components/ui/` | les composants shadcn/ui copiés — seulement ceux qu'un écran emploie |
| `frontend/src/theme/` | la charte : les jetons, en variables CSS, clair et sombre |
| `frontend/src/i18n/` | next-intl : résolution de la langue, formats |
| `frontend/messages/` | `fr.json`, le catalogue de référence, et `en.json` |
| `frontend/src/navigation/functions.json` | la table des fonctions : code FBS, route, clé de libellé ; la navigation en est tirée |
| `fixtures/api/`, `fixtures/api/volume/` | les exemples du contrat ; les exemples de volume, engendrés |

### Charte graphique

- **Tout est jeton.** Les couleurs, la typographie, les espacements et les rayons sont des
  variables CSS (`src/theme/`), que Tailwind et shadcn/ui consomment ; un composant n'écrit
  jamais une couleur ni une police. La palette dérive des bleus des logos de `docs/assets`,
  complétée des neutres de shadcn ; les jetons du signalement (US-0160) portent les zones
  du référentiel, choisis pour le contraste AA et lisibles par un daltonien.
- **Clair et sombre dès la maquette**, par les mêmes jetons : `default` suit le poste
  (`prefers-color-scheme`), et un attribut `data-theme` posé par la coquille force `light`
  ou `dark` selon la préférence de compte — la dixième modification du contrat. Écarté :
  next-themes, une dépendance pour un attribut que la coquille sait poser.
- Le logo emploie ses deux variantes, déjà dans `docs/assets`. Le titre de l'onglet nomme
  l'écran et le projet ; le favicon vient de `waterfall_icon.svg`.

### Qui appelle l'API

- **Seul le serveur Next appelle l'API** (§4.3.1 : le navigateur ne parle qu'au front).
  Les lectures se font dans les composants serveur, les écritures et le suivi des tâches
  dans des actions serveur (`src/api/actions/`) qui appellent le client engendré et rendent
  au composant la réponse ou l'enveloppe `Problem`. `client.ts` et `server.ts` importent
  `server-only` : un composant client qui les importerait ne se construit pas. Écarté :
  appeler l'API depuis le navigateur — EP-03 devrait exposer le témoin de session au CORS ;
  un gestionnaire de route qui relaierait l'API — le composant intermédiaire que WF-ARC-0020
  interdit.
- `serverClient()` reste le seul endroit qu'EP-03 touchera pour transmettre le témoin
  `wf_session` ; EP-02 ne transmet rien, le faux back accorde la session.
- **Après une écriture, l'écran applique la réponse** à la ligne ou à l'objet concerné, et
  ne relit jamais la grille entière : une relecture de six mille nœuds par cellule saisie
  coûterait la seconde du §4.6.2, et réinitialiserait le défilement et la cellule active.
  Sur le faux back, la réponse est un exemple figé : les tests de saisie s'écrivent avec
  les valeurs de cet exemple.
- **Un seul décodeur d'erreur** (`problem.ts`) : `code` et `params` rendus par le
  catalogue ; `412` propose de recharger ; `409` explique ; `401` mène à la connexion et,
  la connexion refaite, ramène à l'écran visé ; une API injoignable rend l'écran de panne —
  jamais d'écran blanc.

### Contexte de lecture, accueil et pages système

- **L'URL fait foi** : le projet dans le chemin ; la révision aussi pour les fonctions qui la
  lisent — planning, devis, reste à engager, risques, coûts réels, indicateurs —, et en
  paramètre `revision_id` pour les fonctions du projet lui-même — révisions, paramètres,
  cycle de vie —, qu'un projet sans révision garde ; sous-projet filtré et date de calcul en
  paramètres. Les liens entre fonctions les reportent, les composants serveur les lisent.
  Écarté : un état global côté client — perdu au rechargement, invisible du rendu serveur,
  une seconde source de vérité.
- **Le dernier contexte de projet** vit dans un témoin du front ; la coquille en tire le
  « retour au projet » depuis une fonction hors projet (WF-IHM-0010).
- **L'accueil** est la liste des projets, filtrée sur « mes projets » — le filtre
  contributeur du contrat —, visible et levable.
- **Les pages système** sont des pièces de la coquille : un écran « introuvable » unique —
  adresse inexistante ou lecture refusée, indistinguables (WF-ADM-0110) —, l'écran de
  panne, les squelettes de chargement, et les états vides — aucun projet, projet sans
  révision, installation dont le référentiel est incomplet, qui guide vers lui
  (`getReferenceReadiness`). Chaque état vide est un exemple nommé du contrat.
- **Une révision est en lecture seule** quand l'API la dit marquée ou que ses commandes
  sont indisponibles : l'écran lit `status` et `available_commands`, il ne déduit rien.

### Faux back et exemples

- **Le premier exemple d'une réponse est celui que prism sert.** Il décrit un univers
  cohérent — le même projet d'un exemple à l'autre, sa révision de référence marquée, sa
  révision courante. Les **exemples nommés** (`marked`, `running`, `failed`, `empty`,
  `not_contributor`…) servent aux états qu'un Vérif demande et que le premier ne montre
  pas.
- **Tests de composants** (Vitest, happy-dom, Testing Library) : `fakeClient` couvre les cinq
  méthodes, choisit un exemple nommé, enchaîne des réponses (`running` puis `succeeded`) et
  enregistre les appels, corps compris. **Parcours de bout en bout** : le premier exemple ;
  une phrase de Vérif qui demande un autre état se vérifie au composant. Écarté : faire
  suivre l'en-tête `Prefer` de prism par le front — du code d'essai dans le front de
  production.
- **Volumes du §4.6.2** : `wftools.mockdata` (`make mock-data`) engendre, déterministe, la
  structure de mille tâches à cinq lignes, les taux de cent cinquante rôles sur quinze ans
  et le portefeuille de trois cents projets, dans `fixtures/api/volume/` — déclarés
  engendrés dans `tools/paths.toml`, vérifiés à jour par la chaîne. Le premier exemple de
  `listNodes` est celui des mille tâches : c'est ainsi que le faux back sert le volume au
  parcours qui mesure la seconde. Le parcours témoin d'EP-01 garde son chemin, ses
  assertions sont réécrites. Écarté : des exemples de volume écrits à la main ; le mode
  dynamique de prism, qui tirerait d'autres nombres à chaque exécution.

### Composants partagés (PBS-1.3)

- **Grille dense** : un composant, des configurations (colonnes, facette, action
  d'écriture, clé de préférences). TanStack Table porte le modèle, **TanStack Virtual** ne
  rend que les lignes visibles — dépendance hors annexe C, de la même famille, comme Vitest
  en EP-01. Écarté : tout rendre — soixante mille cellules, la seconde n'est pas tenue ;
  paginer — un arbre ne se lit pas par pages.
  - **Le tri et les filtres sont demandés au serveur** (décision du cadrage) : le clic
    d'en-tête relit avec le paramètre du contrat, la réponse porte les lignes et les totaux
    du périmètre demandé, et rien ne s'ordonne ni ne se somme dans le front — la règle de
    `typescript.md` reste sans exception. Écarté : trier dans le front, qui aurait exigé
    l'exception et laissé les totaux mentir sous filtre.
  - En-têtes et totaux figés au défilement vertical, colonnes d'identification figées au
    défilement horizontal ; colonnes et largeurs dans les préférences de compte, par clé de
    grille stable, écrites avec anti-rebond.
  - Saisie : une seule cellule dans l'ordre de tabulation, `role="grid"`, `aria-rowcount`
    malgré la virtualisation ; Entrée ou F2 entre en saisie, Entrée valide et avance,
    Échap abandonne ; chaque cellule validée part seule, par une action serveur. Une
    cellule est saisissable si son champ est au schéma d'écriture et que le nœud ne le
    déclare pas calculé (`computed_fields`) ; une cellule calculée est traversée, et une
    tentative est refusée en nommant ce dont la valeur dépend. Un nombre se saisit au
    format de la langue et repart dans le décimal exact du contrat.
  - Collage : lecture TSV du presse-papiers, `previewPaste`, compte rendu, `applyPaste`
    après confirmation ; le front ne juge rien du contenu.
  - **Annuler et Rétablir sont posées, pas branchées** : leur place — grille, menu,
    Ctrl+Z/Ctrl+Maj+Z —, leur état, et rien d'autre ; EP-06 les branchera sur
    `undoLastChange` et `redoLastUndo`.
- **Valeur calculée** : un seul style, une marque non colorée, un nom accessible.
- **Signalement** : `Signal` reçoit une `AlertZone` du contrat — icône Lucide, libellé du
  catalogue, jeton de couleur ; la table zone → jeton est unique, aucune zone ne se déduit
  d'une valeur dans le front.
- **Bandeau de contexte** : projet ; révision, son état, son caractère de référence ;
  filtres en pastilles ; date de calcul — une valeur sous enveloppe `Computable` ne
  s'affiche pas sans la date de son `CalculationContext`, rendue en heure locale. Quand la
  date de calcul renvoie à une autre révision que celle de l'adresse — `as_of` lit la
  dernière révision marquée antérieure —, le bandeau nomme la révision du calcul
  (`CalculationContext.revision_id`), pas celle de l'adresse.
- **Commande** : sur le projet et la révision, absente quand l'objet ne la liste pas — le
  serveur ne liste dans `available_commands` que les commandes dont l'appelant a la
  permission, et le front ne sait pas quelle permission garde quelle commande —, présente
  et indisponible avec ses conditions manquantes. Ailleurs — comptes, rôles, référentiel,
  sauvegarde —, les commandes d'une fonction suivent sa permission de modification dans
  `Session.permissions`, et la restauration sa permission propre, `platform_restore` :
  c'est la règle même du catalogue (WF-ADM-0100), sans condition à nommer. Un refus est rendu par le catalogue des codes d'erreur.
- **Suivi des tâches de fond** : un fournisseur de la coquille garde chaque référence avec
  la commande qui l'a lancée, interroge `getBackgroundTask` par une action serveur tant que
  la tâche court, annonce l'aboutissement ou l'échec (`aria-live`) quel que soit l'écran,
  et offre de relancer. Écarté : un suivi par écran.
- **Courbes** : ECharts importé à la carte, rendu SVG, option `aria` activée, une enveloppe
  maison de quelques lignes. Écarté : echarts-for-react, une dépendance pour trente lignes.
- **Gantt** : un SVG propre, aligné sur les lignes virtualisées de la grille, en lecture
  seule — définitivement. Écarté : ECharts, dont le canvas perdrait l'alignement ligne à
  ligne. **Arborescence de tâches** : `role="tree"`, en lecture.
- **shadcn/ui, Tailwind CSS, Lucide** : shadcn s'installe en copiant du source — les
  composants copiés sont du code du dépôt, soumis à toutes ses règles : en-têtes, lint,
  JSDoc, couverture. *Ceci corrige la conception d'EP-01, qui tenait les dépendances
  d'affichage pour étrangères au code du dépôt.* Radix, leur socle, se verrouille comme
  toute dépendance.

### Langues et textes

- **next-intl, sans langue dans l'URL** : un lien partagé s'ouvre chez chacun dans sa
  langue (WF-INTF-0170). Écarté : un préfixe `/fr` ; react-i18next, pensé pour le client.
- **La langue est une préférence à trois états** — `default`, `fr`, `en` — où `default`
  suit le navigateur. Le front la résout à chaque requête : la préférence si elle est
  fixée, sinon `Accept-Language`, sinon la langue par défaut de l'installation
  (`getInstallation`, lisible sans session). Le compte n'a plus qu'un champ de langue : une des dix
  modifications du cadrage l'y réduit.
- **Catalogues** : clés hiérarchiques en anglais ; une clé par valeur d'énumération
  traduite du contrat (`enums.ProjectState.in_progress`), une par code d'erreur
  (`errors.<CODE>`), une par permission. `make catalogs` (`wftools.catalogs`, dans
  `check-front`) : les deux catalogues portent exactement les mêmes clés, et chaque valeur
  d'énumération comme chaque code du catalogue d'erreurs, lus dans le bundle, a la sienne ;
  next-intl est typé par le catalogue de référence, une clé absente casse
  `make typecheck-front`.
- **Texte en dur** : `react/jsx-no-literals` pour le texte, `no-restricted-syntax` pour les
  attributs lus par l'utilisateur (`aria-label`, `title`, `alt`, `placeholder`) écrits en
  littéral.
- **Formats** : `Intl`, selon la langue ; `Money`, `Decimal` et `Hours` formatés depuis la
  chaîne exacte du contrat, jamais par un flottant ; les dates de planning telles quelles,
  sans fuseau ; les horodatages en heure locale du poste ; la devise, celle du référentiel.
- Le guide reçoit « Clés de traduction », « Ajouter un code côté front » et « Charte
  graphique ».

### Contrôles et tests

- **Vitest** en deux projets, réglés dans `vitest.config.ts`, jamais par un commentaire
  d'environnement : `node` pour la logique et les composants serveur, qui s'exécutent
  côté serveur — un test en navigateur simulé laisserait passer un composant serveur qui
  touche `window` ; `dom` (happy-dom) pour les composants client, par le suffixe
  `.dom.test.tsx`. Écarté : jsdom, dont les corps `Blob` et multipart ne se lisent pas
  sous Vitest. Testing Library et user-event entrent avec les composants.
- **Garde réseau élargie** : `no-restricted-globals` et `no-restricted-properties` déjà en
  place, étendus à `XMLHttpRequest`, `WebSocket`, `EventSource` ; `no-restricted-imports`
  et `import()` refusés pour `openapi-fetch` et les clients http connus. Seul
  `src/api/client.ts` en est exempté — les actions serveur de `src/api/actions/` n'appellent
  que lui, et portent `"use server"`. Un composant client n'importe de `src/api/` que ces
  actions et des types. Un test lint des extraits piégés et attend l'erreur ; la liste des
  dépendances est figée, pour qu'une nouvelle soit examinée pour la garde.
- **Accessibilité** : @axe-core/playwright, niveau AA, sur chaque route de
  `functions.json`, **en clair et en sombre**, à 1366 points puis à l'agrandissement de
  150 % ; parcours au clavier, focus visible. Le helper arrive avec la coquille, chaque lot
  d'écran y ajoute ses routes.
- **Navigateurs** : chromium-fr et chromium-en pour tous les parcours ; les quatre
  navigateurs de la spécification — Chrome et Edge par leurs canaux Playwright, Firefox,
  WebKit pour Safari — pour les parcours de WF-CMP-0010, grilles, Gantt et courbes à 1366
  points, vues d'indicateurs à 360. `make e2e-browsers` les installe tous.
- **Performance** : au palier complet, sur chromium, l'ouverture de la grille de devis de
  mille tâches — du clic à la première ligne rendue — tient en une seconde ; la mesure
  s'écrit au relevé de livraison. Le plafond n'est pas acquis : une réponse `listNodes` de
  plusieurs mégaoctets rendue côté serveur peut le crever, et ce serait alors un constat
  sur le contrat (représentation d'un nœud trop lourde).
- **Complétude des écrans** : `make screens` (`wftools.screens`) confronte
  `functions.json` aux fonctions feuilles de la FBS de la projection — une fonction sans
  adresse fait échouer la chaîne —, et un parcours ouvre chaque route depuis la navigation.

### Modifications du contrat

Les dix de la section « Opérations du contrat », faites avant le code qui les consomme,
chacune avec son entrée dans `docs/api/DECISIONS.md`, `make inventory` et
`make generate-client`. Les constats que feront les écrans s'écrivent dans une section
« Constats sur le contrat » de ce fichier, par le lot qui les trouve, puis se corrigent
dans `docs/api` ou s'ouvrent en issue « Interface contract issue ». Déjà pressentis : la
portée de `getRemainingIndicators`, le tri de `listActualCosts`, la liste des tâches de
fond d'un utilisateur, la révision ouverte par défaut.

### Constats sur le contrat

- `Computable.reason` est une phrase libre, que le front ne peut pas traduire, quand le
  contrat a partout ailleurs remplacé la phrase par un code (`ErrorCode`,
  `CommandCondition`) — US-0100/L1, ouvert en #137. D'ici là, le front affiche le motif tel
  que l'API le donne.
- Le contrat n'a pas de liste des tâches de fond d'un utilisateur : une tâche ne se relit que
  par son `task_id`, que seul l'onglet qui l'a lancée connaît — US-0180/L1, ouvert en #146.
  D'ici là, le suivi garde les références des tâches qui courent dans le stockage de session
  de l'onglet (`sessionStorage`) : un rechargement complet les suit encore, sans la commande
  qui les a lancées — une tâche suivie après un rechargement ne se relance que de son écran —,
  mais un autre onglet ou un autre poste n'en sait rien.

### Ordre de construction

1. Les modifications du contrat ; la garde réseau élargie et le socle des tests de
   composants.
2. La charte, la coquille, l'accueil et les pages système ; le helper d'accessibilité.
3. Les langues : catalogues, formats, `make catalogs`, sélecteur ; les sections du guide.
4. Le bandeau, le signalement, les commandes, le suivi des tâches de fond ; la connexion et
   le compte (US-0320).
5. La grille : lecture et volume (`make mock-data`), calculé contre saisi, saisie au
   clavier, collage, Annuler/Rétablir posées.
6. Les écrans, par famille : projets et révisions ; planning et devis, Gantt et
   arborescence ; reste à engager ; risques ; coûts réels ; indicateurs ; portefeuille ;
   référentiel ; administration et sauvegarde ; import.
7. La clôture : continuité du contexte, parcours bilingue, `make screens`, accessibilité
   sur toutes les routes dans les deux modes, les quatre navigateurs.

---

## US-0090 — Coquille de l'application et contexte de projet

- **statut** : en cours
- **exigences** : `WF-IHM-0010-A`
- **opérations** : `getCurrentSession`, `getMe`, `listProjects`, `getProject`,
  `getSystemStatus`, `getReferenceReadiness`
- **issue** : #73

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
- propre à l'US : à la connexion, l'accueil présente la liste des projets dont l'utilisateur
  est contributeur (décision du cadrage) — un filtre par défaut, visible et levable, jamais
  une restriction de lecture (WF-PRJ-0060) ; ce filtre est la neuvième modification du
  contrat ;
- propre à l'US : la coquille porte les pages système : une adresse inexistante et une
  lecture refusée mènent au même écran « introuvable » — l'écart entre les deux fuirait
  l'existence de l'objet (WF-ADM-0110) ; une API injoignable est annoncée, sans écran
  blanc ; un chargement se voit ; le vide se dit — aucun projet, projet sans révision — et
  une installation dont le référentiel est incomplet guide vers lui
  (`getReferenceReadiness`). Les états vides sont des exemples nommés du contrat ;
- propre à l'US : la charte graphique — couleurs, typographie, espacements, rayons — est
  définie en jetons (les variables de Tailwind et de shadcn/ui), dérivée des logos de
  `docs/assets`, en mode clair et en mode sombre ; aucun composant n'écrit une couleur ni
  une police en dur, et le guide reçoit la section « Charte graphique » — comment on ajoute
  une couleur : par un jeton, jamais dans un composant ; le mode suit le poste par défaut et
  se choisit dans la coquille — une préférence de compte, comme la langue.

**Notes de réalisation.** Les logos de `docs/assets` ont déjà leur variante sombre, et les
jetons du signalement (US-0160) viennent des zones du référentiel, choisis pour le
contraste AA — la revue tient la règle « aucune couleur en dur ». Le contexte de lecture —
projet, révision, sous-projet filtré, date de calcul — est l'état que porte la coquille, et
tout écran le lit. C'est lui que le bandeau
de l'US-0100 affiche et que les filtres des grilles restreignent : le décider ici évite que
chaque écran s'invente le sien.

## US-0100 — Bandeau de contexte de lecture

- **statut** : fini
- **exigences** : `WF-IHM-0020-A`
- **opérations** : `getRevision`, `listRevisions`, `listSubprojects`
- **issue** : #74

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
- **opérations** : `listNodes`, `getMe`, `updateMyPreferences`
- **issue** : #75

**En tant que** chef de projet, **je veux** une grille qui se trie, se filtre, dont je choisis
les colonnes et leur largeur, et qui garde mes en-têtes et mes totaux sous les yeux quand je
défile, **afin de** travailler sur mille tâches sans perdre le fil de ce que je lis.

**Critères d'acceptation.**

- `WF-IHM-0060-A` — « Après défilement de mille lignes, en-têtes et totaux sont toujours
  visibles, de même que la colonne de libellé après défilement horizontal. »
- propre à l'US : le clic d'un en-tête demande le tri au serveur, dans les deux sens, par le
  paramètre du contrat, et la grille rend les lignes dans l'ordre reçu ; les filtres font de
  même, et la ligne de totaux affiche ceux que le serveur rend pour la requête courante —
  rien n'est ordonné ni sommé dans le front ;
- propre à l'US : l'ouverture d'une grille de mille tâches tient l'objectif d'une seconde du
  §4.6.2, mesuré contre le faux back.

**Notes de réalisation.** Composant propre fondé sur TanStack Table (annexe C). C'est le
composant le plus réutilisé de l'application — planning, devis, reste à engager, risques,
coûts réels — et les US-0120 à US-0150 en sont la suite. Le tri et les filtres sont demandés
au serveur (décision du cadrage) : TanStack Table n'ordonne rien en local, et la règle « le
front ne réordonne pas ce que le back ordonne » reste sans exception. Les réglages sont une
préférence d'affichage (WF-ADM-0040), donc personnels et sans effet sur les données.

- écart : `WF-IHM-0060-A` — « Chaque colonne d'une grille se trie dans les deux sens. » : le
  faux back rend toujours le même exemple, quel que soit le paramètre ; le réordonnancement
  effectif se constate en EP-03, sur la première grille servie par le vrai service.
- écart : `WF-IHM-0060-A` — « Les colonnes masquées et les largeurs choisies sont retrouvées
  à la réouverture, et un autre utilisateur ouvrant la même grille voit ses propres
  réglages. » : la conservation passe par `updateMyPreferences`, que le mock accepte sans
  rien garder, et le second utilisateur demande un compte réel — EP-03. Ici, l'écran des
  colonnes et des largeurs existe et écrit la préférence ; rien ne la restitue encore.
- écart : `WF-ADM-0040-A` — « Deux utilisateurs ouvrant le même projet voient les mêmes
  données présentées selon leurs réglages respectifs. » demande deux comptes réels — EP-03.
- écart : `WF-ADM-0040-A` — « Un utilisateur modifie ses préférences et ne peut pas modifier
  celles d'un autre. » est l'affaire de l'US-0190, et demande des comptes réels — EP-03.

## US-0120 — Grille dense : saisie au clavier seul

- **statut** : à faire
- **exigences** : `WF-IHM-0040-A`
- **opérations** : `updateEstimateLine`, `updateTaskFacet`, `listCostCategories`,
  `listResourceRoles`
- **issue** : #76

**En tant que** chef de projet, **je veux** saisir une ligne entière sans toucher la souris,
**afin de** chiffrer plusieurs centaines de lignes à la vitesse à laquelle je les lis.

**Critères d'acceptation.**

- `WF-IHM-0040-A` — « Une ligne de devis complète — libellé, catégorie, rôle, quantité,
  charge — se saisit sans toucher la souris, et la validation de la dernière cellule place le
  curseur sur la ligne suivante. »
- `WF-IHM-0040-A` — « L'abandon d'une saisie en cours laisse la cellule à sa valeur
  antérieure. »
- `WF-IHM-0040-A` — « Les cellules calculées sont traversées sans entrer en saisie. »
- propre à l'US : une quantité ou un montant se saisit au format de la langue — virgule en
  français, point en anglais — et voyage dans le décimal exact du contrat ;
- écart : le recalcul qui suit une saisie tient l'objectif d'une seconde du §4.6.2 — il n'y
  a pas de recalcul sur le faux back ; la mesure revient à EP-06.

## US-0130 — Grille dense : collage depuis un tableur

- **statut** : à faire
- **exigences** : `WF-IHM-0050-A`
- **opérations** : `previewPaste`, `applyPaste`
- **issue** : #77

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
- **opérations** : aucune en propre — `undoLastChange` et `redoLastUndo` attendent EP-06
- **issue** : #78

**En tant que** chef de projet, **je veux** annuler mes saisies une par une et rétablir ce que
je viens d'annuler, **afin de** corriger une fausse manœuvre sans reconstruire à la main ce
qu'elle a défait.

**Critères d'acceptation.**

- `WF-IHM-0110-A` — « Aucune commande n'annule un marquage, un import appliqué ou une
  exclusion de ligne de coût. »
- propre à l'US : Annuler et Rétablir sont présentes et positionnées — dans les grilles, au
  menu et par Ctrl+Z et Ctrl+Maj+Z — et leur état se lit ; aucune n'est branchée : elles
  n'agissent qu'en EP-06 (décision du cadrage).

**Notes de réalisation.** L'annulation sera portée par le serveur (`undoLastChange`), non
par une pile dans le navigateur : c'est ce qui permet le refus en cas de conflit, et ce que
WF-ARC-0070 impose. EP-06 branchera ces commandes ; les poser au bon endroit dès la maquette
évite de redessiner les grilles à ce moment-là.

- écart : `WF-IHM-0110-A` — « La suppression d'une tâche puis son annulation restituent la
  tâche, ses lignes et ses liaisons. », « Cinquante modifications successives s'annulent une
  par une, puis se rétablissent dans l'ordre. » et « L'annulation d'une modification qu'un
  autre contributeur a depuis reprise est refusée en nommant l'objet en conflit. » demandent
  un serveur qui restitue et qui refuse — le faux back ne conserve rien. Ces trois phrases
  reviennent à EP-06, où la grille de planning conserve ses saisies : ici, les commandes se
  voient et se placent, elles n'agissent pas (décision du cadrage).

## US-0150 — Valeur calculée contre valeur saisie

- **statut** : à faire
- **exigences** : `WF-IHM-0030-A`
- **opérations** : aucune en propre
- **issue** : #79

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
(`docs/api/DECISIONS.md`). Mais le schéma ne suffit pas à la ligne : une date de tâche est
saisie en mode manuel et calculée en mode automatique, et seul le serveur le sait. Chaque
nœud porte donc la liste de ses champs calculés (`computed_fields`, modification du
cadrage) : le front la lit, ligne par ligne, au lieu de recopier une règle.

## US-0160 — Échelle de signalement commune, lisible sans couleur

- **statut** : en cours
- **exigences** : `WF-IHM-0070-A`
- **opérations** : aucune en propre
- **issue** : #80

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

- **statut** : fini
- **exigences** : `WF-IHM-0090-A`
- **opérations** : `getProject`, `getRevision`, `getCurrentSession`, `listPermissions`
- **issue** : #81

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
recopiée dans le front (WF-ARC-0020) : le projet et la révision portent leurs commandes
disponibles et ce qui manque à chacune (`available_commands`, modification du cadrage —
`getProjectNextState` ne couvrait que les transitions d'avant En cours), les codes de
permission sont énumérés au contrat, et l'enveloppe d'erreur porte un code et ses paramètres
que le front rend en phrase (WF-ARC-0110). Griser un bouton reste une commodité de lecture,
pas une protection.

## US-0180 — Traitements longs : suivi et signalement

- **statut** : fini
- **exigences** : `WF-IHM-0080-A`
- **opérations** : `getBackgroundTask`, `getBackgroundTaskResult`, `markRevision`
- **issue** : #82

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
(WF-ARC-0090), qui porte désormais les neuf genres d'opérations longues, fusion d'une
structure et survenance d'un risque comprises (modification du cadrage) : le suivi est un
composant de la coquille, commun à toutes les tâches, et non un morceau d'écran par action
longue.

## US-0190 — Langue de l'interface, catalogues et formats d'affichage

- **statut** : en cours
- **exigences** : `WF-INTF-0160-A`, `WF-INTF-0170-A`, `WF-INTF-0180-A`, `WF-ADM-0040-A`, `WF-QUA-0070-A`, `WF-DAT-0100-A`
- **opérations** : `getMe`, `updateMyPreferences`, `getInstallation`
- **issue** : #83

**En tant que** chef de projet, manager ou administrateur, **je veux** l'interface dans ma
langue, choisie par mon navigateur puis par moi, sans que cela change une donnée ni un
montant, **afin de** travailler dans la langue que je lis et de partager les mêmes projets
que mes collègues.

**Critères d'acceptation.**

- `WF-INTF-0160-A` — « Un utilisateur dont le navigateur demande l'anglais obtient l'interface
  en anglais à sa première connexion, un autre demandant le français l'obtient en français. »
- `WF-INTF-0160-A` — « Un utilisateur dont le navigateur demande une langue non offerte
  obtient la langue par défaut de l'installation. » — la résolution est dans le front, et la
  langue par défaut vient de `getInstallation`, lisible sans session, que le faux back sert.
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
- `WF-DAT-0100-A` — « Une tâche planifiée au 30 juin s'affiche au 30 juin sur tout poste
  client, quel que soit son fuseau. » — les dates de planning s'affichent telles quelles,
  sans conversion ; les horodatages, eux — date de calcul d'un indicateur, colonnes
  d'audit —, s'affichent en heure locale du poste (décision du cadrage).
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

La langue est une préférence de compte à trois états — `default`, `fr`, `en` —, où `default`
suit le navigateur ; dès qu'elle est fixée, elle prime (décision du cadrage). Le front la
résout à chaque requête — la préférence, sinon `Accept-Language`, sinon la langue par défaut
de l'installation, que `getInstallation` rend sans session — et le compte n'a plus qu'un
seul champ de langue.

- écart : `WF-ADM-0040-A` — « Un utilisateur modifie ses préférences et ne peut pas modifier
  celles d'un autre. » demande des comptes réels — EP-03.
- écart : `WF-ADM-0040-A` — « Deux utilisateurs ouvrant le même projet voient les mêmes
  données présentées selon leurs réglages respectifs. » est l'affaire de l'US-0110, et
  demande deux comptes réels — EP-03.
- écart : `WF-INTF-0160-A` — « Un utilisateur qui force le français le retrouve en se
  connectant depuis un autre poste dont le navigateur demande l'anglais. » : la conservation
  du choix dans le compte demande un compte réel — EP-03.
- écart : `WF-DAT-0100-A` — « La somme des montants budgétés d'une révision est identique
  quel que soit l'ordre de sommation. » et « Un montant de 0,10 additionné dix fois donne
  exactement 1,00. » sont des phrases du noyau de calcul — amorcées en EP-03, closes en
  EP-07.
- écart : `WF-INTF-0180-A` — « Un devis exporté par un utilisateur en français et réimporté
  par un utilisateur en anglais donne un devis identique, sans avertissement de format. » et
  « Le fichier Excel exporté porte les mêmes en-têtes quelle que soit la langue de celui qui
  l'exporte. » attendent les échanges de fichiers — EP-12 ; ici, seul l'affichage.

## US-0200 — Accessibilité minimale

- **statut** : à faire
- **exigences** : `WF-IHM-0100-A`
- **opérations** : aucune en propre
- **issue** : #84

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
  ne reprend pas ; un contrôle automatisé d'accessibilité le vérifie dans la chaîne ;
- propre à l'US : le contrôle de contraste joue en mode clair et en mode sombre — la charte
  existe dans les deux (US-0090), et un mode qui n'est pas contrôlé dérive.

**Notes de réalisation.** Le contrôle de contraste est exécuté par la chaîne, sinon il n'est
fait qu'une fois. Aucune conformité complète à un référentiel n'est visée ni déclarée
(§2.2) : ces quatre points, et rien de plus.

**Hors périmètre.** L'aide en ligne, qui n'est pas dans cet EPIC.

## US-0210 — Écrans du projet, des révisions et des contributeurs

- **statut** : à faire
- **exigences** : aucune en propre — les exigences de ces fonctions sont réalisées en EP-04
- **opérations** : `listProjects`, `getProject`, `listProjectStateTransitions`,
  `exitProject`, `listSubprojects`, `listContributors`, `listRevisions`, `getRevision`,
  `compareRevisions`, `listCostStructures`, `getRateUpdateProposal`
- **issue** : #85

**En tant que** chef de projet, **je veux** les écrans de la liste des projets, du projet, de
ses sous-projets, de ses contributeurs, de ses révisions, de leurs structures de coûts et de
la proposition de mise à jour des taux, **afin de** voir si le contrat sait dire tout ce
qu'ils ont à montrer.

**Critères d'acceptation.**

- propre à l'US : chaque écran s'alimente du faux back par le client engendré, sans qu'aucune
  donnée soit écrite dans le front ;
- propre à l'US : l'écran de comparaison de deux révisions présente ce que `compareRevisions`
  renvoie, sans rapprochement calculé dans le front ;
- propre à l'US : aucun de ces écrans ne propose de créer ni de modifier — projet,
  révision, contributeurs : ces formulaires appartiennent à l'EPIC de leur domaine (décision
  du cadrage) ; seule la sortie du cycle de vie, commande du §3.6, s'y exerce ;
- propre à l'US : tout manque du contrat constaté ici est écrit dans cet EPIC, puis corrigé
  dans `docs/api` ou ouvert en issue.

## US-0220 — Écrans du planning et du devis

- **statut** : à faire
- **exigences** : aucune en propre — EP-06 et EP-07
- **opérations** : `getWorkBreakdown`, `listNodes`, `createNode`, `updateTaskFacet`,
  `setPredecessors`, `listTimelines`, `listCostStructures`, `updateEstimateLine`,
  `getEstimateIndicators`, `getMissingRates`
- **issue** : #86

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
  `getRemainingIndicators`, `setLineRemaining`, `listStartableTasks`, `listActualCosts`,
  `listCostImports`
- **issue** : #87

**En tant que** chef de projet, **je veux** les écrans des risques et de leur matrice, du
reste à engager, de l'avancement et des coûts réels, **afin de** vérifier que la maquette
porte le cycle d'une revue mensuelle de bout en bout.

**Critères d'acceptation.**

- propre à l'US : la matrice de risques emploie le composant de signalement de l'US-0160 ;
- propre à l'US : la gravité et la provision d'un risque sont présentées comme calculées
  (US-0150) ;
- propre à l'US : l'écran d'avancement ne propose aucun pourcentage à saisir — une tâche est
  terminée ou elle ne l'est pas ; démarrer ou terminer une tâche est une commande de l'EPIC
  des coûts réels et de l'avancement, pas de la maquette.

## US-0240 — Écrans des indicateurs et du portefeuille

- **statut** : à faire
- **exigences** : aucune en propre — EP-10 et EP-11
- **opérations** : `getProjectIndicators`, `getCostCurve`, `getEarnedValueCurves`,
  `getProjectCashOut`, `getMilestoneTracking`, `getProjectWorkload`, `getPortfolioProjects`,
  `getPortfolioValue`, `getPortfolioPerformance`, `getPortfolioWorkload`,
  `getPortfolioCostStructure`, `getPortfolioRisks`, `getPortfolioCashOut`,
  `getPortfolioPilotHealth`
- **issue** : #88

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
  `listHourlyRates`, `setHourlyRate`, `listUsers`, `listAccessRoles`, `listPermissions`,
  `getSystemStatus`, `listBackups`, `getBackupSchedule`
- **issue** : #89

**En tant qu'**administrateur, **je veux** les écrans du référentiel, des comptes, des rôles
d'habilitation, de l'état du système et de la sauvegarde, **afin de** vérifier qu'ils
s'atteignent sans projet ouvert et que la matrice des permissions se lit.

**Critères d'acceptation.**

- propre à l'US : ces écrans sont atteignables sans qu'aucun projet ne soit ouvert (US-0090) ;
- propre à l'US : la grille des taux horaires, qui porte quinze ans de valeurs pour cent
  cinquante rôles, emploie le composant de grille dense ;
- propre à l'US : l'écran des rôles d'habilitation présente les permissions par fonction de
  second niveau, telles que `listPermissions` les renvoie ;
- propre à l'US : l'écran de sauvegarde et de restauration (FBS-1.4) présente les sauvegardes
  et leur planification telles que le contrat les rend, sans déclencher ni sauvegarde ni
  restauration — commandes de l'EPIC d'exploitation.

## US-0260 — Écran d'import en deux temps

- **statut** : à faire
- **exigences** : aucune en propre — EP-09 et EP-12
- **opérations** : `uploadFile`, `openImport`, `getImport`, `abandonImport`, `applyImport`,
  `listImports`, `requestExport`
- **issue** : #90

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

- **statut** : en cours
- **exigences** : `WF-ARC-0020-A`
- **opérations** : aucune
- **issue** : #91

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
- **issue** : #92

**En tant que** chef de projet, **je veux** que les grilles, le Gantt et les courbes
fonctionnent sur le navigateur de mon poste, et consulter les indicateurs depuis mon
téléphone, **afin de** ne rien installer et de répondre à une question sur un projet loin de
mon bureau.

**Critères d'acceptation.**

- `WF-CMP-0010-A` — « Les vues d'indicateurs se lisent sur un écran de 360 points de large et
  n'y proposent aucune saisie. »
- `WF-CMP-0010-A` — « Aucune fonction n'exige une installation sur le poste. »
- propre à l'US : les parcours des grilles, du Gantt et des courbes se jouent dans la chaîne
  sur les quatre navigateurs de la spécification — Chrome et Edge par leurs canaux
  Playwright, Firefox, et WebKit tenant lieu de Safari —, en version courante, à 1366 points
  de large ;
- écart : `WF-CMP-0010-A` — « Les grilles, le diagramme de Gantt et les courbes s'affichent et
  s'utilisent sur chacun des quatre navigateurs, dans leurs deux dernières versions majeures,
  à 1366 points de large. » : la version majeure précédente et le Safari réel ne se rejouent
  pas par l'outillage ; ils se constatent en recette, sur la plateforme déployée — EP-13.

**Notes de réalisation.** Le harnais d'EP-01 ne joue que Chromium : c'est cette US qui lui
ajoute les quatre navigateurs — Chrome et Edge sont des canaux de Chromium dans Playwright,
Firefox et WebKit ses deux autres moteurs, et le Safari réel reste à la recette (EP-13) —
et les deux largeurs, 1366 points partout, 360 pour les vues d'indicateurs.

## US-0320 — Connexion et compte personnel

- **statut** : à faire
- **exigences** : aucune en propre — l'authentification réelle est EP-03
- **opérations** : `listAuthProviders`, `openSession`, `closeSession`, `startOidcSession`,
  `requestPasswordReset`, `confirmPasswordReset`, `getMe`, `updateMyPreferences`,
  `changeMyPassword`, `putMyAvatar`, `deleteMyAvatar`
- **issue** : #93

**En tant que** chef de projet, manager ou administrateur, **je veux** l'écran de connexion —
compte local, annuaire, fournisseur d'identité — et celui de mon compte : mes préférences,
ma langue, mon mot de passe, mon avatar, **afin que** l'entrée dans Waterfall existe avant
qu'EP-03 ne la branche sur une authentification réelle.

**Critères d'acceptation.**

- propre à l'US : l'écran de connexion présente les fournisseurs que `listAuthProviders`
  rend — le compte local toujours, l'annuaire et le fournisseur d'identité quand
  l'installation les active — et le mot de passe oublié en deux temps ;
- propre à l'US : la connexion aboutit parce que le faux back répond, et mène à la liste des
  projets ; la déconnexion ramène à la connexion ;
- propre à l'US : l'écran du compte porte les préférences et la langue (US-0190), le
  changement de mot de passe et l'avatar ; aucune règle de mot de passe n'est recopiée dans
  le front — un refus est un code du catalogue ;
- propre à l'US : une session qui expire en cours de route (401) mène à la connexion et, la
  connexion refaite, ramène à l'écran visé — constaté au niveau des composants, par
  l'exemple nommé du contrat.

**Notes de réalisation.** EP-03 attend « les écrans de connexion, des comptes et des rôles de
la maquette, branchés sur le service » : cet écran de connexion est celui qu'il branchera.
La session que le faux back accorde est celle dont toute la maquette part, et cette US lui
donne enfin une porte d'entrée visible.
