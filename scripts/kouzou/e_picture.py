# 手本の絵の出来事を1コマずつ数字で取る：カット（中身が入れ替わる）・フラッシュ（明るさが跳ねて戻る）・寄り（同じ絵が急に大きく）
import cv2, numpy as np, json, sys
V = sys.argv[1]; OUT = sys.argv[2]
cap = cv2.VideoCapture(V); fps = cap.get(cv2.CAP_PROP_FPS); F = []
prev = None; orb = cv2.ORB_create(400); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
rows = []
while True:
    ok, fr = cap.read()
    if not ok: break
    g = cv2.cvtColor(cv2.resize(fr, (320, 180)), cv2.COLOR_BGR2GRAY)
    top = g[:126]   # 下の3割（字幕）を外す
    h = cv2.calcHist([cv2.cvtColor(cv2.resize(fr, (160, 90))[:63], cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256]); h = cv2.normalize(h, h).flatten()
    r = dict(f=len(rows), lum=float(top.mean()))
    if prev is not None:
        pg, ph = prev
        r['diff'] = float(np.abs(top.astype(int) - pg.astype(int)).mean()); r['hist'] = float(cv2.compareHist(ph, h, cv2.HISTCMP_BHATTACHARYYA))
        k1, d1 = orb.detectAndCompute(pg, None); k2, d2 = orb.detectAndCompute(top, None); sc = 1.0; nm = 0
        if d1 is not None and d2 is not None and len(k1) > 20 and len(k2) > 20:
            m = bf.match(d1, d2); nm = len(m)
            if nm > 25:
                A = np.float32([k1[x.queryIdx].pt for x in m]); B = np.float32([k2[x.trainIdx].pt for x in m])
                M, inl = cv2.estimateAffinePartial2D(A, B)
                if M is not None and inl is not None and inl.sum() > 20: sc = float(np.sqrt(abs(np.linalg.det(M[:, :2]))))
        r['scale'] = sc; r['nm'] = nm
    rows.append(r); prev = (top, h)
fps = float(fps); ev = []
lum = np.array([r['lum'] for r in rows])
for i, r in enumerate(rows[1:], 1):
    t = round(i / fps, 4)
    if r['hist'] > 0.35 or (r['diff'] > 28 and r['nm'] < 25): ev.append(dict(t=t, f=i, kind='cut', s=round(r['hist'], 3)))
    elif r['scale'] > 1.035 or r['scale'] < 0.965: ev.append(dict(t=t, f=i, kind='punch', s=round(r['scale'], 3)))
    if i + 3 < len(rows) and lum[i] - lum[i - 1] > 35 and lum[i + 2] - lum[i] < -20: ev.append(dict(t=t, f=i, kind='flash', s=round(float(lum[i] - lum[i - 1]), 1)))
json.dump(dict(fps=fps, n=len(rows), events=ev, rows=rows), open(OUT, 'w'))
from collections import Counter; print(fps, len(rows), Counter(e['kind'] for e in ev))
