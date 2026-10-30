"""手本の1カット（ref t0〜t1）が、元の映像（cand）のどの秒・どの切り抜きかを当てる。

python3 match.py ref.mp4 t0 t1 cand.mp4 [--out res.json]
1. 粗く：cand を 2fps で SIFT。手本のカットの真ん中のコマと特徴点が一番合う秒を5つ
2. 細かく：その秒の前後1秒を元の fps で、手本の全コマとの差（射影で重ねた後の SSIM）が一番良い始まりのコマ
出力＝{start: cand の秒, H: 3x3（cand→ref の重ね方）, flip, ssim, frames}
"""
import argparse, json, os, pickle, subprocess
import cv2
import numpy as np

W = 480


def frames(path, t0, dur, fps=None, w=W):
    vf = f"scale={w}:-2" + (f",fps={fps}" if fps else "")
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", path,
                        "-vf", vf, "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
    h = int(round(int(probe[1]) * w / int(probe[0]) / 2) * 2)
    a = np.frombuffer(p.stdout, np.uint8)
    return a.reshape(-1, h, w)


def native_fps(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    a, b = r.split("/")
    return float(a) / float(b)


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True).stdout)


sift = cv2.SIFT_create(1500)
sift_small = cv2.SIFT_create(1500)
bf = cv2.BFMatcher()


def homog(a, b):
    """a の点を b に重ねる 3x3 と、合った点の数"""
    ka, da = sift.detectAndCompute(a, None)
    kb, db = sift.detectAndCompute(b, None)
    if da is None or db is None or len(ka) < 8 or len(kb) < 8:
        return None, 0
    m = [x for x, y in (p for p in bf.knnMatch(da, db, k=2) if len(p) == 2) if x.distance < 0.75 * y.distance]
    if len(m) < 8:
        return None, len(m)
    pa = np.float32([ka[x.queryIdx].pt for x in m])
    pb = np.float32([kb[x.trainIdx].pt for x in m])
    H, inl = cv2.findHomography(pa, pb, cv2.RANSAC, 4.0)
    return H, int(inl.sum()) if inl is not None else 0


def coarse_feats(path, fps, w=320):
    """cand の粗いコマの特徴点を1回だけ取って横に置く（同じ動画を何カットでも使い回す）"""
    cp = f"{path}.sift{fps:g}_{w}.pkl"
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    out = []
    for c in frames(path, 0, duration(path), fps=fps, w=w):
        k, d = sift_small.detectAndCompute(c, None)
        # 保存は uint8（SIFT の値は 0〜255 に収まる）＝1/4 の大きさ
        out.append((np.float16([x.pt for x in k]) if k else np.zeros((0, 2), np.float16),
                    None if d is None else np.clip(d, 0, 255).astype(np.uint8)))
    pickle.dump(out, open(cp, "wb"))
    return out


def homog_feats(fa, b):
    """a（特徴点が取ってある）を b に重ねる"""
    pa_all, da = fa
    da = None if da is None else da.astype(np.float32)
    kb, db = sift.detectAndCompute(b, None)
    if da is None or db is None or len(pa_all) < 8 or len(kb) < 8:
        return None, 0
    m = [x for x, y in (p for p in bf.knnMatch(da, db, k=2) if len(p) == 2) if x.distance < 0.75 * y.distance]
    if len(m) < 8:
        return None, len(m)
    pa = np.float32([pa_all[x.queryIdx] for x in m])
    pb = np.float32([kb[x.trainIdx].pt for x in m])
    H, inl = cv2.findHomography(pa, pb, cv2.RANSAC, 4.0)
    return H, int(inl.sum()) if inl is not None else 0


def ssim(a, b, mask):
    a = a.astype(np.float32); b = b.astype(np.float32)
    C1, C2 = 6.5025, 58.5225
    k = (7, 7)
    mu_a, mu_b = cv2.blur(a, k), cv2.blur(b, k)
    sa = cv2.blur(a * a, k) - mu_a ** 2
    sb = cv2.blur(b * b, k) - mu_b ** 2
    sab = cv2.blur(a * b, k) - mu_a * mu_b
    s = ((2 * mu_a * mu_b + C1) * (2 * sab + C2)) / ((mu_a ** 2 + mu_b ** 2 + C1) * (sa + sb + C2))
    return float(s[mask].mean()) if mask.any() else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref"); ap.add_argument("t0", type=float); ap.add_argument("t1", type=float); ap.add_argument("cand")
    ap.add_argument("--out"); ap.add_argument("--coarse_fps", type=float, default=2)
    g = ap.parse_args()
    rf = frames(g.ref, g.t0, g.t1 - g.t0)
    mid = rf[len(rf) // 2]
    cf = coarse_feats(g.cand, g.coarse_fps)
    mid_s = cv2.resize(mid, (320, int(round(mid.shape[0] * 320 / mid.shape[1]))))
    best = []
    for flip in (False, True):
        m = cv2.flip(mid_s, 1) if flip else mid_s
        for i, c in enumerate(cf):
            H, n = homog_feats(c, m)
            if H is not None:
                best.append((n, i / g.coarse_fps, flip, H))
    best.sort(key=lambda x: -x[0])
    if not best or best[0][0] < 12:
        res = {"found": False, "best_inliers": best[0][0] if best else 0}
    else:
        fps = native_fps(g.cand)
        res = None
        for n, tc, flip, _ in best[:3]:
            # 手本の真ん中のコマが cand の tc 近くにある → 始まりは tc - 半分
            half = (g.t1 - g.t0) / 2
            lo = max(0, tc - half - 1.0)
            win = frames(g.cand, lo, (g.t1 - g.t0) + 2.0)
            rr = [cv2.flip(x, 1) if flip else x for x in rf]
            Hm, _ = homog(win[min(len(win) - 1, int(round((tc - lo) * fps)))], rr[len(rr) // 2])
            if Hm is None:
                continue
            h, w = rr[0].shape
            mask = cv2.warpPerspective(np.ones_like(win[0]), Hm, (w, h)) > 0
            warped = [cv2.warpPerspective(x, Hm, (w, h)) for x in win]
            for off in range(0, max(1, len(win) - len(rr) + 1)):
                s = np.mean([ssim(warped[off + j], rr[j], mask) for j in range(len(rr))])
                if res is None or s > res["ssim"]:
                    res = {"found": True, "start": round(lo + off / fps, 4), "flip": flip, "ssim": round(float(s), 4),
                           "inliers": n, "H": Hm.tolist(), "cand_fps": fps, "ref_frames": len(rf)}
        res = res or {"found": False, "best_inliers": best[0][0]}
    print(json.dumps({k: v for k, v in res.items() if k != "H"}, ensure_ascii=False))
    if g.out:
        json.dump(res, open(g.out, "w"))


if __name__ == "__main__":
    main()
