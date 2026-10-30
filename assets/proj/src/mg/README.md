# 動く MG の部品（段2d・2026-10-25）

手本の中で**動く** MG（吹き出し・通知・砂嵐・札の雨・紙のしわ・描き順・広がる写真・差し替えの連打・カメラが動く1枚の絵）は、
Codex の止まった一枚絵＋曲げる（flow_tx）では点が上がらん（t181 で赤が残った）。51 は Remotion の部品で組んで v112 まで行った。その部品の汎用版がここ。
**止まった一枚絵で済まさん。動く所はここの部品で組み、手本から測った値を表（json）にして渡す。**

## 使い方（3つだけ）
1. `src/mg.json` に並べる：`[{"part":"Chat","f0":1650,"f1":1920,"props":{…}}, …]`（f0〜f1 は両端込みのコマ・並びの順に下から重なる）
2. 大きい表（毎コマ測った値）は `public/mg/<名前>.json` に置いて、props に `"@mg/<名前>.json"` と書く（読み終わるまで待つ）
3. 層：`"layer":"under"`＝土台の動画の上・一枚絵の下（Paper・Boil・紙の上の CamImg）／既定 `over`＝カードの上・字幕の下／`top`＝場面の色とぼかしの外（Notif）。`"style":{"mixBlendMode":"multiply","opacity":0.9}` で層ごとの重ね方
- `mg.json` が `[]` なら何も描かん＝今まで通り。時刻は全部**コマ**・位置は全部**画面の px**（51 の数字は 1920x1080）

## 手本の MG の種類 → 部品 → 測る値
| 手本で見える物 | 部品（ファイル） | 手本から測る値 | 測る命令（scripts/tools/） |
|---|---|---|---|
| 紙の地・点の網（全場面で同じ紙） | `Paper`（Paper.tsx） | 紙の色・点の周期と位相・同じ紙か | `mg_measure.py <手本> corners f0 f1`（0.95 以上＝1枚の紙）・色＝四隅の中央値 |
| 紙のしわ・線がちらちら替わる | `Boil`・`Jitter`（Boil.tsx） | 替わるコマ（段の表）・強さ | `mg_measure.py <手本> boil f0 f1 --out public/mg/boil.json`（間のコマ 中央値＝every） |
| メッセージの吹き出し | `Chat`・`Bub`・`Words`・`RiseWords`（Chat.tsx） | 箱（色の塊）・ぽんの段・伸びるコマ・語の出るコマ | `mg_measure.py <手本> box f0 f1 --color 47,125,225`（青）／`180,178,176`（灰）・語＝`steps --box <行の箱>` |
| スマホの通知 | `Notif`（Notif.tsx） | 箱・出るコマ・題と本文の出るコマ・書体 | `box --color <箱の色>`・`steps --box <行>`・書体＝txt51/README.md の当て比べ |
| テレビの砂嵐 | `Static`（Static.tsx） | 粒・濃淡の幅・平均の色・止めの間隔 | `mg_measure.py <手本> noise f0 f1 --box x0,y0,x1,y1` |
| 平たい物がはじける | `Burst`（Flat.tsx） | 中心・枚数・速さ（目で）・横切る1枚 | 手本を 1コマずつ並べて目で（点の追跡は重なって取れん） |
| 平たい物が落ちる | `FallBills`（Flat.tsx） | 1枚ずつ [始まり, x, 幅, 横, 落ち, 種] | 10fps で並べて目で置く（ぶれて追跡できん） |
| 大量に散って漂う | `Rain`（Flat.tsx） | 毎コマの見えとる割合と幅→ k,s の表 | `mg_measure.py <手本> area f0 f1`→うちも同じに測って ks を1歩ずつ寄せる（2〜3回） |
| 黒い地に散る物（塊が分かれとる） | `RainRects`（Flat.tsx） | 毎コマの塊の四角 | `mg_measure.py <手本> rects f0 f1 --out public/mg/rects.json`（そのまま rects に） |
| 画面いっぱいに舞う | `Scatter`（Flat.tsx） | 枚数・大きさ | 目で |
| 形が変わる物（玉が開く） | `CrumpleBall`（CrumpleBall.tsx） | 段ごとの中心・幅・絵 | `box --far <紙の色>`（同じ幅が続く所が1段） |
| 線が描かれていく | `Scribble`（Scribble.tsx） | 線の形・描き切るコマ・色と濃さの段 | 形＝Codex に path で書かせる・速さ＝`area --far <地>` の増え方 |
| 写真が破れた形で広がる | `War`＝`TornReveal`（War.tsx） | 毎コマの見えとる割合→広がり e | `area --far <下の地の色>`→e を1歩ずつ寄せる |
| 2〜3コマごとの差し替え（連打・目・画面） | `Swap`（Swap.tsx） | 替わるコマ・箱・どの絵か・中で寄るか | `steps`（●＝替わり・・＝止め）・`box --far`・寄り＝`zoom_meas.py` |
| 1枚の大きな絵をカメラが流す・寄る・振る | `CamImg`（CamImg.tsx） | 3x3 の鎖・横振りの D・s・L | `cam_chain.py <作業> f0 f1 --out public/mg/cam_x.json`・`whip_fit.py`・縁＝`pad_mirror.py` |

各部品の頭に「何をする・props・51 で効いた数字・測る道具」を書いてある。足りん値は推測で埋めず、測るか目で読んでから入れる。

## 合わせ方（1部品ずつ・この順）
1. **時刻**：`steps` の●（替わり）と・（止め）で、出るコマ・段の間隔（2コマ／3コマ打ち）を決める。🔴 10fps の帯から作った表は間隔を間違える（51：0.585→0.613 は 30fps で測り直して）
2. **箱と位置**：`box` で毎コマの外枠 → 部品の x,y,w,h／段の表へ。中身の絵は Codex で描き直した物（画素は貼らん）
3. **量**（広がり・面積・粒）：手本とうちの書き出しに同じ命令（`area`・`noise`）をかけ、差を1歩ずつ表に戻す。枚数を増やすより大きさで合わせる（枚数を増やすと SSIM が下がる）
4. **乱数**：位置は `random("種")`＝毎回同じ。種（seed）を替えて SSIM の良い方を採る。画素で合わん物（砂嵐）は数字（粒・幅・平均・止め）で合わせて止める
5. 測った値は mg.json（小さい表）か public/mg/*.json（毎コマの表）へ。数字は会話に置かず、作業の 作り方.md にも1行

## 確かめ方
- その範囲だけ書き出す：`npx remotion render src/index.ts Main ../try.mp4 --frames=<f0>-<f1> --gl=angle --concurrency=3`
- `python3 scripts/tools/seg_ssim.py <作業> try.mp4 <f0> <f1> --off <f0> --each`＝前と後を比べて上がった時だけ残す
- 動きは `python3 scripts/tools/wave_top.py <作業> <うち.mp4> --vs <前の版.mp4>`＝その範囲が波を下げとらんか
- MG と実写は分けて見る（51 v109：全体 0.759・MG 0.817・実写 0.701）。手本｜うち｜差を目でも見る

## motion-cm の決まりのうち、写しに効く物だけ
- **手本の値が先**：曲線・ms・止まりは手本から測った物を使う。図鑑（~/.claude/skills/motion-cm/references/ugoki-zukan.md）は「測った動きに一番近い名前」を選んで `common.ts` の `curve("easeOutBack", p)` で呼ぶだけ（自分流の気持ちいい動きに替えん）
- 動きは**名前＋コマ数＋曲線**で書く（例：吹き出しの伸び＝6コマ easeOutCubic・ぽん＝3コマの段で 0.585→1.02→1.078→1）。spring は `springAt(f−f0, fps, {stiffness, damping})`
- **段で動く物は段のまま**（紙のコラージュは 3コマ・連打は 2〜3コマ）。滑らかにすると手本より速く・別物に見える
- 止まり：手本が止まっとるコマは止める（毎コマ寄せると ffmpeg のカット判定が消える＝51 v7 でカット 88→66）。止まっとらん所を止めん
- 字（吹き出し・通知の字も）は Remotion で描く（PIL・ffmpeg で焼かん）。書体は FontFace を読み終わってから（Txt51 の loadTxtFonts で読んで、その名前を font に渡す）

## 試し（2026-10-25）
- `npx tsc --noEmit`（strict）通った。Paper・Boil・Static・Chat・RainRects（@ の表）・Burst・Scribble・War・Notif・CamImg（射影つき）・Swap・CrumpleBall を1画面に並べたスチルを2枚書いて、全部出るのを目で見た
- `mg_measure.py` を 51 の手本に当てた：灰色の吹き出しの段＝1696・1699・1702・1705（51 の表と同じ）／頭の紙幣の替わり＝3コマごと／砂嵐＝粒 3px・幅 48・平均 (96,95,107)（51 の測り 40〜48・(92,95,111)）／しわの替わり＝間 3コマ／紙の四隅＝0.98（1枚の紙）
