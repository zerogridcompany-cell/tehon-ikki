# カメラ・描き分け・見た目の道具（51 から移した物・2026-10-25）

元＝`~/research/mane-20261021/air/items/51/tools/`。51 の決め打ちの道（items/51・ref/51.mp4・shots.json・cam.json）は外して、
1つ目の引数を `<作業>`（`ref/*.mp4`・`eye/out.json`・`proj/src/green.json`・`caps.json` がある所）か mp4 にした。共通の小物は `tk_common.py`。
各ファイルの頭に「何をする・使い方・入れる物と出す物・効いた数字（51）・採る条件」を書いてある。

## どの段で・どの順で使うか（waza.md の段に合わせて）

| 段 | 順 | 道具 | いつ使うか |
|---|---|---|---|
| 1 目と測り | 1 | `hold.py <作業>` | 手本の止めコマ（3コマ打ち・25→30fps の重ね）を全部出す。止めが 5% 以上なら hold.json を使う（下の「hold」） |
| 1 | 2 | `zoom_meas.py <作業> f0 f1` | 寄り・引きがある「らしい」カットで、本当に寄っとるか・どのコマから寄るか |
| 1 | 3 | `cam_chain.py <作業> f0 f1 --out x.json` | 長い振り・横流し・寄りのカット（カットの中だけ・🔴カットをまたぐと警告が出る） |
| 1 | 4 | `whip_fit.py <作業> f0 f1 左 右` | 横振り（ぶれて流れる数コマ）。左右の止まったコマで D を測る |
| 3 合わせる | 5 | （green_fit の後）`cam_chain.py <作業> f0 f1 --plate <id> --write` | ECC が追えん（mode が init・mid）長いカメラの絵だけ。M を鎖で書き換える |
| 3 | 6 | `pad_mirror.py <作業> --auto` | 絵の外（黒）が画面に出るコマがある絵だけ（Green.tsx に「pad」を足してから効く） |
| 3 | 7 | `variant_align.py <作業> <id> v1.png …` → `flow_variants.py <作業> --only <id>` | 絵の中で人・水・煙が動く場面に、Codex で中身違いを 4〜6枚描かせた時。無い絵は今まで通り flow_tx.py |
| 3 | 8 | `fx_extend.py <作業> <id> <n> --write` | 手本の切り替えが溶けで、前の場面が溶けの間も動いとる所だけ |
| 4 書き出し後に測る | 9 | `seg_ssim.py`・`wave_top.py`・`persec.py --vs`・`scene_ecc.py`・`sharp_cmp.py` | どこが低いか・何が違うか（全部読むだけ・軽い） |
| 5 見た目 | 10 | `fx_smooth.py <作業> <id> --sigma s` | persec の d の比（うち÷手本）が 1.5 以上の fx の絵 |
| 5 | 11 | `fx_grade.py <作業> <id>` | fx の絵の色がコマで手本からずれる所（look_shot の前） |
| 5 | 12 | `lum_frames.py <作業> <id> --write` | 比の幅 0.1 以上＝コマで明るさが動く絵（タイムラプス・点滅）。Green.tsx に「lum」を足してから効く |
| 5 | 13 | `lab_grade.py` | green_fit を通さん絵（使い回し・寄りの絵）だけ |
| 5 | 14 | （grain → look_shot の後）`cap_sigma.py <作業> <うち.mp4>` | 字幕の語のずれとぼけ。Main.tsx に「字の縁」を足してから効く |
| 5 | 最後 | cut_tune.py（今まで通り最後） | 🔴色・明るさを変えたら切り替えの強さも変わる |

## 毎回「測って効く時だけ採る」
- 1つ直すごとに、その範囲だけ書き出して比べる：`npx remotion render src/index.ts Main ../try.mp4 --frames=<f0>-<f1> --gl=angle --concurrency=3` → `seg_ssim.py <作業> try.mp4 <f0> <f1> --off <f0>`。前と後を並べて上がった物だけ残す（51 はこれで +0.01〜0.03 を確かめてから全体に入れた）
- 線（51 の実測から）：SSIM が 0.002 より下がらん・色は ΔE が 0.5 以上下がる・動きは mane_check の「動きの波」かカットが上がる。🔴 描き分けと粒は SSIM と動きの取り合い（SSIM が少し下がって動きが上がる）＝両方の数字を見せて選ぶ
- fx の絵を作り直したら（cam_chain・flow_variants・fx_extend）、fx_smooth・fx_grade はやり直す（元の控えは arai/fx_bak・fx_orig＝いつもそこから作るので何度回しても同じ。🔴 作り直した時は控えを消してから）
- 重い物（flow_variants・cam_chain --plate の後の flow_tx）は `run.sh guard` を通してから・同時2本まで

## Remotion 側に要る足し（tsx は親が組み込む・ここは案）

### pad（pad_mirror.py）
Green.tsx の Plate 型に `pad?: number`。置くだけの `<Img>`（seq でない方）を：
```tsx
const P = p.pad ?? 0;
<Img src={staticFile(P ? `green/pad/${id}.png` : `green/${id}.png`)}
  style={{position: 'absolute', left: 0, top: 0, width: p.w + 2 * P, height: p.h + 2 * P, transformOrigin: '0 0',
    transform: `matrix(${M[0]}, ${M[3]}, ${M[1]}, ${M[4]}, ${M[2] - P * (M[0] + M[1])}, ${M[5] - P * (M[3] + M[4])})`, ...}} />
```
（広げた絵の画素 x＝元の u＋P なので、平行移動から P·(a＋c)・P·(b＋d) を引く）。flow_tx.py の place も pad の絵で置くと fx の縁の黒も消える（今は borderValue=0）。

### lum（lum_frames.py）
Plate 型に `lum?: Record<string, number>`。置くだけの `<Img>` の filter に `brightness(${p.lum?.[String(f)] ?? 1})` を足す（blur の後・粒の前）。seq の fx の絵は焼き込み済みでないので同じく足す。

### hold（hold.py）
`assets/proj/src/hold.json` に `[]` を置き、Green.tsx と Cards.tsx の頭で：
```tsx
import HOLD from './hold.json';
const f0 = useCurrentFrame(); const fh = (HOLD as number[])[f0] ?? f0;
// 同じ絵（同じカット）の中だけ止める：entry を f0 で探して、fh が p.f0 より前なら f0 のまま
const f = entry && fh >= entry[1].f0 ? fh : f0;
```
土台の動画（base.mp4＝実写）には使わん（手本のままの止めが入っとる）。字幕（caps）にも使わん。

### whip（whip_fit.py）
`proj/src/whip.json`＝`[{"f0","f1","D","left":"<id>","right":"<id>","rows":[{"f","s","L"}]}]`（left・right は左右の止まったコマを描いた一枚絵の id）。Green.tsx に1つ部品を足す：
```tsx
// 地図＝左の絵を 0・右の絵を D に置いた幅 W+D の帯を、s だけ左へ流す。ぶれは横だけ（σ＝L×0.29・縦 0）
<svg width={0} height={0}><filter id={`wh${f}`}><feGaussianBlur stdDeviation={`${r.L * 0.29} 0`} /></filter></svg>
<div style={{position: 'absolute', left: -r.s, top: 0, width: W + w.D, height: H, filter: `url(#wh${f})`}}>
  <Img src={staticFile(`green/${w.left}.png`)} style={{position: 'absolute', left: 0, width: W, height: H}} />
  <Img src={staticFile(`green/${w.right}.png`)} style={{position: 'absolute', left: w.D, width: W, height: H}} />
</div>
```
🔴 2枚の重ね溶け＋全方向の blur にせん（51：0.59〜0.78→0.87〜0.89 はこの形で出た）。

### 字の縁（cap_sigma.py）
caps.json の語に `"eb": σ`（gain が --min-gain 以上の語だけ）。Main.tsx の `<text>` に CSS の blur() は SVG の子に効かん＝SVG の filter で：
```tsx
{c.eb ? <filter id={`eb${c.i}`}><feGaussianBlur stdDeviation={c.eb} /></filter> : null}
<text ... filter={c.eb ? `url(#eb${c.i})` : undefined}>
```
🔴 先に cap_sigma の「ずれ dx,dy」を見る。±2px 以上ずれとる語は位置（txt_build）を直してから σ を測り直す（ずれたままだと、ぼかすほど差が下がって σ が大きく出る）。

### 溶け（fx_extend.py）
fx_extend で f1 を伸ばした絵（"ext": n）は次の絵と重なる。今の Green.tsx は先に見つかった1枚だけ出す＝重なる所は：
```tsx
const entries = Object.entries(GREEN).filter(([, p]) => f >= p.f0 && f <= p.f1);  // 全部出す
// 伸ばした分のコマは上に重ねて薄くする：op = 1 − (f − (p.f1 − p.ext)) / (p.ext + 1)
```
の形にする（下に次の絵・上に伸ばした前の絵）。溶けの長さは手本の切り替えのコマ数に合わせる（51：1263 から6コマ）。

### Tsx の足しが要らん物
- cam_chain.py --plate --write：green.json の M を書き換えるだけ（Green.tsx はそのまま読む）
- flow_variants.py：fx/<id>/<f>.jpg と seq を書く＝今の seq の読み方のまま
- fx_smooth・fx_grade・lab_grade・variant_align：絵を書き換えるだけ

## r2 で回した数字（10/25・r2_v12・測るだけ・直してない）
- wave_top：相関 0.6828（mane_check の 0.683 と同じ）・一番下げとるのは 17.7s・47.9s・57.6s（手本は大きく動く・うちはほぼ 0）
- hold：2290 コマ中 止め 584（25.5%）・1コマの止め 422 か所＝25→30fps の重ねらしい・止め2の塊 48
- persec（300〜420）：うち÷手本 d 0.72・sm 0.70・sh 0.91＝止まりすぎ側（fx_smooth は要らん・粒か hold の候補）
- scene_ecc（42・67・95・110）：cc 0.95〜0.99・ずれ 3px 以内・倍率 1% 以内＝直す候補なし
- cap_sigma：230 語中 ずれ ±2px 以上 161 語・σ が測る幅の上の端（4.2）136 語＝1語ずつのぼかしより先に字の位置か光の当て直し
- lum_frames：w19 だけ比 0.94〜1.68（光るコマ）・ほかは幅 0.07 以下
