# Ligne de conduite – maquettes Nexform

Les règles tirées des tests d'impression d'André. Elles valent pour **toutes les maquettes**, celles qui existent
et les nouvelles. Chaque règle dit ce qui a été constaté, ce qu'il faut faire et comment c'est vérifié.

Pour toute maquette, qu'on la modifie ou qu'on la crée :

- lire ces règles avant de toucher au programme ;
- brancher les contrôles communs (dossier [`commun/`](commun/)) dans le `construire.sh` du bateau ;
- une règle qui se mesure est vérifiée à chaque construction : si elle n'est pas respectée, le programme
  s'arrête et le kit n'est pas fabriqué ;
- ajouter ici chaque nouvelle règle validée par André, avec sa date et le test qui l'a fait naître.

## Règle 1 – Chaque connecteur est accessible

*20 novembre 2026, test d'impression du Bowen 28 (kit v24).* Les 2 clés de jonction du plancher passaient sous
l'avant du siège de console. Le siège, imprimé avec la coque, couvrait environ un quart de leur tête arrière :
impossible de les enfoncer.

**La règle**

- Chaque pièce se pose en ligne droite, dans l'ordre de la notice, par le côté où la notice la fait poser,
  sans rien toucher en route : ni la pièce qui la reçoit, ni une pièce déjà posée.
- Elle doit pouvoir reculer de sa propre hauteur (mesurée dans le sens de la pose) + 1 mm sans obstacle : c'est
  la place qu'il faut pour la présenter au-dessus de son logement, puis l'enfoncer. À défaut, elle doit au moins
  pouvoir reculer jusqu'à être sortie de tous ses emboîtements, + 1 mm.
- Une pièce qu'on enfonce au doigt (clés de jonction, taquets, anneaux, petits écrans, mât…) a en plus une
  cheminée vide au-dessus d'elle : son contour élargi de 3 mm, de 2 mm à 25 mm au-dessus de son dessus.
- Un logement ne passe jamais sous une autre partie de la pièce qui le porte (siège, banquette, plat-bord,
  console…) : on déplace le connecteur, on ne creuse pas dessous.
- L'ordre de la notice fait partie de la règle : si une pièce posée barre le chemin d'une autre, on change
  l'ordre de la notice.

**Vérifié par** `commun/montage.py` (fonction `controle_pose`), que chaque bateau appelle avec la liste de ses
pièces, leur direction de pose et l'ordre de sa notice. Pour le Bowen 28 : `bowen28/v25/s3b_chemins.py`, qui
doit afficher « chemins de pose bloques : 0 » ; ce script vérifie aussi qu'il suit bien l'ordre de la notice.
Seules les pièces qui se plient pendant la pose (filets souples, bandes de fauteuil) ne sont pas contrôlées, et
la raison est écrite à côté.

Le jeu des emboîtements n'est pas l'affaire de ce contrôle (c'est la règle du jeu de 0,1 mm). Un frottement
de moins de 0,1 mm (coussin enfilé sans jeu sur ses nervures), ou moins de 0,5 mm³ touché sur tout le chemin,
ne bloque pas.

**Appliqué au Bowen 28** : clés du plancher déplacées de part et d'autre du siège (z = ±31 mm au lieu de
±22 mm ; logement de 9,5 mm pour garder 2,6 mm de coque dessous) ; dans la notice, le volant se pose avant les
fauteuils (le fauteuil bâbord barrait son axe) ; les anneaux de pare-battage (v25) sont encastrés dans la paroi :
en saillie, ils barraient la descente des boudins sur leurs tenons. Le crochet de pare-battage (v25.2) s'accroche en
pivotant autour de la barrette de l'anneau : pas de ligne droite possible, son chemin est cherché en 2D
(`chemin_crochet` dans `pare_battages25.py`, appelé par `s3b_chemins.py`). Moteurs en 3 pièces (v25.3) : chaque moteur
se monte sur la table (embase par-dessous, hélice par l'arrière), contrôlé comme le volant, puis se pousse sur la chaise.

## Règle 2 – Une petite pièce ne tombe pas toute seule

*20 novembre 2026, test d'impression du Bowen 28 (kit v24).* Une des petites pièces de la console ne restait pas
en place : le trou paraissait trop large. Ces pièces ne tenaient que par le jeu standard de 0,1 mm, qui ne serre que
si l'imprimante et le filament sont parfaitement réglés (l'éprouvette P00 est imprimée en blanc, elles en noir).
Trois empreintes avaient même gardé l'ancien jeu de 0,15 à 0,2 mm.

**La règle**

- Une pièce que son propre poids ne tient pas (accrochée à une paroi, debout sur un seul tenon, penchée) reçoit
  des côtes d'écrasement sur son emboîtement : de fines nervures de 0,7 mm de large, dans le sens de la pose, qui
  serrent de 0,15 mm (0,08 mm pour un mini-tenon de 1,4 mm) et s'écrasent un peu quand on enfonce la pièce. Elle
  tient alors par serrage, quels que soient l'imprimante et le filament, sans colle.
- Les côtes vont toujours sur la petite pièce (son tenon, son trou ou les flancs de sa semelle) : si le serrage
  ne convient pas, on ne réimprime qu'elle. Elles commencent après l'entrée du logement : la pièce s'engage d'abord
  sans forcer.
- Une empreinte plus large que le jeu standard, héritée d'une ancienne version, se rattrape en grossissant la
  petite pièce, jamais en refaisant la coque.
- Une pièce que son poids tient (coussins, tuiles, taquets, moyeu du volant…) n'a pas de côtes : inutile de la
  durcir. Les côtes restent cachées dans l'emboîtement : l'aspect de la maquette ne change pas.

**Vérifié par** `commun/montage.py` (fonction `controle_maintien`), les côtes étant dessinées par
`commun/emboitements.py`. Pour chaque pièce concernée, la pièce imprimée, côtes comprises, posée à sa place, doit
toucher la pièce d'en face (serrage de 0,05 à 5 mm³) ; sans ses côtes, elle n'a pas plus de 0,16 mm de jeu de côté
(vers le bas, son poids la tient). La maquette assemblée garde les pièces sans côtes : elles ne comptent pas comme
des chevauchements. Pour le Bowen 28 : `bowen28/v25/s3c_maintien.py`, qui doit afficher « pieces mal tenues : 0 ».

**Appliqué au Bowen 28** : grand écran (semelle +0,1 mm par côté, 3 côtes dans son trou), petit écran (+0,1 mm
par côté, une côte par flanc), tableau d'interrupteurs (+0,1 mm par côté, 6 côtes sur ses flancs), manette des gaz
(4 côtes sur son tenon losange), pompe du volant (4 côtes dans son logement, 3 sur son tenon avant), barre de
console (3 côtes par patte). Sur une maquette déjà imprimée, il suffit de réimprimer ces 6 pièces. Moteurs en 3 pièces
(v25.3) : l'embase pend sous le bloc gris (3 côtes dans chacun de ses 2 logements), l'hélice tient sur un tenon
losange horizontal (4 côtes dans son logement).
