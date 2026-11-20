"""Etape 1 (v25, sans colle) : toutes les pieces SAUF coque et coussins, reconstruites avec model.py et les
emboitements v25 (fit25), orientees pour l'impression. Sortie : pieces.pkl (impression + assemblage, repere visionneuse).

Changements par rapport a la v23.1 :
  - jeu des logements ronds 0,15 -> 0,1 mm (F.FIT) ; tenons qui entrent dans la coque v23 : 2,0 -> 2,1 mm ;
  - embase moteur : 2 tenons losange a la place des 2 goupilles ; tenon de la jupe en losange ;
  - aileron : U ajuste (jeu 0,32 -> 0,1 mm) ; gaines, flaps, verins : tenons +0,1 mm ;
  - fauteuil : trou du teton 0,2 -> 0,1 mm ; rainures des bandes blanches 0,1 -> 0,03 mm (bandes en force) ;
  - volant : encoches de la jante et trou du moyeu 0,2 -> 0,1 mm ; pompe avec tenon rond devant (dans le croisillon)
    et logement losange derriere (le tenon est sur la console) : plus de goupille de 16 mm ;
  - manette : tenon losange integre (plus de goupille de 8 mm) ; barre de console : pattes +0,1 mm dans les trous ;
  - ecran tribord : +0,1 mm par cote ; mat de pavillon : pied +0,1 mm ;
  - filets noirs : mini-tenons au dos, un fichier par cote ; dos du dossier : 3 mini-tenons losange ;
  - taud : cadres (tenons +0,1 mm, encoches 1,2 mm) + toit rigide d'une piece (noir) ; plus d'arceaux separes,
    de boitiers d'echelle, de taud TPU ni de toile.
"""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, time, pickle, inspect
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/v25')
import numpy as np, trimesh
import model as M, fit as F
import fit25 as G
import pieces as P
from pieces import U, clean, lego_points
import roof25 as RF, stripes25 as ST, back25 as BK
from manifold3d import Manifold, OpType

mm = M.mm2m
t0 = time.time()
C = []


def add(name, color, asm, proto=None, down=(0, 0, -1), note=""):
    asm = [clean(a) for a in (asm if isinstance(asm, list) else [asm])]
    proto = clean(proto) if proto is not None else asm[0]
    C.append(dict(name=name, color=color, qty=len(asm), asm=asm, proto=proto, down=np.asarray(down, float), note=note, option=False))


def patched(fns, repl):
    """Recompile des fonctions de model.py avec des remplacements de texte (dans un espace de noms a part)."""
    ns = dict(vars(M))
    for fn in fns:
        src = inspect.getsource(fn)
        for a, b in repl.get(fn.__name__, []):
            assert a in src, (fn.__name__, a)
            src = src.replace(a, b)
        exec(src, ns)
    return ns


class hull_studs:
    """Pendant le bloc : F.stud fait des tenons de 2,1 mm (ils entrent dans des logements de la coque v23)."""
    def __enter__(self):
        self.d = F.stud.__defaults__; F.stud.__defaults__ = (self.d[0], G.STUD_R_HULL, self.d[2])
    def __exit__(self, *a):
        F.stud.__defaults__ = self.d


ped_pts, bol_pts = lego_points()
B = 9.0

# ---- moteurs
def engine_split25():
    Pp = M.build_outboard_parts()
    grey = Pp["gris"] - Pp["capot"] - Pp["jupe"]
    grey = grey - U(M.hose_hole_engine_local())                     # trou de gaine : jeu 0,2 (la gaine grossit de 0,1)
    pc, nc = P.cowl_stud_frame()
    pt, nt = P.tail_stud_frame()
    grey = grey + F.stud(pc, nc)                                     # presque vertical : rond
    grey = grey + G.dpeg(pt, nt, (0, 0, 1), mm(1.0), mm(1.5))       # couche : losange
    for zl in M.ENG_PIN_Z:                                           # 2 tenons losange vers la chaise
        grey = grey + G.dpeg((0.0, 0.0, zl), (-1.0, 0.0, 0.0), (0, 0, 1), mm(1.0), mm(5.0))
    return Pp["capot"] - F.socket(pc, nc), Pp["jupe"] - G.dhole(pt, nt, (0, 0, 1), mm(1.0), mm(1.8)), grey


cowl, tail, grey = engine_split25()
nb = M.plane_normal(); down_cowl = (nb[0], 0.0, -nb[2])
add("capot_moteur", "blanc", [M.place_engine(cowl, s * M.ENG_Y) for s in (1, -1)], down=down_cowl, note="posé sur son plan de joint")
add("jupe_moteur", "blanc", [M.place_engine(tail, s * M.ENG_Y) for s in (1, -1)], down=(-nb[0], 0.0, nb[2]), note="à l'envers, sur sa face du dessus")
add("embase_moteur", "alu", [M.place_engine(grey, s * M.ENG_Y) for s in (1, -1)], note="debout, supports arborescents")
foil = patched([M.build_hydrofoil], {"build_hydrofoil": [("(x1 - x0) / 2 + 0.006, b0 + 0.006", "(x1 - x0) / 2 + 0.0019, b0 + 0.0019")]})["build_hydrofoil"]()
add("aileron_moteur", "noir", [M.place_engine(foil, s * M.ENG_Y) for s in (1, -1)], proto=foil)
M.HOSE_PEG_R = 0.016 + mm(0.10)                                       # trous (coque, moteur) : 0,016 + 0,2 mm
add("gaine_moteur", "noir", [M.build_hose(1), M.build_hose(-1)], proto=M.build_hose(1), down=M.hose_down(1), note="à plat sur un méplat")
M.TAB_PEG_R = mm(0.7)                                                 # trous de la coque : 0,6 + 0,2 mm
tab = M.build_tab_local()
add("flap", "alu", [M.place_tab(tab, 1), M.place_tab(tab, 1).mirror([0, 1, 0])], proto=tab, note="à plat, charnière vers le haut")
add("verin_flap", "noir", [M.build_actuator(1), M.build_actuator(-1)], proto=M.build_actuator(1), down=(0, -1, 0), note="couché sur le flanc")

# ---- poste de pilotage
ns = patched([M.bucket_seat_v16, M.bucket_seat_v19], {"bucket_seat_v16": [("PIN_R + mm2m(0.2), PIN_R + mm2m(0.2)", "PIN_R + mm2m(0.1), PIN_R + mm2m(0.1)")]})
ns["STRIPE_CLR"] = mm(0.03)                                           # rainures des bandes : 0,03 mm par cote
seat = ns["bucket_seat_v19"]()
add("fauteuil", "taupe", [M.place_seat(seat, s) for s in (1, -1)], proto=seat, note="debout, cavité vers le haut")
band = M.seat_band()
add("bande_fauteuil", "blanc", [M.place_seat(band.translate([0, sy * M.SEAT_BAND_C, 0]), s) for s in (1, -1) for sy in (1, -1)], proto=band, down=(0, -1, 0), note="couchée sur le flanc")
add("embase_fauteuil", "alu", [M.build_seat_base(s) - F.socket(p) for s, p in zip((1, -1), ped_pts)])
with hull_studs():
    net = M.build_net_flat()
add("filet_caisson", "noir", M.place_net(net), proto=net, down=(0, 0, 1), note="face visible sur le plateau, tenons vers le haut")
M.WHEEL_NOTCH = mm(0.10)
rim = M.build_wheel_rim()
ns = patched([M.build_wheel_spokes, M.build_wheel_cap, M.build_helm_pump],
             {"build_wheel_spokes": [("mm2m(1.0), mm2m(1.0), 16).translate([0, 0, -0.05])", "mm2m(1.1), mm2m(1.1), 32).translate([0, 0, -0.05])")],
              "build_wheel_cap": [("BOSS_R + CLR, BOSS_R + CLR", "BOSS_R + mm2m(0.1), BOSS_R + mm2m(0.1)")],
              "build_helm_pump": [("    return m - hole.transform(", "    return m\n    _ = (")]})
spokes, cap = ns["build_wheel_spokes"](), ns["build_wheel_cap"]()
n = M.WHEEL_N
pf = M.WHEEL_C - (M.RIM_ZC + M.PUMP_GAP) * n                         # face avant de la pompe
t_face = (M.CON_AFT_X - M.WHEEL_C[0]) / (-n[0])
pump = ns["build_helm_pump"]()
pump = pump + F.stud(pf, n, F.STUD_R, M.PUMP_GAP + M.BOSS_H - mm(0.8) - mm(0.15))      # tenon rond dans le croisillon
pump = pump - G.dhole(M.WHEEL_C - (t_face + mm(1.2)) * n, n, (0, 0, 1), mm(1.0), mm(3.9 + 1.2))   # logement du tenon de la console
add("jante_volant", "teck", M.place_wheel(rim), proto=rim)
add("branches_volant", "alu", M.place_wheel(spokes), proto=spokes)
add("moyeu_volant", "teck", M.place_cap(cap), proto=cap)
add("pompe_direction", "noir", pump, down=(1, 0, 0), note="debout sur sa base")
ns = patched([M.build_throttle], {"build_throttle": [("    return t - cyl_x(", "    return t\n    _ = (")]})
thr = ns["build_throttle"]()
wdt, h = M.THR["y1"] - M.THR["y0"], M.THR["z1"] - M.THR["z0"]
thr = thr + G.dpeg((0.0, wdt / 2, h / 2), (-1.0, 0.0, 0.0), (0, 0, 1), mm(1.0), mm(4.0))
add("manette_gaz", "noir", M.place_throttle(thr), down=(0, 1, 0), note="couchée sur le flanc")
# barre de console : pattes grossies dans les trous de la console (jeu 0,2 -> 0,1 mm)
x = M.CON_BACK_X
bar = M.console_bar()
sleeves = [M.tube_path([(x, yy, M.CB_Z), (x + 0.05, yy, M.CB_Z)], M.LAD_R + mm(0.1), 14) for yy in M.CB_Y]
bar = (bar + U(sleeves)).trim_by_plane([0.0, 0.0, 1.0], M.CB_Z - M.LAD_R + mm(0.25))
add("barre_console", "alu", bar)
add("ecran_mfd", "noir", M.build_mfd(), down=M.mfd_down(), note="debout sur sa base")
for i in range(len(M.SCREENS)):
    xc, yc, lx, ly = M.SCREENS[i]
    add("ecran_tribord", "noir", M.screen_box(i, mm(0.05)), proto=M.box(0, lx + 2 * mm(0.05), 0, ly + 2 * mm(0.05), 0, 0.032 + mm(0.05)))
sw = M.build_switch_flat()
add("interrupteurs", "noir", M.place_switch(sw), proto=sw)

# ---- taud : 2 cadres + toit rigide d'une piece
frames = [RF.build_frame25(s) for s in (1, -1)]
add("cadre_taud", "alu", frames, proto=RF.build_frame25(1), down=(0, 1, 0))
roof = RF.build_roof()
add("toit_taud", "noir", roof, down=(0, 0, 1), note="à l'envers, dessus sur le plateau, sans support")

# ---- pont, plats-bords, tableau
add("echelle_bain", "alu", M.build_ladder())
with hull_studs():
    cl = M.build_cleat()
    tiles = M.seadeck_tiles()
add("taquet", "alu", [M.place_cleat(cl, x, y, a) for (x, y, a) in M.cleat_spots()], proto=cl, down=(0, 0, 1), note="à l'envers, tenon vers le haut")
pole = M.build_flagpole(flat=False)
fx, fy = M.flag_xy(); fz0 = float(M.zs(fx))
pole = pole + Manifold.cylinder(M.FLAG_SOCK - M.SD_REC - mm(1.15), M.FLAG_R + mm(0.1), M.FLAG_R + mm(0.1), 32).translate([fx, fy, fz0 - M.FLAG_SOCK])   # sous le tapis
pole = pole.trim_by_plane([0.0, -1.0, 0.0], -(fy + M.FLAG_R * 1.2 - mm(0.3)))
pole = pole.translate([0, 0, mm(0.06)])                                   # la collerette pose sur le tapis
add("mat_pavillon", "alu", pole, down=(0, -1, 0))
eye = M.build_eye_local()
add("anneau_tableau", "alu", [M.place_eye(eye, s) for s in (1, -1)], proto=eye, down=(0, -1, 0))
for seg in ('arriere', 'avant'):
    for s, sn in ((1, 'babord'), (-1, 'tribord')):
        add(f"filet_noir_{seg}_{sn}", "noir", ST.side_asm(seg, s), proto=ST.side_flat(seg, s), note="à plat, face visible sur le plateau, tenons vers le haut")
for s, sn in ((1, 'babord'), (-1, 'tribord')):
    add(f"filet_noir_tableau_{sn}", "noir", ST.transom_asm(s), down=(-1, 0, 0), note="face visible sur le plateau, tenons vers le haut")
for name, tile, surf in tiles:
    add(name, "teck", M.place_on_surface(tile, surf), proto=tile, down=(0, 0, 1), note="à l'envers : dessus sur le plateau, tenons vers le haut")
add("dos_dossier_arriere", "taupe", BK.build(), note="debout")
light, dark = M.build_bolsters()
light = light ^ M.build_cockpit_cutter()
light = light - U([F.socket(p) for p in bol_pts])
add("boudin_babord", "taupe", light ^ M.box(-B, B, 0, B, -B, B))
add("boudin_tribord", "taupe", light ^ M.box(-B, B, -B, 0, -B, B))
shell, _hull = M.build_hull()
hull_full = shell + M.build_bracket()
add("berceau_arriere", "alu", M.build_cradle2(1.05, hull_full))
add("berceau_avant", "alu", M.build_cradle2(5.15, hull_full))
print('catalogue v25 sans coque ni coussins :', len(C), 'entrees en', round(time.time() - t0), 's', flush=True)


def view(tm):
    V = np.asarray(tm.vertices); return np.c_[V[:, 0], V[:, 2], -V[:, 1]].astype(np.float32), np.asarray(tm.faces, np.int64)


out = []
for e in C:
    tm = P.print_mesh(e)
    asm = [view(P.to_tm(a, welded=False)) for a in e['asm']]
    out.append(dict(name=e['name'], color=e['color'], qty=e['qty'], note=e['note'], option=False, V=np.asarray(tm.vertices), F=np.asarray(tm.faces),
                    watertight=bool(tm.is_watertight), bodies=int(tm.body_count), vol_print=float(tm.volume),
                    vol_asm=sum(float(P.to_tm(a).volume) for a in e['asm']), asm=asm))
    if not (tm.is_watertight and tm.body_count == 1):
        print('  ATTENTION', e['name'], tm.is_watertight, tm.body_count)
pickle.dump(out, open(ROOT + '/v25/pieces.pkl', 'wb'))
print('pieces orientees', len(out), 'en', round(time.time() - t0), 's')
