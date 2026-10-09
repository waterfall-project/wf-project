---
revue_du: 2026-09-19
sur: waterfall-spec.md généré le 2026-09-19 (commit f405d74)
revue_par: Claude Opus 5
perimetre: document complet (révision A)
---

# Revue du 2026-09-19 — document complet

## Suivi de la revue du 2026-09-17

| # | Constat | État constaté | Ce qui a changé |
|---|---|---|---|
| C-001 | Boucle de pilotage vers la révision de référence | sans objet | La figure du flux de travail a été retirée du document. |
| C-002 | « Cout réel » incluant les engagements | résolu | La définition ne cite plus les engagements. Le sujet de fond est inscrit en PO-01. |
| C-003 | États sans transitions | résolu | Diagramme d'état et exigences WF-CYC-0010 à 0110. |
| C-004 | Composants internes dans le diagramme de contexte | résolu | Base de données, cache et stockage ont été retirés. |
| C-005 | Chaîne SAP → Excel → Waterfall | résolu | FLX-07, FLX-08 et le motif de WF-INTF-0140. |
| C-006 | Tableau des flux vide | résolu | Tableaux 4 et 5, FLX-01 à FLX-18. |
| C-007 | Termes non définis | résolu en partie | Sigles et définitions ajoutés. PBS est défini comme sigle, mais aucune arborescence produit n'existe : les champs PBS restent à « TBD ». |
| C-008 | Codes de domaines insuffisants | résolu pour l'existant | INTF, ADM, CYC et DEV couvrent toutes les exigences écrites. |
| C-009 | Terminologie et coquilles | résolu en partie | La coquille « ésigne » est corrigée. Le reste est repris en C-022. |
| C-010 | Synthèse de l'état d'avancement | informatif | Les sections §3.1 et §3.3 sont rédigées. Les §3.2, §3.4 et §4 restent à écrire. |

## Nouveaux constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-011 | majeur | §3.1.1 | Des renvois par numéro de section désignent désormais d'autres sections | intégré |
| C-012 | majeur | §3.1.2 | Des renvois entre exigences MS Project ont été décalés par la renumérotation | intégré |
| C-013 | majeur | §3.4.5.4 | WF-DEV-0010 vérifie encore une condition que son corps ne pose plus | intégré |
| C-014 | majeur | §3.3.1 | Le paragraphe sur les prérequis n'a pas d'introduction et se contredit sur l'inflation | intégré |
| C-015 | majeur | §3.3.2 | WF-CYC-0040 n'est pas vérifiable tant que les paramètres requis ne sont pas listés | sans objet : l'état Initialisé et WF-CYC-0040 ont été retirés (C-028) |
| C-016 | majeur | §3.1.2, §3.3.2 | Un import sans révision en cours d'élaboration n'a pas de comportement défini | intégré |
| C-017 | majeur | §1.3 | Les impacts d'un risque sont décrits comme des « lignes de coût », c'est-à-dire des coûts réels | intégré |
| C-018 | majeur | §1.3 | « Charge » est employé dans deux sens | intégré |
| C-019 | mineur | §3.1.2, §3.1.3, §3.3.2 | Des erreurs de copie relevées le 2026-09-18 ne sont pas corrigées | intégré |
| C-020 | mineur | §3.1, §3.4.2 | Des champs FBS restent vides alors que l'arborescence existe | intégré |
| C-021 | mineur | §1.4.1 | L'exemple d'exigence réutilise un identifiant réel | intégré |
| C-022 | mineur | document | Écarts de terminologie et coquilles restants | intégré |
| C-023 | mineur | §1.3, §2 | Des passages supposent le point ouvert PO-01 résolu | reporté : passages rattachés à PO-01 |

---

## C-011 — Des renvois par numéro de section désignent désormais d'autres sections

- **gravité** : majeur
- **emplacement** : §3.1.1, texte d'introduction ; WF-INTF-0010, 0020 et 0030, champ Vérif
- **citation** : « les fonctions de planification (§3.3.4.2), de chiffrage (§3.3.4.3), de gestion des risques (§3.3.4.5) »

**Constat.** L'insertion des §3.2 et §3.3 a décalé le découpage fonctionnel de §3.3 à §3.4. Neuf renvois écrits à la main pointent maintenant vers d'autres sections : §3.3.2, cité par WF-INTF-0020, est devenu le cycle de vie d'un projet, et §3.3.1.2, cité par le texte du §3.1.1, est devenu un titre qui n'existe plus. Un lecteur qui suit ces renvois arrive au mauvais endroit, sans que rien ne l'en avertisse.

**Proposition.** Remplacer chaque renvoi par le code FBS de la fonction, qui ne bouge pas :

| Où | Actuel | Remplacer par |
|---|---|---|
| §3.1.1, texte | définis au §3.3.1.2 | définis par la fonction FBS-1.2 (WF-ADM-0010) |
| WF-INTF-0010 Vérif | §3.3.4.2, §3.3.4.3, §3.3.4.5, §3.3.4.4 | FBS-4.3, FBS-4.4, FBS-4.6, FBS-4.5 |
| WF-INTF-0020 Vérif | §3.3.3, §3.3.2.3 | FBS-3, FBS-2.3 |
| WF-INTF-0030 Vérif | §3.3.1.1, §3.3.1.2, §3.3.1.3 | FBS-1.1, FBS-1.2, FBS-1.3 |

Tant que WF-INTF-0010 est ouverte, deux autres corrections s'imposent. Son corps cite maintenant cinq usages, mais son Motif dit encore « Ces quatre usages » : écrire « Ces usages ». Et sa Vérif ne teste pas l'import ni l'export : ajouter « ainsi que les imports et exports de fichiers (FBS-4.3.4, FBS-4.7) ».

**Statut.** intégré

---

## C-012 — Des renvois entre exigences MS Project ont été décalés par la renumérotation

- **gravité** : majeur
- **emplacement** : §3.1.2, WF-INTF-0050 (Vérif) et WF-INTF-0060 (Motif)
- **citation** : « l'export transmet à MS Project les calendriers nécessaires à ses calculs (WF-INTF-0060), tandis que l'import les ignore (WF-INTF-0050) »

**Constat.** Depuis la renumérotation, l'import MS Project est WF-INTF-0040 et l'export WF-INTF-0050. Deux renvois n'ont pas suivi. WF-INTF-0060 cite l'export sous le numéro 0060, c'est-à-dire elle-même, et l'import sous le numéro 0050, qui est l'export. La Vérif de WF-INTF-0050 renvoie à « les versions de MS Project visées par WF-INTF-0050 », c'est-à-dire à elle-même, alors que ces versions sont définies dans l'import.

**Proposition.**
- WF-INTF-0050, Vérif : « visées par WF-INTF-0040 ».
- WF-INTF-0060, Motif : « L'export transmet à MS Project les calendriers nécessaires à ses calculs (WF-INTF-0050), tandis que l'import les ignore (WF-INTF-0040). »

**Statut.** intégré

---

## C-013 — WF-DEV-0010 vérifie encore une condition que son corps ne pose plus

- **gravité** : majeur
- **emplacement** : §3.4.5.4, WF-DEV-0010
- **citation** : « Le refus énumère les catégories de coût sans taux pour l'année de référence, et les années de consommation sans coefficient d'inflation. »

**Constat.** La condition sur le coefficient d'inflation a été retirée du corps, puisque ce coefficient est garanti par l'initialisation du projet (WF-CYC-0040). La Vérif et le titre le citent pourtant encore. Le testeur chercherait donc un refus que le logiciel n'a aucune raison de produire.

**Proposition.**
- Titre : « Taux horaires requis pour le calcul ».
- Vérif : « Le refus énumère les catégories de coût sans taux horaire pour l'année de référence. Le calcul aboutit dès que ces taux sont renseignés. »

**Statut.** intégré

---

## C-014 — Le paragraphe sur les prérequis n'a pas d'introduction et se contredit sur l'inflation

- **gravité** : majeur
- **emplacement** : §3.3.1, paragraphe avant WF-CYC-0120
- **citation** : « Les taux horaires et les coefficients d'inflation, eux, dépendent de ce que le devis emploie réellement. […] le coefficient d'inflation, lui, est garanti par l'initialisation du projet (WF-CYC-0040). »

**Constat.** Deux défauts. D'abord, le paragraphe commence par « Les prérequis se vérifient en deux temps » sans avoir dit de quels prérequis il s'agit : le paragraphe d'introduction a disparu. Ensuite, la même phrase dit que le coefficient d'inflation dépend du devis et qu'il est garanti par l'initialisation. C'est précisément le flou que l'auteur voulait lever.

**Proposition.** Remplacer le paragraphe par :

> La plateforme ne permet de créer des projets que lorsque le référentiel commun suffit pour les planifier et les chiffrer : un calendrier pour convertir une durée en dates, des rôles de ressources et des catégories de coût pour convertir une charge en montant.
>
> Ces prérequis se vérifient en deux temps. L'existence du référentiel se vérifie à la création du projet (WF-CYC-0120). Les taux horaires, eux, dépendent des catégories de coût qu'un devis emploie réellement : ils se vérifient au calcul du devis ou du reste à engager, pour l'année de référence seulement (WF-DEV-0010). Le taux d'inflation n'est pas un prérequis de calcul, car il fait partie des paramètres exigés pour l'initialisation du projet (WF-CYC-0040).

**Statut.** intégré

---

## C-015 — WF-CYC-0040 n'est pas vérifiable tant que les paramètres requis ne sont pas listés

- **gravité** : majeur
- **emplacement** : §3.3.2, WF-CYC-0040 ; §3.4.5.2, vide
- **citation** : « Un projet passe de Créé à Initialisé dès que ses paramètres sont complets. »

**Constat.** « Complets » ne renvoie à aucune liste. Le §3.4.5.2 Paramètres de projets, où cette liste devait figurer, est vide. En l'état, un testeur ne peut pas savoir quand l'état Initialisé doit être atteint, et WF-CYC-0120 et WF-DEV-0010 s'appuient toutes deux sur cette initialisation.

**Proposition.** Ajouter au §3.4.5.2 une exigence qui énumère les paramètres requis, et faire renvoyer WF-CYC-0040 à son identifiant : « dès que ses paramètres requis (WF-PRJ-0010) sont renseignés ». Les éléments connus à ce jour sont le taux d'inflation et les codes de sous-projets. Le lotissement n'en fait pas partie, puisqu'il a une valeur par défaut. L'auteur a indiqué que la liste en comporte d'autres. Le code `PRJ` est une proposition : il faut l'ajouter au §1.4.2.

**Statut.** sans objet : l'état Initialisé et WF-CYC-0040 ont été retirés (C-028), et PO-03 ne figure plus en annexe D

---

## C-016 — Un import sans révision en cours d'élaboration n'a pas de comportement défini

- **gravité** : majeur
- **emplacement** : §3.1.2, WF-INTF-0090 ; §3.3.2, WF-CYC-0040
- **citation** : « Les imports de planning, de devis et de reste à engager s'appliquent à la révision en cours d'élaboration du projet. »

**Constat.** Deux situations ne sont couvertes par aucune exigence :
- **À l'état Créé**, aucune révision n'existe, puisque WF-CYC-0040 en interdit la création. Que devient un import MS Project à ce stade ?
- **Après un marquage**, par exemple juste après une revue périodique, rien n'indique qu'une révision en cours d'élaboration existe encore.

L'import n'a alors pas de cible. Le développeur devra choisir entre refuser l'import et créer une révision, et les deux choix ont des conséquences sur le cycle de vie : créer la première révision fait passer le projet à Chiffrage.

**Proposition.** Ajouter au corps de WF-INTF-0090 : « Lorsque le projet ne comporte aucune révision en cours d'élaboration, l'import est refusé, et le refus indique qu'une révision doit d'abord être créée. » C'est l'option la plus sûre, puisqu'un import ne déclenche alors jamais de transition du cycle de vie. L'autre option, créer la révision automatiquement, est possible, mais WF-CYC-0020 devrait alors citer l'import parmi les faits déclencheurs.

**Statut.** intégré

---

## C-017 — Les impacts d'un risque sont décrits comme des « lignes de coût », c'est-à-dire des coûts réels

- **gravité** : majeur
- **emplacement** : §1.3, entrée « Risque »
- **citation** : « Ses impacts prévisionnels sont composés de taches de plannings et de lignes de couts. »

**Constat.** Le §1.3 définit la « ligne de coût » comme « une ligne comptable importée depuis l'ERP », qui constitue un coût réel. Un impact prévisionnel ne peut pas être un coût réel : c'est une prévision. Un développeur qui suit les définitions rattacherait les risques aux lignes importées de l'ERP.

**Proposition.** « Ses impacts prévisionnels sont composés de tâches de planning et de lignes de devis. » Si les impacts doivent pouvoir être exprimés dans le reste à engager, écrire « de lignes de devis ou de reste à engager ».

**Statut.** intégré

---

## C-018 — « Charge » est employé dans deux sens

- **gravité** : majeur
- **emplacement** : §1.3, entrées « Charge » et « Année de consommation »
- **citation** : « Désigne le nombre d'heures de travail nécessaires par mois pour réaliser un projet ou un ensemble de projets. »

**Constat.** La définition décrit une charge **mensuelle agrégée**, celle d'un plan de charge. Mais « Année de consommation » parle de « l'année au cours de laquelle **une** charge sera consommée », c'est-à-dire du volume d'heures d'une ligne de devis ou d'une tâche. La règle de chiffrage à venir (taux de l'année de référence projeté sur l'année de consommation) utilisera ce second sens. Or c'est le premier qui est défini.

**Proposition.** Définir les deux notions séparément :
- **Charge** : « Désigne un volume d'heures de travail, associé à un rôle de ressource et réparti dans le temps selon le planning. »
- **Plan de charge** : « Désigne la répartition mensuelle des charges d'un projet ou d'un ensemble de projets, par rôle de ressource. »

La question de savoir si la charge est associée au rôle relève du point ouvert PO-02. La définition pourra s'ajuster quand il sera tranché.

**Statut.** intégré

---

## C-019 — Des erreurs de copie relevées le 2026-09-18 ne sont pas corrigées

- **gravité** : mineur
- **emplacement** : WF-INTF-0070 à 0110 ; tableau 4 ; WF-CYC-0040
- **citation** : « FBS FBS-4.4, FBS-4.5, FBS-4.7 »

**Constat.** Il reste trois erreurs de copie :
- le champ FBS des exigences 0070, 0080, 0090, 0100 et 0110 commence toujours par l'étiquette « FBS » ;
- dans le tableau 4, FLX-06 porte toujours le libellé « Reste à engage » ;
- le Motif de WF-CYC-0040 commence par « a planification », sans le L.

**Proposition.** Retirer « FBS » en tête des cinq champs, et corriger « Reste à engager » et « La planification ».

**Statut.** intégré

---

## C-020 — Des champs FBS restent vides alors que l'arborescence existe

- **gravité** : mineur
- **emplacement** : WF-INTF-0010 à 0060 ; WF-ADM-0010
- **citation** : champ FBS « TBD »

**Constat.** Il y a deux problèmes :
- Les champs FBS de WF-INTF-0040, 0050 et 0060 sont encore à « TBD », alors que la fonction existe : FBS-4.3.4 Imports / Exports. Ceux de WF-INTF-0010, 0020 et 0030 le sont aussi, et ils peuvent renvoyer à FBS-1.2, puisque ces usages fixent le contenu des rôles prédéfinis.
- WF-ADM-0010, qui porte sur les rôles d'habilitation prédéfinis, a des champs FBS et PBS vides. Elle est aussi rangée au §3.4.2.1 Gestion des utilisateurs, alors qu'elle traite des rôles.

**Proposition.**
- FBS de WF-INTF-0040 à 0060 : FBS-4.3.4.
- FBS de WF-INTF-0010 à 0030 : FBS-1.2.
- WF-ADM-0010 : FBS-1.2, PBS « TBD », et déplacement au §3.4.2.2 Gestion des rôles d'habilitation.

**Statut.** intégré

---

## C-021 — L'exemple d'exigence réutilise un identifiant réel

- **gravité** : mineur
- **emplacement** : §1.4.1, exemple d'exigence
- **citation** : « WF-ADM-0010-A — Support multi-utilisateur — FBS1.2.6 »

**Constat.** L'exemple porte le même identifiant que l'exigence réelle sur les rôles prédéfinis : le build signale le doublon à chaque génération. Son champ FBS suit aussi un format qui n'existe plus (`FBS1.2.6`, sans tiret, et une fonction absente de l'arborescence).

**Proposition.** Donner à l'exemple un identifiant visiblement fictif, `WF-XXX-0010-A`, et un champ FBS au format actuel, par exemple `FBS-1.1`.

**Statut.** intégré

---

## C-022 — Écarts de terminologie et coquilles restants

- **gravité** : mineur
- **emplacement** : document
- **citation** : —

**Constat.** Ces écarts ne changent le sens d'aucune exigence, mais le document devient irrégulier :
- dans le §1.2, « Cout réel » et « Indice de cout » ; dans le §1.3, « Tache », « Tache récapitulative », « Tache feuille », « Fin a Fin » ;
- dans les titres de sections, « Paramètres de couts », « Nature et catégories de couts », « Gestion des couts », « Couts réels », « Projection a terminaison », « Indicateur de couts (CPI) » et « Couts cumulés ». Les figures de l'arborescence ont été corrigées, pas les titres. Figure et titre divergent donc ;
- dans la légende de la figure 5, « plannification » ;
- dans le diagramme de contexte (draw.io), « Couts réels », « Reste à engagé » et « Etats du système » ;
- WF-CYC-0010 a pour titre « Etats du cycle de vie » ;
- au §3.1.3, « les différents types d'utilisateurs », alors que le document parle désormais d'« acteurs » ;
- le §1.3 devait être trié par ordre alphabétique, mais les entrées ajoutées figurent à la fin ;
- la définition de « Référentiel commun » ne cite pas les natures de coût.

**Proposition.** Corriger dans Word et dans draw.io, puis relancer `./build.sh`.

**Statut.** intégré

---

## C-023 — Des passages supposent le point ouvert PO-01 résolu

- **gravité** : mineur
- **emplacement** : §2, « Objectif de la plateforme » ; §1.3, « Engagé » et « Consommé »
- **citation** : « La plateforme met en relation les prévisions initiales, les évolutions du planning, les coûts engagés et réalisés »

**Constat.** PO-01 établit que l'ERP ne fournit que les dépenses payées. Pourtant, le §2 promet de relier les coûts **engagés**, et le §1.3 définit « Engagé » et « Consommé » comme des montants que Waterfall connaîtrait, alors qu'aucun flux ne les apporte. Ces passages ne sont pas faux dans l'absolu, mais ils anticipent une solution qui n'est pas encore décidée.

**Proposition.** Aucune correction avant que PO-01 soit tranché. En revanche, citer ces trois passages dans l'annexe B, en regard de PO-01, pour qu'ils soient revus en même temps que le sujet.

**Statut.** reporté : passages rattachés à PO-01
