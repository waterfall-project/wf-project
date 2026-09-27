# -*- coding: utf-8 -*-
"""Allocation des champs PBS des exigences du §3, d'après la matrice du §4.2.2.

Socle commun à toute fonction : PBS-1.1, PBS-2.1, PBS-2.3, PBS-3.1.
Une exigence ne porte, parmi les composants de la ligne de sa fonction, que
ceux qu'elle engage réellement.
"""
SOCLE = ["PBS-1.1", "PBS-2.1", "PBS-2.3", "PBS-3.1"]

SUP = {
    # FBS-1.1 Gestion des utilisateurs (ligne : PBS-2.5, PBS-2.2, PBS-5.3)
    "WF-ADM-0030": [], "WF-ADM-0040": [], "WF-ADM-0050": [], "WF-ADM-0080": [],
    "WF-ADM-0060": ["PBS-2.5"], "WF-ADM-0140": ["PBS-2.5"], "WF-ADM-0180": ["PBS-2.5"],
    "WF-ADM-0070": ["PBS-2.2", "PBS-2.5", "PBS-5.3"],
    # FBS-1.2 Gestion des rôles d'habilitation (ligne : PBS-2.5, PBS-3.2)
    "WF-ADM-0010": [], "WF-ADM-0020": [], "WF-ADM-0100": [], "WF-ADM-0120": [],
    "WF-INTF-0010": [], "WF-INTF-0020": [], "WF-INTF-0030": [],
    "WF-ADM-0090": ["PBS-3.2"], "WF-ADM-0110": ["PBS-3.2"],
    # §3.1.5 Langue de l'interface : le choix est une préférence du compte, la
    # règle de traduction ne touche que l'interface, les formats engagent le
    # worker qui engendre exports et courriels.
    "WF-INTF-0160": [], "WF-INTF-0170": [], "WF-INTF-0180": ["PBS-2.2"],
    # FBS-1.3 Surveillance de l'état du système
    "WF-ADM-0130": ["PBS-4.1", "PBS-4.3"],
    # FBS-1.4 Sauvegarde et restauration (ligne : PBS-2.2, PBS-3.3, PBS-5.3)
    "WF-ADM-0150": ["PBS-2.2", "PBS-3.3"], "WF-ADM-0160": ["PBS-2.2", "PBS-3.3"],
    "WF-ADM-0170": ["PBS-2.2", "PBS-3.3", "PBS-5.3"],
    # FBS-4.1 Gestion des révisions (ligne : PBS-2.2, PBS-3.2)
    "WF-REV-0030": [], "WF-REV-0060": [], "WF-REV-0070": [], "WF-REV-0080": [], "WF-REV-0090": [],
    "WF-REV-0010": ["PBS-2.2"], "WF-REV-0040": ["PBS-3.2"], "WF-REV-0100": [],
    "WF-REV-0020": ["PBS-2.2", "PBS-3.2"], "WF-REV-0050": ["PBS-2.2", "PBS-3.2"],
    # Imports et exports par fichier (ligne FBS-4.3.4 / FBS-4.7 : PBS-2.2, PBS-3.3).
    # Un export n'est pas stocké (WF-DAT-0120) : il n'engage pas PBS-3.3.
    "WF-INTF-0040": ["PBS-2.2", "PBS-3.3"], "WF-INTF-0070": ["PBS-2.2", "PBS-3.3"],
    "WF-INTF-0080": ["PBS-2.2", "PBS-3.3"], "WF-INTF-0100": ["PBS-2.2", "PBS-3.3"],
    "WF-INTF-0120": ["PBS-2.2", "PBS-3.3"], "WF-INTF-0140": ["PBS-2.2", "PBS-3.3"],
    "WF-INTF-0150": ["PBS-2.2", "PBS-3.3"],
    "WF-INTF-0050": ["PBS-2.2"], "WF-INTF-0060": ["PBS-2.2"],
    "WF-INTF-0110": ["PBS-2.2"], "WF-INTF-0130": ["PBS-2.2"],
    "WF-INTF-0090": ["PBS-2.2"],
    # FBS-4.7 Coûts réels
    "WF-CRE-0010": [], "WF-CRE-0030": [], "WF-CRE-0040": [],
    "WF-CRE-0020": ["PBS-2.2"], "WF-CRE-0050": ["PBS-2.2"],
    # §3.6 Principes d'interface : les grilles engagent les composants partagés,
    # les traitements longs le worker, le reste le socle.
    "WF-IHM-0010": [], "WF-IHM-0020": [], "WF-IHM-0030": [], "WF-IHM-0090": [],
    "WF-IHM-0040": ["PBS-1.3"], "WF-IHM-0050": ["PBS-1.3"], "WF-IHM-0060": ["PBS-1.3"],
    "WF-IHM-0070": ["PBS-1.3"], "WF-IHM-0100": ["PBS-1.3"], "WF-IHM-0080": ["PBS-2.2"],
    "WF-IHM-0110": ["PBS-1.3"],
    # Grilles, diagrammes et arborescences (PBS-1.3)
    "WF-PLA-0060": ["PBS-1.3"], "WF-PLA-0080": ["PBS-1.3"], "WF-PLA-0090": ["PBS-1.3"],
    "WF-PLA-0100": ["PBS-1.3"], "WF-PLA-0110": ["PBS-1.3"], "WF-PLA-0120": ["PBS-1.3"],
    "WF-PLA-0140": ["PBS-1.3"], "WF-DEV-0050": ["PBS-1.3"], "WF-DEV-0070": ["PBS-1.3"],
    "WF-RAE-0030": ["PBS-1.3"], "WF-RAE-0040": ["PBS-1.3"], "WF-RIS-0040": ["PBS-1.3"],
    # Indicateurs (PBS-3.2, cache de la révision en cours)
    "WF-DEV-0060": ["PBS-3.2"], "WF-RAE-0020": ["PBS-3.2"],
    "WF-IND-0040": ["PBS-3.2"], "WF-IND-0050": ["PBS-3.2"], "WF-IND-0060": ["PBS-3.2"],
    "WF-IND-0070": ["PBS-3.2"], "WF-IND-0080": ["PBS-3.2"],
    # Courbes et diagrammes d'indicateurs
    "WF-IND-0090": ["PBS-1.3", "PBS-3.2"], "WF-IND-0100": ["PBS-1.3", "PBS-3.2"],
    "WF-IND-0110": ["PBS-1.3", "PBS-3.2"], "WF-IND-0120": ["PBS-1.3", "PBS-3.2"],
}

def valeur(identifiant):
    """Champ PBS d'une exigence, socle compris, trié par code."""
    base = identifiant[:-2] if identifiant.endswith("-A") else identifiant
    codes = set(SOCLE) | set(SUP.get(base, []))
    return ", ".join(sorted(codes, key=lambda c: [int(n) for n in c[4:].split(".")]))
