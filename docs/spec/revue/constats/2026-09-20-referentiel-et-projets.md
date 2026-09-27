---
revue_du: 2026-09-20
sur: waterfall-spec.md généré le 2026-09-20 (commit 2cba090)
revue_par: Claude Opus 5
perimetre: §3.4.4 référentiel, §3.4.5.1 révisions, §3.4.5.2 paramètres de projets, et leurs croisements
---

# Revue du 2026-09-20 — référentiel, révisions et paramètres de projets

## Suivi des revues précédentes

Les trois revues précédentes sont soldées. Le seul reliquat connu est l'apostrophe
droite du terme « État d'avancement » au §1.3, signalée dans le statut de C-032.

## Nouveaux constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-033 | majeur | §3.1.1 | Le champ Vérif de WF-INTF-0010 contient une copie de son Motif | intégré |
| C-034 | majeur | §3.4.5.4 | La restriction de WF-DEV-0010 n'existe que dans son titre | intégré |
| C-035 | majeur | §3.4.5.2.4 | Le créateur d'un projet n'en est pas contributeur | intégré |
| C-036 | majeur | §3.4.5.1 | Une désignation erronée de la révision de référence est sans recours | intégré |
| C-037 | mineur | §3.4.5.2 | FBS-4.2.4 manque à l'arborescence fonctionnelle | intégré |
| C-038 | mineur | §3.4.2.2 | WF-ADM-0030 est rangée hors de son sujet | intégré |
| C-039 | mineur | §3.4.4.2.1 | Deux phrases voisines se contredisent en apparence | intégré |
| C-040 | mineur | §3.1.2 | L'immuabilité d'une révision marquée est écrite à trois endroits | intégré |

---

## C-033 — Le champ Vérif de WF-INTF-0010 contient une copie de son Motif

- **gravité** : majeur
- **emplacement** : §3.1.1, WF-INTF-0010
- **citation** : « Vérif — Ces usages sont ceux de l'acteur qui connaît le contenu technique du projet et produit les données d'entrée du calcul des indicateurs. »

**Constat.** Le Motif a été recopié dans la Vérif, et le critère d'origine est perdu. L'exigence n'a donc plus de condition observable : rien ne dit comment vérifier qu'elle est satisfaite. C'est la seule des soixante et une exigences dans ce cas.

**Proposition.** Restaurer le critère :

> Un utilisateur porteur du rôle prédéfini « chef de projet » atteint, sur un projet où il est habilité, les fonctions de planification (FBS-4.3), de chiffrage (FBS-4.4), de gestion des risques (FBS-4.6), d'estimation du reste à engager (FBS-4.5) et d'échange des fichiers du tableau des flux (FLX-01 à FLX-07), et les mène jusqu'à leur terme.

**Statut.** intégré

---

## C-034 — La restriction de WF-DEV-0010 n'existe que dans son titre

- **gravité** : majeur
- **emplacement** : §3.4.5.4, WF-DEV-0010 ; §3.4.5.1, WF-REV-0060
- **citation** : titre « Taux horaires requis pour le calcul **à la création d'un chiffrage** », corps « Le calcul d'un devis ou d'un reste à engager est refusé tant qu'une catégorie de coût employée n'a pas de taux horaire pour l'année de référence. »

**Constat.** Le titre restreint l'exigence à la création d'un chiffrage, le corps ne la restreint pas. Un titre n'est pas normatif : lu tel quel, le corps interdit tout calcul dès qu'une catégorie manque de taux, y compris lors d'une mise à jour. Or WF-REV-0060 pose exactement l'inverse : une catégorie sans taux pour l'année retenue conserve son taux précédent projeté par l'inflation. Les deux exigences se contredisent, et c'est le cas fréquent — une catégorie désactivée lors d'une réorganisation — qui tombe entre les deux.

**Proposition.** Porter la restriction dans le corps :

> Le calcul d'un devis ou d'un reste à engager créé dans l'année est refusé tant qu'une catégorie de coût employée n'a pas de taux horaire pour l'année de référence retenue. Les catégories concernées sont nommées une par une. La mise à jour des taux d'un chiffrage existant relève de WF-REV-0060.

**Statut.** intégré

---

## C-035 — Le créateur d'un projet n'en est pas contributeur

- **gravité** : majeur
- **emplacement** : §3.4.5.2.4, WF-PRJ-0060
- **citation** : « Toute saisie sur un projet est réservée à ses contributeurs. »

**Constat.** La liste des contributeurs est vide à la création d'un projet. Personne ne peut donc y saisir quoi que ce soit, pas même celui qui vient de le créer — et il ne peut pas non plus s'y inscrire, puisque modifier la liste est une saisie sur le projet. Le projet est bloqué dès sa naissance.

WF-PRJ-0070 n'y change rien : la proposition automatique s'appuie sur les rôles employés par le planning, qui n'existe pas encore.

**Proposition.** Ajouter au corps de WF-PRJ-0060 :

> Le créateur du projet en est contributeur.

Et préciser dans la Vérif que la liste d'un projet nouvellement créé comporte son créateur, et que celui-ci peut y inscrire d'autres utilisateurs.

**Statut.** intégré

---

## C-036 — Une désignation erronée de la révision de référence est sans recours

- **gravité** : majeur
- **emplacement** : §3.4.5.1, WF-REV-0040 ; §3.3.2, WF-CYC-0020 et WF-CYC-0030
- **citation** : « La révision de référence est désignée par l'utilisateur parmi les révisions marquées, une seule fois, à la contractualisation. »

**Constat.** La désignation fait passer le projet à En cours, et ce passage est automatique (WF-CYC-0020). Après lui, la désignation manuelle n'est plus proposée. Désigner la mauvaise révision — l'offre v2 plutôt que la v3 effectivement contractualisée — est donc une erreur définitive, qui fausse le budget de référence, les jalons contractuels et tous les indicateurs de valeur acquise du projet.

Les deux seuls chemins de sortie sont un avenant, qui suppose un acte contractuel qui n'a pas eu lieu, ou l'abandon du projet et sa ressaisie complète.

**Proposition.** Autoriser la correction tant qu'elle est sans conséquence, c'est-à-dire tant qu'aucun coût réel n'a été importé et qu'aucune revue périodique n'a été marquée :

> La désignation peut être corrigée tant que le projet n'a reçu aucun coût réel et qu'aucune révision n'a été marquée depuis. Au-delà, la référence ne se déplace que par un avenant ou par la survenance d'un risque.

**Statut.** intégré

---

## C-037 — FBS-4.2.4 manque à l'arborescence fonctionnelle

- **gravité** : mineur
- **emplacement** : §3.4.5.2, figure de l'arborescence des paramètres de projets
- **citation** : champ FBS de WF-PRJ-0060 et WF-PRJ-0070, « FBS-4.2.4 »

**Constat.** Deux exigences se rattachent à FBS-4.2.4, qui n'existe dans aucune figure. La fonction « Contributeurs » a été créée dans le texte sans être ajoutée au diagramme du §3.4.5.2, qui montre toujours les trois seules sous-fonctions d'origine.

**Proposition.** Ajouter le nœud à la page draw.io des paramètres de projets, sous FBS-4.2, à la suite de FBS-4.2.3.

**Statut.** intégré

---

## C-038 — WF-ADM-0030 est rangée hors de son sujet

- **gravité** : mineur
- **emplacement** : §3.4.2.2, WF-ADM-0030
- **citation** : « Un compte utilisateur peut être rattaché à un nœud d'organisation. »

**Constat.** L'exigence traite du compte utilisateur et porte le code FBS-1.1, mais elle se trouve au §3.4.2.2 Gestion des rôles d'habilitation. Sa place est le §3.4.2.1 Gestion des utilisateurs. Elle ne parle d'habilitations que pour dire qu'elle n'en accorde aucune.

**Proposition.** La déplacer au §3.4.2.1.

**Statut.** intégré

---

## C-039 — Deux phrases voisines se contredisent en apparence

- **gravité** : mineur
- **emplacement** : §3.4.4.2.1
- **citation** : « les rôles étant recréés sous les nouveaux nœuds plutôt que déplacés (WF-REF-0080). Un nœud peut être déplacé dans l'arbre. »

**Constat.** Les deux phrases sont exactes : ce sont les rôles qui ne se déplacent pas, et les nœuds qui le peuvent. Mais elles se suivent immédiatement, avec le même verbe, et le lecteur y voit une contradiction.

**Proposition.**

> Une réorganisation se traduit par des désactivations en cascade : les rôles ne se déplacent pas d'un nœud à l'autre, ils sont recréés sous les nouveaux nœuds (WF-REF-0080). Un nœud, lui, peut être déplacé dans l'arbre. Les regroupements par service, notamment le plan de charge agrégé, sont toujours lus à travers l'organigramme courant : déplacer un nœud change donc la présentation des données passées, sans en changer les valeurs.

**Statut.** intégré

---

## C-040 — L'immuabilité d'une révision marquée est écrite à trois endroits

- **gravité** : mineur
- **emplacement** : §3.4.5.1 WF-REV-0020 ; §3.1.2 WF-INTF-0090 ; §1.3
- **citation** : « Une révision marquée n'est plus modifiable, par aucun moyen : ni saisie, ni import, ni traitement automatique. » (WF-REV-0020) et « Un import ne modifie jamais une révision marquée. » (WF-INTF-0090)

**Constat.** Depuis que WF-REV-0020 existe, elle couvre explicitement le cas de l'import. La dernière phrase de WF-INTF-0090 la répète, et la définition du §1.3 une troisième fois. Ce n'est pas faux, mais deux textes à corriger le jour où la règle changera, c'est un de trop.

**Proposition.** Retirer la dernière phrase du corps de WF-INTF-0090, qui ne garde alors que ce qui lui est propre : à quelle révision un import s'applique, et ce qui se passe quand il n'y en a pas. Sa Vérif, qui teste qu'une révision marquée est inchangée après import, peut rester : elle vérifie utilement l'application de WF-REV-0020 au cas particulier des imports.

**Statut.** intégré
