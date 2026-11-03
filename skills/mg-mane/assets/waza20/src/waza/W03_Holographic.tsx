// 03 Holographic（虹の薄膜・ホログラム）— 手本 tehonM 03：画面の幅いっぱいの、ねじれて浅いひだの寄った平たい輪が、倒れた向き（縦横比 0.67）から正面寄り（0.96）へ起き上がりながら回る。面に細かい虹の縞が流れる
// canvas 2D に自前の小さな 3D（輪を 720x120 の四角に割る→回す→遠い順に塗る）。色＝見る角度（1−|法線の z|）と帯の幅の位置と時間で色相を回す（薄膜の干渉の見た目）
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export type HolographicProps = {width?: number; height?: number; colors?: Partial<typeof DEF>; sat?: number; light?: number; detail?: number; bands?: number};
const DEF = {bgCenter: '#f7eef5', bgEdge: '#e9d9e4', hueShift: 0};
// 測った起き上がり：外形の縦横比 f0 0.67・f12 0.80・f24 0.87・f34 0.96（ほぼ一定の速さ）。そのあとは同じ速さで少しずつ起き続ける
const tilt = (f: number) => (f <= 34 ? 30 + 36 * (f / 34) + 4 * Math.sin((Math.PI * f) / 34) : 66 + 0.5 * (f - 34));

export const W03_Holographic: React.FC<HolographicProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H);
  const C = {...DEF, ...(p.colors || {})}; const K = p.bands ?? 1;   // bands＝縞の細かさ（1＝手本どおり）
  const NU = Math.round(720 * (p.detail ?? 1)), NV = Math.round(120 * (p.detail ?? 1));   // 細かく割る（1 枚 ≒ 3px）＝細い縞がモザイクにならん
  const ref = useRef<HTMLCanvasElement>(null);
  const idx = useMemo(() => { const a: number[] = []; for (let i = 0; i < NU; i++) for (let j = 0; j < NV; j++) a.push(i, j); return a; }, [NU, NV]);
  useLayoutEffect(() => {
    const cv = ref.current; if (!cv) return; const g = cv.getContext('2d')!; g.clearRect(0, 0, W, H);
    const t = f / 30; const R0 = 0.375 * S, A = 0.145 * S, B = 0.06 * S;   // 外の幅 ≒ 1.0W・穴 ≒ 0.55W・輪の面積 ≒ 0.41〜0.5W²（手本の札を測った値）・帯の断面は平たい楕円（面が丸い＝見る角度が帯の幅で変わり縞になる）
    const al = (tilt(f) * Math.PI) / 180, spin = 0.6 + f * 0.05;   // 2.9°/コマ
    const ca = Math.cos(al), sa = Math.sin(al), cs = Math.cos(spin), ss = Math.sin(spin);
    const D = 3.2 * S, cx = W / 2, cy = H / 2;
    const X = new Float32Array((NU + 1) * (NV + 1)), Y = new Float32Array(X.length), Z = new Float32Array(X.length);
    for (let i = 0; i <= NU; i++) {
      const u = (i / NU) * Math.PI * 2; const Ru = R0 * (1 + 0.035 * Math.sin(8 * u + 2.4 * t + 1.1)); const yw = 0.04 * S * Math.sin(3 * u - 2.2 * t);
      const tau = 1.5 * u + 1.8 * t + 0.22 * Math.sin(8 * u + 2.4 * t),   // 1 周で 1.5 回ねじる（長い縞）＋8 つの浅いひだ ±13°（丸い外形）。ひだだけ（±26〜49°）は縞が細かい輪切れ・花びらになった
        ct = Math.cos(tau), st = Math.sin(tau), cu = Math.cos(u), su = Math.sin(u);
      for (let j = 0; j <= NV; j++) {
        const v = (j / NV) * Math.PI * 2; const a = A * Math.cos(v), b = B * Math.sin(v);
        const rr = a * ct - b * st, yy = a * st + b * ct;
        let x = (Ru + rr) * cu, y = yw + yy, z = (Ru + rr) * su;
        const x1 = x * cs + z * ss, z1 = -x * ss + z * cs; x = x1; z = z1;   // 輪の軸（Y）まわりに回す
        const y2 = y * ca - z * sa, z2 = y * sa + z * ca;                     // X まわりに起こす（0°＝真横・90°＝正面）
        const k = i * (NV + 1) + j; X[k] = x; Y[k] = y2; Z[k] = z2;
      }
    }
    type Fc = {z: number; pts: number[]; col: string};
    const faces: Fc[] = [];
    for (let q = 0; q < idx.length; q += 2) {
      const i = idx[q], j = idx[q + 1]; const k00 = i * (NV + 1) + j, k10 = (i + 1) * (NV + 1) + j, k11 = (i + 1) * (NV + 1) + j + 1, k01 = i * (NV + 1) + j + 1;
      const ux = X[k11] - X[k00], uy = Y[k11] - Y[k00], uz = Z[k11] - Z[k00], vx = X[k01] - X[k10], vy = Y[k01] - Y[k10], vz = Z[k01] - Z[k10];
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; const nn = Math.hypot(nx, ny, nz) || 1; nx /= nn; ny /= nn; nz /= nn;
      const zc = (Z[k00] + Z[k10] + Z[k11] + Z[k01]) / 4;
      const ndv = Math.abs(nz);
      const u = i / NU, v = j / NV;
      // 縞（手本は帯の幅に 4〜5 本・縁に寄らず並ぶ）：見る角度 x=1−|nz| を 約 1.8 周（x^0.7 で縁の詰まりをならし、0.5 で止める）＋帯の幅の位置 cos(2πv+πu) を 0.9 周＋輪にそって小波＋時間で流れる
      // v の項は必ず「2πv＋πu」の形（1.5 回ねじり＝1 周で v が v+0.5 に入れ替わる。sin(2πv) だけだと継ぎ目で色が切れる）
      const x = Math.pow(Math.min(1 - ndv, 0.5), 0.7) * 1.3, wv = Math.cos(2 * Math.PI * v + Math.PI * u) * Math.min(1, ndv / 0.35);
      // 縁と折れ目（横向きの面）は灰色になりやすい：x は 0.5 で止め（×1.3 で平らな所の縞の数は保つ）、帯の幅の項は横向きほど弱める（細い所に縞が何周も詰まり、縮めると混ざって灰色の線に見えた）
      const hue = ((360 * (K * (2.3 * x + 0.9 * wv + 0.1 * Math.sin(15 * Math.PI * u + 2 * Math.PI * v)) + 0.45 * t) + 300 + C.hueShift) % 360 + 360) % 360;
      const face = Math.min(1, Math.max(0, (ndv - 0.55) / 0.3));   // 光の白い点は正面寄りの広い面だけ（手本の白い点も広い面にだけ出る。縁の銀色の線の元はこれではなく、詰まった縞＝上の x と wv）
      const spec = Math.pow(Math.max(0, -0.35 * nx + 0.55 * ny + 0.76 * Math.abs(nz)), 30) * face * face;
      const l = (p.light ?? 64) + 24 * spec, s = (p.sat ?? 88) - 30 * spec;
      const pts: number[] = [];
      for (const k of [k00, k10, k11, k01]) { const sc = D / (D + Z[k]); pts.push(cx + X[k] * sc, cy - Y[k] * sc); }
      faces.push({z: zc, pts, col: `hsl(${hue.toFixed(1)},${s.toFixed(0)}%,${l.toFixed(0)}%)`});
    }
    faces.sort((a, b) => b.z - a.z);
    g.lineJoin = 'round'; g.lineWidth = 0.5;
    for (const fc of faces) { const P = fc.pts; g.beginPath(); g.moveTo(P[0], P[1]); g.lineTo(P[2], P[3]); g.lineTo(P[4], P[5]); g.lineTo(P[6], P[7]); g.closePath(); g.fillStyle = fc.col; g.strokeStyle = fc.col; g.fill(); g.stroke(); }
  }, [f, W, H, S, idx, NU, NV, K, C.hueShift, p.sat, p.light]);
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: `radial-gradient(circle at 50% 46%, ${C.bgCenter} 0%, ${C.bgEdge} ${0.9 * S}px)`}}>
      <canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0, filter: `blur(${0.0011 * S}px)`}} />
    </div>
  );
};
