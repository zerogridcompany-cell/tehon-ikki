// 07 Kinetic type（字が動いて場面が替わる）— 手本 tehonM 07：MAKE（黒地に朱）→ IT（朱地に黒）→ MOVE（生成りに黒）。
// 測ったコマ：MAKE f0〜8（f0→4 で 0.94→1.0 に膨らむ）／f9〜11 で朱の板が左から右へ（覆い 5%→62%→100%）／IT は f11 で 0.80→f13.5 で 1.0（f15 で 1.03 戻って f17 で 1.0）
// ／f22〜24 で生成りの板が上から（覆い 26%→92%→100%）・MOVE は板と一緒に落ちて f25〜26 で +5% 行き過ぎて f28 で止まる。後ろに同じ字の線だけの行が上下に並び、ゆっくり上へ流れる
// SVG の text：本文字は textLength で横幅 94% に合わせる（短い語は伸ばさん）・線の行は stroke だけ
import React, {useMemo} from 'react';
import {interpolate, Easing, useCurrentFrame, useVideoConfig} from 'remotion';

export type KineticScene = {word: string; bg: string; fg: string; line: string};
export type KineticTypeProps = {width?: number; height?: number; scenes?: KineticScene[]; fontFamily?: string; fontWeight?: number; starts?: number[]};
const DEF_SCENES: KineticScene[] = [
  {word: 'MAKE', bg: '#100f0d', fg: '#ff4a2a', line: '#6a2418'},
  {word: 'IT', bg: '#fd4c2d', fg: '#100f0f', line: '#b02a10'},
  {word: 'MOVE', bg: '#efebe4', fg: '#111111', line: '#bfb8ad'},
];
const C01 = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const W07_KineticType: React.FC<KineticTypeProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height;
  const scenes = p.scenes ?? DEF_SCENES;
  const FF = p.fontFamily ?? 'system-ui, -apple-system, "Arial Black", Helvetica, sans-serif'; const FW = p.fontWeight ?? 900;
  const starts = p.starts ?? scenes.map((_, i) => (i === 0 ? 0 : i === 1 ? 9 : 22 + (i - 2) * 13));
  const sizes = useMemo(() => {
    const cv = document.createElement('canvas').getContext('2d')!;
    return scenes.map((s) => { const fs = Math.min((0.94 * W) / (s.word.length * 0.62), 0.54 * W, s.word.length >= 3 ? 0.235 * W : 1e9); cv.font = `${FW} ${fs}px ${FF}`; const nat = cv.measureText(s.word).width; return {fs, stretch: nat > 0.6 * W ? 0.94 * W : nat > 0.94 * W ? 0.94 * W : 0, nat}; });
  }, [W, FF, FW, scenes.map((s) => s.word).join('|')]);
  // いまの場面と、上に重なってくる次の場面
  let cur = 0; for (let i = 1; i < scenes.length; i++) if (f >= starts[i] + 2) cur = i;   // 板が覆い切った（頭から2コマ）ら、その場面が「いま」
  const layer = (i: number, local: number, clip: string | undefined, dy: number) => {
    const s = scenes[i], z = sizes[i];
    let sc = 1;
    if (i === 0) sc = interpolate(local, [0, 4, 9], [0.94, 1.0, 1.015], {...C01, easing: Easing.out(Easing.cubic)});
    else if (i % 2 === 1) sc = interpolate(local, [2, 4.5, 6, 8], [0.8, 1.0, 1.03, 1.0], {...C01, easing: Easing.out(Easing.quad)});
    const pitch = z.fs * 0.86, drift = (f * 0.004 * H) % pitch, rows = Math.ceil(H / pitch) + 2;
    const lines = [] as React.ReactNode[];
    for (let r = -rows; r <= rows; r++) { if (r === 0) continue; lines.push(<text key={r} x={W / 2} y={H / 2 + r * pitch - drift + dy} textAnchor="middle" dominantBaseline="central" fontFamily={FF} fontWeight={FW} fontSize={z.fs} fill="none" stroke={s.line} strokeWidth={Math.max(2, z.fs * 0.016)} {...(z.stretch ? {textLength: z.stretch, lengthAdjust: 'spacingAndGlyphs'} : {})}>{s.word}</text>); }
    return (
      <svg key={i} width={W} height={H} style={{position: 'absolute', inset: 0, clipPath: clip}}>
        <rect width={W} height={H} fill={s.bg} />
        {lines}
        <g transform={`translate(${W / 2} ${H / 2 + dy}) scale(${sc}) translate(${-W / 2} ${-H / 2})`}>
          <text x={W / 2} y={H / 2} textAnchor="middle" dominantBaseline="central" fontFamily={FF} fontWeight={FW} fontSize={z.fs} fill={s.fg} {...(z.stretch ? {textLength: z.stretch, lengthAdjust: 'spacingAndGlyphs'} : {})}>{s.word}</text>
        </g>
      </svg>
    );
  };
  const out = [layer(cur, f - starts[cur], undefined, cur >= 2 && cur % 2 === 0 ? interpolate(f - starts[cur], [0, 1, 2, 3, 4, 5, 6], [-0.40, -0.15, 0, 0.05, 0.05, 0.02, 0], C01) * H : 0)];
  const nx = cur + 1;
  if (nx < scenes.length) {
    const tl = f - starts[nx];   // 次の場面の頭まで何コマか（負）
    if (nx % 2 === 1 && tl > -1.4) { const cov = interpolate(tl, [-0.3, 0, 1, 2], [0, 0.05, 0.62, 1], C01); out.push(layer(nx, tl, `inset(0 ${(1 - cov) * 100}% 0 0)`, 0)); }
    if (nx % 2 === 0 && tl > -1.4) { const cov = interpolate(tl, [-0.4, 0, 1, 2], [0, 0.26, 0.92, 1], C01); out.push(layer(nx, tl, `inset(0 0 ${(1 - cov) * 100}% 0)`, interpolate(tl, [0, 1, 2], [-0.40, -0.15, 0], C01) * H)); }
  }
  return <div style={{position: 'relative', width: W, height: H, overflow: 'hidden'}}>{out}</div>;
};
