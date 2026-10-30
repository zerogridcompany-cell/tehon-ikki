"""char_time.py  打ち字（reveal あり）の1字ずつの出るコマを手本とうちで測り、reveal [r0,r1] の直しを出す（51 再開4回目）。

何をする：字の型を1字ずつの塊に分ける（空白以外の字の数と合う時だけ）。1字の出る＝その字の型の中の字の色の近さ（まわりの輪を引く）が
  出揃いの 0.5 を超える最初のコマ。直し：うちの（出るコマ − fps×決めた時刻 ti）の中央値＝ずれ off。
  手本の出るコマ − off を fps で割った物に r0 + (r1−r0)k/(n−1) を最小二乗で当てる（rtl＝右から出る字も読む）。
使い方：python3 char_time.py <うちの mp4> <版名> --work <作業> [--ids a,b] [--apply]
入れる物：手本・うちの mp4・字の表（reveal がある字・words がある字は外す）・字だけの層
出す物：<out>/reg/char_<版名>.json（字ごとの出るコマ・r0,r1 の案 new・残り resid コマ）。--apply で resid 2コマ以内の字だけ reveal に書く
効いた数字（51）：打ち字 10/11 が全部の字で ±1コマ。Txt51.tsx の charAlpha（1字の溶け込み cfade 既定 0.1秒＝手本は 3コマで出る）と組
"""
import os, sys, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U

def onset(F, M, Mbg, col, kf):
    L = np.exp(-((F - col) ** 2).sum(3) / (2 * 45.0 ** 2)); p = L[:, M].mean(1) - L[:, Mbg].mean(1)
    pre = np.median(p[:4]); top = np.median(p[max(0, kf - 2):kf + 3]); rng = top - pre
    if rng < 0.05: return None
    q = (p - pre) / rng
    return next((i for i in range(0, kf + 1) if q[i] >= 0.5), None)

def main():
    ap = U.base_args(__doc__); ap.add_argument('ours'); ap.add_argument('ver'); ap.add_argument('--apply', action='store_true')
    a = U.resolve(ap.parse_args()); K, fps = a.K, a.fps
    P = int(round(24 * K)); e3 = np.ones((3, 3), np.uint8); d29 = np.ones((int(29 * K) | 1,) * 2, np.uint8); d11 = np.ones((int(11 * K) | 1,) * 2, np.uint8)
    res = []; nap = 0
    for k, d in enumerate(a.T):
        if a.idset and d['id'] not in a.idset: continue
        if not d.get('reveal') or d.get('words'): continue
        A = U.sheet_alpha(a.sheet, k)
        if A is None: continue
        X0, Y0, X1, Y1 = U.ebox(A, P, a.W, a.H); aa = A[Y0:Y1, X0:X1] > 0.5
        G = U.glyphs(aa); chars = [i for i, c in enumerate(d['text']) if not c.isspace()]
        if len(G) != len(chars): res.append(dict(id=d['id'], err=f'塊 {len(G)} と字 {len(chars)} が合わん')); print(d['id'], res[-1]['err']); continue
        Mbg = (cv2.dilate(aa.astype(np.uint8), d29) > 0) & ~(cv2.dilate(aa.astype(np.uint8), d11) > 0)
        fm = U.frame_of(d, fps)
        f0 = max(0, int(round(min(d['t0'], d['reveal'][0]) * fps)) - int(round(0.33 * fps))); f1 = min(a.N - 1, fm + 3); n = f1 - f0; kf = fm - f0
        on = {}
        for tag, src in (('ref', a.ref), ('ours', a.ours)):
            F = U.clip(src, f0, n, X0, Y0, X1 - X0, Y1 - Y0, fps); kk = min(kf, len(F) - 1)
            col = np.median(F[kk][aa], 0)
            on[tag] = [None if (o := onset(F, cv2.erode(g.astype(np.uint8), e3) > 0, Mbg, col, kk)) is None else f0 + o for g in G]
        N = len(d['text']); r0, r1 = d['reveal']; rtl = d.get('rtl')
        ti = [r0 + (r1 - r0) * ((N - 1 - i) if rtl else i) / max(1, N - 1) for i in chars]
        offs = [o - fps * t for o, t in zip(on['ours'], ti) if o is not None]
        row = dict(id=d['id'], chars=[d['text'][i] for i in chars], ref=on['ref'], ours=on['ours'], reveal=[r0, r1])
        if offs and sum(o is not None for o in on['ref']) >= 2:
            off = float(np.median(offs))
            kx = np.array([((N - 1 - i) if rtl else i) / max(1, N - 1) for i, o in zip(chars, on['ref']) if o is not None])
            y = np.array([(o - off) / fps for o in on['ref'] if o is not None])
            X = np.stack([1 - kx, kx], 1); (n0, n1), *_ = np.linalg.lstsq(X, y, rcond=None)
            row.update(off=round(off, 2), new=[round(float(n0), 3), round(float(n1), 3)], resid=round(float(np.abs(X @ [n0, n1] - y).max() * fps), 1),
                       d=[None if (x is None or z is None) else z - x for x, z in zip(on['ref'], on['ours'])])
            if a.apply and row['resid'] <= 2: d['reveal'] = row['new']; nap += 1
        res.append(row); print(d['id'], 'd', row.get('d'), 'reveal', [r0, r1], '→', row.get('new'), 'resid', row.get('resid'), flush=True)
    os.makedirs(f'{a.out}/reg', exist_ok=True)
    json.dump(res, open(f'{a.out}/reg/char_{a.ver}.json', 'w'), ensure_ascii=False, indent=1)
    if a.apply: U.save_texts(a.texts, a.T, a.fmt, fps); print('reveal を書いた', nap)

if __name__ == '__main__':
    main()
