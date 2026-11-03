// 絵コンテの下書き板（11/3）＝灰色の箱＋ラベルだけ。色も動きも無し。props＝ekonte.json
// 11/4 追加：句に img（絵の道）があれば「左＝絵・右＝台詞と動きのメモ」の横板（1920x1080 向け）。words（[{text,in,out}]）があれば絵の下に 1 語ずつの字幕
import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
type Mono={what:string; at:string; size?:string; text?:string};
export type Ku={ku:string; t:[number,number]; kousei?:string; mono:Mono[]; ugoki?:string; waza?:(number|string)[]; oto?:string; img?:string; jitsubutsu?:string; gamen?:string};
type Word={text:string; in:number; out:number};
const POS:Record<string,[number,number]>={'上左':[0.2,0.2],'上中':[0.5,0.2],'上右':[0.8,0.2],'中左':[0.2,0.5],'中央':[0.5,0.5],'中右':[0.8,0.5],'下左':[0.2,0.8],'下中':[0.5,0.8],'下右':[0.8,0.8]};
const SZ:Record<string,number>={'大':0.4,'中':0.2,'小':0.1};
const Row:React.FC<{h:string; children:React.ReactNode; s:number}>=({h,children,s})=>(
  <div style={{marginBottom:18*s}}>
    <div style={{fontSize:13*s,letterSpacing:2*s,color:'#9a978f',fontWeight:600,marginBottom:4*s}}>{h}</div>
    <div style={{fontSize:20*s,lineHeight:1.45,color:'#2a2926'}}>{children}</div>
  </div>);
const ImgBoard:React.FC<{kus:Ku[]; title?:string; words?:Word[]; i:number; t:number}>=({kus,title,words,i,t})=>{
  const {width,height}=useVideoConfig(); const s=width/1920; const k=i>=0?kus[i]:null;
  const iw=1240*s, ih=iw*9/16, ix=40*s, iy=84*s;
  const w=(words??[]).find(x=>t>=x.in&&t<x.out);
  return <AbsoluteFill style={{background:'#F4F3F0',fontFamily:'Inter, "Hiragino Sans", Helvetica, Arial, sans-serif'}}>
    <div style={{position:'absolute',left:ix,top:28*s,fontSize:18*s,color:'#8a877f',letterSpacing:1*s}}>{title??'STORYBOARD'}</div>
    <div style={{position:'absolute',right:40*s,top:24*s,fontSize:24*s,color:'#2a2926',fontWeight:700,fontVariantNumeric:'tabular-nums'}}>{k?`${String(i+1).padStart(2,'0')} / ${kus.length}　${k.t[0].toFixed(2)}–${k.t[1].toFixed(2)}s`:''}</div>
    <div style={{position:'absolute',left:ix,top:iy,width:iw,height:ih,borderRadius:10*s,overflow:'hidden',background:'#ddd',boxShadow:`0 ${6*s}px ${24*s}px rgba(0,0,0,.12)`}}>
      {k?.img&&<Img src={staticFile(k.img)} style={{width:'100%',height:'100%',objectFit:'cover'}}/>}
    </div>
    <div style={{position:'absolute',left:ix,top:iy+ih+22*s,width:iw,height:64*s,display:'flex',alignItems:'center',justifyContent:'center'}}>
      {w&&<div style={{background:'#111',color:'#fff',fontSize:34*s,fontWeight:700,padding:`${6*s}px ${22*s}px`,borderRadius:8*s}}>{w.text}</div>}
    </div>
    <div style={{position:'absolute',left:ix,top:iy+ih+96*s,width:iw,fontSize:22*s,color:'#55524b',lineHeight:1.4}}>{k?`「${k.ku}」`:''}</div>
    {k&&<div style={{position:'absolute',left:1320*s,top:iy,width:560*s,bottom:120*s,overflow:'hidden'}}>
      <Row h="画面" s={s}>{k.gamen??k.kousei}</Row>
      <Row h="動き" s={s}>{k.ugoki??'—'}</Row>
      <Row h="技" s={s}>{(k.waza??[]).join('・')||'—'}</Row>
      <Row h="音" s={s}>{k.oto??'—'}</Row>
      {k.jitsubutsu&&<Row h="実物" s={s}>{k.jitsubutsu}</Row>}
    </div>}
    <div style={{position:'absolute',left:ix,right:40*s,bottom:36*s,height:10*s,display:'flex',gap:4*s}}>
      {kus.map((x,j)=><div key={j} style={{flex:x.t[1]-x.t[0],background:j===i?'#EE6433':j<i?'#b9b6ad':'#dcd9d1',borderRadius:3*s}}/>)}
    </div>
  </AbsoluteFill>;
};
export const Ekonte:React.FC<{kus:Ku[]; title?:string; words?:Word[]}>=({kus,title,words})=>{
  const f=useCurrentFrame(); const {fps,width,height}=useVideoConfig(); const t=f/fps;
  const i=kus.findIndex(k=>t>=k.t[0]&&t<k.t[1]); const k=i>=0?kus[i]:null;
  if(kus.some(x=>x.img)) return <ImgBoard kus={kus} title={title} words={words} i={i} t={t}/>;
  return <AbsoluteFill style={{background:'#f2f1ee',fontFamily:'Helvetica, Arial, sans-serif'}}>
    <div style={{position:'absolute',left:24,top:16,fontSize:height*0.03,color:'#777'}}>{title??'STORYBOARD'}　{k?`${i+1}/${kus.length}　${k.t[0].toFixed(2)}–${k.t[1].toFixed(2)}s`:''}</div>
    {k&&k.mono.map((m,j)=>{const [px,py]=POS[m.at]??[0.5,0.5]; const h=height*(SZ[m.size??'中']??0.2); const w=Math.min(h*1.6,width*0.86); const lx=Math.min(Math.max(px*width-w/2,width*0.04),width*0.96-w);
      return <div key={j} style={{position:'absolute',left:lx,top:py*height-h/2,width:w,height:h,border:'3px solid #8a8a86',borderRadius:12,background:'#e3e2dd',display:'flex',alignItems:'center',justifyContent:'center',fontSize:Math.min(Math.max(16,h*0.18),width*0.05),color:'#444',textAlign:'center',padding:6,boxSizing:'border-box'}}>{m.text??m.what}</div>;})}
    {k&&<div style={{position:'absolute',left:24,bottom:24,right:24,fontSize:height*0.032,color:'#333',lineHeight:1.4}}>
      <b>「{k.ku}」</b>　{k.kousei??''}<br/><span style={{color:'#666'}}>動き：{k.ugoki??'—'}　技：{(k.waza??[]).join(',')||'—'}　音：{k.oto??'—'}</span></div>}
  </AbsoluteFill>;
};
