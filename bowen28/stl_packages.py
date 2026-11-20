"""Paquets STL d'une version : une liste par couleur (LISTE_couleur.txt), un zip par couleur et un zip complet.

Appele par build_vXX.py apres pieces.build_all() : les STL sont deja ecrits dans OUT/stl_par_couleur/<couleur>/.
"""
import os, json, zipfile, textwrap
from collections import OrderedDict
import numpy as np

ORDER = ["blanc", "alu", "noir", "teck", "taupe"]
TITLE = {"blanc": "BLANC (blanc cassé)", "alu": "GRIS ALU / ARGENT", "noir": "NOIR", "teck": "TECK (beige / bois)", "taupe": "TAUPE"}
LABEL = {"blanc": "Blanc (blanc cassé)", "alu": "Gris alu / argent", "noir": "Noir", "teck": "Teck (beige / bois)", "taupe": "Taupe"}
SUPPORT = {"coque_arriere": "oui, arborescents + bordure", "coque_avant": "oui, arborescents + bordure",
           "embase_moteur": "oui, arborescents"}
# filaments Bambu Lab conseilles (v20) : les plus proches des couleurs de la maquette
FILAMENT = {"blanc": "PLA Matte Ivory White", "alu": "PLA Basic Silver", "noir": "PLA Matte Charcoal",
            "teck": "PLA Matte Caramel", "taupe": "PLA Matte Dark Brown"}
FILAMENT_OPTION = "TPU 90A Black"
TIPS = {
    "blanc": ["Coques : debout, quille en bas, supports arborescents « sur le plateau uniquement » et bordure de 5 mm.",
              "__COQUES__",
              "Capots moteur : posés sur leur plan de joint (le dessous plat), sans support.",
              "Jupes moteur : à l'envers, posées sur leur face du dessus (plate), sans support.",
              "Inserts « bandes_… » : à plat sur leur semelle de 0,6 mm, barrettes vers le haut, sans support.",
              "Pare-brise : à plat, sans support. Bandes de fauteuils : couchées sur le flanc (le L à plat), sans support."],
    "alu": ["Embases moteur (avec le bas de capot gris) : debout, supports arborescents « sur le plateau uniquement ».",
            "Berceaux et embases de fauteuils : debout, sans support.",
            "Cadres et arceaux du taud, échelle repliée, mât, croisillon du volant, barre, taquets, anneaux et flaps : à plat, "
            "sans support (charnière des flaps vers le haut)."],
    "noir": ["Filets de coque, écrans, interrupteurs, filet du caisson, ailerons et gaines : à plat, sans support ; "
             "couches de 0,08 mm pour la finesse.",
             "Les filets noirs servent des 2 côtés : imprimer 2 fois chacun, retourner l'un des deux pour le flanc tribord.",
             "Manette des gaz et vérins de flaps : couchés sur le flanc ; pompe de direction : debout sur sa base. Sans support.",
             "Sous-dossier option_taud_imprime : le taud imprimé, seulement si tu ne fais pas la toile en tissu. En TPU 90A "
             "noir (souple) : à plat, le dessus sur le plateau et les 14 clips vers le haut, sans support. Profil « Bambu TPU "
             "90A », bobine séchée et branchée en direct (pas dans l'AMS lite), colle sur le plateau."],
    "teck": ["Tuiles SeaDek, tapis de plats-bords, jante et moyeu du volant : à plat, rainures vers le haut, sans support."],
    "taupe": ["Coussins sur leur face plate (dessous ou dos), sans support ; dossiers et retours de la banquette avant debout.",
              "Fauteuils : debout, la cavité vers le haut, sans support. Dos du dossier arrière : debout.",
              "Les petits ponts au-dessus des logements de tenons et des fentes (moins de 5 mm) s'impriment sans support."],
}
SHELL, INFILL, RHO = 1.0, 0.15, 1.24


def nbsp(t):
    """Espaces insecables du francais (avant : ; ? ! », apres «)."""
    import re
    return re.sub(r" ([:;?!»])", "\u00a0\\1", t).replace("« ", "«\u00a0")


def para(text, first="", rest="", width=98):
    return textwrap.wrap(nbsp(text), width, initial_indent=first, subsequent_indent=rest, break_on_hyphens=False, break_long_words=False)


def fr(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def round_g(g):
    return max(5, int(round(g / 10.0)) * 10) if g >= 10 else max(1, int(round(g)))


def hull_sentence(plates, rest="le reste"):
    """Repartition des 2 moities de coque sur les plateaux, lue dans la mise en plateaux."""
    alone, shared = [], []
    for p in plates:
        names = [iid.split("#")[0] for (iid, x, y, r) in p["items"]]
        for h in ("coque_arriere", "coque_avant"):
            if h in names:
                (alone if len(names) == 1 else shared).append(h)
    if len(alone) == 2:
        return "Les 2 moitiés de coque occupent chacune tout un plateau : coque_arriere et coque_avant seules."
    if len(alone) == 1 and len(shared) == 1:
        return f"Les 2 moitiés ne tiennent pas sur le même plateau : {alone[0]} seule, {shared[0]} avec {rest}."
    return "Les 2 moitiés de coque sont sur 2 plateaux différents, chacune avec d'autres pièces blanches."


def grams(tm, qty):
    V, A = float(tm.volume), float(tm.area)
    est = min(V, A * SHELL) + INFILL * max(0.0, V - A * SHELL)
    return est * RHO / 1000.0 * qty


def build(C, meshes, plates, out, version, content):
    """Ecrit les listes par couleur, puis les zips par couleur et le zip complet dans le dossier parent de out."""
    here = os.path.dirname(out)
    src = os.path.join(out, "stl_par_couleur")
    plate_of = {}
    for k, p in enumerate(plates):
        for (iid, x, y, rot) in p["items"]:
            plate_of.setdefault(iid.split("#")[0], set()).add(k + 1)
    summary = OrderedDict()
    for col in ORDER:
        rows = sorted([e for e in C if e["color"] == col], key=lambda e: (bool(e.get("option")), e["file"]))
        main = [e for e in rows if not e.get("option")]
        opt = [e for e in rows if e.get("option")]
        g_main = sum(grams(meshes[e["name"]], e["qty"]) for e in main)
        g_opt = sum(grams(meshes[e["name"]], e["qty"]) for e in opt)
        pl = sorted({p for e in main for p in plate_of[e["name"]]})
        opl = sorted({p for e in opt for p in plate_of[e["name"]]})
        nf, npr = len(main), sum(e["qty"] for e in main)
        summary[col] = dict(files=nf, prints=npr, grams=round_g(g_main), opt_grams=round_g(g_opt) if opt else 0, plates=pl, oplates=opl)
        L = []
        head = f"BOWEN 28 AU 1:19 – STL {TITLE[col]} – version {version}"
        L += [head, "=" * len(head), ""]
        L += para(f"Contenu : {content[col]}.")
        qs = sorted({e["qty"] for e in main if e["qty"] > 1})
        mult = (" (" + " ou ".join(f"« _x{q} »" for q in qs) + " à la fin du nom = imprimer " + " ou ".join(str(q) for q in qs) + " fois)") if qs else ""
        L += para(f"{nf} fichiers, {npr} impressions{mult}.")
        if opt:
            L.append(f"+ en option : {len(opt)} fichier (taud imprimé).")
        L += para(f"Filament : environ {summary[col]['grams']} g de Bambu {FILAMENT[col]}" + (f" (+ {summary[col]['opt_grams']} g de Bambu {FILAMENT_OPTION} souple pour le taud en option)" if opt else "")
                  + ", estimation hors supports ; le trancheur donne le chiffre exact.")
        L += para("Mêmes pièces que le" + ("s plateaux 3MF " if len(pl) > 1 else " plateau 3MF ") + " et ".join(map(str, pl))
                  + (f" (option : plateau {opl[0]})" if opl else "") + f" du kit v{version}.")
        L += ["", "IMPRESSION", "----------"]
        L += para("Fichiers en millimètres, déjà orientés pour l'impression (bonne face en bas) : les glisser dans Bambu Studio "
                  "sans les tourner, puis « Disposer » pour les répartir sur le plateau de l'A1.", "- ", "  ")
        L += para("PLA, buse 0,4 mm, couches de 0,12 mm, 3 périmètres, 10 à 15 % de remplissage gyroïde.", "- ", "  ")
        for t in TIPS[col]:
            L += para(hull_sentence(plates) if t == "__COQUES__" else t, "- ", "  ")
        L += para("Emboîtement trop serré ? « Compensation X-Y des trous » à 0,05 mm dans Bambu Studio, ou ponçage léger.", "- ", "  ")
        L += ["", "FICHIERS", "--------"]
        show = lambda e: ("option_taud_imprime/" if e.get("option") else "") + os.path.basename(e["file"])
        w = max(len(show(e)) for e in rows) + 2
        L.append(f"{'Fichier':{w}s}{'Qté':>4s}   {'Dimensions (mm)':24s}{'Supports':30s}Plateau")
        for e in rows:
            ext = meshes[e["name"]].extents
            dims = " × ".join(fr(v) for v in ext)
            sup = SUPPORT.get(e["name"], "non")
            pls = ", ".join(map(str, sorted(plate_of[e["name"]]))) + (" (option)" if e.get("option") else "")
            L.append(f"{show(e):{w}s}{e['qty']:>4d}   {dims:24s}{sup:30s}{pls}")
        L.append("")
        open(os.path.join(src, col, f"LISTE_{col}.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    # zips par couleur
    deliv = os.path.join(here, f"stl_par_couleur_v{version}")
    os.makedirs(deliv, exist_ok=True)
    zips = []
    for col in ORDER:
        zp = os.path.join(deliv, f"Bowen28_STL_{col}.zip")
        top = f"Bowen28_STL_{col}"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(os.path.join(src, col)):
                dirs.sort()
                for fn in sorted(files):
                    full = os.path.join(root, fn)
                    z.write(full, top + "/" + os.path.relpath(full, os.path.join(src, col)).replace(os.sep, "/"))
        zips.append(zp)
    json.dump(summary, open(os.path.join(deliv, "_resume.json"), "w"), ensure_ascii=False, indent=1)
    return summary, zips


def build_complete(C, plates, out, version, summary, steps, nice, short):
    """Zip unique : un dossier par couleur + LISEZMOI (rangement, impression, pieces par etape)."""
    here = os.path.dirname(out)
    src = os.path.join(out, "stl_par_couleur")
    top = f"Bowen28_STL_complet_v{version}"
    by = {e["name"]: e for e in C}
    n_files = sum(1 for e in C if not e.get("option")); n_prints = sum(e["qty"] for e in C if not e.get("option"))
    L = []
    title = f"BOWEN 28 CENTER CONSOLE AU 1:19 – TOUTES LES PIÈCES EN STL (version {version})"
    L += [title, "=" * len(title), ""]
    L += para(f"Toutes les pièces imprimables de la maquette, rangées par couleur de filament : un dossier = une couleur "
              f"= une bobine à charger sur l'A1. {n_files} fichiers ({n_prints} impressions), plus le taud imprimé en option (TPU souple).")
    L += ["", "RANGEMENT", "---------", f"{top}/", "├── LISEZMOI.txt   ce fichier : rangement, impression, pièces par étape de montage"]
    for i, c in enumerate(ORDER):
        s = summary[c]; last = i == len(ORDER) - 1
        L.append(f"{'└──' if last else '├──'} {c + '/':7s}{s['files']:3d} STL, {s['prints']:2d} impressions   {short[c]}")
        if s["oplates"]:
            L.append(f"{'    ' if last else '│  '} └── option_taud_imprime/   1 STL : taud imprimé, seulement si tu ne fais pas la toile")
    L += para("Chaque dossier contient aussi sa liste (LISTE_couleur.txt) : quantité, dimensions, supports et plateau 3MF "
              "correspondant de chaque pièce.")
    L += ["", "IMPRESSION (Bambu Lab A1, plateau de 256 × 256 mm)", "--------------------------------------------------"]
    for t in ["Fichiers en millimètres, à l'échelle 1:19, déjà orientés pour l'impression (bonne face en bas) : ouvrir un "
              "dossier, glisser ses STL dans Bambu Studio sans les tourner, puis « Disposer ».",
              "« _x2 », « _x3 » ou « _x4 » à la fin du nom = imprimer la pièce 2, 3 ou 4 fois.",
              "PLA, buse 0,4 mm, couches de 0,12 mm (0,08 mm pour le noir), 3 périmètres, 10 à 15 % de remplissage gyroïde.",
              "Supports (arborescents, « sur le plateau uniquement ») seulement pour les 2 moitiés de coque (avec une bordure "
              "de 5 mm) et les embases moteur. Toutes les autres pièces s'impriment sans support, y compris le taud en TPU.",
              "Filaments Bambu Lab conseillés : " + " ; ".join(f"{LABEL[c].split(' (')[0].lower()} = {FILAMENT[c]}" for c in ORDER)
              + f" ; taud imprimé en option = {FILAMENT_OPTION} (souple).",
              hull_sentence(plates, "les autres pièces blanches"),
              "Emboîtement trop serré ? « Compensation X-Y des trous » à 0,05 mm dans Bambu Studio, ou ponçage léger."]:
        L += para(t, "- ", "  ")
    L += ["", f"  {'Couleur':22s}{'Fichiers':>9s}{'Impressions':>13s}   {'Plateaux 3MF':17s}Filament (environ, hors supports)"]
    for c in ORDER:
        s = summary[c]
        f = f"{s['files']}" + (" (+1)" if s["oplates"] else ""); p = f"{s['prints']}" + (" (+1)" if s["oplates"] else "")
        pl = ", ".join(map(str, s["plates"])) + (f" (option : {s['oplates'][0]})" if s["oplates"] else "")
        g = f"{s['grams']} g" + (f" (+{s['opt_grams']} g pour le taud)" if s["oplates"] else "")
        L.append(f"  {LABEL[c]:22s}{f:>9s}{p:>13s}   {pl:17s}{g}")
    L += ["", "MONTAGE : PIÈCES PAR ÉTAPE (même ordre que notice_de_montage.pdf)",
          "-----------------------------------------------------------------"]
    for k, st in enumerate(steps, 1):
        L.append(f"Étape {k} – {st['title']}")
        for n in st["parts"]:
            if n in by:
                e = by[n]
                L.append(f"    {e['file'].replace('stl_par_couleur/', ''):56s}{nice(n)}" + (f" ×{e['qty']}" if e["qty"] > 1 else ""))
            elif n == "tissu_taud":
                L.append(f"    {'(tissu, pas de STL)':56s}toile du taud : gabarit_taud_tissu.pdf du kit")
                opt = [e for e in C if e.get("option")][0]
                L.append(f"    {opt['file'].replace('stl_par_couleur/', ''):56s}ou, en option, le taud imprimé")
        L.append("")
    L += ["À PRÉVOIR EN PLUS (non imprimé)", "-------------------------------"]
    for t in ["11 goupilles coupées dans du filament 1,75 mm : 5 × 12 mm (jonction de coque), 4 × 12 mm (moteurs), "
              "1 × 8 mm (manette), 1 × 16 mm (volant).",
              "Colle cyanoacrylate : jonction de coque, filets noirs, tuiles et tapis SeaDek, taquets, pieds des vérins de "
              "flaps, toile du taud.",
              "La planche d'autocollants (immatriculation, nom, pavillon) : planche_autocollants.pdf du kit, sur papier décalque.",
              "Toile fine noire pour le taud en tissu, sauf si tu imprimes l'option.",
              "En option : un feutre peinture blanc pour le liseré des fauteuils, du noir pour les boutons des capots et le "
              "haut du mât."]:
        L += para(t, "- ", "  ")
    readme = "\n".join(L) + "\n"
    zp = os.path.join(here, f"{top}.zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{top}/LISEZMOI.txt", readme)
        for c in ORDER:
            for root, dirs, files in os.walk(os.path.join(src, c)):
                dirs.sort()
                for fn in sorted(files):
                    full = os.path.join(root, fn)
                    z.write(full, f"{top}/{c}/" + os.path.relpath(full, os.path.join(src, c)).replace(os.sep, "/"))
    return zp, readme
