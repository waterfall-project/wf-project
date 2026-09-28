# Trous de la spécification, à intégrer au document Word

Ce fichier accumule ce que le cadrage et la construction révèlent : des décisions prises en
route qui devraient vivre dans la spécification, et n'y sont pas. L'auteur les intègre au
Word en une passe, lance `make build-doc`, puis efface les entrées intégrées. Chaque entrée
suit la forme des constats de revue : où, quoi, et un texte proposé — à retravailler
librement dans le document.

## 1. L'écran d'accueil à la connexion

- **Où** : §3.6 (principes d'interface), nouvelle exigence — prochain identifiant libre
  `WF-IHM-0120`.
- **Quoi** : rien ne dit ce qu'un utilisateur voit en arrivant. Décidé au cadrage d'EP-02
  (2026-09-28) : la liste des projets dont il est contributeur.
- **Hypothèse à trancher en intégrant** : c'est un filtre par défaut, visible et levable —
  pas une restriction de lecture, qui contredirait WF-PRJ-0060 (« la consultation ne dépend
  que des habilitations »).
- **Texte proposé** — Corps : « À la connexion, l'utilisateur voit la liste des projets dont
  il est contributeur. Ce filtre est visible et peut être levé pour voir tout ce que ses
  habilitations permettent de consulter. » Vérif : « Un contributeur de deux projets les
  voit à sa connexion ; la levée du filtre montre aussi les projets qu'il peut seulement
  consulter. »

## 2. Introuvable et lecture refusée : le même écran

- **Où** : WF-ADM-0110 (corps), ou §3.6.
- **Quoi** : le contrat répond 404 quand la permission de consultation manque, précisément
  pour que l'existence d'un objet ne fuie pas. L'interface doit tenir la même ligne : une
  adresse inexistante et une lecture refusée mènent au même écran « introuvable ». La spec
  ne le dit que côté API.
- **Texte proposé** (corps de WF-ADM-0110, ajout) : « L'interface présente le même écran
  pour un objet inexistant et pour un objet dont la consultation n'est pas permise. »

## 3. L'installation neuve guide vers le référentiel

- **Où** : WF-CYC-0120 (corps ou Vérif), ou l'exigence de l'entrée 1.
- **Quoi** : tant que le référentiel minimal est incomplet, la création de projet est
  refusée (WF-CYC-0120). Rien ne dit ce que voit l'administrateur d'une installation
  neuve : un accueil vide sans explication serait une impasse.
- **Texte proposé** (Vérif, ajout) : « Sur une installation dont le référentiel est
  incomplet, l'accueil énonce les prérequis manquants et mène au référentiel. »

## 4. La session qui expire ramène où l'on allait

- **Où** : WF-SEC-0020 (corps), ou §3.6.
- **Quoi** : rien ne dit ce que vit l'utilisateur quand sa session expire en cours de
  travail.
- **Texte proposé** (corps, ajout) : « Une session expirée mène à l'écran de connexion ;
  la connexion refaite ramène à l'écran visé. »

## 5. La saisie des nombres suit la langue

- **Où** : WF-INTF-0180 (corps).
- **Quoi** : l'exigence couvre l'affichage (« 1 234,56 » / « 1,234.56 ») mais pas la
  saisie. Décidé au cadrage : on saisit au format de sa langue, la valeur voyage en décimal
  exact.
- **Texte proposé** (corps, ajout) : « La saisie d'un nombre suit le format de la langue de
  l'interface — virgule décimale en français, point en anglais. »

## 6. Les horodatages s'affichent en heure locale

- **Où** : WF-DAT-0100 ou WF-INTF-0180 (corps).
- **Quoi** : les horodatages sont conservés en temps universel, les dates de planning sans
  heure ne bougent jamais de fuseau — mais rien ne dit dans quelle heure s'affiche un
  horodatage (date de calcul d'un indicateur, colonnes d'audit). Décidé au cadrage : l'heure
  locale du poste.
- **Texte proposé** (corps de WF-DAT-0100, ajout) : « Un horodatage s'affiche dans l'heure
  locale du poste ; une date de planning s'affiche telle quelle. »
