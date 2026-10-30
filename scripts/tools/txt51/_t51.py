"""_t51.py  字の道具（txt51）の共通の部品。単独では回さん。

- 作業フォルダの決まり（tehon-ikki）：<作業>/ref/*.mp4（手本）・<作業>/proj/src/texts.json か caps.json（字の表）・<作業>/cfg.json
- 字の表は2つの形を読める：
  texts 形（51）＝[{id, text, font, w, color, t0, t1(秒), reveal?, fs, x, y, sx, ...}]
  caps 形（r2） ＝[{i, w(語), f0, f1(コマ・f1 も出とる), kind, fs, x, y, sx, box}]
  → 道具の中では全部 texts 形に直して扱う（id＝"c<i>"・t0＝f0/fps・t1＝(f1+1)/fps・font＝kind・色は既定 #ffffff）。
  書き戻す時は元の形に戻す（caps 形なら x,y,fs,sx と足した値だけ戻す）
- 🔴 コマの読み方：ffmpeg -ss (f+0.5)/fps は f+1 から読む（51 の再開4・5回目の落とし穴）。ここは (f-0.5)/fps で「ちょうど f」を読む
- 大きさ：51 の px の数字（余白 24・帯 18・線 9.6px＝幅の 0.5% など）は 1080 の高さの時の値。K＝高さ/1080 で掛けて使う
"""
import os, sys, json, glob, subprocess, argparse
import numpy as np

def probe(mp4):
    """→ (幅, 高さ, fps, コマ数)"""
    o = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                        'stream=width,height,r_frame_rate,nb_read_packets', '-of', 'json', mp4], capture_output=True, text=True).stdout
    s = json.loads(o)['streams'][0]; a, b = s['r_frame_rate'].split('/')
    return int(s['width']), int(s['height']), float(a) / float(b), int(s.get('nb_read_packets') or 0)

def base_args(desc, need_ours=True, ver=True):
    """共通の引数。--work が無ければ手本・字の表・型を全部 --ref/--texts/--sheet で渡す"""
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument('--work', default=None, help='作業フォルダ（<作業>/ref/*.mp4・proj/src/texts.json か caps.json）')
    ap.add_argument('--ref', default=None, help='手本の mp4（既定＝<作業>/ref/*.mp4 の1本目）')
    ap.add_argument('--texts', default=None, help='字の表（既定＝<作業>/proj/src/texts.json → 無ければ caps.json）')
    ap.add_argument('--look', default=None, help='caps 形の時の look.json（太さ・横の倍率・書体）。既定＝字の表の横の look.json')
    ap.add_argument('--sheet', default=None, help='字だけの層の書き出し（element-00.png…・Txt51.tsx の TxtSheet）。既定＝<out>/sheet')
    ap.add_argument('--out', default=None, help='出す所（既定＝<作業>/txt51）')
    ap.add_argument('--ids', default=None, help='この字だけ（id をカンマで）')
    return ap

def resolve(a):
    w = a.work
    if a.ref is None:
        c = sorted(glob.glob(f'{w}/ref/*.mp4')) if w else []
        if not c: sys.exit('手本が無い：--ref か <作業>/ref/*.mp4')
        a.ref = c[0]
    if a.texts is None:
        for p in (f'{w}/proj/src/texts.json', f'{w}/proj/src/caps.json'):
            if w and os.path.exists(p): a.texts = p; break
        else: sys.exit('字の表が無い：--texts')
    if a.out is None: a.out = f'{w}/txt51' if w else os.path.join(os.path.dirname(os.path.abspath(a.texts)), 'txt51')
    os.makedirs(a.out, exist_ok=True)
    if a.sheet is None: a.sheet = f'{a.out}/sheet'
    a.W, a.H, a.fps, a.N = probe(a.ref)
    a.K = a.H / 1080.0
    if a.look is None:
        p = os.path.join(os.path.dirname(os.path.abspath(a.texts)), 'look.json'); a.look = p if os.path.exists(p) else None
    a.T, a.fmt = load_texts(a.texts, a.fps, a.look)
    a.idset = set(a.ids.split(',')) if a.ids else None
    return a

# ── 字の表 ────────────────────────────────────────────
def is_caps(L): return bool(L) and isinstance(L[0], dict) and 'f0' in L[0] and 'w' in L[0] and 'text' not in L[0]

def caps_to_texts(L, fps, look=None):
    lk = json.load(open(look)) if look else {}
    T = []
    for c in L:
        k = c.get('kind', 'sans')
        d = dict(id=c.get('id', f"c{c['i']}"), text=c['w'], font=k, w=lk.get(f'{k}W', c.get('wght', 700)),
                 color=c.get('color', '#ffffff'), t0=c['f0'] / fps, t1=(c['f1'] + 1) / fps, reveal=c.get('reveal'),
                 fs=c['fs'], x=c['x'], y=c['y'], sx=lk.get(f'{k}Sx', c.get('sx', 1.0)))
        for kk, v in c.items():
            if kk not in ('i', 'w', 'f0', 'f1', 'kind', 'fs', 'x', 'y', 'sx') and kk not in d: d[kk] = v
        d['_i'] = c['i']; d['_sxl'] = d['sx']; T.append(d)   # _sxl＝読んだ時の横の倍率（変わってなければ caps に書き戻さん）
    return T

def load_texts(p, fps, look=None):
    L = json.load(open(p))
    return (caps_to_texts(L, fps, look), 'caps') if is_caps(L) else (L, 'texts')

KEEP_OUT = {'id', 'text', 'font', 'w', 't0', 't1'}
def save_texts(p, T, fmt, fps):
    if fmt == 'texts':
        json.dump([{k: v for k, v in d.items() if not k.startswith('_')} for d in T], open(p, 'w'), ensure_ascii=False, indent=1); return
    L = json.load(open(p)); by = {c['i']: c for c in L}
    for d in T:
        c = by[d['_i']]
        for k, v in d.items():
            if k in KEEP_OUT or k.startswith('_') or (k == 'sx' and v == d.get('_sxl')) or (v is None and k not in c) or (k == 'color' and v == '#ffffff' and 'color' not in c): continue
            c[k] = v
        c['f0'] = int(round(d['t0'] * fps)); c['f1'] = int(round(d['t1'] * fps)) - 1
    json.dump(L, open(p, 'w'), ensure_ascii=False)

def frame_of(d, fps):
    """測るコマ＝出揃ってから消えるまでの真ん中（51 の ocr_match・TextSheet51 と同じ決まり）"""
    a = max(d['t0'], (d.get('reveal') or [0, 0])[1]); return int(round(fps * (a + d['t1']) / 2))

def hexbgr(h):
    h = h.lstrip('#'); return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.float32)

# ── 絵を読む ──────────────────────────────────────────
def _ss(f, fps): return f'{max(0.0, (f - 0.5) / fps):.4f}'

def grab(src, f, fps, cache):
    import cv2
    os.makedirs(cache, exist_ok=True); p = f'{cache}/{f:05d}.png'
    if not os.path.exists(p):
        subprocess.run(['nice', '-n', '10', 'ffmpeg', '-nostdin', '-v', 'error', '-threads', '2', '-ss', _ss(f, fps), '-i', src,
                        '-frames:v', '1', p], check=True)
    return cv2.imread(p)

def clip(src, f0, n, x0, y0, w, h, fps, gray=False):
    raw = subprocess.run(['nice', '-n', '10', 'ffmpeg', '-nostdin', '-v', 'error', '-threads', '2', '-ss', _ss(f0, fps), '-i', src,
                          '-frames:v', str(n), '-vf', f'crop={w}:{h}:{x0}:{y0}' + (',format=gray' if gray else ''),
                          '-f', 'rawvideo', '-pix_fmt', 'gray' if gray else 'bgr24', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8)
    return (a.reshape(-1, h, w) if gray else a.reshape(-1, h, w, 3)).astype(np.float32)

def sheet_alpha(sheet, k):
    """字だけの層の k 番目（element-kk.png・透明の地）の濃さ 0..1。無い・空なら None"""
    import cv2
    for p in (f'{sheet}/element-{k:02d}.png', f'{sheet}/element-{k:03d}.png', f'{sheet}/element-{k:04d}.png'):
        if os.path.exists(p):
            im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
            if im is None or im.ndim < 3 or im.shape[2] < 4: return None
            A = im[..., 3].astype(np.float32) / 255
            return A if (A > 0.5).sum() >= 50 else None
    return None

def ebox(A, pad, W, H, th=0.5):
    """型の箱を pad だけ広げる（偶数にそろえる＝ffmpeg の crop）"""
    ys, xs = np.where(A > th)
    return (max(0, xs.min() - pad) // 2 * 2, max(0, ys.min() - pad) // 2 * 2,
            min(W, xs.max() + pad + 2) // 2 * 2, min(H, ys.max() + pad + 2) // 2 * 2)

def glyphs(a):
    """字の型を1字ずつの塊に（つながった塊→横に3割以上重なる塊はまとめる＝i の点・" など）"""
    import cv2
    n, lab, st, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8), 8)
    cs = [[st[i, 0], st[i, 0] + st[i, 2], [i]] for i in range(1, n) if st[i, 4] > 15]
    cs.sort(key=lambda c: c[0]); out = []
    for c in cs:
        if out and min(out[-1][1], c[1]) - max(out[-1][0], c[0]) > 0.3 * min(c[1] - c[0], out[-1][1] - out[-1][0]):
            out[-1][1] = max(out[-1][1], c[1]); out[-1][2] += c[2]
        else: out.append(c)
    return [np.isin(lab, c[2]) for c in out]

def zoom_at(d, t, W, H):
    """字の拡大（zoom＝[t0,t1,倍]・zoomk＝[[秒,倍],…]）の倍率と中心。中心＝d.zc（無ければ画面の真ん中）＝Txt51.tsx と同じ"""
    zc = tuple(d.get('zc') or (W / 2, H / 2))
    if d.get('zoomk'):
        k = d['zoomk']
        if t < k[0][0]: return k[0][1], zc
        for i in range(1, len(k)):
            if t < k[i][0]: return k[i - 1][1] + (k[i][1] - k[i - 1][1]) * min(1, max(0, (t - k[i - 1][0]) / (k[i][0] - k[i - 1][0]))), zc
        return k[-1][1], zc
    if d.get('zoom'):
        z0, z1, zk = d['zoom']; p = min(1, max(0, (t - z0) / (z1 - z0))); e = p * p * (3 - 2 * p); return 1 + (zk - 1) * e, zc
    return 1.0, zc
