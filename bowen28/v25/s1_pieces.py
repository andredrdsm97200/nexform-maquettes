"""Etape 1 (v25, sans colle) : toutes les pieces SAUF coque et coussins, reconstruites avec model.py et les
emboitements v25 (fit25), orientees pour l'impression. Sortie : pieces.pkl (impression + assemblage, repere visionneuse).

Changements par rapport a la v23.1 :
  - jeu des logements ronds 0,15 -> 0,1 mm (F.FIT) ; tenons qui entrent dans la coque v23 : 2,0 -> 2,1 mm ;
  - moteur : 2 tenons losange a la place des 2 goupilles ; tenon de la jupe en losange ; (v25.3) partie grise en
    3 pieces (bloc, embase, helice) et cheville du capot, voir moteur25.py ;
  - aileron : U ajuste (jeu 0,32 -> 0,1 mm) ; gaines, flaps, verins : tenons +0,1 mm ;
  - fauteuil : trou du teton 0,2 -> 0,1 mm ; rainures des bandes blanches 0,1 -> 0,03 mm (bandes en force) ;
  - volant : encoches de la jante et trou du moyeu 0,2 -> 0,1 mm ; pompe avec tenon rond devant (dans le croisillon)
    et logement losange derriere (le tenon est sur la console) : plus de goupille de 16 mm ;
  - manette : tenon losange integre (plus de goupille de 8 mm) ; barre de console : pattes +0,1 mm dans les trous ;
  - ecran tribord : +0,1 mm par cote ; mat de pavillon : pied +0,1 mm ;
  - filets noirs : mini-tenons au dos, un fichier par cote ; dos du dossier : 3 mini-tenons losange ;
  - taud : cadres (tenons +0,1 mm, encoches 1,2 mm) + toit rigide d'une piece (noir) ; plus d'arceaux separes,
    de boitiers d'echelle, de taud TPU ni de toile ;
  - (v25.4) socle d'un seul morceau, noir, avec le nom du bateau (socle25.py) ; SeaDek en taupe (le volant reste teck).
"""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, time, pickle, inspect
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/v25')
import numpy as np, trimesh
import model as M, fit as F
import fit25 as G
import poste25 as PO                           # caisson des fauteuils v25 : fauteuils, embases et filet suivent
import pieces as P
from pieces import U, clean, lego_points
import roof25 as RF, stripes25 as ST, back25 as BK
from manifold3d import Manifold, OpType
sys.path.insert(0, _os.path.join(_os.path.dirname(ROOT), 'commun'))
import emboitements as E                       # cotes d'ecrasement (LIGNE_DE_CONDUITE.md, regle 2)

mm = M.mm2m
t0 = time.time()
C = []


def add(name, color, asm, proto=None, down=(0, 0, -1), note="", serre=None):
    """serre : la piece imprimee (avec ses cotes d'ecrasement) a sa place dans la maquette, pour le controle de
    maintien ; la maquette assemblee (asm) garde la piece nominale, au jeu standard."""
    asm = [clean(a) for a in (asm if isinstance(asm, list) else [asm])]
    proto = clean(proto) if proto is not None else asm[0]
    serre = [clean(a) for a in serre] if serre else None
    C.append(dict(name=name, color=color, qty=len(asm), asm=asm, proto=proto, down=np.asarray(down, float), note=note, option=False,
                  serre=serre))


MMU = mm(1.0)                                  # 1 mm de maquette, en metres reels (unite des cotes)


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

# ---- moteurs (v25.3, demande d'Andre du 24 novembre 2026) : la partie grise en 3 pieces imprimees a plat, voir moteur25.py
import moteur25 as MO
def engine_split25():
    Pp = M.build_outboard_parts()
    pc, nc = P.cowl_stud_frame()
    pt, nt = P.tail_stud_frame()
    cowl = Pp["capot"] - F.socket(pc, nc)                            # logement de la cheville (l'ancien tenon du gris)
    tail = Pp["jupe"] - G.dhole(pt, nt, (0, 0, 1), mm(1.0), mm(1.8))
    return cowl, tail, MO.pieces(Pp["capot"], Pp["jupe"], U(M.hose_hole_engine_local()))   # trou de gaine : jeu 0,2


cowl, tail, (bloc, emb, emb_s, hel, hel_s, chev) = engine_split25()
place2 = lambda m: [M.place_engine(m, s * M.ENG_Y) for s in (1, -1)]
nb = M.plane_normal(); down_cowl = (nb[0], 0.0, -nb[2])
add("capot_moteur", "blanc", [M.place_engine(cowl, s * M.ENG_Y) for s in (1, -1)], down=down_cowl, note="posé sur son plan de joint")
add("jupe_moteur", "blanc", [M.place_engine(tail, s * M.ENG_Y) for s in (1, -1)], down=(-nb[0], 0.0, nb[2]), note="à l'envers, sur sa face du dessus")
add("bloc_moteur", "alu", place2(bloc), proto=bloc, down=MO.BAS_BLOC, note="à l'envers, sur son plan de joint")
add("embase_moteur", "alu", place2(emb), proto=emb_s, down=MO.BAS_EMBASE, note="à l'envers, sur la plaque anti-cavitation",
    serre=place2(emb_s))
add("helice", "alu", place2(hel), proto=hel_s, down=MO.BAS_HELICE, note="debout sur l'avant du moyeu", serre=place2(hel_s))
add("cheville_capot", "alu", place2(chev), proto=MO.cheville_local(), note="debout")
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
L_av = M.PUMP_GAP + M.BOSS_H - mm(0.8) - mm(0.15)
pump = pump + F.stud(pf, n, F.STUD_R, L_av)                                          # tenon rond dans le croisillon
pump = pump - G.dhole(M.WHEEL_C - (t_face + mm(1.2)) * n, n, (0, 0, 1), mm(1.0), mm(3.9 + 1.2))   # logement du tenon de la console
q_f = M.WHEEL_C - t_face * n                                                         # face de la console
pump_serre = (pump + E.cotes_logement(q_f, n, (0, 0, 1), mm(1.0), mm(0.4), mm(3.0), n=4, angle0=45.0, unite=MMU)
              + E.cotes_tenon(pf, n, (0, 0, 1), F.STUD_R + mm(G.C), mm(0.3), L_av - F.STUD_TIP - mm(0.05), n=3, unite=MMU))
add("jante_volant", "teck", M.place_wheel(rim), proto=rim)
add("branches_volant", "alu", M.place_wheel(spokes), proto=spokes)
add("moyeu_volant", "teck", M.place_cap(cap), proto=cap)
add("pompe_direction", "noir", pump, proto=pump_serre, down=(1, 0, 0), note="debout sur sa base", serre=[pump_serre])
def build_throttle_double():
    """v25 (photos du bateau, 2 hors-bords) : commande double, 2 leviers sur la meme embase, un sur chaque flanc,
    poignees vers l'interieur (1 mm entre elles). Meme embase et meme tenon losange que la manette v24 (meme logement
    dans la console). Imprimee debout sur sa base : leviers inclines de 15 degres, poignees de 1 mm en porte-a-faux."""
    h = M.THR["z1"] - M.THR["z0"]; wdt = M.THR["y1"] - M.THR["y0"]
    t_arm, L_grip = 0.035, 0.05
    parts = [M.extrude_xz([(0.0, 0.0), (0.12, 0.0), (0.12, h * 0.55), (0.07, h), (0.0, h)], 0.0, wdt)]
    arm = [(0.055, h * 0.55), (0.105, h * 0.55), (0.165, h + 0.14), (0.125, h + 0.155)]
    for y0, g0 in ((0.0, 0.0), (wdt - t_arm, wdt - L_grip)):
        parts.append(M.extrude_xz(arm, y0, y0 + t_arm))                                                      # levier
        parts.append(Manifold.cylinder(L_grip, 0.026, 0.026, 24).rotate([-90, 0, 0]).translate([0.145, g0, h + 0.15]))  # poignee
        parts.append(Manifold.cylinder(t_arm, 0.045, 0.045, 24).rotate([-90, 0, 0]).translate([0.08, y0, h * 0.55]))   # moyeu
    return Manifold.batch_boolean(parts, OpType.Add)


thr = build_throttle_double()
wdt, h = M.THR["y1"] - M.THR["y0"], M.THR["z1"] - M.THR["z0"]
thr = thr + G.dpeg((0.0, wdt / 2, h / 2), (-1.0, 0.0, 0.0), (0, 0, 1), mm(1.0), mm(4.0))
thr_serre = thr + E.cotes_tenon((0.0, wdt / 2, h / 2), (-1.0, 0.0, 0.0), (0, 0, 1), mm(1.0 + G.C), mm(0.3), mm(3.4), n=4, angle0=45.0, unite=MMU)
add("manette_gaz", "noir", M.place_throttle(thr), proto=M.place_throttle(thr_serre), down=(0, 0, -1), note="debout sur sa base",
    serre=[M.place_throttle(thr_serre)])
# barre de console : pattes grossies dans les trous de la console (jeu 0,2 -> 0,1 mm)
x = M.CON_BACK_X
bar = M.console_bar()
sleeves = [M.tube_path([(x, yy, M.CB_Z), (x + 0.05, yy, M.CB_Z)], M.LAD_R + mm(0.1), 14) for yy in M.CB_Y]
ribs = U([E.cotes_tenon((x, yy, M.CB_Z), (1.0, 0.0, 0.0), (0, 0, 1), M.LAD_R + M.CLR, mm(0.3), 0.05 - mm(0.3), angles=(0.0, 100.0, 260.0), unite=MMU)
          for yy in M.CB_Y])
trim = lambda m: m.trim_by_plane([0.0, 0.0, 1.0], M.CB_Z - M.LAD_R + mm(0.25))
bar, bar_serre = trim(bar + U(sleeves)), trim(bar + U(sleeves) + ribs)
add("barre_console", "alu", bar, proto=bar_serre, serre=[bar_serre])
foot0 = M.MFD_FOOT
M.MFD_FOOT = (foot0[0] + 2 * mm(G.C), foot0[1] + 2 * mm(G.C))      # empreinte de la coque v23 : jeu 0,2 -> 0,1 mm
mfd = M.build_mfd()
M.MFD_FOOT = foot0
o_m, u_m, v_m, n_m = M.mfd_foot_frame()
mfd_serre = mfd + E.cotes_logement(o_m + n_m * (-M.MFD_REC + mm(0.02)), n_m, u_m, F.STUD_R, mm(0.4), mm(1.75), n=3, unite=MMU)
add("ecran_mfd", "noir", mfd, proto=mfd_serre, down=M.mfd_down(), note="debout sur sa base", serre=[mfd_serre])
(dx0, dz0), (dx1, dz1) = M.DASH
for i in range(len(M.SCREENS)):
    # Empreinte de la coque v23 : paroi a 0,2 mm sur les 4 cotes jusqu'a 0,8 mm de profondeur ; plus bas, la paroi du
    # haut de la pente rentre (0,06 mm a 1,1 mm). Ecran : +0,1 mm par cote (jeu standard), sauf vers le haut de la pente
    # (+0,05 mm, comme en v24) ; une cote d'ecrasement par flanc, entre 0,1 et 0,75 mm de profondeur.
    xc, yc, lx, ly = M.SCREENS[i]
    g, g_haut, g_bas = mm(G.C), mm(0.05), mm(0.05)
    loc = M.box(-lx / 2 - g, lx / 2 + g_haut, -ly / 2 - g, ly / 2 + g, -0.02 - g_bas, 0.012)     # repere de screen_box
    ribs = U([E.cote_flanc((0, 0, 0), (0, 0, 1), nrm, half + M.CLR, -mm(0.75), -mm(0.1), unite=MMU)
              for nrm, half in (((1, 0, 0), lx / 2), ((-1, 0, 0), lx / 2), ((0, 1, 0), ly / 2), ((0, -1, 0), ly / 2))])
    ang = -np.degrees(np.arctan2(dz1 - dz0, dx1 - dx0))
    place = lambda m: m.rotate([0, ang, 0]).translate([xc + M.DXC, yc, M.dash_z(xc)])
    to_plate = lambda m: m.translate([lx / 2 + g, ly / 2 + g, 0.02 + g_bas])
    add("ecran_tribord", "noir", place(loc), proto=to_plate(loc + ribs), serre=[place(loc + ribs)])
ns = patched([M.build_switch_flat], {"build_switch_flat": [("parts = [box(0, W, 0, H, 0, SW_T)]", "parts = [box(-G_SW, W + G_SW, -G_SW, H + G_SW, 0, SW_T)]")]})
ns["G_SW"] = mm(G.C)                                                  # empreinte de la coque v23 : jeu 0,2 -> 0,1 mm
sw = ns["build_switch_flat"]()
Wsw, Hsw = M.SW_Y[1] - M.SW_Y[0], M.SW_Z[1] - M.SW_Z[0]
rb = lambda p, nrm, paroi: E.cote_flanc(p, (0, 0, 1), nrm, paroi, mm(0.15), M.SW_REC - mm(0.1), unite=MMU)
sw_serre = sw + U([rb((uu, Hsw / 2, 0), (0, s, 0), Hsw / 2 + M.CLR) for uu in (Wsw / 4, 3 * Wsw / 4) for s in (1, -1)]
                  + [rb((Wsw / 2, Hsw / 2, 0), (s, 0, 0), Wsw / 2 + M.CLR) for s in (1, -1)])
add("interrupteurs", "noir", M.place_switch(sw), proto=sw_serre, serre=[M.place_switch(sw_serre)])

# ---- taud : 2 cadres + toit rigide d'une piece
frames = [RF.build_frame25(s) for s in (1, -1)]
add("cadre_taud", "alu", frames, proto=RF.build_frame25(1), down=(0, 1, 0))
roof = RF.build_roof()
add("toit_taud", "noir", roof, down=(0, 0, 1), note="à l'envers, dessus sur le plateau, sans support")

# ---- pont, plats-bords, tableau
import echelle25 as EC
add("echelle_bain", "alu", EC.build(), note="à plat, repliée")              # v25 : repliee, tournee de 90 deg
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
for name, tile, surf in tiles:                # v25.4 : SeaDek en taupe, comme les coussins (demande d'Andre)
    add(name, "taupe", M.place_on_surface(tile, surf), proto=tile, down=(0, 0, 1), note="à l'envers : dessus sur le plateau, tenons vers le haut")
add("dos_dossier_arriere", "taupe", BK.build(), note="debout")
import pare_battages25 as PBT                  # v25 : 4 pare-battages pendus a une ficelle (anneaux dans la coque)
for nom, (asm_pb, proto_pb, down_pb) in PBT.pieces().items():  # v25.2 : et leurs crochets, accroches a l'anneau
    if nom == 'crochet_pare_battage':
        add(nom, "alu", asm_pb, proto=proto_pb, down=down_pb, note="à plat")
    else:
        add(nom, "noir", asm_pb, proto=proto_pb, down=down_pb, note="debout, œil en haut")
light, dark = M.build_bolsters()
light = light ^ M.build_cockpit_cutter()
light = light - U([F.socket(p) for p in bol_pts])
add("boudin_babord", "taupe", light ^ M.box(-B, B, 0, B, -B, B))
add("boudin_tribord", "taupe", light ^ M.box(-B, B, -B, 0, -B, B))
shell, _hull = M.build_hull()
hull_full = shell + M.build_bracket()
import socle25 as SO                          # v25.4 : socle d'un seul morceau, noir, nom du bateau et Nexform 3D Marine
add("socle", "noir", SO.socle(hull_full), note="à plat, tel qu'il est posé")
print('catalogue v25 sans coque ni coussins :', len(C), 'entrees en', round(time.time() - t0), 's', flush=True)


def view(tm):
    V = np.asarray(tm.vertices); return np.c_[V[:, 0], V[:, 2], -V[:, 1]].astype(np.float32), np.asarray(tm.faces, np.int64)


out = []
for e in C:
    tm = P.print_mesh(e)
    asm = [view(P.to_tm(a, welded=False)) for a in e['asm']]
    out.append(dict(name=e['name'], color=e['color'], qty=e['qty'], note=e['note'], option=False, V=np.asarray(tm.vertices), F=np.asarray(tm.faces),
                    watertight=bool(tm.is_watertight), bodies=int(tm.body_count), vol_print=float(tm.volume),
                    vol_asm=sum(float(P.to_tm(a).volume) for a in e['asm']), asm=asm,
                    serre=[view(P.to_tm(a, welded=False)) for a in e['serre']] if e.get('serre') else None))
    if not (tm.is_watertight and tm.body_count == 1):
        print('  ATTENTION', e['name'], tm.is_watertight, tm.body_count)
pickle.dump(out, open(ROOT + '/v25/pieces.pkl', 'wb'))
print('pieces orientees', len(out), 'en', round(time.time() - t0), 's')
