"""Eprouvette de reglage (a imprimer AVANT le kit, en blanc, 10 min) : elle reprend a l'identique les 4 emboitements
du kit, avec le meme jeu de 0,1 mm.
  A : bloc (debout, comme la coque) : tenon rond 2 mm et mini-tenon 1,4 mm dessus, tenon losange 2 mm sur la face
      de jonction, demi-logement de cle ;
  B : bloc : logement losange, autre demi-logement de cle ;
  C : plaquette (logements en dessous, comme la plupart des pieces) : logement rond 2,2 mm et mini 1,6 mm ;
  cle : la cle de jonction du plancher (meme profil), plus courte.
Montage : A + B bout a bout, cle enfoncee par le dessus, C sur les 2 tenons de A."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, pickle
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/v25')
import numpy as np, trimesh
from manifold3d import Manifold, CrossSection, OpType
import fit as F
import fit25 as G

C = G.C
L, W, H = 22.0, 14.0, 9.0                       # bloc A (x de 0 a L), B (x de L a 2L) ; face de jonction en x = L
KEY = dict(a=5.5, R=2.8, w=1.4)
HK = 7.0                                        # profondeur du logement de cle
YK = 9.5                                        # axe de la cle (y) ; le tenon losange est en y = 4, z = 4


def bone(a, R, w, grow=0.0, shift=0.0):
    aa = a - shift
    return (CrossSection.circle(R + grow, 56).translate([-aa, 0]) + CrossSection.circle(R + grow, 56).translate([aa, 0])
            + CrossSection.square([2 * aa, 2 * (w + grow)]).translate([-aa, -(w + grow)]))


def mm_stud(p, r, h):           # tenon rond (fit.stud en mm)
    body = Manifold.cylinder(h - 0.25 + 0.3, r, r, 40).translate([p[0], p[1], p[2] - 0.3])
    tip = Manifold.cylinder(0.27, r, r - 0.25, 40).translate([p[0], p[1], p[2] + h - 0.25 - 0.02])
    return body + tip


def mm_socket(p, r, h):          # logement rond, ouvert vers -z (dessous de la plaquette), entree chanfreinee
    rr = r + C
    hole = Manifold.cylinder(h + 0.35, rr, rr, 40).translate([p[0], p[1], p[2] - 0.05])
    cone = Manifold.cylinder(0.35, rr + 0.3, rr, 40).translate([p[0], p[1], p[2] - 0.05])
    return hole + cone


chan = Manifold.extrude(bone(KEY['a'], KEY['R'], KEY['w'], grow=C), HK + 2).translate([L, YK, H - HK])
A = Manifold.cube([L, W, H]) - chan
A = A + mm_stud((6.0, 4.0, H), 1.0, 1.5) + mm_stud((12.0, 4.0, H), 0.7, 1.0)
A = A + G.diamond_peg((L, 4.0, 4.0), (1, 0, 0), (0, 0, 1), 1.0, 4.0, 0.3, 0.4)
Bm = Manifold.cube([L, W, H]).translate([L, 0, 0]) - chan
Bm = Bm - G.diamond_hole((L, 4.0, 4.0), (1, 0, 0), (0, 0, 1), 1.0 + C, 4.4, 0.25)
Cp = Manifold.cube([10.0, 6.0, 3.0]).translate([3.0, 1.0, H]) - mm_socket((6.0, 4.0, H), 1.0, 1.5) - mm_socket((12.0, 4.0, H), 0.7, 1.0)
cs_key = bone(KEY['a'], KEY['R'], KEY['w'], shift=C)
key = Manifold.extrude(cs_key, HK - 0.15 - 0.5).translate([0, 0, 0.5]) + Manifold.extrude(cs_key.offset(-0.25, F.JoinType.Round), 0.5)
key_asm = key.translate([L, YK, H - HK])
asm = dict(eprouvette_A=A, eprouvette_B=Bm, eprouvette_C=Cp, eprouvette_cle=key_asm)
for a_, b_ in [('eprouvette_A', 'eprouvette_B'), ('eprouvette_A', 'eprouvette_cle'), ('eprouvette_B', 'eprouvette_cle'), ('eprouvette_A', 'eprouvette_C')]:
    v = (asm[a_] ^ asm[b_]).volume()
    assert v < 1e-3, (a_, b_, v)


def tm_of(m):
    me = m.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)


out = []
prints = dict(eprouvette_A=A, eprouvette_B=Bm, eprouvette_C=Cp, eprouvette_cle=key)   # C : logements contre le plateau, comme les pieces du kit
for n, m in prints.items():
    lo = np.array(m.bounding_box()[:3]); t = tm_of(m.translate(list(-lo)))
    assert t.is_watertight and t.body_count == 1, n
    out.append(dict(name=n, color='blanc', qty=1, V=np.asarray(t.vertices), F=np.asarray(t.faces), watertight=True, bodies=1,
                    vol_print=float(t.volume), asm=[(np.asarray(tm_of(asm[n]).vertices, np.float32), np.asarray(tm_of(asm[n]).faces, np.int64))]))
    print(n, np.round(t.extents, 1), 'mm')
pickle.dump(out, open(ROOT + '/v25/eprouvette.pkl', 'wb'))
