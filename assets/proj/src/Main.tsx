import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame, getInputProps} from 'remotion';
import CAPS from './caps.json';
import LOOK from './look.json';
import {Green} from './Green';
import {Cards} from './Cards';
import {Flash} from './Flash';
import SHOTLOOK from './shot_look.json';
import CUTTUNE from './cuttune.json';
// 動く MG の部品（mg/README.md）＝mg.json に {part, f0, f1, props} を並べると出る。[] なら何も描かん＝今まで通り
import MG from './mg.json';
import {MgLayer, MgItem} from './mg/MgLayer';
const MGI = MG as unknown as MgItem[];

// 場面ごとの見た目（tools/look_shot.py）＝色のゲイン・オフセットとぼかしをそのカットの全部の層に／切り替えの強さ（tools/cut_tune.py）＝その1コマだけ
type Look = {f0: number; f1: number; g?: number[]; o?: number[]; blur?: number};
const LOOKS = Object.values(SHOTLOOK as Record<string, Look>);
const CUTT = CUTTUNE as Record<string, {con?: number | null; bri?: number | null; mix?: number}>;

// 重ねる順（下から）：土台の動画（実写のカット＝assemble.py）→ MG の下の層（紙の地・しわ＝mg.json の layer:'under'）→ 一枚絵（Green＝Codex の描き直し＋green_fit）→ カード（字・光・札）→ MG（mg.json）→ 字幕（caps）
// 字幕＝手本の字の形から逆算した大きさと位置（tools/txt_build.py）。1語ずつ手本の出るコマ〜消えるコマに置く
type Cap = {i: number; w: string; f0: number; f1: number; kind: 'serif' | 'sans' | 'plain'; fs: number; x: number; y: number; c?: string};
const FONT_CSS = `
@font-face{font-family:'CapSerif';src:url('${staticFile('fonts/' + (LOOK as any).serifFile)}');font-weight:100 900;font-style:italic;}
@font-face{font-family:'CapPlain';src:url('${staticFile('fonts/TNR-Regular.ttf')}');}
@font-face{font-family:'CapSans';src:url('${staticFile('fonts/' + (LOOK as any).sansFile)}');font-weight:100 900;}
`;

export const Main: React.FC = () => {
  const f = useCurrentFrame();
  const L = LOOK as any;
  // --props '{"off":["caps"]}' で字幕を外して書き出せる（flash_auto.py が反転の元を作る時）
  const OFF = ((getInputProps() as any).off || []) as string[];
  const on = OFF.includes('caps') ? [] : (CAPS as Cap[]).filter((c) => f >= c.f0 && f <= c.f1);
  const lk = LOOKS.find((l) => f >= l.f0 && f <= l.f1);
  const ct = CUTT[String(f)];
  const flt = [lk?.g ? 'url(#shotlook)' : '', lk?.blur ? `blur(${lk.blur}px)` : '',
    ct?.con ? `contrast(${ct.con})` : '', ct?.bri ? `brightness(${ct.bri})` : ''].join(' ').trim();
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {lk?.g && (
        <svg width={0} height={0} style={{position: 'absolute'}}>
          {/* 🔴 sRGB 指定が要る（無いと linearRGB で計算されて色がずれる） */}
          <filter id="shotlook" colorInterpolationFilters="sRGB">
            <feColorMatrix type="matrix" values={`${lk.g[0]} 0 0 0 ${lk.o![0]} 0 ${lk.g[1]} 0 0 ${lk.o![1]} 0 0 ${lk.g[2]} 0 ${lk.o![2]} 0 0 0 1 0`} />
          </filter>
        </svg>
      )}
      <AbsoluteFill style={{filter: flt || undefined}}>
      <style>{FONT_CSS}</style>
      <OffthreadVideo src={staticFile('base.mp4')} muted />
      {/* 余計な切り替えを線の下へ＝前のコマを薄く重ねる（cuttune.json の mix・r2 10/27） */}
      {ct?.mix ? (
        <AbsoluteFill style={{opacity: ct.mix}}>
          <Sequence from={1} layout="none"><OffthreadVideo src={staticFile('base.mp4')} muted /></Sequence>
        </AbsoluteFill>
      ) : null}
      <MgLayer items={MGI} layer="under" />
      <Green />
      <Cards />
      <MgLayer items={MGI} layer="over" />
      </AbsoluteFill>
      {/* 🔴 字幕は場面の色・ぼかし（shot_look）の外＝手本の字はどのカットでもくっきり（r2 10/27） */}
      <svg width={(L.width ?? 1280)} height={(L.height ?? 720)} style={{position: 'absolute', inset: 0, overflow: 'visible',
        filter: `blur(${L.blur}px) drop-shadow(0 0 ${L.glow1}px rgba(255,255,255,${L.glowA1})) drop-shadow(0 0 ${L.glow2}px rgba(255,255,255,${L.glowA2}))`}}>
        {on.filter((c) => !c.c).map((c) => {
          const serif = c.kind === 'serif';
          return (
            <text key={c.i} x={0} y={0} fill="#fff" transform={`translate(${c.x} ${c.y}) scale(${serif ? L.serifSx : L.sansSx} 1)`}
              style={{fontFamily: c.kind === 'plain' ? 'CapPlain' : serif ? 'CapSerif' : 'CapSans', fontStyle: serif ? 'italic' : 'normal', fontWeight: c.kind === 'plain' ? 400 : serif ? L.serifW : L.sansW, fontSize: c.fs}}>
              {c.w}
            </text>
          );
        })}
      </svg>
      {/* 白い地の上の黒い字（caps の c に色）＝光を付けん（r2 121・2128） */}
      <svg width={(L.width ?? 1280)} height={(L.height ?? 720)} style={{position: 'absolute', inset: 0, overflow: 'visible', filter: `blur(${L.blur}px)`}}>
        {on.filter((c) => c.c).map((c) => {
          const serif = c.kind === 'serif';
          return (
            <text key={c.i} x={0} y={0} fill={c.c} transform={`translate(${c.x} ${c.y}) scale(${serif ? L.serifSx : L.sansSx} 1)`}
              style={{fontFamily: c.kind === 'plain' ? 'CapPlain' : serif ? 'CapSerif' : 'CapSans', fontStyle: serif ? 'italic' : 'normal', fontWeight: c.kind === 'plain' ? 400 : serif ? L.serifW : L.sansW, fontSize: c.fs}}>
              {c.w}
            </text>
          );
        })}
      </svg>
      {/* 白く光る1コマ・光の差し込み・大きい字（flash.json＝tools/flash_auto.py）。全部の層の上 */}
      <Flash />
      {/* 一番上のくっきりした層（場面の色・ぼかしの外）＝通知など（51：通知はぼかしの外で字の一番暗い所 35→0） */}
      <MgLayer items={MGI} layer="top" />
    </AbsoluteFill>
  );
};
