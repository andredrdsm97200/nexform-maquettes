"""Echelle de bain v25 (remarque d'Andre du 20 novembre 2026, photo du bateau) : repliee et tournee de 90 degres.

En v24 l'echelle etait couchee dans l'axe du bateau (montants de l'avant vers l'arriere, charniere au bord
arriere de la plateforme). Sur le bateau, elle est repliee en 2 et ses montants sont paralleles au tableau
arriere : charniere au bord exterieur (babord) de la plateforme, elle se deplie sur le cote.

  - section du bas : 2 montants (tubes de 1,8 mm) posees sur la plateforme, 3 marches, charniere et 2 pattes ;
  - section repliee : 2 montants poses sur ceux du bas, relies par un coude a l'extremite interieure ;
  - imprimee a plat comme en v24 (meplat de 0,25 mm sous les tubes) ; les montants du haut reposent sur ceux
    du bas, les marches sont en bas : aucun pont, aucun support ;
  - 2 tenons de la plateforme sous les pattes de la charniere (les tenons v24 sont retires, la tole larmee est
    refaite sous l'ancienne et la nouvelle place de l'echelle : voir s2_coques.py).
Reperes bateau (m reels) comme model.py : x vers l'avant (0 = tableau), y vers babord, z vers le haut.
"""
import numpy as np
from manifold3d import Manifold, OpType
import model as M
import fit as F

X1, X2 = -0.50, -0.26          # montants (arriere, avant) : largeur 0,24 m
YH, YE = 0.92, 0.62            # charniere (bord exterieur babord) -> bout replie (cote moteur)
MARCHES = (0.70, 0.77, 0.84)   # marches (section du bas)
COUDE = 0.025                  # le coude du bout replie depasse de 2,5 cm vers l'interieur
TENONS = [(x, YH - 0.02) for x in (X1, X2)]
V24_TENONS = [(M.LAD2_X[0] + 0.02, y) for y in M.LAD2_Y]


def zone_v24():
    """Rectangle sans tole larmee sous l'echelle v24 (comme model.diamond_zone)."""
    return (M.LAD2_X[0] - 0.05, M.LAD2_X[1] + 0.05, M.LAD2_Y[0] - 0.05, M.LAD2_Y[1] + 0.05)


def zone_v25():
    """Rectangle sans tole larmee sous l'echelle v25 (pattes et coude compris)."""
    return (X1 - 0.05, X2 + 0.05, YE - 0.05, YH + 0.05)


def build():
    r = M.LAD_R
    zl = M.PLATF_Z + r - M.mm2m(0.25)                       # montants du bas : meplat de 0,25 mm
    zu = zl + 2 * r - M.mm2m(0.15)                           # montants replies, poses sur ceux du bas
    parts = []
    for x in (X1, X2):
        parts.append(M.tube_path([(x, YH, zl), (x, YE, zl)], r, 14))                                   # bas
        parts.append(M.tube_path([(x, YE, zu), (x, YH - 0.06, zu)], r, 14))                             # replie
        parts.append(M.tube_path([(x, YE, zl), (x, YE - COUDE, (zl + zu) / 2), (x, YE, zu)], r, 14))   # coude
        parts.append(M.box(x - 0.03, x + 0.03, YH - 0.055, YH + 0.035, M.PLATF_Z, M.PLATF_Z + M.mm2m(0.7)))   # patte
    parts.append(M.tube_path([(X1 - 0.03, YH, zl + 0.004), (X2 + 0.03, YH, zl + 0.004)], r * 1.45, 16))      # charniere
    for y in MARCHES:
        parts.append(M.box(X1, X2, y - 0.024, y + 0.024, M.PLATF_Z + 0.004, zl + 0.012))                      # marches
    m = Manifold.batch_boolean(parts, OpType.Add).trim_by_plane([0.0, 0.0, 1.0], M.PLATF_Z)
    return m - Manifold.batch_boolean([F.socket((x, y, M.PLATF_Z), (0, 0, 1), M.LAD2_PIN_R, M.LAD2_PIN_H) for x, y in TENONS],
                                      OpType.Add)


def tenons():
    return [F.stud((x, y, M.PLATF_Z), (0, 0, 1), M.LAD2_PIN_R, M.LAD2_PIN_H) for x, y in TENONS]


def tole_larmee(zone_cs):
    """Relief de tole larmee (comme model.diamond_plate) sur la grille de la v24, limite a zone_cs : la tole refaite
    sous l'ancienne et la nouvelle place de l'echelle se raccorde exactement a celle de la coque v24."""
    from manifold3d import CrossSection, JoinType
    b24 = M.diamond_zone().bounds()                          # grille de la v24 (echelle v24 dans model.py)
    o = (M.LAD2_X, M.LAD2_Y)
    M.LAD2_X, M.LAD2_Y = (X1, X2), (YE, YH)                  # zone sans tole : celle de l'echelle v25
    zone = M.diamond_zone()
    M.LAD2_X, M.LAD2_Y = o
    bump = CrossSection.square([0.018, 0.001]).translate([-0.009, -0.0005]).offset(0.0055, JoinType.Round, 2.0, 12)
    cells = []
    for i, x in enumerate(np.arange(b24[0] + M.DIAMOND_P / 2, b24[2], M.DIAMOND_P)):
        for j, y in enumerate(np.arange(b24[1] + M.DIAMOND_P / 2, b24[3], M.DIAMOND_P)):
            cells.append(bump.rotate(45 if (i + j) % 2 == 0 else -45).translate([float(x), float(y)]))
    pat = CrossSection.batch_boolean(cells, OpType.Add) ^ zone.offset(-0.012, JoinType.Round, 2.0, 12) ^ zone_cs
    return Manifold.extrude(pat, M.DIAMOND_H + 0.004).translate([0, 0, M.PLATF_Z - 0.004])
