// Paper＝共通の紙（1枚の紙の絵）＋点の網。紙のコラージュの場面の一番下に敷く（51 の Scenes.tsx Paper・DotSharp の汎用版）
// 何をする：全部の紙の場面に「同じ紙が1枚、動かずに」敷かれとる手本を写す。上に乗る物（札・人の影・字）は切り抜いて別の層で動かす
// props：
//   img?      紙の絵（public からの道）。Codex で描き直した紙のうち手本に一番 SSIM が高い1枚。無ければ color の無地
//   color     紙の地の色（既定 #ece9e4＝51 の紙の中央値）
//   dots?     {period, r, color, phase:[x,y], blend}＝点の網。🔴 SVG の pattern で描く（CSS の background は位相が崩れる・r2 で 0.04→0.88）。紙の絵に点が描き込んであれば付けん
//   sharpK?   紙の絵にだけアンシャープ（ぼかし σ との差を k 倍足す）。51 は 0 が最良（濃くするとしわまで強まって ui 0.832→0.814）
//   id        filter・pattern の id（同じ画面に2枚出す時だけ替える）
// 51 で効いた数字：紙を場面ごとに描き直すのをやめて1枚にした＝SSIM 0.654→0.682（紙の場面 +0.1〜0.2）。手本の紙は 9秒と55秒の隅で SSIM 0.963
//   点の網＝24px おき・rgba(90,80,80,.22)・半径 1.6〜2.2px（手本の紙の点の網の周期は 38px の所もあった＝手本ごとに測る）
// 測る道具：
//   紙の色＝手本の紙の場面の四隅（物の無い所）の中央値
//   点の周期と位相＝紙の場面の1コマを灰にして FFT の山（周期）→ その周期でずらした相関の一番高い所（位相）。51/tools/dot_phase.py・dot_grid.py（51 の道は決め打ち＝REF を差し替えて使う）
//   同じ紙かどうか＝離れた2つの紙の場面の四隅の SSIM（0.95 以上なら「1枚の紙」）→ mg_measure.py corners
import React from 'react';
import {Img, staticFile, useVideoConfig} from 'remotion';

export type Dots = {period: number; r: number; color?: string; phase?: [number, number]; blend?: string};
export const Paper: React.FC<{img?: string; color?: string; dots?: Dots; sharpK?: number; sigma?: number; id?: string}> = ({img, color = '#ece9e4', dots, sharpK = 0, sigma = 6, id = 'paper'}) => {
  const {width: W, height: H} = useVideoConfig();
  return (
    <div style={{position: 'absolute', inset: 0, background: color}}>
      {img && sharpK > 0 && (
        <svg width={0} height={0} style={{position: 'absolute'}}>
          <filter id={`${id}_sharp`} colorInterpolationFilters="sRGB" x={0} y={0} width="100%" height="100%">
            <feGaussianBlur in="SourceGraphic" stdDeviation={sigma} edgeMode="duplicate" result="b" />
            <feComposite in="SourceGraphic" in2="b" operator="arithmetic" k1={0} k2={1 + sharpK} k3={-sharpK} k4={0} />
          </filter>
        </svg>
      )}
      {img && <Img src={staticFile(img)} style={{position: 'absolute', inset: 0, width: W, height: H, filter: sharpK > 0 ? `url(#${id}_sharp)` : undefined}} />}
      {dots && (
        <svg width={W} height={H} style={{position: 'absolute', inset: 0, mixBlendMode: (dots.blend ?? 'multiply') as any}}>
          <pattern id={`${id}_dots`} x={dots.phase?.[0] ?? 0} y={dots.phase?.[1] ?? 0} width={dots.period} height={dots.period} patternUnits="userSpaceOnUse">
            <circle cx={dots.period / 2} cy={dots.period / 2} r={dots.r} fill={dots.color ?? 'rgba(90,80,80,0.22)'} />
          </pattern>
          <rect x={0} y={0} width={W} height={H} fill={`url(#${id}_dots)`} />
        </svg>
      )}
    </div>
  );
};
