# -*- coding: utf-8 -*-
"""Écrit le champ PBS des exigences du document Word, à la place de « TBD »."""
import pathlib, re, shutil, sys, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pbs

DOCX = str(pathlib.Path(__file__).resolve().parent.parent / 'stb-waterfall.docx')
RE_TBL = re.compile(r'<w:tbl>.*?</w:tbl>', re.S)
RE_TR = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
RE_TC = re.compile(r'<w:tc>.*?</w:tc>', re.S)
RE_T = re.compile(r'<w:t(?:\s[^>]*)?>(.*?)</w:t>', re.S)

def texte(xml):
    return ''.join(RE_T.findall(xml)).replace('\xa0', ' ').strip()

def maj_tableau(tbl, journal):
    """Remplace « TBD » par la valeur voulue dans la ligne PBS ; None si rien à faire."""
    lignes = list(RE_TR.finditer(tbl))
    champs = {}
    for m in lignes:
        cs = list(RE_TC.finditer(m.group(0)))
        if len(cs) >= 2:
            champs[texte(cs[0].group(0))] = (m, cs[1], texte(cs[1].group(0)))
    if 'ID' not in champs or 'PBS' not in champs:
        return None
    identifiant = champs['ID'][2]
    if not re.fullmatch(r'WF-[A-Z]+-\d{4}-[A-Z#]', identifiant):
        journal.append(f'identifiant inattendu : {identifiant!r}')
        return None
    ligne, cellule, valeur_actuelle = champs['PBS']
    if valeur_actuelle != 'TBD':
        return None
    nouvelle = pbs.valeur(identifiant)
    tc = cellule.group(0)
    if len(RE_T.findall(tc)) != 1:
        journal.append(f'{identifiant} : {len(RE_T.findall(tc))} runs dans la cellule PBS, non modifiée')
        return None
    tc2 = RE_T.sub(lambda m: m.group(0).replace('>TBD</w:t>', f'>{nouvelle}</w:t>'), tc, count=1)
    # Les offsets de `cellule` sont relatifs à la ligne, ceux de `ligne` au tableau.
    tr = ligne.group(0)
    tr2 = tr[:cellule.start()] + tc2 + tr[cellule.end():]
    journal.append(f'{identifiant} → {nouvelle}')
    return tbl[:ligne.start()] + tr2 + tbl[ligne.end():]

def main():
    shutil.copy2(DOCX, DOCX + '.avant-pbs')
    with zipfile.ZipFile(DOCX) as z:
        noms = z.namelist()
        contenus = {n: z.read(n) for n in noms}
    xml = contenus['word/document.xml'].decode('utf-8')
    journal, sorties, fin = [], [], 0
    for m in RE_TBL.finditer(xml):
        nouveau = maj_tableau(m.group(0), journal)
        if nouveau is not None:
            sorties.append(xml[fin:m.start()]); sorties.append(nouveau); fin = m.end()
    sorties.append(xml[fin:])
    contenus['word/document.xml'] = ''.join(sorties).encode('utf-8')
    with zipfile.ZipFile(DOCX, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in noms:
            z.writestr(n, contenus[n])
    modifiees = [l for l in journal if '→' in l]
    print(f'{len(modifiees)} exigence(s) modifiée(s)')
    for l in journal:
        if '→' not in l:
            print('  !', l)
    return modifiees

if __name__ == '__main__':
    main()
