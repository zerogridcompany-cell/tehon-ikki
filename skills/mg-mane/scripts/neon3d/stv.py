# 手本｜うちの静止画（proj の Ref＝手本の秒そのまま）を並べる: python3 tools/stv.py <静止画フォルダ> <出す jpg> <コマ,コマ,...> [列]
import glob as _g, os as _o
REF = _o.environ.get('REF') or sorted(_g.glob('ref/*.mp4'))[0]   # 手本（作業フォルダの ref/ の mp4）
import sys, cv2, numpy as np
d, out, fs = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')]; cols = int(sys.argv[4]) if len(sys.argv) > 4 else 6
cap = cv2.VideoCapture(REF); want = set(fs); got = {}; n = 0
while len(got) < len(want):
    ok, fr = cap.read()
    if not ok: break
    if n in want: got[n] = fr
    n += 1
TW, TH = 216, 384; tiles = []
for f in fs:
    r = cv2.resize(got[f], (TW, TH)); u = cv2.imread(f'{d}/u{f:05d}.png'); u = cv2.resize(u, (TW, TH)) if u is not None else np.zeros_like(r)
    p = np.vstack([r, u]); cv2.putText(p, f'{f/60:.2f}', (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1); tiles.append(p)
while len(tiles) % cols: tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack([np.pad(t, ((2, 2), (2, 2), (0, 0)), constant_values=80) for t in tiles[i:i + cols]]) for i in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85]); print(out)
