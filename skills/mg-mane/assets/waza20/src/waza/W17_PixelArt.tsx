// 17 Pixel art（ドット絵のゲーム画面）— 手本 tehonM 17：紫の空・黄色い夕日（下に横縞）・紫の山が3重（奥ほどゆっくり流れる）・暗い緑の地面。
// 真ん中で赤い服の子が走り（4コマで足を替える）、金貨が右から 5.4 ドット/コマで流れてきて、5コマに1枚とる → 上の「COINS x00」が 5コマごとに増える
// canvas 2D：108x192 ドットの小さな絵に fillRect で描いて、ぼかさず（imageSmoothing なし）10倍に。字は自前の 5x7 のドットの字
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export type PixelArtProps = {width?: number; height?: number; label?: string; dots?: number; colors?: Partial<typeof DEF>; coinEvery?: number};
const DEF = {sky: '#6b256c', band: '#4a1a50', far: '#56286b', mid: '#3d164e', near: '#2c1140', sun: '#f9db92', ground: '#1c3b29', grass: '#2e6b45', text: '#f9e7d0', coin: '#f8c840', coinHi: '#fff1a6', shirt: '#dd212c', pants: '#2a4ab0', skin: '#f6c690', shoe: '#1a1020'};
const FONT: Record<string, string> = {A: '01110100011000111111100011000110001', B: '11110100011000111110100011000111110', C: '01110100011000010000100001000101110', D: '11100100101000110001100011001011100', E: '11111100001000011110100001000011111', F: '11111100001000011110100001000010000', G: '01110100011000010111100011000101111', H: '10001100011000111111100011000110001', I: '01110001000010000100001000010001110', J: '00111000100001000010000101001001100', K: '10001100101010011000101001001010001', L: '10000100001000010000100001000011111', M: '10001110111010110101100011000110001', N: '10001100011100110101100111000110001', O: '01110100011000110001100011000101110', P: '11110100011000111110100001000010000', Q: '01110100011000110001101011001001101', R: '11110100011000111110101001001010001', S: '01111100001000001110000010000111110', T: '11111001000010000100001000010000100', U: '10001100011000110001100011000101110', V: '10001100011000110001100010101000100', W: '10001100011000110101101011010101010', X: '10001100010101000100010101000110001', Y: '10001100011000101010001000010000100', Z: '11111000010001000100010001000011111', '0': '01110100011001110101110011000101110', '1': '00100011000010000100001000010001110', '2': '01110100010000100010001000100011111', '3': '11111000100010000010000011000101110', '4': '00010001100101010010111110001000010', '5': '11111100001111000001000011000101110', '6': '00110010001000011110100011000101110', '7': '11111000010001000100010000100001000', '8': '01110100011000101110100011000101110', '9': '01110100011000101111000010001001100', x: '00000000001000101010001000101010001', ' ': '00000000000000000000000000000000000', '.': '00000000000000000000000000110001100', ':': '00000011000110000000011000110000000', '!': '00100001000010000100001000000000100', '-': '00000000000000011111000000000000000'};
// 走る子（8x12）：2つの足の形を 4 コマごとに替える
const KID = [['..ssss..', '.ssssss.', '..ssss..', '...ss...', '.RRRRRR.', 'sRRRRRRs', 'sRRRRRRs', '.RRRRRR.', '.BBBBBB.', '.BB..BB.', '.BB..BB.', '.KK..KK.'], ['..ssss..', '.ssssss.', '..ssss..', '...ss...', '.RRRRRR.', '.RRRRRRs', 'sRRRRRR.', '.RRRRRR.', '.BBBBBB.', 'BB....BB', 'BB....BB', 'KK....KK']];

export const W17_PixelArt: React.FC<PixelArtProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height;
  const C = {...DEF, ...(p.colors || {})}; const AW = p.dots ?? 64, AH = Math.round((AW * H) / W), PX = W / AW;
  const ref = useRef<HTMLCanvasElement>(null);
  const art = useMemo(() => { const c = document.createElement('canvas'); c.width = AW; c.height = AH; return c; }, [AW, AH]);
  useLayoutEffect(() => {
    const cv = ref.current; if (!cv) return; const g = art.getContext('2d')!;
    const R = (x: number, y: number, w: number, h: number, col: string) => { g.fillStyle = col; g.fillRect(Math.round(x), Math.round(y), w, h); };
    const gy = Math.round(AH * 0.79), every = p.coinEvery ?? 5, gapC = 16, speed = gapC / every;
    R(0, 0, AW, AH, C.sky);
    // 上の帯（網目のディザ）
    R(0, 0, AW, 12, C.band); for (let y = 12; y < 15; y++) for (let x = (y % 2); x < AW; x += 2) R(x, y, 1, 1, C.band);
    // 夕日（ゆっくり上る・下半分に横縞）
    const sr = Math.round(AW * 0.15), scx = AW / 2, scy = Math.round(AH * 0.56 - Math.min(16, f * 0.22));   // 手本は 45 コマで高さの 12% 上がる
    for (let y = -sr; y <= sr; y++) { const w = Math.round(Math.sqrt(sr * sr - y * y)); const yy = scy + y; if (y > 1 && [3, 5, 7, 8].some((s) => y === s)) continue; R(scx - w, yy, 2 * w, 1, C.sun); }
    // 山（3重・奥ほどゆっくり）
    const ridge = (base: number, a1: number, k1: number, a2: number, k2: number, sp: number, col: string) => { for (let x = 0; x < AW; x++) { const X = x + f * sp; const h = Math.round(base + a1 * Math.sin(X * k1) + a2 * Math.sin(X * k2 + 1.3)); R(x, h, 1, gy - h, col); } };
    ridge(AH * 0.60, 4, 0.15, 2, 0.37, 0.22, C.far); ridge(AH * 0.665, 3, 0.2, 2, 0.5, 0.5, C.mid); ridge(AH * 0.725, 2, 0.33, 1, 0.8, 1.1, C.near);
    R(0, gy, AW, AH - gy, C.ground); R(0, gy, AW, 1, C.grass);
    // 金貨（右から流れる・子の真ん中を過ぎたら取った）
    const kx = Math.round(AW * 0.44); let got = 0;
    for (let i = 1; i < 40; i++) { const x = kx + 4 + gapC * i - speed * f; if (x <= kx + 4) got++; if (x > AW + 4 || x < -3) continue; const y = gy - [8, 5, 10, 6, 4, 9][i % 6]; const spin = Math.floor((f + i) / 3) % 4; const w = spin === 1 || spin === 3 ? 1 : 2; R(x + (2 - w) / 2, y, w, 3, C.coin); if (w === 2) R(x, y, 1, 1, C.coinHi); }
    // 走る子
    const sp = KID[Math.floor(f / 4) % 2]; const cmap: Record<string, string> = {s: C.skin, R: C.shirt, B: C.pants, K: C.shoe};
    sp.forEach((row, ry) => [...row].forEach((ch, rx) => { if (ch !== '.') R(kx - 4 + rx, gy - 12 + ry + (Math.floor(f / 4) % 2 ? 0 : 0), 1, 1, cmap[ch]); }));
    // 字（5x7）
    const m = cv.getContext('2d')!; m.imageSmoothingEnabled = false; m.drawImage(art, 0, 0, AW * PX, AH * PX);
    // 上の字は細かいドット（絵の 0.55 倍）で：画面幅の 4〜5 割（手本どおり）
    const label = `${p.label ?? 'COINS'} x${String(got).padStart(2, '0')}`; const dd = Math.round(PX * 0.55), tw = (label.length * 6 - 1) * dd; let tx = Math.round(W / 2 - tw / 2); const ty = Math.round(3.2 * PX);
    m.fillStyle = C.text; for (const ch of label) { const gl = FONT[ch] ?? FONT[ch.toUpperCase()] ?? FONT[' ']; for (let k = 0; k < 35; k++) if (gl[k] === '1') m.fillRect(tx + (k % 5) * dd, ty + Math.floor(k / 5) * dd, dd, dd); tx += 6 * dd; }
  }, [f, art, AW, AH, PX, p.label, p.coinEvery]);
  return <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: C.sky}}><canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0, imageRendering: 'pixelated'}} /></div>;
};
