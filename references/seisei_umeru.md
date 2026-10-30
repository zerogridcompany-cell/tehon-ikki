# 人が出ん実写を生成で埋める（seisei_umeru・2026-10-26）

🔒 依頼者 10/26「実際に映像がなさそうな部分＝ロケットとかロボットとかお金とか、人が出てない部分。そこは Kling とかで生成AIで作ってほしい。モーションブラーとか写真の角度も含めて進められるように」。
→ 10/25 の「実写は元探しだけ」は、**人が出ん実写で元が見つからん物**についてだけ上書き。本人（手本の主役）や人物が出る実写は今まで通り元探しだけ（jissha-sagashi）。

## いつ使う（全部そろった時だけ）
1. jissha-sagashi の段1〜5 を全部回して、まだ元が見つかってない
2. そのカットに**人が出ん**（ロケット・工場・ロボット・札・車の外観・空撮・物）。eye/out.json の what で判断し、黒コマ/<番号>.jpg を目で見て確かめる
3. 決め.md に「生成で埋めてよい」と本人が書いとる（r2 は 10/26 に書いた）

## 手順
| 段 | やる事 | 道具・置き場 |
|---|---|---|
| 1 | **手本を測る**：コマ数・秒・明るさ・色3つ・鋭さ・動きの大きさと向き・寄り引き・モーションブラーの比→指示文の下書き（英語）と参照コマ3枚 | `/usr/bin/python3 scripts/tools/ref_look.py <作業> <番号>` → `shirabe/seisei/<番号>.json`・`<番号>_{0,1,2}.jpg` |
| 2 | **指示文を仕上げる**：what＋測った数字（camera / movement / blur_words / palette）＋「no people, no text, no logos」。角度は what と参照コマから言葉に（low-angle・top-down・three-quarter 等 camera-work-24 の名前） | `shirabe/seisei/<番号>.txt` |
| 3 | **撃つ前の照合**：`python3 ~/bin/shippai-shoumei.py init <作業>` → 失敗集の頭20と1行ずつ照らす（SHOUMEI.md） | 門＝shippai-zentai-gate.sh |
| 4 | **見積もりを出して止まる**：480p 試し（Seedance 2.5 5秒≒15cr／Kling 2.5 5秒≒数十cr）→本番 1080p。カット数×本数×単価を表で見せて **「作って」を待つ** | 有料は「作って」の後だけ（CLAUDE.md） |
| 5 | **撃つ**：`higgsfield account status` で 自分のアカウント を確かめてから。image→video（参照コマ = 手本の字幕を隠した1枚）か text→video。5秒が最小＝手本の秒に切る | higgsfield-generate |
| 6 | **当てる**：出来た動画を src/hi/<番号>.mp4 に置き、hi.json に手で登録（id="gen"・start=0・H は match.py で出す）→ `fit_all.py --only <番号>`（位置・色・ぼかしは手本に合う） | tehon-ikki 段3 |
| 7 | **測る**：mane_check の秒ごとの表でそのカットの SSIM・ΔE が黒（0）より上がったか。モーションブラーが手本と違えば ref_look の blur_words を強弱して1つだけ変えて撃ち直す | 1回に1つだけ変える（feedback_one_change_per_shot） |

## 指示文の型（英語・ref_look の prompt_draft を土台に）
```
<what をそのまま>. <camera: locked-off / slow push-in / slow pull-out>, <movement: static / subtle drift / steady pan / fast whip> (<px/frame> toward <deg>°),
<blur_words: crisp / natural 180° shutter motion blur / heavy motion blur>. Overall <dark/mid/bright> (L=<n>), palette <#hex ×3>.
Vertical 1080x1920, <sec>s. Photoreal documentary footage, no people, no text, no logos, no captions.
```
- 角度の言葉＝ai-drama/references/knowledge/camera-work-24.md（英語名）
- 札・紙幣は「架空の札」（本物の札の複製は撃たん＝51 の実測）
- 480p で1本試して目で見てから本番。本番は 1080p（feedback_cgi_final_1080p）

## やらん事
- 人物が出るカットを生成で埋める（顔が別人になる＝手本の写しにならん）
- 「作って」の前に撃つ・見積もり無しで撃つ
- 参照に手本の字幕が入ったコマをそのまま渡す（字が焼き付く）＝字幕の帯を消すか、字の無いコマを選ぶ

## 🔒 10/26 16:10 依頼者「差分ゼロが芯。でも考えすぎても困る。無い所は生成AIでどんどん提案してええ」
- 元が見つからん「人が出ん実写」は、待たずに**提案を出す**（見積もり付き・1カットずつ）。順＝①無料の素材（Pexels・Pixabay・Mixkit の実写＝0cr・札や工場の寄りは大体ある）→②生成（Seedance 2.5 / Kling・480p 試し→1080p）。どちらも fit で位置・色・ぼかしを手本に合わせる
- 提案の形＝「カット番号・手本の中身・候補（無料 or 生成）・見込みの差（SSIM/ΔE）・クレジット」の表。撃つのは「作って」の後

## 実測（10/26 r2 65・初回）
- 🔴 手本の縦横を先に見る（r2 は 1280x720 の横。ref_look の下書きを縦で書いて2本無駄＝15cr）。ref_look は実寸から書くように直した
- 手本のカットの**中の切り替わり**を先に数える（コマ差の山）：65 は 署名7＋シート7＋舞台5＝19コマ。生成は切り替わりごとに1本撃って、ffmpeg の trim/concat で手本のコマ数どおりに1本にする（src/hi/<番号>.mp4・H＝単位行列・clip_start 0）
- 合わせは `fit_cut.py <作業> <番号> --track 0 --color mean`（追わん・色は Lab の平均と幅だけ）。既定の2次の色の式は画素が対応せんので白く飛ぶ（0.33→見た目は×）。mean で 0.24 でも見た目は手本の色。cuts/_all.json は手で足す（fit_cut は書かん）
- 手本にすでに別カットで当たっとる実写（舞台＝hi/63）が混ざる時は、その元の続きのコマを切って足す
- 門3つ：SHOUMEI.md（「」の引用は「指示文:」のファイルと一字一句同じ・ー の行も8字以上）・DESIGN_CHECK.md（商品が無くても「対象なし」と書いて置く）・ミスの門（1080p の前に 720p/480p で1回）
- 値段：Kling 3.0 Turbo 720p 5秒＝7.5cr・1080p＝10cr（480p 無し）
