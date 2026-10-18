# Engagements envers l'édition communautaire

Version : 1.0 du 18 octobre 2026, applicable à compter de sa fusion dans `main`, avec
l'accord de contribution ([`CLA.md`](CLA.md)) dont il est la contrepartie (article 6.2).
[`README.md`](README.md) dit ce que chaque engagement écarte, et pourquoi il a été retenu.

Waterfall pourra avoir des offres payantes. Ce document dit ce qu'elles ne feront jamais à
l'édition communautaire : celle que ce dépôt publie, sous ses licences libres. Chaque engagement
est écrit comme une exigence de la spécification — on doit pouvoir constater qu'il est tenu, ou
qu'il ne l'est pas — et porte sa raison, parce qu'un engagement dont on ne sait plus pourquoi il
a été pris finit par être lu comme une gêne.

L'accord de contribution les rend opposables pour chaque contribution, dans leur rédaction du
jour où elle a été soumise (CLA, article 6.2), et dit ce que le contributeur peut faire s'ils ne
sont pas tenus (CLA, article 6.4).

## E-01 — Le produit reste libre

Le noyau métier, le service d'API, le worker, le front, le contrat d'interface, la
spécification et l'outillage du dépôt sont publiés en entier dans ce dépôt public, sous une
licence libre : AGPL-3.0-only pour le code et l'outillage, CC BY-SA 4.0 pour la spécification,
Apache-2.0 pour le contrat d'interface, qui sert à s'intégrer à Waterfall. Toute version que le
Mainteneur distribue ou héberge a son code source publié ici, à l'identique.

**Pourquoi.** Waterfall pilote des projets de dix ou quinze ans. Une organisation ne peut y
confier ses budgets de référence que si elle sait pouvoir faire tourner le logiciel, le
corriger et en relire les calculs sans dépendre de la survie d'un fournisseur.

## E-02 — La spécification entière est dans l'édition communautaire

Chaque exigence de la spécification (`docs/spec`) est réalisée par l'édition communautaire.
Une fonction payante ne réalise aucune exigence de la spécification ; elle a, s'il le faut, sa
propre spécification, publiée ou non.

**Pourquoi.** La spécification décrit un produit complet, de la tâche au portefeuille : c'est ce
produit que les contributeurs améliorent, et c'est lui qu'une organisation évalue. Une
édition communautaire amputée de ce que la spécification promet ne serait ni l'un ni l'autre.
Cet engagement écarte donc un découpage par acheteur, où le portefeuille (FBS-2) ou
l'exploitation (FBS-1) seraient payants ; il laisse au payant ce qui est hors de la
spécification : les connecteurs aux outils d'exécution et à l'ERP, et les services.

## E-03 — Rien ne quitte l'édition communautaire

Une fonction publiée dans l'édition communautaire n'en est jamais retirée pour devenir payante.
Elle n'y est pas non plus bridée — en nombre de projets, d'utilisateurs, de révisions ou en
volume — pour pousser vers une offre payante. Les volumes que la spécification fixe (§4.6.2)
sont ceux de l'édition communautaire.

**Pourquoi.** Le seul soupçon qu'une contribution puisse un jour passer derrière un paiement
suffit à tarir les contributions.

## E-04 — Les offres payantes passent par le contrat public

Une offre payante est soit un service — hébergement, support, versions maintenues au long
cours, migration, formation —, soit un programme distinct de l'édition communautaire, qui
n'emploie que les opérations du contrat d'interface publié (`docs/api`). Le noyau ne contient
ni clé de licence, ni fonction masquée, ni opération réservée à une offre payante.

**Pourquoi.** Une frontière que le contrat trace se vérifie : il suffit de lire les appels
d'une offre payante. Et tout ce qu'une offre payante fait, un tiers peut le faire aussi, par le
même contrat ; l'édition communautaire ne dépend donc jamais du Mainteneur pour s'ouvrir à
d'autres outils. Cet engagement écarte des modules payants dans le noyau, activés par une clé
de licence : avec eux, E-03 ne se vérifierait plus, et le noyau devrait porter des points
d'extension que la spécification ne prévoit pas (WF-ARC-0010).

## E-05 — Les données restent à leur propriétaire

Toutes les données d'une installation restent lisibles, sauvegardables et restaurables avec la
seule édition communautaire, et ses exports — MS Project, Excel — restent complets. Aucune
offre payante n'écrit dans la base de Waterfall de donnée que l'édition communautaire ne sait
ni lire, ni sauvegarder, ni restaurer.

**Pourquoi.** Une révision marquée doit rester lisible des années après avoir été remise.
Elle ne le serait plus si une partie de ce qu'elle porte dépendait d'un abonnement en cours.

## E-06 — Une contribution reste libre

Toute contribution reçue sous l'accord de contribution est publiée sous la licence libre du
dépôt qui la régit — AGPL-3.0-only, CC BY-SA 4.0 ou Apache-2.0 selon ce qu'elle touche —, ou
sous une autre licence libre au sens de l'accord, y compris lorsqu'elle est aussi intégrée à
une offre payante (CLA, article 6.1).

**Pourquoi.** L'accord donne au Mainteneur le droit de distribuer une contribution sous
d'autres conditions ; cet engagement garantit que ce droit s'ajoute à la licence libre, et ne la
remplace jamais.

## E-07 — Ces engagements ne reculent pas

Ce document peut s'enrichir à tout moment. Un engagement ne peut être affaibli ou retiré que par
une modification de ce document, publiée dans ce dépôt six mois avant de prendre effet, et
jamais pour les contributions soumises avant sa prise d'effet (CLA, article 6.2).

**Pourquoi.** Un engagement qu'on peut retirer du jour au lendemain n'engage à rien. Six mois
laissent à chaque contributeur le temps de lire la modification et de décider s'il continue ;
ce qu'il a déjà soumis reste couvert par le texte qu'il a lu.
