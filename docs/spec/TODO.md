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
- **Ce que le schéma établit (2026-10-03)** : le format d'échange XML de MS Project n'a pas
  changé depuis 2010. Le schéma de Project 2013 (`mspdi_pj15.xsd`, SDK Project 2013,
  révision du 2012-07-18) garde l'espace de noms `http://schemas.microsoft.com/project/2007`
  et dit lui-même, sur `SaveVersion` : « 12 = Project 2007, 14 = Project 2010. Project 2013
  saves the same XML version as Project 2010 ». Les champs de la planification manuelle
  (`Manual`, `ManualStart`, `ManualFinish`, `ManualDuration`), que WF-PLA-0020 transporte,
  y sont, et manquent au schéma de 2007. Les pages de documentation des versions 2010, 2013
  et 2016 republient des extraits du schéma de 2007, inutilisables pour valider. Un seul
  format depuis 2010, lu par toutes les versions suivantes, qui ignorent les éléments
  qu'elles ne connaissent pas : c'est ce que le corps peut promettre, et ce qu'un fichier de
  la version 2013 vérifie.
- **À trancher en intégrant** : proposé, le corps nomme le format — celui des versions 2010
  et suivantes — et non une liste de versions ; le Vérif se tient à ce qui est disponible,
  la version 2013. Écarté : garder la liste de 2007 à 2024 et réduire le seul Vérif, qui ne
  vérifierait plus ce que le corps promet ; ramener le corps à la seule version 2013, qui
  promettrait moins que ce que le format garantit.
- **Texte proposé** :
  - corps de WF-INTF-0040, remplacer « des fichier XML de MS Project dans les version de
    2007 à 2024 » par « des fichiers au format d'échange XML de MS Project des versions
    2010 et suivantes » ;
  - Vérif de WF-INTF-0040, remplacer « Un fichier XML produit par chacune des versions
    2007, 2010, 2013, 2016, 2019, 2021 et 2024 de MS Project est importé sans erreur. » par
    « Un fichier XML produit par MS Project 2013 est importé sans erreur. »
- **Hors du document** : le XSD ne se versionne pas dans le dépôt — son en-tête réserve tous
  les droits à Microsoft et n'accorde aucune licence de redistribution, que `reuse lint`
  exigerait de déclarer. L'entrée 15 dit comment les tests s'en servent.

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

  Le corpus prouve les dates ; il ne prouve pas qu'un fichier exporté par Waterfall
  s'ouvre : MS Project est strict sur l'ordre des éléments, et un fichier mal formé se
  découvre à l'ouverture. Le schéma XML de MS Project (entrée 14) garantit cette
  structure-là, et rien d'autre : un fichier valide peut donner d'autres dates. La
  compatibilité tient donc sur deux preuves, le schéma pour la structure, le corpus pour
  les dates. Le schéma n'étant pas redistribuable, le test qui s'en sert le lit à un
  chemin déclaré du poste ou de la chaîne, et se déclare non exécuté — jamais réussi —
  quand il n'y est pas.
- **Texte proposé** (nouvelle exigence, F0, FBS-4.3 et FBS-4.3.4, PBS-2.3 et PBS-5.2) :
  - titre : « Corpus de plannings de référence et schéma d'échange » ;
  - corps : « Un corpus de plannings saisis dans MS Project et enregistrés au format XML,
    avec les dates que MS Project a calculées, est versionné avec le code. Il couvre au
    moins les quatre types de liaison, des décalages positifs et négatifs dans chaque
    unité, des calendriers dont les journées n'ont pas toutes la même durée, des tâches
    récapitulatives, des jalons et des tâches en mode manuel. Pour chaque planning du
    corpus, un test lit le fichier et vérifie que Waterfall calcule, pour chaque tâche, les
    mêmes dates de début et de fin que MS Project. Tout fichier que Waterfall exporte au
    format MS Project est valide contre le schéma XML publié par Microsoft pour ce format
    (WF-INTF-0040) ; ce schéma n'est pas versionné avec le code, et le test qui l'emploie
    se déclare non exécuté lorsqu'il est absent. » ;
  - motif : « La chaîne d'intégration ne peut pas exécuter MS Project, et un moteur éprouvé
    contre ses propres résultats ne prouve rien. Prendre pour valeurs attendues celles que
    MS Project a calculées fait de l'égalité des dates de WF-INTF-0050 et de WF-INTF-0060
    une propriété vérifiée à chaque modification, et non constatée une fois à la recette.
    C'est la raison qui fait déjà des exemples chiffrés du document des cas de test
    (WF-QUA-0020). Le schéma garantit ce que le corpus ne voit pas — qu'un fichier exporté
    s'ouvre —, et le corpus ce que le schéma ignore — que les dates sont les mêmes. Un test
    qui passerait faute de schéma cacherait son absence. » ;
  - Vérif : « Chaque cas cité par le corps figure dans au moins un planning du corpus. La
    modification de la règle de calcul des dates fait échouer au moins un test du corpus.
    Leur exécution ne demande ni MS Project, ni base de données, ni navigateur. Chaque
    planning du corpus réimporté puis exporté par Waterfall est valide contre le schéma ;
    un élément exporté hors de l'ordre du schéma fait échouer ce test, et l'absence du
    schéma le marque non exécuté. »

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
  existants : rien à prévoir dans cette passe.

## 17. Le document reste en révision A jusqu'au tag

- **Où** : historique des modifications ; indice de chaque exigence modifiée ; §1.3.1.
- **Quoi** : les entrées 5 à 7, 9 à 14 et 18 modifient le corps ou le Vérif d'exigences
  existantes, et le §1.3.1 veut que l'indice d'une exigence modifiée change. **Tranché
  (2026-10-03) : pas de révision B.** Le document reste en révision A, et toute exigence
  modifiée par cette passe garde son indice `-A`. La révision A n'est pas encore un état
  de référence : elle se met en cohérence avec le contrat d'API et la maquette d'EP-02, et
  c'est cet ensemble cohérent — spécification, contrat, maquette — qu'un tag Git fixera à
  la fin d'EP-02. Le suivi des modifications d'exigences, au sens du §1.3.1, ne commence
  qu'après ce tag : la première exigence modifiée ensuite passera à l'indice B, et le
  document avec elle. Les US de la roadmap et les tests continuent donc de citer les
  identifiants en `-A`, et `make roadmap` n'a rien à reprendre.
- **À faire en intégrant** : ne toucher ni à l'indice de révision du document, ni à celui
  des exigences ; les exigences nouvelles (entrées 1, 10, 15 et 19) naissent à l'indice A.
  Si l'historique des modifications doit dire quelque chose, c'est sur la ligne de la
  révision A, dont l'objet et l'auteur sont vides.
- **Suite hors du document** : le tag, posé par une personne sur `main`, après la fusion
  d'EP-02 et de cette passe.

## 18. L'authentification déléguée à un fournisseur d'identité

- **Où** : §3.4.2.1 (WF-ADM-0050, WF-ADM-0060, WF-ADM-0070, WF-ADM-0140, WF-ADM-0180) ;
  WF-ADM-0120 ; WF-ADM-0150 et WF-ADM-0160 ; §4.2 (troisième décision, PBS-2.5, un
  composant nouveau) ; WF-ARC-0030 ; WF-ARC-0040 ; WF-ARC-0110 ; WF-SEC-0010 ;
  WF-SEC-0020 ; WF-EXP-0020 ; WF-EXP-0040 et le tableau des modes dégradés ; WF-EXP-0050 et
  WF-EXP-0060 ; WF-CMP-0020 ; le tableau des flux techniques (TFX-06 à TFX-08) et la
  figure 17 ; le glossaire (« Annuaire d'entreprise ») ; l'annexe C.
- **Quoi** : orientation prise le 2026-09-30, avant le cadrage d'EP-03 qui porte ce
  domaine. La conception actuelle — une session en base, émise par l'API pour le seul
  navigateur, et l'authentification écrite dans Waterfall — ne sert pas ce qui viendra après
  le MVP :
  - un serveur MCP, que la spécification d'autorisation de MCP veut serveur de ressources
    OAuth 2.1, validant des jetons émis par un serveur d'autorisation ;
  - wf-requirement, qui partagera les utilisateurs de Waterfall et une seule connexion ;
  - des agents qui créent des tâches, donc des comptes de service.

  EP-03 n'étant pas commencé, le changement ne coûte aujourd'hui que la spécification et le
  contrat ; après EP-03, il coûterait la moitié de son code et la migration des comptes
  d'installations réelles. L'authentification n'est pas écrite par le projet : un
  fournisseur existant, livré avec la plateforme, porte les comptes locaux, la politique de
  mot de passe, le verrouillage, la réinitialisation, la fédération d'un annuaire LDAP ou
  Active Directory, le relais vers un fournisseur OIDC externe, la rotation des jetons et les
  comptes de service. Waterfall devient client OIDC (le front) et serveur de ressources
  (l'API, puis le serveur MCP).
- **Ce qui ne change pas** : le jeton dit qui est l'appelant, jamais ce qu'il peut faire.
  Les rôles d'habilitation, le catalogue des permissions, les contributeurs, l'état actif
  d'un compte, son rattachement, ses préférences et son avatar restent dans Waterfall, lus
  à chaque requête. C'est ce qui garde leur effet immédiat au retrait d'une permission
  (WF-ADM-0090), à la désactivation d'un compte (WF-SEC-0020) et à la qualité de
  contributeur (WF-ADM-0110) — un jeton porteur de rôles les retarderait jusqu'à son
  expiration.
- **Conséquences à écrire** :
  - WF-ADM-0140 devient la configuration livrée du fournisseur : douze caractères au moins,
    ni l'adresse ni le nom, verrouillage de quinze minutes après dix échecs, lien de
    réinitialisation d'une heure à usage unique ;
  - WF-ADM-0180 : les fournisseurs se paramètrent dans la console du fournisseur
    d'identité, non dans les écrans de Waterfall ; WF-INTF-0030 et FLX-16 le suivent ;
  - WF-ADM-0070 : l'annuaire est synchronisé par le fournisseur ; Waterfall doit pourtant
    connaître un compte avant la première connexion de la personne, pour l'inscrire comme
    contributeur ; la désactivation d'un compte que l'annuaire ne connaît plus, et la garde
    du dernier administrateur (WF-ADM-0120), se répartissent entre les deux ;
  - WF-ARC-0040 : PostgreSQL reste la seule source de vérité des données de Waterfall,
    mais les identifiants vivent dans la base du fournisseur ; les sessions quittent la
    base de Waterfall ;
  - WF-ADM-0150, WF-ADM-0160, WF-EXP-0050 et WF-EXP-0060 : une sauvegarde et une
    restauration couvrent les deux bases, faute de quoi une restauration ne rend pas une
    plateforme complète ;
  - WF-EXP-0040 : le fournisseur indisponible, aucune connexion ni aucun renouvellement de
    jeton n'aboutit, et les connexions en cours tiennent jusqu'à l'expiration de leur jeton
    d'accès ; les comptes locaux cessent d'être un recours, puisqu'ils vivent eux aussi dans
    le fournisseur ;
  - WF-EXP-0020 : l'amorçage crée le premier administrateur dans le fournisseur, et son
    compte dans Waterfall ;
  - WF-ARC-0110 : les courriels d'authentification partent du fournisseur, dans la langue
    du compte ; ses modèles existent en français et en anglais ;
  - §4.2 : PBS-2.5 devient l'intégration — validation des jetons, correspondance entre
    l'identité du fournisseur et le compte Waterfall — et le fournisseur prend un code
    PBS propre ; TFX-06 à TFX-08 et la figure 17 passent par lui.
- **À trancher en intégrant** :
  - le fournisseur. Proposé : Keycloak, le seul des trois comparés le 2026-09-30 (Keycloak,
    Zitadel, Authentik) qui tienne WF-ADM-0140 et WF-ADM-0070 tels quels — verrouillage
    temporaire, import de l'annuaire avant la première connexion —, et qui serve déjà un
    serveur MCP (enregistrement dynamique des clients, échange de jetons). Écartés :
    Zitadel, dont la fédération LDAP ne crée un compte qu'à la connexion et dont le
    verrouillage attend un administrateur ; Authentik, dont le verrouillage est une
    réputation et non un compteur, et dont l'enregistrement dynamique des clients est
    réservé à l'édition payante ;
  - comment Waterfall connaît les comptes. Proposé : il lit l'API d'administration du
    fournisseur par un compte de service, à la demande et à intervalle régulier. Écarté pour
    le MVP : SCIM, dont Keycloak n'offre encore qu'une API entrante, expérimentale ;
  - les comptes de service des agents, et leur place dans le modèle d'habilitation : ils
    peuvent attendre l'après-MVP, mais le catalogue des permissions (WF-ADM-0100) ne doit
    rien supposer d'humain.
- **Texte proposé** (WF-ARC-0030, corps, motif et Vérif remplacés) :
  - corps : « L'authentification est déléguée à un fournisseur d'identité OpenID Connect
    livré avec la plateforme, qui porte les comptes locaux, la fédération d'un annuaire
    LDAP — dont Active Directory — et, le cas échéant, le relais vers un fournisseur
    d'identité externe. Le front obtient les jetons par le flux du code d'autorisation,
    côté serveur, et ne les transmet jamais au navigateur. L'API valide chaque jeton d'accès
    par les clés publiques du fournisseur et n'en tire que l'identité de l'appelant : l'état
    de son compte, ses rôles et ses permissions sont lus dans Waterfall à chaque requête.
    Un jeton d'accès vit au plus cinq minutes ; un jeton de rafraîchissement ne sert qu'une
    fois, et son emploi en délivre un nouveau. » ;
  - motif : « Un seul serveur d'autorisation sert le front, le serveur MCP et les
    applications voisines, et leur donne une seule connexion ; confier les mots de passe,
    le verrouillage et la fédération à un produit éprouvé retire du code de sécurité au
    projet. Ne tirer du jeton que l'identité garde aux permissions et à la désactivation
    leur effet immédiat (WF-ADM-0090, WF-SEC-0020), qu'un jeton porteur de rôles
    retarderait jusqu'à son expiration. » ;
  - Vérif : « Un compte local, un compte de l'annuaire et un compte venu d'un fournisseur
    externe obtiennent chacun un jeton, et agissent selon leurs rôles dans Waterfall. Un
    jeton d'accès expiré, ou signé par une autre clé, est refusé. Un jeton de
    rafraîchissement déjà employé est refusé. Le retrait d'un rôle prend effet à la requête
    suivante, sans attendre l'expiration du jeton. Le navigateur ne détient aucun jeton. »
- **Suites hors du document** : le contrat — la famille `session` (quinze opérations) est
  remplacée, `access` reste, `startDirectorySync` et `getLatestDirectorySync` sont à
  revoir ; le front d'EP-02 — l'écran de connexion, le mot de passe et sa réinitialisation
  (US-0320) cèdent la place à la redirection vers le fournisseur, et `serverClient()` porte
  le jeton ; EP-03, à cadrer sur cette base. À intégrer avant le cadrage d'EP-03, donc
  avant la fin d'EP-02.

## 19. Le fonctionnement sur réseau isolé

- **Où** : §4.6.5, nouvelle exigence WF-CMP-0030 ; WF-CMP-0020 (un serveur de temps, un
  registre d'images) ; §4.5.1.
- **Quoi** : décidé le 2026-09-30 — le fonctionnement sur un réseau sans accès à Internet
  est un cas d'usage du MVP. Rien ne le dit, et l'exigence pèse sur des choix qui paraissent
  anodins : une police, un script ou une icône chargés depuis un réseau de diffusion à
  l'exécution, la télémétrie de Next.js, une vérification de mise à jour, un fournisseur
  d'identité hébergé en ligne. Elle impose aussi à l'installation : les images chargées
  depuis un registre interne ; les courriels par un serveur de messagerie interne, s'il en
  existe un ; des certificats émis par une autorité interne, auxquels l'API doit faire
  confiance pour lire les clés du fournisseur d'identité ; un serveur de temps interne, sans
  lequel la validation des jetons refuse des jetons valides ; les correctifs importés par le
  même circuit que les images. Les fournisseurs d'identité externes ne sont pas joignables :
  restent l'annuaire interne et les comptes locaux.
- **Texte proposé** (nouvelle exigence, F0, FBS-1, PBS-5.1) :
  - titre : « Fonctionnement sur réseau isolé » ;
  - corps : « Waterfall s'installe, fonctionne et se met à jour sur un réseau sans accès à
    Internet. Aucun de ses composants, fournisseur d'identité compris, n'émet de flux hors
    du réseau de l'installation : ni police, ni script, ni icône chargés depuis un réseau de
    diffusion, ni télémétrie, ni vérification de mise à jour. Les images se chargent depuis
    un registre interne, les courriels partent par un serveur de messagerie interne, les
    certificats peuvent être émis par une autorité interne, et l'heure vient d'un serveur
    de temps interne. Sans serveur de messagerie, la réinitialisation d'un mot de passe se
    fait par un utilisateur habilité. » ;
  - motif : « Les entreprises visées hébergent souvent leurs outils de pilotage sur des
    réseaux fermés : ils portent les coûts de toutes leurs affaires. Un seul flux sortant
    suffit à interdire une installation, et c'est au choix de chaque dépendance qu'il
    s'introduit : l'écrire est ce qui le fait chercher. » ;
  - Vérif : « La plateforme s'installe depuis un registre interne et passe les tests de bout
    en bout sur un réseau dont tout flux sortant est bloqué, sans erreur ni attente. Aucun
    composant ne tente de connexion hors du réseau de l'installation pendant ces tests. Une
    plateforme dont les certificats sont émis par une autorité interne fonctionne. »
