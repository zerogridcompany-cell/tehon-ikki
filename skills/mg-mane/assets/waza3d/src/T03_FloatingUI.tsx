// T03 FloatingUI（手札 R2_05・道 A＝CSS 3D）
// 宙に浮く広告の札 6 枚を弧に並べる。札は下から ease out で浮かび上がり、弧ごとゆっくり回る（カメラ 1 軸＝回り込み）。
// 足元の光源・床の映り込み・縁の光 1 本・柔らかい落ち影。札の中身は白い Mercury 型（日本の広告＝読めない広告の場面）。
import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {E, FONT_JP, GRAIN, lerp, tw, breathe} from './lib';

export type T03Card = {brand: string; caption: string; image: string; tint: string; cta: string};
export type T03Props = {accent: string; cards: T03Card[]; orbitFrom: number; orbitTo: number; radius: number};
const D = (c: string) => `zg/daruma_${c}.png`;
export const t03Defaults: T03Props = {
  accent: '#f06433',
  cards: [
    {brand: 'だるま本舗', caption: '願いが叶う、赤いだるま。', image: D('red'), tint: '#fdece8', cta: '購入する'},
    {brand: '開運ショップ', caption: '本日限り 送料無料', image: D('yellow'), tint: '#fdf5dd', cta: '詳しくはこちら'},
    {brand: '高崎だるま', caption: '職人の手描き 一点物', image: D('blue'), tint: '#e8eefc', cta: '購入する'},
    {brand: '福だるま堂', caption: '受験・商売繁盛に', image: D('brown'), tint: '#f3ece6', cta: '今すぐ見る'},
    {brand: 'だるま本舗', caption: 'レビュー 4.9 ★ 1,200件', image: D('red'), tint: '#fdece8', cta: '購入する'},
    {brand: '開運ショップ', caption: '新色 入荷しました', image: D('yellow'), tint: '#fdf5dd', cta: '詳しくはこちら'},
  ],
  orbitFrom: -13,
  orbitTo: 9,
  radius: 1150,
};
const src = (s: string) => (s.startsWith('http') ? s : staticFile(s));
const CW = 300, CH = 452;

const AdCard: React.FC<{c: T03Card; accent: string}> = ({c, accent}) => (
  <div style={{position: 'absolute', inset: 0, borderRadius: 22, background: '#fbfcfd', overflow: 'hidden', fontFamily: FONT_JP,
    boxShadow: `inset 0 1px 0 rgba(255,255,255,1), 0 0 0 1px rgba(255,255,255,.65), 0 0 0 2px ${accent}55, 0 0 26px ${accent}44`}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 9, padding: '14px 14px 10px'}}>
      <div style={{width: 30, height: 30, borderRadius: 15, background: c.tint, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 0 1px #e8e7ed'}}>
        <Img src={src(c.image)} style={{height: 22}} />
      </div>
      <div style={{lineHeight: 1.15}}>
        <div style={{fontSize: 13, fontWeight: 700, color: '#040506'}}>{c.brand}</div>
        <div style={{fontSize: 10.5, color: '#8b93a1'}}>広告</div>
      </div>
      <div style={{marginLeft: 'auto', color: '#8b93a1', fontSize: 16, letterSpacing: 1}}>···</div>
    </div>
    <div style={{margin: '0 10px', height: 268, borderRadius: 14, background: `radial-gradient(circle at 50% 42%, #ffffff 0, ${c.tint} 70%)`, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative'}}>
      <div style={{position: 'absolute', bottom: 34, width: 150, height: 18, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(60,40,40,.28) 0, rgba(60,40,40,0) 70%)'}} />
      <Img src={src(c.image)} style={{height: 200, position: 'relative', filter: 'drop-shadow(0 10px 12px rgba(60,30,30,.18))'}} />
    </div>
    <div style={{padding: '12px 14px 0', fontSize: 15, fontWeight: 700, color: '#040506'}}>{c.caption}</div>
    <div style={{position: 'absolute', left: 10, right: 10, bottom: 10, height: 38, borderRadius: 10, background: '#f1f3f6', display: 'flex', alignItems: 'center', padding: '0 12px', fontSize: 13, fontWeight: 700, color: '#3a3f4b'}}>
      {c.cta}<span style={{marginLeft: 'auto', color: '#8b93a1'}}>›</span>
    </div>
  </div>
);

export const T03_FloatingUI: React.FC<Partial<T03Props>> = (props) => {
  const p = {...t03Defaults, ...props};
  const f = useCurrentFrame();
  const orbit = lerp(p.orbitFrom, p.orbitTo, tw(f, -20, 110, E.inout));
  const n = p.cards.length;
  const step = 17.5;
  const R = p.radius;
  const base = tw(f, -8, 30, E.out);
  return (
    <AbsoluteFill style={{background: '#07070a', overflow: 'hidden'}}>
      {/* 舞台：上は暗く・足元の光源から商品色の 2 段の光 */}
      <AbsoluteFill style={{background: `radial-gradient(circle 300px at 50% 86%, ${p.accent}66 0, ${p.accent}22 45%, transparent 100%), radial-gradient(circle 1100px at 50% 90%, ${p.accent}2a 0, ${p.accent}0c 45%, transparent 100%), linear-gradient(180deg,#0b0b10 0%,#07070a 100%)`, opacity: lerp(0.4, 1, base)}} />
      {/* 光の束（足元から上へ・とても薄い） */}
      <div style={{position: 'absolute', left: 960 - 700, top: 120, width: 1400, height: 840, clipPath: 'polygon(46% 100%, 54% 100%, 100% 0, 0 0)',
        background: `linear-gradient(0deg, ${p.accent}30 0%, ${p.accent}0a 55%, transparent 100%)`, filter: 'blur(26px)', opacity: base * 0.9}} />
      <AbsoluteFill style={{perspective: 1700, perspectiveOrigin: '50% 46%'}}>
        <div style={{position: 'absolute', left: 960, top: 500, transformStyle: 'preserve-3d', transform: `translateZ(${-R + 520}px) rotateX(-5deg) rotateY(${orbit}deg)`}}>
          {/* 床（反射する暗い面・接地の光の楕円） */}
          <div style={{position: 'absolute', left: -1400, top: 330, width: 2800, height: 2800, transformOrigin: '50% 0', transform: `translateZ(${R}px) rotateX(90deg) translateY(-1400px)`,
            background: `radial-gradient(circle 520px at 50% 50%, ${p.accent}2e 0, ${p.accent}0a 50%, transparent 100%)`}} />
          {p.cards.map((c, i) => {
            const a = (i - (n - 1) / 2) * step;
            const order = Math.abs(i - (n - 1) / 2);
            const k = tw(f, -10 + order * 4, 18 + order * 4, E.out);
            const bob = breathe(f, 7, 84, i * 1.3);
            const y = lerp(150, 0, k) + bob;
            return (
              <div key={i} style={{position: 'absolute', left: -CW / 2, top: -CH / 2, width: CW, height: CH, transformStyle: 'preserve-3d',
                transform: `rotateY(${a}deg) translateZ(${R}px) translateY(${y}px) rotateX(${lerp(14, 0, k)}deg) scale(${lerp(0.9, 1, k)})`, opacity: k}}>
                {/* 映り込み（床に逆さ・下へ消える） */}
                <div style={{position: 'absolute', left: 0, top: CH + 14, width: CW, height: CH, transform: 'scaleY(-1)', opacity: 0.16,
                  WebkitMaskImage: 'linear-gradient(0deg, transparent 55%, #000 100%)', filter: 'blur(2px)'}}><AdCard c={c} accent={p.accent} /></div>
                {/* 落ち影（下に偏る・柔らかい） */}
                <div style={{position: 'absolute', left: 20, top: 40, width: CW - 40, height: CH - 20, borderRadius: 30, background: 'rgba(0,0,0,.55)', filter: 'blur(30px)', transform: 'translateZ(-40px) translateY(40px)'}} />
                <AdCard c={c} accent={p.accent} />
                {/* 縁の光 1 本（上の縁を斜めに撫でる） */}
                <div style={{position: 'absolute', inset: 0, borderRadius: 22, pointerEvents: 'none', mixBlendMode: 'screen',
                  background: `linear-gradient(${105 + orbit * 1.5 + a * 0.6}deg, rgba(255,255,255,0) 38%, rgba(255,255,255,.22) 48%, rgba(255,255,255,0) 58%)`}} />
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse 80% 75% at 50% 50%, transparent 55%, rgba(0,0,0,.55) 100%)'}} />
      <AbsoluteFill style={{backgroundImage: GRAIN, opacity: 0.045, mixBlendMode: 'overlay'}} />
    </AbsoluteFill>
  );
};
