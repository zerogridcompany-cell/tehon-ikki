# 🔴10/31 戻した（目の問題集 v2）：練習 51 の字体 47→70% やが本番 tehonU 68→35%・r2 76→56%＝ゴシック寄りに倒れる。run.sh には入れてない。次の道＝線のむら(line_mura)と票を合わせる・見本に無い字体は決めん
# 段0 見るの足し（10/31 目の問題集）：字体の系統（セリフ／ゴシック／筆記）を、1語ずつ字の墨と見本の字体を重ねて決める
#  前＝線の太さのむら（line_mura>0.45）だけで「明朝・セリフ系の見当」＝51 のセリフ↔ゴシックが 47%
#  見本＝システムのセリフ 9本＋編集でよく使う Instrument Serif・Lora Italic（assets/fonts_kei）／ゴシック 11本＋Inter・Lato／筆記 2本
#  今＝語の真ん中のコマの墨（字の箱の中・明るい字か暗い字か）と、セリフ 9本・ゴシック 11本・筆記 2本の字体で同じ語を描いた形を
#      高さでそろえて重ね（IoU）、系統ごとの一番で決める。差が小さい（0.02 未満）時は前の見当のまま
# 使い方：python3 moji_kei.py <作業> [手本.mp4]
import json, os, sys, glob
import numpy as np, cv2
from PIL import Image, ImageFont, ImageDraw
D = os.path.dirname(os.path.abspath(__file__)); TANA = os.path.join(D, '..', '..', 'assets', 'fonts_tana'); KEI = os.path.join(D, '..', '..', 'assets', 'fonts_kei'); SUP = '/System/Library/Fonts/Supplemental'
W_ = sys.argv[1]; ZP = f'{W_}/zukan/zukan.json'; Z = json.load(open(ZP)); REF = sys.argv[2] if len(sys.argv) > 2 else Z['meta']['ref']
F = dict(serif=[(f'{SUP}/Times New Roman.ttf', 0), (f'{SUP}/Times New Roman Bold.ttf', 0), (f'{SUP}/Times New Roman Italic.ttf', 0), (f'{SUP}/Georgia.ttf', 0), (f'{SUP}/Georgia Bold.ttf', 0),
                 (f'{SUP}/Georgia Italic.ttf', 0), (f'{SUP}/Didot.ttc', 0), (f'{SUP}/Bodoni 72.ttc', 0), (f'{SUP}/Baskerville.ttc', 0),
                 (f'{KEI}/InstrumentSerif-Regular.ttf', 0), (f'{KEI}/InstrumentSerif-Italic.ttf', 0), (f'{KEI}/Lora-Italic[wght].ttf', 0)],
         sans=[(f'{TANA}/Arial.ttf', 0), (f'{TANA}/Arial Bold.ttf', 0), ('/System/Library/Fonts/Helvetica.ttc', 0), ('/System/Library/Fonts/Helvetica.ttc', 1), (f'{TANA}/Impact.ttf', 0),
                (f'{TANA}/D-DIN-Bold.otf', 0), (f'{TANA}/NotoSans-Bold.ttf', 0), (f'{TANA}/Verdana.ttf', 0), (f'{TANA}/Anton-Regular.ttf', 0), (f'{TANA}/BebasNeue-Regular.ttf', 0), (f'{SUP}/Futura.ttc', 0),
                (f'{KEI}/Inter[opsz,wght].ttf', 0), (f'{KEI}/Lato-Bold.ttf', 0), (f'{KEI}/Lato-Regular.ttf', 0)],
         script=[(f'{SUP}/SnellRoundhand.ttc', 0), (f'{SUP}/Zapfino.ttf', 0)])
FT = {}
def font(p, i):
    if (p, i) not in FT:
        try: FT[(p, i)] = ImageFont.truetype(p, 120, index=i)
        except Exception: FT[(p, i)] = None
    return FT[(p, i)]
def render(t, ft):
    l, tp, r, bt = ft.getbbox(t, anchor='ls')
    if r - l < 2 or bt - tp < 2: return None
    im = Image.new('L', (r - l + 10, bt - tp + 10), 0); ImageDraw.Draw(im).text((5 - l, 5 - tp), t, font=ft, fill=255, anchor='ls')
    a = np.asarray(im) > 127; ys, xs = np.where(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(ys) else None
def iou(mask, t, ft):
    g = render(t, ft)
    if g is None: return 0
    h, w = mask.shape; ww = max(1, int(round(g.shape[1] * h / g.shape[0])))
    if ww > 3 * w or ww < w / 3: return 0
    a = cv2.resize(g.astype(np.uint8), (ww, h), interpolation=cv2.INTER_AREA) > 0
    Wd = max(ww, w); A = np.zeros((h, Wd), bool); M = np.zeros((h, Wd), bool); A[:, :ww] = a; M[:, :w] = mask
    return (A & M).sum() / max(1, (A | M).sum())
words = Z.get('moji', {}).get('words', [])
need = {}
for w in words:
    t = ''.join(ch for ch in w['w'] if ch.isalnum() or ch in "'&-")
    if len(t) < 2 or (w['box_px'][3] - w['box_px'][1]) < 10: continue
    need.setdefault((w['f0'] + w['f1']) // 2, []).append((w, t))
cap = cv2.VideoCapture(REF); f = 0; done = 0; cnt = {}
while need:
    ok, fr = cap.read()
    if not ok: break
    if f in need:
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        for w, t in need.pop(f):
            x0, y0, x1, y1 = w['box_px']; x0, y0 = max(0, x0), max(0, y0); c = g[y0:y1, x0:x1]
            if c.size == 0: continue
            th, _ = cv2.threshold(c, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            mask = c > th if w.get('polarity') == '白っぽい字' else c < th
            ys, xs = np.where(mask)
            if len(ys) < 20: continue
            mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            best = {k: max((iou(mask, t, font(p, i)) for p, i in v if font(p, i)), default=0) for k, v in F.items()}
            o = sorted(best.items(), key=lambda x: -x[1]); w['kei_iou'] = {k: round(float(v), 3) for k, v in best.items()}
            if o[0][1] - o[1][1] >= 0.02 and o[0][1] >= 0.3:
                w['font_kei'] = o[0][0]; w['font_guess'] = {'serif': 'セリフ系（墨の重ね）', 'sans': 'ゴシック系（墨の重ね）', 'script': '筆記体（墨の重ね）'}[o[0][0]]
                cnt[o[0][0]] = cnt.get(o[0][0], 0) + 1; done += 1
    f += 1
json.dump(Z, open(ZP, 'w'), ensure_ascii=False)
print(f'字体の系統（墨の重ね）：{done}/{len(words)} 語を決めた {cnt}')
