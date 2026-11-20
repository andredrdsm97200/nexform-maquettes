"""Pare-battages v25 (remarques d'Andre du 20 novembre 2026) : 4 pare-battages noirs pendus a une ficelle (non
imprimee), nouee a un anneau a l'interieur du bateau.

  - PARE-BATTAGE (noir, imprime debout, oeil en haut) : corps a bouts arrondis de 8 x 30 mm, 2 anneaux, et un oeil en
    haut pour la ficelle (trou en goutte d'eau de 1,7 mm, pointe en haut : il s'imprime sans support) ;
  - ANNEAU (blanc, dans la coque arriere) : encastre dans la paroi interieure, entre le boudin du bas et le coussin
    de plat-bord, en face de chaque pare-battage : une poche de 4 mm de large et 2,6 mm de profondeur, barree par une
    barrette au ras de la paroi ; la ficelle entre par la fente du haut, passe derriere la barrette et ressort par
    celle du bas. Rien ne depasse de la paroi : le boudin se pose toujours par le dessus (regle 1). Imprime avec la
    coque, debout : la barrette fait pont sur 4 mm, le haut de la poche est a 45 deg, sans support ;
  - places : 2 par bord, a x = 80 et 185 mm. Dans la maquette montee, le pare-battage pend contre le flanc, l'oeil
    1,5 mm sous le liston ; la ficelle passe par-dessus le plat-bord, puis sous le coussin, jusqu'a l'anneau.
  (Premiere version du meme jour, remplacee : des crochets blancs glisses sur le liston.)
Repere : visionneuse (mm, y vers le haut, z vers tribord) pour la mise en place ; le pare-battage est rendu en metres
reels, repere bateau (comme model.py), pour s1_pieces.py ; les anneaux en mm visionneuse, pour s2_coques.py.
"""
import math
import pickle
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection, OpType
import model as M

# ---- pare-battage (mm), repere local : v = axe (vers le haut), u = axe du trou de l'oeil, bas a plat en v = 0
R_PB, L_PB = 4.0, 22.0          # rayon, longueur de la partie droite (30 mm hors tout, avant le meplat)
MEPLAT = 1.3                    # le bas est coupe de 1,3 mm : il pose a plat, la suite du bas est a 45 deg
OEIL_R, OEIL_E = 2.0, 1.6       # oeil : rayon exterieur, epaisseur
TROU_R = 0.85                   # trou de l'oeil (goutte d'eau, pointe en haut)
OEIL_H = 1.6                    # centre du trou au-dessus du haut du corps
V1 = R_PB - MEPLAT + L_PB       # centre du bout haut
V_TROU = V1 + R_PB + OEIL_H     # centre du trou
H_PB = V_TROU + OEIL_R          # hauteur totale : 32,3 mm
# ---- mise en place
LISTON_H = 3.30                 # hauteur du liston (mesuree sur toute la coque)
SOUS_LISTON = 1.5               # le haut de l'oeil pend 1,5 mm sous le liston
JEU_FLANC = 0.4                 # ecart entre le pare-battage et le flanc
PLACES = [(80.0, -1), (185.0, -1), (80.0, 1), (185.0, 1)]   # (x, cote : -1 babord, +1 tribord)
# ---- anneau encastre (mm), repere local : u depuis la paroi vers le cockpit (paroi en u = 0), v vers le haut, w le long
A_PROF, A_BARRE_E = 2.6, 1.0      # profondeur de la poche ; epaisseur de la barrette, au ras de la paroi (passage : 1,6 mm)
A_LARG = 4.0                      # largeur de la poche le long de la paroi : la barrette fait pont sur 4 mm
A_FENTE, A_BARRE_H = 2.0, 1.4     # hauteur des 2 fentes (sous et sur la barrette) ; hauteur de la barrette
A_DROIT = 2 * A_FENTE + A_BARRE_H # 5,4 mm de poche droite, puis le haut a 45 deg (2,6 mm)
A_BAS = 39.3                      # bas de la poche : haut des boudins a 38,4 mm ; haut de la poche a 47,3 (coussins : 49,0)


def pare_battage_local():
    """Le pare-battage en mm, debout : axe vertical (v) en u = w = 0, bas a plat en v = 0, trou de l'oeil selon u."""
    v0 = R_PB - MEPLAT
    cyl_v = lambda h, r, v: Manifold.cylinder(h, r, r, 48).rotate([-90, 0, 0]).translate([0, v, 0])
    corps = (cyl_v(L_PB, R_PB, v0) + Manifold.sphere(R_PB, 48).translate([0, V1, 0])
             + Manifold.sphere(R_PB, 48).translate([0, v0, 0]))
    anneaux = [cyl_v(0.8, R_PB + 0.25, v) for v in (v0 + 1.2, V1 - 2.0)]
    oeil = (Manifold.cylinder(OEIL_E, OEIL_R, OEIL_R, 40).rotate([0, 90, 0]).translate([-OEIL_E / 2, V_TROU, 0])
            + Manifold.cube([OEIL_E, V_TROU - (V1 + 1.5), 2 * OEIL_R]).translate([-OEIL_E / 2, V1 + 1.5, -OEIL_R]))
    q = TROU_R / math.sqrt(2)
    goutte = (CrossSection.circle(TROU_R, 32) + CrossSection([[(q, q), (0.0, 2 * q), (-q, q), (0.0, 0.0)]])).translate([0, V_TROU])
    trou = Manifold.extrude(goutte, OEIL_E + 2.0).rotate([0, 90, 0]).translate([-(OEIL_E + 2.0) / 2, 0, 0])
    pb = Manifold.batch_boolean([corps, oeil] + anneaux, OpType.Add) - trou
    return pb.trim_by_plane([0.0, 1.0, 0.0], 0.0)


def poche_local():
    """La poche de l'anneau a retirer de la paroi, en mm (u, v depuis A_BAS, w) : elle deborde de 0,5 mm cote cockpit."""
    p = CrossSection([[(-A_PROF, 0.0), (0.5, 0.0), (0.5, A_DROIT + A_PROF + 0.5), (-A_PROF, A_DROIT)]])
    return Manifold.extrude(p, A_LARG).translate([0, 0, -A_LARG / 2])


def barrette_local():
    """La barrette, au ras de la paroi, ancree de 0,4 mm dans les 2 joues de la poche."""
    return Manifold.cube([A_BARRE_E, A_BARRE_H, A_LARG + 0.8]).translate([-A_BARRE_E, A_FENTE, -(A_LARG + 0.8) / 2])


_H = {}


def _coque():
    if 'S' not in _H:
        import os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        H = pickle.load(open(root + '/v24/coques_soudees.pkl', 'rb'))
        _H['S'] = trimesh.util.concatenate([trimesh.Trimesh(*map(np.asarray, H[k]), process=False) for k in H])
    return _H['S']


def _rayons(O, D):
    loc, idx, _ = _coque().ray.intersects_location(np.asarray(O, float), np.asarray(D, float), multiple_hits=False)
    out = np.full(len(O), np.nan); out[idx] = np.abs(loc[:, 2]); return out


def liston(x, s):
    """(dessus du plat-bord, |z| de la face du liston) a l'abscisse x (mm), cote s (-1 babord, +1 tribord)."""
    ys = np.arange(55.0, 72.0, 0.02)
    zz = _rayons([[x, y, s * 200.0] for y in ys], np.tile([0, 0, -s * 1.0], (len(ys), 1))); ok = ~np.isnan(zz)
    top = float(ys[ok].max())
    face = float(np.nanmax(zz[(ys > top - 2.5) & ok]))
    return top, face


def flanc(x, s, y_bas, y_haut):
    """Flanc exterieur sous le liston, cote s, autour de x : droite |z| = a + b y qui passe au plus pres a
    l'exterieur de la coque (3 coupes, x - 4, x, x + 4 : la largeur du pare-battage)."""
    ys = np.arange(y_bas, y_haut, 0.5)
    pts = []
    for xx in (x - R_PB, x, x + R_PB):
        zz = _rayons([[xx, y, s * 200.0] for y in ys], np.tile([0, 0, -s * 1.0], (len(ys), 1)))
        pts += [(y, z) for y, z in zip(ys, zz) if not np.isnan(z)]
    yy, zz = np.array(pts).T
    b, a = np.polyfit(yy, zz, 1)
    return a + float(np.max(zz - (a + b * yy))), b


def repere_pb(x, s):
    """Matrice 3x4 local du pare-battage (u, v, w) -> visionneuse : pendu contre le flanc, l'oeil sous le liston,
    trou de l'oeil perpendiculaire au flanc."""
    top, _ = liston(x, s)
    y_lb = top - LISTON_H                                   # bas du liston
    a, b = flanc(x, s, y_lb - H_PB - 2.0, y_lb - 0.5)
    k = math.sqrt(1 + b * b)
    D = np.array([0.0, 1.0, s * b]) / k                     # le long du flanc, vers le haut
    N = np.array([0.0, -b, s * 1.0]) / k                    # vers l'exterieur
    W = np.cross(N, D)
    d = R_PB + JEU_FLANC
    y_base = y_lb - SOUS_LISTON - H_PB * D[1]
    y_s = y_base + d * b / k
    O = np.array([x, y_s, s * (a + b * y_s)]) + d * N
    return np.c_[N, D, W, O]


def paroi(x, s, y):
    """|z| de la paroi interieure (rayon lance depuis le cockpit, a 38 mm de l'axe, vers l'exterieur)."""
    return float(_rayons([[x, y, s * 38.0]], [[0, 0, s * 1.0]])[0])


def repere_anneau(x, s):
    """Matrice 3x4 local de l'anneau (u, v, w) -> visionneuse : paroi interieure en u = 0, bas de la poche en A_BAS."""
    ym = A_BAS + (A_DROIT + A_PROF) / 2
    P1 = np.array([x - 2.0, ym, s * paroi(x - 2.0, s, ym)]); P2 = np.array([x + 2.0, ym, s * paroi(x + 2.0, s, ym)])
    T = (P2 - P1) / np.linalg.norm(P2 - P1)
    U = np.array([0.0, 1.0, 0.0])
    Nin = s * np.array([T[2], 0.0, -T[0]])                  # vers l'axe du bateau
    W = np.cross(Nin, U)
    O = np.array([x, A_BAS, s * paroi(x, s, ym)])
    return np.c_[Nin, U, W, O]


def anneaux():
    """(poches a retirer, barrettes a remettre ensuite) : les 4 anneaux en mm visionneuse, pour la coque arriere."""
    Ts = [repere_anneau(x, s) for x, s in PLACES]
    return [poche_local().transform(T) for T in Ts], [barrette_local().transform(T) for T in Ts]


V2BM = np.array([[1 / M.MM, 0, 0, 0], [0, 0, -1 / M.MM, 0], [0, 1 / M.MM, 0, 0]])   # visionneuse (mm) -> bateau (m)
LOC2M = [[1 / M.MM, 0, 0, 0], [0, 1 / M.MM, 0, 0], [0, 0, 1 / M.MM, 0]]          # mm -> m, sans tourner


def _compose(A, B):
    A4 = np.vstack([np.asarray(A, float), [0, 0, 0, 1]]); B4 = np.vstack([np.asarray(B, float), [0, 0, 0, 1]])
    return (A4 @ B4)[:3].tolist()


def pieces():
    """{nom: (liste des pieces placees, repere bateau m), piece a imprimer (m), sens 'bas' pour l'impression}."""
    p = pare_battage_local()
    Ts = [_compose(V2BM, repere_pb(x, s)) for x, s in PLACES]
    return {'pare_battage': ([p.transform(T) for T in Ts], p.transform(LOC2M), (0, -1, 0))}
