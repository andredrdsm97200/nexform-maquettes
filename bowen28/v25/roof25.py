"""Toit du taud v25 : une seule piece rigide en PLA noir, sans colle, a la place des 4 arceaux alu, de la toile
(tissu ou TPU) et de leurs clips.

  - coque de 1,2 mm qui reprend la forme de la toile v22 : dessus plat, bords qui descendent jusqu'a l'axe des
    rails, enroulement a l'arriere et a l'avant ;
  - les 4 arceaux sont moules dessous (tube + voile jusqu'a la coque) ; leurs 8 pieds carres entrent dans des
    encoches de 1,2 mm des rails (jeu 0,1 mm, 0,15 mm aux 2 arceaux extremes) ;
  - les jupes laterales s'appuient contre l'exterieur des rails : le toit ne peut pas glisser de cote ;
  - imprime a l'envers, dessus sur le plateau, SANS SUPPORT : chaque bord commence par un chanfrein a 45 deg
    puis s'arrondit jusqu'a la verticale.
"""
import numpy as np
from manifold3d import Manifold, CrossSection, OpType
import model as M

mm = M.mm2m
T = mm(1.2)                    # epaisseur de la coque
CS_ = -M.FLAT + mm(0.10)       # jupe a 0,1 mm du meplat exterieur des rails
NOTCH_D2 = mm(1.2)             # profondeur des encoches des rails (v22 : 0,6 mm)
NOTCH_C = {M.ARCH_X[0]: mm(0.15), M.ARCH_X[1]: mm(0.10), M.ARCH_X[2]: mm(0.10), M.FRONT_X: mm(0.15)}
YS = M.FRAME_Y + M.TR + CS_ + T                       # face exterieure des jupes
ZT = M.TAUD_TOP + M.TR + T                            # dessus (exterieur)
X_ARCH = tuple(M.ARCH_X) + (M.FRONT_X,)


def rad_at(x):
    t = np.clip((x - M.X_SWEEP0) / (M.FRONT_X - M.X_SWEEP0), 0, 1)
    return M.ARCH_RAD + (M.FRONT_RAD - M.ARCH_RAD) * t


def _corner(ys, zt, R, n=10):
    """Coin d'un profil : de la verticale (ys, zt - R) a 45 deg sur l'arc de rayon R, puis chanfrein a 45 deg
    jusqu'au dessus zt. Renvoie les points (y, z), du bas vers le haut."""
    cy, cz = ys - R, zt - R
    pts = [(cy + R * np.cos(a), cz + R * np.sin(a)) for a in np.linspace(0, np.pi / 4, n)]
    ay, az = pts[-1]
    pts.append((ay - (zt - az), zt))
    return pts


def station_pts(x, inner=False, bottom=1.5, t=None):
    """Profil plein (y, z), sens trigo, sous la surface exterieure (ou interieure, ou a t sous l'exterieure)
    du toit a l'abscisse x."""
    R = rad_at(x) + M.TR + CS_ + T
    d = T if t is None else t
    ys, zt = (YS - d, ZT - d) if (inner or t is not None) else (YS, ZT)
    rr = R - d if (inner or t is not None) else R
    right = [(ys, bottom)] + _corner(ys, zt, rr)
    left = [(-y, z) for (y, z) in right[::-1]]
    return M.ccw(right + left)


def station_cs(x, inner=False, bottom=1.5, t=None):
    return CrossSection([station_pts(x, inner, bottom, t)])


def xz_profile(inner=False, bottom=1.5):
    """Profil plein (x, z) : arriere enroule (rayon jusqu'au rail), avant enroule sur l'arceau avant."""
    d = T if inner else 0.0
    zt = ZT - d
    # arriere : centre (x0 + Rr, Z_RAIL) ; Rr = ZT - Z_RAIL ; exterieur a x0 = 1,54 - TR - jeu - T
    Rr = ZT - M.Z_RAIL
    x0 = M.TAUD_X[0] - M.TR - CS_ - T
    cr = (x0 + Rr, M.Z_RAIL)
    rear = [(cr[0] - (Rr - d) * np.cos(a), cr[1] + (Rr - d) * np.sin(a)) for a in np.linspace(0, np.pi / 4, 10)]
    ax, az = rear[-1]; rear.append((ax + (zt - az), zt))
    # avant : centre (FRONT_X, zf)
    zf = float(M.rail_z(M.FRONT_X)) + 0.02
    Rf = ZT - zf
    xf = M.FRONT_X + mm(0.7)                    # le bout du rail (calotte) reste a l'interieur
    front = [(xf + (Rf - d) * np.cos(a), zf + (Rf - d) * np.sin(a)) for a in np.linspace(0, np.pi / 4, 10)]
    fx, fz = front[-1]; front.append((fx - (zt - fz), zt))
    pts = [(rear[0][0], bottom)] + rear + front[::-1] + [(front[0][0], bottom)]
    return CrossSection([M.ccw(pts)])


def _loft_y(cs, xs, inner):
    secs = []
    for x in xs:
        poly = np.asarray(station_pts(x, inner))
        secs.append(np.column_stack([np.full(len(poly), x), poly]))
    m = M.loft(secs)
    assert m.volume() > 0, "loft retourne"
    return m


def shell():
    xs = np.linspace(M.TAUD_X[0] - 0.12, M.FRONT_X + 0.15, 90)
    outer = _loft_y(None, xs, False) ^ M.extrude_xz(xz_profile(False).to_polygons()[0], -2.0, 2.0)
    inner = _loft_y(None, xs, True) ^ M.extrude_xz(xz_profile(True).to_polygons()[0], -2.0, 2.0)
    m = outer - inner
    # bas des jupes : axe du rail (il remonte vers l'avant)
    xx = np.linspace(xs[0] - 0.1, xs[-1] + 0.1, 80)
    keep = [(x, float(M.rail_z(x))) for x in xx] + [(xx[-1], 4.0), (xx[0], 4.0)]
    return m ^ M.extrude_xz(M.ccw(keep), -2.0, 2.0)


def notch_bottom(xa):
    return float(M.rail_z(xa)) + M.TR - NOTCH_D2


def arch(xa, front=False):
    """Arceau moule sous le toit : tube + voile jusqu'a la coque, pieds carres plats au fond des encoches."""
    path, _ = M.arch_axis(front)
    zb = notch_bottom(xa)
    tube = M.tube_path([(xa, y, z) for (y, z) in path])
    # voile : entre l'axe de l'arceau et l'interieur du toit
    axis_poly = [(path[0][0], -1.0)] + [tuple(p) for p in path] + [(path[-1][0], -1.0)]
    web = station_cs(xa, t=T / 2) - CrossSection([M.ccw(axis_poly)])        # le voile entre a mi-epaisseur dans la coque
    webm = Manifold.extrude(web, 2 * M.TR).transform([[0, 0, 1, xa - M.TR], [1, 0, 0, 0], [0, 1, 0, 0]])
    m = (tube + webm) ^ M.box(xa - 1.0, xa + 1.0, -2.0, 2.0, zb, 9.0)
    feet = [M.box(xa - M.TR, xa + M.TR, s * M.FRAME_Y - M.TR, s * M.FRAME_Y + M.TR, zb, zb + NOTCH_D2 + mm(0.8)) for s in (1, -1)]
    return Manifold.batch_boolean([m] + feet, OpType.Add)


def build_roof():
    parts = [shell()] + [arch(x, front=(x == M.FRONT_X)) for x in X_ARCH]
    return Manifold.batch_boolean(parts, OpType.Add)


def rail_notch25(xa, side):
    c = NOTCH_C[xa]
    zt = notch_bottom(xa)
    return M.box(xa - M.TR - c, xa + M.TR + c, side * M.FRAME_Y - 0.2, side * M.FRAME_Y + 0.2, zt, zt + 0.5)


def build_frame25(side, flat=True):
    """Cadre lateral v25 : tenons des pieds +0,1 mm (logements de la coque v23 : jeu 0,2 -> 0,1 mm), encoches
    de 1,2 mm pour les pieds du toit."""
    y = side * M.FRAME_Y
    parts = [M.tube_path([(x, y, z) for (x, z) in path]) for path in M.frame_paths()]
    for i, (x, z) in enumerate(M.frame_feet()):
        r = M.tenon_r(i) + mm(0.10)
        parts.append(Manifold.cylinder(M.TR + 0.012, M.TR, M.TR, M.TUBE_SEG).translate([x, y, z]))
        parts.append(Manifold.cylinder(M.SOCK_D - mm(0.35) + 0.002, r, r, M.TUBE_SEG).translate([x, y, z - M.SOCK_D + mm(0.35)]))
        parts.append(Manifold.cylinder(mm(0.3) + 0.0005, r - mm(0.25), r, M.TUBE_SEG).translate([x, y, z - M.SOCK_D + mm(0.05)]))   # entree
    m = Manifold.batch_boolean(parts, OpType.Add)
    m = m - Manifold.batch_boolean([rail_notch25(xa, side) for xa in X_ARCH], OpType.Add)
    if flat:
        m = m.trim_by_plane([0.0, -float(side), 0.0], -(M.FRAME_Y + M.TR - M.FLAT))
    return m
