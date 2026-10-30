import React from 'react';
import {AbsoluteFill, useCurrentFrame, getInputProps} from 'remotion';
import SHAPE from './logo_shape.json';
import TRACK from './logo_track.json';
import LOOK from './look.json';

// 締めのロゴ（140・141）：形＝手本の一番くっきりしたコマの輪郭（logo_shape.json）・大きさと位置と明るさ＝手本から1コマずつ測った値（logo_track.json）
type T = {f: number; s: number | null; cx?: number; cy?: number; op?: number; bg?: number};
export const LOGO_F0 = (TRACK as T[])[0].f;
export const Logo: React.FC = () => {
  const f = useCurrentFrame() + LOGO_F0;
  const t = (TRACK as T[]).find((x) => x.f === f);
  // --props '{"look":{…}}' で値を上書きして試す（tools/mg_opt.py が手本と比べて一番合う値を探す）
  const L = {...(LOOK as any), ...((getInputProps() as any).look || {})};
  if (!t || !t.s) return <AbsoluteFill style={{backgroundColor: L.logoBg}} />;
  const k = (SHAPE.core_w * t.s) / 1000;
  return (
    <AbsoluteFill style={{backgroundColor: L.logoBg}}>
      {/* 地の明るさ＝手本で測った bg（8＝logoBg そのまま・0＝黒）。締めで黒へ落ちる所を写す */}
      <AbsoluteFill style={{backgroundColor: '#000', opacity: t.bg == null ? 0 : Math.max(0, Math.min(1, 1 - t.bg / 8))}} />
      <svg width={1280} height={720} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="halo" x="-150%" y="-150%" width="400%" height="400%"><feGaussianBlur stdDeviation={L.haloBig / k} /><feComponentTransfer><feFuncA type="linear" slope={L.haloBigGain} /></feComponentTransfer></filter>
          <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation={L.haloSmall / k} /><feComponentTransfer><feFuncA type="linear" slope={L.haloSmallGain} /></feComponentTransfer></filter>
          <filter id="soft"><feGaussianBlur stdDeviation={L.logoSoft / k} /></filter>
          <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={f} /><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.5 0" /></filter>
        </defs>
        <g opacity={t.op ?? 1} transform={`translate(${t.cx} ${t.cy}) scale(${k})`}>
          <g filter="url(#halo)" opacity={L.haloBigA}>{SHAPE.paths.map((p, i) => <path key={i} d={p} fill="#ffffff" />)}</g>
          <g filter="url(#glow)" opacity={L.haloSmallA}>{SHAPE.paths.map((p, i) => <path key={i} d={p} fill="#ffffff" />)}</g>
          <g filter="url(#soft)">{SHAPE.paths.map((p, i) => <path key={i} d={p} fill={L.logoColor} />)}</g>
        </g>
        <rect width={1280} height={720} filter="url(#grain)" opacity={L.logoGrain} />
      </svg>
    </AbsoluteFill>
  );
};
