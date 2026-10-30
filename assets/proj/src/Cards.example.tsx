import React from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';

// 字・光だけのカット（13 後半・18・20・73・74・94）。数字は手本のコマを測った値（shirabe/進み.md 10/25「カード」）。
// 字幕の語（into・this・anything.）は R2.tsx の caps が上に乗る。ここは地と光と「They Said」だけ。
const fontH = delayRender('R2TNR');
new FontFace('R2TNR', `url(${staticFile('fonts/TNR-Bold.ttf')})`, {weight: '700'}).load()
  .then((ff) => { (document.fonts as any).add(ff); continueRender(fontH); }).catch(() => continueRender(fontH));

// ガウスの光（中心 cx,cy・強さ amp・半径 sg＝画面の幅と高さで割った距離）を放射のグラデーションに
const halo = (cx: number, cy: number, base: number[], amp: number, sg: number) => {
  const stops = Array.from({length: 21}, (_, k) => {
    const d = (k / 20) * 0.5;
    const v = amp * Math.exp(-(d * d) / (2 * sg * sg));
    return `rgb(${base.map((b) => Math.round(b + v)).join(',')}) ${k * 5}%`;
  });
  return `radial-gradient(ellipse 640px 360px at ${cx}px ${cy}px, ${stops.join(', ')})`;
};

type Card = {f0: number; f1: number; el: React.ReactNode};
// 点の網（73）：手本の点の中心＝x,y とも 22.2＋5.3333 おき（mg/w2 で当てた）。SVG の模様で位相をそのまま置く
const DOT_R = 0.8, DOT_C = 30;
const dots = (
  <svg width={1280} height={720} style={{position: 'absolute', inset: 0}}>
    <defs>
      <pattern id="r2dots" width={16 / 3} height={16 / 3} patternUnits="userSpaceOnUse" x={22.2 - 8 / 3} y={22.2 - 8 / 3}>
        <circle cx={8 / 3} cy={8 / 3} r={DOT_R} fill={`rgb(${DOT_C},${DOT_C},${DOT_C})`} />
      </pattern>
    </defs>
    <rect width={1280} height={720} fill="rgb(253,253,253)" />
    <rect width={1280} height={720} fill="url(#r2dots)" />
  </svg>
);
const theySaid = (color: string) => (
  <svg width={1280} height={720} style={{position: 'absolute', inset: 0}}>
    <text x={0} y={0} fill={color} transform="translate(150.59 433.88) scale(1.0222 1)"
      style={{fontFamily: 'R2TNR', fontWeight: 700, fontSize: 228.44}}>They Said</text>
  </svg>
);
const CARDS: Card[] = [
  {f0: 80, f1: 82, el: <AbsoluteFill style={{background: 'radial-gradient(ellipse farthest-corner at 640px 360px, rgb(253,253,253) 0%, rgb(253,253,253) 55%, rgb(72,55,42) 100%)'}} />},
  {f0: 154, f1: 156, el: <AbsoluteFill style={{background: halo(586, 347, [9, 11, 10], 34.6, 0.1047)}} />},
  {f0: 162, f1: 166, el: <AbsoluteFill style={{background: halo(653, 344, [9, 11, 10], 63.2, 0.1168)}} />},
  // 25（242-254）：暗い紫の地＋字のまわりの光（コマごとにガウスを当てた値）。字は caps、ロケットの光跡と追いかけの枠はまだ
  {f0: 242, f1: 244, el: <AbsoluteFill style={{background: halo(604, 374, [28, 25, 33], 35.5, 0.157)}} />},
  {f0: 245, f1: 246, el: <AbsoluteFill style={{background: halo(567, 393, [27, 23, 31], 11.5, 0.232)}} />},
  {f0: 247, f1: 247, el: <AbsoluteFill style={{background: halo(629, 364, [28, 25, 33], 117.7, 0.172)}} />},
  {f0: 248, f1: 248, el: <AbsoluteFill style={{background: halo(626, 370, [19, 16, 25], 188.9, 0.235)}} />},
  {f0: 249, f1: 254, el: <AbsoluteFill style={{background: halo(616, 370, [24, 21, 29], 103.2, 0.219)}} />},
  {f0: 1000, f1: 1003, el: <AbsoluteFill>{dots}{theySaid('rgb(3,3,3)')}</AbsoluteFill>},
  {f0: 1004, f1: 1007, el: <AbsoluteFill style={{backgroundColor: '#000'}}>{theySaid('rgb(249,249,249)')}</AbsoluteFill>},
  {f0: 1312, f1: 1312, el: <AbsoluteFill style={{backgroundColor: 'rgb(250,250,214)'}} />},
  {f0: 1313, f1: 1317, el: <AbsoluteFill style={{backgroundColor: 'rgb(250,249,246)'}} />},
];

// 110 の左上の札「10,000,000 ft² / Tesla Gigafactory, TX」＝Rajdhani（Bold・Medium）。濃さは手本の 1604〜1645 コマを測った値
const fontR = delayRender('R2Raj');
Promise.all([
  new FontFace('R2RajB', `url(${staticFile('fonts/Rajdhani-Bold.ttf')})`).load(),
  new FontFace('R2RajM', `url(${staticFile('fonts/Rajdhani-Medium.ttf')})`).load(),
]).then((fs) => { fs.forEach((ff) => (document.fonts as any).add(ff)); continueRender(fontR); }).catch(() => continueRender(fontR));
const LABEL_F0 = 1604;
const LABEL_OP = [0, 0.4, 0.4, 0.6, 0.73, 0.83, 0.93, 0.94, 0.95, 0.96, 0.96, 0.98, 0.98, 0.99, ...Array(19).fill(1), 0.99, 0.99, 0.89, 0.79, 0.79, 0.67, 0.39, 0];
const Label: React.FC<{op: number}> = ({op}) => (
  <svg width={1280} height={720} style={{position: 'absolute', inset: 0, opacity: op}}>
    <rect x={87.5} y={52} width={2} height={668} fill="rgba(255,255,255,0.22)" />
    <text x={0} y={0} fill="rgb(238,238,238)" transform="translate(100.14 76) scale(0.855 1)" style={{fontFamily: 'R2RajB', fontSize: 43.55}}>10,000,000 ft</text>
    <text x={301.86} y={59} fill="rgb(238,238,238)" style={{fontFamily: 'R2RajB', fontSize: 26.44}}>2</text>
    <text x={0} y={0} fill="rgb(215,215,215)" transform="translate(105.67 107) scale(0.877 1)" style={{fontFamily: 'R2RajM', fontSize: 23.33}}>Tesla Gigafactory, TX</text>
  </svg>
);

export const Cards: React.FC = () => {
  const f = useCurrentFrame();
  const c = CARDS.find((c) => f >= c.f0 && f <= c.f1);
  const k = f - LABEL_F0;
  const lop = k >= 0 && k < LABEL_OP.length ? LABEL_OP[k] : 0;
  return <>{c ? c.el : null}{lop > 0 ? <Label op={lop} /> : null}</>;
};
