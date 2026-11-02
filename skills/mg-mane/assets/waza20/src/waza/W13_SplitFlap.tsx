// 13 Split-flap（空港の案内板）— 手本 手本M 13：黒地に 3段×6枚のパタパタ板。字は2コマごとにめくれて、左上から順に止まる
// 測った止まるコマ：MAKE＝M8・A11・K13・E15／IT＝I18・T21／MOVE＝M18・O21・V23・E26（＝8＋段の遅れ[0,10,10]＋2.7×何字目）。上に DEPARTURES（金）・下に GATE C · ON TIME（灰）
// CSS：板を上半分・下半分の2枚に分け、めくれ中のコマは「上＝新しい字／下＝古い字」＋落ちる羽を scaleY で潰す
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export type SplitFlapProps = {width?: number; height?: number; rows?: string[]; cols?: number; header?: string; footer?: string; start?: number; rowDelay?: number[]; perChar?: number; colors?: Partial<typeof DEF>; fontFamily?: string};
const DEF = {bg: '#0c0c0c', tile: '#242424', tileTop: '#2b2b2b', split: '#0a0a0a', ch: '#f0efeb', head: '#f2b51f', foot: '#8a8a86'};
const ABC = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
const rch = (a: number, b: number) => ABC[Math.abs(Math.imul(a * 73856093 ^ b * 19349663, 2654435761)) % ABC.length];

export const W13_SplitFlap: React.FC<SplitFlapProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height;
  const C = {...DEF, ...(p.colors || {})}; const FF = p.fontFamily ?? 'Menlo, ui-monospace, "SF Mono", monospace';
  const rows = p.rows ?? ['MAKE', '  IT', 'MOVE']; const COLS = p.cols ?? 6;
  const st = p.start ?? 8, rd = p.rowDelay ?? [0, 10, 10, 18, 26], pc = p.perChar ?? 2.7;
  const gap = 0.012 * W, tw = (0.92 * W - gap * (COLS - 1)) / COLS, th = tw * 1.3, x0 = (W - (tw * COLS + gap * (COLS - 1))) / 2;
  const boardH = rows.length * th + (rows.length - 1) * gap * 2.2, y0 = H / 2 - boardH / 2;
  const tiles = [] as React.ReactNode[];
  rows.forEach((row, r) => {
    const firstIdx = row.search(/\S/);
    for (let c = 0; c < COLS; c++) {
      const target = row[c] && row[c] !== ' ' ? row[c] : '';
      const x = x0 + c * (tw + gap), y = y0 + r * (th + gap * 2.2);
      let cur = target, prev = target, phase = 2;   // phase 0,1＝めくれ途中・2＝止まり
      if (target) {
        const settle = Math.round(st + (rd[r] ?? r * 10) + pc * (c - Math.max(0, firstIdx)));
        if (f < settle) { const step = Math.floor(f / 2); cur = rch(r * 10 + c, step + 1); prev = rch(r * 10 + c, step); phase = f % 2; }
        else if (f < settle + 2) { prev = rch(r * 10 + c, Math.floor((settle - 1) / 2)); phase = f - settle; cur = target; }
      }
      const half = (show: string, top: boolean, extra?: React.CSSProperties) => (
        <div style={{position: 'absolute', left: 0, width: tw, height: th / 2, top: top ? 0 : th / 2, overflow: 'hidden', background: top ? C.tileTop : C.tile, borderRadius: top ? `${0.07 * tw}px ${0.07 * tw}px 0 0` : `0 0 ${0.07 * tw}px ${0.07 * tw}px`, ...extra}}>
          <div style={{position: 'absolute', left: 0, width: tw, height: th, top: top ? 0 : -th / 2, lineHeight: `${th}px`, textAlign: 'center', fontFamily: FF, fontWeight: 800, fontSize: th * 0.8, color: C.ch}}>{show}</div>
        </div>
      );
      tiles.push(
        <div key={`${r}-${c}`} style={{position: 'absolute', left: x, top: y, width: tw, height: th, boxShadow: `0 ${0.01 * W}px ${0.02 * W}px rgba(0,0,0,0.5)`}}>
          {half(phase === 2 ? cur : cur, true)}
          {half(phase === 2 ? cur : prev, false)}
          {phase === 0 && half(prev, true, {transformOrigin: '50% 100%', transform: 'scaleY(0.42)', filter: 'brightness(0.8)'})}
          {phase === 1 && half(cur, false, {transformOrigin: '50% 0%', transform: 'scaleY(0.5)', filter: 'brightness(1.15)'})}
          <div style={{position: 'absolute', left: 0, right: 0, top: th / 2 - 0.006 * W, height: 0.012 * W, background: C.split}} />
          <div style={{position: 'absolute', left: -0.004 * W, top: th / 2 - 0.014 * W, width: 0.008 * W, height: 0.028 * W, background: '#111', borderRadius: 2}} />
          <div style={{position: 'absolute', right: -0.004 * W, top: th / 2 - 0.014 * W, width: 0.008 * W, height: 0.028 * W, background: '#111', borderRadius: 2}} />
        </div>,
      );
    }
  });
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: C.bg, fontFamily: 'system-ui, -apple-system, Helvetica, sans-serif'}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: y0 - 0.13 * W, textAlign: 'center', color: C.head, fontWeight: 800, fontSize: 0.034 * W, letterSpacing: '0.42em', paddingLeft: '0.42em'}}>{p.header ?? 'DEPARTURES'}</div>
      {tiles}
      <div style={{position: 'absolute', left: 0, right: 0, top: y0 + boardH + 0.09 * W, textAlign: 'center', color: C.foot, fontWeight: 700, fontSize: 0.03 * W, letterSpacing: '0.34em', paddingLeft: '0.34em'}}>{p.footer ?? 'GATE C · ON TIME'}</div>
    </div>
  );
};
