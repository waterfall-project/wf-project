---
id: EP-29
titre: Les habilitations et les comptes suivent la spécification 1.0.7 — le référentiel sous permission, la visibilité d'un projet, le catalogue, les chefs de projet, les administrateurs, le lien de mot de passe
statut: à planifier
depend_de: EP-08
famille: front, back
issue:
---

# EP-29 — Habilitations et comptes : suites de la spécification 1.0.7

## Objet

Le tri des constats de spécification du 2026-11-18 (`docs/api/DECISIONS.md`, « Le tri des constats
de spécification », #3349) a tranché, pour la spécification 1.0.7, plusieurs règles d'habilitation
que le code livré ne suit pas : un compte sans rôle lit encore le référentiel, un rôle composé du
seul planning n'ouvre aucun projet, le catalogue porte deux permissions sans effet, une ligne de
coût s'exclut sans être chef de projet, la garde du dernier administrateur compte un compte qui
ne s'est jamais connecté, et un compte que l'annuaire désactive reste actif.

Ces constats étaient étiquetés EP-13. Le cadrage d'EP-13 les en sort (décision de l'auteur du
2026-11-18) : ils touchent les habilitations et le contrat, non l'exploitation, et EP-13 écarte
« toute fonction métier ». L'EPIC reste à cadrer : ses US, sa conception et son rang se décident
à son cadrage.

La ventilation du 2026-11-21 l'élargit aux comptes : il reçoit le bloquant de la revue du
2026-11-14 sur le lien de mot de passe (#3342), qui laisse un porteur de `users.write` seul prendre
un compte administrateur, et les constats de la même revue sur les habilitations du back, l'écran
des comptes et les écrans du référentiel ouverts sans la permission de les consulter. Il est de la
première vague : il ne touche ni le code d'EP-13, ni celui d'EP-30.

## Ce qui en fait partie

- la lecture des objets actifs du référentiel, des paramètres communs et des unités de durée sous
  la permission de consulter leur fonction (#3960, #3962), après la réponse donnée aux formulaires
  des projets qui les nomment (#3961, à trancher) ;
- la liste et l'ouverture d'un projet par qui consulte l'une de ses fonctions (#3974) ;
- le catalogue des permissions sans `lifecycle.write` ni `project_indicators.write` (#3975) ;
- l'exclusion et la réintégration d'une ligne de coût réservées aux chefs de projet (#3973) ;
- la garde du dernier administrateur, qui ne compte que les comptes déjà connectés (#3987) ;
- la lecture des comptes, qui désactive ceux que l'annuaire tient pour désactivés (#3986) ;
- la citation de WF-ADM-0200 dans les opérations qui servent les réglages de l'installation
  (#3993) ;
- le lien de mot de passe et le changement d'adresse d'un compte qui porte l'administration, et la
  garde du dernier administrateur, qui compte les quatre permissions (#3342) ;
- l'inscription d'un participant sur un projet terminal (#3990), et celle des comptes que le serveur
  ne propose pas ;
- les écrans du référentiel refusés à qui n'a pas la permission de les consulter ;
- l'écran des comptes : le rattachement atteint au clavier, les commandes de la table ;
- les habilitations du back que WF-ADM-0110 laisse à trancher, et l'avatar décodé à la pose.

## Ce qui n'en fait pas partie

- l'inscription des chefs de projet au journal d'audit (#3988) — EP-13, qui clôt WF-SEC-0030
  (US-2980) ;
- l'exploitation de la plateforme — EP-13.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Les
exigences que ses constats citent — WF-ADM-0020, WF-ADM-0070, WF-ADM-0090, WF-ADM-0100,
WF-ADM-0110, WF-ADM-0120, WF-PRJ-0060 — restent closes par les EPIC qui les ont réalisées, dont
les US notent déjà en écart les phrases que la spécification 1.0.7 ajoute, avec le constat qui
les éprouve.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

À établir au cadrage. Quatre constats modifient le contrat, figé (`docs/api/DECISIONS.md`, « La
règle d'après le gel ») : #3960, #3962, #3974 et #3975 ; #3993 n'en change que des descriptions.

## Préalables

EP-08 fusionné : le risque survenu et la fusion d'un différentiel, qu'il livre, suivent la règle des
chefs de projet de #3973. #3961 tranché par l'auteur, avant le travail qui referme les lectures
du référentiel (#3960, #3962).

## Définition de fini

À établir au cadrage.

## Constats reçus

Reportés d'EP-13 à son cadrage, le 2026-11-18 (décision de l'auteur), et rattachés à l'issue
d'EP-13 jusqu'à l'ouverture de celle de cet EPIC :

- #3960 — contrat : la lecture des objets actifs du référentiel repasse sous permission
  (WF-ADM-0020, WF-ADM-0090) ;
- #3961 — à trancher : les formulaires des projets nomment le référentiel sans la permission de le
  consulter ;
- #3962 — contrat : les paramètres communs et les unités de durée se lisent par toute session ;
- #3973 — back : l'exclusion d'une ligne de coût est réservée aux chefs de projet (WF-ADM-0100,
  WF-PRJ-0060) ;
- #3974 — contrat : un projet se voit de qui consulte l'une de ses fonctions, non le seul
  paramétrage (WF-ADM-0110) ;
- #3975 — contrat : FBS-4.8 et FBS-4.9 n'ont que la permission de consulter (WF-ADM-0100) ;
- #3986 — back : la lecture des comptes désactive ceux que l'annuaire tient pour désactivés
  (WF-ADM-0070) ;
- #3987 — back : la garde du dernier administrateur ne compte que les comptes déjà connectés
  (WF-ADM-0120) ;
- #3993 — contrat : citer WF-ADM-0200 dans les opérations qui servent les réglages de
  l'installation.

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3342 — back : un porteur de users.write seul obtient le lien de mot de passe d'un compte
  administrateur, ou change son adresse, et prend le compte (bloquant de la revue du 2026-11-14,
  BAC-01 ; elle porte aussi BAC-02 et CTA-02, la garde du dernier administrateur qui ne compte que
  deux permissions) ;
- #3990 — contrat : l'inscription d'un participant sur un projet terminal (WF-CYC-0100).

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4487 — un chef de projet ne peut inscrire que les comptes que le serveur propose (FPL-02) — une
  opération de contrat d'abord ;
- #4488 — la liste du rattachement d'un compte est inatteignable au clavier dans la grille (FAR-02,
  FAR-06) ;
- #4489 — trois écrans du référentiel se présentent par URL directe sans la permission de consulter
  (FAR-03) — #3960 en ferme un, non les deux autres ;
- #4490 — les habilitations du back, WF-ADM-0110 (BAC-03, BAC-04) — BAC-04 demande un arbitrage de
  spécification avant tout code ;
- #4491 — l'avatar : image décodée à la pose (BAC-05) ;
- #4492 — l'écran des comptes : commandes de la table (FAR-04, FAR-08) — FAR-08 après #3342.

Constat de la même revue joint à une issue ci-dessus : BAC-08, l'exclusion d'une ligne de coût sans
la qualité de chef de projet, à #3973.

## Conduite

Vague 1 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 2.
