---
id: EP-02
titre: Tous les écrans, navigables, alimentés par le faux back, avant toute règle métier
statut: en cours
depend_de: EP-01
famille: front
issue: 72
---

# EP-02 — Maquette du front sur contrat simulé

## Objet

Construire l'application web entière contre le faux back d'EP-01 : la navigation, les
composants d'interface de PBS-1.3, les exigences du §3.6 qu'il réalise, les deux langues, et
chaque fonction adressable à l'écran. Rien n'est calculé par le front — c'est le mock qui
répond.
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
| `WF-IHM-0060-A` | Lecture d'une grille | début — close en EP-07 | US-0110 |
| `WF-IHM-0070-A` | Une échelle de signalement commune, lisible sans couleur | entière | US-0160 |
| `WF-IHM-0080-A` | Traitements longs | début — close en EP-04 | US-0180 |
| `WF-IHM-0090-A` | Refus et commandes indisponibles | entière | US-0170 |
| `WF-IHM-0100-A` | Accessibilité minimale | entière | US-0200 |
| `WF-IHM-0110-A` | Annulation et rétablissement des saisies | début — close en EP-06 | US-0140 |
| `WF-IHM-0130-A` | Filtrage des tables et export des graphiques | début — close en EP-11 | US-0240 |
| `WF-INTF-0160-A` | Choix de la langue de l'interface | début — close en EP-03 | US-0190 |
| `WF-INTF-0170-A` | Ce qui est traduit et ce qui ne l'est pas | entière | US-0190 |
| `WF-INTF-0180-A` | Formats indépendants de la langue | début — close en EP-12 | US-0190 |
| `WF-ADM-0040-A` | Préférences d'affichage | début — close en EP-04 | US-0110, US-0190 |
| `WF-DAT-0100-A` | Types des grandeurs | début — close en EP-07 | US-0190 |
| `WF-QUA-0070-A` | Complétude des traductions | entière | US-0190 |
| `WF-CMP-0010-A` | Navigateurs et affichage | début — close en EP-13 | US-0290 |

Le §3.6 compte treize exigences ; cet EPIC en réalise douze, et en clôt huit : elles portent
sur l'interface, et l'interface existe ici pour de bon. La treizième, WF-IHM-0120 (l'écran
d'accueil), se réalise et se clôt en EP-04 (cadrage d'EP-03). Neuf exigences ne font que commencer, et leurs US
disent quelle phrase attend quoi : WF-IHM-0060 (le tri effectif des tables et les réglages par compte —
EP-03, le devis ordonné — EP-07), WF-IHM-0080 (le marquage de dix mille objets, sur le marquage réel — EP-04),
WF-IHM-0110 (l'annulation qui restitue — EP-06), WF-IHM-0130 (des totaux que le filtre
restreint, calculés par un serveur réel — EP-11), WF-ADM-0040 et WF-INTF-0160 (la
conservation des préférences et de la langue dans le compte — EP-03 ; deux utilisateurs
sur un même projet — EP-04), WF-INTF-0180 (le
format des fichiers d'échange — EP-12), WF-CMP-0010 (la version majeure précédente et le
Safari réel — EP-13, en recette), et WF-DAT-0100 (l'affichage des dates sans fuseau est
ici ; les sommes exactes sont au noyau — EP-03, closes en EP-07). WF-IHM-0130 touche aussi
les grilles et le Gantt d'US-0110, US-0220 et US-0230, qui filtrent par le serveur, et dont
l'export PNG se clôt en EP-11.

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
- les exigences du §3.6 que cet EPIC réalise — de WF-IHM-0010 à WF-IHM-0110, et WF-IHM-0130
  — ont chacune au moins un test de bout en bout qui les cite ;
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
| `frontend/src/app/` | les routes, en anglais : `/` (l'accueil), `/login`, `/account/…` (le compte : préférences, mot de passe, avatar), `/projects/[projectId]/<fonction>` pour les fonctions du projet lui-même (`revisions`, `settings`, `lifecycle`), `/projects/[projectId]/revisions/[revisionId]/<fonction>` pour celles d'une révision (`planning`, `estimate`, `remaining`, `risks`, `actual-costs`, `indicators`…), `/portfolio/…`, `/reference/…`, `/admin/…`, `/system`, et la page « introuvable » |
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
- **La mise en page suit la maquette validée par l'utilisateur** (2026-09-29,
  https://claude.ai/artifact/FZCXeHGRQVZEjgaooh9vJf) : shadcn/ui partout où un composant
  existe ; la barre latérale est le Sidebar de shadcn, repliable en rail d'icônes ; la barre
  du haut porte à droite l'avatar, qui déroule le menu du compte — préférences, mot de
  passe, avatar, déconnexion ; une icône Lucide sur chaque entrée, chaque bouton et chaque
  nature de ligne. Le style est sobre et professionnel, sans autre ornement que les icônes.
  Les grilles sont denses — le plus d'informations sous les yeux —, les écrans d'indicateurs
  aérés. Le lot US-0090/L4 (#149) refait la coquille ainsi, avant la grille.

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
- **Les lectures du témoin** (#287, EP-02/L20 et L21) : le cœur lisible du projet témoin est
  décrit une fois (`wftools.mockwitness`), daté en heures sur ses calendriers et chiffré
  (`wftools.mockcore`), et les exemples nommés de `listNodes` — `nodes`, `nodes_planning`,
  `nodes_estimate`, `nodes_milestone`, `nodes_risk_occurred` — comme les `dependencies_*`
  sont des lectures de ce seul arbre, que `make mock-data` écrit sous `fixtures/api/` par
  leur nom et que la chaîne vérifie à jour : un nœud y a un identifiant, une lignée et des
  montants, quel que soit l'exemple (`docs/api/DECISIONS.md`, « L'univers témoin »).
  Écarté : les écrire à la main, où deux exemples se contredisaient sur les mêmes
  identifiants.

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
    `undoLastChange` et `redoLastUndo`. Le menu est le menu contextuel de la cellule (clic
    droit, Maj+F10, touche Menu), à côté des boutons de la barre de la grille (US-0140/L1,
    décision confirmée par l'utilisateur le 2026-10-07). Écarté : un menu
    « Édition » dans la barre, qui ne faisait que doubler les deux boutons.
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
  et offre de relancer. Il suit les tâches de l'utilisateur qui courent, que le layout racine
  demande pour une session ouverte et lui transmet sans que le document les attende, et les
  relit quand l'onglet redevient visible (`listBackgroundTasks`, EP-02/L4) ; une tâche trouvée
  ainsi se relance depuis son écran.
  Écarté : un suivi par écran.
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
  mille tâches — du clic à la grille utilisable, dessinée et hydratée — se mesure contre
  l'objectif d'une seconde ; la mesure s'écrit au journal, au résumé de la chaîne et au relevé
  de livraison, sans bloquer : contre le faux back, sur une machine partagée de la chaîne, elle
  ne dit pas ce que tiendra le service, et la seconde bloquante revient à EP-13. Le plafond n'est pas acquis : une
  réponse `listNodes` de plusieurs mégaoctets rendue côté serveur peut le crever, et ce serait
  alors un constat sur le contrat (représentation d'un nœud trop lourde).
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

**Révision de la spécification du 2026-10-03 (EP-02/L7).** La spécification revue (#207) impose
au contrat, avant les lots restants : une durée et un décalage dans l'unité de leur saisie
(`Duration`, `Lag`, WF-PLA-0160, WF-PLA-0030), à la place de `duration_days`, `lag` et
`lag_unit`, et les constantes de conversion en ressource du référentiel
(`GET`/`PUT /reference/duration-units`) ; le début et la fin d'une tâche en date et heures de
travail écoulées (`WorkInstant`, WF-DAT-0100), `start` et `finish` à la place de `start_date`
et `finish_date`, sur la facette, dans les champs calculés et dans le tri ; la permission
`all_projects_read`, la qualité de contributeur (`Contributor.kind`, `ContributorsWrite`), la
condition `is_project_manager` et le code `NOT_PROJECT_MANAGER`, et `listProjects` qui ne rend
que les projets ouvrables (WF-PRJ-0060, WF-ADM-0100, WF-ADM-0110) ; des filtres sur toute liste
dont l'écran présente les colonnes, et le tri de la liste du portefeuille (WF-IHM-0130) ; les
décaissements rendus par `getCostCurve` avec `payment_delays`, `getProjectCashOut` et `CashOut`
retirés (WF-IND-0100, WF-IND-0120 retirée) ; `getIndexHistory` (WF-IND-0130) ; le motif d'une
transition (`StateTransition.reason`, #185) ; `inflated_amount` sur la ligne de devis
(WF-DEV-0050), `finish_overdue` sur la tâche (WF-RAE-0040), `uses_inactive_object` sur la ligne
(WF-REF-0010) ; la base du plan de charge (`basis`, WF-DEV-0070) ; la part de la provision sur
les lignes fusionnées d'un risque survenu (WF-RIS-0060, exemple `nodes_risk_occurred` — abandonnée
par la révision du 2026-10-04 : ces lignes sont budgétées à zéro, voir ci-dessous) ;
`delta_to_reference` sur la ligne du portefeuille (WF-PTF-0040). Chaque forme est consignée
dans `docs/api/DECISIONS.md`, « Révision de la spécification du 2026-10-03 ». Le front n'est
touché que là où le client engendré ne compilait plus : la grille de planning écrit la durée
par sa valeur et son unité, et les dates par leur date.

**Révision de la spécification du 2026-10-04 (PR #328, fusionnée dans la branche le 2026-10-06).**
Les provisions ne font jamais partie du budget de référence, la révision de référence conserve une
réserve pour risques, la couverture des risques est une lecture (`getProjectRiskCoverage`,
`RemainingIndicators.coverage`, `PortfolioRisks.coverage`, `ProvisionTotals.reserve`), la survenance
d'un risque fusionne son devis propre dans la révision en cours à montant budgété nul sans
marquage (`RiskOccurrence` sans `version_name`, `steps[].cause` à `amendment` seul) ; FBS-2.6
devient la courbe en S du portefeuille, une seule opération `getPortfolioCostCurve` avec
`payment_delays`, `getPortfolioCashOut` retirée, permission `portfolio_cost_curve`. Les exemples
`nodes_risk_occurred`, `risks`, `risk_matrix`, `remaining_indicators*` et les volumes suivent ;
l'univers témoin reste à refaire sur ce modèle (L20 à L27, #287). Ce que la révision demande et
que le contrat ne portait pas a été ouvert en constats #381 à #389, fermés par EP-02/L29 (#392) :
l'année de référence d'une révision, le rattachement d'une récapitulative au lotissement, le compte
rendu d'import en aller-retour, les trois permissions de WF-ADM-0100, `deleteRisk`, le code de
sous-projet d'une ligne de coût, le tri des tables plates, le lien de fixation du mot de passe et
`can_open`. Chaque forme est consignée dans `docs/api/DECISIONS.md`, « Révision de la
spécification du 2026-10-04 » et « Ce que la révision de la spécification demande (EP-02/L29) ».

**Constats d'EP-02 tranchés (EP-02/L30, #393).** Les constats #238, #244, #348, #352, #359, #360,
#362, #364 et #365, selon les décisions de l'auteur du 2026-10-07, et les suites de la
spécification modifiée par les PR #410 et #418 : toute tâche porte son rattachement au lotissement,
la tâche d'un lot restant sous celle de son poste (`WORK_PACKAGE_OUTSIDE_ORDER_ITEM`,
`SUMMARY_TASK_REQUIRED` retiré) ; la marge totale signée ; le refus d'une saisie qui laisserait une
tâche sans heure travaillée (`TASK_WITHOUT_WORKING_HOURS`) ; les commandes d'un risque
(`Risk.available_commands`) ; la saisie des risques devenue une commande de la révision
(`edit_risks`), annulable, le projet la gardant tant qu'il n'a pas de révision en cours ; le refus d'une ligne de provision
créée à la main (`PROVISION_CATEGORY_RESERVED`) ; la révision en cours suspendue pendant l'application d'un import ou une
survenance ; `listBackups` sans 403 ; les indicateurs de devis à l'année de référence ; la révision
exigée d'un export ; le nœud nommé par le plan de charge ; le prédécesseur d'un écart de liaison ;
les courbes d'une révision marquée et les colonnes conservées d'une ligne de coût. Chaque forme est
consignée dans `docs/api/DECISIONS.md`, « Les constats d'EP-02 tranchés (EP-02/L30) ».

### Constats sur le contrat

- `Computable.reason` était une phrase libre, que le front ne pouvait pas traduire, quand le
  contrat a partout ailleurs remplacé la phrase par un code (`ErrorCode`,
  `CommandCondition`) — US-0100/L1, ouvert en #137. Corrigé par EP-02/L4 : `reason` est un
  code (`NotComputableReason`), un par grandeur nulle au dénominateur des indicateurs du
  §3.4.5.8 et des autres `Computable` du contrat, que `ComputedIndicator` rend par le
  catalogue ; les exemples ne portent plus de phrase. L'avancement physique d'une
  récapitulative (`TaskFacet.physical_progress`) devient un `Computable`, qui peut dire qu'il
  n'est pas calculable faute de montant budgété dans son sous-arbre (`no_budgeted_amount`,
  WF-IND-0060) ; la grille de planning le lira avec le Gantt (#114).
- Le contrat n'avait pas de liste des tâches de fond d'un utilisateur : une tâche ne se
  relisait que par son `task_id`, que seul l'onglet qui l'a lancée connaît — US-0180/L1,
  ouvert en #146. Corrigé par EP-02/L4 : `listBackgroundTasks` (`GET /tasks`) rend les tâches
  de l'appelant, celles qui courent et celles finies depuis une date, et `BackgroundTaskStatus`
  est nommé. Le suivi de la coquille suit, pour une session ouverte, celles qui courent — le
  layout racine les demande côté serveur et les lui transmet sans que le document les attende —
  et celles qu'il relit chaque fois que l'onglet redevient visible, en plus des références que
  garde le stockage de session de l'onglet (`sessionStorage`), qui porte aussi le nom que
  l'utilisateur leur a donné : un autre onglet, un autre poste les retrouvent. Une tâche trouvée
  par la liste ou le stockage vient sans la commande qui l'a lancée, et se relance depuis
  l'écran de son objet. Reste hors de portée l'annonce d'une tâche lancée ailleurs et finie
  entre deux lectures : elle ne court plus, la liste ne la rend pas. `finished_since` ne le règle pas simplement — sa date est celle du
  serveur, que l'horloge du poste ne vaut pas, et l'onglet qui l'a lancée l'a déjà annoncée —,
  ce qui demanderait un curseur rendu par la liste elle-même.
- Deux signalements n'avaient pas de zone au contrat — le dépassement du budget d'un
  sous-projet (`SubprojectBalance.is_over_budget`) et les signaux de santé du pilotage
  (`PilotHealth.signals`) — US-0160/L1, ouvert en #139. Corrigé par EP-02/L4 : chacun porte sa
  `zone` (`AlertZone`), que le serveur classe, avec leurs exemples (`remaining_indicators`,
  `remaining_indicators_over_budget`, `pilot_health`) ; les écrans qui les montrent (#115,
  #120) les rendront par `Signal`.
- `listStartableTasks` et `setLineRemaining` n'avaient aucun exemple : le faux back aurait tiré le
  Kanban et la réponse d'une réestimation de leurs schémas — US-0230/L1. Corrigé par ce lot, comme
  les ajouts de lecture des lots d'écran, par des exemples engendrés du cœur du témoin
  (`make mock-data`) : `startable_tasks` (au 3 juin 2026, deux tâches démarrées, aucune non démarrée),
  `startable_tasks_milestone` (le câblage déclaré terminé ce jour-là, la réception usine gardée au
  30 juin et signalée à terminer) et
  `remaining_reestimated` (10 h au taux de 80,00, 800,00 réestimés).
- La grille de reste à engager ne peut présenter les grandeurs d'une ligne au reste à engager
  précédent (WF-RAE-0040) : `EstimateLineFacet` n'en porte qu'un jeu, celui de la révision lue, et
  le seul montant précédent — US-0230/L1, ouvert en #424. D'ici là, la grille présente le montant
  budgété, le montant réestimé précédent, les grandeurs courantes, saisies par `setLineRemaining`,
  et le montant réestimé courant.
- `listStartableTasks` ne rend pas les tâches terminées, que le Kanban rouvre (WF-RAE-0030), ni les
  tâches non démarrées dont un prédécesseur ne l'est pas — US-0230/L1, ouvert en #425. D'ici là, le
  Kanban présente les deux colonnes que l'opération rend, non démarrées et démarrées.
- `listTimelines` n'avait aucun exemple, et aucune tâche témoin ne portait d'inscription
  (`TaskFacet.tracking`) : l'écran des chronologies n'aurait rien eu à montrer — US-0220/L2. Corrigé
  par ce lot, par des exemples engendrés du cœur du témoin (`make mock-data`) : `timelines` (le
  comité de pilotage et la revue client, famille d'identifiants « chronologies », 1000 à 1009) et
  les inscriptions des tâches du cœur — les études, les deux réceptions et la mise en service au
  comité, les deux réceptions à la revue client, et les deux jalons du diagramme temps/temps
  (`milestone_tracking`) au suivi temps/temps, ceux que `milestone_tracking` suit déjà.
- `listNodes` ne filtre ni sur la récapitulative ni sur le niveau, ni sur l'inscription à une
  chronologie : l'arborescence de tâches (WF-PLA-0110) et une chronologie (WF-PLA-0140) ne peuvent
  demander au serveur les seules tâches qu'elles montrent — US-0220/L2, ouvert en #463. D'ici là,
  l'arborescence garde, des tâches que le serveur rend dans l'ordre du plan, les récapitulatives
  dont le niveau que l'API calcule est dans la profondeur demandée (`depth`, dans l'adresse), et
  une chronologie les tâches dont les inscriptions la nomment, sans rien ordonner ni calculer.
- Le 401 n'est pas déclaré sur la plupart des opérations gardées par la session —
  US-0170/L1, ouvert en #141. D'ici là, le décodeur le traite quand il arrive, mais les
  tests ne peuvent pas le simuler sur ces opérations. Corrigé par EP-02/L8 : cent dix
  opérations déclarent leur 401, et une règle d'assertion de `docs/api/redocly.yaml`
  (`rule/session-operation-declares-401`) l'exige de toute opération dont `security` est
  absent, une opération publique le disant par `security: []` ; le cas de la session perdue
  pendant une saisie peut désormais se simuler sur `updateEstimateLine` et `updateTaskFacet`,
  et le test qui l'écrit est demandé en #224. Fait par EP-02/L11 : la cellule revient à sa valeur
  et l'avis mène à la connexion, qui ramène à l'écran.
- `correlation_id` n'a pas de motif, ni de longueur minimale — US-0090/L2, ouvert en #144.
  D'ici là, le front le préfixe dans le digest de Next et traite une valeur vide comme
  absente. Corrigé par EP-02/L8 : `Problem.correlation_id` porte le motif
  `^[A-Za-z0-9._-]{1,64}$`, jamais vide ; le front garde son préfixe dans le digest.
- `CommandCondition` n'avait pas de condition « traitement en cours » : pendant un marquage,
  une révision relue listait toujours `mark` disponible — US-0180/L1, ouvert en #147
  (décision de l'utilisateur). Corrigé par EP-02/L4 : le serveur nomme
  `no_background_task_running` dans `missing_conditions` des commandes qu'un traitement de fond
  en cours rendrait caduques, quel que soit l'utilisateur qui l'a lancé (exemple `marking` de
  `getRevision`) ; `Command` la dit comme toute condition. Le suivi offre toujours « Recharger
  l'écran » à l'aboutissement d'une tâche, qui relit la révision.
- `AuthProvider.start_url` ne dit pas ce qu'il désigne — l'adresse de `startOidcSession` vue du
  navigateur, ou celle du fournisseur —, et le 303 de `startOidcSession` ne déclare pas son
  `Location` — US-0320/L1, ouvert en #152. D'ici là, la page de connexion offre le fournisseur
  d'identité par un lien vers `start_url`, et ne l'offre pas sans lui.
- La taille admise d'un avatar n'est pas au contrat, quand Next borne le corps d'une action
  serveur à 1 Mo — US-0320/L1, ouvert en #153. D'ici là, une image plus lourde échoue avant
  l'API, sur l'écran de panne. Corrigé par EP-02/L8 : `Installation.avatar_max_bytes`, lisible
  sans session, dit la borne, que `putMyAvatar` cite ; le front la lira et réglera son corps
  dans #221. Borné par EP-02/L15 (#233) : 8 Mio au plus (`maximum`), sous la taille de corps que le front règle d'avance.
- L'adresse du front que vise le lien de réinitialisation du mot de passe, écrit par l'API dans le courriel, n'est pas au contrat — US-0320/L1, ouvert en #154. D'ici là, le front attend `/login/reset?token=…`.
- Aucun code d'erreur ne nomme une règle du mot de passe, et le front ne rend pas encore `Problem.fields` — US-0320/L1, ouvert en #155. D'ici là, un mot de passe refusé l'est par « Les données saisies ne sont pas valides. ».
- La connexion par le fournisseur d'identité ne peut pas ramener à l'écran visé : `start_url` ne transmet pas `next`, et `completeOidcSession` répond 303 « vers l'application » — US-0320/L1, #152. D'ici là, elle mène à l'accueil.
- `Predecessor` ne nommait sa tâche que par `predecessor_node_id` : la grille de planning tirait le numéro de ligne d'un prédécesseur de la même réponse de `listNodes`, et ne pouvait plus le nommer quand une recherche retenait une tâche sans lui — US-0220/L1, ouvert en #158 ; le décalage n'avait pas d'unité (`lag_days`), alors que WF-PLA-0030 le garde en jours, semaines ou mois. Corrigé par EP-02/L4 : `row_number` numérote toute la structure, tâches et lignes, quels que soient ce que la lecture rend, ses filtres, sa recherche et son tri ; chaque liaison porte le numéro de son prédécesseur (`predecessor_row_number`) et son décalage dans son unité (`lag`, `lag_unit`). La grille l'écrit tel quel, suffixe de Microsoft Project compris (`5;4DD+1 sem`).
- Le contrat ne dit pas ce que rend `getEstimateIndicators` quand des taux horaires manquent (WF-DEV-0010) — US-0220/L1, ouvert en #159. D'ici là, l'écran du devis montre l'avis des taux manquants et ce que les indicateurs rendent ; quand l'API ne les trouve pas ou les refuse faute de taux horaire (`HOURLY_RATE_MISSING`), l'écran reste debout et les dit indisponibles ; toute autre réponse suit la règle des lectures. Corrigé par EP-02/L8 : chaque montant des indicateurs de devis est un `Computable`, et ceux qu'un taux manquant touche ne se calculent pas, motif `hourly_rate_missing` (`NotComputableReason`), les catégories et les années nommées par `params.missing_rates` ; exemple nommé `estimate_indicators_missing_rates` ; le résumé du devis dit un montant non calculable avec son motif.
- `EstimateIndicators` ne porte que l'écart à la révision précédente et aucun total par poste, là où WF-DEV-0060 demande l'écart à la référence et les totaux par poste — US-0220/L1, ouvert en #160. D'ici là, l'écran affiche l'écart que le contrat rend, sous son nom exact. Corrigé par EP-02/L8 : `EstimateIndicators` porte `delta_to_reference` (nul sans référence) et `by_order_item` (nul quand le planning n'est pas structuré en postes, chaque poste nommé), `delta_to_previous_revision` restant ; le résumé du devis les affiche depuis EP-02/L11 (#220).
- `listNodes` rendait chaque nœud entier — identifiants de lignée, de parent, de catégorie, de rôle et de sous-projet, disponibilité de la saisie du reste, noms de clés répétés sur six mille nœuds — : quatre mégaoctets pour mille tâches et leurs lignes, que le serveur de Next lit puis écrivait entiers dans la page, et l'ouverture d'une grille ne tenait la seconde du §4.6.2 qu'à la marge — US-0110/L2, ouvert en #166. Corrigé par EP-02/L4 : `fields` choisit les propriétés d'un nœud et de ses facettes que la lecture rend ; les pages du devis et du planning le passent, tiré des listes de leurs grilles (`nodeFieldNames`). La projection de la page (`projectNodes`) reste en garde, tirée des mêmes listes : le faux back ignore `fields` et rend son exemple entier, et ce qui passe au navigateur ne dépend pas de ce que la réponse a porté en trop.
- Le contrat ne disait pas ce dont dépend une valeur calculée, que WF-IHM-0030 demande de nommer au refus d'une saisie : `computed_fields` dit quels champs d'un nœud sont calculés, pas d'où ils viennent ; `COMPUTED_VALUE` ne porte aucun paramètre, et `SUMMARY_TASK_DERIVED` ne nommait les subordonnées que par `subordinate_node_ids` — directes ou toutes, le contrat ne le disait pas — US-0150/L1, ouvert en #168. Corrigé par EP-02/L4 (décision de l'utilisateur) : une opération de lecture à la demande, `getComputedValueDependencies`, prend le nœud et le champ tenté, et rend les règles qui calculent la valeur (`ComputedDependency`) et les lignes dont elle est tirée, nommées par leur numéro et leur libellé, que la recherche ou les filtres les retiennent ou non ; `subordinate_node_ids` désigne les subordonnées directes. Le refus d'une saisie l'appelle à son ouverture et dit ce qu'elle rend : la table des règles du noyau que le front recopiait, ses replis et la phrase d'une réponse partielle ont disparu.
- `updateEstimateLine` et `updateTaskFacet` sont des `PATCH` dont les schémas d'écriture exigent des champs que la cellule saisie ne change pas — le libellé, la catégorie et la quantité d'une ligne, le libellé d'une tâche —, quand WF-IHM-0040 veut que chaque cellule se valide seule — US-0120/L1, ouvert en #178. D'ici là, la grille du devis renvoie ces champs tels que le serveur les a rendus en dernier, avec le champ saisi et la version lue (`lock_version`). Corrigé par EP-02/L8 : `TaskFacetUpdate` et `EstimateLineUpdate` n'exigent que `lock_version`, tout autre champ est facultatif et seul ce qui est envoyé change ; la création garde ses champs exigés (`TaskFacetWrite`, `EstimateLineWrite`) ; la grille du devis n'envoie plus que la cellule saisie et la version lue.
- Après une écriture de grille — une cellule (`updateEstimateLine`, `updateTaskFacet`), un collage (`applyPaste`) —, la réponse ne portait que les nœuds écrits : les montants des tâches parentes et les totaux de la grille restaient périmés jusqu'à une relecture de la page (WF-DEV-0050, WF-ARC-0020) — US-0120/L1 et US-0130/L1, ouvert en #188. Corrigé par EP-02/L8 : toute écriture de grille rend `NodesWritten` — les nœuds écrits, leurs ancêtres recalculés, les totaux de la structure et son compteur — ; la grille du devis en applique les nœuds, les ancêtres, les tâches redatées et, lue sans recherche ni filtre, les totaux — lue avec l'une ou l'autre, elle relit les siens par la même requête une fois ses écritures répondues —, et garde le compteur (EP-02/L11, #218).
- `listContributors`, `listProjectStateTransitions` et la réponse de `exitProject` n'avaient aucun exemple : le faux back en aurait tiré de son schéma des valeurs sans rapport avec l'univers des autres — US-0210/L1. Corrigé par ce lot : `contributors.json` (un compte actif, un désactivé), `state_transitions.json` (de la création à En cours) et `project_completed.json` (le projet terminé, ses commandes indisponibles faute d'un état non terminal).
- Le motif d'une sortie du cycle de vie (`ProjectExit.reason`), que la confirmation doit nommer (WF-CYC-0090), s'écrit et ne se relit nulle part : `StateTransition` ne le porte pas, et l'historique des états ne peut pas dire pourquoi une offre a été perdue — US-0210/L1, ouvert en #185. D'ici là, l'écran du cycle de vie demande le motif et l'envoie, et l'historique montre la date, les états et l'auteur de chaque transition. Corrigé par EP-02/L7 : `StateTransition.reason`, exigé, nul pour une transition automatique ou une sortie sans motif ; l'historique l'affichera (#227).
- `setContributors` exige un `lock_version` sans dire de quel objet, et `listContributors` rend un tableau nu, sans compteur : le formulaire d'EP-04 n'aurait rien à renvoyer ; `Contributor.is_active` est facultatif, et son absence ne dit rien — US-0210/L1, ouvert en #186. D'ici là, l'écran des paramètres montre la liste en lecture, et ne dit un compte désactivé que quand l'API le dit. Corrigé par EP-02/L8 : `listContributors` rend `ContributorList`, la liste et son propre compteur, que `ContributorsWrite` exige et que `setContributors` rend avec le suivant, 412 s'il est périmé ; `Contributor.is_active` est exigé ; l'écran des paramètres lit `items`.
- `compareRevisions` et `getRateUpdateProposal` n'avaient aucun exemple, et `listCostStructures` ne montrait que la structure principale : le faux back n'aurait rien eu de cohérent à servir à l'écran des révisions — US-0210/L2. Corrigé par ce lot : `comparison.json` et `comparison_identical.json`, `rate_update.json` et `rate_update_none.json` — dont la catégorie sans taux pour 2026, chiffrée à son taux précédent corrigé de l'inflation du projet —, `structures_amendments.json` (deux avenants qui coexistent, l'un fusionné, et le devis propre d'un risque), et une offre v1.0 marquée ajoutée à `revisions.json`, pour que deux révisions marquées se comparent.
- Un écart de `RevisionComparison.amount_deltas` ne nomme son poste que par sa `key`, et une catégorie de `RateUpdateProposal.categories` que par `cost_category_id`, sans libellé, quand le contrat rend partout ailleurs le libellé à côté de la clé (`AmountByKey.label`) : l'écran ne peut les nommer sans joindre le référentiel dans le front (WF-ARC-0020) — US-0210/L2, ouvert en #204. D'ici là, l'écran des révisions dit « Sans nom », sans jamais montrer l'identifiant. Corrigé par EP-02/L8 : chaque écart porte son `label`, résolu à la lecture, exigé et nul pour la seule clé `unassigned`, et chaque catégorie proposée le sien, exigé ; les exemples `comparison` et `rate_update` les portent, et l'écran des révisions les affiche.
- Le nœud ne dit pas quels champs de sa facette il accepte en écriture — le rôle et la charge d'une ligne de main-d'œuvre, le débours unitaire d'une autre (WF-DEV-0020) —, seulement ceux qu'il calcule — US-0120/L1, ouvert en #194. D'ici là, la grille du devis offre ces cellules sur toute ligne qui ne les déclare pas calculées, sans rien déduire de la nature de sa catégorie, et le serveur refuse ce qu'elle n'accepte pas. Corrigé par EP-02/L8 : le nœud rend `editable_fields` (`EditableField`), symétrique de `computed_fields` — le rôle et la charge d'une ligne de main-d'œuvre, le débours unitaire d'une autre, ni l'un ni l'autre pour une provision —, dans tous les exemples et les volumes ; la grille n'offre une cellule que si son champ y figure (EP-02/L11, #219).
- Les rôles de ressources relèvent de `resource_settings`, qu'un chiffreur peut ne pas avoir, alors que la grille du devis les nomme et les offre au choix — US-0120/L1, ouvert en #195. D'ici là, l'écran du devis se dégrade : sans la liste des rôles ou des catégories, sa colonne n'est ni nommée ni saisie, et le reste de l'écran s'affiche. Corrigé par EP-02/L8 : `listResourceRoles` et `listCostCategories` sont ouvertes, pour les objets actifs, à quiconque consulte un projet ; les objets désactivés (`include_inactive`) et l'écriture restent sous la permission du référentiel, et les deux lectures déclarent le 403 ; la dégradation de l'écran reste pour une API qui refuse.
- Aucune opération ne rendait la grille des taux horaires — catégories de main-d'œuvre en lignes, années en colonnes (§3.4.4.1.2, WF-REF-0050) — : l'écran du référentiel (US-0250) aurait lu les catégories, les natures, puis `listHourlyRates` une catégorie à la fois, cent cinquante appels — EP-02/L2, ouvert en #162. Corrigé par EP-02/L8 : `GET /reference/hourly-rates` (`getHourlyRateGrid`) rend `HourlyRateGrid` en une lecture, les années en colonnes et chaque catégorie nommée en ligne, une cellule par année, nulle sans taux (WF-REF-0060) ; son volume de cent cinquante catégories sur quinze ans est engendré par `make mock-data` (`hourly_rate_grid.json`) ; `listHourlyRates` reste.
- `previewPaste` ne déclarait aucune réponse pour un bloc plus large que la grille, alors que le catalogue porte `PASTE_TOO_WIDE` et son paramètre `max_columns` ; ni l'un ni l'autre n'avait d'exemple — US-0130/L1. Corrigé par ce lot : un 422 `PASTE_TOO_WIDE` (`paste_too_wide.json`), et les exemples des deux temps, `paste_plan.json` (trois lignes acceptées), `paste_plan_unknown_category.json` (une ligne refusée, `UNKNOWN_COST_CATEGORY`) et `paste_applied.json` (les lignes 4 à 6 de la structure des volumes, écrites).
- `PastePreview` ne nomme la colonne visée que par une chaîne libre (`target_column`), sans dire quels champs remplissent les colonnes suivantes : le serveur ne sait ni lesquelles la grille affiche, ni dans quel ordre — une colonne masquée (WF-IHM-0060) décalerait ainsi le bloc sans que rien ne le dise — ; et un refus ne nomme pas sa cellule — US-0130/L1, ouvert en #200. D'ici là, la grille refuse aussitôt un bloc plus large que les colonnes de sa configuration à partir de la cellule active, et un bloc dont la portée, de la colonne visée à la dernière colonne remplie dans cet ordre, enjambe une colonne masquée ; elle envoie la colonne sous son nom de `sort_by`, et signale une ligne refusée par sa place dans le bloc. Corrigé par EP-02/L8 : `target_column` est une colonne de `NodeColumn`, l'énumération nommée que le tri de `listNodes` emploie aussi, dans l'ordre des grilles ; le contrat dit que le bloc remplit, à partir de la colonne visée, les colonnes de la facette du nœud visé dans cet ordre, sans décaler aucune cellule — une cellule non vide sur une colonne que la ligne n'accepte pas est refusée, nommée par sa ligne et sa colonne (`PastePlan.rejected[].column`), une cellule vide n'écrit rien —, et `max_columns` compte les colonnes de la facette à partir de la colonne visée ; la garde locale du front sur une colonne masquée reste.
- `PasteApply.lock_version` ne dit pas de quel objet il est, `applyPaste` ne déclare pas de 412, et sa réponse ne rend pas la version suivante — US-0130/L1, ouvert en #201. D'ici là, la confirmation porte la version de la structure principale lue avec la page ; un refus se dit par `OutcomeNotice`. Corrigé par EP-02/L8 : `PasteApply.lock_version` est le compteur de la structure, qui avance à chaque écriture dans son arbre ; `applyPaste` déclare 412 et rend, dans `NodesWritten`, le compteur suivant (`structure_lock_version`), que la grille du devis garde pour le collage suivant.
- Une liaison écrite, ou la durée saisie d'une tâche en mode automatique, redate ses successeurs (WF-PLA-0020), qui ne sont ni les nœuds écrits ni leurs ancêtres : `NodesWritten` ne les rendait pas, et la grille de planning aurait montré les dates d'avant pour toute la chaîne qui suit, jusqu'à une relecture — EP-02/L8, ouvert en #222. Corrigé par EP-02/L10 (décision de l'utilisateur du 2026-10-04) : toute écriture de grille rend `rescheduled`, exigé, les tâches non récapitulatives dont le début, la fin, la marge totale ou la criticité ont changé sans être écrites — successeurs, et ce que le chemin critique déplace (WF-PLA-0100) —, chacune une fois, dans l'ordre du plan, vide quand rien d'autre n'a bougé ; chacune en projection légère (`NodeSchedule` : début, fin, marge, nulle en mode manuel, criticité, fin dépassée), sans les montants qui dépendent des dates, que la grille de devis relit à son ouverture ; `ancestors` porte les ancêtres des nœuds écrits et des tâches redatées, recalculés, chacun une fois, entier ; la marge totale est une durée sur la facette comme dans la projection (`TaskFacet.total_float`, à la place de `total_float_days`), que la grille de planning écrit par sa valeur et son unité ; l'exemple `predecessor_set` de `setPredecessors` en porte deux, les autres exemples une liste vide.
- Le contrat ne nomme pas le montant à l'année de référence que la grille de devis présente à côté du montant corrigé de l'inflation (WF-DEV-0050), et ne porte `inflated_amount` ni sur la facette d'une tâche — récapitulatives comprises — ni dans `NodeTotals` — EP-02/L11, ouvert en #235. D'ici là, la grille lit `reestimated_amount` pour le montant à l'année de référence, d'une ligne comme d'une tâche, avec son total ; la cellule corrigée de l'inflation d'une tâche, et le total corrigé, restent vides. Les tests de la grille ne tiennent donc du Vérif de WF-DEV-0050 que l'absence des montants budgété et réestimé nommés ; le montant corrigé supérieur de 4,04 % reste au serveur, aucun exemple ne le chiffrant. Corrigé par EP-02/L16 (décision de l'utilisateur du 2026-10-05) : `base_amount`, le montant à l'année de référence (WF-DEV-0030), sur la ligne, la tâche et `NodeTotals`, et `inflated_amount` sur la tâche et dans `NodeTotals`, chacun une somme que le serveur calcule ; les montants budgété et réestimé sont dits à l'année de référence, seul `inflated_amount` portant l'inflation ; après une écriture qui déplace des lignes dans le temps, leurs montants et ceux des tâches non récapitulatives qu'elles changent en projection légère (`NodesWritten.reinflated`, `NodeInflation` : le nœud, son montant corrigé, l'année de consommation d'une ligne), les récapitulatives restant dans `ancestors`, montrée par l'exemple `task_lengthened` du volume (une durée allongée qui pousse une tâche en 2027) ; `NodeColumn.base_amount` et les champs calculés suivent. La grille de devis présente `base_amount` et `inflated_amount` sur les lignes, les tâches et les totaux, et applique la projection aux lignes comme aux tâches ; ses tests nomment l'absence des montants budgété et réestimé, et lisent le montant corrigé d'une ligne du volume consommée deux ans après l'année de référence, à l'inflation de 3 % du projet témoin. Le montant corrigé d'une tâche redatée sans être écrite, d'abord laissé ouvert, est rendu dans `reinflated` (décision de l'utilisateur du même jour) ; l'exemple `paste_too_wide` dit la largeur de la ligne, quatorze colonnes.
- La grille de devis nommait la catégorie et le rôle d'une ligne en rapprochant les listes du référentiel (`namer`), quand un objet rattaché se nomme par le libellé que le serveur rend (WF-ARC-0020), et disait inconnu un objet désactivé mais employé (WF-REF-0150) — relecture d'US-0250/L1, ouvert en #305. Corrigé par EP-02/L16 (décision de l'utilisateur du 2026-10-05) : `cost_category_label`, `resource_role_label` et `subproject_label` sur la facette de la ligne, exigés, résolus par le serveur pour un objet actif ou désactivé, nuls sans objet ; la grille de devis demande par `fields` les deux qu'elle présente et les affiche, et `namer` a disparu ; les listes du référentiel ne servent plus qu'au choix d'une saisie.
- Les lectures des risques ne nommaient pas de révision, quand l'écran est sous `…/revisions/[r]/risks` et que chaque révision fige le devis propre d'un risque, donc sa gravité, sa provision et sa case (WF-RIS-0030) ; la matrice ne disait pas les bornes de ses niveaux, que l'écran ne pouvait tirer que du référentiel ; aucun total général des provisions n'était rendu, que WF-RIS-0040 veut égal à la somme des trois ; aucune des quatre lectures n'avait d'exemple — US-0230/L2. Corrigé par ce lot, sur l'autorisation de l'utilisateur du 2026-10-04 (ajouts de lecture d'un lot d'écran) : `revision_id` (`RiskRevision`) sur `listRisks`, `getRisk`, `listRiskReviews` et `getProjectRiskMatrix` ; `RiskMatrix.probability_levels` et `severity_levels` (`RiskMatrixLevel`, la gravité en pourcentage du budget de référence) ; `ProvisionTotals.total` ; les exemples `risks`, `risks_empty`, `risk`, `risk_occurred_detail`, `risk_reviews` et `risk_matrix`.
- Le refus d'une saisie sur la gravité ou la provision d'un risque ne peut pas nommer ce dont elles dépendent (WF-IHM-0030) : `getComputedValueDependencies` ne connaît que les champs d'un nœud (`ComputedValueField`), et un risque n'en est pas un — US-0230/L2, ouvert en #250. Corrigé par EP-02/L17, sur la décision de l'utilisateur du 2026-10-05 : le risque porte ses dépendances, `Risk.computed_fields`, la gravité et la provision chacune avec ses règles — `own_estimate` et `severity_and_probability`, ajoutés à `ComputedDependency` —, constantes, sans appel au refus ; la grille des risques les nomme dans le refus d'une saisie, comme les grilles du devis.
- `getMilestoneTracking`, `getCostCurve` et `getEarnedValueCurves` n'avaient aucun exemple : le faux back aurait tiré de leurs schémas des valeurs sans rapport avec l'univers témoin, et le test du diagramme temps/temps lisait un objet écrit à la main — US-0240/L1, ouvert en #246. Corrigé par US-0240/L2 (autorisation de l'utilisateur du 2026-10-04) : `milestone_tracking.json`, `milestone_tracking_none.json`, `cost_curve.json`, `cost_curve_payment_delays.json`, `cost_curve_amendment.json` et `earned_value_curves.json`, au 16 mars 2026 sur la révision courante du projet témoin, aux montants de `project_indicators` et de `remaining_indicators` (#287) ; la marche de `cost_curve_amendment` porte deux points à sa date, avant et après, pour être verticale (revue de la PR #289). Les exemples de `getProjectWorkload` et des révisions marquées sont venus avec l'écran du plan de charge (US-0240/L4, #286) : `workload`, `workload_reference_budget` et `workload_marked_remaining`, un par base, au 16 mars 2026 sur le devis de `nodes_estimate` (#287) ; `revisions_marked`.
- `ActualCostLine` ne nommait son sous-projet que par `subproject_id` : l'écran des coûts réels ne pouvait présenter l'imputation d'une ligne (WF-CRE-0020) qu'en rapprochant `listSubprojects` dans le front ; `listActualCosts` et `listCostImports` n'avaient aucun exemple — US-0230/L3. Corrigé par ce lot, sur l'autorisation de l'utilisateur du 2026-10-04 (ajouts de lecture d'un lot d'écran) : `subproject_code` et `subproject_label`, exigés, nuls hors sous-projet ; `last_import_at` exigé, nul tant que rien n'a été importé, que son absence ne se confonde plus avec « aucun import » ; les exemples `actual_costs`, `actual_costs_page`, `actual_costs_subproject`, `actual_costs_empty`, `cost_imports`, `cost_imports_periods`, `cost_imports_beyond` et `cost_imports_empty`, dans l'univers des indicateurs.
- `getPortfolioValue`, `getPortfolioWorkload`, `getPortfolioPerformance`, `getPortfolioCostStructure`, `getPortfolioRisks` et `getPortfolioCashOut` n'avaient aucun exemple, et `getPortfolioProjects` aucune liste vide : le faux back aurait tiré de leurs schémas des vues sans rapport avec les trois cents projets de la liste — US-0240/L3. Corrigé par ce lot, sur l'autorisation de l'utilisateur du 2026-10-04 : la valeur, la performance, la structure des coûts et les risques engendrés avec la liste par `make mock-data`, sommés de ses lignes au 16 mars 2026 ; `portfolio_workload` et `portfolio_cash_out` écrits au même instant ; `portfolio_projects_empty`.
- `PortfolioWorkload.under_load_threshold` était facultatif : une réponse conforme pouvait omettre le seuil de sous-charge retenu, que l'écran montre quand l'adresse n'en nomme aucun — US-0240/L5 (relevé par Copilot sur la PR #338). Corrigé par ce lot, sur l'autorisation de l'utilisateur du 2026-10-04 (ajouts de lecture) : le seuil est exigé, celui que la requête a demandé ou celui que le serveur a choisi.
- `PortfolioWorkload` ne dit pas que chaque rôle porte les mêmes mois : l'écran du plan de charge agrégé prend les mois du premier rôle pour en-têtes de colonnes — US-0240/L5, ouvert en #326.
- `listActualCosts` ne trie que quatre des sept colonnes de la grille des coûts réels (`sort_by` : `document_date`, `document_number`, `amount`, `subproject`) : le périmètre suivi, le motif d'exclusion et les colonnes conservées du fichier ne se trient pas — US-0230/L3, ouvert en #292. D'ici là, ces colonnes n'offrent aucun tri. Corrigé par EP-02/L15 (décision de l'utilisateur du 2026-10-05 pour les colonnes conservées) : `sort_by` trie aussi par `in_tracked_scope`, `excluded_reason` et `passthrough.<colonne>`, comparés en texte ; la grille présente chaque colonne conservée comme une colonne, sous le nom que le fichier lui donne, et les trie toutes.
- `getReferenceSettings`, `listCostTypes`, `listOrgNodes`, `listCalendars` et `setHourlyRate` n'avaient aucun exemple, et `getHourlyRateGrid` ne se cherchait pas, quand la grille dense offre sa recherche et que WF-IHM-0130 veut toute table filtrable — US-0250/L1. Corrigé par US-0250/L1, sur l'autorisation de l'utilisateur du 2026-10-04 : `search` sur `getHourlyRateGrid`, les années restant celles de toute la grille ; les exemples `reference_settings`, `cost_types`, `org_nodes`, `calendars`, `hourly_rate_entered` et `hourly_rate_corrected`, dans l'univers des autres.
- `setHourlyRate` exige la version lue pour corriger un taux (`HourlyRateWrite.lock_version`) sans déclarer le 412 qui refuse une version périmée — US-0250/L1, ouvert en #296. D'ici là, la grille des taux envoie la version lue et dit tout refus par `OutcomeNotice`, un 412 comme ailleurs ; ses tests éprouvent les refus déclarés, 409 et 422. Corrigé par EP-02/L15 : le 412 est déclaré (`STALE_LOCK_VERSION`, `params.expected_lock_version`), exemple `hourly_rate_stale`, que les tests de la grille des taux éprouvent.
- `OrgNode` ne porte ni le code unique que WF-REF-0070 donne à chaque nœud, ni sa profondeur, et `listOrgNodes` ne dit pas dans quel ordre il rend l'arbre — US-0250/L1, ouvert en #297. D'ici là, l'écran des ressources présente les nœuds dans l'ordre de la réponse, chacun avec le libellé de son parent.
- `RiskMatrixSettings.zones` ne dit pas dans quel ordre ses seize zones se rangent — US-0250/L1, ouvert en #298. D'ici là, l'écran des paramètres de risques présente les bornes de la matrice, pas ses zones, que l'écran des risques d'une révision montre case par case. Corrigé par EP-02/L15 : les zones se rangent par probabilité puis par gravité, chaque axe du plus bas au plus haut ; l'écran des paramètres de risques présente la zone de chaque case.
- Un rôle de ressource ne nommait son nœud, sa catégorie et son calendrier, une catégorie sa nature, un nœud son parent que par leur identifiant : l'écran les rapprochait des listes qu'il lit (WF-ARC-0020), et aurait dit inconnu un objet désactivé mais employé, que ces listes ne rendent pas sans `include_inactive` (WF-REF-0150) — revue d'US-0250/L1. Corrigé par US-0250/L1 : `ResourceRole.org_node_label`, `cost_category_label`, `calendar_label`, `CostCategory.cost_type_label` et `OrgNode.parent_label`, résolus à la lecture, exigés, nul pour le parent d'une racine seul ; les exemples et le volume des catégories les portent.
- Le filtre `org_node_id` de `getProjectWorkload` ne dit pas s'il retient aussi les rôles des nœuds descendants du nœud choisi, que WF-DEV-0070 laisse entendre (« les rôles qui en relèvent ») — US-0240/L4, ouvert en #297. D'ici là, le filtre du plan de charge liste les nœuds dans l'ordre de la réponse, chacun avec le libellé de son parent (`parent_label`), comme l'écran des ressources ; l'arbre lui-même — profondeur, ordre — est #297. Proposition : la portée du filtre dite dans sa description.
- Le 422 de `getProjectWorkload` (`VALIDATION_FAILED`) refuse aussi bien une révision marquée manquante ou non marquée qu'un nœud d'organisation inconnu, et `FieldProblem.pointer` ne dit pas comment il désigne un paramètre de requête — US-0240/L4, ouvert en #307. D'ici là, l'écran lit le dernier segment du pointeur (`revision_id`, `org_node_id`) et dit la raison du seul paramètre désigné, une raison générique sinon. Proposition : la description de `FieldProblem.pointer` fixe la forme qui désigne un paramètre de requête (`/revision_id`). Corrigé par EP-02/L15 : un paramètre de requête se désigne par `/query/<nom>` (exemple `workload_revision_refused`), que l'écran compare entier.
- `listUsers`, `listPermissions`, `listAccessRoles`, `getSystemStatus`, `listBackups` et `getBackupSchedule` n'avaient aucun exemple, et un compte ne nommait ses rôles et son nœud que par leur identifiant : l'écran des comptes les aurait rapprochés de `listAccessRoles` et de `listOrgNodes` dans le front (WF-ARC-0020) — US-0250/L2. Corrigé par ce lot, sur l'autorisation de l'utilisateur du 2026-10-04 (ajouts de lecture d'un lot d'écran) : `User.access_role_labels` et `User.org_node_label`, résolus à la lecture, exigés, que la session porte aussi ; les exemples `users`, `users_page`, `permissions`, `access_roles`, `system_status`, `system_status_backup_failed`, `backups`, `backups_empty`, `backups_beyond`, `backup_schedule`, `backup_schedule_weekly` et `backup_schedule_disabled`, dans l'univers des autres ; les sessions d'un chiffreur et sans administration portent chacune leur rôle propre, `Chiffreur` et `Pilotage de projet`, plutôt que celui qui accorde tout le catalogue (revue d'US-0250/L2).
- `BackupSchedule.weekday` va de 1 à 7 sans dire quel jour est le premier — US-0250/L2, ouvert en #314. D'ici là, l'écran des sauvegardes le lit comme ISO 8601 : 1 est le lundi. Corrigé par EP-02/L15 : ISO 8601, 1 le lundi, dit par le contrat.
- `BackupSchedule.at_time` ne dit pas dans quel fuseau s'entend l'heure d'une sauvegarde planifiée, quand l'écran montre les horodatages dans l'heure locale du poste — US-0250/L2, ouvert en #316. D'ici là, l'écran des sauvegardes rend l'heure telle quelle, « heure de la plateforme », sans la convertir. Corrigé par EP-02/L15 : l'heure est en temps universel, comme les exemples la prenaient, et se décale d'une heure en heure locale aux changements d'heure, ce qui est assumé ; l'écran la dit en UTC, sans la convertir. Le sens du 403 de `listBackups`, relevé avec elle, est suivi en #348.
- Le filtre `org_node_id` de `getProjectWorkload` ne dit pas s'il retient aussi les rôles des nœuds descendants du nœud choisi, que WF-DEV-0070 laisse entendre (« les rôles qui en relèvent ») — US-0240/L4. D'ici là, le filtre du plan de charge liste les nœuds dans l'ordre de la réponse, chacun avec le libellé de son parent (`parent_label`), comme l'écran des ressources ; l'arbre lui-même — profondeur, ordre — est #297. Proposition : la portée du filtre dite dans sa description.
- Le 422 de `getProjectWorkload` (`VALIDATION_FAILED`) refuse aussi bien une révision marquée manquante ou non marquée qu'un nœud d'organisation inconnu, et `FieldProblem.pointer` ne dit pas comment il désigne un paramètre de requête — US-0240/L4, revue. D'ici là, l'écran lit le dernier segment du pointeur (`revision_id`, `org_node_id`) et dit la raison du seul paramètre désigné, une raison générique sinon. Proposition : la description de `FieldProblem.pointer` fixe la forme qui désigne un paramètre de requête (`/revision_id`). Corrigé par EP-02/L15 : un paramètre de requête se désigne par `/query/<nom>` (exemple `workload_revision_refused`), que l'écran compare entier.
- `uploadFile`, `openImport`, `getImport`, `listImports` et `requestExport` n'avaient aucun exemple, et un import ne nommait pas son fichier, que l'écran ne pouvait rappeler ni au compte rendu ni dans la liste des imports une fois le fichier supprimé (WF-DAT-0120) — US-0260/L1. Corrigé par ce lot, sur l'autorisation de l'utilisateur du 2026-10-04 : `Import.filename`, exigé ; les exemples `file_upload`, `import_analysing`, `import_analysed`, `import_planning_mismatch`, `imports`, `imports_page`, `imports_empty`, `task_export_queued` et `task_export_succeeded`, dans l'univers des autres.
- Le contrat ne nomme une commande d'import que pour les coûts réels (`import_actual_costs`, sur le projet) : rien ne dit quand un import de planning, de devis ou de reste à engager est disponible, ni s'il l'est sans révision en cours, que l'import crée au besoin (WF-INTF-0090) ; aucune commande ne dit non plus qu'un export est disponible — US-0260/L1, ouvert en #318. Corrigé par EP-02/L17, sur la décision de l'utilisateur du 2026-10-05 : les imports sur le projet, `import_planning`, `import_estimate`, `import_remaining` à côté de `import_actual_costs`, disponibles sans révision en cours, la condition `may_create_revision` nommée à qui n'a pas la permission de créer la révision que l'import créerait ; les exports sur la révision, `export_planning`, `export_estimate`, `export_remaining`, `export_task_tree_image`. L'écran des imports et exports offre chaque import et chaque export selon sa commande, et ne déduit plus rien de la saisie ni de la lecture. Reste #332 : l'écran est une feuille de la planification, de portée révision, et un projet sans révision n'a toujours aucune adresse qui offre un import.
- `ImportDifference.fields` nomme les champs d'un écart par des chaînes libres, qu'aucun catalogue ne rend (WF-ARC-0110) — US-0260/L1, ouvert en #319. D'ici là, le compte rendu présente chaque écart par son changement, son objet et son libellé, sans ses champs.
- `listImports` ne dit pas dans quel ordre il rend les imports — US-0260/L1, ouvert en #320. D'ici là, l'écran les présente dans l'ordre de la réponse. Corrigé par EP-02/L15 : du plus récent au plus ancien, par leur ouverture.
- Le refus d'un fichier au format ou à la version non reconnus (`openImport`, 422) dit nommer le format attendu (WF-INTF-0070), mais `FILE_FORMAT_UNREADABLE` ne déclare aucun paramètre qui le porte — US-0260/L1, ouvert en #321. D'ici là, le refus se dit par la phrase de son code. Corrigé par EP-02/L15 : `params.expected_format` (un `ExchangeKind`) et `params.expected_version`, exemple `import_format_unreadable`, que la phrase du refus nomme.
- `getBackgroundTaskResult` ne déclare ni le nom du fichier rendu (`Content-Disposition`) ni sa nature au-delà de `application/octet-stream` — revue d'US-0260/L1, ouvert en #323. D'ici là, le front transmet le `Content-Disposition` de l'API quand il vient, et pose sinon `attachment`, avec `X-Content-Type-Options: nosniff`. Corrigé par EP-02/L15 : `Content-Disposition` exigé, nommant le fichier, et le type de média de chaque nature d'export ; le front le transmet, et répond 502 à une réponse qui ne le porte pas.
- Le contrat ne borne pas la taille d'un fichier déposé (`uploadFile`, 413 sans maximum) — revue d'US-0260/L1, ouvert en #324. D'ici là, l'écran refuse dans la page un fichier de plus de 10 Mio, la plus grande taille d'import du §4.6.2 (un fichier MS Project), et la borne des actions serveur de Next (`next.config.ts`) est réglée un peu au-dessus, l'enveloppe multipart comprise. Corrigé par EP-02/L15 (décision de l'utilisateur du 2026-10-05, une borne par usage) : le dépôt dit son usage (`purpose`) ; un import est borné à 10 Mio, une sauvegarde à restaurer par `Installation.external_backup_max_bytes` ; le front dépose pour un import, sa borne réglée sur celle des imports.
- `NodeSchedule` ne porte pas `lock_version`, sans que le contrat dise si redater une tâche fait avancer son compteur : la saisie suivante d'une tâche redatée partirait sinon d'une version périmée — revue d'EP-02/L11, ouvert en #236. Corrigé par EP-02/L15 (décision de l'utilisateur du 2026-10-05) : un recalcul ne fait avancer le compteur d'aucun nœud, qui suit les écritures de l'utilisateur (`LockVersion`, `NodeSchedule`, `NodesWritten.rescheduled`) ; la grille garde la version lue d'une tâche redatée et n'en prend que le calendrier (`rescheduled()`, `components/grid/nodes.tsx`).
- Cinq constats ouverts en issue sans entrée ici : `listActualCosts` ne déclarait aucun refus de requête (#293) ; le 409 de `getProjectIndicators` ne disait pas son code (#248), pas plus que celui de `getProjectWorkload` ; deux structures propres des risques témoins n'avaient pas d'exemple (#252) ; la ligne de provision d'un risque identifié portait un montant budgété sans que le contrat dise ce que le budget de référence en compte (#245) ; `CurveSeries.steps[].amount` ne disait pas s'il porte la marche ou le budget après elle (#285). Corrigé par EP-02/L15 : un 422 `VALIDATION_FAILED` par champ pour une période inversée ou un sous-projet inconnu, que l'écran des coûts réels dit à la place des lignes ; `STATE_FORBIDS_OPERATION` pour les deux 409, `params.state` l'état du projet, exemples `project_indicators_not_in_progress` et `workload_no_reference` ; `structures_amendments` porte les trois, leur chronologie suivie dans #287 ; le montant budgété est celui que la révision de référence a fixé, le budget de référence cette somme diminuée des provisions selon WF-RIS-0050 (glossaire), le cas d'un risque écarté ou identifié après la référence étant l'issue de spécification #347 ; le montant de la marche, signé, que l'écran nomme ainsi.
- `PortfolioWorkload` ne dit pas que chaque rôle porte les mêmes mois : l'écran du plan de charge agrégé prend les mois du premier rôle pour en-têtes de colonnes — US-0240/L5, ouvert en #326. Corrigé par EP-02/L18 (décision de l'utilisateur du 2026-10-05) : `PortfolioWorkload.months`, exigé, porte les mois de l'horizon, et chaque rôle un mois par mois de cette liste, dans le même ordre ; l'écran en tire ses colonnes.
- `listActualCosts` ne trie que quatre des sept colonnes de la grille des coûts réels (`sort_by` : `document_date`, `document_number`, `amount`, `subproject`) : le périmètre suivi, le motif d'exclusion et les colonnes conservées du fichier ne se trient pas — US-0230/L3, ouvert en #292. D'ici là, ces colonnes n'offrent aucun tri.
- `getReferenceSettings`, `listCostTypes`, `listOrgNodes`, `listCalendars` et `setHourlyRate` n'avaient aucun exemple, et `getHourlyRateGrid` ne se cherchait pas, quand la grille dense offre sa recherche et que WF-IHM-0130 veut toute table filtrable — US-0250/L1. Corrigé par US-0250/L1, sur l'autorisation de l'utilisateur du 2026-10-04 : `search` sur `getHourlyRateGrid`, les années restant celles de toute la grille ; les exemples `reference_settings`, `cost_types`, `org_nodes`, `calendars`, `hourly_rate_entered` et `hourly_rate_corrected`, dans l'univers des autres.
- `setHourlyRate` exige la version lue pour corriger un taux (`HourlyRateWrite.lock_version`) sans déclarer le 412 qui refuse une version périmée — US-0250/L1, ouvert en #296. D'ici là, la grille des taux envoie la version lue et dit tout refus par `OutcomeNotice`, un 412 comme ailleurs ; ses tests éprouvent les refus déclarés, 409 et 422.
- `OrgNode` ne porte ni le code unique que WF-REF-0070 donne à chaque nœud, ni sa profondeur, et `listOrgNodes` ne dit pas dans quel ordre il rend l'arbre — US-0250/L1, ouvert en #297. D'ici là, l'écran des ressources présente les nœuds dans l'ordre de la réponse, chacun avec le libellé de son parent. Corrigé par EP-02/L18 (décision de l'utilisateur du 2026-10-05) : `OrgNode.code`, unique, refusé en double par 409, `ALREADY_EXISTS`, et `OrgNode.level` ; `listOrgNodes` rend l'arbre en ordre de profondeur, les frères par libellé, et une recherche rend aussi les ancêtres. L'écran des ressources présente l'arbre — code, libellé décalé de sa profondeur, niveau —, et les filtres par nœud l'offrent dans le même ordre, chaque nœud décalé de sa profondeur.
- `RiskMatrixSettings.zones` ne dit pas dans quel ordre ses seize zones se rangent — US-0250/L1, ouvert en #298. D'ici là, l'écran des paramètres de risques présente les bornes de la matrice, pas ses zones, que l'écran des risques d'une révision montre case par case.
- Un rôle de ressource ne nommait son nœud, sa catégorie et son calendrier, une catégorie sa nature, un nœud son parent que par leur identifiant : l'écran les rapprochait des listes qu'il lit (WF-ARC-0020), et aurait dit inconnu un objet désactivé mais employé, que ces listes ne rendent pas sans `include_inactive` (WF-REF-0150) — revue d'US-0250/L1. Corrigé par US-0250/L1 : `ResourceRole.org_node_label`, `cost_category_label`, `calendar_label`, `CostCategory.cost_type_label` et `OrgNode.parent_label`, résolus à la lecture, exigés, nul pour le parent d'une racine seul ; les exemples et le volume des catégories les portent.
- Le filtre `org_node_id` de `getProjectWorkload` ne dit pas s'il retient aussi les rôles des nœuds descendants du nœud choisi, que WF-DEV-0070 laisse entendre (« les rôles qui en relèvent ») — US-0240/L4, ouvert en #297. D'ici là, le filtre du plan de charge liste les nœuds dans l'ordre de la réponse, chacun avec le libellé de son parent (`parent_label`), comme l'écran des ressources ; l'arbre lui-même — profondeur, ordre — est #297. Proposition : la portée du filtre dite dans sa description. Corrigé par EP-02/L18 (décision de l'utilisateur du 2026-10-05) : relever d'un nœud, c'est relever de lui ou de l'un de ses descendants, pour les quatre filtres `org_node_id` — `getProjectWorkload`, `listResourceRoles`, `listUsers` et le portefeuille —, et le filtre se dit « Nœud d'organisation et ses descendants ».
- Le 422 de `getProjectWorkload` (`VALIDATION_FAILED`) refuse aussi bien une révision marquée manquante ou non marquée qu'un nœud d'organisation inconnu, et `FieldProblem.pointer` ne dit pas comment il désigne un paramètre de requête — US-0240/L4, ouvert en #307. D'ici là, l'écran lit le dernier segment du pointeur (`revision_id`, `org_node_id`) et dit la raison du seul paramètre désigné, une raison générique sinon. Proposition : la description de `FieldProblem.pointer` fixe la forme qui désigne un paramètre de requête (`/revision_id`).
- `listUsers`, `listPermissions`, `listAccessRoles`, `getSystemStatus`, `listBackups` et `getBackupSchedule` n'avaient aucun exemple, et un compte ne nommait ses rôles et son nœud que par leur identifiant : l'écran des comptes les aurait rapprochés de `listAccessRoles` et de `listOrgNodes` dans le front (WF-ARC-0020) — US-0250/L2. Corrigé par ce lot, sur l'autorisation de l'utilisateur du 2026-10-04 (ajouts de lecture d'un lot d'écran) : `User.access_role_labels` et `User.org_node_label`, résolus à la lecture, exigés, que la session porte aussi ; les exemples `users`, `users_page`, `permissions`, `access_roles`, `system_status`, `system_status_backup_failed`, `backups`, `backups_empty`, `backups_beyond`, `backup_schedule`, `backup_schedule_weekly` et `backup_schedule_disabled`, dans l'univers des autres ; les sessions d'un chiffreur et sans administration portent chacune leur rôle propre, `Chiffreur` et `Pilotage de projet`, plutôt que celui qui accorde tout le catalogue (revue d'US-0250/L2).
- `BackupSchedule.weekday` va de 1 à 7 sans dire quel jour est le premier — US-0250/L2, ouvert en #314. D'ici là, l'écran des sauvegardes le lit comme ISO 8601 : 1 est le lundi.
- `BackupSchedule.at_time` ne dit pas dans quel fuseau s'entend l'heure d'une sauvegarde planifiée, quand l'écran montre les horodatages dans l'heure locale du poste — US-0250/L2, ouvert en #316. D'ici là, l'écran des sauvegardes rend l'heure telle quelle, « heure de la plateforme », sans la convertir.
- Le filtre `org_node_id` de `getProjectWorkload` ne dit pas s'il retient aussi les rôles des nœuds descendants du nœud choisi, que WF-DEV-0070 laisse entendre (« les rôles qui en relèvent ») — US-0240/L4. D'ici là, le filtre du plan de charge liste les nœuds dans l'ordre de la réponse, chacun avec le libellé de son parent (`parent_label`), comme l'écran des ressources ; l'arbre lui-même — profondeur, ordre — est #297. Proposition : la portée du filtre dite dans sa description. Corrigé par EP-02/L18 (décision de l'utilisateur du 2026-10-05) : relever d'un nœud, c'est relever de lui ou de l'un de ses descendants, pour les quatre filtres `org_node_id` — `getProjectWorkload`, `listResourceRoles`, `listUsers` et le portefeuille —, et le filtre se dit « Nœud d'organisation et ses descendants ».
- Le 422 de `getProjectWorkload` (`VALIDATION_FAILED`) refuse aussi bien une révision marquée manquante ou non marquée qu'un nœud d'organisation inconnu, et `FieldProblem.pointer` ne dit pas comment il désigne un paramètre de requête — US-0240/L4, revue. D'ici là, l'écran lit le dernier segment du pointeur (`revision_id`, `org_node_id`) et dit la raison du seul paramètre désigné, une raison générique sinon. Proposition : la description de `FieldProblem.pointer` fixe la forme qui désigne un paramètre de requête (`/revision_id`).
- `uploadFile`, `openImport`, `getImport`, `listImports` et `requestExport` n'avaient aucun exemple, et un import ne nommait pas son fichier, que l'écran ne pouvait rappeler ni au compte rendu ni dans la liste des imports une fois le fichier supprimé (WF-DAT-0120) — US-0260/L1. Corrigé par ce lot, sur l'autorisation de l'utilisateur du 2026-10-04 : `Import.filename`, exigé ; les exemples `file_upload`, `import_analysing`, `import_analysed`, `import_planning_mismatch`, `imports`, `imports_page`, `imports_empty`, `task_export_queued` et `task_export_succeeded`, dans l'univers des autres.
- Le contrat ne nomme une commande d'import que pour les coûts réels (`import_actual_costs`, sur le projet) : rien ne dit quand un import de planning, de devis ou de reste à engager est disponible, ni s'il l'est sans révision en cours, que l'import crée au besoin (WF-INTF-0090) ; aucune commande ne dit non plus qu'un export est disponible — US-0260/L1, ouvert en #318. D'ici là, l'écran des imports et exports offre l'import d'un planning, d'un devis, d'un reste à engager comme la révision en cours offre `edit_planning`, `edit_estimate`, `edit_remaining`, et aucun sans révision en cours ; il offre l'export à qui lit l'écran, un refus dit par `OutcomeNotice`.
- `ImportDifference.fields` nomme les champs d'un écart par des chaînes libres, qu'aucun catalogue ne rend (WF-ARC-0110) — US-0260/L1, ouvert en #319. D'ici là, le compte rendu présente chaque écart par son changement, son objet et son libellé, sans ses champs. Corrigé par EP-02/L18 (décision de l'utilisateur du 2026-10-05) : `fields` nomme ses champs par `NodeColumn` pour une tâche, une ligne de devis ou une liaison, et par `ActualCostColumn`, nommée comme le tri de `listActualCosts`, pour une ligne de coût réel ; le compte rendu les nomme par le catalogue.
- `PilotHealth.signals[].params` et `Alert.params` étaient des objets libres : l'écran de santé du pilotage ne pouvait dire ni les semaines sans revue ni le jalon dépassé, l'écran d'état ni le composant indisponible — US-0240/L3 et US-0250/L2, ouvert en #311. Corrigé par EP-02/L18 (décision de l'utilisateur du 2026-10-05) : des propriétés facultatives typées, comme `Computable.params`, dont la description dit lesquelles chaque code porte, le jalon nommé par son libellé (`milestone_label`) ; les deux écrans les disent.
- `getProjectIndicators`, `getCostCurve` et `getEarnedValueCurves` ne se lisaient pas pour une révision : sur l'adresse d'une révision marquée, l'écran des indicateurs montrait ceux de la révision en cours, et le disait par un avis — US-0240/L1, ouvert en #247. Corrigé par EP-02/L18 (décision de l'utilisateur du 2026-10-05) : `revision_id`, comme les indicateurs de devis, refusé avec `as_of` par 422, et par 409 sur une révision marquée avant l'état En cours ; exemples `project_indicators_marked`, `project_indicators_offer`. Point ouvert dans `docs/api/DECISIONS.md` : des courbes recalculées à la date du marquage peuvent s'écarter des indicateurs conservés. L'écran lit la révision de son adresse, ou la date qu'elle demande, et son avis nomme ce qui est calculé ailleurs — l'évolution des indices, toujours sur la révision en cours.
- `PortfolioScope` ne nommait pas le nœud retenu, son défaut d'états (« les projets en cours ») contredisait les résumés des exemples qui retiennent aussi les projets en chiffrage, et `CashOutMonth` disait qu'un mois porte le passé ou l'avenir, quand le mois de la date de calcul porte les deux — revue d'US-0240/L3, ouvert en #327. Corrigé par EP-02/L18 : `org_node_label`, que l'en-tête d'une vue du portefeuille dit ; les résumés disent que la requête ajoute les projets en chiffrage au périmètre par défaut ; la description de `CashOutMonth` dit le mois de la date de calcul.
- `listImports` ne dit pas dans quel ordre il rend les imports — US-0260/L1, ouvert en #320. D'ici là, l'écran les présente dans l'ordre de la réponse.
- Le refus d'un fichier au format ou à la version non reconnus (`openImport`, 422) dit nommer le format attendu (WF-INTF-0070), mais `FILE_FORMAT_UNREADABLE` ne déclare aucun paramètre qui le porte — US-0260/L1, ouvert en #321. D'ici là, le refus se dit par la phrase de son code.
- `getBackgroundTaskResult` ne déclare ni le nom du fichier rendu (`Content-Disposition`) ni sa nature au-delà de `application/octet-stream` — revue d'US-0260/L1, ouvert en #323. D'ici là, le front transmet le `Content-Disposition` de l'API quand il vient, et pose sinon `attachment`, avec `X-Content-Type-Options: nosniff`.
- Le contrat ne borne pas la taille d'un fichier déposé (`uploadFile`, 413 sans maximum) — revue d'US-0260/L1, ouvert en #324. D'ici là, l'écran refuse dans la page un fichier de plus de 10 Mio, la plus grande taille d'import du §4.6.2 (un fichier MS Project), et la borne des actions serveur de Next (`next.config.ts`) est réglée un peu au-dessus, l'enveloppe multipart comprise.

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

- **statut** : fini
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
- écart : l'ouverture d'une grille de mille tâches tient l'objectif d'une seconde du §4.6.2 —
  mesurée contre le faux back, pour un utilisateur seul, sur les machines de la chaîne, elle
  écrit ses chiffres sans bloquer ni `make e2e` ni la chaîne ; la seconde se tient en EP-13,
  bloquante, sur le jeu de référence, avec cinquante utilisateurs, contre le vrai service.

**Notes de réalisation.** Composant propre fondé sur TanStack Table (annexe C). C'est le
composant le plus réutilisé de l'application — planning, devis, reste à engager, risques,
coûts réels — et les US-0120 à US-0150 en sont la suite. Le tri et les filtres sont demandés
au serveur (décision du cadrage) : TanStack Table n'ordonne rien en local, et la règle « le
front ne réordonne pas ce que le back ordonne » reste sans exception. Les réglages sont une
préférence d'affichage (WF-ADM-0040), donc personnels et sans effet sur les données.

- écart : `WF-IHM-0060-A` — « Chaque colonne d'une table plate se trie dans les deux sens. » :
  le faux back rend toujours le même exemple, quel que soit le paramètre ; le réordonnancement
  effectif se constate en EP-03, sur la première grille servie par le vrai service.
- écart : `WF-IHM-0060-A` — « Dans la grille de planning, aucun en-tête de colonne ne propose
  de tri ; dans la grille de devis, le tri par montant réordonne les lignes sous chaque tâche
  sans déplacer les tâches. » : l'absence de tri sur la grille de planning se constate dans la
  maquette ; le réordonnancement des lignes sous chaque tâche demande le vrai service, qui
  rend le devis ordonné — EP-07.
- écart : `WF-IHM-0060-A` — « Les colonnes masquées et les largeurs choisies sont retrouvées
  à la réouverture, et un autre utilisateur ouvrant la même grille voit ses propres
  réglages. » : la conservation passe par `updateMyPreferences`, que le mock accepte sans
  rien garder, et le second utilisateur demande un compte réel — EP-03. Ici, l'écran des
  colonnes et des largeurs existe et écrit la préférence ; rien ne la restitue encore.
- écart : `WF-ADM-0040-A` — « Deux utilisateurs ouvrant le même projet voient les mêmes
  données présentées selon leurs réglages respectifs. » demande deux comptes réels et un projet
  — EP-04.
- écart : `WF-ADM-0040-A` — « Un utilisateur modifie ses préférences et ne peut pas modifier
  celles d'un autre. » est l'affaire de l'US-0190, et demande des comptes réels — EP-03.

## US-0120 — Grille dense : saisie au clavier seul

- **statut** : fini
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

- **statut** : fini
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
serveur produit. C'est la même forme que l'import en deux temps de WF-ARC-0100. En attendant
#200, le front refuse localement ce que le serveur ne peut pas juger faute de connaître les
colonnes montrées : un bloc plus large que les colonnes de la configuration à partir de la
cellule active, et un bloc dont la portée, dans cet ordre, enjambe une colonne masquée
(décision de la revue L1, en délégation de l'utilisateur) ; cette garde locale disparaît
avec #200.

## US-0140 — Annulation et rétablissement des saisies

- **statut** : fini
- **exigences** : `WF-IHM-0110-A`
- **opérations** : aucune en propre — `undoLastChange` et `redoLastUndo` attendent EP-06
- **issue** : #78

**En tant que** chef de projet, **je veux** annuler mes saisies une par une et rétablir ce que
je viens d'annuler, **afin de** corriger une fausse manœuvre sans reconstruire à la main ce
qu'elle a défait.

**Critères d'acceptation.**

- `WF-IHM-0110-A` — « Aucune commande n'annule un marquage, un import appliqué, une
  déclaration de survenance ou une exclusion de ligne de coût. »
- propre à l'US : Annuler et Rétablir sont présentes et positionnées — dans les grilles, au
  menu et par Ctrl+Z et Ctrl+Maj+Z — et leur état se lit ; aucune n'est branchée : elles
  n'agissent qu'en EP-06 (décision du cadrage).

**Notes de réalisation.** L'annulation sera portée par le serveur (`undoLastChange`), non
par une pile dans le navigateur : c'est ce qui permet le refus en cas de conflit, et ce que
WF-ARC-0070 impose. EP-06 branchera ces commandes ; les poser au bon endroit dès la maquette
évite de redessiner les grilles à ce moment-là.

Toute grille dont la révision en cours se saisit par sa commande `edit_*` les pose — le devis
par `edit_estimate`, le planning par `edit_planning`, le reste à engager par `edit_remaining`
(#115, qui fermera le critère propre à l'US) ; aucune grille hors d'une révision en cours ne les
pose : ni le marquage, ni un import appliqué, ni l'exclusion d'une ligne de coût ne s'annulent.
Le menu est le menu contextuel de la cellule (clic droit, Maj+F10, touche Menu), à côté des
boutons de la barre (US-0140/L1) — décision confirmée par l'utilisateur le 2026-10-07.

- écart : `WF-IHM-0110-A` — « La suppression d'une tâche puis son annulation restituent la
  tâche, ses lignes et ses liaisons. », « Le réexamen d'un risque puis son annulation lui
  rendent sa probabilité et son état précédents. », « Cinquante modifications successives
  s'annulent une par une, puis se rétablissent dans l'ordre. » et « L'annulation d'une
  modification qu'un autre contributeur a depuis reprise est refusée en nommant l'objet en
  conflit. » demandent un serveur qui restitue et qui refuse — le faux back ne conserve rien,
  et la grille des risques est en lecture seule en EP-02. Trois de ces phrases reviennent à
  EP-06, où la grille de planning conserve ses saisies, et celle du réexamen d'un risque à
  EP-08, qui réalise la saisie des risques (#337) : ici, les commandes se voient et se
  placent, elles n'agissent pas (décision du cadrage).

## US-0150 — Valeur calculée contre valeur saisie

- **statut** : fini
- **exigences** : `WF-IHM-0030-A`
- **opérations** : `getComputedValueDependencies` (EP-02/L4)
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
cadrage) : le front la lit, ligne par ligne, au lieu de recopier une règle. Ce dont une valeur
dépend, le refus le demande au serveur à son ouverture (`getComputedValueDependencies`,
EP-02/L4), qui nomme les subordonnées d'une récapitulative même quand la recherche ou les
filtres de la grille ne les montrent pas.

## US-0160 — Échelle de signalement commune, lisible sans couleur

- **statut** : fini
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
- **opérations** : `getBackgroundTask`, `markRevision`, `listBackgroundTasks` (EP-02/L4) — `getBackgroundTaskResult` passe à l'US-0260, qui décide du téléchargement d'un résultat (décision de l'utilisateur, 2026-09-29)
- **issue** : #82

**En tant que** chef de projet, **je veux** qu'une action longue me rende la main et me
signale son aboutissement même si j'ai changé d'écran, **afin de** continuer à travailler
pendant qu'un marquage ou un import se fait.

**Critères d'acceptation.**

- `WF-IHM-0080-A` — « Le marquage d'une révision de dix mille objets laisse l'écran utilisable
  et présente son avancement. » — ici, l'écran utilisable et l'avancement présenté, sur le
  faux back ; le volume de dix mille objets se constate sur le marquage réel, en EP-04
  (décision de l'utilisateur, 2026-09-29).
- `WF-IHM-0080-A` — « Un utilisateur qui change d'écran pendant un import est informé de son
  aboutissement. »
- `WF-IHM-0080-A` — « L'échec d'un traitement de fond est signalé avec son motif, et le même
  traitement peut être relancé. »

**Notes de réalisation.** Le contrat répond 202 avec une référence de tâche de fond
(WF-ARC-0090), qui porte désormais les neuf genres d'opérations longues, fusion d'une
structure et survenance d'un risque comprises (modification du cadrage) : le suivi est un
composant de la coquille, commun à toutes les tâches, et non un morceau d'écran par action
longue. Le suivi retrouve en outre, pour une session, les tâches de son utilisateur qui
courent (`listBackgroundTasks`, EP-02/L4), lancées d'un autre onglet ou d'un autre poste.

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
- écart : `WF-DAT-0100-A` — « Deux tâches de quatre heures liées fin à début, sur un
  calendrier de huit heures, commencent et finissent le même jour. » — attend le moteur de
  dates en heures d'EP-06 ; l'exigence est close en EP-07.
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
  demande deux comptes réels et un projet — EP-04.
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

- **statut** : fini
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
  du cadrage) ; seule la sortie du cycle de vie, commande du §3.6, s'y exerce — écart : le
  marquage, commande du §3.6 lui aussi, s'exerce en outre depuis l'écran des révisions, qui
  porte les commandes de la révision lue : c'est le premier emploi de `MarkCommand`, décidé
  avec le suivi des traitements longs (US-0180, conception « Commande ») ;
- propre à l'US : tout manque du contrat constaté ici est écrit dans cet EPIC, puis corrigé
  dans `docs/api` ou ouvert en issue.

## US-0220 — Écrans du planning et du devis

- **statut** : fini
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
- écart : sur mille tâches servies par le faux back, l'ouverture d'une grille tient
  l'objectif d'une seconde du §4.6.2 — mesurée contre le faux back, elle écrit ses chiffres
  sans bloquer ; la seconde se tient en EP-13, bloquante, sur le jeu de référence, avec
  cinquante utilisateurs, contre le vrai service.

**Notes de réalisation.** Le Gantt est la dernière colonne de la grille de planning (US-0220/L2) :
chaque cellule dessine en SVG la ligne de sa tâche — sa barre, les morceaux des liaisons qui la
quittent, la longent ou l'atteignent —, de sorte que le dessin est aligné ligne à ligne sur la
grille et rendu avec ses seules lignes visibles ; son en-tête porte l'axe des mois. L'arborescence
(`…/task-tree`) et les chronologies (`…/timelines`) sont deux feuilles du planning, FBS-4.3.5 et
FBS-4.3.1. Le second critère propre à l'US est porté par « modifies no task, from the pointer or
the keyboard [WF-PLA-0090-A] » (`frontend/src/components/gantt/gantt.dom.test.tsx`), par le
parcours « draws the Gantt beside the grid, row for row, the critical path told in words, and
modifies no task [WF-PLA-0090-A] » (`frontend/e2e/planning.spec.ts`) et, pour l'arborescence, par
« is one stop of the tabulation, whose arrows go through the items as in any tree, and change
nothing » (`frontend/src/components/tree/task-tree.dom.test.tsx`). Le pliage commun de la grille et
du Gantt (WF-PLA-0090), qui suppose l'arbre pliable de la grille (WF-PLA-0080), et l'export PNG de
l'arborescence et des chronologies (WF-PLA-0120, WF-PLA-0140) restent à EP-06, comme le menu
contextuel des cellules — Annuler et Rétablir —, qui s'ouvre aussi sur une cellule du Gantt, où
rien ne se saisit : EP-06, qui branche ces commandes, décide où le menu s'offre (revue 1
d'US-0220/L2). Une arborescence de quatre niveaux s'éprouve sur `nodes_nested`, une variante
contrefactuelle du cœur du témoin — le lot du poste de commande rangé sous l'installation sur
site —, engendrée par `make mock-data`.

## US-0230 — Écrans des risques, du reste à engager et des coûts réels

- **statut** : fini
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

- **statut** : fini
- **exigences** : `WF-IHM-0130-A` ; les autres sont à EP-10 et EP-11
- **opérations** : `getProjectIndicators`, `getCostCurve`, `getEarnedValueCurves`,
  `getMilestoneTracking`, `getIndexHistory`, `getProjectWorkload`, `getPortfolioProjects`,
  `getPortfolioValue`, `getPortfolioPerformance`, `getPortfolioWorkload`,
  `getPortfolioCostStructure`, `getPortfolioRisks`, `getPortfolioCostCurve`,
  `getPortfolioPilotHealth`
- **issue** : #88

**En tant que** manager, **je veux** les courbes et les tableaux d'indicateurs du projet et du
portefeuille, **afin de** voir si les endpoints d'agrégation renvoient ce qu'une vue demande,
sans que le front ait à sommer quoi que ce soit.

**Critères d'acceptation.**

- propre à l'US : aucune somme, aucune moyenne, aucun ratio n'est calculé dans le front ; une
  vue qui en aurait besoin est un constat sur le contrat ;
- propre à l'US : chaque indicateur affiché porte sa date de calcul (US-0100) ;
- propre à l'US : les zones d'indice emploient le composant de signalement de l'US-0160 ;
- `WF-IHM-0130-A` — « Le plan de charge exporté est une image PNG qui porte le nom du projet,
  la révision et la date de calcul. »

**Notes de réalisation.** Courbes en Apache ECharts (annexe C). Le plan de charge du projet
(FBS-4.4.4) a son propre écran, feuille du devis, auquel l'écran du devis mène ; son export PNG
tient `WF-IHM-0130-A` (US-0240/L4). Le portefeuille est livré en deux lots, coupés à l'estimation
(2026-10-04) : la liste des projets et la valeur du portefeuille (US-0240/L3, #120), puis les six
autres vues et la preuve de la phrase 2 de `WF-IHM-0070-A` (US-0240/L5, #310). L'horizon et le
seuil de sous-charge des vues du portefeuille (WF-PTF-0060) sont proposés parmi quelques valeurs ;
toute valeur de l'adresse que le contrat prend est envoyée et montrée choisie, et, sans seuil dans
l'adresse, le menu montre celui que le serveur a retenu — décision de la revue de #310, confirmée
par l'utilisateur le 2026-10-04.

- écart : `WF-IHM-0130-A` — « La liste des projets filtrée sur un état ne compte que les
  projets de cet état dans ses totaux. » demande un serveur qui filtre : le faux back rend
  l'exemple du contrat, quels que soient les filtres envoyés, et ne restreint pas les totaux.
  Ici, la liste des projets offre les filtres que le contrat porte — l'état d'abord —, les
  envoie à `getPortfolioProjects` et affiche le nombre de projets retenus (`meta.total`),
  sans rien sommer ; la phrase revient à EP-11, qui clôt l'exigence sur le portefeuille réel.

## US-0250 — Écrans du référentiel et de l'administration

- **statut** : fini
- **exigences** : aucune en propre — EP-03 et EP-05
- **opérations** : `getReferenceReadiness`, `getReferenceSettings`, `listOrgNodes`,
  `listResourceRoles`, `listCalendars`, `listCostTypes`, `listCostCategories`,
  `listHourlyRates`, `getHourlyRateGrid`, `setHourlyRate`, `getDurationUnits`,
  `setDurationUnits`, `listUsers`, `listAccessRoles`, `listPermissions`,
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

**Notes de réalisation.** US-0250/L1 réalise le référentiel (FBS-3.1 à 3.4) : la grille des taux
horaires sur la grille dense, écrite par `setHourlyRate`, et les autres paramètres en lecture. La
grille ne saisit que les années que la réponse porte : l'ajout d'une colonne d'année
(WF-REF-0060) manque au front, #299. Les écrans lisent les objets actifs seuls ; présenter les
désactivés, qui restent lisibles (WF-REF-0150), est #300, et filtrer chaque table sur ses
colonnes (WF-IHM-0130), #301.
US-0250/L2 réalise l'administration (FBS-1.1 à 1.4), en lecture : les comptes, désactivés
compris, chacun avec ses rôles et son rattachement nommés par le serveur, par pages ; les rôles
d'habilitation et la matrice des permissions — une ligne par permission dans l'ordre de
`listPermissions`, groupée sous la fonction de second niveau qu'elle couvre, une colonne par rôle ;
l'état du système ; les sauvegardes et leur planification, sans aucune commande. Un parcours
atteint les huit écrans du référentiel et de l'administration depuis la navigation, sans projet
ouvert. Les formulaires — créer un compte, composer un rôle, régler la planification, déclencher
une sauvegarde ou une restauration — restent aux EPICs de l'administration et de l'exploitation.

## US-0260 — Écran d'import en deux temps

- **statut** : fini
- **exigences** : aucune en propre — EP-09 et EP-12
- **opérations** : `uploadFile`, `openImport`, `getImport`, `abandonImport`, `applyImport`,
  `listImports`, `requestExport`, `getBackgroundTaskResult`
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

**Notes de réalisation.** L'écran est la feuille FBS-4.3.4 (Imports / Exports) du planning,
`…/revisions/[revisionId]/exchanges`, de la portée et de la permission du planning, sur le modèle
du plan de charge (FBS-4.4.4) : l'en-tête de l'écran du planning, son point d'accès d'après la
spécification, y mène dans le même contexte, comme l'en-tête de l'écran des coûts réels. Il offre
aussi l'import des coûts réels, qui suit `import_actual_costs` du projet. Cette place, proposée à
la revue d'US-0260/L1, est confirmée par l'utilisateur le 2026-10-04, en connaissance de ses deux
conséquences :

- l'écran est de portée révision et se lit sous la permission du planning : un utilisateur qui
  exerce `import_actual_costs` sans lire le planning y arrive par l'écran des coûts réels, mais
  pas s'il ne lit pas non plus les coûts réels ;
- un projet sans aucune révision ne peut plus rien importer, alors que l'import des coûts réels
  n'a pas besoin de révision et que WF-INTF-0090 dit que l'import en crée une au besoin — suivi en
  #332.

L'alternative écartée était un écran de portée projet, `/projects/[projectId]/…`, hors des
feuilles de la FBS, que le premier passage du lot avait pris.

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
- écart : `WF-CMP-0010-A` — « Vérifiée en recette pour Safari et les terminaux mobiles. » : la
  recette se tient sur la plateforme déployée, avec son procès-verbal — EP-13.

**Notes de réalisation.** Le harnais d'EP-01 ne joue que Chromium : c'est cette US qui lui
ajoute les quatre navigateurs — Chrome et Edge sont des canaux de Chromium dans Playwright,
Firefox et WebKit ses deux autres moteurs, et le Safari réel reste à la recette (EP-13) —
et les deux largeurs, 1366 points partout, 360 pour les vues d'indicateurs.

## US-0320 — Connexion et compte personnel

- **statut** : fini
- **exigences** : aucune en propre — l'authentification réelle est EP-03
- **opérations** : `listAuthProviders`, `openSession`, `closeSession`, `startOidcSession`,
  `requestPasswordReset`, `confirmPasswordReset`, `getMe`, `updateMyPreferences`,
  `changeMyPassword`, `putMyAvatar`, `deleteMyAvatar`, `getUserAvatar`
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
