# 段0 見るの足し（10/31 目の問題集）：曲の名前を「当たった作者の他の曲も全部比べて」決め直す＋声が曲の声か語りかを曲と比べて分ける
#  🔴 Shazam は同じ作者の同じ太鼓・同じ速さの別の曲を返す（手本R・r2 とも TREAT ME TEKK＝本当は SCREAMTEKK）
#  ① 区間ごとに Shazam の作者の曲を YouTube から 20本ほど落とす（cand/・使い回す）→ 自前の指紋（bgm_fp の hashes）で区間の音楽の層と照らす
#     一番当たった曲が Shazam の曲の 2倍以上・当たり 60 以上なら名前を替える（根拠 fp_hits を残す）
#  ② 声の層（demucs vocals）を、当たった曲の同じ位置と 300〜3400Hz のメルの形で比べる＝似とる（相関 0.35 以上）の声が 6割超なら「歌・声ネタ（語りなし）」
# 使い方：python3 kyoku_plus.py <作業>（<作業>/zukan/zukan.json の oto.kyoku・koe_shurui を書き換える）
import json, os, sys, subprocess, glob, re
import numpy as np, librosa
from collections import Counter, defaultdict
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(D, '..', 'kouzou'))
from bgm_fp import hashes, SR, HOP
W_ = sys.argv[1]; ZP = f'{W_}/zukan/zukan.json'; Z = json.load(open(ZP)); O = f'{W_}/zukan/oto'; CA = f'{O}/cand'; os.makedirs(CA, exist_ok=True)
secs = Z.get('oto', {}).get('kyoku', [])
log = []
def yt_list(q, n):
    r = subprocess.run(['yt-dlp', f'ytsearch{n}:{q}', '--flat-playlist', '-J', '--no-warnings'], capture_output=True, text=True, timeout=120)
    try: return [(e['id'], e.get('title', ''), e.get('duration') or 0, e.get('channel') or e.get('uploader') or '') for e in json.loads(r.stdout).get('entries', []) if e.get('id')]
    except Exception: return []
def get(vid):
    have = glob.glob(f'{CA}/{vid}.*')
    if have: return have[0]
    subprocess.run(['yt-dlp', '-f', 'bestaudio[ext=m4a]/bestaudio', '-o', f'{CA}/%(id)s.%(ext)s', '--no-warnings', '-q', '--', vid], capture_output=True, timeout=180)
    have = glob.glob(f'{CA}/{vid}.*'); return have[0] if have else None
# ⓪ Shazam が黙った区間（8秒以上）は、窓の位相を 2秒ずらしてもう一度聞く（Shazam は回すたびに当たる窓が変わる＝r2 の 2回目は TEKK の区間が全部黙った）
import soundfile as sf
SHZ = os.path.join(D, '..', 'kouzou', 'shazam_undo.py')
for s in secs:
    if s.get('name') not in (None, '不明') or s['b'] - s['a'] < 8: continue
    js = f"{O}/shazam_re_{s['a']:.2f}.json"
    if not os.path.exists(js):
        y, sr_ = librosa.load(f'{O}/music.wav', sr=44100, offset=s['a'] + 2, duration=s['b'] - s['a'] - 2); tmp = f"{O}/_re_{s['a']:.2f}.wav"; sf.write(tmp, y, sr_)
        subprocess.run([sys.executable, SHZ, tmp, js, '1.0'], capture_output=True, text=True, timeout=600); os.remove(tmp)
        if not os.path.exists(js): json.dump([], open(js, 'w'))
    hits = json.load(open(js))
    if hits:
        nmc = Counter(f"{h['artist']} - {h['title']}" for h in hits).most_common(1)[0][0]; hh = [h for h in hits if f"{h['artist']} - {h['title']}" == nmc]
        s['name'] = nmc; s.pop('fumei', None); s['skew'] = float(np.median([h['skew'] for h in hh if h.get('skew') is not None] or [0]))
        s.setdefault('konkyo', {})['shazam_re'] = len(hh); log.append(f"{s['a']}-{s['b']}秒：Shazam 聞き直し → {nmc}（{len(hh)}窓）")
    else: log.append(f"{s['a']}-{s['b']}秒：Shazam 聞き直しても黙った")
meta = json.load(open(f'{CA}/meta.json')) if os.path.exists(f'{CA}/meta.json') else {}
artists = sorted({s['name'].split(' - ')[0].strip() for s in secs if s.get('name') and s['name'] != '不明' and ' - ' in s['name']})
for ar in artists:
    if ar in meta.get('_done', []): continue
    titles = {s['name'].split(' - ', 1)[1] for s in secs if s.get('name', '').startswith(ar + ' - ')}
    L = yt_list(ar, 20) + sum((yt_list(f'{ar} {t}', 4) for t in titles), [])
    for vid, ti, du, ch in L:
        if not du or du > 600 or vid in meta: continue
        p = get(vid)
        if p: meta[vid] = dict(title=ti, artist=ar, channel=ch, path=os.path.basename(p))
    meta.setdefault('_done', []).append(ar)
json.dump(meta, open(f'{CA}/meta.json', 'w'), ensure_ascii=False)
# 指紋の倉（曲ごと）
cache = {}
def song_hashes(vid):
    if vid not in cache:
        y, _ = librosa.load(f"{CA}/{meta[vid]['path']}", sr=SR); db = defaultdict(list)
        for h, t in hashes(y): db[h].append(t)
        cache[vid] = db
    return cache[vid]
mus = f'{O}/music.wav'
def match(y, r, db):
    """手本の区間 y を r 倍で戻して、6秒の窓ごとに一番そろった（ずれ）の数を足す。戻り＝(当たりの合計, 一番の曲の秒)"""
    yr = librosa.resample(y, orig_sr=SR, target_sr=int(round(SR * r))) if abs(r - 1) > 1e-4 else y
    hs = hashes(yr); fr = SR / HOP; dur = len(y) / SR; tot = 0; offs = []
    for w0 in np.arange(0, max(0.1, dur - 3), 2.0):
        a, b = w0 * r * fr, (w0 + 6) * r * fr; cnt = Counter()
        for h, t in hs:
            if a <= t < b:
                for tt in db.get(h, ()): cnt[tt - t] += 1
        if cnt:
            off, n = cnt.most_common(1)[0]; tot += n; offs.append((n, off / fr))
    best_off = max(offs)[1] if offs else None
    return tot, best_off
for s in secs:
    if not s.get('name') or s['name'] == '不明' or ' - ' not in s['name']: continue
    ar = s['name'].split(' - ')[0].strip(); cands = [v for v, m in meta.items() if v != '_done' and m['artist'] == ar]
    if not cands: continue
    y, _ = librosa.load(mus, sr=SR, offset=s['a'], duration=s['b'] - s['a'])
    rs = sorted({1.0, round(1 / (1 + (s.get('skew') or 0)), 4), round(1 + (s.get('skew') or 0), 4)})
    sc = []
    for v in cands:
        best = max((match(y, r, song_hashes(v)) + (r,) for r in rs), key=lambda x: x[0]); sc.append((best[0], v, best[1], best[2]))
    sc.sort(reverse=True); top = sc[0]
    shz_t = s['name'].split(' - ', 1)[1].lower()
    same = [x for x in sc if re.sub(r'[^a-z0-9]', '', shz_t)[:10] in re.sub(r'[^a-z0-9]', '', meta[x[1]]['title'].lower())]
    shz_hits = same[0][0] if same else 0
    s['fp_kouho'] = [dict(title=meta[v]['title'][:60], id=v, hits=int(h)) for h, v, _, _ in sc[:5]]
    need_ = 60 if same else 300   # Shazam の曲そのものが落とせんかった時は強い当たりだけ（51：Hallowaves が無いまま Unleashed 85 に替えかけた）
    if top[0] >= need_ and top[0] >= 2 * max(1, shz_hits) and top[1] not in [x[1] for x in same]:
        old = s['name']; ti = re.sub(r'\s*[\(\[].*?[\)\]]', '', meta[top[1]]['title']).strip()
        s['name'] = f"{ar} - {ti}"; s['shazam_name'] = old; s['cand_id'] = top[1]; s['at0_fp'] = round(float(top[2] - 0), 3) if top[2] is not None else None
        s.setdefault('konkyo', {})['fp_hits'] = int(top[0]); s['konkyo']['fp_shazam_no_kyoku'] = int(shz_hits)
        log.append(f'{s["a"]}-{s["b"]}秒：{old} → {s["name"]}（指紋 {top[0]} 対 {shz_hits}）')
    else:
        s['cand_id'] = (same[0][1] if same else top[1]) if top[0] >= 30 else None; s['at0_fp'] = (same[0][2] if same else top[2]) if s['cand_id'] else None
        log.append(f'{s["a"]}-{s["b"]}秒：{s["name"]} のまま（一番 {meta[top[1]]["title"][:30]} {top[0]}・Shazam の曲 {shz_hits}）')
# 不明の区間：隣の区間で落とした曲（全部）と照らす＝同じ曲が続いとるだけの事が多い（手本R 0〜3秒＝SCREAMTEKK の頭）
allc = [v for v in meta if v != '_done']
for s in secs:
    if s.get('name') not in (None, '不明') or not allc: continue
    y, _ = librosa.load(mus, sr=SR, offset=s['a'], duration=s['b'] - s['a']); du = s['b'] - s['a']
    sc = sorted(((match(y, 1.0, song_hashes(v)) + (v,)) for v in allc), key=lambda x: x[0], reverse=True)
    top = sc[0]; sec2 = sc[1][0] if len(sc) > 1 else 0; need = max(40, 12 * du)
    s['fp_kouho'] = [dict(title=meta[v]['title'][:60], id=v, hits=int(h)) for h, _, v in sc[:3]]
    if top[0] >= need and top[0] >= 2 * max(1, sec2):
        ar = meta[top[2]]['artist']; ti = re.sub(r'\s*[\(\[].*?[\)\]]', '', meta[top[2]]['title']).strip()
        nm2 = next((x['name'] for x in secs if x.get('cand_id') == top[2]), f'{ar} - {ti}')
        s['name'] = nm2; s.pop('fumei', None); s['cand_id'] = top[2]; s['at0_fp'] = top[1]; s.setdefault('konkyo', {})['fp_hits'] = int(top[0])
        log.append(f'{s["a"]}-{s["b"]}秒：不明 → {nm2}（指紋 {top[0]}・次 {sec2}）')
    else:
        # 指紋が足りん（短い・静か）＝隣の曲がそのまま続いとるかを、隣から読んだ曲の位置のメルの形（0.5秒ごとの相関）で見る
        def melc(a_ref, dur_, v, st):
            SRm = 22050; yr_, _ = librosa.load(mus, sr=SRm, offset=a_ref, duration=dur_); ys_, _ = librosa.load(f"{CA}/{meta[v]['path']}", sr=SRm, offset=max(0, st), duration=dur_)
            if len(ys_) < len(yr_) * 0.9 or st < 0: return -1
            f = lambda y: librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=SRm, n_mels=64, hop_length=256, fmin=40, fmax=10000) + 1e-10)
            A, B = f(yr_), f(ys_); n = min(A.shape[1], B.shape[1]); Wn = int(0.5 * SRm / 256)
            cs = [np.corrcoef(A[:, j:j + Wn].ravel(), B[:, j:j + Wn].ravel())[0, 1] for j in range(0, n - Wn + 1, Wn)]
            return float(np.mean(cs)) if cs else -1
        i = secs.index(s); best = (-1, None)
        for nb in (i - 1, i + 1):
            if 0 <= nb < len(secs) and secs[nb].get('cand_id') and secs[nb].get('at0_fp') is not None:
                q = secs[nb]; st = q['at0_fp'] + (s['a'] - q['a'])   # 隣の頭の曲の秒から、この区間の頭の曲の秒
                c = max((melc(s['a'], du, q['cand_id'], st + dt), dt) for dt in np.arange(-0.1, 0.101, 0.02))
                if c[0] > best[0]: best = (c[0], q, st + c[1])
        if best[1] is not None and best[0] >= 0.5:
            q = best[1]; s['name'] = q['name']; s.pop('fumei', None); s['cand_id'] = q['cand_id']; s['at0_fp'] = round(float(best[2]), 3); s.setdefault('konkyo', {})['mel_tsuzuki'] = round(best[0], 3)
            log.append(f'{s["a"]}-{s["b"]}秒：不明 → {q["name"]}（隣の曲の続き・メルの相関 {best[0]:.2f}）')
        else: log.append(f'{s["a"]}-{s["b"]}秒：不明のまま（指紋 一番 {meta[top[2]]["title"][:30]} {top[0]}・要る {need:.0f}・隣の続きの相関 {best[0]:.2f}）')
# 🔒11/2 手本S（初見 曲 0%）：名前の無い隣どうし（Shazam が全部黙った・作者の候補も無い）は「別の曲という証拠」が無い限り1本
#   手本S＝オリジナル曲1本を、拍の速さの揺れで 7つの「不明」に割っとった（速さの揺れは曲の中の揺れ＝10/30 mm4u と同じ）
#   証拠＝①境目に無音の切れ目（音楽の層が境目 ±0.5秒で、まわり ±8秒の中央値より 30dB 以上落ちる）②音の高さの並び（chroma の相関 0.85 未満）
#   🟡 弱み：同じ系統の別の曲が切れ目なしに重なって替わる物（r2 の phonk どうし＝chroma 0.98・音色 0.98）は耳では分けられん＝名前が要る（Shazam の聞き直し・音源の名前）
if os.path.exists(mus) and sum(1 for s in secs if s.get('name') in (None, '不明')) >= 2:
    srm = 22050; ym_, _ = librosa.load(mus, sr=srm)
    rms_ = librosa.feature.rms(y=ym_, hop_length=512)[0]; tr_ = librosa.times_like(rms_, sr=srm, hop_length=512)
    def chroma_(a, b):
        seg = ym_[int(a * srm):int(b * srm)]
        if len(seg) < srm: return None
        c = librosa.feature.chroma_cqt(y=seg, sr=srm).mean(1); return c / (np.linalg.norm(c) + 1e-9)
    mg0 = []
    for s in secs:
        p_ = mg0[-1] if mg0 else None
        if p_ and p_.get('name') in (None, '不明') and s.get('name') in (None, '不明'):
            t = s['a']; side = float(np.median(rms_[(tr_ > t - 8) & (tr_ < t + 8)])) + 1e-9; tani = float(rms_[(tr_ > t - 0.5) & (tr_ < t + 0.5)].min())
            tani_db = 20 * np.log10(tani / side + 1e-9)
            cL, cR = chroma_(max(0, t - 8), t - 0.3), chroma_(t + 0.3, t + 8); ch = float(cL @ cR) if cL is not None and cR is not None else 1.0
            if tani_db > -30 and ch >= 0.85:
                p_['b'] = s['b']; p_.setdefault('matome', []).append(dict(a=s['a'], bpm=s.get('bpm'), riyuu=f'不明どうし・切れ目なし（谷 {tani_db:.1f}dB・chroma {ch:.2f}）'))
                p_['beats'] = p_.get('beats', []) + s.get('beats', []); p_['bars'] = p_.get('bars', []) + s.get('bars', [])
                p_.setdefault('konkyo', {})['madoi'] = p_.get('konkyo', {}).get('madoi', 0) + s.get('konkyo', {}).get('madoi', 0)
                log.append(f'{s["a"]}-{s["b"]}秒：不明どうし → 前に続ける（谷 {tani_db:.1f}dB・chroma {ch:.2f}）'); continue
            log.append(f'{s["a"]}-{s["b"]}秒：不明どうしやが切れ目あり（谷 {tani_db:.1f}dB・chroma {ch:.2f}）＝分けたまま')
        mg0.append(s)
    secs = mg0
# 隣の同じ名前はまとめる
mg = []
for s in secs:
    if mg and s.get('name') == mg[-1].get('name') and s.get('name') != '不明':
        mg[-1]['b'] = s['b']; mg[-1].setdefault('matome', []).append(dict(a=s['a'], bpm=s.get('bpm')))
        mg[-1]['beats'] = mg[-1].get('beats', []) + s.get('beats', []); mg[-1]['bars'] = mg[-1].get('bars', []) + s.get('bars', [])
    else: mg.append(s)
Z['oto']['kyoku'] = mg
# ② 声は曲の声か
sep = f'{O}/sep/htdemucs/src/vocals.wav'
if os.path.exists(sep) and Z['oto'].get('koe_shurui', {}).get('v') == '語り':
    SR2 = 22050; yv, _ = librosa.load(sep, sr=SR2); dur = len(yv) / SR2
    def mel(y): return librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=SR2, n_mels=48, hop_length=512, fmin=300, fmax=3400) + 1e-10)
    tot = song = 0.0; rows = []
    for s in mg:
        v = s.get('cand_id'); off = s.get('at0_fp')
        if not v or off is None: continue
        ys, _ = librosa.load(f"{CA}/{meta[v]['path']}", sr=SR2)
        for t in np.arange(s['a'], s['b'] - 1, 1.0):
            seg = yv[int(t * SR2):int((t + 1) * SR2)]
            if len(seg) < SR2 // 2 or np.sqrt(np.mean(seg ** 2)) < 0.01: continue
            st = off + (t - s['a'])   # at0_fp＝区間の頭の時の曲の秒
            best = -1
            for dt in np.arange(-0.15, 0.151, 0.05):
                a0 = int((st + dt) * SR2)
                if a0 < 0 or a0 + SR2 > len(ys): continue
                A = mel(seg); B = mel(ys[a0:a0 + len(seg)])
                best = max(best, float(np.corrcoef(A.ravel(), B.ravel())[0, 1]))
            tot += 1; song += best >= 0.35; rows.append(round(best, 2))
    ks = Z['oto']['koe_shurui']; ks['uta_hikaku'] = dict(byou=int(tot), uta_no_koe=int(song), corr=rows[:40], rule='声の層と当たった曲の同じ位置を 300〜3400Hz のメルで比べ・相関 0.35 以上＝曲の声')
    if tot >= 3 and song / tot > 0.6:
        ks['v_mae'] = ks['v']; ks['v'] = '歌・声ネタ（語りなし）'; log.append(f'声：曲の声と同じ {int(song)}/{int(tot)}秒 → 語りなし')
    else: log.append(f'声：曲の声と同じ {int(song)}/{int(tot)}秒 → 語りのまま')
json.dump(Z, open(ZP, 'w'), ensure_ascii=False)
print('曲の決め直し：' + ' ／ '.join(log))
