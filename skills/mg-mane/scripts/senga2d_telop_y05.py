# 照合の門の telop_center_y を 0.5 秒おきで測り直す（門は 2 秒おき＝揺れる）。oracle.py の OCR をそのまま使う
# 使い方: python3 tools/telop_y05.py <動画>…
import sys, os, subprocess, tempfile, statistics, importlib.util
sp = importlib.util.spec_from_file_location('oracle', os.path.expanduser('~/.claude/skills/tehon-oracle/scripts/oracle.py')); O = importlib.util.module_from_spec(sp); sp.loader.exec_module(O)
for p in sys.argv[1:]:
    d = tempfile.mkdtemp(prefix='ty05_'); subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-vf', 'fps=2,scale=720:-2', os.path.join(d, 'f_%04d.png')], check=True)
    fr = sorted(os.path.join(d, f) for f in os.listdir(d)); L = O.ocr_lines(fr); ys = []
    for f in fr:
        bg = O.biggest(L.get(os.path.basename(f)) or [])
        if bg: ys.append((bg[2] + bg[4]) / 2 / (720 * 1080 / 1920))
    q = statistics.quantiles(ys, n=4)
    print(f'{os.path.basename(p)}: telop_center_y 中央 {statistics.median(ys):.3f}（四分位 {q[0]:.3f}–{q[2]:.3f}・{len(ys)}/{len(fr)} コマ）')
