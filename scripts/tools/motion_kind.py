"""カットごとに「動きの種類」を手本とうちで測って比べる（静止画を動かしてごまかしとるカットを数字で見つける）。
python3 motion_kind.py <作業> <うちの書き出し.mp4> [--out shirabe/動き表.json] [--cuts]
- 隣のコマ同士で、全体の動き（拡大・移動＝カメラ／Ken Burns）を当ててから引いた残り＝「中の動き」L を出す
  - 本物の動画（人が話す・物が動く・奥行き）＝L が大きい／静止画を動かしただけ＝L がほぼ 0
- 全体の動きの量 G（1コマあたりの px）と、コマの変わる量 D も出す
- 判定（カットごと）：
  - 偽の動き🔴＝手本の L が大きい（≥ L_REAL）のに、うちの L が手本の 40% 未満
  - 余計な動き🔴＝手本は止まっとる（G<0.15 かつ L<L_REAL）のに、うちは G が 0.5 以上
  - 動きの量違い🟡＝両方カメラが動くが、G の比が 0.7〜1.4 を外れる
- 字幕の帯（高さ 41.6〜58.3%）は外す。切り替えの前後 2 コマは外す
- --cuts＝書き出しの代わりに cuts/<番号>.mp4 をそのまま測る（書き出し前の見込み）
"""
import argparse, glob, json, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo

W, H, FPS = 320, 180, 29.97   # __main__ で geo の SW・SH・FPS に替わる（10/30）
FULLW = 1280                  # 手本の横の画素（G を手本の px に直す）
L_REAL = 1.2  # 中の動き（0〜255 の平均の差）。圧縮の揺れは 0.3〜0.6


def frames(p, n=None):
    cap = cv2.VideoCapture(p); out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        out.append(cv2.cvtColor(cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY))
        if n and len(out) >= n: break
    return np.array(out)


def _mask():
    m = np.ones((H, W), np.uint8); m[int(H * .416):int(H * .583)] = 0; return m


MASK = _mask()


def pair(a, b):
    """a→b の全体の動き（相似）と、引いた残り"""
    ab, bb = cv2.GaussianBlur(a, (0, 0), 1.2), cv2.GaussianBlur(b, (0, 0), 1.2)
    D = float(np.mean(cv2.absdiff(ab, bb)[MASK > 0]))
    p0 = cv2.goodFeaturesToTrack(ab, 200, 0.01, 6, mask=MASK)
    G, L = 0.0, D
    if p0 is not None and len(p0) >= 8:
        p1, st, _ = cv2.calcOpticalFlowPyrLK(ab, bb, p0, None, winSize=(21, 21), maxLevel=3)
        g = st.ravel() == 1
        if g.sum() >= 8:
            M, inl = cv2.estimateAffinePartial2D(p0[g], p1[g], method=cv2.RANSAC, ransacReprojThreshold=1.5)
            if M is not None:
                c = np.array([W / 2, H / 2]); mv = M[:, :2] @ c + M[:, 2] - c
                s = float(np.hypot(M[0, 0], M[1, 0]))
                G = float(np.hypot(*mv) + abs(s - 1) * W / 2) * (FULLW / W)  # 手本の幅の px に直す（r2 は 1280）
                wa = cv2.warpAffine(ab, M, (W, H), borderMode=cv2.BORDER_REFLECT)
                vm = cv2.warpAffine(MASK, M, (W, H), flags=cv2.INTER_NEAREST)
                m = (MASK > 0) & (vm > 0)
                if m.sum() > 1000: L = float(np.mean(cv2.absdiff(wa, bb)[m]))
    return G, L, D


def measure(F, f0, f1):
    r = [pair(F[i], F[i + 1]) for i in range(f0 + 1, f1 - 2) if i + 1 < len(F)]
    if not r: return None
    a = np.array(r)
    return dict(G=round(float(np.median(a[:, 0])), 2), L=round(float(np.median(a[:, 1])), 2), D=round(float(np.median(a[:, 2])), 2), n=len(r), d=[round(float(x), 2) for x in a[:, 2]], l=[round(float(x), 2) for x in a[:, 1]])


def holds(t, o):
    """止まりコマ＝手本は動いとる（D>0.6）のに、うちは前のコマと同じ（D<0.15）"""
    return sum(1 for x, y in zip(t["d"], o["d"]) if x > 0.6 and y < 0.15)


def switches(t, o):
    """切り替え（写真が替わる・フラッシュ）＝全体の動きを引いた残りが 20 以上。手本とうちで位置が違う数"""
    a = {i for i, x in enumerate(t["l"]) if x >= 20}; b = {i for i, x in enumerate(o["l"]) if x >= 20}
    return len(a ^ b), sorted(a), sorted(b)


def judge(t, o):
    if not t or not o: return "測れん", ""
    nsw, sa, sb = switches(t, o)
    if nsw >= 1 and (len(sa) + len(sb)) >= 1:
        return "🔴替わる位置", f"手本 {sa} / うち {sb}（カットの中のコマ番号−1）"
    h = holds(t, o)
    if h >= 2:
        return "🔴止まりコマ", f"手本は動くのに、うちが前と同じコマ {h}/{len(t['d'])}"
    if t["L"] >= L_REAL and o["L"] < t["L"] * 0.4:
        return "🔴偽の動き", f"手本の中の動き {t['L']} / うち {o['L']}"
    if t["G"] < 0.15 and t["L"] < L_REAL and o["G"] >= 0.5:
        return "🔴余計な動き", f"手本は止まり / うち {o['G']}px/コマ"
    if t["G"] >= 0.5 and o["G"] >= 0.1 and not (0.7 <= o["G"] / t["G"] <= 1.4):
        return "🟡動きの量", f"手本 {t['G']} / うち {o['G']} px/コマ"
    if t["G"] >= 0.5 and o["G"] < 0.1:
        return "🔴止まっとる", f"手本はカメラ {t['G']}px/コマ / うち止まり"
    return "✅", ""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out_mp4", nargs="?")
    ap.add_argument("--out", default="shirabe/動き表.json"); ap.add_argument("--cuts", action="store_true")
    ap.add_argument("--ids", default=""); ap.add_argument("--try", dest="tryf", default="", help="--cuts の時、cuts/<番号>.mp4 の代わりに測るファイル（1カットだけ）")
    a = ap.parse_args(); w = os.path.abspath(a.w)
    GG = geo(w); W, H, FPS, FULLW = GG["SW"], GG["SH"], GG["FPS"], GG["W"]; MASK = _mask()
    segs = []
    for l in open(f"{w}/eye/segs.txt"):
        if ":" in l:
            k, v = l.split(":"); s0, s1 = map(float, v.split("-")); segs.append((int(k), round(s0 * FPS), round(s1 * FPS)))
    ids = set(map(int, a.ids.split(","))) if a.ids else None
    R = frames(glob.glob(f"{w}/ref/*.mp4")[0])
    V = None if a.cuts else frames(os.path.join(w, a.out_mp4))
    rows = []
    for k, f0, f1 in segs:
        if ids and k not in ids: continue
        if f1 - f0 < 5: rows.append(dict(cut=k, ok="短い")); continue
        t = measure(R, f0, f1)
        if a.cuts:
            cp = os.path.abspath(a.tryf) if a.tryf else f"{w}/cuts/{k}.mp4"
            o = measure(frames(cp, f1 - f0 + 2), 0, f1 - f0) if os.path.exists(cp) else None
        else:
            o = measure(V, f0, f1)
        ok, why = judge(t, o)
        rows.append(dict(cut=k, t=round(f0 / FPS, 2), frames=f1 - f0, ref=t, ours=o, ok=ok, why=why))
        print(k, ok, why, flush=True)
    op = os.path.join(w, a.out)
    if ids and os.path.exists(op):
        old = {r["cut"]: r for r in json.load(open(op))}; old.update({r["cut"]: r for r in rows}); rows = [old[c] for c in sorted(old)]
    json.dump(rows, open(op, "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(r["ok"] for r in rows))
