"""Controle des chemins de pose (LIGNE_DE_CONDUITE.md, regle 1 : connecteurs accessibles).

On remonte la maquette dans l'ordre de la notice : chaque piece doit arriver en ligne droite, par le cote ou la
notice la fait poser, sans rien toucher en route (ni la piece qui la recoit, ni une piece deja posee). Les pieces
qu'on enfonce au doigt (les 4 cles de jonction) doivent en plus avoir 3 mm de degagement tout autour de leur chemin,
au-dessus d'elles. Le programme s'arrete si un chemin est bloque : le kit n'est pas fabrique.
Entree : v25b.pkl (maquette assemblee, repere visionneuse en mm : x vers l'avant, y vers le haut, z vers tribord).
"""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))   # dossier bowen28 du depot
import sys, pickle, collections
sys.path.insert(0, ROOT); sys.path.insert(0, _os.path.join(_os.path.dirname(ROOT), 'commun'))
import numpy as np
from manifold3d import Manifold, Mesh
import model as M
import nf25_steps as S
import montage as MT
from montage import Pose

A = pickle.load(open(ROOT + '/v25/v25b.pkl', 'rb'))
P = {k: Manifold(Mesh(np.asarray(V, np.float32), np.asarray(F, np.uint32))) for k, (V, F) in A.items()}
par_nom = collections.defaultdict(list)
for k in sorted(P):
    par_nom[k.split('__')[1]].append(k)

DESSUS, DESSOUS, AVANT, ARRIERE = (0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0)
def vis(d): return (d[0], d[2], -d[1])                      # repere bateau (z haut) -> visionneuse (y haut)
VOLANT = vis(M.WHEEL_N)                                       # axe du volant : pompe et volant arrivent par la
(x0, z0), (x1, z1) = M.DASH
TABLEAU = vis((-(z1 - z0), 0.0, x1 - x0))                    # normale du tableau de bord incline (ecran tribord)


def tous(nom, a, **kw):
    """Une pose par exemplaire de la piece."""
    assert par_nom[nom], nom
    return [Pose(k, a(k) if callable(a) else a, **kw) for k in par_nom[nom]]


def anneau(k):
    s = 1 if P[k].bounding_box()[2] < 0 else -1               # babord : z < 0
    return vis(M.eye_frame(s)[1])


def vers_axe(k):
    """Coussins de plat-bord : leurs nervures sont des dalles paralleles a l'axe transversal ; le coussin arrive
    de l'interieur du cockpit, droit vers la paroi."""
    return (0, 0, 1) if P[k].bounding_box()[2] < 0 else (0, 0, -1)


ORDRE = []
# 1. La coque : coque avant contre coque arriere, cles par le dessus, puis la coque sur ses berceaux
ORDRE += [Pose('blanc__coque_avant__0', AVANT)]
ORDRE += tous('cle_jonction_fond', DESSUS, doigt=True) + tous('cle_jonction_plat_bord', DESSUS, doigt=True)
ORDRE += tous('berceau_arriere', DESSOUS) + tous('berceau_avant', DESSOUS)
# 2. Les filets noirs
for seg in ('arriere', 'avant'):
    for c in ('babord', 'tribord'):
        ORDRE += tous(f'filet_noir_{seg}_{c}', None, hors="filet souple : il se plie dans sa rainure, tenon par tenon")
ORDRE += tous('filet_noir_tableau_babord', ARRIERE, cone=True) + tous('filet_noir_tableau_tribord', ARRIERE, cone=True)
ORDRE += tous('anneau_tableau', anneau, cone=True, doigt=True)
# 3. Le pont
for n in ('seadeck_pointe_babord', 'seadeck_pointe_tribord', 'seadeck_passage_arriere'):
    ORDRE += tous(n, DESSUS, cone=True)
for k in (1, 2, 3, 4):
    for c in ('babord', 'tribord'):
        ORDRE += tous(f'seadeck_plat_bord_{k}_{c}', DESSUS, cone=True)
ORDRE += tous('taquet', DESSUS, cone=True, doigt=True) + tous('boudin_babord', DESSUS, cone=True) + tous('boudin_tribord', DESSUS, cone=True)
# 4. La banquette arriere (dans l'ordre des numeros de la notice)
ORDRE += tous('coussin_banquette_basse_assise', DESSUS, cone=True) + tous('coussin_banquette_basse_dossier', AVANT, cone=True)
# dossier haut : il coiffe la planche du dossier, il ne peut venir que par le dessus (la notice dit « par l'avant »)
ORDRE += tous('coussin_banquette_haute_dossier', DESSUS, cone=True) + tous('coussin_banquette_haute_assise', DESSUS, cone=True)
ORDRE += tous('dos_dossier_arriere', ARRIERE, cone=True)
# 5. Le poste de pilotage : volant, manette et barre AVANT les fauteuils (le fauteuil babord barre l'axe du volant)
ORDRE += tous('filet_caisson', ARRIERE, cone=True)
VOL = par_nom['pompe_direction'] + par_nom['branches_volant'] + par_nom['jante_volant'] + par_nom['moyeu_volant']
ORDRE += [Pose(VOL, VOLANT)]                                  # volant monte sur la table, puis sur le tenon de la console
ORDRE += tous('manette_gaz', ARRIERE, cone=True) + tous('barre_console', ARRIERE, cone=True)
ORDRE += tous('embase_fauteuil', DESSUS, cone=True) + tous('fauteuil', DESSUS, cone=True)
ORDRE += tous('bande_fauteuil', None, hors="bande enfoncee dans la rainure du fauteuil en suivant sa courbe (assise puis dossier)")
# 6. La console et son siege
ORDRE += tous('ecran_mfd', DESSUS, cone=True) + tous('ecran_tribord', TABLEAU, cone=True, doigt=True) + tous('interrupteurs', ARRIERE, cone=True)
ORDRE += tous('coussin_siege_console_assise', DESSUS, cone=True) + tous('coussin_siege_console_dossier', AVANT, cone=True)
# 7. La banquette avant
for n in S.AV:
    ORDRE += tous(n, DESSUS, cone=True)
# 8. Les coussins de plat-bord
for k in (1, 2, 3):
    for n in S.PC(k):
        ORDRE += tous(n, vers_axe, cone=True)
# 9. Les moteurs (dans l'ordre de la notice) : chaque moteur est monte sur la table (v25.3 : embase sous le bloc gris,
#    helice sur la torpille, controle plus bas) puis pousse vers l'avant sur la chaise ; la cheville dans le bloc avant
#    le capot ; flap et verin pousses ensemble contre le tableau
MOTEURS = [[par_nom[n][i] for n in ('bloc_moteur', 'embase_moteur', 'helice')] for i in range(2)]
ORDRE += tous('gaine_moteur', ARRIERE, cone=True) + [Pose(m, ARRIERE, cone=True) for m in MOTEURS] + tous('jupe_moteur', ARRIERE, cone=True)
ORDRE += tous('cheville_capot', DESSUS, cone=True, doigt=True) + tous('capot_moteur', DESSUS, cone=True) + tous('aileron_moteur', ARRIERE, cone=True)
for i in range(2):
    ORDRE += [Pose([f'noir__verin_flap__{i}', f'alu__flap__{i}'], ARRIERE, cone=True)]
ORDRE += tous('echelle_bain', DESSUS, cone=True)
# 10-12. Le taud, le toit, le pavillon ; les pare-battages pendent contre le flanc, a une ficelle dont le crochet
#        (v25.2) s'accroche a l'anneau de la paroi : on les approche par l'exterieur
ORDRE += tous('cadre_taud', DESSUS, cone=True) + tous('toit_taud', DESSUS, cone=True) + tous('mat_pavillon', DESSUS, cone=True, doigt=True)
def dehors(k): return (0, 0, 1) if P[k].bounding_box()[5] > 0 else (0, 0, -1)
ORDRE += tous('pare_battage', dehors, cone=True)
# le crochet (v25.2) s'accroche a l'anneau en pivotant autour de sa barrette : pas de ligne droite, son chemin est
# cherche en 2D sur l'anneau imprime (pare_battages25.chemin_crochet) ; sans chemin, le programme s'arrete
import pare_battages25 as PBT
_ch = PBT.chemin_crochet()
if not _ch:
    sys.exit("crochet de pare-battage : aucun chemin pour l'accrocher a l'anneau")
print(f"crochet de pare-battage : s'accroche a l'anneau en pivotant de {max(a for a, _, _ in _ch):.0f} deg autour de la barrette (chemin 2D)")
ORDRE += tous('crochet_pare_battage', None, hors="s'accroche en pivotant autour de la barrette : chemin verifie en 2D ci-dessus")

# la notice et ce controle parlent des memes pieces, dans le meme ordre (etapes, et sous-etapes numerotees)
notice = {p for st in S.STEPS for p in st['parts']}
controle = {k.split('__')[1] for p in ORDRE for k in p.noms} | {'coque_arriere'}
assert notice == controle, (notice ^ controle)
rang = {}
for i, st in enumerate(S.STEPS):
    for j, sb in enumerate(st.get('subs') or [dict(parts=st['parts'])]):
        for n in sb['parts']:
            rang[n] = (i, j if st.get('order') else 0)
suite = [rang[k.split('__')[1]] for p in ORDRE for k in p.noms]
assert suite == sorted(suite), "l'ordre de ce controle ne suit plus celui de la notice (nf25_steps.py)"

print('chemins de pose : coque arriere en place, puis', len(ORDRE), 'poses dans l\'ordre de la notice')
defauts, hors, oublies = MT.controle_pose(P, ORDRE, base=["blanc__coque_arriere__0"], verbeux=("-v" in sys.argv))
# sous-ensemble monte sur la table : croisillon, jante et moyeu sur la pompe
d2, _, _ = MT.controle_pose({k: P[k] for k in VOL}, [Pose(par_nom[n], VOLANT) for n in ('branches_volant', 'jante_volant', 'moyeu_volant')],
                            base=par_nom['pompe_direction'], verbeux='-v' in sys.argv)
defauts += d2
# sous-ensembles montes sur la table : l'embase monte sous le bloc gris, l'helice arrive par l'arriere sur la torpille
for b, e, h in MOTEURS:
    d3, _, _ = MT.controle_pose({k: P[k] for k in (b, e, h)}, [Pose(e, DESSOUS), Pose(h, ARRIERE)], base=[b], verbeux='-v' in sys.argv)
    defauts += d3
for noms, raison in hors:
    print('  non controle :', ', '.join(noms), '-', raison)
if oublies:
    defauts.append((oublies, None, 0, 0, 'pieces absentes de l\'ordre de pose'))
print('chemins de pose bloques :', len(defauts))
for d in defauts:
    print('  BLOQUE', d)
if defauts:
    sys.exit(1)
