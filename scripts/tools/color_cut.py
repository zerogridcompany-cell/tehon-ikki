"""カットのファイルの色を、look 込みで手本に当て直す（色ごとに平均と散らばりをそろえる・カット全体で1つ・濃さ 0.85〜1.4）。retime や写真の差し替えの後に、色の差（ΔE）が増えた時に（10/28 r2 v81：129 は明るさ 91→74・ΔE 2.1→2.4）。
python3 color_cut.py <作業> <書き出し_noaudio.mp4> [--ids 1,2] [--write]
- 測るのは書き出し（Remotion の全部の層が乗った絵）。直すのはカットのファイル（look は1次なので、書き出しでの1次の直しをカットの色に戻して当てる）。一枚絵（green）がコマの半分以上を覆うカットは飛ばす
- 物差し＝コマごとの平均の色（Lab）の差 ΔE と、白黒 SSIM（640）。どちらも look（コマごと・Remotion と同じ）を通してから
- 入れる条件＝ΔE が 0.3 以上下がって、SSIM の下がりが 0.002 以内。前の物は .bak_col
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f, pre_f
import retime
from geo import geo, half
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("render"); ap.add_argument("--ids", default=""); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w)
retime.use_geo(w); G = geo(w); FPS, W, H = G["FPS"], G["W"], G["H"]; MW, MH = half(w)
ids = set(a.ids.split(",")) if a.ids else None
RA = rd(glob.glob(f"{w}/ref/*.mp4")[0]); VA = rd(os.path.join(w, a.render))
import json
GR = json.load(open(f"{w}/proj/src/green.json")); OFF = json.load(open(f"{w}/proj/src/layer_off.json"))
def plate_cover(f0, f1):
    cov = set()
    for v in GR.values():
        for f in range(max(f0, v["f0"]), min(f1, v["f1"] + 1)):
            if not any(o["f0"] <= f < o["f1"] and "green" in o["off"] for o in OFF): cov.add(f)
    return len(cov) / max(1, f1 - f0)
lab = lambda x: cv2.cvtColor(cv2.resize(x, (G["SW"] // 2, G["SH"] // 2), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32).mean(0)
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH))
txt = np.ones((H, W), bool); txt[round(300 * H / 720):round(420 * H / 720)] = False  # 字幕の帯（r2 の 300〜420 行）は高さの比で移す
for l in open(f"{w}/eye/segs.txt"):
    if ":" not in l: continue
    cut = l.split(":")[0].strip()
    if ids and cut not in ids: continue
    cp = f"{w}/cuts/{cut}.mp4"
    if not os.path.exists(cp): continue
    s0, s1 = map(float, l.split(":")[1].split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
    R = RA[f0:f1]; n = len(R); C = rd(cp)
    if len(C) < n or n < 2: continue
    if plate_cover(f0, f1) > 0.5: continue
    LK = looks(w, f0, n)
    P = [VA[f0 + k] for k in range(n)]
    X = np.concatenate([p[::6, ::6][txt[::6, ::6]] for p in P]).astype(np.float32)
    Y = np.concatenate([r[::6, ::6][txt[::6, ::6]] for r in R]).astype(np.float32)
    # 平均と散らばりをそろえる（polyfit の傾きは中身がずれると縮む＝絵が薄くなる。10/28 r2 61・10・2 が濃さ 0.70 に）
    kb = [(Y[:, c].std() / max(X[:, c].std(), 1e-3), 0.0) for c in range(3)]
    kb = [(float(np.clip(k, 0.85, 1.4)), float(np.clip(Y[:, c].mean() - np.clip(k, 0.85, 1.4) * X[:, c].mean(), -60, 60))) for c, (k, _) in enumerate(kb)]
    Q = [np.clip(np.stack([p[..., c].astype(np.float32) * kb[c][0] + kb[c][1] for c in range(3)], -1), 0, 255).astype(np.uint8) for p in P]
    de0 = np.mean([np.linalg.norm(lab(R[k]) - lab(P[k])) for k in range(n)]); de1 = np.mean([np.linalg.norm(lab(R[k]) - lab(Q[k])) for k in range(n)])
    s0_ = np.mean([ssim(g(R[k]), g(P[k])) for k in range(0, n, max(1, n // 6))]); s1_ = np.mean([ssim(g(R[k]), g(Q[k])) for k in range(0, n, max(1, n // 6))])
    ok = de1 < de0 - 0.3 and s1_ >= s0_ - 0.002
    print(f"カット {cut} ΔE {de0:.2f}→{de1:.2f} SSIM {s0_:.3f}→{s1_:.3f} {'入れる' if ok else ''}", flush=True)
    if ok and a.write:
        out = C.copy()
        for k in range(len(C)):
            lk = LK[min(k, n - 1)]
            p = post_f(C[k], (lk[0], lk[1], 0.0))
            q = np.clip(np.stack([p[..., c].astype(np.float32) * kb[c][0] + kb[c][1] for c in range(3)], -1), 0, 255)
            out[k] = pre_f(q, lk)
        if not os.path.exists(cp + ".bak_col"): shutil.copy(cp, cp + ".bak_col")
        pp = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", G["FPS_FF"], "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cp], stdin=subprocess.PIPE)
        pp.stdin.write(out.tobytes()); pp.stdin.close(); pp.wait()
