#!/usr/bin/env python3
"""mg-mane の「滑らか」：動いとる物の速さを1コマずつ測って、カクカク（止まり・階段・ギザ）を手本と比べる。

/usr/bin/python3 nameraka.py <手本.mp4> <うち.mp4> [--out <置き場>] [--w 480] [--top 5]

hakaru.py の「滑らかさ」は画面全体の差の2階差＝動く面積と速さが混ざって、字1つの階段は薄まる。
ここは光の流れ（Farneback）で「動いとる画素だけの速さ v(t)」を出して、動く区間ごとに比べる：
  止まり   ＝手本がそのコマで動いとる（>1px/コマ）のに、うちが同じコマか、速さもコマの差も手本の3割未満（止めコマ＝カクつきの一番の元。差も見るのは黒い無地で流れが暴れるから）
  余計     ＝手本が止まっとるのに、うちが動いとるコマ
  速さの波 ＝区間の中の v(t) の形の相関（線形の表＝台形、手本のイージング＝山）
  ギザ     ＝区間の中の |Δ²v| の平均 ÷ 区間の速さの平均。うち÷手本の比
  折れ     ＝加速度の符号が変わる回数（線形の表はキーごとに折れる）
出す物＝<置き場>/滑らか.md（区間の表・悪い順）・滑らか.json・滑らか_<区間>.jpg（手本｜うち 8コマ＋v(t) の線）
目安＝止まり 0・速さの波 ≥0.95・ギザ比 ≤1.3・折れ比 ≤1.5（🟡は 2・0.90・1.6・2）
"""
import argparse, json, os, sys
import numpy as np
import cv2

J_STOP = (0, 2)
J_WAVE = (0.95, 0.90)
J_GIZA = (1.3, 1.6)
J_ORE = (1.5, 2.0)


def read(p, w):
    cap = cv2.VideoCapture(p)
    fps = cap.get(cv2.CAP_PROP_FPS)
    G, C = [], []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        h = int(round(f.shape[0] * w / f.shape[1]))
        s = cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA)
        C.append(s)
        G.append(cv2.cvtColor(s, cv2.COLOR_BGR2GRAY))
    cap.release()
    return fps, G, C


def speeds(G):
    """v[t]＝コマ t-1→t で動いとる画素の速さの平均（px/コマ・480 幅）。area[t]＝動いとる割合。dup[t]＝同じコマ"""
    n = len(G)
    v = np.zeros(n); area = np.zeros(n); dup = np.zeros(n, bool); mags = [None] * n; dif = np.zeros(n)
    for t in range(1, n):
        d = np.abs(G[t].astype(np.int16) - G[t - 1].astype(np.int16)).mean()
        dif[t] = d
        dup[t] = d < 0.25
        if dup[t]:
            continue
        fl = cv2.calcOpticalFlowFarneback(G[t - 1], G[t], None, 0.5, 3, 15, 3, 5, 1.2, 0)
        m = np.hypot(fl[..., 0], fl[..., 1])
        mv = m > 0.5
        area[t] = mv.mean()
        if area[t] > 0.002:
            v[t] = float(m[mv].mean())
        mags[t] = m
    return v, area, dup, mags, dif


def spans(va, vb, gap=3, minlen=4):
    """手本かうちが動いとる区間（速さ>0.5 が続く所。gap コマ以内の切れ目はつなぐ）"""
    mv = (va > 0.5) | (vb > 0.5)
    out = []; s = None; last = -99
    for t, m in enumerate(mv):
        if m:
            if s is None or t - last > gap:
                if s is not None and last - s + 1 >= minlen:
                    out.append((s, last))
                s = t
            last = t
    if s is not None and last - s + 1 >= minlen:
        out.append((s, last))
    return out


def corr(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    if x.std() < 1e-6 or y.std() < 1e-6:
        return 1.0 if x.std() < 1e-6 and y.std() < 1e-6 else 0.0
    return float(np.corrcoef(x, y)[0, 1])


def giza(v):
    v = np.asarray(v, float)
    if len(v) < 4 or v.mean() < 1e-6:
        return 0.0
    return float(np.abs(np.diff(v, 2)).mean() / v.mean())


def ore(v, frac=0.1):
    v = np.asarray(v, float)
    a = np.diff(v)
    th = frac * max(v.max(), 1e-6)
    sg = np.sign(np.where(np.abs(a) < th, 0, a))
    sg = sg[sg != 0]
    return int((np.diff(sg) != 0).sum()) if len(sg) > 1 else 0


def judge(val, j, bigger_bad=True):
    g, y = j
    if bigger_bad:
        return "🟢" if val <= g else ("🟡" if val <= y else "🔴")
    return "🟢" if val >= g else ("🟡" if val >= y else "🔴")


def strip(CA, CB, va, vb, s, e, t0, path, n=8):
    """手本｜うち 8コマ（t0 から）＋ v(t) の線"""
    h, w = CA[0].shape[:2]
    tw = 240; th = int(round(h * tw / w))
    rows = []
    for C, col in ((CA, (0, 200, 255)), (CB, (255, 160, 0))):
        tiles = []
        for t in range(t0, min(t0 + n, len(C))):
            im = cv2.resize(C[t], (tw, th), interpolation=cv2.INTER_AREA).copy()
            cv2.putText(im, str(t), (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
            tiles.append(im)
        while len(tiles) < n:
            tiles.append(np.zeros((th, tw, 3), np.uint8))
        rows.append(np.hstack(tiles))
    # v(t) の線（区間全体）
    W = tw * n; H = 150
    g = np.full((H, W, 3), 30, np.uint8)
    L = e - s + 1; vmax = max(va[s:e + 1].max(), vb[s:e + 1].max(), 1e-6)
    for v, col in ((va, (0, 200, 255)), (vb, (255, 160, 0))):
        pts = [(int(8 + (t - s) / max(L - 1, 1) * (W - 16)), int(H - 10 - v[t] / vmax * (H - 30))) for t in range(s, e + 1)]
        cv2.polylines(g, [np.array(pts, np.int32)], False, col, 2, cv2.LINE_AA)
        for p in pts:
            cv2.circle(g, p, 2, col, -1, cv2.LINE_AA)
    x0 = int(8 + (t0 - s) / max(L - 1, 1) * (W - 16)); x1 = int(8 + (min(t0 + n - 1, e) - s) / max(L - 1, 1) * (W - 16))
    cv2.rectangle(g, (x0, 4), (x1, H - 4), (90, 90, 90), 1)
    cv2.putText(g, f"v(t) {s}-{e}  上の色=手本  下の色=うち  枠=上のコマ", (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1, cv2.LINE_AA)
    cv2.imwrite(path, np.vstack(rows + [g]), [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("ours")
    ap.add_argument("--out", default=None); ap.add_argument("--w", type=int, default=480); ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.ours)), "滑らか")
    os.makedirs(out, exist_ok=True)
    fa, GA, CA = read(a.ref, a.w); fb, GB, CB = read(a.ours, a.w)
    n = min(len(GA), len(GB))
    note = []
    if abs(fa - fb) > 0.01:
        note.append(f"🔴 fps が違う 手本 {fa:.2f} うち {fb:.2f}")
    if len(GA) != len(GB):
        note.append(f"コマ数 手本 {len(GA)} うち {len(GB)}（先頭 {n} コマで比べた）")
    GA, CA, GB, CB = GA[:n], CA[:n], GB[:n], CB[:n]
    va, aa, da, _, dfa = speeds(GA); vb, ab, db, _, dfb = speeds(GB)
    # 同じコマ（dup）：手本に無くてうちにある物＝止まり
    rows = []
    for (s, e) in spans(va, vb):
        A = va[s:e + 1]; B = vb[s:e + 1]
        ma = A.mean(); mb = B.mean()
        # 止まり＝手本がそのコマで 1px/コマ超 動いとるのに、うちが同じコマ（dup）か手本の 3 割未満
        # 2つ目の証人＝コマの差（黒い無地の上で光の流れが暴れる＝11/3 F。差も 3 割未満の時だけ止まりに数える）
        stop = [t for t in range(s, e + 1) if va[t] > 1.0 and (db[t] or (vb[t] < 0.3 * va[t] and dfb[t] < 0.3 * max(dfa[t], 1e-6)))]
        extra = [t for t in range(s, e + 1) if vb[t] > 1.0 and (da[t] or (va[t] < 0.3 * vb[t] and dfa[t] < 0.3 * max(dfb[t], 1e-6)))]
        c = corr(A, B); ga, gb = giza(A), giza(B); oa, ob = ore(A), ore(B)
        gr = gb / ga if ga > 1e-6 else (1.0 if gb < 1e-6 else 9.9)
        orr = ob / oa if oa > 0 else (1.0 if ob == 0 else float(ob))
        js = [judge(len(stop), J_STOP), judge(c, J_WAVE, False), judge(gr, J_GIZA), judge(orr, J_ORE)]
        worst = "🔴" if "🔴" in js else ("🟡" if "🟡" in js else "🟢")
        bad = len(stop) * 3 + len(extra) + max(0, (0.95 - c)) * 40 + max(0, gr - 1.3) * 10 + max(0, orr - 1.5) * 3
        rows.append(dict(s=s, e=e, len=e - s + 1, v_ref=round(float(A.max()), 2), v_ours=round(float(B.max()), 2), stop=stop, extra=extra,
                         wave=round(c, 3), giza_ref=round(ga, 3), giza_ours=round(gb, 3), giza_ratio=round(gr, 2),
                         ore_ref=oa, ore_ours=ob, ore_ratio=round(orr, 2), judge=worst, bad=round(bad, 2),
                         why=[w for w, j in zip(("止まり", "速さの波", "ギザ", "折れ"), js) if j != "🟢"]))
    rows.sort(key=lambda r: -r["bad"])
    tot_stop = sum(len(r["stop"]) for r in rows); tot_extra = sum(len(r["extra"]) for r in rows)
    reds = sum(r["judge"] == "🔴" for r in rows); yels = sum(r["judge"] == "🟡" for r in rows)
    dup_ref = int(da.sum()); dup_ours = int(db.sum())
    md = [f"# 滑らか（{os.path.basename(a.ref)} ｜ {os.path.basename(a.ours)}）", ""]
    md += [f"- {x}" for x in note]
    md += [f"- 動く区間 {len(rows)}・🔴 {reds}・🟡 {yels}・止まり（手本は動くのにうちが止まっとるコマ）合計 {tot_stop}・余計 {tot_extra}・同じコマ 手本 {dup_ref}／うち {dup_ours}",
           "- 目安＝止まり 0（🟡2）・速さの波 ≥0.95（🟡0.90）・ギザ比 ≤1.3（🟡1.6）・折れ比 ≤1.5（🟡2.0）", "",
           "| 区間（コマ） | 長さ | 速さの山 手本→うち | 止まり | 余計 | 速さの波 | ギザ 手本→うち（比） | 折れ 手本→うち | 判定 | 何が |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        st = ",".join(map(str, r["stop"][:8])) + ("…" if len(r["stop"]) > 8 else "")
        ex = ",".join(map(str, r["extra"][:6])) + ("…" if len(r["extra"]) > 6 else "")
        md.append(f"| {r['s']}-{r['e']} | {r['len']} | {r['v_ref']}→{r['v_ours']} | {len(r['stop'])} {st} | {len(r['extra'])} {ex} | {r['wave']} | {r['giza_ref']}→{r['giza_ours']}（{r['giza_ratio']}） | {r['ore_ref']}→{r['ore_ours']} | {r['judge']} | {'・'.join(r['why'])} |")
    # 悪い順に絵
    pics = []
    for r in rows[:a.top]:
        if r["judge"] == "🟢":
            continue
        t0 = r["stop"][0] - 3 if r["stop"] else (r["extra"][0] - 3 if r["extra"] else r["s"])
        t0 = max(r["s"], min(t0, r["e"] - 7))
        p = os.path.join(out, f"滑らか_{r['s']}-{r['e']}.jpg")
        strip(CA, CB, va, vb, r["s"], r["e"], t0, p)
        pics.append(p)
    md += ["", "絵（悪い順・手本｜うち 8コマ＋v(t)）＝" + "・".join(os.path.basename(p) for p in pics)]
    open(os.path.join(out, "滑らか.md"), "w").write("\n".join(md) + "\n")
    json.dump(dict(ref=a.ref, ours=a.ours, fps=[fa, fb], frames=[len(va), len(vb)], v_ref=[round(float(x), 3) for x in va], v_ours=[round(float(x), 3) for x in vb],
                   dup_ref=np.where(da)[0].tolist(), dup_ours=np.where(db)[0].tolist(), spans=rows,
                   summary=dict(spans=len(rows), red=reds, yellow=yels, stop=tot_stop, extra=tot_extra)),
              open(os.path.join(out, "滑らか.json"), "w"), ensure_ascii=False, indent=1)
    print("\n".join(md[:5 + min(len(rows), a.top + 2)]))
    print(f"→ {out}/滑らか.md")


if __name__ == "__main__":
    main()
