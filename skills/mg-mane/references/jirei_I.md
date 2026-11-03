# 実例I＝tehonI（Google Maps 風 3D 地図の飛行 MG・モニター撮りの手本・11/3）

手本＝TikTok @tehonI 7700928759863495968（21.9秒・1080x1920）。**作り手が DaVinci Resolve で組んだ MG をモニターで再生し、部屋を手持ちで撮った動画**＝画面の中身が手本。Barcelona の 3D 地図（白い街・青い経路・緑の案内札・店の札・地下鉄の断面・公園・ペグマン・AR の矢印）→ 黒地のロックアップ→クレジット。語り（女声 手本の女声）11句・曲は打ち込みのドラム/ベース（Shazam 不明）。
作業＝~/research/tehon-me/tehonI（決め.md＝Fable が段0 を見て 11 場面の表と 3D の作り方を書いた・係 Opus が A〜D）。

## 1. モニター撮りの手本は「画面だけ」を起こしてから写す
- `scripts/quad_white.py <撮った.mp4> <out.json>`＝白い画面のコマで4辺を直線で当てて4隅＋上の景色の位相相関で「カメラが止まっとるか」（tehonI は手持ち＝最大 13px 流れた）
- `scripts/rectify_monitor.py <撮った.mp4> <出す.mp4> [fps] [--quad …]`＝景色（画面の外・TikTok の字幕の板や中身が変わる小窓は mask で外す）を LK＋homography で毎コマ追い、白い画面のコマでは4辺を直に当て、追いとの差 6px 超は捨てて savgol(21) で滑らかに → 1920x1080 に warp（LANCZOS4）・音は元のまま・yuv420p bt709
- 🔴 直の測りを 0.5/0.5 で混ぜたら 1 コマ 186px の外れが混ざった＝外れを捨ててから補正を内挿する
- 色・鋭さはモニター撮りの分だけ甘い＝色は起こした板の色に合わせる（真の色は追わん）・鋭さは追わん。IG 版（4倍ビットレート）があっても 30fps vs 29.97 で ±1 コマずれる＝測りには混ぜん（見る用だけ）
- 図鑑（miru）はこの板でカットを 2 本としか見ん（ブレの切り替え・場面の継ぎ目は拾えん）＝場面の表は親が 2 コマおき（`scripts/sheet.py`）で読んで決め.md に書く

## 2. 3D の MG（街の飛行）の写し方＝Remotion＋three.js
- **カメラの 2D の影を測る**：`scripts/cam2d.py <mp4> <out.json>`＝隣のコマの相似（拡大 s・回り rot・画面中心のずれ tx/ty・流れの中央値）を 8 コマごとの表に。手本とうちの表は `scripts/cam_cmp.py <手本.json> <うち.json> [区間]` で場面ごとの相関（log s・rot・tx/ty）と流れの量の比
- **係の組み方（proj/src/rk/）**：場面 A〜E を別の原点（x=0,3000,6000…）に置いた街・カメラ＝場面ごとの鍵 [f, 的xyz, 距離r, 俯角°, 方位°, fov] を PCHIP で連続（cam.ts）・街は seed 固定の手続き（city.ts：道・建物・木・車・公園・経路の帯 ribbonGeo・地下鉄の穴・ペグマン・AR の矢印）・速い所は RenderTarget→放射状ブレ・UI の札とロックアップは 2D の層
- **数字の道**：v2 波 0.807 → 直し.md（カメラの量と形を場面ごとに cam2d の 8 コマ表で指定）→ v3 波 0.869・止まり 21→8・S08 0.89・S06 量 ×0.54→0.76。残りの弱み＝S03（物の pop と点の進み・波 0.20）・S07（公園の飛行の量）・S11（終わりの出方）・S02（ピン→点の回りのギザ ×2.4）
- 🔴 hakaru の「動きの量」は差の平均＝街の格子のコントラストが高いと同じ動きでも大きく出る（道は手本と同じほぼ白・遠くは霧）

## 3. 語り（英語の女声）
- ElevenLabs の直 API は 401 payment_issue（請求の未払い）で撃てん日があった＝Higgsfield CLI `elevenlabs_v4`（`--dialogue '[{"voice_type":"preset","voice_id":"<UUID>","text":"…"}]'`・1句 約0.23cr）。🔴 while read の中で呼ぶ時は `</dev/null`（stdin を食って次の行が消える）
- 声の選び方＝候補を 1 句ずつ撃って f0 の中央・長さ・重心を手本の同じ句と並べる（9 声で 2cr）。tehonI＝手本 手本の女声 157Hz → Isla 161Hz（7367e919-3069-5a0b-939e-dfb1c0fd91b4）・Vera 154Hz
- 句は 1 本ずつ撃って、手本の whisper の語の頭に置く。枠（次の句の頭 −0.12s）に収まらん句だけ atempo ≤1.25。書き起こし（whisper-cli）で 11/11 一致を確かめて oto/vo.wav
- 撃つ前の照合＝oto/vo/SHOUMEI.md（shippai-shoumei init→check OK）

## 4. 作り手の見せ方（本人の問い「Claude が編集ソフトを使っとる？」）
- 映っとるのは「Claude が素材（ショット）をコードで作り、人が DaVinci Resolve Studio 21 で並べる」型（Resolve のビン＝01 Shots／02 MG layers／03 Lock-up／04 End card／05 VO（女声）／06 Music stems／07 SFX stems／08 Reference）＝うちの型（Remotion で素材→ffmpeg で組む）と同じ。プロンプトは「Maps」とコメントした人に DM＝未取得
