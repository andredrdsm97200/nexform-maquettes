"""Rendus de la notice facon Lego : etapes, sous-etapes, vignettes des pieces. Met tout en cache dans nf/img."""
import os as _os
ROOT = _os.path.dirname(_os.path.abspath(__file__))          # dossier bowen28 du depot
import sys, json, os
sys.path.insert(0, ROOT)
import numpy as np, trimesh
import guide as Gd, pieces as P
from raster import render
from nf25_steps import STEPS, BG, PANEL
OFFS = json.load(open(ROOT + '/donnees/eclate.json'))          # vue eclatee de la notice (mm, repere visionneuse)
import pickle
V23 = pickle.load(open(ROOT + '/v25/v25b.pkl', 'rb'))
conv = lambda v: np.c_[v[:, 0], -v[:, 2], v[:, 1]]
data = []
def offs(n):
    """Eclate de la v23 ; pieces nouvelles de la v24 : filets par cote, cles et toit."""
    col, name, k = n.split('__')
    if n in OFFS: return OFFS[n]
    for seg in ('arriere', 'avant', 'tableau'):
        for j, sd in enumerate(('babord', 'tribord')):
            if name == f'filet_noir_{seg}_{sd}': return OFFS.get(f'noir__filet_noir_{seg}__{j}', [0, 0, 0])
    if name.startswith('cle_jonction'): return [0, 26, 0]
    if name == 'toit_taud': return OFFS.get('toile__tissu_taud__0', [0, 70, 0])
    return [0, 0, 0]
for n, (V, F) in V23.items():
    col, name, k = n.split('__'); ex = np.array(offs(n), float)
    if name in ('pare_battage', 'crochet_pare_battage'):          # v25.1 : ecartes du flanc tribord (vue de l'etape 12) ;
        tri = np.asarray(V)[:, 2].mean() > 0                     # a babord, caches par la coque : sur place, sans fleche
        ex = np.array([0.0, -9.0, 10.0] if name == 'pare_battage' else [0.0, 5.0, 7.0]) if tri else np.zeros(3)
    data.append((name, col, int(k), trimesh.Trimesh(conv(np.asarray(V, float)), F, process=False), (ex[0], -ex[2], ex[1])))
IMG = ROOT + '/nf25/img/'
counts = {}
for d in data: counts[d[0]] = counts.get(d[0], 0) + 1
json.dump(counts, open(IMG + 'counts.json', 'w'))
couleurs = {}
for d in data: couleurs[d[1]] = couleurs.get(d[1], 0) + 1
json.dump(couleurs, open(IMG + 'couleurs.json', 'w'))           # pieces par couleur (page « Avant de commencer »)
def lit(eye, target):
    v = np.asarray(eye, float) - np.asarray(target, float); v /= np.linalg.norm(v)
    side = np.cross(v, [0, 0, 1.0]); side /= np.linalg.norm(side)
    L = 0.75 * v + 0.35 * side + np.array([0, 0, 0.75]); return tuple(L / np.linalg.norm(L))
def step_img(path, parts, done, cam, k, W, H, vif=False, fleches=()):
    if os.path.exists(path): return
    st = dict(parts=parts, cam=dict(cam, light=lit(cam['eye'], cam['target'])), k=k, vif=vif, fleches=fleches)
    # fond du panneau : on remplace le blanc par la couleur du panneau en rendant puis en recollant
    im = Gd.render_step(data, P.rgb_of, st, done, W=W, H=H, ss=2)
    im.save(path); print(os.path.basename(path), flush=True)
def thumb(path, name):
    if os.path.exists(path): return
    ms = [(tm, P.rgb_of(c)) for (n, c, k, tm, ex) in data if n == name and k == 0]
    tm = ms[0][0]; lo, hi = tm.bounds; c = (lo + hi) / 2; r = np.linalg.norm(hi - lo) / 2
    d = np.array([0.62, -0.62, 0.48]); d /= np.linalg.norm(d)
    dist = r / np.tan(np.radians(11)) * 1.08
    im = render(ms, eye=tuple(c + d * dist), target=tuple(c), fov=22, W=200, H=200, ss=2, bg=PANEL, light=lit(tuple(c + d * dist), tuple(c)))
    im.save(path); print(os.path.basename(path), flush=True)
allp = [(tm, P.rgb_of(c)) for (n, c, k, tm, ex) in data]
if not os.path.exists(IMG + 'cover.png'):
    render(allp, eye=(610, -470, 300), target=(175, 0, 50), fov=27, W=1500, H=900, ss=2, bg=(18, 20, 24), light=lit((610, -470, 300), (175, 0, 50))).save(IMG + 'cover.png')
if not os.path.exists(IMG + 'fin.png'):
    render(allp, eye=(-330, -520, 260), target=(175, 0, 50), fov=30, W=1500, H=900, ss=2, bg=(149, 250, 5), light=lit((-330, -520, 260), (175, 0, 50))).save(IMG + 'fin.png')
done = set()
for si, st in enumerate(STEPS):
    g = Gd.STEPS[si] if si < len(Gd.STEPS) else {}                # v25 : etape 12 (pare-battages) sans equivalent v23
    cam = st.get('cam') or g.get('cam'); k = st.get('k', g.get('k', 1.0))   # etape 12 : cameras dans les sous-etapes
    if st.get('subs'):
        for j, sub in enumerate(st['subs']):
            step_img(f"{IMG}s{si+1:02d}_{j+1}.png", sub['parts'], set(done), sub.get('cam', cam), sub.get('k', k),
                     sub.get('W', 900), sub.get('H', 640), sub.get('vif', False), sub.get('fleches', ()))
            done |= set(sub['parts'])
    else:
        step_img(f"{IMG}s{si+1:02d}.png", st['parts'], set(done), cam, k, 1300, 900)
        done |= set(st['parts'])
    for n in st['parts']: thumb(f"{IMG}t_{n}.png", n)
assert done == set(counts), set(counts) ^ done
print("rendus ok")
