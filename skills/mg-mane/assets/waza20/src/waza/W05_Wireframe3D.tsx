// 05 Wireframe 3D（線だけの立体・街を前へ進む）— 手本 手本M 05：生成りの紙に青紫の線の箱（ビル）が道の両側に並び、一点透視で手前へ流れる。道の真ん中に朱の破線
// SVG の線：箱の12辺を透視で写す（手前の面で切る）。遠いほど線を薄く。速さは最初だけ少し速く（動きの量 16→10）
import React, {useMemo} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export type Wireframe3DProps = {width?: number; height?: number; colors?: Partial<typeof DEF>; speed?: number; seed?: number; horizon?: number};
const DEF = {bg: '#f2f0eb', near: '#2f28c0', far: '#aeaaea', road: '#e2603f', ground: '#d6d4e2'};
const mulberry = (a: number) => () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const mix = (a: string, b: string, t: number) => { const h = (s: string, i: number) => parseInt(s.slice(1 + 2 * i, 3 + 2 * i), 16); return '#' + [0, 1, 2].map((i) => Math.round(h(a, i) + (h(b, i) - h(a, i)) * t).toString(16).padStart(2, '0')).join(''); };
const L = 72, ROAD = 1.7, CAMY = 1.25, ZN = 0.3;

export const W05_Wireframe3D: React.FC<Wireframe3DProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height;
  const C = {...DEF, ...(p.colors || {})};
  const blds = useMemo(() => {
    const rnd = mulberry(p.seed ?? 11); const out: {x0: number; x1: number; z0: number; z1: number; h: number}[] = [];
    for (const side of [-1, 1]) { let z = rnd() * 2; while (z < L - 1) { const dz = 2.0 + rnd() * 3.4, wx = 1.8 + rnd() * 2.8, set = rnd() < 0.3 ? rnd() * 1.2 : 0, h = 2.4 + Math.pow(rnd(), 0.8) * 5.6; const xa = side * (ROAD + set), xb = side * (ROAD + set + wx); out.push({x0: Math.min(xa, xb), x1: Math.max(xa, xb), z0: z, z1: z + dz, h}); z += dz + 0.3 + rnd() * 1.6; } }
    return out;
  }, [p.seed]);
  const zc = (0.33 * f + 3 * (1 - Math.exp(-f / 6))) * (p.speed ?? 1);
  const FX = 1.1 * W, HY = (p.horizon ?? 0.52) * H, CX = W / 2;
  const proj = (x: number, y: number, z: number) => [CX + (FX * x) / z, HY - (FX * (y - CAMY)) / z];
  const seg = (a: number[], b: number[]) => {   // 3D の線分を手前の面 ZN で切ってから写す
    let [x1, y1, z1] = a, [x2, y2, z2] = b; if (z1 < ZN && z2 < ZN) return null;
    if (z1 < ZN) { const t = (ZN - z1) / (z2 - z1); x1 += (x2 - x1) * t; y1 += (y2 - y1) * t; z1 = ZN; }
    if (z2 < ZN) { const t = (ZN - z2) / (z1 - z2); x2 += (x1 - x2) * t; y2 += (y1 - y2) * t; z2 = ZN; }
    const P = proj(x1, y1, z1), Q = proj(x2, y2, z2); return `M${P[0].toFixed(1)} ${P[1].toFixed(1)}L${Q[0].toFixed(1)} ${Q[1].toFixed(1)}`;
  };
  const paths: {d: string; col: string; op: number; w: number; z: number}[] = [];
  for (const b of blds) {
    let z0 = ((b.z0 - zc) % L + L) % L; const dz = b.z1 - b.z0; if (z0 > L - dz) z0 -= L; const z1 = z0 + dz;
    if (z1 < ZN) continue;
    const depth = Math.max(0, z0) / L; const op = 1 - Math.min(1, Math.max(0, (depth - 0.55) / 0.4));
    if (op <= 0) continue;
    const xs = [b.x0, b.x1], zs = [z0, z1], ys = [0, b.h]; let d = '';
    for (const y of ys) for (const z of zs) { const s = seg([xs[0], y, z], [xs[1], y, z]); if (s) d += s; }
    for (const y of ys) for (const x of xs) { const s = seg([x, y, zs[0]], [x, y, zs[1]]); if (s) d += s; }
    for (const x of xs) for (const z of zs) { const s = seg([x, 0, z], [x, b.h, z]); if (s) d += s; }
    const t = Math.min(1, Math.max(0, z0 / (L * 0.5)));
    paths.push({d, col: mix(C.near, C.far, t), op, w: Math.max(1.8, 5.2 * (1 - t)) * W / 1080, z: z0});
  }
  paths.sort((a, b) => b.z - a.z);
  let dash = ''; for (let k = 0; k < 60; k++) { const z = 2 * k - (zc % 2); const s = seg([0, 0, z], [0, 0, z + 0.9]); if (s && z < L * 0.7) dash += s; }
  let grd = ''; for (const x of [-ROAD, ROAD, -6, 6]) { const s = seg([x, 0, ZN], [x, 0, L]); if (s) grd += s; }
  for (let k = 0; k < 24; k++) { const z = 4 * k - (zc % 4); const s = seg([-ROAD, 0, z], [ROAD, 0, z]); if (s) grd += s; }
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: C.bg}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <path d={grd} stroke={C.ground} strokeWidth={1.2 * W / 1080} fill="none" opacity={0.8} />
        <path d={dash} stroke={C.road} strokeWidth={3 * W / 1080} fill="none" strokeLinecap="butt" />
        {paths.map((q, i) => <path key={i} d={q.d} stroke={q.col} strokeOpacity={q.op} strokeWidth={q.w} fill="none" strokeLinejoin="round" />)}
      </svg>
    </div>
  );
};
