// 06 Glassmorphism（すりガラスのUI）— 手本 手本M 06：ぼけた色の玉（ピンク・青・ミント・橙）の上に、すりガラスの札が3枚。
// 曲の進みが伸びる（1.47%/コマ）・トグルが f16 で入る / f33 で切れる（3コマで滑る）・歩数が 4.44/コマで数え上がる・札はゆっくり浮く
// CSS：backdrop-filter blur＋白の薄い板＋1.5px の白い縁。数字は tabular-nums
import React from 'react';
import {interpolate, Easing, useCurrentFrame, useVideoConfig} from 'remotion';

export type GlassmorphismProps = {width?: number; height?: number; colors?: Partial<typeof DEF>; title?: string; subtitle?: string; temp?: string; sky?: string; label?: string; startCount?: number; perFrame?: number; fontFamily?: string};
const DEF = {white: '#f6f4fb', pink: '#ff4f9e', blue: '#5c78f5', mint: '#36ecc2', teal: '#14b896', orange: '#f7b44e', on: '#23c55e'};
const TOG = [16, 33, 50, 67];   // 測った値：f16 で入る・f33 で切れる（17コマごと）

export const W06_Glassmorphism: React.FC<GlassmorphismProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H), u = Math.min(W / 330, H / 380);
  const C = {...DEF, ...(p.colors || {})};
  const FF = p.fontFamily ?? 'system-ui, -apple-system, Helvetica, Arial, sans-serif';
  const blob = (x: number, y: number, r: number, col: string, ph: number) => {
    const dx = Math.sin(f / 22 + ph) * 26 * u, dy = Math.cos(f / 26 + ph * 1.7) * 30 * u;
    return <div style={{position: 'absolute', left: x * W - r * S + dx, top: y * H - r * S + dy, width: 2 * r * S, height: 2 * r * S, borderRadius: '50%', background: col, filter: `blur(${0.07 * S}px)`}} />;
  };
  // トグル：入る時・切れる時に 3 コマで滑る（ease-in-out）
  let tog = 0; for (let i = 0; i < TOG.length; i++) { const k = interpolate(f, [TOG[i] - 1, TOG[i] + 2], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)}); tog = i % 2 === 0 ? Math.max(tog, k) : tog * (1 - k); }
  const prog = Math.min(0.985, 0.12 + 0.0147 * f);
  const count = Math.round((p.startCount ?? 8103) + (p.perFrame ?? 4.44) * f).toLocaleString('en-US');
  const cw = 270 * u, x0 = (W - cw) / 2;
  const card = (y: number, h: number, ph: number, children: React.ReactNode) => (
    <div style={{position: 'absolute', left: x0, top: y + Math.sin(f / 21 + ph) * 2.2 * u, width: cw, height: h, borderRadius: 22 * u, background: 'rgba(255,255,255,0.20)', border: `${1.5 * u}px solid rgba(255,255,255,0.55)`,
      backdropFilter: `blur(${10 * u}px) saturate(1.35)`, WebkitBackdropFilter: `blur(${10 * u}px) saturate(1.35)`, boxShadow: `0 ${8 * u}px ${24 * u}px rgba(40,20,90,0.10), inset 0 ${1 * u}px 0 rgba(255,255,255,0.45)`, overflow: 'hidden', fontFamily: FF, color: '#fff'}}>{children}</div>
  );
  const top = H / 2 - 156 * u;   // 3枚の束（高さ 312u）を縦の真ん中に
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: C.white}}>
      {blob(0.14, 0.30, 0.42, C.pink, 0)}{blob(0.86, 0.26, 0.40, C.blue, 1.3)}{blob(0.22, 0.70, 0.40, C.mint, 2.1)}{blob(0.62, 0.62, 0.30, C.teal, 2.9)}{blob(0.95, 0.80, 0.25, C.orange, 3.7)}{blob(0.78, 0.47, 0.22, C.blue, 4.4)}
      {card(top, 112 * u, 0, <>
        <div style={{position: 'absolute', left: 16 * u, top: 18 * u, width: 48 * u, height: 48 * u, borderRadius: 12 * u, background: 'linear-gradient(135deg,#f472b6 0%,#a855f7 55%,#6366f1 100%)', opacity: 0.85}} />
        <div style={{position: 'absolute', left: 78 * u, top: 22 * u, fontSize: 19 * u, fontWeight: 800}}>{p.title ?? 'Midnight Glass'}</div>
        <div style={{position: 'absolute', left: 78 * u, top: 46 * u, fontSize: 12.5 * u, fontWeight: 500, opacity: 0.82}}>{p.subtitle ?? 'Frosted Hours'}</div>
        <div style={{position: 'absolute', left: 18 * u, right: 18 * u, top: 86 * u, height: 5 * u, borderRadius: 3 * u, background: 'rgba(255,255,255,0.32)'}}>
          <div style={{width: `${prog * 100}%`, height: '100%', borderRadius: 3 * u, background: '#fff'}} /></div>
      </>)}
      {card(top + 128 * u, 92 * u, 1.4, <>
        <div style={{position: 'absolute', left: 18 * u, top: 14 * u, fontSize: 30 * u, fontWeight: 800}}>{p.temp ?? '24°'}</div>
        <div style={{position: 'absolute', left: 18 * u, top: 56 * u, fontSize: 12.5 * u, fontWeight: 500, opacity: 0.85}}>{p.sky ?? 'Clear sky'}</div>
        <div style={{position: 'absolute', right: 18 * u, top: 31 * u, width: 50 * u, height: 28 * u, borderRadius: 14 * u, background: `rgba(${Math.round(255 + (35 - 255) * tog)},${Math.round(255 + (197 - 255) * tog)},${Math.round(255 + (94 - 255) * tog)},${0.35 + 0.65 * tog})`, border: `${1 * u}px solid rgba(255,255,255,0.5)`}}>
          <div style={{position: 'absolute', top: 3 * u, left: (3 + 22 * tog) * u, width: 22 * u, height: 22 * u, borderRadius: '50%', background: '#fff', boxShadow: `0 ${1 * u}px ${3 * u}px rgba(0,0,0,0.2)`}} /></div>
      </>)}
      {card(top + 236 * u, 76 * u, 2.6, <>
        <div style={{position: 'absolute', left: 20 * u, top: 29 * u, fontSize: 11 * u, fontWeight: 800, letterSpacing: '0.14em', opacity: 0.9}}>{p.label ?? 'STEPS'}</div>
        <div style={{position: 'absolute', left: 82 * u, top: 18 * u, fontSize: 28 * u, fontWeight: 800, fontVariantNumeric: 'tabular-nums'}}>{count}</div>
      </>)}
    </div>
  );
};
