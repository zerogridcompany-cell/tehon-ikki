# 手本を N コマおきに全部並べた一覧（rikai/ken2/）。使い方: python3 ken_ichiran.py ref/x.mp4 rikai/ken2 [おき=2] [列=8] [行=6]
import cv2, sys, os
from PIL import Image, ImageDraw
src, out = sys.argv[1], sys.argv[2]; st = int(sys.argv[3]) if len(sys.argv) > 3 else 2
C = int(sys.argv[4]) if len(sys.argv) > 4 else 8; R = int(sys.argv[5]) if len(sys.argv) > 5 else 6
os.makedirs(out, exist_ok=True); cap = cv2.VideoCapture(src); tw, th = 240, 135; buf = []; f = 0; k = 0
def flush():
    global buf, k
    if not buf: return
    sh = Image.new('RGB', (C * tw, R * th), 'white'); d = ImageDraw.Draw(sh)
    for i, (fn, im) in enumerate(buf):
        x, y = (i % C) * tw, (i // C) * th; sh.paste(im, (x, y)); d.rectangle([x, y, x + 40, y + 11], fill='black'); d.text((x + 2, y), str(fn), fill='yellow')
    sh.save(f'{out}/k{k:02d}_{buf[0][0]:05d}.jpg', quality=80); k += 1; buf = []
while True:
    ok, im = cap.read()
    if not ok: break
    if f % st == 0:
        buf.append((f, Image.fromarray(cv2.resize(im, (tw, th), interpolation=cv2.INTER_AREA)[:, :, ::-1])))
        if len(buf) == C * R: flush()
    f += 1
flush(); print(k, '枚', f, 'コマ')
