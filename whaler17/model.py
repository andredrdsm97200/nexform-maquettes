"""Maquette Boston Whaler 17 Montauk (coque classique 1976-2002) + Suzuki DF90A.

Cotes en metres reels. Axes : x vers l'avant (0 = tableau arriere), y vers babord, z vers le haut (0 = quille au tableau).
Sources des cotes : constructeur (longueur 16 ft 7 in = 5,05 m, largeur 6 ft 2 in = 1,88 m, tableau 20 in) ;
le reste est releve sur les 7 photos du client.
"""
import json, base64, os
import numpy as np
import trimesh
from manifold3d import Manifold, Mesh, CrossSection

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorties")
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ helpers
def mesh_to_manifold(V, F):
    tm = trimesh.Trimesh(V, F, process=False)
    if tm.volume < 0:
        F = F[:, ::-1]
    m = Manifold(Mesh(vert_properties=np.asarray(V, np.float32), tri_verts=np.asarray(F, np.uint32)))
    assert m.status().name == "NoError", m.status()
    assert not m.is_empty()
    return m

def loft(sections, close=False):
    """Loft de sections fermees (meme nb de points). close=True : boucle (pas de bouchons)."""
    S, N = len(sections), len(sections[0])
    V = np.concatenate([np.asarray(s, float) for s in sections])
    F = []
    rng = range(S) if close else range(S - 1)
    for i in rng:
        i2 = (i + 1) % S
        for j in range(N):
            a, b = i * N + j, i * N + (j + 1) % N
            c, d = i2 * N + (j + 1) % N, i2 * N + j
            F += [[a, b, c], [a, c, d]]
    if not close:
        c0, c1 = len(V), len(V) + 1
        V = np.vstack([V, np.mean(sections[0], axis=0), np.mean(sections[-1], axis=0)])
        base = (S - 1) * N
        for j in range(N):
            F.append([c0, (j + 1) % N, j])
            F.append([c1, base + j, base + (j + 1) % N])
    return mesh_to_manifold(V, np.array(F))

def ccw(poly):
    p = np.asarray(poly, float)
    area = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    return p if area > 0 else p[::-1]

def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])

def extrude_xz(poly_xz, y0, y1):
    """Extrude un profil (x,z) entre y0 et y1."""
    m = Manifold.extrude(CrossSection([ccw(poly_xz)]), y1 - y0).rotate([90, 0, 0])
    return m.translate([0, y1, 0])

def extrude_xy(poly_xy, z0, z1):
    return Manifold.extrude(CrossSection([ccw(poly_xy)]), z1 - z0).translate([0, 0, z0])

def extrude_yz(poly_yz, x0, x1):
    """Extrude un profil (y,z) entre x0 et x1."""
    m = Manifold.extrude(CrossSection([ccw(poly_yz)]), x1 - x0)   # (Y,Z) dans XY du profil, epaisseur en Z
    m = m.rotate([0, 0, 0])
    # (u,v,w) -> (x=w, y=u, z=v)
    V = np.array(m.to_mesh().vert_properties)[:, :3]; F = np.array(m.to_mesh().tri_verts)
    V2 = np.stack([V[:, 2] + x0, V[:, 0], V[:, 1]], 1)
    return mesh_to_manifold(V2, F)

def cyl(p0, p1, r0, r1=None, seg=24):
    """Cylindre (ou cone) entre deux points."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0; h = float(np.linalg.norm(d))
    m = Manifold.cylinder(h, r0, r0 if r1 is None else r1, seg)
    z = np.array([0, 0, 1.0]); u = d / h
    v = np.cross(z, u); s = np.linalg.norm(v); c = float(np.dot(z, u))
    if s < 1e-9:
        R = np.eye(3) if c > 0 else np.diag([1, -1, -1.0])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        R = np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)
    M = np.hstack([R, p0[:, None]])
    return m.transform(M)

def sphere(c, r, seg=24):
    return Manifold.sphere(r, seg).translate(list(c))

def tube(path, r, seg=14):
    """Tube de section circulaire le long d'une polyligne (mains courantes, volant)."""
    P = np.asarray(path, float); n = len(P)
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    ref = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    secs = []
    N0 = np.cross(T[0], ref); N0 /= np.linalg.norm(N0)
    Nn = N0
    for i in range(n):
        Nn = Nn - np.dot(Nn, T[i]) * T[i]; Nn /= np.linalg.norm(Nn)
        B = np.cross(T[i], Nn)
        a = np.linspace(0, 2 * np.pi, seg, endpoint=False)
        secs.append(P[i] + r * (np.cos(a)[:, None] * Nn + np.sin(a)[:, None] * B))
    return loft(secs)

def rounded_rect(cx, cy, a, b, r, N=8):
    """Rectangle arrondi (demi-cotes a, b ; rayon r)."""
    r = min(r, a * 0.999, b * 0.999); pts = []
    for (sx, sy, a0) in [(1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)]:
        ox, oy = cx + sx * (a - r), cy + sy * (b - r)
        for t in np.linspace(np.radians(a0), np.radians(a0 + 90), N):
            pts.append((ox + r * np.cos(t), oy + r * np.sin(t)))
    return np.array(pts)

def cushion(x0, x1, y0, y1, z0, z1, r=0.035):
    """Coussin : pave a aretes arrondies (arrondi dans le plan, chanfrein en haut)."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; a, b = (x1 - x0) / 2, (y1 - y0) / 2
    base = extrude_xy(rounded_rect(cx, cy, a, b, r), z0, z1 - r * 0.6)
    top = extrude_xy(rounded_rect(cx, cy, a - r * 0.45, b - r * 0.45, r * 0.7), z1 - r * 0.62, z1)
    return base + top

# ------------------------------------------------------------------ coque (Whaler 17 classique, carene « cathedrale »)
# v2 (retours du BAT v1) : etrave plus pleine en « U » vue de dessus, bouchain et quille qui remontent en courbe continue
# depuis le tiers avant jusqu'en haut de l'etrave (profil epure), plage avant agrandie.
from scipy.interpolate import PchipInterpolator

L = 5.05          # longueur hors tout de la coque (constructeur : 16 ft 7 in)
BMAX = 0.94       # demi-largeur max (constructeur : 6 ft 2 in)
GUN = 0.11        # largeur du plat-bord
FLOOR = 0.30      # plancher du cockpit
T_TR = 0.06       # epaisseur du tableau
X_PL = 3.72       # arete arriere de la plage avant (marche vers le cockpit avant)
X_PL_RAMP = 4.35  # la plage remonte ensuite en pente douce...
X_PL_END = 4.80   # ...jusqu'au pont d'etrave (taquets, feu)
PL_REC = 0.28     # retrait de la plage sous le plat-bord (photo « poste » : plage ~20 cm au-dessus du plancher avant)

X_TAPER = 3.6     # la largeur maxi est conservee jusqu'ici, puis etrave pleine en « U » (rectangle a coins arrondis)

def ys(x):
    """Demi-largeur au livet : 0,86 au tableau, 0,94 de 1,7 m a 3,6 m, puis etrave tres pleine (photo « avant » : liston presque droit
    sur l'avant, coins arrondis) : superellipse d'exposants 4 / 3,6."""
    x = np.asarray(x, float)
    aft = 0.86 + 0.08 * np.sin(np.pi / 2 * np.clip(x / 1.7, 0, 1))
    t = np.clip((x - X_TAPER) / (L - X_TAPER), 0, 1)
    fwd = BMAX * np.clip(1 - t ** 4.0, 0, 1) ** (1 / 3.6)
    return np.maximum(np.where(x <= X_TAPER, aft, fwd), 0.012)

def zs(x):
    """Livet : 0,76 a l'arriere (tableau 20 in + 10 in), tonture qui remonte de 15 cm vers l'etrave."""
    u = np.clip(np.asarray(x, float), 0, L) / L
    return 0.76 + 0.15 * u ** 2.3

CH_X0 = 2.90      # debut de la remontee des fonds (2,15 m de l'etrave), d'apres le trace bleu du client
# bouchain (arete basse du flanc) en fonction de la distance a l'etrave (m) -> hauteur (m), releve sur le trace bleu
_CH_FB = np.array([2.40, 2.15, 1.90, 1.60, 1.30, 1.00, 0.70, 0.45, 0.25, 0.10, 0.0])
_CH_Z = np.array([0.120, 0.120, 0.140, 0.205, 0.275, 0.355, 0.450, 0.545, 0.635, 0.700, 0.725])
_CH = PchipInterpolator((L - _CH_FB), _CH_Z)

def zc(x):
    """Bouchain : 0,12 m a l'arriere, puis courbe continue jusqu'a 0,725 m au pied d'etrave (19 cm sous le livet)."""
    x = np.clip(np.asarray(x, float), L - 2.40, L)
    return _CH(x)

def zk(x):
    """Quille : 12 cm sous le bouchain a l'arriere, 5 cm seulement a l'etrave (avant degage, « coupe epuree »)."""
    s = np.clip((np.asarray(x, float) - CH_X0) / (L - CH_X0), 0, 1)
    return zc(x) - (0.12 - 0.07 * s)

def chain(x):
    """Demi-section (y, z) de la quille au livet : quille centrale, tunnel, sponson exterieur (carene « cathedrale »), bouchain, flanc.
    Vers l'avant, les fonds se resserrent et remontent : pied d'etrave haut, pont large en « U »."""
    B = float(ys(x)); H = float(zs(x)); c = float(zc(x)); k = float(zk(x)); h = c - k
    u = float(np.clip((x - CH_X0) / (L - CH_X0), 0, 1))
    g = 1 - 0.12 * u ** 1.5          # fonds presque aussi larges que le pont jusqu'a l'etrave (avant « cathedrale »)
    yc = 0.87 * B * g
    return [(0.0, k), (0.14 * B * g, k + 0.42 * h), (0.30 * B * g, k + h), (0.46 * B * g, k + h), (0.66 * B * g, k + 0.29 * h),
            (0.80 * B * g, k + 0.62 * h), (yc, c), (yc + 0.62 * (B - yc), c + 0.45 * (H - c)), (B, H)]

def y_out(x, z):
    """Demi-largeur exterieure de la coque a la hauteur z (partie flanc, ou z croit avec y)."""
    ch = chain(x)[5:]
    zz = np.array([p[1] for p in ch]); yy = np.array([p[0] for p in ch])
    return float(np.interp(z, zz, yy))

def hull_section(x):
    ch = chain(x)
    star = [(x, y, z) for (y, z) in ch]
    port = [(x, -y, z) for (y, z) in ch[1:]][::-1]
    return np.array(star + port)

def zbot(x, y):
    ch = chain(x); yy = np.maximum.accumulate(np.array([p[0] for p in ch])); zz = np.array([p[1] for p in ch])
    return float(np.interp(abs(y), yy, zz)) if abs(y) < yy[-1] else float(zs(x))

def w_ck(x):
    return float(ys(x)) - GUN

LINER = 0.13      # retrait du contre-moule au niveau du plancher

def zfloor(x):
    """Plancher : au-dessus du fond sur toute sa largeur, et assez haut pour que le flanc reste epais (il remonte vers l'avant)."""
    wf = w_ck(x) - LINER
    zf = max(FLOOR, max(zbot(x, y) for y in np.linspace(0, wf, 25)) + 0.06)
    while y_out(x, zf) < wf + 0.05 and zf < float(zs(x)) - 0.1:
        zf += 0.005
    return zf

def hull_shell():
    xs = np.unique(np.concatenate([np.linspace(0, X_TAPER, 34), X_TAPER + (L - X_TAPER) * (1 - (1 - np.linspace(0, 1, 70)) ** 1.7)]))
    return loft([hull_section(x) for x in xs])

def liner_half(x, zf, slope=LINER, d=0.10, na=7):
    """Demi-profil (y, z) du contre-moule a l'abscisse x : conge au plancher zf, flanc incline jusqu'au plat-bord."""
    w = w_ck(x); zt = float(zs(x)) + 0.03; wf = w - slope
    a = np.arctan2(zt - zf, w - wf)
    A = np.array([wf - d, zf]); K = np.array([wf, zf]); Bp = np.array([wf + d * np.cos(a), zf + d * np.sin(a)])
    right = [(1 - t) ** 2 * A + 2 * (1 - t) * t * K + t * t * Bp for t in np.linspace(0, 1, na)]
    return right + [np.array([w, zt])]

def cockpit_cutter(slope=LINER, d=0.10, na=7):
    """Volume du cockpit : contre-moule a flancs inclines (plus etroit au plancher), raccorde au plancher par un conge.
    Il s'arrete a la marche de la plage avant (X_PL)."""
    xs = np.linspace(T_TR, X_PL, 80); secs = []
    for x in xs:
        right = liner_half(x, zfloor(x), slope, d, na) + [np.array([w_ck(x), 3.0])]
        left = [np.array([-p_[0], p_[1]]) for p_ in right[::-1]]
        secs.append([(x, p_[0], p_[1]) for p_ in right + left])
    return loft(secs)

def pl_rec(x):
    """Retrait de la plage avant sous le plat-bord : constant, puis la plage remonte en pente douce jusqu'au pont d'etrave."""
    s = float(np.clip((x - X_PL_RAMP) / (X_PL_END - X_PL_RAMP), 0, 1))
    return PL_REC * 0.5 * (1 + np.cos(np.pi * s)) - 0.012 * s

def z_plage(x):
    return float(zs(x)) - pl_rec(x)

def plage_cutter(slope=0.26, d=0.14, na=7):
    """Plage avant (« petite plage » du client) : surface plate en retrait sous le plat-bord, bords releves en pente douce,
    de la marche X_PL jusqu'au pont d'etrave."""
    xs = np.linspace(X_PL - 0.004, X_PL_END, 48); secs = []
    for x in xs:
        right = liner_half(x, z_plage(x), slope, d, na) + [np.array([w_ck(x), 3.0])]
        left = [np.array([-p_[0], p_[1]]) for p_ in right[::-1]]
        secs.append([(x, p_[0], p_[1]) for p_ in right + left])
    return loft(secs)

def sheer_path(n=180):
    """Contour du livet vu de dessus : tribord tableau -> etrave -> babord tableau (+ normales exterieures)."""
    xs = np.concatenate([np.linspace(0, X_TAPER, 34), X_TAPER + (L - X_TAPER) * (1 - (1 - np.linspace(0, 1, n // 2)) ** 1.7)])
    xs = np.unique(xs)
    side = [(x, -float(ys(x)), float(zs(x))) for x in xs]
    P = np.array(side + [(x, -y, z) for (x, y, z) in side[::-1]][1:])
    P[len(side) - 1, 1] = 0.0
    return P

def rub_rail(t=0.034, h=0.06, inset=0.02):
    P = sheer_path(); secs = []
    T = np.gradient(P[:, :2], axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    N = np.stack([-T[:, 1], T[:, 0]], 1)            # normale dans le plan (x, y)
    c = P[:, :2].mean(0)
    for i, p in enumerate(P):
        n = N[i] if np.dot(N[i], p[:2] - [c[0], 0]) > 0 or True else -N[i]
        if np.dot(n, p[:2] - np.array([L * 0.45, 0])) < 0:
            n = -n
        a = p[:2] - n * inset; b = p[:2] + n * t
        secs.append([(a[0], a[1], p[2] - h), (b[0], b[1], p[2] - h), (b[0], b[1], p[2] + 0.006), (a[0], a[1], p[2] + 0.006)])
    return loft(secs)

def hull():
    shell = hull_shell() - cockpit_cutter() - plage_cutter()
    shell = shell - box(-0.2, T_TR + 0.01, -0.34, 0.34, 0.508, 2.0)          # echancrure du tableau (moteur 20 in)
    return shell

# ------------------------------------------------------------------ amenagement
def grab_rail(x0, x1, y, z0, h=0.075, r=0.011, rc=0.035):
    """Main courante inox : deux pieds et une barre, coins arrondis (le long de x)."""
    pts = [(x0, y, z0 - 0.01), (x0, y, z0 + h - rc)]
    for a in np.linspace(np.pi, np.pi / 2, 7)[1:]:
        pts.append((x0 + rc + rc * np.cos(a), y, z0 + h - rc + rc * np.sin(a)))
    for a in np.linspace(np.pi / 2, 0, 7)[1:]:
        pts.append((x1 - rc + rc * np.cos(a), y, z0 + h - rc + rc * np.sin(a)))
    pts.append((x1, y, z0 - 0.01))
    P = np.array(pts); P2 = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(np.linalg.norm(b - a) / 0.02))
        for t in np.linspace(0, 1, n + 1)[1:]:
            P2.append(a + (b - a) * t)
    return tube(np.array(P2), r)

def cleat(x, y, z, ang=0.0, l=0.16):
    """Taquet : barre arquee sur deux pieds, oriente selon ang (rad) dans le plan."""
    c, s_ = np.cos(ang), np.sin(ang); pts = []
    for t in np.linspace(-1, 1, 15):
        u = t * l / 2; hgt = 0.035 + 0.012 * (1 - t * t)
        pts.append((x + c * u, y + s_ * u, z + hgt))
    bar = tube(np.array(pts), 0.008)
    feet = cyl((x - c * l * 0.22, y - s_ * l * 0.22, z - 0.005), (x - c * l * 0.22, y - s_ * l * 0.22, z + 0.045), 0.012) + \
           cyl((x + c * l * 0.22, y + s_ * l * 0.22, z - 0.005), (x + c * l * 0.22, y + s_ * l * 0.22, z + 0.045), 0.012)
    return bar + feet

def cushion2(x0, x1, y0, y1, z0, z1, rp=0.045, re=0.032, rb=0.010, pitch=0.06, gw=0.007, gd=0.004, piping=True):
    """Coussin capitonne (retour client) : coins arrondis en plan (rp), aretes du dessus en quart de rond (re), arete basse
    adoucie (rb), coutures en rainures sur toute la longueur du dessus (sens du grand cote, pas « pitch ») et couture de
    passepoil sur le pourtour, juste sous l'arrondi."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; a, b = (x1 - x0) / 2, (y1 - y0) / 2
    prof = [(rb * (1 - np.sin(t)), z0 + rb * (1 - np.cos(t))) for t in np.linspace(0, np.pi / 2, 5)]
    prof += [(re * (1 - np.cos(t)), z1 - re + re * np.sin(t)) for t in np.linspace(0, np.pi / 2, 9)]
    m = loft([[(px, py, z) for (px, py) in rounded_rect(cx, cy, a - ins, b - ins, rp - ins, N=8)] for ins, z in prof])
    cuts = None
    along_y = (y1 - y0) >= (x1 - x0)
    span = (x1 - x0) if along_y else (y1 - y0)
    n = max(1, int((span - 2 * re) / pitch) + 1)
    for i in range(n):
        o = (i - (n - 1) / 2) * pitch
        g = box(cx + o - gw / 2, cx + o + gw / 2, y0 + re * 0.45, y1 - re * 0.45, z1 - gd, z1 + 0.02) if along_y else \
            box(x0 + re * 0.45, x1 - re * 0.45, cy + o - gw / 2, cy + o + gw / 2, z1 - gd, z1 + 0.02)
        cuts = g if cuts is None else cuts + g
    zp = z1 - re - 0.004
    if piping and zp - gw > z0 + rb:
        outer = extrude_xy(rounded_rect(cx, cy, a + 0.01, b + 0.01, rp + 0.01), zp - gw / 2, zp + gw / 2)
        inner = extrude_xy(rounded_rect(cx, cy, a - gd, b - gd, rp - gd), zp - gw / 2 - 0.001, zp + gw / 2 + 0.001)
        cuts = cuts + (outer - inner)
    return m - cuts

def bench(xa, xb, half, seat_z=0.64, end_w=0.10, end_top=0.82, with_post=True):
    """Banquette moulee : assise creme + caissons d'extremite plus hauts, coussin capitonne blanc, poteau central inox."""
    plank = box(xa, xb, -half + end_w, half - end_w, seat_z, seat_z + 0.05)
    prof = [(xa, FLOOR), (xb, FLOOR), (xb, end_top - 0.03), (xb - 0.04, end_top), (xa + 0.04, end_top), (xa, end_top - 0.03)]
    ends = extrude_xz(prof, half - end_w, half) + extrude_xz(prof, -half, -half + end_w)
    frame = plank + ends
    cush = cushion2(xa + 0.01, xb - 0.01, -half + end_w + 0.005, half - end_w - 0.005, seat_z + 0.05, seat_z + 0.13)
    post = cyl(((xa + xb) / 2, 0, FLOOR), ((xa + xb) / 2, 0, seat_z), 0.018) if with_post else None
    rails = grab_rail(xa + 0.07, xb - 0.07, half - end_w / 2, end_top) + grab_rail(xa + 0.07, xb - 0.07, -half + end_w / 2, end_top)
    return frame, cush, post, rails

# console (retour client) : calee contre le bord tribord, sur les 3/4 de la largeur, passage a babord pour y acceder.
CON_X0, CON_X1, CON_H = 1.85, 2.35, 1.10
CON_YP = 0.37                   # face babord de la console ; le contre-moule tribord borde l'autre cote
CON_GAP = 0.004                 # jeu contre le contre-moule (pieces imprimees separement)
DASH_Z0, DASH_DX = 0.62, 0.17   # tableau de bord incline : de z = 0,62 jusqu'au dessus, recule de 17 cm (photos « detail » et 3/4 arriere)
WHEEL_Y = -0.10                 # volant au tiers babord de la console (photos « detail » et 3/4 arriere)

def console_section(x):
    """Profil (y, z) de la console : face babord droite, face tribord qui epouse le contre-moule puis le plat-bord."""
    zf = zfloor(x); lh = liner_half(x, zf); w = w_ck(x); H = float(zs(x)); zt = lh[-1][1]; zb = zf - 0.02
    p_hi, p_lo = lh[-1], lh[-2]
    y_h = p_hi[0] - (zt - H) * (p_hi[0] - p_lo[0]) / (zt - p_lo[1])
    st = [(-(w - CON_GAP), CON_H), (-(y_h - CON_GAP), H)]
    st += [(-(p[0] - CON_GAP), p[1]) for p in lh[-2::-1]]
    st.append((st[-1][0], zb))
    return [(CON_YP, zb), (CON_YP, CON_H)] + st

def dash_x(z):
    """Abscisse du tableau de bord incline a la hauteur z."""
    return CON_X0 + DASH_DX * float(np.clip((z - DASH_Z0) / (CON_H - DASH_Z0), 0, 1))

def dash_frame():
    phi = np.arctan2(DASH_DX, CON_H - DASH_Z0)
    n = np.array([-np.cos(phi), 0, np.sin(phi)]); v = np.array([np.sin(phi), 0, np.cos(phi)]); u = np.array([0, 1.0, 0])
    return n, u, v

def on_dash(y, z, off=0.0):
    n, _, _ = dash_frame()
    return np.array([dash_x(z), y, z]) + n * off

def torus(c, n, u, v, R, r, N=96, M=16):
    """Tore (jante) de centre c, d'axe n, dans le plan (u, v)."""
    secs = []
    for t in np.linspace(0, 2 * np.pi, N, endpoint=False):
        e = np.cos(t) * u + np.sin(t) * v
        secs.append([c + (R + r * np.cos(s)) * e + r * np.sin(s) * n for s in np.linspace(0, 2 * np.pi, M, endpoint=False)])
    return loft(secs, close=True)

def console():
    """Console d'apres les photos « poste », « detail » et 3/4 arriere, et le retour client sur le BAT v1."""
    xm = (CON_X0 + CON_X1) / 2; zb = zfloor(xm) - 0.02
    body = extrude_yz(console_section(xm), CON_X0, CON_X1)
    k = DASH_DX / (CON_H - DASH_Z0)
    side = [(CON_X0, zb - 0.1), (CON_X1 + 0.1, zb - 0.1), (CON_X1 + 0.1, CON_H + 0.3), (CON_X0 + DASH_DX + 0.3 * k, CON_H + 0.3), (CON_X0, DASH_Z0)]
    body = body ^ extrude_xz(side, -1.3, 1.3)
    body = body ^ extrude_xy(rounded_rect(xm, (CON_YP - 1.3) / 2, (CON_X1 - CON_X0) / 2, (CON_YP + 1.3) / 2, 0.06), zb - 0.2, CON_H + 0.5)

    n, u, v = dash_frame()
    base = on_dash(WHEEL_Y, 0.875); H = base + n * 0.12
    rim = torus(H, n, u, v, 0.172, 0.0135)
    grips = None                                   # petits creux sur l'interieur de la jante pour la prise en main
    for t in np.radians(np.arange(0, 360, 12.0)):
        if min(abs(((np.degrees(t) - sa + 180) % 360) - 180) for sa in (-90, 30, 150)) < 14:
            continue
        e = np.cos(t) * u + np.sin(t) * v
        g = sphere(H + (0.172 - 0.0135 * 0.95) * e, 0.0075, 14)
        grips = g if grips is None else grips + g
    rim = rim - grips
    spokes = None
    for sa in (-90, 30, 150):
        t = np.radians(sa); e = np.cos(t) * u + np.sin(t) * v
        sp = cyl(H + n * 0.004, H + 0.165 * e, 0.011)
        spokes = sp if spokes is None else spokes + sp
    wheel = rim + spokes + cyl(H - n * 0.01, H + n * 0.012, 0.03)
    hub = cyl(base - n * 0.03, H - n * 0.008, 0.052, 0.034, 28) + cyl(H + n * 0.008, H + n * 0.04, 0.034, 0.028, 28)

    xc = CON_X0 + DASH_DX + 0.09
    comp = (sphere((xc, WHEEL_Y + 0.04, CON_H), 0.06, 28) ^ box(xc - 0.1, xc + 0.1, WHEEL_Y - 0.1, WHEEL_Y + 0.2, CON_H, CON_H + 0.2)) + \
           cyl((xc, WHEEL_Y + 0.04, CON_H - 0.005), (xc, WHEEL_Y + 0.04, CON_H + 0.012), 0.068)

    def dial(y, z, r):
        p = on_dash(y, z)
        return cyl(p - n * 0.01, p + n * 0.016, r, r, 32)
    inst = dial(WHEEL_Y - 0.46, 0.985, 0.048) + dial(WHEEL_Y - 0.44, 0.855, 0.032)
    pb = on_dash(WHEEL_Y - 0.61, 1.035)                            # petit tableau d'interrupteurs noir, en haut a droite
    inst = inst + extrude_xy(rounded_rect(pb[0] - 0.01, pb[1], 0.02, 0.06, 0.008), 1.005, 1.065)
    p0 = on_dash(WHEEL_Y + 0.31, 0.745)                            # tableau de 4 interrupteurs a gauche du volant
    plate = None
    for i in range(4):
        q = on_dash(WHEEL_Y + 0.25 + i * 0.04, 0.745, 0.012)
        sw = box(q[0] - 0.012, q[0] + 0.012, q[1] - 0.012, q[1] + 0.012, q[2] - 0.028, q[2] + 0.028)
        plate = sw if plate is None else plate + sw
    pl = box(p0[0] - 0.012, p0[0] + 0.03, p0[1] - 0.11, p0[1] + 0.05, 0.69, 0.80)
    for dy in (0.0, 0.06):                                          # deux prises sous les interrupteurs
        pl = pl + cyl((CON_X0 + 0.01, WHEEL_Y + 0.26 + dy, 0.575), (CON_X0 - 0.018, WHEEL_Y + 0.26 + dy, 0.575), 0.018)
    inst = inst + pl + plate

    yt = WHEEL_Y - 0.30                                             # commande moteur laterale, manette en T
    thr = extrude_xy(rounded_rect(CON_X0 - 0.01, yt, 0.06, 0.055, 0.02), 0.55, 0.72)
    lever = cyl((CON_X0 - 0.035, yt, 0.70), (CON_X0 - 0.07, yt, 0.92), 0.012)
    grip = cyl((CON_X0 - 0.072, yt - 0.075, 0.935), (CON_X0 - 0.072, yt + 0.075, 0.935), 0.019, 0.019, 24) + \
           sphere((CON_X0 - 0.072, yt - 0.075, 0.935), 0.019, 20) + sphere((CON_X0 - 0.072, yt + 0.075, 0.935), 0.019, 20)
    neck = cyl((CON_X0 - 0.07, yt, 0.90), (CON_X0 - 0.072, yt, 0.935), 0.016)
    throttle = thr + lever + neck + grip

    rods = None                                                     # trois porte-cannes sur le flanc babord de la console
    for dx in (0.08, 0.18, 0.28):
        x = CON_X0 + dx
        t_ = cyl((x, CON_YP + 0.03, 0.50), (x, CON_YP + 0.03, 0.86), 0.026) - cyl((x, CON_YP + 0.03, 0.56), (x, CON_YP + 0.03, 0.90), 0.020)
        rods = t_ if rods is None else rods + t_
    rods = rods + box(CON_X0 + 0.05, CON_X0 + 0.31, CON_YP - 0.01, CON_YP + 0.008, 0.62, 0.70)

    clear = lambda m: m - body
    return dict(body=body, wheel=wheel, hub=clear(hub), compass=clear(comp), gauge=clear(inst), panel=None,
                throttle=clear(throttle), rod=clear(rods))

def dossier(body):
    """Dossier capitonne de la banquette avant, contre la face avant de la console (coutures dans sa longueur)."""
    w = w_ck(CON_X1)
    c = cushion2(-1.05, -0.785, -(w - 0.07), CON_YP - 0.06, 0.0, 0.085, re=0.03)
    c = c.transform([[0, 0, 1, CON_X1 + 0.002], [0, 1, 0, 0], [-1, 0, 0, 0]])
    return c - body

def fuel_tank(x0, y0, w=0.32, d=0.30, h=0.27):
    b = cushion(x0, x0 + w, y0, y0 + d, FLOOR + 0.002, FLOOR + h, r=0.03)
    handle = tube([(x0 + 0.08, y0 + d / 2, FLOOR + h - 0.005), (x0 + 0.10, y0 + d / 2, FLOOR + h + 0.035), (x0 + w - 0.10, y0 + d / 2, FLOOR + h + 0.035), (x0 + w - 0.08, y0 + d / 2, FLOOR + h - 0.005)], 0.012)
    cap = cyl((x0 + w - 0.06, y0 + 0.06, FLOOR + h - 0.01), (x0 + w - 0.06, y0 + 0.06, FLOOR + h + 0.025), 0.025)
    return b + handle + cap

def hatch(x0, x1, hw, z, t=0.012, hinge_fwd=False):
    """Trappe : couvercle a coins arrondis, deux charnieres (cote arriere, ou avant si hinge_fwd) et un loquet en face."""
    lid = extrude_xy(rounded_rect((x0 + x1) / 2, 0, (x1 - x0) / 2, hw, 0.03), z, z + t)
    xh, xl = (x1, x0) if hinge_fwd else (x0, x1)
    hinges = box(xh - 0.032, xh + 0.032, -hw + 0.08, -hw + 0.15, z, z + t + 0.006) + box(xh - 0.032, xh + 0.032, hw - 0.15, hw - 0.08, z, z + t + 0.006)
    dl = 0.04 if hinge_fwd else -0.04
    latch = box(min(xl, xl + dl) + 0.0, max(xl, xl + dl), -0.05, 0.05, z + t, z + t + 0.006)
    return lid, hinges + latch

def bollard(x, z0, z1, l=0.22):
    """Bitte d'amarrage en T sur la plage avant (photo « avant ») : socle moule et barre transversale."""
    ped = extrude_xy(rounded_rect(x, 0, 0.05, 0.035, 0.03), z0, z1 - 0.01) + cyl((x, 0, z1 - 0.03), (x, 0, z1 + 0.012), 0.03, 0.026)
    bar = cyl((x, -l / 2, z1 + 0.012), (x, l / 2, z1 + 0.012), 0.017, 0.017, 20) + sphere((x, -l / 2, z1 + 0.012), 0.017, 16) + sphere((x, l / 2, z1 + 0.012), 0.017, 16)
    return ped + bar

# ------------------------------------------------------------------ moteur Suzuki DF90A (fixe sur l'echancrure, en position de route)
def superellipse(x, z0, z1, w, n=3.0, N=48):
    t = np.linspace(0, 2 * np.pi, N, endpoint=False); c, s_ = np.cos(t), np.sin(t)
    zc, hz = (z0 + z1) / 2, (z1 - z0) / 2
    return [(x, w * np.sign(cc) * abs(cc) ** (2 / n), zc + hz * np.sign(ss) * abs(ss) ** (2 / n)) for cc, ss in zip(c, s_)]

COWL = [  # z, x avant, x arriere, demi-largeur  (DF90A arbre L : plaque anti-ventilation au niveau de la quille)
    (0.00, -0.160, -0.420, 0.068), (0.30, -0.170, -0.440, 0.075), (0.40, -0.160, -0.470, 0.100), (0.48, -0.148, -0.530, 0.140),
    (0.58, -0.128, -0.625, 0.190), (0.70, -0.110, -0.720, 0.225), (0.81, -0.100, -0.775, 0.240), (0.95, -0.100, -0.790, 0.240),
    (1.08, -0.102, -0.765, 0.235), (1.14, -0.120, -0.700, 0.210), (1.165, -0.160, -0.620, 0.170), (1.175, -0.220, -0.540, 0.110)]

def hsec(z, xf, xb, w, n=2.6, N=48, grow=0.0):
    t = np.linspace(0, 2 * np.pi, N, endpoint=False); c, s_ = np.cos(t), np.sin(t)
    xc, hx = (xf + xb) / 2, (xf - xb) / 2 + grow; w = w + grow
    return [(xc + hx * np.sign(cc) * abs(cc) ** (2 / n), w * np.sign(ss) * abs(ss) ** (2 / n), z) for cc, ss in zip(c, s_)]

def cowl(grow=0.0, z0=-1, z1=9):
    return loft([hsec(*r, grow=grow) for r in COWL if z0 <= r[0] <= z1])

def engine():
    cw = cowl()
    band = cowl(grow=0.006, z0=0.58, z1=1.08) ^ box(-1.0, 0.0, -0.4, 0.4, 0.80, 0.814)   # ligne de separation du capot
    bracket = box(-0.14, T_TR + 0.012, -0.12, 0.12, 0.508, 0.545) + box(-0.14, 0.0, -0.12, 0.12, 0.32, 0.545) + \
              box(T_TR - 0.002, T_TR + 0.012, -0.10, 0.10, 0.38, 0.545) + \
              extrude_xz([(-0.20, 0.10), (-0.13, 0.10), (-0.11, 0.53), (-0.20, 0.53)], -0.085, 0.085)
    plate = extrude_xy(rounded_rect(-0.34, 0, 0.23, 0.15, 0.06), -0.02, 0.0)
    strut = extrude_xz([(-0.43, -0.25), (-0.19, -0.25), (-0.15, 0.0), (-0.42, 0.0)], -0.045, 0.045)
    torp = cyl((-0.56, 0, -0.29), (-0.14, 0, -0.29), 0.066, 0.058, 28) + sphere((-0.14, 0, -0.29), 0.058, 20)
    skeg = extrude_xz([(-0.48, -0.29), (-0.30, -0.29), (-0.37, -0.45), (-0.44, -0.45)], -0.012, 0.012)
    body = cw + plate + strut + torp + skeg
    hubp = cyl((-0.66, 0, -0.29), (-0.555, 0, -0.29), 0.042, 0.052, 24)
    blades = None
    for k in range(3):
        a0 = k * 2 * np.pi / 3; B = []
        for rr in np.linspace(0.045, 0.17, 8):
            w2 = 0.055 * np.sin(np.pi * (rr - 0.035) / 0.145) + 0.01
            ang = a0 + 0.30 * (rr / 0.17)
            c = np.array([0, np.cos(ang) * rr, np.sin(ang) * rr]); tg = np.array([0, -np.sin(ang), np.cos(ang)])
            pitch = np.array([0.45, 0, 0]) * 0                                       # pale vrillee : corde inclinee de 35 deg
            ch = np.cos(0.6) * tg + np.sin(0.6) * np.array([1.0, 0, 0])
            ctr = np.array([-0.61, 0, -0.29]) + c
            th = np.array([0.0, 0, 0]) + 0.004 * np.cross(ch, c / rr)
            B.append([ctr - ch * w2 - th, ctr + ch * w2 - th, ctr + ch * w2 + th, ctr - ch * w2 + th])
        blade = loft(B)
        blades = blade if blades is None else blades + blade
    return dict(body=body, band=band, bracket=bracket, prop=hubp + blades)

# ------------------------------------------------------------------ berceau de presentation
def cradle(xs=(1.05, 3.25), half=0.62, zb=-0.56, t=0.07):
    out = None
    for x0 in xs:
        ys_ = np.linspace(-half, half, 41)
        top = [(y, min(zbot(x0 - t / 2, y), zbot(x0 + t / 2, y)) - 0.004) for y in ys_]
        poly = [(-half, zb), (half, zb)] + top[::-1]
        sad = extrude_yz(poly, x0 - t / 2, x0 + t / 2)
        sad = sad - extrude_yz(rounded_rect(0, (zb + min(z for _, z in top)) / 2 - 0.02, half - 0.16, ((min(z for _, z in top)) - zb) / 2 - 0.09, 0.08), x0 - t, x0 + t)
        foot = box(x0 - 0.14, x0 + 0.14, -half - 0.04, half + 0.04, zb - 0.03, zb + 0.015)
        part = sad + foot
        out = part if out is None else out + part
    beam = box(xs[0], xs[1], -0.05, 0.05, zb - 0.03, zb + 0.05)
    return out + beam

if __name__ == "__main__":
    h = hull()
    print("hull", h.volume(), h.bounding_box())
