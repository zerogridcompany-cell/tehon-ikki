"""Codex が無い時の「目」の代わり（2026-11-02）：図鑑（zukan.json）のカットから eye/out.json の骨だけを書く。
python3 eye_nashi.py <作業>
- 中身（誰・何の場面・元の候補・検索語）は "?"＝推測で埋めん。カットの秒だけは図鑑どおり
- これで run.sh render が通る（素材の無いカットは黒）。Codex を入れたら eye/task.md を渡して out.json を作り直す
"""
import json, os, sys
w = os.path.abspath(sys.argv[1]); p = f"{w}/eye/out.json"
if os.path.exists(p): print("eye/out.json はもうある＝触らん"); sys.exit(0)
Z = json.load(open(f"{w}/zukan/zukan.json"))
shots = []
for c in Z["cuts"]:
    k = (c.get("seishi") or {}).get("kind", "") if isinstance(c.get("seishi"), dict) else ""
    shots.append(dict(i=c["i"], t0=round(float(c["t0"]), 3), t1=round(float(c["t1"]), 3), kind="?", who=["?"], what="?",
                      source_guess="?", search=[], screen_text="?", edit=k or "?", same_as=None, caption=None))
os.makedirs(f"{w}/eye", exist_ok=True)
json.dump(dict(shots=shots, captions_style={}, mg=[], src="eye_nashi（Codex 無し・カットの秒だけ）"), open(p, "w"), ensure_ascii=False, indent=1)
print(f"eye/out.json（骨だけ・{len(shots)} カット）を書いた＝Codex 無しで render まで進める")
