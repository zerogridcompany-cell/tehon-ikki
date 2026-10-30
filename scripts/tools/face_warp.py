"""人の写真・映像のカットを、顔の大きさと位置で手本に合わせる（10/27 r2：ECC はぼけ・縁に引っぱられて拡大の向きを逆に測った）。
python3 face_warp.py <作業> <カット番号> [--out tmp/face/<番号>.mp4] [--write]
- 手本とうち（cuts/<番号>.mp4）の各コマで顔（mediapipe）を測り、倍率＝手本の顔の幅÷うち・移動＝顔の真ん中の差。コマの中央値で1つの相似にする
- 縮める時に出る縁は BORDER_REFLECT で埋める（黒い縁を出さん）
- 顔が 3コマ未満しか取れんカットはやらん
"""
import argparse, glob, json, os, shutil, subprocess
import cv2, numpy as np, mediapipe as mp
W, H = 1280, 720
FD = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.4)


def rd(p, a=None, b=None):
    vf = ["-vf", f"select=between(n\\,{a}\\,{b - 1})", "-vsync", "0"] if a is not None else []
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p] + vf + ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()


def face(im):
    r = FD.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    if not r.detections: return None
    b = max(r.detections, key=lambda d: d.location_data.relative_bounding_box.width).location_data.relative_bounding_box
    return np.array([(b.xmin + b.width / 2) * W, (b.ymin + b.height / 2) * H, b.width * W])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("--out"); ap.add_argument("--write", action="store_true")
    g = ap.parse_args()
    s = [s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"] if str(s["i"]) == str(g.i)][0]
    f0 = int(round(s["t0"] * 29.97)); src = f"{g.w}/cuts/{g.i}.mp4"
    F = rd(src); R = rd(sorted(glob.glob(f"{g.w}/ref/*.mp4"))[0], f0, f0 + len(F)); n = min(len(F), len(R))
    P = []
    for j in range(0, n, max(1, n // 8)):
        a, b = face(R[j]), face(F[j])
        if a is not None and b is not None: P.append((a, b))
    if len(P) < 3: print(g.i, "顔が足らん", len(P)); return
    sc = float(np.median([a[2] / b[2] for a, b in P])); ca = np.median([a[:2] for a, _ in P], 0); cb = np.median([b[:2] for _, b in P], 0)
    M = np.array([[sc, 0, ca[0] - sc * cb[0]], [0, sc, ca[1] - sc * cb[1]]], np.float32)
    print(f"{g.i} 顔 {len(P)}コマ 倍率 {sc:.3f} 移動 {ca - cb}")
    out = [cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT) for f in F]
    o = g.out or f"{g.w}/tmp/face/{g.i}.mp4"; os.makedirs(os.path.dirname(o), exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", o], stdin=subprocess.PIPE)
    p.stdin.write(np.array(out).tobytes()); p.stdin.close(); p.wait(); print("書いた", o)
    if g.write:
        if not os.path.exists(src + ".bak_face"): shutil.copy(src, src + ".bak_face")
        shutil.copy(o, src); print("置き換えた", src)


if __name__ == "__main__":
    main()
