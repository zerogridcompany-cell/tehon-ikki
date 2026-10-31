# 段4 字の入り方（フェード）を1コマずつ測る：同じ字が続く間（板をまたいでも1本）の、字の墨の明るさ÷その間で一番明るい時
# 使い方：python3 ban_fade.py <ban の置き場> → fade.json {"frame": {"コマ": 割合}, "text": {"状態:字:箱x0": {"コマ": 割合}}}
#   frame＝そのコマに出とる字の中央値（板ごと一斉のフェード）・text＝その字だけ中央値とずれる（ずらし入り・1字ずつ等）時の曲がり
#   🔴 代表コマで割らん（手本R の最後の板は代表コマがフェードの途中＝割合が 2.4 になった）。🔴 変わる字（kawaru）も外さん（入りのフェードが「変わる」に拾われとる）
#   🔴 CapCut のフェードのアニメ（6724916044072227332）は曲がり方が手本と違う（手本R：入り2コマ目 手本0.27／アニメ0.21）＝測った値を1コマずつ打つ
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ban_lib import Ban
b = Ban(sys.argv[1]); W, H = b.W, b.H
N = os.path.getsize(b.p('gray_full.raw')) // (W * H); a = np.memmap(b.p('gray_full.raw'), np.uint8, 'r', shape=(N, H, W))
R = b.rows(); st = b.states()
G = []                                                # 同じ字・同じ場所（±6px）が続く板をつないだ組
for s in st:
    g = b.gray(s['i'])
    for t, box in R.get(s['i'], []):
        if not b.capcut(s['i'], t): continue
        ib, _ = b.ink_box(g, box)
        for z in G:
            if z['t'] == t and z['f1'] == s['f0'] and abs(z['ib'][0] - ib[0]) <= 6 and abs(z['ib'][1] - ib[1]) <= 6: z['f1'] = s['f1']; z['keys'].append(f"{s['i']}:{t}:{box[0]}"); break
        else: G.append(dict(t=t, ib=ib, f0=s['f0'], f1=s['f1'], g=g, keys=[f"{s['i']}:{t}:{box[0]}"]))
cur = {}
for k, z in enumerate(G):
    X0, Y0, X1, Y1 = z['ib']; X0, Y0, X1, Y1 = max(0, X0 - 4), max(0, Y0 - 4), min(W, X1 + 4), min(H, Y1 + 4)
    c = z['g'][Y0:Y1, X0:X1]
    if c.size < 20: continue
    bg = np.percentile(c, 10)                          # 箱の中の明るさの合計（にじみ・大きさの変化があっても墨の量で測れる＝手本R v12 で書き出しと手本が 42.5／41.7 で合った測り方）
    v = a[z['f0']:z['f1'], Y0:Y1, X0:X1].astype(np.float32).reshape(z['f1'] - z['f0'], -1).mean(1) - bg
    top = np.percentile(v, 95)
    if top < 30: continue
    cur[k] = np.clip(v / top, 0, 1.0)
FR = {}; per = {}
for k, c in cur.items():
    for j, f in enumerate(range(G[k]['f0'], G[k]['f1'])): per.setdefault(f, []).append((k, c[j]))
for f, lst in sorted(per.items()):
    m = float(np.median([v for _, v in lst]))
    if m < 0.99: FR[str(f)] = round(m, 4)
TX = {}
for k, c in cur.items():
    dev = [abs(c[j] - FR.get(str(f), 1.0)) for j, f in enumerate(range(G[k]['f0'], G[k]['f1']))]
    if max(dev) <= 0.1: continue
    # その字だけの曲がりは「0近くから上がる入り」「0近くへ下がる終わり」だけ採る（途中で明るくなる光り・暗くなる揺れは図の側＝手本R の TRAP は 38→57 に光る）
    lo = np.where(c < 0.99)[0]; n = len(c); ok = np.zeros(n, bool)
    if len(lo) and lo[0] == 0 and c[0] < 0.3:
        j = 0
        while j < n and c[j] < 0.99: ok[j] = True; j += 1
    if len(lo) and lo[-1] == n - 1 and c[-1] < 0.3:
        j = n - 1
        while j >= 0 and c[j] < 0.99: ok[j] = True; j -= 1
    if ok.any():
        crv = {str(f): (round(float(c[j]), 4) if ok[j] else FR.get(str(f), 1.0)) for j, f in enumerate(range(G[k]['f0'], G[k]['f1'])) if (c[j] < 0.99 and ok[j]) or FR.get(str(f), 1.0) < 0.99}
        for key in G[k]['keys']: TX[key] = crv
json.dump({'frame': FR, 'text': TX}, open(b.p('fade.json'), 'w'), indent=0)
print('字の組', len(G), '・測れた組', len(cur), '・フェードのコマ', len(FR), '・その字だけ入り方が違う字', len(TX))
