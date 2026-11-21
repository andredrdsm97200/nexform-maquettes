# Bowen 28 au 1:19 – kit d'impression v25.2, montage sans colle

`./construire.sh` reconstruit tout le kit (`./construire.sh --notice` ajoute la notice illustrée).
Résultat : `Bowen28_kit_impression_v25.2.zip` (99 pièces sur 9 plateaux + l'éprouvette P00, environ 765 g de PLA).

## Comment c'est construit

| Fichier | Rôle |
|---|---|
| `model.py` | La maquette elle-même : coque, pont, console, moteurs, taud, coussins… (cotes en mètres réels, échelle 1:19) |
| `fit.py`, `v25/fit25.py` | Les emboîtements : tenons ronds, tenons losange, logements, **jeu de 0,1 mm** (`C` dans `fit25.py`) ; côtes d'écrasement des petites pièces : `../commun/emboitements.py` |
| `pieces.py`, `cushions.py` | Découpe en pièces imprimables, orientation sur le plateau |
| `v25/s2_coques.py` | Les 2 moitiés de coque : clés de jonction, tenons losange, logements des pièces |
| `v25/s1_pieces.py` | Toutes les autres pièces (moteurs, volant, filets noirs, cadres…) |
| `v25/roof25.py` | Le toit rigide du taud, arceaux intégrés, imprimé à l'envers sans support |
| `v25/poste25.py` | v25 : le caisson des fauteuils (25 mm, à 23 mm de la console) ; change les cotes de `model.py` pour toute la chaîne |
| `v25/echelle25.py` | v25 : l'échelle de bain repliée, tournée de 90°, et la tôle larmée refaite dessous |
| `v25/pare_battages25.py` | v25 : les 4 pare-battages (œil pour la ficelle), leurs 4 anneaux encastrés dans les parois du cockpit et (v25.2) leurs 4 crochets alu |
| `v25/s4_coussins.py` | Les 20 coussins, recalés sur les coques |
| `v25/s3_assemblage.py` | La maquette assemblée, avec contrôle de tous les chevauchements |
| `v25/s3b_chemins.py` | Les chemins de pose ([ligne de conduite](../LIGNE_DE_CONDUITE.md), règle 1) : chaque pièce se pose sans obstacle, dans l'ordre de la notice |
| `v25/s3c_maintien.py` | Le maintien (règle 2) : les petites pièces accrochées à la console tiennent par leurs côtes d'écrasement |
| `v25/s5_eprouvette.py` | L'éprouvette de réglage P00 |
| `v25/s6_kit.py` … `s9_lisezmoi.py` | STL par couleur, plateaux 3MF, aperçus, fiche d'impression, LISEZMOI |
| `nf25_*.py` | La notice de montage (12 étapes, images et PDF) |
| `v25/s10_controle.py` | Le contrôle final du kit |

Données d'origine (ne pas modifier à la main) : `v23/v23b.pkl` (maquette assemblée v23), `v24/coques_soudees.pkl`
(coques v23 réparées), `v24/coque_coussins.pkl` (orientation d'impression des coussins), `donnees/eclate.json`
(vue éclatée de la notice), `fonts/` (polices DM Sans, DM Mono, Exo 2, Bricolage, licence libre OFL), `v24/nxlogo.svg`.

## Couleurs

Blanc (coques, capots, clés) · Gris alu (cadres, moteurs, échelle) · Noir (toit, filets, écrans, pare-battages) ·
Teck (SeaDek, volant) · Taupe (coussins, fauteuils). Bobines prévues : Bambu Lab ; équivalents chez
Caraïbes 3D Productions : PLA Basic Blanc, PLA+ Gris, PLA Basic Noir, PLA+ Beige, PLA+ Brun (Landu3D).
