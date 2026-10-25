# Exemples des formats d'échange

Ce dossier porte des fichiers de référence pour les formats Excel de l'annexe B de la
spécification. Ils servent au cadrage et à la discussion ; ils ne font pas foi. Les formats
sont décrits par la spécification, et les décisions qui les ont fixés se lisent dans
`../revue/constats/2026-10-22-reprise.md` (C-370).

| Fichier | Contenu |
|---|---|
| `prototype_devis.py` | engendre un fichier au format « Devis », version 1, comme Waterfall le produirait, à partir de données inventées |
| `devis-prototype.xlsx` | le fichier qu'il engendre |
| `prototype_rae.py` | engendre un fichier au format « Reste à engager », version 1, sur les mêmes données une fois le projet En cours |
| `rae-prototype.xlsx` | le fichier qu'il engendre |
| `check_xlsx.py` | deux contrôles que LibreOffice ne fait pas et qu'Excel sanctionne : un total de tableau non déclaré, une formule qui lit sa propre cellule |

Les prototypes ne sont pas le code de Waterfall : l'export du back s'en inspirera au cadrage
d'EP-07 pour le devis, d'EP-09 pour le reste à engager. Ils se sont construits sur les exemples
et les indications de l'auteur du 2026-10-22, qui ne sont pas versés ici.

## Régénérer

Depuis la racine du dépôt :

```bash
uv run --with xlsxwriter --with openpyxl --with lxml python docs/spec/exemples/prototype_devis.py docs/spec/exemples/devis-prototype.xlsx
uv run --with xlsxwriter --with openpyxl --with lxml python docs/spec/exemples/prototype_rae.py docs/spec/exemples/rae-prototype.xlsx
uv run --with openpyxl --with lxml python docs/spec/exemples/check_xlsx.py docs/spec/exemples/devis-prototype.xlsx
uv run --with openpyxl --with lxml python docs/spec/exemples/check_xlsx.py docs/spec/exemples/rae-prototype.xlsx
```

Le classeur n'enregistre pas les valeurs de ses formules : Excel et LibreOffice les calculent
à l'ouverture.

## Ce que le prototype a appris

- Une formule écrite dans la ligne de total d'un tableau Excel doit y être déclarée
  (`totalsRowFunction`) : sinon Excel répare le tableau à l'ouverture.
- La forme courte `[Colonne]`, qu'XlsxWriter écrit pour un total, passe dans Excel et pas dans
  LibreOffice : une formule nomme toujours son tableau.
- Une formule ne lit jamais une plage qui contient sa propre cellule, même écartée par un
  critère : Excel signale une référence circulaire, LibreOffice calcule sans rien dire.
- Les fonctions sont celles de toutes les versions d'Excel et de LibreOffice : `SOMME.SI.ENS`,
  `INDEX`/`EQUIV`, `SOUS.TOTAL` ; ni `RECHERCHEX`, ni `FILTRE`, ni tableaux dynamiques.
