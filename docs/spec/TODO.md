# Trous de la spécification, à intégrer au document Word

Ce fichier accumule ce que le cadrage et la construction révèlent : des décisions prises en
route qui devraient vivre dans la spécification, et n'y sont pas. L'auteur les intègre au
Word en une passe, lance `make build-doc`, puis efface les entrées intégrées. Chaque entrée
suit la forme des constats de revue : où, quoi, et un texte proposé — à retravailler
librement dans le document.

## 1. L'écran d'accueil à la connexion

- **Où** : §3.6 (principes d'interface), nouvelle exigence — prochain identifiant libre
  `WF-IHM-0120`.
- **Quoi** : rien ne dit ce qu'un utilisateur voit en arrivant. Décidé au cadrage d'EP-02
  (2026-09-28) : la liste des projets dont il est contributeur.
- **Hypothèse à trancher en intégrant** : c'est un filtre par défaut, visible et levable —
  pas une restriction de lecture, qui contredirait WF-PRJ-0060 (« la consultation ne dépend
  que des habilitations »).
- **Texte proposé** — Corps : « À la connexion, l'utilisateur voit la liste des projets dont
  il est contributeur. Ce filtre est visible et peut être levé pour voir tout ce que ses
  habilitations permettent de consulter. » Vérif : « Un contributeur de deux projets les
  voit à sa connexion ; la levée du filtre montre aussi les projets qu'il peut seulement
  consulter. »

## 2. Introuvable et lecture refusée : le même écran

- **Où** : WF-ADM-0110 (corps), ou §3.6.
- **Quoi** : le contrat répond 404 quand la permission de consultation manque, précisément
  pour que l'existence d'un objet ne fuie pas. L'interface doit tenir la même ligne : une
  adresse inexistante et une lecture refusée mènent au même écran « introuvable ». La spec
  ne le dit que côté API.
- **Texte proposé** (corps de WF-ADM-0110, ajout) : « L'interface présente le même écran
  pour un objet inexistant et pour un objet dont la consultation n'est pas permise. »

## 3. L'installation neuve guide vers le référentiel

- **Où** : WF-CYC-0120 (corps ou Vérif), ou l'exigence de l'entrée 1.
- **Quoi** : tant que le référentiel minimal est incomplet, la création de projet est
  refusée (WF-CYC-0120). Rien ne dit ce que voit l'administrateur d'une installation
  neuve : un accueil vide sans explication serait une impasse.
- **Texte proposé** (Vérif, ajout) : « Sur une installation dont le référentiel est
  incomplet, l'accueil énonce les prérequis manquants et mène au référentiel. »

## 4. La session qui expire ramène où l'on allait

- **Où** : WF-SEC-0020 (corps), ou §3.6.
- **Quoi** : rien ne dit ce que vit l'utilisateur quand sa session expire en cours de
  travail.
- **Texte proposé** (corps, ajout) : « Une session expirée mène à l'écran de connexion ;
  la connexion refaite ramène à l'écran visé. »

## 5. La saisie des nombres suit la langue

- **Où** : WF-INTF-0180 (corps).
- **Quoi** : l'exigence couvre l'affichage (« 1 234,56 » / « 1,234.56 ») mais pas la
  saisie. Décidé au cadrage : on saisit au format de sa langue, la valeur voyage en décimal
  exact.
- **Texte proposé** (corps, ajout) : « La saisie d'un nombre suit le format de la langue de
  l'interface — virgule décimale en français, point en anglais. »

## 6. Les horodatages s'affichent en heure locale

- **Où** : WF-DAT-0100 ou WF-INTF-0180 (corps).
- **Quoi** : les horodatages sont conservés en temps universel, les dates de planning sans
  heure ne bougent jamais de fuseau — mais rien ne dit dans quelle heure s'affiche un
  horodatage (date de calcul d'un indicateur, colonnes d'audit). Décidé au cadrage : l'heure
  locale du poste.
- **Texte proposé** (corps de WF-DAT-0100, ajout) : « Un horodatage s'affiche dans l'heure
  locale du poste ; une date de planning s'affiche telle quelle. »

## 7. Une tâche non démarrée se réestime à la demande

- **Où** : WF-RAE-0030 (corps et Vérif).
- **Quoi** : WF-RAE-0030 contredisait WF-RAE-0040 sur la saisie. WF-RAE-0030 disait
  « Seules les lignes des tâches démarrées sont exposées à la réestimation du reste à
  engager » et, dans son Vérif, « Une tâche non démarrée n'y est pas modifiable » ;
  WF-RAE-0040 dit que la grille fait apparaître à la demande les tâches non démarrées
  « pour les réestimer », et son Vérif qu'elles « sont alors modifiables ». **Tranché
  (2026-09-28) : WF-RAE-0040 fait foi.** Le contrat la suit déjà : seule une ligne d'une
  tâche terminée refuse la réestimation (`setLineRemaining`, `remaining_entry`).
  WF-RAE-0040 ne change pas ; WF-RAE-0030 s'aligne.
- **Texte proposé** :
  - corps de WF-RAE-0030, remplacer « Seules les lignes des tâches démarrées sont exposées
    à la réestimation du reste à engager. » par « Les lignes des tâches démarrées sont
    exposées par défaut à la réestimation du reste à engager ; celles des tâches non
    démarrées le sont à la demande (WF-RAE-0040). » ;
  - Vérif de WF-RAE-0030, remplacer « Une tâche non démarrée n'y est pas modifiable. » par
    « Une tâche non démarrée n'y apparaît qu'à la demande. »

## 8. Le document décrit le périmètre du MVP

- **Où** : §1.1 (Objet).
- **Quoi** : décidé le 2026-09-30 — la spécification actuelle est le périmètre du MVP,
  attendu avant la fin de 2026. Ce qui viendra ensuite ne relève pas du périmètre exclu
  (§2.2) : ce sont des évolutions, qui passeront par des révisions du document. Rien ne dit
  aujourd'hui à quelle version du produit le document s'applique.
- **Texte proposé** (§1.1, ajout) : « Le périmètre décrit par ce document est celui de la
  première version publiée de Waterfall. Ses évolutions ultérieures feront l'objet de
  révisions du document. »

## 9. Le planning se calcule en heures

- **Où** : WF-PLA-0010 (corps, motif, Vérif) ; WF-INTF-0050 (corps). À relire dans la même
  passe : WF-PLA-0100 (la marge totale s'exprime désormais en temps de travail),
  WF-PLA-0130 (l'unité de la durée), §3.2.2 « Calendriers », §3.4.4.2.3 et le glossaire
  (« Calendrier »).
- **Quoi** : décidé le 2026-09-30. MS Project calcule les dates en temps de travail, en
  heures : une durée ou un décalage est converti en heures (entrée 10), puis placé heure
  après heure sur le calendrier de la tâche. WF-PLA-0010 dit le contraire : « Les heures des
  calendriers n’interviennent pas dans le calcul des dates ». Deux calendriers qui ont les
  mêmes jours travaillés et des heures différentes donnent donc les mêmes dates dans
  Waterfall et des dates différentes dans MS Project : l'égalité des dates à l'export
  (WF-INTF-0050) et la réversibilité (WF-INTF-0060) ne tiennent plus dès qu'un calendrier
  compte moins de huit heures un jour. Le motif actuel — l'intersection est la règle la plus
  contraignante, donc la plus sûre — survit s'il porte sur les heures.
- **À trancher en intégrant** : le calendrier d'une tâche qui porte plusieurs rôles. Proposé
  ci-dessous : jour par jour, le plus petit nombre d'heures de leurs calendriers — c'est
  l'intersection des plages, si les deux outils placent les heures d'un jour d'un seul
  tenant et à partir de la même heure (entrée 11). Écarté : chaque ligne sur le calendrier de
  son rôle, comme le fait MS Project pour les affectations — une tâche n'aurait plus une
  seule paire de dates.
- **Texte proposé** :
  - corps de WF-PLA-0010, remplacer tout le corps par « Le calendrier applicable à une tâche
    donne, pour chaque jour de la semaine, le plus petit des nombres d'heures travaillées
    que les calendriers des rôles de ses lignes de main-d’œuvre accordent ce jour-là. Une
    tâche qui ne porte aucune ligne de main-d’œuvre relève du calendrier par défaut. Les
    dates d'une tâche en mode automatique se calculent en heures de travail sur son
    calendrier applicable : sa durée et les décalages de ses liaisons, convertis en heures
    (WF-PLA-0160), s'y placent heure après heure. La charge de chaque ligne se répartit
    dans le temps selon le calendrier de son propre rôle. » ;
  - motif de WF-PLA-0010 : « MS Project place les durées en heures sur le calendrier de la
    tâche : un calcul en jours donnerait d'autres dates dès qu'un calendrier compte moins de
    huit heures un jour, et l'aller-retour de WF-INTF-0060 ne serait plus neutre. Retenir le
    plus petit nombre d'heures revient à ne planifier que les heures où tous les rôles
    travaillent : c'est la règle la plus contraignante, donc la plus sûre. Les écarts dus
    aux jours fériés et aux temps partiels, que le calendrier ignore, restent assumés. » ;
  - Vérif de WF-PLA-0010 : « Une tâche de seize heures en mode automatique, commencée un
    lundi matin sur un calendrier de huit heures du lundi au vendredi, finit le mardi ; sur
    un calendrier de quatre heures, elle finit le jeudi. Une tâche dont les deux rôles
    travaillent huit et six heures le lundi est planifiée sur six heures ce jour-là. Une
    tâche sans ligne de main-d’œuvre est planifiée sur le calendrier par défaut. La
    répartition mensuelle de la charge d’une ligne suit les heures du calendrier de son
    rôle. » ;
  - corps de WF-INTF-0050, remplacer « Les calendriers Waterfall doivent être exportés dans
    ce fichier. » par « Chaque tâche y porte son calendrier applicable (WF-PLA-0010) comme
    calendrier de tâche ; aucune ressource n'étant exportée, aucun calendrier de ressource
    n'intervient dans le calcul de MS Project. »
- **Suites hors du document** : le contrat (durée, début et fin d'une tâche, décalage d'une
  liaison) et la grille de planning d'EP-02 (US-0220). À intégrer avant le cadrage d'EP-06.

## 10. La conversion des unités de durée

- **Où** : nouvelle exigence WF-PLA-0160, que citent les textes proposés aux entrées 9 et
  12. Elle porte sur les unités du planning, où que vivent les constantes : leur
  emplacement ne change que « de l'installation » dans son corps.
- **Quoi** : MS Project convertit les unités par trois réglages, que son fichier XML
  transporte : les minutes par jour (480 par défaut), les minutes par semaine (2 400) et
  les jours par mois (20). « 1 j » vaut alors huit heures quel que soit le calendrier,
  « 1 sem » quarante, « 1 m » cent soixante. Le fichier conserve les durées en heures et
  les décalages en dixièmes de minute, avec l'unité de leur saisie pour l'affichage : les
  constantes ne changent pas les dates d'un fichier importé, seulement ce que vaut une
  unité saisie. Ce comportement est à confirmer sur le corpus de l'entrée 15.
- **À trancher en intégrant** : où vivent les constantes. Proposé : dans le référentiel,
  pour toute l'installation, comme la devise — « 1 j » a le même sens sur tous les projets.
  Écarté : par projet, comme MS Project — plus fidèle à un fichier importé, mais la même
  saisie ne vaudrait plus la même durée d'un projet à l'autre.
- **Texte proposé** (nouvelle exigence, F0, FBS-4.3) :
  - titre : « Unités de durée » ;
  - corps : « Une durée ou un décalage se saisit en minutes, heures, jours, semaines ou mois
    de travail, et se conserve en temps de travail avec l'unité de sa saisie. Les jours,
    les semaines et les mois se convertissent en heures par trois constantes de
    l'installation — heures par jour, heures par semaine, jours par mois —, qui valent par
    défaut 8, 40 et 20, et que l'export MS Project transporte. » ;
  - motif : « Ce sont les conventions de MS Project, avec ses valeurs par défaut : une unité
    qui ne vaudrait pas la même chose dans les deux outils changerait la durée d'une tâche
    à chaque aller-retour. Les porter par l'installation plutôt que par le projet garde à
    une unité le même sens sur tous les projets, comme la devise le garde à un montant. » ;
  - Vérif : « Avec les valeurs par défaut, une durée saisie « 2 j » vaut seize heures,
    « 1 sem » quarante heures et « 1 m » cent soixante heures. Un décalage saisi « 1 sem »
    est exporté puis réimporté sans changer d'unité. Un fichier MS Project dont les
    constantes diffèrent de celles de l'installation est importé avec les mêmes durées en
    heures, et le compte rendu signale la différence. »

## 11. Une tâche peut commencer et finir en cours de journée

- **Où** : WF-DAT-0100 (corps, Vérif) ; §4.4.1, paragraphe « Intégrité » (« les dates du
  planning, des dates sans heure ») ; entrée 6 du présent fichier.
- **Quoi** : avec des durées en heures, deux tâches de quatre heures liées fin à début
  tiennent le même jour sur un calendrier de huit heures. Si Waterfall ne sait pas où en est
  une tâche dans sa journée, les dates d'une chaîne de demi-journées s'écartent de celles de
  MS Project. Il n'a pas besoin pour autant de plages horaires : si les deux outils placent
  les heures d'un jour d'un seul tenant et à partir de la même heure, le jour où tombe une
  tâche ne dépend que du cumul des heures travaillées. L'export fabrique donc pour chaque
  calendrier une plage continue canonique — par exemple à partir de 8 h —, et le planning
  conserve pour chaque début et chaque fin une date et le nombre d'heures de travail déjà
  écoulées ce jour-là. Ce n'est pas un horodatage : aucun fuseau ne s'y applique, et la
  raison de WF-DAT-0100 — un jalon ne glisse pas d'un jour selon le poste — tient toujours.
- **À trancher en intégrant** : l'affichage. Proposé : la grille et le Gantt affichent des
  dates, comme MS Project dans son format par défaut ; l'heure n'apparaît nulle part.
- **Texte proposé** :
  - corps de WF-DAT-0100, remplacer « Les dates du planning et des pièces sont des dates
    sans heure. » par « Les dates des pièces sont des dates sans heure. Le début et la fin
    d'une tâche sont une date sans heure et un nombre d'heures de travail écoulées ce
    jour-là, sans fuseau. » ;
  - Vérif de WF-DAT-0100, ajout : « Deux tâches de quatre heures liées fin à début, sur un
    calendrier de huit heures, commencent et finissent le même jour. » ;
  - §4.4.1, « Intégrité » : remplacer « les dates du planning, des dates sans heure » par
    « le début et la fin d'une tâche, une date sans heure et des heures de travail écoulées
    ce jour-là ; les dates des pièces, des dates sans heure ».

## 12. Les unités de MS Project que Waterfall ne connaît pas

- **Où** : WF-PLA-0030 (corps) ; WF-INTF-0040 (corps).
- **Quoi** : MS Project admet des durées et des décalages en temps écoulé (« ej », « esem »,
  « em » : jours civils, week-ends compris) et des décalages en pourcentage de la durée du
  prédécesseur. WF-PLA-0030 ne connaît que j, sem et m, et l'import ne dit pas ce qu'il fait
  des autres.
- **À trancher en intégrant** :
  - les accepter : le moteur les calcule, et l'aller-retour les conserve ;
  - les convertir à l'import en temps de travail : l'aller-retour n'est plus neutre pour ces
    liaisons, et l'écart est présenté comme le prévoit déjà WF-INTF-0040 ;
  - refuser la ligne au compte rendu : l'import d'un planning réel échoue souvent.

  Proposé : la conversion, qui n'empêche aucun import et reste visible.
- **Texte proposé** :
  - corps de WF-PLA-0030, remplacer « exprimé en jours, en semaines ou en mois. L’unité est
    indiquée par un suffixe selon la convention de Microsoft Project : j, sem ou m. » par
    « exprimé en temps de travail dans l'une des unités de WF-PLA-0160. L’unité est
    indiquée par un suffixe selon la convention de Microsoft Project : min, h, j, sem ou
    m. » ;
  - corps de WF-INTF-0040, ajout : « Une durée ou un décalage exprimés en temps écoulé ou en
    pourcentage sont convertis en temps de travail, et chaque conversion figure au compte
    rendu. »

## 13. Étaler un montant ou une charge : sur quel temps

- **Où** : WF-DEV-0040, WF-DEV-0070, WF-DEV-0080, WF-IND-0120 (corps et Vérif) ;
  WF-PLA-0010 (dernière phrase) ; §3.5.1.
- **Quoi** : ces exigences étalent un montant ou une charge « par interpolation linéaire
  sur la durée de la tâche ». Avec des durées en heures, deux lectures sont possibles : au
  prorata du temps civil entre le début et la fin, ou au prorata des heures travaillées.
  Elles ne donnent ni la même valeur planifiée à une date, ni la même part d'une année pour
  l'inflation, dès que deux mois ne comptent pas autant d'heures travaillées. WF-PLA-0010
  étale déjà la charge d'une ligne selon les heures du calendrier de son rôle : les deux
  règles coexistent aujourd'hui sans que l'une dise rien de l'autre.
- **À trancher en intégrant** : proposé, les heures travaillées partout, chaque ligne selon
  le calendrier qui répartit déjà sa charge — celui de son rôle pour la main-d'œuvre, le
  calendrier applicable de la tâche sinon. La valeur planifiée, le plan de charge,
  l'inflation et les décaissements se lisent alors sur la même base. Écarté : le temps civil
  pour les montants et les heures pour la charge, plus simple, mais la valeur planifiée et
  le plan de charge ne se liraient plus sur la même base.
- **Exemples chiffrés à revérifier** : « Une ligne portée par une tâche de deux mois
  contribue pour moitié à la fin du premier mois » (WF-DEV-0080), « au prorata de la durée
  de la tâche dans chacun » (WF-DEV-0070), « dont le rapport est celui des durées de la
  tâche dans chacune » (WF-DEV-0040), et la tâche de deux mois de WF-IND-0120 ne restent
  justes que si les mois comparés comptent autant d'heures travaillées. Les Vérif doivent
  le dire, ou prendre des mois égaux.

## 14. Les versions de MS Project exigées pour le MVP

- **Où** : WF-INTF-0040 (corps, Vérif) ; WF-INTF-0050 et WF-INTF-0060 suivent, puisque leur
  Vérif renvoie aux « versions de MS Project visées par WF-INTF-0040 ».
- **Quoi** : le Vérif de WF-INTF-0040 demande un fichier produit par chacune des versions
  2007, 2010, 2013, 2016, 2019, 2021 et 2024. Seule la version 2013 est disponible
  aujourd'hui ; une licence plus récente sera prise le moment venu. En l'état, l'exigence
  resterait non vérifiée, et WF-QUA-0010 bloquerait la publication du MVP.
- **À trancher en intégrant** : proposé, le corps ramené à ce qui se vérifie pour le MVP —
  MS Project 2013 —, et l'élargissement aux autres versions par une révision ultérieure,
  avec la licence. Écarté : garder le corps et réduire le seul Vérif, qui ne vérifierait
  plus ce que le corps promet.
- **Texte proposé** :
  - corps de WF-INTF-0040, remplacer « dans les version de 2007 à 2024 » par « produits par
    MS Project 2013 » ;
  - Vérif de WF-INTF-0040, remplacer « Un fichier XML produit par chacune des versions
    2007, 2010, 2013, 2016, 2019, 2021 et 2024 de MS Project est importé sans erreur. » par
    « Un fichier XML produit par MS Project 2013 est importé sans erreur. »

## 15. Un corpus de plannings calculés par MS Project

- **Où** : §4.7, nouvelle exigence WF-QUA-0080, à côté de WF-QUA-0020.
- **Quoi** : l'égalité des dates entre Waterfall et MS Project ne se vérifie pas dans la
  chaîne d'intégration, qui ne sait pas exécuter MS Project. Elle se vérifie contre un
  corpus : des plannings saisis dans MS Project et enregistrés en XML avec les dates qu'il a
  calculées, versionnés comme fixtures. Le moteur de Waterfall doit retrouver ces dates, en
  test unitaire, sans MS Project. C'est le pendant de WF-QUA-0020 pour le calcul des dates :
  les valeurs attendues sont celles de MS Project, non celles que le moteur produit. Le
  corpus peut se constituer dès maintenant, avec MS Project 2013, avant le cadrage d'EP-06 ;
  c'est lui qui éprouvera les entrées 9 à 13.
- **Texte proposé** (nouvelle exigence, F0, FBS-4.3, PBS-2.3 et PBS-5.2) :
  - titre : « Corpus de plannings de référence » ;
  - corps : « Un corpus de plannings saisis dans MS Project et enregistrés au format XML,
    avec les dates que MS Project a calculées, est versionné avec le code. Il couvre au
    moins les quatre types de liaison, des décalages positifs et négatifs dans chaque
    unité, des calendriers dont les journées n'ont pas toutes la même durée, des tâches
    récapitulatives, des jalons et des tâches en mode manuel. Pour chaque planning du
    corpus, un test lit le fichier et vérifie que Waterfall calcule, pour chaque tâche, les
    mêmes dates de début et de fin que MS Project. » ;
  - motif : « La chaîne d'intégration ne peut pas exécuter MS Project, et un moteur éprouvé
    contre ses propres résultats ne prouve rien. Prendre pour valeurs attendues celles que
    MS Project a calculées fait de l'égalité des dates de WF-INTF-0050 et de WF-INTF-0060
    une propriété vérifiée à chaque modification, et non constatée une fois à la recette.
    C'est la raison qui fait déjà des exemples chiffrés du document des cas de test
    (WF-QUA-0020). » ;
  - Vérif : « Chaque cas cité par le corps figure dans au moins un planning du corpus. La
    modification de la règle de calcul des dates fait échouer au moins un test du corpus.
    Leur exécution ne demande ni MS Project, ni base de données, ni navigateur. »

## 16. Les formats Excel de l'annexe B

- **Où** : annexe B ; WF-INTF-0070 ; annexe D (PO-01).
- **Quoi** : l'annexe B ne porte que deux phrases. Les formats « Devis », « Reste à
  engager » et « Coûts réels » n'y sont pas décrits : ni colonnes, ni types, ni caractère
  obligatoire, ni l'emplacement du numéro de version que WF-INTF-0070 veut inscrit dans le
  fichier. Or WF-INTF-0070 à WF-INTF-0140, WF-CRE-0010 et WF-CRE-0020 renvoient à ces
  formats, et EP-09 en aura besoin le premier, pour les coûts réels. Le document fixe déjà
  une partie de leur contenu :
  - une ligne de coût porte un numéro de pièce, une date de pièce, un montant signé, un
    élément d'OTP de la forme préfixe.code projet/code sous-projet (WF-CRE-0020), et des
    colonnes conservées à titre d'information — le fournisseur, le texte de la commande, la
    référence, le document d'achat, que cite le motif de WF-CRE-0010 ;
  - une ligne de devis ou de reste à engager désigne sa tâche (obligatoire) et son
    sous-projet (facultatif), sa catégorie ou, pour la main-d'œuvre, son rôle, et sa
    quantité, sa charge ou son débours (WF-INTF-0100) ; il y manque au moins le délai de
    paiement (WF-DEV-0020) et, pour le reste à engager, le montant réestimé.
- **À trancher en intégrant** : comment une ligne désigne sa tâche. Par le libellé, deux
  tâches homonymes se confondent ; par le numéro de ligne, un planning réordonné déplace les
  lignes ; par l'identifiant de lignée, un fichier construit de zéro dans Excel n'en a pas.
  C'est ce choix qui rend vraie la phrase « Un second import du même fichier donne un devis
  identique » (WF-INTF-0100).
- **PO-01** : l'extraction des engagements et des heures relève de l'après-MVP. Le format
  étant versionné (WF-INTF-0070), il pourra s'étendre sans rendre illisibles les fichiers
  existants : rien à prévoir dans la révision B.

## 17. La révision B du document

- **Où** : historique des modifications ; indice de chaque exigence modifiée.
- **Quoi** : les entrées 5 à 7 et 9 à 14 modifient le corps ou le Vérif d'exigences
  existantes. Le §1.3.1 veut que l'indice d'une exigence modifiée change, de A à B. L'outil
  de la roadmap (`make roadmap`) et le rapport de couverture des exigences refusent un
  identifiant dont l'indice est périmé : chaque US et chaque test qui cite une exigence
  modifiée devra suivre. Peu de tests citent aujourd'hui une exigence métier, et c'est le
  moment où le passage coûte le moins. L'historique ne porte qu'une ligne, sans objet ni
  auteur.
- **À trancher en intégrant** : proposé, chaque exigence modifiée passe à l'indice B, et le
  document à la révision B — la règle du §1.3.1 telle qu'elle est écrite. Écarté : garder
  l'indice A pour les corrections faites avant le premier code métier ; moins de reprises,
  mais l'indice ne dirait plus qu'une exigence a changé. Les exigences nouvelles
  (entrées 1, 10 et 15) naissent à l'indice A.
- **Texte proposé** (historique, nouvelle ligne) : révision « B », objet « Planning calculé
  en heures ; échanges MS Project ramenés à la version 2013 ; corpus de plannings de
  référence ; formats Excel de l'annexe B ; décisions du cadrage d'EP-02 ».
