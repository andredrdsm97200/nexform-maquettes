"""Petit rasteriseur z-buffer (numpy) pour des rendus propres sans GPU."""
import numpy as np
from PIL import Image


def look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = map(lambda v: np.asarray(v, float), (eye, target, up))
    f = target - eye; f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return r, u, f


def render(parts, eye, target, W=1600, H=1000, fov=28, ss=2, bg=(255, 255, 255),
           light=(-0.35, -0.55, 0.75), ortho=None):
    """parts: liste de (trimesh, rgb 0-1). Retourne une image PIL."""
    Wp, Hp = W * ss, H * ss
    r, u, f = look_at(eye, target)
    eye = np.asarray(eye, float)
    zbuf = np.full((Hp, Wp), np.inf)
    img = np.empty((Hp, Wp, 3)); img[:] = np.array(bg) / 255.0
    L = np.asarray(light, float); L /= np.linalg.norm(L)
    focal = (Hp / 2) / np.tan(np.radians(fov) / 2)
    for tm, col in parts:
        tri = tm.triangles - eye
        cam = np.stack([tri @ r, tri @ u, tri @ f], -1)       # (n,3,3)
        n = tm.face_normals
        view = -(tm.triangles.mean(1) - eye); view /= np.linalg.norm(view, axis=1)[:, None]
        nn = np.where((n * view).sum(1)[:, None] < 0, -n, n)   # ombrage double face
        diff = np.clip(nn @ L, 0, 1)
        hv = L + view; hv /= np.linalg.norm(hv, axis=1)[:, None]
        spec = np.clip((nn * hv).sum(1), 0, 1) ** 40
        shade = 0.30 + 0.62 * diff
        c = np.clip(np.asarray(col)[None, :] * shade[:, None] + 0.18 * spec[:, None], 0, 1)
        if ortho:
            sx = cam[..., 0] / ortho * (Hp / 2) + Wp / 2
            sy = -cam[..., 1] / ortho * (Hp / 2) + Hp / 2
        else:
            sx = cam[..., 0] / cam[..., 2] * focal + Wp / 2
            sy = -cam[..., 1] / cam[..., 2] * focal + Hp / 2
        z = cam[..., 2]
        near = 1.0 if not ortho else -1e9
        for i in range(len(tri)):
            if z[i].min() < near:
                continue
            x0, x1, x2 = sx[i]; y0, y1, y2 = sy[i]
            minx = max(int(np.floor(min(x0, x1, x2))), 0); maxx = min(int(np.ceil(max(x0, x1, x2))), Wp - 1)
            miny = max(int(np.floor(min(y0, y1, y2))), 0); maxy = min(int(np.ceil(max(y0, y1, y2))), Hp - 1)
            if minx > maxx or miny > maxy:
                continue
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-12:
                continue
            xs = np.arange(minx, maxx + 1) + 0.5
            ys = np.arange(miny, maxy + 1) + 0.5
            X, Y = np.meshgrid(xs, ys)
            a = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / den
            b = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / den
            g = 1 - a - b
            m = (a >= -1e-6) & (b >= -1e-6) & (g >= -1e-6)
            if not m.any():
                continue
            zz = a * z[i, 0] + b * z[i, 1] + g * z[i, 2]
            sub = zbuf[miny:maxy + 1, minx:maxx + 1]
            upd = m & (zz < sub)
            sub[upd] = zz[upd]
            img[miny:maxy + 1, minx:maxx + 1][upd] = c[i]
    # contours legers (discontinuites de profondeur)
    zf = np.where(np.isinf(zbuf), zbuf[np.isfinite(zbuf)].max() * 1.5 if np.isfinite(zbuf).any() else 0, zbuf)
    gx = np.abs(np.diff(zf, axis=1, prepend=zf[:, :1])); gy = np.abs(np.diff(zf, axis=0, prepend=zf[:1, :]))
    edge = (gx + gy) > 0.012 * np.median(zf[np.isfinite(zbuf)]) if np.isfinite(zbuf).any() else gx > 0
    img[edge] *= 0.35
    im = Image.fromarray((img * 255).astype(np.uint8))
    return im.resize((W, H), Image.LANCZOS)
