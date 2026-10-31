# 板の写し（CapCut）の共通部品：設定（cfg.json）・字の行・墨の箱・字体の当て方・大きさと位置
# 置き場（ban/）＝cfg.json・fonts/・states.json・f/sNN.png（状態ごとの代表コマ）・ocr.tsv（代表コマの字の行）・gray_full.raw ほか
import json, os, re
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from fontTools.ttLib import TTFont

class Ban:
    def __init__(s, B):
        s.B = os.path.abspath(B); s.cfg = json.load(open(f'{s.B}/cfg.json'))
        c = s.cfg; s.W, s.H, s.FPS = c['W'], c['H'], float(c.get('fps', 30.0))
        s.F = c['fonts']; s.CAND = c.get('candidates', [k for k in s.F])
        s.EXCL = {(int(i), t) for i, t in c.get('exclude', [])}
        s.RULES = c.get('rules', []); s.CENTER = c.get('center_cols', [s.W / 2]); s.K_LINE = c.get('k_line', 11.46)
        s.MODE = c.get('plain', 'caps')
        s._tm, s._fc, s._pick = {}, {}, {}
    def p(s, *a): return os.path.join(s.B, *a)
    def states(s): return json.load(open(s.p('states.json')))
    def ref(s): return os.path.expanduser(s.cfg['ref'])

    # ---- 字の行（Vision の OCR）。読みの癖を直して、ページ番号は「02 / 06」にそろえる
    @staticmethod
    def norm(t): return re.sub(r'^(\d\d) ?/ ?(\d\d)$', r'\1 / \2', t.replace('у', 'y').replace('•', '·'))
    def rows(s, path=None):
        R = {}
        for l in open(path or s.p('ocr.tsv')):
            f, t, b = l.rstrip('\n').split('\t')
            if t == 'ERR': continue
            R.setdefault(int(re.findall(r'\d+', f)[0]), []).append((s.norm(t), list(map(int, b.split(',')))))
        return R

    # ---- CapCut の字にする行：きれいに読めた普通の字（題・札・説明・ページ番号・時計）。数式・図の中の小さい字は図の側に残す
    PLAIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 /&\-·•.,:;%()'+>#]*$")
    def plain(s, t):
        if re.fullmatch(r'\d\d ?/ ?\d\d', t) or re.fullmatch(r'\d\d\.\d s', t): return True
        if s.MODE == 'all': return bool(t.strip())
        up = sum(c.isupper() for c in t); lo = sum(c.islower() for c in t)
        if s.MODE == 'text': return bool(s.PLAIN.match(t)) and bool(re.search(r'[A-Za-z]{4,}', t))
        return bool(s.PLAIN.match(t)) and up >= 3 and lo <= max(1, up // 8) and bool(re.search(r'[A-Za-z]{4,}', t))   # 4字以上の語がある大文字の行だけ（表の切れ端を拾わん）
    def capcut(s, i, t): return s.plain(t) and (i, t) not in s.EXCL

    # ---- 墨の箱：一番長い続きの行だけ（下の小さい字の頭を拾わん）
    @staticmethod
    def ink_box(g, box):
        x0, y0, x1, y1 = box; c = g[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2]
        if c.size == 0: return box, 255
        pk = np.percentile(c, 99.5); bg = np.percentile(c, 30); thr = bg + 0.45 * (pk - bg)
        m = c > thr; ys = np.where(m.sum(1) >= 1)[0]
        if len(ys) == 0: return box, pk
        runs, cur = [], [ys[0]]
        for y in ys[1:]:
            if y - cur[-1] <= 3: cur.append(y)
            else: runs.append(cur); cur = [y]
        runs.append(cur); ys = np.array(max(runs, key=len))
        xs = np.where(m[ys[0]:ys[-1] + 1].sum(0) >= 1)[0]
        ox, oy = max(0, x0 - 2), max(0, y0 - 2)
        return [ox + xs[0], oy + ys[0], ox + xs[-1] + 1, oy + ys[-1] + 1], pk

    # ---- 字体
    def font(s, key, size):
        k = (key, size)
        if k not in s._fc: s._fc[k] = ImageFont.truetype(s.p(s.F[key]), size)
        return s._fc[k]
    def typo(s, key):                                 # CapCut は OS/2 の typo の上下で行の高さを決める（hhea で測ると Impact +30%・Selawik +24% 大きく出た）
        if key not in s._tm:
            f = TTFont(s.p(s.F[key])); o = f['OS/2']; u = f['head'].unitsPerEm; s._tm[key] = (o.sTypoAscender / u, -o.sTypoDescender / u)
        return s._tm[key]
    def rule_font(s, i, t, box):                      # cfg の rules：上から順に当たった物で字体を決め打ち（無ければ None＝墨で当てる）
        x0, y0, x1, y1 = box
        for r in s.RULES:
            if 'states' in r and i not in r['states']: continue
            if 'text' in r and not re.search(r['text'], t): continue
            if 'min_h' in r and y1 - y0 < r['min_h']: continue
            if 'max_x0' in r and x0 >= r['max_x0']: continue
            if 'max_y0' in r and y0 >= r['max_y0']: continue
            if 'y0' in r and not (r['y0'][0] <= y0 <= r['y0'][1]): continue
            if 'min_w' in r and x1 - x0 <= r['min_w']: continue
            return r['font']
        return None
    def pick_font(s, t, g, ib):                       # 候補の字体で同じ字を書いて、手本の墨と一番重なる物（高さだけ合わせる＝幅の違いで等幅かどうかが分かる）
        k = (t, tuple(int(v) // 3 for v in ib))
        if k in s._pick: return s._pick[k]
        X0, Y0, X1, Y1 = ib; c = g[Y0:Y1, X0:X1]; best = (-1, s.CAND[0])
        if c.size and X1 - X0 >= 3 and Y1 - Y0 >= 3:
            m = c > c.max() * 0.5
            for key in s.CAND:
                ft = s.font(key, 120); l, tp, r, bt = ft.getbbox(t, anchor='ls')
                if r - l < 2 or bt - tp < 2: continue
                im = Image.new('L', (r - l + 10, bt - tp + 10), 0); ImageDraw.Draw(im).text((5 - l, 5 - tp), t, font=ft, fill=255, anchor='ls')
                ww = max(1, int(round((r - l) * (Y1 - Y0) / (bt - tp))))
                aa = np.asarray(Image.fromarray(np.asarray(im)[5:5 + bt - tp, 5:5 + r - l]).resize((ww, Y1 - Y0), Image.LANCZOS)) > 127
                Wd = max(ww, X1 - X0); A = np.zeros((Y1 - Y0, Wd), bool); M_ = np.zeros((Y1 - Y0, Wd), bool)
                A[:, :ww] = aa; M_[:, :X1 - X0] = m
                iou = (A & M_).sum() / max(1, (A | M_).sum())
                if iou > best[0]: best = (iou, key)
        s._pick[k] = best[1]; return best[1]

    # ---- 大きさと位置：手本の墨の高さに同じ字体の墨の高さを合わせる → CapCut の字の箱（送り幅×typo の行）の真ん中
    def fit(s, t, key, ib):
        X0, Y0, X1, Y1 = ib; hh = Y1 - Y0
        l, tp, r, bt = s.font(key, 100).getbbox(t, anchor='ls'); sz = round(100 * hh / max(1, bt - tp) * 4) / 4
        n = max(4, int(round(sz))); f = s.font(key, n); l, tp, r, bt = f.getbbox(t, anchor='ls'); sc = sz / n
        l, tp, r, bt = l * sc, tp * sc, r * sc, bt * sc
        adv = f.getlength(t) * sc; ta, td = s.typo(key); asc, desc = ta * sz, td * sz
        sx = min(1.4, max(0.6, (X1 - X0) / max(1.0, r - l)))   # 横の倍率で手本の墨の幅に合わせる（clip.scale.x・uniform_scale を切る）
        cx = (X0 + X1) / 2 - ((l + r) / 2 - adv / 2) * sx; cy = Y0 - tp + (desc - asc) / 2
        return sz, cx, cy, (r - l), sx
    def fit_new(s, nt, key, ib, sz, center):          # 差し替えの字：同じ字体・同じ大きさで、元の箱の真ん中（左寄せの字は左の端）に置く。箱の幅の 1.1倍を超えたら小さくする
        X0, Y0, X1, Y1 = ib
        for _ in range(2):
            n = max(4, int(round(sz))); f = s.font(key, n); sc = sz / n
            l, tp, r, bt = [v * sc for v in f.getbbox(nt, anchor='ls')]; adv = f.getlength(nt) * sc
            if r - l <= (X1 - X0) * 1.1 or r - l < 1: break
            sz = sz * (X1 - X0) * 1.1 / (r - l)
        ta, td = s.typo(key); asc, desc = ta * sz, td * sz
        cx = ((X0 + X1) / 2 - ((l + r) / 2 - adv / 2)) if center else (X0 - l + adv / 2)
        cy = (Y0 + Y1) / 2 - (tp + bt) / 2 + (desc - asc) / 2   # 墨の縦の真ん中を箱の真ん中に
        return sz, cx, cy, 1.0
    def fs_of(s, key, em):                            # CapCut の font_size：1 あたり行の高さ 11.46px（1920x1080 で測った・別の大きさの下書きは calib で測り直す）
        ta, td = s.typo(key); return em * (ta + td) / s.K_LINE
    def is_center(s, ib): return any(abs((ib[0] + ib[2]) / 2 - c) < 30 for c in s.CENTER)

    def gray(s, i): return np.asarray(Image.open(s.p('f', f's{i:02d}.png')).convert('L'), np.float32)
