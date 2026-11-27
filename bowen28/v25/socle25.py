"""Socle v25.4 (demande d'Andre du 25 novembre 2026) : d'un seul morceau, en noir, avec le nom du bateau et
NEXFORM 3D MARINE en relief, dans l'ecriture Nexform.

  - les 2 berceaux d'avant (memes profils, ajustes a la coque a 0,25 mm, le plus haut a l'avant) relies par une
    poutre a flancs inclines : son dessus passe 6 mm sous la quille ;
  - sur chaque flanc de la poutre, lisible de gauche a droite de chaque cote du bateau : le nom en Exo 2 Black
    italique (la police des titres Nexform, celle de la notice) et le logo Nexform 3D Marine trace du site
    (v24/nxlogo.svg) ; lettres en relief de 0,8 mm ;
  - imprime tel qu'il est pose, sur sa base : 236 x 103 mm, il prend un plateau a lui seul.
Repere bateau (m : x vers l'avant, y vers babord, z vers le haut), comme model.py.
"""
import os
import re
import numpy as np
from manifold3d import Manifold, CrossSection, FillRule, OpType
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
import model as M

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOM = "KANPAÏ 2.O"                       # nom du bateau, ecrit sur le socle
POLICE = ROOT + '/fonts/Exo2-900-italic.ttf'
LOGO = ROOT + '/v24/nxlogo.svg'
mm = M.mm2m
X_BERCEAUX = (1.05, 5.15)                # les 2 berceaux, comme en v25.3 (m)
DEMI_X = 0.19                            # demi-epaisseur d'un berceau (m)
Z_BAS = -0.50                            # dessous du socle : la table (m)
H_POUTRE = 20.0                          # hauteur de la poutre (mm) : son dessus passe 6 mm sous la quille
L_BAS, L_HAUT = 28.0, 15.0               # demi-largeurs de la poutre en bas et en haut (mm) : flancs a 33 deg
RELIEF, ANCRE = 0.8, 0.3                 # relief des lettres, et ce qu'elles entrent dans le flanc (mm)
H_NOM, H_LOGO, ECART = 12.0, 11.5, 12.0  # capitales du nom, hauteur du logo (traits de 0,8 mm au moins), ecart (mm)


class _Plume(BasePen):
    """Contours d'un glyphe en polylignes (courbes decoupees en 8)."""
    def __init__(self, gs):
        super().__init__(gs); self.polys, self.cur = [], []
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for k in range(1, 9):
            t = k / 8; a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
            self.cur.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for k in range(1, 9):
            t = k / 8; a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t ** 2
            self.cur.append((a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]))
    def _closePath(self):
        if len(self.cur) > 2: self.polys.append(self.cur)
        self.cur = []
    _endPath = _closePath


def texte(s, h_cap):
    """Le texte en mm, ligne de base en y = 0, capitales de hauteur h_cap : CrossSection (regle non nulle)."""
    f = TTFont(POLICE)
    gs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f['hmtx']
    k = h_cap / f['OS/2'].sCapHeight
    polys, x = [], 0.0
    for ch in s:
        g = cmap[ord(ch)]
        p = _Plume(gs); gs[g].draw(p)
        polys += [[(x + px * k, py * k) for px, py in poly] for poly in p.polys]
        x += hmtx[g][0] * k
    return CrossSection(polys, FillRule.NonZero)


def logo(h):
    """Le logo Nexform 3D Marine (NEXFORM et 3D MARINE) en mm, haut de h, bas en y = 0 : CrossSection (pair-impair)."""
    svg = open(LOGO).read()
    k = h / 358.0
    polys = [[(float(a) * k, (358.0 - float(b)) * k) for a, b in (q.split(',') for q in poly.strip().split())]
             for d in re.findall(r' d="([^"]+)"', svg) for poly in re.findall(r'M([^Z]+)Z', d)]
    return CrossSection(polys, FillRule.EvenOdd)


def lettrage():
    """Le nom puis le logo, en mm, centres sur l'origine (x) et sur la hauteur des capitales du nom (y)."""
    nom, lg = texte(NOM, H_NOM), logo(H_LOGO)
    (n0, _), (n1, _) = nom.bounds()[:2], nom.bounds()[2:]
    b = lg.bounds(); l0, l1, lb, lh = b[0], b[2], b[1], b[3]
    larg = (n1 - n0) + ECART + (l1 - l0)
    nom = nom.translate([-larg / 2 - n0, -H_NOM / 2])
    lg = lg.translate([-larg / 2 + (n1 - n0) + ECART - l0, -(lb + lh) / 2])
    return nom + lg, larg


def poutre():
    """La poutre qui relie les 2 berceaux, en m : trapeze (y, z) extrude le long de x, d'un bout a l'autre."""
    x0, x1 = X_BERCEAUX[0] - DEMI_X, X_BERCEAUX[1] + DEMI_X
    p = CrossSection([[(-mm(L_BAS), Z_BAS), (mm(L_BAS), Z_BAS), (mm(L_HAUT), Z_BAS + mm(H_POUTRE)), (-mm(L_HAUT), Z_BAS + mm(H_POUTRE))]])
    return Manifold.extrude(p, x1 - x0).rotate([0, 0, 0]).transform([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]])


def flanc(s):
    """Repere 3x4 (mm de texte -> m bateau) du flanc incline de la poutre, cote s (-1 tribord, +1 babord) : u le long
    du bateau, de gauche a droite pour qui regarde ce flanc ; v en montant le flanc ; w vers l'exterieur. Origine au
    milieu de la poutre, a mi-hauteur du flanc."""
    k = 1.0 / M.MM
    dy, dz = s * (L_HAUT - L_BAS), H_POUTRE
    ls = float(np.hypot(dy, dz))
    u = np.array([-s, 0.0, 0.0])
    v = np.array([0.0, dy / ls, dz / ls])
    w = np.cross(u, v)
    xm = (X_BERCEAUX[0] + X_BERCEAUX[1]) / 2
    o = np.array([xm, s * mm(L_BAS + L_HAUT) / 2, Z_BAS + mm(H_POUTRE) / 2])
    return np.c_[u * k, v * k, w * k, o], ls


def socle(hull_full):
    """Le socle d'un seul tenant, en m (repere bateau)."""
    cs, larg = lettrage()
    lettres = Manifold.extrude(cs, RELIEF + ANCRE).translate([0, 0, -ANCRE])
    assert larg < (X_BERCEAUX[1] - X_BERCEAUX[0] - 2 * DEMI_X) * M.MM - 20, 'lettrage trop long pour la poutre'
    morceaux = [M.build_cradle2(x, hull_full) for x in X_BERCEAUX] + [poutre()]
    for s in (-1, 1):
        T, ls = flanc(s)
        assert H_NOM < ls - 4 and H_LOGO < ls - 4, 'lettrage trop haut pour le flanc'
        morceaux.append(lettres.transform(T.tolist()))
    return Manifold.batch_boolean(morceaux, OpType.Add)
