"""Catalogue des pieces imprimees, une couleur par piece, et mise en plateaux 250 x 250 (Bambu Lab A1).

Chaque piece : nom, couleur, quantite, instances en place (assemblage), prototype a imprimer et
vecteur 'down' (face posee sur le plateau), en coordonnees bateau (metres reels).
"""
import os, sys, json
import numpy as np
import trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M
import fit as F
from manifold3d import Manifold, OpType

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_v22")
PLATE, MARGIN, GAP = 250.0, 6.0, 5.0

COLORS = {   # nom affiche, rgb (rendu)
    "blanc": ("Blanc (blanc cassé)", (0.94, 0.93, 0.90)),
    "alu": ("Gris alu / argent", (0.72, 0.75, 0.78)),
    "noir": ("Noir", (0.13, 0.13, 0.14)),
    "teck": ("Teck (beige / bois)", (0.78, 0.63, 0.45)),
    "taupe": ("Taupe", (0.62, 0.55, 0.48)),
}


def U(ms):
    ms = [m for m in ms if not m.is_empty()]
    return Manifold.batch_boolean(ms, OpType.Add)


def clean(m):
    """Supprime les faces degenerees et les eclats (garde les corps de plus de 2 % du plus gros)."""
    m = m.simplify(1e-5)
    parts = m.decompose()
    if len(parts) > 1:
        vmax = max(p.volume() for p in parts)
        m = U([p for p in parts if p.volume() > 0.02 * vmax])
    return m


def cowl_stud_frame():
    """Tenon du bas de capot gris qui entre sous le capot blanc : sur le plan de joint, perpendiculaire a lui."""
    x = M.COWL_STUD_X
    return np.array([x, 0.0, M.plane_z(x)]), M.plane_normal()


def tail_stud_frame():
    """Tenon horizontal du bas de capot gris qui entre dans la jupe blanche (sur la face arriere du gris)."""
    x, y, z = M.TAIL_STUD
    xe = float(np.interp(z, [p[1] for p in M.TAIL_EDGE][::-1], [p[0] for p in M.TAIL_EDGE][::-1]))
    return np.array([xe, y, z]), np.array([1.0, 0.0, 0.0])


def engine_split():
    """v17 (photo du moteur) : capot blanc au-dessus du plan de joint, jupe arriere blanche jusqu'a la ceinture,
    tout le reste gris alu (bas de capot avec sa fenetre, ceinture, embase, support, helice). v18 : forme du capot
    revue sur 5 vues (pointe vers l'avant, arete dorsale, chanfreins d'epaule, prises d'air)."""
    P = M.build_outboard_parts()
    grey = P["gris"] - P["capot"] - P["jupe"]
    for z in M.ENG_PIN_Z:
        grey = grey - M.cyl_x(-0.01, 0.12, 0, z, M.mm2m(1.0), 16)
    grey = grey - U(M.hose_hole_engine_local())
    pc, nc = cowl_stud_frame()
    pt, nt = tail_stud_frame()
    grey = grey + F.stud(pc, nc) + F.stud(pt, nt)
    return P["capot"] - F.socket(pc, nc), P["jupe"] - F.socket(pt, nt), grey


def lego_points():
    """Tenons imprimes sur la coque a la place des goupilles : pieds de fauteuils, boudins rayes."""
    ped = [(M.SEAT_X, s * M.SEAT_Y, M.PLAT_TOP) for s in (1, -1)]
    bol = [(x, s * (M.w_ck(x) - 0.045), M.zfloor(x)) for s in (-1, 1) for x in M.BOL_PIN_X]
    return ped, bol


def catalog():
    import cushions as CU
    C = []

    def add(name, color, asm, proto=None, down=(0, 0, -1), note="", explode=(0, 0, 0), option=False):
        asm = [clean(a) for a in (asm if isinstance(asm, list) else [asm])]
        proto = clean(proto) if proto is not None else asm[0]
        C.append(dict(name=name, color=color, qty=len(asm), asm=asm, proto=proto,
                      down=np.asarray(down, float), note=note, explode=explode, option=option))

    # ---- coussins imprimes : ils apportent des tenons et des empreintes a la coque
    cush = CU.printed_cushions()
    ped_pts, bol_pts = lego_points()
    hull_add = [a for c in cush for a in c["hull_add"]] + [F.stud(p) for p in ped_pts + bol_pts]
    hull_sub = [h for c in cush for h in c["hull_sub"]]

    # ---- coque blanche en 2 pieces
    shell, hull = M.build_hull()
    hull = (hull - U(hull_sub)) + U(hull_add)
    rest = hull
    for x in M.SPLITS:
        for h in M.joint_holes(x)[0]:
            rest = rest - h
    B = 9.0
    sx = M.SPLITS[0]
    add("coque_arriere", "blanc", rest ^ M.box(-B, sx, -B, B, -B, B), note="debout, supports arborescents sur le plateau", explode=(-25, 0, 0))
    add("coque_avant", "blanc", rest ^ M.box(sx, B, -B, B, -B, B), note="debout, supports arborescents sur le plateau", explode=(25, 0, 0))

    # ---- moteurs : capot blanc + jupe arriere blanche + bas de capot et embase gris + aileron noir
    cowl, tail, grey = engine_split()
    nb = M.plane_normal()                                    # normale du plan de joint (repere moteur, vers le haut)
    down_cowl = (nb[0], 0.0, -nb[2])                         # moteur tourne de 180 deg : x -> -x
    add("capot_moteur", "blanc", [M.place_engine(cowl, s * M.ENG_Y) for s in (1, -1)], down=down_cowl,
        note="pose sur son plan de joint, sans support", explode=(-70, 0, 22))
    add("jupe_moteur", "blanc", [M.place_engine(tail, s * M.ENG_Y) for s in (1, -1)], down=(-nb[0], 0.0, nb[2]),
        note="a l'envers, sur sa face du dessus, sans support", explode=(-86, 0, 8))
    add("embase_moteur", "alu", [M.place_engine(grey, s * M.ENG_Y) for s in (1, -1)], note="debout, supports arborescents", explode=(-70, 0, 0))
    foil = M.build_hydrofoil()
    add("aileron_moteur", "noir", [M.place_engine(foil, s * M.ENG_Y) for s in (1, -1)], proto=foil, explode=(-70, 0, -14))
    add("gaine_moteur", "noir", [M.build_hose(1), M.build_hose(-1)], proto=M.build_hose(1), down=M.hose_down(1),
        note="a plat sur un de ses meplats", explode=(-30, 0, 10))
    # ---- flaps inox et leurs verins noirs, sous le pont de la chaise (photo v17)
    tab = M.build_tab_local()
    add("flap", "alu", [M.place_tab(tab, 1), M.place_tab(tab, 1).mirror([0, 1, 0])], proto=tab,
        note="a plat, charniere vers le haut", explode=(-20, 0, -10))
    add("verin_flap", "noir", [M.build_actuator(1), M.build_actuator(-1)], proto=M.build_actuator(1), down=(0, -1, 0),
        note="couche sur le flanc", explode=(-24, 0, -4))

    # ---- poste de pilotage (photos v16) : caisson haut + filet, embases basses, fauteuils taupe d'une piece
    seat = M.bucket_seat_v19()                               # v19 : 2 rainures interieures pour les bandes blanches
    add("fauteuil", "taupe", [M.place_seat(seat, s) for s in (1, -1)], proto=seat, explode=(0, 0, 30))
    band = M.seat_band()
    add("bande_fauteuil", "blanc", [M.place_seat(band.translate([0, sy * M.SEAT_BAND_C, 0]), s) for s in (1, -1) for sy in (1, -1)],
        proto=band, down=(0, -1, 0), note="couchee sur le flanc", explode=(0, 0, 40))
    bases = [M.build_seat_base(s) - F.socket(p) for s, p in zip((1, -1), ped_pts)]
    add("embase_fauteuil", "alu", bases, explode=(0, 0, 14))
    net = M.build_net_flat()
    add("filet_caisson", "noir", M.place_net(net), proto=net, down=(0, 0, 1), explode=(-12, 0, 0),
        note="a plat, face visible sur le plateau, tenons vers le haut (v22)")
    rim, spokes, cap = M.build_wheel_rim(), M.build_wheel_spokes(), M.build_wheel_cap()
    add("jante_volant", "teck", M.place_wheel(rim), proto=rim, explode=(-24, 0, 6))
    add("branches_volant", "alu", M.place_wheel(spokes), proto=spokes, explode=(-16, 0, 4))
    add("moyeu_volant", "teck", M.place_cap(cap), proto=cap, explode=(-30, 0, 8))
    add("pompe_direction", "noir", M.build_helm_pump(), down=(1, 0, 0), note="debout sur sa base", explode=(-8, 0, 2))
    add("manette_gaz", "noir", M.place_throttle(M.build_throttle()), down=(0, 1, 0), explode=(-20, 0, 0))     # noire (photo v17)
    add("barre_console", "alu", M.console_bar(), explode=(-20, 0, 0))
    add("pare_brise", "blanc", M.build_windshield(), down=(0.949, 0, 0.316), explode=(0, 0, 22),
        note="blanc (v19), ou PETG transparent si tu en as")
    add("ecran_mfd", "noir", M.build_mfd(), down=M.mfd_down(), explode=(-6, 0, 16))
    for i in range(len(M.SCREENS)):
        xc, yc, lx, ly = M.SCREENS[i]
        add("ecran_tribord", "noir", M.build_screen(i), proto=M.box(0, lx, 0, ly, 0, 0.032), explode=(0, 0, 16))
    sw = M.build_switch_flat()
    add("interrupteurs", "noir", M.place_switch(sw), proto=sw, explode=(-14, 0, 0))

    # ---- armature du taud
    frames = [M.build_frame(s) for s in (1, -1)]
    add("cadre_taud", "alu", frames, proto=frames[0], down=(0, 1, 0), explode=(0, 0, 45))
    arches = [M.build_arch(x) for x in M.ARCH_X]
    add("arceau_taud", "alu", arches, proto=arches[0], down=(-1, 0, 0), explode=(0, 0, 75))
    front = M.build_arch(M.FRONT_X, front=True)
    add("arceau_avant_taud", "alu", front, down=(-1, 0, 0), explode=(0, 0, 75))
    add("boitier_echelle_babord", "blanc", M.build_ladder_box(1), down=(0, -1, 0), explode=(0, -14, 45))
    add("boitier_echelle_tribord", "blanc", M.build_ladder_box(-1), down=(0, 1, 0), explode=(0, 14, 45))

    # ---- echelle de bain repliee sur la plateforme, taquets, mat de pavillon, anneaux de tableau
    add("echelle_bain", "alu", M.build_ladder(), explode=(0, 0, 14))
    cl = M.build_cleat()
    add("taquet", "alu", [M.place_cleat(cl, x, y, a) for (x, y, a) in M.cleat_spots()], proto=cl, down=(0, 0, 1), explode=(0, 0, 12),
        note="a l'envers, tenon vers le haut (v22)")
    fp = M.build_flagpole()
    add("mat_pavillon", "alu", fp, down=(0, -1, 0), explode=(0, 0, 40))
    eye = M.build_eye_local()
    add("anneau_tableau", "alu", [M.place_eye(eye, s) for s in (1, -1)], proto=eye, down=(0, -1, 0), explode=(0, 0, 0))

    # ---- filet noir de coque : 2 inserts par flanc + la bande du tableau
    xs0, xs1, gap = M.mm2m(0.6), M.STRIPE_SPLIT, M.mm2m(0.1)
    add("filet_noir_arriere", "noir", [M.stripe_inlay_side(xs0, xs1 - gap, s) for s in (1, -1)],
        proto=M.stripe_inlay_flat(xs0, xs1 - gap), note="a plat ; le meme sert des 2 cotes (retourne)", explode=(0, 0, 0))
    add("filet_noir_avant", "noir", [M.stripe_inlay_side(xs1 + gap, M.STRIPE_X_END, s) for s in (1, -1)],
        proto=M.stripe_inlay_flat(xs1 + gap, M.STRIPE_X_END), note="a plat ; le meme sert des 2 cotes (retourne)", explode=(0, 0, 0))
    add("filet_noir_tableau", "noir", [M.stripe_inlay_transom(s) for s in (1, -1)], proto=M.stripe_transom_flat(), explode=(-12, 0, 0))

    # ---- SeaDek (teck)
    for name, tile, surf in M.seadeck_tiles():
        add(name, "teck", M.place_on_surface(tile, surf), proto=tile, down=(0, 0, 1), explode=(0, 0, 14),
            note="a l'envers : dessus sur le plateau, tenons vers le haut (v22)")

    # ---- dos taupe du dossier arriere (vu de la plateforme)
    add("dos_dossier_arriere", "taupe", M.build_back_skin(), explode=(-14, 0, 0), note="debout")

    # ---- boudins rayes (taupe), logements sous les tenons du pont
    light, dark = M.build_bolsters()
    light = light ^ M.build_cockpit_cutter()                  # rayures en creux de 0,8 mm (pas traversantes)
    light = light - U([F.socket(p) for p in bol_pts])
    add("boudin_babord", "taupe", light ^ M.box(-B, B, 0, B, -B, B), explode=(0, 0, 14))
    add("boudin_tribord", "taupe", light ^ M.box(-B, B, -B, 0, -B, B), explode=(0, 0, 14))

    # ---- coussins imprimes (taupe) et bandes (inserts blancs)
    for c in cush:
        add(c["name"], c["color"], c["solid"], down=c["down"], explode=c["explode"])

    # ---- taud imprime (option, a la place de la toile)
    add("taud_imprime_option", "noir", M.build_taud_print(), proto=M.build_taud_flat(), down=(0, 0, -1), explode=(0, 0, 110),
        option=True, note="option (v20) : TPU 90A noir souple, imprime a plat, clips vers le haut, sans support")

    # ---- berceaux d'exposition
    hull_full = shell + M.build_bracket()
    add("berceau_arriere", "alu", M.build_cradle2(1.05, hull_full), explode=(0, 0, -25))
    add("berceau_avant", "alu", M.build_cradle2(5.15, hull_full), explode=(0, 0, -25))
    return C


# ------------------------------------------------------------------ export
WELD = 5e-4      # mm : sommets plus proches soudes, sinon l'arrondi float32 du STL les confond (faces degenerees, aretes non manifold)


def weld(tm, eps=None):
    """Soude les sommets que l'arrondi float32 du STL confondrait (memes coordonnees en float32 ; ou, si eps est
    donne, distants de moins de eps), retire les faces degenerees et les paires de faces doublees.
    A appliquer APRES la derniere transformation : les coordonnees rendues sont exactement des float32."""
    from scipy.spatial import cKDTree
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    V, F = tm.vertices, tm.faces
    n = len(V)
    if eps is None:
        V = np.round(V, 6).astype(np.float32).astype(np.float64)      # 1e-6 mm : les quasi-zeros deviennent 0
        _, lab = np.unique(V, axis=0, return_inverse=True)
        lab = lab.ravel(); nc = int(lab.max()) + 1
    else:
        pairs = cKDTree(V).query_pairs(eps, output_type="ndarray")
        if len(pairs):
            nc, lab = connected_components(coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n)), directed=False)
        else:
            nc, lab = n, np.arange(n)
    rep = np.empty(nc, dtype=np.int64)
    rep[lab[::-1]] = np.arange(n)[::-1]
    Fn = lab[F]
    Fn = Fn[(Fn[:, 0] != Fn[:, 1]) & (Fn[:, 1] != Fn[:, 2]) & (Fn[:, 0] != Fn[:, 2])]
    _, inv, cnt = np.unique(np.sort(Fn, axis=1), axis=0, return_inverse=True, return_counts=True)
    Fn = Fn[cnt[inv.ravel()] == 1]
    used = np.unique(Fn)
    remap = -np.ones(nc, dtype=np.int64); remap[used] = np.arange(len(used))
    return trimesh.Trimesh(V[rep][used], remap[Fn], process=False)


def weld_best(tm):
    """Soudure float32 ; si le resultat n'est pas etanche (deux sommets distincts confondus par l'arrondi), soude
    d'abord les sommets tres proches (5e-4 puis 2e-3 mm) avant l'arrondi. Renvoie la premiere version etanche."""
    w = weld(tm)
    if w.is_watertight:
        return w
    for eps in (5e-4, 2e-3):
        w2 = weld(weld(tm, eps))
        if w2.is_watertight:
            return w2
    return w


def to_tm(m, welded=True):
    """Maillage en mm, double precision (to_mesh64) ; welded : sommets soudes en float32 (pour un export direct)."""
    mesh = m.to_mesh64()
    tm = trimesh.Trimesh(np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3] * M.MM,
                         np.asarray(mesh.tri_verts, dtype=np.int64), process=False)
    return weld(tm) if welded else tm


def print_mesh(entry):
    tm = to_tm(entry["proto"], welded=False)
    R = trimesh.geometry.align_vectors(entry["down"], [0, 0, -1])
    tm.apply_transform(R)
    # orientation dans le plan : plus grande dimension le long de X
    ext = tm.extents
    if ext[1] > ext[0]:
        tm.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
    tm.apply_translation(-tm.bounds[0])
    return weld_best(tm)                # soudure float32 apres la derniere transformation


def maxrects_pack(items, W, H):
    """items : liste (id, w, h). Retourne une liste de plateaux : [(id, x, y, rot)]."""
    plates = []
    todo = sorted(items, key=lambda t: -max(t[1], t[2]) * min(t[1], t[2]))
    for it in todo:
        placed = False
        for pl in plates:
            r = _place(pl, it)
            if r:
                placed = True
                break
        if not placed:
            pl = dict(free=[(0.0, 0.0, W, H)], items=[])
            if not _place(pl, it):
                raise ValueError(f"piece trop grande pour le plateau : {it}")
            plates.append(pl)
    return [pl["items"] for pl in plates]


def _place(pl, it):
    iid, w, h = it
    best = None
    for (fx, fy, fw, fh) in pl["free"]:
        for rot, (ww, hh) in ((0, (w, h)), (1, (h, w))):
            if ww <= fw + 1e-9 and hh <= fh + 1e-9:
                score = (min(fw - ww, fh - hh), max(fw - ww, fh - hh))
                if best is None or score < best[0]:
                    best = (score, fx, fy, ww, hh, rot)
    if best is None:
        return False
    _, x, y, ww, hh, rot = best
    pl["items"].append((iid, x, y, rot))
    new = []
    for (fx, fy, fw, fh) in pl["free"]:
        if x >= fx + fw or x + ww <= fx or y >= fy + fh or y + hh <= fy:
            new.append((fx, fy, fw, fh)); continue
        if x > fx: new.append((fx, fy, x - fx, fh))
        if x + ww < fx + fw: new.append((x + ww, fy, fx + fw - x - ww, fh))
        if y > fy: new.append((fx, fy, fw, y - fy))
        if y + hh < fy + fh: new.append((fx, y + hh, fw, fy + fh - y - hh))
    pruned = []
    for i, a in enumerate(new):
        if any(j != i and a[0] >= b[0] - 1e-9 and a[1] >= b[1] - 1e-9 and a[0] + a[2] <= b[0] + b[2] + 1e-9
               and a[1] + a[3] <= b[1] + b[3] + 1e-9 and (a != b or j < i) for j, b in enumerate(new)):
            continue
        pruned.append(a)
    pl["free"] = pruned
    return True


def build_all(write=True, C=None):
    C = C or catalog()
    os.makedirs(OUT, exist_ok=True)
    meshes = {}
    report = []
    for e in C:
        tm = print_mesh(e)
        meshes[e["name"]] = tm
        e["print_ext"] = tm.extents.copy()
        if write:
            sub = "option_taud_imprime" if e.get("option") else ""
            d = os.path.join(OUT, "stl_par_couleur", e["color"], sub)
            os.makedirs(d, exist_ok=True)
            fn = f"{e['name']}" + (f"_x{e['qty']}" if e["qty"] > 1 else "") + ".stl"
            tm.export(os.path.join(d, fn))
            e["file"] = os.path.join("stl_par_couleur", e["color"], sub, fn)
        report.append((e["color"], e["name"], e["qty"], tm.extents, tm.is_watertight, tm.body_count))
    # plateaux par couleur
    plates = []
    usable = PLATE - 2 * MARGIN
    for col in COLORS:
        for opt in (False, True):
            items = []
            for e in C:
                if e["color"] != col or bool(e.get("option")) != opt:
                    continue
                ext = e["print_ext"]
                for k in range(e["qty"]):
                    items.append((f"{e['name']}#{k + 1}", ext[0] + GAP, ext[1] + GAP))
            if not items:
                continue
            for pi, pl in enumerate(maxrects_pack(items, usable + GAP, usable + GAP)):
                plates.append(dict(color=col, index=pi + 1, items=pl, option=opt))
    if write:
        pdir = os.path.join(OUT, "plateaux_3mf")
        os.makedirs(pdir, exist_ok=True)
        for p in plates:
            scene = trimesh.Scene()
            for (iid, x, y, rot) in p["items"]:
                tm = meshes[iid.split("#")[0]].copy()
                if rot:
                    tm.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
                    tm.apply_translation(-tm.bounds[0])
                tm.apply_translation([MARGIN + x, MARGIN + y, 0])
                tm = weld_best(tm)          # coordonnees exactes en float32 dans le 3MF aussi
                assert tm.bounds[0][0] >= -1e-6 and tm.bounds[0][1] >= -1e-6 and tm.bounds[1][0] <= PLATE + 1e-6 \
                    and tm.bounds[1][1] <= PLATE + 1e-6, f"{iid} deborde du plateau"
                scene.add_geometry(tm, node_name=iid.replace("#", "_"), geom_name=iid.replace("#", "_"))
            num = len([q for q in plates if plates.index(q) <= plates.index(p)])
            p["file"] = f"plateau_{num:02d}_{p['color']}_{'option_taud' if p.get('option') else p['index']}.3mf"
            with open(os.path.join(pdir, p["file"]), "wb") as f:
                f.write(scene.export(file_type="3mf"))
    return C, meshes, plates, report


def short_name(n):
    n = n.replace("coussin_", "").replace("bandes_", "bandes ").replace("banquette_", "banq. ").replace("plat_bord_", "plat-bord ")
    return n.replace("_", " ")


def placed_meshes(meshes, p):
    """[(nom, maillage en place sur le plateau)] d'un plateau."""
    out = []
    for (iid, x, y, rot) in p["items"]:
        tm = meshes[iid.split("#")[0]].copy()
        if rot:
            tm.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
            tm.apply_translation(-tm.bounds[0])
        tm.apply_translation([MARGIN + x, MARGIN + y, 0])
        out.append((iid.split("#")[0], tm))
    return out


def plates_png(meshes, plates, path, label=None):
    """Vue de dessus de chaque plateau : pieces numerotees sur un plateau sombre (clair pour le noir), legende a cote."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    label = label or short_name
    n = len(plates); cols = 2; rows = (n + cols - 1) // cols
    fig = plt.figure(figsize=(cols * 7.4, rows * 4.25))
    gs = fig.add_gridspec(rows, cols * 2, width_ratios=[1.0, 0.95] * cols, wspace=0.03, hspace=0.16,
                          left=0.01, right=0.99, top=0.975, bottom=0.01)
    for k, p in enumerate(plates):
        r, c = divmod(k, cols)
        ax = fig.add_subplot(gs[r, 2 * c]); lg = fig.add_subplot(gs[r, 2 * c + 1]); lg.axis("off")
        dark = p["color"] != "noir"
        ax.add_patch(plt.Rectangle((0, 0), PLATE, PLATE, fc="#43464b" if dark else "#dfe2e6", ec="#222", lw=1.0))
        rgb = COLORS[p["color"]][1]
        placed = placed_meshes(meshes, p)
        # numeros dans l'ordre de lecture (haut -> bas, gauche -> droite)
        names = []
        for nm, tm in sorted(placed, key=lambda t: (-round(t[1].bounds[:, 1].mean() / 30.0), t[1].bounds[:, 0].mean())):
            if nm not in names:
                names.append(nm)
        num = {nm: i + 1 for i, nm in enumerate(names)}
        qty = {nm: sum(1 for m, _ in placed if m == nm) for nm in names}
        for nm, tm in placed:
            tris = tm.triangles[:, :, :2]
            ax.add_collection(PolyCollection(tris, facecolors=[rgb], edgecolors=[rgb], linewidths=0.2))
            cen = tris.mean(1); bc = tm.bounds[:, :2].mean(0)
            pt = cen[np.argmin(((cen - bc) ** 2).sum(1))]          # point sur la piece, au plus pres du centre
            ax.text(pt[0], pt[1], str(num[nm]), fontsize=5.6, ha="center", va="center", color="#111", zorder=5,
                    bbox=dict(boxstyle="circle,pad=0.15", fc="white", ec="#222", lw=0.4))
        ax.set_xlim(-3, PLATE + 3); ax.set_ylim(-3, PLATE + 3); ax.set_aspect("equal"); ax.axis("off")
        title = f"Plateau {k + 1} – {COLORS[p['color']][0]}" + (" – option" if p.get("option") else "")
        ax.set_title(title, fontsize=9.5, weight="bold", loc="left")
        nums = [str(num[nm]) for nm in names]
        lines = [label(nm) + (f" ×{qty[nm]}" if qty[nm] > 1 else "") for nm in names]
        ncol = 1 if len(lines) <= 17 else 2
        per = (len(lines) + ncol - 1) // ncol
        fs = 7.0 if ncol == 1 else 6.0
        lg.text(0.0, 1.0, f"{p.get('file', '')}  ·  {len(placed)} pièce{'s' if len(placed) > 1 else ''}",
                fontsize=7, color="#666", va="top", transform=lg.transAxes)
        for j in range(ncol):
            x0 = j * 0.5
            lg.text(x0 + 0.04, 0.93, "\n".join(nums[j * per:(j + 1) * per]), fontsize=fs, va="top", ha="right",
                    multialignment="right", linespacing=1.38, color="#555", transform=lg.transAxes)
            lg.text(x0 + 0.06, 0.93, "\n".join(lines[j * per:(j + 1) * per]), fontsize=fs, va="top",
                    linespacing=1.38, transform=lg.transAxes)
    plt.savefig(path, dpi=110, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    C, meshes, plates, report = build_all()
    for r in report:
        print(f"{r[0]:6s} {r[1]:28s} x{r[2]}  {r[3][0]:6.1f} x {r[3][1]:6.1f} x {r[3][2]:6.1f} mm  watertight={r[4]} bodies={r[5]}")
    for k, p in enumerate(plates):
        print(f"plateau {k + 1:2d} {p['color']:6s} : {len(p['items'])} pieces -> {p.get('file')}")
    plates_png(meshes, plates, os.path.join(OUT, "plateaux_apercu.png"))


# ------------------------------------------------------------------ assemblage colore (rendus, visionneuse)
FABRIC_RGB = {"tissu_coussins": (0.66, 0.59, 0.52), "tissu_bandes": (0.93, 0.89, 0.80), "tissu_taud": (0.18, 0.18, 0.20)}


def assembly_parts(C=None, fabric=True):
    """[(nom, couleur, instance_index, manifold, explode_mm)] pour l'assemblage complet."""
    C = C or catalog()
    out = []
    for e in C:
        if e.get("option"):
            continue
        for k, m in enumerate(e["asm"]):
            out.append((e["name"], e["color"], k, m, e["explode"]))
    if fabric:
        out.append(("tissu_taud", "toile", 0, M.build_taud_fabric(), (0, 0, 110)))
    return out


def rgb_of(color):
    return COLORS[color][1] if color in COLORS else {"tissu": FABRIC_RGB["tissu_coussins"], "bande": FABRIC_RGB["tissu_bandes"],
                                                      "toile": FABRIC_RGB["tissu_taud"]}[color]
