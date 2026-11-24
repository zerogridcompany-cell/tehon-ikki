# 掃除係（差し色の塊）の箱を手本とうちで比べる：カットごと q=0.35,0.55,0.75 の中央値（画面の px）
# 使い方: python3 tools/hito_box.py <うちの静止画dir>   → rikai/hito_box.json
import cv2, json, re, numpy as np
RF = json.load(open('rikai/rf.json')); rx = [a for a, b in RF]; ry = [b for a, b in RF]
CUT = [('A_factory', 0)]
for line in open('rikai/zure_kirikae.md'):
    m = re.match(r'\| (\w+) \| (\d+) \|', line)
    if m: CUT.append((m.group(1), int(m.group(2))))
CUT.append(('END', 2580)); import sys; D = sys.argv[1]; cr = cv2.VideoCapture('ref/mute-pagani.mp4'); out = {}
def blob(im, ref):
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV); h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    m = ((h < 20) if ref else ((h > 28) & (h < 50))) & (s > 140) & (v > 140); m = m.astype(np.uint8); m[:170] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    c = [i for i in range(1, n) if st[i, 4] > 1500 and st[i, 3] > st[i, 2] * 1.2]  # 縦長の塊＝人
    if not c: return None
    i = max(c, key=lambda i: st[i, 4]); x, y, w, hh, a = st[i]; return [x + w / 2, y + hh, hh]
for i in range(len(CUT) - 1):
    nm, f0 = CUT[i]; t0, t1 = f0 / 30, CUT[i + 1][1] / 30; R, O = [], []
    for q in (0.35, 0.55, 0.75):
        tr = t0 + q * (t1 - t0); to = float(np.interp(tr, rx, ry)); fo = int(round(to * 30))
        cr.set(cv2.CAP_PROP_POS_MSEC, tr * 1000); ok, a = cr.read()
        import glob
        cand = sorted(glob.glob(f'{D}/u*.png'), key=lambda p: abs(int(p[-9:-4]) - fo))[0]; b = cv2.imread(cand)
        ra, ob = blob(a, True), blob(b, False)
        if ra and ob: R.append(ra); O.append(ob)
    if R:
        r = np.median(R, 0); o = np.median(O, 0); out[nm] = dict(ref=[round(v, 1) for v in r], ours=[round(v, 1) for v in o])
        print(f'{nm:12s} 手本 x{r[0]:6.0f} 下{r[1]:5.0f} 高{r[2]:4.0f} | うち x{o[0]:6.0f} 下{o[1]:5.0f} 高{o[2]:4.0f} | 差 x{o[0]-r[0]:+5.0f} 下{o[1]-r[1]:+5.0f} 高{(o[2]/r[2]-1)*100:+5.1f}%')
json.dump(out, open('rikai/hito_box.json', 'w'))
