"""写真が2〜4コマで替わるモンタージュで、小さいカット（手本のコマ f0〜f1）ごとに写真をはめて、カットの動画の該当コマだけ差し替える。

python3 sub_photo.py <作業フォルダ> <pick.json> --ids 2017,2055 [--segs tmp/open_segs.json]
- pick.json＝img_pick.py の出力（img・A＝画像→手本1280x720）
- 1コマずつ：A から ECC（拡大・移動・回転）で詰める→色を手本に合わせる（色ごとに1次・字幕の帯を外す）→ぼかし 0〜3 の良い方
- 差し替え先＝eye/out.json でその手本のコマを含むカットの cuts/<番号>.mp4（無ければ黒から作る）。前の物は .bak_sub に控え
"""
import argparse, glob, json, os, shutil, subprocess
import cv2
import numpy as np

W, H = 1280, 720
FPS = 29.97  # 手本の r_frame_rate＝2997/100


def read_all(p, fps="2997/100"):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"fps={fps},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()


def ref_frames(ref, f0, f1):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, f0 - 0.3) / FPS:.4f}", "-i", ref, "-frames:v", str(f1 - f0),
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3)


def ssim_g(a, b, m):
    a = cv2.resize(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (320, 180)).astype(np.float32)
    b = cv2.resize(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (320, 180)).astype(np.float32)
    m = cv2.resize(m.astype(np.uint8), (320, 180)) > 0
    C1, C2 = 6.5, 58.5
    mu1 = cv2.GaussianBlur(a, (7, 7), 1.5); mu2 = cv2.GaussianBlur(b, (7, 7), 1.5)
    s1 = cv2.GaussianBlur(a * a, (7, 7), 1.5) - mu1 ** 2; s2 = cv2.GaussianBlur(b * b, (7, 7), 1.5) - mu2 ** 2
    s12 = cv2.GaussianBlur(a * b, (7, 7), 1.5) - mu1 * mu2
    s = ((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 ** 2 + mu2 ** 2 + C1) * (s1 + s2 + C2))
    return float(s[m].mean()) if m.any() else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("pick"); ap.add_argument("--ids", required=True); ap.add_argument("--segs", default="tmp/open_segs.json"); ap.add_argument("--frame", action="store_true", help="白地・黒地の小さい枠の MG：手本で地の色と違う所の箱の中だけに写真を出す")
    g = ap.parse_args()
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    pick = json.load(open(g.pick))
    segs = {str(s["id"]): s for s in json.load(open(f"{g.w}/{g.segs}"))}
    shots = json.load(open(f"{g.w}/eye/out.json"))["shots"]
    txt = np.ones((H, W), bool); txt[300:420] = False
    cache = {}
    for sid in g.ids.split(","):
        p, sg = pick[sid], segs[sid]
        f0, f1 = sg["f0"], sg["f1"]
        R = ref_frames(ref, f0, f1)
        im = cv2.imread(p["img"])
        A0 = np.array(p["A"], np.float32)
        img_g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        outs = []
        for j, r in enumerate(R):
            # ECC は 480 幅で（画像→手本の A を 480 幅に直して詰める）
            s = 480 / W
            A = A0.copy()
            a480 = np.diag([s, s, 1.0]) @ np.vstack([A, [0, 0, 1]])
            wv = cv2.warpAffine(img_g, a480[:2].astype(np.float32), (480, 270))
            rg = cv2.resize(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), (480, 270))
            try:
                _, D = cv2.findTransformECC(rg.astype(np.float32), wv.astype(np.float32), np.eye(2, 3, dtype=np.float32), cv2.MOTION_AFFINE,
                                            (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5), None, 3)
                # wv(x) ≈ rg(D x) ＝ 手本の座標 D x に画像の点が来る → 画像→手本 = D^-1 ∘ a480
                D3 = np.vstack([D, [0, 0, 1]])
                a480 = np.linalg.inv(D3) @ a480
            except cv2.error:
                pass
            Af = (np.diag([1 / s, 1 / s, 1.0]) @ a480)[:2].astype(np.float32)
            wc = cv2.warpAffine(im, Af, (W, H))
            cv = cv2.warpAffine(np.ones(im.shape[:2], np.uint8), Af, (W, H)) > 0
            if g.frame:
                bg = np.median(np.concatenate([r[:20].reshape(-1, 3), r[-20:].reshape(-1, 3)]), axis=0)
                dm = (np.abs(r.astype(np.int16) - bg.astype(np.int16)).max(2) > 40).astype(np.uint8)
                dm = cv2.morphologyEx(dm, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
                ys, xs = np.nonzero(dm)
                if len(xs) > 400:
                    box = np.zeros((H, W), bool); box[ys.min():ys.max() + 1, xs.min():xs.max() + 1] = True
                    cv = cv & box
            m = cv if g.frame else (cv & txt)  # 小さい枠は字幕の帯の高さにある＝帯を外すと色合わせが空振りする
            fit = wc.astype(np.float32)
            if m.sum() > 1000:
                for c in range(3):
                    x = wc[..., c][m].astype(np.float32); y = r[..., c][m].astype(np.float32)
                    k, b = np.polyfit(x, y, 1)
                    fit[..., c] = wc[..., c] * k + b
            fit = np.clip(fit, 0, 255).astype(np.uint8)
            best = (-1, fit)
            for bl in (0, 1, 2, 3):
                fb = cv2.GaussianBlur(fit, (0, 0), bl) if bl else fit
                sc = ssim_g(fb, r, m)
                if sc > best[0]:
                    best = (sc, fb)
            o = best[1].copy()
            # 写真の外は手本の地の色（白地・黒地の枠の MG）
            out_m = ~cv & txt
            if g.frame:
                o[~cv] = np.median(np.concatenate([r[:20].reshape(-1, 3), r[-20:].reshape(-1, 3)]), axis=0).astype(np.uint8)
            else:
                o[~cv] = np.median(r[out_m], axis=0).astype(np.uint8) if out_m.sum() > 1000 else 0
            outs.append((f0 + j, o, best[0]))
        # 差し替え先のカット
        for fa, o, sc in outs:
            sh = [x for x in shots if int(round(float(x["t0"]) * FPS)) <= fa < int(round(float(x["t1"]) * FPS))]
            if not sh:
                continue
            i = str(sh[0]["i"]); c0 = int(round(float(sh[0]["t0"]) * FPS)); n = int(round(float(sh[0]["t1"]) * FPS)) - c0
            if i not in cache:
                cp = f"{g.w}/cuts/{i}.mp4"
                F = read_all(cp)[:n] if os.path.exists(cp) else np.zeros((n, H, W, 3), np.uint8)
                if len(F) < n:
                    F = np.concatenate([F, np.zeros((n - len(F), H, W, 3), np.uint8)])
                cache[i] = F
            cache[i][fa - c0] = o
        print(sid, "コマ", f0, "〜", f1 - 1, "近さ", [round(x[2], 3) for x in outs], flush=True)
    for i, F in cache.items():
        cp = f"{g.w}/cuts/{i}.mp4"
        if os.path.exists(cp) and not os.path.exists(cp + ".bak_sub"):
            shutil.copy(cp, cp + ".bak_sub")
        tmp = cp + ".tmp.mp4"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100",
                              "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        p.stdin.write(F.tobytes()); p.stdin.close(); p.wait()
        shutil.move(tmp, cp)
        print("書いた", cp, flush=True)


if __name__ == "__main__":
    main()
