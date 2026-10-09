---
revue_du: 2026-10-07
sur: waterfall-spec.md généré le 2026-10-07 (commit dd280d9, branche epic/EP-02)
revue_par: Claude Code
perimetre: document complet — accent sur les six exigences modifiées depuis main (WF-PLA-0010, WF-PLA-0100, WF-PLA-0130, WF-DEV-0060, WF-RIS-0020, WF-IHM-0110) et sur ce que la passe du 2026-10-04 a laissé derrière elle
---

# Revue du 2026-10-07 — document complet

## Suivi des revues précédentes

Les neuf revues précédentes ne laissent aucun constat « à traiter ». Deux étaient reportés :

- **C-015** (WF-CYC-0040 non vérifiable tant que les paramètres requis ne sont pas listés,
  reporté sur PO-03) est **résolu** par disparition de son objet : l'état Initialisé et
  WF-CYC-0040 ont été retirés à la suite de C-028, le cycle de vie compte six états
  (WF-CYC-0010), et PO-03 ne figure plus en annexe D. Son statut peut passer à « sans objet ».
- **C-023** (des passages supposent PO-01 résolu) est **toujours ouvert**, à l'identique : le §2
  promet encore de relier « les coûts engagés et réalisés », le glossaire définit toujours
  « Engagé » et « Consommé », et PO-01 est le seul point ouvert restant.

Aucune régression n'a été relevée sur les constats intégrés, à une exception près : C-025 (le
caractère de référence porté à deux endroits) a été intégré au glossaire mais pas dans le
paragraphe du §3.2.3 qu'il visait aussi ; c'est l'objet de C-092.

## Ce que vaut le document

Le document tient. Les 209 exigences se renvoient les unes aux autres sans référence morte,
chaque fonction feuille de l'arborescence porte au moins une exigence, les codes FBS et PBS
cités existent tous, et les exemples chiffrés des Vérif — projections (WF-IND-0050), avancement
financier (WF-IND-0040), agrégation de portefeuille (WF-PTF-0020), couverture des risques
(WF-RIS-0050), inflation (WF-DEV-0030, WF-DEV-0050), calendrier (WF-PLA-0010) — sont justes.

Treize constats, huit majeurs, aucun bloquant. Ils se rangent en trois familles.

**Deux survivances de l'ancien mécanisme des provisions.** La passe du 4 octobre a décidé que
les provisions n'entrent jamais au budget de référence et qu'un risque survenu ne le déplace
pas. Deux phrases disent encore le contraire, dont le corps de WF-RAE-0050 (C-091), et le §3.2.3
donne encore aux structures de coûts les deux natures que C-025 a fait retirer du glossaire
(C-092).

**Ce que les six exigences modifiées sur la branche n'ont pas entraîné avec elles.** Rattacher
les saisies de risque à la révision en cours (WF-RIS-0020) contredit le modèle, le régime de
données du §4.4.1 et la survenance « définitive » (C-093). Le refus d'une tâche sans heure
travaillée (WF-PLA-0010) ne dit ni quelles révisions il examine, ni ce qu'il fait d'un import, et
fait refuser une saisie du référentiel au nom de projets que le manager ne voit pas (C-094). Le
chemin critique à marge « nulle ou négative » (WF-PLA-0100) renvoie pour son signalement à une
exigence qui ne le décrit pas (C-096) et contredit deux entrées du glossaire (C-097). Le
rattachement ouvert aux feuilles (WF-PLA-0130) a laissé « récapitulative » dans le Motif et la
Vérif de WF-DEV-0060 (C-099).

**Deux trous plus anciens, visibles maintenant que tout le reste est écrit.** Le reste à engager
ignore la réestimation d'une tâche non démarrée que WF-RAE-0040 permet pourtant, et compte
peut-être deux fois les provisions (C-095). Et aucune exigence ne dit quelle tâche porte la ligne
de provision : le §3.2.6 la confie à une « tâche récapitulative du projet » que le modèle ne
définit pas (C-098).

Le reste est de la cohérence de surface : vocabulaire d'avant le modèle (C-100), une liste de
colonnes en retard sur les attributs (C-101), une charge « calculée sur les montants » (C-102),
deux ponctuations (C-103).

Deux choses ne sont pas des constats. L'annexe B reste à deux phrases : c'est inscrit au
`TODO.md` du dépôt, décidé jusqu'au cadrage d'EP-09. Et l'en-tête du fichier compte 209
exigences pour 210 blocs : le 210e est l'exemple WF-EXA-0010 du §1.3.1, à juste titre hors
index.

## Constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-091 | majeur | §3.4.5.5.3, WF-RAE-0050 | Deux passages font déplacer le budget de référence par un risque survenu | intégré |
| C-092 | majeur | §3.2.3 | Le §3.2.3 donne encore aux structures deux natures qui n'existent plus | intégré |
| C-093 | majeur | WF-RIS-0020, §3.2.6, §4.4.1, WF-DAT-0010, WF-RIS-0060 | Un risque est porté par le projet, mais ses saisies appartiennent à la révision en cours | intégré avec écart |
| C-094 | majeur | WF-PLA-0010, §3.4.4, WF-INTF-0100 | Le refus d'une tâche sans heure travaillée n'est pas borné | intégré |
| C-095 | majeur | WF-RAE-0010, WF-RAE-0040 | Le reste à engager ignore la réestimation d'une tâche non démarrée, et compte peut-être deux fois les provisions | intégré avec écart |
| C-096 | majeur | WF-PLA-0100, WF-PLA-0020 | Le signalement du conflit avec une tâche manuelle renvoie à une exigence qui ne le décrit pas | intégré |
| C-097 | majeur | annexe A, WF-PLA-0100 | Le glossaire définit encore le chemin critique par la seule marge nulle | intégré |
| C-098 | majeur | §3.2.6, WF-RIS-0010, WF-PLA-0040 | Aucune exigence ne dit quelle tâche porte la ligne de provision | intégré |
| C-099 | mineur | WF-DEV-0060, WF-PRJ-0030 | Le rattachement s'ouvre aux feuilles, mais trois passages parlent encore de récapitulatives | intégré |
| C-100 | mineur | annexe A, §2.1 | Deux formules d'avant le modèle | intégré |
| C-101 | mineur | WF-PLA-0080, WF-PLA-0130 | La grille de planning n'affiche pas tous les attributs que WF-PLA-0130 dit affichés | intégré |
| C-102 | mineur | WF-DEV-0070 | Le plan de charge calcule une charge « sur les montants » | intégré |
| C-103 | mineur | WF-ADM-0050, WF-ADM-0040 | Deux ponctuations qui coupent une énumération | intégré avec écart |

---

## C-091 — Deux passages font déplacer le budget de référence par un risque survenu

- **gravité** : majeur
- **emplacement** : §3.4.5.5.3 « Grille de reste à engager », texte d'introduction ; exigence `WF-RAE-0050-A`
- **citation** : « Ces ajouts ne changent pas le budget de référence, qui n’est déplacé que par un avenant ou par un risque survenu. » (§3.4.5.5.3) ; « et n’entrent pas dans le budget de référence, que seuls un avenant ou un risque survenu déplacent » (WF-RAE-0050)

**Constat.** Tout le reste du document dit le contraire, et le dit depuis la passe du 4 octobre :
« un risque survenu, lui, entre dans le reste à engager sans toucher à la référence » (§2.1),
« La survenance ne marque aucune révision et ne déplace pas la référence : le budget de référence
ne bouge que par un avenant » (§3.2.6), « Les lignes de provision ne font jamais partie du budget
de référence » (WF-RIS-0050), « Le budget de référence change à chaque avenant, et à rien d’autre :
ni la survenance ni l’écart d’un risque ne le déplacent » (§3.4.5.8). Les deux phrases citées sont
les seules survivantes de l'ancien mécanisme, et l'une d'elles est dans le corps d'une exigence
F0 : un développeur qui part de WF-RAE-0050 ferait entrer les lignes d'un risque survenu au
budget, ce que WF-RIS-0060 interdit avec un exemple chiffré.

**Proposition.** Dans WF-RAE-0050, corps :

> Elles augmentent le reste à engager et la projection à terminaison, et n’entrent pas dans le
> budget de référence, que seul un avenant déplace (WF-RIS-0050). Ces tâches et ces lignes
> portent un montant budgété nul, comme celles issues d’un risque survenu (WF-RIS-0060).

Dans le texte du §3.4.5.5.3 :

> Ces ajouts ne changent pas le budget de référence, qui n’est déplacé que par un avenant ; un
> risque survenu entre lui aussi au reste à engager sans le toucher (WF-RIS-0060).

**Statut.** intégré

---

## C-092 — Le §3.2.3 donne encore aux structures deux natures qui n'existent plus

- **gravité** : majeur
- **emplacement** : §3.2.3 « Structure d’un projet », paragraphe « Un projet porte plusieurs structures de coûts » ; à rapprocher de `WF-REV-0100-A`
- **citation** : « La nature d’une structure dit ce qu’elle décrit : le budget de référence, le différentiel d’un avenant, le devis propre à un risque, ou l’état courant du projet. »

**Constat.** WF-REV-0100 fixe trois natures — principale, différentielle, devis de risque — et le
glossaire les reprend. Le §3.2.3 en nomme quatre, dont deux, « le budget de référence » et
« l’état courant du projet », qui ne sont pas des natures de structure mais des rangs de révision,
comme la phrase suivante du même paragraphe le dit d'ailleurs. C'est précisément ce que C-025
avait relevé, et qui a été intégré au glossaire sans l'être ici. Un lecteur du modèle conceptuel
en déduit une énumération à quatre valeurs que le contrat n'a pas.

**Proposition.**

> La nature d’une structure dit ce qu’elle décrit : la structure principale du projet, le
> différentiel d’un avenant, ou le devis propre à un risque (WF-REV-0100). Le caractère de
> référence, lui, est un attribut de la révision : c’est elle qui fait foi pour le budget de
> référence et les dates contractuelles.

**Statut.** intégré

---

## C-093 — Un risque est porté par le projet, mais ses saisies appartiennent à la révision en cours

- **gravité** : majeur
- **emplacement** : §3.4.5.6, `WF-RIS-0020-A` ; §3.2.6 ; §4.4.1 (régimes de données, tableau 10) ; `WF-DAT-0010-A` ; `WF-RIS-0060-A`
- **citation** : « La création, le réexamen et la suppression d’un risque sont des saisies de la révision en cours ; lorsque le projet n’en comporte pas, la saisie en crée une au préalable. » (WF-RIS-0020) ; « Un risque est porté par le projet, et non par une révision » (§3.2.6)

**Constat.** La phrase ajoutée à WF-RIS-0020 est juste dans son intention — chaque révision fige
une évaluation des risques, et les saisies doivent suivre le chemin du devis —, mais elle
contredit trois endroits qui n'ont pas bougé :

- le modèle (§3.2.6, figure 7) et le §4.4.1 rangent le risque et ses réexamens dans le régime
  **projet** (`risk`, `risk_review`), c'est-à-dire hors de ce qu'une révision possède en propre ;
- WF-DAT-0010 dit que l'abandon d'une révision en cours « supprime ses lignes » : un risque créé
  ou réexaminé dans cette révision n'est pas une de ses lignes, et l'« abandon compris » du motif
  de WF-RIS-0020 n'a donc aucune mise en œuvre ;
- WF-RIS-0060 déclare la survenance « définitive » et WF-IHM-0110 l'exclut de l'annulation, mais
  elle fusionne des tâches dans la révision en cours : si cette révision est abandonnée
  (WF-REV-0010), les tâches fusionnées disparaissent et rien ne dit dans quel état le risque se
  retrouve — survenu sans tâches ni provision, ou identifié de nouveau.

Un développeur doit choisir où vivent la probabilité, l'état et l'historique d'un risque, et ce
choix décide de ce qu'un abandon défait.

**Proposition.** Dire ce qu'une révision porte d'un risque, et ce que l'abandon en fait. Dans
WF-RIS-0020, remplacer la dernière phrase par :

> Un risque appartient au projet : son libellé, sa description et sa note de mitigation sont des
> données du projet. Son évaluation — probabilité, état, structure propre et ligne de provision —
> est portée par chaque révision : la révision en cours porte l’évaluation courante, une révision
> marquée fige celle de sa date (WF-RIS-0030). La création, le réexamen, la suppression et la
> survenance d’un risque sont des saisies de la révision en cours ; lorsque le projet n’en
> comporte pas, la saisie en crée une au préalable. L’abandon de la révision en cours (WF-REV-0010)
> ramène les risques à l’évaluation de la dernière révision marquée : un risque créé dans la
> révision abandonnée disparaît, et un risque qui y a été déclaré survenu redevient identifié,
> avec sa provision.

Dans WF-RIS-0060, préciser « Elle est définitive : aucune transition ne part de l’état survenu,
et aucune commande ne l’annule (WF-IHM-0110) ; seul l’abandon de la révision en cours la défait,
avec tout ce que cette révision contient. » Au §4.4.1, passer le réexamen d'un risque (et
l'évaluation qu'il porte) du régime projet au régime révisionné, en gardant `risk` au régime
projet pour l'identité et les notes. Au §3.2.6, remplacer « c’est lui qui traverse le temps » par
une phrase qui dit la même répartition.

**Statut.** intégré avec écart : WF-RIS-0020, WF-RIS-0060 et le §3.2.6 sont rédigés ; au §4.4.1, le réexamen d’un risque reste au régime projet, le passage au régime révisionné ayant été signalé en commentaire et résolu par l’auteur sans retouche du tableau 10

---

## C-094 — Le refus d'une tâche sans heure travaillée n'est pas borné

- **gravité** : majeur
- **emplacement** : §3.4.5.3, `WF-PLA-0010-A` ; §3.4.4 (texte d'introduction) ; `WF-INTF-0100-A`
- **citation** : « Une saisie qui laisserait une tâche sans aucune heure travaillée dans la semaine — ligne de main-d’œuvre ajoutée, rôle d’une ligne changé, calendrier d’un rôle modifié — est refusée, en nommant les rôles et les tâches en cause. »

**Constat.** Le refus est juste, mais trois choses restent à décider par celui qui l'implémente.

1. **Quelles tâches sont examinées ?** Une révision marquée conserve ses calendriers
   (WF-REV-0030) et n'est jamais affectée par le référentiel (WF-REF-0130) : seules les révisions
   en cours sont concernées, dans toutes leurs structures — principale, différentiels, devis
   propres des risques — ou dans la seule principale ? Le texte ne le dit pas.
2. **La modification d'un calendrier est une saisie du référentiel.** Le §3.4.4 pose qu'« une
   modification du référentiel n’impose jamais de retoucher un projet » ; ici, elle est refusée
   tant qu'un projet n'a pas été retouché, ce qui est l'inverse. Et le refus « nomme les tâches
   en cause » à un manager qui, selon WF-ADM-0110, ne doit pas pouvoir distinguer un projet qu'il
   ne peut pas consulter d'un projet inexistant.
3. **Les imports.** Un import de devis (WF-INTF-0100) change le rôle d'une ligne ou en ajoute une.
   La saisie fautive est-elle rejetée ligne par ligne au compte rendu (WF-INTF-0080), ou l'import
   entier est-il refusé ? Rien ne le dit, et WF-INTF-0100 ne cite pas ce motif de rejet.

**Proposition.** Dans WF-PLA-0010, remplacer la phrase citée par :

> Une saisie qui laisserait une tâche d’une révision en cours, dans l’une quelconque de ses
> structures, sans aucune heure travaillée dans la semaine est refusée en nommant les rôles et
> la tâche en cause : ligne de main-d’œuvre ajoutée ou rôle d’une ligne changé, par saisie comme
> par import, où la ligne est rejetée au compte rendu (WF-INTF-0080). La modification d’un
> calendrier du référentiel qui produirait le même effet est refusée en nommant les rôles et,
> pour chaque projet en cause, son libellé et son code, sans autre détail.

Et ajouter à la Vérif : « L’import d’un fichier de devis dont une ligne donnerait ce résultat
rejette cette ligne au compte rendu et applique les autres. La modification d’un calendrier qui
laisserait une tâche sans heure dans un projet que le manager ne peut pas consulter est refusée en
nommant ce projet par son libellé et son code. » Ajouter le motif de rejet à la Vérif de
WF-INTF-0100.

**Statut.** intégré

---

## C-095 — Le reste à engager ignore la réestimation d'une tâche non démarrée, et compte peut-être deux fois les provisions

- **gravité** : majeur
- **emplacement** : §3.4.5.5, `WF-RAE-0010-A` ; `WF-RAE-0040-A` ; `WF-RAE-0030-A`
- **citation** : « du montant réestimé de ses lignes si elle est démarrée, et du montant budgété de ses lignes, projeté sur son année de consommation courante, si elle n’est pas démarrée ; et des lignes de provision des risques identifiés à la date de calcul, pour leur montant. »

**Constat.** WF-RAE-0040 permet de « faire apparaître les tâches non démarrées pour les
réestimer », et le texte du §3.4.5.5.3 en fait un cas voulu : « d’autres doivent être réestimées
avant même d’avoir commencé ». Mais WF-RAE-0010 compte une tâche non démarrée pour son montant
budgété projeté, quoi qu'on ait saisi : la réestimation permise par la grille n'entre jamais au
reste à engager, et donc ni dans la projection du chef de projet, ni dans le plan de charge
(WF-DEV-0070). Un développeur qui suit WF-RAE-0010 rend WF-RAE-0040 sans effet ; un autre qui
suit WF-RAE-0040 contredit la Vérif de WF-RAE-0010.

Par ailleurs, la somme « pour chaque tâche […] de ses lignes » puis « et des lignes de provision »
compte deux fois une ligne de provision si celle-ci est portée par une tâche, ce qu'elle est
(§3.2.6, WF-RIS-0010). Il faut dire que les termes par tâche excluent les lignes de provision.

**Proposition.** Corps de WF-RAE-0010 :

> Le reste à engager d’un projet est la somme, pour chaque tâche de la structure principale de la
> révision courante et hors lignes de provision : de zéro si la tâche est terminée ; du montant
> réestimé de ses lignes si elle est démarrée, ou si elle ne l’est pas et que ses lignes ont été
> réestimées depuis la grille (WF-RAE-0040) ; et sinon du montant budgété de ses lignes, projeté
> sur son année de consommation courante ; et des lignes de provision des risques identifiés à
> la date de calcul, pour leur montant. Une ligne dont le montant budgété est nul — ajoutée après
> la référence — compte pour son montant réestimé quel que soit l’état de sa tâche.

Vérif, ajouter : « La réestimation à 120 d’une ligne budgétée à 100 sur une tâche non démarrée,
saisie depuis la grille, porte le reste à engager de 100 à 120. Un projet portant un risque de
provision 40 compte cette provision une fois. »

**Statut.** intégré avec écart : une rédaction unique de WF-RAE-0010 concilie C-095 et C-154

---

## C-096 — Le signalement du conflit avec une tâche manuelle renvoie à une exigence qui ne le décrit pas

- **gravité** : majeur
- **emplacement** : §3.4.5.3.3, `WF-PLA-0100-A` ; `WF-PLA-0020-A`
- **citation** : « Un prédécesseur qui ne peut pas finir à temps pour une tâche manuelle porte une marge négative, et le conflit est signalé (WF-PLA-0020). »

**Constat.** WF-PLA-0020 décrit les deux modes de planification et ne dit rien d'un signalement :
le renvoi tombe à vide. La Vérif de WF-PLA-0100 demande que le prédécesseur soit « signalé », sans
dire où — grille, Gantt, les deux — ni comment. Comme WF-IHM-0070 impose une échelle commune à
tous les signalements et les énumère, un signalement qui n'y figure pas est un signalement que
chaque écran inventera.

**Proposition.** Ajouter à WF-PLA-0020, corps :

> Lorsqu’un prédécesseur en mode automatique ne peut pas finir avant la date qu’impose une tâche
> en mode manuel, la tâche manuelle et ce prédécesseur sont signalés dans la grille de planning
> et dans le diagramme de Gantt, selon l’échelle commune de WF-IHM-0070 ; le signalement nomme
> la liaison en cause et disparaît dès que les dates le permettent.

Vérif de WF-PLA-0020, ajouter : « Une tâche manuelle datée avant la fin calculée de son
prédécesseur est signalée dans la grille et dans le Gantt, avec ce prédécesseur ; avancer la
tâche manuelle fait disparaître le signalement. » Et ajouter « conflit entre une tâche manuelle et
ses prédécesseurs (WF-PLA-0020) » à la liste des signalements de WF-IHM-0070.

**Statut.** intégré

---

## C-097 — Le glossaire définit encore le chemin critique par la seule marge nulle

- **gravité** : majeur
- **emplacement** : annexe A, entrées « Chemin critique » et « Marge totale » ; à rapprocher de `WF-PLA-0100-A`
- **citation** : « Désigne l'ensemble des tâches dont la marge totale est nulle : tout retard sur l'une d'elles retarde la fin du projet. » ; « le retard qu'elle peut prendre sans retarder la fin du projet. »

**Constat.** WF-PLA-0100 dit désormais « nulle ou négative », et fait porter une marge négative
au prédécesseur d'une tâche manuelle, qui ne retarde pas la fin du projet mais une date imposée.
Les deux entrées du glossaire décrivent l'ancienne règle : un développeur qui part du glossaire
n'affiche pas sur le chemin critique la tâche que la Vérif de WF-PLA-0100 y attend.

**Proposition.**

> **Chemin critique.** Désigne l'ensemble des tâches en mode automatique dont la marge totale est
> nulle ou négative : tout retard sur l'une d'elles retarde la fin du projet, ou une date imposée
> par une tâche en mode manuel (WF-PLA-0100).
>
> **Marge totale.** Désigne, pour une tâche en mode automatique, l'écart entre sa date au plus
> tard et sa date au plus tôt : le retard qu'elle peut prendre sans retarder la fin du projet ni
> une date imposée par une tâche en mode manuel. Elle est négative lorsque la tâche ne peut pas
> finir à temps pour une tâche manuelle qui la suit.

**Statut.** intégré

---

## C-098 — Aucune exigence ne dit quelle tâche porte la ligne de provision

- **gravité** : majeur
- **emplacement** : §3.2.6 « Risques », paragraphe « Nature de la provision » ; `WF-RIS-0010-A` ; `WF-PLA-0040-A`
- **citation** : « Faute de tâche qui lui revienne naturellement, cette ligne est portée par la tâche récapitulative du projet, à moins que l’utilisateur ne la rattache à la phase que le risque menace. »

**Constat.** « La tâche récapitulative du projet » n'existe dans aucun objet du document : une
structure de coûts est un arbre de tâches dont chacune a zéro ou un parent (figures 4 et 5), donc
une forêt, et le « nœud racine qui représente le projet » de WF-PLA-0110 est un artifice de
dessin, pas une tâche. WF-RIS-0010 dit seulement que le risque porte « une ligne de provision
dans la structure principale » ; aucune exigence ne dit sur quelle tâche elle est créée, ni si
l'utilisateur peut la déplacer, alors que la phrase du §3.2.6 le suppose. Trois choses en
dépendent : le filtre par sous-arbre de WF-DEV-0050, les totaux par poste de WF-DEV-0060, et
l'état de la tâche porteuse — WF-PLA-0040 garde une récapitulative démarrée « tant que [le reste
à engager de ses lignes propres] n’est pas nul », or une ligne de provision est calculée et ne se
réestime pas (WF-DEV-0020) : la tâche qui la porte ne peut pas être terminée tant que le risque
est identifié.

**Proposition.** Ajouter à WF-RIS-0010, corps :

> La ligne de provision est portée par la tâche de la structure principale que l’utilisateur
> désigne à la déclaration du risque, et peut être déplacée sur une autre ; à défaut de
> désignation, elle est portée par la première tâche de premier niveau de la structure. Elle
> n’entre pas dans l’état de la tâche qui la porte (WF-PLA-0040) : une récapitulative dont
> seules des lignes de provision gardent un reste à engager est terminée quand ses subordonnées
> le sont.

Vérif, ajouter : « Un risque déclaré sans désignation de tâche porte sa provision sur la première
tâche de premier niveau ; la ligne peut être déplacée sur une autre tâche de la structure
principale, et le total du devis est inchangé. » Et remplacer la phrase citée du §3.2.6 par :
« Cette ligne est portée par la tâche que l’utilisateur désigne, la phase que le risque menace
le plus souvent, et peut être déplacée (WF-RIS-0010). »

**Statut.** intégré

---

## C-099 — Le rattachement au lotissement s'ouvre aux feuilles, mais trois passages parlent encore de récapitulatives

- **gravité** : mineur
- **emplacement** : §3.4.5.4.1, `WF-DEV-0060-A` (Motif et Vérif) ; §3.4.5.2.1 (texte) ; `WF-PRJ-0030-A`
- **citation** : « Les totaux par poste se lisent par le rattachement d’une récapitulative au poste, posé par le squelette ou à la main » (Motif) ; « Sur un planning importé dont aucune récapitulative n’est rattachée à un poste, les totaux par poste sont absents plutôt que nuls ; après rattachement d’une récapitulative au poste 1, son total apparaît. » (Vérif)

**Constat.** Le corps de WF-DEV-0060 et WF-PLA-0130 ont été mis à jour pour une « tâche
rattachée », récapitulative ou feuille ; le Motif et la Vérif de WF-DEV-0060 sont restés à
« récapitulative ». Ce n'est pas faux, mais le testeur qui lit la Vérif ne teste pas le cas
nouveau. Par ailleurs, WF-PLA-0130 exige désormais que la tâche d'un lot soit dans le sous-arbre
de la tâche de son poste ; WF-PRJ-0030 engendre « une tâche récapitulative par poste et par
lot » sans dire que celle du lot est subordonnée à celle du poste, ce que la règle nouvelle
impose au squelette lui-même.

**Proposition.** Motif de WF-DEV-0060 : « par le rattachement d’une tâche au poste ». Vérif : « Sur
un planning importé dont aucune tâche n’est rattachée à un poste, les totaux par poste sont absents
plutôt que nuls ; après rattachement d’une récapitulative au poste 1, son total apparaît, et il
vaut celui de son sous-arbre ; après rattachement d’une feuille à un poste, le total de ce poste
est le montant des lignes de cette feuille. » Dans WF-PRJ-0030, corps : « une tâche
récapitulative par poste, une tâche récapitulative par lot subordonnée à celle de son poste,
toutes deux rattachées au poste ou au lot qu’elles représentent (WF-PLA-0130), une tâche feuille
par livrable sous celle de son lot ».

**Statut.** intégré

---

## C-100 — Deux formules d'avant le modèle : « planning/reste à engager » et « associe un planning à un devis »

- **gravité** : mineur
- **emplacement** : annexe A, entrée « Revue périodique » ; §2.1, paragraphe « Construction d’une offre »
- **citation** : « marque une nouvelle révision planning/reste à engager et importe les nouveaux coûts réels » ; « Chaque révision associe un planning à un devis. »

**Constat.** Depuis C-024, une révision n'est plus un couple planning/devis mais un instantané
qui porte des structures de coûts, le planning et le devis étant deux vues du même arbre
(§3.2.4, §3.5.1). Les deux formules citées sont les dernières à employer l'ancien vocabulaire, et
la première est dans le glossaire, qui fait foi pour les termes.

**Proposition.**

> **Revue périodique.** Désigne l'opération au cours de laquelle un utilisateur habilité met à
> jour le planning et le reste à engager de la révision en cours, réexamine les risques, importe
> les nouveaux coûts réels, puis marque la révision. Ces données permettent de mettre à jour les
> indicateurs du projet.

§2.1 : « Chaque révision porte le planning et le devis de l’offre, deux vues d’un même arbre de
tâches. »

**Statut.** intégré

---

## C-101 — La grille de planning n'affiche pas tous les attributs que WF-PLA-0130 dit affichés

- **gravité** : mineur
- **emplacement** : §3.4.5.3.2, `WF-PLA-0080-A` ; `WF-PLA-0130-A` (Vérif)
- **citation** : « avec pour chacune : son libellé, sa description, sa durée, ses dates, son mode de planification, son état, signalé par une marque visuelle et non par une colonne, pour une récapitulative, son avancement physique, sa marge totale, ses prédécesseurs. »

**Constat.** La Vérif de WF-PLA-0130 commence par « Chacun de ces attributs est affiché dans la
grille de planning » et finit par « La marge totale, la criticité et l’avancement physique
s’affichent ». La liste des colonnes de WF-PLA-0080 ne comporte ni la criticité, ni les dates de
démarrage et de terminaison, ni le rattachement au poste ou au lot. Les deux exigences sont
vérifiées par le même écran, et l'une des deux Vérif échouera.

**Proposition.** Dans WF-PLA-0080, après « sa marge totale, » : « son appartenance au chemin
critique, ses dates de démarrage et de terminaison, son rattachement à un poste ou à un lot
(WF-PLA-0130), ».

**Statut.** intégré

---

## C-102 — Le plan de charge calcule une charge « sur les montants »

- **gravité** : mineur
- **emplacement** : §3.4.5.4.4, `WF-DEV-0070-A`
- **citation** : « la charge des lignes de main-d’œuvre, calculée, au choix, sur les montants budgétés de la révision de référence, sur les montants réestimés d’une révision marquée, ou sur ceux de la révision en cours. »

**Constat.** Une charge est un nombre d'heures (glossaire), saisi sur la ligne ; un montant en
découle par le taux horaire. Lire « calculée sur les montants » invite à diviser un montant par un
taux pour retrouver des heures, ce qui n'est pas le sens. Ce que l'exigence veut dire, c'est que
la charge prise est celle de la référence, celle réestimée d'une révision marquée, ou celle de la
révision en cours.

**Proposition.** « la charge des lignes de main-d’œuvre, prise, au choix, dans la révision de
référence, dans une révision marquée pour sa charge réestimée, ou dans la révision en cours. »

**Statut.** intégré

---

## C-103 — Deux ponctuations qui coupent une énumération

- **gravité** : mineur
- **emplacement** : §3.4.2.1, `WF-ADM-0050-A` et `WF-ADM-0040-A`
- **citation** : « un avatar facultatif. son origine : compte local, » ; « les tâches ajoutées après la révision de référence La langue de l'interface »

**Constat.** Dans WF-ADM-0050, le point après « facultatif » coupe la liste des attributs : « son
origine » se lit comme une phrase à part et un lecteur pressé ne la compte pas parmi les
attributs. Dans WF-ADM-0040, le point manquant soude deux phrases.

**Proposition.** « un avatar facultatif, et son origine : compte local, » ; « après la révision de
référence. La langue de l'interface ».

**Statut.** intégré avec écart : le point de WF-ADM-0040 est venu avec la rédaction de C-159
