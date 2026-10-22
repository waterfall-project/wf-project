# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Prototype du format « Devis » de l'annexe B, produit comme Waterfall le produirait.

Les données sont inventées, inspirées de l'exemple de l'auteur (Devis_waterfall.xlsx). Le script
montre ce qu'un export sait écrire : formules de recherche et de somme, listes de choix, tableaux
Excel qui s'étendent à la saisie, onglets protégés. Il n'est pas le code de Waterfall.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import xlsxwriter

# --- Données d'un projet, telles que Waterfall les lirait --------------------------------------

ENTREPRISE = "Exemple Industrie"  # saisi à l'installation (WF-EXP-0020)
PROJET = {"code": "AFF-2026-014", "libellé": "Contrôle d’accès du site de Lyon", "client": "Client Exemple"}
REVISION = "Chiffrage v2 (en cours)"
STRUCTURE = "Structure principale"
ANNEE_REF = 2026
DEVISE = "EUR"  # la devise de l'installation (WF-REF-0140) : les montants du fichier sont dans celle-ci
SYMBOLES = {"EUR": "€", "USD": "$", "GBP": "£"}
MONTANT = f'#,##0.00 "{SYMBOLES.get(DEVISE, DEVISE)}"'

EXPORTE_LE = "2026-10-22 14:05"

NATURES = [  # nom, type
    ("Main-d’œuvre", "Main-d’œuvre"),
    ("Fournitures", "Hors main-d’œuvre"),
    ("Sous-traitance", "Hors main-d’œuvre"),
    ("Provisions pour risques", "Provision"),
]
# code comptable, libellé, nature, taux horaire de l'année de référence (main-d'œuvre)
CATEGORIES = [
    ("I810", "Gestion d’affaires", "Main-d’œuvre", 100),
    ("I329", "Ingénierie logicielle", "Main-d’œuvre", 80),
    ("I1M2", "Ingénierie électronique", "Main-d’œuvre", 60),
    ("fo-AINT", "Anti-intrusion", "Fournitures", None),
    ("fo-APPA", "Appareillage", "Fournitures", None),
    ("st-POSE", "Pose sur site", "Sous-traitance", None),
    ("PRV", "Provision pour risques", "Provisions pour risques", None),
]
# code, libellé, service (chemin dans l'arbre d'organisation), catégorie
ROLES = [
    ("RA-A1", "Responsable d’affaire A1", "Affaires › Activité 1", "I810"),
    ("IQ-A1", "Ingénieur qualité A1", "Affaires › Activité 1", "I1M2"),
    ("ARCH-LOG", "Architecte logiciel", "Ingénierie › Logiciel", "I329"),
    ("DEV", "Développeur", "Ingénierie › Logiciel", "I1M2"),
    ("ARCH-ELEC", "Architecte électronique", "Ingénierie › Électronique", "I329"),
    ("ING-CARTE", "Ingénieur carte", "Ingénierie › Électronique", "I1M2"),
]
SOUS_PROJETS = [("SP-MAT", "Matériel"), ("SP-PRE", "Prestations")]


@dataclass
class Tache:
    numero: str
    libelle: str
    lineage: str
    debut: str
    fin: str
    coefficient: float  # inflation de l'année de consommation, calculée par Waterfall
    lignes: list[tuple] = field(default_factory=list)


@dataclass
class Onglet:
    nom: str  # nom de l'onglet, ramené aux règles d'Excel
    numero: str  # « 1.1 », « 1 », ou « » pour Hors lot
    libelle: str
    lot: str  # numéro du lot, pour les totaux de la synthèse
    taches: list[Tache]


def ligne(entree, quantite, heures=None, debours=None, sous_projet=None, delai=0, libelle="", lineage=""):
    return (lineage, entree, libelle, sous_projet, quantite, heures, debours, delai)


def role(code):
    r = next(r for r in ROLES if r[0] == code)
    return f"{r[1]} ({r[0]})"


def cat(code):
    c = next(c for c in CATEGORIES if c[0] == code)
    return f"{c[1]} ({c[0]})"


ONGLETS = [
    Onglet("1.1 Centrale et logiciel", "1.1", "Centrale et logiciel", "1", [
        Tache("1.1", "Centrale et logiciel", "t-0007", "2026-11-02", "2027-03-26", 1.0),
        Tache("1.1.1", "Management", "t-0011", "2026-11-02", "2027-03-26", 1.0, [
            ligne(role("RA-A1"), 5, heures=7.4, lineage="l-0101", sous_projet="SP-PRE"),
        ]),
        Tache("1.1.2", "Développement du logiciel", "t-0012", "2026-11-09", "2027-02-26", 1.0, [
            ligne(role("ARCH-LOG"), 20, heures=7.4, lineage="l-0102", sous_projet="SP-PRE"),
            ligne(role("DEV"), 60, heures=7.4, lineage="l-0103", sous_projet="SP-PRE"),
        ]),
        Tache("1.1.3", "Carte d’interface", "t-0013", "2026-11-09", "2027-01-29", 1.0, [
            ligne(role("ING-CARTE"), 15, heures=7.4, lineage="l-0104", sous_projet="SP-PRE"),
            ligne(cat("fo-AINT"), 5, debours=20, lineage="l-0105", sous_projet="SP-MAT", delai=30,
                  libelle="Détecteurs"),
        ]),
    ]),
    Onglet("1.2 Lecteurs et câblage", "1.2", "Lecteurs et câblage", "1", [
        Tache("1.2", "Lecteurs et câblage", "t-0008", "2027-01-04", "2027-04-30", 1.02),
        Tache("1.2.1", "Approvisionnement des lecteurs", "t-0021", "2027-01-04", "2027-02-26", 1.02, [
            ligne(cat("fo-APPA"), 40, debours=180, lineage="l-0201", sous_projet="SP-MAT", delai=45,
                  libelle="Lecteurs de badges"),
            ("l-0202", cat("PRV"), "Provision — Retard de livraison des lecteurs", None, 1, None, 1500, None),
        ]),
        Tache("1.2.2", "Câblage", "t-0022", "2027-03-01", "2027-04-30", 1.02, [
            ligne(cat("st-POSE"), 1, debours=8500, lineage="l-0203", sous_projet="SP-PRE", delai=60),
        ]),
    ]),
    Onglet("1 Contrôle d’accès", "1", "Contrôle d’accès, hors postes", "1", [
        Tache("1", "Contrôle d’accès", "t-0003", "2026-11-02", "2027-04-30", 1.0),
        Tache("1.3", "Revue de conception", "t-0009", "2026-12-14", "2026-12-18", 1.0, [
            ligne(role("ARCH-ELEC"), 3, heures=7.4, lineage="l-0301"),
        ]),
    ]),
    Onglet("2.1 Essais sur site", "2.1", "Essais sur site", "2", [
        Tache("2", "Mise en service", "t-0004", "2027-05-03", "2027-06-25", 1.02),
        Tache("2.1", "Essais sur site", "t-0010", "2027-05-03", "2027-06-25", 1.02),
        Tache("2.1.1", "Essais", "t-0031", "2027-05-03", "2027-06-11", 1.02, [
            ligne(role("IQ-A1"), 10, heures=7.4, lineage="l-0401", sous_projet="SP-PRE"),
            ligne(role("ING-CARTE"), 10, heures=7.4, lineage="l-0402", sous_projet="SP-PRE"),
        ]),
    ]),
    Onglet("Hors lot", "", "Hors lot", "", [
        Tache("3", "Gestion de projet", "t-0005", "2026-11-02", "2027-06-25", 1.01, [
            ligne(role("RA-A1"), 20, heures=7.4, lineage="l-0501", libelle="=1+1 reste une désignation"),
        ]),
    ]),
]
# La description de chaque tâche, que le planning et MS Project portent (WF-PLA-0130) : écrite pour
# la lecture, elle ne se modifie que dans Waterfall ou dans MS Project.
DESCRIPTIONS = {
    "1.1.1": "Pilotage, réunions d’avancement et compte rendu au client",
    "1.1.2": "Logiciel de la centrale : gestion des badges et des droits d’accès",
    "1.1.3": "Carte d’interface entre la centrale et les lecteurs",
    "1.2.1": "Achat et réception des lecteurs de badges",
    "1.2.2": "Tirage des câbles et raccordement des lecteurs",
    "1.3": "Revue de conception préliminaire avec le client",
    "2.1.1": "Essais d’intégration et recette sur site",
    "3": "Gestion de projet transverse",
}
LOTS = [("1", "Contrôle d’accès"), ("2", "Mise en service")]
LOGO = Path(__file__).resolve().parents[2] / "assets" / "waterfall_logo.png"
# Le fichier est celui de l'utilisateur : la mention dit d'où il vient, elle ne revendique rien
# sur son contenu.
MENTION = (f"© {EXPORTE_LE[:4]} {ENTREPRISE} — Généré par Waterfall le {EXPORTE_LE} — "
           "logiciel libre sous licence AGPL-3.0 — www.waterfall-project.pro")
PREVUES = 30  # lignes vides préparées sous les lignes exportées, avec listes et formules

# --- Colonnes d'un onglet de lignes -------------------------------------------------------------
# (en-tête, lu à l'import ?, largeur). L'ordre importe peu à l'import, qui lit par en-tête.
COLONNES = [
    ("Tâche", True, 34),
    ("Description de la tâche", False, 34),
    ("Rôle ou catégorie", True, 34),
    ("Désignation", True, 30),  # facultative : vide, Waterfall compose le libellé de la ligne
    ("Quantité", True, 10),
    ("Heures", True, 9),
    ("Débours unitaire", True, 12),
    ("Délai de paiement (j)", True, 11),
    ("Sous-projet", True, 12),  # facultatif ; sert surtout aux avenants et aux risques d'un projet En cours
    ("Nature", False, 18),
    ("Code comptable", False, 11),
    ("Service", False, 22),
    ("Taux horaire", False, 9),
    ("Heures totales", False, 10),
    ("Main-d’œuvre", False, 13),
    ("Débours", False, 13),
    ("Montant", False, 13),
    ("Montant Waterfall", False, 14),
    ("ID ligne", True, 10),
]
LU = {nom for nom, lu, _ in COLONNES if lu}
# Les en-têtes ne nomment pas la devise : ils sont fixes, et la devise est celle de l'installation.
MONTANTS = {"Main-d’œuvre", "Débours", "Montant", "Montant Waterfall"}


def this(table, colonne):
    return f"{table}[[#This Row],[{colonne}]]"


def recherche(table, colonne_ref):
    """La colonne du référentiel pour le rôle ou la catégorie de la ligne, vide si rien n'est choisi."""
    cle = this(table, "Rôle ou catégorie")
    return (f'=IF({cle}="","",IFERROR(INDEX(Referentiel[[{colonne_ref}]],'
            f'MATCH({cle},Referentiel[[Entrée]],0)),"?"))')


def formules(table):
    def t(colonne):
        return this(table, colonne)

    vide = f'{t("Rôle ou catégorie")}=""'
    return {
        "Description de la tâche": f'=IF({t("Tâche")}="","",IFERROR(INDEX(Taches[[Description]],'
                                   f'MATCH({t("Tâche")},Taches[[Entrée]],0)),""))',
        "Nature": recherche(table, "Nature"),
        "Code comptable": recherche(table, "Code comptable"),
        "Service": recherche(table, "Service")[:-1] + '&"")',  # un texte vide reste vide, et non 0
        "Taux horaire": recherche(table, "Taux horaire"),
        "Heures totales": f'=IF({vide},"",IF({t("Type")}="Main-d’œuvre",{t("Quantité")}*{t("Heures")},0))',
        "Main-d’œuvre": f'=IF({vide},"",IF({t("Type")}="Main-d’œuvre",{t("Quantité")}*{t("Heures")}*{t("Taux horaire")},0))',
        "Débours": f'=IF({vide},"",IF(OR({t("Type")}="Hors main-d’œuvre",{t("Type")}="Provision"),'
                       f'{t("Quantité")}*{t("Débours unitaire")},0))',
        "Montant": f'=IF({vide},"",{t("Main-d’œuvre")}+{t("Débours")})',
        "Type": recherche(table, "Type de nature"),
    }


def main(sortie: str) -> None:
    # Un texte saisi reste un texte : un libellé « =… » ne devient jamais une formule. Seules
    # les formules écrites comme telles (write_formula, colonnes calculées) en sont.
    wb = xlsxwriter.Workbook(sortie, {"strings_to_formulas": False})
    wb.set_properties({"title": f"Devis — {PROJET['code']}", "author": "Waterfall"})
    wb.set_calc_mode("auto")

    gras = wb.add_format({"bold": True})
    titre = wb.add_format({"bold": True, "font_size": 14})
    euros = wb.add_format({"num_format": MONTANT})
    euros_gras = wb.add_format({"num_format": MONTANT, "bold": True, "top": 1})
    heures_fmt = wb.add_format({"num_format": "#,##0.0"})
    heures_gras = wb.add_format({"num_format": "#,##0.0", "bold": True, "top": 1})
    pourcent = wb.add_format({"num_format": "0.0 %"})
    calcule = wb.add_format({"bg_color": "#EEEEEE", "font_color": "#555555"})
    calcule_euros = wb.add_format({"bg_color": "#EEEEEE", "font_color": "#555555", "num_format": MONTANT})
    calcule_h = wb.add_format({"bg_color": "#EEEEEE", "font_color": "#555555", "num_format": "#,##0.0"})
    note = wb.add_format({"italic": True, "font_color": "#666666", "text_wrap": True, "valign": "top"})
    lot_fmt = wb.add_format({"bold": True, "bg_color": "#DDEBF7"})
    lot_euros = wb.add_format({"bold": True, "bg_color": "#DDEBF7", "num_format": MONTANT})
    lot_h = wb.add_format({"bold": True, "bg_color": "#DDEBF7", "num_format": "#,##0.0"})
    texte = wb.add_format({"num_format": "@"})

    presentation = wb.add_worksheet("Présentation")
    synthese = wb.add_worksheet("Devis")
    feuilles = [wb.add_worksheet(o.nom) for o in ONGLETS]
    taches_ws = wb.add_worksheet("Tâches")
    param = wb.add_worksheet("Paramètres")

    # --- Paramètres : le référentiel lu par les formules, protégé --------------------------------
    param.write("A1", "Référentiel de la révision : écrit par l’export, ignoré à l’import.", gras)
    param.write("A2", f"Taux horaires de l’année de référence {ANNEE_REF} retenus par la révision. "
                      "Les modifier ici ne change aucun taux dans Waterfall.", note)
    nature_type = dict(NATURES)
    cat_par_code = {c[0]: c for c in CATEGORIES}
    lignes_ref = []
    for code, libelle, service, categorie in ROLES:  # rôles, triés par service
        c = cat_par_code[categorie]
        lignes_ref.append([f"{libelle} ({code})", "Rôle", code, libelle, service, c[2], nature_type[c[2]], c[0], c[3]])
    for code, libelle, nature, _ in CATEGORIES:  # catégories hors main-d'œuvre, puis provisions
        if nature_type[nature] != "Main-d’œuvre":
            lignes_ref.append([f"{libelle} ({code})", "Catégorie", code, libelle, "", nature, nature_type[nature], code, None])
    lignes_ref.sort(key=lambda r: {"Main-d’œuvre": 0, "Hors main-d’œuvre": 1, "Provision": 2}[r[6]])
    entete_ref = ["Entrée", "Genre", "Code", "Libellé", "Service", "Nature", "Type de nature", "Code comptable", "Taux horaire"]
    debut = 4
    param.add_table(debut - 1, 0, debut - 1 + len(lignes_ref), len(entete_ref) - 1, {
        "name": "Referentiel", "data": lignes_ref, "style": "Table Style Light 1",
        "columns": [{"header": h} for h in entete_ref],
    })
    choisissables = sum(1 for r in lignes_ref if r[6] != "Provision")  # une provision ne se saisit pas
    liste_ref = f"='Paramètres'!$A${debut + 1}:$A${debut + choisissables}"
    col_sp = len(entete_ref) + 1
    param.add_table(debut - 1, col_sp, debut - 1 + len(SOUS_PROJETS), col_sp + 1, {
        "name": "SousProjets", "data": [list(s) for s in SOUS_PROJETS], "style": "Table Style Light 1",
        "columns": [{"header": "Code"}, {"header": "Libellé"}],
    })
    liste_sp = f"='Paramètres'!${xlsxwriter.utility.xl_col_to_name(col_sp)}${debut + 1}:${xlsxwriter.utility.xl_col_to_name(col_sp)}${debut + len(SOUS_PROJETS)}"
    for i, w in enumerate([34, 10, 10, 26, 24, 22, 18, 14, 11, 2, 10, 16]):
        param.set_column(i, i, w)
    param.protect("", {"autofilter": True, "sort": True})

    # --- Tâches : le dictionnaire des tâches, par onglet, protégé ------------------------------
    taches_ws.write("A1", "Tâches de la structure : la liste de chaque onglet, et l’identifiant que l’import retrouve.", gras)
    rows_t, plage_par_onglet = [], {}
    r0 = 4
    for o in ONGLETS:
        premier = r0 + len(rows_t)
        for t in o.taches:
            rows_t.append([f"{t.numero} {t.libelle}", t.lineage, t.numero, t.libelle, o.nom, t.debut, t.fin,
                           DESCRIPTIONS.get(t.numero, "")])
        plage_par_onglet[o.nom] = f"='Tâches'!$A${premier + 1}:$A${r0 + len(rows_t)}"
    taches_ws.add_table(r0 - 1, 0, r0 - 1 + len(rows_t), 7, {
        "name": "Taches", "data": rows_t, "style": "Table Style Light 1",
        "columns": [{"header": h} for h in ["Entrée", "ID tâche", "N°", "Libellé", "Onglet", "Début", "Fin",
                                            "Description"]],
    })
    for i, w in enumerate([40, 10, 8, 34, 26, 11, 11, 50]):
        taches_ws.set_column(i, i, w)
    taches_ws.protect("", {"autofilter": True, "sort": True})

    # --- Un onglet de lignes par poste, un par lot hors de ses postes, « Hors lot » ------------
    entetes = [c[0] for c in COLONNES] + ["Type"]
    noms_tables = []
    for ws, o in zip(feuilles, ONGLETS):
        table = "Lignes_" + (o.numero.replace(".", "_") if o.numero else "hors_lot")
        noms_tables.append(table)
        f = formules(table)
        data = []
        for t in o.taches:
            for (lineage, entree, libelle, sp, qte, h, deb, delai) in t.lignes:
                mo = h is not None
                taux = None
                montant_ref = 0.0
                if mo:
                    r = next(r for r in lignes_ref if r[0] == entree)
                    taux = r[8]
                    montant_ref = qte * h * taux
                else:
                    montant_ref = qte * deb
                data.append([f"{t.numero} {t.libelle}", None, entree, libelle, qte, h, deb, delai, sp or ""]
                            + [None] * 8 + [round(montant_ref * t.coefficient, 2), lineage, None])
        n = len(data) + PREVUES
        data += [[None] * len(entetes) for _ in range(PREVUES)]
        colonnes = []
        for h in entetes:
            spec = {"header": h}
            if h in f:
                spec["formula"] = f[h]
                spec["format"] = calcule_euros if h in MONTANTS else calcule_h if h == "Heures totales" else calcule
            elif h == "Montant Waterfall":
                spec["format"] = calcule_euros
            elif h in ("Tâche", "Rôle ou catégorie", "Désignation", "Sous-projet"):
                spec["format"] = texte
            colonnes.append(spec)
        colonnes[-1]["total_function"] = None
        colonnes[0]["total_string"] = "Total"
        # Le total est déclaré dans le tableau (sinon Excel le répare), et nomme son tableau :
        # LibreOffice ne lit pas la forme courte « [Colonne] » que XlsxWriter écrit pour « sum ».
        for h in ("Heures totales", "Main-d’œuvre", "Débours", "Montant", "Montant Waterfall"):
            colonnes[entetes.index(h)]["total_function"] = f"=SUBTOTAL(109,{table}[[{h}]])"
        ws.add_table(0, 0, n + 1, len(entetes) - 1, {
            "name": table, "data": data, "columns": colonnes, "total_row": True,
            "style": "Table Style Light 9",
        })
        # Les listes valent pour bien plus de lignes que le tableau, qui s'étend à la saisie.
        idx = {h: i for i, h in enumerate(entetes)}
        ws.data_validation(1, idx["Tâche"], 1000, idx["Tâche"], {
            "validate": "list", "source": plage_par_onglet[o.nom],
            "error_title": "Tâche", "error_message": "Choisis une tâche de cet onglet (onglet Tâches)."})
        ws.data_validation(1, idx["Rôle ou catégorie"], 1000, idx["Rôle ou catégorie"], {
            "validate": "list", "source": liste_ref,
            "error_title": "Rôle ou catégorie", "error_message": "Choisis un rôle ou une catégorie du référentiel."})
        ws.data_validation(1, idx["Sous-projet"], 1000, idx["Sous-projet"], {
            "validate": "list", "source": liste_sp, "ignore_blank": True})
        for i, (_, lu, w) in enumerate(COLONNES):
            ws.set_column(i, i, w)
        ws.set_column(idx["ID ligne"], idx["ID ligne"], 10, None, {"level": 1, "hidden": True})
        ws.set_column(idx["Type"], idx["Type"], 14, None, {"level": 1, "hidden": True})
        ws.freeze_panes(1, 1)
        ws.write_comment(0, idx["Montant Waterfall"],
                         "Écrit par l’export : le montant de la ligne inflation comprise, que Waterfall calcule "
                         "à l’année de consommation de la tâche. Vide pour une ligne ajoutée dans Excel.")
        ws.write_comment(0, idx["ID ligne"], "Identifiant de lignée, écrit par l’export. Vide : la ligne est nouvelle.")

    # --- Devis : une ligne par lot, par poste, par lot hors postes, et Hors lot ------------------
    # Ventilation par nature de coût, puis heures par code comptable de main-d'œuvre. Une ligne
    # dont « Inclus » vaut Non passe à zéro ; les lots et le total additionnent les lignes.
    cats_mo = [c for c in CATEGORIES if nature_type[c[2]] == "Main-d’œuvre"]
    a1 = xlsxwriter.utility.xl_rowcol_to_cell
    synthese.write("A1", f"Devis — {PROJET['code']} {PROJET['libellé']}", titre)
    synthese.write("A2", "Aux taux de l’année de référence, avant inflation. « Inclus » n’est pas lu à l’import.",
                   wb.add_format({"italic": True, "font_color": "#666666"}))
    entete = ["N°", "Lot ou poste", "Inclus", "Niveau"] + [n for n, _ in NATURES] \
        + [f"Heures {c[0]}" for c in cats_mo] + ["Total", "Montant Waterfall"]
    col = {h: i for i, h in enumerate(entete)}
    R = 4  # rang (0) de la ligne d'en-tête
    synthese.write_row(R, 0, entete, wb.add_format({"bold": True, "text_wrap": True, "bottom": 1, "valign": "top"}))
    synthese.set_row(R, 32)
    plan = []
    for num, lib in LOTS:
        plan.append(("lot", num, lib, None))
        plan += [("onglet", o.numero, o.libelle, t) for o, t in zip(ONGLETS, noms_tables) if o.lot == num]
    plan += [("onglet", "", o.libelle, t) for o, t in zip(ONGLETS, noms_tables) if not o.lot]
    premier_rang, dernier_rang = R + 1, R + len(plan)

    def par_onglet(tbl, h):
        if h.startswith("Heures "):
            code = h.removeprefix("Heures ")
            return f'SUMIFS({tbl}[[Heures totales]],{tbl}[[Code comptable]],"{code}")'
        if h == "Total":
            return f"SUM({tbl}[[Montant]])"
        if h == "Montant Waterfall":
            return f"SUM({tbl}[[Montant Waterfall]])"
        return f'SUMIFS({tbl}[[Montant]],{tbl}[[Nature]],"{h}")'

    for i, (genre, num, lib, tbl) in enumerate(plan):
        r = premier_rang + i
        if genre == "lot":
            # Les onglets du lot suivent sa ligne : la somme ne contient jamais la ligne du lot.
            k = sum(1 for o in ONGLETS if o.lot == num)
            synthese.write_string(r, 0, num, lot_fmt)
            synthese.write(r, 1, lib, lot_fmt)
            synthese.write(r, 2, "", lot_fmt)
            synthese.write(r, 3, "lot", lot_fmt)
            for h in entete[4:]:
                c = col[h]
                synthese.write_formula(r, c, f"=SUM({a1(r + 1, c)}:{a1(r + k, c)})",
                                       lot_h if h.startswith("Heures") else lot_euros)
        else:
            synthese.write_string(r, 0, num)
            synthese.write(r, 1, lib)
            synthese.write(r, 2, "Oui")
            synthese.data_validation(r, 2, r, 2, {"validate": "list", "source": ["Oui", "Non"]})
            synthese.write(r, 3, "onglet")
            for h in entete[4:]:
                synthese.write_formula(r, col[h], f'=IF($C${r + 1}="Oui",{par_onglet(tbl, h)},0)',
                                       heures_fmt if h.startswith("Heures") else euros)
    total_rang = dernier_rang + 1
    synthese.write(total_rang, 1, "Total", gras)
    niveaux = f"$D${premier_rang + 1}:$D${dernier_rang + 1}"
    for h in entete[4:]:
        c = col[h]
        cellules = f"{a1(premier_rang, c)}:{a1(dernier_rang, c)}"
        synthese.write_formula(total_rang, c, f'=SUMIFS({cellules},{niveaux},"onglet")',
                               heures_gras if h.startswith("Heures") else euros_gras)
    synthese.set_column(0, 0, 6)
    synthese.set_column(1, 1, 30)
    synthese.set_column(2, 2, 7)
    synthese.set_column(3, 3, 7, None, {"hidden": True})
    synthese.set_column(4, len(entete) - 1, 14)
    synthese.freeze_panes(R + 1, 2)

    # --- Présentation : le format, la version, la ventilation par nature --------------------------
    presentation.write("A1", "Format")
    presentation.write("B1", "Devis")
    presentation.write("A2", "Version")
    presentation.write_number("B2", 1, wb.add_format({"align": "left"}))
    presentation.write_comment("A1", "Format et version, lus à l’import (annexe B) : ne pas modifier.")
    presentation.insert_image("D1", str(LOGO), {"x_scale": 0.2, "y_scale": 0.2, "x_offset": 0, "y_offset": 4,
                                                "object_position": 3, "description": "Waterfall"})
    presentation.write("A4", f"{PROJET['code']} — {PROJET['libellé']}", titre)
    infos = [("Entreprise", ENTREPRISE), ("Client", PROJET["client"]), ("Révision", REVISION), ("Structure", STRUCTURE), ("Année de référence", ANNEE_REF),
             ("Devise", DEVISE), ("Exporté le", EXPORTE_LE)]
    for i, (k, v) in enumerate(infos):
        presentation.write(5 + i, 0, k, gras)
        presentation.write(5 + i, 1, v, wb.add_format({"align": "left"}))
    base = 6 + len(infos)
    presentation.write(base, 0, "Ventilation par nature de coût, aux taux de l’année de référence, avant inflation", gras)
    presentation.write_row(base + 1, 0, ["Nature", "Montant", "Part"], gras)
    ligne_total = base + 2 + len(NATURES)
    for i, (nature, _) in enumerate(NATURES):
        rr = base + 2 + i
        presentation.write(rr, 0, nature)
        presentation.write_formula(rr, 1, f"=Devis!{a1(total_rang, col[nature])}", euros)
        presentation.write_formula(rr, 2, f"=IF({a1(ligne_total, 1)}=0,0,{a1(rr, 1)}/{a1(ligne_total, 1)})", pourcent)
    presentation.write(ligne_total, 0, "Total", gras)
    presentation.write_formula(ligne_total, 1, f"=SUM({a1(base + 2, 1)}:{a1(ligne_total - 1, 1)})", euros_gras)
    fin = ligne_total + 2
    presentation.write(fin, 0, "Montant Waterfall, inflation comprise", gras)
    presentation.write_formula(fin, 1, f"=Devis!{a1(total_rang, col['Montant Waterfall'])}", euros_gras)
    presentation.write(fin + 1, 0, "Celui des lignes exportées : le montant inflation comprise d’une ligne "
                                   "ajoutée ou modifiée dans Excel n’est connu qu’après l’import.", wb.add_format({"italic": True, "font_color": "#666666"}))
    presentation.write(fin + 3, 0, MENTION, wb.add_format({"font_size": 8, "font_color": "#666666"}))
    presentation.set_column(0, 0, 44)
    presentation.set_column(1, 1, 24)
    presentation.set_column(2, 2, 10)
    presentation.set_column(3, 3, 34)  # le logo
    presentation.print_area(0, 0, fin + 3, 3)
    presentation.fit_to_pages(1, 1)
    for ws in wb.worksheets():
        ws.set_footer(f"&L&8{MENTION}&R&8Page &P / &N")
    presentation.activate()
    wb.close()


if __name__ == "__main__":
    main(sys.argv[1])
