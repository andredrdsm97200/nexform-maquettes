"""Coussins v25 : les 20 coussins v23 (assemblage v23b), recales sur les coques v25.
Chaque coussin perd la matiere qui chevauchait la coque (nervures, parois : jusqu'a 0,7 mm sur les coussins de
plat-bord) : la coque est retranchee du coussin, qui l'epouse exactement a ces endroits. Les fentes sur les
nervures gardent leur jeu de 0,12 mm ; sous la banquette avant, les tenons de la coque sont passes a 2,1 mm.
L'orientation d'impression est celle du kit v23.1 (retrouvee parmi les 24 rotations a angle droit)."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, pickle, itertools
sys.path.insert(0, ROOT)
import numpy as np, trimesh
from manifold3d import Manifold, Mesh, OpType
from scipy.spatial import cKDTree
import pieces as P

HERE = ROOT + '/v25'
V23 = pickle.load(open(ROOT + '/v23/v23b.pkl', 'rb'))
CQ = pickle.load(open(f'{HERE}/coques_v25.pkl', 'rb'))['hulls']
OLD = {e['name']: e for e in pickle.load(open(ROOT + '/v24/coque_coussins.pkl', 'rb')) if e['name'].startswith('coussin_')}


def man(V, F): return Manifold(Mesh(np.asarray(V, np.float32), np.asarray(F, np.uint32)))
def tm_of(m):
    me = m.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)


hull = man(*CQ['blanc__coque_arriere__0']) + man(*CQ['blanc__coque_avant__0'])
c = 0.10
dirs = [np.eye(3)[i] * s for i in range(3) for s in (1, -1)] + [np.array(v) / np.sqrt(3) for v in itertools.product((1, -1), repeat=3)]
ROTS = []
for perm in itertools.permutations(range(3)):
    for sg in itertools.product((1, -1), repeat=3):
        R = np.zeros((3, 3))
        for i, j in enumerate(perm): R[i, j] = sg[i]
        if np.linalg.det(R) > 0: ROTS.append(R)
out = []
for k in sorted(V23):
    if not k.startswith('taupe__coussin_'): continue
    name = k.split('__')[1]
    cu = man(*V23[k])
    reg = [q for q in (hull ^ cu).decompose() if q.volume() > 1e-4]                    # chevauchements reels seulement
    if reg:                                           # on retire exactement la coque : la ou ca chevauchait, le coussin
        new = max((cu - hull).decompose(), key=lambda q: q.volume())          # epouse la coque (jeu 0), ailleurs 0,12 mm
    else:
        new = cu
    rest = new ^ hull
    # orientation d'impression v23.1 : reperes d'inertie (4 jeux de signes) puis plus proche voisin
    old = OLD[name]; Vp = np.asarray(old['V']); tree = cKDTree(Vp)
    A_ = trimesh.Trimesh(*V23[k], process=False); B_ = trimesh.Trimesh(old['V'], old['F'], process=False)
    ca, cb = A_.center_mass, B_.center_mass
    ea, eb = A_.principal_inertia_vectors, B_.principal_inertia_vectors
    best = None
    for sg in itertools.product((1, -1), repeat=3):
        R = eb.T @ np.diag(sg) @ ea
        if np.linalg.det(R) < 0: continue
        W = (np.asarray(V23[k][0], float) - ca) @ R.T + cb
        d = tree.query(W[::5])[0].mean()
        if best is None or d < best[0]: best = (d, R)
    assert best[0] < 0.05, (name, best[0])
    R = best[1]
    t = tm_of(new)
    Tm = np.c_[R, cb - R @ ca]
    pm = new.transform(Tm.tolist()); lo = np.array(pm.bounding_box()[:3]); pm = pm.translate(list(-lo))
    tp = P.weld_best(tm_of(pm))                    # soudure float32 apres la derniere transformation (STL)
    out.append(dict(name=name, color='taupe', qty=1, src=old.get('src', ''), V=np.asarray(tp.vertices), F=np.asarray(tp.faces),
                    watertight=bool(tp.is_watertight), bodies=int(tp.body_count), vol_print=float(tp.volume),
                    asm=[(np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.int64))]))
    print(f"{name:34s} retire {cu.volume() - new.volume():6.2f} mm3 ; reste contre la coque {rest.volume():.4f} ; "
          f"etanche {tp.is_watertight} corps {tp.body_count} ; orientation v23.1 (ecart {best[0]:.4f} mm)")
pickle.dump(out, open(f'{HERE}/coussins_v25.pkl', 'wb'))
