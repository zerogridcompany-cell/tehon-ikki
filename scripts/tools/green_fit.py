"""Codex の一枚絵を、手本のコマ（サブカット）に当てる。

python3 green_fit.py <r2> <mg/green> [--only g1,g2]
- plates.tsv（id f0 f1 fm tone）の各絵を、f0〜f1 の手本の1コマずつに ECC（アフィン）で合わせる
- 色＝各チャンネルを 2次式で（字幕の白は外す）→ 色を当てた絵 proj/public/green/<id>.png（絵の元の大きさ）
- ぼかし 0〜3 を選ぶ → green.json（コマごとの 2x3 行列・ぼかし・SSIM）
"""
import argparse, json, os
import cv2, numpy as np
from skimage.metrics import structural_similarity as ssim

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("g"); ap.add_argument("--only")
a = ap.parse_args()
import glob
ref = cv2.VideoCapture(glob.glob(f"{a.w}/ref/*.mp4")[0])
W, H = int(ref.get(cv2.CAP_PROP_FRAME_WIDTH)), int(ref.get(cv2.CAP_PROP_FRAME_HEIGHT))
def frame(n):
    ref.set(cv2.CAP_PROP_POS_FRAMES, n); ok, im = ref.read(); return im

CAPS = json.load(open(f"{a.w}/proj/src/caps.json"))
def cap_mask(im, n=None):
    # 字幕＝caps.json の語の箱（そのコマに出とる語だけ）。白い地の絵で白を全部外してしまわんように、色では探さん
    m = np.zeros((H, W), np.uint8)
    for c in CAPS:
        if n is not None and c["f0"] <= n <= c["f1"]:
            x0 = int(c["x"] - 0.2 * c["fs"]); x1 = int(c["x"] + 0.62 * c["fs"] * len(c["w"]) + 0.2 * c["fs"])
            y0 = int(c["y"] - 1.0 * c["fs"]); y1 = int(c["y"] + 0.35 * c["fs"])
            m[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = 1
    return cv2.dilate(m, np.ones((21, 21), np.uint8)) > 0

def ecc(src_g, dst_g, M0, mask):
    M = M0.astype(np.float32).copy()
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
    for s in (0.25, 0.5, 1.0):
        sm = np.array([[s, 0, 0], [0, s, 0]], np.float32)
        a_ = cv2.resize(src_g, None, fx=s, fy=s); b_ = cv2.resize(dst_g, None, fx=s, fy=s)
        mk = cv2.resize(mask.astype(np.uint8), (b_.shape[1], b_.shape[0]), interpolation=cv2.INTER_NEAREST)
        Ms = M.copy(); Ms[:, 2] *= s
        # マスクは「入力（絵）」側の大きさで渡す（画面側で渡すと毎回エラー＝10/25 まで全部の絵で ECC が効いてなかった）
        mki = cv2.warpAffine(mk, Ms, (a_.shape[1], a_.shape[0]), flags=cv2.INTER_NEAREST)
        try:
            _, Ms = cv2.findTransformECC(b_, a_, Ms, cv2.MOTION_AFFINE, crit, mki, 5)
            M = Ms.copy(); M[:, 2] /= s
        except cv2.error as e:
            print("  ECC 失敗", s, str(e)[:80], flush=True)
    return M  # dst(x) = src(M x) ではなく warpAffine(src, M_inv) 形式に直すのは下で

def gray(im):
    return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255

def fit_color(src, dst, mask):
    out = []
    for c in range(3):
        x = src[..., c][mask].astype(np.float64) / 255; y = dst[..., c][mask].astype(np.float64) / 255
        keep = np.ones_like(x, bool)
        for _ in range(2):
            A = np.stack([x[keep] ** 2, x[keep], np.ones(keep.sum())], 1)
            k, *_ = np.linalg.lstsq(A, y[keep], rcond=None)
            r = np.abs(np.stack([x ** 2, x, np.ones_like(x)], 1) @ k - y)
            keep = r < np.percentile(r, 85)
        out.append(k.tolist())
    return out

def apply_color(im, K):
    f = im.astype(np.float32) / 255; o = np.zeros_like(f)
    for c in range(3):
        k = K[c]; o[..., c] = k[0] * f[..., c] ** 2 + k[1] * f[..., c] + k[2]
    return np.clip(o * 255, 0, 255).astype(np.uint8)

rows = [l.rstrip("\n").split("\t") for l in open(f"{a.g}/plates.tsv")]
only = set(a.only.split(",")) if a.only else None
od = f"{a.w}/proj/public/green"; os.makedirs(od, exist_ok=True)
outp = f"{a.g}/green.json"
res = json.load(open(outp)) if os.path.exists(outp) else {}
for r in rows:
    pid, f0, f1, fm = r[0], int(r[1]), int(r[2]), int(r[3])
    if only and pid not in only:
        continue
    pl = cv2.imread(f"{a.g}/{pid}/plate.png")
    if pl is None:
        print(pid, "絵が無い"); continue
    ph, pw = pl.shape[:2]
    # 下敷きのコマへ：まず全面に引き伸ばし（Codex は同じ構図で描く）
    M0 = np.array([[pw / W, 0, 0], [0, ph / H, 0]], np.float32)  # dst→src
    fr = {n: frame(n) for n in range(f0, f1 + 1)}
    pg = gray(pl)
    # 1回目：真ん中のコマで色を荒く当ててから ECC（緑と白黒で明るさが違うため）
    mid = fr[fm]; mk = ~cap_mask(mid, fm)
    w0 = cv2.warpAffine(pl, M0, (W, H), flags=cv2.INTER_AREA | cv2.WARP_INVERSE_MAP)
    K = fit_color(w0, mid, mk)
    plc = apply_color(pl, K)
    Ms = {}; prev = M0
    for n in sorted(fr, key=lambda n: abs(n - fm)):
        near = min((m for m in Ms), key=lambda m: abs(m - n), default=None)
        init = Ms[near] if near is not None else M0
        Ms[n] = ecc(gray(plc), gray(fr[n]), init, (~cap_mask(fr[n], n)).astype(np.uint8))
    # 追う／真ん中で固定／初めの位置 の3つを比べて良い方（3D のカメラを平面で追うと床がずれて悪くなる時がある）
    fq = sorted(fr)[::max(1, len(fr) // 12)]  # 長い絵は最大12コマで比べる（10/25）
    def quick(MM):
        return float(np.mean([ssim(cv2.cvtColor(cv2.warpAffine(plc, MM[n], (W, H), flags=cv2.INTER_AREA | cv2.WARP_INVERSE_MAP), cv2.COLOR_BGR2GRAY),
                                   cv2.cvtColor(fr[n], cv2.COLOR_BGR2GRAY)) for n in fq]))
    opts = {"track": Ms, "mid": {n: Ms[fm] for n in fr}, "init": {n: M0 for n in fr}}
    qs = {k: quick(v) for k, v in opts.items()}
    mode = max(qs, key=qs.get); Ms = opts[mode]
    print("  ", pid, {k: round(v, 3) for k, v in qs.items()}, "→", mode, flush=True)
    # 色を全コマでもう一度（合わせた後）
    # 🔴 10/25 t51ikki：全コマ×全画素を lstsq に入れると 140コマの絵で何十分も止まる（c63_1）＝画素を間引いて合計 200万点まで
    xs, ys = [], []
    step = max(1, int(np.ceil(len(fr) * W * H / 2e6)))
    for n in fr:
        wv = cv2.warpAffine(pl, Ms[n], (W, H), flags=cv2.INTER_AREA | cv2.WARP_INVERSE_MAP)
        mk = ~cap_mask(fr[n], n); mk[:4] = mk[-4:] = False; mk[:, :4] = mk[:, -4:] = False
        idx = np.flatnonzero(mk.ravel())[::step]
        xs.append(wv.reshape(-1, 3)[idx]); ys.append(fr[n].reshape(-1, 3)[idx])
    xs = np.concatenate(xs)[None]; ys = np.concatenate(ys)[None]
    K = fit_color(xs, ys, np.ones(xs.shape[:2], bool))
    plc = apply_color(pl, K)
    # ぼかしを選ぶ（絵の画素でのσ）
    cand = []
    for sg in (0, 0.6, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.5, 8.5, 11, 14):
        src = cv2.GaussianBlur(plc, (0, 0), sg) if sg else plc
        sc = []
        for n in fq:
            wv = cv2.warpAffine(src, Ms[n], (W, H), flags=cv2.INTER_AREA | cv2.WARP_INVERSE_MAP)
            sc.append(ssim(cv2.cvtColor(wv, cv2.COLOR_BGR2GRAY), cv2.cvtColor(fr[n], cv2.COLOR_BGR2GRAY)))
        cand.append((sg, float(np.mean(sc)), sc))
    # ぼかすほど SSIM は上がりやすい＝見た目がぼやける。一番良い点から 0.01 以内で一番小さいぼかしを採る
    top = max(c[1] for c in cand)
    best = min((c for c in cand if c[1] >= top - 0.01), key=lambda c: c[0])
    cv2.imwrite(f"{od}/{pid}.png", plc)
    # Remotion 用＝絵の画素→画面の画素（WARP_INVERSE_MAP の M は 画面→絵 なので逆にする）
    fwd = {}
    for n, M in Ms.items():
        A = np.vstack([M, [0, 0, 1]]); F = np.linalg.inv(A)[:2]
        fwd[str(n)] = [round(float(v), 5) for v in F.ravel()]
    res[pid] = {"f0": f0, "f1": f1, "w": pw, "h": ph, "blur": best[0], "ssim": round(best[1], 3),
                "ssim_each": [round(v, 3) for v in best[2]], "M": fwd, "color": K, "mode": mode}
    print(pid, "ssim", round(best[1], 3), "blur", best[0], flush=True)
    json.dump(res, open(outp, "w"), indent=1)
