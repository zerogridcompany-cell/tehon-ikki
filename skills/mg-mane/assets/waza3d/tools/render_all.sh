#!/bin/bash
# 5 本を書き出す（重い物は同時 2 本まで）
cd "$(dirname "$0")/.."
r(){ npx remotion render src/index.ts $1 out/$1.mp4 --gl=angle --concurrency=4 --crf=16 --log=error >out/render_$1.log 2>&1 && echo "OK $1" || echo "NG $1"; }
r T01 & r T02 & wait
r T03 & r T04 & wait
r T05
