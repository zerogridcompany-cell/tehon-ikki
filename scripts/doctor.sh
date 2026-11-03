#!/bin/bash
# run.sh doctor：この Mac で何が使えて何が足りんかを一覧にする（2026-11-02）。何も変えん。
HERE="$(cd "$(dirname "$0")" && pwd)"; SK="$(cd "$HERE/.." && pwd)"
. "$HERE/config.sh"
ok=0; ng=0; opt=0
row(){ # 印 名前 状態 入れ方
  printf '%s %-22s %s\n' "$1" "$2" "$3"; [ -n "${4:-}" ] && printf '   └ %s\n' "$4"
  case "$1" in ✅) ok=$((ok+1));; 🔴) ng=$((ng+1));; *) opt=$((opt+1));; esac; }
have(){ command -v "$1" >/dev/null 2>&1; }
echo "■ 設定の読み元：$( for f in "$SK/tehon-ikki.config" "$HOME/.config/tehon-ikki/config" "${TI_CONFIG:-}"; do [ -n "$f" ] && [ -f "$f" ] && printf '%s ' "$f"; done; echo '(既定)')"
echo "■ 要る物（無いと出力が出ん）"
if "$TI_PY" -c "import numpy,cv2,scipy,librosa,skimage" 2>/dev/null; then row ✅ Python "$TI_PY"
else miss=$("$TI_PY" -c "
import importlib.util as u
print(' '.join(p for m,p in [('numpy','numpy'),('cv2','opencv-python'),('scipy','scipy'),('librosa','librosa'),('skimage','scikit-image')] if u.find_spec(m) is None))" 2>/dev/null)
  row 🔴 Python "$TI_PY に足りん部品：${miss:-?}" "$TI_PY -m pip install ${miss:-numpy opencv-python scipy librosa scikit-image}"; fi
have ffmpeg && row ✅ ffmpeg "$(command -v ffmpeg)" || row 🔴 ffmpeg 無し "brew install ffmpeg"
have node && row ✅ Node "$(node -v)" || row 🔴 Node 無し "brew install node"
if [ -n "$TI_NODE_MODULES" ]; then
  [ -d "$TI_NODE_MODULES/remotion" ] && row ✅ Remotion "$TI_NODE_MODULES" || row 🔴 Remotion "TI_NODE_MODULES=$TI_NODE_MODULES に remotion が無い" "設定の TI_NODE_MODULES を消すと作業フォルダで npm install する"
else row ✅ Remotion "作業フォルダの proj で npm install（init の時・初回だけ数分）"; fi
[ "$TI_CLAUDE" != off ] && row ✅ "Claude Code" "${TI_CLAUDE}（回し役のモデル ${TI_LOOP_MODEL}・ログインしてない時は ikki が KAKARI_OCHI で止まる）" || row 🔴 "Claude Code" "無し＝run.sh ikki の回し役が動かん（1本目 v1 だけは出す）" "npm i -g @anthropic-ai/claude-code → claude を1回開いてログイン"
echo "■ 無くても回る（その段は飛ばして記録に残す）"
have yt-dlp && row ✅ yt-dlp ok || row 🟡 yt-dlp "無い＝曲の決め直し・サムネの元動画を飛ばす" "brew install yt-dlp"
"$TI_PY" -c "import demucs" 2>/dev/null && row ✅ demucs ok || row 🟡 demucs "無い＝声と曲を粗く分ける（声の1語ずつの時刻も取れん）" "$TI_PY -m pip install demucs"
"$TI_PY" -c "import matplotlib" 2>/dev/null && row ✅ matplotlib ok || row 🟡 matplotlib "無い＝音の譜面の絵（hako.png）を飛ばす" "$TI_PY -m pip install matplotlib"
WM="${TI_WHISPER_MODEL:-$HOME/Library/Caches/whisper-cpp/ggml-large-v3-turbo.bin}"
if have whisper-cli && [ -s "$WM" ]; then row ✅ whisper-cli "ok（型 $WM）"
elif have whisper-cli; then row 🟡 whisper-cli "型が無い（$WM）＝言葉の時刻を飛ばす" "mkdir -p ~/Library/Caches/whisper-cpp && curl -L -o $WM https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin（約1.6GB・置き場は設定の TI_WHISPER_MODEL）"
else row 🟡 whisper-cli "無い＝言葉の時刻を飛ばす" "brew install whisper-cpp（型も要る＝もう一度 doctor で出る）"; fi
"$TI_PY" -c "import shazamio" 2>/dev/null && row ✅ shazamio ok || row 🟡 shazamio "無い＝曲の名前当てを飛ばす" "$TI_PY -m pip install shazamio"
"$TI_PY" -c "import mediapipe" 2>/dev/null && row ✅ mediapipe ok || row 🟡 mediapipe "無い＝顔の測りを飛ばす" "$TI_PY -m pip install mediapipe"
[ "$TI_CODEX" != off ] && row ✅ Codex "$TI_CODEX" || row 🟡 Codex "off＝カットの目・一枚絵を飛ばす（点は下がる）" "npm i -g @openai/codex して codex login"
[ -s "$TI_ELEVENLABS_KEY_FILE" ] && row ✅ ElevenLabs "$TI_ELEVENLABS_KEY_FILE" || row 🟡 ElevenLabs "鍵が無い＝声の作り直しを飛ばす（手本の音のまま）" "鍵を $TI_ELEVENLABS_KEY_FILE に1行で置く"
if [ -n "$TI_OCR" ]; then [ -x "$TI_OCR" ] && row ✅ 字の読み取り "$TI_OCR" || row 🟡 字の読み取り "TI_OCR=$TI_OCR が動かん"
elif [ "$(uname)" = Darwin ] && have swiftc; then row ✅ 字の読み取り "同梱の ocr-words（macOS Vision・初回に組む）"
else row 🟡 字の読み取り "macOS の swiftc が無い＝画面の字を飛ばす" "xcode-select --install"; fi
if [ "$TI_CAPCUT" = on ]; then [ -d /Applications/CapCut.app ] && row ✅ CapCut ok || row 🟡 CapCut "on やけど /Applications/CapCut.app が無い"
else row 🟡 CapCut "off（板の写しは Remotion で組む）"; fi
[ -d "$SK/assets/proj/public/fonts" ] && [ -n "$(ls "$SK/assets/proj/public/fonts" 2>/dev/null)" ] && row ✅ 書体 ok || row 🟡 書体 "assets/proj/public/fonts が空＝既定の書体で描く" "使う書体を assets/proj/public/fonts に置く"
echo "■ まとめ：✅ ${ok}・🔴 ${ng}・🟡 $opt"
[ "$ng" -eq 0 ] && echo "→ 回せます：bash scripts/run.sh ikki <手本.mp4> <作業フォルダ> <決め.md>" || echo "→ 🔴 を先に入れてください"
[ "$ng" -eq 0 ]
