"""段0 見る（miru）：手本を1回だけ見て、カットごとの全部の数字を図鑑（zukan.json）にする。作る段はこの数字だけを読む。
python3 miru.py <手本.mp4> <作業> [--redo 部品,部品] [--no-oto] [--no-moji]
部品（<作業>/zukan/parts/*.json に残す＝もう一度回すと済んだ物は飛ばす）：
  kihon  大きさ・fps・コマの時刻表（pts）・抜けたコマ
  cuts   カット（ffmpeg scene 0.3＝門の mane_check と同じ／eye_prep の scene 0.3／中身の入れ替わり＝色の山 0.35 超＋形の相関 0.7 未満）
         ＋切り替えの種類（hard・flash・dissolve・whip・glitch・zoom-through）
  ugoki  カメラ（相似の鎖＝cam_chain の est）・動き G/L/D（motion_kind.measure）・一枚絵か本物の動画か（still_check.newness）
  mikake 色（Lab）・コントラスト・彩度・明るさの曲線・粒（grain_need の tn）・鋭さ（sharp_check）・暗い縁と色収差（ca_vig）・網点（ht_scan）・顔と主役（face_index）
  moji   画面の字（miru_moji.py＝Vision で1語ずつ→出る・消えるコマを cap_time の型合わせで詰める）
  mg     飾り（赤い線と緑の点＝hud_measure の色・角の動かんロゴ・色の板の札）
  oto    音（miru_oto.py＝hako.py の7つの箱・whisper の1語ずつ・強い低音・Shazam・拍の網・LUFS）
  awase  カットの頭が何に合わせとるか（小節の頭・1拍・半拍・4分の1拍・言葉の頭・効果音・強い低音＋ずれのコマ数・区間ごとの決まり＝kouzou.py と同じ「たまたまの1.5倍」）
最後に zukan.json・設計図.md・一覧.html を書く（miru_report.py）。門＝check_zukan.py
"""
import argparse, json, os, re, subprocess, sys, time
import cv2, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.join(HERE, "..", "tools")
sys.path.insert(0, HERE); sys.path.insert(0, TOOLS)
import mk
from mk import nashi

ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("w")
ap.add_argument("--redo", default=""); ap.add_argument("--no-oto", action="store_true"); ap.add_argument("--no-moji", action="store_true")
A = ap.parse_args()
REF = os.path.abspath(A.ref); W_ = os.path.abspath(A.w); Z = f"{W_}/zukan"; P = f"{Z}/parts"; CA = f"{Z}/cache"
for d in (Z, P, CA): os.makedirs(d, exist_ok=True)
REDO = set(x for x in A.redo.split(",") if x)
PY = sys.executable


def step(name):
    p = f"{P}/{name}.json"
    if name not in REDO and os.path.exists(p):
        return json.load(open(p)), True
    return p, False


def save(p, d):
    json.dump(d, open(p, "w"), ensure_ascii=False)
    return d


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ───────── kihon ─────────
pr = mk.probe(REF); WW, HH = pr["W"], pr["H"]
T = mk.pts_table(REF, f"{CA}/pts.npy")
F = mk.small(REF, f"{CA}/small.npy")
N = len(F); FPS = 1.0 / float(np.median(np.diff(T))) if N > 1 else pr["fps"]
dt = np.diff(T); gaps = [int(i + 1) for i in np.where(dt > 1.5 / FPS)[0]]; back = [int(i + 1) for i in np.where(dt <= 0)[0]]
kihon = dict(ref=REF, W=WW, H=HH, fps=round(FPS, 4), r_frame_rate=pr["r_frame_rate"], avg_frame_rate=pr["avg_frame_rate"], codec=pr["codec"],
             frames=N, dur=round(float(T[-1] + 1 / FPS), 3), pts_gaps=gaps, pts_back=back,
             note="コマ番号＝手本のそのままのコマ（passthrough）。秒＝pts。抜け・戻りのコマは pts_gaps・pts_back")
save(f"{P}/kihon.json", kihon)
log("手本", f"{WW}x{HH}", f"{FPS:.3f}fps", N, "コマ", "抜け", gaps, "戻り", back)
G = np.array([cv2.cvtColor(np.ascontiguousarray(f), cv2.COLOR_BGR2GRAY) for f in F])
LUM = G.reshape(N, -1).mean(1)


def ft(f):
    return float(T[min(max(f, 0), N - 1)])


# ───────── cuts ─────────
cuts, done = step("cuts")
if not done:
    Y = G.astype(np.int16)
    m = np.r_[0, np.abs(np.diff(Y, axis=0)).mean((1, 2))]
    s = np.r_[0, [min(m[i], abs(m[i] - m[i - 1])) / 100 for i in range(1, N)]]          # eye_prep と同じ scene
    H_ = []
    for f in F:
        h = cv2.calcHist([cv2.cvtColor(cv2.resize(np.ascontiguousarray(f), (160, 90))[:63], cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256])
        H_.append(cv2.normalize(h, h).flatten())
    hb = np.r_[0, [cv2.compareHist(H_[i - 1], H_[i], cv2.HISTCMP_BHATTACHARYYA) for i in range(1, N)]]   # e_picture と同じ色の山
    Zs = np.array([cv2.resize(y.astype(np.float32), (80, 45)) for y in Y]); Zs = (Zs - Zs.mean((1, 2), keepdims=True)) / (Zs.std((1, 2), keepdims=True) + 1e-3)
    cc = np.r_[1, (Zs[1:] * Zs[:-1]).mean((1, 2))]
    e = subprocess.run(["ffmpeg", "-hide_banner", "-i", REF, "-vf", "select='gt(scene,0.3)',metadata=print", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    gate = sorted({int(np.argmin(np.abs(T - float(x)))) for x in re.findall(r"pts_time:([\d.]+)", e)})
    src = {}
    for i in gate: src.setdefault(i, []).append("ffmpeg")
    # 絵の中だけ（黒い地・枠を外す）で前後の形と色を比べる＝縦型の小窓の手本で「同じ人・同じ色の別カット」を拾う（10/30 mm4u：670・802・810・859 を見落としとった）
    def box_pair(i, j):
        a, b_ = G[i].astype(np.float32), G[j].astype(np.float32); mk_ = np.maximum(a, b_) > 25; ys, xs = np.where(mk_)
        if len(ys) < 50: return 1.0, 0.0, 0.0
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        if mk_.mean() < 0.05: return 1.0, 0.0, 0.0   # 暗い地に字だけ（51 の 1421＝2.5%・1430＝4.5%・明るい所が 5% 未満）は絵の替わりにせん
        A_ = cv2.resize(a[y0:y1, x0:x1], (40, 40)); B2 = cv2.resize(b_[y0:y1, x0:x1], (40, 40))
        A_ = (A_ - A_.mean()) / (A_.std() + 1e-3); B2 = (B2 - B2.mean()) / (B2.std() + 1e-3)
        h1 = cv2.calcHist([cv2.cvtColor(np.ascontiguousarray(F[i][y0:y1, x0:x1]), cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256])
        h2 = cv2.calcHist([cv2.cvtColor(np.ascontiguousarray(F[j][y0:y1, x0:x1]), cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256])
        return float((A_ * B2).mean()), float(cv2.compareHist(cv2.normalize(h1, h1), cv2.normalize(h2, h2), cv2.HISTCMP_BHATTACHARYYA)), float(np.abs(a - b_)[mk_].mean())
    ccb = np.ones(N); hbb = np.zeros(N); db = np.zeros(N)
    for i in range(1, N): ccb[i], hbb[i], db[i] = box_pair(i - 1, i)
    def is_flash(i):   # 前と後の両方より明るい山（光るだけ）
        lo_ = LUM[max(0, i - 6):max(1, i - 1)]; hi_ = LUM[min(N - 1, i + 2):min(N, i + 7)]
        return len(lo_) and len(hi_) and LUM[i] - max(np.median(lo_), np.median(hi_)) > 30
    for i in range(2, N - 2):
        steady = ccb[i - 1] >= 0.75 and ccb[i + 1] >= 0.75
        if steady and not is_flash(i) and db[i] > 35 and (ccb[i] < 0.45 or (hbb[i] > 0.45 and db[i] > 40)): src.setdefault(i, []).append("中身")   # 差 35 以下＝MG の中で動いとるだけ（51 の 141〜168・396・890）
        # 1コマだけ挟まる替わり目（859：前→1コマ→後）
        elif i + 2 < N and ccb[i - 1] >= 0.75 and ccb[i + 2] >= 0.75 and ccb[i] < 0.45 and db[i] > 35 and box_pair(i - 1, i + 1)[0] < 0.45 and not is_flash(i): src.setdefault(i, []).append("中身1コマ")
    for i in range(1, N):
        if s[i] > 0.3: src.setdefault(i, []).append("eye")
        if hb[i] > 0.35 and cc[i] < 0.7 and s[i] > 0.2: src.setdefault(i, []).append("入れ替わり")
    # 🔒11/2 手本X（暗い MG・初見でカット 0/5）：暗い地で板ごと替わる切り替え。scene・中身（db>35）・入れ替わり（s>0.2）は全部「絶対の明るさ」のしきい＝平均の明るさ 15〜25 の手本では山が出ん
    #   → 明るい画素（>60）が前のコマと重ならん（消えた割合か現れた割合が 0.8 超・明るい画素が画面の 0.3% 以上）のに、動きを許した相関（前の真ん中 60% を今の中で探す）が 0.5 未満＝板替え。速い流れ（70〜75）は相関 0.95・打ち込みの字（244）は重なる、で外れる
    MB = G > 60; inter_ = (MB[1:] & MB[:-1]).sum((1, 2)); gone_ = np.r_[0, 1 - inter_ / np.maximum(1, MB[:-1].sum((1, 2)))]; appe_ = np.r_[0, 1 - inter_ / np.maximum(1, MB[1:].sum((1, 2)))]; area_ = MB.mean((1, 2))
    def shiftcorr(i):
        a, b_ = G[i - 1].astype(np.float32), G[i].astype(np.float32); h, w = a.shape; y0, x0 = int(h * 0.2), int(w * 0.2); tpl = a[y0:h - y0, x0:w - x0]
        if tpl.std() < 1 or b_.std() < 1: return 0.0
        return float(cv2.matchTemplate(b_, tpl, cv2.TM_CCOEFF_NORMED).max())
    for i in range(1, N):
        if i not in src and (gone_[i] > 0.8 or appe_[i] > 0.8) and max(area_[i - 1], area_[i]) >= 0.003 and shiftcorr(i) < 0.5: src.setdefault(i, []).append("板替え")
    # 同じ絵の中で光っただけ（320・494）は切れ目にせん。門（ffmpeg）の切れ目は消さん
    NEWR = {"中身", "中身1コマ", "板替え"}
    for i in list(src):
        if i not in gate and 2 <= i < N - 3 and is_flash(i) and box_pair(i - 2, i + 2)[0] >= 0.75: src.pop(i)
    # 2コマ以内に並んだ切れ目は前の1つに（859・860）
    for i in sorted(src):
        if i in src and set(src[i]) <= NEWR and (any(j in src for j in (i - 1, i - 2)) or any(j in src and not set(src[j]) <= NEWR for j in (i + 1, i + 2))): src.pop(i)   # 新しい規則だけの切れ目が前からの切れ目の2コマ以内なら新しい方を外す（前からの切れ目は消さん）
    b = [0] + sorted(src) + [N]
    cuts = []
    for k in range(len(b) - 1):
        f0, f1 = b[k], b[k + 1]
        cuts.append(dict(i=k, f0=f0, f1=f1, n=f1 - f0, t0=round(ft(f0), 4), t1=round(ft(f1) if f1 < N else kihon["dur"], 4),
                         gate=f0 in gate, src=src.get(f0, ["頭"]), scene=round(float(s[f0]), 3), hist=round(float(hb[f0]), 3), corr=round(float(cc[f0]), 3)))
    save(f"{CA}/cutfeat.json", dict(s=s.round(4).tolist(), m=m.round(2).tolist(), hb=hb.round(4).tolist(), cc=cc.round(3).tolist(), ccb=ccb.round(3).tolist(), hbb=hbb.round(3).tolist(), db=db.round(1).tolist(), gate=gate))
    save(f"{P}/cuts.json", cuts)
log("カット", len(cuts), "（門の ffmpeg と同じ物", sum(c["gate"] for c in cuts), "）")
CF = json.load(open(f"{CA}/cutfeat.json"))


# ───────── ugoki（カメラ・動き・静止） ─────────
import motion_kind, still_check   # 測りの中身はそのまま使う（320x180・字幕の帯を外す）
ugoki, done = step("ugoki")
if not done:
    MASK = motion_kind.MASK

    def pair_sim(a, b):
        """a→b の相似（cam_chain の est と同じ：特徴点→LK→estimateAffinePartial2D）。返り＝(dx, dy, 倍率, 回転°, 点の数)"""
        pt = cv2.goodFeaturesToTrack(a, 400, 0.01, 6, mask=MASK)
        if pt is None or len(pt) < 10: return None
        q, st, _ = cv2.calcOpticalFlowPyrLK(a, b, pt, None, winSize=(21, 21), maxLevel=3); st = st.ravel() == 1
        if st.sum() < 10: return None
        M, inl = cv2.estimateAffinePartial2D(pt[st], q[st], method=cv2.RANSAC, ransacReprojThreshold=1.0)
        if M is None or inl is None or inl.sum() < 8: return None
        c = np.array([mk.SW / 2, mk.SH / 2]); mv = M[:, :2] @ c + M[:, 2] - c
        return float(mv[0]), float(mv[1]), float(np.hypot(M[0, 0], M[1, 0])), float(np.degrees(np.arctan2(M[1, 0], M[0, 0]))), int(inl.sum())

    ugoki = []
    kx = WW / mk.SW
    for c in cuts:
        f0, f1 = c["f0"], c["f1"]; r = dict(i=c["i"])
        mm = motion_kind.measure(G, f0, f1) if f1 - f0 >= 5 else None
        r["ugoki"] = dict(G=mm["G"], L=mm["L"], D=mm["D"], n=mm["n"]) if mm else nashi(f"{f1 - f0}コマ＝5コマ未満は motion_kind で測らん", G=None)
        # 静止（一枚絵を動かしただけか）＝still_check の newness
        ks = [k for k in range(f0, f1 - 1)]
        nv = [still_check.newness(G[k], G[k + 1]) for k in ks]
        keep = [v for v in nv if v < still_check.SW]
        Nn = round(float(np.median(keep)), 2) if keep else None
        sw = int(sum(v >= still_check.SW for v in nv))
        moving = mm is not None and (mm["G"] >= 0.5 or mm["D"] >= 1.0)
        if Nn is None: kind = "1コマ" if f1 - f0 <= 1 else "替わるだけ"
        elif Nn >= 2.0: kind = "本物の動画"
        elif moving: kind = "一枚絵を動かしとる"
        else: kind = "止め絵"
        r["seishi"] = dict(kind=kind, N=Nn if Nn is not None else nashi(f"となりの組 {len(nv)}・続く組 0（全部が替わり N≥35 か 1コマ）"), sw=sw, pairs=len(nv), rule="N≥2.0＝本物の動画（still_check）・N<2 で動いとる＝一枚絵を動かしとる")
        # カメラ
        pp = [pair_sim(G[k], G[k + 1]) for k in ks if nv[ks.index(k)] < still_check.SW] if ks else []
        pp = [x for x in pp if x]
        if len(pp) >= 2:
            a = np.array(pp)
            # 外れの組を外す（1組だけ特徴点が別の物に飛ぶ＝51 の 2390 で振り 1083px/s・正解 9）
            def okm(v):
                md = np.median(v); mad = np.median(np.abs(v - md)) + 1e-6; return np.abs(v - md) <= 6 * mad + 0.5
            keepm = okm(a[:, 0]) & okm(a[:, 1]) & okm(np.log(a[:, 2]) * 100)
            if keepm.sum() >= 2: a = a[keepm]
            dx, dy = a[:, 0] * kx, a[:, 1] * kx
            zoom = float((np.exp(np.mean(np.log(a[:, 2])) * FPS) - 1) * 100)
            panx, pany = float(np.mean(dx) * FPS), float(np.mean(dy) * FPS)
            rot = float(np.mean(a[:, 3]) * FPS)
            sm = lambda v: np.convolve(v, np.ones(5) / 5, mode="same") if len(v) >= 5 else np.full(len(v), v.mean())
            shake = float(np.sqrt(np.mean((dx - sm(dx)) ** 2 + (dy - sm(dy)) ** 2)))
            still_pairs = int(np.sum((np.abs(dx) < 0.3 * kx) & (np.abs(dy) < 0.3 * kx) & (np.abs(a[:, 2] - 1) < 0.002)))
            kinds = []
            if abs(zoom) >= 2: kinds.append("寄り" if zoom > 0 else "引き")
            if abs(panx) >= 0.02 * WW: kinds.append("横の振り（右→左）" if panx < 0 else "横の振り（左→右）")
            if abs(pany) >= 0.02 * HH: kinds.append("縦の振り（下→上）" if pany < 0 else "縦の振り（上→下）")
            if abs(rot) >= 1.0: kinds.append("回る")
            if shake >= 3.0: kinds.append("揺れ")
            elif shake >= 0.7: kinds.append("手持ち")
            if not kinds: kinds = ["止まり"]
            r["kamera"] = dict(kind=kinds, zoom_pct_s=round(zoom, 2), pan_px_s=[round(panx, 1), round(pany, 1)], rot_deg_s=round(rot, 2),
                               shake_px=round(shake, 2), still_pairs=still_pairs, pairs=len(pp),
                               dx_px=[round(float(x), 2) for x in dx], dy_px=[round(float(x), 2) for x in dy], s=[round(float(x), 5) for x in a[:, 2]])
        else:
            r["kamera"] = dict(kind=["測れん"], zoom_pct_s=0.0, pan_px_s=[0.0, 0.0], rot_deg_s=0.0, shake_px=0.0, pairs=len(pp),
                               konkyo=f"続いた組 {len(pp)}（特徴点が10未満か {f1 - f0}コマ）")
        ugoki.append(r)
    save(f"{P}/ugoki.json", ugoki)
log("動き・カメラ・静止 済み")
UG = {u["i"]: u for u in ugoki}


# ───────── kirikae（切り替えの種類） ─────────
kirikae, done = step("kirikae")
if not done:
    def grad_ratio(g):
        gx = np.abs(cv2.Sobel(g.astype(np.float32), cv2.CV_32F, 1, 0)).mean(); gy = np.abs(cv2.Sobel(g.astype(np.float32), cv2.CV_32F, 0, 1)).mean()
        return float(gy / (gx + 1e-3)), float(gx + gy)

    def rb_shift(f):
        r_ = f[..., 2].astype(np.float32); b_ = f[..., 0].astype(np.float32)
        (sx, sy), _ = cv2.phaseCorrelate(r_ - r_.mean(), b_ - b_.mean()); return float(np.hypot(sx, sy))

    kirikae = []
    for c in cuts:
        f = c["f0"]; r = dict(i=c["i"])
        if f == 0:
            r["kind"] = "頭"; r["konkyo"] = "動画の1コマ目"; kirikae.append(r); continue
        lo = [x for x in list(range(max(0, f - 7), f - 1)) + list(range(f + 2, min(N, f + 8)))]
        base = float(np.median(LUM[lo])) if lo else float(LUM[f])
        pk = max(range(max(0, f - 1), min(N, f + 2)), key=lambda x: LUM[x])
        jump = float(LUM[pk] - base)
        why = dict(lum_jump=round(jump, 1), lum_peak=round(float(LUM[pk]), 1))
        # ① フラッシュ（e_picture：明るさ +35 → 2コマで戻る・flash_auto：>150）
        bb_ = float(np.median(LUM[max(0, f - 7):max(1, f - 1)])) if f > 1 else float(LUM[pk]); ba_ = float(np.median(LUM[min(N - 1, pk + 2):min(N, pk + 8)])) if pk + 2 < N else float(LUM[pk])
        why["over_both"] = round(float(LUM[pk]) - max(bb_, ba_), 1)
        # 前と後の両方より明るい山だけ（暗い→明るいの普通のカットを光るにせん・r2：74→下の数）
        if jump > 35 and float(LUM[pk]) - max(bb_, ba_) > 30:
            r.update(kind="flash", frame=int(pk), **why); kirikae.append(r); continue
        # ② 溶け（前後のコマの重ね＝α が途中の値でずっと残りが小さい）
        A_ = G[max(0, f - 7)].astype(np.float32); B_ = G[min(N - 1, f + 6)].astype(np.float32); dAB = float(np.abs(A_ - B_).mean())
        mix = []
        if dAB > 12:
            for j in range(max(0, f - 6), min(N, f + 6)):
                x = G[j].astype(np.float32); d_ = (A_ - B_).ravel(); al = float(np.clip(np.dot(x.ravel() - B_.ravel(), d_) / (np.dot(d_, d_) + 1e-6), 0, 1))
                res = float(np.abs(x - (al * A_ + (1 - al) * B_)).mean())
                if 0.12 < al < 0.88 and res < 0.35 * dAB: mix.append((j, round(al, 2)))
        if len(mix) >= 2:
            r.update(kind="dissolve", frames=[m_[0] for m_ in mix], alpha=[m_[1] for m_ in mix], dAB=round(dAB, 1), **why); kirikae.append(r); continue
        # ③ 色ずれ（グリッチ）＝赤と青のずれが切れ目だけ大きい
        sh_cut = max(rb_shift(F[x]) for x in (f - 1, f) if 0 <= x < N)
        inner = [rb_shift(F[x]) for x in (c["f0"] + c["n"] // 2,) if x < N]
        if sh_cut >= 1.5 and sh_cut > 3 * max(0.3, max(inner)):
            r.update(kind="glitch", rb_shift=round(sh_cut, 2), **why); kirikae.append(r); continue
        # ④ 振り（ホイップ）＝切れ目のコマが一方向に流れとる（縦÷横の線の比）・⑤ 寄り抜け＝切れ目の手前で急に大きく
        rat = [grad_ratio(G[x]) for x in (f - 1, f) if 0 <= x < N]
        ratio_ = max((x[0] if x[0] >= 1 else 1 / max(x[0], 1e-3)) for x in rat)
        prev = UG.get(c["i"] - 1, {}).get("kamera", {}); sc = prev.get("s", [])[-3:]
        zth = float(np.prod(sc)) if sc else 1.0
        # 振りは「切れ目のコマだけ」流れとる時だけ（縦長の小窓は線の向きがいつも偏る＝mm4u で 20 中 15 が whip になっとった）
        nb_ = [grad_ratio(G[x]) for x in list(range(max(0, f - 6), max(0, f - 2))) + list(range(min(N, f + 3), min(N, f + 7)))]
        base_r = float(np.median([(x[0] if x[0] >= 1 else 1 / max(x[0], 1e-3)) for x in nb_])) if nb_ else 1.0
        why["flow_base"] = round(base_r, 2)
        if ratio_ >= 2.5 and ratio_ >= 1.8 * base_r:
            r.update(kind="whip", flow_ratio=round(ratio_, 2), dir="横" if any(x[0] >= 2.5 for x in rat) else "縦", **why)
        elif zth >= 1.15 or zth <= 0.87:
            r.update(kind="zoom-through", zoom_last3=round(zth, 3), **why)
        else:
            r.update(kind="hard", flow_ratio=round(ratio_, 2), rb_shift=round(sh_cut, 2), mix_frames=len(mix), zoom_last3=round(zth, 3), **why)
        kirikae.append(r)
    # カットの中の光るだけのコマ（カットにならん flash）も拾う
    inner_flash = []
    for f in range(2, N - 2):
        base = float(np.median(LUM[[max(0, f - 4), max(0, f - 3), min(N - 1, f + 3), min(N - 1, f + 4)]]))
        if LUM[f] - base > 35 and LUM[f] >= LUM[f - 1] and LUM[f] >= LUM[f + 1] and LUM[f] >= 100 and min(LUM[f + 1], LUM[min(N - 1, f + 2)]) < LUM[f] - 20:   # 明るい（≥100）・1〜2コマで戻る（r2：67→40・当たり同じ）
            inner_flash.append(dict(f=f, jump=round(float(LUM[f] - base), 1), lum=round(float(LUM[f]), 1)))
    save(f"{P}/kirikae.json", kirikae := dict(cuts=kirikae, flash_frames=inner_flash))
log("切り替え 済み")
KK = {k["i"]: k for k in kirikae["cuts"]}


# ───────── mikake（見た目・主役・顔）＝原寸のコマで ─────────
mikake, done = step("mikake")
if not done:
    import ca_vig
    import mediapipe as mp
    FD = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.6)
    need = {}
    for c in cuts:
        f0, f1 = c["f0"], c["f1"]; mid = f0 + (f1 - f0) // 2
        need[c["i"]] = sorted({f0, mid, max(f0, f1 - 1), min(f1 - 1, mid + 1)})
    allf = sorted({x for v in need.values() for x in v})
    log("原寸のコマを読む", len(allf))
    NAT = mk.native(REF, allf, WW, HH)
    yy, xx = np.mgrid[0:HH, 0:WW]; rr = (((xx - WW / 2) / (WW / 2)) ** 2 + ((yy - HH / 2) / (HH / 2)) ** 2)
    capband = np.zeros((HH, WW), bool); capband[int(HH * .416):int(HH * .583)] = True

    def lab(img):
        L = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
        return L[..., 0] * 100 / 255, L[..., 1] - 128, L[..., 2] - 128

    def lap(img):   # sharp_check と同じ（字幕の帯と端 16px を外す）
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float64); L = cv2.Laplacian(g, cv2.CV_64F)[16:-16, 16:-16]
        m = ~capband[16:-16, 16:-16]; return float(L[m].var())

    def ht_power(img):   # ht_scan と同じ（左上の窓の周波数の山÷中央値）＝周期 2〜6px を見る
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        y0, x0 = int(HH * 0.06), int(WW * 0.05); g = g[y0:y0 + 256, x0:x0 + 512]
        Fq = np.abs(np.fft.fft2(g - g.mean())); h, ww = Fq.shape; med = np.median(Fq) + 1e-6; best = (0.0, None)
        for per in np.arange(2.2, 6.01, 0.1):
            fx, fy = int(round(ww / per)), int(round(h / per))
            if fx < 2 or fy < 2: continue
            v = float(max(Fq[fy - 1:fy + 2, fx - 1:fx + 2].max(), Fq[fy - 1:fy + 2, ww - fx - 1:ww - fx + 2].max()) / med)
            if v > best[0]: best = (v, round(float(per), 2))
        return best

    def vignette(img):
        L = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), max(4, WW / 50)) + 1
        ok = (~capband) & (L > 6); X = np.stack([np.ones(ok.sum()), rr[ok], rr[ok] ** 2], 1)
        cf = np.linalg.lstsq(X, L[ok], rcond=None)[0]
        edge = cf[0] + cf[1] * 1.0 + cf[2] * 1.0
        return float(1 - edge / max(cf[0], 1e-3))

    def faces(img):
        im = cv2.resize(img, (640, int(round(640 * HH / WW))))
        d = FD.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)); out = []
        for det in (d.detections or []):
            bb = det.location_data.relative_bounding_box
            out.append(dict(cx=round(100 * (bb.xmin + bb.width / 2), 1), cy=round(100 * (bb.ymin + bb.height / 2), 1), h=round(100 * bb.height, 1), score=round(float(det.score[0]), 2)))
        return sorted(out, key=lambda x: -x["h"])

    def content_box(img):
        """絵の範囲（平らな帯・黒い縁を除いた所）と主役の箱（線の強さの 70% が入る箱）＝％"""
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        cs, rs = g.std(0), g.std(1)
        cols = np.where(cs > 6)[0]; rows = np.where(rs > 6)[0]
        if len(cols) == 0 or len(rows) == 0: return None, None
        box = [cols[0], rows[0], cols[-1] + 1, rows[-1] + 1]
        e = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1)); e[capband] = 0
        e = cv2.GaussianBlur(e, (0, 0), 3); tot = e.sum() + 1e-6
        cx_, cy_ = np.cumsum(e.sum(0)) / tot, np.cumsum(e.sum(1)) / tot
        sb = [int(np.searchsorted(cx_, .15)), int(np.searchsorted(cy_, .15)), int(np.searchsorted(cx_, .85)), int(np.searchsorted(cy_, .85))]
        pc = lambda b: dict(x=round(100 * b[0] / WW, 1), y=round(100 * b[1] / HH, 1), w=round(100 * (b[2] - b[0]) / WW, 1), h=round(100 * (b[3] - b[1]) / HH, 1))
        return pc(box), pc(sb)

    mikake = []
    for c in cuts:
        fs = [NAT[x] for x in need[c["i"]] if x in NAT]
        if not fs: mikake.append(dict(i=c["i"], err="原寸のコマが読めん")); continue
        f0, f1 = c["f0"], c["f1"]; mid = f0 + (f1 - f0) // 2
        im = NAT.get(mid, fs[len(fs) // 2])
        L, a_, b_ = lab(im); m = ~capband
        Ls = L[m]
        tone = [round(float(np.percentile(Ls, q)), 1) for q in (1, 5, 25, 50, 75, 95, 99)]
        chroma = np.hypot(a_[m], b_[m])
        # 粒＝grain_need の tn（となりのコマの差から 3px より大きい形を引いた物の標準偏差）
        g1 = NAT.get(mid + 1)
        if g1 is not None and mid + 1 < f1:
            d = cv2.cvtColor(g1, cv2.COLOR_BGR2GRAY).astype(float) - cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(float)
            grain = round(float((d - cv2.GaussianBlur(d, (0, 0), 3)).std()), 2)
        else: grain = None
        sharp = round(float(np.median([lap(x) for x in fs])), 1)
        hp, hper = ht_power(im)
        sm_ = cv2.resize(im, (1280, int(round(1280 * HH / WW / 2)) * 2)) if WW != 1280 else im
        try:
            ca_vig.W, ca_vig.H = sm_.shape[1], sm_.shape[0]
            kr, kb = ca_vig.ca_measure([sm_])
        except Exception as ex: kr, kb = None, None
        vg = vignette(im)
        fc = [faces(x) for x in fs]
        fbest = max(fc, key=lambda v: (len(v), v[0]["h"] if v else 0))
        cb, sb = content_box(im)
        row = dict(i=c["i"], frames=need[c["i"]],
                   iro=dict(L=round(float(Ls.mean()), 1), a=round(float(a_[m].mean()), 1), b=round(float(b_[m].mean()), 1),
                            contrast=round(float(Ls.std()), 1), saido=round(float(chroma.mean()), 1), tone=tone,
                            bgr=[round(float(v), 1) for v in im[m].reshape(-1, 3).mean(0)]),
                   tsubu=grain if grain is not None else nashi(f"{f1 - f0}コマ＝となりのコマが無い", grain_px=None),
                   surudosa=sharp,
                   boke=("ぼけ" if sharp < 30 else "やわらか" if sharp < 120 else "くっきり"),
                   kumi=dict(power=round(hp, 1), period_px=hper if hper else nashi(f"山の強さ {hp:.1f}＝周期 2.2〜6px に山なし"), ari=bool(hp > 40), rule="ht_scan：山÷中央値 >40 で網点あり"),
                   shuushuu=dict(kr=kr, kb=kb, ari=bool(kr is not None and max(abs(kr), abs(kb)) >= 0.002), rule="ca_vig の倍率（±0.002 以上で色収差あり）"),
                   fuchi=dict(kurasa=round(vg, 3), ari=bool(vg >= 0.15), rule="真ん中から縁へ 15% 以上暗い＝暗い縁"),
                   kao=fbest if fbest else nashi(f"顔 0（{len(fs)}コマを mediapipe・確かさ0.6）"),
                   e_hani=cb if cb else nashi("全部平ら（列の散らばり 6 未満）"),
                   shuyaku=(dict(kind="顔", **fbest[0]) if fbest else (dict(kind="線の強い所（70%の箱）", **sb) if sb else nashi("線の強さの合計 0（全部平ら）"))))
        mikake.append(row)
    save(f"{P}/mikake.json", mikake)
log("見た目 済み")


# ───────── moji（画面の字） ─────────
if not A.no_moji:
    if "moji" in REDO or not os.path.exists(f"{P}/moji.json"):
        subprocess.run([PY, os.path.join(HERE, "miru_moji.py"), REF, W_], check=True)
    log("字 済み")

# ───────── mg（飾り） ─────────
mg, done = step("mg")
if not done and os.path.exists(os.path.join(HERE, "miru_mg.py")):
    subprocess.run([PY, os.path.join(HERE, "miru_mg.py"), REF, W_], check=True)
    mg = json.load(open(f"{P}/mg.json"))
log("飾り 済み")

# ───────── oto（音） ─────────
if not A.no_oto:
    if "oto" in REDO or not os.path.exists(f"{P}/oto.json"):
        subprocess.run([PY, os.path.join(HERE, "miru_oto.py"), REF, W_], check=True)
    log("音 済み")

# ───────── 組み立て＋awase ─────────
if os.path.exists(os.path.join(HERE, "miru_kumi.py")): subprocess.run([PY, os.path.join(HERE, "miru_kumi.py"), W_], check=True)
