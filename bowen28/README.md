# Bowen 28 au 1:19 – kit d'impression v24, montage sans colle

`./construire.sh` reconstruit tout le kit (`./construire.sh --notice` ajoute la notice illustrée).
Résultat : `Bowen28_kit_impression_v24.zip` (91 pièces sur 9 plateaux + l'éprouvette P00, environ 765 g de PLA).

## Comment c'est construit

| Fichier | Rôle |
|---|---|
| `model.py` | La maquette elle-même : coque, pont, console, moteurs, taud, coussins… (cotes en mètres réels, échelle 1:19) |
| `fit.py`, `v25/fit25.py` | Les emboîtements : tenons ronds, tenons losange, logements, **jeu de 0,1 mm** (`C` dans `fit25.py`) |
| `pieces.py`, `cushions.py` | Découpe en pièces imprimables, orientation sur le plateau |
| `v25/s2_coques.py` | Les 2 moitiés de coque : clés de jonction, tenons losange, logements des pièces |
| `v25/s1_pieces.py` | Toutes les autres pièces (moteurs, volant, filets noirs, cadres…) |
| `v25/roof25.py` | Le toit rigide du taud, arceaux intégrés, imprimé à l'envers sans support |
| `v25/s4_coussins.py` | Les 20 coussins, recalés sur les coques |
| `v25/s3_assemblage.py` | La maquette assemblée, avec contrôle de tous les chevauchements |
| `v25/s5_eprouvette.py` | L'éprouvette de réglage P00 |
| `v25/s6_kit.py` … `s9_lisezmoi.py` | STL par couleur, plateaux 3MF, aperçus, fiche d'impression, LISEZMOI |
| `nf25_*.py` | La notice de montage (11 étapes, images et PDF) |
| `v25/s10_controle.py` | Le contrôle final du kit |

Données d'origine (ne pas modifier à la main) : `v23/v23b.pkl` (maquette assemblée v23), `v24/coques_soudees.pkl`
(coques v23 réparées), `v24/coque_coussins.pkl` (orientation d'impression des coussins), `donnees/eclate.json`
(vue éclatée de la notice), `fonts/` (polices DM Sans, DM Mono, Exo 2, Bricolage, licence libre OFL), `v24/nxlogo.svg`.

## Couleurs

Blanc (coques, capots, clés) · Gris alu (cadres, moteurs, échelle) · Noir (toit, filets, écrans) ·
Teck (SeaDek, volant) · Taupe (coussins, fauteuils). Bobines prévues : Bambu Lab ; équivalents chez
Caraïbes 3D Productions : PLA Basic Blanc, PLA+ Gris, PLA Basic Noir, PLA+ Beige, PLA+ Brun (Landu3D).
