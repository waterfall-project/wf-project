---
revue_du: 2026-10-09
sur: waterfall-spec.md généré le 2026-10-08 (commit bea5aaa, branche epic/EP-02 à 78fd28e)
revue_par: Claude Code — cinq relecteurs par tranche du document, recoupés par un sixième
perimetre: document complet, section par section — avec les quatre modifications du 8 octobre (FBS-1.5, WF-ADM-0100, WF-ADM-0160, WF-SEC-0030) et l'issue #456
---

# Revue du 2026-10-09 — document complet, seconde passe

## Suivi des revues précédentes

**Les treize constats du 7 octobre (C-091 à C-103) sont tous encore ouverts, à l'identique.** Le
document n'a bougé qu'en quatre endroits depuis — l'ajout de la feuille FBS-1.5 Journal d'audit
(#518), la fonction en lecture seule dans WF-ADM-0100, le journal hors restauration dans
WF-ADM-0160 (#539), le rattachement de WF-SEC-0030 à FBS-1.5, et une Vérif de WF-IND-0130 —, et
aucune de ces retouches ne touche un passage cité par la passe précédente : chacune de ses dix-neuf
citations se retrouve mot pour mot dans la projection du 8 octobre.

**C-023** (reporté sur PO-01) reste ouvert ; **C-015** reste à passer « sans objet », comme la
passe du 7 l'a établi. Aucune régression sur les constats intégrés des neuf revues de septembre,
hormis celle que C-092 relève déjà (C-025 au §3.2.3) et deux survivances que C-175 ajoute
(C-070 et C-074 au §4.2).

## Ce que cette passe apporte par rapport à celle du 7 octobre

La passe du 7 était une lecture seule, en une journée, tournée vers le diff de la branche et les
contradictions transverses : elle a trouvé treize constats, dont huit majeurs. Celle-ci a relu le
document en cinq tranches, chacune en entier et contre le reste, puis a recoupé les cinq lectures :
elle en trouve **soixante-dix-huit**, dont **trente-quatre majeurs**, aucun bloquant. Les deux
passes ne se recouvrent pas : aucun constat d'aujourd'hui ne reprend un constat du 7, et neuf s'y
adossent explicitement (C-146 prolonge C-096, C-149 et C-150 prolongent C-094 et C-099, C-168
dépend de C-098, C-118 est de la famille de C-093, C-154 et C-170 touchent la composition du reste
à engager que C-095 corrige). L'écart de volume tient à la méthode, pas au document : la première
passe a lu ce que la branche changeait, la seconde a lu ce que chaque exigence suppose.

Trois relecteurs sur cinq ont fait indépendamment le même constat sur « révision courante »
(C-114), deux sur l'emplacement du journal d'audit (C-116), deux sur l'absence d'exigence de
FBS-1.5 (C-104), deux sur les rôles prédéfinis qui ne couvrent pas le référentiel (C-105), deux sur
la liste des actions journalisées (C-117) et deux sur la matrice (C-181) : ces constats sont
fusionnés, et c'est un indice de solidité.

**L'issue #456**, ouverte le 7 octobre par le cadrage d'EP-03 — la suppression d'un rôle
d'habilitation que WF-ADM-0090 demande et que WF-DAT-0080 interdit —, a été retrouvée par la revue
sans la connaître ; elle est reprise ici en **C-118**, avec sa proposition, pour qu'elle ait sa
trace dans les constats. Elle appartient à la même famille que C-093 du 7 octobre : le §4.4.1 dit
« trois régimes, et aucun quatrième », et deux objets — le risque, le rôle — n'entrent dans aucun
des trois tel que le §3 les décrit. C-139 y ajoute un troisième cas, le rattachement d'une tâche à
un lot que la base refuse de supprimer là où WF-DAT-0080 le permet.

## Ce que vaut le document, et où il faut regarder d'abord

Le socle tient : les 209 exigences se renvoient sans référence morte, chaque feuille de
l'arborescence a son exigence sauf la nouvelle FBS-1.5, les codes FBS et PBS existent, les
exemples chiffrés sont justes à deux exceptions près (C-145, C-162), et l'index est exact. Les
trente-quatre majeurs se rangent en huit familles ; les quatre premières méritent d'être
tranchées avant que les EPIC concernés ne figent leur contrat.

1. **Les montants et l'inflation (C-154).** Rien ne dit si le montant budgété et le montant
   réestimé sont aux taux de l'année de référence ou projetés par l'inflation ; le budget de
   référence, la valeur planifiée, la valeur acquise et le reste à engager en dépendent, et
   WF-RAE-0010 peut composer l'inflation deux fois. Deux développeurs produiront deux indices de
   coût. C'est le constat le plus lourd de la passe.
2. **Les indicateurs d'un projet sans révision en cours (C-114, C-165, C-166).** « Révision
   courante » n'est pas défini et n'est pas « révision en cours » ; un projet dont la revue vient
   d'être marquée n'a pas d'indicateurs « au jour courant » définis ; et le coût réel d'une
   révision marquée se lit par date de pièce ici, par date d'import là.
3. **Les risques et la couverture (C-160, C-161, C-162, C-170).** La Vérif de WF-RIS-0030 dit
   qu'un devis propre modifié ne change aucun indicateur, alors qu'il change la provision donc le
   reste à engager ; le coût d'un risque survenu est un montant réestimé qui retombe à zéro quand
   ses tâches se terminent, de sorte qu'en fin de projet la couverture dit toujours que les risques
   n'ont rien coûté ; les scénarios chiffrés de WF-RIS-0050 ne disent pas qu'ils repartent de zéro ;
   et le mode décaissements ajoute les provisions à un reste à engager qui les contient déjà.
4. **Le journal d'audit, ajouté le 8 octobre (C-104, C-116, C-117, C-181).** La feuille FBS-1.5
   n'a pas d'exigence et aucun rôle livré ne la porte ; le journal est « hors de ce que la
   restauration remplace » sans qu'aucun texte dise où il vit pour cela ; sa liste d'actions n'est
   pas celle du catalogue des permissions et l'inscription ne porte pas l'action ; la matrice
   FBS–PBS l'ignore.
5. **Les rôles livrés ne couvrent pas le catalogue (C-105, C-106).** Les usages du manager
   ignorent FBS-3.3 et FBS-3.4 — sur une installation neuve, personne ne peut saisir la matrice de
   risques, les seuils ni le délai entre revues, qui n'ont par ailleurs aucune valeur à l'amorçage
   — et ceux du chef de projet ignorent FBS-4.9 et les permissions distinctes : à la lettre,
   personne ne peut clore un projet.
6. **La planification (C-133, C-141, C-142, C-144, C-145, C-148, C-149, C-150).** Aucune date de
   début de planning n'existe dans le document, de sorte qu'une tâche automatique sans prédécesseur
   n'a pas d'ancre ; les suffixes d'unités renvoient à MS Project et le contredisent (« m » y est la
   minute) ; l'exemple des 2 ej place une tâche un dimanche hors de tout calendrier ; une
   récapitulative qui perd sa dernière subordonnée ne sait plus ce qu'elle est ; le rattachement au
   lotissement n'a ni périmètre (quelle structure ? la fusion ? les jalons ?) ni règle pour l'import
   MS Project ; la mise à jour des taux n'a lieu qu'à la création d'une révision, que quatre
   exigences créent sans dialogue ; et rien n'empêche un projet de perdre son dernier chef de projet.
7. **Le portefeuille (C-121, C-122).** La projection au rythme constaté agrégée n'est pas la même
   selon qu'on somme les projections ou qu'on divise les sommes, et ce qu'un projet en chiffrage
   apporte à la structure des coûts et aux risques du portefeuille n'est pas dit.
8. **La technique (C-172, C-173, C-174).** Redis indisponible arrête toute requête du front,
   puisque la session y vit, contrairement au tableau des modes dégradés ; un export est une tâche
   de fond dont le fichier n'a nulle part où attendre son téléchargement ; et la demande
   d'effacement promise au §4.6.1 n'est portée par aucune exigence.

S'y ajoutent trois majeurs isolés — la désignation d'une révision vide comme référence, qui mène
à une impasse (C-107) ; l'annexe B qui place le sous-projet dans une colonne là où WF-INTF-0120 le
place dans un onglet (C-113) ; un rôle de ressource sans libellé et un calendrier auquel la Vérif
interdit d'en avoir (C-123) — et quarante-quatre mineurs : vocabulaire, glossaire, Vérif qui
testent ce qu'une autre exigence impose, figures en retard sur les exigences, seuils sans valeur.

Trois choses ne sont pas des constats. L'annexe B reste à deux phrases, ce qui est inscrit au
`TODO.md` jusqu'au cadrage d'EP-09 — mais l'une de ces deux phrases contredit une exigence F0, et
c'est l'objet de C-113. Le compte de 209 exigences pour 210 blocs s'explique par l'exemple
WF-EXA-0010. Et les constats du 7 octobre ne sont pas recopiés : leur statut se met à jour dans
leur fichier.

## Constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-104 | majeur | §3.4.2.5 « FBS-1.5 : Journal d’audit » ; §3.1.3, WF-INTF-0030-A | FBS-1.5 est une fonction sans exigence, et aucun rôle livré ne la porte | intégré |
| C-105 | majeur | §3.1.3, WF-INTF-0020-A ; §4.5.2, WF-EXP-0020-A et texte | Sur une installation neuve, personne ne peut saisir les bornes, les seuils ni le délai entre revues, et ils n'ont aucune valeur | intégré avec écart |
| C-106 | majeur | §3.1.3 — exigence WF-INTF-0010-A ; à rapprocher de WF-ADM-0010-A,… | Les usages du chef de projet ignorent FBS-4.9 et les permissions distinctes | intégré |
| C-107 | majeur | §3.3.2 — exigence WF-CYC-0030-A ; WF-REV-0040-A | La désignation d'une révision vide comme référence se lit de deux façons, dont l'une mène à une impasse | intégré |
| C-108 | mineur | §3.2.2 « Référentiel de l’entreprise », paragraphe « Organisation… | Le modèle dit que l'arbre d'organisation ne sert qu'aux rôles ; trois exigences y rattachent les utilisateurs | intégré |
| C-109 | mineur | §3.2.1 « Conventions », troisième règle et tableau 5 ; §3.2.3,… | Deux écarts aux conventions du modèle | intégré |
| C-110 | mineur | annexe A ; WF-INTF-0040-A, WF-INTF-0100-A, WF-INTF-0120-A | Deux termes employés par les exigences du §3.1.4 sans entrée au glossaire | intégré |
| C-111 | mineur | annexe A, entrées « Sauvegarde », « Mode manuel », « Mode… | Quatre entrées en retard sur les exigences, et « projeté du chef de projet » | intégré |
| C-112 | mineur | §1.2 « Sigles et terminologie », tableau 1 | Neuf sigles employés dans le document manquent au tableau des abréviations | intégré |
| C-113 | majeur | annexe B « Formats d’échanges Excel », première phrase ; §3.1.4,… | Le sous-projet d'une ligne de reste à engager est dans un onglet selon WF-INTF-0120, dans une colonne selon l'annexe B | intégré avec écart |
| C-114 | majeur | annexe A | « Révision courante » n'est défini nulle part, et n'est pas « révision en cours » | intégré |
| C-115 | mineur | §3.3.1 — exigence WF-CYC-0120-A  ; WF-IHM-0120-A | La Vérif de WF-CYC-0120 teste l'écran d'accueil, que WF-IHM-0120 spécifie déjà | intégré |
| C-116 | majeur | §3.4.2.4, WF-ADM-0160-A et WF-ADM-0150-A ; §4.6.1, WF-SEC-0030-A | Le journal d'audit survit à la restauration, mais rien ne dit où il vit pour cela | intégré |
| C-117 | majeur | §4.6.1, WF-SEC-0030-A ; §3.4.2.2, WF-ADM-0100-A | La liste des actions journalisées n'est pas celle du catalogue, et l'inscription ne porte pas l'action | intégré avec écart |
| C-118 | majeur | §4.4.1, WF-DAT-0080-A et texte « Suppression », tableau 10 ;… | La suppression d'un rôle d'habilitation face aux régimes de suppression (issue #456) | intégré |
| C-119 | mineur | §3.4.2.2, exigence WF-ADM-0100-A | Les fonctions en lecture seule ne sont pas nommées | intégré |
| C-120 | mineur | §3.4.2.2 « FBS-1.2 : Gestion des rôles d’habilitation », texte… | « Une seule permission échappe à la liste » : les vues du portefeuille y échappent aussi | intégré |
| C-121 | majeur | §3.4.3.3, exigence WF-PTF-0070-A ; §3.4.3, WF-PTF-0020-A | La projection au rythme constaté agrégée : somme des projections ou quotient des sommes ? | intégré |
| C-122 | majeur | §3.4.3, exigence WF-PTF-0020-A ; §3.4.3.4, WF-PTF-0080-A | Ce qu'un projet en chiffrage apporte à la structure des coûts et aux risques du portefeuille n'est pas dit | intégré |
| C-123 | majeur | §3.4.4.2.2, exigences WF-REF-0090-A, WF-REF-0100-A ; §3.4.4.2.3,… | Un rôle de ressource n'a pas de libellé, et la Vérif de WF-REF-0110 interdit d'en donner un à un calendrier | intégré |
| C-124 | mineur | §3.4.4.3, exigence WF-REF-0160-A, Vérif | Une Vérif qui n'est vraie que pour des valeurs bien choisies | intégré |
| C-125 | mineur | §3.4.4, exigence WF-REF-0130-A ; à rapprocher de WF-DAT-0040-A et… | Rien ne dit si une révision marquée est lue avec les seuils et bornes de son époque ou ceux d'aujourd'hui | intégré |
| C-126 | mineur | §3.4.4 « FBS-3 : Paramètres applicatifs », texte d'introduction | « Il se divise en deux familles » : FBS-3 en compte quatre | intégré avec écart |
| C-127 | mineur | §3.3.1, exigence WF-CYC-0120-A  ; §4.5.2, WF-EXP-0020-A | « Au moins une catégorie de coût active » est satisfait dès l'amorçage, par la catégorie de provision | intégré |
| C-128 | mineur | §3.4.4.2.1 « FBS-3.2.1 : Arbre d’organisation », texte… | Le déplacement d'un nœud n'existe qu'en prose | intégré |
| C-129 | mineur | §3.4.2.1, exigence WF-ADM-0070-A ; à rapprocher de WF-ADM-0170-A… | « À intervalle régulier » : ni valeur ni paramètre | intégré |
| C-130 | mineur | annexe A ; WF-PTF-0050-A | « Réalisé », « Couverture des risques » et « Révision courante » manquent au glossaire | intégré |
| C-131 | mineur | §3.4.5.1 « Gestion des révisions » — exigence WF-REV-0010-A  ; à… | La Vérif de WF-REV-0010 suppose l'année de référence inchangée | intégré |
| C-132 | mineur | §3.4.5.1 — exigence WF-REV-0010-A ; à rapprocher de §3.3.2 | L'abandon de l'unique révision d'un projet en chiffrage n'a pas d'issue dite | intégré |
| C-133 | majeur | §3.4.5.1 — exigence WF-REV-0060-A ; WF-REV-0050-A | La mise à jour des taux n'a lieu qu'à la création d'une révision, et quatre créations se font sans dialogue | intégré |
| C-134 | mineur | §3.4.5.1 — exigence WF-REV-0080-A | La comparaison de deux révisions ne dit pas quel montant elle compare | intégré |
| C-135 | mineur | §3.4.5.1 — exigence WF-REV-0090-A ; à rapprocher de WF-REV-0030-A | Le taux d'inflation et la probabilité de gain conservés manquent aux attributs d'une révision | intégré |
| C-136 | mineur | §3.4.5.2 — exigence WF-PRJ-0010-A  ; à rapprocher de… | Un « refus » pour une transition qui n'est pas une action | intégré avec écart |
| C-137 | mineur | §3.4.5.2.1 « Lotissement du projet », texte d'introduction ; §3.2.3 | Le filtre par poste ou par lot est promis par le texte et porté par aucune exigence | intégré |
| C-138 | mineur | §3.4.5.2.1 — exigences WF-PRJ-0020-A et WF-PRJ-0030-A | Lotissement implicite et squelette : trois valeurs par défaut non dites | intégré |
| C-139 | majeur | §3.4.5.2.1 — exigence WF-PRJ-0030-A ; WF-PLA-0130-A | Ce que devient le rattachement quand le lot est supprimé ou déplacé n'est pas dit, et le §4 répond à l'envers | intégré |
| C-140 | mineur | §3.4.5.2.2 — exigence WF-PRJ-0040-A  ; à rapprocher de… | « Charges » pour « lignes » : le rechiffrage exempterait les lignes hors main-d'œuvre | intégré |
| C-141 | majeur | §3.4.5.2.4 — exigence WF-PRJ-0060-A ; à rapprocher de… | Rien n'empêche un projet de perdre son dernier chef de projet | intégré |
| C-142 | majeur | §3.4.5.3 — exigence WF-PLA-0020-A ; WF-PLA-0010-A | Aucune date de début de planning : une tâche automatique sans prédécesseur n'a pas d'ancre | intégré |
| C-143 | mineur | §3.4.5.3 — exigences WF-PLA-0040-A, WF-PLA-0130-A ; WF-INTF-0040-A | Une récapitulative en mode manuel : sans sens ici, importable depuis MS Project | intégré |
| C-144 | majeur | §3.4.5.3 — exigences WF-PLA-0030-A  et WF-PLA-0160-A | Les suffixes d'unités renvoient à MS Project et le contredisent | intégré |
| C-145 | majeur | §3.4.5.3 — exigence WF-PLA-0160-A  ; à rapprocher de WF-PLA-0010-A… | L'exemple des 2 ej fait commencer une tâche un dimanche, hors de tout calendrier | intégré |
| C-146 | mineur | §3.4.5.3 — exigence WF-PLA-0040-A  ; WF-IHM-0070-A | Les lignes propres « signalées » : dans quel écran, selon quelle échelle ? | intégré |
| C-147 | mineur | §3.4.5.3 — exigence WF-PLA-0050-A  ; WF-RAE-0030-A | Un jalon porteur de lignes terminé depuis le Kanban : accepté ou refusé ? | intégré |
| C-148 | majeur | §3.4.5.3 — exigence WF-PLA-0130-A  ; WF-PLA-0040-A | Une récapitulative qui perd sa dernière subordonnée ne sait plus ce qu'elle est | intégré |
| C-149 | majeur | §3.4.5.3 — exigence WF-PLA-0130-A ; WF-PRJ-0030-A | Le rattachement n'a pas de périmètre : structures, fusion, survenance, jalons | intégré |
| C-150 | majeur | §3.4.5.3 — exigence WF-PLA-0130-A ; §3.1.4 — WF-INTF-0040-A | L'import MS Project ne dit pas ce qu'il fait d'un déplacement refusé par WF-PLA-0130 ni d'une tâche rattachée supprimée | intégré |
| C-151 | mineur | §3.4.5.3.3 — exigence WF-PLA-0100-A ; WF-PLA-0080-A | La marge et la criticité d'une récapitulative ne sont pas définies | intégré |
| C-152 | mineur | §3.4.5.3.5 — exigence WF-PLA-0120-A | « Tenir sur une page A4 » n'est pas une condition observable | intégré |
| C-153 | mineur | §3.4.5.3 — exigence WF-PLA-0150-A  ; §4.4.2, second paragraphe | « Cent quatre-vingts révisions au plus » est une hypothèse, pas une borne | intégré |
| C-154 | majeur | §3.4.5.4, WF-DEV-0020-A ; §3.4.5.4.3, WF-DEV-0030-A | Rien ne dit si les montants et leurs agrégats sont à l'année de référence ou corrigés de l'inflation | intégré avec écart |
| C-155 | majeur | §3.4.5.8.7, WF-IND-0100-A ; §3.4.5.4.4, WF-DEV-0070-A | Le reste à engager est étalé sur toute la durée de la tâche, dates passées comprises | intégré |
| C-156 | mineur | §3.4.5.4.4, WF-DEV-0070-A | La Vérif de WF-DEV-0070 ne propose que la révision en cours là où une révision marquée existe | intégré |
| C-157 | majeur | §3.4.5.5.1, WF-RAE-0020-A | L'écart « avec le budget de référence » compare un reste à un total ; la ventilation par sous-projet compare autre chose | intégré avec écart |
| C-158 | mineur | §3.4.5.5.2, WF-RAE-0030-A ; à rapprocher de WF-PLA-0050-A | Un jalon rouvert passe à un état qu'il n'a pas | intégré avec écart |
| C-159 | mineur | §3.4.5.5.3, WF-RAE-0040-A ; §3.4.2.1, WF-ADM-0040-A | La préférence distingue des lignes ici, des tâches là | intégré |
| C-160 | majeur | §3.4.5.6, WF-RIS-0030-A | La Vérif de WF-RIS-0030 dit qu'un devis propre modifié ne change aucun indicateur ; il change le reste à engager | intégré |
| C-161 | majeur | §3.4.5.6.2, WF-RIS-0050-A ; annexe A, entrée « Écart de couverture » | Le coût d'un risque survenu est un montant réestimé, donc nul quand ses tâches sont terminées | intégré avec écart |
| C-162 | majeur | §3.4.5.6.2, WF-RIS-0050-A | La suite de scénarios de WF-RIS-0050 ne dit pas qu'elle repart de zéro, et l'écart de −30 est faux dans la continuité | intégré |
| C-163 | mineur | §3.4.5.7, WF-CRE-0020-A | La Vérif de WF-CRE-0020 rejette une forme d'OTP que le corps ne mentionne pas | intégré |
| C-164 | mineur | §3.4.5.7, WF-CRE-0040-A | « Leur somme est cohérente » n'est pas une condition observable | intégré |
| C-165 | majeur | §3.4.5.8, WF-IND-0010-A ; §3.4.5.8.5, WF-IND-0130-A | Un projet sans révision en cours n'a pas d'indicateurs au jour courant | intégré avec écart |
| C-166 | majeur | §3.4.5.8, WF-IND-0010-A ; §4.4.2, WF-DAT-0040-A | Le coût réel d'une révision marquée est défini par date de pièce ici, par date d'import là | intégré |
| C-167 | mineur | §3.4.5.8, WF-IND-0020-A | Le budget de référence par sous-projet n'est pas dans la liste des grandeurs par sous-projet | intégré |
| C-168 | mineur | §3.4.5.8, WF-IND-0030-A | La valeur acquise n'exclut pas les lignes de provision, contrairement à la valeur planifiée | intégré |
| C-169 | mineur | §3.4.5.8.6, WF-IND-0090-A | La pente 1 suppose des revues mensuelles, et le dernier point sur la diagonale suppose une abscisse non dite | intégré |
| C-170 | majeur | §3.4.5.8.7, WF-IND-0100-A ; à rapprocher de WF-RAE-0010-A | En mode décaissements, les provisions sont ajoutées à un reste à engager qui les contient déjà | intégré |
| C-171 | majeur | §3.4.5.8.7, WF-IND-0100-A ; à rapprocher de WF-DEV-0080-A | La courbe du budget ne peut pas présenter une marche si elle se lit sur la seule référence en vigueur | intégré |
| C-172 | majeur | §4.5.4, tableau 12 Modes dégradés, ligne « Redis » ; §4.4.5… | Redis indisponible : la session du front y vit, donc ni la consultation ni la saisie ne continuent, et personne ne peut se reconnecter | intégré avec écart |
| C-173 | majeur | §4.3.4 WF-ARC-0090-A ; §4.4.4  et WF-DAT-0120-A | Un export est une tâche de fond dont le fichier n'a nulle part où attendre son téléchargement | intégré |
| C-174 | majeur | §4.6.1, texte « Un mot des données personnelles » ; §3.4.2.1… | Le traitement d'une demande d'effacement est promis en prose et porté par aucune exigence | intégré |
| C-175 | mineur | §4.2 Découpage technique, texte d'introduction | Deux phrases d'introduction du §4.2 contredisent WF-DAT-0010 et WF-ARC-0040 | intégré |
| C-176 | mineur | §4.4.1, tableau 10 Correspondance entre objets et tables ; §4.3.4… | Trois données conservées sans table : le compte rendu d'import, la tâche de fond, les préférences d'affichage | intégré |
| C-177 | mineur | §4.4.5 WF-DAT-0130-A ; §4.6.3 WF-OBS-0030-A | Trois seuils ni fixés ni déclarés paramétrables | intégré |
| C-178 | mineur | §3.6 WF-IHM-0130-A | L'export PNG exige un nom de projet et une révision sur des diagrammes de portefeuille qui n'en ont pas | intégré |
| C-179 | mineur | §4.3.1 figure 18 ; §4.3.2 tableau 8 | Deux flux techniques absents : le fournisseur d'identité vers PostgreSQL, et les courriels | intégré |
| C-180 | mineur | §4.3.4, figure 19 Diagramme de séquence des imports  ; WF-ARC-0100-A | La figure 19 ne montre ni la revérification à l'application (WF-ARC-0100) ni la demande d'abandon | intégré |
| C-181 | mineur | §4.2.2, tableau 7 ; WF-SEC-0030-A | La matrice FBS–PBS n'a pas de ligne pour FBS-1.5, et la ligne FBS-1.3 n'a pas PBS-4.2 | intégré avec écart |

---

## C-104 — FBS-1.5 est une fonction sans exigence, et aucun rôle livré ne la porte

- **gravité** : majeur
- **emplacement** : §3.4.2.5 « FBS-1.5 : Journal d’audit » ; §3.1.3, `WF-INTF-0030-A` ; §3.1.2, tableau 4 ; `WF-SEC-0030-A` ; `WF-ADM-0010-A`
- **citation** : « Cette fonction en est la consultation : un utilisateur habilité parcourt les inscriptions du journal et les filtre par période, auteur, action, projet et objet. Elle est en lecture seule : elle ne modifie ni ne supprime jamais une inscription. » (§3.4.2.5) ; « de consulter l’état de fonctionnement du système, et de sauvegarder et restaurer la plateforme » (WF-INTF-0030)

**Constat.** La feuille FBS-1.5 a été ajoutée le 8 octobre pour donner une fonction à l'écran du
journal (#518). Ce que la fonction fait — parcourir, filtrer sur cinq critères, ne rien modifier —
n'est écrit que dans la prose du paragraphe : aucune exigence ne le porte, donc rien ne le
vérifie ni ne le trace (WF-QUA-0010). WF-SEC-0030, rattachée à FBS-1.5, dit ce que le journal
inscrit et combien de temps il le garde ; sa Vérif se borne à « toujours consultable ». C'est la
seule feuille de l'arborescence dans ce cas. Trois choses en dépendent : la permission
« consulter FBS-1.5 », que WF-ADM-0100 vient de créer sans qu'aucune exigence ne dise ce qu'elle
ouvre ; la qualité de contributeur, puisque le journal cite des projets que le lecteur ne peut
peut-être pas ouvrir (WF-ADM-0110) ; et le rôle prédéfini qui la porte — WF-INTF-0030 énumère
les usages de l'administrateur sans le journal, et WF-ADM-0010 fait couvrir au rôle livré les
seuls usages de WF-INTF-0030 : sur une installation neuve, personne ne peut lire le journal, comme
personne ne pouvait sauvegarder avant C-061. Enfin, le tableau 4 ne connaît qu'un flux sortant
vers l'administrateur, FLX-18 « États du système » ; le journal n'en est pas un.

**Proposition.** Ajouter au §3.4.2.5 :

```yaml exigence
section: "3.4.2.5"
id: "WF-ADM-0190-A"
titre: "Consultation du journal d’audit"
flexibilite: "F0"
fbs: "FBS-1.5"
pbs: "PBS-1.1, PBS-2.1, PBS-2.3, PBS-3.1"
corps: "Un utilisateur habilité consulte le journal d’audit (WF-SEC-0030) : la liste de ses inscriptions, de la plus récente à la plus ancienne, qui se filtre par période, par auteur, par action, par projet et par objet. Chaque inscription mène au projet concerné lorsque l’utilisateur peut le consulter (WF-ADM-0110), et le nomme par son libellé et son code sinon. La consultation est soumise à la seule permission de consulter FBS-1.5, sans condition de contributeur, et est accessible sans qu’aucun projet ne soit ouvert. Elle ne propose ni modification ni suppression d’une inscription."
motif: "Un journal qu’on ne peut pas interroger ne prouve rien de plus qu’un journal qu’on peut réécrire. Les cinq filtres sont les cinq questions qu’on pose après coup : quand, qui, quoi, sur quelle affaire, sur quel objet. La permission est propre à la fonction parce que le journal cite tous les projets, y compris ceux que son lecteur ne peut pas ouvrir : il en voit l’acte, pas le contenu."
verification: "Après le marquage d’une révision par un utilisateur, le journal filtré sur cet utilisateur et sur l’action de marquage présente une inscription datée du jour, qui nomme le projet et la révision. Filtré sur un mois sans aucune action, il ne présente rien. Une inscription sur un projet que le lecteur ne peut pas consulter nomme ce projet sans l’ouvrir. Aucune commande de la vue ne modifie ni ne supprime une inscription. Un utilisateur sans la permission de consulter FBS-1.5 n’atteint pas la vue."
```

Dans WF-INTF-0030, corps : « de gérer les comptes utilisateurs et les rôles d’habilitation, de
consulter l’état de fonctionnement du système et le journal d’audit, et de sauvegarder et
restaurer la plateforme. » Vérif : « ouvre l’écran d’état du système (FBS-1.3), ouvre le journal
d’audit et y applique un filtre (FBS-1.5), et déclenche une sauvegarde (FBS-1.4). » Tableau 4,
ajouter : « FLX-19 Journal d’audit | Waterfall | Administrateur | Sortant | IHM | À la demande »,
et l'arc correspondant dans la page « Contexte » du fichier draw.io.

**Statut.** intégré


---

## C-105 — Sur une installation neuve, personne ne peut saisir les bornes, les seuils ni le délai entre revues, et ils n'ont aucune valeur

- **gravité** : majeur
- **emplacement** : §3.1.3, `WF-INTF-0020-A` ; §4.5.2, `WF-EXP-0020-A` et texte ; §3.4.4.3, `WF-REF-0160-A` ; §3.4.4.4, `WF-REF-0170-A`, `WF-REF-0180-A` ; `WF-ADM-0010-A`
- **citation** : « Waterfall doit permettre à un utilisateur habilité de paramétrer l’organisation de l’entreprise, les rôles de ressources, les calendriers et les taux horaires, et de consulter les indicateurs agrégeant les données de plusieurs projets. » (WF-INTF-0020) ; « Les natures et catégories de coût, les rôles de ressources, l'arbre d'organisation et les taux restent à saisir. » (§4.5.2)

**Constat.** Le §3.1.2 présente le manager comme celui « qui tient le référentiel », et le
glossaire définit le référentiel commun jusqu'aux « bornes de la matrice de risques, les seuils
d’alerte des indices et le délai maximal entre deux revues ». WF-INTF-0020 n'en nomme que quatre
éléments. Les permissions étant définies par fonction de second niveau (WF-ADM-0100), les
paramètres de risques (FBS-3.3) et d'indicateurs (FBS-3.4) ont chacun leur permission, que ni
WF-INTF-0020 ni WF-INTF-0030 ne réclament : par WF-ADM-0010, aucun rôle prédéfini ne les porte,
et sur une installation neuve personne ne peut saisir la matrice, les seuils ni le délai tant
qu'un administrateur n'a pas modifié un rôle — le cas de C-061 pour la sauvegarde. L'amorçage
(WF-EXP-0020) ne leur donne par ailleurs aucune valeur et ne les cite pas parmi ce qui « reste à
saisir » : tant qu'ils sont vides, WF-REF-0170 ne sait classer aucun indice, WF-RIS-0040 ne sait
colorer aucun risque, et WF-PTF-0110 ne sait signaler aucune revue en retard, sans qu'aucune
exigence ne dise ce que ces vues affichent alors. La Vérif de WF-INTF-0020, qui écrit
« (FBS-3) » après quatre objets, ne dit pas si elle couvre le bloc ou ces quatre objets.

**Proposition.** WF-INTF-0020, corps :

> Waterfall doit permettre à un utilisateur habilité de paramétrer le référentiel commun —
> l’organisation de l’entreprise, les rôles de ressources, les calendriers, les natures et
> catégories de coût, les taux horaires, les bornes de la matrice de risques, les seuils d’alerte
> des indices et le délai maximal entre deux revues (FBS-3) — et de consulter les indicateurs
> agrégeant les données de plusieurs projets. Il peut consulter tout projet sans en être
> contributeur (WF-PRJ-0060). Le rôle prédéfini « manager » accorde ces permissions.

Vérif : « mène à leur terme le paramétrage de chacune des fonctions FBS-3.1 à FBS-3.4 — nœuds
d’organisation, rôles de ressources, calendriers, natures et catégories de coût, taux horaires,
bornes de la matrice de risques, seuils d’alerte, délai maximal entre deux revues —, ouvre les
vues du portefeuille (FBS-2) […] ». Dans WF-EXP-0020, corps, après « sa catégorie
(WF-REF-0030), » : « les bornes de la matrice de risques, les seuils d’alerte des indices et le
délai maximal entre deux revues, avec des valeurs livrées — 0,9 et 0,8 pour les seuils de chaque
indice — modifiables ensuite (WF-REF-0160 à WF-REF-0180), » ; au texte du §4.5.2, après « les
taux restent à saisir » : « ; les bornes, les seuils et le délai sont livrés avec des valeurs que
l’entreprise ajuste. » Les valeurs livrées des bornes et du délai sont à fixer par l'auteur.

**Statut.** intégré avec écart : les valeurs livrées des bornes de la matrice et du délai entre revues restent à fixer, seules celles des seuils (0,9 et 0,8) sont écrites


---

## C-106 — Les usages du chef de projet ignorent FBS-4.9 et les permissions distinctes

- **gravité** : majeur
- **emplacement** : §3.1.3 — exigence `WF-INTF-0010-A` ; à rapprocher de `WF-ADM-0010-A`, `WF-ADM-0100-A`, `WF-CYC-0060-A`, `WF-CRE-0030-A`
- **citation** : « d’en importer et d’en consulter les coûts réels, d’en lire les indicateurs, et d’importer ou d’exporter les données du projet par fichier. » (corps) ; « de lecture des indicateurs (FBS-4.8) et d’échange des fichiers du tableau des flux (FLX-01 à FLX-07), et les mène jusqu’à leur terme. » (Vérif)

**Constat.** La Vérif énumère FBS-4.1 à FBS-4.8 et s'arrête là : FBS-4.9 « Cycle de vie du
projet » n'y est pas, et le corps ne parle ni de terminer, ni de perdre, ni d'abandonner un
projet. Les trois sorties de WF-CYC-0060 sont pourtant « commandées par l’utilisateur », sous une
permission distincte (« déclarer une sortie du cycle de vie », WF-ADM-0100), et aucun des trois
usages ne les réclame : le rôle prédéfini qui en découle (WF-ADM-0010) ne permet à personne de
clore un projet. Le même raisonnement vaut pour « exclure une ligne de coût du périmètre suivi »
(WF-CRE-0030), que « consulter les coûts réels » ne couvre pas, et, plus discrètement, pour
marquer une révision, désigner la référence, fusionner un différentiel et déclarer un risque
survenu : WF-ADM-0100 les sépare exprès de la saisie, et WF-INTF-0010 ne dit pas que le rôle
prédéfini les reçoit. Un développeur qui construit le rôle « chef de projet » à partir de
WF-INTF-0010 doit deviner lesquelles des dix permissions distinctes y mettre.

**Proposition.** Corps :

> Waterfall doit permettre à un utilisateur habilité de créer un projet et ses révisions, de les
> marquer ou de les abandonner, de désigner la révision de référence et de fusionner un
> différentiel, d’en désigner les
> contributeurs, d’en construire le planning, d’en structurer le devis, d’en gérer les risques et
> d’en déclarer un survenu, d’en estimer le reste à engager, d’en importer et d’en consulter les
> coûts réels et d’en exclure une ligne du périmètre suivi, d’en lire les indicateurs, d’importer
> ou d’exporter les données du projet par fichier, et de déclarer la sortie du projet du cycle de
> vie. Le rôle prédéfini « chef de projet » accorde ces permissions, dont les permissions
> distinctes du catalogue (WF-ADM-0100) hors « restaurer la plateforme » et « consulter tous les
> projets ».

Vérif, remplacer la fin par : « … de lecture des indicateurs (FBS-4.8), de sortie du cycle de
vie (FBS-4.9) et d’échange des fichiers du tableau des flux (FLX-01 à FLX-07), et les mène
jusqu’à leur terme, marquage d’une révision, exclusion d’une ligne de coût et déclaration d’une
sortie compris. »

**Statut.** intégré


---

## C-107 — La désignation d'une révision vide comme référence se lit de deux façons, dont l'une mène à une impasse

- **gravité** : majeur
- **emplacement** : §3.3.2 — exigence `WF-CYC-0030-A` ; `WF-REV-0040-A` ; `WF-PRJ-0010-A` ; figure 8
- **citation** : « Le passage à En cours exige qu’une révision de référence soit désignée, qu’elle porte au moins une tâche et au moins une ligne de devis, et que le code projet soit renseigné. » (corps) ; « La désignation comme référence d’une révision sans tâche ou sans ligne de devis ne fait pas passer le projet à En cours, et la condition manquante est nommée à l’utilisateur. » (Vérif)

**Constat.** « Ne fait pas passer le projet à En cours » se lit de deux façons : la désignation
est refusée, ou elle est acceptée et le projet reste en Chiffrage avec une référence désignée.
Rien ne tranche, et la seconde lecture mène à une impasse. WF-REV-0040 permet de corriger la
désignation « tant que le projet n’a reçu aucun coût réel et qu’aucune révision n’a été marquée
depuis » ; pour donner des tâches à la référence, il faut marquer une autre révision (WF-REV-0020
ne demande qu'un nom de version), après quoi la correction est refusée : le projet ne peut plus
atteindre En cours, et ne peut que sortir par Perdu ou Abandonné. Par ailleurs la figure 8 nomme
un seul fait déclencheur, « Révision de référence désignée », alors que WF-CYC-0030 pose trois
conditions dont l'une, le code projet, « peut être renseigné à tout moment » (WF-PRJ-0010) : si la
référence est désignée avant le code, c'est la saisie du code qui doit faire la transition, et
aucun texte ne le dit. WF-PRJ-0010 écrit d'ailleurs « Le passage à En cours est refusé tant qu’il
n’est pas renseigné », comme s'il s'agissait d'une action, ce que WF-CYC-0020 exclut.

**Proposition.** Corps de WF-CYC-0030 :

> Le passage à En cours se produit dès que le projet porte à la fois une révision de référence
> désignée (WF-REV-0040) et un code projet (WF-PRJ-0010), quel que soit l’ordre de ces deux
> saisies. La désignation comme référence d’une révision qui ne porte aucune tâche ou aucune ligne
> de devis est refusée, en nommant la condition manquante.

Vérif : « La désignation d’une révision marquée sans tâche, ou sans ligne de devis, est refusée
et la condition manquante est nommée ; le projet n’a pas de référence. Un projet dont la référence
est désignée avant le code projet passe à En cours à la saisie du code ; un projet dont le code
est saisi avant la désignation y passe à la désignation. » Dans la figure 8, libeller la
transition « Révision de référence désignée et code projet renseigné ». Dans la Vérif de
WF-PRJ-0010, remplacer « Le passage à En cours est refusé tant qu’il n’est pas renseigné » par
« Le projet ne passe pas à En cours tant qu’il n’est pas renseigné, et la condition manquante est
nommée (WF-CYC-0050) ».

**Statut.** intégré


---

## C-108 — Le modèle dit que l'arbre d'organisation ne sert qu'aux rôles ; trois exigences y rattachent les utilisateurs

- **gravité** : mineur
- **emplacement** : §3.2.2 « Référentiel de l’entreprise », paragraphe « Organisation » ; annexe A, entrées « Nœud d’organisation » et « Utilisateur » ; à rapprocher de `WF-ADM-0030-A`, `WF-ADM-0050-A`, `WF-PRJ-0070-A`
- **citation** : « rattacher les rôles de ressources, et donc regrouper les postes par service ou département. Il ne porte aucune habilitation. » (§3.2.2, phrase commençant par « L’arbre sert à une seule chose ») ; « Les nœuds forment un arbre qui classe les rôles de ressources. Ils ne portent aucune habilitation. » (glossaire)

**Constat.** WF-ADM-0030 dit « Un compte utilisateur peut être rattaché à un nœud
d’organisation », WF-ADM-0050 en fait un attribut du compte, et WF-PRJ-0070 s'en sert pour
proposer les contributeurs — ce que le §3.2.3 raconte lui aussi (« les utilisateurs des services
dont un rôle est employé »). Le §3.2.2 affirme pourtant que l'arbre « sert à une seule chose », et
ni la figure 2, ni l'entrée « Utilisateur » du glossaire ne connaissent ce rattachement. Le
lecteur du modèle conçoit un schéma sans cette relation, et découvre au §3.4.2 qu'elle existe.
Les exigences étant claires, le risque est de lecture, pas d'implémentation.

**Proposition.** §3.2.2 :

> L’arbre sert à deux choses : rattacher les rôles de ressources, et donc regrouper les postes par
> service ou département ; et situer, facultativement, les utilisateurs (WF-ADM-0030), ce qui
> permet de proposer comme contributeurs d’un projet les utilisateurs des services dont il emploie
> un rôle (WF-PRJ-0070). Il ne porte aucune habilitation.

Glossaire, « Nœud d’organisation » : « Les nœuds forment un arbre qui classe les rôles de
ressources et, facultativement, les utilisateurs. Ils ne portent aucune habilitation. » ;
« Utilisateur » : ajouter « Il peut être rattaché à un nœud d'organisation, sans que ce
rattachement lui donne aucun droit (WF-ADM-0030). »

**Statut.** intégré


---

## C-109 — Deux écarts aux conventions du modèle

- **gravité** : mineur
- **emplacement** : §3.2.1 « Conventions », troisième règle et tableau 5 ; §3.2.3, figure 4 ; §3.2.4, figure 5
- **citation** : « Un objet ne figure dans un diagramme que s’il est défini en ANNEXE A: Glossaire. » ; « class ObjetRef["Objet du référentiel"] » (figure 4) ; « Tache <|-- Jalon : durée nulle » (figure 5)

**Constat.** La figure 4 dessine un objet « Objet du référentiel » qui n'a pas d'entrée au
glossaire, contre la troisième règle du §3.2.1 ; le glossaire définit « Référentiel commun », pas
l'objet générique. La figure 5 relie Jalon à Tâche par une flèche de spécialisation (triangle
vide), que le tableau 5 ne décrit pas : il ne connaît que l'association, la contenance et le
trait pointillé. Le texte dit bien qu'un jalon « est une tâche de durée nulle », mais le lecteur
qui applique le tableau ne sait pas lire la flèche.

**Proposition.** Ajouter au tableau 5 :

> | Trait plein terminé par un triangle vide | Spécialisation. L’objet du côté du triangle est le cas général, l’autre un cas particulier qui en a toutes les propriétés : « un jalon *est une* tâche, de durée nulle ». |

Ajouter au glossaire :

> **Objet du référentiel.** Désigne l'un des objets du référentiel commun — nœud d'organisation,
> rôle de ressource, calendrier, nature de coût, catégorie de coût ou taux horaire — tel qu'une
> révision en conserve la valeur employée (WF-REV-0030).

**Statut.** intégré


---

## C-110 — Deux termes employés par les exigences du §3.1.4 sans entrée au glossaire

- **gravité** : mineur
- **emplacement** : annexe A ; `WF-INTF-0040-A`, `WF-INTF-0100-A`, `WF-INTF-0120-A` ; §3.2.5, paragraphe « Montants d’une ligne »
- **citation** : « met à jour l’objet existant sans toucher à sa lignée, à ses lignes de devis ni à son état » (WF-INTF-0040) ; « une ligne sans identifiant crée une ligne non anticipée (WF-RAE-0050) » (WF-INTF-0120)

**Constat.** « Lignée » est employé par trois exigences F0 du §3.1.4 et par leurs Vérif, et n'est
défini qu'au §4.4.2 (WF-DAT-0030), que le lecteur du §3 n'a pas encore atteint ; le glossaire
n'en dit rien. « Ligne non anticipée » et « tâche non anticipée » sont employés par WF-INTF-0120,
par le §3.2.5 et par le texte du §3.4.5.5.3 comme des termes définis, avec un renvoi à WF-RAE-0050
qui, lui, parle de « travail qui n’avait pas été anticipé » sans nommer la chose.

**Proposition.** Ajouter au glossaire :

> **Lignée.** Désigne l'identité qu'une tâche ou une ligne de devis conserve d'une révision à
> l'autre, distincte de l'identifiant propre à chaque révision (WF-DAT-0030). C'est elle que les
> imports rapprochent, qu'un différentiel désigne, et qui permet de comparer deux révisions.
>
> **Ligne non anticipée.** Désigne une ligne de devis, ou une tâche et ses lignes, ajoutée à la
> structure principale après la révision de référence pour du travail qui n'avait pas été
> chiffré (WF-RAE-0050). Elle porte un montant budgété nul et pèse sur le reste à engager, jamais
> sur le budget de référence.

**Statut.** intégré


---

## C-111 — Quatre entrées en retard sur les exigences, et « projeté du chef de projet »

- **gravité** : mineur
- **emplacement** : annexe A, entrées « Sauvegarde », « Mode manuel », « Mode automatique », « Tâche récapitulative », « Avancement financier » ; §3.4.5.8.1, texte d'introduction
- **citation** : « Désigne une copie datée et vérifiée de la base de données, dans un état cohérent » ; « Désigne le mode dans lequel Waterfall ne recalcule pas automatiquement l’ensemble des éléments de planification. L’utilisateur peut notamment saisir directement les dates des tâches. » ; « à partir des durées, des dépendances et des calendriers » ; « Elle synthétise leur périmètre, leur durée, leurs dates et, le cas échéant, leur avancement. » ; « le coût réel rapporté au projeté du chef de projet »

**Constat.**
- **Sauvegarde** : WF-ADM-0150 et WF-ADM-0160 couvrent « l’intégralité de la base de données de
  Waterfall et celle du fournisseur d’identité » ; le glossaire n'en connaît qu'une.
- **Mode manuel** : WF-PLA-0020 est net — « l’utilisateur saisit ses dates et Waterfall ne les
  recalcule jamais » ; le glossaire dit « ne recalcule pas automatiquement l’ensemble des
  éléments » et « peut notamment », ce qui laisse croire à un recalcul partiel.
- **Mode automatique** : « dépendances » n'est pas un terme du document, qui dit « liaisons »
  partout ailleurs (glossaire « Liaison », WF-PLA-0020).
- **Tâche récapitulative** : « le cas échéant, leur avancement » est en retard sur WF-PLA-0040,
  où l'état d'une récapitulative découle toujours de ses subordonnées et de ses lignes propres.
- **Projeté du chef de projet** : WF-IND-0050 nomme « la projection du chef de projet » ; le
  glossaire (« Avancement financier ») et le texte du §3.4.5.8.1 disent « projeté du chef de
  projet », reliquat du vocabulaire que C-064 a fait changer ailleurs.

**Proposition.**

> **Sauvegarde.** Désigne une copie datée et vérifiée des deux bases de données de la
> plateforme, Waterfall et fournisseur d'identité, chacune dans un état cohérent, à partir de
> laquelle la plateforme peut être restaurée (WF-ADM-0150).
>
> **Mode manuel.** Désigne le mode dans lequel l'utilisateur saisit les dates d'une tâche et
> Waterfall ne les recalcule jamais, y compris lorsque ses prédécesseurs se déplacent
> (WF-PLA-0020).
>
> **Mode automatique.** Désigne le mode dans lequel Waterfall calcule les dates d'une tâche à
> partir de sa durée, de ses liaisons et de son calendrier applicable, et les recalcule à chaque
> modification de l'un d'eux (WF-PLA-0020).
>
> **Tâche récapitulative.** Désigne une tâche qui porte des sous-tâches. Ses dates, sa durée et
> son état d'avancement découlent de ses subordonnées (WF-PLA-0040). Elle peut porter ses propres
> lignes de devis, et son coût est alors la somme de celles-ci et de celles de ses subordonnées.

Et « projection du chef de projet » dans l'entrée « Avancement financier » et au §3.4.5.8.1.

**Statut.** intégré


---

## C-112 — Neuf sigles employés dans le document manquent au tableau des abréviations

- **gravité** : mineur
- **emplacement** : §1.2 « Sigles et terminologie », tableau 1
- **citation** : « Fichier XML MS Project (WF-INTF-0040) » (tableau 3) ; « Désigne le code d'imputation que l'ERP attache à chaque ligne de coût. » (glossaire, « Élément d'OTP »)

**Constat.** C-067 avait fait entrer onze sigles du §4 au tableau 1. En restent neuf, dont trois
dans mon périmètre : XML (dix occurrences, dès le tableau des flux), OTP (sept, dont l'entrée de
glossaire « Élément d'OTP », qui ne développe pas le sigle), UML (§3.2.1). Hors périmètre : PNG
(six), HTTP, TLS (employé dans les définitions mêmes de HTTPS et LDAPS), URL, DSI, MVP.

**Proposition.** Ajouter au tableau 1 :

> | DSI | Direction des systèmes d’information |
> | HTTP | Protocole de transfert hypertexte (HyperText Transfer Protocol) |
> | MVP | Produit minimum viable (Minimum Viable Product) |
> | OTP | Organigramme technique de projet, structure d’imputation de l’ERP |
> | PNG | Format d’image sans perte (Portable Network Graphics) |
> | TLS | Protocole de chiffrement des échanges (Transport Layer Security) |
> | UML | Langage de modélisation unifié (Unified Modeling Language) |
> | URL | Adresse d’une ressource Web (Uniform Resource Locator) |
> | XML | Format de données structurées (eXtensible Markup Language) |

**Statut.** intégré

---

## C-113 — Le sous-projet d'une ligne de reste à engager est dans un onglet selon WF-INTF-0120, dans une colonne selon l'annexe B

- **gravité** : majeur
- **emplacement** : annexe B « Formats d’échanges Excel », première phrase ; §3.1.4, exigence `WF-INTF-0120-A` ; §3.2.3, paragraphe « Deux découpages sans lien entre eux »
- **citation** : « Les formats « Devis » et « Reste à engager » comportent une colonne de désignation de tâche, obligatoire, et une colonne de sous-projet, facultative. » (annexe B) ; « Le sous-projet d’une ligne est celui de l’onglet qui la porte, le format plaçant chaque sous-projet dans un onglet. » (WF-INTF-0120) ; « et il structure le fichier de devis de l’annexe B, un onglet par lot. » (§3.2.3)

**Constat.** L'annexe B est encore à écrire — c'est connu et ce n'est pas l'objet du constat.
Mais sa seule phrase normative contredit deux passages du document. Pour le format « Reste à
engager », WF-INTF-0120 (F0) place chaque sous-projet dans un onglet et en déduit le sous-projet
de la ligne ; l'annexe B lui donne une colonne de sous-projet. Pour le format « Devis », le
§3.2.3 fait du lotissement la structure du fichier, « un onglet par lot », ce que l'annexe B ne
dit pas. Le développeur de l'import de reste à engager ne peut pas satisfaire WF-INTF-0120 et
l'annexe B à la fois, et celui de l'import de devis ne sait pas si un fichier à un seul onglet
est conforme.

**Proposition.** Remplacer la première phrase de l'annexe B par :

> Le format « Devis » place chaque lot du lotissement dans un onglet (§3.2.3) ; chaque ligne y
> porte une colonne de désignation de tâche, obligatoire, et une colonne de sous-projet,
> facultative. Le format « Reste à engager » place chaque sous-projet dans un onglet, et les
> lignes sans sous-projet dans un onglet « Hors sous-projet » (WF-INTF-0120) ; chaque ligne y
> porte une colonne de désignation de tâche, obligatoire, et aucune colonne de sous-projet. Les
> deux formats portent l’identifiant de ligne que l’export écrit, et que l’import rapproche
> (WF-INTF-0100, WF-INTF-0120).

Si l'auteur préfère au contraire une colonne pour les deux formats, c'est WF-INTF-0120 qu'il
faut corriger : « Le sous-projet d’une ligne est celui de sa colonne de sous-projet, absent
lorsqu’elle est vide. »

**Statut.** intégré avec écart : le format « Reste à engager » à un onglet par sous-projet ; l’alternative de la colonne, signalée en commentaire, n’a pas été retenue


---

## C-114 — « Révision courante » n'est défini nulle part, et n'est pas « révision en cours »

- **gravité** : majeur
- **emplacement** : annexe A (entrée manquante ; l'entrée « Assiette du projet » emploie le terme) ; §3.2.5 ; §3.5.1 ; `WF-RAE-0010-A`, `WF-RAE-0030-A`, `WF-REF-0160-A`, `WF-RIS-0050-A`, `WF-IND-0100-A` ; `WF-PTF-0010-A` ; « devis courant » dans `WF-PTF-0040-A`, `WF-PTF-0050-A`
- **citation** : « pour chaque tâche de la structure principale de la révision courante » (WF-RAE-0010) ; « le total hors provisions du devis de sa révision courante » (WF-REF-0160) ; « Au jour courant, chaque projet contribue par sa révision en cours et ses indicateurs au jour courant. » (WF-PTF-0010)

**Constat.** Le document emploie « révision en cours » soixante-douze fois et « révision
courante » douze fois, dont le corps de WF-RAE-0010 — la définition même du reste à engager — et
celui de WF-REF-0160 ; « devis courant » paraît quatre fois, dont l'entrée « Pipeline » du
glossaire. Le glossaire définit « Révision », « Révision marquée » et « Révision de référence »,
pas « Révision courante ». Les deux termes ne sont pas synonymes : un projet n'a pas toujours de
révision en cours — après chaque marquage, après une fusion (WF-REV-0050), dans un état
terminal —, alors que son reste à engager, son assiette et ses indicateurs existent toujours ; et
le reste à engager d'une révision marquée se calcule sur cette révision (WF-IND-0010), qui n'est
pas « en cours » mais est bien celle dans laquelle on lit. Le lecteur devine « la révision dans
laquelle on lit ; au jour courant, la révision en cours s'il en existe une, sinon la dernière
marquée », mais il devine, et WF-PTF-0010 écrit « révision en cours » là où il faut lire
« courante » : pris au mot, un projet qui vient de marquer sa revue ne contribue par rien au
portefeuille au jour courant. Trois relecteurs ont fait ce constat séparément.

**Proposition.** Ajouter au glossaire :

> **Révision courante.** Désigne la révision dans laquelle une grandeur est lue ou calculée :
> pour les indicateurs d'une révision marquée, cette révision ; au jour courant, la révision en
> cours d'élaboration lorsqu'il en existe une, sinon la dernière révision marquée (WF-IND-0010).
> C'est elle que lisent le reste à engager (WF-RAE-0010), le devis courant, l'assiette du projet
> (WF-REF-0160) et le portefeuille au jour courant (WF-PTF-0010).
>
> **Devis courant.** Désigne le devis de la structure principale de la révision courante d'un
> projet, lignes de provision comprises sauf lorsque le texte précise « hors provisions »
> (WF-REF-0160). C'est lui que le pipeline somme pour les projets en chiffrage (WF-PTF-0050).

Dans WF-PTF-0010, corps : « Au jour courant, chaque projet contribue par sa révision courante et
ses indicateurs au jour courant. » Vérif, ajouter : « Un projet dont la revue vient d’être marquée
et qui n’a pas de révision en cours contribue par cette revue. » Ce que valent alors les
indicateurs « au jour courant » d'un tel projet fait l'objet de C-165.

**Statut.** intégré


---

## C-115 — La Vérif de WF-CYC-0120 teste l'écran d'accueil, que WF-IHM-0120 spécifie déjà

- **gravité** : mineur
- **emplacement** : §3.3.1 — exigence `WF-CYC-0120-A` (Vérif) ; `WF-IHM-0120-A`
- **citation** : « Sur une installation dont le référentiel est incomplet, l’accueil énonce les prérequis manquants et mène au référentiel. »

**Constat.** La phrase figure mot pour mot dans le corps de WF-IHM-0120 et, à peine changée, dans
sa Vérif. Dans WF-CYC-0120, elle n'a pas de corps : l'exigence porte sur le refus de créer un
projet, pas sur l'accueil. Une Vérif qui teste ce qu'une autre exigence impose fait courir deux
traces pour un seul comportement, et c'est la seconde qu'on oublie de mettre à jour — le
problème que C-040 avait relevé pour l'immuabilité des révisions marquées.

**Proposition.** Vérif de WF-CYC-0120 : « Sur une plateforme dont le référentiel est incomplet,
la création d’un projet est refusée, et le refus nomme chaque prérequis manquant. La création
aboutit dès que tous les prérequis sont satisfaits. L’énoncé des prérequis manquants à l’accueil
relève de WF-IHM-0120. »

**Statut.** intégré


---

## C-116 — Le journal d'audit survit à la restauration, mais rien ne dit où il vit pour cela

- **gravité** : majeur
- **emplacement** : §3.4.2.4, `WF-ADM-0160-A` et `WF-ADM-0150-A` ; §4.6.1, `WF-SEC-0030-A` (champ PBS) ; §4.2.1.4 « PBS-4.2 Journaux » ; §4.4.1 (régimes de données, paragraphe « Audit », tableau 10) ; `WF-ARC-0040-A` ; §3.4.2 (texte d'introduction)
- **citation** : « La restauration remplace l’intégralité des deux bases — Waterfall et fournisseur d’identité — par leur contenu sauvegardé » puis « Le journal d’audit est hors de ce qu’elle remplace : il garde les inscriptions postérieures à la sauvegarde, et la restauration s’y inscrit une fois faite (WF-SEC-0030). » (WF-ADM-0160) ; « les journaux structurés des services, dont le journal d’audit des actions irréversibles (§4.6.1) » (PBS-4.2) ; « Aucune donnée métier n'existe ailleurs que dans PostgreSQL. » (WF-ARC-0040)

**Constat.** La phrase ajoutée le 8 octobre à WF-ADM-0160 (#539) tranche la bonne question, mais
elle suppose un emplacement que le document ne donne pas, et chaque emplacement possible casse
une exigence :

- **si le journal est une table de la base de Waterfall** — ce que suggèrent le champ PBS de
  WF-SEC-0030 (PBS-3.1), la consultation filtrée du §3.4.2.5, la conservation « aussi longtemps
  que les projets » et WF-ARC-0110, qui en fait « un message conservé » —, alors « remplace
  l’intégralité des deux bases » le remplace aussi, et la nouvelle phrase contredit la précédente
  dans la même exigence. Le §3.4.2 dit d'ailleurs encore que « la restauration les remplace
  toutes ensemble, sans en distinguer aucune » ;
- **si le journal est dans les journaux structurés des services**, comme le dit PBS-4.2, il
  échappe à la restauration mais aussi à la sauvegarde, qui ne couvre que les deux bases
  (WF-ADM-0150) : une perte de la plateforme l'emporte, contre « conservé aussi longtemps que
  les projets » et contre WF-EXP-0050 ; et rien ne dit comment un flux de journaux se filtre par
  projet ni se protège de toute suppression « depuis la plateforme » ;
- **le tableau 10 ne le mentionne pas**, et le paragraphe « Audit » du §4.4.1 dit seulement
  qu'il « n’est pas une colonne » : aucun des quatre régimes de données ne l'accueille.

Un développeur doit donc choisir seul entre une table et un fichier, et dans les deux cas une
exigence F0 est fausse. La réponse qui fait tenir les trois exigences est la première : une table
de la base de Waterfall, sauvegardée comme le reste, que la restauration préserve explicitement,
et dont la protection relève de la base comme pour les révisions marquées (WF-DAT-0020).

**Proposition.** Six retouches, dans l'ordre du document.

1. **§3.4.2, texte** : « Aucune d’elles ne modifie une donnée de projet en particulier ; la
   restauration les remplace toutes ensemble, hors le journal d’audit, qui en garde la trace
   (WF-ADM-0160). »
2. **WF-ADM-0160, corps**, remplacer la dernière phrase par : « Le journal d’audit (WF-SEC-0030)
   est conservé à travers la restauration : ses inscriptions postérieures à la date de la
   sauvegarde sont relues avant le remplacement des bases et réinscrites après lui, et la
   restauration elle-même s’y inscrit une fois faite. » Vérif, ajouter : « Une inscription faite
   après la sauvegarde est encore présente après la restauration, et la dernière inscription est
   la restauration elle-même. »
3. **WF-SEC-0030**, champ PBS : « PBS-3.1 » ; corps, ajouter après « le projet s'il y en a un » :
   « Le journal est une table de la base de Waterfall, du régime plateforme (§4.4.1), sauvegardée
   avec elle (WF-ADM-0150) ; la base refuse toute modification et toute suppression de ses
   lignes, comme pour une révision marquée (WF-DAT-0020). » Vérif, ajouter : « Une mise à jour ou
   une suppression exécutée directement en base sur une inscription du journal est rejetée par la
   base. »
4. **PBS-4.2** : « les journaux structurés des services (WF-OBS-0020). » Le journal d'audit n'y
   est plus cité.
5. **§4.4.1**, régime plateforme : « comptes, rôles d’habilitation, permissions, sauvegardes,
   inscriptions du journal d’audit. Sans lien avec les projets, hors la référence qu’une
   inscription du journal porte vers le sien. » Tableau 10, après « Sauvegarde » : « Inscription
   au journal d’audit (WF-SEC-0030) | audit_entry | plateforme ». Paragraphe « Audit », fin :
   « c’est une table à part, dont les lignes ne se modifient ni ne se suppriment. »
6. **Annexe A** : « **Journal d’audit.** Désigne la table qui inscrit chaque action irréversible
   ou structurante avec sa date, son auteur, son objet et son projet (WF-SEC-0030). Il se
   consulte (FBS-1.5), ne se modifie ni ne se supprime, et survit à une restauration
   (WF-ADM-0160). »

**Statut.** intégré


---

## C-117 — La liste des actions journalisées n'est pas celle du catalogue, et l'inscription ne porte pas l'action

- **gravité** : majeur
- **emplacement** : §4.6.1, `WF-SEC-0030-A` ; §3.4.2.2, `WF-ADM-0100-A` ; §3.4.2.5
- **citation** : « Chaque action irréversible ou structurante est inscrite dans un journal d'audit : le marquage d'une révision, la désignation de la révision de référence, la contractualisation d'un avenant, la déclaration d'un risque survenu, la sortie du cycle de vie d'un projet, l'exclusion ou la réintégration d'une ligne de coût, l'application d'un import, la création et la modification des comptes, des rôles et de leurs attributions, la sauvegarde et la restauration. » ; « Chaque inscription porte la date, l'auteur, l'objet concerné et le projet s'il y en a un. » (WF-SEC-0030) ; « créer un projet, marquer une révision, abandonner une révision en cours, désigner la révision de référence » (WF-ADM-0100)

**Constat.** Les deux exigences emploient la même expression, « actions irréversibles ou
structurantes », et n'en dressent pas la même liste. WF-ADM-0100 y range l'abandon d'une
révision en cours — qui supprime physiquement ses lignes (WF-DAT-0010), et dont la trace est
précisément ce qu'on cherchera quand un mois de saisie aura disparu — et la création d'un
projet ; WF-SEC-0030 ne les inscrit pas. WF-ADM-0090 permet de supprimer un rôle ; le journal
n'inscrit que « la création et la modification » des rôles. La Vérif de WF-SEC-0030 porte sur
« chacune des actions énumérées » : un développeur qui la suit ne journalise ni l'abandon ni la
suppression. Enfin, le §3.4.2.5 filtre le journal « par action », mais l'inscription ne porte
pas l'action : la date, l'auteur, l'objet et le projet, sans dire ce qui a été fait.

**Proposition.** Corps de WF-SEC-0030 :

> Chaque action irréversible ou structurante — celles que WF-ADM-0100 soumet à une permission
> propre, et celles qui s'y ajoutent ici — est inscrite dans un journal d'audit : la création
> d'un projet, le marquage d'une révision, l'abandon d'une révision en cours, la désignation de
> la révision de référence, la contractualisation d'un avenant, la déclaration d'un risque
> survenu, la sortie du cycle de vie d'un projet, l'exclusion ou la réintégration d'une ligne de
> coût, l'application d'un import, la création, la modification et la désactivation d'un
> compte, la création, la modification et la suppression d'un rôle d'habilitation,
> l'attribution et le retrait d'un rôle à un compte, la sauvegarde et la restauration. Chaque
> inscription porte l'action, la date, l'auteur, l'objet concerné et le projet s'il y en a un.

Vérif, ajouter : « L'abandon d'une révision en cours et la suppression d'un rôle produisent
chacun une inscription qui nomme l'action et l'objet. »

**Statut.** intégré avec écart : la phrase ajoutée à la Vérif de WF-SEC-0030 suit « datée et attribuée » plutôt que de clore le champ, et l’anonymisation de C-174 y est jointe

---

## C-118 — La suppression d'un rôle d'habilitation face aux régimes de suppression (issue #456)

- **gravité** : majeur
- **emplacement** : §4.4.1, `WF-DAT-0080-A` et texte « Suppression », tableau 10 ; §3.4.2.2, `WF-ADM-0090-A`, `WF-ADM-0010-A`, `WF-ADM-0120-A`
- **citation** : « Les objets du référentiel et de la plateforme ne sont jamais supprimés ; ils se désactivent. » (WF-DAT-0080) ; « Un utilisateur habilité peut créer, modifier, renommer et supprimer des rôles, et attribuer ou retirer des rôles aux comptes. Un rôle ne peut être supprimé tant qu’un compte le porte. » (WF-ADM-0090) ; « Un administrateur en renomme un, en modifie les permissions et le supprime, sans erreur. » (WF-ADM-0010)

**Constat.** Ce constat reprend l'issue
[waterfall-project/wf-project#456](https://github.com/waterfall-project/wf-project/issues/456),
ouverte le 7 octobre par le cadrage d'EP-03 et toujours « à trancher », pour qu'elle ait sa trace
ici ; la revue l'a retrouvée indépendamment. Le tableau 10 range le rôle d'habilitation
(`access_role`) dans le régime plateforme, dont WF-DAT-0080 dit qu'il ne supprime jamais ;
WF-ADM-0090 et WF-ADM-0010 demandent de supprimer un rôle, et WF-ADM-0120 refuse « la
suppression de son rôle » au dernier administrateur, ce qui suppose qu'elle existe. Les deux
lectures — suppression physique, désactivation — donnent deux réalisations, et le journal d'audit
(WF-SEC-0030) cite les rôles et leurs attributions passées, qu'une suppression physique
laisserait sans objet. Il relève de la même famille que C-093 : le §4.4.1 dit « trois régimes,
et aucun quatrième », et deux objets — le risque, le rôle — n'entrent dans aucun des trois tel
que le §3 les décrit. EP-03 a retenu en attendant une suppression logique (US-0380/L1, #444) :
le rôle supprimé n'est plus lu ni attribuable, et sa ligne est conservée.

**Proposition.** Celle de l'issue, complétée. WF-DAT-0080, corps, première phrase :

> Les objets du référentiel et de la plateforme ne sont jamais supprimés physiquement : ils se
> désactivent, ou, pour un rôle d’habilitation, se suppriment sans que leur trace disparaisse.

Vérif de WF-DAT-0080 : « Aucune commande ne supprime physiquement un rôle de ressource, un rôle
d’habilitation ou un compte. » WF-ADM-0090, corps, ajouter : « Un rôle supprimé n’est plus
proposé ni attribuable, et reste cité par le journal d’audit. » Vérif, ajouter : « Un rôle
supprimé n’apparaît plus dans la liste des rôles ni dans les choix d’attribution ; l’inscription
du journal d’audit qui l’attribuait à un compte le nomme toujours. » Au §4.4.1, texte
« Suppression », première puce : « le référentiel et la plateforme ne suppriment jamais
physiquement : un objet se désactive (WF-REF-0130, WF-ADM-0060), et un rôle d’habilitation se
supprime en conservant sa ligne (WF-ADM-0090) ».

**Statut.** intégré


---

## C-119 — Les fonctions en lecture seule ne sont pas nommées

- **gravité** : mineur
- **emplacement** : §3.4.2.2, exigence `WF-ADM-0100-A`
- **citation** : « Une fonction en lecture seule, comme la consultation du journal d’audit (FBS-1.5), n’a que la permission de consulter. »

**Constat.** « Comme » donne un exemple, pas la liste, et le catalogue est « livré avec la
plateforme et n’est pas modifiable » : c'est donc le développeur qui arrête la liste. L'écran
d'état (FBS-1.3) ne modifie rien ; les sept vues du portefeuille « ne permettent aucune saisie »
(WF-PTF-0030). Deux catalogues sont possibles, l'un avec dix permissions de modifier sans objet,
l'autre sans ; la Vérif — « ses deux permissions, ou … la seule permission de consulter pour une
fonction en lecture seule » — ne tranche pas entre eux.

**Proposition.** « Les fonctions en lecture seule — la surveillance de l’état du système
(FBS-1.3), le journal d’audit (FBS-1.5) et les vues du portefeuille (FBS-2.1 à FBS-2.7) — n’ont
que la permission de consulter. » Vérif : « ou par la seule permission de consulter pour FBS-1.3,
FBS-1.5 et FBS-2.1 à FBS-2.7. »

**Statut.** intégré


---

## C-120 — « Une seule permission échappe à la liste » : les vues du portefeuille y échappent aussi

- **gravité** : mineur
- **emplacement** : §3.4.2.2 « FBS-1.2 : Gestion des rôles d’habilitation », texte d'introduction, second paragraphe
- **citation** : « Une seule permission échappe à la liste, « consulter tous les projets » »

**Constat.** Le paragraphe pose que c'est la liste des contributeurs qui restreint la
consultation aux participants, à une exception près. Il y en a une seconde, posée par
WF-PTF-0030 et rappelée par WF-PRJ-0060 : les vues du portefeuille agrègent tous les projets du
périmètre, ouvrables ou non, et un utilisateur qui en porte la permission les lit « qu’il soit
ou non contributeur des projets qu’elles agrègent ». Le texte n'est pas faux sur « consulter tous
les projets », il est incomplet, et c'est le paragraphe que lira celui qui implémente le filtre.

**Proposition.** « Deux choses échappent à la liste : la permission « consulter tous les
projets », qui ouvre à un manager la lecture de tous les projets sans lui permettre d’y saisir ;
et les vues du portefeuille (FBS-2), qui agrègent tous les projets du périmètre et n’ouvrent que
ceux que l’utilisateur peut consulter (WF-PTF-0030). »

**Statut.** intégré


---

## C-121 — La projection au rythme constaté agrégée : somme des projections ou quotient des sommes ?

- **gravité** : majeur
- **emplacement** : §3.4.3.3, exigence `WF-PTF-0070-A` ; §3.4.3, `WF-PTF-0020-A` ; `WF-IND-0050-A`
- **citation** : « les trois projections à terminaison agrégées face au budget de référence agrégé » (WF-PTF-0070) ; « La projection au rythme constaté est le budget de référence divisé par l’indice de coût » (WF-IND-0050)

**Constat.** WF-PTF-0020 pose deux règles : une *grandeur* de portefeuille est la somme des
grandeurs des projets, un *indice* est le rapport des sommes. La projection au rythme constaté
est un montant obtenu par un quotient, et les deux règles ne donnent pas le même nombre. Deux
projets de budget 1 000 : l'un avec une valeur acquise de 400 pour un coût réel de 500
(indice 0,8, projection 1 250), l'autre avec 500 pour 500 (indice 1, projection 1 000). La
somme des projections vaut 2 250 ; le budget agrégé divisé par l'indice agrégé (2 000 / 0,9)
vaut 2 222. Et la somme n'est pas définie dès qu'un projet du périmètre n'a pas de coût réel,
puisque sa projection est non calculable (WF-IND-0050) ; le quotient des sommes l'est. Les deux
autres projections sont des sommes de sommes et n'ont pas ce problème. Un développeur choisira
l'une ou l'autre, et deux écrans — celui-ci et la courbe en S du portefeuille, qui somme les
projections du chef de projet — ne raconteront plus la même histoire.

**Proposition.** Dans WF-PTF-0070, corps, remplacer « les trois projections à terminaison
agrégées face au budget de référence agrégé » par :

> les trois projections à terminaison agrégées face au budget de référence agrégé — la
> projection au budget et celle du chef de projet comme sommes des projections des projets, la
> projection au rythme constaté comme le budget de référence agrégé divisé par l’indice de coût
> agrégé, non calculable tant que celui-ci ne l’est pas (WF-PTF-0020)

Vérif, ajouter : « Sur deux projets de budget 1 000, de valeur acquise 400 et 500 et de coût
réel 500 et 500, la projection au rythme constaté agrégée vaut 2 222 et non 2 250. »

**Statut.** intégré


---

## C-122 — Ce qu'un projet en chiffrage apporte à la structure des coûts et aux risques du portefeuille n'est pas dit

- **gravité** : majeur
- **emplacement** : §3.4.3, exigence `WF-PTF-0020-A` ; §3.4.3.4, `WF-PTF-0080-A` ; §3.4.3.5, `WF-PTF-0090-A`
- **citation** : « Un projet en chiffrage contribue à toute somme pour son montant pondéré par sa probabilité de gain (WF-PRJ-0090), à la seule exception du pipeline brut (WF-PTF-0050) » (WF-PTF-0020) ; « la ventilation par nature de coût du budget de référence agrégé et du reste à engager agrégé, en montant et en pourcentage » (WF-PTF-0080) ; « Le total des provisions identifiées égale la somme des provisions des risques identifiés des projets du périmètre. La matrice compte chaque risque identifié une fois. » (WF-PTF-0090, Vérif)

**Constat.** Le périmètre peut inclure les projets en chiffrage (WF-PTF-0010), et quatre vues
disent ce qu'ils y apportent : la liste substitue le devis courant au budget (WF-PTF-0040), le
plan de charge pondère leur charge (WF-PTF-0060), la performance les exclut (WF-PTF-0070), la
courbe en S pondère leurs courbes (WF-PTF-0100). Deux vues ne disent rien. WF-PTF-0080 ventile
un « budget de référence agrégé » qu'un projet en chiffrage n'a pas : contribue-t-il pour zéro,
ou pour son devis pondéré, comme dans WF-PTF-0040 et WF-PTF-0100 ? WF-PTF-0090 est pire : la
règle de WF-PTF-0020 veut que ses provisions comptent pondérées — « toute somme » —, mais la
Vérif demande que le total « égale la somme des provisions des risques identifiés des projets du
périmètre », sans pondération, classe les risques « par montant de provision » et compte chaque
risque « une fois », ce qu'une pondération ne sait pas faire. Un développeur qui applique
WF-PTF-0020 fait échouer la Vérif de WF-PTF-0090 ; un autre qui suit la Vérif viole WF-PTF-0020.

**Proposition.** Dans WF-PTF-0020, corps : « à la seule exception du pipeline brut (WF-PTF-0050),
qui est précisément la somme non pondérée, et de la vue des risques (WF-PTF-0090), qui compte des
risques et leurs provisions telles qu’elles sont ». Dans WF-PTF-0080, corps, ajouter : « Pour un
projet en chiffrage, lorsqu’il est inclus, son devis courant pondéré par sa probabilité de gain
tient lieu de budget de référence et de reste à engager (WF-PTF-0100). » Dans WF-PTF-0090,
corps, ajouter : « Un projet en chiffrage, lorsqu’il est inclus, apporte ses risques identifiés
et leurs provisions sans pondération ; la réserve et la couverture ne portent que sur les
projets en cours, seuls à avoir une référence. » Vérif de WF-PTF-0080, ajouter : « Une offre à
40 % dont le devis porte 100 de main-d’œuvre ajoute 40 à la main-d’œuvre du budget agrégé
lorsqu’elle est incluse. »

**Statut.** intégré


---

## C-123 — Un rôle de ressource n'a pas de libellé, et la Vérif de WF-REF-0110 interdit d'en donner un à un calendrier

- **gravité** : majeur
- **emplacement** : §3.4.4.2.2, exigences `WF-REF-0090-A`, `WF-REF-0100-A` ; §3.4.4.2.3, `WF-REF-0110-A` ; à rapprocher de `WF-REF-0070-A` et `WF-REF-0030-A`
- **citation** : « Un calendrier se saisit par sept valeurs d’heures, du lundi au dimanche, et aucune autre donnée n’est demandée. » (WF-REF-0110, Vérif) ; « Chaque nœud porte un code unique et un libellé. » (WF-REF-0070)

**Constat.** Le référentiel donne un code et un libellé aux nœuds (WF-REF-0070), un code et un
nom aux natures (WF-REF-0030), un code comptable aux catégories (WF-REF-0040). Le rôle de
ressource, l'objet le plus employé du référentiel — chaque ligne de main-d'œuvre le porte, les
refus le nomment (WF-PLA-0010), l'import de devis le désigne (WF-INTF-0100), le plan de charge
l'affiche —, n'a dans WF-REF-0090 que ses trois rattachements et dans WF-REF-0100 sa capacité :
rien ne dit par quoi on le nomme ni ce qui le rend unique. Le calendrier est dans le cas
inverse : il faut le choisir pour rattacher un rôle (WF-REF-0090), le désigner par défaut
(WF-REF-0120), le lire « partout où il est employé » (WF-REF-0010), et la Vérif de WF-REF-0110
interdit toute donnée autre que les sept valeurs — donc tout libellé. Un développeur qui ajoute
le nom qu'il lui faut fait échouer cette Vérif ; un autre qui la respecte livre des calendriers
qu'on ne peut distinguer que par leurs heures.

**Proposition.** Dans WF-REF-0090, corps, en tête : « Un rôle de ressource porte un code unique
et un libellé. Il est rattaché… » ; Vérif, ajouter : « La création d’un rôle dont le code existe
déjà est refusée. » Dans WF-REF-0110, corps : « Un calendrier porte un libellé unique et donne,
pour chacun des sept jours de la semaine, un nombre d’heures travaillées par le rôle qui
l’emploie. » ; Vérif : « Un calendrier se saisit par un libellé et sept valeurs d’heures, du lundi
au dimanche, et aucune autre donnée n’est demandée ; deux calendriers de même libellé sont
refusés. » Reporter les deux attributs dans le §3.2.2 (paragraphes « Rôles de ressources » et
« Calendriers ») et dans WF-DAT-0090, qui déclare les unicités en base.

**Statut.** intégré


---

## C-124 — Une Vérif qui n'est vraie que pour des valeurs bien choisies

- **gravité** : mineur
- **emplacement** : §3.4.4.3, exigence `WF-REF-0160-A`, Vérif
- **citation** : « Un même risque, rapporté à deux projets de budgets différents, ne tombe pas dans le même niveau de gravité. »

**Constat.** Ce n'est vrai que si les deux assiettes placent la gravité de part et d'autre
d'une borne. Un risque de gravité 10 sur des budgets de 1 000 et de 2 000 fait 1 % et 0,5 %, tous
deux sous une borne à 1 % : même niveau, et la Vérif, prise au mot, échoue sur un système
correct. Le testeur doit choisir ses nombres ; autant les lui donner, comme les autres Vérif du
document le font.

**Proposition.** « Avec des bornes de gravité à 1 %, 5 % et 10 %, un risque de gravité 60 est au
troisième niveau sur un projet de budget 1 000 (6 %) et au deuxième sur un projet de budget
2 000 (3 %). »

**Statut.** intégré


---

## C-125 — Rien ne dit si une révision marquée est lue avec les seuils et bornes de son époque ou ceux d'aujourd'hui

- **gravité** : mineur
- **emplacement** : §3.4.4, exigence `WF-REF-0130-A` ; à rapprocher de `WF-DAT-0040-A` et du §4.4.1 (valeurs du référentiel employées)
- **citation** : « La modification d’un objet du référentiel — libellé, rattachement, capacité, taux — n’affecte aucune révision marquée, qui conserve les valeurs employées au moment de son marquage. »

**Constat.** L'énumération couvre les objets du référentiel, pas ses paramètres : bornes de la
matrice (WF-REF-0160), seuils des indices (WF-REF-0170), délai entre revues (WF-REF-0180). Le
§4.4.1 ne conserve avec une révision que quatre tables — rôle, calendrier, catégorie, taux — et
WF-DAT-0040 conserve les indicateurs, pas leur zone. On en déduit qu'une révision marquée est
lue avec les seuils courants, comme le §3.4.4.2.1 le dit explicitement pour l'organigramme ;
mais on le déduit, et un développeur peut tout aussi bien figer la zone au marquage pour
respecter la lettre de WF-REF-0130. Les deux lectures donnent des historiques d'indices
différents après un changement de seuils.

**Proposition.** Ajouter au corps de WF-REF-0130 : « Les bornes de la matrice de risques, les
seuils d’alerte et le délai maximal entre deux revues ne sont pas conservés par les révisions :
une révision marquée est toujours lue avec leurs valeurs courantes, comme à travers
l’organigramme courant (§3.4.4.2.1) ; ses indicateurs conservés (WF-DAT-0040) ne changent pas,
seule la zone qui les qualifie peut changer. » Vérif, ajouter : « Après abaissement du seuil
d’alerte, la zone de l’indice de coût d’une révision marquée peut changer, sa valeur non. »

**Statut.** intégré


---

## C-126 — « Il se divise en deux familles » : FBS-3 en compte quatre

- **gravité** : mineur
- **emplacement** : §3.4.4 « FBS-3 : Paramètres applicatifs », texte d'introduction
- **citation** : « Il se divise en deux familles : » suivi des deux puces « paramètres de coûts » et « paramètres de ressources »

**Constat.** La figure 9, les §3.4.4.3 et §3.4.4.4, le §3.2.2 (« et les paramètres communs des
risques et des indicateurs (FBS-3.3, FBS-3.4) ») et le glossaire (« Référentiel commun »)
donnent quatre sous-fonctions. L'introduction du bloc en nomme deux, et la règle qui suit —
« rien ne se supprime, tout se désactive » — ne s'applique d'ailleurs qu'à ces deux-là : les
bornes et les seuils sont des valeurs, pas des objets désactivables.

**Proposition.** « Il se divise en quatre : les paramètres de coûts définissent la nature des
dépenses et le coût d’une heure ; les paramètres de ressources définissent les rôles, leur
rattachement dans l’organisation et leur calendrier ; les paramètres de risques fixent les bornes
de la matrice (FBS-3.3) ; les paramètres d’indicateurs fixent les seuils des indices et le rythme
des revues (FBS-3.4). Deux règles valent pour les objets des deux premières familles : rien ne se
supprime, tout se désactive (WF-REF-0010), et une modification du référentiel n’impose jamais de
retoucher un projet (WF-REF-0020, WF-REF-0130). »

**Statut.** intégré avec écart : l’introduction de FBS-3 reste une liste, portée à quatre familles, plutôt qu’un paragraphe unique


---

## C-127 — « Au moins une catégorie de coût active » est satisfait dès l'amorçage, par la catégorie de provision

- **gravité** : mineur
- **emplacement** : §3.3.1, exigence `WF-CYC-0120-A` (citée par le §3.4.4 et par WF-REF-0120) ; §4.5.2, `WF-EXP-0020-A` ; `WF-REF-0030-A`
- **citation** : « au moins une catégorie de coût active ; au moins un rôle de ressource actif » (WF-CYC-0120) ; « jusqu’à ce qu’une catégorie de coût de main-d’œuvre et un rôle de ressource aient été saisis » (WF-EXP-0020, Vérif)

**Constat.** Depuis que WF-REF-0030 fait créer à l'amorçage une nature de type provision et sa
catégorie, le deuxième prérequis de WF-CYC-0120 est toujours vrai, et le refus qui « nomme chaque
prérequis manquant » ne le nommera jamais. Ce que le Motif veut — « Sans catégorie de coût ni
rôle, aucune ligne de devis ne peut être chiffrée » — est une catégorie de main-d'œuvre, et c'est
ce que la Vérif de WF-EXP-0020 teste. Les deux exigences ne disent pas la même condition.

**Proposition.** WF-CYC-0120, corps : « au moins une catégorie de coût active dont la nature
relève de la main-d’œuvre ; au moins un rôle de ressource actif ». Vérif, ajouter : « Sur une
installation neuve, dont la seule catégorie est celle des provisions, la création est refusée en
nommant la catégorie de main-d’œuvre et le rôle manquants. »

**Statut.** intégré


---

## C-128 — Le déplacement d'un nœud n'existe qu'en prose

- **gravité** : mineur
- **emplacement** : §3.4.4.2.1 « FBS-3.2.1 : Arbre d’organisation », texte d'introduction ; exigence `WF-REF-0070-A`
- **citation** : « Un nœud, lui, peut être déplacé dans l’arbre. »

**Constat.** La phrase, issue de C-039, décrit une opération que ni WF-REF-0070 — un arbre,
un code, un libellé — ni WF-REF-0080 ne portent : aucune exigence ne dit qu'un nœud se déplace,
sous quelle condition (un parent actif ? la racine ?), ce qu'il emporte (ses descendants, ses
rôles), ni comment on le vérifie. Le texte en tire pourtant une conséquence précise — le plan de
charge agrégé est relu à travers l'organigramme courant —, qu'aucune Vérif ne couvre.

**Proposition.** Ajouter au corps de WF-REF-0070 : « Un nœud peut être déplacé sous un autre
nœud actif ou à la racine ; ses descendants et les rôles qui y sont rattachés le suivent, et rien
d’autre ne change. » Vérif, ajouter : « Le déplacement d’un nœud sous un autre emporte ses
descendants et ses rôles ; le plan de charge agrégé filtré sur le nœud d’arrivée inclut désormais
ces rôles, et les valeurs par rôle sont inchangées. Le déplacement sous un nœud désactivé est
refusé. »

**Statut.** intégré


---

## C-129 — « À intervalle régulier » : ni valeur ni paramètre

- **gravité** : mineur
- **emplacement** : §3.4.2.1, exigence `WF-ADM-0070-A` ; à rapprocher de `WF-ADM-0170-A` et de PBS-5.3
- **citation** : « par son API d’administration, à la demande et à intervalle régulier »

**Constat.** La lecture périodique des comptes est une tâche planifiée (PBS-5.3 : « à l'heure
convenue ») dont rien ne dit la fréquence : ni une valeur, ni un paramètre, ni qui le règle,
alors que WF-ADM-0170 fait choisir à un utilisateur habilité « une fréquence et une heure » pour
les sauvegardes. C'est le cas de C-071 : un délai que personne ne fixe est un délai que chaque
installation aura différent, et la Vérif — « à la synchronisation suivante » — ne dit pas combien
de temps une personne ajoutée à l'annuaire attend son compte.

**Proposition.** « par son API d’administration, à la demande et selon une périodicité choisie par
un utilisateur habilité, quotidienne par défaut, comme celle des sauvegardes (WF-ADM-0170) ».
Vérif, ajouter : « Une personne ajoutée à l’annuaire a un compte dans Waterfall au terme de la
périodicité choisie, sans intervention. »

**Statut.** intégré


---

## C-130 — « Réalisé », « Couverture des risques » et « Révision courante » manquent au glossaire

- **gravité** : mineur
- **emplacement** : annexe A ; `WF-PTF-0050-A` ; `WF-PTF-0090-A`, `WF-RIS-0050-A`
- **citation** : « le réalisé, somme des coûts réels du périmètre suivi des projets terminés sur la période choisie » (WF-PTF-0050) ; « et la couverture des risques agrégée (WF-RIS-0050) » (WF-PTF-0090)

**Constat.** Le glossaire définit « Carnet » et « Pipeline », les deux autres valeurs de
WF-PTF-0050, mais pas « Réalisé », qui est pourtant le terme le plus exposé à un contresens : un
lecteur y entend le coût réel à ce jour, et le document y met les coûts des projets terminés sur
une période. « Couverture des risques » est employé par WF-RIS-0050, WF-PTF-0090 et le texte du
§3.4.3.5 comme le nom d'une présentation ; le glossaire n'a que « Écart de couverture ».
« Révision courante » fait l'objet de C-114.

**Proposition.**

> **Réalisé.** Désigne la somme des coûts réels du périmètre suivi des projets terminés sur la
> période choisie : ce que l'entreprise a livré (WF-PTF-0050).
>
> **Couverture des risques.** Désigne la mise en regard, pour un projet ou pour le portefeuille,
> de la réserve pour risques de la référence avec la somme des provisions des risques identifiés
> et du coût réestimé des risques survenus ; leur différence est l'écart de couverture
> (WF-RIS-0050).

**Statut.** intégré

---

## C-131 — La Vérif de WF-REV-0010 suppose l'année de référence inchangée

- **gravité** : mineur
- **emplacement** : §3.4.5.1 « Gestion des révisions » — exigence `WF-REV-0010-A` (Vérif) ; à rapprocher de `WF-REV-0060-A`
- **citation** : « Une révision créée à partir d’une révision marquée porte les mêmes tâches, les mêmes lignes et les mêmes valeurs de référentiel. »

**Constat.** WF-REV-0060 fait, à la création d'une révision dont l'année de référence diffère de celle
de la précédente, présenter les taux catégorie par catégorie et accepter ou refuser chaque mise à
jour. Une révision créée en janvier dont l'utilisateur accepte les nouveaux taux ne porte donc pas
« les mêmes valeurs de référentiel ». Le testeur qui applique la Vérif en début d'année échoue, ou
refuse toutes les mises à jour sans que la Vérif le lui dise.

**Proposition.** Vérif de WF-REV-0010 :

> Une révision créée à partir d’une révision marquée porte les mêmes tâches et les mêmes lignes ; à
> année de référence égale, elle porte aussi les mêmes valeurs de référentiel, et sinon celles que la
> mise à jour de WF-REV-0060 n’a pas remplacées.

**Statut.** intégré


---

## C-132 — L'abandon de l'unique révision d'un projet en chiffrage n'a pas d'issue dite

- **gravité** : mineur
- **emplacement** : §3.4.5.1 — exigence `WF-REV-0010-A` ; à rapprocher de §3.3.2 (figure 8, `WF-CYC-0020-A`, `WF-CYC-0050-A`)
- **citation** : « Une révision en cours peut être abandonnée tant qu’elle n’est pas marquée ; le projet revient alors à son état à la dernière révision marquée. »

**Constat.** Pendant le chiffrage, la première révision d'un projet peut être abandonnée alors
qu'aucune révision marquée n'existe : la phrase n'a alors pas d'objet. Le projet se retrouve sans
révision à l'état Chiffrage, état que la figure 8 fait atteindre par « Première révision créée » ;
rien ne dit s'il y reste ou revient à Créé, et WF-CYC-0020 et WF-CYC-0050 ne décrivent que des
progressions. L'état commande des droits (motif de WF-CYC-0010) et les sorties permises (Perdu
depuis Chiffrage seulement) : un développeur choisira l'un ou l'autre.

**Proposition.** Ajouter au corps de WF-REV-0010 :

> Lorsqu’il n’existe aucune révision marquée, l’abandon laisse le projet sans révision ; il reste à
> l’état Chiffrage (WF-CYC-0020), et une nouvelle révision peut être créée.

Vérif, ajouter : « L’abandon de l’unique révision d’un projet en chiffrage le laisse sans révision,
à l’état Chiffrage, et la création d’une révision y est de nouveau proposée. »

**Statut.** intégré


---

## C-133 — La mise à jour des taux n'a lieu qu'à la création d'une révision, et quatre créations se font sans dialogue

- **gravité** : majeur
- **emplacement** : §3.4.5.1 — exigence `WF-REV-0060-A` ; `WF-REV-0050-A` ; `WF-INTF-0090-A` ; `WF-RIS-0020-A` ; `WF-RIS-0060-A` ; §4.3.4 (figures 19 et 20)
- **citation** : « Lorsqu’elle diffère de celle de la révision précédente, Waterfall présente, catégorie par catégorie, le taux conservé et le taux du référentiel pour la nouvelle année ; l’utilisateur accepte ou refuse chaque mise à jour. » (WF-REV-0060) ; « Lorsque le projet ne comporte pas de révision en cours, elle en crée une au préalable. » (WF-REV-0050, WF-RIS-0060)

**Constat.** Quatre exigences créent une révision sans que l'utilisateur l'ait demandée : l'import
(WF-INTF-0090 : « l’import en crée une »), la fusion d'un différentiel (WF-REV-0050), la saisie
d'un risque (WF-RIS-0020 : « la saisie en crée une au préalable ») et la survenance (WF-RIS-0060).
L'import se déroule en deux temps déjà fixés par WF-ARC-0100 et la figure 19, sans place pour un
dialogue catégorie par catégorie ; la fusion crée et marque « dans la même opération », donc la
révision est figée avant qu'aucune mise à jour ait pu être acceptée. Or WF-REV-0060 n'attache la
mise à jour qu'au moment de la création : si ce moment passe sans dialogue, la révision garde ses
taux projetés jusqu'au marquage suivant, et la première révision de l'année — le plus souvent créée
par l'import du reste à engager de la revue de janvier — ne passe jamais aux taux constatés. Un
développeur a deux issues, toutes deux défendables : bloquer l'import ou la fusion sur un dialogue
que le §4 ne prévoit pas, ou ne jamais proposer la mise à jour.

**Proposition.** Dans WF-REV-0060, remplacer la phrase citée par :

> Lorsqu’elle diffère de celle de la révision précédente, Waterfall présente, catégorie par
> catégorie, le taux conservé et le taux du référentiel pour la nouvelle année ; l’utilisateur
> accepte ou refuse chaque mise à jour. Cette présentation est faite à la création lorsque
> l’utilisateur la demande lui-même ; lorsque la révision est créée par un import (WF-INTF-0090), une
> saisie de risque (WF-RIS-0020) ou une survenance (WF-RIS-0060), les taux conservés sont appliqués, et
> la présentation reste proposée depuis la révision en cours tant qu’elle n’est pas marquée. La
> fusion d’un différentiel sur un projet sans révision en cours (WF-REV-0050) chiffre la révision
> qu’elle produit aux taux conservés, projetés ; pour la chiffrer aux taux de la nouvelle année, la
> révision est créée avant la fusion.

Vérif, ajouter : « Une révision créée en 2027 par un import de reste à engager porte les taux de
2026 projetés d’une année ; la mise à jour catégorie par catégorie reste proposée jusqu’à son
marquage, et l’accepter pour une catégorie la rechiffre au taux de 2027. »

**Statut.** intégré


---

## C-134 — La comparaison de deux révisions ne dit pas quel montant elle compare

- **gravité** : mineur
- **emplacement** : §3.4.5.1 — exigence `WF-REV-0080-A` (corps et Vérif)
- **citation** : « ainsi que les écarts de montants par nature de coût et par sous-projet » ; « La comparaison de deux révisions dont l’une a été obtenue par fusion d’un différentiel restitue exactement les tâches et les montants de ce différentiel. »

**Constat.** Une ligne porte deux montants (WF-DEV-0020). Pendant le chiffrage ils sont égaux ;
pendant l'exécution ils diffèrent, et l'exigence ne dit pas lequel est comparé : instruire un
avenant (motif) demande les montants budgétés, comparer deux revues demande les réestimés. La Vérif,
elle, ne nomme pas la seconde révision comparée et suppose qu'aucune autre modification n'a eu
lieu dans la révision en cours que la fusion a marquée : telle quelle, elle échoue dès qu'une
réestimation a précédé la fusion dans la même révision, ce que WF-REV-0050 permet.

**Proposition.** Corps : « ainsi que les écarts de montants budgétés et de montants réestimés, par
nature de coût et par sous-projet ». Vérif :

> La comparaison d’une révision obtenue par fusion d’un différentiel avec la révision marquée qui la
> précède, lorsqu’aucune autre modification n’a été faite entre les deux, restitue exactement les
> tâches et les montants budgétés de ce différentiel, et aucun écart de montant réestimé.

**Statut.** intégré


---

## C-135 — Le taux d'inflation et la probabilité de gain conservés manquent aux attributs d'une révision

- **gravité** : mineur
- **emplacement** : §3.4.5.1 — exigence `WF-REV-0090-A` ; à rapprocher de `WF-REV-0030-A`
- **citation** : « Une révision porte un nom de version, une description facultative, son état — en cours d’élaboration (draft) ou marquée (marked) —, la date de son marquage, son année de référence (WF-REV-0060), et le cas échéant son caractère de révision de référence. »

**Constat.** WF-REV-0030 fait conserver par la révision « son année de référence, le taux
d’inflation et la probabilité de gain du projet ». WF-REV-0090, qui se présente comme la liste de
référence (« évite que chaque vue définisse les siens ») et alimente l'historique de WF-REV-0070,
ne retient que l'année. Le taux et la probabilité conservés n'ont donc aucun écran où se lire,
alors que la Vérif de WF-REV-0030 suppose qu'on constate sur une révision marquée qu'ils n'ont pas
bougé.

**Proposition.** « …, la date de son marquage, son année de référence, le taux d’inflation et la
probabilité de gain qu’elle conserve (WF-REV-0030, WF-REV-0060), et le cas échéant son caractère de
révision de référence. »

**Statut.** intégré


---

## C-136 — Un « refus » pour une transition qui n'est pas une action

- **gravité** : mineur
- **emplacement** : §3.4.5.2 — exigence `WF-PRJ-0010-A` (Vérif) ; à rapprocher de `WF-CYC-0020-A`, `WF-CYC-0030-A`
- **citation** : « Le passage à En cours est refusé tant qu’il n’est pas renseigné. »

**Constat.** Le passage à En cours est une progression automatique : « Elles ne sont jamais
proposées à l’utilisateur comme une action » (WF-CYC-0020). Rien ne peut donc être « refusé », et le
testeur cherche un refus qu'aucun écran ne produit. WF-CYC-0030 dit la même chose dans les bons
termes : « ne fait pas passer le projet à En cours, et la condition manquante est nommée ».

**Proposition.** « Le projet ne passe pas à En cours tant qu’il n’est pas renseigné, et le code
manquant figure parmi les conditions restantes (WF-CYC-0050). »

**Statut.** intégré avec écart : réalisé par la rédaction de C-107 sur la Vérif de WF-PRJ-0010


---

## C-137 — Le filtre par poste ou par lot est promis par le texte et porté par aucune exigence

- **gravité** : mineur
- **emplacement** : §3.4.5.2.1 « Lotissement du projet », texte d'introduction ; §3.2.3 ; `WF-PLA-0080-A` ; `WF-DEV-0050-A`
- **citation** : « filtrer le planning ou le devis sur l’un d’eux revient à filtrer le sous-arbre correspondant : le lotissement sert alors de grille de lecture, par ce seul rattachement » (§3.4.5.2.1) ; « de filtrer sur le sous-arbre d’une récapitulative ou sur les tâches démarrées » (WF-PLA-0080)

**Constat.** Le §3.4.5.2.1 et le §3.2.3 (« de filtrer le planning comme le devis par poste ou par
lot, à travers la tâche rattachée à chacun (WF-PLA-0130) ») promettent un filtre par poste ou par
lot. Aucune exigence ne le porte : WF-PLA-0080 filtre « sur le sous-arbre d’une récapitulative »,
WF-DEV-0050 « sur une nature de coût, un sous-projet ou le sous-arbre d’une récapitulative ». Et
depuis que le rattachement s'ouvre aux feuilles, le filtre sur le sous-arbre d'une récapitulative ne
couvre même pas un lot porté par une feuille. C'est un trou fonctionnel entre le texte et les
exigences.

**Proposition.** WF-PLA-0080, corps : « de filtrer sur le sous-arbre d’une récapitulative, sur le
poste ou le lot porté par une tâche rattachée (WF-PLA-0130) ou sur les tâches démarrées ».
WF-DEV-0050, corps : « de filtrer sur une nature de coût, un sous-projet, le sous-arbre d’une
récapitulative ou le poste ou le lot porté par une tâche rattachée (WF-PLA-0130) ». Vérif de
WF-PLA-0080, ajouter : « Le filtre sur un lot ne laisse voir que la tâche qui le porte, son
sous-arbre et ses parents. »

**Statut.** intégré


---

## C-138 — Lotissement implicite et squelette : trois valeurs par défaut non dites

- **gravité** : mineur
- **emplacement** : §3.4.5.2.1 — exigences `WF-PRJ-0020-A` et `WF-PRJ-0030-A`
- **citation** : « en son absence, le lotissement vaut un poste comprenant un lot sans livrable. Chaque poste, lot et livrable porte un libellé. » (WF-PRJ-0020) ; « une tâche feuille par livrable, et un jalon de fin par lot et par poste » (WF-PRJ-0030)

**Constat.** Trois choses que le développeur fixera seul et que le testeur ne peut pas vérifier : le
libellé du poste et du lot implicites, obligatoire pour tout poste et tout lot et pourtant non
donné ; la durée et le mode des tâches feuilles engendrées — une feuille en mode automatique sans
durée n'a pas de dates, et une durée nulle en ferait un jalon (WF-PLA-0050) ; la place des jalons
de fin dans l'arbre. La Vérif de WF-PRJ-0030 (« les feuilles et les jalons attendus ») n'est
observable qu'avec ces valeurs.

**Proposition.** WF-PRJ-0020 : « en son absence, le lotissement vaut un poste et un lot qui portent
le libellé du projet, sans livrable ». WF-PRJ-0030 : « une tâche feuille par livrable, en mode
automatique et d’une durée d’un jour (WF-PLA-0160), sous la récapitulative de son lot ; un jalon de
fin par lot, sous la récapitulative du lot, et un jalon de fin par poste, sous celle du poste ».

**Statut.** intégré


---

## C-139 — Ce que devient le rattachement quand le lot est supprimé ou déplacé n'est pas dit, et le §4 répond à l'envers

- **gravité** : majeur
- **emplacement** : §3.4.5.2.1 — exigence `WF-PRJ-0030-A` ; `WF-PLA-0130-A` ; §4.4.1 « Suppression » ; `WF-DAT-0080-A` ; `WF-DAT-0090-A`
- **citation** : « ne crée d’autre lien entre le lotissement et le planning que ce rattachement : modifier ensuite le lotissement ne déplace ni ne supprime aucune tâche. » (WF-PRJ-0030) ; « se supprime physiquement tant qu’aucune révision marquée ni aucune ligne de coût ne le référence » (WF-DAT-0080)

**Constat.** Le rattachement est, de l'aveu de WF-PRJ-0030, un lien du planning vers le lotissement.
Que devient-il quand le lot disparaît ou change de poste ? WF-PRJ-0030 dit seulement qu'aucune
tâche n'est déplacée ni supprimée ; son motif pose la question (« ce que devient une tâche dont le
lot a été renommé, déplacé ou supprimé ») et n'y répond pas pour le rattachement. Le §4 tranche, et
à l'envers : WF-DAT-0090 fait de « toute relation du modèle conceptuel » une clé étrangère « en
refus par défaut », donc la suppression d'un lot porté par une tâche de la révision en cours est
rejetée par la base, alors que WF-DAT-0080 dit qu'un lot non référencé par une révision marquée
« se supprime physiquement ». Enfin, si un lot change de poste — ce que le motif de WF-PRJ-0030
envisage —, la règle de sous-arbre de WF-PLA-0130 est violée sans qu'aucune saisie ait été
refusée. Trois comportements sont possibles : refuser, retirer le rattachement, le laisser pendre.

**Proposition.** Ajouter au corps de WF-PLA-0130 :

> La suppression d’un poste ou d’un lot retire le rattachement des tâches de la révision en cours
> qui le portaient ; les révisions marquées le conservent, et le poste ou le lot est alors marqué
> supprimé (WF-DAT-0080). Le déplacement d’un lot sous un autre poste retire de même le rattachement
> de sa tâche lorsqu’elle n’est pas dans le sous-arbre de la tâche de ce poste.

Vérif, ajouter : « La suppression d’un lot porté par une tâche de la révision en cours aboutit ; la
tâche reste et ne porte plus de rattachement ; une révision marquée qui la citait l’affiche
toujours rattachée. » Dans WF-DAT-0090, nommer cette exception au refus par défaut : « la
suppression d’un poste ou d’un lot met à nul le rattachement des tâches de la révision en cours
(WF-PLA-0130) ».

**Statut.** intégré


---

## C-140 — « Charges » pour « lignes » : le rechiffrage exempterait les lignes hors main-d'œuvre

- **gravité** : mineur
- **emplacement** : §3.4.5.2.2 — exigence `WF-PRJ-0040-A` (corps et Vérif) ; à rapprocher de `WF-DEV-0030-A` et de l'annexe A, entrée « Charge »
- **citation** : « pour les charges dont l’année de consommation est postérieure à l’année de référence » ; « les charges dont l’année de consommation suit l’année de référence sont rechiffrées, les autres non »

**Constat.** Le glossaire définit la charge comme « le nombre d'heures de travail d'une ligne de
devis ou de reste à engager de main-d'œuvre ». WF-DEV-0030 applique pourtant l'inflation à toute
ligne, hors main-d'œuvre comprise, et son motif y insiste. Lu avec le glossaire, WF-PRJ-0040
exempte les fournitures du rechiffrage, ce que WF-DEV-0030 interdit.

**Proposition.** Corps : « pour les lignes dont l’année de consommation est postérieure à l’année de
référence (WF-DEV-0030) ». Vérif : « les lignes, de main-d’œuvre ou non, dont l’année de
consommation suit l’année de référence sont rechiffrées, les autres non ».

**Statut.** intégré


---

## C-141 — Rien n'empêche un projet de perdre son dernier chef de projet

- **gravité** : majeur
- **emplacement** : §3.4.5.2.4 — exigence `WF-PRJ-0060-A` ; à rapprocher de `WF-ADM-0110-A`, `WF-ADM-0060-A`, `WF-ADM-0120-A`
- **citation** : « Un projet porte la liste des utilisateurs qui y contribuent, dont son créateur, chacun avec sa qualité : chef de projet ou participant. »

**Constat.** Seuls les chefs de projet marquent, désignent, fusionnent et paramètrent (WF-PRJ-0060,
WF-ADM-0110), et le paramétrage comprend la liste des contributeurs elle-même (FBS-4.2.4). Rien
n'empêche de retirer le dernier chef de projet, de le passer en participant, ni de désactiver son
compte (WF-ADM-0060). Le projet n'a alors plus personne pour inscrire un chef de projet, et aucune
permission — pas même « consulter tous les projets », qui n'ouvre que la consultation — ne permet
d'y remédier autrement qu'en base. WF-ADM-0120 pose la garde équivalente pour la plateforme (dernier
administrateur) ; le projet n'en a pas.

**Proposition.** Ajouter au corps de WF-PRJ-0060 :

> Un projet non terminal compte toujours au moins un chef de projet : le retrait du dernier, ou son
> passage en participant, est refusé. Lorsque le compte du dernier chef de projet est désactivé
> (WF-ADM-0060), un utilisateur portant la permission de modifier FBS-4.2 et celle de consulter tous
> les projets peut y inscrire un chef de projet ; c’est la seule saisie ouverte à un non-contributeur.

Vérif, ajouter : « Le retrait du seul chef de projet d’un projet est refusé, de même que son passage
en participant ; il est accepté dès qu’un second chef de projet est inscrit. »

**Statut.** intégré


---

## C-142 — Aucune date de début de planning : une tâche automatique sans prédécesseur n'a pas d'ancre

- **gravité** : majeur
- **emplacement** : §3.4.5.3 — exigence `WF-PLA-0020-A` ; `WF-PLA-0010-A` (Vérif) ; `WF-PRJ-0080-A` ; `WF-REV-0090-A` ; `WF-INTF-0040-A` ; `WF-INTF-0050-A`
- **citation** : « En mode automatique, ses dates sont calculées à partir de sa durée, de ses liaisons et du calendrier applicable »

**Constat.** Une tâche en mode automatique sans prédécesseur n'a rien d'où partir : ni le projet
(WF-PRJ-0080), ni la révision (WF-REV-0090), ni la structure (WF-REV-0100) ne portent de date de début
de planning, et aucune exigence du document ne dit quand commence la première tâche. MS Project
l'ancre sur la date de début du projet ; sans elle, l'égalité des dates qu'exigent WF-INTF-0050
(« MS Project recalcule pour chaque tâche des dates de début et de fin identiques ») et WF-INTF-0060
n'est pas définie, et la Vérif de WF-PLA-0010 (« commencée un lundi matin ») suppose un ancrage
qu'elle ne nomme pas. Un développeur prendra le jour courant, la date de création, ou la plus
ancienne tâche manuelle ; les trois donnent des plannings différents, et avec le jour courant une
révision relue des années plus tard (WF-REV-0030) changerait de dates.

**Proposition.** Ajouter au corps de WF-PLA-0020 :

> Chaque structure de coûts porte une date de début de planning, saisie, qui vaut par défaut le
> jour de sa création et que la révision conserve (WF-REV-0030). Une tâche en mode automatique sans
> prédécesseur commence à cette date, à la première heure travaillée de son calendrier applicable.
> L’import MS Project la lit dans la date de début du projet du fichier, et l’export l’y écrit
> (WF-INTF-0040, WF-INTF-0050).

Vérif, ajouter : « Une tâche en mode automatique sans prédécesseur commence à la date de début de
planning ; avancer cette date d’une semaine l’avance d’autant, ainsi que ses successeurs
automatiques. » Ajouter la date de début de planning aux attributs d'une structure dans WF-REV-0100.

**Statut.** intégré


---

## C-143 — Une récapitulative en mode manuel : sans sens ici, importable depuis MS Project

- **gravité** : mineur
- **emplacement** : §3.4.5.3 — exigences `WF-PLA-0040-A`, `WF-PLA-0130-A` ; `WF-INTF-0040-A`
- **citation** : « son mode de planification et, en mode manuel, ses dates » (WF-INTF-0040) ; « Les dates et l’état d’une récapitulative ne sont pas saisissables. » (WF-PLA-0040)

**Constat.** WF-PLA-0130 donne un mode de planification à toute tâche ; WF-PLA-0040 fait dériver
dates et durée d'une récapitulative de ses subordonnées, et WF-IHM-0030 les range parmi les valeurs
calculées. Une récapitulative en mode manuel n'a donc pas de sens dans Waterfall. MS Project en
produit pourtant (récapitulative planifiée manuellement, avec ses propres dates), et WF-INTF-0040
dit importer le mode et les dates de toute tâche manuelle. Que fait Waterfall de ces dates : les
garder, contre WF-PLA-0040, ou les écraser, contre WF-INTF-0040 ?

**Proposition.** WF-PLA-0040, ajouter : « Une tâche récapitulative est toujours en mode automatique ;
son mode n’est pas saisissable. » WF-INTF-0040, ajouter : « une récapitulative en mode manuel dans le
fichier est importée en mode automatique, et le compte rendu la signale avec l’écart de dates ».

**Statut.** intégré


---

## C-144 — Les suffixes d'unités renvoient à MS Project et le contredisent

- **gravité** : majeur
- **emplacement** : §3.4.5.3 — exigences `WF-PLA-0030-A` (corps) et `WF-PLA-0160-A` (corps et Vérif)
- **citation** : « L’unité est indiquée par un suffixe selon la convention de Microsoft Project. » ; « suffixes emin, eh, ej, esem et em » ; « une durée saisie « 2 j » vaut seize heures, « 1 sem » quarante heures et « 1 m » cent soixante heures »

**Constat.** WF-PLA-0030 renvoie aux conventions de MS Project ; WF-PLA-0160 énumère ses propres
suffixes pour le temps écoulé et ne nomme pas ceux du temps de travail, qu'on ne devine qu'aux
exemples de la Vérif (j, sem, m). Or dans MS Project, en français comme en anglais, « m » est la
minute — le mois s'écrit « ms » en français, « mo » en anglais — et « em » est l'*elapsed minute*.
Un développeur qui applique la convention annoncée lit « 1 m » comme une minute et fait échouer la
Vérif ; un autre qui suit la Vérif contredit WF-PLA-0030. Reste à dire si les suffixes dépendent de la
langue de l'interface : WF-INTF-0180 fixe les formats d'échange, pas les saisies.

**Proposition.** WF-PLA-0030 : « L’unité est indiquée par un suffixe (WF-PLA-0160). » WF-PLA-0160,
corps :

> Une durée ou un décalage se saisit en minutes, heures, jours, semaines ou mois de travail —
> suffixes min, h, j, sem et m —, et se conserve en temps de travail avec l’unité de sa saisie. […]
> Une durée ou un décalage se saisit aussi en temps écoulé — minutes, heures, jours, semaines ou mois
> civils, suffixes emin, eh, ej, esem et em […]. Les suffixes sont les mêmes quelle que soit la
> langue de l’interface.

Vérif, ajouter : « « 1 m » est lu comme un mois et « 1 min » comme une minute, dans chacune des
langues de l’interface. »

**Statut.** intégré


---

## C-145 — L'exemple des 2 ej fait commencer une tâche un dimanche, hors de tout calendrier

- **gravité** : majeur
- **emplacement** : §3.4.5.3 — exigence `WF-PLA-0160-A` (Vérif) ; à rapprocher de `WF-PLA-0010-A` et `WF-DAT-0100-A`
- **citation** : « Un décalage de 2 ej placé un vendredi soir fait commencer le successeur le dimanche soir. »

**Constat.** Deux jours écoulés après le vendredi 18 h tombent bien le dimanche 18 h. Mais une tâche
ne commence qu'à une heure travaillée de son calendrier applicable — WF-PLA-0010 : « s’y placent heure
après heure » — et WF-DAT-0100 représente un début par « une date sans heure et un nombre d’heures de
travail écoulées ce jour-là » : un dimanche sans heure travaillée n'est pas même représentable. Sur
le calendrier des autres exemples (du lundi au vendredi), le successeur commence le lundi matin, et
c'est ce que MS Project affiche. Un développeur qui fait passer la Vérif à la lettre place une tâche
hors de son calendrier.

**Proposition.**

> Un décalage de 2 ej sur une liaison fin à début dont le prédécesseur finit un vendredi à 18 h
> s’achève le dimanche à 18 h ; le successeur, sur un calendrier du lundi au vendredi, commence le
> lundi à la première heure travaillée. Un décalage de 2 j sur la même liaison le fait commencer le
> mercredi.

**Statut.** intégré


---

## C-146 — Les lignes propres « signalées » : dans quel écran, selon quelle échelle ?

- **gravité** : mineur
- **emplacement** : §3.4.5.3 — exigence `WF-PLA-0040-A` (corps et Vérif) ; `WF-IHM-0070-A`
- **citation** : « Tant que ce reste n’est pas nul, elle reste démarrée et ses lignes propres sont exposées à la réestimation, signalées comme seules lignes ouvertes de la phase » ; « porte un reste à engager de 500 est démarrée et signalée »

**Constat.** Signalée où — grille de reste à engager, Kanban, grille de planning — et comment ?
WF-IHM-0070 impose une échelle commune à tous les signalements et les énumère ; celui-ci n'y figure
pas. C'est le même défaut que C-096 pour un autre signalement : un signalement sans écran nommé est
un signalement que chaque écran inventera.

**Proposition.** Corps : « signalées, dans la grille de reste à engager et dans le Kanban, comme
seules lignes ouvertes de la phase ». Ajouter « lignes propres d’une récapitulative dont toutes les
subordonnées sont terminées (WF-PLA-0040) » à la liste des signalements de WF-IHM-0070.

**Statut.** intégré


---

## C-147 — Un jalon porteur de lignes terminé depuis le Kanban : accepté ou refusé ?

- **gravité** : mineur
- **emplacement** : §3.4.5.3 — exigence `WF-PLA-0050-A` (corps et Vérif) ; `WF-RAE-0030-A`
- **citation** : « Son état passe directement de non démarré à terminé, par le Kanban (WF-RAE-0030) ou, s’il porte des lignes, par la saisie d’un reste à engager nul. » ; « un jalon sans ligne est terminé depuis le Kanban »

**Constat.** La Vérif réserve le Kanban aux jalons sans ligne ; le corps dit « ou », sans exclure
l'un ni l'autre ; WF-RAE-0030 fait passer « un jalon directement à l’état terminé, en saisissant la
date de l’événement » sans distinguer. Un jalon porteur d'un acompte terminé depuis le Kanban : son
reste à engager est-il mis à zéro d'office, contre le « rien ne se termine seul » du motif de
WF-RAE-0030, ou le geste est-il refusé ?

**Proposition.** Corps : « Son état passe directement de non démarré à terminé : par le Kanban
(WF-RAE-0030) s’il ne porte aucune ligne, par la saisie d’un reste à engager nul sur toutes ses
lignes sinon ; le Kanban renvoie alors à cette saisie. » Vérif, ajouter : « La terminaison depuis le
Kanban d’un jalon portant une ligne est refusée en renvoyant à la saisie de son reste à engager. »

**Statut.** intégré


---

## C-148 — Une récapitulative qui perd sa dernière subordonnée ne sait plus ce qu'elle est

- **gravité** : majeur
- **emplacement** : §3.4.5.3 — exigence `WF-PLA-0130-A` (Vérif) ; `WF-PLA-0040-A` ; `WF-PLA-0050-A` ; §3.2.4
- **citation** : « une récapitulative rattachée dont on supprime la dernière subordonnée garde son rattachement » (WF-PLA-0130) ; « une tâche sans sous-tâche est une tâche feuille. Ce n’est donc pas une nature qu’on lui donne, mais une conséquence de sa place dans l’arbre. » (§3.2.4)

**Constat.** Une récapitulative n'a ni durée, ni dates, ni état propres (WF-PLA-0040, WF-IHM-0030).
Privée de sa dernière subordonnée, elle est une feuille (§3.2.4), qui doit porter une durée et un
état. Rien ne dit lesquels. Si sa durée tombe à zéro, elle devient un jalon (WF-PLA-0050), et « une
tâche de durée nulle ne peut recevoir de sous-tâche » : la phase vidée ne peut plus être regarnie.
Si elle garde une durée, laquelle — celle qu'elle calculait, celle de ses dates sur son
calendrier ? Et que devient l'état démarré qu'elle tenait de sa subordonnée disparue ? Le cas est
courant à la reprise d'un planning importé, et la Vérif citée le suppose possible.

**Proposition.** Ajouter au corps de WF-PLA-0040 :

> Une récapitulative qui perd sa dernière subordonnée devient une tâche feuille en mode
> automatique : elle prend pour durée celle qu’elle calculait, conserve son état, ses lignes propres
> et son rattachement, et ses dates sont recalculées (WF-PLA-0020). Si cette durée est nulle, elle
> devient un jalon.

Vérif, ajouter : « La suppression de la seule subordonnée d’une récapitulative de dix jours laisse
une tâche feuille de dix jours, à laquelle une sous-tâche peut de nouveau être ajoutée. »

**Statut.** intégré


---

## C-149 — Le rattachement n'a pas de périmètre : structures, fusion, survenance, jalons

- **gravité** : majeur
- **emplacement** : §3.4.5.3 — exigence `WF-PLA-0130-A` ; `WF-PRJ-0030-A` ; `WF-REV-0050-A` ; `WF-RIS-0060-A` ; `WF-REV-0100-A` ; `WF-DEV-0060-A`
- **citation** : « et un poste ou un lot n’est porté que par une tâche à la fois » (WF-PLA-0130) ; « La génération n’est proposée que sur une structure sans tâche » (WF-PRJ-0030) ; « les tâches et les lignes ajoutées y sont créées, les tâches modifiées prennent leurs nouvelles valeurs, les tâches devenues inutiles en sont retirées » (WF-REV-0050)

**Constat.** Une révision porte plusieurs structures (WF-REV-0100). L'unicité « une tâche à la
fois » ne dit pas si elle vaut dans la structure principale, dans chaque structure, ou dans toute la
révision. Le squelette est « proposé sur une structure sans tâche » : le devis propre d'un risque
qui vient d'être déclaré en est une, et le squelette y poserait des rattachements. Un différentiel
ajoute et modifie des tâches ; à la fusion (WF-REV-0050) comme à la survenance (WF-RIS-0060), une
tâche rattachée au lot 2 rejoint une structure principale qui a déjà la sienne, ou une tâche
« modifiée » change de place et sort du sous-arbre de son poste : le refus de WF-PLA-0130 n'a pas
d'issue dite pour une fusion, qui n'a pas de compte rendu. Enfin « récapitulative ou feuille » laisse
le jalon incertain, que WF-PLA-0080 distingue des feuilles. Les totaux par poste de WF-DEV-0060 et
le filtre de C-137 dépendent de ces réponses. C-099 ne couvre que le squelette et le vocabulaire.

**Proposition.** Dans WF-PLA-0130, remplacer la phrase citée et son contexte par :

> Le rattachement n’existe que dans la structure principale : un poste ou un lot n’y est porté que
> par une tâche à la fois, récapitulative, feuille ou jalon. Les structures différentielles et les
> devis propres des risques n’en portent pas, et le squelette (WF-PRJ-0030) ne s’engendre que sur la
> structure principale. Une tâche fusionnée (WF-REV-0050, WF-RIS-0060) n’en porte pas ; une fusion
> qui déplacerait la tâche d’un lot hors du sous-arbre de la tâche de son poste est refusée en
> nommant la tâche.

Vérif, ajouter : « La génération du squelette n’est pas proposée sur le devis propre d’un risque. La
fusion d’un différentiel qui déplacerait la tâche d’un lot hors du sous-arbre de la tâche de son poste
est refusée en nommant la tâche. »

**Statut.** intégré


---

## C-150 — L'import MS Project ne dit pas ce qu'il fait d'un déplacement refusé par WF-PLA-0130 ni d'une tâche rattachée supprimée

- **gravité** : majeur
- **emplacement** : §3.4.5.3 — exigence `WF-PLA-0130-A` ; §3.1.4 — `WF-INTF-0040-A` ; `WF-PLA-0070-A` ; `WF-PLA-0150-A`
- **citation** : « Le déplacement de la tâche d’un lot hors du sous-arbre de la tâche de son poste est refusé. » (WF-PLA-0130) ; « sa position dans l’arbre » ; « met à jour l’objet existant sans toucher à sa lignée, à ses lignes de devis ni à son état » ; « une tâche existante absente du fichier est supprimée selon WF-PLA-0070, une tâche démarrée ou terminée étant conservée et signalée » (WF-INTF-0040)

**Constat.** L'import lit la position dans l'arbre et met à jour la tâche existante : un planning
retravaillé dans MS Project peut déplacer la tâche d'un lot hors du sous-arbre de son poste.
WF-PLA-0130 refuse « un déplacement » ; appliqué à un import, cela veut-il dire le rejet du fichier
entier, comme pour l'horizon (WF-PLA-0150 : « rejeté au compte rendu »), le rejet de la seule tâche,
ou le retrait du rattachement ? WF-INTF-0040 ne cite pas ce motif parmi ce que le compte rendu
signale. De même, une tâche non démarrée rattachée à un poste et absente du fichier est supprimée :
le poste perd sa tâche, son total de WF-DEV-0060 disparaît, et rien ne le dit à l'utilisateur. Enfin
le rattachement n'est pas dans la liste de ce que la mise à jour conserve — lignée, lignes, état —
alors que l'import ne le transporte pas ; il faut le dire pour qu'il survive à l'aller-retour de
WF-INTF-0060.

**Proposition.** WF-INTF-0040, corps, après « sans toucher à sa lignée, à ses lignes de devis ni à son
état » : « ni à son rattachement au lotissement (WF-PLA-0130) ». Puis ajouter :

> Un fichier qui déplacerait la tâche d’un lot hors du sous-arbre de la tâche de son poste est
> rejeté au compte rendu, qui nomme les deux tâches, comme un planning qui dépasse l’horizon
> (WF-PLA-0150). La suppression d’une tâche rattachée est appliquée, et le compte rendu nomme le
> poste ou le lot qui perd sa tâche.

Vérif de WF-INTF-0040, ajouter : « Un fichier qui place la tâche d’un lot hors du sous-arbre de la
tâche de son poste est rejeté et le compte rendu nomme les deux tâches ; un fichier dont une tâche
rattachée a disparu est appliqué et le compte rendu nomme le lot qu’elle portait ; une tâche
rattachée réimportée conserve son rattachement. »

**Statut.** intégré


---

## C-151 — La marge et la criticité d'une récapitulative ne sont pas définies

- **gravité** : mineur
- **emplacement** : §3.4.5.3.3 — exigence `WF-PLA-0100-A` ; `WF-PLA-0080-A` ; `WF-QUA-0080-A`
- **citation** : « Waterfall calcule, pour chaque tâche en mode automatique, ses dates au plus tôt et au plus tard, et la marge totale qui les sépare. »

**Constat.** Une récapitulative est une tâche en mode automatique dont les dates dérivent de ses
subordonnées (WF-PLA-0040), et WF-PLA-0080 affiche « sa marge totale » pour chaque ligne de la grille.
Rien ne dit comment se calculent la marge et la criticité d'une récapitulative — la plus petite de
ses subordonnées, un calcul sur ses propres dates, ou rien — et le corpus de WF-QUA-0080 ne compare
que les dates. Deux développeurs, deux grilles.

**Proposition.** Ajouter au corps de WF-PLA-0100 : « Une tâche récapitulative porte la plus petite
marge totale de ses subordonnées en mode automatique, et appartient au chemin critique dès que l’une
d’elles y appartient ; une récapitulative dont toutes les subordonnées sont en mode manuel ne porte
pas de marge. » Vérif, ajouter : « Une récapitulative dont une subordonnée est critique est critique
et affiche une marge nulle. »

**Statut.** intégré


---

## C-152 — « Tenir sur une page A4 » n'est pas une condition observable

- **gravité** : mineur
- **emplacement** : §3.4.5.3.5 — exigence `WF-PLA-0120-A` (corps)
- **citation** : « de manière à tenir sur une page A4. Aucune pagination ni réduction automatique n’est appliquée »

**Constat.** Le corps promet de tenir sur une page A4, le motif admet le contraire (« Si l’image
déborde malgré tout ») et la Vérif ne teste pas le format. À quel niveau, pour combien de tâches ?
La phrase n'est pas vérifiable ; la disposition — premier niveau horizontal, suivants verticaux —
l'est, et c'est elle qui compte.

**Proposition.** Corps : « Sa mise en page dispose le premier niveau horizontalement et les niveaux
suivants verticalement sous leur parent, disposition pensée pour l’impression sur une page A4 en
portrait. Aucune pagination ni réduction automatique n’est appliquée : l’image a la taille que son
contenu exige, et c’est le niveau de profondeur qui règle l’encombrement. » Vérif, ajouter :
« L’export d’une arborescence trop large pour une page produit une image plus large que la page, sans
réduction. »

**Statut.** intégré


---

## C-153 — « Cent quatre-vingts révisions au plus » est une hypothèse, pas une borne

- **gravité** : mineur
- **emplacement** : §3.4.5.3 — exigence `WF-PLA-0150-A` (Motif) ; §4.4.2, second paragraphe
- **citation** : « cent quatre-vingts révisions marquées au plus par projet » (WF-PLA-0150) ; « cent quatre-vingts révisions par projet au plus » (§4.4.2)

**Constat.** Quinze ans × douze revues = cent quatre-vingts : le calcul est juste sous l'hypothèse
d'une revue mensuelle (§4.6.2, tableau 13). Mais aucune exigence ne borne la cadence : WF-REF-0180
fixe un délai maximal entre deux revues, pas un délai minimal ; rien n'interdit de marquer deux fois
dans le mois, et les révisions du chiffrage ne sont pas comptées. « Au plus » est faux ; c'est un
ordre de grandeur, que le §4.4.2 réemploie comme borne de dimensionnement.

**Proposition.** Motif de WF-PLA-0150 : « La borne donne aussi aux volumes de la plateforme un ordre
de grandeur connu : cent quatre-vingts révisions marquées par projet pour une revue mensuelle sur
quinze ans (§4.6.2). » §4.4.2 : « cent quatre-vingts révisions par projet pour une revue mensuelle ».

**Statut.** intégré

---

## C-154 — Rien ne dit si les montants et leurs agrégats sont à l'année de référence ou corrigés de l'inflation

- **gravité** : majeur
- **emplacement** : §3.4.5.4, `WF-DEV-0020-A` ; §3.4.5.4.3, `WF-DEV-0030-A` ; §3.4.5.4.2, `WF-DEV-0050-A` ; §3.4.5.5, `WF-RAE-0010-A` ; annexe A, entrées « Budget de référence », « Montant budgété », « Montant réestimé »
- **citation** : « le montant budgété depuis les grandeurs de la ligne dans la révision de référence, le montant réestimé depuis ses grandeurs courantes » (WF-DEV-0020) ; « Dans les deux cas, ce montant est ensuite projeté sur l’année de consommation de la ligne par application composée du taux d’inflation du projet » (WF-DEV-0030) ; « son montant réestimé à l’année de référence et corrigé de l’inflation (WF-DEV-0040) » (WF-DEV-0050) ; « du montant budgété de ses lignes, projeté sur son année de consommation courante, si elle n’est pas démarrée » (WF-RAE-0010)

**Constat.** Une ligne a deux valeurs possibles : son montant aux taux de l'année de référence, et ce montant projeté par l'inflation sur son année de consommation. Le document ne dit jamais laquelle des deux est « le montant budgété » et « le montant réestimé », et ses passages tirent dans les deux sens. WF-DEV-0020 calcule les deux montants « depuis les grandeurs » — charge, quantité, débours — qui ne comprennent pas les dates, et sa Vérif donne « 80 fois le taux » : c'est le montant de base. WF-DEV-0030 dit que « ce montant est ensuite projeté », et le Motif de WF-REV-0030 que « Le taux d’inflation entre dans le montant de chaque ligne » : c'est le montant projeté. WF-DEV-0050 affiche « son montant réestimé à l'année de référence et corrigé de l'inflation », ce qui se lit aussi bien comme une colonne que comme deux. WF-RAE-0010 projette le « montant budgété » d'une tâche non démarrée « sur son année de consommation courante » : si le montant budgété est déjà projeté sur l'année de consommation de la référence, un développeur qui applique cette phrase à la lettre compose l'inflation deux fois ; s'il ne l'est pas, le reste à engager mélange des tâches démarrées à l'année de référence et des tâches non démarrées projetées. Tout ce qui s'agrège en dépend : le budget de référence, la valeur planifiée, la valeur acquise — comparées à un coût réel qui est, lui, en euros de l'année où il est payé —, le reste à engager et les trois projections. Deux développeurs produiront deux indices de coût différents, et aucune Vérif du document ne les départagera.

**Proposition.** Trancher dans WF-DEV-0020, corps, après « les deux montants sont calculés » :

> Les deux montants sont exprimés inflation comprise, à l'année de consommation de la ligne (WF-DEV-0030, WF-DEV-0040) : c'est à ce titre qu'ils entrent au budget de référence, au reste à engager, à la valeur planifiée et à la valeur acquise. Le montant aux taux de l'année de référence, avant inflation, est une valeur de lecture (WF-DEV-0050).

Dans WF-DEV-0050, corps : « son montant réestimé aux taux de l'année de référence et, dans une colonne distincte, ce montant corrigé de l'inflation (WF-DEV-0040) ». Dans WF-RAE-0010, corps : « du montant budgété de ses lignes, reporté de l'année de consommation que lui donnait la référence sur son année de consommation courante, si elle n'est pas démarrée ». Au glossaire, ajouter à « Budget de référence » et à « Montant budgété » : « inflation comprise, à l'année de consommation des lignes ». Si l'auteur choisit au contraire des montants à l'année de référence, c'est WF-DEV-0030 (« ce montant est ensuite projeté »), le Motif de WF-REV-0030 et le Motif de WF-DEV-0030 (« une fourniture achetée dans trois ans coûtera plus cher ») qu'il faut reprendre, et dire alors comment le coût réel, qui est en euros courants, se compare à un budget en euros de l'année de référence.

**Statut.** intégré avec écart : une rédaction unique de WF-RAE-0010 concilie C-095 et C-154 ; l’alternative des montants à l’année de référence, signalée en commentaire, n’a pas été retenue


---

## C-155 — Le reste à engager est étalé sur toute la durée de la tâche, dates passées comprises

- **gravité** : majeur
- **emplacement** : §3.4.5.8.7, `WF-IND-0100-A` ; §3.4.5.4.4, `WF-DEV-0070-A`
- **citation** : « et, au-delà, la projection du chef de projet, le reste à engager étant étalé sur les dates de la révision courante » (WF-IND-0100) ; « la somme des décaissements à venir égale le reste à engager » (WF-IND-0100, Vérif) ; « La charge d’une ligne est répartie sur la durée de la tâche qui la porte au prorata des heures travaillées du calendrier de son rôle. » (WF-DEV-0070)

**Constat.** Une tâche démarrée a une date de début passée. Son reste à engager, « étalé sur les dates de la révision courante » ou « répartie sur la durée de la tâche », tombe pour partie avant la date de calcul : cette part n'est ni dans le coût réel ni dans la projection tracée « au-delà », et la Vérif « la somme des décaissements à venir égale le reste à engager » échoue dès qu'une tâche est à moitié faite. Le plan de charge sur la base du reste à engager place de même des heures restantes dans des mois écoulés, que personne ne pourra plus staffer, et c'est cette base que le plan de charge agrégé consolide (WF-PTF-0060). Le cas de la tâche démarrée dont la fin est dépassée — que WF-RAE-0040 signale — n'a aucune date sur laquelle s'étaler. Rien ne dit non plus la règle d'étalement de WF-IND-0100 : linéaire, ou au prorata des heures comme WF-DEV-0040 et WF-DEV-0080.

**Proposition.** WF-IND-0100, corps : « et, au-delà, la projection du chef de projet : le reste à engager de chaque ligne est étalé, au prorata des heures travaillées (WF-DEV-0040), sur la part de la durée de sa tâche postérieure à la date de calcul, et porté entier à la date de calcul lorsque la fin de la tâche est dépassée (WF-RAE-0040). » WF-DEV-0070, corps, après la phrase citée : « Sur la base du reste à engager, la charge restante d'une ligne d'une tâche démarrée est répartie sur la seule part de la durée de la tâche postérieure au jour courant, et portée au mois courant lorsque la fin de la tâche est dépassée. » Vérif de WF-DEV-0070, ajouter : « Une tâche démarrée de quatre mois, à mi-parcours, dont une ligne porte un reste de 80 heures, présente 40 heures sur chacun des deux mois restants et rien sur les mois écoulés. »

**Statut.** intégré


---

## C-156 — La Vérif de WF-DEV-0070 ne propose que la révision en cours là où une révision marquée existe

- **gravité** : mineur
- **emplacement** : §3.4.5.4.4, `WF-DEV-0070-A` (Vérif)
- **citation** : « Les trois bases sont proposées ; sur un projet sans révision de référence, seule la révision en cours l’est. »

**Constat.** Le corps offre trois bases : la révision de référence, « une révision marquée », la révision en cours. Un projet en chiffrage n'a pas de référence mais a des révisions marquées dès sa première offre (WF-REV-0020, WF-DAT-0040) ; la base « une révision marquée » y est possible, et la Vérif dit qu'elle ne l'est pas. Un testeur qui suit la Vérif refuse une base que le corps accorde.

**Proposition.** « Les trois bases sont proposées ; sur un projet sans révision de référence, la base de la référence est absente, et sur un projet sans aucune révision marquée, seule la révision en cours est proposée. »

**Statut.** intégré


---

## C-157 — L'écart « avec le budget de référence » compare un reste à un total ; la ventilation par sous-projet compare autre chose

- **gravité** : majeur
- **emplacement** : §3.4.5.5.1, `WF-RAE-0020-A`
- **citation** : « ainsi que ses écarts avec le budget de référence et avec le reste à engager de la révision marquée précédente » ; « Pour chaque sous-projet, il présente l’écart entre le budget du sous-projet et la somme de son coût réel et de son reste à engager. »

**Constat.** Au niveau du projet, l'écart est entre le reste à engager et le budget de référence ; par sous-projet, il est entre le budget et la somme du coût réel et du reste à engager. Ce ne sont pas les mêmes grandeurs : le reste à engager décroît à mesure que le projet se fait, le budget non, et leur différence ne mesure pas un dépassement mais l'avancement. Le Motif veut pourtant que « L’écart avec la référence dit où en est le projet par rapport à son engagement », ce qui est la seconde définition — celle de la projection du chef de projet (WF-IND-0050). Un développeur qui implémente la première affiche au total un écart que la somme des sous-projets ne retrouve pas, alors que WF-RAE-0020 exige que « les totaux par sous-projet s'additionnent au total du projet ». Le texte ne dit pas non plus ce que devient cet écart sur un projet sans révision de référence, alors qu'il le dit pour l'écart avec la revue précédente.

**Proposition.** Corps : « ainsi que deux écarts, signés : entre la somme de son coût réel et de son reste à engager — la projection du chef de projet (WF-IND-0050) — et le budget de référence ; et entre son reste à engager et celui de la révision marquée précédente. Pour chaque sous-projet, il présente le premier de ces écarts, entre le budget du sous-projet et la somme de son coût réel et de son reste à engager. » Vérif : « Sur un projet sans revue précédente, l'écart correspondant est absent plutôt que nul ; sur un projet sans révision de référence, l'écart au budget l'est aussi. L'écart au budget du projet égale la somme des écarts de ses sous-projets, ensemble hors sous-projet compris. »

**Statut.** intégré avec écart : « et la couverture des risques (WF-RIS-0050) » est conservé dans l’énumération de WF-RAE-0020


---

## C-158 — Un jalon rouvert passe à un état qu'il n'a pas

- **gravité** : mineur
- **emplacement** : §3.4.5.5.2, `WF-RAE-0030-A` ; à rapprocher de `WF-PLA-0050-A`
- **citation** : « permet de faire passer une tâche à l’état démarré, y compris une tâche terminée que l’on rouvre » (WF-RAE-0030) ; « Son état passe directement de non démarré à terminé » (WF-PLA-0050)

**Constat.** Un jalon est une tâche ; WF-RAE-0030 permet donc de rouvrir un jalon terminé, et le rouvrir le met « à l'état démarré », état qu'un jalon n'a pas selon WF-PLA-0050. Le même WF-RAE-0030 interdit de ramener une tâche à « non démarrée ». Un jalon terminé par erreur et non annulé dans le délai de WF-IHM-0110 n'a donc aucune issue définie, et un développeur choisira entre un jalon « démarré », qui n'existe pas, et un refus que rien n'énonce.

**Proposition.** Corps : « y compris une tâche terminée que l'on rouvre ; un jalon terminé que l'on rouvre redevient non démarré, seul cas où une tâche revient à cet état, et sa date de terminaison est effacée ». Et remplacer « Aucun geste ne ramène une tâche à l'état non démarré » par « Aucun geste ne ramène une tâche autre qu'un jalon à l'état non démarré ». Vérif, ajouter : « Un jalon terminé que l'on rouvre est non démarré et ne contribue plus à la valeur acquise. »

**Statut.** intégré avec écart : la clause du jalon rouvert est ajoutée après « (WF-PLA-0130) », hors de l’énumération


---

## C-159 — La préférence distingue des lignes ici, des tâches là

- **gravité** : mineur
- **emplacement** : §3.4.5.5.3, `WF-RAE-0040-A` ; §3.4.2.1, `WF-ADM-0040-A`
- **citation** : « Une préférence d’affichage permet de distinguer visuellement les lignes dont le montant budgété est nul (WF-ADM-0040). » (WF-RAE-0040) ; « Une préférence d’affichage permet de distinguer visuellement les tâches ajoutées après la révision de référence » (WF-ADM-0040)

**Constat.** WF-RAE-0040 renvoie à WF-ADM-0040 pour une préférence qui porte sur les lignes à montant budgété nul ; WF-ADM-0040 décrit une préférence qui porte sur les tâches ajoutées après la référence. Une ligne ajoutée à une tâche de la référence a un montant budgété nul sans que sa tâche soit « ajoutée » : les deux préférences n'ont pas le même périmètre, et le renvoi laisse croire qu'elles sont une.

**Proposition.** Dans WF-ADM-0040 : « Une préférence d'affichage permet de distinguer visuellement les tâches ajoutées après la révision de référence et les lignes dont le montant budgété est nul (WF-RAE-0040). »

**Statut.** intégré


---

## C-160 — La Vérif de WF-RIS-0030 dit qu'un devis propre modifié ne change aucun indicateur ; il change le reste à engager

- **gravité** : majeur
- **emplacement** : §3.4.5.6, `WF-RIS-0030-A` (Vérif)
- **citation** : « La modification du devis propre d’un risque identifié ne change ni le budget de référence ni les indicateurs du projet. »

**Constat.** La gravité d'un risque « est le total de sa structure propre », et sa provision « suivent toute modification de la structure propre » (WF-RIS-0010) ; la provision « pèse sur le devis et sur le reste à engager dès l'identification » (§3.4.5.6), et WF-RAE-0010 compte « des lignes de provision des risques identifiés ». Modifier le devis propre d'un risque identifié change donc le reste à engager, et avec lui l'avancement financier (WF-IND-0040), la projection du chef de projet (WF-IND-0050), la couverture des risques (WF-RIS-0050) et la courbe en S (WF-IND-0100), qui sont des indicateurs du projet. La Vérif, prise à la lettre, échoue sur une implémentation correcte ; un développeur qui veut la faire passer sort les provisions du reste à engager, contre WF-RAE-0010.

**Proposition.** « La modification du devis propre d'un risque identifié ne change ni le budget de référence, ni la valeur planifiée, ni la valeur acquise, ni les indices de coût et de délai ; elle change la provision, donc le reste à engager, l'avancement financier et la projection du chef de projet (WF-RAE-0010). »

**Statut.** intégré


---

## C-161 — Le coût d'un risque survenu est un montant réestimé, donc nul quand ses tâches sont terminées

- **gravité** : majeur
- **emplacement** : §3.4.5.6.2, `WF-RIS-0050-A` ; annexe A, entrée « Écart de couverture » ; §3.4.3.5, `WF-PTF-0090-A`
- **citation** : « face à la somme des provisions des risques identifiés dans la révision courante et du montant réestimé des lignes issues des risques survenus. La différence, signée, est l’écart de couverture. »

**Constat.** Le montant réestimé d'une ligne est son reste à engager : « La saisie d’un reste à engager nul pour toutes les lignes d’une tâche la fait passer à l’état terminé » (WF-RAE-0040), et WF-RAE-0010 compte une tâche terminée pour zéro. Les lignes fusionnées d'un risque survenu suivent ce sort — « ses tâches deviennent du travail comme un autre, qui se planifie, se réestime et se termine » (Motif de WF-RIS-0060). Leur montant réestimé décroît donc à mesure que le travail se fait, et vaut zéro quand il est fait. Le « coût des risques survenus » de la couverture retombe alors à zéro, et l'écart de couverture remonte à la réserve entière : en fin de projet, la couverture dit toujours que les risques n'ont rien coûté. C'est l'inverse du Motif, qui veut « rend l’écart mesurable », et de la santé du pilotage, qui présente « la réserve de référence, face aux provisions restantes et au coût des risques survenus » (WF-PTF-0090). L'exemple de la Vérif (coût des survenus 250) n'est juste qu'au jour de la survenance.

**Proposition.** Figer le coût à la survenance, comme la réserve l'est à la référence. WF-RIS-0010, corps, ajouter : « Un risque survenu conserve son coût à la survenance : le total de son devis propre au moment où il est déclaré survenu (WF-RIS-0060). » WF-RIS-0050, corps : « face à la somme des provisions des risques identifiés dans la révision courante et du coût à la survenance des risques survenus (WF-RIS-0010). La différence, signée, est l'écart de couverture. » Glossaire, « Écart de couverture » : remplacer « du montant réestimé des lignes issues des risques survenus » par « du coût à la survenance des risques survenus ». Vérif de WF-RIS-0050, ajouter : « La terminaison des tâches issues d'un risque survenu ne change ni le coût des survenus ni l'écart de couverture. » Si l'auteur préfère un coût qui suit les réestimations ultérieures, il faut alors conserver, par ligne issue d'un risque, le dernier montant réestimé non nul, et le dire dans WF-DEV-0020.

**Statut.** intégré avec écart : le coût figé à la survenance est retenu ; l’alternative du dernier montant réestimé non nul, signalée en commentaire, n’a pas été retenue


---

## C-162 — La suite de scénarios de WF-RIS-0050 ne dit pas qu'elle repart de zéro, et l'écart de −30 est faux dans la continuité

- **gravité** : majeur
- **emplacement** : §3.4.5.6.2, `WF-RIS-0050-A` (Vérif)
- **citation** : « Un second risque de provision 40, écarté, fait passer les provisions restantes de 40 à 0 sans toucher le budget de référence ; un risque identifié après la référence, de provision 30, porte les provisions restantes à 30 et l’écart de couverture à −30. »

**Constat.** La Vérif enchaîne trois phrases qui se lisent comme un seul scénario : projet à 1 000, risque de 200 à 30 % survenu et réévalué à 250 (écart − 190), puis un second risque, puis un troisième. Dans cette continuité, le dernier chiffre est faux : avec une réserve de 60 et un coût des survenus de 250, un risque identifié après la référence de provision 30 donne un écart de 60 − (30 + 250) = − 220, non − 30. Le − 30 n'est juste que sur un projet dont la réserve est nulle et qui n'a aucun risque survenu, ce que rien ne dit. Le deuxième scénario est lui aussi indéterminé : si le second risque était dans la référence, la réserve vaut 100 et non 60, et l'écart après son écart passe de − 190 à − 150 ; s'il a été identifié après, l'écart passe de − 230 à − 190. Aucun de ces deux nombres n'est donné. Un testeur ne peut pas écrire le cas de test sans deviner les hypothèses.

**Proposition.** « Sur un projet chiffré à 1 000 portant un risque de gravité 200 à 30 %, le devis totalise 1 060, le budget de référence 1 000 et la réserve 60. Après survenance de ce risque, réévalué à 250, le budget de référence vaut toujours 1 000, les provisions restantes 0, le coût des survenus 250, et l'écart de couverture −190. Sur le même projet, un second risque de provision 40 présent dans la référence porte la réserve à 100 ; l'écarter fait passer les provisions restantes de 40 à 0 sans toucher le budget de référence, et l'écart de couverture de −190 à −150. Sur un projet dont la réserve est nulle et sans risque survenu, un risque identifié après la référence, de provision 30, porte les provisions restantes à 30 et l'écart de couverture à −30. »

**Statut.** intégré


---

## C-163 — La Vérif de WF-CRE-0020 rejette une forme d'OTP que le corps ne mentionne pas

- **gravité** : mineur
- **emplacement** : §3.4.5.7, `WF-CRE-0020-A`
- **citation** : « Une ligne dont l’élément d’OTP ne respecte pas la forme attendue est signalée au compte rendu et n’est pas importée. » (Vérif) ; « Le projet et le sous-projet d’une ligne de coût sont déduits de son élément d’OTP, de la forme préfixe.code projet/code sous-projet. » (corps)

**Constat.** Le corps traite trois cas — autre projet, sans sous-projet, sous-projet inconnu — et aucun n'est celui d'un élément d'OTP qui n'a pas la forme attendue. La Vérif le teste pourtant, comme un rejet. Un développeur qui lit le corps peut aussi bien imputer une telle ligne « au seul projet » (le cas « sans partie sous-projet ») que la rejeter.

**Proposition.** Corps, après la première phrase : « Une ligne dont l'élément d'OTP n'a pas cette forme est rejetée et signalée au compte rendu, comme une ligne d'un autre projet. »

**Statut.** intégré


---

## C-164 — « Leur somme est cohérente » n'est pas une condition observable

- **gravité** : mineur
- **emplacement** : §3.4.5.7, `WF-CRE-0040-A` (Vérif)
- **citation** : « Les trois totaux sont présents et leur somme est cohérente. »

**Constat.** Trois totaux n'ont pas de somme attendue ; ce que le corps pose, c'est que le total général est la somme des deux autres. « Cohérente » ne dit pas quelle égalité vérifier, et c'est la seule relation testable de l'exigence.

**Proposition.** « Les trois totaux sont présents, et le total général égale la somme du total du périmètre suivi et du total exclu. Un filtre par sous-projet ou par période s'applique aux trois (WF-IHM-0130). »

**Statut.** intégré


---

## C-165 — Un projet sans révision en cours n'a pas d'indicateurs au jour courant

- **gravité** : majeur
- **emplacement** : §3.4.5.8, `WF-IND-0010-A` ; §3.4.5.8.5, `WF-IND-0130-A` ; à rapprocher de `WF-PTF-0010-A`
- **citation** : « Les indicateurs d’une révision marquée se calculent à sa date de marquage, et ceux de la révision en cours au jour courant. » (WF-IND-0010) ; « et le dernier point au jour courant pour la révision en cours » (WF-IND-0130)

**Constat.** Un projet n'a pas toujours de révision en cours : le marquage ne crée pas la suivante (WF-REV-0010, WF-DAT-0010), la fusion d'un avenant n'en laisse aucune (« Après fusion, le projet ne comporte plus de révision en cours », WF-REV-0050), et WF-RIS-0020 comme WF-RIS-0060 prévoient le cas (« lorsque le projet n'en comporte pas »). Entre deux revues, c'est même l'état normal d'un projet dont la revue est close. Pour un tel projet, le texte ne définit que les indicateurs conservés des révisions marquées, invariables ; rien ne dit ce que l'écran d'indicateurs, le dernier point de WF-IND-0130 ou le portefeuille « au jour courant » (WF-PTF-0010 : « chaque projet contribue par sa révision en cours ») présentent. Deux lectures : les valeurs conservées de la dernière révision marquée, datées de son marquage — mais alors les coûts réels importés depuis ne se voient nulle part — ; ou la dernière révision marquée recalculée au jour courant, avec le coût réel du jour, ce qui est possible puisque sa structure est figée. Un développeur choisira, et le portefeuille ne sommera pas la même chose d'un projet à l'autre.

**Proposition.** WF-IND-0010, corps, après la première phrase : « Lorsque le projet ne comporte pas de révision en cours, ses indicateurs au jour courant se calculent sur sa dernière révision marquée, avec le coût réel au jour courant ; les indicateurs conservés de cette révision à sa date de marquage restent inchangés (WF-DAT-0040). » Vérif, ajouter : « Sur un projet sans révision en cours, un import de coûts réels change les indicateurs au jour courant et laisse inchangés ceux conservés de la dernière révision marquée. » Dans WF-IND-0130 et WF-PTF-0010, remplacer « pour la révision en cours » et « par sa révision en cours » par « au jour courant (WF-IND-0010) ».

**Statut.** intégré avec écart : WF-IND-0130 et WF-PTF-0010 disent « au jour courant (WF-IND-0010) » sans redoubler l’expression


---

## C-166 — Le coût réel d'une révision marquée est défini par date de pièce ici, par date d'import là

- **gravité** : majeur
- **emplacement** : §3.4.5.8, `WF-IND-0010-A` ; §4.4.2, `WF-DAT-0040-A` ; §3.4.5.8.7, `WF-IND-0100-A` ; §3.4.5.8.8, `WF-IND-0110-A`
- **citation** : « Le coût réel à une date est la somme des lignes de coût du périmètre suivi dont la date de pièce est antérieure ou égale à cette date. » (WF-IND-0010) ; « Les indicateurs d’une révision marquée ne changent pas après son marquage, même après import de coûts réels postérieurs. » (WF-IND-0010, Vérif) ; « Les indicateurs conservés d’une révision marquée sont identiques avant et après un import de coûts réels postérieur. » (WF-DAT-0040, Vérif)

**Constat.** Une ligne de coût peut être datée avant le marquage et importée après : la pièce de mars arrive à l'extraction d'avril. Selon la définition de WF-IND-0010, elle entre dans le coût réel « à la date » de marquage ; selon WF-DAT-0040, les indicateurs conservés ne bougent pas. Les deux textes sont compatibles si l'on comprend que la définition s'applique aux lignes connues au moment du calcul, mais ni l'un ni l'autre ne le dit, et « postérieurs » dans les deux Vérif peut se lire « datés après » comme « importés après ». La conséquence se voit sur les courbes : WF-IND-0100 et WF-IND-0110 tracent « le coût réel cumulé selon les dates de pièce, jusqu'à la date de calcul », et rien ne dit que les courbes d'une révision marquée sont conservées avec ses indicateurs. Un développeur qui les retrace depuis les lignes de coût du jour obtient, sur une révision marquée, un point de coût réel qui ne correspond plus à l'indice de coût conservé dès qu'une ligne a été importée, mise à jour (WF-INTF-0140) ou exclue (WF-CRE-0030) depuis le marquage.

**Proposition.** WF-IND-0010, corps : « Le coût réel à une date est la somme des lignes de coût du périmètre suivi, connues au moment du calcul, dont la date de pièce est antérieure ou égale à cette date. Pour une révision marquée, ce sont les lignes connues à son marquage, telles qu'elles étaient alors : une ligne importée, mise à jour ou exclue ensuite n'y entre pas, quelle que soit sa date de pièce. Les courbes d'une révision marquée (WF-IND-0100, WF-IND-0110) sont conservées avec ses indicateurs (WF-DAT-0040). » Vérif : remplacer « même après import de coûts réels postérieurs » par « même après l'import d'une ligne de coût datée avant le marquage, qui n'entre ni dans son coût réel ni dans ses courbes ».

**Statut.** intégré


---

## C-167 — Le budget de référence par sous-projet n'est pas dans la liste des grandeurs par sous-projet

- **gravité** : mineur
- **emplacement** : §3.4.5.8, `WF-IND-0020-A`
- **citation** : « La valeur planifiée, la valeur acquise, le coût réel, le reste à engager et les indicateurs qui en dérivent se calculent pour le projet et pour chacun de ses sous-projets, l’ensemble « hors sous-projet » compris. »

**Constat.** La consommation du budget (WF-IND-0040), les projections (WF-IND-0050), l'avancement physique (WF-IND-0060) et l'écart de WF-RAE-0020 se calculent par sous-projet et divisent ou soustraient un « budget du sous-projet » que WF-IND-0020 ne nomme pas et que le glossaire ne définit qu'au niveau du projet. La lecture naturelle — somme des montants budgétés des lignes du sous-projet, hors provisions — est la bonne, mais c'est la seule grandeur de la formule que le lecteur doit déduire.

**Proposition.** « Le budget de référence, la valeur planifiée, la valeur acquise, le coût réel, le reste à engager et les indicateurs qui en dérivent se calculent pour le projet et pour chacun de ses sous-projets, l'ensemble « hors sous-projet » compris ; le budget de référence d'un sous-projet est la somme des montants budgétés de ses lignes dans la révision de référence, hors lignes de provision. » Vérif : ajouter « le budget de référence » à l'énumération.

**Statut.** intégré


---

## C-168 — La valeur acquise n'exclut pas les lignes de provision, contrairement à la valeur planifiée

- **gravité** : mineur
- **emplacement** : §3.4.5.8, `WF-IND-0030-A`
- **citation** : « La valeur acquise à une date est la somme des montants budgétés des lignes portées par les tâches terminées à cette date, la date de terminaison de la tâche faisant foi. »

**Constat.** WF-DEV-0080 calcule la valeur planifiée « sur les lignes comptées au budget de référence — hors lignes de provision — » ; WF-IND-0030 ne dit rien des lignes de provision. Tant que C-098 n'est pas tranché, une ligne de provision peut être portée par une tâche qui se termine ; si son montant dans la révision de référence est lu comme un montant budgété — WF-RIS-0040 parle de « la provision qu'ils portaient dans la révision de référence » —, la valeur acquise peut dépasser le budget de référence, et l'avancement physique 100 %.

**Proposition.** « La valeur acquise à une date est la somme des montants budgétés des lignes portées par les tâches terminées à cette date, hors lignes de provision (WF-DEV-0080), la date de terminaison de la tâche faisant foi. »

**Statut.** intégré


---

## C-169 — La pente 1 suppose des revues mensuelles, et le dernier point sur la diagonale suppose une abscisse non dite

- **gravité** : mineur
- **emplacement** : §3.4.5.8.6, `WF-IND-0090-A`
- **citation** : « Un jalon repoussé d’un mois à chaque revue trace une droite de pente 1. » ; « Un jalon terminé n’a plus de point après sa terminaison, et son dernier point est sur la diagonale. »

**Constat.** La pente d'une courbe temps/temps est le glissement rapporté à l'intervalle entre revues : un jalon repoussé d'un mois à chaque revue trimestrielle trace une pente d'un tiers. La Vérif ne fixe pas l'intervalle. Par ailleurs, le corps place les points « en fonction de la date de marquage » ; une révision marquée après la terminaison du jalon donnerait un point (date de marquage, date de terminaison), sous la diagonale. Le dernier point n'est sur la diagonale que s'il est placé à l'abscisse de la terminaison elle-même, ce que « la courbe d'un jalon s'arrête à sa terminaison » laisse entendre sans le dire.

**Proposition.** Corps : « La diagonale des dates égales y figure ; la courbe d'un jalon s'arrête par un point à sa date de terminaison, en abscisse comme en ordonnée, et aucune révision marquée après cette date n'y ajoute de point. » Vérif : « Un jalon repoussé d'un mois à chacune de trois revues mensuelles trace une droite de pente 1. »

**Statut.** intégré


---

## C-170 — En mode décaissements, les provisions sont ajoutées à un reste à engager qui les contient déjà

- **gravité** : majeur
- **emplacement** : §3.4.5.8.7, `WF-IND-0100-A` ; à rapprocher de `WF-RAE-0010-A`
- **citation** : « Sur demande, chaque montant est décalé du délai de paiement de sa ligne, et les provisions des risques identifiés s’ajoutent à la date de la tâche qui les porte : la courbe présente alors les décaissements, passés et à venir, par mois. » (WF-IND-0100) ; « et des lignes de provision des risques identifiés à la date de calcul, pour leur montant » (WF-RAE-0010)

**Constat.** La projection tracée « au-delà » de la date de calcul est celle du chef de projet, « le reste à engager étant étalé » ; or le reste à engager comprend déjà les lignes de provision (WF-RAE-0010, §3.2.5 : « lignes de provision des risques identifiés comprises »), chacune portée par une tâche qui la date. En mode décaissements, « les provisions des risques identifiés s'ajoutent » une seconde fois. Soit la phrase double les provisions, soit elle suppose que le mode normal les exclut de la projection, ce qui contredirait WF-IND-0050 (la projection du chef de projet est « la somme du coût réel et du reste à engager ») et la Vérif de la même exigence (« la somme des décaissements à venir égale le reste à engager »). Un développeur ne peut satisfaire à la fois le corps et la Vérif.

**Proposition.** « Sur demande, chaque montant est décalé du délai de paiement de sa ligne — une ligne de provision, qui n'en porte pas, reste à la date de la tâche qui la porte — : la courbe présente alors les décaissements, passés et à venir, par mois. » Vérif, préciser : « la somme des décaissements à venir égale le reste à engager, provisions des risques identifiés comprises ».

**Statut.** intégré


---

## C-171 — La courbe du budget ne peut pas présenter une marche si elle se lit sur la seule référence en vigueur

- **gravité** : majeur
- **emplacement** : §3.4.5.8.7, `WF-IND-0100-A` ; à rapprocher de `WF-DEV-0080-A`
- **citation** : « le budget de référence cumulé selon les dates de la référence » ; « Les changements du budget de référence — les avenants — y apparaissent comme des marches, datées. » (WF-IND-0100) ; « lorsqu’un avenant en produit une nouvelle, la courbe est recalculée intégralement sur celle-ci » (WF-DEV-0080)

**Constat.** Une courbe cumulée lue sur une seule révision de référence ne saute qu'aux dates de ses jalons : si l'avenant ajoute des tâches futures, la pente change, mais il n'y a pas de marche « à sa date ». La marche n'existe que si la courbe est historique : le cumul de l'ancienne référence avant la date de l'avenant, celui de la nouvelle après, et le saut entre les deux à cette date. C'est ce que l'introduction du §3.4.5.8 annonce (« les courbes les datent »), mais WF-IND-0100 dit « selon les dates de la référence », au singulier, et WF-DEV-0080 dit de la valeur planifiée exactement l'inverse : recalculée intégralement sur la nouvelle référence, donc sans marche. Les deux courbes sont voisines — l'une est l'autre en EVM — et le document ne dit ni qu'elles diffèrent, ni comment se construit celle qui a des marches. Le testeur de la Vérif « la courbe du budget présente une marche à sa date » ne sait pas quelle hauteur attendre, ni comment la courbe se répartit après la marche.

**Proposition.** WF-IND-0100, corps : « le budget de référence cumulé : à chaque date, celui de la révision de référence en vigueur à cette date, lu sur ses propres dates par la règle de la valeur planifiée (WF-DEV-0080) ; au passage d'une référence à la suivante, la courbe saute de la différence des deux cumulés à la date de l'avenant, ce qui en fait une marche datée ». Vérif : « Après contractualisation d'un avenant qui porte le budget de 1 000 à 1 200, la courbe du budget présente à la date de l'avenant une marche égale à l'écart des deux cumulés à cette date, et atteint 1 200 à la date de fin de la nouvelle référence. » Et dans WF-DEV-0080, Motif, ajouter : « contrairement à la courbe de coûts cumulés (WF-IND-0100), qui garde l'histoire des références ».

**Statut.** intégré


---

## C-172 — Redis indisponible : la session du front y vit, donc ni la consultation ni la saisie ne continuent, et personne ne peut se reconnecter

- **gravité** : majeur
- **emplacement** : §4.5.4, tableau 12 Modes dégradés, ligne « Redis » ; §4.4.5 `WF-DAT-0130-A` (Vérif) ; §4.2.2 `WF-ARC-0030-A` et `WF-ARC-0040-A` ; §4.2.1.3 PBS-3.2 ; §4.3.2 TFX-01 et TFX-04
- **citation** : « Redis | La consultation et la saisie, les indicateurs de la révision en cours étant recalculés à chaque requête | La prise de nouvelles tâches ; les sessions du front, que les utilisateurs rouvrent en se reconnectant » (tableau 12) ; « L'indisponibilité du cache n'empêche aucune lecture ni aucune saisie. » (WF-DAT-0130) ; « Le front obtient les jetons par le flux du code d’autorisation, côté serveur, et ne les transmet jamais au navigateur. » (WF-ARC-0030) ; « la correspondance que le front garde entre le témoin du navigateur et les jetons, qu'une reconnexion reconstruit » (WF-ARC-0040)

**Constat.** C-074 a été intégré avec un écart : les permissions sont sorties de Redis, mais la
session du front y est restée (PBS-3.2, WF-ARC-0040, §4.4.1, §4.4.5), au motif que « sa perte ne
coûte qu'une reconnexion ». C'est vrai d'un **vidage** de Redis, que la Vérif de WF-ARC-0040
teste. Ce n'est pas vrai de son **indisponibilité**, que le tableau 12 décrit : à chaque requête
du navigateur (TFX-01, « Témoin de session du front »), le front doit lire dans Redis (TFX-04) la
correspondance entre le témoin et les jetons, puisque les jetons ne sont jamais au navigateur
(WF-ARC-0030). Redis absent, aucune requête du front ne peut être authentifiée, et aucune
reconnexion ne peut écrire la session nouvelle. La colonne « ce qui continue » promet la
consultation et la saisie à des utilisateurs qui ne peuvent ni rester connectés ni se
reconnecter ; la colonne « ce qui s'arrête » dit qu'ils « rouvrent en se reconnectant », ce qui
n'est possible qu'après le rétablissement. La Vérif de WF-DAT-0130 — « n'empêche aucune lecture
ni aucune saisie » — ne peut pas passer, puisque le cache et la session sont le même composant.

Le tableau se contredit donc lui-même comme le 26 septembre, pour une autre raison : le texte du
§4.5.4 présente ce tableau comme ce « qui justifie » WF-ARC-0040, et c'est le seul composant de
données dont la panne arrête tout sans que le tableau le dise.

**Proposition.** Deux voies, selon qu'on garde ou non la session dans Redis.

*Si la session reste dans Redis* (choix actuel), rendre le tableau et la Vérif vrais :

> | Redis | Les traitements que le worker a déjà pris ; les appels directs à l’API porteurs d’un jeton d’accès valide, les indicateurs de la révision en cours étant recalculés à chaque requête | Toute requête du front, dont la session ne peut être ni lue ni recréée ; la prise de nouvelles tâches |

et, dans la Vérif de WF-DAT-0130 : « L'indisponibilité du cache des indicateurs n'empêche aucune
lecture ni aucune saisie faite par l'API ; la session du front, elle, n'est pas disponible
pendant cette indisponibilité (§4.5.4). » Ajouter au texte du §4.5.4, après le tableau : « Redis
est, avec PostgreSQL, le composant dont l'indisponibilité interrompt le travail des utilisateurs :
c'est le prix de la session dans Redis (WF-ARC-0040), accepté parce que Redis se redémarre en
quelques secondes et ne porte rien à restaurer. »

*Si l'on veut que le tableau dise ce qu'il disait*, la correspondance témoin–jetons doit vivre
ailleurs que dans Redis : en base (une ligne « Session du front | front_session | plateforme » au
tableau 10, et WF-ARC-0040 sans « aucune session n’est conservée en base »), comme C-074 le
proposait. La ligne « Redis » du tableau 12 devient alors : « Tout, les indicateurs de la révision
en cours étant recalculés à chaque requête | La prise de nouvelles tâches ».

**Statut.** intégré avec écart : la première voie, session conservée dans Redis ; la seconde, signalée en commentaire, n’a pas été retenue


---

## C-173 — Un export est une tâche de fond dont le fichier n'a nulle part où attendre son téléchargement

- **gravité** : majeur
- **emplacement** : §4.3.4 `WF-ARC-0090-A` ; §4.4.4 (texte) et `WF-DAT-0120-A` ; §4.3.3 tableau 9, ligne FLX-02 ; §4.1.3 `WF-ARC-0080-A` ; §4.3.1 figure 18 ; §4.5.4 tableau 12, ligne « Stockage objet » ; §4.6.2 tableau 15
- **citation** : « Les traitements dont la durée dépend du volume des données — analyse et application d’un import, marquage d’une révision, engendrement d’un export, […] — sont exécutés par le worker à partir d’une file de tâches, et non dans la requête qui les demande. […] Aucun de ces traitements n’est joignable par un endpoint qui répondrait après l’avoir exécuté. » (WF-ARC-0090) ; « Aucun autre fichier n’y est conservé, et les exports sont engendrés à la demande sans y être stockés. » (WF-DAT-0120) ; « Demande par TFX-02, engendrement du fichier par le worker à partir de la révision, transmission à l’utilisateur, aucun stockage (WF-DAT-0120) » (tableau 9, FLX-02)

**Constat.** Quatre passages, pris ensemble, ne laissent au fichier exporté aucun endroit où
exister entre sa production et son téléchargement :

- WF-ARC-0090 en fait une tâche du worker, asynchrone, dont « l’utilisateur suit l’avancement et
  le résultat » ; WF-IHM-0080 veut qu'il « retrouve son avancement en revenant » ; le tableau 15
  lui donne trente secondes et le range parmi « des tâches de fond (WF-ARC-0090) » ;
- le worker n'a « aucun état […] sur [son] disque local entre deux requêtes ou deux tâches »
  (WF-ARC-0080), et la figure 18 ne relie pas le service d'API au worker : le fichier ne peut
  passer de l'un à l'autre que par un composant de données ;
- Redis « ne porte que des données reconstructibles […] et la file de tâches » (WF-ARC-0040), et
  le tableau 10 n'a pas de table pour un fichier ;
- le stockage objet « ne porte que les fichiers en transit pendant un import et les sauvegardes »
  (WF-ARC-0040), et WF-DAT-0120 interdit expressément d'y mettre les exports, ce que le §4.4.4 et
  le tableau 9 répètent.

Un développeur ne peut pas satisfaire WF-ARC-0090 et WF-DAT-0120 à la fois. Le tableau 12 a
d'ailleurs déjà tranché sans le dire : il arrête « Les imports, les exports et les sauvegardes »
quand le stockage objet tombe, ce qui n'a de sens que si les exports y passent.

**Proposition.** Donner aux exports le même régime qu'aux imports : un passage par le stockage
objet, borné dans le temps.

- **WF-DAT-0120, corps** : « Le stockage objet porte trois compartiments : les fichiers en cours
  d’import, les fichiers exportés en attente de téléchargement, et les sauvegardes. Un fichier en
  cours d’import est supprimé dès que l’import est appliqué, abandonné ou expiré (WF-ARC-0100). Un
  fichier exporté est supprimé à son téléchargement ou au terme de vingt-quatre heures. Les
  sauvegardes suivent la rétention de WF-ADM-0170. Aucun autre fichier n’y est conservé. » Vérif,
  remplacer la dernière phrase par : « Un export téléchargé n’est plus sur le stockage objet ; un
  export jamais téléchargé en disparaît au terme de vingt-quatre heures. »
- **§4.4.4, texte** : « Le stockage objet ne contient que trois choses, et rien d’autre n’y est
  déposé : les fichiers en cours d’import, qui y vivent le temps d’un import, les fichiers
  exportés, qui y attendent leur téléchargement, et les sauvegardes, qui y vivent le temps de leur
  rétention. »
- **Tableau 9, FLX-02** : « Demande par TFX-02, tâche mise en file (TFX-04), engendrement du
  fichier par le worker à partir de la révision, dépôt sur le stockage objet (TFX-05),
  téléchargement par l’utilisateur, suppression du fichier (WF-DAT-0120) ».
- **PBS-3.3 et WF-ARC-0040** : ajouter « les fichiers exportés en attente de téléchargement » à
  l'énumération de ce que porte le stockage objet.

La ligne « Stockage objet » du tableau 12 devient alors exacte sans changer.

**Statut.** intégré


---

## C-174 — Le traitement d'une demande d'effacement est promis en prose et porté par aucune exigence

- **gravité** : majeur
- **emplacement** : §4.6.1, texte « Un mot des données personnelles » ; §3.4.2.1 `WF-ADM-0060-A`
- **citation** : « Un compte ne se supprime pas (WF-ADM-0060), parce que ses actes doivent rester attribuables ; une demande d'effacement se traite donc en remplaçant l'identité par un libellé neutre, ce qui laisse l'attribution intacte et ne dit plus qui c'était. »

**Constat.** La phrase engage le produit sur un comportement — remplacer le nom, le prénom,
l'adresse et l'avatar d'un compte par un libellé neutre à la demande de la personne — qu'aucune
exigence ne porte. WF-ADM-0060 connaît trois actes : « Un compte se crée, se modifie et se
désactive » ; aucune fonction de FBS-1.1 n'en décrit un quatrième, aucune permission du catalogue
ne le couvre, et WF-SEC-0030 ne le journalise pas alors qu'il modifie un compte de façon
irréversible. Le mot « donc » présente comme une conséquence ce qui n'est écrit nulle part : un
développeur qui construit FBS-1.1 d'après ses exigences ne le construit pas, et le document
affirme pourtant qu'une demande d'effacement « se traite ». La seule anonymisation spécifiée est
celle des copies de production (WF-EXP-0010), qui ne répond pas à une demande individuelle.

**Proposition.** Ajouter au corps de WF-ADM-0060 :

> Un compte désactivé peut être anonymisé par un utilisateur habilité, à la demande de la
> personne : son nom, son prénom et son adresse électronique sont remplacés par un libellé neutre
> et son avatar retiré, de façon irréversible, sans que ses actes cessent de lui être attribués.
> Un compte anonymisé ne peut pas être réactivé, et l’anonymisation est inscrite au journal
> d’audit (WF-SEC-0030).

Vérif, ajouter : « Après anonymisation d’un compte désactivé, aucun écran ne présente plus son
nom ni son adresse ; les révisions qu’il a marquées affichent le libellé neutre comme auteur ; sa
réactivation est refusée. » Dans WF-SEC-0030, remplacer « la création et la modification des
comptes » par « la création, la modification et l’anonymisation des comptes ». Dans le §4.6.1 :
« une demande d'effacement se traite en anonymisant le compte (WF-ADM-0060) ».

**Statut.** intégré


---

## C-175 — Deux phrases d'introduction du §4.2 contredisent WF-DAT-0010 et WF-ARC-0040

- **gravité** : mineur
- **emplacement** : §4.2 Découpage technique, texte d'introduction (paragraphes « Un service, pas plusieurs » et « Trois composants de données »)
- **citation** : « Le marquage d’une révision est une transaction unique qui copie des structures et calcule des indicateurs (WF-DAT-0040) » ; « Redis porte le cache des indicateurs de la révision en cours et la file de tâches, et rien d'autre : ce qu'on y met doit pouvoir se recalculer, faute de quoi sa perte devient une panne. »

**Constat.** Deux survivances d'intégrations antérieures.

- La première phrase est ce que C-070 a fait retirer du §4.3.4 et de la figure 20 : WF-DAT-0010
  dit « le marquage ne copie rien », et la copie a lieu à la création de la révision suivante. Le
  §4.2 motive l'unicité du service par une transaction qui n'existe plus sous cette forme.
- La seconde est ce que C-074 proposait pour le §4.2, appliqué alors que la session du front est
  restée dans Redis (PBS-3.2, WF-ARC-0040, §4.4.5). « rien d'autre » est faux, et « ce qu'on y met
  doit pouvoir se recalculer » ne décrit pas une session, que WF-DAT-0130 dit justement « sans être
  un cache ».

Ni l'une ni l'autre ne trompe celui qui lit les exigences ; elles trompent celui qui lit le §4.2
pour comprendre les choix.

**Proposition.** « Le marquage d’une révision est une transaction unique qui fige des structures
et calcule des indicateurs (WF-DAT-0040) : elle ne survivrait pas à un découpage en services. » Et :
« Redis porte le cache des indicateurs de la révision en cours, la session du front et la file de
tâches, et rien d'autre : ce qu'on y met doit pouvoir se recalculer ou se refaire par une
reconnexion, faute de quoi sa perte devient une panne (WF-ARC-0040). » Si C-172 fait passer la
session en base, retirer « la session du front » de cette phrase.

**Statut.** intégré


---

## C-176 — Trois données conservées sans table : le compte rendu d'import, la tâche de fond, les préférences d'affichage

- **gravité** : mineur
- **emplacement** : §4.4.1, tableau 10 Correspondance entre objets et tables ; §4.3.4 figure 19 ; §3.4.2.1 `WF-ADM-0040-A` ; §3.6 `WF-IHM-0060-A` et `WF-IHM-0080-A`
- **citation** : « W->>B: conserve le compte rendu » (figure 19) ; « Son aboutissement comme son échec sont signalés même si l'utilisateur a changé d'écran entre-temps » (WF-IHM-0080) ; « Le choix des colonnes, des largeurs, du tri et des filtres est une préférence d’affichage (WF-ADM-0040), conservée par grille. » (WF-IHM-0060)

**Constat.** Le tableau 10 se présente comme la correspondance de « chaque objet » avec « une table
qui porte son nom ». Trois données que le document fait conserver n'y figurent pas :

- le **compte rendu d'import** : la figure 19 l'écrit dans PostgreSQL, WF-ARC-0110 en fait « Un message conservé », et il vit vingt-quatre heures (WF-ARC-0100) ;
- la **tâche de fond** : WF-ARC-0090 la fait désigner par la requête et suivre par l'utilisateur,
  WF-IHM-0080 veut son résultat retrouvé après un changement d'écran ; la file (Redis) porte la
  tâche à exécuter, mais son état et son résultat survivent à son exécution et à un vidage de Redis
  (WF-ARC-0040, Vérif) seulement s'ils sont en base ;
- les **préférences d'affichage** : WF-ADM-0040 les conserve par utilisateur, WF-IHM-0060 par
  grille, et un autre poste doit les retrouver ; leur champ `pbs` cite PBS-3.1, le tableau non.

Rien de cela n'est ambigu quant au composant — PostgreSQL dans les trois cas —, mais le régime
de chacune fixe sa suppression (WF-DAT-0080) : un compte rendu expiré se supprime, ce que le
régime projet n'autorise que « tant qu’aucune révision marquée ni aucune ligne de coût ne le
référence ».

**Proposition.** Trois lignes au tableau 10, et une phrase avant lui.

> | Tâche de fond et son résultat (WF-ARC-0090) | background_task | plateforme |
> | Compte rendu d’import (WF-INTF-0080, WF-ARC-0100) | import_report | projet |
> | Préférences d’affichage (WF-ADM-0040) | display_preference | plateforme |

Avant le tableau : « Une tâche de fond, un compte rendu d’import expiré et une préférence
d’affichage sont les seules lignes de ces régimes qui se suppriment physiquement : la première au
terme de la rétention de son résultat, le second à son expiration (WF-ARC-0100), la troisième à la
demande de son porteur. » Et compléter WF-DAT-0080 en conséquence : « hors les tâches de fond, les
comptes rendus d’import et les préférences d’affichage, qui se suppriment selon leur propre
règle (§4.4.1) ».

**Statut.** intégré


---

## C-177 — Trois seuils ni fixés ni déclarés paramétrables

- **gravité** : mineur
- **emplacement** : §4.4.5 `WF-DAT-0130-A` ; §4.6.3 `WF-OBS-0030-A` ; §4.4.1, texte « Correspondance entre objets et tables »
- **citation** : « Une durée de validité borne en outre chaque entrée. » (WF-DAT-0130) ; « file de tâches qui ne se vide plus, […] espace de stockage proche de la saturation, taux d'erreur anormal » (WF-OBS-0030) ; « La taille d'un avatar est bornée par l'application. » (§4.4.1)

**Constat.** C-071 a fait chiffrer les délais de WF-ARC-0100 et WF-SEC-0020. Trois seuils du §4
sont restés sans valeur et sans régime : la durée de validité du cache, les trois seuils d'alerte
qualifiés de « ne se vide plus », « proche » et « anormal », et la taille maximale d'un avatar. Pour
les alertes, la Vérif n'en teste que deux sur trois et aucune par sa borne : « anormal » ne se
vérifie pas. Ce sont des réglages d'exploitation, et c'est ce qu'il faut dire, avec une valeur
livrée.

**Proposition.**

- WF-DAT-0130 : « Une durée de validité, paramètre d'exploitation livré à dix minutes, borne en
  outre chaque entrée. »
- WF-OBS-0030 : « […] file de tâches dont la plus ancienne attend plus longtemps qu'un seuil,
  échec d'une sauvegarde planifiée (WF-ADM-0170), échec d'une synchronisation de l'annuaire,
  espace de stockage au-delà d'un taux d'occupation, taux d'erreur des requêtes au-delà d'un
  seuil. Les trois seuils sont des paramètres d'exploitation, livrés à quinze minutes, 85 % et 5 %
  sur cinq minutes. » Vérif, ajouter : « Un taux d'erreur porté au-dessus du seuil pendant cinq
  minutes produit une alerte ; chaque seuil est vérifiable par un essai à sa borne. »
- §4.4.1 : « La taille d'un avatar est bornée par un paramètre d'exploitation, livré à 512 Ko. »

**Statut.** intégré


---

## C-178 — L'export PNG exige un nom de projet et une révision sur des diagrammes de portefeuille qui n'en ont pas

- **gravité** : mineur
- **emplacement** : §3.6 `WF-IHM-0130-A`
- **citation** : « Toute courbe et tout diagramme — Gantt, plan de charge, courbes d’indicateurs, matrice des risques — s’exportent en image PNG, avec leur titre, leur légende, le nom du projet, la révision et la date de calcul. » ; Vérif : « Le plan de charge exporté est une image PNG qui porte le nom du projet, la révision et la date de calcul. »

**Constat.** « Toute courbe et tout diagramme » couvre le plan de charge agrégé (WF-PTF-0060), la
courbe en S du portefeuille (WF-PTF-0100) et la matrice des risques du portefeuille (WF-PTF-0090),
qui n'ont ni projet ni révision : ils ont un périmètre et une date de calcul (WF-PTF-0010). À la
lettre, l'image exportée d'une vue de portefeuille doit porter « le nom du projet », et la Vérif,
qui ne nomme pas le plan de charge dont elle parle, se lit aussi bien sur l'un que sur l'autre.

**Proposition.** « […] s’exportent en image PNG, avec leur titre, leur légende et la date de
calcul, et, pour une vue de projet, le nom du projet et la révision, pour une vue de portefeuille,
le périmètre affiché (WF-PTF-0010). » Vérif : « Le plan de charge d’un projet exporté est une
image PNG qui porte le nom du projet, la révision et la date de calcul ; le plan de charge agrégé
exporté porte le périmètre et la date de calcul. »

**Statut.** intégré


---

## C-179 — Deux flux techniques absents : le fournisseur d'identité vers PostgreSQL, et les courriels

- **gravité** : mineur
- **emplacement** : §4.3.1 figure 18 ; §4.3.2 tableau 8 ; §4.2.1.3 PBS-3.1 ; §4.6.5 `WF-CMP-0030-A` ; §4.1.3 `WF-ARC-0110-A` ; §4.6.1 `WF-SEC-0010-A`
- **citation** : « dans une base séparée de la même instance, les données du fournisseur d’identité (PBS-5.4) » (PBS-3.1) ; « les courriels partent par un serveur de messagerie interne » (WF-CMP-0030) ; « Tout échange est chiffré : […] conformément au tableau des flux techniques. » (WF-SEC-0010)

**Constat.** Le tableau 8 se veut la liste des flux techniques, et WF-SEC-0010 y adosse
l'obligation de chiffrement. Deux flux que le document décrit ailleurs n'y sont pas, ni sur la
figure 18 :

- le **fournisseur d'identité vers PostgreSQL** : sa base est « dans une base séparée de la même
  instance » (PBS-3.1), que le worker sauvegarde ; la figure 18 ne relie pas Keycloak à PostgreSQL,
  et TFX-03 ne nomme que « Service d’API, worker » ;
- les **courriels** : le fournisseur d'identité envoie les liens de mot de passe (WF-ARC-0110,
  WF-ADM-0140) et les services produisent eux-mêmes des courriels (WF-ARC-0110), vers un « serveur
  de messagerie interne » (WF-CMP-0030) qui n'apparaît ni comme destination ni comme système
  externe.

Un flux absent du tableau est un flux dont personne ne dit s'il est chiffré ni comment il
s'authentifie — et le second sort du cluster.

**Proposition.** Deux lignes au tableau 8 :

> | TFX-12 | Fournisseur d’identité | PostgreSQL | Connexion chiffrée | Secret de la plateforme |
> | TFX-13 | Fournisseur d’identité, service d’API, worker | Serveur de messagerie | SMTP sur TLS | Compte de service |

Dans `figures/deploiement.mmd` : un nœud « Serveur de messagerie » hors du cluster, les arêtes
`IdP --> PG`, `IdP --> SMTP`, `API --> SMTP` et `Worker --> SMTP`. Dans le texte du §4.3.1 : « Le
navigateur ne parle qu’au front et, le cas échéant, au fournisseur d’identité ; la plateforme ne
parle hors du cluster qu’à l’annuaire et au serveur de messagerie ; aucun composant de données
n’est joignable de l’extérieur. »

**Statut.** intégré


---

## C-180 — La figure 19 ne montre ni la revérification à l'application (WF-ARC-0100) ni la demande d'abandon

- **gravité** : mineur
- **emplacement** : §4.3.4, figure 19 Diagramme de séquence des imports (`figures/import-deux-temps.mmd`) ; `WF-ARC-0100-A`
- **citation** : « W->>F: prend la tâche / W->>B: applique en une transaction unique » et « else L'utilisateur abandonne ou laisse expirer / W->>S: supprime le fichier » (figure 19) ; « L'application d'un import revérifie, au moment où elle s'exécute, la permission et la qualité de contributeur de l'utilisateur qui l'a demandée, ainsi que l'état du projet » (WF-ARC-0100)

**Constat.** La figure est présentée comme un des enchaînements qui « méritent d’être suivis de bout en bout ». Depuis C-082,
WF-ARC-0100 fait de la revérification des droits et de l'état du projet une étape de
l'application, avec un refus possible qui « nomme la condition manquante » ; la figure passe de
« prend la tâche » à « applique » sans elle, et sans issue de refus. Dans la branche d'abandon,
le worker supprime le fichier sans qu'aucun message ne vienne de l'utilisateur ni de l'API : la
figure ne dit pas par où passe l'abandon, alors qu'elle le fait pour la confirmation.

**Proposition.** Dans `figures/import-deux-temps.mmd`, après « W->>F: prend la tâche » de la
branche de confirmation : « W->>B: revérifie permission, contributeur et état du projet » suivi
d'un `alt` à deux issues — « applique en une transaction unique » / « W-->>U: import refusé, condition
nommée » puis « W->>S: supprime le fichier ». Dans la branche d'abandon, en tête : « U->>A: abandonne
l'import » puis « A->>F: met en file la suppression » avant « W->>S: supprime le fichier » ; pour
l'expiration, une note « au terme de vingt-quatre heures (WF-ARC-0100) ».

**Statut.** intégré

---

## C-181 — La matrice FBS–PBS n'a pas de ligne pour FBS-1.5, et la ligne FBS-1.3 n'a pas PBS-4.2

- **gravité** : mineur
- **emplacement** : §4.2.2, tableau 7 ; `WF-SEC-0030-A` ; `WF-OBS-0020-A`
- **citation** : « Une fonction absente de la matrice est réalisée par le socle seul » ; « la ligne de la matrice est l’union des composants de ses exigences. »

**Constat.** FBS-1.5 n'a pas de ligne dans le tableau 7, ce qui, par la règle citée, la réalise
« par le socle seul » ; or WF-SEC-0030, désormais rattachée à FBS-1.5, cite PBS-4.2, qui n'est
pas du socle. De même, WF-OBS-0020 porte FBS-1.3 et engage PBS-4.2, que la ligne FBS-1.3 ne cite
pas. C'est la règle que C-068 et C-069 ont fait écrire ; les ajouts du 8 octobre l'ont enjambée.

**Proposition.** Ajouter au tableau 7, après FBS-1.4 : « | FBS-1.5 Journal d’audit | — (lecture
de la table du journal, WF-SEC-0030) | » si C-116 fait du journal une table de PostgreSQL, sinon
« PBS-4.2 ». Ligne FBS-1.3 : « PBS-4.1, PBS-4.2, PBS-4.3 ».

**Statut.** intégré avec écart : la ligne FBS-1.5 porte « — (lecture de la table du journal, WF-SEC-0030) », le journal étant une table (C-116)

