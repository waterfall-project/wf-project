#!/usr/bin/env python3
"""Convertit une page d'un fichier .drawio en diagramme Mermaid.

Les arêtes dessinées « à la main » dans draw.io n'ont pas toujours d'attribut
source/target : elles ne portent que des coordonnées. On rattache alors chaque
extrémité au sommet le plus proche géométriquement, et on signale la distance
retenue pour que le rattachement reste vérifiable.
"""

import base64
import unicodedata
import html
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from collections import defaultdict

# Au-delà de ce nombre de pixels, on refuse d'inférer l'extrémité d'une arête.
SEUIL_INFERENCE_PX = 20.0


def charger_pages(chemin):
    """Retourne {nom_de_page: element mxGraphModel}, en gérant les pages compressées."""
    racine = ET.parse(chemin).getroot()
    pages = {}
    for i, diagramme in enumerate(racine.iter("diagram")):
        nom = diagramme.get("name") or f"Page-{i + 1}"
        modele = diagramme.find("mxGraphModel")
        if modele is None and (diagramme.text or "").strip():
            # Page compressée : base64 -> deflate brut -> URL-encoding.
            brut = zlib.decompress(base64.b64decode(diagramme.text.strip()), -15)
            modele = ET.fromstring(urllib.parse.unquote(brut.decode("utf-8")))
        if modele is None:
            continue
        pages[nom] = modele
    return pages


def texte(cellule):
    """Libellé d'une cellule, balises HTML de draw.io converties en sauts Mermaid."""
    valeur = cellule.get("value") or ""
    # <div> ouvrant compris : draw.io s'en sert aussi comme séparateur de ligne.
    valeur = re.sub(r"<br\s*/?>|</?(?:div|p|li)[^>]*>", "\n", valeur, flags=re.I)
    valeur = re.sub(r"<[^>]+>", "", valeur)
    valeur = html.unescape(valeur).replace("\xa0", " ")
    lignes = [re.sub(r"\s+", " ", l).strip() for l in valeur.split("\n")]
    return "<br>".join(l for l in lignes if l)


def style_en_dict(cellule):
    style = {}
    for morceau in (cellule.get("style") or "").split(";"):
        if "=" in morceau:
            cle, _, val = morceau.partition("=")
            style[cle.strip()] = val.strip()
        elif morceau.strip():
            style[morceau.strip()] = True
    return style


def forme_mermaid(style, libelle):
    """Choisit la forme Mermaid d'après le style draw.io."""
    libelle = libelle or " "
    if "rhombus" in style:
        return '{"%s"}' % libelle
    if "ellipse" in style:
        return '(("%s"))' % libelle
    if "cylinder" in style or "mxgraph.flowchart.database" in str(style.get("shape", "")):
        return '[("%s")]' % libelle
    if str(style.get("rounded")) == "1":
        return '("%s")' % libelle
    return '["%s"]' % libelle


def identifiant(libelle, pris):
    """Identifiant Mermaid lisible dérivé du libellé, unique dans le diagramme."""
    sans_accents = unicodedata.normalize("NFKD", libelle.replace("<br>", " "))
    sans_accents = "".join(c for c in sans_accents if not unicodedata.combining(c))
    base = re.sub(r"[^0-9A-Za-z]+", "_", sans_accents)
    base = base.strip("_") or "N"
    if base[0].isdigit():
        base = "N" + base
    candidat, n = base, 2
    while candidat in pris:
        candidat, n = f"{base}_{n}", n + 1
    pris.add(candidat)
    return candidat


def geometrie(cellule):
    g = cellule.find("mxGeometry")
    if g is None:
        return None
    return (
        float(g.get("x", 0)), float(g.get("y", 0)),
        float(g.get("width", 0)), float(g.get("height", 0)),
    )


def distance_au_rectangle(px, py, rect):
    x, y, w, h = rect
    dx = max(x - px, 0.0, px - (x + w))
    dy = max(y - py, 0.0, py - (y + h))
    return (dx * dx + dy * dy) ** 0.5


def convertir(modele, direction="LR", avertir=lambda m, niveau="attention": None):
    cellules = {c.get("id"): c for c in modele.iter("mxCell")}

    sommets, libelles_aretes, conteneurs = {}, defaultdict(list), set()
    for ident, cellule in cellules.items():
        style = style_en_dict(cellule)
        if cellule.get("vertex") != "1":
            continue
        if "edgeLabel" in style:
            libelles_aretes[cellule.get("parent")].append(texte(cellule))
            continue
        rect = geometrie(cellule)
        if rect is None:
            continue
        sommets[ident] = (texte(cellule), rect, style)
        if cellule.get("parent") not in ("1", "0", None):
            conteneurs.add(ident)

    if conteneurs:
        avertir(
            f"{len(conteneurs)} sommet(s) imbriqué(s) dans un conteneur draw.io : "
            "les coordonnées sont relatives au parent, le rattachement géométrique "
            "peut être faux. Vérifier le diagramme produit."
        )

    for parent, libelles in libelles_aretes.items():
        if cellules.get(parent) is None or cellules[parent].get("edge") != "1":
            avertir(
                "libellé d'arête orphelin, non rattaché à une arête : "
                + ", ".join(f"« {l} »" for l in libelles if l)
            )

    def plus_proche(px, py):
        ident = min(sommets, key=lambda i: (
            round(distance_au_rectangle(px, py, sommets[i][1]), 1),
            sommets[i][1][2] * sommets[i][1][3],
        ))
        return ident, distance_au_rectangle(px, py, sommets[ident][1])

    aretes, inferences = [], []
    for ident, cellule in cellules.items():
        if cellule.get("edge") != "1":
            continue
        g = cellule.find("mxGeometry")
        points = {}
        if g is not None:
            for p in g.findall("mxPoint"):
                points[p.get("as")] = (float(p.get("x", 0)), float(p.get("y", 0)))

        extremites = {}
        for bout, attribut, point in (("source", "source", "sourcePoint"),
                                      ("cible", "target", "targetPoint")):
            ref = cellule.get(attribut)
            if ref in sommets:
                extremites[bout] = ref
                continue
            if point in points:
                candidat, dist = plus_proche(*points[point])
                if dist <= SEUIL_INFERENCE_PX:
                    extremites[bout] = candidat
                    inferences.append((ident, bout, sommets[candidat][0], dist))

        libelle = "<br>".join(l for l in libelles_aretes.get(ident, []) if l)
        if "source" in extremites and "cible" in extremites:
            pointille = str(style_en_dict(cellule).get("dashed")) == "1"
            aretes.append((extremites["source"], extremites["cible"], libelle, pointille))
        else:
            avertir(
                f"arête {ident} ignorée (extrémité non résolue)"
                + (f' — libellé « {libelle} »' if libelle else "")
            )

    for ident, bout, nom, dist in inferences:
        avertir(
            f"arête {ident} : {bout} inférée vers « {nom} » (distance {dist:.0f} px)",
            "info",
        )
    if inferences:
        pire = max(d for *_, d in inferences)
        avertir(
            f"{len(inferences)} extrémité(s) d'arête rattachée(s) par géométrie "
            f"(écart maximal {pire:.0f} px sur {SEUIL_INFERENCE_PX:.0f} tolérés)",
            "info",
        )

    pris = set()
    noms = {i: identifiant(sommets[i][0] or "N", pris) for i in sommets}

    # Cadres : un sommet libellé dont le rectangle contient celui d'autres sommets.
    # Chaque sommet est rangé dans le plus petit cadre qui le contient.
    def contient(a, b):
        ax, ay, aw, ah = sommets[a][1]
        bx, by, bw, bh = sommets[b][1]
        return (a != b and ax <= bx and ay <= by and bx + bw <= ax + aw
                and by + bh <= ay + ah and aw * ah > bw * bh)

    parent = {}
    for b in sommets:
        englobants = [a for a in sommets if sommets[a][0] and contient(a, b)]
        if englobants:
            parent[b] = min(englobants, key=lambda a: sommets[a][1][2] * sommets[a][1][3])
    cadres = set(parent.values())

    lignes = [f"flowchart {direction}"]

    def emettre(conteneur, retrait):
        for ident, (libelle, _, style) in sommets.items():
            if parent.get(ident) != conteneur:
                continue
            if ident in cadres:
                lignes.append(f'{retrait}subgraph {noms[ident]}["{libelle}"]')
                emettre(ident, retrait + "    ")
                lignes.append(f"{retrait}end")
            else:
                lignes.append(f"{retrait}{noms[ident]}{forme_mermaid(style, libelle)}")

    emettre(None, "    ")

    lignes.append("")
    for source, cible, libelle, pointille in aretes:
        trait = "-.->" if pointille else "-->"
        fleche = f'{trait}|"{libelle}"|' if libelle else trait
        lignes.append(f"    {noms[source]} {fleche} {noms[cible]}")

    # Les couleurs de remplissage deviennent des classes, pour rester proche du visuel d'origine.
    par_couleur = defaultdict(list)
    for ident, (_, _, style) in sommets.items():
        if ident in cadres:
            continue
        remplissage = style.get("fillColor")
        if remplissage and remplissage != "none":
            par_couleur[(remplissage, style.get("strokeColor", "#000000"))].append(noms[ident])
    if par_couleur:
        lignes.append("")
        for n, ((remplissage, trait), membres) in enumerate(sorted(par_couleur.items()), 1):
            lignes.append(f"    classDef c{n} fill:{remplissage},stroke:{trait}")
            lignes.append(f"    class {','.join(sorted(membres))} c{n}")

    return "\n".join(lignes) + "\n"


def main(argv):
    if not 2 <= len(argv) <= 4:
        print("usage: drawio2mermaid.py <fichier.drawio> [page] [direction]", file=sys.stderr)
        return 2
    pages = charger_pages(argv[1])
    if len(argv) < 3:
        for nom in pages:
            print(nom)
        return 0
    if argv[2] not in pages:
        print(f"page « {argv[2]} » absente ; pages disponibles : {', '.join(pages)}", file=sys.stderr)
        return 1
    messages = []
    sortie = convertir(
        pages[argv[2]],
        argv[3] if len(argv) > 3 else "LR",
        lambda m, niveau="attention": messages.append((niveau, m)),
    )
    for niveau, message in messages:
        print(f"  {'!' if niveau == 'attention' else '-'} {message}", file=sys.stderr)
    print(sortie, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
