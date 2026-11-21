"""Fiche d'impression (A4) a remettre a l'imprimeur : plateaux, filaments, reglages, puis les apercus numerotes."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import os, json, collections, datetime
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
import re

HERE = ROOT + '/v25'
KIT = os.path.join(HERE, 'kit', 'Bowen28_kit_impression_v25.2')
meta = json.load(open(os.path.join(HERE, 'kit_meta.json')))
plates = meta['plates']; pieces = meta['pieces']
for n, f in (('Exo', 'Exo2-800-italic'), ('Exo9', 'Exo2-900-italic'), ('Sans', 'DMSans-400'), ('SansB', 'DMSans-700'), ('Mono', 'DMMono-500')):
    pdfmetrics.registerFont(TTFont(n, f'{ROOT}/fonts/{f}.ttf'))
W, H = 595.28, 841.89; M = 34
INK, BG, LINE, MUTED, FLUO, WHITE = HexColor('#121418'), HexColor('#F3F5F7'), HexColor('#D9DDE2'), HexColor('#5F6670'), HexColor('#95FA05'), HexColor('#FFFFFF')
SW = {'blanc': '#F2EFE6', 'alu': '#B8BEC4', 'noir': '#26272B', 'teck': '#C29A6A', 'taupe': '#8C7A6B', 'tpu': '#0E0E10'}
FIL = {'blanc': 'PLA Matte Ivory White', 'alu': 'PLA Basic Silver', 'noir': 'PLA Matte Charcoal', 'teck': 'PLA Matte Caramel', 'taupe': 'PLA Matte Dark Brown'}
CNAME = {'blanc': 'Blanc cassé', 'alu': 'Gris alu', 'noir': 'Noir', 'teck': 'Teck', 'taupe': 'Taupe'}
import sys; sys.path.insert(0, HERE)
from noms25 import nice

_SVG = open(ROOT + '/v24/nxlogo.svg').read()
_PATHS = [[[tuple(map(float, p.split(','))) for p in poly.strip().split()] for poly in re.findall(r'M([^Z]+)Z', d)] for d in re.findall(r' d="([^"]+)"', _SVG)]


def logo(c, x, y, h, col, col2=None):
    """Logo Nexform 3D Marine du site : NEXFORM dans col, 3D MARINE dans col2 (vert fluo sur fond sombre)."""
    from reportlab.pdfgen.canvas import FILL_EVEN_ODD
    s = h / 358.0
    for polys, cc in zip(_PATHS, (col, col2 or col)):
        p = c.beginPath()
        for poly in polys:
            p.moveTo(x + poly[0][0] * s, y + (358 - poly[0][1]) * s)
            for (px, py) in poly[1:]: p.lineTo(x + px * s, y + (358 - py) * s)
            p.close()
        c.setFillColor(cc); c.drawPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)


def t(c, s, x, y, font='Sans', size=9, col=INK, align='l'):
    c.setFont(font, size); c.setFillColor(col)
    (c.drawString if align == 'l' else c.drawRightString if align == 'r' else c.drawCentredString)(x, y, s)


def para(c, s, x, y, w, font='Sans', size=9, lead=12, col=INK):
    for line in simpleSplit(s, font, size, w):
        t(c, line, x, y, font, size, col); y -= lead
    return y


def nb(s):
    return re.sub(r" ([:;?!»])", " \\1", s).replace("« ", "« ")


def grams_txt(g):
    return f"{int(round(g / 5.0) * 5)} g" if g >= 10 else f"{max(1, round(g))} g"


def footer(c, page):
    logo(c, M, 15, 18, INK)
    t(c, "BOWEN 28 · 1:19 · KIT D'IMPRESSION V25.2 · SANS COLLE", W / 2, 21, 'Mono', 7, MUTED, 'c')
    t(c, f"{page}", W - M, 21, 'Mono', 7, MUTED, 'r')


out = os.path.join(KIT, 'FICHE_IMPRESSION.pdf')
c = canvas.Canvas(out, pagesize=(W, H)); c.setTitle("Bowen 28 – fiche d'impression (kit v25.2 sans colle)"); c.setAuthor("Nexform 3D Marine")
# ---------------- page 1
c.setFillColor(INK); c.rect(0, H - 112, W, 112, fill=1, stroke=0)
logo(c, M, H - 52, 30, WHITE, FLUO)
t(c, "FICHE D'IMPRESSION", M, H - 78, 'Exo9', 24, WHITE)
t(c, "Bowen 28 center console · maquette au 1:19 · kit v25.2, montage sans colle · " + datetime.date(2026, 11, 21).strftime('%d/%m/%Y'), M, H - 96, 'Sans', 9.5, HexColor('#C9CED6'))
main = [p for p in plates if not p['eprouvette']]; epr = [p for p in plates if p['eprouvette']]
npieces = sum(len(p['inst']) for p in main)
g_pla = sum(p['grams'] for p in main)
chips = [(f"{len(main)}", "plateaux PLA", "+ P00 : l'éprouvette"), (f"{npieces}", "pièces", f"+ {len(epr[0]['inst'])} pour l'éprouvette"),
         ("5", "couleurs", "une par plateau"), (f"{int(round(g_pla / 10) * 10)} g", "de PLA", "environ, hors supports")]
cw = (W - 2 * M - 3 * 10) / 4; y = H - 112 - 14 - 50
for i, (a, b, d) in enumerate(chips):
    x = M + i * (cw + 10)
    c.setFillColor(BG); c.roundRect(x, y, cw, 50, 10, fill=1, stroke=0)
    t(c, a, x + 12, y + 26, 'Exo', 19, INK); t(c, b, x + 12 + pdfmetrics.stringWidth(a, 'Exo', 19) + 6, y + 27, 'SansB', 9.2, INK)
    t(c, d, x + 12, y + 11, 'Sans', 7.8, MUTED)
# tableau des plateaux
y -= 20
t(c, "LES PLATEAUX", M, y, 'Mono', 8, MUTED); y -= 8
cols = [M, M + 34, M + 210, M + 352, W - M]
c.setStrokeColor(LINE); c.setLineWidth(0.8)
hy = y - 15
for x, lab in ((cols[0] + 2, "N°"), (cols[1], "Contenu et fichier 3MF"), (cols[2], "Filament (Bambu Lab)"), (cols[3], "Réglages")):
    t(c, lab, x, hy + 3, 'SansB', 8, MUTED)
t(c, "Poids env.", cols[4], hy + 3, 'SansB', 8, MUTED, 'r')
c.line(M, hy - 4, W - M, hy - 4); y = hy - 4
for p in plates:
    col = p['color']
    cnt = collections.Counter(i['name'] for i in p['inst'])
    content = nb(p['title'])
    fil = FIL[p['color']]
    setl = []
    setl.append(f"couches {str(p['layer']).replace('.', ',')} mm")
    setl.append('supports arborescents, « sur le plateau uniquement »' if p['sup'] else 'sans support')
    if p['brim']: setl.append('bordure 5 mm')
    if p['eprouvette']: setl.append('à imprimer et monter en premier (page 2)')
    sets = nb(' · '.join(setl))
    l1 = simpleSplit(content, 'SansB', 8.6, cols[2] - cols[1] - 8)
    l3 = simpleSplit(sets, 'Sans', 8, cols[4] - cols[3] - 44)
    rh = max(len(l1) * 10.5 + 11, len(l3) * 10 + 3, 25) + 6
    yt = y - 12
    c.setFillColor(FLUO if not p['eprouvette'] else INK); c.roundRect(cols[0], y - 22, 26, 17, 5, fill=1, stroke=0)
    t(c, f"P{p['num']:02d}", cols[0] + 13, y - 17, 'Exo', 9, INK if not p['eprouvette'] else FLUO, 'c')
    yy = yt
    for ln in l1: t(c, ln, cols[1], yy, 'SansB', 8.6); yy -= 10.5
    t(c, p['file'], cols[1], yy - 1, 'Mono', 6.6, MUTED)
    c.setFillColor(HexColor(SW[col])); c.setStrokeColor(HexColor('#9AA2AC')); c.setLineWidth(0.6); c.circle(cols[2] + 5, yt + 3, 4.5, fill=1, stroke=1)
    t(c, CNAME[p['color']], cols[2] + 14, yt, 'SansB', 8.6)
    t(c, fil, cols[2] + 14, yt - 10.5, 'Sans', 8, MUTED)
    yy = yt
    for ln in l3: t(c, ln, cols[3], yy, 'Sans', 8); yy -= 10
    t(c, grams_txt(p['grams']), cols[4], yt, 'SansB', 8.6, INK, 'r')
    t(c, f"{len(p['inst'])} pièce{'s' if len(p['inst']) > 1 else ''}", cols[4], yt - 10.5, 'Sans', 8, MUTED, 'r')
    y -= rh; c.setStrokeColor(LINE); c.line(M, y, W - M, y)
# reglages communs
y -= 15
t(c, "RÉGLAGES COMMUNS", M, y, 'Mono', 8, MUTED); y -= 8
box = [
    "Bambu Lab A1 (plateau 256 × 256 mm) : les 3MF sont disposés pour ce plateau ; ailleurs, importer les STL du dossier « stl » puis « Disposer ». Pièces en mm, à l'échelle 1:19, déjà orientées : ne pas les redimensionner ni les tourner.",
    "PLA ou PLA+ uniquement, buse 0,4 mm, 3 périmètres, remplissage gyroïde 15 %, plateau texturé PEI. Couches de 0,12 mm, sauf le plateau noir P06 en 0,08 mm.",
    "Montage sans colle : tenons, clés et logements ont 0,1 mm de jeu. Imprimer et monter d'abord l'éprouvette P00 (page 2), puis lancer les autres plateaux avec le même réglage.",
    "Supports seulement sur P01, P02 (coques) et P05 (embases moteur) : arborescents, « sur le plateau uniquement » ; bordure de 5 mm pour les 2 coques. Tous les autres plateaux, dont le toit P07 imprimé à l'envers : aucun support.",
    "Coques : retirer les supports avec soin (nervures blanches, pare-brise, 3 tenons losange sur la face de jonction de la coque arrière). Rendre les pièces en 10 sachets étiquetés P00 à P09.",
]
bx_h = sum(len(simpleSplit(nb(s), 'Sans', 8.6, W - 2 * M - 34)) * 11.2 + 5 for s in box) + 18
c.setFillColor(BG); c.roundRect(M, y - bx_h, W - 2 * M, bx_h, 12, fill=1, stroke=0)
yy = y - 18
for s in box:
    c.setFillColor(FLUO); c.circle(M + 16, yy + 3, 3.2, fill=1, stroke=0)
    yy = para(c, nb(s), M + 28, yy, W - 2 * M - 34, 'Sans', 8.6, 11.2) - 5
assert y - bx_h > 38, y - bx_h
footer(c, 1); c.showPage()
# ---------------- page 2 : l'eprouvette de reglage
c.setFillColor(INK); c.rect(0, H - 92, W, 92, fill=1, stroke=0)
t(c, "P00 · ÉPROUVETTE DE RÉGLAGE", M, H - 50, 'Exo9', 21, WHITE)
t(c, "À imprimer et monter avant tout le reste : 4 petites pièces, environ 15 minutes, filament blanc, réglages du kit.", M, H - 70, 'Sans', 9.2, HexColor('#C9CED6'))
im = Image.open(os.path.join(KIT, 'eprouvette.png')); iw, ih = im.size; w = W - 2 * M; h = w * ih / iw
y = H - 92 - 16 - h
c.setFillColor(BG); c.roundRect(M - 6, y - 6, w + 12, h + 12, 10, fill=1, stroke=0)
b = __import__('io').BytesIO(); im.convert('RGB').save(b, 'PNG'); b.seek(0); c.drawImage(ImageReader(b), M, y, w, h)
y -= 26
t(c, "MONTAGE (LES MÊMES EMBOÎTEMENTS QUE DANS LE KIT)", M, y, 'Mono', 8, MUTED); y -= 16
for k_, s_ in enumerate(["Pousser le bloc B contre le bloc A : le tenon losange de A entre dans le logement de B (comme les 2 moitiés de coque).",
                          "Enfoncer la clé par le dessus, dans le logement en forme d'os, jusqu'à ce qu'elle affleure (comme les 4 clés de jonction).",
                          "Poser la plaquette C sur les 2 tenons ronds de A : le gros (2 mm) et le petit (1,4 mm), comme toutes les petites pièces."], 1):
    c.setFillColor(FLUO); c.circle(M + 9, y + 3, 8, fill=1, stroke=0); t(c, str(k_), M + 9, y, 'Exo', 9, INK, 'c')
    y = para(c, nb(s_), M + 26, y + 0.5, W - 2 * M - 30, 'Sans', 9.2, 12) - 7
y -= 4
c.setFillColor(BG); c.roundRect(M, y - 34, W - 2 * M, 34, 10, fill=1, stroke=0)
para(c, nb("Bon réglage : chaque pièce entre à la main avec un léger effort, sans outil, et rien ne tombe quand on retourne l'éprouvette. Les 3 emboîtements bons : lancer le kit avec ce réglage."),
     M + 14, y - 14, W - 2 * M - 28, 'SansB', 9, 11.5)
y -= 34 + 22
t(c, "SINON, UN SEUL RÉGLAGE À CHANGER (BAMBU STUDIO › QUALITÉ › PRÉCISION), PUIS RÉIMPRIMER L'ÉPROUVETTE", M, y, 'Mono', 7.6, MUTED); y -= 8
rows = [("La plaquette C force ou ne descend pas", "Compensation X-Y des trous", "+0,05 mm"),
        ("La plaquette C tombe toute seule", "Compensation X-Y des trous", "−0,05 mm"),
        ("La clé ou le bloc B force", "Compensation X-Y du contour", "−0,03 mm"),
        ("La clé ou le bloc B a du jeu", "Compensation X-Y du contour", "+0,03 mm")]
c.setStrokeColor(LINE); c.setLineWidth(0.8)
for r_ in rows:
    y -= 19
    t(c, nb(r_[0]), M + 2, y + 5, 'Sans', 9); t(c, r_[1], M + 268, y + 5, 'Sans', 9, MUTED); t(c, r_[2], W - M - 2, y + 5, 'SansB', 9.2, INK, 'r')
    c.line(M, y - 2, W - M, y - 2)
y -= 22
y = para(c, nb("Garder ensuite ce même réglage pour les 10 plateaux, et rendre l'éprouvette montée avec le kit (sachet P00) : elle sert de pièce d'essai au client."),
         M, y, W - 2 * M, 'Sans', 9, 12)
assert y > 40, y
footer(c, 2); c.showPage()
# ---------------- pages des apercus : 2 plateaux par page, avec la liste des pieces
pg = 3
ims = [(p, Image.open(os.path.join(KIT, 'plateaux_apercu', p['file'].replace('.3mf', '.png')))) for p in plates]
for k in range(0, len(ims), 2):
    c.setFillColor(WHITE); c.rect(0, 0, W, H, fill=1, stroke=0)
    t(c, "APERÇU DES PLATEAUX · VUE DE DESSUS, À L'ÉCHELLE DU PLATEAU DE 256 MM", M, H - M - 6, 'Mono', 7.5, MUTED)
    for j, (p, im) in enumerate(ims[k:k + 2]):
        iw, ih = im.size; w = W - 2 * M; h = w * ih / iw
        y0 = H - M - 24 - (j + 1) * (h + 26) + 10
        c.setFillColor(BG); c.roundRect(M - 6, y0 - 8, w + 12, h + 16, 10, fill=1, stroke=0)
        b = __import__('io').BytesIO(); im.convert('RGB').save(b, 'PNG'); b.seek(0)
        c.drawImage(ImageReader(b), M, y0, w, h)
    footer(c, pg); pg += 1; c.showPage()
c.save()
print('fiche', out, os.path.getsize(out) // 1024, 'Ko', pg - 1, 'pages')
