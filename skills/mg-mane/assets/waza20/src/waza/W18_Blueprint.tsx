// 18 Blueprint（設計図 → 立体）— 手本 手本M 18：青い方眼紙に白い線の歯車3つが f1〜5 で描かれ（止め f5〜11）、f12〜18 で光の縦線が左→右へ走る（f14 2%・f15 15%・f16 50%・f17 88%）。
// 線が通った所から灰色の金属の立体の歯車に替わり、右下の札が DRAFT → RENDER。あとは歯車が少しずつ倒れて（見える厚み）ゆっくり回る
// SVG：歯車の形を作る関数・描き込みは pathLength=1 の dashoffset・立体は同じ形を奥から 12 枚ずらして重ねる・境目は clipPath
import React from 'react';
import {interpolate, Easing, useCurrentFrame, useVideoConfig} from 'remotion';

export type BlueprintProps = {width?: number; height?: number; colors?: Partial<typeof DEF>; code?: string; fontFamily?: string};
const DEF = {paper: '#0b4a8a', minor: '#1b5a9b', major: '#2b6cad', line: '#eaf4ff', face: '#8f9bb0', faceHi: '#aab5c6', side: '#4d607a', hole: '#2f3f55', scan: '#bfe6ff'};
const C0 = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const gear = (r: number, n: number, depth: number) => { const pts: string[] = []; const pitch = (Math.PI * 2) / n, rr = r - depth;
  for (let i = 0; i < n; i++) { const a = i * pitch; for (const [da, rad] of [[-0.5, rr], [-0.28, rr], [-0.16, r], [0.16, r], [0.28, rr]] as [number, number][]) { const t = a + da * pitch; pts.push(`${(Math.cos(t) * rad).toFixed(2)} ${(Math.sin(t) * rad).toFixed(2)}`); } }
  return `M${pts.join('L')}Z`; };

export const W18_Blueprint: React.FC<BlueprintProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H);
  const C = {...DEF, ...(p.colors || {})}; const FF = p.fontFamily ?? 'ui-monospace, Menlo, "SF Mono", monospace';
  const G = [{x: 0.40 * W, y: 0.43 * H, r: 0.215 * S, n: 16, hole: 0.27, dir: 1}, {x: 0.665 * W, y: 0.53 * H, r: 0.13 * S, n: 10, hole: 0.3, dir: -1.6}, {x: 0.42 * W, y: 0.635 * H, r: 0.10 * S, n: 8, hole: 0.3, dir: 2}];
  const draw = interpolate(f, [0.6, 5], [0, 1], {...C0, easing: Easing.out(Easing.cubic)});
  const scanX = interpolate(f, [12, 14, 15, 16, 17, 18], [-0.06, 0.02, 0.15, 0.5, 0.88, 1.08], C0) * W;
  const scanOp = interpolate(f, [11.5, 13, 17.5, 18.5], [0, 1, 1, 0], C0);
  const tilt = interpolate(f, [16, 32, 75], [0.05, 0.9, 1.0], {...C0, easing: Easing.inOut(Easing.sin)});   // f36 で約 50° 倒れて見える
  const spin = Math.max(0, f - 15) * 2.0;   // 2°/コマ
  const thick = 0.07 * S, NL = 12, minor = 0.025 * W;
  const solid = G.map((g, i) => {
    const path = gear(g.r, g.n, 0.16 * g.r); const sy = Math.cos(tilt), off = thick * Math.sin(tilt);
    const tf = (k: number) => `translate(${g.x} ${g.y + off * (1 - k / (NL - 1))}) rotate(-18) scale(1 ${sy}) rotate(${spin * g.dir})`;
    return (<g key={i}>
      {Array.from({length: NL}, (_, k) => <path key={k} d={path} transform={tf(k)} fill={k === NL - 1 ? 'url(#w18f)' : C.side} stroke={k === NL - 1 ? C.faceHi : 'none'} strokeWidth={1} />)}
      <g transform={tf(NL - 1)}><circle r={g.r * g.hole} fill={C.hole} /><circle r={g.r * g.hole} fill="none" stroke={C.side} strokeWidth={2} /></g>
    </g>);
  });
  const lw = 2.4 * (S / 1080);
  const draft = G.map((g, i) => (<g key={i} transform={`translate(${g.x} ${g.y})`}>
    <path d={gear(g.r, g.n, 0.16 * g.r)} fill="none" stroke={C.line} strokeWidth={lw} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - draw} strokeLinejoin="round" />
    <circle r={g.r * g.hole} fill="none" stroke={C.line} strokeWidth={lw} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - draw} transform="rotate(-90)" />
  </g>));
  const stage = scanX > 0.62 * W ? 'RENDER' : 'DRAFT';
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: C.paper}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <pattern id="w18m" width={minor} height={minor} patternUnits="userSpaceOnUse"><path d={`M${minor} 0L0 0 0 ${minor}`} fill="none" stroke={C.minor} strokeWidth={1} /></pattern>
          <pattern id="w18M" width={minor * 5} height={minor * 5} patternUnits="userSpaceOnUse"><rect width={minor * 5} height={minor * 5} fill="url(#w18m)" /><path d={`M${minor * 5} 0L0 0 0 ${minor * 5}`} fill="none" stroke={C.major} strokeWidth={1.6} /></pattern>
          <linearGradient id="w18f" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor={C.faceHi} /><stop offset="1" stopColor={C.face} /></linearGradient>
          <linearGradient id="w18s" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor={C.scan} stopOpacity={0} /><stop offset="0.42" stopColor={C.scan} stopOpacity={0.55} /><stop offset="0.5" stopColor="#ffffff" stopOpacity={1} /><stop offset="0.58" stopColor={C.scan} stopOpacity={0.55} /><stop offset="1" stopColor={C.scan} stopOpacity={0} /></linearGradient>
          <radialGradient id="w18v" cx="50%" cy="50%" r="75%"><stop offset="0.6" stopColor="#000" stopOpacity={0} /><stop offset="1" stopColor="#001a3a" stopOpacity={0.45} /></radialGradient>
          <clipPath id="w18L"><rect x={0} y={0} width={Math.max(0, scanX)} height={H} /></clipPath>
          <clipPath id="w18R"><rect x={Math.max(0, scanX)} y={0} width={W} height={H} /></clipPath>
        </defs>
        <rect width={W} height={H} fill="url(#w18M)" />
        <g clipPath="url(#w18R)">{draft}</g>
        <g clipPath="url(#w18L)" style={{filter: `drop-shadow(0 ${0.012 * S}px ${0.014 * S}px rgba(0,10,30,0.45))`}}>{solid}</g>
        <rect x={scanX - 0.035 * W} y={0} width={0.07 * W} height={H} fill="url(#w18s)" opacity={scanOp} />
        <rect width={W} height={H} fill="url(#w18v)" />
      </svg>
      <div style={{position: 'absolute', right: 0.05 * W, bottom: 0.04 * H, fontFamily: FF, fontWeight: 700, fontSize: 0.026 * W, letterSpacing: '0.22em', color: C.line, opacity: 0.88}}>{p.code ?? 'DWG A-01'} · {stage}</div>
    </div>
  );
};
