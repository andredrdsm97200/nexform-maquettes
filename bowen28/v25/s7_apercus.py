"""Apercus des plateaux : vue de dessus a l'echelle sur le plateau de 256 mm, pieces numerotees, legende."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, os, pickle, json, collections
sys.path.insert(0, ROOT)
import numpy as np, trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib import font_manager as fm
import pieces as P

HERE = ROOT + '/v25'
KIT = os.path.join(HERE, 'kit', 'Bowen28_kit_impression_v25.3')
for f in ('DMSans-400', 'DMSans-700', 'DMMono-500', 'Exo2-800-italic'):
    fm.fontManager.addfont(f'{ROOT}/fonts/{f}.ttf')
FONT = 'DM Sans'
sys.path.insert(0, HERE)
from noms25 import nice
from kit_inputs import load_all
A, _ = load_all()
TM = {e['name']: trimesh.Trimesh(e['V'], e['F'], process=False) for e in A}
plates = pickle.load(open(os.path.join(HERE, 'kit_plates.pkl'), 'rb'))['plates']
BED = 256.0
FIL = {'blanc': 'PLA Matte Ivory White', 'alu': 'PLA Basic Silver', 'noir': 'PLA Matte Charcoal', 'teck': 'PLA Matte Caramel', 'taupe': 'PLA Matte Dark Brown'}


def outline(tm, T):
    """Triangles projetes (x, y) de la piece posee ; on garde les faces tournees vers le haut (vue de dessus)."""
    v = trimesh.transform_points(tm.vertices, T); tri = v[tm.faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    return tri[n[:, 2] > 0][:, :, :2], tri


def draw_plate(p, ax, lg, compact=False):
    dark = p['color'] != 'noir' or p.get('option')
    bed = '#2B2F35' if dark else '#D9DDE2'
    ax.add_patch(plt.Rectangle((0, 0), BED, BED, fc=bed, ec='#15171A', lw=1.2, zorder=0))
    for t in range(32, 256, 32):
        ax.plot([t, t], [0, BED], color='#ffffff' if dark else '#000000', alpha=0.06, lw=0.6, zorder=0)
        ax.plot([0, BED], [t, t], color='#ffffff' if dark else '#000000', alpha=0.06, lw=0.6, zorder=0)
    rgb = np.array(P.COLORS[p['color']][1])
    if p.get('option'): rgb = np.array([0.09, 0.09, 0.1])
    names = []
    for i in sorted(p['inst'], key=lambda i: (-round((i['y'] + i['h'] / 2) / 26.0), i['x'] + i['w'] / 2)):
        if i['name'] not in names: names.append(i['name'])
    num = {n: k + 1 for k, n in enumerate(names)}
    qty = collections.Counter(i['name'] for i in p['inst'])
    for i in p['inst']:
        tris, all_t = outline(TM[i['name']], np.array(i['T']))
        z = all_t[:, :, 2].mean(1)
        # ombrage leger selon l'inclinaison des faces vues de dessus
        nn = np.cross(all_t[:, 1] - all_t[:, 0], all_t[:, 2] - all_t[:, 0]); nn /= np.linalg.norm(nn, axis=1)[:, None] + 1e-12
        up = nn[:, 2] > 0
        shade = np.clip(0.55 + 0.45 * (nn[up] @ np.array([-0.35, 0.45, 0.82])), 0.35, 1.05)
        cols = np.clip(rgb[None, :] * shade[:, None], 0, 1)
        ax.add_collection(PolyCollection(tris, facecolors=cols, edgecolors=cols, linewidths=0.15, zorder=2 + 0.001 * z[up].mean() if up.any() else 2))
        cx, cy = i['x'] + i['w'] / 2, i['y'] + i['h'] / 2
        ax.text(cx, cy, str(num[i['name']]), fontsize=5.4 if compact else 6.5, ha='center', va='center', color='#111', zorder=9, family=FONT, weight='bold',
                bbox=dict(boxstyle='circle,pad=0.18', fc='#C8FF2E' if False else '#95FA05', ec='#111', lw=0.4))
    ax.set_xlim(-4, BED + 4); ax.set_ylim(-4, BED + 4); ax.set_aspect('equal'); ax.axis('off')
    ax.text(0, BED + 7, f"P{p['num']:02d}", fontsize=13 if not compact else 11, family='Exo 2', style='italic', weight='heavy', va='bottom')
    ax.text(31 if not compact else 27, BED + 8, p['title'], fontsize=8.6 if not compact else 7.2, family=FONT, weight='bold', va='bottom')
    # legende
    fil = 'Bambu TPU 90A Black (souple)' if p.get('option') else f"Bambu {FIL[p['color']]}"
    sets = [f"{P.COLORS[p['color']][0].split(' (')[0]} · {fil}" if not p.get('option') else f"Noir souple · {fil}",
            f"Couches {str(p['layer']).replace('.', ',')} mm · " + ('supports arborescents « sur le plateau uniquement »' if p['sup'] else 'sans support')
            + (' · bordure 5 mm' if p['brim'] else ''),
            f"{len(p['inst'])} pièce{'s' if len(p['inst']) > 1 else ''} · environ {int(round(p['grams'] / 5.0) * 5) if p['grams'] >= 10 else max(1, round(p['grams']))} g hors supports · {p['file']}"]
    y = 1.0
    for s in sets:
        lg.text(0, y, s, fontsize=7.4, family=FONT, va='top', transform=lg.transAxes, color='#222'); y -= 0.055
    y -= 0.03
    lines = [(str(num[n]), nice(n) + (f"  ×{qty[n]}" if qty[n] > 1 else '')) for n in names]
    ncol = 1 if len(lines) <= 15 else 2
    per = (len(lines) + ncol - 1) // ncol
    fs = 7.6 if ncol == 1 else 6.7
    for j in range(ncol):
        yy = y
        for a, b in lines[j * per:(j + 1) * per]:
            lg.text(j * 0.52 + 0.035, yy, a, fontsize=fs, family=FONT, weight='bold', ha='right', va='top', transform=lg.transAxes, color='#3a6600')
            lg.text(j * 0.52 + 0.055, yy, b, fontsize=fs, family=FONT, va='top', transform=lg.transAxes, color='#111')
            yy -= 0.052 if ncol == 1 else 0.048
    lg.axis('off')


outdir = os.path.join(KIT, 'plateaux_apercu'); os.makedirs(outdir, exist_ok=True)
for p in plates:
    fig = plt.figure(figsize=(10.5, 5.6))
    ax = fig.add_axes([0.01, 0.02, 0.5, 0.92]); lg = fig.add_axes([0.53, 0.05, 0.46, 0.83])
    draw_plate(p, ax, lg)
    fig.savefig(os.path.join(outdir, p['file'].replace('.3mf', '.png')), dpi=150, facecolor='white')
    plt.close(fig)
    print('apercu', p['file'])
# planche de tous les plateaux
n = len(plates); cols = 2; rows = (n + cols - 1) // cols
fig = plt.figure(figsize=(cols * 8.2, rows * 4.3 + 0.6))
for k, p in enumerate(plates):
    r, c = divmod(k, cols)
    h = 1.0 / (rows + 0.14); y0 = 1 - (r + 1) * h - 0.01
    ax = fig.add_axes([c * 0.5 + 0.005, y0, 0.235, h * 0.9]); lg = fig.add_axes([c * 0.5 + 0.245, y0 + 0.01, 0.25, h * 0.78])
    draw_plate(p, ax, lg, compact=True)
fig.savefig(os.path.join(KIT, 'plateaux_apercu.png'), dpi=110, facecolor='white')
print('planche ok')
