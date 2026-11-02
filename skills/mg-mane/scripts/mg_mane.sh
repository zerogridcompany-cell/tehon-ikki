#!/bin/bash
# mg-mane の入口（薄い）。中身は tehon-ikki の道具を呼ぶだけ（写さん）。
#   mg_mane.sh miru   <手本.mp4> [作業]               … 段0 見る（作業の既定＝~/research/tehon-me/<手本の名前>・手本は <作業>/ref/ に置く）→ run.sh miru
#   mg_mane.sh kime   <手本.mp4> <作業>               … 決め.md を型（references/kime_template.md）から書くだけ（あれば触らん）
#   mg_mane.sh ikki   <手本.mp4> <作業> [決め.md]     … 図鑑が無ければ miru → 決め.md が無ければ kime → run.sh ikki（裏で係が A〜D・v2 で止まる）
#   mg_mane.sh ken    <手本.mp4> <うち.mp4> <出す所> [--step 6] [--from コマ --to コマ] … 検品の一覧（6コマおき・上＝手本・下＝うち）→ <出す所>/k00.jpg …
#   mg_mane.sh kurabe <手本.mp4> <うち.mp4> <出す所>  … 上下比べ（960x540×2・うちの音）と半透明の重ね（blend=average・両方の音を半分ずつ）
#   mg_mane.sh hakaru <手本.mp4> <うち.mp4> [--kukan 名:a-b,…] [--md 出す.md] [--json 出す.json] … 数字の照合（SSIM・波・滑らかさ・量・切り替え・ΔE・効果音・LUFS）
set -e
PY=/usr/bin/python3   # homebrew の python3 には numpy・cv2 が無い（tehon-ikki run.sh と同じ）
HERE="$(cd "$(dirname "$0")" && pwd)"; SK="$(cd "$HERE/.." && pwd)"
TI="${TEHON_IKKI_SCRIPTS:-$HOME/.claude/skills/tehon-ikki/scripts}"; [ -d "$TI" ] || TI="$(cd "$HERE/../../.." && pwd)/scripts"   # 公開リポの中（skills/mg-mane）に置いた時はリポの scripts/
abs(){ echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; }
absdir(){ mkdir -p "$1" && (cd "$1" && pwd); }   # 作業フォルダは絶対の道で run.sh に渡す
put_ref(){   # 手本を <作業>/ref/ に置いて、その道を返す（同じファイルなら写さん・BSD cp -n は「もうある」で 1 を返す＝使わん）
  local R="$1" W="$2"; mkdir -p "$W/ref"; local D="$W/ref/$(basename "$R")"
  [ -f "$D" ] || cp "$R" "$D"; abs "$D"
}
kime(){
  local R="$1" W="$2"
  [ -f "$W/決め.md" ] && { echo "決め.md はもうある（触らん）：$W/決め.md"; return 0; }
  $PY - "$R" "$W" "$SK/references/kime_template.md" > "$W/.kime_tmp.md" <<'PY'
import json, os, re, subprocess, sys, time
R, W, T = sys.argv[1:4]
j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,nb_frames", "-show_entries", "format=duration", "-of", "json", R], capture_output=True, text=True).stdout)
v = next(s for s in j["streams"] if s["codec_type"] == "video"); a, b = v["r_frame_rate"].split("/"); fps = float(a) / float(b)
has_a = any(s["codec_type"] == "audio" for s in j["streams"])
lu = "—"
if has_a:
    e = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", R, "-vn", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", e); lu = m[-1] if m else "—"
zp = os.path.join(W, "zukan", "zukan.json"); cuts = "（図鑑がまだ無い＝係が段0 の後に書く）"; rows = "- （係が A 見る100% の最初に、カットごとに1行ずつ書く）"
if os.path.exists(zp):
    Z = json.load(open(zp)); cs = Z.get("cuts", [])
    cuts = "・".join(str(c["f0"]) for c in cs)
    rows = "\n".join(f"- {c['f0']}〜{c['f1'] - 1}：（係が A 見る100% で中身を1行・設計図.md のこのカットから）" for c in cs)
name = os.path.splitext(os.path.basename(R))[0]
rep = {"名前": name, "日付": time.strftime("%-m/%-d"), "手本": os.path.relpath(R, W), "W": v["width"], "H": v["height"], "fps": f"{fps:.3f}".rstrip("0").rstrip("."),
       "N": v.get("nb_frames", "?"), "秒": f"{float(j['format']['duration']):.2f}", "音": "あり" if has_a else "なし", "LUFS": lu, "カット": cuts, "カットごと": rows}
s = open(T).read(); s = s.split("<!-- ここから下が決め.md -->", 1)[-1].lstrip()
print(re.sub(r"\{\{(.+?)\}\}", lambda m: str(rep.get(m.group(1), m.group(0))), s), end="")
PY
  mv "$W/.kime_tmp.md" "$W/決め.md"
  echo "決め.md を型から書いた：$W/決め.md（中身の行は係が段0 の設計図から書き足す。本人が言うた事があれば先に足す）" >&2
}
case "$1" in
  miru)
    [ -f "$2" ] || { echo "🔴 手本が無い：$2"; exit 1; }
    NAME=$(basename "${2%.*}"); W=$(absdir "${3:-$HOME/research/tehon-me/$NAME}"); R=$(put_ref "$2" "$W")
    bash "$TI/run.sh" miru "$R" "$W"
    echo "次：$W/zukan/設計図.md と 一覧.html を読む → mg_mane.sh ikki $R $W" ;;
  kime)
    [ -f "$2" ] && [ -n "$3" ] || { echo "使い方：mg_mane.sh kime <手本.mp4> <作業>"; exit 1; }
    W=$(absdir "$3"); R=$(put_ref "$2" "$W"); kime "$R" "$W" ;;
  ikki)
    [ -f "$2" ] && [ -n "$3" ] || { echo "使い方：mg_mane.sh ikki <手本.mp4> <作業> [決め.md]"; exit 1; }
    W=$(absdir "$3"); R=$(put_ref "$2" "$W"); K="$4"
    [ -f "$W/zukan/zukan.json" ] || bash "$TI/run.sh" miru "$R" "$W" || { echo "🔴 段0 見る が門を通らん＝作る段に入らん"; exit 1; }
    [ -n "$K" ] || kime "$R" "$W"
    bash "$TI/run.sh" ikki "$R" "$W" ${K:+"$K"}
    echo "見張り：$W/ikki_loop.log。🟡 見張りの点は 0 のまま・3回で REST で止まるのが正常（構成の写しの点は mg_mane.sh hakaru で測る）" ;;
  ken)    [ -n "$4" ] || { echo "使い方：mg_mane.sh ken <手本.mp4> <うち.mp4> <出す所> [--step 6] [--from コマ --to コマ]"; exit 1; }; $PY "$HERE/ken.py" "${@:2}" ;;
  hakaru) [ -n "$3" ] || { echo "使い方：mg_mane.sh hakaru <手本.mp4> <うち.mp4> [--kukan 名:a-b,…] [--md 出す.md] [--json 出す.json]"; exit 1; }; $PY "$HERE/hakaru.py" "${@:2}" ;;
  kurabe)
    A="$2"; B="$3"; O="$4"; [ -f "$A" ] && [ -f "$B" ] && [ -n "$O" ] || { echo "使い方：mg_mane.sh kurabe <手本.mp4> <うち.mp4> <出す所>"; exit 1; }
    mkdir -p "$O"; NM=$(basename "${B%.*}")
    pv(){ ffprobe -v error -select_streams v:0 -show_entries "stream=$1" -of default=nw=1:nk=1 "$2" | head -1; }
    W=$(pv width "$A"); H=$(pv height "$A"); FR=$(pv r_frame_rate "$A")
    HA=$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$A" | head -1)
    HB=$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$B" | head -1)
    FB=$(pv r_frame_rate "$B")
    # コマ番号でそろえる（hakaru と同じ1対1）：両方の時刻を「コマ番号÷手本の fps」に置き直す（settb＋setpts=N）。
    #   fps フィルタや -shortest を通すと最後の1コマが落ち（379→378）、時刻の刻みが違う（2997/100 と 30000/1001）と 59.94fps に倍になった
    #   うちの fps が手本と違う時だけ、先に手本の fps にそろえる
    TB=$(echo "$FR" | awk -F/ '{print ($2==""?1:$2) "/" $1}')
    if [ "$($PY -c "from fractions import Fraction as F;print(int(abs(float(F('$FR'))-float(F('$FB')))<0.001))")" = 1 ]; then FA=""; else FA="fps=$FR,"; fi
    SA="settb=$TB,setpts=N"; SB="${FA}settb=$TB,setpts=N"; ENC=(-fps_mode passthrough -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k)
    if [ "$W" -ge "$H" ]; then TW=960; TH=$(( 960 * H / W / 2 * 2 )); ST=vstack; F1="$O/比べ_上が手本_下がうち_$NM.mp4"
    else TH=960; TW=$(( 960 * W / H / 2 * 2 )); ST=hstack; F1="$O/比べ_左が手本_右がうち_$NM.mp4"; fi
    F2="$O/重ね_半透明_手本xうち_$NM.mp4"
    ffmpeg -nostdin -v error -y -i "$A" -i "$B" -filter_complex "[0:v]$SA,scale=$TW:$TH,setsar=1[a];[1:v]$SB,scale=$TW:$TH,setsar=1[b];[a][b]$ST=inputs=2:shortest=1[v]" \
      -map "[v]" ${HB:+-map 1:a} "${ENC[@]}" "$F1"
    if [ -n "$HA" ] && [ -n "$HB" ]; then AF=";[0:a]aresample=48000[x];[1:a]aresample=48000[y];[x][y]amix=inputs=2:duration=shortest:normalize=0,volume=0.5[aa]"; AM=(-map "[aa]")
    elif [ -n "$HB" ]; then AF=""; AM=(-map 1:a); elif [ -n "$HA" ]; then AF=""; AM=(-map 0:a); else AF=""; AM=(); fi
    ffmpeg -nostdin -v error -y -i "$A" -i "$B" -filter_complex "[0:v]$SA,scale=$W:$H,setsar=1,format=yuv420p[a];[1:v]$SB,scale=$W:$H,setsar=1,format=yuv420p[b];[a][b]blend=all_mode=average:shortest=1[v]$AF" \
      -map "[v]" "${AM[@]}" "${ENC[@]}" "$F2"
    echo "できた：${F1}（音＝うち）"; echo "できた：${F2}（音＝手本とうちを半分ずつ＝音が二重に聞こえたらずれ）"
    echo "見せる：tehon-oracle の門（🔴0・ORACLE_OK.json）が通ってから open -R で Finder に出す" ;;
  *) sed -n 2,8p "$0"; exit 1 ;;
esac
