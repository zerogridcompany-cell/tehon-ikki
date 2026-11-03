# 光の当て方・光らせ方（11/3 依頼者「光らせ方・文字のテカリ・光沢・グロウが分からんなら実物を拾って真似する」）

実物 YouTube 14 本を落として測った（~/research/hikari-ref-20261103/・測り＝gamen.py measure --step 12・断面は `prof`＝画面幅の 2% 刻みで山=1・地=0）。出所は全部未承認（YouTube の作り方動画）。数字は「実物から測った値」と「うちで試作して測った値」を分けて書く。

## 0. 先に結論（いちばん効く 5 つ）
1. **光は 2 段の山**：芯（幅の 10〜14% で 50% に落ちる）＋ 長い裾（幅の 28〜48% 先でもまだ山の 15〜25% 残る）。1 本のガウスだと「ボール」に見える。実物は裾が長い。
2. **縁を作らん**：`radial-gradient` は 0%→100% まで滑らかに alpha を落とす。途中に「円の縁」が見えたら裾の段が足りん（試作で内側の円が見えた）。
3. **文字のグロウは 4〜5 段の text-shadow**（白い芯＋色の外が倍々の半径）。外の 10% 地点は **字の高さの約 0.5 倍**。
4. **テカリ＝上が明るい／真ん中が暗い帯／下は暖かい**の縦グラデ＋斜め（約 25° 傾き）の細い白い帯を `background-position` で走らせる。
5. **暗い地の帯（バンディング）は粒 1〜3% で消す**（地より下に敷く。字の上には乗せん）。

## 1. 暗い地に暖色の放射状の光（spotlight / radial glow）
### 実物（測った）
| 実物 | URL | 光の中心 | 山 L | 色 a/b | 断面（画面幅比の半径→山比） | 50% まで | 備考 |
|---|---|---|---|---|---|---|---|
| Gold Text Animation（SOVEREIGN の天井スポット） | youtu.be/dMTEth6eCp0 | 上中央 (50,7%) | 55 | +1/+22 | 2%:.86 6%:.74 10%:.56 14%:.37 20%:.24 28%:.23 36%:.25 48%:.15 | 11.3% | 周辺減光 0.07・にじみ 108px |
| Gold orange abstract（金の粒の帯） | youtu.be/iF19lWWG6UM | 下中央 (52,70%) | 82〜88 | +8/+23 | 2%:.95 6%:.68 10%:.48 14%:.37 20%:.29 28%:.25 36%:.22 48%:.18 | 9.4〜13.6% | にじみ 130〜250px |
| Volumetric Light（BX_DahOOg2k） | youtu.be/BX_DahOOg2k | 中央〜上 | 95 | +3/+4 | 2%:.91 6%:.85 10%:.83 14%:.77 20%:.60 28%:.51 36%:.49 | 約 35〜48% | 白い光・裾がとても長い（ライトシャフト） |
| aflow identity film（暗い青） | youtu.be/xBZzVNi_4Xw | 球の周り | 99 | +32/−56 | 山が飽和＝ほぼ平らで 36% でも .88 | 48% 超 | 暖色でなく青。色は a/b で寄せる |
- **読み方**：暖色（a≈+1〜+9・b≈+22〜+24＝橙〜金）で 50% 半径 9〜14%・2 段目の裾 15〜25% が幅の 28〜48% まで続く。暗い地の山 L は 55（控えめな光）〜 88（金の帯）。
- **周辺減光** 0.07〜0.24（隅が中心の 70〜90% 残る＝真っ黒に落とさん）。
### 作り方（層）
1. 地：`#0a0604` 付近（L≈3〜10・暖黒）。
2. 芯：`radial-gradient(circle 150px at 50% 12%, rgba(255,200,120,.55) 0, rgba(255,170,80,.28) 45%, rgba(255,150,60,0) 100%)`（半径＝画面幅の約 12%）。
3. 裾：`radial-gradient(circle 620px at 50% 12%, rgba(255,150,70,.30) 0, rgba(255,120,40,.12) 40%, rgba(255,100,30,0) 100%)`（半径＝幅の約 48%）。2 と 3 を **加算（`mix-blend-mode: screen`）**。
4. 二重のぼかしの代わりに `filter: blur(40px)` を 2 と同じ層に足すと縁が消える（canvas なら blur を 2 回＝σ 20 と σ 80）。
5. 帯消し：地の下に feTurbulence の粒（opacity .03〜.05）。字の上には乗せん。
6. 落とし穴：`circle` を明示（既定の ellipse は縦横比で伸びる）／stop を増やしても帯は消えん＝粒で消す（toolmia・css-tricks Grainy Gradients の説明）。
### 試作（うち・Chrome 1280x720・test/t.html）
上の 2+3 で 山 L130・r=100px:.47 150px:.24 200px:.19 300px:.12 450px:.07。**手本は 200〜450px の所が .22〜.25 まで残る＝裾の alpha をもう 1.5〜2 倍**に（`.30→.45`・`.12→.2`）して寄せる。
### Remotion
`<AbsoluteFill style={{background:'#0a0604'}}>` の下に 2 つの `<div style={{position:'absolute',inset:0,background:'radial-gradient(...)',mixBlendMode:'screen'}}/>`。光の中心の動きは `interpolate(frame,…)` で `at X% Y%` を差し替える（山の明るさも同じ式で）。

## 2. 文字のグロウ（text glow）
### 実物（測った）
| 実物 | URL | 芯 | 外の色 | 縁からの距離→(明るさ−地)/(芯−地) | 50%/25%/10% まで |
|---|---|---|---|---|---|
| Creative Glow Text Reveal（緑ネオン CREA） | youtu.be/jZ2R-tEHUDI | 白寄り黄緑 RGB(187,240,132) | 緑 | 1px:.62 3px:.42 6px:.29 10px:.19 15px:.14 20px:.11 30px:.06 45px:.03（字高 43px） | 2px / 8px / 22px＝字高の 0.05 / 0.19 / 0.51 倍 |
| Gold Text（Dominique 筆文字） | youtu.be/dMTEth6eCp0 | 金 RGB(242,199,84) | 暗い橙（縁+8〜16px で RGB(30,18,4)） | 1-3px:.41 3-6:.27 6-10:.16 10-16:.08 16-24:.03 | 2px / 6px / 12px（幅 854px の 0.2/0.7/1.4%） |
| Glow Text（P6zWrfcXk0k）：Color Control＋Drop Shadow を複製 | 説明のみ | 字 | Drop Shadow の色を Color Control に紐付け | 距離 0・ソフトネス 10 を複製して重ねる（複製の度に大きく） | — |
| Shiny Glowing Bevel（wrEw_6VyebM） | 説明のみ | 縁の細い白 | Venetian Blinds で縁だけ抜き Glow を 2 回 | 強度↑・半径↑・しきい値を調整 | — |
- **読み方**：芯は白〜明るい色 → 縁から 3px で 40% → 字高の 0.2 倍で 25% → 0.5 倍で 10%。外の色は **芯より彩度が高く暗い**（金なら橙）。
### 作り方（層・AE）
- 内側の光（inner）＝字そのものを明るい色（#fff3d6）に。外側の光（outer）＝**Glow 2 段**：①半径 小（字高の 0.1 倍）・強度 1.0 ②半径 大（字高の 0.5 倍・L_fha の例は半径 100）・強度 0.5。または Drop Shadow（距離 0・ソフトネス 10→20→40）を複製（P6z）。
### CSS／Remotion（試作で確認）
```tsx
<div style={{fontSize:120,color:'#fff3d6',
 textShadow:'0 0 6px #fff3d6,0 0 14px #ffb347,0 0 30px #ff9a2e,0 0 60px rgba(255,140,40,.7),0 0 120px rgba(255,120,30,.4)'}}>光る文字</div>
```
半径は倍々（6→14→30→60→120）。字高 120px で試作→縁から 3px:.65・10px:.32・30px:.12・60px:.05。**手本は 6px:.45 相当で近いが外（0.5h＝60px）がやや足りん**＝最後の 2 段の alpha を .7→.85・.4→.55。`filter: drop-shadow()` は字の形でなく箱の透けで効くので、字ごとに動かす時は text-shadow のほうが軽い。mix-blend-mode: screen で別の光の層に重ねると外が自然に混ざる。
### 落とし穴
text-shadow の blur が大きい（120px 以上）と低スペックで重い。アニメ中は 3 段に減らす。白飛びさせると色が消える＝芯の色を #fff でなく #fff3d6（暖色）に。

## 3. 文字のテカリ・光沢（specular / sheen / light sweep）
### 実物
| 実物 | URL | 作り方（読み取った設定） |
|---|---|---|
| ICON SHINE（Instagram ロゴ） | youtu.be/Mr_SpvZkPrk | CC Light Sweep。**Direction 25°**・Shape＝Smooth か Sharp・Width／Sweep Intensity／Edge Intensity を調整。Center を左の外→右の外へ 1 秒で動かす。測り：帯は斜め 25°傾き・ロゴ幅の約 12〜15% |
| Light Sweep（Ross） | youtu.be/_U0HHLX4EZE | Fill を暗い灰に→CC Light Sweep：**Edge Thickness 0（ベベルを消す）・Edge Intensity ≈100・Sweep Intensity ≈40・Width 50・Shape Sharp**。Center の横だけ動かす |
| CC Light Sweep Text | youtu.be/c6tFiuUuBCE | 字の左外の Center にキー → 右外に。F9（Easy Ease） |
| Gold（SOVEREIGN / Dominique） | youtu.be/dMTEth6eCp0 | 金字の体は暖色の縦グラデ＋上のスポットが字を撫でる |
- **読み方（本人の字＝上が白い縁・体が暗い帯・足元が暖かい）は tekari.md が正**（feSpecularLighting の 3 灯）。ここは「走る帯」を足す。
### CSS／Remotion
```tsx
const t = frame/ (fps*1.0);                       // 1 秒で走る
const x = interpolate(t,[0,1],[-40,140],{easing:Easing.inOut(Easing.cubic),extrapolateRight:'clamp'});
<div style={{fontSize:120,fontWeight:800,color:'transparent',WebkitBackgroundClip:'text',backgroundClip:'text',
 backgroundImage:`linear-gradient(105deg,transparent 40%,rgba(255,255,255,.95) 50%,transparent 60%),
  linear-gradient(180deg,#fff2c8 0%,#e8b85a 45%,#8a5a1a 55%,#f0c878 100%)`,
 backgroundSize:'300% 100%,100% 100%',backgroundPosition:`${x}% 0,0 0`,backgroundRepeat:'no-repeat'}}>GOLD</div>
```
- 帯は 105°（AE の 25° と同じ傾き）・白 .95・幅＝全体の 20%（40%→60%）。縦グラデは **上 #fff2c8 → 45% #e8b85a → 55% #8a5a1a（暗い帯）→ 下 #f0c878**＝金属の映り込み。
- 落とし穴：`background-position` の%は「はみ出し分」基準なので x が思った所に来ん＝px で `calc` するか、`backgroundSize` を固定して実測。帯が字の外に出る時は `opacity` を絞る。反射の 1 点（ハイライト）は ::after の白い点（blur 2px）で。

## 4. 縁の光（rim light）・光の線（light streak / trail）
### 実物
| 実物 | URL | 測り・作り方 |
|---|---|---|
| Golden Light Streaks（k2W4HOy9-AQ） | youtu.be/k2W4HOy9-AQ | 右上から流れる金の筋。山 L90〜96・色 a/b +11/+15・隅が同じ明るさ（周辺減光 0.85〜1.0）・断面は d50 が幅の 29〜48%＝**幅広い光の束** |
| Cinematic Gradients（L_fhA1FmXaI） | youtu.be/L_fhA1FmXaI | ①Layer Style Gradient Overlay（暗い色＋さらに暗い色・明るい色を側面に）②**Bevel & Emboss：Depth 下げ・Size≈50・明るい側を上へ**＝縁の光 ③Tritone→Noise 12%（カラー粒なし）④光の線＝白ストローク・Trim Paths・**Taper 開始/終了 100%**⑤**Dodge and Blur→Glow 半径 100→もう 1 つ Glow 半径を大きく→CC Radial Fast Blur 60・Brightest**⑥調整レイヤーに Glow＋Posterize |
| aflow（xBZzVNi_4Xw） | youtu.be/xBZzVNi_4Xw | 球・ガラスの縁だけ白く光る（暗い青の地・山 99）・にじみ 128〜148px・色は青 (a+30/b−56) |
| Volumetric Light 2 分 | youtu.be/BX_DahOOg2k | 光源から放射する筋（ライトシャフト）。裾の長い白（上表の断面） |
### 層の構成（CSS／Remotion）
- **縁の光（rim）**：`box-shadow: inset 0 1px 0 rgba(255,255,255,.55), inset 0 0 18px rgba(255,255,255,.12)`（上の縁 1px＋内側）。球は `radial-gradient(circle at 30% 25%, #fff 0, rgba(255,255,255,0) 30%)` を `mix-blend-mode: screen`。
- **光の線（streak）**：細い `div`（高さ 2px）に `linear-gradient(90deg,transparent,#fff,transparent)`＋`filter: blur(1px) drop-shadow(0 0 8px #ffb347) drop-shadow(0 0 24px #ff9a2e)`。進む時は `scaleX` と `translateX` を同じ式で・先端だけ明るく（尾は alpha 0 へ）。
- **ブルーム（three.js）**：`new UnrealBloomPass(resolution, strength 1.5, radius 0.4, threshold 0.85)`（公式の例）。暗い絵なら threshold を下げ、強さ 0〜3・半径 0〜1 の範囲で。Remotion では @remotion/three のシーンを EffectComposer で包む（Remotion 専用の値は見つからず）。

## 5. 光のにじみの断面（実物から測った「中心からの落ち方」）
| 実物 | 50% | 25% 付近 | 10%（幅の％） | 裾の残り |
|---|---|---|---|---|
| dMTE スポット | 幅の 11% | 20% 地点で .24 | 48% でも .15 | 15〜25% が 28〜48% まで |
| iF19 金の帯 | 9〜14% | 20% で .29 | 48% で .18 | 18〜25% |
| 字のグロウ（緑ネオン） | 字高 0.05 | 字高 0.19 | 字高 0.51 | 0.7 倍で .06 |
| 字のグロウ（金筆文字） | 2px | 6px | 12px | 24px で .03 |
- **中心・50%・10% の距離の比＝ 1 : 3 〜 5 : 10 〜 ∞**（ガウスなら 1 : 1.8 のところ、実物は 10% がずっと遠い）。→ 光は**ガウス 1 本でなく、芯のガウスと大きい裾の足し算**。
- 使い方：試作の断面を同じ手順（gamen.py measure の prof）で測り、上の表の 50%・20%・36% の山比に寄せる。

## 取れなかった物・次の道
- 動画の取得失敗＝oRNTBzOo3tE（Dark Volumetric Cinematic Intro）・3h27HxfA7Lg（Hyper Cinematic Luxury Text）・9TmspFPijQ0（金属テキスト）＝形式エラー。次＝`yt-dlp -f 18` か `--cookies-from-browser`。
- X・TikTok・GitHub（remotion glow・UnrealBloomPass の実プロジェクト）・中韓（Bilibili・小红书）は未回収（検索回数の上限）。次＝site:x.com の「glow text AE」とハッシュタグ #motiongraphics。
- Light Sweep の帯の幅・強さの正確な数値化（今は画面録画の中のプレビューで 25° と幅 12〜15% のみ）。次＝書き出し済みの完成品（ロゴ ID 動画）の 1 コマで測る。
