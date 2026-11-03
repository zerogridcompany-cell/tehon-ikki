// 絵コンテの下書き板（11/3）＝灰色の箱＋ラベルだけ。色も動きも無し。props＝ekonte.json
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
type Mono={what:string; at:string; size?:string; text?:string};
export type Ku={ku:string; t:[number,number]; kousei?:string; mono:Mono[]; ugoki?:string; waza?:number[]; oto?:string};
const POS:Record<string,[number,number]>={'上左':[0.2,0.2],'上中':[0.5,0.2],'上右':[0.8,0.2],'中左':[0.2,0.5],'中央':[0.5,0.5],'中右':[0.8,0.5],'下左':[0.2,0.8],'下中':[0.5,0.8],'下右':[0.8,0.8]};
const SZ:Record<string,number>={'大':0.4,'中':0.2,'小':0.1};
export const Ekonte:React.FC<{kus:Ku[]; title?:string}>=({kus,title})=>{
  const f=useCurrentFrame(); const {fps,width,height}=useVideoConfig(); const t=f/fps;
  const i=kus.findIndex(k=>t>=k.t[0]&&t<k.t[1]); const k=i>=0?kus[i]:null;
  return <AbsoluteFill style={{background:'#f2f1ee',fontFamily:'Helvetica, Arial, sans-serif'}}>
    <div style={{position:'absolute',left:24,top:16,fontSize:height*0.03,color:'#777'}}>{title??'STORYBOARD'}　{k?`${i+1}/${kus.length}　${k.t[0].toFixed(2)}–${k.t[1].toFixed(2)}s`:''}</div>
    {k&&k.mono.map((m,j)=>{const [px,py]=POS[m.at]??[0.5,0.5]; const h=height*(SZ[m.size??'中']??0.2); const w=Math.min(h*1.6,width*0.86); const lx=Math.min(Math.max(px*width-w/2,width*0.04),width*0.96-w);
      return <div key={j} style={{position:'absolute',left:lx,top:py*height-h/2,width:w,height:h,border:'3px solid #8a8a86',borderRadius:12,background:'#e3e2dd',display:'flex',alignItems:'center',justifyContent:'center',fontSize:Math.min(Math.max(16,h*0.18),width*0.05),color:'#444',textAlign:'center',padding:6,boxSizing:'border-box'}}>{m.text??m.what}</div>;})}
    {k&&<div style={{position:'absolute',left:24,bottom:24,right:24,fontSize:height*0.032,color:'#333',lineHeight:1.4}}>
      <b>「{k.ku}」</b>　{k.kousei??''}<br/><span style={{color:'#666'}}>動き：{k.ugoki??'—'}　技：{(k.waza??[]).join(',')||'—'}　音：{k.oto??'—'}</span></div>}
  </AbsoluteFill>;
};
