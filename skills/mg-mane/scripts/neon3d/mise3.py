# 手本｜v1｜新しい版 を同じ「手本の秒」で縦に並べた一覧（検品用・0.5 秒おき）
# 使い方: python3 tools/mise3.py <出す所> <動画1> [動画2 ...] [--step 0.5] [--from 0] [--to 65.2] [--cols 8]
# 手本の秒 t → うちの秒＝rikai/ref2out_sec.json（時間の地図）。手本は ref/goat-mercedes.mp4 の round(t*60) コマ
import glob as _g, os as _o
REF = _o.environ.get('REF') or sorted(_g.glob('ref/*.mp4'))[0]   # 手本（作業フォルダの ref/ の mp4）
import sys, json, os, cv2, numpy as np
a = sys.argv[1:]; opt = {}
for k in ['--step', '--from', '--to', '--cols']:
    if k in a: i = a.index(k); opt[k] = float(a[i + 1]); del a[i:i + 2]
out, vids = a[0], a[1:]
step, t0, t1, cols = opt.get('--step', 0.5), opt.get('--from', 0.0), opt.get('--to', 65.15), int(opt.get('--cols', 8))
R2O = json.load(open('rikai/ref2out_sec.json'))
ts = list(np.round(np.arange(t0, t1 + 1e-6, step), 3))
TW, TH = 180, 320
def grab(path, idx):
    want = sorted(set(idx)); cap = cv2.VideoCapture(path); got = {}; n = 0; j = 0
    while j < len(want):
        ok, fr = cap.read()
        if not ok: break
        if n == want[j]:
            got[n] = cv2.resize(fr, (TW, TH), interpolation=cv2.INTER_AREA)
            while j < len(want) and want[j] == n: j += 1
        n += 1
    return [got.get(i, np.zeros((TH, TW, 3), np.uint8)) for i in idx]
rows = [('ref', grab(REF, [int(round(t * 60)) for t in ts]))]
for v in vids:
    rows.append((os.path.basename(v)[:14], grab(v, [int(round(R2O[min(len(R2O) - 1, int(round(t * 60)))] * 60)) for t in ts])))
os.makedirs(out, exist_ok=True)
for s in range(0, len(ts), cols):
    sheet = np.full((len(rows) * (TH + 4) + 24, cols * (TW + 4), 3), 60, np.uint8)
    for c, t in enumerate(ts[s:s + cols]):
        x = c * (TW + 4); cv2.putText(sheet, f'{t:.1f}', (x + 4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
        for r, (name, ims) in enumerate(rows):
            y = 24 + r * (TH + 4); sheet[y:y + TH, x:x + TW] = ims[s + c]
            if c == 0: cv2.putText(sheet, name, (x + 3, y + TH - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
    cv2.imwrite(f'{out}/m_{ts[s]:05.1f}.jpg', sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
print(out, len(ts), 'コマ', (len(ts) + cols - 1) // cols, '枚')
