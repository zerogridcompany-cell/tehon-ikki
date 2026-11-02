#!/bin/bash
# tehon-ikki：手本の写し。`run.sh ikki` 1回で v0 からゴール（51 v112 の数字）まで自動。段ごとに手で打つ事もできる（SKILL.md の順）。
#   run.sh miru <手本.mp4> <作業>          … 🆕段0 見る：手本を1回だけ見て全部を数字に（<作業>/zukan/zukan.json・設計図.md・一覧.html）→ 門 check_zukan
#   run.sh init <手本.mp4> <作業フォルダ>   … 置き場・Remotion の土台・カット分け（eye_prep）
#   run.sh plates <作業> <波 例 mg/w1>      … 一枚絵の表と頼み書き（make_plates）→ 裏で Codex（3本ずつ）
#   run.sh fit <作業>                        … 全部の波の一枚絵を手本に当てる（green_fit・ECC）→ proj/src/green.json
#   run.sh render <作業> <版 例 v1>          … 土台を組む→Remotion→音→上下の比べ→mane_check（重さの見張りつき）
#   run.sh grain <作業> <版>                 … 粒の強さ（grain.json）を測る＝次の render で効く
#   run.sh look <作業> <版>                  … 場面ごとの色・明るさ・やわらかさ（look_shot）→ proj/src/shot_look.json＝次の render で効く
#   run.sh cut <作業> <版>                   … 切り替えの強さの直し案（cut_tune・色の後にやる）
#   run.sh ikki <手本.mp4> <作業> [決め.md]  … 🔒1回の命令で最後まで：init→決め.md を置く→ikki_loop.sh を裏で（係が段0〜7→1つずつ直す→ゴール到達か頭打ちまで）
#   run.sh loop <作業>                       … 回し続けるだけ（ikki_loop.sh・記録＝<作業>/ikki_loop.log）
#   run.sh guard                             … メモリとスワップを見る（重い作業の前に毎回）
#   run.sh doctor                            … 🆕この Mac で使える物・足りん物と入れ方の一覧（最初に1回・設定を変えたら）
#   ── 仕上げ（10/27 r2 で効いた順・どの段も「点が上がった物だけ入れる・前は .bak」）──
#   run.sh size <作業> <版>      … 大きさと位置のずれ（size_check）→ ずれたカットを cut_warp で重ね直す
#   run.sh thumbs <作業>         … 素材が YouTube のサムネイルのカットを、元の動画を落として当てる（thumb_vid）
#   run.sh plates-low <作業> <版> … 人が出ん・点の低いカットを Codex の一枚絵で埋める（plates_low→plate_into_cut）
#   run.sh flash <作業> <版>     … 1コマだけ白く光る所（反転・光の差し込み）を Flash 層で（flash_auto）
#   run.sh color <作業> <版>     … 色の当て直し（look_pred で古い色を戻す→look_refit で暗い地の明るさなど）
#   run.sh caps <作業> <版>      … 字幕：大きさ・位置の型合わせ（cap_fit）→時刻（cap_time）→重なり0の確認→手本の読み取りとの突き合わせ（cap_ocr_diff）
#   run.sh zoomblur <作業>       … 手本の放射状のズームぼかしを足す（zoom_blur・全カット）
#   run.sh finish <作業> <版>    … 🔒上を全部この順で：size→thumbs→plates-low→書き出しa→flash→color→caps→zoomblur→書き出しb→cut→書き出しc→照合の門
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; T="$HERE/tools"; SK="$(cd "$HERE/.." && pwd)"
# 🆕11/02 人ごとの設定（tehon-ikki.config・~/.config/tehon-ikki/config）＝場所・鍵・Codex・CapCut。確かめる＝ run.sh doctor
. "$HERE/config.sh"
PY="$TI_PY"; NODE_MODULES="$TI_NODE_MODULES"
guard(){
  local free=$(sysctl -n vm.swapusage 2>/dev/null | sed -E 's/.*free = ([0-9.]+)M.*/\1/'); free=${free:-9999}
  local pct=$(memory_pressure 2>/dev/null | awk -F': ' '/free percentage/{gsub("%","",$2);print $2}')
  echo "見張り：スワップの残り ${free}MB・メモリの空き ${pct}%"
  if [ "${free%.*}" -lt 500 ] || [ "${pct:-100}" -lt 15 ]; then echo "🔴 重い作業を止める（スワップ 500MB 未満かメモリ 15% 未満）"; return 1; fi
  local heavy=$(ps -Ao args= | grep -E "^[^ ]*([Pp]ython|node)[^ ]* " | grep -cE "remotion render|find_sources.py|green_fit.py|fit_all.py|tv_comp|hires.py")
  echo "重い作業 ${heavy} 本"; if [ "$heavy" -ge 2 ]; then echo "🔴 重い作業は同時2本まで（agent-harness 鉄則5）"; return 1; fi
}
case "$1" in
  miru)  REF="$2"; W="$3"; mkdir -p "$W"; guard || exit 1
         # 🔒 手本は1回だけ見る。作る段は zukan.json の数字だけを使う・測り直さん（差の検査は最後の門だけ）
         $PY "$HERE/miru/miru.py" "$REF" "$W" ${@:4} 2>&1 | grep -vE "Warn|^I0000|^W0000|^INFO|non monotonically"
         $PY "$HERE/miru/zukan_plus.py" "$W" 2>&1 | grep -v Warn   # 板の切り替え・図が動くコマ・音は絵の何ms後・フェードの曲がり・字体（assets/fonts_tana に自分で字体を置く）・変わる字
         { $PY "$HERE/miru/kyoku_plus.py" "$W" 2>&1 | grep "曲の決め直し"; } || echo "🟡 曲の決め直しは飛ばした"   # 曲は Shazam の作者の他の曲も指紋で比べ直す・不明の区間は隣の曲の続きか・声は曲の声か語りか（yt-dlp が要る）
         $PY "$HERE/miru/check_zukan.py" "$W" ;;
  meshiken) $PY "$HERE/miru/me_shiken.py" "$2/zukan/zukan.json" "$3" "$2/zukan/me_shiken.json" ;;   # 目の試験：詰め切った答え（seikai.json）と照らして最初に見えた割合
  kouzou) W="$2"; KZ="$HERE/kouzou"; mkdir -p "$W/kouzou"; REF=$(ls "$W"/ref/*.mp4 | head -1)
         [ -f "$W/kouzou/picture.json" ] || $PY "$KZ/e_picture.py" "$REF" "$W/kouzou/picture.json"
         [ -f "$W/kouzou/kyoku.json" ] && $PY "$KZ/kouzou.py" "$W" 2>/dev/null | grep "■\|→" 
         $PY "$KZ/check_kouzou.py" "$W" ;;
  guard) guard ;;
  doctor) bash "$HERE/doctor.sh" ;;
  ban)   S="$2"; B="$3"; BAN="$HERE/ban"   # 板の写し（CapCut）：run.sh ban <states|kawaru|zu|fade|spec|all|draft|gate <mp4>|hosei> <作業>/ban（references/ban.md）
         case "$S" in
           all)  for x in states kawaru zu fade spec; do $PY "$BAN/ban_$x.py" "$B" || exit 1; done ;;
           gate) $PY "$BAN/ban_gate.py" "$B" "$4" 2>&1 | grep -v Warn ;;
           draft) python3 "$BAN/make_draft_spec.py" "$B" ;;
           *)    $PY "$BAN/ban_$S.py" "$B" ${@:4} ;;
         esac ;;
  ikki)
    REF="$2"; W="$3"; K="$4"
    [ -d "$W/proj" ] || bash "$0" init "$REF" "$W"
    if [ -n "$K" ] && [ "$(cd "$(dirname "$K")" && pwd)/$(basename "$K")" != "$(cd "$W" && pwd)/決め.md" ]; then cp "$K" "$W/決め.md"; fi
    [ -f "$W/決め.md" ] || { echo "🔴 $W/決め.md が無い（実写の埋め方・有料生成の許可・書体の候補）＝先に本人に1回聞いて書く"; exit 1; }
    nohup bash "$HERE/ikki_loop.sh" "$W" > "$W/ikki_loop.out" 2>&1 &
    echo "回し始めた：記録 $W/ikki_loop.log・終わり＝$W/IKKI_END（GOAL／REST／MAXRESTART）"
    ;;
  loop) nohup bash "$HERE/ikki_loop.sh" "$2" > "$2/ikki_loop.out" 2>&1 & echo "回し始めた：$2/ikki_loop.log" ;;
  init)
    REF="$2"; W="$3"; mkdir -p "$W/ref" "$W/cuts" "$W/src" "$W/shirabe"
    cp -n "$REF" "$W/ref/" 2>/dev/null || true   # 🔒11/2 BSD の cp -n は「もうある」で 1 を返す＝set -e で init が黙って死んどった（作業の中に ref がある時）
    if [ ! -d "$W/proj" ]; then cp -R "$SK/assets/proj" "$W/proj"
      # 🔴11/02 前は作者の Mac の場所に決め打ちでつないどった＝他の人の Mac では Remotion が無くて何も出んかった
      if [ -n "$NODE_MODULES" ] && [ -d "$NODE_MODULES/remotion" ]; then ln -s "$NODE_MODULES" "$W/proj/node_modules"
      else echo "Remotion を入れる（初回だけ・数分）"; (cd "$W/proj" && npm install --no-audit --no-fund) || { echo "🔴 npm install が通らん＝run.sh doctor を見る"; exit 1; }; fi
    fi
    # 🔒10/30 つなぎ：段0 の図鑑が無ければ先に作る（手本は1回だけ見る）→ カット分け・cfg・字幕の下書きは図鑑から
    [ -f "$W/zukan/zukan.json" ] || bash "$0" miru "$W/ref/$(basename "$REF")" "$W" || { echo "🔴 段0 見る が門を通らん＝作る段に入らん"; exit 1; }
    $PY "$HERE/eye_prep.py" "$W"
    cp "$W/cfg.json" "$W/proj/src/cfg.json"
    $PY "$HERE/zukan_proj.py" "$W"
    if [ "$TI_CODEX" = off ]; then TI_SKIP_LOG="$W/skipped.log" ti_skip "カットの目（eye/out.json）" "Codex が off"
    else echo "次：Codex に eye/task.md を渡して eye/out.json を作らせる（cd $W/eye && $TI_CODEX exec --skip-git-repo-check -s workspace-write \"task.md を読んでその通りに out.json を作って\"）"; fi
    ;;
  plates)
    W="$2"; WV="$3"
    [ "$TI_CODEX" = off ] && { TI_SKIP_LOG="$W/skipped.log" ti_skip "一枚絵 $WV" "Codex が off"; exit 0; }
    $PY "$HERE/make_plates.py" "$W" "$WV" ${@:4}
    (bash "$W/$WV/run_codex.sh" > "$W/$WV/run_codex.log" 2>&1 &) ; echo "裏で Codex：$W/$WV/run_codex.log に ALLDONE"
    ;;
  fit)
    W="$2"; guard
    for g in "$W"/mg/w* "$W"/mg/green; do [ -f "$g/plates.tsv" ] || continue
      ids=$(cut -f1 "$g/plates.tsv" | while read i; do [ -s "$g/$i/plate.png" ] && echo $i; done | paste -sd, -)
      [ -n "$ids" ] && (cd "$W" && $PY "$T/green_fit.py" . "${g#$W/}" --only "$ids" 2>&1 | grep -v Warn | grep -v "r = np")
    done
    $PY - "$W" <<'P'
import json,glob,sys
w=sys.argv[1]; a={}
for g in sorted(glob.glob(f'{w}/mg/w*'))+glob.glob(f'{w}/mg/green'):
    try: a.update(json.load(open(f'{g}/green.json')))
    except FileNotFoundError: pass
# 🔴 flow の結果（seq・ssim_fx）は run.sh flow が proj/src/green.json にだけ書く＝合わせ直しの時に消さん
#    （10/26 t51ikki v9：fit を打ち直して 19 枚の曲げが全部消え SSIM 0.668→0.658・実質fps 16→13）
#    当て（M・color・blur）が変わった絵だけ外す＝その絵は run.sh flow --only で曲げ直す
try: old=json.load(open(f'{w}/proj/src/green.json'))
except FileNotFoundError: old={}
keep,drop=0,[]
for i,p in a.items():
    o=old.get(i)
    if o and 'seq' in o:
        if o.get('M')==p.get('M') and o.get('color')==p.get('color') and o.get('blur')==p.get('blur'):
            p['seq']=o['seq']; p['ssim_fx']=o.get('ssim_fx'); keep+=1
        else: drop.append(i)
json.dump(a,open(f'{w}/proj/src/green.json','w')); print('一枚絵 合わせて',len(a),f'／flow 残した {keep}・当て直しで外した {len(drop)}',(' → run.sh flow <作業> --only '+','.join(drop)) if drop else '')
P
    ;;
  render)
    W="$2"; V="$3"; guard; cd "$W"; REF=$(ls ref/*.mp4 | head -1)
    # 🔴 土台は毎回組み直す（r2 で base.mp4 が古いまま＝テレビ5カットが黒かった）
    $PY "$T/assemble.py" . "base_$V"; cp "base_$V.mp4" proj/public/base.mp4
    # 🔴 --gl=angle（無いと three.js の場面で WebGL が作れず落ちる）・同時に描く数 3（16GB の Mac を詰まらせん）
    (cd proj && npx remotion render src/index.ts Main "../${V}_noaudio.mp4" --muted --gl=angle --concurrency=3)
    ffmpeg -nostdin -v error -y -i "${V}_noaudio.mp4" -i "$REF" -map 0:v -map 1:a? -c:v copy -c:a aac -shortest "$V.mp4"
    ffmpeg -nostdin -v error -y -i "$REF" -i "$V.mp4" -filter_complex "[0:v]scale=960:-2[a];[1:v]scale=960:-2[b];[a][b]vstack[v]" -map "[v]" -map 1:a? -c:v libx264 -crf 18 -c:a aac "${V}_比べ.mp4"
    $PY "$T/mane_check.py" "$REF" "$V.mp4" --out "check_$V" || true
    ;;
  flow)  W="$2"; guard; $PY "$T/flow_tx.py" "$W" ${@:3} 2>&1 | grep -v Warn ;;
  grain) W="$2"; V="$3"; $PY "$HERE/grain_need.py" "$W" "$W/$V.mp4" ;;
  look)  W="$2"; V="$3"; $PY "$T/look_shot.py" "$W" "$W/$V.mp4" 2>&1 | grep -v Warn | tail -3 ;;
  cut)   W="$2"; V="$3"; cd "$W"; $PY "$T/cut_tune.py" "$(ls ref/*.mp4 | head -1)" "$V.mp4" tmp/cuttune_new.json
    # 🔴 測った版にもう cuttune が入っとると「足りん」が消えて空の表になる（10/26 t51ikki v22）＝前の表と和にする（同じコマは新しい方）
    $PY - "$W" <<'P'
import json,sys,os
w=sys.argv[1]; new=json.load(open(f'{w}/tmp/cuttune_new.json')); p=f'{w}/proj/src/cuttune.json'
old=json.load(open(p)) if os.path.exists(p) else {}
u=dict(old); u.update(new); json.dump(u,open(p,'w')); print('cuttune 前',len(old),'新',len(new),'和',len(u))
P
    ;;
  size)  W="$2"; V="$3"; cd "$W"; $PY "$T/size_check.py" . "${V}_noaudio.mp4" | grep -v -i warn | tail -30
    ids=$($PY - <<'P'
import json,os
r=[x for x in json.load(open('tmp/size_check.json')) if x.get('n') and x['bad']>=2 and os.path.exists(f"cuts/{x['cut']}.mp4")]
print(','.join(x['cut'] for x in r))
P
)
    [ -n "$ids" ] && $PY "$T/cut_warp.py" . --ids "$ids" --model affine --min 0.0 2>&1 | grep -v -i warn | tail -30 || echo "重ね直すカット無し" ;;
  thumbs) W="$2"; $PY "$T/thumb_vid.py" "$W" ;;
  plates-low) W="$2"; V="$3"; $PY "$T/plates_low.py" "$W" "$W/${V}_noaudio.mp4" ${@:4} ;;
  flash) W="$2"; V="$3"; guard; $PY "$T/flash_auto.py" "$W" "$W/${V}_noaudio.mp4" --comp Main ;;
  color) W="$2"; V="$3"; $PY "$T/look_pred.py" "$W" "${V}_noaudio.mp4" --write; $PY "$T/look_refit.py" "$W" "${V}_noaudio.mp4" ;;
  caps)  W="$2"; V="$3"; cd "$W"; REF=$(ls ref/*.mp4 | head -1)
    # 🔴 字幕が場面の色・ぼかしの外にあるか（無いとぼかしのカットで字がぼやける）
    grep -q "字幕は場面の色・ぼかし" proj/src/Main.tsx || echo "🔴 proj/src/Main.tsx の字幕が色・ぼかしの中＝スキルの assets/proj/src/Main.tsx を写す"
    [ -d txt/f ] && [ "$(ls txt/f | wc -l)" -gt 10 ] || { mkdir -p txt/f; ffmpeg -nostdin -v error -i "$REF" -vf fps=2997/100 -q:v 2 txt/f/%05d.jpg; }
    $PY "$T/cap_fit.py" . --write | grep -E "変える語|時刻を直す"
    $PY "$T/cap_time.py" . --write | head -3
    $PY "$T/cap_fit.py" . --write --min 9 | grep "時刻を直す"
    $PY "$T/cap_fit.py" . | grep "時刻を直す"
    [ -f txt/ocr_raw.tsv ] && $PY "$T/cap_ocr_diff.py" | head -40 || echo "txt/ocr_raw.tsv が無い＝読み取りとの突き合わせは飛ばす"
    $PY - <<'P'
import json
s=[(c['i'],c['w'],c['f0'],c['f1']) for c in json.load(open('proj/src/caps.json')) if c['f1']-c['f0']<4]
print('4コマ未満しか出ん語（句の途中で消えとらんか目で見る）',s)
P
    ;;
  zoomblur) W="$2"; cd "$W"
    T="$T" $PY - <<'P' | while read k r; do $PY "$T/zoom_blur.py" . "$k" --frames "$r" | grep -E "書いた" | sed "s/^/$k /"; done
import os,sys
sys.path.insert(0, os.environ["T"]); from geo import cut_frames   # 10/30：29.97 の直書きをやめて図鑑のカット（無ければ segs.txt×手本の fps）
for k,(f0,f1) in enumerate(cut_frames('.')):
    if f1-f0>=2 and os.path.exists(f'cuts/{k}.mp4'): print(k, f'{f0}-{f1-1}')
P
    ;;
  zero)  bash "$HERE/zero.sh" "$2" "$3" ;;
  finish) W="$2"; V="$3"
    # 1段こけても次へ（どの段も点が上がった物だけ入れる＝飛ばしても悪くならん）。書き出しだけは失敗したら止める
    bash "$0" size "$W" "$V" || echo "🟡 段 size は失敗＝飛ばした"
    bash "$0" thumbs "$W" || echo "🟡 段 thumbs は失敗＝飛ばした"
    bash "$0" plates-low "$W" "$V" || echo "🟡 段 plates-low は失敗＝飛ばした"
    bash "$0" render "$W" "${V}a"
    for st in flash color caps; do bash "$0" $st "$W" "${V}a" || echo "🟡 段 $st は失敗＝飛ばした"; done
    bash "$0" zoomblur "$W" || echo "🟡 段 zoomblur は失敗＝飛ばした"
    bash "$0" render "$W" "${V}b"; bash "$0" cut "$W" "${V}b" || true; bash "$0" render "$W" "${V}c"
    cd "$W"; SP=$(ls ref/ORACLE_SPEC_*.json 2>/dev/null | head -1)
    if [ -n "$SP" ]; then python3 ~/.claude/skills/tehon-oracle/scripts/oracle.py check "$SP" "${V}c.mp4"; else python3 ~/.claude/skills/tehon-oracle/scripts/oracle.py diff ref/*.mp4 "${V}c.mp4"; fi
    echo "仕上げ済み：${V}c（比べ＝${V}c_比べ.mp4・check_${V}c）" ;;
  *) sed -n 2,23p "$0" ;;
esac
