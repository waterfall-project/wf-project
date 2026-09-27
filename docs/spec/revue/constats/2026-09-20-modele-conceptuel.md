---
revue_du: 2026-09-20
sur: waterfall-spec.md généré le 2026-09-20 (commit 48f79c6)
revue_par: Claude Opus 5
perimetre: §1.3, §3.1, §3.2, §3.3 — le modèle conceptuel et ce qu'il touche
---

# Revue du 2026-09-20 — modèle conceptuel

## Suivi des revues précédentes

Les revues du 2026-09-17 et du 2026-09-19 sont soldées : tous leurs constats sont
intégrés, sauf C-015 et C-023, reportés et inscrits en PO-03 et PO-01. Je n'ai
relevé aucune régression sur les corrections appliquées.

## Nouveaux constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-024 | majeur | §1.3 | « Devis » décrit encore une révision planning/devis | intégré |
| C-025 | majeur | §1.3, §3.2.3 | Le caractère de référence est porté à deux endroits | intégré |
| C-026 | majeur | §1.3 | Une ligne hors main-d'œuvre n'a aucun moyen de porter sa catégorie de coût | intégré |
| C-027 | majeur | §1.3 | La définition d'un risque ignore son devis propre | intégré |
| C-028 | majeur | §3.3.2, annexe B | WF-CYC-0040 pourrait n'avoir plus aucun déclencheur | intégré |
| C-029 | mineur | §1.3 | La définition de « Tâche » est antérieure au modèle | intégré |
| C-030 | mineur | §3.2.3 | Une relation est dessinée dans deux grappes | intégré |
| C-031 | mineur | annexe A | Les formats Excel doivent désigner une tâche | intégré |
| C-032 | mineur | §1.3 | Coquilles | intégré, hors l'apostrophe du terme « État d'avancement » |

---

## C-024 — « Devis » décrit encore une révision planning/devis

- **gravité** : majeur
- **emplacement** : §1.3, entrées « Devis » et « Devis de référence »
- **citation** : « Désigne l'estimation des coûts d'un projet dans une révision planning/devis. »

**Constat.** Une révision n'est plus un couple planning/devis : c'est un instantané qui porte plusieurs structures de coûts. Le devis n'est donc plus rattaché à une révision, mais à une structure : ce sont les lignes portées par les tâches de cet arbre. « Devis de référence » souffre du même décalage : il désigne un devis, alors que la référence est désormais un caractère de la révision.

**Proposition.**

> **Devis.** Désigne l'ensemble des lignes de devis d'une structure de coûts. C'est la vue de cette structure du côté de l'argent, comme le planning en est la vue du côté du temps.
>
> **Devis de référence.** Désigne le devis de la révision de référence. Il sert à établir le budget de référence et à calculer la valeur planifiée.

**Statut.** intégré

---

## C-025 — Le caractère de référence est porté à deux endroits

- **gravité** : majeur
- **emplacement** : §1.3, entrées « Structure de coûts » et « Révision de référence » ; §3.2.3
- **citation** : « Sa nature indique ce qu'elle décrit : **le budget de référence**, le différentiel d'un avenant, le devis propre à un risque, ou l'état courant du projet. »

**Constat.** La même information est portée deux fois. La nature d'une structure peut valoir « budget de référence », et la révision porte par ailleurs un attribut qui dit qu'elle est la référence. Rien ne dit laquelle des deux fait foi, ni ce que signifie une structure de nature « budget de référence » dans une révision qui n'est pas la référence — cas qui se produit dès le premier avenant, puisque l'ancienne révision de référence conserve sa structure.

Le même raisonnement vaut pour la nature « état courant » : ce qui est courant, c'est la dernière révision, pas une structure en particulier.

**Proposition.** Ne garder dans la nature que ce qui distingue réellement les structures entre elles, et laisser à la révision ce qui relève de son rang :

> **Structure de coûts.** Désigne un arbre de tâches portant des lignes de devis. Sa nature indique ce qu'elle décrit : la structure principale du projet, le différentiel d'un avenant, ou le devis propre à un risque.

Une révision porte alors une structure principale et, le cas échéant, des différentiels et des devis de risques. Qu'elle soit la référence ou la plus récente ne se lit que sur elle.

**Statut.** intégré

---

## C-026 — Une ligne hors main-d'œuvre n'a aucun moyen de porter sa catégorie de coût

- **gravité** : majeur
- **emplacement** : §1.3, entrée « Ligne de devis » ; WF-DEV-0010 ; §3.2.2
- **citation** : « Elle peut être de type main-d'œuvre, auquel cas elle est caractérisée par une quantité, un nombre d'heures et un rôle, ou de type hors main-d'œuvre, auquel cas elle est caractérisée par une quantité et un débours. »

**Constat.** Une ligne de main-d'œuvre atteint sa catégorie de coût par son rôle, et donc son taux horaire. Une ligne hors main-d'œuvre, elle, ne porte qu'une quantité et un débours : rien ne la rattache à une nature ni à une catégorie. Trois choses en dépendent pourtant :

- la ventilation du devis par nature, qui est la raison d'être même des natures (§3.2.2) ;
- WF-DEV-0010, qui refuse un calcul quand « une catégorie de coût employée » n'a pas de taux : la notion de catégorie employée n'est définie que pour la main-d'œuvre ;
- le rapprochement comptable, puisque c'est la catégorie qui porte le code comptable.

**Proposition.** Rattacher toute ligne à une catégorie de coût, quelle que soit sa nature :

> **Ligne de devis.** Désigne une ligne portée par une tâche et rattachée à une catégorie de coût. Lorsque la catégorie relève d'une nature de main-d'œuvre, la ligne porte un rôle de ressource et une charge en heures ; sinon, elle porte une quantité et un débours.

La catégorie devient alors le point commun des deux types de lignes, le rôle n'apportant que la charge et le calendrier. Cela reste à confirmer : le rôle détermine peut-être la catégorie pour la main-d'œuvre, auquel cas il faut dire lequel des deux l'emporte en cas de désaccord.

**Statut.** intégré

---

## C-027 — La définition d'un risque ignore son devis propre

- **gravité** : majeur
- **emplacement** : §1.3, entrée « Risque »
- **citation** : « Ses impacts prévisionnels sont composés de taches de plannings et de lignes de devis. »

**Constat.** Le modèle du §3.2.3 donne à chaque risque une structure de coûts qui lui est propre, reportée dans la structure principale par une ligne de provision pondérée par la probabilité. La définition, elle, décrit des impacts faits de tâches et de lignes, sans dire qu'ils forment une structure ni qu'une provision les représente. Un lecteur qui s'en tient au §1.3 ne peut pas comprendre le mécanisme, ni pourquoi le budget de référence augmente à la survenance.

**Proposition.**

> **Risque.** Désigne un événement incertain susceptible d'affecter le coût ou les délais du projet. Il est caractérisé par sa probabilité d'occurrence et par sa gravité. Ses impacts prévisionnels sont décrits dans une structure de coûts qui lui est propre, reportée dans la structure principale par une ligne de provision pondérée par sa probabilité.

Le devenir de cette ligne à la survenance relève de PO-05.

**Statut.** intégré

---

## C-028 — WF-CYC-0040 pourrait n'avoir plus aucun déclencheur

- **gravité** : majeur
- **emplacement** : §3.3.2, WF-CYC-0040 ; annexe B, PO-03
- **citation** : « Un projet passe de Créé à Initialisé dès que ses paramètres sont complets. »

**Constat.** À mesure que les paramètres du projet ont été décrits, chacun a cessé d'être obligatoire. Le lotissement est facultatif et possède une valeur par défaut, le taux d'inflation vaut 0 % par défaut, le code projet n'est exigé qu'au passage à En cours, et les codes de sous-projets viennent de l'ERP à la commande. Il se pourrait donc qu'aucun paramètre ne soit requis, auquel cas l'état Initialisé serait franchi dès la création et ne distinguerait plus rien.

**Proposition.** Deux issues, à trancher avec PO-03. Soit il reste un paramètre réellement obligatoire, et il faut le nommer. Soit il n'en reste aucun, et il vaut mieux supprimer l'état Initialisé que de garder un état que tout projet franchit immédiatement : le cycle de vie reviendrait alors à Créé, Chiffrage, En cours, et la voie directe que nous avions supprimée redeviendrait la seule.

**Statut.** intégré

---

## C-029 — La définition de « Tâche » est antérieure au modèle

- **gravité** : mineur
- **emplacement** : §1.3, entrées « Tâche » et « Tâche feuille »
- **citation** : « Elle possède généralement une durée, une date de début et une date de fin, et peut être liée à d'autres tâches par des dépendances. »

**Constat.** Le mot « généralement » date d'avant le modèle. Une tâche porte désormais une durée, des dates, un mode de planification et un état d'avancement, et elle est liée aux autres par des liaisons, terme maintenant défini. « Tâche feuille » parle par ailleurs de « la structure du projet », expression qui désigne aujourd'hui autre chose.

**Proposition.**

> **Tâche.** Désigne une activité à réaliser dans le cadre du projet. Elle porte une durée, des dates, un mode de planification et un état d'avancement, et elle est reliée à d'autres tâches par des liaisons. Elle porte les lignes de devis qui la chiffrent.
>
> **Tâche feuille.** Désigne une tâche qui ne comporte aucune sous-tâche.

**Statut.** intégré

---

## C-030 — Une relation est dessinée dans deux grappes

- **gravité** : mineur
- **emplacement** : §3.2.3, second diagramme ; §3.2.4
- **citation** : `Tache "1" o-- "*" LigneDevis : porte`

**Constat.** La relation entre une tâche et ses lignes figure dans les deux grappes. Dans celle du §3.2.3, les deux objets sont grisés : la relation y est dessinée entre deux points d'ancrage, ce que la convention du §3.2.1 ne prévoit pas. Deux dessins de la même relation, c'est un risque de divergence pour rien.

**Proposition.** Retirer cette relation du diagramme du §3.2.3, ainsi que l'objet « Ligne de devis » qui n'y sert plus qu'à la porter. La grappe du planning reste son seul lieu.

**Statut.** intégré

---

## C-031 — Les formats Excel doivent désigner une tâche

- **gravité** : mineur
- **emplacement** : annexe A ; WF-INTF-0100, WF-INTF-0110, WF-INTF-0120, WF-INTF-0130
- **citation** : « portée par la tâche qu'il désigne »

**Constat.** Depuis que les lignes de devis sont portées par des tâches, les formats « Devis » et « Reste à engager » doivent comporter une colonne qui désigne la tâche, et les exports doivent l'écrire, faute de quoi l'aller-retour de WF-INTF-0110 ne peut pas être vérifié. L'annexe A étant à écrire, c'est un point à ne pas perdre plutôt qu'un défaut.

**Proposition.** Noter dès maintenant, dans l'annexe A, que les deux formats comportent une colonne de désignation de tâche et une colonne facultative de sous-projet.

**Statut.** intégré

---

## C-032 — Coquilles

- **gravité** : mineur
- **emplacement** : §1.3
- **citation** : « composés de taches de plannings »

**Constat.** Dans l'entrée « Risque », « taches de plannings » prend un accent et perd son pluriel. L'entrée « État d'avancement » emploie par ailleurs une apostrophe droite, là où le reste du tableau emploie l'apostrophe typographique.

**Proposition.** Corriger en même temps que C-027, qui réécrit l'entrée « Risque ».

**Statut.** intégré, hors l'apostrophe du terme « État d'avancement »
