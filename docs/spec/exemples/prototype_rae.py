# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Prototype du format « Reste à engager » de l'annexe B, produit comme Waterfall le produirait.

Les données sont inventées, celles du prototype du devis une fois le projet En cours. Une synthèse,
qui ventile le reste de chaque sous-projet, puis un onglet par sous-projet, nommé par son code, et
« Hors sous-projet ». Comme au devis, une ligne du fichier est une ligne de Waterfall, désignée par
sa tâche et son rôle ou sa catégorie ; le reste s'y saisit en jours pour la main-d'œuvre, en
montant pour un débours. Il n'est pas le code de Waterfall.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

ENTREPRISE = "Exemple Industrie"
PROJET = {"code": "A.ABC.26001", "libellé": "Contrôle d’accès du site de Lyon", "client": "Client Exemple"}
REVISION = "Revue de février (en cours)"
REVUE = "2027-02-15"
DEVISE = "EUR"
SYMBOLES = {"EUR": "€", "USD": "$", "GBP": "£"}
MONTANT = f'#,##0.00 "{SYMBOLES.get(DEVISE, DEVISE)}"'
HEURES_PAR_JOUR = 8  # constante de l'installation (WF-PLA-0160)
LOGO = Path(__file__).resolve().parents[2] / "assets" / "waterfall_logo.png"
MENTION = (f"© {REVUE[:4]} {ENTREPRISE} — Généré par Waterfall le {REVUE} — "
           "logiciel libre sous licence AGPL-3.0 — www.waterfall-project.pro")

NATURES = [("Main-d’œuvre", "Main-d’œuvre"), ("Fournitures", "Hors main-d’œuvre"),
           ("Sous-traitance", "Hors main-d’œuvre"), ("Provisions pour risques", "Provision")]
# Catégories : code comptable, libellé, nature, taux horaire de l'année de référence (main-d'œuvre).
CATEGORIES = [
    ("I810", "Gestion d’affaires", "Main-d’œuvre", 100),
    ("I329", "Ingénierie logicielle", "Main-d’œuvre", 80),
    ("I1M2", "Ingénierie électronique", "Main-d’œuvre", 60),
    ("fo-AINT", "Anti-intrusion", "Fournitures", None),
    ("fo-APPA", "Appareillage", "Fournitures", None),
    ("st-POSE", "Pose sur site", "Sous-traitance", None),
]
# Rôles : code, libellé, service, catégorie — la même liste que celle du devis.
ROLES = [
    ("RA-A1", "Responsable d’affaire A1", "Affaires › Activité 1", "I810"),
    ("IQ-A1", "Ingénieur qualité A1", "Affaires › Activité 1", "I1M2"),
    ("ARCH-LOG", "Architecte logiciel", "Ingénierie › Logiciel", "I329"),
    ("DEV", "Développeur", "Ingénierie › Logiciel", "I1M2"),
    ("ARCH-ELEC", "Architecte électronique", "Ingénierie › Électronique", "I329"),
    ("ING-CARTE", "Ingénieur carte", "Ingénierie › Électronique", "I1M2"),
]
# La description de chaque tâche, que le planning et MS Project portent (WF-PLA-0130, C-375).
DESCRIPTIONS = {
    "1.1.1": "Pilotage, réunions d’avancement et compte rendu au client",
    "1.1.2": "Logiciel de la centrale : gestion des badges et des droits d’accès",
    "1.2.1": "Achat et réception des lecteurs de badges",
    "1.2.2": "Tirage des câbles et raccordement des lecteurs",
    "2.1.1": "Essais d’intégration et recette sur site",
    "3": "Gestion de projet transverse",
}


def role(code: str) -> str:
    r = next(r for r in ROLES if r[0] == code)
    return f"{r[1]} ({r[0]})"


def cat(code: str) -> str:
    c = next(c for c in CATEGORIES if c[0] == code)
    return f"{c[1]} ({c[0]})"


@dataclass
class Tache:
    entree: str
    lineage: str
    etat: str  # « démarrée » ou « non démarrée » ; une tâche terminée n'est pas dans le fichier
    coefficient: float  # inflation de l'année de consommation, calculée par Waterfall


@dataclass
class Ligne:
    tache: str
    entree: str  # rôle ou catégorie, tel que la liste l'écrit
    designation: str
    budget: float
    precedent: float
    reste: float  # en jours pour la main-d'œuvre, en montant pour un débours
    lineage: str


@dataclass
class SousProjet:
    code: str
    libelle: str
    budget: float  # montant budgété de toutes ses lignes, tâches terminées comprises
    couts_reels: float
    provisions: float  # reste à engager des lignes de provision des risques identifiés
    taches: list[Tache]
    lignes: list[Ligne]


SOUS_PROJETS = [
    SousProjet("SP-PRE", "Prestations", 68567.6, 21500.0, 0.0,
               [Tache("1.1.1 Management", "t-0011", "démarrée", 1.0),
                Tache("1.1.2 Développement du logiciel", "t-0012", "démarrée", 1.0),
                Tache("1.2.2 Câblage", "t-0022", "non démarrée", 1.02),
                Tache("2.1.1 Essais", "t-0031", "non démarrée", 1.02)],
               [Ligne("1.1.1 Management", role("RA-A1"), "", 3700.0, 1480.0, 3, "l-0101"),
                Ligne("1.1.2 Développement du logiciel", role("ARCH-LOG"), "", 11840.0, 6000.0, 8, "l-0102"),
                Ligne("1.1.2 Développement du logiciel", role("DEV"), "", 26640.0, 18300.0, 35, "l-0103"),
                Ligne("1.1.2 Développement du logiciel", cat("st-POSE"), "Commande 4500000102 — recette externe",
                      2000.0, 2000.0, 1500, "l-0106"),
                # Une tâche non démarrée porte le reste que Waterfall calcule depuis la référence.
                Ligne("1.2.2 Câblage", cat("st-POSE"), "", 8670.0, 8670.0, 8670, "l-0203"),
                Ligne("2.1.1 Essais", role("IQ-A1"), "", 4528.8, 4528.8, 9.25, "l-0401"),
                Ligne("2.1.1 Essais", role("ING-CARTE"), "", 4528.8, 4528.8, 9.25, "l-0402")]),
    SousProjet("SP-MAT", "Matériel", 7444.0, 3800.0, 0.0,
               [Tache("1.2.1 Approvisionnement des lecteurs", "t-0021", "démarrée", 1.02)],
               [Ligne("1.2.1 Approvisionnement des lecteurs", cat("fo-APPA"), "Commande 4500000101 — lecteurs, lot 1",
                      3672.0, 3600.0, 2400, "l-0201"),
                Ligne("1.2.1 Approvisionnement des lecteurs", cat("fo-APPA"), "Commande 4500000103 — lecteurs, lot 2",
                      3672.0, 1600.0, 1200, "l-0204")]),
    SousProjet("Hors sous-projet", "", 16724.0, 4200.0, 1500.0,
               [Tache("3 Gestion de projet", "t-0005", "démarrée", 1.01)],
               [Ligne("3 Gestion de projet", role("RA-A1"), "", 14948.0, 11200.0, 12, "l-0501")]),
]
PREVUES = 10  # lignes vides, pour une ligne non anticipée (WF-RAE-0050)
CATS_MO = [c for c in CATEGORIES if c[2] == "Main-d’œuvre"]


class Formats:
    """Les formats de cellule du classeur."""

    def __init__(self, wb: xlsxwriter.Workbook) -> None:
        self.gras = wb.add_format({"bold": True})
        self.titre = wb.add_format({"bold": True, "font_size": 14})
        self.gauche = wb.add_format({"align": "left"})
        self.euros = wb.add_format({"num_format": MONTANT})
        self.euros_gras = wb.add_format({"num_format": MONTANT, "bold": True})
        self.jours = wb.add_format({"num_format": "#,##0.0"})
        self.jours_gras = wb.add_format({"num_format": "#,##0.0", "bold": True})
        self.pourcent = wb.add_format({"num_format": "0.0 %", "align": "right"})
        self.pourcent_gras = wb.add_format({"num_format": "0.0 %", "align": "right", "bold": True})
        self.note = wb.add_format({"italic": True, "font_color": "#666666"})
        self.petit = wb.add_format({"font_size": 8, "font_color": "#666666"})
        self.bloc = wb.add_format({"bold": True, "align": "center", "bg_color": "#DDEBF7", "border": 1})
        self.calcule_euros = wb.add_format({"bg_color": "#EEEEEE", "font_color": "#555555", "num_format": MONTANT})
        self.calcule = wb.add_format({"bg_color": "#EEEEEE", "font_color": "#555555"})
        self.texte = wb.add_format({"num_format": "@"})
        self.entete = wb.add_format({"bold": True, "text_wrap": True, "valign": "top", "bottom": 1})


def parametres(wb, ws, f: Formats) -> str:
    """Le référentiel de la révision, comme au devis, et les heures par jour ; rend la liste."""
    ws.write("A1", "Référentiel de la révision : écrit par l’export, ignoré à l’import.", f.gras)
    ws.write("A2", "Heures par jour")
    ws.write_number("B2", HEURES_PAR_JOUR)
    wb.define_name("HeuresParJour", "='Paramètres'!$B$2")
    nature_type = dict(NATURES)
    par_code = {c[0]: c for c in CATEGORIES}
    rows = []
    for code, libelle, service, categorie in ROLES:
        c = par_code[categorie]
        rows.append([f"{libelle} ({code})", "Rôle", code, libelle, service, c[2], nature_type[c[2]], c[0], c[3]])
    for code, libelle, nature, _ in CATEGORIES:
        if nature_type[nature] != "Main-d’œuvre":
            rows.append([f"{libelle} ({code})", "Catégorie", code, libelle, "", nature, nature_type[nature], code, None])
    ws.add_table(3, 0, 3 + len(rows), 8, {
        "name": "Referentiel", "data": rows, "style": "Table Style Light 1",
        "columns": [{"header": h} for h in ["Entrée", "Genre", "Code", "Libellé", "Service", "Nature",
                                            "Type de nature", "Code comptable", "Taux horaire"]],
    })
    for i, w in enumerate([34, 10, 10, 26, 24, 22, 18, 14, 11]):
        ws.set_column(i, i, w)
    ws.protect("", {"autofilter": True, "sort": True})
    return f"='Paramètres'!$A$5:$A${4 + len(rows)}"


def taches(ws, f: Formats) -> dict[str, str]:
    """Les tâches non terminées par sous-projet ; rend la plage de la liste de chaque onglet."""
    ws.write("A1", "Tâches non terminées par sous-projet : la liste de chaque onglet.", f.gras)
    rows, plages = [], {}
    r0 = 3
    for sp in SOUS_PROJETS:
        premier = r0 + len(rows)
        for t in sp.taches:
            rows.append([t.entree, t.lineage, sp.code, t.etat, t.coefficient,
                         DESCRIPTIONS.get(t.entree.split(" ")[0], "")])
        plages[sp.code] = f"='Tâches'!$A${premier + 2}:$A${premier + 1 + len(sp.taches)}"
    ws.add_table(r0, 0, r0 + len(rows), 5, {
        "name": "Taches", "data": rows, "style": "Table Style Light 1",
        "columns": [{"header": h} for h in ["Entrée", "ID tâche", "Sous-projet", "État", "Coefficient",
                                            "Description"]],
    })
    for i, w in enumerate([38, 10, 16, 14, 11, 50]):
        ws.set_column(i, i, w)
    ws.protect("", {"autofilter": True, "sort": True})
    return plages


COLS = ["Tâche", "Description de la tâche", "État", "Rôle ou catégorie", "Désignation", "Budget",
        "Reste précédent", "Jours restants", "Débours restant", "Nature", "Code comptable", "Service",
        "Taux horaire", "Main-d’œuvre", "Débours", "Reste à engager", "Type", "Coefficient", "ID ligne"]


def sous_projet(ws, sp: SousProjet, f: Formats, liste_taches: str, liste_ref: str) -> dict[str, str]:
    """L'onglet d'un sous-projet ; rend ses cellules, que la synthèse reprend."""
    table = "RAE_" + sp.code.replace("-", "_").replace(" ", "_")
    idx = {h: i for i, h in enumerate(COLS)}

    def ref(h):
        return f"{table}[[{h}]]"

    def this(h):
        return f"{table}[[#This Row],[{h}]]"

    t0 = 14  # rang (0) de l'en-tête du tableau
    ws.write("A1", f"{sp.code} {sp.libelle}".strip(), f.titre)
    ws.write("A2", f"Revue du {REVUE} — une ligne par rôle ou par débours, comme au devis. La main-d’œuvre se "
                   f"saisit en jours de {HEURES_PAR_JOUR} heures, un débours en montant.", f.note)
    cellules = {}
    entete = [
        ("Budget du sous-projet", sp.budget, "budget"),
        ("Coûts réels imputés", sp.couts_reels, "cr"),
        ("Reste à engager du tableau", f"=SUBTOTAL(109,{ref('Reste à engager')})", "rae_t"),
        ("Provisions des risques identifiés", sp.provisions, "prov"),
    ]
    for i, (label, val, key) in enumerate(entete):
        ws.write(3 + i, 0, label)
        if isinstance(val, str):
            ws.write_formula(3 + i, 1, val, f.euros)
        else:
            ws.write_number(3 + i, 1, val, f.euros)
        cellules[key] = xl_rowcol_to_cell(3 + i, 1, row_abs=True, col_abs=True)
    indicateurs = [
        ("Reste à engager", "={rae_t}+{prov}", f.euros_gras, "rae"),
        ("Projection (coûts réels + reste)", "={cr}+{rae}", f.euros_gras, "proj"),
        ("Écart au budget", "={proj}-{budget}", f.euros_gras, "ecart"),
        ("Avancement financier", '=IF({proj}=0,"non calculable",{cr}/{proj})', f.pourcent, "av"),
    ]
    for i, (label, formule, fmt, key) in enumerate(indicateurs):
        r = 4 + len(entete) + i
        ws.write(r, 0, label, f.gras)
        ws.write_formula(r, 1, formule.format(**cellules), fmt)
        cellules[key] = xl_rowcol_to_cell(r, 1, row_abs=True, col_abs=True)
    refs = {k: f"'{sp.code}'!{v}" for k, v in cellules.items()}
    # Ce que la synthèse ventile : le reste par nature, les jours par code comptable.
    for n, _ in NATURES:
        if n == "Provisions pour risques":
            refs[n] = refs["prov"]
        else:
            refs[n] = f'SUMIFS({ref("Reste à engager")},{ref("Nature")},"{n}")'
    for c in CATS_MO:
        refs[c[0]] = f'SUMIFS({ref("Jours restants")},{ref("Code comptable")},"{c[0]}")'

    ws.merge_range(t0 - 1, idx["Jours restants"], t0 - 1, idx["Débours restant"], f"Reste au {REVUE}", f.bloc)
    codes_roles = {r[0] for r in ROLES}
    data = []
    for lg in sp.lignes:
        de_main_oeuvre = lg.entree.rsplit("(", 1)[-1].rstrip(")") in codes_roles
        data.append([lg.tache, None, None, lg.entree, lg.designation or None, lg.budget, lg.precedent,
                     lg.reste if de_main_oeuvre else None, None if de_main_oeuvre else lg.reste,
                     None, None, None, None, None, None, None, None, None, lg.lineage])
    data += [[None] * len(COLS) for _ in range(PREVUES)]

    def recherche(colonne):
        cle = this("Rôle ou catégorie")
        return (f'=IF({cle}="","",IFERROR(INDEX(Referentiel[[{colonne}]],'
                f'MATCH({cle},Referentiel[[Entrée]],0)),"?"))')

    def de_la_tache(colonne, defaut):
        return f"IFERROR(INDEX(Taches[[{colonne}]],MATCH({this('Tâche')},Taches[[Entrée]],0)),{defaut})"

    vide = f'{this("Rôle ou catégorie")}=""'
    formules = {
        "Description de la tâche": f'=IF({this("Tâche")}="","",{de_la_tache("Description", chr(34) * 2)})',
        "État": f'=IF({this("Tâche")}="","",{de_la_tache("État", chr(34) * 2)})',
        "Nature": recherche("Nature"),
        "Code comptable": recherche("Code comptable"),
        "Service": recherche("Service")[:-1] + '&"")',  # un texte vide reste vide, et non 0
        "Taux horaire": recherche("Taux horaire"),
        "Type": recherche("Type de nature"),
        "Coefficient": f"={de_la_tache('Coefficient', 1)}",
        "Main-d’œuvre": f'=IF({vide},"",IF({this("Type")}="Main-d’œuvre",N({this("Jours restants")})'
                        f'*HeuresParJour*{this("Taux horaire")}*{this("Coefficient")},0))',
        # Un débours saisi est un montant réel, inflation comprise : il entre tel quel.
        "Débours": f'=IF({vide},"",IF({this("Type")}="Hors main-d’œuvre",N({this("Débours restant")}),0))',
        "Reste à engager": f'=IF({vide},"",{this("Main-d’œuvre")}+{this("Débours")})',
    }
    colonnes = []
    for h in COLS:
        spec = {"header": h}
        if h in formules:
            spec["formula"] = formules[h]
            spec["format"] = f.calcule_euros if h in ("Main-d’œuvre", "Débours", "Reste à engager") else f.calcule
        elif h in ("Budget", "Reste précédent"):
            spec["format"] = f.calcule_euros
        elif h == "ID ligne":
            spec["format"] = f.calcule
        elif h == "Jours restants":
            spec["format"] = f.jours
        elif h == "Débours restant":
            spec["format"] = f.euros
        else:
            spec["format"] = f.texte
        colonnes.append(spec)
    colonnes[0]["total_string"] = "Total"
    for h in ("Budget", "Reste précédent", "Jours restants", "Débours restant", "Main-d’œuvre", "Débours",
              "Reste à engager"):
        colonnes[idx[h]]["total_function"] = f"=SUBTOTAL(109,{table}[[{h}]])"
    n = len(data)
    ws.add_table(t0, 0, t0 + n + 1, len(COLS) - 1, {
        "name": table, "data": data, "columns": colonnes, "total_row": True, "style": "Table Style Light 9",
    })
    ws.data_validation(t0 + 1, idx["Tâche"], t0 + 400, idx["Tâche"], {
        "validate": "list", "source": liste_taches,
        "error_message": "Choisis une tâche non terminée du sous-projet (onglet Tâches)."})
    ws.data_validation(t0 + 1, idx["Rôle ou catégorie"], t0 + 400, idx["Rôle ou catégorie"], {
        "validate": "list", "source": liste_ref,
        "error_message": "Choisis un rôle ou une catégorie du référentiel (onglet Paramètres)."})
    for h in ("Jours restants", "Débours restant"):
        ws.data_validation(t0 + 1, idx[h], t0 + 400, idx[h], {
            "validate": "decimal", "criteria": ">=", "value": 0,
            "error_message": "Un reste à engager est un nombre positif ou nul."})
    largeurs = {"Tâche": 34, "Description de la tâche": 40, "État": 13, "Rôle ou catégorie": 32,
                "Désignation": 34, "Service": 22, "Nature": 16}
    for h, i in idx.items():
        ws.set_column(i, i, largeurs.get(h, 13))
    ws.set_column(idx["Type"], idx["ID ligne"], 10, None, {"level": 1, "hidden": True})
    ws.set_row(t0, 30, f.entete)
    ws.freeze_panes(t0 + 1, 1)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    ws.write(t0 + n + 3, 0, "Les tâches terminées ne sont pas dans le fichier. Une tâche dont tout le reste vaut "
                            "zéro est terminée à la date de la revue.", f.note)
    ws.write(t0 + n + 4, 0, MENTION, f.petit)
    return refs


def synthese(ws, f: Formats, refs: dict[str, dict[str, str]]) -> None:
    """Le format et la version, le projet, puis chaque sous-projet : indicateurs et ventilation."""
    ws.write("A1", "Format")
    ws.write("B1", "Reste à engager")
    ws.write("A2", "Version")
    ws.write_number("B2", 1, f.gauche)
    ws.write_comment("A1", "Format et version, lus à l’import (annexe B) : ne pas modifier.")
    ws.insert_image("E1", str(LOGO), {"x_scale": 0.2, "y_scale": 0.2, "y_offset": 4,
                                      "object_position": 3, "description": "Waterfall"})
    ws.write("A4", f"{PROJET['code']} — {PROJET['libellé']}", f.titre)
    infos = [("Entreprise", ENTREPRISE), ("Client", PROJET["client"]), ("Révision", REVISION),
             ("Revue du", REVUE), ("Structure", "Structure principale"), ("Devise", DEVISE)]
    for i, (k, v) in enumerate(infos):
        ws.write(5 + i, 0, k, f.gras)
        ws.write(5 + i, 1, v, f.gauche)
    r0 = 6 + len(infos) + 2
    indicateurs = [("Budget", "budget"), ("Coûts réels", "cr"), ("Reste à engager", "rae"),
                   ("Projection", "proj"), ("Écart au budget", "ecart")]
    ventilation = [n for n, _ in NATURES] + [c[0] for c in CATS_MO]
    jours = {c[0] for c in CATS_MO}
    entetes = ["Sous-projet", *[h for h, _ in indicateurs], "Avancement financier",
               *[f"Reste — {n}" for n, _ in NATURES], *[f"Jours {c[0]}" for c in CATS_MO]]
    ws.merge_range(r0 - 1, 7, r0 - 1, 6 + len(ventilation), "Ventilation du reste à engager", f.bloc)
    ws.write_row(r0, 0, entetes, f.entete)
    ws.set_row(r0, 30)
    for i, sp in enumerate(SOUS_PROJETS):
        r = r0 + 1 + i
        s = refs[sp.code]
        ws.write(r, 0, f"{sp.code} {sp.libelle}".strip())
        for c, (_, key) in enumerate(indicateurs, start=1):
            ws.write_formula(r, c, f"={s[key]}", f.euros)
        ws.write_formula(r, 6, f"={s['av']}", f.pourcent)
        for c, key in enumerate(ventilation, start=7):
            ws.write_formula(r, c, f"={s[key]}", f.jours if key in jours else f.euros)
    total = r0 + 1 + len(SOUS_PROJETS)
    ws.write(total, 0, "Projet", f.gras)
    for c in range(1, 7 + len(ventilation)):
        if c == 6:
            ws.write_formula(total, c, f'=IF(E{total + 1}=0,"non calculable",C{total + 1}/E{total + 1})',
                             f.pourcent_gras)
            continue
        col = xl_col_to_name(c)
        fmt = f.jours_gras if c >= 7 + len(NATURES) else f.euros_gras
        ws.write_formula(total, c, f"=SUM({col}{r0 + 2}:{col}{total})", fmt)
    ws.write(total + 2, 0, "Écart signé dans le sens de la dérive : positif quand le sous-projet coûte plus que "
                           "son budget (WF-RAE-0020). Avancement financier : coûts réels sur projection "
                           "(WF-IND-0040).", f.note)
    ws.write(total + 4, 0, MENTION, f.petit)
    ws.set_column(0, 0, 30)
    ws.set_column(1, 6 + len(ventilation), 15)
    ws.set_landscape()
    ws.print_area(0, 0, total + 4, 6 + len(ventilation))
    ws.fit_to_pages(1, 1)


def main(sortie: str) -> None:
    wb = xlsxwriter.Workbook(sortie, {"strings_to_formulas": False})
    wb.set_properties({"title": f"Reste à engager — {PROJET['code']}", "author": "Waterfall"})
    f = Formats(wb)
    synthese_ws = wb.add_worksheet("Synthèse")
    feuilles = [wb.add_worksheet(sp.code) for sp in SOUS_PROJETS]
    taches_ws = wb.add_worksheet("Tâches")
    param_ws = wb.add_worksheet("Paramètres")
    liste_ref = parametres(wb, param_ws, f)
    listes_taches = taches(taches_ws, f)
    refs = {sp.code: sous_projet(ws, sp, f, listes_taches[sp.code], liste_ref)
            for ws, sp in zip(feuilles, SOUS_PROJETS, strict=True)}
    synthese(synthese_ws, f, refs)
    for ws in wb.worksheets():
        ws.set_footer(f"&L&8{MENTION}&R&8Page &P / &N")
    synthese_ws.activate()
    wb.close()


if __name__ == "__main__":
    main(sys.argv[1])
