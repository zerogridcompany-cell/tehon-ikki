#!/bin/bash
# ikki_loop.sh＝手本の写しを、1回の指示で v0 からゴールまで回し続ける見張り役＋係の起動（2026-10-25）
# 元＝51 専用の sup51.sh（見張り）＋ run_air2.sh（係の起動）。どの手本・どの作業フォルダでも使える形にした。
#
#   ikki_loop.sh <作業フォルダ>            … 回し始める（止まるまで前で動く。裏で回すなら nohup … &）
#   ikki_loop.sh score <作業|mane_check.json> … 点数とゴールの判定だけ出す（係は起こさん）
#   ikki_loop.sh prompt <作業フォルダ>     … 係に渡す指示文を出すだけ（係は起こさん）
#
# 止まる条件（どれか1つ）
#   (a) ゴール到達＝🔒10/26 依頼者「全部完全に同じ・51 より上」＝手本を圧縮し直しただけの値（r2 実測 SSIM 0.997・カット 183/184・余計0・波 1.0・ΔE 0.1）
#       既定 SSIM ≥0.997・カット ≥99.5%・余計 0・波 ≥0.999・ΔE ≤0.1・赤0（旧＝51 v112 の 0.69/97%/1/0.98/1.4 は環境変数で戻せる）
#       → DONE の1行目に「ゴール到達」と書いて止まる。終わりの印 IKKI_END＝GOAL
#   (b) 3回続けて点が伸びん（+0.01 以下）→ 休み。IKKI_END＝REST
#   (c) 係の起動が合わせて20回 → 止まる。IKKI_END＝MAXRESTART
#       🔒10/26 依頼者「ネットで止まらんように」＝ネットに届かん間は数えずに待つ（起こす前に api.anthropic.com を見る・係がネットの理由で落ちた回は数えん）
# 点数＝sup51.sh と同じ式：SSIM×100 + 合うカット数 − 余計×0.5 + 波×100 − ΔE×5 + 字×2
#   （字＝<作業>/arai/glyph か <作業>/glyph の最新 match_v*.json で、重なり≥0.95 の数＋箱±0.5% の数。無ければ 0）
# 係＝claude --model <作業/model.txt・無ければ opus> -p（依頼者が「Fable で」と言うたら model.txt に fable）。指示＝references/loop_prompt.md ＋ 作業フォルダの 決め.md（必須）＋ 直し.md（あれば）
# 環境変数で変えられる物：MAX_RESTART(20)・NO_GAIN(3)・GOAL_SSIM(0.997)・GOAL_CUT(0.995)・GOAL_EXTRA(0)・GOAL_WAVE(0.999)・GOAL_DE(0.1)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; SK="$(cd "$HERE/.." && pwd)"
export PATH=$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH
MAX_RESTART=${MAX_RESTART:-20}; NO_GAIN=${NO_GAIN:-3}

# --- 点数とゴール ---------------------------------------------------------
# 出力は1行：「点 ゴール(1/0) 内訳」
score(){ /usr/bin/python3 - "$1" <<'PY'
import json,glob,re,sys,os
a=sys.argv[1]
if os.path.isfile(a):
    f=a; W=os.path.dirname(os.path.dirname(os.path.abspath(a)))
else:
    W=a; vs=glob.glob(os.path.join(W,"check_*","mane_check.json"))
    if not vs: print("0 0 測った版がまだ無い"); sys.exit()
    f=max(vs,key=os.path.getmtime)
j=json.load(open(f))["判定"]
n=lambda s:[float(x) for x in re.findall(r"[\d.]+",str(s))]
def get(k):
    for key in j:
        if key.startswith(k): return j[key]
    return None
s=n(get("絵の近さ SSIM")[0])[0]; c=n(get("カット")[0]); w=n(get("動きの波")[0])[0]; e=n(get("色 ΔE")[0])[0]
m=[p for d in ("arai/glyph","glyph") for p in glob.glob(os.path.join(W,d,"match_v*.json")) if re.search(r"match_v\d+\.json$",p)]
t=0
if m:
    R=json.load(open(max(m,key=os.path.getmtime))).get("rows",[])
    t=sum(1 for x in R if (x.get("iou") or 0)>=0.95)+sum(1 for x in R if x.get("okbox"))
pt=round(s*100+c[0]-c[-1]*0.5+w*100-e*5+t*2,2)
g=lambda k,d:float(os.environ.get(k,d))
cut_rate=c[0]/c[1] if len(c)>=2 and c[1] else 0
red=[k for k,v in j.items() if isinstance(v,list) and len(v)>1 and v[1]=="赤"]
ok=(s>=g("GOAL_SSIM",0.997) and cut_rate>=g("GOAL_CUT",0.995) and c[-1]<=g("GOAL_EXTRA",0)
    and w>=g("GOAL_WAVE",0.999) and e<=g("GOAL_DE",0.1) and not red)
print(pt,1 if ok else 0,f"版={os.path.basename(os.path.dirname(f))} SSIM={s} カット={int(c[0])}/{int(c[1]) if len(c)>1 else '?'}({cut_rate:.1%}) 余計={int(c[-1])} 波={w} ΔE={e} 字={t} 赤={len(red)}{'('+','.join(red)+')' if red else ''}")
PY
}

prompt(){ local W="$1"
  cat "$SK/references/loop_prompt.md"
  printf '\n\n---\n# この回の場所\n- 作業フォルダ＝%s（手本＝%s）\n- スキル＝%s（道具 scripts/run.sh・scripts/tools/・技 references/waza.md・落とし穴 references/otoshiana.md）\n- 今の点（見張りが測った）＝%s\n- 既にある中身を見て、続きからやって。\n\n# 決め.md（本人の決め・必ず守る）\n' "$W" "$(ls "$W"/ref/*.mp4 2>/dev/null | head -1)" "$SK" "$(score "$W")"
  cat "$W/決め.md"
  [ -f "$W/直し.md" ] && { printf '\n\n# 直し.md（この手本の作業指示・一番下の「再開◯回目」から読む）\n'; cat "$W/直し.md"; }
}

case "${1:-}" in
  score)  score "$2"; exit ;;
  prompt) prompt "$(cd "$2" && pwd)"; exit ;;
  ""|-h|--help) sed -n 2,20p "$0"; exit ;;
esac

W="$(cd "$1" && pwd)" || exit 1; L="$W/ikki_loop.log"
[ -f "$W/決め.md" ] || { echo "🔴 $W/決め.md が無い。実写の埋め方・字の書体などを本人に決めてもらって書いてから回す（SKILL.md「先に決めてもらう事」）"; exit 1; }
ls "$W"/ref/*.mp4 >/dev/null 2>&1 || { echo "🔴 $W/ref/ に手本が無い。先に run.sh init <手本.mp4> $W"; exit 1; }
# 🔒10/30 つなぎ：段0 の図鑑が無いまま作る段に入らん（手本は1回だけ見る）
[ -f "$W/zukan/zukan.json" ] || bash "$HERE/run.sh" miru "$(ls "$W"/ref/*.mp4 | head -1)" "$W" || { echo "🔴 段0 見る が門を通らん＝回さん"; exit 1; }
mkdir "$W/.ikki_lock" 2>/dev/null || { echo "🔴 この作業フォルダはもう回っとる（$W/.ikki_lock を見る。落ちた後なら消してから）"; exit 1; }
trap 'rmdir "$W/.ikki_lock" 2>/dev/null' EXIT
rm -f "$W/IKKI_END"
log(){ echo "$(date '+%m/%d %H:%M') $*" | tee -a "$L"; }
net_ok(){ curl -s -m 8 -o /dev/null https://api.anthropic.com/ 2>/dev/null; [ $? -ne 6 ] && [ $? -ne 7 ] && [ $? -ne 28 ]; }
end(){ echo "$1" > "$W/IKKI_END"; log "止まる：$1 $2"; exit 0; }

k=0; r=0; zero=0
read b g0 why < <(score "$W"); log "始め 点 ${b}（${why}）"
[ "$g0" = 1 ] && { printf 'ゴール到達（始めた時にもう届いとった）\n%s\n' "$why" > "$W/DONE"; end GOAL "$why"; }
while true; do
  # 1回分：係が DONE を書くまで起こし直す（重さの見張りで待つ・回数は全部の合計）
  until [ -f "$W/DONE" ]; do
    [ $k -ge $MAX_RESTART ] && end MAXRESTART "係の起動 $k 回"
    until bash "$HERE/run.sh" guard >/dev/null 2>&1; do log "重さの見張りで待つ（run.sh guard）"; sleep 120; done
    # ネットが切れとる間は回数に数えず待つ（10/25〜26 に ENOTFOUND で20回落ちて2回止まった→依頼者「ネットで止まらんように」）
    until net_ok; do log "ネットに届かん（api.anthropic.com）＝数えずに待つ"; sleep 120; done
    k=$((k+1)); log "係を起こす（$k/$MAX_RESTART 回目）"
    n0=$(wc -c < "$W/run.log" 2>/dev/null || echo 0)
    (cd "$W" && nice -n 5 claude --model "$(cat "$W/model.txt" 2>/dev/null || echo opus)" -p "$(prompt "$W")" --dangerously-skip-permissions --output-format stream-json --verbose >> "$W/run.log" 2>&1)
    # 係がすぐ落ちて、落ちた理由がネット（ENOTFOUND・Can't reach the API server・ECONNRESET・ETIMEDOUT）なら、その回は数えん
    if tail -c +$((n0+1)) "$W/run.log" | grep -qE "ENOTFOUND|Can't reach the API server|ECONNRESET|ETIMEDOUT|EAI_AGAIN" && ! [ -f "$W/DONE" ]; then
      k=$((k-1)); log "係がネットの理由で落ちた＝回数に数えん（$k/$MAX_RESTART）"; sleep 120; continue
    fi
    read a ga why < <(score "$W")
    if [ "$ga" = 1 ]; then printf 'ゴール到達\n%s\n' "$why" > "$W/DONE.tmp"; [ -f "$W/DONE" ] && sed 1d "$W/DONE" >> "$W/DONE.tmp"; mv "$W/DONE.tmp" "$W/DONE"; end GOAL "$why"; fi
    [ -f "$W/DONE" ] || sleep 60
  done
  # 回の終わり：点を比べる
  read a ga why < <(score "$W"); r=$((r+1))
  head -1 "$W/DONE" | grep -q "ゴール到達" && log "🟡 係はゴール到達と書いたが数字が届いとらん＝頭打ちとして扱う（${why}）"
  mv "$W/DONE" "$W/DONE_回$r"
  if /usr/bin/python3 -c "import sys;sys.exit(0 if float('$a')>float('$b')+0.01 else 1)"; then zero=0; else zero=$((zero+1)); fi
  log "回$r 終わり 点 ${b}→${a}（伸びなし連続 ${zero}）$why"
  [ $zero -ge $NO_GAIN ] && end REST "$NO_GAIN 回続けて点が伸びず＝休み"
  printf '\n## 再開%s回目（%s・前の回の点 %s→%s）\n- 前の回は頭打ちで止まった。DONE_回%s と 作り方.md の頭打ちの表を読み、loop_prompt.md の「頭打ちで止まったら」の 1〜3 で、前と違うやり方に変える\n- 今の数字：%s\n' \
    $r "$(date '+%m/%d %H:%M')" "$b" "$a" $r "$why" >> "$W/直し.md"
  b=$a; sleep 30
done
