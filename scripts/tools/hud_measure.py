"""追跡の飾り（赤い四角・緑の点・座標の字・白い点線）を手本のコマごとに測って hud.json にする（10/28 r2 21〜25）。手本の画素は写さん＝位置と大きさだけ。
python3 hud_measure.py <作業> <f0> <f1> [--clean cuts の書き出し.mp4] [--out proj/src/hud.json]
- 赤＝R>150・G<90・B<110・R-G>80 → 横線・縦線の切れ端 [x0,y0,x1,y1]（重なった四角もそのまま描ける・画面の縁の長い線は "border"）
- 緑＝G>150・R<130・B<130 の小さい塊（面積 6〜200）→ 中心
- 字＝白い字の塊（--clean がある時は「手本−うちの素の絵」で白く出た所）→ 箱＋中身（近い横線の左端か点の座標 −3＝r2 25 の実測 189,327→"x: 186 y: 324"）。置き場＝左は角の x・字の下の線は角の y−9・大きさ＝数字の高さ÷0.72
- 点線＝--clean がある時、細い白（字の箱の外）を骨にして 8px ごとの点の列
"""
import argparse, glob, json, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retime import rd

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("f0", type=int); ap.add_argument("f1", type=int)
ap.add_argument("--clean"); ap.add_argument("--out", default="proj/src/hud.json"); ap.add_argument("--print", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w)
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(a.f0, a.f1))
C = rd(os.path.join(w, a.clean), sel=(a.f0, a.f1)) if a.clean else None


def comps(m, amin, amax):
    n, l, st, cen = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    return [(st[i], cen[i]) for i in range(1, n) if amin <= st[i, 4] <= amax]


out = {}
for k, f in enumerate(R):
    fr = a.f0 + k; b, g, r = [f[..., i].astype(int) for i in range(3)]
    red = (r > 150) & (g < 90) & (b < 110) & (r - g > 80)
    grn = (g > 150) & (r < 130) & (b < 130) & (g - r > 60)
    dots = [[round(float(c[0]), 1), round(float(c[1]), 1)] for st, c in comps(grn, 6, 200)]
    # 赤い枠＝重なると四角がくっつく → 横線・縦線の切れ端で取る（四角に組まん）
    border = False; segs = []
    rm = red.astype(np.uint8)
    hz = cv2.morphologyEx(rm, cv2.MORPH_OPEN, np.ones((1, 12), np.uint8)); vt = cv2.morphologyEx(rm, cv2.MORPH_OPEN, np.ones((12, 1), np.uint8))
    for st, _ in comps(hz, 12, 10 ** 7):
        x, y, ww, hh, area = map(int, st)
        if ww > 1200: border = True; continue
        segs.append([x, y + hh / 2, x + ww, y + hh / 2])
    for st, _ in comps(vt, 12, 10 ** 7):
        x, y, ww, hh, area = map(int, st)
        if hh > 690: border = True; continue
        segs.append([x + ww / 2, y, x + ww / 2, y + hh])
    boxes = segs
    texts, lines = [], []
    if C is not None:
        d = f.astype(int).sum(2) - C[k].astype(int).sum(2)
        wt = (f.min(2) > 185) & (d > 120)
        wt[red | grn] = False
        tm = cv2.morphologyEx(wt.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 11)))
        for st, _ in comps(tm, 60, 6000):
            x, y, ww, hh, area = map(int, st)
            if 10 <= hh <= 30 and ww >= 2 * hh and wt[y:y + hh, x:x + ww].mean() > 0.12:
                anc = [(sg[0], sg[1]) for sg in segs if sg[1] == sg[3]] + [tuple(d_) for d_ in dots]
                ax, ay = min(anc, key=lambda q: (q[0] - x) ** 2 + (q[1] - (y + hh)) ** 2) if anc else (x, y + hh)
                key = (int(round(ax)), int(round(ay)))
                if key not in [tuple(t_[5]) for t_ in texts]:  # 角ごとに1つ（数字ごとに割れて拾うため）
                    texts.append([int(round(ax)), int(round(ay)) - 9, ww, hh, f"x: {key[0] - 3}  y: {key[1] - 3}", list(key), round(hh / 0.72, 1)])
                wt[y:y + hh, x:x + ww] = False
        ys, xs = np.where(wt)
        pts = sorted(zip(xs.tolist(), ys.tolist()))
        lines = [[int(x), int(y)] for x, y in pts[::3]]
    out[str(fr)] = {"boxes": boxes, "dots": dots, "texts": texts, "dash": lines, "border": border}
    if a.print: print(fr, "四角", len(boxes), "点", len(dots), "字", len(texts), "線点", len(lines), "縁", border)
json.dump(out, open(os.path.join(w, a.out), "w"))
print("書いた", a.out, len(out))
