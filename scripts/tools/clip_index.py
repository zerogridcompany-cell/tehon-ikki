"""手元の動画を CLIP（openai/clip-vit-base-patch32）で索引にし、手本のコマと見た目の意味が近いコマを探す（人の場面の代わり探し）。
build: python3 clip_index.py build <動画…> --out tmp/clip_index.npz [--fps 1]
query: python3 clip_index.py query <作業> <手本のコマ> [--index tmp/clip_index.npz] [--top 11] [--text "英語の説明"]
"""
import argparse, glob, os, subprocess, sys
import cv2, numpy as np, torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
dev = "mps" if torch.backends.mps.is_available() else "cpu"
M = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(dev).eval(); P = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
def emb(ims):
    with torch.no_grad():
        x = P(images=[Image.fromarray(cv2.cvtColor(i, cv2.COLOR_BGR2RGB)) for i in ims], return_tensors="pt").to(dev)
        e = M.get_image_features(**x); return torch.nn.functional.normalize(e, dim=-1).cpu().numpy()
ap = argparse.ArgumentParser(); ap.add_argument("mode"); ap.add_argument("args", nargs="*"); ap.add_argument("--out"); ap.add_argument("--fps", type=float, default=1)
ap.add_argument("--index", default="tmp/clip_index.npz"); ap.add_argument("--top", type=int, default=11); ap.add_argument("--text")
a = ap.parse_args()
if a.mode == "build":
    meta, E = [], []
    for v in a.args:
        r = subprocess.Popen(["ffmpeg", "-v", "error", "-i", v, "-vf", f"fps={a.fps},scale=224:126", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE); buf = []; i = 0
        while True:
            b = r.stdout.read(224 * 126 * 3)
            if len(b) < 224 * 126 * 3: break
            buf.append(np.frombuffer(b, np.uint8).reshape(126, 224, 3)); meta.append((v, i / a.fps)); i += 1
            if len(buf) == 64: E.append(emb(buf)); buf = []
        if buf: E.append(emb(buf))
        print(v, i, flush=True)
    np.savez(a.out, meta=np.array(meta, dtype=object), e=np.concatenate(E)); sys.exit()
w, f = a.args[0], int(a.args[1])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo, half
GG = geo(w); SW, SH = GG["SW"], GG["SH"]; MW, MH = half(w)
Z = np.load(f"{w}/{a.index}", allow_pickle=True); meta, E = Z["meta"], Z["e"]
r = subprocess.run(["ffmpeg", "-v", "error", "-i", glob.glob(f"{w}/ref/*.mp4")[0], "-vf", f"fps={GG['FPS_FF']},select=eq(n\\,{f}),scale={MW}:{MH}", "-vsync", "0", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
im = np.frombuffer(r.stdout, np.uint8).reshape(MH, MW, 3); q = emb([im])[0]
if a.text:
    with torch.no_grad():
        t = M.get_text_features(**P(text=[a.text], return_tensors="pt", padding=True).to(dev)); q = q + torch.nn.functional.normalize(t, dim=-1).cpu().numpy()[0]; q /= np.linalg.norm(q)
sc = E @ q; idx = []; seen = []
for i in np.argsort(-sc):
    v, t = meta[i]
    if any(v == sv and abs(t - st) < 3 for sv, st in seen): continue
    seen.append((v, t)); idx.append(i)
    if len(idx) >= a.top: break
cells = [cv2.resize(im, (SW, SH))]
for i in idx:
    v, t = meta[i]
    rr = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", v, "-frames:v", "1", "-vf", f"scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    cc = np.frombuffer(rr, np.uint8).reshape(SH, SW, 3).copy() if len(rr) == SW * SH * 3 else np.zeros((SH, SW, 3), np.uint8)
    cv2.putText(cc, f"{len(cells)} {v.split('/')[-1][:12]} {t:.0f}s {sc[i]:.2f}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1); cells.append(cc)
    print(len(cells) - 1, v, round(float(t), 1), round(float(sc[i]), 3))
while len(cells) % 4: cells.append(np.zeros_like(cells[0]))
cv2.imwrite(f"{w}/tmp/ci_{f}.jpg", np.vstack([np.hstack(cells[i:i + 4]) for i in range(0, len(cells), 4)]))
