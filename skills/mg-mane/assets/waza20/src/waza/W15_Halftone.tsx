// 15 Halftone（網点の印刷）— 手本 手本M 15：生成りの紙（薄い黄の網点）に、赤と青で塗り分けた大きな球（黒い穴つき・左の端で切れる）と、青い輪。
// 球の赤と青の境目は動かん（画面に固定の縦の線）。球の黒い穴だけ、ゆっくり左へ回る（f36 で 33°・だんだん速く）。
// 輪は倒れた向き（上から少し見る・穴は隠れる）→ 起きながら回り f24 でいちばん正面寄り（42°）→ f36 で縦に立つ（穴が 横長 → 斜めの楕円 → 縦の細い切れ目）。輪の真ん中は動かん。
// 影は「点の大きさ」で出す（45°の網・暗いほど点が大きい）。canvas 2D：1/4 の解像度で光線を飛ばして（球＝式・輪＝SDF の歩み）色の区分と暗さを出す → 平らな色を敷いて、上に網の点を打つ
// 寸法は手本の札（中身 399x472）を幅 W で割った値。縦長の画面では札の構図を上下のまん中に置く
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export type HalftoneProps = {width?: number; height?: number; cell?: number; colors?: Partial<typeof DEF>; quality?: number};
const DEF = {paper: '#f5e8d0', paperDot: '#c9ad5c', red: '#e3263c', redInk: '#3b0a14', blue: '#3a80cf', blueInk: '#0d1838', hole: '#140a16'};
// 暗さ＝網の点が覆う割合。手本の赤を測って合わせた：光の当たり 0.73 → 3 割・0.59 → 5 割・陰 → ほぼ全部（1 − 0.95·lam^1.2）
const darkOf = (lam: number) => Math.min(1, (1 - 0.95 * Math.pow(Math.max(0, lam), 1.2)) / 1.21);
const darkTorus = (lam: number) => Math.min(1, (0.3 + 0.7 * (1 - 0.95 * Math.pow(Math.max(0, lam), 1.2))) / 1.21);   // 輪は球の青より暗い（手本の管は光の側でも点が 5〜6 割）
const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const C0 = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const D2R = Math.PI / 180;
// 輪の軸（カメラから測った角 θ と、画面の中での向き φ）：手本の穴（輪の中の紙の色）を 2 コマごとにモーメントで測った値。
// θ は見える穴の縦横比（f24 で最大 0.57）を、この部品で描いた穴の縦横比と θ の対応（30°→0.79・47°→0.48）で逆引きした値。φ は穴の短い軸の向き（一定の速さで回り続け、止まらん）
const TH_F = [0, 4, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 50, 74], TH_V = [80, 76, 66, 62, 58, 53.3, 49.8, 46.4, 43.8, 42.8, 42.3, 42.8, 44.8, 47.8, 50.7, 54.8, 58, 72, 82];
const PH_F = [0, 4, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 50, 74], PH_V = [88, 83, 76, 73, 67, 62, 57, 50, 43, 35, 27, 19, 12, 6, 2, -2, -4, -30, -60];

export const W15_Halftone: React.FC<HalftoneProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H);
  const C = {...DEF, ...(p.colors || {})}; const Q = p.quality ?? 4, cw = Math.ceil(W / Q), ch = Math.ceil(H / Q);
  const ref = useRef<HTMLCanvasElement>(null);
  const small = useMemo(() => { const c = document.createElement('canvas'); c.width = cw; c.height = ch; return c; }, [cw, ch]);
  useLayoutEffect(() => {
    const cv = ref.current; if (!cv) return;
    const id = new Uint8Array(cw * ch), dk = new Float32Array(cw * ch);
    const Lx = 0.3, Ly = 0.75, Lz = 0.59;   // 光は上・少し右から（手本は球の右寄りがいちばん明るく、青い所はほぼ地の青・下が暗い）
    const U = Math.min(W, H / 1.18), top = (H - 1.18 * U) / 2, ox = (W - U) / 2;   // 札（幅 U・高さ 1.18U）を画面の上下まん中に
    // 球：中心 (0.309U, 0.486U)・半径 0.371U。赤と青の境目＝ nx 0.64 の縦の線（動かん）
    const sx = ox + 0.309 * U, sy = top + 0.486 * U, sr = 0.371 * U;
    // 黒い穴：法線の向き（右 24.9°・上 21.5°）から左へ回る。f36 で 32.8°（だんだん速く・(f/36)^2.2）、そのあとは 1.6°/コマ
    const psi = f <= 36 ? 32.8 * Math.pow(f / 36, 2.2) : 32.8 + 1.6 * (f - 36);
    const haz = (24.9 - psi) * D2R, hel = Math.min(30, 21.5 + 0.21 * psi) * D2R;
    const hdx = Math.cos(hel) * Math.sin(haz), hdy = Math.sin(hel), hdz = Math.cos(hel) * Math.cos(haz), HOLE = Math.cos(11 * D2R);   // 穴の大きさ＝球の上で半径 11°（手本の穴の面積 2000〜2190px²／札 399 幅）
    // 輪：真ん中 (0.80U, 0.865U) で動かん・輪の半径 0.236U・管 0.09U（穴の差し渡し 0.29U）。軸 a = Rz(φ−90°)·Rx(90°−θ)·(0,1,0)
    const th = interpolate(f, TH_F, TH_V, C0) * D2R, ph = interpolate(f, PH_F, PH_V, C0) * D2R;
    const b1 = Math.PI / 2 - th, c1 = Math.cos(b1), s1 = Math.sin(b1), g1 = ph - Math.PI / 2, cg = Math.cos(g1), sg = Math.sin(g1);
    const tx = ox + 0.80 * U, ty = top + 0.865 * U, TR = 0.236 * U, Tr = 0.09 * U;
    const bb = TR + Tr + 2;
    for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) {
      const X = (x + 0.5) * Q, Y = (y + 0.5) * Q, k = y * cw + x;
      let hitZ = -1e9, nid = 0, dark = 0.13;
      // 球
      const dx = X - sx, dy = Y - sy, d2 = dx * dx + dy * dy;
      if (d2 < sr * sr) { const nz = Math.sqrt(1 - d2 / (sr * sr)), nx = dx / sr, ny = -dy / sr; hitZ = nz * sr;
        const lam = Math.max(0, nx * Lx + ny * Ly + nz * Lz); dark = darkOf(lam);
        nid = nx > 0.64 ? 2 : 1;
        if (nx * hdx + ny * hdy + nz * hdz > HOLE) nid = 3; }
      // 輪（SDF を手前から奥へ歩く）
      if (Math.abs(X - tx) < bb && Math.abs(Y - ty) < bb) {
        let z = bb; for (let it = 0; it < 48 && z > -bb; it++) {
          const px = X - tx, py = -(Y - ty), pz = z;
          const p1x = cg * px + sg * py, p1y = -sg * px + cg * py;   // Rz の逆
          const lx = p1x, ly = c1 * p1y + s1 * pz, lz = -s1 * p1y + c1 * pz;   // Rx の逆
          const q = Math.hypot(lx, lz) - TR, dd = Math.hypot(q, ly) - Tr;
          if (dd < 0.6) { if (z > hitZ) {
              const L2 = Math.hypot(lx, lz) || 1; let nx = (lx / L2) * q, nyl = ly, nzl = (lz / L2) * q; const nn = Math.hypot(nx, nyl, nzl) || 1; nx /= nn; nyl /= nn; nzl /= nn;
              const ry = c1 * nyl - s1 * nzl, rz = s1 * nyl + c1 * nzl;   // Rx
              const wx = cg * nx - sg * ry, wy = sg * nx + cg * ry, wz = rz;   // Rz
              const lam = Math.max(0, wx * Lx + wy * Ly + wz * Lz); hitZ = z; nid = 4; dark = darkTorus(lam);
              const ang = Math.atan2(lz, lx), ta = Math.atan2(ly, q); for (const h0 of [0.6, 2.2, 3.9, 5.3]) { let da = Math.abs(ang - h0 + Math.PI * 2) % (Math.PI * 2); da = Math.min(da, Math.PI * 2 - da); if ((da / 0.05) ** 2 + ((ta - 0.9) / 0.3) ** 2 < 1) nid = 3; } }   // 管の小さな楕円の穴（手本は細長い暗い穴）
            break; }
          z -= Math.max(dd, 0.8);
        }
      }
      id[k] = nid; dk[k] = dark;
    }
    // 平らな色
    const sgx = small.getContext('2d')!; const im = sgx.createImageData(cw, ch); const cols = [hex(C.paper), hex(C.red), hex(C.blue), hex(C.hole), hex(C.blue)];
    for (let k = 0; k < cw * ch; k++) { const c = cols[id[k]], o = k * 4; im.data[o] = c[0]; im.data[o + 1] = c[1]; im.data[o + 2] = c[2]; im.data[o + 3] = 255; }
    sgx.putImageData(im, 0, 0);
    const g = cv.getContext('2d')!; g.imageSmoothingEnabled = true; g.drawImage(small, 0, 0, W, H);
    // 45°の網で暗さの点
    const cell = p.cell ?? 11 * (S / 1080), e = cell / Math.SQRT2, inks = [C.paperDot, C.redInk, C.blueInk, C.hole, C.blueInk];
    const a0 = Math.floor(-H / (2 * e)) - 1, a1 = Math.ceil(W / (2 * e)) + 1, b1n = Math.ceil((W + H) / (2 * e)) + 1;
    for (let a = a0; a <= a1; a++) for (let b = -1; b <= b1n; b++) {
      const X = (a + b) * e, Y = (b - a) * e;   // 45°に回した正方の網（間隔 cell）
      if (X < -cell || Y < -cell || X > W + cell || Y > H + cell) continue;
      const xi = Math.min(cw - 1, Math.max(0, Math.floor(X / Q))), yi = Math.min(ch - 1, Math.max(0, Math.floor(Y / Q))), k = yi * cw + xi;
      const t = id[k]; if (t === 3) continue; const dd = t === 0 ? 0.2 : dk[k];
      const r = cell * 0.62 * Math.sqrt(Math.max(0, dd)); if (r < 0.35) continue;
      g.fillStyle = inks[t]; g.beginPath(); g.arc(X, Y, r, 0, Math.PI * 2); g.fill();
    }
  }, [f, W, H, S, cw, ch, Q, small, p.cell, C.paper, C.red, C.blue]);
  return <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: C.paper}}><canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0}} /></div>;
};
