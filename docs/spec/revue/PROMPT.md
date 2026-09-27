# Revue de la spécification Waterfall — instructions pour l'agent

## Contexte

`waterfall-spec.md` est une projection générée du document Word `stb-waterfall.docx`
et du fichier `waterfall.visuels.drawio`. Ces deux fichiers sont la source ; le
Markdown ne l'est pas.

**Tu ne modifies aucun fichier du dépôt.** Ta seule sortie est un fichier de
constats dans `revue/constats/`. Les corrections sont appliquées à la main dans
Word par l'auteur ; c'est pour cela que chaque constat doit être localisable dans
Word sans ambiguïté.

## Ce que tu produis

Un fichier `revue/constats/AAAA-MM-JJ-<périmètre>.md` conforme à
`revue/constats/MODELE.md`. Chaque constat porte obligatoirement :

- un **emplacement** : le numéro de section (`§3.3.4.2`) et, s'il y a lieu,
  l'identifiant d'exigence (`WF-ADM-0010-A`). Les numéros de section du Markdown
  sont ceux de Word : ils servent d'ancre pour retrouver le passage ;
- une **citation** : le texte exact tel qu'il figure dans la spécification, assez
  long pour être retrouvé par recherche dans Word, assez court pour rester lisible ;
- une **proposition** : la rédaction de remplacement, pas seulement le problème.
  Un constat sans proposition rédigée est un constat que l'auteur devra refaire.

## Suivi des revues précédentes

Avant tout nouveau constat, relis les fichiers de `revue/constats/`. Pour chaque
constat encore « à traiter », indique en tête de ta revue s'il est résolu, résolu
en partie ou toujours ouvert dans la version actuelle, en citant ce qui a changé.
Tu ne modifies pas ces fichiers : c'est l'auteur qui met à jour les statuts.

Un constat toujours ouvert n'est pas recopié comme nouveau constat.

## Ce que tu cherches

Par ordre de priorité :

1. **Exigences non vérifiables.** Le champ `verification` doit décrire une
   condition observable. « Le système est performant » n'en est pas une.
2. **Exigences ambiguës ou non atomiques.** Une exigence qui contient « et »,
   « le cas échéant », « si nécessaire » en cache souvent plusieurs, ou aucune.
3. **Contradictions** entre deux passages, ou entre le texte et un diagramme
   Mermaid. Les diagrammes sont dans le document : compare-les au texte.
4. **Trous fonctionnels.** Une section du découpage fonctionnel sans exigence,
   un flux du diagramme de contexte qui n'est décrit nulle part, un terme employé
   dans le corps du texte mais absent du tableau des définitions (§1.3).
5. **Incohérences de terminologie.** Le document définit un vocabulaire en §1.3 ;
   signale les endroits où le corps du texte s'en écarte.
6. **Périmètre.** Un élément du périmètre exclu (§2.2) qui réapparaît en exigence.

## Ce que tu ne signales pas

- Les exigences encore vides : ce sont des gabarits assumés, l'auteur le sait.
  Ne produis pas un constat par gabarit. Si leur nombre pose question, fais-en
  **un seul** constat de synthèse.
- Les identifiants `WF-CODE-xxxx` dupliqués : le build les signale déjà.
- Les sujets inscrits en annexe B « Points ouverts » : ils sont connus et en
  cours d'arbitrage. Tu peux en revanche signaler un passage du document qui
  tranche l'un de ces sujets sans le dire, ou qui le contredit.
- La mise en forme, la typographie, les fautes d'orthographe isolées — sauf si
  elles changent le sens d'une exigence.
- Les choix de conception. Tu revois la spécification, pas le produit.

## Gravités

| Gravité | Sens |
|---|---|
| bloquant | L'exigence ne peut pas être implémentée ni vérifiée telle quelle. |
| majeur | Interprétable de plusieurs façons ; un développeur se tromperait. |
| mineur | Améliore la clarté, sans risque d'erreur d'implémentation. |

Classe honnêtement. Une revue où tout est bloquant ne se traite pas.
Si une section est correcte, ne cherche pas à y trouver un constat.
