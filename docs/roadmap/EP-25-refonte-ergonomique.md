---
id: EP-25
titre: Lire et saisir dans des écrans aérés, sobres et cohérents
statut: à planifier
depend_de: EP-24
famille: front, back
issue:
---

# EP-25 — Refonte ergonomique

## Objet

Les essais manuels de l'auteur du 2026-11-13, sur la plateforme de service, ont jugé les écrans
serrés, sans couleur et inégaux d'une table à l'autre. Un prototype, jugé sur l'écran des paramètres
de coûts, a arrêté une direction : une barre latérale sombre, un fond gris, des sections en cartes,
un bouton de création plein dans l'en-tête de sa carte, des commandes en pastilles, une pagination
discrète, des tables plates à pleine largeur.

L'EPIC étend cette direction à tous les écrans, et vient en premier après EP-24 : les EPICs qui
suivent ajoutent des écrans, des marques et des graphiques, qui naissent alors dans la présentation
nouvelle. Il réalise aussi les phrases que la spécification 1.0.6 ajoute sur les graphiques.

## Ce qui en fait partie

- la présentation des tables plates : le bouton de création, le nombre de lignes, la pagination, les
largeurs, les pastilles des filtres actifs (#3071, #3072, #3073, #3075, #3077) ;
- le filtre d'état en place de « Afficher aussi les désactivés » (#3076) ;
- la mise en page des écrans du référentiel, de l'administration, des paramètres, de l'accueil, d'un
projet et du compte (#3079, #3088, #3090) ;
- la présentation des graphiques, et les motifs des séries passés en préférence du compte,
désactivée par défaut, qui vaut aussi pour l'image exportée (#3097, #3098 ; WF-IHM-0070,
WF-ADM-0040, WF-IHM-0130) ;
- ce qui montre qu'un traitement est en cours, et la relecture de l'écran quand il aboutit (#3103,
WF-IHM-0080) ;
- les deux parcours des paramètres de coûts mis en quarantaine contre le service : leur cause, puis
leur réactivation, par le premier lot (#3190, #3191) ;
- les mineurs ouverts sur les écrans que l'EPIC reprend.

## Ce qui n'en fait pas partie

- la comparaison dans les grilles, son bandeau et ses marques — EP-27 ;
- le détail du plan de charge et la projection de dépenses — EP-10 ;
- la performance des grilles — EP-26.

## Exigences réalisées

L'EPIC ne clôt aucune exigence. Il poursuit WF-IHM-0130, que clôt EP-11, et réalise les phrases que
la spécification 1.0.6 ajoute à des exigences closes par des EPICs livrés — WF-IHM-0070 et
WF-ADM-0040 —, notées en écart dans les US qui les citaient (US-0160, US-0730, US-0740).

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-IHM-0130-A` | Filtrage des tables et export des graphiques | début — close en EP-11, amorcée aussi en EP-02, EP-03, EP-15 | — |

## Opérations du contrat

`getMe`, `updateMyPreferences` : la préférence des motifs des séries s'ajoute à
`DisplayPreferences`, modification du contrat qui précède le front. Les lectures des listes du
référentiel : `include_inactive` cède au filtre d'état.

## Préalables

EP-24 livré. Le prototype des essais (branche `essais/EP-24`, jamais fusionnée) sert de référence
visuelle, non de code à reprendre : il n'a ni tests ni traductions.

## Définition de fini

- chaque écran suit la direction arrêtée sur l'écran des paramètres de coûts, en mode clair et en
mode sombre, sans régression des audits d'accessibilité ;
- les deux parcours `reference-costs.spec.ts` en quarantaine sont rejoués contre le service (#3190,
#3191) ;
- `make check-all` passe.

## Constats reçus

Ventilation du reste à faire du 2026-11-14 (décision de l'auteur, à la livraison d'EP-24) : les
constats ouverts sont rattachés à l'EPIC qui touche leur code, et non plus au prochain EPIC ouvert.
Le cadrage les rattache à l'ouverture des issues de l'EPIC.

- #1512 — front : retirer `prefetch={false}` du menu du compte à la montée vers Next 16.5, et deux
mineurs de commentaire (US-0590e, tour 2) ;
- #1985 — front : le panneau d'aide de chaque écran n'est plus audité que sur l'écran de référence ;
- #1997 — front : la citation du test de la rangée vide, la lecture unique de la puce en e2e, un
commentaire à 101 colonnes (revue 2 d'US-1230/L2) ;
- #2050 — front : deux mineurs de la revue 2 d'US-1170/L4 — le nom sans initiales vérifié
exactement, un commentaire elliptique ;
- #2121 — front : le refus d'un nœud désactivé se dit par le message générique, pas par son champ ;
- #2260 — front : une ligne du référentiel en cours d'écriture garde ses commandes offertes, et la
suivante part d'une version périmée (412) ;
- #2266 — front : la correspondance des coûts réels perd le focus et la saisie en cours quand la
relecture remonte le formulaire ;
- #2267 — front : la correspondance offre un 21ᵉ intitulé pour une colonne lue, et son refus n'est
dit à aucune liste ;
- #2268 — front : la règle locale des seuils d'alerte juge leur ordre hors de ]0, 1[, ce que le
serveur ne fait pas ;
- #2270 — front : le remplacement des descendants d'un nœud désactivé par la cascade n'est éprouvé
par aucun test ;
- #2424 — front : deactivate de reference-manager.spec.ts peut recliquer sur une réponse lente ;
- #3071 — front : le bouton de création d'une liste est repoussé au bout de la page, loin de sa
table (WF-IHM-0060) ;
- #3072 — front : le nombre de lignes d'une table plate est dit deux fois, dans sa barre et dans sa
ligne de total (WF-IHM-0060) ;
- #3073 — front : la pagination d'une table plate n'offre que « Page suivante », sans dire où l'on
est (WF-IHM-0060) ;
- #3075 — front : les tables plates d'un même écran ont des largeurs très différentes (WF-IHM-0060)
;
- #3076 — front : « Afficher aussi les désactivés », bouton de l'écran, fait double emploi avec le
filtre « État » de chaque table (WF-REF-0150, WF-IHM-0130) ;
- #3077 — front : les pastilles des filtres actifs d'une table ne ressortent pas (WF-IHM-0130) ;
- #3079 — front : l'écran des listes du référentiel est serré et sans couleur — une présentation
aérée et sobre (WF-IHM-0040, WF-IHM-0070) ;
- #3088 — front : la mise en page des écrans d'administration et de paramètres, d'après l'écran des
coûts (WF-IHM-0040) ;
- #3090 — front : la mise en page de l'accueil, des écrans d'un projet et du compte, d'après l'écran
des coûts (WF-IHM-0040) ;
- #3097 — front : les graphiques sont datés — une présentation moderne et sobre, les motifs sans
couleur passés en réglage (WF-IHM-0070, WF-IHM-0130) ;
- #3098 — spec : les séries d'un graphique distinguées sans la couleur sur préférence de
l'utilisateur, non d'office (WF-IHM-0070, WF-ADM-0040, WF-IHM-0130) ;
- #3103 — front : rien ne montre qu'un traitement est en cours, et l'écran n'est pas relu quand il
aboutit — l'utilisateur relance (WF-IHM-0080) ;
- #3125 — front : buttonVariants ne stylise pas aria-disabled, partagé par une vingtaine d'écrans ;
- #3150 — front : le texte « indisponible » tronqué des commandes d'annulation, lisible en entier au
tactile par le seul tooltip ;
- #3163 — front : useRaise avale l'erreur après démontage sans le dire, et deux détails du test des
rôles ;
- #3190 — e2e : le parcours « désactive une nature depuis sa ligne » (reference-costs.spec.ts:372)
en quarantaine contre le service ;
- #3191 — e2e : le parcours « montre les natures et catégories désactivées et les réactive »
(reference-costs.spec.ts:470) en quarantaine contre le service.
