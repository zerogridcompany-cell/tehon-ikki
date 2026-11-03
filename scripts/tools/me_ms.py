"""絵の出来事を1コマずつ出す（10/31 依頼者「人が見るより繊細に」）。カットだけでなく、黒地の細い線の書き換え・溶け・光り・動きの入りも拾う。

python3 me_ms.py <動画.mp4> <出す.json> [--w 640]
from me_ms import dekigoto, read_gray;  E = dekigoto(G, fps)
- 1コマごとの「変わった画素の割合」px（明るさの差 >12）と平均差 dd を出す
- 出来事＝px がまわりの静けさ（中央値）の6倍かつ 0.4% を超える山。2コマ以内の山は1つ
- 変わり始め f_start＝山から前へ、px が山の10%を下回る手前まで戻る／止まり f_end＝山から後ろへ同じく
- 1つずつ：f_start・f_peak・f_end・koma（何コマかけて変わったか）・t_start（秒＝pts）・px_peak・kind（cut＝1コマで入れ替わる／fade＝3コマ以上かけて全体が変わる／part＝一部だけ書き換わる／flash＝明るくなって戻る）
"""
import json, subprocess, sys
import numpy as np, cv2


def read_gray(path, w=640):
    cap = cv2.VideoCapture(path); G = []
    while True:
        ok, f = cap.read()
        if not ok: break
        h = int(round(f.shape[0] * w / f.shape[1] / 2) * 2)
        G.append(cv2.cvtColor(cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32))
    fps = cap.get(cv2.CAP_PROP_FPS)
    return np.array(G), fps


def pts(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    v = [x.strip().strip(",") for x in o.split()]   # 手本によっては "0.000000," と後ろに , が付く（10/31 tehonU）
    return np.array([float(x) for x in v if x not in ("", "N/A")])


REL = 2.3     # 画面全体：tehonU の正解 24 カットで一番弱いのが 2.44（802）
REL_T = 3.0   # 升ごと（8x8）
STILL = 0.3   # 升が「止まっとる」＝まわりのコマの変わり方の中央値がこれ以下
OFF = np.r_[np.arange(-10, -2), np.arange(3, 11)]


def _rel(x, eps):
    """x[i] ÷（まわり ±3〜10コマの中央値＋eps）。x は (N,) か (N,升)"""
    N = len(x); idx = np.arange(N)[:, None] + OFF[None, :]; ok = (idx >= 1) & (idx < N)
    w = x[np.clip(idx, 0, N - 1)].astype(float)
    if x.ndim == 1: w[~ok] = np.nan
    else: w[~ok, :] = np.nan
    base = np.nanmedian(w, axis=1)
    return (x / (base + eps), base) if x.ndim > 1 else x / (base + eps)


def dekigoto(G, fps, T=None):
    N = len(G)
    D = np.abs(np.diff(G, axis=0))
    px = np.r_[0, (D > 12).mean((1, 2))]; dd = np.r_[0, D.mean((1, 2))]
    lum = G.reshape(N, -1).mean(1)
    calm = float(np.median(px)) + 1e-6; th = max(0.004, 6 * calm)
    pk = [i for i in range(1, N) if px[i] > th and px[i] >= px[i - 1] and (i + 1 >= N or px[i] >= px[i + 1])]
    # ① 画面全体を、まわり（±3〜10コマ）の変わり方と比べる（10/31 tehonU：動きの多い手本は全体の基準が 0.40 まで上がって静かなカット 7本を見落とした＝17/24）
    #   足す数と下限は手本の「ふだんの変わり方」の中央値で決める（10/31 tehonR：黒地の HUD は中央値 0.03・tehonU は 3.4＝固定の数では片方が死ぬ）
    med = float(np.median(dd[1:])) if N > 2 else 0.0
    rel = _rel(dd, max(0.6 * med, 0.05))
    pk += [i for i in range(1, N) if rel[i] >= REL and dd[i] >= max(0.9 * med, 0.2) and   # 0.2＝止まった絵の圧縮のちらつき（0.14〜0.17）より上（作った試験で 0 近くまで下がって 20 回余計）
                rel[i] >= rel[i - 1] and (i + 1 >= N or rel[i] >= rel[i + 1])]
    # ② 画面を 8x8 の升に分けて、升ごとに同じ比べ方をする（10/31 tehonR 462：小さい札の動きが、別の所で回っとる 3D の動きに埋もれて画面全体では見えんかった。人の目は場所ごとに見とる）
    H8, W8 = G.shape[1] // 8 * 8, G.shape[2] // 8 * 8
    ddt = np.vstack([np.zeros((1, 64)), D[:, :H8, :W8].reshape(N - 1, 8, H8 // 8, 8, W8 // 8).mean((2, 4)).reshape(N - 1, 64)])
    pxt = np.vstack([np.zeros((1, 64)), (D[:, :H8, :W8] > 12).reshape(N - 1, 8, H8 // 8, 8, W8 // 8).mean((2, 4)).reshape(N - 1, 64)])
    medt = np.median(ddt[1:], axis=0)
    relt, baset = _rel(ddt, np.maximum(0.6 * medt, 0.1))
    # 升の出来事は「止まっとった所が急に変わった」時だけ（まわりの中央値 ≤ STILL）。動いとる所の動きは数えん（10/31 tehonU：実写の動きを 160 回も数えた）
    hit = (relt >= REL_T) & (ddt >= np.maximum(0.9 * medt, 0.4)) & (baset <= STILL) & (pxt >= 0.003)   # pxt＝升の中で 12 より大きく変わった画素の割合（圧縮の波は小さい差が広く出るだけ＝作った試験で 10 回余計）／0.4＝升の平均の明るさの差（黒地の圧縮のちらつきは 0.03 前後）
    hit[1:-1] &= (relt[1:-1] >= relt[:-2]) & (relt[1:-1] >= relt[2:])
    prev = np.zeros_like(ddt)   # 同じ升の前6コマの一番大きい変わり
    for j in range(1, 7): prev[j:] = np.maximum(prev[j:], ddt[:-j])
    hit &= ddt >= 0.4 * prev   # 大きい変わりの後の小さい変わり＝圧縮が字を整え直しとるだけ（10/31 作った試験：字の書き換えの 4〜5コマ後に毎回出た）
    pk = sorted(set(pk)); m = []
    for p in pk:   # 隣のコマだけ1つにする＝変わりの大きい方（10/31 tehonR：2コマ離れた式の替わり 359・361 を1つにしとった）
        if m and p - m[-1] <= 1:
            if dd[p] > dd[m[-1]]: m[-1] = p
        else: m.append(p)
    pk = m
    pkm = sorted(int(i) for i in np.where(hit.any(1))[0] if i >= 1 and all(abs(i - q) > 1 for q in pk))   # 升の出来事＝別の帳（kind="masu"）。画面全体の出来事の隣（±1コマ）には足さん
    T = T if T is not None and len(T) == N else np.arange(N) / fps
    out = []; seen = set()
    for chan, P in (("main", pk), ("masu", pkm)):
        for k, p in enumerate(P):
            lo_lim = P[k - 1] + 1 if k else 1; hi_lim = P[k + 1] - 1 if k + 1 < len(P) else N - 1   # 前後の出来事をまたがん（10/31 tehonR：462 が 457 に吸われて消えた）
            if chan == "main":   # 画面全体で戻る＝前の版（tehonU 24/24・作った試験 45/45 の形）
                J = np.ones(64, bool); top = px[p]; s = p
                while s - 1 >= lo_lim and px[s - 1] >= 0.1 * top and px[s - 1] > th * 0.5 and (rel[s - 1] >= 1.5 or dd[s - 1] >= 0.3 * dd[p]): s -= 1
                e = p
                while e + 1 <= hi_lim and px[e + 1] >= 0.1 * top and px[e + 1] > th * 0.5 and (rel[e + 1] >= 1.5 or dd[e + 1] >= 0.3 * dd[p]): e += 1
            else:   # 変わった升だけで戻る
                J = hit[p]; dj = ddt[:, J].mean(1); top = dj[p]; s = p
                while s - 1 >= lo_lim and dj[s - 1] >= 0.35 * top: s -= 1
                e = p
                while e + 1 <= hi_lim and dj[e + 1] >= 0.35 * top: e += 1
            if (chan, s) in seen: continue
            seen.add((chan, s)); a, b = max(0, s - 1), min(N - 1, e + 1)
            whole = float((np.abs(G[b] - G[a]) > 12).mean())
            lo = lum[max(0, s - 4):s].mean() if s > 0 else lum[s]; hi = lum[min(N - 1, e + 1):min(N, e + 5)].mean() if e + 1 < N else lum[e]
            if chan == "masu": kind = "masu"
            elif lum[p] - max(lo, hi) > 25 and e - s <= 2: kind = "flash"
            elif e - s + 1 >= 3 and whole > 0.3: kind = "fade"
            elif whole > 0.3: kind = "cut"
            else: kind = "part"
            out.append(dict(f_start=int(s), f_peak=int(p), f_end=int(e), koma=int(e - s + 1), t_start=round(float(T[s]), 5),
                            px_peak=round(float(px[p]), 4), rel=round(float(rel[p]), 2), rel_t=round(float(relt[p].max()), 2), masu=int(J.sum()), whole=round(whole, 3), kind=kind))
    out.sort(key=lambda e: e["f_start"])
    # 画面全体の出来事でコマが続いとる物（前の止まり＋1 ≥ 次の始まり）は1つ＝ゆっくりの溶けを2つに割らん（10/31 作った試験：7コマの溶けを 6 回割った）
    mo = []
    for e in out:
        q = next((x for x in reversed(mo) if x["kind"] != "masu"), None) if e["kind"] != "masu" else None
        if q is not None and e["f_start"] <= q["f_end"] + 1 and e["koma"] + q["koma"] >= 3 and max(q["whole"], e["whole"]) > 0.3:   # 画面の一部の小さい変わりはつなげん（tehonR の HUD が鎖になって 4つ消えた）
            q["f_end"] = max(q["f_end"], e["f_end"]); q["koma"] = q["f_end"] - q["f_start"] + 1
            if e["px_peak"] > q["px_peak"]: q.update(f_peak=e["f_peak"], px_peak=e["px_peak"], rel=e["rel"])
            if q["koma"] >= 3 and max(q["whole"], e["whole"]) > 0.3: q["kind"] = "fade"
            q["whole"] = max(q["whole"], e["whole"]); continue
        mo.append(e)
    out = mo
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("mp4"); ap.add_argument("out"); ap.add_argument("--w", type=int, default=640); a = ap.parse_args()
    G, fps = read_gray(a.mp4, a.w); E = dekigoto(G, fps, pts(a.mp4))
    json.dump(dict(src=a.mp4, fps=fps, frames=len(G), events=E), open(a.out, "w"), ensure_ascii=False)
    from collections import Counter
    print("絵の出来事", len(E), dict(Counter(e["kind"] for e in E)))
