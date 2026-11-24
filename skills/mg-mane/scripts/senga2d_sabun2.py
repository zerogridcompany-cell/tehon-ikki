# 差を数字で（カットごと）＝ rikai/sabun2.md と rikai/sabun2.json
# 使い方: python3 tools/sabun2.py <うちの動画> [出力の名=sabun2]
#  ①カメラ＝物の塊の中心(画面%)・大きさ(%)・カット内の寄り(倍)と流し(画面%)を手本と比べる
#  ②形＝輪郭(細線)の重なり F1（3px の許し・960 幅）③線の太さ px・光のにじみ（線の外 2〜8px の明るさ÷線の明るさ）
#  ④出る/消える＝zure_kirikae.md／zure_dekigoto.md（別表）⑤色＝背景と線の ΔE（差し色は除く＝意図）
import cv2, json, sys, re, numpy as np
V = sys.argv[1]; STILLS = V if not V.endswith('.mp4') else None; NAME = sys.argv[2] if len(sys.argv) > 2 else 'sabun2'
RF = json.load(open('rikai/rf.json')); rx = [a for a, b in RF]; ry = [b for a, b in RF]
r2o = lambda t: float(np.interp(t, rx, ry))
CUT = [('A_factory', 0)]
for line in open('rikai/zure_kirikae.md'):
    m = re.match(r'\| (\w+) \| (\d+) \|', line)
    if m: CUT.append((m.group(1), int(m.group(2))))
CUT.append(('END', 2691))
cr = cv2.VideoCapture('ref/mute-pagani.mp4'); co = cv2.VideoCapture(V) if not STILLS else 'stills'
FULL = {}
def grab(cap, t):
    if isinstance(cap, str):  # うちの静止画（u00000.png・コマ番号＝round(秒×30)）
        im = cv2.imread(f'{STILLS}/u{int(round(t * 30)):05d}.png')
    else:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, im = cap.read()
    FULL[id(cap)] = im
    return cv2.resize(im, (960, 540), interpolation=cv2.INTER_AREA)
TOP = 0.16  # 見出しの帯（英語と日本語で違う＝除く）
def fg(im):
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
    b = np.concatenate([lab[60:70, :].reshape(-1, 3), lab[-10:, :].reshape(-1, 3), lab[:, :10].reshape(-1, 3), lab[:, -10:].reshape(-1, 3)])
    bg = np.median(b, 0); d = np.linalg.norm(lab - bg, axis=2); m = (d > 28).astype(np.uint8)
    m[:int(540 * TOP)] = 0; return m, bg, lab
def align(a, b):
    # うち→手本 の相似変換（輪郭をぼかして ECC）＝物の位置のずれ(画面%)・大きさ(%)・回り(度)
    ea = cv2.GaussianBlur(edges(a).astype(np.float32), (0, 0), 5); eb = cv2.GaussianBlur(edges(b).astype(np.float32), (0, 0), 5)
    if ea.sum() < 1 or eb.sum() < 1: return None
    sa, sb = cv2.resize(ea, (480, 270)), cv2.resize(eb, (480, 270)); W = np.eye(2, 3, dtype=np.float32)
    try:
        _, W = cv2.findTransformECC(sa, sb, W, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-5), None, 5)
    except cv2.error: return None
    sc = float(np.sqrt(abs(np.linalg.det(W[:, :2])))); rot = float(np.degrees(np.arctan2(W[1, 0], W[0, 0])))
    c = np.array([240, 135]); mv = W[:, :2] @ c + W[:, 2] - c
    return (float(mv[0] / 480 * 100), float(mv[1] / 270 * 100), (sc - 1) * 100, rot)
def box(m):
    ys, xs = np.nonzero(m)
    if len(xs) < 50: return None
    x0, x1 = np.percentile(xs, [2, 98]); y0, y1 = np.percentile(ys, [2, 98])
    return ((x0 + x1) / 2 / 960 * 100, (y0 + y1) / 2 / 540 * 100, np.hypot(x1 - x0, y1 - y0) / np.hypot(960, 540) * 100)
def edges(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY); e = cv2.Canny(cv2.GaussianBlur(g, (3, 3), 0), 40, 110); e[:int(540 * TOP)] = 0; return e
def f1(e1, e2):
    if e1.sum() == 0 or e2.sum() == 0: return np.nan
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)); d1, d2 = cv2.dilate(e1, k), cv2.dilate(e2, k)
    p = (e2 & d1).sum() / e2.sum(); r = (e1 & d2).sum() / e1.sum(); return 2 * p * r / (p + r + 1e-9)
def stroke(im, bg):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32); dark = bg[0] < 128
    line = (g > 150) if dark else (g < 90); line = line.astype(np.uint8); line[:int(g.shape[0] * TOP)] = 0
    if line.sum() < 100: return np.nan, np.nan
    from skimage.morphology import skeletonize
    dt = cv2.distanceTransform(line, cv2.DIST_L2, 5); sk = skeletonize(line > 0); ww = dt[sk] * 2; ww = ww[(ww > 1) & (ww < 14)]
    w = float(np.median(ww)) if len(ww) > 40 else np.nan  # 1920 の px・塗りの面は除く（芯 14px 未満の線だけ）
    out = cv2.distanceTransform((1 - line).astype(np.uint8), cv2.DIST_L2, 5)
    bgl = np.median(g[out > 40]) if dark and (out > 40).sum() > 100 else 0
    ring = (out >= 4) & (out <= 12)  # 1920 の 4〜12px
    glow = (np.mean(g[ring]) - bgl) / max(1, (np.mean(g[line.astype(bool)]) - bgl)) if dark and ring.sum() > 50 else np.nan
    return w, glow
def de(a, b): return float(np.linalg.norm((a - b) * np.array([100 / 255, 1, 1])))
def cam(cap, t0, t1):
    # カットの 0.1→0.9 の 2 コマを直接合わせる（ORB 4000・比の検定 0.8・RANSAC 1.5px の相似）。積み上げ（kamera.py）は小さくずれが溜まるので門はこっち
    a, b = cv2.cvtColor(grab(cap, t0), cv2.COLOR_BGR2GRAY), cv2.cvtColor(grab(cap, t1), cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(4000, fastThreshold=8); m = np.zeros_like(a); m[int(540 * TOP):] = 255
    k1, d1 = orb.detectAndCompute(a, m); k2, d2 = orb.detectAndCompute(b, m)
    if d1 is None or d2 is None or len(k1) < 20 or len(k2) < 20: return (1.0, 0.0, 0.0, 0.0)
    mm = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1, d2, k=2); good = [x for x, y in (z for z in mm if len(z) == 2) if x.distance < 0.8 * y.distance]
    if len(good) < 15: return (1.0, 0.0, 0.0, 0.0)
    p1 = np.float32([k1[x.queryIdx].pt for x in good]); p2 = np.float32([k2[x.trainIdx].pt for x in good])
    M, inl = cv2.estimateAffinePartial2D(p1, p2, ransacReprojThreshold=1.5, maxIters=4000)
    if M is None or inl.sum() < 12: return (1.0, 0.0, 0.0, 0.0)
    sc = float(np.hypot(M[0, 0], M[1, 0])); rot = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    c = np.array([480, 270]); mv = M[:, :2] @ c + M[:, 2] - c
    return (sc, float(mv[0] / 960 * 100), float(mv[1] / 540 * 100), rot)
OUT = []
for i in range(len(CUT) - 1):
    nm, f0 = CUT[i]; f1_ = CUT[i + 1][1]; t0, t1 = f0 / 30, f1_ / 30; L = t1 - t0
    rows = []
    for q in (0.15, 0.35, 0.55, 0.75, 0.92):
        tr = t0 + q * L; to = r2o(tr); a, b = grab(cr, tr), grab(co, to)
        ma, bga, _ = fg(a); mb, bgb, _ = fg(b); ba, bb = box(ma), box(mb)
        wa, ga = stroke(FULL[id(cr)], bga); wb, gb = stroke(FULL[id(co)], bgb)
        al = align(a, b)
        rows.append(dict(q=q, tr=round(tr, 2), to=round(to, 2), ba=ba, bb=bb, al=al, f1=f1(edges(a), edges(b)), wa=wa, wb=wb, ga=ga, gb=gb, de_bg=de(bga, bgb)))
    ca = cam(cr, t0 + 0.1 * L, t0 + 0.9 * L); cb = cam(co, r2o(t0 + 0.1 * L), r2o(t0 + 0.9 * L))
    def med(k, j=None):
        v = [r[k][j] if j is not None and r[k] is not None else r[k] for r in rows if (r[k] is not None)]
        v = [x for x in v if x is not None and not (isinstance(x, float) and np.isnan(x))]; return float(np.median(v)) if v else np.nan
    AL = [r['al'] for r in rows if r['al'] is not None and abs(r['al'][2]) < 40]
    if AL: dx, dy, ds, rot_al = [float(np.median([x[j] for x in AL])) for j in range(4)]
    else: dx, dy, ds, rot_al = np.nan, np.nan, np.nan, np.nan
    OUT.append(dict(rot_al=rot_al, cut=nm, ref=[round(t0, 2), round(t1, 2)], ours=[round(r2o(t0), 2), round(r2o(t1), 2)], dx=dx, dy=dy, ds=ds,
                    cam_ref=ca, cam_ours=cb, f1=med('f1'), w_ref=med('wa'), w_ours=med('wb'), glow_ref=med('ga'), glow_ours=med('gb'), de_bg=med('de_bg'), rows=rows))
def J(o):
    if isinstance(o, (np.floating, np.integer)): return o.item()
    raise TypeError
json.dump(OUT, open(f'rikai/{NAME}.json', 'w'), default=J, ensure_ascii=False, indent=0)
import os
KR = json.load(open('rikai/kamera_raw.json')); KO = json.load(open(f'rikai/kamera_{NAME}.json')) if os.path.exists(f'rikai/kamera_{NAME}.json') else None
def col(ok, warn): return '🟢' if ok else ('🟡' if warn else '🔴')
L = [f'# {NAME}（{V}）カットごとの差・手本の秒→うちの秒は rikai/rf.json', '',
     '線：位置 ±2% 画面・大きさ ±3%（輪郭をぼかして ECC で合わせた相似のずれ）・カメラの寄り ±3%・流し ±2%・回り ±3°（kamera_<名>.json があれば手本と同じ道具で測った終わりの値）・形 F1 ≥0.55（0.40〜 🟡）・線の太さ ±25%・光のにじみ ±0.10・背景 ΔE ≤5（差し色は意図で除く）', '',
     '| カット | 手本(秒) | うち(秒) | 位置 dx,dy % | 大きさ % | 寄り 手本→うち | 流し 手本→うち % | 形 F1 | 線 px 手本/うち | にじみ 手本/うち | 背景 ΔE | 判定 |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
nr = ny = 0
for o in OUT:
    ca, cb = o['cam_ref'], o['cam_ours']
    if not (0.5 < ca[0] < 2): ca = (1.0, 0.0, 0.0, 0.0)
    if not (0.5 < cb[0] < 2): cb = (1.0, 0.0, 0.0, 0.0)
    sc = (cb[0] / ca[0] - 1) * 100; pan = np.hypot(cb[1] - ca[1], cb[2] - ca[2]); rot = abs(cb[3] - ca[3]) + abs(o['rot_al'] if o['rot_al'] == o['rot_al'] else 0)
    ws = (o['w_ours'] / o['w_ref'] - 1) * 100 if (o['w_ref'] == o['w_ref'] and o['w_ours'] == o['w_ours'] and o['w_ref']) else 0
    gd = abs(o['glow_ours'] - o['glow_ref']) if o['glow_ref'] == o['glow_ref'] and o['glow_ours'] == o['glow_ours'] else 0
    ck = [(abs(o['dx']) <= 2 and abs(o['dy']) <= 2, abs(o['dx']) <= 4 and abs(o['dy']) <= 4), (abs(o['ds']) <= 3, abs(o['ds']) <= 6),
          (abs(sc) <= 3 and pan <= 2 and rot <= 3, abs(sc) <= 6 and pan <= 4 and rot <= 6), (o['f1'] >= 0.55, o['f1'] >= 0.40),
          (abs(ws) <= 25, abs(ws) <= 40), (gd <= 0.10, gd <= 0.2), (o['de_bg'] <= 5, o['de_bg'] <= 10)]
    bad = [n for n, (g, w) in zip(['位置', '大きさ', 'カメラ', '形', '線', 'にじみ', '背景'], ck) if not g]
    red = [n for n, (g, w) in zip(['位置', '大きさ', 'カメラ', '形', '線', 'にじみ', '背景'], ck) if not w]
    j = '🟢' if not bad else ('🔴 ' + '・'.join(red) if red else '🟡 ' + '・'.join(bad)); nr += bool(red); ny += bool(bad and not red)
    o['judge'] = j
    L.append(f"| {o['cut']} | {o['ref'][0]}–{o['ref'][1]} | {o['ours'][0]}–{o['ours'][1]} | {o['dx']:+.1f},{o['dy']:+.1f} | {o['ds']:+.1f} | {ca[0]:.3f}→{cb[0]:.3f} | {ca[1]:+.1f},{ca[2]:+.1f}→{cb[1]:+.1f},{cb[2]:+.1f} | {o['f1']:.2f} | {o['w_ref']:.1f}/{o['w_ours']:.1f} | {o['glow_ref']:.2f}/{o['glow_ours']:.2f} | {o['de_bg']:.1f} | {j} |")
L.insert(2, f'**🔴 {nr} カット・🟡 {ny} カット・🟢 {len(OUT) - nr - ny} カット**（全 {len(OUT)} カット）')
open(f'rikai/{NAME}.md', 'w').write('\n'.join(L) + '\n'); print(f'🔴{nr} 🟡{ny} 🟢{len(OUT) - nr - ny}')
