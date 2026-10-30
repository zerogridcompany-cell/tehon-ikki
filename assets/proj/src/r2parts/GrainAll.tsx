import React from 'react';
import {useCurrentFrame} from 'remotion';
import GA from './grain_all.json';
// 層の上から重ねる粒（ロゴ・3D など、カットのファイルに粒を足せん所・r2 141）。overlay で重ねる＝明るい所ほど強く出る（手本のロゴの上の粒）
type R = {f0: number; f1: number; amt: number};
export const GrainAll: React.FC = () => {
  const f = useCurrentFrame();
  const r = (GA as R[]).find((x) => f >= x.f0 && f <= x.f1);
  if (!r) return null;
  return (
    <svg width={1280} height={720} style={{position: 'absolute', inset: 0, mixBlendMode: 'overlay', opacity: r.amt}}>
      <filter id={`ga${f}`} x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={1} seed={f * 7 + 3} />
        <feColorMatrix type="matrix" values="1 0 0 0 0  1 0 0 0 0  1 0 0 0 0  0 0 0 0 1" />
      </filter>
      <rect width={1280} height={720} filter={`url(#ga${f})`} />
    </svg>
  );
};
