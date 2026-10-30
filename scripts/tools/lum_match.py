"""手本の明るさの変化（場面の中のフェード）を、うちの実写の切り出しに毎コマ写す。
python3 lum_match.py <作業> scan            … 全カットで、手本の明るさが場面の中で 35% 以上変わる物を出す
python3 lum_match.py <作業> apply <番号>    … cuts/<番号>.mp4 に毎コマの倍率（手本÷うち・字の箱は外す・0.05〜1.6）をかけて書き直す（元は cuts/<番号>_nolum.mp4 に残す）
"""
import json, os, subprocess, sys
import cv2, numpy as np
w = sys.argv[1]; cmd = sys.argv[2]
shots = {s['i']: s for s in json.load(open(f'{w}/eye/out.json'))['shots']}
ref = [p for p in os.listdir(f'{w}/ref') if p.endswith('.mp4')][0]; ref = f'{w}/ref/{ref}'
fps = 30.0
texts = json.load(open(f'{w}/proj/src/texts.json'))
def tmask(t, h, wd):
    m = np.ones((h, wd), bool)
    for x in texts:
        if x['t0'] - 0.1 <= t <= x['t1'] + 0.1:
            b = x['box']; m[max(0, int(b[1]) - 16):int(b[3]) + 16, max(0, int(b[0]) - 16):int(b[2]) + 16] = False
    return m
def lums(path, f0, n, t0):
    cap = cv2.VideoCapture(path); cap.set(cv2.CAP_PROP_POS_FRAMES, f0); out = []
    for j in range(n):
        ok, fr = cap.read()
        if not ok: break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32); m = tmask(t0 + j / fps, g.shape[0], g.shape[1])
        out.append(float(g[m].mean()) if m.any() else float(g.mean()))
    return out
if cmd == 'scan':
    for i, s in sorted(shots.items()):
        if s['kind'] != 'live' or not os.path.exists(f'{w}/cuts/{i}.mp4'): continue
        f0 = int(round(s['t0'] * fps)); n = int(round((s['t1'] - s['t0']) * fps))
        R = lums(ref, f0, n, s['t0']); O = lums(f'{w}/cuts/{i}.mp4', 0, n, s['t0'])
        if len(R) < 4 or len(O) < 4: continue
        k = max(2, len(R) // 5)
        rs, re_ = np.mean(R[:k]), np.mean(R[-k:]); os_, oe = np.mean(O[:k]), np.mean(O[-k:])
        rr = re_ / max(1, rs); orr = oe / max(1, os_)
        flag = '🔴' if abs(np.log(max(0.05, rr) / max(0.05, orr))) > 0.35 else ''
        if flag: print(i, s['t0'], s['t1'], '手本 始→終', round(rs, 1), round(re_, 1), 'うち', round(os_, 1), round(oe, 1), flag)
elif cmd == 'apply':
    i = int(sys.argv[3]); s = shots[i]; f0 = int(round(s['t0'] * fps)); n = int(round((s['t1'] - s['t0']) * fps))
    src = f'{w}/cuts/{i}.mp4'; bak = f'{w}/cuts/{i}_nolum.mp4'
    if not os.path.exists(bak): os.rename(src, bak)
    R = lums(ref, f0, n, s['t0']); O = lums(bak, 0, n, s['t0'])
    cap = cv2.VideoCapture(bak); W = int(cap.get(3)); H = int(cap.get(4))
    p = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '30', '-i', '-', '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', src], stdin=subprocess.PIPE)
    gains = []
    for j in range(len(O)):
        ok, fr = cap.read()
        if not ok: break
        g = float(np.clip(R[min(j, len(R) - 1)] / max(1.0, O[j]), 0.05, 1.6)); gains.append(round(g, 2))
        p.stdin.write(np.clip(fr.astype(np.float32) * g, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
    print(i, '倍率', gains[:3], '…', gains[-6:])
