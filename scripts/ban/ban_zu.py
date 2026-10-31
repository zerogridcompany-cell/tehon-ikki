# 段3 図の素材：手本の動画から、CapCut で置く字の箱（板ごと）だけ黒く消した動画 → zu.mp4（線が伸びる・点が動く・面が回る、は全部そのまま残る）
# 使い方：python3 ban_zu.py <ban の置き場>   （zu_extra_mask.json＝{"状態": [[x0,y0,x1,y1], ...]} で手で消す所を足せる）
import json, os, sys, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ban_lib import Ban
b = Ban(sys.argv[1]); W, H = b.W, b.H; st = b.states(); R = b.rows()
extra = json.load(open(b.p('zu_extra_mask.json'))) if os.path.exists(b.p('zu_extra_mask.json')) else {}
masks = []
for s in st:
    mk = np.zeros((H, W), bool)
    for t, (x0, y0, x1, y1) in R.get(s['i'], []):
        if b.capcut(s['i'], t): mk[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = True
    for x0, y0, x1, y1 in extra.get(str(s['i']), []): mk[y0:y1, x0:x1] = True
    masks.append(mk)
dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', b.ref(), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(b.FPS), '-i', '-', '-c:v', 'libx264', '-crf', '8', '-preset', 'medium', '-pix_fmt', 'yuv420p', b.p('zu.mp4')], stdin=subprocess.PIPE)
n = 0; si = 0
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    while si + 1 < len(st) and n >= st[si]['f1']: si += 1
    fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy(); fr[masks[si]] = 0
    enc.stdin.write(fr.tobytes()); n += 1
enc.stdin.close(); enc.wait(); print('図の素材のコマ', n)
