# Nexform 3D Marine – maquettes de bateaux

Le programme qui fabrique les maquettes Nexform. Un dossier par bateau. Tout ce qu'il faut pour
reconstruire un kit d'impression, le modifier ou partir d'une maquette existante pour en créer une autre.

| Maquette | Dossier | Contenu |
|---|---|---|
| Bowen 28 au 1:19 (507 mm) | [`bowen28/`](bowen28/) | Programme complet. Kit d'impression **v24, montage sans colle**, reconstruit en une commande |
| Boston Whaler 17 Montauk au 1:12 | [`whaler17/`](whaler17/) | Programme du modèle du BAT v2 (affiché dans la vitrine Nexform) |
| Sunfish 25 cm (1:16,8) | [`sunfish/`](sunfish/) | Les 19 pièces finales de la version 3 (STL) et leurs notes ; programme d'origine à reconstituer |

## Le plus simple : demander à Claude

Dans le projet Claude « Nexform », ouvrez une discussion et écrivez par exemple :

- « Reprends le dépôt nexform-maquettes et modifie le Bowen : … »
- « Reconstruis le kit d'impression du Bowen. »
- « Nouvelle maquette dans nexform-maquettes : un … de … cm. Voici des photos. »

Claude récupère le dépôt, modifie le programme, reconstruit et vérifie le kit, puis enregistre la
nouvelle version ici. Rien ne se perd d'une discussion à l'autre.

## Reconstruire un kit soi-même (sur un ordinateur)

1. Installer Python 3.11 ou plus récent.
2. Dans ce dossier : `pip install -r requirements.txt`
3. `./bowen28/construire.sh` (quelques minutes), ou `./bowen28/construire.sh --notice` pour la notice
   illustrée en plus (30 à 40 minutes).

Résultat : `bowen28/Bowen28_kit_impression_v24.zip`, le même kit que celui envoyé à l'imprimeur
(fichiers identiques au bit près).

## Les règles de la maison

- **Montage sans colle**, en PLA ou PLA+ : 0,1 mm de jeu partout. Tenon rond quand il s'imprime debout,
  tenon en losange quand il s'imprime couché ; clés de jonction en forme d'os entre deux moitiés de coque ;
  une éprouvette de réglage à imprimer en premier.
- **Imprimante de référence** : Bambu Lab A1, plateau 256 × 256 mm. Une couleur par plateau, pièces à 5 mm
  les unes des autres et à 8 mm du bord.
- **Chaque kit** : STL rangés par couleur, plateaux 3MF prêts à imprimer, fiche d'impression, LISEZMOI,
  notice de montage, contrôle automatique (pièces étanches, aucun chevauchement dans la maquette assemblée).
- **Clients** : rien ne leur est envoyé sans validation ; ils voient le modèle 3D, jamais les fichiers sources ;
  pas de logos ni de décors de marques.
- Les photos des clients ne sont pas mises dans ce dépôt.

## Ajouter une nouvelle maquette

Un nouveau dossier par bateau, avec son programme, ses données, un `construire.sh` et un `README.md`.
Les fichiers recalculés (kits, images, fichiers intermédiaires) ne sont pas enregistrés : voir `.gitignore`.
