# -*- coding: utf-8 -*-
"""Controles de montage communs a toutes les maquettes Nexform (voir LIGNE_DE_CONDUITE.md, regle 1).

Regle 1 - connecteurs accessibles. On remonte la maquette piece par piece, dans l'ordre de la notice ; chaque piece
arrive en ligne droite, par le cote ou la notice la fait poser (direction 'a' : le cote d'ou elle vient ; une cle
enfoncee par le dessus a a = vers le haut). Une pose est bonne si :
  1. la piece peut reculer en ligne droite de sa propre hauteur (mesuree dans le sens de la pose) + 1 mm sans rien
     toucher : c'est la place qu'il faut pour la presenter au-dessus de son logement puis l'enfoncer ;
     a defaut, elle peut au moins reculer jusqu'a etre sortie de tous ses emboitements, + 1 mm ;
  2. si on l'enfonce au doigt (cles de jonction...), la cheminee au-dessus d'elle est vide : son contour elargi de
     MARGE_DOIGT, de DEPART_MARGE a HAUTEUR_DOIGT au-dessus de son dessus.
'Rien toucher' : ni la piece qui la recoit, ni une piece deja posee. Le jeu des emboitements n'est pas l'affaire de ce
controle (regle C = 0,1 mm) : un frottement de moins de FROTTEMENT de cote (coussin enfile sans jeu sur ses
nervures) et moins de SEUIL_CHEMIN touche sur tout le chemin sont toleres.

Unites : mm. Les pieces sont des Manifold (manifold3d) dans le repere de la maquette assemblee.
Usage : voir bowen28/v25/s3b_chemins.py.
"""
import math
import numpy as np
from manifold3d import Manifold, CrossSection, OpType, JoinType

MARGE_DOIGT = 3.0     # mm : la cheminee du doigt deborde de 3 mm tout autour de la piece
DEPART_MARGE = 2.0    # mm : elle commence 2 mm au-dessus de la piece (bords de logement, marches de tapis toleres)
HAUTEUR_DOIGT = 25.0  # mm : et monte jusqu'a 25 mm au-dessus (la place du bout du doigt)
COURSE_PLUS = 1.0     # mm : recul demande au-dela de la hauteur de la piece, ou de la sortie de ses emboitements
JEU_TEST = 0.6        # mm : une piece est sortie de ses emboitements quand elle peut bouger de 0,6 mm de cote
FROTTEMENT = 0.1      # mm : un frottement de moins de 0,1 mm (ajustement serre, coussin enfile) ne bloque pas
SEUIL_CHEMIN = 0.5    # mm3 : en mouvement, moins d'un demi-millimetre cube touche sur tout le chemin ne bloque pas
SEUIL = 0.02          # mm3 : meme seuil que le controle des chevauchements
PAS = 0.25            # mm : finesse du balayage (tranches)
CONE = (5.0, 10.0, 15.0)   # degres : directions essayees autour d'une direction annoncee approximative


class Pose:
    """Une piece (ou un groupe de pieces posees ensemble) dans l'ordre de la notice.

    noms  : noms des pieces de l'assemblage qui bougent ensemble (ex. ['blanc__cle_jonction_fond__0'])
    a     : direction d'arrivee (3 nombres, repere de la maquette)
    doigt : True si on l'enfonce au doigt : cheminee libre exigee au-dessus d'elle
    cone  : True si la direction annoncee est approximative (piece posee sur une surface inclinee...) : on cherche
            aussi une direction qui passe dans un cone de 15 degres autour
    hors  : raison pour laquelle la piece n'est pas controlee (piece souple...) ; None sinon
    """
    def __init__(self, noms, a=None, doigt=False, cone=False, hors=None):
        self.noms = [noms] if isinstance(noms, str) else list(noms)
        self.a = None if a is None else np.asarray(a, float) / np.linalg.norm(a)
        self.doigt, self.cone, self.hors = doigt, cone, hors


def _rot(a):
    """Matrice 3x4 (rotation pure) qui amene la direction a sur +Z."""
    a = np.asarray(a, float); a = a / np.linalg.norm(a)
    t = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(t, a); u /= np.linalg.norm(u)
    v = np.cross(a, u)
    return np.c_[np.array([u, v, a]), np.zeros(3)]


def _bbox_rot(bb, R):
    """Boite englobante (conservative) d'une boite apres rotation."""
    lo, hi = np.asarray(bb[:3]), np.asarray(bb[3:])
    pts = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    q = pts @ R[:, :3].T
    return np.r_[q.min(0), q.max(0)]


def _cone_dirs(a):
    """Directions dans un cone autour de a (CONE degres, 8 azimuts chacun), de la plus proche a la plus eloignee."""
    R = _rot(a)[:, :3]
    out = []
    for deg in CONE:
        t = math.radians(deg)
        for k in range(8):
            phi = 2 * math.pi * k / 8
            out.append((deg, R.T @ np.array([math.sin(t) * math.cos(phi), math.sin(t) * math.sin(phi), math.cos(t)])))
    return out


def balayage(piece_r, z_fin, pas=PAS, retrait=FROTTEMENT):
    """Volume balaye par une piece (deja tournee : elle recule selon +Z) de sa place jusqu'a la cote z_fin.
    Tranche k : union des sections de la piece sous la cote h_k (retrecies de 'retrait' : frottement tolere),
    extrudee jusqu'a h_k+1 (exact a 'pas' pres). Renvoie (volume balaye, contour de la piece vue dans l'axe)."""
    bb = piece_r.bounding_box()
    z0, z1 = bb[2], bb[5]
    zt = min(z1, z_fin)                               # au-dela de z_fin, inutile de trancher
    n = min(max(1, int(math.ceil((zt - z0) / pas))), 300)
    hs = z0 + (np.arange(n) + 0.5) * (zt - z0) / n
    U = CrossSection()
    blocs, debut, aire, Uc = [], None, -1.0, None
    for h in hs:
        s = piece_r.slice(float(h))
        if retrait > 0 and not s.is_empty():
            s = s.offset(-retrait, JoinType.Miter, 2.0)
        if not s.is_empty():
            U = (U + s).simplify(0.005)
        a = U.area()
        if debut is None:
            debut, aire, Uc = h, a, U
        elif a > aire * 1.01 + 0.2:                   # le contour grossit nettement : on ferme le bloc precedent
            if aire > 0:
                blocs.append(Manifold.extrude(Uc, float(h - debut)).translate([0, 0, float(debut)]))
            debut, aire, Uc = h, a, U
    if U.area() > 0 and z_fin > debut:
        blocs.append(Manifold.extrude(U, float(z_fin - debut)).translate([0, 0, float(debut)]))
    return (Manifold.batch_boolean(blocs, OpType.Add) if blocs else Manifold()), U


class _Essai:
    """Une piece, une direction, les pieces deja en place : les mesures de la regle 1."""
    def __init__(self, groupe, a, obstacles, bbs, doigt):
        self.R = _rot(a)
        self.p = Manifold.batch_boolean(groupe, OpType.Add).transform(self.R)
        b = self.p.bounding_box()
        self.z0, self.z1 = b[2], b[5]
        self.haut = self.z1 - self.z0                  # hauteur de la piece dans le sens de la pose
        zmax = self.z1 + max(self.haut + COURSE_PLUS, HAUTEUR_DOIGT if doigt else 0.0)
        m = max(MARGE_DOIGT if doigt else 0.0, JEU_TEST) + 0.5
        self.obs = []
        for nom, o in obstacles.items():
            q = _bbox_rot(bbs[nom], self.R)
            if q[5] < self.z0 - 1 or q[2] > zmax or q[0] > b[3] + m or q[3] < b[0] - m or q[1] > b[4] + m or q[4] < b[1] - m:
                continue
            self.obs.append((nom, o.transform(self.R)))
        self._U = None

    def _contact(self, M):
        if M.is_empty() or not self.obs:
            return 0.0, []
        tot, qui = 0.0, []
        for nom, o in self.obs:
            v = (M ^ o).volume()
            if v > SEUIL:
                qui.append((nom, round(v, 2)))
            tot += v
        return tot, qui

    def chemin(self, L):
        """Volume touche quand la piece recule de L."""
        S, self._U = balayage(self.p, self.z1 + L)
        return self._contact(S)

    def cheminee(self):
        """Volume dans la cheminee du doigt."""
        if self._U is None:
            _, self._U = balayage(self.p, self.z1 + 0.1, retrait=0.0)
        ring = self._U.offset(MARGE_DOIGT, JoinType.Round, 2.0, 24)
        D = Manifold.extrude(ring, float(HAUTEUR_DOIGT - DEPART_MARGE)).translate([0, 0, float(self.z1 + DEPART_MARGE)])
        return self._contact(D)

    def recul_libre(self):
        """Recul possible sans rien toucher (mm, a 0,1 mm pres), borne a la hauteur + COURSE_PLUS."""
        lo, hi = 0.0, self.haut + COURSE_PLUS
        while hi - lo > 0.1:
            mid = (lo + hi) / 2
            if self.chemin(mid)[0] <= SEUIL_CHEMIN: lo = mid
            else: hi = mid
        return lo

    def sortie(self, t):
        """True si, reculee de t, la piece peut bouger de JEU_TEST de cote dans au moins une direction (sur 8) :
        elle est sortie de ses emboitements (une cle dans son logement, un tenon dans son trou ne bougent dans aucune)."""
        for k in range(8):
            ang = 2 * math.pi * k / 8
            d = [math.cos(ang) * JEU_TEST, math.sin(ang) * JEU_TEST, t]
            if self._contact(self.p.translate(d))[0] <= SEUIL_CHEMIN:
                return True
        return False


def _juge(groupe, a, obstacles, bbs, doigt, rapide=False):
    """(ok, mesures) pour une direction. rapide : seulement le recul de la hauteur + 1 mm (recherche en cone)."""
    e = _Essai(groupe, a, obstacles, bbs, doigt)
    L = e.haut + COURSE_PLUS
    vc, qui = e.chemin(L)
    info = dict(vol=round(vc, 2), qui=qui, haut=round(e.haut, 2), recul=round(L, 2), sortie=None, cheminee=0.0, qui_d=[])
    ok = vc <= SEUIL_CHEMIN
    if not ok and not rapide:
        F = e.recul_libre()
        info['recul'] = round(F, 2)
        if F >= COURSE_PLUS and e.sortie(F - COURSE_PLUS):
            ok, info['sortie'] = True, round(F - COURSE_PLUS, 2)
    if doigt and ok:
        vd, qd = e.cheminee()
        info['cheminee'], info['qui_d'] = round(vd, 2), qd
        ok = vd <= SEUIL_CHEMIN
    elif doigt and not rapide:
        vd, qd = e.cheminee()
        info['cheminee'], info['qui_d'] = round(vd, 2), qd
    return ok, info


def controle_pose(pieces, ordre, base=(), verbeux=True):
    """Pose les pieces une a une dans l'ordre (regle 1). pieces : {nom: Manifold} ; base : noms deja en place.
    Renvoie (defauts, poses non controlees, pieces oubliees) ; defaut = (noms, direction, mesures)."""
    en_place = {n: pieces[n] for n in base}
    bbs = {n: m.bounding_box() for n, m in pieces.items()}
    defauts, hors, vus = [], [], set(base)
    for p in ordre:
        for n in p.noms:
            if n not in pieces:
                raise KeyError(f"piece inconnue dans l'ordre de pose : {n}")
        if p.hors:
            hors.append((p.noms, p.hors))
        else:
            groupe = [pieces[n] for n in p.noms]
            ok, info = _juge(groupe, p.a, en_place, bbs, p.doigt)
            note = ''
            if not ok and p.cone:
                for deg, a2 in _cone_dirs(p.a):
                    ok2, info2 = _juge(groupe, a2, en_place, bbs, p.doigt, rapide=True)
                    if ok2:
                        ok, info, note = True, info2, f' (a {deg:.0f} deg de la direction annoncee)'
                        break
            if ok and verbeux:
                s = f", sortie de ses emboitements apres {info['sortie']} mm" if info['sortie'] is not None else ''
                print(f"  ok      {', '.join(p.noms)}{note}{s}")
            if not ok:
                defauts.append((p.noms, np.round(p.a, 3).tolist(), info))
                if verbeux:
                    print(f"  BLOQUE  {', '.join(p.noms)} : recule de {info['recul']} mm sur {info['haut']} mm de hauteur ; "
                          f"{info['vol']} mm3 sur le chemin {info['qui'][:4]} ; cheminee {info['cheminee']} mm3 {info['qui_d'][:4]}")
        for n in p.noms:
            en_place[n] = pieces[n]; vus.add(n)
    return defauts, hors, sorted(set(pieces) - vus)


# ---------------------------------------------------------------------------------------------------------------
# Regle 2 - une petite piece ne tombe pas toute seule (cotes d'ecrasement : voir emboitements.py)
JEU_MAX = 0.16        # mm : sans ses cotes, la piece ne bouge pas de plus de 0,16 mm de cote (jeu standard 0,1 mm)
SERRAGE_MIN = 0.05    # mm3 : les cotes de la piece imprimee touchent bien la piece d'en face...
SERRAGE_MAX = 5.0     # mm3 : ... sans la traverser


def controle_maintien(nominale, serree, autres, axe, bas=None):
    """nominale : la piece de la maquette assemblee ; serree : la piece imprimee (avec ses cotes) a la meme place ;
    autres : {nom: Manifold} des pieces qui la recoivent ; axe : sens de la pose ; bas : direction de la pesanteur
    (le jeu a moins de 45 degres du bas est ignore : le poids de la piece la tient dans ce sens).
    Renvoie (ok, serrage en mm3, directions ou le jeu depasse JEU_MAX)."""
    bb = np.array(serree.bounding_box())
    proches = [m for m in autres.values()
               if not (np.any(np.array(m.bounding_box())[3:] < bb[:3] - 1) or np.any(np.array(m.bounding_box())[:3] > bb[3:] + 1))]
    if not proches:
        return False, 0.0, ['aucune piece en face']
    O = Manifold.batch_boolean(proches, OpType.Add)
    serrage = (serree ^ O).volume()
    R = _rot(axe)[:, :3]
    trop = []
    for k in range(8):
        ang = 2 * math.pi * k / 8
        d = R.T @ np.array([math.cos(ang) * JEU_MAX, math.sin(ang) * JEU_MAX, 0.0])
        if bas is not None and d @ np.asarray(bas, float) > JEU_MAX * math.cos(math.radians(45)):
            continue
        if (nominale.translate(d.tolist()) ^ O).volume() <= SEUIL:
            trop.append(f"{k * 45} deg")
    ok = SERRAGE_MIN <= serrage <= SERRAGE_MAX and not trop
    return ok, serrage, trop
