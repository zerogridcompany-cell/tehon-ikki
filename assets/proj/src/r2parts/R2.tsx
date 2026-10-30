import React from 'react';
import {AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame, getInputProps} from 'remotion';
import LAYEROFF from './layer_off.json';
import CAPS from './caps.json';
import LOOK from './look.json';
import {Logo, LOGO_F0} from './Logo';
import {Slabs, SLAB_F0} from './Slabs';
import SLABCFG from './slabs.json';
import {Sequence} from 'remotion';
import {Green} from './Green';
import {Flash} from './Flash';
import {Cards} from './Cards';
import {Hud} from './Hud';
import {GrainAll} from './GrainAll';
import SHOTLOOK from './shot_look.json';
import CUTTUNE from './cuttune.json';
import HT from './ht.json';  // 網点（72・46 と同じ 2.67px の型）を層ごとかけるコマ（44・47）
// 切り替えの強さ（tools/cut_tune.py）：手本で切り替わるのにうちが弱いコマだけ、その1コマのコントラストか明るさを上げる
// 余計な切り替え（手本はゆっくり替わる所）は、前のコマを mix だけ重ねて弱める
const CUTT = CUTTUNE as Record<string, {con?: number | null; bri?: number | null; mix?: number | null}>;

// 場面ごとの見た目（tools/look_shot.py）：色のゲイン・オフセットとぼかしを、そのカットの全部の層にかける
type Look = {f0: number; f1: number; g?: number[]; o?: number[]; blur?: number};
const LOOKS = Object.values(SHOTLOOK as Record<string, Look>);

// 字幕＝手本の字の形から逆算した大きさと位置（tools/txt_build.py）。1語ずつ手本の出るコマ〜消えるコマに置く。
type Cap = {i: number; w: string; f0: number; f1: number; kind: 'serif' | 'sans' | 'plain'; fs: number; x: number; y: number; c?: string};
const FONT_CSS = `
@font-face{font-family:'R2Serif';src:url('${staticFile('fonts/LibreBaskerville-Italic[wght].ttf')}');font-weight:100 900;font-style:italic;}
@font-face{font-family:'R2Plain';src:url('${staticFile('fonts/TNR-Regular.ttf')}');}
@font-face{font-family:'R2Sans';src:url('${staticFile('fonts/Inter[opsz,wght].ttf')}');font-weight:100 900;}
`;

// 層の出し入れ（tools/layer_pick.py）：カットごとに手元で採点して、下げる層（look＝色・ぼかし／cut＝切り替え／caps＝字幕）だけ外す。
// --props '{"off":["look"]}' で全部のコマから外した試しの書き出しもできる
type Off = {f0: number; f1: number; off: string[]};
const IP = getInputProps() as {off?: string[]};
const offAt = (f: number, k: string) => (IP.off || []).includes(k) || (LAYEROFF as Off[]).some((o) => f >= o.f0 && f < o.f1 && o.off.includes(k));

export const R2: React.FC = () => {
  const f = useCurrentFrame();
  const on = offAt(f, 'caps') ? [] : (CAPS as Cap[]).filter((c) => f >= c.f0 && f <= c.f1);
  const lk = offAt(f, 'look') ? undefined : LOOKS.find((l) => f >= l.f0 && f <= l.f1);
  const ct = offAt(f, 'cut') ? undefined : CUTT[String(f)];
  const flt = [lk?.g ? 'url(#shotlook)' : '', lk?.blur ? `blur(${lk.blur}px)` : '',
    ct?.con ? `contrast(${ct.con})` : '', ct?.bri ? `brightness(${ct.bri})` : ''].join(' ').trim();
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {lk?.g && (
        <svg width={0} height={0} style={{position: 'absolute'}}>
          <filter id="shotlook" colorInterpolationFilters="sRGB">
            <feColorMatrix type="matrix" values={`${lk.g[0]} 0 0 0 ${lk.o![0]} 0 ${lk.g[1]} 0 0 ${lk.o![1]} 0 0 ${lk.g[2]} 0 ${lk.o![2]} 0 0 0 1 0`} />
          </filter>
        </svg>
      )}
      <svg width={0} height={0} style={{position: 'absolute'}}>
        <filter id="ht" x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
          <feGaussianBlur in="SourceGraphic" stdDeviation={1.5} result="b" />
          <feImage href={staticFile('halftone.png')} x={0} y={0} width={1280} height={720} preserveAspectRatio="none" result="p" />
          <feComposite in="b" in2="p" operator="arithmetic" k1={3} k2={0} k3={0} k4={0} />
        </filter>
      </svg>
      <AbsoluteFill style={{filter: (HT as number[][]).some(([a, b]) => f >= a && f <= b) ? 'url(#ht)' : undefined}}>
      {/* tf＝カットごとの最後の拡大・移動（tools/final_fit.py が書き出しどうしの ECC で測る・10/27 写真の大きさ） */}
      <AbsoluteFill style={{filter: flt || undefined, transformOrigin: '0 0', transform: (lk as any)?.tf ? `matrix(${(lk as any).tf.join(',')})` : undefined}}>
      <style>{FONT_CSS}</style>
      <OffthreadVideo src={staticFile('base.mp4')} muted />
      {ct?.mix ? (
        <AbsoluteFill style={{opacity: ct.mix}}>
          <Sequence from={1} layout="none"><OffthreadVideo src={staticFile('base.mp4')} muted /></Sequence>
        </AbsoluteFill>
      ) : null}
      {!offAt(f, 'green') && <Green />}
      <Sequence from={LOGO_F0}><Logo /></Sequence>
      <Sequence from={SLAB_F0} durationInFrames={(SLABCFG as any).f1 - SLAB_F0}><Slabs /></Sequence>
      {!offAt(f, 'cards') && <Cards />}
      {!offAt(f, 'grainall') && <GrainAll />}
      </AbsoluteFill>
      </AbsoluteFill>
      {!offAt(f, 'hud') && <Hud />}
      {/* 字幕はカットごとの色・ぼかし（shot_look）の外＝手本の字はどのカットでもくっきり白い（10/27 夜） */}
      <svg width={1280} height={720} style={{position: 'absolute', inset: 0, overflow: 'visible',
        filter: `blur(${LOOK.blur}px) drop-shadow(0 0 ${LOOK.glow1}px rgba(255,255,255,${LOOK.glowA1})) drop-shadow(0 0 ${LOOK.glow2}px rgba(255,255,255,${LOOK.glowA2}))${(LOOK as any).glow3 ? ` drop-shadow(0 0 ${(LOOK as any).glow3}px rgba(255,255,255,${(LOOK as any).glowA3}))` : ''}`}}>
        {on.filter((c) => !c.c).map((c) => {
          const serif = c.kind === 'serif';
          const sx = serif ? LOOK.serifSx : LOOK.sansSx;
          return (
            <text key={c.i} x={0} y={0} fill="#fff"
              transform={`translate(${c.x} ${c.y}) scale(${sx} 1)`}
              style={{fontFamily: c.kind === 'plain' ? 'R2Plain' : serif ? 'R2Serif' : 'R2Sans', fontStyle: serif ? 'italic' : 'normal',
                fontWeight: c.kind === 'plain' ? 400 : serif ? LOOK.serifW : LOOK.sansW, fontSize: c.fs,
                fontVariationSettings: serif ? `'wght' ${LOOK.serifW}` : `'wght' ${LOOK.sansW}, 'opsz' 32`}}>
              {c.w}
            </text>
          );
        })}
      </svg>
      {/* 白い地の上の黒い字（121 の it's not just など）＝光を付けん */}
      <svg width={1280} height={720} style={{position: 'absolute', inset: 0, overflow: 'visible', filter: `blur(${LOOK.blur}px)`}}>
        {on.filter((c) => c.c).map((c) => {
          const serif = c.kind === 'serif';
          return (
            <text key={c.i} x={0} y={0} fill={c.c}
              transform={`translate(${c.x} ${c.y}) scale(${serif ? LOOK.serifSx : LOOK.sansSx} 1)`}
              style={{fontFamily: c.kind === 'plain' ? 'R2Plain' : serif ? 'R2Serif' : 'R2Sans', fontStyle: serif ? 'italic' : 'normal',
                fontWeight: c.kind === 'plain' ? 400 : serif ? LOOK.serifW : LOOK.sansW, fontSize: c.fs,
                fontVariationSettings: serif ? `'wght' ${LOOK.serifW}` : `'wght' ${LOOK.sansW}, 'opsz' 32`}}>
              {c.w}
            </text>
          );
        })}
      </svg>
      <Flash />
    </AbsoluteFill>
  );
};
