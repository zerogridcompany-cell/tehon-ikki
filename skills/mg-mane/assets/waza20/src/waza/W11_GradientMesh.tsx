// 11 Gradient mesh（溶けて流れる色の面）— 手本 手本M 11：珊瑚・すみれ・青緑・桃の4〜5色が、絵の具を混ぜるようにゆっくり流れ続ける（動きの量 3〜6/コマで一定）
// canvas 2D の画素計算：ゆがめた雑音（domain warp：fbm を fbm でずらす×2回）→ 値を色の段に当てる。1/4 の解像度で計算して拡大＋細かい粒
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export type GradientMeshProps = {width?: number; height?: number; stops?: string[]; speed?: number; scale?: number; quality?: number; seed?: number};
const STOPS = ['#22bfc4', '#5a86e0', '#7a4ee8', '#b85cae', '#f45f72', '#f6747a', '#f8c4a4'];
const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const hash = (x: number, y: number, s: number) => { let h = Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(s, 2246822519); h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967295; };
const noise = (x: number, y: number, s: number) => { const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi; const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf); const a = hash(xi, yi, s), b = hash(xi + 1, yi, s), c = hash(xi, yi + 1, s), d = hash(xi + 1, yi + 1, s); return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v; };
const fbm = (x: number, y: number, s: number) => { let v = 0, a = 0.5; for (let o = 0; o < 3; o++) { v += a * noise(x, y, s + o); const nx = 1.6 * x + 1.2 * y, ny = -1.2 * x + 1.6 * y; x = nx + 3.1; y = ny + 1.7; a *= 0.5; } return v / 0.875; };

export const W11_GradientMesh: React.FC<GradientMeshProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H);
  const Q = p.quality ?? 4, cw = Math.ceil(W / Q), ch = Math.ceil(H / Q);
  const stops = useMemo(() => (p.stops ?? STOPS).map(hex), [(p.stops ?? STOPS).join()]);
  // 値の幅：t=0 の荒い升目で値を集め、4%〜96% を 0〜1 に当てる（どのコマでも同じ数字＝ちらつかん）
  const range = useMemo(() => { const sc0 = (p.scale ?? 1) * 0.8 / (S / Q), sd = p.seed ?? 1, vs: number[] = []; for (let y = 0; y < ch; y += 8) for (let x = 0; x < cw; x += 8) { const px = x * sc0, py = y * sc0; const qx = fbm(px, py, sd), qy = fbm(px + 5.2, py + 1.3, sd + 9); const rx = fbm(px + 1.3 * qx + 1.7, py + 1.3 * qy + 9.2, sd + 17), ry = fbm(px + 1.3 * qx + 8.3, py + 1.3 * qy + 2.8, sd + 23); vs.push(fbm(px + 1.5 * rx, py + 1.5 * ry, sd + 31)); } vs.sort((a, b) => a - b); return [vs[Math.floor(vs.length * 0.04)], vs[Math.floor(vs.length * 0.96)]] as [number, number]; }, [cw, ch, S, Q, p.scale, p.seed]);
  const ref = useRef<HTMLCanvasElement>(null);
  const small = useMemo(() => { const c = document.createElement('canvas'); c.width = cw; c.height = ch; return c; }, [cw, ch]);
  const grain = useMemo(() => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d')!; const im = g.createImageData(256, 256); let s = 3; for (let i = 0; i < im.data.length; i += 4) { s = (s * 1103515245 + 12345) & 0x7fffffff; const v = 118 + (s % 20); im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; } g.putImageData(im, 0, 0); return c; }, []);
  useLayoutEffect(() => {
    const cv = ref.current; if (!cv) return; const sg = small.getContext('2d')!; const im = sg.createImageData(cw, ch); const d = im.data;
    const t = (f / 30) * (p.speed ?? 1) * 5.0, sc = (p.scale ?? 1) * 0.8 / (S / Q), sd = p.seed ?? 1;
    const n = stops.length - 1; const [lo, hi] = range;
    for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) {
      const px = x * sc, py = y * sc;
      const qx = fbm(px + 0.11 * t, py - 0.07 * t, sd), qy = fbm(px + 5.2 - 0.09 * t, py + 1.3 + 0.05 * t, sd + 9);
      const rx = fbm(px + 1.3 * qx + 1.7 + 0.15 * t, py + 1.3 * qy + 9.2, sd + 17), ry = fbm(px + 1.3 * qx + 8.3, py + 1.3 * qy + 2.8 + 0.126 * t, sd + 23);
      let v = fbm(px + 1.5 * rx + 0.05 * t, py + 1.5 * ry, sd + 31);
      v = Math.min(1, Math.max(0, (v - lo) / (hi - lo)));
      const pos = v * n, i = Math.min(n - 1, Math.floor(pos)); let k = pos - i; k = k * k * (3 - 2 * k);
      const a = stops[i], b = stops[i + 1], o = (y * cw + x) * 4;
      d[o] = a[0] + (b[0] - a[0]) * k; d[o + 1] = a[1] + (b[1] - a[1]) * k; d[o + 2] = a[2] + (b[2] - a[2]) * k; d[o + 3] = 255;
    }
    sg.putImageData(im, 0, 0);
    const g = cv.getContext('2d')!; g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'; g.drawImage(small, 0, 0, W, H);
    g.save(); g.globalCompositeOperation = 'overlay'; g.globalAlpha = 0.18; g.fillStyle = g.createPattern(grain, 'repeat')!; g.fillRect(0, 0, W, H); g.restore();
  }, [f, W, H, S, cw, ch, small, stops, range, grain, p.speed, p.scale, p.seed, Q]);
  return <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: '#7a4ee8'}}><canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0}} /></div>;
};
