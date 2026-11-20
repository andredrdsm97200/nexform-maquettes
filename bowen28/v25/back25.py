"""Dos taupe du dossier arriere v25 : sans colle. 3 mini-tenons losange (cercle inscrit 1,4 mm) sur sa face
interieure entrent dans 3 logements losange du dossier blanc (la peau s'imprime debout : tenons couches)."""
import numpy as np
from manifold3d import Manifold, OpType
import model as M
import fit25 as G

mm = M.mm2m
GAP = mm(0.02)                      # jeu peau / dossier (model.build_back_skin)
RI, L, DEPTH = mm(0.7), mm(1.8), mm(2.1)
Y_PEGS = (-0.66, -0.32, 0.02)        # le long de la partie droite du dossier (y bateau)


def peg_frames():
    bp = M.back_path()
    d = np.gradient(bp, axis=0); d /= np.linalg.norm(d, axis=1)[:, None]
    n_in = np.stack([d[:, 1], -d[:, 0]], 1)
    z = (M.BACK_SKIN_Z0 + M.BACK_HI[2]) / 2 - mm(0.6)
    out = []
    for y in Y_PEGS:
        i = int(np.argmin(np.abs(bp[:30, 1] - y)))
        nn = np.array([n_in[i, 0], n_in[i, 1], 0.0])
        p = np.array([bp[i, 0], bp[i, 1], z]) + (-0.03 - GAP) * nn
        out.append((p, nn))
    return out


def build():
    skin = M.build_back_skin()
    pegs = [G.dpeg(p, d, (0, 0, 1), RI, L) for (p, d) in peg_frames()]
    return Manifold.batch_boolean([skin] + pegs, OpType.Add)
