"""大きさ表（size_sift.py の出力）の s・dx・dy を、カットのファイルにかける（うちの絵→手本の大きさと位置）。
python3 size_apply.py <作業> <大きさ表.json> --ids 0,1,2 [--damp 1.0]
- 変形＝真ん中 c を中心に s 倍して (dx,dy) ずらす。外に出た所は折り返し（黒い縁を出さん）
- 前の物は cuts/<番号>.mp4.bak_size_<日時>（何回回しても控えが残る）
- 書いたら書き出し→size_sift で測り直す。✅ になるまでくり返す（表の 🔴 が 0 になるまで）
"""
import argparse, json, os, shutil, subprocess, time
import cv2, numpy as np
W, H = 1280, 720


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("table"); ap.add_argument("--ids", required=True); ap.add_argument("--damp", type=float, default=1.0); ap.add_argument("--per", action="store_true", help="表の per（コマごとの s・dx・dy）をコマ番号で直線に補間してかける（寄りの速さが手本と違うカット）")
    g = ap.parse_args()
    T = {str(r["cut"]): r for r in json.load(open(g.table))}
    stamp = time.strftime("%m%d%H%M")
    for i in g.ids.split(","):
        r = T.get(i)
        if not r or "s" not in r: print(i, "表に無い"); continue
        s = 1 + (r["s"] - 1) * g.damp; dx, dy = r["dx"] * g.damp, r["dy"] * g.damp
        M = np.array([[s, 0, (1 - s) * W / 2 + dx], [0, s, (1 - s) * H / 2 + dy]], np.float32)
        src = f"{g.w}/cuts/{i}.mp4"; shutil.copy(src, f"{src}.bak_size_{stamp}")
        cap = cv2.VideoCapture(src); out = []
        per = sorted(r.get("per") or []) if g.per else []
        f0 = round(float(r["t"]) * 29.97); k = 0
        while True:
            ok, f = cap.read()
            if not ok: break
            if len(per) >= 2:
                fr = f0 + k; xs = [p_[0] for p_ in per]
                s_ = 1 + (float(np.interp(fr, xs, [p_[1] for p_ in per])) - 1) * g.damp
                M = np.array([[s_, 0, (1 - s_) * W / 2 + float(np.interp(fr, xs, [p_[2] for p_ in per])) * g.damp],
                              [0, s_, (1 - s_) * H / 2 + float(np.interp(fr, xs, [p_[3] for p_ in per])) * g.damp]], np.float32)
            out.append(cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)); k += 1
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", src], stdin=subprocess.PIPE)
        p.stdin.write(np.array(out).tobytes()); p.stdin.close(); p.wait()
        print(f"{i} s {s:.4f} dx {dx:+.1f} dy {dy:+.1f} → {len(out)}コマ書いた")


if __name__ == "__main__":
    main()
