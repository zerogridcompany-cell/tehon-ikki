# txt51：字の道具（51 で効いた物の汎用版・10/25）

手本の字を1字ずつ写す道具一式。元は `~/research/mane-20261021/air/items/51/tools/`。数字は 51 の `作り方.md` の再開4〜8回目。
字は **Remotion で描く**（`assets/proj/src/Txt51.tsx`）。PIL や ffmpeg で焼かん。

## 共通の決まり
- 回すのは `/usr/bin/python3`（numpy・cv2 あり。homebrew の python3 には無い）
- 引数は全部の道具で同じ：`--work <作業>`（`<作業>/ref/*.mp4`・`<作業>/proj/src/texts.json` か `caps.json`）・`--ref`・`--texts`・`--sheet`・`--out`（既定 `<作業>/txt51`）・`--ids a,b`
- 字の表は **texts 形（51）と caps 形（r2）のどちらでも読める**。中では texts 形に直して扱い、書き戻す時は元の形に戻す（`_t51.py`）。Txt51.tsx で描くなら `caps2texts.py` で texts.json にする
- 画面の大きさ・fps は手本から読む（ffprobe）。51 の px の数字（余白・帯・探す幅）は 高さ/1080 を掛けて使う。合格の線＝幅・高さの 0.5%（51 は 9.6px・5.4px）
- 🔴 コマは「ちょうど f」を読む＝`-ss (f−0.5)/fps`。51 の道具の `(f+0.5)/30` は f+1 を読んどった（r2 で select n と比べて確かめた）。字だけの層・字ごとの書き出しも同じ f で描く
- 測るコマ＝出揃ってから消えるまでの真ん中（`frame_of`・Txt51 の `sheetFrame`）

## 字の表の2つの形
| | texts 形（51） | caps 形（r2） |
|---|---|---|
| 1行 | 字（語の並び）1つ | 語1つ |
| 時刻 | `t0`・`t1`（秒・t1 は出とらん） | `f0`・`f1`（コマ・f1 も出とる） |
| 中身 | `text`・`font`（書体の名前）・`w`（太さ）・`color` | `w`（語）・`kind`（serif/sans）・太さと横の倍率は look.json |
| 置き方 | `fs`・`sx`・`x`・`y`（SVG text を translate(x,y) scale(sx,1)） | 同じ（ただし r2 の Main.tsx は `c.sx` でなく look の serifSx/sansSx で描く） |
| 直し方 | — | id＝`c<i>`・text＝w・font＝kind・t0＝f0/fps・t1＝(f1+1)/fps・color＝#ffffff・w と sx は look から |

## 使う順番
| 順 | 何をする | 道具 | 効いた数字（51） |
|---|---|---|---|
| 0 | 字の型がまだ無い時の最初の測り：字ごとの窓と色の決まりで 時刻・箱・行・色 | `text_measure.py <mp4> spec.json out.json` | 57語の最初の箱と色 |
| 1 | 書体を決める：候補の書体を手本の字のマスクに重ねて IoU 比べ（3 の後に回す・最後は字の形を目で） | `font_id.py <版> --fonts "<dir>/*.ttf"` | Inter 0.651＝SF Pro（同点）＝替えん・通知の字は目で Lato |
| 2 | 箱合わせ：手本の字のインクの箱→同じ書体ファイルで fs・sx・x・y を逆算 → texts.json | `build_texts.py 下書き.json 書体.json texts.json`（1つだけなら `fit_text_box.py`） | 位置 0.5% 以内から始まる |
| — | 字だけの層を書き出す（Txt51 の TxtSheet）。**字の表を変えたら毎回** | `npx remotion render src/index.ts TxtSheet <作業>/txt51/sheet --sequence --image-format=png` | 🔴 古い層で測って数字がずれた |
| 3 | 字の物差し：字ごとに手本とうちの字の色のマスクの IoU と箱。地を拾った測りは「測り不能」 | `glyph_match.py <mp4> <版> --sheet …` | 測れた 47→52（物差し2）・箱 27→43/57 |
| 4 | 字の型の当て（形の重ね合わせ）：dx,dy,sx,sy → 字の表へ | `txt_reg.py <mp4> <版>` → `reg_apply.py <版>` | 字の位置 17→52/57・SSIM 0.715→0.727 |
| 5 | 出る・消える時刻（型の中だけ・左端と右端も） | `txt_time.py <mp4> <版>` | — |
| 6 | 1字ずつの時刻（打ち字の reveal を最小二乗で当て直す） | `char_time.py <mp4> <版> [--apply]` | 打ち字 10/11 が全部の字で ±1コマ |
| 7 | 1字ずつの送り（字ごとの dx＝cdx） | `char_reg.py <mp4> <版>` → `char_apply.py <版>` | IoU 0.766→0.780・28語 |
| 8 | 下の出・上の出・線の削りなど1つの値を全部の字に振った版から字ごとに選ぶ | `dk_pick.py base:1,dk88:0.88,… --key dk` | 字の箱 27→33/57（dk）・costs 🔴→✅（ka） |
| 9 | ぼけと濃さの段（毎コマの σ と濃さ） | `blur_track.py <id> <f0> <f1>` → 字の表の blurk・blurgain | for の σ が全コマ一致・濃さ 2% 以内 |
| 10 | 溶けて削れる消え方（残りの割合→erop） | `ero_fit.py <mp4> id:a:b,… [--init]` | 4つの消え方の差 0.02〜0.05 |
| 11 | 一括補正：今までの版から字ごとに一番良い版を土台に、マスクの重ね合わせで x・y・sx・fs を一度に | `ikkatsu_txt.py <次の版> --hist v1,v2,…` | 箱で直すと IoU 0.70→0.67＝形で合わせる |
| 見る | 字の所を手本（上）・うち（下）でコマごとに並べる | `time_strip.py <mp4> <id> <f0> <f1>` | 5・6 の数字を目で確かめる |
| 形 | caps.json ⇄ texts.json | `caps2texts.py` | — |

- 回すたびに、書き出した時の字の表を `<作業>/txt51/glyph/texts_<版>.json` に写しておく（11 が使う）
- 試しは全部の書き出しを待たずに：字だけの層＋「字ごとの測るコマだけ本編を止めて描いた書き出し」（51 の Probe51＝作業ごとに作る）を `glyph_match.py none <版> --frames <dir>` で測る
- 🔴 箱だけ合って見た目が悪くなる直しは捨てる（51：Ascend の A を右へ＝箱✅でも IoU 0.68→0.59）。帯の SSIM と一緒に見る
- 🔴 太さ（wv）を変えたら 7 の1字ずつの当て直しとセット（太さで字の幅も変わる）

## Remotion 側で読む値（Txt51.tsx）
| 値 | 何 | 書く道具 |
|---|---|---|
| `id` `text` `font` `w` `color` `t0` `t1` | 字・書体の名前（loadTxtFonts の名前）・太さ・色・出る/消える秒 | build_texts・caps2texts |
| `fs` `sx` `sy` `x` `y` | 大きさ・横/縦の倍率・原点（`translate(x,y) scale(sx,sy)`） | build_texts・reg_apply・ikkatsu_txt |
| `reveal` `rtl` `words` `cfade` | 1字ずつ出る [r0,r1]・右から・語ごと [[字a,字b,秒s,秒e]]・1字の溶け（秒・既定 0.1） | char_time |
| `cdx` | 字ごとの送り（tspan の dx・後ろの字も動く） | char_apply |
| `wv` | 太さの上書き（可変の書体） | 手で（51 の weight_try） |
| `dk` `ka` | 下の出（ベースラインより下）・上の出（x の高さより上・書体ごとの `xh`）の縦の倍率 | dk_pick |
| `er` `sw` `eb` | 線だけ削る（px）・同じ色の縁取りで太らせる（px）・縁のぼけ σ | 手で（Probe で振る） |
| `mul` `blend` `opacity` | 掛け合わせの色（multiply）・重ね方（overlay・soft-light）・濃さ | 手で（字の画素の散らばりで決める） |
| `exit` `xout` | 消え方 cut・fade・wipe・glitch・erode と その秒 | 手で・ero_fit |
| `erop` | erode の進み [[コマ, 0→1]] | ero_fit |
| `blurk` `blurgain` | ぼけの段 [[コマ, σ]]・明るさの倍 [[コマ, 倍]] | blur_track |
| `fadein` `blurin` `blurout` | 出る時の溶け・ぼけ・消える時のぼけ [秒, 秒, σ] | 手で |
| `zoom` `zoomk` `zc` | 拡大 [t0,t1,倍]・[[秒, 倍]]・その中心（既定＝画面の真ん中・51 は zoomk に [960,547]） | 手で（51 の zoom_scan） |
| `dyk` `jumps` `clipY` | 縦に流れる [[秒, px]]・跳ぶ [[秒, px, 濃さ]]・その下を切る | 手で |
| `glow` `shc` | 光と光の筋・筋の中心 | 手で |
| `qrect` `qbox` `qk` `qcolor` | 字の後ろの箱 [x,y,幅,高さ]・伸びる秒・測った左右の表 [[コマ, 左, 右]]・色 | 手で |
| `italicTail` | 最後の n 字を斜体（書体の `italicKey`） | 手で |

- 書体＝`loadTxtFonts({名前: {file, weight?, style?, opsz?, xh?, italicKey?}})` をモジュールの頭で1回（delayRender で読み終わりを待つ）
- 試しの props：`{"wd":{"*":-50}}`（太さ）・`{"dk":{"*":0.88}}`・`{"ka":{"*":0.92}}`・`{"eb":1.4}`（`"*"`＝全部・id ごとも可）
- 本編は `<TxtLayer texts={TEXTS} />`、字だけの層は `<TxtSheet texts={TEXTS} />` を Composition に（durationInFrames＝字の数・fps と大きさは本編と同じ）
- r2 のように caps を Main.tsx が自前で描いとる作業では、字の表の直し（x・y・fs と足した値）は caps.json に戻るが、Main は `c.sx`・`cdx`・`dk` 等を読まん＝効かせるには Txt51 の TxtLayer に替える
- `caps2texts.py --back` で戻すと sx は look の値が書かれる（道具の中で caps を直接読んで書いた時は、変わってない sx は書き戻さん）

## 移さんかった物（51 にしか使えん・ほかで足りる）
- `ikkatsu.py` の色と動きの所：51 の場面の決まり（紙の場面の絵の名前・mane_check の秒の表）に乗っとる。色は `scripts/tools/look_shot.py`
- `font_id6.py`：`font_id.py` と中身が同じ（候補の書体の場所だけ違う）＝ `--fonts` で1本に
- 元の `build_texts.py` の字の中身（51 の57語の add 行）：51 の手本の字そのもの。決まり（fit・sx 0.8〜1.3・同じ大きさで縦に並べる）だけ移した
- `keep_curve.py` は `ero_fit.py` の中に入れた（`--curve` で割合だけ出せる）
