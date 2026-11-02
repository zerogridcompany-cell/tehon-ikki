// 12 Comic book（アメコミのコマ）— 手本 手本M 12：生成りの紙に黒枠のコマ2つ。上のコマ＝橙の集中線と網点。
// 吹き出し「WHOOSH!」が f1 で 0.25 → f2 0.9 → f3〜4 で 1.12（行き過ぎ）→ f7 で 1.0 に弾む。下のコマ（青・網点）が f9〜11 で右から滑り込み、f12 で 3% 行き過ぎて f16 で止まる
// SVG：集中線＝黒い細い三角を放射・網点＝pattern の丸・字＝Impact の斜体に黒の縁（paint-order stroke）
import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export type ComicBookProps = {width?: number; height?: number; shout?: string; caption?: string; line?: string; colors?: Partial<typeof DEF>; fontFamily?: string};
const DEF = {paper: '#f8f2e2', ink: '#16100c', burst0: '#ffe56e', burst1: '#ffb43c', burst2: '#f58a1f', dot: '#d8661a', shout: '#e6212b', panel2: '#4ab8f4', dot2: '#2a8fd6', caption: '#ffd43b', line: '#ffffff'};
const C0 = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const W12_ComicBook: React.FC<ComicBookProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H), u = S / 410;
  const C = {...DEF, ...(p.colors || {})}; const FF = p.fontFamily ?? 'Impact, "Arial Black", system-ui, sans-serif';
  const bw = 2.8 * u;
  const p1 = {x: 0.045 * W, y: 0.05 * H, w: 0.91 * W, h: Math.min(0.52 * H, 0.78 * W)}, p2 = {x: 0.045 * W, y: 0.05 * H + Math.min(0.52 * H, 0.78 * W) + 0.03 * H, w: 0.91 * W, h: Math.min(0.40 * H, 0.52 * W)};
  const cx = p1.x + p1.w / 2, cy = p1.y + p1.h * 0.47;
  const rays = [] as React.ReactNode[]; const NR = 30, rot = f * 0.35;
  for (let i = 0; i < NR; i++) { const a = ((i / NR) * 360 + rot) * (Math.PI / 180), da = (0.012 + 0.01 * ((i * 37) % 5) / 4) * Math.PI; const r0 = 0.26 * Math.min(p1.w, p1.h) * (0.85 + 0.3 * (((i * 53) % 7) / 6)), r1 = Math.hypot(p1.w, p1.h);
    rays.push(<path key={i} d={`M${cx + Math.cos(a) * r0} ${cy + Math.sin(a) * r0}L${cx + Math.cos(a - da) * r1} ${cy + Math.sin(a - da) * r1}L${cx + Math.cos(a + da) * r1} ${cy + Math.sin(a + da) * r1}Z`} fill={C.ink} />); }
  const pop = interpolate(f, [0.9, 1, 2, 3, 4, 5, 6, 7], [0, 0.25, 0.9, 1.12, 1.13, 1.05, 0.99, 1.0], C0);
  const slide = interpolate(f, [8, 9, 10, 11, 12, 13, 14, 15, 16], [1.05, 0.62, 0.25, 0.02, -0.035, -0.025, -0.008, 0.004, 0], C0);
  const bwid = 0.86 * p1.w, bh = 0.25 * p1.w, bx = cx - bwid / 2, by = p1.y + p1.h * 0.42 - bh / 2;
  const shout = p.shout ?? 'WHOOSH!';
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: C.paper}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <radialGradient id="w12b" cx={cx} cy={cy} r={0.75 * Math.max(p1.w, p1.h)} gradientUnits="userSpaceOnUse"><stop offset="0" stopColor={C.burst0} /><stop offset="0.28" stopColor={C.burst0} /><stop offset="0.55" stopColor={C.burst1} /><stop offset="1" stopColor={C.burst2} /></radialGradient>
          <radialGradient id="w12m" cx={cx} cy={cy} r={0.7 * Math.max(p1.w, p1.h)} gradientUnits="userSpaceOnUse"><stop offset="0.25" stopColor="#000" /><stop offset="0.75" stopColor="#fff" /></radialGradient>
          <pattern id="w12d" width={7 * u} height={7 * u} patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx={3.5 * u} cy={3.5 * u} r={1.35 * u} fill={C.dot} /></pattern>
          <pattern id="w12e" width={6.5 * u} height={6.5 * u} patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx={3.25 * u} cy={3.25 * u} r={1.25 * u} fill={C.dot2} /></pattern>
          <mask id="w12k"><rect x={p1.x} y={p1.y} width={p1.w} height={p1.h} fill="url(#w12m)" /></mask>
          <clipPath id="w12c"><rect x={p1.x} y={p1.y} width={p1.w} height={p1.h} /></clipPath>
        </defs>
        <g clipPath="url(#w12c)">
          <rect x={p1.x} y={p1.y} width={p1.w} height={p1.h} fill="url(#w12b)" />
          <rect x={p1.x} y={p1.y} width={p1.w} height={p1.h} fill="url(#w12d)" mask="url(#w12k)" opacity={0.85} />
          {rays}
        </g>
        <rect x={p1.x} y={p1.y} width={p1.w} height={p1.h} fill="none" stroke={C.ink} strokeWidth={bw} />
        {pop > 0 && <g transform={`translate(${cx} ${by + bh / 2}) rotate(-2.5) scale(${pop}) translate(${-cx} ${-(by + bh / 2)})`}>
          <path d={`M${bx + 0.30 * bwid} ${by + bh - 2}L${bx + 0.22 * bwid} ${by + bh + 0.42 * bh}L${bx + 0.45 * bwid} ${by + bh - 2}Z`} fill="#fff" stroke={C.ink} strokeWidth={bw * 0.9} strokeLinejoin="round" />
          <rect x={bx} y={by} width={bwid} height={bh} rx={0.2 * bh} fill="#fff" stroke={C.ink} strokeWidth={bw * 0.9} />
          <path d={`M${bx + 0.31 * bwid} ${by + bh - bw}L${bx + 0.44 * bwid} ${by + bh - bw}`} stroke="#fff" strokeWidth={bw * 1.6} />
          <text x={cx} y={by + bh * 0.53} textAnchor="middle" dominantBaseline="central" fontFamily={FF} fontStyle="italic" fontSize={bh * 0.66} fill={C.shout} stroke={C.ink} strokeWidth={bw * 0.75} paintOrder="stroke" transform={`skewX(-6)`} style={{transformBox: 'fill-box', transformOrigin: 'center'}} textLength={bwid * 0.88} lengthAdjust="spacingAndGlyphs">{shout}</text>
        </g>}
        <g transform={`translate(${slide * W} 0)`}>
          <rect x={p2.x} y={p2.y} width={p2.w} height={p2.h} fill={C.panel2} />
          <rect x={p2.x} y={p2.y} width={p2.w} height={p2.h} fill="url(#w12e)" opacity={0.7} />
          <rect x={p2.x} y={p2.y} width={p2.w} height={p2.h} fill="none" stroke={C.ink} strokeWidth={bw} />
          <rect x={p2.x + 0.04 * p2.w} y={p2.y + 0.09 * p2.h} width={0.36 * p2.w} height={0.17 * p2.h} fill={C.caption} stroke={C.ink} strokeWidth={bw * 0.8} />
          <text x={p2.x + 0.22 * p2.w} y={p2.y + 0.177 * p2.h} textAnchor="middle" dominantBaseline="central" fontFamily={FF} fontStyle="italic" fontSize={0.085 * p2.h} fill={C.ink} textLength={0.30 * p2.w} lengthAdjust="spacingAndGlyphs">{p.caption ?? 'MEANWHILE...'}</text>
          <text x={p2.x + 0.95 * p2.w} y={p2.y + 0.70 * p2.h} textAnchor="end" dominantBaseline="central" fontFamily={FF} fontStyle="italic" fontSize={0.25 * p2.h} fill={C.line} stroke={C.ink} strokeWidth={bw * 0.9} paintOrder="stroke" textLength={0.78 * p2.w} lengthAdjust="spacingAndGlyphs">{p.line ?? 'CLAUDE CODE!'}</text>
        </g>
      </svg>
    </div>
  );
};
