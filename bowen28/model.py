"""Maquette Bowen 28 center console + 2 hors-bords, echelle 1:19 (~50 cm hors tout).

Toutes les cotes sont en metres reels ; l'export STL est en millimetres a l'echelle.
Axes : x vers l'avant (0 = tableau arriere), y vers babord (repere direct), z vers le haut (0 = quille au tableau).
"""
import math
import os
import numpy as np
import trimesh
from manifold3d import Manifold, Mesh, CrossSection, JoinType, OpType

SCALE = 1.0 / 19.0           # echelle de la maquette
MM = 1000.0 * SCALE          # metres reels -> mm maquette
OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

def mm2m(v):                 # mm maquette -> metres reels (pour trous, jeux)
    return v / MM

# ------------------------------------------------------------------ helpers
def mesh_to_manifold(V, F):
    tm = trimesh.Trimesh(V, F, process=False)
    if tm.volume < 0:
        F = F[:, ::-1]
    m = Manifold(Mesh(vert_properties=np.asarray(V, np.float32),
                      tri_verts=np.asarray(F, np.uint32)))
    assert m.status().name == "NoError", m.status()
    assert not m.is_empty()
    return m

def loft(sections):
    """Loft de sections fermees (meme nb de points), bouchons en eventail."""
    S, N = len(sections), len(sections[0])
    V = [np.asarray(s, float) for s in sections]
    V = np.concatenate(V)
    F = []
    for i in range(S - 1):
        for j in range(N):
            a = i * N + j
            b = i * N + (j + 1) % N
            c = (i + 1) * N + (j + 1) % N
            d = (i + 1) * N + j
            F += [[a, b, c], [a, c, d]]
    c0 = len(V); c1 = c0 + 1
    V = np.vstack([V, np.mean(sections[0], axis=0), np.mean(sections[-1], axis=0)])
    base = (S - 1) * N
    for j in range(N):
        F.append([c0, (j + 1) % N, j])
        F.append([c1, base + j, base + (j + 1) % N])
    return mesh_to_manifold(V, np.array(F))

def superellipse(cx, cy, a, b, n=2.6, N=72):
    t = np.linspace(0, 2 * np.pi, N, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    x = cx + a * np.sign(c) * np.abs(c) ** (2 / n)
    y = cy + b * np.sign(s) * np.abs(s) ** (2 / n)
    return np.stack([x, y], 1)

def ccw(poly):
    p = np.asarray(poly, float)
    area = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    return p if area > 0 else p[::-1]

def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])

def extrude_xz(poly_xz, y0, y1):
    """Extrude un profil (x,z) entre y0 et y1."""
    cs = CrossSection([ccw(poly_xz)])
    m = Manifold.extrude(cs, y1 - y0)            # profil dans XY, epaisseur en Z
    # (X,Y,Z) -> (x=X, y=Z, z=Y) : rotation -90 autour de x puis miroir => on passe par une matrice
    m = m.rotate([90, 0, 0])                     # (X,Y,Z)->(X,-Z,Y)
    return m.translate([0, y1, 0])               # y = y1 - Z  in [y0,y1]

def cyl_x(x0, x1, y, z, r, seg=24):
    return Manifold.cylinder(x1 - x0, r, r, seg).rotate([0, 90, 0]).translate([x0, y, z])

def cyl_y(y0, y1, x, z, r, seg=20):
    lo, hi = sorted([y0, y1])
    return Manifold.cylinder(hi - lo, r, r, seg).rotate([-90, 0, 0]).translate([x, lo, z])

# ------------------------------------------------------------------ hull definition
L = 8.20          # longueur coque (tableau -> etrave)
BMAX = 1.22       # demi-largeur max (bau 2,44 m = 8 ft)

def ys(x):        # demi-largeur au livet (avant plus fin, cotes quasi droites vers l'etrave)
    x = np.asarray(x, float)
    aft = 1.12 + 0.10 * np.sin(np.pi / 2 * np.clip(x / 3.6, 0, 1))
    t = np.clip((x - 3.6) / (L - 3.6), 0, 1)
    fwd = BMAX * (1 - t ** 1.45)
    return np.maximum(np.where(x <= 3.6, aft, fwd), 0.012)

def zs(x):        # livet : quasi plat, legerement bombe (courbure negative), tres leger plongeant a l'avant
    u = np.clip(np.asarray(x, float), 0, L) / L
    return 1.24 + 0.20 * u - 0.17 * u ** 2

def smax(a, b, k):
    """max lisse (raccord arrondi de largeur k)."""
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.maximum(a, b) + h * h * k * 0.25

# Avant (croquis sur la photo de profil) : quille droite jusqu'a 3 m de l'etrave, puis courbe
# convexe qui remonte de plus en plus vite jusqu'a l'etrave (~35 deg au sommet).
FORE_SPAN = 3.05                   # longueur de la remontee, mesuree depuis l'etrave
FORE_EXP = 1.75                    # forme de la courbe (> 1 : convexe, tangente a la quille)
X_FORE = L - FORE_SPAN

def zk(x):        # ligne de quille
    u = np.clip((np.asarray(x, float) - X_FORE) / FORE_SPAN, 0, 1)
    return (float(zs(L)) - 0.04) * u ** FORE_EXP

def beta_min(x):  # V minimal (deg), s'ouvre progressivement vers l'avant
    t = np.clip((np.asarray(x, float) - 3.8) / (L - 3.8), 0, 1)
    return 21.0 + 25.0 * t ** 1.15

def zchine(x):    # hauteur du bouchain vue de profil : presque droite puis remonte en douceur
    x = np.asarray(x, float)
    u = np.clip((x - 3.2) / (L - 3.2), 0, 1)
    base = 0.40 + 0.03 * np.clip(x / L, 0, 1) + (float(zs(L)) - 0.26 - 0.43) * u ** 2.3
    return base

# ---- filet noir de flanc (v16) : mesure sur la photo de profil (camera calee sur la coque)
STRIPE_C = (0.0020166, 0.023828, 0.57487)       # axe du filet fin : z = a x^2 + b x + c
STRIPE_W, STRIPE_BAND = 0.04, 0.11              # filet fin (4 cm) ; bande arriere (11 cm)
STRIPE_X_BAND = (0.90, 1.15)                    # la bande s'elargit vers le haut entre ces abscisses
STRIPE_X_END, STRIPE_TAPER = 7.15, 0.30         # bout avant (rejoint le bouchain), effile sur 30 cm
KNUCKLE_GAP = 0.02                              # l'arete passe 2 cm sous le bord bas du filet


def stripe_axis(x):
    return float(np.polyval(STRIPE_C, x))


def stripe_low(x):
    """Bord bas du filet (continu, de l'etrave au tableau)."""
    return stripe_axis(min(max(x, 0.0), STRIPE_X_END)) - STRIPE_W / 2


def stripe_width(x):
    a, b = STRIPE_X_BAND
    t = float(np.clip((b - x) / (b - a), 0, 1))
    t = t * t * (3 - 2 * t)
    w = STRIPE_W + (STRIPE_BAND - STRIPE_W) * t
    e = STRIPE_X_END - x
    if e < STRIPE_TAPER:
        w = max(0.006, STRIPE_W * e / STRIPE_TAPER)
    return w


def chain(x):
    """Points (y,z) du flanc tribord, de la quille au liston."""
    b = float(ys(x)); k = min(1.0, b / 0.40)
    r = 0.85 - 0.20 * np.clip((x - 2.5) / 5.7, 0, 1) ** 1.2
    yc = b * r
    zkx = float(zk(x))
    min_tan = math.tan(math.radians(float(beta_min(x))))
    zc = float(smax(float(zchine(x)), zkx + yc * min_tan + 0.01, 0.12))
    zsx = float(zs(x))
    zc = min(zc, zsx - 0.12 * k - 0.02)
    K = (0.0, zkx)
    def on_bottom(f):
        return (yc * f, zkx + (zc - zkx) * f)
    A1 = on_bottom(0.33); A2 = (A1[0] + 0.035 * k, A1[1])       # virure 1
    B1 = on_bottom(0.66); B2 = (B1[0] + 0.035 * k, B1[1])       # virure 2
    Cin = (yc, zc); Cout = (yc + 0.065 * k, zc - 0.012 * k)     # bouchain (spray rail)
    Rl = (b, zsx - 0.07 * k)
    # arete de flanc (v16) : juste sous le filet noir, qui descend de l'avant vers l'arriere (photo de profil)
    zM = max(stripe_low(x) - KNUCKLE_GAP, Cout[1] + 0.005)
    f = float(np.clip((zM - Cout[1]) / max(Rl[1] - Cout[1], 1e-6), 0.0, 0.6))
    Mx = Cout[0] + f * (Rl[0] - Cout[0]) - 0.012 * k * min(1.0, f / 0.12)
    Mz = Cout[1] + f * (Rl[1] - Cout[1])
    M = (Mx, Mz)
    Rol = (b + 0.035 * k, zsx - 0.06 * k)                       # liston
    Roh = (b + 0.035 * k, zsx)
    return [K, A1, A2, B1, B2, Cin, Cout, M, Rl, Rol, Roh]

def hull_section(x):
    ch = chain(x)
    star = [(x, y, z) for (y, z) in ch]
    port = [(x, -y, z) for (y, z) in ch[1:]][::-1]
    return np.array(star + port)

def zbot(x, y):
    """Hauteur de la carene (exterieur) a la demi-largeur y."""
    ch = chain(x)[:9]
    yy = np.maximum.accumulate(np.array([p[0] for p in ch]))
    zz = np.array([p[1] for p in ch])
    if y >= yy[-1]:
        return float(zs(x))
    return float(np.interp(y, yy, zz))

# ---- filet noir : rainure dans la coque + inserts noirs imprimes (v16)
STRIPE_DEPTH = mm2m(0.5)       # profondeur de la rainure
STRIPE_T = mm2m(0.6)           # epaisseur de l'insert (depasse de 0,1 mm)
STRIPE_CLR = mm2m(0.1)         # jeu de chaque cote
STRIPE_SPLIT = 3.80            # comme la coque : un insert par moitie de coque
STRIPE_TR_Y = 0.62             # bout interieur de la bande sur le tableau (contre le caisson de la chaise, v17)


def stripe_center(x):
    if x > STRIPE_X_END - STRIPE_TAPER:
        return stripe_axis(x)
    return stripe_low(x) + stripe_width(x) / 2


def hull_point(x, z):
    """Point de la face exterieure du flanc (y > 0) a la hauteur z, entre l'arete et le liston."""
    ch = chain(x)
    Mp, Rl = np.array(ch[7]), np.array(ch[8])
    t = (z - Mp[1]) / (Rl[1] - Mp[1])
    return np.array([x, Mp[0] + t * (Rl[0] - Mp[0]), z])


def stripe_frames(x0, x1, n=None):
    """Echantillons du filet (cote y > 0) : x, point, normale sortante, direction 'haut' dans la surface, largeur."""
    n = n or max(8, int(abs(x1 - x0) / 0.04))
    xs = np.linspace(x0, x1, n)
    P = np.array([hull_point(x, stripe_center(x)) for x in xs])
    out = []
    for i, x in enumerate(xs):
        h = 0.01
        zc = stripe_center(x)
        Tx = hull_point(x + h, zc) - hull_point(x - h, zc)
        ch = chain(x)
        dsec = np.array([0.0, ch[8][0] - ch[7][0], ch[8][1] - ch[7][1]])
        nrm = np.cross(dsec, Tx); nrm /= np.linalg.norm(nrm)
        if nrm[1] < 0:
            nrm = -nrm
        T = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]; T /= np.linalg.norm(T)
        up = np.cross(T, nrm); up /= np.linalg.norm(up)
        if up[2] < 0:
            up = -up
        out.append((x, P[i], nrm, up, stripe_width(x)))
    return out


def _sweep(frames, half_extra, n_in, n_out, side=1):
    secs = []
    for (x, P, nrm, up, w) in frames:
        a = w / 2 + half_extra
        q = [P - a * up - n_in * nrm, P + a * up - n_in * nrm, P + a * up + n_out * nrm, P - a * up + n_out * nrm]
        q = [np.array([p[0], side * p[1], p[2]]) for p in q]
        secs.append(q if side > 0 else q[::-1])
    return loft(secs)


def stripe_groove():
    """Rainures des filets (2 flancs) + bande sur le tableau, a retrancher de la coque."""
    fr = stripe_frames(0.0, STRIPE_X_END, 190)
    x, P, nrm, up, w = fr[0]
    fr = [(x - 0.03, P - np.array([0.03, 0, 0]), nrm, up, w)] + fr          # traverse le bord du tableau
    cuts = [_sweep(fr, STRIPE_CLR, STRIPE_DEPTH, 0.004, s) for s in (1, -1)]
    z0 = stripe_low(0.0) - STRIPE_CLR; z1 = stripe_low(0.0) + STRIPE_BAND + STRIPE_CLR
    for s in (1, -1):
        y0, y1 = sorted([s * (STRIPE_TR_Y - STRIPE_CLR), s * 1.6])
        cuts.append(box(-0.006, STRIPE_DEPTH, y0, y1, z0, z1))
    return cuts


def stripe_inlay_side(xa, xb, side=1):
    """Insert noir en place (pour l'assemblage) entre xa et xb."""
    return _sweep(stripe_frames(xa, xb), 0.0, STRIPE_DEPTH - mm2m(0.02), STRIPE_T - STRIPE_DEPTH, side)


def stripe_inlay_flat(xa, xb):
    """Insert deplie a plat (impression) : la ligne mediane garde sa courbure geodesique."""
    fr = stripe_frames(xa, xb, 240)
    P = np.array([f[1] for f in fr]); ds = np.linalg.norm(np.diff(P, axis=0), axis=1)
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    dT = np.gradient(T, axis=0)
    s = np.r_[0, np.cumsum(ds)]
    ds_c = np.gradient(s)
    kg = np.array([(dT[i] @ fr[i][3]) / ds_c[i] for i in range(len(fr))])
    th = np.r_[0, np.cumsum(0.5 * (kg[1:] + kg[:-1]) * ds)]
    c = np.stack([np.r_[0, np.cumsum(np.cos(th[:-1]) * ds)], np.r_[0, np.cumsum(np.sin(th[:-1]) * ds)]], 1)
    nrm2 = np.stack([-np.sin(th), np.cos(th)], 1)
    w = np.array([f[4] for f in fr])
    poly = np.vstack([c - nrm2 * (w / 2)[:, None], (c + nrm2 * (w / 2)[:, None])[::-1]])
    return Manifold.extrude(CrossSection([ccw(poly)]), STRIPE_T)


def stripe_transom_profile():
    """Bande du tableau, profil (y, z) cote y > 0 : de la nacelle moteur au coin du tableau."""
    z0 = stripe_low(0.0); z1 = z0 + STRIPE_BAND
    ya, yb = hull_point(0.0, z0)[1], hull_point(0.0, z1)[1]
    return [(STRIPE_TR_Y, z0), (ya + mm2m(0.1), z0), (yb + mm2m(0.1), z1), (STRIPE_TR_Y, z1)]


def stripe_inlay_transom(side=1):
    prof = stripe_transom_profile()
    cs = CrossSection([ccw(prof)])
    m = Manifold.extrude(cs, STRIPE_T)                       # (X=y, Y=z, Z=epaisseur)
    m = m.transform([[0, 0, -1, STRIPE_DEPTH - mm2m(0.02)], [1, 0, 0, 0], [0, 1, 0, 0]])   # epaisseur vers -x
    return m if side > 0 else m.mirror([0, 1, 0])


def stripe_transom_flat():
    return Manifold.extrude(CrossSection([ccw(stripe_transom_profile())]), STRIPE_T)


GUN = 0.22                     # largeur du plat-bord
X_CK0, X_CK1 = 0.30, 6.80      # cockpit : du tableau a la plage avant
FLOOR = 0.52                   # pont du cockpit

def w_ck(x):
    return float(ys(x)) - GUN

BOW_X0 = 4.65            # bout arriere des banquettes avant (retours), contre le module lateral
BOW_SEAT_D = 0.42        # profondeur assise + dossier de la banquette avant
BOW_BACK_T = 0.10        # epaisseur des coussins de dossier (cotes et avant)
BOW_RET_T = 0.10         # epaisseur du retour (le long de x) : 100 % coussin, sans ame blanche
BOW_BACK_TOP = 1.375     # haut des dossiers : ~8 cm au-dessus du plat-bord (moitie du depassement de la v11)
BOW_RET_AU, BOW_RET_AV = 0.20, 0.30   # demi-axes de l'arrondi haut-interieur du retour (horizontal, vertical)

def well_half(x):
    """Demi-largeur du plancher entre les assises de la banquette avant."""
    return max(w_ck(max(x, BOW_X0)) - BOW_SEAT_D, 0.14)

def zfloor(x):
    """Plancher du cockpit. Sous la banquette avant, il suit le fond au droit du puits central
    (les cotes sont remplies par les assises)."""
    y_ref = w_ck(x)
    if x > BOW_X0:
        t = min(1.0, (x - BOW_X0) / 0.25)
        y_ref = (1 - t) * y_ref + t * min(y_ref, well_half(x) + 0.06)
    return max(FLOOR, zbot(x, y_ref) + 0.06)

def build_hull_shell():
    xs = np.unique(np.concatenate([np.linspace(0, 6.0, 61), np.linspace(6.0, L, 90)]))
    return loft([hull_section(x) for x in xs])

_SHELL = {}
def shell_cached():
    if "s" not in _SHELL:
        _SHELL["s"] = build_hull_shell()
    return _SHELL["s"]

def build_cockpit_cutter(grow=0.0):
    xs = np.linspace(X_CK0 - grow, X_CK1 + grow, 120)
    secs = []
    for x in xs:
        xc = min(max(x, X_CK0), X_CK1)
        w = w_ck(xc) + grow; zf = zfloor(xc) - grow
        secs.append([(x, -w, zf), (x, w, zf), (x, w, 3.5), (x, -w, 3.5)])
    return loft(secs)

# ------------------------------------------------------------------ interior
CUSH = 0.08                          # epaisseur reservee aux coussins faits main (4,2 mm a l'echelle)
DXC = -0.68                          # recul de la console et du siege avant par rapport a la v2
SEAT_X, SEAT_Y = 2.08, 0.31          # fauteuils coquilles (centre), de part et d'autre de l'axe
PLAT_X = (1.72, 2.44)                # socle des fauteuils
PLAT_TOP = FLOOR + 0.50              # dessus du caisson des fauteuils (photos v16 : caisson haut avec filet)
PED_H = 0.07                         # embase pivotante + glissiere (alu), sous le fauteuil
SEAT_Z = PLAT_TOP + PED_H            # dessous de la coque du fauteuil
PIN_R, PIN_H = 0.022, 0.05
CLR_SEAT = 0.2 / (1000.0 / 19.0)       # jeu garniture / coque (0,2 mm a l'echelle)
# banquettes arriere : haute (sur l'arriere) + basse (devant), marche a babord
BENCH_HI_X = (X_CK0, 0.75)
BENCH_LO_X = (0.75, 1.20)
BENCH_HI_TOP = 1.12                  # assise haute ~1,20 m avec coussin
BENCH_LO_TOP = 0.86                  # assise basse ~0,94 m avec coussin
STEP_Y = 0.47                        # passage libre a babord (y > 0,47), a droite en regardant vers l'arriere
BACK_HI = (0.28, 0.36, 1.62)         # dossier de la banquette haute : x0, x1, haut
BACK_XB = 0.32                       # axe de la planche du dossier haut
BACK_RET_R = 0.17                    # rayon du retour arrondi (cote passage)
BACK_RET_X = 0.60                    # le retour avance jusqu'a x = 0,60
BOW_SEAT_TOP = 0.92                  # assise rigide de la banquette avant (coussin par-dessus)

SEAT_A, SEAT_B, SEAT_H = 0.25, 0.26, 0.62
SEAT_CX = 0.08                       # centre de la cavite (decale vers l'avant : dossier epais)
SEAT_WALL = 0.05                     # epaisseur des flancs de la coque blanche
SEAT_FLOOR = 0.10                    # fond de la cavite
LINER_T = 0.03                       # garniture taupe (1,6 mm a l'echelle)
RIM_REVEAL = 0.012                   # liseré blanc de la coque visible au-dessus de la garniture
SEAT_BAND_W, SEAT_BAND_G = 0.05, 0.035   # 2 lignes blanches au milieu (meme style que les banquettes)
SEAT_BRIDGE = 0.035                  # pont de garniture au bout des fentes (avant et haut du dossier)

def _seat_plane():
    A = np.array([-SEAT_A, SEAT_H]); B = np.array([SEAT_A, 0.17])
    d = B - A; n = np.array([-d[1], 0.0, d[0]]); n = n / np.linalg.norm(n)
    if n[2] > 0:
        n = -n                           # normale vers le bas/arriere : on garde le dessous du plan
    return n, float(n[0] * A[0] + n[2] * A[1])

def seat_trim(m, drop=0.0):
    """Coupe le haut (dossier haut a l'arriere, flancs qui descendent vers l'avant), abaisse de drop."""
    n, off = _seat_plane()
    return m.trim_by_plane(n.tolist(), off - n[2] * drop)

def seat_cavity(shrink=0.0, floor=SEAT_FLOOR, top=SEAT_H + 0.2):
    secs = []
    for z in (floor, top):
        p = superellipse(SEAT_CX, 0, SEAT_A - SEAT_WALL - shrink, SEAT_B - SEAT_WALL - shrink, 3.0, 64)
        secs.append(np.column_stack([p, np.full(len(p), z)]))
    return loft(secs)

def seat_outer():
    a, b, H = SEAT_A, SEAT_B, SEAT_H
    secs = []
    for z, sa, sb in [(0.0, a - 0.02, b - 0.02), (0.10, a, b), (H, a - 0.01, b - 0.01)]:
        p = superellipse(0, 0, sa, sb, 3.0, 64)
        secs.append(np.column_stack([p, np.full(len(p), z)]))
    return loft(secs)

def seat_stripes(grow=0.0, short=0.0):
    """Deux bandes au milieu, de l'avant (moins le pont) jusque sous le haut du dossier (moins le pont)."""
    c = SEAT_BAND_G / 2 + SEAT_BAND_W / 2
    lim = seat_trim(box(-1, SEAT_A - SEAT_BRIDGE - short, -1, 1, -1, 2), RIM_REVEAL + SEAT_BRIDGE + short)
    return [box(-1, 1, s * c - SEAT_BAND_W / 2 - grow, s * c + SEAT_BAND_W / 2 + grow, -1, 2) ^ lim for s in (-1, 1)]

def bucket_seat_parts():
    """Fauteuil coquille en 2 couleurs (repere local : centre du dessous a l'origine, face vers +x) :
    coque blanche avec 2 nervures + garniture taupe a 2 fentes. Posee dans la coque, la garniture
    laisse passer les nervures : taupe a l'interieur avec 2 lignes blanches, blanc a l'exterieur."""
    outer = seat_outer()
    cav = seat_cavity()
    shell = seat_trim(outer - cav)
    shell = shell - Manifold.cylinder(0.075, PIN_R + mm2m(0.2), PIN_R + mm2m(0.2), 20).translate([0, 0, -0.01])
    lin_out = seat_cavity(CLR_SEAT, SEAT_FLOOR + CLR_SEAT)
    lin_in = seat_cavity(CLR_SEAT + LINER_T, SEAT_FLOOR + CLR_SEAT + LINER_T)
    liner = seat_trim((lin_out - lin_in) ^ outer, RIM_REVEAL)
    band = seat_trim((cav - lin_in) ^ outer, RIM_REVEAL)            # epaisseur garniture + jeu
    ribs = Manifold.batch_boolean([st ^ band for st in seat_stripes(-CLR_SEAT, CLR_SEAT)], OpType.Add)
    slots = Manifold.batch_boolean(seat_stripes(), OpType.Add)
    return shell + ribs, liner - slots

def bucket_seat():
    return bucket_seat_parts()[0]

PIPING_R = 0.0065                    # liseré : rainure de 0,7 mm de large (a passer au feutre blanc)

def _seat_ab(z):
    a, b, H = SEAT_A, SEAT_B, SEAT_H
    za = [0.0, 0.10, H]; aa = [a - 0.02, a, a - 0.01]; bb = [b - 0.02, b, b - 0.01]
    return float(np.interp(z, za, aa)), float(np.interp(z, za, bb))

def _seat_top(x):
    return SEAT_H - (SEAT_H - 0.17) * (x + SEAT_A) / (2 * SEAT_A)

def piping_path(side=1, n=40):
    """Liseré sur le flanc du fauteuil : 6 cm sous le bord du haut, du dos jusqu'a l'avant."""
    pts = []
    for t in np.linspace(0, 1, n):
        phi = (np.pi - 0.25) + (0.62 - (np.pi - 0.25)) * t
        for _ in range(3):
            pass
        c, sn = np.cos(phi), np.sin(phi)
        z = 0.30
        for _ in range(6):                                  # point fixe : hauteur = bord du haut - 6 cm
            a, b = _seat_ab(z)
            x = a * np.sign(c) * abs(c) ** (2 / 3.0)
            z = min(_seat_top(x) - 0.06, SEAT_H - 0.06)
        a, b = _seat_ab(z)
        x = a * np.sign(c) * abs(c) ** (2 / 3.0); y = b * np.sign(sn) * abs(sn) ** (2 / 3.0)
        pts.append((x, side * y, z))
    return pts

def bucket_seat_v16():
    """Fauteuil coquille d'une seule piece taupe (photos v16), liseré en creux de chaque cote, logement du
    teton de l'embase dessous."""
    outer = seat_outer()
    cav = seat_cavity(CLR_SEAT + LINER_T, SEAT_FLOOR + CLR_SEAT + LINER_T)
    seat = seat_trim(outer - cav)
    seat = seat - Manifold.cylinder(0.075, PIN_R + mm2m(0.2), PIN_R + mm2m(0.2), 20).translate([0, 0, -0.01])
    for side in (1, -1):
        seat = seat - tube_path(piping_path(side), PIPING_R, 10)
    return seat

# ---- bandes claires a l'interieur des fauteuils (photo v19, meme style que les banquettes) : 2 bandes blanches au
# milieu, du bord avant de l'assise jusqu'en haut du dossier, posees dans 2 rainures du fauteuil taupe
STRIPE_D = mm2m(0.8)                 # profondeur des rainures = epaisseur des bandes
STRIPE_CLR = mm2m(0.1)               # jeu autour de la bande
SEAT_BAND_C = SEAT_BAND_G / 2 + SEAT_BAND_W / 2   # axe de chaque bande (y = +-)

def _seat_cav():
    sh = CLR_SEAT + LINER_T
    return SEAT_FLOOR + sh, SEAT_A - SEAT_WALL - sh, SEAT_B - SEAT_WALL - sh

def seat_band_profile(grow=0.0, over=0.0):
    """Profil (x, z) en L d'une bande : a plat sur l'assise depuis le bord avant (moins un pont), puis debout contre
    le dossier jusqu'a un pont sous le bord du haut. grow : jeu ; over : debord de l'outil dans la cavite."""
    zf, ac, bc = _seat_cav()
    xw = SEAT_CX - ac * (1 - abs(SEAT_BAND_C / bc) ** 3) ** (1 / 3)      # dossier au droit de la bande
    xf = SEAT_CX + ac - SEAT_BRIDGE
    zt = _seat_top(xw) - SEAT_BRIDGE
    d, g = STRIPE_D, grow
    return [(xw - d - g, zf - d - g), (xf + g, zf - d - g), (xf + g, zf + over), (xw + over, zf + over),
            (xw + over, zt + g), (xw - d - g, zt + g)]

def seat_band():
    """Bande blanche (repere du fauteuil, centree en y = 0) : se pose dans la rainure en y = +-SEAT_BAND_C."""
    w = SEAT_BAND_W / 2
    return extrude_xz(seat_band_profile(), -w, w)

def bucket_seat_v19():
    """Fauteuil taupe v16 + 2 rainures interieures pour les bandes blanches."""
    seat = bucket_seat_v16()
    w = SEAT_BAND_W / 2 + STRIPE_CLR
    prof = seat_band_profile(STRIPE_CLR, 0.03)
    for sy in (1, -1):
        seat = seat - extrude_xz(prof, sy * SEAT_BAND_C - w, sy * SEAT_BAND_C + w)
    return seat

def build_seat_base(s):
    """Embase pivotante + glissiere alu posee sur le caisson, teton en haut pour le fauteuil."""
    parts = [Manifold.cylinder(0.014, 0.105, 0.10, 40),
             box(-0.13, 0.13, -0.115, 0.115, 0.014, 0.032),
             box(-0.13, 0.13, -0.10, -0.07, 0.032, 0.046), box(-0.13, 0.13, 0.07, 0.10, 0.032, 0.046),
             Manifold.cylinder(PED_H - 0.032, 0.06, 0.06, 32).translate([0, 0, 0.032]),
             Manifold.cylinder(PIN_H + 0.005, PIN_R, PIN_R, 24).translate([0, 0, PED_H - 0.005])]
    return Manifold.batch_boolean(parts, OpType.Add).translate([SEAT_X, s * SEAT_Y, PLAT_TOP])

# filet noir sur la face arriere du caisson (cote tribord, photo v16)
NET_Y, NET_Z = (-0.57, 0.57), (FLOOR + 0.10, PLAT_TOP - 0.05)   # v21 : tout le dos du caisson (partie plate)
NET_T, NET_REC = mm2m(1.2), mm2m(1.1)   # v22 : plus epais, logement plus profond (depasse toujours de 0,1 mm), 2 tenons au dos
NET_STUD_U = 0.065                       # tenons dans l'ourlet du haut, a 3,4 mm des bords

def net_stud_uv():
    W = NET_Y[1] - NET_Y[0]; H = NET_Z[1] - NET_Z[0]
    return [(NET_STUD_U, H - 0.025), (W - NET_STUD_U, H - 0.025)]

def net_stud_points():
    """Pieds des tenons du filet (repere bateau), sur le fond du logement ; les tenons entrent vers +x dans le caisson."""
    x_in = PLAT_X[0] + NET_REC - mm2m(0.02)
    return [np.array([x_in, NET_Y[0] + u, NET_Z[0] + v]) for (u, v) in net_stud_uv()]

def net_recess():
    import fit as F
    rec = box(PLAT_X[0] - 0.01, PLAT_X[0] + NET_REC, NET_Y[0] - CLR, NET_Y[1] + CLR, NET_Z[0] - CLR, NET_Z[1] + CLR)
    return Manifold.batch_boolean([rec] + F.stud_pair_sockets(net_stud_points(), (1.0, 0.0, 0.0)), OpType.Add)

def build_net_flat():
    """Filet a plat (u = y, v = z, epaisseur selon w) : cadre + mailles en losange, haut renforce."""
    W = NET_Y[1] - NET_Y[0]; H = NET_Z[1] - NET_Z[0]
    frame = CrossSection.square([W, H])
    holes = []
    pitch, hole = 0.042, 0.026
    sq = CrossSection.square([hole, hole]).translate([-hole / 2, -hole / 2]).rotate(45)
    for u in np.arange(0.03, W - 0.02, pitch):
        for v in np.arange(0.03, H - 0.045, pitch):
            holes.append(sq.translate([float(u + (pitch / 2 if int(round(v / pitch)) % 2 else 0)), float(v)]))
    mesh = frame - (CrossSection.batch_boolean(holes, OpType.Add) ^ CrossSection.square([W - 0.05, H - 0.075]).translate([0.025, 0.025]))
    import fit as F
    studs = [F.stud((u, v, 0.0), (0.0, 0.0, -1.0)) for (u, v) in net_stud_uv()]     # v22 : au dos (w < 0)
    return Manifold.batch_boolean([Manifold.extrude(mesh, NET_T)] + studs, OpType.Add)

def place_net(m):
    """Filet a plat -> face arriere du caisson (u -> -y depuis NET_Y[1]... ), epaisseur vers -x."""
    x_in = PLAT_X[0] + NET_REC - mm2m(0.02)
    return m.transform([[0, 0, -1, x_in], [1, 0, 0, NET_Y[0]], [0, 1, 0, NET_Z[0]]])

def bolster_profile(x, s, D, top, shrink=0.0):
    """Profil (y,z) du boudin le long de la paroi interieure, cote s."""
    w = w_ck(x); zf = zfloor(x)
    Di = D - shrink; topi = top - shrink
    r = Di
    pts = [(w + 0.02, zf - 0.02), (w - Di, zf - 0.02), (w - Di, zf + topi - r)]
    for ang in np.linspace(np.pi, np.pi / 2 - 0.2, 11)[1:]:      # l'arc entre franchement dans la paroi
        pts.append((w + r * np.cos(ang), zf + topi - r + r * np.sin(ang)))
    pts.append((w + 0.02, zf + topi))
    return [(x, s * y, z) for (y, z) in pts]

BOLSTER_X = (1.25, 3.95)              # boudins bas rayes (piece taupe separee)
BOLSTER_GAPS = []
STRIPE_W, STRIPE_P = 0.06, 0.25

def build_bolsters():
    xs = np.linspace(BOLSTER_X[0], BOLSTER_X[1], 90)
    full, core = [], []
    for s in (-1, 1):
        secs = [bolster_profile(x, s, 0.09, 0.21) for x in xs]
        if s < 0:
            secs = [sec[::-1] for sec in secs]
        full.append(loft(secs))
        secs = [bolster_profile(x, s, 0.09, 0.21, 0.016) for x in xs]
        if s < 0:
            secs = [sec[::-1] for sec in secs]
        core.append(loft(secs))
    full = full[0] + full[1]; core = core[0] + core[1]
    for g0, g1 in BOLSTER_GAPS:
        full = full - box(g0, g1, -2, 2, -1, 3); core = core - box(g0, g1, -2, 2, -1, 3)
    stripes = []
    c = BOLSTER_X[0] + 0.15
    while c < BOLSTER_X[1] - 0.05:
        stripes.append(box(c - STRIPE_W / 2, c + STRIPE_W / 2, -2, 2, -1, 3))
        c += STRIPE_P
    stripes = Manifold.batch_boolean(stripes, OpType.Add)
    light = full - (stripes - core)  # boudin d'une piece, rayures en creux de 0,8 mm
    dark = core ^ stripes            # fond des rayures (apercu seulement)
    return light, dark

CON_X0, CON_K = 3.30, 0.5            # console : face arriere (repere non recule) ; longueur x 0,5 (v13 : 2 fois plus courte)
FS_LEN = 0.53                        # profondeur du siege avant de console

def con_x(x):
    """Abscisse du dessin d'origine de la console (repere non recule) -> console raccourcie, meme face arriere."""
    return CON_X0 + (x - CON_X0) * CON_K

CON_FRONT = con_x(4.35)              # face avant de la console (repere non recule)
CON_WS_DX = con_x(4.20) - 4.20       # pare-brise et arceau reculent avec le haut de l'avant de la console
DASH = ((con_x(3.62), 1.50), (con_x(4.20), 1.62))     # tableau de bord incline (ecrans)

def dash_z(x):
    (x0, z0), (x1, z1) = DASH
    return z0 + (z1 - z0) * (x - x0) / (x1 - x0)

def console_parts(dx):
    P = {}
    X = lambda pts: [(x + dx, z) for (x, z) in pts]
    con = [(con_x(x), z) for (x, z) in [(3.30, 0.40), (4.35, 0.40), (4.35, 1.52), (4.20, 1.62),
                                         (3.62, 1.50), (3.45, 1.47), (3.30, 1.36)]]
    P["console"] = extrude_xz(X(con), -0.48, 0.48)
    # siege avant de console (assise rigide, coussin fait main par-dessus), contre la face avant
    P["siege_avant_base"] = box(CON_FRONT + dx, CON_FRONT + FS_LEN + dx, -0.46, 0.46, 0.40, 0.96 - CUSH)
    return P

FRONT_SEAT = (CON_FRONT + DXC, CON_FRONT + FS_LEN + DXC, 0.46, 0.96 - CUSH)     # x0, x1, demi-largeur, dessus

def rect_round_corner(u0, u1, v0, v1, cu, cv, r):
    """Rectangle (u,v) dont un seul coin (cu, cv) est arrondi."""
    cs = CrossSection.square([u1 - u0, v1 - v0]).translate([u0, v0])
    su = 1 if cu == u0 else -1; sv = 1 if cv == v0 else -1
    corner = CrossSection.square([r, r]).translate([cu if su > 0 else cu - r, cv if sv > 0 else cv - r])
    disc = CrossSection.circle(r, 48).translate([cu + su * r, cv + sv * r])
    return (cs - corner) + (disc ^ corner)

def back_path(n=60):
    """Axe du dossier haut en plan (x,y) : droit le long du tableau, puis retour arrondi vers l'avant."""
    xb, R = BACK_XB, BACK_RET_R
    y_end = STEP_Y - 0.04                  # axe du retour
    y_s = -(w_ck(xb) - 0.04)
    yR = y_end - R
    pts = [(xb, y) for y in np.linspace(y_s, yR, 30)]
    c = (xb + R, yR)
    for a in np.linspace(np.pi, np.pi / 2, n)[1:]:
        pts.append((c[0] + R * np.cos(a), c[1] + R * np.sin(a)))
    pts += [(x, y_end) for x in np.linspace(xb + R, BACK_RET_X, 6)[1:]]
    return np.array(pts)

def path_band(pts, o0, o1):
    """Bande entre les decalages o0 et o1 (vers l'interieur = vers l'assise)."""
    d = np.gradient(pts, axis=0); d /= np.linalg.norm(d, axis=1)[:, None]
    n_in = np.stack([d[:, 1], -d[:, 0]], 1)
    a = pts + o0 * n_in; b = pts + o1 * n_in
    return ccw(np.vstack([a, b[::-1]]))

def back_rounding(top, r_end=0.14, r_ret=0.12):
    """Prismes qui arrondissent le haut des deux extremites du dossier."""
    y_s = -(w_ck(BACK_XB) - 0.04) - 0.03
    p1 = rect_round_corner(y_s, 3.0, 0.0, top, y_s, top, r_end)          # profil (y,z)
    m1 = Manifold.extrude(p1, 4.0).transform([[0, 0, 1, -2.0], [1, 0, 0, 0], [0, 1, 0, 0]])
    p2 = rect_round_corner(-2.0, BACK_RET_X, 0.0, top, BACK_RET_X, top, r_ret)  # profil (x,z)
    m2 = extrude_xz(p2.to_polygons()[0], -3.0, 3.0)
    return m1 ^ m2

BACK_SKIN_T, BACK_SKIN_Z0 = 0.025, 1.31      # dos taupe du dossier (vu de l'arriere, photos v16)

def build_back_skin():
    """Dos du dossier arriere en taupe : peau de 1,3 mm collee sur la face arriere du dossier rigide blanc,
    au-dessus du tableau (comme le coussin vu depuis la plateforme)."""
    top = BACK_HI[2]
    cs = CrossSection([path_band(back_path(), -0.03 - BACK_SKIN_T, -0.03 - mm2m(0.02))])
    m = Manifold.extrude(cs, top - BACK_SKIN_Z0).translate([0, 0, BACK_SKIN_Z0])
    return m ^ back_rounding(top) ^ build_cockpit_cutter(0.06)

def back_hi_board():
    """Dossier rigide de la banquette haute avec retour arrondi cote passage."""
    top = BACK_HI[2]
    cs = CrossSection([path_band(back_path(), -0.03, 0.03)])
    m = Manifold.extrude(cs, top - 0.95).translate([0, 0, 0.95])
    return m ^ back_rounding(top)

SEADECK_X0 = X_CK1 + 0.06          # bord arriere des tapis SeaDek de la pointe
SD_T = mm2m(1.6)                    # epaisseur des tuiles SeaDek imprimees (v22 : 0,9 -> 1,6 mm)
SD_REC = mm2m(1.0)                  # logement dans le pont (v22 : 0,3 -> 1 mm) : la tuile depasse toujours de 0,6 mm
GROOVE_W, GROOVE_D, GROOVE_P = mm2m(0.6), mm2m(0.4), mm2m(2.2)
PASS_Z = 1.02                       # sol du passage arriere (SeaDek), au-dessus de la plateforme (photos v16)
PLATF_Z = 0.80                      # dessus de la plateforme de bain et de la nacelle moteur (tole larmee)
STEP2_X, STEP2_Z = (0.75, 1.00), 0.77   # marche intermediaire entre le passage et le pont du cockpit
PASS_Y = (0.52, 0.94)               # ouverture dans le tableau arriere (babord)
PLAT_BOX = (-0.62, 0.02, 0.54, 1.00)  # plateforme de bain babord : x0, x1, y0, y1 (plus grande, photos v16)
BRACKET_Y = 0.84                    # demi-largeur de la nacelle moteur (sous la plateforme)
LAD_R = mm2m(0.9)                   # tubes fins (1,8 mm) : echelle et mains courantes
# echelle de bain repliee a plat sur la plateforme (photos v16) : 2 montants le long de x, charniere a l'arriere
LAD2_X = (-0.59, -0.10)             # charniere (arriere) -> bout des montants
LAD2_Y = (0.645, 0.895)
LAD2_STEPS = (-0.49, -0.38, -0.27, -0.17)
LAD2_PIN_R, LAD2_PIN_H = mm2m(0.6), mm2m(0.6)

def seadeck_outline(side=1):
    """Contour en plan (x,y) du tapis SeaDek d'un cote de la pointe (triangle a coins arrondis)."""
    xs = np.linspace(SEADECK_X0, L, 200)
    outer = np.array([float(ys(x)) - 0.07 for x in xs])
    keep = outer > 0.035
    xs, outer = xs[keep], outer[keep]
    pts = [(xs[0], 0.035)] + [(x, y) for x, y in zip(xs, outer)] + [(xs[-1], 0.035)]
    pts = np.array(pts)
    pts[:, 1] *= side
    cs = CrossSection([ccw(pts)])
    return cs.offset(-0.05, JoinType.Round, 2.0, 24).offset(0.05, JoinType.Round, 2.0, 24)

def passage_outline():
    """Tapis du passage arriere (photo v16) : seulement sur le sol du passage, au-dessus de la plateforme."""
    x0, x1, y0, y1 = 0.025, 0.70, 0.56, 0.90
    return CrossSection.square([x1 - x0 - 0.08, y1 - y0 - 0.08]).translate([x0 + 0.04, y0 + 0.04]).offset(0.04, JoinType.Round, 2.0, 24)

def seadeck_grooves(cs, ang, origin):
    lines = [CrossSection.square([4.0, GROOVE_W]).translate([-2.0, k * GROOVE_P]) for k in range(-60, 60)]
    lines = CrossSection.batch_boolean(lines, OpType.Add).rotate(ang).translate(list(origin))
    inner = cs.offset(-0.045, JoinType.Round, 2.0, 24)
    border = cs.offset(-0.025, JoinType.Round, 2.0, 24) - cs.offset(-0.025 - GROOVE_W, JoinType.Round, 2.0, 24)
    g = ((lines ^ inner) + border).offset(-0.002, JoinType.Miter, 2.0, 0).offset(0.002, JoinType.Miter, 2.0, 0)
    return CrossSection.batch_boolean([p for p in g.decompose() if p.area() > 1e-5], OpType.Add).simplify(1e-4)

def border_grooves(cs, inset=0.025, lines_y=()):
    """Rainure de bordure (liseré noir des tapis SeaDek) + lignes longitudinales eventuelles (y constants)."""
    border = cs.offset(-inset, JoinType.Round, 2.0, 24) - cs.offset(-inset - GROOVE_W, JoinType.Round, 2.0, 24)
    inner = cs.offset(-inset - GROOVE_W, JoinType.Round, 2.0, 24)
    parts = [border]
    for y in lines_y:
        parts.append(CrossSection.square([40.0, GROOVE_W]).translate([-20.0, y - GROOVE_W / 2]) ^ inner)
    return CrossSection.batch_boolean(parts, OpType.Add)

# ---- taquets escamotables (ovales inox) : 2 sur les plats-bords arriere, 2 dans les tapis de la pointe
CLEAT_L, CLEAT_W, CLEAT_T = 0.16, 0.065, mm2m(1.6)   # v22 : 1,1 -> 1,6 mm, tenon dessous
CLEAT_REC = mm2m(1.0)                                # v22 : 0,5 -> 1 mm (affleure toujours avec les tuiles SeaDek)
GW_CLEAT_X = 1.12
BOW_CLEAT_X = 7.12

def bow_cleat_xy(side):
    return BOW_CLEAT_X, side * 0.5 * (0.035 + float(ys(BOW_CLEAT_X)) - 0.07)

def gun_mid(x):
    return 0.5 * (w_ck(x) + float(ys(x)))

def cleat_spots():
    """[(x, y, angle_deg)] des 4 taquets."""
    out = []
    for s in (1, -1):
        out.append((GW_CLEAT_X, s * gun_mid(GW_CLEAT_X), np.degrees(np.arctan2(s * (gun_mid(GW_CLEAT_X + 0.1) - gun_mid(GW_CLEAT_X - 0.1)), 0.2))))
    for s in (1, -1):
        x, y = bow_cleat_xy(s)
        out.append((x, y, 0.0))
    return out

def cleat_outline(grow=0.0):
    cs = CrossSection.square([CLEAT_L - CLEAT_W, 0.001]).translate([-(CLEAT_L - CLEAT_W) / 2, -0.0005])
    return cs.offset(CLEAT_W / 2 + grow, JoinType.Round, 2.0, 32)

def build_cleat():
    """Taquet escamotable a plat (z = 0 a CLEAT_T) : ovale avec la fente du taquet et le cercle de la charniere."""
    import fit as F
    m = Manifold.extrude(cleat_outline(), CLEAT_T)
    slot = CrossSection.square([CLEAT_L * 0.62, 0.016]).translate([-CLEAT_L * 0.31, -0.008])
    m = m - Manifold.extrude(slot, 0.02).translate([0, 0, CLEAT_T - mm2m(0.3)])
    return m + F.stud((0.0, 0.0, 0.0), (0.0, 0.0, -1.0))          # v22 : tenon dessous, dans le trou du pont

def place_cleat(m, x, y, ang):
    z = float(zs(x)) - CLEAT_REC
    return m.rotate([0, 0, ang]).translate([x, y, z])

def cleat_recesses():
    import fit as F
    out = []
    for (x, y, ang) in cleat_spots():
        out.append(Manifold.extrude(cleat_outline(CLR), CLEAT_REC + 0.08).rotate([0, 0, ang]).translate([x, y, float(zs(x)) - CLEAT_REC]))
        out.append(place_cleat(F.socket((0.0, 0.0, 0.0), (0.0, 0.0, -1.0)), x, y, ang))    # v22 : trou du tenon
    return out

# ---- tapis SeaDek des plats-bords arriere (photos v16) : de la poupe jusqu'au milieu, coupes au mat,
# au taquet et aux pieds de l'armature du taud
GW_SEGS = [(0.06, 1.012), (1.228, 1.73), (1.87, 2.35), (2.49, 3.74)]   # v22 : 1 mm de paroi de part et d'autre du taquet
FLAG_X = 0.45                       # mat de pavillon (plat-bord babord arriere)
FLAG_R = 0.019                      # tube de 3,8 cm (2 mm a l'echelle)
FLAG_TOP = 2.40
FLAG_SOCK = 0.064                   # v22 : 2,6 -> 3,4 mm sous le pont (le logement du tapis est plus profond)

def gunwale_pad_outline(side, x0, x1):
    xs = np.linspace(x0, x1, max(6, int((x1 - x0) / 0.04)))
    inner = [(x, w_ck(x) + 0.025) for x in xs]
    outer = [(x, float(ys(x)) - 0.008) for x in xs[::-1]]
    pts = np.array(inner + outer); pts[:, 1] *= side
    cs = CrossSection([ccw(pts)])
    return cs.offset(-0.03, JoinType.Round, 2.0, 24).offset(0.03, JoinType.Round, 2.0, 24)

def gunwale_pads():
    """[(nom, tuile a plat (z de 0 a SD_T), surface)] : 4 tapis par cote, 2 tenons dessous (v22)."""
    studs = seadeck_stud_xy()
    out = []
    for s, sn in ((1, "babord"), (-1, "tribord")):
        for k, (x0, x1) in enumerate(GW_SEGS):
            name = f"seadeck_plat_bord_{k + 1}_{sn}"
            cs = gunwale_pad_outline(s, x0, x1)
            t = Manifold.extrude(cs, SD_T) - Manifold.extrude(border_grooves(cs, 0.022), GROOVE_D + 0.01).translate([0, 0, SD_T - GROOVE_D])
            if s > 0 and k == 0:          # v22 : trou ajuste au mat (jeu 0,2 mm), le tapis le guide
                t = t - Manifold.cylinder(1.0, FLAG_R + CLR, FLAG_R + CLR, 32).translate([FLAG_X, gun_mid(FLAG_X), -0.5])
            out.append((name, t + _tile_studs(studs[name]), "pont"))
    return out

def _pad_mid_y(x, s):
    """Milieu (en largeur) d'un tapis de plat-bord a l'abscisse x."""
    return s * 0.5 * (w_ck(x) + 0.025 + float(ys(x)) - 0.008)

def seadeck_stud_xy():
    """v22 : {nom de tuile : [(x, y), ...]} en plan (repere bateau) : 2 tenons sous chaque tuile SeaDek."""
    out = {}
    for side, name in ((1, "seadeck_pointe_babord"), (-1, "seadeck_pointe_tribord")):
        out[name] = [(6.95, side * 0.207), (7.45, side * 0.121)]      # de part et d'autre du taquet escamotable
    out["seadeck_passage_arriere"] = [(0.18, 0.73), (0.55, 0.73)]
    for s, sn in ((1, "babord"), (-1, "tribord")):
        for k, (x0, x1) in enumerate(GW_SEGS):
            xa, xb = x0 + 0.22 * (x1 - x0), x0 + 0.78 * (x1 - x0)
            out[f"seadeck_plat_bord_{k + 1}_{sn}"] = [(xa, _pad_mid_y(xa, s)), (xb, _pad_mid_y(xb, s))]
    return out

def _tile_studs(pts):
    import fit as F
    return Manifold.batch_boolean([F.stud((x, y, 0.0), (0.0, 0.0, -1.0)) for (x, y) in pts], OpType.Add)

def seadeck_stud_points():
    """v22 : {nom : [point 3D du pied de chaque tenon, au fond du logement]} (repere bateau)."""
    out = {}
    for name, pts in seadeck_stud_xy().items():
        out[name] = [np.array([x, y, (PASS_Z if name == "seadeck_passage_arriere" else float(zs(x))) - SD_REC]) for (x, y) in pts]
    return out

def seadeck_stud_sockets():
    """v22 : trous du pont sous les tenons des tuiles (le 1er rond, le 2e oblong dans l'axe des deux)."""
    import fit as F
    cuts = []
    for name, P in seadeck_stud_points().items():
        cuts += F.stud_pair_sockets(P, (0.0, 0.0, -1.0))
    return cuts

def gunwale_pad_recesses():
    cuts = []
    for s in (1, -1):
        for (x0, x1) in GW_SEGS:
            cs = gunwale_pad_outline(s, x0, x1).offset(CLR, JoinType.Round, 2.0, 24)
            cuts.append(place_on_surface(Manifold.extrude(cs, SD_REC + 0.08 + mm2m(0.04)), "pont", sink=SD_REC + mm2m(0.04)))
    return cuts

def flag_xy():
    return FLAG_X, gun_mid(FLAG_X)

def build_flagpole(flat=True):
    """Mat de pavillon inox (bout haut a gainer de noir), tenon dans le plat-bord, collerette de base."""
    x, y = flag_xy(); z0 = float(zs(x))
    parts = [Manifold.cylinder(FLAG_TOP - z0 + FLAG_SOCK, FLAG_R, FLAG_R, 20).translate([x, y, z0 - FLAG_SOCK]),
             Manifold.cylinder(0.025, 0.032, 0.028, 24).translate([x, y, z0 + mm2m(0.6)]),
             Manifold.sphere(FLAG_R * 1.25, 16).translate([x, y, FLAG_TOP])]
    m = Manifold.batch_boolean(parts, OpType.Add)
    if flat:
        m = m.trim_by_plane([0.0, -1.0, 0.0], -(y + FLAG_R * 1.2 - mm2m(0.3)))
    return m

def flag_socket():
    x, y = flag_xy(); z0 = float(zs(x))
    r = FLAG_R + CLR
    return [Manifold.cylinder(FLAG_SOCK + 0.01, r, r, 20).translate([x, y, z0 - FLAG_SOCK - 0.01]),
            Manifold.cylinder(CHAMF + 0.01, r, r + CHAMF + 0.01, 20).translate([x, y, z0 - CHAMF])]

def seadeck_tiles():
    """Tuiles SeaDek a plat (z = 0 a SD_T) dans le repere du bateau en plan : [(nom, tuile, surface)].
    v22 : 2 tenons dessous (z < 0), imprimees a l'envers (dessus sur le plateau, tenons vers le haut)."""
    studs = seadeck_stud_xy()
    out = []
    for side, name in ((1, "seadeck_pointe_babord"), (-1, "seadeck_pointe_tribord")):
        cs = seadeck_outline(side)
        x0, y0 = SEADECK_X0, side * (float(ys(SEADECK_X0)) - 0.07)
        ang = np.degrees(np.arctan2(side * 0.105 - y0, 7.92 - x0))
        t = Manifold.extrude(cs, SD_T) - Manifold.extrude(seadeck_grooves(cs, ang, (x0, y0)), GROOVE_D + 0.01).translate([0, 0, SD_T - GROOVE_D])
        xc, yc = bow_cleat_xy(side)
        t = t - Manifold.extrude(cleat_outline(CLR), 1.0).translate([xc, yc, -0.5])      # taquet escamotable
        out.append((name, t + _tile_studs(studs[name]), "pont"))
    cs = passage_outline()
    t = Manifold.extrude(cs, SD_T) - Manifold.extrude(border_grooves(cs, 0.025, (0.673, 0.787)), GROOVE_D + 0.01).translate([0, 0, SD_T - GROOVE_D])
    out.append(("seadeck_passage_arriere", t + _tile_studs(studs["seadeck_passage_arriere"]), "passage"))
    return out + gunwale_pads()

def place_on_surface(m, surface, sink=SD_REC):
    m = m.translate([0, 0, -sink])
    if surface == "passage":
        return m.translate([0, 0, PASS_Z])
    m = m.refine_to_length(0.08)
    return m.warp_batch(lambda p: np.column_stack([p[:, 0], p[:, 1], p[:, 2] + zs(p[:, 0])]))

def seadeck_recesses():
    cuts = []
    for side in (1, -1):
        cs = seadeck_outline(side).offset(CLR, JoinType.Round, 2.0, 24)
        cuts.append(place_on_surface(Manifold.extrude(cs, SD_REC + 0.08), "pont"))
    cs = passage_outline().offset(CLR, JoinType.Round, 2.0, 24)
    cuts.append(place_on_surface(Manifold.extrude(cs, SD_REC + 0.08), "passage"))
    return cuts + gunwale_pad_recesses() + seadeck_stud_sockets()

PLAT_R_IN = 0.20                    # coin arriere interieur (cote moteur) : grand arrondi (photo v17)

def platform_outline():
    """Plateforme de bain babord en plan : coin arriere exterieur arrondi (photos v16), coin arriere interieur
    a grand rayon (photo v17)."""
    x0, x1, y0, y1 = PLAT_BOX
    cs = rect_round_corner(x0, x1, y0, y1, x0, y1, 0.12)
    r = PLAT_R_IN
    corner = CrossSection.square([r, r]).translate([x0, y0])
    disc = CrossSection.circle(r, 48).translate([x0 + r, y0 + r])
    return (cs - corner) + (disc ^ corner)

def build_platform():
    """Plateforme de bain babord derriere le tableau ; la nacelle moteur, plus large, la porte."""
    return Manifold.extrude(platform_outline(), 0.08).translate([0, 0, PLATF_Z - 0.08])

DIAMOND_P, DIAMOND_H = 0.042, mm2m(0.2)     # tole larmee : pas 2,2 mm, relief de 0,2 mm

def diamond_zone():
    x0, x1, y0, y1 = PLAT_BOX
    z = CrossSection.square([0.40 - 0.02, 2 * BRACKET_Y - 0.06]).translate([-0.40 + 0.01, -BRACKET_Y + 0.03])
    z = z + platform_outline().offset(-0.03, JoinType.Round, 2.0, 24)
    lad = CrossSection.square([LAD2_X[1] - LAD2_X[0] + 0.10, LAD2_Y[1] - LAD2_Y[0] + 0.10]).translate([LAD2_X[0] - 0.05, LAD2_Y[0] - 0.05])
    hatch = CrossSection.circle(HATCH[2] + 0.025, 48).translate([HATCH[0], HATCH[1]])
    return z - lad - hatch

# ---- trappe de visite ronde (blanche, lisse) sur la chaise, entre la gaine babord et l'echelle (photo v17)
HATCH = (-0.20, 0.47, 0.085)          # x, y, rayon

def build_hatch():
    """Trappe ronde en leger relief (0,2 mm) avec un jonc en creux et une poignee encastree (2 fentes)."""
    x, y, r = HATCH
    h = mm2m(0.25)
    m = Manifold.cylinder(h + 0.004, r, r - 0.004, 64).translate([x, y, PLATF_Z - 0.004])
    ring = Manifold.cylinder(1.0, r - 0.014, r - 0.014, 64) - Manifold.cylinder(1.0, r - 0.014 - mm2m(0.3), r - 0.014 - mm2m(0.3), 64)
    m = m - ring.translate([x, y, PLATF_Z + h - mm2m(0.15)])
    for s in (-1, 1):
        m = m - box(x + s * 0.028 - 0.012, x + s * 0.028 + 0.012, y - 0.022, y + 0.022, PLATF_Z + h - mm2m(0.15), 1.0)
    return m

def diamond_plate():
    """Relief de tole larmee sur la plateforme et la nacelle (petits ovales alternes a +/- 45 deg)."""
    zone = diamond_zone()
    b = zone.bounds()
    bump = CrossSection.square([0.018, 0.001]).translate([-0.009, -0.0005]).offset(0.0055, JoinType.Round, 2.0, 12)
    cells = []
    i = 0
    for x in np.arange(b[0] + DIAMOND_P / 2, b[2], DIAMOND_P):
        j = 0
        for y in np.arange(b[1] + DIAMOND_P / 2, b[3], DIAMOND_P):
            cells.append(bump.rotate(45 if (i + j) % 2 == 0 else -45).translate([float(x), float(y)]))
            j += 1
        i += 1
    pat = CrossSection.batch_boolean(cells, OpType.Add) ^ zone.offset(-0.012, JoinType.Round, 2.0, 12)
    return Manifold.extrude(pat, DIAMOND_H + 0.004).translate([0, 0, PLATF_Z - 0.004])

def transom_passage_cut():
    return box(-0.6, X_CK0 + 0.03, PASS_Y[0], PASS_Y[1], PASS_Z, 3.0)

def ladder_studs():
    """2 petits tenons sur la plateforme, sous les pattes de la charniere de l'echelle."""
    import fit as F
    return [F.stud((LAD2_X[0] + 0.02, y, PLATF_Z), (0, 0, 1), LAD2_PIN_R, LAD2_PIN_H) for y in LAD2_Y]

def build_ladder(flat=True):
    """Echelle de bain inox repliee a plat sur la plateforme : 2 montants, 4 marches, charniere et pattes."""
    import fit as F
    r = LAD_R; z = PLATF_Z + r - mm2m(0.25)                  # meplat de 0,25 mm sous les tubes
    xa, xb = LAD2_X
    parts = [tube_path([(xa, y, z), (xb, y, z)], r, 14) for y in LAD2_Y]
    parts.append(tube_path([(xa, LAD2_Y[0] - 0.03, z + 0.004), (xa, LAD2_Y[1] + 0.03, z + 0.004)], r * 1.45, 16))   # charniere
    for x in LAD2_STEPS:
        parts.append(box(x - 0.024, x + 0.024, LAD2_Y[0], LAD2_Y[1], PLATF_Z + 0.004, z + 0.012))            # marches
    for y in LAD2_Y:
        parts.append(box(xa - 0.035, xa + 0.055, y - 0.03, y + 0.03, PLATF_Z, PLATF_Z + mm2m(0.7)))            # pattes
    m = Manifold.batch_boolean(parts, OpType.Add)
    m = m.trim_by_plane([0.0, 0.0, 1.0], PLATF_Z)
    for y in LAD2_Y:
        m = m - F.socket((LAD2_X[0] + 0.02, y, PLATF_Z), (0, 0, 1), LAD2_PIN_R, LAD2_PIN_H)
    return m

def cockpit_plan_ext(x0=BOW_X0 - 0.6, x1=X_CK1 + 0.6, n=240):
    """Plan des parois laterales du cockpit prolonge au-dela de la paroi avant (pour decaler les seules
    parois laterales : dossiers des cotes de la banquette avant)."""
    xs = np.linspace(x0, x1, n)
    top = [(x, w_ck(x)) for x in xs]
    return CrossSection([ccw(top + [(x, -y) for (x, y) in top[::-1]])])

def bow_return_profile(ext=0.0):
    """Profil (y, z) du retour babord, 100 % coussin : de l'interieur de l'assise jusqu'a la paroi (et
    au-dela, recoupe ensuite par le cockpit), de l'assise rigide au haut du dossier. L'angle haut-interieur
    est arrondi en quart d'ellipse qui descend presque jusqu'a l'assise. ext > 0 : profil prolonge vers le
    bas et vers la paroi (aretes qui ne doivent pas etre arrondies)."""
    xm = BOW_X0 + BOW_RET_T / 2
    yi = w_ck(xm) - BOW_SEAT_D
    y1 = w_ck(BOW_X0) + 0.10 + ext
    z0, z1 = BOW_SEAT_TOP - ext, BOW_BACK_TOP
    au, av = BOW_RET_AU, BOW_RET_AV
    arc = [(yi + au - au * np.cos(a), z1 - av + av * np.sin(a)) for a in np.linspace(np.pi / 2, 0.0, 48)]
    return CrossSection([ccw([(yi, z0), (y1, z0), (y1, z1)] + arc)])

def bow_well_end():
    xs = np.linspace(5.2, X_CK1, 400)
    hw = np.array([w_ck(x) - BOW_SEAT_D for x in xs])
    return float(xs[np.argmax(hw < 0.141)])

def bow_well():
    """Plancher en trapeze entre les assises de la banquette avant (se resserre vers l'avant)."""
    xf = bow_well_end()
    xs = np.linspace(BOW_X0 - 0.15, xf, 40)
    top = [(x, well_half(x)) for x in xs]
    pts = top + [(x, -y) for (x, y) in top[::-1]]
    cs = CrossSection([ccw(pts)])
    return Manifold.extrude(cs, 3.5)

# ------------------------------------------------------------------ details photo 3 / photo 4
LAT_X = (4.00, 4.60)       # module lateral : bloc moule blanc (boudin rond et poignee retires en v13)
LAT_D = 0.18
LAT_TOP = 0.82
U_Z = 0.60                 # hauteur de la poignee en U sur le bloc
GR_X = (4.78, 5.70)        # mains courantes inox sur les plats-bords (devant l'echelle du taud)
GR_H, GR_PIN = 0.10, 0.045
CB_Z, CB_Y = 1.24, (-0.20, -0.44)   # barre de maintien sur la console, cote passager (tribord)
CON_BACK_X = 3.30 + DXC

def lateral_face(x, side):
    return np.array([x, side * (w_ck(x) - LAT_D)])

def lateral_normal(side):
    p0, p1 = lateral_face(LAT_X[0], side), lateral_face(LAT_X[1], side)
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    n = np.array([-d[1], d[0]])
    return n if n[1] * side < 0 else -n          # vers l'axe du bateau

def lateral_block(side):
    xs = np.linspace(LAT_X[0], LAT_X[1], 12)
    pts = [(x, side * (w_ck(x) + 0.03)) for x in xs] + [(x, side * (w_ck(x) - LAT_D)) for x in xs[::-1]]
    m = Manifold.extrude(CrossSection([ccw(pts)]), LAT_TOP - FLOOR + 0.06).translate([0, 0, FLOOR - 0.06])
    return m ^ build_cockpit_cutter(0.03)

def map_plane(pts2d, origin, u, v):
    """Points (a, b) du plan (origin, u, v) -> 3D."""
    o, u, v = (np.asarray(t, float) for t in (origin, u, v))
    return [o + a * u + b * v for (a, b) in pts2d]

def lateral_handle_axis(side):
    p0, p1 = lateral_face(LAT_X[0] + 0.12, side), lateral_face(LAT_X[1] - 0.12, side)
    n = lateral_normal(side)
    return p0, p1, n

def build_u_handle(p0, p1, n, z, stand=0.07, emb=0.05, r=LAD_R, flat=True):
    """Poignee en U dans un plan horizontal : barre parallele a la face, pattes perpendiculaires."""
    q = [p0 - n * emb, p0 + n * stand, p1 + n * stand, p1 - n * emb]
    path = fillet_polyline(q, 0.03, 8)
    m = tube_path([(a, b, z) for (a, b) in path], r, 14)
    if flat:
        m = m.trim_by_plane([0.0, 0.0, 1.0], z - r + mm2m(0.25))
    return m

def u_handle_holes(p0, p1, n, z, emb=0.05, r=LAD_R):
    return [tube_path([(*(p + n * 0.01), z), (*(p - n * (emb + 0.01)), z)], r + CLR, 14) for p in (p0, p1)]

def lateral_handles():
    out = []
    for side in (1, -1):
        p0, p1, n = lateral_handle_axis(side)
        out.append(build_u_handle(p0, p1, n, U_Z))
    return out

def console_bar():
    x = CON_BACK_X
    p0, p1 = np.array([x, CB_Y[0]]), np.array([x, CB_Y[1]])
    return build_u_handle(p0, p1, np.array([-1.0, 0.0]), CB_Z)

def console_bar_holes():
    x = CON_BACK_X
    return u_handle_holes(np.array([x, CB_Y[0]]), np.array([x, CB_Y[1]]), np.array([-1.0, 0.0]), CB_Z)

def grab_rail_frame(side):
    xa, xb = GR_X
    pa = np.array([xa, side * (float(ys(xa)) - GUN / 2)])
    pb = np.array([xb, side * (float(ys(xb)) - GUN / 2)])
    u = (pb - pa) / np.linalg.norm(pb - pa)
    return pa, pb, u

def build_grab_rail(side, flat=True):
    """Main courante inox du plat-bord : 3 pattes avec tenons, coudes arrondis."""
    pa, pb, u = grab_rail_frame(side)
    Lr = float(np.linalg.norm(pb - pa)); z0 = float(zs((GR_X[0] + GR_X[1]) / 2))
    path = fillet_polyline([(0.0, -GR_PIN), (0.0, GR_H), (Lr, GR_H), (Lr, -GR_PIN)], 0.04, 8)
    U3 = np.array([u[0], u[1], 0.0]); O = np.array([pa[0], pa[1], z0])
    pts = [O + a * U3 + np.array([0, 0, b]) for (a, b) in path]
    parts = [tube_path(pts, LAD_R, 14),
             tube_path([O + Lr / 2 * U3 + np.array([0, 0, -GR_PIN]), O + Lr / 2 * U3 + np.array([0, 0, GR_H])], LAD_R, 14)]
    m = Manifold.batch_boolean(parts, OpType.Add)
    if flat:
        nrm = np.array([-u[1], u[0], 0.0])
        if nrm[1] * side < 0:
            nrm = -nrm                              # meplat cote exterieur
        c = O[:2] @ nrm[:2]
        m = m.trim_by_plane((-nrm).tolist(), float(-(c + LAD_R - mm2m(0.25))))
    return m

def grab_rail_holes():
    cuts = []
    for side in (1, -1):
        pa, pb, u = grab_rail_frame(side)
        Lr = float(np.linalg.norm(pb - pa)); z0 = float(zs((GR_X[0] + GR_X[1]) / 2))
        for a in (0.0, Lr / 2, Lr):
            p = pa + a * u
            cuts.append(Manifold.cylinder(GR_PIN + 0.3, LAD_R + CLR, LAD_R + CLR, 14).translate([p[0], p[1], z0 - GR_PIN - LAD_R - 0.01]))
    return cuts

# ------------------------------------------------------------------ pieces rapportees (une couleur chacune)
WS_POLY = [(x + CON_WS_DX, z) for (x, z) in [(4.16, 1.56), (4.24, 1.56), (4.11, 1.95), (4.03, 1.95)]]
WS_HALF = 0.40
HOOP_R = 0.03

def build_windshield():
    return extrude_xz([(x + DXC, z) for (x, z) in WS_POLY], -WS_HALF, WS_HALF)

def windshield_slot():
    cs = CrossSection([ccw([(x + DXC, z) for (x, z) in WS_POLY])]).offset(CLR, JoinType.Miter, 2.0, 0)
    return extrude_xz(cs.to_polygons()[0], -WS_HALF - CLR, WS_HALF + CLR)

def hoop_frame():
    B = np.array([4.205 + CON_WS_DX + DXC, 0.0, 1.50]); T = np.array([4.065 + CON_WS_DX + DXC, 0.0, 2.03])
    d = (T - B) / np.linalg.norm(T - B)
    return B, d, float(np.linalg.norm(T - B))

def build_hoop(flat=True):
    """Arceau inox autour du pare-brise : tube rond en U, pattes emboitees dans la console."""
    B, d, S = hoop_frame(); ey = np.array([0.0, 1.0, 0.0])
    path = fillet_polyline([(-0.48, -0.06), (-0.48, S), (0.48, S), (0.48, -0.06)], 0.12, 10)
    m = tube_path([B + a * ey + b * d for (a, b) in path], HOOP_R, 16)
    if flat:
        n = np.cross(d, ey); n = n / np.linalg.norm(n)
        m = m.trim_by_plane((-n).tolist(), float(-(B @ n + HOOP_R - mm2m(0.25))))
    return m

def hoop_slots():
    B, d, S = hoop_frame()
    return [tube_path([B + np.array([0, y, 0]) + d * -0.07, B + np.array([0, y, 0]) + d * 0.14], HOOP_R + CLR, 16) for y in (-0.48, 0.48)]

SCREENS = ((con_x(3.80), -0.17, 0.18, 0.24),)    # ecran encastre a tribord (repere console non recule)

def screen_box(i, grow=0.0, z_hi=0.012):
    xc, yc, lx, ly = SCREENS[i]
    (x0, z0), (x1, z1) = DASH
    ang = -np.degrees(np.arctan2(z1 - z0, x1 - x0))
    zc = dash_z(xc)
    return box(-lx / 2 - grow, lx / 2 + grow, -ly / 2 - grow, ly / 2 + grow, -0.02 - grow, z_hi).rotate([0, ang, 0]).translate([xc + DXC, yc, zc])

def build_screen(i):
    return screen_box(i)

# ---- console (photos v16) : ecran pose debout a babord, tableau d'interrupteurs, porte
MFD_X, MFD_Y = 2.86, 0.25           # pied de l'ecran sur le tableau de bord (repere bateau)
MFD_W, MFD_H, MFD_T, MFD_TILT = 0.32, 0.20, 0.05, 12.0
MFD_FOOT = (0.10, 0.14)             # semelle du support (x, y), posee dans son logement
MFD_REC = mm2m(1.0)                 # v22 : 0,5 -> 1 mm, semelle sur un tenon du tableau de bord

def dash_angle():
    (x0, z0), (x1, z1) = DASH
    return float(np.degrees(np.arctan2(z1 - z0, x1 - x0)))

def mfd_foot_frame():
    """Repere du logement : origine au centre de la semelle sur le tableau, axes (le long de la pente, y, normale)."""
    a = np.radians(dash_angle())
    u = np.array([np.cos(a), 0.0, np.sin(a)]); n = np.array([-np.sin(a), 0.0, np.cos(a)])
    o = np.array([MFD_X, MFD_Y, dash_z(MFD_X - DXC)])
    return o, u, np.array([0.0, 1.0, 0.0]), n

def build_mfd():
    """Ecran multifonction noir sur son support : boitier incline vers l'arriere + semelle dans le tableau."""
    o, u, v, n = mfd_foot_frame()
    T = [[u[0], v[0], n[0], o[0]], [u[1], v[1], n[1], o[1]], [u[2], v[2], n[2], o[2]]]
    fx, fy = MFD_FOOT
    foot = box(-fx / 2, fx / 2, -fy / 2, fy / 2, -MFD_REC + mm2m(0.02), 0.03).transform(T)
    scr = box(-MFD_T / 2, MFD_T / 2, -MFD_W / 2, MFD_W / 2, 0.0, MFD_H).rotate([0, MFD_TILT, 0])
    scr = scr.translate([o[0] - 0.025, o[1], o[2] + 0.045])          # rien ne depasse en arriere de l'ecran (face posee)
    arm = box(-0.035, 0.035, -0.045, 0.045, 0.0, 0.075).transform(T)
    import fit as F
    sock = F.socket(o + n * (-MFD_REC + mm2m(0.02)), n)                 # v22 : logement du tenon, sous la semelle
    return Manifold.batch_boolean([foot, scr, arm], OpType.Add) - sock

def mfd_stud():
    """v22 : tenon du tableau de bord (perpendiculaire a la pente), au fond du logement de la semelle."""
    import fit as F
    o, u, v, n = mfd_foot_frame()
    return F.stud(o - n * MFD_REC, n)

def mfd_recess():
    o, u, v, n = mfd_foot_frame()
    T = [[u[0], v[0], n[0], o[0]], [u[1], v[1], n[1], o[1]], [u[2], v[2], n[2], o[2]]]
    fx, fy = MFD_FOOT
    return box(-fx / 2 - CLR, fx / 2 + CLR, -fy / 2 - CLR, fy / 2 + CLR, -MFD_REC, 0.06).transform(T)

def mfd_down():
    """Face posee sur le plateau : le dessous de la semelle (l'ecran penche alors de ~34 deg, sans support)."""
    o, u, v, n = mfd_foot_frame()
    return tuple(-n)

SW_Y, SW_Z = (0.04, 0.44), (1.03, 1.10)       # tableau d'interrupteurs sous le volant (face arriere de console)
SW_T, SW_REC = mm2m(1.8), mm2m(1.5)           # v22 : plus epais, logement plus profond (depasse toujours de 0,3 mm)
CON_AFT_X = 3.30 + DXC                         # face arriere de la console

def sw_stud_uv():
    """v22 : 2 mini-tenons de la console, dans les trous du dos du tableau (aux deux bouts)."""
    W = SW_Y[1] - SW_Y[0]; H = SW_Z[1] - SW_Z[0]
    return [(0.055, H / 2), (W - 0.055, H / 2)]

def switch_studs():
    """Mini-tenons sur le fond du logement de la console, vers l'arriere (-x) : ils restent dans le logement."""
    import fit as F
    x_in = CON_AFT_X + SW_REC - mm2m(0.02)
    return [F.stud((x_in, SW_Y[1] - u, SW_Z[0] + v), (-1.0, 0.0, 0.0), r=F.STUD_S_R, h=F.STUD_S_H) for (u, v) in sw_stud_uv()]

def switch_recess():
    return box(CON_AFT_X - 0.01, CON_AFT_X + SW_REC, SW_Y[0] - CLR, SW_Y[1] + CLR, SW_Z[0] - CLR, SW_Z[1] + CLR)

def build_switch_flat():
    """Tableau d'interrupteurs a plat (u = y, v = z, w = epaisseur) : 7 basculeurs + 2 boutons ronds.
    v22 : 2 trous au dos (le 2e oblong) pour les mini-tenons de la console ; imprime a plat, basculeurs vers le haut."""
    import fit as F
    W = SW_Y[1] - SW_Y[0]; H = SW_Z[1] - SW_Z[0]
    parts = [box(0, W, 0, H, 0, SW_T)]
    for k in range(7):
        u = 0.035 + k * 0.040
        parts.append(box(u - 0.012, u + 0.012, 0.016, H - 0.016, SW_T - 0.002, SW_T + 0.010))
    for u in (W - 0.075, W - 0.035):
        parts.append(Manifold.cylinder(0.012, 0.014, 0.012, 20).translate([u, H / 2, SW_T - 0.002]))
    holes = F.stud_pair_sockets([(u, v, 0.0) for (u, v) in sw_stud_uv()], (0.0, 0.0, 1.0), r=F.STUD_S_R, h=F.STUD_S_H)
    return Manifold.batch_boolean(parts, OpType.Add) - Manifold.batch_boolean(holes, OpType.Add)

def place_switch(m):
    x_in = CON_AFT_X + SW_REC - mm2m(0.02)
    # u -> -y (on lit le tableau depuis l'arriere : u croissant vers tribord), v -> z, w -> -x
    return m.transform([[0, 0, -1, x_in], [-1, 0, 0, SW_Y[1]], [0, 1, 0, SW_Z[0]]])

DOOR_Y, DOOR_Z = (-0.03, 0.42), (0.56, 0.97)   # porte de console (contour en creux) sous les interrupteurs
DOOR_G, DOOR_D = mm2m(0.6), mm2m(0.4)

def door_groove():
    cs = CrossSection.square([DOOR_Y[1] - DOOR_Y[0], DOOR_Z[1] - DOOR_Z[0]]).translate([DOOR_Y[0], DOOR_Z[0]])
    cs = cs.offset(-0.04, JoinType.Round, 2.0, 16).offset(0.04, JoinType.Round, 2.0, 16)
    ring = cs - cs.offset(-DOOR_G, JoinType.Round, 2.0, 16)
    handle = CrossSection.square([0.07, 0.03]).translate([DOOR_Y[1] - 0.12, (DOOR_Z[0] + DOOR_Z[1]) / 2])
    m = Manifold.extrude(ring + handle, DOOR_D + 0.01)          # (X=y, Y=z, Z=profondeur)
    return m.transform([[0, 0, 1, CON_AFT_X - 0.01], [1, 0, 0, 0], [0, 1, 0, 0]])

def screen_recesses():
    return [screen_box(i, CLR, 0.06) for i in range(len(SCREENS))]

PED_PIN = mm2m(1.0)

def build_pedestal(s, pin_hole=False):
    """Pied de fauteuil alu : embase, colonne, platine ; teton en haut. En bas : logement pour le tenon
    du socle (ajoute dans pieces.py) ; pin_hole=True redonne l'ancien trou de goupille."""
    cx, cy = SEAT_X, s * SEAT_Y
    parts = [Manifold.cylinder(0.02, 0.11, 0.105, 40),
             Manifold.cylinder(PED_H - 0.065, 0.045, 0.045, 28).translate([0, 0, 0.015]),
             Manifold.cylinder(0.055, 0.045, 0.10, 40).translate([0, 0, PED_H - 0.055]),
             Manifold.cylinder(PIN_H + 0.005, PIN_R, PIN_R, 24).translate([0, 0, PED_H - 0.005])]
    m = Manifold.batch_boolean(parts, OpType.Add)
    if pin_hole:
        m = m - Manifold.cylinder(0.10, PED_PIN, PED_PIN, 16).translate([0, 0, -0.01])
    return m.translate([cx, cy, PLAT_TOP])

def pedestal_holes():
    return [Manifold.cylinder(0.12, PED_PIN, PED_PIN, 16).translate([SEAT_X, s * SEAT_Y, PLAT_TOP - 0.11]) for s in (1, -1)]

def interior_parts():
    """Elements du cockpit, par couleur (unis a la coque pour l'impression)."""
    P = {}
    grown = build_cockpit_cutter(0.03)          # vide du cockpit elargi dans la matiere (pas de faces coincidentes)
    cp = console_parts(DXC)
    P["console"], P["siege_avant_base"] = cp["console"], cp["siege_avant_base"]
    # --- poste de pilotage : socle + 2 pieds de fauteuils coquilles
    plat = Manifold.extrude(CrossSection.square([PLAT_X[1] - PLAT_X[0] - 0.12, 1.28 - 0.12]).translate([PLAT_X[0] + 0.06, -0.64 + 0.06])
                            .offset(0.06, JoinType.Round, 2.0, 24), PLAT_TOP - FLOOR + 0.06).translate([0, 0, FLOOR - 0.06])
    peds = []
    for s in (-1, 1):
        cx, cy = SEAT_X, s * SEAT_Y
        peds.append(Manifold.cylinder(0.02, 0.11, 0.11, 32).translate([cx, cy, PLAT_TOP - 0.005]))
        peds.append(Manifold.cylinder(PED_H - 0.055, 0.045, 0.045, 24).translate([cx, cy, PLAT_TOP]))
        peds.append(Manifold.cylinder(0.055, 0.045, 0.10, 32).translate([cx, cy, PLAT_TOP + PED_H - 0.055]))
        peds.append(Manifold.cylinder(PIN_H + 0.005, PIN_R, PIN_R, 20).translate([cx, cy, SEAT_Z - 0.005]))
    P["socle_pilote"] = plat
    # --- banquettes arriere : haute + basse devant, marche a babord
    P["banquette_haute"] = box(X_CK0 - 0.05, BENCH_HI_X[1], -1.4, STEP_Y, FLOOR - 0.06, BENCH_HI_TOP) ^ grown
    P["banquette_basse"] = box(BENCH_LO_X[0] - 0.01, BENCH_LO_X[1], -1.4, STEP_Y, FLOOR - 0.06, BENCH_LO_TOP) ^ grown
    P["dossier_haut"] = back_hi_board() ^ build_cockpit_cutter(0.06)
    P["marche"] = box(X_CK0 - 0.05, BENCH_HI_X[1], STEP_Y - 0.001, 1.4, FLOOR - 0.06, PASS_Z) ^ grown
    P["marche_2"] = box(STEP2_X[0] - 0.001, STEP2_X[1], STEP_Y - 0.001, 1.4, FLOOR - 0.06, STEP2_Z) ^ grown
    # --- blocs lateraux (photo 3)
    P["blocs_lateraux"] = lateral_block(1) + lateral_block(-1)
    # --- banquette en U a l'avant (assise rigide, coussins faits main)
    well = bow_well()
    P["banquette_avant_base"] = ((box(BOW_X0, X_CK1 + 0.05, -1.4, 1.4, -1.0, BOW_SEAT_TOP) ^ grown) - well) ^ shell_cached()
    return P

def build_interior(hull_full=None):
    return Manifold.batch_boolean(list(interior_parts().values()), OpType.Add)

BRACKET_LOW_Y = 0.60                # demi-largeur du caisson de la chaise sous le pont (v17)
BRACKET_SLAB_Z = 0.66               # dessous du pont de la chaise, pleine largeur : les flaps et leurs verins dessous

def build_bracket():
    """Chaise moteur (v17) : caisson central qui porte les moteurs, pont en tole larmee pleine largeur a la
    hauteur de la plateforme ; de chaque cote, sous le pont, le tableau reste libre pour les flaps."""
    prof = [(0.02, 0.25), (0.02, PLATF_Z), (-0.40, PLATF_Z), (-0.40, 0.45), (-0.22, 0.25)]
    low = extrude_xz(prof, -BRACKET_LOW_Y, BRACKET_LOW_Y)
    slab = box(-0.40, 0.02, -BRACKET_Y, BRACKET_Y, BRACKET_SLAB_Z, PLATF_Z)
    return low + slab

# ---- flaps (trim tabs) inox au bas du tableau, sous le pont de la chaise, avec leur verin noir (photo v17)
TAB_Y = (0.63, 0.97)                # envergure cote babord (le tribord est symetrique)
TAB_C, TAB_T = 0.24, 0.016          # corde (vers l'arriere), epaisseur
TAB_DOWN = 3.0                      # braquage sous la carene (deg)
TAB_HINGE = (0.03, 0.05)            # charniere sur le dessus du flap : profondeur (x), hauteur
TAB_PEG_R, TAB_PEG_L = mm2m(0.6), mm2m(1.2)
ACT_Y, ACT_Z, ACT_W, ACT_H = 0.80, 0.50, 0.05, 0.04   # verin : fixation haute sur le tableau ; section

def tab_frame(side=1):
    """Repere du flap : origine au bord d'attaque (contre le tableau, bout interieur), e1 le long de la
    charniere (vers l'exterieur), e2 vers l'arriere (braque), e3 normale vers le haut."""
    y0, y1 = TAB_Y
    P0 = np.array([0.0, y0, float(zbot(0.0, y0))]); P1 = np.array([0.0, y1, float(zbot(0.0, y1))])
    e1 = (P1 - P0) / np.linalg.norm(P1 - P0)
    a = np.radians(TAB_DOWN)
    e2 = np.array([-np.cos(a), 0.0, -np.sin(a)]); e2 = e2 - (e2 @ e1) * e1; e2 /= np.linalg.norm(e2)
    e3 = np.cross(e1, e2)
    if e3[2] < 0:
        e3 = -e3
    O = P0 + np.array([-mm2m(0.1), 0.0, 0.0])
    if side < 0:
        O, e1, e2, e3 = (np.array([v[0], -v[1], v[2]]) for v in (O, e1, e2, e3))
    return O, e1, e2, e3

def _tab_T(side=1):
    O, e1, e2, e3 = tab_frame(side)
    return [[e1[0], e2[0], e3[0], O[0]], [e1[1], e2[1], e3[1], O[1]], [e1[2], e2[2], e3[2], O[2]]]

def tab_span():
    y0, y1 = TAB_Y
    return float(np.linalg.norm([y1 - y0, float(zbot(0.0, y1)) - float(zbot(0.0, y0))]))

def _tab_peg_pts():
    S = tab_span()
    return [(S * f, mm2m(0.1), TAB_T + TAB_HINGE[1] / 2) for f in (0.22, 0.78)]

def build_tab_local():
    """Flap a plat (repere local : u le long de la charniere, v vers l'arriere, w vers le haut) : plaque, charniere,
    2 tenons vers l'avant (dans le tableau), logement du pied de verin."""
    S = tab_span()
    plate = CrossSection.square([S, TAB_C]).offset(-0.02, JoinType.Round, 2.0, 12).offset(0.02, JoinType.Round, 2.0, 12)
    parts = [Manifold.extrude(plate, TAB_T)]
    parts.append(box(0.03, S - 0.03, 0.0, TAB_HINGE[0], 0.0, TAB_T + TAB_HINGE[1]))
    for (u, v, w) in _tab_peg_pts():
        parts.append(Manifold.cylinder(TAB_PEG_L + mm2m(0.2), TAB_PEG_R, TAB_PEG_R, 16).rotate([90, 0, 0]).translate([u, v + mm2m(0.2), w]))
    parts.append(tab_cradle_local())                                  # v22 : berceau du pied de verin
    m = Manifold.batch_boolean(parts, OpType.Add)
    return m

TAB_CRADLE = (mm2m(0.15), mm2m(0.5), mm2m(0.5))    # v22 : jeu, epaisseur et hauteur du berceau du pied de verin

def tab_cradle_local():
    """v22 : berceau en U sur le dessus du flap, ouvert vers le tableau. Le pied du verin s'y loge quand on pousse le
    flap contre le tableau (le verin deja tenu par son tenon du haut) : il ne peut plus ressortir, plus de colle."""
    T = _tab_T(1)
    R = np.array([r[:3] for r in T]); t = np.array([r[3] for r in T])
    Ti = np.hstack([R.T, (-R.T @ t)[:, None]]).tolist()
    u0, v0, u1, v1 = build_actuator(1).transform(Ti).slice(TAB_T + mm2m(0.1)).bounds()
    c, e, h = TAB_CRADLE
    va = v0 + 0.3 * (v1 - v0)
    z0, z1 = TAB_T - mm2m(0.05), TAB_T + h
    return Manifold.batch_boolean([box(u0 - c - e, u0 - c, va, v1 + c + e, z0, z1),
                                   box(u1 + c, u1 + c + e, va, v1 + c + e, z0, z1),
                                   box(u0 - c - e, u1 + c + e, v1 + c, v1 + c + e, z0, z1)], OpType.Add)

def tab_holes():
    """Trous des tenons des flaps dans le tableau (2 par flap)."""
    holes = []
    for side in (1, -1):
        T = _tab_T(side)
        for (u, v, w) in _tab_peg_pts():
            h = Manifold.cylinder(TAB_PEG_L + mm2m(0.6), TAB_PEG_R + CLR, TAB_PEG_R + CLR, 16).rotate([90, 0, 0]).translate([u, v + mm2m(0.3), w])
            holes.append(h.transform(T))
    return holes

def place_tab(m, side=1):
    return m.transform(_tab_T(side))

def _act_ends(side=1):
    O, e1, e2, e3 = tab_frame(1)
    u = (ACT_Y - TAB_Y[0]) / (TAB_Y[1] - TAB_Y[0]) * tab_span()
    foot = O + u * e1 + 0.60 * TAB_C * e2 + TAB_T * e3
    top = np.array([0.0, ACT_Y, ACT_Z])
    if side < 0:
        foot = np.array([foot[0], -foot[1], foot[2]]); top = np.array([0.0, -ACT_Y, ACT_Z])
    return top, foot

def build_actuator(side=1):
    """Verin electrique noir : corps rectangulaire arrondi du tableau au flap, tenon dans le tableau.
    Plan (x, z) : imprime couche sur le flanc, meplat de chaque cote."""
    top, foot = _act_ends(side)
    O, e1, e2, e3 = tab_frame(side)
    a = np.array([top[0] + 0.02, top[2]]); b = np.array([foot[0], foot[2]])        # axe du verin dans le plan (x, z)
    d = (b - a) / np.linalg.norm(b - a); nrm = np.array([-d[1], d[0]])
    h = ACT_H / 2 - 0.008
    poly = [a + nrm * h, b + nrm * h, b - nrm * h, a - nrm * h]
    cs = CrossSection([ccw(poly)]).offset(0.008, JoinType.Round, 2.0, 12)
    body = extrude_xz([tuple(p) for p in cs.to_polygons()[0]], top[1] - ACT_W / 2, top[1] + ACT_W / 2)
    body = body.trim_by_plane([-1.0, 0.0, 0.0], mm2m(0.02))                         # contre le tableau
    body = body.trim_by_plane(list(e3), float(e3 @ foot) + mm2m(0.02))              # pose sur le flap
    peg = cyl_x(-0.01, TAB_PEG_L, top[1], top[2], TAB_PEG_R, 16)
    return body + peg

def actuator_holes():
    return [cyl_x(-0.005, TAB_PEG_L + mm2m(0.4), s * ACT_Y, ACT_Z, TAB_PEG_R + CLR, 16) for s in (1, -1)]

# ------------------------------------------------------------------ armature du taud (tubes ronds, sur les plats-bords)
# D'apres les 2 photos sur l'eau (camera recalee sur la coque) : de chaque cote une echelle inclinee
# vers l'avant, a cote des fauteuils (2 tubes qui se rapprochent en haut, echelons paralleles au
# plat-bord), un montant arriere qui descend du coin arriere du taud jusqu'au premier echelon, et un
# rail lateral a ~2,30 m qui remonte doucement a l'avant. Le taud couvre la console et le poste de
# pilotage : de x = 1,53 m (derriere les fauteuils) a 3,99 m (au-dessus du siege avant de console).
TUBE = 0.065                 # diametre des tubes (3,4 mm a l'echelle)
TR = TUBE / 2
Z_RAIL = 2.37                # axe du rail lateral (calé sur ton tracé jaune)
FRAME_Y = 1.07               # plan des cadres lateraux : au milieu du plat-bord
FLAT = mm2m(0.35)            # meplat d'impression (face posee sur le plateau)
SOCK_D = mm2m(2.6)           # longueur des tenons / profondeur des logements dans le plat-bord
CLR = mm2m(0.2)              # jeu d'emboitement
KEY = mm2m(0.4)              # detrompeur : le tenon arriere est plus fin que le tenon avant
CHAMF = mm2m(0.4)            # chanfrein d'entree des logements
NOTCH_D = mm2m(0.6)          # profondeur des encoches du rail ou se posent les arceaux
LAD_FOOT = (2.42, 1.80)      # pieds de l'echelle sur le plat-bord : tube avant, tube arriere
LAD_TOP = (3.29, 2.88)       # hauts des tubes, sous le rail
FOOT_H = 0.06                # embase verticale au pied des tubes
RUNGS_DZ = (0.31, 0.60, 0.88)     # echelons : hauteur au-dessus du plat-bord (paralleles a lui)
X_REAR = 1.55                # coin arriere du cadre (haut du montant arriere)
Z_LOW = 2.20                 # rail bas : du tube arriere au montant arriere
RC_REAR = 0.07
X_SWEEP0, X_RAIL_F, SWEEP = 3.62, 4.06, 0.11    # le rail remonte de 11 cm vers l'avant (courbe de la photo)
TUBE_SEG = 18

def capsule(p, q, r, seg=TUBE_SEG):
    return Manifold.batch_hull([Manifold.sphere(r, seg).translate(list(map(float, p))),
                                Manifold.sphere(r, seg).translate(list(map(float, q)))])

def tube_path(pts, r=TR, seg=TUBE_SEG):
    pts = [np.asarray(p, float) for p in pts]
    return Manifold.batch_boolean([capsule(pts[i], pts[i + 1], r, seg) for i in range(len(pts) - 1)], OpType.Add)

def fillet_polyline(pts2d, R, n=10):
    """Polyligne 2D dont les sommets interieurs sont arrondis (rayon R)."""
    P = [np.asarray(p, float) for p in pts2d]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        u = (a - b) / np.linalg.norm(a - b); v = (c - b) / np.linalg.norm(c - b)
        ang = np.arccos(np.clip(np.dot(u, v), -1, 1))
        t = R / np.tan(ang / 2)
        p1 = b + u * t; p2 = b + v * t
        bis = (u + v) / np.linalg.norm(u + v)
        cen = b + bis * (R / np.sin(ang / 2))
        a1 = np.arctan2(p1[1] - cen[1], p1[0] - cen[0]); a2 = np.arctan2(p2[1] - cen[1], p2[0] - cen[0])
        d = (a2 - a1 + np.pi) % (2 * np.pi) - np.pi
        for k in range(n + 1):
            ak = a1 + d * k / n
            out.append(cen + R * np.array([np.cos(ak), np.sin(ak)]))
    out.append(P[-1])
    return out

def rail_z(x):
    """Hauteur de l'axe du rail : droite, puis remontee douce (cosinus) a l'avant."""
    t = np.clip((np.asarray(x, float) - X_SWEEP0) / (X_RAIL_F - X_SWEEP0), 0, 1)
    return Z_RAIL + SWEEP * (1 - np.cos(np.pi * t)) / 2

def lad_line(i):
    """Partie inclinee du tube i de l'echelle (0 = avant, 1 = arriere) : du haut de l'embase au rail."""
    xf = LAD_FOOT[i]
    return np.array([xf, float(zs(xf)) + FOOT_H]), np.array([LAD_TOP[i], Z_RAIL])

def lad_point(i, dz):
    """Point du tube i situe a dz au-dessus du plat-bord (a son aplomb)."""
    p0, p1 = lad_line(i)
    lo, hi = 0.0, 1.0
    for _ in range(60):
        t = (lo + hi) / 2
        p = p0 + t * (p1 - p0)
        if p[1] - float(zs(p[0])) < dz:
            lo = t
        else:
            hi = t
    return p0 + lo * (p1 - p0)

def frame_feet():
    """Pieds (x, z) sur le plat-bord : tube avant, tube arriere."""
    return [(x, float(zs(x))) for x in LAD_FOOT]

def frame_paths():
    """Lignes d'axe (x, z) d'un cadre lateral : 2 tubes d'echelle inclines vers l'avant, 3 echelons
    paralleles au plat-bord, montant arriere + rail lateral qui remonte a l'avant."""
    paths = []
    for i in (0, 1):
        xf = LAD_FOOT[i]; zf = float(zs(xf))
        p0, p1 = lad_line(i)
        paths.append(fillet_polyline([(xf, zf + TR + 0.002), tuple(p0), tuple(p1)], 0.05, 8))
    J = lad_point(1, RUNGS_DZ[0])                   # le montant arriere arrive sur le 1er echelon
    rail = fillet_polyline([tuple(J), (X_REAR, Z_RAIL), (X_SWEEP0, Z_RAIL)], RC_REAR, 10)
    rail += [(x, float(rail_z(x))) for x in np.linspace(X_SWEEP0, X_RAIL_F, 12)[1:]]
    paths.append(rail)
    for dz in RUNGS_DZ:
        paths.append([tuple(lad_point(1, dz)), tuple(lad_point(0, dz))])
    paths.append(low_rail())
    return paths

def low_rail():
    """Rail bas (photo) : du tube arriere de l'echelle au montant arriere, a Z_LOW."""
    p0, p1 = lad_line(1)
    a = p0 + (Z_LOW - p0[1]) / (p1[1] - p0[1]) * (p1 - p0)
    J = lad_point(1, RUNGS_DZ[0]); top = np.array([X_REAR, Z_RAIL])
    b = top + (Z_LOW - top[1]) / (J[1] - top[1]) * (J - top)
    return [tuple(a), tuple(b)]

def ladder_box(side, grow=0.0):
    """Boitier blanc (spot / haut-parleur) entre les 2 tubes, du 3e barreau au rail. Volume plein,
    cote interieur du cadre ; ses rainures epousent les 4 tubes qui l'entourent."""
    y = side * FRAME_Y
    q = [lad_point(1, RUNGS_DZ[2]), lad_point(0, RUNGS_DZ[2]), np.array([LAD_TOP[0], Z_RAIL]), np.array([LAD_TOP[1], Z_RAIL])]
    cs = CrossSection([ccw([tuple(p) for p in q])]).offset(grow, JoinType.Miter, 2.0, 0)
    pts = cs.to_polygons()[0]
    y0, y1 = sorted([y - side * (BOX_T + grow), y + side * (0.006 + grow)])
    return extrude_xz(pts, y0, y1)

BOX_T = 0.09                 # epaisseur du boitier (vers l'interieur du bateau)

def build_ladder_box(side):
    """Boitier imprime en blanc : le cadre (tubes + jeu) est retranche -> 4 rainures de positionnement."""
    b = ladder_box(side)
    y = side * FRAME_Y
    tubes = []
    for path in frame_paths():
        tubes.append(tube_path([(x, y, z) for (x, z) in path], TR + CLR))
    return b - Manifold.batch_boolean(tubes, OpType.Add)

def tenon_r(i):
    return TR if i == 0 else TR - KEY

def rail_notch(xa, side):
    zt = float(rail_z(xa)) + TR - NOTCH_D
    return box(xa - TR - CLR, xa + TR + CLR, side * FRAME_Y - 0.2, side * FRAME_Y + 0.2, zt, zt + 0.5)

def build_frame(side, flat=True):
    y = side * FRAME_Y
    parts = [tube_path([(x, y, z) for (x, z) in path]) for path in frame_paths()]
    for i, (x, z) in enumerate(frame_feet()):
        parts.append(Manifold.cylinder(TR + 0.012, TR, TR, TUBE_SEG).translate([x, y, z]))                 # embase
        parts.append(Manifold.cylinder(SOCK_D + 0.002, tenon_r(i), tenon_r(i), TUBE_SEG).translate([x, y, z - SOCK_D]))
    m = Manifold.batch_boolean(parts, OpType.Add)
    for xa in tuple(ARCH_X) + (FRONT_X,):        # encoches qui recoivent les arceaux
        m = m - rail_notch(xa, side)
    if flat:                                     # meplat cote exterieur pour imprimer a plat sans support
        m = m.trim_by_plane([0.0, -float(side), 0.0], -(FRAME_Y + TR - FLAT))
    return m

def tt_sockets():
    """Logements ronds (entree chanfreinee) dans le plat-bord pour les tenons des cadres."""
    cut = []
    for s in (-1, 1):
        for i, (x, z) in enumerate(frame_feet()):
            r = tenon_r(i) + CLR
            cut.append(Manifold.cylinder(SOCK_D + 0.01, r, r, TUBE_SEG).translate([x, s * FRAME_Y, z - SOCK_D]))
            cut.append(Manifold.cylinder(CHAMF + 0.01, r, r + CHAMF + 0.01, TUBE_SEG).translate([x, s * FRAME_Y, z - CHAMF]))
    return cut

# ---- arceaux du taud : ronds, pieds plats poses dans les encoches du rail
ARCH_X = (1.72, 2.48, 3.24)          # 3 arceaux bombes sur la partie droite du rail
ARCH_RAD = 0.12                      # rayon des angles (dessus plat, bords arrondis)
FRONT_X, FRONT_RAD = 4.00, 0.04      # arceau avant, plus plat, sur le rail releve
TAUD_TOP = Z_RAIL + 0.18             # axe du dessus des arceaux
TAUD_X = (1.54, 4.055)               # etendue de la toile : console + poste de pilotage

def arch_axis(front=False, n=14):
    xa = FRONT_X if front else ARCH_X[0]
    zb = float(rail_z(xa)) + TR - NOTCH_D          # fond de l'encoche
    rad = FRONT_RAD if front else ARCH_RAD
    path = fillet_polyline([(-FRAME_Y, zb - 0.03), (-FRAME_Y, TAUD_TOP), (FRAME_Y, TAUD_TOP), (FRAME_Y, zb - 0.03)], rad, n)
    return path, zb

def yz_to_x(m, x0):
    """Profil extrude (X=y, Y=z, Z=epaisseur) -> repere bateau, epaisseur le long de x a partir de x0."""
    return m.transform([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]])

def build_arch(x=0.0, front=False, flat=True):
    path, zb = arch_axis(front)
    m = tube_path([(x, y, z) for (y, z) in path])
    m = m.trim_by_plane([0.0, 0.0, 1.0], zb)         # pieds plats, poses au fond des encoches
    if flat:
        m = m.trim_by_plane([1.0, 0.0, 0.0], x - TR + FLAT)
    return m

def build_canopy():
    """Les 4 arceaux en place (pour l'assemblage)."""
    return Manifold.batch_boolean([build_arch(x) for x in ARCH_X] + [build_arch(FRONT_X, True)], OpType.Add)

def path_band_line(pts, o):
    pts = np.asarray(pts, float)
    d = np.gradient(pts, axis=0); d /= np.linalg.norm(d, axis=1)[:, None]
    return pts + o * np.stack([d[:, 1], -d[:, 0]], 1)

def taud_station(x, n=14, ext=0.0):
    """Ligne d'axe (y, z) du support de toile a l'abscisse x : bords sur le rail, dessus plat,
    angles arrondis ; extremites avant et arriere qui s'enroulent vers le bas. ext : rabat sous l'axe du rail."""
    s = float(rail_z(x))
    top = TAUD_TOP
    xr = ARCH_X[0]; Rr = TAUD_TOP - Z_RAIL
    if x < xr:                                       # arriere : quart de cercle jusqu'au rail
        top = Z_RAIL + np.sqrt(max(Rr ** 2 - (xr - x) ** 2, 0.0))
    zf = float(rail_z(FRONT_X)) + 0.02; Rf = TAUD_TOP - zf
    if x > FRONT_X:                                  # avant : enroulement sur l'arceau avant
        top = zf + np.sqrt(max(Rf ** 2 - (x - FRONT_X) ** 2, 0.0))
    top = max(top, s + 0.014)
    t = np.clip((x - X_SWEEP0) / (FRONT_X - X_SWEEP0), 0, 1)
    rad = ARCH_RAD + (FRONT_RAD - ARCH_RAD) * t
    rad = float(np.clip(rad, 0.006, 0.9 * (top - s)))
    pts = fillet_polyline([(-FRAME_Y, s), (-FRAME_Y, top), (FRAME_Y, top), (FRAME_Y, s)], rad, n)
    if ext > 0:
        pts = [np.array([-FRAME_Y, s - ext])] + list(pts) + [np.array([FRAME_Y, s - ext])]
    return pts

def taud_stations():
    x0, x1 = TAUD_X
    xs = np.unique(np.r_[np.linspace(x0, ARCH_X[0], 16), np.linspace(ARCH_X[0], FRONT_X, 40), np.linspace(FRONT_X, x1, 10)])
    return xs

def build_taud_fabric(th=0.015, n=14, ext=0.0):
    """Toile posee sur les arceaux et les rails (apercu, non imprimee)."""
    secs = []
    for x in taud_stations():
        p = np.array(taud_station(x, n, ext))
        outer = path_band_line(p, -(TR + th)); inner = path_band_line(p, -TR)
        poly = np.vstack([outer, inner[::-1]])
        secs.append(np.column_stack([np.full(len(poly), x), poly]))
    return loft(secs)

TAUD_PRINT_T = mm2m(1.0)             # epaisseur du taud imprime (option)
CLIP_Y = (-0.55, 0.55)               # clips sous le taud, sur le dessus plat de chaque arceau
CLIP_W, CLIP_WALL, CLIP_OPEN = mm2m(4.0), mm2m(0.8), np.radians(47)
# v20 : taud imprime en TPU 90A noir souple. Imprime A PLAT (gabarit deplie de la toile), sans support : la feuille
# se plie sur les arceaux comme la toile. 8 clips sur le dessus des arceaux, 6 sur les rails qui tiennent les rabats
# lateraux. Un TPU plat ne s'enroulerait pas tout seul vers l'arriere (et le coude du cadre ne laisse pas la place
# d'un clip) : la feuille s'arrete 3,5 cm derriere le dernier arceau.
TAUD_FLAP = mm2m(3.2)                # la feuille descend sous l'axe du rail : le clip de rail est pose dessus
RAIL_CLIPS = ((2.12, CLIP_W), (2.70, CLIP_W), (3.52, CLIP_W))       # (x, largeur) des clips de rail
RAIL_CLIP_X = tuple(x for x, w in RAIL_CLIPS)
TAUD_TPU_TAIL = 0.035                # la feuille TPU depasse de 3,5 cm derriere le dernier arceau

def _clip_cs():
    r_in = TR + mm2m(0.15); r_out = r_in + CLIP_WALL
    ring = (CrossSection.circle(r_out, 40) - CrossSection.circle(r_in, 40))
    a = CLIP_OPEN; R = 2 * r_out
    wedge = CrossSection([ccw([(0.0, 0.0), (R * np.sin(a), -R * np.cos(a)), (R * np.sin(a), -R), (-R * np.sin(a), -R),
                               (-R * np.sin(a), -R * np.cos(a))])])            # sens trigo, sinon le coin est vide
    return ring - wedge                                       # ouverture vers -Y du profil

def rail_clip(x0, side=1, w=CLIP_W):
    """Clip en C sur le rail lateral (axe selon x), ouverture vers l'interieur du bateau, sous le rabat du taud."""
    m = Manifold.extrude(_clip_cs(), w).translate([0, 0, -w / 2])
    z0 = float(rail_z(x0))
    if side > 0:
        return m.transform([[0, 0, 1, x0], [0, 1, 0, FRAME_Y], [-1, 0, 0, z0]])
    return m.transform([[0, 0, 1, x0], [0, -1, 0, -FRAME_Y], [1, 0, 0, z0]])

def taud_clip(xa, y):
    """Clip en C sous le taud, qui se clipse sur le tube de l'arceau (axe le long de y, a TAUD_TOP)."""
    m = Manifold.extrude(_clip_cs(), CLIP_W).translate([0, 0, -CLIP_W / 2])      # profil (x, z), epaisseur selon y
    return m.transform([[1, 0, 0, xa], [0, 0, 1, y], [0, 1, 0, TAUD_TOP]])

def build_taud_print(n=14):
    """Taud imprime (option) en place sur l'armature : forme de la toile avec ses rabats, 1 mm, 8 clips sur les
    arceaux et 8 sur les rails (pour l'assemblage et les controles ; on imprime la feuille plate build_taud_flat)."""
    shell = build_taud_fabric(th=TAUD_PRINT_T, n=n, ext=TAUD_FLAP)
    shell = shell.trim_by_plane([1.0, 0.0, 0.0], ARCH_X[0] - TAUD_TPU_TAIL)
    clips = [taud_clip(xa, y) for xa in tuple(ARCH_X) + (FRONT_X,) for y in CLIP_Y]
    clips += [rail_clip(x, sd, w) for x, w in RAIL_CLIPS for sd in (1, -1)]
    return Manifold.batch_boolean([shell] + clips, OpType.Add)

def build_taud_flat(n=30):
    """Feuille plate a imprimer en TPU (dessus sur le plateau, clips vers le haut, sans support) : gabarit deplie de la
    toile (u le long du taud, v en travers), rabats sous les rails, clips d'arceaux (axe selon v) et de rails (axe selon u)."""
    T = TAUD_PRINT_T
    u, hw, marks = taud_development(T, n)
    hw = hw + TAUD_FLAP
    xs = taud_stations()
    u0 = float(np.interp(ARCH_X[0] - TAUD_TPU_TAIL, xs, u))          # bord arriere de la feuille
    keep = u > u0
    uu = np.r_[u0, u[keep]]; hh = np.r_[float(np.interp(u0, u, hw)), hw[keep]]
    poly = [(a, b) for a, b in zip(uu, hh)] + [(a, -b) for a, b in zip(uu[::-1], hh[::-1])]
    sheet = Manifold.extrude(CrossSection([ccw(poly)]), T)
    zc = T + TR                                               # axe des tubes : a TR de la face interieure
    clip = Manifold.extrude(_clip_cs(), CLIP_W).translate([0, 0, -CLIP_W / 2])
    parts = [sheet]
    for um in marks:
        for v0 in CLIP_Y:
            parts.append(clip.transform([[1, 0, 0, um], [0, 0, 1, v0], [0, -1, 0, zc]]))
    for x, w in RAIL_CLIPS:
        u0 = float(np.interp(x, xs, u)); h0 = float(np.interp(u0, u, hw)) - TAUD_FLAP
        rc = Manifold.extrude(_clip_cs(), w).translate([0, 0, -w / 2])
        for sd in (1, -1):
            parts.append(rc.transform([[0, 0, 1, u0], [-1, 0, 0, sd * h0], [0, -1, 0, zc]]))
    return Manifold.batch_boolean(parts, OpType.Add)

def taud_development(th=0.015, n=30):
    """Gabarit deplie de la toile : [(u, demi-largeur)] le long de l'axe, et u des arceaux."""
    xs = taud_stations()
    tops, widths = [], []
    for x in xs:
        p = path_band_line(np.array(taud_station(x, n)), -(TR + th / 2))
        widths.append(float(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1))))
        tops.append(p[len(p) // 2, 1])
    tops = np.array(tops)
    u = np.r_[0, np.cumsum(np.hypot(np.diff(xs), np.diff(tops)))]
    marks = [float(np.interp(xa, xs, u)) for xa in tuple(ARCH_X) + (FRONT_X,)]
    return u, np.array(widths) / 2, marks

# ------------------------------------------------------------------ pare-battages accroches au T-top (photos v16)
FENDER_X, FENDER_YS = 2.48, (-0.22, -0.42)    # sous le 2e arceau, devant le fauteuil tribord
FENDER_R, FENDER_L, FENDER_ROPE = 0.085, 0.42, 0.06
FENDER_CLIP_W = 0.06

def build_fender(y):
    """Pare-battage noir : clip ouvert vers le haut sur le tube de l'arceau, bout, corps a bouts arrondis."""
    r_in = TR + mm2m(0.15); r_out = r_in + mm2m(0.7)
    ring = CrossSection.circle(r_out, 40) - CrossSection.circle(r_in, 40)
    a = np.radians(55); R = 2 * r_out
    wedge = CrossSection([ccw([(0.0, 0.0), (-R * np.sin(a), R * np.cos(a)), (-R * np.sin(a), R), (R * np.sin(a), R),
                               (R * np.sin(a), R * np.cos(a))])])
    clip = Manifold.extrude(ring - wedge, FENDER_CLIP_W).translate([0, 0, -FENDER_CLIP_W / 2])
    clip = clip.transform([[1, 0, 0, FENDER_X], [0, 0, 1, y], [0, 1, 0, TAUD_TOP]])
    z_top = TAUD_TOP - r_out - FENDER_ROPE
    rope = Manifold.cylinder(FENDER_ROPE + 0.5 * (r_out - r_in), 0.016, 0.016, 16).translate([FENDER_X, y, z_top])
    eye = Manifold.cylinder(0.03, 0.03, 0.02, 20).translate([FENDER_X, y, z_top - 0.02])
    zc1 = z_top - 0.02 - FENDER_R * 0.85; zc0 = zc1 - FENDER_L
    body = capsule((FENDER_X, y, zc0), (FENDER_X, y, zc1), FENDER_R, 32)
    rib = [Manifold.cylinder(0.02, FENDER_R + 0.006, FENDER_R + 0.006, 32).translate([FENDER_X, y, z]) for z in (zc0 + 0.03, zc1 - 0.05)]
    m = Manifold.batch_boolean([clip, rope, eye, body] + rib, OpType.Add)
    return m.trim_by_plane([0.0, 0.0, 1.0], zc0 - FENDER_R + 0.025)

# ---- anneaux inox de tableau (photos v16), un de chaque cote pres du coin arriere
EYE_X, EYE_Z = 0.22, 0.95
EYE_WIRE, EYE_PEG = 0.014, 0.016

def eye_frame(side=1):
    """Point du flanc, normale sortante, direction le long de la coque, verticale dans le flanc."""
    P = hull_point(EYE_X, EYE_Z)
    Tx = hull_point(EYE_X + 0.01, EYE_Z) - hull_point(EYE_X - 0.01, EYE_Z)
    Tz = hull_point(EYE_X, EYE_Z + 0.01) - hull_point(EYE_X, EYE_Z - 0.01)
    n = np.cross(Tz, Tx); n /= np.linalg.norm(n)
    if n[1] < 0:
        n = -n
    t = Tx / np.linalg.norm(Tx); up = np.cross(n, t); up /= np.linalg.norm(up)
    if up[2] < 0:
        up = -up
    if side < 0:
        P, n, t, up = (np.array([v[0], -v[1], v[2]]) for v in (P, n, t, up))
    return P, n, t, up

def build_eye_local():
    """Anneau en D (repere local : X sort de la coque, Z vertical), platine, tenon ; meplats a +/- y."""
    w = EYE_WIRE
    parts = [box(0.0, 0.012, -0.022, 0.022, -0.026, 0.026),
             tube_path([(0.008, 0, 0.026), (0.045, 0, 0.022), (0.062, 0, 0.0), (0.045, 0, -0.022), (0.008, 0, -0.026)], w, 12),
             Manifold.cylinder(0.055, EYE_PEG, EYE_PEG, 16).rotate([0, -90, 0]).translate([0.004, 0, 0])]
    m = Manifold.batch_boolean(parts, OpType.Add)
    f = w - mm2m(0.25)
    return m.trim_by_plane([0.0, 1.0, 0.0], -f).trim_by_plane([0.0, -1.0, 0.0], -f)

def place_eye(m, side=1):
    P, n, t, up = eye_frame(side)
    P = P + n * mm2m(0.3)
    yv = np.cross(up, n)
    return m.transform([[n[0], yv[0], up[0], P[0]], [n[1], yv[1], up[1], P[1]], [n[2], yv[2], up[2], P[2]]])

EYE_FIT = mm2m(0.1)                 # v22 : jeu reduit (0,2 -> 0,1 mm) et trou a la forme du tenon, meplats compris

def eye_holes():
    """v22 : fente a la forme exacte du tenon (rond tronque par les 2 meplats) : l'anneau entre en force, sans colle."""
    f = EYE_WIRE - mm2m(0.25) + EYE_FIT
    out = []
    for side in (1, -1):
        h = Manifold.cylinder(0.065, EYE_PEG + EYE_FIT, EYE_PEG + EYE_FIT, 16).rotate([0, -90, 0]).translate([0.006, 0, 0])
        h = h.trim_by_plane([0.0, 1.0, 0.0], -f).trim_by_plane([0.0, -1.0, 0.0], -f)
        out.append(place_eye(h, side))
    return out

# ------------------------------------------------------------------ outboard (Verado V8 : releve sur la vue de cote, v17)
# Repere local du moteur : x vers l'arriere depuis la face de fixation (x = 0), y lateral,
# z vers le haut depuis le dessus de la plaque anti-cavitation (z = 0).
# Couleurs (photos v17) : capot blanc au-dessus du plan de joint, jupe arriere blanche jusqu'a la ceinture,
# bas de capot gris a l'avant de la jupe, embase, support et helice gris.
ENG_PLANE = (0.072, 0.657, 0.155)      # plan de joint : z = z0 - k (x - x0) (descend un peu vers l'arriere)
# bord arriere du bas de capot gris (= face avant de la jupe blanche) : il quitte le plan de joint a x = 0,66 par un
# coin arrondi (r 5 cm), puis descend en s'inclinant un peu vers l'arriere jusqu'a la ceinture (liseré noir de la photo)
TAIL_TOP_X, TAIL_R = 0.66, 0.05
TAIL_EDGE = [(0.712, 0.45), (0.722, 0.30), (0.733, 0.18), (0.743, 0.072), (0.745, -0.02)]
TAIL_X = 0.72                          # repere moyen de la face avant de la jupe (tenon)
COWL_BOT = 0.06                        # bas du capot (jupe et bas de capot), au-dessus de la ceinture grise
ENG_PEAK = (0.53, 1.46)                # sommet du capot
ENG_NOSE = (-0.048, 1.126)             # nez du capot (deborde un peu en avant de la face de fixation)
ENG_RT = ((0.80, 1.36), (1.010, 1.005))   # dessus arriere : Bezier quadratique du sommet a (1,01 ; 1,005)
ENG_REAR = [(0.833, COWL_BOT), (0.850, 0.121), (0.890, 0.255), (0.930, 0.389), (0.985, 0.520),
            (1.016, 0.657), (1.024, 0.790), (1.022, 0.900), (1.010, 1.005)]
ENG_LOWFRONT = [(-0.048, 1.126), (-0.021, 0.925), (0.019, 0.791), (0.072, 0.657)]
ENG_CHAPS = [(0.240, 0.50), (0.255, 0.30), (0.265, 0.15), (0.270, COWL_BOT)]
ENG_B = ([0.06, 0.15, 0.30, 0.45, 0.55, 0.60, 0.66, 0.75, 0.90, 1.05, 1.11, 1.20, 1.32, 1.40, 1.50],
         [0.178, 0.212, 0.252, 0.280, 0.293, 0.300, 0.325, 0.330, 0.335, 0.335, 0.330, 0.317, 0.299, 0.287, 0.272])
COWL_AF, COWL_AR, COWL_EXP = 0.15, 0.09, 2.8    # bas de capot : arrondis en plan (avant, arriere) et exposant
COWL_CREASE = [(-0.03, 0.80), (0.032, 0.785), (0.30, 0.734), (0.595, 0.683), (0.756, 0.683), (0.90, 0.722),
               (0.997, 0.804), (1.06, 0.86)]
COWL_BUTTONS = ((0.166, 0.718), (0.295, 0.702))
SKIRT = (0.30, 0.82, 0.150, 0.155)          # ceinture grise au-dessus de la plaque : x0, x1, demi-largeurs bas / haut
# ---- v18 : forme du capot relevee sur 5 vues (face, 3/4 avant, 2 vues de cote, 3/4 arriere).
# Vu de dessus le capot est en pointe vers l'avant : face avant etroite (la « cravate », 10 cm en haut, 25 cm en bas),
# flancs avant plans qui s'evasent (~25 deg) jusqu'au milieu du capot, flancs droits a l'arriere (rentrent un peu
# en haut). Dessus : arete dorsale plate (10 cm au nez, 24 cm au sommet) bordee de 2 chanfreins d'epaule (~35 deg)
# qui s'annulent au nez ; prises d'air dans les chanfreins du dessus arriere.
ENG_NOSE_PT = (-0.048, 0.050, 1.126)    # coin haut de la cravate (= bout avant de l'arete dorsale)
ENG_SHOULDER = (0.50, 0.299, 1.32)      # coin d'epaule au sommet (flanc / chanfrein)
ENG_TIE_LOW = (0.055, 0.125, 0.70)      # coin bas de la cravate, a la hauteur du trait de joint avant
SPINE = ([-0.30, -0.048, 0.53, 1.01, 1.40], [0.050, 0.050, 0.122, 0.112, 0.112])   # demi-largeur de l'arete dorsale
COWL_CHAMF = math.radians(35.0)         # pente transversale des chanfreins d'epaule
NOSE_R = 0.03                           # arrondi du nez (vue de cote)
SPINE_LINES = (0.06, 0.32)              # 2 traits en travers de l'arete dorsale, sur le dessus avant
VENT = (0.60, 0.86, 0.06, 0.05)         # prises d'air : x debut / fin, distance au bord de l'arete, largeur
PLAN_R = 0.8                            # rayon (en plan) du raccord flanc avant / flanc droit

def _side_ab():
    N, C, T = (np.array(p, float) for p in (ENG_NOSE_PT, ENG_SHOULDER, ENG_TIE_LOW))
    n = np.cross(C - N, T - N)
    return -n[0] / n[1], -n[2] / n[1]
SIDE_A, SIDE_BZ = _side_ab()            # flanc avant : y = yN + A (x - xN) + Bz (z - zN)

def side_y(x, z, inset=0.0):
    """Demi-largeur du flanc avant plan (babord) en (x, z) ; inset > 0 : plan decale vers l'interieur."""
    xN, yN, zN = ENG_NOSE_PT
    return yN + SIDE_A * (x - xN) + SIDE_BZ * (z - zN) - inset * math.sqrt(1 + SIDE_A ** 2 + SIDE_BZ ** 2)

def side_normal(side=1):
    n = np.array([-SIDE_A, side * 1.0, -SIDE_BZ]); return n / np.linalg.norm(n)

def spine_s(x):
    return float(np.interp(x, SPINE[0], SPINE[1]))

def plane_z(x):
    x0, z0, k = ENG_PLANE
    return z0 - k * (x - x0)

def plane_normal():
    n = np.array([ENG_PLANE[2], 0.0, 1.0]); return n / np.linalg.norm(n)

def _rear_top(n=14):
    P0, P1, P2 = np.array(ENG_PEAK), np.array(ENG_RT[0]), np.array(ENG_RT[1])
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * P0 + 2 * (1 - t) * t * P1 + t ** 2 * P2           # du sommet vers l'arriere

def _fillet_corner(a, b, c, R, n=6):
    """Arc de rayon R qui remplace le coin b entre les segments a-b et b-c."""
    a, b, c = (np.asarray(p, float) for p in (a, b, c))
    u = (a - b) / np.linalg.norm(a - b); v = (c - b) / np.linalg.norm(c - b)
    ang = np.arccos(np.clip(u @ v, -1, 1))
    t = R / np.tan(ang / 2)
    p1, p2 = b + u * t, b + v * t
    bis = (u + v) / np.linalg.norm(u + v)
    cen = b + bis * (R / np.sin(ang / 2))
    a1 = np.arctan2(*(p1 - cen)[::-1]); a2 = np.arctan2(*(p2 - cen)[::-1])
    d = (a2 - a1 + np.pi) % (2 * np.pi) - np.pi
    return [tuple(cen + R * np.array([np.cos(a1 + d * k / n), np.sin(a1 + d * k / n)])) for k in range(n + 1)]

def eng_profile():
    """Silhouette laterale (x, z) du capot, de la jupe et du bas de capot (sens trigo), nez arrondi."""
    pts = [(ENG_CHAPS[-1][0], COWL_BOT)] + ENG_REAR
    pts += [tuple(p) for p in _rear_top()[::-1][1:]]
    pts += _fillet_corner(ENG_PEAK, ENG_LOWFRONT[0], ENG_LOWFRONT[1], NOSE_R)
    pts += ENG_LOWFRONT[1:] + [(0.215, plane_z(0.215))] + ENG_CHAPS[:-1]
    return [(float(a), float(b)) for a, b in pts]

def prof_xrange(z, pts):
    xs = []
    P = np.asarray(pts)
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        if a[1] != b[1] and (a[1] - z) * (b[1] - z) <= 0:
            t = (z - a[1]) / (b[1] - a[1]); xs.append(a[0] + t * (b[0] - a[0]))
    return min(xs), max(xs)

def _prof_ztop_table(n=600):
    P = np.asarray(eng_profile())
    xs = np.linspace(P[:, 0].min() + 1e-4, P[:, 0].max() - 1e-4, n)
    zt = []
    for x in xs:
        best = -1.0
        for i in range(len(P)):
            a, b = P[i], P[(i + 1) % len(P)]
            if a[0] != b[0] and (a[0] - x) * (b[0] - x) <= 0:
                t = (x - a[0]) / (b[0] - a[0]); best = max(best, a[1] + t * (b[1] - a[1]))
        zt.append(best)
    return xs, np.array(zt)
_ZTOP = None

def z_top(x):
    """Dessus du profil (y = 0) a l'abscisse x ; en avant du nez : droite du dessus avant prolongee."""
    global _ZTOP
    if _ZTOP is None:
        _ZTOP = _prof_ztop_table()
    xs, zt = _ZTOP
    k = (ENG_PEAK[1] - ENG_NOSE[1]) / (ENG_PEAK[0] - ENG_NOSE[0])
    if x < xs[0]:
        return ENG_NOSE[1] + k * (x - ENG_NOSE[0])
    return float(np.interp(x, xs, zt))

def z_top_exact(x):
    """Dessus du profil sans la table (droite avant / Bezier arriere), pour les traits graves."""
    if x <= ENG_PEAK[0]:
        k = (ENG_PEAK[1] - ENG_NOSE[1]) / (ENG_PEAK[0] - ENG_NOSE[0])
        return ENG_NOSE[1] + k * (x - ENG_NOSE[0])
    P0, P1, P2 = np.array(ENG_PEAK), np.array(ENG_RT[0]), np.array(ENG_RT[1])
    lo, hi = 0.0, 1.0
    for _ in range(50):
        t = (lo + hi) / 2
        xt = (1 - t) ** 2 * P0[0] + 2 * (1 - t) * t * P1[0] + t ** 2 * P2[0]
        lo, hi = (t, hi) if xt < x else (lo, t)
    t = (lo + hi) / 2
    return float((1 - t) ** 2 * P0[1] + 2 * (1 - t) * t * P1[1] + t ** 2 * P2[1])

def cowl_b(z):
    return float(np.interp(z, ENG_B[0], ENG_B[1]))

def _front_lower(z):
    zz = [COWL_BOT] + [p[1] for p in ENG_CHAPS[::-1][1:]] + [plane_z(0.215)]
    xx = [ENG_CHAPS[-1][0]] + [p[0] for p in ENG_CHAPS[::-1][1:]] + [0.215]
    return float(np.interp(z, zz, xx))

def _rear_pts(xr, ar, b, nr):
    return [(1 - t) ** 2 * np.array([xr, 0.0]) + 2 * (1 - t) * t * np.array([xr - 0.30 * ar, 0.80 * b])
            + t * t * np.array([xr - ar, b]) for t in np.linspace(0, 1, nr)]

def _plan_lower(z, xf, xr, b, nf=19, ns=4, nr=9):
    """Bas de capot (v17) : proue arrondie, flancs droits, arriere large en V tres doux (arete au milieu)."""
    L = xr - xf
    af = min(COWL_AF, 0.45 * L); ar = min(COWL_AR, 0.30 * L)
    pts = list(_rear_pts(xr, ar, b, nr))
    for t in np.linspace(0, 1, ns + 2)[1:-1]:
        pts.append(np.array([xr - ar + t * (xf + af - (xr - ar)), b]))
    for a in np.linspace(np.pi / 2, 3 * np.pi / 2, nf):
        c, s = np.cos(a), np.sin(a)
        pts.append(np.array([xf + af + af * np.sign(c) * abs(c) ** (2 / COWL_EXP), b * np.sign(s) * abs(s) ** (2 / COWL_EXP)]))
    for t in np.linspace(0, 1, ns + 2)[1:-1]:
        pts.append(np.array([xf + af + t * (xr - ar - (xf + af)), -b]))
    for q in _rear_pts(xr, ar, b, nr)[::-1][:-1]:
        pts.append(np.array([q[0], -q[1]]))
    return np.array(pts)

def cowl_plan(z, xr, b, inset=0.0, nf=10, ns=4, nr=9, na=8):
    """Section en plan (v18) : flancs avant plans qui se rejoignent en pointe devant le capot (le profil recoupe
    la pointe : il reste la cravate), raccord en grand rayon (pas d'arete) avec les flancs droits de l'arriere,
    arriere large en V tres doux."""
    ar = COWL_AR
    y0 = side_y(ENG_NOSE_PT[0], z, inset)
    xm = ENG_NOSE_PT[0] + (b - y0) / SIDE_A                   # le flanc avant atteint la demi-largeur b
    xt = ENG_NOSE_PT[0] + (0.004 - y0) / SIDE_A              # pointe (demi-largeur 4 mm reels)
    xm = min(xm, xr - ar - 0.02)
    bm = side_y(xm, z, inset)                                 # = b, sauf si le flanc avant n'a pas la place
    th = math.atan(SIDE_A)
    lt = min(PLAN_R * math.tan(th / 2), 0.45 * (xm - xt) * math.hypot(1, SIDE_A), 0.8 * (xr - ar - xm))
    r = lt / math.tan(th / 2)
    aft = (xm + 0.5, bm); fwd = (xm - 0.5, bm - 0.5 * SIDE_A)
    arc = _fillet_corner(aft, (xm, bm), fwd, r, na)          # du flanc droit vers le flanc avant
    xa = arc[0][0]; xb = arc[-1][0]
    pts = list(_rear_pts(xr, ar, bm, nr))
    for t in np.linspace(0, 1, ns + 2)[1:-1]:
        pts.append(np.array([xr - ar + t * (xa - (xr - ar)), bm]))
    pts += [np.array(p) for p in arc]
    for t in np.linspace(0, 1, nf + 1)[1:]:
        x = xb + t * (xt - xb); pts.append(np.array([x, side_y(x, z, inset)]))
    for t in np.linspace(1, 0, nf + 1)[:-1]:
        x = xb + t * (xt - xb); pts.append(np.array([x, -side_y(x, z, inset)]))
    pts += [np.array([p[0], -p[1]]) for p in arc[::-1]]
    for t in np.linspace(0, 1, ns + 2)[1:-1]:
        pts.append(np.array([xa + t * (xr - ar - xa), -bm]))
    for q in _rear_pts(xr, ar, bm, nr)[::-1][:-1]:
        pts.append(np.array([q[0], -q[1]]))
    return np.array(pts)

def _roof(inset=0.0):
    """Arete dorsale + chanfreins d'epaule : loft (selon x) de trapezes. Au-dessus du profil de 1,5 cm,
    chanfreins de pente COWL_CHAMF depuis les bords de l'arete dorsale (y = +-s(x), z = dessus du profil)."""
    Y, zb, dz = 0.6, -1.0, 0.015
    ta = math.tan(COWL_CHAMF)
    secs = []
    for x in np.arange(-0.30, 1.3001, 0.01):
        s = spine_s(x) - inset / math.sin(COWL_CHAMF)
        zt = z_top(x)
        yt = s - dz / ta
        zc = zt - (Y - s) * ta
        secs.append([(x, -Y, zb), (x, Y, zb), (x, Y, zc), (x, yt, zt + dz), (x, -yt, zt + dz), (x, -Y, zc)])
    return loft(secs)

def build_cowl(inset=0.0):
    """Capot + jupe + bas de capot d'une piece (on le decoupe ensuite par couleur)."""
    prof = eng_profile()
    zl = np.r_[np.arange(COWL_BOT, 0.70, 0.04), 0.70]
    lsec = []
    for z in zl:
        p = _plan_lower(z, _front_lower(z) + inset, prof_xrange(z, prof)[1] - inset, cowl_b(z) - inset)
        lsec.append(np.column_stack([p, np.full(len(p), z)]))
    lower = loft(lsec)
    ztop = 1.452
    zs = sorted(set(np.round(np.r_[COWL_BOT - 0.04, 0.0, 0.30, 0.58, np.arange(0.60, ztop, 0.03), ztop, 1.50,
                                   [z for z in ENG_B[0] if 0.6 < z < ztop]], 4)))
    secs = []
    for z in zs:
        if z < 0.6:
            xr, b = 1.25, 0.36
        else:
            xr = prof_xrange(min(z, ztop), prof)[1] - inset
            b = cowl_b(z) - inset
        p = cowl_plan(z, xr, b, inset)
        secs.append(np.column_stack([p, np.full(len(p), z)]))
    pointed = loft(secs)
    cs = CrossSection([ccw(prof)])
    if inset:
        cs = cs.offset(-inset, JoinType.Miter, 2.0, 0)
    prism = Manifold.extrude(cs, 2.0).rotate([90, 0, 0]).translate([0, 1.0, 0])
    above = box(-1.0, 2.0, -1.0, 1.0, 0.60, 2.0)
    return (lower + above) ^ pointed ^ prism ^ _roof(inset)

def _surface_y(m, x, z):
    """Demi-largeur exterieure du solide m au point (x, z) (coupe horizontale)."""
    best = 0.0
    for poly in m.slice(z).to_polygons():
        P = np.asarray(poly)
        for i in range(len(P)):
            a, b = P[i], P[(i + 1) % len(P)]
            if a[0] != b[0] and (a[0] - x) * (b[0] - x) <= 0:
                t = (x - a[0]) / (b[0] - a[0]); best = max(best, abs(a[1] + t * (b[1] - a[1])))
    return best

def _band_xz(pts, half):
    """Bande mince (x, z) de part et d'autre d'une polyligne, extrudee sur toute la largeur."""
    P = np.asarray(pts, float)
    up, dn = [], []
    for i in range(len(P)):
        a, b = P[max(i - 1, 0)], P[min(i + 1, len(P) - 1)]
        d = (b - a) / np.linalg.norm(b - a); nrm = np.array([-d[1], d[0]])
        up.append(P[i] + half * nrm); dn.append(P[i] - half * nrm)
    return extrude_xz(up + dn[::-1], -1.0, 1.0)

def _above_plane(off=0.0):
    return extrude_xz([(-0.4, plane_z(-0.4) + off), (1.7, plane_z(1.7) + off), (1.7, 3.0), (-0.4, 3.0)], -1.0, 1.0)

CHAPS_WINDOW = [(0.40, 0.50), (0.665, 0.50), (0.685, 0.14), (0.58, 0.13)]   # fenetre en creux du bas de capot (x, z)

def tail_cutter(grow=0.0):
    """Zone (x, z) de la jupe blanche, a l'arriere du bord du bas de capot gris (coin haut arrondi), extrudee
    sur toute la largeur. grow > 0 : avance le bord (sert a creuser le liseré cote gris)."""
    x1 = TAIL_TOP_X - grow
    z1 = plane_z(TAIL_TOP_X)
    arc = [(x1 + TAIL_R * np.sin(a), z1 - TAIL_R + TAIL_R * np.cos(a)) for a in np.linspace(0.0, np.pi / 2, 12)]
    edge = [(x - grow, z) for (x, z) in TAIL_EDGE]
    pts = [(x1 - 0.05, z1 + 0.20)] + arc + edge + [(edge[-1][0], -0.3), (2.0, -0.3), (2.0, 3.0), (x1 - 0.05, 3.0)]
    return extrude_xz(pts, -1.0, 1.0)

GROOVE_W, GROOVE_D = mm2m(0.45), mm2m(0.35)      # traits graves du capot (maquette : 0,45 x 0,35 mm)

def groove_along(pts, nrm, w, d, e=None):
    """Outil de rainure : rectangles (largeur w, de e au-dessus a d sous la surface) le long d'une polyligne 3D
    posee sur la surface ; nrm = normales exterieures."""
    e = mm2m(0.4) if e is None else e
    P = np.asarray(pts, float); Nn = np.asarray(nrm, float)
    secs = []
    for i in range(len(P)):
        a, b = P[max(i - 1, 0)], P[min(i + 1, len(P) - 1)]
        T = (b - a) / np.linalg.norm(b - a)
        n = Nn[i] - (Nn[i] @ T) * T; n /= np.linalg.norm(n)
        B = np.cross(T, n)
        secs.append([P[i] + w / 2 * B + e * n, P[i] - w / 2 * B + e * n, P[i] - w / 2 * B - d * n, P[i] + w / 2 * B - d * n])
    return loft(secs)

def cyl_dir(p, n, r, d0, d1, seg=20):
    """Cylindre de rayon r d'axe n passant par p, de p + d0 n a p + d1 n."""
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    z = np.array([0.0, 0.0, 1.0]); v = np.cross(z, n); c = float(z @ n)
    if np.linalg.norm(v) < 1e-9:
        R = np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        R = np.eye(3) + vx + vx @ vx / (1 + c)
    o = np.asarray(p, float) + d0 * n
    T = np.column_stack([R, o])
    return Manifold.cylinder(d1 - d0, r, r, seg).transform(T.tolist())

def _front_x(z):
    zz = [p[1] for p in ENG_LOWFRONT][::-1]; xx = [p[0] for p in ENG_LOWFRONT][::-1]
    return float(np.interp(z, zz, xx))

def _top_normal(x, h=0.004):
    dz = (z_top_exact(x + h) - z_top_exact(x - h)) / (2 * h)
    n = np.array([-dz, 0.0, 1.0]); return n / np.linalg.norm(n)

def cowl_grooves():
    """Traits graves du capot (photos v18) : bords de l'arete dorsale du nez jusqu'au dessus arriere, 2 traits en
    travers de l'arete sur le dessus avant, bords de la cravate, 2 prises d'air dans les chanfreins arriere."""
    g = []
    off = mm2m(0.6)
    xs = np.unique(np.r_[np.linspace(ENG_NOSE[0] + 0.03, 0.985, 60), ENG_PEAK[0]])
    for sgn in (-1, 1):
        pts = [(x, sgn * (spine_s(x) - off), z_top_exact(x)) for x in xs]
        g.append(groove_along(pts, [_top_normal(x) for x in xs], GROOVE_W, GROOVE_D))
    for x0 in SPINE_LINES:
        s = spine_s(x0) - off
        pts = [(x0, y, z_top_exact(x0)) for y in np.linspace(-s, s, 5)]
        g.append(groove_along(pts, [_top_normal(x0)] * 5, GROOVE_W, GROOVE_D))
    zz = np.linspace(0.815, ENG_NOSE[1] - 0.03, 24)
    for sgn in (-1, 1):
        pts, nr = [], []
        for z in zz:
            x = _front_x(z)
            pts.append((x, sgn * (side_y(x, z) - off), z))
            dxdz = (_front_x(z + 0.003) - _front_x(z - 0.003)) / 0.006
            n = np.array([-1.0, 0.0, dxdz]); nr.append(n / np.linalg.norm(n))
        g.append(groove_along(pts, nr, GROOVE_W, GROOVE_D))
    x0, x1, u, w = VENT
    ta = math.tan(COWL_CHAMF); ct = 1.0 / ta
    for sgn in (-1, 1):
        pts, nr = [], []
        for x in np.linspace(x0, x1, 30):
            pts.append((x, sgn * (spine_s(x) + u), z_top_exact(x) - u * ta))
            ds = (spine_s(x + 0.003) - spine_s(x - 0.003)) / 0.006
            dzt = (z_top_exact(x + 0.003) - z_top_exact(x - 0.003)) / 0.006
            n = np.array([-ds - dzt * ct, sgn * 1.0, ct]); nr.append(n / np.linalg.norm(n))
        g.append(groove_along(pts, nr, w, mm2m(1.0)))
    return g

# ---- helice inox 3 pales (v19, d'apres les photos Mercury) : pales en cuillere, larges, bout rond, vrillees au pas,
# devers vers l'arriere et legere quete ; moyeu cylindrique a capuchon arrondi et sortie d'echappement en creux.
PROP_AX = (0.835, -0.27)                 # x du milieu des pales sur le moyeu, z de l'arbre
PROP_HUB = (0.76, 0.90, 0.055)           # moyeu : x debut, x fin, rayon
PROP_R, PROP_CHORD, PROP_PITCH = 0.195, 0.20, 0.55     # rayon en bout de pale, corde maxi, pas (21 pouces)
PROP_T = (0.026, 0.017)                  # epaisseur au pied / en bout (0,9 mm minimum a l'echelle)
PROP_SKEW, PROP_RAKE = 0.06, 0.02        # devers (bout en retard sur la rotation) et quete (bout vers l'arriere)

def _blade(theta):
    """Pale vrillee : loft de sections elliptiques (corde x epaisseur) le long du rayon, bout arrondi."""
    x0, z0 = PROP_AX
    rh = PROP_HUB[2]
    ex = np.array([1.0, 0.0, 0.0])
    er = np.array([0.0, math.cos(theta), math.sin(theta)])
    em = np.array([0.0, math.sin(theta), -math.cos(theta)])        # sens de la rotation (helice a droite)
    us = np.r_[-0.10, np.linspace(0.0, 0.85, 12), 0.90, 0.94, 0.97, 0.99, 0.997]
    secs = []
    for u in us:
        r = rh + u * (PROP_R - rh)
        uu = max(u, 0.0)
        f = (0.60 + 1.0 * uu - 0.55 * uu ** 2) * math.sqrt(max(1.0 - uu ** 5, 0.0))
        c = max(PROP_CHORD * f, 0.022)
        t = PROP_T[0] + (PROP_T[1] - PROP_T[0]) * uu
        c = max(c, t * 1.15)
        phi = math.atan(PROP_PITCH / (2 * math.pi * r))
        h = math.cos(phi) * em - math.sin(phi) * ex              # vers le bord d'attaque
        n = math.sin(phi) * em + math.cos(phi) * ex              # face en pression, vers l'arriere
        C = np.array([x0, 0.0, z0]) + r * er - PROP_SKEW * uu ** 2 * em + PROP_RAKE * uu * ex
        ps = np.linspace(0, 2 * math.pi, 28, endpoint=False)
        secs.append([C + 0.5 * c * math.cos(a) * h + 0.5 * t * math.sin(a) * n for a in ps])
    return loft(secs)

def build_propeller():
    x0, z0 = PROP_AX
    xa, xb, rh = PROP_HUB
    parts = [cyl_x(xa, xb, 0, z0, rh, 32)]
    cap = Manifold.cylinder(0.025, rh, rh - 0.014, 32).rotate([0, 90, 0]).translate([xb, 0, z0])
    parts.append(cap)
    parts += [_blade(math.pi / 2 + k * 2 * math.pi / 3) for k in range(3)]
    m = Manifold.batch_boolean(parts, OpType.Add)
    return m - cyl_x(xb + 0.025 - 0.012, xb + 0.06, 0, z0, rh - 0.026, 28)      # sortie d'echappement en creux

def build_outboard_parts():
    """{'capot', 'jupe', 'gris'} en repere local. Les tenons et logements sont ajoutes par pieces.engine_split()."""
    cowl = build_cowl()
    grown = build_cowl(inset=-mm2m(0.5))                  # les outils de rainure debordent dehors : pas de faces confondues
    shell = grown - build_cowl(inset=mm2m(0.35))
    above = _above_plane()
    top = cowl ^ above
    # trait de joint du capot, 2 boutons de chaque cote, prise d'air le long du dessus arriere
    top = top - (shell ^ _band_xz(COWL_CREASE, mm2m(0.25)))
    # v18 : bords et traits de l'arete dorsale, bords de la cravate, prises d'air dans les chanfreins arriere
    top = top - Manifold.batch_boolean(cowl_grooves(), OpType.Add)
    for (xb, zb) in COWL_BUTTONS:                          # boutons sur le flanc avant plan, percés selon sa normale
        for sgn in (-1, 1):
            top = top - cyl_dir((xb, sgn * side_y(xb, zb), zb), side_normal(sgn), 0.024, -mm2m(0.6), 0.08)
    below = cowl - above
    cut = tail_cutter()
    tail = below ^ cut
    tail = tail - box(0.60, SKIRT[1] + 0.01, -SKIRT[3] - 0.01, SKIRT[3] + 0.01, -0.1, COWL_BOT + 0.012 + mm2m(0.05))
    chaps = below - cut
    # bas de capot gris : liseré en creux contre le blanc (dessus et bord arriere) et fenetre en creux d'apres la photo
    skin = grown - build_cowl(inset=mm2m(0.3))
    seal = skin ^ (tail_cutter(mm2m(0.3)) + _above_plane(-mm2m(0.3)))
    chaps = chaps - seal
    win = CrossSection([ccw(CHAPS_WINDOW)]).offset(-0.02, JoinType.Round, 2.0, 12).offset(0.02, JoinType.Round, 2.0, 12)
    win_prism = Manifold.extrude(win, 2.0).rotate([90, 0, 0]).translate([0, 1.0, 0])
    chaps = chaps - ((grown - build_cowl(inset=mm2m(0.25))) ^ win_prism)
    # --- ceinture grise, plaque anti-cavitation, carter, torpille, aileron de quille, helice (recales sur la vue de cote)
    g = [chaps]
    x0, x1, b0, b1 = SKIRT
    secs = [np.column_stack([superellipse((x0 + x1) / 2, 0, (x1 - x0) / 2, b, 2.6, 56), np.full(56, z)])
            for z, b in ((-0.005, b0), (COWL_BOT + 0.012, b1))]
    g.append(loft(secs))
    cs = CrossSection.square([0.60, 0.30]).translate([0.25, -0.15]).offset(0.08, JoinType.Round, 2.0, 24)
    g.append(Manifold.extrude(cs, 0.04).translate([0, 0, -0.04]))
    secs = []
    for z, xa, xb, b in [(-0.02, 0.22, 0.80, 0.10), (-0.22, 0.25, 0.74, 0.075)]:
        p = superellipse((xa + xb) / 2, 0, (xb - xa) / 2, b, 2.0, 48)
        secs.append(np.column_stack([p, np.full(len(p), z)]))
    g.append(loft(secs))
    g.append(Manifold.sphere(1.0, 48).scale([0.30, 0.085, 0.085]).translate([0.50, 0, -0.27]))
    g.append(extrude_xz([(0.30, -0.27), (0.56, -0.27), (0.62, -0.58), (0.47, -0.58)], -0.0225, 0.0225))
    g.append(build_propeller())
    # --- support de fixation (etrier), tube de direction, 2 verins de trim, tete de direction (sous le capot)
    sup = [box(0.0, 0.09, -0.13, 0.13, 0.08, 0.58)]
    for sgn in (-1, 1):
        ya, yb2 = sorted([sgn * 0.10, sgn * 0.14])
        sup.append(extrude_xz([(0.0, 0.08), (0.10, 0.08), (0.19, 0.22), (0.19, 0.58), (0.0, 0.58)], ya, yb2))
        sup.append(Manifold.hull(Manifold.sphere(0.03, 16).translate([0.215, sgn * 0.07, 0.10])
                                 + Manifold.sphere(0.03, 16).translate([0.215, sgn * 0.07, 0.50])))
    sup.append(Manifold.cylinder(0.54, 0.055, 0.055, 32).translate([0.155, 0, 0.06]))
    sup.append(box(0.0, 0.30, -0.08, 0.08, 0.55, 0.70))                     # tete de direction, entre dans le bas de capot
    sup.append(box(0.12, 0.36, -0.07, 0.07, -0.03, 0.10))                    # liaison basse : pivot -> ceinture / plaque
    sup = Manifold.batch_boolean(sup, OpType.Add) - _above_plane(-mm2m(0.04))
    g.append(sup)
    return {"capot": top, "jupe": tail, "gris": Manifold.batch_boolean(g, OpType.Add)}

def build_hydrofoil():
    """Aileron noir (hydrofoil) sur la plaque anti-cavitation, en U autour de la ceinture (ouvert vers l'avant),
    ailes qui depassent la plaque de chaque cote et vers l'arriere."""
    T = 0.024
    outer = CrossSection([ccw([(0.26, 0.17), (0.36, 0.33), (0.92, 0.33), (0.99, 0.27), (0.99, -0.27), (0.92, -0.33),
                                (0.36, -0.33), (0.26, -0.17)])])
    x0, x1, b0, b1 = SKIRT
    xc, a, b = (x0 + x1) / 2, (x1 - x0) / 2 + 0.006, b0 + 0.006
    strut = CrossSection([superellipse(xc, 0, a, b, 2.6, 72)])
    front = CrossSection.square([1.0, 2 * b]).translate([xc - 1.0, -b])
    return Manifold.extrude(outer - (strut + front), T)

TAIL_STUD = (TAIL_X, 0.0, 0.30)       # tenon horizontal du bas de capot gris qui entre dans la jupe blanche
COWL_STUD_X = 0.47                     # tenon du bas de capot gris sous le capot blanc (sur le plan de joint)

# ---- gaines de commande noires : 2 trous au milieu du tableau, au-dessus de la chaise, vers l'avant de chaque moteur
HOSE_R = 0.03
HOSE_HOLE = (0.0, 0.10, 0.865)        # passe-coque babord dans le tableau, juste au-dessus de la chaise (tribord symetrique)
HOSE_ENG_LOC = (0.0, 0.0, 0.615)      # arrivee : face avant de la tete de direction (repere local du moteur)
HOSE_PEG_R = 0.016

def _hose_frame(side=1):
    """Repere du plan (incline) de la gaine : origine au trou, u vers l'arriere, v vers le moteur, n normale."""
    S = np.array([HOSE_HOLE[0], side * HOSE_HOLE[1], HOSE_HOLE[2]])
    E = np.array([ENG_X - HOSE_ENG_LOC[0], side * ENG_Y, ENG_Z + HOSE_ENG_LOC[2]])
    u = np.array([-1.0, 0.0, 0.0])
    d = E - S; v = d - (d @ u) * u; v /= np.linalg.norm(v)
    n = np.cross(u, v)
    return S, E, u, v, n

def _hose_ctrl(side=1):
    """Points de controle (u, v) : la gaine sort du passe-coque, s'affaisse jusqu'a toucher la chaise (photo v17),
    puis remonte vers l'avant de la tete de direction, ou elle entre a l'horizontale."""
    S, E, u, v, nn = _hose_frame(side)
    lu, lv = (E - S) @ u, (E - S) @ v
    ua, ub = 0.02 + HOSE_R, lu - (HOSE_R + 0.003)          # le tube s'arrete contre la collerette et contre le moteur
    b_touch = (PLATF_Z + DIAMOND_H + mm2m(0.1) + HOSE_R - S[2]) / v[2]
    t = np.linspace(0, 1, 200)[:, None]
    best = None
    for b1 in np.linspace(0.0, -0.40, 161):
        P = [np.array([ua, 0.0]), np.array([ua + 0.30 * (ub - ua), b1]), np.array([ub - 0.30 * (ub - ua), lv]), np.array([ub, lv])]
        c = (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]
        err = abs(c[:, 1].min() - b_touch)
        if best is None or err < best[0]:
            best = (err, P)
    return best[1]

def hose_path(side=1, n=40):
    S, E, u, v, nn = _hose_frame(side)
    P = _hose_ctrl(side)
    t = np.linspace(0, 1, n)[:, None]
    c = (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]
    return [tuple(S + a * u + b * v) for a, b in c]

def build_hose(side=1):
    """Gaine annelee noire : tube, collerette contre le tableau, tenon dans le tableau et tenon dans la tete
    de direction du moteur. Plane (plan incline) : 2 meplats symetriques, la meme piece sert des 2 cotes."""
    S, E, u, v, nn = _hose_frame(side)
    pts = hose_path(side)
    parts = [tube_path(pts, HOSE_R, 16)]
    parts.append(cyl_x(-0.02 - HOSE_R, -mm2m(0.02), S[1], S[2], 0.055, 28))              # collerette
    parts.append(cyl_x(-0.005, 0.05, S[1], S[2], HOSE_PEG_R, 16))                         # tenon dans le tableau
    parts.append(cyl_x(E[0] - 0.045, E[0] + 0.005, E[1], E[2], HOSE_PEG_R, 16))           # tenon dans le moteur
    m = Manifold.batch_boolean(parts, OpType.Add)
    h = HOSE_R - mm2m(0.25)
    slab = Manifold.cube([4.0, 4.0, 2 * h]).translate([-2.0, -2.0, -h])
    R = np.column_stack([u, v, nn])
    T = [[R[0, 0], R[0, 1], R[0, 2], S[0]], [R[1, 0], R[1, 1], R[1, 2], S[1]], [R[2, 0], R[2, 1], R[2, 2], S[2]]]
    return m ^ slab.transform(T)

def hose_down(side=1):
    return -_hose_frame(side)[4]

def hose_holes_hull():
    return [cyl_x(-0.01, 0.06, s * HOSE_HOLE[1], HOSE_HOLE[2], HOSE_PEG_R + CLR, 16) for s in (1, -1)]

def hose_hole_engine_local():
    x, y, z = HOSE_ENG_LOC
    return [cyl_x(x - 0.01, x + 0.055, y, z, HOSE_PEG_R + CLR, 16)]

ENG_PIN_Z = (0.27, 0.36)            # trous de goupille dans la face de fixation (z local), sous le dessus de la nacelle

def build_outboard():
    P = build_outboard_parts()
    eng = Manifold.batch_boolean([P["capot"], P["jupe"], P["gris"]], OpType.Add)
    for z in ENG_PIN_Z:
        eng = eng - cyl_x(-0.01, 0.12, 0, z, mm2m(1.0), 16)
    return eng

ENG_Y = 0.36
ENG_Z = 0.40                        # hauteur (bateau) du dessus de la plaque anti-cavitation
ENG_X = -0.40

def place_seat(seat, s):
    return seat.translate([SEAT_X, s * SEAT_Y, SEAT_Z])

def place_engine(eng, y):
    return eng.rotate([0, 0, 180]).translate([ENG_X, y, ENG_Z])

# ------------------------------------------------------------------ poste de pilotage : volant sport + manette
WHEEL_C = np.array([2.50, 0.24, 1.30])            # centre du volant (a babord, comme sur la photo)
WHEEL_N = np.array([-np.cos(np.radians(30)), 0.0, np.sin(np.radians(30))])   # axe, vers le pilote
WHEEL_R = 0.18

def build_wheel():
    """Volant sport 3 branches avec palette de flaps, a plat (dos sur le plateau, axe = +z)."""
    rim = Manifold.cylinder(0.034, 0.195, 0.195, 96) - Manifold.cylinder(0.05, 0.160, 0.160, 96).translate([0, 0, -0.01])
    parts = [rim]
    for ang in (0, 180, 270):                              # branches : droite, gauche, bas
        sp = box(0.045, 0.175, -0.022, 0.022, 0.0, 0.022).rotate([0, 0, ang])
        parts.append(sp)
    parts.append(Manifold.cylinder(0.075, 0.060, 0.050, 40))                          # moyeu
    # palette de flaps : sur la branche droite, a cote du moyeu, en relief
    pad = CrossSection.square([0.075, 0.034]).translate([0.065, -0.017]).offset(0.012, JoinType.Round, 2.0, 16)
    parts.append(Manifold.extrude(pad, 0.040))
    w = Manifold.batch_boolean(parts, OpType.Add)
    return w - Manifold.cylinder(0.2, mm2m(1.0), mm2m(1.0), 16).translate([0, 0, -0.05])

WHEEL_NOTCH = mm2m(0.2)
# volant (photos v17) : jante beige epaisse, 3 branches doubles inox (3 h, 11 h, 7 h vu du pilote), moyeu beige
# avec un bossage chrome au centre, pompe de direction noire entre le volant et la console
RIM_R, RIM_RT, RIM_ZC = 0.19, 0.021, 0.015       # rayon de l'axe du tube, rayon du tube, axe au-dessus du meplat
SPOKE_ANG = (0.0, 120.0, 240.0)
SPOKE_W, SPOKE_H, SPOKE_GAP = 0.016, 0.014, 0.036
HUB_R, BOSS_R, BOSS_H = 0.075, 0.034, 0.053
CAP_R0, CAP_R1, CAP_H = 0.074, 0.060, 0.030
BAND_DA = 12.5                                    # bandes noires de la jante, de part et d'autre de chaque branche (deg)

def _torus(rt):
    return Manifold.revolve(CrossSection.circle(rt, 28).translate([RIM_R, RIM_ZC]), 120)

def build_wheel_rim():
    """Jante beige (couleur teck) a plat sur un meplat : tube rond, encoches au dos pour les 6 barres des branches,
    2 fines rainures de chaque cote des branches (bandes noires a peindre)."""
    rim = _torus(RIM_RT).trim_by_plane([0.0, 0.0, 1.0], 0.0)
    for a in SPOKE_ANG:
        for sg in (-1, 1):
            c = sg * SPOKE_GAP / 2
            nb = box(RIM_R - 0.035, RIM_R + 0.004, c - SPOKE_W / 2 - WHEEL_NOTCH, c + SPOKE_W / 2 + WHEEL_NOTCH, -0.01, SPOKE_H + WHEEL_NOTCH)
            rim = rim - nb.rotate([0, 0, a])
    skin = _torus(RIM_RT + mm2m(0.3)) - _torus(RIM_RT - mm2m(0.2))
    for a in SPOKE_ANG:
        for da in (-BAND_DA, BAND_DA):
            sl = box(RIM_R - 0.06, RIM_R + 0.06, -mm2m(0.16), mm2m(0.16), -0.1, 0.2).rotate([0, 0, a + da])
            rim = rim - (skin ^ sl)
    return rim

def build_wheel_spokes():
    """Croisillon inox (alu) a plat : disque central, 3 branches doubles dont les bouts entrent dans les encoches
    de la jante, bossage central (il traverse le moyeu beige) perce pour l'axe en filament."""
    parts = [Manifold.cylinder(SPOKE_H, HUB_R, HUB_R, 48)]
    for a in SPOKE_ANG:
        for sg in (-1, 1):
            c = sg * SPOKE_GAP / 2
            parts.append(box(HUB_R - 0.012, RIM_R + 0.002, c - SPOKE_W / 2, c + SPOKE_W / 2, 0.0, SPOKE_H).rotate([0, 0, a]))
    parts.append(Manifold.cylinder(BOSS_H, BOSS_R, BOSS_R * 0.92, 36))
    w = Manifold.batch_boolean(parts, OpType.Add)
    return w - Manifold.cylinder(0.05 + BOSS_H - mm2m(0.8), mm2m(1.0), mm2m(1.0), 16).translate([0, 0, -0.05])   # trou borgne : le centre reste chrome

def build_wheel_cap():
    """Moyeu beige (couleur teck) pose sur le disque central, troue pour le bossage chrome."""
    cap = Manifold.cylinder(CAP_H, CAP_R0, CAP_R1, 48)
    return cap - Manifold.cylinder(0.2, BOSS_R + CLR, BOSS_R + CLR, 36).translate([0, 0, -0.05])

def place_cap(m):
    return place_wheel(m.translate([0, 0, SPOKE_H]))

def wheel_frame():
    """Matrice 3x4 : repere du volant (x = droite du pilote, y = haut, z = axe vers le pilote, z = 0 au dos
    de la jante) -> bateau ; le plan median de la jante passe par WHEEL_C."""
    n = WHEEL_N; ex = np.array([0.0, -1.0, 0.0]); ey = np.cross(n, ex)
    ey = -ey if ey[2] < 0 else ey
    o = WHEEL_C - RIM_ZC * n
    return [[ex[0], ey[0], n[0], o[0]], [ex[1], ey[1], n[1], o[1]], [ex[2], ey[2], n[2], o[2]]]

PUMP_R0, PUMP_R1, PUMP_GAP = 0.058, 0.098, mm2m(0.2)

def build_helm_pump():
    """Pompe de direction noire (repere bateau) : tronc de cone sur l'axe du volant, de la face arriere de la
    console jusque derriere le croisillon ; percee pour l'axe en filament."""
    n = WHEEL_N
    t_front = RIM_ZC + PUMP_GAP                     # distance derriere le plan median du volant
    t_face = (CON_AFT_X - WHEEL_C[0]) / (-n[0])      # la face arriere de la console (verticale) sur l'axe
    L = t_face + 0.06 - t_front
    cone = Manifold.cylinder(L, PUMP_R1, PUMP_R0, 48)          # base (grosse) en z = 0
    ex = np.array([0.0, -1.0, 0.0]); ey = np.cross(n, ex); ey = -ey if ey[2] < 0 else ey
    o = WHEEL_C - (t_front + L) * n
    m = cone.transform([[ex[0], ey[0], n[0], o[0]], [ex[1], ey[1], n[1], o[1]], [ex[2], ey[2], n[2], o[2]]])
    m = m.trim_by_plane([-1.0, 0.0, 0.0], -CON_AFT_X + mm2m(0.02))   # posee contre la face arriere de la console
    hole = Manifold.cylinder(0.6, mm2m(1.0), mm2m(1.0), 16).translate([0, 0, -0.3])
    return m - hole.transform([[ex[0], ey[0], n[0], WHEEL_C[0]], [ex[1], ey[1], n[1], WHEEL_C[1]], [ex[2], ey[2], n[2], WHEEL_C[2]]])

def place_wheel(w):
    return w.transform(wheel_frame())

def wheel_shaft_hole():
    """Trou de l'axe de direction dans la face arriere de la console (filament 1,75 mm)."""
    t0, t1 = 0.10, 0.28
    h = Manifold.cylinder(t1 - t0, mm2m(1.0), mm2m(1.0), 16).translate([0, 0, -t1])
    n = WHEEL_N; ex = np.array([0.0, -1.0, 0.0]); ey = np.cross(n, ex)
    return h.transform([[ex[0], ey[0], n[0], WHEEL_C[0]], [ex[1], ey[1], n[1], WHEEL_C[1]], [ex[2], ey[2], n[2], WHEEL_C[2]]])

THR_X = 3.30 + DXC                   # face arriere de la console (x)
THR = dict(y0=-0.12, y1=0.0, z0=1.16, z1=1.32)

def build_throttle():
    """Manette d'acceleration a levier lateral, repere local : x vers l'arriere depuis la console,
    y lateral (0 = flanc de pose a plat), z haut. Imprimee couchee sur le flanc y = 0."""
    h = THR["z1"] - THR["z0"]; wdt = THR["y1"] - THR["y0"]
    base = extrude_xz([(0.0, 0.0), (0.12, 0.0), (0.12, h * 0.55), (0.07, h), (0.0, h)], 0.0, wdt)
    arm = extrude_xz([(0.055, h * 0.55), (0.105, h * 0.55), (0.165, h + 0.14), (0.125, h + 0.155)], 0.0, 0.035)
    grip = Manifold.cylinder(0.15, 0.026, 0.026, 24).rotate([-90, 0, 0]).translate([0.145, 0.0, h + 0.15])
    hub = Manifold.cylinder(0.035, 0.045, 0.045, 24).rotate([-90, 0, 0]).translate([0.08, 0.0, h * 0.55])
    t = Manifold.batch_boolean([base, arm, grip, hub], OpType.Add)
    return t - cyl_x(-0.01, 0.08, wdt / 2, h / 2, mm2m(1.0), 16)

def place_throttle(t):
    # local x vers l'arriere -> bateau -x ; local y -> bateau +y (flanc y=0 du cote babord du volant)
    return t.transform([[-1, 0, 0, THR_X], [0, -1, 0, THR["y1"]], [0, 0, 1, THR["z0"]]])

def throttle_pin_hole():
    yc = (THR["y0"] + THR["y1"]) / 2; zc = (THR["z0"] + THR["z1"]) / 2
    return cyl_x(THR_X - 0.01, THR_X + 0.12, yc, zc, mm2m(1.0), 16)

def helm_holes():
    return [wheel_shaft_hole(), throttle_pin_hole()]

# ------------------------------------------------------------------ stand
def build_cradle2(x, hull_full):
    zt = zbot(x, 0.80) + 0.06
    prof_yz = [(-0.98, -0.50), (0.98, -0.50), (0.85, zt), (-0.85, zt)]
    # profil dans le plan (y,z) : on extrude un profil (x',z) = (y,z) puis on tourne de 90 deg autour de z
    m = extrude_xz(prof_yz, -0.19, 0.19)            # profil en (x,z), epaisseur en y
    m = m.rotate([0, 0, 90])                        # x->y, y->-x
    m = m.translate([x, 0, 0])
    clr = mm2m(0.25)
    for d in ([0, clr, 0], [0, -clr, 0], [0, 0, -clr], [0, 0, 0]):
        m = m - hull_full.translate(d)
    return m

# ------------------------------------------------------------------ dowels for hull joints
SPLITS = [3.80]                      # coque en 2 pieces (plateau 250 x 250)
DOWEL_R = mm2m(1.0)        # trou 2,0 mm pour filament 1,75 mm
DOWEL_L = mm2m(6.5)

def joint_holes(x):
    zf = zfloor(x)
    pts = [(0.0, (float(zk(x)) + zf) / 2)]
    for s in (-1, 1):
        pts.append((s * 0.38, (zbot(x, 0.38) + zf) / 2))
        pts.append((s * (float(ys(x)) - GUN / 2 - 0.01), float(zs(x)) - 0.20))
    return [cyl_x(x - DOWEL_L, x + DOWEL_L, y, z, DOWEL_R, 16) for (y, z) in pts], pts

def bracket_holes():
    holes = []
    for s in (-1, 1):
        for zl in ENG_PIN_Z:
            holes.append(cyl_x(ENG_X - 0.01, ENG_X + 0.12, s * ENG_Y, ENG_Z + zl, mm2m(1.0), 16))
    return holes

# ------------------------------------------------------------------ export
def export(m, name, rotate_flat=None):
    mesh = m.to_mesh()
    V = np.asarray(mesh.vert_properties)[:, :3] * MM
    F = np.asarray(mesh.tri_verts)
    tm = trimesh.Trimesh(V, F, process=True)
    if rotate_flat is not None:
        tm.apply_transform(rotate_flat)
    tm.apply_translation(-tm.bounds[0] * np.array([1, 1, 1]))   # posee a l'origine
    path = os.path.join(OUT, name)
    tm.export(path)
    return tm

BOL_PIN_X = (1.70, 3.50)            # 2 goupilles de positionnement sous chaque boudin
BOL_PIN_D = mm2m(3.0)               # profondeur de chaque cote du joint (sol / boudin)

def bolster_pin_holes():
    """Trous de 2,0 mm (goupille en filament 1,75) : dans le pont et sous les boudins, au meme endroit."""
    holes = []
    for s in (-1, 1):
        for x in BOL_PIN_X:
            y = s * (w_ck(x) - 0.045); zf = zfloor(x)
            holes.append(Manifold.cylinder(2 * BOL_PIN_D, mm2m(1.0), mm2m(1.0), 16).translate([x, y, zf - BOL_PIN_D]))
    return holes

def hull_extra_holes():
    """Logements et percages des pieces rapportees."""
    cuts = seadeck_recesses() + console_bar_holes()
    cuts += [windshield_slot()] + screen_recesses() + [mfd_recess(), switch_recess(), door_groove(), net_recess()]
    cuts += cleat_recesses() + flag_socket() + eye_holes() + stripe_groove() + hose_holes_hull()
    cuts += tab_holes() + actuator_holes()
    return cuts

def build_hull():
    shell = shell_cached()
    hull = shell - build_cockpit_cutter()
    hull = Manifold.batch_boolean([hull, build_interior(shell), build_bracket(), build_platform(), diamond_plate(), build_hatch()], OpType.Add)
    hull = hull - transom_passage_cut()
    hull = hull - Manifold.batch_boolean(tt_sockets() + bracket_holes() + helm_holes() + hull_extra_holes(), OpType.Add)
    hull = hull + Manifold.batch_boolean(ladder_studs() + switch_studs() + [mfd_stud()], OpType.Add)   # v22 : + interrupteurs, ecran
    return shell, hull

def main():
    shell, hull = build_hull()
    hull_full = shell + build_bracket()

    eng = build_outboard()
    fr_p, fr_s = build_frame(-1), build_frame(1)
    canopy = build_canopy()
    seat = bucket_seat()

    # coque entiere (pour grandes imprimantes)
    export(hull, "coque_entiere_une_piece.stl")

    # troncons
    pieces = []
    rest = hull
    all_holes = []
    for x in SPLITS:
        hs, _ = joint_holes(x)
        all_holes += hs
    for h in all_holes:
        rest = rest - h
    B = 9.0
    a = rest ^ box(-B, SPLITS[0], -B, B, -B, B)
    b = rest ^ box(SPLITS[0], SPLITS[1], -B, B, -B, B)
    c = rest ^ box(SPLITS[1], B, -B, B, -B, B)
    pieces = {"coque_1_arriere.stl": a, "coque_2_milieu.stl": b, "coque_3_avant.stl": c}
    sizes = {}
    for n, p in pieces.items():
        tm = export(p, n)
        sizes[n] = tm.extents
    tm = export(build_wheel(), "volant_sport.stl")
    sizes["volant_sport.stl"] = tm.extents
    Rside = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)   # couche sur le flanc y = 0
    tm = export(build_throttle(), "manette_gaz.stl", Rside)
    sizes["manette_gaz.stl"] = tm.extents
    tm = export(seat, "fauteuil_coquille_x2.stl")
    sizes["fauteuil_coquille_x2.stl"] = tm.extents
    tm = export(eng, "moteur_x2.stl")
    sizes["moteur_x2.stl"] = tm.extents
    # cadres T-top : a plat (plan x-z -> plan XY)
    R = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
    tm = export(fr_s, "ttop_cadre_x2.stl", R)
    sizes["ttop_cadre_x2.stl"] = tm.extents
    # toit : rainures vers le haut pour imprimer sans support
    R2 = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    Rarch = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)   # (x,y,z)->(y,z,x) : a plat
    tm = export(build_arch(0.0), "ttop_arceau_taud_x4.stl", Rarch)
    sizes["ttop_arceau_taud_x4.stl"] = tm.extents
    for i, x in enumerate((1.05, 5.15)):
        tm = export(build_cradle2(x, hull_full), f"support_berceau_{i+1}.stl")
        sizes[f"support_berceau_{i+1}.stl"] = tm.extents
    for n, e in sizes.items():
        print(f"{n:32s} {e[0]:6.1f} x {e[1]:6.1f} x {e[2]:6.1f} mm")
    # infos
    print("floor at x:", {x: round(zfloor(x), 3) for x in (0.3, 1.36, 3.05, 3.3, 5.3, 6.0, 6.8)})

if __name__ == "__main__":
    main()
