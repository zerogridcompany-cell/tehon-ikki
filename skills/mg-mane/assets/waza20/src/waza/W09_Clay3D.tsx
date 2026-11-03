// 09 Clay 3D（粘土の立体が弾む）— 手本 tehonM 09：桃の球・青の角丸の箱・黄色の輪が、20コマ周期で弾む（輪 f5.5・箱 f12・球 f18.5 に床へ着く）。
// 着く1〜2コマは潰れる（縦 0.75・横 1.15）。床に柔らかい影（高いほど小さく薄い）。光は左上から・ツヤなしの粘土
// canvas 2D に自前の小さな 3D（球・超楕円体の箱・輪を四角に割る→回す→遠い順に塗る・法線は式で出して滑らかな陰）＋細かいざらつき
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export type Clay3DProps = {width?: number; height?: number; colors?: Partial<typeof DEF>; period?: number};
const DEF = {wall: '#f8e2d6', floor: '#fcf1e4', sphere: '#ec98aa', cube: '#74a6d8', torus: '#f7dc7c', shadow: '125,92,84'};
type V = [number, number, number];
type Mesh = {P: V[][]; N: V[][]};
const spow = (x: number, e: number) => Math.sign(x) * Math.pow(Math.abs(x), e);
const norm = (v: V): V => { const n = Math.hypot(...v) || 1; return [v[0] / n, v[1] / n, v[2] / n]; };
const grid = (nu: number, nv: number, fn: (u: number, v: number) => [V, V]): Mesh => { const P: V[][] = [], N: V[][] = []; for (let i = 0; i <= nu; i++) { P.push([]); N.push([]); for (let j = 0; j <= nv; j++) { const [p, n] = fn((i / nu) * Math.PI * 2, (j / nv) * Math.PI - Math.PI / 2); P[i].push(p); N[i].push(norm(n)); } } return {P, N}; };
const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const E = 0.28;   // 箱の角の丸み（小さいほど四角）

export const W09_Clay3D: React.FC<Clay3DProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H);
  const C = {...DEF, ...(p.colors || {})}; const PER = p.period ?? 20;
  const ref = useRef<HTMLCanvasElement>(null);
  const meshes = useMemo(() => ({
    sphere: grid(44, 22, (u, v) => { const q: V = [Math.cos(v) * Math.cos(u), Math.sin(v), Math.cos(v) * Math.sin(u)]; return [q, q]; }),
    cube: grid(44, 30, (u, v) => { const q: V = [spow(Math.cos(v), E) * spow(Math.cos(u), E), spow(Math.sin(v), E), spow(Math.cos(v), E) * spow(Math.sin(u), E)]; const k = 2 / E - 1; return [q, [spow(q[0], k), spow(q[1], k), spow(q[2], k)]]; }),
    torus: grid(48, 22, (u, v) => { const a = v * 2 + Math.PI; const q: V = [(1 + 0.42 * Math.cos(a)) * Math.cos(u), 0.42 * Math.sin(a), (1 + 0.42 * Math.cos(a)) * Math.sin(u)]; return [q, [q[0] - Math.cos(u), q[1], q[2] - Math.sin(u)]]; }),
  }), []);
  const grain = useMemo(() => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d')!; const im = g.createImageData(256, 256); let s = 9; for (let i = 0; i < im.data.length; i += 4) { s = (s * 1103515245 + 12345) & 0x7fffffff; const v = 108 + (s % 41); im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; } g.putImageData(im, 0, 0); return c; }, []);
  useLayoutEffect(() => {
    const cv = ref.current; if (!cv) return; const g = cv.getContext('2d')!; g.clearRect(0, 0, W, H);
    const floorY = H * 0.66, D = 4 * S, pitch = 0.2, cp = Math.cos(pitch), sp = Math.sin(pitch);   // 少し上から見下ろす
    const proj = (x: number, y: number, z: number) => { const y2 = y * cp + z * sp, z2 = -y * sp + z * cp; const s = D / (D + z2); return [W / 2 + x * s, floorY - y2 * s, z2]; };
    const bounce = (fc: number, hb: number) => { const ph = ((((f - fc) / PER) % 1) + 1) % 1; const dphi = ph > 0.5 ? ph - 1 : ph; const hgt = hb * (1 - Math.pow(2 * ph - 1, 2)); const k = Math.max(0, 1 - Math.abs(dphi) / 0.075); const st = Math.abs(dphi) < 0.22 && k === 0 ? 0.06 : 0; return {hgt, sy: 1 - 0.25 * k + st, sx: 1 + 0.15 * k - st * 0.5}; };
    const L = norm([-0.45, 0.78, -0.45]);   // 左上・手前から（z は奥が＋）
    const objs = [
      {m: meshes.sphere, x: -0.32 * S, z: -0.10 * S, r: 0.185 * S, fc: 18.5, hb: 0.36 * S, col: hex(C.sphere), ry: 0, rx: 0, rz: 0, lift: 1},
      {m: meshes.cube, x: 0.0, z: 0.14 * S, r: 0.15 * S, fc: 12, hb: 0.32 * S, col: hex(C.cube), ry: 0.45 + 0.5 * Math.sin((2 * Math.PI * f) / 40), rx: -0.18, rz: 0.06 * Math.sin(f / 7), lift: 1},
      {m: meshes.torus, x: 0.32 * S, z: -0.06 * S, r: 0.15 * S, fc: 5.5, hb: 0.32 * S, col: hex(C.torus), ry: 0.3 * Math.sin(f / 13), rx: 1.05 + 0.55 * Math.sin((2 * Math.PI * (f - 5)) / 40), rz: 0.2, lift: 1.0},
    ];
    // 床の影（先に）
    g.save(); g.filter = `blur(${0.024 * S}px)`;
    for (const o of objs) { const b = bounce(o.fc, o.hb); const q = proj(o.x + 0.04 * S, 0, o.z + 0.02 * S); const k = 1 - Math.min(1, b.hgt / (o.hb * 1.2)); g.fillStyle = `rgba(${C.shadow},${0.16 + 0.30 * k})`; g.beginPath(); g.ellipse(q[0], q[1], o.r * (0.7 + 0.45 * k) * b.sx, o.r * (0.13 + 0.10 * k), 0, 0, Math.PI * 2); g.fill(); }
    g.restore();
    // 物ごとに塗る（奥の物から）＝物どうしが重なる所で面が混ざらん
    const order = [...objs].sort((a, b) => b.z - a.z);
    for (const o of order) {
      const faces: {z: number; pts: number[]; col: string}[] = [];
      const b = bounce(o.fc, o.hb); const yr = o.r * b.sy;
      // 輪は傾くと下の端が床から浮く＝いちばん低い点を床に合わせる
      const [cX, sX, cY, sY, cZ, sZ] = [Math.cos(o.rx), Math.sin(o.rx), Math.cos(o.ry), Math.sin(o.ry), Math.cos(o.rz), Math.sin(o.rz)];
      const rot = (v: V): V => { let [X, Y, Z] = v; let t = Y * cX - Z * sX; Z = Y * sX + Z * cX; Y = t; t = X * cY + Z * sY; Z = -X * sY + Z * cY; X = t; t = X * cZ - Y * sZ; Y = X * sZ + Y * cZ; X = t; return [X, Y, Z]; };
      const RP = o.m.P.map((row) => row.map(rot)), RN = o.m.N.map((row) => row.map(rot));
      let minY = 1e9; for (const row of RP) for (const v of row) minY = Math.min(minY, v[1]);
      const cy = b.hgt - minY * yr;
      for (let i = 0; i < RP.length - 1; i++) for (let j = 0; j < RP[0].length - 1; j++) {
        const q = [RP[i][j], RP[i + 1][j], RP[i + 1][j + 1], RP[i][j + 1]].map((v) => proj(v[0] * o.r * b.sx + o.x, v[1] * yr + cy, v[2] * o.r * b.sx + o.z));
        const n = norm([0, 1, 2].map((c) => RN[i][j][c] + RN[i + 1][j][c] + RN[i + 1][j + 1][c] + RN[i][j + 1][c]) as V);
        const dif = n[0] * L[0] + n[1] * L[1] + n[2] * L[2]; const wrap = Math.pow(Math.max(0, (dif + 0.5) / 1.5), 1.2);
        const k = 0.62 + 0.48 * wrap - 0.06 * Math.max(0, -n[1]);
        faces.push({z: (q[0][2] + q[1][2] + q[2][2] + q[3][2]) / 4, pts: [q[0][0], q[0][1], q[1][0], q[1][1], q[2][0], q[2][1], q[3][0], q[3][1]], col: `rgb(${o.col.map((v) => Math.round(Math.min(255, v * k))).join(',')})`});
      }
      faces.sort((a, b) => b.z - a.z);
      g.lineJoin = 'round'; g.lineWidth = 1;
      for (const fc of faces) { const P = fc.pts; g.beginPath(); g.moveTo(P[0], P[1]); g.lineTo(P[2], P[3]); g.lineTo(P[4], P[5]); g.lineTo(P[6], P[7]); g.closePath(); g.fillStyle = fc.col; g.strokeStyle = fc.col; g.fill(); g.stroke(); }
    }
    g.save(); g.globalCompositeOperation = 'overlay'; g.globalAlpha = 0.16; g.fillStyle = g.createPattern(grain, 'repeat')!; g.fillRect(0, 0, W, H); g.restore();
  }, [f, W, H, S, meshes, grain, PER, C.sphere, C.cube, C.torus, C.shadow]);
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: `linear-gradient(180deg, ${C.wall} 0%, ${C.wall} 48%, ${C.floor} 54%, ${C.floor} 100%)`}}>
      <canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0}} />
    </div>
  );
};
