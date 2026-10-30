"""元の映像（1080p の切り出し）を、手本の1カットとコマも位置も色も同じに作る。

python3 fit_cut.py <作業フォルダ> <カット番号> [--out cuts/]
- 位置：hi.json の H（480幅どうしの重ね方）を元の大きさに直して、手本の大きさ（1280x720）にはめる
- 色：手本のコマとの差が一番小さくなる2次の式を、色ごとに最小二乗で求める（字・端の外れ値は2回目で外す）
- ぼかし：0〜3 の中で手本との SSIM が一番高い強さ
- 出す物：<out>/<番号>.mp4（字なし・手本と同じ fps・コマ数）と <番号>.json（式・ぼかし・SSIM の前後）
"""
import argparse, glob, json, os, subprocess
import cv2
import numpy as np

W = 480


def probe(p, keys):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", f"stream={keys}",
                        "-of", "json", p], capture_output=True, text=True)
    return json.loads(r.stdout)["streams"][0]


def read(p, t0, dur, fps, w, h):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-t", f"{dur:.4f}", "-i", p,
                        "-vf", f"fps={fps}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w, 3)


def ssim_gray(a, b, mask):
    a = cv2.cvtColor(cv2.resize(a, (W, W * a.shape[0] // a.shape[1])), cv2.COLOR_BGR2GRAY).astype(np.float32)
    b = cv2.cvtColor(cv2.resize(b, (W, W * b.shape[0] // b.shape[1])), cv2.COLOR_BGR2GRAY).astype(np.float32)
    m = cv2.resize(mask.astype(np.uint8), (a.shape[1], a.shape[0])) > 0
    C1, C2, k = 6.5025, 58.5225, (7, 7)
    mu_a, mu_b = cv2.blur(a, k), cv2.blur(b, k)
    sa, sb = cv2.blur(a * a, k) - mu_a ** 2, cv2.blur(b * b, k) - mu_b ** 2
    sab = cv2.blur(a * b, k) - mu_a * mu_b
    s = ((2 * mu_a * mu_b + C1) * (2 * sab + C2)) / ((mu_a ** 2 + mu_b ** 2 + C1) * (sa + sb + C2))
    return float(s[m].mean()) if m.any() else 0.0


def feats(x):
    x = x.reshape(-1, 3).astype(np.float64) / 255.0
    b, g, r = x[:, 0], x[:, 1], x[:, 2]
    return np.stack([np.ones_like(b), b, g, r, b * b, g * g, r * r, b * g, g * r, r * b], 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("--out", default="cuts"); ap.add_argument("--track", type=int, default=1); ap.add_argument("--hi", default="src/hi.json"); ap.add_argument("--model", default="homog"); ap.add_argument("--keepH", type=int, default=0, help="1＝hi の H をそのまま使う（SIFT・ECC で詰めん。手本の加工が強くて流れる時）"); ap.add_argument("--blur_by", default="edge", help="edge＝手本と同じ鋭さ（既定・10/28〜）／ssim＝昔の SSIM 最大"); ap.add_argument("--color", default="lsq", help="lsq＝2次の式（既定）／mean＝チャンネルごとの平均と幅だけ（生成した絵など画素が対応せん時）／none＝色を触らん")
    g = ap.parse_args()
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    shot = [s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"] if str(s["i"]) == g.i][0]
    hi = json.load(open(f"{g.w}/{g.hi}"))[g.i]
    rp = probe(ref, "width,height,r_frame_rate")
    rw, rh = rp["width"], rp["height"]
    fps = rp["r_frame_rate"]
    t0, t1 = float(shot["t0"]), float(shot["t1"])
    a, b = fps.split("/")
    fpsf = float(a) / float(b)
    n = int(round((t1 - t0) * fpsf))  # 次のカットの1コマを入れん
    R = read(ref, t0, t1 - t0, fps, rw, rh)[:n]
    n = len(R)
    cp = probe(hi["file"], "width,height")
    cw, ch = cp["width"], cp["height"]
    M = int(round(fpsf))  # 前後1秒ぶん余分に読む
    rel = hi["start"] - hi["clip_start"]
    lo = max(0.0, rel - 1.0)
    C = read(hi["file"], lo, (t1 - t0) + 2.0, fps, cw, ch)
    base = int(round((rel - lo) * fpsf))
    H = np.array(hi["H"], np.float64)
    MOT = cv2.MOTION_AFFINE if g.model == "sim" else cv2.MOTION_HOMOGRAPHY
    Sr = np.diag([rw / W, rw / W, 1.0])
    Sc = np.diag([W / cw, W / cw, 1.0])
    # 時刻と重ね方を詰める：手本の真ん中のコマに、元の前後1秒を1コマずつ ECC で重ねて一番合うコマを探す
    def ecc_m(cg, rg, H0, it):
        H0 = H0 / H0[2, 2]
        if g.keepH:
            return H0
        try:
            if MOT == cv2.MOTION_AFFINE:
                _, A = cv2.findTransformECC(cg, rg, H0[:2].astype(np.float32), MOT,
                                            (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, it, 1e-5), None, 3)
                return np.vstack([A, [0, 0, 1]]).astype(np.float64)
            _, Hj = cv2.findTransformECC(cg, rg, H0.astype(np.float32), MOT,
                                         (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, it, 1e-5), None, 3)
            return Hj.astype(np.float64)
        except cv2.error:
            return H0

    def g480(x):
        return cv2.cvtColor(cv2.resize(x, (W, W * x.shape[0] // x.shape[1])), cv2.COLOR_BGR2GRAY).astype(np.float32)
    rm = g480(R[n // 2])
    if hi["flip"]:
        rm = cv2.flip(rm, 1)
    if g.model == "sim" and not g.keepH:
        # 斜めの歪みを許さん：真ん中のコマどうしで拡大・移動・回転だけを取り直す
        sf = cv2.SIFT_create(2000)
        ci = min(len(C) - 1, base + n // 2)
        ka, da = sf.detectAndCompute(g480(C[ci]).astype(np.uint8), None)
        kb, db = sf.detectAndCompute(rm.astype(np.uint8), None)
        if da is not None and db is not None:
            mm = [x for x, y in (q for q in cv2.BFMatcher().knnMatch(da, db, k=2) if len(q) == 2) if x.distance < 0.75 * y.distance]
            if len(mm) >= 8:
                A, _ = cv2.estimateAffinePartial2D(np.float32([ka[x.queryIdx].pt for x in mm]), np.float32([kb[x.trainIdx].pt for x in mm]),
                                                   method=cv2.RANSAC, ransacReprojThreshold=4.0)
                if A is not None:
                    H = np.vstack([A, [0, 0, 1]])
    best_t = (-1, base, H)
    for j in range(max(0, base + n // 2 - M), min(len(C), base + n // 2 + M + 1)):
        cg = g480(C[j])
        Hj = ecc_m(cg, rm, H, 60).astype(np.float32)
        wv = cv2.warpPerspective(cg, Hj, (rm.shape[1], rm.shape[0]))
        mk = cv2.warpPerspective(np.ones_like(cg), Hj, (rm.shape[1], rm.shape[0])) > 0.99
        sc = ssim_gray(cv2.cvtColor(wv.astype(np.uint8), cv2.COLOR_GRAY2BGR), cv2.cvtColor(rm.astype(np.uint8), cv2.COLOR_GRAY2BGR), mk)
        if sc > best_t[0]:
            best_t = (sc, j - n // 2, Hj.astype(np.float64))
    start_idx = max(0, best_t[1])
    H = best_t[2]
    src_start = hi["clip_start"] + lo + start_idx / fpsf
    Fl = np.array([[-1, 0, rw - 1], [0, 1, 0], [0, 0, 1]], np.float64)

    def full(Hs):
        Hf = Sr @ Hs @ Sc
        return Fl @ Hf if hi["flip"] else Hf

    def ecc(cg, rg, H0):
        return ecc_m(cg, rg, H0, 40)

    def score(cg, rg, Hs):
        wv = cv2.warpPerspective(cg, Hs, (rg.shape[1], rg.shape[0]))
        mk = cv2.warpPerspective(np.ones_like(cg), Hs, (rg.shape[1], rg.shape[0])) > 0.99
        to = lambda x: cv2.cvtColor(np.clip(x, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        return ssim_gray(to(wv), to(rg), mk)

    track = []  # (元のコマ番号, 重ね方)
    if g.track:
        # 真ん中から前と後ろへ追う（前のコマの重ね方を出発点に）
        mid = n // 2
        cur, Hc = start_idx + mid, H
        seq = {}
        for j in list(range(mid, n)) + list(range(mid - 1, -1, -1)):
            if j == mid - 1:
                cur, Hc = seq[mid][0], seq[mid][1]
            rg = g480(R[j])
            if hi["flip"]:
                rg = cv2.flip(rg, 1)
            step = range(0, 4) if j >= mid else range(-3, 1)
            if j == mid:
                step = range(0, 1)
            bestj = None
            for d in step:
                k = cur + d
                if not 0 <= k < len(C):
                    continue
                cg = g480(C[k])
                Hk = ecc(cg, rg, Hc)
                sc = score(cg, rg, Hk)
                s0 = score(cg, rg, Hc)
                if s0 >= sc:  # 合わせ直して悪くなるなら前の重ね方のまま（流れて壊れるのを防ぐ）
                    Hk, sc = Hc, s0
                if bestj is None or sc > bestj[0]:
                    bestj = (sc, k, Hk)
            if bestj is None:
                bestj = (0, min(len(C) - 1, max(0, cur)), Hc)
            seq[j] = (bestj[1], bestj[2])
            cur, Hc = bestj[1], bestj[2]
        track = [seq[j] for j in range(n)]
    else:
        track = [(min(len(C) - 1, start_idx + j), H) for j in range(n)]
    Wp = np.stack([cv2.warpPerspective(C[k], full(Hs), (rw, rh), flags=cv2.INTER_LANCZOS4) for k, Hs in track])
    Hf = full(track[n // 2][1])
    mask = np.ones((rh, rw), bool)
    for k, Hs in track:
        mask &= cv2.warpPerspective(np.full((ch, cw), 255, np.uint8), full(Hs), (rw, rh)) > 250
    mask = cv2.erode(mask.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    before = float(np.mean([ssim_gray(Wp[j], R[j], mask) for j in range(n)]))
    # 色の式（全コマから間引いて取る）
    idx = np.flatnonzero(mask.ravel())
    rng = np.random.default_rng(0)
    pick = rng.choice(idx, min(len(idx), 20000), replace=False)
    X = np.concatenate([feats(Wp[j].reshape(-1, 3)[pick]) for j in range(n)])
    Y = np.concatenate([R[j].reshape(-1, 3)[pick].astype(np.float32) / 255.0 for j in range(n)])
    coef = np.linalg.lstsq(X, Y, rcond=None)[0]
    res = np.abs(X @ coef - Y).sum(1)
    keep = res < np.percentile(res, 85)  # 字・光の点などの外れを外して取り直す
    coef = np.linalg.lstsq(X[keep], Y[keep], rcond=None)[0]

    if g.color == "mean":  # 生成した絵＝画素が対応せんので、Lab の平均と幅だけ手本に寄せる（2次の式は白飛びする・10/26 r2 65）
        src = np.concatenate([cv2.cvtColor(Wp[j], cv2.COLOR_BGR2LAB).reshape(-1, 3)[pick] for j in range(n)]).astype(np.float32)
        dst = np.concatenate([cv2.cvtColor(R[j], cv2.COLOR_BGR2LAB).reshape(-1, 3)[pick] for j in range(n)]).astype(np.float32)
        ms, ss = src.mean(0), src.std(0) + 1e-6; md, sd = dst.mean(0), dst.std(0)
        def color(img):
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
            lab = (lab - ms) / ss * np.minimum(sd, ss * 1.5) + md
            return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    elif g.color == "none":
        def color(img):
            return img
    else:
        def color(img):
            return np.clip(feats(img) @ coef * 255.0, 0, 255).reshape(img.shape).astype(np.uint8)

    Cc = np.stack([color(x) for x in Wp])
    # 🔒10/28 ぼかしは「手本と同じ鋭さ」で選ぶ（SSIM 最大で選ぶと最大の σ に張り付く＝r2 で 34 カットが σ3.0・138 は鋭さ 2831→9）
    def edge90(x):
        gx = cv2.GaussianBlur(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.0)
        m = np.hypot(cv2.Sobel(gx, cv2.CV_32F, 1, 0), cv2.Sobel(gx, cv2.CV_32F, 0, 1)); return float(np.percentile(m[mask > 0] if mask is not None and mask.shape == m.shape else m, 90))
    re_ = float(np.mean([edge90(R[j]) for j in range(0, n, max(1, n // 5))]))
    best = (9, 0, 0)
    for sg in (0, 0.5, 1.0, 1.5, 2.0, 3.0):
        Bx = Cc if sg == 0 else np.stack([cv2.GaussianBlur(x, (0, 0), sg) for x in Cc])
        e = float(np.mean([edge90(Bx[j]) for j in range(0, n, max(1, n // 5))])) / max(re_, 1e-6)
        s = float(np.mean([ssim_gray(Bx[j], R[j], mask) for j in range(n)]))
        d = abs(np.log(max(e, 1e-3)))  # 鋭さ比が 1 に近いほど良い
        if g.blur_by == "ssim": d = -s
        if d < best[0]:
            best = (d, sg, s)
    sg = best[1]; print(f"ぼかし σ{sg}（鋭さで選んだ・点 {best[2]:.4f}）", flush=True)
    Out = Cc if sg == 0 else np.stack([cv2.GaussianBlur(x, (0, 0), sg) for x in Cc])
    od = f"{g.w}/{g.out}"; os.makedirs(od, exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{rw}x{rh}",
                          "-r", fps, "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", f"{od}/{g.i}.mp4"],
                         stdin=subprocess.PIPE)
    p.stdin.write(Out.tobytes()); p.stdin.close(); p.wait()
    rep = {"i": int(g.i), "frames": n, "ssim_place": round(before, 4), "ssim_color": round(best[0], 4), "blur": sg,
           "cover": round(float(mask.mean()), 3), "coef": coef.tolist(), "H_full": Hf.tolist(), "src": hi["url"],
           "src_start": round(src_start, 4), "shift_frames": start_idx - base, "src_frames": [int(k) + int(round((hi["clip_start"] + lo) * fpsf)) for k, _ in track]}
    json.dump(rep, open(f"{od}/{g.i}.json", "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("i", "frames", "ssim_place", "ssim_color", "blur", "cover", "shift_frames")}))


if __name__ == "__main__":
    main()
