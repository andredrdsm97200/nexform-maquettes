"""Controle de maintien (LIGNE_DE_CONDUITE.md, regle 2 : une petite piece ne tombe pas toute seule).

Les pieces qui ne tiennent pas par leur poids (accrochees a la console, debout ou penchees sur le tableau de bord)
ont des cotes d'ecrasement sur leur emboitement (commun/emboitements.py, ajoutees dans s1_pieces.py). Pour chacune :
  - la piece imprimee (avec ses cotes), mise a sa place, touche bien la piece d'en face : serrage de 0,05 a 5 mm3 ;
  - la piece nominale (celle de la maquette assemblee) n'a pas plus de 0,16 mm de jeu de cote (vers le bas, son
    poids la tient : la barre de console, imprimee sur un meplat, peut descendre un peu dans ses trous).
Toute piece accrochee qui n'a pas de cotes est signalee. Le programme s'arrete si une piece est mal tenue.
"""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, pickle
sys.path.insert(0, ROOT); sys.path.insert(0, _os.path.join(_os.path.dirname(ROOT), 'commun'))
import numpy as np
from manifold3d import Manifold, Mesh
import model as M
import montage as MT

def man(V, F): return Manifold(Mesh(np.asarray(V, np.float32), np.asarray(F, np.uint32)))
def vis(d): return (d[0], d[2], -d[1])

A = {k: man(*vf) for k, vf in pickle.load(open(ROOT + '/v25/v25b.pkl', 'rb')).items()}
PC = pickle.load(open(ROOT + '/v25/pieces.pkl', 'rb'))
(x0, z0), (x1, z1) = M.DASH
# pieces qui ne tiennent pas par leur poids, et le sens de leur pose
AXES = {
    'ecran_mfd': vis(M.mfd_foot_frame()[3]),                 # debout sur un tenon, ecran penche
    'ecran_tribord': vis((-(z1 - z0), 0.0, x1 - x0)),         # dans son empreinte, tableau de bord incline
    'interrupteurs': (1, 0, 0),                               # face arriere verticale de la console
    'manette_gaz': (1, 0, 0),
    'barre_console': (1, 0, 0),
    'pompe_direction': vis(M.WHEEL_N),                        # accrochee au tenon de la console, volant en porte-a-faux
    'embase_moteur': (0, 1, 0),                               # v25.3 : pend sous le bloc gris, sur 2 tenons verticaux
    'helice': (1, 0, 0),                                      # v25.3 : sur le tenon losange horizontal de la torpille
}
# (le moyeu du volant, lui, tient par son poids : l'axe du volant monte de 30 degres vers le pilote)
mal = []
for e in PC:
    if e['name'] not in AXES:
        continue
    if not e.get('serre'):
        mal.append((e['name'], 'pas de cotes d\'ecrasement')); continue
    for i, (V, F) in enumerate(e['serre']):
        k = f"{e['color']}__{e['name']}__{i}"
        autres = {n: m for n, m in A.items() if n != k}
        ok, serrage, trop = MT.controle_maintien(A[k], man(V, F), autres, AXES[e['name']], bas=(0, -1, 0))
        print(f"  {'ok    ' if ok else 'MAL   '} {e['name']:16s} serrage des cotes {serrage:5.2f} mm3" + (f" ; jeu > 0,16 mm vers {trop}" if trop else ''))
        if not ok:
            mal.append((k, round(serrage, 2), trop))
for n in AXES:
    if not any(e['name'] == n for e in PC):
        mal.append((n, 'piece introuvable'))
print('pieces mal tenues :', len(mal))
for m in mal:
    print('  MAL', m)
if mal:
    sys.exit(1)
