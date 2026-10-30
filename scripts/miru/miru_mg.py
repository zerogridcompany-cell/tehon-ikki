"""段0 見る：作り手が上に重ねた飾り（MG・HUD・ロゴ・札）を手本だけから探す。
python3 miru_mg.py <手本.mp4> <作業>
- HUD（追跡の飾り）＝hud_measure.py と同じ色の決まり：赤＝R>150・G<90・B<110・R−G>80 の細長い切れ端／緑＝G>150・R<130・B<130 の小さい点。全部のコマ（幅 1280 の絵）
- 動かんロゴ＝カットの中で絵は動いとる（真ん中の揺れ>6）のに、四隅の形が動かん（揺れ<2 かつ線がある）所
- 札・通知・吹き出し＝真ん中のコマの「平らな色の四角」（面積 1〜60%・四角さ 0.85 以上・字が中にある）。最初と最後のコマで位置を比べて動きを出す
出す物：<作業>/zukan/parts/mg.json
"""
import glob, json, os, sys
import cv2, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mk

REF = os.path.abspath(sys.argv[1]); W_ = os.path.abspath(sys.argv[2]); CA = f"{W_}/zukan/cache"; P = f"{W_}/zukan/parts"
pr = mk.probe(REF); WW, HH = pr["W"], pr["H"]
T = mk.pts_table(REF, f"{CA}/pts.npy"); N = len(T); FPS = 1 / float(np.median(np.diff(T)))
F = mk.small(REF, f"{CA}/small.npy")
cuts = json.load(open(f"{P}/cuts.json"))
UG = {u["i"]: u for u in json.load(open(f"{P}/ugoki.json"))}
moji = json.load(open(f"{P}/moji.json"))["words"] if os.path.exists(f"{P}/moji.json") else []
FD = f"{CA}/f"; has_jpg = len(glob.glob(f"{FD}/*.jpg")) >= N
pct = lambda b, w, h: [round(100 * b[0] / w, 2), round(100 * b[1] / h, 2), round(100 * (b[2] - b[0]) / w, 2), round(100 * (b[3] - b[1]) / h, 2)]

# ── HUD ──
hud_rows = []
for f in range(N):
    im = cv2.imread(f"{FD}/{f:05d}.jpg") if has_jpg else cv2.resize(np.ascontiguousarray(F[f]), (1280, 720))
    h, w = im.shape[:2]; b, g, r = [im[..., i].astype(int) for i in range(3)]
    red = ((r > 150) & (g < 90) & (b < 110) & (r - g > 80)).astype(np.uint8)
    grn = ((g > 150) & (r < 130) & (b < 130) & (g - r > 60)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(red, 8)
    lines = [st[i] for i in range(1, n) if st[i, 4] >= 8 and (st[i, 2] >= 6 * st[i, 3] or st[i, 3] >= 6 * st[i, 2])]
    n2, _, st2, cen2 = cv2.connectedComponentsWithStats(grn, 8)
    dots = [cen2[i] for i in range(1, n2) if 6 <= st2[i, 4] <= 200]
    if (len(lines) >= 2 and 1 <= len(dots) <= 60) or len(lines) >= 6:   # 赤い線だけ・緑だけ（景色の緑）は飾りにせん
        xs = [s_[0] for s_ in lines] + [d[0] for d in dots]; ys = [s_[1] for s_ in lines] + [d[1] for d in dots]
        xe = [s_[0] + s_[2] for s_ in lines] + [d[0] for d in dots]; ye = [s_[1] + s_[3] for s_ in lines] + [d[1] for d in dots]
        hud_rows.append(dict(f=f, lines=len(lines), dots=len(dots), box=pct([min(xs), min(ys), max(xe), max(ye)], w, h)))
hud = []
for r_ in hud_rows:
    if hud and r_["f"] - hud[-1]["f1"] <= 3:
        hud[-1]["f1"] = r_["f"]; hud[-1]["rows"].append(r_)
    else: hud.append(dict(kind="HUD（赤い線・緑の点）", f0=r_["f"], f1=r_["f"], rows=[r_]))
for x in hud:
    rs = x.pop("rows"); x["n"] = len(rs); x["lines_max"] = max(r_["lines"] for r_ in rs); x["dots_max"] = max(r_["dots"] for r_ in rs)
    bx = np.array([r_["box"] for r_ in rs]); x["box_pct"] = [round(float(np.min(bx[:, 0])), 1), round(float(np.min(bx[:, 1])), 1),
                                                           round(float(np.max(bx[:, 0] + bx[:, 2]) - np.min(bx[:, 0])), 1), round(float(np.max(bx[:, 1] + bx[:, 3]) - np.min(bx[:, 1])), 1)]
    c = bx[:, :2] + bx[:, 2:] / 2; x["ugoki_pct_s"] = round(float(np.hypot(*(c[-1] - c[0])) / max(1, (x["f1"] - x["f0"]) / FPS)), 1)
    x["t0"], x["t1"] = round(float(T[x["f0"]]), 3), round(float(T[x["f1"]]), 3)
hud = [x for x in hud if x["n"] >= 3]

# ── 動かんロゴ（四隅）・札 ──
G = np.array([cv2.cvtColor(np.ascontiguousarray(f), cv2.COLOR_BGR2GRAY) for f in F]).astype(np.float32)
sh, sw = G.shape[1:]
corners = {"左上": (0, 0), "右上": (sw - int(sw * .25), 0), "左下": (0, sh - int(sh * .22)), "右下": (sw - int(sw * .25), sh - int(sh * .22))}
logo, fuda, per_cut = [], [], {}
for c in cuts:
    f0, f1 = c["f0"], c["f1"]; out = []
    if f1 - f0 >= 8:
        S = G[f0:f1].std(0); center = float(np.median(S[sh // 4:3 * sh // 4, sw // 4:3 * sw // 4]))
        ug = UG.get(c["i"], {}).get("ugoki", {}); gmove = ug.get("G") or 0
        if center > 6 and gmove >= 0.5:   # 下の絵がカメラごと動いとるのに四隅が止まっとる＝上に重ねた物（止まったカメラの景色と分ける）
            mean = G[f0:f1].mean(0); edge = np.abs(cv2.Sobel(mean, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(mean, cv2.CV_32F, 0, 1))
            for nm, (x0, y0) in corners.items():
                cw, ch = int(sw * .25), int(sh * .22)
                m = ((S[y0:y0 + ch, x0:x0 + cw] < 2.0) & (edge[y0:y0 + ch, x0:x0 + cw] > 40)).astype(np.uint8)
                m = cv2.dilate(m, np.ones((3, 3), np.uint8))
                n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
                big = [st[i] for i in range(1, n) if st[i, 4] >= 12 and max(st[i, 2], st[i, 3]) <= 5 * min(st[i, 2], st[i, 3])
                       and st[i, 0] > 1 and st[i, 1] > 1 and st[i, 0] + st[i, 2] < cw - 1 and st[i, 1] + st[i, 3] < ch - 1]   # 細長い線（帯の縁）・角に触る物は外す
                if big:
                    xs0 = min(s_[0] for s_ in big) + x0; ys0 = min(s_[1] for s_ in big) + y0
                    xs1 = max(s_[0] + s_[2] for s_ in big) + x0; ys1 = max(s_[1] + s_[3] for s_ in big) + y0
                    e = dict(kind="動かんロゴ・名札", where=nm, cut=c["i"], f0=f0, f1=f1 - 1, box_pct=pct([xs0, ys0, xs1, ys1], sw, sh), center_yure=round(center, 1), camera_G=gmove)
                    out.append(e)
            if 1 <= len(out) <= 2: logo.extend(out)   # 四隅ぜんぶ＝枠・帯の形（ロゴやない）
            else: out = []
    # 札（平らな色の四角＋中に字）
    mid = f0 + (f1 - f0) // 2; im = np.ascontiguousarray(F[mid]).astype(np.float32)
    loc = cv2.blur((im - cv2.blur(im, (5, 5))) ** 2, (5, 5)).sum(2) ** 0.5
    flat = (loc < 4).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(flat, 4)
    ws = [z for z in moji if z["f0"] <= mid <= z["f1"]]
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if not (0.01 * sw * sh <= a <= 0.6 * sw * sh): continue
        if a / (w * h) < 0.85 or (x <= 1 and x + w >= sw - 1) or (y <= 1 and y + h >= sh - 1): continue
        inside = [z for z in ws if x <= (z["box_px"][0] + z["box_px"][2]) / 2 * sw / WW <= x + w and y <= (z["box_px"][1] + z["box_px"][3]) / 2 * sh / HH <= y + h]
        col = np.median(np.ascontiguousarray(F[mid])[lab == i], 0)
        # 動き：最初と最後のコマで同じ四角を探す
        tpl = G[mid][y:y + h, x:x + w]; mv = []
        for ff in (f0, max(f0, f1 - 1)):
            r_ = cv2.matchTemplate(G[ff], tpl, cv2.TM_CCOEFF_NORMED); _, v, _, p = cv2.minMaxLoc(r_); mv.append((p[0] - x, p[1] - y, round(float(v), 2)))
        if not inside and a < 0.04 * sw * sh: continue
        e = dict(kind="札・通知・吹き出し（字の入った色の板）" if inside else "色の板", cut=c["i"], f=mid, box_pct=pct([x, y, x + w, y + h], sw, sh),
                 color="#%02x%02x%02x" % tuple(int(v) for v in col[::-1]), words=[z["w"] for z in inside][:12],
                 ugoki_px=[[round(m_[0] * WW / sw), round(m_[1] * HH / sh), m_[2]] for m_ in mv])
        fuda.append(e); out.append(e)
    per_cut[c["i"]] = out
json.dump(dict(hud=hud, logo=logo, fuda=fuda, per_cut=per_cut, hud_frames=len(hud_rows),
               rule="HUD＝hud_measure の色・3コマ以上続く／ロゴ＝四隅の揺れ<2・真ん中>6／札＝平ら（局所の揺れ<4）の四角 1〜60%・四角さ≥0.85"),
          open(f"{P}/mg.json", "w"), ensure_ascii=False)
print("HUD", len(hud), "区間・ロゴ", len(logo), "・札/板", len(fuda))
