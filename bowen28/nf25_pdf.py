# -*- coding: utf-8 -*-
"""Mise en page de la notice facon Lego, aux couleurs du site (A4 paysage, une etape par page)."""
import os as _os
ROOT = _os.path.dirname(_os.path.abspath(__file__))          # dossier bowen28 du depot
import sys, os, io, json, math
sys.path.insert(0, ROOT)
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color
from nf25_steps import STEPS
import guide as Gd
sys.path.insert(0, ROOT + '/v25')
from noms25 import nice                                        # noms affiches des pieces (build_v22.py n'est plus dans le depot)
for n in ('DMSans-400', 'DMSans-700', 'DMMono-500'):
    pdfmetrics.registerFont(TTFont(n, f'{ROOT}/fonts/{n}.ttf'))
pdfmetrics.registerFont(TTFont('Brico-800', ROOT + '/fonts/Exo2-800-italic.ttf'))
pdfmetrics.registerFont(TTFont('Brico-700', ROOT + '/fonts/Exo2-800-italic.ttf'))
IMG = ROOT + '/nf25/img/'
counts = json.load(open(IMG + 'counts.json'))
W, H = 842, 595; M = 28
INK, BG, WHITE, MUTED, LINE = HexColor('#121418'), HexColor('#F2F4FA'), HexColor('#FFFFFF'), HexColor('#5E5A7D'), HexColor('#DADDEA')
FLUO, CORAL, BLUE, SUN = HexColor('#95FA05'), HexColor('#FF5A4E'), HexColor('#3D4CFF'), HexColor('#FFC93C')
CYCLE = [(BLUE, WHITE), (CORAL, INK), (SUN, INK), (FLUO, INK)]
def img_reader(im, q=88):
    b = io.BytesIO(); im.convert('RGB').save(b, 'JPEG', quality=q); b.seek(0); return ImageReader(b)
def contain(c, im, x, y, w, h):
    iw, ih = im.size; s = min(w / iw, h / ih); dw, dh = iw * s, ih * s
    c.drawImage(img_reader(im), x + (w - dw) / 2, y + (h - dh) / 2, dw, dh)
def rr(c, x, y, w, h, r, fill, stroke=None, sw=1):
    c.setFillColor(fill)
    if stroke: c.setStrokeColor(stroke); c.setLineWidth(sw)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1 if stroke else 0)
def text(c, s, x, y, font, size, col=INK, align='l'):
    c.setFont(font, size); c.setFillColor(col)
    (c.drawString if align == 'l' else c.drawRightString if align == 'r' else c.drawCentredString)(x, y, s)
def para(c, s, x, y, w, font='DMSans-400', size=10, lead=13.2, col=INK):
    for line in simpleSplit(s, font, size, w):
        text(c, line, x, y, font, size, col); y -= lead
    return y
def para_h(s, w, font='DMSans-400', size=10, lead=13.2): return len(simpleSplit(s, font, size, w)) * lead
def pill(c, s, x, y, fill, col=INK, font='DMMono-500', size=8.5, pad=8, right=False, rot=0):
    tw = pdfmetrics.stringWidth(s, font, size); w = tw + 2 * pad; h = size + 9
    if right: x -= w
    c.saveState(); c.translate(x + w / 2, y + h / 2); c.rotate(rot)
    rr(c, -w / 2, -h / 2, w, h, h / 2, fill); text(c, s, 0, -size * 0.36, font, size, col, 'c'); c.restoreState()
    return w
def badge(c, n, x, y, r, fill, col, size=None):
    c.setFillColor(fill); c.circle(x, y, r, fill=1, stroke=0)
    size = size or r * 1.15; text(c, str(n), x, y - size * 0.35, 'Brico-800', size, col, 'c')
import re as _re
_SVG = open(ROOT + '/v24/nxlogo.svg').read()
_PATHS = [[[tuple(map(float, p.split(','))) for p in poly.strip().split()] for poly in _re.findall(r'M([^Z]+)Z', d)] for d in _re.findall(r' d="([^"]+)"', _SVG)]
def brand(c, x, y, col=INK, dot=None, h=18):
    """Logo Nexform 3D Marine (trace du site) : NEXFORM dans col, 3D MARINE dans dot (par defaut col)."""
    from reportlab.pdfgen.canvas import FILL_EVEN_ODD
    s = h / 358.0
    for polys, cc in zip(_PATHS, (col, dot or col)):
        p = c.beginPath()
        for poly in polys:
            p.moveTo(x + poly[0][0] * s, y + (358 - poly[0][1]) * s)
            for (px, py) in poly[1:]: p.lineTo(x + px * s, y + (358 - py) * s)
            p.close()
        c.setFillColor(cc); c.drawPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)
def footer(c, si):
    brand(c, M, 16, INK, INK, h=20)
    n = len(STEPS); x0 = W / 2 - (n - 1) * 9
    for i in range(n):
        if i == si: c.setFillColor(CYCLE[si % 4][0]); c.circle(x0 + i * 18, 25, 6, fill=1, stroke=0)
        else: c.setFillColor(INK if i < si else LINE); c.circle(x0 + i * 18, 25, 3, fill=1, stroke=0)
    text(c, "BOWEN 28 · 1:19 · V25 SANS COLLE", W - M, 21, 'DMMono-500', 7.5, MUTED, 'r')
def parts_box(c, names, x, ytop, w):
    cols = 4 if len(names) <= 12 else 5
    cell = (w - 16) / cols; rows = math.ceil(len(names) / cols); rh = cell + 11
    h = 26 + rows * rh + 6
    rr(c, x, ytop - h, w, h, 14, WHITE, LINE)
    text(c, "PIÈCES DE L'ÉTAPE", x + 12, ytop - 17, 'DMMono-500', 7.5, MUTED)
    for i, n in enumerate(names):
        cx = x + 8 + (i % cols) * cell; cy = ytop - 26 - (i // cols) * rh - cell
        contain(c, Image.open(IMG + f't_{n}.png'), cx + 2, cy + 2, cell - 4, cell - 4)
        q = counts.get(n, 1)
        text(c, f"×{q}", cx + cell / 2, cy - 7, 'Brico-700', 9, INK if q > 1 else MUTED, 'c')
    return ytop - h
def tip_box(c, s, x, y, w):
    h = para_h(s, w - 24, 'DMSans-400', 9.5, 12.5) + 30
    rr(c, x, y, w, h, 14, SUN); text(c, "ASTUCE", x + 12, y + h - 17, 'DMMono-500', 7.5, INK)
    para(c, s, x + 12, y + h - 31, w - 24, 'DMSans-400', 9.5, 12.5); return h
def header(c, si, st):
    fill, col = CYCLE[si % 4]
    c.setFillColor(BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    badge(c, si + 1, M + 30, H - M - 30, 30, fill, col, 34)
    text(c, f"ÉTAPE {si + 1} SUR {len(STEPS)}", M + 74, H - M - 14, 'DMMono-500', 8, MUTED)
    text(c, st['title'], M + 74, H - M - 46, 'Brico-800', 30, INK)
    x = W - M
    if st.get('glue'): x -= pill(c, "COLLE : " + st['glue'].upper(), x, H - M - 24, CORAL, INK, right=True) + 6
    else: x -= pill(c, "SANS COLLE", x, H - M - 24, FLUO, INK, right=True) + 6
    if st.get('order'): pill(c, "SUIS LES NUMÉROS", x, H - M - 24, INK, FLUO, right=True)
def step_page(c, si, st):
    header(c, si, st); fill, col = CYCLE[si % 4]
    top = H - M - 76; bot = 50; lx, lw = M, 540; rx = lx + lw + 14; rw = W - M - rx
    uniq = list(dict.fromkeys(st['parts']))
    y = parts_box(c, uniq, rx, top, rw) - 12
    if st.get('subs'):
        subs = st['subs']; cols = st.get('cols', 3); rows = math.ceil(len(subs) / cols); gap = 10
        cw = (lw - gap * (cols - 1)) / cols; ch = (top - bot - gap * (rows - 1)) / rows
        for j, sb in enumerate(subs):
            x0 = lx + (j % cols) * (cw + gap); y0 = top - (j // cols + 1) * ch - (j // cols) * gap
            rr(c, x0, y0, cw, ch, 14, WHITE, LINE)
            caph = para_h(sb['cap'], cw - 20, 'DMSans-400', 9.6, 12)
            contain(c, Gd.autocrop(Image.open(IMG + f's{si+1:02d}_{j+1}.png'), 6), x0 + 8, y0 + caph + 14, cw - 16, ch - caph - 22)
            para(c, sb['cap'], x0 + 10, y0 + caph + 0, cw - 20, 'DMSans-400', 9.6, 12)
            badge(c, j + 1, x0 + 17, y0 + ch - 17, 11, fill, col, 13)
    else:
        rr(c, lx, bot, lw, top - bot, 18, WHITE, LINE)
        contain(c, Gd.autocrop(Image.open(IMG + f's{si+1:02d}.png'), 10), lx + 12, bot + 12, lw - 24, top - bot - 24)
        for j, t in enumerate(st['todo']):
            hh = para_h(t, rw - 26); badge(c, j + 1, rx + 9, y - 8, 8.5, INK, FLUO, 10)
            para(c, t, rx + 26, y - 11.5, rw - 26); y -= max(hh, 18) + 6
    if st.get('tip'):
        th = para_h(st['tip'], rw - 24, 'DMSans-400', 9.5, 12.5) + 30
        assert y - th > bot - 2, (si + 1, "colonne trop pleine", y - th)
        tip_box(c, st['tip'], rx, bot, rw)
    else: assert y > bot, (si + 1, y)
    footer(c, si); c.showPage()
def cover(c):
    c.setFillColor(INK); c.rect(0, 0, W, H, fill=1, stroke=0)
    im = Image.open(IMG + 'cover.png'); c.drawImage(img_reader(im, 92), 150, 20, 700, 420)
    brand(c, M, H - M - 26, WHITE, FLUO, h=34)
    text(c, "BOWEN 28", M, H - 150, 'Brico-800', 96, WHITE)
    pill(c, "NOTICE DE MONTAGE", M + 4, H - 196, FLUO, INK, 'DMMono-500', 13, 14, rot=-2)
    for (s1, s2, x, y, r, f, rot) in ((str(sum(counts.values())), "pièces", 96, 190, 46, FLUO, -10), (str(len(STEPS)), "étapes", 196, 120, 38, SUN, 8), ("1:19", "50 cm", 92, 82, 34, CORAL, -6)):
        c.saveState(); c.translate(x, y); c.rotate(rot); c.setFillColor(f); c.circle(0, 0, r, fill=1, stroke=0)
        text(c, s1, 0, -2, 'Brico-800', r * 0.62, INK, 'c'); text(c, s2.upper(), 0, -r * 0.42, 'DMMono-500', r * 0.2, INK, 'c'); c.restoreState()
    c.showPage()
def card(c, x, y, w, h, title, fill=WHITE):
    rr(c, x, y, w, h, 16, fill, None if fill != WHITE else LINE); text(c, title, x + 16, y + h - 28, 'Brico-800', 17, INK)
def before(c):
    c.setFillColor(BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "Avant de commencer", M, H - M - 34, 'Brico-800', 34, INK)
    text(c, "3 MINUTES POUR TOUT PRÉPARER", M, H - M - 52, 'DMMono-500', 8, MUTED)
    gw = (W - 2 * M - 14) / 2; top = H - M - 68; hh = (top - 50 - 14) / 2
    x1, x2 = M, M + gw + 14; y1, y2 = top - hh, 50
    card(c, x1, y1, gw, hh, "Tes outils", FLUO)
    yy = y1 + hh - 50
    for t in ("Tes doigts : rien à coller", "Pince à épiler : pour les petites pièces", "L'éprouvette P00 : pour sentir le bon effort", "Papier de verre fin : si une pièce force", "Ficelle fine et aiguille : pour les pare-battages"):
        c.setFillColor(INK); c.circle(x1 + 22, yy + 3.5, 3, fill=1, stroke=0); text(c, t, x1 + 32, yy, 'DMSans-400', 12.5); yy -= 25
    card(c, x2, y1, gw, hh, "Les emboîtements, grandeur nature")
    mm = 72 / 25.4; yy = y1 + hh - 60; xs = x2 + 34
    c.setFillColor(INK); c.circle(xs, yy + 3, 1.0 * mm, fill=1, stroke=0)
    text(c, "Tenon rond de 2 mm (ou 1,4 mm) : la plupart des pièces", xs + 22, yy, 'DMSans-400', 11.5); yy -= 30
    a = 1.414 * mm; p = c.beginPath(); p.moveTo(xs, yy + 3 + a); p.lineTo(xs + a, yy + 3); p.lineTo(xs, yy + 3 - a); p.lineTo(xs - a, yy + 3); p.close(); c.drawPath(p, stroke=0, fill=1)
    text(c, "Tenon losange : coques, moteurs, manette, volant, dos du dossier", xs + 22, yy, 'DMSans-400', 11.5); yy -= 34
    for dx in (-4.5, 4.5): c.circle(xs + 8 + dx * mm, yy + 3, 2.4 * mm, fill=1, stroke=0)
    c.rect(xs + 8 - 4.5 * mm, yy + 3 - 1.1 * mm, 9 * mm, 2.2 * mm, fill=1, stroke=0)
    text(c, "Clé de jonction : elle serre les 2 coques", xs + 22 + 8 * mm, yy, 'DMSans-400', 11.5); yy -= 24
    para(c, "Page imprimée à 100 % : les formes sont à la taille réelle. Pas de colle, pas de goupille.", x2 + 18, yy - 2, gw - 36, 'DMSans-400', 10.5, 14, MUTED)
    card(c, x1, y2, gw, hh, "Tes 5 couleurs")
    yy = y2 + hh - 50
    nc = json.load(open(IMG + 'couleurs.json'))
    for (hexc, nm, det) in (('#F2EFE6', "Blanc cassé", f"coque, capots, clés · {nc['blanc']} pièces"), ('#B8BEC4', "Gris alu", f"moteurs, cadres, échelle · {nc['alu']} pièces"), ('#26272B', "Noir", f"toit, filets, pare-battages · {nc['noir']} pièces"), ('#C29A6A', "Teck", f"pont, volant · {nc['teck']} pièces"), ('#8C7A6B', "Taupe", f"coussins, fauteuils · {nc['taupe']} pièces")):
        c.setFillColor(HexColor(hexc)); c.setStrokeColor(LINE); c.setLineWidth(0.8); c.circle(x1 + 25, yy + 3.5, 7, fill=1, stroke=1)
        text(c, nm, x1 + 40, yy, 'DMSans-700', 12); text(c, det, x1 + 124, yy, 'DMSans-400', 11, MUTED); yy -= 24
    card(c, x2, y2, gw, hh, "La règle du jeu", WHITE)
    yy = y2 + hh - 52
    for (f, t) in ((FLUO, "Tenon, clé, nervure ou encoche : tout s'emboîte. Aucune colle."), (CORAL, "Ça force ? Vérifie le sens avant d'appuyer plus fort."), (SUN, "Appuie bien droit, dans l'axe du tenon, jusqu'à ce que la pièce affleure."), (BLUE, "Pièces en couleur : à poser. Pièces pâles : déjà posées. La flèche rouge montre le sens.")):
        c.setFillColor(f); c.circle(x2 + 24, yy + 3.5, 6, fill=1, stroke=0)
        yy = para(c, t, x2 + 38, yy, gw - 56, 'DMSans-400', 12, 15.5) - 9
    brand(c, M, 16, INK, INK, h=20); text(c, "BOWEN 28 · 1:19 · V25 SANS COLLE", W - M, 21, 'DMMono-500', 7.5, MUTED, 'r'); c.showPage()
def fin(c):
    c.setFillColor(FLUO); c.rect(0, 0, W, H, fill=1, stroke=0)
    im = Image.open(IMG + 'fin.png'); c.drawImage(img_reader(im, 92), 110, 10, 720, 432)
    brand(c, M, H - M - 26, INK, INK, h=34)
    text(c, "À l'eau !", M, H - 140, 'Brico-800', 88, INK)
    text(c, "Ta maquette est terminée. Pose-la sur ses berceaux, recule d'un pas, admire.", M + 4, H - 172, 'DMSans-700', 13, INK)
    c.showPage()
out = ROOT + '/nf25/notice_de_montage_bowen28_v25.pdf'
c = canvas.Canvas(out, pagesize=(W, H)); c.setTitle("Bowen 28 – notice de montage (v25, sans colle)"); c.setAuthor("Nexform 3D Marine")
cover(c); before(c)
for si, st in enumerate(STEPS): step_page(c, si, st)
fin(c); c.save(); print("ok", os.path.getsize(out))
