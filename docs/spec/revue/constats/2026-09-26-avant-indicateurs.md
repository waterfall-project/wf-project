---
revue_du: 2026-09-26
sur: waterfall-spec.md généré le 2026-09-26 (commit 6c43e5d)
revue_par: Claude Fable 5.1
perimetre: document complet hors paragraphes non rédigés, avec un angle — ce dont les indicateurs projets auront besoin
---

# Revue du 2026-09-26 — les bases avant les indicateurs

## Suivi des revues précédentes

Les cinq revues précédentes sont soldées. Deux reliquats cosmétiques restent en cours de
correction par l'auteur : les renvois d'annexe qui reprennent le titre entier, et un renvoi
relatif du §3.1.2. Ils sont repris en C-053 pour mémoire.

## Réponse à la question posée

Les bases sont solides sur ce qui concerne la structure : l'arbre commun, les révisions, le
référentiel, les coûts réels et leur exclusion, les risques et leurs provisions. Le document
dit ce qu'est un budget de référence, un reste à engager et une valeur acquise, et il le dit une
seule fois.

Elles ne le sont pas encore sur quatre points que les indicateurs consommeront dès la première
formule, et qui sont des trous dans les blocs déjà rédigés, non dans celui à écrire :

- une ligne n'a qu'un montant par révision, et cela rebase silencieusement le budget à chaque
  avenant (C-041) ;
- la valeur planifiée n'a de règle nulle part (C-042) ;
- les changements d'état d'une tâche ne sont pas datés (C-043) ;
- l'état d'une tâche récapitulative n'est pas défini, alors qu'elle porte les provisions (C-044).

Le premier est bloquant : sans lui, l'indice de coût est faux dès le premier avenant. Les trois
autres sont majeurs. Je recommande de les traiter avant d'ouvrir le §3.4.5.8.

## Constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-041 | bloquant | §3.4.5.1, §3.2.5 | Une ligne n'a qu'un montant par révision : un avenant rebase le budget sur le reste à engager | intégré |
| C-042 | majeur | §3.5.1, glossaire | La valeur planifiée n'a de règle nulle part | intégré |
| C-043 | majeur | §3.4.5.3 | Les changements d'état d'une tâche ne sont pas datés | intégré |
| C-044 | majeur | §3.4.5.3, §3.4.5.5 | L'état d'avancement d'une tâche récapitulative n'est pas défini | intégré |
| C-045 | majeur | glossaire, §3.4.5.2 | Deux définitions de l'année de référence d'un reste à engager | intégré |
| C-046 | majeur | §3.4.5.5 | FBS-4.5.2 et FBS-4.5.3 ont été renumérotés par position, contre la règle du §3.4.1 | intégré |
| C-047 | majeur | §3.4.5.4, §3.4.5.5 | Les lignes sans sous-projet n'ont pas de place dans les indicateurs par sous-projet | intégré |
| C-048 | majeur | §3.1.4 | WF-INTF-0090 : la Vérif teste un refus que le corps n'impose plus | intégré |
| C-049 | majeur | glossaire | « Nœud d'organisation » attribue encore des habilitations à l'organigramme | intégré |
| C-050 | mineur | §3.3.2 | WF-CYC-0010 : la Vérif compte sept statuts | intégré |
| C-051 | mineur | glossaire | Quatre entrées en retard sur le modèle | intégré |
| C-052 | mineur | §3.4.5.3.4 | WF-PLA-0110 et 0120 citent FBS-4.3 au lieu de FBS-4.3.5 | intégré |
| C-053 | mineur | §3.1 | Renvois cassés par la réorganisation | sans objet |

---

## C-041 — Une ligne n'a qu'un montant par révision : un avenant rebase le budget sur le reste à engager

- **gravité** : bloquant
- **emplacement** : §3.4.5.1 WF-REV-0010 et WF-REV-0050 ; §3.4.5.5.3 WF-RAE-0040 ; §3.2.5
- **citation** : « Sa création reprend les structures de la dernière révision marquée » (WF-REV-0010) ; « La révision marquée qui en résulte devient la référence » (WF-REV-0050)

**Constat.** Une ligne de devis porte un montant, et une révision en fige la valeur. Le document
distingue deux montants pour une même ligne — « son montant dans la révision de référence » et
« son montant réestimé » (WF-RAE-0040) — mais il ne les distingue que par la révision où on les
lit : le budget est le montant de la ligne dans la révision de référence, le reste à engager est
son montant dans la révision courante.

Cela tient tant que la référence n'est jamais dérivée de la révision courante. Or c'est
exactement ce que fait un avenant. Suivons-le :

1. la référence R1 chiffre une tâche à 100 ;
2. trois revues périodiques réestiment son reste à engager ; la dernière révision marquée porte
   la ligne à 140 ;
3. un avenant est préparé dans une révision créée à partir de cette dernière révision marquée
   (WF-REV-0010), donc avec la ligne à 140 ;
4. le différentiel est fusionné, et la révision produite devient la référence (WF-REV-0050).

Le budget de la tâche est désormais 140. Les 40 de dérive ont disparu du budget de référence, et
l'indice de coût de cette tâche revient à 1 sans qu'aucun acte contractuel ne l'ait décidé. C'est
le défaut du constat C-001, revenu par une autre porte : au lieu de redésigner la référence à
chaque revue, on la reconstruit à partir du reste à engager à chaque avenant. Sur un projet de
dix ans avec plusieurs avenants, le budget de référence finit par n'être que le dernier reste à
engager.

Le même mécanisme touche les tâches ajoutées en cours d'exécution (WF-RAE-0050) : présentes dans
la révision courante, elles entrent dans la référence produite par l'avenant, alors que
l'exigence dit qu'elles n'y entrent jamais.

**Proposition.** Donner à chaque ligne **deux montants**, et non un : un **montant budgété**, qui
ne change que par la référence, et un **montant réestimé**, qui change à chaque revue. Le budget
de référence est la somme des montants budgétés de la révision de référence ; le reste à engager
suit WF-RAE-0010 sur les montants réestimés. Tout devient alors cohérent sans règle
supplémentaire :

- la fusion d'un avenant ne touche que les montants budgétés des lignes qu'il désigne, et
  laisse les réestimations intactes ;
- une tâche ajoutée en revue porte un montant budgété nul et un montant réestimé : elle pèse
  sur le reste à engager et jamais sur le budget, ce que WF-RAE-0050 demande ;
- les lignes fusionnées d'un risque survenu portent un montant budgété nul, et la ligne de
  provision porte le sien : c'est WF-RIS-0050 sans effort ;
- la grille de reste à engager affiche les trois colonnes qu'elle affiche déjà.

Cela demande de reprendre WF-DEV-0020 (attributs d'une ligne), WF-REV-0050 (ce que la fusion
modifie), WF-RAE-0010 et WF-RAE-0040 (sur quel montant ils portent), la définition de « Budget
de référence », et le §3.2.5. C'est le plus gros chantier de cette revue, et il conditionne
tous les indicateurs de valeur acquise.

**Statut.** intégré

---

## C-042 — La valeur planifiée n'a de règle nulle part

- **gravité** : majeur
- **emplacement** : §3.5.1 ; glossaire, entrée « Valeur planifiée »
- **citation** : « La valeur planifiée s'obtient en étalant les lignes de la référence sur les dates de leurs tâches. »

**Constat.** C'est la seule phrase du document sur le calcul de la valeur planifiée, et elle est
dans un paragraphe descriptif. Quatre questions restent sans réponse, et l'indice de délai
dépend de chacune :

- **quelles lignes** : celles comptées dans le budget de référence, donc sans les provisions des
  risques identifiés ni les lignes fusionnées d'un risque survenu, ou toutes les lignes de la
  structure principale ? Si la valeur planifiée ne totalise pas le budget de référence, l'indice
  de délai ne vaut jamais 1 en fin de projet ;
- **quel étalement** : l'interpolation linéaire de WF-DEV-0040, ou autre chose ? Une ligne portée
  par un jalon n'a pas de durée : sa valeur planifiée tombe-t-elle à la date du jalon ?
- **quelles dates** : celles de la révision de référence, qui ne bougent pas, ou celles de la
  révision courante, qui glissent ? La valeur planifiée doit se lire sur les dates de la
  référence, sinon un retard la déplace avec lui et l'indice de délai ne mesure plus rien ;
- **que devient la courbe quand la référence change** : un avenant produit une nouvelle
  référence, dont les dates et les montants diffèrent. Les points passés de la courbe sont-ils
  recalculés sur la nouvelle référence, ou conservés tels qu'ils ont été mesurés à chaque revue ?

**Proposition.** Une exigence dans FBS-4.4.3, où vivent déjà le calcul des montants et l'année de
consommation, qui fixe les quatre points. Je proposerais : les lignes comptées au budget de
référence, étalées linéairement sur la durée de leur tâche dans la révision de référence,
concentrées à la date du jalon pour celles qu'un jalon porte, et une courbe recalculée
intégralement sur la référence en vigueur — les points passés mesurés à chaque revue étant
conservés par les révisions marquées, où l'on peut toujours les relire.

**Statut.** intégré

---

## C-043 — Les changements d'état d'une tâche ne sont pas datés

- **gravité** : majeur
- **emplacement** : §3.4.5.3, WF-PLA-0130 ; §3.4.5.5.2, WF-RAE-0030
- **citation** : « Une tâche porte un libellé, une description facultative, une durée, une date de début, une date de fin, un mode de planification et un état d'avancement. »

**Constat.** L'état d'avancement est un attribut, pas un événement : rien ne dit quand une tâche
a été démarrée ni quand elle a été terminée. Or la valeur acquise s'acquiert à la terminaison,
et deux indicateurs en dépendent dans le temps : les courbes de valeur acquise (FBS-4.8.8) et
l'indice de délai, qui compare la valeur acquise à la valeur planifiée **à une date**.

Sans date, la valeur acquise n'est connue qu'aux dates de marquage des révisions, puisque chaque
révision fige l'état des tâches. La courbe devient un escalier dont les marches sont les revues,
et une tâche terminée le 3 du mois pèse comme si elle l'avait été le jour de la revue. Sur des
revues mensuelles, l'indice de délai est faux d'un mois au plus, ce qui est peut-être acceptable
— mais il faut le décider, pas le découvrir.

**Proposition.** Deux options, à trancher :

- dater les transitions : une tâche porte la date de son démarrage et celle de sa terminaison,
  saisies par l'utilisateur au moment du geste, avec la date du jour par défaut. La valeur
  acquise se situe alors au jour près ;
- assumer l'escalier : écrire que la valeur acquise est datée du marquage de la révision où la
  tâche apparaît terminée pour la première fois, et que la précision de l'indice de délai est
  celle du rythme des revues.

La première est plus juste et coûte un attribut ; la seconde est plus simple et doit être dite.
Dans les deux cas, WF-PLA-0130 ou le §3.4.5.8 doit le porter.

**Statut.** intégré

---

## C-044 — L'état d'avancement d'une tâche récapitulative n'est pas défini

- **gravité** : majeur
- **emplacement** : §3.4.5.3, WF-PLA-0040 et WF-PLA-0130 ; §3.4.5.5, WF-RAE-0010 et WF-RAE-0030
- **citation** : « Une tâche récapitulative tire ses dates et sa durée de ses subordonnées » (WF-PLA-0040) ; « Le reste à engager d'un projet est la somme, pour chaque tâche de la structure principale […] de zéro si la tâche est terminée, du montant réestimé de ses lignes si elle est démarrée » (WF-RAE-0010)

**Constat.** WF-PLA-0040 dit ce qu'une récapitulative tire de ses subordonnées — ses dates et sa
durée — mais pas son état d'avancement. Or cet état commande trois choses pour les lignes que la
récapitulative porte en propre : leur exposition à la réestimation (WF-RAE-0030), leur part dans
le reste à engager (WF-RAE-0010) et le moment où leur valeur s'acquiert.

Ce ne sont pas des cas marginaux. Les provisions sont portées par la récapitulative du projet
(§3.2.6) ; les licences et les assurances aussi. Sans règle, le Kanban propose-t-il de démarrer
une récapitulative ? Sa valeur s'acquiert-elle quand ses subordonnées sont toutes terminées, ou
quand on saisit un reste à engager nul sur ses lignes propres ?

**Proposition.** Compléter WF-PLA-0040 : une récapitulative est démarrée dès qu'une de ses
subordonnées l'est, et terminée quand toutes le sont ; son état n'est pas saisissable. Ses lignes
propres sont exposées à la réestimation dès qu'elle est démarrée, et leur valeur s'acquiert
quand elle est terminée. Pour la récapitulative du projet, cela signifie que les provisions et
les frais généraux s'acquièrent à la fin du projet — ce qui est cohérent avec WF-RIS-0060 pour
les provisions, et qu'il vaut mieux écrire pour le reste.

**Statut.** intégré

---

## C-045 — Deux définitions de l'année de référence d'un reste à engager

- **gravité** : majeur
- **emplacement** : glossaire, entrée « Année de référence » ; §3.4.5.2, WF-PRJ-0080
- **citation** : « Pour un reste à engager, il s'agit de l'année des taux retenus lors de sa dernière mise à jour » (glossaire) ; « La date de réception de la commande fixe l'année de référence des chiffrages pendant l'exécution, comme le dit le glossaire » (WF-PRJ-0080, Motif)

**Constat.** Le glossaire dit une chose, WF-PRJ-0080 dit l'autre en affirmant citer le glossaire.
Selon la première, l'année de référence d'un reste à engager est celle des taux retenus à sa
dernière mise à jour (WF-REV-0060) ; selon la seconde, c'est l'année de réception de la
commande. Les deux donnent des montants différents dès la seconde année d'exécution, et
WF-DEV-0030 ne sait pas laquelle appliquer.

La première est la bonne : c'est le mécanisme de mise à jour des taux décidé pour WF-REV-0060, et
c'est ce qui permet au reste à engager de passer aux taux constatés. La date de réception de la
commande n'a alors plus ce rôle — reste à savoir si elle en a un autre.

**Proposition.** Corriger le Motif et la Vérif de WF-PRJ-0080 pour retirer ce que la date de
commande ne fait pas. Si elle ne sert à rien d'autre, la retirer des attributs plutôt que de
garder un champ exigé au passage à En cours pour rien. Si elle sert — par exemple à dater le
début du pilotage pour les courbes —, le dire.

**Statut.** intégré

---

## C-046 — FBS-4.5.2 et FBS-4.5.3 ont été renumérotés par position, contre la règle du §3.4.1

- **gravité** : majeur
- **emplacement** : §3.4.5.5, figure 13 ; WF-RAE-0030 et WF-RAE-0040
- **citation** : figure 13 « FBS-4.5.2 Grille de reste à engager » ; WF-RAE-0030 « FBS-4.5.2 » ; WF-RAE-0040 « FBS-4.5.3 »

**Constat.** La figure de l'arborescence donne FBS-4.5.1 aux indicateurs et FBS-4.5.2 à la grille,
et ne connaît pas de FBS-4.5.3. Les exigences donnent FBS-4.5.2 au Kanban et FBS-4.5.3 à la
grille. Le Kanban a été inséré entre les deux, et les codes ont suivi la position des
paragraphes — ce que le §3.4.1 interdit explicitement : une fonction nouvelle prend le prochain
code libre, et une fonction existante garde le sien.

**Proposition.** La grille garde FBS-4.5.2, le Kanban prend FBS-4.5.3. Corriger le champ FBS de
WF-RAE-0030 et de WF-RAE-0040, et ajouter le nœud FBS-4.5.3 Démarrage de tâche à la page draw.io
de FBS-4.5. C'est précisément le cas que le §3.4.1 décrit pour FBS-4.2.4 et FBS-4.3.5.

**Statut.** intégré

---

## C-047 — Les lignes sans sous-projet n'ont pas de place dans les indicateurs par sous-projet

- **gravité** : majeur
- **emplacement** : §3.4.5.4.1 WF-DEV-0060 ; §3.4.5.5.1 WF-RAE-0020 ; §3.4.5.7
- **citation** : « la somme des totaux par sous-projet augmentée des lignes sans sous-projet » (WF-DEV-0060, Vérif) ; « Pour chaque sous-projet, il présente l'écart entre le budget du sous-projet et la somme de son coût réel et de son reste à engager » (WF-RAE-0020)

**Constat.** Une ligne de devis appartient facultativement à un sous-projet, et une ligne de
coût peut être imputée au seul projet. L'avancement financier se calcule par sous-projet, à la
maille « la plus fine où les deux mondes se rejoignent ». Les lignes qui n'appartiennent à aucun
sous-projet — et il y en aura toujours : les provisions, les frais généraux, les coûts d'un
sous-projet pas encore déclaré — tombent hors de tous les sous-projets, et leurs totaux ne
s'additionnent plus à celui du projet.

**Proposition.** Nommer la maille résiduelle : un ensemble « hors sous-projet » qui reçoit les
lignes de devis sans sous-projet et les lignes de coût imputées au seul projet, et qui apparaît
dans toutes les ventilations par sous-projet comme une ligne de plus. Une phrase dans le §3.4.5.7
et une dans WF-RAE-0020 suffisent, mais elles doivent exister avant que les indicateurs ne
totalisent quoi que ce soit.

**Statut.** intégré

---

## C-048 — WF-INTF-0090 : la Vérif teste un refus que le corps n'impose plus

- **gravité** : majeur
- **emplacement** : §3.1.4, WF-INTF-0090
- **citation** : « Un import sur un projet à l'état Créé est refusé. » (Vérif)

**Constat.** Le refus à l'état Créé a été retiré du corps quand l'état Initialisé a disparu : un
import crée désormais une révision, ce qui fait passer le projet à Chiffrage. La Vérif teste
toujours le refus. Le Motif, lui, dit encore qu'« une révision porte un couple planning/devis ou
planning/reste à engager », formulation antérieure aux structures de coûts.

**Proposition.** Retirer la dernière phrase de la Vérif, et remplacer dans le Motif « Une révision
porte un couple planning/devis ou planning/reste à engager, dont les deux facettes sont figées
ensemble au marquage » par « Une révision est un instantané, figé au marquage ».

**Statut.** intégré

---

## C-049 — « Nœud d'organisation » attribue encore des habilitations à l'organigramme

- **gravité** : majeur
- **emplacement** : glossaire, entrée « Nœud d'organisation »
- **citation** : « […] et d'influencer l'attribution des rôles d'habilitation. »

**Constat.** Le §3.2.2 dit que l'arbre « ne porte aucune habilitation », WF-ADM-0030 que le
rattachement d'un utilisateur à un nœud « n'accorde aucune permission ». La définition dit le
contraire, et c'est elle qu'un lecteur pressé consultera.

**Proposition.**

> **Nœud d'organisation.** Désigne une unité de la structure organisationnelle de l'entreprise,
> un service ou un département. Les nœuds forment un arbre qui classe les rôles de ressources.
> Ils ne portent aucune habilitation.

**Statut.** intégré

---

## C-050 — WF-CYC-0010 : la Vérif compte sept statuts

- **gravité** : mineur
- **emplacement** : §3.3.2, WF-CYC-0010
- **citation** : « Les listes, filtres et en-têtes de projet ne proposent que ces sept statuts »

**Constat.** Le corps en compte six depuis la suppression d'Initialisé.

**Proposition.** « ces six statuts ».

**Statut.** intégré

---

## C-051 — Quatre entrées du glossaire en retard sur le modèle

- **gravité** : mineur
- **emplacement** : glossaire
- **citation** : « Les rôles de ressources sont affectés aux lignes de devis afin de chiffrer les devis et les restes à engager. »

**Constat.**
- **Rôle de ressource** ne dit ni qu'il relève d'une catégorie, ni qu'il porte un calendrier, ni
  que c'est par lui qu'une tâche obtient ses jours travaillés (WF-REF-0090, WF-PLA-0010). C'était
  différé en attendant PO-02, qui est clos.
- **Tâche feuille** garde « située au niveau le plus détaillé de la structure du projet » ; le
  constat C-029 proposait « une tâche qui ne comporte aucune sous-tâche », et seule l'entrée
  « Tâche » a été reprise.
- **Année de référence** parle de « coefficient d'inflation » ; le terme est « taux d'inflation ».
- **Catégorie de coût** porte « un code comptable unique » (WF-REF-0040) dont plus rien ne se sert
  depuis que l'import des coûts réels ignore la nature comptable. Ce n'est pas faux, mais le
  Motif de WF-REF-0040 justifie ce code par le rapprochement comptable, qui n'a plus lieu.

**Proposition.** Reprendre les trois premières. Pour la quatrième, soit garder le code comptable
à titre documentaire et le dire, soit le rendre facultatif.

**Statut.** intégré

---

## C-052 — WF-PLA-0110 et 0120 citent FBS-4.3 au lieu de FBS-4.3.5

- **gravité** : mineur
- **emplacement** : §3.4.5.3.4
- **citation** : champ FBS « FBS-4.3 »

**Constat.** La fonction FBS-4.3.5 Arborescence de tâches existe dans la figure, et les deux
exigences qui la spécifient renvoient à sa parente.

**Proposition.** FBS-4.3.5 dans les deux.

**Statut.** intégré

---

## C-053 — Renvois cassés par la réorganisation

- **gravité** : mineur
- **emplacement** : §3.1.4 ; WF-INTF-0010 ; huit exigences du §3.1.4 ; §3.2 et §3.2.1
- **citation** : « L'inventaire des flux, avec leur sens et leur fréquence, figure au paragraphe suivant » (§3.1.4)

**Constat.** Trois choses, dont deux déjà signalées et en cours :
- le §3.1.4 renvoie l'inventaire des flux « au paragraphe suivant » ; il est au §3.1.2, deux
  paragraphes avant ;
- les renvois d'annexe reprennent le titre entier — « de ANNEXE B: Formats d'échanges Excel » —
  dans neuf endroits, avec deux tournures cassées (« définit par », « de ANNEXE ») ;
- la Vérif de WF-INTF-0010 contient « du Tableau 3 Flux avec les systèmes externes(FLX-01 à
  FLX-07) », sans espace avant la parenthèse.

**Proposition.** « figure au tableau des flux » pour le premier ; pour les autres, des champs de
renvoi limités au numéro.

**Statut.** sans objet — le « paragraphe suivant » et la parenthèse de WF-INTF-0010 sont corrigés ; les renvois d\'annexe sont des champs Word que l\'auteur conserve tels quels

---

## Ce que le §3.4.5.8 devra trancher lui-même

Ces points ne sont pas des défauts des blocs existants : ce sont les décisions que le bloc des
indicateurs devra prendre, listées ici pour qu'elles ne surprennent pas.

1. **La date de calcul.** Un indicateur se calcule à une date : celle du marquage de la révision
   de revue est la candidate naturelle. Le coût réel à cette date est-il la somme des lignes dont
   la date de pièce est antérieure, ou la somme de tout ce qui a été importé ?
2. **Le reste à engager comprend-il les provisions des risques identifiés ?** WF-RAE-0010 somme
   les lignes des tâches non démarrées à leur montant de référence, ce qui inclut les provisions
   portées par la récapitulative du projet. Le projeté à terminaison contient alors la réserve
   pour risques. C'est défendable — c'est même prudent — mais il faut le dire, et dire qu'une
   provision écartée vaut zéro.
3. **Les cas limites** : coût réel nul avant le premier import, valeur planifiée nulle avant le
   début du projet, budget de référence nul avant la contractualisation.
4. **La discontinuité du budget** quand le dernier risque est écarté (WF-RIS-0050) : les courbes
   la montreront, et le texte devra l'expliquer.
5. **La granularité** : quels indicateurs se calculent par sous-projet, lesquels seulement au
   niveau du projet. L'avancement financier est par sous-projet ; les indices de coût et de délai
   peuvent l'être aussi, le diagramme temps/temps non.
6. **Les formules du glossaire.** Elles y sont depuis le début, et le §3.4.5.8 devait ne pas les
   répéter. Mais une formule est une règle de calcul, et le glossaire n'est pas l'endroit d'une
   règle : c'est le moment de les déplacer dans les exigences des indicateurs, et de ne laisser
   au glossaire que le nom.
