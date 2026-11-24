# 線画の写し取り：手本の 1 コマから線（白い線・黒い線・差し色）の「芯」を細線にして折れ線の点に直す → SVG の path と JSON
# 白の線のしきい値は環境変数 SENGA_G（明るさ・既定 165）・SENGA_S（彩度・既定 80）で変えられる（光で色が乗った線は SENGA_S=120 等）
# 使い方: python3 senga_trace.py <動画> <コマ> <x0,y0,x1,y1> <出力の名> [white|ink|accent|fill] [eps=1.2] [最短=14]
#   white＝暗い場面の白い線 / ink＝明るい場面の黒い線 / accent＝差し色（オレンジ等の彩度の高い線） / fill＝塗りの影（灰色の面の外形）
#   出力: <名>.json（{"roi":[…], "lines":[[[x,y],…],…], "d":"M … L …"}・座標は 1920x1080 の画面のまま）と <名>_check.png（赤＝写した線を手本に重ねた確かめ用）
# 決まり：形は「手本のコマから写した点」で作る（想像で描かん）。写した点は Remotion の <path d=…> にそのまま入れ、置き場所は translate/scale で合わせる
import cv2, sys, json, numpy as np
from skimage.morphology import skeletonize
src, fr, roi, name = sys.argv[1], int(sys.argv[2]), [int(v) for v in sys.argv[3].split(',')], sys.argv[4]
mode = sys.argv[5] if len(sys.argv) > 5 else 'white'; eps = float(sys.argv[6]) if len(sys.argv) > 6 else 1.2; minlen = float(sys.argv[7]) if len(sys.argv) > 7 else 14
cap = cv2.VideoCapture(src); cap.set(1, fr); ok, im = cap.read(); assert ok, 'コマが読めん'
x0, y0, x1, y1 = roi; c = im[y0:y1, x0:x1]; g = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY); hsv = cv2.cvtColor(c, cv2.COLOR_BGR2HSV)
GT = float(__import__('os').environ.get('SENGA_G', 165)); ST = float(__import__('os').environ.get('SENGA_S', 80))
if mode == 'white': m = (g > GT) & (hsv[:, :, 1] < ST)
elif mode == 'ink': m = g < 90
elif mode == 'accent': m = (hsv[:, :, 1] > 120) & (hsv[:, :, 2] > 120)
elif mode == 'fill': m = (g > 60) & (g < 175)
m = m.astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(m)
keep = np.zeros_like(m)
for i in range(1, n):
    if st[i, 4] >= 30: keep[lab == i] = 1
if mode != 'fill': keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
if mode == 'fill':
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cs, _ = cv2.findContours(keep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); lines = []
    for cc in cs:
        if cv2.contourArea(cc) < 400: continue
        ap = cv2.approxPolyDP(cc, eps, True)[:, 0, :]; lines.append([[int(p[0]) + x0, int(p[1]) + y0] for p in ap] + [[int(ap[0][0]) + x0, int(ap[0][1]) + y0]])
else:
    sk = skeletonize(keep > 0).astype(np.uint8); H, W = sk.shape
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    def nbrs(y, x): return [(y + dy, x + dx) for dy, dx in nb if 0 <= y + dy < H and 0 <= x + dx < W and sk[y + dy, x + dx]]
    deg = {}
    for y, x in zip(*np.nonzero(sk)): deg[(y, x)] = len(nbrs(y, x))
    seen = set(); lines = []
    def walk(a, b):
        path = [a, b]; seen.add((a, b)); seen.add((b, a)); prev, cur = a, b
        while deg.get(cur, 0) == 2:
            nx = [q for q in nbrs(*cur) if q != prev and (cur, q) not in seen]
            if not nx: break
            prev, cur = cur, nx[0]; seen.add((prev, cur)); seen.add((cur, prev)); path.append(cur)
        return path
    starts = [p for p, d in deg.items() if d != 2]
    for p in starts:
        for q in nbrs(*p):
            if (p, q) not in seen: lines.append(walk(p, q))
    for p, d in deg.items():  # 輪（端の無い線）
        for q in nbrs(*p):
            if (p, q) not in seen: lines.append(walk(p, q))
    out = []
    for L in lines:
        a = np.array([[x, y] for y, x in L], np.int32)
        if len(a) < 2 or np.sum(np.hypot(*np.diff(a, axis=0).T)) < minlen: continue
        ap = cv2.approxPolyDP(a.reshape(-1, 1, 2), eps, False)[:, 0, :]
        out.append([[int(p[0]) + x0, int(p[1]) + y0] for p in ap])
    lines = out
d = ' '.join('M ' + ' L '.join(f'{p[0]} {p[1]}' for p in L) for L in lines)
json.dump(dict(src=src, frame=fr, roi=roi, mode=mode, lines=lines, d=d), open(name + '.json', 'w'))
chk = im.copy(); cv2.rectangle(chk, (x0, y0), (x1, y1), (0, 255, 255), 2)
for L in lines: cv2.polylines(chk, [np.array(L, np.int32)], False, (0, 0, 255), 2)
cv2.imwrite(name + '_check.png', chk[max(0, y0 - 20):y1 + 20, max(0, x0 - 20):x1 + 20])
print(f'{len(lines)} 本・{sum(len(L) for L in lines)} 点 → {name}.json / {name}_check.png')
