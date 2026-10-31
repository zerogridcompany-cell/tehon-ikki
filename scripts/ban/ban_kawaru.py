# 段2 板の中で変わる字（時計 00.6 s・ITERATION 00→01・02/06→03/06）：CapCut で置く字の箱を1コマずつ見て、中身が変わった所で区切る→区切りごとに読む
# 使い方：python3 ban_kawaru.py <ban の置き場>  → kawaru.json {"状態:元の字:箱x0": [[頭コマ, 終わりコマ, 読んだ字], ...]}
import json, os, sys, subprocess
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ban_lib import Ban
b = Ban(sys.argv[1]); W, H = b.W, b.H
N = os.path.getsize(b.p('gray_full.raw')) // (W * H); a = np.memmap(b.p('gray_full.raw'), np.uint8, 'r', shape=(N, H, W))
R = b.rows(); os.makedirs(b.p('kw'), exist_ok=True); todo = []; spans = {}
for s in b.states():
    for t, (x0, y0, x1, y1) in R.get(s['i'], []):
        if not b.capcut(s['i'], t) or s['f1'] - s['f0'] < 2: continue
        c = a[s['f0']:s['f1'], max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2].astype(np.int16)
        dd = np.abs(np.diff(c, axis=0)).reshape(len(c) - 1, -1); ch = (dd > 40).sum(1)   # はっきり変わった画素の数
        cuts = [s['f0'] + k + 1 for k in np.where(ch > max(6, 0.004 * dd.shape[1]))[0]]
        if not cuts: continue
        edges = [s['f0']]
        for k in cuts:                                # 続けて変わるコマ（フェードの途中）はまとめて、変わり終わったコマを頭に
            if k - edges[-1] <= 1 and len(edges) > 1: edges[-1] = k
            else: edges.append(k)
        edges.append(s['f1']); key = f"{s['i']}:{t}:{x0}"; spans[key] = []
        for e0, e1 in zip(edges[:-1], edges[1:]):
            if e1 - e0 < 1: continue
            fr = min(e1 - 1, e0 + 1); p = b.p('kw', f"{s['i']:02d}_{x0}_{e0}.png")
            Image.fromarray(np.asarray(a[fr, max(0, y0 - 6):y1 + 6, max(0, x0 - 10):x1 + 40])).resize(((x1 - x0 + 50) * 3, (y1 - y0 + 12) * 3), Image.LANCZOS).save(p)
            spans[key].append([e0, e1, p]); todo.append(p)
read = {}
for k in range(0, len(todo), 200):
    for l in subprocess.run([b.p('ocr_en')] + todo[k:k + 200], capture_output=True, text=True).stdout.splitlines():
        f, t, _ = l.split('\t'); read.setdefault(f, []).append(t)
for key, sp in spans.items():
    for x in sp: x[2] = ' '.join(read.get(os.path.basename(x[2]), ['']))
json.dump(spans, open(b.p('kawaru.json'), 'w'), ensure_ascii=False, indent=0, default=int)
print('変わる字', len(spans), '区切り', sum(len(v) for v in spans.values()))
