"""Export des pieces vers le format JSON du site (quantifie, une entree par piece et par couleur)."""
import json, base64
import numpy as np

SCALE = 1.0 / 12.0
MM = 1000.0 * SCALE

def to_site(parts, path):
    """parts : liste de dict(id, nm, k, m (Manifold), e (vecteur d'eclatement en m reels, optionnel))."""
    meshes = []
    for p in parts:
        me = p["m"].to_mesh(); V = np.array(me.vert_properties)[:, :3].astype(np.float64); F = np.array(me.tri_verts).astype(np.int64)
        X = np.stack([V[:, 0] * MM, V[:, 2] * MM, -V[:, 1] * MM], 1)       # x avant, y haut, z tribord
        meshes.append((p, X, F))
    allv = np.vstack([X for _, X, _ in meshes]); o = allv.min(0); s = float((allv.max(0) - o).max() / 65535.0)
    out = []
    for p, X, F in meshes:
        q = np.clip(np.round((X - o) / s), 0, 65535).astype(np.uint16)
        big = len(X) > 65535; ii = F.astype(np.uint32 if big else np.uint16)
        lo, hi = X.min(0), X.max(0); c = (lo + hi) / 2
        e = p.get("e", (0, 0, 0)); e = [e[0] * MM, e[2] * MM, -e[1] * MM]
        out.append({"k": p["k"], "n": int(len(X)), "b": bool(big), "p": base64.b64encode(q.tobytes()).decode(), "i": base64.b64encode(ii.tobytes()).decode(),
                    "id": p["id"], "nm": p.get("nm", p["id"]), "c": [round(float(v), 1) for v in c], "r": round(float(np.linalg.norm(hi - lo) / 2), 1), "e": [round(float(v), 1) for v in e]})
    json.dump({"o": [float(v) for v in o], "s": s, "g": out}, open(path, "w"), separators=(",", ":"), ensure_ascii=False)
    return path
