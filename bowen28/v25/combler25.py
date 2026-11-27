"""v25.4 : coussins de plat-bord ajustés à la paroi (le jour entre coussin et coque se voyait d'en haut).

Constat d'André (26 novembre 2026, coque déjà imprimée) : un jour entre le coussin de plat-bord 3 et la paroi du
cockpit, des 2 côtés. La paroi est courbe en plan (le cockpit se resserre vers l'avant) alors que la face extérieure
du coussin est plane : jusqu'à 1,7 mm de jour au milieu du coussin 3, 0,3 à 0,45 mm sur les coussins 1 et 2.

On ne touche qu'aux coussins : leur face extérieure suit maintenant la paroi, au jeu de 0,1 mm (fit25.C).
  - remplissage : la silhouette du coussin vue de côté (le long de z, sens de la pose), prolongée vers la paroi ;
    le coin chanfreiné du bas, côté paroi, est rempli lui aussi ;
  - on retire la coque grossie du jeu et balayée dans le sens de la pose : le coussin glisse toujours tout droit
    vers la paroi (règle 1), autour des nervures qui le traversent ;
  - la face posée sur le plateau n'est plus plane : le coussin s'imprime debout, sur son dessous aplani de 0,4 mm
    (l'arrondi du bas, côté cockpit, reste ; plus de surplomb, aucun support). Debout, la face visible du coussin
    est imprimée en parois verticales : plus de courbes de niveau sur l'arrondi.
Repère de la visionneuse (mm, x avant, y haut, z tribord), comme coussins_v25.pkl.
"""
import numpy as np
from manifold3d import Manifold, OpType

JEU = 0.10           # jeu contre la paroi (fit25.C)
L = 2.4              # avancée maximale vers la paroi (le plus grand jour mesuré : 1,72 mm)
ARASE = 0.4          # le dessous est aplani de 0,4 mm pour poser le coussin debout


def _tris(m):
    me = m.to_mesh()
    V = np.asarray(me.vert_properties, float)[:, :3]
    F = np.asarray(me.tri_verts, np.int64)
    return V, F


def _boite_locale(rep, u, v, w):
    """Boite [u0,u1] x [v0,v1] x [w0,w1] dans le repere local (o, eu, ev, ew) -> Manifold dans le repere global."""
    o, eu, ev, ew = rep
    b = Manifold.cube([u[1] - u[0], v[1] - v[0], w[1] - w[0]]).translate([u[0], v[0], w[0]])
    T = np.c_[eu, ev, ew, o]                            # colonnes : axes locaux, puis origine
    return b.transform(T.tolist())


def repere(cu, s):
    """Repere du coussin : ew normale de la face exterieure (vers la paroi), eu le long du coussin, ev vers le haut."""
    V, F = _tris(cu)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(b - a, c - a); ar = np.linalg.norm(n, axis=1) / 2; n = n / (2 * ar[:, None] + 1e-30)
    face = (n[:, 2] * s > 0.9) & (ar > 1e-6)
    ew = (n[face] * ar[face, None]).sum(0); ew /= np.linalg.norm(ew)
    # la face exterieure plane est la plus a l'exterieur (la ou la coque a ete retranchee, le coussin est en retrait)
    g = (a + b + c) / 3
    wc = g @ ew
    face &= wc > wc[face].max() - 0.05
    ew = (n[face] * ar[face, None]).sum(0); ew /= np.linalg.norm(ew)
    P = np.unique(F[face].ravel()); Q = V[P]
    o = Q.mean(0)
    o = o + ew * ((V - o) @ ew).max()                   # sur le plan de la face, rien au-dela
    # axe long : les aretes du haut et du bas de la face exterieure (son bord, a peu pres horizontal)
    eu_h = np.cross([0.0, 1.0, 0.0], ew); eu_h /= np.linalg.norm(eu_h)
    Ff = F[face]
    E = np.sort(np.r_[Ff[:, [0, 1]], Ff[:, [1, 2]], Ff[:, [2, 0]]], axis=1)
    Eu, cnt = np.unique(E, axis=0, return_counts=True)
    B = Eu[cnt == 1]                                    # aretes du bord de la face
    d = V[B[:, 1]] - V[B[:, 0]]; ln = np.linalg.norm(d, axis=1)
    d = d / ln[:, None]; d = d * np.sign(d @ eu_h)[:, None]
    lg = np.abs(d @ eu_h) > 0.95
    eu = (d[lg] * ln[lg, None]).sum(0); eu = eu - (eu @ ew) * ew; eu /= np.linalg.norm(eu)
    ev = np.cross(ew, eu)
    if ev[1] < 0:
        eu = -eu; ev = np.cross(ew, eu)
    return (o, eu, ev, ew), V, P


def combler(cu, coque, s):
    """cu, coque : Manifold (repere visionneuse, mm) ; s = -1 a babord (paroi en z < 0), +1 a tribord.
    Rend (coussin ajuste a la paroi, repere local pour l'impression debout, infos)."""
    rep, V, P = repere(cu, s)
    o, eu, ev, ew = rep
    lv = (V - o) @ ev; lw = (V - o) @ ew
    v_cut = lv.min() + ARASE
    v_coin = lv[P].min() + 0.4                          # haut du coin chanfreine (bas de la face exterieure)
    # profondeur du coin : jusqu'a 0,1 mm de l'arrondi du bas, cote cockpit, a la hauteur de l'arasement
    tranche = cu.trim_by_plane((-ev).tolist(), float(-(o @ ev) - v_cut - 0.05)).trim_by_plane(ev.tolist(), float(o @ ev + v_cut - 0.05))
    Wt, _ = _tris(tranche)
    W = -((Wt - o) @ ew).min() - JEU
    # silhouette vue de cote (le long de z, sens de la pose), en prisme
    lo, hi = np.array(cu.bounding_box()[:3]), np.array(cu.bounding_box()[3:])
    Sz = Manifold.extrude(cu.project(), float(hi[2] - lo[2] + 2 * L + 20)).translate([0, 0, float(lo[2] - L - 10)])
    T = L + W + 0.5                                     # course a verifier : du bord du remplissage jusque dans le coussin
    G = 1000.0
    rempli = Sz ^ (_boite_locale(rep, (-G, G), (-G, G), (-0.5, L)) + _boite_locale(rep, (-G, G), (-G, v_coin), (-W, 0.0)))
    # obstacle : coque proche, grossie du jeu, balayee vers la paroi (le coussin recule tout droit vers l'axe)
    marge = np.array([0.5, 0.5, T + L + 1.0])          # la coque n'agit qu'au droit du coussin, balayee le long de z
    zone = Manifold.cube((hi - lo + 2 * marge).tolist()).translate((lo - marge).tolist())
    proche = coque ^ zone
    # (somme de Minkowski avec une boite : exacte, sans les milliers de sommets presque confondus de copies decalees)
    z0, z1 = sorted([-s * JEU, s * T])
    interdit = proche.minkowski_sum(Manifold.cube([2 * JEU, 2 * JEU, z1 - z0]).translate([-JEU, -JEU, z0]))
    neuf = cu + (rempli - interdit)
    neuf = neuf.trim_by_plane(ev.tolist(), float(o @ ev + v_cut))          # dessous plan, pour l'impression debout
    morceaux = sorted(neuf.decompose(), key=lambda q: -q.volume())
    neuf = morceaux[0].simplify(0.002)                  # retire les aretes de moins de 2 microns laissees par les booleens
    infos = dict(ajoute=neuf.volume() - cu.volume(), morceaux=len(morceaux), v_cut=v_cut, W=W,
                 ecartes=[round(q.volume(), 3) for q in morceaux[1:]])
    return neuf, rep, v_cut, infos


def debout(m, rep, v_cut):
    """Matrice 3x4 qui pose le coussin debout sur son dessous aplani : X le long du coussin, Z vers le haut."""
    o, eu, ev, ew = rep
    R = np.array([eu, -ew, ev])                         # X = eu, Y = -ew, Z = ev (repere direct)
    t = -R @ o - np.array([0, 0, v_cut])
    return np.c_[R, t]
