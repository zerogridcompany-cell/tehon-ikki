// 04 Neon glow（ネオン管が灯る）— 手本 手本M 04：f0〜1 は字が消えた管（暗い紫）・f2 で1コマで点く（白い芯＋桃色の光）。
// 後ろはピンクと水色の角丸の枠が奥から手前へ流れるトンネル（8コマで1枠ぶん・ゆっくり ±3° 傾く）
// CSS：枠＝border＋box-shadow の光／字＝text-shadow を4重。霧＝中心が明るい放射グラデ
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export type NeonGlowProps = {width?: number; height?: number; text?: string; colors?: Partial<typeof DEF>; onFrame?: number; fontFamily?: string};
const DEF = {bgCenter: '#8f7aa3', bgMid: '#55456a', bgEdge: '#241c30', tubeA: '#ff5fd2', tubeB: '#68e3f0', textOn: '#ffe0f8', glow: '#ff3fd0', glowDeep: '#c21fae', textOff: '#5a2f55'};
const PERIOD = 8, Q = 1.28, N = 13;   // 測った値：枠は 8 コマで1つ分 手前へ（動きの山 f6・13・21・29）・隣の枠の大きさの比 1.28

export const W04_NeonGlow: React.FC<NeonGlowProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H);
  const C = {...DEF, ...(p.colors || {})};
  const text = p.text ?? 'NEON'; const on = f >= (p.onFrame ?? 2);
  const roll = 3 * Math.sin((2 * Math.PI * f) / 40);
  const ph = f / PERIOD, base = Math.floor(ph), fr = ph - base;
  const rects = [] as React.ReactNode[];
  for (let k = N - 1; k >= 0; k--) {
    const sc = Math.pow(Q, k + fr - 3);                   // k が大きいほど手前（大きい）
    const id = k - base;                                   // 枠ごとの番号（色が枠についていく）
    const col = ((id % 2) + 2) % 2 === 0 ? C.tubeA : C.tubeB;
    const w = 0.30 * S * sc, h = 0.235 * S * sc;
    const depth = Math.min(1, Math.max(0, (k + fr - 1) / (N - 2)));
    const op = Math.min(1, (k + fr) / 2.2) * (0.55 + 0.45 * depth);
    const bw = Math.max(2, 0.0045 * S * Math.sqrt(sc));
    rects.push(
      <div key={id} style={{position: 'absolute', left: W / 2 - w / 2, top: H * 0.47 - h / 2, width: w, height: h, borderRadius: 0.025 * S * sc + 6, border: `${bw}px solid ${col}`,
        boxShadow: `0 0 ${8 * Math.sqrt(sc)}px ${col}, 0 0 ${22 * Math.sqrt(sc)}px ${col}aa, inset 0 0 ${10 * Math.sqrt(sc)}px ${col}88`,
        opacity: op, filter: depth < 0.35 ? `blur(${(0.35 - depth) * 6}px)` : undefined, transform: `rotate(${roll * (0.25 + 0.75 * depth)}deg)`}} />,
    );
  }
  const fs = Math.min(0.27 * S, (0.84 * W) / (text.length * 0.66));
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: `radial-gradient(ellipse at 50% 47%, ${C.bgCenter} 0%, ${C.bgMid} ${0.38 * S}px, ${C.bgEdge} ${1.05 * Math.max(W, H) * 0.6}px)`}}>
      {rects}
      <div style={{position: 'absolute', left: 0, right: 0, top: H * 0.47 - fs * 0.62, textAlign: 'center', fontFamily: p.fontFamily ?? 'system-ui, -apple-system, Helvetica, Arial, sans-serif', fontWeight: 800, fontSize: fs, lineHeight: 1.2, letterSpacing: '0.02em',
        color: on ? C.textOn : C.textOff,
        textShadow: on ? `0 0 ${0.006 * S}px #ffffff, 0 0 ${0.016 * S}px #ff9be8, 0 0 ${0.035 * S}px ${C.glow}, 0 0 ${0.07 * S}px ${C.glow}, 0 0 ${0.12 * S}px ${C.glowDeep}, 0 0 ${0.2 * S}px ${C.glowDeep}` : `0 0 ${0.004 * S}px #00000088`}}>{text}</div>
      {on && <div style={{position: 'absolute', left: W / 2 - 0.5 * S, top: H * 0.47 - 0.25 * S, width: S, height: 0.5 * S, borderRadius: '50%', background: `radial-gradient(ellipse, ${C.glow}33 0%, ${C.glow}00 70%)`, mixBlendMode: 'screen'}} />}
    </div>
  );
};
