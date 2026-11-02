"""段0 見る：画面の字を1語ずつ（出る・消えるコマ・箱・字の高さ・色・縁取り・影・光・書体の見当）。手本だけを見る。
python3 miru_moji.py <手本.mp4> <作業> [--step 2]
- 読み取り＝macOS の Vision（ocr_words.swift・1語ずつの箱）を step コマおきに → 同じ語の箱をつないで「語の列」にする
- 出る・消えるコマ＝cap_time.py と同じ型合わせ（字の線＝白黒−σ6 のぼかし・±6px・一番高い値の 60% を超えた連続・途切れ2コマまで）を、手本の一番はっきりしたコマの字を型にして全部のコマで
- 字の高さ＝インクの箱（大津の2値の少ない方・枠に触る塊は外す）の高さ÷画面の高さ
- 色＝インクの中央値・縁取り＝インクのすぐ外の輪の明るさが字とも地とも違う・影＝ずらした所が地より暗い・光＝外 4〜15px が地より明るい
- 書体の見当＝傾き（列の山が一番鋭くなるずらし角）と線の太さのむら（距離変換）。🔴見当なので作る段では当て比べ（waza.md「書体の当て比べ」）で決める
出す物：<作業>/zukan/parts/moji.json
"""
import argparse, collections, difflib, glob, json, os, subprocess, sys
import cv2, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mk

ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("w"); ap.add_argument("--step", type=int, default=2)
A = ap.parse_args(); REF = os.path.abspath(A.ref); W_ = os.path.abspath(A.w); CA = f"{W_}/zukan/cache"; P = f"{W_}/zukan/parts"
pr = mk.probe(REF); WW, HH = pr["W"], pr["H"]
T = mk.pts_table(REF, f"{CA}/pts.npy"); N = len(T); FPS = 1 / float(np.median(np.diff(T)))
OW = min(WW, 1280); OH = int(round(HH * OW / WW / 2)) * 2; K = WW / OW   # 読む絵の大きさ → 原寸へ戻す倍率
FD = f"{CA}/f"; os.makedirs(FD, exist_ok=True)
if len(glob.glob(f"{FD}/*.jpg")) < N:
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", REF, "-map", "0:v:0", "-vsync", "passthrough", "-vf", f"scale={OW}:{OH}:flags=area",
                    "-q:v", "2", "-start_number", "0", f"{FD}/%05d.jpg"], check=True)
BIN = os.path.expanduser("~/.cache/tehon-ikki-miru/ocr_words")
SRC = os.path.join(HERE, "ocr_words.swift")
if not os.path.exists(BIN) or os.path.getmtime(BIN) < os.path.getmtime(SRC):
    os.makedirs(os.path.dirname(BIN), exist_ok=True); subprocess.run(["swiftc", "-O", "-o", BIN, SRC], check=True)
raw = f"{CA}/ocr_words.tsv"
if not os.path.exists(raw):
    lst = f"{CA}/ocr_list.txt"; open(lst, "w").write("\n".join(f"{FD}/{i:05d}.jpg" for i in range(0, N, A.step)))
    with open(raw, "w") as fo: subprocess.run([BIN, lst], stdout=fo, check=True)
obs = collections.defaultdict(list)
for l in open(raw):
    p = l.rstrip("\n").split("\t")
    if len(p) < 5 or p[1] == "ERR" or not p[2]: continue
    f = int(p[0].split(".")[0]); w = p[1].strip(); conf = float(p[3])
    if conf < 0.3 or not any(ch.isalnum() for ch in w): continue
    x0, y0, x1, y1 = [int(v) for v in p[2].split(",")]
    if x1 - x0 < 3 or y1 - y0 < 4: continue
    obs[f].append(dict(w=w, b=[x0, y0, x1, y1], c=conf))


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); I = ix * iy
    return I / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - I + 1e-6)


def norm(w): return "".join(ch for ch in w.lower() if ch.isalnum())


tracks = []; active = []
for f in sorted(obs):
    nxt = []
    for o in obs[f]:
        best = None
        for t in active:
            if f - t["last"] > 3 * A.step: continue
            io = iou(t["b"], o["b"]); sim = difflib.SequenceMatcher(None, norm(t["w"]), norm(o["w"])).ratio()
            # 🔒11/2 手本X（字 68%・位置 42%）：カメラで寄る UI の字は箱が動いて IoU が落ち、同じ語が 4〜5 本の列に割れた（Podcasts 10-14／20-41／49-60／61-62）
            #   → 動きを許す：①前の2つの観測から次の箱を予測した IoU ②中心のずれが字の高さの 1.5倍以内・大きさ 0.7〜1.4倍・字が 0.6 以上似とる
            pb = t.get("pb"); iop = iou(pb, o["b"]) if pb else 0.0
            h_ = max(1, t["b"][3] - t["b"][1]); cx, cy = (t["b"][0] + t["b"][2]) / 2, (t["b"][1] + t["b"][3]) / 2; ox, oy = (o["b"][0] + o["b"][2]) / 2, (o["b"][1] + o["b"][3]) / 2
            ratio = (o["b"][3] - o["b"][1]) / h_
            near = ((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5 <= 1.5 * h_ and 0.7 <= ratio <= 1.4 and sim >= 0.6
            if (io > 0.4 and sim >= 0.5) or io > 0.75 or (iop > 0.4 and sim >= 0.5) or near:
                sc = max(io, iop) + sim
                if best is None or sc > best[0]: best = (sc, t)
        if best:
            t = best[1]; pb_ = [2 * b1 - b0 for b0, b1 in zip(t["b"], o["b"])] if f - t["last"] <= A.step else None   # 次の箱の予測＝今の箱＋（今−前）
            t["seen"].append((f, o)); t["last"] = f; t["b"] = o["b"]; t["pb"] = pb_
        else:
            t = dict(seen=[(f, o)], last=f, b=o["b"], w=o["w"]); tracks.append(t); active.append(t)
    active = [t for t in active if f - t["last"] <= 3 * A.step]
tracks = [t for t in tracks if len(t["seen"]) >= 1]

IMC = {}


def line_img(f):
    if f not in IMC:
        if len(IMC) > 400: IMC.clear()
        g = cv2.imread(f"{FD}/{f:05d}.jpg", cv2.IMREAD_GRAYSCALE).astype(np.float32)
        IMC[f] = (g, np.abs(g - cv2.GaussianBlur(g, (0, 0), 6)))   # cap_time の「字の線」（白い字も黒い字も拾うように絶対値）
    return IMC[f]


def refine(t):
    """cap_time と同じ：型＝一番はっきりしたコマの字・±6px・60% を超えた連続（途切れ2コマまで）"""
    fs = [s[0] for s in t["seen"]]
    cnt = collections.Counter(norm(s[1]["w"]) for s in t["seen"]); top = cnt.most_common(1)[0][0]
    cands = [s for s in t["seen"] if norm(s[1]["w"]) == top]
    pk_f, pk_o = max(cands, key=lambda s: s[1]["c"] * ((s[1]["b"][2] - s[1]["b"][0]) * (s[1]["b"][3] - s[1]["b"][1])) ** 0.25)
    x0, y0, x1, y1 = pk_o["b"]; x0, y0 = max(0, x0 - 2), max(0, y0 - 2); x1, y1 = min(OW, x1 + 2), min(OH, y1 + 2)
    tpl = line_img(pk_f)[1][y0:y1, x0:x1]
    if tpl.size < 20 or tpl.std() < 1: return None
    lo, hi = max(0, min(fs) - 2 * A.step - 4), min(N - 1, max(fs) + 2 * A.step + 4)
    fr = list(range(lo, hi + 1)); sc = []; en = []; thr = 0.75 * float(np.percentile(tpl, 90))   # 「はっきり白い」線の画素＝型の濃い所の 3/4 以上
    for f in fr:
        s_ = line_img(f)[1]; wx0, wy0 = max(0, x0 - 6), max(0, y0 - 6); win = s_[wy0:y1 + 6, wx0:x1 + 6]
        if win.shape[0] < tpl.shape[0] or win.shape[1] < tpl.shape[1]: sc.append(0.0); en.append(0.0); continue
        sc.append(float(cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED).max())); en.append(float((win >= thr).sum()))   # en＝はっきり白い画素の数（薄く出とる途中は少ない）
    sc = np.array(sc); en = np.array(en); pk = fr.index(pk_f)
    # 🔒11/2 手本S（初見 字の出る・消える 1/14）：相関は明るさの倍率に強い＝薄く出始めた・消えかけのコマまで「出とる」と見て、出るが 4コマ早く・消えるが 5コマ遅かった（12本全部）
    #   → 「はっきり白い画素の数が、落ち着いた量の半分以上」のコマだけ出とる（答えの作り方「白い画素が落ち着いた量の半分以上」と同じ物差し。線の量の平均やと薄い途中を数えてまだ 2コマ早かった）
    # 🔒11/2（2回目）：出る・消えるは2つの物差しで出す。f0/f1＝「見え始め〜見え終わり」（相関 60%・前と同じ。r2・51・手本J の答えはこれ）／f0_koi/f1_koi＝「はっきり見える」（はっきり白い画素の数が落ち着いた量の半分以上。手本S の答え・人が「出た」と見る所）
    #   はっきりの方だけにすると、字が小さく出て大きくなる・縁取りの字（r2 の buy 48→58・51 の句が 1〜3コマ遅れ）で見え始めを落とす＝両方を持ち、採点はどちらかが ±1 で当たり
    def hani(on, force=False):
        on = on.copy()
        if force: on[pk] = True
        i0 = pk
        while i0 > 0 and (on[i0 - 1] or (i0 > 1 and on[i0 - 2]) or (i0 > 2 and on[i0 - 3])): i0 -= 1
        i1 = pk
        while i1 < len(fr) - 1 and (on[i1 + 1] or (i1 < len(fr) - 2 and on[i1 + 2]) or (i1 < len(fr) - 3 and on[i1 + 3])): i1 += 1
        while not on[i0] and i0 < pk: i0 += 1
        while not on[i1] and i1 > pk: i1 -= 1
        return i0, i1
    on0 = sc > 0.6 * sc.max(); i0, i1 = hani(on0); f0_, f1_ = fr[i0], fr[i1]
    seen0, seen1 = min(fs), max(fs)   # Vision が読めたコマは「出とる」証拠＝型合わせの範囲はそれより内に縮めん
    if seen0 < f0_: f0_ = seen0
    if seen1 > f1_: f1_ = seen1
    solid = sc > 0.8 * sc.max(); plat = float(np.median(en[solid])) if solid.any() else float(en.max())
    k0, k1 = hani(on0 & (en >= 0.5 * plat), force=True); f0k, f1k = fr[k0], fr[k1]
    if seen0 < f0k and en[fr.index(seen0)] >= 0.5 * plat: f0k = seen0
    if seen1 > f1k and en[fr.index(seen1)] >= 0.5 * plat: f1k = seen1
    f0k, f1k = max(f0k, f0_), min(f1k, f1_)
    return dict(f0=f0_, f1=f1_, f0_koi=f0k, f1_koi=f1k, mieta0=seen0, mieta1=seen1, peak=pk_f, ocr_box=pk_o["b"], w=pk_o["w"], score=round(float(sc.max()), 3),
                edge=(i0 == 0, i1 == len(fr) - 1), sc=sc)


def style(f, box):
    """インク・色・縁取り・影・光・傾き（原寸のコマで）"""
    im = cv2.imread(f"{FD}/{f:05d}.jpg"); pad = 18
    x0, y0, x1, y1 = box; X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(OW, x1 + pad), min(OH, y1 + pad)
    R = im[Y0:Y1, X0:X1]; g = cv2.cvtColor(R, cv2.COLOR_BGR2GRAY)
    inner = np.zeros(g.shape, bool); inner[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = True
    gi = g[inner]
    th, _ = cv2.threshold(gi.reshape(1, -1).astype(np.uint8), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bright = (g > th) & inner; dark = (g <= th) & inner
    # 地＝箱の外の輪の中央値に近い方は地。字はもう一方
    ring = (~inner); bgv = float(np.median(g[ring])) if ring.any() else float(np.median(gi))
    ink = bright if abs(float(np.median(g[bright])) - bgv) > abs(float(np.median(g[dark])) - bgv) else dark
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
    keep = np.zeros_like(ink)
    for i in range(1, n):
        if st[i, 4] >= 3: keep |= lab == i
    ink = keep
    if ink.sum() < 10: return None
    ys, xs = np.where(ink); ib = [int(xs.min() + X0), int(ys.min() + Y0), int(xs.max() + X0 + 1), int(ys.max() + Y0 + 1)]
    inkc = np.median(R[ink], 0); inkl = float(np.median(g[ink]))
    dil = lambda k: cv2.dilate(ink.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))) > 0
    far = ~dil(16); bgl = float(np.median(g[far])) if far.any() else bgv
    stroke = None; prev = ink
    for k in range(1, 7):
        d = dil(k); r_ = d & ~prev; prev = d
        if r_.sum() < 5: break
        rl = float(np.median(g[r_]))
        if abs(rl - inkl) > 60 and abs(rl - bgl) > 30:
            stroke = dict(px=round(k * K, 1), color="#%02x%02x%02x" % tuple(int(v) for v in np.median(R[r_], 0)[::-1]))
        else: break
    shadow = None; d3 = dil(1)
    for dx, dy in ((2, 2), (3, 3), (4, 4), (0, 3), (3, 0), (-2, 2), (2, -2)):
        M = np.float32([[1, 0, dx], [0, 1, dy]]); sh = cv2.warpAffine(ink.astype(np.uint8), M, (g.shape[1], g.shape[0])) > 0
        z = sh & ~d3
        if z.sum() > 10 and float(np.mean(g[z])) < bgl - 25: shadow = dict(dx=round(dx * K, 1), dy=round(dy * K, 1), kurasa=round(bgl - float(np.mean(g[z])), 1)); break
    gl = dil(15) & ~dil(4)
    glow = round(float(np.mean(g[gl])) - bgl, 1) if gl.any() else 0.0
    # 傾き（ずらして列の山が一番鋭い角）
    best = (0, -1.0)
    for ang in range(-24, 25, 2):
        Ms = np.float32([[1, np.tan(np.radians(ang)), -np.tan(np.radians(ang)) * g.shape[0] / 2], [0, 1, 0]])
        sh = cv2.warpAffine(ink.astype(np.float32), Ms, (g.shape[1], g.shape[0]))
        v = float((sh.sum(0) ** 2).sum())
        if v > best[1]: best = (ang, v)
    dt = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 3); sk = dt[(dt > 0) & (dt >= cv2.dilate(dt, np.ones((3, 3))) - 1e-3)]
    mura = float(sk.std() / (sk.mean() + 1e-6)) if sk.size > 5 else 0.0
    slant = -best[0]
    font = "斜体（イタリック・セリフ系の見当）" if abs(slant) >= 7 else ("明朝・セリフ系の見当" if mura > 0.45 else "ゴシック系の見当")
    return dict(ink_box=[int(v * K) for v in ib], color="#%02x%02x%02x" % tuple(int(v) for v in inkc[::-1]), polarity="白っぽい字" if inkl > bgl else "黒っぽい字",
                bg_lum=round(bgl, 1), stroke=stroke, shadow=shadow, glow=glow, slant_deg=slant, line_mura=round(mura, 2), font_guess=font)


words = []
for t in tracks:
    r = refine(t)
    if not r: continue
    if r["f1"] - r["f0"] < 1 and len(t["seen"]) < 2: continue
    stl = style(r["peak"], r["ocr_box"]) or {}
    ib = stl.get("ink_box") or [int(v * K) for v in r["ocr_box"]]
    words.append(dict(w=r["w"], f0=int(r["f0"]), f1=int(r["f1"]), t0=round(float(T[r["f0"]]), 4), t1=round(float(T[min(N - 1, r["f1"])]), 4),
                      f0_koi=int(r["f0_koi"]), f1_koi=int(r["f1_koi"]), t0_koi=round(float(T[r["f0_koi"]]), 4), t1_koi=round(float(T[min(N - 1, r["f1_koi"])]), 4),
                      mieta0=int(r["mieta0"]), mieta1=int(r["mieta1"]),
                      box_px=ib, box_pct=[round(100 * ib[0] / WW, 2), round(100 * ib[1] / HH, 2), round(100 * (ib[2] - ib[0]) / WW, 2), round(100 * (ib[3] - ib[1]) / HH, 2)],
                      moji_takasa_pct=round(100 * (ib[3] - ib[1]) / HH, 2), ocr_box_px=[int(v * K) for v in r["ocr_box"]],
                      score=r["score"], kenshutsu=len(t["seen"]), **{k: v for k, v in stl.items() if k != "ink_box"}))
# 🔒11/2 手本S：同じ字が同じ場所で続いとるのに、Vision の読みが揺れる（もし365日→もし、5日）・数コマ読み落とすと列が切れ、題 138〜1641 が 131-388／382-1076／1068-1168／1154-1646 の4本になった
#   → 同じ字（0.8 以上似とる）・同じ箱（IoU≥0.5）で、コマが重なる（か1コマ以内で続く）列は1本につなぐ。間が空いた物はつながん（手本J の点滅＝消えてまた出るは別の列のまま）
words.sort(key=lambda x: (x["f0"], x["box_px"][1], x["box_px"][0])); stitched = []
for x in words:
    m = next((y for y in reversed(stitched) if x["f0"] <= y["f1"] + 1 and x["mieta0"] - y["mieta1"] <= 12 and iou(y["box_px"], x["box_px"]) >= 0.5
              and difflib.SequenceMatcher(None, norm(y["w"]), norm(x["w"])).ratio() >= 0.8), None)   # Vision が読めたコマも 12コマ（0.4秒）以内で続く物だけ＝次の板の同じ語（r2）はつながん
    if m is None: stitched.append(x); continue
    f0_, f1_ = min(m["f0"], x["f0"]), max(m["f1"], x["f1"]); k0_, k1_ = min(m["f0_koi"], x["f0_koi"]), max(m["f1_koi"], x["f1_koi"])
    s0_, s1_ = min(m["mieta0"], x["mieta0"]), max(m["mieta1"], x["mieta1"]); n_ = m["kenshutsu"] + x["kenshutsu"]; k_ = m.get("tsunagi", 0) + 1
    if x["kenshutsu"] > m["kenshutsu"]: stitched[stitched.index(m)] = m = x   # 見えたコマが多い方の字・箱・見た目を残す
    m["f0"], m["f1"], m["f0_koi"], m["f1_koi"], m["mieta0"], m["mieta1"], m["kenshutsu"], m["tsunagi"] = f0_, f1_, k0_, k1_, s0_, s1_, n_, k_
    m["t0"], m["t1"] = round(float(T[f0_]), 4), round(float(T[min(N - 1, f1_)]), 4)
    m["t0_koi"], m["t1_koi"] = round(float(T[k0_]), 4), round(float(T[min(N - 1, k1_)]), 4)
words = stitched
words.sort(key=lambda x: (x["f0"], x["box_px"][1], x["box_px"][0]))
for i, x in enumerate(words): x["i"] = i
json.dump(dict(step=A.step, read_w=OW, n_frames_read=len(range(0, N, A.step)), words=words,
               rule="出る・消える＝cap_time の型合わせ（60%・±6px・途切れ2コマ）／箱＝インクの箱（原寸の px）"), open(f"{P}/moji.json", "w"), ensure_ascii=False)
print("字", len(words), "語（読んだコマ", len(range(0, N, A.step)), "）")
