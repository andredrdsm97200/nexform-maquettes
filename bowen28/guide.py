"""Notice de montage pas a pas, facon Lego : pour chaque etape, les pieces deja posees (attenuees), les
pieces nouvelles en couleur, decalees le long de leur sens de montage, avec une fleche vers leur place."""
import os, re
from collections import OrderedDict
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageChops
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from raster import render, look_at

BANDES = ["bandes_banquette_basse_assise", "bandes_banquette_basse_dossier", "bandes_banquette_haute_assise",
          "bandes_banquette_haute_dossier"]
COUSS_AR = ["coussin_banquette_basse_assise", "coussin_banquette_basse_dossier", "coussin_banquette_haute_assise",
            "coussin_banquette_haute_dossier"]
AVANT = ["coussin_avant_retour_babord", "coussin_avant_retour_tribord", "coussin_avant_dossier_babord",
         "coussin_avant_dossier_tribord", "coussin_avant_dossier_avant", "coussin_avant_assise_babord",
         "coussin_avant_assise_tribord", "coussin_avant_assise_avant"]
PADS_B = [f"bandes_plat_bord_{k}_{s}" for k in (1, 2, 3) for s in ("babord", "tribord")]
PADS_C = [f"coussin_plat_bord_{k}_{s}" for k in (1, 2, 3) for s in ("babord", "tribord")]

GW = [f"seadeck_plat_bord_{k}_{s}" for k in (1, 2, 3, 4) for s in ("babord", "tribord")]
FILETS = ["filet_noir_arriere", "filet_noir_avant", "filet_noir_tableau"]

STEPS = [
    dict(title="Coque sur ses berceaux",
         parts=["berceau_arriere", "berceau_avant", "coque_arriere", "coque_avant"],
         text="Coller les 2 moitiés de coque avec 5 goupilles de filament 1,75 mm × 12 mm (quille, fond, plats-bords), "
              "sur une surface plane. Poser la coque sur les 2 berceaux, le plus haut à l'avant : ils la tiennent pendant "
              "tout le montage.",
         cam=dict(eye=(560, 420, 300), target=(205, 0, 20), fov=34), k=1.0),
    dict(title="Filet noir, anneaux et autocollants",
         parts=FILETS + ["anneau_tableau"],
         text="Les filets noirs se couchent dans la rainure des flancs : l'arrière (avec la bande élargie) et l'avant "
              "de chaque côté, le même insert sert des 2 côtés en le retournant. Puis la petite bande du tableau. Une "
              "goutte de colle cyano par filet. Les 2 anneaux entrent en force dans leur fente près du coin arrière, "
              "sans colle. Immatriculation et nom : planche d'autocollants.",
         cam=dict(eye=(60, 470, 120), target=(190, 0, 40), fov=40), k=1.0),
    dict(title="Pont : SeaDek, tapis de plats-bords, taquets et boudins",
         parts=["seadeck_pointe_babord", "seadeck_pointe_tribord", "seadeck_passage_arriere"] + GW +
               ["taquet", "boudin_babord", "boudin_tribord"],
         text="Chaque tuile teck a 2 tenons dessous : la poser dans son logement, tenons dans les trous du pont, et "
              "appuyer, sans colle. Les 2 pointes, le passage arrière et les 8 tapis de plats-bords (1 à 4 de l'arrière "
              "vers l'avant, le n° 1 bâbord est percé pour le mât). Les 4 taquets ovales, chacun sur son tenon : 2 dans "
              "les tapis de la pointe, 2 entre les tapis arrière. Chaque boudin rayé se pose au pied de sa paroi sur 2 "
              "tenons.",
         cam=dict(eye=(470, 300, 330), target=(205, 0, 35), fov=34), k=1.6),
    dict(title="Banquette arrière",
         parts=["bandes_banquette_basse_assise", "bandes_banquette_haute_dossier", "coussin_banquette_basse_assise",
                "bandes_banquette_basse_dossier", "coussin_banquette_basse_dossier", "coussin_banquette_haute_dossier",
                "bandes_banquette_haute_assise", "coussin_banquette_haute_assise", "dos_dossier_arriere"],
         text="Suivre cet ordre, sinon une pièce barre le passage de la suivante. 1 : l'insert blanc de l'assise basse et "
              "celui du dossier haut dans leurs empreintes. 2 : le coussin de l'assise basse, enfilé par le dessus. 3 : "
              "l'insert du dossier bas, puis son coussin, enfilé par l'avant. 4 : le coussin du dossier haut, par l'avant. "
              "5 : l'insert de l'assise haute, puis son coussin par le dessus. Le dos taupe se colle derrière le dossier, "
              "au-dessus du tableau.",
         cam=dict(eye=(235, -95, 205), target=(40, 0, 52), fov=32), k=1.4),
    dict(title="Poste de pilotage",
         parts=["filet_caisson", "embase_fauteuil", "fauteuil", "bande_fauteuil", "pompe_direction", "branches_volant",
                "jante_volant", "moyeu_volant", "manette_gaz", "barre_console"],
         text="Filet noir dans son logement au dos du caisson, ses 2 tenons dans les trous du haut. Embases alu sur les tenons du caisson, fauteuils taupe sur "
              "le téton des embases ; dans chaque fauteuil, les 2 bandes blanches, souples, se pressent dans leurs rainures "
              "(l'assise d'abord, puis le dossier, une goutte de colle). Volant, à monter sur la table : les 6 barres du "
              "croisillon inox dans les encoches de la jante beige, le moyeu beige sur le bossage chromé ; puis la pompe "
              "noire contre la console et le volant sur sa colonne (filament de 16 mm qui traverse la pompe). Manette noire avec 1 goupille de 8 mm, barre de console dans ses 2 trous.",
         cam=dict(eye=(60, 95, 175), target=(128, 4, 62), fov=34, light=(-0.4, 0.5, 0.75)), k=0.55),
    dict(title="Console et son siège",
         parts=["pare_brise", "ecran_mfd", "ecran_tribord", "interrupteurs", "bandes_siege_console_assise",
                "coussin_siege_console_assise", "bandes_siege_console_dossier", "coussin_siege_console_dossier"],
         text="Pare-brise blanc dans sa fente. Écran multifonction debout à bâbord du tableau de bord, sa semelle sur "
              "le tenon de son logement ; petit écran encastré à tribord ; tableau d'interrupteurs sur les 2 petits "
              "tenons de la console, sous le volant. Siège : l'insert blanc de l'assise puis son coussin par le dessus, "
              "l'insert du dossier puis son coussin par l'avant.",
         cam=dict(eye=(345, -175, 190), target=(165, 0, 78), fov=36), k=1.0),
    dict(title="Banquette avant",
         parts=AVANT,
         text="Tout se pose sur des tenons de l'assise rigide : d'abord les 2 retours au bout, puis les 2 dossiers "
              "latéraux le long des parois, le dossier avant entre eux, et enfin les 3 assises.",
         cam=dict(eye=(530, -150, 240), target=(285, 0, 45), fov=34), k=1.4),
    dict(title="Coussins de plat-bord",
         parts=PADS_B + PADS_C,
         text="Chaque insert blanc dans son empreinte de la paroi (barrettes inclinées vers l'avant), puis le coussin "
              "s'enfile dessus. Numéros 1 à 3 de l'arrière vers l'avant ; bâbord et tribord ne s'échangent pas.",
         cam=dict(eye=(170, -175, 205), target=(160, 45, 55), fov=40), k=1.2),
    dict(title="Moteurs, gaines, flaps et échelle de bain",
         parts=["gaine_moteur", "embase_moteur", "jupe_moteur", "capot_moteur", "aileron_moteur", "verin_flap", "flap",
                "echelle_bain"],
         text="Les 2 gaines noires d'abord : tenon dans le passe-coque au milieu du tableau, gaine couchée sur la chaise. "
              "Puis chaque embase grise, poussée vers l'avant sur ses 2 goupilles de 12 mm : le bout de la gaine entre "
              "dans la tête de direction. Jupe blanche enfilée par l'arrière sur le tenon du bas de capot gris, capot "
              "blanc posé sur le tenon de son plan de joint, aileron noir glissé par l'arrière sur la plaque "
              "anti-cavitation. Flaps : poser le pied du vérin noir dans le berceau du flap, puis pousser les deux "
              "ensemble contre le tableau, sous la chaise (2 tenons du flap, 1 tenon du vérin). L'échelle repliée se "
              "pose sur les 2 tenons de la plateforme.",
         cam=dict(eye=(-250, 240, 170), target=(-20, 15, 40), fov=34, light=(-0.5, 0.45, 0.75)), k=1.0),
    dict(title="Armature du taud",
         parts=["cadre_taud", "boitier_echelle_babord", "boitier_echelle_tribord", "arceau_taud", "arceau_avant_taud"],
         text="Cadres : 2 tenons dans les logements chanfreinés du plat-bord (le tenon avant est plus gros : impossible de "
              "se tromper). Boîtiers blancs pressés en haut des échelles. Arceaux bombés dans les encoches du rail, arceau "
              "avant dans les encoches du bout relevé.",
         cam=dict(eye=(430, -360, 300), target=(150, 0, 85), fov=34), k=0.7),
    dict(title="Taud et pavillon",
         parts=["tissu_taud", "mat_pavillon"],
         text="En tissu (gabarit PDF) : coller la toile sur les 4 arceaux en partant du milieu, bords rabattus sous les "
              "rails. En option, le taud imprimé en TPU noir souple : poser la feuille sur l'armature, clipser les 8 clips sur les "
              "arceaux, puis rabattre les côtés et clipser les 6 clips sur les rails. Le mât de pavillon traverse le tapis "
              "n° 1 bâbord et s\'enfonce dans le plat-bord ; le drapeau de la planche d'autocollants se plie autour.",
         cam=dict(eye=(430, -360, 300), target=(150, 0, 85), fov=34), k=0.35),
]


def _project(cam, W, H, pts):
    r, u, f = look_at(cam["eye"], cam["target"])
    eye = np.asarray(cam["eye"], float)
    focal = (H / 2) / np.tan(np.radians(cam["fov"]) / 2)
    d = np.atleast_2d(pts) - eye
    X, Y, Z = d @ r, d @ u, d @ f
    return np.stack([X / Z * focal + W / 2, -Y / Z * focal + H / 2], 1)


def fade(rgb, a=0.55):
    return tuple(a * c + (1 - a) * 1.0 for c in rgb)


def render_step(data, rgb_of, step, done, W=1000, H=700, ss=2):
    """data : [(nom, couleur, k, trimesh mm, explode mm)] ; done : noms deja poses."""
    new = set(step["parts"])
    k = step.get("k", 1.0)
    ex_over = step.get("explode", {})
    parts, arrows = [], []
    for (n, c, i, tm, ex) in data:
        if n in done:
            parts.append((tm, rgb_of(c) if step.get("vif") else fade(rgb_of(c))))   # vif : rien d'estompe
        elif n in new:
            if ex_over.get(n) is not None:
                e = np.asarray(ex_over[n], float)
            else:
                e = np.asarray(ex, float) * k
            t = trimesh.Trimesh(tm.vertices + e, tm.faces, process=False)
            parts.append((t, rgb_of(c)))
            if np.linalg.norm(e) > 3:
                cen = tm.bounds.mean(0)
                arrows.append((cen + e, cen))
    for a, b in step.get("fleches", ()):                          # fleches en plus (repere du rendu, mm) : montrer un detail
        arrows.append((np.asarray(a, float), np.asarray(b, float)))
    cam = step["cam"]
    im = render(parts, eye=cam["eye"], target=cam["target"], fov=cam["fov"], W=W, H=H, ss=ss,
                light=cam.get("light", (0.35, -0.5, 0.8))).convert("RGB")
    dr = ImageDraw.Draw(im)
    for a, b in arrows:
        (x0, y0), (x1, y1) = _project(cam, W, H, np.array([a, b]))
        L = np.hypot(x1 - x0, y1 - y0)
        if L < 14:
            continue
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        xe, ye = x1 - ux * 6, y1 - uy * 6
        dr.line([(x0, y0), (xe, ye)], fill=(214, 64, 32), width=3)
        px, py = -uy, ux
        dr.polygon([(xe + ux * 6, ye + uy * 6), (xe - ux * 8 + px * 6, ye - uy * 8 + py * 6),
                    (xe - ux * 8 - px * 6, ye - uy * 8 - py * 6)], fill=(214, 64, 32))
    return im


def autocrop(im, m=12):
    bg = Image.new(im.mode, im.size, (255, 255, 255))
    bb = ImageChops.difference(im.convert("RGB"), bg.convert("RGB")).getbbox()
    if not bb:
        return im
    return im.crop((max(bb[0] - m, 0), max(bb[1] - m, 0), min(bb[2] + m, im.width), min(bb[3] + m, im.height)))


def nbsp(t):
    """Espaces insecables du francais (avant : ; ? ! », apres «) : la coupure de ligne ne les separe jamais."""
    t = re.sub(r" ([:;?!»])", "\u00a0\\1", t)
    return t.replace("« ", "«\u00a0")


def build_pdf(path, data, rgb_of, nice, colors, cover_img, intro_lines, fit_lines, step_imgs=None):
    """PDF A4 : couverture (apercu + legende), puis 2 etapes par page."""
    counts = OrderedDict()
    for (n, c, i, tm, ex) in data:
        counts[n] = counts.get(n, 0) + 1
    imgs = step_imgs or []
    with PdfPages(path) as pdf:
        # ---- couverture
        fig = plt.figure(figsize=(210 / 25.4, 297 / 25.4))
        fig.text(0.07, 0.955, "Bowen 28 au 1:19 – notice de montage", fontsize=17, weight="bold", va="top")
        fig.text(0.07, 0.925, "Comme un Lego : chaque pièce a sa place et s'emboîte. Imprimer les plateaux, puis suivre les étapes.",
                 fontsize=9, va="top", color="#333")
        ax = fig.add_axes([0.05, 0.50, 0.90, 0.40]); ax.imshow(cover_img); ax.axis("off")
        y = 0.48
        for line in intro_lines + [""] + fit_lines:
            head = line.startswith("#")
            fig.text(0.07, y, line.lstrip("# "), fontsize=9.2 if head else 8.4, va="top", color="#111" if head else "#333",
                     weight="bold" if head else "normal")
            y -= 0.022 if line else 0.008
        pdf.savefig(fig); plt.close(fig)
        # ---- etapes : 2 par page ; l'image se reduit si le texte de l'etape est long (jamais de chevauchement)
        import textwrap
        SLOT, HEAD, GAP_T, L_P, L_T = 0.485, 0.020, 0.007, 0.016, 0.0185
        for p0 in range(0, len(STEPS), 2):
            fig = plt.figure(figsize=(210 / 25.4, 297 / 25.4))
            for j, si in enumerate(range(p0, min(p0 + 2, len(STEPS)))):
                st = STEPS[si]
                top = 0.965 - j * SLOT
                fig.text(0.06, top, f"Étape {si + 1} – {st['title']}", fontsize=13, weight="bold", va="top")
                plist = OrderedDict()
                for n in st["parts"]:
                    plist[n] = counts.get(n, 1)
                txt = "Pièces : " + ", ".join(f"{nice(n)}{' ×' + str(q) if q > 1 else ''}" for n, q in plist.items())
                p_lines = textwrap.wrap(nbsp(txt), 118, break_on_hyphens=False)
                t_lines = textwrap.wrap(nbsp(st["text"]), 108, break_on_hyphens=False)
                text_h = len(p_lines) * L_P + 0.004 + len(t_lines) * L_T
                img_h = min(0.325, SLOT - 0.012 - HEAD - GAP_T - text_h)
                y0 = top - HEAD - img_h
                im = autocrop(imgs[si])
                ax = fig.add_axes([0.05, y0, 0.90, img_h]); ax.imshow(im); ax.axis("off")
                yy = y0 - GAP_T
                for line in p_lines:
                    fig.text(0.06, yy, line, fontsize=7.6, va="top", color="#555"); yy -= L_P
                yy -= 0.004
                for line in t_lines:
                    fig.text(0.06, yy, line, fontsize=8.6, va="top", color="#111"); yy -= L_T
                assert yy > top - SLOT, f"etape {si + 1} : texte trop long"
            pdf.savefig(fig); plt.close(fig)
