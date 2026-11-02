#!/bin/bash
# 人ごとの設定を読む（2026-11-02）。run.sh・ikki_loop.sh の頭で source する。
# 読む順（後ろが勝つ）：既定 → <スキル>/tehon-ikki.config → ~/.config/tehon-ikki/config → 環境変数 TI_CONFIG のファイル
# 書き方は tehon-ikki.config.example。足りん物は `run.sh doctor` で一覧に出る。
_TI_SK="${SK:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
for _f in "$_TI_SK/tehon-ikki.config" "$HOME/.config/tehon-ikki/config" "${TI_CONFIG:-}"; do
  [ -n "$_f" ] && [ -f "$_f" ] && . "$_f"
done
# Python：numpy と cv2 が入っとる物を自動で選ぶ（指定があればそれ）
if [ -z "${TI_PY:-}" ]; then
  for _p in /usr/bin/python3 "$(command -v python3 2>/dev/null)" /opt/homebrew/bin/python3; do
    [ -x "$_p" ] && "$_p" -c "import numpy,cv2" 2>/dev/null && { TI_PY="$_p"; break; }
  done
  TI_PY="${TI_PY:-python3}"
fi
TI_NODE_MODULES="${TI_NODE_MODULES:-}"                       # 空＝作業フォルダの proj で npm install する
TI_ELEVENLABS_KEY_FILE="${TI_ELEVENLABS_KEY_FILE:-$HOME/.elevenlabs_key}"
TI_CODEX="${TI_CODEX:-$(command -v codex 2>/dev/null || echo off)}"   # off＝Codex を使う段は飛ばす
TI_CLAUDE="${TI_CLAUDE:-$(command -v claude 2>/dev/null || echo off)}"
TI_LOOP_MODEL="${TI_LOOP_MODEL:-opus}"
TI_OCR="${TI_OCR:-}"                                           # 空＝scripts/tools/bin/ocr-words（初回に swiftc で組む）
TI_CAPCUT="${TI_CAPCUT:-off}"                                  # on＝板の写しを CapCut で組む（macOS・CapCut デスクトップ版）
TI_SFX_DIRS="${TI_SFX_DIRS:-}"                                 # 効果音の棚（: 区切り）。空＝<作業>/oto/sfx だけ
TI_WORK_ROOT="${TI_WORK_ROOT:-$HOME/tehon-ikki-work}"         # 音の段の置き場など、作業フォルダが決まってない時の既定
export TI_PY TI_NODE_MODULES TI_ELEVENLABS_KEY_FILE TI_CODEX TI_CLAUDE TI_LOOP_MODEL TI_OCR TI_CAPCUT TI_SFX_DIRS TI_WORK_ROOT
ti_skip(){ echo "⏭️ 飛ばした：$1（理由：$2）" | tee -a "${TI_SKIP_LOG:-/dev/null}"; }
