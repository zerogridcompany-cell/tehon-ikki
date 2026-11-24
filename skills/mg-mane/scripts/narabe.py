# 手本｜うちの版… を同じ絵の秒（rikai/rf.json の地図）で縦に並べた一覧を 0.5 秒おきに全部（mise/v2/ 等）
# 使い方: python3 narabe.py <出力dir> <おき秒> <手本.mp4> <うちA.mp4> [うちB.mp4 …]   （手本の秒→うちの秒の地図＝環境変数 RF_JSON・既定 rikai/rf.json＝[[手本の秒,うちの秒],…]）   ※時刻は最後の版（うちの秒）で刻む
import cv2, json, sys, os, numpy as np
from PIL import Image, ImageDraw
out, st, ref, vids = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4:]
RF = json.load(open(os.environ.get('RF_JSON', 'rikai/rf.json'))); rx = [a for a, b in RF]; ry = [b for a, b in RF]
o2r = lambda t: float(np.interp(t, ry, rx))
os.makedirs(out, exist_ok=True); caps = [cv2.VideoCapture(p) for p in [ref] + vids]
dur = cv2.VideoCapture(vids[-1]).get(cv2.CAP_PROP_FRAME_COUNT) / 30
tw, th = 320, 180; n = len(caps); C = 6; R = max(1, 1620 // (th * n)); per = C * R
ts = list(np.arange(0, dur - 0.05, st)); k = 0
def grab(c, t):
    c.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, im = c.read()
    if not ok: return Image.new('RGB', (tw, th), 'gray')
    return Image.fromarray(cv2.resize(im, (tw, th), interpolation=cv2.INTER_AREA)[:, :, ::-1])
for s in range(0, len(ts), per):
    sub = ts[s:s + per]; sh = Image.new('RGB', (C * tw + (C - 1) * 4, R * (th * n + 6)), 'white'); d = ImageDraw.Draw(sh)
    for i, to in enumerate(sub):
        x, y = (i % C) * (tw + 4), (i // C) * (th * n + 6); tr = o2r(to)
        for j, c in enumerate(caps):
            sh.paste(grab(c, tr if j == 0 else to), (x, y + j * th))
        d.rectangle([x, y, x + 118, y + 12], fill='black'); d.text((x + 2, y), f'手{tr:.2f} う{to:.2f}', fill='yellow')
    sh.save(f'{out}/n{k:02d}_{sub[0]:06.1f}.jpg', quality=82); k += 1
print(k, '枚', len(ts), '点', '段:', ['手本'] + vids)
