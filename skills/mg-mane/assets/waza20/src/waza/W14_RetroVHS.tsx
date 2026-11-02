// 14 Retro VHS（80年代のビデオ）— 手本 手本M 14：夕日（上は珊瑚・下半分に黄色の横縞）・紫の山の影・桃色の床に手前へ流れる方眼。
// 画面の字＝PLAY ▶（左上）・● REC（右上・16コマ点いて8コマ消える）・SP 0:04:12（左下・25コマで1秒進む）。f0〜2 は横に裂けるノイズ・下の端にトラッキングの砂嵐・走査線・色ずれ
// SVG で景色＋SVG フィルタ（feTurbulence＋feDisplacementMap で横ずれ／赤だけずらす色ずれ）＋CSS の走査線＋canvas の砂嵐
import React, {useLayoutEffect, useRef} from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export type RetroVHSProps = {width?: number; height?: number; colors?: Partial<typeof DEF>; startSec?: number; label?: string; fontFamily?: string};
const DEF = {sky0: '#1b0a2e', sky1: '#4a1450', sky2: '#c9506e', sunTop: '#ec6476', sunBot: '#f28a4e', stripe: '#f6c443', mount: '#2b0e3c', mountEdge: '#5a1f5e', floor: '#f655ef', grid: '#b01fa8', osd: '#f4f6ff'};

export const W14_RetroVHS: React.FC<RetroVHSProps> = (p) => {
  const vc = useVideoConfig(); const f = useCurrentFrame();
  const W = p.width ?? vc.width, H = p.height ?? vc.height, S = Math.min(W, H), u = S / 410;
  const C = {...DEF, ...(p.colors || {})}; const FF = p.fontFamily ?? 'ui-monospace, Menlo, "SF Mono", monospace';
  const hy = 0.6 * H, sunR = 0.24 * S, sunCy = hy - 0.12 * S;
  const tear = interpolate(f, [0, 1, 2, 3], [70, 48, 22, 0], {extrapolateRight: 'clamp'}) * u / 2.6 + (f >= 18 && f <= 21 ? 6 : 0);
  // 山：正弦の足し算
  let mp = `M0 ${hy}`; for (let i = 0; i <= 80; i++) { const x = (i / 80) * W, t = i / 80; const y = hy - S * (0.10 + 0.07 * Math.sin(t * 9.5 + 0.6) + 0.05 * Math.sin(t * 23 + 1.9) + 0.025 * Math.sin(t * 41)) ; mp += `L${x.toFixed(1)} ${y.toFixed(1)}`; } mp += `L${W} ${hy}Z`;
  // 床の方眼：横線は手前へ（24コマで1升）・縦線は消失点へ
  const lines = [] as React.ReactNode[]; const ph = (f / 12) % 1;
  for (let k = 0; k < 22; k++) { const z = 1 + (k - ph) * 0.9; if (z <= 0.2) continue; const y = hy + (0.95 * H - hy) * (1.3 / (z + 0.3)); if (y > H) continue; lines.push(<line key={'h' + k} x1={0} x2={W} y1={y} y2={y} stroke={C.grid} strokeWidth={Math.max(1.2, 3.4 * u / Math.max(1, z))} opacity={0.75} />); }
  for (let k = -12; k <= 12; k++) { const xb = W / 2 + k * 0.16 * W * 2.2; lines.push(<line key={'v' + k} x1={W / 2 + k * 0.012 * W} y1={hy} x2={xb} y2={H * 1.25} stroke={C.grid} strokeWidth={2.2 * u / 2.6 + 1} opacity={0.7} />); }
  const sec = (p.startSec ?? 252) + Math.floor(f / 25); const tc = `${Math.floor(sec / 3600)}:${String(Math.floor(sec / 60) % 60).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`;
  const rec = f % 24 < 16;
  const noiseRef = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {   // 下の端のトラッキングの砂嵐（コマごとに種を替える）
    const cv = noiseRef.current; if (!cv) return; const g = cv.getContext('2d')!; const w = cv.width, h = cv.height; const im = g.createImageData(w, h); let s = 1234 + f * 7919;
    for (let y = 0; y < h; y++) { s = (s * 1103515245 + 12345) & 0x7fffffff; const row = (s % 100) / 100; for (let x = 0; x < w; x++) { s = (s * 1103515245 + 12345) & 0x7fffffff; const v = (s % 256); const on = v > 150 + row * 80; const o = (y * w + x) * 4; im.data[o] = im.data[o + 1] = im.data[o + 2] = on ? 230 : 20; im.data[o + 3] = on ? 220 : 90; } }
    g.putImageData(im, 0, 0);
  }, [f]);
  const osd: React.CSSProperties = {position: 'absolute', fontFamily: FF, fontWeight: 800, color: C.osd, fontSize: 24 * u, letterSpacing: '0.02em', textShadow: `${-1.2 * u}px 0 rgba(255,40,80,0.75), ${1.2 * u}px 0 rgba(40,220,255,0.75), 0 0 ${3 * u}px rgba(255,255,255,0.5)`, transform: 'scaleX(1.08)', transformOrigin: 'left center'};
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: C.sky0}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <linearGradient id="w14s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={C.sky0} /><stop offset="0.45" stopColor={C.sky1} /><stop offset="1" stopColor={C.sky2} /></linearGradient>
          <linearGradient id="w14u" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={C.sunTop} /><stop offset="1" stopColor={C.sunBot} /></linearGradient>
          <linearGradient id="w14f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ff7af6" /><stop offset="0.35" stopColor={C.floor} /><stop offset="1" stopColor="#e93fe0" /></linearGradient>
          <filter id="w14t" x="-5%" y="0" width="110%" height="100%"><feTurbulence type="fractalNoise" baseFrequency={`0.0001 ${0.035 / u}`} numOctaves={2} seed={Math.floor(f / 2)} result="n" /><feDisplacementMap in="SourceGraphic" in2="n" scale={tear * 2.6} xChannelSelector="R" yChannelSelector="A" /></filter>
          <filter id="w14c" x="0" y="0" width="100%" height="100%"><feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r" /><feOffset in="r" dx={2.2 * u} result="r2" /><feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0" result="gb" /><feBlend in="r2" in2="gb" mode="screen" /></filter>
          <clipPath id="w14k"><circle cx={W / 2} cy={sunCy} r={sunR} /></clipPath>
        </defs>
        <g filter="url(#w14c)">
          <g filter={tear > 0 ? 'url(#w14t)' : undefined}>
            <rect width={W} height={hy} fill="url(#w14s)" />
            <circle cx={W / 2} cy={sunCy} r={sunR} fill="url(#w14u)" />
            <g clipPath="url(#w14k)">{Array.from({length: 6}, (_, i) => <rect key={i} x={W / 2 - sunR} y={sunCy + sunR * (0.06 + i * 0.165)} width={2 * sunR} height={sunR * (0.05 + 0.014 * i)} fill={C.stripe} />)}</g>
            <path d={mp} fill={C.mount} stroke={C.mountEdge} strokeWidth={1.5 * u} />
            <rect y={hy} width={W} height={H - hy} fill="url(#w14f)" />
            {lines}
          </g>
        </g>
      </svg>
      <div style={{position: 'absolute', inset: 0, background: `repeating-linear-gradient(0deg, rgba(0,0,0,0.16) 0px, rgba(0,0,0,0.16) ${1.2 * u / 2.6 + 1}px, rgba(0,0,0,0) ${1.2 * u / 2.6 + 1}px, rgba(0,0,0,0) ${2.6 * u / 2.6 + 2.4}px)`, mixBlendMode: 'multiply'}} />
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.35) 100%)'}} />
      <canvas ref={noiseRef} width={Math.round(W / 3)} height={Math.round(0.018 * H)} style={{position: 'absolute', left: 0, bottom: 0, width: W, height: 0.024 * H, imageRendering: 'pixelated'}} />
      <div style={{...osd, left: 16 * u, top: 12 * u}}>{p.label ?? 'PLAY'} ▶</div>
      {rec && <div style={{...osd, right: 16 * u, top: 12 * u, transformOrigin: 'right center', fontSize: 19 * u}}><span style={{fontSize: 15 * u}}>●</span> REC</div>}
      <div style={{...osd, left: 16 * u, bottom: 0.024 * H + 10 * u}}>SP {tc}</div>
    </div>
  );
};
