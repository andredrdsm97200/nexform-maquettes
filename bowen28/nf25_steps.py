# -*- coding: utf-8 -*-
"""Contenu de la notice v25.4 facon Lego, SANS COLLE (tutoiement, phrases courtes). L'ordre des pieces est l'ordre verifie."""
BG = (242, 244, 250); PANEL = (255, 255, 255)
GW = [f"seadeck_plat_bord_{k}_{s}" for k in (1, 2, 3, 4) for s in ("babord", "tribord")]
AV = ["coussin_avant_retour_babord", "coussin_avant_retour_tribord", "coussin_avant_dossier_babord", "coussin_avant_dossier_tribord",
      "coussin_avant_dossier_avant", "coussin_avant_assise_babord", "coussin_avant_assise_tribord", "coussin_avant_assise_avant"]
PC = lambda k: [f"coussin_plat_bord_{k}_babord", f"coussin_plat_bord_{k}_tribord"]
def S(title, parts=None, todo=(), glue=None, tip=None, subs=None, **kw):
    if subs: parts = [p for s in subs for p in s['parts']]
    return dict(title=title, parts=parts, todo=list(todo), glue=glue, tip=tip, subs=subs, **kw)
def sub(cap, *parts, **kw): return dict(cap=cap, parts=list(parts), **kw)
FN = lambda seg: [f"filet_noir_{seg}_babord", f"filet_noir_{seg}_tribord"]
# v25.3 : pare-battages a une ficelle dont le crochet s'accroche a l'anneau ; vue de dessus, puis de l'anneau tribord
CAM_ANNEAU = dict(eye=(50.0, 18.0, 64.0), target=(79.0, -48.0, 45.0), fov=34)
FLECHE_ANNEAU = [((80.0, -30.0, 57.0), (80.0, -49.4, 44.2))]       # repere du rendu (x avant, y babord, z haut)
CAM_PB = dict(eye=(-110.0, 0.0, 330.0), target=(150.0, 0.0, 30.0), fov=40)          # les 4 pare-battages, vus de dessus
STEPS = [
    S("La coque", ["socle", "coque_arriere", "coque_avant", "cle_jonction_fond", "cle_jonction_plat_bord"],
      ["Pousse la coque avant contre la coque arrière : ses 3 tenons losange entrent dans les trous de la coque avant.",
       "Enfonce les 2 clés du plancher par le dessus, jusqu'à ce qu'elles affleurent.",
       "Puis les 2 clés des plats-bords, grosse tête vers l'arrière.",
       "Pose la coque sur son socle, l'avant du bateau sur le berceau le plus haut."],
      tip="Les clés serrent les 2 coques l'une contre l'autre : appuie bien droit, avec le pouce."),
    S("Les filets noirs", FN("arriere") + FN("avant") + FN("tableau") + ["anneau_tableau"],
      ["Chaque filet a des petits tenons au dos. Présente-le dans la rainure du flanc et enfonce les tenons un par un, de l'arrière vers l'avant.",
       "Bâbord et tribord ont chacun leurs filets : arrière (bande large), puis avant.",
       "Les 2 petites bandes sur le tableau arrière, tenons dans leurs trous.",
       "Enfonce les 2 anneaux dans leur fente, près du coin arrière."],
      tip="Le filet est souple : une fois ses tenons enfoncés, il suit la courbe de la coque tout seul."),
    S("Le pont", ["seadeck_pointe_babord", "seadeck_pointe_tribord", "seadeck_passage_arriere"] + GW + ["taquet", "boudin_babord", "boudin_tribord"],
      ["Chaque tuile SeaDek a 2 tenons dessous : pose-la dans son logement et appuie.",
       "Tapis de plats-bords : n° 1 à 4, de l'arrière vers l'avant. Le n° 4 recouvre la tête des clés.",
       "Les 4 taquets : 2 dans les tuiles de la pointe, 2 entre les tapis arrière.",
       "Les 2 boudins rayés au pied des parois, sur leurs 2 tenons."],
      tip="Le tapis n° 1 bâbord est percé : c'est le trou du mât de pavillon."),
    S("La banquette arrière", order=True,
      tip="Suis les numéros : dans un autre ordre, un coussin barre le passage du suivant.",
      subs=[sub("Coussin de l'assise basse, enfilé par le dessus sur les nervures blanches de la coque.", "coussin_banquette_basse_assise"),
            sub("Coussin du dossier bas, enfilé par l'avant.", "coussin_banquette_basse_dossier"),
            sub("Coussin du dossier haut, par le dessus.", "coussin_banquette_haute_dossier"),
            sub("Coussin de l'assise haute, par le dessus.", "coussin_banquette_haute_assise"),
            sub("Dos taupe derrière le dossier, poussé vers l'avant : ses 3 tenons losange dans les 3 trous.", "dos_dossier_arriere")]),
    S("Le poste de pilotage", order=True,
      tip="Monte le volant sur la table, puis pose-le avant les fauteuils : après, le fauteuil bâbord lui barre le passage.",
      subs=[sub("Filet noir au dos du caisson : ses 2 tenons dans les trous du haut.", "filet_caisson"),
            sub("Pompe noire sur le tenon de la console. Croisillon sur le tenon de la pompe, jante sur les branches, moyeu au centre.", "pompe_direction", "branches_volant", "jante_volant", "moyeu_volant"),
            sub("Manette double (un levier par moteur) : son tenon losange dans la console. Barre de console dans ses 2 trous.", "manette_gaz", "barre_console"),
            sub("Embases alu sur les tenons du caisson, puis un fauteuil sur chaque embase.", "embase_fauteuil", "fauteuil"),
            sub("2 bandes blanches par fauteuil, enfoncées dans leur rainure : l'assise d'abord, puis le dossier.", "bande_fauteuil")]),
    S("La console et son siège", ["ecran_mfd", "ecran_tribord", "interrupteurs", "coussin_siege_console_assise", "coussin_siege_console_dossier"],
      ["Le pare-brise blanc fait partie de la coque : rien à poser.",
       "Grand écran debout à bâbord, sa semelle sur le tenon. Petit écran enfoncé dans son logement à tribord.",
       "Tableau d'interrupteurs sur les 2 petits tenons, sous le volant.",
       "Siège : coussin d'assise par le dessus, puis coussin du dossier par l'avant."],
      tip="Les bandes blanches du siège sont des nervures de la coque : chaque coussin s'enfile dessus."),
    S("La banquette avant", AV,
      ["Tout se pose sur les tenons de l'assise.",
       "D'abord les 2 retours, au bout.",
       "Puis les 2 dossiers le long des parois, et le dossier avant entre eux.",
       "Les 3 assises pour finir."]),
    S("Les coussins de plat-bord", PC(1) + PC(2) + PC(3),
      ["Chaque coussin taupe s'enfile sur les nervures blanches de la paroi, inclinées vers l'avant.",
       "N° 1 à 3, de l'arrière vers l'avant."],
      tip="Bâbord et tribord ne s'échangent pas : si ça force, essaie l'autre côté."),
    S("Les moteurs", order=True,
      tip="La gaine avant le moteur, toujours. Après, elle ne passe plus.",
      subs=[sub("Les 2 gaines noires : tenon dans le passe-coque, gaine couchée sur la chaise.", "gaine_moteur"),
            sub("Sur la table : l'embase sous le bloc gris (2 tenons), l'hélice au bout de la torpille. Puis pousse le moteur vers l'avant : ses 2 tenons losange entrent dans la chaise, la gaine dans la tête.",
                "bloc_moteur", "embase_moteur", "helice"),
            sub("Jupe blanche, enfilée par l'arrière sur son tenon.", "jupe_moteur"),
            sub("Cheville dans le dessus du bloc gris, capot blanc par le dessus, aileron noir par l'arrière.", "cheville_capot", "capot_moteur", "aileron_moteur"),
            sub("Pied du vérin dans le berceau du flap, puis pousse les deux ensemble contre le tableau.", "verin_flap", "flap"),
            sub("Échelle de bain sur ses 2 tenons.", "echelle_bain")]),
    S("L'armature du taud", ["cadre_taud"],
      ["Les 2 cadres : 2 tenons dans le plat-bord.",
       "Les 4 encoches du haut des rails reçoivent le toit à l'étape suivante."],
      tip="Le tenon avant d'un cadre est plus gros : impossible de le monter à l'envers."),
    S("Le toit et le pavillon", ["toit_taud", "mat_pavillon"],
      ["Le toit est d'une seule pièce, arceaux compris. Pose-le sur les 2 cadres : ses 8 pieds descendent dans les encoches des rails.",
       "Appuie au-dessus de chaque arceau : les bords du toit viennent contre l'extérieur des rails.",
       "Mât de pavillon : à travers le tapis n° 1 bâbord, jusque dans le plat-bord."],
      tip="Rien à coller : toute la maquette tient par emboîtement."),
    S("Les pare-battages", cols=2,
      tip="Ficelle tendue, le crochet reste droit : il ne se décroche qu'en le penchant vers la paroi. Une pince à épiler aide à le présenter.",
      subs=[sub("Noue un bout de ficelle fine (non fournie) dans l'œil de chaque pare-battage, et un crochet alu à l'autre bout. Passe la ficelle par-dessus le plat-bord, puis sous le coussin.",
                "pare_battage", W=640, H=900, cam=CAM_PB, k=1.0),
            sub("Accroche le crochet à l'anneau blanc : penche-le vers la paroi, bec sous la barrette et œil au-dessus, puis redresse-le. Pour enlever le pare-battage, fais l'inverse.",
                "crochet_pare_battage", W=640, H=900, cam=CAM_ANNEAU, k=1.0)]),
]
