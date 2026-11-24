"""Moteurs v25.3 (demande d'Andre du 24 novembre 2026) : la partie grise de chaque moteur en 3 pieces imprimees a
plat, sans support, au lieu d'une seule piece debout sur supports arborescents :
  1. BLOC (bloc_moteur) : bas de capot gris, ceinture et etrier, au-dessus de la plaque anti-cavitation. Imprime a
     l'envers, pose sur son plan de joint (le dessus, sous le capot). Il garde ses tenons losange (chaise, jupe) et le
     trou de la gaine ; 2 tenons ronds sous la ceinture pour l'embase ; le tenon du capot devient un logement : une
     cheville a part relie bloc et capot, qui s'impriment tous deux sur le plan de joint ;
  2. EMBASE (embase_moteur) : plaque anti-cavitation, carter, torpille et aileron de quille. Imprimee a l'envers,
     posee sur le dessus de la plaque. 2 logements pour les tenons du bloc, avec cotes d'ecrasement (elle pend sous le
     bloc : regle 2 de la ligne de conduite) ; tenon losange au bout de la torpille pour l'helice ;
  3. HELICE (helice) : moyeu et 3 pales. Imprimee debout sur l'avant du moyeu ; logement losange avec cotes
     d'ecrasement (elle tient sur un tenon horizontal : regle 2).
Repere local du moteur (m reels, comme model.py) : x depuis la face de fixation vers l'arriere, z = 0 sur la plaque
anti-cavitation ; M.place_engine le met en place.
"""
import numpy as np
from manifold3d import Manifold, OpType
import model as M
import fit as F
import fit25 as G
import emboitements as E
import pieces as P

mm = M.mm2m
MMU = mm(1.0)
TENONS_X = (0.42, 0.70)                 # 2 tenons ronds sous la ceinture, dans l'axe (y = 0)
TENON_H = mm(3.0)
HUB_X, AXE_Z = M.PROP_HUB[0], M.PROP_AX[1]   # avant du moyeu (bout de la torpille), hauteur de l'arbre
PIN_RI, PIN_L, PIN_PROF = mm(0.7), mm(3.0), mm(3.4)
CHEV_BAS, CHEV_HAUT = mm(2.5), mm(1.5)  # cheville : enfoncee dans le bloc, dans le capot


def _cote(dessus):
    return Manifold.cube([20.0, 20.0, 20.0]).translate([-10.0, -10.0, 0.0 if dessus else -20.0])


def gris_sans_helice():
    """La partie grise de model.py, sans l'helice (pour l'embase)."""
    vrai = M.build_propeller
    M.build_propeller = lambda: Manifold()
    try:
        return M.build_outboard_parts()["gris"]
    finally:
        M.build_propeller = vrai


def cheville_frame():
    """Point et axe de la cheville : l'ancien tenon du capot, sur le plan de joint, perpendiculaire a lui."""
    x = M.COWL_STUD_X
    return np.array([x, 0.0, M.plane_z(x)]), M.plane_normal()


def cheville_local():
    """Cheville ronde de diametre 2 mm, longue de CHEV_BAS + CHEV_HAUT, chanfreinee aux 2 bouts ; axe z, bas en 0."""
    L, r, t = CHEV_BAS + CHEV_HAUT, F.STUD_R, mm(0.3)
    corps = Manifold.cylinder(L - 2 * t + mm(0.04), r, r, 28).translate([0, 0, t - mm(0.02)])
    bas = Manifold.cylinder(t, r - t, r, 28)
    haut = Manifold.cylinder(t, r, r - t, 28).translate([0, 0, L - t])
    return Manifold.batch_boolean([corps, bas, haut], OpType.Add)


def pieces(capot, jupe, trou_gaine):
    """(bloc, embase, embase serree, helice, helice serree, cheville placee) en repere local du moteur ; capot et
    jupe : ceux de model.build_outboard_parts(), retires du gris comme avant."""
    gris = M.build_outboard_parts()["gris"] - capot - jupe - trou_gaine
    # 1. bloc
    bloc = gris ^ _cote(True)
    pt, nt = P.tail_stud_frame()
    bloc = bloc + G.dpeg(pt, nt, (0, 0, 1), mm(1.0), mm(1.5))                    # jupe : losange (couche)
    for zl in M.ENG_PIN_Z:                                                       # chaise : 2 tenons losange
        bloc = bloc + G.dpeg((0.0, 0.0, zl), (-1.0, 0.0, 0.0), (0, 0, 1), mm(1.0), mm(5.0))
    for x in TENONS_X:                                                           # embase : 2 tenons ronds vers le bas
        bloc = bloc + F.stud((x, 0.0, 0.0), (0.0, 0.0, -1.0), F.STUD_R, TENON_H)
    pc, nc = cheville_frame()
    bloc = bloc - F.socket(pc, -nc, F.STUD_R, CHEV_BAS)
    # 2. embase
    moyeu = Manifold.cylinder(0.60, 0.06, 0.06, 48).rotate([0, 90, 0]).translate([HUB_X, 0.0, AXE_Z])
    emb = ((gris_sans_helice() - capot - jupe - trou_gaine) ^ _cote(False)) - moyeu
    emb = emb + G.dpeg((HUB_X, 0.0, AXE_Z), (1.0, 0.0, 0.0), (0, 0, 1), PIN_RI, PIN_L)
    for x in TENONS_X:
        emb = emb - F.socket((x, 0.0, 0.0), (0.0, 0.0, -1.0), F.STUD_R, TENON_H)
    cotes = Manifold.batch_boolean([E.cotes_logement((x, 0.0, 0.0), (0.0, 0.0, -1.0), (1, 0, 0), F.STUD_R, mm(0.4),
                                                     TENON_H - mm(0.3), n=3, unite=MMU) for x in TENONS_X], OpType.Add)
    emb_s = emb + cotes
    # 3. helice
    hel = M.build_propeller() - G.dhole((HUB_X, 0.0, AXE_Z), (1.0, 0.0, 0.0), (0, 0, 1), PIN_RI, PIN_PROF)
    hel_s = hel + E.cotes_logement((HUB_X, 0.0, AXE_Z), (1.0, 0.0, 0.0), (0, 0, 1), PIN_RI, mm(0.4), PIN_PROF - mm(0.4),
                                   n=4, angle0=45.0, unite=MMU)
    # cheville a sa place : CHEV_BAS dans le bloc, CHEV_HAUT dans le capot
    z = np.array([0.0, 0.0, 1.0]); a = np.cross(z, nc); ang = np.degrees(np.arcsin(np.linalg.norm(a)))
    chev = cheville_local().rotate([0.0, ang if a[1] >= 0 else -ang, 0.0]).translate(pc - CHEV_BAS * nc)
    return bloc, emb, emb_s, hel, hel_s, chev


BAS_BLOC = tuple(M.plane_normal())      # imprime sur son plan de joint (petits supports caches : dessus de l'etrier,
                                        # sous le capot, et arriere de la ceinture, sous la jupe)
BAS_EMBASE = (0.0, 0.0, 1.0)            # sur le dessus de la plaque anti-cavitation
BAS_HELICE = (-1.0, 0.0, 0.0)           # sur l'avant du moyeu (petits supports sous le bout des pales)
