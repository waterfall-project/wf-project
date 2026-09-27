---
revue_du: 2026-09-26
sur: waterfall-spec.md généré le 2026-09-26 (commit 9a6c6e1)
revue_par: Claude Fable 5.1
perimetre: §3 complet — accent sur les derniers blocs intégrés (FBS-1, FBS-2, FBS-3.4, FBS-4.8) et sur ce que le portefeuille demande aux blocs projet
---

# Revue du 2026-09-26 — la partie fonctionnelle complète

## Suivi des revues précédentes

Un seul constat restait à traiter, C-053. Il est **résolu en partie** :

- le renvoi « au paragraphe suivant » du §3.1.4 a disparu, et la Vérif de WF-INTF-0010 dit
  désormais « du tableau des flux (FLX-01 à FLX-07) » : réglé ;
- les renvois d'annexe reprennent toujours le titre entier, en neuf endroits (§3.1.2 deux fois,
  WF-INTF-0090 à WF-INTF-0140, §3.2 deux fois), dont « définit par ANNEXE B », « de ANNEXE B » et
  « de l' ANNEXE B » : toujours ouvert.

## Réponse à la question posée

La partie fonctionnelle tient. Les 138 exigences se renvoient les unes aux autres sans référence
morte, chaque fonction de l'arborescence a ses exigences, et les exemples chiffrés des Vérif
(WF-PTF-0020, WF-IND-0040, WF-IND-0050, WF-RIS-0050) sont justes.

Ce que cette revue trouve tient en une phrase : **le portefeuille consomme des dates que les
blocs projet ne produisent pas.** Le bloc FBS-2 raisonne par période — projets terminés d'une
période, offres perdues ou gagnées dans la période, provisions survenues ou écartées dans la
période, coûts importés depuis la dernière revue, portefeuille recalculé à une date passée — et
quatre de ces dates n'existent nulle part : les transitions d'état d'un projet (C-054), les
changements d'état d'un risque (C-057), les imports de coûts réels (C-058), et l'état qu'avait un
projet à une date passée (C-055). C'est le même défaut que C-043 pour les tâches, remonté d'un
niveau. Aucun n'est bloquant, tous sont majeurs, et ils se corrigent chacun par un attribut ou
une phrase.

Le reste est de la cohérence entre blocs voisins : une contradiction entre WF-PTF-0100 et
WF-IND-0010 sur les projets en chiffrage (C-056), trois points du bloc d'administration où un
développeur choisirait seul (C-059 à C-061), et des mineurs.

## Constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-054 | majeur | §3.3.2, §3.4.5.2 | Les transitions d'état d'un projet ne sont pas datées, le portefeuille en a besoin | intégré |
| C-055 | majeur | §3.4.3, WF-PTF-0010 | Portefeuille à une date passée : quels indicateurs et quel état du projet ? | intégré |
| C-056 | majeur | §3.4.3.6, WF-PTF-0100 | Les projets en chiffrage n'ont pas de projection de décaissement à pondérer | intégré |
| C-057 | majeur | §3.4.5.6, WF-RIS-0010 | Les changements d'état d'un risque et ses réexamens ne sont pas datés | intégré |
| C-058 | majeur | §3.4.5.7 | Aucun import de coûts réels n'est daté | intégré |
| C-059 | majeur | §3.4.2.1, WF-ADM-0070 | La resynchronisation désactive aussi les comptes locaux, et peut désactiver le dernier administrateur | intégré |
| C-060 | majeur | §3.4.2.2, WF-ADM-0100 | « Par fonction de l'arborescence » sans dire à quel niveau | intégré |
| C-061 | majeur | §3.1.3, WF-INTF-0030 | Sur une installation neuve, personne ne peut sauvegarder | intégré |
| C-062 | mineur | §3.4.2.2, WF-ADM-0090 | La Vérif teste un refus que le corps n'énonce pas | intégré |
| C-063 | mineur | §3.4.2 | « Aucune d'elles ne touche une donnée de projet » — sauf la restauration | intégré |
| C-064 | mineur | glossaire | Projeté ou projection à terminaison ; trois entrées à ajouter, une à retirer | intégré |
| C-065 | mineur | §3.4.5.8.4, §3.4.5.8.5 | Les écarts de coût et de délai ne sont présentés par aucune exigence projet | intégré |
| C-066 | mineur | §3.4.5.5, §3.4.5.8 | Un renvoi par numéro de paragraphe, un titre en désaccord avec la figure, une liste qui a fusionné deux puces | intégré |

---

## C-054 — Les transitions d'état d'un projet ne sont pas datées, le portefeuille en a besoin

- **gravité** : majeur
- **emplacement** : §3.3.2 (WF-CYC-0010 à WF-CYC-0110) ; §3.4.5.2, WF-PRJ-0080 ; §3.4.3, WF-PTF-0010 et WF-PTF-0050
- **citation** : « Un projet porte : un libellé, une description facultative, un code projet (WF-PRJ-0010), un état du cycle de vie (WF-CYC-0010), un taux d'inflation (WF-PRJ-0040), une probabilité de gain (WF-PRJ-0090), facultativement, la date de réception de sa commande. » (WF-PRJ-0080)

**Constat.** L'état du cycle de vie est un attribut, pas un événement : rien ne dit quand un
projet est passé à Chiffrage, à En cours, à Terminé, à Perdu ou à Abandonné. La date de
réception de la commande est facultative et « n'est exigée par aucune transition » : elle ne
peut pas tenir ce rôle.

Or le portefeuille raisonne par période, et trois de ses exigences supposent ces dates :

- WF-PTF-0010 retient « les projets terminés d'une période » : il faut la date du passage à
  Terminé ;
- WF-PTF-0050 somme « les coûts réels […] des projets terminés sur la période choisie », et
  calcule le taux de transformation sur « les offres marquées perdues ou passées en cours sur la
  période » : il faut les dates des passages à Perdu et à En cours ;
- WF-PTF-0010 calcule le portefeuille « à une date passée » : il faut savoir dans quel état était
  chaque projet à cette date (voir C-055).

Sans elles, un développeur prendra la date de marquage de la révision de référence pour le
passage à En cours, et n'aura rien pour les trois sorties.

Deuxième point, dans WF-PTF-0050 : le taux de transformation compte des projets Perdus, que le
périmètre de WF-PTF-0010 ne contient jamais — il n'admet que En cours, Chiffrage et Terminé. Ce
n'est pas faux, mais il faut le dire.

**Proposition.** Une exigence de plus au §3.3.2, après WF-CYC-0090 :

> **WF-CYC-0130-A — Datation des transitions.** Chaque transition d'état d'un projet est datée
> du jour où elle se produit, et l'historique de ses états est consultable depuis le projet. Ces
> dates ne sont pas modifiables.
>
> Motif : les statistiques de portefeuille se calculent par période — projets terminés,
> offres perdues ou gagnées, portefeuille à une date passée — et n'ont de sens que si chaque
> changement d'état est situé dans le temps par le fait qui l'a produit, non par une saisie.
>
> Vérif : après passage d'un projet à En cours puis à Terminé, l'historique présente les deux
> transitions avec leur date. Un projet passé à Perdu le 15 mars compte parmi les offres closes
> de mars et d'aucun autre mois.

Ajouter « les dates de ses transitions d'état (WF-CYC-0130) » à la liste des attributs de
WF-PRJ-0080. Et compléter WF-PTF-0050 : « […] la part des offres sorties de l'état Chiffrage sur
la période — vers En cours ou vers Perdu, qu'elles appartiennent ou non au périmètre — qui sont
passées à En cours ».

**Statut.** intégré

---

## C-055 — Portefeuille à une date passée : quels indicateurs et quel état du projet ?

- **gravité** : majeur
- **emplacement** : §3.4.3, WF-PTF-0010 ; §3.4.3.3, WF-PTF-0070
- **citation** : « Elle se calcule à une date : au jour courant, chaque projet contribue par sa révision en cours ; à une date passée, par sa dernière révision marquée antérieure à cette date. »

**Constat.** La phrase dit quelle révision on prend ; elle ne dit pas à quelle date on calcule
ses indicateurs. WF-IND-0010 pose que les indicateurs d'une révision marquée se calculent « à
sa date de marquage » et que le coût réel à une date ne compte que les pièces antérieures. Pour un
portefeuille au 31 mars dont un projet a marqué sa dernière revue le 10 mars, deux lectures sont
possibles : les indicateurs de cette révision tels qu'ils étaient au 10 mars, ou les structures
de cette révision confrontées au coût réel au 31 mars. Les deux donnent des indices différents,
et WF-PTF-0070 en trace l'évolution trimestre par trimestre.

La première lecture est la seule cohérente avec WF-IND-0010 — « les indicateurs d'une révision
marquée ne changent pas après son marquage » — et c'est elle qui rend la Vérif de WF-PTF-0070
vraie sans effort.

Second point, lié à C-054 : à une date passée, un projet aujourd'hui Terminé était En cours. S'il
sort du périmètre « en cours » parce qu'on lit son état d'aujourd'hui, l'évolution trimestrielle
ne garde que les survivants, et l'indice agrégé s'améliore à mesure que les projets se
terminent. Le périmètre doit se lire dans l'état qu'avait chaque projet à la date de calcul.

**Proposition.** Remplacer la phrase citée par : « Elle se calcule à une date. Au jour courant,
chaque projet contribue par sa révision en cours et ses indicateurs au jour courant. À une date
passée, chaque projet contribue par sa dernière révision marquée antérieure à cette date, avec
les indicateurs de cette révision tels que WF-IND-0010 les fixe à sa date de marquage, et il est
retenu dans le périmètre selon l'état qu'il avait à cette date (WF-CYC-0130). »

Ajouter à la Vérif : « Un projet terminé aujourd'hui, en cours à une date passée, compte parmi
les projets en cours du portefeuille calculé à cette date. »

**Statut.** intégré

---

## C-056 — Les projets en chiffrage n'ont pas de projection de décaissement à pondérer

- **gravité** : majeur
- **emplacement** : §3.4.3.6, WF-PTF-0100 ; §3.4.5.8, WF-IND-0010 ; §3.4.5.8.9, WF-IND-0120
- **citation** : « les décaissements à venir, somme des projections des projets, les projets en chiffrage étant pondérés par leur probabilité de gain lorsqu'ils sont inclus » (WF-PTF-0100) ; « Les indicateurs projets ne sont calculés qu'à partir de l'état En cours ; avant, seuls les indicateurs de devis sont disponibles. » (WF-IND-0010)

**Constat.** WF-PTF-0100 somme les projections de décaissement (WF-IND-0120) des projets du
périmètre, en pondérant ceux en chiffrage. Mais WF-IND-0120 est un indicateur projet, donc
inexistant avant En cours ; et il étale « le montant réestimé de chaque ligne du reste à
engager », qu'un projet en chiffrage n'a pas. Il n'y a rien à pondérer. Le plan de charge agrégé
(WF-PTF-0060) a réglé le même cas en disant explicitement « sur le devis pondéré […] pour les
projets en chiffrage ».

**Proposition.** Soit exclure les projets en chiffrage de cette vue, soit — ce que je
recommande, par symétrie avec WF-PTF-0060 — définir leur contribution. Dans le corps de
WF-PTF-0100, remplacer « les projets en chiffrage étant pondérés par leur probabilité de gain
lorsqu'ils sont inclus » par : « pour un projet en chiffrage, lorsqu'il est inclus, la
projection est obtenue par la règle de WF-IND-0120 appliquée aux lignes de son devis courant, et
pondérée par sa probabilité de gain ».

**Statut.** intégré

---

## C-057 — Les changements d'état d'un risque et ses réexamens ne sont pas datés

- **gravité** : majeur
- **emplacement** : §3.4.5.6, WF-RIS-0010 et WF-RIS-0020 ; §3.4.5.6.1, WF-RIS-0040 ; §3.4.3.5, WF-PTF-0090 ; §3.4.3.7, WF-PTF-0110
- **citation** : « Il conserve l'historique de ses réexamens : à chaque revue, la probabilité et la gravité retenues. » (WF-RIS-0010) ; « et, sur la période choisie, le montant des provisions des risques survenus face à celui des risques écartés » (WF-PTF-0090)

**Constat.** Trois choses manquent au même endroit.

- **L'état n'est pas dans l'historique.** WF-RIS-0020 dit que « la probabilité et l'état de
  chaque risque sont réexaminés à chaque revue », mais l'historique de WF-RIS-0010 ne conserve
  que la probabilité et la gravité. Rien ne dit quand un risque a été écarté. La survenance est
  datée par ricochet — elle produit une révision marquée (WF-RIS-0060) —, l'écart ne l'est pas.
  WF-PTF-0090 compte pourtant « sur la période choisie » les provisions des risques écartés.
- **Le réexamen n'est pas défini.** WF-RIS-0040 affiche « la date de son dernier réexamen »,
  WF-PTF-0110 signale les risques « qui n'ont pas été réexaminés depuis leur dernière révision
  marquée ». Un réexamen est-il toute modification du risque, ou un acte explicite par lequel on
  confirme une probabilité qu'on ne change pas ? Si c'est la première lecture, un risque qu'on a
  regardé et jugé inchangé apparaît comme non réexaminé à chaque revue ; si c'est la seconde,
  il faut un geste dans la grille. Un développeur choisira.
- **L'historique dit « à chaque revue »**, ce qui laisse entendre qu'il n'y a qu'un réexamen par
  revue, alors qu'un risque peut être réévalué entre deux revues.

**Proposition.** Dans WF-RIS-0010, remplacer la phrase citée par : « Il conserve l'historique de
ses réexamens : la date de chacun, et la probabilité, la gravité et l'état retenus. Un réexamen
est l'acte par lequel un utilisateur confirme ou modifie la probabilité et l'état d'un risque ;
il est daté du jour où il est fait. » Ajouter à la Vérif : « La confirmation d'un risque sans
modification produit un réexamen daté. »

WF-PTF-0090 et WF-PTF-0110 n'ont alors plus rien à préciser : un risque est survenu ou écarté à
la date du réexamen qui lui a donné cet état, et « non réexaminé depuis la dernière révision
marquée » se lit sur la date du dernier réexamen.

**Statut.** intégré

---

## C-058 — Aucun import de coûts réels n'est daté

- **gravité** : majeur
- **emplacement** : §3.4.5.7, WF-CRE-0010 à WF-CRE-0040 ; §3.1.4, WF-INTF-0140 ; §3.4.3.7, WF-PTF-0110
- **citation** : « ceux dont aucun coût réel n'a été importé depuis leur dernière révision marquée » (WF-PTF-0110)

**Constat.** Une ligne de coût porte une date de pièce, qui est celle de l'ERP, pas celle de
l'import. Aucune exigence ne conserve la date à laquelle un import a été fait, ni ne l'affiche.
Le signal de WF-PTF-0110 ne peut donc pas être calculé — ou il le sera sur la date de pièce la
plus récente, ce qui est autre chose : un import fait hier de pièces datées d'il y a trois mois
est un import fait hier.

Le même manque gêne le chef de projet lui-même : la consultation des coûts réels (WF-CRE-0040) ne
dit pas de quand datent les chiffres qu'elle montre.

**Proposition.** Une exigence de plus au §3.4.5.7 :

> **WF-CRE-0050-A — Journal des imports.** Chaque import de coûts réels est journalisé avec sa
> date, son auteur, la période extraite et le nombre de lignes créées, mises à jour et
> ignorées. La date du dernier import est présentée dans la consultation des coûts réels.
>
> Motif : la date d'une pièce dit quand la dépense a eu lieu, celle de l'import dit de quand
> datent les chiffres qu'on lit. Ce sont deux questions différentes, et la seconde est celle que
> pose la santé du pilotage (WF-PTF-0110).
>
> Vérif : après un import, le journal présente une entrée datée du jour avec ses comptes de
> lignes, et la consultation des coûts réels affiche cette date comme celle du dernier import.

**Statut.** intégré

---

## C-059 — La resynchronisation désactive aussi les comptes locaux, et peut désactiver le dernier administrateur

- **gravité** : majeur
- **emplacement** : §3.4.2.1, WF-ADM-0070 ; §3.4.2.2, WF-ADM-0120
- **citation** : « met à jour ces trois attributs sur les comptes existants, et désactive les comptes que l'annuaire ne connaît plus » (WF-ADM-0070)

**Constat.** Un compte créé dans Waterfall n'est, par construction, pas connu de l'annuaire. Lu
à la lettre, WF-ADM-0070 le désactive à la première resynchronisation. WF-ADM-0050 distingue
pourtant les deux origines précisément pour dire « qui fait foi pour l'identité », et
WF-ADM-0140 fait s'authentifier les comptes locaux dans Waterfall : ils doivent survivre à la
synchronisation. Le corps ne le dit pas.

Second cas : si le dernier compte portant la permission de gérer les comptes est retiré de
l'annuaire, la resynchronisation le désactive, et WF-ADM-0120 — qui refuse cette désactivation
— ne dit pas ce que fait un traitement automatique face à ce refus.

**Proposition.** Dans le corps de WF-ADM-0070 : « […] met à jour ces trois attributs sur les
comptes importés existants, et désactive les comptes importés que l'annuaire ne connaît plus.
Les comptes créés dans Waterfall ne sont pas concernés. Un compte que WF-ADM-0120 interdit de
désactiver est conservé actif et signalé dans le compte rendu de la synchronisation. » Ajouter à
la Vérif : « Un compte créé dans Waterfall reste actif après resynchronisation. Le dernier
compte administrateur, retiré de l'annuaire, reste actif et la synchronisation le signale. »

**Statut.** intégré

---

## C-060 — « Par fonction de l'arborescence » sans dire à quel niveau

- **gravité** : majeur
- **emplacement** : §3.4.2.2, WF-ADM-0100
- **citation** : « Les permissions sont définies par fonction de l'arborescence fonctionnelle, à deux niveaux — consulter, modifier — »

**Constat.** L'arborescence a trois profondeurs : FBS-4, FBS-4.3, FBS-4.3.5. Selon le niveau
retenu, le catalogue compte une quinzaine de couples ou une cinquantaine, et un rôle « planning en
consultation, arborescence de tâches en modification » est possible ou ne l'est pas. La Vérif —
« Chaque fonction de l'arborescence est représentée par ses deux permissions » — hérite de la
même imprécision.

Le corps liste aussi « gérer le référentiel, gérer les comptes et les rôles, sauvegarder et
restaurer la plateforme » parmi les permissions distinctes, alors que FBS-3, FBS-1.1, FBS-1.2 et
FBS-1.4 ont déjà, par la première règle, leur couple consulter/modifier. Il faut dire si ces
permissions remplacent le couple pour ces fonctions ou s'y ajoutent.

**Proposition.** « Les permissions sont définies par fonction de second niveau de l'arborescence
fonctionnelle (FBS-x.y), à deux niveaux — consulter, modifier —, la permission d'une fonction
couvrant ses sous-fonctions. Pour les fonctions d'administration et de référentiel (FBS-1 et
FBS-3), la permission de modifier tient lieu de permission de gérer. S'y ajoutent des
permissions distinctes pour les actions irréversibles ou structurantes : marquer une révision,
désigner la révision de référence, déclarer une sortie du cycle de vie, déclarer un risque
survenu, exclure une ligne de coût du périmètre suivi, restaurer la plateforme. » Vérif : « Chaque
fonction de second niveau est représentée par ses deux permissions […] ». WF-ADM-0120 se lit
alors « la permission de modifier la gestion des utilisateurs et celle des rôles (FBS-1.1,
FBS-1.2) » — ou reste tel quel si l'auteur préfère garder les permissions « gérer » en plus du
couple : l'important est de trancher.

**Statut.** intégré

---

## C-061 — Sur une installation neuve, personne ne peut sauvegarder

- **gravité** : majeur
- **emplacement** : §3.1.3, WF-INTF-0020 et WF-INTF-0030 ; §3.4.2.2, WF-ADM-0010
- **citation** : « Waterfall doit permettre à un utilisateur habilité de gérer les comptes utilisateurs et les rôles d'habilitation, et de consulter l'état de fonctionnement du système. Le rôle prédéfini « administrateur » accorde ces permissions. » (WF-INTF-0030)

**Constat.** WF-ADM-0010 définit le rôle prédéfini « administrateur » par les usages de
WF-INTF-0030, qui ne mentionne ni la sauvegarde ni la restauration (FBS-1.4, ajoutées depuis).
Sur une installation neuve, aucun des trois rôles livrés ne porte donc la permission de
sauvegarder : il faut composer un rôle avant la première sauvegarde, ce qui est exactement ce
que WF-ADM-0010 veut éviter.

Même retard, moins grave, dans WF-INTF-0020 : la Vérif ouvre « la zone d'indicateurs agrégés
(FBS-2.3) », qui n'est plus qu'une des sept vues du portefeuille.

**Proposition.** WF-INTF-0030, corps : « […] de gérer les comptes utilisateurs et les rôles
d'habilitation, de consulter l'état de fonctionnement du système, et de sauvegarder et restaurer
la plateforme. » Vérif : « […] ouvre l'écran d'état du système (FBS-1.3) et déclenche une
sauvegarde (FBS-1.4). » WF-INTF-0020, Vérif : « et ouvre les vues du portefeuille (FBS-2),
lesquelles portent sur au moins deux projets ».

**Statut.** intégré

---

## C-062 — WF-ADM-0090 : la Vérif teste un refus que le corps n'énonce pas

- **gravité** : mineur
- **emplacement** : §3.4.2.2, WF-ADM-0090
- **citation** : « La suppression d'un rôle est refusée tant qu'un compte le porte. » (Vérif)

**Constat.** Le corps dit qu'un utilisateur habilité peut « créer, modifier, renommer et
supprimer des rôles » sans condition ; la Vérif teste une condition. C'est la règle inverse de
C-048.

**Proposition.** Ajouter au corps, après « attribuer ou retirer des rôles aux comptes » : « Un
rôle ne peut être supprimé tant qu'un compte le porte. »

**Statut.** intégré

---

## C-063 — « Aucune d'elles ne touche une donnée de projet » — sauf la restauration

- **gravité** : mineur
- **emplacement** : §3.4.2, introduction du bloc
- **citation** : « Aucune d'elles ne touche une donnée de projet. »

**Constat.** La phrase date d'avant le §3.4.2.4. La restauration (WF-ADM-0160) « remplace
l'intégralité de la base et du stockage », ce qui touche toutes les données de projet à la fois.

**Proposition.** « Aucune d'elles ne modifie une donnée de projet en particulier ; la
restauration les remplace toutes ensemble, sans en distinguer aucune. »

**Statut.** intégré

---

## C-064 — Projeté ou projection à terminaison ; trois entrées à ajouter, une à retirer

- **gravité** : mineur
- **emplacement** : annexe A ; §3.4.5.8.2, WF-IND-0050 ; §3.4.3.1, WF-PTF-0040
- **citation** : « Projeté à terminaison. Désigne l'estimation du coût total du projet à son terme. Waterfall en présente trois […] (WF-IND-0050). » (glossaire) ; « Projections à terminaison » (titre de WF-IND-0050)

**Constat.**
- Le glossaire dit « projeté à terminaison » (cinq occurrences dans le corps), l'exigence qui le
  définit et le portefeuille disent « projection à terminaison » (sept occurrences). Le glossaire
  renvoie lui-même à WF-IND-0050, qui emploie l'autre mot.
- « Devis de référence » n'est employé nulle part dans le corps du document.
- « Taux de transformation » est employé trois fois (WF-PTF-0050) et n'est pas défini, alors que
  « Carnet » et « Pipeline », introduits par la même exigence, le sont.
- « Portefeuille » n'a pas d'entrée, alors que le mot désigne désormais un périmètre précis
  (WF-PTF-0010) et non l'ensemble des projets.

**Proposition.** Renommer l'entrée « Projection à terminaison » et aligner les cinq occurrences
de « projeté ». Retirer « Devis de référence », ou l'employer là où l'on écrit « devis de la
révision de référence ». Ajouter :

> **Portefeuille.** Désigne l'ensemble des projets retenus par le périmètre d'une vue
> multi-projets : les projets en cours, éventuellement les projets en chiffrage, et les projets
> terminés d'une période (WF-PTF-0010).
>
> **Taux de transformation.** Désigne, sur une période, la part des offres sorties de l'état
> Chiffrage qui sont passées à En cours plutôt qu'à Perdu (WF-PTF-0050).

**Statut.** intégré

---

## C-065 — Les écarts de coût et de délai ne sont présentés par aucune exigence projet

- **gravité** : mineur
- **emplacement** : §3.4.5.8.4, WF-IND-0070 ; §3.4.5.8.5, WF-IND-0080 ; §3.4.3.3, WF-PTF-0070
- **citation** : « les écarts de coût et de délai cumulés » (WF-PTF-0070)

**Constat.** Le portefeuille agrège des écarts de coût et de délai que le glossaire définit,
mais qu'aucune exigence projet ne calcule ni n'affiche : ils n'apparaissent que dans le Motif de
WF-IND-0110, comme lecture d'un graphique. Le portefeuille somme donc une grandeur que le projet
ne présente pas. Ce n'est pas ambigu — le glossaire fixe la formule et le signe — mais c'est un
trou dans la règle « un concept, un propriétaire ».

**Proposition.** Ajouter au corps de WF-IND-0070 : « Il est présenté avec l'écart de coût,
différence de la valeur acquise et du coût réel. » Et à WF-IND-0080 : « Il est présenté avec
l'écart de délai, différence de la valeur acquise et de la valeur planifiée. » Une phrase de
Vérif chacun : « Une valeur acquise de 400 pour un coût réel de 500 donne un écart de −100. »

**Statut.** intégré

---

## C-066 — Un renvoi par numéro de paragraphe, un titre en désaccord avec la figure, une liste qui a fusionné deux puces

- **gravité** : mineur
- **emplacement** : §3.4.5.5 (introduction et titre du §3.4.5.5.2) ; §3.4.5.8 (introduction)
- **citation** : « C'est le Kanban qui fait passer une tâche du premier cas au deuxième (§3.4.5.5.2) » ; « Démarrage de tache - Kanban » (titre) ; « FBS-4.5.3 Kanban - Démarrage des tâches » (figure) ; « La valeur acquise, ce qui l'a été ; le coût réel, ce que cela a coûté. »

**Constat.**
- Le renvoi « (§3.4.5.5.2) » est le seul du §3.4 à désigner un paragraphe par son numéro plutôt
  que par son code FBS, contre la règle du §3.4.1. Les renvois vers le §3.2 restent légitimes,
  ce chapitre n'ayant pas de codes.
- Le titre du §3.4.5.5.2 dit « Démarrage de tache - Kanban », la figure de FBS-4.5 dit « Kanban -
  Démarrage des tâches ». Les autres titres du §3.4 reprennent le libellé de leur nœud.
- L'introduction du §3.4.5.8 annonce « quatre grandeurs » et les présente en quatre puces, mais
  la valeur acquise et le coût réel partagent la troisième, et le reste à engager — qui « y
  ajoute » un cinquième regard — occupe la quatrième comme s'il était l'une des quatre.

**Proposition.** « (FBS-4.5.3) » ; titre « Kanban - Démarrage des tâches » ; et cinq puces, ou
quatre puces suivies de la phrase sur le reste à engager hors liste.

**Statut.** intégré — titre et puces corrigés ; le renvoi « (§3.4.5.5.2) » est un champ Word que l'auteur conserve (sans objet)

---

## Remarque hors constats

L'exemple d'exigence du §1.3.1 (WF-EXAMP-0010-A) est parsé par le build comme une exigence :
il porte le code FBS-1.1, il entre dans le compte des 139 et dans l'index. Ce n'est pas un défaut
du document — l'exemple est à sa place — mais du build, qui devrait ignorer les tableaux du
chapitre 1. À corriger dans `tools/build.py`, pas dans Word. La partie fonctionnelle compte donc
138 exigences.
