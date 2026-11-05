// T01 ZoomThroughScreen（手札 R2_07・道 A＝CSS 3D）
// 宙の iPhone → 画面に寄り続けて、そのまま画面の中の世界（Discord の招待）へ入る。
// カメラは 1 軸（寄りだけ）。寄りは対数空間＋Apple の曲線（加速短く・減速長く）。傾きは同じ進みでほどける。
import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {CameraMotionBlur} from '@remotion/motion-blur';
import {E, FONT, GRAIN, clamp01, lerp, logLerp, tw, breathe} from './lib';

export type T01Props = {
  accent: string; // 舞台の光の色（商品色 1 色）
  serverName: string;
  serverIcon: string; // staticFile の名前 or URL
  inviteLine: string;
  notifTitle: string;
  notifBody: string;
  time: string;
  zoomFrom: number; // 寄りの始まり（コマ）
  zoomTo: number; // 寄りの終わり（コマ）
  blur: boolean;
};
export const t01Defaults: T01Props = {
  accent: '#f06433',
  serverName: 'ZeroGrid',
  serverIcon: 'zg/zg_mark.svg',
  inviteLine: "YOU'VE BEEN INVITED TO JOIN",
  notifTitle: 'Discord',
  notifBody: 'ZeroGrid invited you to join the server.',
  time: '9:41',
  zoomFrom: 22,
  zoomTo: 88,
  blur: true,
};
const src = (s: string) => (s.startsWith('http') ? s : staticFile(s));

const PW = 430, PH = 884, BEZ = 13, SW = PW - BEZ * 2, SH = PH - BEZ * 2;
const S_END = 5.7; // 画面が 1920 を覆う倍率（縁が外へ出切る）

// 世界（1920x1080 の座標で描く・中では 1/S_END に縮めて画面の真ん中に置く）
const World: React.FC<{p: T01Props; f: number}> = ({p, f}) => {
  const pulse = Math.max(0, Math.sin(((f - 62) / 18) * Math.PI)) * (f > 62 ? 1 : 0);
  return (
    <div style={{position: 'absolute', width: 1920, height: 1080, background: '#1e1f22', fontFamily: FONT, overflow: 'hidden'}}>
      {/* 招待ページの地＝Discord の暗い地に Blurple の 2 段の光 */}
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(circle 420px at 50% 46%, rgba(88,101,242,.42) 0, rgba(88,101,242,.16) 45%, rgba(88,101,242,0) 100%), radial-gradient(circle 1100px at 50% 50%, rgba(88,101,242,.20) 0, rgba(88,101,242,.06) 50%, rgba(88,101,242,0) 100%)'}} />
      <div style={{position: 'absolute', inset: 0, backgroundImage: GRAIN, opacity: 0.05, mixBlendMode: 'overlay'}} />
      {/* 招待カード（白モード・公式の数字） */}
      <div style={{position: 'absolute', left: 960 - 240, top: 540 - 196, width: 480, height: 392, borderRadius: 8, background: '#ffffff', transform: `translateY(${lerp(14, 0, tw(f, 50, 96, E.out))}px)`,
        boxShadow: '0 30px 80px rgba(0,0,0,.45), 0 6px 18px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.9)', textAlign: 'center'}}>
        <div style={{marginTop: 34, fontSize: 12, letterSpacing: '0.06em', fontWeight: 600, color: '#5c5e66'}}>{p.inviteLine}</div>
        <div style={{margin: '20px auto 0', width: 76, height: 76, borderRadius: 22, background: '#fff', boxShadow: '0 0 0 1px #e3e5e8, 0 6px 14px rgba(0,0,0,.08)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <Img src={src(p.serverIcon)} style={{width: 54}} />
        </div>
        <div style={{marginTop: 18, fontSize: 26, fontWeight: 700, color: '#060607', letterSpacing: '-0.01em'}}>{p.serverName}</div>
        <div style={{marginTop: 10, fontSize: 14, color: '#5c5e66', display: 'flex', justifyContent: 'center', gap: 18}}>
          <span><span style={{display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: '#23a55a', marginRight: 6}} />1,280 Online</span>
          <span><span style={{display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: '#80848e', marginRight: 6}} />5,400 Members</span>
        </div>
        <div style={{position: 'absolute', left: 32, right: 32, bottom: 34, height: 44, borderRadius: 4, background: '#5865f2', color: '#fff', fontSize: 16, fontWeight: 600,
          display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 0 ${4 * pulse}px rgba(88,101,242,${0.35 * pulse}), 0 6px 16px rgba(88,101,242,.35)`}}>Join Server</div>
      </div>
    </div>
  );
};

// 鍵の画面（壁紙＋時刻＋通知）
const Lock: React.FC<{p: T01Props; f: number}> = ({p, f}) => {
  const n = tw(f, 4, 22, E.out);
  return (
    <div style={{position: 'absolute', inset: 0, fontFamily: FONT, color: '#fff'}}>
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(ellipse 120% 70% at 50% 108%, ${p.accent} 0%, rgba(120,40,20,.55) 38%, rgba(16,14,20,0) 70%), linear-gradient(180deg,#121118 0%,#1a1520 60%,#2a1712 100%)`}} />
      <div style={{position: 'absolute', top: 104, width: '100%', textAlign: 'center', fontSize: 17, fontWeight: 500, opacity: 0.85}}>Friday, November 6</div>
      <div style={{position: 'absolute', top: 124, width: '100%', textAlign: 'center', fontSize: 104, fontWeight: 600, letterSpacing: '-0.02em'}}>{p.time}</div>
      {/* 通知（すりガラス）＝上から ease out で降りる */}
      <div style={{position: 'absolute', left: 14, right: 14, top: SH / 2 - 52, height: 104, borderRadius: 26,
        background: 'rgba(58,56,64,.62)', backdropFilter: 'blur(18px) saturate(1.4)', boxShadow: 'inset 0 1px 0 rgba(255,255,255,.22), 0 10px 30px rgba(0,0,0,.3)',
        transform: `translateY(${lerp(-40, 0, n)}px) scale(${lerp(0.94, 1, n)})`, opacity: n, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 12}}>
        <div style={{width: 46, height: 46, borderRadius: 11, background: '#5865f2', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none'}}>
          <Img src={staticFile('zg/discord.svg')} style={{width: 28, filter: 'brightness(0) invert(1)'}} />
        </div>
        <div style={{flex: 1, minWidth: 0}}>
          <div style={{display: 'flex', justifyContent: 'space-between', fontSize: 15, fontWeight: 600}}><span>{p.notifTitle}</span><span style={{opacity: 0.55, fontWeight: 400, fontSize: 13}}>now</span></div>
          <div style={{fontSize: 14, opacity: 0.9, marginTop: 2, lineHeight: 1.3}}>{p.notifBody}</div>
        </div>
      </div>
      <div style={{position: 'absolute', bottom: 10, left: SW / 2 - 70, width: 140, height: 5, borderRadius: 3, background: 'rgba(255,255,255,.8)'}} />
    </div>
  );
};

const Scene: React.FC<{p: T01Props}> = ({p}) => {
  const f = useCurrentFrame();
  const u = tw(f, p.zoomFrom, p.zoomTo, E.apple); // 寄りの進み（曲線つき）
  const lin = clamp01((f - p.zoomFrom) / (p.zoomTo - p.zoomFrom));
  const pre = tw(f, -16, p.zoomFrom + 10, E.linear);
  const S = logLerp(lerp(0.8, 0.92, pre), S_END, u) * (1 + Math.max(0, f - p.zoomTo + 14) * 0.0022); // 着いた後も息をする
  // 傾きは寄りの 8 割で 0 に（0 になったら 2D の変形だけ＝字がくっきり描き直される）
  const r0 = clamp01(u / 0.8), rr = r0 * r0 * (3 - 2 * r0);
  const rotY = lerp(lerp(-25, -15, pre), 0, rr);
  const rotX = lerp(lerp(9, 7, pre), 0, rr);
  const rotZ = lerp(-2.5, 0, rr);
  const flat = rr >= 0.9999;
  const y = lerp(28 + breathe(f, 4, 120), 0, u);
  const lockOp = 1 - clamp01((lin - 0.1) / 0.32);
  const worldOp = clamp01((lin - 0.08) / 0.3);
  const bezelOp = 1 - clamp01((u - 0.86) / 0.1);
  const ws = 1 / S_END;
  return (
    <AbsoluteFill style={{background: '#08080b', overflow: 'hidden'}}>
      {/* 舞台：暖黒＋商品色の 2 段の光（芯＋長い裾） */}
      <AbsoluteFill style={{background: `radial-gradient(circle 360px at 50% 56%, ${p.accent}55 0, ${p.accent}22 45%, transparent 100%), radial-gradient(circle 1000px at 50% 60%, ${p.accent}26 0, ${p.accent}0d 45%, transparent 100%)`, opacity: 1 - u}} />
      {/* 床の接地の影（寄ると外へ） */}
      <div style={{position: 'absolute', left: 960 - 230, top: 540 + 470 * Math.min(S, 2) / 0.9, width: 460, height: 60, borderRadius: '50%',
        background: 'radial-gradient(ellipse at center, rgba(0,0,0,.75) 0, rgba(0,0,0,0) 70%)', filter: 'blur(10px)', opacity: 1 - u * 3}} />
      <AbsoluteFill style={flat ? {} : {perspective: 2400, perspectiveOrigin: '50% 50%'}}>
        <div style={{position: 'absolute', left: 960 - PW / 2, top: 540 - PH / 2, width: PW, height: PH,
          transform: flat ? `translateY(${y}px) scale(${S})` : `translateY(${y}px) scale(${S}) rotateX(${rotX}deg) rotateY(${rotY}deg) rotateZ(${rotZ}deg)`, transformStyle: flat ? 'flat' : 'preserve-3d'}}>
          {/* 落ち影（柔らかい・下に偏る） */}
          <div style={{position: 'absolute', inset: 0, borderRadius: 68, boxShadow: '0 60px 120px -20px rgba(0,0,0,.85), 0 18px 40px rgba(0,0,0,.6)', opacity: bezelOp}} />
          {/* 本体＝チタンの縁（縦の映り込み＋上の縁の光 1 本） */}
          <div style={{position: 'absolute', inset: 0, borderRadius: 68, opacity: bezelOp,
            background: 'linear-gradient(160deg,#6b6e74 0%,#2b2d31 18%,#1a1b1e 50%,#3d4045 78%,#8a8d93 100%)',
            boxShadow: 'inset 0 1.5px 0 rgba(255,255,255,.55), inset 0 -1px 0 rgba(255,255,255,.18), inset 0 0 0 4px #0c0c0e'}} />
          {/* 画面 */}
          <div style={{position: 'absolute', left: BEZ, top: BEZ, width: SW, height: SH, borderRadius: 56, overflow: 'hidden', background: '#1e1f22'}}>
            <div style={{position: 'absolute', left: SW / 2 - 960, top: SH / 2 - 540, width: 1920, height: 1080, transform: `scale(${ws})`, opacity: worldOp}}>
              <World p={p} f={f} />
            </div>
            <div style={{position: 'absolute', inset: 0, opacity: lockOp}}><Lock p={p} f={f} /></div>
            {/* ガラスの映り込み（斜めの弱い帯）＝寄ると消える */}
            <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(115deg, rgba(255,255,255,0) 30%, rgba(255,255,255,.07) 42%, rgba(255,255,255,0) 54%)', opacity: 1 - u}} />
            {/* Dynamic Island */}
            <div style={{position: 'absolute', left: SW / 2 - 62, top: 14, width: 124, height: 36, borderRadius: 18, background: '#000', opacity: bezelOp}} />
          </div>
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{backgroundImage: GRAIN, opacity: 0.035, mixBlendMode: 'overlay', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};

export const T01_ZoomThroughScreen: React.FC<Partial<T01Props>> = (props) => {
  const p = {...t01Defaults, ...props};
  return p.blur ? (
    <CameraMotionBlur shutterAngle={180} samples={8}><Scene p={p} /></CameraMotionBlur>
  ) : (
    <Scene p={p} />
  );
};
