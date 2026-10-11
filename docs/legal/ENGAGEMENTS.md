# Engagements envers l'édition communautaire

> **Brouillon, sans effet.** Ce texte est un projet, à faire relire avec l'accord de
> contribution ([`CLA.md`](CLA.md)), dont il est la contrepartie (article 6.2). Les notes
> « À trancher » posent une décision à l'auteur ; [`README.md`](README.md) dit ce qu'elles
> engagent.

Waterfall pourra avoir des offres payantes. Ce document dit ce qu'elles ne feront jamais à
l'édition communautaire : celle que ce dépôt publie, sous AGPL-3.0-only. Chaque engagement est
écrit comme une exigence de la spécification — on doit pouvoir constater qu'il est tenu, ou qu'il
ne l'est pas — et porte sa raison, parce qu'un engagement dont on ne sait plus pourquoi il a été
pris finit par être lu comme une gêne.

L'accord de contribution les rend opposables pour chaque contribution, dans leur rédaction du
jour où elle a été soumise (CLA, article 6.2).

## E-01 — Le produit reste libre

Le noyau métier, le service d'API, le worker, le front, le contrat d'interface, la
spécification et l'outillage du dépôt sont publiés en entier dans ce dépôt public, sous
AGPL-3.0-only — ou, pour ce qui sert à s'intégrer à Waterfall, comme le contrat d'interface,
sous une licence libre plus permissive. Toute version que le Bénéficiaire distribue ou héberge
a son code source publié ici, à l'identique.

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

> À trancher : cet engagement écarte un découpage par acheteur, où le portefeuille (FBS-2) ou
> l'exploitation (FBS-1) seraient payants. Il laisse au payant ce qui est aujourd'hui hors de la
> spécification : les connecteurs aux outils d'exécution et à l'ERP, et les services.

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
même contrat ; l'édition communautaire ne dépend donc jamais du Bénéficiaire pour s'ouvrir à
d'autres outils.

> À trancher : cet engagement écarte des modules payants dans le noyau, activés par une clé de
> licence, sur le modèle de Plane ou de GitLab EE. Les admettre demanderait de le réécrire, et
> de prévoir dans le noyau les points d'extension que la spécification ne prévoit pas
> (WF-ARC-0010).

## E-05 — Les données restent à leur propriétaire

Toutes les données d'une installation restent lisibles, sauvegardables et restaurables avec la
seule édition communautaire, et ses exports — MS Project, Excel — restent complets. Aucune
offre payante n'écrit dans la base de Waterfall de donnée que l'édition communautaire ne sait
ni lire, ni sauvegarder, ni restaurer.

**Pourquoi.** Une révision marquée doit rester lisible des années après avoir été remise.
Elle ne le serait plus si une partie de ce qu'elle porte dépendait d'un abonnement en cours.

## E-06 — Une contribution reste libre

Toute contribution reçue sous l'accord de contribution est publiée sous AGPL-3.0-only, ou sous
une autre licence approuvée par l'Open Source Initiative, y compris lorsqu'elle est aussi
intégrée à une offre payante (CLA, article 6.1).

**Pourquoi.** L'accord donne au Bénéficiaire le droit de distribuer une contribution sous
d'autres conditions ; cet engagement garantit que ce droit s'ajoute à la licence libre, et ne la
remplace jamais.

## E-07 — Ces engagements ne reculent pas

Ce document peut s'enrichir à tout moment. Un engagement ne peut être affaibli ou retiré que par
une modification de ce document, publiée dans ce dépôt [SIX MOIS] avant de prendre effet, et
jamais pour les contributions soumises avant elle (CLA, article 6.2).

**Pourquoi.** Un engagement qu'on peut retirer du jour au lendemain n'engage à rien.

> À trancher : la durée du préavis.
