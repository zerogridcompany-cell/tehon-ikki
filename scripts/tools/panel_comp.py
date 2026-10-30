"""寄せ集め（何枚もの枠に別々の映像が入る）カットを、枠ごとに元の映像で作って1枚に重ねる。

python3 panel_comp.py <作業フォルダ> <カット番号> <panels.json> [--base cuts/<番号>.mp4]
panels.json＝[{"name":"top_mid","rect":[x,y,w,h],"file":"src/long/<id>.mp4","start":<元の秒・だいたい>}, …]
1. 手本を枠の大きさで切り抜いた動画を tmp/panel/<番号>_<name>/ref/ に作る（eye/out.json もそのカットだけ）
2. 元の start の前後3秒を切り出し、match.py で秒と重ね方を当てる
3. fit_cut.py で枠の大きさの動画にする（追う／追わんの SSIM が高い方）
4. 土台（--base・既定は今の cuts/<番号>.mp4）の上に、枠ごとに重ねて cuts/<番号>.mp4 に書く（前の物は .bak_panel に控え）
"""
import argparse, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        print("  失敗:", " ".join(map(str, a))[:160], r.stderr[-300:], flush=True)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("panels"); ap.add_argument("--base")
    g = ap.parse_args()
    w = os.path.abspath(g.w)
    ref = [f for f in os.listdir(f"{w}/ref") if f.endswith(".mp4")][0]
    ref = f"{w}/ref/{ref}"
    shot = [s for s in json.load(open(f"{w}/eye/out.json"))["shots"] if str(s["i"]) == g.i][0]
    t0, t1 = float(shot["t0"]), float(shot["t1"])
    base = g.base or f"{w}/cuts/{g.i}.mp4"
    done = []
    for p in json.load(open(g.panels)):
        x, y, pw, ph = p["rect"]
        pw -= pw % 2; ph -= ph % 2
        d = f"{w}/tmp/panel/{g.i}_{p['name']}"
        for sub in ("ref", "eye", "src", "out"):
            os.makedirs(f"{d}/{sub}", exist_ok=True)
        # 1. 手本を枠で切り抜く（カットの前後1秒だけ・秒はそのまま残す＝頭に黒を足さず -ss を付けん）
        rc = f"{d}/ref/ref.mp4"
        if not os.path.exists(rc):
            run(["ffmpeg", "-v", "error", "-y", "-i", ref, "-t", f"{t1 + 1:.3f}", "-vf", f"crop={pw}:{ph}:{x}:{y}",
                 "-an", "-c:v", "libx264", "-crf", "12", rc])
        json.dump({"shots": [dict(shot)]}, open(f"{d}/eye/out.json", "w"))
        # 2. 元の前後3秒を切り出して当てる
        a = max(0.0, float(p["start"]) - 3.0)
        clip = f"{d}/src/clip.mp4"
        if not os.path.exists(clip):
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-i", p["file"], "-t", f"{(t1 - t0) + 6:.3f}",
                 "-an", "-c:v", "libx264", "-crf", "12", clip])
        mj = f"{d}/src/match.json"
        run([PY, f"{HERE}/match.py", rc, str(t0), str(t1), clip, "--out", mj])
        if not os.path.exists(mj) or not json.load(open(mj)).get("found"):
            print(p["name"], "当たらんかった＝この枠は土台のまま", flush=True)
            continue
        m = json.load(open(mj))
        json.dump({g.i: {"file": clip, "url": p.get("url", p["file"]), "clip_start": 0.0, "start": m["start"], "flip": m["flip"], "H": m["H"]}},
                  open(f"{d}/src/hi.json", "w"))
        # 3. 枠の大きさで合わせる（追う／追わんの良い方）
        best = None
        for t in (1, 0):
            o = f"{d}/out/t{t}"  # fit_cut の --out は作業フォルダ（d）からの相対
            run([PY, "-W", "ignore", f"{HERE}/fit_cut.py", d, g.i, "--track", str(t), "--out", f"out/t{t}", "--hi", "src/hi.json"])
            try:
                s = json.load(open(f"{o}/{g.i}.json"))["ssim_color"]
            except Exception:
                continue
            if best is None or s > best[0]:
                best = (s, f"{o}/{g.i}.mp4")
        if not best:
            print(p["name"], "合わせられんかった", flush=True)
            continue
        print(p["name"], "SSIM", round(best[0], 3), flush=True)
        done.append((x, y, best[1]))
    if not done:
        return
    # 4. 土台に重ねる
    out = f"{w}/cuts/{g.i}.mp4"
    # 🔴10/27 古い .bak_panel を土台にして後の直しを消した＝土台は毎回「今の物」を写してから使う
    if os.path.exists(out) and not os.path.exists(out + ".bak_panel"):
        shutil.copy(out, out + ".bak_panel")
    src = base
    if os.path.abspath(base) == os.path.abspath(out):
        src = f"{w}/tmp/panel/{g.i}_base_now.mp4"; shutil.copy(out, src)
    args = ["ffmpeg", "-v", "error", "-y", "-i", src]
    for _, _, f in done:
        args += ["-i", f]
    fl, last = [], "0:v"
    for k, (x, y, _) in enumerate(done):
        fl.append(f"[{last}][{k + 1}:v]overlay={x}:{y}:eof_action=pass[o{k}]")
        last = f"o{k}"
    tmp = f"{w}/tmp/panel/{g.i}_comp.mp4"
    run(args + ["-filter_complex", ";".join(fl), "-map", f"[{last}]", "-an", "-c:v", "libx264", "-crf", "12", tmp])
    shutil.move(tmp, out)
    print("書いた", out, "枠", len(done), flush=True)


if __name__ == "__main__":
    main()
