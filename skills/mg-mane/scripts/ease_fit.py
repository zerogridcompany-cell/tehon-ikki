#!/usr/bin/env python3
"""mg-mane の「曲線当て」：測った道（kiseki.json）を「動く区間／止まる区間」に割り、区間ごとに一番合うイージングを選ぶ。

/usr/bin/python3 ease_fit.py <kiseki.json> [--axis y] --out <keys.json> [--warp 9] [--seg "25-34,34-60"] [--name M.y]
    [--scale 1] [--offset 0] [--rel 1] [--thr 0.3] [--kinds bezier,expo_out,pow_out,back_out,spring,bounce] [--jpg 絵.jpg]

時間＝手本のコマ f。--warp 9 は「手本の中の時間 τ が 9 コマごとに 1 コマ飛ぶ」（τ(f)=f+floor(f/9)・tehonN で実測）＝曲線は τ で当てる。
候補＝cubic-bezier(x1,y1,x2,y2)（CSS と同じ）・expo_out(k)・pow_out(n)（n=3 が cubic-out）・pow_in(n)・back_out(c)（行き過ぎ）・
      spring(w,z,v0)（バネ・w=1τコマあたりの角速度・z=減衰比・v0=初めの速さ）・bounce・linear
判定＝位置の残差 RMS（測った単位）と、速さ v(τ) の相関（≥0.97 を「合う」）。合う物の中で RMS が一番小さい物。合う物が無ければ相関が一番高い物（ok=false）
出す物＝keys.json {name, warp, unit, segs:[{t0,t1（手本のコマ）,T0,T1（τ）,from,to,ease:{kind,…},rms,vcorr,ok} | {kind:"hold",t0,t1,v}]}
        ＋絵（上＝位置：点が測り・線が当て／下＝速さ）
"""
import argparse, json, math, os
import numpy as np
import cv2

# ---------------- 時間 ----------------
def tau(f, warp):
    if not warp:
        return float(f)
    n = math.floor(f); fr = f - n
    a = n + math.floor(n / warp); b = (n + 1) + math.floor((n + 1) / warp)
    return a + (b - a) * fr

def tau_inv(T, warp):
    if not warp:
        return float(T)
    n = math.floor(T * warp / (warp + 1)) - 2
    while tau(n + 1, warp) <= T:
        n += 1
    a, b = tau(n, warp), tau(n + 1, warp)
    return n + (T - a) / (b - a)

# ---------------- 曲線（u∈[0,1] → 0..1） ----------------
def bezier(u, x1, y1, x2, y2):
    u = np.clip(np.asarray(u, float), 0, 1)
    s = u.copy()
    for _ in range(8):  # Newton
        x = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s ** 2 * x2 + s ** 3
        dx = 3 * (1 - s) ** 2 * x1 + 6 * (1 - s) * s * (x2 - x1) + 3 * s ** 2 * (1 - x2)
        s = np.clip(s - (x - u) / np.where(np.abs(dx) < 1e-6, 1e-6, dx), 0, 1)
    lo = np.zeros_like(u); hi = np.ones_like(u)
    for _ in range(20):  # 二分（Newton が外れた所の保険）
        x = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s ** 2 * x2 + s ** 3
        bad = np.abs(x - u) > 1e-5
        if not bad.any():
            break
        m = (lo + hi) / 2
        xm = 3 * (1 - m) ** 2 * m * x1 + 3 * (1 - m) * m ** 2 * x2 + m ** 3
        lo = np.where(bad & (xm < u), m, lo); hi = np.where(bad & (xm >= u), m, hi)
        s = np.where(bad, (lo + hi) / 2, s)
    return 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s ** 2 * y2 + s ** 3

def bounce(u):
    u = np.clip(np.asarray(u, float), 0, 1); n1, d1 = 7.5625, 2.75
    return np.where(u < 1 / d1, n1 * u * u, np.where(u < 2 / d1, n1 * (u - 1.5 / d1) ** 2 + 0.75,
                    np.where(u < 2.5 / d1, n1 * (u - 2.25 / d1) ** 2 + 0.9375, n1 * (u - 2.625 / d1) ** 2 + 0.984375)))

def spring_t(t, w, z, v0=0.0):
    """0→1 のバネ（t は τ コマ・t<0 は 0）。x''+2zw x'+w²x=w²・x(0)=0・x'(0)=v0"""
    t = np.maximum(np.asarray(t, float), 0)
    if z < 0.999:
        wd = w * math.sqrt(1 - z * z)
        return 1 - np.exp(-z * w * t) * (np.cos(wd * t) + ((z * w - v0) / wd) * np.sin(wd * t))
    if z <= 1.001:
        return 1 - np.exp(-w * t) * (1 + (w - v0) * t)
    r1 = -w * (z - math.sqrt(z * z - 1)); r2 = -w * (z + math.sqrt(z * z - 1))
    # x = 1 + A e^{r1 t} + B e^{r2 t} ; A+B=-1 ; r1 A + r2 B = v0
    B = (v0 + r1) / (r2 - r1); A = -1 - B
    return 1 + A * np.exp(r1 * t) + B * np.exp(r2 * t)

def ease_u(kind, p, u):
    u = np.clip(np.asarray(u, float), 0, 1)
    if kind == 'linear': return u
    if kind == 'pow_out': return 1 - (1 - u) ** p[0]
    if kind == 'pow_in': return u ** p[0]
    if kind == 'pow_inout': return np.where(u < 0.5, 0.5 * (2 * u) ** p[0], 1 - 0.5 * (2 - 2 * u) ** p[0])
    if kind == 'expo_out': k = p[0]; return (1 - np.exp(-k * u)) / (1 - math.exp(-k))
    if kind == 'bezier': return bezier(u, *p)
    if kind == 'back_out': c = p[0]; return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2
    if kind == 'bounce': return bounce(u)
    raise ValueError(kind)

KINDS = ['linear', 'pow_out', 'pow_in', 'pow_inout', 'expo_out', 'bezier', 'back_out', 'bounce', 'spring']

# ---------------- 当て（Nelder–Mead） ----------------
def nm(fun, x0, step, iters=500):
    n = len(x0); P = [np.array(x0, float)] + [np.array(x0, float) + np.eye(n)[i] * step[i] for i in range(n)]
    V = [fun(p) for p in P]
    for _ in range(iters):
        o = np.argsort(V); P = [P[i] for i in o]; V = [V[i] for i in o]
        if abs(V[-1] - V[0]) < 1e-12:
            break
        c = np.mean(P[:-1], 0); xr = c + (c - P[-1]); fr = fun(xr)
        if fr < V[0]:
            xe = c + 2 * (c - P[-1]); fe = fun(xe)
            P[-1], V[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < V[-2]:
            P[-1], V[-1] = xr, fr
        else:
            xc = c + 0.5 * (P[-1] - c); fc = fun(xc)
            if fc < V[-1]:
                P[-1], V[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    P[i] = P[0] + 0.5 * (P[i] - P[0]); V[i] = fun(P[i])
    i = int(np.argmin(V)); return P[i], V[i]

def model(kind, prm, T, S0, S1, p0, p1):
    """prm＝曲線の数（spring は w,z,v0,to）。S0,S1＝τ の始め・終わり"""
    if kind == 'spring':
        w, z, v0, to = prm
        return p0 + (to - p0) * spring_t(T - S0, w, z, v0)
    u = (T - S0) / max(S1 - S0, 1e-6)
    return p0 + (p1 - p0) * ease_u(kind, prm, u)

def corr(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if len(a) < 3 or a.std() < 1e-9 or b.std() < 1e-9:
        return 1.0 if np.allclose(a, b, atol=1e-6) else 0.0
    return float(np.corrcoef(a, b)[0, 1])

def fit_kind(kind, T, P, S0, S1, p0, p1, tail=None):
    """S0,S1 も ±1 τ の中で動かす。tail＝区間のあとの止まり（バネの尾を確かめる）"""
    TT = T if tail is None else np.concatenate([T, tail[0]]); PP = P if tail is None else np.concatenate([P, tail[1]])
    rng = abs(p1 - p0) + 1e-6
    def loss(x):
        s0, s1 = x[0], x[1]
        if s1 - s0 < 0.5 or abs(s0 - S0) > 1.2 or abs(s1 - S1) > 1.2:
            return 1e9
        prm = x[2:]
        if kind in ('pow_out', 'pow_in', 'pow_inout') and not (1.0 <= prm[0] <= 12): return 1e9
        if kind == 'expo_out' and not (0.3 <= prm[0] <= 30): return 1e9
        if kind == 'bezier' and not (0 <= prm[0] <= 1 and 0 <= prm[2] <= 1 and -1.5 <= prm[1] <= 2.5 and -1.5 <= prm[3] <= 2.5): return 1e9
        if kind == 'back_out' and not (0 <= prm[0] <= 6): return 1e9
        if kind == 'spring' and not (0.05 <= prm[0] <= 3.5 and 0.05 <= prm[1] <= 1.6): return 1e9
        m = model(kind, prm, TT, s0, s1, p0, p1)
        e = np.mean((m - PP) ** 2)
        # 速さの形も見る（測りのゆれに負けんように軽く）
        vm = np.diff(PP) / np.maximum(np.diff(TT), 1e-6); vf = np.diff(m) / np.maximum(np.diff(TT), 1e-6)
        return e + 0.25 * np.mean((vm - vf) ** 2)
    inits = {
        'linear': [[]], 'pow_out': [[2.0], [3.0], [5.0]], 'pow_in': [[2.0], [3.0]], 'pow_inout': [[2.0], [3.0]],
        'expo_out': [[3.0], [6.0], [10.0]], 'bezier': [[0.25, 0.1, 0.25, 1.0], [0.0, 0.0, 0.2, 1.0], [0.4, 0.0, 0.2, 1.0], [0.3, 0.6, 0.3, 1.2], [0.5, 0.0, 0.5, 1.0]],
        'back_out': [[1.0], [1.7], [3.0]], 'bounce': [[]],
        'spring': [[w, z, v0, p1] for w in (0.25, 0.6, 1.2) for z in (0.3, 0.6, 0.95) for v0 in (0.0,)],
    }[kind]
    best = None
    for ini in inits:
        x0 = [S0, S1] + list(ini)
        st = [0.4, 0.4] + [max(0.05, abs(v) * 0.3) if i < 3 or kind != 'spring' else rng * 0.1 for i, v in enumerate(ini)]
        if kind == 'spring':
            st = [0.4, 0.4, 0.15, 0.15, 0.05, rng * 0.05 + 1e-3]
        x, val = nm(loss, x0, st, iters=600 if len(x0) > 3 else 300)
        if best is None or val < best[1]:
            best = (x, val)
    x = best[0]; s0, s1, prm = x[0], x[1], list(x[2:])
    m = model(kind, prm, TT, s0, s1, p0, p1)
    rms = float(np.sqrt(np.mean((m - PP) ** 2)))
    vm = np.diff(PP) / np.maximum(np.diff(TT), 1e-6); vf = np.diff(m) / np.maximum(np.diff(TT), 1e-6)
    vc = corr(vm, vf) if np.abs(vm).max() > 1e-6 else 1.0
    return dict(kind=kind, prm=prm, S0=float(s0), S1=float(s1), rms=rms, vcorr=vc)

def ease_dict(kind, prm):
    if kind == 'spring': return dict(kind='spring', w=round(prm[0], 4), z=round(prm[1], 4), v0=round(prm[2], 5))
    if kind == 'bezier': return dict(kind='bezier', x1=round(prm[0], 4), y1=round(prm[1], 4), x2=round(prm[2], 4), y2=round(prm[3], 4))
    if kind in ('pow_out', 'pow_in', 'pow_inout'): return dict(kind=kind, n=round(prm[0], 4))
    if kind == 'expo_out': return dict(kind=kind, k=round(prm[0], 4))
    if kind == 'back_out': return dict(kind=kind, c=round(prm[0], 4))
    return dict(kind=kind)

# ---------------- 区間 ----------------
def auto_segments(T, P, thr, rel):
    v = np.abs(np.diff(P)) / np.maximum(np.diff(T), 1e-6)
    lim = max(thr, rel * (v.max() if len(v) else 0))
    mv = v > lim
    runs = []; s = None; last = -99
    for i, m in enumerate(mv):
        if m:
            if s is None or i - last > 2:
                if s is not None: runs.append((s, last))
                s = i
            last = i
    if s is not None: runs.append((s, last))
    # 速さ v[i] は i→i+1。区間は点 i0=s から i1=last+1
    return [(a, b + 1) for a, b in runs if b + 1 - a >= 2]

def split_reversals(T, P, a, b, frac=0.15):
    seg = P[a:b + 1]; rng = seg.max() - seg.min()
    if rng < 1e-6: return [(a, b)]
    cuts = [a]
    d = np.sign(np.diff(seg)); d[d == 0] = 1
    last = 0
    for i in range(1, len(d)):
        if d[i] != d[i - 1]:
            j = i  # 点 a+i が山・谷
            if abs(seg[j] - seg[last]) > frac * rng and abs(seg[-1] - seg[j]) > 0.02 * rng:
                cuts.append(a + j); last = j
    cuts.append(b)
    return [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1) if cuts[i + 1] > cuts[i]]

def split_valleys(T, P, a, b, frac=0.45):
    """同じ向きに 2 回以上加速する動き（速さの谷）で割る"""
    v = np.abs(np.diff(P[a:b + 1])) / np.maximum(np.diff(T[a:b + 1]), 1e-6)
    if len(v) < 5: return [(a, b)]
    vs = np.convolve(v, np.ones(3) / 3, 'same')
    cuts = [a]
    for i in range(2, len(vs) - 2):
        if vs[i] <= vs[i - 1] and vs[i] <= vs[i + 1]:
            lp = vs[max(cuts[-1] - a, 0):i].max() if i > cuts[-1] - a else 0; rp = vs[i + 1:].max()
            if vs[i] < frac * min(lp, rp) and i + a - cuts[-1] >= 3 and b - (i + a) >= 3:
                cuts.append(a + i)
    cuts.append(b)
    return [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('--axis', default='y'); ap.add_argument('--out', required=True)
    ap.add_argument('--warp', type=int, default=0); ap.add_argument('--seg', default=None); ap.add_argument('--name', default=None)
    ap.add_argument('--scale', type=float, default=1.0); ap.add_argument('--offset', type=float, default=0.0)
    ap.add_argument('--rel', type=int, default=0, help='1＝始めのコマを 0 にする')
    ap.add_argument('--thr', type=float, default=0.3); ap.add_argument('--relthr', type=float, default=0.02)
    ap.add_argument('--kinds', default='linear,pow_out,pow_in,pow_inout,expo_out,bezier,back_out,bounce,spring')
    ap.add_argument('--from', dest='f0', type=float, default=None); ap.add_argument('--to', dest='f1', type=float, default=None)
    ap.add_argument('--jpg', default=None)
    a = ap.parse_args()
    J = json.load(open(a.src))
    rows = [r for r in J['frames'] if a.axis in r and r[a.axis] is not None]
    if a.f0 is not None: rows = [r for r in rows if r['f'] >= a.f0]
    if a.f1 is not None: rows = [r for r in rows if r['f'] <= a.f1]
    F = np.array([r['f'] for r in rows], float)
    P = np.array([r[a.axis] for r in rows], float) * a.scale + a.offset
    if a.rel: P = P - P[0]
    T = np.array([tau(f, a.warp) for f in F])
    kinds = a.kinds.split(',')
    if a.seg:
        segs = []
        for part in a.seg.split(','):
            x0, x1 = [float(v) for v in part.split('-')]
            i0 = int(np.argmin(np.abs(F - x0))); i1 = int(np.argmin(np.abs(F - x1))); segs.append((i0, i1))
    else:
        segs = []
        for (i0, i1) in auto_segments(T, P, a.thr, a.relthr):
            segs.append((i0, i1))
    out = []; cur = P[0]; prev_end = 0
    fitted = np.full(len(P), np.nan)
    def add_hold(i0, i1, v):
        if i1 > i0: out.append(dict(kind='hold', t0=float(F[i0]), t1=float(F[i1]), T0=float(T[i0]), T1=float(T[i1]), v=round(float(v), 4)))
    for (i0, i1) in segs:
        if i0 > prev_end: add_hold(prev_end, i0, P[prev_end] if not out else cur)
        pieces = [(i0, i1)]
        # 1 本で当てて合わんなら、行き過ぎ以外の戻り（山・谷）で割る
        trial = []
        for k in kinds:
            if abs(P[i1] - P[i0]) < 1e-6 and k != 'spring': continue
            tail = None
            if k == 'spring' and i1 + 1 < len(P):
                j = min(len(P), i1 + 12); tail = (T[i1 + 1:j], P[i1 + 1:j])
            r = fit_kind(k, T[i0:i1 + 1], P[i0:i1 + 1], T[i0], T[i1], P[i0], P[i1], tail)
            trial.append(r)
        good = [r for r in trial if r['vcorr'] >= 0.97]
        best = min(good, key=lambda r: r['rms']) if good else (max(trial, key=lambda r: r['vcorr']) if trial else None)
        if best is None or best['vcorr'] < 0.97:
            pieces = []
            for (q0, q1) in split_reversals(T, P, i0, i1):
                pieces += split_valleys(T, P, q0, q1)
        if len(pieces) == 1 and best is not None:
            res = [(i0, i1, best)]
        else:
            res = []
            for (j0, j1) in pieces:
                tr = []
                for k in kinds:
                    if abs(P[j1] - P[j0]) < 1e-6 and k != 'spring': continue
                    tail = None
                    if k == 'spring' and j1 + 1 < len(P):
                        jj = min(len(P), j1 + 12); tail = (T[j1 + 1:jj], P[j1 + 1:jj])
                    tr.append(fit_kind(k, T[j0:j1 + 1], P[j0:j1 + 1], T[j0], T[j1], P[j0], P[j1], tail))
                gd = [r for r in tr if r['vcorr'] >= 0.97]
                bb = min(gd, key=lambda r: r['rms']) if gd else max(tr, key=lambda r: r['vcorr'])
                res.append((j0, j1, bb))
        for (j0, j1, r) in res:
            S0, S1 = r['S0'], r['S1']
            to = r['prm'][3] if r['kind'] == 'spring' else float(P[j1])
            # つなぎ目で跳ばん：前の区間（止まり・バネの尾）の終わりの値から始める
            fr0 = float(cur) if (out and abs(cur - P[j0]) < 0.25 * (abs(to - P[j0]) + 1e-6) + 2.0) else float(P[j0])
            seg = dict(kind='move', t0=round(tau_inv(S0, a.warp), 4), t1=round(tau_inv(S1, a.warp), 4), T0=round(S0, 4), T1=round(S1, 4),
                       **{'from': round(fr0, 4)}, to=round(float(to), 4), ease=ease_dict(r['kind'], r['prm']),
                       rms=round(r['rms'], 3), vcorr=round(r['vcorr'], 4), ok=bool(r['vcorr'] >= 0.97),
                       cands={x['kind']: [round(x['rms'], 3), round(x['vcorr'], 3)] for x in trial} if (j0, j1) == (i0, i1) else None)
            if seg['cands'] is None: del seg['cands']
            out.append(seg)
            m = model(r['kind'], r['prm'], T[j0:j1 + 1], S0, S1, fr0, P[j1])
            fitted[j0:j1 + 1] = m
            cur = float(to) if r['kind'] != 'spring' else float(fr0 + (to - fr0) * spring_t(T[min(j1, len(T) - 1)] - S0, r['prm'][0], r['prm'][1], r['prm'][2]))
        prev_end = segs[-1][1] if segs else 0
        prev_end = i1
    if prev_end < len(P) - 1: add_hold(prev_end, len(P) - 1, cur)
    # 止まりの所の当て＝前の値（バネは尾）
    name = a.name or f"{J.get('name') or os.path.basename(a.src)}.{a.axis}"
    K = dict(name=name, src=os.path.abspath(a.src), axis=a.axis, warp=a.warp, scale=a.scale, offset=a.offset, rel=a.rel, segs=out,
             measured=[[float(f), round(float(p), 3)] for f, p in zip(F, P)])
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(K, open(a.out, 'w'), ensure_ascii=False, indent=1)
    # 絵：全体を keys で評価（ease.ts と同じ式）して測りと並べる
    ev = np.array([eval_keys(K, f) for f in F])
    jp = a.jpg or os.path.splitext(a.out)[0] + '.jpg'
    draw(F, P, ev, out, jp, name, a.warp)
    for s in out:
        if s['kind'] == 'hold':
            print(f"  止  {s['t0']:.1f}-{s['t1']:.1f}  {s['v']}")
        else:
            e = s['ease']; ps = ' '.join(f'{k}={v}' for k, v in e.items() if k != 'kind')
            print(f"  動  {s['t0']:.2f}-{s['t1']:.2f}  {s['from']:.2f}→{s['to']:.2f}  {e['kind']}({ps})  rms {s['rms']}  vcorr {s['vcorr']}{'' if s['ok'] else '  ⚠'}")
    print(f'→ {a.out}・絵 {jp}')

def eval_keys(K, f):
    """ease.ts の kfAt と同じ（Python 版・確かめ用）"""
    w = K.get('warp', 0); t = tau(f, w); segs = K['segs']
    if not segs: return 0.0
    act = None
    for s in segs:
        if tau(s['t0'], w) <= t + 1e-9: act = s
    if act is None:
        s = segs[0]; return s['v'] if s['kind'] == 'hold' else s['from']
    if act['kind'] == 'hold': return act['v']
    S0, S1 = tau(act['t0'], w), tau(act['t1'], w); e = act['ease']; k = e['kind']
    if k == 'spring':
        return act['from'] + (act['to'] - act['from']) * float(spring_t(t - S0, e['w'], e['z'], e.get('v0', 0.0)))
    prm = {'pow_out': [e.get('n')], 'pow_in': [e.get('n')], 'pow_inout': [e.get('n')], 'expo_out': [e.get('k')], 'back_out': [e.get('c')],
           'bezier': [e.get('x1'), e.get('y1'), e.get('x2'), e.get('y2')]}.get(k, [])
    u = (t - S0) / max(S1 - S0, 1e-6)
    return act['from'] + (act['to'] - act['from']) * float(ease_u(k, prm, u))

def draw(F, P, E, segs, path, name, warp):
    Wd, Hg = 1400, 260
    def panel(Y1, Y2, title, h):
        g = np.full((h, Wd, 3), 26, np.uint8)
        ok = np.isfinite(Y1)
        lo = min(np.nanmin(Y1), np.nanmin(Y2)); hi = max(np.nanmax(Y1), np.nanmax(Y2)); sp = max(hi - lo, 1e-6)
        X = lambda f: int(10 + (f - F[0]) / max(F[-1] - F[0], 1) * (Wd - 20))
        Yp = lambda v: int(h - 12 - (v - lo) / sp * (h - 34))
        for s in segs:
            c = (60, 60, 60) if s['kind'] == 'hold' else (40, 70, 40)
            cv2.rectangle(g, (X(s['t0']), 22), (X(s['t1']), h - 4), c, -1)
        pts2 = np.array([(X(f), Yp(v)) for f, v in zip(F, Y2)], np.int32)
        cv2.polylines(g, [pts2], False, (80, 200, 255), 2, cv2.LINE_AA)
        for f, v in zip(F, Y1):
            cv2.circle(g, (X(f), Yp(v)), 3, (255, 170, 60), -1, cv2.LINE_AA)
        cv2.putText(g, f'{title}  {lo:.2f}..{hi:.2f}   dots=measured  line=fit   {name}  warp={warp}', (8, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)
        for f in range(int(F[0]), int(F[-1]) + 1):
            if f % 9 == 0 and warp:
                cv2.line(g, (X(f), h - 8), (X(f), h - 2), (120, 120, 255), 1)
        return g
    v1 = np.r_[0, np.diff(P)]; v2 = np.r_[0, np.diff(E)]
    img = np.vstack([panel(P, E, 'position', Hg), panel(v1, v2, 'speed per frame', 200)])
    cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 85])

if __name__ == '__main__':
    main()
