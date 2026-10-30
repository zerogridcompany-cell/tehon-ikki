#!/usr/bin/env python3
"""text_measure.py  字の型が無いうちに、字ごとに色の決まりでマスクを取って 時刻・箱・行・色を測る（51 の最初の測り＝build_texts の箱の元）。

何をする：字ごとに決めた窓（reg）を半分の大きさで毎コマ読み、色の決まり（cls）でマスク → 出る（10%）・出揃う（90%）・消え始め・消える
  コマ、左端・右端の列が出るコマ（打ち字の速さ）、箱（出揃った間ずっと同じ色の所だけ＝動く地を抜く）・行ごとの箱 lines・色の中央値。
  手本とうちの両方に同じ物をかけて比べる。
使い方：python3 text_measure.py <mp4> <spec.json> <out.json> [--ids a,b]
入れる物：spec＝[{id, a, b（秒・探す範囲）, full（出揃った秒）, reg:[x0,y0,x1,y1]（画面の px）, cls, still?:true, nosub?:false}]
  cls＝white・white2・cream・dark・black・red・darkred・green・green2・olive・navy・grey か "#rrggbb"（RGB 距離 70 以内）
出す物：out.json＝[{id, on, full, exit, gone, left, right（秒）, box, lines, w, h, color, ink}] → build_texts.py の下書きの box / color に
効いた数字（51）：57語の最初の箱と色（この後 字だけの層ができたら txt_time・glyph_match の型の中の測りに替える＝後ろの白・赤を拾わんため）
"""
import sys, json, subprocess, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U

def cls_mask(f, c):
    r, g, b = f[..., 0].astype(int), f[..., 1].astype(int), f[..., 2].astype(int)
    if c.startswith('#'):
        h = c.lstrip('#'); col = np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)])
        return np.linalg.norm(f.astype(np.float32) - col, axis=2) < 70
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b); lum = (r * 3 + g * 6 + b) / 10
    return {
        "white": (mn > 205) & (mx - mn < 60), "white2": (mn > 165) & (mx - mn < 45),
        "cream": (r > 200) & (g > 185) & (b > 120) & (r - b > 25),
        "dark": lum < 70, "black": lum < 70,
        "red": (r > 110) & (r > 2.2 * g) & (r > 2.0 * b),
        "darkred": (r > 55) & (r > 1.9 * g) & (r > 1.9 * b) & (lum < 120),
        "green": (g > r + 30) & (g > b + 20), "green2": (g > r + 30) & (g > b + 15),
        "olive": (r > 70) & (r < 160) & (g > 70) & (g < 160) & (b < g - 18) & (abs(r - g) < 28),
        "navy": (b > r + 12) & (lum < 100),
        "grey": (lum > 45) & (lum < 140) & (mx - mn < 25),
    }[c]

def frames(p, a, b, fps, W, H):
    n = int(round((b - a) * fps)); w, h = W // 2, H // 2
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(a - 0.5 / fps, 0):.4f}", "-i", p, "-frames:v", str(n), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)

def measure(p, s, fps, W, H):
    S = 2; a0 = max(0, s["a"] - 0.2); b0 = s["b"] + 0.1
    F = frames(p, a0, b0, fps, W, H)
    x0, y0, x1, y1 = [v // S for v in s["reg"]]
    M = np.stack([cls_mask(f[y0:y1, x0:x1], s["cls"]) for f in F])
    ink = M.reshape(len(M), -1).sum(1).astype(float)
    kf = min(len(F) - 1, int(round((s["full"] - a0) * fps)))
    base = np.median(ink[:3]) if s["a"] > 0.1 else 0
    pk = ink[kf]
    k1 = min(len(M) - 1, kf + int(0.4 * fps)); k0 = max(0, kf - int(0.2 * fps))
    m = np.logical_and.reduce(M[k0:k1 + 1]) if s.get("still", True) else M[kf].copy()
    if s["a"] > 0.1 and not s.get("nosub"): m &= ~np.logical_and.reduce(M[0:3])
    cols = m.sum(0); rows = m.sum(1)
    def span(v):
        idx = np.where(v > max(2, v.max() * 0.06))[0]
        return (int(idx[0]), int(idx[-1])) if len(idx) else (0, 0)
    cx = span(cols); ry = span(rows)
    box = [(x0 + cx[0]) * S, (y0 + ry[0]) * S, (x0 + cx[1] + 1) * S, (y0 + ry[1] + 1) * S]
    lines = []; rr = m.sum(1); on_ = rr > max(2, rr.max() * 0.04); i = 0
    while i < len(on_):
        if on_[i]:
            j = i
            while j < len(on_) and (on_[j] or (j + 6 < len(on_) and on_[j:j + 6].any())): j += 1
            if j - i > 4:
                cc = m[i:j].sum(0); ix = np.where(cc > 0)[0]
                lines.append([(x0 + int(ix[0])) * S, (y0 + i) * S, (x0 + int(ix[-1]) + 1) * S, (y0 + j) * S])
            i = j
        else: i += 1
    fr = F[kf][y0:y1, x0:x1][m]
    col = [int(v) for v in np.median(fr, 0)] if len(fr) else [0, 0, 0]
    rng = pk - base
    t = lambda i: round(a0 + i / fps, 3)
    on = next((i for i in range(len(ink)) if ink[i] - base > 0.1 * rng), None)
    full = next((i for i in range(len(ink)) if ink[i] - base > 0.9 * rng), None)
    ex = next((i for i in range(len(ink) - 1, kf - 1, -1) if ink[i] - base > 0.9 * rng), None)
    gone = next((i for i in range(len(ink) - 1, kf - 1, -1) if ink[i] - base > 0.1 * rng), None)
    sub = M[:, ry[0]:ry[1] + 1, cx[0]:cx[1] + 1].sum(1).astype(float)
    fin = sub[kf] + 1e-6; w = sub.shape[1]
    def first(c0, c1):
        s_ = sub[:, c0:c1].sum(1); f_ = fin[c0:c1].sum()
        return next((i for i in range(len(s_)) if s_[i] > 0.5 * f_), None)
    L = first(0, max(1, w // 10)); R = first(w - max(1, w // 10), w)
    tt = lambda v: t(v) if v is not None else None
    return {"id": s["id"], "on": tt(on), "full": tt(full), "exit": tt(ex), "gone": tt(gone), "left": tt(L), "right": tt(R),
            "box": box, "lines": lines, "h": box[3] - box[1], "w": box[2] - box[0], "color": col, "ink": int(pk)}

if __name__ == "__main__":
    p, sp, out = sys.argv[1:4]
    W, H, fps, _ = U.probe(p)
    spec = json.load(open(sp))
    if "--ids" in sys.argv: ids = sys.argv[sys.argv.index("--ids") + 1].split(","); spec = [s for s in spec if s["id"] in ids]
    res = []
    for s in spec:
        try: r = measure(p, s, fps, W, H)
        except Exception as e: r = {"id": s["id"], "err": str(e)}
        res.append(r); print(json.dumps(r, ensure_ascii=False))
    json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
