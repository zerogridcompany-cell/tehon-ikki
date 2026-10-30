#!/usr/bin/env python3
"""mane_check.py <手本.mp4> <うちの.mp4> [--out <フォルダ>] [--fps 10]
手本と「全く同じ物」を作る時の照合（2026-10-21・依頼者「探してきた物全部と全く同じ物を作れる状態に」）。
両方を手本の大きさ・10fps にそろえて、4つを数字で比べる。
 1. 絵の近さ：コマごとの SSIM（1秒ごとの平均・全体の平均）
 2. カットの時刻：場面の切れ目（scene 0.3）が手本と ±0.1秒で合う割合（手本のカットのうち合った数／うちの余計なカット）
 3. 動きの波：前のコマとの違い（毎コマ）の形がどれだけ同じか（相関）
 4. 色：1秒ごとの平均の色の差（Lab の ΔE）
線（未標定の初期値・手本を何本か写したら直す）：
 SSIM 平均 0.80 以上＝緑／0.65〜0.80＝黄／0.65 未満＝赤（別の動画同士でも 0.56 出た＝10/21 実測）
 カット 手本の80%以上が合う＝緑／60%以上＝黄／それ未満＝赤
 動きの波 相関 0.7 以上＝緑／0.5 以上＝黄
 色 ΔE 平均 8 以下＝緑／15 以下＝黄
 尺の差 0.2秒以内（越えたら赤）
出す物：<out>/mane_check.json・mane_check.md（1秒ごとの表＝どこが違うか）・yoko.mp4（左手本・右うち・手本の音）・sa_NN.jpg（一番違う3秒の並べ絵）
赤があれば終了コード 2。
"""
import argparse, json, os, re, subprocess, sys
import numpy as np


def sh(c, text=True):
    return subprocess.run(c, capture_output=True, text=text)


def dur(p):
    # 絵の長さで測る（音だけ長いファイルで尺がずれん様に）
    v = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", p]).stdout.strip()
    try:
        return float(v)
    except ValueError:
        return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).stdout)


def size(p):
    w, h = sh(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", p]).stdout.strip().split(",")[:2]
    return int(w), int(h)


def frames(p, W, H, fps, n):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,format=rgb24",
                          "-frames:v", str(n), "-f", "rawvideo", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8)
    k = len(a) // (W * H * 3)
    return a[:k * W * H * 3].reshape(k, H, W, 3).astype(np.float32)


def ssim(a, b):
    # 明るさだけ・8x8 の窓の平均で近似（ffmpeg ssim と同じ考え・速さ優先）
    ya = a @ np.array([0.299, 0.587, 0.114], np.float32); yb = b @ np.array([0.299, 0.587, 0.114], np.float32)
    H, W = ya.shape; H8, W8 = H // 8 * 8, W // 8 * 8
    A = ya[:H8, :W8].reshape(H8 // 8, 8, W8 // 8, 8); B = yb[:H8, :W8].reshape(H8 // 8, 8, W8 // 8, 8)
    ma, mb = A.mean((1, 3)), B.mean((1, 3))
    va, vb = A.var((1, 3)), B.var((1, 3)); cv = ((A - ma[:, None, :, None]) * (B - mb[:, None, :, None])).mean((1, 3))
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    return float((((2 * ma * mb + c1) * (2 * cv + c2)) / ((ma ** 2 + mb ** 2 + c1) * (va + vb + c2))).mean())


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    x, y, z = (M @ c) / np.array([0.95047, 1.0, 1.08883])
    f = lambda t: np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)
    return np.array([116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))])


def rate(p):
    o = sh(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", p]).stdout.strip()
    a, b = o.split(",")[0].split("/"); return float(a) / float(b)


def komakaku(p, W, H, n_sec):
    """🆕10/22 細かい動き：元の fps のまま。動いたコマの割合（実質fps）と、少しだけ動いたマスの割合（手・振動）"""
    raw = sh(["ffmpeg", "-v", "error", "-threads", "2", "-i", p, "-t", str(n_sec), "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"], text=False).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
    d = np.abs(np.diff(f, axis=0)); gh, gw = H // 9, W // 16
    c = d[:, :gh * 9, :gw * 16].reshape(len(d), 9, gh, 16, gw).mean(axis=(2, 4))
    return float((d.mean(axis=(1, 2)) > 0.3).mean()) * rate(p), float(((c > 0.8) & (c < 12)).mean())


def cuts(p):
    e = sh(["ffmpeg", "-hide_banner", "-i", p, "-vf", "select='gt(scene,0.3)',metadata=print", "-an", "-f", "null", "-"]).stderr
    return [float(x) for x in re.findall(r"pts_time:([\d.]+)", e)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("ours"); ap.add_argument("--out"); ap.add_argument("--fps", type=float, default=10)
    a = ap.parse_args()
    ref, ours = os.path.abspath(a.ref), os.path.abspath(a.ours)
    out = os.path.abspath(a.out or os.path.join(os.path.dirname(ours), "mane_check")); os.makedirs(out, exist_ok=True)
    dr, do = dur(ref), dur(ours)
    rw, rh = size(ref); W = 320; H = int(round(W * rh / rw / 2)) * 2
    n = int(min(dr, do) * a.fps)
    R, O = frames(ref, W, H, a.fps, n), frames(ours, W, H, a.fps, n)
    n = min(len(R), len(O)); R, O = R[:n], O[:n]
    ss = np.array([ssim(R[i], O[i]) for i in range(n)])
    mr = np.r_[0, np.abs(np.diff(R, axis=0)).mean((1, 2, 3))]; mo = np.r_[0, np.abs(np.diff(O, axis=0)).mean((1, 2, 3))]
    corr = float(np.corrcoef(mr, mo)[0, 1]) if mr.std() > 0 and mo.std() > 0 else 0.0
    fps = int(a.fps); secs = n // fps
    rows = []
    for s in range(secs):
        sl = slice(s * fps, (s + 1) * fps)
        de = float(np.linalg.norm(lab(R[sl].reshape(-1, 3).mean(0)) - lab(O[sl].reshape(-1, 3).mean(0))))
        rows.append({"秒": s, "SSIM": round(float(ss[sl].mean()), 3), "色ΔE": round(de, 1), "動き手本": round(float(mr[sl].mean()), 2), "動きうち": round(float(mo[sl].mean()), 2)})
    kr, ko = komakaku(ref, W, H, min(dr, do)), komakaku(ours, W, H, min(dr, do))
    fr_ratio, sm_ratio = ko[0] / (kr[0] + 1e-9), ko[1] / (kr[1] + 1e-9)
    # 🆕10/23 絵が動いとるだけの秒（katachi.py：手本は形が動くのに、うちは半分未満の秒）
    kt = sh(["python3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "katachi.py"), ref, ours]).stdout
    m = re.search(r"だけの秒.*?：(\d+)/(\d+)秒(.*)", kt); kb, kn, ks = (int(m.group(1)), int(m.group(2)), m.group(3).strip()) if m else (0, 0, "")
    kr_ = kb / kn if kn else 0.0
    cr, co = cuts(ref), cuts(ours)
    hit = sum(1 for c in cr if any(abs(c - d) <= 0.1 for d in co)); extra = sum(1 for d in co if not any(abs(c - d) <= 0.1 for c in cr))
    rec = hit / len(cr) if cr else 1.0
    S = float(ss.mean()); DE = float(np.mean([r["色ΔE"] for r in rows])) if rows else 0
    L = lambda v, g, y, hi=True: ("緑" if (v >= g if hi else v <= g) else "黄" if (v >= y if hi else v <= y) else "赤")
    res = {"手本": ref, "うち": ours, "尺": [round(dr, 2), round(do, 2)],
           "判定": {"絵の近さ SSIM": [round(S, 3), L(S, 0.80, 0.65)], "カット": [f"{hit}/{len(cr)} 合う・余計 {extra}", L(rec, 0.8, 0.6)],
                   "動きの波 相関": [round(corr, 3), L(corr, 0.7, 0.5)], "色 ΔE": [round(DE, 1), L(DE, 8, 15, False)],
                   "細かい動き 実質fps": [f"うち {ko[0]:.0f} / 手本 {kr[0]:.0f}（{fr_ratio:.2f}）", L(fr_ratio, 0.85, 0.6)],
                   "細かい動き 小さい動きのマス": [f"うち {ko[1]*100:.1f}% / 手本 {kr[1]*100:.1f}%（{sm_ratio:.2f}）", L(sm_ratio, 0.8, 0.6)],
                   "絵が動いとるだけの秒": [f"{kb}/{kn}秒 {ks[:120]}", L(kr_, 0.1, 0.25, False)],
                   "尺の差": [round(abs(dr - do), 2), "緑" if abs(dr - do) <= 0.2 else "赤"]},
           "カット手本": cr, "カットうち": co, "秒ごと": rows}
    json.dump(res, open(os.path.join(out, "mane_check.json"), "w"), ensure_ascii=False, indent=1)
    worst = sorted(rows, key=lambda r: r["SSIM"])[:3]
    md = [f"# 写しの照合 {os.path.basename(ours)} ← {os.path.basename(ref)}", "", "| 項目 | 値 | 判定 |", "|---|---|---|"]
    md += [f"| {k} | {v[0]} | {v[1]} |" for k, v in res["判定"].items()]
    md += ["", "## 一番違う3秒（sa_*.jpg に並べ絵）"] + [f"- {r['秒']}秒：SSIM {r['SSIM']}・色ΔE {r['色ΔE']}" for r in worst]
    md += ["", "## 1秒ごと", "| 秒 | SSIM | 色ΔE | 動き手本 | 動きうち |", "|---|---|---|---|---|"] + [f"| {r['秒']} | {r['SSIM']} | {r['色ΔE']} | {r['動き手本']} | {r['動きうち']} |" for r in rows]
    open(os.path.join(out, "mane_check.md"), "w").write("\n".join(md) + "\n")
    for k, r in enumerate(worst):
        i = r["秒"] * fps + fps // 2
        from PIL import Image
        Image.fromarray(np.concatenate([R[i], O[i]], 1).astype(np.uint8)).save(os.path.join(out, f"sa_{k + 1}_{r['秒']}s.jpg"))
    sh(["ffmpeg", "-v", "error", "-y", "-i", ref, "-i", ours, "-filter_complex",
        f"[0:v]scale=-2:540,setsar=1,fps=30[a];[1:v]scale={W * 540 // H // 2 * 2}:540:force_original_aspect_ratio=decrease,pad={W * 540 // H // 2 * 2}:540:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[b];[a][b]hstack[v]",
        "-map", "[v]", "-map", "0:a?", "-t", str(min(dr, do)), "-c:v", "libx264", "-crf", "22", "-c:a", "aac", os.path.join(out, "yoko.mp4")])
    for k, v in res["判定"].items():
        print({"緑": "🟢", "黄": "🟡", "赤": "🔴"}[v[1]], k, v[0])
    red = [k for k, v in res["判定"].items() if v[1] == "赤"]
    print(f"赤 {len(red)} → {out}/mane_check.md")
    sys.exit(2 if red else 0)


if __name__ == "__main__":
    main()
