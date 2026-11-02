# テカリ（金属・つや）の作り方（11/2 手本N v3・本人「テカリとかがまだないから、そこもしっかり詰めて」）

手本の金属の字（手本N の MOTION）＝灰オリーブのクローム。**上の縁が白く光る・足元に床の橙が映り込む・体は上が明るく真ん中が暗い帯・ほんの少し柔らかい**。これを Remotion（HTML）で出す型。

## 字＝SVG フィルタ #chrome ＋ 体のグラデ（background-clip: text）
```tsx
// 一度だけ描く（Filters）
<filter id="chrome" x="-12%" y="-18%" width="124%" height="136%" colorInterpolationFilters="sRGB">
  <feGaussianBlur in="SourceAlpha" stdDeviation="5" result="bump" />               {/* 縁の丸み＝縁の光の幅 */}
  <feSpecularLighting in="bump" surfaceScale="10" specularConstant="1.3" specularExponent="22" lightingColor="#ffffff" result="st"><feDistantLight azimuth="270" elevation="28" /></feSpecularLighting>  {/* 上の縁＝白。仰角は低く（高いと平らな所まで白く飛ぶ） */}
  <feComposite in="st" in2="SourceAlpha" operator="in" result="stc" />
  <feSpecularLighting in="bump" surfaceScale="10" specularConstant="0.45" specularExponent="22" lightingColor="#ffffff" result="sl"><feDistantLight azimuth="200" elevation="30" /></feSpecularLighting>  {/* 横の縁＝弱い白 */}
  <feComposite in="sl" in2="SourceAlpha" operator="in" result="slc" />
  <feSpecularLighting in="bump" surfaceScale="10" specularConstant="2.4" specularExponent="26" lightingColor="#ffb860" result="sb"><feDistantLight azimuth="90" elevation="30" /></feSpecularLighting>   {/* 足元＝床の橙の映り込み */}
  <feComposite in="sb" in2="SourceAlpha" operator="in" result="sbc" />
  <feComposite in="SourceGraphic" in2="stc" operator="arithmetic" k2="1" k3="1" result="m1" />
  <feComposite in="m1" in2="slc" operator="arithmetic" k2="1" k3="1" result="m2" />
  <feComposite in="m2" in2="sbc" operator="arithmetic" k2="1" k3="0.9" />
</filter>
// 字の体（部屋の映り込み＝上が明るい・真ん中が暗い帯・足元は暖かい）
const Metal = { color: '#9fa396',
  backgroundImage: 'linear-gradient(180deg,#c9cdbf 0%,#d8dbcf 15%,#969a8c 38%,#878b7e 55%,#a9ada0 70%,#c9c5b0 86%,#e6c48e 100%)',
  WebkitBackgroundClip: 'text', backgroundClip: 'text', WebkitTextFillColor: 'transparent',
  filter: 'url(#chrome) blur(0.4px) drop-shadow(0 7px 7px rgba(40,35,30,0.42))' };
```
- 落とし穴：①仰角を 50° にしたら字が真っ白に飛んだ（平らな所の鏡面が 0.94^18＝33% 乗る）→ 28° ②下の橙の指数が低い（12）と体が全部黄色く染まる → 26 ③体のグラデを明るくしすぎると紙の切り抜きに見える＝手本の体の色（#9a9e90 前後）を測って合わせる
- 確かめ方：`remotion still` で手本と同じコマを出し、等倍で切り出して横に並べる（rikai/v3/tekari_v3c.jpg の型）。3 周で寄せた

## 物のつや
- **トグル（橙のカプセル）**：上に白い光の帯＝子の div（上 5%・幅 86%・高さ 40%・白→透明の縦グラデ・blur 5px）。つまみは動く時だけ `blur(1〜6px)`（速さ×0.12）＋ inset の影
- **札（橙）**：`inset 0 2px 0 rgba(255,255,255,0.55)`（上の縁の光）＋ `inset 0 14px 18px rgba(255,255,255,0.28)` ＋下に `inset 0 -8px 14px rgba(180,50,15,0.38)`
- **立方体**：上の面は `linear-gradient(155deg,#ffc2a0 0%,#ff8a5a 28%,#ff6a3c 60%,#f85a2c 100%)`（左上に光）・側面もうっすらグラデ・線は 2px
- **窓の中の床の光**：`radial-gradient(ellipse at 50% 62%, rgba(255,118,30,0.62) 0%, …, 透明 62%)` を床の下に。出す時は枠と一緒にフェード（急に足すと 1 コマ跳ぶ）
