"""Kit d'impression complet v25.3 (sans colle) : STL par couleur, plateaux equilibres (3MF), listes.
Entrees (dossier v25) : pieces.pkl (pieces reconstruites), coussins_v25.pkl, coques_v25.pkl (coques + cles), eprouvette.pkl."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, os, pickle, json, shutil, collections
sys.path.insert(0, ROOT)
import numpy as np, trimesh
import pieces as P, stl_packages as SP

HERE = ROOT + '/v25'
KIT = os.path.join(HERE, 'kit', 'Bowen28_kit_impression_v25.3')
VERSION = '24'
BED, S, GAP = 256.0, 240.0, 5.0            # plateau A1 256 x 256 ; zone de pose 240 x 240 centree (marge 8 mm)

sys.path.insert(0, ROOT + '/v25')
from noms25 import nice

from kit_inputs import load_all
A, EPR = load_all()
E = {}
for e in A:
    e.setdefault('option', False); e.setdefault('note', ''); e.setdefault('eprouvette', False)
    e['tm'] = trimesh.Trimesh(e['V'], e['F'], process=False)
    e['ext'] = e['tm'].extents.copy()
    E[e['name']] = e
assert len(E) == len(A)

SUP = {'coque_arriere', 'coque_avant', 'bloc_moteur', 'helice'}   # v25.3 : petits supports caches (moteur25.py)
COLOR_DIR = {'blanc': '1_blanc', 'alu': '2_alu', 'noir': '3_noir', 'teck': '4_teck', 'taupe': '5_taupe'}
LAYER = {'noir': 0.08}
GROUPS = [
    dict(key='eprouvette', color='blanc', title="Éprouvette de réglage : à imprimer en premier", names={e['name'] for e in EPR}, num=0),
    dict(key='coque_arriere', color='blanc', title='Coque arrière', names={'coque_arriere'}),
    dict(key='coque_avant', color='blanc', title='Coque avant', names={'coque_avant'}),
    dict(key='blanc', color='blanc', title="Capots et jupes moteur, bandes des fauteuils, clés de jonction", names=None),
    dict(key='alu', color='alu', title="Cadres du taud, berceaux, échelle, mât, flaps, taquets…", names=None),
    dict(key='embases', color='alu', title='Moteurs : blocs gris, embases, hélices, chevilles', names={'bloc_moteur', 'embase_moteur', 'helice', 'cheville_capot'}),
    dict(key='noir', color='noir', title='Filets de coque, écrans, commandes, ailerons, gaines, vérins', names=None),
    dict(key='toit', color='noir', title='Toit du taud (arceaux intégrés) et pare-battages', names={'toit_taud', 'pare_battage'}, layer=0.12),
    dict(key='teck', color='teck', title='SeaDek, tapis de plats-bords, jante et moyeu du volant', names=None),
    dict(key='taupe', color='taupe', title='Coussins, fauteuils, boudins, dos du dossier', names=None),
]
taken = set().union(*[g['names'] for g in GROUPS if g['names']])
for g in GROUPS:
    if g['names'] is None:
        g['names'] = {n for n, e in E.items() if e['color'] == g['color'] and n not in taken and not e['eprouvette']}
assert sorted(n for g in GROUPS for n in g['names']) == sorted(E), "chaque piece dans exactement un groupe"


def area(it): return it[1] * it[2]


def pack_balanced(items, n):
    """Repartit les pieces sur n plateaux en equilibrant la surface occupee (maxrects, plus grandes d'abord)."""
    pls = [dict(free=[(0.0, 0.0, S + GAP, S + GAP)], items=[], load=0.0) for _ in range(n)]
    for it in sorted(items, key=lambda t: -area(t)):
        for pl in sorted(pls, key=lambda p: p['load']):
            if P._place(pl, it):
                pl['load'] += area(it); break
        else:
            return None
    return pls


def pack_group(g):
    items = []
    for n in sorted(g['names']):
        e = E[n]
        for k in range(e['qty']):
            items.append((f"{n}#{k + 1}", e['ext'][0] + GAP, e['ext'][1] + GAP))
    n0 = len(P.maxrects_pack(items, S + GAP, S + GAP))
    for n in range(n0, n0 + 3):
        pls = pack_balanced(items, n)
        if pls: return pls
    raise RuntimeError(g['key'])


def shelf_pack(items):
    """Rangement en rangees (FFDH) : cote long a l'horizontale, plus hautes d'abord, chaque rangee centree.
    Renvoie [(id, x, y, rot)] dans la zone S x S, ou None si ca ne tient pas."""
    its = []
    for (iid, w, h) in items:
        rot = 1 if h > w + 1e-9 else 0
        its.append((iid, h, w, rot) if rot else (iid, w, h, rot))
    its.sort(key=lambda t: (-t[2], -t[1], t[0]))
    rows = []
    for it in its:
        for r in rows:
            if r['w'] + it[1] <= S + GAP + 1e-9:
                r['items'].append(it); r['w'] += it[1]; break
        else:
            rows.append(dict(items=[it], w=it[1], h=it[2]))
    H = sum(r['h'] for r in rows)
    if H > S + GAP + 1e-9: return None
    out, y = [], 0.0
    for r in rows:
        x = (S + GAP - r['w']) / 2
        for (iid, ww, hh, rot) in r['items']:
            out.append((iid, x, y + (r['h'] - hh) / 2, rot)); x += ww
        y += r['h']
    return out


def place_T(e, rot, x, y):
    """Matrice qui pose la piece orientee (coin bas ramene a l'origine) au point (x, y) du plateau, tournee de 90 deg si rot.
    Les coques gardent leurs coordonnees float32 d'origine dans le maillage : leur decalage passe dans la matrice."""
    T = np.eye(4)
    if rot:
        T[:2, :2] = [[0, -1], [1, 0]]; T[0, 3] = e['ext'][1]
    T[0, 3] += x; T[1, 3] += y
    T0 = np.eye(4); T0[:3, 3] = -e['tm'].bounds[0]
    return T @ T0


plates = []
for g in GROUPS:
    pls = pack_group(g)
    for j, pl in enumerate(pls):
        inst = []
        ids = [it[0] for it in pl['items']]
        tidy = shelf_pack([(iid, E[iid.split('#')[0]]['ext'][0] + GAP, E[iid.split('#')[0]]['ext'][1] + GAP) for iid in ids])
        pl['layout'] = 'rangées' if tidy else 'imbriqué'
        for (iid, x, y, rot) in (tidy or pl['items']):
            n, k = iid.split('#'); e = E[n]
            w, h = (e['ext'][1], e['ext'][0]) if rot else (e['ext'][0], e['ext'][1])
            inst.append(dict(name=n, k=int(k), x=x, y=y, rot=rot, w=w, h=h))
        # centrer le groupe sur le plateau de 256 mm
        x0 = min(i['x'] for i in inst); y0 = min(i['y'] for i in inst)
        x1 = max(i['x'] + i['w'] for i in inst); y1 = max(i['y'] + i['h'] for i in inst)
        dx = (BED - (x1 - x0)) / 2 - x0; dy = (BED - (y1 - y0)) / 2 - y0
        for i in inst:
            i['x'] += dx; i['y'] += dy; i['T'] = place_T(E[i['name']], i['rot'], i['x'], i['y'])
        title = g['title'] + (f" ({j + 1}/{len(pls)})" if len(pls) > 1 else '')
        plates.append(dict(key=g['key'], color=g['color'], title=title, inst=inst, option=False, eprouvette=g['key'] == 'eprouvette', layout=pl['layout'],
                           sup=any(i['name'] in SUP for i in inst), brim=any(i['name'].startswith('coque_') for i in inst),
                           layer=g.get('layer', LAYER.get(g['color'], 0.12))))

# ---- sorties
if os.path.isdir(os.path.dirname(KIT)): shutil.rmtree(os.path.dirname(KIT))
os.makedirs(KIT)
# STL par couleur
files = {}
for n, e in E.items():
    d = os.path.join(KIT, 'stl', '0_eprouvette' if e['eprouvette'] else COLOR_DIR[e['color']])
    os.makedirs(d, exist_ok=True)
    fn = n + (f"_x{e['qty']}" if e['qty'] > 1 else '') + '.stl'
    e['tm'].export(os.path.join(d, fn))
    files[n] = os.path.relpath(os.path.join(d, fn), KIT)
# 3MF par plateau
pdir = os.path.join(KIT, 'plateaux_3mf'); os.makedirs(pdir)
slug = {'eprouvette': 'eprouvette_reglage', 'coque_arriere': 'coque_arriere', 'coque_avant': 'coque_avant', 'blanc': 'blanc_moteurs_et_petites_pieces',
        'alu': 'alu_taud_berceaux', 'embases': 'alu_moteurs', 'noir': 'noir', 'toit': 'noir_toit_taud', 'teck': 'teck_seadeck', 'taupe': 'taupe_coussins'}
seen = collections.Counter()
for num, p in enumerate(plates, 0):
    p['num'] = num; seen[p['key']] += 1
    multi = sum(1 for q in plates if q['key'] == p['key']) > 1
    p['file'] = f"P{num:02d}_{slug[p['key']]}" + (f"_{seen[p['key']]}" if multi else '') + '.3mf'
    sc = trimesh.Scene()
    for i in p['inst']:
        nm = f"{i['name']}_{i['k']}"
        sc.add_geometry(E[i['name']]['tm'], node_name=nm, geom_name=nm, transform=i['T'])
    open(os.path.join(pdir, p['file']), 'wb').write(sc.export(file_type='3mf'))
    p['grams'] = sum(SP.grams(E[i['name']]['tm'], 1) for i in p['inst'])

meta = dict(version=VERSION, plates=[{k: (v if k != 'inst' else [{kk: (vv.tolist() if isinstance(vv, np.ndarray) else vv) for kk, vv in i.items()} for i in v])
                                      for k, v in p.items()} for p in plates],
            pieces={n: dict(color=e['color'], qty=e['qty'], option=False, eprouvette=e['eprouvette'], file=files[n], ext=e['ext'].tolist(), note=e.get('note', ''),
                            src=e.get('src', 'v22 (inchangée)'), grams=SP.grams(e['tm'], e['qty']), watertight=bool(e['tm'].is_watertight),
                            bodies=int(e['tm'].body_count)) for n, e in E.items()})
json.dump(meta, open(os.path.join(HERE, 'kit_meta.json'), 'w'), ensure_ascii=False, indent=1)
pickle.dump(dict(plates=plates), open(os.path.join(HERE, 'kit_plates.pkl'), 'wb'))
for p in plates:
    cnt = collections.Counter(i['name'] for i in p['inst'])
    print(f"P{p['num']:02d} {p['color']:6s} [{p['layout']}] {len(p['inst']):2d} pièces  {p['grams']:6.0f} g  sup={p['sup']} bord={p['brim']} couche={p['layer']}  {p['file']}")
    print('      ' + ', '.join(f"{nice(n)}" + (f" ×{q}" if q > 1 else '') for n, q in cnt.items()))
print('total', sum(len(p['inst']) for p in plates if not p['eprouvette']), 'impressions + éprouvette', sum(len(p['inst']) for p in plates if p['eprouvette']))
