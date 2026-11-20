"""Systeme d'emboitement facon Lego, regle pour une Bambu Lab A1 (PLA, buse 0,4 mm).

Trois familles, toutes en metres reels (maquette 1:19) :
  - tenon / logement : le tenon est imprime debout sur la piece support, le logement dans le dessous
    de la piece posee (diametre 2 mm, hauteur 1,5 mm, jeu 0,15 mm, entree chanfreinee) ;
  - barrettes / fentes : les bandes blanches des coussins sont des barrettes dressees sur une semelle,
    qui traversent le coussin taupe par des fentes et affleurent dessus. La semelle se loge dans une
    empreinte de la piece support : elle positionne et tient le coussin ;
  - jeux entre pieces voisines (coussins, parois).
"""
import numpy as np
from manifold3d import Manifold, CrossSection, JoinType, OpType
import model as M

mm = M.mm2m
STUD_R, STUD_H = mm(1.0), mm(1.5)      # tenon : diametre 2 mm, hauteur 1,5 mm
STUD_TIP = mm(0.25)                    # chanfrein en tete de tenon
FIT = mm(0.15)                         # jeu radial tenon / logement
SOCK_DEPTH = STUD_H + mm(0.3)
SOCK_CHAMF = mm(0.3)
BAR_CLR = mm(0.12)                     # jeu de chaque cote barrette / fente
PLATE_T = mm(0.6)                      # semelle des barrettes
POCKET_CLR = mm(0.15)                  # jeu semelle / empreinte
POCKET_EXTRA = mm(0.05)                # l'empreinte est un peu plus profonde que la semelle
BRIDGE = mm(1.0)                       # pont de matiere au bout de chaque fente
JOINT = mm(0.3)                        # jeu entre coussins voisins, et entre coussin et paroi
STUD_S_R, STUD_S_H = mm(0.7), mm(1.0)  # v22 : mini-tenon (diametre 1,4 mm) pour les toutes petites pieces
SLOT_HALF = mm(0.25)                   # v22 : logement oblong (+/- 0,25 mm) : rattrape l'ecart d'entraxe entre 2 tenons


def U(ms):
    ms = [m for m in ms if m is not None and not m.is_empty()]
    return Manifold.batch_boolean(ms, OpType.Add) if ms else Manifold()


def frame_T(O, Uv, Vv, N):
    """Matrice 3x4 : repere local (u, v, n) -> bateau."""
    O, Uv, Vv, N = (np.asarray(a, float) for a in (O, Uv, Vv, N))
    return [[Uv[0], Vv[0], N[0], O[0]], [Uv[1], Vv[1], N[1], O[1]], [Uv[2], Vv[2], N[2], O[2]]]


def frame_Tinv(O, Uv, Vv, N):
    R = np.array([Uv, Vv, N], float)          # lignes : axes locaux
    t = -R @ np.asarray(O, float)
    return [[R[0, 0], R[0, 1], R[0, 2], t[0]], [R[1, 0], R[1, 1], R[1, 2], t[1]], [R[2, 0], R[2, 1], R[2, 2], t[2]]]


def _orient(m, p, n):
    """Oriente un solide construit selon +z : axe z -> n, origine -> p."""
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    a = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    a = a - n * (a @ n); a /= np.linalg.norm(a); b = np.cross(n, a)
    return m.transform(frame_T(p, a, b, n))


def stud(p, n=(0.0, 0.0, 1.0), r=STUD_R, h=STUD_H):
    """Tenon sur la piece support (pied enfonce de 0,3 mm), tete chanfreinee."""
    body = Manifold.cylinder(h - STUD_TIP + mm(0.3), r, r, 28).translate([0, 0, -mm(0.3)])
    tip = Manifold.cylinder(STUD_TIP + mm(0.02), r, r - STUD_TIP, 28).translate([0, 0, h - STUD_TIP - mm(0.02)])
    return _orient(body + tip, p, n)


def socket(p, n=(0.0, 0.0, 1.0), r=STUD_R, h=STUD_H):
    """Logement dans le dessous de la piece posee (n : vers l'interieur de la piece), entree chanfreinee."""
    rr = r + FIT
    hole = Manifold.cylinder(h + mm(0.3) + mm(0.05), rr, rr, 28).translate([0, 0, -mm(0.05)])
    cone = Manifold.cylinder(SOCK_CHAMF + mm(0.05), rr + SOCK_CHAMF, rr, 28).translate([0, 0, -mm(0.05)])
    return _orient(hole + cone, p, n)


def socket_slot(p, n, d, half=SLOT_HALF, r=STUD_R, h=STUD_H):
    """Logement oblong (v22) : comme socket, allonge de +/- half le long de d (perpendiculaire a n). Le 2e tenon d'une
    piece longue y entre meme si le retrait du PLA a un peu change l'entraxe entre la piece et la coque."""
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    d = np.asarray(d, float); d = d - n * (d @ n); d = d / np.linalg.norm(d)
    b = np.cross(n, d)
    rr = r + FIT
    hole = Manifold.batch_hull([Manifold.cylinder(h + mm(0.3) + mm(0.05), rr, rr, 28).translate([s * half, 0, -mm(0.05)])
                                for s in (-1, 1)])
    cone = Manifold.batch_hull([Manifold.cylinder(SOCK_CHAMF + mm(0.05), rr + SOCK_CHAMF, rr, 28).translate([s * half, 0, -mm(0.05)])
                                for s in (-1, 1)])
    return (hole + cone).transform(frame_T(p, d, b, n))


def stud_pair_sockets(pts, n, r=STUD_R, h=STUD_H):
    """Logements de plusieurs tenons d'une meme piece : le 1er rond, les autres oblongs dans l'axe du 1er."""
    pts = [np.asarray(q, float) for q in pts]
    out = [socket(pts[0], n, r, h)]
    for q in pts[1:]:
        out.append(socket_slot(q, n, q - pts[0], r=r, h=h))
    return out


def inner_points(cs, n, inset=mm(1.6)):
    """n points bien a l'interieur d'un contour allonge (le long de son grand axe)."""
    from shapely.geometry import Polygon, LineString
    cs2 = cs.offset(-inset, JoinType.Round, 2.0, 16)
    polys = [Polygon(p) for p in cs2.to_polygons() if len(p) >= 3]
    poly = max(polys, key=lambda q: q.area)
    rect = np.array(poly.minimum_rotated_rectangle.exterior.coords)[:4]
    e1, e2 = rect[1] - rect[0], rect[2] - rect[1]
    if np.linalg.norm(e1) < np.linalg.norm(e2):
        e1, e2 = e2, e1
        o = rect[1]
    else:
        o = rect[0]
    L = np.linalg.norm(e1); d = e1 / L
    c = np.array(poly.centroid.coords[0])
    nrm = np.array([-d[1], d[0]])
    pts = []
    for i in range(n):
        t = (i + 0.5) / n
        q = o + d * (t * L) + nrm * ((c - o) @ nrm)
        line = LineString([q - nrm * 50, q + nrm * 50])
        seg = poly.intersection(line)
        if seg.is_empty:
            pts.append(q); continue
        geoms = getattr(seg, "geoms", [seg])
        g = max(geoms, key=lambda s: s.length)
        a, b = np.array(g.coords[0]), np.array(g.coords[-1])
        pts.append((a + b) / 2)
    return pts


def striped(solid, bands_fn, frame, outline=None, gap=0.0, bridge=BRIDGE, plate_clip=None):
    """Coussin a bandes : renvoie (coussin taupe fendu, insert blanc, empreinte a creuser dans le support).

    solid      : coussin complet (repere bateau) ;
    bands_fn   : supplement de largeur (None = largeur nominale) -> bandes en volume (repere bateau) ;
    frame      : (O, U, V, N), plan de pose : N sort du support et traverse le coussin ;
    outline    : contour du coussin dans le plan de pose (u, v) ; par defaut, son ombre portee ;
    gap        : jeu entre le support (n = 0) et le dos du coussin, comble par le pied des barrettes ;
    plate_clip : zone (u, v) ou la semelle a le droit d'aller (par defaut : sous tout le coussin).
    """
    T, Ti = frame_T(*frame), frame_Tinv(*frame)
    if outline is None:
        outline = solid.transform(Ti).project()

    def prism(cs, n0, n1):
        return Manifold.extrude(cs, n1 - n0).translate([0, 0, n0]).transform(T)

    core = outline.offset(-bridge, JoinType.Round, 2.0, 16)
    core_g = outline.offset(-(bridge - BAR_CLR), JoinType.Round, 2.0, 16)
    base = core if plate_clip is None else core ^ plate_clip
    bands = bands_fn(None)
    root = bands ^ prism(base, -PLATE_T, gap + mm(0.05))              # pied des barrettes, sur la semelle
    bars = (solid ^ bands ^ prism(core, -1.0, 1.0)) + root
    slots = bands_fn(2 * BAR_CLR) ^ prism(core_g, -1.0, 1.0)
    cushion = solid - slots
    foot = root.transform(Ti).project()
    plate_cs = CrossSection.hull(foot).offset(mm(0.5), JoinType.Round, 2.0, 16) ^ outline.offset(-mm(0.4), JoinType.Round, 2.0, 16)
    if plate_clip is not None:
        plate_cs = plate_cs ^ plate_clip
    insert = prism(plate_cs, -PLATE_T, 0.0) + bars
    pocket = prism(plate_cs.offset(POCKET_CLR, JoinType.Round, 2.0, 16), -(PLATE_T + POCKET_EXTRA), mm(0.05))
    return cushion, insert, pocket


def studded(solid, footprint, z0, n=2, extra_points=None):
    """Coussin pose a plat sur des tenons : renvoie (coussin avec logements, tenons a unir au support)."""
    pts = extra_points if extra_points is not None else inner_points(footprint, n)
    studs = [stud((p[0], p[1], z0)) for p in pts]
    socks = [socket((p[0], p[1], z0)) for p in pts]
    return solid - U(socks), studs
