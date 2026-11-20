"""Controle final du kit v24 (sans colle) : quantites, STL et 3MF relus, couleurs, pieces supprimees, fichiers,
et aucune mention de colle ou de goupille dans les consignes (sauf pour dire qu'il n'y en a pas)."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import os, re, json, glob, pickle, collections
import numpy as np, trimesh
HERE = ROOT + '/v25'
KIT = os.path.join(HERE, 'kit', 'Bowen28_kit_impression_v24')
meta = json.load(open(os.path.join(HERE, 'kit_meta.json')))
v25 = pickle.load(open(os.path.join(HERE, 'v25b.pkl'), 'rb'))
err = []
# 1) quantites : assemblage v25 == plateaux (hors eprouvette) == suffixes des STL
asm = collections.Counter(k.split('__')[1] for k in v25)
onplates = collections.Counter(i['name'] for p in meta['plates'] if not p['eprouvette'] for i in p['inst'])
if asm != onplates: err.append(('plateaux', set(asm.items()) ^ set(onplates.items())))
stl = {}
for f in glob.glob(os.path.join(KIT, 'stl', '*', '*.stl')):
    b = os.path.basename(f)[:-4]; q = 1
    if '_x' in b and b.rsplit('_x', 1)[1].isdigit(): b, q = b.rsplit('_x', 1)[0], int(b.rsplit('_x', 1)[1])
    stl[b] = (q, f)
stl_main = {n: q for n, (q, f) in stl.items() if '0_eprouvette' not in f}
if dict(asm) != stl_main: err.append(('stl', set(asm.items()) ^ set(stl_main.items())))
# 2) chaque STL : etanche, un seul corps, pose a z = 0, dimensions = celles des plateaux
for n, (q, f) in sorted(stl.items()):
    m = trimesh.load(f)
    ok = m.is_watertight and m.body_count == 1 and abs(m.bounds[0][2]) < 1e-3 and np.allclose(m.extents, meta['pieces'][n]['ext'], atol=0.01)
    if not ok: err.append(('stl', n, m.is_watertight, m.body_count, m.bounds[0][2]))
# 3) couleur de chaque STL = couleur de la piece dans l'assemblage
col = {k.split('__')[1]: k.split('__')[0] for k in v25}
for n, (q, f) in stl.items():
    if '0_eprouvette' in f: continue
    d = os.path.basename(os.path.dirname(f)).split('_', 1)[1]
    if col[n] != d: err.append(('couleur', n, col[n], d))
# 4) 3MF : nombre d'objets, etancheite, dans le plateau de 256 mm (marge 8 mm), 5 mm entre pieces
n3 = 0
for p in meta['plates']:
    sc = trimesh.load(os.path.join(KIT, 'plateaux_3mf', p['file']))
    ms = []
    for node in sc.graph.nodes_geometry:
        T, g = sc.graph[node]; m = sc.geometry[g].copy(); m.apply_transform(T); ms.append(m)
    n3 += len(ms)
    if len(ms) != len(p['inst']): err.append(('3mf nombre', p['file']))
    for m in ms:
        if not m.is_watertight or m.bounds[0][0] < 7.9 or m.bounds[0][1] < 7.9 or m.bounds[1][0] > 248.1 or m.bounds[1][1] > 248.1 or abs(m.bounds[0][2]) > 1e-3:
            err.append(('3mf piece', p['file'], m.bounds.round(1).tolist()))
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            a, b = ms[i].bounds, ms[j].bounds
            if max(b[0][0] - a[1][0], a[0][0] - b[1][0], b[0][1] - a[1][1], a[0][1] - b[1][1]) < 4.99: err.append(('3mf ecart', p['file'], i, j))
# 5) pieces supprimees absentes
GONE = ('boitier_echelle', 'arceau_taud', 'arceau_avant_taud', 'taud_imprime_option', 'tissu_taud', 'bandes_', 'pare_brise')
for n in list(stl) + list(asm):
    if n.startswith(GONE) or n in ('filet_noir_arriere', 'filet_noir_avant', 'filet_noir_tableau'): err.append(('piece supprimee presente', n))
# 6) fichiers attendus
for f in ('LISEZMOI.txt', 'FICHE_IMPRESSION.pdf', 'plateaux_apercu.png', 'eprouvette.png'):
    if not os.path.exists(os.path.join(KIT, f)): err.append(('manque', f))
if not os.path.exists(os.path.join(KIT, 'notice_de_montage_v24.pdf')):
    print("note : notice de montage absente (la construire avec : ./construire.sh --notice)")
# 7) consignes : « colle » / « goupille » seulement pour dire qu'il n'y en a pas
import sys; sys.path.insert(0, ROOT)
import nf25_steps as S
txt = open(os.path.join(KIT, 'LISEZMOI.txt'), encoding='utf-8').read()
for st in S.STEPS:
    txt += ' '.join([st['title']] + st['todo'] + [st.get('tip') or ''] + [s['cap'] for s in (st.get('subs') or [])] + [st.get('glue') or ''])
    if st.get('glue'): err.append(('etape avec colle', st['title']))
OK = re.compile(r"(sans colle|ni colle|pas de colle|plus de colle|aucune colle|rien à coller|ni goupille|pas de goupille|ni de goupille|goupille en filament|"
                r"colle ni de goupille|sur le plateau|autocollant)", re.I)
for m in re.finditer(r"[^.\n]*\b(coll\w*|goupill\w*)[^.\n]*", txt, re.I):
    phrase = m.group(0)
    if not OK.search(phrase): err.append(('mention de colle/goupille', phrase.strip()[:120]))
print(f"pièces de la maquette : {sum(asm.values())} impressions, {len(asm)} pièces différentes ; STL : {len(stl)} fichiers ; objets 3MF : {n3}")
print('ERREURS :', err if err else 'aucune')
