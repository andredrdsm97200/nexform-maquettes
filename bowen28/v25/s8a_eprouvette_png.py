"""Image de l'eprouvette pour la fiche : montee (a gauche) et eclatee (a droite)."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, pickle
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/v25')
import numpy as np, trimesh
from PIL import Image
from raster import render
E = pickle.load(open(ROOT + '/v25/eprouvette.pkl', 'rb'))
KIT = ROOT + '/v25/kit/Bowen28_kit_impression_v25.2'
col = {'eprouvette_A': (0.93, 0.92, 0.88), 'eprouvette_B': (0.86, 0.85, 0.80), 'eprouvette_C': (0.95, 0.94, 0.90), 'eprouvette_cle': (0.80, 0.79, 0.74)}
EX = {'eprouvette_A': (0, 0, 0), 'eprouvette_B': (9, 0, 0), 'eprouvette_C': (0, 0, 9), 'eprouvette_cle': (4.5, 0, 14)}
ims = []
for ex in (0.0, 1.0):
    parts = []
    for e in E:
        V, F = e['asm'][0]; t = trimesh.Trimesh(np.asarray(V, float) + np.array(EX[e['name']]) * ex, F, process=False)
        parts.append((t, col[e['name']]))
    allv = np.vstack([p[0].vertices for p in parts]); c = (allv.min(0) + allv.max(0)) / 2
    eye = c + np.array([-34, -52, 40]) * (1.0 + 0.25 * ex)
    ims.append(render(parts, eye=tuple(eye), target=tuple(c), fov=30, W=900, H=560, ss=2, bg=(243, 245, 247), light=(0.35, -0.6, 0.75)))
out = Image.new('RGB', (1800, 560), (243, 245, 247)); out.paste(ims[0], (0, 0)); out.paste(ims[1], (900, 0))
out.save(f'{KIT}/eprouvette.png'); print('eprouvette.png')
