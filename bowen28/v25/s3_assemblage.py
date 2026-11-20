"""Assemblage v25 (repere visionneuse, mm) : coques v25 + 4 cles + pieces v25 + coussins v23 ; controle des
interferences (toute piece contre les coques et contre ses voisines). Sortie : v25b.pkl au format de v23b.pkl."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, pickle, itertools
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/v25')
import numpy as np
from manifold3d import Manifold, Mesh, OpType

HERE = ROOT + '/v25'
V23 = pickle.load(open(ROOT + '/v23/v23b.pkl', 'rb'))
CQ = pickle.load(open(f'{HERE}/coques_v25.pkl', 'rb'))
PC = pickle.load(open(f'{HERE}/pieces.pkl', 'rb'))
asm = {}
for k, vf in CQ['hulls'].items(): asm[k] = vf
cnt = {}
for kk in CQ['keys']:
    i = cnt.get(kk['name'], 0); cnt[kk['name']] = i + 1
    asm[f"blanc__{kk['name']}__{i}"] = (np.asarray(kk['asm'].vertices, np.float32), np.asarray(kk['asm'].faces, np.int64))
for e in PC:
    for i, (V, F) in enumerate(e['asm']):
        asm[f"{e['color']}__{e['name']}__{i}"] = (V, F)
for e in pickle.load(open(f'{HERE}/coussins_v25.pkl', 'rb')):
    asm[f"taupe__{e['name']}__0"] = e['asm'][0]
pickle.dump(asm, open(f'{HERE}/v25b.pkl', 'wb'))
print('assemblage v25 :', len(asm), 'impressions')


def man(V, F): return Manifold(Mesh(np.asarray(V, np.float32), np.asarray(F, np.uint32)))


M_ = {k: man(*vf) for k, vf in asm.items()}
hulls = [k for k in M_ if '__coque_' in k]
bad = []
# 1) chaque piece contre les 2 coques
for k, m in M_.items():
    if k in hulls: continue
    for h in hulls:
        v = (m ^ M_[h]).volume()
        if v > 0.02: bad.append((k, h, round(v, 3)))
# 2) pieces voisines entre elles (boites englobantes qui se touchent)
keys = [k for k in M_ if k not in hulls]
bb = {k: np.array(M_[k].bounding_box()) for k in keys}
for a, b in itertools.combinations(keys, 2):
    A, B = bb[a], bb[b]
    if np.any(A[3:] < B[:3] - 0.01) or np.any(B[3:] < A[:3] - 0.01): continue
    v = (M_[a] ^ M_[b]).volume()
    if v > 0.02: bad.append((a, b, round(v, 3)))
print('interferences > 0,02 mm3 :', len(bad))
for x in sorted(bad, key=lambda t: -t[2]): print('  ', x)
