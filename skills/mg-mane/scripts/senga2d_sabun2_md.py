# sabun2 の json から表（md）だけ作り直す。使い方: python3 tools/sabun2_md.py <名> [動画の名]
import json, sys, numpy as np, os
NAME = sys.argv[1]; V = sys.argv[2] if len(sys.argv) > 2 else NAME
OUT = json.load(open(f'rikai/{NAME}.json'))
for o in OUT:
    for k in list(o.keys()):
        if o[k] is None: o[k] = float('nan')
import os
KR = json.load(open('rikai/kamera_raw.json')); KO = json.load(open(f'rikai/kamera_{NAME}.json')) if os.path.exists(f'rikai/kamera_{NAME}.json') else None
def col(ok, warn): return '🟢' if ok else ('🟡' if warn else '🔴')
L = [f'# {NAME}（{V}）カットごとの差・手本の秒→うちの秒は rikai/rf.json', '',
     '線：位置 ±2% 画面・大きさ ±3%（輪郭をぼかして ECC で合わせた相似のずれ）・カメラの寄り ±3%・流し ±2%・回り ±3°（kamera_<名>.json があれば手本と同じ道具で測った終わりの値）・形 F1 ≥0.55（0.40〜 🟡）・線の太さ ±25%・光のにじみ ±0.10・背景 ΔE ≤5（差し色は意図で除く）', '',
     '| カット | 手本(秒) | うち(秒) | 位置 dx,dy % | 大きさ % | 寄り 手本→うち | 流し 手本→うち % | 形 F1 | 線 px 手本/うち | にじみ 手本/うち | 背景 ΔE | 判定 |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
nr = ny = 0
for o in OUT:
    ca, cb = o['cam_ref'], o['cam_ours']
    if not (0.5 < ca[0] < 2): ca = (1.0, 0.0, 0.0, 0.0)
    if not (0.5 < cb[0] < 2): cb = (1.0, 0.0, 0.0, 0.0)
    sc = (cb[0] / ca[0] - 1) * 100; pan = np.hypot(cb[1] - ca[1], cb[2] - ca[2]); rot = abs(cb[3] - ca[3]) + abs(o['rot_al'] if o['rot_al'] == o['rot_al'] else 0)
    ws = (o['w_ours'] / o['w_ref'] - 1) * 100 if (o['w_ref'] == o['w_ref'] and o['w_ours'] == o['w_ours'] and o['w_ref']) else 0
    gd = abs(o['glow_ours'] - o['glow_ref']) if o['glow_ref'] == o['glow_ref'] and o['glow_ours'] == o['glow_ours'] else 0
    ck = [(abs(o['dx']) <= 2 and abs(o['dy']) <= 2, abs(o['dx']) <= 4 and abs(o['dy']) <= 4), (abs(o['ds']) <= 3, abs(o['ds']) <= 6),
          (abs(sc) <= 3 and pan <= 2 and rot <= 3, abs(sc) <= 6 and pan <= 4 and rot <= 6), (o['f1'] >= 0.55, o['f1'] >= 0.40),
          (abs(ws) <= 25, abs(ws) <= 40), (gd <= 0.10, gd <= 0.2), (o['de_bg'] <= 5, o['de_bg'] <= 10)]
    bad = [n for n, (g, w) in zip(['位置', '大きさ', 'カメラ', '形', '線', 'にじみ', '背景'], ck) if not g]
    red = [n for n, (g, w) in zip(['位置', '大きさ', 'カメラ', '形', '線', 'にじみ', '背景'], ck) if not w]
    j = '🟢' if not bad else ('🔴 ' + '・'.join(red) if red else '🟡 ' + '・'.join(bad)); nr += bool(red); ny += bool(bad and not red)
    o['judge'] = j
    L.append(f"| {o['cut']} | {o['ref'][0]}–{o['ref'][1]} | {o['ours'][0]}–{o['ours'][1]} | {o['dx']:+.1f},{o['dy']:+.1f} | {o['ds']:+.1f} | {ca[0]:.3f}→{cb[0]:.3f} | {ca[1]:+.1f},{ca[2]:+.1f}→{cb[1]:+.1f},{cb[2]:+.1f} | {o['f1']:.2f} | {o['w_ref']:.1f}/{o['w_ours']:.1f} | {o['glow_ref']:.2f}/{o['glow_ours']:.2f} | {o['de_bg']:.1f} | {j} |")
L.insert(2, f'**🔴 {nr} カット・🟡 {ny} カット・🟢 {len(OUT) - nr - ny} カット**（全 {len(OUT)} カット）')
open(f'rikai/{NAME}.md', 'w').write('\n'.join(L) + '\n'); print(f'🔴{nr} 🟡{ny} 🟢{len(OUT) - nr - ny}')
