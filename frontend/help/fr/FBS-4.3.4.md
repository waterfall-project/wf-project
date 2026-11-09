# Imports et exports

## Ce que montre l’écran

Une feuille de la [planification](FBS-4.3.md), où se font les échanges de fichiers du projet : le planning MS Project, le devis, le reste à engager et les coûts réels s’y importent, et la révision lue s’y exporte. L’en-tête du planning y mène, comme ceux du devis, du reste à engager et des coûts réels quand leur import vous est offert. L’écran se montre à qui lit le planning, ou à qui le projet offre un import.

Un import se fait en deux temps. Le fichier est déposé et analysé, sans rien changer au projet ; son **compte rendu** dit ce que l’import ferait. Puis il s’applique, après confirmation, en une seule opération — ou s’abandonne, et le projet reste tel qu’il était. Un import de planning, de devis ou de reste à engager s’applique à la révision en cours, quelle que soit la révision lue, et la crée si le projet n’en a pas ; un import de coûts réels n’écrit dans aucune révision : les coûts réels appartiennent au projet.

De haut en bas :

- **Importer un fichier**, une commande par nature de fichier que le projet vous offre ;
- le compte rendu de l’import que l’adresse nomme, quand il y en a un ;
- **Imports du projet** : chaque import ouvert, avec son fichier, sa nature, son état et sa date, une page à la fois ;
- **Demander un export**, de la révision lue.

## Ses commandes

- **Importer un planning MS Project**, **Importer un devis**, **Importer un reste à engager**, **Importer des coûts réels** : chacune suit la commande que le projet liste, et dit, indisponible, la condition qui lui manque. Elle ouvre le choix du **Fichier à importer**, puis **Analyser le fichier**. Un fichier trop grand est refusé aussitôt ; son contenu, l’analyse le juge. Une extraction de coûts réels déclare la **Période extraite**, **Du** et **Au**, si vous la donnez.
- Les coûts réels ne s’importent que si la correspondance de l’extraction est complète (« correspondance de l’extraction des coûts réels complète ») : l’écran nomme les colonnes exigées sans intitulé, et **Régler la correspondance de l’extraction** mène à la [correspondance](FBS-3.1.3.md).
- L’analyse est un traitement de fond : le suivi des tâches propose de recharger l’écran quand elle a abouti.
- **Appliquer l’import**, sur un compte rendu analysé, demande une confirmation — **Confirmer l’application** —, puis s’applique en traitement de fond. Les deux commandes suivent ce que l’import liste lui-même, et disent, indisponibles, la condition qui leur manque : l’application, quand le compte rendu n’est pas en attente de décision (« import en attente de décision ») ou rejette le fichier entier (« fichier accepté par le compte rendu ») ; l’abandon, quand l’import est appliqué ou en cours d’application (« import non appliqué »).
- **Abandonner l’import** n’applique rien, et ramène l’écran à ce qu’il était.
- Un import **Refusé** l’a été à l’application — droits, état du projet ou fichier rejeté par le compte rendu — : le fichier est supprimé, et l’import est à relancer. Le compte rendu et la liste des imports le disent.
- **Demander un export** : la nature du **Fichier à exporter** parmi celles que la révision offre — le planning MS Project, le devis, le reste à engager, l’image de l’arborescence de tâches —, avec, pour le reste à engager, la **Date de la revue** qu’il porte, et, pour l’image, le **Niveau de l’arborescence** où elle s’arrête. Le fichier se fait à la demande, en traitement de fond, et se télécharge depuis le suivi des tâches ; il n’est pas conservé : le service le supprime à la fin du premier téléchargement complet, un téléchargement interrompu le laisse disponible, et un fichier jamais téléchargé disparaît au bout de vingt-quatre heures. Le planning s’exporte en XML MS Project, sous le nom `ms-project-` suivi du code du projet : il s’ouvre dans MS Project avec les mêmes dates, et se réimporte sans perdre vos tâches. Un projet terminal s’exporte encore.

## Ses colonnes et ses valeurs calculées

Le compte rendu est celui du serveur. Il dit le nombre de lignes lues, les motifs qui demandent une confirmation explicite, les lignes rejetées avec leur ligne, leur onglet et leur motif — ou les motifs qui rejettent le fichier entier, rien ne s’appliquant alors —, les écarts avec les données existantes, objet par objet, et les éléments que l’import ignore. Pour un planning MS Project, il dit aussi les tâches que le fichier date autrement, ce que Waterfall recalcule faisant foi, et les valeurs gardées et signalées (une tâche démarrée ou terminée que le fichier ne porte plus est conservée), la date de début du projet quand elle diffère, et ce que l’import ignore : ressources, calendriers, avancement, coûts, champs personnalisés et contraintes de date. Un fichier qui n’est pas un XML MS Project est refusé à l’ouverture. Pour un reste à engager, il nomme les tâches que l’import termine, parce qu’il met à zéro le reste à engager de toutes leurs lignes, à la date de la revue que porte le fichier. Pour des coûts réels, il désigne une ligne par sa pièce et son poste — deux lignes du fichier de même pièce et de même poste sont rejetées —, et nomme chaque colonne de l’extraction ni lue ni conservée. Un compte rendu s’applique jusqu’à la date qu’il dit ; au-delà, l’import expire.

## Les gestes au clavier

- `Tab` parcourt les commandes d’import, les champs, le compte rendu, ses tables et ses commandes, puis la liste des imports et le formulaire d’export.
- Une table du compte rendu qui dépasse sa boîte défile aux flèches une fois atteinte.
- Dans la confirmation, qui s’ouvre dans la page, **Annuler** revient au compte rendu sans rien appliquer.
- `F1` ouvre cette aide.

## Voir aussi

- [La planification](FBS-4.3.md), [le devis](FBS-4.4.md), [le reste à engager](FBS-4.5.md), [les coûts réels](FBS-4.7.md) ;
- [la correspondance de l’extraction des coûts réels](FBS-3.1.3.md) ;
- [l’arborescence de tâches](FBS-4.3.5.md), qui s’exporte en image.
