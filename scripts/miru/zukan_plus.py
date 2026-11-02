# 段0 見るの足し（10/31 目の試験で 21% やった所を見る）：zukan.json に足す
#  ban＝板の切り替えと板の中の段（全体の変わり方の山・山の比・広がり。暗い所は明るさをそろえて）
#  ugoku_koma＝図が動くコマ（切り替え以外で変わり方 >0.15）・oto_ato_ms＝音は絵の何ms後（30〜150Hz の鳴り始め）
#  fade＝入りと終わりの1コマずつの曲がり（画面の明るさの合計÷落ち着いた後）・jitai＝字体（字の墨と棚の字体を重ねる）
# 使い方：python3 zukan_plus.py <作業>（<作業>/zukan/zukan.json と手本＝meta.ref）
import json, os, sys, subprocess, re, glob
import numpy as np
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(D, '..', 'tools')); sys.path.insert(0, os.path.join(D, '..', 'ban'))
W_ = sys.argv[1]; ZP = f'{W_}/zukan/zukan.json'; Z = json.load(open(ZP)); REF = Z['meta']['ref']; FPS = float(Z['meta'].get('fps', 30))
pr = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', REF], capture_output=True, text=True).stdout.strip().split(',')
VW, VH = int(pr[0]), int(pr[1]); SW = 480; SH = int(round(SW * VH / VW / 2) * 2)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', REF, '-vf', f'scale={SW}:{SH},format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
g = np.frombuffer(raw, np.uint8).reshape(-1, SH, SW).astype(np.float32); n = len(g) - 1
top = np.maximum(np.percentile(g.reshape(len(g), -1), 99.5, axis=1), 20)
# ---- 板の切り替え
ban = {}
for norm in (False, True):
    gg = g / top[:, None, None] * 255 if norm else g
    m = np.abs(np.diff(gg, axis=0)) > 24; p = m.mean(axis=(1, 2)) * 100
    hh, ww = SH // 9 * 9, SW // 16 * 16
    spread = (m[:, :hh, :ww].reshape(n, 9, hh // 9, 16, ww // 16).mean(axis=(2, 4)) > 0.01).sum(axis=(1, 2))
    for k in range(n):
        nbv = np.median([p[j] for j in range(max(0, k - 4), min(n, k + 5)) if j != k])
        if p[k] >= 0.7 and p[k] / (nbv + 0.05) >= 2 and spread[k] >= 5 and p[k] == p[max(0, k - 2):k + 3].max():
            dim = top[k] < 0.9 * np.percentile(top, 90)
            if norm and not dim: continue
            ban.setdefault(k + 1, dict(f=k + 1, p=round(float(p[k]), 2), masu=int(spread[k]), kurai=bool(dim)))
Z['ban'] = sorted(ban.values(), key=lambda x: x['f']); BF = [x['f'] for x in Z['ban']]
# ---- 図が動くコマ
d = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2)); near = {f + j for f in BF for j in (-1, 0, 1)}
Z['ugoku_koma'] = [int(k + 1) for k in np.where(d > 0.15)[0] if (k + 1) not in near]
# ---- 音は絵の何ms後
from oto_ms import tachiagari
y = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', REF, '-ac', '1', '-ar', '44100', '-f', 'f32le', '-'], capture_output=True).stdout, np.float32)
T = np.array([x['t'] for x in tachiagari(y, 44100, band=(30, 150))]); av = []
# 🔒11/2 手本S（初見 ms 10%）：どの「絵の変わり目」で測るかを手本の種類で決める
#   本物の動画の場面がある手本（実写・3D）＝カット（hard/dissolve）で測る。板の切り替え（ban）には字の出入り・ハエ・題の動きが混ざり、音の無い変わり目まで数えて 12.9ms（答え 31.0）になった。カット 12 本なら 36.2ms
#   止め絵だけの手本（MG・手本R）＝板の切り替えで測る（MG は板の動き1つ1つに音が付く。板 83 で 22.5＝答え 22.9）
CUTS = [c['f0'] for c in Z.get('cuts', []) if c.get('kirikae', {}).get('kind') not in (None, '頭')]
honmono = sum(1 for c in Z.get('cuts', []) if c.get('seishi', {}).get('kind') == '本物の動画')
#   🔒11/2（2回目）：「1つでも本物の動画」やと MG の板1枚の見間違いで切り替わる（手本R v7：11 カット中 1 が本物の動画と出て ms 22.5→34.7）→ カットの 1/4 以上が本物の動画の時だけ（手本S 10/13・mm4u 23/24・r2 125/213・手本J 27/68・51 41/134＝31%）
EV, de = (CUTS, 'カット（本物の動画の場面が 1/4 以上の手本）') if len(CUTS) >= 3 and honmono >= 0.25 * len(CUTS) else (BF, '板の切り替え（止め絵が主の手本＝MG）')
for f in EV:
    if not len(T): break
    t = f / FPS; j = np.argmin(abs(T - t)); dt = (T[j] - t) * 1000
    if abs(dt) < 120: av.append(dt)
if av: Z.setdefault('oto', {})['oto_ato_ms'] = round(float(np.median(av)), 1); Z['oto']['oto_ato'] = dict(q1=round(float(np.percentile(av, 25)), 1), q3=round(float(np.percentile(av, 75)), 1), saki=int((np.array(av) < 0).sum()), n=len(av), de=de, honmono=honmono)
# ---- 入りと終わりのフェード（画面の明るさの合計）
mean = g.reshape(len(g), -1).mean(1); fades = []; ED = [0] + BF + [len(mean)]
for a, b in zip(ED[:-1], ED[1:]):                    # 板の中だけで見る（次の板の明るさを混ぜん）
    seg = mean[a:min(b, a + 30)]
    if len(seg) < 6: continue
    plat = np.median(seg[len(seg) // 2:])
    if plat < 3 or seg[0] > 0.15 * plat: continue    # 黒に近い所から上がる物だけ＝入りのフェード
    k = next((i for i in range(len(seg)) if seg[i] >= 0.995 * plat), None)
    if k and 3 <= k <= 25 and np.all(np.diff(seg[:k + 1]) >= -0.02 * plat):
        fades.append(dict(kind='fade_in', f0=a, f1=a + k, curve={str(a + i): round(float(min(1, (seg[i] - seg[0]) / (plat - seg[0]))), 4) for i in range(k + 1)}))
med = np.median(mean); ms = np.array([np.median(mean[max(0, i - 3):i + 4]) for i in range(len(mean))])
for b in BF + [len(mean)]:                           # 切り替え（か終わり）の直前が黒＝そこへ下がる消え。板をまたいで、なだらかに下がり続ける所まで戻る
    if b < 8 or mean[b - 1] > 0.15 * med or any(f['kind'] == 'fade_out' and f['f1'] >= b - 6 for f in fades): continue
    k = b - 2; miss = 0                              # 1コマ戻るごとに明るくなる間だけ戻る（平らなコマは3つまで許す＝途中の切り替え）
    while k > 0 and miss <= 3:
        if mean[k - 1] > mean[k] * 1.003: miss = 0
        else: miss += 1
        k -= 1
    k += miss + 1
    s0 = next((i for i in range(k, b) if ms[i] < 0.99 * ms[k]), None)
    if s0 is not None and b - s0 >= 6: fades.append(dict(kind='fade_out', f0=int(s0), f1=int(b - 1), curve={str(i): round(float(mean[i] / mean[s0]), 4) for i in range(s0, b)}))
Z['fade'] = fades
for c in Z.get('cuts', []):
    for fd in fades:
        if fd['kind'] == 'fade_in' and abs(c['f0'] - fd['f0']) <= 1: c['kirikae']['curve'] = fd['curve']; c['kirikae']['kind'] = 'fade_in'
Z['owari'] = next(({'kind': 'fade_out', 'f0': fd['f0'], 'f1': fd['f1']} for fd in fades if fd['kind'] == 'fade_out'), {'kind': 'なし'})
# ---- 字体：一番長い板3枚の真ん中のコマで字の行を読み、大・中・小の行を棚の字体と重ねる
TANA = sorted(glob.glob(os.path.join(D, '..', '..', 'assets', 'fonts_tana', '*.[ot]tf')))
OCR = f'{W_}/zukan/ocr_en'
if TANA and not os.path.exists(OCR): subprocess.run(['swiftc', '-O', '-o', OCR, os.path.join(D, '..', 'ban', 'ocr_en.swift')], check=True)
if TANA:
    from PIL import Image, ImageFont, ImageDraw
    from ban_lib import Ban
    edges = [0] + BF + [len(g)]; segl = [s for s in zip(edges[:-1], edges[1:]) if s[1] - s[0] >= 5]
    segs = [segl[int(i * (len(segl) - 1) / 7)] for i in range(8)] if len(segl) >= 8 else segl   # 板を8枚、頭から終わりまで散らして読む（長い板は題だけの事が多い）
    lines = []
    for a, b in segs:
        fr = (a + b) // 2; pth = f'{W_}/zukan/jitai_{fr}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', REF, '-vf', f"select='eq(n\\,{fr})'", '-vsync', '0', '-frames:v', '1', pth], check=True)
        gi = np.asarray(Image.open(pth).convert('L'), np.float32)
        for l in subprocess.run([OCR, pth], capture_output=True, text=True).stdout.splitlines():
            _, t, bx = l.split('\t'); box = list(map(int, bx.split(',')))
            if re.fullmatch(r"[A-Za-z0-9 /&\-.,:%()']{4,}", t) and re.search(r'[A-Za-z]{3,}', t):
                ib, _ = Ban.ink_box(gi, box); lines.append((ib[3] - ib[1], t, ib, gi))
    def iou(t, ib, gi, fp):
        X0, Y0, X1, Y1 = ib; c = gi[Y0:Y1, X0:X1]
        if c.size == 0 or Y1 - Y0 < 4: return 0
        mk = c > c.max() * 0.5; ft = ImageFont.truetype(fp, 120); l, tp, r, bt = ft.getbbox(t, anchor='ls')
        if r - l < 2 or bt - tp < 2: return 0
        im = Image.new('L', (r - l + 10, bt - tp + 10), 0); ImageDraw.Draw(im).text((5 - l, 5 - tp), t, font=ft, fill=255, anchor='ls')
        ww_ = max(1, int(round((r - l) * (Y1 - Y0) / (bt - tp))))
        aa = np.asarray(Image.fromarray(np.asarray(im)[5:5 + bt - tp, 5:5 + r - l]).resize((ww_, Y1 - Y0), Image.LANCZOS)) > 127
        Wd = max(ww_, X1 - X0); A = np.zeros((Y1 - Y0, Wd), bool); M_ = np.zeros((Y1 - Y0, Wd), bool); A[:, :ww_] = aa; M_[:, :X1 - X0] = mk
        return (A & M_).sum() / max(1, (A | M_).sum())
    # 字の行1本ずつ、棚の字体で一番重なる物（高さだけ合わせる＝幅で等幅かどうかも分かる）→ 字体ごとの本数
    per = []
    for h, t, ib, gi in lines:
        if h < 9: continue
        sc = sorted(((iou(t, ib, gi, fp), os.path.basename(fp)) for fp in TANA), reverse=True)
        per.append(dict(t=t, h=int(h), font=sc[0][1], iou=round(float(sc[0][0]), 3), ni=sc[1][1]))
    from collections import Counter
    cnt = Counter(x['font'] for x in per)
    Z['jitai'] = dict(gyou=per, kazoe=dict(cnt.most_common()), dai=max(per, key=lambda x: x['h'])['font'] if per else None,
                      rule='字の行1本ずつ棚（assets/fonts_tana）の字体と墨を重ねた一番。手本の字体が棚に無い時は一番近い代わり（Bahnschrift→D-DIN・Segoe UI→Selawik）')
# ---- 変わる字：見つけた切り替えで板に分けて、板の字の箱を1コマずつ見る（ban_states → ban_kawaru）
BD = f'{W_}/zukan/ban'; os.makedirs(BD, exist_ok=True)
json.dump(dict(name='miru', ref=REF, events=BF, W=VW, H=VH, fps=FPS, fonts={}, plain='text'), open(f'{BD}/cfg.json', 'w'))
for x in ('ban_states', 'ban_kawaru'):
    subprocess.run([sys.executable, os.path.join(D, '..', 'ban', x + '.py'), BD], capture_output=True)
if os.path.exists(f'{BD}/kawaru.json'):
    kw = json.load(open(f'{BD}/kawaru.json'))
    Z['kawaru'] = [dict(key=k, kugiri=[[e0, e1, r] for e0, e1, r in v]) for k, v in kw.items()]
if os.path.exists(f'{BD}/gray_full.raw'): os.remove(f'{BD}/gray_full.raw')   # 全コマの明るさ（手本1本で数GB）は使い終わったら消す
json.dump(Z, open(ZP, 'w'), ensure_ascii=False)
print(f"板の切り替え {len(BF)}・図が動くコマ {len(Z['ugoku_koma'])}・音は絵の {Z.get('oto', {}).get('oto_ato_ms')}ms 後・フェード {[(x['kind'], x['f0']) for x in fades]}・字体 {Z.get('jitai', {}).get('kazoe')}・変わる字 {len(Z.get('kawaru', []))}")
