#!/usr/bin/python3
"""手本のカットを測って、生成AIの指示文に入れる数字を出す（人が出ん実写を生成で埋める時の下調べ・2026-10-26）

/usr/bin/python3 ref_look.py <作業フォルダ> <カット番号> [--out shirabe/seisei/<番号>.json]
- 測る物：コマ数・秒・縦横・明るさ（平均）・色（Lab の平均と主な色3つ）・ぼけ（Laplacian 分散・小さいほどぼけ）
  ・動き（DIS フローの平均の大きさ[px/コマ]と向き・カメラの寄り引き＝中心からの放射の符号）・モーションブラー（動きの向きと直交／平行の鋭さの比）
  ・最初・真ん中・最後のコマの jpg（shirabe/seisei/<番号>_{0,1,2}.jpg）＝生成の参照・目の確認に使う
- 出す物：json＋画面に「指示文の下書き（英語）」。what（eye/out.json）＋測った数字＋「no people」「no text」
"""
import argparse, json, os, subprocess, sys
import numpy as np, cv2


def frames(path, t0, t1, w=640):
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
    W, H = int(pr[0]), int(pr[1]); num, den = pr[2].split("/"); fps = float(num) / float(den)
    h = int(round(H * w / W / 2) * 2)
    o = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", path, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return np.frombuffer(o, np.uint8).reshape(-1, h, w, 3), fps, (W, H)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut", type=int); ap.add_argument("--out")
    g = ap.parse_args()
    import glob
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    s = {x["i"]: x for x in json.load(open(f"{g.w}/eye/out.json"))["shots"]}[g.cut]
    F, fps, size = frames(ref, float(s["t0"]), float(s["t1"]))
    n = len(F)
    od = g.out or f"{g.w}/shirabe/seisei/{g.cut}.json"; os.makedirs(os.path.dirname(od), exist_ok=True)
    gray = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in F]
    # 明るさ・色
    lab = np.concatenate([cv2.cvtColor(f, cv2.COLOR_BGR2LAB).reshape(-1, 3) for f in F[:: max(1, n // 4)]]).astype(np.float32)
    L, a, b = lab.mean(0)
    px = np.concatenate([f.reshape(-1, 3) for f in F[:: max(1, n // 4)]]).astype(np.float32)
    px = px[np.random.RandomState(0).choice(len(px), min(20000, len(px)), replace=False)]
    _, lbl, cen = cv2.kmeans(px, 3, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(lbl.ravel(), minlength=3) / len(lbl)
    cols = sorted([("#%02x%02x%02x" % (int(c[2]), int(c[1]), int(c[0])), round(float(p), 2)) for c, p in zip(cen, share)], key=lambda x: -x[1])
    # ぼけ（Laplacian 分散）
    lap = [float(cv2.Laplacian(x, cv2.CV_64F).var()) for x in gray]
    # 動き（DIS）
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    mags, angs, zooms = [], [], []
    h, w = gray[0].shape; yy, xx = np.mgrid[0:h, 0:w]; cx, cy = w / 2, h / 2
    for i in range(n - 1):
        fl = dis.calc(gray[i], gray[i + 1], None)
        m = np.hypot(fl[..., 0], fl[..., 1]); mags.append(float(m.mean()))
        angs.append(float(np.degrees(np.arctan2(-fl[..., 1].mean(), fl[..., 0].mean()))))
        rad = ((xx - cx) * fl[..., 0] + (yy - cy) * fl[..., 1]) / (np.hypot(xx - cx, yy - cy) + 1e-6)
        zooms.append(float(rad.mean()))
    mag = float(np.mean(mags)) if mags else 0.0; ang = float(np.median(angs)) if angs else 0.0; zoom = float(np.mean(zooms)) if zooms else 0.0
    # モーションブラー＝動きの向きに沿った鋭さ／直交の鋭さ（1 より小さいほど向きにぼけとる）
    kx = np.array([[-1, 0, 1]], np.float32); ky = kx.T
    gx = np.mean([np.abs(cv2.filter2D(x.astype(np.float32), -1, kx)).mean() for x in gray]); gy = np.mean([np.abs(cv2.filter2D(x.astype(np.float32), -1, ky)).mean() for x in gray])
    th = np.radians(ang); along = abs(gx * np.cos(th)) + abs(gy * np.sin(th)); across = abs(gx * np.sin(th)) + abs(gy * np.cos(th))
    mb = float(along / (across + 1e-6))
    for k, i in enumerate([0, n // 2, n - 1]):
        cv2.imwrite(f"{os.path.dirname(od)}/{g.cut}_{k}.jpg", F[i])
    cam = "slow push-in" if zoom > 0.15 else ("slow pull-out" if zoom < -0.15 else "locked-off")
    move = "static" if mag < 0.3 else ("subtle drift" if mag < 1.5 else ("steady pan/track" if mag < 5 else "fast whip"))
    blur = "very soft, heavy motion blur" if mb < 0.6 else ("natural 180° shutter motion blur" if mb < 0.9 else "crisp, little motion blur")
    out = {"cut": g.cut, "t0": s["t0"], "t1": s["t1"], "frames": n, "sec": round(n / 25, 2), "ref_size": size, "fps": fps,
           "what": s.get("what"), "L_mean": round(float(L), 1), "lab_ab": [round(float(a) - 128, 1), round(float(b) - 128, 1)], "colors": cols,
           "sharp_laplacian": round(float(np.mean(lap)), 1), "flow_px_per_frame": round(mag, 2), "flow_dir_deg": round(ang, 1), "zoom_sign": round(zoom, 3),
           "motion_blur_ratio": round(mb, 2), "camera": cam, "movement": move, "blur_words": blur,
           "prompt_draft": f"{s.get('what','')}. {cam} camera, {move} ({mag:.1f}px/frame toward {ang:.0f}°), {blur}. "
                           f"Overall brightness {'dark' if L < 70 else ('mid' if L < 150 else 'bright')} (L={L:.0f}), palette {', '.join(c for c, _ in cols)}. "
                           f"{'Vertical 9:16' if size[1] > size[0] else 'Horizontal 16:9'} {size[0]}x{size[1]}, {n / 25:.1f}s. Photoreal documentary footage, no people, no text, no logos, no captions."}
    json.dump(out, open(od, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("cut", "frames", "sec", "sharp_laplacian", "flow_px_per_frame", "flow_dir_deg", "zoom_sign", "motion_blur_ratio", "camera", "movement", "blur_words", "colors")}, ensure_ascii=False))
    print("PROMPT:", out["prompt_draft"]); print("→", od)


if __name__ == "__main__":
    main()
