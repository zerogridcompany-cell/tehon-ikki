# 手本の動画を写すための目の作業（tehon-ikki）

手本＝__REF__（__SEC__秒・__W__x__H__・__FPS__fps）。
これを、元の映像を YouTube 等から探して同じ所を切り、1コマもずらさずに作り直す。そのための目の作業をしてほしい。

## 見る物
- `sheets/g000.png`〜`g132.png`：1枚に12カット（左上から右へ4つ×3段）。g000 はカット 0〜11、g012 は 12〜23 …
- カットの番号と秒は `segs.txt`（番号: 始まり-終わり 秒）
- 1カットを細かく見たい時は `k/k<番号3桁>.png`（480px）。もっと見たい時は自分で `ffmpeg -ss <秒> -i ../ref/__REF__ -frames:v 1 x.png` で取ってよい（手本は ../ref/__REF__）

## 出す物：`eye/out.json`（JSON だけ）
```
{"shots":[
 {"i":番号, "t0":秒, "t1":秒,
  "kind":"live|mg|text_only|mix",
  "who":["映っとる人の名前（分かる時だけ・分からんなら ?）"],
  "what":"何の場面か（英語）：例 Elon Musk interview, 60 Minutes 2012, sitting in chair, rubbing forehead",
  "source_guess":"元の映像の候補（番組名・局・年・イベント・YouTube の題名になりそうな言葉）。分からんなら ?",
  "search":["YouTube で元を探す英語の検索語 3つ（強い順）"],
  "screen_text":"画面に焼き込まれとる局の字・札（KXAN・CNBC・SQUAWK BOX 等）そのまま",
  "edit":"手本で足されとる加工（左右反転・拡大・白黒・ぼかし・光・VHS風・テレビの枠に入れる・揺れ・速さ）",
  "same_as":"前のカットと同じ元の映像の続きなら、その番号。違うなら null",
  "caption":"このカットに乗っとる字そのまま（無ければ null）"}
],
"captions_style":{"font":"一番近い書体名","weight":数字,"italic":true/false,"color":"#hex","glow":"光の有無と強さ","size_pct":字の高さ÷画面の高さ,"pos":"位置"},
"mg":[{"i":番号,"what":"MG の中身（緑の数字の並び・大きな字に写真をはめる 等）と作り方の見立て"}]
}
```
推測で埋めない。分からん所は "?"。有名人の名前は顔と状況から確かな時だけ書く。
