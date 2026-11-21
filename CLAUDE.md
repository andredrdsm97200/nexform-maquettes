# Consignes pour Claude – dépôt nexform-maquettes

Propriétaire : André, Nexform 3D Marine (Martinique). Lui répondre en français, en le tutoyant.
Les textes de l'Atelier Nexform réservés au propriétaire le tutoient.

## Le principe

Ce dépôt est la source unique du programme des maquettes : **on fabrique ici, on regarde dans Nexform**
(Atelier « Nexform 3D Marine » : https://claude.ai/artifact/FnKuZfor6XjY6fRcNLKVUq). Toujours partir du
programme existant, jamais de zéro. Lire `README.md`, puis le `README.md` du bateau concerné.

**Ligne de conduite** : avant de modifier ou de créer une maquette, lire `LIGNE_DE_CONDUITE.md` (les règles
tirées des tests d'impression d'André) et l'appliquer, à la maquette demandée comme à toute nouvelle maquette.
Chaque remarque d'André validée après un test devient une règle de ce fichier, avec son contrôle automatique
quand elle se mesure.

## Construire et vérifier

- Python 3.11+ (testé en 3.13). Module manquant : `pip install --break-system-packages -r requirements.txt`.
  Garder trimesh 5.2.1 : le kit sort alors identique au fichier près d'une construction à l'autre.
- Bowen 28 : `./bowen28/construire.sh` (environ 1 min) → `bowen28/Bowen28_kit_impression_v25.2.zip`.
  `--notice` ajoute la notice illustrée (30 à 40 min : lancer en arrière-plan).
- Whaler 17 : `python3 whaler17/build.py` → `whaler17/sorties/whaler.json` (format de la vitrine Nexform).
- Sunfish : seulement les pièces finales v3 (`sunfish/pieces_v3/`) ; le programme est à reconstituer
  (voir `sunfish/README.md`).
- Avant de livrer, dans la sortie de `construire.sh` : `s3_assemblage.py` doit afficher
  « interferences > 0,02 mm3 : 0 » (aucun chevauchement dans la maquette assemblée), `s3b_chemins.py`
  « chemins de pose bloques : 0 » (ligne de conduite, règle 1 : chaque pièce se pose sans obstacle dans l'ordre
  de la notice ; sinon le programme s'arrête), `s3c_maintien.py` « pieces mal tenues : 0 » (règle 2 : les petites
  pièces accrochées tiennent par leurs côtes d'écrasement) et `s10_controle.py` « ERREURS : aucune » (pièces étanches d'un
  seul tenant, plateaux 256 mm avec 8 mm de marge et 5 mm entre pièces, aucune mention de colle). Regarder les
  aperçus des plateaux et des pièces modifiées avant d'annoncer un résultat.
- Ordre ou texte de la notice modifié (`nf25_steps.py`) : garder `v25/s3b_chemins.py` dans le même ordre (il le
  vérifie) et reconstruire la notice (`--notice`) avant de livrer.
- Nouvelle maquette : brancher les contrôles communs de `commun/` dans son `construire.sh` (règle 1 : la direction
  de pose de chaque pièce et l'ordre de sa notice, comme `bowen28/v25/s3b_chemins.py` ; règle 2 : la liste des
  pièces que leur poids ne tient pas, comme `bowen28/v25/s3c_maintien.py`).
- `bowen28/v25/` est la chaîne de fabrication actuelle ; le kit qu'elle produit s'appelle « v25.2 » côté client.
  Nouvelle version livrée : changer le numéro là où il nomme le kit livré (nom du zip, du dossier du kit et de la
  notice, titres, date de la fiche) : `construire.sh`, `nf25_pdf.py`, `nf25_steps.py`, `v25/s6_kit.py` à
  `v25/s10_controle.py`, `v25/kit_inputs.py`, `v25/noms25.py`. Ne pas remplacer à l'aveugle : les commentaires qui
  racontent l'historique (« en v24… ») et les noms comme `zone_v24` ou `V24_PLAT_X` restent ; les chemins vers
  `bowen28/v24/` (données d'origine) ne bougent jamais. Ajouter au LISEZMOI (`s9_lisezmoi.py`) la rubrique
  « ce qui change » et vider `bowen28/nf25/img/` avant `--notice` (les images y sont en cache ; si seules des
  pièces de la dernière étape changent, effacer seulement `cover.png`, `fin.png`, les images de cette étape et
  les vignettes `t_*.png` des pièces touchées).

## Les règles de fabrication

- Montage sans colle, PLA ou PLA+, accessible à tous : jeu `C = 0,10 mm` par côté (`v25/fit25.py`). Une pièce que
  son poids ne tient pas reçoit en plus des côtes d'écrasement, côté petite pièce (`commun/emboitements.py`, règle 2).
  Tenon rond si la pièce s'imprime debout, tenon losange (carré à 45°) si elle s'imprime couchée,
  clés en os pour joindre deux pièces de coque, éprouvette P00 à imprimer en premier.
- Bambu Lab A1 : plateau 256 × 256 mm, une couleur par plateau, 5 mm entre pièces, 8 mm au bord, sans supports
  autant que possible.
- Un kit = STL par couleur, plateaux 3MF, fiche d'impression PDF, LISEZMOI, notice de montage, contrôle.

## Enregistrer

- Après chaque modification validée : `git commit` sur `main` avec un message clair en français, puis `git push`.
- Les fichiers recalculés ne sont pas versionnés (`.gitignore`) : livrer le zip et les PDF à André comme fichiers.
- Jamais dans le dépôt : photos de clients, adresses e-mail, numéros de téléphone, logos ou décors de marques.
  Fichiers de données sous 50 Mo.

## Clients

Rien n'est envoyé à un client et la vitrine Nexform n'est mise à jour qu'après validation d'André.
Les clients voient le modèle 3D, jamais les fichiers sources.
