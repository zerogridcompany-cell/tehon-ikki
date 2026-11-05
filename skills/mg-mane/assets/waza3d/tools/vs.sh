#!/bin/bash
# 比べ：上＝手本・下＝見本（2 コマ/秒・6 枚）
ref=$1; ours=$2; out=$3
ffmpeg -v error -y -i "$ref" -i "$ours" -filter_complex "[0]fps=2,scale=480:270,tile=6x1[a];[1]fps=2,scale=480:270,tile=6x1[b];[a][b]vstack" -frames:v 1 "$out"
