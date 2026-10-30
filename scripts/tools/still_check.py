"""一枚絵を無理やり動かしとるカットを見つける（10/28 r2 依頼者「画像を無理やり動かしてる部分が多い・動画を動画として動かす」）。
python3 still_check.py <作業> <うちの書き出し_noaudio.mp4> [--out shirabe/静止表.json]
- 考え方：一枚絵を拡大・移動・流れ（flow）で曲げた物は、前のコマを流れで曲げると次のコマがほぼ再現できる＝「新しい中身」N が出ん。
  本物の動画は瞬き・口・奥行き・照明・物の出入りで N が出る。手本とうちの N を比べる（motion_kind の L は flow で曲げた絵も動きと数えてまう）
- N＝隣のコマ同士で、DIS の流れで前のコマを曲げた残りの差（0〜255 の平均・320x180 白黒・字幕の帯と端 8px を外す・上位 10% の場所の平均＝局所の変化を拾う）
- 替わる瞬間（N≥35）は外して、手本がつながっとるコマの組だけで比べる。替わった数 sw も出す
- 判定：手本の N が 2.0 以上（本物の動き）なのに、うちの N が手本の 45% 未満＝🔴一枚絵／45〜70%＝🟡弱い。切り替えの前後 1 コマは外す
"""
import argparse, glob, json, os, sys
import cv2, numpy as np

W, H, FPS = 320, 180, 29.97
DIS = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
mask = np.ones((H, W), bool); mask[int(H * .416):int(H * .583)] = False; mask[:8] = mask[-8:] = False; mask[:, :8] = mask[:, -8:] = False


def frames(p):
    cap = cv2.VideoCapture(p); out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        out.append(cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (W, H), interpolation=cv2.INTER_AREA))
    return out


def newness(a, b):
    fl = DIS.calc(b, a, None)  # b の各点が a のどこから来たか
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    wa = cv2.remap(a, gx + fl[..., 0], gy + fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    d = np.abs(wa.astype(np.float32) - b.astype(np.float32))[mask]
    top = np.sort(d)[-max(1, d.size // 10):]
    return float(top.mean())


SW = 35.0  # これより上は「替わった」（写真の差し替え・切り替え）＝動きの物差しから外す


def cut_n(R, O, f0, f1):
    ks = [k for k in range(f0 + 1, f1 - 2) if k + 1 < min(len(R), len(O))]
    vr = [newness(R[k], R[k + 1]) for k in ks]; vo = [newness(O[k], O[k + 1]) for k in ks]
    keep = [i for i, v in enumerate(vr) if v < SW]
    md = lambda v: round(float(np.median(v)), 2) if v else None
    return md([vr[i] for i in keep]), md([vo[i] for i in keep]), sum(v >= SW for v in vr), sum(v >= SW for v in vo)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("ours"); ap.add_argument("--out", default="shirabe/静止表.json")
    a = ap.parse_args(); w = os.path.abspath(a.w)
    R = frames(glob.glob(f"{w}/ref/*.mp4")[0]); O = frames(a.ours)
    rows = []
    for l in open(f"{w}/eye/segs.txt"):
        c, t = l.strip().split(":"); s0, s1 = map(float, t.split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
        if f1 - f0 < 5: rows.append({"cut": c, "f0": f0, "f1": f1, "ok": "短い"}); continue
        nr, no, swr, swo = cut_n(R, O, f0, f1)
        ok = "✅"
        if nr is not None and no is not None and nr >= 2.0:
            r = no / nr
            ok = "🔴一枚絵" if r < 0.45 else ("🟡弱い" if r < 0.7 else "✅")
        rows.append({"cut": c, "f0": f0, "f1": f1, "N_ref": nr, "N_ours": no, "sw_ref": swr, "sw_ours": swo, "ok": ok})
        print(c, f0, f1, nr, no, swr, swo, ok, flush=True)
    json.dump(rows, open(os.path.join(w, a.out), "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(r["ok"] for r in rows))
