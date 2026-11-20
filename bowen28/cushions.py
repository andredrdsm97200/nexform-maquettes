"""Coussins et taud faits main : gabarits a l'echelle (2D) et volumes d'apercu (3D, non imprimes).

Chaque element : name, kind, cs (contour du gabarit, en metres reels), stripes (bandes creme, meme repere),
folds (positions de pliure le long de u), solid / stripe_solid (apercu 3D), qty (nombre a faire).
"""
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M
from manifold3d import Manifold, CrossSection, JoinType, OpType
from shapely.geometry import Polygon, LineString

C = M.CUSH                      # epaisseur des coussins (4,2 mm a l'echelle)
BAND_W, BAND_G = 0.05, 0.035    # bande creme de 5 cm, ecart de 3,5 cm dans une paire
PAIR_STEP = 0.55                # ecart entre paires sur les banquettes
PAD_H, PAD_T = 0.30, 0.10       # coussins de plat-bord (photo 3) : hauteur, epaisseur
UB_TOP = M.BOW_BACK_TOP         # haut du dossier de la banquette avant
BACK_TOP = M.BACK_HI[2] + 0.02  # haut du coussin de dossier haut


def U(ms):
    ms = [m for m in ms if not m.is_empty()]
    return Manifold.batch_boolean(ms, OpType.Add) if ms else Manifold()


def cockpit_plan(z):
    return M.build_cockpit_cutter().slice(z)


def half_space(x0=None, x1=None, y0=None, y1=None):
    a, b = (x0 if x0 is not None else -20), (x1 if x1 is not None else 20)
    c, d = (y0 if y0 is not None else -20), (y1 if y1 is not None else 20)
    return CrossSection.square([b - a, d - c]).translate([a, c])


def pair_centers(v0, v1, step=PAIR_STEP):
    n = max(1, int(round((v1 - v0) / step)))
    return [v0 + (i + 0.5) * (v1 - v0) / n for i in range(n)]


def bands_2d(centers, axis, lo, hi):
    """Paires de bandes ; axis='u' : bandes paralleles a v, centrees en u = c."""
    out = []
    for c in centers:
        for s in (-1, 1):
            m = c + s * (BAND_G / 2 + BAND_W / 2)
            if axis == "u":
                out.append(CrossSection.square([BAND_W, hi - lo]).translate([m - BAND_W / 2, lo]))
            else:
                out.append(CrossSection.square([hi - lo, BAND_W]).translate([lo, m - BAND_W / 2]))
    return CrossSection.batch_boolean(out, OpType.Add) if out else CrossSection()


def bands_3d(centers, axis):
    """Boites de bandes en 3D : axis 'y' -> bandes perpendiculaires a y (coupent a y = c +/-)."""
    out = []
    for c in centers:
        for s in (-1, 1):
            m = c + s * (BAND_G / 2 + BAND_W / 2)
            if axis == "y":
                out.append(M.box(-5, 15, m - BAND_W / 2, m + BAND_W / 2, -5, 5))
            else:
                out.append(M.box(m - BAND_W / 2, m + BAND_W / 2, -5, 5, -5, 5))
    return U(out)


def yz_solid(cs, x0, th):
    return M.yz_to_x(Manifold.extrude(cs, th), x0)


def largest(cs):
    parts = cs.decompose()
    return max(parts, key=lambda p: p.area()) if len(parts) > 1 else cs


def _inset(r, d):
    """Retrait d'un arrondi de rayon r a la distance d de l'arete (d = 0 : sur la face, d = r : fin de l'arrondi)."""
    return r - math.sqrt(max(r * r - (r - d) ** 2, 0.0))


def round_top(cs, z0, h, r, n=7, ext=None):
    """Apercu d'un coussin pose a plat : dalle cs de z0 a z0 + h, aretes du dessus arrondies (rayon r),
    par couches decalees. ext : contour plus grand servant au decalage (aretes laissees vives)."""
    base = ext if ext is not None else cs
    zc = z0 + h - r
    parts = [Manifold.extrude(cs, h - r).translate([0, 0, z0])]
    for k in range(n):
        za, zb = zc + r * k / n, zc + r * (k + 1) / n
        lay = base.offset(-_inset(r, r - (0.5 * (za + zb) - zc)), JoinType.Round, 2.0, 24) ^ cs
        if not lay.is_empty():
            parts.append(Manifold.extrude(lay, zb - za).translate([0, 0, za]))
    return U(parts)


def round_x(prof, x0, t, r, n=6, ext=None, lo=True, hi=True):
    """Apercu d'un coussin debout : profil (y, z) extrude le long de x de x0 a x0 + t, aretes des faces
    x0 (lo) et x0 + t (hi) arrondies (rayon r), par tranches decalees."""
    base = ext if ext is not None else prof
    xa, xb = x0 + (r if lo else 0.0), x0 + t - (r if hi else 0.0)
    slabs = [(xa, xb, prof)]
    for k in range(n):
        d0, d1 = r * k / n, r * (k + 1) / n
        lay = base.offset(-_inset(r, 0.5 * (d0 + d1)), JoinType.Round, 2.0, 24) ^ prof
        if lay.is_empty():
            continue
        if lo:
            slabs.append((x0 + d0, x0 + d1, lay))
        if hi:
            slabs.append((x0 + t - d1, x0 + t - d0, lay))
    return U([M.yz_to_x(Manifold.extrude(cs, b - a), a) for (a, b, cs) in slabs])


def item(name, kind, cs, solid, stripes2d=None, stripes3d=None, folds=(), qty=1, cut=None, hseams=()):
    if kind == "assise":
        big = largest(cs)
        if big.area() < cs.area() - 1e-9:
            solid = solid ^ Manifold.extrude(big, 10.0).translate([0, 0, -5.0])
        cs = big
    st = stripes2d if stripes2d is not None else CrossSection()
    st = st ^ cs if not st.is_empty() else st
    ss = (solid ^ stripes3d) if stripes3d is not None else Manifold()
    main = (solid - stripes3d) if stripes3d is not None else solid
    return dict(name=name, kind=kind, cs=cs, stripes=st, folds=list(folds), qty=qty, cut=cut,
                solid=main, stripe_solid=ss, hseams=list(hseams))


# --------------------------------------------------------------------------- banquettes arriere
def aft_items():
    """Banquettes arriere : 2 grandes marches. Le coussin d'assise haute avance au-dessus du dossier
    de l'assise basse : la face avant de l'assise haute et ce dossier forment une seule face, sans
    petite marche entre les deux. Bandes alignees d'une assise a l'autre."""
    P = M.interior_parts()
    out = []
    # banquette haute : assise devant le dossier, prolongee de C vers l'avant (recouvre le dossier bas)
    zt = M.BENCH_HI_TOP
    backzone = CrossSection([M.path_band(M.back_path(), -0.05, 0.11 + 0.005)])
    front = M.BENCH_HI_X[1] + C + 0.008                      # bord avant apres le retrait de 0,008
    seat_hi = ((half_space(x1=front, y1=M.STEP_Y) ^ cockpit_plan(zt - 0.003) ^ half_space(x0=M.BACK_XB + 0.11))
               - backzone).offset(-0.008, JoinType.Round, 2.0, 16)
    b = seat_hi.bounds()
    yc_hi = pair_centers(b[1], b[3])                          # memes colonnes de bandes pour les 3 coussins
    # banquette basse : assise
    zl = M.BENCH_LO_TOP
    seat = (P["banquette_basse"].slice(zl - 0.003) ^ cockpit_plan(zl - 0.003)).offset(-0.008, JoinType.Round, 2.0, 16)
    bl = seat.bounds()
    out.append(item("Banquette arrière basse – assise", "assise", seat,
                    Manifold.extrude(seat, C).translate([0, 0, zl]),
                    bands_2d(yc_hi, "v", bl[0] - 1, bl[2] + 1), bands_3d(yc_hi, "y")))
    # banquette basse : dossier contre la face avant de la banquette haute, jusqu'a son dessus
    w = M.w_ck(M.BENCH_HI_X[1])
    back = M.rect_round_corner(-w + 0.008, M.STEP_Y - 0.008, zl + C, zt, -w + 0.008, zt, 0.001)
    out.append(item("Banquette arrière basse – dossier", "dossier", back,
                    yz_solid(back, M.BENCH_HI_X[1], C),
                    bands_2d(yc_hi, "u", zl, 2), bands_3d(yc_hi, "y")))
    out.append(item("Banquette surélevée – assise", "assise", seat_hi,
                    Manifold.extrude(seat_hi, C).translate([0, 0, zt]),
                    bands_2d(yc_hi, "v", b[0] - 1, b[2] + 1), bands_3d(yc_hi, "y")))
    # banquette haute : dossier avec retour arrondi
    z0 = zt + C
    band = CrossSection([M.path_band(M.back_path(), 0.03, 0.11)])
    solid = Manifold.extrude(band, BACK_TOP - z0).translate([0, 0, z0]) ^ M.back_rounding(BACK_TOP, 0.15, 0.13)
    # developpe : ligne moyenne decalee de 0,07
    pts = M.back_path(200)
    d = np.gradient(pts, axis=0); d /= np.linalg.norm(d, axis=1)[:, None]
    mid = pts + 0.07 * np.stack([d[:, 1], -d[:, 0]], 1)
    seglen = np.r_[0, np.cumsum(np.linalg.norm(np.diff(mid, axis=0), axis=1))]
    Ld = seglen[-1]
    y_s = pts[0, 1]
    i_arc0 = np.argmin(np.abs(pts[:, 1] - (M.STEP_Y - 0.04 - M.BACK_RET_R)))
    i_arc1 = np.argmin(np.abs(pts[:, 0] - (M.BACK_XB + M.BACK_RET_R)) + np.abs(pts[:, 1] - (M.STEP_Y - 0.04)))
    H = BACK_TOP - z0
    dev = CrossSection.square([Ld, H])
    dev = dev ^ M.rect_round_corner(0, Ld, 0, H, 0, H, 0.15) ^ M.rect_round_corner(0, Ld, 0, H, Ld, H, 0.13)
    uc = [y - y_s for y in yc_hi if y - y_s < seglen[i_arc0] - 0.1]
    out.append(item("Banquette surélevée – dossier avec retour", "dossier", dev, solid,
                    bands_2d(uc, "u", -1, 2),
                    bands_3d([y for y in yc_hi if y < M.STEP_Y - 0.04 - M.BACK_RET_R - 0.1], "y") ^ M.box(-1, M.BACK_XB + 0.14, -5, 5, -5, 5),
                    folds=[seglen[i_arc0], seglen[i_arc1]]))
    return out


# --------------------------------------------------------------------------- siege avant de console
FS_GAP, FS_BACK_TOP = 0.15, 1.46     # siege de console : vide (face blanche) entre assise et dossier, haut du dossier
R_SEAT, R_BACK = 0.03, 0.04            # arrondi des aretes : assises, dossiers et retours


def front_seat_items():
    """Siege avant de console : 2 coussins, assise contre la console et dossier moins haut, avec une bande
    de face blanche de la console entre les deux."""
    fx0, fx1, fh, ftop = M.FRONT_SEAT
    seat = CrossSection.square([fx1 - fx0 - 0.008, 2 * fh - 0.016]).translate([fx0 + 0.003, -fh + 0.008])
    back = M.rect_round_corner(-fh + 0.008, fh - 0.008, ftop + C + FS_GAP, FS_BACK_TOP, -fh + 0.008, FS_BACK_TOP, 0.001)
    back = back.offset(-0.02, JoinType.Round, 2.0, 16).offset(0.02, JoinType.Round, 2.0, 16)
    return [item("Siège avant de console – assise", "assise", seat, round_top(seat, ftop, C, R_SEAT),
                 bands_2d([0.0], "v", fx0 - 1, fx1 + 1), bands_3d([0.0], "y")),
            item("Siège avant de console – dossier", "dossier", back, round_x(back, fx0, C, R_SEAT, lo=False),
                 bands_2d([0.0], "u", 0, 3), bands_3d([0.0], "y"))]


# --------------------------------------------------------------------------- banquette avant en U
BOW_JOINT = 0.004               # joint entre deux coussins voisins de la banquette avant


def bow_layout():
    """Plans (x, y) des coussins de la banquette avant, comme sur la photo depuis l'etrave :
    2 dossiers lateraux du retour jusqu'a la paroi avant (bout arrondi visible a l'avant), 1 dossier avant
    entre les deux, 2 retours debout au bout des assises, 2 assises laterales + 1 assise avant."""
    G, BB, RT = BOW_JOINT, M.BOW_BACK_T, M.BOW_RET_T
    Cp = cockpit_plan(1.1)
    xr = M.BOW_X0 + RT                                         # face avant des retours
    inner = M.cockpit_plan_ext().offset(-BB, JoinType.Round, 2.0, 32)
    side = (Cp ^ half_space(x0=xr + G)) - inner
    sides = [side ^ half_space(y0=0.0), side ^ half_space(y1=0.0)]
    front = (Cp ^ half_space(x0=M.X_CK1 - BB)) ^ inner.offset(-G, JoinType.Round, 2.0, 32)
    return dict(Cp=Cp, xr=xr, sides=sides, front=front, backs=CrossSection.batch_boolean(sides + [front], OpType.Add))


def bow_return_solids():
    """Retours babord et tribord : coussins pleins (sans ame blanche), angle haut-interieur arrondi."""
    prof, ext = M.bow_return_profile(), M.bow_return_profile(ext=0.5)
    port = round_x(prof, M.BOW_X0, M.BOW_RET_T, R_BACK, ext=ext) ^ M.build_cockpit_cutter()
    return [port, port.mirror([0, 1, 0])]


def bow_items():
    """Banquette avant en U : assises, dossiers lateraux et avant, retours. Tout est en coussin (mousse +
    tissu) pose sur l'assise rigide blanche ; dossiers a ~8 cm au-dessus du plat-bord, aretes arrondies."""
    P = M.interior_parts()
    zs0 = M.BOW_SEAT_TOP
    G, BB = BOW_JOINT, M.BOW_BACK_T
    Lb = bow_layout()
    H = UB_TOP - zs0                                           # dossiers et retours poses sur l'assise rigide
    out = []
    # assises
    seat_all = ((P["banquette_avant_base"].slice(zs0 - 0.003) ^ cockpit_plan(zs0 - 0.003) ^ half_space(x0=Lb["xr"] + G))
                - Lb["backs"].offset(G, JoinType.Round, 2.0, 16))
    xf = M.bow_well_end()
    parts = [("Banquette avant – assise bâbord", seat_all ^ half_space(x1=xf - G / 2, y0=0.0)),
             ("Banquette avant – assise tribord", seat_all ^ half_space(x1=xf - G / 2, y1=0.0)),
             ("Banquette avant – assise avant", seat_all ^ half_space(x0=xf + G / 2))]
    for name, cs in parts:
        cs = largest(cs.offset(-0.004, JoinType.Round, 2.0, 16))
        out.append(item(name, "assise", cs, round_top(cs, zs0, C, R_SEAT)))
    # dossiers lateraux : bande le long de la paroi, du retour a la paroi avant
    xs = np.linspace(Lb["xr"] + G, M.X_CK1, 200)
    ym = np.array([M.w_ck(x) for x in xs]) - BB / 2
    Ls = float(np.sum(np.hypot(np.diff(xs), np.diff(ym))))
    dev_side = CrossSection.square([Ls, H]) ^ M.rect_round_corner(0, Ls, 0, H, Ls, H, R_BACK)
    side_solids = [round_top(s, zs0, H, R_BACK) for s in Lb["sides"]]
    out.append(item("Banquette avant – dossier latéral (bâbord + tribord)", "dossier", dev_side, U(side_solids), qty=2))
    # dossier avant : entre les deux dossiers lateraux, contre la paroi avant
    Lf = Lb["front"].area() / BB
    dev_front = CrossSection.square([Lf, H])
    out.append(item("Banquette avant – dossier avant", "dossier", dev_front, round_top(Lb["front"], zs0, H, R_BACK)))
    # retours : profil (y, z) a plat pour le gabarit (bout interieur a gauche)
    yw = M.w_ck(M.BOW_X0 + M.BOW_RET_T / 2)                   # paroi, au milieu de l'epaisseur du retour
    prof = M.bow_return_profile() ^ half_space(x1=yw)
    b = prof.bounds()
    prof = prof.translate([-b[0], -b[1]])
    out.append(item("Banquette avant – retour (bâbord + tribord)", "retour", prof, U(bow_return_solids()), qty=2))
    return out


# --------------------------------------------------------------------------- coussins de plat-bord
PAD_SEGS = [(1.22, 2.36), (2.36, 3.50), (3.50, 4.65)]   # 3 longueurs par cote, jusqu'a la banquette avant
ROLL_R = 0.06


def pad_profile(x, s):
    """Profil du coussin de plat-bord : dessus arrondi, face bombee, bas chanfreine vers la paroi."""
    w = M.w_ck(x); zt = float(M.zs(x)) - 0.035; zb = zt - PAD_H; T = PAD_T; r = 0.05
    pts = [(w + 0.005, zb + 0.03), (w - 0.55 * T, zb), (w - T, zb + 0.07), (w - T - 0.008, zb + 0.5 * PAD_H)]
    for a in np.linspace(np.pi, np.pi / 2, 8):
        pts.append((w - T + r + r * np.cos(a), zt - r + r * np.sin(a)))
    pts.append((w + 0.005, zt))
    sec = [(x, s * y, z) for (y, z) in pts]
    return sec if s > 0 else sec[::-1]


PAD_SLANT = math.radians(15)    # lignes inclinees vers l'avant : le haut est plus pres de la proue


def slanted_bands_2d(centers, v_mid, lo, hi, slant=PAD_SLANT):
    """Paires de bandes inclinees (gabarit) : u le long du coussin (avant vers la droite), v vers le haut."""
    t = math.tan(slant); out = []
    for c in centers:
        for s in (-1, 1):
            m = c + s * (BAND_G / 2 + BAND_W / 2)
            pts = [(m - BAND_W / 2 + (lo - v_mid) * t, lo), (m + BAND_W / 2 + (lo - v_mid) * t, lo),
                   (m + BAND_W / 2 + (hi - v_mid) * t, hi), (m - BAND_W / 2 + (hi - v_mid) * t, hi)]
            out.append(CrossSection([np.array(pts)]))
    return CrossSection.batch_boolean(out, OpType.Add) if out else CrossSection()


def slanted_bands_3d(centers, z_mid, slant=PAD_SLANT):
    """Memes bandes en volume : dalles inclinees dans le plan (x, z), sur toute la largeur."""
    t = math.tan(slant); out = []
    for c in centers:
        for s in (-1, 1):
            m = c + s * (BAND_G / 2 + BAND_W / 2)
            z0, z1 = z_mid - 1.0, z_mid + 1.0
            poly = [(m - BAND_W / 2 + (z0 - z_mid) * t, z0), (m + BAND_W / 2 + (z0 - z_mid) * t, z0),
                    (m + BAND_W / 2 + (z1 - z_mid) * t, z1), (m - BAND_W / 2 + (z1 - z_mid) * t, z1)]
            out.append(M.extrude_xz(poly, -3, 3))
    return U(out)


def pad_items():
    """Coussins anti-choc de plat-bord : 3 longueurs par cote, une paire de bandes inclinee par longueur."""
    out = []
    for (a, b) in PAD_SEGS:
        xs = np.linspace(a, b, max(8, int((b - a) / 0.05)))
        Ls = np.r_[0, np.cumsum(np.hypot(np.diff(xs), np.diff([M.w_ck(x) for x in xs])))]
        Ld = Ls[-1]
        xc = [(a + b) / 2]
        solid = U([M.loft([pad_profile(x, s) for x in xs]) for s in (-1, 1)])
        dev = CrossSection.square([Ld, PAD_H]).offset(-0.015, JoinType.Round, 2.0, 16).offset(0.015, JoinType.Round, 2.0, 16)
        uc = [float(np.interp(x, xs, Ls)) for x in xc]
        z_mid = float(M.zs(xc[0])) - 0.035 - PAD_H / 2
        it = item(f"Coussin de plat-bord {a:.2f}–{b:.2f} m", "bande", dev, solid,
                  slanted_bands_2d(uc, PAD_H / 2, -1, PAD_H + 1), slanted_bands_3d(xc, z_mid), qty=2)
        it["hseams"] = [PAD_H / 2]
        out.append(it)
    return out


def roll_axis(side):
    n = M.lateral_normal(side)
    p0 = M.lateral_face(M.LAT_X[0] + 0.03, side) - n * 0.075
    p1 = M.lateral_face(M.LAT_X[1] - 0.03, side) - n * 0.075
    z = M.LAT_TOP + ROLL_R - 0.005
    return np.array([p0[0], p0[1], z]), np.array([p1[0], p1[1], z])


def roll_items():
    p0, p1 = roll_axis(1)
    Lr = float(np.linalg.norm(p1 - p0)) - 2 * ROLL_R
    solid = U([M.tube_path(list(roll_axis(s)), ROLL_R, 28) for s in (1, -1)])
    circ = np.pi * 2 * ROLL_R
    cs = CrossSection.square([Lr, circ])
    it = item("Boudin rond du module latéral (photo 3)", "roll", cs, solid, qty=2)
    return [it]


# --------------------------------------------------------------------------- taud
def taud_item():
    u, hw, marks = M.taud_development()
    pts = [(ui, -h) for ui, h in zip(u, hw)] + [(ui, h) for ui, h in zip(u[::-1], hw[::-1])]
    cs = CrossSection([np.array(pts)]).offset(-0.04, JoinType.Round, 2.0, 24).offset(0.04, JoinType.Round, 2.0, 24)
    b = cs.bounds()
    cs = cs.translate([-b[0], -b[1]])
    cut = cs.offset(M.mm2m(8.0), JoinType.Round, 2.0, 48)
    return dict(name="Taud (toile)", kind="taud", cs=cs, cut=cut, stripes=CrossSection(), folds=list(marks), qty=1,
                solid=M.build_taud_fabric(), stripe_solid=Manifold(), hseams=[])


def fabric_items():
    return aft_items() + front_seat_items() + bow_items() + pad_items() + roll_items() + [taud_item()]


def fabric_preview():
    """Volumes d'apercu : (coussins, bandes creme, taud)."""
    items = fabric_items()
    cush = U([i["solid"] for i in items if i["kind"] != "taud"])
    bands = U([i["stripe_solid"] for i in items if i["kind"] != "taud"])
    roof = [i["solid"] for i in items if i["kind"] == "taud"][0]
    return cush, bands, roof


if __name__ == "__main__":
    pass
    for it in fabric_items():
        b = it["cs"].bounds()
        print(f'{it["name"]:52s} {(b[2]-b[0])*M.MM:6.1f} x {(b[3]-b[1])*M.MM:6.1f} mm  x{it["qty"]}  '
              f'bandes={0 if it["stripes"].is_empty() else len(it["stripes"].to_polygons())}  plis={[round(f*M.MM,1) for f in it["folds"]]}')
