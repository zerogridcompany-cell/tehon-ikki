# 世界の MG 実例：Apple「The MacBook Air with M5」

- 手本＝〈URL〉 公式・2026-03-03・452 万回・50 秒・1920x1080・24fps・-19.9 LUFS）。出所は未承認
- 実物＝~/research/mg-sekai-20261104/dl/02_apple_air_m5.mp4・測り＝an/02_apple_air_m5/
- 切り替え 23 回・間隔の中央 0.77 秒（25〜75% 0.53〜3.44）＝**MG の所は 0.5〜1 秒ごとに新しい絵・実写の所は 3〜7 秒**
- 明るい部屋の実写＋MacBook の画面の中の MG（L 中央 48.5）。B 案の「暗い舞台」とは逆だが、**字の札の作り方と切り替えの速さ**を借りる

## 0. 先に結論
1. **ページめくり（Page curl）で画面の中身を替え続ける**（5.0・5.5・6.5・7.5・8.0＝0.5〜1 秒ごと）＝切り替えの種類を 1 つに統一
2. **極太の字を「窓の札」に入れて OS の窓のように重ねる**：「Do more faster with」＋M5 チップの札＋「chip」の札（12.5〜15）
3. **札ごとに 1 色**：UP TO 9X＝橙・18 HOURS＝黄緑（#d4ff00 付近）・16GB＝付箋の黄・ideas＝選択の青
4. **付箋を 1 枚ずつ貼って文にする**：「Starting at／16GB／of／unified memory」を 1 語 1 枚（0.3〜0.5 秒）
5. **打ち込みの字を選択の青で強調**：「Great ideas start here」をカーソルで 1 字ずつ→「here」が選択されて青く塗られる（34〜38）

## 1. 場面の秒の表
| 秒 | 何が起きる |
|---|---|
| 0.0–3.5 | 実写：部屋・人が座る・開く |
| 3.5 | 顔の寄り（目） |
| 4.0–4.5 | 画面へ寄る（中の窓） |
| 5.0–8.5 | ページめくりの連打（窓が角からめくれて次の窓） |
| 9.0–10.0 | 「THE NEW／MACBOOK AIR」が空の写真の上に奥からせり出す |
| 10.5–11.5 | 指がトラックパッドを押す実写 |
| 12.0–15.0 | 「Do more faster with」の極太の字の窓＋M5 チップ＋「chip」 |
| 15.5–18.5 | 指の実写→「UP TO 9X / FASTER AI PERFORMANCE」橙の札・斜体・速さでぶれる |
| 18.5–21.0 | めくり→94%→100% の進み棒 |
| 21.5–25.0 | 「UP TO 18 HOURS OF BATTERY LIFE」黄緑の札・1 語ずつ |
| 25.5–27.0 | 通知の実写 |
| 27.5–29.5 | 付箋が 1 枚ずつ貼られて文「Starting at 16GB of unified memory」 |
| 30.0–31.5 | 「AND 512GB OF STORAGE」極太の字が画面からはみ出すまで寄る |
| 32.5–36.0 | カレンダー→白い紙の札に打ち込み「Great ideas start here」 |
| 36.5–38.0 | 口元・手元の実写→「here」が選択の青 |
| 38.5–45.0 | MacBook が宙に浮いて回り、閉じて上へ飛ぶ＋「The new MacBook Air with M5」 |
| 45.5–50.0 | 黒にリンゴ（灰→白 1.5 秒） |

## 2. 技
### 技① Page-curl chain（ページめくりの連打）
- 1 回 0.4〜0.6 秒・めくれの角は右下か右上・めくれた裏は白（紙）＋影
- Remotion：`@remotion/transitions` に page curl が無いので、SVG で三角の折れの多角形＋裏面のグラデ＋影を `t` で動かす（自作 PageCurl 部品）か、WebGL のシェーダー（gl-transitions の "InvertedPageCurl"）
### 技② Type-as-window（字の札を窓として重ねる）
- 札＝角 12〜16px の矩形・面 1 色・中に極太の字（Apple はSF Pro Display Heavy 系・行間 0.9）・札どうしは影で重なる
- Remotion：`<Card bg="#ff5a1f"><h1 style={{fontWeight:900,fontStyle:'italic',lineHeight:.9}}>UP TO 9X</h1></Card>` を `translate` と `scale` で順に重ねる
### 技③ One-color-per-claim（主張ごとに 1 色）
- 橙（速さ）・黄緑（電池）・黄（容量）・青（選択）＝色が変わる＝話題が変わる
### 技④ Sticky-note words（付箋で 1 語ずつ）
- 付箋（#fff27a 付近・少し傾き ±3°）が 0.3〜0.5 秒ごとに「ぽん」と貼られる（scale 1.15→1・80ms）
### 技⑤ Type-and-select（打ち込み→選択の青で強調）
- 1 字 50〜70ms・2 行目は大きい字・最後に語の選択（#b3d4ff 付近）が左→右に 200ms で塗られる
### 技⑥ Float-and-fly product（製品が浮いて回って去る）
- 38.5〜41：MacBook が机から浮き、回り、閉じて上へ（1 動作 2.5 秒・ease-in-out）＋細い白い字

## 3. 音
- 曲 約 103 BPM（目安）・-19.9 LUFS。切り替え ±120ms 内 7 件・中央 −57ms（絵先 5・音先 2）＝**絵が少し先**（me_mimi の「絵が先」と同じ向き）

## 4. 測れんかった物
- 書体は SF Pro 系と見えるが未当て。めくりの角度・影の値は目視
