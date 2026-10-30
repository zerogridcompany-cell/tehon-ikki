"""全カットの「写真の大きさ・位置」を特徴点（SIFT）で数字にする（10/28 r2：依頼者3回目「写真の大きさが違う・数字で出して0になるまで」）。
python3 size_sift.py <作業> <書き出し.mp4> [--out shirabe/大きさ表.json] [--ids 1,2]
- カットごとに 3コマ（25・50・75%）。手本とうちの白黒 960 幅・字幕の帯（y 300〜400/720）は外す
- 特徴点を比べて（比 0.75）RANSAC の相似（拡大・回転・移動）＝うち→手本。目印 15 以上のコマだけ・中央値
- 出す値：s＝手本の大きさ÷うち（1.00 が正しい・1.05＝うちが5%小さい）・dx/dy＝画面の真ん中がずれとる px（1280 幅・＋は手本が右/下）・rot（度）・inl（目印）
- 判定：|s−1|≤0.01 かつ |dx|,|dy|≤4 で ✅。目印が足らんカットは「測れん」（中身が別物＝代わりの映像・生成）
"""
import argparse, glob, json, os, subprocess
import cv2, numpy as np
W, H, w = 1280, 720, 960; k = W / w; h = int(H / k)
sift = cv2.SIFT_create(4000); bf = cv2.BFMatcher()


def grab(p, want):
    """動画を1回だけ頭から読んで、要るコマだけ取っとく"""
    cap = cv2.VideoCapture(p); out = {}; n = 0; mx = max(want)
    while n <= mx:
        ok, f = cap.read()
        if not ok: break
        if n in want: out[n] = cv2.cvtColor(cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        n += 1
    return out


def meas(a, b):
    m = np.ones_like(a) * 255; m[int(300 / k):int(400 / k)] = 0
    ka, da = sift.detectAndCompute(a, m); kb, db = sift.detectAndCompute(b, m)
    if da is None or db is None or len(ka) < 10 or len(kb) < 10: return None
    mm = [x for x, y in (p for p in bf.knnMatch(db, da, k=2) if len(p) == 2) if x.distance < 0.75 * y.distance]
    if len(mm) < 10: return None
    src = np.float32([kb[x.queryIdx].pt for x in mm]); dst = np.float32([ka[x.trainIdx].pt for x in mm])
    A, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3)
    if A is None: return None
    n = int(inl.sum())
    if n < 15: return None
    s = float(np.hypot(A[0, 0], A[1, 0]))
    if s < 0.2 or s > 5: return None
    rot = float(np.degrees(np.arctan2(A[1, 0], A[0, 0])))
    c = np.array([w / 2, h / 2]); cd = A[:, :2] @ c + A[:, 2] - c   # うちの真ん中が手本でどこへ行くか
    return s, cd[0] * k, cd[1] * k, rot, n, A   # s＝手本÷うち（A はうち→手本・10/28 1/s は逆やった）


def meas_ncc(a, b):
    """2つ目の測り方：両方ぼかして、うちを 0.60〜1.60 倍（0.01刻み・480幅）→ 一番の近くを 0.002刻み・960幅で詰める。真ん中の 60% を手本の中で一番合う所に置く"""
    def run(ww, scs, blur):
        f = ww / w
        A = cv2.GaussianBlur(cv2.resize(a, None, fx=f, fy=f), (0, 0), blur).astype(np.float32)
        B = cv2.GaussianBlur(cv2.resize(b, None, fx=f, fy=f), (0, 0), blur).astype(np.float32)
        hh, wb = B.shape; best = None
        for sc in scs:
            Bs = cv2.resize(B, None, fx=sc, fy=sc); cy, cx = Bs.shape[0] / 2, Bs.shape[1] / 2
            th, tw = int(hh * 0.6), int(wb * 0.6); y0, x0 = int(cy - th / 2), int(cx - tw / 2)
            T = Bs[y0:y0 + th, x0:x0 + tw]
            if T.std() < 3: continue
            r = cv2.matchTemplate(A, T, cv2.TM_CCOEFF_NORMED); _, mv, _, ml = cv2.minMaxLoc(r)
            px, py = float(ml[0]), float(ml[1])
            if 0 < ml[0] < r.shape[1] - 1:   # 山の頂点を2次で詰める（1px 未満）
                l, c, rr = r[ml[1], ml[0] - 1], r[ml[1], ml[0]], r[ml[1], ml[0] + 1]; d = l - 2 * c + rr; px += 0.5 * (l - rr) / d if d else 0
            if 0 < ml[1] < r.shape[0] - 1:
                u, c, dd = r[ml[1] - 1, ml[0]], r[ml[1], ml[0]], r[ml[1] + 1, ml[0]]; d = u - 2 * c + dd; py += 0.5 * (u - dd) / d if d else 0
            if best is None or mv > best[0]:
                best = (mv, float(sc), (px + tw / 2 - A.shape[1] / 2) / f * k, (py + th / 2 - A.shape[0] / 2) / f * k)
        return best
    b1 = run(480, np.arange(0.60, 1.601, 0.01), 2)
    if b1 is None or b1[0] < 0.55: return None
    b2 = run(960, np.arange(b1[1] - 0.012, b1[1] + 0.0121, 0.002), 3) or b1
    return b2[1], b2[2], b2[3], 0.0, int(b2[0] * 100), None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--json", default="shirabe/大きさ表.json"); ap.add_argument("--ids"); ap.add_argument("--cuts", action="store_true", help="書き出しの代わりに cuts/<番号>.mp4 を直接測る（書き出さずに回せる）")
    g = ap.parse_args()
    ref = sorted(glob.glob(f"{g.w}/ref/*.mp4"))[0]
    shots = sorted(json.load(open(f"{g.w}/eye/out.json"))["shots"], key=lambda s: s["t0"])
    want = set(g.ids.split(",")) if g.ids else None
    plan = []
    for s in shots:
        if want and str(s["i"]) not in want: continue
        f0, f1 = int(round(s["t0"] * 29.97)), int(round(s["t1"] * 29.97))
        if f1 - f0 < 2: continue
        plan.append((s, sorted(set(int(f0 + (f1 - f0) * q) for q in (0.25, 0.5, 0.75)))))
    need = {n for _, ns in plan for n in ns}
    RF = grab(ref, need)
    if g.cuts:
        OF = {}
        for s_, ns_ in plan:
            f0_ = int(round(s_["t0"] * 29.97)); got_ = grab(f"{g.w}/cuts/{s_['i']}.mp4", {n - f0_ for n in ns_})
            for n in ns_:
                if n - f0_ in got_: OF[n] = got_[n - f0_]
    else:
        OF = grab(g.out, need)
    rows = []
    for s, ns in plan:
        got = []
        for n in ns:
            a, b = RF.get(n), OF.get(n)
            if a is None or b is None: continue
            r = meas(a, b)
            if r: got.append(r)
        how = "特徴点"
        if not got:
            for n in ns:
                a, b = RF.get(n), OF.get(n)
                if a is None or b is None: continue
                r = meas_ncc(a, b)
                if r: got.append(r)
            how = "ぼかし重ね"
        if not got:
            rows.append({"cut": s["i"], "t": round(s["t0"], 2), "kind": s["kind"], "ok": "測れん"}); continue
        v = np.median(np.array([x[:5] for x in got]), 0)
        ok = "✅" if abs(v[0] - 1) <= 0.01 and abs(v[1]) <= 4 and abs(v[2]) <= 4 else "🔴"
        rows.append({"cut": s["i"], "t": round(s["t0"], 2), "kind": s["kind"], "s": round(float(v[0]), 4), "dx": round(float(v[1]), 1), "dy": round(float(v[2]), 1), "rot": round(float(v[3]), 2), "inl": int(v[4]), "how": how, "ok": ok, "per": [[int(n_), round(float(x[0]), 4), round(float(x[1]), 1), round(float(x[2]), 1)] for n_, x in zip(ns, got)] if len(got) == len(ns) else []})
        print(rows[-1], flush=True)
    if want and os.path.exists(g.json):   # 一部だけ測った時は表のその行だけ差し替える
        old = {str(r["cut"]): r for r in json.load(open(g.json))}
        for r in rows: old[str(r["cut"])] = r
        rows = sorted(old.values(), key=lambda r: r["t"])
    json.dump(rows, open(g.json, "w"), ensure_ascii=False, indent=1)
    red = [r for r in rows if r["ok"] == "🔴"]; na = [r for r in rows if r["ok"] == "測れん"]
    print(f"✅ {sum(r['ok'] == '✅' for r in rows)}／🔴 {len(red)}／測れん {len(na)}")


if __name__ == "__main__":
    main()
