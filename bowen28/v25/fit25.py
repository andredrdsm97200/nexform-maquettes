"""Emboitements v25 : maquette montee SANS COLLE, uniquement en PLA / PLA+ (regle pour une Bambu Lab A1, buse 0,4 mm).

Une seule logique pour tout l'assemblage, un seul jeu : 0,1 mm par cote.
  - tenon rond (diametre 2 mm, mini 1,4 mm) quand il s'imprime debout, dans un logement de 2,2 mm (1,6 mm) ;
  - tenon losange (cercle inscrit de 2 mm, ou 1,4 / 3 mm) quand il s'imprime couche : ses faces a 45 degres
    tiennent sans support, comme le toit de son logement losange ;
  - cle de jonction en forme d'os (2 tetes rondes + col) pour les 2 moities de coque : elle tire les 2 faces
    l'une contre l'autre ; on l'enfonce par le dessus ;
  - nervure / fente des coussins (inchangees, la pesanteur les tient) ;
  - piece que son poids ne tient pas (ecrans, manette, interrupteurs, pompe, barre de console) : cotes d'ecrasement
    en plus, cote petite piece (../../commun/emboitements.py, ajoutees dans s1_pieces.py ; LIGNE_DE_CONDUITE.md, regle 2).
Les logements deja perces dans la coque v23 (jeu 0,15 ou 0,2 mm) sont gardes : ce sont les tenons des pieces
qui y entrent qui grossissent, pour retrouver 0,1 mm.
"""
import numpy as np
from manifold3d import Manifold, CrossSection, OpType
import model as M
import fit as F

mm = M.mm2m
C = 0.10                          # jeu standard, mm (par cote / radial)
F.FIT = mm(C)                     # tous les logements ronds reconstruits : 0,1 mm (au lieu de 0,15)
OLD_FIT = mm(0.15)                # logements ronds deja dans la coque v23
OLD_CLR = mm(0.20)                # percages M.CLR deja dans la coque v23
STUD_R_HULL = F.STUD_R + OLD_FIT - mm(C)       # tenon (piece) qui entre dans un logement de la coque : 2,1 mm


def U(ms):
    ms = [m for m in ms if m is not None and not m.is_empty()]
    return Manifold.batch_boolean(ms, OpType.Add) if ms else Manifold()


def diamond_cs(ri):
    """Losange (carre a 45 deg) de cercle inscrit ri ; sommets sur +-X (le haut a l'impression) et +-Y."""
    a = ri * np.sqrt(2.0)
    return CrossSection([[(a, 0.0), (0.0, a), (-a, 0.0), (0.0, -a)]])


def _frame(p, d, up):
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    u = np.asarray(up, float); u = u - d * (u @ d); u = u / np.linalg.norm(u)
    s = np.cross(d, u)
    return F.frame_T(np.asarray(p, float), u, s, d)


def diamond_peg(p, d, up, ri, L, embed, tip):
    """Tenon losange qui sort de la piece en p selon d (L : longueur hors piece), sommet vers 'up'."""
    cs = diamond_cs(ri)
    e = tip * 0.05                                    # recouvrement : la tete fait corps avec le tenon
    body = Manifold.extrude(cs, L - tip + embed).translate([0, 0, -embed])
    head = Manifold.extrude(cs, tip + e, 0, 0.0, (0.6, 0.6)).translate([0, 0, L - tip - e])
    return (body + head).transform(_frame(p, d, up))


def diamond_hole(p, d, up, ri, depth, flare):
    """Logement losange : entree en p (evasee de 'flare'), s'enfonce de depth selon d."""
    e = flare * 0.2
    body = Manifold.extrude(diamond_cs(ri), depth + e).translate([0, 0, -e])
    k = ri / (ri + flare)
    cone = Manifold.extrude(diamond_cs(ri + flare), flare + e, 0, 0.0, (k, k)).translate([0, 0, -e])
    return (body + cone).transform(_frame(p, d, up))


# ---- tailles en metres (repere bateau, comme model.py)
def dpeg(p, d, up=(0, 0, 1), ri=mm(1.0), L=mm(4.0)):
    return diamond_peg(p, d, up, ri, L, mm(0.3), mm(0.4))


def dhole(p, d, up=(0, 0, 1), ri=mm(1.0), depth=mm(4.4)):
    return diamond_hole(p, d, up, ri + mm(C), depth, mm(0.25))


def dogbone_cs(a, R, w, n=48):
    """Profil en os : 2 tetes de rayon R en +-a, col de demi-largeur w."""
    heads = CrossSection.circle(R, n).translate([-a, 0.0]) + CrossSection.circle(R, n).translate([a, 0.0])
    return heads + CrossSection.square([2 * a, 2 * w]).translate([-a, -w])
