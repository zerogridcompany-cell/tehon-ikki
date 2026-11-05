// T01 ZoomThroughScreen（手札 R2_07・道 B＝@remotion/three）
// 宙の iPhone（角丸の箱・チタンの縁＝MeshPhysical の金属）→ カメラが画面へ寄り続け、画面の中の Discord の招待が画面いっぱいになる。
// カメラは 1 軸（寄り＝対数空間の距離＋Apple の曲線：加速短く・減速長く）。端末の傾きは同じ進みでほどける。
// 画面＝白い ZeroGrid の UI を Canvas2D で描いたテクスチャ（2048 幅＝寄り切っても 1:1 に近い）。
import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {CameraMotionBlur} from '@remotion/motion-blur';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {E, INTER, interReady, GRAIN, clamp01, lerp, logLerp, tw, breathe} from './lib';

export type T01Props = {
  accent: string; // 舞台の光（商品色 1 色）
  serverName: string;
  serverIcon: string;
  inviteLine: string;
  online: string;
  members: string;
  button: string;
  time: string;
  zoomFrom: number;
  zoomTo: number; // 曲線の終わり（90 より先＝最後まで減速しながら寄り続ける）
  blur: boolean;
};
export const t01Defaults: T01Props = {
  accent: '#f06433',
  serverName: 'ZeroGrid',
  serverIcon: 'zg/zg_mark.svg',
  inviteLine: "YOU'VE BEEN INVITED TO JOIN",
  online: '1,280 Online',
  members: '5,400 Members',
  button: 'Join Server',
  time: '9:41',
  zoomFrom: 10,
  zoomTo: 104,
  blur: true,
};
const src = (s: string) => (s.startsWith('http') ? s : staticFile(s));
const CF = (w: number, px: number) => `${w} ${px}px ${INTER}, 'Helvetica Neue', Helvetica, Arial, sans-serif`;

// 端末の寸法（three の単位）
const PW = 2.15, PH = 4.4, PD = 0.24, PR = 0.36, INS = 0.075;
const SW = PW - INS * 2, SH = PH - INS * 2, SR = PR - INS;
const TW = 2048, TH = Math.round((TW * SH) / SW);
// 画面の中の招待カード（テクスチャの px）
const CARD = {w: 1720, h: 1000}; const CARD_X = (TW - CARD.w) / 2, CARD_Y = Math.round(TH * 0.5 - CARD.h / 2);
const cardCenterY = SH / 2 - ((CARD_Y + CARD.h / 2) / TH) * SH; // 端末の座標で
const D_END = 2.05; // 寄り切った距離（カードの幅＝画面の約 88%）

function rounded(w: number, h: number, r: number) {
  const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + h - r);
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h); s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y); return s;
}
function planeUV(w: number, h: number, r: number) {
  const g = new THREE.ShapeGeometry(rounded(w, h, r), 32); const p = g.attributes.position, uv = g.attributes.uv;
  for (let i = 0; i < p.count; i++) uv.setXY(i, (p.getX(i) + w / 2) / w, (p.getY(i) + h / 2) / h); return g;
}
const rr = (g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) => { g.beginPath(); g.roundRect(x, y, w, h, r); };

// 画面の UI（白い Mercury 型の地＋Discord の招待カード＝公式の白モードの色）
function drawScreen(p: T01Props, icon: HTMLImageElement) {
  const c = document.createElement('canvas'); c.width = TW; c.height = TH; const g = c.getContext('2d')!;
  g.fillStyle = '#f8fcfd'; g.fillRect(0, 0, TW, TH);
  const bg = g.createRadialGradient(TW / 2, TH * 0.5, 0, TW / 2, TH * 0.5, TW * 0.9); bg.addColorStop(0, 'rgba(88,101,242,.10)'); bg.addColorStop(1, 'rgba(88,101,242,0)'); g.fillStyle = bg; g.fillRect(0, 0, TW, TH);
  g.fillStyle = '#040506'; g.font = CF(600, 64); g.fillText(p.time, 150, 170);
  // 上の帯：ZG の印＋名前
  g.drawImage(icon, 110, 330, 150, 97); g.font = CF(700, 84); g.fillText(p.serverName, 300, 410);
  g.fillStyle = '#8b93a1'; g.font = CF(500, 52); g.fillText('Community', 300, 480);
  g.fillStyle = '#e8e7ed'; g.fillRect(110, 560, TW - 220, 3);
  // 招待カード
  g.save(); g.shadowColor = 'rgba(20,20,60,.16)'; g.shadowBlur = 110; g.shadowOffsetY = 50; g.fillStyle = '#ffffff'; rr(g, CARD_X, CARD_Y, CARD.w, CARD.h, 34); g.fill(); g.restore();
  g.strokeStyle = '#e3e5e8'; g.lineWidth = 3; rr(g, CARD_X, CARD_Y, CARD.w, CARD.h, 34); g.stroke();
  g.textAlign = 'center'; const cx = TW / 2;
  g.fillStyle = '#5c5e66'; g.font = CF(600, 48); g.fillText(p.inviteLine, cx, CARD_Y + 120);
  g.fillStyle = '#fff'; g.save(); g.shadowColor = 'rgba(0,0,0,.10)'; g.shadowBlur = 40; g.shadowOffsetY = 16; rr(g, cx - 120, CARD_Y + 170, 240, 240, 64); g.fill(); g.restore();
  g.strokeStyle = '#e3e5e8'; g.lineWidth = 4; rr(g, cx - 120, CARD_Y + 170, 240, 240, 64); g.stroke();
  g.drawImage(icon, cx - 90, CARD_Y + 290 - 58, 180, 116);
  g.fillStyle = '#060607'; g.font = CF(700, 96); g.fillText(p.serverName, cx, CARD_Y + 530);
  g.font = CF(500, 52); g.fillStyle = '#5c5e66';
  g.fillText(`●  ${p.online}       ●  ${p.members}`, cx, CARD_Y + 625);
  g.fillStyle = '#23a55a'; g.beginPath(); g.arc(cx - g.measureText(`●  ${p.online}       ●  ${p.members}`).width / 2 + 18, CARD_Y + 607, 18, 0, 7); g.fill();
  g.fillStyle = '#5865f2'; rr(g, CARD_X + 120, CARD_Y + CARD.h - 250, CARD.w - 240, 150, 16); g.fill();
  g.fillStyle = '#fff'; g.font = CF(600, 68); g.fillText(p.button, cx, CARD_Y + CARD.h - 152);
  g.textAlign = 'left';
  // 下の行（ぼんやり見える次の情報）
  g.fillStyle = '#3a3f4b'; g.font = CF(600, 56); g.fillText('# daruma-drops', 150, CARD_Y + CARD.h + 200);
  g.fillStyle = '#8b93a1'; g.font = CF(500, 46); g.fillText('New colors every Friday', 150, CARD_Y + CARD.h + 280);
  g.fillStyle = 'rgba(4,5,6,.85)'; rr(g, TW / 2 - 260, TH - 80, 520, 22, 11); g.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 16; t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; return t;
}
function drawStage(accent: string) {
  const c = document.createElement('canvas'); c.width = 2048; c.height = 1152; const g = c.getContext('2d')!;
  g.fillStyle = '#08080b'; g.fillRect(0, 0, 2048, 1152);
  const blob = (r: number, a: number) => { const rg = g.createRadialGradient(1024, 640, 0, 1024, 640, r); const h = (x: number) => Math.round(x * 255).toString(16).padStart(2, '0'); rg.addColorStop(0, accent + h(a)); rg.addColorStop(0.45, accent + h(a * 0.35)); rg.addColorStop(1, accent + '00'); g.fillStyle = rg; g.fillRect(0, 0, 2048, 1152); };
  blob(360, 0.38); blob(1000, 0.12);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

const Env: React.FC = () => {
  const {gl, scene} = useThree();
  useMemo(() => {
    const pm = new THREE.PMREMGenerator(gl); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    (scene as any).environmentIntensity = 0.8; gl.toneMapping = THREE.ACESFilmicToneMapping; gl.toneMappingExposure = 1.0;
    gl.shadowMap.enabled = true; gl.shadowMap.type = THREE.VSMShadowMap;
  }, [gl, scene]);
  return null;
};

const World: React.FC<{p: T01Props; f: number; T: {screen: THREE.Texture; stage: THREE.Texture}}> = ({p, f, T}) => {
  const {camera} = useThree();
  const u = tw(f, p.zoomFrom, p.zoomTo, E.apple);
  const intro = tw(f, -6, 26, E.out); // 端末が回り込みながら来る（出てくる＝ease out）
  const r0 = clamp01(u / 0.7), rot = r0 * r0 * (3 - 2 * r0); // 傾きは寄りの 7 割で 0
  const dist = logLerp(13.5, D_END, u);
  camera.position.set(0, lerp(0.35, cardCenterY, u), dist); camera.lookAt(0, lerp(0, cardCenterY, u), 0); camera.updateMatrixWorld();
  const frameMat = useMemo(() => new THREE.MeshPhysicalMaterial({color: '#8e9096', metalness: 1, roughness: 0.28, clearcoat: 0.6, clearcoatRoughness: 0.2, envMapIntensity: 1.4}), []);
  const backMat = useMemo(() => new THREE.MeshPhysicalMaterial({color: '#2a2b30', metalness: 0.2, roughness: 0.35, clearcoat: 1, clearcoatRoughness: 0.15}), []);
  const body = useMemo(() => new THREE.ExtrudeGeometry(rounded(PW - 0.04, PH - 0.04, PR - 0.02), {depth: PD - 0.04, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 8, curveSegments: 48}), []);
  const screenGeo = useMemo(() => planeUV(SW, SH, SR), []);
  const glassGeo = useMemo(() => planeUV(PW - 0.03, PH - 0.03, PR - 0.015), []);
  const islandGeo = useMemo(() => planeUV(0.62, 0.18, 0.09), []);
  const ry = lerp(lerp(-1.05, -0.42, intro), 0, rot), rx = lerp(lerp(0.32, 0.14, intro), 0, rot), rz = lerp(-0.06, 0, rot);
  const py = lerp(lerp(-0.9, 0, intro) + breathe(f, 0.04, 100), 0, rot);
  const glow = Math.max(0, Math.sin(((f - 70) / 22) * Math.PI)) * (f > 70 ? 1 : 0);
  return (
    <>
      <Env />
      <ambientLight intensity={0.1} />
      <directionalLight position={[-2, 5, 9]} intensity={2.4} castShadow shadow-mapSize={[2048, 2048]} shadow-radius={16} shadow-blurSamples={20}
        shadow-camera-left={-5} shadow-camera-right={5} shadow-camera-top={5} shadow-camera-bottom={-5} />
      <directionalLight position={[6, 1, -3]} intensity={4} color="#ffffff" />
      <pointLight position={[0, -3.2, 1.2]} intensity={5} distance={5} color={p.accent} />
      {/* 舞台の板（影を受ける・商品色の 2 段の光） */}
      <mesh position={[0, 0, -2.2]}><planeGeometry args={[34, 19]} /><meshBasicMaterial map={T.stage} toneMapped={false} /></mesh>
      <mesh position={[0, 0, -2.19]} receiveShadow><planeGeometry args={[34, 19]} /><shadowMaterial transparent opacity={0.2} /></mesh>
      <group position={[0, py, 0]} rotation={[rx, ry, rz]}>
        <mesh geometry={body} position={[0, 0, -PD / 2 + 0.02]} castShadow><primitive object={frameMat} attach="material" /></mesh>
        <mesh position={[0, 0, -PD / 2 - 0.001]} rotation={[0, Math.PI, 0]} geometry={glassGeo}><primitive object={backMat} attach="material" /></mesh>
        {/* 前のガラスの黒い縁 → 画面 → ガラスの映り込み */}
        <mesh geometry={glassGeo} position={[0, 0, PD / 2 + 0.002]}><meshPhysicalMaterial color="#050506" roughness={0.05} clearcoat={1} metalness={0} /></mesh>
        <mesh geometry={screenGeo} position={[0, 0, PD / 2 + 0.004]}><meshBasicMaterial map={T.screen} toneMapped={false} /></mesh>
        <mesh geometry={islandGeo} position={[0, SH / 2 - 0.2, PD / 2 + 0.006]}><meshBasicMaterial color="#000" /></mesh>
        {/* Join の光の輪（押せる合図） */}
        <mesh geometry={planeUV(SW * ((CARD.w - 240) / TW), SH * (150 / TH), SH * (16 / TH))} position={[0, cardCenterY - SH * ((CARD.h / 2 - 175) / TH), PD / 2 + 0.0035]} scale={[1 + glow * 0.03, 1 + glow * 0.18, 1]}>
          <meshBasicMaterial color="#5865f2" transparent opacity={glow * 0.28} toneMapped={false} />
        </mesh>
        <mesh geometry={glassGeo} position={[0, 0, PD / 2 + 0.008]}><meshPhysicalMaterial color="#ffffff" transparent opacity={0.06 * (1 - u)} roughness={0} clearcoat={1} metalness={0} /></mesh>
      </group>
    </>
  );
};

const Scene: React.FC<{p: T01Props; T: any}> = ({p, T}) => {
  const f = useCurrentFrame();
  const {width, height} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: '#08080b'}}>
      <ThreeCanvas width={width} height={height} gl={{antialias: true}} camera={{fov: 30, position: [0, 0, 13], near: 0.05, far: 100}}>
        <World p={p} f={f} T={T} />
      </ThreeCanvas>
      <AbsoluteFill style={{backgroundImage: GRAIN, opacity: 0.03, mixBlendMode: 'overlay'}} />
    </AbsoluteFill>
  );
};

export const T01_ZoomThroughScreen: React.FC<Partial<T01Props>> = (props) => {
  const p = {...t01Defaults, ...props};
  const [h] = useState(() => delayRender('t01-assets'));
  const [T, setT] = useState<any>(null);
  useEffect(() => {
    const img = new Image(); img.src = src(p.serverIcon);
    Promise.all([interReady(), new Promise((r) => (img.onload = r))]).then(() => Promise.all([document.fonts.load(CF(600, 40)), document.fonts.load(CF(700, 40)), document.fonts.load(CF(500, 40))]))
      .then(() => { setT({screen: drawScreen(p, img), stage: drawStage(p.accent)}); continueRender(h); });
  }, []); // eslint-disable-line
  if (!T) return <AbsoluteFill style={{background: '#08080b'}} />;
  return p.blur ? <CameraMotionBlur shutterAngle={180} samples={6}><Scene p={p} T={T} /></CameraMotionBlur> : <Scene p={p} T={T} />;
};
