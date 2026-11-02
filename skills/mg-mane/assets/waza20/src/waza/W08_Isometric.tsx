// 08 Isometric（等角の街がせり上がる）— 手本 手本M 08：6x6 のミント色の平たい板（f0〜6 は止まる）→ f7〜11 で全部がビルに伸び、
// 高さの山が 外周（f14）→ 真ん中（f21）→ 1つ外の輪（f29）→ 外周（f40）と輪を伝わる。低い＝藤色・高い＝桃色、側面に窓の点
// canvas 2D：等角（2:1）で柱を奥から順に塗る（上面・左の面・右の面）。高さ h＝土台＋A·exp(-(輪-山の位置)²/2σ²)
import React, {useLayoutEffect, useRef} from 'react';
import {interpolate, Easing, useCurrentFrame, useVideoConfig} from 'remotion';

export type IsometricProps = {width?: number; height?: number; n?: number; colors?: Partial<typeof DEF>};
const DEF = {bgTop: '#c8c4fe', bgMid: '#e2c7ef', bgBottom: '#f9d0cd', mint: '#a6f3e4', low: '#bdbaf0', high: '#f6bfae', slab: '#806667', slabDark: '#5f474a', gap: '#6c585c', win: '#fff3e8'};
const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const mixc = (a: number[], b: number[], t: number) => a.map((v, i) => v + (b[i] - v) * t);
const rgb = (c: number[], k = 1) => `rgb(${c.map((v) => Math.round(Math.min(255, v * k))).join(',')})`;
// 山の位置（輪の番号：0＝真ん中・2＝外周）を測ったコマで（f14 外・f21 中・f29 1つ外・f40 外 → 同じ周期でくり返す）
// 波は真ん中から外へ：真ん中 f21・1つ外 f29・外周 f40（1輪 ≈ 9.5 コマ）。26 コマごとに次の波（f14 の外周の山は f-5 に出た波）
const EMIT = [-5, 21, 47, 73, 99], RING_F = 9.5;

export const W08_Isometric: React.FC<IsometricProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H);
  const C = {...DEF, ...(p.colors || {})}; const N = p.n ?? 6;
  const ref = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const cv = ref.current; if (!cv) return; const g = cv.getContext('2d')!; g.clearRect(0, 0, W, H);
    const tw = (0.96 * S) / N, th = tw / 2, hz = 0.13 * S, cx = W / 2, cy0 = H * 0.58 - (N * th) / 2;
    const P = (gx: number, gy: number, z: number) => [cx + ((gx - gy) * tw) / 2, cy0 + ((gx + gy) * th) / 2 - z * hz];
    const poly = (pts: number[][], fill: string) => { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]); g.closePath(); g.fillStyle = fill; g.fill(); };
    // 土台（厚み 0.35）
    const SL = -0.38;
    poly([P(0, N, 0), P(N, N, 0), P(N, N, SL), P(0, N, SL)], C.slab);
    poly([P(N, 0, 0), P(N, N, 0), P(N, N, SL), P(N, 0, SL)], C.slabDark);
    poly([P(0, 0, 0), P(N, 0, 0), P(N, N, 0), P(0, N, 0)], C.gap);
    const rise = interpolate(f, [7, 11], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
    const amp = interpolate(f, [8, 12.5], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.sin)});
    const mint = hex(C.mint), lo = hex(C.low), hi = hex(C.high), win = C.win;
    const cells: [number, number][] = []; for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) cells.push([i, j]);
    cells.sort((a, b) => a[0] + a[1] - (b[0] + b[1]));
    const G = 0.075, half = (N - 1) / 2;
    for (const [i, j] of cells) {
      const ring = Math.max(Math.abs(i - half), Math.abs(j - half)) - 0.5;      // 0＝真ん中の 2x2 … 外周＝(N/2-1)
      const ringN = (ring / Math.max(1, N / 2 - 1)) * 2;                         // 0〜2 にそろえる
      let wave = 0; for (const e of EMIT) { const pos = (f - e) / RING_F; if (pos < -1 || pos > 3.2) continue; wave += Math.exp(-Math.pow(ringN - pos, 2) / (2 * 0.6 * 0.6)) * (pos > 2 ? Math.max(0, 1 - (pos - 2) / 1.2) : 1); }
      const bob = 0.12 * Math.sin(f * 0.35 + i * 1.7 + j * 2.3);   // 1棟ずつの小さな上下（止まって見えんように）
      const h = 0.10 + 0.42 * rise + amp * (1.95 * Math.min(1.2, wave) + bob);
      const t = Math.min(1, Math.max(0, (h - 0.35) / 1.9));
      const col = mixc(mixc(lo, hi, t), mint, 1 - rise);
      const a = [i + G, j + G], b = [i + 1 - G, j + G], c = [i + 1 - G, j + 1 - G], d = [i + G, j + 1 - G];
      poly([P(d[0], d[1], 0), P(c[0], c[1], 0), P(c[0], c[1], h), P(d[0], d[1], h)], rgb(col, 0.86));   // 左の面
      poly([P(b[0], b[1], 0), P(c[0], c[1], 0), P(c[0], c[1], h), P(b[0], b[1], h)], rgb(col, 0.66));   // 右の面
      if (h > 0.45) {   // 窓：0.22 ごとの段・面ごとに2列
        g.fillStyle = win;
        for (let z = 0.22; z < h - 0.14; z += 0.22) for (const s of [0.3, 0.62]) {
          g.globalAlpha = 0.55; const wl = 0.11, wh = 0.075;
          poly([P(d[0] + s * (c[0] - d[0]), d[1], z), P(d[0] + (s + wl) * (c[0] - d[0]), d[1], z), P(d[0] + (s + wl) * (c[0] - d[0]), d[1], z + wh), P(d[0] + s * (c[0] - d[0]), d[1], z + wh)], win);
          g.globalAlpha = 0.42;
          poly([P(b[0], b[1] + s * (c[1] - b[1]), z), P(b[0], b[1] + (s + wl) * (c[1] - b[1]), z), P(b[0], b[1] + (s + wl) * (c[1] - b[1]), z + wh), P(b[0], b[1] + s * (c[1] - b[1]), z + wh)], win);
        }
        g.globalAlpha = 1;
      }
      poly([P(a[0], a[1], h), P(b[0], b[1], h), P(c[0], c[1], h), P(d[0], d[1], h)], rgb(col, 1.04));      // 上の面
    }
  }, [f, W, H, S, N, C.mint, C.low, C.high]);
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: `linear-gradient(180deg, ${C.bgTop} 0%, ${C.bgMid} 55%, ${C.bgBottom} 100%)`}}>
      <canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0}} />
    </div>
  );
};
