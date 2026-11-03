// 16 Bauhaus（原色の立体が積まれる）— 手本 tehonM 16：生成りの地に白い台。黒い箱（f2→5）・赤い球（f5→9・1回小さく弾む）・青い円柱（f8→12）・
// 黄色の半円（f11→15・落ちながら向きを変える）が上から順に落ちて着く（重力＝落ちるほど速い・4コマ前後）。着いたら全体がゆっくり回る（0.35°/コマ）
// canvas 2D に自前の小さな 3D（箱・円柱・半円の厚板を面に割り、遠い順に塗る・面ごとの平らな陰）。球は放射グラデの丸。影は台の上のぼかした楕円
import React, {useLayoutEffect, useRef} from 'react';
import {interpolate, Easing, useCurrentFrame, useVideoConfig} from 'remotion';

export type BauhausProps = {width?: number; height?: number; colors?: Partial<typeof DEF>};
const DEF = {bg: '#eee5cf', slabTop: '#f8f3e8', slabSide: '#d8cfbf', black: '#262428', red: '#d02a36', blue: '#1b45b5', yellow: '#f2b400', shadow: '90,78,60'};
type V = [number, number, number];
const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const box = (sx: number, sy: number, sz: number): V[][] => { const x = sx / 2, y = sy / 2, z = sz / 2; const P: V[] = [[-x, -y, -z], [x, -y, -z], [x, y, -z], [-x, y, -z], [-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z]]; return [[0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7], [1, 5, 6, 2], [3, 2, 6, 7], [4, 5, 1, 0]].map((q) => q.map((i) => P[i])); };
const cyl = (r: number, h: number, n = 40): V[][] => { const F: V[][] = []; const top: V[] = [], bot: V[] = []; for (let i = 0; i < n; i++) { const a0 = (i / n) * Math.PI * 2, a1 = ((i + 1) / n) * Math.PI * 2; F.push([[r * Math.cos(a0), -h / 2, r * Math.sin(a0)], [r * Math.cos(a1), -h / 2, r * Math.sin(a1)], [r * Math.cos(a1), h / 2, r * Math.sin(a1)], [r * Math.cos(a0), h / 2, r * Math.sin(a0)]]); top.push([r * Math.cos(-a0), h / 2, r * Math.sin(-a0)]); bot.push([r * Math.cos(a0), -h / 2, r * Math.sin(a0)]); } F.push(top, bot); return F; };
const halfDisc = (r: number, t: number, n = 32): V[][] => { const F: V[][] = []; const fr: V[] = [], bk: V[] = []; for (let i = 0; i <= n; i++) { const a = (i / n) * Math.PI; fr.push([r * Math.cos(a), r * Math.sin(a), t / 2]); bk.push([r * Math.cos(Math.PI - a), r * Math.sin(Math.PI - a), -t / 2]); } for (let i = 0; i < n; i++) { const a0 = (i / n) * Math.PI, a1 = ((i + 1) / n) * Math.PI; F.push([[r * Math.cos(a0), r * Math.sin(a0), -t / 2], [r * Math.cos(a1), r * Math.sin(a1), -t / 2], [r * Math.cos(a1), r * Math.sin(a1), t / 2], [r * Math.cos(a0), r * Math.sin(a0), t / 2]]); } F.push(fr, bk, [[-r, 0, t / 2], [r, 0, t / 2], [r, 0, -t / 2], [-r, 0, -t / 2]]); return F; };
const MESH = {cube: box(0.85, 0.85, 0.85), cyl: cyl(0.32, 1.15), half: halfDisc(0.5, 0.22), slab: box(3.3, 0.32, 2.5)};
// 落ちる：start→land の間 高さ H0·(1-(t/T)²)（＝重力）。着いた後の小さな弾み（球だけ）
const drop = (f: number, s: number, l: number, h0: number, bounce = 0) => { if (f < s) return h0 * 1.6; if (f < l) { const t = (f - s) / (l - s); return h0 * (1 - t * t); } const b = f - l; return bounce && b < 2 ? bounce * Math.sin((b / 2) * Math.PI) : 0; };

export const W16_Bauhaus: React.FC<BauhausProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H);
  const C = {...DEF, ...(p.colors || {})};
  const ref = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const cv = ref.current; if (!cv) return; const g = cv.getContext('2d')!; g.clearRect(0, 0, W, H);
    const th = ((32 + Math.max(0, f - 15) * 0.6) * Math.PI) / 180, el = (27 * Math.PI) / 180, D = 8, sc = 0.40 * S, cx = W / 2, cy = H * 0.56;
    const ct = Math.cos(th), st = Math.sin(th), ce = Math.cos(el), se = Math.sin(el);
    const cam = (v: V): V => { const x = v[0] * ct - v[2] * st, z0 = v[0] * st + v[2] * ct; const y = v[1] * ce + z0 * se, z = -v[1] * se + z0 * ce; return [x, y, z]; };
    const pr = (c: V) => { const s = (D / (D + c[2])) * sc; return [cx + c[0] * s, cy - c[1] * s]; };
    const L: V = [-0.5, 0.75, -0.45]; const ln = Math.hypot(...L); L[0] /= ln; L[1] /= ln; L[2] /= ln;
    const faces: {z: number; pts: number[][]; col: string}[] = [];
    const Lc = cam(L);
    // 面の向きは「物の真ん中から外へ」にそろえてから、カメラ（cam 空間の (0,0,-D)）を向く面だけ塗る
    const addMesh = (m: V[][], pos: V, ry: number, base: number[], rx = 0, faceCol?: (i: number) => number[] | null, out = faces) => { const cr = Math.cos(ry), sr = Math.sin(ry), cx2 = Math.cos(rx), sx2 = Math.sin(rx);
      const W3 = m.map((q) => q.map(([x, y, z]) => { const y1 = y * cx2 - z * sx2, z1 = y * sx2 + z * cx2; return cam([x * cr + z1 * sr + pos[0], y1 + pos[1], -x * sr + z1 * cr + pos[2]] as V); }));
      let mx = 0, my = 0, mz = 0, mn = 0; for (const q of W3) for (const v of q) { mx += v[0]; my += v[1]; mz += v[2]; mn++; } mx /= mn; my /= mn; mz /= mn;
      W3.forEach((c, fi) => {
        const a = c[0], b = c[1], d = c[Math.floor(c.length / 2)]; const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2], vx = d[0] - a[0], vy = d[1] - a[1], vz = d[2] - a[2];
        let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; const nn = Math.hypot(nx, ny, nz) || 1; nx /= nn; ny /= nn; nz /= nn;
        let fx = 0, fy = 0, fz = 0; for (const v of c) { fx += v[0]; fy += v[1]; fz += v[2]; } fx /= c.length; fy /= c.length; fz /= c.length;
        if (nx * (fx - mx) + ny * (fy - my) + nz * (fz - mz) < 0) { nx = -nx; ny = -ny; nz = -nz; }
        if (nx * (0 - fx) + ny * (0 - fy) + nz * (-D - fz) <= 0) return;   // 裏
        const k = 0.55 + 0.55 * Math.max(0, nx * Lc[0] + ny * Lc[1] + nz * Lc[2]);
        const bc = (faceCol && faceCol(fi)) || base;
        out.push({z: fz, pts: c.map(pr), col: `rgb(${bc.map((v) => Math.round(Math.min(255, v * k))).join(',')})`}); }); };
    const fill = (pts: number[][], col: string) => { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (const q of pts.slice(1)) g.lineTo(q[0], q[1]); g.closePath(); g.fillStyle = col; g.strokeStyle = col; g.lineWidth = 1; g.fill(); g.stroke(); };
    // 台の下の影 → 台（上の面＝白・横の面＝陰）
    g.save(); g.filter = `blur(${0.03 * S}px)`; const sp = [[-1.75, -0.36, -1.35], [1.85, -0.36, -1.35], [1.95, -0.36, 1.45], [-1.65, -0.36, 1.45]].map((v) => pr(cam([v[0] + 0.25, v[1], v[2] + 0.1] as V))); fill(sp, `rgba(${C.shadow},0.28)`); g.restore();
    const slabF: typeof faces = []; addMesh(MESH.slab, [0, -0.16, 0], 0, hex(C.slabSide), 0, (i) => (i === 4 ? hex(C.slabTop) : null), slabF);
    slabF.sort((a2, b2) => b2.z - a2.z); for (const s2 of slabF) fill(s2.pts, s2.col);
    // 物の位置と落ち
    const yc = drop(f, 2, 5, 3.4), ys = drop(f, 5, 9, 3.2, 0.13), yy = drop(f, 8, 12, 3.2), yh = drop(f, 11, 15, 3.0);
    const hRot = interpolate(f, [11, 16], [-0.9, 0.05], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
    const hTilt = interpolate(f, [11, 15], [-0.5, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    const objs = [{pos: [-0.42, 0.425, 0.42] as V, y: yc, r: 0.55}, {pos: [0.78, 0.45, 0.12] as V, y: ys, r: 0.5}, {pos: [-0.78, 0.575, -0.28] as V, y: yy, r: 0.4}, {pos: [0.08, 0, -0.55] as V, y: yh, r: 0.5}];
    // 台の上の影（近づくほど濃く小さく）
    g.save(); g.filter = `blur(${0.018 * S}px)`;
    for (const o of objs) { if (o.y > 3) continue; const k = 1 - Math.min(1, o.y / 3); const c = pr(cam([o.pos[0] + 0.18, 0.001, o.pos[2] - 0.12])); g.fillStyle = `rgba(${C.shadow},${0.10 + 0.32 * k})`; g.beginPath(); g.ellipse(c[0], c[1], o.r * sc * 0.75 * (1.3 - 0.3 * k), o.r * sc * 0.32 * (1.3 - 0.3 * k), 0, 0, Math.PI * 2); g.fill(); }
    g.restore();
    addMesh(MESH.cube, [objs[0].pos[0], objs[0].pos[1] + yc, objs[0].pos[2]], 0.25, hex(C.black));
    addMesh(MESH.cyl, [objs[2].pos[0], objs[2].pos[1] + yy, objs[2].pos[2]], 0, hex(C.blue));
    addMesh(MESH.half, [objs[3].pos[0], objs[3].pos[1] + yh, objs[3].pos[2]], hRot, hex(C.yellow), hTilt);
    const sc3 = cam([objs[1].pos[0], objs[1].pos[1] + ys, objs[1].pos[2]]);
    faces.push({z: sc3[2], pts: [], col: 'SPHERE'});
    faces.sort((a, b) => b.z - a.z);
    for (const fc of faces) {
      if (fc.col === 'SPHERE') { const c = pr(sc3), rr = 0.45 * (D / (D + sc3[2])) * sc; const gr = g.createRadialGradient(c[0] - 0.35 * rr, c[1] - 0.4 * rr, rr * 0.1, c[0], c[1], rr); gr.addColorStop(0, '#f0525b'); gr.addColorStop(0.55, C.red); gr.addColorStop(1, '#8e1622'); g.fillStyle = gr; g.beginPath(); g.arc(c[0], c[1], rr, 0, Math.PI * 2); g.fill(); continue; }
      fill(fc.pts, fc.col);
    }
  }, [f, W, H, S, C.black, C.red, C.blue, C.yellow]);
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: `radial-gradient(ellipse at 50% 45%, #f6efde 0%, ${C.bg} 60%, #e3d8bf 100%)`}}>
      <canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0}} />
    </div>
  );
};
