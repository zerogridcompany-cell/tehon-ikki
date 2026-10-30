"""face_index の中から、手本のコマの顔（位置・大きさ・顔まわりの明暗の形・全体の色）に近い候補を上位 N 件出し、並べ絵を作る。
python3 face_query.py <作業> <手本のコマ> --index tmp/face_index.npz [--top 12] [--out tmp/fq_<コマ>.jpg]
"""
import argparse, glob, os, subprocess, sys
import cv2, numpy as np, mediapipe as mp
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("f", type=int); ap.add_argument("--index", default="tmp/face_index.npz"); ap.add_argument("--top", type=int, default=12); ap.add_argument("--out")
a = ap.parse_args()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo, half
G = geo(a.w); SW, SH = G["SW"], G["SH"]; MW, MH = half(a.w)
Z = np.load(f"{a.w}/{a.index}", allow_pickle=True); meta, num, pat = Z["meta"], Z["num"], Z["pat"]
ref = glob.glob(f"{a.w}/ref/*.mp4")[0]
r = subprocess.run(["ffmpeg", "-v", "error", "-i", ref, "-vf", f"fps={G['FPS_FF']},select=eq(n\\,{a.f}),scale={MW}:{MH}", "-vsync", "0", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
im = np.frombuffer(r.stdout, np.uint8).reshape(MH, MW, 3)
d = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.4).process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
if not d.detections: print("手本に顔が取れん"); raise SystemExit(1)
bb = max(d.detections, key=lambda x: x.location_data.relative_bounding_box.width).location_data.relative_bounding_box
cx, cy, fh = bb.xmin + bb.width / 2, bb.ymin + bb.height / 2, bb.height
x0, y0 = int(max(0, (cx - fh * 1.1) * MW)), int(max(0, (cy - fh * 1.1) * MH)); x1, y1 = int(min(MW, (cx + fh * 1.1) * MW)), int(min(MH, (cy + fh * 1.1) * MH))
p = cv2.resize(cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY), (32, 32)).astype(np.float32); p = (p - p.mean()) / (p.std() + 1e-6)
col = cv2.resize(im, (4, 3)).astype(np.float32).ravel() / 255
sc = (pat.reshape(len(pat), -1) @ p.ravel()) / p.size - 1.5 * np.abs(np.log(num[:, 2] / fh)) - 1.0 * np.abs(num[:, 0] - cx) - 1.0 * np.abs(num[:, 1] - cy) - 0.8 * np.abs(num[:, 4:] - col).mean(1) + 0.3 * num[:, 3]
idx = np.argsort(-sc)[: a.top]
cells = [cv2.resize(im, (SW, SH))]
for i in idx:
    v, t = meta[i]
    rr = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", v, "-frames:v", "1", "-vf", f"scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    c = np.frombuffer(rr, np.uint8).reshape(SH, SW, 3).copy() if len(rr) == SW * SH * 3 else np.zeros((SH, SW, 3), np.uint8)
    cv2.putText(c, f"{len(cells)} {v.split('/')[-1][:14]} {t:.0f}s {sc[i]:.2f}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1); cells.append(c)
    print(len(cells) - 1, v, round(float(t), 1), round(float(sc[i]), 3))
while len(cells) % 4: cells.append(np.zeros_like(cells[0]))
cv2.imwrite(f"{a.w}/" + (a.out or f"tmp/fq_{a.f}.jpg"), np.vstack([np.hstack(cells[i:i + 4]) for i in range(0, len(cells), 4)]))
