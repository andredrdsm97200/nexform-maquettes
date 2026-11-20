"""Assemble la maquette du Boston Whaler 17 Montauk du client et l'exporte au format du site (1:12)."""
import sys, time
import numpy as np
from model import *
from export import to_site

# ------------------------------------------------------------------ implantation (cotes relevees sur les photos, en m depuis le tableau)
# v2 : retours du client sur le BAT v1 (console a tribord, plage avant agrandie, manette en T, coussins capitonnes, volant a creux)
AFT_BENCH = (1.10, 1.55)        # banquette arriere (pilote), 30 cm derriere la console, poteau inox au centre
FWD_BENCH = (CON_X1, 2.80)      # banquette avant pleine largeur, dossier contre la console, nourrices dessous a babord
PLAGE_HATCH = (3.80, 4.30, 0.34)  # grande trappe sur la plage avant, charnieres cote etrave (photos « avant » et « poste »)
VISITE = (3.30, 0.0)            # petite trappe de visite au plancher du cockpit avant
AFT_HATCH = (0.40, 0.66, 0.13, 0.12)  # x0, x1, demi-largeur, decalage babord

def sheared(m, x0, z0, slope):
    """Incline une piece construite a plat (z0) pour suivre une surface de pente « slope » le long de x."""
    return m.transform([[1, 0, 0, 0], [0, 1, 0, 0], [slope, 0, 1, -slope * x0]])

def deck_slope(x0, x1):
    return (float(zs(x1)) - float(zs(x0))) / (x1 - x0)

def parts():
    P = []
    add = lambda id_, nm, k, m, e=(0, 0, 0): P.append(dict(id=id_, nm=nm, k=k, m=m, e=e))

    hl = hull()
    add("coque", "Coque", "coque", hl)
    add("liston", "Liston", "liston", rub_rail(), (0, 0, 0.10))

    # plage avant : grande trappe (charnieres cote etrave), bitte en T ; pont d'etrave : taquets, feu de navigation
    x0, x1, hw = PLAGE_HATCH; za, zb = z_plage(x0), z_plage(x1); sl = (zb - za) / (x1 - x0)
    lid, hw_ = hatch(x0, x1, hw, za - 0.004, hinge_fwd=True)
    add("trappe_avant", "Trappe de la plage avant", "trappe", sheared(lid, x0, za, sl), (0, 0, 0.30))
    add("charnieres_avant", "Charnières de la trappe avant", "inox", sheared(hw_, x0, za, sl), (0, 0, 0.30))
    xb_ = 4.56
    add("bitte", "Bitte d'amarrage", "trappe", bollard(xb_, z_plage(xb_) - 0.06, z_plage(xb_) + 0.075) - hl, (0.10, 0, 0.32))
    cl = None
    for sgn in (1, -1):
        xc_ = 4.93
        c = cleat(xc_, sgn * 0.25, float(zs(xc_)) - 0.004, ang=sgn * np.radians(105), l=0.15)
        cl = c if cl is None else cl + c
    add("taquets_avant", "Taquets avant", "inox", cl, (0.15, 0, 0.30))
    zn = float(zs(4.985))
    nav = cyl((4.985, 0, zn - 0.01), (4.985, 0, zn + 0.03), 0.05, 0.045, 28) + (sphere((4.985, 0, zn + 0.03), 0.042, 28) ^ box(4.8, 5.1, -0.1, 0.1, zn + 0.03, zn + 0.2))
    add("feu", "Feu de navigation", "gris", nav, (0.25, 0, 0.35))

    # cockpit : trappe de visite (cockpit avant), trappe arriere
    xv, yv = VISITE; zv = zfloor(xv)
    add("trappe_visite", "Trappe de visite", "trappe", extrude_xy(rounded_rect(xv, yv, 0.08, 0.08, 0.02), zv - 0.004, zv + 0.008), (0, 0, 0.25))
    x0, x1, hw, dy = AFT_HATCH
    lid = extrude_xy(rounded_rect((x0 + x1) / 2, dy, (x1 - x0) / 2, hw, 0.025), FLOOR - 0.004, FLOOR + 0.008)
    add("trappe_arriere", "Trappe arrière", "trappe", lid, (0, 0, 0.25))

    # console calee a tribord, passage a babord
    c = console()
    add("console", "Console", "coque", c["body"], (0, -0.10, 0.45))
    add("volant", "Volant", "inox", c["wheel"], (-0.30, -0.10, 0.70))
    add("moyeu", "Moyeu de volant", "noir", c["hub"], (-0.36, -0.10, 0.72))
    add("compas", "Compas", "noir", c["compass"], (0, -0.10, 0.80))
    add("instruments", "Compte-tours et interrupteurs", "noir", c["gauge"], (-0.18, -0.10, 0.58))
    add("commande", "Commande moteur (manette en T)", "noir", c["throttle"], (-0.20, -0.30, 0.55))
    add("porte_cannes", "Porte-cannes", "coussin", c["rod"], (0, 0.30, 0.50))
    add("dossier", "Dossier de la banquette avant", "coussin", dossier(c["body"]), (0.30, -0.10, 0.55))

    # banquettes
    xa, xb = AFT_BENCH; half = w_ck((xa + xb) / 2) + 0.02
    frame, cush, post, rails = bench(xa, xb, half, with_post=True)
    add("banquette_arriere", "Banquette arrière", "coque", frame, (0, 0, 0.35))
    add("coussin_arriere", "Coussin arrière", "coussin", cush, (0, 0, 0.60))
    add("poteau", "Poteau de banquette", "inox", post, (0, 0, 0.18))
    add("mains_courantes_arriere", "Mains courantes arrière", "inox", rails, (0, 0, 0.70))
    xa, xb = FWD_BENCH; half = w_ck((xa + xb) / 2) + 0.02
    frame, cush, _, rails = bench(xa + 0.005, xb, half, with_post=False)
    add("banquette_avant", "Banquette avant", "coque", frame, (0.10, 0, 0.35))
    add("coussin_avant", "Coussin avant", "coussin", cush, (0.10, 0, 0.60))
    add("mains_courantes_avant", "Mains courantes avant", "inox", rails, (0.10, 0, 0.70))
    tk = fuel_tank(CON_X1 + 0.09, -0.01) + fuel_tank(CON_X1 + 0.09, 0.30)       # deux nourrices a babord (photos « avant » et « poste »)
    add("nourrices", "Nourrices", "rouge", tk, (0.45, 0, 0.12))

    # taquets arriere
    cl = None
    for sgn in (1, -1):
        c2 = cleat(0.17, sgn * (float(ys(0.17)) - 0.05), float(zs(0.17)) - 0.004, ang=0.0, l=0.14)
        cl = c2 if cl is None else cl + c2
    add("taquets_arriere", "Taquets arrière", "inox", cl, (-0.10, 0, 0.30))

    # moteur Suzuki DF90A (sans marquage)
    e = engine()
    add("moteur", "Moteur", "moteur", e["body"], (-0.70, 0, 0.10))
    add("capot_joint", "Joint de capot", "noir", e["band"], (-0.70, 0, 0.10))
    add("support_moteur", "Support moteur", "gris", e["bracket"], (-0.40, 0, 0.0))
    add("helice", "Hélice", "noir", e["prop"], (-1.05, 0, 0.10))

    add("berceau", "Berceau de présentation", "berceau", cradle(), (0, 0, -0.45))

    # pieces posees sur la coque : on retire la partie noyee pour qu'elles s'impriment et s'assemblent sans chevauchement
    pose = {"trappe_avant", "charnieres_avant", "taquets_avant", "feu", "trappe_visite", "trappe_arriere", "console",
            "banquette_arriere", "banquette_avant", "poteau", "taquets_arriere", "support_moteur"}
    for p in P:
        if p["id"] in pose:
            p["m"] = p["m"] - hl
    return P

if __name__ == "__main__":
    t = time.time()
    P = parts()
    for p in P:
        assert not p["m"].is_empty(), p["id"]
    import os
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorties"), exist_ok=True)
    to_site(P, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorties", "whaler.json"))
    print("exported", len(P), "parts", round(time.time() - t, 1), "s")
