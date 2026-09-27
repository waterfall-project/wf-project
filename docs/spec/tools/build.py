#!/usr/bin/env python3
"""Projette la spécification Word + draw.io en Markdown destiné à un agent.

Word et draw.io restent les sources ; ce script régénère `waterfall-spec.md`,
qui ne doit jamais être édité à la main. Le Markdown produit ajoute deux choses
absentes du .docx et nécessaires au retour des revues : la numérotation de
section sur chaque titre, et un ancrage explicite (section + identifiant) sur
chaque exigence.
"""

import argparse
import html
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import date

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "tools"))

import drawio2mermaid  # noqa: E402

CHAMPS_EXIGENCE = {
    "ID": "id",
    "Titre": "titre",
    "Flex": "flexibilite",
    "FBS": "fbs",
    "PBS": "pbs",
    "Corp": "corps",
    "Motif": "motif",
    "Vérif": "verification",
}

MOTS_CLES_MERMAID = (
    "flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram",
    "stateDiagram-v2", "erDiagram", "journey", "gantt", "pie", "mindmap",
    "timeline", "quadrantChart", "requirementDiagram", "C4Context",
)

RE_ENTREE_SOMMAIRE = re.compile(
    r"^\[(?:(\d+(?:\.\d+)*)\.\s+)?(.+?)\s+\[\d+\]\(#[^)]*\)\]\(#[^)]*\)$"
)
RE_ANCRE = re.compile(r'<span id="[^"]*" class="anchor"></span>')
RE_LEGENDE = re.compile(r"^(Figure|Tableau)\s*(\d+)?\s*[:–—-]?\s*(.*)$")
RE_IMG = re.compile(r'^<img\s+(?P<attrs>.*?)\s*/?>$', re.S)
RE_ATTR = re.compile(r'(\w+)="([^"]*)"')
RE_FLECHE = re.compile(r"(-{2,3}>|={2,3}>|-\.->|-{3,}|={3,}|--[ox])")


class Journal:
    """Sépare ce qui demande une décision de ce qui relève de la traçabilité."""

    def __init__(self, verbeux=False):
        self.avertissements = []
        self.details = []
        self.verbeux = verbeux

    def avertir(self, message, niveau="attention"):
        (self.details if niveau == "info" else self.avertissements).append(message)

    def afficher(self):
        for message in self.avertissements:
            print(f"  ! {message}", file=sys.stderr)
        if self.verbeux:
            for message in self.details:
                print(f"  - {message}", file=sys.stderr)
        elif self.details:
            print(f"  - {len(self.details)} message(s) de traçabilité "
                  f"(relancer avec --verbeux)", file=sys.stderr)


# --------------------------------------------------------------------------- #
# Étape 1 : extraction pandoc
# --------------------------------------------------------------------------- #

def extraire_docx(docx, dossier_media):
    resultat = subprocess.run(
        ["pandoc", str(docx), "-t", "gfm", "--wrap=none",
         f"--extract-media={dossier_media}"],
        capture_output=True, text=True, check=True,
    )
    return resultat.stdout


# --------------------------------------------------------------------------- #
# Étape 2 : sommaire, ancres, numérotation des titres
# --------------------------------------------------------------------------- #

def normaliser(titre):
    titre = titre.replace("’", "'").replace("\xa0", " ")
    return re.sub(r"\s+", " ", titre).strip().rstrip(":").lower()


def lire_sommaire(lignes):
    """Numéros de section tels que Word les a figés, indexés par titre normalisé.

    Sert uniquement à repérer les titres non numérotés et à détecter un sommaire
    Word périmé ; la numérotation émise, elle, est recalculée depuis la structure.
    """
    numeros, sans_numero = {}, set()
    for ligne in lignes:
        correspondance = RE_ENTREE_SOMMAIRE.match(ligne.strip())
        if not correspondance:
            continue
        numero, titre = correspondance.group(1), normaliser(correspondance.group(2))
        if titre.startswith(("figure ", "tableau ")):
            continue
        if numero:
            numeros.setdefault(titre, numero)
        else:
            sans_numero.add(titre)
    return numeros, sans_numero


def retirer_sommaire(lignes):
    """Supprime les entrées de sommaire et leurs intertitres : un agent lit les titres."""
    intertitres = {"sommaire", "liste des figures", "liste des tables",
                   "liste des tableaux", "table des matières"}
    gardees = []
    for ligne in lignes:
        depouillee = ligne.strip()
        if RE_ENTREE_SOMMAIRE.match(depouillee):
            continue
        if normaliser(depouillee) in intertitres:
            continue
        gardees.append(ligne)
    return gardees


def numeroter_titres(lignes, numeros_word, sans_numero, journal):
    """Préfixe chaque titre de son numéro de section, recalculé depuis la structure."""
    compteurs, sorties = [], []
    for ligne in lignes:
        correspondance = re.match(r"^(#{1,6})\s+(.*)$", ligne)
        if not correspondance:
            sorties.append(ligne)
            continue
        niveau, titre = len(correspondance.group(1)), correspondance.group(2).strip()
        cle = normaliser(titre)
        if cle in sans_numero:
            sorties.append(f"{'#' * niveau} {titre}")
            continue
        del compteurs[niveau:]
        while len(compteurs) < niveau:
            compteurs.append(0)
        compteurs[niveau - 1] += 1
        numero = ".".join(str(c) for c in compteurs)
        attendu = numeros_word.get(cle)
        if attendu and attendu != numero:
            journal.avertir(
                f"sommaire Word périmé : « {titre} » y est numéroté {attendu}, "
                f"la structure du document donne {numero}"
            )
        sorties.append(f"{'#' * niveau} {numero}. {titre}")
    return sorties


def section_courante(lignes, index):
    for ligne in reversed(lignes[:index]):
        correspondance = re.match(r"^#{1,6}\s+(\d+(?:\.\d+)*)\.", ligne)
        if correspondance:
            return correspondance.group(1)
    return ""


# --------------------------------------------------------------------------- #
# Étape 3 : figures -> Mermaid
# --------------------------------------------------------------------------- #

def decouper_mermaid(source):
    """Restitue un source Mermaid écrit sur une seule ligne (texte alternatif Word).

    Word stocke le diagramme sans saut de ligne ; Mermaid, lui, exige une
    instruction par ligne. On re-segmente en respectant guillemets et crochets.
    """
    jetons, courant, profondeur, dans_guillemets = [], [], 0, False
    for caractere in source:
        if caractere == '"':
            dans_guillemets = not dans_guillemets
        elif not dans_guillemets:
            if caractere in "[{(":
                profondeur += 1
            elif caractere in "]})":
                profondeur -= 1
            elif caractere.isspace() and profondeur == 0:
                if courant:
                    jetons.append("".join(courant))
                    courant = []
                continue
        courant.append(caractere)
    if courant:
        jetons.append("".join(courant))

    if not jetons:
        return ""

    entete, jetons = jetons[0], jetons[1:]
    if entete in MOTS_CLES_MERMAID and jetons and re.fullmatch(r"[A-Z]{2}", jetons[0]):
        entete, jetons = f"{entete} {jetons[0]}", jetons[1:]

    if entete.startswith("classDiagram"):
        return decouper_class_diagram(entete, jetons)

    arite_fixe = {"classDef": 3, "class": 3, "style": 3, "linkStyle": 3, "direction": 2}
    instructions, i = [], 0
    while i < len(jetons):
        jeton = jetons[i]
        if jeton in arite_fixe:
            n = arite_fixe[jeton]
            instructions.append(" ".join(jetons[i:i + n]))
            i += n
            continue
        if jeton in ("subgraph", "end"):
            instructions.append(jeton if jeton == "end" else " ".join(jetons[i:i + 2]))
            i += 1 if jeton == "end" else 2
            continue
        instruction = [jeton]
        i += 1
        while i < len(jetons) and RE_FLECHE.search(jetons[i]):
            instruction.append(jetons[i])
            i += 1
            if i < len(jetons):
                instruction.append(jetons[i])
                i += 1
        # Libellé de transition à la manière des stateDiagram (« A --> B : texte ») :
        # il court jusqu'au prochain jeton suivi d'une flèche, qui ouvre l'instruction suivante.
        if i < len(jetons) and jetons[i].startswith(":"):
            while i < len(jetons):
                suivant_est_fleche = i + 1 < len(jetons) and RE_FLECHE.search(jetons[i + 1])
                if jetons[i] in arite_fixe or (suivant_est_fleche and instruction[-1] != ":"):
                    break
                instruction.append(jetons[i])
                i += 1
        instructions.append(" ".join(instruction))

    return "\n".join([entete] + [f"    {i}" for i in instructions]) + "\n"


RE_FLECHE_CLASSE = re.compile(
    r"^(<\|--|--\|>|\*--|--\*|o--|--o|<--|-->|--|<\|\.\.|\.\.\|>|<\.\.|\.\.>|\.\.)$"
)


def decouper_class_diagram(entete, jetons):
    """Re-segmente un classDiagram écrit sur une seule ligne.

    Une relation s'écrit « A "1" --> "*" B : libellé », avec des cardinalités
    facultatives entre guillemets. Son libellé court jusqu'au début de
    l'instruction suivante : un identifiant suivi d'une flèche, éventuellement
    précédée d'une cardinalité, ou un mot-clé.
    """
    arite = {"class": 2, "direction": 2, "style": 3, "classDef": 3, "cssClass": 3}
    fleche = lambda j: j < len(jetons) and RE_FLECHE_CLASSE.match(jetons[j]) is not None
    guillemets = lambda j: j < len(jetons) and jetons[j].startswith('"')

    def debut_relation(j):
        return (not guillemets(j) and not fleche(j) and jetons[j] != ":"
                and (fleche(j + 1) or (guillemets(j + 1) and fleche(j + 2))))

    instructions, i = [], 0
    while i < len(jetons):
        if jetons[i] in arite:
            n = arite[jetons[i]]
            instructions.append(" ".join(jetons[i:i + n]))
            i += n
            continue
        instruction = [jetons[i]]
        i += 1
        # Cardinalité, flèche, cardinalité, cible.
        while i < len(jetons) and (guillemets(i) or fleche(i)) and len(instruction) < 4:
            instruction.append(jetons[i])
            i += 1
        if len(instruction) > 1 and i < len(jetons):
            instruction.append(jetons[i])
            i += 1
        if i < len(jetons) and jetons[i].startswith(":"):
            while i < len(jetons) and jetons[i] not in arite and not (
                    instruction[-1] != ":" and debut_relation(i)):
                instruction.append(jetons[i])
                i += 1
        instructions.append(" ".join(instruction))

    return "\n".join([entete] + [f"    {x}" for x in instructions]) + "\n"


def mermaid_depuis_alt(alt):
    """Renvoie le source Mermaid si le texte alternatif en est un, sinon None."""
    texte = html.unescape(alt or "").strip()
    if not texte:
        return None
    premier = texte.split(None, 1)[0]
    if premier not in MOTS_CLES_MERMAID:
        return None
    return decouper_mermaid(texte)


def charger_config_figures(chemin):
    if not chemin.exists():
        return []
    return tomllib.loads(chemin.read_text(encoding="utf-8")).get("figure", [])


def convertir_figures(lignes, drawio, config, dossier_images, journal):
    """Remplace chaque <img> par un bloc Mermaid, ou conserve l'image à défaut."""
    pages = drawio2mermaid.charger_pages(drawio) if drawio.exists() else {}
    sorties, i = [], 0
    while i < len(lignes):
        ligne = lignes[i].strip()
        correspondance = RE_IMG.match(ligne)
        if not correspondance:
            sorties.append(lignes[i])
            i += 1
            continue

        attributs = dict(RE_ATTR.findall(correspondance.group("attrs")))
        legende, saut = lire_legende(lignes, i + 1)

        if legende and not re.search(r"\d", legende.split("—")[0]):
            journal.avertir(
                f"« {legende} » : légende sans numéro dans Word — un constat de revue "
                "ne pourra désigner cette figure que par son titre"
            )
        mermaid = mermaid_depuis_alt(attributs.get("alt"))
        origine = "texte alternatif Word"
        if mermaid is None:
            entree = trouver_config(config, legende)
            if entree and entree.get("source"):
                # Source Mermaid tenue dans le dépôt : aucune re-segmentation, donc
                # tous les types de diagrammes sont permis, séquences comprises.
                chemin = RACINE / entree["source"]
                if chemin.exists():
                    mermaid = chemin.read_text(encoding="utf-8")
                    origine = entree["source"]
                else:
                    journal.avertir(
                        f"{legende} : source Mermaid « {entree['source']} » introuvable"
                    )
            elif entree and entree.get("page") in pages:
                mermaid = drawio2mermaid.convertir(
                    pages[entree["page"]],
                    entree.get("direction", "LR"),
                    lambda m, niveau="attention", lg=legende: journal.avertir(
                        f"{lg} : {m}", niveau
                    ),
                )
                origine = f"{drawio.name}, page « {entree['page']} »"
            elif entree:
                journal.avertir(
                    f"{legende} : page draw.io « {entree.get('page')} » introuvable"
                )

        if mermaid is None:
            if not legende:
                journal.avertir(
                    "figure sans légende exploitable : l'association avec une page "
                    "draw.io se fait par la légende, elle ne peut donc pas être faite. "
                    "L'image est conservée telle quelle."
                )
            else:
                journal.avertir(
                    f"{legende} : aucune source Mermaid (ni texte alternatif, ni entrée "
                    f"correspondante dans tools/figures.toml) — l'image est conservée "
                    f"telle quelle"
                )
            sorties.extend(conserver_image(attributs, legende, dossier_images))
        else:
            sorties.append(f"<!-- source : {origine} — régénéré par tools/build.py -->")
            sorties.append("")
            sorties.append("```mermaid")
            sorties.append(mermaid.rstrip("\n"))
            sorties.append("```")

        if legende:
            sorties.append("")
            sorties.append(f"*{legende}*")
        i = saut
    return sorties


def lire_legende(lignes, depart):
    """Légende « Figure n … » / « Tableau n … » qui suit l'image ; renvoie (légende, index suivant)."""
    i = depart
    while i < len(lignes) and not lignes[i].strip():
        i += 1
    if i < len(lignes):
        candidat = RE_ANCRE.sub("", lignes[i]).strip()
        correspondance = RE_LEGENDE.match(candidat)
        if correspondance:
            genre, numero, titre = correspondance.groups()
            tete = f"{genre} {numero}" if numero else genre
            return (f"{tete} — {titre.strip()}" if titre.strip() else tete), i + 1
    return "", depart


def trouver_config(config, legende):
    """Entrée dont le fragment de légende correspond ; le plus long l'emporte.

    Plusieurs légendes peuvent partager un préfixe (« Arborescence fonctionnelle »
    et « Arborescence fonctionnelle de la planification ») : l'ordre des entrées
    dans figures.toml ne doit pas décider à la place du sens.
    """
    if not legende:
        return None
    candidates = [e for e in config if normaliser(e.get("legende", "")) in normaliser(legende)]
    return max(candidates, key=lambda e: len(e.get("legende", "")), default=None)


def conserver_image(attributs, legende, dossier_images):
    source = pathlib.Path(attributs.get("src", ""))
    if not source.exists():
        return [f"<!-- image manquante : {source} -->"]
    dossier_images.mkdir(parents=True, exist_ok=True)
    destination = dossier_images / source.name
    shutil.copy2(source, destination)
    chemin = destination.relative_to(RACINE).as_posix()
    return [f"![{legende or source.name}]({chemin})"]


# --------------------------------------------------------------------------- #
# Étape 4 : tableaux d'exigences -> blocs YAML ancrés
# --------------------------------------------------------------------------- #

def cellules(ligne):
    return [c.strip() for c in ligne.strip().strip("|").split("|")]


def desechapper(valeur):
    valeur = valeur.strip()
    # Une cellule entièrement en gras dans Word arrive en **…** : la mise en forme
    # n'a pas de sens dans une valeur d'exigence.
    entiere = re.fullmatch(r"\*\*(.+)\*\*", valeur)
    if entiere:
        valeur = entiere.group(1).strip()
    valeur = re.sub(r"\\(.)", r"\1", valeur)
    return "" if valeur in ("", "-") else valeur


def scalaire_yaml(valeur):
    if not valeur:
        return '""'
    return '"' + valeur.replace("\\", "\\\\").replace('"', '\\"') + '"'


def tableaux_html_en_pipe(lignes):
    """Réécrit en tableau Markdown les tableaux HTML qui portent une exigence.

    Pandoc produit un tableau HTML dès qu'une cellule contient plusieurs
    paragraphes (un Motif en deux paragraphes, par exemple). Sans cette étape,
    l'exigence échapperait à la conversion, à l'index et au contrôle des doublons.
    """
    texte = "\n".join(lignes)

    def reecrire(correspondance):
        bloc = correspondance.group(0)
        paires = []
        for rangee in re.findall(r"<tr[^>]*>(.*?)</tr>", bloc, re.S):
            cellules_html = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rangee, re.S)
            if len(cellules_html) != 2:
                return bloc
            valeurs = []
            for cellule in cellules_html:
                cellule = re.sub(r"</p>\s*<p>", " ", cellule)
                cellule = re.sub(r"<[^>]+>", "", cellule)
                valeurs.append(re.sub(r"\s+", " ", html.unescape(cellule)).strip())
            paires.append(valeurs)
        if [cle for cle, _ in paires] != list(CHAMPS_EXIGENCE):
            return bloc
        pipe = [f"| {paires[0][0]} | {paires[0][1]} |", "|---|---|"]
        pipe += [f"| {cle} | {valeur.replace('|', '/')} |" for cle, valeur in paires[1:]]
        return "\n".join(pipe)

    texte = re.sub(r"<table>.*?</table>", reecrire, texte, flags=re.S)
    return texte.split("\n")


def convertir_exigences(lignes, journal):
    """Transforme les tableaux d'exigences en blocs YAML portant leur section."""
    sorties, exigences, i = [], [], 0
    while i < len(lignes):
        if not lignes[i].strip().startswith("| ID "):
            sorties.append(lignes[i])
            i += 1
            continue

        fin = i
        while fin < len(lignes) and lignes[fin].strip().startswith("|"):
            fin += 1
        corps = [l for l in lignes[i:fin] if not re.match(r"^\|[\s|:-]+\|$", l.strip())]
        paires = [cellules(l) for l in corps]
        if any(len(p) != 2 for p in paires) or [p[0] for p in paires] != list(CHAMPS_EXIGENCE):
            sorties.extend(lignes[i:fin])
            i = fin
            continue

        valeurs = {CHAMPS_EXIGENCE[cle]: desechapper(val) for cle, val in paires}
        valeurs["section"] = section_courante(sorties, len(sorties))
        # L'exemple du chapitre 1 (« Forme des exigences ») est rendu comme les
        # autres, mais n'entre ni dans le compte ni dans l'index.
        if not (valeurs["section"] or "").startswith("1."):
            exigences.append(valeurs)

        sorties.append("```yaml exigence")
        sorties.append(f"section: {scalaire_yaml(valeurs['section'])}")
        for champ in CHAMPS_EXIGENCE.values():
            sorties.append(f"{champ}: {scalaire_yaml(valeurs[champ])}")
        sorties.append("```")
        i = fin

    doublons = {}
    for exigence in exigences:
        doublons.setdefault(exigence["id"], []).append(exigence["section"])
    for identifiant, sections in doublons.items():
        if len(sections) > 1:
            journal.avertir(
                f"identifiant {identifiant} porté par {len(sections)} exigences "
                f"(sections {', '.join(s or '?' for s in sections)})"
            )
    return sorties, exigences


def remplacer_index(lignes, exigences):
    """Réécrit « Index des exigences » : les numéros de page Word n'ont pas de sens ici."""
    depart = None
    for i, ligne in enumerate(lignes):
        if re.match(r"^#{1,6}\s+(?:\d+(?:\.\d+)*\.\s+)?Index des exigences\s*$", ligne):
            depart = i
            break
    if depart is None:
        return lignes

    fin = depart + 1
    while fin < len(lignes) and not lignes[fin].startswith("#"):
        fin += 1

    table = ["", "| Exigence | Section | Titre | Flex |", "|---|---|---|---|"]
    for exigence in sorted(exigences, key=lambda e: (e["id"], e["section"])):
        table.append(
            f"| {exigence['id'] or '—'} | {exigence['section'] or '—'} "
            f"| {exigence['titre'] or '—'} | {exigence['flexibilite'] or '—'} |"
        )
    table.append("")
    return lignes[:depart + 1] + table + lignes[fin:]


# --------------------------------------------------------------------------- #
# Étape 5 : assemblage
# --------------------------------------------------------------------------- #

def nettoyer(lignes):
    sorties, vides = [], 0
    for ligne in lignes:
        ligne = RE_ANCRE.sub("", ligne).rstrip()
        if not ligne.strip():
            vides += 1
            if vides > 1:
                continue
        else:
            vides = 0
        sorties.append(ligne)
    while sorties and not sorties[0].strip():
        sorties.pop(0)
    return sorties


def entete(docx, drawio, nb_exigences):
    return [
        "---",
        f"genere_le: {date.today().isoformat()}",
        "genere_par: tools/build.py",
        f"source_texte: {docx.name}",
        f"source_diagrammes: {drawio.name}",
        f"nombre_exigences: {nb_exigences}",
        "---",
        "",
        "<!-- FICHIER GÉNÉRÉ — NE PAS ÉDITER.",
        f"     Les sources sont {docx.name} (Word) et {drawio.name} (draw.io).",
        "     Toute correction se fait dans ces fichiers, puis ./build.sh. -->",
        "",
    ]


def valider_mermaid(lignes, journal):
    """Compile chaque bloc Mermaid produit, pour que le build échoue avant l'agent."""
    if shutil.which("mmdc") is None:
        journal.avertir("mmdc absent : les diagrammes Mermaid ne sont pas validés", "info")
        return
    blocs, courant = [], None
    for ligne in lignes:
        if courant is None and ligne.strip() == "```mermaid":
            courant = []
        elif courant is not None and ligne.strip() == "```":
            blocs.append("\n".join(courant))
            courant = None
        elif courant is not None:
            courant.append(ligne)

    with tempfile.TemporaryDirectory() as temporaire:
        dossier = pathlib.Path(temporaire)
        for n, bloc in enumerate(blocs, 1):
            entree = dossier / f"d{n}.mmd"
            entree.write_text(bloc + "\n", encoding="utf-8")
            resultat = subprocess.run(
                ["mmdc", "-i", str(entree), "-o", str(dossier / f"d{n}.svg")],
                capture_output=True, text=True,
            )
            if resultat.returncode != 0:
                premiere = (resultat.stderr or resultat.stdout).strip().split("\n")
                journal.avertir(
                    f"diagramme Mermaid n°{n} ne compile pas : "
                    + " ".join(premiere[:3])
                )
    journal.avertir(f"{len(blocs)} diagramme(s) Mermaid validé(s) par mmdc", "info")


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--docx", default="stb-waterfall.docx")
    analyseur.add_argument("--drawio", default="waterfall.visuels.drawio")
    analyseur.add_argument("--sortie", default="waterfall-spec.md")
    analyseur.add_argument("--config", default="tools/figures.toml")
    analyseur.add_argument("--strict", action="store_true",
                           help="échoue si un avertissement est émis")
    analyseur.add_argument("--verbeux", action="store_true",
                           help="affiche aussi les messages de traçabilité")
    arguments = analyseur.parse_args()

    docx = RACINE / arguments.docx
    drawio = RACINE / arguments.drawio
    sortie = RACINE / arguments.sortie
    if not docx.exists():
        print(f"source Word introuvable : {docx}", file=sys.stderr)
        return 1

    journal = Journal(arguments.verbeux)
    config = charger_config_figures(RACINE / arguments.config)

    with tempfile.TemporaryDirectory() as temporaire:
        brut = extraire_docx(docx, pathlib.Path(temporaire) / "media")
        lignes = brut.replace("\r\n", "\n").split("\n")

        numeros_word, sans_numero = lire_sommaire(lignes)
        lignes = retirer_sommaire(lignes)
        lignes = [RE_ANCRE.sub("", l) for l in lignes]
        lignes = numeroter_titres(lignes, numeros_word, sans_numero, journal)
        lignes = convertir_figures(lignes, drawio, config, RACINE / "images", journal)

    lignes = tableaux_html_en_pipe(lignes)
    lignes, exigences = convertir_exigences(lignes, journal)
    lignes = remplacer_index(lignes, exigences)
    lignes = nettoyer(lignes)
    valider_mermaid(lignes, journal)

    sortie.write_text(
        "\n".join(entete(docx, drawio, len(exigences)) + lignes) + "\n",
        encoding="utf-8",
    )
    print(f"{sortie.relative_to(RACINE)} — {len(lignes)} lignes, {len(exigences)} exigences")
    journal.afficher()
    if journal.avertissements and arguments.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
