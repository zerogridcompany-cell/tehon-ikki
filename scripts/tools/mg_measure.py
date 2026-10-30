"""mg_measure.py  動く MG の部品（assets/proj/src/mg/）に渡す値を、手本のコマから測る（51 の note_box・area_seq・blob_rects・boil・d30 を1本に・汎用版・2026-10-25）。
使い方：python3 mg_measure.py <作業|手本.mp4|うち.mp4> <命令> <f0> <f1> [オプション]
  🔴 コマは select n で読む（-ss (f−0.5)/fps は1コマ後ろを読む＝51 の元の道具の誤り）。出す px は全部「元の動画の画面の px」
命令：
  box     地の色から遠い（--far r,g,b・既定 236,232,230）か、ある色に近い（--color r,g,b）一番大きい塊の外枠を毎コマ → 1行「コマ x0 y0 x1 y1 面積」
          → Swap の箱・CrumpleBall の中心と幅・Chat の吹き出しの箱とぽんの段・Notif の箱が出るコマ
  area    見えとる割合（--thr Y のしきい・既定 40。--far r,g,b なら地の色から遠い画素）と x の 5〜95% の幅 → 1行「コマ 割合 幅」
          → Rain の ks（広がり k と大きさ s）・War の e（広がり）を「うちも同じに測って1歩ずつ寄せる」
  rects   明るい塊（--far があれば地から遠い塊）ごとの回った長方形 → json {"<コマ>":[[cx,cy,w,h,deg,lum,area]…]}（--out 必須・--min 塊の最小の面積 300）
          → RainRects の rects にそのまま
  steps   前のコマとの差（--box x0,y0,x1,y1 の中だけ・320 幅の灰の平均の差）→ 1行「コマ 差 ●(跳び)/・(止め 0.05 未満)」と「跳びのコマの並び・間のコマの数」
          → Swap の表のコマ・語の出るコマ・打ち（2コマ／3コマ）・Static の holdEvery
  boil    四隅（--corners 0.06＝画面の割合）の前のコマとの差が小さく替わるコマ（0.35〜8）→ json {"<コマ>":段 0..3}（--out）と「間のコマ 中央値」
          → Boil の table・every。🔴 字や物が四隅に来る範囲は外す
  noise   --box の中の粒の大きさ（自己相関の半値幅 px）・濃淡の幅（標準偏差）・平均の色・毎コマの差（0 のコマ＝止め）→ Static の freq・slope・icpt・holdEvery
  corners 2つのコマ（f0 と f1）の四隅の SSIM＝同じ紙かどうか（0.95 以上＝1枚の紙＝Paper を1枚だけ敷く）
入れる物：手本（作業なら <作業>/ref/*.mp4）・コマの範囲（両端込み）
効いた数字（51）：面積から逆算した表で War 43秒 0.591→0.680・Rain の切り替えが合った・塊の四角で札の雨 0.31→0.50・しわの強さ ΔE 1.0→0.9・3コマごとの差し替えを 30fps で測り直して 0.585→0.613
採る条件：測るだけ。測った値を mg.json か public/mg/*.json に書き、seg_ssim.py でその範囲を前後比べて上がった時だけ残す
"""
import argparse, json, sys
import numpy as np
import cv2
from tk_common import ref_path, probe, gray, bgr


def rgb_of(s):
    return np.array([float(v) for v in s.split(",")], np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("cmd"); ap.add_argument("f0", type=int); ap.add_argument("f1", type=int)
    ap.add_argument("--far"); ap.add_argument("--color"); ap.add_argument("--tol", type=float, default=40)
    ap.add_argument("--thr", type=float, default=40); ap.add_argument("--min", type=int, default=300)
    ap.add_argument("--box"); ap.add_argument("--out"); ap.add_argument("--corners", type=float, default=0.06)
    a = ap.parse_args()
    p = ref_path(a.src); W, H, fps, _ = probe(p); n = a.f1 - a.f0 + 1
    box = [int(v) for v in a.box.split(",")] if a.box else [0, 0, W, H]

    if a.cmd in ("box", "rects", "area"):
        F = bgr(p, a.f0, n, W, H)
        res = {}
        for i, im in enumerate(F):
            f = a.f0 + i; rgb = im[:, :, ::-1].astype(np.float32)
            if a.color:
                m = np.sqrt(((rgb - rgb_of(a.color)) ** 2).sum(2)) < a.tol
            elif a.far:
                m = np.sqrt(((rgb - rgb_of(a.far)) ** 2).sum(2)) > a.tol * 0.7
            else:
                m = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) > a.thr
            m = m.astype(np.uint8)
            if a.cmd == "area":
                xs = np.nonzero(m)[1]
                wd = float(np.percentile(xs, 95) - np.percentile(xs, 5)) if m.sum() > 20 else 0.0
                print(f"{f} {m.mean():.4f} {wd:.0f}"); continue
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            k, lab, st, _ = cv2.connectedComponentsWithStats(m)
            if a.cmd == "box":
                if k <= 1: print(f"{f} -"); continue
                j = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])); x, y, w, h, ar = st[j]
                print(f"{f} {x} {y} {x + w} {y + h} {ar}"); continue
            g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY); out = []
            for j in range(1, k):
                if st[j, cv2.CC_STAT_AREA] < a.min: continue
                ys, xs = np.nonzero(lab == j)
                (cx, cy), (rw, rh), deg = cv2.minAreaRect(np.c_[xs, ys].astype(np.float32))
                if rw < rh: rw, rh, deg = rh, rw, deg + 90
                out.append([round(cx, 1), round(cy, 1), round(rw, 1), round(rh, 1), round(deg, 1), round(float(g[ys, xs].mean()), 1), int(st[j, cv2.CC_STAT_AREA])])
            res[str(f)] = out; print(f, len(out), "塊")
        if a.cmd == "rects":
            if not a.out: sys.exit("--out が要る")
            json.dump(res, open(a.out, "w")); print("書いた", a.out)
        return

    if a.cmd == "steps":
        x0, y0, x1, y1 = box; s = 320 / W
        G = gray(p, a.f0, n, 320, round(H * s)).astype(np.float32)[:, round(y0 * s):max(round(y0 * s) + 1, round(y1 * s)), round(x0 * s):max(round(x0 * s) + 1, round(x1 * s))]
        d = np.r_[0, np.abs(np.diff(G, axis=0)).mean((1, 2))]
        thr = max(0.5, float(np.median(d[1:])) * 3) if len(d) > 2 else 0.5
        jumps = []
        for i, v in enumerate(d):
            mark = "●" if (i and v > thr) else ("・" if i and v < 0.05 else "")
            if mark == "●": jumps.append(a.f0 + i)
            print(f"{a.f0 + i} {v:6.2f} {mark}")
        print("跳び（しきい", round(thr, 2), "）：", jumps); print("間のコマ：", [int(v) for v in np.diff(jumps)])
        return

    if a.cmd == "boil":
        G = gray(p, a.f0, n, 480, round(480 * H / W)).astype(np.int16); h, w = G.shape[1:]
        c = a.corners; cy, cx = max(4, int(h * c * 1.8)), max(4, int(w * c * 1.8))
        cs = [(slice(5, 5 + cy), slice(5, 5 + cx)), (slice(5, 5 + cy), slice(w - 5 - cx, w - 5)), (slice(h - 5 - cy, h - 5), slice(5, 5 + cx)), (slice(h - 5 - cy, h - 5), slice(w - 5 - cx, w - 5))]
        stt = 0; out = {str(a.f0): 0}; ch = []
        for i in range(1, len(G)):
            dd = sorted(float(np.abs(G[i][q] - G[i - 1][q]).mean()) for q in cs)
            if 0.35 < dd[1] < 8 and dd[2] < 12: stt = (stt + 1) % 4; ch.append(a.f0 + i)
            out[str(a.f0 + i)] = stt
        gaps = np.diff(ch) if len(ch) > 1 else np.array([0])
        print("替わり", len(ch), "間のコマ 中央値", float(np.median(gaps)), "分布", np.bincount(np.minimum(gaps, 8)).tolist())
        if a.out: json.dump(out, open(a.out, "w")); print("書いた", a.out)
        return

    if a.cmd == "noise":
        x0, y0, x1, y1 = box
        F = bgr(p, a.f0, n, W, H)[:, y0:y1, x0:x1].astype(np.float32)
        g = F.mean(3); res = []
        for im in g[: min(len(g), 10)]:
            z = im - im.mean(); ac = np.fft.ifft2(np.abs(np.fft.fft2(z)) ** 2).real; ac /= ac[0, 0]
            row = ac[0, : min(40, ac.shape[1])]; hw = int(np.argmax(row < 0.5)) if (row < 0.5).any() else len(row)
            res.append(hw)
        d = np.abs(np.diff(g, axis=0)).mean((1, 2)) if len(g) > 1 else np.array([0])
        mean = F.mean((0, 1, 2))[::-1]
        print(f"粒（自己相関の半値幅）{np.median(res):.1f}px・濃淡の幅（標準偏差）{g.std((1, 2)).mean():.1f}・平均の色 RGB {mean.round(0).tolist()}")
        print("毎コマの差", d.round(1).tolist()); z = [a.f0 + 1 + i for i, v in enumerate(d) if v < 0.5]
        print("止め（差 0.5 未満）のコマ", z, "間", [int(v) for v in np.diff(z)])
        return

    if a.cmd == "corners":
        A, B = bgr(p, a.f0, 1, W, H)[0], bgr(p, a.f1, 1, W, H)[0]
        cw, chh = int(W * 0.12), int(H * 0.12); out = []
        for (yy, xx) in [(0, 0), (0, W - cw), (H - chh, 0), (H - chh, W - cw)]:
            ga = cv2.cvtColor(A[yy:yy + chh, xx:xx + cw], cv2.COLOR_BGR2GRAY).astype(np.float64); gb = cv2.cvtColor(B[yy:yy + chh, xx:xx + cw], cv2.COLOR_BGR2GRAY).astype(np.float64)
            C1, C2 = 6.5025, 58.5225; mu1, mu2 = cv2.GaussianBlur(ga, (11, 11), 1.5), cv2.GaussianBlur(gb, (11, 11), 1.5)
            s1 = cv2.GaussianBlur(ga * ga, (11, 11), 1.5) - mu1 ** 2; s2 = cv2.GaussianBlur(gb * gb, (11, 11), 1.5) - mu2 ** 2; s12 = cv2.GaussianBlur(ga * gb, (11, 11), 1.5) - mu1 * mu2
            out.append(float((((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 ** 2 + mu2 ** 2 + C1) * (s1 + s2 + C2))).mean()))
        print("四隅の SSIM", [round(v, 3) for v in out], "→", "1枚の紙" if min(out) >= 0.95 else "別の紙か物が載っとる")
        return
    sys.exit("命令は box / area / rects / steps / boil / noise / corners")


if __name__ == "__main__":
    main()
