"""古い映像のカットに「フィルムの窓」（左右の暗い帯・左の縁のギザギザの水色の光・右の縁の橙の光）を足す（10/27 r2：59・126・127・128）。
python3 gate_fx.py <作業> <カット番号> [--out tmp/gate/<番号>.mp4] [--write] [--jag 6]
- 測る：手本のそのカットの列ごとの平均の色（左 0〜260・右 1020〜1280）＝帯の色と光の形（1次元の表。手本のコマをそのまま写さん）
- 縁：左＝水色の山の位置＋12px まで帯・そこから 30px でうちの絵へ／右＝暗い所が始まる列から帯・その手前 60px で橙の光を重ねる
- ギザギザ：縁の位置を行ごとになめらかな乱数で ±jag px ずらす（コマごとに少しずつ変える）
- 色は shot_look の g・o を逆にかけてカットの段の色に戻す（後で Remotion が同じ g・o をかける）
- --write＝cuts/<番号>.mp4 を置き換え（前の物は .bak_gate）
"""
import argparse, glob, json, os, shutil, subprocess
import cv2, numpy as np
W, H = 1280, 720


def rd(p, a=None, b=None):
    vf = ["-vf", f"select=between(n\\,{a}\\,{b - 1})", "-vsync", "0"] if a is not None else []
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p] + vf + ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("--out"); ap.add_argument("--write", action="store_true")
    ap.add_argument("--jag", type=float, default=3); ap.add_argument("--src", help="既定 cuts/<番号>.mp4"); ap.add_argument("--side", default="both", help="both|left|right")
    g = ap.parse_args()
    s = [s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"] if str(s["i"]) == str(g.i)][0]
    f0 = int(round(s["t0"] * 29.97)); src = f"{g.w}/cuts/{g.i}.mp4"
    F = rd(g.src or src); R = rd(sorted(glob.glob(f"{g.w}/ref/*.mp4"))[0], f0, f0 + len(F)); n = min(len(F), len(R))
    look = json.load(open(f"{g.w}/proj/src/shot_look.json")).get(str(g.i)) or {}
    gg = np.array(look.get("g", [1, 1, 1]), np.float32)[::-1]; oo = np.array(look.get("o", [0, 0, 0]), np.float32)[::-1]  # rgb→bgr
    T = R[:n].astype(np.float32).mean(axis=(0, 1))          # 列ごとの平均の色（W,3）
    P = np.clip(((T / 255 - oo) / gg) * 255, 0, 255)         # カットの段の色へ戻す
    lum = T.mean(1); cy = (T[:, 0] + T[:, 1]) / 2 - T[:, 2]
    kl = 80 + int(np.argmax(cy[80:260])); el = kl + 12           # 左の縁
    dark = np.where(lum[900:] < 30)[0]; er = 900 + int(dark[0]) if len(dark) else W  # 右の暗い帯の始まり
    orange = float((T[er - 40:er, 2] - T[er - 40:er, 0]).mean()) if er < W else 0
    rr = 60 if orange > 15 else 8
    print(f"右の光 {orange:.0f}→幅 {rr}")
    print(f"左の縁 {el}（水色の山 {kl}・{cy[kl]:.0f}）右の帯 {er}")
    rng = np.random.default_rng(int(g.i))
    base_l = cv2.GaussianBlur(rng.normal(0, 1, (H, 1)).astype(np.float32), (0, 0), 3)[:, 0]
    base_r = cv2.GaussianBlur(rng.normal(0, 1, (H, 1)).astype(np.float32), (0, 0), 10)[:, 0]
    xs = np.arange(W, dtype=np.float32)[None, :]
    out = []
    for j, f in enumerate(F):
        jl = (0.7 * base_l + 0.3 * cv2.GaussianBlur(rng.normal(0, 1, (H, 1)).astype(np.float32), (0, 0), 6)[:, 0]); jl = jl / (jl.std() + 1e-6) * g.jag
        jr = base_r / (base_r.std() + 1e-6) * g.jag * 0.5
        eL = el + jl[:, None]; eR = er + jr[:, None]
        aL = np.clip((eL + 30 - xs) / 30, 0, 1)                   # 左：縁まで帯・30px でうちへ
        aR = np.clip((xs - (eR - rr)) / rr, 0, 1)                  # 右：橙の光がある時は 60px 手前から・無い時は 8px
        if g.side == "left": aR = aR * 0
        if g.side == "right": aL = aL * 0
        a = np.maximum(aL, aR)[..., None]
        # 帯の色＝列の色を行ごとのずれに合わせて引く（ギザギザの水色が縁と一緒に動く）
        idxL = np.clip((xs - jl[:, None]).astype(int), 0, W - 1); idxR = np.clip((xs - jr[:, None]).astype(int), 0, W - 1)
        gate = np.where((xs < W / 2)[..., None], P[idxL], P[idxR])
        o = f.astype(np.float32) * (1 - a) + gate * a
        out.append(np.clip(o, 0, 255).astype(np.uint8))
    o = g.out or f"{g.w}/tmp/gate/{g.i}.mp4"; os.makedirs(os.path.dirname(o), exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", o], stdin=subprocess.PIPE)
    p.stdin.write(np.array(out).tobytes()); p.stdin.close(); p.wait(); print("書いた", o)
    if g.write:
        if not os.path.exists(src + ".bak_gate"): shutil.copy(src, src + ".bak_gate")
        shutil.copy(o, src); print("置き換えた", src)


if __name__ == "__main__":
    main()
