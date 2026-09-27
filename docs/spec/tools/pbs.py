# -*- coding: utf-8 -*-
"""PBS allocation for the requirements of chapter 3, per the matrix in section 4.2.2.

Every function is realised at least by BASELINE. A requirement carries, among the
components on its function's row, only those it actually engages.
"""
BASELINE = ["PBS-1.1", "PBS-2.1", "PBS-2.3", "PBS-3.1"]

EXTRA = {
    # FBS-1.1 User management (row: PBS-2.5, PBS-2.2, PBS-5.3)
    "WF-ADM-0030": [], "WF-ADM-0040": [], "WF-ADM-0050": [], "WF-ADM-0080": [],
    "WF-ADM-0060": ["PBS-2.5"], "WF-ADM-0140": ["PBS-2.5"], "WF-ADM-0180": ["PBS-2.5"],
    "WF-ADM-0070": ["PBS-2.2", "PBS-2.5", "PBS-5.3"],
    # FBS-1.2 Access role management (row: PBS-2.5, PBS-3.2)
    "WF-ADM-0010": [], "WF-ADM-0020": [], "WF-ADM-0100": [], "WF-ADM-0120": [],
    "WF-INTF-0010": [], "WF-INTF-0020": [], "WF-INTF-0030": [],
    "WF-ADM-0090": ["PBS-3.2"], "WF-ADM-0110": ["PBS-3.2"],
    # Section 3.1.5, interface language: the choice is an account preference, the
    # translation rule only touches the front, and the format rules engage the
    # worker that generates exports and e-mails.
    "WF-INTF-0160": [], "WF-INTF-0170": [], "WF-INTF-0180": ["PBS-2.2"],
    # FBS-1.3 System status monitoring
    "WF-ADM-0130": ["PBS-4.1", "PBS-4.3"],
    # FBS-1.4 Backup and restore (row: PBS-2.2, PBS-3.3, PBS-5.3)
    "WF-ADM-0150": ["PBS-2.2", "PBS-3.3"], "WF-ADM-0160": ["PBS-2.2", "PBS-3.3"],
    "WF-ADM-0170": ["PBS-2.2", "PBS-3.3", "PBS-5.3"],
    # FBS-4.1 Revision management (row: PBS-2.2, PBS-3.2)
    "WF-REV-0030": [], "WF-REV-0060": [], "WF-REV-0070": [], "WF-REV-0080": [], "WF-REV-0090": [],
    "WF-REV-0010": ["PBS-2.2"], "WF-REV-0040": ["PBS-3.2"], "WF-REV-0100": [],
    "WF-REV-0020": ["PBS-2.2", "PBS-3.2"], "WF-REV-0050": ["PBS-2.2", "PBS-3.2"],
    # File imports and exports (rows FBS-4.3.4 and FBS-4.7: PBS-2.2, PBS-3.3).
    # An export is never stored (WF-DAT-0120), so it does not engage PBS-3.3.
    "WF-INTF-0040": ["PBS-2.2", "PBS-3.3"], "WF-INTF-0070": ["PBS-2.2", "PBS-3.3"],
    "WF-INTF-0080": ["PBS-2.2", "PBS-3.3"], "WF-INTF-0100": ["PBS-2.2", "PBS-3.3"],
    "WF-INTF-0120": ["PBS-2.2", "PBS-3.3"], "WF-INTF-0140": ["PBS-2.2", "PBS-3.3"],
    "WF-INTF-0150": ["PBS-2.2", "PBS-3.3"],
    "WF-INTF-0050": ["PBS-2.2"], "WF-INTF-0060": ["PBS-2.2"],
    "WF-INTF-0110": ["PBS-2.2"], "WF-INTF-0130": ["PBS-2.2"],
    "WF-INTF-0090": ["PBS-2.2"],
    # FBS-4.7 Actual costs
    "WF-CRE-0010": [], "WF-CRE-0030": [], "WF-CRE-0040": [],
    "WF-CRE-0020": ["PBS-2.2"], "WF-CRE-0050": ["PBS-2.2"],
    # Section 3.6, interface principles: grids engage the shared components, long
    # operations engage the worker, the rest only the baseline.
    "WF-IHM-0010": [], "WF-IHM-0020": [], "WF-IHM-0030": [], "WF-IHM-0090": [],
    "WF-IHM-0040": ["PBS-1.3"], "WF-IHM-0050": ["PBS-1.3"], "WF-IHM-0060": ["PBS-1.3"],
    "WF-IHM-0070": ["PBS-1.3"], "WF-IHM-0100": ["PBS-1.3"], "WF-IHM-0080": ["PBS-2.2"],
    "WF-IHM-0110": ["PBS-1.3"],
    # Grids, charts and task trees (PBS-1.3)
    "WF-PLA-0060": ["PBS-1.3"], "WF-PLA-0080": ["PBS-1.3"], "WF-PLA-0090": ["PBS-1.3"],
    "WF-PLA-0100": ["PBS-1.3"], "WF-PLA-0110": ["PBS-1.3"], "WF-PLA-0120": ["PBS-1.3"],
    "WF-PLA-0140": ["PBS-1.3"], "WF-DEV-0050": ["PBS-1.3"], "WF-DEV-0070": ["PBS-1.3"],
    "WF-RAE-0030": ["PBS-1.3"], "WF-RAE-0040": ["PBS-1.3"], "WF-RIS-0040": ["PBS-1.3"],
    # Indicators (PBS-3.2, cache of the revision in progress)
    "WF-DEV-0060": ["PBS-3.2"], "WF-RAE-0020": ["PBS-3.2"],
    "WF-IND-0040": ["PBS-3.2"], "WF-IND-0050": ["PBS-3.2"], "WF-IND-0060": ["PBS-3.2"],
    "WF-IND-0070": ["PBS-3.2"], "WF-IND-0080": ["PBS-3.2"],
    # Indicator curves and charts
    "WF-IND-0090": ["PBS-1.3", "PBS-3.2"], "WF-IND-0100": ["PBS-1.3", "PBS-3.2"],
    "WF-IND-0110": ["PBS-1.3", "PBS-3.2"], "WF-IND-0120": ["PBS-1.3", "PBS-3.2"],
}

def value(identifier):
    """PBS field of a requirement, baseline included, sorted by code."""
    base = identifier[:-2] if identifier.endswith("-A") else identifier
    codes = set(BASELINE) | set(EXTRA.get(base, []))
    return ", ".join(sorted(codes, key=lambda c: [int(n) for n in c[4:].split(".")]))
