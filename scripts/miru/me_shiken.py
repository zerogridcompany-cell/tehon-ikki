# 目の試験：1回目に見た物（zukan.json）を、何周も詰めて分かった答え（seikai.json）と照らして「最初に見えた割合」を出す
# 使い方：python3 me_shiken.py <zukan.json> <seikai.json> [結果.json]
#   答えの作り方＝写しを詰め切った作業から（例＝作業フォルダの me_shiken/seikai.json）。道具を直すたびに測り直して点を上げる
import json, re, sys
import numpy as np
Z = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2])); rows = []
def add(name, score, mita, kotae): rows.append(dict(k=name, score=round(float(score), 3), mita=mita, kotae=kotae))
cuts = Z.get('cuts', []); f0s = [b['f'] for b in Z['ban']] if Z.get('ban') else [c['f0'] for c in cuts[1:]]
NASHI = dict(S.get('nashi', {}))
if not isinstance(S.get('kirikae'), list):   # 🆕10/31 型を問わん答え（51・mm4u・r2）＝me_shiken_ippan.py で採点
    sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
    import me_shiken_ippan; me_shiken_ippan.saiten(Z, S, add, NASHI); rows_done = True
else: rows_done = False
KW = set()
if not rows_done:
  for sp in S['kawaru'].values():
    for e0, e1, r in sp[1:]: KW |= {e0 - 1, e0, e0 + 1}
def ban_shiken():
    global hit, tot, hit9
    # 1 板の切り替え（±1コマ）
    ev = S['kirikae']; hit = sum(any(abs(e - f) <= 1 for f in f0s) for e in ev); extra = sum(not any(abs(e - f) <= 1 for e in ev) and f not in KW for f in f0s); naka = sum(not any(abs(e - f) <= 1 for e in ev) and f in KW for f in f0s)
    add('板の切り替え', hit / len(ev) * (1 - extra / max(1, len(f0s))) if f0s else 0, f'{len(f0s)}回（当たり {hit}・板の中の段 {naka}・余計 {extra}）', f'{len(ev)}回')
    # 2 図が動くコマ：止め絵・動き0 と書いた区間に入る動くコマは見落とし
    mv = S['ugoku_koma']; seen = 0; UK = set(Z.get('ugoku_koma', []))
    for f in mv:
        if UK:
            seen += any(f + j in UK for j in (-1, 0, 1)); continue
        c = next((c for c in cuts if c['f0'] <= f < c['f1']), None)
        if c and not (c.get('seishi', {}).get('kind') == '止め絵' and max(c.get('ugoki', {}).get(k, 0) for k in 'GLD') < 0.1): seen += 1
    add('図が動くコマ', seen / len(mv), f'動くと見た {seen}', f'{len(mv)}コマ（線が伸びる・点が動く・面が回る）')
    # 3 音は絵の何ms後
    v = Z.get('oto', {}).get('oto_ato_ms') or Z.get('meta', {}).get('oto_ato_ms')
    add('音は絵の何ms後', 0 if v is None else max(0, 1 - abs(v - S['oto_ato_ms']) / 20), '測ってない' if v is None else f'{v:+.1f}ms', f"{S['oto_ato_ms']:+.1f}ms")
    # 4 曲
    ky = Z.get('oto', {}).get('kyoku', []); names = [k.get('name', '') for k in ky]
    ok = any(S['kyoku'].lower() in n.lower() for n in names); one = (len(ky) == 1) == (not S['kyoku_kirekoto'])
    add('曲の名前と切れ目', (ok + one) / 2, ' / '.join(names) or 'なし', f"{S['kyoku']}・{'切れ目あり' if S['kyoku_kirekoto'] else '1本・切れ目なし'}")
    # 5 語りの有無
    ks = Z.get('oto', {}).get('koe_shurui', {}).get('v'); katari = ks in ('語り', 'ナレーション')
    add('語り（ナレ）の有無', 1 if katari == S['katari'] else 0, str(ks), '語りあり' if S['katari'] else '語りなし（歌の声だけ）')
    # 6 入りのフェード
    fi = {int(k): v for k, v in S['fade_in'].items()}; f0 = min(fi)
    c = next((c for c in cuts if abs(c['f0'] - f0) <= 1), None); kind = (c or {}).get('kirikae', {}).get('kind')
    crv = (c or {}).get('kirikae', {}).get('curve')
    if crv: sc = max(0, 1 - np.mean([abs(crv.get(str(f), 1.0) - v) for f, v in fi.items()]) / 0.1)
    else: sc = 0.3 if kind and 'fade' in str(kind) else 0
    add('入りのフェード（1コマずつの曲がり）', sc, f'{kind}' + ('・曲がりあり' if crv else '・曲がりなし'), f'{len(fi)}コマ 0→0.27→0.49→…→1')
    # 7 終わりの消え
    lastk = [c.get('kirikae', {}).get('kind') for c in cuts if c['f0'] <= S['fade_out_f0'] < c['f1']] + [Z.get('owari', {}).get('kind')]
    fo = [f for f in Z.get('fade', []) if f['kind'] == 'fade_out']
    add('終わりの消え', (1 if abs(fo[0]['f0'] - S['fade_out_f0']) <= 3 else 0.5) if fo else (1 if any(k and 'fade' in str(k) for k in lastk) else 0), str([k for k in lastk if k]) or '見てない', f"{S['fade_out_f0']}〜{S['fade_out_f1']}コマで 1→0")
    # 8 字体
    words = Z.get('moji', {}).get('words', []); fg = set(Z['jitai']['kazoe']) if isinstance(Z.get('jitai'), dict) and Z['jitai'].get('kazoe') else {w.get('font_guess') for w in words}
    FAM = lambda g: 'Impact' if 'Impact' in g else 'DIN' if 'DIN' in g else 'Segoe' if ('Segoe' in g or 'Selawik' in g) else 'Mono' if ('Mono' in g or '等幅' in g) else None
    named0 = [g for g in fg if g and any(k in str(g) for k in ('Impact', 'DIN', 'Segoe', 'Selawik', 'Bahnschrift', '等幅', 'mono', 'Mono'))]
    named = {FAM(str(g)) for g in named0} - {None}
    dai = 'Impact' in str(Z['jitai'].get('dai')) if isinstance(Z.get('jitai'), dict) and Z['jitai'].get('dai') else any('Impact' in str(g) for g in fg)
    add('字体（題・札・説明・等幅）', (0.5 * dai + 0.5 * min(1, len(named) / 4)), ' / '.join(sorted(str(g) for g in fg))[:60], f"題 {S['jitai_dai']}・{S['jitai']}")
    # 9 変わる字（時計・札・ページ番号）：区切りの字が、その時刻の読みにあるか
    tot = hit9 = 0
    for key, sp in S['kawaru'].items():
        for e0, e1, r in sp:
            r = r.strip()
            if not r: continue
            tok = re.findall(r'[A-Za-z0-9.]{2,}', r)
            if not tok: continue
            tot += 1
            near = {w['w'] for w in words if w['f0'] <= e1 and w['f1'] >= e0} | {x for k in Z.get('kawaru', []) for a0, a1, rr in k['kugiri'] if a0 <= e1 and a1 >= e0 for x in re.findall(r'[A-Za-z0-9.]{2,}', rr)}
            if all(t in near for t in tok): hit9 += 1
    add('変わる字（時計・札・番号）', hit9 / max(1, tot), f'読めた区切り {hit9}', f'{tot}区切り（時計は {S["tokei_koma"]}コマごとに 0.1）')
    # 10 色収差
    sh = [c['i'] for c in cuts if c.get('shuushuu', {}).get('ari')]
    add('色収差（ずらし）の板', 1 if sh and all(any(c['f0'] <= S['kirikae'][b - 1] < c['f1'] for c in cuts if c['i'] in sh) for b in S['shuushuu_ban']) and len(sh) <= 2 * len(S['shuushuu_ban']) else 0, f'カット {sh}', f"板 {S['shuushuu_ban']}")
    # 11 音量
    lu = Z.get('oto', {}).get('lufs', {}).get('I')
    add('音量（LUFS）', 1 if lu is not None and abs(lu - S['lufs']) <= 0.5 else 0, str(lu), str(S['lufs']))

if not rows_done: ban_shiken()
tot_sc = np.mean([r['score'] for r in rows])
print(f'目の試験：最初に見えた割合 {tot_sc * 100:.0f}%（{len(rows)}項目）')
for k, v in NASHI.items(): print(f'  ー {k}：答えなし（{v}）')
for r in rows: print(f"  {'✅' if r['score'] >= 0.9 else ('🟡' if r['score'] >= 0.4 else '🔴')} {r['k']}：{r['score'] * 100:.0f}%  見た＝{r['mita']}／答え＝{r['kotae']}")
if len(sys.argv) > 3: json.dump(dict(score=tot_sc, rows=rows, nashi=NASHI), open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
