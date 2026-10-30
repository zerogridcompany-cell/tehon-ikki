# tehon-ikki（手本の写し 一発）

他人の動画（手本）を1コマずつ写すための Claude Code スキルです。
前に作った2本の写し（51・r2）で見つけた技と落とし穴を、最初から全部、効く順番でかけます。
測る → 作る → 合わせる → 見た目 → 切り替え → 音 → 比べる、までを1回の命令で回します。編集ソフトは使いません。

## 2本の写しで伸びた数字
| 写し | 手本 | 結果 |
|---|---|---|
| 51 | @ascendculture・94秒 | v112 で SSIM 0.694〜0.75・色の差 ΔE 0.9〜1.4・カット 99〜102/102 |
| r2 | @attentioncompound・76秒 | v4 0.362 → v10 0.541（式の見込み 0.537）。その後 v88 まで進め、音の写しまで |

## 段0 見る：手本を1回見て全部を数字の設計図にする
```bash
bash scripts/run.sh miru <手本.mp4> <作業フォルダ>
```
手本だけを1回見て、カットごとの全部の数字（カットの頭と終わりのコマ・切り替えの種類・拍や言葉や効果音のどれに合わせとるか・カメラ・一枚絵か動画か・色・粒・鋭さ・網点・顔・画面の字の出る/消えるコマと箱・飾り・効果音・声・曲・拍の網・LUFS）を `<作業>/zukan/zukan.json`・`設計図.md`・`一覧.html` に書きます。門は `scripts/miru/check_zukan.py`（升が空なら止める）。
作る段はこの数字だけを使い、測り直しません（差の検査は最後の門だけ）。何をどの道具で測るか・前の2本の写しとの当たりの数字・まだ弱い所は `references/miru.md`。
字の読み取りに macOS の Vision（`scripts/miru/ocr_words.swift`・初回に swiftc で組む）、音に demucs・whisper-cli（large-v3-turbo）・shazamio、顔に mediapipe を使います。

## 入れ方
```bash
git clone https://github.com/zerogridcompany-cell/tehon-ikki.git ~/.claude/skills/tehon-ikki
```
Claude Code で「この動画を写して」「手本の写し」と言うと呼ばれます。

## 読む順
1. `SKILL.md`：全体の一本道と各段の門
2. `references/miru.md`：段0 見る（手本を1回見て全部を数字に）
3. `references/kouzou.md`：作る前に曲・拍・切り替わりを数字で固める（段0.5）
4. `references/waza.md`：効いた技と数字
5. `references/otoshiana.md`：踏んだ落とし穴
6. `references/oto.md`・`references/sabun_zero.md`：音の写しと差分0の手順

## 必要な物
- Python 3（opencv・numpy・scipy・librosa・scikit-image）
- ffmpeg・yt-dlp・demucs
- Node と Remotion 4（書き出しの土台は `assets/proj`。`npm install` してから使う）
- Codex CLI（カットの中身を書く「目」と、一枚絵の描き直し）
- ElevenLabs の鍵（音の段だけ。`~/.elevenlabs_key` に置く）

## 注意
- 書体ファイル（`assets/proj/public/fonts`）は入れていません。各自で用意してください。
- 文中の `~/research/...` は作った時の作業フォルダです。自分の場所に読み替えてください。
- 写した動画を公開する時は、元の動画の権利を確かめてください。
