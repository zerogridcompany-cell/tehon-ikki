// 線画 2D の MG を手本に寄せる部品（mute-pagani 11/24 で作った・references/senga2d_mute.md）
// 1) 手本を逆算したカメラ（kamera.json）を「うちの秒→手本の秒（rf.json）」でそのまま当てる
// 2) 手本の 2 種類の切り替え＝ずれ（横の帯 4 コマ）・光（白 3 コマ）を字幕ごと全体にかける
// 3) 手本の断面を測った光のにじみ（芯 6px＋σ10×0.8＋σ28×1.2）
// 使い方: <GlowDefs/> を svg の <defs> に・<SceneView> の中で camTransform(...)・一番外で <Kirikae frame={...} gl={[...]} fl={[...]}><Frame/></Kirikae>
import React from 'react';
import {AbsoluteFill} from 'remotion';

export type Kam = {f0: number; f1: number; k: number[][]}; // k = [[手本のコマ, 倍, x流し px, y流し px, 回り度], …]（kamera_gyaku.py → ならし）

// うちの秒 → 手本の秒（rf = [[手本の秒, うちの秒], …] を線でつなぐ）
export const makeO2R = (rf: number[][]) => (t: number) => {
  if (t <= rf[0][1]) return rf[0][0];
  for (let i = 1; i < rf.length; i++) if (t <= rf[i][1]) { const [a0, b0] = rf[i - 1]; const [a1, b1] = rf[i]; return a0 + ((t - b0) / (b1 - b0)) * (a1 - a0); }
  return rf[rf.length - 1][0];
};

// 手本のコマ fr のカメラ [倍, x, y, 回り]
export const camAt = (d: Kam | undefined, fr: number): number[] => {
  if (!d) return [1, 0, 0, 0];
  const k = d.k; const f = Math.min(Math.max(fr, d.f0), d.f1);
  if (f <= k[0][0]) return k[0].slice(1);
  for (let i = 1; i < k.length; i++) if (f <= k[i][0]) { const u = (f - k[i - 1][0]) / (k[i][0] - k[i - 1][0]); return [1, 2, 3, 4].map((j) => k[i - 1][j] + (k[i][j] - k[i - 1][j]) * u); }
  return k[k.length - 1].slice(1);
};

// 土台（場面の置き場所 z0・ox・oy を cx,cy 中心で）→ 手本のカメラ（画面の中心で 寄り・回り・流し）
export const camTransform = (cam: number[], base: {z0?: number; ox?: number; oy?: number; cx?: number; cy?: number} = {}, W = 1920, H = 1080) => {
  const [s, tx, ty, rot] = cam; const cx = base.cx ?? W / 2, cy = base.cy ?? H / 2;
  return `translate(${W / 2 + tx} ${H / 2 + ty}) rotate(${rot}) scale(${s}) translate(${-W / 2} ${-H / 2}) translate(${cx + (base.ox ?? 0)} ${cy + (base.oy ?? 0)}) scale(${base.z0 ?? 1}) translate(${-cx} ${-cy})`;
};

// 光のにじみ（手本の断面：芯から 1px で 0.44・2〜16px で 0.29→0.14 のゆるい裾）
export const GlowDefs: React.FC = () => (
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="b1" />
    <feGaussianBlur in="SourceGraphic" stdDeviation="28" result="b2" />
    <feComponentTransfer in="b1" result="c1"><feFuncA type="linear" slope="0.8" /></feComponentTransfer>
    <feComponentTransfer in="b2" result="c2"><feFuncA type="linear" slope="1.2" /></feComponentTransfer>
    <feMerge><feMergeNode in="c2" /><feMergeNode in="c1" /><feMergeNode in="SourceGraphic" /></feMerge>
  </filter>
);

const rnd = (n: number) => { const x = Math.sin(n * 12.9898) * 43758.5453; return x - Math.floor(x); };
export const FLASH = [0.92, 0.58, 0.25]; // 手本の明るさ 223→146→70（地 15・白 240）から
export const GLAMP = [1, 0.55, 0.3, 0.12]; // ずれの強さ（4 コマ）

// 切り替え：frame＝今のコマ・gl＝ずれの頭のコマ・fl＝[光の頭のコマ, ずらし(-1 で 1 コマ前から)]・light＝明るい場面か
export const Kirikae: React.FC<{frame: number; gl: number[]; fl: [number, number][]; light?: (g0: number) => boolean; children: React.ReactNode}> = ({frame: f, gl, fl, light, children}) => {
  const g0 = gl.find((a) => f >= a && f < a + 4);
  const fq = fl.find(([a, o]) => f >= a + o && f < a + o + 3);
  let body: React.ReactNode = children;
  if (g0 !== undefined) {
    const k = f - g0; const amp = GLAMP[k]; const bands: [number, number, number][] = []; let y = 0; let i = 0;
    while (y < 1080) { const h = 8 + Math.floor(rnd(g0 * 7 + i * 13) * 56); const on = rnd(g0 * 3 + i * 29 + k * 5) < 0.62; bands.push([y, Math.min(1080, y + h), on ? (rnd(g0 + i * 17 + k * 11) - 0.5) * 460 * amp : 0]); y += h; i++; }
    const lt = light ? light(g0) : false;
    body = (<AbsoluteFill style={{background: lt ? '#ececec' : '#000'}}>
      {children}
      {bands.filter((b) => Math.abs(b[2]) > 0.5).map(([y0, y1, off], j) => (
        <AbsoluteFill key={j} style={{clipPath: `inset(${y0}px 0px ${1080 - y1}px 0px)`, transform: `translateX(${off}px)`}}>{children}</AbsoluteFill>
      ))}
      <svg width={1920} height={1080} style={{position: 'absolute'}}>
        {k < 3 && [...Array(Math.round(7 * amp) + 1)].map((_, j) => { const bw = 20 + rnd(g0 + j * 3 + k) * 110; const left = rnd(g0 * 2 + j) < 0.5; return <rect key={j} x={left ? 0 : 1920 - bw} y={rnd(g0 * 5 + j * 7 + k) * 1040} width={bw} height={12 + rnd(j * 11 + g0) * 40} fill="#000" />; })}
        {!lt && k < 3 && [0, 1, 2].map((j) => <rect key={'l' + j} x={0} y={rnd(g0 * 9 + j * 5 + k) * 1080} width={1920} height={2} fill="#bdbdbd" opacity={0.55 * amp + 0.2} />)}
      </svg>
    </AbsoluteFill>);
  }
  return (<AbsoluteFill>{body}{fq && <AbsoluteFill style={{background: '#f4f4f4', opacity: FLASH[f - fq[0] - fq[1]]}} />}</AbsoluteFill>);
};
