// Scribble＝手描きの線が描き順どおりに引かれていく（strokeDashoffset）。51 の parts/Extra.tsx Scribble の汎用版
// 何をする：strokes（SVG の d）を drawDur コマで描き切る。線ごとに stagger だけ遅れる。筆のがたつき＝feTurbulence＋feDisplacementMap
//   段の表で色・濃さ・置き方を替える（黒地の白い線 → 紙の地で灰色に残る → 次の物の上で小さく、など）
// props：
//   f・f0・f1（消えるコマ・含まん）・drawDur(4)・over(1.4)・stagger(0.06)＝線 i の進み＝clamp(p·over − i·stagger)
//   strokes＝[d…]・width0(36)・widthStep(2)（線ごとに細く）・cap('round')
//   colors＝[[コマ, 色]…]・ops＝[[コマ, 濃さ]…]・tf＝[[コマ, "translate(x,y) scale(s)"]…]
//   rough＝{freq(0.04), scale(14), seed(3)} | null
// 51 で効いた数字：1499〜1510 の 11コマ・4コマで描き切る・黒地 #d8d8d8→紙の地 #8d8b8a・濃さ 1→0.7→0.35・目の上で 0.55 倍
// 測る道具：線の形＝手本の描き切ったコマを Codex に下敷きで渡して「同じ線を SVG の path で」書かせる（か、線の画素を細線化して手で path に）
//   描く速さ＝mg_measure.py area <手本> f0 f1 --dark/明るさのしきい＝線の画素の割合が毎コマどれだけ増えるか（drawDur と stagger を合わせる）
import React from 'react';
import {useVideoConfig} from 'remotion';
import {cl, stepAt} from './common';

export const Scribble: React.FC<{f: number; f0: number; f1: number; strokes: string[]; drawDur?: number; over?: number; stagger?: number; width0?: number; widthStep?: number; cap?: string;
  colors?: [number, string][]; ops?: [number, number][]; tf?: [number, string][]; rough?: {freq?: number; scale?: number; seed?: number} | null; id?: string}> = (P) => {
  const {width: W, height: H} = useVideoConfig();
  const {f, f0, f1} = P;
  if (f < f0 || f >= f1) return null;
  const p = cl((f - f0) / (P.drawDur ?? 4));
  const color = stepAt(P.colors, f) ?? '#d8d8d8';
  const op = stepAt(P.ops, f) ?? 1;
  const tf = stepAt(P.tf, f);
  const rough = P.rough === null ? null : {freq: 0.04, scale: 14, seed: 3, ...(P.rough ?? {})};
  const id = P.id ?? 'scr';
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: op}}>
      {rough && <filter id={`${id}r`}><feTurbulence baseFrequency={rough.freq} numOctaves={2} seed={rough.seed} /><feDisplacementMap in="SourceGraphic" scale={rough.scale} /></filter>}
      <g transform={tf}>
        {P.strokes.map((d, i) => (
          <path key={i} d={d} fill="none" stroke={color} strokeWidth={Math.max(1, (P.width0 ?? 36) - i * (P.widthStep ?? 2))} strokeLinecap={(P.cap ?? 'round') as any}
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - cl(p * (P.over ?? 1.4) - i * (P.stagger ?? 0.06))} style={{filter: rough ? `url(#${id}r)` : undefined}} />
        ))}
      </g>
    </svg>
  );
};
