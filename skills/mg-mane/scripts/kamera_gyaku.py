# カメラの逆算（カットごと）＝ 2 コマおきに前のコマと特徴点を合わせ（ORB＋RANSAC の相似変換）、カットの頭からの寄り(倍)・流し(px)・回り(度)を積む
# 使い方: python3 kamera_gyaku.py <動画> <切り替えの表 json [[名,頭のコマ],…]> <出力 json> [見出しの帯=0.16]
# 出力: {名: {"f0":頭, "f1":終わり, "k":[[コマ, 倍, x流し(1920px), y流し(1080px), 回り度, 合った点の数], …]}}
#   ※ 倍・流しは「頭のコマの画面中心」を基準にした相似変換（p_t = s·R·(p_0 − c) + c + T）
import cv2, json, sys, numpy as np
src, cuts_p, outp = sys.argv[1], sys.argv[2], sys.argv[3]; TOP = float(sys.argv[4]) if len(sys.argv) > 4 else 0.16
CUTS = json.load(open(cuts_p)); cap = cv2.VideoCapture(src); N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
W, H = 960, 540; G = []
while True:
    ok, im = cap.read()
    if not ok: break
    G.append(cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (W, H), interpolation=cv2.INTER_AREA))
orb = cv2.ORB_create(4000, fastThreshold=8); mask = np.zeros((H, W), np.uint8); mask[int(H * TOP):] = 255
bf = cv2.BFMatcher(cv2.NORM_HAMMING)
def step(a, b):
    k1, d1 = orb.detectAndCompute(a, mask); k2, d2 = orb.detectAndCompute(b, mask)
    if d1 is None or d2 is None or len(k1) < 12 or len(k2) < 12: return None, 0
    mm = bf.knnMatch(d1, d2, k=2); good = [m for m, n in (x for x in mm if len(x) == 2) if m.distance < 0.8 * n.distance]
    if len(good) < 10: return None, len(good)
    p1 = np.float32([k1[m.queryIdx].pt for m in good]); p2 = np.float32([k2[m.trainIdx].pt for m in good])
    M, inl = cv2.estimateAffinePartial2D(p1, p2, ransacReprojThreshold=1.5, maxIters=4000, confidence=0.995)
    if M is None: return None, 0
    return np.vstack([M, [0, 0, 1]]), int(inl.sum())
OUT = {}
for i, (nm, f0) in enumerate(CUTS):
    f1 = CUTS[i + 1][1] if i + 1 < len(CUTS) else N
    a0 = f0 + 4; acc = np.eye(3); K = [[a0, 1.0, 0.0, 0.0, 0.0, 0]]
    for f in range(a0 + 2, f1 - 1, 2):
        M, n = step(G[f - 2], G[f])
        if M is None or n < 12: M = np.eye(3)
        s = np.hypot(M[0, 0], M[1, 0])
        cm = M @ np.array([W / 2, H / 2, 1]) - np.array([W / 2, H / 2, 1])
        if abs(s - 1) > 0.06 or abs(cm[0]) > 12 or abs(cm[1]) > 12: M = np.eye(3)  # 物の動きに引っぱられた跳びは捨てる
        acc = M @ acc; s = float(np.hypot(acc[0, 0], acc[1, 0])); r = float(np.degrees(np.arctan2(acc[1, 0], acc[0, 0])))
        c = np.array([W / 2, H / 2, 1]); mv = acc @ c - c
        K.append([f, round(s, 4), round(float(mv[0]) * 2, 1), round(float(mv[1]) * 2, 1), round(r, 2), n])
    OUT[nm] = dict(f0=f0, f1=f1, k=K)
    e = K[-1]; print(f'{nm:12s} {f0:5d}-{f1:5d} 倍 {e[1]:.3f} 流し {e[2]:+.0f},{e[3]:+.0f}px 回り {e[4]:+.2f}° 点(中央) {int(np.median([k[5] for k in K[1:]] or [0]))}')
json.dump(OUT, open(outp, 'w'))
