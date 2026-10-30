"""元の動画から、手本の1コマずつの「元の時刻（小数のコマ）」を測って、その時刻のコマを作り直す（止まりコマ・遅回し・早回しを手本と同じにする）。
python3 retime.py <作業> <カット番号> <元の動画> [--win a-b 秒] [--min -0.003] [--write]
- 手本は元を遅回し（r2 の 21＝元 60fps の 0.3 倍）にして、間のコマを作っとる事がある。うちが同じコマを並べると「止まりコマ」になる（motion_kind.py で🔴）
- 手順：①手本の真ん中のコマと元を SIFT で重ねる（H）②元の全コマを H で手本の形に曲げて、手本のコマごとに一番似た元のコマを放物線で小数まで出す
  ③時刻は前へしか進まん（単調）・手本が前と同じコマ（差<0.15）の所は前と同じ時刻＝手本の重複コマもそのまま写す
  ④小数の時刻は DIS フローで前後のコマの間を作る ⑤コマごとに ECC（射影）で手本へ詰めて、前後でならす ⑥色は色ごとの表（カット全体で1つ・単調）・ぼかし 0〜3
- 似る度合い（NCC）が 0.5 未満の手本のコマ（切り替えの光・別の絵）は今のカットのコマのまま
- --write でカットを書き換える（SSIM が今より --min 以上の時だけ）。前の物は .bak_rt
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
import cut_score
from geo import geo

W, H, FPS = 1280, 720, 29.97   # use_geo(<作業>) で手本の数字に替わる（10/30 geo）
FPS_FF = "2997/100"


def use_geo(w):
    """手本の大きさ・fps を geo から読む（rd・interp・gray と cut_score.frames に効く）。rd を使う道具は最初に1回呼ぶ"""
    global W, H, FPS, FPS_FF
    G = geo(w); W, H, FPS, FPS_FF = G["W"], G["H"], G["FPS"], G["FPS_FF"]
    cut_score.use_geo(w)
cv2.setNumThreads(4)


def rd(p, fps=None, ss=None, t=None, w=None, h=None, sel=None):
    w = w or W; h = h or H
    vf = f"scale={w}:{h}" if fps is None else f"fps={fps},scale={w}:{h}"
    if sel: vf = f"fps={FPS_FF},select='between(n\\,{sel[0]}\\,{sel[1]})',scale={w}:{h}"
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss is not None else []) + (["-t", str(t)] if t is not None else []) + ["-i", p, "-vf", vf]
    if sel: cmd += ["-vsync", "0"]
    r = subprocess.run(cmd + ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w, 3)


def gray(x, s=320):
    return cv2.cvtColor(cv2.resize(x, (s, s * H // W), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)


def ncc(a, b, m):
    a = a[m] - a[m].mean(); b = b[m] - b[m].mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum() + 1e-6))


def interp(S, p, dis):
    i = int(np.floor(p)); a = float(p - i)
    if i >= len(S) - 1: return S[-1]
    if a < 0.04: return S[i]
    if a > 0.96: return S[i + 1]
    g0, g1 = cv2.cvtColor(S[i], cv2.COLOR_BGR2GRAY), cv2.cvtColor(S[i + 1], cv2.COLOR_BGR2GRAY)
    f01 = dis.calc(g0, g1, None); f10 = dis.calc(g1, g0, None)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    w0 = cv2.remap(S[i], (xx - a * f01[..., 0]).astype(np.float32), (yy - a * f01[..., 1]).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    w1 = cv2.remap(S[i + 1], (xx - (1 - a) * f10[..., 0]).astype(np.float32), (yy - (1 - a) * f10[..., 1]).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return cv2.addWeighted(w0, 1 - a, w1, a, 0)


def looks(w, f0, n):
    """Remotion と同じ順で、コマごとに効く shot_look（g・o・blur）を返す。layer_off の look を外す所は無し（10/28：23 で取り違えて真っ暗）"""
    import json
    L = list(json.load(open(f"{w}/proj/src/shot_look.json")).values())
    off = [x for x in json.load(open(f"{w}/proj/src/layer_off.json")) if "look" in x.get("off", [])] if os.path.exists(f"{w}/proj/src/layer_off.json") else []
    out = []
    for f in range(f0, f0 + n):
        lk = None if any(o["f0"] <= f < o["f1"] for o in off) else next((l for l in L if l["f0"] <= f <= l["f1"]), None)
        if not lk or not lk.get("g"):
            out.append((np.ones(3, np.float32), np.zeros(3, np.float32), float((lk or {}).get("blur", 0) or 0)))
        else:
            out.append((np.array(lk["g"], np.float32)[::-1], np.array(lk["o"], np.float32)[::-1] * 255, float(lk.get("blur", 0) or 0)))
    return out


def post_f(x, lk):
    gg, oo, bs = lk
    y = np.clip(x.astype(np.float32) * gg + oo, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(y, (0, 0), bs) if bs else y


def pre_f(x, lk):
    gg, oo, _ = lk
    return np.clip((x.astype(np.float32) - oo) / gg, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("src")
    ap.add_argument("--win", default=""); ap.add_argument("--min", type=float, default=-0.003); ap.add_argument("--write", action="store_true")
    ap.add_argument("--nomove", action="store_true", help="ECC で詰めん（H だけ）")
    ap.add_argument("--cols", default="", help="合わせに使う列 x0-x1（手本の幅の画素）。フィルムの窓のカットは 260-1020＝帯を外して、後で gate_fx")
    a = ap.parse_args(); w = os.path.abspath(a.w); use_geo(w)
    G = geo(w); SW, SH = G["SW"], G["SH"]  # 字幕の帯（r2 の 720 の 300〜420）の行は手本の高さの比で移す
    h480 = int(round(480 * H / W)); h960 = int(round(960 * H / W)); MW, MH = cut_score.W, cut_score.H
    seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{a.cut}:")][0]
    s0, s1 = map(float, seg.split(":")[1].split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
    R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(f0, f1 - 1)); n = len(R)
    cutp = f"{w}/cuts/{a.cut}.mp4"; C = rd(cutp)[:n] if os.path.exists(cutp) else R.copy() * 0
    sw = [float(x) for x in a.win.split("-")] if a.win else None
    S = rd(a.src, ss=sw[0] if sw else None, t=(sw[1] - sw[0]) if sw else None)  # 元の fps のまま
    sfps = cv2.VideoCapture(a.src).get(cv2.CAP_PROP_FPS)
    print("手本", n, "コマ／元", len(S), "コマ", round(sfps, 2), "fps", flush=True)
    m = np.ones((SH, SW), bool); m[round(75 * SH / 180):round(105 * SH / 180)] = False
    m480 = np.ones((h480, 480), np.uint8); m480[round(112 * h480 / 270):round(158 * h480 / 270)] = 0
    cx = [int(v) for v in a.cols.split("-")] if a.cols else [0, W]
    m[:, :cx[0] * SW // W] = False; m[:, cx[1] * SW // W:] = False
    m480[:, :cx[0] * 480 // W] = 0; m480[:, cx[1] * 480 // W:] = 0
    # ① H：手本の真ん中と、元を4コマおきに SIFT
    sf = cv2.SIFT_create(3000); bf = cv2.BFMatcher()
    mid = n // 2; rg = cv2.resize(cv2.cvtColor(R[mid], cv2.COLOR_BGR2GRAY), (960, h960)); rmask = np.ones_like(rg); rmask[round(225 * h960 / 540):round(315 * h960 / 540)] = 0
    kr, dr = sf.detectAndCompute(rg, rmask)
    best = (0, None, 0)
    for j in range(0, len(S), 3):
        ks, ds = sf.detectAndCompute(cv2.resize(cv2.cvtColor(S[j], cv2.COLOR_BGR2GRAY), (960, h960)), None)
        if ds is None or dr is None: continue
        mm = [x for x, y in (q for q in bf.knnMatch(ds, dr, k=2) if len(q) == 2) if x.distance < 0.75 * y.distance]
        if len(mm) < 10: continue
        Hm, inl = cv2.findHomography(np.float32([ks[x.queryIdx].pt for x in mm]), np.float32([kr[x.trainIdx].pt for x in mm]), cv2.RANSAC, 4.0)
        if Hm is not None and inl.sum() > best[0]: best = (int(inl.sum()), Hm, j)
    if best[1] is None: sys.exit("SIFT が当たらん")
    Hm = best[1]; Sc = np.diag([960 / W, 960 / W, 1]); Hf = np.linalg.inv(Sc) @ Hm @ Sc
    print("H 目印", best[0], "元のコマ", best[2], flush=True)
    # ② 元を手本の形にして SW（320）で NCC
    Sg = [gray(cv2.warpPerspective(s, Hf, (W, H), borderMode=cv2.BORDER_REFLECT)) for s in S]
    pos, conf = [], []
    for k in range(n):
        rgk = gray(R[k]); sc = np.array([ncc(rgk, x, m) for x in Sg]); j = int(np.argmax(sc)); p = float(j)
        if 0 < j < len(sc) - 1:
            d = sc[j - 1] - 2 * sc[j] + sc[j + 1]
            if d < 0: p = j + 0.5 * (sc[j - 1] - sc[j + 1]) / d
        pos.append(p); conf.append(float(sc[j]))
    # ③ 単調・重複コマ
    rd_ = [0] + [float(np.mean(np.abs(cv2.GaussianBlur(gray(R[k]), (0, 0), 1.2) - cv2.GaussianBlur(gray(R[k - 1]), (0, 0), 1.2))[m])) for k in range(1, n)]
    P = list(pos); last = None
    for k in range(n):
        if conf[k] < 0.5: continue
        if last is not None:
            if rd_[k] < 0.15 and conf[k - 1] >= 0.5: P[k] = P[k - 1]
            elif P[k] < P[last]: P[k] = P[last]
        last = k
    for k in range(n): print(f0 + k, "元", round(pos[k], 2), "→", round(P[k], 2), "似", round(conf[k], 3), "手本の差", round(rd_[k], 2))
    # ④⑤ 作る
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    out = C.copy(); use = [k for k in range(n) if conf[k] >= 0.5]
    Ms = {}
    for k in use:
        fr = interp(S, P[k], dis); Ms[k] = (fr, Hf.copy())
        if not a.nomove:
            tg = cv2.resize(cv2.cvtColor(R[k], cv2.COLOR_BGR2GRAY), (480, h480)).astype(np.float32)
            Sh = np.diag([480 / W, 480 / W, 1]); H0 = (Sh @ Hf @ np.linalg.inv(Sh)).astype(np.float32)
            sg = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (480, h480)).astype(np.float32)
            try:
                _, Hk = cv2.findTransformECC(tg, sg, np.linalg.inv(H0).astype(np.float32), cv2.MOTION_HOMOGRAPHY, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5), m480, 3)
                Ms[k] = (fr, np.linalg.inv(Sh) @ np.linalg.inv(Hk.astype(np.float64)) @ Sh)
            except cv2.error:
                pass
    # 前後でならす（3コマの平均）
    ks = sorted(Ms)
    sm = {k: np.mean([Ms[j][1] / Ms[j][1][2, 2] for j in ks if abs(j - k) <= 1], 0) for k in ks}
    warped = {k: cv2.warpPerspective(Ms[k][0], sm[k], (W, H), borderMode=cv2.BORDER_REFLECT) for k in ks}
    # ⑥ 色（カット全体で1つの2次）
    txt = np.ones((H, W), bool); txt[round(300 * H / 720):round(420 * H / 720)] = False; txt[:, :cx[0]] = False; txt[:, cx[1]:] = False
    X = np.concatenate([warped[k][::4, ::4][txt[::4, ::4]] for k in ks]).astype(np.float64) / 255
    Y = np.concatenate([R[k][::4, ::4][txt[::4, ::4]] for k in ks]).astype(np.float64)
    # 色ごとの「元の値→手本の値」の表（区間ごとの中央値・前へしか上がらん形）。2次の式は空が白く飛んだ（67）
    X = X * 255
    lut = []
    for c in range(3):
        xs, ys = X[:, c], Y[:, c]; t = np.full(256, np.nan)
        for v in range(0, 256, 4):
            sel = (xs >= v) & (xs < v + 4)
            if sel.sum() >= 30: t[v:v + 4] = np.median(ys[sel])
        ok = ~np.isnan(t)
        t = np.interp(np.arange(256), np.arange(256)[ok], t[ok]) if ok.sum() >= 2 else np.arange(256, dtype=float)
        t = np.maximum.accumulate(cv2.GaussianBlur(t.reshape(1, -1).astype(np.float32), (0, 0), 3).ravel())
        lut.append(np.clip(t, 0, 255).astype(np.uint8))
    def col(im):
        return np.stack([cv2.LUT(im[..., c], lut[c]) for c in range(3)], -1)
    g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH))
    # カットは Remotion の shot_look（g・o・blur）の前の色＝比べる時は look をかけてから、書く時は g・o を逆にかける（コマごとに効く物）
    LK = looks(w, f0, n)
    bs = max(l[2] for l in LK)
    post = lambda x, k: post_f(x, LK[k])
    pre = lambda x, k: pre_f(x, LK[k])
    cand = {k: col(warped[k]) for k in ks}
    bb = (-1, 0)
    for bl in sorted(set([bs, 0.7, 1.2, 2, 3, 4] + ([((bs ** 2) + t ** 2) ** 0.5 for t in (0.7, 1.2, 2)] if bs else []))):
        if bl < bs: continue
        sc = np.mean([ssim(g(R[k]), g(cv2.GaussianBlur(cand[k], (0, 0), bl) if bl else cand[k])) for k in ks])
        if sc > bb[0]: bb = (sc, bl)
    before = np.mean([ssim(g(R[k]), g(post(C[k], k))) for k in range(n)])
    bc = (max(0.0, bb[1] ** 2 - bs ** 2)) ** 0.5
    for k in ks:
        y = pre(cand[k], k); out[k] = cv2.GaussianBlur(y, (0, 0), bc) if bc > 0.3 else y
    after = np.mean([ssim(g(R[k]), g(post(out[k], k))) for k in range(n)])
    print(f"カット {a.cut} SSIM {before:.3f} → {after:.3f}（ぼかし {bb[1]}・作り直した {len(ks)}/{n} コマ）", flush=True)
    tmp = f"{w}/tmp/rt_{a.cut}.mp4"; os.makedirs(f"{w}/tmp", exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", FPS_FF, "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    p.stdin.write(out.tobytes()); p.stdin.close(); p.wait(); print("試し", tmp)
    if a.write and after >= before + a.min:
        if os.path.exists(cutp) and not os.path.exists(cutp + ".bak_rt"): shutil.copy(cutp, cutp + ".bak_rt")
        shutil.copy(tmp, cutp); print("書いた", cutp)
    elif a.write:
        print("書かん（SSIM が下がる）")


if __name__ == "__main__":
    main()
