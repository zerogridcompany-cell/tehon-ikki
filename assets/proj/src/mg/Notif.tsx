// Notif＝スマホの通知（箱がふわっと出る→題→本文が1語ずつ／1字ずつ打ち出し）。51 の Scenes.tsx Notif の汎用版
// 何をする：f0 から inDur コマで箱が scaleFrom→1・透明→不透明。題は title.f で出る。本文は body.f から語（か字）ごとに下からせり上がって薄い灰→黒
// props：
//   f0, inDur(6), scaleFrom(0.92), curve      箱の出方。51＝75.7秒から 0.2秒・easeOutCubic
//   box [x,y,w,h], radius(64), bg, shadow       箱。51＝[108,366,1704,342]・角 64・rgba(242,242,244,.93)
//   icon {x,y,size,radius,bg,img?,bubble?}      アイコン（img＝public の絵／無ければ bg の色・bubble＝白い吹き出しの形を描く）。51＝212px・角 50・緑のグラデ
//   title {text,f,x,y,fs,font,weight,color}     51＝Lato Bold 74.5px・body より 6コマ前
//   body  {text,f,x,y,fs,font,weight,color,mode,step,rise,riseDur,darkDur,from,lineH}
//          mode 'word'（既定）|'char'・語 i は f+step·i に出る。51＝step 1.5・rise 60・riseDur 4・darkDur 4.2・from 0.15（15%→100% の濃さ）
//   time  {text,right,top,fs,color}             右上の「now」。51＝62px #8a8a8a
// 51 で効いた数字：1字ずつの打ち出しをやめて「1語ずつせり上がって灰→黒」にした＝通知の字の帯 SSIM 0.829→0.878・箱 0.836→0.856
//   書体は字の形で当てた（y の尾・f・B）＝SF でも Inter でもなく Lato。箱のずれ 1px 以内。🔴 通知は全画面のぼかし・色の変換の外（一番上のくっきりした層）に置く
// 測る道具：箱＝mg_measure.py box <手本> f0 f1 --color <箱の色>（箱の半分が出るコマ＝出始め）・題と本文の出るコマ＝mg_measure.py steps --box <字の行の箱>
//   書体＝scripts/tools/txt51/README.md の書体の当て比べ（字の形を候補に重ねる）
import React from 'react';
import {Img, staticFile} from 'remotion';
import {cl, curve} from './common';

type TextDef = {text: string; f: number; x: number; y: number; fs: number; font?: string; weight?: number; color?: string};
type BodyDef = TextDef & {mode?: 'word' | 'char'; step?: number; rise?: number; riseDur?: number; darkDur?: number; from?: number; lineH?: number};
export const Notif: React.FC<{
  f: number; f0: number; inDur?: number; scaleFrom?: number; curve?: string;
  box: [number, number, number, number]; radius?: number; bg?: string; shadow?: string;
  icon?: {x: number; y: number; size: number; radius?: number; bg?: string; img?: string; bubble?: boolean};
  title?: TextDef; body?: BodyDef; time?: {text: string; right: number; top: number; fs: number; color?: string; font?: string};
}> = (P) => {
  const {f} = P;
  const p = curve(P.curve, (f - P.f0) / (P.inDur ?? 6));
  if (f < P.f0 || p <= 0) return null;
  const [bx, by, bw, bh] = P.box;
  const sf = P.scaleFrom ?? 0.92;
  const B = P.body;
  const units = B ? (B.mode === 'char' ? Array.from(B.text) : B.text.split(' ')) : [];
  return (
    <div style={{position: 'absolute', left: bx, top: by, width: bw, height: bh, borderRadius: P.radius ?? 64, background: P.bg ?? 'rgba(242,242,244,0.93)', opacity: p, transform: `scale(${sf + (1 - sf) * p})`, boxShadow: P.shadow ?? '0 10px 40px rgba(0,0,0,0.35)'}}>
      {P.icon && (
        <div style={{position: 'absolute', left: P.icon.x, top: P.icon.y, width: P.icon.size, height: P.icon.size, borderRadius: P.icon.radius ?? P.icon.size * 0.24, background: P.icon.bg ?? 'linear-gradient(#5df774,#27c13f)', overflow: 'hidden'}}>
          {P.icon.img && <Img src={staticFile(P.icon.img)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />}
          {P.icon.bubble && <svg width={P.icon.size} height={P.icon.size} viewBox="0 0 212 212" style={{position: 'absolute', inset: 0}}><ellipse cx={107} cy={98} rx={78} ry={61} fill="#fff" /><path d="M 58 132 Q 52 160 40 172 Q 70 168 88 148 Z" fill="#fff" /></svg>}
        </div>
      )}
      {P.title && f >= P.title.f && <div style={{position: 'absolute', left: P.title.x, top: P.title.y, fontSize: P.title.fs, fontFamily: P.title.font ?? 'sans-serif', fontWeight: P.title.weight ?? 700, color: P.title.color ?? '#1b1b1b', whiteSpace: 'nowrap'}}>{P.title.text}</div>}
      {B && (
        <div style={{position: 'absolute', left: B.x, top: B.y, fontSize: B.fs, fontFamily: B.font ?? 'sans-serif', fontWeight: B.weight ?? 400, color: B.color ?? '#1b1b1b', height: B.lineH ?? B.fs * 1.32, overflow: 'hidden', whiteSpace: 'nowrap'}}>
          {units.map((u, i) => {
            const s0 = B.f + (B.step ?? 1.5) * i;
            const q = cl((f - s0) / (B.riseDur ?? 4)); const e = 1 - (1 - q) * (1 - q); const c = cl((f - s0) / (B.darkDur ?? 4.2));
            const from = B.from ?? 0.15;
            return <span key={i} style={{display: 'inline-block', marginRight: B.mode === 'char' ? 0 : '0.25em', whiteSpace: 'pre', transform: `translateY(${(1 - e) * (B.rise ?? 60)}px)`, opacity: q > 0 ? from + (1 - from) * c : 0}}>{u}</span>;
          })}
        </div>
      )}
      {P.time && <div style={{position: 'absolute', right: P.time.right, top: P.time.top, fontSize: P.time.fs, color: P.time.color ?? '#8a8a8a', fontFamily: P.time.font ?? P.body?.font ?? 'sans-serif'}}>{P.time.text}</div>}
    </div>
  );
};
