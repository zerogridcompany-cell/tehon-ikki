// 10 ASCII art（字で描く立体）— 手本 手本M 10：黒地に緑の字でドーナツ（donut.c の作り方）が画面いっぱいに回る（f0〜20）
// → f20.5〜23 で輪の形（穴も埋めた外形）のまま字と色が替わりだす → f24.5〜27.5 で外形の字が抜けて朱と白の字の 12 本の星だけ残る → あとは字だけ ちらちら替わる
// canvas 2D の fillText：升目は等幅の字の送り（34 列・行の高さ＝列の幅×1.2＝手本を測った値）。明るさ→字（" .,-~:;=!*#$@"）・明るいほど白に近い色
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export type ASCIIArtProps = {width?: number; height?: number; cols?: number; colors?: Partial<typeof DEF>; ramp?: string; starRamp?: string; morphAt?: number; fontFamily?: string};
const DEF = {bg: '#020d04', dim: '#1f7a3e', mid: '#3ccf72', hi: '#eaf6ea', star: '#ff6a3d', starHi: '#ffeede', glitch: ['#43c46e', '#d7e04a', '#e8a33a', '#e0603a', '#d7e6d4'] as string[]};
const RAMP = ' .,-~:;=!*#$@';
const STAR = '.:-=•o@';   // ばらけと星の字（手本は @・丸い粒・短い : - . が多い。| ! * # $ のような背の高い字・とがった字は少ない）
const mulberry = (a: number) => () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const lerpc = (a: number[], b: number[], t: number) => `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(',')})`;

export const W10_ASCIIArt: React.FC<ASCIIArtProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height;
  const C = {...DEF, ...(p.colors || {})}; const ramp = p.ramp ?? RAMP, sr = p.starRamp ?? STAR; const M0 = p.morphAt ?? 21;
  const COLS = p.cols ?? 34, cw = W / COLS, rh = cw * 1.2, ROWS = Math.ceil(H / rh), fs = cw * 1.0;   // 升は 34 列・行＝列×1.2（手本を測った値）。字は升の 6 割の幅（手本は字と字の間に暗いすき間）＝太らせて塊の粒に
  const ref = useRef<HTMLCanvasElement>(null);
  const cellRnd = useMemo(() => { const r = mulberry(5); return Array.from({length: COLS * ROWS}, () => [r(), r(), r()]); }, [COLS, ROWS]);
  // 星（12 本）の明るさ：腕の真ん中ほど明るい・腕の長さは少しずつ違う。左下→右上の 2 本（5・11 番）は白い字が多い（手本の光の筋）
  const star = useMemo(() => {
    const out = new Float32Array(COLS * ROWS), arm = new Int8Array(COLS * ROWS); const S = Math.min(W, H), step = (2 * Math.PI) / 12;
    for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
      const x = (c + 0.5) * cw - W / 2, y = (r + 0.5) * rh - H / 2, rr = Math.hypot(x, y) / S;
      const ang = Math.atan2(y, x) + 0.14, kk = Math.round(ang / step), dA = ang - kk * step;
      const along = rr * Math.cos(dA), perp = Math.abs(rr * Math.sin(dA)), len = 0.43 + 0.05 * Math.sin(kk * 2.1), hw = 0.07 * (1 - 0.35 * along / len);
      let v = 0;
      if (along > 0 && along < len) v = Math.max(0, 1 - perp / hw) * (1 - 0.25 * along / len);
      else if (along >= len) v = Math.max(0, 1 - Math.hypot(along - len, perp) / hw) * 0.7;
      if (rr < 0.12) v = Math.max(v, 1 - rr / 0.16);   // 真ん中は詰まった円
      out[r * COLS + c] = v; arm[r * COLS + c] = ((kk % 12) + 12) % 12;
    }
    return {v: out, arm};
  }, [COLS, ROWS, W, H, cw, rh]);
  useLayoutEffect(() => {
    const cv = ref.current; if (!cv) return; const g = cv.getContext('2d')!;
    g.fillStyle = C.bg; g.fillRect(0, 0, W, H);
    g.font = `700 ${fs}px ${p.fontFamily ?? 'Menlo, ui-monospace, "SF Mono", monospace'}`; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.shadowBlur = 0.25 * cw; g.lineWidth = 0.07 * cw; g.lineJoin = 'round';   // 手本の字はにじんだ太い粒（ふちを足して太らせ、ぼかしの光で寄せる）
    // ドーナツ（donut.c）：A・B の回転を 1 コマごとに進める。大きさは手本の札（縦横 1.18）に換えた画面の大きさに合わせる（手本は寄りで画面いっぱい＝升の 66〜82% に字・角だけ暗い）
    const lum = new Float32Array(COLS * ROWS).fill(-1), zb = new Float32Array(COLS * ROWS);
    const fa = Math.min(f, M0 + 3);   // ばらけの間も輪はほぼ止まらず回る
    const A = 1.0 + fa * 0.1, B = 0.4 + fa * 0.05, cA = Math.cos(A), sA = Math.sin(A), cB = Math.cos(B), sB = Math.sin(B);
    const Ud = Math.sqrt(W * H / 1.18), R1 = 1, R2 = 2, K2 = 4.2, K1 = (0.6 * Ud * K2) / (R1 + R2);
    if (f < M0 + 6.5) for (let th = 0; th < 6.283; th += 0.03) { const ct = Math.cos(th), st = Math.sin(th);
      for (let ph = 0; ph < 6.283; ph += 0.008) { const cp = Math.cos(ph), sp = Math.sin(ph);
        const cx = R2 + R1 * ct, cy = R1 * st;
        const x = cx * (cB * cp + sA * sB * sp) - cy * cA * sB, y = cx * (sB * cp - sA * cB * sp) + cy * cA * cB, z = K2 + cA * cx * sp + cy * sA, ooz = 1 / z;
        const xp = Math.floor((W / 2 + K1 * ooz * x) / cw), yp = Math.floor((H / 2 - K1 * ooz * y) / rh);
        if (xp < 0 || yp < 0 || xp >= COLS || yp >= ROWS) continue;
        const L = cp * ct * sB - cA * ct * sp - sA * st + cB * (cA * st - ct * sA * sp);
        const k = yp * COLS + xp; if (ooz > zb[k]) { zb[k] = ooz; lum[k] = L; } } }
    // 輪の外形（穴も埋める）：外から字のない升をたどって届かん所＝穴
    const inside = new Uint8Array(COLS * ROWS);
    if (f >= M0 - 1) {
      const seen = new Uint8Array(COLS * ROWS), q: number[] = [];
      for (let c = 0; c < COLS; c++) for (const r of [0, ROWS - 1]) { const k = r * COLS + c; if (zb[k] === 0 && !seen[k]) { seen[k] = 1; q.push(k); } }
      for (let r = 0; r < ROWS; r++) for (const c of [0, COLS - 1]) { const k = r * COLS + c; if (zb[k] === 0 && !seen[k]) { seen[k] = 1; q.push(k); } }
      while (q.length) { const k = q.pop()!, r = (k / COLS) | 0, c = k % COLS;
        for (const [dr, dc] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const r2 = r + dr, c2 = c + dc; if (r2 < 0 || c2 < 0 || r2 >= ROWS || c2 >= COLS) continue; const k2 = r2 * COLS + c2; if (!seen[k2] && zb[k2] === 0) { seen[k2] = 1; q.push(k2); } } }
      for (let k = 0; k < COLS * ROWS; k++) inside[k] = seen[k] ? 0 : 1;
    }
    const dim = hex(C.dim), mid = hex(C.mid), hi = hex(C.hi), sc = hex(C.star), sh = hex(C.starHi);
    const NG = C.glitch.length;
    for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
      const k = r * COLS + c, [r0, r1, r2] = cellRnd[k];
      const g0 = M0 + r0 * 3, s0 = M0 + 3.5 + r1 * 3;   // 升ごと：字が替わりだす f21〜24 → 星に替わる f24.5〜27.5
      let ch = '', col = '';
      if (f < g0) { const L = lum[k]; if (L < 0) continue; const v = Math.min(1, Math.max(0, L / 1.414)); ch = ramp[Math.max(1, Math.round(v * (ramp.length - 1)))]; col = v < 0.68 ? lerpc(dim, mid, v / 0.68) : lerpc(mid, hi, (v - 0.68) / 0.32); }   // 白は一番明るい所だけ（手本は緑が主）
      else if (f < s0) {
        if (!inside[k] && lum[k] < 0) continue;   // 輪の外形（穴も）の中だけ
        const q = (r1 * 97 + f * 13.7) % 1; ch = sr[Math.floor(q * q * sr.length)];   // 小さい字が多め
        const warm = Math.min(1, Math.max(0, (f - (M0 + 2.5)) / 3));   // 緑の多い色 → 朱の多い色へ（手本 f22 緑と白・f24 黄緑・f26 朱）
        // 色の割合（緑・黄緑・橙・朱・白）：f24 は緑が主 → f26 は朱が主（手本の色相 f24 黄緑・f26 朱）
        const P = [0.5 - 0.38 * warm, 0.25 - 0.17 * warm, 0.1 + 0.05 * warm, 0.05 + 0.5 * warm, 0.1], rq = (r2 * 7.3 + f * 0.37) % 1; let gi = 0, acc = P[0]; while (rq > acc && gi < NG - 1) { gi++; acc += P[gi]; } col = C.glitch[gi];
      } else {
        const v = star.v[k]; if (v <= 0.12) continue; const fl = ((r0 * 31 + f * 0.618) % 1);
        if (v < 0.45 && fl < 0.3) continue;   // 腕の縁は字が抜ける（手本も腕の中にすき間）
        ch = sr[Math.max(0, Math.min(sr.length - 1, Math.round((0.35 + 0.65 * v) * (sr.length - 1) + (fl - 0.5) * 3)))];   // 腕は大きい粒（• o @）が主
        const a = star.arm[k], streak = (a === 5 || a === 11) && v > 0.35;   // 左下→右上の 2 本（5・11 番の腕）は白い @ の筋（手本の星はこの対角がはっきり白い）
        if (streak && fl < 0.78) { ch = '@'; col = lerpc(sc, sh, 0.92); }
        else col = fl < 0.08 + 0.25 * Math.max(0, v - 0.6) ? lerpc(sc, sh, 0.9) : lerpc(sc.map((x) => x * 0.8), sc, Math.min(1, v * 1.6));
      }
      g.fillStyle = col; g.strokeStyle = col; g.shadowColor = col; g.fillText(ch, (c + 0.5) * cw, (r + 0.5) * rh); g.strokeText(ch, (c + 0.5) * cw, (r + 0.5) * rh);
    }
  }, [f, W, H, COLS, ROWS, cw, rh, fs, cellRnd, star, ramp, sr, M0]);
  return <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: C.bg}}><canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0}} /></div>;
};
