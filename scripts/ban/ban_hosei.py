# 段8 字ごとの戻し：次の戻し＝「その書き出しの仕様書で使った戻し（hosei_used.json）」＋「門で測ったずれ（out/moji.json）」→ hosei.json
#   使った戻しが基準＝字体が替わった字に古い字体の戻しが混ざらん（手本R v13 で行が 98px 広がった穴）
# 使い方：python3 ban_hosei.py <ban の置き場>  → もう一度 ban_spec.py → 組む → 書き出す → ban_gate.py（2周で 2px 超えが 1% 未満まで詰まった）
import json, os, sys
B = os.path.abspath(sys.argv[1]); U = json.load(open(f'{B}/hosei_used.json')); H = []
for o in json.load(open(f'{B}/out/moji.json')):
    u = U.get(f"{o['i']}|{o['t']}|{o['bx']}")
    if o.get('miss') or not u: continue
    h = dict(u); h['x'] = u['x'] + o['dx']; h['y'] = u['y'] + o['dy']; h['w'] = u['w'] * (o['wt'] / max(1.0, o['wt'] + o['dw'])); H.append(h)
json.dump(H, open(f'{B}/hosei.json', 'w'), ensure_ascii=False, indent=0); print('戻し', len(H))
