// 19 Art deco（金の放射とアーチ）— 手本 tehonM 19：黒地に細い金の枠。f0 で金の縦線1本 → f1〜15 で 25 本の放射が扇に開く（S 字・f8 で 64%）。
// 低い半円のアーチ（日の出）3 本の弧が左の根元から描かれ（外 f2〜12・中 f5.4〜16・内 f8.8〜18.8・ease-out）、2 段の門が f9.4〜12 で浮かぶ、
// 細い DECO が f6〜10 で浮かぶ、上の角飾りが f11.3〜13.5。f13〜31 に光が左から右へ 1 回走って（左半分は速く・右半分はゆっくり）、あとは止まる（動きの量 → 0）
// SVG：寸法は手本の札（中身 399x479）を測った値を U（＝幅。横長の画面では 高さ/1.2）で割った物。縦長の画面ではアーチを下に置き、上は放射の空にする
import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export type ArtDecoProps = {width?: number; height?: number; text?: string; colors?: Partial<typeof DEF>; fontFamily?: string; rays?: number};
const DEF = {bg: '#090702', bgTop: '#130f06', arch: '#070503', gold: '#c9a253', goldHi: '#f3dc8e', goldDim: '#8a7030', goldThin: '#b8ae62', text: '#e6dc92', frame: '#7d6532'};
const C0 = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
// 測った扇の開き（いちばん外の線が最後の角度の何割まで来たか・コマごと）
const FAN_F = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15];
const FAN_V = [0, 0.005, 0.027, 0.06, 0.12, 0.204, 0.318, 0.472, 0.635, 0.762, 0.855, 0.919, 0.962, 0.985, 0.997, 1];
const eo = (t: number) => 1 - Math.pow(1 - t, 2.3);   // 弧の描き込み（手本は ease-out・指数 2.3）

export const W19_ArtDeco: React.FC<ArtDecoProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, U = Math.min(W, H / 1.2);
  const C = {...DEF, ...(p.colors || {})}; const FF = p.fontFamily ?? '"Avenir Next", "Futura", system-ui, sans-serif';
  const NR = p.rays ?? 25;
  // アーチ：中心は下から 0.2U・脚は下から 0.068U まで（低い半円＝日の出）。弧の半径 0.436・0.348・0.26U
  const cx = W / 2, cy = H - 0.2 * U, legY = H - 0.068 * U, R = [0.436, 0.348, 0.26].map((k) => k * U);
  const s = interpolate(f, FAN_F, FAN_V, C0);
  const glint = interpolate(f, [13, 17, 28, 31], [-1, NR * 0.52, NR - 1, NR + 2], C0), glintOn = f >= 12 && f <= 33;   // 手本：左半分は f13〜17 で速く・右半分は f28 までゆっくり
  const rays = Array.from({length: NR}, (_, k) => {
    const tgt = 180 - ((k + 0.5) * 180) / NR, ang = ((90 + (tgt - 90) * s) * Math.PI) / 180;   // k=0 が左端（176.4°）・偶数が太い線
    const thick = k % 2 === 0, r0 = R[0], r1 = 3 * H;
    const g = glintOn ? Math.exp(-Math.pow(k - glint, 2) / 6) : 0;
    return <line key={k} x1={cx + Math.cos(ang) * r0} y1={cy - Math.sin(ang) * r0} x2={cx + Math.cos(ang) * r1} y2={cy - Math.sin(ang) * r1}
      stroke={g > 0.35 ? C.goldHi : thick ? C.gold : C.goldThin} strokeOpacity={0.92 + 0.08 * g} strokeWidth={(thick ? 0.0103 : 0.0045) * U * (1 + 0.45 * g)} />;
  });
  const arc = (r: number) => `M${cx - r} ${legY}L${cx - r} ${cy}A${r} ${r} 0 0 1 ${cx + r} ${cy}L${cx + r} ${legY}`;
  const prog = (a: number, b: number) => eo(interpolate(f, [a, b], [0, 1], C0));
  // 2 段の門：外の幅 ±0.167U（下から段まで）→ 段 cy−0.134U → 内の幅 ±0.1U → 上 cy−0.202U
  const d0 = 0.167 * U, d1 = 0.1 * U, y0 = cy - 0.134 * U, y1 = cy - 0.202 * U;
  const door = `M${cx - d0} ${legY}L${cx - d0} ${y0}L${cx - d1} ${y0}L${cx - d1} ${y1}L${cx + d1} ${y1}L${cx + d1} ${y0}L${cx + d0} ${y0}L${cx + d0} ${legY}`;
  const doorOp = interpolate(f, [9.4, 10, 12], [0, 0.7, 1], C0);
  // 角飾り（左上・右上は鏡）：縦 2 本の L ＋ 端からの横棒
  const corner = (sx: number) => {
    const X = (v: number) => (sx > 0 ? v * U : W - v * U), Y = (v: number) => v * U;
    return `M${X(0.04)} ${Y(0.068)}L${X(0.04)} ${Y(0.246)}L${X(0.12)} ${Y(0.246)}M${X(0.08)} ${Y(0.068)}L${X(0.08)} ${Y(0.296)}L${X(0.16)} ${Y(0.296)}M${X(0.0)} ${Y(0.2)}L${X(0.08)} ${Y(0.2)}`;
  };
  const cornerDraw = interpolate(f, [11.3, 13.5], [0, 1], C0);
  const textOp = interpolate(f, [6, 10], [0, 1], C0);
  const fs = 0.148 * U, ls = 0.1 * fs, tY = cy - 0.688 * U + 0.052 * U;   // 字の高さ 0.105U・幅 約 0.46U（手本 0.45U）・字の中心はアーチの中心の 0.688U 上
  const bi = 0.02 * U;
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: `radial-gradient(ellipse at 50% ${((cy - 0.7 * U) / H) * 100}%, ${C.bgTop} 0%, ${C.bg} 70%)`}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <rect x={bi} y={bi} width={W - 2 * bi} height={H - 2 * bi} fill="none" stroke={C.frame} strokeOpacity={0.8} strokeWidth={0.005 * U} />
        {[-1, 1].map((sx) => <path key={sx} d={corner(sx)} fill="none" stroke={C.goldDim} strokeWidth={0.005 * U} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - cornerDraw} />)}
        <g>{rays}</g>
        <path d={`M${cx - R[0]} ${legY}L${cx - R[0]} ${cy}A${R[0]} ${R[0]} 0 0 1 ${cx + R[0]} ${cy}L${cx + R[0]} ${legY}Z`} fill={C.arch} />
        {[[R[0], 2, 12, 0.01], [R[1], 5.4, 16, 0.0075], [R[2], 8.8, 18.8, 0.0075]].map(([r, a, b, w], i) => (
          <path key={i} d={arc(r)} fill="none" stroke={C.gold} strokeWidth={w * U} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - prog(a, b)} />
        ))}
        <path d={door} fill="none" stroke={C.goldDim} strokeWidth={0.0063 * U} strokeOpacity={doorOp} />
        <text x={cx + ls / 2} y={tY} textAnchor="middle" fill={C.text} stroke={C.text} strokeWidth={0.004 * U} opacity={textOp}
          style={{fontFamily: FF, fontWeight: 100, fontSize: fs, letterSpacing: ls}}>{p.text ?? 'DECO'}</text>
      </svg>
    </div>
  );
};
