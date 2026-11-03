"""段0 見るの足し（11/2 tehonJ で見えてなかった字の4つ）：zukan.json に足す
  moji_track＝同じ所に続けて読めた語を1本の字にまとめる（読み違い SANDY/COY も BODY と同じ場所・同じ間なら1本）
  ・tenmetsu＝字が出とる間に消えるコマ（字の箱の輪郭の形を1コマずつ字の見本と比べる＝反転しても輪郭は同じ）
  ・atsumi＝字に厚み・影（字の輪郭を少しずらした所に、もう1本の輪郭がそろって出る）
  ・ushiro＝字が人の後ろ（macOS Vision で人を切り抜き、人の上に字の墨が無いのに、人の外には墨がある）
  hanten＝反転の切り替わり（前のコマと明るさの形が逆に並ぶ＝相関が −0.3 未満）
使い方：python3 moji_plus.py <作業>（run.sh miru が zukan_plus の後に回す）"""
import json, os, sys, subprocess, difflib, shutil
import numpy as np, cv2
W_ = sys.argv[1]; ZP = f'{W_}/zukan/zukan.json'; Z = json.load(open(ZP)); REF = Z['meta']['ref']
pr = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', REF], capture_output=True, text=True).stdout.strip().split(',')
VW, VH = int(pr[0]), int(pr[1]); SW = 480; SH = int(round(SW * VH / VW / 2) * 2); K = VW / SW
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', REF, '-vf', f'scale={SW}:{SH},format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
g = np.frombuffer(raw, np.uint8).reshape(-1, SH, SW); N = len(g)
CUT = shutil.which('cutout') or os.path.expanduser('~/bin/cutout')
TMP = f'{W_}/zukan/moji_plus'; os.makedirs(TMP, exist_ok=True)

# ---- 反転の切り替わり
sm = np.stack([cv2.resize(x, (96, int(round(96 * SH / SW))), interpolation=cv2.INTER_AREA).ravel() for x in g]).astype(np.float32)
hanten = []
for k in range(1, N):
    a, b = sm[k - 1] - sm[k - 1].mean(), sm[k] - sm[k].mean()
    r = float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6))
    if r < -0.3 and abs(sm[k].mean() - sm[k - 1].mean()) > 25: hanten.append(dict(f=k, r=round(r, 2)))
Z['hanten'] = hanten

# ---- 字を1本にまとめる
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); I = ix * iy
    return I / max(1e-6, (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - I)
W = [w for w in Z.get('moji', {}).get('words', []) if w.get('moji_takasa_pct', 0) >= 4 and len(w['w']) >= 1]
W.sort(key=lambda w: w['f0']); tr = []
for w in W:
    sim = lambda a, b: difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
    t = next((t for t in tr if w['f0'] - t['f1'] <= 8 and ((iou(w['box_px'], t['box']) >= 0.6 and min(w.get('kenshutsu', 1), t['best'].get('kenshutsu', 1)) <= 3) or (iou(w['box_px'], t['box']) >= 0.3 and sim(w['w'], t['best']['w']) >= 0.4))), None)   # 別の字（前の字と箱が重なる・どっちも何回も読めた語）を1本にせん＝LOOKS→PRETTY（11/2）
    if t:
        t['ws'].append(w); t['f1'] = max(t['f1'], w['f1'])
        if w.get('kenshutsu', 0) > t['best'].get('kenshutsu', 0): t['best'] = w; t['box'] = w['box_px']
    else: tr.append(dict(ws=[w], f0=w['f0'], f1=w['f1'], best=w, box=w['box_px']))

def edge(img):
    gx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=3); m = np.sqrt(gx * gx + gy * gy)
    return m - m.mean()
def ncc(a, b): return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6))
def frame_full(f):
    p = f'{TMP}/f{f}.png'
    if not os.path.exists(p): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', REF, '-vf', f"select='eq(n\\,{f})'", '-vsync', '0', '-frames:v', '1', p], check=True)
    return p

out = []
for t in tr:
    b = t['best']; x0, y0, x1, y1 = [int(round(v / K)) for v in t['box']]; x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(SW, x1), min(SH, y1)
    if x1 - x0 < 6 or y1 - y0 < 4: continue
    fm = (b['f0'] + b['f1']) // 2; T = edge(g[fm, y0:y1, x0:x1])
    # 点滅：見本の輪郭と1コマずつ比べる。続けて出とる隣のコマとも比べる（寄り・回りで形が少しずつ変わる）
    A, B = max(0, t['f0'] - 10), min(N - 1, t['f1'] + 10); sc = {}
    for f in range(A, B + 1): sc[f] = ncc(edge(g[f, y0:y1, x0:x1]), T)
    core = [sc[f] for f in range(t['f0'], t['f1'] + 1)]; hi = float(np.percentile(core, 75))
    th = max(0.15, 0.2 * hi); on = {f for f in sc if sc[f] >= th}   # 消えたコマは 0 前後・出とるコマは寄り・揺れ・反転でも 0.2 以上（tehonJ 11/2）
    for f in sorted(sc):   # 隣の出とるコマとよく似とる＝出とる（ゆっくり変わる字を落とさん）
        if f not in on and (f - 1) in on and ncc(edge(g[f, y0:y1, x0:x1]), edge(g[f - 1, y0:y1, x0:x1])) >= 0.75 and sc[f] >= 0.6 * th: on.add(f)
    seq = sorted(on)
    if not seq: continue
    # 出る〜消える＝見本のコマを含む塊。間が6コマより長い抜けは別の字（点滅は短い）
    runs = []; s = seq[0]; p = seq[0]
    for f in seq[1:]:
        if f - p > 6: runs.append((s, p)); s = f
        p = f
    runs.append((s, p)); r0, r1 = next((r for r in runs if r[0] <= fm <= r[1]), (t['f0'], t['f1']))
    kesu = [f for f in range(r0, r1 + 1) if f not in on]
    # 厚み・影：字の墨（見本の大きいコマ）の輪郭をずらした所に、もう1本の輪郭がそろうか
    img = cv2.imread(frame_full(fm), cv2.IMREAD_GRAYSCALE); X0, Y0, X1, Y1 = [max(0, int(v)) for v in t['box']]
    pad = int(0.15 * (Y1 - Y0)); cx0, cy0, cx1, cy1 = max(0, X0 - pad), max(0, Y0 - pad), min(VW, X1 + pad), min(VH, Y1 + pad)
    c = img[cy0:cy1, cx0:cx1]; col = b.get('color') or next((w['color'] for w in t['ws'] if w.get('color')), None)
    tl = int(cv2.cvtColor(np.uint8([[[int(col[5:7], 16), int(col[3:5], 16), int(col[1:3], 16)]]]), cv2.COLOR_BGR2GRAY)[0, 0]) if col else int(np.percentile(c, 95))
    I = (np.abs(c.astype(int) - tl) < 30).astype(np.uint8)
    I = cv2.morphologyEx(I, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    O = cv2.dilate(I, np.ones((3, 3), np.uint8)) - I
    E = cv2.Canny(cv2.GaussianBlur(c, (3, 3), 0), 40, 100) > 0; E &= cv2.dilate(I, np.ones((5, 5), np.uint8)) == 0
    hgt = Y1 - Y0; best = (0, 0, 0); vals = []
    if O.sum() > 50:
        R = max(6, int(0.12 * hgt))
        for dy in range(-R, R + 1, 2):
            for dx in range(-R, R + 1, 2):
                if dx * dx + dy * dy < max(16, (0.03 * hgt) ** 2): continue
                S_ = np.roll(np.roll(O, dy, 0), dx, 1) > 0; v = float((E & S_).sum() / O.sum()); vals.append(v)
                if v > best[0]: best = (v, dx, dy)
    atsu = dict(peak=round(best[0], 3), dx=best[1], dy=best[2], base=round(float(np.median(vals)) if vals else 0, 3))
    atsu['hi'] = round(atsu['peak'] / max(1e-3, atsu['base']), 2)
    # 人の後ろ：Vision で切り抜いた人の上に、字の墨が無い（人の外の墨と比べて）
    mp = f'{TMP}/m{fm}.png'; ushi = None
    if os.path.exists(CUT):
        if not os.path.exists(mp): subprocess.run([CUT, frame_full(fm), mp], capture_output=True)
        if os.path.exists(mp):
            al = cv2.imread(mp, cv2.IMREAD_UNCHANGED)
            if al is not None and al.ndim == 3 and al.shape[2] == 4:
                M = al[cy0:cy1, cx0:cx1, 3] > 128; inb = np.zeros_like(M); inb[Y0 - cy0:Y1 - cy0, X0 - cx0:X1 - cx0] = True
                Mi = M & inb; Mo = (~M) & inb
                ov = float(Mi.sum() / max(1, inb.sum())); din = float(I[Mi].mean()) if Mi.sum() else 0; dout = float(I[Mo].mean()) if Mo.sum() else 0
                ushi = dict(kasanari=round(ov, 3), sumi_naka=round(din, 3), sumi_soto=round(dout, 3), hi=round(din / max(1e-3, dout), 2))
    out.append(dict(w=b['w'], f0=int(r0), f1=int(r1), box_px=t['box'], kesu=kesu, mihon=fm, atsumi=atsu, ushiro=ushi,
                    mieta1=int(max(w.get('mieta1', w['f1']) for w in t['ws'])),   # Vision がこの字を最後に読めたコマ（11/2 tehonX：点滅＝その後また見えた時だけ）
                    yomi=sorted({w['w'] for w in t['ws']})[:6]))
for o in out:
    a = o['atsumi']; o['atsumi_ari'] = bool(a['hi'] >= 2.2 and a['peak'] >= 0.12)
    u = o['ushiro']; o['ushiro_ari'] = bool(u and u['kasanari'] >= 0.08 and u['hi'] < 0.35 and u['sumi_soto'] >= 0.05)
Z['moji_track'] = out
# 切り替えの見直し：絵は同じで ①白黒が入れ替わっただけ（反転）②大きい字が出た・消えただけ（点滅） は切り替えと数えん＝前のカットにつなぐ
def same_pic(f, moji_ok=True):
    a = cv2.resize(g[f - 1], (192, int(round(192 * SH / SW))), interpolation=cv2.INTER_AREA).astype(np.float32); b = cv2.resize(g[f], a.shape[::-1], interpolation=cv2.INTER_AREA).astype(np.float32)
    m = np.ones(a.shape, bool); kk = VW / 192; txt = False
    for o in out:
        if o['f0'] - 2 <= f <= o['f1'] + 2 and (o['box_px'][3] - o['box_px'][1]) >= 0.08 * VH:
            x0, y0, x1, y1 = [int(v / kk) for v in o['box_px']]; m[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2] = False; txt = True
    def r(mm):
        u = a[mm] - a[mm].mean(); v = b[mm] - b[mm].mean(); return float((u * v).sum() / (np.sqrt((u * u).sum() * (v * v).sum()) + 1e-6))
    rw = r(np.ones(a.shape, bool))
    if rw <= -0.72:   # 反転＝絵は同じで白黒だけ逆。2コマ先も同じ絵が続く（白か黒かは問わん）。光って次の場面へ行く切り替え（r2）は2コマ先が別の絵（11/2）
        c2 = cv2.resize(g[min(N - 1, f + 2)], a.shape[::-1], interpolation=cv2.INTER_AREA).astype(np.float32)
        u = a - a.mean(); v = c2 - c2.mean(); r2_ = float((u * v).sum() / (np.sqrt((u * u).sum() * (v * v).sum()) + 1e-6))
        if abs(r2_) >= 0.6: return 'hanten'
    # 🔒11/2 tehonX：点滅＝「消えてまた出る」＝その字を Vision が f より後にも読めた時だけ（mieta1 ≥ f）。字の列は輪郭の相関 0.15 で別の字（In real-time）の上まで伸びる＝「And react」が 266 の板替えで消えた所を点滅と見てカットを消した
    same_word = any(o['f0'] < f <= o['f1'] and o.get('mieta1', o['f1']) >= f and (f in o['kesu'] or (f - 1) in o['kesu']) for o in out)   # 同じ字が消えてまた出る所だけ（字が別の字に替わる板の切り替え＝tehonR は切り替えのまま）
    if moji_ok and txt and same_word and m.mean() >= 0.15:
        if r(m) >= 0.9 or float(np.abs(a[m] - b[m]).mean()) < 5: return 'tenmetsu'
    return None
C = Z.get('cuts', [])
if C:
    nc = [dict(C[0])]
    for c in C[1:]:
        why = same_pic(c['f0'], c.get('kirikae', {}).get('kind') not in ('fade_in', 'dissolve', 'zoom', 'whip', 'flash')) if c['f0'] >= 1 else None   # 反転は種類を問わず（「見る」は反転を whip・flash と見とった）・点滅は普通の切り替えだけ
        if why: nc[-1]['f1'] = c['f1']; nc[-1].setdefault('tsunagi', []).append([c['f0'], why])
        else: nc.append(dict(c))
    Z['cuts_mae'] = [c['f0'] for c in C]; Z['cuts'] = nc
Z['moji_track_rule'] = '点滅＝輪郭の相関が字の 75%点の 2割（0.15 以上）を下回るコマ／厚み＝輪郭をずらした所の縁の一番が並みの 2.2倍以上・0.12 以上／後ろ＝Vision の人と字の箱が 8%以上重なり、人の上の墨が人の外の 35% 未満'
json.dump(Z, open(ZP, 'w'), ensure_ascii=False)
for f in os.listdir(TMP):
    if f.startswith('f'): os.remove(f'{TMP}/{f}')
print(f"反転 {len(hanten)}・字 {len(out)} 本（点滅あり {sum(bool(o['kesu']) for o in out)}・厚み {sum(o['atsumi_ari'] for o in out)}・後ろ {sum(o['ushiro_ari'] for o in out)}）")
