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
- **Revue Word du 2026-10-03** : le commentaire porté sur WF-PLA-0010 (« C'est cette phrase qui a
  fait mal ») renvoie aux entrées 9 à 12 ; rien de plus à trancher ici.

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
- **Décidé en revue (2026-10-03)**, à reporter dans l'annexe et dans les textes qui la citent :
  le fichier « Devis » présente une synthèse en premier onglet, puis un onglet par lot du
  lotissement ; le fichier « Reste à engager », un onglet par sous-projet. Le lotissement
  conditionne donc la structure du fichier de devis : le §3.4.5.2.1 (« Il ne conditionne
  rien : un projet se chiffre et se pilote sans lui ») et le §3.2.3 (« sa seule valeur est
  pratique ») sont à reprendre, de même que WF-INTF-0120 (« Le sous-projet est repris s'il
  est renseigné »), puisque l'onglet le porte. Reste à dire ce que devient une ligne sans lot
  — le lot unique du lotissement par défaut — et sans sous-projet — l'ensemble « hors
  sous-projet ».
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

## 20. La consultation d'un projet restreinte à ses contributeurs

- **Où** : WF-PRJ-0060 (corps, Vérif) ; WF-ADM-0110 (corps, Vérif) ; §3.2.3 « Les
  contributeurs » ; §3.4.2.2, paragraphe « Les permissions ne portent que sur ce qu'on peut
  faire, jamais sur quel projet » ; WF-INTF-0020 (le manager « consulte les indicateurs sur
  tous les projets ») ; entrée 2 du présent fichier.
- **Quoi** : revue du 2026-10-03, quatre commentaires. La règle actuelle — la liste des
  contributeurs restreint la saisie, la consultation ne dépend que des habilitations — laisse
  tout projet lisible par quiconque porte la permission de consulter. L'auteur veut que la
  consultation d'un projet soit elle aussi réservée à ses contributeurs, sans que cela prive
  le portefeuille (FBS-2) des projets que l'utilisateur ne peut pas ouvrir : les indicateurs
  consolidés se calculent sur tout le périmètre.
- **À trancher** :
  - la règle. Proposé : la liste des contributeurs porte la consultation comme la saisie — un
    projet n'est ouvert que par ses contributeurs —, et une permission distincte, « consulter
    tous les projets », lève cette restriction pour les fonctions de direction. Le portefeuille
    agrège tout le périmètre quelle que soit la liste, parce qu'il ne montre que des sommes et
    des listes, jamais le contenu d'un projet ; un projet qu'on ne peut pas ouvrir y figure par
    son libellé, son état et ses totaux, sans lien. Écarté : filtrer aussi le portefeuille par
    contributeur, qui ferait mentir le carnet et le pipeline ;
  - ce que montre la liste des projets (entrée 1) : les projets du contributeur par défaut, et
    la levée du filtre ne montre que ceux que la permission « consulter tous les projets »
    permet d'ouvrir ;
  - le rôle prédéfini « manager » porte-t-il « consulter tous les projets » ? Proposé : oui,
    c'est l'usage de WF-INTF-0020.
- **Texte proposé** (WF-PRJ-0060, corps) : « Un projet porte la liste des utilisateurs qui y
  contribuent, dont son créateur. La consultation et la saisie sur un projet sont réservées à
  ses contributeurs, chacune sous sa permission ; la permission « consulter tous les
  projets » ouvre à la consultation les projets dont l'utilisateur n'est pas contributeur.
  Les vues du portefeuille agrègent tous les projets du périmètre, qu'ils soient ou non
  ouvrables par l'utilisateur. » Vérif : « Un utilisateur habilité à consulter les projets,
  non contributeur d'un projet et sans la permission « consulter tous les projets », ne
  l'ouvre pas et ne le trouve pas par son adresse ; le carnet du portefeuille le compte
  pourtant. Inscrit comme contributeur, il l'ouvre. »
- **Suites hors du document** : le catalogue des permissions (WF-ADM-0100) gagne une
  permission transverse ; le contrat répond déjà 404 sur une consultation refusée (entrée 2) ;
  l'accueil d'EP-02 (US-0100) et le cadrage d'EP-03 et d'EP-11.

## 21. La qualité d'un contributeur dépend du projet

- **Où** : WF-ADM-0090 (corps) ; WF-PRJ-0060 ; §3.4.2.2.
- **Quoi** : revue du 2026-10-03 : « un utilisateur peut très bien être chef de projet sur un
  projet, simple contributeur sur un autre ». Aujourd'hui les rôles d'habilitation sont
  globaux : un porteur du rôle « chef de projet » l'est sur tous les projets où il est
  contributeur. Deux lectures de la demande :
  - la liste des contributeurs qualifie chacun — chef de projet, ou contributeur — et la
    qualité restreint ce que les permissions du rôle global autorisent sur ce projet (un
    contributeur saisit les charges de son métier, ne marque pas de révision, ne touche ni au
    lotissement ni aux contributeurs) ;
  - les rôles d'habilitation s'attribuent par projet, et non plus au compte : c'est un autre
    modèle, où chaque inscription à un projet porte ses rôles.
- **À trancher** : proposé, la première lecture, qui garde le modèle à deux mécanismes (ce
  qu'on sait faire, où on le fait) et ajoute une seule donnée à la liste des contributeurs. La
  seconde revient à des habilitations par projet, que l'administration ne pourrait plus
  tenir à l'échelle de trois cents projets. Reste à dire précisément ce qu'un « contributeur »
  peut faire : proposé, tout ce que ses rôles permettent, moins les actions structurantes du
  catalogue (WF-ADM-0100 : marquer, désigner la référence, sorties du cycle de vie, risque
  survenu) et moins le paramétrage du projet (FBS-4.2), réservés aux chefs de projet du
  projet.
- **Texte proposé** : attend la décision ; touche WF-PRJ-0060, WF-ADM-0110 et le §3.2.3.

## 22. Les lignes d'un risque survenu portent un montant budgété

- **Où** : WF-RIS-0050 (corps, Vérif) ; WF-RIS-0060 (corps, Vérif) ; WF-IND-0030 (corps) ;
  WF-RAE-0040 (dernière phrase) ; §3.2.5 « Montants d'une ligne » ; §3.2.6.
- **Quoi** : revue du 2026-10-03, quatre commentaires. Aujourd'hui, à la survenance, les
  lignes du devis propre entrent dans la structure principale avec un montant budgété nul, la
  provision entre dans le budget de référence à sa valeur, et sa valeur s'acquiert d'un bloc
  quand toutes les tâches issues du devis propre sont terminées. L'auteur veut que chaque
  ligne fusionnée porte pour montant budgété sa part de la provision — son montant dans le
  devis propre multiplié par la probabilité retenue à la référence —, de sorte que la somme
  des montants budgétés des lignes fusionnées soit la provision, et que la valeur acquise
  s'acquière ligne par ligne, tâche par tâche, comme pour toute ligne. Le dépassement — on
  dépense la gravité, on n'avait budgété que la provision — dégrade l'indice de coût, et les
  provisions des risques écartés, entrant dans le budget, le rétablissent.
- **Ce qui ne change pas** : les chiffres du Vérif de WF-RIS-0050 (devis 1 060, référence
  1 000 puis 1 060, écart 190, puis 1 100) restent justes ; seul le mécanisme change.
- **À trancher** :
  - l'arrondi : la part de chaque ligne est arrondie au centime, et la dernière ligne porte le
    reste, pour que la somme soit exactement la provision ;
  - le moment où la provision d'un risque écarté entre dans le budget de référence :
    aujourd'hui, seulement lorsque plus aucun risque n'est identifié (WF-RIS-0050) ; le
    commentaire se lit aussi « à chaque risque écarté ». Proposé : garder la règle actuelle,
    qui évite qu'un écartement précoce gonfle le budget d'un projet encore exposé ;
  - la ligne de provision elle-même, après survenance : proposé, elle disparaît de la
    structure principale, remplacée par les lignes fusionnées qui en portent le montant.
- **Texte proposé** :
  - WF-RIS-0060, corps, remplacer « Les lignes fusionnées portent un montant budgété nul et,
    pour montant réestimé, celui du devis propre. » par « Chaque ligne fusionnée porte, pour
    montant budgété, son montant dans le devis propre multiplié par la probabilité du risque
    dans la révision de référence, arrondi au centime, la dernière ligne portant le reste de
    sorte que leur somme soit la provision ; et, pour montant réestimé, son montant dans le
    devis propre. La ligne de provision du risque est retirée de la structure principale. » ;
    supprimer la dernière phrase (« La valeur de la provision est acquise lorsque… ») ;
  - WF-RIS-0050, corps, remplacer « tandis que les lignes issues de son devis propre y entrent
    avec un montant budgété nul » par « portée par les lignes issues de son devis propre
    (WF-RIS-0060) » ;
  - WF-IND-0030, corps, supprimer « Les lignes issues d'un risque survenu, de montant budgété
    nul, n'y contribuent pas ; la provision du risque s'acquiert selon WF-RIS-0060. » ;
  - Vérif de WF-RIS-0060 : « Après déclaration de survenance d'un risque de gravité 200 à
    30 %, dont le devis propre porte deux lignes de 120 et 80, les lignes fusionnées portent
    des montants budgétés de 36 et 24, et des montants réestimés de 120 et 80. La valeur
    acquise augmente de 36 à la terminaison de la première tâche. »
- **Suites hors du document** : le contrat (RiskOccurrence) et EP-08.

## 23. Le devis n'affiche pas de montant réestimé

- **Où** : WF-DEV-0050 (corps, Vérif) ; WF-DEV-0020 (corps) ; §3.2.5 « Montants d'une
  ligne » ; maquette d'EP-02 (US-0130, grille de devis).
- **Quoi** : revue du 2026-10-03, deux commentaires. La maquette montre les deux montants —
  budgété, réestimé — sur la grille de devis. Pour l'auteur, le montant réestimé n'a pas de
  sens sur le devis, qui définit le budget de référence : les deux colonnes ne vont que sur la
  grille de reste à engager. Le devis montre, pour chaque ligne, son montant à l'année de
  référence et son montant corrigé de l'inflation (WF-DEV-0040), pour que l'utilisateur voie
  ce que l'inflation ajoute.
- **Ce qui ne change pas** : les deux montants restent des attributs de la ligne
  (WF-DEV-0020) ; c'est la présentation qui change.
- **Texte proposé** (WF-DEV-0050, corps) : remplacer « son délai de paiement et son montant »
  par « son délai de paiement, son montant à l'année de référence et son montant corrigé de
  l'inflation (WF-DEV-0040) ». Vérif, ajout : « La grille de devis ne présente ni montant
  budgété ni montant réestimé ; une ligne dont la tâche se place deux ans après l'année de
  référence, avec une inflation de 2 %, affiche un montant corrigé supérieur de 4,04 % à son
  montant. »
- **Suites hors du document** : issue de front sur US-0130 ; le contrat, si la grille lit
  les deux montants par un champ dédié.

## 24. Les bases de calcul du plan de charge

- **Où** : WF-DEV-0070 (corps, Vérif).
- **Quoi** : revue du 2026-10-03 : le plan de charge se calcule « soit sur le devis d'une
  révision, soit sur le reste à engager courant » ; l'auteur veut trois bases — le devis de
  référence, le reste à engager d'une révision marquée, le reste à engager courant.
- **Texte proposé** (corps) : remplacer « calculée soit sur le devis d'une révision, soit sur
  le reste à engager courant » par « calculée, au choix, sur les montants budgétés de la
  révision de référence, sur les montants réestimés d'une révision marquée, ou sur ceux de la
  révision en cours ». Vérif, ajout : « Les trois bases sont proposées ; sur un projet sans
  révision de référence, seule la révision en cours l'est. »

## 25. La réestimation du reste à engager et les dates du planning

- **Où** : WF-RAE-0040 (corps, Vérif) ; WF-PLA-0080 ; §3.4.5.5.
- **Quoi** : revue du 2026-10-03. Réestimer le reste à engager d'une tâche démarrée décale
  souvent sa fin ; rien ne rappelle au chef de projet de revoir les dates des tâches en cours.
  Deux voies proposées par l'auteur : afficher dans la grille de reste à engager, pour chaque
  tâche en édition, sa date de fin prévue, modifiable ; ou faire apparaître les tâches
  démarrées dans la grille de planning, par un filtre.
- **Avis** : la seconde, complétée. La saisie des dates a un seul lieu, la grille de planning
  (c'est la raison de WF-PLA-0090 pour le Gantt), et une date modifiée depuis le reste à
  engager relancerait le calcul des dates hors de l'écran qui le montre. La grille de reste à
  engager affiche la date de fin de chaque tâche, en lecture, et signale celles dont la fin est
  antérieure à la date de calcul ; la grille de planning gagne un filtre « tâches démarrées »,
  et la revue y passe après le reste à engager — c'est l'ordre du flux de travail (figure 16).
- **Texte proposé** :
  - WF-RAE-0040, corps, ajout : « La grille présente la date de fin de chaque tâche, sans la
    rendre saisissable, et signale les tâches démarrées dont la fin est antérieure à la date
    de calcul. » Vérif : « Une tâche démarrée dont la fin est dépassée est signalée ; sa date
    n'est pas modifiable depuis cette grille. » ;
  - WF-PLA-0080, corps, remplacer « de filtrer sur le sous-arbre d'une récapitulative » par
    « de filtrer sur le sous-arbre d'une récapitulative ou sur les tâches démarrées ».

## 26. L'état d'une tâche : trois valeurs, montrées par une marque

- **Où** : WF-PLA-0130 (corps) ; WF-PLA-0080 (corps, Vérif) ; §3.4.5.3.
- **Quoi** : revue du 2026-10-03, deux commentaires. « État d'avancement » se lit comme un
  pourcentage, alors que c'est l'état du cycle d'une tâche — non démarrée, démarrée,
  terminée — qui commande le Kanban, la réestimation et la valeur acquise. L'auteur doute de
  l'intérêt d'une colonne pour une feuille, dont l'avancement est 0 ou 100 %, et suggère une
  marque visuelle pour les tâches terminées.
- **Texte proposé** :
  - WF-PLA-0130 et partout : « état » au lieu d'« état d'avancement » ; corps, remplacer « et
    un état d'avancement » par « et un état — non démarrée, démarrée, terminée » ;
  - WF-PLA-0080, corps, remplacer « son état d'avancement, son avancement physique » par « son
    état, signalé par une marque visuelle et non par une colonne, et, pour une récapitulative,
    son avancement physique ». Vérif, ajout : « Une tâche terminée se distingue d'une tâche
    démarrée sans lire de colonne ; une feuille ne porte pas d'avancement physique. »

## 27. Le Gantt suit le pliage de la grille

- **Où** : WF-PLA-0090 (corps, Vérif) ; annexe C (rendu propre du Gantt).
- **Quoi** : revue du 2026-10-03 : « comment gère-t-on les pliages/dépliages sur la grille ?
  Un nouveau SVG à chaque fois ? ». La spécification ne dit pas que le Gantt et la grille
  partagent leur état de pliage. Côté réalisation, le Gantt est dessiné ligne par ligne, pour
  les seules lignes visibles ; plier une récapitulative retire ses lignes et redessine les
  suivantes, ce que le rendu par composants fait sans reconstruire le dessin entier. C'est
  un choix d'EP-06, pas du document.
- **Texte proposé** (WF-PLA-0090, corps, ajout) : « Le diagramme et la grille de planning
  présentent le même arbre, plié de la même façon : plier ou déplier une récapitulative dans
  l'un le fait dans l'autre. » Vérif : « Une récapitulative pliée dans la grille l'est dans le
  Gantt, et réciproquement. »

## 28. Les objets désactivés sont signalés sur les lignes qui les emploient

- **Où** : WF-REF-0010 (corps, Vérif) ; WF-DEV-0050 ; WF-RAE-0040.
- **Quoi** : revue du 2026-10-03. Un objet désactivé reste lisible partout où il est employé ;
  l'auteur veut qu'il soit signalé sur les lignes de devis d'un projet en chiffrage — où le
  chef de projet doit le remplacer, puisqu'il n'y a pas encore de référence — et sur les
  lignes de reste à engager d'un projet en cours, où il reste simplement visible.
- **Texte proposé** (WF-REF-0010, corps, ajout) : « Une ligne de devis ou de reste à engager
  qui emploie un objet désactivé le signale visuellement. » Vérif, ajout : « Après
  désactivation d'un rôle de ressource, les lignes qui le portent sont signalées dans la
  grille de devis et dans celle du reste à engager, et restent lisibles. »

## 29. La colonne de taux d'une nouvelle année : le texte contredit WF-REF-0060

- **Où** : §3.4.4.1.2, paragraphe « Un taux est une valeur constatée ».
- **Quoi** : revue du 2026-10-03. Le texte dit « Au changement d'année, une colonne vide
  apparaît », WF-REF-0060 dit « Aucune colonne n'est créée automatiquement ». L'exigence fait
  foi ; l'auteur confirme : un utilisateur habilité ajoute la colonne.
- **Texte proposé** : remplacer « Au changement d'année, une colonne vide apparaît, que les
  utilisateurs habilités renseignent (WF-REF-0060). » par « Un utilisateur habilité ajoute la
  colonne de la nouvelle année et la renseigne (WF-REF-0060) ; aucune colonne n'apparaît
  d'elle-même. »

## 30. Le dépassement potentiel au portefeuille

- **Où** : WF-PTF-0050 (corps, Vérif) ; WF-PTF-0060.
- **Quoi** : revue du 2026-10-03 : ajouter au portefeuille la somme des coûts réels et des
  restes à engager, pour donner une indication de dépassement potentiel. Cette somme est la
  projection du chef de projet (WF-IND-0050), et WF-PTF-0060 présente déjà « les trois
  projections à terminaison agrégées » face au carnet, dans la performance du portefeuille.
- **À trancher** : l'indication existe au §3.4.3.3 ; manque-t-elle sur la liste des projets
  (§3.4.3.1) ? Proposé : la liste des projets gagne, pour chaque projet en cours, sa projection
  du chef de projet et son écart au budget de référence, sans nouvelle valeur du portefeuille.
- **Texte proposé** (WF-PTF-0040, liste des projets, corps) : ajouter aux colonnes « la projection du chef de projet et son écart au budget de référence, pour un
  projet en cours ».

## 31. Le diagramme temps/temps et les décaissements se calculent pour le seul projet

- **Où** : WF-IND-0020 (corps).
- **Quoi** : revue du 2026-10-03 : l'auteur ne se souvient plus de la raison. Elle est que les
  sous-projets sont des périmètres de coûts, non de temps : un sous-projet regroupe des lignes,
  dont les tâches sont dispersées dans le planning, et il n'a ni jalon ni date de fin. Le
  diagramme temps/temps suit des jalons, donc le projet. Les décaissements, eux, pourraient se
  ventiler par sous-projet, puisque chaque ligne en porte un et un délai de paiement.
- **À trancher** : garder la règle pour le diagramme temps/temps ; pour les décaissements,
  proposé : les calculer aussi par sous-projet, ce qui ne coûte qu'un filtre. Écarté : un
  temps/temps par sous-projet, qui n'aurait pas de jalon à suivre.
- **Texte proposé** (corps) : remplacer « Le diagramme temps/temps et les projections de
  décaissement se calculent pour le seul projet. » par « Le diagramme temps/temps se calcule
  pour le seul projet : il suit des jalons, qu'un sous-projet n'a pas. »

## 32. L'exemple des dix tâches

- **Où** : §3.4.5.8.3, paragraphe « L'avancement physique dit quelle part du travail promis
  est faite ».
- **Quoi** : revue du 2026-10-03 : « un projet découpé en dix tâches aura un avancement
  grossier » est discutable — tout dépend de la durée du projet.
- **Texte proposé** : remplacer « sa finesse est celle du découpage du planning, et un projet
  découpé en dix tâches aura un avancement grossier » par « sa finesse est celle du découpage
  du planning ».

## 33. L'évolution des indices de coût et de délai

- **Où** : §3.4.5.8.4 et §3.4.5.8.5 ; nouvelle exigence, prochain identifiant libre
  `WF-IND-0130` ; WF-PTF-0060 (« l'évolution de l'ensemble dans le temps » existe déjà pour le
  portefeuille).
- **Quoi** : revue du 2026-10-03, deux commentaires : une courbe d'évolution de chaque indice.
  Les indicateurs sont calculés au marquage de chaque révision et conservés (§4.4.2) : la
  courbe par révision marquée ne demande aucun calcul nouveau.
- **Texte proposé** (nouvelle exigence, F1, FBS-4.8, PBS-1.1, PBS-2.1, PBS-2.3) :
  - titre : « Évolution des indices » ;
  - corps : « Waterfall présente, pour le projet et pour chaque sous-projet, l'évolution de
    l'indice de coût et de l'indice de délai : un point par révision marquée, à sa date de
    marquage, et le dernier point au jour courant pour la révision en cours, avec les seuils de
    vigilance et d'alerte du référentiel. » ;
  - motif : « Un indice ne se lit qu'avec sa tendance : 0,9 qui remonte et 0,9 qui descend ne
    demandent pas la même décision. Les indicateurs des révisions marquées sont conservés ;
    les montrer dans le temps ne coûte rien de plus. » ;
  - Vérif : « Sur un projet de trois révisions marquées, chaque courbe porte quatre points, le
    dernier au jour courant ; les deux seuils sont tracés ; un sous-projet a ses courbes. »

## 34. Les projections de décaissement et la courbe en S

- **Où** : WF-IND-0100, WF-IND-0120 ; §3.4.5.8.7 et §3.4.5.8.9 ; FBS-4.8.9.
- **Quoi** : revue du 2026-10-03 : les deux indicateurs semblent dire la même chose. La courbe
  en S cumule les montants aux dates des tâches — le budget, le réel aux dates de pièce, la
  projection sur les dates du reste à engager ; la projection de décaissement prend les mêmes
  montants, mois par mois, décalés du délai de paiement de chaque ligne : c'est la même
  courbe translatée, qui ne s'en écarte que lorsque les délais de paiement diffèrent d'une
  ligne à l'autre, et elle montre en plus les provisions des risques identifiés.
- **À trancher** : proposé, fusionner — la courbe en S gagne une option « décalée des délais
  de paiement », qui montre la trésorerie, et WF-IND-0120 disparaît, avec la fonction
  FBS-4.8.9 et la figure de l'arborescence. Écarté : garder deux écrans pour une translation.
  Point d'attention : l'exigence est citée par la roadmap (EP-10) et par le contrat ; le
  périmètre exclu (§2.2) admet « la projection et le suivi des dépenses ».
- **Texte proposé** (WF-IND-0100, corps, ajout) : « Sur demande, chaque montant est décalé du
  délai de paiement de sa ligne, et les provisions des risques identifiés s'ajoutent à la
  date de la tâche qui les porte : la courbe présente alors les décaissements. » Vérif,
  ajout : « Avec un délai de paiement de 60 jours sur toutes les lignes, la courbe décalée est
  la courbe de référence translatée de 60 jours. »

## 35. Tables filtrables, graphiques exportables en PNG

- **Où** : §3.6, nouvelle exigence — après celle de l'entrée 1, prochain identifiant libre
  `WF-IHM-0130` ; WF-DEV-0070 (le commentaire y demande l'export du plan de charge).
- **Quoi** : revue du 2026-10-03, deux commentaires : toute table se filtre ; toute courbe et
  toute représentation graphique s'exporte en PNG. Les grilles ont chacune leurs filtres
  (WF-PLA-0080, WF-DEV-0050, WF-RIS-0040…) ; rien ne le dit en règle générale, ni pour les
  tables du portefeuille et de l'administration.
- **Texte proposé** (nouvelle exigence, F0, FBS-1 à FBS-4, PBS-1.1, PBS-1.3) :
  - titre : « Filtrage des tables et export des graphiques » ;
  - corps : « Toute table se filtre sur chacune de ses colonnes, et le filtre s'applique aux
    totaux qu'elle présente. Toute courbe et tout diagramme — Gantt, plan de charge, courbes
    d'indicateurs, matrice des risques — s'exportent en image PNG, avec leur titre, leur
    légende, le nom du projet, la révision et la date de calcul. » ;
  - motif : « Un filtre commun évite qu'une table l'ait et l'autre non ; une image exportée
    entre dans un compte rendu de revue sans copie d'écran, et dit d'elle-même d'où elle
    vient. » ;
  - Vérif : « La liste des projets filtrée sur un état ne compte que les projets de cet état
    dans ses totaux. Le plan de charge exporté est une image PNG qui porte le nom du projet,
    la révision et la date de calcul. »
