# -*- coding: utf-8 -*-
"""Emboitements communs a toutes les maquettes Nexform (voir LIGNE_DE_CONDUITE.md, regle 2).

Regle 2 - une petite piece ne tombe pas toute seule. Une piece qui ne tient pas par son propre poids (accrochee
a une paroi, debout sur un seul tenon, penchee) recoit des COTES D'ECRASEMENT sur son emboitement : de fines
nervures (0,7 mm de large) paralleles au sens de la pose, qui depassent du jeu standard et s'ecrasent un peu
quand on enfonce la piece. Elle tient alors par serrage, quels que soient l'imprimante et le filament, sans colle.

  - toujours du cote de la PETITE piece (sur son tenon, dans son logement, sur les flancs de sa semelle) :
    si le serrage ne convient pas, on ne reimprime qu'elle ;
  - serrage SERRAGE (0,15 mm) pour un tenon de 2 mm et plus, SERRAGE_MINI (0,08 mm) pour un mini-tenon ;
  - les cotes commencent apres l'entree du logement (le tenon s'engage d'abord sans forcer) ;
  - elles ne vont que sur la piece imprimee, pas dans la maquette assemblee (elle reste au jeu standard,
    sans chevauchement) : le controle de maintien verifie qu'elles touchent bien la piece d'en face.

Unites : celles de la piece (le Bowen travaille en metres reels : passer des longueurs converties, ex. M.mm2m(0.35)).
"""
import math
import numpy as np
from manifold3d import Manifold, OpType

RAYON = 0.35          # mm : rayon d'une cote (0,7 mm de large : environ 2 passes de buse de 0,4 mm)
SERRAGE = 0.15        # mm : la cote s'enfonce de 0,15 mm dans la piece d'en face (tenon de 2 mm et plus)
SERRAGE_MINI = 0.08   # mm : mini-tenon (1,4 mm)


def repere(p, d, up):
    """Matrice 3x4 : repere local (x = up, y = cote, z = d) -> piece."""
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    u = np.asarray(up, float); u = u - d * (u @ d); u = u / np.linalg.norm(u)
    s = np.cross(d, u)
    p = np.asarray(p, float)
    return [[u[0], s[0], d[0], p[0]], [u[1], s[1], d[1], p[1]], [u[2], s[2], d[2], p[2]]]


def cotes(p, d, up, distance, angles_deg, debut, fin, rayon, segments=16):
    """Cotes cylindriques paralleles a d : axe a 'distance' de l'axe (p, d), aux angles donnes (0 = direction up),
    de 'debut' a 'fin' le long de d. Renvoie un Manifold (a unir a la piece)."""
    T = repere(p, d, up)
    out = []
    for a in angles_deg:
        t = math.radians(a)
        c = Manifold.cylinder(fin - debut, rayon, rayon, segments).translate([distance * math.cos(t), distance * math.sin(t), debut])
        out.append(c.transform(T))
    return Manifold.batch_boolean(out, OpType.Add)


def cotes_logement(p, d, up, r_tenon, debut, fin, n=3, serrage=None, rayon=None, angle0=0.0, unite=1.0):
    """Cotes dans un logement rond (ou losange : r_tenon = rayon inscrit, n=4, angle0=45) : leur bord interieur
    descend a r_tenon - serrage. p, d : entree et sens du logement ; debut, fin : le long de d."""
    serrage = (SERRAGE if serrage is None else serrage) * unite
    rayon = (RAYON if rayon is None else rayon) * unite
    return cotes(p, d, up, r_tenon - serrage + rayon, [angle0 + k * 360.0 / n for k in range(n)], debut, fin, rayon)


def cotes_tenon(p, d, up, r_logement, debut, fin, n=3, serrage=None, rayon=None, angle0=0.0, angles=None, unite=1.0):
    """Cotes sur un tenon rond (ou losange : r_logement = rayon inscrit du logement, n=4, angle0=45) : leur bord
    exterieur monte a r_logement + serrage. p, d : pied et sens du tenon ; debut, fin : le long de d."""
    serrage = (SERRAGE if serrage is None else serrage) * unite
    rayon = (RAYON if rayon is None else rayon) * unite
    ang = angles if angles is not None else [angle0 + k * 360.0 / n for k in range(n)]
    return cotes(p, d, up, r_logement + serrage - rayon, ang, debut, fin, rayon)


def cote_flanc(p, d, normale, paroi, debut, fin, serrage=None, rayon=None, unite=1.0):
    """Une cote sur un flanc plat (semelle dans son empreinte) : p sur l'axe de la piece, normale vers la paroi,
    'paroi' = distance de l'axe a la paroi d'en face ; le bord de la cote va a paroi + serrage."""
    serrage = (SERRAGE if serrage is None else serrage) * unite
    rayon = (RAYON if rayon is None else rayon) * unite
    return cotes(p, d, normale, paroi + serrage - rayon, [0.0], debut, fin, rayon)
