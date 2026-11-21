"""Toutes les pieces du kit v25.2 (sans colle), orientees pour l'impression : [dict(name, color, qty, V, F, note, eprouvette)]."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import os, pickle
import sys
import numpy as np, trimesh
from manifold3d import Manifold, Mesh
sys.path.insert(0, ROOT)
import pieces as P
HERE = ROOT + '/v25'


def load_all():
    A = pickle.load(open(os.path.join(HERE, 'pieces.pkl'), 'rb')) + pickle.load(open(os.path.join(HERE, 'coussins_v25.pkl'), 'rb'))
    CQ = pickle.load(open(os.path.join(HERE, 'coques_v25.pkl'), 'rb'))
    for k, (V, F) in CQ['hulls'].items():                      # debout, quille en bas : y (visionneuse) -> z
        t = P.weld(trimesh.Trimesh(np.asarray(V, np.float64), np.asarray(F), process=False))      # float32 exact, etanche
        W = np.asarray(t.vertices); W = np.c_[W[:, 0], -W[:, 2], W[:, 1]]                      # permutation exacte, sans arrondi
        A.append(dict(name=k.split('__')[1], color='blanc', qty=1, note='debout, quille en bas', V=W, F=np.asarray(t.faces)))
    for nm in ('cle_jonction_plat_bord', 'cle_jonction_fond'):
        kk = [k for k in CQ['keys'] if k['name'] == nm]
        t = kk[0]['local'].copy(); t.apply_translation(-t.bounds[0]); t = P.weld_best(t)
        A.append(dict(name=nm, color='blanc', qty=len(kk), note="debout, entrée en retrait vers le plateau", V=np.asarray(t.vertices), F=np.asarray(t.faces)))
    EPR = pickle.load(open(os.path.join(HERE, 'eprouvette.pkl'), 'rb'))
    for e in EPR:
        e['eprouvette'] = True; t = P.weld_best(trimesh.Trimesh(e['V'], e['F'], process=False)); e['V'], e['F'] = np.asarray(t.vertices), np.asarray(t.faces)
    A += EPR
    return A, EPR
