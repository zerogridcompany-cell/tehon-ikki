"""手元の動画を1秒に1コマ（--fps）で読み、顔の位置・大きさ・確かさ・顔まわりの明暗の形を索引にする（人の場面の代わり探し用）。
python3 face_index.py <動画…> --out tmp/face_index.npz [--fps 1]
"""
import argparse, subprocess, sys
import cv2, numpy as np, mediapipe as mp
ap = argparse.ArgumentParser(); ap.add_argument("vids", nargs="+"); ap.add_argument("--out", required=True); ap.add_argument("--fps", type=float, default=1)
a = ap.parse_args()
FD = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.6)
rows = []; pats = []
for v in a.vids:
    r = subprocess.Popen(["ffmpeg", "-v", "error", "-i", v, "-vf", f"fps={a.fps},scale=640:360", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    i = 0
    while True:
        b = r.stdout.read(640 * 360 * 3)
        if len(b) < 640 * 360 * 3: break
        im = np.frombuffer(b, np.uint8).reshape(360, 640, 3)
        d = FD.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
        if d.detections:
            for det in d.detections:
                bb = det.location_data.relative_bounding_box
                cx, cy, fh = bb.xmin + bb.width / 2, bb.ymin + bb.height / 2, bb.height
                x0, y0 = int(max(0, (cx - fh * 1.1) * 640)), int(max(0, (cy - fh * 1.1) * 360)); x1, y1 = int(min(640, (cx + fh * 1.1) * 640)), int(min(360, (cy + fh * 1.1) * 360))
                if x1 - x0 < 8 or y1 - y0 < 8: continue
                p = cv2.resize(cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY), (32, 32)).astype(np.float32)
                rows.append((v, i / a.fps, cx, cy, fh, det.score[0], *cv2.resize(im, (4, 3)).astype(np.float32).ravel() / 255)); pats.append((p - p.mean()) / (p.std() + 1e-6))
        i += 1
    print(v, i, "コマ", len(rows), "顔", flush=True)
np.savez(a.out, meta=np.array([r[:2] for r in rows], dtype=object), num=np.array([r[2:] for r in rows], np.float32), pat=np.array(pats, np.float32))
