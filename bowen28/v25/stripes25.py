"""Filets noirs v25 : sans colle. Chaque filet porte des mini-tenons ronds (1,4 mm) au dos, qui entrent dans des
mini-logements au fond de la rainure de la coque. Les filets sont imprimes a plat, face visible sur le plateau,
tenons vers le haut : il faut donc un fichier par cote (babord / tribord sont symetriques)."""
import numpy as np
from manifold3d import Manifold, CrossSection, OpType
import model as M
import fit as F

mm = M.mm2m
XS0, XS1, GAP = mm(0.6), M.STRIPE_SPLIT, mm(0.1)
SEGS = {'arriere': (XS0, XS1 - GAP), 'avant': (XS1 + GAP, M.STRIPE_X_END)}
STUD_X = {'arriere': (0.25, 0.80, 1.35, 1.90, 2.45, 3.00, 3.55), 'avant': (4.05, 4.60, 5.15, 5.70, 6.25, 6.75)}
TR_Y = (0.70, 0.93)                                   # tenons de la bande du tableau (y bateau)
IN = M.STRIPE_DEPTH - mm(0.02)                        # face interieure du filet sous la surface de la coque


def frame_at(x, side=1):
    _, P, nrm, up, w = M.stripe_frames(x - 0.01, x + 0.01, 3)[1]
    return np.array([P[0], side * P[1], P[2]]), np.array([nrm[0], side * nrm[1], nrm[2]])


def tr_point(y, side=1):
    z0 = M.stripe_low(0.0)
    return np.array([0.0, side * y, z0 + M.STRIPE_BAND / 2])


def hull_stud_points():
    """[(x, point au fond de la rainure, direction vers l'interieur de la coque)] des 2 flancs et du tableau."""
    out = []
    for s in (1, -1):
        for seg in ('arriere', 'avant'):
            for x in STUD_X[seg]:
                P, n = frame_at(x, s)
                out.append((x, P - M.STRIPE_DEPTH * n, -n))
        for y in TR_Y:
            p = tr_point(y, s); out.append((0.0, p + np.array([M.STRIPE_DEPTH, 0, 0]), np.array([1.0, 0, 0])))
    return out


def _stud(p, d):
    return F.stud(p, d, F.STUD_S_R, F.STUD_S_H)


def side_asm(seg, side):
    xa, xb = SEGS[seg]
    m = M.stripe_inlay_side(xa, xb, side)
    studs = []
    for x in STUD_X[seg]:
        P, n = frame_at(x, side)
        studs.append(_stud(P - IN * n, -n))
    return Manifold.batch_boolean([m] + studs, OpType.Add)


def side_flat(seg, side):
    """Filet deplie (meme calcul que model.stripe_inlay_flat) + tenons sur la face du dessus (cote coque) ;
    face visible en z = 0. Tribord = symetrique de babord."""
    xa, xb = SEGS[seg]
    fr = M.stripe_frames(xa, xb, 240)
    P = np.array([f[1] for f in fr]); ds = np.linalg.norm(np.diff(P, axis=0), axis=1)
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    dT = np.gradient(T, axis=0)
    s = np.r_[0, np.cumsum(ds)]
    ds_c = np.gradient(s)
    kg = np.array([(dT[i] @ fr[i][3]) / ds_c[i] for i in range(len(fr))])
    th = np.r_[0, np.cumsum(0.5 * (kg[1:] + kg[:-1]) * ds)]
    c = np.stack([np.r_[0, np.cumsum(np.cos(th[:-1]) * ds)], np.r_[0, np.cumsum(np.sin(th[:-1]) * ds)]], 1)
    nrm2 = np.stack([-np.sin(th), np.cos(th)], 1)
    w = np.array([f[4] for f in fr])
    poly = np.vstack([c - nrm2 * (w / 2)[:, None], (c + nrm2 * (w / 2)[:, None])[::-1]])
    m = Manifold.extrude(CrossSection([M.ccw(poly)]), M.STRIPE_T)
    xs = np.array([f[0] for f in fr])
    studs = [_stud((float(np.interp(x, xs, c[:, 0])), float(np.interp(x, xs, c[:, 1])), M.STRIPE_T), (0, 0, 1)) for x in STUD_X[seg]]
    m = Manifold.batch_boolean([m] + studs, OpType.Add)
    return m if side > 0 else m.mirror([0, 1, 0])


def transom_asm(side):
    m = M.stripe_inlay_transom(side)
    studs = [_stud(tr_point(y, side) + np.array([IN, 0, 0]), (1, 0, 0)) for y in TR_Y]
    return Manifold.batch_boolean([m] + studs, OpType.Add)
