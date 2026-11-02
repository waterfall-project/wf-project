# Correspondance de l’extraction des coûts réels

## Ce que montre l’écran

Comment Waterfall lit l’extraction des coûts réels de l’ERP, pour toute l’installation. L’ERP nomme ses colonnes à sa façon : pour chacune des cinq colonnes que l’import lit — **Sous-projet** (l’élément d’OTP), **N° de pièce**, **Poste**, **Date de pièce**, **Montant** —, la liste des intitulés qui la désignent dans l’extraction ; puis les **Colonnes conservées**, celles de l’extraction que Waterfall garde à titre d’information et restitue à la consultation des lignes importées.

Le poste est facultatif, les quatre autres colonnes sont exigées. Au-dessus des listes, une barre dit les colonnes exigées qui n’ont pas d’intitulé, ou que la correspondance est complète. Elle est vide à l’installation, et l’import des coûts réels est refusé tant qu’elle est incomplète.

Un intitulé se compare à l’en-tête du fichier, et aux autres intitulés, sans égard à la casse, aux accents ni aux espaces en bout. Une colonne de l’extraction ni lue ni conservée est ignorée, et le compte rendu de l’import la nomme. Une modification vaut pour les imports suivants, et ne change aucune ligne déjà importée.

## Ses commandes

À qui ne peut pas modifier les paramètres de coûts, l’écran montre les listes, sans commande. Aux autres, un formulaire :

- **Ajouter un intitulé** à une colonne lue, et la corbeille d’un intitulé pour le retirer ;
- **Déclarer une colonne conservée**, et la corbeille pour la retirer ; une colonne lue ne se déclare pas aussi conservée ;
- **Enregistrer la correspondance** remplace la correspondance entière. Le serveur juge les intitulés : un intitulé refusé l’est à son champ, qui prend le focus, et un doublon nomme l’intitulé qu’il double. Si la correspondance a changé depuis sa lecture, le refus offre de relire la page.

Les champs attendent la réponse du serveur pendant l’enregistrement.

## Ses colonnes et ses valeurs calculées

Aucune table : la barre des colonnes exigées sans intitulé est celle que le serveur calcule, à la lecture comme après un enregistrement.

## Les gestes au clavier

- `Tab` parcourt les intitulés, leurs corbeilles et les commandes, dans l’ordre des colonnes.
- `Entrée` dans un intitulé enregistre la correspondance.
- `F1` ouvre cette aide.

## Voir aussi

- [Les paramètres de coûts](FBS-3.1.md) ;
- [les coûts réels d’un projet](FBS-4.7.md), où l’extraction s’importe.
