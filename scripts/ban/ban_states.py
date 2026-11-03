# 段1 板に分ける：手本の切り替え（cfg の events か、自動で出した切り替え）→ 状態（板）の表・代表コマ・1コマずつの明るさ・字の行
# 使い方：python3 ban_states.py <ban の置き場> [--force]
#   出力：states.json（[{i,f0,f1,rep}]）・f/sNN.png・gray_full.raw（全コマの明るさ・W×H）・ocr.tsv
import json, os, sys, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ban_lib import Ban
b = Ban(sys.argv[1]); force = '--force' in sys.argv; W, H = b.W, b.H; REF = b.ref()
N = int(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', REF], capture_output=True, text=True).stdout.strip())
raw = b.p('gray_full.raw')
if force or not os.path.exists(raw) or os.path.getsize(raw) != N * W * H:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', REF, '-f', 'rawvideo', '-pix_fmt', 'gray', raw], check=True)
a = np.memmap(raw, np.uint8, 'r', shape=(N, H, W))
small = a[:, ::4, ::4].astype(np.int16); d = np.abs(np.diff(small, axis=0)).mean(axis=(1, 2))   # d[k]＝コマ k→k+1 の変わり方
if force or not os.path.exists(b.p('states.json')):
    ev = b.cfg.get('events')
    if isinstance(ev, str):
        j = json.load(open(os.path.expanduser(ev))); ev = j['events'] if isinstance(j, dict) else j
    if not ev:                                        # 切り替えの表が無い時：変わり方の山（cut_thr 以上・前後3コマで一番）
        thr = b.cfg.get('cut_thr', 3.0)
        ev = [k + 1 for k in range(len(d)) if d[k] >= thr and d[k] == d[max(0, k - 3):k + 4].max()]
    edges = [0] + sorted(int(e) for e in ev if 0 < int(e) < N) + [N]
    st = []
    for i, (f0, f1) in enumerate(zip(edges[:-1], edges[1:])):
        lo = f0 + int((f1 - f0) * 0.4); cand = list(range(max(f0 + 1, lo), f1)) or [f0]
        br = {f: float(small[f].mean()) for f in range(f0, f1)}; top = max(br.values())
        cand = [f for f in cand if br[f] >= 0.85 * top] or [max(br, key=br.get)]   # 🔴 暗くなり切ったコマを選ばん（tehonR の最後の板は消えかけ＝字が読めず消えのフェードが抜けた）
        rep = min(cand, key=lambda f: (round(float(d[f - 1]) if f > 0 else 0.0, 2), -f))   # 一番止まっとるコマ（同じなら後ろ＝入りのフェードが終わった所）
        st.append(dict(i=i, f0=f0, f1=f1, rep=int(rep)))
    json.dump(st, open(b.p('states.json'), 'w'))
st = b.states(); os.makedirs(b.p('f'), exist_ok=True)
from PIL import Image
for s in st:
    p = b.p('f', f"s{s['i']:02d}.png")
    if force or not os.path.exists(p):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', REF, '-vf', f"select='eq(n\\,{s['rep']})'", '-vsync', '0', '-frames:v', '1', p], check=True)
OCR = b.p('ocr_en')
if not os.path.exists(OCR):
    subprocess.run(['swiftc', '-O', '-o', OCR, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ocr_en.swift')], check=True)
if force or not os.path.exists(b.p('ocr.tsv')):
    out = subprocess.run([OCR] + [b.p('f', f"s{s['i']:02d}.png") for s in st], capture_output=True, text=True).stdout
    open(b.p('ocr.tsv'), 'w').write(out)
R = b.rows(); n = sum(1 for i, v in R.items() for t, _ in v if b.capcut(i, t))
print(f'コマ {N}・板 {len(st)}・字の行 {sum(len(v) for v in R.values())}（CapCut の字にする行 {n}）')
