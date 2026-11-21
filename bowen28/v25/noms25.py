# -*- coding: utf-8 -*-
"""Noms affiches des pieces (kit v25.1 sans colle)."""
NICE = {
    "coque_arriere": "coque arrière", "coque_avant": "coque avant", "capot_moteur": "capot moteur (blanc)",
    "jupe_moteur": "jupe arrière du moteur (blanche)", "flap": "flap", "verin_flap": "vérin de flap",
    "moyeu_volant": "moyeu du volant", "pompe_direction": "pompe de direction",
    "embase_moteur": "embase moteur (bas de capot gris)", "aileron_moteur": "aileron de moteur", "gaine_moteur": "gaine de commande",
    "fauteuil": "fauteuil", "bande_fauteuil": "bande blanche de fauteuil", "embase_fauteuil": "embase de fauteuil", "filet_caisson": "filet du caisson",
    "jante_volant": "jante du volant", "branches_volant": "croisillon du volant (branches doubles)", "manette_gaz": "manette des gaz double",
    "barre_console": "barre de console", "pare_brise": "pare-brise", "ecran_mfd": "écran multifonction",
    "ecran_tribord": "écran tribord", "interrupteurs": "tableau d'interrupteurs",
    "cadre_taud": "cadre du taud", "boitier_echelle_babord": "boîtier d'échelle bâbord",
    "boitier_echelle_tribord": "boîtier d'échelle tribord", "arceau_taud": "arceau du taud", "arceau_avant_taud": "arceau avant du taud",
    "pare_battage": "pare-battage", "crochet_pare_battage": "crochet de pare-battage", "echelle_bain": "échelle de bain repliée", "taquet": "taquet escamotable",
    "mat_pavillon": "mât de pavillon", "anneau_tableau": "anneau de tableau",
    "filet_noir_arriere": "filet noir arrière", "filet_noir_avant": "filet noir avant", "filet_noir_tableau": "bande noire du tableau",
    "seadeck_pointe_babord": "SeaDek pointe bâbord", "seadeck_pointe_tribord": "SeaDek pointe tribord",
    "seadeck_passage_arriere": "SeaDek passage arrière", "boudin_babord": "boudin rayé bâbord", "boudin_tribord": "boudin rayé tribord",
    "dos_dossier_arriere": "dos du dossier arrière",
    "berceau_arriere": "berceau arrière", "berceau_avant": "berceau avant", "taud_imprime_option": "taud imprimé (option)",
    "tissu_taud": "toile du taud (tissu)",
}

NICE.update({
    "toit_taud": "toit du taud (arceaux intégrés)",
    "cadre_taud": "cadre du taud",
    "cle_jonction_plat_bord": "clé de jonction de plat-bord",
    "cle_jonction_fond": "clé de jonction du plancher",
    "filet_noir_arriere_babord": "filet noir arrière bâbord", "filet_noir_arriere_tribord": "filet noir arrière tribord",
    "filet_noir_avant_babord": "filet noir avant bâbord", "filet_noir_avant_tribord": "filet noir avant tribord",
    "filet_noir_tableau_babord": "bande noire du tableau bâbord", "filet_noir_tableau_tribord": "bande noire du tableau tribord",
    "eprouvette_A": "éprouvette A (bloc à tenons)", "eprouvette_B": "éprouvette B (bloc à logements)",
    "eprouvette_C": "éprouvette C (plaquette)", "eprouvette_cle": "éprouvette : clé de jonction",
})


def nice(n):
    if n in NICE:
        return NICE[n]
    t = n
    for a, b in (("coussin_", "coussin "), ("bandes_", "bandes "), ("banquette_basse_", "banquette basse – "),
                 ("banquette_haute_", "banquette haute – "), ("siege_console_", "siège de console – "),
                 ("avant_assise_", "avant – assise "), ("avant_dossier_", "avant – dossier "), ("avant_retour_", "avant – retour "),
                 ("seadeck_plat_bord_", "tapis de plat-bord "), ("plat_bord_", "plat-bord "), ("babord", "bâbord"), ("_", " ")):
        t = t.replace(a, b)
    return t.replace("dossier avant", "dossier avant").strip()


