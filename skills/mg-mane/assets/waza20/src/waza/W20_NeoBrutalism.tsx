// 20 Neo-brutalism（太い黒枠とずらした影のUI）— 手本 tehonM 20：黄色の地に「CLICK ME」（桃）。札が上から落ちて、下へ行き過ぎて戻る（SHIP IT. f2→4 で +20%・f7 で止まる／98% FASTER f5→8・f12／★ f8→11・f14）。
// f10〜14 で CLICK ME が下へ落ちて消え、f15 で地が桃色に・★が黄色に替わり、緑の CLICK ME が下から f15→18 で上がって止まる。下の黒い帯に SHIP IT ✦ が流れ続ける
// CSS：黒枠 2.5u・影は 4u ずらしたぼかし無しの黒・地は点の網。落ち方は測ったコマごとの値を interpolate
import React, {useMemo} from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export type NeoBrutalismProps = {width?: number; height?: number; colors?: Partial<typeof DEF>; title?: string; stat?: string[]; button?: string; marquee?: string; fontFamily?: string; switchAt?: number};
const DEF = {bgA: '#ffd84a', bgB: '#f590c1', ink: '#0a0a0a', card: '#fdfdfb', cyan: '#5cdee0', starA: '#ff8c42', starB: '#fadd5d', btnA: '#ff5fa2', btnB: '#9cf05a', band: '#0a0a0a', bandText: '#ffe68a', bar: '#bdbdbd'};
const C0 = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const W20_NeoBrutalism: React.FC<NeoBrutalismProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H), u = S / 410;
  const C = {...DEF, ...(p.colors || {})}; const FF = p.fontFamily ?? 'system-ui, -apple-system, "Arial Black", Helvetica, sans-serif';
  const SW = p.switchAt ?? 15, after = f >= SW;
  const bd = 2.6 * u, sh = 4.2 * u;
  const box = (x: number, y: number, w: number, h: number, rot: number, bg: string, children: React.ReactNode, z = 1) => (
    <div style={{position: 'absolute', left: x, top: y, width: w, height: h, background: bg, border: `${bd}px solid ${C.ink}`, boxShadow: `${sh}px ${sh}px 0 ${C.ink}`, transform: `rotate(${rot}deg)`, zIndex: z, fontFamily: FF, color: C.ink, boxSizing: 'border-box'}}>{children}</div>
  );
  // 測った落ち方（コマ → 止まる位置からのずれ・H に対する割合）
  const yShip = interpolate(f, [1, 2, 3, 4, 5, 6, 7, 8, 9], [-0.40, -0.25, 0.07, 0.20, 0.15, 0.05, -0.03, -0.02, 0], C0);
  const rShip = interpolate(f, [2, 4, 6, 9], [-4, -2, 1, -1.2], C0);
  const yStat = interpolate(f, [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], [-0.6, -0.40, -0.01, 0.17, 0.19, 0.10, 0.04, -0.01, -0.03, -0.03, -0.01, 0], C0);
  const rStat = interpolate(f, [5, 6, 8, 12], [-3, -3, 4, 2.5], C0);
  const yStar = interpolate(f, [7, 8, 9, 10, 11, 12, 13, 14, 15], [-0.6, -0.42, -0.06, 0.16, 0.20, 0.14, 0.06, 0.01, 0], C0);
  const rStar = interpolate(f, [8, 9, 12, 15], [6, 6, -4, -3], C0);
  const yBtnA = interpolate(f, [10, 11, 12, 13, 14, 15], [0, 0.23, 0.53, 0.79, 0.92, 1.2], C0);
  const yBtnB = interpolate(f, [SW, SW + 1, SW + 2, SW + 3, SW + 5], [0.30, 0.085, 0.025, 0.01, 0], C0);
  const title = p.title ?? 'SHIP IT.'; const stat = p.stat ?? ['98%', 'FASTER']; const btn = p.button ?? 'CLICK ME';
  const mq = p.marquee ?? 'SHIP IT ✦ ', mqText = mq.repeat(14);
  const unit = useMemo(() => { const g = document.createElement('canvas').getContext('2d')!; g.font = `italic 900 ${0.05 * W}px ${FF}`; return g.measureText(mq).width + mq.length * 0.03 * 0.05 * W; }, [mq, W, FF]);   // 1回ぶんの幅（字間 0.03em 込み）
  const mqX = -((f * 3.1 * u) % unit);   // 1回ぶんの幅で割った余り＝継ぎ目なしで流れる
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: after ? C.bgB : C.bgA}}>
      <div style={{position: 'absolute', inset: 0, backgroundImage: `radial-gradient(${C.ink}22 ${1.1 * u}px, transparent ${1.3 * u}px)`, backgroundSize: `${10 * u}px ${10 * u}px`, backgroundPosition: `${(f * 0.6 * u) % (10 * u)}px ${(f * 0.6 * u) % (10 * u)}px`}} />
      {box(0.07 * W, (0.11 + yShip) * H, 0.86 * W, 0.17 * H, rShip, C.card, <>
        <div style={{position: 'absolute', left: 0.05 * W, top: 0.02 * H, fontWeight: 900, fontSize: 0.085 * W, letterSpacing: '0.01em'}}>{title}</div>
        <div style={{position: 'absolute', left: 0.05 * W, top: 0.095 * H, width: 0.50 * W, height: 0.016 * H, background: C.ink}} />
        <div style={{position: 'absolute', left: 0.05 * W, top: 0.125 * H, width: 0.34 * W, height: 0.013 * H, background: C.bar}} />
      </>, 3)}
      {box(0.07 * W, (0.37 + yStat) * H, 0.50 * W, 0.135 * H, rStat, C.cyan, <div style={{position: 'absolute', left: 0.05 * W, top: 0.022 * H, fontWeight: 900, fontSize: 0.064 * W, lineHeight: 1.05}}>{stat[0]}<br />{stat[1]}</div>, 2)}
      {box(0.64 * W, (0.365 + yStar) * H, 0.27 * W, 0.27 * W, rStar, after ? C.starB : C.starA, <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 0.12 * W, lineHeight: 1}}>★</div>, 2)}
      {!after && box(0.14 * W, (0.045 + yBtnA) * H, 0.46 * W, 0.068 * H, -1 + yBtnA * 8, C.btnA, <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: 0.047 * W, letterSpacing: '0.04em'}}>{btn}</div>, 4)}
      {after && box(0.27 * W, (0.60 + yBtnB) * H, 0.46 * W, 0.068 * H, -1, C.btnB, <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: 0.047 * W, letterSpacing: '0.04em'}}>{btn}</div>, 4)}
      <div style={{position: 'absolute', left: -0.1 * W, top: 0.885 * H, width: 1.2 * W, height: 0.062 * H, background: C.band, transform: 'rotate(-3deg)', overflow: 'hidden', zIndex: 5}}>
        <div style={{position: 'absolute', left: mqX, top: 0, height: '100%', display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', fontFamily: FF, fontWeight: 900, fontStyle: 'italic', fontSize: 0.05 * W, color: C.bandText, letterSpacing: '0.03em'}}>{mqText}</div>
      </div>
    </div>
  );
};
