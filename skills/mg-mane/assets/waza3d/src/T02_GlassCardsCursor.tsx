// T02 GlassCardsCursor（手札 R2_09・道 B＝@remotion/three）
// 斜めの階段に並ぶガラスの札。ガラスのカーソルが来て、1 枚が持ち上がり、Approve を押す。
// 質：MeshPhysicalMaterial（透過・粗さ・clearcoat）＋部屋の映り込み（RoomEnvironment＝手続きで作る・外の HDR なし）＋3 灯
//     ＋接地の影（VSM のやわらかい影）＋被写界深度は「ぼかしの層」（同じ場面をもう 1 枚ぼかして上下だけ見せる）。カメラは 1 軸（寄り）。
import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {E, INTER, interReady, GRAIN, clamp01, lerp, tw} from './lib';
const CF = (w: number, px: number) => `${w} ${px}px ${INTER}, 'Helvetica Neue', Helvetica, Arial, sans-serif`;

export type T02Item = {title: string; sub: string};
export type T02Props = {
  accent: string;
  items: T02Item[]; // 4 枚
  target: number; // 押す札
  button: string;
  done: string;
  bgTop: string;
  bgBottom: string;
};
export const t02Defaults: T02Props = {
  accent: '#5268e4',
  items: [
    {title: 'New ad set · Daruma Red', sub: 'Meta · ¥30,000 / day'},
    {title: 'Store page update', sub: 'Hero image + price'},
    {title: 'Reply to 3 customers', sub: 'Drafted by your team'},
    {title: 'Restock 400 units', sub: 'Supplier in Shenzhen'},
  ],
  target: 1,
  button: 'Approve',
  done: 'Approved',
  bgTop: '#15161d',
  bgBottom: '#07070a',
};

const CW = 3.7, CH = 0.74, CD = 0.1, GAP = 0.9;
function roundedShape(w: number, h: number, r: number) {
  const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + h - r);
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h); s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y); return s;
}
function planeUV(w: number, h: number, r: number) {
  const g = new THREE.ShapeGeometry(roundedShape(w, h, r), 24); const p = g.attributes.position, uv = g.attributes.uv;
  for (let i = 0; i < p.count; i++) uv.setXY(i, (p.getX(i) + w / 2) / w, (p.getY(i) + h / 2) / h); return g;
}
function tex(draw: (g: CanvasRenderingContext2D, W: number, H: number) => void, W: number, H: number) {
  const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d')!; draw(g, W, H);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

const Env: React.FC = () => {
  const {gl, scene} = useThree();
  useMemo(() => {
    const pm = new THREE.PMREMGenerator(gl); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    (scene as any).environmentIntensity = 0.55;
    gl.toneMapping = THREE.ACESFilmicToneMapping; gl.toneMappingExposure = 1.05;
    gl.shadowMap.enabled = true; gl.shadowMap.type = THREE.VSMShadowMap;
  }, [gl, scene]);
  return null;
};

const Cam: React.FC<{f: number}> = ({f}) => {
  const {camera} = useThree();
  const k = tw(f, -30, 120, E.linear);
  camera.position.set(0, 0.15, lerp(11.6, 9.0, k)); camera.lookAt(0, 0, 0); camera.updateMatrixWorld();
  return null;
};

const World: React.FC<{p: T02Props; f: number; T: any}> = ({p, f, T}) => {
  const glass = useMemo(() => new THREE.MeshPhysicalMaterial({color: '#d9dbe6', transmission: 1, roughness: 0.22, thickness: 0.55, ior: 1.48,
    clearcoat: 1, clearcoatRoughness: 0.08, metalness: 0, attenuationColor: new THREE.Color('#3b3f52'), attenuationDistance: 1.1, specularIntensity: 1, envMapIntensity: 1.2}), []);
  const cardGeo = useMemo(() => new THREE.ExtrudeGeometry(roundedShape(CW, CH, 0.2), {depth: CD, bevelEnabled: true, bevelThickness: 0.025, bevelSize: 0.025, bevelSegments: 6, curveSegments: 24}), []);
  const faceGeo = useMemo(() => planeUV(CW, CH, 0.2), []);
  const pillGeo = useMemo(() => planeUV(0.86, 0.3, 0.15), []);
  const cursorGeo = useMemo(() => {
    const s = new THREE.Shape(); s.moveTo(0, 0); s.lineTo(0, -0.62); s.lineTo(0.15, -0.48); s.lineTo(0.26, -0.72); s.lineTo(0.36, -0.67); s.lineTo(0.25, -0.44); s.lineTo(0.45, -0.44); s.lineTo(0, 0);
    const g = new THREE.ExtrudeGeometry(s, {depth: 0.07, bevelEnabled: true, bevelThickness: 0.03, bevelSize: 0.025, bevelSegments: 5}); g.center(); return g;
  }, []);
  const cursorMat = useMemo(() => new THREE.MeshPhysicalMaterial({color: '#ffffff', roughness: 0.12, clearcoat: 1, transmission: 0.25, thickness: 0.2, ior: 1.4}), []);
  const bgMat = useMemo(() => new THREE.MeshStandardMaterial({map: T.bg, roughness: 1, metalness: 0}), [T]);

  // 札の入り（下から・ease out・4 コマずつ遅れて・頭は途中から始める＝0 コマ目から動いとる）
  const hoverIn = tw(f, 40, 56, E.out);
  const press = tw(f, 56, 60, E.out) - tw(f, 60, 70, E.out);
  const fill = tw(f, 58, 68, E.out);
  // カーソル（中を移動＝ease in-out・押した後はゆっくり去る）
  const cu = tw(f, 14, 52, E.inout), cl = tw(f, 64, 104, E.inout);
  const tgtY = (1.5 - p.target) * GAP;
  const cx = lerp(lerp(3.6, 1.35, cu), 1.9, cl), cy = lerp(lerp(-2.6, tgtY - 0.12, cu), tgtY - 0.55, cl);
  const ring = clamp01((f - 58) / 22);
  return (
    <>
      <Env />
      <Cam f={f} />
      <ambientLight intensity={0.15} />
      {/* 3 灯＝主（上左・影を落とす）・縁（右奥・縁の光 1 本）・補（下・商品色） */}
      <directionalLight position={[-3, 5, 6]} intensity={2.2} castShadow shadow-mapSize={[2048, 2048]} shadow-radius={14} shadow-blurSamples={20}
        shadow-camera-left={-6} shadow-camera-right={6} shadow-camera-top={6} shadow-camera-bottom={-6} shadow-bias={-0.0004} />
      <directionalLight position={[6, 2, -4]} intensity={3.2} color="#e6ecff" />
      <pointLight position={[0, -3, 2]} intensity={6} distance={9} color={p.accent} />
      <group rotation={[-0.78, 0.34, 0.52]} position={[0.1, -0.05, 0]}>
        {/* 地の板（影を受ける・ガラスの向こうの光の玉） */}
        <mesh position={[0, 0, -0.62]} receiveShadow><planeGeometry args={[44, 26]} /><primitive object={bgMat} attach="material" /></mesh>
        {p.items.map((it, i) => {
          const a = tw(f, -14 + i * 4, 14 + i * 4, E.out);
          const isT = i === p.target;
          const lift = isT ? hoverIn * 0.26 - press * 0.06 : -hoverIn * 0.03;
          const y = (1.5 - i) * GAP;
          return (
            <group key={i} position={[lerp(0.5, 0, a), y + lerp(-0.7, 0, a), lerp(-0.55, 0, a) + lift + i * -0.02]} rotation={[isT ? hoverIn * -0.1 : 0, isT ? hoverIn * 0.05 : 0, 0]}>
              <mesh geometry={cardGeo} position={[0, 0, -CD / 2]} castShadow><primitive object={glass} attach="material" /></mesh>
              <mesh geometry={faceGeo} position={[0, 0, CD / 2 + 0.03]}><meshBasicMaterial map={T.face[i]} transparent toneMapped={false} opacity={lerp(0.6, 1, isT ? hoverIn : 0.4)} /></mesh>
              {/* Approve の札（縁→押すと商品色で満ちる） */}
              <mesh geometry={pillGeo} position={[CW / 2 - 0.62, 0, CD / 2 + 0.035]} scale={isT ? 1 - press * 0.06 : 1}>
                <meshBasicMaterial color={p.accent} transparent opacity={isT ? fill : 0} toneMapped={false} />
              </mesh>
              <mesh geometry={pillGeo} position={[CW / 2 - 0.62, 0, CD / 2 + 0.04]} scale={isT ? 1 - press * 0.06 : 1}>
                <meshBasicMaterial map={T.pill} transparent opacity={isT ? 1 - fill : 0.75} toneMapped={false} />
              </mesh>
              {isT && <mesh geometry={pillGeo} position={[CW / 2 - 0.62, 0, CD / 2 + 0.045]}><meshBasicMaterial map={T.pillDone} transparent opacity={fill} toneMapped={false} /></mesh>}
              {isT && ring > 0 && ring < 1 && (
                <mesh position={[CW / 2 - 0.62, 0, CD / 2 + 0.03]} scale={1 + E.out(ring) * 1.1}>
                  <ringGeometry args={[0.2, 0.215, 64]} /><meshBasicMaterial color={p.accent} transparent opacity={(1 - ring) * 0.8} toneMapped={false} />
                </mesh>
              )}
            </group>
          );
        })}
        {/* ガラスのカーソル（札の上 0.5・影を落とす） */}
        <mesh geometry={cursorGeo} position={[cx, cy, 0.55 - press * 0.12]} rotation={[0, 0, 0.18]} scale={0.62 * (1 - press * 0.1)} castShadow>
          <primitive object={cursorMat} attach="material" />
        </mesh>
      </group>
    </>
  );
};

export const T02_GlassCardsCursor: React.FC<Partial<T02Props>> = (props) => {
  const p = {...t02Defaults, ...props};
  const f = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const [h] = useState(() => delayRender('fonts'));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    interReady().then(() => Promise.all([document.fonts.load(CF(600, 40)), document.fonts.load(CF(500, 30))])).then(() => { setReady(true); continueRender(h); });
  }, [h]);
  const T = useMemo(() => {
    if (!ready) return null;
    const face = p.items.map((it) => tex((g, W, H) => {
      g.clearRect(0, 0, W, H);
      g.fillStyle = 'rgba(255,255,255,.10)'; g.beginPath(); g.arc(92, H / 2, 46, 0, Math.PI * 2); g.fill();
      g.strokeStyle = 'rgba(255,255,255,.75)'; g.lineWidth = 5; g.beginPath(); g.arc(92, H / 2, 20, 0, Math.PI * 2); g.stroke();
      g.fillStyle = '#ffffff'; g.font = CF(600, 46); g.fillText(it.title, 170, H / 2 - 4);
      g.fillStyle = 'rgba(235,238,255,.62)'; g.font = CF(500, 32); g.fillText(it.sub, 170, H / 2 + 42);
    }, 1280, 256));
    const pill = tex((g, W, H) => {
      g.strokeStyle = 'rgba(255,255,255,.8)'; g.lineWidth = 4; g.beginPath(); g.roundRect(3, 3, W - 6, H - 6, H / 2 - 3); g.stroke();
      g.fillStyle = '#fff'; g.font = CF(600, 44); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(p.button, W / 2, H / 2 + 2);
    }, 300, 104);
    const pillDone = tex((g, W, H) => {
      g.fillStyle = '#fff'; g.font = CF(600, 42); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('✓ ' + p.done, W / 2, H / 2 + 2);
    }, 300, 104);
    const bg = tex((g, W, H) => {
      const lg = g.createLinearGradient(0, 0, 0, H); lg.addColorStop(0, p.bgTop); lg.addColorStop(1, p.bgBottom); g.fillStyle = lg; g.fillRect(0, 0, W, H);
      const blob = (x: number, y: number, r: number, c: string, a: number) => { const rg = g.createRadialGradient(x, y, 0, x, y, r); rg.addColorStop(0, c + Math.round(a * 255).toString(16).padStart(2, '0')); rg.addColorStop(0.45, c + Math.round(a * 0.35 * 255).toString(16).padStart(2, '0')); rg.addColorStop(1, c + '00'); g.fillStyle = rg; g.fillRect(0, 0, W, H); };
      blob(W * 0.56, H * 0.46, W * 0.16, p.accent, 0.85); blob(W * 0.56, H * 0.46, W * 0.42, p.accent, 0.35); blob(W * 0.6, H * 0.42, W * 0.1, '#ff9a5a', 0.18);
    }, 2048, 1200);
    return {face, pill, pillDone, bg};
  }, [ready, p.items, p.button, p.done, p.accent, p.bgTop, p.bgBottom]);
  if (!T) return <AbsoluteFill style={{background: p.bgBottom}} />;
  const canvas = (extra: React.CSSProperties) => (
    <AbsoluteFill style={extra}>
      <ThreeCanvas width={width} height={height} gl={{antialias: true}} camera={{fov: 30, position: [0, 0.15, 11], near: 0.1, far: 100}}>
        <World p={p} f={f} T={T} />
      </ThreeCanvas>
    </AbsoluteFill>
  );
  return (
    <AbsoluteFill style={{background: p.bgBottom}}>
      {canvas({})}
      {/* 被写界深度＝ぼかしの層：同じ場面をぼかして、ピントの帯（押す札の高さ）の外だけ見せる */}
      {canvas({filter: 'blur(9px)', WebkitMaskImage: 'linear-gradient(180deg, #000 0%, rgba(0,0,0,.85) 14%, transparent 36%, transparent 64%, rgba(0,0,0,.85) 86%, #000 100%)'})}
      <AbsoluteFill style={{background: 'radial-gradient(ellipse 75% 70% at 50% 48%, transparent 55%, rgba(0,0,0,.45) 100%)'}} />
      <AbsoluteFill style={{backgroundImage: GRAIN, opacity: 0.04, mixBlendMode: 'overlay'}} />
    </AbsoluteFill>
  );
};
