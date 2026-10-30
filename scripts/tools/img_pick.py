"""手本の小さいカット（写真が2〜4コマで替わるモンタージュの1枚）ごとに、手元の候補画像の山から一番合う写真を選ぶ。

python3 img_pick.py <作業フォルダ> <segs.json> <画像フォルダ…> [--out pick.json]
- segs.json＝[{"id":2004,"f0":4,"f1":8}, …]（手本のコマ番号・30fps）
- 点＝手本のコマ（字幕の帯を隠す）と、拡大・移動・回転だけで重ねた画像の SSIM × 覆う割合。目印 12 未満は外す
- 同じ点なら大きい画像を選ぶ（細くて帯が出るのを防ぐ）
- 出力＝{id: {"img":path, "inl":…, "cover":…, "ssim":…, "score":…, "A":2x3（画像→手本の画素・r2 は 1280x720）}}
"""
import argparse, glob, json, os, subprocess, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo, half
W, H, FPS = 1280, 720, 29.97   # main で geo(<作業>) に替わる（10/30）
MW, MH, SW, SH = 640, 360, 320, 180
sift = cv2.SIFT_create(3000)
bf = cv2.BFMatcher()


def ref_frame(ref, f):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, f - 0.3) / FPS:.4f}", "-i", ref, "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(H, W, 3)


def gray_ssim(a, b, m):
    a = a.astype(np.float32); b = b.astype(np.float32)
    C1, C2 = 6.5, 58.5
    mu1 = cv2.GaussianBlur(a, (7, 7), 1.5); mu2 = cv2.GaussianBlur(b, (7, 7), 1.5)
    s1 = cv2.GaussianBlur(a * a, (7, 7), 1.5) - mu1 ** 2; s2 = cv2.GaussianBlur(b * b, (7, 7), 1.5) - mu2 ** 2
    s12 = cv2.GaussianBlur(a * b, (7, 7), 1.5) - mu1 * mu2
    s = ((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 ** 2 + mu2 ** 2 + C1) * (s1 + s2 + C2))
    return float(s[m].mean()) if m.any() else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("segs"); ap.add_argument("dirs", nargs="+"); ap.add_argument("--out", default="pick.json")
    g = ap.parse_args()
    global W, H, FPS, MW, MH, SW, SH
    G = geo(g.w); W, H, FPS, SW, SH = G["W"], G["H"], G["FPS"], G["SW"], G["SH"]; MW, MH = half(g.w)
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    pool = []
    for d in g.dirs:
        for p in sorted(glob.glob(f"{d}/*")):
            im = cv2.imread(p)
            if im is None or min(im.shape[:2]) < 120:
                continue
            s = 640 / max(im.shape[:2])
            sm = cv2.resize(im, None, fx=s, fy=s) if s < 1 else im
            k, ds = sift.detectAndCompute(cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY), None)
            if ds is not None and len(k) > 20:
                pool.append((p, im.shape[1], im.shape[0], s if s < 1 else 1.0, k, ds))
    print("候補の画像", len(pool), flush=True)
    out = {}
    for sg in json.load(open(g.segs)):
        f = (sg["f0"] + sg["f1"] - 1) // 2
        R = ref_frame(ref, f)
        Rg = cv2.cvtColor(R, cv2.COLOR_BGR2GRAY)
        mask_txt = np.ones_like(Rg, bool); mask_txt[round(300 * H / 720):round(420 * H / 720)] = False  # 字幕の帯（r2 の 300〜420 行を高さの比で）
        Rs = cv2.resize(Rg, (MW, MH))
        kr, dr = sift.detectAndCompute(Rs, None)
        best = None
        for p, w, h, s, k, ds in pool:
            if dr is None:
                break
            mm = [a for a, b in (q for q in bf.knnMatch(ds, dr, k=2) if len(q) == 2) if a.distance < 0.75 * b.distance]
            if len(mm) < 12:
                continue
            A, inl = cv2.estimateAffinePartial2D(np.float32([k[m.queryIdx].pt for m in mm]), np.float32([kr[m.trainIdx].pt for m in mm]),
                                                 method=cv2.RANSAC, ransacReprojThreshold=4.0)
            if A is None or int(inl.sum()) < 12:
                continue
            # 画像（元の大きさ）→手本の画素
            A3 = np.vstack([A, [0, 0, 1]])
            Af = np.diag([W / MW, H / MH, 1.0]) @ A3 @ np.diag([s, s, 1.0])
            im = cv2.imread(p)
            wv = cv2.warpAffine(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), Af[:2], (W, H))
            cv = cv2.warpAffine(np.ones(im.shape[:2], np.uint8), Af[:2], (W, H)) > 0
            cover = float(cv.mean())
            ss = gray_ssim(cv2.resize(wv, (SW, SH)), cv2.resize(Rg, (SW, SH)), cv2.resize((cv & mask_txt).astype(np.uint8), (SW, SH)) > 0)
            sc = ss * cover
            cand = (round(sc, 4), w * h, p, int(inl.sum()), round(cover, 3), round(ss, 3), Af[:2].tolist())
            if best is None or cand[:2] > best[:2]:
                best = cand
        if best:
            out[str(sg["id"])] = {"img": best[2], "inl": best[3], "cover": best[4], "ssim": best[5], "score": best[0], "A": best[6]}
            print(sg["id"], "→", os.path.basename(os.path.dirname(best[2])) + "/" + os.path.basename(best[2]), "目印", best[3], "覆う", best[4], "近さ", best[5], flush=True)
        else:
            print(sg["id"], "合う画像なし", flush=True)
    json.dump(out, open(g.out, "w"), indent=1)


if __name__ == "__main__":
    main()
