# Modèle d'un EPIC et de ses US

Copier ce qui suit dans `EP-nn-<intitulé>.md`, et n'y laisser aucun `<…>`. Les règles —
identifiants, statuts, traçabilité — sont dans [`README.md`](README.md).

Un EPIC porte ses US dans le même fichier, à la suite de son propre en-tête.

---

```markdown
---
id: EP-nn
titre: <ce que l'EPIC rend possible, en une ligne>
statut: à planifier
depend_de: <EP-nn, ou « rien »>
issue: <numéro, rempli au démarrage>
---

# EP-nn — <titre>

## Objet

<Ce que cet EPIC rend possible, du point de vue de celui qui s'en sert, et pourquoi il
vient à ce rang plutôt qu'à un autre. Deux paragraphes au plus.>

## Ce qui en fait partie

- <…>

## Ce qui n'en fait pas partie

- <ce qu'on pourrait croire dedans, et où cela se trouve — l'EPIC qui le porte, ou rien>

## Exigences réalisées

<Les identifiants, groupés par domaine. C'est de cette liste que se déduit la couverture,
et une exigence citée ici doit l'être par au moins une US ci-dessous.>

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-CODE-0010-A` | <titre de l'exigence> | <entière, début — close en EP-nn, ou fin — amorcée en EP-nn> | US-nnnn |

## Opérations du contrat

<Les `operationId` consommés ou servis, tels qu'ils figurent dans docs/api. Une opération
qui manque au contrat se note ici : c'est une modification du contrat, donc un travail
qui précède.>

## Préalables

<Ce qui doit être vrai pour démarrer : un autre EPIC livré, une décision prise, un outil
installé. « rien » est une réponse.>

## Définition de fini

<Ce qui se constate, pas ce qui se déclare : les commandes qui passent, ce qu'un tiers
peut faire tourner et voir. C'est cette liste qui autorise le statut « livré ».>

## Conception

<Écrite après les US, validée avant le plan de lots ; c'est elle qui fait passer l'EPIC
`prêt`. Ce qu'un développeur ou un agent devrait sinon décider seul, lot par lot :

- les tables et les migrations, avec leurs contraintes (§4.4.1) ;
- les modules du noyau touchés, et ce que chacun expose aux autres ;
- les modifications du contrat, faites avant le code qui les consomme ;
- l'ordre de construction : ce qui doit exister avant quoi ;
- les décisions prises, chacune avec l'option écartée et la raison.

Pas de code, pas de pseudo-code d'algorithme : ce qui relève d'un lot reste au lot.>

---

## US-nnnn — <titre court>

- **statut** : à faire
- **exigences** : `WF-CODE-0010-A`, `WF-CODE-0020-A`
- **opérations** : `listProjects`, `getProject`
- **issue** : <numéro, rempli au démarrage>

**En tant que** <chef de projet, manager ou administrateur — §3.1.3 ; ou « développeur » et
« exploitant » lorsque l'US ne sert aucun des trois acteurs : socle, chaîne, exploitation>,
**je veux** <…>, **afin de** <…>.

**Critères d'acceptation.**

<Repris mot pour mot des champs Vérif des exigences citées, exemples chiffrés compris
(WF-QUA-0020). Un critère reformulé porte la mention « écart : <pourquoi> ».>

- `WF-CODE-0010-A` — « <citation du champ Vérif> »
- <critère propre à l'US, lorsque le Vérif ne dit rien de l'écran ou du parcours>

**Notes de réalisation.**

<Optionnel : ce que celui qui prendra la US doit savoir et ne devinerait pas — une
décision du contrat, un piège de calcul, un renvoi à une revue. Pas de conception
d'écran ici.>

**Hors périmètre.**

<Optionnel, mais ce qui évite la US qui grossit en cours de route.>
```
