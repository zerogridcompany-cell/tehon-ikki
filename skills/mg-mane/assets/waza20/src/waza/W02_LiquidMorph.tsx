// 02 Liquid morph（液体の玉がくっつく・離れる）— 手本 tehonM 02：真珠色の金属っぽい玉（メタボール）が休まず合体・分裂（動きの量 4〜9/コマで一定）
// canvas 2D の画素計算：場 F=Σr²/d² の 1 で縁・高さ h=√(1-1/F) から法線 → 映り込み（反射の向き R で 上＝白い空・横＝灰に左ピンク/右シアン・下＝金）＋白い光。1/3 の解像度で計算して拡大
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export type LiquidMorphProps = {width?: number; height?: number; colors?: Partial<typeof DEF>; blobs?: number; speed?: number; quality?: number};
const DEF = {bgTop: '#efebef', bgBottom: '#cbc7cf', sky: '#f4f0f7', mid: '#b6afbd', dark: '#827b8a', pink: '#e070cf', cyan: '#5ccfe2', gold: '#d2b064', goldDeep: '#9a7c48', spec: '#ffffff'};
const hex = (h: string) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const sst = (a: number, b: number, x: number) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
// 玉の軌道（S を 1 とした値）：半径・中心のずれ・周期（コマ 24〜46）・位相。手本は 37 コマで1回 くっつく→離れる・動きの量 6.4/コマ
const BALLS = [
  {r: 0.165, ax: 0.13, ay: 0.15, px: 46, py: 37, ox: 0.0, oy: 0.4},
  {r: 0.135, ax: 0.30, ay: 0.13, px: 33, py: 41, ox: 1.7, oy: 2.1},
  {r: 0.115, ax: 0.22, ay: 0.32, px: 37, py: 29, ox: 3.3, oy: 0.9},
  {r: 0.095, ax: 0.33, ay: 0.28, px: 28, py: 44, ox: 4.4, oy: 3.6},
  {r: 0.072, ax: 0.27, ay: 0.38, px: 24, py: 34, ox: 2.6, oy: 5.2},
];

export const W02_LiquidMorph: React.FC<LiquidMorphProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame() * (p.speed ?? 1);
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H);
  const C = {...DEF, ...(p.colors || {})};
  const Q = p.quality ?? 2;   // 何分の1で計算するか（2＝1080x1920 で 540x960）
  const cw = Math.ceil(W / Q), ch = Math.ceil(H / Q);
  const ref = useRef<HTMLCanvasElement>(null);
  const small = useMemo(() => { const c = document.createElement('canvas'); c.width = cw; c.height = ch; return c; }, [cw, ch]);
  const nb = Math.min(BALLS.length, p.blobs ?? 5);
  useLayoutEffect(() => {
    const cv = ref.current; if (!cv) return;
    const sg = small.getContext('2d')!; const img = sg.createImageData(cw, ch); const d = img.data;
    const s = S / Q, cx = cw / 2, cy = ch / 2;
    const bx: number[] = [], by: number[] = [], br2: number[] = [];
    for (let i = 0; i < nb; i++) { const b = BALLS[i]; bx.push(cx + b.ax * s * Math.sin(2 * Math.PI * f / b.px + b.ox)); by.push(cy + b.ay * s * 1.25 * Math.sin(2 * Math.PI * f / b.py + b.oy)); br2.push(Math.pow(b.r * s, 2)); }
    const h = new Float32Array(cw * ch), F = new Float32Array(cw * ch);
    for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) {
      let v = 0; for (let i = 0; i < nb; i++) { const dx = x - bx[i], dy = y - by[i]; v += br2[i] / (dx * dx + dy * dy + 0.5); }
      const k = y * cw + x; F[k] = v; h[k] = v > 1 ? Math.sqrt(1 - 1 / v) : 0;
    }
    const sky = hex(C.sky), mid = hex(C.mid), dk = hex(C.dark), pk = hex(C.pink), cy2 = hex(C.cyan), gd = hex(C.gold), gd2 = hex(C.goldDeep), sp = hex(C.spec);
    const R = 0.12 * s;   // 法線の強さ＝玉の大きさの目安
    const Lx = -0.4, Ly = -0.7, Lz = 0.6, Ln = Math.hypot(Lx, Ly, Lz);
    const col = [0, 0, 0];
    for (let y = 1; y < ch - 1; y++) for (let x = 1; x < cw - 1; x++) {
      const k = y * cw + x; const v = F[k]; if (v < 0.9) { d[k * 4 + 3] = 0; continue; }
      let nx = -(h[k + 1] - h[k - 1]) * 0.5 * R, ny = -(h[k + cw] - h[k - cw]) * 0.5 * R, nz = 1; const nn = Math.hypot(nx, ny, nz); nx /= nn; ny /= nn; nz /= nn;
      const rx = 2 * nz * nx, ry = 2 * nz * ny, rz = 2 * nz * nz - 1;     // 見る向きの反射（y は下が＋）
      // 横の帯：灰に 左＝ピンク・右＝シアン
      const tp = sst(0.1, 0.9, -rx) * 0.7, tc = sst(0.1, 0.9, rx) * 0.7, hz = 1 - sst(0.0, 0.3, Math.abs(ry - 0.12));   // 地平の少し下に暗い帯（金属らしさ）
      for (let c = 0; c < 3; c++) { let m = mid[c]; m += (dk[c] - m) * hz * 0.7; m += (pk[c] - m) * tp; m += (cy2[c] - m) * tc; col[c] = m; }
      if (ry < 0) { const t = sst(-0.05, -0.55, ry); for (let c = 0; c < 3; c++) col[c] += (sky[c] - col[c]) * t; }
      else { const t = sst(0.25, 0.7, ry) * 0.75, t2 = sst(0.6, 1.0, ry); for (let c = 0; c < 3; c++) { col[c] += (gd[c] - col[c]) * t; col[c] += (gd2[c] - col[c]) * t2 * 0.45; } }
      const rim = sst(0.15, -0.6, rz);   // 縁（後ろを映す所）は色を濃く
      if (rim > 0) { const tint = nx < 0 ? pk : cy2; for (let c = 0; c < 3; c++) col[c] += (tint[c] - col[c]) * rim * 0.4; }
      const spec = Math.pow(Math.max(0, (rx * Lx + ry * Ly + rz * Lz) / Ln), 40) * 1.2;
      for (let c = 0; c < 3; c++) d[k * 4 + c] = col[c] + (sp[c] - col[c]) * Math.min(1, spec);
      d[k * 4 + 3] = 255 * sst(0.94, 1.06, v);
    }
    sg.putImageData(img, 0, 0);
    const g = cv.getContext('2d')!; g.clearRect(0, 0, W, H); g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'; g.drawImage(small, 0, 0, W, H);
  }, [f, W, H, S, cw, ch, nb, small, C.sky, C.mid, C.dark, C.pink, C.cyan, C.gold, C.goldDeep, C.spec, Q]);
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: `linear-gradient(180deg, ${C.bgTop} 0%, ${C.bgBottom} 100%)`}}>
      <canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0}} />
    </div>
  );
};
