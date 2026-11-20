"""Coques v25 sans colle : les 2 moities v23 (soudees en v24) + toutes les modifications d'emboitement.
Repere de la visionneuse (mm, y vers le haut) : (x, z, -y) bateau x 52,63.

  1. les 5 trous de goupille de la jonction sont rebouches ;
  2. 4 cles de jonction en forme d'os, enfoncees par le dessus : 2 dans les plats-bords (tete arriere plus grosse :
     detrompeur ; la tete arriere passe sous le tapis SeaDek n 4 qui la bloque), 2 dans le plancher ;
  3. 3 tenons losange (cercle inscrit 3 mm) sur la face de la coque arriere, 3 logements dans la coque avant ;
  4. chaise moteur : 4 logements losange a la place des trous de goupille ;
  5. filets noirs : mini-logements le long des rainures (flancs et tableau) ;
  6. banquette avant : les 18 tenons sous les coussins passent de 2,0 a 2,1 mm (leurs logements font 2,3 mm) ;
  7. console : trou d'axe du volant rebouche, tenon losange pour la pompe ; logement losange de la manette ;
  8. dossier arriere : 3 mini-logements losange pour le dos taupe.
"""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, pickle
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/v25')
import numpy as np, trimesh
from manifold3d import Manifold, Mesh, OpType, CrossSection
import model as M, fit as F
import fit25 as G

MM = M.MM
B2V = [[MM, 0, 0, 0], [0, 0, MM, 0], [0, -MM, 0, 0]]          # bateau (m, z haut) -> visionneuse (mm, y haut)
XJ = M.SPLITS[0] * MM                                          # plan de joint : x = 200 mm


def v(p): return np.array([p[0], p[2], -p[1]]) * MM
def vd(d): return np.array([d[0], d[2], -d[1]], float)
def man(V, Fc): return Manifold(Mesh(np.asarray(V, np.float32), np.asarray(Fc, np.uint32)))
def tm_of(m):
    me = m.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)


H = pickle.load(open(ROOT + '/v24/coques_soudees.pkl', 'rb'))
REAR, FRONT = man(*H['blanc__coque_arriere__0']), man(*H['blanc__coque_avant__0'])
vol0 = (REAR.volume(), FRONT.volume())
probe = trimesh.Trimesh(*map(np.asarray, H['blanc__coque_arriere__0']), process=False)
probe_f = trimesh.Trimesh(*map(np.asarray, H['blanc__coque_avant__0']), process=False)


def top_y(tm, x, z):
    loc, _, _ = tm.ray.intersects_location([[x, 150.0, z]], [[0, -1.0, 0]])
    return float(loc[:, 1].max())


add_r, add_f, cut_r, cut_f = [], [], [], []
report = []

# ---- 1. goupilles de la jonction rebouchees
_, jpts = M.joint_holes(M.SPLITS[0])
for (y, z) in jpts:
    c = v((M.SPLITS[0], y, z))
    cyl = Manifold.cylinder(6.8, 1.08, 1.08, 32).rotate([0, 90, 0])            # axe x, de 0 a 6,8
    add_r.append(cyl.translate([XJ - 6.8, c[1], c[2]]))
    add_f.append(cyl.translate([XJ, c[1], c[2]]))

# ---- 2. cles de jonction (os) : profil dans le plan (x, z), enfoncees selon -y
KEYS = []


def rot_local(m, x0, y0, z0):
    """local (lx, ly, lz) -> visionneuse (x0 + lx, y0 + lz, z0 - ly)."""
    return m.transform([[1, 0, 0, x0], [0, 0, 1, y0], [0, -1, 0, z0]])


def bone_cs(a, Rr, Rf, w, grow=0.0, shift=0.0):
    """Os a 2 tetes (arriere Rr en -a, avant Rf en +a) ; grow : jeu ; shift : tetes rapprochees (cle)."""
    aa = a - shift
    hr = CrossSection.circle(Rr + grow, 56).translate([-aa, 0.0])
    hf = CrossSection.circle(Rf + grow, 56).translate([aa, 0.0])
    return hr + hf + CrossSection.square([2 * aa, 2 * (w + grow)]).translate([-aa, -(w + grow)])


def key_piece(cs, h_rear, h_front, x_step, lead=0.5, inset=0.25):
    """Cle debout (z local) : hauteur h_front devant x_step (local), h_rear derriere ; bas en retrait (entree)."""
    body = Manifold.extrude(cs, h_front - lead).translate([0, 0, lead]) + Manifold.extrude(cs.offset(-inset, F.JoinType.Round), lead)
    if h_rear < h_front - 1e-6:
        body = body - Manifold.cube([50, 50, h_front - h_rear + 1]).translate([-50 + x_step, -25, h_rear])
    return body


C = G.C
# plats-bords : bord avant du logement du tapis SeaDek n 4 (le dessus du plat-bord y remonte de 67,1 a 68,2 mm)
for zk, nm in ((-57.2, 'babord'), (57.2, 'tribord')):
    xs = np.arange(195.0, 199.0, 0.02)
    ys = np.array([top_y(probe, x, zk) for x in xs])
    x_step = float(xs[np.argmax(ys > ys.min() + 0.5)])
    y_rec, y_top = float(ys.min()), top_y(probe_f, 203.0, zk)
    depth = 14.0
    y_bot = y_top - depth
    a, Rr, Rf, w = 4.5, 2.4, 2.0, 1.1
    chan = Manifold.extrude(bone_cs(a, Rr, Rf, w, grow=C), depth + 3.0)
    chan = rot_local(chan, XJ, y_bot, zk)
    key_l = key_piece(bone_cs(a, Rr, Rf, w, shift=C), y_rec - 0.10 - y_bot, y_top - 0.15 - y_bot, x_step - XJ)
    KEYS.append(dict(name='cle_jonction_plat_bord', side=nm, local=key_l, asm=rot_local(key_l, XJ, y_bot, zk)))
    cut_r.append(chan); cut_f.append(chan)
    report.append(f"cle plat-bord {nm} : z {zk}, recess {y_rec:.2f} jusqu'a x {x_step:.2f}, dessus {y_top:.2f}, fond {y_bot:.2f}")
# plancher
for zk in (-22.0, 22.0):
    y_top = min(top_y(probe, XJ - 3, zk), top_y(probe_f, XJ + 3, zk))
    depth = 11.0
    y_bot = y_top - depth
    a, R, w = 5.5, 2.8, 1.4
    chan = rot_local(Manifold.extrude(bone_cs(a, R, R, w, grow=C), depth + 3.0), XJ, y_bot, zk)
    key_l = key_piece(bone_cs(a, R, R, w, shift=C), y_top - 0.15 - y_bot, y_top - 0.15 - y_bot, 0.0)
    KEYS.append(dict(name='cle_jonction_fond', side='babord' if zk > 0 else 'tribord', local=key_l, asm=rot_local(key_l, XJ, y_bot, zk)))
    cut_r.append(chan); cut_f.append(chan)
    report.append(f"cle plancher z {zk} : dessus {y_top:.2f}, fond {y_bot:.2f}")

# ---- 3. tenons losange de la jonction (coque arriere -> coque avant)
for (zz, yy) in ((-10.0, 17.0), (10.0, 17.0), (0.0, 7.5)):
    p = np.array([XJ, yy, zz])
    add_r.append(G.diamond_peg(p, (1, 0, 0), (0, 1, 0), 1.5, 6.0, 0.4, 0.5))
    cut_f.append(G.diamond_hole(p, (1, 0, 0), (0, 1, 0), 1.5 + C, 6.5, 0.3))

# ---- 4. chaise moteur : logements losange (les embases portent les tenons)
for s in (1, -1):
    for zl in M.ENG_PIN_Z:
        p = v((M.ENG_X, s * M.ENG_Y, M.ENG_Z + zl))
        cut_r.append(G.diamond_hole(p, (1, 0, 0), (0, 1, 0), 1.0 + C, 5.4, 0.25))

# ---- 5. filets noirs : mini-logements au fond des rainures
import stripes25 as ST
for (xb, pb, nb) in ST.hull_stud_points():
    m = F.socket(pb, nb, F.STUD_S_R, F.STUD_S_H).transform(B2V)
    (cut_r if xb < M.SPLITS[0] else cut_f).append(m)

# ---- 6. banquette avant : tenons 2,0 -> 2,1 mm (logements des coussins : 2,3 mm)
V23 = pickle.load(open(ROOT + '/v23/v23b.pkl', 'rb'))
hull_all = REAR + FRONT
n_big = 0
for k in V23:
    if not k.startswith('taupe__coussin_avant_'): continue
    c = man(*V23[k]); feats = [q for q in ((hull_all ^ Manifold.hull(c)) - c).decompose() if q.volume() > 0.5]
    for q in feats:
        b = np.array(q.bounding_box()); cx, cz = (b[0] + b[3]) / 2, (b[2] + b[5]) / 2; y0 = b[1]
        rr = F.STUD_R * MM + (G.OLD_FIT * MM - C)                # 1,05
        body = Manifold.cylinder(1.5 - 0.25 + 0.3, rr, rr, 40).rotate([-90, 0, 0]).translate([cx, y0 - 0.3, cz])
        tip = Manifold.cylinder(0.25 + 0.02, rr, rr - 0.25, 40).rotate([-90, 0, 0]).translate([cx, y0 + 1.25 - 0.02, cz])
        (add_r if cx < XJ else add_f).append(body + tip); n_big += 1
report.append(f"tenons de la banquette avant agrandis : {n_big}")

# ---- 7. console : axe du volant rebouche + tenon losange (pompe) ; manette : logement losange
n = M.WHEEL_N
t_face = (M.CON_AFT_X - M.WHEEL_C[0]) / (-n[0])
q = lambda t: M.WHEEL_C - t * n
L_f = 0.28 + M.mm2m(0.3) - (t_face - M.mm2m(1.0))
fill = Manifold.cylinder(L_f, M.mm2m(1.12), M.mm2m(1.12), 32).transform(G._frame(q(t_face - M.mm2m(1.0)), -n, (0, 0, 1)))
fill = fill ^ M.box(M.CON_AFT_X, 9.0, -9.0, 9.0, -9.0, 9.0)                # coupe exactement a la face de la console
add_r.append(fill.transform(B2V))
add_r.append(G.dpeg(q(t_face), n, (0, 0, 1), M.mm2m(1.0), M.mm2m(3.5)).transform(B2V))
yc = (M.THR["y0"] + M.THR["y1"]) / 2; zc = (M.THR["z0"] + M.THR["z1"]) / 2
cut_r.append(G.dhole((M.THR_X, yc, zc), (1, 0, 0), (0, 0, 1), M.mm2m(1.0), M.mm2m(4.4)).transform(B2V))

# ---- 8. dossier arriere : 3 mini-logements losange pour le dos taupe
import back25 as BK
for (p, d) in BK.peg_frames():
    cut_r.append(G.dhole(p + d * BK.GAP, d, (0, 0, 1), BK.RI, BK.DEPTH).transform(B2V))

REAR = Manifold.batch_boolean([REAR] + add_r, OpType.Add) - Manifold.batch_boolean(cut_r, OpType.Add)
FRONT = Manifold.batch_boolean([FRONT] + add_f, OpType.Add) - Manifold.batch_boolean(cut_f, OpType.Add)
B = 9000.0
REAR = REAR ^ Manifold.cube([B, B, B]).translate([-B + XJ, -B / 2, -B / 2])          # rien ne depasse du plan de joint
FRONT = FRONT ^ Manifold.cube([B, B, B]).translate([XJ, -B / 2, -B / 2])

out = {}
for k, m in (('blanc__coque_arriere__0', REAR), ('blanc__coque_avant__0', FRONT)):
    t = tm_of(m)
    out[k] = (np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.int64))
    report.append(f"{k}: etanche {t.is_watertight}, corps {t.body_count}, volume {m.volume():.0f} mm3, genre {m.genus()}")
report.append(f"volumes avant : {vol0[0]:.0f} / {vol0[1]:.0f}")
keys = [dict(name=k['name'], side=k['side'], asm=tm_of(k['asm']), local=tm_of(k['local'])) for k in KEYS]
pickle.dump(dict(hulls=out, keys=keys), open(ROOT + '/v25/coques_v25.pkl', 'wb'))
print("\n".join(report))
