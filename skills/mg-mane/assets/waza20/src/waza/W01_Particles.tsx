// 01 Particles（粒子が集まる）— 手本 手本M 01：f2〜f9 で散った粒が円に、f9〜f14.5 で12本の星に集まり、あとは瞬く
// canvas 2D・粒 2200・加算合成（lighter）・粒は放射グラデの小さな絵（sprite）を drawImage
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export type ParticlesProps = {
  width?: number; height?: number; seed?: number;
  count?: number;          // 粒の数（既定 4200）
  arms?: number;           // 星の腕の数（既定 12）
  colors?: Partial<typeof DEF>;
  /** 集まる先を自前で渡す（0〜1 の座標・中心0.5）。無ければ星 */
  target?: (rnd: () => number) => [number, number];
};
const DEF = {bgCenter: '#2b1a48', bgMid: '#170f30', bgEdge: '#0a081b', dots: ['#ff9bcc', '#ffb89c', '#c39cff', '#fff0f6'] as string[], weights: [0.46, 0.26, 0.2, 0.08] as number[]};
// 測った時刻（clip のコマ・30fps）
const T = {fadeIn0: 1.5, fadeIn1: 5, gather0: 2, disc: 9, star: 14.5, twinkle: 12};

const mulberry = (a: number) => () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const eo3 = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
const gauss = (r: () => number) => { let u = 0; for (let i = 0; i < 4; i++) u += r(); return (u - 2) / 0.577; };

export const W01_Particles: React.FC<ParticlesProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H);
  const C = {...DEF, ...(p.colors || {})};
  const N = p.count ?? 4200, ARMS = p.arms ?? 12;
  const ref = useRef<HTMLCanvasElement>(null);
  const parts = useMemo(() => {
    const rnd = mulberry(p.seed ?? 7); const out: {sx: number; sy: number; dx: number; dy: number; tx: number; ty: number; r: number; c: number; ph: number; dl: number}[] = [];
    const armLen = Array.from({length: ARMS}, (_, k) => 0.37 + 0.06 * ((k * 7919) % 5) / 4);   // 腕の長さ 0.37〜0.43 S（手本も少し不ぞろい）
    const rot0 = -0.14;
    for (let i = 0; i < N; i++) {
      let tx: number, ty: number;
      if (p.target) { const [u, v] = p.target(rnd); tx = (u - 0.5) * S; ty = (v - 0.5) * S; }
      else if (rnd() < 0.06) { const rr = Math.abs(gauss(rnd)) * 0.07 * S, a = rnd() * Math.PI * 2; tx = Math.cos(a) * rr; ty = Math.sin(a) * rr; }
      else { const k = Math.floor(rnd() * ARMS), L = armLen[k] * S; const s = 0.07 * S + Math.pow(rnd(), 0.8) * (L - 0.07 * S); const w = (0.050 - 0.014 * s / L) * S; const a = rot0 + (k / ARMS) * Math.PI * 2; const off = gauss(rnd) * w * 0.55; tx = Math.cos(a) * s - Math.sin(a) * off; ty = Math.sin(a) * s + Math.cos(a) * off; }
      const da = rnd() * Math.PI * 2, dr = Math.sqrt(rnd()) * 0.36 * S * (0.55 + 0.45 * rnd());
      let cc = 0, q = rnd(); for (let k = 0; k < C.weights.length; k++) { if (q < C.weights[k]) { cc = k; break; } q -= C.weights[k]; cc = k; }
      out.push({sx: (rnd() * 1.3 - 0.15) * W - W / 2, sy: (rnd() * 1.2 - 0.1) * H - H / 2, dx: Math.cos(da) * dr, dy: Math.sin(da) * dr, tx, ty, r: (1.5 + 3.0 * rnd() * rnd()) * S / 1080, c: cc, ph: rnd() * 6.28, dl: (rnd() - 0.5) * 2});
    }
    return out;
  }, [W, H, S, N, ARMS, p.seed]);
  const sprites = useMemo(() => C.dots.map((col) => {
    const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d')!;
    const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.18, col); gr.addColorStop(0.45, col + '55'); gr.addColorStop(1, col + '00');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64); return c;
  }), [C.dots.join()]);
  useLayoutEffect(() => {
    const cv = ref.current; if (!cv) return; const g = cv.getContext('2d')!;
    g.clearRect(0, 0, W, H); g.globalCompositeOperation = 'lighter';
    const e1 = eo3((f - T.gather0) / (T.disc - T.gather0)), e2 = eo3((f - T.disc) / (T.star - T.disc));
    for (const q of parts) {
      const a = clamp01((f - T.fadeIn0 - q.dl * 0.6) / (T.fadeIn1 - T.fadeIn0));
      if (a <= 0) continue;
      const x1 = q.sx + (q.dx - q.sx) * e1, y1 = q.sy + (q.dy - q.sy) * e1;
      let x = x1 + (q.tx - x1) * e2, y = y1 + (q.ty - y1) * e2;
      const tw = f > T.twinkle ? 0.62 + 0.38 * Math.sin(f * 0.85 + q.ph) : 1;
      x += Math.sin(f * 0.21 + q.ph) * 0.0016 * S * e2; y += Math.cos(f * 0.17 + q.ph * 1.3) * 0.0016 * S * e2;
      const dc = Math.hypot(x, y) / S, core = 0.35 + 0.65 * Math.min(1, dc / 0.13);   // 真ん中は粒が重なって白く飛ぶ＝薄くする
      const s = q.r * 7.5; g.globalAlpha = a * tw * 0.85 * (e2 > 0.3 ? core : 1) * (1 - 0.42 * e1 * (1 - e2));   // 円にまとまる間は粒が重なる＝薄く
      g.drawImage(sprites[q.c], W / 2 + x - s / 2, H / 2 + y - s / 2, s, s);
    }
    g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
  }, [f, parts, sprites, W, H]);
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: `radial-gradient(circle at 50% 50%, ${C.bgCenter} 0%, ${C.bgMid} ${0.36 * S}px, ${C.bgEdge} ${0.85 * S}px)`}}>
      <canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0}} />
    </div>
  );
};
