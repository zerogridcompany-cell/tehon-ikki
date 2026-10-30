// Static＝テレビの砂嵐（feTurbulence・毎コマ種を替える）。51 の Scenes.tsx Static の汎用版
// 何をする：箱の中に白黒のざらざらを描き、毎コマ模様を替える。holdEvery コマに1回は前のコマのまま（手本の差 0 のコマ）
// props：
//   f, box [x,y,w,h], rx(角丸)        砂嵐の窓。51＝[385,95,1150,880]・rx 80（テレビの画面の形）
//   freq(0.2)・octaves(1)              粒の大きさ。0.2＝粒 3〜4px（1920 幅）
//   slope(3.6)・icpt([-1.36,-1.35,-1.29])  濃淡の幅（標準偏差）と平均の色。51＝幅 40〜48・平均 (92,95,111)
//   holdEvery(6)                       n コマに1回は前の模様のまま（0＝止めん）
//   opacity(0.92)・vignette({cx,cy,r,stop,alpha})  窓の縁の暗がり。51＝中心 50%,42%・r 62%・0.62 から 0.32
// 51 で効いた数字：砂嵐は画素では合わん（乱数）＝粒の大きさ・濃淡の幅・平均・毎コマの差で合わせた＝58〜60秒の動き 手本どおり・ΔE 3.8→1.2（SSIM は 0.45〜0.56 のまま＝作らん所）
// 測る道具：mg_measure.py noise <手本> f0 f1 --box x0,y0,x1,y1＝粒の大きさ（自己相関の半値幅）・濃淡の幅（標準偏差）・平均の色・毎コマの差（0 のコマの間隔＝holdEvery）
//   うちの書き出しにも同じ物をかけて、粒→幅→平均の順に freq・slope・icpt を寄せる
import React from 'react';

export const Static: React.FC<{f: number; box: [number, number, number, number]; rx?: number; freq?: number; octaves?: number; slope?: number; icpt?: [number, number, number]; holdEvery?: number; opacity?: number;
  vignette?: {cx?: string; cy?: string; r?: string; stop?: number; alpha?: number} | null; seedBase?: number; id?: string}> = ({f, box, rx = 0, freq = 0.2, octaves = 1, slope = 3.6, icpt = [-1.36, -1.35, -1.29], holdEvery = 6, opacity = 0.92, vignette = {}, seedBase = 0, id = 'st'}) => {
  const k = holdEvery > 0 && f % holdEvery === 0 ? f - 1 : f;
  const [x, y, w, h] = box;
  return (
    <svg width={x + w} height={y + h} style={{position: 'absolute', left: 0, top: 0, opacity, overflow: 'visible'}}>
      <filter id={`${id}n${k}`} x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={octaves} seed={(k + seedBase) % 997} />
        <feColorMatrix type="saturate" values="0" />
        <feComponentTransfer>
          <feFuncR type="linear" slope={slope} intercept={icpt[0]} /><feFuncG type="linear" slope={slope} intercept={icpt[1]} /><feFuncB type="linear" slope={slope} intercept={icpt[2]} /><feFuncA type="linear" slope={0} intercept={1} />
        </feComponentTransfer>
      </filter>
      <rect x={x} y={y} width={w} height={h} rx={rx} filter={`url(#${id}n${k})`} />
      {vignette && (
        <>
          <radialGradient id={`${id}v`} cx={vignette.cx ?? '50%'} cy={vignette.cy ?? '42%'} r={vignette.r ?? '62%'}><stop offset={vignette.stop ?? 0.62} stopColor="#000" stopOpacity="0" /><stop offset="1" stopColor="#000" stopOpacity={vignette.alpha ?? 0.32} /></radialGradient>
          <rect x={x} y={y} width={w} height={h} rx={rx} fill={`url(#${id}v)`} />
        </>
      )}
    </svg>
  );
};
