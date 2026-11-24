// three.js の部品：光る線（Line2 の太い線＋にじみ）・映り込み・床・粒・光のにじみ（UnrealBloom）
import React, {useMemo, useContext} from 'react';
export const MirCtx = React.createContext(false);
import * as THREE from 'three';
import {useThree, useFrame} from '@react-three/fiber';
import {LineSegments2} from 'three/examples/jsm/lines/LineSegments2.js';
import {LineSegmentsGeometry} from 'three/examples/jsm/lines/LineSegmentsGeometry.js';
import {LineMaterial} from 'three/examples/jsm/lines/LineMaterial.js';
import {EffectComposer} from 'three/examples/jsm/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/examples/jsm/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/examples/jsm/postprocessing/OutputPass.js';
import {Pass, FullScreenQuad} from 'three/examples/jsm/postprocessing/Pass.js';
import type {Seg} from './geo';

export const W = 1080, H = 1920;
// 🎨 差し色はここ 1 か所（ACCENT）。goat は手本の色のまま（本人が色を選んだらここだけ替えて書き出し直す）
export const ACCENT = {cyan: '#2fb9d6', cyanCore: '#9ef0ff', red: '#ef5a60', redCore: '#ffc2c4', orange: '#f59f5b', orangeCore: '#ffd6ad', yellow: '#f0cf4a', yellowCore: '#fff2a8', teal: '#4ff0c8', tealCore: '#c8fff0', white: '#c8d0d8', whiteCore: '#ffffff'};
export const GOLD = ACCENT.cyan, GOLD_CORE = ACCENT.cyanCore, WHITE = '#f4f4f4', RED = ACCENT.red;

// 線の材質（画面の太さ px＝遠くても細くならん・手本の線は遠近でほぼ同じ太さ）。w は m の単位で書いて PX 倍
export const PX = 175;
export const lineMat = (color: string, width: number, opacity = 1, additive = false) => {
  const m = new LineMaterial({color: new THREE.Color(color).getHex(), linewidth: width * PX, worldUnits: false, transparent: true, opacity, depthWrite: false, fog: true} as any);
  if (additive) m.blending = THREE.AdditiveBlending;
  m.side = THREE.DoubleSide; m.resolution.set(W, H); m.toneMapped = false; return m;
};
const geoCache = new Map<Seg, LineSegmentsGeometry>();
export const segGeo = (s: Seg) => { let g = geoCache.get(s); if (!g) { g = new LineSegmentsGeometry(); g.setPositions(s); geoCache.set(s, g); } return g; };

// 光る線（芯＋にじみの 2 本）。op＝見え方 0〜1・mir＝映り込み（暗く）
export const Glow: React.FC<{seg: Seg; color?: string; core?: string; w?: number; op?: number; mir?: boolean; halo?: number; pos?: number[]; rot?: number[]; scale?: number | number[]; draw?: number}> =
  ({seg, color = GOLD, core = GOLD_CORE, w = 0.026, op = 1, mir: mir0 = false, halo = 0.12, pos, rot, scale, draw = 1}) => {
  const mir = useContext(MirCtx) || mir0;
  const g = segGeo(seg);
  const [m1, m2] = useMemo(() => [lineMat(core, w, 1), lineMat(color, w * 2.7, 1, true)], [core, color, w]);
  const k = mir ? 0.18 : 1; const o = Math.min(1, op); m1.opacity = o * k; m2.opacity = o * halo * k;
  // draw＜1 は線の本数を先から順に出す（描いていく）
  const n = Math.max(0, Math.floor((seg.length / 6) * draw));
  g.instanceCount = n;
  const o1 = useMemo(() => new LineSegments2(g, m1), [g, m1]), o2 = useMemo(() => new LineSegments2(g, m2), [g, m2]);
  if (op <= 0.002 || n === 0) return null;
  o1.renderOrder = o2.renderOrder = mir ? -30 : 0;
  return <group position={pos as any} rotation={rot as any} scale={scale as any}><primitive object={o2} /><primitive object={o1} /></group>;
};

// 後処理：カメラのぶれ（速く動く時だけ・cams の数だけ描いて平均）→ 光のにじみ（UnrealBloom）
class BlurRenderPass extends Pass {
  scene: THREE.Scene; camera: THREE.PerspectiveCamera; cams: number[][] = []; tmp: THREE.WebGLRenderTarget; quad: FullScreenQuad; qm: THREE.MeshBasicMaterial;
  constructor(scene: THREE.Scene, camera: THREE.PerspectiveCamera) {
    super(); this.scene = scene; this.camera = camera; this.needsSwap = false;
    this.tmp = new THREE.WebGLRenderTarget(W, H, {type: THREE.HalfFloatType, samples: 4});
    this.qm = new THREE.MeshBasicMaterial({map: this.tmp.texture, transparent: true, blending: THREE.AdditiveBlending, depthTest: false, depthWrite: false, toneMapped: false});
    this.quad = new FullScreenQuad(this.qm);
  }
  render(renderer: THREE.WebGLRenderer, _w: THREE.WebGLRenderTarget, readBuffer: THREE.WebGLRenderTarget) {
    const ac = renderer.autoClear; renderer.autoClear = false;
    const target = this.renderToScreen ? null : readBuffer;
    this.camera.aspect = W / H; this.camera.updateProjectionMatrix();   // R3F が箱の大きさで書き換えるので毎回戻す
    renderer.setRenderTarget(target); renderer.setClearColor(0x000000, 1); renderer.clear();
    const list: (number[] | null)[] = this.cams.length > 1 ? this.cams : [null]; const n = list.length; this.qm.opacity = 1 / n;
    for (const c of list) {
      if (c) setCam(this.camera, c);
      renderer.setRenderTarget(this.tmp); renderer.clear(); renderer.render(this.scene, this.camera);
      renderer.setRenderTarget(target); this.quad.render(renderer);
    }
    if (n > 1) setCam(this.camera, this.cams[Math.floor(n / 2)]);
    renderer.autoClear = ac;
  }
}
export const setCam = (cam: THREE.PerspectiveCamera, c: number[]) => {
  cam.position.set(c[0], c[1], c[2]); cam.fov = c[6]; cam.aspect = W / H; cam.near = 0.05; cam.far = 300; cam.updateProjectionMatrix();
  cam.up.set(Math.sin(c[7] || 0), Math.cos(c[7] || 0), 0); cam.lookAt(c[3], c[4], c[5]); cam.updateMatrixWorld(); (cam as any).manual = true;
};
export const Post: React.FC<{strength?: number; radius?: number; threshold?: number; cams?: number[][]; skip?: boolean}> = ({strength = 0.24, radius = 0.2, threshold = 0.25, cams = [], skip = false}) => {
  const {gl, scene, camera} = useThree();
  const [comp, rp] = useMemo(() => {
    gl.localClippingEnabled = true; gl.toneMapping = THREE.NoToneMapping;   // R3F の既定（ACES）は色をくすませる
    const c = new EffectComposer(gl); c.setPixelRatio(1); c.setSize(W, H);
    const r = new BlurRenderPass(scene, camera as THREE.PerspectiveCamera);
    c.addPass(r); c.addPass(new UnrealBloomPass(new THREE.Vector2(W, H), strength, radius, threshold)); c.addPass(new OutputPass());
    return [c, r] as const;
  }, [gl, scene, camera]);
  const bp = comp.passes[1] as UnrealBloomPass; bp.strength = strength; bp.radius = radius; bp.threshold = threshold;
  (bp as any).highPassUniforms['smoothWidth'].value = 0.5;   // にじみの入り口をなだらかに（既定 0.01 だと消えていく札がしきいを越えた 1 コマでにじみが消える＝ポン）
  rp.cams = cams;
  useFrame(() => { if (skip) { gl.setRenderTarget(null); gl.setClearColor('#000000', 1); gl.clear(); return; } comp.render(); }, 1);   // skip＝重ねる 2 枚目を使わんコマ（黒で消すだけ）
  return null;
};

// 床：黒い鏡（映り込みは下に逆さに描いた物を半分透ける黒で覆う）＋道の白い破線
export const Floor: React.FC<{op?: number}> = ({op = 1}) => {
  // 床（黒い鏡）＋床の下に薄い黒の板を何枚も重ねる＝映り込みが深いほど暗くなる（手本の床は映り込みがすぐ消える）
  const ys = [0.002, -0.2, -0.45, -0.75, -1.1, -1.6, -2.3];
  return <>{ys.map((y, i) => <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[0, y, 0]} renderOrder={-20 + i}>
    <planeGeometry args={[400, 400]} />
    <meshBasicMaterial color="#000000" transparent opacity={(i === 0 ? 0.45 : 0.3) * op} depthWrite={false} />
  </mesh>)}</>;
};

// 背景の粒（ぼけた小さい点）
export const Dust: React.FC<{n?: number; seed?: number; spread?: number[]}> = ({n = 220, seed = 7, spread = [40, 14, 40]}) => {
  const obj = useMemo(() => {
    let s = seed; const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    const p = new Float32Array(n * 3); const col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { p[i * 3] = (r() - 0.5) * spread[0]; p[i * 3 + 1] = 0.3 + r() * spread[1]; p[i * 3 + 2] = (r() - 0.5) * spread[2]; const warm = r() < 0.35, b = 0.25 + r() * 0.45; col[i * 3] = b; col[i * 3 + 1] = b * (warm ? 0.8 : 1); col[i * 3 + 2] = b * (warm ? 0.45 : 1); }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3)); g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d')!; const gr = x.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.4, 'rgba(255,255,255,0.5)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = gr; x.fillRect(0, 0, 64, 64);
    const m = new THREE.PointsMaterial({size: 0.09, vertexColors: true, map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true});
    return new THREE.Points(g, m);
  }, [n, seed]);
  return <primitive object={obj} />;
};

// カメラ：[位置 xyz, 見る点 xyz, 画角, 傾き]
export const Cam: React.FC<{c: number[]}> = ({c}) => { const {camera} = useThree(); setCam(camera as THREE.PerspectiveCamera, c); return null; };
