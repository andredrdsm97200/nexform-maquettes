"""Artefact de vision 3D du Bowen 28 : a faire valider par Andre AVANT le kit d'impression, la notice et la marina
(consigne du projet du 25 novembre 2026).

  - page : vision3d.html (la visionneuse de l'Elliott 52 : vues, vue eclatee, socle, fiche d'une piece au toucher,
    carnet de demandes de modification et bouton de validation dans la base de l'artefact ; sans option de voiles) ;
  - modele : sorties/vision3d/m/bowen28.json, tire de la maquette assemblee (v25/v25b.pkl, repere de la
    visionneuse : mm, y vers le haut, z vers tribord) ; sommets quantifies sur 16 bits, indices sur 16 ou 32 bits, en
    base64, a pleine resolution (allegee, la coque arriere se creusait a la jonction des 2 coques et laissait voir le
    boudin) ; ecarts de la vue eclatee repris de la notice.
Usage : apres ./construire.sh, python3 bowen28/vision3d.py, puis publier le dossier sorties/vision3d (index.html et
m/bowen28.json) dans l'artefact, avec la capacite db.
"""
import os
import sys
import json
import base64
import pickle
import datetime
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/v25')
from noms25 import nice

OUT = ROOT + '/sorties/vision3d'
VERSION, VERSION_ID = 'v25.4', 'v25_4'
ALLEGER = {}             # part des faces retirees par piece : aucune (la vue doit montrer la maquette telle qu'imprimee)
COULEURS = {
    'blanc': {'nom': 'Blanc cassé', 'hex': '#F2EFE6', 'rendu': '#EDEAE2', 'rugosite': 0.65},
    'alu': {'nom': 'Gris alu', 'hex': '#B8BEC4', 'rendu': '#AEB5BC', 'rugosite': 0.4},
    'noir': {'nom': 'Noir', 'hex': '#26272B', 'rendu': '#26272B', 'rugosite': 0.5},
    'teck': {'nom': 'Teck', 'hex': '#C29A6A', 'rendu': '#B88F5F', 'rugosite': 0.7},
    'taupe': {'nom': 'Taupe', 'hex': '#8C7A6B', 'rendu': '#857364', 'rugosite': 0.8},
}
OFFS = json.load(open(ROOT + '/donnees/eclate.json'))
LETTRES = '#6A6E76'      # teinte d'affichage des lettres du socle : imprimees, elles sont noires comme lui (relief de 0,8 mm)
VUES = [['3/4 avant', [1, 0.42, 0.95]], ['Profil', [0, 0.05, 1]], ['Dessus', [-0.02, 1, 0]], ['Arrière', [-1, 0.5, -0.85]],
        ['Nom', [0.0, 0.22, 1.0], ['socle']]]   # le flanc tribord du socle, de face : le nom et le logo de pres


def ecart(n, V):
    """Ecart de la vue eclatee (mm, repere visionneuse), comme dans la notice ; le socle descend."""
    col, name, k = n.split('__')
    z = 1.0 if np.asarray(V)[:, 2].mean() > 0 else -1.0
    if name == 'socle': return [0.0, -40.0, 0.0]
    if name in ('bloc_moteur', 'embase_moteur', 'helice', 'cheville_capot'):
        base = np.array(OFFS.get(f'alu__embase_moteur__{k}', [-70.0, 0.0, 0.0]), float)
        return list(base + {'bloc_moteur': (0, 0, 0), 'embase_moteur': (0, -14, 0), 'helice': (-18, -14, 0), 'cheville_capot': (0, 14, 0)}[name])
    if name == 'pare_battage': return [0.0, 4.0, 12.0 * z]
    if name == 'crochet_pare_battage': return [0.0, 2.0, -7.0 * z]
    if n in OFFS: return OFFS[n]
    for seg in ('arriere', 'avant', 'tableau'):
        for j, sd in enumerate(('babord', 'tribord')):
            if name == f'filet_noir_{seg}_{sd}': return OFFS.get(f'noir__filet_noir_{seg}__{j}', [0, 0, 0])
    if name.startswith('cle_jonction'): return [0, 26, 0]
    if name == 'toit_taud': return OFFS.get('toile__tissu_taud__0', [0, 70, 0])
    return [0.0, 0.0, 0.0]


def alleger(V, F, part):
    import fast_simplification
    v, f = fast_simplification.simplify(np.asarray(V, np.float32), np.asarray(F, np.int64), target_reduction=part)
    return v, f


def lettres_du_socle(V, F):
    """Faces des lettres en relief du socle (dessus et bords des lettres, sur les 2 flancs de la poutre) : masque."""
    import model as M
    import socle25 as SO
    c = V[F].mean(1)                                            # centres des faces, repere visionneuse (mm)
    P = np.c_[c[:, 0], -c[:, 2], c[:, 1]] / M.MM                # -> repere bateau (m)
    larg = SO.lettrage()[1]
    m = np.zeros(len(F), bool)
    for s in (-1, 1):
        T, ls = SO.flanc(s)
        T = np.asarray(T)
        t = (P - T[:, 3]) @ (T[:, :3] * M.MM) * M.MM            # (le long, en montant, vers l'exterieur) en mm
        m |= (np.abs(t[:, 0]) < larg / 2 + 1) & (np.abs(t[:, 1]) < ls / 2) & (t[:, 2] > 0.05) & (t[:, 2] < SO.RELIEF + 0.05)
    return m


def compacter(V, F):
    u, inv = np.unique(F.ravel(), return_inverse=True)
    return V[u], inv.reshape(F.shape)


def modele(D):
    """Le modele au format de la visionneuse : {o, s, g: [{id, nm, k, e, p, i, b (, r, sub)}]}."""
    allV = np.concatenate([np.asarray(V, float) for V, F in D.values()])
    o = allV.min(0); s = float((allV.max(0) - o).max()) / 65535.0
    g, nf = [], 0

    def groupe(gid, nm, col, e, V, F, **extra):
        q = np.clip(np.round((V - o) / s), 0, 65535).astype('<u2')
        b = len(V) > 65535
        g.append(dict(id=gid, nm=nm, k=col, e=e, p=base64.b64encode(q.tobytes()).decode(),
                      i=base64.b64encode(F.astype('<u4' if b else '<u2').tobytes()).decode(), b=b, **extra))

    for n, (V, F) in D.items():
        col, name, k = n.split('__')
        V, F = np.asarray(V, float), np.asarray(F)
        if name in ALLEGER: V, F = alleger(V, F, ALLEGER[name])
        e = [round(float(x), 2) for x in ecart(n, V)]
        if name == 'socle':
            # les lettres a part, eclaircies a l'ecran pour etre lisibles (le socle reste une seule piece)
            lt = lettres_du_socle(V, F)
            assert 1000 < lt.sum() < len(F) - 100, f'lettres du socle introuvables ({lt.sum()} faces sur {len(F)})'
            groupe(f'{name}_{k}', nice(name), col, e, *compacter(V, F[~lt]))
            groupe(f'{name}_{k}_lettres', nice(name), col, e, *compacter(V, F[lt]), r=LETTRES, sub=True)
        else:
            groupe(f'{name}_{k}', nice(name), col, e, V, F)
        nf += len(F)
    return dict(o=[round(float(x), 4) for x in o], s=s, g=g), nf, allV


def config(n_pieces, n_couleurs, allV):
    ext = allV.max(0) - allV.min(0)
    date = datetime.date.today().strftime('%d/%m/%Y')
    return {
        "titre": "Bowen 28 · KANPAÏ 2.O", "sous_titre": "Center console de 8,50 m · maquette au 1:19",
        "statut": f"À valider · {VERSION}", "version": f"Version 25.4 ({date})", "version_id": VERSION_ID,
        "modele": "m/bowen28.json", "socle": ["socle"], "eclate": 1.0, "vues": VUES,
        "exemple": "Par exemple : un jour entre deux pièces, une couleur à changer, une pièce à déplacer…",
        "couleurs": COULEURS,
        "chiffres": [["1:19", "échelle de la maquette"], [f"{ext[0] / 10:.0f} cm".replace('.', ','), "de long, moteurs compris"],
                     [f"{ext[1] / 10:.0f} cm".replace('.', ','), "de haut, sur son socle"], [str(n_pieces), f"pièces, en {n_couleurs} couleurs"]],
        "points": [
            {"t": "Coussins de plat-bord ajustés à la paroi", "d": "Leur face côté coque suit maintenant la courbe du cockpit, à 0,1 mm, des 2 côtés : plus de jour entre le coussin 3 et la coque (jusqu'à 1,7 mm avant). La coque ne change pas ; les 6 coussins de plat-bord s'impriment debout, sans support."},
            {"t": "SeaDek en taupe", "d": "Les 11 tapis SeaDek (pointe avant, plats-bords, passage arrière) passent en taupe, comme les coussins. Le volant reste en teck."},
            {"t": "Socle validé : KANPAÏ 2.O", "d": "Avec la lettre O, comme tu l'écris (dans la police Nexform, le O et le zéro se ressemblent presque). Fichier d'impression P10 envoyé le 26 novembre. Bouton « Nom » pour le voir de près."},
            {"t": "Lettres en relief, sur les 2 flancs", "d": "0,8 mm de relief, sur les flancs inclinés de la poutre ; chacun se lit de gauche à droite. Imprimées, elles sont noires comme le socle et ressortent par la lumière ; à l'écran, elles sont éclaircies pour qu'on les lise."},
        ],
        "changements": {"titre": "Ce qui change en v25.4", "items": [
            {"t": "Socle d'un seul morceau", "d": "Les 2 berceaux gris deviennent un socle noir d'une pièce : ils sont reliés par une poutre qui passe 6 mm sous la quille."},
            {"t": "KANPAÏ 2.O et Nexform 3D Marine", "d": "Le nom du bateau et le logo Nexform en relief, sur chaque flanc de la poutre."},
            {"t": "SeaDek en taupe", "d": "Les tapis SeaDek quittent le teck pour le taupe des coussins."},
            {"t": "Coussins de plat-bord ajustés à la paroi", "d": "Ils suivent la paroi courbe du cockpit au jeu de 0,1 mm, des 2 côtés, et s'impriment debout."},
        ]},
        "pied": ["Programme : dépôt nexform-maquettes, dossier bowen28 (socle : v25/socle25.py).",
                 "Les fichiers d'impression, la notice de montage et la place dans la marina Nexform viennent après la validation de cette version.",
                 "Nexform 3D Marine."],
    }


if __name__ == '__main__':
    D = pickle.load(open(ROOT + '/v25/v25b.pkl', 'rb'))
    m, nf, allV = modele(D)
    os.makedirs(OUT + '/m', exist_ok=True)
    json.dump(m, open(OUT + '/m/bowen28.json', 'w'), separators=(',', ':'))
    cfg = config(len(D), len({n.split('__')[0] for n in D}), allV)
    page = open(ROOT + '/vision3d.html', encoding='utf-8').read()
    page = page.replace('__CFG__', json.dumps(cfg, ensure_ascii=False).replace('<', '\\u003c')).replace('__TITRE__', cfg['titre']).replace('__EXEMPLE__', cfg['exemple'])
    open(OUT + '/index.html', 'w', encoding='utf-8').write(page)
    print(f"vision 3D : {len(D)} pieces, {nf} faces, modele {os.path.getsize(OUT + '/m/bowen28.json') / 1e6:.1f} Mo -> {OUT}")
