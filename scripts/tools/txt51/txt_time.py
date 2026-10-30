"""txt_time.py  字の出る・消える時刻を「字の型の中だけ」で測る（51 再開4回目・後ろの白・赤を拾わん）。

何をする：毎コマ「型の中の字の色の近さ − 型のまわりの輪の近さ」を出し、出揃いを 1 にした値が 0.5 を超える最初のコマ＝出る・最後のコマ＝消える。
  左端・右端の 15% の列だけでも出るコマを出す（打ち字の速さ・向き）。
使い方：python3 txt_time.py <うちの mp4> <版名> --work <作業> [--ids a,b]
入れる物：手本・うちの mp4・字の表・字だけの層（手本に当て直し済みの場所＝txt_reg の後に書き出した物）
出す物：<out>/reg/time_<版名>.json・.md（手本｜うち｜差 コマ＝うち−手本）→ t0・t1・reveal・xout を手で直すか char_time.py へ
効いた数字（51）：打ち字 10/11 が全部の字で ±1コマ（char_time と組）
"""
import os, sys, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U

def curve(F, Min, Mbg, col):
    L = np.exp(-((F - col) ** 2).sum(3) / (2 * 45.0 ** 2))
    return L[:, Min].mean(1) - L[:, Mbg].mean(1)

def times(p, k_full, f0):
    pre = np.median(p[:4]); top = np.median(p[max(0, k_full - 2):k_full + 3]); rng = top - pre
    if abs(rng) < 0.03: return None
    q = (p - pre) / rng
    on = next((i for i in range(0, k_full + 1) if q[i] >= 0.5), None)
    off = next((i for i in range(len(q) - 1, k_full - 1, -1) if q[i] >= 0.5), None)
    return dict(on=None if on is None else f0 + on, off=None if off is None else f0 + off, rng=round(float(rng), 3))

def main():
    ap = U.base_args(__doc__); ap.add_argument('ours'); ap.add_argument('ver')
    a = U.resolve(ap.parse_args()); K, fps = a.K, a.fps
    P = int(round(24 * K)); e3 = np.ones((3, 3), np.uint8); d29 = np.ones((int(29 * K) | 1,) * 2, np.uint8); d11 = np.ones((int(11 * K) | 1,) * 2, np.uint8)
    rows = []
    for k, d in enumerate(a.T):
        if a.idset and d['id'] not in a.idset: continue
        A = U.sheet_alpha(a.sheet, k)
        if A is None: continue
        X0, Y0, X1, Y1 = U.ebox(A, P, a.W, a.H); aa = (A[Y0:Y1, X0:X1] > 0.5).astype(np.uint8)
        Min = cv2.erode(aa, e3) > 0
        Mbg = (cv2.dilate(aa, d29) > 0) & ~(cv2.dilate(aa, d11) > 0)
        cols = np.where(Min.any(0))[0]; cl, cr = cols[0], cols[-1]; wq = max(2, int((cr - cl) * 0.15))
        ML = Min.copy(); ML[:, cl + wq:] = False; MR = Min.copy(); MR[:, :cr - wq] = False
        f0 = max(0, int(round(d['t0'] * fps)) - int(round(0.4 * fps))); f1 = min(a.N - 1, int(round(d['t1'] * fps)) + int(round(0.27 * fps))); n = f1 - f0
        kf = U.frame_of(d, fps) - f0; res = {}
        for tag, src in (('ref', a.ref), ('ours', a.ours)):
            F = U.clip(src, f0, n, X0, Y0, X1 - X0, Y1 - Y0, fps)
            if len(F) == 0: res[tag] = None; continue
            kk = min(kf, len(F) - 1); col = np.median(F[kk][Min], 0)
            r = times(curve(F, Min, Mbg, col), kk, f0)
            if r:
                for nm, M in (('L', ML), ('R', MR)):
                    t = times(curve(F, M, Mbg, col), kk, f0); r[nm] = t['on'] if t else None
            res[tag] = r
        R, O = res['ref'], res['ours']
        if not R or not O: rows.append(dict(id=d['id'], err='字の色が地と分かれん', ref=R, ours=O)); print(d['id'], 'err', flush=True); continue
        df = {x: (None if R.get(x) is None or O.get(x) is None else O[x] - R[x]) for x in ('on', 'off', 'L', 'R')}
        rows.append(dict(id=d['id'], ref=R, ours=O, d=df)); print(d['id'], 'ref', R, 'ours', O, 'd', df, flush=True)
    od = f'{a.out}/reg'; os.makedirs(od, exist_ok=True)
    json.dump(rows, open(f'{od}/time_{a.ver}.json', 'w'), ensure_ascii=False, indent=1)
    ok = lambda r, x: r.get('d') and r['d'][x] is not None and abs(r['d'][x]) <= 1
    L = [f'# 字の時刻（{a.ver}）＝ 型の中だけで測る・差＝うち−手本（コマ）', '',
         f"- 出る 1コマ以内 {sum(1 for r in rows if ok(r, 'on'))}/{len(rows)}・消える {sum(1 for r in rows if ok(r, 'off'))}/{len(rows)}・左端 {sum(1 for r in rows if ok(r, 'L'))}・右端 {sum(1 for r in rows if ok(r, 'R'))}", '',
         '| id | 手本 出る | 左 | 右 | 消える | うち 出る | 左 | 右 | 消える | 差 出る | 左 | 右 | 消える |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        if 'err' in r: L.append(f"| {r['id']} | {r['err']} |||||||||||| "); continue
        x, o, z = r['ref'], r['ours'], r['d']
        L.append(f"| {r['id']} | {x['on']} | {x['L']} | {x['R']} | {x['off']} | {o['on']} | {o['L']} | {o['R']} | {o['off']} | {z['on']} | {z['L']} | {z['R']} | {z['off']} |")
    open(f'{od}/time_{a.ver}.md', 'w').write('\n'.join(L) + '\n'); print(L[2])

if __name__ == '__main__':
    main()
