"""LISEZMOI du kit v24 (sans colle) : contenu, plateaux, reglages, principe d'emboitement, changements, pieces par plateau."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import os, json, collections, re, textwrap
HERE = ROOT + '/v25'
KIT = os.path.join(HERE, 'kit', 'Bowen28_kit_impression_v24')
meta = json.load(open(os.path.join(HERE, 'kit_meta.json')))
plates, pieces = meta['plates'], meta['pieces']
import sys; sys.path.insert(0, HERE)
from noms25 import nice
FIL = {'blanc': 'PLA Matte Ivory White', 'alu': 'PLA Basic Silver', 'noir': 'PLA Matte Charcoal', 'teck': 'PLA Matte Caramel', 'taupe': 'PLA Matte Dark Brown'}
CN = {'blanc': 'Blanc cassé', 'alu': 'Gris alu', 'noir': 'Noir', 'teck': 'Teck', 'taupe': 'Taupe'}
DIRS = {'blanc': '1_blanc', 'alu': '2_alu', 'noir': '3_noir', 'teck': '4_teck', 'taupe': '5_taupe'}


def nb(t): return re.sub(r" ([:;?!»])", " \\1", t).replace("« ", "« ")
def wrap(t, first='', rest='', w=100): return textwrap.wrap(nb(t), w, initial_indent=first, subsequent_indent=rest, break_on_hyphens=False, break_long_words=False)
def g(x): return f"{int(round(x / 5.0) * 5)}\u00a0g" if x >= 10 else f"{max(1, round(x))}\u00a0g"


main = [p for p in plates if not p['eprouvette']]; epr = [p for p in plates if p['eprouvette']]
n_main = sum(len(p['inst']) for p in main); n_epr = sum(len(p['inst']) for p in epr)
L = []
title = "BOWEN 28 AU 1:19 – KIT D'IMPRESSION v24, MONTAGE SANS COLLE"
L += [title, "=" * len(title), ""]
L += wrap(f"Tout ce qu'il faut pour imprimer la maquette : {n_main} pièces réparties sur {len(main)} plateaux, une seule couleur de "
          f"filament par plateau, plus l'éprouvette de réglage P00 ({n_epr} petites pièces) à imprimer en premier. La maquette "
          "s'assemble entièrement par emboîtement, comme des Lego : ni colle, ni goupille, ni toile, uniquement du PLA ou du PLA+. "
          "Ce kit remplace le kit v23.1 : n'utilise plus ses fichiers, tout est ici.")
L += ["", "CONTENU", "-------",
      "Bowen28_kit_impression_v24/",
      "├── LISEZMOI.txt              ce fichier",
      "├── FICHE_IMPRESSION.pdf      la fiche à remettre à l'imprimeur : plateaux, réglages, éprouvette, aperçus",
      f"├── plateaux_3mf/             {len(plates)} fichiers 3MF (P00 à P{len(plates) - 1:02d}), pièces orientées et disposées sur le plateau de 256 mm",
      "├── plateaux_apercu/          la vue de dessus numérotée de chaque plateau (PNG)",
      "├── plateaux_apercu.png       tous les plateaux sur une planche",
      "├── eprouvette.png            l'éprouvette, montée et éclatée",
      "├── stl/                      les mêmes pièces en STL, une par fichier, rangées par couleur",
      f"│   ├── {'0_eprouvette/':20s}{len([n for n, p in pieces.items() if p['eprouvette']]):2d} fichiers, l'éprouvette de réglage (P00)"]
cnt = collections.defaultdict(lambda: [0, 0])
for n, p in pieces.items():
    if p['eprouvette']: continue
    cnt[p['color']][0] += 1; cnt[p['color']][1] += p['qty']
cols = ['blanc', 'alu', 'noir', 'teck', 'taupe']
for k, c in enumerate(cols):
    L.append(f"│   {'└' if k == len(cols) - 1 else '├'}── {DIRS[c] + '/':20s}{cnt[c][0]:2d} fichiers, {cnt[c][1]:2d} impressions")
L.append("└── notice_de_montage_v24.pdf la notice illustrée, sans colle")
L += [""]
L += wrap("« _x2 », « _x3 » ou « _x4 » à la fin d'un nom de STL = imprimer la pièce 2, 3 ou 4 fois. Les plateaux 3MF "
          "contiennent déjà le bon nombre d'exemplaires.")
L += ["", "LES PLATEAUX", "------------"]
L.append(f"{'N°':4s}{'Fichier':44s}{'Filament':34s}{'Pièces':>7s}  {'Supports':10s}{'Couches':>8s}{'Poids env.':>12s}")
for p in plates:
    fil = f"Bambu {FIL[p['color']]}"
    L.append(f"P{p['num']:02d} {p['file']:44s}{fil:34s}{len(p['inst']):7d}  {'oui' if p['sup'] else 'non':10s}"
             f"{str(p['layer']).replace('.', ',') + ' mm':>8s}{g(p['grams']):>12s}")
tot = sum(p['grams'] for p in main)
L += [""] + wrap(f"Environ {g(tot)} de PLA hors supports (le trancheur donne le chiffre exact) : blanc {g(sum(p['grams'] for p in main if p['color'] == 'blanc'))}, "
                 f"gris alu {g(sum(p['grams'] for p in main if p['color'] == 'alu'))}, noir {g(sum(p['grams'] for p in main if p['color'] == 'noir'))}, "
                 f"teck {g(sum(p['grams'] for p in main if p['color'] == 'teck'))}, taupe {g(sum(p['grams'] for p in main if p['color'] == 'taupe'))}. "
                 "Une bobine de chaque couleur suffit largement.")
L += ["", "COMMENCE PAR L'ÉPROUVETTE (P00)", "-------------------------------"]
for t_ in ["4 petites pièces blanches, environ 15 minutes, avec les mêmes réglages que le kit. Elles reprennent les 4 emboîtements "
           "de la maquette : tenon losange, clé de jonction, tenon rond de 2 mm et mini-tenon de 1,4 mm.",
           "Monte-la : bloc B contre bloc A, clé enfoncée par le dessus, plaquette C sur les 2 tenons. Bon réglage : tout entre "
           "à la main avec un léger effort et rien ne tombe quand on la retourne.",
           "Plaquette C trop dure : « Compensation X-Y des trous » à +0,05 mm ; trop lâche : −0,05 mm. Clé ou bloc B trop durs : "
           "« Compensation X-Y du contour » à −0,03 mm ; trop lâches : +0,03 mm (Bambu Studio › Qualité › Précision). Réimprime "
           "l'éprouvette, puis garde ce réglage pour tous les plateaux."]:
    L += wrap(t_, "- ", "  ")
L += ["", "POURQUOI CETTE RÉPARTITION", "--------------------------"]
for t_ in ["Une couleur par plateau : pas de changement de bobine en cours d'impression, pas d'AMS nécessaire.",
           "Les pièces qui demandent des supports sont seules sur leur plateau : P01 et P02 (les 2 moitiés de coque, "
           "232 mm de long chacune, une par plateau) et P05 (les 2 embases moteur). Tous les autres plateaux s'impriment "
           "sans aucun support.",
           "Le noir a 2 plateaux : P06 en couches de 0,08 mm (filets de coque de 0,6 mm d'épaisseur, écrans, commandes) et "
           "P07, le toit du taud seul, en 0,12 mm, imprimé à l'envers sans support (ses bords commencent par un chanfrein à 45°).",
           "Sur chaque plateau, les pièces sont rangées en rangées, centrées, à 5 mm les unes des autres et à au moins "
           "8 mm du bord du plateau."]:
    L += wrap(t_, "- ", "  ")
L += ["", "RÉGLAGES (Bambu Lab A1, plateau 256 × 256 mm)", "---------------------------------------------"]
for t_ in ["PLA ou PLA+ uniquement, buse 0,4 mm, 3 périmètres, remplissage gyroïde 15 %, plateau texturé PEI.",
           "Couches de 0,12 mm ; 0,08 mm pour le plateau noir P06.",
           "Fichiers en millimètres, à l'échelle 1:19, déjà orientés : ne pas redimensionner, ne pas tourner.",
           "Ouvrir un 3MF dans Bambu Studio : les pièces sont déjà disposées. Sur une autre imprimante, importer les STL du "
           "dossier « stl » et utiliser « Disposer ».",
           "Supports arborescents « sur le plateau uniquement » pour P01, P02 et P05 ; bordure de 5 mm pour P01 et P02. "
           "Les coques sont debout, quille en bas."]:
    L += wrap(t_, "- ", "  ")
L += ["", "LE PRINCIPE D'EMBOÎTEMENT", "-------------------------"]
for t_ in ["Un seul jeu pour tous les tenons, clés et logements : 0,1 mm par côté. Les pièces entrent à la main avec un léger "
           "effort et tiennent seules. Les fentes des coussins gardent 0,12 mm pour s'enfiler sans forcer sur les nervures.",
           "Tenons ronds (2 mm, ou 1,4 mm pour les petites pièces) quand ils s'impriment debout ; tenons en losange quand ils "
           "s'impriment couchés : leurs faces à 45° tiennent sans support, comme le toit de leur logement.",
           "Les 2 moitiés de coque : 3 tenons losange de 3 mm guident la coque avant, puis 4 clés en forme d'os s'enfoncent "
           "par le dessus et tirent les 2 faces l'une contre l'autre (2 dans les plats-bords, 2 dans le plancher).",
           "Les coussins s'enfilent sur les nervures blanches de la coque ou se posent sur des tenons : la pesanteur les tient."]:
    L += wrap(t_, "- ", "  ")
L += ["", "CE QUI CHANGE DEPUIS LA v23.1", "-----------------------------"]
for t_ in ["Plus de colle ni de goupille en filament : jonction de coque (4 clés + 3 tenons losange), moteurs (2 tenons losange "
           "par embase), manette des gaz et pompe du volant (tenons intégrés), filets noirs (mini-tenons au dos), bandes des "
           "fauteuils (emboîtées en force), dos du dossier arrière (3 mini-tenons losange).",
           "Taud : un toit rigide d'une seule pièce en PLA noir, arceaux moulés dessous, posé dans les encoches des rails. "
           "Les 4 arceaux séparés, le taud TPU en option et la toile en tissu n'existent plus.",
           "Les 2 boîtiers d'échelle sont supprimés.",
           "Filets noirs : un fichier par côté (bâbord et tribord), car leurs tenons sont au dos.",
           "Tous les logements de tenons passent de 0,15–0,2 mm de jeu à 0,1 mm ; les coussins sont recalés sur la coque "
           "(plus aucun chevauchement) et les tenons sous la banquette avant passent à 2,1 mm.",
           "Nouvelles pièces : toit du taud, 4 clés de jonction, éprouvette P00. Toutes les autres pièces gardent leur forme.",
           f"La v23.1 comptait 92 pièces (+ le taud en option) ; la v24 en compte {n_main}, sur {len(main)} plateaux, plus l'éprouvette."]:
    L += wrap(t_, "- ", "  ")
L += ["", "À PRÉVOIR POUR LE MONTAGE", "-------------------------"]
for t_ in ["Rien d'autre que les pièces imprimées : ni colle, ni goupille, ni toile.",
           "En option, la planche d'autocollants du kit v22 (immatriculation, nom, drapeau), inchangée."]:
    L += wrap(t_, "- ", "  ")
L += ["", "LES PIÈCES, PLATEAU PAR PLATEAU", "-------------------------------"]
for p in plates:
    names = []
    for i in sorted(p['inst'], key=lambda i: (-round((i['y'] + i['h'] / 2) / 26.0), i['x'] + i['w'] / 2)):
        if i['name'] not in names: names.append(i['name'])
    q = collections.Counter(i['name'] for i in p['inst'])
    L.append(f"P{p['num']:02d} – {p['title']} ({len(p['inst'])} pièce{'s' if len(p['inst']) > 1 else ''})")
    for k, n in enumerate(names, 1):
        L.append(f"   {k:2d}. {nice(n) + (f' ×{q[n]}' if q[n] > 1 else ''):48s}stl/{pieces[n]['file'].split('stl/')[-1]}")
    L.append("")
open(os.path.join(KIT, 'LISEZMOI.txt'), 'w', encoding='utf-8').write("\n".join(L) + "\n")
print("\n".join(L[:60]))
