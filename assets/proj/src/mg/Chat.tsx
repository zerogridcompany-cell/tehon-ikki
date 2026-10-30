// Chat・Bub・Words・RiseWords＝メッセージの吹き出し（iMessage 風）。51 の Scenes.tsx Chat の汎用版（中身の字・位置・コマは全部 props）
// 何をする：1つの吹き出しが ①点々（ぽんと出る＝大きさの段）②横に伸びる ③字が1語ずつ下からせり上がる、の3段で出る
// props（Chat）：bubbles＝BubbleEv の並び（下の型）。1つの吹き出し＝1行
//   x,y,w,h      点々の時の箱（左上・幅・高さ・画面の px）
//   anchor       伸びる時に止める端（'left'＝灰色の受け・'right'＝青の送り。51 の青は右端 1622 で止めて左へ伸びた）
//   pop          [[コマ, 倍率]…]＝点々がぽんと出る段（箱の真ん中を中心に）。51 灰1＝[[1696,.585],[1699,1.02],[1702,1.078],[1705,1]]
//   grow         {f, dur, w, h, curve}＝f から dur コマで w×h へ伸びる。51＝6コマ（0.2秒）easeOutCubic
//   text         {f, lines, step, dur, rise, curve}＝lines＝[[語…]…]・語 i は f+step·i に出て dur コマでせり上がる（rise px 下から）
//                51＝step 3（0.1秒）・dur 3.6（0.12秒）・rise 40・easeOutQuad・行の高さで overflow を切る
//   look         'blue'|'gray'|BubLook。灰色は mixBlendMode multiply（紙の上で紙の 0.69 倍に見える）
// 51 で効いた数字：吹き出しの区間 SSIM 0.794→0.806・字の箱のずれ 12〜19px→0〜6px。字＝Inter の本文用 opsz 14（iMessage の字と幅が 1〜2% で合う・opsz 32 は 10% 細い）
//   青 38px wght500 行 49px・灰 37px wght450 行 46px・角丸＝h/2.2
// 測る道具：
//   箱と色＝mg_measure.py box <手本> f0 f1 --color 47,125,225（青）/ 180,178,176（灰）＝色の塊の外枠を毎コマ（select n で読む）
//   ぽんの段＝その箱の幅÷止まった時の幅を毎コマ→同じ値が続く所を段に（3コマずつ・行き過ぎて戻る）
//   語の出るコマ＝字の行の帯の中の「字の色の画素の右端」が跳ぶコマ（mg_measure.py steps --box …）
import React from 'react';
import {curve, cl, stepAt} from './common';

export type BubLook = {bg: string; color: string; blend?: string; fs: number; weight: number; opsz?: number; lineH: number; pad: string; radiusK?: number; dot: string; dotSize?: number; font?: string};
export const BUB_LOOKS: Record<string, BubLook> = {
  blue: {bg: '#2f7de1', color: '#fff', fs: 38, weight: 500, opsz: 14, lineH: 49, pad: '30px 30px 18px 49px', dot: '#cfe2ff'},
  gray: {bg: '#b4b2b0', color: '#222', blend: 'multiply', fs: 37, weight: 450, opsz: 14, lineH: 46, pad: '22px 30px 18px 32px', dot: '#8d8d90'},
};
const lookOf = (l?: string | BubLook): BubLook => (typeof l === 'object' ? l : BUB_LOOKS[l ?? 'gray'] ?? BUB_LOOKS.gray);

export const Bub: React.FC<{x: number; y: number; w: number; h: number; look?: string | BubLook; dots?: boolean; op?: number; font?: string; children?: React.ReactNode}> = ({x, y, w, h, look, dots, op = 1, font, children}) => {
  const L = lookOf(look);
  const ds = L.dotSize ?? 12;
  return (
    <div style={{position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: h / (L.radiusK ?? 2.2), background: L.bg, mixBlendMode: (L.blend as any) ?? undefined, opacity: op,
      color: L.color, fontFamily: font ?? L.font ?? 'Inter, sans-serif', fontSize: L.fs, fontWeight: L.weight, fontVariationSettings: L.opsz ? `'opsz' ${L.opsz}, 'wght' ${L.weight}` : undefined,
      lineHeight: `${L.lineH}px`, padding: L.pad, whiteSpace: 'pre-line', boxSizing: 'border-box', overflow: 'hidden'}}>
      {dots ? <div style={{display: 'flex', gap: ds * 0.83, justifyContent: 'center', marginTop: (h - 40) / 2}}>{[0, 1, 2].map((i) => <div key={i} style={{width: ds, height: ds, borderRadius: ds / 2, background: L.dot}} />)}</div> : children}
    </div>
  );
};

export type RiseOpt = {f: number; step?: number; dur?: number; rise?: number; curve?: string; gap?: number; lineH?: number};
/** 1行の語を1語ずつ下からせり上げる。k0＝この行の最初の語の通し番号（行をまたいで語の時刻を続ける） */
export const RiseWords: React.FC<{f: number; words: string[]; o: RiseOpt; k0?: number}> = ({f, words, o, k0 = 0}) => (
  <div style={{height: o.lineH ?? 46, overflow: 'hidden', whiteSpace: 'nowrap'}}>
    {words.map((w, i) => {
      const p = cl((f - (o.f + (o.step ?? 3) * (k0 + i))) / (o.dur ?? 3.6));
      const e = curve(o.curve ?? 'easeOutQuad', p);
      return <span key={i} style={{display: 'inline-block', marginRight: o.gap ?? 12, transform: `translateY(${(1 - e) * (o.rise ?? 40)}px)`, opacity: p > 0 ? 1 : 0}}>{w}</span>;
    })}
  </div>
);
/** 何行もの語（行をまたいで語の時刻が続く） */
export const Words: React.FC<{f: number; lines: string[][]; o: RiseOpt}> = ({f, lines, o}) => {
  let k = 0;
  return <>{lines.map((ln, li) => { const k0 = k; k += ln.length; return <RiseWords key={li} f={f} words={ln} o={o} k0={k0} />; })}</>;
};

export type BubbleEv = {
  f0: number; f1?: number; x: number; y: number; w: number; h: number; anchor?: 'left' | 'right'; look?: string | BubLook; font?: string;
  pop?: [number, number][]; grow?: {f: number; dur?: number; w: number; h?: number; curve?: string}; text?: RiseOpt & {lines: string[][]};
};
export const Chat: React.FC<{f: number; bubbles: BubbleEv[]; font?: string}> = ({f, bubbles, font}) => (
  <>
    {bubbles.map((b, i) => {
      if (f < b.f0 || (b.f1 != null && f > b.f1)) return null;
      const L = lookOf(b.look);
      const growing = b.grow && f >= b.grow.f;
      if (!growing) {
        const sc = b.pop ? stepAt(b.pop, f) ?? 0 : 1;
        if (sc <= 0) return null;
        const cx = b.x + b.w / 2, cy = b.y + b.h / 2;
        return <Bub key={i} x={cx - (b.w * sc) / 2} y={cy - (b.h * sc) / 2} w={b.w * sc} h={b.h * sc} look={b.look} font={font ?? b.font} dots />;
      }
      const g = b.grow!;
      const p = curve(g.curve, (f - g.f) / (g.dur ?? 6));
      const w = b.w + (g.w - b.w) * p, h = b.h + ((g.h ?? b.h) - b.h) * p;
      const x = b.anchor === 'right' ? b.x + b.w - w : b.x;
      const showText = b.text && f >= b.text.f;
      return (
        <Bub key={i} x={x} y={b.y} w={w} h={h} look={b.look} font={font ?? b.font}>
          {showText ? <Words f={f} lines={b.text!.lines} o={{lineH: L.lineH, ...b.text!}} /> : null}
        </Bub>
      );
    })}
  </>
);
