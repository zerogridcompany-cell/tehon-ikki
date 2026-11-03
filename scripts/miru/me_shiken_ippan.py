# 目の試験の型を問わん項目（10/31 目の問題集）：seikai.json に答えがある項目だけ採点。無い項目は nashi（答えなし）＝点に入れん
# 答えの形（全部どれでも無くてええ）：
#   cuts[コマ]・cuts_ok_extra[余計に数えんコマ]・kirikae{コマ:hard|dissolve|whip|flash|zoom|glitch}・hikari[コマ]
#   douga{頭のコマ:本物の動画か}・camera{kind:G,v{頭:{G,n}}}|{kind:cam,v{頭:{zoom_pct_s,pan_px_s,n}}}・naka{頭:L}
#   kyoku[{a,b,name}]・katari(bool)・sfx[秒]・lufs・oto_ato_ms
#   moji[{w,f0,f1,box?,kei?}]＋moji_unit(word|phrase|shot_words)・jitai_kei(serif|sans)・amiten[頭のコマ]・boke{頭:σ}
import difflib
import numpy as np

nm = lambda w: ''.join(ch for ch in str(w).lower() if ch.isalnum())
def fam(g):
    g = str(g or '')
    if any(k in g for k in ('セリフ', 'serif', 'Serif', '明朝', 'Times', 'Didot', 'Bodoni', 'Playfair', 'Georgia', 'Garamond')) and 'sans' not in g.lower(): return 'serif'
    if any(k in g for k in ('ゴシック', 'sans', 'Sans', 'Impact', 'DIN', 'Segoe', 'Selawik', 'Helvetica', 'Arial', 'Montserrat', 'Bahnschrift', 'Inter')): return 'sans'
    if any(k in g for k in ('筆記', 'script', 'Script', 'cursive')): return 'script'
    return None
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); I = ix * iy
    return I / max(1e-6, (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - I)
def num(x):
    if isinstance(x, (int, float)): return float(x)
    return None

def saiten(Z, S, add, NASHI):
    C = Z.get('cuts', []); f0s = [c['f0'] for c in C[1:]]
    def cut_at(f):
        return next((c for c in C if c['f0'] <= f < c['f1']), None)
    def segs(d):   # {頭: v} → [(頭, 終わり, v)]
        ks = sorted(int(k) for k in d); ends = ks[1:] + [Z['meta'].get('n_frames') or (C[-1]['f1'] if C else ks[-1] + 30)]
        return [(a, b, d[str(a)]) for a, b in zip(ks, ends)]
    # 1 カットの位置（±1コマ）
    if 'cuts' in S:
        ev = S['cuts']; ok = set(S.get('cuts_ok_extra', []))
        lo = lambda e: e[0] if isinstance(e, list) else e; hi_ = lambda e: e[1] if isinstance(e, list) else e   # 答えは1コマか [頭, 終わり]（ホイップの間のどこか・11/2）
        on = lambda e, f: lo(e) - 1 <= f <= hi_(e) + 1
        hit = sum(any(on(e, f) for f in f0s) for e in ev)
        extra = [f for f in f0s if not any(on(e, f) for e in ev) and not any(abs(e - f) <= 1 for e in ok)]
        miss = [e for e in ev if not any(on(e, f) for f in f0s)]
        add('カットの位置（±1コマ）', hit / len(ev) * (1 - len(extra) / max(1, len(f0s))) if f0s else 0,
            f'{len(f0s)}回（当たり {hit}・余計 {len(extra)}{(" " + str(extra[:8])) if extra else ""}・見落とし {miss[:8]}）', f'{len(ev)}回')
    else: NASHI.setdefault('cuts', '答えなし')
    # 2 切り替えの種類
    if S.get('kirikae'):
        NORM = {'fade_in': 'dissolve', 'zoom-through': 'zoom'}; m = 0; seen = {}
        for f, k in S['kirikae'].items():
            c = next((c for c in C[1:] if abs(c['f0'] - int(f)) <= 1), None)
            zk = NORM.get((c or {}).get('kirikae', {}).get('kind'), (c or {}).get('kirikae', {}).get('kind'))
            seen[zk] = seen.get(zk, 0) + 1; m += (zk == k)
        add('切り替えの種類', m / len(S['kirikae']), str(seen), f"{dict(__import__('collections').Counter(S['kirikae'].values()))}")
    # 3 光るコマ（取りこぼしだけ）
    if S.get('hikari'):
        det = {x['f'] for x in Z.get('flash_frames', [])} | {c['kirikae'].get('frame') for c in C if c.get('kirikae', {}).get('kind') == 'flash'}
        h = [f for f in S['hikari'] if any(d is not None and abs(f - d) <= 1 for d in det)]
        add('光るコマ（±1）', len(h) / len(S['hikari']), f'当たり {len(h)}・取れん {sorted(set(S["hikari"]) - set(h))}', f'{len(S["hikari"])}コマ')
    # 4 止め絵か動画か
    if S.get('douga'):
        ok = n = 0
        for a, b, v in segs(S['douga']):
            n += 1; c = cut_at((a + b) // 2); sd = (c or {}).get('seishi', {}); N = num(sd.get('N')) if isinstance(sd, dict) else None
            if N is not None: ok += ((N >= 2) == v)
        add('止め絵か動画か', ok / max(1, n), f'一致 {ok}', f'{n}場面')
    # 5 カメラ
    cam = S.get('camera')
    if cam and cam['kind'] == 'G':
        ok = n = 0
        for a, b, v in segs(cam['v']):
            if v['n'] < 5: continue
            n += 1; c = cut_at((a + b) // 2); G = num((c or {}).get('ugoki', {}).get('G'))
            if G is not None: ok += ((G < 0.5) == (v['G'] < 0.5))
        add('カメラ（止まり／動く）', ok / max(1, n), f'一致 {ok}', f'{n}場面（G 0.5px/コマ 未満＝止まり）')
    elif cam and cam['kind'] == 'cam':
        dz = []; dp = []
        for k, v in cam['v'].items():
            f0 = int(k); n = v['n']; cs = [c for c in C if c['f0'] <= f0 + n // 2 < c['f1']]
            c = cs[0] if cs else None; km = (c or {}).get('kamera', {})
            zp = num(km.get('zoom_pct_s')); pp = km.get('pan_px_s'); pp = num(pp[0]) if isinstance(pp, list) else None
            if abs(v['zoom_pct_s']) >= 2: dz.append(zp is not None and np.sign(zp) == np.sign(v['zoom_pct_s']))
            dp.append(pp is not None and abs(pp - v['pan_px_s']) <= max(30, 0.2 * abs(v['pan_px_s'])))
        add('カメラ（寄り引きの向き・横の振り）', 0.5 * np.mean(dz) + 0.5 * np.mean(dp), f'向き {np.mean(dz):.0%}・振り {np.mean(dp):.0%}', f'{len(cam["v"])}場面')
    # 6 中の動き
    if S.get('naka'):
        ok = n = 0
        for a, b, v in segs(S['naka']):
            if b - a < 5: continue
            n += 1; c = cut_at((a + b) // 2); L = num((c or {}).get('ugoki', {}).get('L'))
            if L is not None: ok += abs(L - v) <= max(0.5, 0.25 * v)
        add('中の動き（人・物）', ok / max(1, n), f'差が小さい {ok}', f'{n}場面（差 0.5px か 25% 以内）')
    # 7 曲
    if S.get('kyoku'):
        zk = Z.get('oto', {}).get('kyoku', []); nh = []; bh = []
        for i, s in enumerate(S['kyoku']):
            if s.get('name'):
                ov = [z for z in zk if min(z['b'], s['b']) - max(z['a'], s['a']) > 0.3 * (s['b'] - s['a'])]
                toks = [t for t in nm(s['name']).split() if t] or [nm(s['name'])]
                nh.append(any(nm(s['name']) in nm(z.get('name', '')) for z in ov))
            if i > 0: bh.append(any(abs(z['a'] - s['a']) <= 1.0 for z in zk[1:]))
        zb = [z['a'] for z in zk[1:]]; extra = [b for b in zb if not any(abs(b - s['a']) <= 1.0 for s in S['kyoku'][1:])]
        bsc = (np.mean(bh) if bh else 1.0) * (1 - len(extra) / max(1, len(zb))) if zb else (np.mean(bh) if bh else 1.0) * (0 if bh else 1)
        if not bh and not zb: bsc = 1.0
        sc = 0.5 * (np.mean(nh) if nh else bsc) + 0.5 * bsc
        add('曲（名前と区間）', sc, ' / '.join(f"{z['a']}-{z['b']} {str(z.get('name'))[:24]}" for z in zk)[:160], ' / '.join(f"{s['a']}-{s['b']} {s.get('name')}" for s in S['kyoku']))
    # 8 語り
    if 'katari' in S:
        ks = Z.get('oto', {}).get('koe_shurui', {}).get('v'); kt = ks in ('語り', 'ナレーション')
        add('語り（話す声）の有無', 1 if kt == S['katari'] else 0, str(ks), '語りあり' if S['katari'] else '語りなし')
    # 9 効果音の時刻
    if S.get('sfx'):
        zt = np.array([x['t'] for x in Z.get('oto', {}).get('sfx', [])]); a = np.array(S['sfx'])
        if len(zt):
            r = np.mean([np.min(np.abs(zt - t)) <= 0.05 for t in a]); p = np.mean([np.min(np.abs(a - t)) <= 0.05 for t in zt]); f1 = 2 * r * p / max(1e-6, r + p)
        else: r = p = f1 = 0
        add('効果音の時刻（±50ms）', f1, f'{len(zt)}個（取れた {r:.0%}・正しい {p:.0%}）', f'{len(a)}個')
    # 10 音は絵の何ms後
    if 'oto_ato_ms' in S:
        v = Z.get('oto', {}).get('oto_ato_ms')
        add('音は絵の何ms後', 0 if v is None else max(0, 1 - abs(v - S['oto_ato_ms']) / 20), str(v), str(S['oto_ato_ms']))
    # 11 音量
    if 'lufs' in S:
        lu = Z.get('oto', {}).get('lufs', {}).get('I')
        add('音量（LUFS）', 0 if lu is None else (1 if abs(lu - S['lufs']) <= 0.5 else max(0, 1 - abs(lu - S['lufs']) / 3)), str(lu), str(S['lufs']))
    # 12〜14 字
    if S.get('moji'):
        W = Z.get('moji', {}).get('words', []); HH = S.get('H') or Z['meta'].get('H'); unit = S.get('moji_unit', 'word')
        fnd = d0 = d1 = bx = hk = 0; fo = []; miss = []
        # 🔒11/2：出る・消えるの物差しは答えの作り方で2つある＝「見え始め・見え終わり」（f0/f1・r2/51/tehonJ の答え＝cap_time の相関）と「はっきり見える」（f0_koi/f1_koi・tehonS の答え＝白い画素が落ち着いた量の半分以上）。見る段は両方を出し、どちらかが ±1 なら当たり
        q0 = lambda w: min(abs(w['f0'] - m['f0']), abs(w.get('f0_koi', w['f0']) - m['f0']))
        q1 = lambda w: min(abs(w['f1'] - m['f1']), abs(w.get('f1_koi', w['f1']) - m['f1']))
        for m in S['moji']:
            if unit == 'shot_words':
                ws = [w for w in W if w['f1'] >= m['f0'] - 3 and w['f0'] <= m['f1'] + 3 and difflib.SequenceMatcher(None, nm(w['w']), nm(m['w'])).ratio() >= 0.75]
            elif unit == 'phrase':
                toks = [nm(x) for x in m['w'].split() if nm(x)]; b = m['box']
                ws = [w for w in W if w['f1'] >= m['f0'] - 3 and w['f0'] <= m['f1'] + 3 and b[0] - 30 <= (w['box_px'][0] + w['box_px'][2]) / 2 <= b[2] + 30 and b[1] - 30 <= (w['box_px'][1] + w['box_px'][3]) / 2 <= b[3] + 30
                      and any(difflib.SequenceMatcher(None, nm(w['w']), k).ratio() >= 0.6 for k in toks)]
            else:
                ws = [w for w in W if q0(w) <= 6 and difflib.SequenceMatcher(None, nm(w['w']), nm(m['w'])).ratio() >= 0.8]
                if ws: ws = [min(ws, key=q0)]
            if not ws: miss.append(m['w']); continue
            fnd += 1
            if unit != 'shot_words':
                if unit == 'phrase':   # 句は語の集まり＝前の句から残る語（to feel → to grow の to）があるので「句の頭／終わりに出る・消える語が1つでもあるか」
                    d0 += min(q0(w) for w in ws) <= 1; d1 += min(q1(w) for w in ws) <= 1
                else:
                    d0 += min(q0(w) for w in ws) <= 1; d1 += min(q1(w) for w in ws) <= 1
            if m.get('box'):
                ub = [min(w['box_px'][0] for w in ws), min(w['box_px'][1] for w in ws), max(w['box_px'][2] for w in ws), max(w['box_px'][3] for w in ws)]
                hb = m['box'][3] - m['box'][1]; bx += iou(ub, m['box']) >= 0.5; hk += abs((ub[3] - ub[1]) - hb) <= max(0.02 * HH, 0.1 * hb)   # 高さの差＝画面の 2% か字の高さの 10% の大きい方まで
            if m.get('kei'):
                big = max(ws, key=lambda w: (w['box_px'][2] - w['box_px'][0]) * (w['box_px'][3] - w['box_px'][1])); fo.append(fam(big.get('font_guess')) == m['kei'])
        N = len(S['moji'])
        if unit == 'shot_words': add('字（語が見えたか）', fnd / N, f'見えた {fnd}・取れん {miss[:6]}', f'{N}語（場面ごと）')
        else: add('字（見つかる・出る・消える ±1）', (fnd + d0 + d1) / (3 * N), f'見つかった {fnd}・出る±1 {d0}・消える±1 {d1}・取れん {miss[:5]}', f'{N}{"語" if unit == "word" else "句"}')
        if any(m.get('box') for m in S['moji']): add('字の位置と大きさ', (bx + hk) / (2 * N), f'箱 IoU≥0.5 {bx}・高さの差≤2%か1割 {hk}', f'{N}')
        if fo: add('字体の系統（セリフ／ゴシック）', sum(fo) / N, f'当たり {sum(fo)}（見つかった {len(fo)} 中）', f"{dict(__import__('collections').Counter(m['kei'] for m in S['moji'] if m.get('kei')))}")
    if S.get('jitai_kei'):
        fs = [fam(w.get('font_guess')) for w in Z.get('moji', {}).get('words', [])]
        add('字体の系統（全体）', np.mean([f == S['jitai_kei'] for f in fs]) if fs else 0, str(dict(__import__('collections').Counter(fs))), S['jitai_kei'])
    # 15 色と粒（網点・ぼけ）
    if S.get('amiten'):
        A = S['amiten']; det = [c for c in C if c.get('kumi', {}).get('ari')]
        h = sum(any(c['f0'] <= a + 1 < c['f1'] for c in det) for a in A); ex = sum(not any(c['f0'] <= a + 1 < c['f1'] for a in A) for c in det)
        add('色と粒（網点の場面）', h / len(A) * (1 - ex / max(1, len(det))), f'網点ありのカット {len(det)}（当たり {h}・余計 {ex}）', f'{len(A)}場面')
    if S.get('boke'):
        a, b = [], []
        for s0, s1, v in segs(S['boke']):
            c = cut_at((s0 + s1) // 2); sr = num((c or {}).get('surudosa'))
            if sr is not None: a.append(v); b.append(sr)
        rk = lambda v: np.argsort(np.argsort(v)); rho = np.corrcoef(rk(a), rk(b))[0, 1] if len(a) > 3 else 0
        add('色と粒（ぼけの順位）', max(0, -rho), f'鋭さとの順位相関 {rho:+.2f}', f'{len(a)}場面（ぼけ σ が大きい＝鋭さが低いはず）')
    # 16〜19 字の点滅・厚み・後ろ・反転（11/2 tehonJ＝見る段の moji_plus.py）
    if S.get('tenmetsu') or S.get('ushiro') or S.get('atsumi'):
        T = Z.get('moji_track', []); A = {m['id']: m for m in S.get('moji', []) if m.get('id')}
        def match(m):
            c = [((min(o['f1'], m['f1']) - max(o['f0'], m['f0'])) / max(1, m['f1'] - m['f0']), iou(o['box_px'], m['box']), o) for o in T]
            c = [x for x in c if x[0] > 0.3 and x[1] >= 0.3]
            return max(c, key=lambda x: x[0] * x[1])[2] if c else None
        MT = {k: match(m) for k, m in A.items()}
        if S.get('tenmetsu'):
            ans = {(k, f) for k, v in S['tenmetsu'].items() for f in v['kesu']}; det = set()
            for k, v in S['tenmetsu'].items():
                o = MT.get(k)
                if o: det |= {(k, f) for f in o['kesu'] if v['f0'] <= f <= v['f1']}
            near = lambda x, Y: any(x[0] == y[0] and abs(x[1] - y[1]) <= 1 for y in Y)
            r = np.mean([near(a, det) for a in ans]) if ans else 1; p = np.mean([near(d, ans) for d in det]) if det else (1 if not ans else 0)
            nw = sum(bool(v['kesu']) for v in S['tenmetsu'].values()); fw = sum(bool(v['kesu']) and MT.get(k) is not None for k, v in S['tenmetsu'].items())
            add('字の点滅（消えるコマ ±1）', 2 * r * p / max(1e-6, r + p), f'取れた {r:.0%}・正しい {p:.0%}・点滅する字 {nw} 中 字が見つかった {fw}', f'{len(ans)}コマ（{nw}語）')
        for key, name in (('ushiro', '字が人の後ろか'), ('atsumi', '字の厚み・影')):
            if not S.get(key): continue
            tp = tn = P = Nn = 0
            for k, v in S[key].items():
                o = MT.get(k); d = bool(o and o.get(key + '_ari'))
                if v: P += 1; tp += d
                else: Nn += 1; tn += (not d)
            sc = 0.5 * (tp / max(1, P) + tn / max(1, Nn)) if P and Nn else (tp / max(1, P) if P else tn / max(1, Nn))
            add(name, sc, f'ありを当てた {tp}/{P}・なしを当てた {tn}/{Nn}', f'あり {P}・なし {Nn}（ありとなしの当たりの平均）')
    if 'hanten' in S:
        sh = [(a, b) for a, b in S.get('hanten_shiran', [])]; cu = [c for c in S.get('cuts', []) if not isinstance(c, list)]
        dz = [h['f'] for h in Z.get('hanten', []) if not any(a <= h['f'] <= b for a, b in sh) and not any(abs(h['f'] - c) <= 1 for c in cu)]
        an = S['hanten']; r = np.mean([any(abs(a - d) <= 1 for d in dz) for a in an]) if an else 1; p = np.mean([any(abs(a - d) <= 1 for a in an) for d in dz]) if dz else (0 if an else 1)   # 反転なしの手本で何も拾わん＝満点（11/2）
        add('反転の切り替わり（±1コマ）', 2 * r * p / max(1e-6, r + p), f'{len(dz)}回（取れた {r:.0%}・正しい {p:.0%}）', f'{len(an)}回')
