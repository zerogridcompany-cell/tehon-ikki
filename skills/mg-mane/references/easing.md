# easing（動きの曲線）の名前と使い分け（11/3・手本＝@uiuxmanuel「Every ball covers the same distance in 1.4s — the only thing that changes is the easing」・~/research/tehon-me/ugoki_hint）

依頼者 11/3「最初速いのに後ゆっくり＝高級感。この動きを極めたらいろんな動きが付けられる。名前と道具が無いなら入れる」。
手本の 8 本（同じ距離・同じ 1.4 秒）＝Linear／Ease in／Ease out／Ease in-out／Overshoot／Elastic／Bounce／Steps。

## 使い分け（手本の説明文そのまま＝決まり）
| 動きの役 | 曲線 | ease.ts | 感じ |
|---|---|---|---|
| **画面に出てくる**（arriving） | **Ease Out** | `EASE.out`（bezier 0.16,1,0.3,1）／`expo_out k`／`pow_out n=3` | 最初速く・後ゆっくり＝高級感の正体 |
| **画面から消える**（leaving） | **Ease In** | `EASE.in`（bezier 0.7,0,0.84,0）／`pow_in` | ゆっくり始まって速く去る |
| **画面の中を移動**（moving around） | **Ease In-Out** | `EASE.inout`（bezier 0.65,0,0.35,1）／`pow_inout` | 滑らかに出て滑らかに止まる |
| **回る・ループ・読み込みの輪** | **Linear** | `EASE.linear` | 一定。ここだけ線形でええ |
| **味を付ける**（attitude） | **Overshoot**（控えめ・1 本に 1〜2 回） | `EASE.overshoot`（back_out c=1.70158）／`spring` z 0.5〜0.7 | 行き過ぎて戻る（やりすぎると安っぽい） |
| 弾む・ビヨン | Elastic／Bounce | `EASE.elastic`（a,p）／`EASE.bounce`／`spring` z<0.3 | ゲーム・遊び・通知の pop |
| 段で動く | Steps | `EASE.steps n` | 数字の回り・フリップ・レトロ |

- 🔴 **線形で出す・線形で止める＝カクつき**（nameraka.md）。出入りに linear を使わん。線形は「回る・ループ」だけ
- 🔴 止まる時は 0 にピタッと置かん＝out の尾（expo）か spring の尾でサブピクセルまで収まる
- 手本の写しは曲線を当てる（`scripts/kiseki.py`→`ease_fit.py`＝bezier／expo_out／pow／back_out／spring／bounce）。新作は上の表で役から決める
- 使い方：`import {EASE, tw} from './ease'` → `const u = tw(f, 30, 45, EASE.out)`（30〜45 コマで 0→1）／`kfAt(keys, f)` の keys.json の `ease` に `{"kind":"bezier","x1":0.16,"y1":1,"x2":0.3,"y2":1}`
- 絵コンテ（ekonte.json）の `ugoki` には役の名前で書く（例「札が右から **ease out** で入る・消えるは **ease in**・題は **overshoot** 控えめ」）＝係は表で曲線に直す
